"""Analyzed damaged-source holds and source-incarnation reconciliation.

Internal assessment calls only. No HTTP/imported-receipt marking, file removal,
source approval, output adoption or queue creation belongs here.
"""
import contextlib
import copy
import datetime
import hashlib
import json
from pathlib import Path

SCHEMA='books-source-damage-analysis-v1'
REQUIRED='Need to reacquire — replace the damaged source and scan again'
_TOKEN=object()

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def _table(db,name):return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone() is not None
def ensure(db):
    db.execute("CREATE TABLE IF NOT EXISTS reacquire_markers(candidate_id TEXT PRIMARY KEY,job_id TEXT NOT NULL,root TEXT NOT NULL,state TEXT NOT NULL,snapshot TEXT NOT NULL,analysis TEXT NOT NULL,receipt TEXT NOT NULL DEFAULT '')")
def markers(db,root=None):
    if not _table(db,'reacquire_markers'):return []
    return [dict(row) for row in db.execute('SELECT * FROM reacquire_markers'+(' WHERE root=?' if root is not None else ''),((root,) if root is not None else ()))]
def marker(db,identity):
    if not _table(db,'reacquire_markers'):return None
    row=db.execute('SELECT * FROM reacquire_markers WHERE candidate_id=?',(identity,)).fetchone()
    return dict(row) if row else None
def admission_hold(db,identity):
    value=marker(db,identity)
    return ('Damaged-source entry archived; use the newly discovered replacement' if value['state']=='archived' else REQUIRED) if value else None
def require_admission(db,identity):
    reason=admission_hold(db,identity)
    if reason:raise ValueError(reason)
def archived_ids(db,root):return {row['candidate_id'] for row in markers(db,root) if row['state']=='archived'}
def frozen_scopes(db,root):return {json.loads(row['snapshot'])['group']['scope'] for row in markers(db,root) if row['state']=='required'}
def marked_path(db,root,path):
    return any(path in {m['path'] for m in json.loads(row['snapshot'])['members']} for row in markers(db,root) if row['state']=='required')
def _current(db,identity,archiving=False):
    group=db.execute('SELECT * FROM book_groups WHERE id=? AND superseded=0',(identity,)).fetchone()
    if not group:raise ValueError('Damaged-source candidate is no longer current')
    group=dict(group);context=db.execute('SELECT * FROM candidate_context WHERE id=?',(identity,)).fetchone()
    if not context or context['revision']!=group['revision']:raise ValueError('Damaged-source review context changed')
    jobs=[dict(row) for row in db.execute("SELECT * FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? ORDER BY created DESC,job_id DESC",(identity,))]
    aside={row[0] for row in db.execute('SELECT job_id FROM audio_job_set_aside')} if _table(db,'audio_job_set_aside') else set()
    current=next((row for row in jobs if row['job_id'] not in aside),None)
    if not current or current['state']!='needs attention':raise ValueError('Newest damaged-source job is not held')
    members=json.loads(group['evidence'])['members'];sources=json.loads(current['manifest'])['sources']
    if not members or len({m['path'] for m in members})!=len(members) or {m['path'] for m in members}!={s['path'] for s in sources}:raise ValueError('Exact whole candidate source membership is required')
    for row in jobs:
        if row['output'] or 'publication_intent' in json.loads(row['journal']) or row['state'] in ('pending','running','completed'):raise ValueError('Publication or active work protects damaged-source history')
    paths={m['path'] for m in members}
    for other in db.execute('SELECT id,evidence FROM book_groups WHERE root=? AND superseded=0 AND id<>?',(group['root'],identity)):
        if paths & {m['path'] for m in json.loads(other['evidence'])['members']}:raise ValueError('Source members overlap another active candidate')
    if _table(db,'automatic_manual_drafts'):
        import time
        if db.execute('SELECT 1 FROM automatic_manual_drafts WHERE id=? AND expires>?',(identity,time.time())).fetchone():raise ValueError('Candidate is being edited')
    jobids={row['job_id'] for row in jobs}
    for table,column in (('source_cleanup','job_id'),('storage_cleanup_jobs','job_id'),('recovery_retention','job_id'),('recovery_completion','job_id'),('source_retirements','job_id'),('owned_artifacts','job_id'),('working_files','job_id')):
        if archiving and _table(db,table):
            columns={r[1] for r in db.execute('PRAGMA table_info('+table+')')}
            if column not in columns:raise ValueError('Unknown retained dependency shape: '+table)
            if any(db.execute('SELECT 1 FROM '+table+' WHERE '+column+'=?',(j,)).fetchone() for j in jobids):raise ValueError('Retained dependency protects damaged-source history: '+table)
    if archiving and _table(db,'audiobook_replacements') and db.execute('SELECT 1 FROM audiobook_replacements WHERE candidate_id=?',(identity,)).fetchone():raise ValueError('Replacement history protects damaged source')
    if archiving and _table(db,'audio_repair_admissions'):
        columns={r[1] for r in db.execute('PRAGMA table_info(audio_repair_admissions)')}
        if not {'parent_job_id','child_job_id'}<=columns:raise ValueError('Unknown repair dependency')
        if any(db.execute('SELECT 1 FROM audio_repair_admissions WHERE parent_job_id=? OR child_job_id=?',(j,j)).fetchone() for j in jobids):raise ValueError('Repair lineage protects damaged-source history')
    if _table(db,'working_attempts'):
        columns={r[1] for r in db.execute('PRAGMA table_info(working_attempts)')}
        if not {'job_id','producer','state'}<=columns:raise ValueError('Unknown working dependency')
        for row in db.execute('SELECT * FROM working_attempts'):
            if row['job_id'] in jobids and (row['producer'] not in ('closed','not_started') or row['state'] in ('producing','creating')):raise ValueError('Producer closure is not proved')
    for table,column in (('m4b_readmissions','parent_job_id'),):
        if _table(db,table) and any(db.execute("SELECT 1 FROM "+table+" WHERE "+column+"=? AND state IN ('queued','admitted')",(j,)).fetchone() for j in jobids):raise ValueError('Saved admission still references the damaged source')
    inventory=[]
    for member in members:
        row=db.execute('SELECT * FROM files WHERE root=? AND path=?',(group['root'],member['path'])).fetchone()
        if not row:raise ValueError('Source inventory is incomplete')
        inventory.append(dict(row))
    return {'group':group,'context':dict(context),'jobs':jobs,'current_job':current,'members':members,'sources':sources,'inventory':inventory}

