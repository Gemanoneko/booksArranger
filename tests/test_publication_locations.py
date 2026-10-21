"""Pure relocation ledger tests; only one isolated hook performs native reads.

Synthetic proof dictionaries test structural rejection, never media clearance.
No application/catalog startup, live paths, publication or deletion occurs.
"""
import copy
import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path

import publication_locations as p

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'publication-locations'


def packed(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(packed(value).encode()).hexdigest()


class PublicationLocationsTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT,manifest_hash TEXT,journal TEXT,output TEXT,state TEXT)')
        self.root=str(AREA/'publication-fixture'/'old')
        self.target=str(AREA/'publication-fixture'/'sorted')
        self.original={'job_id':str(uuid.uuid4()),'root':self.root,'final_path':str(Path(self.root)/'Book.m4b'),
            'sha256':hashlib.sha256(b'owned tiny audio fixture').hexdigest(),'size':24,
            'parent_identity':[[self.root,1,0,1]],'validation':{'passed':True,'marker':'historical immutable receipt'}}
        self.job_id=self.original['job_id'];self.manifest={'job_id':self.job_id,'candidate_id':str(uuid.uuid4()),'candidate_revision':3,
            'root':self.root,'sources':[{'path':str(Path(self.root)/'input.mp3')}],
            'metadata_facts':{'source_fingerprint':'source-fingerprint'}}
        self.job={'job_id':self.job_id,'state':'completed','manifest':packed(self.manifest),'manifest_hash':digest(self.manifest),
            'journal':packed({'publication_intent':self.original}),'output':packed(self.original)}
        self.store_job();p.initialize(self.db)
        self.destination=str(Path(self.target)/'Book.m4b')
        self.routing={'routing_policy_version':'accepted-hierarchy-v1','source_fingerprint':'source-fingerprint'}

    def store_job(self):
        self.db.execute('INSERT OR REPLACE INTO audio_jobs(job_id,manifest,manifest_hash,journal,output,state) VALUES(?,?,?,?,?,?)',
            tuple(self.job[key] for key in ('job_id','manifest','manifest_hash','journal','output','state')))

    def plan(self,kind='base',receipt=None):
        return p.plan(self.db,self.job,kind,receipt or self.original,self.target,self.destination,self.routing)

    def completed_backfill(self):
        old=copy.deepcopy(self.original)
        old['validation'].update(sha256=old['sha256'],size=old['size'],tags={'title':'Book','album':'Book'})
        review={'title':'Book','series':'Series','number':'2'}
        record={'root':self.root,'old_path':old['final_path'],'old_sha256':old['sha256'],'old_size':old['size'],
            'new_path':str(Path(self.root)/'Series - 2 - Book.m4b'),'new_sha256':hashlib.sha256(b'retagged fixture').hexdigest(),'new_size':old['size']+1,
            'old_identity':[1,0,2],'new_identity':[1,0,3],'new_mtime':123456,'parent_identity':old['parent_identity'],
            'temp':str(Path(self.root)/('.books-arranger-series-'+self.job_id+'.m4b')),'removal_intended':True,
            'provider':'goodreads','source_url':'https://www.goodreads.com/book/show/fixture','series_proof':{},
            'research_receipts':[],'deferred_sources':[],'review':review,'series':'Series','number':'2'}
        self.original=copy.deepcopy(old)
        self.original.update(final_path=record['new_path'],sha256=record['new_sha256'],size=record['new_size'])
        self.original['validation'].update(sha256=record['new_sha256'],size=record['new_size'])
        self.original['validation']['tags'].update(album='Series - 2 - Book',grouping='Series')
        self.manifest.update(metadata=review,destination=record['new_path'])
        self.manifest['metadata_facts'].update(series_state='verified',series_source={'provider':record['provider'],'url':record['source_url'],'evidence':[],'deferred_sources':[]})
        self.job.update(manifest=packed(self.manifest),manifest_hash=digest(self.manifest),journal=packed({'publication_intent':old}),output=packed(self.original))
        self.store_job()
        self.db.execute('CREATE TABLE series_backfill(job_id TEXT PRIMARY KEY,state TEXT,reason TEXT,record TEXT)')
        self.db.execute('INSERT INTO series_backfill VALUES(?,?,?,?)',(self.job_id,'done','',packed(record)))
        return record,old

    def test_completed_backfill_pins_lineage_without_rewriting_original_intent(self):
        record,old=self.completed_backfill();before=self.job['journal']
        # The pre-0.18 Goodreads producer omitted this optional research field.
        record.pop('series_proof');self.db.execute('UPDATE series_backfill SET record=?',(packed(record),))
        result=self.plan();proof=json.loads(result['accepted_routing_json'])['completed_parent_lineage']
        self.assertEqual(proof['record_sha256'],digest(record));self.assertEqual(proof['original_intent_sha256'],digest(old))
        self.assertEqual(result['original_publication_intent_sha256'],digest(old));self.assertEqual(self.job['journal'],before)
        self.assertEqual(json.loads(result['original_output_json']),self.original)
        self.assertEqual(self.plan(),result)
        record['series_proof']={}
        self.db.execute('UPDATE series_backfill SET record=?',(packed(record),))
        with self.assertRaisesRegex(p.PublicationRefused,'lineage changed'):p.resolve(self.db,self.job,'base',self.original)

    def test_backfill_rejects_incomplete_stale_cross_job_and_multiple_lineage(self):
        record,old=self.completed_backfill()
        cases=[('old_sha256','0'*64),('new_sha256','0'*64),('old_size',old['size']+1),('new_size',self.original['size']+1),
            ('new_identity',record['old_identity']),('old_identity',[0,0,0]),('removal_intended',False),
            ('temp',str(Path(self.root)/'.books-arranger-series-other-job.m4b')),('old_path',record['new_path']),
            ('parent_identity',[[self.root,1,0,99]]),('review',dict(record['review'],number='3')),
            ('series_proof',None),('series_proof',[])]
        for key,value in cases:
            with self.subTest(key=key):
                changed=copy.deepcopy(record);changed[key]=value
                self.db.execute('UPDATE series_backfill SET record=?',(packed(changed),))
                with self.assertRaises(p.PublicationRefused):self.plan()
        self.db.execute('UPDATE series_backfill SET record=?,state=?',(packed(record),'cataloged'))
        with self.assertRaises(p.PublicationRefused):self.plan()

    def test_missing_research_annotation_is_not_allowed_for_new_provider_or_declared_proof(self):
        record,old=self.completed_backfill();record.pop('series_proof')
        for provider in ('wikidata','publisher','unknown'):
            with self.subTest(provider=provider):
                changed=dict(record,provider=provider)
                self.db.execute('UPDATE series_backfill SET record=?',(packed(changed),))
                with self.assertRaises(p.PublicationRefused):self.plan()
        self.db.execute('UPDATE series_backfill SET record=?',(packed(record),))
        self.manifest['metadata_facts']['series_source']['series_proof']={}
        self.job.update(manifest=packed(self.manifest),manifest_hash=digest(self.manifest));self.store_job()
        with self.assertRaisesRegex(p.PublicationRefused,'manifest-declared'):self.plan()

    def test_backfill_rejects_unexplained_receipt_change_and_missing_row(self):
        record,old=self.completed_backfill();self.original['validation']['marker']='not a retag'
        self.job['output']=packed(self.original);self.store_job()
        with self.assertRaisesRegex(p.PublicationRefused,'unexplained'):self.plan()
        self.db.execute('DELETE FROM series_backfill')
        with self.assertRaises(p.PublicationRefused):self.plan()

    def final_proof(self,row):
        location={'root':row['target_root'],'final_path':row['planned_destination'],'sha256':self.original['sha256'],
            'size':self.original['size'],'identity':getattr(self,'target_identity',[1,0,42]),'parent_identity':getattr(self,'target_parents',[[row['target_root'],1,0,41]])}
        intent=self.prior(row,'final_publish_intent')
        return {'schema':p.PROOF_SCHEMA,'publication_id':row['publication_id'],'immutable_receipt_sha256':row['immutable_receipt_sha256'],
            'generation':row['generation'],**copy.deepcopy(location),
            'final_publish_intent_sha256':digest(intent) if intent else None,
            'media_validation':{'passed':True,'full_content_sha256':self.original['sha256'],'size':self.original['size']},
            'final_publication':{'published':True,'no_replace':True,**copy.deepcopy(location)}}

    def prior(self,row,stage):
        result=self.db.execute("SELECT proof_json FROM migration_events WHERE publication_id=? AND to_stage=? AND outcome='transition' ORDER BY event_id DESC LIMIT 1",(row['publication_id'],stage)).fetchone()
        return json.loads(result[0]) if result else None

    def phase_proof(self,row,stage):
        common={'publication_id':row['publication_id'],'immutable_receipt_sha256':row['immutable_receipt_sha256'],'generation':row['generation']}
        temp={'root':row['target_root'],'temporary_path':str(Path(row['planned_destination']).with_name(row['publication_id']+'.owned-partial')),
              'parent_identity':copy.deepcopy(getattr(self,'target_parents',[[row['target_root'],1,0,41]]))}
        if stage=='copy_intent':return {**common,**temp,'schema':'books-output-copy-intent-v1','no_replace':True,'creation':'owned_exclusive_create','original_location':dict(copy.deepcopy(self.original),identity=[1,0,2])}
        if stage in {'copied','temporary_verified'}:
            result={**common,**temp,'schema':'books-output-temporary-proof-v1','identity':getattr(self,'target_identity',[1,0,42]),'sha256':self.original['sha256'],'size':self.original['size'],'flushed':True}
            if stage=='copied':result['copy_intent_sha256']=digest(self.prior(row,'copy_intent'))
            else:result.update(copied_proof_sha256=digest(self.prior(row,'copied')),media_validation={'passed':True,'full_content_sha256':self.original['sha256'],'size':self.original['size']})
            return result
        return {**common,**temp,'schema':'books-output-final-publish-intent-v1','final_path':row['planned_destination'],
                'temporary_identity':getattr(self,'target_identity',[1,0,42]),'no_replace':True,'temporary_verification_sha256':digest(self.prior(row,'temporary_verified'))}

    def removal_intent(self,row):
        return {'publication_id':row['publication_id'],'immutable_receipt_sha256':row['immutable_receipt_sha256'],'generation':row['generation'],
            'old_location':dict(copy.deepcopy(self.original),identity=[1,0,2]),
            'destination_verification_sha256':digest(json.loads(row['destination_verification_json']))}

    def next(self,row,stage):
        proof=None
        if stage in ('copy_intent','copied','temporary_verified','final_publish_intent'):proof=self.phase_proof(row,stage)
        if stage in {'final_published','location_committed'}:proof=self.final_proof(row)
        if stage=='old_removal_intent':proof=self.removal_intent(row)
        if stage=='original_removed':
            prior=self.db.execute("SELECT proof_json FROM migration_events WHERE publication_id=? AND to_stage='old_removal_intent' AND outcome='transition'",(row['publication_id'],)).fetchone()
            proof={'removal_intent_sha256':digest(json.loads(prior[0])),'original_removed':True,'native_owner_closed':True}
        if stage=='complete':proof={'outcome':'moved'}
        return p.transition(self.db,row['publication_id'],row['generation'],stage,proof)

    def advance(self,row,stage):
        while row['stage']!=stage:row=self.next(row,p.STAGES[p.STAGES.index(row['stage'])+1])
        return row

    def resolve(self,verify=None,kind='base',receipt=None):
        return p.resolve(self.db,self.job,kind,receipt or self.original,verify)

    def test_original_round_trip_has_no_implicit_verification(self):
        before=copy.deepcopy(self.original);result=self.resolve()
        self.assertFalse(result['verified']);self.assertEqual(result['stage'],'original');self.assertIsNone(result['generation'])
        self.assertEqual(result['original_receipt'],before);self.assertEqual(result['effective_location']['final_path'],before['final_path'])
        result['original_receipt']['validation']['marker']='changed';self.assertEqual(self.original,before)

    def test_initialize_does_not_commit_enclosing_transaction(self):
        self.db.commit();self.db.execute('BEGIN');self.db.execute('UPDATE audio_jobs SET manifest_hash=?',('a'*64,))
        p.initialize(self.db);self.db.rollback()
        self.assertEqual(self.db.execute('SELECT manifest_hash FROM audio_jobs').fetchone()[0],self.job['manifest_hash'])

    def test_existing_incomplete_schema_is_refused_without_repair(self):
        db=sqlite3.connect(':memory:');self.addCleanup(db.close)
        db.execute('CREATE TABLE output_relocations(planned_destination TEXT)')
        with self.assertRaises(p.PublicationRefused):p.initialize(db)
        self.assertEqual([row[1] for row in db.execute('PRAGMA table_info(output_relocations)')],['planned_destination'])

    def test_three_publications_same_job_have_distinct_stable_ids_and_rows(self):
        identities=[]
        for kind in ('base','Chapters','Chaptersv2'):
            receipt=copy.deepcopy(self.original)
            if kind!='base':receipt.update(job_id=str(uuid.uuid4()),final_path=str(Path(self.root)/(kind+'.m4b')))
            first=p.publication_id(self.job_id,kind,receipt);self.assertEqual(first,p.publication_id(self.job_id,kind,json.loads(packed(receipt))))
            self.plan(kind,receipt);identities.append(first)
        self.assertEqual(len(set(identities)),3);self.assertEqual(self.db.execute('SELECT count(*) FROM output_relocations').fetchone()[0],3)

    def test_replacement_kind_has_its_own_identity(self):
        self.assertNotEqual(self.plan()['publication_id'],self.plan('replacement')['publication_id'])

    def test_plan_idempotent_but_changed_route_refused(self):
        first=self.plan();self.assertEqual(self.plan(),first)
        with self.assertRaises(p.PublicationRefused):p.plan(self.db,self.job,'base',self.original,self.target,str(Path(self.target)/'Other.m4b'),self.routing)
        self.assertEqual(self.db.execute('SELECT count(*) FROM migration_events').fetchone()[0],1)

    def test_every_crash_stage_resolves_original_until_location_commit(self):
        row=self.plan()
        for stage in p.STAGES:
            if stage!='planned':row=self.next(row,stage)
            envelope=self.resolve();self.assertEqual(envelope['stage'],stage);self.assertEqual(envelope['generation'],row['generation'])
            self.assertEqual(envelope['effective_location']['final_path'],self.destination if stage in p.COMMITTED else self.original['final_path'])
            self.assertEqual(envelope['original_receipt'],self.original);self.assertFalse(envelope['verified'])

    def test_stale_cas_has_no_state_change_and_appends_refusal(self):
        row=self.plan();self.next(row,'copy_intent')
        with self.assertRaises(p.PublicationRefused) as error:p.transition(self.db,row['publication_id'],0,'copy_intent')
        self.assertEqual(error.exception.code,'relocation_generation_changed');self.assertEqual(self.resolve()['stage'],'copy_intent')
        self.assertEqual(self.db.execute("SELECT count(*) FROM migration_events WHERE outcome='refusal'").fetchone()[0],1)

    def test_illegal_skip_cannot_commit_or_remove_original(self):
        row=self.plan()
        for target in ('location_committed','old_removal_intent','original_removed','complete'):
            with self.subTest(target=target),self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],0,target,self.final_proof(row))
        self.assertEqual(self.resolve()['stage'],'planned')

    def test_every_early_phase_requires_its_complete_bound_proof(self):
        row=self.plan()
        for stage in p.STAGES[1:7]:
            for proof in (None,{}):
                with self.subTest(stage=stage,proof=proof),self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],stage,proof)
            row=self.next(row,stage)

    def test_phase_proofs_reject_replaced_temporary_or_no_replace_drift(self):
        row=self.plan();intent=self.phase_proof(row,'copy_intent')
        with self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'copy_intent',intent|{'no_replace':False})
        row=self.next(row,'copy_intent');copied=self.phase_proof(row,'copied')
        with self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'copied',copied|{'copy_intent_sha256':'f'*64})
        row=self.next(row,'copied');verified=self.phase_proof(row,'temporary_verified')
        with self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'temporary_verified',verified|{'identity':[1,0,999]})
        row=self.next(row,'temporary_verified');final=self.phase_proof(row,'final_publish_intent')
        with self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'final_publish_intent',final|{'temporary_identity':[1,0,999]})
        row=self.next(row,'final_publish_intent');published=self.final_proof(row)
        with self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'final_published',published|{'final_publish_intent_sha256':'f'*64})

    def test_history_revalidates_early_structural_claims_after_restart(self):
        row=self.plan()
        self.db.execute("INSERT INTO migration_events(migration_id,publication_id,generation,from_stage,to_stage,outcome,proof_json,error,created_utc) VALUES(?,?,1,'planned','copy_intent','transition','{}',NULL,'synthetic crash')",(row['migration_id'],row['publication_id']))
        self.db.execute("UPDATE output_relocations SET stage='copy_intent',generation=1 WHERE publication_id=?",(row['publication_id'],))
        with self.assertRaises(p.PublicationRefused):self.resolve()

    def test_unfinished_parent_cannot_enter_any_publication_kind(self):
        for state in ('queued','running','needs attention','paused'):
            self.job['state']=state;self.store_job()
            for kind in ('base','Chapters','Chaptersv2','replacement'):
                with self.subTest(state=state,kind=kind),self.assertRaises(p.PublicationRefused) as error:self.plan(kind)
                self.assertEqual(error.exception.code,'publication_not_completed')
        self.assertEqual(self.db.execute('SELECT count(*) FROM output_relocations').fetchone()[0],0)

    def test_completed_label_cannot_replace_passing_parent_publication_proof(self):
        bad=self.original|{'validation':{'passed':False}}
        self.job.update(output=packed(bad),journal=packed({'publication_intent':bad}));self.store_job()
        for kind in ('base','Chapters','replacement'):
            with self.subTest(kind=kind),self.assertRaises(p.PublicationRefused):self.plan(kind,bad)

    def test_final_temp_proof_cannot_stand_in_for_final_destination(self):
        row=self.advance(self.plan(),'final_publish_intent');proof=self.final_proof(row);proof['final_path']=str(Path(self.target)/'private.partial')
        with self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'final_published',proof)
        self.assertEqual(self.resolve()['effective_location']['final_path'],self.original['final_path'])

    def test_incomplete_or_wrong_final_proofs_refused(self):
        row=self.advance(self.plan(),'final_publish_intent')
        for change in ({'sha256':'f'*64},{'size':25},{'identity':[0,0,0]},{'parent_identity':[]},{'generation':0},{'final_publication':{'published':False}},
                       {'media_validation':{'passed':True,'full_content_sha256':'f'*64,'size':24}}):
            with self.subTest(change=change),self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'final_published',self.final_proof(row)|change)

    def test_final_commit_requires_fresh_generation_and_same_native_publication(self):
        row=self.advance(self.plan(),'final_published');proof=self.final_proof(row)
        for change in ({'generation':row['generation']-1},{'identity':[1,0,999]}):
            with self.subTest(change=change),self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'location_committed',proof|change)
        self.next(row,'location_committed');self.assertEqual(self.resolve()['effective_location']['final_path'],self.destination)

    def test_retained_original_outcome_explicit_and_postcommit_only(self):
        row=self.advance(self.plan(),'location_committed')
        for proof in (None,{'outcome':'moved'},{'outcome':'copied_verified_original_retained','reason':''}):
            with self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'complete',proof)
        result=p.transition(self.db,row['publication_id'],row['generation'],'complete',{'outcome':'copied_verified_original_retained','reason':'Old output remains open'})
        self.assertEqual(result['stage'],'complete');self.assertFalse(self.resolve()['verified'])
        self.assertEqual(result['last_error'],'Old output remains open')
        self.assertEqual(self.resolve()['outcome'],'copied_verified_original_retained')

    def test_removal_requires_original_identity_and_exact_precommitted_intent(self):
        row=self.advance(self.plan(),'location_committed')
        with self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'old_removal_intent',{'old_location':self.original})
        row=self.next(row,'old_removal_intent')
        for proof in ({'original_removed':True,'native_owner_closed':True,'removal_intent_sha256':'f'*64},
                      {'original_removed':True,'native_owner_closed':False}):
            with self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'original_removed',proof)
        self.next(row,'original_removed')

    def test_mutated_receipt_cannot_satisfy_original_base_guard(self):
        self.advance(self.plan(),'location_committed');changed=self.original|{'final_path':self.destination,'root':self.target,'parent_identity':[[self.target,1,0,41]]}
        with self.assertRaises(p.PublicationRefused):self.resolve(receipt=changed)

    def test_unknown_derived_receipt_cannot_bypass_an_existing_kind_binding(self):
        receipt=self.original|{'final_path':str(Path(self.root)/'Chapters.m4b')};self.plan('Chapters',receipt)
        with self.assertRaises(p.PublicationRefused) as error:self.resolve(kind='Chapters',receipt=receipt|{'sha256':'f'*64})
        self.assertEqual(error.exception.code,'immutable_receipt_mismatch')

    def test_job_manifest_and_candidate_drift_refused(self):
        self.plan();changed=copy.deepcopy(self.manifest);changed['candidate_revision']+=1
        self.job['manifest']=packed(changed);self.job['manifest_hash']=digest(changed);self.store_job()
        with self.assertRaises(p.PublicationRefused):self.resolve()

    def test_tampered_binding_cannot_retarget_even_before_commit(self):
        row=self.plan();self.db.execute('UPDATE output_relocations SET planned_destination=?',(str(Path(self.target)/'Other.m4b'),))
        with self.assertRaises(p.PublicationRefused):self.resolve()
        with self.assertRaises(p.PublicationRefused):self.next(row,'copy_intent')

    def test_committed_binding_missing_or_malformed_proof_has_no_old_path_fallback(self):
        self.advance(self.plan(),'location_committed')
        for value in (None,'{}','not-json'):
            self.db.execute('UPDATE output_relocations SET destination_verification_json=?',(value,))
            with self.subTest(value=value),self.assertRaises(p.PublicationRefused):self.resolve()

    def test_offline_or_rejected_native_verifier_is_typed_and_no_fallback(self):
        self.advance(self.plan(),'location_committed')
        def offline(location,envelope):raise OSError('Private destination unavailable')
        for callback in (offline,lambda location,envelope:False,lambda location,envelope:1):
            with self.assertRaises(p.PublicationRefused) as error:self.resolve(callback)
            self.assertEqual(error.exception.code,'relocated_output_unavailable')
        self.assertEqual(self.resolve()['effective_location']['final_path'],self.destination)

    def test_pending_offline_is_typed_original_unavailable(self):
        self.plan()
        with self.assertRaises(p.PublicationRefused) as error:self.resolve(lambda location,envelope:False)
        self.assertEqual(error.exception.code,'original_output_unavailable')

    def test_append_only_events_cannot_be_edited_or_deleted(self):
        self.plan()
        for command in ('UPDATE migration_events SET generation=99','DELETE FROM migration_events'):
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(command)

    def test_all_inputs_remain_immutable_and_no_filesystem_module_is_called(self):
        before=copy.deepcopy((self.job,self.original,self.routing));row=self.plan();self.advance(row,'location_committed');self.resolve()
        self.assertEqual((self.job,self.original,self.routing),before)
        self.assertNotIn('os',vars(p));self.assertNotIn('pathlib',vars(p));self.assertNotIn('native_io',vars(p))

    def test_invalid_path_and_source_routing_inputs_refused(self):
        for target in ('relative.m4b',str(Path(self.target)/'..'/'escape.m4b'),str(Path(self.target)/'Book.m4b:private'),str(Path(self.target)/'NUL.m4b')):
            with self.subTest(target=target),self.assertRaises(p.PublicationRefused):p.plan(self.db,self.job,'base',self.original,self.target,target,self.routing)
        with self.assertRaises(p.PublicationRefused):p.plan(self.db,self.job,'base',self.original,self.target,self.destination,self.routing|{'source_fingerprint':'other-source'})

    def test_parser_works_with_dictionary_sqlite_rows(self):
        self.db.row_factory=sqlite3.Row;self.plan();self.assertEqual(self.resolve()['stage'],'planned')

    def test_real_isolated_native_hook_verifies_hash_identity_and_detects_generation_drift(self):
        from native_io import DirectoryBoundary,VerifiedFile
        AREA.mkdir(parents=True,exist_ok=True)
        directory=Path(tempfile.mkdtemp(prefix='publication-native-',dir=AREA));old=directory/'old';new=directory/'sorted';old.mkdir();new.mkdir()
        source=old/'Book.m4b';destination=new/'Book.m4b';raw=b'owned synthetic native-read fixture';source.write_bytes(raw);destination.write_bytes(raw)
        # This is deliberately not media clearance. The hook demonstrates exact
        # private native identity/hash validation only; production adds media.
        with DirectoryBoundary(old,source.parent) as boundary,VerifiedFile(source) as file:
            original=self.original|{'root':str(old),'final_path':str(source),'size':len(raw),'sha256':file.sha256(),'parent_identity':boundary.identities}
        self.original=json.loads(packed(original));self.job['output']=packed(self.original);self.job['journal']=packed({'publication_intent':self.original});self.store_job()
        self.target=str(new);self.destination=str(destination)
        with DirectoryBoundary(new,destination.parent) as boundary,VerifiedFile(destination) as file:
            self.target_identity=file.facts()['identity'];self.target_parents=json.loads(packed(boundary.identities))
        row=self.advance(self.plan(),'final_publish_intent')
        with DirectoryBoundary(new,destination.parent) as boundary,VerifiedFile(destination) as file:
            proof=self.final_proof(row);proof.update(identity=file.facts()['identity'],parent_identity=json.loads(packed(boundary.identities)))
            proof['final_publication'].update(identity=proof['identity'],parent_identity=proof['parent_identity'])
        row=p.transition(self.db,row['publication_id'],row['generation'],'final_published',proof)
        proof['generation']=row['generation'];row=p.transition(self.db,row['publication_id'],row['generation'],'location_committed',proof)
        def verify(location,envelope):
            with DirectoryBoundary(location['root'],Path(location['final_path']).parent) as boundary,VerifiedFile(location['final_path']) as file:
                return file.facts()['identity']==location['identity'] and file.facts()['size']==location['size'] and file.sha256()==location['sha256'] and json.loads(packed(boundary.identities))==location['parent_identity']
        self.assertTrue(self.resolve(verify)['verified']);self.assertEqual(source.read_bytes(),raw)
        def drift(location,envelope):
            accepted=verify(location,envelope)
            p.transition(self.db,row['publication_id'],row['generation'],'complete',{'outcome':'copied_verified_original_retained','reason':'Isolated generation race'})
            return accepted
        with self.assertRaises(p.PublicationRefused) as error:self.resolve(drift)
        self.assertEqual(error.exception.code,'relocation_generation_changed');self.assertEqual(source.read_bytes(),raw);self.assertEqual(destination.read_bytes(),raw)


