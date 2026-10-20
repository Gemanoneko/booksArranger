"""Enroll only current Ready publications under an already exclusive catalog owner.

Native media copying belongs to the per-publication worker. This planner never
starts the app, scans, resets jobs, changes reviews/settings or edits receipts.
"""
import copy
import hashlib
import time
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
from catalog_owner import ACTIVE_CATALOG
from scanner import connect
import groups
from metadata import propose
from review_backend import member_key
from conversion_progress import approved_scope,completed_book
from encoding_policy import PROFILE,AUTOMATIC_PROFILE
from source_config import normalize_sources
from replacement_jobs import Replacements
from current_audiobook import CurrentAudiobooks
from publication_binding import PublicationBindings
from migration_operation import PLAN_SCHEMA,policy_roots,catalog_identity_lease
from organization import frozen_plan,POLICY
import publication_locations as locations

class VerificationDeferred(ValueError):pass

def _completed_census(candidates,jobs,set_aside=()):
    """Current completed candidates, independently of review/Ready eligibility."""
    identities=[row['id'] for row in candidates]
    if len(set(identities))!=len(identities):raise ValueError('Duplicate current candidate in completeness census')
    current=set(identities);excluded=set(set_aside);latest={}
    for job in jobs:
        identity=job['manifest'].get('candidate_id')
        if identity not in current or job['job_id'] in excluded:continue
        previous=latest.get(identity)
        if previous is None or (job['created'],job['job_id'])>(previous['created'],previous['job_id']):latest[identity]=job
    return [{'candidate_id':identity,'completed_job_id':job['job_id'],'manifest_hash':job['manifest_hash']}
            for identity,job in sorted(latest.items()) if job['state']=='completed']

def _completeness_receipt(census,outcomes):
    """Require exactly one explicit disposition per independently counted book."""
    expected={row['candidate_id']:row for row in census}
    if len(expected)!=len(census):raise ValueError('Duplicate completed candidate in completeness census')
    accounted={}
    for outcome in outcomes:
        identity=outcome.get('candidate_id')
        if identity not in expected:raise ValueError('Unknown completed candidate outcome')
        if identity in accounted:raise ValueError('Duplicate completed candidate outcome')
        if outcome.get('outcome') not in {'enrolled','already_at_destination','held','verification_deferred'} or not isinstance(outcome.get('reason'),str) or not outcome['reason'].strip():
            raise ValueError('Explicit completed candidate outcome and reason required')
        accounted[identity]=dict(outcome)
    if set(accounted)!=set(expected):raise ValueError('Missing completed candidate outcome')
    return {'schema':'books-completed-candidate-accounting-v1','census':copy.deepcopy(census),
            'outcomes':[accounted[identity] for identity in sorted(accounted)],'completed_candidates':len(census),'accounted_candidates':len(accounted)}

