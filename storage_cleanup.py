"""Discard only verified owned copies after durable audiobook success.

Receipts survive a crash. An absent name is reconciled only after recorded
verified removal intent; unknown absence/replacement never counts as success.
"""
import contextlib
import hashlib
import json
import os
import re
import uuid
import sqlite3
import traceback
import threading
from sqlite_retry import transaction
from pathlib import Path
from scanner import connect
from native_io import BoundaryError, DirectoryBoundary, VerifiedFile, VerifiedDirectory, DirectoryNotEmptyError, DirectoryDispositionUnsupported, ordinary
from source_cleanup import packed, stamp, single_stream
# The MP3 trailing-tag repair's private copy and proof (audio_pipeline._mp3_tag_copy); exact producer receipts decide their bytes.
TAG_REPAIR=re.compile(r'tag-repair-[0-9a-f]{32}\.(?:mp3|json)')

TERMINAL = {'removed', 'absent_after_intent'}
# Ruling 76b (Sergei 2026-10-31): a folder cleanup an earlier version finished ('completed' or 'unsupported') while it kept a
# folder is run once more under 74e. One row per job once it has been looked at: never twice.
SWEEP_TABLE = 'CREATE TABLE IF NOT EXISTS source_folder_sweep(job_id TEXT PRIMARY KEY,outcome TEXT NOT NULL,at TEXT NOT NULL)'
KEPT_STATES = ('retained_nonempty', 'retained_unsupported', 'verified')

