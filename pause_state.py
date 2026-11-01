"""Recorded stop attribution. Missing history stays unknown; display never controls work."""
import json
import datetime

def record(db, scope, origin, reason):
    if scope not in ('jobs','automatic') or origin not in ('user','update','closing','interrupted'):
        raise ValueError('Invalid pause attribution')
    db.execute('CREATE TABLE IF NOT EXISTS pause_attribution(scope TEXT PRIMARY KEY, data TEXT NOT NULL)')
    value={'origin':origin,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reason':str(reason)}
    db.execute('INSERT OR REPLACE INTO pause_attribution VALUES(?,?)',(scope,json.dumps(value)))
    return value

def read(db, scope):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pause_attribution'").fetchone():return None
    row=db.execute('SELECT data FROM pause_attribution WHERE scope=?',(scope,)).fetchone()
    return json.loads(row[0]) if row else None

def clear(db, scope):
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pause_attribution'").fetchone():
        db.execute('DELETE FROM pause_attribution WHERE scope=?',(scope,))
