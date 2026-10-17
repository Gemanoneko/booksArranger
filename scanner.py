"""Persistent incremental inventory. Source roots are opened read-only."""
import json
import os
from pathlib import Path
import sqlite3
import threading
import datetime
from metadata import AUDIO, EBOOK, ScanStopped, read_metadata, propose, future_audio_tags
import groups

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

class Inventory:
    def __init__(self, database, roots=None, reader=read_metadata):
        self.database = str(database)
        self.roots = dict(roots or DEFAULT_ROOTS)
        if any(inside(self.database, root) for root in self.roots.values()):
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

    def status(self, label):
        root = self.roots[label]
        with connect(self.database) as connection:
            row = connection.execute('SELECT * FROM jobs WHERE root=?', (root,)).fetchone()
            count = connection.execute('SELECT count(*) FROM files WHERE root=?', (root,)).fetchone()[0]
            pending = connection.execute("SELECT count(*) FROM queue WHERE root=? AND state IN ('pending','running')", (root,)).fetchone()[0]
            unresolved = connection.execute("SELECT count(*) FROM files WHERE root=? AND error<>''",(root,)).fetchone()[0]
            issues = connection.execute("SELECT path,error,time FROM scan_outcomes WHERE root=? AND generation=? AND directory=1 AND outcome='error' ORDER BY path",(root,row['generation'] if row else 0)).fetchall()
        extra={'count':count,'pending':pending,'unresolved_errors':unresolved,'scan_issues':[dict(issue) for issue in issues]}
        return dict(row) | extra if row else {'state': 'not scanned', 'checked': 0, 'reused': 0, 'errors': 0, 'current': ''} | extra

    def _outcome(self, connection, root, generation, path, directory, error='', details=''):
        connection.execute('INSERT OR REPLACE INTO scan_outcomes VALUES(?,?,?,?,?,?,?,?)',
            (root,generation,path,int(directory),'error' if error else 'success',error,
             datetime.datetime.now(datetime.timezone.utc).isoformat(),details))

    def launch(self, label, resume=False):
        if self.worker and self.worker.is_alive():
            raise ValueError('A scan is already running; stop it before starting another')
        root = self.roots[label]
        with connect(self.database) as connection:
            job = connection.execute('SELECT * FROM jobs WHERE root=?', (root,)).fetchone()
            if resume:
                if not job or job['state'] not in {'stopped', 'offline', 'failed'}:
                    raise ValueError('No stopped scan to resume')
                generation = job['generation']
            else:
                if job and job['state'] in {'stopped', 'offline', 'failed'}:
                    raise ValueError('Use Resume scanning to continue saved progress')
                generation = (job['generation'] if job else 0) + 1
                connection.execute('DELETE FROM queue WHERE root=?', (root,))
                connection.execute('INSERT OR REPLACE INTO jobs(root,label,generation,state) VALUES(?,?,?,?)', (root,label,generation,'scanning'))
                connection.execute('INSERT INTO queue(root,generation,path,directory) VALUES(?,?,?,1)', (root,generation,root))
            connection.execute("UPDATE jobs SET state='scanning' WHERE root=?", (root,))
        self.stop_event.clear()
        self.last_error = ''
        self.worker = threading.Thread(target=self._run, args=(label,root,generation), daemon=True)
        self.worker.start()

    def stop(self):
        self.stop_event.set()

    def _run(self, label, root, generation):
        connection = connect(self.database)
        task = None
        try:
            if not os.path.isdir(root):
                connection.execute("UPDATE jobs SET state='offline', current=? WHERE root=?", ('Root unavailable; saved results preserved', root))
                connection.commit()
                return
            while not self.stop_event.is_set():
                task = connection.execute("SELECT * FROM queue WHERE root=? AND generation=? AND state='pending' ORDER BY path LIMIT 1", (root,generation)).fetchone()
                if not task:
                    errors = connection.execute('SELECT errors FROM jobs WHERE root=?', (root,)).fetchone()[0]
                    if not errors:
                        if _has_retirements(connection):
                            connection.execute("""UPDATE files SET missing=(seen<>? AND NOT EXISTS(
                                SELECT 1 FROM source_retirements r WHERE r.root=files.root AND r.path=files.path
                                AND r.state='removed' AND r.size=files.size AND r.modified=CAST(files.modified AS TEXT)))
                                WHERE root=?""",(generation,root))
                        else:
                            connection.execute('UPDATE files SET missing=(seen<>?) WHERE root=?', (generation,root))
                    connection.execute('UPDATE jobs SET state=?, current=? WHERE root=?', ('completed with errors' if errors else 'completed','',root))
                    connection.commit()
                    return
                path = task['path']
                connection.execute("UPDATE queue SET state='running' WHERE root=? AND generation=? AND path=?", (root,generation,path))
                connection.execute('UPDATE jobs SET current=? WHERE root=?', (path,root))
                connection.commit()
                try:
                    if task['directory']:
                        self._directory(connection, label, root, generation, path)
                    else:
                        self._file(connection, label, root, generation, path)
                    connection.execute("UPDATE queue SET state='done' WHERE root=? AND generation=? AND path=?", (root,generation,path))
                except ScanStopped:
                    connection.execute("UPDATE queue SET state='pending' WHERE root=? AND generation=? AND path=?", (root,generation,path))
                    connection.commit()
                    break
                except (OSError, ValueError, TimeoutError, sqlite3.Error) as error:
                    connection.execute("UPDATE queue SET state='error' WHERE root=? AND generation=? AND path=?", (root,generation,path))
                    connection.execute('UPDATE jobs SET errors=errors+1, current=? WHERE root=?', (f'{path}: {error}', root))
                    self._outcome(connection,root,generation,path,task['directory'],str(error))
                    if not task['directory']:
                        connection.execute('UPDATE jobs SET checked=checked+1 WHERE root=?',(root,))
                        # A source changing/disappearing mid-read invalidates its old canonical review.
                        # Keep a visible catalog error even if this is its very first scan.
                        result = connection.execute("UPDATE files SET error=?,review='' WHERE root=? AND path=?", (str(error),root,path))
                        if not result.rowcount:
                            kind, arrival = self._classify(label,root,path)
                            connection.execute('''INSERT INTO files(root,path,size,modified,seen,kind,arrival,metadata,error)
                              VALUES(?,?,0,0,?,?,?,?,?)''', (root,path,generation,kind,int(arrival),json.dumps({'notes':['File unavailable or changed during read; inspect before arranging']}),str(error)))
                connection.commit()
            connection.execute("UPDATE jobs SET state='stopped' WHERE root=?", (root,))
            connection.commit()
        except Exception as error:
            self.last_error = str(error)
            if task:
                connection.execute("UPDATE queue SET state='pending' WHERE root=? AND generation=? AND path=?", (root,generation,task['path']))
            connection.execute("UPDATE jobs SET state='failed', current=? WHERE root=?", (str(error),root))
            connection.commit()
        finally:
            connection.close()

    def _directory(self, connection, label, root, generation, path):
        owned=set()
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='owned_artifacts'").fetchone():
            owned={os.path.normcase(r['path']) for r in connection.execute("SELECT path FROM owned_artifacts WHERE kind IN ('temporary','recovery')")}
        with os.scandir(path) as entries:
            for entry in entries:
                if self.stop_event.is_set():
                    raise ScanStopped()
                # Never follow symlinks/junctions into another tree or a recursive loop.
                if entry.is_symlink() or (hasattr(os.path, 'isjunction') and os.path.isjunction(entry.path)):
                    continue
                if label == 'Audiobooks' and inside(entry.path, self.roots['Podcasts']):
                    continue
                if os.path.normcase(entry.path) in owned:
                    continue
                directory = entry.is_dir(follow_symlinks=False)
                if directory or entry.is_file(follow_symlinks=False):
                    connection.execute('INSERT OR IGNORE INTO queue(root,generation,path,directory) VALUES(?,?,?,?)', (root,generation,entry.path,int(directory)))
                    connection.commit()
        self._outcome(connection,root,generation,path,True)

    def _file(self, connection, label, root, generation, path):
        if self.stop_event.is_set():
            raise ScanStopped()
        if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='owned_artifacts'").fetchone():
            if connection.execute("SELECT 1 FROM owned_artifacts WHERE path=? AND kind IN ('temporary','recovery')",(path,)).fetchone():
                self._outcome(connection,root,generation,path,False,details='Exact owned recovery/temporary asset excluded from discovery')
                return
        retired = _retired_source(connection,root,path)
        try:
            before = fresh_stat(path)
        except FileNotFoundError:
            if not retired:raise
            # A saved queue may precede cleanup. Absence plus exact retirement provenance
            # is an intentional historical source, not a read failure. Existing names
            # always continue through the normal read path below.
            connection.execute("UPDATE files SET missing=0,error='' WHERE root=? AND path=?",(root,path))
            connection.execute('UPDATE jobs SET checked=checked+1 WHERE root=?',(root,))
            self._outcome(connection,root,generation,path,False,details='Source intentionally retired; recovery provenance retained')
            return
        old = connection.execute('SELECT * FROM files WHERE root=? AND path=?', (root,path)).fetchone()
        unchanged = old and old['size'] == before.st_size and old['modified'] == before.st_mtime_ns and not old['error'] and not retired
        if unchanged:
            _same_source(before, fresh_stat(path))
            connection.execute('UPDATE files SET seen=?,missing=0 WHERE root=? AND path=?', (generation,root,path))
            connection.execute('UPDATE jobs SET checked=checked+1,reused=reused+1 WHERE root=?', (root,))
            self._outcome(connection,root,generation,path,False)
            return
        kind, arrival = self._classify(label,root,path)
        metadata, error = {}, ''
        try:
            metadata = self.reader(path, kind, self.stop_event)
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='owned_artifacts'").fetchone():
                output=connection.execute("SELECT * FROM owned_artifacts WHERE path=? AND kind='output'",(path,)).fetchone()
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
        except ScanStopped:
            raise
        except Exception as issue:
            error = str(issue)
            metadata = {'notes': ['Metadata read failed; source file untouched'], 'title': '', 'author': ''}
        after = fresh_stat(path)
        _same_source(before, after)
        connection.execute('''INSERT OR REPLACE INTO files(root,path,size,modified,seen,kind,arrival,metadata,error,missing,review)
          VALUES(?,?,?,?,?,?,?,?,?,0,'')''', (root,path,before.st_size,before.st_mtime_ns,generation,kind,int(arrival),json.dumps(metadata,ensure_ascii=False),error))
        connection.execute('UPDATE jobs SET checked=checked+1,errors=errors+? WHERE root=?', (int(bool(error)),root))
        self._outcome(connection,root,generation,path,False,error)
        if not error:_supersede_retirement(connection,root,path)

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
            job=db.execute('SELECT * FROM jobs WHERE root=?',(root,)).fetchone()
            if job and job['state']=='scanning' or self.worker and self.worker.is_alive():raise ValueError('A library scan is active; source refresh waits')
            rows=[db.execute('SELECT * FROM files WHERE root=? AND path=?',(root,path)).fetchone() for path in member_paths]
            if any(row is None for row in rows):raise ValueError('Observed source is missing from the inventory')
            return dict(group),[dict(row) for row in rows],dict(job) if job else None,dict(context) if context else None
        root=self.roots[label]
        try:
            with self.group_lock,contextlib.ExitStack() as guards:
                check()
                with connect(self.database) as db:initial=snapshot(db)
                group,rows,job,context=initial;old_fingerprint=group['fingerprint'];paths=[row['path'] for row in rows]
                root_path=ordinary(root);updates=[];receipts=[];hashed_bytes=0
                for row in rows:
                    check();path=ordinary(row['path'])
                    if not inside(path,root_path) or row['kind']!='audiobook' or inside(path,self.roots.get('Podcasts',str(root_path/'Podcasts'))):
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
                with connect(self.database) as db:
                    db.execute('BEGIN IMMEDIATE')
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
        root = self.roots[label]
        with connect(self.database) as connection:
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
            row['metadata'] = json.loads(row['metadata'])
            row['review'] = json.loads(row['review']) if row['review'] else None
            row['preview'] = propose(row['path'],root,row['kind'],row['metadata'],row['review'])
            if row['kind'] == 'ebook' and row['preview']['path']:
                destination = os.path.normcase(os.path.normpath(row['preview']['path']))
                occupied = existing.get(destination)
                if len(destinations.get(destination,[])) > 1 or (occupied and occupied != row['path']):
                    row['preview'] = {'path':row['preview']['path'],'confidence':'Collision review','reason':'Destination is shared by another catalog file; preserve all editions and resolve before future arranging'}
            if row['missing'] or row['error']:
                row['preview'] = {'path': '', 'confidence': 'Unavailable' if row['missing'] else 'Read error', 'reason': row['error'] or 'Missing in last complete scan'}
            row['error_time']=failures.get(row['path'],{}).get('time','')
            row['saved_snapshot']=bool(row['error'] and row['metadata'].get('method'))
            if row['kind'] == 'audiobook':
                row['tag_preview'] = future_audio_tags(row['metadata'],row['review'] if not row['missing'] and not row['error'] else None)
            rows.append(row)
        filters={'all':lambda row:True,'errors':lambda row:bool(row['error']),
            'review':lambda row:row['preview']['confidence']=='Needs review',
            'preview':lambda row:bool(row['preview']['path']) and not row['error'] and not row['missing'],
            'missing':lambda row:bool(row['missing'])}
        if status not in filters:raise ValueError('Unknown inventory status')
        rows=[row for row in rows if filters[status](row)]
        result=rows[offset:offset+limit]
        return {'rows':result,'total':len(rows)} if page else result

    def save_review(self, root, path, review, size=None, modified=None):
        with connect(self.database) as connection:
            clause = ' AND size=? AND modified=?' if size is not None else ''
            arguments = (json.dumps(review,ensure_ascii=False),root,path) + ((size,modified) if size is not None else ())
            result = connection.execute('UPDATE files SET review=? WHERE root=? AND path=?' + clause, arguments)
            if not result.rowcount:
                raise ValueError('Inventory file changed or is no longer available; reload its evidence before reviewing')

    def candidates(self,label,limit=100,offset=0,search='',status='all',ids=None):
        if label!='Audiobooks':raise ValueError('Book candidates are available only for Audiobooks')
        with self.group_lock,connect(self.database) as connection:
            connection.execute('BEGIN IMMEDIATE')
            current=connection.execute('SELECT state,errors FROM jobs WHERE root=?',(self.roots[label],)).fetchone()
            pending=connection.execute("SELECT count(*) FROM queue WHERE root=? AND state IN ('pending','running')",(self.roots[label],)).fetchone()[0]
            return groups.page(connection,self.roots[label],limit,offset,search,status,
                bool(current and current['state']=='completed' and not pending and not current['errors']),ids=ids)

    def candidate(self,label,identity):
        if label!='Audiobooks':raise ValueError('Book candidates are available only for Audiobooks')
        root=self.roots[label]
        with self.group_lock,connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE');groups.sync(db,root)
            row=db.execute('SELECT * FROM book_groups WHERE root=? AND id=? AND superseded=0',(root,identity)).fetchone()
            if row is None:raise ValueError('Candidate no longer current')
            current=db.execute('SELECT state,errors FROM jobs WHERE root=?',(root,)).fetchone()
            pending=db.execute("SELECT count(*) FROM queue WHERE root=? AND state IN ('pending','running')",(root,)).fetchone()[0]
            return groups.render(row,root,bool(current and current['state']=='completed' and not pending and not current['errors']),groups.retired_sources(db,root))

    def save_candidate(self,label,identity,revision,review,approve=False):
        if label!='Audiobooks':raise ValueError('Only audiobooks have book candidates')
        with self.group_lock,connect(self.database) as connection:
            connection.execute('BEGIN IMMEDIATE')
            return groups.save(connection,self.roots[label],identity,revision,review,approve)