def _prepare(database,roots,audiobook_sources,output_root,decisions=(),verification_candidates=None):
    database=Path(database).absolute()
    if ACTIVE_CATALOG.get()!=str(database):raise ValueError('Acquire the real exclusive catalog owner before final migration planning')
    config=normalize_sources(roots,audiobook_sources,output_root)
    if not config.audiobook_output_root:raise ValueError('An explicit reviewed destination root is required')
    target=Path(config.audiobook_output_root)
    if not target.is_dir():raise ValueError('Connect the reviewed destination directory')
    decision_by={}
    for decision in decisions:
        if not isinstance(decision,dict) or decision.get('actor')!='user' or not decision.get('evidence') or decision.get('candidate_id') in decision_by:raise ValueError('Explicit unique user routing evidence is required')
        if set(decision.get('values',{}))-{'universe','multi_author'}:raise ValueError('Routing decision cannot replace canonical identity')
        decision_by[decision['candidate_id']]=copy.deepcopy(decision)
    bindings=PublicationBindings(database);replacements=Replacements(database)
    publications=CurrentAudiobooks(tuple(config.audiobook_sources)+(config.audiobook_output_root,),database.parent/'chapter-repairs',replacements,bindings=bindings)
    deadline=time.monotonic()+540;verified_missing=0;approved_count=0;not_approved=0;context_unavailable=0
    enrolled=[];pending=[];held=[];already=[];seen={};collisions=set();bytes_required=0;variant_counts={}
    with connect(database) as db:
        db.execute('PRAGMA synchronous=FULL');locations.initialize(db)
        rawjobs=[dict(row) for row in db.execute('SELECT * FROM audio_jobs ORDER BY updated')]
        if any(row['state']=='running' for row in rawjobs):raise ValueError('Drain running jobs before final planning')
        jobs=[dict(row,manifest=json.loads(row['manifest']),output=json.loads(row['output']) if row['output'] else None) for row in rawjobs]
        raw_by={row['job_id']:row for row in rawjobs}
        candidates=[dict(row) for row in db.execute('SELECT * FROM book_groups WHERE root IN (SELECT value FROM json_each(?)) AND superseded=0',(json.dumps(list(config.audiobook_sources)),))]
        if verification_candidates is not None:
            if not isinstance(verification_candidates,(list,tuple)) or len(verification_candidates)>10000 or any(not isinstance(value,str) for value in verification_candidates):raise ValueError('Expected bounded explicit verification candidate IDs')
            selected=set(verification_candidates)
            if selected-{row['id'] for row in candidates}:raise ValueError('Unknown current verification candidate ID')
        else:selected=None
        set_aside=[row[0] for row in db.execute('SELECT job_id FROM audio_job_set_aside')] if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audio_job_set_aside'").fetchone() else []
        completed_census=_completed_census(candidates,jobs,set_aside)
        completed_ids={row['candidate_id'] for row in completed_census}
        contexts={row['id']:dict(row) for row in db.execute('SELECT * FROM candidate_context')}
        retired={root:groups.retired_sources(db,root) for root in config.audiobook_sources}
        for saved in candidates:
            identity=saved['id'];context=contexts.get(identity)
            if not context or context['revision']!=saved['revision']:
                context_unavailable+=1
                held.append({'candidate_id':identity,'reason':'Current review context is missing or revision differs'});continue
            ctx=json.loads(context['data'])
            if not ctx.get('metadata_approved'):
                not_approved+=1
                if identity in completed_ids:held.append({'candidate_id':identity,'hold_type':'current_review_unapproved','reason':'Completed candidate current metadata approval is absent; publication retained'})
                continue
            approved_count+=1
            try:
                book=groups.render(saved,saved['root'],True,retired[saved['root']]);review=book['review']
                preview_root=config.audiobook_output_root if review.get('organization_policy')==POLICY else saved['root']
                book['preview']=propose(book['members'][0]['path'],preview_root,'audiobook',book['metadata'],review,automatic_facts=ctx.get('metadata_facts'))
                if not approved_scope(book,ctx,member_key):
                    held.append({'candidate_id':identity,'reason':'Approved book is not Ready: current source membership/order/review approval scope does not match'});continue
                publication=publications.publication(jobs,identity)
                if publication is None:
                    held.append({'candidate_id':identity,'reason':'Approved book has no current completed publication'});continue
                original=copy.deepcopy(publication['record']);parent=publication['parent'];raw=raw_by[parent['job_id']]
                kind='replacement' if publication['kind']=='replacement' else ('Chaptersv2' if publication.get('corrected') else 'Chapters') if publication['kind']=='chapter_update' else 'base'
                variant_counts[kind]=variant_counts.get(kind,0)+1
                # No reservation held while writing the enrollment transaction.
                # The outer exclusive native owner prevents another interface.
                newly_verified=False
                with publications.protected(publication) as (held_file,_):
                    effective=publication['record'];envelope=publication.get('location_envelope')
                    path=Path(effective['final_path']);stat=path.stat()
                    known=db.execute('SELECT identity FROM verified_outputs WHERE path=? AND sha256=?',(os.path.normcase(str(path)),effective['sha256'])).fetchone()
                    current=bool(known) and json.loads(known[0])==[stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns]
                    if not current:
                        if selected is not None and identity not in selected:raise VerificationDeferred('Current '+kind+' publication has no cached verification and was not selected for this bounded preflight pass; original retained')
                        full=hashlib.sha256()
                        for block in held_file.chunks():
                            if time.monotonic()>deadline:raise VerificationDeferred('Current '+kind+' publication has no cached verification and bounded full-hash preflight exhausted; original retained. Replanning reuses completed verifications only. If this file alone exceeds the bound, it remains held pending source-throughput correction or separately reviewed bounded per-file verification')
                            full.update(block)
                        if full.hexdigest()!=effective['sha256']:raise ValueError('Current '+kind+' publication full bytes differ from immutable receipt; original retained')
                        current=True;verified_missing+=1;newly_verified=True
                if newly_verified:
                    db.execute('INSERT OR REPLACE INTO verified_outputs VALUES(?,?,?,?,?)',(os.path.normcase(str(path)),effective['sha256'],parent['job_id'],json.dumps([stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns]),datetime.now(timezone.utc).isoformat()))
                    db.commit()
                source=db.execute('SELECT * FROM source_cleanup WHERE job_id=?',(parent['job_id'],)).fetchone()
                storage=db.execute('SELECT * FROM storage_cleanup_jobs WHERE job_id=?',(parent['job_id'],)).fetchone()
                relation=publication.get('relation')
                eligibility_book=book
                if parent['manifest'].get('metadata')==review and parent['manifest'].get('candidate_revision')==book['revision']:
                    eligibility_book=dict(book,preview={'path':parent['manifest']['destination']})
                if not completed_book(eligibility_book,ctx,parent,dict(source) if source else None,dict(storage) if storage else None,None,current,member_key,{PROFILE,AUTOMATIC_PROFILE},relation,location_envelope=envelope):
                    held.append({'candidate_id':identity,'kind':kind,'reason':'Current publication is not Ready: frozen metadata/source/cover or completed cleanup scope no longer matches'});continue
                routing_review=copy.deepcopy(review);evidence=[]
                decision=decision_by.get(identity)
                if decision:
                    if decision.get('fingerprint')!=book['fingerprint'] or decision.get('review_sha256')!=locations._digest(review):raise ValueError('Explicit routing decision source/review snapshot changed')
                    routing_review.update(decision['values']);evidence.append(decision)
                if parent['manifest'].get('metadata_facts',{}).get('destination_suffix') and parent['manifest'].get('metadata_facts')!=ctx.get('metadata_facts'):raise ValueError('Current recording distinction evidence differs from frozen publication')
                route=frozen_plan(parent['manifest'],config.audiobook_output_root,routing_review);destination=route['path'];key=os.path.normcase(destination)
                if key in seen and seen[key]!=identity:collisions.add(key)
                seen[key]=identity
                if os.path.normcase(str(path))==key:
                    already.append({'candidate_id':identity,'path':str(path),'size':effective['size']});continue
                pubid=locations.publication_id(parent['job_id'],kind,original)
                existing=db.execute('SELECT * FROM output_relocations WHERE publication_id=?',(pubid,)).fetchone()
                if Path(destination).exists() and not existing:raise ValueError('Unowned destination collision; preserve both')
                routing={'routing_policy_version':POLICY,'source_fingerprint':book['fingerprint'],'accepted_candidate_revision':book['revision'],
                    'accepted_review_sha256':locations._digest(review),'routing_review':routing_review,'user_routing_evidence':evidence}
                if parent['manifest'].get('metadata_facts',{}).get('destination_suffix'):routing['recording_facts_sha256']=locations._digest(parent['manifest']['metadata_facts'])
                if publication.get('journal_sha256'):routing['repair_journal_sha256']=publication['journal_sha256']
                pending.append({'raw':raw,'kind':kind,'original':original,'destination':destination,'routing':routing,'identity':identity,'journal':publication.get('journal'),'journal_sha256':publication.get('journal_sha256')})
            except (ValueError,OSError,KeyError) as error:held.append({'candidate_id':identity,'hold_type':'verification_deferred' if isinstance(error,VerificationDeferred) else 'scope_or_native_proof_refused','reason':str(error)})
        valid=[]
        for item in pending:
            if os.path.normcase(item['destination']) in collisions:held.append({'candidate_id':item['identity'],'reason':'Reviewed destination collides with another current book; all colliding publications retained'})
            else:valid.append(item)
        bytes_required=sum(item['original']['size'] for item in valid)
        free=shutil.disk_usage(target).free
        if bytes_required+1024*1024*1024>free:raise ValueError('Insufficient destination space for verified second copies plus reserve; no publication enrolled')
        db.execute('BEGIN IMMEDIATE')
        for item in valid:
            if item['journal']:
                rows,sha,facts,ancestry=publications._read_journal(publications.repairs,Path(item['journal']))
                if sha!=item['journal_sha256']:raise ValueError('Authoritative chapter journal changed before enrollment')
            relocation=locations.plan(db,item['raw'],item['kind'],item['original'],config.audiobook_output_root,item['destination'],item['routing'])
            enrolled.append({'publication_id':relocation['publication_id'],'candidate_id':item['identity'],'kind':item['kind'],'source':item['original']['final_path'],'destination':item['destination'],
                'size':item['original']['size'],'frozen_binding_sha256':locations._digest(locations._frozen(relocation))})
        db.commit()
    outcomes=[]
    for outcome,items in (('enrolled',enrolled),('already_at_destination',already),('held',held)):
        for item in items:
            if item['candidate_id'] not in completed_ids:continue
            disposition='verification_deferred' if item.get('hold_type')=='verification_deferred' else outcome
            reason=item.get('reason') or ('Verified publication enrolled for migration' if outcome=='enrolled' else 'Verified publication already at reviewed destination')
            outcomes.append(dict(item,outcome=disposition,reason=reason))
    completeness=_completeness_receipt(completed_census,outcomes)
    policy={'legacy_roots':dict(roots),'audiobook_sources':list(config.audiobook_sources),'audiobook_output_root':config.audiobook_output_root}
    guard_roots=policy_roots(policy)
    return {'schema':PLAN_SCHEMA,'database':str(database),'roots':guard_roots,'source_policy':policy,'source_policy_sha256':locations._digest(policy),'verification_selection':sorted(selected) if selected is not None else None,
            'publications':enrolled,'already_at_destination':already,'held':held,'completed_candidate_completeness':completeness,
            'planning_inputs':{'configuration_sha256':locations._digest({'database':str(database),**policy}),'routing_decisions_sha256':locations._digest(list(decisions))},
            'planned_bytes':bytes_required,'free_bytes':free,'routing_policy_version':POLICY,
            'scope_counts':{'current_candidates':len(candidates),'approved_candidates':approved_count,'not_approved':not_approved,'context_unavailable':context_unavailable,'enrolled':len(enrolled),'already_at_destination':len(already),'held':len(held),'uncached_variants_fully_hashed':verified_missing,'verification_deferred':sum(item.get('hold_type')=='verification_deferred' for item in held)},
            'active_variant_counts':variant_counts,'import_scope':'One active publication per current Ready book; superseded base/chapter variants and recovery media remain at original locations, outside the import tree'}