class AssessedDamage:
    """Ephemeral result of a trusted in-process diagnostic, never a JSON capability."""
    def __init__(self,token,analysis):
        if token is not _TOKEN:raise ValueError('Trusted bounded diagnostic assessment required')
        self.analysis=copy.deepcopy(analysis);self._token=token

@contextlib.contextmanager
def assess_live_sources(snapshot,assessment):
    """Only the fixed internal producer can supply an assessment; held through CAS."""
    from mp3_tag_repair import SourceDamageAssessment
    from native_io import ordinary,DirectoryBoundary,VerifiedFile,single_stream
    if not isinstance(assessment,SourceDamageAssessment):raise ValueError('Actual internal diagnostic assessment required')
    result=assessment.data
    if result.get('schema')!=SCHEMA or result.get('outcome')!='uncertain_audio_loss' or result.get('decision')!='reacquire' or result.get('context_completed') is not True:raise ValueError('No supported unsafe-audio assessment')
    job=snapshot['current_job'];group=snapshot['group']
    expected={'job_id':job['job_id'],'manifest_sha256':job['manifest_hash'],'candidate_id':group['id'],'candidate_revision':group['revision'],'source_fingerprint':group['fingerprint'],'sources':[{'path':s['path'],'sha256':s['sha256'],'size':s['size'],'modified':str(s['modified'])} for s in snapshot['sources']]}
    if any(result.get(key)!=value for key,value in expected.items()):raise ValueError('Diagnostic source/job evidence changed')
    if result.get('analysis_version')!='audio-damage-v1' or any(not isinstance(result.get(key),str) or not result[key].strip() for key in ('reason','repair_limit','analysis_id')):raise ValueError('Diagnostic measurement unavailable')
    for key in ('script_sha256','tool_sha256'):
        value=result.get(key)
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ValueError('Diagnostic implementation pin missing')
    if not isinstance(result.get('argv'),list) or not result['argv']:raise ValueError('Diagnostic invocation missing')
    with contextlib.ExitStack() as stack:
        held=[]
        for source in snapshot['sources']:
            path=ordinary(source['path']);stack.enter_context(DirectoryBoundary(ordinary(group['root']),path.parent));file=stack.enter_context(VerifiedFile(path));single_stream(path)
            if file.facts()['links']!=1 or file.facts()['size']!=source['size'] or file.sha256()!=source['sha256']:raise ValueError('Analyzed original differs from frozen source')
            held.append(file)
        result=dict(result,verdict='unsafe_meaningful_audio_repair',snapshot_sha256=digest(snapshot),closure_basis='production-owned-context-completed; active-zero checked; handle-close unverified')
        yield AssessedDamage(_TOKEN,result)
        for source,file in zip(snapshot['sources'],held):
            single_stream(source['path'])
            if file.sha256()!=source['sha256']:raise ValueError('Original changed during marker persistence')

