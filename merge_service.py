"""Join reviewed candidates to the durable, source-preserving media queue."""
from encoding_policy import LEGACY_PROFILE, AUTOMATIC_PROFILE
import contextlib
import copy
import json
import os
import re
import sqlite3
from pathlib import Path
import threading
import time
import hashlib
import uuid
import subprocess
import functools
import shutil

from audio_jobs import AudioJobs, repair_record, StartRefused
from audio_pipeline import create_private, publish, digest, fingerprint, Paused, PROFILE
from native_io import DirectoryBoundary, ProtectedFiles, VerifiedFile, ordinary
from review_backend import CandidateReviewService
from scanner import connect
from metadata import propose
from source_cleanup import CleanupJobs, packed
from review_backend import member_key, NEEDS_GROUPS, JOB_GROUPS
from conversion_progress import approved_scope,completed_book,phase_progress
from replacement_jobs import Replacements,digest as record_digest,now as replacement_now
from replacement_retirement import ReplacementRetirement
from current_audiobook import CurrentAudiobooks
import groups

INITIAL_CLEANUP_JOBS={'0b6fedcc-2d95-46a9-a4a3-4192da37ff72','dc4874af-e132-47cd-93ab-85e5b0fbeea7'}
STATUS_MAX_AGE=1.0 # Seconds after a status computation STARTED during which polling readers may reuse it.
STATUS_WAIT=4.0 # Seconds a reader waits on another thread's computation; below the desktop shell's 5 s request timeout.
STALE_WAIT=0.5 # Seconds a poll waits for a newer status when an earlier answer exists; then it gets that answer.
CATALOG_MAX_AGE=60.0 # Seconds catalog facts (cleanups, Ready totals) are reused per catalog version while no cleanup runs.
QUIET_MAX_AGE=300.0 # Seconds a polling answer is reused while nothing runs and the catalog has no new commit;
# the bound only refreshes what can change without a commit (files removed by hand outside the app).
WORKING_MAX_AGE=30.0 # The same bound while any listed row carries leftover working files: files removed outside the app
# show within a minute, not five (RefusedRetry follow-up 2, section 2.6); or a book stopped by a drive that went away.
WORKING_RECHECK=20.0 # Seconds a classified working folder is reused while its listing is unchanged (it stats the originals).
CHECK_REFRESH=10.0 # Seconds between status refreshes while the M4B check pass finishes checks (follow-up 2, section 3).
_QUIET_LOCK=threading.Lock()


class StatusUnavailable(RuntimeError):
    """Another thread's status computation did not finish within STATUS_WAIT; the poll reports status unavailable."""


# Background re-verification of finished books shares one read budget, so the
# library share keeps answering status and inventory metadata while it runs.
VERIFY_RATE=32*1024*1024


class Pacer:
    """One shared read budget (bytes per second) for background verification readers."""
    def __init__(self,rate,clock=time.monotonic,sleep=time.sleep):
        self.rate=rate;self._clock=clock;self._sleep=sleep;self._lock=threading.Lock();self._next=None

    def __call__(self,size,stop=None):
        with self._lock:
            now=self._clock();start=max(now,self._next if self._next is not None else now)
            self._next=start+size/self.rate;wait=start-now
        while wait>0:
            if stop is not None and stop.is_set():raise InterruptedError('Published-book check stopped')
            step=min(wait,.1);self._sleep(step);wait-=step
        if stop is not None and stop.is_set():raise InterruptedError('Published-book check stopped')


class _Flag:
    """is_set() over a live condition, for cooperative stops that are not one Event."""
    def __init__(self,check):self.is_set=check


def verify_digest(path,stop=None,pace=None):
    """Full SHA-256 of a published book; stop interrupts between 1 MiB blocks, pace limits background reads."""
    value=hashlib.sha256()
    with open(path,'rb') as stream:
        while block:=stream.read(1024*1024):
            if stop is not None and stop.is_set():raise InterruptedError('Published-book check stopped')
            if pace is not None:pace(len(block),stop)
            value.update(block)
    return value.hexdigest()


def file_identity(path):
    """Native identity of a published file: volume, file id, size, modification time."""
    stat=os.stat(path)
    return [stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns]


class SharedSnapshot:
    """Single-flight read: concurrent callers wait for one computation, then reuse it until max_age after it started.

    Threads arriving while a computation runs never start another one, so a slow
    catalog cannot accumulate one expensive computation per poll. invalidate()
    (after every control) drops the remembered answer and detaches a running
    computation: its result is never cached and no later reader joins it.

    The computation runs on its own thread. While it runs, a reader gets the last good answer after
    STALE_WAIT instead of "still updating" (v0.16.8: under load half of the polls answered 503 and the
    page showed "Local server unavailable"). Only with no answer yet, or right after a control, does a
    reader wait the full bound for a fresh one.
    """
    def __init__(self,clock=time.monotonic,wait=STATUS_WAIT):
        self._lock=threading.Lock();self._clock=clock;self._wait=wait;self._value=None;self._at=None;self._flight=None;self._generation=0
        self._last=None  # (value, generation, started) of the newest finished computation

    def invalidate(self):
        with self._lock:self._generation+=1;self._value=None;self._at=None;self._flight=None

    def _run(self,flight,compute):
        try:flight['value']=compute()
        except BaseException as error:flight['error']=error
        finally:
            with self._lock:
                if flight['error'] is None:
                    if flight['generation']==self._generation:self._value,self._at=flight['value'],flight['started']
                    if self._last is None or flight['started']>=self._last[2]:self._last=(flight['value'],flight['generation'],flight['started'])
                if self._flight is flight:self._flight=None
            flight['done'].set()

    def get(self,compute,max_age):
        with self._lock:
            if self._at is not None and 0<=self._clock()-self._at<max_age:return copy.deepcopy(self._value)
            flight=self._flight
            if flight is None:
                flight=self._flight={'done':threading.Event(),'value':None,'error':None,'generation':self._generation,'started':self._clock()}
                threading.Thread(target=self._run,args=(flight,compute),name='books-status',daemon=True).start()
            last=self._last;current=self._generation
        bound=self._wait if last is None or last[1]!=current else min(self._wait,STALE_WAIT)
        if not flight['done'].wait(bound):
            if last is not None:return copy.deepcopy(last[0])
            raise StatusUnavailable('Status computation is still running')
        if flight['error'] is not None:raise flight['error']
        return copy.deepcopy(flight['value'])

_BULK_LOCK=threading.Lock()    # Retry all: its run record and thread
_REPAIR_LOCK=threading.Lock()  # M4B repair checks: pending ids and the checker thread
JOB_ONLY_FIELDS=('job_id','attempt_id','m4b_repair')  # never produced by the review's build_manifest
_PURGE_LOCK=threading.RLock()  # one recovery purge at a time (the converter's and the sweep's never overlap)
_WORKING_LOCK=threading.Lock()  # the working-folder classification cache and the folders whose clear failed
_MANUAL_LOCK=threading.Lock()   # the queued Delete recovery copies presses (ruling 35)

def attention_counts(summary):
    """(counts per attention group, Can retry books whose leftover working files Retry clears first) for the strip and
    the Retry all dialog (RefusedRetry follow-up 2, section 2.4: k is the server's, read when the dialog opens)."""
    counts=dict.fromkeys(JOB_GROUPS,0);cleanable=0  # the one list of chips (review_backend)
    for item in summary.values():
        counts[item['group']]=counts.get(item['group'],0)+1
        if item['group']=='retry' and isinstance(item.get('working'),dict) and item['working'].get('state')=='cleanable':cleanable+=1
    return counts,cleanable

def catalog_busy_text(reason):
    return 'database is locked' in (reason or '') or 'database is busy' in (reason or '')

def operation(method):
    @functools.wraps(method)
    def locked(self,*args,**kwargs):
        with self.operation_lock:return method(self,*args,**kwargs)
    return locked


class MergeService:
    draining=False # Set by a desktop Quit: the current book finishes, nothing new starts.

    def __init__(self, inventory, cache_dir, progress=None):
        from publication_locations import require_no_pending_moves
        require_no_pending_moves(inventory.database)
        self.inventory = inventory
        self.operation_lock=threading.RLock()
        self._progress_lock=threading.RLock()
        self._approved_cache=None
        self._post_current=None
        self._validated_outputs={}
        self._held_sources={}  # job_id -> sources its in-place publication holds deny-writers (review_backend held)
        self.cache_dir = ordinary(cache_dir)
        with DirectoryBoundary(self.cache_dir.anchor,self.cache_dir,create=True):pass
        self.stage_root = self.cache_dir / 'audio-staging'
        self.reviews = CandidateReviewService(inventory, self.cache_dir / 'covers')
        with connect(inventory.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS owned_artifacts(path TEXT PRIMARY KEY, job_id TEXT, kind TEXT, sha256 TEXT, size INTEGER)')
            # Last full verification of each published book (path, sha) and the file identity it had then.
            db.execute('CREATE TABLE IF NOT EXISTS verified_outputs(path TEXT, sha256 TEXT, job_id TEXT, identity TEXT, verified TEXT, PRIMARY KEY(path, sha256))')
        self._pacer=Pacer(VERIFY_RATE)
        self.replacements=Replacements(inventory.database)
        from publication_binding import PublicationBindings
        self.publication_bindings=PublicationBindings(inventory.database)
        self.publications=CurrentAudiobooks(tuple(inventory.source_roots('Audiobooks'))+((inventory.output_root,) if getattr(inventory,'output_root',None) else ()) if hasattr(inventory,'source_roots') else inventory.roots['Audiobooks'],self.cache_dir.parent/'chapter-repairs',self.replacements,
                                            verified=self._publication_current,remember=self._publication_verified,pace=self._pacer,bindings=self.publication_bindings)
        self.retirement=ReplacementRetirement(self.replacements,self.cache_dir.parent/'replacement-recovery',inventory.roots['Audiobooks'],threading.Event(),self._replacement_guard,self.publications.protect_former,bindings=self.publication_bindings)
        self.jobs = AudioJobs(inventory.database, self._run, self._guard, self._output_valid,self.retirement.historical_retired)
        self.jobs.output_current=self._output_current;self.jobs.verify_pace=self._pacer
        self.retirement.stop=self.jobs._stop
        self.jobs.pending_postprocessing=self._pending_replacement_postprocessing
        self.jobs.postprocessing=self._finish_replacement
        self.cleanup = CleanupJobs(inventory.database,self.cache_dir.parent/'source-recovery',self._cleanup_guard,self._review_boundary,output_location=self.publication_bindings.current,output_location_guard=self.publication_bindings.guard,output_policy=lambda:self.output_policy())
        self.cleanup.stop=self.jobs._stop
        # Pause and Stop set the shared stop; a Quit drain does not, so it is checked separately.
        self.cleanup.interrupt=lambda:self.draining or self.jobs._drain.is_set()
        self.jobs.after_completed=self._after_completed
        self.cleanup.after_drain=None  # Each Merge resume supplies its own generation-bound handoff.
        from storage_cleanup import StorageCleanup
        self.storage_cleanup=StorageCleanup(inventory.database,self.stage_root,self.cleanup.root,self._storage_guard,output_location=self.publication_bindings.current,output_location_guard=self.publication_bindings.guard,repair_publication=self._repair_publication,repair_location_guard=self.publication_bindings.guard)
        from working_lifecycle import WorkingLifecycle
        self.working=WorkingLifecycle(inventory.database,self.stage_root,self._working_guard)
        from producer_recovery import ProducerRecovery,windows_boot
        self.producer_recovery=ProducerRecovery(inventory.database,self.stage_root,active=lambda job,attempt:getattr(self,'_active_producer',None)==(job,attempt),boot=windows_boot)
        self.jobs.before_attempt=self.working.admit
        self.jobs.attempt_boundary=self._attempt_boundary
        self.jobs.destination_policy=self._destination_policy
        self.jobs.next_priority=self._next_m4b_readmission
        self.jobs.m4b_working_clear=self._m4b_working_clear  # live check for a Retry refused on working files
        self.jobs.repair_check_failed=self._repair_check_failed  # a dry run that cannot finish reads "can't open", never "checking"
        self.jobs.working_state=self._working_state  # leftover working files: cleanable or blocked, live (follow-up 2)
        # Edit names (Judy 0.22.2 section 1.4): a job planned under other names than Sergei's saved ones never starts.
        self.jobs.names_stamp=self._names_stamp
        self.jobs.names_stale=self._names_stale
        self.jobs.names_replan=self._names_replan
        try:
            # Once per catalog: v0.18.0 plain-text Retry/Repair refusals become typed records (RefusedRetry spec).
            import m4b_readmission
            with connect(inventory.database) as db:m4b_readmission.convert_legacy(db)
        except sqlite3.Error:pass  # unconverted records read the same way (retry_refusal.parse); the next start converts them
        self.jobs.after_attempt=self.working.terminal
        self.jobs.after_failed=self._record_source_damage
        from recovery_retention import RecoveryRetention
        self.recovery=RecoveryRetention(self.storage_cleanup,guard=self._retention_guard)
        self.cleanup.recovery_status=self.recovery_status
        self._retention_stop=threading.Event();self._retention_wake=threading.Event();self._retention_thread=None;self._manual_recovery=None
        # 0.22.2 (Futaba's 0.22.1 QA, m-3): Restart to update holds the background recovery pass at its next safe point;
        # Cancel, the bound or a failed close let it go on (desktop_backend). It used to run set after set while the update
        # waited for it (_post_current), up to the engine's 150 s bound at 8,000 books.
        self._update_hold=threading.Event()
        self.cleanup.on_completed=lambda job_id:self._prune_completed(job_id,source_completed=True)
        # Rulings 69 and 71h: folders Sergei chose hold books directly; they count as Sorted for those books.
        self.publications.chosen_roots=self._chosen_folders;self.cleanup.chosen_folders=self._chosen_folders
        self._start_move_recovery()
        self.reviews.set_jobs(self)
        from automatic_processing import AutomaticProcessing
        self.automatic=AutomaticProcessing(self)
        self.automatic.on_change=self.invalidate_status  # a pending start that fires, changes kind or ends shows on the next poll
        from series_backfill import SeriesBackfill
        self.series_backfill=SeriesBackfill(self,research=self.automatic.research)  # v0.16.12; started with the retention sweep
        from gap_fill import GapFill
        self.gap_fill=GapFill(self)  # 0.22.1: optional fields after approval (research: the automatic pass's); started with series backfill
        self.jobs.on_space_hold=lambda:self.automatic.stop(force=True)
        self.jobs.on_working_hold=lambda:self.automatic.stop(force=True)
        # Startup (0.22.1, ruling 28): every finished book's location is looked up once, in one catalog snapshot. Each used
        # to be resolved twice through current() (a lookup and its fresh re-check: 42 s for 508 books on the live catalog),
        # recorded through its own connection (3 s) and checked for enrollment through the full cleanup status (recovery
        # sets and source folders, 10 s). Display lookups need no lease: nothing here reads or removes a file. They also
        # seed progress_books' cache (_lookups), so the first status does not resolve them again. progress(done, total)
        # reports each book to the startup loader, which may stop the construction there (web_server.LoadAborted).
        known=self._known_identities()
        completed=[job for job in self.jobs.status()['jobs'] if job['state']=='completed']
        with connect(inventory.database) as db:
            db.executemany('INSERT OR REPLACE INTO owned_artifacts VALUES(?,?,?,?,?)',[(job['output']['final_path'],job['job_id'],'output',job['output']['sha256'],job['output']['size']) for job in completed])
            enrolled={row[0] for row in db.execute('SELECT job_id FROM source_cleanup')}
        looked={}
        with connect(inventory.database) as db:
            db.execute('BEGIN');token=self.publication_bindings.lookup_token(db)
            for index,job in enumerate(completed):
                if progress is not None:progress(index,len(completed))
                # Ready/converted counts compare the live file with its last full verification, from the first status.
                try:
                    effective,envelope=self.publication_bindings.remembered(db,job['output'],token)  # the first page reuses it too
                    looked[job['job_id']]=((token,packed(job['output'])),(effective,envelope))
                    identity=known.get(self._identity_key(effective['final_path'],effective['sha256']))
                    if identity:self._validated_outputs[job['job_id']]=tuple(identity)
                except (ValueError,OSError,KeyError):pass  # Current-view reports the binding failure; catalog remains readable.
        self._lookups=looked
        if progress is not None:progress(len(completed),len(completed))
        for job in completed:
            if job['manifest'].get('cleanup_policy',{}).get('enabled') and job['job_id'] not in enrolled:
                # A crash after durable audio success but before enrollment does
                # not turn its explicit frozen policy into a historical sweep.
                self._enroll_completed_without_start(job)

    @operation
    def prepare_producer_recovery(self,job_id):
        self._no_scan()
        if self.draining:raise ValueError('The app is closing; recovery checkpoint was not saved')
        capability=self.producer_recovery.prepare(job_id)
        self.invalidate_status()
        return {'job_id':job_id,'producer_recovery':capability,'queued':False,'outputs_changed':False}

    def producer_retention(self,candidate_id):
        return self.producer_recovery.retained(candidate_id)

    # Сказка (0.21.1): the statement Sergei ticks, verbatim (rulings 6-7); the recorded claim carries exactly this text.
    ORIGIN_STATEMENTS=('The interrupted conversion ran on this PC.','Since then, Windows and these files were not moved, copied, cloned or restored from a backup.')

    def confirm_origin_and_convert(self,library,identity,revision,job_id,statements):
        """Confirm and convert: save Sergei's origin statement (record_origin), prove the old producer ended by a later
        Windows startup, and queue the recovery Retry, in one press. A failed proof keeps the statement (UX spec R1a)."""
        from audio_jobs import RetryRefused,RETRY_SCANNING,RETRY_CLOSING
        import producer_recovery
        if library!='Audiobooks':raise ValueError('Audiobook operations apply only to Audiobooks')
        if list(statements)!=list(self.ORIGIN_STATEMENTS):raise ValueError('Both statements must be confirmed exactly as shown')
        if self.inventory.worker and self.inventory.worker.is_alive():raise RetryRefused(RETRY_SCANNING.replace('Retry','Convert'))
        if self.draining:raise RetryRefused(RETRY_CLOSING.replace('Retry','Convert'))
        self._reacquire_admission(identity=identity)
        changed='This book changed. Review its details and try again.'
        if self.producer_recovery.status(job_id).get('can_confirm_origin') is not True:raise RetryRefused(changed,'book_changed')
        try:parent=self._m4b_parent(job_id,identity,revision,lambda row:row['state']=='needs attention' and not row['output'])
        except RetryRefused:parent=None
        if parent is None:raise RetryRefused(changed,'book_changed')
        self.producer_recovery.record_origin(job_id,{'actor':'user','claim':producer_recovery.CLAIM,'evidence':'Confirmed by the user in Books Arranger (Confirm and convert): '+' '.join(self.ORIGIN_STATEMENTS),'statements':list(self.ORIGIN_STATEMENTS)})
        capability=self.producer_recovery.status(job_id);self.invalidate_status()
        if capability['state']!='ready':return {'job_id':job_id,'accepted':False,'queued_next':False,'origin_recorded':True,'producer_recovery':capability}
        result=self._request_m4b_readmission(job_id,'retry');self._resume_later()
        return {'job_id':job_id,'requeued':False,'origin_recorded':True,**result,'producer_recovery':capability}

    def output_policy(self):
        """(configured output folder or None, every source and library root), read live (Sergei, rulings 2 and 1a)."""
        inventory=self.inventory
        sources=inventory.all_source_roots() if hasattr(inventory,'all_source_roots') else tuple(getattr(inventory,'roots',{}).values())
        return getattr(inventory,'output_root',None),tuple(sources)

    def _require_sorted(self,path):
        """ValueError unless path is in the configured output folder, which is set and outside every source (or directly
        in a folder Sergei chose for it, ruling 71h)."""
        from source_config import require_sorted
        chosen=getattr(self,'_chosen_folders',None)
        require_sorted(str(path),*self.output_policy(),chosen() if callable(chosen) else ())

    def _finish_recovery_child(self,job_id):
        """Ruling 5, in the worker right after the child's lease on the old files ends: remove them, then the child's
        normal source cleanup. A refusal keeps the files and the original, with its reason."""
        # Never raises into the worker: the child is published, and each refusal is recorded where its own step records it.
        id=None;row=None;posting=self.__dict__.setdefault('_post_jobs',set());posting.add(job_id)
        try:
            row=next((job for job in self.jobs.status()['jobs'] if job['job_id']==job_id),None)
            if not row or row['state']!='completed' or self.cleanup.status(job_id):return
            try:self._dispose_retained(job_id);id=self.enroll_cleanup(job_id)['cleanup_id'];self.cleanup.current=id;self.cleanup.run_with_retry(id)
            except Exception as error:
                if id:self.cleanup.hold(id,error)
                else:self._enrollment_attention(row,error)
            finally:self.cleanup.current=None
            self._prune_completed(job_id)  # then temporary files, in the normal order (_after_completed_work)
        except Exception as error:self.storage_cleanup._diagnose(job_id,'',error)
        finally:posting.discard(job_id)

    def _dispose_retained(self,job_id):
        """Ruling 5: a verified boot-proved recovery child removes its parent's old working files before its own source
        cleanup is enrolled. Any refusal keeps the files and protects the original (_cleanup_guard), visibly."""
        binding=(self.jobs._rows('SELECT manifest FROM audio_jobs WHERE job_id=?',(job_id,)) or [{'manifest':'{}'}])[0]
        binding=json.loads(binding['manifest']).get('retry_intent') or {}
        if binding.get('retained_disposal') is not True:return None
        roots=[*self.inventory.roots.values(),*(self.inventory.all_source_roots() if hasattr(self.inventory,'all_source_roots') else ()),*([self.inventory.output_root] if getattr(self.inventory,'output_root',None) else [])]
        try:
            # Audit m5: the child's published output is hashed in full and held while the old files go, not taken from
            # the catalog's flags alone.
            with self.storage_cleanup.protected_output(job_id,guard=lambda:None):
                return self.producer_recovery.dispose(binding['parent_job_id'],job_id,roots)
        except (ValueError,OSError) as error:raise ValueError('Old working files of the interrupted attempt were kept, so the original is kept too: '+str(error)) from error

    def _destination_policy(self):
        import destination_admission
        sources=self.inventory.source_roots('Audiobooks') if hasattr(self.inventory,'source_roots') else [self.inventory.roots['Audiobooks']]
        return destination_admission.policy(self.inventory.roots,sources,getattr(self.inventory,'output_root',None))

    def _destination_preflight(self,manifest):
        root=ordinary(manifest.get('output_root',manifest['root']));destination=ordinary(manifest['destination'])
        if not destination.is_relative_to(root):raise ValueError('Current proposed destination is outside its output root')
        parent=destination.parent
        while not os.path.lexists(parent) and parent!=root:parent=parent.parent
        with DirectoryBoundary(root.anchor,root),DirectoryBoundary(root,parent) as held:
            if os.path.lexists(destination):raise ValueError('Current proposed destination already exists: '+str(destination))
            held.revalidate()

    @contextlib.contextmanager
    def _attempt_boundary(self,row):
        import destination_admission
        manifest=json.loads(row['manifest'])
        if any(key in manifest for key in ('replacement_id','replacement_parent_job_id')):
            relation=self.replacements.get(new_job=manifest['job_id'])
            target=self._destination_policy()['output_root'] or manifest['root']
            if not relation or relation.get('id')!=manifest.get('replacement_id') or relation.get('replacement_job_id')!=manifest['job_id'] or relation.get('state')!='queued' or json.loads(relation['approval_json']).get('replacement_manifest')!=manifest or destination_admission.path_key(manifest.get('output_root',manifest['root']))!=destination_admission.path_key(target) or not self.replacements.structural_guard(relation,queued=True):raise ValueError('Queued replacement destination or lineage needs its exact replacement review; generic route Retry is unavailable')
            yield
            return
        observation=destination_admission.observe(manifest,self._destination_policy())
        if observation:
            if row['attempt_id'] is not None:raise ValueError('Saved destination changed; prior working attempt requires normal verified review before retry')
            raise destination_admission.DestinationReviewNeeded(observation)
        binding=json.loads(row['manifest']).get('retry_intent') or {}
        if not binding.get('retained_checkpoint_id'):
            yield
            return
        with self.producer_recovery.protect_retained(binding['parent_job_id']) as retained:
            if retained['checkpoint_id']!=binding['retained_checkpoint_id']:raise ValueError('Retained producer checkpoint differs at attempt admission')
            yield
        if binding.get('retained_disposal') is True:self._finish_recovery_child(row['job_id'])  # the write-deny lease has ended

    def _enroll_completed_without_start(self,job):
        try:
            self._dispose_retained(job['job_id'])
            self.enroll_cleanup(job['job_id'])
        except (ValueError,OSError) as error:
            # Senua 0.21.3 F1: a process started without a valid output folder enrols nothing and parks nothing;
            # the next start with the setting enrols the book (its sources stay, rulings 2 and 1a).
            from source_config import CONFIGURATION_REFUSALS
            if str(error) in CONFIGURATION_REFUSALS:return
            self._enrollment_attention(job,error)

    def _enrollment_attention(self,job,error):
        with connect(self.inventory.database) as db:
            id=str(uuid.uuid4());intent={'id':id,'job_id':job['job_id'],'manifest':job['manifest'],'output':job['output'],'binding':{},'actor':'assistant'}
            db.execute('INSERT OR IGNORE INTO source_cleanup VALUES(?,?,?,?,?,?,?)',(id,job['job_id'],packed(intent),'needs_attention',str(error),'',''))

    def _register(self,path,job,kind,hash='',size=0):
        with connect(self.inventory.database) as db:
            db.execute('INSERT OR REPLACE INTO owned_artifacts VALUES(?,?,?,?,?)',(path,job,kind,hash,size))

    def progress_books(self,jobs=None,cleanups=None,storage=None,folders=None):
        """One coherent catalog observation (one SQLite snapshot); no writer/reader transaction crosses filesystem checks.

        0.22.1 (backlog items 6-7): it takes Inventory.group_lock only to rebuild stale groups, never for the read, and
        never while it holds its own lock. It used to hold group_lock for the whole read, about 500 publication lookups
        (15 s on the live catalog), on every status computation, which each research step and each poll makes: the list,
        Scan again, Remove from list, Delete and approvals queued behind it. Each approved book is rendered again only when
        its own row changed, and each job's publication lookup is reused while its receipt and the relocation records are
        unchanged (PublicationBindings.lookup_token)."""
        from catalog_contention import groups_current,synchronize_groups
        jobs=jobs if jobs is not None else self.jobs.status()['jobs']
        cleanups=cleanups if cleanups is not None else self.cleanup.status()
        storage=storage if storage is not None else self.storage_cleanup.status()
        folders=folders if folders is not None else self.storage_cleanup.folder_status()
        roots=list(self.inventory.source_roots('Audiobooks')) if hasattr(self.inventory,'source_roots') else [self.inventory.roots['Audiobooks']]
        if not groups_current(self.inventory,roots):
            # Control paths may already own group_lock before calling state(): taken here first, never after _progress_lock.
            with self.inventory.group_lock:synchronize_groups(self.inventory,roots)
        self._progress_lock.acquire()
        try:
            with connect(self.inventory.database) as db:
                db.execute('BEGIN')
                root_json=json.dumps(roots)
                candidate_ids={r[0] for r in db.execute('SELECT id FROM book_groups WHERE root IN (SELECT value FROM json_each(?)) AND superseded=0',(root_json,))}
                rows=[dict(r) for r in db.execute("SELECT g.*,c.revision AS context_revision,c.data AS context_data FROM book_groups g JOIN candidate_context c ON c.id=g.id WHERE g.root IN (SELECT value FROM json_each(?)) AND g.superseded=0 AND json_extract(c.data,'$.metadata_approved')=1",(root_json,))]
                signature=[(r['id'],r['revision'],r['fingerprint'],r['review'],r['context_revision'],r['context_data'],r['changed']) for r in rows]
                if self._approved_cache is None or self._approved_cache[0]!=signature:
                    # Each row is rendered again only when its own row changed (an approval used to render all ~500).
                    previous=self.__dict__.get('_approved_rows') or {}
                    retired=None;approved={};rendered={}
                    for r,key in zip(rows,signature):
                        if r['context_revision']!=r['revision']:continue
                        kept=previous.get(r['id'])
                        if kept is not None and kept[0]==(key,r['root']):
                            rendered[r['id']]=kept
                            if kept[1] is not None:approved[r['id']]=kept[1]
                            continue
                        if retired is None:
                            retired={}
                            for root in roots:retired.update(groups.retired_sources(db,root))
                        row=groups.render(r,r['root'],True,retired);ctx=json.loads(r['context_data'])
                        if ctx.get('metadata_facts'):
                            from standing_metadata import validate_policy
                            validate_policy(row,row['review'],ctx['metadata_facts'])
                            row['preview']=propose(row['members'][0]['path'],self.reviews._output_root(row),'audiobook',row['metadata'],row['review'],automatic_facts=ctx['metadata_facts'])
                        if (row.get('review') or {}).get('organization_policy')=='books-hierarchy-v2':row['preview']=propose(row['members'][0]['path'],self.reviews._output_root(row),'audiobook',row['metadata'],row['review'],automatic_facts=ctx.get('metadata_facts'))
                        value=(row,ctx) if approved_scope(row,ctx,member_key) else None
                        rendered[r['id']]=((key,r['root']),value)
                        if value is not None:approved[row['id']]=value
                    self._approved_rows=rendered
                    self._approved_cache=(signature,approved)
                catalog_approved=dict(self._approved_cache[1])
                # Do not use Replacements.get/representative: their cached/new-connection
                # rows can belong to another snapshot. Freeze the same exact DB guards here.
                replacements=getattr(self,'replacements',None)
                relations=[dict(r) for r in db.execute('SELECT * FROM audiobook_replacements ORDER BY created,id')] if replacements else []
                representatives=[]
                if replacements:
                    for identity in catalog_approved:
                        matches=[r for r in relations if r['candidate_id']==identity]
                        if len(matches)>1:raise ValueError('Ambiguous replacement relation')
                        relation=matches[0] if matches else None
                        if relation and relation['state'] in {'published','retiring','completed'}:
                            job=next((j for j in jobs if j['job_id']==relation['replacement_job_id']),None)
                        else:
                            matches=[j for j in jobs if j['manifest']['candidate_id']==identity and not j['manifest'].get('replacement_id')]
                            job=matches[-1] if matches else None
                        representatives.append((job,relation))
                else:representatives=[(job,None) for job in jobs]
                observed=[]
                bindings=getattr(self,'publication_bindings',None)
                token=bindings.lookup_token(db) if bindings is not None and hasattr(bindings,'lookup_token') else None
                looked=self.__dict__.get('_lookups') or {};kept={}
                for job,relation in representatives:
                    if not job or job['manifest']['candidate_id'] not in catalog_approved:continue
                    record=job.get('output') or {};effective=None;location_envelope=None
                    key=(token,packed(record)) if token is not None else None
                    saved=looked.get(job['job_id'])
                    if key is not None and saved is not None and saved[0]==key:
                        effective,location_envelope=saved[1];kept[job['job_id']]=saved  # read-only below
                    else:
                        try:
                            effective,location_envelope=bindings.lookup(db,record) if bindings else (record,None)
                            if key is not None:kept[job['job_id']]=(key,(effective,location_envelope))
                        except (OSError,KeyError,ValueError):pass
                    binding=relation if relation and relation['state'] in {'published','retiring','completed'} and replacements.structural_guard(relation,db=db) else None
                    retry_binding=False
                    if job['manifest'].get('retry_intent'):
                        import retry_intent
                        proof=job['manifest']['retry_intent']
                        retry_binding=retry_intent.guard(db,job['manifest'],proof['approved_manifest'],proof['target_root'])
                    observed.append((job,relation,binding,effective,location_envelope,retry_binding))
                self._lookups=kept
            # DB committed/closed before every filesystem callback.
            approved={identity:(row,ctx) for identity,(row,ctx) in catalog_approved.items()
                      if any((self.reviews.cache/(ctx['cover_id']+suffix)).is_file() for suffix in ('.png','.jpg'))}
            source_by={r['job_id']:r for r in cleanups};storage_by={r['job_id']:r for r in storage};folder_by={r['job_id']:r for r in folders}
            converted=set()
            for job,relation,binding,effective,location_envelope,retry_binding in observed:
                identity=job['manifest']['candidate_id']
                if identity not in approved:continue
                if relation and relation['state'] in {'published','retiring','completed'} and binding is None:continue
                row,ctx=approved[identity];current=False
                try:
                    stat=Path(effective['final_path']).stat()
                    current=(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns)==self._validated_outputs.get(job['job_id'])
                except (OSError,KeyError,ValueError,TypeError):pass
                if completed_book(row,ctx,job,source_by.get(job['job_id']),storage_by.get(job['job_id']),folder_by.get(job['job_id']),current,member_key,{PROFILE,AUTOMATIC_PROFILE},binding,location_envelope=location_envelope,retry_binding=retry_binding):converted.add(identity)
            return {'approved':len(approved),'converted':len(converted),'converted_ids':converted,'candidate_total':len(candidate_ids),'not_approved_total':len(candidate_ids-set(approved))}
        finally:self._progress_lock.release()

    def warm_status(self,progress=None):
        """Startup (0.22.1, ruling 28): the first status, computed by the loader with a counter. Its largest part, the
        cleanup status of every enrolled book (9 s on the live catalog), is read one book at a time, in the order the full
        read gives, each reported to progress(done, total), and kept as the status computation keeps it (_catalog_cached),
        so state() reuses it. Returns state()."""
        self._catalog_version(create=True)
        before=self._catalog_version()
        rows=self.cleanup._rows('SELECT * FROM source_cleanup ORDER BY created',())
        cleanups=[]
        for index,row in enumerate(rows):
            if progress is not None:progress(index,len(rows))
            item=self.cleanup.status(row['job_id'])
            if item is not None:cleanups.append(item)
        if progress is not None:progress(len(rows),len(rows))
        # Nothing else writes while loading; a commit in between all the same means a fresh full read.
        self._catalog_cached('cleanups',lambda:cleanups if self._catalog_version()==before else self.cleanup.status())
        return self.state()

    def status_snapshot(self,max_age=STATUS_MAX_AGE):
        """Polling routes only: concurrent readers share one state() computation, reused briefly. Controls keep fresh state().

        While the app is quiet (nothing runs, no catalog commit since), the last answer is reused for up to
        QUIET_MAX_AGE: an idle window no longer re-reads the catalog every second.
        """
        token=self._quiet_token(True)
        with _QUIET_LOCK:
            kept=self.__dict__.get('_quiet_state')
            if token is not None and kept and kept[0]==token and 0<=time.monotonic()-kept[1]<self.quiet_max_age():return copy.deepcopy(kept[2])
        started,value=self.__dict__.setdefault('_status_shared',SharedSnapshot()).get(lambda:(self._quiet_token(),self.state()),max_age)
        if token is not None and started==token:
            with _QUIET_LOCK:self._quiet_state=(token,time.monotonic(),copy.deepcopy(value))
        return value

    def cached_page(self,limit,offset,search,status,group=None):
        """The book list for polling: a quiet app reuses the identical page (see status_snapshot). A page the list marks
        'recheck' (an offer withheld while its audiobook was out of reach: Futaba's 0.22.0 QA, m-15) is reused for
        WORKING_MAX_AGE at most: a drive coming back is no catalog commit."""
        key=(limit,offset,search,status,group);token=self._quiet_token(True)
        with _QUIET_LOCK:
            kept=self.__dict__.get('_quiet_pages',{}).get(key)
            if token is not None and kept and kept[0]==token and 0<=time.monotonic()-kept[1]<min(self.quiet_max_age(),kept[3]):return copy.deepcopy(kept[2])
        value=self.reviews.page(limit,offset,search,status,group) if group else self.reviews.page(limit,offset,search,status)
        recheck=isinstance(value,dict) and value.pop('recheck',False) is True
        if token is not None and self._quiet_token()==token:
            with _QUIET_LOCK:
                pages=self.__dict__.setdefault('_quiet_pages',{})
                if len(pages)>=16:pages.clear()
                pages[key]=(token,time.monotonic(),copy.deepcopy(value),WORKING_MAX_AGE if recheck else QUIET_MAX_AGE)
        return value

    def quiet_max_age(self):
        """How long a quiet poll may reuse its answer: QUIET_MAX_AGE, or WORKING_MAX_AGE while the last status listed a row
        with leftover working files (they can go without a catalog commit, removed outside the app)."""
        return WORKING_MAX_AGE if self.__dict__.get('_working_listed') else QUIET_MAX_AGE

    def cleanup_statuses(self,job_ids,max_age=30.0):
        """Book list: each shown book's cleanup status, reused from the last status computation while it is under
        max_age old or the app has stayed quiet since (one status costs about 30 ms per book on the real catalog). Book
        list speed (Sergei 2026-10-24, ruling 18): 30 s, not 5 s, as for converted_ids(); the page polls the status every
        0.8 s, and under load one status computation takes longer than 5 s, so the page read every job's status again."""
        kept=self.__dict__.get('_cleanup_kept')
        age=time.monotonic()-kept[0] if kept else -1
        if kept and (0<=age<max_age or 0<=age<QUIET_MAX_AGE and kept[1] is not None and kept[1]==self._quiet_token()):
            return {job_id:copy.deepcopy(kept[2].get(job_id)) for job_id in job_ids}
        return {job_id:self.cleanup.status(job_id) for job_id in job_ids}

    def _busy(self):
        """Anything in this app that changes polling answers without a catalog commit is running."""
        jobs=getattr(self,'jobs',None);cleanup=getattr(self,'cleanup',None)
        # Not here: the published-book check (its progress is part of the quiet token, so its status refreshes
        # once per checked book) and the M4B repair checks (their classes show when the pass ends, which
        # invalidates the status; they are saved, so a pass runs once per job, not per launch).
        threads=(getattr(jobs,'_thread',None),getattr(cleanup,'thread',None),
                 getattr(getattr(self,'automatic',None),'thread',None),getattr(getattr(self,'inventory',None),'worker',None),
                 getattr(getattr(self,'publications',None),'_thread',None),
                 self.__dict__.get('_retry_all_thread'))
        return bool(any(thread is not None and thread.is_alive() for thread in threads) or getattr(jobs,'_resuming',False)
                    or getattr(cleanup,'current',None) or getattr(self,'_post_current',None) or getattr(self,'_resume_pending',False) or getattr(self,'draining',False))

    def _catalog_version(self,create=False):
        """(PRAGMA data_version on one idle monitor connection, control counter): equal between two reads only
        if no catalog commit and no control happened between them. None until a poll opens the monitor."""
        try:
            with _QUIET_LOCK:
                monitor=self.__dict__.get('_monitor')
                if monitor is None:
                    if not create:return None
                    monitor=self._monitor=sqlite3.connect(self.inventory.database,timeout=1,check_same_thread=False)
                return (monitor.execute('PRAGMA data_version').fetchone()[0],self.__dict__.get('_quiet_generation',0))
        except Exception:return None

    def _catalog_cached(self,name,compute):
        """Catalog facts that change with a commit or with cleanup work, not with a book's progress (cleanup,
        storage and folder status, the Ready totals): reused for up to CATALOG_MAX_AGE per catalog version while
        no cleanup work runs. A poll during conversion no longer re-reads every recovery set and checks every
        source folder on the library share, which under conversion load took seconds (v0.16.8 item 1)."""
        version=self._catalog_version();cleanup=getattr(self,'cleanup',None);thread=getattr(cleanup,'thread',None)
        settled=version is not None and not getattr(cleanup,'current',None) and not (thread and thread.is_alive()) and not getattr(self,'_post_current',None)
        kept=self.__dict__.setdefault('_catalog_kept',{}).get(name)
        if settled and kept and kept[0]==version and 0<=time.monotonic()-kept[1]<CATALOG_MAX_AGE:return copy.deepcopy(kept[2])
        value=compute()
        if settled and self._catalog_version()==version:self._catalog_kept[name]=(version,time.monotonic(),copy.deepcopy(value))
        return value

    def _quiet_token(self,create=False):
        """Equal between two reads only if nothing ran and no catalog commit happened between them (PRAGMA
        data_version on one idle monitor connection, plus a counter every control bumps); None while busy.
        Only the polling entry points open the monitor (create=True); until then every answer is fresh."""
        try:
            if self._busy():return None
            version=self._catalog_version(create)
            if version is None:return None
            check=json.dumps(getattr(self.jobs,'_check_progress',None),sort_keys=True,default=str)
            return (*version,check)
        except Exception:return None

    def invalidate_status(self):
        """A control ran: the next polling read recomputes instead of reusing a pre-control answer."""
        shared=self.__dict__.get('_status_shared')
        if shared is not None:shared.invalidate()
        with _QUIET_LOCK:
            self._quiet_generation=self.__dict__.get('_quiet_generation',0)+1;self._quiet_state=None;self._quiet_pages={}

    def state(self):
        snapshot=getattr(getattr(self,'replacements',None),'snapshot',None)
        if snapshot is None:value=self._state()
        else:
            with snapshot():value=self._state()
        if isinstance(value,dict):
            run=self._bulk_retry_view()
            if run is not None:value['retry_all']=run
            waiting=self.__dict__.get('_start_waiting')
            if waiting is not None:value['start_waiting']={'reason':waiting['reason']}  # Resume kept until it settles (ruling 35)
        return value

    def _worker_active(self):
        """A book's inline cleanup holds the marker, or the cleanup or converter worker is alive.

        The cleanup thread is checked before the converter: it starts the converter before it exits.
        """
        cleanup=getattr(self.cleanup,'thread',None);jobs=getattr(self.jobs,'_thread',None)
        return bool(getattr(self.cleanup,'current',None) or (cleanup and cleanup.is_alive()) or (jobs and jobs.is_alive()))

    def _state(self):
        # Between two books the converter thread runs the finished book's cleanup inline and
        # then starts the next book; a cleanup thread resumes the converter before it exits.
        # Workers are sampled BEFORE the slow durable read too, so a cleanup that ends mid-read
        # (its marker cleared, its row still read as pending) is never reported Paused (v0.16.2).
        worker=self._worker_active();token=self._quiet_token();started=time.monotonic()
        value=self.jobs.status()
        cleanups=self._catalog_cached('cleanups',self.cleanup.status);storage=self._catalog_cached('storage',self.storage_cleanup.status)
        folders=self._catalog_cached('folders',self.storage_cleanup.folder_status)
        self._cleanup_kept=(started,token,{item['job_id']:item for item in cleanups})  # the book list reuses these
        raw_jobs=value['jobs']
        if hasattr(self,'replacements'):
            visible,completed=self.replacements.projected(value['jobs'],value['current_job_id'])
            value['jobs']=visible;value['completed']=completed
        current=next((j for j in value['jobs'] if j['job_id']==value['current_job_id']),None)
        pending=[c for c in cleanups if c['state'] in ('waiting','checking','removing','pausing','paused')]
        active=next((c for c in pending if c['id']==self.cleanup.current),None)
        if not active and pending and not value['current_job_id']:active=pending[0]
        post=self._post_current
        if not current and (active or post):
            id=active['job_id'] if active else post[0]
            current=next((j for j in value['jobs'] if j['job_id']==id),None)
        worker=worker or self._worker_active() # The pre-v0.16.2 after-read check, kept: a worker resumed mid-read.
        if pending and not value['current_job_id']:
            value['state']='Pausing' if worker and self.cleanup.stop.is_set() else 'Running' if worker else 'Paused'
            value['queued']+=len(pending)
        elif value['state']=='Paused' and worker:value['state']='Pausing' if self.cleanup.stop.is_set() else 'Running'
        errors=[c for c in cleanups if c['state']=='needs_attention']+[r for r in storage if r['state']=='needs_attention']
        if hasattr(self,'replacements'):
            for relation in self.replacements.rows():
                failure=json.loads(relation['failure_json'] or '{}')
                if failure and failure.get('type')!='InterruptedError':errors.append({'job_id':relation['replacement_job_id'],'state':'needs_attention','reason':failure.get('message','Replacement postprocessing needs attention'),'replacement':True})
        # Empty-folder housekeeping holds nothing and is never attention (Sergei, 2026-10-18).
        folder_notes=[]
        value['failed']+=len(errors)
        if errors and value['state']=='Completed':value['state']='Needs attention'
        progress=None
        if active:
            progress={'phase':'originals','completed':active.get('removed',0),'total':active.get('total',0)} if active['state'] in ('removing','pausing','paused') else {'phase':'recovery copies','completed':active.get('checked') or 0,'total':active.get('total',0)} if active['state']=='checking' and active.get('total') else {'phase':'recovery copies'}
        elif post:progress={'phase':post[1]}
        elif current:progress=phase_progress(current['stage'],current.get('progress'))
        elif errors:
            error=errors[0];current=next((j for j in value['jobs'] if j['job_id']==error['job_id']),None)
            phase='former outputs' if error.get('replacement') else 'originals' if error in cleanups else 'folders' if error in folders else 'temporary'
            progress={'phase':phase,'reason':error['reason'],'attention':True}  # held, not running
            if phase=='originals':progress.update(completed=error['removed'],total=error['total'])
        elif value['state'] in ('Paused','Needs attention'):
            waiting=next((j for j in reversed(value['jobs']) if j['state'] in ('pending','needs attention') and j.get('progress')),None)
            if waiting:current=waiting;progress=phase_progress(waiting['stage'],waiting['progress'])
        if current and (current.get('reason') or errors):
            progress=progress or {'phase':current['stage']}
            progress['reason']=current.get('reason') or next((e['reason'] for e in errors if e['job_id']==current['job_id']),'')
        attention_row=None
        if errors:
            # Shown as its own needs-attention row whatever else runs, so it never flickers in as
            # the active row between two books.
            error=errors[0];held=next((j for j in value['jobs'] if j['job_id']==error['job_id']),None)
            phase='former outputs' if error.get('replacement') else 'originals' if error in cleanups else 'folders' if error in folders else 'temporary'
            attention_row={'title':held['manifest']['metadata'].get('title','') if held else '','phase':phase,'reason':error.get('reason','')}
            if phase=='originals':attention_row.update(completed=error.get('removed'),total=error.get('total'))
        totals=self._catalog_cached('totals',lambda:self.progress_books(raw_jobs,cleanups,storage,folders))
        self._converted_cache=(started,set(totals.get('converted_ids') or ()),token)
        # One predicate feeds every count and every list (Judy 2026-10-24, section 1): stale job rows are not counted, and
        # the books only Sergei can move on are counted beside the stopped jobs.
        summary=self.attention_summary(retry=False)
        try:summary=self.stale_attention(summary,raw_jobs,set(totals.get('converted_ids') or ()))
        except (sqlite3.Error,OSError):pass
        counts,cleanable=attention_counts(summary)
        try:needs,coverage=self._todo()
        except (sqlite3.Error,OSError,ValueError):needs,coverage={},dict(self.NO_COVERAGE)
        for entry in needs.values():counts[entry['group']]=counts.get(entry['group'],0)+1
        for group in self.NEEDS_GROUPS:counts.setdefault(group,0)
        return {key:value[key] for key in ('state','queued','completed','failed')} | {
            'approved_total':totals['approved'],'converted_total':totals['converted'],'candidate_total':totals.get('candidate_total'),'not_approved_total':totals.get('not_approved_total'),'folder_cleanup_notes':list(dict.fromkeys(folder_notes)),
            'current_title':current['manifest']['metadata'].get('title','') if current else '',
            'current_job_id':current['job_id'] if current else None,'attempt_id':current.get('attempt_id') if current else None,
            'progress':progress,'stage':active['status'] if active else progress['phase'] if progress else '',
            'cleanup_active':bool(active or pending or post),'postprocessing_pending':bool(self._pending_replacement_postprocessing()) if hasattr(self,'replacements') else False,
            'published_check':value.get('published_check'),'attention_counts':counts,'todo_still_checking':coverage['still_checking'],'working_cleanable':cleanable,'attention_row':attention_row,
            'series_update':self.series_backfill.status() if 'series_backfill' in self.__dict__ else None}

    def converted_ids(self,max_age=30.0):
        """Converted candidate ids for the book list: the set the last status computation produced, while it is under
        max_age old or the app has stayed quiet since it. The page polls the status every 0.8 s, so that set is at most
        one status computation old, the same moment as the Jobs counts. Book list speed (Sergei 2026-10-24, ruling 18):
        the list no longer computes its own set once that one is 5 s old; that read waited for group_lock behind every
        automatic approval and costs 10-25 s on the live catalog. Only with no recent set (no status poll for 30 s)
        does the list compute it."""
        cached=getattr(self,'_converted_cache',None)
        age=time.monotonic()-cached[0] if cached else -1
        if cached and (0<=age<max_age or 0<=age<QUIET_MAX_AGE and len(cached)>2 and cached[2] is not None and cached[2]==self._quiet_token()):return set(cached[1])
        # 0.22.1: while a status computation reads the same set, the list shows the last one instead of queuing a second.
        computing=self.__dict__.get('_progress_lock')
        if cached and computing is not None:
            if not computing.acquire(blocking=False):return set(cached[1])
            computing.release()
        token=self._quiet_token();started=time.monotonic()
        value=set(self.progress_books()['converted_ids']);self._converted_cache=(started,value,token);return set(value)

    def pause(self):
        if self.draining:return None
        with _BULK_LOCK:
            self._start_generation=self.__dict__.get('_start_generation',0)+1
            self._pause_depth=self.__dict__.get('_pause_depth',0)+1
            pending=self.__dict__.get('_retry_all_stop')
            if pending:pending.set()
        try:
            # Neither queue can clear stop after this Pause completes using an older generation.
            self.cleanup.pause();self.jobs.pause()
        finally:
            with _BULK_LOCK:self._pause_depth-=1
        return self.state()

    def drain(self):
        """Finish current work; invalidate every delayed start before shutdown waits."""
        with _BULK_LOCK:
            self.draining=True;self._start_generation=self.__dict__.get('_start_generation',0)+1
            pending=self.__dict__.get('_retry_all_stop')
            if pending:pending.set()
            for press in list(self.__dict__.get('_approve_stops',())):press.set()
        self.jobs.drain()

    def drained(self):
        jobs=bool(self.jobs._thread and self.jobs._thread.is_alive())
        cleanup=bool(self.cleanup.thread and self.cleanup.thread.is_alive())
        return not jobs and not cleanup and not self.cleanup.current and not self._post_current

    def _capture_start_generation(self):
        with _BULK_LOCK:
            if self.__dict__.get('_closing') or self.draining:raise StartRefused('closing','Books is closing; saved retry requests are retained.')
            if self.__dict__.get('_pause_depth',0):raise StartRefused('busy','Pause is still reaching the queue checkpoints. Retry Start after it completes.')
            return self.__dict__.get('_start_generation',0)

    def _start_allowed(self,generation):
        # Read-only callback: called under worker locks; never acquires a Merge lock or performs I/O.
        return generation==self.__dict__.get('_start_generation',0) and not self.draining and not self.__dict__.get('_closing',False) and not self.__dict__.get('_pause_depth',0)

    def _authorize_automatic_cleanup(self,generation):
        # An admitted explicit Start renews the existing policy; a periodic wake never does.
        with _BULK_LOCK:
            if not self._start_allowed(generation):raise StartRefused('stale','Start was superseded by Pause or closing.')
            self._automatic_cleanup_generation=generation

    def resume(self,*,start_generation=None,pending_owner=None,recheck=True):
        """Start (or keep running) the audiobook queue. recheck (Start, the automatic run's start): first re-check every
        finished book (its temporary and folder cleanup, AudioJobs' published-output check), then answer the full status.

        recheck=False (an approval that queued a book, 0.22.1): only starts the queue when it is idle; no re-check of the
        finished books and no status computation. The approval path used to run both under the operation lock: 4-5 min on
        the live catalog (506 finished books) whenever the converter was idle, and a full status computation otherwise,
        with every press waiting."""
        generation=self._capture_start_generation() if start_generation is None else start_generation
        if recheck:self._recheck_finished(generation,pending_owner)
        return self._resume_guarded(generation,pending_owner,recheck)

    def _recheck_finished(self,generation,pending_owner=None):
        """Start's re-check of every finished book, one book at a time under the operation lock (0.22.1): presses run
        between two books instead of waiting minutes for the whole pass. Skipped while a worker runs, as before."""
        allow=lambda:self._start_allowed(generation)
        with self.operation_lock:
            if not allow():raise StartRefused('closing' if self.draining or self.__dict__.get('_closing') else 'stale','This start was superseded by Pause or closing; saved requests are retained.')
            if self.__dict__.get('_resume_pending') and self.__dict__.get('_resume_pending_owner') is not pending_owner:
                raise StartRefused('busy','A previous start request is still checking. Retry Start after it stops; saved retry requests are retained.')
            self._no_scan()
            if self.jobs._thread and self.jobs._thread.is_alive() or self.cleanup.thread and self.cleanup.thread.is_alive():return
            finished=[job['job_id'] for job in self.jobs.status()['jobs'] if job['state']=='completed']
        # The queue itself clears its stop only at guarded admission; pruning cannot erase Pause.
        stop=_Flag(lambda:not allow() or self.jobs._drain.is_set())
        try:
            for job_id in finished:
                with self.operation_lock:
                    if stop.is_set():raise InterruptedError()
                    self._prune_completed(job_id,stop=stop)
                time.sleep(.01)  # a press waiting for the lock takes it here (a lock handed straight back is not fair)
        except InterruptedError:raise StartRefused('stale','Startup was paused; saved retry requests are retained.')

    @operation
    def _resume_guarded(self,generation,pending_owner=None,recheck=True):
        allow=lambda:self._start_allowed(generation)
        answer=(lambda:self.state()) if recheck else dict
        if not allow():raise StartRefused('closing' if self.draining or self.__dict__.get('_closing') else 'stale','This start was superseded by Pause or closing; saved requests are retained.')
        if self.__dict__.get('_resume_pending') and self.__dict__.get('_resume_pending_owner') is not pending_owner:
            raise StartRefused('busy','A previous start request is still checking. Retry Start after it stops; saved retry requests are retained.')
        self._no_scan()
        if self.jobs._thread and self.jobs._thread.is_alive():
            if self.jobs._stop.is_set():raise StartRefused('busy','The audiobook worker is still pausing. Retry Start after it stops.')
            self._authorize_automatic_cleanup(generation)
            return answer()|{'start_admission':{'state':'running','generation':generation}}
        if self.cleanup.thread and self.cleanup.thread.is_alive():
            if self.cleanup.stop.is_set():raise StartRefused('busy','The cleanup worker is still pausing. Retry Start after it stops.')
            self._authorize_automatic_cleanup(generation)
            return answer()|{'start_admission':{'state':'checking','generation':generation}}
        if not allow():raise StartRefused('stale','Startup was paused; saved retry requests are retained.')
        pending=self.cleanup._rows("SELECT id,intent FROM source_cleanup WHERE state IN ('waiting','paused')")
        historical=[c['id'] for c in pending if json.loads(c['intent']).get('historical')]
        def handoff():
            try:return self.jobs.resume(admission_check=allow,admission_token=generation,settle=recheck)
            except Exception as error:
                value=self._record_start_failure(error)
                if isinstance(value,dict) and value.get('state')=='waiting':return {'start_admission':value}  # kept until it settles (ruling 35)
                return {'start_admission':{'state':getattr(error,'start_state','blocked'),'reason':str(error)}}
        if historical:started=self.cleanup.resume(historical,follow_audio=False,admission_check=allow,admission_token=generation)
        elif pending:started=self.cleanup.resume(admission_check=allow,after_drain=handoff,admission_token=generation)
        else:started=self.jobs.resume(admission_check=allow,admission_token=generation,settle=recheck)
        if not allow():raise StartRefused('closing' if self.draining or self.__dict__.get('_closing') else 'stale','Startup was superseded by Pause or closing; saved retry requests are retained.')
        self._authorize_automatic_cleanup(generation)
        admission=started.get('start_admission',started) if isinstance(started,dict) else {'state':'requested'}
        return answer()|{'start_admission':admission}

    def _cleanup_binding(self,db,manifest):
        row=db.execute('SELECT revision,review FROM book_groups WHERE id=?',(manifest['candidate_id'],)).fetchone()
        context=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(manifest['candidate_id'],)).fetchone()
        if not row or not context or row['revision']!=manifest['candidate_revision'] or context['revision']!=row['revision']:
            raise ValueError('Completed candidate revision changed')
        ctx=json.loads(context['data']);review=json.loads(row['review'])
        if review!=manifest['metadata'] or not all(ctx.get(k) for k in ('metadata_approved','source_coverage_confirmed','order_confirmed')):
            raise ValueError('Completed source/metadata approval changed')
        keys=[member_key(s['path']) for s in manifest['sources']]
        if [k for k in ctx.get('track_order',[]) if k in ctx.get('included',[])]!=keys or set(ctx.get('included',[]))!=set(keys) or ctx.get('cover_id')!=manifest['cover']['id']:
            raise ValueError('Completed source order or cover changed')
        for source,key in zip(manifest['sources'],keys):
            saved=ctx.get('source_hashes',{}).get(key,{})
            if any(str(saved.get(k))!=str(source[k]) for k in ('sha256','size','modified')):raise ValueError('Approved source fingerprint changed')
        if bool(ctx.get('chapters'))!=bool(manifest['chapters']):raise ValueError('Completed chapter choice changed')
        return {'context':ctx,'review':review,'revision':row['revision']}

    def _cleanup_guard(self,db,intent):
        try:
            self._no_scan();manifest=intent['manifest']
            from producer_recovery import protected_dependency
            if protected_dependency(db,[item['path'] for item in manifest.get('sources',[])]):return False
            row=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(intent['job_id'],)).fetchone()
            if not row or row['state']!='completed' or packed(json.loads(row['manifest']))!=packed(manifest) or packed(json.loads(row['output']))!=packed(intent['output']):return False
            if '_location_envelope' in intent and not self.publication_bindings.guard(db,intent['output'],intent['_location_envelope']):return False
            return self._cleanup_binding(db,manifest)==intent['binding']
        except (ValueError,KeyError,TypeError):return False

    @operation
    def enroll_cleanup(self,job_id,historical=False):
        if historical and job_id not in INITIAL_CLEANUP_JOBS:raise ValueError('Historical cleanup is limited to the two verified batch books')
        if historical and self.jobs._thread and self.jobs._thread.is_alive():raise ValueError('Pause audiobook work before enrolling historical cleanup')
        with self._review_boundary(),connect(self.inventory.database) as db:
            self._no_scan();row=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()
            if not row:raise ValueError('Unknown completed audiobook identity')
            job=dict(row);job['manifest']=json.loads(job['manifest']);job['output']=json.loads(job['output']) if job['output'] else None
            if not historical and not job['manifest'].get('cleanup_policy',{}).get('enabled'):raise ValueError('Original removal was not enrolled for this job')
            binding=self._cleanup_binding(db,job['manifest'])
        id=self.cleanup.enroll(job,binding,historical=historical)
        return {'cleanup_id':id,'status':self.cleanup.status(job_id)}

    def start_historical_cleanup(self,job_id):
        # Capture this human action before waiting for unrelated operation/enrollment work.
        generation=self._capture_start_generation()
        return self._start_historical_cleanup(job_id,generation)

    @operation
    def _start_historical_cleanup(self,job_id,generation):
        allow=lambda:self._start_allowed(generation)
        if not allow():raise StartRefused('stale','This cleanup request was superseded by Pause or closing; saved cleanup remains retained.')
        self._no_scan()
        if self.jobs._thread and self.jobs._thread.is_alive() or self.cleanup.thread and self.cleanup.thread.is_alive():raise ValueError('Wait for existing audiobook work to become idle')
        if any(j['state'] in ('pending','running') for j in self.jobs.status()['jobs']):raise ValueError('Unrelated queued audiobook work must be resolved before finite cleanup')
        if any(c['job_id']!=job_id and c['state'] in ('waiting','checking','removing','pausing','paused') for c in self.cleanup.status()):raise ValueError('Unrelated pending source cleanup must be resolved first')
        result=self.enroll_cleanup(job_id,historical=True)
        self.cleanup.resume([result['cleanup_id']],follow_audio=False,admission_check=allow,admission_token=generation)
        return result

    @operation
    def restore_cleanup(self,job_id):
        self._no_scan()
        if self.jobs._thread and self.jobs._thread.is_alive():raise ValueError('Pause audiobook work before restoring original tracks')
        receipt=self.cleanup.status(job_id)
        if not receipt:raise ValueError('No recovery enrollment exists for this audiobook')
        self.cleanup.restore(receipt['id']);return self.cleanup.status(job_id)

    def _storage_guard(self):
        self._no_scan()
        if self.jobs._stop.is_set():
            raise InterruptedError('Temporary cleanup interrupted; remaining copies retained')

    def _working_guard(self):
        self._no_scan()
        closing=getattr(self,'_retention_stop',None)
        if closing is not None and closing.is_set():raise InterruptedError('Working cleanup is closing')
        if self.__dict__.get('_update_hold') is not None and self._update_hold.is_set():raise InterruptedError('An update is stopping the work')
        if self.working.in_background:
            if self.jobs._thread and self.jobs._thread.is_alive() or self.cleanup.thread and self.cleanup.thread.is_alive() or self._post_current:
                raise InterruptedError('Foreground audiobook work takes priority over idle working cleanup')

    def _retention_guard(self):
        self._no_scan()
        if self._retention_stop.is_set():raise InterruptedError('Recovery cleanup is closing; remaining copies preserved')
        if self.__dict__.get('_update_hold') is not None and self._update_hold.is_set():raise InterruptedError('An update is stopping the work; remaining copies preserved')

    def _recovery_idle(self):
        """Recovery copies may be deleted now. v0.16.8 (Sergei, 2026-10-18): a book being converted or queued
        never holds them back any more; only a scan, closing, or a source cleanup removing originals right
        now (its own copies are what it writes) waits."""
        self._no_scan()
        if self._retention_stop.is_set():raise ValueError('Recovery cleanup is closing')
        if self.__dict__.get('_update_hold') is not None and self._update_hold.is_set():raise ValueError('An update is stopping the work')
        if self.cleanup.current or self.cleanup.thread and self.cleanup.thread.is_alive():raise ValueError('Wait for source cleanup to finish')

    RECOVERY_CLOSING='Books Arranger is closing. Delete the recovery copies after it restarts.'
    RECOVERY_UPDATING='An update is installing. Delete the recovery copies after Books Arranger restarts.'

    def _recovery_closed(self):
        """The real refusals of Delete recovery copies (ruling 35 keeps them): closing and an update. Else None."""
        stop=self.__dict__.get('_retention_stop')
        if stop is not None and stop.is_set():return self.RECOVERY_CLOSING
        if self.__dict__.get('_update_hold') is not None and self._update_hold.is_set():return self.RECOVERY_UPDATING
        return None

    def _recovery_waits(self):
        """What a Delete recovery copies press waits for (ruling 35: queued, made when it ends): 'scan', 'cleanup' (a source
        cleanup removing originals now), else None. Read only."""
        if self.inventory.worker and self.inventory.worker.is_alive():return 'scan'
        if self.cleanup.current or self.cleanup.thread and self.cleanup.thread.is_alive():return 'cleanup'
        return None

    def _manual_queue(self):
        return self.__dict__.setdefault('_manual_presses',[])

    def recovery_status(self,job_id):
        value=self.recovery.status(job_id)
        reason=self._recovery_idle_reason()
        if reason is not None:value=value|{'eligible':False,'reason':reason}
        else:
            waits=self._recovery_waits()
            if waits:value=value|{'waits':waits}  # Delete recovery copies is still offered: it is queued behind it
        with _MANUAL_LOCK:queued=[item[0] for item in self._manual_queue()]
        if job_id in queued:value=value|{'queued':True,'waits':value.get('waits') or ('deletion' if queued.index(job_id) else 'start')}
        return value

    def _recovery_idle_reason(self,max_age=1.0):
        """Display only: one check shared by every book's recovery status for a second (a page asks once per book):
        the real refusals only (closing, an update). A scan or a source cleanup no longer makes the copies ineligible:
        a deletion pressed then is queued (ruling 35)."""
        cached=self.__dict__.get('_idle_cache');now=time.monotonic()
        if cached and 0<=now-cached[0]<max_age:return cached[1]
        reason=self._recovery_closed()
        self._idle_cache=(now,reason);return reason

    @operation
    def delete_recovery(self,job_id,token,count,bytes):
        """Delete recovery copies (the panel's press, after its confirm). Ruling 35 (Sergei 2026-10-26): while a scan or a
        source cleanup runs, or another book's deletion waits, the press is kept in order and the retention worker makes
        it when they end, every check again then; {'started', 'queued', 'waits', 'job_id'}. The same book pressed again
        answers its place. Closing, an update and copies that changed are refused; nothing is deleted then."""
        closed=self._recovery_closed()
        if closed:raise ValueError(closed)
        with _MANUAL_LOCK:
            queue=self._manual_queue()
            place=next((n for n,item in enumerate(queue) if item[0]==job_id),None)
        if place is not None:return {'started':False,'queued':True,'job_id':job_id,'waits':self._recovery_waits() or ('deletion' if place else 'start')}
        status=self.recovery.status(job_id)
        if not status['eligible']:raise ValueError(status['reason'] or 'No eligible recovery copies remain')
        confirmation={'token':token,'count':count,'bytes':bytes}
        if any(status[k]!=confirmation[k] for k in confirmation):raise ValueError('Recovery copies changed. Review the updated details and try again.')
        waits=self._recovery_waits()
        with _MANUAL_LOCK:
            queue.append((job_id,confirmation))
            ahead=len(queue)>1 or self.__dict__.get('_manual_recovery') is not None
        self._retention_wake.set();self.invalidate_status()
        if waits or ahead:return {'started':False,'queued':True,'job_id':job_id,'waits':waits or 'deletion'}
        return {'started':True,'job_id':job_id}

    def cancel_recovery(self,job_id):
        """Take a queued Delete recovery copies back: {'cancelled': True}, or None once it has started (or never was)."""
        with _MANUAL_LOCK:
            queue=self._manual_queue()
            for n,item in enumerate(queue):
                if item[0]==job_id:
                    del queue[n];break
            else:return None
        self.invalidate_status()
        return {'cancelled':True}

    def _claim_manual(self,manual):
        """The retention worker starts a queued deletion: True unless it was cancelled meanwhile."""
        with _MANUAL_LOCK:
            queue=self._manual_queue()
            if manual not in queue:return False
            queue.remove(manual);self._manual_recovery=manual
            return True

    def start_published_check(self):
        """After construction: re-verify published audiobooks off the startup path (AudioJobs._recover). The existing-data
        pass of ruling 71d starts beside it (regroup_partial_jobs)."""
        self.jobs.start_published_check()
        def regroup():
            try:self.regroup_partial_jobs()
            except Exception:pass  # each job stays as it was; the claim check still sets a pending one aside before it runs
        threading.Thread(target=regroup,name='books-folder-regroup',daemon=True).start()

    def start_retention(self,admission):
        from recovery_retention import kept_reason
        if self._retention_thread:return
        def work():
            while not self._retention_stop.is_set():
                # Snapshot the existing admitted intent before any slow work/admission wait.
                cleanup_generation=self.__dict__.get('_automatic_cleanup_generation',0)
                published_revisits=[]
                # This distinct unpublished-working operation holds only its
                # relevant job/native leases. No central operation/admission lock
                # spans its hashing; foreground start preempts it between blocks.
                try:self.working.reconcile(limit=1,storage=self.storage_cleanup)
                except (InterruptedError,ValueError):pass
                try:
                    with admission():
                        self._recovery_idle()
                        # Ruling 35: the queued Delete recovery copies presses, first in first out, one per pass.
                        with _MANUAL_LOCK:manual=next(iter(self._manual_queue()),None)
                        selected=[manual[0]] if manual else [id for id in self.recovery.due() if id not in self._purge_tried]
                        for id in selected:
                            # One set at a time under the operation lock, so controls interleave between sets.
                            with self.operation_lock,_PURGE_LOCK:
                                self._recovery_idle()
                                if manual and not self._claim_manual(manual):break  # taken back meanwhile: nothing deleted
                                self._post_current=(id,'temporary')
                                try:
                                    self.recovery.purge(id,'manual' if manual else 'automatic',manual[1] if manual else None)
                                    published_revisits.append(id)
                                except InterruptedError:pass # Keep the durable partial purge resumable at startup.
                                except Exception as error:
                                    # Kept and flagged (missing or unverified output, changed copy); tried once per run.
                                    self._purge_tried.add(id);self.recovery._set(id,'needs_attention',kept_reason(error))
                                finally:self._post_current=None
                        if manual:self._manual_recovery=None
                        self._purge_replacement_recoveries()
                        self._finish_held_cleanups(cleanup_generation)
                        self._finish_temporary_cleanups()
                except ValueError:pass # Busy/closing admission defers; never purges while scanning.
                for id in published_revisits:
                    try:self.working.schedule_published(id)
                    except (InterruptedError,ValueError,OSError):pass
                # A queued deletion is looked at again every 2 s, so it runs right after the scan or cleanup it waited for.
                self._retention_wake.wait(2 if self._manual_queue() else 60);self._retention_wake.clear()
        self._purge_tried=set()
        self._retention_thread=threading.Thread(target=work,name='books-recovery-retention',daemon=False);self._retention_thread.start()
        for name in ('series_backfill','gap_fill'):
            background=self.__dict__.get(name)
            if background is not None:background.start()

    def _purge_recovery_now(self,job_id):
        """Right after a book's source cleanup: its recovery copies go at once (the purge verifies the output in
        full first; anything else keeps them, flagged). Runs on the converter thread between books."""
        from recovery_retention import kept_reason
        try:
            self.recovery.sync()
            if not self.recovery._rows("SELECT 1 FROM recovery_retention WHERE job_id=? AND state IN ('retained','deleting','needs_attention')",(job_id,)):return
            if self.recovery.kept(job_id):return  # Keep files: kept until Sergei acts again
            self._post_current=(job_id,'temporary')
            with _PURGE_LOCK:self.recovery.purge(job_id,'automatic')
        except InterruptedError:pass  # resumed by the next sweep
        except Exception as error:
            try:self.recovery._set(job_id,'needs_attention',kept_reason(error))  # keeps the Audiobook missing/not verified prefix
            except Exception:pass
        finally:self._post_current=None

    def _purge_replacement_recoveries(self):
        """Recovery copies of retired former outputs, once the replacement is verified (same rule)."""
        if not hasattr(self,'replacements'):return
        relations=[relation for relation in self.replacements.rows() if relation['state']=='completed' and relation['id'] not in self._purge_tried]
        try:kept=self._kept_by_choice([relation['replacement_job_id'] for relation in relations]) if relations else set()
        except (sqlite3.Error,AttributeError):return  # the Keep files record is unreadable: nothing is purged this pass
        for relation in relations:
            if relation['replacement_job_id'] in kept:continue  # Keep files: kept until Sergei acts again
            try:
                with self.operation_lock:self.retirement.purge_recoveries(relation)
            except InterruptedError:return
            except Exception:self._purge_tried.add(relation['id'])  # kept; the relation's records say why

    HELD_FOR_METADATA=('Download marker native identity differs','Unknown download marker contents preserved')

    def _finish_held_cleanups(self,generation=None):
        """Only an existing admitted Start intent can authorize this automatic held-cleanup sweep."""
        if generation is None:generation=self.__dict__.get('_automatic_cleanup_generation',0)
        allow=lambda:self._start_allowed(generation) and generation==self.__dict__.get('_automatic_cleanup_generation',0)
        if self.jobs._thread and self.jobs._thread.is_alive() or self.cleanup.thread and self.cleanup.thread.is_alive():return
        if not allow():
            self._settle_folder_jobs();return
        rows=[row for row in self.cleanup._rows("SELECT id,job_id,reason FROM source_cleanup WHERE state='needs_attention'") if row['reason'] in self.HELD_FOR_METADATA and row['id'] not in self._purge_tried]
        try:kept=self._kept_by_choice([row['job_id'] for row in rows]) if rows else set()
        except (sqlite3.Error,AttributeError):kept=None
        held=[] if kept is None else [row['id'] for row in rows if row['job_id'] not in kept]
        if held:
            try:started=self.cleanup.resume(held,follow_audio=False,admission_check=allow,admission_token=generation)
            except StartRefused:started=None
            if started and started.get('state')=='started':self._purge_tried.update(held)
        self._settle_folder_jobs()

    def _finish_temporary_cleanups(self):
        """A finished book whose temporary-file cleanup has no record, or stopped before it started or on a busy
        catalog, gets it here between sweeps, once per run (v0.16.11, "Storm of the Century": the step after its
        source cleanup ended without a record, and nothing tried again while the queue kept running). The same
        cleanup as after a book (_prune_completed, without the recovery purge the sweep does itself); a failure
        is recorded with its reason."""
        storage=getattr(self,'storage_cleanup',None)
        if storage is None or not hasattr(storage,'status'):return
        stored={row['job_id']:row for row in storage.status()}
        posting=self.__dict__.get('_post_jobs',set())
        for row in self.jobs._rows("SELECT job_id FROM audio_jobs WHERE state='completed' ORDER BY updated,job_id"):
            job_id=row['job_id'];prior=stored.get(job_id)
            if prior and not (prior['state']=='needs_attention' and (prior['output_hash']=='' or catalog_busy_text(prior['reason']))):continue
            if job_id in posting or ('temporary',job_id) in self._purge_tried:continue
            receipt=self.cleanup.status(job_id)
            if receipt and receipt['state']!='completed':continue  # its source cleanup comes first
            self._purge_tried.add(('temporary',job_id))
            try:
                with self.operation_lock:self._prune_completed(job_id,stop=_Flag(lambda:self._retention_stop.is_set()))
            except InterruptedError:return
            except Exception as error:storage._diagnose(job_id,'',error)

    FOLDER_ALREADY_GONE='Source-folder ancestor is missing without verified removal intent'

    def _settle_folder_jobs(self):
        """Empty source folders are housekeeping, not backups: none holds anything (Sergei, 2026-10-18).
        A folder job that stopped on a busy catalog runs again; one whose folder is already gone is complete."""
        storage=getattr(self,'storage_cleanup',None)
        if storage is None or not hasattr(storage,'folder_status'):return
        for row in storage.folder_status():
            if row['state']!='needs_attention' or ('folder',row['job_id']) in self._purge_tried:continue
            self._purge_tried.add(('folder',row['job_id']))
            if row['reason']==self.FOLDER_ALREADY_GONE:storage._folder_set(row['job_id'],row['output_hash'],'completed','Source folder was already gone')
            elif catalog_busy_text(row['reason']):
                try:
                    with self.operation_lock:storage.run_folders(row['job_id'])
                except Exception:pass  # stays as housekeeping; it holds nothing

    def _prune_working(self,job_id):
        output_hash=''
        try:
            if not self.storage_cleanup.working_pending(job_id):return
            self._post_current=(job_id,'temporary')
            self.storage_cleanup._phase='verify published working receipts'
            with connect(self.inventory.database) as db:
                row=db.execute('SELECT output FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()
            output_hash=json.loads(row['output'])['sha256']
            self.storage_cleanup.working_files(job_id)
        except Exception as error:
            self.storage_cleanup._diagnose(job_id,output_hash,error)
        finally:self._post_current=None

    def _prune_completed(self,job_id,source_completed=False,stop=None):
        if source_completed:self.working.schedule_published(job_id)
        if hasattr(self,'replacements'):
            relation=self.replacements.get(parent=job_id)
            if relation and relation['state'] in {'retiring','completed'}:
                with connect(self.inventory.database) as db:parent=self.replacements.raw_job(db,job_id)
                if self.retirement.historical_retired(parent,stop=stop):return
        self._prune_working(job_id)
        self.recovery.sync()
        # Between books (not during Start's re-check of every finished book, which the sweep covers).
        if stop is None and (source_completed or (self.cleanup.status(job_id) or {}).get('state')=='completed'):self._purge_recovery_now(job_id)
        receipt=self.cleanup.status(job_id)
        if receipt and receipt['state']!='completed':return
        prior=next((r for r in self.storage_cleanup.status() if r['job_id']==job_id),None)
        self._post_current=(job_id,'temporary')
        try:
            if not prior or prior['state']!='completed':self.storage_cleanup.run(job_id)
            self.storage_cleanup.run_folders(job_id,progress=lambda phase:setattr(self,'_post_current',(job_id,phase)))
        except Exception:
            # Durable audio success remains independent; cleanup errors stay visible.
            pass
        finally:self._post_current=None

    def _after_completed(self,job_id):
        # The book's own post-processing: the retention sweep leaves it alone meanwhile (_finish_temporary_cleanups).
        posting=self.__dict__.setdefault('_post_jobs',set());posting.add(job_id)
        try:self._after_completed_work(job_id)
        finally:posting.discard(job_id)
        # Rulings 69 and 71h: a book whose chosen folder it was not converted into (outside Sorted, chosen while it ran)
        # is moved there now, after its sources were handled; never converted again.
        try:self._move_to_chosen(job_id)
        except Exception:pass  # the book stays where it was published; its row offers Choose folder again

    def _after_completed_work(self,job_id):
        # Durable audio success already exists. Cleanup failure must not reset it.
        row=next(j for j in self.jobs.status()['jobs'] if j['job_id']==job_id)
        self._prune_working(job_id)  # Publication is sufficient; retirement is independent.
        try:self.working.discharge_published(job_id,self.storage_cleanup,revisit=True)
        except (OSError,ValueError):pass  # Exact held reason stays in the working ledger.
        # A boot-proved recovery child cleans up once its lease on the old files ends (_finish_recovery_child).
        if (row['manifest'].get('retry_intent') or {}).get('retained_disposal') is True:return
        if row['manifest'].get('cleanup_policy',{}).get('enabled'):
            try:
                enrolled=self.enroll_cleanup(job_id);id=enrolled['cleanup_id'];self.cleanup.current=id
                self.cleanup.run_with_retry(id)
            except Exception as error:
                # A busy catalog pauses the cleanup (the next Start or Resume continues it); anything else needs attention.
                if 'id' in locals():self.cleanup.hold(id,error)
                else:self._enrollment_attention(row,error)
            finally:self.cleanup.current=None
        try:self._prune_completed(job_id)
        except InterruptedError:raise
        except Exception as error:
            # v0.16.11 ("Storm of the Century"): an error here used to vanish in the worker, leaving no temporary
            # cleanup record, so the book read "pending" with no reason. It is recorded with its reason now,
            # and the retention sweep tries the cleanup again.
            self.storage_cleanup._diagnose(job_id,'',error)
        if hasattr(self,'replacements') and self.replacements.get(new_job=job_id):self._finish_replacement(job_id)

    def _replacement_guard(self,relation,historical=False):
        return self.replacements.structural_guard(relation,historical=historical,queued=True)

    def _pending_replacement_postprocessing(self):
        pending=[]
        with connect(self.inventory.database) as db:
            for relation in self.replacements.rows():
                failure=json.loads(relation['failure_json'] or '{}')
                if failure and failure.get('type')!='InterruptedError':continue
                row=self.replacements.raw_job(db,relation['replacement_job_id'])
                if row['state']=='completed' and relation['state'] in {'queued','published','retiring'}:pending.append(row['job_id'])
        return pending

    def _finish_replacement(self,job_id):
        relation=self.replacements.get(new_job=job_id)
        if not relation or relation['state']=='completed':return
        try:
            self._post_current=(job_id,'verifying replacement')
            self._prune_completed(job_id)
            if self.jobs._stop.is_set():raise InterruptedError('Replacement postprocessing paused')
            if relation['state']=='queued':
                with connect(self.inventory.database) as db:
                    row=self.replacements.raw_job(db,job_id)
                    stored=db.execute('SELECT * FROM storage_cleanup_jobs WHERE job_id=?',(job_id,)).fetchone()
                    if not stored or stored['state']!='completed':raise ValueError('Replacement staging cleanup must finish before current publication')
                    storage=dict(stored)
                output=json.loads(row['output'])
                effective,envelope=self.publication_bindings.current(output,'replacement')
                with DirectoryBoundary(effective['root'],ordinary(effective['final_path']).parent),VerifiedFile(effective['final_path']) as file:
                    if effective.get('identity') is not None and file.facts()['identity']!=effective['identity']:raise ValueError('Replacement effective native identity changed')
                    if not self._output_valid(output):raise ValueError('New replacement output changed')
                    relation=self.replacements.publish(relation,row,output,storage,True,location=envelope,location_guard=self.publication_bindings.guard)
            self._post_current=(job_id,'retiring former outputs')
            self.retirement.run(relation)
        except Exception as error:
            fresh=self.replacements.get(new_job=job_id)
            if fresh and not fresh['failure_json']:
                try:self.replacements.failure(fresh,error,'replacement postprocessing')
                except Exception:pass # The original exception remains authoritative to the caller.
            raise
        finally:self._post_current=None

    @operation
    def replace_audiobook(self,library,identity,revision,parent_job_id):
        """Exact approved Eye of God replacement; no arbitrary output or source paths."""
        if library!='Audiobooks' or parent_job_id!='9e04e700-ecf8-4807-8195-01a7a1d73bd6':raise ValueError('No approved replacement for this book')
        from replacement_media import prepare_replacement
        plan_path=Path(__file__).with_name('replacement_eye_plan.json')
        data=plan_path.read_bytes()
        if hashlib.sha256(data).hexdigest()!='db493dbbfa691e1fe6b875a3edacb8ebd318d487c80c9fa4de66639afa35d20f':raise ValueError('Approved replacement media plan changed')
        plan=json.loads(data)
        with self.reviews.lock,self.inventory.group_lock,contextlib.ExitStack() as location_stack:
            self._no_scan()
            existing=self.replacements.get(candidate=identity)
            if existing:
                if existing['parent_job_id']!=parent_job_id or existing['candidate_revision']!=revision:raise ValueError('Replacement identity differs')
                return {'job_id':existing['replacement_job_id'],'replacement_id':existing['id'],'state':existing['state'],'already_enrolled':True}
            with connect(self.inventory.database) as db:
                raw=self.replacements.raw_job(db,parent_job_id)
                parent={'job_id':parent_job_id,'state':raw['state'],'manifest':json.loads(raw['manifest']),'output':json.loads(raw['output'] or '{}')}
                group=dict(db.execute('SELECT * FROM book_groups WHERE id=?',(identity,)).fetchone() or {})
                context=dict(db.execute('SELECT * FROM candidate_context WHERE id=?',(identity,)).fetchone() or {})
            if parent['manifest']['candidate_id']!=identity or parent['manifest']['candidate_revision']!=revision or group.get('revision')!=revision or context.get('revision')!=revision:raise ValueError('Replacement candidate revision changed')
            effective,envelope=self.publication_bindings.current(parent['output'],'base',parent)
            new_id=str(uuid.uuid4());publication_id=str(uuid.uuid4());manifest=prepare_replacement(parent,new_id,plan,**({'effective_output':effective,'location_envelope':envelope} if envelope is not None else {}));manifest['replacement_id']=publication_id
            root=ordinary(manifest.get('output_root',manifest['root']));destination=ordinary(manifest['destination'])
            with DirectoryBoundary(root,destination.parent):
                if destination.exists():raise ValueError('Distinct final audiobook already exists; nothing will be overwritten')
            repairs=self.publications._repairs(parent)
            if len(repairs)!=2 or len([r for r in repairs if r['corrected']])!=1:raise ValueError('Both approved chapter-repair receipts are required')
            paths=[{'record':parent['output'],'id':parent_job_id,'journal':None}]+repairs
            old=[];former_locations={}
            for publication in paths:
                original=publication['record'];kind='base' if publication['journal'] is None else 'Chaptersv2' if publication['corrected'] else 'Chapters'
                record,envelope=self.publication_bindings.current(original,kind,parent,repair_journal_sha256=publication.get('journal_sha256'))
                path=ordinary(record['final_path']);record_root=ordinary(record['root'])
                boundary=location_stack.enter_context(DirectoryBoundary(record_root,path.parent));file=location_stack.enter_context(VerifiedFile(path))
                if file.facts()['links']!=1 or file.facts()['size']!=record['size'] or file.sha256()!=record['sha256'] or (record.get('identity') is not None and file.facts()['identity']!=record['identity']) or [list(v) for v in boundary.identities]!=[list(v) for v in record['parent_identity']]:raise ValueError('Former audiobook identity or full content changed')
                if publication['journal'] is not None:
                    jp=ordinary(publication['journal']);jb=location_stack.enter_context(DirectoryBoundary(self.publications.repairs,jp.parent));jf=location_stack.enter_context(VerifiedFile(jp))
                    if jf.facts()!=publication['journal_facts'] or jb.identities!=publication['journal_ancestry'] or jf.sha256()!=publication['journal_sha256']:raise ValueError('Former chapter receipt changed during approval')
                old.append({'path':original['final_path'],'size':original['size'],'sha256':original['sha256'],'facts':file.facts(),'ancestry':original['parent_identity'],'publication_id':publication['id'],'journal_sha256':publication.get('journal_sha256')})
                former_locations[original['final_path']]={'original':copy.deepcopy(original),'effective':record,'envelope':envelope,'kind':kind,'journal_sha256':publication.get('journal_sha256')}
            corrected=next(r for r in repairs if r['corrected'])
            previous={'id':corrected['id'],'path':corrected['record']['final_path'],'sha256':corrected['record']['sha256'],'journal_sha256':corrected['journal_sha256']}
            approval={'group_row':group,'context_row':context,'destination':manifest['destination'],'profile':manifest['profile'],'sources':manifest['sources'],
                      'old_outputs':old,'former_locations':former_locations,'parent_output':parent['output']['final_path'],'source_policy':'KEEP_ALL_40_ORIGINALS','media_plan_sha256':hashlib.sha256(data).hexdigest(),'replacement_manifest':copy.deepcopy(manifest)}
            binding={'id':publication_id,'parent_row':raw,'previous_publication':previous,'approval':approval,'timestamp':replacement_now(),'location_guard':self.publication_bindings.guard}
            job=self.jobs.enqueue(manifest,replacement_context=(self.replacements,binding))
        self.resume()
        return {'job_id':job,'replacement_id':publication_id,'queued':True}

    def candidate_status(self, identity):
        jobs = [j for j in self.jobs.status()['jobs'] if j['manifest']['candidate_id'] == identity]
        if not jobs: return None
        job = jobs[-1]
        state = {'pending':'Queued','running':'Creating','completed':'Audiobook created','needs attention':'Output needs attention'}[job['state']]
        from review_backend import job_destination
        value={'job_id':job['job_id'],'state':state,'stage':job['stage'],'reason':job['reason'],'cleanup':self.cleanup.status(job['job_id']),'cleanup_policy':job['manifest'].get('cleanup_policy',{'enabled':False}),
               'destination':job_destination(job['manifest'])}
        if isinstance(job['manifest'].get('retry_intent'),dict):value['retry_parent_job_id']=job['manifest']['retry_intent'].get('parent_job_id')
        if job['state']=='needs attention':
            attention=self.attention_summary([job['job_id']]).get(job['job_id'])
            if attention:
                if 'retry' in attention:value['retry']=attention.pop('retry')
                if 'repair' in attention:value['repair']=attention.pop('repair')
                attention.pop('readmission',None)  # carried at the top level below, for every state
                value['attention']=attention
        import m4b_readmission
        with self.jobs._db() as db:readmission=m4b_readmission.describe(db,job['job_id'])
        if readmission:value['readmission']=readmission  # queued_next + position, or the refusal reason
        repaired=repair_record(job)
        if repaired:value['repaired']=repaired
        if job['state']=='completed':
            kept=self.kept_files([job['job_id']]).get(job['job_id'])
            if kept:
                value['attention']={key:item for key,item in kept.items() if key!='keep'};value['keep']=kept['keep']
            elif job['job_id'] in self.kept_by_choice([job['job_id']]):value['kept']=True
        return value

    def retry_statuses(self,job_id=None):
        """Retry data for audiobook jobs a Retry can resolve; the UI reads creation.job.retry."""
        working=getattr(self,'working',None)
        if working is None:return {}
        return self.jobs.retry_statuses(working.admission_clear,job_id,self._space_ready)

    def attention_summary(self,job_ids=None,retry=True):
        """Group, cause and Retry data per job that needs attention (audio_jobs.attention_summary).

        'repair_check' is the internal trigger for the background check and never leaves this method; the typed
        'precheck' state does (RefusedRetry follow-up, finding F2). A current working-files refusal carries the
        job's absolute working folder for the Technical detail line only (point 3c)."""
        clear=getattr(getattr(self,'working',None),'admission_clear',None)
        if not hasattr(self.jobs,'attention_summary'):return {}
        if getattr(getattr(self,'inventory',None),'database',None):self._load_repair_checks()
        summary=self.jobs.attention_summary(clear,self._space_ready,job_ids,retry and clear is not None)
        unchecked=[job_id for job_id,item in summary.items() if item.pop('repair_check',False)]
        if unchecked:self._check_repairs(unchecked)
        self._startover_facts(summary)
        stage=getattr(self,'stage_root',None)
        for job_id,item in summary.items():
            refusal=item.get('readmission')
            if stage is not None and (isinstance(item.get('working'),dict) or isinstance(refusal,dict) and refusal.get('state')=='refused' and refusal.get('cause')=='working_files' and refusal.get('stale') is not True):
                item['working_folder']=os.path.abspath(stage/job_id)  # Technical detail only
        recovery=getattr(self,'producer_recovery',None)
        if recovery:
            for job_id,item in summary.items():
                if isinstance(item.get('working'),dict) and item['working'].get('state')=='blocked':
                    item['producer_recovery']=recovery.status(job_id)
                    if item['producer_recovery']['can_retry']:item['retry']={'allowed':True,'reason':''};item['group']='retry'  # one predicate: an enabled Retry the bulk path accepts
        # A drive that comes back (cause 'unreachable', 0.22.1) is no catalog commit either: its Retry shows within WORKING_MAX_AGE.
        if job_ids is None:self._working_listed=any(isinstance(item.get('working'),dict) or item.get('cause')=='unreachable' for item in summary.values())
        for job_id,item in self.kept_files(job_ids).items():
            if job_id not in summary:summary[job_id]=item if retry else {key:value for key,value in item.items() if key!='keep'}
        return summary

    def _startover_facts(self,summary):
        """A current source_changed refusal (fix 'review') offers Start over (RefusedRetry follow-ups 2-4): 'startover'
        is what automatic processing will do with the book once the job is set aside, 'automatic' or 'manual_draft' (it
        holds a book with a saved review), the same read-only test the pass runs; 'release_ok' is true when the combined
        "Start over and let the app handle it" applies (one included .m4b, a saved review, no editing lease now)."""
        wanted=[job_id for job_id,item in summary.items() if isinstance(item.get('readmission'),dict) and item['readmission'].get('state')=='refused'
                and item['readmission'].get('cause')=='source_changed' and item['readmission'].get('stale') is not True]
        database=getattr(getattr(self,'inventory',None),'database',None)
        if not wanted or not database:return
        import book_restart
        try:
            with connect(database) as db:
                for job_id in wanted:
                    found=db.execute("SELECT json_extract(manifest,'$.candidate_id') FROM audio_jobs WHERE job_id=?",(job_id,)).fetchone()
                    facts=book_restart.book(db,found[0]) if found else None
                    summary[job_id]['startover']='manual_draft' if facts and facts['manual_draft'] else 'automatic'
                    summary[job_id]['release_ok']=book_restart.release_ok(facts)
        except (sqlite3.Error,ValueError):
            for job_id in wanted:summary[job_id].setdefault('startover','automatic');summary[job_id].setdefault('release_ok',False)

    # S5 (ruling 35's refusal texts): each cause says itself. Closing is the real refusal; a catalog still busy after the
    # transaction's 30 s of retries is no refusal for Sergei: the page holds the press and sends it again (cause 'busy').
    STARTOVER_REFUSED='Books Arranger is closing. Start over after it restarts.'  # Judy 14.6
    STARTOVER_NOTHING=STARTOVER_REFUSED
    STARTOVER_BUSY='Start over queued. It runs when the app is free.'
    EDITING='This book is being edited. Finish editing, then try again.'
    RELEASE_BUSY='Let the app handle it queued. It runs when the app is free.'
    RELEASE_REFUSED='Books Arranger is closing. Let the app handle it after it restarts.'

    def _restart_locks(self):
        """The review and grouping locks every review write takes (a save, the automatic approval)."""
        stack=contextlib.ExitStack()
        for lock in (getattr(getattr(self,'reviews',None),'lock',None),getattr(getattr(self,'inventory',None),'group_lock',None)):
            if lock is not None:stack.enter_context(lock)
        return stack

    def start_over(self,library,identity,revision,job_id,discard_review=False,server_closing=False):
        """Start over (Sergei, 2026-10-19): set a stuck job aside and send the book back to automatic processing, which
        is started if it is not running (O9; a blocker that clears by itself leaves a pending start, O12).

        Set aside only the book's newest job that needs attention, has no output and no publication intent, with a
        current source_changed refusal, on the book revision as read: a compare-and-set on the whole job row and the
        book's revision in one transaction. The job row, its journal and its working files are kept. discard_review
        (O13, "Start over and let the app handle it") also discards the saved review in the same transaction: all or
        nothing. RetryRefused (typed cause) means nothing changed."""
        self._reacquire_admission(identity=identity)
        import book_restart,m4b_readmission
        from audio_jobs import RetryRefused,RETRY_BOOK_CHANGED,CURRENT
        from sqlite_retry import transaction
        if library!='Audiobooks':raise ValueError('Audiobook operations apply only to Audiobooks')
        refused=self.STARTOVER_NOTHING if discard_review else self.STARTOVER_REFUSED
        if self.draining:raise RetryRefused(refused,'closing')
        entry=self.attention_summary([job_id]).get(job_id)
        if not entry or entry.get('startover') not in ('automatic','manual_draft'):raise RetryRefused(RETRY_BOOK_CHANGED,'changed')
        rows=self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))
        if not rows or json.loads(rows[0]['manifest']).get('candidate_id')!=identity:raise RetryRefused(RETRY_BOOK_CHANGED,'changed')
        row=rows[0]
        def write(db):
            import reacquire_sources
            reacquire_sources.require_admission(db,identity)
            book_restart.ensure(db)
            current=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()
            if not current or dict(current)!=row or row['state']!='needs attention' or row['output'] or 'publication_intent' in json.loads(row['journal']):
                raise book_restart.Changed('Job changed')
            if book_restart.current_job(db,identity)!=job_id:raise book_restart.Changed('Newer work')
            refusal=m4b_readmission.describe(db,job_id)
            if not refusal or refusal.get('state')!='refused' or refusal.get('cause')!='source_changed' or refusal.get('stale') is True:
                raise book_restart.Changed('Refusal changed')
            facts=book_restart.book(db,identity)
            if not facts or facts['revision']!=revision:raise book_restart.Changed('Book changed')
            current_revision=revision
            if discard_review:
                if facts['lease']:raise book_restart.Editing('Editing')
                if not book_restart.release_ok(facts):raise book_restart.Changed('Release not allowed')
                current_revision=book_restart.discard_review(db,facts)
            book_restart.set_aside(db,job_id,identity,revision)
            book_restart.reset_automatic(db,identity,current_revision,facts['fingerprint'])
            book_restart.mark(db,identity,'start_over',job_id)
        try:
            with self._restart_locks():transaction(self.inventory.database,write)
        except book_restart.Editing:raise RetryRefused(self.EDITING,'editing') from None
        except book_restart.Changed:raise RetryRefused(RETRY_BOOK_CHANGED,'changed') from None
        except sqlite3.Error:raise RetryRefused(self.STARTOVER_BUSY,'busy') from None
        return self._after_restart(identity,server_closing)|{'set_aside':True,'released':bool(discard_review),'job_id':job_id}

    def _after_restart(self,identity,server_closing=False):
        """Put the book back on the pass and start it; the answer carries the outcome and the refreshed row."""
        import book_restart
        automatic=getattr(self,'automatic',None)
        visit=automatic.requeue(identity) if automatic is not None and hasattr(automatic,'requeue') else 'this_run'
        started=automatic.request_start(server_closing=server_closing) if automatic is not None and hasattr(automatic,'request_start') else None
        run=automatic._run_row() if automatic is not None and hasattr(automatic,'_run_row') else None
        try:
            with connect(self.inventory.database) as db:
                book_restart.set_visit(db,identity,visit,run['id'] if run else None)
                facts=book_restart.book(db,identity)
        except sqlite3.Error:facts=None
        self.invalidate_status()
        answer={'outcome':'manual_draft' if facts and facts['manual_draft'] else 'automatic','row':self.restart_row(identity)}
        if started is not None:answer['pass']=dict(started,visit=visit)
        return answer

    def release(self,library,identity,revision,server_closing=False):
        """"Let the app handle it" (O7, option A): discard a held single-M4B book's saved review (hand edits included) and
        its context and any editing lease, reset its automatic record, put it back on the pass and start the pass. Its
        sources and any older job are kept. RetryRefused with cause 'changed', 'editing' or 'busy' changes nothing."""
        self._reacquire_admission(identity=identity)
        if library!='Audiobooks':raise ValueError('Audiobook operations apply only to Audiobooks')
        self._release_one(identity,revision)
        return self._after_restart(identity,server_closing)|{'released':True}

    def _release_one(self,identity,revision):
        import book_restart
        from audio_jobs import RetryRefused,RETRY_BOOK_CHANGED
        from sqlite_retry import transaction
        if self.draining:raise RetryRefused(self.RELEASE_REFUSED,'closing')
        def write(db):
            import reacquire_sources
            reacquire_sources.require_admission(db,identity)
            facts=book_restart.book(db,identity)
            if not facts or facts['revision']!=revision:raise book_restart.Changed('Book changed')
            if facts['lease']:raise book_restart.Editing('Editing')
            if book_restart.current_job(db,identity) is not None:raise book_restart.Changed('Book has a job')
            held=db.execute("SELECT result FROM automatic_candidates WHERE id=? AND revision=? AND fingerprint=? AND state='Held'",
                            (identity,facts['revision'],facts['fingerprint'])).fetchone() if book_restart._table(db,'automatic_candidates') else None
            try:reasons=json.loads(held[0]).get('reasons') or [] if held else []
            except (TypeError,ValueError,AttributeError):reasons=[]
            if book_restart.MANUAL_DRAFT not in reasons or not book_restart.release_ok(facts):raise book_restart.Changed('Not held for a saved review')
            current_revision=book_restart.discard_review(db,facts)
            book_restart.reset_automatic(db,identity,current_revision,facts['fingerprint'])
            book_restart.mark(db,identity,'release')
        try:
            with self._restart_locks():transaction(self.inventory.database,write)
        except book_restart.Editing:raise RetryRefused(self.EDITING,'editing') from None
        except book_restart.Changed:raise RetryRefused(RETRY_BOOK_CHANGED,'changed') from None
        except sqlite3.Error:raise RetryRefused(self.RELEASE_BUSY,'busy') from None

    def release_selected(self,library,items,server_closing=False):
        """"Let the app handle selected" (O14): each book through its own compare-and-set (a book that changed is refused
        alone), then automatic processing is started once, after the last book. {'released', 'refused':[{id, cause}],
        'pass'}."""
        from audio_jobs import RetryRefused
        if library!='Audiobooks':raise ValueError('Audiobook operations apply only to Audiobooks')
        released,refused=[],[]
        for identity,revision in items:
            try:self._release_one(identity,revision)
            except RetryRefused as error:refused.append({'id':identity,'cause':error.cause or 'unknown'});continue
            released.append(identity)
        automatic=getattr(self,'automatic',None)
        visits={identity:automatic.requeue(identity) for identity in released} if automatic is not None else {}
        started=automatic.request_start(server_closing=server_closing) if released and automatic is not None else None
        if released:
            import book_restart
            run=automatic._run_row() if automatic is not None else None
            try:
                with connect(self.inventory.database) as db:
                    for identity,visit in visits.items():book_restart.set_visit(db,identity,visit,run['id'] if run else None)
            except sqlite3.Error:pass
            self.invalidate_status()
        answer={'released':len(released),'refused':refused}
        if started is not None:answer['pass']=dict(started,visit='next_run' if 'next_run' in visits.values() else 'this_run')
        return answer

    def restart_row(self,identity):
        """The book's refreshed list row (marker, release and job included), for a press answer; None if unavailable."""
        reviews=getattr(self,'reviews',None)
        if not hasattr(reviews,'enrich'):return None
        try:row=reviews.enrich(reviews._row('Audiobooks',identity),check_sources=False)
        except (ValueError,OSError,sqlite3.Error):return None
        self.restart_view([row])
        return row

    def restart_view(self,rows):
        """List rows (enriched candidates), in place: 'restart' (the Started over marker's state, Follow-up 3 section 2),
        'release' {'allowed'} for a book the pass holds for its saved review (section 4.2), and automatic 'hold' /
        'lease' for that hold. Read-only."""
        import book_restart
        database=getattr(getattr(self,'inventory',None),'database',None)
        if not rows or not database:return rows
        automatic=getattr(self,'automatic',None)
        run=automatic._run_row() if automatic is not None and hasattr(automatic,'_run_row') else None
        try:
            with connect(database) as db:
                marks=book_restart.markers(db)
                for row in rows:
                    auto=row.get('automatic') if isinstance(row.get('automatic'),dict) else None
                    held=bool(auto and auto.get('state')=='Held' and book_restart.MANUAL_DRAFT in (auto.get('reasons') or []))
                    marker=marks.get(row.get('id'))
                    if not held and not marker:continue
                    facts=book_restart.book(db,row['id'])
                    job=(row.get('creation') or {}).get('job')
                    if held:
                        auto['hold']='manual_draft';auto['lease']=bool(facts and facts['lease'])
                        row['release']={'allowed':bool(facts and facts['saved_review'] and facts['single_m4b'] and not facts['lease'] and not job)}
                    value=book_restart.state(marker,job.get('state') if isinstance(job,dict) else None,auto,facts,run) if marker else None
                    if value:row['restart']=value
        except sqlite3.Error:pass
        return rows

    def restart_index(self,jobs,index=None):
        """(order, counts) for the Started over filter: {book id: sort rank} for every marked book that automatic
        processing has not queued yet, and the global counts the summary line needs (waiting, working, held, failed,
        next_run, release). jobs: {book id: current job as the book list reads it}."""
        import book_restart
        counts={'waiting':0,'working':0,'held':0,'failed':0,'next_run':0,'release':0}
        database=getattr(getattr(self,'inventory',None),'database',None)
        if not database:return {},counts
        automatic=getattr(self,'automatic',None)
        index=index if index is not None else automatic.index() if automatic is not None and hasattr(automatic,'index') else {}
        run=automatic._run_row() if automatic is not None and hasattr(automatic,'_run_row') else None
        order={}
        with connect(database) as db:
            for identity,marker in book_restart.markers(db).items():
                current=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=?'+(' AND superseded=0' if 'superseded' in book_restart._columns(db,'book_groups') else ''),(identity,)).fetchone()
                if current is None:continue
                item=index.get(identity)
                auto=item if item and item.get('revision')==current[0] and item.get('fingerprint')==current[1] else None
                job=jobs.get(identity)
                value=book_restart.state(marker,job.get('state') if isinstance(job,dict) else None,auto,None,run)
                if not value or value['state']=='queued':continue
                order[identity]=book_restart.ORDER[value['state']]
                counts[value['state']]+=1
                if value.get('visit')=='next_run':counts['next_run']+=1
                if value.get('hold')=='manual_draft':
                    facts=book_restart.book(db,identity)
                    if facts and facts['saved_review'] and facts['single_m4b'] and not facts['lease']:counts['release']+=1
        return order,counts

    KEPT_CHANGED=('Original bytes differ from reviewed sources',)  # a content mismatch: keep-case (A)

    def kept_files(self,job_ids=None):
        """Completed books whose files the 0.16.8 rule keeps, as attention entries (Judy's spec section 3):
        (A) 'changed', an original's content no longer matches what was checked (its source cleanup held);
        (B) 'audiobook', the purge found the audiobook missing or not verified. A book marked kept is left
        out. Keep files is offered; Check again and Convert again are not built (they need a replace-after-
        verify flow and, for (B), the recovery copies as the only source)."""
        from recovery_retention import AUDIOBOOK_MISSING,AUDIOBOOK_UNVERIFIED,kept_by_choice
        database=getattr(getattr(self,'inventory',None),'database',None)
        if not database:return {}
        try:
            with connect(database) as db:
                kept=kept_by_choice(db)  # read-only on the status path
                found={}
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='source_cleanup'").fetchone():
                    for job_id,reason in db.execute("SELECT job_id,reason FROM source_cleanup WHERE state='needs_attention'"):
                        if reason in self.KEPT_CHANGED:found[job_id]={'group':'changed','cause':None,'reason':reason}
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='recovery_retention'").fetchone():
                    for job_id,reason in db.execute("SELECT job_id,reason FROM recovery_retention WHERE state='needs_attention'"):
                        for prefix,cause in ((AUDIOBOOK_MISSING,'missing'),(AUDIOBOOK_UNVERIFIED,'unverified')):
                            if (reason or '').startswith(prefix):found[job_id]={'group':'audiobook','cause':cause,'reason':reason[len(prefix):]}
        except sqlite3.Error:return {}
        wanted=set(job_ids) if job_ids is not None else None
        return {job_id:item|{'originals_untouched':False,'keep':{'allowed':True,'reason':''}} for job_id,item in found.items()
                if job_id not in kept and (wanted is None or job_id in wanted)}

    def kept_by_choice(self,job_ids):
        """Job ids whose files Sergei chose to keep (for the row and panel line)."""
        try:return self._kept_by_choice(job_ids)
        except (sqlite3.Error,AttributeError):return set()

    def _kept_by_choice(self,job_ids):
        """The purge guard reads it without a fallback: an unreadable catalog keeps everything."""
        from recovery_retention import kept_by_choice
        with connect(self.inventory.database) as db:return kept_by_choice(db,job_ids)

    def keep_files(self,library,identity,revision,job_id):
        """Keep files: this book's kept files stop being flagged and no automatic purge touches them again
        (recovery_retention.kept_by_choice). Nothing is deleted and no job is queued."""
        from audio_jobs import RetryRefused,RETRY_BOOK_CHANGED
        from recovery_retention import KEPT_FILES_TABLE
        if library!='Audiobooks':raise ValueError('Audiobook operations apply only to Audiobooks')
        entry=self.kept_files([job_id]).get(job_id)
        rows=self.jobs._rows('SELECT manifest FROM audio_jobs WHERE job_id=?',(job_id,))
        manifest=json.loads(rows[0]['manifest']) if rows else {}
        if not entry or manifest.get('candidate_id')!=identity:raise RetryRefused(RETRY_BOOK_CHANGED)
        with connect(self.inventory.database) as db:
            db.execute(KEPT_FILES_TABLE)
            db.execute('INSERT OR IGNORE INTO kept_files VALUES(?,?)',(job_id,time.strftime('%Y-%m-%dT%H:%M:%S+00:00',time.gmtime())))
        self.invalidate_status()
        return {'job_id':job_id,'kept':True}

    def _check_repairs(self,job_ids):
        """Classify unchecked M4B rows for Repair (m4b_repair.check), one at a time, off the request thread.

        A check reads only the source's box headers and movie box, read-only; the next status read shows
        the result. It never repairs anything: Repair runs only when the user presses it.
        """
        self._load_repair_checks()
        with _REPAIR_LOCK:
            pending=self.__dict__.setdefault('_repair_pending',[]);skipped=self.__dict__.setdefault('_repair_skipped',set())
            pending.extend(job_id for job_id in job_ids if job_id not in pending and job_id not in skipped)
            stop=self.__dict__.setdefault('_repair_stop',threading.Event())
            if not pending or self.__dict__.get('_repair_running') or stop.is_set():return
            self._repair_running=True
            self._repair_thread=threading.Thread(target=self._repair_check_work,args=(stop,),name='books-repair-check',daemon=True)
            self._repair_thread.start()

    def _load_repair_checks(self):
        """Once per app run: finished checks saved by earlier runs (m4b_repair_checks), so a launch does not
        re-parse every M4B movie box (about 3 CPU-minutes on the real catalog, which slowed every request)."""
        if self.__dict__.get('_repair_checks_loaded'):return
        self._repair_checks_loaded=True
        from audio_jobs import remember_repair_check
        try:
            with connect(self.inventory.database) as db:
                db.execute('CREATE TABLE IF NOT EXISTS m4b_repair_checks(job_id TEXT PRIMARY KEY,manifest_hash TEXT NOT NULL,module_sha256 TEXT NOT NULL,result TEXT NOT NULL,checked TEXT NOT NULL)')
                for row in db.execute('SELECT job_id,manifest_hash,module_sha256,result FROM m4b_repair_checks'):
                    result=json.loads(row['result'])
                    if isinstance(result,dict) and result.get('state') in ('intact','refused','repairable'):remember_repair_check((row['job_id'],row['manifest_hash'],row['module_sha256']),result)
        except (sqlite3.Error,ValueError,TypeError,AttributeError):pass  # display only: the checker runs again

    def _save_repair_checks(self,found):
        """One write at the end of a pass, so the pass itself never invalidates the quiet status."""
        if not found:return
        try:
            with connect(self.inventory.database) as db:
                checked=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
                db.executemany('INSERT OR REPLACE INTO m4b_repair_checks VALUES(?,?,?,?,?)',[(key[0],key[1],key[2],json.dumps(result,ensure_ascii=False),checked) for key,result in found])
        except (sqlite3.Error,TypeError,ValueError):pass

    def _repair_check_work(self,stop):
        import m4b_repair
        from audio_jobs import REPAIR_CHECKS,repair_check_key,remember_repair_check
        found=[];saved=0;refreshed=time.monotonic();finished=0
        while True:
            # Futaba's Minor 1: the Checking count and each row follow finished checks within CHECK_REFRESH seconds, one
            # status refresh per interval and only when a check finished since the last one (the pass end stays the last).
            if finished and time.monotonic()-refreshed>=CHECK_REFRESH and not stop.is_set():
                self._save_repair_checks(found[saved:]);saved=len(found);finished=0;refreshed=time.monotonic()
                self.invalidate_status()
            with _REPAIR_LOCK:
                if stop.is_set() or not self._repair_pending:
                    self._repair_running=False
                    break
                job_id=self._repair_pending.pop(0)
            try:
                rows=self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))
                key=repair_check_key(rows[0]) if rows else None
                if rows and key and key not in REPAIR_CHECKS and m4b_repair.classify(rows[0])=={'state':'unchecked'}:
                    started=time.monotonic();result=m4b_repair.check(rows[0],stop);finished+=1
                    if isinstance(result,dict) and result.get('state') in ('intact','refused','repairable') and not str(result.get('reason','')).startswith('Source unavailable'):
                        remember_repair_check(key,result);found.append((key,result))
                        with _REPAIR_LOCK:self.__dict__.setdefault('_repair_failed',{}).pop(job_id,None)
                    elif isinstance(result,dict) and result.get('unavailable') is True and not stop.is_set():
                        # Kept for this run beside m4b_repair's own cache, so the row reads "can't open" until a
                        # press or the next start, never "checking" again (RefusedRetry follow-up, finding F3a).
                        with _REPAIR_LOCK:self.__dict__.setdefault('_repair_failed',{})[job_id]=str(result.get('reason') or 'Source unavailable')
                    # The parse is pure Python: rest as long as it ran (at most 2 s), so requests keep most of the interpreter.
                    stop.wait(min(2.0,time.monotonic()-started))
            except Exception as error:
                # Stays unchecked and is never re-read in a loop; the row reads "can't open", not "checking" (finding F3b).
                with _REPAIR_LOCK:
                    self._repair_skipped.add(job_id)
                    self.__dict__.setdefault('_repair_failed',{})[job_id]=('Source check failed: '+type(error).__name__+': '+str(error))[:500]
        self._save_repair_checks(found[saved:])
        if not stop.is_set():self.invalidate_status()  # the new classes show on the next poll

    def _repair_check_failed(self,job_id):
        """The raw text of this run's repair check that could not finish for the job (an error, or a source it could not
        open), else None. Read-only; audio_jobs.precheck reads it as 'unavailable', never 'pending'."""
        with _REPAIR_LOCK:return self.__dict__.get('_repair_failed',{}).get(job_id)

    def _space_ready(self,manifest):
        """A full-disk failure can be retried once the working drive has room for a conservative bound
        (six times the source bytes plus 64 MiB; the real peak is the snapshots plus three outputs).
        The worker's own admission still checks the exact requirement before any copy."""
        try:
            needed=6*sum(int(source['size']) for source in manifest['sources'])+64*1024*1024
            return shutil.disk_usage(self.stage_root if self.stage_root.exists() else self.stage_root.parent).free>=needed
        except (KeyError,TypeError,ValueError,OSError):return False

    def retry_blocked_job(self,library,identity,revision,job_id):
        """Retry button: requeue one audiobook job whose start was refused, once that refusal has cleared.

        It requeues the same job row (audio_jobs.retry_admission_hold) and puts it next, right after the
        current book (v0.16.8: every Retry and Repair runs next). The worker's own admission and revision
        checks run again before any work, so the press itself is fast: no operation lock, no source read and
        no status computation in the reply. RetryRefused means nothing changed.
        """
        self._reacquire_admission(identity=identity)
        import failed_m4b_retry
        from audio_jobs import RetryRefused,RETRY_CLOSING,RETRY_SCANNING,RETRY_WORKER_BUSY
        if library!='Audiobooks':raise ValueError('Audiobook operations apply only to Audiobooks')
        if self.inventory.worker and self.inventory.worker.is_alive():raise RetryRefused(RETRY_SCANNING)
        if self.draining:raise RetryRefused(RETRY_CLOSING)
        repeat=self._already_accepted(job_id,identity)
        if repeat is not None:return repeat
        recovery=getattr(self,'producer_recovery',None)
        capability=recovery.status(job_id) if recovery else {}
        if capability.get('state') in {'ready','isolated_retained'}:
            if self._m4b_parent(job_id,identity,revision,lambda row:row['state']=='needs attention' and not row['output']) is None:raise ValueError('Recovery book changed')
            result=self._request_m4b_readmission(job_id,'retry');self._resume_later()
            return {'job_id':job_id,'requeued':False,**result}
        if capability.get('can_confirm_origin') is True:raise RetryRefused('No confirmation is saved for this book.','origin_unconfirmed')
        from audio_jobs import tag_repair_retry
        if self._m4b_parent(job_id,identity,revision,tag_repair_retry) is not None:
            result=self._request_m4b_readmission(job_id,'retry');self._resume_later()
            return {'job_id':job_id,'requeued':False,**result}
        import destination_admission
        with self.jobs._db() as destination_db:
            destination_raw=destination_db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()
            destination_hold=destination_admission.current(destination_db,dict(destination_raw),self._destination_policy()) if destination_raw else None
        if getattr(self.inventory,'output_root',None) or destination_hold:
            rows=self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))
            if rows:
                with self.jobs._db() as db:shape=self.jobs._retry_shape(db,rows[0])
                if shape and shape.get('candidate_id')==identity and shape.get('candidate_revision')==revision:
                    self._clear_first(job_id,'retry');self.working.admission_clear(rows[0])
                    result=self._request_m4b_readmission(job_id,'retry');self._resume_later()
                    return {'job_id':job_id,'requeued':False,**result}
        if self._m4b_parent(job_id,identity,revision,failed_m4b_retry.eligible) is not None:
            # An M4B failure this version can preserve: accepted at once, even while a book converts. The worker
            # admits it right after that book through the proof route (m4b_readmission); a refusal is per book.
            self._m4b_refusal_gate(job_id)
            self._clear_first(job_id,'retry')
            result=self._request_m4b_readmission(job_id,'retry');self._resume_later()
            return {'job_id':job_id,'requeued':False,**result}
        # v0.16.12: no review lock here. It is held while the start-of-book check re-reads a whole book, so a
        # press could wait past the page's timeout; the worker's own admission re-checks the review anyway.
        self._clear_first(job_id,'retry')
        result=self.jobs.retry_admission_hold(job_id,identity,revision,self.working.admission_clear,self._space_ready,review=False)
        queued=self._queue_next_same(job_id);self._resume_later()
        return result|queued

    def _m4b_parent(self,job_id,identity,revision,check):
        """The raw failed row when check(row) holds (M4B retry or repair eligibility), else None.

        RetryRefused(RETRY_BOOK_CHANGED) when it does hold but the book or revision on screen is not this
        job's, or the book already has newer work: nothing is admitted from an outdated view.
        """
        from audio_jobs import RetryRefused,RETRY_BOOK_CHANGED,CURRENT
        rows=self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))
        if not rows or not check(rows[0]):return None
        manifest=json.loads(rows[0]['manifest'])
        with self.jobs._db() as db:
            newest=db.execute("SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? AND "+CURRENT+" ORDER BY created DESC, job_id DESC LIMIT 1",(manifest.get('candidate_id'),)).fetchone()
        if manifest.get('candidate_id')!=identity or manifest.get('candidate_revision')!=revision or not newest or newest[0]!=job_id:
            raise RetryRefused(RETRY_BOOK_CHANGED)
        return rows[0]

    def repair_blocked_job(self,library,identity,revision,job_id):
        """Repair button: the same request rules as Retry; the request is accepted at once and the worker runs
        it right after the current book (_repair_damaged_m4b re-diagnoses the source under file holds and admits
        one child job: a compare-and-set on the failed row, one child per failed parent). The original files are
        only read. RetryRefused means nothing changed.
        """
        self._reacquire_admission(identity=identity)
        import m4b_repair
        from audio_jobs import RetryRefused,REPAIR_CLOSING,REPAIR_SCANNING,RETRY_BOOK_CHANGED
        if library!='Audiobooks':raise ValueError('Audiobook operations apply only to Audiobooks')
        if self.inventory.worker and self.inventory.worker.is_alive():raise RetryRefused(REPAIR_SCANNING)
        if self.draining:raise RetryRefused(REPAIR_CLOSING)
        repeat=self._already_accepted(job_id,identity)
        if repeat is not None:return repeat
        if self._m4b_parent(job_id,identity,revision,m4b_repair.eligible) is None:
            # A Repair job that stopped only on the revision guard (v0.16.10) runs again as itself, with the repair
            # it was admitted with (audio_jobs._retry_shape); anything else is refused, nothing changed.
            rows=self.jobs._rows('SELECT manifest FROM audio_jobs WHERE job_id=?',(job_id,))
            binding=json.loads(rows[0]['manifest']).get('m4b_repair') if rows else None
            if not isinstance(binding,dict) or binding.get('user_requested') is not True:raise RetryRefused(RETRY_BOOK_CHANGED)
            self._clear_first(job_id,'repair')
            result=self.jobs.retry_admission_hold(job_id,identity,revision,self.working.admission_clear,self._space_ready,review=False)
            queued=self._queue_next_same(job_id,'repair');self._resume_later()
            return result|queued
        self._m4b_refusal_gate(job_id,'repair')
        self._clear_first(job_id,'repair')
        result=self._request_m4b_readmission(job_id,'repair');self._resume_later()  # runs right after the current book
        return {'job_id':job_id,'requeued':False,**result}

    def _m4b_refusal_gate(self,job_id,kind='retry'):
        """An M4B Retry/Repair press for a book whose refusal is current follows that refusal's fix, the same rule as
        the row (audio_jobs.attention_summary): 'update' and 'review' offer no control, so a press from an outdated
        view is refused and queues nothing; 'wait' only once the working files are gone; 'user' always. A stale
        refusal (the deciding code changed) does not block: one attempt per book per build."""
        import m4b_readmission
        from audio_jobs import RetryRefused,RETRY_CHECKING,RETRY_GATE_UPDATE,RETRY_GATE_REVIEW,RETRY_GATE_WAIT,RETRY_GATE_STOPS,RETRY_GATE_REFUSED
        verb='Repair' if kind=='repair' else 'Retry'
        with self.jobs._db() as db:value=m4b_readmission.describe(db,job_id)
        # A working-files record no longer decides (follow-up 2, section 2.2): the live state of the files does.
        # S9 (ruling 35's refusal texts): each cause in its own words, never one "status changed" for all of them.
        if value and value.get('state')=='refused' and value.get('stale') is not True and value.get('cause')!='working_files':
            fix=value.get('fix')
            if fix=='user':return
            raise RetryRefused(RETRY_GATE_REVIEW%verb if fix=='review' else RETRY_GATE_WAIT%(verb,verb) if fix=='wait' else RETRY_GATE_UPDATE%verb)
        # Files the app cannot clear stop the row (no Retry, no Repair): a press from an outdated view changes nothing.
        stops=self.attention_summary([job_id],retry=False).get(job_id,{}).get('working')
        if isinstance(stops,dict) and stops.get('stops'):raise RetryRefused(RETRY_GATE_STOPS%verb)
        # No current refusal: a Retry still needs a source this build's read-only dry run did not refuse, and a finished
        # check (a pending row offers no Retry; one that could not open the source does, and the press reads it).
        if kind=='retry':
            check=self._m4b_precheck(job_id)
            if check=='pending':raise RetryRefused(RETRY_CHECKING)
            if check=='refused':raise RetryRefused(RETRY_GATE_REFUSED)

    def _m4b_precheck(self,job_id):
        """The read-only plan() dry run's state for this job under this build (audio_jobs.precheck), or None when the
        job is not an M4B row Retry covers."""
        import failed_m4b_retry
        from audio_jobs import _m4b_fields,precheck
        if getattr(getattr(self,'inventory',None),'database',None):self._load_repair_checks()
        rows=self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))
        try:
            if not rows or not failed_m4b_retry.eligible(rows[0]):return None
        except (KeyError,TypeError,ValueError):return None
        return precheck(_m4b_fields(rows[0])[0],self._repair_check_failed(job_id))[0]

    def _already_accepted(self,job_id,identity):
        """A repeated Retry/Repair press for a book already accepted (v0.16.12): the same answer, and nothing new
        is queued or reordered. None when this press is the first one."""
        import m4b_readmission
        rows=self.jobs._rows('SELECT state,manifest FROM audio_jobs WHERE job_id=?',(job_id,))
        if not rows or json.loads(rows[0]['manifest']).get('candidate_id')!=identity:return None
        with self.jobs._db() as db:value=m4b_readmission.describe(db,job_id)
        if value and value.get('queued_next'):return {'job_id':job_id,'requeued':False,**value}
        if rows[0]['state'] in ('pending','running'):return {'job_id':job_id,'requeued':True,'accepted':True,'queued_next':False}
        return None

    def _queue_next_same(self,job_id,kind='retry'):
        """A requeued failed job (the same row) runs right after the current book, in click order, like an M4B
        Retry: one entry in the queue-next ledger, already admitted, whose child is the job itself."""
        import m4b_readmission
        from sqlite_retry import transaction
        def write(db):
            m4b_readmission.ensure(db)
            prior=db.execute('SELECT state,child_job_id FROM m4b_readmissions WHERE parent_job_id=?',(job_id,)).fetchone()
            if prior and prior[0]=='admitted' and prior[1]==job_id:return m4b_readmission.describe(db,job_id) or {}  # keeps its place
            seq=db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM m4b_readmissions').fetchone()[0]
            stamp=time.strftime('%Y-%m-%dT%H:%M:%S+00:00',time.gmtime())
            db.execute('INSERT OR REPLACE INTO m4b_readmissions VALUES(?,?,?,?,?,?,?,?)',(job_id,kind,seq,'admitted',job_id,json.dumps({'reason':'Requeued by '+kind.capitalize()}),stamp,stamp))
            return m4b_readmission.describe(db,job_id) or {}
        # A busy catalog is retried (v0.16.12): every accepted Retry reports its place after the current book.
        try:return transaction(self.jobs.database,write)
        except sqlite3.Error:return {'accepted':True,'queued_next':False}  # still requeued; it runs in normal queue order

    # ------------------------------------------------------------------ a start kept until the queue settles (ruling 35)
    def _settling(self):
        """What a start would wait for now, read only: 'pause' (a Pause still reaching its checkpoints, or a worker still
        pausing), 'start' (an earlier start still checking), else None."""
        if self.__dict__.get('_pause_depth',0):return 'pause'
        if self.__dict__.get('_resume_pending'):return 'start'
        jobs=getattr(self.jobs,'_thread',None)
        if jobs is not None and jobs.is_alive() and self.jobs._stop.is_set():return 'pause'
        cleanup=getattr(self.cleanup,'thread',None)
        if cleanup is not None and cleanup.is_alive() and self.cleanup.stop.is_set():return 'pause'
        return None

    def start_when_settled(self,why=None):
        """Ruling 35 (Sergei 2026-10-26): a start refused only because a Pause, an earlier start or a stopping worker is
        still settling ("Retry Start after it stops") is kept and made when it settles, every check again then. One waits at
        a time; a second press joins it. A Pause pressed after it, or closing, drops it (the later press wins).
        {'state': 'waiting', 'reason': 'pause' | 'start'}."""
        with _BULK_LOCK:
            if self.__dict__.get('_closing') or self.draining:raise StartRefused('closing','Books Arranger is closing. Resume audiobook jobs after it restarts.')
            generation=self.__dict__.get('_start_generation',0)
            waiting=self.__dict__.get('_start_waiting')
            if waiting is not None and waiting['generation']==generation:return {'state':'waiting','reason':waiting['reason']}
            token=object()
            self._start_waiting={'generation':generation,'reason':why or self._settling() or 'pause','since':time.time(),'token':token}
            answer={'state':'waiting','reason':self._start_waiting['reason']}
        threading.Thread(target=self._settle_then_start,args=(token,),name='books-start-when-settled',daemon=True).start()
        self.invalidate_status()
        return answer

    def cancel_waiting_start(self):
        """Resume audiobook jobs pressed again while it waits: {'cancelled': True}, or None when nothing waits."""
        with _BULK_LOCK:
            if self.__dict__.get('_start_waiting') is None:return None
            self._start_waiting=None
        self.invalidate_status()
        return {'cancelled':True}

    def _settle_then_start(self,token,poll=.25):
        def current():
            waiting=self.__dict__.get('_start_waiting')
            return waiting if waiting is not None and waiting['token'] is token else None
        try:
            while True:
                with _BULK_LOCK:
                    waiting=current()
                    if waiting is None:return  # cancelled, or a newer press waits instead
                    if waiting['generation']!=self.__dict__.get('_start_generation',0) or self.draining or self.__dict__.get('_closing'):
                        self._start_waiting=None;return  # a Pause pressed after it, or closing: the later press wins
                why=self._settling()
                if why is not None:
                    with _BULK_LOCK:
                        if current() is not None:current()['reason']=why
                    time.sleep(poll);continue
                with _BULK_LOCK:
                    if current() is None:return
                    self._start_waiting=None
                try:self.resume()
                except StartRefused as error:
                    if error.start_state!='busy':self._record_start_failure(error);return
                    with _BULK_LOCK:
                        again=self.__dict__.get('_start_generation',0)==waiting['generation'] and self.__dict__.get('_start_waiting') is None and not self.draining
                        if again:self._start_waiting=dict(waiting)  # settling again between the look and the start: it waits on
                    if not again:return
                    time.sleep(poll);continue
                except Exception as error:self._record_start_failure(error)
                return
        finally:self.invalidate_status()

    def resume_press(self):
        """Resume audiobook jobs (the toolbar): the queue's start, or, while a Pause or an earlier start is still settling,
        the start kept and made when it settles (start_when_settled; ruling 35)."""
        try:return self.resume()
        except StartRefused as error:
            if error.start_state!='busy':raise
        return self.state()|{'start_admission':self.start_when_settled()}

    def _record_start_failure(self,error):
        if getattr(error,'start_state',None)=='busy' and not self.draining and not self.__dict__.get('_closing'):
            # Ruling 35: a start refused only while something settles is kept and made when it settles, never recorded as a
            # failure that asks Sergei to press Start again.
            try:return self.start_when_settled()
            except StartRefused as closing:error=closing
        reason=str(error) or type(error).__name__
        value={'state':getattr(error,'start_state','blocked'),'job_id':None,'reason':reason}
        self.jobs.report_priority(value)
        import m4b_readmission
        try:
            with self.jobs._db() as db:m4b_readmission.record_waiting(db,reason)
        except sqlite3.Error as failure:
            value=dict(value,reason=reason+'; could not save start failure: '+str(failure));self.jobs.report_priority(value)
        return value

    def _resume_later(self):
        """One existing scheduler owner; a newer request behind it gets explicit retryable busy."""
        try:generation=self._capture_start_generation()
        except StartRefused as error:return self._record_start_failure(error)
        with _BULK_LOCK:
            busy=self.__dict__.get('_resume_pending',False)
            if not busy:
                owner=object();self._resume_pending=True;self._resume_pending_owner=owner
        if busy:return self._record_start_failure(StartRefused('busy','A previous start request is still checking. Retry Start after it stops; saved requests are retained.'))
        def start():
            try:self.resume(start_generation=generation,pending_owner=owner)
            except Exception as error:self._record_start_failure(error)
            finally:
                with _BULK_LOCK:
                    if self.__dict__.get('_resume_pending_owner') is owner:
                        self._resume_pending=False;self._resume_pending_owner=None
        try:threading.Thread(target=start,name='books-resume-after-control',daemon=True).start()
        except Exception as error:
            with _BULK_LOCK:
                if self.__dict__.get('_resume_pending_owner') is owner:self._resume_pending=False;self._resume_pending_owner=None
            return self._record_start_failure(error)
        return {'state':'checking','generation':generation}

    def retry_all(self,items=None,skip=()):
        """Reserve one submitter briefly; persist outside the control lock, then recheck its intent. skip: job ids with a
        queued Retry or Repair press (0.22.1, Judy 1.3): Retry all leaves them out; the queue runs them."""
        from audio_jobs import RETRY_SCANNING,RETRY_CLOSING,RETRY_ALL_RUNNING,RETRY_ALL_NONE
        if self.inventory.worker and self.inventory.worker.is_alive():raise StartRefused('busy',RETRY_SCANNING)
        generation=self._capture_start_generation()
        if items is None:
            summary=self.attention_summary()
            targets=[{'job_id':job_id,'kind':'retry'} for job_id,item in summary.items() if item.get('retry',{}).get('allowed') is True and job_id not in skip]
        else:
            if not isinstance(items,list) or not 1<=len(items)<=10000 or len({item.get('job_id') for item in items if isinstance(item,dict)})!=len(items):raise ValueError('Expected unique selected retry targets')
            targets=[]
            for item in items:
                if not isinstance(item,dict) or set(item)!={'id','revision','job_id','kind'} or item['kind'] not in ('retry','repair') or type(item['revision']) is not int or item['revision']<1 or not isinstance(item['id'],str) or not isinstance(item['job_id'],str):raise ValueError('Invalid selected retry target')
                targets.append(dict(item))
        if not targets:raise StartRefused('busy',RETRY_ALL_NONE)
        run_id=str(uuid.uuid4());created=replacement_now()
        with _BULK_LOCK:
            if not self._start_allowed(generation):raise StartRefused('stale','Retry submission was superseded by Pause or closing; no new requests were submitted.')
            current=getattr(self,'_retry_all_run',None)
            if current and current['state']=='running':raise StartRefused('busy',RETRY_ALL_RUNNING)
            owner=object();stop=threading.Event()
            run={'id':run_id,'created':created,'mode':'selected' if items is not None else 'all','state':'running','total':len(targets),'done':0,'accepted':0,'queued':0,'next':0,'refused':0,'accepted_ids':[],'targets':targets,'start_generation':generation,'start_outcome':None,'receipt_durable':False}
            self._retry_all_run=run;self._retry_all_owner=owner;self._retry_all_stop=stop
        # SQLite connection/write/commit may wait: never hold _BULK_LOCK across it.
        if not self._save_bulk_receipt(run):
            with _BULK_LOCK:
                if self.__dict__.get('_retry_all_owner') is owner:run['state']='stopped'
            raise StartRefused('blocked','Retry submission receipt could not be saved; no new retry requests were submitted.')
        launch_error=None
        with _BULK_LOCK:
            valid=self.__dict__.get('_retry_all_owner') is owner and self._start_allowed(generation) and not stop.is_set()
            if not valid:
                run['state']='stopped';run['start_outcome']={'state':'stale','reason':'Retry submission was paused or closed before admission; no new requests were submitted.'}
            else:
                self._retry_all_thread=threading.Thread(target=self._retry_all_work,args=(run,targets,stop),name='books-retry-all',daemon=True)
                try:self._retry_all_thread.start()
                except Exception as error:
                    launch_error=error;run['state']='stopped';run['start_outcome']={'state':'blocked','reason':str(error) or type(error).__name__}
            response=copy.deepcopy(run)
        if not valid or launch_error:
            self._save_bulk_receipt(run)
            with _BULK_LOCK:response=copy.deepcopy(run)
        if launch_error:raise StartRefused('blocked','Retry submission could not start: '+str(launch_error))
        return response

    def _save_bulk_receipt(self,run):
        import m4b_readmission
        try:
            with _BULK_LOCK:
                snapshot=copy.deepcopy(run);snapshot['receipt_durable']=True;snapshot.pop('receipt_error',None)
            with self.jobs._db() as db:m4b_readmission.save_bulk(db,snapshot)
            with _BULK_LOCK:run['receipt_durable']=True;run.pop('receipt_error',None)
        except sqlite3.Error as error:
            with _BULK_LOCK:run['receipt_durable']=False;run['receipt_error']=str(error)
            return False
        return True

    def _retry_all_work(self,run,targets,stop):
        accepted=False
        try:
            for target in targets:
                if stop.is_set() or not self._start_allowed(run['start_generation']):break
                try:ok=self._retry_one(target['job_id'],target.get('kind','retry'),target,start_generation=run['start_generation'])
                except Exception as error:ok=None;failure=str(error) or type(error).__name__
                else:failure='' if ok else 'This book cannot accept another retry request; check its current details.'
                accepted=accepted or bool(ok)
                with _BULK_LOCK:
                    run['done']+=1
                    if ok:
                        run['accepted']+=1;run['queued']+=1;run['accepted_ids'].append(target['job_id'])
                        if ok=='next':run['next']+=1
                    else:run['refused']+=1
                    if failure:run['last_refusal']=failure
                if not self._save_bulk_receipt(run):break
        finally:
            if accepted and not stop.is_set() and not self.draining:
                try:
                    result=self.resume(start_generation=run.get('start_generation'))
                    outcome=result.get('start_admission',{'state':'requested'}) if isinstance(result,dict) else {'state':'requested'}
                    with _BULK_LOCK:run['start_outcome']=dict(outcome,reason=outcome.get('reason',''))
                except Exception as error:
                    with _BULK_LOCK:run['start_outcome']={'state':getattr(error,'start_state','blocked'),'reason':str(error) or type(error).__name__}
            elif accepted:
                closing=self.draining or self.__dict__.get('_closing',False)
                with _BULK_LOCK:run['start_outcome']={'state':'closing' if closing else 'paused','reason':'Books is closing; retry requests are saved.' if closing else 'Retry requests are saved; audiobook work is paused.'}
            with _BULK_LOCK:run['state']='done' if run['done']==run['total'] else 'stopped'
            self._save_bulk_receipt(run)

    def _bulk_retry_view(self):
        import m4b_readmission
        with _BULK_LOCK:run=copy.deepcopy(getattr(self,'_retry_all_run',None))
        with self.jobs._db() as db:
            db.execute('BEGIN')
            if run is None:
                run=m4b_readmission.latest_bulk(db)
                if run and run['state']=='running':run=dict(run,state='interrupted',start_outcome={'state':'blocked','reason':'Previous request submission was interrupted. Saved requests are retained.'})
            if run is None:return None
            worker=copy.deepcopy(getattr(self.jobs,'_priority_status',{}))
            run['progress']=m4b_readmission.target_progress(db,run.get('accepted_ids',[]),worker.get('job_id') if worker.get('state')=='checking' else None)
            run['worker']=worker
            return {key:value for key,value in run.items() if key not in ('targets','accepted_ids')}

    def _retry_one(self,job_id,kind='retry',target=None,start_generation=None):
        """One Retry all book through its own Retry path, without starting the queue.

        'next' (M4B: runs right after the current book), 'queued' (normal queue order) or None (refused).
        """
        self._reacquire_admission(job_id=job_id)
        import failed_m4b_retry,m4b_repair
        from audio_jobs import RetryRefused
        with self.operation_lock:
            if start_generation is not None and not self._start_allowed(start_generation):raise StartRefused('stale','Retry admission was superseded by Pause or closing.')
            if self.inventory.worker and self.inventory.worker.is_alive() or self.draining:return None
            current=self.attention_summary([job_id]).get(job_id)
            # A current user-fixable refusal can offer Retry while grouped under Other.
            # Use the same capability as the individual button; admission still rechecks the book.
            if kind not in ('retry','repair') or not current or current.get(kind,{}).get('allowed') is not True:return None
            rows=self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))
            if not rows:return None
            manifest=json.loads(rows[0]['manifest'])
            if target and 'id' in target and (target['id']!=manifest['candidate_id'] or target['revision']!=manifest['candidate_revision']):return None
            try:
                from audio_jobs import tag_repair_retry
                recovery=(current.get('producer_recovery') or {}).get('state') in {'ready','isolated_retained'}
                if kind=='retry' and self._m4b_parent(job_id,manifest.get('candidate_id'),manifest.get('candidate_revision'),(lambda row:row['state']=='needs attention' and not row['output']) if recovery else tag_repair_retry) is not None:
                    return 'next' if self._request_m4b_readmission(job_id,'retry').get('accepted') else None
                if self._m4b_parent(job_id,manifest.get('candidate_id'),manifest.get('candidate_revision'),(m4b_repair.eligible if kind=='repair' else failed_m4b_retry.eligible)) is not None:
                    self._m4b_refusal_gate(job_id,kind)
                    self._clear_first(job_id,kind)
                    return 'next' if self._request_m4b_readmission(job_id,kind).get('accepted') else None
                self._clear_first(job_id,kind)
                with self._review_boundary():
                    self.jobs.retry_admission_hold(job_id,manifest.get('candidate_id'),manifest.get('candidate_revision'),self.working.admission_clear,self._space_ready,review=False)
                return 'next' if self._queue_next_same(job_id,kind).get('queued_next') else 'queued'
            except RetryRefused:return None

    def current_audiobook(self,identity,jobs=None):
        """jobs: the caller's one jobs list for a whole page (loading every job per row was the book list's main cost)."""
        if not hasattr(self,'publications'):return {'state':'none','reason':'No verified audiobook created yet','identity':'none'}
        value=self.publications.describe(jobs if jobs is not None else self.jobs.status()['jobs'],identity)
        return {key:copy.deepcopy(value[key]) for key in ('state','reason','path','identity','publication_id','kind','tags_state') if key in value}

    # ------------------------------------------------------------ the one to-do list (Judy 2026-10-24, rulings 10, 6a, 6b)
    # Judy 2026-10-24 (0.22.0 review, B3): the three hold chips join "Needs your answer"; Other keeps stopped jobs and a
    # catch-all for a hold the app cannot classify.
    NEEDS_GROUPS=NEEDS_GROUPS  # the one list of chips (review_backend)
    ASK_GROUPS=('title_author','author_unclear','same_author')
    NO_COVERAGE={'listed':0,'still_checking':0,'removed':0,'with_job':0}

    def needs_you(self):
        """{candidate id: {'group', 'reasons', 'ask', 'also', 'hold'}} for every current book without a job that only
        Sergei can move on: files gone from disk (files_missing), a question from the identity step (title_author,
        author_unclear, same_author), a name already in Sorted (name_taken), one of the three holds (part_of_book,
        files_unclear, order_unclear; a book with several counts once, in that order, the next as 'also'), or a hold the
        app cannot classify ('other', "Needs you"). Read-only; cached on cheap catalog stamps. todo_coverage() says
        where every other current book is."""
        return self._todo()[0]

    def todo_coverage(self):
        """Where every current book is (Judy 2026-10-24, 0.22.0 review B5): {'listed', 'still_checking', 'removed',
        'with_job'}. still_checking counts the books automatic processing researches again before they can be listed
        or filed: never researched yet, researching, waiting for a source, a retry-later hold, or a record from an older
        research version, older author rules, or a book whose files or saved values changed since."""
        return self._todo()[1]

    def _todo(self):
        database=getattr(getattr(self,'inventory',None),'database',None)
        if not database:return {},dict(self.NO_COVERAGE)  # no catalog (a status computed without one): nothing to list
        with connect(database) as db:
            have={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'book_groups' not in have or 'automatic_candidates' not in have:return {},dict(self.NO_COVERAGE)
            stamp=(tuple(db.execute('SELECT count(*),max(attempted) FROM automatic_candidates').fetchone()),
                   tuple(db.execute('SELECT count(*),total(revision) FROM book_groups WHERE superseded=0').fetchone()),
                   tuple(db.execute('SELECT revision FROM book_catalog_revision WHERE id=1').fetchone() or ()) if 'book_catalog_revision' in have else (),
                   tuple(db.execute('SELECT count(*),max(updated) FROM audio_jobs').fetchone()) if 'audio_jobs' in have else (),
                   tuple(db.execute('SELECT count(*) FROM attention_dismissals').fetchone()) if 'attention_dismissals' in have else ())
            rules=__import__('author_rules').load(database);generation=rules.generation if rules else ''
            cached=self.__dict__.get('_needs_cache')
            if cached and cached[0]==(stamp,generation):return copy.deepcopy(cached[1]),dict(cached[2])
            current={r['id']:(r['revision'],r['fingerprint']) for r in db.execute('SELECT id,revision,fingerprint FROM book_groups WHERE superseded=0')}
            jobs={r[0] for r in db.execute("SELECT json_extract(manifest,'$.candidate_id') FROM audio_jobs")} if 'audio_jobs' in have else set()
            dismissed={(r[0],r[1]) for r in db.execute('SELECT candidate_id,fingerprint FROM attention_dismissals')} if 'attention_dismissals' in have else set()
            gone=set()
            if 'catalog_group_members' in have:
                gone={r[0] for r in db.execute('SELECT DISTINCT m.group_id FROM catalog_group_members m JOIN files f ON f.root=m.root AND f.path=m.path WHERE f.missing=1')}
            records={r['id']:r for r in db.execute('SELECT id,revision,fingerprint,state,result FROM automatic_candidates')}
        import todo_causes,local_identity
        from public_research import RESEARCH_VERSION
        found={};coverage=dict(self.NO_COVERAGE)
        for identity,(revision,fingerprint) in current.items():
            if identity in jobs:coverage['with_job']+=1;continue  # queued, converting, converted or a stopped job (listed as Stopped)
            record=records.get(identity)
            same_files=bool(record and record['fingerprint']==fingerprint);exact=bool(same_files and record['revision']==revision)
            try:result=json.loads(record['result']) if same_files else None
            except (TypeError,ValueError):result=None
            if not isinstance(result,dict):result=None
            ask=result.get('ask') if result and exact and isinstance(result.get('ask'),dict) else None
            hold=(result or {}).get('identity_hold') if result and record['state']=='Held' else None
            if isinstance(hold,dict) and hold.get('kind')=='missing_parts' and result.get('research_version')==RESEARCH_VERSION:
                # Rulings 19 and 10 (2026-10-24): the track numbers say parts of this book are missing; the row names them.
                if (identity,fingerprint) in dismissed:coverage['removed']+=1
                else:found[identity]={'group':'files_missing','reasons':[str(r) for r in result.get('reasons') or []][:8],'ask':None,'hold':hold}
                continue
            if identity in gone:
                # Missing files first; the identity question, if any, is answered on the same row ("Also:").
                if (identity,fingerprint) in dismissed:coverage['removed']+=1
                else:found[identity]={'group':'files_missing','reasons':['Files missing'],'ask':ask,'also':ask['kind'] if ask and ask.get('kind') in ('title_author','author_unclear') else None}
                continue
            if result is None or record['state']!='Held':coverage['still_checking']+=1;continue
            reasons=[str(r) for r in result.get('reasons') or []][:8]
            if not reasons:coverage['still_checking']+=1;continue
            if reasons==['Manual draft retained']:
                # His saved review holds the book; automatic processing only looks again (Held filter: Let the app handle it).
                found[identity]={'group':'other','reasons':reasons,'ask':None};continue
            if exact and any('already exists at this path' in r for r in reasons):
                found[identity]={'group':'name_taken','reasons':reasons,'ask':None};continue
            # Senua's 0.22.0 review, G5 (rulings 10 and 5): a held book with a reason is listed whether or not it waits for a
            # change (a refusal at the approval step is retried on a timer and was never listed). Still checking: a record
            # from an older research version (researched once more after an update) or one a newer author rule decides (G6:
            # only the books whose credits or folders the rule names; every other row stays listed).
            version=result.get('research_version')
            if version and version!=RESEARCH_VERSION:coverage['still_checking']+=1;continue
            if 'rules_generation' in result and (result.get('rules_generation') or '')!=generation and (rules is None or not hasattr(rules,'changed_for') or rules.changed_for(result)):
                coverage['still_checking']+=1;continue
            if result.get('ask'):
                # A question needs the exact revision: a value Sergei saved since (6a) is researched again first.
                if not ask or ask.get('kind')=='same_author' and rules is not None and (rules.same_as(ask.get('new','')) or rules.keep(ask.get('new',''))):
                    coverage['still_checking']+=1;continue
                if ask.get('kind') in self.ASK_GROUPS:found[identity]={'group':ask['kind'],'reasons':reasons,'ask':ask};continue
            kinds=todo_causes.holds(result)
            if kinds==['order_unclear']:
                # Ruling 71m: a numbering gap in a folder settled as the whole book is listed under Missing files.
                gap=self._established_gap(identity)
                if gap:
                    if (identity,fingerprint) in dismissed:coverage['removed']+=1
                    else:found[identity]={'group':'files_missing','reasons':reasons,'ask':None,'hold':gap}
                    continue
            if kinds:
                # The same files: an order or file choice he saved in the panel (a new revision) keeps the row listed.
                found[identity]={'group':kinds[0],'also':kinds[1] if len(kinds)>1 else None,'reasons':reasons,'ask':None,'hold':result.get('identity_hold')}
            elif exact:found[identity]={'group':'other','reasons':reasons,'ask':None}
            else:coverage['still_checking']+=1
        coverage['listed']=len(found)
        self.__dict__['_needs_cache']=((stamp,generation),copy.deepcopy(found),dict(coverage))
        return found,coverage

    def stale_attention(self,summary,jobs,converted):
        """Judy's stale rule (section 1): a job is not listed when its book was converted since by another job, or when
        its book is no longer current (regrouped); whatever older jobs say. One predicate for every count and list."""
        if not summary:return {}
        database=getattr(getattr(self,'inventory',None),'database',None)
        if not database:return summary
        by_job={job['job_id']:job for job in jobs}
        with connect(database) as db:
            current={r[0] for r in db.execute('SELECT id FROM book_groups WHERE superseded=0')} if db.execute("SELECT 1 FROM sqlite_master WHERE name='book_groups'").fetchone() else None
        kept={}
        for job_id,item in summary.items():
            job=by_job.get(job_id);candidate=(job or {}).get('manifest',{}).get('candidate_id')
            if current is not None and candidate not in current:continue
            if candidate in converted and (job or {}).get('state')!='completed':continue
            kept[job_id]=item
        return kept

    def ask_payload(self,row,entry):
        """Per book, one 'ask' object for the row (Judy's section 11): kind, fields with proposal and basis, author
        candidates, the destination and whether it is taken, the missing files, the same-author pair."""
        ask=copy.deepcopy(entry.get('ask') or {})
        payload={'kind':entry['group'],'also':entry.get('also'),'why':ask.get('why',''),'reasons':list(entry.get('reasons') or [])[:4],
                 'fields':ask.get('fields') or {},'candidates':ask.get('candidates') or [],
                 # 0.22.1: an odd-name question is approved on its own row only, never in bulk (Judy 11.4, item 2).
                 'odd_name':ask.get('odd_name') is True}
        if entry['group']=='same_author':
            payload['same_author']={k:ask.get(k) for k in ('new','existing','existing_books','why')}
            payload['same_author']['count']=sum(1 for e in self.needs_you().values() if e['group']=='same_author' and (e.get('ask') or {}).get('new')==ask.get('new'))
        members=row.get('members') or []
        parts=(entry.get('hold') or {}) if (entry.get('hold') or {}).get('kind')=='missing_parts' else None
        if parts and members:
            # The parts the track numbers say are missing, named "Part 3 of 3" in the book's folder.
            folder=os.path.dirname(members[0]['path']);total=int(parts.get('total') or len(members))
            payload['missing']={'folders':[folder],'files':[os.path.join(folder,'Part %d of %d'%(int(n),total)) for n in parts.get('missing') or []],
                                'present':len(members),'total':len(members)+len(parts.get('missing') or []),'parts':list(parts.get('missing') or [])}
        elif entry['group']=='files_missing' or any(m.get('missing') for m in members):
            gone=[m for m in members if m.get('missing')]
            try:root=self.reviews._source_root(row)
            except (ValueError,OSError,KeyError):root=''
            full=[m['path'] if not root or os.path.isabs(m['path']) else os.path.join(root,m['path']) for m in gone]
            payload['missing']={'folders':sorted({os.path.dirname(p) for p in full}),'files':full,
                                'present':sum(1 for m in members if not m.get('missing')),'total':len(members)}
        shown_series=None
        if entry['group']!='files_missing' or payload['missing']['present']:
            try:
                preview=self.approval_preview(row['id'],row['revision'])
                payload['destination']={'path':preview['path'],'absolute':preview['absolute'],'taken':preview['taken'],'reason':preview['reason']}
                shown_series=preview.get('series')
                # The proposals are the values Approve uses (local_identity.shown): a suspected reader is never proposed
                # as the author (ruling 14), and an empty author files the book under Без автора.
                from organization import NO_AUTHOR
                fields=payload['fields']
                fields['title']=dict(fields.get('title') or {'basis':''},proposal=preview['title'])
                author=fields.get('author') or {'basis':''};shown_author='' if preview['author']==NO_AUTHOR else preview['author']
                fields['author']=dict(author,proposal=shown_author,basis=author.get('basis','') if author.get('proposal')==shown_author else '')
            except (ValueError,OSError) as error:
                payload['destination']={'path':'','absolute':'','taken':False,'reason':str(error)[:200]}
        if entry['group'] in ('part_of_book','files_unclear','order_unclear','other'):self._hold_payload(row,entry,payload)
        # A duplicate-recording row (Futaba's 0.22.0 QA, m-3): typed, so the page hides its Approve (inert there, with a
        # wrong "name taken" tooltip) without reading copy. 'verified' or 'possible'; Remove this copy is ask.copy.
        import book_delete
        payload['duplicate']=book_delete.duplicate(entry)
        try:self._identity_lines(row,payload)
        except (ValueError,KeyError,TypeError,OSError,sqlite3.Error):pass
        # The series Approve uses, when the question itself carries none (section 8.4): a found series, never a guess.
        if 'series' not in payload and isinstance(shown_series,dict) and shown_series.get('name'):
            payload['series']=dict(shown_series,basis='research');payload.pop('series_clue',None)
        try:self._membership_lines(row,entry,payload)
        except (ValueError,KeyError,TypeError,OSError,sqlite3.Error):pass
        return payload

    # ---------------------------------------------------------------- Judy's 0.23.1 spec, sections 4-6 (POST-023)
    _GENERIC_CLUES={'mp3','m4a','m4b','audio','аудио','аудиокнига','audiobook','книга','book','cd','disc','диск','track','трек'}

    def _identity_lines(self,row,payload):
        """Section 4: the facts behind the Book and Author / reader lines, from the row's own tags and folders (the page
        never infers them): a flag on the shown title or author, the raw clue with its role when it differs, the reader,
        the series the title mentions."""
        import local_identity
        from local_identity import NARRATOR_MARKER,garbled,author_prefix,quoted_title,narrator_names,NARRATOR_TAGS,clean_title,norm
        fields=payload.setdefault('fields',{});members=row.get('members') or []
        title=fields.get('title') or {};author=fields.get('author') or {}
        shown=str(title.get('proposal') or '')
        ancestors=[Path(members[0]['path']).parent.name,Path(members[0]['path']).parent.parent.name] if members else []
        flag=''
        if shown and NARRATOR_MARKER.search(shown):flag='narrator'
        elif shown and garbled(shown):flag='garbled'
        elif shown and author_prefix(shown,members,ancestors):flag='author_in_title'
        if flag:fields['title']=dict(title,flag=flag)
        def role(value,kind):
            value=str(value or '')
            if garbled(value):return 'garbled'
            if NARRATOR_MARKER.search(value):return 'narrator'
            if quoted_title(value) or kind=='author' and re.match(r'^\s*[^.\d]{3,60}?\.\s+\S',value) or kind=='title' and author_prefix(value,members,ancestors):return 'author_and_title'
            if re.search(r'\[[^\]]{2,60}\]\s*$',value):return 'uploader'
            if norm(clean_title(value)) in self._GENERIC_CLUES or re.fullmatch(r'\s*(?:cd|disc|диск)\s*\d*\s*',value,re.I):return 'generic'
            return ''
        clue=str(row.get('title_clue') or '')
        if clue and clean_title(clue)!=clean_title(shown):
            fields['title']=dict(fields.get('title') or {},clue={'text':clue,'role':role(clue,'title')})
        credits=[str(a) for a in row.get('artists') or [] if a]
        shown_author=str(author.get('proposal') or '')
        if shown_author and garbled(shown_author):fields['author']=dict(author,flag='garbled')
        raw='; '.join(credits)
        readers=[]
        for member in members[:50]:
            tags=local_identity._tags(member)
            readers+=[local_identity.text(tags.get(key)) for key in NARRATOR_TAGS if tags.get(key)]
        readers+=narrator_names([clue]+credits+ancestors+[local_identity.text(local_identity._tags(m).get('album')) for m in members[:3]])
        readers=[r for r in dict.fromkeys(readers) if r and not local_identity.compare_names(r,shown_author or '-')]
        if readers:payload['reader']=', '.join(readers[:3])
        if raw and norm(raw)!=norm(shown_author) and not (readers and norm(raw)==norm(readers[0])):
            fields['author']=dict(fields.get('author') or author,clue={'text':raw[:300],'role':role(raw,'author')})
        series=fields.get('series') or {};number=fields.get('number') or {}
        if series.get('proposal'):
            payload['series']={'name':series['proposal'],'number':str(number.get('proposal') or ''),'basis':series.get('basis','')}
        else:
            mention=re.search(r'\(([^()]{3,80}?#\s*\d{1,3})\)',clue) or re.search(r'\(([^()]*(?:книга|book|том)\s*\d{1,3}[^()]*)\)',clue,re.I)
            if mention and mention[1] not in shown:payload['series_clue']=mention[1].strip()

    def _established_gap(self,identity):
        """Ruling 71m: {'kind': 'missing_parts', 'missing', 'total'} when this book is its whole source folder (no other
        current book holds a file of it; not a raised folder question) and its numbering (file names, else track tags)
        skips numbers or starts after 1. A year or an id in a file name is not a part number (ruling 73f,
        folder_unit.numbers). None otherwise. Read-only."""
        import folder_unit,itertools
        with connect(self.inventory.database) as db:
            found=db.execute('SELECT root,evidence FROM book_groups WHERE id=? AND superseded=0',(identity,)).fetchone()
            if found is None:return None
            evidence=json.loads(found['evidence']);members=evidence.get('members') or []
            if len(members)<2 or (evidence.get('folder_unit') or {}).get('kind') in ('ask','remainder') or evidence.get('source_partition_uncertain'):return None
            if any(Path(m['path']).suffix.lower()=='.m4b' for m in members):return None
            if self._unit_siblings(db,{'members':members,'source_root':found['root']}):return None
        numbers=folder_unit.numbers(members)
        if not numbers:return None
        # The numbers before the first, then the skipped ones: the first 500, never the whole run built (Senua 0.24.0 M3:
        # a large number in a file name costs nothing more than a small one).
        missing=list(itertools.islice(itertools.chain(range(1,max(numbers['start'],1)),numbers['missing']),folder_unit.MAX_LISTED))
        if not missing:return None
        return {'kind':'missing_parts','missing':missing,'total':numbers['end'],'numbers':{k:numbers[k] for k in ('source','first','last','skipped','skipped_total')}}

    def _unit_siblings(self,db,row):
        """The catalog's present audio files of this book's source folder that another current book holds: [(path, group
        id)]. Disc and part folders of one book count as its folder (folder_unit.unit_of)."""
        import folder_unit
        members=row.get('members') or []
        if not members:return []
        units={folder_unit.unit_of(m['path']) for m in members}
        if len(units)!=1:return []
        folder,kind=next(iter(units));prefix=folder.rstrip('\\/')+os.sep
        own={m['path'] for m in members}
        found=[]
        for path,group in db.execute("""SELECT f.path,c.group_id FROM files f LEFT JOIN catalog_group_members c ON c.root=f.root AND c.path=f.path
                AND c.group_id IN (SELECT id FROM book_groups WHERE superseded=0) WHERE f.root=? AND f.kind='audiobook' AND f.missing=0
                AND substr(f.path,1,?)=?""",(row.get('source_root') or '',len(prefix),prefix)):
            if path in own or folder_unit.unit_of(path)!=(folder,kind):continue
            found.append((path,group))
        return found

    def _membership_lines(self,row,entry,payload):
        """Sections 5 and 6: the Numbers line (what the present numbering does), whether membership is settled
        ('established': no other current book holds a file of this folder and the scan is complete; 'checking'
        otherwise), the stories a one-folder book includes, and the raised folder question (cause folder_books)."""
        import folder_unit
        members=[m for m in row.get('members') or [] if not m.get('intentionally_retired')]
        unit=row.get('folder_unit') or {}
        if unit.get('kind')=='ask' and payload.get('kind')=='files_unclear':
            payload['cause']='folder_books';payload['facts']={'works':[{'name':b['name'],'files':b['files']} for b in unit.get('books') or []][:200]}
        if payload.get('kind') in ('order_unclear','files_unclear','part_of_book','files_missing') and len(members)>1:
            numbers=folder_unit.numbers(members)
            if numbers:payload['numbers']={k:numbers[k] for k in ('source','first','last','skipped','skipped_total')}
        if payload.get('kind') in ('order_unclear','files_unclear','part_of_book'):
            with connect(self.inventory.database) as db:siblings=self._unit_siblings(db,row)
            complete=str(row.get('coverage') or '').startswith('Scanned scope complete')
            if unit.get('kind') in ('ask','remainder'):pass
            elif siblings or not complete:payload['membership']='checking'
            else:payload['membership']='established'
        if unit.get('kind')=='one' or len({str((m.get('metadata') or {}).get('tags',{}).get('album','')).strip() for m in members})>1:
            found=folder_unit.contents(members)
            if found:payload['contents']=found

    def folder_view(self,rows):
        """Judy's section 3 (rulings 68 and 70) for every shown row: its source folders with the ids open_folder takes,
        the number of the book's files in each, and whether its originals are gone (every file gone from the catalog or
        removed by the app after conversion). Catalog facts only; the press checks the folder live."""
        for row in rows:
            members=row.get('members') or []
            counts={}
            for member in members:
                folder=str(Path(member['path']).parent)
                counts[folder]=counts.get(folder,0)+1
            directories=sorted(counts,key=str.casefold)
            row['source_directories']=[{'id':str(uuid.uuid5(uuid.NAMESPACE_URL,'Audiobooks\x1f'+p)),'path':p,'files':counts[p]} for p in directories[:50]]
            row['source_directory_count']=len(directories)
            row['source_state']='gone' if members and all(m.get('missing') or m.get('intentionally_retired') for m in members) else 'present'

    def _hold_payload(self,row,entry,payload):
        """The three hold rows (Judy 2026-10-24, 0.22.0 review B4): the typed cause and the numbers its sentence needs
        (from the row's own members and the recorded hold: no research, no file access), and the files Approve will use
        in its order: the order and files Sergei saved in the panel, else every file in the catalog's order. Other's
        catch-all gets its first reason."""
        import todo_causes
        members=row.get('members') or [];reasons=list(entry.get('reasons') or [])
        payload['reason']=reasons[0] if reasons else ''
        saved=(row.get('review_context') or {}).get('track_actor')=='user'
        order=row.get('track_order') if saved else None;included=row.get('included') if saved else None
        listed=todo_causes.files(members,order,included)
        chosen=[m for m in members if m['path'] in {f['path'] for f in listed}];by_path={m['path']:m for m in chosen}
        chosen=[by_path[f['path']] for f in listed]
        title=((payload.get('fields') or {}).get('title') or {}).get('proposal','')
        def cause(kind):
            if kind=='order_unclear':return todo_causes.order_cause(chosen)
            if kind=='files_unclear':return todo_causes.files_cause(chosen,reasons,title,split=bool(row.get('split_book')),works=(row.get('joined_parts') or {}).get('works') or row.get('album_works'))
            if kind=='part_of_book':return todo_causes.piece_cause(entry.get('hold'),files=len(chosen))
            return {}
        found=cause(entry['group'])
        payload['cause']=found.get('cause','');payload['facts']={k:v for k,v in found.items() if k not in ('cause','flagged')}
        flagged=set(found.get('flagged') or ())
        if entry.get('also'):
            also=cause(entry['also']);payload['also_cause']=also.get('cause','');payload['also_facts']={k:v for k,v in also.items() if k not in ('cause','flagged')}
            flagged|=set(also.get('flagged') or ())
        listed=todo_causes.files(chosen,None,None,flagged)  # chosen is already in Approve's order
        payload['files']=listed[:6];payload['file_count']=len(listed);payload['flagged']=[f for f in listed if f['flag']][:6]
        payload['saved_tracks']=saved

    def scan_again(self,id,revision):
        """Scan again: read this book's files again now. Changes and deletes nothing on disk. Missing files (ruling 10):
        a file that is back is catalogued again ('found'). A hold row (Judy 2026-10-24, 0.22.0 review B4): 'changed' when
        a file changed (the book is then checked again), and when a file is gone or renamed a scan of the book's source
        starts so the new names are catalogued ('scan_started'), unless automatic processing or a scan owns discovery
        ('scan_later'). {'found', 'changed', 'scan_started', 'scan_later', 'checked_utc', 'reason'}."""
        import datetime
        try:listed_missing=any(m.get('missing') for m in self.inventory.candidate('Audiobooks',id)['members'])
        except (ValueError,KeyError,TypeError):listed_missing=False
        entry=self.needs_you().get(id) or {}
        if entry.get('group')=='files_missing' and (entry.get('hold') or {}).get('kind')=='missing_parts':
            # Futaba's 0.22.0 QA, M-2: a missing part ("Part 2 of 3") is no known member, so re-reading the known parts said
            # "found" with the part still absent, and a restored part was never catalogued. Found now means a new audio
            # file beside the book: its source is scanned so the file is catalogued and the set regroups; none: not found.
            self.inventory.refresh_candidate_sources('Audiobooks',id,revision,force=False)  # the known parts: changed or gone
            new=self._new_audio_beside(id)
            started,later=self._scan_book_source(id) if new else (False,False)
            if started:self.__dict__.pop('_needs_cache',None)
            return {'found':False,'changed':bool(new),'scan_started':started,'scan_later':later,
                    'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reason':''}
        receipt=self.inventory.refresh_candidate_sources('Audiobooks',id,revision,force=False)
        state=receipt.get('state');found=state in ('refreshed','unchanged')
        gone=not listed_missing and state=='held' and receipt.get('hold_code')=='source_unavailable'
        started=later=False
        if gone:started,later=self._scan_book_source(id)
        if state=='refreshed':
            # The groups take the changed files now, so the book leaves the list at this answer, not one poll later.
            try:self.inventory.candidate('Audiobooks',id)
            except ValueError:pass  # regrouped: the old id is no longer current
        if found or started:self.__dict__.pop('_needs_cache',None)
        return {'found':found,'changed':state=='refreshed' or gone,'scan_started':started,'scan_later':later,
                'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reason':'' if found or gone else receipt.get('reason','')}

    def _scan_book_source(self,id):
        """Start a scan of this book's source so new or renamed files are catalogued: (started, later). Later when automatic
        processing or another scan owns discovery (it picks them up); never two scans at once."""
        automatic=getattr(self,'automatic',None)
        owned=automatic is not None and automatic.status()['state'] in ('Running','Stopping')
        worker=getattr(self.inventory,'worker',None)
        if owned or worker is not None and worker.is_alive():return False,True
        try:self.inventory.launch_source(self.inventory.source_root_for_candidate(id))
        except ValueError:return False,True
        return True,False

    def _new_audio_beside(self,id,limit=5000):
        """Audio files in this book's folders that the catalog does not hold yet (a restored part). Read-only: one
        directory listing per folder, at most `limit` entries each."""
        from metadata import AUDIO
        try:members=self.inventory.candidate('Audiobooks',id)['members']
        except (ValueError,KeyError,TypeError):return []
        folders=sorted({str(Path(m['path']).parent) for m in members})
        found=[]
        with connect(self.inventory.database) as db:
            for folder in folders:
                try:
                    with os.scandir(folder) as entries:
                        for count,item in enumerate(entries):
                            if count>=limit:break
                            if Path(item.name).suffix.lower() in AUDIO and item.is_file(follow_symlinks=False) \
                                    and not db.execute('SELECT 1 FROM files WHERE path=?',(item.path,)).fetchone():found.append(item.path)
                except OSError:continue
        return found

    def keep_separate(self,id,revision):
        """Judy's "Keep as separate books" (2026-10-25): Sergei's answer "these are separate books" to a "Part of a bigger book"
        set row. Records each file (its size and time) as its own book in the separate-volumes store and touches no file;
        it approves nothing: each new book is checked again like any other. Remembered per file until it changes.
        Returns {'kept': n}, n the books the regroup really made. Raises ValueError for a changed row ('Candidate changed...'),
        a row that is not an asked set, or a set the regroup did not split (nothing recorded, nothing changed).

        Senua's 0.22.0 review, N1: a Save in the details panel (a saved review) protects the set's group, so its files never
        became books of their own while Keep answered {'kept': 2}. Keep now drops the set's saved panel values with the set:
        they describe the joined book, which no longer exists, so they are not carried to the new books (each is named from
        its own tags or file name, Judy's spec 5.2; the "Entered by you" record of the Save stays under the old set). Save
        stores no per-file value, so none is lost. A set with a job is never split. The press reports success only when
        every file is its own book after the regroup; otherwise everything is rolled back and it is refused."""
        import datetime,groups
        row=self.reviews._row('Audiobooks',id,revision)
        members=row.get('members') or []
        entry=self.needs_you().get(id) or {}
        hold=(entry.get('hold') or {}).get('piece') or {}
        # Ruling 68 (Judy 6.3): "Keep as separate books" also answers a raised folder question: the books its Books line
        # named are kept apart (folder_unit.verdict reads the recorded answer), each checked again on its own.
        folder_question=entry.get('group')=='files_unclear' and (row.get('folder_unit') or {}).get('kind')=='ask' and len(members)>1
        if not folder_question and (entry.get('group')!='part_of_book' or hold.get('piece')!='set' or len(members)<2 or not (row.get('part_set') or row.get('split_book'))):
            raise ValueError('These files are not a set of parts asked about. Nothing was changed.')
        root=self.reviews._source_root(row)
        refused='Keep as separate books was not accepted. Nothing was changed.'
        # One transaction: record the files, drop the set's saved values, regroup, check the split; any failure rolls all
        # of it back. The catalog regroups now, so the row leaves at this answer, not one poll later.
        with self.inventory.group_lock,connect(self.inventory.database) as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT revision,superseded FROM book_groups WHERE root=? AND id=?',(root,id)).fetchone()
            if current is None or current['superseded'] or current['revision']!=revision:raise ValueError('Candidate changed; reload evidence before reviewing')
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='audio_jobs'").fetchone() and any(
                    json.loads(r[0]).get('candidate_id')==id for r in db.execute('SELECT manifest FROM audio_jobs')):raise ValueError(refused)
            groups.record_volumes(db,root,members,groups.KEPT_BASIS+' on '+datetime.date.today().isoformat())
            db.execute("UPDATE book_groups SET review='',approved=0 WHERE id=?",(id,))
            groups.sync(db,root)
            if folder_question:
                kept=len({r[0] for path in [m['path'] for m in members] for r in db.execute(
                    'SELECT c.group_id FROM catalog_group_members c JOIN book_groups g ON g.id=c.group_id WHERE c.root=? AND c.path=? AND g.superseded=0',(root,path))})
                if kept<2:raise ValueError(refused)
            else:
                kept=groups.separate_books(db,root,[m['path'] for m in members])
                if kept!=len(members):raise ValueError(refused)
        self.__dict__.pop('_needs_cache',None)
        return {'kept':kept}

    def delete_preview(self,id,revision,mode='delete',wait=False):
        """Delete book or Remove this copy, step 1 (rulings 23-26; Judy's specs): the files and folders it would remove,
        from the disk now, and any refusal, so a refusal shows before Sergei confirms. mode 'copy' also proves the copy
        against the audiobook in Sorted now. Read-only. wait (a queued Delete book, 0.22.1): a scan or the book's own
        processing is named in 'blocked' instead of refused. See book_delete."""
        import book_delete
        return book_delete.preview(self,id,revision,mode,wait)

    def delete_book(self,id,revision,paths,folders=None,mode='delete'):
        """Step 2: removes exactly the listed files and folders (those the dialog showed), then every record of the book,
        records last. Raises book_delete.DeleteRefused (typed, nothing touched); otherwise {'deleted','bytes','failed',
        'forgotten','folders'}. See book_delete."""
        import book_delete
        if self.draining or self.__dict__.get('_closing'):raise book_delete.DeleteRefused('busy',book_delete.BUSY)
        return book_delete.delete(self,id,revision,paths,folders,mode)

    def after_delete(self,identity):
        """Delete book touched the disk or the catalog: every cached list, count and status is read again."""
        self.__dict__.pop('_needs_cache',None)
        self.invalidate_status()

    def dismiss_attention(self,id,revision):
        """Remove from list (ruling 10): a book with no audio file left stops being listed. No file is touched; a scan
        that finds its files again (a new fingerprint) lists it again."""
        import datetime
        row=self.reviews._row('Audiobooks',id,revision)
        if any(not m.get('missing') for m in row.get('members') or []):raise ValueError('This book still has audio files. Convert what\'s there instead.')
        with connect(self.inventory.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS attention_dismissals(candidate_id TEXT NOT NULL,fingerprint TEXT NOT NULL,dismissed_utc TEXT NOT NULL,PRIMARY KEY(candidate_id,fingerprint))')
            db.execute('INSERT OR IGNORE INTO attention_dismissals VALUES(?,?,?)',(id,row['fingerprint'],datetime.datetime.now(datetime.timezone.utc).isoformat()))
        self.__dict__.pop('_needs_cache',None)
        return {'removed':True}

    def _approval_result(self,id,revision,title=None,author=None,chosen=None,names=None):
        """(row, research result) of Approve with the values shown (typed values win); no network, read-only. names: the
        Edit names editor's series, number, universe and collection (Judy 0.22.2 section 1), over his saved names."""
        def bounded(value,name):
            if value is None:return None
            if not isinstance(value,str) or len(value)>1000 or any(c in value for c in '\x00\r\n'):raise ValueError('The '+name+' must be one line of text')
            return value
        title,author=bounded(title,'title'),bounded(author,'author')
        if names is not None:
            import entered_names
            names={field:value for field,value in names.items() if field in ('series','number','universe','collection')}
            entered_names.check(names)
        row=self.reviews._row('Audiobooks',id,revision)
        # 0.22.1 (item 1, the list read during research): every listed to-do row computes this for its "Goes to" line and
        # Author field, about 0.3 s each (folder siblings, the catalog index, the rules); a page of 100 held rows took
        # 11-30 s while research ran. The answer is reused while the book, the rules and the catalog facts it reads are
        # unchanged; the caller still checks the destination on disk live.
        key=(row['id'],row['revision'],row['fingerprint'],title,author,chosen,json.dumps(names,sort_keys=True,ensure_ascii=False) if names else None,self._approval_stamp())
        cache=self.__dict__.setdefault('_approval_results',{})
        kept=cache.get(key)
        if kept is not None:return row,copy.deepcopy(kept)
        extra={'chosen':chosen} if chosen is not None else {}
        if names:extra['names']=names
        result=self.automatic.research.approved(row,self.reviews._source_root(row),title,author,**extra)
        if len(cache)>=4096:cache.clear()
        cache[key]=copy.deepcopy(result)
        return row,result

    def _approval_stamp(self):
        """What research.approved() reads beyond the book: the catalog revision (folder siblings), the job manifests
        (library and confirmed spellings, the authors already filed), the admitted books and the saved or approved
        metadata (confirmed spellings), and Sergei's author rules with their retractions.

        2026-10-26: the jobs part was count and max(updated); a converting job moves updated several times a second, so
        while anything converted every held row of the list was computed again (0.3 s each). A job's progress is not
        read; its manifest is, and a manifest changes only when a job is added, removed or rewritten (series backfill),
        each of which changes its hash. The retractions and the saved metadata were not in the stamp at all."""
        import hashlib
        with connect(self.inventory.database) as db:
            have={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('book_catalog_revision','audio_jobs','automatic_candidates','author_rules','author_rule_retractions','candidate_context','names_entries')")}
            manifests=hashlib.sha256()
            if 'audio_jobs' in have:
                for job,digest in db.execute('SELECT job_id,manifest_hash FROM audio_jobs ORDER BY job_id'):manifests.update(f'{job}\0{digest}\n'.encode('utf-8','surrogatepass'))
            return (tuple(db.execute('SELECT revision FROM book_catalog_revision WHERE id=1').fetchone() or ()) if 'book_catalog_revision' in have else (),
                    manifests.hexdigest() if 'audio_jobs' in have else (),
                    tuple(db.execute("SELECT count(*),max(attempted) FROM automatic_candidates WHERE state='Queued'").fetchone()) if 'automatic_candidates' in have else (),
                    tuple(db.execute('SELECT count(*),max(saved_utc) FROM author_rules').fetchone()) if 'author_rules' in have else (),
                    tuple(db.execute('SELECT count(*),max(saved_utc) FROM author_rule_retractions').fetchone()) if 'author_rule_retractions' in have else (),
                    tuple(db.execute('SELECT count(*),sum(revision) FROM candidate_context').fetchone()) if 'candidate_context' in have else (),
                    # Edit names (0.22.2): Sergei's saved names and fixes, with their Forgets.
                    tuple(db.execute("SELECT count(*),coalesce(max(saved_utc),'') FROM names_entries").fetchone()) if 'names_entries' in have else ())

    def _approval_destination(self,row,result):
        """(path relative to the output folder, absolute path, reason when there is none) Approve files this result as."""
        if not isinstance(result.get('review'),dict):
            # An unresolved English author has no destination yet (ruling 59). The existing Goes to fallback names
            # the hold; listing a question must not crash or invent a Cyrillic destination.
            reason="Enter the author's English name, then approve." if (result.get('ask') or {}).get('why')=='english_spelling' else '; '.join(dict.fromkeys(result.get('reasons') or []))[:300]
            return '', '', reason or 'Confirm the book title and author.'
        review=dict(result['review'],organization_policy='books-hierarchy-v2')
        output_root=self.reviews._output_root(row,review)
        # Rulings 69 and 71i: the folder Sergei chose for this book replaces the computed folder (organization.plan).
        preview=propose(row['members'][0]['path'],output_root,'audiobook',row['metadata'],review,automatic_facts=self._with_override(row,result.get('metadata_facts')))
        path=self._chosen_display(row,preview.get('path') or '')
        return (self._shown_path(path,output_root) if path else ''),path,('' if path else preview.get('reason',''))

    def routing_preview(self,id,revision,review):
        """The panel's "Unsaved destination preview" for a book (Senua's 0.22.3 review, m14). Ruling 40: a book's names are
        edited on its row only, so the six name fields are the ones its Goes to line files with (research and Edit names),
        never the panel's hidden inputs; the panel's other values are its own (one left empty keeps the row's), planned with
        the row's metadata facts. Read-only; the planner's answer."""
        try:row,result=self._approval_result(id,revision)
        except ValueError as error:
            if 'Candidate changed' in str(error):raise
            return {'confidence':'Needs review','path':'','reason':str(error)}
        names=result.get('review')
        if not isinstance(names,dict):
            return {'confidence':'Needs review','path':'','reason':'; '.join(dict.fromkeys(result.get('reasons') or []))[:300] or 'Confirm the book title'}
        answer=self.reviews.routing_preview('Audiobooks',id,revision,review,names=names,facts=self._with_override(row,result.get('metadata_facts')))
        if isinstance(answer,dict) and answer.get('path'):answer=dict(answer,path=self._chosen_display(row,answer['path']))
        return answer

    def approval_preview(self,id,revision,title=None,author=None,names=None):
        """Judy's "Goes to" line: what Approve would file this book as, with these values. {'path' relative to the output
        folder, 'absolute', 'taken' (a file already there: never overwritten), 'title', 'author', 'reason'}. Read-only.
        names (Edit names, Judy 0.22.2 section 1): the editor's series, number, universe and collection; the answer then
        also has 'place' (the Place line's values, the planner's) and 'applies' (the books a Save would reach)."""
        row,result=self._approval_result(id,revision,title,author,names=names)
        relative,path,reason=self._approval_destination(row,result)
        approval=result['approval']
        answer={'path':relative,'absolute':path,'taken':bool(path and os.path.lexists(path)),
                'title':approval['title'],'author':approval['author'],'collection':approval['collection'],'reason':reason}
        # The series Approve files this book in (Judy 0.23.1 section 8.4; 2026-10-29, Tolkien: «Властелин Колец» 1).
        review=result.get('review') or {}
        if str(review.get('series') or '').strip() and str(review.get('number') or '').strip():
            answer['series']={'name':str(review['series']).strip(),'number':str(review['number']).strip()}
        if names is not None:
            answer['place']=self._place(result.get('review') or {})
            values=dict(names)
            if title is not None:values['title']=title
            if author is not None:values['author']=author
            answer['applies']=self._names_applies(row,values)
        return answer

    # ------------------------------------------------------------------ Edit names (Sergei 2026-10-26; Judy 0.22.2 section 1)
    NAMES_CONVERTING="This book is converting. Its names can't change now."
    NAMES_REFUSED='Save was not accepted. Nothing was changed.'
    NAMES_REPLANNED='Set aside: the names were changed (Edit names). Nothing ran; the book is checked again with the new names.'
    NAMES_REACH_LIMIT=200  # books read to count "Applies to {n} books" (each read is the identity, about 0.3 s)

    class NamesRefused(ValueError):
        """Nothing was saved; code is the page's: 'converting', 'queued', 'changed', 'refused'."""
        def __init__(self,code,message):
            super().__init__(message);self.code=code

    def _names_stamp(self):
        import entered_names
        return entered_names.stamp(self.inventory.database)

    def _names_book(self,id,revision=None):
        """(row, source root, research) of a current book; ValueError ('Candidate changed...') when it is not current."""
        row=self.reviews._row('Audiobooks',id,revision) if revision is not None else self.reviews._row('Audiobooks',id)
        return row,self.reviews._source_root(row),self.automatic.research

    def _names_state(self,row,root,research):
        """(read, scope, now, record): what the files say, where a fix from this book reaches, Sergei's values in force for
        it (entered_names.effective) and its identity record."""
        import entered_names
        read,scope,record=research.names_read(row,root)
        database=self.inventory.database
        now=entered_names.effective(database,row,read,scope) if entered_names.may_apply(database,row) else {}
        return read,scope,now,record

    @staticmethod
    def _place(review):
        """The Place line's values (Judy 0.22.2 section 2): {universe, series, number, collection}, the planner's."""
        return {'universe':str(review.get('universe') or ''),'series':str(review.get('series') or ''),'number':str(review.get('number') or ''),
                'collection':review.get('anthology') is True}

    def _names_job(self,identity):
        """The book's current job as Edit names sees it (Judy 1.3, 1.4): {'state': 'none' | 'pending' | 'running' | 'stopped' |
        'retry_queued' | 'ready', 'row'}. 'running' also while the queue has claimed it or a retry check reads it."""
        import book_restart,m4b_readmission
        with self.jobs._db() as db:
            job_id=book_restart.current_job(db,identity)
            row=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone() if job_id else None
            row=dict(row) if row else None
            request=db.execute("SELECT state FROM m4b_readmissions WHERE parent_job_id=? AND state='queued'",(job_id,)).fetchone() if row and m4b_readmission._exists(db) else None
        if row is None:return {'state':'none','row':None}
        with self.jobs._lock:checking=dict(self.jobs._priority_status)
        if row['state']=='running' or self.jobs.claimed(row['job_id']) or checking.get('state')=='checking' and checking.get('job_id')==row['job_id']:state='running'
        elif row['state']=='pending':state='pending'
        elif row['state']=='completed':state='ready'
        else:
            journal=json.loads(row['journal'] or '{}')
            state='ready' if row['output'] or 'publication_intent' in journal else 'retry_queued' if request else 'stopped'
        return {'state':state,'row':row}

    def _names_lists(self):
        """The editor's pick-lists (Judy 3): the universes and series already in use, from the audiobooks queued or made
        and from Sergei's saved names."""
        import entered_names
        from audio_jobs import CURRENT
        universes,series=set(),set()
        with self.jobs._db() as db:
            for universe,name in db.execute("SELECT json_extract(manifest,'$.metadata.universe'),json_extract(manifest,'$.metadata.series') FROM audio_jobs WHERE "+CURRENT):
                if isinstance(universe,str) and universe.strip():universes.add(universe.strip())
                if isinstance(name,str) and name.strip():series.add(name.strip())
        universes.update(entered_names.in_use(self.inventory.database,'universe'));series.update(entered_names.in_use(self.inventory.database,'series'))
        order=lambda values:sorted(values,key=str.casefold)[:2000]
        return order(universes),order(series)

    def _names_others(self,row,entries,research):
        """[(row, read, scope)] of the other current books a press's fixes may reach: those whose folder, file names or tags
        hold the old text (case variants, in the catalog's evidence), at most NAMES_REACH_LIMIT, each read."""
        sources=sorted({source for kind,_,_,source,_,_ in entries if kind=='fix' and source})
        if not sources:return []
        variants=sorted({form for source in sources for form in (source,source.lower(),source.upper(),source.capitalize(),source.title())})
        with connect(self.inventory.database) as db:
            ids=[r[0] for r in db.execute('SELECT id FROM book_groups WHERE superseded=0 AND id!=? AND ('+' OR '.join(['instr(evidence,?)>0']*len(variants))+') LIMIT ?',
                                          (row['id'],*variants,self.NAMES_REACH_LIMIT))]
        others=[]
        for other_id in ids:
            try:
                other=self.reviews._row('Audiobooks',other_id)
                read,scope,_=research.names_read(other,self.reviews._source_root(other))
            except (ValueError,OSError,KeyError,sqlite3.Error):continue
            others.append((other,read,scope))
        return others

    def _names_applies(self,row,values):
        """Judy 1.5: "Applies to {n} books." The books a Save of these values would change, this one included."""
        import entered_names
        research=self.automatic.research
        root=self.reviews._source_root(row)
        read,scope,now,_=self._names_state(row,root,research)
        entries=entered_names.plan(row,values,read,scope,now)
        if not any(kind=='fix' for kind,*_ in entries):return 1
        key=(row['id'],row['revision'],json.dumps(entries,ensure_ascii=False),self._approval_stamp())
        cache=self.__dict__.setdefault('_names_reach',{})
        if key not in cache:
            if len(cache)>=256:cache.clear()
            cache[key]=1+len(entered_names.reach(entries,self._names_others(row,entries,research)))
        return cache[key]

    def names_editor(self,id,revision):
        """Edit names, opened (Judy 1.1 item 7: one read for one row): {'fields': {title, author, series, number, universe,
        collection}: {'proposal', 'basis'}, 'read': what the files say, 'remembered': [{id, field, from, to}], 'universes',
        'series' (the pick-lists), 'job': the job state (1.3), 'place', 'entered'}. Read-only."""
        import entered_names
        row,root,research=self._names_book(id,revision)
        read,scope,now,record=self._names_state(row,root,research)
        import local_identity
        shown=local_identity.shown(record)
        series=record.get('series') or {}
        guessed={'title':shown.get('title_basis') or '','author':shown.get('author_basis') or '','series':'folder_name' if series.get('folder') else '','number':'folder_name' if series.get('folder') else '',
                 'universe':'','collection':''}
        fields={}
        for field in entered_names.FIELDS:
            value=now[field]['value'] if field in now else read[field]
            fields[field]={'proposal':value,'basis':'entered' if field in now else guessed[field]}
        universes,names=self._names_lists()
        try:
            preview=self.approval_preview(id,revision,names={})
            place,destination=preview['place'],{'path':preview['path'],'absolute':preview['absolute'],'taken':preview['taken'],'reason':preview['reason']}
        except (ValueError,OSError) as error:
            place,destination=self._place({'universe':fields['universe']['proposal'],'series':fields['series']['proposal'],'number':fields['number']['proposal'],
                                           'anthology':fields['collection']['proposal']}),{'path':'','absolute':'','taken':False,'reason':str(error)[:200]}
        job=self._names_job(row['id'])
        return {'fields':fields,'read':read,'remembered':entered_names.remembered(self.inventory.database,row,read,scope),'universes':universes,'series':names,
                'job':job['state'],'place':place,'destination':destination,'entered':entered_names.entered(entered_names.book_values(self.inventory.database,row)),'applies':1}

    def names_save(self,id,revision,values):
        """Edit names, Save (Judy 1.3 to 1.5): records the values as Sergei's lasting names and touches no file. The book's
        job follows (1.4): a queued job that has not started is set aside and its book checked again with the new names
        ('replanned'); a Stopped one runs with them at its next attempt (the queue's claim check); a finished audiobook keeps
        its name ('ready_only'); a converting one refuses with nothing saved. A retry, repair or delete queued from the row
        is the web layer's refusal ('queued'). {'outcome': 'saved' | 'replanned' | 'ready_only' | 'unchanged', 'applies',
        'job', 'entered'}. NamesRefused when nothing was saved."""
        import entered_names
        if self.draining or self.__dict__.get('_closing'):raise self.NamesRefused('refused','Books Arranger is closing. Nothing was changed.')
        entered_names.check(values)
        try:row,root,research=self._names_book(id,revision)
        except ValueError:raise self.NamesRefused('changed','Candidate changed; reload evidence before reviewing') from None
        read,scope,now,_=self._names_state(row,root,research)
        entries=entered_names.plan(row,values,read,scope,now)
        job=self._names_job(row['id'])
        if job['state']=='running':raise self.NamesRefused('converting',self.NAMES_CONVERTING)
        if not entries:return {'outcome':'unchanged','applies':1,'job':job['state'],'entered':entered_names.entered(entered_names.book_values(self.inventory.database,row))}
        applies=1+len(entered_names.reach(entries,self._names_others(row,entries,research)))
        with self.jobs._lock:
            # Under the queue's lock: its claim either came first (refused here, nothing saved) or reads these names.
            job=self._names_job(row['id'])
            if job['state']=='running':raise self.NamesRefused('converting',self.NAMES_CONVERTING)
            try:entered_names.save(self.inventory.database,row,entries)
            except sqlite3.Error:raise self.NamesRefused('refused',self.NAMES_REFUSED) from None
        outcome='saved'
        if job['state']=='pending':
            try:self._names_replan(job['row'])
            except (ValueError,sqlite3.Error):pass  # claimed meanwhile or busy: the claim check re-plans it before it starts
            outcome='replanned'
        elif job['state']=='retry_queued':outcome='replanned'  # the retry's child is checked against these names
        elif job['state']=='ready':outcome='ready_only'
        self.__dict__.pop('_needs_cache',None)
        self.invalidate_status()
        answer={'outcome':outcome,'applies':applies,'job':job['state'],'entered':entered_names.entered(entered_names.book_values(self.inventory.database,row))}
        return answer|self._press_after(id,revision,destination=outcome!='ready_only')

    def _press_after(self,id,revision,destination=True):
        """0.22.3 (Judy 2.2 and 2.3): what a Save or Approve answer adds for the page: the book's list row now ('list_row', its
        status the page names when the book leaves the list) and, for a Save, where it goes with the names now saved
        ('destination', the planner's path; absent when it can't be planned, never guessed). Read-only. It never fails the
        press: any error leaves the extras out (Senua's 0.22.3 review, m1)."""
        try:return self._press_extras(id,revision,destination)
        except Exception:return {}

    def _press_extras(self,id,revision,destination):
        extra={}
        row=self.restart_row(id)
        if row is not None:
            # The fields the row's status is made from; the track list and evidence stay out of the answer (and the queue's).
            extra['list_row']={k:v for k,v in row.items() if k not in ('members','metadata','title_evidence','cover_choices','track_order','included','companions','matching','manual_metadata_sources')}
        if destination:
            try:
                preview=self.approval_preview(id,row['revision'] if row is not None else revision,names={})
                if preview.get('path'):extra['destination']={'path':preview['path'],'absolute':preview.get('absolute') or ''}
            except (ValueError,OSError,sqlite3.Error,KeyError,TypeError):pass
        return extra

    def names_forget(self,id,revision,entry_id):
        """Edit names, Forget (Judy 1.5): takes one remembered correction back, with the rest of its press; behaves like a
        Save of the old values (the same job handling and outcomes) and touches no file. NamesRefused when nothing changed."""
        import entered_names
        if not isinstance(entry_id,str) or not 1<=len(entry_id)<=64:raise ValueError('Forget takes one remembered correction')
        try:row,root,research=self._names_book(id,revision)
        except ValueError:raise self.NamesRefused('changed','Candidate changed; reload evidence before reviewing') from None
        job=self._names_job(row['id'])
        if job['state']=='running':raise self.NamesRefused('converting',self.NAMES_CONVERTING)
        with self.jobs._lock:
            job=self._names_job(row['id'])
            if job['state']=='running':raise self.NamesRefused('converting',self.NAMES_CONVERTING)
            try:taken=entered_names.forget(self.inventory.database,entry_id)
            except sqlite3.Error:raise self.NamesRefused('refused',self.NAMES_REFUSED) from None
        if not taken:raise self.NamesRefused('changed','This correction was already taken back. Nothing was changed.')
        outcome='forgotten'
        if job['state']=='pending':
            try:self._names_replan(job['row'])
            except (ValueError,sqlite3.Error):pass
        self.__dict__.pop('_needs_cache',None)
        self.invalidate_status()
        return {'outcome':outcome,'job':job['state'],'entered':entered_names.entered(entered_names.book_values(self.inventory.database,row))}

    def _names_take_back(self,press):
        """An Approve that saved names and was then refused takes its press back (Forget rows), so nothing stays changed."""
        import entered_names
        rows=entered_names._rows(self.inventory.database)
        for entry in [r for r in entered_names._live(rows) if r['press']==press]:
            try:entered_names.forget(self.inventory.database,entry['entry_id'])
            except sqlite3.Error:pass

    def _names_stale(self,job):
        """AudioJobs' claim check: True when this pending job must not start as planned and goes back to research
        (_names_replan): planned under other names than those now in force (Edit names), a job that converts only part of
        one source folder (ruling 71d), a foreign author still in Cyrillic (ruling 71f) or a destination folder chosen
        since it was planned (ruling 69). Each check reads only the catalog; an unreadable one never stops the queue."""
        for check in (self._names_changed,getattr(self,'_replan_needed',None),getattr(self,'_override_stale',None)):
            if check is None:continue
            try:
                if check(job):return True
            except (ValueError,KeyError,TypeError,OSError,sqlite3.Error):continue
        return False

    def _names_changed(self,job):
        """True when this pending job was planned under other names than those now in force for its book
        (entered_names.digest_for; the job's is in metadata_facts.entered_names). Reads only the store and the book."""
        import entered_names
        manifest=json.loads(job['manifest'])
        planned=((manifest.get('metadata_facts') or {}).get('entered_names') or {}).get('digest') or entered_names.NONE
        try:row=self.reviews._row('Audiobooks',manifest['candidate_id'])
        except (ValueError,KeyError,TypeError):return False  # the book changed: the job's own revision checks refuse it
        return entered_names.digest_for(self.inventory.database,row)!=planned

    REGROUP_REASON='Set aside: this job converted only part of one source folder. Nothing ran; the whole folder is checked again as one book.'
    RECHECK_REASON='Set aside: the author is a foreign name in Cyrillic. Nothing ran; the book is checked again for the English spelling.'

    def _replan_needed(self,job):
        """Rulings 71d and 71f for a pending job about to start: it converts only part of one source folder (the whole
        folder is regrouped as one book), or it files a foreign author in Cyrillic and was planned before the author's
        English spelling was required (re-checked once: the book is researched again and Sergei is asked when no English
        spelling is found). Records the reason for _names_replan. Catalog reads only."""
        manifest=json.loads(job['manifest'])
        with connect(self.inventory.database) as db:
            partial=self._partial_folder_job(db,manifest)
            recheck=not partial and self._foreign_cyrillic_job(db,manifest)
        if partial or recheck:
            self.__dict__.setdefault('_replan_reasons',{})[job['job_id']]=self.REGROUP_REASON if partial else self.RECHECK_REASON
            return True
        return False

    def _partial_folder_job(self,db,manifest):
        """True when a job's sources are only part of the audio files of their one source folder and ruling 68 makes that
        folder one book (groups.folder_verdict is not 'separate'). Whole .m4b files, named anthology volumes (the «Ужасы и
        трэшатинка» volume-1 claim), books whose files Sergei kept separate ("Keep as separate books"), library roots and
        container folders (71a) and folders of whole books or separately tagged novels are never partial. Senua 0.24.0 C1:
        this check reads the same decision as grouping, with the same inputs, so a book grouping keeps apart is never set
        aside here (once at Approve, then again at every engine start)."""
        import folder_unit,anthology_volumes
        sources=[s for s in manifest.get('sources') or [] if isinstance(s,dict) and s.get('path')]
        root=manifest.get('root') or ''
        if not sources or any(Path(s['path']).suffix.lower()=='.m4b' for s in sources):return False
        units={folder_unit.unit_of(s['path']) for s in sources}
        if len(units)!=1 or any(anthology_volumes.folder({'path':s['path']}) for s in sources):return False
        folder,kind=next(iter(units))
        prefix=folder.rstrip('\\/')+os.sep
        rows=[r for r in db.execute("SELECT * FROM files WHERE root=? AND kind='audiobook' AND missing=0 AND substr(path,1,?)=?",(root,len(prefix),prefix))
              if folder_unit.unit_of(r['path'])==(folder,kind) and Path(r['path']).suffix.lower()!='.m4b' and not json.loads(r['metadata'] or '{}').get('arranger_output')]
        # The book the job was made from decides, not the files it converts: files Sergei left out of a whole-folder
        # book ("Approve these files", a saved file choice) are his choice, never a partial folder.
        group=db.execute('SELECT evidence FROM book_groups WHERE id=?',(manifest.get('candidate_id'),)).fetchone()
        members=[m['path'] for m in json.loads(group[0]).get('members') or []] if group else []
        own={os.path.normcase(p) for p in (members or [s['path'] for s in sources])}
        if not any(os.path.normcase(r['path']) not in own for r in rows):return False
        # His "Keep as separate books" answer settles it for the files he kept: this book is one of them, whatever else
        # is in the folder now (a file added later is grouping's question, never a reason to take his answer back).
        kept=groups.kept_parts(db,root)
        if all(p in kept for p in (members or [s['path'] for s in sources])):return False
        items=[groups.member(r) for r in rows]
        scope_of={}
        for item in items:
            found=db.execute('SELECT g.scope FROM catalog_group_members c JOIN book_groups g ON g.id=c.group_id WHERE c.root=? AND c.path=? AND g.superseded=0 LIMIT 1',(root,item['path'])).fetchone()
            scope_of[item['path']]=found[0] if found else item['path']
        for item in items:
            if os.path.normcase(item['path']) in own:scope_of[item['path']]='\x1fthis job'
        return groups.folder_verdict(items,scope_of,kept,folder,{str(root).casefold().rstrip('\\/')})['verdict']!='separate'

    def _foreign_cyrillic_job(self,db,manifest):
        """Ruling 71f: the job files its author in Cyrillic while the name is a foreign one or one the app does not know,
        no Russian original is recorded, and the book was not re-checked yet (one re-check: its research then decides)."""
        import local_identity
        from public_research import RESEARCH_VERSION
        if (manifest.get('metadata_facts') or {}).get('research_version')==RESEARCH_VERSION:return False  # planned under rulings 39/59
        review=manifest.get('metadata') or {}
        author=str(review.get('author') or '')
        if local_identity.script(author)!='cyrillic' or review.get('original_language')=='Russian':return False
        if not (local_identity.foreign_given(author) or local_identity.unknown_given(author)):return False
        rules=self.automatic.research.rules() if getattr(self,'automatic',None) is not None else None
        if not local_identity.foreign_given(author) and rules is not None and rules.keep(author):return False
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audio_job_set_aside'").fetchone() and \
                db.execute("SELECT 1 FROM audio_job_set_aside WHERE candidate_id=? AND kind='recheck'",(manifest.get('candidate_id'),)).fetchone():return False
        return True

    def _release_for_regroup(self,db,identity):
        """71d: the set-aside job's book stops holding its files (its approval and saved values describe one part of the
        folder), and its root regroups at the next catalog read, so the whole folder becomes one book."""
        row=db.execute('SELECT root FROM book_groups WHERE id=?',(identity,)).fetchone()
        db.execute("UPDATE book_groups SET review='',approved=0,changed=0,revision=revision+1 WHERE id=?",(identity,))
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='candidate_context'").fetchone():
            db.execute('DELETE FROM candidate_context WHERE id=?',(identity,))
        if row is not None:db.execute('DELETE FROM book_group_sync WHERE root=?',(row[0],))

    def regroup_partial_jobs(self):
        """Ruling 71d, the existing-data pass (once per engine start, in the background): every unfinished job that converts
        only part of one source folder (pending or stopped, never started publishing: no output, no publication intent,
        not claimed) is set aside with REGROUP_REASON, and its folder regroups as one book. Completed books are never
        touched. Returns the job ids set aside."""
        import book_restart
        from sqlite_retry import transaction
        done=[]
        with connect(self.inventory.database) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audio_jobs'").fetchone():return done
            book_restart.ensure(db)
            rows=[dict(r) for r in db.execute("SELECT * FROM audio_jobs WHERE state IN ('pending','needs attention') AND output IS NULL AND job_id NOT IN (SELECT job_id FROM audio_job_set_aside)")]
            chosen=[]
            for row in rows:
                try:
                    manifest=json.loads(row['manifest']);journal=json.loads(row['journal'] or '{}')
                    if isinstance(journal,dict) and 'publication_intent' in journal:continue
                    if book_restart.current_job(db,manifest['candidate_id'])!=row['job_id']:continue
                    if self._partial_folder_job(db,manifest):chosen.append((row,manifest))
                except (ValueError,KeyError,TypeError,sqlite3.Error):continue
        stamp=__import__('audio_jobs')._now()
        for row,manifest in chosen:
            identity=manifest['candidate_id']
            def write(db,row=row,identity=identity):
                current=db.execute('SELECT state,output,journal FROM audio_jobs WHERE job_id=?',(row['job_id'],)).fetchone()
                if not current or current['state']!=row['state'] or current['output'] is not None or 'publication_intent' in json.loads(current['journal'] or '{}'):raise book_restart.Changed('Job changed')
                if book_restart.current_job(db,identity)!=row['job_id']:raise book_restart.Changed('Newer work')
                revision=(db.execute('SELECT revision FROM book_groups WHERE id=?',(identity,)).fetchone() or [0])[0]
                db.execute("UPDATE audio_jobs SET state='needs attention',reason=?,updated=? WHERE job_id=? AND state IN ('pending','needs attention')",(self.REGROUP_REASON,stamp,row['job_id']))
                book_restart.set_aside(db,row['job_id'],identity,revision,kind='regroup')
                self._release_for_regroup(db,identity)
            try:
                with self.jobs._lock:
                    if self.jobs.claimed(row['job_id']):continue
                    transaction(self.inventory.database,write)
                done.append(row['job_id'])
            except (book_restart.Changed,ValueError,sqlite3.Error):continue
        if done:
            self.__dict__.pop('_needs_cache',None)
            self.invalidate_status()
        return done

    def _names_replan(self,job):
        """A pending job planned under other names is set aside (its row, journal and working files are kept, as Start
        over does) and its book goes back to automatic processing, which researches it with the names in force and queues
        a new job; automatic processing is started if it is not running. A job Sergei approved keeps his title and author
        (saved as his names), so the new plan does not ask him again. Raises ValueError when nothing was changed."""
        import book_restart,entered_names
        from sqlite_retry import transaction
        manifest=json.loads(job['manifest']);identity=manifest['candidate_id']
        try:
            row=self.reviews._row('Audiobooks',identity)
            approval=(self.reviews._context(row) or {}).get('user_approval')
        except (ValueError,KeyError,TypeError):row,approval=None,None
        if row is not None and isinstance(approval,dict) and isinstance(approval.get('values'),dict):
            values={field:approval['values'][field] for field in ('title','author') if isinstance(approval['values'].get(field),str) and approval['values'][field].strip()}
            if values:
                try:
                    read,scope,now,_=self._names_state(row,self.reviews._source_root(row),self.automatic.research)
                    entries=[entry for entry in entered_names.plan(row,values,read,scope,now) if entry[0]=='book']
                    if entries:entered_names.save(self.inventory.database,row,entries)
                except (ValueError,OSError,sqlite3.Error):pass
        stamp=__import__('audio_jobs')._now()
        # Why the claim check set it aside (_names_stale): names, one part of a source folder (71d), a foreign author in
        # Cyrillic (71f) or a folder chosen since (69). The set-aside kind keeps the reason on record.
        reason=self.__dict__.setdefault('_replan_reasons',{}).pop(job['job_id'],self.NAMES_REPLANNED)
        kind={self.REGROUP_REASON:'regroup',self.RECHECK_REASON:'recheck'}.get(reason,'names')
        def write(db):
            book_restart.ensure(db)
            current=db.execute('SELECT state FROM audio_jobs WHERE job_id=?',(job['job_id'],)).fetchone()
            if not current or current[0]!='pending':raise book_restart.Changed('Job changed')
            if book_restart.current_job(db,identity)!=job['job_id']:raise book_restart.Changed('Newer work')
            facts=book_restart.book(db,identity)
            if not facts:raise book_restart.Changed('Book changed')
            db.execute("UPDATE audio_jobs SET state='needs attention',reason=?,updated=? WHERE job_id=? AND state='pending'",(reason,stamp,job['job_id']))
            book_restart.set_aside(db,job['job_id'],identity,facts['revision'],kind=kind)
            book_restart.reset_automatic(db,identity,facts['revision'],facts['fingerprint'])
            if kind=='regroup':self._release_for_regroup(db,identity)
        with self.jobs._lock:
            if self.jobs.claimed(job['job_id']):raise book_restart.Changed('Job claimed')
            transaction(self.inventory.database,write)
        self.__dict__.pop('_needs_cache',None)
        automatic=getattr(self,'automatic',None)
        if automatic is not None and hasattr(automatic,'requeue'):
            automatic.requeue(identity)
            if hasattr(automatic,'request_start'):automatic.request_start()
        self.invalidate_status()

    def answer_same_author(self,id,revision,choice,press=None):
        """Ruling 12: Sergei's answer to this book's "Same author?" question becomes a lasting rule (same: the new name
        files under the existing author; different: the new name is a separate author, never asked again). Returns the
        author to file this book under. Only an explicit choice teaches a rule. press (the Approve carrying the answer,
        0.22.3): the rule's id is recorded there and his other books are not requeued yet; the Approve takes the rule
        back if it is refused, and requeues them once it is accepted."""
        import author_rules
        if choice not in ('same','different'):raise ValueError('Choose Same author or Different author')
        row=self.reviews._row('Audiobooks',id,revision)
        record=self.automatic.candidate(row) or {}
        question=record.get('ask') or {}
        if question.get('kind')!='same_author':raise ValueError('This book has no Same author? question. Nothing was changed.')
        title=(((question.get('fields') or {}).get('title') or {}).get('proposal') or row.get('title_clue') or '')
        with connect(self.inventory.database) as db:
            author_rules.setup(db)
            if choice=='same':rule=author_rules.append(db,'same_as',question['new'],target=question['existing'],actor='user',source='Sergei (Same author?)',question=title)
            else:rule=author_rules.append(db,'keep',question['new'],actor='user',source='Sergei (Same author?)',question=title)
        if press is not None:press['rule_id']=rule
        else:self._continue_after_rule(skip=id)
        return question['existing'] if choice=='same' else question['new']

    def _english_spelling_answer(self,id,revision,author):
        """Ruling 39: Approve on a book asked for the English spelling of a foreign author credited only in Cyrillic is
        Sergei's answer for that author, kept as a lasting rule (once per author): the English name he typed or chose
        files every book of that credit under it (same_as, surname first). Ruling 59 requires an English answer;
        approving the Cyrillic name as shown keeps the question. Returns the rule to save ({'kind', 'credit', 'target',
        'title'}) or None; nothing is written here (Senua's 0.22.2 review, m7: only an accepted Approve saves it)."""
        import author_rules,local_identity
        automatic=getattr(self,'automatic',None)
        if automatic is None or not hasattr(automatic,'candidate'):return None
        try:row=self.reviews._row('Audiobooks',id,revision)
        except ValueError:return None
        ask=(automatic.candidate(row) or {}).get('ask') or {}
        credit=local_identity.text(ask.get('credit'))
        if ask.get('kind')!='author_unclear' or ask.get('why')!='english_spelling' or not credit:return None
        typed=local_identity.text(author) if author is not None else ''
        if local_identity.script(typed)!='latin':
            raise ValueError('Enter the author\'s English name, then approve. Nothing was changed.')
        title=(((ask.get('fields') or {}).get('title') or {}).get('proposal') or row.get('title_clue') or '')
        if typed and author_rules.key(typed)!=author_rules.key(credit):
            return {'kind':'same_as','credit':credit,'target':local_identity.surname_first(typed)[0],'title':title}
        return {'kind':'keep','credit':credit,'target':None,'title':title}

    def _answer_english_spelling(self,id,answer):
        """Saves the rule _english_spelling_answer planned, once the Approve that carries it is accepted, and researches
        his other books of that credit again now."""
        import author_rules
        if not answer:return
        with connect(self.inventory.database) as db:
            author_rules.setup(db)
            if answer['kind']=='same_as':
                author_rules.append(db,'same_as',answer['credit'],target=answer['target'],actor='user',source='Sergei (English spelling, ruling 39)',question=answer['title'])
            else:author_rules.append(db,'keep',answer['credit'],actor='user',source='Sergei (English spelling, ruling 39)',question=answer['title'])
        self._continue_after_rule(skip=id)

    def learned_author_rules(self):
        """0.22.3 (Judy 4.1, Senua M5): the rules research learned online (ruling 39) that are in force, newest first, for
        the page's list with Take back. Read-only."""
        import author_rules
        return author_rules.learned(self.inventory.database)

    def retract_author_rule(self,rule_id):
        """Senua's 0.22.0 review, m6: Sergei takes back one author rule, a seed included (author_rules.retract). Every held
        book whose research it decided is researched again, so it is asked again. Touches no file. Raises ValueError
        with nothing changed; returns {'retracted', 'requeued'}."""
        import author_rules
        with connect(self.inventory.database) as db:author_rules.retract(db,rule_id,actor='user',source='Sergei (taken back)')
        return {'retracted':rule_id,'requeued':len(self._continue_after_rule())}

    def _continue_after_rule(self,skip=None):
        """Futaba's 0.22.0 QA, M-1: a run visits a book once, so a book whose question a new rule answers (the partner of a
        "Same author?" answer) stayed held and listed nowhere ("Still checking") until a new run's scan: Start continued
        the saved run, which had passed it. Every other current book without a job whose research the new rules decide
        (author_rules.Rules.changed_for: a credit or folder it asked about) is put back on the run's list: researched in
        this run, or in the saved run when it continues (AutomaticProcessing.requeue). Returns the ids put back."""
        import author_rules
        database=self.inventory.database
        rules=author_rules.load(database)
        automatic=getattr(self,'automatic',None)
        if rules is None or automatic is None or not hasattr(automatic,'requeue'):return []
        with connect(database) as db:
            have={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'automatic_candidates' not in have or 'book_groups' not in have:return []
            current={r[0] for r in db.execute('SELECT id FROM book_groups WHERE superseded=0')}
            jobs={r[0] for r in db.execute("SELECT json_extract(manifest,'$.candidate_id') FROM audio_jobs")} if 'audio_jobs' in have else set()
            records=db.execute("SELECT id,result FROM automatic_candidates WHERE state IN ('Held','Waiting for source')").fetchall()
        back=[]
        for record in records:
            if record['id']==skip or record['id'] not in current or record['id'] in jobs:continue
            try:result=json.loads(record['result'])
            except (TypeError,ValueError):continue
            if isinstance(result,dict) and 'rules_generation' in result and rules.changed_for(result):
                automatic.requeue(record['id']);back.append(record['id'])
        self.__dict__.pop('_needs_cache',None)
        return back

    def approve_book(self,id,revision,title=None,author=None,without_missing=False,choice=None,path=None,names=None):
        """Sergei's Approve (rulings 6a, 6b, 10, 11a): converts if needed, renames and moves the book to its Audiobooks
        Sorted folder with the values shown (typed values win and are saved as "Entered by you"). without_missing:
        Convert what's there, leaving out the files missing from disk. choice ('same' / 'different'): his answer to the
        book's Same author? question, saved as a rule first (ruling 12) and used as the author (not a typed value). path:
        the "Goes to" line the row showed (relative to the output folder); a different destination now refuses (Senua's
        0.22.0 review, m1: the path shown is the path used). names (Edit names, Judy 0.22.2 1.1: "Approve records and
        approves"): the open editor's values, saved as his lasting names first, taken back if the approval is refused.
        Raises ValueError with the reason it is refused."""
        if names is None:return self._approve_book(id,revision,title,author,without_missing,choice,path)
        import entered_names
        values={field:value for field,value in names.items() if field in ('series','number','universe','collection')}
        if title is not None and str(title).strip():values['title']=title
        if author is not None and str(author).strip():values['author']=author
        entered_names.check(values)
        if self.draining:raise ValueError('Books Arranger is closing. Nothing was changed.')
        row,root,research=self._names_book(id,revision)
        read,scope,now,_=self._names_state(row,root,research)
        entries=entered_names.plan(row,values,read,scope,now)
        # Ruling 57: an Approve's corrected series belongs to this book, never the author's other books (M12).
        entries=[entry for entry in entries if not (entry[0]=='fix' and entry[1]=='series')]
        press=entered_names.save(self.inventory.database,row,entries) if entries else ''
        approval={}
        try:return self._approve_book(id,revision,title,author,without_missing,choice,path,names=values,press=approval)
        except BaseException as error:
            if approval.get('accepted') or approval.get('answered'):raise  # queued (M4), or answered with the series next (M10): his names stay
            if press and (self.draining or self.__dict__.get('_closing')):
                # Ruling 35: closing is no reason to lose his input; the names stay saved for the next session.
                raise ValueError('Books Arranger is closing. Your names are saved; approve again after it restarts.') from error
            if press:self._names_take_back(press)
            raise

    def _approve_book(self,id,revision,title=None,author=None,without_missing=False,choice=None,path=None,names=None,press=None):
        # 0.22.3 (Sergei 2026-10-27; the m7 pattern): his Same author? answer is saved before the approval is built, because
        # the approval files the book by that rule, and taken back if this Approve is refused (the path changed, the name is
        # taken, a safety hold, closing). Once it is accepted, his other books the answer decides are requeued; once it is
        # refused, the books the run researched while the answer was in force are (_drop_answer_rule, m15).
        # Senua's 0.22.3 review, m1 and M4: the undo covers only the refusal. approve_automatic marks the press accepted
        # (press['accepted']) the moment it queues the job; what raises after that inside it (the row read, the stop check,
        # starting the queue) or after it (the extras) neither reports a refusal nor takes an answer or a name back.
        press={} if press is None else press
        try:answer=self._approve_once(id,revision,title,author,without_missing,choice,path,names,press)
        except BaseException:
            if press.get('rule_id') and press.get('answered'):
                # M10: the press answered his Same author? question and the series is asked next: the rule stays.
                try:self._continue_after_rule(skip=id)
                except Exception:pass
            elif press.get('rule_id') and not press.get('accepted'):self._drop_answer_rule(press['rule_id'],skip=id)
            raise
        if press.get('rule_id'):
            try:self._continue_after_rule(skip=id)
            except Exception:pass  # the next run's scan researches them; the Approve stands
        return answer

    def _drop_answer_rule(self,rule_id,skip=None):
        """The rules are append-only: the refused press's answer gets an app retraction (actor 'app'), and Rules drops the two
        together, so the row in force before the press decides again (Senua's 0.22.3 review, M1). A newer rule meanwhile
        stays in force. A book the run researched while the answer was in force is put back on the run (m15; changed_for
        counts the undo, m13), as the accepted press puts back the books its answer decides; skip: the refused book."""
        import author_rules
        try:
            with connect(self.inventory.database) as db:author_rules.retract(db,rule_id,actor=author_rules.APP_RETRACTION,source='Approve refused; the answer it carried is not kept')
        except ValueError:pass
        self.__dict__.pop('_needs_cache',None)
        try:self._continue_after_rule(skip=skip)
        except Exception:pass  # the next run's scan researches it; the refusal stands as it is

    def _approve_once(self,id,revision,title,author,without_missing,choice,path,names,press):
        import datetime
        if self.draining:raise ValueError('Books Arranger is closing. Nothing was changed.')
        chosen=None
        if choice is not None:
            chosen=self.answer_same_author(id,revision,choice,press=press)
            if author is not None:chosen=None
        # Senua's 0.22.2 review, m7: the English-spelling answer is planned now and saved only once this Approve is accepted
        # (below); a refused Approve (the path changed, the name is taken, a safety hold) leaves no rule and requeues nothing.
        spelling=self._english_spelling_answer(id,revision,author)
        row,result=self._approval_result(id,revision,title,author,chosen,names=names)
        import local_identity
        approved_author=(result.get('approval') or {}).get('author') or ''
        if local_identity.script(approved_author)=='cyrillic' and (result.get('work') or {}).get('original_language')!='ru' \
                and (local_identity.foreign_given(approved_author) or local_identity.unknown_given(approved_author)):
            # Ruling 59 for every Approve, "Approve this order" included (POST-023-01: «Джин Вулф» was filed in Cyrillic
            # because the guard needed an old keep rule, and «джин» was no known first name). A foreign first name in
            # Cyrillic never files without its English spelling, rule or no rule. A first name the app does not know
            # («Наиль», «Цысинь»): a keep answer (research found Russian, or his own) or the name he typed in this
            # Approve settles it; otherwise the English spelling is asked first.
            rules=self.automatic.research.rules()
            settled=not local_identity.foreign_given(approved_author) and (author is not None and str(author).strip() or rules is not None and rules.keep(approved_author))
            if not settled:
                raise ValueError('Enter the author\'s English name, then approve. Nothing was changed.')
        if path is not None and result.get('review'):
            relative,_,_=self._approval_destination(row,result)
            if os.path.normcase(os.path.normpath(relative or '.'))!=os.path.normcase(os.path.normpath(str(path) or '.')):
                raise ValueError('Destination changed since it was shown: it is now '+(relative or 'not set')+'. Nothing was changed.')
        include=None
        if without_missing:
            present=[m['path'] for m in row['members'] if not m.get('missing') and not m.get('error')]
            if not present:raise ValueError('No audio file of this book is left to convert')
            include=set(present)
        safety=[r for r in result.get('reasons',[]) if r in self.APPROVAL_SAFETY_REASONS and not (include and r=='Source files unavailable or unreadable')]
        if safety:raise ValueError('; '.join(dict.fromkeys(safety)))
        if not result.get('work') or not result.get('review'):
            # «Спящие красавицы» (2026-10-26): never the bare sentence; the reason the research gave, else the identity.
            raise ValueError("Approve was not accepted: the app couldn't read this book's identity from its files"+(' ('+'; '.join(dict.fromkeys(result.get('reasons') or []))[:300]+')' if result.get('reasons') else '')+'. Type its title and author, then approve. Nothing was changed.')
        # Senua's 0.22.3 review, M10 (rulings 52 and 53): an Approve that answered another question ("Same author?", the
        # English spelling, an author choice, a hold) is no answer to the series question. While the book's series is still
        # unconfirmed and not his, his answer is kept, the book is checked again with the author settled, and its series
        # question comes next: nothing is filed, and its set is not answered.
        automatic=getattr(self,'automatic',None)
        held=((automatic.candidate(row) or {}).get('ask') if automatic is not None and hasattr(automatic,'candidate') else None) or {}
        series_answered=held.get('why')=='title_series' and isinstance(held.get('split'),dict)
        if (result.get('approval') or {}).get('series_question') and not series_answered:
            self._answer_then_ask_series(row,title,author,names,spelling,press,held)
        # Futaba's 0.22.0 QA, m-9: a name taken since the row was shown refused only in build_manifest, after the approval
        # (the review, "Approved by you", the track order) was written, so the row said "Nothing was changed" while the book
        # left the to-do list until the next Start. The destination is checked before anything is written; the late check
        # in build_manifest stays (and the publication itself never overwrites).
        _relative,destination,_reason=self._approval_destination(row,result)
        if destination and os.path.lexists(destination):raise ValueError('An audiobook already exists at this path; nothing was overwritten')
        approval=result['approval']
        files=[m['path'] for m in sorted(row['members'],key=lambda m:m.get('order') or 0) if include is None or m['path'] in include]
        ctx=self.reviews._context(row)
        if ctx.get('track_actor')=='user' and isinstance(ctx.get('track_order'),list) and isinstance(ctx.get('included'),list):
            # The order and files he saved in the panel (approve_automatic applies the same choice).
            by_key={member_key(m['path']):m['path'] for m in row['members']}
            files=[by_key[k] for k in ctx['track_order'] if k in ctx['included'] and k in by_key and (include is None or by_key[k] in include)]
        approved_by={'actor':'user','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'values':{'title':approval['title'],'author':approval['author']},
                     'typed':list(approval['typed']),'collection':approval['collection'],'files':files,'without_missing':bool(include)}
        result['reasons']=[]
        # Senua's 0.22.0 review, m4: closing or draining the app stops a press still checking the files (hashes, probes).
        stop=threading.Event();presses=self.__dict__.setdefault('_approve_stops',set());presses.add(stop)
        if self.draining or self.__dict__.get('_closing'):stop.set()
        try:fresh,job=self.approve_automatic(row,result,stop,self.automatic.research.client,approved_by=approved_by,include=include,queued=press)
        except Exception as error:
            # Senua's 0.22.3 review, M4: once the job is queued the Approve is accepted. Pause still settling (Start refused),
            # Quit arriving (the press's stop) or a failed row read leave the job queued: it is never reported as refused.
            if not press.get('accepted'):
                if isinstance(error,InterruptedError):raise ValueError('Books Arranger is closing. The book was not approved.') from None
                raise
            fresh,job=self._queued_row(id),press['job_id']
        finally:presses.discard(stop)
        press['accepted']=True
        # The book is approved: his English-spelling answer becomes his rule for the author (m7). A failure to save it never
        # turns the accepted Approve into a refusal; the author's other books then ask again.
        try:self._answer_english_spelling(id,spelling)
        except Exception:pass
        try:self.automatic._record(fresh,'Queued',dict(result,user_approval=approved_by))
        except Exception:pass  # the job is queued; the automatic record only drives the list's status line
        return {'row':fresh,'job_id':job}|self._press_after(id,None,destination=False)

    class SeriesAsked(ValueError):
        """His answer is saved; this book still needs its explicit series answer, with no queued job."""
        code='series_needed'
        def payload(self):return {'saved':True,'code':self.code,'message':str(self)}

    SERIES_ASKED='Answer saved. This book still needs its series confirmed. Enter Series and Number, then press Approve. This book has not been queued or filed.'

    def _answer_then_ask_series(self,row,title,author,names,spelling,press,held):
        """Keep the author answer, including an unchanged proposal, then wait for this book's explicit Series/Number and Approve.
        Rulings 56 and 57: never start or resume a run, and never answer another book's series question."""
        import entered_names
        values={field:value for field,value in (('title',title),('author',None if spelling else author)) if value is not None}
        book,root,research=self._names_book(row['id'],row['revision'])
        read,scope,now,_=self._names_state(book,root,research)
        entries=entered_names.plan(book,values,read,scope,now) if names is None else []
        if not spelling and not press.get('rule_id') and not any(entry[1]=='author' for entry in entries) and 'author' not in now:
            # Approve as shown answers the author too. An empty author is an explicit no-author answer (ruling 11).
            proposal=author if author is not None else (((held.get('fields') or {}).get('author') or {}).get('proposal') or '')
            entries.append(('book','author',str(proposal),'','',''))
        if entries:entered_names.save(self.inventory.database,book,entries)
        if spelling:self._answer_english_spelling(row['id'],spelling)
        press['answered']=True
        # A real automatic hold has until_change=True. Saving the shown answer does not change the file revision;
        # invalidate only this book's cached hold so Start actually researches its saved answer (M11).
        import book_restart
        with connect(self.inventory.database) as db:
            book_restart.reset_automatic(db,row['id'],row['revision'],row['fingerprint'])
        self.__dict__.pop('_needs_cache',None)
        self.automatic.requeue(row['id'])
        raise self.SeriesAsked(self.SERIES_ASKED)

    def _queued_row(self,id):
        """The queued book's row for the Approve's answer (M4); None when it can't be read (the answer leaves it out)."""
        try:return self.reviews.enrich(self.reviews._row('Audiobooks',id))
        except Exception:pass
        try:return self.reviews._row('Audiobooks',id)
        except Exception:return None

    # Sergei's Approve overrides every identity and confidence hold (ruling 6b); these source-gate reasons are safety and
    # stay: unreadable or missing files, an audio format with no encoding decision, a changed collection binding.
    APPROVAL_SAFETY_REASONS=('Source files unavailable or unreadable','Audio format needs an encoding decision','Collection source/component binding changed')

    @operation
    def approve_automatic(self,row,result,stop,client,approved_by=None,include=None,queued=None):
        """Private evidence-gated path. HTTP cannot submit an automatic approval.

        queued (Sergei's Approve, Senua's 0.22.3 review, M4): a dict marked accepted, with the job id, as soon as the job is
        queued; what raises after that (the row read, the stop check, starting the queue) leaves the job queued.

        approved_by (Sergei's Approve, rulings 6a, 6b and 11a; only approve_book passes it): {'actor':'user','at',
        'values','typed','files'}. His approval is the identity: open metadata questions, the local-identity re-check,
        drafts, part sets and the identity/order/membership reasons of the source gate no longer hold the book. Every
        safety gate stays: changed or unreadable sources, the encoding decision, chapters that joining would drop, an
        existing job, never overwriting a destination, media verification and source removal only after the result
        is verified in Sorted. include: the member paths to convert (Convert what's there); None converts all."""
        from source_identity import source_gate,VERSION
        from public_research import allowed_url
        from review_backend import image_kind,source_hash,identity
        from audio_pipeline import generated_artifacts,run_owned,probe
        from encoding_policy import choose_encoding,choose_automatic_encoding
        standing=bool(result.get('metadata_facts'))
        # Rulings 69 and 71i: the folder Sergei chose is frozen with the book's facts, so the preview, the manifest, every
        # rebuild of it and the queued-route check (organization.frozen_plan) all name the same destination.
        if standing:result['metadata_facts']=self._with_override(row,result['metadata_facts'],strict=True)
        if standing:
            from standing_metadata import validate_policy
            validate_policy(row,result['review'],result['metadata_facts'])
        from native_io import VerifiedFile
        from source_cleanup import single_stream
        import shutil
        if stop.is_set():raise InterruptedError()
        if result.get('reasons') or not result.get('work') or not result.get('review'):raise ValueError('Book identity uncertain')
        # Local agreement (Sergei decision 2026-10-12) replaces the fetched credit only for
        # identity; it is re-derived from the current sources below. Media, publication,
        # retirement and recovery checks are unchanged.
        local=bool(standing and result['metadata_facts'].get('identity_basis')=='local_agreement')
        if local:primary=[s for s in result.get('sources',[]) if s.get('kind')=='local_agreement' and s.get('verified_identity')]
        else:primary=[s for s in result.get('sources',[]) if s.get('kind') in ('publisher_or_journal','recording_credit','collection_manifest') and s.get('verified_identity')]
        if not primary:raise ValueError('Author and work not independently verified')
        # No converted-books read in the approval (without_ready, Senua 0.21.2 F31): each enrich below otherwise
        # recomputed the set under group_lock, 10-25 s each on the live catalog, with the status poll and book list
        # waiting, and nothing here reads the audiobook_ready flag it feeds.
        unready=getattr(self.reviews,'without_ready',None)
        with self.reviews.lock,self.inventory.group_lock,(unready() if unready else contextlib.nullcontext()):
            current=self.reviews._row('Audiobooks',row['id'],row['revision']);ctx=self.reviews._context(current)
            if current['fingerprint']!=row['fingerprint']:raise ValueError('Source files changed')
            import metadata_choices
            if approved_by is None:
                decision_row=dict(current,automatic=result)
                metadata_choices.admission(self.reviews.metadata_questions(decision_row,ctx),result['review'])
                if self.automatic.manual_draft(current):raise ValueError('Manual draft retained')
            if self.candidate_status(row['id']):raise ValueError('Audiobook job already exists')
            # Judy 2026-10-24 (0.22.0 review B4): Sergei's Approve uses the order and the files he saved in the panel
            # (track_actor 'user', this revision); without them, every file in the catalog's order, as before.
            saved=None
            if approved_by is not None and ctx.get('track_actor')=='user':
                keys=[member_key(m['path']) for m in current['members']];order=ctx.get('track_order');chosen=ctx.get('included')
                if isinstance(order,list) and sorted(order)==sorted(keys) and isinstance(chosen,list) and chosen and set(chosen)<=set(keys):saved=(order,chosen)
            if include is not None:
                # Convert what's there (ruling 10): only the present files named by the press; the left-out ones are reported.
                chosen=[m for m in current['members'] if m['path'] in include]
                if not chosen or len(chosen)!=len(include) or any(m.get('missing') or m.get('error') for m in chosen):raise ValueError('Source files changed')
                gate_row=dict(current,members=chosen)
            else:gate_row=current
            if saved:
                by_key={member_key(m['path']):m for m in gate_row['members']}
                ordered=[by_key[k] for k in saved[0] if k in saved[1] and k in by_key]
                if not ordered:raise ValueError('Source files changed')
                gate_row=dict(gate_row,members=ordered)
            if approved_by is not None:pass  # Sergei's values are the identity (bound to this fingerprint above)
            elif local:
                from local_identity import revalidate,folder_siblings,catalog_index
                # Any failure to read the folder contents holds this book; it never stops the run.
                try:
                    siblings=folder_siblings(self.inventory.database,current,self.reviews._source_root(current))
                    index=catalog_index(self.inventory.database,self.reviews._source_root(current));readers=index['readers']
                    rules=__import__('author_rules').load(self.inventory.database)
                except Exception:raise ValueError("Folder contents could not be checked; local identity held") from None
                revalidate(current,self.reviews._source_root(current),result['metadata_facts']['local_agreement'],siblings,readers,index,rules)
            reasons=source_gate(gate_row,result['work'])
            if approved_by is not None:reasons=[r for r in reasons if r in self.APPROVAL_SAFETY_REASONS]
            if reasons:raise ValueError('; '.join(reasons))
            paths=[m['path'] for m in gate_row['members']]
            with contextlib.ExitStack() as stack:
                for parent in {str(Path(p).parent) for p in paths}:stack.enter_context(DirectoryBoundary(self.reviews._source_root(current),parent))
                stack.enter_context(ProtectedFiles(paths))
                for m in gate_row['members']:
                    stat=Path(m['path']).stat()
                    if stat.st_size!=m['size'] or stat.st_mtime_ns!=int(m['modified']):raise ValueError('Source files changed')
                if stop.is_set():raise InterruptedError()
                with generated_artifacts(self.reviews.cache) as artifacts:
                    try:
                        profiles=[];own_chapters={}
                        for path in paths:
                            raw_profile=probe(path,self.reviews.cache,stop)
                            member=next(m for m in current['members'] if m['path']==path)
                            observed={k.casefold():v for k,v in raw_profile.get('format',{}).get('tags',{}).items()}
                            catalog={k.casefold():v for k,v in member.get('metadata',{}).get('tags',{}).items()}
                            if observed!=catalog:raise ValueError('Source embedded identity or order evidence changed')
                            streams=[s for s in raw_profile.get('streams',[]) if s.get('codec_type')=='audio']
                            if len(streams)!=1:raise ValueError('Audio format needs an encoding decision')
                            stream=streams[0];profiles.append((stream.get('codec_name'),stream.get('sample_rate'),stream.get('channels'),stream.get('bit_rate'),stream.get('channel_layout')))
                            if Path(path).suffix.lower() in ('.m4b','.m4a'):own_chapters[path]=len(raw_profile.get('chapters') or [])
                        # Sergei 2026-10-13: M4B parts with their own chapters are never joined. Only the .m4b
                        # members of a split book are re-filed (the fact regroups the catalog: each part becomes
                        # its own candidate); any other joined set is held as it is, every member kept together
                        # (Senua R2-M1). Either way this joined attempt is held with every source preserved.
                        chaptered={p:n for p,n in own_chapters.items() if n>1}
                        from split_books import joinable_parts
                        # Rulings 19 and 19a: .m4b parts with their own chapters are joined, every part's chapters kept, when
                        # each part is explicitly marked, when their chapters show one book (research: part_set 'join'), or
                        # when Sergei approved them as one book. Otherwise nothing is joined and nothing is re-filed.
                        joinable=all(Path(p).suffix.lower()=='.m4b' for p in paths) and (joinable_parts(gate_row['members'])
                                  or (result.get('part_set') or {}).get('decision')=='join' or approved_by is not None)
                        if len(paths)>1 and chaptered and not joinable:
                            raise ValueError('Book parts carry their own chapters; joining them would drop those chapters')
                        part=(result['metadata_facts'].get('local_agreement') or {}).get('part_book') if local else None
                        # A file Sergei kept as its own book ("Keep as separate books") is a whole book, not one part of a set.
                        if part and not (current.get('volume_of_set') or {}).get('kept'):
                            # One part of a set is its own book only as a whole .m4b with its own chapters, kept in
                            # copy mode (never re-encoded), and only when EVERY part of the set carries its own
                            # chapters: a set is never published piecemeal (Senua R2-C1, R2-M1).
                            if len(paths)!=1 or Path(paths[0]).suffix.lower()!='.m4b' or own_chapters.get(paths[0],0)<2:
                                raise ValueError('One part of a multi-part set without its own chapters; one part is not the whole book')
                            if (choose_automatic_encoding(profiles,single_m4b=True) or {}).get('mode')!='copy':
                                raise ValueError('A part filed as its own book must keep its chapters without re-encoding')
                            others=[p for p in part.get('members') or [] if p!=paths[0]]
                            if not others or paths[0] not in (part.get('members') or []):raise ValueError('Local identity evidence changed')
                            admitted={tuple(s['path'] for s in j['manifest']['sources']):len(j['manifest'].get('source_chapters') or []) for j in self.jobs.status()['jobs']}
                            for other in others:
                                # A part already admitted as its own book proved its chapters then (its original
                                # may since be retired): the job's frozen chapter plan is the evidence.
                                if admitted.get((other,),0)>1:continue
                                try:count=len(probe(other,self.reviews.cache,stop).get('chapters') or [])
                                except TimeoutError:raise  # a media deadline is transient (0.22.2): the book waits and is tried again
                                except (ValueError,OSError):raise ValueError('Another part of this set could not be checked; the whole set is held') from None
                                if count<2:raise ValueError('Another part of this set has no chapters of its own; the whole set is held (never published piecemeal)')
                        # Split book (v0.15.0): every part must be the same recording profile; the v4
                        # normalizer would otherwise silently resample or upmix one of them.
                        if current.get('split_book') and len({p[:3] for p in profiles})!=1:
                            raise ValueError('Split book parts are different recordings (audio profiles differ)')
                        try:
                            if standing:choose_automatic_encoding(profiles,single_m4b=len(paths)==1 and Path(paths[0]).suffix.lower()=='.m4b')
                            else:choose_encoding(profiles)
                        except (ValueError,TypeError):raise ValueError('Audio format needs an encoding decision') from None
                        fresh=self.reviews.covers('Audiobooks',current['id'],current['revision'],all_embedded=True,stop=stop)
                        if stop.is_set():raise InterruptedError('Automatic cover inspection paused')
                        covers=[c for c in fresh['cover_choices'] if c['source_label'].startswith('Embedded artwork:')]
                        if standing:
                            if covers:
                                selected_cover=covers[0];result['metadata_facts']['cover']={'kind':'embedded'}
                            else:
                                from neutral_cover import neutral_cover
                                neutral=neutral_cover(result['review']['title'],authors=result['metadata_facts']['authors'])
                                raw=neutral['bytes'];kind=image_kind(raw);hash=hashlib.sha256(raw).hexdigest()
                                cover_id=str(uuid.uuid5(uuid.NAMESPACE_URL,current['id']+'neutral:'+hash));path=self.reviews.cache/(cover_id+'.'+kind)
                                with DirectoryBoundary(self.reviews.cache.anchor,self.reviews.cache):
                                    if not path.exists():
                                        with open(path,'xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                                    with ProtectedFiles([path]):
                                        if digest(path,stop)!=hash:raise ValueError('Neutral artwork cache changed')
                                selected_cover={'id':cover_id,'source_label':'Neutral cover','source_url':'','evidence_kind':'Generated neutral label; no edition identity claimed','thumbnail_url':'/api/cover?id='+cover_id,'sha256':hash}
                                context=self.reviews._context(fresh);context['cover_choices']=fresh['cover_choices']+[selected_cover]
                                fresh=self.reviews._write(fresh,context,bump=False)
                                result['metadata_facts']['cover']={'kind':'neutral'}
                            self._recording_review(gate_row,result,stop)  # the files being converted
                        else:
                            covers=[c for c in fresh['cover_choices'] if c['source_label'].startswith('Embedded artwork:')]
                            if len(covers)!=1:raise ValueError('Cover not verified')
                            remote=result['work'].get('cover_url') or ''
                            try:allowed_url(remote)
                            except ValueError:raise ValueError('Cover not verified') from None
                            raw=client.read(remote,stop,{'remaining':1});kind=image_kind(raw);hash=hashlib.sha256(raw).hexdigest()
                            remote_id=str(uuid.uuid5(uuid.NAMESPACE_URL,current['id']+'public-cover:'+hash));path=self.reviews.cache/(remote_id+'.'+kind)
                            with DirectoryBoundary(self.reviews.cache.anchor,self.reviews.cache):
                                if not path.exists():
                                    with open(path,'xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                                with ProtectedFiles([path]):
                                    if digest(path,stop)!=hash:raise ValueError('Cover evidence bytes changed')
                                    ffmpeg=shutil.which('ffmpeg')
                                    if not ffmpeg:raise ValueError('Cover decoder unavailable')
                                    def pixels(image):
                                        return run_owned([ffmpeg,'-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1','-protocol_whitelist','file','-f','image2','-i',str(image),'-vf','scale=1200:1200:force_original_aspect_ratio=decrease,scale=96:144:force_original_aspect_ratio=decrease,pad=96:144:(ow-iw)/2:(oh-ih)/2','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],self.reviews.cache,stop,15,96*144*3)
                                    local_path=self.reviews.cover_file(covers[0]['id'])
                                    with ProtectedFiles([local_path]):
                                        first=pixels(local_path);second=pixels(path)
                                        if len(first)!=96*144*3 or len(set(first))<8 or first!=second:raise ValueError('Cover not verified')
                            result['sources'].append({'url':remote,'kind':'matching_cover','sha256':hash,'retrieved_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'verified_identity':True})
                            selected_cover=covers[0]
                        if stop.is_set() or approved_by is None and self.automatic.manual_draft(fresh):raise InterruptedError() if stop.is_set() else ValueError('Manual draft retained')
                        note=('Automatically accepted local-agreement identity (Sergei decision 2026-10-12): embedded tags and file/folder names agree on title and author; only missing fields were searched, unknown optional facts are omitted. All observed sources remain the recording scope.' if local else
                            'Automatically accepted verified work identity and associated author credit under the approved standing rules; source-derived output names, omitted unknown facts and usable embedded/neutral artwork retain honest provenance. All observed sources remain the recording scope.' if standing else 'Automatically accepted fetched public work evidence and independent publisher/journal credit; exact embedded cover pixels match catalog artwork. Source scope remains the observed recording; external recording completeness unknown.')
                        actor='assistant';evidence=result['evidence'];typed={}
                        if approved_by is not None:
                            # Ruling 6b: Sergei's approval, recorded as his: who, when, the exact values, files and order shown.
                            actor='user';typed={k:v for k,v in approved_by['values'].items() if k in approved_by['typed']}
                            note='Approved by you on '+approved_by['at']+' (Sergei 2026-10-24, ruling 6b): "'+approved_by['values']['title']+'" by "'+(approved_by['values']['author'] or 'Разные авторы')+'", '+str(len(paths))+' file(s) in the order shown'+(' (typed: '+', '.join(sorted(approved_by['typed']))+')' if approved_by['typed'] else '')+'. Converted if needed, renamed and moved to Audiobooks Sorted; the originals are removed only after the result is verified there.'
                            evidence=[dict(record,reviewer_actor='user',reviewer_identity='Sergei (Approve)',basis=note) for record in result['evidence']]
                        fresh=self.reviews.save('Audiobooks',fresh['id'],fresh['revision'],result['review'],approve=True,manual_note=note,cover_id=selected_cover['id'],actor=actor,evidence=evidence,automatic_pending={'matcher_version':VERSION,'work_id':result['work']['id']},automatic_facts=result.get('metadata_facts'),
                                              capture_manual=bool(typed),manual_source_values=({'title':typed['title']} if 'title' in typed else {})|({'canonical_author':typed['author']} if 'author' in typed else {}) if typed else None,user_approval=approved_by is not None)
                        context=self.reviews._context(fresh);context['duplicate_review']=copy.deepcopy(result.get('duplicate_review'));context['metadata_approved']=False;context['automatic_pending']={'matcher_version':VERSION,'work_id':result['work']['id']}
                        if approved_by is not None:context['user_approval']=copy.deepcopy(approved_by)
                        fresh=self.reviews._write(fresh,context,bump=False)
                        keys=list(saved[0]) if saved else [m['member_key'] for m in fresh['members']]
                        included=[k for k in keys if k in {m['member_key'] for m in fresh['members'] if m['path'] in paths}]
                        if stop.is_set():raise InterruptedError()
                        fresh=self.reviews.tracks('Audiobooks',fresh['id'],fresh['revision'],keys,included,True,True,len(included)>1,actor=actor,keep_pending=approved_by is not None,
                            evidence_note=('Approved by you: the files shown, in the order shown'+(' (the order and files you saved)' if saved else '')+(' (missing files left out)' if include is not None else '')+'; every included file SHA256 verified.') if approved_by is not None else 'Automatic recording scope: consistent verified work album/source identity; embedded gap-free unique track/disc order, or one self-contained source. All observed source files selected and SHA256 verified; commercial recording completeness unknown.',stop=stop)
                        with self.automatic.lock:
                            if stop.is_set() or approved_by is None and self.automatic.manual_draft(fresh):raise InterruptedError() if stop.is_set() else ValueError('Manual draft retained')
                            context=self.reviews._context(fresh);context['metadata_approved']=True
                            # Pending metadata stays invisible to approval counts/public creation.
                            fresh=self.reviews._write(fresh,context,bump=False)
                            try:
                                manifest=self.reviews.build_manifest('Audiobooks',fresh['id'],fresh['revision'],allow_automatic_pending=True,stop=stop)
                                approved=copy.deepcopy(context);approved.pop('automatic_pending',None)
                                approved['automatic_approval']={'matcher_version':VERSION,'work_id':result['work']['id'],'sources':result['sources'],'approved_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
                                # Queue insertion and final approval become durable together.
                                job=self.jobs.enqueue(manifest,approval_context=(fresh['id'],fresh['revision'],context,approved))
                                # Senua's 0.22.3 review, M4: Sergei's Approve is accepted the moment its job is queued.
                                if queued is not None:queued.update(accepted=True,job_id=job)
                                fresh=self.reviews.enrich(self.reviews._row('Audiobooks',fresh['id'],fresh['revision']))
                            except BaseException:
                                if not self.candidate_status(fresh['id']):
                                    context['metadata_approved']=False;context.pop('automatic_approval',None)
                                    self.reviews._write(fresh,context,bump=False)
                                raise
                    finally:
                        # Producer-pinned diagnostics only; unknown replacements remain preserved.
                        with DirectoryBoundary(self.reviews.cache.anchor,self.reviews.cache):
                            for name,pin in artifacts.items():
                                path=self.reviews.cache/name
                                try:
                                    with VerifiedFile(path,delete=True) as file:
                                        single_stream(path);facts=file.facts()
                                        if facts['links']==1 and facts['size']==pin['size'] and file.sha256()==pin['sha256']:file.dispose()
                                except (ValueError,OSError):pass
        if stop.is_set():raise InterruptedError()
        # Ruling 56: Sergei's Approve saves/queues only; it never starts or resumes the conversion/cleanup queue.
        # Automatic research runs inside an authorized Start and may keep that run's conversion queue moving.
        if approved_by is None:self.resume(recheck=False)
        return fresh,job

    def _request_m4b_readmission(self,job_id,kind,origin=None):
        """A Retry/Repair click is accepted at once and runs right after the current book, in click order."""
        import m4b_readmission
        with self.jobs._lock:
            self._reacquire_admission(job_id=job_id)
            with self.jobs._db() as db:
                existing=m4b_readmission.describe(db,job_id)
                if existing and existing.get('queued_next'):
                    from audio_jobs import RetryRefused
                    raise RetryRefused('A retry request is already saved for this book.')
                return m4b_readmission.request(db,job_id,kind,time.time(),origin)

    def readmission_status(self,job_ids):
        """{job_id: queued_next/position or refusal} for the book list's shown jobs (read-only)."""
        import m4b_readmission
        if not job_ids:return {}
        with self.jobs._db() as db:return m4b_readmission.status(db,list(job_ids))

    def _next_m4b_readmission(self):
        """audio_jobs worker hook, between books (no operation lock): the job id that runs next, or None."""
        import m4b_readmission
        return m4b_readmission.next_job(self.jobs._db,self._admit_m4b_readmission,time.time(),self.jobs.report_priority)

    def _admit_m4b_readmission(self,parent_job_id,kind):
        """Worker thread, between books: the same proof routes as an idle click, minus the worker-busy refusal."""
        if self.inventory.worker and self.inventory.worker.is_alive():return {'defer':True,'reason':'Retry checks are waiting for the library scan to finish.'}  # after the scan
        parent=next(iter(self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(parent_job_id,))),None)
        if not parent:return {'requeued':False,'reason':'The failed book is no longer in the queue.','cause':'unknown'}
        if kind=='retry':
            capability=self.producer_recovery.status(parent_job_id)
            if capability['state'] in {'ready','isolated_retained'}:return self._admit_new_retry(parent,recovery=True)
            import failed_m4b_retry
            if not failed_m4b_retry.eligible(parent):return self._admit_new_retry(parent)
            return self._retry_preserved_m4b(parent,time.time(),in_worker=True)
        return self._repair_damaged_m4b(parent,time.time(),in_worker=True)

    def retry_automatic_job(self,job_id,now,resume=True):
        """resume=False: Retry all admits every book first and starts the queue once, after its loop."""
        self._reacquire_admission(job_id=job_id)
        self._no_scan()
        from failed_m4b_retry import eligible
        from audio_jobs import tag_repair_retry
        import m4b_readmission
        parent=next(iter(self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))),None)
        if parent and tag_repair_retry(parent):
            # Iron Inferno: queued once, by itself; a request already saved, refused or admitted is never repeated.
            with self.jobs._db() as db:known=m4b_readmission._exists(db) and db.execute('SELECT 1 FROM m4b_readmissions WHERE parent_job_id=?',(job_id,)).fetchone() is not None
            if not known:
                self._request_m4b_readmission(job_id,'retry','automatic')
                if resume:self._resume_later()
            return {'retryable':False,'requeued':False,'accepted':not known}
        if parent and eligible(parent):
            result=self._retry_preserved_m4b(parent,now)
            if result.get('requeued') and resume:self.resume(recheck=False)  # one requeued book: no re-check of the finished ones
            return result
        result=self.jobs.retry_failed(job_id,now)
        if result.get('requeued') and resume:self.resume(recheck=False)  # one requeued book: no re-check of the finished ones
        return result

    def _m4b_prior_audio(self,job_id):
        """True when an earlier attempt of this job still holds audio working files (.m4b/.wav). A read-only
        listing; ValueError/OSError when the folders cannot be proven. Old attempts predate receipt-owned
        lifecycle cleanup: M4B Retry and Repair never clone a source while that debt is retained.

        A catalog whose staging root was never created holds no working files at all. Until 2026-10-19 the
        boundary below refused the missing root itself ("An inspected destination ancestor is unavailable"), so
        every M4B Retry on such a catalog was refused as a file problem. The root's absence is proven while its
        parent is held, so a root created meanwhile is still listed."""
        job_root=self.stage_root/job_id
        if not os.path.lexists(self.stage_root):
            with DirectoryBoundary(self.stage_root.anchor,self.stage_root.parent):
                if not os.path.lexists(self.stage_root):return False
        with DirectoryBoundary(self.stage_root.anchor,self.stage_root):
            if job_root.exists():
                with DirectoryBoundary(job_root.anchor,job_root):
                    for attempt in job_root.iterdir():
                        if not attempt.is_dir():continue
                        with DirectoryBoundary(attempt.anchor,attempt):
                            if any(p.suffix.lower() in {'.m4b','.wav'} for p in attempt.iterdir()):return True
        return False

    def _m4b_working_clear(self,job_id):
        """Live check for a Retry/Repair refused on working files (fix 'wait'), run on status reads: the same
        listing as _m4b_prior_audio but holding no directory handle, so it never stands in the way of the working-
        file cleanup it waits for. A link or junction reads as not clear. Admission re-runs the strict listing."""
        job_root=self.stage_root/job_id
        try:
            if not job_root.exists():return True
            if job_root.is_symlink() or os.path.isjunction(job_root):return False
            for attempt in job_root.iterdir():
                if attempt.is_symlink() or os.path.isjunction(attempt):return False
                if attempt.is_dir() and any(p.suffix.lower() in {'.m4b','.wav'} for p in attempt.iterdir()):return False
            return True
        except OSError:return False

    def _blocked_working(self,reason,cause=None):
        value={'state':'blocked','bytes':None,'reason':str(reason)[:500]}
        if cause:value['cause']=cause
        return value

    def _working_listing(self,job_id):
        """(listing, has ownership record) of the job's working folder without opening any file: [(attempt folder name,
        [(file name, regular file, size)])] for each attempt folder holding files; a link, junction or unknown item
        anywhere is a ValueError (blocked, never followed). ([], False) when there is no folder."""
        stage=self.stage_root;job_root=stage/job_id
        if not os.path.lexists(job_root):return [],False
        for path in (stage,job_root):
            if os.path.islink(path) or os.path.isjunction(path):raise ValueError('The working folder is a link; the app does not follow links')
        listing=[];marker=False
        with os.scandir(job_root) as entries:
            for entry in entries:
                if entry.name=='ownership.json' and entry.is_file(follow_symlinks=False) and not entry.is_symlink():marker=True;continue
                if entry.is_symlink() or os.path.isjunction(entry.path) or not entry.is_dir(follow_symlinks=False):
                    raise ValueError('An item the app did not create is in the working folder: '+entry.name)
                with os.scandir(entry.path) as names:
                    files=sorted((item.name,item.is_file(follow_symlinks=False) and not item.is_symlink(),item.stat(follow_symlinks=False).st_size) for item in names)
                if files:listing.append((entry.name,files))
        return sorted(listing),marker

    def _working_state(self,row,audio_only=True,fresh=False):
        """Leftover working files of one needs-attention job (RefusedRetry follow-up 2, section 2), read-only and without
        opening a file: None (no leftovers; for an M4B row, audio_only: none that stop Retry/Repair, .m4b/.wav), or
        {'state':'cleanable'|'blocked','bytes','reason','cause'?}. Cleanable means the app's verified disposal
        (working_lifecycle.retire) would remove all of it now: receipt-owned, closed attempts, every file recorded and
        unchanged in size, and the originals still where they were (their copies go only once the originals are
        verified). Anything the app cannot prove reads blocked, never cleanable. A classification is reused while the
        listing is unchanged for WORKING_RECHECK seconds; a clear that failed keeps its folder blocked until it changes."""
        stage=getattr(self,'stage_root',None);job_id=row.get('job_id')
        if stage is None or not isinstance(job_id,str):return None
        try:
            if str(uuid.UUID(job_id))!=job_id:return None
        except ValueError:return None
        try:listing,marker=self._working_listing(job_id)
        except ValueError as error:return self._blocked_working(error)
        except OSError as error:return self._blocked_working('The working folder could not be read: '+str(error))
        if not listing:return None
        names=[name for _,files in listing for name,_,_ in files]
        if audio_only and not any(name.lower().endswith(('.m4b','.wav')) for name in names):return None
        total=sum(size for _,files in listing for _,_,size in files)
        signature=json.dumps([marker,listing])
        with _WORKING_LOCK:
            failed=self.__dict__.setdefault('_working_failed',{}).get(job_id)
            if failed and failed[0]==signature:return self._blocked_working(failed[1])|{'bytes':total}
            cached=self.__dict__.setdefault('_working_cache',{}).get(job_id)
            if not fresh and cached and cached[0]==signature and 0<=time.monotonic()-cached[1]<WORKING_RECHECK:return copy.deepcopy(cached[2])
        value=self._working_classify(row,listing,marker)|{'bytes':total}
        with _WORKING_LOCK:
            cache=self._working_cache
            if len(cache)>=512:cache.clear()
            cache[job_id]=(signature,time.monotonic(),copy.deepcopy(value))
        return value

    TERMINAL_WORKING=('removed','absent_after_intent','not_created')

    def _working_classify(self,row,listing,marker):
        if not marker:return self._blocked_working('The working folder has no ownership record; the app cannot prove these files are its own')
        try:
            with connect(self.inventory.database) as db:
                if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='working_attempts'").fetchone():
                    return self._blocked_working('An earlier attempt has no ownership record; the app cannot prove these files are its own')
                for attempt_id,files in listing:
                    try:valid=str(uuid.UUID(attempt_id))==attempt_id
                    except ValueError:valid=False
                    if not valid:return self._blocked_working('An item the app did not create is in the working folder: '+attempt_id)
                    attempt=db.execute('SELECT * FROM working_attempts WHERE job_id=? AND attempt_id=?',(row['job_id'],attempt_id)).fetchone()
                    if attempt is None:return self._blocked_working('An earlier attempt has no ownership record; the app cannot prove these files are its own')
                    if attempt['producer']!='closed':return self._blocked_working('An earlier attempt did not close cleanly; its files are kept')
                    if attempt['state'] in ('published','published_held'):return self._blocked_working('These files belong to a published audiobook')
                    receipts={r['name']:dict(r) for r in db.execute('SELECT * FROM working_files WHERE job_id=? AND attempt_id=?',(row['job_id'],attempt_id))}
                    for name,regular,size in files:
                        receipt=receipts.get(name)
                        if receipt is None or not regular:return self._blocked_working('A file the app did not record is in the working folder: '+name)
                        if receipt['state'] in self.TERMINAL_WORKING:return self._blocked_working('A removed working-file name was used again: '+name)
                        if receipt['state']=='creation_intended':return self._blocked_working('A file whose creation the app did not finish recording is kept: '+name)
                        if receipt['size']!=size:return self._blocked_working('A working file changed since the app recorded it: '+name)
                        if name.endswith(('.stdout','.stderr','.decode-stderr','.txt')) and size>8*1024*1024:
                            return self._blocked_working('A large diagnostic file is kept as evidence: '+name)
                    present={name for name,_,_ in files}
                    for name,receipt in receipts.items():
                        if receipt['state']=='closed' and name not in present:  # the disposal refuses a file gone without its intent
                            return self._blocked_working('A recorded working file is missing without a removal record: '+name)
        except (sqlite3.Error,KeyError,TypeError) as error:return self._blocked_working('The app could not read its working-file records: '+str(error))
        try:sources=json.loads(row['manifest']).get('sources') or []
        except (TypeError,ValueError,AttributeError):sources=[]
        for item in sources:
            try:info=os.stat(item['path'])
            except (OSError,KeyError,TypeError):
                return self._blocked_working('The original files cannot be reached; their working copies are kept',cause='originals_unreachable')
            # The same facts the disposal compares before it hashes (WorkingLifecycle._input): those the manifest records.
            if 'size' in item and info.st_size!=item['size'] or 'modified' in item and str(info.st_mtime_ns)!=str(item['modified']):
                return self._blocked_working('An original file changed since it was checked; its working copies are kept')
        return {'state':'cleanable','reason':'Leftover working files from an earlier attempt'}

    def _working_targets(self,row,listing):
        """The attempt folders a clear hands to verified disposal, each proven first (the hard safety rule: inside this
        app's own staging root, owned by this job, never an original). BoundaryError, and nothing removed, unless every
        name is a canonical UUID, no folder from the staging root down is a link or junction and each resolves to its own
        place inside the root, the ownership record names this job, every recorded file of each attempt sits directly in
        its own attempt folder, and no recorded file is an original source, the cover or inside a library."""
        from native_io import BoundaryError
        root=ordinary(self.stage_root);job_id=row['job_id']
        try:canonical=str(uuid.UUID(job_id))==job_id
        except (ValueError,TypeError,AttributeError):canonical=False
        if not canonical:raise BoundaryError('Working folder name is not a job identity')
        real_root=os.path.normcase(os.path.realpath(root))
        def inside(path,*parts):
            if os.path.islink(path) or os.path.isjunction(path):raise BoundaryError('A working folder is a link or junction')
            if os.path.normcase(os.path.realpath(path))!=os.path.join(real_root,*[os.path.normcase(part) for part in parts]):raise BoundaryError('A working folder resolves outside the staging root')
        if os.path.islink(root) or os.path.isjunction(root):raise BoundaryError('The staging root is a link or junction')
        job_root=root/job_id;inside(job_root,job_id)
        try:
            with open(job_root/'ownership.json','rb') as stream:owner=json.loads(stream.read(16*1024*1024+1))
        except (OSError,ValueError) as error:raise BoundaryError('Working ownership record unreadable: '+str(error)) from None
        if not isinstance(owner,dict) or owner.get('job_id')!=job_id:raise BoundaryError('Working ownership record names another job')
        manifest=json.loads(row['manifest'])
        protected={os.path.normcase(os.path.abspath(item['path'])) for item in manifest.get('sources') or [] if isinstance(item,dict) and item.get('path')}
        cover=manifest.get('cover') if isinstance(manifest.get('cover'),dict) else {}
        if cover.get('path'):protected.add(os.path.normcase(os.path.abspath(cover['path'])))
        libraries=[ordinary(path) for path in getattr(getattr(self,'inventory',None),'roots',{}).values() if path]
        targets=[]
        with connect(self.inventory.database) as db:
            for attempt_id,_ in listing:
                try:canonical=str(uuid.UUID(attempt_id))==attempt_id
                except (ValueError,TypeError,AttributeError):canonical=False
                if not canonical:raise BoundaryError('Working attempt folder name is not an attempt identity')
                stage=job_root/attempt_id;inside(stage,job_id,attempt_id)
                for receipt in db.execute('SELECT path,name FROM working_files WHERE job_id=? AND attempt_id=?',(job_id,attempt_id)):
                    path=ordinary(receipt['path'])
                    if path.parent!=stage or path.name!=receipt['name']:raise BoundaryError('A recorded working file is outside its attempt folder')
                    if os.path.normcase(os.path.abspath(path)) in protected or any(path.is_relative_to(library) for library in libraries):
                        raise BoundaryError('A recorded working file is an original or inside a library')
                targets.append(attempt_id)
        return targets

    def clear_working_files(self,library,identity,revision,job_id):
        """Clear working files (Sergei, decision B): the app's verified disposal removes the leftover working files of an
        earlier attempt of this book's current job. {'cleared': True, 'bytes', 'already'?, 'row'}; RetryRefused with cause
        'changed', 'busy', 'not_safe' or 'file_problem' otherwise (a 'not_safe' or 'file_problem' clear may have removed
        part of it: verified disposal stops at the first file it cannot prove). Originals are never touched."""
        from audio_jobs import RetryRefused,RETRY_BOOK_CHANGED,CURRENT
        if library!='Audiobooks':raise ValueError('Audiobook operations apply only to Audiobooks')
        rows=self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))
        if not rows or rows[0]['state']!='needs attention' or rows[0]['output'] or json.loads(rows[0]['manifest']).get('candidate_id')!=identity:
            raise RetryRefused(RETRY_BOOK_CHANGED,'changed')
        with connect(self.inventory.database) as db:
            newest=db.execute("SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? AND "+CURRENT+" ORDER BY created DESC, job_id DESC LIMIT 1",(identity,)).fetchone()
            group=db.execute('SELECT revision FROM book_groups WHERE id=?',(identity,)).fetchone() if db.execute("SELECT 1 FROM sqlite_master WHERE name='book_groups'").fetchone() else None
        if not newest or newest[0]!=job_id or not group or group[0]!=revision:raise RetryRefused(RETRY_BOOK_CHANGED,'changed')
        answer=self._clear_working(rows[0])
        self.invalidate_status()
        return answer|{'row':self.restart_row(identity)}

    def _working_kind(self,row):
        """audio_only for the working-file state: True for an M4B job (only .m4b/.wav stop its Retry/Repair)."""
        import m4b_repair
        try:return bool(m4b_repair.eligible(row))
        except Exception:return False

    NOT_SAFE_PLAIN="the app couldn't prove every file in it is its own"

    def _not_safe(self,job_id,reason=None):
        """S10: why the app kept working files and where they are (the full folder path), with what Sergei can do. Judy
        14.6: the reason is a plain-language clause, never an id, a path or an engine message: only the classifier's own
        sentence up to its first colon, else NOT_SAFE_PLAIN."""
        import re
        from audio_jobs import WORKING_NOT_SAFE,WORKING_NOT_SAFE_AT
        reason=str(reason or '').strip()
        if reason.startswith('Working files were kept: '):reason=reason[len('Working files were kept: '):]
        reason=reason.split(': ',1)[0].strip().rstrip('.')
        if not re.fullmatch(r"[A-Za-z][A-Za-z ,;'’-]*",reason):reason=self.NOT_SAFE_PLAIN
        reason=reason[0].lower()+reason[1:] if reason[:1].isupper() and not reason[1:2].isupper() else reason
        try:folder=str(Path(self.stage_root)/job_id)
        except (TypeError,ValueError):folder=''
        return WORKING_NOT_SAFE_AT%(reason,folder) if reason and folder else WORKING_NOT_SAFE

    def _clear_working(self,row):
        from audio_jobs import RetryRefused,WORKING_BUSY,WORKING_FILE_PROBLEM
        from native_io import BoundaryError,FileInUse
        job_id=row['job_id'];audio_only=self._working_kind(row)
        before=self._working_state(row,audio_only,fresh=True)
        if before is None:return {'cleared':True,'bytes':0,'already':True}
        if before['state']!='cleanable':raise RetryRefused(self._not_safe(job_id,before.get('reason')),'not_safe')
        if self.inventory.worker and self.inventory.worker.is_alive():raise RetryRefused(WORKING_BUSY,'busy')
        working=getattr(self,'working',None)
        if working is None or not hasattr(working,'retire'):raise RetryRefused(WORKING_BUSY,'busy')
        failure=None
        try:
            listing,_=self._working_listing(job_id)
            for attempt_id in self._working_targets(row,listing):working.retire(job_id,attempt_id)
        except InterruptedError:failure=('busy','The app was busy; nothing more was removed')
        except sqlite3.Error as error:failure=('busy',str(error))
        # Another program holds a file open (an antivirus scan can): nothing is proven unsafe, and the disposal opens
        # every file of an attempt before it removes any of them. "Try again"; never remembered as blocked below, so
        # the row stays cleanable and clears once the file is released.
        except FileInUse as error:failure=('file_problem',str(error))
        except (BoundaryError,ValueError) as error:failure=('not_safe',str(error))
        except (OSError,RuntimeError) as error:failure=('file_problem',str(error))
        with _WORKING_LOCK:self.__dict__.setdefault('_working_cache',{}).pop(job_id,None)
        after=self._working_state(row,audio_only,fresh=True)
        if failure is None and after is None:
            with _WORKING_LOCK:self.__dict__.setdefault('_working_failed',{}).pop(job_id,None)
            return {'cleared':True,'bytes':before['bytes']}
        cause,reason=failure or ('not_safe',"The app couldn't prove every file in it is its own")  # plain: S10 shows it (Judy 14.6)
        try:
            listing,marker=self._working_listing(job_id)
            if listing and cause=='not_safe':
                with _WORKING_LOCK:self._working_failed[job_id]=(json.dumps([marker,listing]),'Working files were kept: '+reason)
        except (OSError,ValueError):pass
        # S10's reason is the folder's own classification now (plain), never the exception's text.
        raise RetryRefused({'busy':WORKING_BUSY,'file_problem':WORKING_FILE_PROBLEM}.get(cause) or self._not_safe(job_id,(after or {}).get('reason') if (after or {}).get('state')=='blocked' else None),cause)

    def _clear_first(self,job_id,kind='retry'):
        with self.jobs._lock:
            self._reacquire_admission(job_id=job_id)
            return self._clear_first_unmarked(job_id,kind)

    def _clear_first_unmarked(self,job_id,kind='retry'):
        """Retry and Repair clear leftover working files first (decisions A and O10). Only cleanable files are cleared;
        when the clear does not finish nothing is queued (RetryRefused, typed cause). Blocked files are left to the
        row's own rule (no control) and to the worker's admission."""
        from audio_jobs import RetryRefused,RETRY_NOT_CLEARED,REPAIR_NOT_CLEARED
        rows=self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))
        if not rows:return
        row=rows[0];audio_only=self._working_kind(row)
        if not audio_only:
            with self.jobs._db() as db:
                if self.jobs._retry_shape(db,row) is None:return
        state=self._working_state(row,audio_only,fresh=True)
        if not state or state['state']!='cleanable':return
        try:self._clear_working(row)
        except RetryRefused as error:raise RetryRefused(REPAIR_NOT_CLEARED if kind=='repair' else RETRY_NOT_CLEARED,error.cause) from None
        self.invalidate_status()

    def _m4b_working_refusal(self,job_id):
        """The typed refusal when prior working files block an M4B Retry/Repair, else None."""
        try:
            if self._m4b_prior_audio(job_id):
                return {'reason':'Prior audio working files need verified disposal before another source copy','cause':'working_files'}
        except (ValueError,OSError) as error:
            return {'reason':'Prior working-file ownership requires attention: '+str(error),'cause':'file_problem'}
        return None

    def _route_retry_manifest(self,parent,fresh,retention=None,dispose=False):
        import retry_intent
        root=getattr(self.inventory,'output_root',None) or fresh.get('output_root',fresh['root'])
        return retry_intent.bind(parent,fresh,root,retention=retention,dispose=dispose)

    def _admit_new_retry(self,parent,recovery=False):
        """Worker-only normal approval/source checks, then a distinct immutable child."""
        try:
            retained=None;dispose=False
            if recovery:
                capability=self.producer_recovery.status(parent['job_id'])
                if capability['state']=='ready':capability=self.producer_recovery.isolate(parent['job_id'])
                if capability['state']!='isolated_retained':raise ValueError(capability['reason'])
                retained=capability['checkpoint_id'];dispose=capability.get('basis')=='boot_after_attempt'
            else:self.working.admission_clear(parent)
            with contextlib.ExitStack() as retained_lease:
                if retained:retained_lease.enter_context(self.producer_recovery.protect_retained(parent['job_id']))
                manifest=json.loads(parent['manifest'])
                import destination_admission
                with connect(self.inventory.database) as destination_db:
                    destination_hold=destination_admission.current(destination_db,parent,self._destination_policy())
                with connect(self.inventory.database) as db:
                    group=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=?',(manifest['candidate_id'],)).fetchone()
                    context=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(manifest['candidate_id'],)).fetchone()
                if not group or not context:raise ValueError('Current approved review is unavailable')
                fresh=self.reviews.build_manifest('Audiobooks',manifest['candidate_id'],manifest['candidate_revision'],allow_existing_job=True,stop=self.automatic.stop_event)
                fresh=self._route_retry_manifest(parent,fresh,retained,dispose)
                self._destination_preflight(fresh)
                if destination_hold:
                    with connect(self.inventory.database) as destination_db:
                        if destination_admission.current(destination_db,parent,self._destination_policy())!=destination_hold:raise ValueError(destination_admission.STALE)
                child=self.jobs.enqueue(fresh,retry_context=(parent,tuple(group),tuple(context),destination_hold))
                return {'requeued':True,'job_id':child,'parent_job_id':parent['job_id'],'reason':'A separate conversion intent was admitted; the failed intent and old files are retained.'}
        except (ValueError,OSError) as error:return {'requeued':False,'reason':str(error),'cause':'source_changed'}

    def _retry_preserved_m4b(self,parent,now,in_worker=False):
        """Admit one new child, retaining the failed parent's entire durable row.

        A refusal carries a typed cause (retry_refusal.FIXES) from the step that raised it, never from its text.
        """
        self._reacquire_admission(job_id=parent['job_id'])
        from failed_m4b_retry import bind,profile_proof
        result={'retryable':True,'retry_at':now+3600,'requeued':False}
        if not in_worker and self.jobs._thread and self.jobs._thread.is_alive():return result
        manifest=json.loads(parent['manifest'])
        blocked=self._m4b_working_refusal(parent['job_id'])
        if blocked:return result|blocked
        from zone_identifier import readable_source_streams
        import m4b_preservation
        step='file_problem'  # the cause of a ValueError raised by the step running now
        try:
            with contextlib.ExitStack() as holds:
                source=ordinary(manifest['sources'][0]['path'])
                holds.enter_context(DirectoryBoundary(manifest['root'],source.parent))
                held=holds.enter_context(VerifiedFile(source));streams_check=holds.enter_context(readable_source_streams(source,held))
                if held.facts()['links']!=1:raise ValueError('Source alias is not eligible for repaired admission')
                step='unknown'
                module=Path(m4b_preservation.__file__).absolute()
                holds.enter_context(DirectoryBoundary(module.anchor,module.parent))
                module_file=holds.enter_context(VerifiedFile(module))
                step='source_changed'
                with connect(self.inventory.database) as db:
                    group_before=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=?',(manifest['candidate_id'],)).fetchone()
                    context_before=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(manifest['candidate_id'],)).fetchone()
                if not group_before or not context_before:raise ValueError('Reviewed candidate unavailable')
                fresh=self.reviews.build_manifest('Audiobooks',manifest['candidate_id'],manifest['candidate_revision'],allow_existing_job=True,stop=self.automatic.stop_event)
                title=fresh['metadata'].get('title')
                if not isinstance(title,str) or not title:raise ValueError('Approved title unavailable')
                step='file_problem'
                with source.open('rb') as reader:
                    def read_at(offset,count):
                        if self.automatic.stop_event.is_set():raise InterruptedError('Automatic processing stopped')
                        reader.seek(offset);return reader.read(count)
                    try:profile=m4b_preservation.plan(held.facts()['size'],read_at,{'title':title},None)
                    except m4b_preservation.Refused:
                        step='unsupported_file';raise
                step='unknown'
                proof=profile_proof(profile,module_file.sha256())
                step='source_changed'
                fresh=bind(parent,fresh,proof)
                routed=bool(getattr(self.inventory,'output_root',None))
                if routed:fresh=self._route_retry_manifest(parent,fresh)
                with connect(self.inventory.database) as db:
                    group=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=?',(fresh['candidate_id'],)).fetchone()
                    context=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(fresh['candidate_id'],)).fetchone()
                if not group or not context or tuple(group)!=tuple(group_before) or tuple(context)!=tuple(context_before):raise ValueError('Reviewed candidate changed during source proof')
                step='unknown'
                streams_check()
                child=self.jobs.enqueue(fresh,repair_context=(parent,tuple(group),tuple(context)),retry_context=(parent,tuple(group),tuple(context)) if routed else None)
                return result|{'requeued':True,'job_id':child,'parent_job_id':parent['job_id'],'reason':'Source-preserving M4B repair admitted as new work'}
        except InterruptedError:raise
        except (OSError,sqlite3.Error) as error:
            return result|{'reason':'Failed M4B retained: '+str(error),'cause':'file_problem'}
        except ValueError as error:
            return result|{'reason':'Failed M4B retained: '+str(error),'cause':step}

    @operation
    def repair_damaged_m4b(self,job_id,now):
        """Repair entry point, never automatic: accepted at once and admitted by the worker right after the
        current book (m4b_readmission), through _repair_damaged_m4b."""
        self._reacquire_admission(job_id=job_id)
        import m4b_repair
        self._no_scan()
        parent=next(iter(self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))),None)
        if not parent or not m4b_repair.eligible(parent):return {'requeued':False,'accepted':False,'reason':'This book cannot be repaired.'}
        result=self._request_m4b_readmission(job_id,'repair');self.resume()
        return result|{'requeued':False}

    def _repair_damaged_m4b(self,parent,now,in_worker=False):
        """Admit one child job that applies the user-approved, proven M4B damage repair (m4b_repair). The
        failed parent row is kept unchanged; the child is verified like every preserved M4B before
        publication, and originals then follow the normal cleanup and recovery policy."""
        self._reacquire_admission(job_id=parent['job_id'])
        import m4b_preservation,m4b_repair
        from zone_identifier import readable_source_streams
        from audio_jobs import REPAIR_WORKER_BUSY
        result={'requeued':False}
        if not m4b_repair.eligible(parent):return result|{'reason':'This book cannot be repaired.','cause':'unknown'}
        if not in_worker and self.jobs._thread and self.jobs._thread.is_alive():return result|{'reason':REPAIR_WORKER_BUSY}
        manifest=json.loads(parent['manifest'])
        blocked=self._m4b_working_refusal(parent['job_id'])
        if blocked:return result|blocked
        step='file_problem'  # the cause of a ValueError raised by the step running now (typed, never from the text)
        try:
            with contextlib.ExitStack() as holds:
                source=ordinary(manifest['sources'][0]['path'])
                holds.enter_context(DirectoryBoundary(manifest['root'],source.parent))
                held=holds.enter_context(VerifiedFile(source));streams_check=holds.enter_context(readable_source_streams(source,held))
                if held.facts()['links']!=1:raise ValueError('Source alias is not eligible for repaired admission')
                step='unknown'
                module=Path(m4b_preservation.__file__).absolute()
                holds.enter_context(DirectoryBoundary(module.anchor,module.parent))
                module_file=holds.enter_context(VerifiedFile(module))
                step='source_changed'
                with connect(self.inventory.database) as db:
                    group_before=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=?',(manifest['candidate_id'],)).fetchone()
                    context_before=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(manifest['candidate_id'],)).fetchone()
                if not group_before or not context_before:raise ValueError('Reviewed candidate unavailable')
                step='file_problem'
                with source.open('rb') as reader:
                    def read_at(offset,count):
                        reader.seek(offset);return reader.read(count)
                    diagnosis=m4b_repair.diagnose(held.facts()['size'],read_at)
                if diagnosis['state']!='repairable':
                    # refused: the preservation proof refuses the file even with every repair; intact: nothing to repair.
                    return result|{'reason':'No provable repair: '+(diagnosis['reason'] or 'the source is intact'),
                                   'cause':'unsupported_file' if diagnosis['state']=='refused' else 'unknown'}
                step='source_changed'
                fresh=self.reviews.build_manifest('Audiobooks',manifest['candidate_id'],manifest['candidate_revision'],allow_existing_job=True,stop=self.automatic.stop_event)
                fresh=m4b_repair.bind(parent,fresh,diagnosis,module_file.sha256())
                with connect(self.inventory.database) as db:
                    group=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=?',(fresh['candidate_id'],)).fetchone()
                    context=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(fresh['candidate_id'],)).fetchone()
                if not group or not context or tuple(group)!=tuple(group_before) or tuple(context)!=tuple(context_before):raise ValueError('Reviewed candidate changed during source proof')
                step='unknown'
                streams_check()
                child=self.jobs.enqueue(fresh,repair_context=(parent,tuple(group),tuple(context)))
        except InterruptedError:raise
        except (OSError,sqlite3.Error) as error:
            return result|{'reason':'Repair refused: '+str(error),'cause':'file_problem'}
        except ValueError as error:
            return result|{'reason':'Repair refused: '+str(error),'cause':step}
        if not in_worker:self.resume()
        return result|{'requeued':True,'job_id':child,'parent_job_id':parent['job_id'],'damage':diagnosis['damage'],'reason':'Repair admitted as new work'}

    def _recording_review(self,row,result,stop):
        """Full source-byte comparisons only; freshly validate any completed counterpart."""
        from recording_classification import classify_recording
        from audio_pipeline import source_chapters
        def chapter_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        facts=result['metadata_facts'];review=result['review']
        tracks=[]
        for member in row['members']:
            if stop.is_set():raise InterruptedError()
            chapters=source_chapters(member['path'],self.reviews.cache,stop,member['duration']) if Path(member['path']).suffix.lower()=='.m4b' else []
            tracks.append({'source_sha256':digest(member['path'],stop),'size_bytes':member['size'],'chapter_sha256':chapter_hash(chapters)})
        def entry(identity,work_ids,meta,policy,source_tracks,complete=True):
            recording=policy.get('recording_language') or {}
            return {'id':identity,'identity_verified':True,'work_ids':work_ids,'collection_kind':(policy.get('collection') or {}).get('kind','single'),
                'series_volume':meta.get('number') or None,'narrator':{'value':meta.get('narrator',''),'verified':bool(meta.get('narrator'))},
                'recording_language':{'value':recording.get('value'),'verified':recording.get('basis') in ('embedded','recording_credit')},
                'edition':{'value':'','verified':False},'manifest':{'complete':complete,'observed_count':len(source_tracks),'tracks':source_tracks}}
        candidate=entry(row['id'],facts['work_ids'],review,facts,tracks);existing=[];related=[]
        for job in self.jobs.status()['jobs']:
            manifest=job['manifest'];other_id=manifest['candidate_id']
            if other_id==row['id']:continue
            try:other=self.reviews._row('Audiobooks',other_id);context=self.reviews._context(other)
            except ValueError:continue
            policy=context.get('metadata_facts') or {};approval=context.get('automatic_approval') or {}
            work_ids=policy.get('work_ids') or ([approval['work_id']] if approval.get('work_id') else [])
            if sorted(work_ids)!=sorted(facts['work_ids']):continue
            source_tracks=[]
            for source in manifest['sources']:
                chapters=manifest.get('source_chapters',[]) if len(manifest['sources'])==1 and Path(source['path']).suffix.lower()=='.m4b' else []
                source_tracks.append({'source_sha256':source['sha256'],'size_bytes':source['size'],'chapter_sha256':chapter_hash(chapters)})
            record=entry(job['job_id'],work_ids,manifest['metadata'],policy,source_tracks)
            output=job.get('output') or {}
            record.update(approved=bool(context.get('metadata_approved') and not context.get('automatic_pending')),
                completed_verified=job['state']=='completed' and output.get('validation',{}).get('passed') is True,
                current_output_valid=bool(job['state']=='completed' and self._output_valid(output)))
            existing.append(record);related.append({'candidate_id':other_id,'title':manifest['metadata'].get('title',''),'narrator':manifest['metadata'].get('narrator',''),'edition':'','language':policy.get('recording_language',{}).get('value')})
        decision=classify_recording(candidate,existing);marker=decision.get('duplicate_review')
        if marker:
            marker['related']=related;result['duplicate_review']=marker
            context=self.reviews._context(row);context['duplicate_review']=copy.deepcopy(marker)
            self.reviews._write(row,context,bump=False)
        if decision['hold']:raise ValueError('Possible duplicate recording — original sources preserved')
        if decision.get('reuse_job_id'):
            # Proven existing publication may be skipped; do not manufacture a new
            # completed candidate/job or remove this duplicate's original bytes.
            raise ValueError('Identical verified recording already arranged — duplicate sources preserved')
        if decision['classification']=='related_distinct':facts['destination_suffix']=decision['destination_suffix']

    @operation
    def create(self, library, identity, revision):
        self._reacquire_admission(identity=identity)
        with self.reviews.lock, self.inventory.group_lock:
            self._no_scan()
            manifest = self.reviews.build_manifest(library, identity, revision)
            job = self.jobs.enqueue(manifest)
        self.resume()
        return {'job_id':job,'queued':True}

    @operation
    def queue(self, library, candidates):
        queued=[]; excluded=[]
        with self.reviews.lock, self.inventory.group_lock:
            self._no_scan()
            for item in candidates:
                try:
                    manifest=self.reviews.build_manifest(library,item['id'],item['revision'])
                    queued.append(self.jobs.enqueue(manifest))
                except (ValueError,OSError) as error:
                    excluded.append({'id':item['id'],'reason':str(error)})
        if queued:self.resume()
        return {'queued':queued,'excluded':excluded}

    def _no_scan(self):
        if self.inventory.worker and self.inventory.worker.is_alive():
            raise ValueError('Wait for the scan to stop before creating audiobooks')

    @contextlib.contextmanager
    def _review_boundary(self):
        # Both metadata/context writes and candidate revisions share this boundary.
        with self.reviews.lock, self.inventory.group_lock:
            yield

    def _record_source_damage(self,job_id,attempt_id,assessment):
        import reacquire_sources
        with self.reviews.lock,self.inventory.group_lock,self.jobs._lock:
            with connect(self.inventory.database) as db:
                row=db.execute('SELECT manifest,attempt_id FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()
                if not row or row['attempt_id']!=attempt_id:raise ValueError('Diagnostic attempt changed')
                identity=json.loads(row['manifest'])['candidate_id'];snapshot=reacquire_sources._current(db,identity)
                with reacquire_sources.assess_live_sources(snapshot,assessment) as accepted:
                    db.execute('BEGIN IMMEDIATE')
                    reacquire_sources.record_assessment(db,identity,accepted)
                    db.commit()

    def _reacquire_admission(self,identity=None,job_id=None):
        import reacquire_sources
        with connect(self.inventory.database) as db:
            if identity is None:
                row=db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()
                if not row:raise ValueError('Saved audiobook job is unavailable')
                identity=json.loads(row['manifest'])['candidate_id']
            reacquire_sources.require_admission(db,identity)

    def _guard(self, manifest):
        try:
            self._reacquire_admission(identity=manifest['candidate_id'])
            self._no_scan()
            if manifest.get('replacement_id'):
                relation=self.replacements.get(new_job=manifest['job_id'])
                if not relation or relation['id']!=manifest['replacement_id'] or relation['state']!='queued':return False
                with connect(self.inventory.database) as db:raw=self.replacements.raw_job(db,manifest['job_id'])
                frozen={k:v for k,v in manifest.items() if k!='attempt_id'}
                return json.loads(raw['manifest'])==frozen and self._replacement_guard(relation)
            held=getattr(self,'_held_sources',{}).get(manifest['job_id'])  # only while this job's in-place publication holds its source
            current=self.reviews.build_manifest('Audiobooks',manifest['candidate_id'],manifest['candidate_revision'],allow_existing_job=True,**({'held':held} if held else {}))
            # Only what the review decides is compared. The queue and the Retry/Repair admission add job-only fields
            # (JOB_ONLY_FIELDS); until 0.16.10 the m4b_repair binding made every Retry/Repair job fail here. The
            # rebuild re-hashes every source in full at the attempt's first check (later checks in the same attempt
            # compare its fingerprint, 0.21.0 source_proofs), and the repair binding is validated when the job runs.
            if manifest.get('retry_intent'):
                import retry_intent
                root=getattr(self.inventory,'output_root',None) or current.get('output_root',current['root'])
                with connect(self.inventory.database) as db:return retry_intent.guard(db,manifest,current,root)
            from manifest_compatibility import equivalent_manifest
            return equivalent_manifest(current,manifest,ignore_fields=JOB_ONLY_FIELDS)
        except (ValueError,OSError,KeyError):return False

    def _run(self, manifest, stop, checkpoint):
        self._active_producer=(manifest['job_id'],manifest['attempt_id'])
        try:return self._run_media(manifest,stop,checkpoint)
        finally:self._active_producer=None

    def _run_media(self, manifest, stop, checkpoint):
        stages={'Checking sources':'checking sources','Creating audio':'creating','Checking output':'checking'}
        import inplace_m4b
        try:self._require_sorted(manifest['destination']);sorted_destination=True
        except ValueError:sorted_destination=False  # the copy flow then runs, and its cleanup keeps the sources (C2)
        session=None if manifest.get('replacement_id') or not sorted_destination else inplace_m4b.Session(self.inventory.database,manifest['job_id'],manifest['attempt_id'])
        output, validation=create_private(manifest,self.stage_root,stop,lambda stage,info:checkpoint(stages[stage],info),artifact_observer=self.working,in_place=session)
        if isinstance(output,inplace_m4b.Edited):return self._publish_in_place(manifest,output,validation,checkpoint)
        if manifest.get('replacement_id'):
            from replacement_media import verify_replacement
            validation=verify_replacement(manifest,validation,output,output.parent,stop)
        record={}
        def journal(stage, details):
            if stage=='completed':return
            if stage=='copying':self._register(details['temporary'],manifest['job_id'],'temporary')
            if stage=='publishing':
                record.update(job_id=manifest['job_id'],final_path=details['destination'],owned_temp=details['temporary'],
                    sha256=validation['sha256'],size=validation['size'],root=manifest.get('output_root',manifest['root']),
                    candidate_id=manifest['candidate_id'],candidate_revision=manifest['candidate_revision'],
                    validation={'passed':True,**validation},parent_identity=details['parent_identity'])
                checkpoint('publishing',copy.deepcopy(record))
            else:checkpoint(stage,details)
        with ProtectedFiles([output]):
            publish(output,manifest,validation,stop,journal,lambda:self._guard(manifest),self._review_boundary(),report=lambda value:checkpoint('copying',{'progress':value}))
        self._register(record['final_path'],manifest['job_id'],'output',record['sha256'],record['size'])
        return record

    def _publish_in_place(self,manifest,edited,validation,checkpoint):
        """0.21.0: move the verified in-place edit by the 0.20.2 handle-bound no-copy rename, with the same durable
        publication intent and guards as publish(). Every failure before the rename undoes the edit first."""
        from native_io import rename_no_replace,RenamePostconditionError
        from audio_pipeline import ValidationError
        destination=ordinary(manifest['destination']);root=manifest.get('output_root',manifest['root']);renamed=False
        if not hasattr(self,'_held_sources'):self._held_sources={}
        self._held_sources[manifest['job_id']]={os.path.normcase(str(edited.path)):{'sha256':manifest['sources'][0]['sha256'],'source_chapters':validation['preserved_source_chapters']}}
        try:
            with DirectoryBoundary(root,destination.parent,create=True,rename_destination=True) as target:
                if os.path.lexists(destination):raise FileExistsError('An audiobook already exists at this path; nothing was overwritten')
                record=dict(job_id=manifest['job_id'],final_path=str(destination),owned_temp=str(edited.path),sha256=validation['sha256'],size=validation['size'],
                    root=root,candidate_id=manifest['candidate_id'],candidate_revision=manifest['candidate_revision'],
                    validation={'passed':True,**validation},parent_identity=target.identities)
                checkpoint('publishing',copy.deepcopy(record))  # revision guard and durable publication intent
                edited.session.record('publishing')
                with self._review_boundary():
                    if not self._guard(manifest):raise ValidationError('Candidate review changed — review required')
                    # The rename retires the source path: only into the configured output folder (rulings 2 and 1a).
                    try:self._require_sorted(destination)
                    except ValueError as problem:raise ValidationError(str(problem)) from None
                    target.revalidate()
                    try:receipt=rename_no_replace(edited.handle,destination,edited.boundary,target,expected_identity=edited.handle.facts(),
                        expected_size=validation['size'],expected_sha256=validation['sha256'])
                    except RenamePostconditionError:
                        renamed=True;raise
                    renamed=True
            edited.session.record('published',rename=receipt)
        except BaseException as error:
            if renamed:edited.session.record('publishing',postcondition=str(error)[:500])  # recovery and _settle prove the move
            else:edited.undo()
            raise
        finally:
            self._held_sources.pop(manifest['job_id'],None);edited.close()
        self._register(record['final_path'],manifest['job_id'],'output',record['sha256'],record['size'])
        return record

    def _output_valid(self, record, stop=None, pace=None):
        """Resolve immutable receipts under a generation lease before hashing."""
        try:
            bindings=getattr(self,'publication_bindings',None)
            lease=bindings.protect(record) if bindings else contextlib.nullcontext((record,None))
            captured=[]
            with lease as (effective,envelope):
                valid=self._output_valid_at(effective,stop,pace,captured)
            if valid and captured:
                self._validated_outputs[record['job_id']]=tuple(captured[0])
                self._remember_identity(effective,captured[0])
            return valid
        except InterruptedError:raise
        except (ValueError,OSError,KeyError):return False

    def _output_valid_at(self, record, stop=None, pace=None, captured=None):
        """Full check: exact recorded bytes. A stop is raised, never reported as invalid."""
        try:
            root=ordinary(record['root']); final=ordinary(record['final_path'])
            if os.path.normcase(str(root)) not in {os.path.normcase(str(r)) for r in (tuple(self.inventory.source_roots('Audiobooks'))+((self.inventory.output_root,) if getattr(self.inventory,'output_root',None) else ()) if hasattr(self.inventory,'source_roots') else [self.inventory.roots['Audiobooks']])} and not (hasattr(self,'_chosen_root') and self._chosen_root(root,final)):return False
            if final.suffix.lower()!='.m4b' or record['validation'].get('profile') not in {PROFILE,LEGACY_PROFILE,AUTOMATIC_PROFILE}:return False
            with DirectoryBoundary(root,final.parent) as boundary, VerifiedFile(final) as native:
                if record.get('identity') is not None and native.facts()['identity']!=record['identity']:return False
                if record.get('parent_identity')!=[list(i) for i in boundary.identities]:
                    # In-memory records contain tuples, persisted JSON contains lists.
                    if record.get('parent_identity')!=boundary.identities:return False
                valid=fingerprint(final)['size']==record['size'] and verify_digest(final,stop,pace)==record['sha256']
                if valid:
                    identity=file_identity(final)
                    if captured is not None:captured.append(identity)
                return valid
        except InterruptedError:raise
        except (ValueError,OSError,KeyError):return False

    def _output_current(self, record, stop=None, pace=None):
        """Routine check (startup, Start): a book whose file identity is unchanged since its last full
        verification is current; anything else is hashed in full, interruptibly. Removing originals,
        recovery copies or working files still hashes the book in full first."""
        try:
            if self._identity_current(record):return True
        except (ValueError,OSError,KeyError):pass
        return self._output_valid(record,stop,pace)

    def _identity_current(self, record):
        bindings=getattr(self,'publication_bindings',None)
        lease=bindings.protect(record) if bindings else contextlib.nullcontext((record,None))
        with lease as (effective,envelope):return self._identity_current_at(effective)

    def _identity_current_at(self, record):
        root=ordinary(record['root']); final=ordinary(record['final_path'])
        if os.path.normcase(str(root)) not in {os.path.normcase(str(r)) for r in (tuple(self.inventory.source_roots('Audiobooks'))+((self.inventory.output_root,) if getattr(self.inventory,'output_root',None) else ()) if hasattr(self.inventory,'source_roots') else [self.inventory.roots['Audiobooks']])} and not (hasattr(self,'_chosen_root') and self._chosen_root(root,final)):return False
        if final.suffix.lower()!='.m4b' or record['validation'].get('profile') not in {PROFILE,LEGACY_PROFILE,AUTOMATIC_PROFILE}:return False
        known=self._known_identity(final,record['sha256'])
        if not known or known[2]!=record['size']:return False
        with DirectoryBoundary(root,final.parent) as boundary,VerifiedFile(final) as native:
            if record.get('identity') is not None and native.facts()['identity']!=record['identity']:return False
            if record.get('parent_identity')!=[list(i) for i in boundary.identities] and record.get('parent_identity')!=boundary.identities:return False
            identity=file_identity(final)
        if identity!=known:return False
        self._validated_outputs[record['job_id']]=tuple(identity)
        return True

    @staticmethod
    def _identity_key(path,sha256):
        return (os.path.normcase(str(ordinary(path))),sha256)

    def _known_identities(self):
        try:
            with connect(self.inventory.database) as db:
                return {(path,sha):json.loads(identity) for path,sha,identity in db.execute('SELECT path,sha256,identity FROM verified_outputs')}
        except (sqlite3.Error,ValueError):return {}

    def _known_identity(self,path,sha256):
        try:
            with connect(self.inventory.database) as db:
                row=db.execute('SELECT identity FROM verified_outputs WHERE path=? AND sha256=?',self._identity_key(path,sha256)).fetchone()
            return json.loads(row[0]) if row else None
        except (sqlite3.Error,ValueError,OSError):return None

    def _remember_identity(self,record,identity):
        try:
            with connect(self.inventory.database) as db:
                db.execute('INSERT OR REPLACE INTO verified_outputs VALUES(?,?,?,?,?)',
                           (*self._identity_key(record['final_path'],record['sha256']),record.get('job_id',''),json.dumps(identity),
                            time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
        except (sqlite3.Error,ValueError,OSError):pass  # Not remembered: the next routine check hashes it again.

    def _repair_publication(self,job_id,journal_path,journal_sha256):
        """Authorize a derived receipt through the exact native-held journal.

        Caller retains its independently held journal through disposition; this
        method re-derives the immutable receipt, never accepts an HTTP path.
        """
        with connect(self.inventory.database) as db:
            saved=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()
        if saved is None or saved['state']!='completed':raise ValueError('Completed chapter parent unavailable')
        parent=dict(saved);parent['manifest']=json.loads(parent['manifest']);parent['output']=json.loads(parent['output'])
        choices=[publication for publication in self.publications._repairs(parent) if ordinary(publication['journal'])==ordinary(journal_path) and publication['journal_sha256']==journal_sha256]
        if len(choices)!=1:raise ValueError('Authoritative chapter publication journal differs')
        publication=choices[0];kind='Chaptersv2' if publication['corrected'] else 'Chapters'
        effective,envelope=self.publication_bindings.current(publication['record'],kind,parent,repair_journal_sha256=journal_sha256)
        return {'original':publication['record'],'kind':kind,'effective':effective,'envelope':envelope,'journal_sha256':journal_sha256}

    def _publication_current(self,record):
        """Current-audiobook view: the protected publication's file identity equals its last full verification."""
        known=self._known_identity(record['final_path'],record['sha256'])
        return bool(known) and known[2]==record['size'] and file_identity(ordinary(record['final_path']))==known

    def _publication_verified(self,record):
        try:self._remember_identity(record,file_identity(ordinary(record['final_path'])))
        except OSError:pass

    def close(self):
        with _BULK_LOCK:
            self._closing=True;self._start_generation=self.__dict__.get('_start_generation',0)+1
            pending=self.__dict__.get('_retry_all_stop')
            if pending:pending.set()
            for press in list(self.__dict__.get('_approve_stops',())):press.set()
        for name in ('series_backfill','gap_fill'):
            background=self.__dict__.get(name)
            if background is not None:background.close()
        for name in ('_repair_stop','_retry_all_stop'):
            event=self.__dict__.get(name)
            if event:event.set()
        for name in ('_repair_thread','_retry_all_thread'):
            thread=self.__dict__.get(name)
            if thread and thread is not threading.current_thread():thread.join(30)
        if hasattr(self,'automatic'):self.automatic.close()
        self._retention_stop.set();self._retention_wake.set()
        if self._retention_thread:
            self._retention_thread.join(30)
            if self._retention_thread.is_alive():raise TimeoutError('Recovery cleanup is reaching its safe file checkpoint')
        self.jobs.close()
        if hasattr(self,'publications'):self.publications.close()
        self.cleanup.close()
        with _QUIET_LOCK:
            monitor=self.__dict__.pop('_monitor',None)
        if monitor is not None:monitor.close()

    @staticmethod
    def file_id(library,path):
        return hashlib.sha256((library+'\x1f'+path).encode('utf-8')).hexdigest()

    def _file_record(self,library,identity):
        roots=self.inventory.source_roots(library) if hasattr(self.inventory,'source_roots') else (self.inventory.roots[library],)
        with connect(self.inventory.database) as db:
            rows=db.execute('SELECT * FROM files WHERE root IN (SELECT value FROM json_each(?))',(json.dumps(list(roots)),)).fetchall()
        row=next((dict(r) for r in rows if self.file_id(library,r['path'])==identity),None)
        if row is None:raise ValueError('Catalog file is unavailable')
        return row

    def _source_directories(self,library,view,identity):
        if view=='files':paths=[self._file_record(library,identity)['path']]
        elif view=='candidates':paths=[m['path'] for m in self.reviews._row(library,identity)['members']]
        else:raise ValueError('Unknown inspection view')
        directories=sorted({str(Path(p).parent) for p in paths},key=str.casefold)
        return [{'id':str(uuid.uuid5(uuid.NAMESPACE_URL,library+'\x1f'+p)),'path':p} for p in directories]

    def _completed_output(self,identity):
        jobs=[j for j in self.jobs.status()['jobs'] if j['manifest']['candidate_id']==identity and j['state']=='completed']
        for job in reversed(jobs):
            if self._output_valid(job['output']):return job
        return None

    def _source_section(self,source):
        metadata=json.loads(source['metadata']) if isinstance(source['metadata'],str) else source['metadata']
        cover={'status':'No embedded cover','label':'Source cover'}
        if source.get('missing') or source.get('error'):
            # A gone file's old read error stays in the catalog, not on screen (MissingFiles UX 2026-10-24).
            cover={'status':'Cover could not be read','error':'Source is missing' if source.get('missing') else source.get('error'),'label':'Source cover'}
        else:
            try:
                root=source.get('root',self.inventory.roots['Audiobooks'])
                allowed=self.inventory.all_source_roots() if hasattr(self.inventory,'all_source_roots') else self.inventory.roots.values()
                if os.path.normcase(root) not in {os.path.normcase(str(r)) for r in allowed}:raise ValueError('Source is outside configured libraries')
                with DirectoryBoundary(root,Path(source['path']).parent):
                    cover=self.reviews.source_cover(source['path'],metadata)
            except (ValueError,OSError,TimeoutError) as error:cover={'status':'Cover could not be read','error':str(error),'label':'Source cover'}
        tags={k.casefold():v for k,v in metadata.get('tags',{}).items()}
        facts=[{'label':label,'value':value} for label,value in [('Title',tags.get('title',metadata.get('track_title',metadata.get('title','')))),('Album / book clue',tags.get('album','')),('Artist — role unverified',tags.get('artist',metadata.get('author',''))),('Recording language',metadata.get('edition_language','')),('Series clue',metadata.get('series','')),('Position clue',metadata.get('number','')),('Comments',tags.get('comment',tags.get('comments',''))),('Read method',metadata.get('method',''))]]
        return {'kind':'source','heading':'Existing source metadata','status':'Source tags unchanged','path':source['path'],'facts':facts,'cover':cover,'raw_tags':metadata.get('tags',{}),'member_values':[]}

    @staticmethod
    def _review_facts(review):
        review=review or {}
        labels={'title':'Title','canonical_author':'Author','narrator':'Reader / narrator','original_language':'Original work language','series':'Series','number':'Number in series'}
        facts=[]
        for key,label in labels.items():
            value=review.get(key,'')
            if key=='original_language':value={'Other':'Non-Russian','Unknown':'Unverified'}.get(value,value)
            if value:facts.append({'label':label,'value':value})
        if review.get('anthology'):facts.append({'label':'Collection','value':'Short-story collection by multiple authors'})
        if review.get('multi_author'):facts.append({'label':'Series authors','value':'Multiple authors'})
        return facts

    @staticmethod
    def _output_facts(tags):
        labels={'title':'Title','artist':'Author','album':'Album','grouping':'Series','track':'Number in series','comment':'Comments'}
        return [{'label':label,'value':tags.get(key,'')} for key,label in labels.items() if tags.get(key,'')]+[{'label':'Format','value':'M4B audiobook'}]

    def inspect(self,library,view,identity):
        directories=self._source_directories(library,view,identity);sections=[];completed=None;ready=False
        if view=='files':
            source=self._file_record(library,identity);sections.append(self._source_section(source))
            review=json.loads(source['review']) if source['review'] else None
            if review:sections.append({'kind':'draft','heading':'Sorting preview metadata','status':'Preview — source tags unchanged','facts':self._review_facts(review),'cover':{'status':'No selected cover'},'raw_tags':review})
        else:
            row=self.reviews.enrich(self.reviews._row(library,identity));metadata=row['metadata'];ready=row['audiobook_ready']
            values=[]
            for member in row['members']:
                for field,value in member['metadata'].get('tags',{}).items():values.append({'path':member['path'],'field':field,'value':value})
            sections.append({'kind':'source','heading':'Existing source metadata','status':'Per-file clues; roles and book identity remain unverified','facts':[],
                'cover':{'status':'Source covers differ or are unreviewed; inspect the individual files'},'raw_tags':{},'member_values':values,
                'alternatives':[{**c,'label':c['source_label'],'status':'Source artwork — edition unverified'} for c in row['cover_choices']]})
            selected=row['selected_cover']
            sections.append({'kind':'approved' if row['metadata_approved'] else 'draft','heading':'Approved preview metadata' if row['metadata_approved'] else 'Draft preview metadata',
                'status':'Source tags unchanged','facts':self._review_facts(row['review']),
                'cover':({**selected,'label':selected['source_label'],'status':'Selected cover — edition unverified'} if selected else {'status':'No selected cover'}),
                'raw_tags':row['review'] or {},'member_values':[]})
            current=self.publications.describe(self.jobs.status()['jobs'],identity)
            completed=self.replacements.representative(self.jobs.status()['jobs'],identity)[0]
            if current['state']=='verified':
                output=current['record'];cover=current['cover']
                cleanup=self.cleanup.status(completed['job_id']);cleanup_facts=[]
                if cleanup:
                    cleanup_facts=[{'label':label,'value':value} for label,value in [('Source cleanup',cleanup['status']),('Originals removed',cleanup['removed']),('Originals remaining',cleanup['remaining']),('Removed from Z: (bytes)',cleanup['bytes_removed']),('Recovery copies (bytes)',cleanup['recovery_bytes']),('Recovery location',cleanup['recovery_location']),('Recovery','Temporary recovery files were removed after successful cleanup. Original tracks cannot be restored from them.' if cleanup.get('recovery',{}).get('state')=='deleted' else 'Remaining temporary recovery copies can restore original tracks. Existing files are never overwritten.' if cleanup['restore_available'] else 'Temporary recovery files are unavailable; see cleanup status.')]]
                saved=current.get('tags_state')=='saved_preserved';tags=current.get('saved_tags',{}) if saved else current['tags']
                sections.append({'kind':'created','heading':'Saved chapter-update metadata' if saved else 'Current audiobook metadata',
                    'status':'Verified chapter update; saved preserved tags, fresh tag reading unavailable' if saved else 'Output checks passed; Apple Books sync not checked','path':output['final_path'],
                    'facts':self._output_facts(tags)+cleanup_facts,
                    'cover':{**cover,'label':'Current audiobook cover','status':'Validated attached cover'},'raw_tags':tags,'member_values':[]})
            elif current['state'] in {'verifying','unavailable'}:
                sections.append({'kind':'snapshot','heading':'Current audiobook unavailable','status':current['reason'],'facts':[],'raw_tags':{},'member_values':[]})
        return {'inspector':{'id':identity,'view':view,'heading':'Metadata and cover','sections':sections,'source_directories':directories,
            'source_directory_count':len(directories),'output_folder_available':bool(view=='candidates' and current['state']=='verified'),'audiobook_ready':ready,
            'current_audiobook':self.current_audiobook(identity) if view=='candidates' else None}}

    FOLDER_UNAVAILABLE='Folder unavailable. Connect the library drive and try again.'

    def open_folder(self,library,view,identity,folder_kind='source',directory_id=None):
        """Open a book's source folder, or the folder that holds its converted file (folder_kind 'output'), in File
        Explorer. Ruling 70 (Sergei 2026-10-29): when the source folder is gone and the book is finished, its converted
        file's folder opens instead (that file is the book's current source). A folder that cannot be opened answers
        Judy's one sentence, never the engine's error text."""
        root=self.inventory.roots[library]
        if folder_kind=='source':
            directories=self._source_directories(library,view,identity)
            if directory_id is None:
                if len(directories)!=1:raise ValueError('Choose one source folder')
                directory=directories[0]['path']
            else:
                item=next((d for d in directories if d['id']==directory_id),None)
                if item is None:raise ValueError('Unknown source folder choice')
                directory=item['path']
            if view=='candidates' and not os.path.isdir(directory):
                try:return dict(self.open_folder(library,view,identity,'output'),fallback='output')
                except ValueError:raise ValueError(self.FOLDER_UNAVAILABLE) from None
        elif folder_kind=='output' and view=='candidates':
            self.reviews._row(library,identity)
            try:
                jobs=self.jobs.status()['jobs'];current=self.publications.describe(jobs,identity)
                if current['state']!='verified':raise ValueError(current.get('reason','Current audiobook unavailable'))
                publication=self.publications.publication(jobs,identity)
                with self.publications.protected(publication) as (_,key):
                    if key!=current['identity']:raise ValueError('Current audiobook changed before folder opening')
                    directory=str(Path(current['path']).parent)
                    self.dispatch_folder(directory)
                    return {'opened':True,'directory':directory}
            except (ValueError,OSError,KeyError):raise ValueError(self.FOLDER_UNAVAILABLE) from None
        else:raise ValueError('Unknown folder target')
        if hasattr(self.inventory,'source_root_for_path'):root=self.inventory.source_root_for_path(directory,library)
        try:
            with DirectoryBoundary(root,directory):self.dispatch_folder(directory)
        except (ValueError,OSError):raise ValueError(self.FOLDER_UNAVAILABLE) from None
        return {'opened':True}

    @staticmethod
    def dispatch_folder(directory):
        # Only a user-click route calls this; tests replace it with a mock.
        import ctypes
        buffer=ctypes.create_unicode_buffer(32768)
        if not ctypes.windll.kernel32.GetWindowsDirectoryW(buffer,len(buffer)):raise OSError('Windows folder launcher unavailable')
        subprocess.Popen([str(Path(buffer.value)/'explorer.exe'),str(directory)],shell=False)


    # --- Rulings 69/70: destination override and moves ---
    # Sergei 2026-10-29: on any row he chooses the folder a book goes to (the Windows folder picker); it outranks every
    # computed folder, only the folder is his (71i), choosing never approves (71j), a folder outside Audiobooks Sorted is
    # allowed and its book's originals are still removed after the verified result (71h). A finished book is moved, never
    # converted again; its old folder goes when it is left empty (71k). destination_overrides keeps the choices, book_move
    # the moves; PublicationBindings follows the moves, so every consumer of a book's location follows them too.
    OVERRIDE_REPLANNED='Set aside: you chose another folder. Nothing ran; the book is checked again with your folder.'
    OVERRIDE_UNAVAILABLE="The folder you chose isn't available (renamed, moved or disconnected). Choose the folder again or use the computed folder."
    folder_probe=None      # tests: a seam for the writable probe (destination_overrides.validate)
    move_same_volume=None  # tests: a seam for the move strategy (book_move.Mover)
    move_fault=None        # tests: a hook raised at each move journal boundary
    move_requester=None    # the server's action queue: (move, title) -> its queued answer; None runs the move at once

    def _chosen_folders(self):
        """Every folder Sergei ever chose and every folder a move put a book in (append-only records)."""
        import destination_overrides,book_move
        try:
            with connect(self.inventory.database) as db:
                found=set(destination_overrides.folders(db))
                if book_move.have(db):
                    found|={r[0] for r in db.execute("SELECT DISTINCT target_folder FROM book_moves WHERE state IN ('committed','old_removal_intent','complete','partial')")}
        except sqlite3.Error:return ()
        return tuple(sorted(found,key=str.casefold))

    def _chosen_root(self,root,final):
        """A book filed directly in a folder Sergei chose: that folder is its root (outside the configured roots too)."""
        try:
            if ordinary(final).parent!=ordinary(root):return False
            return any(ordinary(folder)==ordinary(root) for folder in self._chosen_folders())
        except (ValueError,OSError):return False

    def _all_source_roots(self):
        inventory=self.inventory
        return tuple(inventory.all_source_roots() if hasattr(inventory,'all_source_roots') else getattr(inventory,'roots',{}).values())

    def _override_rows(self):
        """Every choice, read once and kept until this engine writes one (_destination_changed): the Goes to line and the
        approval preview of every listed row read them, so a list read opens no extra connection per row."""
        import destination_overrides
        cached=self.__dict__.get('_override_cache')
        if cached is not None:return cached
        try:
            with connect(self.inventory.database) as db:found=destination_overrides.rows(db)
        except sqlite3.Error:return []
        self.__dict__['_override_cache']=found
        return found

    def _live_override(self,row,job_id=None):
        import destination_overrides,entered_names
        return destination_overrides.live_in(self._override_rows(),book_key=entered_names.book_key(row),job_id=job_id)

    def _with_override(self,row,facts,strict=False):
        """These facts with the book's live chosen folder (organization.plan reads it), or without one. strict (an approval
        that writes a job): a chosen folder that is no longer the same folder (renamed, replaced, gone) refuses, never
        followed by name and never silently replaced by the computed folder."""
        import destination_overrides
        live=self._live_override(row)
        value=destination_overrides.fact(live)
        if value is None and not isinstance(facts,dict):return facts
        facts=copy.deepcopy(facts) if isinstance(facts,dict) else {}
        if value is None:
            facts.pop('destination_override',None);return facts
        if strict and not destination_overrides.same_identity(value['identity'],destination_overrides.current_identity(value['folder'])):
            raise ValueError(self.OVERRIDE_UNAVAILABLE)
        facts['destination_override']=value
        return facts

    def _chosen_display(self,row,path):
        """A destination as Sergei will see it: a chosen folder outside the output root is reached by a move after the
        conversion (organization.chosen_folder), so its preview names the chosen folder and the computed file name."""
        import destination_overrides
        if not path:return path
        live=self._live_override(row)
        if not live or not live.get('folder'):return path
        output_root=getattr(self.inventory,'output_root',None)
        if output_root and destination_overrides.inside(live['folder'],output_root):return path
        return os.path.join(os.path.normpath(live['folder']),os.path.basename(path))

    def _shown_path(self,path,output_root):
        import destination_overrides
        if path and output_root and destination_overrides.inside(path,output_root):return os.path.relpath(path,output_root)
        return path

    def _computed_destination(self,row,manifest=None):
        """The planner's own destination for the book (absolute), ignoring any chosen folder; '' when it has none."""
        try:
            if manifest is not None:
                facts=copy.deepcopy(manifest.get('metadata_facts')) if isinstance(manifest.get('metadata_facts'),dict) else None
                if facts:facts.pop('destination_override',None)
                root=getattr(self.inventory,'output_root',None) or manifest.get('output_root',manifest['root'])
                review=dict(manifest['metadata'],organization_policy='books-hierarchy-v2')
                first=row['members'][0]['path'] if row.get('members') else ''
                return propose(first,root,'audiobook',row.get('metadata') or {},review,automatic_facts=facts).get('path') or ''
            book,result=self._approval_result(row['id'],row['revision'])
            if not isinstance(result.get('review'),dict):return ''
            facts=copy.deepcopy(result.get('metadata_facts')) if isinstance(result.get('metadata_facts'),dict) else None
            if facts:facts.pop('destination_override',None)
            review=dict(result['review'],organization_policy='books-hierarchy-v2')
            return propose(book['members'][0]['path'],self.reviews._output_root(book,review),'audiobook',book['metadata'],review,automatic_facts=facts).get('path') or ''
        except (ValueError,KeyError,TypeError,OSError,IndexError):return ''

    def _override_stale(self,job):
        """AudioJobs' claim check (ruling 69): a pending job planned with another chosen folder than the book's now, or
        whose chosen folder is no longer the same folder, never starts; it goes back to research (_names_replan)."""
        import destination_overrides
        manifest=json.loads(job['manifest'])
        facts=manifest.get('metadata_facts') if isinstance(manifest.get('metadata_facts'),dict) else {}
        frozen=facts.get('destination_override') or {}
        try:row=self.reviews._row('Audiobooks',manifest['candidate_id'])
        except (ValueError,KeyError,TypeError):return False  # the book changed: the job's own revision checks refuse it
        live=self._live_override(row) or {}
        frozen_folder=frozen.get('folder') or '';live_folder=live.get('folder') or ''
        stale=destination_overrides.key(frozen_folder)!=destination_overrides.key(live_folder) if (frozen_folder or live_folder) else False
        if not stale and frozen_folder:
            stale=not destination_overrides.same_identity(frozen.get('identity'),destination_overrides.current_identity(frozen_folder))
        if stale:self.__dict__.setdefault('_replan_reasons',{})[job['job_id']]=self.OVERRIDE_REPLANNED
        return stale

    def _finished(self,identity,jobs=None):
        """(publication, binding kind, job id) of the book's current published audiobook, else None."""
        jobs=jobs if jobs is not None else self.jobs.status()['jobs']
        try:publication=self.publications.publication(jobs,identity)
        except (ValueError,OSError,KeyError):return None
        if not publication:return None
        kind={'original':'base','replacement':'replacement'}.get(publication['kind'],publication['kind'])
        return publication,kind,publication['parent']['job_id']

    def _publication_location(self,job_id,kind):
        """The book's effective location now (receipt, relocation and moves), through a generation lease."""
        import book_move
        with connect(self.inventory.database) as db:
            row=db.execute('SELECT output FROM audio_jobs WHERE job_id=? AND state=?',(job_id,'completed')).fetchone()
        if row is None or not row['output']:raise ValueError('The audiobook has no completed publication')
        effective,_envelope=self.publication_bindings.current(json.loads(row['output']),kind)
        return book_move.location(effective)

    def _move_root(self,folder):
        import destination_overrides
        output_root=getattr(self.inventory,'output_root',None)
        return output_root if output_root and destination_overrides.inside(folder,output_root) else folder

    def destination_choose(self,id,revision,folder):
        """Choose folder... (folder, from the picker) or Use computed folder (None) on one book. Not finished: the choice
        is saved, nothing is approved or queued (71j). Finished: the choice is saved and the audiobook's move is queued
        (never a conversion). Returns {'outcome': saved | cleared | move_queued | unchanged, 'destination_override',
        'preview', 'move'}. Refusals: destination_overrides.Refused or book_move.Refused, with a typed cause."""
        import destination_overrides,entered_names,book_move
        if self.draining or self.__dict__.get('_closing'):raise destination_overrides.Refused('changed','Books Arranger is closing. Nothing was moved.')
        try:row=self.reviews._row('Audiobooks',id,revision)
        except ValueError:raise destination_overrides.Refused('changed','This book changed. Review its details and try again.') from None
        book_key=entered_names.book_key(row)
        finished=self._finished(id)
        if finished and finished[1] not in book_move.KINDS:
            raise destination_overrides.Refused('changed',"This audiobook can't be moved: it is a chapter update of another file.")
        job_id=finished[2] if finished else None
        try:start=self._publication_location(job_id,finished[1]) if finished else None
        except (ValueError,OSError,KeyError):raise destination_overrides.Refused('source_missing',"The audiobook isn't where the app expects it. Nothing was moved.") from None
        if folder is None:
            with connect(self.inventory.database) as db:destination_overrides.retract(db,book_key=book_key,job_id=job_id)
            self._destination_changed()
            if not finished:return self._destination_answer(id,'cleared')
            computed=self._computed_destination(row,self._job_manifest(job_id))
            if not computed:raise destination_overrides.Refused('changed',"The app can't compute this book's folder now. Nothing was moved.")
            return self._queue_move(row,finished,start,os.path.dirname(computed),None)
        name=os.path.basename(start['final_path']) if finished else os.path.basename(self._computed_destination(row) or '')
        data_dir=str(Path(self.inventory.database).parent)
        chosen,identity=destination_overrides.validate(folder,sources=self._all_source_roots(),data_dir=data_dir,name=name,probe=self.folder_probe)
        if destination_overrides.inside(chosen,str(self.cache_dir)):raise destination_overrides.Refused('unsafe','That folder belongs to the app. Choose another folder.')
        with connect(self.inventory.database) as db:
            saved=destination_overrides.choose(db,folder=chosen,identity=identity,book_key=book_key,candidate_id=id,job_id=job_id)
        self._destination_changed()
        if not finished:return self._destination_answer(id,'saved')
        return self._queue_move(row,finished,start,chosen,saved['override_id'])

    def _job_manifest(self,job_id):
        with connect(self.inventory.database) as db:
            found=db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()
        return json.loads(found['manifest']) if found else None

    def _destination_changed(self):
        self.__dict__.pop('_override_cache',None)
        self.__dict__.pop('_needs_cache',None)
        self.invalidate_status()

    def _destination_answer(self,id,outcome,move=None):
        try:row=self.reviews._row('Audiobooks',id)
        except ValueError:row=None
        view={'destination_override':None,'preview':None,'move':move}
        if row is not None:
            shown=[copy.deepcopy(row)]
            try:self.destination_view(shown)
            except (ValueError,OSError,sqlite3.Error):pass
            view['destination_override']=shown[0].get('destination_override')
            preview=shown[0].get('preview') or {}
            view['preview']={'path':preview.get('path',''),'absolute':preview.get('absolute',preview.get('path',''))}
            if move is None:view['move']=shown[0].get('move')
        return {'outcome':outcome,**view}

    def _queue_move(self,row,finished,start,folder,override_id):
        """Plan the finished book's move (book_move.plan) and queue it; 'unchanged' when it is already in that folder."""
        import book_move,destination_overrides
        publication,kind,job_id=finished
        root=self._move_root(folder)
        with connect(self.inventory.database) as db:
            move=book_move.plan(db,job_id=job_id,kind=kind,candidate_id=row['id'],start=start,folder=folder,root=root,override_id=override_id)
        if move is None:return self._destination_answer(row['id'],'unchanged')
        title=str(row.get('title_clue') or '')[:200]
        if self.move_requester is not None:
            try:queued=self.move_requester(move,title)
            except Exception:
                with connect(self.inventory.database) as db:book_move.cancel(db,move['move_id'])
                raise destination_overrides.Refused('changed','Move was not accepted. Nothing was moved.') from None
            return self._destination_answer(row['id'],'move_queued',dict(book_move.view(move),queue=queued))
        done=self.run_move(move['move_id'])
        return self._destination_answer(row['id'],'move_queued',done)

    def cancel_move(self,move_id):
        """The queued move's Cancel (ActionQueue): True when it had not started."""
        import book_move
        with connect(self.inventory.database) as db:return book_move.cancel(db,move_id)

    def _mover(self):
        import book_move,book_delete
        configured=[*self._all_source_roots(),*([self.inventory.output_root] if getattr(self.inventory,'output_root',None) else [])]
        progress=self.__dict__.setdefault('_move_progress',{})
        def report(move_id,percent):progress[move_id]=percent
        return book_move.Mover(lambda:connect(self.inventory.database),self._publication_location,sources=self._all_source_roots,
                               output_root=getattr(self.inventory,'output_root',None),same_volume=self.move_same_volume or book_move.default_same_volume,
                               fault=self.move_fault,progress=report,remove_folder=book_delete._remove_folder,protected_roots=lambda:configured)

    @operation
    def run_move(self,move_id):
        """Run one queued move now (the action queue's runner). Returns the row's move line."""
        import book_move
        if self.draining or self.__dict__.get('_closing'):
            with connect(self.inventory.database) as db:book_move.cancel(db,move_id)
            raise ValueError('Books Arranger is closing. Nothing was moved.')
        move=self._mover().run(move_id)
        self._after_move(move)
        return book_move.view(move)

    def _after_move(self,move):
        """A committed move: its new location is the book's owned output and its last full verification (the move hashed
        every byte); the caches that showed the old location are dropped."""
        import book_move
        self.__dict__.get('_move_progress',{}).pop(move['move_id'],None)
        if move['state'] in book_move.EFFECTIVE and isinstance(move.get('final'),dict):
            final=move['final']
            try:
                with connect(self.inventory.database) as db:
                    db.execute('INSERT OR REPLACE INTO owned_artifacts VALUES(?,?,?,?,?)',(final['final_path'],move['job_id'],'output',final['sha256'],final['size']))
            except sqlite3.Error:pass
            self._publication_verified(dict(final,job_id=move['job_id']))
            self._validated_outputs.pop(move['job_id'],None)
        self._destination_changed()

    def _start_move_recovery(self):
        """In-engine reconciliation of moves a restart interrupted (no startup refusal); only when there are any."""
        import book_move
        try:
            with connect(self.inventory.database) as db:open_moves=book_move.pending(db)
        except sqlite3.Error:return
        if not open_moves:return
        def work():
            try:
                for move in self._mover().recover():self._after_move(move)
            except Exception:pass  # each unreconciled move stays journaled; the next start tries again
        self._move_recovery=threading.Thread(target=work,name='books-move-recovery',daemon=True)
        self._move_recovery.start()

    def _move_to_chosen(self,job_id):
        """After a book is published: when the folder chosen for it is not where it was published (outside Sorted, or
        chosen while it converted), its move is queued."""
        import destination_overrides,book_move
        job=next((j for j in self.jobs.status()['jobs'] if j['job_id']==job_id),None)
        if not job or job['state']!='completed':return
        identity=job['manifest']['candidate_id']
        try:row=self.reviews._row('Audiobooks',identity)
        except ValueError:return
        finished=self._finished(identity)
        if not finished or finished[2]!=job_id or finished[1] not in book_move.KINDS:return
        live=self._live_override(row,job_id=job_id)
        if not live or not live.get('folder'):return
        start=self._publication_location(job_id,finished[1])
        if destination_overrides.key(os.path.dirname(start['final_path']))==destination_overrides.key(live['folder']):return
        if not destination_overrides.same_identity(live.get('identity'),destination_overrides.current_identity(live['folder'])):return  # fails closed
        self._queue_move(row,finished,start,live['folder'],live['override_id'])

    def destination_view(self,rows):
        """Every shown list row: destination_override, output and move (Judy's 0.23.1 spec, sections 15-18). Catalog and
        page facts only; no file is opened."""
        import destination_overrides,entered_names,book_move
        if not rows:return
        ids=[r['id'] for r in rows if r.get('id')]
        output_root=getattr(self.inventory,'output_root',None)
        progress=self.__dict__.get('_move_progress',{})
        try:
            with connect(self.inventory.database) as db:
                moves=book_move.latest(db,ids)
                completed={}
                if ids and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audio_jobs'").fetchone():
                    marks=','.join('?' for _ in ids)
                    aside=' AND job_id NOT IN (SELECT job_id FROM audio_job_set_aside)' if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audio_job_set_aside'").fetchone() else ''
                    for job_id,candidate,manifest in db.execute("SELECT job_id,json_extract(manifest,'$.candidate_id'),manifest FROM audio_jobs WHERE state='completed' AND json_extract(manifest,'$.candidate_id') IN (%s)%s ORDER BY created,job_id"%(marks,aside),ids):
                        completed[candidate]=(job_id,manifest)
            records=self._override_rows()
            lives={}
            for row in rows:
                job=completed.get(row.get('id'))
                lives[row.get('id')]=destination_overrides.live_in(records,book_key=entered_names.book_key(row),job_id=job[0] if job else None)
        except sqlite3.Error:
            for row in rows:row.setdefault('destination_override',None);row.setdefault('move',None);row.setdefault('output',None)
            return
        for row in rows:
            current=row.get('current_audiobook') or {}
            output=None
            if current.get('state')=='verified' and current.get('path'):
                path=current['path'];output={'path':self._shown_path(path,output_root),'absolute':path,'folder':os.path.dirname(path)}
            row['output']=output
            move=book_move.view(moves.get(row.get('id')))
            if move and move['state']=='moving' and move['move_id'] in progress:move['progress']=progress[move['move_id']]
            row['move']=move
            live=lives.get(row.get('id'))
            if not live or not live.get('folder'):
                row['destination_override']=None;continue
            folder=live['folder'];job=completed.get(row.get('id'))
            manifest=None
            if job:
                try:manifest=json.loads(job[1])
                except (TypeError,ValueError):manifest=None
            computed=self._computed_destination(row,manifest) if manifest is not None else self._computed_destination(row)
            outside=not (output_root and destination_overrides.inside(folder,output_root))
            row['destination_override']={'folder':folder,'computed_folder':self._shown_path(os.path.dirname(computed),output_root) if computed else '',
                                         'computed_path':computed,'outside_sorted':bool(outside)}
            if job:continue  # a finished book's file is where "Now in" says; a move takes it to the chosen folder
            chosen=os.path.join(os.path.normpath(folder),os.path.basename(computed)) if computed else ''
            # row.ask.destination already names the chosen folder (approval_preview plans with it): its path is the one an
            # Approve sends back and compares, so it is left exactly as planned.
            if chosen and isinstance(row.get('preview'),dict):row['preview']=dict(row['preview'],path=chosen,absolute=chosen)
