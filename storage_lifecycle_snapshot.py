"""Installer-only, native-frozen SQLite tuples; originals are never queried.

The RAW closed tuple includes WAL/SHM. SQLite Backup is run on that private
tuple, then only its standalone backup is opened immutable. This is not an
online/main-only database copy or authority to relocate a catalog.
"""
import contextlib
from contextvars import ContextVar
import os
from pathlib import Path
import sqlite3
import uuid

from native_io import DirectoryBoundary,VerifiedFile
from source_cleanup import single_stream

_ACTIVE=ContextVar('books_installer_frozen_sqlite',default={})


def _temp():
    import storage_lifecycle as life
    value=os.environ.get('BOOKS_WORK_TEMP')
    if value is None:
        value=os.environ.get('TEMP');life._need(value and value==os.environ.get('TMP'),'temporary_work_not_configured')
    else:
        life._need(os.environ.get('TEMP')==value and os.environ.get('TMP')==value,'temporary_work_not_configured')
    root=life._absolute(value);life._local(root)
    life._need(root.is_dir(),'temporary_work_unavailable',root)
    return root


@contextlib.contextmanager
def frozen_catalog(database):
    import storage_lifecycle as life
    from runtime_disposition_owners import support_dispositions
    database=life._absolute(str(database));key=os.path.normcase(str(database))
    active=_ACTIVE.get()
    if key in active:
        yield active[key];return
    root=_temp();token=uuid.uuid4().hex
    clone=root/('books-sqlite-'+token+'.sqlite3');backup=root/('books-sqlite-'+token+'-closed.sqlite3')
    suffixes=('', '-wal', '-shm', '-journal')
    copies=[Path(str(base)+suffix) for base in (clone,backup) for suffix in suffixes]
    source_paths=[Path(str(database)+suffix) for suffix in suffixes]
    owner_path=Path(str(database)+'.lock')
    with contextlib.ExitStack() as stack:
        stack.enter_context(DirectoryBoundary(root.anchor,root))
        stack.enter_context(DirectoryBoundary(database.anchor,database.parent))
        if not owner_path.exists():life._write_new(owner_path,b'')
        owner=stack.enter_context(VerifiedFile(owner_path,writable=True));single_stream(owner_path)
        life._need(owner.facts()['links']==1,'in_use',owner_path)
        pinned=[];present={str(path):path.exists() for path in source_paths}
        for source in source_paths:
            if not present[str(source)]:continue
            held=stack.enter_context(VerifiedFile(source));single_stream(source)
            life._need(held.facts()['links']==1,'ownership_not_confirmed',source)
            pinned.append((source,held,held.facts(),held.sha256()))
        life._need(pinned and pinned[0][0]==database,'catalog_unavailable',database)
        with support_dispositions(root,[str(p) for p in copies]) as context:
            try:
                for source,held,facts,sha in pinned:
                    target=Path(str(clone)+str(source)[len(str(database)):])
                    produced=life._write_new_chunks(target,held.chunks())
                    life._need(produced['sha256']==sha,'snapshot_copy_changed',source)
                # A real catalog may be close to a GiB. Neither its raw copy
                # nor its standalone backup is accumulated in Python memory.
                life._write_new(backup,b'')
                with contextlib.closing(sqlite3.connect(str(clone),timeout=1)) as raw,contextlib.closing(sqlite3.connect(str(backup),timeout=1)) as clean:
                    raw.execute('PRAGMA temp_store=MEMORY');clean.execute('PRAGMA temp_store=MEMORY')
                    raw.backup(clean)
                for source,held,facts,sha in pinned:
                    held.refresh()
                    life._need(held.facts()==facts and held.sha256()==sha,'snapshot_source_changed',source)
                    single_stream(source)
                life._need(all(path.exists()==present[str(path)] for path in source_paths),
                           'snapshot_source_changed',database)
                # No source SQL connection exists at or after this census.
                marker=_ACTIVE.set(dict(active,**{key:backup}))
                try:yield backup
                finally:_ACTIVE.reset(marker)
                for source,held,facts,sha in pinned:
                    held.refresh()
                    life._need(held.facts()==facts and held.sha256()==sha,'snapshot_source_changed',source)
                life._need(all(path.exists()==present[str(path)] for path in source_paths),
                           'snapshot_source_changed',database)
            finally:
                for path in reversed(copies):
                    if path.exists():
                        with VerifiedFile(path,delete=True) as held:
                            single_stream(path);held.dispose()


@contextlib.contextmanager
def frozen_connection(database):
    with frozen_catalog(database) as snapshot:
        with contextlib.closing(sqlite3.connect(snapshot.as_uri()+'?mode=ro&immutable=1',uri=True,timeout=1)) as db:
            db.execute('PRAGMA query_only=ON');db.execute('PRAGMA temp_store=MEMORY')
            yield db
