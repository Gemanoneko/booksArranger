"""Priority re-admission for M4B Retry and Repair: "queued after the book that is running".

A click is accepted at any time and stored durably in click order. Between books, the audio
worker asks next_job(): the request at the head is admitted through the existing proof route
(plan() proof, frozen-review compare-and-swap, one child per failed parent, the per-book
working-file gate) and its child job runs next, before the normal queue. Several clicks run in
click order. A refused admission is recorded for that book only, with a typed cause (retry_refusal),
and the next request proceeds. Nothing here proves media, opens sources or changes a job row; it only
orders and records.
"""
import json

import retry_refusal

KINDS=('retry','repair')
SCHEMA=('CREATE TABLE IF NOT EXISTS m4b_readmissions(parent_job_id TEXT PRIMARY KEY,kind TEXT NOT NULL,'
        'seq INTEGER NOT NULL UNIQUE,state TEXT NOT NULL,child_job_id TEXT UNIQUE,detail TEXT NOT NULL DEFAULT \'\','
        'requested TEXT NOT NULL,updated TEXT NOT NULL)')
# Priority order: requests not yet admitted, and admitted children that have not started yet.
_ORDER=("SELECT r.parent_job_id,r.kind,r.state,r.child_job_id FROM m4b_readmissions r "
        "LEFT JOIN audio_jobs c ON c.job_id=r.child_job_id "
        "WHERE r.state='queued' OR r.state='admitted' AND c.state='pending' ORDER BY r.seq")

def ensure(db):db.execute(SCHEMA)

def _stamp(now):
    import datetime
    return datetime.datetime.fromtimestamp(now,datetime.timezone.utc).isoformat()