def record_assessment(db,identity,assessment):
    """Caller owns review/group/admission boundary and writer transaction."""
    if not isinstance(assessment,AssessedDamage) or assessment._token is not _TOKEN:raise ValueError('Imported diagnostic records cannot mark sources')
    if not db.in_transaction:raise ValueError('Assessment persistence requires writer transaction')
    snapshot=_current(db,identity)
    job=snapshot['current_job']
    if not job['attempt_id'] or not _table(db,'working_attempts'):raise ValueError('Exact post-attempt producer closure is unavailable')
    attempt=db.execute('SELECT producer FROM working_attempts WHERE job_id=? AND attempt_id=?',(job['job_id'],job['attempt_id'])).fetchone()
    if not attempt or attempt[0]!='closed':raise ValueError('Exact post-attempt producer is not durably closed')
    if assessment.analysis['snapshot_sha256']!=digest(snapshot):raise ValueError('Assessment candidate or source snapshot changed')
    ensure(db)
    if marker(db,identity):raise ValueError('Existing assessment must not be replaced silently')
    db.execute('INSERT INTO reacquire_markers VALUES(?,?,?,?,?,?,?)',(identity,snapshot['current_job']['job_id'],snapshot['group']['root'],'required',json.dumps(snapshot,ensure_ascii=False),json.dumps(assessment.analysis,ensure_ascii=False),''))

def project(db,job_id):
    if not _table(db,'reacquire_markers'):return None
    row=db.execute("SELECT * FROM reacquire_markers WHERE job_id=? AND state='required'",(job_id,)).fetchone()
    if not row:return None
    value=dict(row);analysis=json.loads(value['analysis']);snapshot=json.loads(value['snapshot'])
    scan=db.execute('SELECT state FROM jobs WHERE root=?',(value['root'],)).fetchone() if _table(db,'jobs') else None
    presence='checking' if not scan or scan[0]=='scanning' else 'unavailable' if scan[0] in ('offline','failed','stopped','completed with errors') else 'present'
    if presence=='present':
        missing=[db.execute('SELECT missing FROM files WHERE root=? AND path=?',(value['root'],s['path'])).fetchone() for s in snapshot['sources']]
        if any(r is None or r[0] for r in missing):presence='partially_missing'
    return {'state':'required','reason':analysis['reason'],'repair_limit':analysis['repair_limit'],'certainty':'uncertain' if analysis['verdict']=='unsafe_meaningful_audio_repair' else 'measured',
            'analysis_id':analysis['analysis_id'],'originals':[{'path':s['path']} for s in snapshot['sources']],'original_count':len(snapshot['sources']),
            'source_presence':presence,'retained_history':True}


@contextlib.contextmanager
def root_scan_lease(db,root):
    if not any(row['state']=='required' for row in markers(db,root)):
        yield None;return
    from native_io import ordinary,DirectoryBoundary
    with DirectoryBoundary(ordinary(root),ordinary(root)) as boundary:yield boundary

def _hash(file,stop,deadline):
    import time
    value=hashlib.sha256()
    for chunk in file.chunks():
        if stop.is_set() or time.monotonic()>deadline:raise ValueError('Damaged-source reconciliation stopped or exceeded its bound')
        value.update(chunk)
    return value.hexdigest()

def reconcile_scan(db,inventory,root,generation,root_lease):
    """Only an accessible, error-free, fully drained original-root scan may retire."""
    import time
    pending=[row for row in markers(db,root) if row['state']=='required']
    if not pending:return []
    if root_lease is None:raise ValueError('Original source root identity was not retained for this scan')
    root_lease.revalidate();result=[]
    for saved in pending:
        try:
            with db: result.append(_reconcile_one(db,inventory,root,generation,root_lease,saved,time.monotonic()+120))
        except (ValueError,OSError,KeyError) as error:
            # The marked candidate remains active. No diagnostic is mistaken for deletion.
            result.append({'candidate_id':saved['candidate_id'],'archived':False,'reason':str(error)})
    return result

