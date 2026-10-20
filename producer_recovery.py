"""Explicit later-boot producer closure; legacy files are retained, never adopted."""
import contextlib
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
from datetime import datetime,timezone
from native_io import DirectoryBoundary,VerifiedFile,ordinary,kernel,BoundaryError
from migration_operation import catalog_identity_lease

SCHEMA='books-producer-recovery-v1'
CLAIM='same-local-windows-installation-no-move-restore-clone-or-memory-rollback'

def packed(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(packed(value).encode()).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
def copied(value):return json.loads(packed(value))

def windows_platform():
    if os.name!='nt':raise ValueError('Trusted Windows startup measurement is unavailable')
    import winreg
    from ctypes import wintypes
    kernel.GetTickCount64.argtypes=[];kernel.GetTickCount64.restype=ctypes.c_ulonglong
    kernel.GetComputerNameW.argtypes=[wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)];kernel.GetComputerNameW.restype=wintypes.BOOL
    kernel.GetWindowsDirectoryW.argtypes=[wintypes.LPWSTR,wintypes.UINT];kernel.GetWindowsDirectoryW.restype=wintypes.UINT
    buffer=ctypes.create_unicode_buffer(32768);length=wintypes.DWORD(len(buffer))
    if not kernel.GetComputerNameW(buffer,ctypes.byref(length)):raise ValueError('Windows machine identity is unavailable')
    computer=buffer.value
    if not kernel.GetWindowsDirectoryW(buffer,len(buffer)):raise ValueError('Windows installation identity is unavailable')
    windows=str(ordinary(buffer.value))
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography',0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:machine=winreg.QueryValueEx(key,'MachineGuid')[0]
    if not isinstance(machine,str) or not machine.strip() or not computer:raise ValueError('Windows installation identity is ambiguous')
    serial=wintypes.DWORD()
    kernel.GetVolumeInformationW.argtypes=[wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.POINTER(wintypes.DWORD),ctypes.POINTER(wintypes.DWORD),wintypes.LPWSTR,wintypes.DWORD];kernel.GetVolumeInformationW.restype=wintypes.BOOL
    if not kernel.GetVolumeInformationW(ordinary(windows).anchor,None,0,ctypes.byref(serial),None,None,None,0) or not serial.value:raise ValueError('Windows system volume identity is unavailable')
    return {'system_volume_serial':str(serial.value),'schema':'books-windows-startup-v1','machine_guid':machine,'computer':computer,'windows_directory':windows,'uptime_ms':int(kernel.GetTickCount64())}

def validate_origin_evidence(evidence):
    if not isinstance(evidence,dict) or evidence.get('actor')!='user' or evidence.get('claim')!=CLAIM or not isinstance(evidence.get('evidence'),str) or not evidence['evidence'].strip() or len(packed(evidence))>8000:raise ValueError('Explicit historical human locality fact is malformed')
    return evidence