def prepare(database,roots,audiobook_sources,output_root,decisions=(),verification_candidates=None):
    database=Path(database).absolute()
    if ACTIVE_CATALOG.get()!=str(database):raise ValueError('Acquire the real exclusive catalog owner before final migration planning')
    with catalog_identity_lease(database) as identity:
        result=_prepare(database,roots,audiobook_sources,output_root,decisions,verification_candidates)
        result['catalog_identity']=identity
        return result


def read_pinned_json(path,sha256):
    import hashlib
    from native_io import ordinary,DirectoryBoundary,VerifiedFile
    path=ordinary(path)
    with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as file:
        if file.facts()['links']!=1 or file.facts()['size']>4*1024*1024:raise ValueError('Input must be bounded unique ordinary data')
        raw=b''.join(file.chunks())
        if hashlib.sha256(raw).hexdigest()!=sha256:raise ValueError('Reviewed planning input SHA256 changed')
        return json.loads(raw)

def write_plan(path,plan):
    import hashlib
    from native_io import ordinary,DirectoryBoundary,VerifiedFile
    path=ordinary(path);raw=(json.dumps(plan,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
    if len(raw)>4*1024*1024:raise ValueError('Reviewed plan exceeds bounded operator input size')
    if path.is_relative_to(Path(plan['database']).parent) or any(path.is_relative_to(Path(root)) for root in plan['roots'].values()):raise ValueError('Keep plan outside catalog data and libraries')
    with DirectoryBoundary(path.anchor,path.parent) as boundary:
        with open(path,'xb') as created:
            created.write(raw);created.flush();os.fsync(created.fileno())
        with VerifiedFile(path) as held:
            boundary.revalidate()
            if held.facts()['links']!=1 or held.sha256()!=hashlib.sha256(raw).hexdigest():raise ValueError('Published plan changed; do not run migration')
    return {'plan':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'publications':len(plan['publications']),'held':len(plan['held']),'outputs_changed':False}

def main(argv=None):
    import argparse
    from catalog_owner import catalog_lock
    parser=argparse.ArgumentParser(description='Enroll current verified publications and write a new reviewable plan under offline catalog ownership; never moves media')
    parser.add_argument('--config',required=True);parser.add_argument('--config-sha',required=True)
    parser.add_argument('--output-plan',required=True)
    parser.add_argument('--decisions');parser.add_argument('--decisions-sha')
    parser.add_argument('--verify-candidate',action='append',help='Only these uncached candidate IDs receive bounded hash preflight; cached publications remain eligible and all others are accounted as deferred')
    args=parser.parse_args(argv)
    if bool(args.decisions)!=bool(args.decisions_sha):raise ValueError('Routing decisions require an exact SHA256')
    config=read_pinned_json(args.config,args.config_sha)
    decisions=read_pinned_json(args.decisions,args.decisions_sha) if args.decisions else []
    if isinstance(decisions,dict):decisions=decisions['decisions']
    if config.get('schema')!='books-reviewed-migration-config-v1':raise ValueError('Reviewed migration configuration schema differs')
    roots=config['roots'];guard_roots=dict(roots)
    for index,root in enumerate(config.get('audiobook_sources') or [roots['Audiobooks']]):guard_roots['Source '+str(index+1)]=root
    guard_roots['Output']=config['audiobook_output_root']
    if Path(args.output_plan).exists():raise ValueError('Choose a fresh plan path; existing evidence is never overwritten')
    with catalog_lock(config['database'],guard_roots):
        plan=prepare(config['database'],roots,config.get('audiobook_sources'),config['audiobook_output_root'],decisions,verification_candidates=args.verify_candidate)
        plan['planning_inputs']['configuration_file']={'path':str(Path(args.config).absolute()),'sha256':args.config_sha}
        if args.decisions:plan['planning_inputs']['routing_decisions_file']={'path':str(Path(args.decisions).absolute()),'sha256':args.decisions_sha}
        result=write_plan(args.output_plan,plan)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0

if __name__=='__main__':raise SystemExit(main())
