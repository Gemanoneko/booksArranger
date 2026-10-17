"""Read-only current publication views, bound to native identities and receipts."""
import contextlib
import copy
import hashlib
import json
import queue
import threading
import uuid
from pathlib import Path
from native_io import DirectoryBoundary, VerifiedFile, ordinary, BoundaryError
from replacement_jobs import packed, digest

class CurrentAudiobooks:
    def __init__(self,library,repairs,replacements,verified=None,remember=None,pace=None):
        self.library=ordinary(library);self.repairs=ordinary(repairs);self.replacements=replacements
        # Optional persisted verification: verified(record) answers from the last full hash when the
        # file identity is unchanged; remember(record) records a new full hash; pace(n, stop) limits reads.
        self.verified=verified;self.remember=remember;self.pace=pace
        self._lock=threading.RLock();self._cache={};self._pending=set();self._work=queue.Queue(maxsize=32)
        self._stop=threading.Event();self._thread=None

    @staticmethod
    def _read_journal(root,path):
        with DirectoryBoundary(root,path.parent) as boundary,VerifiedFile(path) as file:
            facts=file.facts()
            if facts['links']!=1 or facts['size']>2*1024*1024:raise BoundaryError('Chapter publication receipt is not a bounded ordinary file')
            data=b''.join(file.chunks())
            if not data.endswith(b'\n'):raise BoundaryError('Chapter publication receipt is incomplete')
            rows=[json.loads(line) for line in data.decode('utf-8').splitlines()]
            return rows,hashlib.sha256(data).hexdigest(),facts,boundary.identities

    def _repairs(self,parent):
        if not self.repairs.exists():return []
        with DirectoryBoundary(self.repairs.anchor,self.repairs):
            directories=list(self.repairs.iterdir())
            if len(directories)>256:raise BoundaryError('Chapter publication registry exceeds its bound')
        result=[]
        for directory in directories:
            try:repair_id=str(uuid.UUID(directory.name))
            except ValueError:continue
            path=directory/'corrected-artifact.jsonl'
            if not path.exists():continue
            rows,sha,facts,ancestry=self._read_journal(self.repairs,path)
            if not rows or any(r.get('parent_job_id')!=rows[0].get('parent_job_id') for r in rows):raise BoundaryError('Chapter publication parent is ambiguous')
            if rows[0]['parent_job_id']!=parent['job_id']:continue
            if any(r.get('job_id')!=repair_id for r in rows) or [r.get('state') for r in rows]!=['intent','validated','copying','publishing','completed']:
                raise BoundaryError('Recorded chapter update is incomplete')
            intent=rows[0]['data'];validation=rows[1]['data'];copying=rows[2]['data'];publishing=rows[3]['data'];completed=rows[4]['data']
            manifest=parent['manifest'];output=parent['output'];base=ordinary(output['final_path'])
            normalized=validation.get('chapter_format',{}).get('description',{})
            corrected=normalized.get('entry_size')==65 and normalized.get('font_name')=='Arial' and normalized.get('layout')=='Apple QTFF legacy text'
            expected=base.with_name(base.stem+(' - Chapters v2.m4b' if corrected else ' - Chapters.m4b'))
            if (intent.get('parent_output')!=str(base) or intent.get('parent_sha256')!=output['sha256'] or intent.get('parent_size')!=output['size'] or
                    intent.get('parent_manifest_sha256')!=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest() or
                    intent.get('candidate_id')!=manifest['candidate_id'] or intent.get('candidate_revision')!=manifest['candidate_revision'] or
                    intent.get('sources')!=manifest['sources'] or intent.get('cover')!=manifest['cover'] or intent.get('root')!=manifest['root'] or
                    intent.get('profile')!=manifest['profile'] or intent.get('mode')!='copy existing validated AAC; source-track navigation'):
                raise BoundaryError('Recorded chapter update no longer matches its reviewed parent')
            if any(part.get('destination')!=str(expected) for part in (intent,copying,publishing,completed)) or any(part.get('validation')!=validation for part in (copying,publishing,completed)):
                raise BoundaryError('Chapter publication intent and completed proof disagree')
            if validation.get('chapters')!=intent.get('chapters') or validation.get('cover_sha256')!=manifest['cover']['sha256'] or validation.get('profile')!=manifest['profile']:
                raise BoundaryError('Chapter publication content proof disagrees')
            record={'job_id':parent['job_id'],'root':manifest['root'],'final_path':str(expected),'size':validation['size'],'sha256':validation['sha256'],
                    'parent_identity':publishing['parent_identity'],'validation':validation}
            result.append({'id':repair_id,'kind':'chapter_update','record':record,'journal':str(path),'journal_sha256':sha,'journal_facts':facts,
                           'journal_ancestry':ancestry,'corrected':corrected,'saved_tags':copy.deepcopy(output['validation'].get('tags',{})),
                           'cover':copy.deepcopy(manifest['cover']),'parent':parent})
        return result

    def publication(self,jobs,candidate):
        parent,relation=self.replacements.representative(jobs,candidate)
        if not parent:return None
        if relation and relation['state'] in {'published','retiring','completed'}:
            if not self.replacements.structural_guard(relation):raise BoundaryError('Current replacement lineage or publication proof changed')
            if parent['job_id']!=relation['replacement_job_id'] or parent['state']!='completed' or parent.get('output')!=json.loads(relation['current_output_json']):
                raise BoundaryError('Current replacement publication changed')
            return {'id':relation['id'],'kind':'replacement','record':copy.deepcopy(parent['output']),'relation':relation,'parent':parent,'cover':copy.deepcopy(parent['manifest']['cover'])}
        if parent['state']!='completed':return None
        repairs=self._repairs(parent)
        corrected=[r for r in repairs if r['corrected']]
        choices=corrected or repairs
        if len(choices)>1:raise BoundaryError('Current chapter publication is ambiguous')
        if choices:return choices[0]
        return {'id':parent['job_id'],'kind':'original','record':copy.deepcopy(parent['output']),'parent':parent,'cover':copy.deepcopy(parent['manifest']['cover'])}

    @contextlib.contextmanager
    def protect_former(self,relation,parent_row):
        """Hold authoritative former repair receipts, never the leaf files to be disposed."""
        if digest(parent_row)!=relation['parent_record_sha256']:raise BoundaryError('Original publication history changed')
        parent={'job_id':parent_row['job_id'],'state':parent_row['state'],'manifest':json.loads(parent_row['manifest']),'output':json.loads(parent_row['output'])}
        base=ordinary(parent['output']['final_path']);expected={str(base),str(base.with_name(base.stem+' - Chapters.m4b')),str(base.with_name(base.stem+' - Chapters v2.m4b'))}
        approval=json.loads(relation['approval_json']);old=approval['old_outputs']
        if len(old)!=3 or {p['path'] for p in old}!=expected:raise BoundaryError('Former publication path set is not the exact approved three')
        repairs=self._repairs(parent)
        if len(repairs)!=2 or len([r for r in repairs if r['corrected']])!=1:raise BoundaryError('Both authoritative chapter publications are required')
        with contextlib.ExitStack() as stack:
            for proof in old:
                if proof['path']==str(base):
                    if proof.get('publication_id')!=parent['job_id'] or proof['sha256']!=parent['output']['sha256'] or proof['size']!=parent['output']['size'] or proof.get('journal_sha256') is not None:raise BoundaryError('Former base publication proof changed')
                    continue
                publication=next((r for r in repairs if r['record']['final_path']==proof['path']),None)
                if not publication or proof.get('publication_id')!=publication['id'] or proof.get('journal_sha256')!=publication['journal_sha256'] or proof['sha256']!=publication['record']['sha256'] or proof['size']!=publication['record']['size']:
                    raise BoundaryError('Former chapter publication no longer matches its authoritative receipt')
                path=ordinary(publication['journal']);boundary=stack.enter_context(DirectoryBoundary(self.repairs,path.parent));file=stack.enter_context(VerifiedFile(path))
                if file.facts()!=publication['journal_facts'] or boundary.identities!=publication['journal_ancestry'] or file.sha256()!=publication['journal_sha256']:raise BoundaryError('Former publication receipt changed during protection')
            yield

    @contextlib.contextmanager
    def protected(self,publication):
        record=publication['record'];path=ordinary(record['final_path'])
        if ordinary(record['root'])!=self.library or not path.is_relative_to(self.library) or path.suffix.lower()!='.m4b':raise BoundaryError('Current publication is outside its library')
        with contextlib.ExitStack() as stack:
            boundary=stack.enter_context(DirectoryBoundary(self.library,path.parent));file=stack.enter_context(VerifiedFile(path));facts=file.facts()
            if facts['links']!=1 or facts['size']!=record['size'] or [list(v) for v in boundary.identities]!=[list(v) for v in record['parent_identity']]:
                raise BoundaryError('Current audiobook native identity or ancestry changed')
            journal_key=None
            if publication.get('journal'):
                journal_path=ordinary(publication['journal'])
                journal_boundary=stack.enter_context(DirectoryBoundary(self.repairs,journal_path.parent))
                journal_file=stack.enter_context(VerifiedFile(journal_path));jfacts=journal_file.facts();jancestry=journal_boundary.identities
                if jfacts['links']!=1 or jfacts['size']>2*1024*1024:raise BoundaryError('Chapter receipt is not a bounded ordinary file')
                sha=journal_file.sha256()
                if sha!=publication['journal_sha256'] or jfacts!=publication['journal_facts'] or jancestry!=publication['journal_ancestry']:raise BoundaryError('Current publication receipt changed')
                journal_key=sha
            key=digest({'id':publication['id'],'kind':publication['kind'],'record':record,'facts':facts,'ancestry':boundary.identities,
                        'journal':journal_key,'relation':publication.get('relation'),'manifest':publication['parent']['manifest']})
            yield file,key

    def _enqueue(self,publication,key):
        with self._lock:
            if self._stop.is_set():return
            if key in self._pending:return
            if len(self._cache)>64:self._cache.clear()
            try:self._work.put_nowait((copy.deepcopy(publication),key))
            except queue.Full:return
            self._pending.add(key)
            if not self._thread or not self._thread.is_alive():
                self._thread=threading.Thread(target=self._verify,name='BooksArrangerPublicationVerification',daemon=False);self._thread.start()

    def _verify(self):
        import time
        while not self._stop.is_set():
            try:publication,key=self._work.get(timeout=.2)
            except queue.Empty:continue
            error='Current audiobook verification did not complete'
            try:
                started=time.monotonic()
                with self.protected(publication) as (file,current):
                    if current!=key:raise BoundaryError('Current publication changed before verification')
                    h=hashlib.sha256()
                    for block in file.chunks():
                        if self._stop.is_set():raise InterruptedError('Current audiobook verification stopped')
                        if self.pace is not None:self.pace(len(block),self._stop)
                        if time.monotonic()-started>600:raise TimeoutError('Current audiobook verification exceeded its bound')
                        h.update(block)
                    if h.hexdigest()!=publication['record']['sha256']:raise BoundaryError('Current audiobook bytes differ from its completed publication')
                    error=''
                    if self.remember is not None:self.remember(publication['record'])
            except Exception as failure:error=str(failure) or type(failure).__name__
            finally:
                with self._lock:self._pending.discard(key);self._cache[key]=error
                self._work.task_done()

    def describe(self,jobs,candidate):
        try:
            publication=self.publication(jobs,candidate)
            if publication is None:return {'state':'none','reason':'No verified audiobook created yet','identity':'none'}
            with self.protected(publication) as (_,key):
                with self._lock:known=key in self._cache;error=self._cache.get(key)
                if not known and self.verified is not None:
                    try:current=self.verified(publication['record']) is True
                    except (ValueError,OSError,KeyError):current=False
                    if current:
                        with self._lock:self._cache[key]='';known=True;error=''
                if not known:
                    self._enqueue(publication,key)
                    return {'state':'verifying','reason':'Verifying the recorded audiobook','identity':key}
                if error:return {'state':'unavailable','reason':error,'identity':key}
                record=publication['record']
                return {'state':'verified','path':record['final_path'],'identity':key,'publication_id':publication['id'],'kind':publication['kind'],
                        'record':copy.deepcopy(record),'cover':copy.deepcopy(publication['cover']),
                        'tags':copy.deepcopy(record['validation'].get('tags',{})),
                        'saved_tags':copy.deepcopy(publication.get('saved_tags',{})),
                        'tags_state':'saved_preserved' if publication['kind']=='chapter_update' else 'validated'}
        except (ValueError,OSError,KeyError,json.JSONDecodeError) as error:
            return {'state':'unavailable','reason':str(error),'identity':digest({'candidate':candidate,'failure':str(error)})}

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(30)
            if self._thread.is_alive():raise TimeoutError('Current audiobook verification has not reached its safe stop')