def _reconcile_one(db,inventory,root,generation,root_lease,saved,deadline):
    from native_io import ordinary,DirectoryBoundary,VerifiedFile,single_stream
    snapshot=json.loads(saved['snapshot']);identity=saved['candidate_id'];observations=[]
    def scan_guard():
        root_lease.revalidate()
        job=db.execute('SELECT * FROM jobs WHERE root=?',(root,)).fetchone()
        if not job or job['generation']!=generation or job['state']!='scanning' or job['errors'] or inventory.stop_event.is_set():raise ValueError('Accessible complete source scan is not confirmed')
        if db.execute("SELECT 1 FROM queue WHERE root=? AND generation=? AND state<>'done'",(root,generation)).fetchone():raise ValueError('Source enumeration is incomplete')
    scan_guard()
    with contextlib.ExitStack() as stack:
        for original in snapshot['sources']:
            path=ordinary(original['path'])
            row=db.execute('SELECT * FROM files WHERE root=? AND path=?',(root,str(path))).fetchone()
            try:
                path.stat()
            except FileNotFoundError:
                parent=path.parent
                while not parent.exists() and parent!=ordinary(root):parent=parent.parent
                if not parent.is_relative_to(ordinary(root)):raise ValueError('Absent source ancestry is not covered')
                boundary=stack.enter_context(DirectoryBoundary(ordinary(root),parent))
                covered=db.execute("SELECT 1 FROM queue WHERE root=? AND generation=? AND path=? AND directory=1 AND state='done'",(root,generation,str(parent))).fetchone()
                if not covered:raise ValueError('Absent source parent was not successfully enumerated')
                observations.append({'path':str(path),'state':'absent','row':dict(row) if row else None,'boundary':boundary});continue
            boundary=stack.enter_context(DirectoryBoundary(ordinary(root),path.parent));file=stack.enter_context(VerifiedFile(path));single_stream(path)
            facts=file.facts()
            if facts['links']!=1:raise ValueError('Replacement source is not a unique ordinary file')
            sha=_hash(file,inventory.stop_event,deadline)
            if sha==original['sha256']:raise ValueError('Some original source content remains')
            if not row or row['seen']!=generation or row['error']:raise ValueError('Replacement inventory was not successfully refreshed')
            # Reread while that exact replacement is protected, even for unchanged stat tuples.
            metadata=inventory.reader(str(path),row['kind'],inventory.stop_event)
            boundary.revalidate();single_stream(path)
            if file.facts()!=facts or _hash(file,inventory.stop_event,deadline)!=sha:raise ValueError('Replacement source changed during metadata read')
            observations.append({'path':str(path),'state':'displaced','row':dict(row),'facts':facts,'sha256':sha,'metadata':metadata,'boundary':boundary,'file':file})
        if db.in_transaction:raise ValueError('Reconciliation requires a fresh writer transaction')
        db.execute('BEGIN IMMEDIATE')
        try:
            scan_guard()
            current=marker(db,identity)
            if current!=saved or current['state']!='required':raise ValueError('Damaged-source assessment was superseded')
            fresh=_current(db,identity,archiving=True)
            # Inventory observations may change during scanning; all identity/review/job bindings may not.
            for key in ('group','context','jobs','current_job','members','sources'):
                if fresh[key]!=snapshot[key]:raise ValueError('Damaged-source candidate or job changed before reconciliation')
            archive_scope=snapshot['group']['scope']+'\x1freacquired:'+identity
            if db.execute('SELECT 1 FROM book_groups WHERE root=? AND scope=?',(root,archive_scope)).fetchone():raise ValueError('Archive scope collision; original retained')
            for item in observations:
                item['boundary'].revalidate()
                if item['state']=='absent':
                    try:Path(item['path']).stat()
                    except FileNotFoundError:pass
                    else:raise ValueError('Source reappeared before reconciliation')
                elif item['file'].facts()!=item['facts'] or _hash(item['file'],inventory.stop_event,deadline)!=item['sha256']:raise ValueError('Replacement changed before reconciliation')
            import book_restart
            book_restart.ensure(db)
            for job in fresh['jobs']:
                if job['state']!='needs attention':raise ValueError('Historical job is not eligible for set-aside')
                db.execute('INSERT OR IGNORE INTO audio_job_set_aside VALUES(?,?,?,?,?)',(job['job_id'],identity,snapshot['group']['revision'],'reacquire',datetime.datetime.now(datetime.timezone.utc).isoformat()))
            receipt={'schema':'books-reacquire-archive-v1','original_snapshot':snapshot,'observations':[{k:v for k,v in item.items() if k not in ('boundary','file')} for item in observations]}
            for item in observations:
                if item['state']=='absent':db.execute('DELETE FROM files WHERE root=? AND path=?',(root,item['path']))
                else:db.execute("UPDATE files SET metadata=?,review='',error='',missing=0 WHERE root=? AND path=?",(json.dumps(item['metadata'],ensure_ascii=False),root,item['path']))
            changed=db.execute('UPDATE book_groups SET scope=?,superseded=1,approved=0 WHERE id=? AND scope=? AND superseded=0',(archive_scope,identity,snapshot['group']['scope']))
            if changed.rowcount!=1:raise ValueError('Damaged-source archive compare-and-set refused')
            changed=db.execute("UPDATE reacquire_markers SET state='archived',receipt=? WHERE candidate_id=? AND state='required' AND snapshot=? AND analysis=?",(json.dumps(receipt,ensure_ascii=False),identity,saved['snapshot'],saved['analysis']))
            if changed.rowcount!=1:raise ValueError('Damaged-source marker compare-and-set refused')
            db.execute('UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1')
            db.execute('DELETE FROM book_group_sync WHERE root=?',(root,));scan_guard();db.commit()
        except BaseException:db.rollback();raise
    return {'candidate_id':identity,'archived':True,'reason':'Damaged originals confirmed removed or replaced; history retained'}
