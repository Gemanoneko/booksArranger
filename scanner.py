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

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

def connect(database):
    connection = sqlite3.connect(database, timeout=10, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA busy_timeout=10000')
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
        with os.scandir(path) as entries:
            for entry in entries:
                if self.stop_event.is_set():
                    raise ScanStopped()
                # Never follow symlinks/junctions into another tree or a recursive loop.
                if entry.is_symlink() or (hasattr(os.path, 'isjunction') and os.path.isjunction(entry.path)):
                    continue
                if label == 'Audiobooks' and inside(entry.path, self.roots['Podcasts']):
                    continue
                directory = entry.is_dir(follow_symlinks=False)
                if directory or entry.is_file(follow_symlinks=False):
                    connection.execute('INSERT OR IGNORE INTO queue(root,generation,path,directory) VALUES(?,?,?,?)', (root,generation,entry.path,int(directory)))
                    connection.commit()
        self._outcome(connection,root,generation,path,True)

    def _file(self, connection, label, root, generation, path):
        if self.stop_event.is_set():
            raise ScanStopped()
        before = fresh_stat(path)
        old = connection.execute('SELECT * FROM files WHERE root=? AND path=?', (root,path)).fetchone()
        unchanged = old and old['size'] == before.st_size and old['modified'] == before.st_mtime_ns and not old['error']
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

    def candidates(self,label,limit=100,offset=0,search='',status='all'):
        if label!='Audiobooks':raise ValueError('Book candidates are available only for Audiobooks')
        with self.group_lock,connect(self.database) as connection:
            connection.execute('BEGIN IMMEDIATE')
            current=connection.execute('SELECT state,errors FROM jobs WHERE root=?',(self.roots[label],)).fetchone()
            pending=connection.execute("SELECT count(*) FROM queue WHERE root=? AND state IN ('pending','running')",(self.roots[label],)).fetchone()[0]
            return groups.page(connection,self.roots[label],limit,offset,search,status,
                bool(current and current['state']=='completed' and not pending and not current['errors']))

    def save_candidate(self,label,identity,revision,review,approve=False):
        if label!='Audiobooks':raise ValueError('Only audiobooks have book candidates')
        with self.group_lock,connect(self.database) as connection:
            connection.execute('BEGIN IMMEDIATE')
            return groups.save(connection,self.roots[label],identity,revision,review,approve)
