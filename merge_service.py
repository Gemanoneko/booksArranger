"""Join reviewed candidates to the durable, source-preserving media queue."""
from encoding_policy import LEGACY_PROFILE
import contextlib
import copy
import json
import os
from pathlib import Path
import threading
import hashlib
import uuid
import subprocess
import functools

from audio_jobs import AudioJobs
from audio_pipeline import create_private, publish, digest, fingerprint, Paused, PROFILE
from native_io import DirectoryBoundary, ProtectedFiles, ordinary
from review_backend import CandidateReviewService
from scanner import connect
from metadata import propose
from source_cleanup import CleanupJobs, packed
from review_backend import member_key
from conversion_progress import approved_scope,completed_book,phase_progress
import groups

INITIAL_CLEANUP_JOBS={'0b6fedcc-2d95-46a9-a4a3-4192da37ff72','dc4874af-e132-47cd-93ab-85e5b0fbeea7'}

def operation(method):
    @functools.wraps(method)
    def locked(self,*args,**kwargs):
        with self.operation_lock:return method(self,*args,**kwargs)
    return locked


class MergeService:
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
        self.jobs = AudioJobs(inventory.database, self._run, self._guard, self._output_valid)
        self.cleanup = CleanupJobs(inventory.database,self.cache_dir.parent/'source-recovery',self._cleanup_guard,self._review_boundary)
        self.cleanup.stop=self.jobs._stop
        self.jobs.after_completed=self._after_completed
        self.cleanup.after_drain=lambda:self.jobs.resume()
        from storage_cleanup import StorageCleanup
        self.storage_cleanup=StorageCleanup(inventory.database,self.stage_root,self.cleanup.root,self._storage_guard)
        from recovery_retention import RecoveryRetention
        self.recovery=RecoveryRetention(self.storage_cleanup,guard=self._retention_guard)
        self.cleanup.recovery_status=self.recovery_status
        self._retention_stop=threading.Event();self._retention_wake=threading.Event();self._retention_thread=None;self._manual_recovery=None
        self.cleanup.on_completed=self._prune_completed
        self.reviews.set_jobs(self)
        from automatic_processing import AutomaticProcessing
        self.automatic=AutomaticProcessing(self)
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
                    if approved_scope(row,ctx,member_key):approved[row['id']]=(row,ctx)
                self._approved_cache=(signature,approved)
            approved={}
            for id,(row,ctx) in self._approved_cache[1].items():
                if any((self.reviews.cache/(ctx['cover_id']+suffix)).is_file() for suffix in ('.png','.jpg')):approved[id]=(row,ctx)
            source_by={r['job_id']:r for r in cleanups};storage_by={r['job_id']:r for r in storage};folder_by={r['job_id']:r for r in folders}
            converted=set()
            for job in jobs:
                id=job['manifest']['candidate_id']
                if id not in approved:continue
                row,ctx=approved[id];record=job.get('output') or {};current=False
                try:
                    stat=Path(record['final_path']).stat()
                    current=(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns)==self._validated_outputs.get(job['job_id'])
                except (OSError,KeyError):pass
                if completed_book(row,ctx,job,source_by.get(job['job_id']),storage_by.get(job['job_id']),folder_by.get(job['job_id']),current,member_key,PROFILE):converted.add(id)
            return {'approved':len(approved),'converted':len(converted),'converted_ids':converted}

    def state(self):
        value=self.jobs.status();cleanups=self.cleanup.status();storage=self.storage_cleanup.status();folders=self.storage_cleanup.folder_status()
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
            phase='originals' if error in cleanups else 'folders' if error in folders else 'temporary'
            progress={'phase':phase,'reason':error['reason']}
            if phase=='originals':progress.update(completed=error['removed'],total=error['total'])
        elif value['state'] in ('Paused','Needs attention'):
            waiting=next((j for j in reversed(value['jobs']) if j['state'] in ('pending','needs attention') and j.get('progress')),None)
            if waiting:current=waiting;progress=phase_progress(waiting['stage'],waiting['progress'])
        if current and (current.get('reason') or errors):
            progress=progress or {'phase':current['stage']}
            progress['reason']=current.get('reason') or next((e['reason'] for e in errors if e['job_id']==current['job_id']),'')
        totals=self.progress_books(value['jobs'],cleanups,storage,folders)
        return {key:value[key] for key in ('state','queued','completed','failed')} | {
            'approved_total':totals['approved'],'converted_total':totals['converted'],'folder_cleanup_notes':list(dict.fromkeys(folder_notes)),
            'current_title':current['manifest']['metadata'].get('title','') if current else '',
            'current_job_id':current['job_id'] if current else None,'attempt_id':current.get('attempt_id') if current else None,
            'progress':progress,'stage':active['status'] if active else progress['phase'] if progress else '',
            'cleanup_active':bool(active or pending or post)}

    def pause(self):
        self.cleanup.pause();self.jobs.pause();return self.state()

    @operation
    def resume(self):
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

    def _retention_guard(self):
        self._no_scan()
        if self._retention_stop.is_set():raise InterruptedError('Recovery cleanup is closing; remaining copies preserved')

    def _recovery_idle(self):
        self._no_scan()
        if self._retention_stop.is_set():raise ValueError('Recovery cleanup is closing')
        if self.jobs._thread and self.jobs._thread.is_alive() or self.cleanup.thread and self.cleanup.thread.is_alive():raise ValueError('Wait for audiobook work to become idle')
        if any(j['state'] in ('pending','running') for j in self.jobs.status()['jobs']):raise ValueError('Resolve queued audiobook work before deleting recovery copies')
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
                try:
                    with admission():
                        with self.operation_lock:
                            self._recovery_idle()
                            manual=self._manual_recovery
                            selected=[manual[0]] if manual else self.recovery.due()
                            for id in selected:
                                self._recovery_idle();self._post_current=(id,'temporary')
                                try:self.recovery.purge(id,'manual' if manual else 'automatic',manual[1] if manual else None)
                                except InterruptedError:pass # Keep the durable partial purge resumable at startup.
                                except Exception as error:self.recovery._set(id,'needs_attention',str(error)) # Preserve failed/stale sets and report their reason.
                                finally:self._post_current=None
                            if manual:self._manual_recovery=None
                except ValueError:pass # Busy/closing admission defers; never purges while scanning.
                self._retention_wake.wait(60);self._retention_wake.clear()
        self._retention_thread=threading.Thread(target=work,name='books-recovery-retention',daemon=False);self._retention_thread.start()

    def _prune_completed(self,job_id):
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
        if row['manifest'].get('cleanup_policy',{}).get('enabled'):
            try:
                enrolled=self.enroll_cleanup(job_id);id=enrolled['cleanup_id'];self.cleanup.current=id
                self.cleanup.run(id)
            except Exception as error:
                if 'id' in locals():self.cleanup._set(id,'needs_attention',str(error))
                else:self._enrollment_attention(row,error)
            finally:self.cleanup.current=None
        self._prune_completed(job_id)

    def candidate_status(self, identity):
        jobs = [j for j in self.jobs.status()['jobs'] if j['manifest']['candidate_id'] == identity]
        if not jobs: return None
        job = jobs[-1]
        state = {'pending':'Queued','running':'Creating','completed':'Audiobook created','needs attention':'Output needs attention'}[job['state']]
        return {'job_id':job['job_id'],'state':state,'stage':job['stage'],'reason':job['reason'],'cleanup':self.cleanup.status(job['job_id']),'cleanup_policy':job['manifest'].get('cleanup_policy',{'enabled':False})}

    @operation
    def approve_automatic(self,row,result,stop,client):
        """Private evidence-gated path. HTTP cannot submit an automatic approval."""
        from source_identity import source_gate,VERSION
        from public_research import allowed_url
        from review_backend import image_kind,source_hash,identity
        from audio_pipeline import generated_artifacts,run_owned,probe
        from encoding_policy import choose_encoding
        from native_io import VerifiedFile
        from source_cleanup import single_stream
        import shutil
        if stop.is_set():raise InterruptedError()
        if result.get('reasons') or not result.get('work') or not result.get('review'):raise ValueError('Book identity uncertain')
        primary=[s for s in result.get('sources',[]) if s.get('kind')=='publisher_or_journal' and s.get('verified_identity')]
        if not primary:raise ValueError('Author and work not independently verified')
        with self.reviews.lock,self.inventory.group_lock:
            current=self.reviews._row('Audiobooks',row['id'],row['revision']);ctx=self.reviews._context(current)
            if current['fingerprint']!=row['fingerprint']:raise ValueError('Source files changed')
            if self.automatic.manual_draft(current):raise ValueError('Manual draft retained')
            if self.candidate_status(row['id']):raise ValueError('Audiobook job already exists')
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
                        profiles=[]
                        for path in paths:
                            raw_profile=probe(path,self.reviews.cache,stop)
                            member=next(m for m in current['members'] if m['path']==path)
                            observed={k.casefold():v for k,v in raw_profile.get('format',{}).get('tags',{}).items()}
                            catalog={k.casefold():v for k,v in member.get('metadata',{}).get('tags',{}).items()}
                            if observed!=catalog:raise ValueError('Source embedded identity or order evidence changed')
                            streams=[s for s in raw_profile.get('streams',[]) if s.get('codec_type')=='audio']
                            if len(streams)!=1:raise ValueError('Audio format needs an encoding decision')
                            stream=streams[0];profiles.append((stream.get('codec_name'),stream.get('sample_rate'),stream.get('channels'),stream.get('bit_rate')))
                        try:choose_encoding(profiles)
                        except (ValueError,TypeError):raise ValueError('Audio format needs an encoding decision') from None
                        fresh=self.reviews.covers('Audiobooks',current['id'],current['revision'],all_embedded=True,stop=stop)
                        if stop.is_set():raise InterruptedError('Automatic cover inspection paused')
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
                        if stop.is_set() or self.automatic.manual_draft(fresh):raise InterruptedError() if stop.is_set() else ValueError('Manual draft retained')
                        note='Automatically accepted fetched public work evidence and independent publisher/journal credit; exact embedded cover pixels match catalog artwork. Source scope remains the observed recording; external recording completeness unknown.'
                        fresh=self.reviews.save('Audiobooks',fresh['id'],fresh['revision'],result['review'],approve=True,manual_note=note,cover_id=covers[0]['id'],actor='assistant',evidence=result['evidence'],automatic_pending={'matcher_version':VERSION,'work_id':result['work']['id']})
                        context=self.reviews._context(fresh);context['metadata_approved']=False;context['automatic_pending']={'matcher_version':VERSION,'work_id':result['work']['id']}
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
            current=self.reviews.build_manifest('Audiobooks',manifest['candidate_id'],manifest['candidate_revision'],allow_existing_job=True)
            def frozen(value):return {k:v for k,v in value.items() if k not in ('job_id','attempt_id')}
            return frozen(current)==frozen(manifest)
        except (ValueError,OSError,KeyError):return False

    def _run(self, manifest, stop, checkpoint):
        stages={'Checking sources':'checking sources','Creating audio':'creating','Checking output':'checking'}
        output, validation=create_private(manifest,self.stage_root,stop,lambda stage,info:checkpoint(stages[stage],info))
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
            if final.suffix.lower()!='.m4b' or record['validation'].get('profile') not in {PROFILE,LEGACY_PROFILE}:return False
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
        directories=self._source_directories(library,view,identity);sections=[];completed=None
        if view=='files':
            source=self._file_record(library,identity);sections.append(self._source_section(source))
            review=json.loads(source['review']) if source['review'] else None
            if review:sections.append({'kind':'draft','heading':'Sorting preview metadata','status':'Preview — source tags unchanged','facts':self._review_facts(review),'cover':{'status':'No selected cover'},'raw_tags':review})
        else:
            row=self.reviews.enrich(self.reviews._row(library,identity));metadata=row['metadata']
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
            completed=self._completed_output(identity)
            if completed:
                output=completed['output'];cover=completed['manifest']['cover']
                cleanup=self.cleanup.status(completed['job_id']);cleanup_facts=[]
                if cleanup:
                    cleanup_facts=[{'label':label,'value':value} for label,value in [('Source cleanup',cleanup['status']),('Originals removed',cleanup['removed']),('Originals remaining',cleanup['remaining']),('Removed from Z: (bytes)',cleanup['bytes_removed']),('Recovery copies (bytes)',cleanup['recovery_bytes']),('Recovery location',cleanup['recovery_location']),('Recovery','Temporary recovery files were removed after successful cleanup. Original tracks cannot be restored from them.' if cleanup.get('recovery',{}).get('state')=='deleted' else 'Remaining temporary recovery copies can restore original tracks. Existing files are never overwritten.' if cleanup['restore_available'] else 'Temporary recovery files are unavailable; see cleanup status.')]]
                sections.append({'kind':'created','heading':'Created audiobook metadata','status':'Output checks passed; Apple Books sync not checked','path':output['final_path'],
                    'facts':self._output_facts(output['validation']['tags'])+cleanup_facts,
                    'cover':{**cover,'label':'Created audiobook cover','status':'Validated attached cover'},'raw_tags':output['validation']['tags'],'member_values':[]})
        return {'inspector':{'id':identity,'view':view,'heading':'Metadata and cover','sections':sections,'source_directories':directories,
            'source_directory_count':len(directories),'output_folder_available':bool(completed)}}

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
            output=self._completed_output(identity)
            if not output:raise ValueError('No validated created output folder is available')
            directory=str(Path(output['output']['final_path']).parent)
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
