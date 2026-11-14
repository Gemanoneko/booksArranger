"""Finite current-path migration. Immutable producer/history JSON is never edited."""
import hashlib,json,ntpath
from storage_relocation import _inside,_key,_need

# These columns describe current working locations, not user library roots.
COLUMNS={'working_files':('path',),'storage_cleanup_files':('path',),
 'owned_artifacts':('path',),'cleanup_members':('backup',),
 'candidate_context':(), 'book_groups':()}
JSON_KEYS={'path','root','cover_path','cache_path','staging_path','working_path','data_dir'}

def migrate(db,before,after):
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    changed=[]
    def path(value):
        if not isinstance(value,str) or not ntpath.isabs(value):return value
        for origin in before:
            if _inside(value,origin):
                rel=ntpath.relpath(value,origin)
                return after if rel=='.' else ntpath.join(after,rel)
        return value
    for table,columns in COLUMNS.items():
        if table not in tables:continue
        actual={r[1] for r in db.execute('PRAGMA table_info('+table+')')}
        for column in columns:
            if column not in actual:continue
            rows=db.execute('SELECT rowid,"'+column+'" FROM "'+table+'"').fetchall()
            _need(len(rows)<=100000,'Portable migration exceeds its typed row bound')
            for key,old in rows:
                new=path(old)
                if new!=old:
                    db.execute('UPDATE "'+table+'" SET "'+column+'"=? WHERE rowid=? AND "'+column+'"=?',(new,key,old))
                    changed.append((table,column,key,old,new))
    # Queued/paused/completed manifests and their hashes remain byte-identical.
    return changed