class StorageCleanup:
    def __init__(self, database, stage_root, recovery_root, guard=lambda: None,output_location=None,output_location_guard=None,repair_publication=None,repair_location_guard=None):
        self.database = str(database)
        self.stage_root = ordinary(stage_root)
        self.recovery_root = ordinary(recovery_root)
        self.guard = guard
        self.repair_publication=repair_publication;self.repair_location_guard=repair_location_guard
        self.output_location=output_location;self.output_location_guard=output_location_guard;self._location_local=threading.local()
        self._receipts = {}
        self.last_errors = {}
        self._phase = "not_started"
        self._disposition = "not_started"
        with connect(self.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS storage_cleanup_errors(id TEXT PRIMARY KEY,job_id TEXT,output_hash TEXT,created TEXT,diagnostic TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS storage_cleanup_jobs(job_id TEXT PRIMARY KEY, output_hash TEXT, state TEXT, reason TEXT, updated TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS storage_cleanup_authorizations(path TEXT PRIMARY KEY,job_id TEXT,output_hash TEXT,sha256 TEXT,size INTEGER,proof_hash TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS storage_cleanup_preserved(path TEXT PRIMARY KEY,job_id TEXT,reason TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS source_folder_cleanup_jobs(job_id TEXT PRIMARY KEY,output_hash TEXT,state TEXT,reason TEXT,updated TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS source_folder_cleanup_directories(job_id TEXT,path TEXT,identity TEXT,ancestry TEXT,state TEXT,reason TEXT,updated TEXT,PRIMARY KEY(job_id,path))')
            db.execute(SWEEP_TABLE)  # ruling 76b: the folder cleanups an earlier version finished, looked at again once
            db.execute('CREATE TABLE IF NOT EXISTS storage_cleanup_files(path TEXT PRIMARY KEY, job_id TEXT, kind TEXT, sha256 TEXT, size INTEGER, facts TEXT, state TEXT, updated TEXT)')
            # Recovery status reads these per book on every status read and book-list page; without an index
            # each lookup scanned the whole table (about 1.6 GB read per status on the real catalog).
            db.execute('CREATE INDEX IF NOT EXISTS storage_cleanup_files_job ON storage_cleanup_files(job_id,kind)')
            db.execute('CREATE INDEX IF NOT EXISTS storage_cleanup_preserved_job ON storage_cleanup_preserved(job_id)')

    @staticmethod
    def _cas(db, table, expected, target):
        key = 'path' if table != 'storage_cleanup_jobs' else 'job_id'
        actual = db.execute('SELECT * FROM '+table+' WHERE '+key+'=?', (target[key],)).fetchone()
        actual = dict(actual) if actual else None
        if actual == target:return target
        if actual != expected:raise BoundaryError('Cleanup receipt changed; preserved')
        if expected is None:
            columns=list(target)
            db.execute('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',tuple(target.values()))
        else:
            columns=list(target);prior=list(expected)
            changed=db.execute('UPDATE '+table+' SET '+','.join(c+'=?' for c in columns)+' WHERE '+ ' AND '.join(c+' IS ?' for c in prior),tuple(target.values())+tuple(expected.values())).rowcount
            if changed!=1:raise BoundaryError('Cleanup receipt CAS refused; preserved')
        return target

    def _set(self, job_id, output_hash, state, reason=''):
        timestamp=stamp();frozen=[]
        def write(db):
            row=db.execute('SELECT * FROM storage_cleanup_jobs WHERE job_id=?',(job_id,)).fetchone()
            row=dict(row) if row else None
            if not frozen:
                if row and row['output_hash']!=output_hash and not (row['output_hash']=='' and row['state']=='needs_attention' and state=='checking' and output_hash):raise BoundaryError('Cleanup output provenance changed')
                if row and row['state']=='completed':
                    if state=='completed' and row['reason']!=reason:raise BoundaryError('Completed receipt reason differs')
                    return row  # Never downgrade durable cleanup success.
                if row and row['state']=='removing' and state=='checking':
                    return row  # Resume revalidates without rolling back durable intent.
                if row and row['state']==state and row['reason']==reason:return row
                allowed={'checking':{'removing','needs_attention'},'removing':{'completed','needs_attention'},'needs_attention':{'checking'}}
                if (row and state not in allowed.get(row['state'],set())) or (not row and state not in {'checking','needs_attention'}):raise BoundaryError('Invalid cleanup job transition')
                frozen.extend([row,{'job_id':job_id,'output_hash':output_hash,'state':state,'reason':reason,'updated':timestamp}])
            return self._cas(db,'storage_cleanup_jobs',frozen[0],frozen[1])
        return transaction(self.database,write)

    def _diagnose(self, job_id, output_hash, error):
        frames=[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(error.__traceback__)[-12:]]
        diagnostic={'exception_class':type(error).__name__,'message':str(error)[:1000],
                    'sqlite_errorcode':getattr(error,'sqlite_errorcode',None),'sqlite_errorname':getattr(error,'sqlite_errorname',None),
                    'phase':self._phase,'disposition':self._disposition,'stack':frames,'secondary':[]}
        self.last_errors[job_id]=diagnostic
        while len(self.last_errors)>32:self.last_errors.pop(next(iter(self.last_errors)))
        values=(str(uuid.uuid4()),job_id,output_hash,stamp(),packed(diagnostic))
        try:
            def append(db):
                old=db.execute('SELECT * FROM storage_cleanup_errors WHERE id=?',(values[0],)).fetchone()
                if old:
                    if tuple(old)!=values:raise BoundaryError('Diagnostic identity changed')
                    return
                db.execute('INSERT INTO storage_cleanup_errors VALUES(?,?,?,?,?)',values)
            transaction(self.database,append)
        except Exception as secondary:
            diagnostic['secondary'].append({'operation':'diagnostic persistence','exception_class':type(secondary).__name__,'message':str(secondary)[:1000]})
        try:self._set(job_id,output_hash,'needs_attention',str(error))
        except Exception as secondary:
            diagnostic['secondary'].append({'operation':'state persistence','exception_class':type(secondary).__name__,'message':str(secondary)[:1000]})

    def status(self):
        with connect(self.database) as db:
            return [dict(r) for r in db.execute('SELECT * FROM storage_cleanup_jobs ORDER BY job_id')]

    def _job(self, job_id):
        with connect(self.database) as db:
            row = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()
        if not row or row['state'] != 'completed':
            raise BoundaryError('Only a durably completed audiobook can discard copies')
        if str(uuid.UUID(job_id)) != job_id:
            raise BoundaryError('Invalid completed job identity')
        m = json.loads(row['manifest']); out = json.loads(row['output'])
        if hashlib.sha256(packed(m).encode('utf-8')).hexdigest() != row['manifest_hash']:
            raise BoundaryError('Completed manifest identity changed')
        if out['job_id'] != job_id or out['validation'].get('passed') is not True:
            raise BoundaryError('Completed output validation is unavailable')
        from source_cleanup import CleanupJobs
        from encoding_policy import LEGACY_PROFILE
        with connect(self.database) as db:retirement=db.execute('SELECT 1 FROM source_cleanup WHERE job_id=?',(job_id,)).fetchone()
        if m.get('profile')!=LEGACY_PROFILE or retirement or m.get('cleanup_policy',{}).get('enabled'):
            CleanupJobs._validation_contract(m,out)
        else:
            from audio_jobs import AudioJobs
            AudioJobs._validate_record(out)
            v=out['validation']
            if v.get('checks')!='Output checks passed' or v.get('profile')!=m['profile'] or v.get('sha256')!=out['sha256'] or v.get('size')!=out['size']:
                raise BoundaryError('Legacy output checks do not match the recorded output')
        return m, out

    @contextlib.contextmanager
    def protected_output(self, job_id, guard=None):
        (guard or self.guard)()
        m, original = self._job(job_id)
        frozen_root=ordinary(m.get('output_root',m['root']))
        if ordinary(original.get('root',str(frozen_root)))!=frozen_root or ordinary(original['final_path'])!=ordinary(m['destination']):
            raise BoundaryError('Frozen publication provenance changed')
        out,envelope=self.output_location(original) if self.output_location else (original,None)
        root=ordinary(out.get('root',str(frozen_root)));final=ordinary(out['final_path'])
        if not final.is_relative_to(root) or final.suffix.lower()!='.m4b':raise BoundaryError('Completed output destination changed')
        prior=getattr(self._location_local,'publication',None);prior_effective=getattr(self._location_local,'effective',None)
        self._location_local.publication=(original,envelope);self._location_local.effective=out
        try:
            with DirectoryBoundary(root,final.parent) as ancestry,VerifiedFile(final) as handle:
                if out.get('identity') is not None and handle.facts()['identity']!=out['identity']:raise BoundaryError('Relocated output native identity changed; copies retained')
                if [list(x) for x in ancestry.identities]!=[list(x) for x in out['parent_identity']]:raise BoundaryError('Completed output ancestry changed')
                value=hashlib.sha256()
                for block in handle.chunks():(guard or self.guard)();value.update(block)
                if handle.facts()['size']!=out['size'] or value.hexdigest()!=out['sha256']:raise BoundaryError('Completed output bytes changed; copies retained')
                yield m,original
        finally:self._location_local.publication=prior;self._location_local.effective=prior_effective

    @contextlib.contextmanager
    def _publication_transaction(self):
        current=getattr(self._location_local,'publication',None)
        if not self.output_location_guard or current is None:
            yield None;return
        original,envelope=current
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE')
            if not self.output_location_guard(db,original,envelope,require_transaction=True):raise BoundaryError('Current publication changed before copy disposition')
            for derived in getattr(self._location_local,'derived_publications',()):
                if not self.repair_location_guard or not self.repair_location_guard(db,derived['original'],derived['envelope'],kind=derived['kind'],repair_journal_sha256=derived['journal_sha256'],require_transaction=True):raise BoundaryError('Authorized repaired publication changed before copy disposition')
            prior=getattr(self._location_local,'disposal_db',None);self._location_local.disposal_db=db
            try:yield db
            finally:self._location_local.disposal_db=prior

    def _known(self, path):
        with connect(self.database) as db:
            row = db.execute('SELECT * FROM storage_cleanup_files WHERE path=?', (str(path),)).fetchone()
        return dict(row) if row else None

    def _prepare(self, stack, job_id, kind, path, root, expected=None):
        from producer_recovery import protected_dependency
        with connect(self.database) as db:
            if protected_dependency(db,[path]):raise BoundaryError('Isolated old files and source dependencies are retained')
        path = ordinary(path); root = ordinary(root)
        if not path.is_relative_to(root) or path == root:
            raise BoundaryError('Copy is outside its owned storage root')
        ancestry = stack.enter_context(DirectoryBoundary(root.anchor, path.parent))
        parent = path.parent
        while parent.is_relative_to(root):
            if (parent / '.git').exists():
                raise BoundaryError('Nested Git data preserved')
            if parent == root:break
            parent = parent.parent
        old = self._known(path)
        try:
            path.stat()
        except FileNotFoundError:
            if old and old['job_id'] == job_id and old['kind'] == kind and old['state'] in TERMINAL | {'removal_intended', 'disposition_set'}:
                if expected and (old['sha256'], old['size']) != expected[:2]:
                    raise BoundaryError('Missing-copy receipt differs from approved bytes')
                if old['state'] not in TERMINAL:
                    state = 'removed' if old['state'] == 'disposition_set' else 'absent_after_intent'
                    self._receipts[str(path)]=old
                    self._file_state(path, state)
                return None
            raise BoundaryError('Copy is missing without verified removal intent: ' + str(path))
        if expected is None:
            raise BoundaryError('Exact producer artifact receipt is required')
        if old and old['state'] in TERMINAL:
            raise BoundaryError('A replacement at a discarded-copy path was preserved')
        handle = stack.enter_context(VerifiedFile(path, delete=True))
        facts = handle.facts()
        if facts['links'] != 1:
            raise BoundaryError('Copy has another filesystem alias; preserved')
        single_stream(path)
        sha = handle.sha256()
        if expected and (sha, facts['size']) != expected[:2]:
            raise BoundaryError('Owned copy differs from approved bytes: ' + str(path))
        if expected and len(expected)>2 and str(facts['modified'])!=str(expected[2]):
            raise BoundaryError('Recovery-copy timestamp changed')
        if old:
            if old['job_id'] != job_id or old['kind'] != kind or (old['sha256'], old['size']) != (sha, facts['size']) or json.loads(old['facts']) != facts:
                raise BoundaryError('Copy identity changed after cleanup intent; preserved')
        else:
            target={'path':str(path),'job_id':job_id,'kind':kind,'sha256':sha,'size':facts['size'],'facts':packed(facts),'state':'verified','updated':stamp()}
            def insert(db):
                current=db.execute('SELECT * FROM storage_cleanup_files WHERE path=?',(str(path),)).fetchone()
                if current:
                    current=dict(current)
                    if current['state']!='verified' or any(current[k]!=target[k] for k in target if k!='updated'):raise BoundaryError('Verified cleanup receipt provenance changed')
                    return current
                return self._cas(db,'storage_cleanup_files',None,target)
            old=transaction(self.database,insert)
        self._receipts[str(path)]=old
        return path, handle, ancestry

    def record_absent(self, job_id, kind, path, expected):
        """A recorded copy that is already gone (removed outside the app, or by an interrupted earlier
        purge): a terminal receipt, so the set can close and a rerun skips it. Never touches a file."""
        target = {'path': str(path), 'job_id': job_id, 'kind': kind, 'sha256': expected[0], 'size': expected[1],
                  'facts': packed({'absent': True}), 'state': 'absent_after_intent', 'updated': stamp()}
        def insert(db):
            current = db.execute('SELECT * FROM storage_cleanup_files WHERE path=?', (str(path),)).fetchone()
            if current:
                current = dict(current)
                if current['job_id'] != job_id or current['kind'] != kind:raise BoundaryError('Copy receipt belongs to other work')
                if current['state'] in TERMINAL:return current
                return self._cas(db, 'storage_cleanup_files', current, dict(current, state='absent_after_intent', updated=stamp()))
            return self._cas(db, 'storage_cleanup_files', None, target)
        return transaction(self.database, insert)

    def _file_state(self, path, state):
        expected=self._receipts.get(str(path))
        if not expected:raise BoundaryError('No held cleanup receipt provenance')
        held_db=getattr(self._location_local,'disposal_db',None)
        apply=lambda change:self._cas(held_db,'storage_cleanup_files',expected,change) if held_db is not None else transaction(self.database,lambda db:self._cas(db,'storage_cleanup_files',expected,change))
        if expected['state']==state:
            return apply(expected)
        allowed={'verified':{'removal_intended'},'removal_intended':{'disposition_set','absent_after_intent'},'disposition_set':{'removed'}}
        if state not in allowed.get(expected['state'],set()):raise BoundaryError('Invalid cleanup file transition')
        target=dict(expected,state=state,updated=stamp())
        result=apply(target)
        self._receipts[str(path)]=result
        return result

    def _dispose(self, prepared, guard=None):
        for path, handle, ancestry in prepared:
            (guard or self.guard)(); ancestry.revalidate()
            self._phase='commit removal intent'
            self._file_state(path, 'removal_intended')
            self._disposition='intent_committed'
            with self._publication_transaction():
                handle.dispose()
                self._disposition='disposition_called'
                self._phase='commit disposition receipt'
                self._file_state(path, 'disposition_set')
                self._disposition='disposition_receipt_committed'
                handle.__exit__(None, None, None)
                try:
                    path.stat()
                except FileNotFoundError:
                    self._disposition='confirmed_absent'
                    self._phase='commit removed receipt'
                    self._file_state(path, 'removed')
                else:
                    raise BoundaryError('Verified copy disposition did not remove its name')

    def _source_safety(self, stack, job_id, manifest, output):
        with connect(self.database) as db:
            row = db.execute('SELECT * FROM source_cleanup WHERE job_id=?', (job_id,)).fetchone()
            members = [dict(r) for r in db.execute('SELECT * FROM cleanup_members WHERE cleanup_id=?', (row['id'],))] if row else []
            retired = [dict(r) for r in db.execute('SELECT * FROM source_retirements WHERE cleanup_id=?', (row['id'],))] if row else []
        sources = manifest['sources']
        if row:
            intent = json.loads(row['intent'])
            if row['state'] != 'completed' or intent['manifest'] != manifest or intent['output'] != output:
                raise BoundaryError('Source retirement is incomplete or changed; copies retained')
            if len(members) != len(sources) or len(retired) != len(sources):
                raise BoundaryError('Exact source-retirement proof is incomplete')
            for s in sources:
                member = next((r for r in members if r['path'] == s['path']), None)
                retirement = next((r for r in retired if r['path'] == s['path']), None)
                if not member or not retirement or member['state'] != 'removed' or retirement['state'] != 'removed' or retirement['job_id'] != job_id or retirement['source_hash'] != s['sha256'] or retirement['size'] != s['size'] or str(retirement['modified']) != str(s['modified']):
                    raise BoundaryError('Original retirement correspondence changed')
                stack.enter_context(self._folder_boundary(job_id,manifest['root'],Path(s['path']).parent))
                try:
                    Path(s['path']).stat()
                except FileNotFoundError:
                    pass
                else:
                    raise BoundaryError('A replacement original was preserved; copies retained')
            return row, members
        if manifest.get('cleanup_policy', {}).get('enabled'):
            raise BoundaryError('Enrolled source retirement has not completed')
        for s in sources:
            stack.enter_context(DirectoryBoundary(manifest['root'], Path(s['path']).parent))
            handle = stack.enter_context(VerifiedFile(s['path']))
            if handle.facts()['size'] != s['size'] or str(handle.facts()['modified']) != str(s['modified']) or handle.sha256() != s['sha256']:
                raise BoundaryError('Retained original source changed; staging retained')
        return None, []

    def snapshot_source_safety(self, stack, job_id, manifest, output, guard=None):
        """Prove redundant published snapshots without retiring any original.

        An enrolled/ADS-held source cleanup does not prohibit independently
        verifying surviving original bytes. Missing sources require the existing
        accepted retirement contract and actual recovery survival or disposal.
        """
        guard=guard or self.guard
        def sha(handle):
            value=hashlib.sha256()
            for block in handle.chunks():
                guard();value.update(block)
            return value.hexdigest()
        originals=stack.enter_context(contextlib.ExitStack())
        try:
            for source in manifest['sources']:
                path=ordinary(source['path'])
                if not path.is_relative_to(ordinary(manifest['root'])):
                    raise BoundaryError('Frozen source escaped its library')
                originals.enter_context(DirectoryBoundary(path.anchor,path.parent))
                handle=originals.enter_context(VerifiedFile(path))
                facts=handle.facts()
                if facts['links']!=1 or facts['size']!=source['size'] or str(facts['modified'])!=str(source['modified']) or sha(handle)!=source['sha256']:
                    raise BoundaryError('Frozen surviving source differs')
            return lambda: guard()
        except InterruptedError:raise
        except (OSError,BoundaryError):
            originals.close()
        with connect(self.database) as db:
            retirement=db.execute('SELECT state FROM source_cleanup WHERE job_id=?',(job_id,)).fetchone()
        if not retirement or retirement['state']!='completed':
            raise BoundaryError('Missing originals have no accepted completed retirement')
        cleanup,members=self._source_safety(stack,job_id,manifest,output)
        if not cleanup:
            raise BoundaryError('Snapshot source survival is unavailable')
        with connect(self.database) as db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            retention=db.execute('SELECT * FROM recovery_retention WHERE job_id=?',(job_id,)).fetchone() if 'recovery_retention' in tables else None
            completion=db.execute('SELECT * FROM recovery_completion WHERE cleanup_id=?',(cleanup['id'],)).fetchone()
            receipts={r['path']:dict(r) for r in db.execute("SELECT * FROM storage_cleanup_files WHERE job_id=? AND kind='recovery'",(job_id,))}
        if not completion or completion['job_id']!=job_id:
            raise BoundaryError('Immutable recovery completion is unavailable')
        location=ordinary(self.recovery_root/cleanup['id'])
        deleted=bool(retention and retention['state']=='deleted')
        missing_location=deleted and not os.path.lexists(location)
        stack.enter_context(DirectoryBoundary(location.anchor,self.recovery_root if missing_location else location))
        if deleted:
            from recovery_retention import moment,HOURS
            from datetime import timedelta
            if retention['cleanup_id']!=cleanup['id'] or retention['output_hash']!=output['sha256'] or retention['completed_at']!=completion['completed_at'] or (moment(completion['completed_at'])+timedelta(hours=HOURS)).isoformat()!=retention['expires_at']:
                raise BoundaryError('Terminal recovery provenance changed')
            if retention['actor'] not in {'manual','automatic','legacy'} or moment(retention['deleted_at'])<moment(completion['completed_at']):
                raise BoundaryError('Actual recovery disposal completion is unavailable')
            if retention['actor']=='automatic' and moment(retention['deleted_at'])<moment(retention['expires_at']):
                raise BoundaryError('Automatic recovery disposal predates retention deadline')
        elif retention and retention['state'] not in {'retained'}:
            raise BoundaryError('Recovery has an active or uncertain operation')
        for source in manifest['sources']:
            member=next(r for r in members if r['path']==source['path'])
            backup=ordinary(member['backup'])
            if backup.parent!=location or not member['backup_facts'] or member.get('restore_intent'):
                raise BoundaryError('Recovery input ownership is unavailable or restoring')
            facts=json.loads(member['backup_facts'])
            receipt=receipts.get(str(backup))
            if deleted:
                if not receipt or receipt['state'] not in TERMINAL or receipt['job_id']!=job_id or receipt['kind']!='recovery' or (receipt['sha256'],receipt['size'])!=(source['sha256'],source['size']) or json.loads(receipt['facts'])!=facts or os.path.lexists(backup):
                    raise BoundaryError('Actual terminal recovery receipt is incomplete or replaced')
            else:
                if receipt and receipt['state'] in TERMINAL | {'removal_intended','disposition_set'}:
                    raise BoundaryError('Recovery disposal has not reached a terminal outcome')
                handle=stack.enter_context(VerifiedFile(backup))
                if handle.facts()!=facts or facts['links']!=1 or facts['size']!=source['size'] or str(facts['modified'])!=str(source['modified']) or sha(handle)!=source['sha256']:
                    raise BoundaryError('Registered recovery source changed')
        def revalidate():
            guard()
            with connect(self.database) as db:
                current=db.execute('SELECT * FROM source_cleanup WHERE job_id=?',(job_id,)).fetchone()
                current_members=[dict(r) for r in db.execute('SELECT * FROM cleanup_members WHERE cleanup_id=?',(cleanup['id'],))]
                current_retention=db.execute('SELECT * FROM recovery_retention WHERE job_id=?',(job_id,)).fetchone() if 'recovery_retention' in tables else None
            if not current or dict(current)!=dict(cleanup) or current_members!=members or (dict(current_retention) if current_retention else None)!=(dict(retention) if retention else None):
                raise BoundaryError('Recovery/source retirement changed during snapshot disposal')
            if missing_location and os.path.lexists(location):
                raise BoundaryError('A replacement recovery directory appeared')
            if deleted and any(os.path.lexists(member['backup']) for member in members):
                raise BoundaryError('A replacement recovery member appeared')
        revalidate()
        return revalidate

    def _staging(self, stack, job_id, manifest, output):
        job = self.stage_root / job_id
        if not job.exists():
            return []
        stack.enter_context(DirectoryBoundary(self.stage_root.anchor, job))
        marker = stack.enter_context(VerifiedFile(job / 'ownership.json'))
        if marker.facts()['size'] > 16 * 1024 * 1024 or json.loads(b''.join(marker.chunks()).decode('utf-8')) != {'job_id': job_id, 'manifest': manifest}:
            raise BoundaryError('Private staging ownership changed')
        expected = {f'source{i:05d}' + Path(s['path']).suffix.lower(): (s['sha256'], s['size']) for i, s in enumerate(manifest['sources'])}
        targets = []
        recorded=output['validation'].get('staging_artifacts',{})
        with connect(self.database) as db:
            authorizations={r['path']:dict(r) for r in db.execute('SELECT * FROM storage_cleanup_authorizations WHERE job_id=? AND output_hash=?',(job_id,output['sha256']))}
        for attempt in job.iterdir():
            if attempt.name == 'ownership.json':
                continue
            try:
                if str(uuid.UUID(attempt.name)) != attempt.name:
                    raise ValueError()
            except ValueError:
                raise BoundaryError('Unknown staging content preserved: ' + attempt.name) from None
            stack.enter_context(DirectoryBoundary(job, attempt))
            for path in attempt.iterdir():
                name = path.name
                known = name in expected or name in {'cover.jpg', 'cover.png', 'checked.m4b', 'compatible.m4b', 'inputs.txt', 'chapters.txt'} or re.fullmatch(r'[0-9a-f]{32}\.(stderr|decode-stderr|stdout|jpg|png)', name) or TAG_REPAIR.fullmatch(name)
                from encoding_policy import AUTOMATIC_PROFILE
                normalized=manifest.get('profile')==AUTOMATIC_PROFILE and re.fullmatch(r'normalized[0-9]{5}\.wav',name) and recorded.get('attempt_id')==attempt.name and name in recorded.get('files',{})
                known=bool(known or normalized)
                if not known:
                    raise BoundaryError('Unknown staging content preserved: ' + name)
                if name.endswith(('.jpg', '.png')):
                    # Every staging image is the reviewed cover, including extracted validation artwork.
                    with VerifiedFile(path) as image:
                        if image.sha256() != manifest['cover']['sha256']:
                            raise BoundaryError('Staging artwork identity changed')
                approved=expected.get(name)
                if recorded.get('attempt_id')==attempt.name and name in recorded.get('files',{}):
                    entry=recorded['files'][name];approved=(entry['sha256'],entry['size'])
                elif name.endswith(('.jpg','.png')):
                    approved=(manifest['cover']['sha256'],Path(manifest['cover']['path']).stat().st_size)
                elif name in ('checked.m4b','compatible.m4b'):
                    approved=(output['sha256'],output['size'])
                elif name=='inputs.txt':
                    text=''.join(f"file '{n}'\n" for n in expected)
                    # Historical Windows write_text used CRLF; current producer receipts use exact bytes.
                    raw=text.replace('\n','\r\n').encode('utf-8');approved=(hashlib.sha256(raw).hexdigest(),len(raw))
                authorization=authorizations.get(str(path))
                if authorization:approved=(authorization['sha256'],authorization['size'])
                if approved is None:
                    if re.fullmatch(r'[0-9a-f]{32}\.(stderr|decode-stderr|stdout)',name) or name=='chapters.txt':
                        values=(str(path),job_id,'Legacy evidence lacks exact producer bytes; preserved')
                        def preserve(db):
                            prior=db.execute('SELECT * FROM storage_cleanup_preserved WHERE path=?',(values[0],)).fetchone()
                            if prior:
                                if tuple(prior)!=values:raise BoundaryError('Preserved evidence provenance changed')
                                return
                            db.execute('INSERT INTO storage_cleanup_preserved VALUES(?,?,?)',values)
                        transaction(self.database,preserve)
                        continue
                    raise BoundaryError('Exact producer artifact receipt is required: '+name)
                targets.append((path, 'staging', approved))
        # Include interrupted disposition receipts whose names are already absent.
        with connect(self.database) as db:
            for r in db.execute("SELECT path,sha256,size FROM storage_cleanup_files WHERE job_id=? AND kind='staging' AND state NOT IN ('removed','absent_after_intent')", (job_id,)):
                p = ordinary(r['path'])
                if not p.is_relative_to(job):
                    raise BoundaryError('Staging receipt escaped its owned job')
                if p not in [x[0] for x in targets]:
                    targets.append((p, 'staging', (r['sha256'], r['size'])))
        return targets

    @staticmethod
    def working_name(manifest, name):
        """Shared finite disposable role policy; never includes source snapshots."""
        disposable=name in {'cover.jpg','cover.png','checked.m4b','compatible.m4b','inputs.txt','chapters.txt'} or re.fullmatch(r'[0-9a-f]{32}\.(stderr|decode-stderr|stdout|jpg|png)',name) or TAG_REPAIR.fullmatch(name)
        from encoding_policy import AUTOMATIC_PROFILE
        return bool(disposable or (manifest.get('profile')==AUTOMATIC_PROFILE and re.fullmatch(r'normalized[0-9]{5}\.wav',name)))

    def working_pending(self, job_id):
        """Read-only scheduling hint; it never authorizes disposition or Ready.

        Startup remains inactive. Explicit resume checks completed jobs, including
        retirement attention, without repeatedly hashing already disposed media.
        """
        manifest,output=self._job(job_id)
        recorded=output['validation'].get('staging_artifacts',{})
        attempt_id=recorded.get('attempt_id')
        if not attempt_id:return False  # No exact producer receipt, no candidate.
        if str(uuid.UUID(attempt_id))!=attempt_id:raise BoundaryError('Invalid published attempt identity')
        snapshots={f'source{i:05d}'+Path(item['path']).suffix.lower() for i,item in enumerate(manifest['sources'])}
        from encoding_policy import AUTOMATIC_PROFILE
        for name,entry in recorded.get('files',{}).items():
            if name in snapshots:continue
            disposable=self.working_name(manifest,name)
            if not disposable:continue
            path=self.stage_root/job_id/attempt_id/name
            if path.exists():return True  # Includes a replacement at a terminal name.
            old=self._known(path)
            if not old or old['job_id']!=job_id or old['kind']!='staging' or old['state'] not in TERMINAL or (old['sha256'],old['size'])!=(entry['sha256'],entry['size']):return True
        return False

    def working_files(self, job_id, dry_run=False, normalized_only=False, expected_plan=None):
        """Discard exact published-attempt disposable receipts, preserving snapshots.

        Historical cleanup uses this same path. Unknown files/attempts are never
        selected; publication and native byte/name/stream guards stay mandatory.
        This never satisfies the full staging/retirement/Ready obligation.
        """
        with self.protected_output(job_id) as (manifest, output):
            recorded = output['validation'].get('staging_artifacts', {})
            attempt_id = recorded.get('attempt_id')
            if not attempt_id or str(uuid.UUID(attempt_id)) != attempt_id:
                raise BoundaryError('Exact published-attempt receipt is required')
            job = self.stage_root / job_id
            attempt = job / attempt_id
            snapshot_names = {f'source{i:05d}' + Path(item['path']).suffix.lower() for i, item in enumerate(manifest['sources'])}
            result = []
            with contextlib.ExitStack() as stack:
                stack.enter_context(DirectoryBoundary(self.stage_root.anchor, attempt))
                marker = stack.enter_context(VerifiedFile(job / 'ownership.json'))
                if marker.facts()['size'] > 16*1024*1024 or json.loads(b''.join(marker.chunks()).decode('utf-8')) != {'job_id':job_id, 'manifest':manifest}:
                    raise BoundaryError('Private staging ownership changed')
                prepared = []
                for name, entry in recorded.get('files', {}).items():
                    if name in snapshot_names:
                        continue
                    disposable=self.working_name(manifest,name)


                    if normalized_only and not re.fullmatch(r'normalized[0-9]{5}\.wav',name):continue
                    if not disposable:
                        continue  # A receipt alone never expands the disposable-name policy.
                    path = attempt / name
                    expected = (entry['sha256'], entry['size'])
                    if dry_run:
                        old = self._known(path)
                        if not path.exists():
                            if old and old['job_id']==job_id and old['kind']=='staging' and old['state'] in TERMINAL | {'removal_intended','disposition_set'} and (old['sha256'],old['size'])==expected:
                                continue
                            raise BoundaryError('Working file absent without verified removal intent')
                        ancestry=stack.enter_context(DirectoryBoundary(self.stage_root.anchor,path.parent))
                        parent=path.parent
                        while parent.is_relative_to(self.stage_root):
                            if (parent/'.git').exists():raise BoundaryError('Nested Git data preserved')
                            if parent==self.stage_root:break
                            parent=parent.parent
                        handle=stack.enter_context(VerifiedFile(path))
                        facts=handle.facts();single_stream(path)
                        if facts['links']!=1 or (handle.sha256(),facts['size'])!=expected:
                            raise BoundaryError('Working file differs from its producer receipt')
                        if old and (old['job_id']!=job_id or old['kind']!='staging' or old['state'] in TERMINAL or json.loads(old['facts'])!=facts):
                            raise BoundaryError('Working file cleanup identity changed')
                    else:
                        item=self._prepare(stack,job_id,'staging',path,self.stage_root,expected)
                        if not item:continue
                        prepared.append(item)
                        facts=item[1].facts()
                    result.append({'path':str(path),'sha256':expected[0],'size':expected[1],'facts':facts})
                if expected_plan is not None and result!=expected_plan:
                    raise BoundaryError('Working cleanup dry-run identity changed; preserved')
                if not dry_run:self._dispose(prepared)
            return {'job_id':job_id,'output_sha256':output['sha256'],'files':result,'bytes':sum(item['size'] for item in result),'dry_run':dry_run}

    def run(self, job_id, include_recovery=False):
        output_hash = ''
        self._phase='verify completed output';self._disposition='not_started'
        try:
            with self.protected_output(job_id) as (manifest, output):
                output_hash = output['sha256']
                previous = next((r for r in self.status() if r['job_id'] == job_id), None)
                if previous and previous['state'] == 'completed' and previous['output_hash'] == output_hash:
                    return
                self._phase='commit checking receipt'
                self._set(job_id, output_hash, 'checking')
                with contextlib.ExitStack() as stack:
                    self._phase='verify source retirement'
                    cleanup, members = self._source_safety(stack, job_id, manifest, output)
                    self._phase='verify staging'
                    targets = self._staging(stack, job_id, manifest, output)
                    if cleanup and include_recovery:
                        recovery_dir=self.recovery_root/cleanup['id']
                        stack.enter_context(DirectoryBoundary(self.recovery_root.anchor,recovery_dir))
                        expected_names={Path(r['backup']).name for r in members}
                        if any(p.name not in expected_names for p in recovery_dir.iterdir()):
                            raise BoundaryError('Unknown recovery content preserved')
                        for s in manifest['sources']:
                            member = next(r for r in members if r['path'] == s['path'])
                            p = ordinary(member['backup'])
                            if p.parent != self.recovery_root / cleanup['id']:
                                raise BoundaryError('Recovery-copy location changed')
                            targets.append((p, 'recovery', (s['sha256'], s['size'], s['modified'])))
                    self._phase='prepare verified file receipts'
                    prepared = []
                    for path, kind, expected in targets:
                        item = self._prepare(stack, job_id, kind, path, self.recovery_root if kind == 'recovery' else self.stage_root, expected)
                        if item:
                            prepared.append(item)
                    # All copies and obligations are checked before any disposition.
                    self._phase='commit removing receipt'
                    self._set(job_id, output_hash, 'removing')
                    self._dispose(prepared)
                self._phase='commit completed receipt'
                self._set(job_id, output_hash, 'completed')
        except Exception as error:
            self._diagnose(job_id,output_hash,error)
            raise


    def folder_status(self, job_id=None):
        with connect(self.database) as db:
            rows=[dict(r) for r in db.execute('SELECT * FROM source_folder_cleanup_jobs'+(' WHERE job_id=?' if job_id else '')+' ORDER BY job_id',(job_id,) if job_id else ())]
            for row in rows:
                states=[r[0] for r in db.execute('SELECT state FROM source_folder_cleanup_directories WHERE job_id=?',(row['job_id'],))]
                row.update(total=len(states),removed=states.count('removed'),absent_after_intent=states.count('absent_after_intent'),retained=states.count('retained_nonempty'),unsupported=states.count('retained_unsupported'))
        return (rows[0] if rows else None) if job_id else rows

    def _folder_set(self, job_id, output_hash, state, reason=''):
        with connect(self.database) as db:
            db.execute('INSERT OR REPLACE INTO source_folder_cleanup_jobs VALUES(?,?,?,?,?)',(job_id,output_hash,state,reason,stamp()))

    def _folder_known(self, job_id, path):
        with connect(self.database) as db:
            row=db.execute('SELECT * FROM source_folder_cleanup_directories WHERE job_id=? AND path=?',(job_id,str(path))).fetchone()
        return dict(row) if row else None

    def _folder_state(self, job_id, path, state, reason=''):
        with connect(self.database) as db:
            db.execute('UPDATE source_folder_cleanup_directories SET state=?,reason=?,updated=? WHERE job_id=? AND path=?',(state,reason,stamp(),job_id,str(path)))

    def _folder_obligations(self, job_id, manifest, output):
        """Require the existing exact retirement and completed copy-purge proofs."""
        current_m,current_out=self._job(job_id)
        if current_m!=manifest or current_out!=output:raise BoundaryError('Completed folder-cleanup provenance changed')
        with connect(self.database) as db:
            row=db.execute('SELECT * FROM source_cleanup WHERE job_id=?',(job_id,)).fetchone()
            storage=db.execute('SELECT * FROM storage_cleanup_jobs WHERE job_id=?',(job_id,)).fetchone()
            if not row or row['state']!='completed':raise BoundaryError('Source retirement must complete before folder cleanup')
            intent=json.loads(row['intent'])
            if intent['manifest']!=manifest or intent['output']!=output or intent['job_id']!=job_id or intent['id']!=row['id']:
                raise BoundaryError('Completed source-retirement intent changed')
            if not storage or storage['state']!='completed' or storage['output_hash']!=output['sha256']:
                raise BoundaryError('Verified temporary-copy cleanup must complete before folder cleanup')
            members=[dict(r) for r in db.execute('SELECT * FROM cleanup_members WHERE cleanup_id=?',(row['id'],))]
            retired=[dict(r) for r in db.execute('SELECT * FROM source_retirements WHERE cleanup_id=?',(row['id'],))]
        if len(members)!=len(manifest['sources']) or len(retired)!=len(manifest['sources']):
            raise BoundaryError('Exact source-retirement proof is incomplete')
        for source in manifest['sources']:
            member=next((r for r in members if r['path']==source['path']),None)
            retirement=next((r for r in retired if r['path']==source['path']),None)
            if not member or not retirement or member['state']!='removed' or retirement['state']!='removed' or retirement['root']!=manifest['root'] or retirement['job_id']!=job_id or retirement['source_hash']!=source['sha256'] or retirement['size']!=source['size'] or str(retirement['modified'])!=str(source['modified']):
                raise BoundaryError('Original retirement correspondence changed')
        return row

    @staticmethod
    def _folder_candidates(manifest):
        root=ordinary(manifest['root']);candidates=set()
        for source in manifest['sources']:
            path=ordinary(source['path'])
            from encoding_policy import AUTOMATIC_PROFILE
            formats={'.mp3','.m4a','.m4b','.aac','.flac','.ogg','.opus','.wav','.wma'} if manifest.get('profile')==AUTOMATIC_PROFILE else {'.mp3'}
            if not path.is_relative_to(root) or path==root or path.suffix.lower() not in formats:
                raise BoundaryError('Retired source is outside its approved audiobook library')
            parent=path.parent
            # Audit m2: never a direct child of the source root (the Unsorted folder, an author folder); only the
            # book's own folders below it.
            while parent!=root and parent.parent!=root:
                if not parent.is_relative_to(root):raise BoundaryError('Source-folder ancestry escaped the library')
                candidates.add(parent);parent=parent.parent
        return sorted(candidates,key=lambda p:(-len(p.parts),str(p).casefold()))

    @contextlib.contextmanager
    def _folder_boundary(self, job_id, root, parent, expected=None):
        """Protect surviving ancestors; missing ones need our own durable intent."""
        root=ordinary(root);parent=ordinary(parent)
        if not parent.is_relative_to(root):raise BoundaryError('Source-folder ancestor is outside the library')
        current=parent;missing=[]
        while True:
            try:current.lstat();break
            except FileNotFoundError:
                if current==root:raise BoundaryError('The source-library root is unavailable') from None
                known=self._folder_known(job_id,current)
                if not known or known['state'] not in TERMINAL|{'removal_intended','disposition_set'}:
                    raise BoundaryError('Source-folder ancestor is missing without verified removal intent') from None
                missing.append((current,known));current=current.parent
        with DirectoryBoundary(root,current) as boundary:
            if expected is not None and [list(i) for i in boundary.identities]!=expected[:len(boundary.identities)]:
                raise BoundaryError('Source-folder ancestor identity changed')
            for path,known in missing:
                chain=json.loads(known['ancestry'])
                if chain[:len(boundary.identities)]!=[list(i) for i in boundary.identities]:
                    raise BoundaryError('Removed source-folder ancestry changed')
                if expected is not None and chain!=expected[:len(chain)]:
                    raise BoundaryError('Removed source-folder proof differs from the candidate ancestry')
            inspected=current
            while inspected.is_relative_to(root):
                try:(inspected/'.git').lstat()
                except FileNotFoundError:pass
                else:raise BoundaryError('Nested Git source data preserved')
                if inspected==root:break
                inspected=inspected.parent
            yield boundary

    def _folder_sources_absent(self, job_id, manifest):
        root=ordinary(manifest['root'])
        for source in manifest['sources']:
            path=ordinary(source['path']);known=self._folder_known(job_id,path.parent)
            expected=json.loads(known['ancestry']) if known else None
            with self._folder_boundary(job_id,root,path.parent,expected):
                try:path.lstat()
                except FileNotFoundError:pass
                else:raise BoundaryError('A replacement original was preserved; source-folder cleanup stopped')

    def _capture_folder(self, job_id, root, path):
        known=self._folder_known(job_id,path);expected=json.loads(known['ancestry']) if known else None
        with self._folder_boundary(job_id,root,path.parent,expected) as boundary:
            try:
                with VerifiedDirectory(path) as target:
                    facts=target.facts();ancestry=[list(i) for i in boundary.identities]+[[str(path),*facts['identity']]]
                    if known:
                        if known['state'] in TERMINAL:raise BoundaryError('A replacement at a removed source-folder path was preserved')
                        if json.loads(known['identity'])!=facts or expected!=ancestry:
                            raise BoundaryError('Source-folder native identity changed; replacement preserved')
                    else:
                        with connect(self.database) as db:
                            db.execute('INSERT INTO source_folder_cleanup_directories VALUES(?,?,?,?,?,?,?)',(job_id,str(path),packed(facts),packed(ancestry),'verified','',stamp()))
            except FileNotFoundError:
                if not known or known['state'] not in TERMINAL|{'removal_intended','disposition_set'}:
                    raise BoundaryError('Source folder is missing without verified removal intent') from None
                if known['state'] not in TERMINAL:
                    self._folder_state(job_id,path,'removed' if known['state']=='disposition_set' else 'absent_after_intent','Reconciled absence from durable exact-directory intent')
                return None
        return self._folder_known(job_id,path)

    # Ruling 74e (Sergei, 2026-10-31): a book's own source folder goes once no audio file is left in it, even when covers or
    # other non-audio files remain. A bound past which a folder counts as holding something else (its files stay).
    LEFTOVER_LIMIT = 500

    def _held(self, job_id, manifest, paths):
        """The leftover paths another book, an unfinished job or a reacquire record still names, as normcase keys: another
        current book's member, a source or cover of any other job that has not completed (its cover may still be read), or a
        reacquire record that is not archived. Read-only; an unreadable catalog holds everything."""
        wanted = {os.path.normcase(str(p)) for p in paths}
        held = set()
        try:
            with connect(self.database) as db:
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'catalog_group_members' in tables and 'book_groups' in tables:
                    for (member,) in db.execute('SELECT c.path FROM catalog_group_members c JOIN book_groups g ON g.id=c.group_id WHERE g.superseded=0 AND g.id IS NOT ?', (manifest.get('candidate_id'),)):
                        held.add(os.path.normcase(str(member)))
                for (raw,) in db.execute("SELECT manifest FROM audio_jobs WHERE job_id!=? AND state!='completed'", (job_id,)):
                    other = json.loads(raw)
                    for source in other.get('sources') or []:
                        if isinstance(source, dict) and source.get('path'):held.add(os.path.normcase(str(source['path'])))
                    cover = other.get('cover')
                    if isinstance(cover, dict) and cover.get('path'):held.add(os.path.normcase(str(cover['path'])))
                if 'reacquire_markers' in tables:
                    for (snapshot,) in db.execute("SELECT snapshot FROM reacquire_markers WHERE state!='archived'"):
                        for member in (json.loads(snapshot) or {}).get('members') or []:
                            if isinstance(member, dict) and member.get('path'):held.add(os.path.normcase(str(member['path'])))
        except (sqlite3.Error, ValueError, TypeError, AttributeError):
            return wanted
        return wanted & held

    def _leftovers(self, job_id, manifest, path, own):
        """What stands between the folder and its removal: ([{'path','size'}] to remove first, reason to keep it or None).

        Ruling 74e: only a folder a source of this book sat in (own) loses its other files, and only when nothing in it is
        audio in any format (book_delete.SOUND, as Delete book counts it), a subfolder or a link, every file is an ordinary
        single-name file the app can name, and no other book, unfinished job or reacquire record names one of them. An
        ancestor folder is removed only once it is empty. Read-only."""
        from book_delete import SOUND
        import stat as stat_module
        with os.scandir(path) as listing:
            entries = []
            for entry in listing:
                entries.append(entry)
                if len(entries) > self.LEFTOVER_LIMIT:return [], 'Folder holds too many entries to clear; retained'
        if not entries:return [], None
        if not own:return [], 'Folder contains entries or filesystem streams; retained'
        for entry in entries:
            if entry.is_symlink() or os.path.isjunction(entry.path) or entry.is_dir(follow_symlinks=False):
                return [], 'Folder contains a subfolder or link; retained'
            if Path(entry.name).suffix.lower() in SOUND:
                return [], 'Audio files remain in the folder; retained'
        leftovers = []
        for entry in entries:
            try:
                item = ordinary(entry.path);facts = os.lstat(item)
            except FileNotFoundError:
                continue
            except (BoundaryError, OSError):
                return [], 'A file in the folder cannot be removed safely; retained'
            if not stat_module.S_ISREG(facts.st_mode) or getattr(facts, 'st_file_attributes', 0) & 0x400 or facts.st_nlink != 1:
                return [], 'A file in the folder is a link or has a second name; retained'
            leftovers.append({'path': str(item), 'size': facts.st_size})
        if self._held(job_id, manifest, [item['path'] for item in leftovers]):
            return [], 'Another book or job uses a file in this folder; retained'
        return leftovers, None

    def _remove_folder(self, job_id, manifest, output, path, own=False):
        """One candidate folder (deepest first). Ruling 74e: the book's own folder loses its non-audio leftovers through the
        exact-handle file disposal source cleanup and Delete book use (book_delete.remove: inside the source root, held
        ancestry, one link, the listed size), then the folder goes with a plain, non-recursive rmdir (ruling 24a's removal,
        extended by 74e to this automatic cleanup): it fails if anything arrived meanwhile, and works on NTFS and network
        drives such as Z:, where the exact-handle empty-folder disposition refuses. The folder's native identity and
        ancestry must still be the ones captured, it must hold no named stream, the source root and its direct children
        are never candidates (_folder_candidates), and a folder holding the published audiobook is never touched."""
        from producer_recovery import protected_dependency
        from book_delete import remove
        with connect(self.database) as db:
            if protected_dependency(db,[path]):raise BoundaryError('Isolated old namespace is retained')
        root=ordinary(manifest['root'])
        known=self._capture_folder(job_id,root,path)
        if known is None:return
        effective=getattr(self._location_local,'effective',None) or output
        if ordinary(effective['final_path']).is_relative_to(path):
            self._folder_state(job_id,path,'retained_nonempty','Folder contains the published audiobook; retained');return
        ancestry=json.loads(known['ancestry'])
        with DirectoryBoundary(root,path) as held:
            if [list(i) for i in held.identities]!=ancestry:raise BoundaryError('Source-folder native identity changed before disposition')
            leftovers,reason=self._leftovers(job_id,manifest,path,own)
            if reason:
                self._folder_state(job_id,path,'retained_nonempty',reason);return
            self.guard();held.revalidate();self._folder_obligations(job_id,manifest,output);self._folder_sources_absent(job_id,manifest)
            names=', '.join(Path(item['path']).name for item in leftovers)
            self._folder_state(job_id,path,'removal_intended',('Removing with its non-audio files: '+names)[:1000] if names else '')
            for item in leftovers:
                self.guard()
                failed=remove(item['path'],str(root),item['size'])
                if failed:
                    self._folder_state(job_id,path,'retained_nonempty',('A non-audio file could not be removed; retained: '+failed[1])[:1000]);return
        try:
            with self._folder_boundary(job_id,root,path.parent,ancestry) as boundary:
                with VerifiedDirectory(path) as target:
                    if target.facts()!=json.loads(known['identity']):raise BoundaryError('Source-folder native identity changed before disposition')
                    if not target.empty():
                        self._folder_state(job_id,path,'retained_nonempty','Folder contains entries or filesystem streams; retained');return
                self.guard();boundary.revalidate()
                os.rmdir(path)
        except FileNotFoundError:
            pass  # gone after our intent: reconciled below
        except OSError as error:
            self._folder_state(job_id,path,'retained_nonempty',('Folder could not be removed; retained: '+str(error))[:1000]);return
        if os.path.lexists(path):
            self._folder_state(job_id,path,'retained_nonempty','Folder is still there after its removal; retained');return
        self._folder_state(job_id,path,'disposition_set')
        self._folder_state(job_id,path,'removed')

    def old_folder_jobs(self):
        """Ruling 76b: the folder cleanups an earlier version finished ('completed' or 'unsupported') that kept a folder and
        that the sweep has not looked at yet, oldest first. Read-only."""
        with connect(self.database) as db:
            db.execute(SWEEP_TABLE)
            return [r[0] for r in db.execute("SELECT j.job_id FROM source_folder_cleanup_jobs j WHERE j.state IN ('completed','unsupported') "
                                             "AND j.job_id NOT IN (SELECT job_id FROM source_folder_sweep) AND EXISTS (SELECT 1 FROM source_folder_cleanup_directories d "
                                             "WHERE d.job_id=j.job_id AND d.state IN (%s)) ORDER BY j.updated,j.job_id" % ','.join('?'*len(KEPT_STATES)),KEPT_STATES)]

    @staticmethod
    def _might_clear(path):
        """A kept folder 74e could remove now: it holds nothing, or only files that are not audio (no subfolder, no link, no
        audio in any format). Read-only, one listing; the run itself checks everything again."""
        from book_delete import SOUND
        try:
            with os.scandir(path) as listing:
                for entry in listing:
                    if entry.is_symlink() or os.path.isjunction(entry.path) or entry.is_dir(follow_symlinks=False) or Path(entry.name).suffix.lower() in SOUND:return False
        except OSError:
            return False
        return True

    def sweep_folders(self, job_id):
        """Ruling 76b: one earlier folder cleanup, run again under 74e, once. Cheap checks first: 'gone' when no kept folder
        is there any more, 'kept' when each one still holds audio, a subfolder or a link. Otherwise the full run, with every
        check of the post-conversion cleanup (the published audiobook re-read, source retirement and the copy purge
        complete, no replacement original, identity and ancestry, never a source root or a folder directly inside one); its
        resulting state is the outcome. The outcome is recorded whatever it is, so a job is never swept twice; an
        InterruptedError (closing) records nothing and the next start resumes it."""
        with connect(self.database) as db:
            kept=[r[0] for r in db.execute('SELECT path FROM source_folder_cleanup_directories WHERE job_id=? AND state IN (%s)' % ','.join('?'*len(KEPT_STATES)),(job_id,*KEPT_STATES))]
        present=[path for path in kept if os.path.isdir(path)]
        if not present:outcome='gone'
        elif not any(self._might_clear(path) for path in present):outcome='kept'
        else:
            try:outcome=(self.run_folders(job_id,rerun=True) or {}).get('state') or 'none'
            except InterruptedError:raise
            except Exception:outcome='needs_attention'  # recorded on the folder job by run_folders; housekeeping, never attention
        with connect(self.database) as db:
            db.execute(SWEEP_TABLE)
            db.execute('INSERT OR REPLACE INTO source_folder_sweep VALUES(?,?,?)',(job_id,outcome,stamp()))
        return outcome

    def run_folders(self, job_id, progress=None, rerun=False):
        """Check only completed enrolled source parents; never enroll originals. rerun (ruling 76b, sweep_folders only): a
        cleanup an earlier version finished runs again."""
        with connect(self.database) as db:
            enrolled=db.execute('SELECT 1 FROM source_cleanup WHERE job_id=?',(job_id,)).fetchone()
        if not enrolled:return None
        terminal=self.folder_status(job_id)
        if terminal and terminal['state'] in ('completed','unsupported') and not rerun:return terminal
        output_hash=''
        try:
            with self.protected_output(job_id) as (manifest,output):
                output_hash=output['sha256'];self._folder_obligations(job_id,manifest,output)
                candidates=self._folder_candidates(manifest)
                with connect(self.database) as db:
                    prior={ordinary(r[0]) for r in db.execute('SELECT path FROM source_folder_cleanup_directories WHERE job_id=?',(job_id,))}
                if not prior.issubset(set(candidates)):raise BoundaryError('Source-folder receipt escaped approved source provenance')
                self._folder_set(job_id,output_hash,'checking')
                if progress:progress('folders')
                self._folder_sources_absent(job_id,manifest)
                # Capture every initial identity before the first disposition.
                for path in candidates:self.guard();self._capture_folder(job_id,ordinary(manifest['root']),path)
                self._folder_set(job_id,output_hash,'removing')
                own={ordinary(source['path']).parent for source in manifest['sources']}  # ruling 74e: the folders the book sat in
                for path in candidates:self.guard();self._remove_folder(job_id,manifest,output,path,own=path in own)
                self._folder_obligations(job_id,manifest,output);self._folder_sources_absent(job_id,manifest)
                with connect(self.database) as db:
                    reasons=[r[0] for r in db.execute("SELECT DISTINCT reason FROM source_folder_cleanup_directories WHERE job_id=? AND state='retained_unsupported'",(job_id,))]
                self._folder_set(job_id,output_hash,'unsupported' if reasons else 'completed','; '.join(reasons))
            return self.folder_status(job_id)
        except Exception as error:
            self._folder_set(job_id,output_hash,'needs_attention',str(error));raise

    def discard_repair_copy(self, job_id, path, sha256, size):
        """Explicit one-off caller: validate its retained repair journal before calling.

        This is never an HTTP path API or an automatic historical repair sweep.
        """
        root = Path(self.database).parent / 'chapter-repairs'
        p = ordinary(path)
        if not p.is_relative_to(root) or p.name != 'checked.m4b' or p.parent.parent != root:
            raise BoundaryError('Only a retained owned chapter-repair checked copy is eligible')
        with self.protected_output(job_id) as (manifest,parent_output), contextlib.ExitStack() as stack:
            journal = stack.enter_context(VerifiedFile(p.parent / 'corrected-artifact.jsonl'))
            if journal.facts()['size'] > 2 * 1024 * 1024:
                raise BoundaryError('Repair journal exceeds its bound')
            rows = [json.loads(line) for line in b''.join(journal.chunks()).decode('utf-8').splitlines()]
            if not rows or any(r['parent_job_id'] != job_id or r['job_id'] != p.parent.name for r in rows) or rows[0]['state'] != 'intent' or rows[-1]['state'] != 'completed':
                raise BoundaryError('Completed repair ownership is not proved')
            final=ordinary(rows[-1]['data']['destination']);validated=rows[-1]['data']['validation']
            source=ordinary(rows[0]['data']['parent_output']);published_parent=ordinary(rows[0]['data'].get('parent_effective_output',str(source)))
            if source!=ordinary(parent_output['final_path']) or final not in {published_parent.with_name(published_parent.stem+' - Chapters.m4b'),published_parent.with_name(published_parent.stem+' - Chapters v2.m4b')}:
                raise BoundaryError('Corrected repair destination changed')
            authorization=None
            if self.repair_publication:
                authorization=self.repair_publication(job_id,p.parent/'corrected-artifact.jsonl',journal.sha256())
                if authorization['original']['final_path']!=str(final) or authorization['original']['sha256']!=validated['sha256'] or authorization['original']['size']!=validated['size']:raise BoundaryError('Repair authorization differs from the exact completed journal')
                final=ordinary(authorization['effective']['final_path']);publication_root=authorization['effective']['root']
            else:
                publication_root=rows[0]['data'].get('output_root',manifest.get('output_root',manifest['root']))
                if rows[0]['data'].get('parent_location') is not None:raise BoundaryError('Relocated repair requires independent authorized publication binding')
            ancestry=stack.enter_context(DirectoryBoundary(publication_root,final.parent))
            corrected=stack.enter_context(VerifiedFile(final))
            if corrected.facts()['size']!=validated['size'] or corrected.sha256()!=validated['sha256']:
                raise BoundaryError('Corrected published repair is missing or changed; copy retained')
            if authorization:
                effective=authorization['effective']
                if (effective.get('identity') is not None and corrected.facts()['identity']!=effective['identity']) or [list(v) for v in ancestry.identities]!=[list(v) for v in effective['parent_identity']]:raise BoundaryError('Relocated repaired publication native identity changed')
                prior=getattr(self._location_local,'derived_publications',())
                self._location_local.derived_publications=tuple(prior)+(authorization,)
                stack.callback(setattr,self._location_local,'derived_publications',prior)
            item = self._prepare(stack, job_id, 'repair', p, root, (sha256, size))
            if item:
                self._dispose([item])
