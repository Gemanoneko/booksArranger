"""Offline operator capabilities for exact reviewed output relocation plans.

No app startup, scan, job recovery, queue reset, configuration editing or process
control. The app must release its existing native catalog ownership normally.
"""
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
import uuid
from catalog_owner import catalog_lock
from native_io import DirectoryBoundary,VerifiedFile,ordinary,BoundaryError
from output_migration import MigrationWorker,row,digest
import publication_locations as locations

PLAN_SCHEMA='books-reviewed-output-migration-v1'

def policy_roots(policy):
    from source_config import normalize_sources
    if not isinstance(policy,dict) or set(policy)!={'legacy_roots','audiobook_sources','audiobook_output_root'}:raise ValueError('Exact source/output policy is required')
    roots=policy['legacy_roots']
    if not isinstance(roots,dict) or 'Audiobooks' not in roots:raise ValueError('Legacy source root is required')
    config=normalize_sources(roots,policy['audiobook_sources'],policy['audiobook_output_root'])
    if not config.audiobook_output_root:raise ValueError('Explicit output root required')
    expected={key:str(ordinary(value)) for key,value in roots.items()}
    for index,root in enumerate(config.audiobook_sources):expected['Audiobooks source '+str(index+1)]=str(ordinary(root))
    expected['Audiobooks output']=str(ordinary(config.audiobook_output_root))
    return expected

@contextlib.contextmanager
def catalog_identity_lease(database):
    # READ_ATTRIBUTES permits SQLite writes, while withholding DELETE sharing
    # prevents pathname replacement throughout the actual owned operation.
    import ctypes
    from native_io import kernel,FileInfo
    path=ordinary(database)
    with DirectoryBoundary(path.anchor,path.parent):
        handle=kernel.CreateFileW(str(path),0x80,3,None,3,0x00200000,None)
        if handle==ctypes.c_void_p(-1).value:raise ValueError('Native catalog identity cannot be retained')
        try:
            info=FileInfo()
            if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or info.attributes&(0x400|0x10) or info.links!=1:raise ValueError('Catalog is not a unique ordinary file')
            view=VerifiedFile(path);view.handle=handle;view.info=info;facts=view.facts();view.handle=None
            yield {key:facts[key] for key in ('identity','dev','ino','identity_method','identity_api_error','links')}
        finally:kernel.CloseHandle(handle)

