"""Discard only verified owned copies after durable audiobook success.

Receipts survive a crash. An absent name is reconciled only after recorded
verified removal intent; unknown absence/replacement never counts as success.
"""
import contextlib
import hashlib
import json
import re
import uuid
from pathlib import Path
from scanner import connect
from native_io import BoundaryError, DirectoryBoundary, VerifiedFile, VerifiedDirectory, DirectoryNotEmptyError, DirectoryDispositionUnsupported, ordinary
from source_cleanup import packed, stamp, single_stream

TERMINAL = {'removed', 'absent_after_intent'}

class StorageCleanup:
    def __init__(self, database, stage_root, recovery_root, guard=lambda: None):
        self.database = str(database)
        self.stage_root = ordinary(stage_root)
        self.recovery_root = ordinary(recovery_root)
        self.guard = guard
        with connect(self.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS storage_cleanup_jobs(job_id TEXT PRIMARY KEY, output_hash TEXT, state TEXT, reason TEXT, updated TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS storage_cleanup_authorizations(path TEXT PRIMARY KEY,job_id TEXT,output_hash TEXT,sha256 TEXT,size INTEGER,proof_hash TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS storage_cleanup_preserved(path TEXT PRIMARY KEY,job_id TEXT,reason TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS source_folder_cleanup_jobs(job_id TEXT PRIMARY KEY,output_hash TEXT,state TEXT,reason TEXT,updated TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS source_folder_cleanup_directories(job_id TEXT,path TEXT,identity TEXT,ancestry TEXT,state TEXT,reason TEXT,updated TEXT,PRIMARY KEY(job_id,path))')
            db.execute('CREATE TABLE IF NOT EXISTS storage_cleanup_files(path TEXT PRIMARY KEY, job_id TEXT, kind TEXT, sha256 TEXT, size INTEGER, facts TEXT, state TEXT, updated TEXT)')

    def _set(self, job_id, output_hash, state, reason=''):
        with connect(self.database) as db:
            db.execute('INSERT OR REPLACE INTO storage_cleanup_jobs VALUES(?,?,?,?,?)', (job_id, output_hash, state, reason, stamp()))

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
    def protected_output(self, job_id):
        self.guard()
        m, out = self._job(job_id)
        root = ordinary(m['root']); final = ordinary(out['final_path'])
        if final != ordinary(m['destination']) or not final.is_relative_to(root) or final.suffix.lower() != '.m4b':
            raise BoundaryError('Completed output destination changed')
        with DirectoryBoundary(root, final.parent) as ancestry, VerifiedFile(final) as handle:
            if [list(x) for x in ancestry.identities] != [list(x) for x in out['parent_identity']]:
                raise BoundaryError('Completed output ancestry changed')
            if handle.facts()['size'] != out['size'] or handle.sha256() != out['sha256']:
                raise BoundaryError('Completed output bytes changed; copies retained')
            yield m, out

    def _known(self, path):
        with connect(self.database) as db:
            row = db.execute('SELECT * FROM storage_cleanup_files WHERE path=?', (str(path),)).fetchone()
        return dict(row) if row else None

    def _prepare(self, stack, job_id, kind, path, root, expected=None):
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
            with connect(self.database) as db:
                db.execute('INSERT INTO storage_cleanup_files VALUES(?,?,?,?,?,?,?,?)',
                           (str(path), job_id, kind, sha, facts['size'], packed(facts), 'verified', stamp()))
        return path, handle, ancestry

    def _file_state(self, path, state):
        with connect(self.database) as db:
            db.execute('UPDATE storage_cleanup_files SET state=?,updated=? WHERE path=?', (state, stamp(), str(path)))

    def _dispose(self, prepared):
        for path, handle, ancestry in prepared:
            self.guard(); ancestry.revalidate()
            self._file_state(path, 'removal_intended')
            handle.dispose()
            self._file_state(path, 'disposition_set')
            handle.__exit__(None, None, None)
            try:
                path.stat()
            except FileNotFoundError:
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
                stack.enter_context(DirectoryBoundary(manifest['root'], Path(s['path']).parent))
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
                known = name in expected or name in {'cover.jpg', 'cover.png', 'checked.m4b', 'compatible.m4b', 'inputs.txt', 'chapters.txt'} or re.fullmatch(r'[0-9a-f]{32}\.(stderr|decode-stderr|stdout|jpg|png)', name)
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
                        with connect(self.database) as db:db.execute('INSERT OR REPLACE INTO storage_cleanup_preserved VALUES(?,?,?)',(str(path),job_id,'Legacy evidence lacks exact producer bytes; preserved'))
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

    def run(self, job_id):
        output_hash = ''
        try:
            with self.protected_output(job_id) as (manifest, output):
                output_hash = output['sha256']
                previous = next((r for r in self.status() if r['job_id'] == job_id), None)
                if previous and previous['state'] == 'completed' and previous['output_hash'] == output_hash:
                    return
                self._set(job_id, output_hash, 'checking')
                with contextlib.ExitStack() as stack:
                    cleanup, members = self._source_safety(stack, job_id, manifest, output)
                    targets = self._staging(stack, job_id, manifest, output)
                    if cleanup:
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
                    prepared = []
                    for path, kind, expected in targets:
                        item = self._prepare(stack, job_id, kind, path, self.recovery_root if kind == 'recovery' else self.stage_root, expected)
                        if item:
                            prepared.append(item)
                    # All copies and obligations are checked before any disposition.
                    self._set(job_id, output_hash, 'removing')
                    self._dispose(prepared)
                self._set(job_id, output_hash, 'completed')
        except Exception as error:
            self._set(job_id, output_hash, 'needs_attention', str(error))
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
            if not path.is_relative_to(root) or path==root or path.suffix.lower()!='.mp3':
                raise BoundaryError('Retired source is outside its approved MP3 library')
            parent=path.parent
            while parent!=root:
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

    def _remove_folder(self, job_id, manifest, output, path):
        known=self._capture_folder(job_id,ordinary(manifest['root']),path)
        if known is None:return
        # The validated output keeps any candidate containing it nonempty. Its
        # held ancestor handle also intentionally denies DELETE on that target.
        contains_output=ordinary(output['final_path']).is_relative_to(path)
        with self._folder_boundary(job_id,manifest['root'],path.parent,json.loads(known['ancestry'])) as boundary, VerifiedDirectory(path,delete=not contains_output) as target:
            if target.facts()!=json.loads(known['identity']):raise BoundaryError('Source-folder native identity changed before disposition')
            if not target.empty():
                self._folder_state(job_id,path,'retained_nonempty','Folder contains entries or filesystem streams; retained')
                return
            if contains_output:raise BoundaryError('Protected published output ancestry unexpectedly became empty')
            try:target.require_empty_disposition()
            except DirectoryDispositionUnsupported as error:
                self._folder_state(job_id,path,'retained_unsupported',str(error));return
            self.guard();boundary.revalidate();self._folder_obligations(job_id,manifest,output)
            self._folder_state(job_id,path,'removal_intended')
            try:target.dispose_empty()
            except DirectoryNotEmptyError as error:
                self._folder_state(job_id,path,'retained_nonempty',str(error));return
            except DirectoryDispositionUnsupported as error:
                self._folder_state(job_id,path,'retained_unsupported',str(error));return
            self._folder_state(job_id,path,'disposition_set')
            target.__exit__(None,None,None)
            try:path.lstat()
            except FileNotFoundError:self._folder_state(job_id,path,'removed')
            else:raise BoundaryError('Exact empty-directory disposition did not remove its name')

    def run_folders(self, job_id, progress=None):
        """Check only completed enrolled source parents; never enroll originals."""
        with connect(self.database) as db:
            enrolled=db.execute('SELECT 1 FROM source_cleanup WHERE job_id=?',(job_id,)).fetchone()
        if not enrolled:return None
        terminal=self.folder_status(job_id)
        if terminal and terminal['state'] in ('completed','unsupported'):return terminal
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
                for path in candidates:self.guard();self._remove_folder(job_id,manifest,output,path)
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
            source=ordinary(rows[0]['data']['parent_output'])
            if source!=ordinary(parent_output['final_path']) or final not in {source.with_name(source.stem+' - Chapters.m4b'),source.with_name(source.stem+' - Chapters v2.m4b')}:
                raise BoundaryError('Corrected repair destination changed')
            stack.enter_context(DirectoryBoundary(manifest['root'],final.parent))
            corrected=stack.enter_context(VerifiedFile(final))
            if corrected.facts()['size']!=validated['size'] or corrected.sha256()!=validated['sha256']:
                raise BoundaryError('Corrected published repair is missing or changed; copy retained')
            item = self._prepare(stack, job_id, 'repair', p, root, (sha256, size))
            if item:
                self._dispose([item])
