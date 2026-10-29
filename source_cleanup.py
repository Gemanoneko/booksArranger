"""Persistent, snapshot-backed retirement of exact selected audiobook sources.

No pathname deletion or background historical enrollment. Completed copies can
be discarded by the separate hash-bound storage cleanup after durable success.
Audio success is separate from cleanup state. Constructors never start work.
"""
import contextlib
import critical_sections
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import threading
import time
import uuid
from datetime import datetime, timezone

from scanner import connect
from sqlite_retry import transaction
from native_io import DirectoryBoundary, VerifiedFile, BoundaryError, ordinary, publish_no_replace

# SQLite's fixed text for SQLITE_BUSY. Before v0.16.5 a cleanup that hit a busy catalog stored it as
# its reason; startup turns exactly that legacy shape into a paused cleanup (CleanupJobs.__init__).
LEGACY_BUSY='database is locked'
# Seconds to wait before the second and third attempt of a cleanup run that hit a busy catalog.
RETRY_WAITS=(5,15)


def catalog_busy(error):
    """Typed SQLITE_BUSY or SQLITE_LOCKED, any extended code. Never inferred from the message."""
    code=getattr(error,'sqlite_errorcode',None) if isinstance(error,sqlite3.OperationalError) else None
    return type(code) is int and code>=0 and (code&255) in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED)


def busy_cause(error,attempt=None):
    name=getattr(error,'sqlite_errorname',None)
    if not isinstance(name,str) or not name:name='SQLITE_BUSY' if (error.sqlite_errorcode&255)==sqlite3.SQLITE_BUSY else 'SQLITE_LOCKED'
    return 'catalog busy ('+name+')'+(f', attempt {attempt}' if attempt else '')


def regular_evidence(path):
    try:facts=Path(path).lstat()
    except OSError:return False
    return stat.S_ISREG(facts.st_mode) and not getattr(facts,'st_file_attributes',0)&0x400

