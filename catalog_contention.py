"""Replay only captured catalog SQL; never repeat media/native/research operations."""
import json
import sqlite3


class CatalogHold(RuntimeError):
    """A saved scan needs another supported attempt; this is not a media error."""


def is_busy(error):
    code=getattr(error,'sqlite_errorcode',None)
    return isinstance(error,sqlite3.OperationalError) and type(code) is int and code & 255 == sqlite3.SQLITE_BUSY


def write(database,operation,stop=None):
    from sqlite_retry import transaction
    try:return transaction(database,operation,stop)
    except sqlite3.OperationalError as error:
        if not is_busy(error):raise
        raise CatalogHold('Catalog busy after bounded database retries; saved scan task remains pending') from error


def scan_guard(db,root,generation,path=None,task_directory=None):
    job=db.execute('SELECT generation,state FROM jobs WHERE root=?',(root,)).fetchone()
    if not job or job['generation']!=generation or job['state']!='scanning':
        raise CatalogHold('Scan generation or state changed; saved catalog work was not applied')
    if path is not None:
        task=db.execute('SELECT state,directory FROM queue WHERE root=? AND generation=? AND path=?',(root,generation,path)).fetchone()
        if not task or task['state']!='running' or (task_directory is not None and task['directory']!=int(task_directory)):
            raise CatalogHold('Scan task changed; captured catalog work was not applied')


def file_token(db,root,path):
    def table(name):return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone())
    row=db.execute('SELECT * FROM files WHERE root=? AND path=?',(root,path)).fetchone()
    token={'file':dict(row) if row else None}
    token['queue']=[dict(r) for r in db.execute('SELECT * FROM queue WHERE root=? AND path=? ORDER BY generation',(root,path))]
    token['retirements']=[dict(r) for r in db.execute('SELECT * FROM source_retirements WHERE root=? AND path=? ORDER BY cleanup_id',(root,path))] if table('source_retirements') else []
    token['owned']=[dict(r) for r in db.execute('SELECT * FROM owned_artifacts WHERE path=?',(path,))] if table('owned_artifacts') else []
    token['relocations']=[dict(r) for r in db.execute('SELECT * FROM output_relocations WHERE planned_destination=?',(path,))] if table('output_relocations') and 'planned_destination' in {r[1] for r in db.execute('PRAGMA table_info(output_relocations)')} else []
    token['reacquire']=[dict(r) for r in db.execute('SELECT * FROM reacquire_markers WHERE root=? ORDER BY candidate_id',(root,)) if path in {m['path'] for m in json.loads(r['snapshot'])['members']}] if table('reacquire_markers') else []
    grouped=[dict(r) for r in db.execute('SELECT * FROM book_groups WHERE root=? ORDER BY id',(root,)) if path in {m['path'] for m in json.loads(r['evidence'])['members']}] if table('book_groups') else []
    token['groups']=grouped
    token['contexts']=[dict(r) for group in grouped for r in db.execute('SELECT * FROM candidate_context WHERE id=?',(group['id'],))] if table('candidate_context') else []
    return token


def scan_write(inventory,root,generation,path,operation,expected=None,*,stopping=False,finish=True,task_directory=None):
    def persist(db):
        scan_guard(db,root,generation,path,task_directory)
        if expected is not None and file_token(db,root,path)!=expected:
            raise CatalogHold('Catalog review, retirement or source evidence changed during read; task remains pending')
        result=operation(db)
        if finish:db.execute("UPDATE queue SET state='done' WHERE root=? AND generation=? AND path=? AND state='running'",(root,generation,path))
        return result
    return write(inventory.database,persist,None if stopping else inventory.stop_event)


def synchronize_groups(inventory,roots):
    # Caller owns group_lock. Drop the reader before acquiring a fresh writer.
    import groups
    from scanner import connect
    with connect(inventory.database) as db:
        db.execute('BEGIN')
        fresh=_groups_current(db,roots,groups)
    if fresh:return
    def synchronize(db):
        for root in roots:
            if not _groups_current(db,[root],groups):groups.sync(db,root)
    write(inventory.database,synchronize)


def _groups_current(db,roots,groups):
    try:
        algorithm=db.execute('SELECT version FROM book_group_algorithm WHERE id=1').fetchone()
        return bool(algorithm and algorithm[0]==groups.GROUP_VERSION and all(groups.current(db,root) for root in roots))
    except sqlite3.OperationalError as error:
        if is_busy(error):raise
        if 'no such table' not in str(error):raise
        return False


def remember_busy_failure(inventory,root,generation,error,message):
    if is_busy(getattr(error,'__cause__',None)):
        failures=getattr(inventory,'_catalog_failures',{})
        failures[root]={'root':root,'generation':generation,'message':message,'failure_durable':False}
        inventory._catalog_failures=failures
