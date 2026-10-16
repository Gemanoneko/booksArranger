"""Join reviewed candidates to the durable, source-preserving media queue."""
from encoding_policy import LEGACY_PROFILE, AUTOMATIC_PROFILE
import contextlib
import copy
import json
import os
import sqlite3
from pathlib import Path
import threading
import time
import hashlib
import uuid
import subprocess
import functools

from audio_jobs import AudioJobs
from audio_pipeline import create_private, publish, digest, fingerprint, Paused, PROFILE
from native_io import DirectoryBoundary, ProtectedFiles, VerifiedFile, ordinary
from review_backend import CandidateReviewService
from scanner import connect
from metadata import propose
from source_cleanup import CleanupJobs, packed
from review_backend import member_key
from conversion_progress import approved_scope,completed_book,phase_progress
from replacement_jobs import Replacements,digest as record_digest,now as replacement_now
from replacement_retirement import ReplacementRetirement
from current_audiobook import CurrentAudiobooks
import groups

INITIAL_CLEANUP_JOBS={'0b6fedcc-2d95-46a9-a4a3-4192da37ff72','dc4874af-e132-47cd-93ab-85e5b0fbeea7'}
STATUS_MAX_AGE=1.0 # Seconds after a status computation STARTED during which polling readers may reuse it.
STATUS_WAIT=4.0 # Seconds a reader waits on another thread's computation; below the desktop shell's 5 s request timeout.


class StatusUnavailable(RuntimeError):
    """Another thread's status computation did not finish within STATUS_WAIT; the poll reports status unavailable."""


class SharedSnapshot:
    """Single-flight read: concurrent callers wait for one computation, then reuse it until max_age after it started.

    Threads arriving while a computation runs never start another one, so a slow
    catalog cannot accumulate one expensive computation per poll. invalidate()
    (after every control) drops the remembered answer and detaches a running
    computation: its result is never cached and no later reader joins it.
    """
    def __init__(self,clock=time.monotonic,wait=STATUS_WAIT):
        self._lock=threading.Lock();self._clock=clock;self._wait=wait;self._value=None;self._at=None;self._flight=None;self._generation=0

    def invalidate(self):
        with self._lock:self._generation+=1;self._value=None;self._at=None;self._flight=None

    def get(self,compute,max_age):
        with self._lock:
            if self._at is not None and 0<=self._clock()-self._at<max_age:return copy.deepcopy(self._value)
            flight=self._flight;owner=flight is None
            if owner:flight=self._flight={'done':threading.Event(),'value':None,'error':None,'generation':self._generation,'started':self._clock()}
        if owner:
            try:flight['value']=compute()
            except BaseException as error:flight['error']=error
            finally:
                with self._lock:
                    if flight['error'] is None and flight['generation']==self._generation:self._value,self._at=flight['value'],flight['started']
                    if self._flight is flight:self._flight=None
                flight['done'].set()
        elif not flight['done'].wait(self._wait):raise StatusUnavailable('Status computation is still running')
        if flight['error'] is not None:raise flight['error']
        return copy.deepcopy(flight['value'])

def operation(method):
    @functools.wraps(method)
    def locked(self,*args,**kwargs):
        with self.operation_lock:return method(self,*args,**kwargs)
    return locked


