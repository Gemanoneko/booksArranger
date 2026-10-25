"""Persistent incremental inventory. Source roots are opened read-only."""
import json
import os
from pathlib import Path
import sqlite3
import threading
import datetime
from metadata import AUDIO, EBOOK, ScanStopped, read_metadata, propose, future_audio_tags
import groups
from source_config import normalize_sources, contains as source_contains

DEFAULT_ROOTS = {'Audiobooks': r'Z:\Audiobooks', 'Podcasts': r'Z:\Audiobooks\Podcasts', 'Ebooks': r'Y:\Books\Books'}

def fresh_stat(path):
    """Fingerprint the opened source, without reading or modifying its contents."""
    with open(path, 'rb') as source:
        return os.fstat(source.fileno())

def _same_source(before, after):
    if (before.st_size, before.st_mtime_ns, before.st_dev, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_dev, after.st_ino):
        raise OSError('File changed during read; try a fresh scan after it finishes arriving; '
            f'before size={before.st_size}, modified_ns={before.st_mtime_ns}, identity={before.st_dev}:{before.st_ino}; '
            f'after size={after.st_size}, modified_ns={after.st_mtime_ns}, identity={after.st_dev}:{after.st_ino}')

def _has_retirements(connection):
    return bool(connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_retirements'").fetchone())

def _retired_source(connection, root, path):
    if not _has_retirements(connection):return False
    return bool(connection.execute("""SELECT 1 FROM source_retirements r JOIN files f ON f.root=r.root AND f.path=r.path
        WHERE r.root=? AND r.path=? AND r.state='removed' AND r.size=f.size AND f.error='' AND f.missing=0
          AND r.modified=CAST(f.modified AS TEXT) LIMIT 1""",(root,path)).fetchone())

def _supersede_retirement(connection,root,path):
    if _has_retirements(connection):
        connection.execute("UPDATE source_retirements SET state='superseded' WHERE root=? AND path=? AND state='removed'",(root,path))

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

_ENSURED=set();_ENSURED_LOCK=threading.Lock()

def _catalog_identity(database):
    """(path, volume, file index) of an existing catalog file; None when it cannot be read."""
    try:
        value=os.stat(database)
        return (os.path.normcase(os.path.abspath(str(database))),value.st_dev,value.st_ino)
    except (OSError,TypeError,ValueError):return None

def connect(database, timeout=10):
    connection = sqlite3.connect(database, timeout=timeout, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    # The book list and status open hundreds of connections per read; WAL mode and the base tables are
    # persistent, so they are ensured once per catalog file (a replaced file has a new identity).
    identity=_catalog_identity(database)
    if identity is not None and identity in _ENSURED:
        try:
            connection.execute('PRAGMA busy_timeout='+str(int(timeout*1000)))
            # The schema is read for any statement anyway; a missing base table falls back to the full setup.
            if connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('jobs','queue','files','scan_outcomes')").fetchone()[0]==4:
                return connection
        except BaseException:
            connection.close()
            raise
    try:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA busy_timeout='+str(int(timeout*1000)))
        connection.executescript('''
      CREATE TABLE IF NOT EXISTS jobs(root TEXT PRIMARY KEY, label TEXT, generation INTEGER,
        state TEXT, checked INTEGER DEFAULT 0, reused INTEGER DEFAULT 0, errors INTEGER DEFAULT 0, current TEXT DEFAULT '');
      CREATE TABLE IF NOT EXISTS queue(root TEXT, generation INTEGER, path TEXT, directory INTEGER,
        state TEXT DEFAULT 'pending', PRIMARY KEY(root,generation,path));
      CREATE TABLE IF NOT EXISTS files(root TEXT, path TEXT, size INTEGER, modified INTEGER,
        seen INTEGER, kind TEXT, arrival INTEGER, metadata TEXT, error TEXT DEFAULT '', missing INTEGER DEFAULT 0,
        review TEXT DEFAULT '', PRIMARY KEY(root,path));
      CREATE TABLE IF NOT EXISTS scan_outcomes(root TEXT, generation INTEGER, path TEXT,
        directory INTEGER, outcome TEXT, error TEXT, time TEXT, details TEXT DEFAULT '',
        PRIMARY KEY(root,generation,path));
    ''')
        connection.commit()
    except BaseException:
        connection.close()
        raise
    identity=_catalog_identity(database)
    if identity is not None:
        with _ENSURED_LOCK:_ENSURED.add(identity)
    return connection

def inside(path, root):
    try:
        return os.path.normcase(os.path.commonpath([os.path.abspath(path), os.path.abspath(root)])) == os.path.normcase(os.path.abspath(root))
    except ValueError:
        return False

def gone(root, path):
    """The folder that proves path was removed: the nearest folder, at or below the source root, that lists now without
    the next name toward path. None when it cannot be shown: the name is still listed, a folder cannot be read, or the
    source root itself cannot be listed (a dropped share is never "gone", so nothing is marked missing because of it)."""
    # Queue paths are the scanner's own absolute paths: the folder returned is spelled as its queue task is.
    top=os.path.normcase(os.path.abspath(root));current=str(path)
    while True:
        parent=os.path.dirname(current)
        if parent==current or not inside(parent,root):return None
        try:
            with os.scandir(parent) as entries:names={os.path.normcase(entry.name) for entry in entries}
        except FileNotFoundError:
            if os.path.normcase(os.path.abspath(parent))==top:return None
            current=parent;continue
        except OSError:return None
        return None if os.path.normcase(os.path.basename(current)) in names else parent

class Inventory:
    def __init__(self, database, roots=None, reader=read_metadata, *, audiobook_sources=None, output_root=None):
        # Before directory/schema creation or resetting saved running tasks.
        from publication_locations import require_no_pending_moves
        require_no_pending_moves(database)
        self.database = str(database)
        self.roots = dict(roots or DEFAULT_ROOTS)
        self.source_config = normalize_sources(self.roots, audiobook_sources, output_root)
        self.audiobook_sources = self.source_config.audiobook_sources
        self.output_root = self.source_config.audiobook_output_root
        if any(source_contains(self.database, root) for root in self.all_source_roots()) or (self.output_root and source_contains(self.database,self.output_root)):
            raise ValueError('Keep the inventory database outside source libraries')
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.reader = reader
        self.stop_event = threading.Event()
        self.worker = None
        self.group_lock=threading.RLock()
        self.last_error = ''
        with connect(self.database) as connection:
            # A prior process may have died while a task was running.
            connection.execute("UPDATE queue SET state='pending' WHERE state='running'")
            connection.execute("UPDATE jobs SET state='stopped' WHERE state='scanning'")
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='book_groups'").fetchone():
                groups.setup_group_member_index(connection)

    def source_roots(self, label='Audiobooks'):
        return self.audiobook_sources if label=='Audiobooks' else (self.roots[label],)

    def all_source_roots(self):
        return tuple(dict.fromkeys((*self.audiobook_sources, *self.roots.values())))

    def source_root_for_path(self, path, label='Audiobooks'):
        if not os.path.isabs(path):raise ValueError('Source paths must be absolute')
        normalize_sources(self.roots,self.audiobook_sources,self.output_root)
        matches=[root for root in self.source_roots(label) if source_contains(path,root)]
        if len(matches)!=1 or self._excluded_path(path,label):
            raise ValueError('Path is outside the configured source boundary')
        return matches[0]

    def source_root_for_candidate(self, identity):
        with connect(self.database) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='book_groups'").fetchone():
                raise ValueError('Candidate inventory is unavailable')
            row=db.execute('SELECT root FROM book_groups WHERE id=? AND superseded=0',(identity,)).fetchone()
            if row is None or row['root'] not in self.audiobook_sources:
                raise ValueError('Candidate is outside configured audiobook sources')
            return row['root']

    def _excluded_path(self,path,label):
        return bool(label=='Audiobooks' and ((self.roots.get('Podcasts') and source_contains(path,self.roots['Podcasts'])) or
                    (self.output_root and source_contains(path,self.output_root))))

    def status(self, label):
        values=[self.source_status(root) for root in self.source_roots(label)]
        if len(values)==1:return values[0]
        states=[value['state'] for value in values]
        state=next((name for name in ('scanning','failed','offline','stopped','completed with errors','not scanned') if name in states),'completed')
        return {'state':state, **{name:sum(value.get(name,0) for value in values) for name in
                ('checked','reused','errors','count','pending','unresolved_errors')},
                'current':next((value.get('current','') for value in values if value.get('current')),''),
                'scan_issues':[issue for value in values for issue in value['scan_issues']],
                'sources':[{'source_root':root,**value} for root,value in zip(self.source_roots(label),values)]}

    def source_status(self, root):
        if root not in self.all_source_roots():raise ValueError('Unknown configured source')
        failure=getattr(self,'_catalog_failures',{}).get(root)
        ended=not self.worker or not self.worker.is_alive()
        matching=bool(failure and failure['root']==root and ended)
        try:
            with connect(self.database) as connection:
                row=connection.execute('SELECT * FROM jobs WHERE root=?',(root,)).fetchone()
                count=connection.execute('SELECT count(*) FROM files WHERE root=?',(root,)).fetchone()[0]
                pending=connection.execute("SELECT count(*) FROM queue WHERE root=? AND state IN ('pending','running')",(root,)).fetchone()[0]
                # A read error is a file with an error that is not marked gone (Judy, MissingFiles UX 2026-10-24): a gone file
                # cannot be re-read, and only a scan that finished with no errors marks one gone.
                unresolved=connection.execute("SELECT count(*) FROM files WHERE root=? AND error<>'' AND missing=0",(root,)).fetchone()[0]
                issues=connection.execute("SELECT path,error,time FROM scan_outcomes WHERE root=? AND generation=? AND directory=1 AND outcome='error' ORDER BY path",(root,row['generation'] if row else 0)).fetchall()
        except sqlite3.Error as error:
            if matching:
                from catalog_contention import CatalogHold
                raise CatalogHold('Catalog status unknown: saved scan generation could not be read; failure checkpoint is not durable') from error
            raise
        extra={'count':count,'pending':pending,'unresolved_errors':unresolved,'scan_issues':[dict(issue) for issue in issues]}
        result=dict(row)|extra if row else {'state':'not scanned','checked':0,'reused':0,'errors':0,'current':''}|extra
        if matching and row and row['generation']==failure['generation'] and row['state']=='scanning':
            result.update(state='failed',current=failure['message'],failure_durable=False,catalog_hold={'root':root,'generation':failure['generation'],'reason':failure['message']})
        return result

    def _outcome(self, connection, root, generation, path, directory, error='', details=''):
        connection.execute('INSERT OR REPLACE INTO scan_outcomes VALUES(?,?,?,?,?,?,?,?)',
            (root,generation,path,int(directory),'error' if error else 'success',error,
             datetime.datetime.now(datetime.timezone.utc).isoformat(),details))

    def launch(self, label, resume=False):
        self._launch_sources(label,self.source_roots(label),resume)

    def launch_source(self,root,resume=False):
        labels=[label for label in self.roots if root in self.source_roots(label)]
        if len(labels)!=1:raise ValueError('Unknown or ambiguous configured source')
        self._launch_sources(labels[0],(root,),resume)

    def _launch_sources(self,label,roots,resume):
        if self.worker and self.worker.is_alive():
            raise ValueError('A scan is already running; stop it before starting another')
        normalize_sources(self.roots,self.audiobook_sources,self.output_root)
        from catalog_contention import write
        def prepare(connection):
          plans=[]
          saved={root:connection.execute('SELECT * FROM jobs WHERE root=?',(root,)).fetchone() for root in roots}
          resumable={'stopped','offline','failed'}
          if resume and not any(job and job['state'] in resumable for job in saved.values()):
              raise ValueError('No stopped scan to resume')
          for root in roots:
            job=saved[root]
            if resume and job:
                if job and job['state'] in {'completed','completed with errors'}:
                    continue
                if job['state'] not in resumable:
                    raise ValueError('No stopped scan to resume')
                generation = job['generation']
            else:
                if job and job['state'] in resumable:
                    raise ValueError('Use Resume scanning to continue saved progress')
                generation = (job['generation'] if job else 0) + 1
                connection.execute('DELETE FROM queue WHERE root=?', (root,))
                connection.execute('INSERT OR REPLACE INTO jobs(root,label,generation,state) VALUES(?,?,?,?)', (root,label,generation,'scanning'))
                connection.execute('INSERT INTO queue(root,generation,path,directory) VALUES(?,?,?,1)', (root,generation,root))
            connection.execute("UPDATE jobs SET state='scanning' WHERE root=?", (root,))
            plans.append((label,root,generation))
          return plans
        # Only SQL is replayed on contention. A saved source keeps its generation
        # and queue; newly configured sources start once in the same transaction.
        plans=write(self.database,prepare)
        if not plans:raise ValueError('No stopped scan to resume')
        self.stop_event.clear()
        self.last_error = ''
        self.worker = threading.Thread(target=self._run_sources, args=(plans,), daemon=True)
        self.worker.start()

    def _run_sources(self,plans):
        from catalog_contention import remember_busy_failure,write
        for label,root,generation in plans:
            if self.stop_event.is_set():
                def stopped(db):db.execute("UPDATE jobs SET state='stopped' WHERE root=? AND generation=? AND state='scanning'",(root,generation))
                try:write(self.database,stopped)
                except Exception as error:
                    self.last_error='Scan stop checkpoint could not be saved: '+str(error)
                    remember_busy_failure(self,root,generation,error,self.last_error)
            else:self._run(label,root,generation)

    def stop(self):
        self.stop_event.set()

    def _run(self, label, root, generation):
        from catalog_contention import CatalogHold,file_token,remember_busy_failure,scan_guard,write
        import contextlib,reacquire_sources
        connection=None;task=None;expected=None
        failures=getattr(self,'_catalog_failures',{});failures.pop(root,None);self._catalog_failures=failures
        reacquire_lease=contextlib.ExitStack()
        def pending(db):
            row=db.execute('SELECT generation,state FROM jobs WHERE root=?',(root,)).fetchone()
            if not row or row['generation']!=generation or row['state']!='scanning':return False
            if task:db.execute("UPDATE queue SET state='pending' WHERE root=? AND generation=? AND path=? AND state='running'",(root,generation,task['path']))
            return True
        try:
            connection=connect(self.database)
            source_boundary=reacquire_lease.enter_context(reacquire_sources.root_scan_lease(connection,root))
            if not os.path.isdir(root):
                def offline(db):
                    scan_guard(db,root,generation)
                    db.execute("UPDATE jobs SET state='offline',current=? WHERE root=? AND generation=?",('Root unavailable; saved results preserved',root,generation))
                write(self.database,offline,self.stop_event);return
            while not self.stop_event.is_set():
                row=connection.execute("SELECT * FROM queue WHERE root=? AND generation=? AND state='pending' ORDER BY path LIMIT 1",(root,generation)).fetchone()
                task=dict(row) if row else None
                if not task:
                    errors=connection.execute('SELECT errors FROM jobs WHERE root=? AND generation=?',(root,generation)).fetchone()
                    if errors is None:raise CatalogHold('Scan generation changed before completion')
                    errors=errors[0]
                    if not errors:
                        # Native/source reconciliation is deliberately ONCE, outside DB replay.
                        reacquire_sources.reconcile_scan(connection,self,root,generation,source_boundary)
                    def complete(db):
                        scan_guard(db,root,generation)
                        if db.execute("SELECT 1 FROM queue WHERE root=? AND generation=? AND state IN ('pending','running') LIMIT 1",(root,generation)).fetchone():raise CatalogHold('Scan queue changed before completion')
                        fresh=db.execute('SELECT errors FROM jobs WHERE root=? AND generation=?',(root,generation)).fetchone()[0]
                        if fresh!=errors:raise CatalogHold('Scan errors changed before completion')
                        if not errors:
                            if _has_retirements(db):
                                db.execute("""UPDATE files SET missing=(seen<>? AND NOT EXISTS(
                                    SELECT 1 FROM source_retirements r WHERE r.root=files.root AND r.path=files.path AND r.state='removed' AND r.size=files.size AND r.modified=CAST(files.modified AS TEXT))) WHERE root=?""",(generation,root))
                            else:db.execute('UPDATE files SET missing=(seen<>?) WHERE root=?',(generation,root))
                        db.execute('UPDATE jobs SET state=?,current=? WHERE root=? AND generation=?',('completed with errors' if errors else 'completed','',root,generation))
                    write(self.database,complete,self.stop_event);return
                def claim(db):
                    scan_guard(db,root,generation)
                    fresh=db.execute('SELECT * FROM queue WHERE root=? AND generation=? AND path=?',(root,generation,task['path'])).fetchone()
                    if not fresh or dict(fresh)!=task:raise CatalogHold('Scan task changed before admission')
                    db.execute("UPDATE queue SET state='running' WHERE root=? AND generation=? AND path=?",(root,generation,task['path']))
                    db.execute('UPDATE jobs SET current=? WHERE root=? AND generation=?',(task['path'],root,generation))
                write(self.database,claim,self.stop_event)
                path=task['path'];expected=file_token(connection,root,path)
                try:
                    if task['directory']:self._directory(connection,label,root,generation,path)
                    else:self._file(connection,label,root,generation,path)
                except (ScanStopped,InterruptedError):raise
                except (CatalogHold,sqlite3.Error):raise
                except (OSError,ValueError,TimeoutError) as error:
                    # Database/CAS exceptions never enter this source-read error branch.
                    message=str(error);kind,arrival=self._classify(label,root,path) if not task['directory'] else ('',False)
                    def source_error(db):
                        scan_guard(db,root,generation,path,task['directory'])
                        if file_token(db,root,path)!=expected:raise CatalogHold('Catalog evidence changed during source error; review preserved')
                        db.execute("UPDATE queue SET state='error' WHERE root=? AND generation=? AND path=?",(root,generation,path))
                        db.execute('UPDATE jobs SET errors=errors+1,current=? WHERE root=? AND generation=?',(path+': '+message,root,generation))
                        self._outcome(db,root,generation,path,task['directory'],message)
                        if not task['directory']:
                            db.execute('UPDATE jobs SET checked=checked+1 WHERE root=? AND generation=?',(root,generation))
                            changed=db.execute("UPDATE files SET error=?,review='' WHERE root=? AND path=?",(message,root,path))
                            if not changed.rowcount:db.execute("""INSERT INTO files(root,path,size,modified,seen,kind,arrival,metadata,error)
                              VALUES(?,?,0,0,?,?,?,?,?)""",(root,path,generation,kind,int(arrival),json.dumps({'notes':['File unavailable or changed during read; inspect before arranging']}),message))
                    write(self.database,source_error,self.stop_event)
            def stopped(db):
                if pending(db):db.execute("UPDATE jobs SET state='stopped' WHERE root=? AND generation=? AND state='scanning'",(root,generation))
            write(self.database,stopped)
        except (ScanStopped,InterruptedError):
            try:
                def stopped(db):
                    if pending(db):db.execute("UPDATE jobs SET state='stopped' WHERE root=? AND generation=? AND state='scanning'",(root,generation))
                write(self.database,stopped)
            except Exception as error:
                self.last_error='Scan stop checkpoint could not be saved: '+str(error)
                remember_busy_failure(self,root,generation,error,self.last_error)
        except Exception as error:
            try:
                if connection is not None:connection.rollback()
            except sqlite3.Error:pass
            self.last_error=str(error)
            def failed(db):
                if pending(db):db.execute("UPDATE jobs SET state='failed',current=? WHERE root=? AND generation=? AND state='scanning'",(str(error),root,generation))
            try:write(self.database,failed)
            except Exception as save_error:
                self.last_error=str(error)+'; failure checkpoint could not be saved: '+str(save_error)
                remember_busy_failure(self,root,generation,save_error,self.last_error)
        finally:
            try:reacquire_lease.close()
            finally:
                if connection is not None:connection.close()

    def _directory(self, connection, label, root, generation, path):
        from catalog_contention import CatalogHold,file_token,scan_write
        def preserve(tree,details=None):
            observed={row['path']:file_token(connection,root,row['path']) for row in connection.execute('SELECT path FROM files WHERE root=?',(root,)).fetchall() if source_contains(row['path'],tree)}
            def persist(db):
                for name,expected in observed.items():
                    if file_token(db,root,name)!=expected:raise CatalogHold('Catalog source changed during directory read; task remains pending')
                    db.execute('UPDATE files SET seen=? WHERE root=? AND path=?',(generation,root,name))
                if details:self._outcome(db,root,generation,path,True,details=details)
            scan_write(self,root,generation,path,persist,finish=details is not None,task_directory=True)
        if self._excluded_path(path,label):
            preserve(path,'Excluded output or separate library tree');return
        if self.source_root_for_path(path,label)!=root:raise ValueError('Saved directory belongs to another source boundary')
        owned=set()
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='owned_artifacts'").fetchone():
            owned={os.path.normcase(r['path']) for r in connection.execute("SELECT path FROM owned_artifacts WHERE kind IN ('temporary','recovery','output')")}
        if 'planned_destination' in {row[1] for row in connection.execute('PRAGMA table_info(output_relocations)')}:
            owned.update(os.path.normcase(row[0]) for row in connection.execute("SELECT planned_destination FROM output_relocations WHERE planned_destination<>''"))
        try:listing=os.scandir(path)
        except FileNotFoundError as error:
            # A folder the scan queued that is gone before its listing (Sergei deletes torrent folders outside the app):
            # the same quiet skip as a gone file, on the same evidence (see _vanished).
            return self._vanished(root,generation,path,lambda operation:scan_write(self,root,generation,path,operation,task_directory=True),error,directory=True)
        with listing as entries:
            for entry in entries:
                if self.stop_event.is_set():raise ScanStopped()
                if entry.is_symlink() or (hasattr(os.path,'isjunction') and os.path.isjunction(entry.path)):continue
                if self._excluded_path(entry.path,label):preserve(entry.path);continue
                if os.path.normcase(entry.path) in owned:
                    name=entry.path;expected=file_token(connection,root,name)
                    def preserve_owned(db):
                        if file_token(db,root,name)!=expected:raise CatalogHold('Owned source evidence changed; scan task remains pending')
                        db.execute('UPDATE files SET seen=? WHERE root=? AND path=?',(generation,root,name))
                    scan_write(self,root,generation,path,preserve_owned,finish=False,task_directory=True);continue
                directory=entry.is_dir(follow_symlinks=False)
                if directory or entry.is_file(follow_symlinks=False):
                    name=entry.path
                    prior=connection.execute('SELECT * FROM queue WHERE root=? AND generation=? AND path=?',(root,generation,name)).fetchone()
                    prior=dict(prior) if prior else None
                    def enqueue(db):
                        row=db.execute('SELECT * FROM queue WHERE root=? AND generation=? AND path=?',(root,generation,name)).fetchone()
                        if (dict(row) if row else None)!=prior:raise CatalogHold('Directory queue changed; captured entry was not applied')
                        db.execute('INSERT OR IGNORE INTO queue(root,generation,path,directory) VALUES(?,?,?,?)',(root,generation,name,int(directory)))
                    scan_write(self,root,generation,path,enqueue,finish=False)
        scan_write(self,root,generation,path,lambda db:self._outcome(db,root,generation,path,True),task_directory=True)

    def _vanished(self, root, generation, path, save, error, directory=False):
        """A file or folder listed by this scan that is gone before its read or listing (Senua's 0.22.0 final review, N13:
        deleted by Delete book, or by Sergei outside the app, a whole torrent folder included). Skipped quietly: no error
        row, no catalog row, no failed scan; a catalogued file is not seen, so the completed scan marks it missing. Only
        on positive evidence (gone): otherwise the read error stands as before, and a source root is never gone. The
        proving folder is listed again once in this scan, so a renamed file's or folder's new name is still catalogued by
        it, not one scan later."""
        folder=gone(root,path)
        if folder is None:raise error
        relisted=self.__dict__.setdefault('_relisted',set());key=(root,generation,os.path.normcase(folder))
        again=key not in relisted;relisted.add(key)
        def persist(db):
            self._outcome(db,root,generation,path,directory,details='Gone before it was read')
            if again:db.execute("UPDATE queue SET state='pending' WHERE root=? AND generation=? AND path=? AND directory=1 AND state='done'",(root,generation,folder))
        save(persist)

    def _file(self, connection, label, root, generation, path):
        from catalog_contention import CatalogHold,file_token,scan_write
        if self.stop_event.is_set():raise ScanStopped()
        expected=file_token(connection,root,path)
        def save(operation):return scan_write(self,root,generation,path,operation,expected,task_directory=False)
        def excluded(details):
            def persist(db):
                db.execute('UPDATE files SET seen=? WHERE root=? AND path=?',(generation,root,path))
                self._outcome(db,root,generation,path,False,details=details)
            save(persist)
        if self._excluded_path(path,label):
            excluded('Configured output or separate library excluded from discovery');return
        if self.source_root_for_path(path,label)!=root:raise ValueError('Saved file belongs to another source boundary')
        if expected['relocations']:
            excluded('Exact relocation destination excluded from discovery');return
        if any(row['kind'] in ('temporary','recovery','output') for row in expected['owned']):
            excluded('Exact owned output/recovery/temporary asset excluded from discovery');return
        retired=_retired_source(connection,root,path)
        try:before=fresh_stat(path)
        except FileNotFoundError as error:
            if not retired:return self._vanished(root,generation,path,save,error)
            def persist_retired(db):
                db.execute("UPDATE files SET missing=0,error='' WHERE root=? AND path=?",(root,path))
                db.execute('UPDATE jobs SET checked=checked+1 WHERE root=? AND generation=?',(root,generation))
                self._outcome(db,root,generation,path,False,details='Source intentionally retired; recovery provenance retained')
            save(persist_retired);return
        old=expected['file']
        unchanged=old and old['size']==before.st_size and old['modified']==before.st_mtime_ns and not old['error'] and not retired
        import reacquire_sources
        if unchanged and not reacquire_sources.marked_path(connection,root,path):
            try:again=fresh_stat(path)
            except FileNotFoundError as error:return self._vanished(root,generation,path,save,error)
            _same_source(before,again)
            def persist_reused(db):
                db.execute('UPDATE files SET seen=?,missing=0 WHERE root=? AND path=?',(generation,root,path))
                db.execute('UPDATE jobs SET checked=checked+1,reused=reused+1 WHERE root=? AND generation=?',(root,generation))
                self._outcome(db,root,generation,path,False)
            save(persist_reused);return
        kind,arrival=self._classify(label,root,path)
        metadata,error={},''
        try:
            metadata=self.reader(path,kind,self.stop_event)
            # Existing source guards and the captured output token are not replayed.
            output=next((row for row in expected['owned'] if row['kind']=='output'),None)
            if output:
                import hashlib
                digest=hashlib.sha256()
                with open(path,'rb') as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):
                        if self.stop_event.is_set():raise ScanStopped()
                        digest.update(block)
                if before.st_size!=output['size'] or digest.hexdigest()!=output['sha256']:
                    raise ValueError('Created audiobook changed; inspect the recorded output')
                metadata['arranger_output']=output['job_id']
        except (ScanStopped,InterruptedError,CatalogHold,sqlite3.Error):raise
        except Exception as issue:
            error=str(issue)
            metadata={'notes':['Metadata read failed; source file untouched'],'title':'','author':''}
        try:after=fresh_stat(path)
        except FileNotFoundError as gone_error:return self._vanished(root,generation,path,save,gone_error)
        _same_source(before,after)
        encoded=json.dumps(metadata,ensure_ascii=False)
        def persist_read(db):
            db.execute("""INSERT OR REPLACE INTO files(root,path,size,modified,seen,kind,arrival,metadata,error,missing,review)
              VALUES(?,?,?,?,?,?,?,?,?,0,'')""",(root,path,before.st_size,before.st_mtime_ns,generation,kind,int(arrival),encoded,error))
            db.execute('UPDATE jobs SET checked=checked+1,errors=errors+? WHERE root=? AND generation=?',(int(bool(error)),root,generation))
            self._outcome(db,root,generation,path,False,error)
            if not error:_supersede_retirement(db,root,path)
        save(persist_read)

    def refresh_candidate_sources(self,label,identity,revision,stop=None,*,force=False,max_members=500,max_bytes=4*1024*1024*1024,deadline_seconds=120):
        """Freshen one unprotected candidate's observed sources without a scan.

        No discovery, grouping, review reset, counter/outcome changes or source
        writes. The caller retrieves the new group revision and researches again.
        """
        import contextlib,hashlib,time
        from native_io import DirectoryBoundary,VerifiedFile,BoundaryError,ordinary
        old_revision=revision;old_fingerprint='';paths=[]
        def result(state,reason='',code='',receipts=None,changed=None):
            return {'state':state,'reason':reason,'hold_code':code,'old_revision':old_revision,
                    'old_fingerprint':old_fingerprint,'observed_paths':paths,
                    'source_receipts':receipts or [],'refreshed_paths':changed or []}
        if label!='Audiobooks' or label not in self.roots:return result('held','Only audiobook candidates support source refresh','unsupported_library')
        if type(revision) is not int or revision<1 or type(force) is not bool:
            return result('held','Candidate refresh arguments are invalid','invalid_request')
        if type(max_members) is not int or not 1<=max_members<=500 or type(max_bytes) is not int or not 1<=max_bytes<=4*1024*1024*1024:
            return result('held','Candidate refresh bounds are invalid','invalid_request')
        if isinstance(deadline_seconds,bool) or not isinstance(deadline_seconds,(int,float)) or not 0<deadline_seconds<=120:
            return result('held','Candidate refresh deadline is invalid','invalid_request')
        deadline=time.monotonic()+deadline_seconds
        class BoundedStop:
            def is_set(inner):return bool(stop is not None and stop.is_set()) or time.monotonic()>=deadline
        bounded=BoundedStop()
        def check():
            if bounded.is_set():raise ScanStopped()
        def table(db,name):return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone())
        def snapshot(db):
            if not table(db,'book_groups'):raise ValueError('Candidate inventory is unavailable')
            group=db.execute('SELECT * FROM book_groups WHERE root=? AND id=? AND superseded=0',(root,identity)).fetchone()
            if not group or group['revision']!=revision:raise ValueError('Candidate changed before source refresh')
            evidence=json.loads(group['evidence']);members=evidence.get('members',[])
            member_paths=[member['path'] for member in members]
            if not members or len(members)>max_members or len(set(member_paths))!=len(member_paths):raise ValueError('Candidate member count is empty, duplicated or exceeds the refresh bound')
            if group['approved']:raise ValueError('Approved candidate source evidence is preserved')
            data={}
            if table(db,'automatic_manual_drafts') and db.execute(
                'SELECT 1 FROM automatic_manual_drafts WHERE id=? AND revision=? AND expires>?',
                (identity,revision,time.time())).fetchone():
                raise ValueError('Active browser editing lease is preserved; source refresh waits')
            if table(db,'candidate_context'):
                context=db.execute('SELECT * FROM candidate_context WHERE id=?',(identity,)).fetchone()
                if context:
                    data=json.loads(context['data'])
                    if data.get('metadata_approved') or data.get('automatic_pending') or data.get('manual_draft_active') or data.get('manual_note') or data.get('metadata_actor')=='user' or data.get('track_actor')=='user':
                        raise ValueError('Approved metadata or manual editing evidence is preserved')
            else:context=None
            automatic_unapproved=bool(context and context['revision']==revision and data.get('automatic_approval'))
            if group['review'] and not automatic_unapproved:raise ValueError('Manual or unclassified candidate review is preserved')
            marks=','.join('?' for _ in member_paths)
            arguments=(root,*member_paths)
            protected=db.execute(f"""SELECT 1 FROM book_groups g,json_each(g.evidence,'$.members') m
                WHERE g.root=? AND g.id<>? AND (g.approved<>0 OR g.review<>'')
                  AND json_extract(m.value,'$.path') IN ({marks}) LIMIT 1""",(root,identity,*member_paths)).fetchone()
            if protected:raise ValueError('Member belongs to another approved or reviewed candidate')
            if table(db,'audio_jobs'):
                job=db.execute(f"""SELECT 1 FROM audio_jobs j WHERE json_extract(j.manifest,'$.candidate_id')=?
                  OR EXISTS(SELECT 1 FROM json_each(j.manifest,'$.sources') s WHERE json_extract(s.value,'$.path') IN ({marks})) LIMIT 1""",(identity,*member_paths)).fetchone()
                if job:raise ValueError('Candidate or source has a durable conversion job; immutable job evidence is preserved')
            if table(db,'source_retirements') and db.execute(f'SELECT 1 FROM source_retirements WHERE root=? AND path IN ({marks}) LIMIT 1',arguments).fetchone():
                raise ValueError('Source retirement provenance is preserved')
            if table(db,'owned_artifacts') and db.execute(f'SELECT 1 FROM owned_artifacts WHERE path IN ({marks}) LIMIT 1',member_paths).fetchone():
                raise ValueError('App-owned output or recovery evidence is preserved')
            if 'planned_destination' in {row[1] for row in db.execute('PRAGMA table_info(output_relocations)')}:
                if db.execute(f'SELECT 1 FROM output_relocations WHERE planned_destination IN ({marks}) LIMIT 1',member_paths).fetchone():
                    raise ValueError('Relocation destination evidence is preserved')
            job=db.execute('SELECT * FROM jobs WHERE root=?',(root,)).fetchone()
            if job and job['state']=='scanning' or self.worker and self.worker.is_alive():raise ValueError('A library scan is active; source refresh waits')
            rows=[db.execute('SELECT * FROM files WHERE root=? AND path=?',(root,path)).fetchone() for path in member_paths]
            if any(row is None for row in rows):raise ValueError('Observed source is missing from the inventory')
            return dict(group),[dict(row) for row in rows],dict(job) if job else None,dict(context) if context else None
        try:root=self.source_root_for_candidate(identity)
        except ValueError as issue:return result('held',str(issue),'protected_or_changed')
        try:
            # 0.22.1 (backlog items 6-7): the catalog snapshot and the file reads take no group_lock, so Scan again no longer
            # queues behind a status computation or an approval. Only a write takes the lock, briefly, and it still writes
            # nothing unless the catalog is exactly the snapshot read here (compare-and-set below).
            with contextlib.ExitStack() as guards:
                check()
                with connect(self.database) as db:initial=snapshot(db)
                group,rows,job,context=initial;old_fingerprint=group['fingerprint'];paths=[row['path'] for row in rows]
                root_path=ordinary(root);updates=[];receipts=[];hashed_bytes=0
                for row in rows:
                    check();path=ordinary(row['path'])
                    if not inside(path,root_path) or row['kind']!='audiobook' or self.source_root_for_path(path,label)!=root:
                        raise BoundaryError('Source refresh must stay within exact observed audiobook members')
                    guards.enter_context(DirectoryBoundary(root_path,path.parent))
                    held=guards.enter_context(VerifiedFile(path));facts=held.facts();before=fresh_stat(path)
                    if facts['links']!=1:raise BoundaryError('Source refresh refuses a linked or ambiguous file')
                    changed=force or row['size']!=facts['size'] or row['modified']!=facts['modified'] or bool(row['error']) or bool(row['missing'])
                    receipt={'path':str(path),'size':facts['size'],'modified':str(facts['modified']),
                             'identity':{'dev':facts['dev'],'ino':facts['ino']},'sha256':None}
                    if changed:
                        if hashed_bytes+facts['size']>max_bytes:return result('held','Changed source bytes exceed the bounded refresh budget','budget_exceeded')
                        metadata=self.reader(str(path),row['kind'],bounded);check()
                        if not isinstance(metadata,dict):raise ValueError('Source metadata reader returned invalid evidence')
                        digest=hashlib.sha256()
                        for block in held.chunks():check();digest.update(block);hashed_bytes+=len(block)
                        _same_source(before,fresh_stat(path))
                        if len(json.dumps(metadata,ensure_ascii=False).encode('utf-8'))>4*1024*1024:
                            return result('held','Source metadata exceeds the bounded refresh budget','budget_exceeded')
                        receipt['sha256']=digest.hexdigest()
                        metadata=dict(metadata)
                        metadata['source_refresh']={'sha256':receipt['sha256'],'size':facts['size'],'modified':str(facts['modified']),
                                                    'identity':receipt['identity']}
                        updates.append((row,metadata,facts))
                    receipts.append(receipt)
                check()
                # Nothing changed on disk: a read transaction confirms the snapshot, with no write lock and no group_lock.
                with self.group_lock if updates else contextlib.nullcontext(),connect(self.database) as db:
                    db.execute('BEGIN IMMEDIATE' if updates else 'BEGIN')
                    if snapshot(db)!=initial:return result('held','Catalog or protected state changed during source refresh','catalog_changed')
                    for row,metadata,facts in updates:
                        db.execute("UPDATE files SET size=?,modified=?,metadata=?,error='',missing=0 WHERE root=? AND path=?",
                            (facts['size'],facts['modified'],json.dumps(metadata,ensure_ascii=False),root,row['path']))
                return result('refreshed' if updates else 'unchanged',receipts=receipts,changed=[row['path'] for row,_,_ in updates])
        except ScanStopped:
            return result('held','Source refresh cancelled' if stop is not None and stop.is_set() else 'Source refresh reached its time budget','cancelled' if stop is not None and stop.is_set() else 'budget_exceeded')
        except (OSError,BoundaryError) as issue:return result('held',str(issue),'source_unavailable')
        except (ValueError,KeyError,TypeError,sqlite3.Error) as issue:return result('held',str(issue),'protected_or_changed')

    def _classify(self,label,root,path):
        ext = Path(path).suffix.lower()
        kind = 'podcast' if label == 'Podcasts' and ext in AUDIO else 'audiobook' if label == 'Audiobooks' and ext in AUDIO else 'ebook' if label == 'Ebooks' and ext in EBOOK else 'companion'
        arrival = label == 'Ebooks' or (label == 'Audiobooks' and inside(path, os.path.join(root,'Unsorted')))
        return kind, arrival

    def rows(self, label, limit=1000, offset=0, search='', status='all', page=False):
        roots=self.source_roots(label)
        with connect(self.database) as connection:
            connection.execute('BEGIN')
            rows=[row for root in roots for row in self._rows_source(connection,root,search,status)]
        rows.sort(key=lambda row:(row['path'].casefold(),row['source_root']))
        result=rows[offset:offset+limit]
        return {'rows':result,'total':len(rows)} if page else result

    def _rows_source(self,connection,root,search,status):
        # Escape wildcard characters: searching a filename means literal substring.
        pattern = '%' + search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        values = connection.execute("SELECT * FROM files WHERE root=? AND path LIKE ? ESCAPE '\\' ORDER BY path", (root,pattern)).fetchall()
        failures={item['path']:dict(item) for item in connection.execute("SELECT path,error,time FROM scan_outcomes WHERE root=? AND outcome='error' ORDER BY generation",(root,))}
        reviewed = connection.execute("SELECT path,kind,metadata,review FROM files WHERE root=? AND kind='ebook' AND review<>'' AND missing=0", (root,)).fetchall()
        existing = {os.path.normcase(os.path.normpath(item[0])):item[0] for item in connection.execute('SELECT path FROM files WHERE root=? AND missing=0',(root,))}
        destinations = {}
        for candidate in reviewed:
            preview = propose(candidate['path'],root,'ebook',json.loads(candidate['metadata']),json.loads(candidate['review']))
            if preview['path']:
                key = os.path.normcase(os.path.normpath(preview['path']))
                destinations.setdefault(key,[]).append(candidate['path'])
        rows = []
        for source in values:
            row = dict(source)
            row['source_root']=root
            row['metadata'] = json.loads(row['metadata'])
            row['review'] = json.loads(row['review']) if row['review'] else None
            row['preview'] = propose(row['path'],root,row['kind'],row['metadata'],row['review'])
            if row['kind'] == 'ebook' and row['preview']['path']:
                destination = os.path.normcase(os.path.normpath(row['preview']['path']))
                occupied = existing.get(destination)
                if len(destinations.get(destination,[])) > 1 or (occupied and occupied != row['path']):
                    row['preview'] = {'path':row['preview']['path'],'confidence':'Collision review','reason':'Destination is shared by another catalog file; preserve all editions and resolve before future arranging'}
            if row['missing'] or row['error']:
                # Gone wins over an old error: the error text stays in the catalog, not on screen (MissingFiles UX 2026-10-24).
                row['preview'] = ({'path': '', 'confidence': 'No longer found', 'reason': 'Not found in the last complete scan.'} if row['missing'] else
                                  {'path': '', 'confidence': 'Read error', 'reason': row['error']})
            row['error_time']=failures.get(row['path'],{}).get('time','')
            row['saved_snapshot']=bool(row['error'] and row['metadata'].get('method'))
            if row['kind'] == 'audiobook':
                row['tag_preview'] = future_audio_tags(row['metadata'],row['review'] if not row['missing'] and not row['error'] else None)
            rows.append(row)
        filters={'all':lambda row:True,'errors':lambda row:bool(row['error']) and not row['missing'],
            'review':lambda row:row['preview']['confidence']=='Needs review',
            'preview':lambda row:bool(row['preview']['path']) and not row['error'] and not row['missing'],
            'missing':lambda row:bool(row['missing'])}
        if status not in filters:raise ValueError('Unknown inventory status')
        rows=[row for row in rows if filters[status](row)]
        return rows

    def save_review(self, root, path, review, size=None, modified=None):
        with connect(self.database) as connection:
            clause = ' AND size=? AND modified=?' if size is not None else ''
            arguments = (json.dumps(review,ensure_ascii=False),root,path) + ((size,modified) if size is not None else ())
            result = connection.execute('UPDATE files SET review=? WHERE root=? AND path=?' + clause, arguments)
            if not result.rowcount:
                raise ValueError('Inventory file changed or is no longer available; reload its evidence before reviewing')

    def candidates(self,label,limit=100,offset=0,search='',status='all',ids=None):
        if label!='Audiobooks':raise ValueError('Book candidates are available only for Audiobooks')
        # Book list speed (Sergei 2026-10-24, ruling 18): when the stored groups are current the page is a plain read
        # of one SQLite snapshot (WAL), so it no longer waits for group_lock, which an automatic approval holds for
        # seconds (cover extraction, track review, the job). Only a page that must rebuild the groups takes the lock.
        roots=self.source_roots(label)
        with connect(self.database) as connection:
            connection.execute('BEGIN')
            if all(groups.current(connection,root) for root in roots):
                return self._candidate_page(connection,roots,limit,offset,search,status,ids)
            connection.execute('ROLLBACK')
        with self.group_lock,connect(self.database) as connection:
            # v0.16.12: a plain read when the stored groups are current, so the page (11-13 s on the live catalog)
            # no longer holds the write lock every other write waited behind, a Retry press included.
            connection.execute('BEGIN')
            roots=self.source_roots(label)
            if not all(groups.current(connection,root) for root in roots):
                connection.execute('ROLLBACK');connection.execute('BEGIN IMMEDIATE')  # the groups are rebuilt: that writes
            return self._candidate_page(connection,roots,limit,offset,search,status,ids)

    def _candidate_page(self,connection,roots,limit,offset,search,status,ids):
        import reacquire_sources
        archived=[item['candidate_id'] for root in roots for item in reacquire_sources.markers(connection,root) if item['state']=='archived']
        if len(roots)==1:
            result=groups.page(connection,roots[0],limit,offset,search,status,self._coverage(connection,roots[0]),ids=ids)
            return dict(result,reacquire_archives=archived)
        # One transaction, one global ordering/filter/pagination. Each source
        # is grouped independently; no tracks cross a durable root boundary.
        result=groups.page_sources(connection,roots,limit,offset,search,status,
            {root:self._coverage(connection,root) for root in roots},ids=ids)
        return dict(result,reacquire_archives=archived)

    def _coverage(self,connection,root):
        current=connection.execute('SELECT state,errors FROM jobs WHERE root=?',(root,)).fetchone()
        pending=connection.execute("SELECT count(*) FROM queue WHERE root=? AND state IN ('pending','running')",(root,)).fetchone()[0]
        return bool(current and current['state']=='completed' and not pending and not current['errors'])

    def candidate(self,label,identity):
        if label!='Audiobooks':raise ValueError('Book candidates are available only for Audiobooks')
        root=self.source_root_for_candidate(identity)
        # 0.22.1 (backlog items 6-7): when the stored groups are current, one book is a plain read of one SQLite snapshot
        # (WAL), with no group_lock, no write transaction and no regroup. Scan again, Remove from list, the Delete check
        # and every other one-book read used to queue behind whatever held the lock (a status computation, an approval).
        with connect(self.database) as db:
            db.execute('BEGIN')
            if groups.current(db,root):return self._candidate_row(db,root,identity)
            db.execute('ROLLBACK')
        with self.group_lock,connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE');groups.sync(db,root)
            return self._candidate_row(db,root,identity)

    @staticmethod
    def _candidate_row(db,root,identity):
        row=db.execute('SELECT * FROM book_groups WHERE root=? AND id=? AND superseded=0',(root,identity)).fetchone()
        if row is None:raise ValueError('Candidate no longer current')
        current=db.execute('SELECT state,errors FROM jobs WHERE root=?',(root,)).fetchone()
        pending=db.execute("SELECT count(*) FROM queue WHERE root=? AND state IN ('pending','running')",(root,)).fetchone()[0]
        return groups.render(row,root,bool(current and current['state']=='completed' and not pending and not current['errors']),groups.retired_sources(db,root))

    def save_candidate(self,label,identity,revision,review,approve=False):
        if label!='Audiobooks':raise ValueError('Only audiobooks have book candidates')
        with self.group_lock,connect(self.database) as connection:
            connection.execute('BEGIN IMMEDIATE')
            root=self.source_root_for_candidate(identity)
            return groups.save(connection,root,identity,revision,review,approve)
