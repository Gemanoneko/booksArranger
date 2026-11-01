"""Normalized leftover ownership index, invalidated by relevant catalog mutations.

No SQL custom function/collation is persisted: every catalog writer can maintain the
small generation triggers. Unicode path comparison stays Python normcase, exactly
as the former full scan. Cleanup receipts and conversion progress do not invalidate it.
"""
import json
import os
import threading

_TRACKED = {
    'catalog_group_members': None,
    'book_groups': 'id,superseded',
    'audio_jobs': 'job_id,manifest,state',
    'audio_job_set_aside': None,
    'reacquire_markers': 'snapshot,state',
}

class OwnershipIndex:
    def __init__(self):
        self.lock = threading.RLock()
        self.token = None
        self.paths = {}
        self.schema = None

    def _prepare(self, db, tables):
        schema = db.execute('PRAGMA schema_version').fetchone()[0]
        if self.schema == schema:
            return
        db.execute('CREATE TABLE IF NOT EXISTS cleanup_ownership_revision(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL)')
        db.execute('INSERT OR IGNORE INTO cleanup_ownership_revision VALUES(1,0)')
        for table, columns in _TRACKED.items():
            if table not in tables:
                continue
            for event in ('INSERT','UPDATE','DELETE'):
                clause = 'UPDATE OF ' + columns if event == 'UPDATE' and columns else event
                name = 'cleanup_ownership_' + table + '_' + event.lower()
                db.execute('CREATE TRIGGER IF NOT EXISTS ' + name + ' AFTER ' + clause + ' ON ' + table +
                           ' BEGIN UPDATE cleanup_ownership_revision SET revision=revision+1 WHERE id=1; END')
        self.schema = db.execute('PRAGMA schema_version').fetchone()[0]
        self.token = None

    def held(self, db, tables, job_id, candidate_id, wanted):
        with self.lock:
            self._prepare(db, tables)
            # Freeze one coherent ownership snapshot; a later query rechecks its token.
            db.commit()
            db.execute('BEGIN')
            token = (db.execute('PRAGMA schema_version').fetchone()[0],
                     db.execute('SELECT revision FROM cleanup_ownership_revision WHERE id=1').fetchone()[0])
            if token != self.token:
                paths = {}
                def add(path, kind, owner):
                    if path:
                        paths.setdefault(os.path.normcase(str(path)), set()).add((kind, owner))
                if {'catalog_group_members','book_groups'} <= tables:
                    for member, owner in db.execute('SELECT c.path,c.group_id FROM catalog_group_members c JOIN book_groups g ON g.id=c.group_id WHERE g.superseded=0'):
                        add(member, 'candidate', owner)
                aside = ' AND job_id NOT IN (SELECT job_id FROM audio_job_set_aside)' if 'audio_job_set_aside' in tables else ''
                for owner, raw in db.execute("SELECT job_id,manifest FROM audio_jobs WHERE state!='completed'" + aside):
                    other = json.loads(raw)
                    for source in other.get('sources') or []:
                        if isinstance(source, dict):add(source.get('path'), 'job', owner)
                    cover = other.get('cover')
                    if isinstance(cover, dict):add(cover.get('path'), 'job', owner)
                if 'reacquire_markers' in tables:
                    for (snapshot,) in db.execute("SELECT snapshot FROM reacquire_markers WHERE state!='archived'"):
                        for member in (json.loads(snapshot) or {}).get('members') or []:
                            if isinstance(member, dict):add(member.get('path'), 'reacquire', None)
                self.paths, self.token = paths, token
            return {name for name in wanted if any(kind == 'reacquire' or
                    kind == 'candidate' and owner != candidate_id or kind == 'job' and owner != job_id
                    for kind, owner in self.paths.get(name, ()))}
