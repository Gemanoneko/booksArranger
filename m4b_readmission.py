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
            return {'accepted':True,'queued_next':True,'position':position,'kind':kind,'state':state,'parent_job_id':parent,'child_job_id':child}
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

def next_job(db_factory,admit,now):
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
        if not order:return None
        parent,kind,state,child=order[0]
        if state=='admitted':return child
        try:result=admit(parent,kind)
        except InterruptedError:raise
        except Exception as error:result={'requeued':False,'reason':str(error),'cause':'unknown'}
        if result.get('defer'):return None
        with db_factory() as db:
            if result.get('requeued') and result.get('job_id'):
                db.execute("UPDATE m4b_readmissions SET state='admitted',child_job_id=?,detail=?,updated=? WHERE parent_job_id=? AND state='queued'",
                    (result['job_id'],json.dumps({'reason':result.get('reason','')}),_stamp(now),parent))
            else:
                refusal=retry_refusal.record(result.get('reason'),result.get('cause'),_stamp(now))
                db.execute("UPDATE m4b_readmissions SET state='refused',detail=?,updated=? WHERE parent_job_id=? AND state='queued'",
                    (json.dumps(refusal,ensure_ascii=False),_stamp(now),parent))

def convert_legacy(db):
    """Startup, once per catalog: v0.18.0 plain-text refusals become typed records (retry_refusal.legacy)."""
    return retry_refusal.convert_legacy(db)
