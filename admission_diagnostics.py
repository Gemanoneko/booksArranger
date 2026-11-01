"""Display-only chapter refusals bound to the candidate actually inspected."""
import json

def save(db,row,diagnostic):
    current=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=? AND superseded=0',(row['id'],)).fetchone()
    if not current or tuple(current)!=(row['revision'],row['fingerprint']):return
    db.execute('CREATE TABLE IF NOT EXISTS chapter_admission_errors(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, fingerprint TEXT NOT NULL, diagnostic TEXT NOT NULL)')
    db.execute('INSERT OR REPLACE INTO chapter_admission_errors VALUES(?,?,?,?)',(row['id'],row['revision'],row['fingerprint'],json.dumps(diagnostic,ensure_ascii=False,allow_nan=False)))

def read(db,row):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='chapter_admission_errors' AND type='table'").fetchone():return None
    value=db.execute('SELECT diagnostic FROM chapter_admission_errors WHERE id=? AND revision=? AND fingerprint=?',(row['id'],row['revision'],row['fingerprint'])).fetchone()
    return {'chapter_diagnostic':json.loads(value[0])} if value else None

def clear(db,row):
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='chapter_admission_errors' AND type='table'").fetchone():
        db.execute('DELETE FROM chapter_admission_errors WHERE id=? AND revision=? AND fingerprint=?',(row['id'],row['revision'],row['fingerprint']))
