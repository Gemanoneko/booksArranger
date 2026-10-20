"""App-owned retirement of closed, unpublished conversion attempts.

This ledger is deliberately separate from published-output/original cleanup.
Creation intent is not deletion authority: retirement revalidates the exact
closed file, current failed job, protected input and every durable reference.
"""
import contextlib
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
import threading
from scanner import connect
from sqlite_retry import transaction
from native_io import BoundaryError, DirectoryBoundary as NativeBoundary, VerifiedFile as NativeFile, ordinary, kernel
from source_cleanup import packed, stamp, single_stream

TERMINAL = {'removed', 'absent_after_intent', 'not_created'}
GENERATED = re.compile(r'(?:checked|compatible)\.m4b|normalized[0-9]{5}\.wav|(?:inputs|chapters)\.txt|[0-9a-f]{32}\.(?:stderr|stdout|decode-stderr|jpg|png)')
REFERENCE_TABLES = ('source_cleanup', 'cleanup_members', 'source_retirements',
                    'audiobook_replacements', 'audiobook_replacement_retirements',
                    'storage_cleanup_files', 'storage_cleanup_preserved',
                    'storage_cleanup_authorizations', 'storage_cleanup_jobs', 'owned_artifacts',
                    'recovery_retention', 'recovery_completion')


def digest(value):
    return hashlib.sha256(packed(value).encode('utf-8')).hexdigest()


def normalized(value):
    text = str(value).casefold()
    while chr(92) * 2 in text:
        text = text.replace(chr(92) * 2, chr(92))
    return text.replace(chr(92), '/')


class DirectoryBoundary(NativeBoundary):
    def __exit__(self, *unused):
        failures = []
        for handle in reversed(self.handles):
            if not kernel.CloseHandle(handle):
                failures.append(handle)
        self.handles = []
        if failures:
            raise RuntimeError('Working ancestry native close failed')


class VerifiedFile(NativeFile):
    def __exit__(self, *unused):
        if self.handle is not None:
            if not kernel.CloseHandle(self.handle):
                raise RuntimeError('Working file native close failed')
            self.handle = None