class ProducerRecovery:
    def __init__(self,database,stage_root,*,platform=windows_platform,active=lambda job,attempt:False):
        self.database=ordinary(database);self.stage_root=ordinary(stage_root);self.platform=platform;self.active=active
        with self._db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS producer_origin_facts(id TEXT PRIMARY KEY,job_id TEXT,attempt_id TEXT,scope_sha256 TEXT,record TEXT,created TEXT);
            CREATE TABLE IF NOT EXISTS producer_recovery_checkpoints(id TEXT PRIMARY KEY,job_id TEXT,attempt_id TEXT,scope_sha256 TEXT,scope TEXT,native TEXT,platform TEXT,origin_id TEXT,state TEXT,proof TEXT,created TEXT);''')
    @contextlib.contextmanager
    def _db(self):
        db=sqlite3.connect(self.database,timeout=10);db.row_factory=sqlite3.Row
        try:
            db.execute('PRAGMA synchronous=FULL')
            if str(db.execute('PRAGMA journal_mode').fetchone()[0]).lower() not in {'wal','delete','truncate','persist'}:raise ValueError('Persistent catalog journal is required')
            yield db
        finally:db.rollback();db.close()
    def _scope(self,db,job_id):
        if str(uuid.UUID(job_id))!=job_id:raise ValueError('Invalid job identity')
        raw=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()
        if raw is None:raise ValueError('Recovery job is unavailable')
        job=dict(raw);manifest=json.loads(job['manifest']);journal=json.loads(job['journal'])
        if job['state']!='needs attention' or job['output'] or journal.get('publication_intent'):raise ValueError('Current job is active or has a publication dependency')
        attempt_id=job.get('attempt_id')
        if not attempt_id or str(uuid.UUID(attempt_id))!=attempt_id:raise ValueError('Current prior attempt identity is unavailable')
        raw=db.execute('SELECT * FROM working_attempts WHERE job_id=? AND attempt_id=?',(job_id,attempt_id)).fetchone()
        if raw is None:raise ValueError('Prior attempt has no durable manifest')
        attempt=dict(raw)
        if attempt['producer'] not in {'active','uncertain'} or attempt['state'] not in {'producing','attention'}:raise ValueError('Prior attempt is outside unresolved producer recovery')
        if attempt['manifest_hash']!=job['manifest_hash'] or json.loads(attempt['manifest'])!=manifest:raise ValueError('Prior attempt manifest changed')
        if digest(manifest)!=job['manifest_hash']:raise ValueError('Frozen job manifest hash differs')
        if self.active(job_id,attempt_id):raise ValueError('Current app producer is still active')
        files=[dict(row) for row in db.execute('SELECT * FROM working_files WHERE job_id=? AND attempt_id=? ORDER BY name',(job_id,attempt_id))]
        if not files or len(files)>512 or any(row['state']!='creation_intended' or row['sha256'] or row['size'] or json.loads(row['facts']) for row in files):raise ValueError('Attempt is outside the legacy unadopted-file scope')
        candidate=db.execute('SELECT id,revision,fingerprint,superseded FROM book_groups WHERE id=?',(manifest['candidate_id'],)).fetchone()
        if candidate is None or candidate['superseded']:raise ValueError('Current source candidate is unavailable')
        return {'job':job,'attempt':attempt,'files':files,'candidate':dict(candidate)}
    @staticmethod
    def _machine(platform):
        if platform.get('schema')!='books-windows-startup-v1' or type(platform.get('uptime_ms')) is not int or not 0<=platform['uptime_ms']<2**64:raise ValueError('Trusted startup measurement is malformed')
        if any(not isinstance(platform.get(key),str) or not platform[key] for key in ('machine_guid','computer','windows_directory','system_volume_serial')):raise ValueError('Trusted machine identity is incomplete')
        return {key:value for key,value in platform.items() if key!='uptime_ms'}
    @contextlib.contextmanager
    def _native(self,scope,*,hash_files=False):
        from ctypes import wintypes
        kernel.GetDriveTypeW.argtypes=[wintypes.LPCWSTR];kernel.GetDriveTypeW.restype=wintypes.UINT
        stage=self.stage_root/scope['job']['job_id']/scope['attempt']['attempt_id']
        if any(kernel.GetDriveTypeW(ordinary(path).anchor)!=3 for path in (self.database,self.stage_root)):raise ValueError('Recovery requires local fixed catalog and staging volumes')
        manifest=json.loads(scope['attempt']['manifest']);deadline=time.monotonic()+540
        with contextlib.ExitStack() as held:
            catalog=held.enter_context(catalog_identity_lease(self.database))
            boundary=held.enter_context(DirectoryBoundary(stage.anchor,stage))
            marker=held.enter_context(VerifiedFile(stage.parent/'ownership.json'))
            if marker.facts()['links']!=1 or marker.facts()['size']>16*1024*1024:raise ValueError('Staging marker is not unique bounded data')
            from source_cleanup import single_stream
            single_stream(stage.parent/'ownership.json')
            raw=b''.join(marker.chunks())
            if json.loads(raw)!={'job_id':scope['job']['job_id'],'manifest':manifest}:raise ValueError('Staging marker differs from the frozen attempt')
            names=sorted(entry.name for entry in os.scandir(stage));expected=sorted(row['name'] for row in scope['files'])
            if names!=expected:raise ValueError('Unknown, missing or changed old staging members are preserved')
            files=[]
            for row in scope['files']:
                path=ordinary(row['path'])
                if path.parent!=stage or path.name!=row['name']:raise ValueError('Old artifact path is outside its exact attempt')
                file=held.enter_context(VerifiedFile(path));single_stream(path);facts=file.facts()
                if facts['links']!=1:raise ValueError('Old artifact has an alias; files retained')
                item={'name':row['name'],'path':str(path),'facts':facts}
                if hash_files:
                    full=hashlib.sha256()
                    for block in file.chunks():
                        if time.monotonic()>deadline:raise ValueError('Old-file observation exceeded bounded recovery preflight; files retained')
                        full.update(block)
                    item['sha256']=full.hexdigest()
                files.append(item)
            yield {'schema':'books-unadopted-attempt-fence-v1','ownership_authority':False,'catalog':catalog,'stage':str(stage),'ancestry':boundary.identities,'marker_sha256':hashlib.sha256(raw).hexdigest(),'files':files}
            boundary.revalidate()
    def record_origin(self,job_id,evidence):
        """Explicit trusted user fact entry only; never called by automatic startup/Prepare."""
        if not isinstance(evidence,dict) or evidence.get('actor')!='user' or evidence.get('claim')!=CLAIM or not isinstance(evidence.get('evidence'),str) or not evidence['evidence'].strip() or len(packed(evidence))>8000:raise ValueError('Explicit historical human locality fact is required')
        with self._db() as db:
            scope=self._scope(db,job_id);platform=self.platform();self._machine(platform)
            with self._native(scope) as native:
                record={'evidence':copied(evidence),'native':native,'machine':self._machine(platform)};identity=str(uuid.uuid4())
                db.execute('BEGIN IMMEDIATE')
                if digest(self._scope(db,job_id))!=digest(scope):raise ValueError('Recovery source/attempt changed')
                db.execute('INSERT INTO producer_origin_facts VALUES(?,?,?,?,?,?)',(identity,job_id,scope['attempt']['attempt_id'],digest(scope),packed(record),stamp()));db.commit()
                return identity
    def _origin(self,db,scope,platform,native):
        raw=db.execute('SELECT * FROM producer_origin_facts WHERE job_id=? AND attempt_id=? ORDER BY rowid DESC LIMIT 1',(scope['job']['job_id'],scope['attempt']['attempt_id'])).fetchone()
        if raw is None:raise ValueError('Historical local origin is not confirmed; all old files are retained')
        record=json.loads(raw['record'])
        validate_origin_evidence(record.get('evidence'))
        if raw['scope_sha256']!=digest(scope) or record['machine']!=self._machine(platform) or record['native']!=copied(native):raise ValueError('Historical origin binding differs; files retained')
        return dict(raw)
    @staticmethod
    def _without_hash(native):
        value=copied(native)
        for file in value['files']:file.pop('sha256',None)
        return value
    def prepare(self,job_id):
        with self._db() as db:
            scope=self._scope(db,job_id);platform=self.platform();self._machine(platform)
            if not db.execute('SELECT 1 FROM producer_origin_facts WHERE job_id=? AND attempt_id=?',(job_id,scope['attempt']['attempt_id'])).fetchone():raise ValueError('Historical local origin is not confirmed; all old files are retained')
            with self._native(scope,hash_files=True) as native:
                origin=self._origin(db,scope,platform,self._without_hash(native));identity=str(uuid.uuid4())
                prior_checkpoint=db.execute('SELECT * FROM producer_recovery_checkpoints WHERE job_id=? AND attempt_id=? ORDER BY rowid DESC LIMIT 1',(job_id,scope['attempt']['attempt_id'])).fetchone()
                prior_checkpoint=dict(prior_checkpoint) if prior_checkpoint else None
                db.execute('BEGIN IMMEDIATE')
                if digest(self._scope(db,job_id))!=digest(scope):raise ValueError('Recovery source/attempt changed while saving')
                latest=db.execute('SELECT * FROM producer_recovery_checkpoints WHERE job_id=? AND attempt_id=? ORDER BY rowid DESC LIMIT 1',(job_id,scope['attempt']['attempt_id'])).fetchone()
                if (dict(latest) if latest else None)!=prior_checkpoint or self._origin(db,scope,platform,self._without_hash(native))!=origin:raise ValueError('Recovery checkpoint/origin changed while saving')
                db.execute('INSERT INTO producer_recovery_checkpoints VALUES(?,?,?,?,?,?,?,?,?,?,?)',(identity,job_id,scope['attempt']['attempt_id'],digest(scope),packed(scope),packed(native),packed(platform),origin['id'],'prepared','',stamp()))
                db.commit()
        return self.status(job_id)

    @staticmethod
    def capability(state,cause,reason,checkpoint=None):
        result={'schema':'books-producer-recovery-capability-v1','state':state,'cause':cause,
                'can_prepare':state=='prepare','can_retry':state in {'ready','isolated_retained'},
                'reason':str(reason),'retained_files':True}
        if checkpoint:result['checkpoint_id']=checkpoint
        return result
    def status(self,job_id):
        # No media hash, producer claim or isolation mutation occurs on a status read.
        try:
            with self._db() as db:
                retained=db.execute("SELECT attempt_id,id FROM producer_recovery_checkpoints WHERE job_id=? AND state='isolated_retained' ORDER BY rowid DESC LIMIT 1",(job_id,)).fetchone()
                if retained:
                    verify_retained(db,job_id,retained['attempt_id'])
                    return self.capability('isolated_retained','isolated_retained','Old working files are kept. Retry checks the original sources and starts a separate attempt.',retained['id'])
                scope=self._scope(db,job_id)
                if not db.execute('SELECT 1 FROM producer_origin_facts WHERE job_id=? AND attempt_id=?',(job_id,scope['attempt']['attempt_id'])).fetchone():return self.capability('unsupported','origin_unproved','Historical local origin is not confirmed; all old files are retained')
                try:platform=self.platform();self._machine(platform)
                except (ValueError,OSError) as error:return self.capability('unsupported','startup_unavailable',error)
                with self._native(scope) as native:
                    try:self._origin(db,scope,platform,native)
                    except ValueError as error:return self.capability('unsupported','origin_unproved',error)
                    raw=db.execute('SELECT * FROM producer_recovery_checkpoints WHERE job_id=? AND attempt_id=? ORDER BY rowid DESC LIMIT 1',(job_id,scope['attempt']['attempt_id'])).fetchone()
                    if raw is None:return self.capability('prepare','checkpoint_required','Save a recovery checkpoint before restarting Windows. Old working files stay untouched.')
                    saved=dict(raw)
                    if saved['scope_sha256']!=digest(scope) or self._without_hash(json.loads(saved['native']))!=copied(native) or self._machine(json.loads(saved['platform']))!=self._machine(platform):
                        return self.capability('unsupported','binding_mismatch','Saved recovery binding changed; all old files are retained.',saved['id'])
                    if platform['uptime_ms']>=json.loads(saved['platform'])['uptime_ms']:
                        return self.capability('waiting_restart','restart_unverified','A later Windows startup has not been verified. All old working files are kept.',saved['id'])
                    return self.capability('ready','proof_ready','A later local Windows startup is verified. Retry must check the original sources and start a separate attempt.',saved['id'])
        except (ValueError,OSError,BoundaryError,sqlite3.Error,KeyError,TypeError) as error:
            return self.capability('unsupported','binding_mismatch',str(error))

    def isolate(self,job_id):
        """Only a bound later boot closes a producer. No old file becomes owned."""
        with self._db() as db:
            scope=self._scope(db,job_id);platform=self.platform();self._machine(platform)
            saved=db.execute('SELECT * FROM producer_recovery_checkpoints WHERE job_id=? AND attempt_id=? ORDER BY rowid DESC LIMIT 1',(job_id,scope['attempt']['attempt_id'])).fetchone()
            if not saved:raise ValueError('Save a recovery checkpoint first')
            saved=dict(saved);prior=json.loads(saved['platform'])
            if saved['state']!='prepared' or saved['scope_sha256']!=digest(scope) or self._machine(platform)!=self._machine(prior) or platform['uptime_ms']>=prior['uptime_ms']:
                raise ValueError('A later continuously bound local Windows startup is not verified')
            with self._native(scope,hash_files=True) as native:
                origin=self._origin(db,scope,platform,self._without_hash(native))
                if origin['id']!=saved['origin_id']:raise ValueError('Recovery origin checkpoint was superseded')
                if copied(native)!=json.loads(saved['native']):raise ValueError('Old attempt contents or native identities changed; files retained')
                target=dict(scope['attempt'],producer='closed',state='isolated_retained',reason='Old working files and their source dependencies are retained.',updated=stamp())
                proof={'schema':'books-isolated-producer-proof-v1','checkpoint_id':saved['id'],'scope_sha256':digest(scope),'native_sha256':digest(native),'prior_startup':prior,'later_startup':platform,'target_attempt':target,'ownership_authority':False}
                db.execute('BEGIN IMMEDIATE')
                if digest(self._scope(db,job_id))!=digest(scope):raise ValueError('Recovery attempt changed before isolation')
                latest=db.execute('SELECT * FROM producer_recovery_checkpoints WHERE job_id=? AND attempt_id=? ORDER BY rowid DESC LIMIT 1',(job_id,scope['attempt']['attempt_id'])).fetchone()
                if latest is None or dict(latest)!=saved or self._origin(db,scope,platform,self._without_hash(native))!=origin:raise ValueError('Recovery checkpoint/origin was superseded before isolation')
                db.execute('UPDATE working_attempts SET producer=?,state=?,reason=?,updated=? WHERE job_id=? AND attempt_id=?',(target['producer'],target['state'],target['reason'],target['updated'],job_id,target['attempt_id']))
                changed=db.execute("UPDATE producer_recovery_checkpoints SET state='isolated_retained',proof=? WHERE id=? AND state='prepared' AND proof=? AND scope_sha256=? AND origin_id=?",(packed(proof),saved['id'],saved['proof'],saved['scope_sha256'],saved['origin_id']))
                if changed.rowcount!=1:raise ValueError('Recovery checkpoint CAS failed')
                db.commit()
        return self.capability('isolated_retained','isolated_retained','Old working files are kept. Retry must check the original sources and start a separate attempt.',saved['id'])

    @contextlib.contextmanager
    def protect_retained(self,job_id):
        with self._db() as db:
            saved=db.execute("SELECT attempt_id FROM producer_recovery_checkpoints WHERE job_id=? AND state='isolated_retained' ORDER BY rowid DESC LIMIT 1",(job_id,)).fetchone()
            if not saved:raise ValueError('Bound retained attempt is unavailable')
            record=verify_retained(db,job_id,saved['attempt_id'])
            with self._native(record['scope'],hash_files=True) as native:
                if copied(native)!=record['native']:raise ValueError('Retained attempt contents or native fence changed')
                yield record
                verify_retained(db,job_id,saved['attempt_id'])

    def retained(self,candidate_id):
        with self._db() as db:
            attempts=[]
            for raw in db.execute("SELECT * FROM producer_recovery_checkpoints WHERE state='isolated_retained' ORDER BY rowid"):
                row=dict(raw);scope=json.loads(row['scope'])
                if scope['candidate']['id']!=candidate_id:continue
                verify_retained(db,scope['job']['job_id'],scope['attempt']['attempt_id'])
                attempts.append({'job_id':scope['job']['job_id'],'attempt_id':scope['attempt']['attempt_id'],'path':json.loads(row['native'])['stage'],'reason':'Old working files and their source dependencies are retained.'})
            return {'schema':'books-producer-retention-v1','count':len(attempts),'reason':'Old working files and their source dependencies are retained.','attempts':attempts} if attempts else None

def verify_retained(db,job_id,attempt_id):
    raw=db.execute("SELECT * FROM producer_recovery_checkpoints WHERE job_id=? AND attempt_id=? AND state='isolated_retained' ORDER BY rowid DESC LIMIT 1",(job_id,attempt_id)).fetchone()
    if raw is None:raise ValueError('Retained attempt has no bound isolation proof')
    saved=dict(raw);scope=json.loads(saved['scope']);proof=json.loads(saved['proof']);native=json.loads(saved['native'])
    if saved['scope_sha256']!=digest(scope) or proof.get('schema')!='books-isolated-producer-proof-v1' or proof.get('checkpoint_id')!=saved['id'] or proof.get('scope_sha256')!=digest(scope) or proof.get('native_sha256')!=digest(native) or proof.get('ownership_authority') is not False:
        raise ValueError('Retained attempt proof is malformed')
    origin=db.execute('SELECT * FROM producer_origin_facts WHERE id=?',(saved['origin_id'],)).fetchone()
    if origin is None or origin['scope_sha256']!=digest(scope):raise ValueError('Retained historical locality evidence is unavailable')
    fact=json.loads(origin['record']);validate_origin_evidence(fact.get('evidence'))
    if fact['native']!=ProducerRecovery._without_hash(native) or fact['machine']!=ProducerRecovery._machine(proof['prior_startup']):raise ValueError('Retained historical locality binding differs')
    prior=proof['prior_startup'];later=proof['later_startup']
    if ProducerRecovery._machine(prior)!=ProducerRecovery._machine(later) or later['uptime_ms']>=prior['uptime_ms']:raise ValueError('Retained producer closure is unproved')
    job=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone();attempt=db.execute('SELECT * FROM working_attempts WHERE job_id=? AND attempt_id=?',(job_id,attempt_id)).fetchone()
    files=[dict(r) for r in db.execute('SELECT * FROM working_files WHERE job_id=? AND attempt_id=? ORDER BY name',(job_id,attempt_id))]
    if job is None or dict(job)!=scope['job'] or attempt is None or dict(attempt)!=proof['target_attempt'] or files!=scope['files']:raise ValueError('Retained history changed; no cleanup or reuse permitted')
    return {'checkpoint_id':saved['id'],'scope':scope,'native':native,'proof':proof}

def protected_dependency(db,paths):
    """Conservative namespace/source guard; never grants ownership or deletion."""
    exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='producer_recovery_checkpoints'").fetchone()
    if not exists:return False
    targets=[ordinary(path) for path in paths]
    for raw in db.execute("SELECT job_id,attempt_id FROM producer_recovery_checkpoints WHERE state='isolated_retained'"):
        record=verify_retained(db,raw[0],raw[1]);scope=record['scope'];stage=ordinary(record['native']['stage'])
        sources=[ordinary(item['path']) for item in json.loads(scope['attempt']['manifest'])['sources']]
        for path in targets:
            if path==stage or stage in path.parents or path in stage.parents or any(path==source or path in source.parents for source in sources):return True
    return False