def _exists(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='m4b_readmissions'").fetchone() is not None

def _order(db):
    """Read-only: no table yet means nothing is queued."""
    return [tuple(row) for row in db.execute(_ORDER)] if _exists(db) else []

def request(db,parent_job_id,kind,now):
    """Accept a Retry/Repair click (idempotent while queued). Caller checks static eligibility."""
    if kind not in KINDS:raise ValueError('Unknown re-admission kind')
    ensure(db);db.execute('BEGIN IMMEDIATE')
    row=db.execute('SELECT state FROM m4b_readmissions WHERE parent_job_id=?',(parent_job_id,)).fetchone()
    if not row or row[0]=='refused':
        seq=db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM m4b_readmissions').fetchone()[0]
        db.execute('INSERT OR REPLACE INTO m4b_readmissions VALUES(?,?,?,?,?,?,?,?)',(parent_job_id,kind,seq,'queued',None,'',_stamp(now),_stamp(now)))
    return describe(db,parent_job_id)

def describe(db,job_id):
    """{'queued_next':True,'position':n,...} while waiting; refusal or admission facts after. Read-only."""
    if not _exists(db):return None
    order=_order(db)
    for position,(parent,kind,state,child) in enumerate(order,1):
        if job_id in (parent,child):
            saved=db.execute('SELECT detail FROM m4b_readmissions WHERE parent_job_id=?',(parent,)).fetchone()
            detail=json.loads(saved[0] or '{}') if saved else {}
            return {'accepted':True,'queued_next':True,'position':position,'kind':kind,'state':state,'parent_job_id':parent,'child_job_id':child,'waiting_reason':detail.get('waiting_reason','')}
    row=db.execute('SELECT parent_job_id,kind,state,child_job_id,detail,updated FROM m4b_readmissions WHERE parent_job_id=? OR child_job_id=?',(job_id,job_id)).fetchone()
    if not row:return None
    parent,kind,state,child,detail,updated=tuple(row)
    value={'queued_next':False,'kind':kind,'state':state,'parent_job_id':parent,'child_job_id':child}
    if state=='refused':
        # Typed refusal: cause and fix decide what the row offers; reason is the raw text for Technical detail.
        refusal=retry_refusal.parse(detail,updated)
        value.update(accepted=False,reason=refusal['reason'],cause=refusal['cause'],fix=refusal['fix'],app_version=refusal['app_version'],
                     key=refusal['key'],at=refusal['at'],stale=retry_refusal.stale(refusal))
    return value

def status(db,job_ids):
    """Per job id (failed parent or its child): describe(), for the row/panel. Read-only, one pass."""
    if not _exists(db):return {}
    return {job_id:value for job_id in job_ids if (value:=describe(db,job_id))}

def next_job(db_factory,admit,now,report=None):
    """Worker hook between books. Admits queued requests at the head in click order and returns the
    child job id that must run next, or None (normal queue order).

    admit(parent_job_id, kind) runs the existing proof route and returns {'requeued': True,
    'job_id': child}, {'requeued': False, 'reason': ..., 'cause': ...} (refused for that book only; cause is
    a retry_refusal.FIXES key, 'unknown' when absent), or
    {'defer': True} (not now, e.g. a library scan; the request keeps its place and the normal
    queue runs one book). InterruptedError leaves the request queued for the next resume.
    """
    while True:
        with db_factory() as db:order=_order(db)
        if not order:
            if report:report({'state':'idle','reason':'','job_id':None})
            return None
        parent,kind,state,child=order[0]
        if state=='admitted':return child
        if report:report({'state':'checking','job_id':parent,'reason':''})
        try:result=admit(parent,kind)
        except InterruptedError:raise
        except Exception as error:result={'requeued':False,'reason':str(error),'cause':'unknown'}
        if result.get('defer'):
            with db_factory() as db:record_waiting(db,result.get('reason') or 'Retry admission is waiting.')
            if report:report({'state':'waiting','job_id':parent,'reason':result.get('reason') or 'Retry requests are saved; admission is waiting.'})
            return None
        with db_factory() as db:
            if result.get('requeued') and result.get('job_id'):
                db.execute("UPDATE m4b_readmissions SET state='admitted',child_job_id=?,detail=?,updated=? WHERE parent_job_id=? AND state='queued'",
                    (result['job_id'],json.dumps({'reason':result.get('reason','')}),_stamp(now),parent))
            else:
                refusal=retry_refusal.record(result.get('reason'),result.get('cause'),_stamp(now))
                db.execute("UPDATE m4b_readmissions SET state='refused',detail=?,updated=? WHERE parent_job_id=? AND state='queued'",
                    (json.dumps(refusal,ensure_ascii=False),_stamp(now),parent))

def convert_legacy(db):
    """Startup, once per catalog: v0.18.0 plain-text refusals become typed records (retry_refusal.legacy), then refusals
    caused by a defect fixed since are marked resolved (retry_refusal.convert_resolved). Returns the number changed."""
    return retry_refusal.convert_legacy(db)+retry_refusal.convert_resolved(db)


def pending_count(db):
    return db.execute("SELECT COUNT(*) FROM m4b_readmissions WHERE state='queued'").fetchone()[0] if _exists(db) else 0

def target_progress(db,job_ids,checking_job=None):
    """Mutually exclusive current states; accepted requests are never child jobs."""
    counts={key:0 for key in ('waiting','checking','queued','running','completed','stopped')};targets=[]
    for job_id in job_ids:
        request=db.execute('SELECT * FROM m4b_readmissions WHERE parent_job_id=?',(job_id,)).fetchone() if _exists(db) else None
        child=request['child_job_id'] if request else job_id
        job=db.execute('SELECT state,reason FROM audio_jobs WHERE job_id=?',(child or job_id,)).fetchone()
        reason=''
        if request and request['state']=='queued':
            state='checking' if checking_job==job_id else 'waiting'
            if state=='waiting':reason=json.loads(request['detail'] or '{}').get('waiting_reason','')
        elif request and request['state']=='refused':
            state='stopped'
            try:reason=__import__('json').loads(request['detail']).get('reason','')
            except (ValueError,TypeError):reason='Retry request refused; see details'
        elif job and job['state'] in ('pending','running','completed'):state={'pending':'queued','running':'running','completed':'completed'}[job['state']]
        else:state='stopped';reason=job['reason'] if job else 'Saved retry target is unavailable'
        counts[state]+=1;targets.append({'job_id':job_id,'state':state,'child_job_id':child,'reason':reason})
    return {'schema':'books-retry-progress-v1','counts':counts,'targets':targets}


def save_bulk(db,run):
    """Submission receipt only; durable request rows remain the admission authority."""
    import json
    db.execute('CREATE TABLE IF NOT EXISTS retry_bulk_runs(id TEXT PRIMARY KEY,created TEXT NOT NULL,data TEXT NOT NULL)')
    db.execute('INSERT OR REPLACE INTO retry_bulk_runs VALUES(?,?,?)',(run['id'],run['created'],json.dumps(run,ensure_ascii=False,allow_nan=False)))

def latest_bulk(db):
    import json
    if not _table_exists(db,'retry_bulk_runs'):return None
    row=db.execute('SELECT data FROM retry_bulk_runs ORDER BY created DESC,rowid DESC LIMIT 1').fetchone()
    return json.loads(row[0]) if row else None

def _table_exists(db,name):return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone() is not None


def record_waiting(db,reason):
    """A failed start preserves requests and records its real reason; never admits a child."""
    if not _exists(db):return
    db.execute("UPDATE m4b_readmissions SET detail=? WHERE state='queued'",(json.dumps({'waiting_reason':str(reason)},ensure_ascii=False),))