class WorkingLifecycle:
    def __init__(self, database, stage_root, guard=lambda: None):
        self.database = str(database)
        self.stage_root = ordinary(stage_root)
        self.guard = guard
        self._locks = {}
        self._locks_guard = threading.Lock()
        self._background_thread = None
        self._reconcile_lock = threading.Lock()
        with connect(self.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS working_attempts(job_id TEXT,attempt_id TEXT,manifest TEXT,manifest_hash TEXT,producer TEXT,state TEXT,reason TEXT,updated TEXT,PRIMARY KEY(job_id,attempt_id))')
            db.execute('CREATE TABLE IF NOT EXISTS working_diagnostics(job_id TEXT,attempt_id TEXT,name TEXT,sha256 TEXT,size INTEGER,evidence TEXT,updated TEXT,PRIMARY KEY(job_id,attempt_id,name))')
            db.execute('CREATE TABLE IF NOT EXISTS working_files(job_id TEXT,attempt_id TEXT,name TEXT,path TEXT,role TEXT,state TEXT,sha256 TEXT,size INTEGER,facts TEXT,updated TEXT,PRIMARY KEY(job_id,attempt_id,name))')

    @property
    def in_background(self):
        return self._background_thread == threading.get_ident()

    def _hash(self, handle):
        value = hashlib.sha256()
        for block in handle.chunks():
            self.guard()  # No SQLite transaction or central service lock is held.
            value.update(block)
        return value.hexdigest()

    def _rows(self, sql, params=()):
        with connect(self.database) as db:
            return [dict(r) for r in db.execute(sql, params)]

    def _attempt(self, job_id, attempt_id):
        rows = self._rows('SELECT * FROM working_attempts WHERE job_id=? AND attempt_id=?', (job_id, attempt_id))
        if len(rows) != 1:
            raise BoundaryError('Working attempt has no durable ownership receipt')
        return rows[0]

    def _files(self, job_id, attempt_id):
        return self._rows('SELECT * FROM working_files WHERE job_id=? AND attempt_id=? ORDER BY name', (job_id, attempt_id))

    def _set_attempt(self, expected, **fields):
        target = dict(expected, **fields, updated=stamp())
        def write(db):
            current = db.execute('SELECT * FROM working_attempts WHERE job_id=? AND attempt_id=?', (expected['job_id'], expected['attempt_id'])).fetchone()
            current = dict(current) if current else None
            if current == target:
                return target
            if current != expected:
                raise BoundaryError('Working attempt changed; files preserved')
            db.execute('UPDATE working_attempts SET producer=?,state=?,reason=?,updated=? WHERE job_id=? AND attempt_id=?',
                       (target['producer'], target['state'], target['reason'], target['updated'], target['job_id'], target['attempt_id']))
            return target
        return transaction(self.database, write)

    def _file_state(self, expected, state, **fields):
        held_db=fields.pop('_db',None)
        allowed = {'creation_intended': {'closed', 'not_created'}, 'closed': {'removal_intended'},
                   'removal_intended': {'disposition_set', 'absent_after_intent'}, 'disposition_set': {'removed'}}
        if state not in allowed.get(expected['state'], set()):
            raise BoundaryError('Invalid working-file retirement transition')
        target = dict(expected, state=state, **fields, updated=stamp())
        def write(db):
            row = db.execute('SELECT * FROM working_files WHERE job_id=? AND attempt_id=? AND name=?',
                             (expected['job_id'], expected['attempt_id'], expected['name'])).fetchone()
            current = dict(row) if row else None
            if current == target:
                return target
            if current != expected:
                raise BoundaryError('Working-file receipt changed; files preserved')
            db.execute('UPDATE working_files SET state=?,sha256=?,size=?,facts=?,updated=? WHERE job_id=? AND attempt_id=? AND name=?',
                       (state, target['sha256'], target['size'], target['facts'], target['updated'], target['job_id'], target['attempt_id'], target['name']))
            return target
        return write(held_db) if held_db is not None else transaction(self.database, write)

    def begin(self, manifest):
        job_id, attempt_id = manifest['job_id'], manifest['attempt_id']
        if any(str(uuid.UUID(value)) != value for value in (job_id, attempt_id)):
            raise BoundaryError('Invalid working-attempt identity')
        frozen = {key: value for key, value in manifest.items() if key != 'attempt_id'}
        target = {'job_id': job_id, 'attempt_id': attempt_id, 'manifest': packed(frozen),
                  'manifest_hash': digest(frozen), 'producer': 'active', 'state': 'producing', 'reason': '', 'updated': stamp()}
        def insert(db):
            row = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()
            if not row or row['state'] != 'running' or row['attempt_id'] != attempt_id or row['manifest_hash'] != target['manifest_hash']:
                raise BoundaryError('Working producer is not the current admitted attempt')
            if json.loads(row['manifest']) != frozen or row['output'] or json.loads(row['journal']).get('publication_intent'):
                raise BoundaryError('Working producer has a publication dependency')
            if db.execute('SELECT 1 FROM working_attempts WHERE job_id=? AND attempt_id=?', (job_id, attempt_id)).fetchone():
                raise BoundaryError('Working attempt cannot be reused')
            db.execute('INSERT INTO working_attempts VALUES(?,?,?,?,?,?,?,?)', tuple(target.values()))
        transaction(self.database, insert)

    def planned(self, stage, path):
        stage, path = ordinary(stage), ordinary(path)
        if path.parent != stage or stage.parent.parent != self.stage_root:
            raise BoundaryError('Producer path is outside its admitted working attempt')
        attempt = self._attempt(stage.parent.name, stage.name)
        if attempt['producer'] != 'active':
            raise BoundaryError('Producer has already closed')
        manifest = json.loads(attempt['manifest'])
        snapshots = {'source%05d' % index + Path(item['path']).suffix.lower() for index, item in enumerate(manifest['sources'])}
        role = 'source' if path.name in snapshots else 'cover' if path.name in {'cover.jpg', 'cover.png'} else 'generated'
        if role == 'generated' and not GENERATED.fullmatch(path.name):
            raise BoundaryError('Unknown producer artifact is not admitted')
        with DirectoryBoundary(self.stage_root.anchor, stage):
            if os.path.lexists(path):
                raise BoundaryError('Producer output name already exists')
            target = {'job_id': attempt['job_id'], 'attempt_id': attempt['attempt_id'], 'name': path.name,
                      'path': str(path), 'role': role, 'state': 'creation_intended', 'sha256': '', 'size': 0, 'facts': '{}', 'updated': stamp()}
            def insert(db):
                if db.execute('SELECT 1 FROM working_files WHERE job_id=? AND attempt_id=? AND name=?',
                              (target['job_id'], target['attempt_id'], target['name'])).fetchone():
                    raise BoundaryError('Producer artifact intent cannot be replayed')
                db.execute('INSERT INTO working_files VALUES(?,?,?,?,?,?,?,?,?,?)', tuple(target.values()))
            transaction(self.database, insert)

    def closed(self, stage, producer_closed=True):
        """Called only after the runner closes every owned producer and file handle."""
        stage = ordinary(stage)
        attempt = self._attempt(stage.parent.name, stage.name)
        if attempt['producer'] != 'active':
            raise BoundaryError('Working producer closure cannot be replayed')
        if producer_closed is not True:
            self._set_attempt(attempt, producer='uncertain', state='attention', reason='Owned media producer closure was not established')
            raise BoundaryError('Working files retained: producer closure is uncertain')
        attempt = self._set_attempt(attempt, producer='closed', state='closed')
        try:
            files = self._files(attempt['job_id'], attempt['attempt_id'])
            if not files and not os.path.lexists(stage):
                self._set_attempt(attempt, producer='closed', state='closed')
                return
            with DirectoryBoundary(self.stage_root.anchor, stage):
                known = {entry['name'] for entry in files}
                with os.scandir(stage) as names:
                    if any(entry.name not in known or not entry.is_file(follow_symlinks=False) for entry in names):
                        raise BoundaryError('Unknown attempt member preserved; producer scope differs')
                for entry in files:
                    path = ordinary(entry['path'])
                    if path.parent != stage or path.name != entry['name']:
                        raise BoundaryError('Working artifact path changed')
                    if not os.path.lexists(path):
                        self._file_state(entry, 'not_created')
                        continue
                    with VerifiedFile(path) as handle:
                        facts = handle.facts()
                        if facts['links'] != 1:
                            raise BoundaryError('Working artifact has another filesystem alias')
                        single_stream(path)
                        self._file_state(entry, 'closed', sha256=self._hash(handle), size=facts['size'], facts=packed(facts))
            return {entry['name']: {'sha256':entry['sha256'], 'size':entry['size']}
                    for entry in self._files(attempt['job_id'], attempt['attempt_id']) if entry['state']=='closed'}
        except Exception as error:
            current = self._attempt(attempt['job_id'], attempt['attempt_id'])
            self._set_attempt(current, state='closed', reason='Closed producer; incomplete artifact capture: '+str(error)[:900])
            raise

    def _unpublished(self, attempt):
        rows = self._rows('SELECT * FROM audio_jobs WHERE job_id=?', (attempt['job_id'],))
        if len(rows) != 1:
            raise BoundaryError('Working job ownership is unavailable')
        row = rows[0]
        if row['manifest_hash'] != attempt['manifest_hash'] or json.loads(row['manifest']) != json.loads(attempt['manifest']):
            raise BoundaryError('Frozen working manifest changed')
        if row['state'] not in {'needs attention', 'pending'} or row['output'] or json.loads(row['journal']).get('publication_intent'):
            raise BoundaryError('Working job is active or has a publication dependency')
        if row['attempt_id'] != attempt['attempt_id']:
            prior = self._rows('SELECT record FROM audio_failure_history WHERE job_id=? AND attempt_id=?', (attempt['job_id'], attempt['attempt_id']))
            if len(prior) != 1 or json.loads(prior[0]['record']).get('publication_intent'):
                raise BoundaryError('Historical working attempt has no failed-attempt journal')
        return row

    def _references(self, attempt, paths):
        wanted = [normalized(path) for path in paths]
        with connect(self.database) as db:
            for row in db.execute('SELECT * FROM audio_jobs WHERE job_id!=?', (attempt['job_id'],)):
                text = normalized(packed(dict(row)))
                if any(path in text for path in wanted):
                    raise BoundaryError('Another audio job references working files')
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ('working_attempts', 'working_files'):
                for raw in db.execute('SELECT * FROM '+table+' WHERE job_id!=? OR attempt_id!=?', (attempt['job_id'], attempt['attempt_id'])):
                    if any(path in normalized(packed(dict(raw))) for path in wanted):
                        raise BoundaryError('Another working attempt references the same file')
            for table in REFERENCE_TABLES:
                if table not in tables:
                    continue
                cursor = db.execute('SELECT * FROM ' + table)
                for raw in cursor:
                    row = dict(raw)
                    if row.get('job_id') == attempt['job_id'] or any(path in normalized(packed(row)) for path in wanted):
                        raise BoundaryError('Working file has a publication/recovery dependency: ' + table)

    def _input(self, stack, root, path, item):
        path = ordinary(path)
        if not path.is_relative_to(root):
            raise BoundaryError('Protected source is outside its frozen library')
        stack.enter_context(DirectoryBoundary(root.anchor, path.parent))
        handle = stack.enter_context(VerifiedFile(path))
        facts = handle.facts()
        if facts['links'] != 1 or ('size' in item and facts['size'] != item['size']) or self._hash(handle) != item['sha256']:
            raise BoundaryError('Protected source bytes are unavailable')
        if 'modified' in item and str(facts['modified']) != str(item['modified']):
            raise BoundaryError('Frozen original source timestamp changed')
        return handle

    def _diagnostic(self, entry, handle):
        """Keep compact actual bytes/semantic evidence before deleting scratch.

        A diagnostic that cannot fit the bounded evidence contract is retained,
        while unrelated generated audio can still be retired. No new attempt is
        admitted over unresolved evidence. Empty diagnostics have zero payload.
        """
        if not entry['name'].endswith(('.stdout','.stderr','.decode-stderr','.txt')):
            return True
        rows = self._rows('SELECT * FROM working_diagnostics WHERE job_id=? AND attempt_id=? AND name=?',
                          (entry['job_id'],entry['attempt_id'],entry['name']))
        if rows:
            if (rows[0]['sha256'],rows[0]['size']) != (entry['sha256'],entry['size']):
                raise BoundaryError('Compact diagnostic provenance changed')
            return True
        if entry['size'] == 0:
            return True  # Empty bytes are fully represented by their existing SHA/size receipt.
        if entry['size'] > 8*1024*1024:
            return False
        blocks = []
        for block in handle.chunks():
            self.guard();blocks.append(block)
        raw = b''.join(blocks)
        if len(raw)!=entry['size'] or hashlib.sha256(raw).hexdigest()!=entry['sha256']:
            raise BoundaryError('Leased diagnostic bytes differ')
        semantic = None
        try:
            value=json.loads(raw)
            if isinstance(value,dict) and ('streams' in value or 'format' in value):
                fields=('index','codec_type','codec_name','codec_long_name','profile','codec_tag_string','sample_fmt','sample_rate','channels','channel_layout','time_base','start_pts','start_time','duration_ts','duration','nb_frames','extradata_size','extradata_hash','side_data_list')
                streams=value.get('streams',[])
                if not isinstance(streams,list):raise ValueError('Malformed diagnostic streams')
                semantic={'streams':[{key:stream[key] for key in fields if key in stream} for stream in streams if isinstance(stream,dict)],
                          'format':{key:item for key,item in value.get('format',{}).items() if key in {'format_name','start_time','duration','size','bit_rate','tags'}},
                          'chapters':value.get('chapters',[])}
        except (ValueError,TypeError,AttributeError):pass
        complete=len(raw)<=8192
        evidence={'schema':'working-diagnostic-v1','path':entry['path'],'sha256':entry['sha256'],'size':entry['size'],
                  'complete':complete,'truncated':not complete,'encoding':'base64',
                  'head':base64.b64encode(raw if complete else raw[:4096]).decode('ascii'),
                  'tail':base64.b64encode(b'' if complete else raw[-4096:]).decode('ascii'),'semantic':semantic}
        encoded=packed(evidence)
        if len(encoded.encode('utf8'))>64*1024:
            return False
        values=(entry['job_id'],entry['attempt_id'],entry['name'],entry['sha256'],entry['size'],encoded,stamp())
        def save(db):
            old=db.execute('SELECT * FROM working_diagnostics WHERE job_id=? AND attempt_id=? AND name=?',values[:3]).fetchone()
            if old:
                if (old['sha256'],old['size'],old['evidence'])!=values[3:6]:raise BoundaryError('Compact diagnostic changed')
                return True
            used=db.execute('SELECT COALESCE(SUM(length(CAST(evidence AS BLOB))),0) FROM working_diagnostics WHERE job_id=? AND attempt_id=?',values[:2]).fetchone()[0]
            if used+len(encoded.encode('utf8'))>1024*1024:return False
            db.execute('INSERT INTO working_diagnostics VALUES(?,?,?,?,?,?,?)',values)
            return True
        return transaction(self.database,save)

    def retire(self, job_id, attempt_id):
        with self._locks_guard:
            lock = self._locks.setdefault(job_id, threading.RLock())
        with lock:
            return self._retire(job_id, attempt_id)

    def _retire(self, job_id, attempt_id):
        self.guard()
        attempt = self._attempt(job_id, attempt_id)
        if attempt['state'] == 'isolated_retained':
            raise BoundaryError('Isolated old files and source dependencies are retained; Clear is unavailable')
        if attempt['state'] == 'published':
            raise BoundaryError('Published working files belong to protected output cleanup')
        if attempt['state'] == 'retired':
            # A same-name replacement must still be refused, even after success.
            files = self._files(job_id, attempt_id)
            stage = self.stage_root / job_id / attempt_id
            if os.path.lexists(stage):
                with os.scandir(stage) as names:
                    if any(entry.name not in {row['name'] for row in files} for entry in names):
                        raise BoundaryError('Unknown member of a retired attempt preserved')
            if any(os.path.lexists(row['path']) for row in files if row['state'] in TERMINAL):
                raise BoundaryError('A retired working name was replaced; preserved')
            return
        if attempt['producer'] != 'closed':
            raise BoundaryError('A prior producer is not durably closed; another attempt is not admitted')
        self._unpublished(attempt)
        manifest = json.loads(attempt['manifest'])
        stage = self.stage_root / job_id / attempt_id
        entries = self._files(job_id, attempt_id)
        if not entries:
            self._set_attempt(attempt, state='retired')
            return
        self._references(attempt, [entry['path'] for entry in entries])
        with contextlib.ExitStack() as stack:
            boundary = stack.enter_context(DirectoryBoundary(self.stage_root.anchor, stage))
            marker = stack.enter_context(VerifiedFile(stage.parent / 'ownership.json'))
            if marker.facts()['size'] > 16 * 1024 * 1024 or json.loads(b''.join(marker.chunks())) != {'job_id': job_id, 'manifest': manifest}:
                raise BoundaryError('Private staging ownership changed')
            known = {entry['name'] for entry in entries}
            with os.scandir(stage) as names:
                unknown = any(entry.name not in known or not entry.is_file(follow_symlinks=False) for entry in names)
            # Prefer exact frozen originals: these attempts always restart rather
            # than resume a partial encoder. If unavailable, keep valid snapshots.
            originals = True
            original_stack = stack.enter_context(contextlib.ExitStack())
            try:
                for item in manifest['sources']:
                    self._input(original_stack, ordinary(manifest['root']), item['path'], item)
            except (OSError, BoundaryError):
                original_stack.close()
                originals = False
            if not originals:
                for index, item in enumerate(manifest['sources']):
                    name = 'source%05d' % index + Path(item['path']).suffix.lower()
                    snapshot = stack.enter_context(VerifiedFile(stage / name))
                    if snapshot.facts()['links'] != 1 or snapshot.facts()['size'] != item['size'] or self._hash(snapshot) != item['sha256']:
                        raise BoundaryError('Neither original nor protected snapshot proves source survival')
            cover_available = False
            if originals and manifest.get('cover'):
                cover_stack = stack.enter_context(contextlib.ExitStack())
                try:
                    self._input(cover_stack, ordinary(manifest['cover']['path']).parent, manifest['cover']['path'], manifest['cover'])
                except (OSError, BoundaryError):
                    cover_stack.close()
                else:
                    cover_available = True
            prepared = []
            for entry in entries:
                path = ordinary(entry['path'])
                if path.parent != stage or path.name != entry['name']:
                    raise BoundaryError('Working retirement path changed')
                if entry['state'] == 'creation_intended':
                    continue  # No native producer identity was durably captured; never adopt its name.
                if entry['role'] == 'source' and not originals or entry['role'] == 'cover' and not cover_available:
                    continue
                if entry['state'] in TERMINAL:
                    if os.path.lexists(path):
                        raise BoundaryError('A discarded working name was replaced')
                    continue
                if not os.path.lexists(path):
                    if entry['state'] in {'removal_intended', 'disposition_set'}:
                        self._file_state(entry, 'removed' if entry['state'] == 'disposition_set' else 'absent_after_intent')
                        continue
                    raise BoundaryError('Working file is missing without durable removal intent')
                handle = stack.enter_context(VerifiedFile(path, delete=True))
                facts = handle.facts()
                single_stream(path)
                if facts['links'] != 1 or facts != json.loads(entry['facts']) or facts['size'] != entry['size'] or self._hash(handle) != entry['sha256']:
                    raise BoundaryError('Closed working-file native identity or bytes changed')
                prepared.append((entry, path, handle))
            diagnostic_held = False
            for entry, path, handle in prepared:
                self.guard()
                self._unpublished(attempt)
                self._references(attempt, [str(path)])
                boundary.revalidate()
                if not self._diagnostic(entry,handle):
                    diagnostic_held = True
                    continue
                if entry['state'] == 'closed':
                    entry = self._file_state(entry, 'removal_intended')
                if entry['state'] == 'removal_intended':
                    handle.dispose()
                    entry = self._file_state(entry, 'disposition_set')
                # A surviving exact disposition_set file may have come from a
                # crash before native close; reapply only to the same verified ID.
                elif entry['state'] == 'disposition_set':
                    handle.dispose()
                handle.__exit__(None, None, None)
                if os.path.lexists(path):
                    raise BoundaryError('Disposed working name still exists or was replaced')
                self._file_state(entry, 'removed')
            current = self._attempt(job_id, attempt_id)
            files = self._files(job_id, attempt_id)
            uncertain = any(row['state']=='creation_intended' for row in files)
            remaining = any(row['state'] not in TERMINAL for row in files)
            self._set_attempt(current, state='attention' if uncertain or unknown or diagnostic_held else 'sources_retained' if remaining else 'retired',
                              reason='Uncaptured producer file preserved; explicit review required' if uncertain else 'Unknown attempt member preserved; explicit review required' if unknown else 'Compact diagnostic capture limit reached; exact scratch evidence retained' if diagnostic_held else 'Frozen originals/artwork unavailable; source snapshots retained' if remaining else '')

    def terminal(self, job_id, attempt_id):
        attempts = self._rows('SELECT * FROM working_attempts WHERE job_id=? AND attempt_id=?', (job_id, attempt_id))
        if not attempts:
            return  # Revision/stop failure before the media runner created no working producer.
        rows = self._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))
        if rows and rows[0]['state'] == 'completed':
            attempt = attempts[0]
            output = json.loads(rows[0]['output'])
            from audio_jobs import AudioJobs
            from source_cleanup import CleanupJobs
            from storage_cleanup import StorageCleanup
            AudioJobs._validate_record(output)
            CleanupJobs._validation_contract(json.loads(attempt['manifest']),output)
            validation = output.get('validation', {})
            artifacts = validation.get('staging_artifacts', {})
            if rows[0]['attempt_id']!=attempt_id or rows[0]['manifest_hash']!=attempt['manifest_hash'] or json.loads(rows[0]['manifest'])!=json.loads(attempt['manifest']):
                raise BoundaryError('Published attempt ownership changed')
            if attempt['producer']!='closed' or output.get('job_id')!=job_id or validation.get('passed') is not True or artifacts.get('attempt_id')!=attempt_id:
                raise BoundaryError('Published working-file handoff is unavailable')
            snapshots={'source%05d'%index+Path(item['path']).suffix.lower() for index,item in enumerate(json.loads(attempt['manifest'])['sources'])}
            for entry in self._files(job_id, attempt_id):
                if entry['name'] not in snapshots and not StorageCleanup.working_name(json.loads(attempt['manifest']),entry['name']):
                    raise BoundaryError('Published working role is not accepted by protected cleanup')
                if entry['state']=='not_created':continue
                if entry['state']!='closed' or artifacts.get('files',{}).get(entry['name'])!={'sha256':entry['sha256'],'size':entry['size']}:
                    raise BoundaryError('Published working-file handoff differs from closed producer')
            self._set_attempt(attempt,state='published',reason='Exact staging receipts handed to protected published-output cleanup')
            return
        self.retire(job_id, attempt_id)

    def _published(self, attempt):
        rows=self._rows('SELECT * FROM audio_jobs WHERE job_id=?',(attempt['job_id'],))
        if len(rows)!=1:raise BoundaryError('Published job is unavailable')
        row=rows[0];manifest=json.loads(attempt['manifest']);output=json.loads(row['output'] or '{}')
        if row['state']!='completed' or row['attempt_id']!=attempt['attempt_id'] or row['manifest_hash']!=attempt['manifest_hash'] or json.loads(row['manifest'])!=manifest or digest(manifest)!=attempt['manifest_hash']:
            raise BoundaryError('Published snapshot attempt changed')
        if attempt['producer']!='closed' or output.get('job_id')!=attempt['job_id'] or output.get('validation',{}).get('staging_artifacts',{}).get('attempt_id')!=attempt['attempt_id']:
            raise BoundaryError('Closed published producer is unavailable')
        return manifest,output

    def _published_references(self, attempt, paths):
        wanted=[normalized(path) for path in paths]
        with connect(self.database) as db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ('audio_jobs','working_attempts','working_files')+REFERENCE_TABLES+('audio_failure_history',):
                if table not in tables:continue
                for raw in db.execute('SELECT * FROM '+table):
                    row=dict(raw)
                    if table=='audio_jobs' and row['job_id']==attempt['job_id']:continue
                    if table in {'working_attempts','working_files'} and row['job_id']==attempt['job_id'] and row['attempt_id']==attempt['attempt_id']:continue
                    if table=='storage_cleanup_files' and row['job_id']==attempt['job_id'] and row['kind']=='staging':continue
                    if any(path in normalized(packed(row)) for path in wanted):
                        raise BoundaryError('Published snapshot has another durable dependency: '+table)

    def schedule_published(self, job_id):
        """A relevant completed cleanup event wakes one held attempt; no file IO."""
        with self._locks_guard:lock=self._locks.setdefault(job_id,threading.RLock())
        with lock:
            for attempt in self._rows("SELECT * FROM working_attempts WHERE job_id=? AND state='published_held'",(job_id,)):
                self._published(attempt)
                self._set_attempt(attempt,state='published',reason='Relevant recovery cleanup completed; idle snapshot proof pending')

    def discharge_published(self, job_id, storage, revisit=False):
        """Relevant completed attempt only; no adoption of legacy working names."""
        with self._locks_guard:lock=self._locks.setdefault(job_id,threading.RLock())
        with lock:
            attempts=self._rows("SELECT * FROM working_attempts WHERE job_id=? AND state IN ('published','published_held')",(job_id,))
            if not attempts:return
            if len(attempts)!=1:raise BoundaryError('Ambiguous published working attempts')
            attempt=attempts[0]
            if attempt['state']=='published_held' and not revisit:return
            try:
                self._discharge_published(attempt,storage)
            except InterruptedError:raise
            except (OSError,ValueError,BoundaryError) as error:
                current=self._attempt(job_id,attempt['attempt_id'])
                self._set_attempt(current,state='published_held',reason=str(error)[:1000])
                raise

    def _discharge_published(self, attempt, storage):
        self.guard()
        manifest,output=self._published(attempt)
        entries=self._files(attempt['job_id'],attempt['attempt_id'])
        snapshots={'source%05d'%i+Path(s['path']).suffix.lower():s for i,s in enumerate(manifest['sources'])}
        sources=[entry for entry in entries if entry['role']=='source']
        if {entry['name'] for entry in sources}!=set(snapshots):
            raise BoundaryError('Complete captured source snapshots are required')
        stage=self.stage_root/attempt['job_id']/attempt['attempt_id']
        paths=[entry['path'] for entry in entries]
        self._published_references(attempt,paths)
        with storage.protected_output(attempt['job_id'],guard=self.guard) as (current_manifest,current_output),contextlib.ExitStack() as stack:
            if current_manifest!=manifest or current_output!=output:
                raise BoundaryError('Current protected publication changed')
            boundary=stack.enter_context(DirectoryBoundary(stage.anchor,stage))
            marker=stack.enter_context(VerifiedFile(stage.parent/'ownership.json'))
            if marker.facts()['size']>16*1024*1024 or json.loads(b''.join(marker.chunks()))!={'job_id':attempt['job_id'],'manifest':manifest}:
                raise BoundaryError('Published staging ownership changed')
            known={entry['name'] for entry in entries}
            with os.scandir(stage) as names:
                if any(item.name not in known or not item.is_file(follow_symlinks=False) for item in names):
                    raise BoundaryError('Unknown published attempt member preserved')
            source_proof=storage.snapshot_source_safety(stack,attempt['job_id'],manifest,output,guard=self.guard)
            prepared=[]
            artifacts=output['validation']['staging_artifacts']['files']
            for entry in sources:
                path=ordinary(entry['path']);source=snapshots[entry['name']]
                if path.parent!=stage or path.name!=entry['name'] or (entry['sha256'],entry['size'])!=(source['sha256'],source['size']) or artifacts.get(entry['name'])!={'sha256':entry['sha256'],'size':entry['size']}:
                    raise BoundaryError('Frozen snapshot producer correspondence changed')
                if entry['state'] in TERMINAL:
                    if os.path.lexists(path):raise BoundaryError('Discarded snapshot name was replaced')
                    continue
                if entry['state']=='creation_intended':raise BoundaryError('Snapshot native producer identity was never captured')
                if not os.path.lexists(path):
                    receipt=storage._known(path)
                    if receipt and receipt['job_id']==attempt['job_id'] and receipt['kind']=='staging' and receipt['state'] in {'removed','absent_after_intent'} and (receipt['sha256'],receipt['size'])==(entry['sha256'],entry['size']) and json.loads(receipt['facts'])==json.loads(entry['facts']):
                        if entry['state']=='closed':entry=self._file_state(entry,'removal_intended')
                    elif entry['state'] not in {'removal_intended','disposition_set'}:
                        raise BoundaryError('Snapshot missing without accepted disposition intent')
                    self._file_state(entry,'removed' if entry['state']=='disposition_set' else 'absent_after_intent')
                    continue
                handle=stack.enter_context(VerifiedFile(path,delete=True))
                facts=handle.facts();single_stream(path)
                if facts!=json.loads(entry['facts']) or facts['links']!=1 or facts['size']!=entry['size'] or self._hash(handle)!=entry['sha256']:
                    raise BoundaryError('Published snapshot native identity or bytes changed')
                prepared.append((entry,path,handle))
            for entry,path,handle in prepared:
                source_proof();self._published(attempt);self._published_references(attempt,[str(path)]);boundary.revalidate()
                if entry['state']=='closed':entry=self._file_state(entry,'removal_intended')
                with storage._publication_transaction() as generation_db:
                    if entry['state']=='removal_intended':
                        handle.dispose();entry=self._file_state(entry,'disposition_set',_db=generation_db)
                    elif entry['state']=='disposition_set':handle.dispose()
                    else:raise BoundaryError('Snapshot retirement state is invalid')
                    handle.__exit__(None,None,None)
                    if os.path.lexists(path):raise BoundaryError('Discarded snapshot name survived or was replaced')
                    self._file_state(entry,'removed',_db=generation_db)
            # Generated roles were handed to StorageCleanup. Recognize only its
            # exact terminal native receipts; publication alone is not removal.
            all_removed=True
            for entry in self._files(attempt['job_id'],attempt['attempt_id']):
                if entry['state'] in TERMINAL:
                    if os.path.lexists(entry['path']):raise BoundaryError('Discarded published name was replaced')
                    continue
                receipt=storage._known(entry['path'])
                if not receipt or receipt['job_id']!=attempt['job_id'] or receipt['kind']!='staging' or receipt['state'] not in {'removed','absent_after_intent'} or (receipt['sha256'],receipt['size'])!=(entry['sha256'],entry['size']) or json.loads(receipt['facts'])!=json.loads(entry['facts']) or os.path.lexists(entry['path']):
                    all_removed=False;continue
                if entry['state']=='closed':entry=self._file_state(entry,'removal_intended')
                self._file_state(entry,'removed' if entry['state']=='disposition_set' else 'absent_after_intent')
            self._set_attempt(self._attempt(attempt['job_id'],attempt['attempt_id']),state='retired' if all_removed else 'published_held',reason='' if all_removed else 'Published generated-file cleanup has remaining obligations')

    def _legacy_prior(self, row):
        """A prior attempt with no ownership receipt (legacy) must have left its folder absent or empty."""
        prior_id=row.get('attempt_id')
        if prior_id and not self._rows('SELECT 1 FROM working_attempts WHERE job_id=? AND attempt_id=?',(row['job_id'],prior_id)):
            if str(uuid.UUID(prior_id))!=prior_id:raise BoundaryError('Prior working attempt identity is invalid')
            prior_stage=self.stage_root/row['job_id']/prior_id
            if os.path.lexists(prior_stage):
                with DirectoryBoundary(self.stage_root.anchor,prior_stage), os.scandir(prior_stage) as members:
                    if next(members,None) is not None:
                        raise BoundaryError('Legacy attempt still contains working inputs; exact retirement review required before another snapshot')
        return prior_id

    def admission_clear(self, row):
        """Read-only Retry pre-check of what admit() requires; it retires and writes nothing.

        Raises when a legacy prior folder still holds files or any receipt-owned attempt of the
        job is not yet retired.
        """
        self._legacy_prior(row)
        if self._rows("SELECT 1 FROM working_attempts WHERE job_id=? AND state!='retired' LIMIT 1",(row['job_id'],)):
            raise BoundaryError('Prior working attempt is not retired')

    def admit(self, row):
        """No new source/derived copy until registered prior cleanup debt clears."""
        prior_id=self._legacy_prior(row)
        for attempt in self._rows("SELECT * FROM working_attempts WHERE job_id=? AND (state!='retired' OR attempt_id=?) ORDER BY updated", (row['job_id'],prior_id)):
            self.retire(attempt['job_id'], attempt['attempt_id'])
            if self._attempt(attempt['job_id'], attempt['attempt_id'])['state'] != 'retired':
                raise BoundaryError('Prior working sources cannot be restaged; another attempt is not admitted')

    def reconcile(self, limit=1, storage=None):
        """One closed attempt per idle tick; audio/scan start preempts its hash IO.

        Attention/retained-source rows are revisited only on relevant explicit
        admission. Intent-only names never acquire a new native identity here.
        """
        if type(limit) is not int or not 1 <= limit <= 8:
            raise ValueError('Working reconciliation requires a bounded attempt count')
        attention = []
        if not self._reconcile_lock.acquire(blocking=False):return attention
        self._background_thread = threading.get_ident()
        try:
            states=('closed','published') if storage is not None else ('closed',)
            for attempt in self._rows("SELECT * FROM working_attempts WHERE state IN ("+','.join('?' for _ in states)+") ORDER BY updated LIMIT ?", (*states,limit)):
                try:
                    if attempt['state']=='published':self.discharge_published(attempt['job_id'],storage)
                    else:self.terminal(attempt['job_id'], attempt['attempt_id'])
                except InterruptedError:
                    break  # A normal audio/scan/close admission takes priority.
                except (OSError, ValueError, BoundaryError) as error:
                    current = self._attempt(attempt['job_id'], attempt['attempt_id'])
                    self._set_attempt(current, state='published_held' if attempt['state']=='published' else 'attention', reason=str(error)[:1000])
                    attention.append({'job_id': attempt['job_id'], 'attempt_id': attempt['attempt_id'], 'reason': str(error)})
        finally:
            self._background_thread = None
            self._reconcile_lock.release()
        return attention
