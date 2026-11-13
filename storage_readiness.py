"""Bounded read-only catalog readiness diagnostics; never closure authority."""
import datetime
import json
from pathlib import Path
import sqlite3


def inspect_readiness(database):
    database=Path(database).absolute()
    result=dict(schema='books-storage-readiness-v1',observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                database=str(database),authority=False,ready_to_freeze=False,unclosed_producers=[],states={})
    db=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=2)
    try:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('PRAGMA temp_store=MEMORY')
        db.execute('BEGIN')
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ('audio_jobs','working_attempts','producer_recovery_checkpoints','inplace_edits','audiobook_replacement_retirements'):
            if table in tables:
                columns={r[1] for r in db.execute('PRAGMA table_info('+table+')')}
                if 'state' in columns:
                    result['states'][table]={str(r[0]):r[1] for r in db.execute('SELECT state,count(*) FROM '+table+' GROUP BY state')}
        if 'working_attempts' not in tables:
            result['diagnostic']='No working-attempt ledger; explicit legacy inspection required'
            return result
        rows=db.execute("SELECT job_id,attempt_id,state,producer,updated FROM working_attempts WHERE COALESCE(producer,'')!='closed' AND COALESCE(state,'')!='retired' ORDER BY job_id,attempt_id LIMIT 1001").fetchall()
        if len(rows)>1000:raise ValueError('Unclosed attempt diagnostic exceeds its explicit bound')
        for row in rows:
            item=dict(row);job=None
            if 'audio_jobs' in tables:job=db.execute('SELECT state,attempt_id,output,journal FROM audio_jobs WHERE job_id=?',(row['job_id'],)).fetchone()
            item.update(job_state=job['state'] if job else None,current_attempt=bool(job and job['attempt_id']==row['attempt_id']),
                        output_recorded=bool(job and job['output']),publication_intent=False)
            if job and job['journal']:
                if len(job['journal'])>8*1024*1024:raise ValueError('Job journal exceeds the diagnostic bound')
                journal=json.loads(job['journal']);item['publication_intent']=bool(journal.get('publication_intent'))
            item['origin_records']=db.execute('SELECT count(*) FROM producer_origin_facts WHERE job_id=? AND attempt_id=?',tuple(row[k] for k in ('job_id','attempt_id'))).fetchone()[0] if 'producer_origin_facts' in tables else 0
            item['checkpoints']={r[0]:r[1] for r in db.execute('SELECT state,count(*) FROM producer_recovery_checkpoints WHERE job_id=? AND attempt_id=? GROUP BY state',tuple(row[k] for k in ('job_id','attempt_id')))} if 'producer_recovery_checkpoints' in tables else {}
            eligible=bool(job and job['state']=='needs attention' and item['current_attempt'] and not item['output_recorded'] and not item['publication_intent'] and row['state'] in ('producing','attention') and row['producer'] in ('active','uncertain'))
            item['source_recovery_scope_eligible']=eligible
            item['required_next_step']='Use the supported source recovery assessment; producer absence alone is insufficient' if eligible else 'Preserve the attempt and reconcile its current job/publication dependency through the supported source application'
            result['unclosed_producers'].append(item)
        result['diagnostic']='Source recovery obligations prevent a closed migration snapshot' if rows else 'No unclosed producer rows observed; actual ownership, complete receipt census and graceful freeze still required'
        result['source_recovery_contract']=[
            'Keep old native files, runtime originals and receipts intact while assessing the source application.',
            'A recovery-eligible job must be needs attention, the current attempt, without output/publication intent.',
            'Historical local-origin confirmation is an explicit truthful human fact; a copy or missing encoder cannot supply it.',
            'The existing checkpoint/later-startup or reviewed Windows boot-after-all-activity proof establishes closure; do not synthesize it.',
            'Supported Retry isolates the old attempt as retained work before creating new work. Unknown origin/startup/binding remains held.',
            'Only an approved source compatibility startup/recovery step may write the real catalog; this diagnostic never does so.']
        return result
    finally:db.close()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--database',required=True)
    print(json.dumps(inspect_readiness(parser.parse_args().database),sort_keys=True))