class MigrationOperation:
    def __init__(self,database,roots,plan_path,plan_sha256,*,stop=None):
        self.database=ordinary(database);self.roots={key:str(ordinary(value)) for key,value in roots.items()}
        self.plan_path=ordinary(plan_path);self.plan_sha256=plan_sha256
        if not isinstance(plan_sha256,str) or len(plan_sha256)!=64:raise ValueError('Exact reviewed plan SHA256 is required')
        if self.plan_path.is_relative_to(self.database.parent) or any(self.plan_path.is_relative_to(ordinary(root)) for root in self.roots.values()):raise ValueError('Keep reviewed plan outside catalog data and libraries')
        self.stop=stop or threading.Event();self.worker=MigrationWorker(self.database,operation_lease=self.operation_lease,media_verify=self.media_verify,invalidate=self.invalidate,stop=self.stop)

    def _plan(self,file):
        if file.facts()['links']!=1 or file.facts()['size']>4*1024*1024:raise ValueError('Migration plan is not a bounded unique file')
        raw=b''.join(file.chunks())
        if hashlib.sha256(raw).hexdigest()!=self.plan_sha256:raise ValueError('Reviewed migration plan changed')
        plan=json.loads(raw)
        if plan.get('schema')!=PLAN_SCHEMA or ordinary(plan.get('database',''))!=self.database:raise ValueError('Plan catalog/schema differs')
        if policy_roots(plan.get('source_policy'))!=self.roots or plan.get('roots')!=self.roots:raise ValueError('Reviewed plan source/output roots differ from concrete operation')
        if plan.get('source_policy_sha256')!=digest(plan['source_policy']):raise ValueError('Reviewed source/output policy digest differs')
        if plan.get('catalog_identity')!=self.catalog_facts:raise ValueError('Reviewed native catalog identity differs')
        inputs=plan.get('planning_inputs')
        if not isinstance(inputs,dict) or inputs.get('configuration_sha256')!=digest({'database':str(self.database),**plan['source_policy']}) or not isinstance(inputs.get('routing_decisions_sha256'),str) or len(inputs['routing_decisions_sha256'])!=64:raise ValueError('Reviewed configuration/decisions identity differs')
        selected=plan.get('verification_selection')
        if selected is not None and (not isinstance(selected,list) or len(selected)>10000 or any(not isinstance(identity,str) for identity in selected) or len(set(selected))!=len(selected)):raise ValueError('Reviewed verification selection is malformed')
        entries=plan.get('publications')
        if not isinstance(entries,list) or not entries or len(entries)>10000 or len({entry.get('publication_id') for entry in entries})!=len(entries):raise ValueError('Invalid reviewed publication scope')
        return plan

    def _scope(self,db,entry):
        publication=row(db,'SELECT * FROM output_relocations WHERE publication_id=?',(entry['publication_id'],))
        if publication is None or entry.get('frozen_binding_sha256')!=digest(locations._frozen(publication)):raise ValueError('Reviewed publication binding changed')
        expected={'source':json.loads(publication['original_output_json'])['final_path'],'destination':publication['planned_destination'],'kind':publication['publication_kind'],'candidate_id':publication['candidate_id'],'size':json.loads(publication['original_output_json'])['size']}
        if any(type(entry.get(key)) is not type(value) or entry.get(key)!=value for key,value in expected.items()):raise ValueError('Reviewed publication displayed scope differs from immutable binding')
        if publication['target_root']!=self.plan['source_policy']['audiobook_output_root']:raise ValueError('Publication output root differs from reviewed policy')
        if publication['source_fingerprint']!=json.loads(publication['accepted_routing_json']).get('source_fingerprint'):raise ValueError('Reviewed source fingerprint differs')
        job=row(db,'SELECT * FROM audio_jobs WHERE job_id=?',(publication['job_id'],))
        envelope=locations.resolve(db,job,publication['publication_kind'],json.loads(publication['original_output_json']))
        routing=json.loads(publication['accepted_routing_json'])
        candidate=row(db,'SELECT * FROM book_groups WHERE id=?',(publication['candidate_id'],))
        context=row(db,'SELECT * FROM candidate_context WHERE id=?',(publication['candidate_id'],))
        if candidate is None or context is None or candidate['superseded'] or candidate['changed'] or candidate['fingerprint']!=publication['source_fingerprint']:raise ValueError('Reviewed current book/source identity changed')
        review=json.loads(candidate['review']);accepted=json.loads(context['data'])
        if candidate['revision']!=context['revision'] or not accepted.get('metadata_approved') or accepted.get('automatic_pending'):raise ValueError('Book approval changed before migration')
        if routing.get('accepted_candidate_revision')!=candidate['revision'] or routing.get('accepted_review_sha256')!=digest(review):raise ValueError('Accepted routing review changed')
        manifest=json.loads(job['manifest']);original=json.loads(publication['original_output_json'])
        from organization import frozen_plan
        if manifest.get('metadata_facts',{}).get('destination_suffix') and frozen_plan(manifest,publication['target_root'],routing['routing_review'])['path']!=publication['planned_destination']:raise ValueError('Reviewed frozen recording route differs')
        if manifest.get('metadata_facts',{}).get('destination_suffix') and (routing.get('recording_facts_sha256')!=digest(manifest['metadata_facts']) or accepted.get('metadata_facts')!=manifest['metadata_facts']):raise ValueError('Reviewed recording distinction evidence changed')
        if manifest['root'] not in self.plan['source_policy']['audiobook_sources']:raise ValueError('Publication source root is outside reviewed configured sources')
        from review_backend import member_key
        from encoding_policy import PROFILE,AUTOMATIC_PROFILE
        if not accepted.get('source_coverage_confirmed') or not accepted.get('order_confirmed'):raise ValueError('Source membership/order approval changed')
        included=accepted.get('included',[]);order=accepted.get('track_order',[])
        keys=[member_key(source['path']) for source in manifest['sources']]
        if set(included)!=set(keys) or [key for key in order if key in included]!=keys:raise ValueError('Reviewed source membership/order differs from publication')
        for source in manifest['sources']:
            saved=accepted.get('source_hashes',{}).get(member_key(source['path']),{})
            if any(str(saved.get(field))!=str(source.get(field)) for field in ('sha256','size','modified')):raise ValueError('Reviewed source hash proof changed')
        if accepted.get('cover_id')!=manifest.get('cover',{}).get('id'):raise ValueError('Reviewed cover correspondence changed')
        cleanup=row(db,'SELECT * FROM source_cleanup WHERE job_id=?',(publication['job_id'],))
        if (manifest.get('cleanup_policy',{}).get('enabled') or cleanup) and (not cleanup or cleanup.get('state')!='completed'):raise ValueError('Publication source cleanup is not complete')
        has_storage=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='storage_cleanup_jobs'").fetchone()
        storage=row(db,'SELECT * FROM storage_cleanup_jobs WHERE job_id=?',(publication['job_id'],)) if has_storage else None
        if (manifest.get('profile') in {PROFILE,AUTOMATIC_PROFILE} or storage) and (not storage or storage.get('state')!='completed'):raise ValueError('Publication working-copy cleanup is not complete')
        if publication['publication_kind'] in {'Chapters','Chaptersv2'}:self._authorized_chapter(db,publication)
        return publication,envelope

    def _authorized_chapter(self,db,publication):
        from current_audiobook import CurrentAudiobooks
        from publication_binding import PublicationBindings
        raw=row(db,'SELECT * FROM audio_jobs WHERE job_id=?',(publication['job_id'],))
        parent=dict(raw,manifest=json.loads(raw['manifest']),output=json.loads(raw['output']))
        views=CurrentAudiobooks(tuple(self.roots.values()),self.database.parent/'chapter-repairs',None,bindings=PublicationBindings(self.database))
        accepted=json.loads(publication['accepted_routing_json']);expected=json.loads(publication['original_output_json'])
        candidates=[item for item in views._repairs(parent) if ('Chaptersv2' if item['corrected'] else 'Chapters')==publication['publication_kind']]
        if len(candidates)!=1 or candidates[0]['record']!=expected or candidates[0]['journal_sha256']!=accepted.get('repair_journal_sha256'):
            raise ValueError('Fresh authoritative chapter publication differs from frozen relocation')
        return candidates[0]

    @contextlib.contextmanager
    def operation_lease(self,publication_id):
        # The same lock every production interface uses. A live app refuses this
        # open before any queue, plan or output mutation; no PID inference.
        with catalog_lock(self.database,self.roots) as owner,catalog_identity_lease(self.database) as catalog_facts,DirectoryBoundary(self.plan_path.anchor,self.plan_path.parent),VerifiedFile(self.plan_path) as planfile:
            if not isinstance(owner,dict) or owner.get('held') is not True:raise ValueError('Native exclusive catalog owner unavailable')
            self.catalog_facts=catalog_facts
            plan=self._plan(planfile);self.plan=plan;entry=next((item for item in plan['publications'] if item.get('publication_id')==publication_id),None)
            if entry is None:raise ValueError('Publication is outside the exact reviewed plan')
            db=sqlite3.connect(self.database,timeout=10);db.row_factory=sqlite3.Row
            try:
                db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL')
                if str(db.execute('PRAGMA journal_mode').fetchone()[0]).lower() not in {'wal','delete','truncate','persist'}:raise ValueError('Catalog has no persistent journal')
                if db.execute("SELECT 1 FROM audio_jobs WHERE state='running' LIMIT 1").fetchone():raise ValueError('Drain running audiobook work through the app before migration')
                if db.execute("SELECT 1 FROM source_cleanup WHERE state IN ('checking','removing') LIMIT 1").fetchone():raise ValueError('Drain active source cleanup through the app before migration')
                selected=plan.get('verification_selection')
                if selected is not None:
                    known={item[0] for item in db.execute('SELECT id FROM book_groups WHERE superseded=0')}
                    if set(selected)-known:raise ValueError('Reviewed verification selection contains unknown current candidates')
                current,envelope=self._scope(db,entry);invocation=str(uuid.uuid4())
                native={'schema':'books-migration-native-owner-v1','invocation_id':invocation,'catalog_identity':self.worker._catalog_identity(),
                    'owner_handle_proof':json.loads(json.dumps(owner))}
                self.active=(db,publication_id,entry,current,native)
                def guard(identity,generation):
                    if identity!=publication_id or not db.in_transaction:return False
                    actual,_=self._scope(db,entry)
                    return actual['generation']==generation and self.worker._catalog_identity()==native['catalog_identity']
                def durable(connection):
                    if connection is not db:raise ValueError('Durability callback catalog changed')
                    db.commit();actual,_=self._scope(db,entry)
                    event=row(db,'SELECT * FROM migration_events WHERE publication_id=? ORDER BY event_id DESC LIMIT 1',(publication_id,))
                    return {'schema':'books-migration-durable-commit-v1','committed':not db.in_transaction,'publication_id':publication_id,
                        'generation':actual['generation'],'relocation_sha256':digest(actual),'event_sha256':digest(event),
                        'journal_mode':str(db.execute('PRAGMA journal_mode').fetchone()[0]).lower(),'synchronous':int(db.execute('PRAGMA synchronous').fetchone()[0]),'owner_invocation_id':invocation}
                yield {'db':db,'drained':True,'native_owner':native,'generation_guard':guard,'durable_commit':durable,'removal_closure':lambda intent:None}
            finally:
                self.active=None;db.rollback();db.close()

    def media_verify(self,path,receipt,stop):
        # The worker independently hashes native-held original AND destination;
        # this callback seals the supported historical media contract only.
        db,identity,entry,current,native=self.active
        current,envelope=self._scope(db,entry)
        if receipt!=json.loads(current['original_output_json']):raise ValueError('Original media receipt changed')
        validation=receipt.get('validation') or {}
        from encoding_policy import PROFILE,LEGACY_PROFILE,AUTOMATIC_PROFILE
        derived=current['publication_kind'] in {'Chapters','Chaptersv2'}
        if validation.get('sha256')!=receipt['sha256'] or validation.get('size')!=receipt['size'] or validation.get('profile') not in {PROFILE,LEGACY_PROFILE,AUTOMATIC_PROFILE}:
            raise ValueError('Historical media validation is not sealed to this exact output')
        if derived:
            authorized=self._authorized_chapter(db,current)
            if validation.get('checks')!='Audio copied without re-encoding; presentation and chapter checks passed' or not isinstance(validation.get('chapters'),list) or not validation.get('presentation') or not validation.get('chapter_format'):
                raise ValueError('Authoritative chapter validation contract is incomplete')
        elif validation.get('passed') is not True or validation.get('checks')!='Output checks passed':
            raise ValueError('Historical media validation is not sealed to this exact output')
        result={'kind':'sealed_media_proof_reused','supported_validation_contract':'books-authorized-chapter-output-v1' if derived else 'books-audio-output-v1','passed':True,
          'immutable_receipt_sha256':digest(receipt),'validation_sha256':digest(validation),'full_content_sha256':receipt['sha256'],'size':receipt['size'],
          'details':{'basis':'Exact original/output full SHA256 and size equality enforced by native worker; immutable supported production media validation reused','profile':validation['profile']}}
        if derived:result['authoritative_repair_journal_sha256']=authorized['journal_sha256']
        return result

    @staticmethod
    def invalidate(db,original,effective):
        if not db.in_transaction:raise ValueError('Location invalidation must share the commit transaction')
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='verified_outputs'").fetchone():
            paths=[os.path.normcase(str(ordinary(location['final_path']))) for location in (original,effective)]
            db.execute('DELETE FROM verified_outputs WHERE path IN (?,?)',paths)
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='owned_artifacts'").fetchone():
            db.execute('INSERT OR REPLACE INTO owned_artifacts VALUES(?,?,?,?,?)',(effective['final_path'],original['job_id'],'output',effective['sha256'],effective['size']))

    def run(self,publication_id):return self.worker.run(publication_id)

