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
        self.reviews.set_jobs(self)
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

    def state(self):
        value = self.jobs.status()
        current = next((j for j in value['jobs'] if j['job_id'] == value['current_job_id']), None)
        cleanups=self.cleanup.status();pending=[c for c in cleanups if c['state'] in ('waiting','checking','removing','pausing','paused')]
        active=next((c for c in pending if c['id']==self.cleanup.current),None)
        if pending and not current:
            alive=bool(self.cleanup.thread and self.cleanup.thread.is_alive())
            value['state']='Pausing' if (active or alive) and self.cleanup.stop.is_set() else 'Running' if active or alive else 'Paused'
            value['queued']+=len(pending)
        value['failed']+=sum(c['state']=='needs_attention' for c in cleanups)
        return {key: value[key] for key in ('state','queued','completed','failed')} | {
            'current_title': current['manifest']['metadata'].get('title','') if current else '',
            'stage': active['status'] if active else value['current_stage'] or '', 'cleanup_active':bool(active or pending)}

    def pause(self):
        self.cleanup.pause();self.jobs.pause();return self.state()

    @operation
    def resume(self):
        self._no_scan()
        if self.jobs._thread and self.jobs._thread.is_alive():return self.state()
        if self.cleanup.thread and self.cleanup.thread.is_alive():return self.state()
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

    def _after_completed(self,job_id):
        # Durable audio success already exists. Cleanup failure must not reset it.
        row=next(j for j in self.jobs.status()['jobs'] if j['job_id']==job_id)
        if not row['manifest'].get('cleanup_policy',{}).get('enabled'):return
        try:
            enrolled=self.enroll_cleanup(job_id);id=enrolled['cleanup_id'];self.cleanup.current=id
            self.cleanup.run(id)
        except Exception as error:
            if 'id' in locals():self.cleanup._set(id,'needs_attention',str(error))
            else:
                # Enrollment failure is visible without inventing removal facts.
                self._enrollment_attention(row,error)
        finally:self.cleanup.current=None

    def candidate_status(self, identity):
        jobs = [j for j in self.jobs.status()['jobs'] if j['manifest']['candidate_id'] == identity]
        if not jobs: return None
        job = jobs[-1]
        state = {'pending':'Queued','running':'Creating','completed':'Audiobook created','needs attention':'Output needs attention'}[job['state']]
        return {'job_id':job['job_id'],'state':state,'stage':job['stage'],'reason':job['reason'],'cleanup':self.cleanup.status(job['job_id']),'cleanup_policy':job['manifest'].get('cleanup_policy',{'enabled':False})}

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
                return fingerprint(final)['size']==record['size'] and digest(final)==record['sha256']
        except (ValueError,OSError,KeyError):return False

    def close(self):
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
                    cleanup_facts=[{'label':label,'value':value} for label,value in [('Source cleanup',cleanup['status']),('Originals removed',cleanup['removed']),('Originals remaining',cleanup['remaining']),('Removed from Z: (bytes)',cleanup['bytes_removed']),('Recovery copies (bytes)',cleanup['recovery_bytes']),('Recovery location',cleanup['recovery_location']),('Recovery','Recovery copies can restore the original tracks. Existing files are never overwritten.')]]
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