def stamp():return datetime.now(timezone.utc).isoformat()
def packed(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def setup(db):
    db.execute('CREATE TABLE IF NOT EXISTS source_cleanup(id TEXT PRIMARY KEY,job_id TEXT UNIQUE,intent TEXT NOT NULL,state TEXT NOT NULL,reason TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS cleanup_members(cleanup_id TEXT,path TEXT,backup TEXT,facts TEXT,state TEXT,PRIMARY KEY(cleanup_id,path))')
    if 'restore_intent' not in [r[1] for r in db.execute('PRAGMA table_info(cleanup_members)')]:db.execute("ALTER TABLE cleanup_members ADD COLUMN restore_intent TEXT NOT NULL DEFAULT ''")
    if 'backup_facts' not in [r[1] for r in db.execute('PRAGMA table_info(cleanup_members)')]:db.execute("ALTER TABLE cleanup_members ADD COLUMN backup_facts TEXT NOT NULL DEFAULT ''")
    db.execute('CREATE TABLE IF NOT EXISTS recovery_completion(cleanup_id TEXT PRIMARY KEY,job_id TEXT UNIQUE,completed_at TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS source_retirements(root TEXT,path TEXT,cleanup_id TEXT,job_id TEXT,source_hash TEXT,size INTEGER,modified TEXT,state TEXT,PRIMARY KEY(root,path,cleanup_id))')
    db.execute('CREATE TABLE IF NOT EXISTS source_zone_marker_intents(cleanup_id TEXT,path TEXT,marker_sha256 TEXT,receipt TEXT NOT NULL,created TEXT NOT NULL,PRIMARY KEY(cleanup_id,path,marker_sha256))')
    # Append-only evidence: a paused cleanup carries an empty reason, so why it paused is kept here.
    db.execute('CREATE TABLE IF NOT EXISTS source_cleanup_holds(cleanup_id TEXT,at TEXT,prior_state TEXT,prior_reason TEXT,cause TEXT,PRIMARY KEY(cleanup_id,at))')

def single_stream(path):
    """Reject ADS rather than silently discard filesystem data in recovery."""
    import ctypes
    from ctypes import wintypes
    from native_io import kernel
    class Stream(ctypes.Structure):_fields_=[('size',ctypes.c_longlong),('name',wintypes.WCHAR*296)]
    kernel.FindFirstStreamW.argtypes=[wintypes.LPCWSTR,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.FindFirstStreamW.restype=wintypes.HANDLE
    kernel.FindNextStreamW.argtypes=[wintypes.HANDLE,ctypes.c_void_p];kernel.FindNextStreamW.restype=wintypes.BOOL
    kernel.FindClose.argtypes=[wintypes.HANDLE]
    info=Stream();h=kernel.FindFirstStreamW(str(path),0,ctypes.byref(info),0)
    if h==ctypes.c_void_p(-1).value:raise BoundaryError('Cannot verify source filesystem streams; originals retained')
    try:
        while True:
            if info.name!='::$DATA':raise BoundaryError('Additional filesystem streams require review; original retained')
            if not kernel.FindNextStreamW(h,ctypes.byref(info)):
                if ctypes.get_last_error()!=38:raise BoundaryError('Cannot finish source stream verification')
                break
    finally:kernel.FindClose(h)


class CleanupJobs:
    def __init__(self,database,recovery_root,guard,review_boundary,output_location=None,output_location_guard=None,output_policy=None):
        # output_policy() -> (configured output folder or None, every source/library root), read live at each check.
        # Without one nothing is removed (Sergei, rulings 2 and 1a, 2026-10-24: only a book whose result is in Sorted).
        self.output_policy=output_policy
        self.output_location_guard=output_location_guard
        self.output_location=output_location
        self.database=str(database);self.root=ordinary(recovery_root);self.guard=guard;self.review_boundary=review_boundary
        self.stop=threading.Event();self.thread=None;self.lock=threading.RLock();self.closed=False;self.current=None
        self.checked={}  # cleanup id -> originals checked so far while its recovery copies are checked (in memory)
        self.after_drain=None;self.on_completed=None
        # Quit (a drain) does not set stop; the owner supplies it so Quit also cuts a retry wait short.
        self.interrupt=lambda:False
        with DirectoryBoundary(self.root.anchor,self.root,create=True) as boundary:self.root_identity=boundary.identities
        with connect(self.database) as db:
            setup(db)
            db.execute("UPDATE source_cleanup SET state='paused' WHERE state IN ('checking','removing','pausing')")
            self._reclassify_legacy_busy(db)
    @staticmethod
    def _reclassify_legacy_busy(db):
        """Startup, database only: no file is opened and no work starts.

        A cleanup that stopped on a busy catalog before v0.16.5 kept the bare SQLite text as a
        needs-attention reason, and nothing resumed it. Exactly that shape (a real enrollment of a
        completed book, no restore started) becomes an ordinary paused cleanup; the next Start or
        Resume finishes it through run(), which re-verifies everything.
        """
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audio_jobs'").fetchone():return
        for row in db.execute("SELECT id,job_id,intent FROM source_cleanup WHERE state='needs_attention' AND reason=?",(LEGACY_BUSY,)).fetchall():
            try:intent=json.loads(row['intent'])
            except (TypeError,ValueError):continue
            if not isinstance(intent,dict) or intent.get('id')!=row['id'] or intent.get('job_id')!=row['job_id']:continue
            if not intent.get('binding') or not intent.get('recovery_identity'):continue  # enrollment-attention rows
            job=db.execute('SELECT state FROM audio_jobs WHERE job_id=?',(row['job_id'],)).fetchone()
            if not job or job['state']!='completed':continue
            if db.execute("SELECT 1 FROM cleanup_members WHERE cleanup_id=? AND (state IN ('restore_intended','restored') OR COALESCE(restore_intent,'')!='') LIMIT 1",(row['id'],)).fetchone():continue
            now=stamp()
            if db.execute("UPDATE source_cleanup SET state='paused',reason='',updated=? WHERE id=? AND state='needs_attention' AND reason=?",(now,row['id'],LEGACY_BUSY)).rowcount==1:
                db.execute('INSERT OR IGNORE INTO source_cleanup_holds VALUES(?,?,?,?,?)',(row['id'],now,'needs_attention',LEGACY_BUSY,'legacy catalog busy'))
    def hold(self,id,error,attempt=None,record=True):
        """The single place a failed cleanup records its state; returns that state.

        A typed busy or locked catalog is not a verdict on the files: the cleanup pauses with an empty
        reason, so the next Start or Resume continues it from its durable progress, and the cause is
        kept in source_cleanup_holds. Any other failure needs attention with its reason, as before.
        The write is a replay-safe database update, so a busy catalog here is retried, not raised.
        """
        busy=catalog_busy(error)
        state,reason=('paused','') if busy else ('needs_attention',str(error) or type(error).__name__)
        cause=busy_cause(error,attempt) if busy and record else None
        def write(db):
            prior=db.execute('SELECT state,reason FROM source_cleanup WHERE id=?',(id,)).fetchone()
            if prior is None:return
            now=stamp()
            db.execute('UPDATE source_cleanup SET state=?,reason=?,updated=? WHERE id=?',(state,reason,now,id))
            if cause:db.execute('INSERT OR IGNORE INTO source_cleanup_holds VALUES(?,?,?,?,?)',(id,now,prior['state'],prior['reason'],cause))
        transaction(self.database,write)
        return state
    def _note_busy(self,id,error,attempt,wait):
        """Evidence for a busy attempt that will be retried; the cleanup's own state is unchanged.

        Returns whether the record was written. Pause and Stop also cut short its own busy retries.
        """
        def write(db):
            prior=db.execute('SELECT state,reason FROM source_cleanup WHERE id=?',(id,)).fetchone()
            if prior is not None:db.execute('INSERT OR IGNORE INTO source_cleanup_holds VALUES(?,?,?,?,?)',(id,stamp(),prior['state'],prior['reason'],busy_cause(error,attempt)+f'; retry in {wait} s'))
        try:
            transaction(self.database,write,stop=self.stop);return True
        except (sqlite3.Error,InterruptedError):return False  # Evidence only; the retry and the final hold() still run.
    def _retry_wait(self,seconds):
        """Wait before another attempt. True when Pause, Stop or Quit cut the wait short."""
        deadline=time.monotonic()+seconds
        while not (self.stop.is_set() or self.interrupt()):
            left=deadline-time.monotonic()
            if left<=0:return False
            self.stop.wait(min(left,.1))
        return True
    def run_with_retry(self,id):
        """run(id); a typed busy or locked catalog waits 5 s, then 15 s, and runs again (three attempts in all).

        Each attempt is a full run() from durable state, exactly what a manual Resume does, so no
        file operation or state step is added or skipped. Every failure is recorded through hold():
        busy pauses, anything else needs attention, and an interrupted wait pauses.
        """
        for attempt in range(1,len(RETRY_WAITS)+2):
            try:
                self.run(id);return
            except Exception as error:
                if not catalog_busy(error):
                    self.hold(id,error);return
                if attempt>len(RETRY_WAITS):
                    self.hold(id,error,attempt);return
                wait=RETRY_WAITS[attempt-1];noted=self._note_busy(id,error,attempt,wait)
                if self._retry_wait(wait):
                    self.hold(id,error,attempt,record=not noted);return
    def _rows(self,sql,params=()):
        with connect(self.database) as db:return [dict(r) for r in db.execute(sql,params)]
    def _set(self,id,state,reason=''):
        with connect(self.database) as db:
            now=stamp();db.execute('UPDATE source_cleanup SET state=?,reason=?,updated=? WHERE id=?',(state,reason,now,id))
            if state=='completed':db.execute('INSERT OR IGNORE INTO recovery_completion SELECT id,job_id,? FROM source_cleanup WHERE id=?',(now,id))
    def _sorted(self,path,error=ValueError):
        """The deletion rule (rulings 2 and 1a): the effective output is inside the configured output folder, which is
        set and outside every source. Read from the live configuration at each check."""
        from source_config import require_sorted
        output_root,sources=self.output_policy() if self.output_policy else (None,())
        # Ruling 71h: a folder Sergei chose counts as Sorted for the book filed directly in it (MergeService supplies them).
        chosen=getattr(self,'chosen_folders',None)
        try:require_sorted(str(path),output_root,sources,chosen() if callable(chosen) else ())
        except ValueError as problem:raise error(str(problem)) from None
    def enroll(self,job,binding,historical=False):
        if job['state']!='completed':raise ValueError('Only a completed validated audiobook can remove its sources')
        manifest=job['manifest'];output=job['output']
        if output['validation'].get('passed') is not True or not manifest['sources']:raise ValueError('Complete output validation is required')
        self._validation_contract(manifest,output)
        root=ordinary(manifest['root']);paths=[]
        for source in manifest['sources']:
            path=ordinary(source['path'])
            from encoding_policy import AUTOMATIC_PROFILE
            formats={'.mp3','.m4a','.m4b','.aac','.flac','.ogg','.opus','.wav','.wma'} if manifest.get('profile')==AUTOMATIC_PROFILE else {'.mp3'}
            if not path.is_relative_to(root) or path.suffix.lower() not in formats or 'podcasts' in [p.casefold() for p in path.relative_to(root).parts]:
                raise ValueError('Only selected verified audiobook originals are eligible')
            if str(path).casefold() in paths:raise ValueError('Duplicate selected source path')
            paths.append(str(path).casefold())
        with connect(self.database) as db:
            setup(db);prior=db.execute('SELECT id FROM source_cleanup WHERE job_id=?',(job['job_id'],)).fetchone()
        if not prior:self._sorted((self.output_location(output)[0] if self.output_location else output)['final_path'])
        id=str(uuid.uuid4());intent={'id':id,'job_id':job['job_id'],'manifest':manifest,'output':output,'binding':binding,'actor':'assistant','created':stamp(),'recovery_identity':self.root_identity,'historical':historical}
        with connect(self.database) as db:
            setup(db)
            prior=db.execute('SELECT id FROM source_cleanup WHERE job_id=?',(job['job_id'],)).fetchone()
            if prior:return prior[0]
            if self.guard(db,intent) is not True:raise ValueError('Completed book review/source selection changed')
            db.execute('INSERT INTO source_cleanup VALUES(?,?,?,?,?,?,?)',(id,job['job_id'],packed(intent),'waiting','',stamp(),stamp()))
        return id
    @staticmethod
    def _validation_contract(manifest,output):
        v=output['validation'];meta=manifest.get('metadata',{});tags=v.get('tags',{})
        if v.get('checks')!='Output checks passed' or v.get('profile')!=manifest.get('profile') or v.get('sha256')!=output['sha256'] or v.get('size')!=output['size']:
            raise ValueError('The complete published output validation record is required')
        if str(tags.get('media_type'))!='2' or tags.get('title')!=meta.get('title') or tags.get('artist')!=meta.get('canonical_author'):
            raise ValueError('Validated audiobook kind, title and author do not match the reviewed book')
        if v.get('publication_mode')=='in_place':
            # 0.21.0, no decode (Sergei, 2026-10-22): the original itself became the output; its byte proof replaces PCM frames.
            proof=v.get('in_place',{});reviewed=manifest['sources'][0]['sha256'] if len(manifest['sources'])==1 else None
            if proof.get('all_retained_bytes_verified') is not True or proof.get('original_sha256')!=reviewed or v.get('metadata_preservation',{}).get('source_sha256')!=reviewed:
                raise ValueError('Exact in-place byte proof of the selected source is required')
        else:
            frames=v.get('source_pcm_frames',[]);rate=v.get('source_pcm_rate')
            if len(frames)!=len(manifest['sources']) or not isinstance(rate,int) or rate<=0 or any(not isinstance(n,int) or n<=0 for n in frames):
                raise ValueError('Exact selected-source decoded-audio validation is required')
            if abs(float(v.get('decoded_duration',-1))-sum(frames)/rate)>float(v.get('duration_tolerance',0)):
                raise ValueError('Decoded output does not match the selected source audio')
        if 'part_chapters' in manifest:
            from audio_pipeline import planned_chapter_titles
            expected_chapters=planned_chapter_titles(manifest)  # ruling 19a: joined parts keep their own chapters
        else:expected_chapters=[c['title'] for c in manifest['source_chapters']] if 'source_chapters' in manifest else manifest.get('chapters',[])
        if [c.get('title') for c in v.get('chapters',[])]!=expected_chapters:raise ValueError('Validated chapter choice does not match this completed book')
    def status(self,job_id=None):
        rows=self._rows('SELECT * FROM source_cleanup'+(' WHERE job_id=?' if job_id else '')+' ORDER BY created', (job_id,) if job_id else ())
        result=[]
        for row in rows:
            intent=json.loads(row['intent']);members=self._rows('SELECT * FROM cleanup_members WHERE cleanup_id=?',(row['id'],))
            removed=[m for m in members if m['state']=='removed'];total=len(intent['manifest']['sources'])
            state='pausing' if self.current==row['id'] and self.stop.is_set() else row['state']
            storage={}
            with connect(self.database) as db:
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='storage_cleanup_jobs'").fetchone():
                    stored=db.execute('SELECT * FROM storage_cleanup_jobs WHERE job_id=?',(row['job_id'],)).fetchone()
                    if stored:storage=dict(stored)
            evidence_count=0
            with connect(self.database) as db:
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='storage_cleanup_preserved'").fetchone():
                    evidence_count=sum(regular_evidence(r['path']) for r in db.execute('SELECT path FROM storage_cleanup_preserved WHERE job_id=?',(row['job_id'],)))
            temporary=storage.get('state','pending')
            success='Originals removed; verified temporary recovery and working copies removed' if temporary=='completed' else 'Originals removed; removing temporary files' if temporary in ('checking','removing') else 'Originals removed; temporary file cleanup pending'
            reason=row['reason'] or storage.get('reason','')
            if temporary=='needs_attention':success='Source cleanup needs attention: '+reason+'. Remaining originals and temporary files are preserved for recovery.'
            current_bytes=0
            for member in members:
                try:current_bytes+=Path(member['backup']).stat().st_size
                except FileNotFoundError:pass
            texts={'waiting':'Waiting for output checks','checking':'Checking temporary recovery copies','removing':f'Removing originals: {len(removed)} of {total}',
                'pausing':'Pausing source cleanup','paused':f'Source cleanup paused: {len(removed)} of {total} removed','completed':success,
                'needs_attention':'Source cleanup needs attention: '+reason+'. Remaining originals and temporary files are preserved for recovery.'}
            result.append({'id':row['id'],'job_id':row['job_id'],'state':state,'status':texts[state],'removed':len(removed),'total':total,'remaining':total-len(removed),
                'checked':self.checked.get(row['id'],0) if state=='checking' else None,
                'bytes_removed':sum(json.loads(m['facts'])['size'] for m in removed),'recovery_bytes':current_bytes,
                'recovery_location':str(self.root/row['id']) if current_bytes else '', 'temporary_cleanup':temporary,
                'preserved_evidence_count':evidence_count,'restore_available':bool(members) and all(Path(m['backup']).is_file() for m in members),'reason':reason})
        provider=getattr(self,'recovery_status',None)
        if provider:
            for item in result:
                item['recovery']=provider(item['job_id']);recovery=item['recovery']
                if recovery['state']!='unavailable':item['restore_available']=item['restore_available'] and recovery['state']=='retained'
                item['restore_available']=item['restore_available'] and all(Path(m['path']).parent.is_dir() for m in self._rows('SELECT path FROM cleanup_members WHERE cleanup_id=?',(item['id'],)))
                if item['state']=='completed':
                    if recovery['state']=='retained':item['status']='Originals removed; deleting recovery copies'
                    elif recovery['state']=='deleting':item['status']='Originals removed; deleting recovery copies'
                    elif recovery['state']=='needs_attention':item['status']='Originals removed; recovery cleanup needs attention: '+recovery['reason']
                    elif recovery['state']=='deleted':item['status']='Originals removed; recovery copies deleted'
                item['recovery_bytes']=recovery['bytes'];item['recovery_location']=recovery['location'] if recovery['count'] else ''
        return result[0] if job_id and result else (None if job_id else result)
    def resume(self,selected=None,follow_audio=True,admission_check=None,after_drain=None,admission_token=None):
        with self.lock:
            if self.closed:raise ValueError('Cleanup worker is closing')
            if admission_check is not None and admission_check() is not True:
                from audio_jobs import StartRefused
                raise StartRefused('stale','Cleanup startup was superseded by Pause or closing.')
            if self.thread and self.thread.is_alive():
                if admission_check is not None and (self.stop.is_set() or getattr(self,'_thread_admission_token',None)!=admission_token):
                    from audio_jobs import StartRefused
                    raise StartRefused('busy','The previous cleanup worker is still pausing. Retry Start after it stops.')
                return {'state':'checking'}
            self.stop.clear()
            try:
                if admission_check is not None and admission_check() is not True:
                    from audio_jobs import StartRefused
                    raise StartRefused('stale','Cleanup startup was superseded by Pause or closing.')
            except BaseException:
                self.stop.set();raise
            self._thread_admission_token=admission_token
            self.thread=threading.Thread(target=self._work,args=(selected,follow_audio,after_drain),name='books-source-cleanup',daemon=False)
            self.thread.start()
            return {'state':'started'}

    def pause(self):
        with self.lock:self.stop.set()
    def close(self):
        with self.lock:
            self.closed=True;self.stop.set();worker=self.thread
        if worker:
            worker.join(30)
            if worker.is_alive():raise TimeoutError('Source cleanup is still reaching its safe file checkpoint')

    def _work(self,selected=None,follow_audio=True,after_drain=None):
        # Senua 0.21.3 F1: a cleanup refused only because this process had no valid output folder runs again here;
        # every check runs again before any copy or removal, so a setting that is still missing refuses again.
        from source_config import CONFIGURATION_REFUSALS
        retried=('Additional filesystem streams require review; original retained','Download marker native identity differs','Unknown download marker contents preserved')+CONFIGURATION_REFUSALS
        for row in self._rows("SELECT * FROM source_cleanup WHERE state IN ('waiting','paused') OR (state='needs_attention' AND reason IN (%s)) ORDER BY created"%','.join('?'*len(retried)),retried):
            if selected is not None and row['id'] not in selected:continue
            if self.stop.is_set():break
            self.current=row['id']
            try:
                self.run_with_retry(row['id'])
                if self.on_completed and self.status(row['job_id'])['state']=='completed':self.on_completed(row['job_id'])
            except Exception as error:self.hold(row['id'],error)
            finally:self.current=None
        handoff=after_drain if after_drain is not None else self.after_drain
        if follow_audio and not self.stop.is_set() and handoff:handoff()
    @staticmethod
    def _match(handle,source,stored=None,approved=None):
        facts=handle.facts()
        if facts['size']!=source['size'] or facts['modified']!=int(source['modified']) or facts['links']!=1 or facts['attributes']&~0xA0:
            raise BoundaryError('Source size, timestamp, attributes or alias layout changed/unsupported')
        if stored and any(facts.get(k)!=stored.get(k) for k in ('identity','identity_method','dev','ino')):raise BoundaryError('Original source file identity changed or its identity representation drifted')
        if approved and (facts['dev'],facts['ino'])!=(approved.get('dev'),approved.get('ino')):raise BoundaryError('Reviewed original file identity changed or cannot be verified')
        if handle.sha256()!=source['sha256']:raise BoundaryError('Original bytes differ from reviewed sources')
        return facts
    def run(self,id):
        # Audit m3: a download marker this run removed from an original that is still in place when the run stops or
        # holds is put back from its receipt; only a removed original loses its marker.
        # Senua 0.21.3 F4: so is one an earlier run removed before it was killed (crash, power loss): its receipt stays
        # in source_zone_marker_intents, and every run starts by putting such markers back.
        self._put_back_markers(id,self._stale_markers(id))
        marked={}
        try:result=self._run(id,marked)
        except BaseException:
            self._put_back_markers(id,marked);raise
        self._put_back_markers(id,marked)
        return result
    def _stale_markers(self,id):
        """{path: (receipt, facts, root)} for every marker receipt of this cleanup; _put_back_markers restores only those
        whose original is still in place, unchanged and without its marker."""
        rows=self._rows('SELECT path,receipt FROM source_zone_marker_intents WHERE cleanup_id=?',(id,))
        if not rows:return {}
        cleanup=self._rows('SELECT intent FROM source_cleanup WHERE id=?',(id,))
        if not cleanup:return {}
        manifest=json.loads(cleanup[0]['intent'])['manifest'];sources={s['path']:s for s in manifest['sources']}
        members={m['path']:m for m in self._rows('SELECT path,facts,state FROM cleanup_members WHERE cleanup_id=?',(id,))}
        found={}
        for row in rows:
            source=sources.get(row['path']);member=members.get(row['path'])
            if source is None or member and member['state'] in ('removed','disposition_set'):continue
            facts=json.loads(member['facts']) if member and member['facts'] else {'size':source['size'],'modified':int(source['modified']),'attributes':None}
            found[row['path']]=(json.loads(row['receipt']),facts,manifest['root'])
        return found
    def _put_back_markers(self,id,marked):
        """Best effort: the same file (native identity, size, single link) gets its exact marker bytes and write time back.
        Anything that does not match is left as it is; the receipt in source_zone_marker_intents keeps the bytes."""
        import base64
        from zone_identifier import MARKER,restore_marker,streams
        for path,(receipt,facts,root) in list(marked.items()):
            try:
                p=ordinary(path)
                if not os.path.lexists(p):continue
                with DirectoryBoundary(ordinary(root),p.parent),VerifiedFile(p,writable=True) as handle:
                    now=handle.refresh()
                    if now['identity']!=receipt['identity'] or now['size']!=facts['size'] or now['links']!=1:continue
                    if MARKER in {name for name,_ in streams(p)}:continue
                    restore_marker(p,base64.b64decode(receipt['marker_bytes_base64']))
                    attributes=facts['attributes'] if facts.get('attributes') is not None else now['attributes']
                    handle.restore_metadata(facts['modified'],attributes);handle.flush()
                marked.pop(path,None)
            except (BoundaryError,OSError,ValueError,KeyError):pass
    def _run(self,id,marked):
        row=self._rows('SELECT * FROM source_cleanup WHERE id=?',(id,))[0];intent=json.loads(row['intent']);manifest=intent['manifest'];out=intent['output']
        source_root=ordinary(manifest['root'])
        frozen_root=ordinary(manifest.get('output_root',manifest['root']))
        if ordinary(out.get('root',str(frozen_root)))!=frozen_root:raise BoundaryError('Validated output root differs from frozen output policy')
        if self.output_location:
            out,envelope=self.output_location(out)
            intent['_location_envelope']=envelope
        root=ordinary(out.get('root',str(frozen_root)));final=ordinary(out['final_path']);recovery=self.root/id
        if not final.is_relative_to(root) or final.suffix.lower()!='.m4b':raise BoundaryError('Validated output is outside the frozen output root')
        with contextlib.ExitStack() as stack:
            rb=stack.enter_context(DirectoryBoundary(self.root.anchor,recovery,create=True))
            if rb.identities[:len(self.root_identity)]!=self.root_identity:raise BoundaryError('Recovery root identity changed')
            if [list(v) for v in self.root_identity]!=[list(v) for v in intent['recovery_identity']]:raise BoundaryError('Persisted recovery ancestry changed')
            ob=stack.enter_context(DirectoryBoundary(root,final.parent));output=stack.enter_context(VerifiedFile(final))
            if out.get('identity') is not None and output.facts()['identity']!=out['identity']:raise BoundaryError('Relocated output native identity changed; originals retained')
            if ob.identities!=[tuple(v) for v in out['parent_identity']] or output.facts()['size']!=out['size'] or output.sha256()!=out['sha256']:
                raise BoundaryError('Validated output is changed or unavailable; originals retained')
            cover=ordinary(manifest['cover']['path']);stack.enter_context(DirectoryBoundary(cover.anchor,cover.parent));art=stack.enter_context(VerifiedFile(cover))
            if art.sha256()!=manifest['cover']['sha256']:raise BoundaryError('Reviewed cover bytes changed')
            with connect(self.database) as db:
                if not self.guard(db,intent):raise BoundaryError('Completed book review changed')
            if out['validation'].get('publication_mode')=='in_place':return self._retire_moved(id,intent,manifest,out)
            self._sorted(final,BoundaryError)  # before any copy or marker change; again before each disposal below
            self._set(id,'checking');held=[]
            required=sum(s['size'] for s in manifest['sources'])
            if shutil.disk_usage(self.root).free<required+1024*1024:raise BoundaryError('Insufficient recovery space; originals retained')
            for index,source in enumerate(manifest['sources']):
                self.checked[id]=index
                path=ordinary(source['path']);backup=recovery/(f'{index:05d}'+path.suffix.lower())
                prior=self._rows('SELECT * FROM cleanup_members WHERE cleanup_id=? AND path=?',(id,str(path)))
                member=prior[0] if prior else None
                if member and member['backup']!=str(backup):raise BoundaryError('Recovery correspondence changed')
                if member and member['state'] in ('removed','disposition_set'):
                    recovery_handle=stack.enter_context(VerifiedFile(backup,writable=True));recovery_handle.flush()
                    if recovery_handle.facts()['size']!=source['size'] or recovery_handle.sha256()!=source['sha256']:raise BoundaryError('Recovery bytes changed')
                    if path.exists():raise BoundaryError('An existing replacement at a retired original path was preserved')
                    if member['state']=='disposition_set':self._retire(intent,source,member)
                    continue
                if member and member['state']=='removal_intended' and not path.exists():
                    raise BoundaryError('Interrupted removal has unknown outcome; verified recovery can restore this original before another cleanup attempt')
                stack.enter_context(DirectoryBoundary(source_root,path.parent))
                key=str(uuid.uuid5(uuid.NAMESPACE_URL,os.path.normcase(os.path.abspath(str(path)))))
                approved=intent['binding'].get('context',{}).get('source_hashes',{}).get(key)
                from zone_identifier import remove_marker
                def validate_marker_base(handle):
                    self._match(handle,source,json.loads(member['facts']) if member else None,approved)
                    with connect(self.database) as db:
                        if not self.guard(db,intent):raise BoundaryError('Reviewed source changed before download marker removal')
                removed_marker={}
                def persist_marker(receipt):
                    with connect(self.database) as db:
                        db.execute('INSERT OR IGNORE INTO source_zone_marker_intents VALUES(?,?,?,?,?)',(id,str(path),receipt['marker_sha256'],packed(receipt),stamp()))
                    removed_marker['receipt']=receipt
                remove_marker(path,validate_marker_base,persist_marker)
                original=stack.enter_context(VerifiedFile(path,delete=True))
                facts=self._match(original,source,json.loads(member['facts']) if member else None,approved);single_stream(path)
                if removed_marker:marked[str(path)]=(removed_marker['receipt'],facts,str(source_root))
                if not member:
                    if backup.exists():raise BoundaryError('Unknown recovery collision; originals retained')
                    with connect(self.database) as db:
                        db.execute('INSERT INTO cleanup_members(cleanup_id,path,backup,facts,state) VALUES(?,?,?,?,?)',(id,str(path),str(backup),packed(facts),'backup_pending'))
                        db.execute('INSERT OR IGNORE INTO owned_artifacts VALUES(?,?,?,?,?)',(str(backup),intent['job_id'],'recovery',source['sha256'],source['size']))
                    with open(backup,'xb') as dest:
                        for block in original.chunks():dest.write(block)
                        dest.flush();os.fsync(dest.fileno())
                backup_handle=stack.enter_context(VerifiedFile(backup,writable=True))
                backup_handle.restore_metadata(facts['modified'],facts['attributes'])
                backup_handle.flush() # Also required for reused backup_pending copies, after timestamp updates.
                if backup_handle.facts()['size']!=source['size'] or backup_handle.sha256()!=source['sha256']:raise BoundaryError('Recovery copy failed full byte verification; originals retained')
                with connect(self.database) as db:db.execute("UPDATE cleanup_members SET state='backup_verified',backup_facts=? WHERE cleanup_id=? AND path=?",(packed(backup_handle.facts()),id,str(path)))
                held.append((source,original,facts))
            # All recovery copies are durable and protected BEFORE the first dispose.
            self.checked.pop(id,None)
            self._set(id,'removing')
            for source,original,facts in held:
                if self.stop.is_set():self._set(id,'paused');return
                rb.revalidate();ob.revalidate()
                # Senua 0.21.3 F2: the pure re-reads run before the removal intent is recorded too, so a refusal leaves no
                # member in removal_intended (restore() reads that as a collision). They run again just before disposal.
                self._sorted(final,BoundaryError);self._output_present(output,out,final)
                # Ruling 27: one original's removal (intent, disposal, retirement record) finishes once begun.
                with critical_sections.critical(critical_sections.CLEANUP),self.review_boundary(),connect(self.database) as db:
                    db.execute('BEGIN IMMEDIATE')
                    if not self.guard(db,intent):raise BoundaryError('Completed source review changed before removal')
                    db.execute("UPDATE cleanup_members SET state='removal_intended' WHERE cleanup_id=? AND path=?",(id,source['path']))
                    db.commit() # Intent must survive a crash before native disposition.
                    db.execute('BEGIN IMMEDIATE')
                    if not self.guard(db,intent):raise BoundaryError('Completed source review changed before disposition')
                    if self.output_location_guard and not self.output_location_guard(db,intent['output'],intent.get('_location_envelope'),require_transaction=True):raise BoundaryError('Current output location changed before source disposition')
                    self._sorted(final,BoundaryError)
                    self._output_present(output,out,final)
                    single_stream(source['path'])
                    original.dispose();marked.pop(str(ordinary(source['path'])),None)
                    db.execute("UPDATE cleanup_members SET state='disposition_set' WHERE cleanup_id=? AND path=?",(id,source['path']))
                    original.__exit__(None,None,None)
                    if Path(source['path']).exists():raise BoundaryError('Disposition did not remove the verified name; no weaker deletion attempted')
                    db.commit() # Keep the location-generation reservation through native closure and absence.
                    db.execute('BEGIN IMMEDIATE');self._retire(intent,source,{'facts':packed(facts)},db);db.commit()
            self._set(id,'completed')
    @staticmethod
    def _output_present(output,out,final):
        """Audit m1: the held handle blocks deletes over SMB, not on the NAS itself; re-read the output now."""
        now=output.refresh()
        if now['size']!=out['size'] or now['links']<1 or not os.path.lexists(final) or out.get('identity') is not None and now['identity']!=out['identity']:
            raise BoundaryError('Validated output changed or is gone before source removal; originals retained')
    def _retire_moved(self,id,intent,manifest,out):
        """0.21.0 in-place edit: the original WAS the output (verified in full above). Its journaled no-copy rename is
        its retirement; there is no recovery copy and no deletion. A file at the old name is preserved and blocks."""
        import inplace_m4b
        source=manifest['sources'][0];path=ordinary(source['path'])
        moved=inplace_m4b.published_move(self.database,intent['job_id'],str(path)) if len(manifest['sources'])==1 else None
        if moved is None and len(manifest['sources'])==1:
            # A crash or rename postcondition error after the rename journaled no receipt: prove the move itself (0.21.0 F2).
            moved=inplace_m4b.confirm_move(self.database,intent['job_id'],str(path),out['final_path'])
        if moved is None:raise BoundaryError('In-place move receipt is missing; nothing retired')
        if os.path.lexists(path):raise BoundaryError('A file at the moved original path was preserved')
        facts={'disposition':'renamed_into_output','size':source['size'],'modified':source['modified'],'sha256':source['sha256'],
               'final_path':moved['final_path'],'identity':moved['identity']}
        with self.review_boundary(),connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE')
            if not self.guard(db,intent):raise BoundaryError('Completed source review changed before retirement')
            db.execute('INSERT OR IGNORE INTO cleanup_members(cleanup_id,path,backup,facts,state) VALUES(?,?,?,?,?)',
                       (id,str(path),str(self.root/id/('00000'+path.suffix.lower())),packed(facts),'removed'))
            self._retire(intent,source,{'facts':packed(facts)},db);db.commit()
        self._set(id,'completed')
    def _retire(self,intent,source,member,db=None):
        if db is None:
            with connect(self.database) as connection:return self._retire(intent,source,member,connection)
        db.execute("UPDATE cleanup_members SET state='removed' WHERE cleanup_id=? AND path=?",(intent['id'],source['path']))
        db.execute('INSERT OR REPLACE INTO source_retirements VALUES(?,?,?,?,?,?,?,?)',(intent['manifest']['root'],source['path'],intent['id'],intent['job_id'],source['sha256'],source['size'],source['modified'],'removed'))
        db.execute("UPDATE files SET missing=0,error='' WHERE root=? AND path=?",(intent['manifest']['root'],source['path']))
    def restore(self,id):
        receipt=next((r for r in self.status() if r['id']==id),None)
        if receipt and not receipt['restore_available']:
            raise BoundaryError('Temporary recovery files are unavailable after successful cleanup; original tracks cannot be restored from them')
        """Technical opaque-ID restore; preserve any current destination collision."""
        with self.lock:
            if self.thread and self.thread.is_alive():raise ValueError('Pause cleanup before restoring originals')
            row=self._rows('SELECT * FROM source_cleanup WHERE id=?',(id,))
            if not row:raise ValueError('Unknown recovery identity')
            intent=json.loads(row[0]['intent']);root=ordinary(intent['manifest']['root'])
            for member in self._rows("SELECT * FROM cleanup_members WHERE cleanup_id=? AND state IN ('removed','removal_intended','disposition_set','restore_intended')",(id,)):
                source=next(s for s in intent['manifest']['sources'] if s['path']==member['path']);path=ordinary(source['path']);backup=ordinary(member['backup'])
                if backup.parent!=self.root/id or not path.is_relative_to(root):raise BoundaryError('Recovery mapping is outside its owned boundary')
                with DirectoryBoundary(self.root.anchor,backup.parent) as rb,VerifiedFile(backup) as held,DirectoryBoundary(root,path.parent) as boundary:
                    if [list(v) for v in self.root_identity]!=[list(v) for v in intent['recovery_identity']]:raise BoundaryError('Persisted recovery ancestry changed')
                    if rb.identities[:len(self.root_identity)]!=self.root_identity:raise BoundaryError('Recovery ancestor identity drifted before restoration')
                    if held.facts()['size']!=source['size'] or held.sha256()!=source['sha256']:raise BoundaryError('Recovery copy changed')
                    if path.exists():
                        saved=json.loads(member['restore_intent']) if member['restore_intent'] else None
                        if not saved:raise FileExistsError('Restore collision; existing file preserved')
                        with VerifiedFile(path) as restored:
                            if restored.facts()['identity']!=saved['identity'] or restored.sha256()!=source['sha256'] or restored.facts()['modified']!=int(source['modified']):raise FileExistsError('Restore collision; unrelated replacement preserved')
                        self._restored(id,str(path));continue
                    temp=path.parent/('.books-restore-'+str(uuid.uuid4())+'.partial')
                    with connect(self.database) as db:db.execute('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)',(str(temp),intent['job_id'],'temporary',source['sha256'],source['size']))
                    with open(temp,'xb') as dest:
                        for block in held.chunks():dest.write(block)
                        dest.flush();os.fsync(dest.fileno())
                    facts=json.loads(member['facts'])
                    with VerifiedFile(temp,writable=True) as temporary:
                        temporary.restore_metadata(facts['modified'],facts['attributes']);temporary.flush()
                    def intent_before_rename(native):
                        native.update(temporary=str(temp),destination=str(path))
                        with connect(self.database) as db:db.execute("UPDATE cleanup_members SET state='restore_intended',restore_intent=? WHERE cleanup_id=? AND path=?",(packed(native),id,str(path)))
                    publish_no_replace(temp,path,boundary,source['sha256'],source['size'],intent_before_rename)
                    self._restored(id,str(path))
            self._set(id,'needs_attention','Originals restored; recovery copies retained. Cleanup is not automatically repeated.')
    def _restored(self,id,path):
        with connect(self.database) as db:
            db.execute("UPDATE cleanup_members SET state='restored' WHERE cleanup_id=? AND path=?",(id,path))
            db.execute("UPDATE source_retirements SET state='restored' WHERE cleanup_id=? AND path=?",(id,path))