def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description='Run one exact reviewed publication under exclusive catalog ownership; never starts the app')
    parser.add_argument('--plan',required=True);parser.add_argument('--plan-sha',required=True)
    parser.add_argument('--publication',required=True);parser.add_argument('--mode',choices=('check','run'),default='check')
    args=parser.parse_args(argv);path=ordinary(args.plan)
    with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as file:
        if file.facts()['links']!=1 or file.facts()['size']>4*1024*1024:raise ValueError('Reviewed plan is not bounded unique data')
        raw=b''.join(file.chunks())
        if hashlib.sha256(raw).hexdigest()!=args.plan_sha:raise ValueError('Reviewed plan SHA256 differs')
        plan=json.loads(raw)
        if not isinstance(plan.get('roots'),dict) or not plan['roots']:raise ValueError('Reviewed source/output roots are required')
        operation=MigrationOperation(plan['database'],plan['roots'],path,args.plan_sha)
        if args.mode=='check':
            with operation.operation_lease(args.publication) as lease:
                current=row(lease['db'],'SELECT * FROM output_relocations WHERE publication_id=?',(args.publication,))
                result={'mode':'check','publication_id':args.publication,'stage':current['stage'],'generation':current['generation'],'native_owner_acquired':True,'outputs_changed':False}
        else:result=operation.run(args.publication)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=='__main__':raise SystemExit(main())