class NativeMoveLedger(unittest.TestCase):
    setUp=PublicationLocationsTests.setUp
    store_job=PublicationLocationsTests.store_job
    plan=PublicationLocationsTests.plan
    resolve=PublicationLocationsTests.resolve
    advance=PublicationLocationsTests.advance
    next=PublicationLocationsTests.next
    phase_proof=PublicationLocationsTests.phase_proof
    final_proof=PublicationLocationsTests.final_proof
    prior=PublicationLocationsTests.prior
    removal_intent=PublicationLocationsTests.removal_intent

    def claim(self,row,schema,strategy=p.RENAME_STRATEGY):
        return {'schema':schema,'strategy':strategy,'publication_id':row['publication_id'],
            'immutable_receipt_sha256':row['immutable_receipt_sha256'],'generation':row['generation'],
            'frozen_binding_sha256':digest(p._frozen(row)),'operation_plan_sha256':'a'*64}

    def intent(self,row,strategy=p.RENAME_STRATEGY):
        native={'identity':[1,0,2],'dev':1,'ino':2,'modified':1,'size':self.original['size'],'links':1,'attributes':32}
        source=dict(copy.deepcopy(self.original),identity=native['identity'],native=native,content_basis={'kind':'fresh_full_held_hash'})
        proof=dict(self.claim(row,'books-output-native-move-intent-v1',strategy),original_location=source,
            target={'root':row['target_root'],'final_path':row['planned_destination'],'parent_identity':[[row['target_root'],1,0,41]]},no_replace=True,copy_fallback=False)
        if strategy==p.DUPLICATE_STRATEGY:
            final=json.loads(row['destination_verification_json'])
            proof['destination_location']={k:copy.deepcopy(final[k]) for k in ('root','final_path','sha256','size','identity','parent_identity')}
            proof['destination_location']['content_basis']={'kind':'fresh_full_held_hash'}
        return proof

    def rename_final(self,row):
        target={'root':row['target_root'],'final_path':row['planned_destination'],'sha256':self.original['sha256'],
            'size':self.original['size'],'identity':[1,0,2],'parent_identity':[[row['target_root'],1,0,41]]}
        return dict(schema=p.PROOF_SCHEMA,publication_id=row['publication_id'],immutable_receipt_sha256=row['immutable_receipt_sha256'],
            generation=row['generation'],**target,media_validation={'passed':True,'full_content_sha256':self.original['sha256'],'size':self.original['size']},
            final_publication=dict(target,published=True,no_replace=True,copy_fallback=False))

    def renamed(self):
        row=self.plan();intent=self.intent(row);row=p.move_transition(self.db,row['publication_id'],row['generation'],'rename_intent',intent)
        final=self.rename_final(row)
        proof=dict(self.claim(row,'books-output-native-renamed-v1'),intent_sha256=digest(intent),old_absent=True,final=final)
        return p.move_transition(self.db,row['publication_id'],row['generation'],'renamed',proof),intent,final

    def test_rename_history_commits_same_file_without_copy_stages(self):
        before=copy.deepcopy(self.job);row,intent,final=self.renamed()
        self.assertEqual(self.resolve()['effective_location']['final_path'],self.original['final_path'])
        final=dict(final,generation=row['generation'])
        row=p.move_transition(self.db,row['publication_id'],row['generation'],'location_committed',dict(self.claim(row,'books-output-native-move-commit-v1'),intent_sha256=digest(intent),final=final))
        row=p.move_transition(self.db,row['publication_id'],row['generation'],'complete',dict(self.claim(row,'books-output-native-move-complete-v1'),intent_sha256=digest(intent),outcome='moved'))
        result=self.resolve();self.assertEqual(result['effective_location']['final_path'],self.destination);self.assertEqual(result['outcome'],'moved')
        self.assertEqual(self.job,before);self.assertEqual([v[0] for v in self.db.execute('SELECT to_stage FROM migration_events')],['planned','rename_intent','renamed','location_committed','complete'])

    def test_rename_refuses_copy_fallback_cross_volume_and_alias(self):
        row=self.plan()
        for change in ('fallback','volume','hardlink'):
            proof=self.intent(row)
            if change=='fallback':proof['copy_fallback']=True
            if change=='volume':proof['target']['parent_identity'][0][1]=2
            if change=='hardlink':proof['original_location']['native']['links']=2
            with self.subTest(change=change),self.assertRaises(p.PublicationRefused):p.move_transition(self.db,row['publication_id'],0,'rename_intent',proof)
        self.assertEqual(self.resolve()['stage'],'planned')

    def test_copy_transition_cannot_consume_rename_intent(self):
        row=self.plan();row=p.move_transition(self.db,row['publication_id'],0,'rename_intent',self.intent(row))
        with self.assertRaises(p.PublicationRefused):p.transition(self.db,row['publication_id'],row['generation'],'copied',{})
        self.assertEqual(self.resolve()['stage'],'rename_intent')

    def test_rename_wrong_same_hash_destination_identity_refused(self):
        row=self.plan();intent=self.intent(row);row=p.move_transition(self.db,row['publication_id'],0,'rename_intent',intent)
        final=self.rename_final(row);final['identity']=[1,0,999];final['final_publication']['identity']=[1,0,999]
        with self.assertRaises(p.PublicationRefused):p.move_transition(self.db,row['publication_id'],1,'renamed',dict(self.claim(row,'books-output-native-renamed-v1'),intent_sha256=digest(intent),old_absent=True,final=final))

    def test_cache_authority_must_match_exact_native_identity(self):
        row=self.plan();proof=self.intent(row)
        proof['original_location']['content_basis']={'kind':'accepted_persisted_verification_cache','identity':[1,2,self.original['size'],1],'cache_record_sha256':'b'*64}
        bad=copy.deepcopy(proof);bad['original_location']['content_basis']['identity'][1]=999
        with self.assertRaises(p.PublicationRefused):p.move_transition(self.db,row['publication_id'],0,'rename_intent',bad)
        p.move_transition(self.db,row['publication_id'],0,'rename_intent',proof)
        self.assertEqual(self.resolve()['stage'],'rename_intent')
        self.assertEqual(p.STAGES[1],'copy_intent')

    def test_explicit_duplicate_cleanup_preserves_retained_copy_prefix(self):
        row=self.advance(self.plan(),'location_committed')
        row=p.transition(self.db,row['publication_id'],row['generation'],'complete',{'outcome':'copied_verified_original_retained','reason':'NAS parent flush unsupported'})
        prefix=[tuple(v) for v in self.db.execute('SELECT * FROM migration_events')]
        intent=self.intent(row,p.DUPLICATE_STRATEGY)
        row=p.move_transition(self.db,row['publication_id'],row['generation'],'duplicate_cleanup_intent',intent)
        proof=dict(self.claim(row,'books-output-duplicate-removed-v1',p.DUPLICATE_STRATEGY),intent_sha256=digest(intent),old_absent=True,
            destination_location=intent['destination_location'],basis='intent_bound_absence_with_verified_destination')
        row=p.move_transition(self.db,row['publication_id'],row['generation'],'duplicate_removed',proof)
        row=p.move_transition(self.db,row['publication_id'],row['generation'],'complete',dict(self.claim(row,'books-output-native-move-complete-v1',p.DUPLICATE_STRATEGY),intent_sha256=digest(intent),outcome='moved'))
        self.assertEqual(self.resolve()['outcome'],'moved');self.assertEqual([tuple(v) for v in self.db.execute('SELECT * FROM migration_events')][:len(prefix)],prefix)


if __name__=='__main__':unittest.main()