class MergeService:
    draining=False # Set by a desktop Quit: the current book finishes, nothing new starts.

    def __init__(self, inventory, cache_dir):
        self.inventory = inventory
        self.operation_lock=threading.RLock()
        self._progress_lock=threading.RLock()
        self._approved_cache=None
        self._post_current=None
        self._validated_outputs={}
        self.cache_dir = ordinary(cache_dir)
        with DirectoryBoundary(self.cache_dir.anchor,self.cache_dir,create=True):pass
        self.stage_root = self.cache_dir / 'audio-staging'
        self.reviews = CandidateReviewService(inventory, self.cache_dir / 'covers')
        with connect(inventory.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS owned_artifacts(path TEXT PRIMARY KEY, job_id TEXT, kind TEXT, sha256 TEXT, size INTEGER)')
        self.replacements=Replacements(inventory.database)
        self.publications=CurrentAudiobooks(inventory.roots['Audiobooks'],self.cache_dir.parent/'chapter-repairs',self.replacements)
        self.retirement=ReplacementRetirement(self.replacements,self.cache_dir.parent/'replacement-recovery',inventory.roots['Audiobooks'],threading.Event(),self._replacement_guard,self.publications.protect_former)
        self.jobs = AudioJobs(inventory.database, self._run, self._guard, self._output_valid,self.retirement.historical_retired)
        self.retirement.stop=self.jobs._stop
        self.jobs.pending_postprocessing=self._pending_replacement_postprocessing
        self.jobs.postprocessing=self._finish_replacement
        self.cleanup = CleanupJobs(inventory.database,self.cache_dir.parent/'source-recovery',self._cleanup_guard,self._review_boundary)
        self.cleanup.stop=self.jobs._stop
        self.jobs.after_completed=self._after_completed
        self.cleanup.after_drain=lambda:self.jobs.resume()
        from storage_cleanup import StorageCleanup
        self.storage_cleanup=StorageCleanup(inventory.database,self.stage_root,self.cleanup.root,self._storage_guard)
        from working_lifecycle import WorkingLifecycle
        self.working=WorkingLifecycle(inventory.database,self.stage_root,self._working_guard)
        self.jobs.before_attempt=self.working.admit
        self.jobs.after_attempt=self.working.terminal
        from recovery_retention import RecoveryRetention
        self.recovery=RecoveryRetention(self.storage_cleanup,guard=self._retention_guard)
        self.cleanup.recovery_status=self.recovery_status
        self._retention_stop=threading.Event();self._retention_wake=threading.Event();self._retention_thread=None;self._manual_recovery=None
        self.cleanup.on_completed=lambda job_id:self._prune_completed(job_id,source_completed=True)
        self.reviews.set_jobs(self)
        from automatic_processing import AutomaticProcessing
        self.automatic=AutomaticProcessing(self)
        self.jobs.on_space_hold=lambda:self.automatic.stop(force=True)
        self.jobs.on_working_hold=lambda:self.automatic.stop(force=True)
        for job in self.jobs.status()['jobs']:
            if job['state']=='completed':self._register(job['output']['final_path'],job['job_id'],'output',job['output']['sha256'],job['output']['size'])
            if job['state']=='completed' and job['manifest'].get('cleanup_policy',{}).get('enabled') and not self.cleanup.status(job['job_id']):
                # A crash after durable audio success but before enrollment does
                # not turn its explicit frozen policy into a historical sweep.
                self._enroll_completed_without_start(job)

    def _enroll_completed_without_start(self,job):
        try:self.enroll_cleanup(job['job_id'])
        except (ValueError,OSError) as error:self._enrollment_attention(job,error)

    def _enrollment_attention(self,job,error):
        with connect(self.inventory.database) as db:
            id=str(uuid.uuid4());intent={'id':id,'job_id':job['job_id'],'manifest':job['manifest'],'output':job['output'],'binding':{},'actor':'assistant'}
            db.execute('INSERT OR IGNORE INTO source_cleanup VALUES(?,?,?,?,?,?,?)',(id,job['job_id'],packed(intent),'needs_attention',str(error),'',''))

    def _register(self,path,job,kind,hash='',size=0):
        with connect(self.inventory.database) as db:
            db.execute('INSERT OR REPLACE INTO owned_artifacts VALUES(?,?,?,?,?)',(path,job,kind,hash,size))

    def progress_books(self,jobs=None,cleanups=None,storage=None,folders=None):
        """Catalog transitions invalidate eligibility; polls never decode or hash media."""
        jobs=jobs if jobs is not None else self.jobs.status()['jobs']
        cleanups=cleanups if cleanups is not None else self.cleanup.status()
        storage=storage if storage is not None else self.storage_cleanup.status()
        folders=folders if folders is not None else self.storage_cleanup.folder_status()
        with self._progress_lock,connect(self.inventory.database) as db:
            # Group sync uses the existing indexed catalog revision guard, not a library scan.
            groups.sync(db,self.inventory.roots['Audiobooks'])
            rows=[dict(r) for r in db.execute("SELECT g.*,c.revision AS context_revision,c.data AS context_data FROM book_groups g JOIN candidate_context c ON c.id=g.id WHERE g.root=? AND json_extract(c.data,'$.metadata_approved')=1",(self.inventory.roots['Audiobooks'],))]
            signature=[(r['id'],r['revision'],r['fingerprint'],r['review'],r['context_revision'],r['context_data'],r['changed']) for r in rows]
            if self._approved_cache is None or self._approved_cache[0]!=signature:
                retired=groups.retired_sources(db,self.inventory.roots['Audiobooks']);approved={}
                for r in rows:
                    if r['context_revision']!=r['revision']:continue
                    row=groups.render(r,r['root'],True,retired);ctx=json.loads(r['context_data'])
                    if ctx.get('metadata_facts'):
                        from standing_metadata import validate_policy
                        validate_policy(row,row['review'],ctx['metadata_facts'])
                        row['preview']=propose(row['members'][0]['path'],r['root'],'audiobook',row['metadata'],row['review'],automatic_facts=ctx['metadata_facts'])
                    if approved_scope(row,ctx,member_key):approved[row['id']]=(row,ctx)
                self._approved_cache=(signature,approved)
            approved={}
            for id,(row,ctx) in self._approved_cache[1].items():
                if any((self.reviews.cache/(ctx['cover_id']+suffix)).is_file() for suffix in ('.png','.jpg')):approved[id]=(row,ctx)
            source_by={r['job_id']:r for r in cleanups};storage_by={r['job_id']:r for r in storage};folder_by={r['job_id']:r for r in folders}
            converted=set()
            representatives=[self.replacements.representative(jobs,id)[0] for id in approved] if hasattr(self,'replacements') else jobs
            for job in representatives:
                if not job:continue
                id=job['manifest']['candidate_id']
                if id not in approved:continue
                row,ctx=approved[id];record=job.get('output') or {};current=False
                try:
                    stat=Path(record['final_path']).stat()
                    current=(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns)==self._validated_outputs.get(job['job_id'])
                except (OSError,KeyError):pass
                relation=self.replacements.get(new_job=job['job_id']) if hasattr(self,'replacements') else None
                binding=relation if relation and relation['state'] in {'published','retiring','completed'} and self.replacements.structural_guard(relation) else None
                if relation and relation['state'] in {'published','retiring','completed'} and binding is None:continue
                if completed_book(row,ctx,job,source_by.get(job['job_id']),storage_by.get(job['job_id']),folder_by.get(job['job_id']),current,member_key,{PROFILE,AUTOMATIC_PROFILE},binding):converted.add(id)
            return {'approved':len(approved),'converted':len(converted),'converted_ids':converted}

    def status_snapshot(self,max_age=STATUS_MAX_AGE):
        """Polling routes only: concurrent readers share one state() computation, reused briefly. Controls keep fresh state()."""
        return self.__dict__.setdefault('_status_shared',SharedSnapshot()).get(self.state,max_age)

    def invalidate_status(self):
        """A control ran: the next polling read recomputes instead of reusing a pre-control answer."""
        shared=self.__dict__.get('_status_shared')
        if shared is not None:shared.invalidate()

    def state(self):
        snapshot=getattr(getattr(self,'replacements',None),'snapshot',None)
        if snapshot is None:return self._state()
        with snapshot():return self._state()

    def _state(self):
        value=self.jobs.status();cleanups=self.cleanup.status();storage=self.storage_cleanup.status();folders=self.storage_cleanup.folder_status()
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
        if pending and not value['current_job_id']:
            alive=bool(self.cleanup.thread and self.cleanup.thread.is_alive())
            value['state']='Pausing' if (self.cleanup.current or alive) and self.cleanup.stop.is_set() else 'Running' if self.cleanup.current or alive else 'Paused'
            value['queued']+=len(pending)
        errors=[c for c in cleanups if c['state']=='needs_attention']+[r for r in storage if r['state']=='needs_attention']
        if hasattr(self,'replacements'):
            for relation in self.replacements.rows():
                failure=json.loads(relation['failure_json'] or '{}')
                if failure and failure.get('type')!='InterruptedError':errors.append({'job_id':relation['replacement_job_id'],'state':'needs_attention','reason':failure.get('message','Replacement postprocessing needs attention'),'replacement':True})
        folder_notes=[r['reason'] for r in folders if r['state'] in ('needs_attention','unsupported') and r.get('reason')]
        value['failed']+=len(errors)
        if errors and value['state']=='Completed':value['state']='Needs attention'
        progress=None
        if active:
            progress={'phase':'originals','completed':active.get('removed',0),'total':active.get('total',0)} if active['state'] in ('removing','pausing','paused') else {'phase':'checking sources'}
        elif post:progress={'phase':post[1]}
        elif current:progress=phase_progress(current['stage'],current.get('progress'))
        elif errors:
            error=errors[0];current=next((j for j in value['jobs'] if j['job_id']==error['job_id']),None)
            phase='former outputs' if error.get('replacement') else 'originals' if error in cleanups else 'folders' if error in folders else 'temporary'
            progress={'phase':phase,'reason':error['reason']}
            if phase=='originals':progress.update(completed=error['removed'],total=error['total'])
        elif value['state'] in ('Paused','Needs attention'):
            waiting=next((j for j in reversed(value['jobs']) if j['state'] in ('pending','needs attention') and j.get('progress')),None)
            if waiting:current=waiting;progress=phase_progress(waiting['stage'],waiting['progress'])
        if current and (current.get('reason') or errors):
            progress=progress or {'phase':current['stage']}
            progress['reason']=current.get('reason') or next((e['reason'] for e in errors if e['job_id']==current['job_id']),'')
        totals=self.progress_books(raw_jobs,cleanups,storage,folders)
        return {key:value[key] for key in ('state','queued','completed','failed')} | {
            'approved_total':totals['approved'],'converted_total':totals['converted'],'folder_cleanup_notes':list(dict.fromkeys(folder_notes)),
            'current_title':current['manifest']['metadata'].get('title','') if current else '',
            'current_job_id':current['job_id'] if current else None,'attempt_id':current.get('attempt_id') if current else None,
            'progress':progress,'stage':active['status'] if active else progress['phase'] if progress else '',
            'cleanup_active':bool(active or pending or post),'postprocessing_pending':bool(self._pending_replacement_postprocessing()) if hasattr(self,'replacements') else False}

    def pause(self):
        # During a desktop Quit drain the current book finishes; nothing is interrupted.
        if self.draining:return self.state()
        self.cleanup.pause();self.jobs.pause();return self.state()

    def drain(self):
        """Desktop Quit: finish the current book and its cleanup, start nothing new."""
        self.draining=True;self.jobs.drain();return self.state()

    def drained(self):
        jobs=bool(self.jobs._thread and self.jobs._thread.is_alive())
        cleanup=bool(self.cleanup.thread and self.cleanup.thread.is_alive())
        return not jobs and not cleanup and not self.cleanup.current and not self._post_current

    @operation
    def resume(self):
        if self.draining:return self.state() # Quitting: queued books stay saved for the next launch.
        self._no_scan()
        if self.jobs._thread and self.jobs._thread.is_alive():return self.state()
        if self.cleanup.thread and self.cleanup.thread.is_alive():return self.state()
        self.jobs._stop.clear()
        for job in self.jobs.status()['jobs']:
            if job['state']=='completed':self._prune_completed(job['job_id'])
        pending=self.cleanup._rows("SELECT id,intent FROM source_cleanup WHERE state IN ('waiting','paused')")
        historical=[c['id'] for c in pending if json.loads(c['intent']).get('historical')]
        if historical:self.cleanup.resume(historical,follow_audio=False)
        elif pending:self.cleanup.resume()
        else:self.jobs.resume()
        return self.state()

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
            row=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(intent['job_id'],)).fetchone()
            if not row or row['state']!='completed' or packed(json.loads(row['manifest']))!=packed(manifest) or packed(json.loads(row['output']))!=packed(intent['output']):return False
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

    @operation
    def start_historical_cleanup(self,job_id):
        self._no_scan()
        if self.jobs._thread and self.jobs._thread.is_alive() or self.cleanup.thread and self.cleanup.thread.is_alive():raise ValueError('Wait for existing audiobook work to become idle')
        if any(j['state'] in ('pending','running') for j in self.jobs.status()['jobs']):raise ValueError('Unrelated queued audiobook work must be resolved before finite cleanup')
        if any(c['job_id']!=job_id and c['state'] in ('waiting','checking','removing','pausing','paused') for c in self.cleanup.status()):raise ValueError('Unrelated pending source cleanup must be resolved first')
        result=self.enroll_cleanup(job_id,historical=True)
        self.cleanup.resume([result['cleanup_id']],follow_audio=False)
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
        if self.working.in_background:
            if self.jobs._thread and self.jobs._thread.is_alive() or self.cleanup.thread and self.cleanup.thread.is_alive() or self._post_current:
                raise InterruptedError('Foreground audiobook work takes priority over idle working cleanup')

    def _retention_guard(self):
        self._no_scan()
        if self._retention_stop.is_set():raise InterruptedError('Recovery cleanup is closing; remaining copies preserved')

    def _recovery_idle(self):
        self._no_scan()
        if self._retention_stop.is_set():raise ValueError('Recovery cleanup is closing')
        if self.jobs._thread and self.jobs._thread.is_alive() or self.cleanup.thread and self.cleanup.thread.is_alive():raise ValueError('Wait for audiobook work to become idle')
        unfinished=getattr(self.jobs,'has_unfinished',None)
        # Runs once per cleanup row on every status poll: an indexed existence check, not a full job load.
        if unfinished() if unfinished else any(j['state'] in ('pending','running') for j in self.jobs.status()['jobs']):raise ValueError('Resolve queued audiobook work before deleting recovery copies')
        if self.cleanup.current or self._post_current or any(c['state'] in ('waiting','checking','removing','pausing','paused') for c in self.cleanup._rows('SELECT state FROM source_cleanup')):raise ValueError('Wait for source cleanup to finish')

    def recovery_status(self,job_id):
        value=self.recovery.status(job_id)
        try:self._recovery_idle()
        except ValueError as error:value=value|{'eligible':False,'reason':str(error)}
        if self._manual_recovery:value=value|{'eligible':False,'reason':'Recovery deletion is queued'}
        return value

    @operation
    def delete_recovery(self,job_id,token,count,bytes):
        self._recovery_idle()
        if self._manual_recovery:raise ValueError('Recovery deletion is already queued')
        status=self.recovery.status(job_id)
        if not status['eligible']:raise ValueError(status['reason'] or 'No eligible recovery copies remain')
        confirmation={'token':token,'count':count,'bytes':bytes}
        if any(status[k]!=confirmation[k] for k in confirmation):raise ValueError('Recovery copies changed. Review the updated details and try again.')
        self._manual_recovery=(job_id,confirmation);self._retention_wake.set()
        return {'started':True,'job_id':job_id}

    def start_retention(self,admission):
        if self._retention_thread:return
        def work():
            while not self._retention_stop.is_set():
                published_revisits=[]
                # This distinct unpublished-working operation holds only its
                # relevant job/native leases. No central operation/admission lock
                # spans its hashing; foreground start preempts it between blocks.
                try:self.working.reconcile(limit=1,storage=self.storage_cleanup)
                except (InterruptedError,ValueError):pass
                try:
                    with admission():
                        with self.operation_lock:
                            self._recovery_idle()
                            manual=self._manual_recovery
                            selected=[manual[0]] if manual else self.recovery.due()
                            for id in selected:
                                self._recovery_idle();self._post_current=(id,'temporary')
                                try:
                                    self.recovery.purge(id,'manual' if manual else 'automatic',manual[1] if manual else None)
                                    published_revisits.append(id)
                                except InterruptedError:pass # Keep the durable partial purge resumable at startup.
                                except Exception as error:self.recovery._set(id,'needs_attention',str(error)) # Preserve failed/stale sets and report their reason.
                                finally:self._post_current=None
                            if manual:self._manual_recovery=None
                except ValueError:pass # Busy/closing admission defers; never purges while scanning.
                for id in published_revisits:
                    try:self.working.schedule_published(id)
                    except (InterruptedError,ValueError,OSError):pass
                self._retention_wake.wait(60);self._retention_wake.clear()
        self._retention_thread=threading.Thread(target=work,name='books-recovery-retention',daemon=False);self._retention_thread.start()

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

    def _prune_completed(self,job_id,source_completed=False):
        if source_completed:self.working.schedule_published(job_id)
        if hasattr(self,'replacements'):
            relation=self.replacements.get(parent=job_id)
            if relation and relation['state'] in {'retiring','completed'}:
                with connect(self.inventory.database) as db:parent=self.replacements.raw_job(db,job_id)
                if self.retirement.historical_retired(parent):return
        self._prune_working(job_id)
        self.recovery.sync()
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
        # Durable audio success already exists. Cleanup failure must not reset it.
        row=next(j for j in self.jobs.status()['jobs'] if j['job_id']==job_id)
        self._prune_working(job_id)  # Publication is sufficient; retirement is independent.
        try:self.working.discharge_published(job_id,self.storage_cleanup,revisit=True)
        except (OSError,ValueError):pass  # Exact held reason stays in the working ledger.
        if row['manifest'].get('cleanup_policy',{}).get('enabled'):
            try:
                enrolled=self.enroll_cleanup(job_id);id=enrolled['cleanup_id'];self.cleanup.current=id
                self.cleanup.run(id)
            except Exception as error:
                if 'id' in locals():self.cleanup._set(id,'needs_attention',str(error))
                else:self._enrollment_attention(row,error)
            finally:self.cleanup.current=None
        self._prune_completed(job_id)
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
                with DirectoryBoundary(output['root'],ordinary(output['final_path']).parent),VerifiedFile(output['final_path']):
                    if not self._output_valid(output):raise ValueError('New replacement output changed')
                    relation=self.replacements.publish(relation,row,output,storage,True)
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
        with self.reviews.lock,self.inventory.group_lock:
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
            new_id=str(uuid.uuid4());publication_id=str(uuid.uuid4());manifest=prepare_replacement(parent,new_id,plan);manifest['replacement_id']=publication_id
            root=ordinary(manifest['root']);destination=ordinary(manifest['destination'])
            with DirectoryBoundary(root,destination.parent):
                if destination.exists():raise ValueError('Distinct final audiobook already exists; nothing will be overwritten')
            repairs=self.publications._repairs(parent)
            if len(repairs)!=2 or len([r for r in repairs if r['corrected']])!=1:raise ValueError('Both approved chapter-repair receipts are required')
            paths=[{'record':parent['output'],'id':parent_job_id,'journal':None}]+repairs
            old=[]
            for publication in paths:
                record=publication['record'];path=ordinary(record['final_path'])
                with DirectoryBoundary(root,path.parent) as boundary,VerifiedFile(path) as file:
                    if file.facts()['links']!=1 or file.facts()['size']!=record['size']:raise ValueError('Former audiobook identity changed')
                    old.append({'path':str(path),'size':record['size'],'sha256':record['sha256'],'facts':file.facts(),'ancestry':boundary.identities,'publication_id':publication['id'],'journal_sha256':publication.get('journal_sha256')})
            corrected=next(r for r in repairs if r['corrected'])
            previous={'id':corrected['id'],'path':corrected['record']['final_path'],'sha256':corrected['record']['sha256'],'journal_sha256':corrected['journal_sha256']}
            approval={'group_row':group,'context_row':context,'destination':manifest['destination'],'profile':manifest['profile'],'sources':manifest['sources'],
                      'old_outputs':old,'parent_output':parent['output']['final_path'],'source_policy':'KEEP_ALL_40_ORIGINALS','media_plan_sha256':hashlib.sha256(data).hexdigest(),'replacement_manifest':copy.deepcopy(manifest)}
            binding={'id':publication_id,'parent_row':raw,'previous_publication':previous,'approval':approval,'timestamp':replacement_now()}
            job=self.jobs.enqueue(manifest,replacement_context=(self.replacements,binding))
        self.resume()
        return {'job_id':job,'replacement_id':publication_id,'queued':True}

    def candidate_status(self, identity):
        jobs = [j for j in self.jobs.status()['jobs'] if j['manifest']['candidate_id'] == identity]
        if not jobs: return None
        job = jobs[-1]
        state = {'pending':'Queued','running':'Creating','completed':'Audiobook created','needs attention':'Output needs attention'}[job['state']]
        return {'job_id':job['job_id'],'state':state,'stage':job['stage'],'reason':job['reason'],'cleanup':self.cleanup.status(job['job_id']),'cleanup_policy':job['manifest'].get('cleanup_policy',{'enabled':False})}

    def current_audiobook(self,identity):
        if not hasattr(self,'publications'):return {'state':'none','reason':'No verified audiobook created yet','identity':'none'}
        value=self.publications.describe(self.jobs.status()['jobs'],identity)
        return {key:copy.deepcopy(value[key]) for key in ('state','reason','path','identity','publication_id','kind','tags_state') if key in value}

    @operation
    def approve_automatic(self,row,result,stop,client):
        """Private evidence-gated path. HTTP cannot submit an automatic approval."""
        from source_identity import source_gate,VERSION
        from public_research import allowed_url
        from review_backend import image_kind,source_hash,identity
        from audio_pipeline import generated_artifacts,run_owned,probe
        from encoding_policy import choose_encoding,choose_automatic_encoding
        standing=bool(result.get('metadata_facts'))
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
        with self.reviews.lock,self.inventory.group_lock:
            current=self.reviews._row('Audiobooks',row['id'],row['revision']);ctx=self.reviews._context(current)
            if current['fingerprint']!=row['fingerprint']:raise ValueError('Source files changed')
            if self.automatic.manual_draft(current):raise ValueError('Manual draft retained')
            if self.candidate_status(row['id']):raise ValueError('Audiobook job already exists')
            if local:
                from local_identity import revalidate,folder_siblings,catalog_index
                # Any failure to read the folder contents holds this book; it never stops the run.
                try:
                    siblings=folder_siblings(self.inventory.database,current,self.inventory.roots['Audiobooks'])
                    readers=catalog_index(self.inventory.database,self.inventory.roots['Audiobooks'])['readers']
                except Exception:raise ValueError("Folder contents could not be checked; local identity held") from None
                revalidate(current,self.inventory.roots['Audiobooks'],result['metadata_facts']['local_agreement'],siblings,readers)
            reasons=source_gate(current,result['work'])
            if reasons:raise ValueError('; '.join(reasons))
            paths=[m['path'] for m in current['members']]
            with contextlib.ExitStack() as stack:
                for parent in {str(Path(p).parent) for p in paths}:stack.enter_context(DirectoryBoundary(self.inventory.roots['Audiobooks'],parent))
                stack.enter_context(ProtectedFiles(paths))
                for m in current['members']:
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
                        if len(paths)>1 and chaptered:
                            refile={p:n for p,n in chaptered.items() if current.get('split_book') and Path(p).suffix.lower()=='.m4b'}
                            if not refile:raise ValueError('Book parts carry their own chapters; joining them would drop those chapters')
                            from groups import setup_part_chapters
                            sizes={m['path']:(m['size'],str(m['modified'])) for m in current['members']}
                            with connect(self.inventory.database) as db:
                                setup_part_chapters(db)
                                for p,n in sorted(refile.items()):
                                    db.execute('INSERT OR REPLACE INTO part_chapters VALUES(?,?,?,?,?,?)',(self.inventory.roots['Audiobooks'],p,sizes[p][0],sizes[p][1],n,__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()))
                            raise ValueError('Book parts carry their own chapters; each part becomes its own book')
                        part=(result['metadata_facts'].get('local_agreement') or {}).get('part_book') if local else None
                        if part:
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
                            self._recording_review(current,result,stop)
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
                        if stop.is_set() or self.automatic.manual_draft(fresh):raise InterruptedError() if stop.is_set() else ValueError('Manual draft retained')
                        note=('Automatically accepted local-agreement identity (Sergei decision 2026-10-12): embedded tags and file/folder names agree on title and author; only missing fields were searched, unknown optional facts are omitted. All observed sources remain the recording scope.' if local else
                            'Automatically accepted verified work identity and associated author credit under the approved standing rules; source-derived output names, omitted unknown facts and usable embedded/neutral artwork retain honest provenance. All observed sources remain the recording scope.' if standing else 'Automatically accepted fetched public work evidence and independent publisher/journal credit; exact embedded cover pixels match catalog artwork. Source scope remains the observed recording; external recording completeness unknown.')
                        fresh=self.reviews.save('Audiobooks',fresh['id'],fresh['revision'],result['review'],approve=True,manual_note=note,cover_id=selected_cover['id'],actor='assistant',evidence=result['evidence'],automatic_pending={'matcher_version':VERSION,'work_id':result['work']['id']},automatic_facts=result.get('metadata_facts'))
                        context=self.reviews._context(fresh);context['duplicate_review']=copy.deepcopy(result.get('duplicate_review'));context['metadata_approved']=False;context['automatic_pending']={'matcher_version':VERSION,'work_id':result['work']['id']}
                        fresh=self.reviews._write(fresh,context,bump=False)
                        keys=[m['member_key'] for m in fresh['members']]
                        if stop.is_set():raise InterruptedError()
                        fresh=self.reviews.tracks('Audiobooks',fresh['id'],fresh['revision'],keys,keys,True,True,len(keys)>1,actor='assistant',evidence_note='Automatic recording scope: consistent verified work album/source identity; embedded gap-free unique track/disc order, or one self-contained source. All observed source files selected and SHA256 verified; commercial recording completeness unknown.',stop=stop)
                        with self.automatic.lock:
                            if stop.is_set() or self.automatic.manual_draft(fresh):raise InterruptedError() if stop.is_set() else ValueError('Manual draft retained')
                            context=self.reviews._context(fresh);context['metadata_approved']=True
                            # Pending metadata stays invisible to approval counts/public creation.
                            fresh=self.reviews._write(fresh,context,bump=False)
                            try:
                                manifest=self.reviews.build_manifest('Audiobooks',fresh['id'],fresh['revision'],allow_automatic_pending=True,stop=stop)
                                approved=copy.deepcopy(context);approved.pop('automatic_pending',None)
                                approved['automatic_approval']={'matcher_version':VERSION,'work_id':result['work']['id'],'sources':result['sources'],'approved_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
                                # Queue insertion and final approval become durable together.
                                job=self.jobs.enqueue(manifest,approval_context=(fresh['id'],fresh['revision'],context,approved))
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
        self.resume()
        return fresh,job

    def retry_automatic_job(self,job_id,now):
        self._no_scan()
        from failed_m4b_retry import eligible
        parent=next(iter(self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))),None)
        if parent and eligible(parent):
            result=self._retry_preserved_m4b(parent,now)
            if result.get('requeued'):self.resume()
            return result
        result=self.jobs.retry_failed(job_id,now)
        if result.get('requeued'):self.resume()
        return result

    def _retry_preserved_m4b(self,parent,now):
        """Admit one new child, retaining the failed parent's entire durable row."""
        from failed_m4b_retry import bind,profile_proof
        result={'retryable':True,'retry_at':now+3600,'requeued':False}
        if self.jobs._thread and self.jobs._thread.is_alive():return result
        manifest=json.loads(parent['manifest'])
        # Old attempts predate receipt-owned lifecycle cleanup. Never clone their
        # compressed source or generated candidates while that debt is retained.
        job_root=self.stage_root/parent['job_id']
        try:
            with DirectoryBoundary(self.stage_root.anchor,self.stage_root):
                if job_root.exists():
                    with DirectoryBoundary(job_root.anchor,job_root):
                        for attempt in job_root.iterdir():
                            if not attempt.is_dir():continue
                            with DirectoryBoundary(attempt.anchor,attempt):
                                if any(p.suffix.lower() in {'.m4b','.wav'} for p in attempt.iterdir()):
                                    return result|{'reason':'Prior audio working files need verified disposal before another source copy'}
        except (ValueError,OSError) as error:
            return result|{'reason':'Prior working-file ownership requires attention: '+str(error)}
        from source_cleanup import single_stream
        import m4b_preservation
        try:
            with contextlib.ExitStack() as holds:
                source=ordinary(manifest['sources'][0]['path'])
                holds.enter_context(DirectoryBoundary(manifest['root'],source.parent))
                held=holds.enter_context(VerifiedFile(source));single_stream(source)
                if held.facts()['links']!=1:raise ValueError('Source alias is not eligible for repaired admission')
                module=Path(m4b_preservation.__file__).absolute()
                holds.enter_context(DirectoryBoundary(module.anchor,module.parent))
                module_file=holds.enter_context(VerifiedFile(module))
                with connect(self.inventory.database) as db:
                    group_before=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=?',(manifest['candidate_id'],)).fetchone()
                    context_before=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(manifest['candidate_id'],)).fetchone()
                if not group_before or not context_before:raise ValueError('Reviewed candidate unavailable')
                fresh=self.reviews.build_manifest('Audiobooks',manifest['candidate_id'],manifest['candidate_revision'],allow_existing_job=True,stop=self.automatic.stop_event)
                title=fresh['metadata'].get('title')
                if not isinstance(title,str) or not title:raise ValueError('Approved title unavailable')
                with source.open('rb') as reader:
                    def read_at(offset,count):
                        if self.automatic.stop_event.is_set():raise InterruptedError('Automatic processing stopped')
                        reader.seek(offset);return reader.read(count)
                    profile=m4b_preservation.plan(held.facts()['size'],read_at,{'title':title},None)
                proof=profile_proof(profile,module_file.sha256())
                fresh=bind(parent,fresh,proof)
                with connect(self.inventory.database) as db:
                    group=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=?',(fresh['candidate_id'],)).fetchone()
                    context=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(fresh['candidate_id'],)).fetchone()
                if not group or not context or tuple(group)!=tuple(group_before) or tuple(context)!=tuple(context_before):raise ValueError('Reviewed candidate changed during source proof')
                child=self.jobs.enqueue(fresh,repair_context=(parent,tuple(group),tuple(context)))
                return result|{'requeued':True,'job_id':child,'parent_job_id':parent['job_id'],'reason':'Source-preserving M4B repair admitted as new work'}
        except InterruptedError:raise
        except (ValueError,OSError,sqlite3.Error) as error:
            return result|{'reason':'Failed M4B retained: '+str(error)}

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

    def _guard(self, manifest):
        try:
            self._no_scan()
            if manifest.get('replacement_id'):
                relation=self.replacements.get(new_job=manifest['job_id'])
                if not relation or relation['id']!=manifest['replacement_id'] or relation['state']!='queued':return False
                with connect(self.inventory.database) as db:raw=self.replacements.raw_job(db,manifest['job_id'])
                frozen={k:v for k,v in manifest.items() if k!='attempt_id'}
                return json.loads(raw['manifest'])==frozen and self._replacement_guard(relation)
            current=self.reviews.build_manifest('Audiobooks',manifest['candidate_id'],manifest['candidate_revision'],allow_existing_job=True)
            def frozen(value):return {k:v for k,v in value.items() if k not in ('job_id','attempt_id')}
            return frozen(current)==frozen(manifest)
        except (ValueError,OSError,KeyError):return False

    def _run(self, manifest, stop, checkpoint):
        stages={'Checking sources':'checking sources','Creating audio':'creating','Checking output':'checking'}
        output, validation=create_private(manifest,self.stage_root,stop,lambda stage,info:checkpoint(stages[stage],info),artifact_observer=self.working)
        if manifest.get('replacement_id'):
            from replacement_media import verify_replacement
            validation=verify_replacement(manifest,validation,output,output.parent,stop)
        record={}
        def journal(stage, details):
            if stage=='completed':return
            if stage=='copying':self._register(details['temporary'],manifest['job_id'],'temporary')
            if stage=='publishing':
                record.update(job_id=manifest['job_id'],final_path=details['destination'],owned_temp=details['temporary'],
                    sha256=validation['sha256'],size=validation['size'],root=manifest['root'],
                    candidate_id=manifest['candidate_id'],candidate_revision=manifest['candidate_revision'],
                    validation={'passed':True,**validation},parent_identity=details['parent_identity'])
                checkpoint('publishing',copy.deepcopy(record))
            else:checkpoint(stage,details)
        with ProtectedFiles([output]):
            publish(output,manifest,validation,stop,journal,lambda:self._guard(manifest),self._review_boundary())
        self._register(record['final_path'],manifest['job_id'],'output',record['sha256'],record['size'])
        return record

    def _output_valid(self, record):
        try:
            root=ordinary(record['root']); final=ordinary(record['final_path'])
            if os.path.normcase(str(root)) != os.path.normcase(self.inventory.roots['Audiobooks']):return False
            if final.suffix.lower()!='.m4b' or record['validation'].get('profile') not in {PROFILE,LEGACY_PROFILE,AUTOMATIC_PROFILE}:return False
            with DirectoryBoundary(root,final.parent) as boundary, ProtectedFiles([final]):
                if record.get('parent_identity')!=[list(i) for i in boundary.identities]:
                    # In-memory records contain tuples, persisted JSON contains lists.
                    if record.get('parent_identity')!=boundary.identities:return False
                valid=fingerprint(final)['size']==record['size'] and digest(final)==record['sha256']
                if valid:
                    stat=final.stat()
                    self._validated_outputs[record['job_id']]=(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns)
                return valid
        except (ValueError,OSError,KeyError):return False

    def close(self):
        if hasattr(self,'automatic'):self.automatic.close()
        self._retention_stop.set();self._retention_wake.set()
        if self._retention_thread:
            self._retention_thread.join(30)
            if self._retention_thread.is_alive():raise TimeoutError('Recovery cleanup is reaching its safe file checkpoint')
        self.jobs.close()
        if hasattr(self,'publications'):self.publications.close()
        self.cleanup.close()

    @staticmethod
    def file_id(library,path):
        return hashlib.sha256((library+'\x1f'+path).encode('utf-8')).hexdigest()

    def _file_record(self,library,identity):
        root=self.inventory.roots[library]
        with connect(self.inventory.database) as db:
            rows=db.execute('SELECT * FROM files WHERE root=?',(root,)).fetchall()
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
            cover={'status':'Cover could not be read','error':source.get('error') or 'Source is missing','label':'Source cover'}
        else:
            try:
                library=next(k for k,v in self.inventory.roots.items() if os.path.normcase(v)==os.path.normcase(source.get('root',self.inventory.roots['Audiobooks'])))
                with DirectoryBoundary(self.inventory.roots[library],Path(source['path']).parent):
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

    def open_folder(self,library,view,identity,folder_kind='source',directory_id=None):
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
        elif folder_kind=='output' and view=='candidates':
            self.reviews._row(library,identity)
            jobs=self.jobs.status()['jobs'];current=self.publications.describe(jobs,identity)
            if current['state']!='verified':raise ValueError(current.get('reason','Current audiobook unavailable'))
            publication=self.publications.publication(jobs,identity)
            with self.publications.protected(publication) as (_,key):
                if key!=current['identity']:raise ValueError('Current audiobook changed before folder opening')
                directory=str(Path(current['path']).parent)
                self.dispatch_folder(directory)
                return {'opened':True,'directory':directory}
        else:raise ValueError('Unknown folder target')
        with DirectoryBoundary(root,directory):self.dispatch_folder(directory)
        return {'opened':True}

    @staticmethod
    def dispatch_folder(directory):
        # Only a user-click route calls this; tests replace it with a mock.
        import ctypes
        buffer=ctypes.create_unicode_buffer(32768)
        if not ctypes.windll.kernel32.GetWindowsDirectoryW(buffer,len(buffer)):raise OSError('Windows folder launcher unavailable')
        subprocess.Popen([str(Path(buffer.value)/'explorer.exe'),str(directory)],shell=False)
