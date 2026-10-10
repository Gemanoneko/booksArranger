from chapter_plan import prepare as prepare_chapters, names as chapter_names, available as chapters_available, default as chapters_default
"""Revision-bound candidate review. Source audio is opened read-only."""
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import threading
import uuid
from metadata import propose, future_audio_tags
from metadata_sources import MetadataClient, SourceUnavailable, manual_evidence
from native_io import DirectoryBoundary, ProtectedFiles, ordinary
from audio_pipeline import run_owned, INPUT_FORMATS
from scanner import connect, fresh_stat, inside

from encoding_policy import PROFILE, freeze_policy
TEXT_FIELDS=('title','author','canonical_author','original_language','series','number','genre','topic','narrator')
MAX_COVER=8*1024*1024
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def member_key(path): return str(uuid.uuid5(uuid.NAMESPACE_URL,os.path.normcase(os.path.abspath(path))))
def digest(path):
    result=hashlib.sha256()
    with open(path,'rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):result.update(block)
    return result.hexdigest()
def identity(stat): return (stat.st_size,stat.st_mtime_ns,stat.st_dev,stat.st_ino)
def source_hash(path,expected):
    result=hashlib.sha256()
    with open(path,'rb') as source:
        before=os.fstat(source.fileno())
        if identity(before)!=identity(expected):raise ValueError('Source changed — review required')
        for block in iter(lambda:source.read(1024*1024),b''):result.update(block)
        if identity(before)!=identity(os.fstat(source.fileno())):raise ValueError('Source changed — review required')
    if identity(before)!=identity(fresh_stat(path)):raise ValueError('Source changed — review required')
    return result.hexdigest()
def image_kind(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>=33:
        width,height=struct.unpack('>II',data[16:24])
        if width and height and width*height<=100000000 and b'IEND' in data[-16:]:return 'png'
    if data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9'):
        at=2
        while at+4<len(data):
            if data[at]!=255:break
            marker=data[at+1]; at+=2
            length=int.from_bytes(data[at:at+2],'big')
            if marker in (0xc0,0xc1,0xc2) and length>=7:
                height,width=struct.unpack('>HH',data[at+3:at+7])
                if width and height and width*height<=100000000:return 'jpg'
            if length<2:break
            at+=length
    raise ValueError('Cover must be a bounded usable JPEG or PNG')


class CandidateReviewService:
    def __init__(self,inventory,cache_dir,client=None,jobs=None):
        self.inventory=inventory; self.cache=ordinary(cache_dir)
        if any(inside(self.cache,root) for root in inventory.roots.values()):raise ValueError('Cover cache must be outside source libraries')
        with DirectoryBoundary(self.cache.anchor,self.cache,create=True) as boundary:
            self.cache_identity=boundary.identities
        self.client=client or MetadataClient(); self.jobs=jobs
        self._decoded=set()
        self.lock=threading.RLock(); self.matching={}; self.workers={}
        self.page_local=threading.local()
        with connect(inventory.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS candidate_context(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL)')

    def set_jobs(self,jobs):self.jobs=jobs

    def _row(self,library,id,revision=None):
        if library!='Audiobooks':raise ValueError('Only Audiobooks have candidate review')
        row=next((r for r in self.inventory.candidates(library,limit=1000000)['rows'] if r['id']==id),None)
        if row is None or (revision is not None and row['revision']!=revision):raise ValueError('Candidate changed; reload evidence before reviewing')
        return row

    def _context(self,row):
        cached=getattr(self.page_local,'contexts',None)
        if cached is not None:
            saved=cached.get(row['id'])
            return copy.deepcopy(saved['data']) if saved and saved['revision']==row['revision'] else {}
        with connect(self.inventory.database) as db:
            saved=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(row['id'],)).fetchone()
        return json.loads(saved['data']) if saved and saved['revision']==row['revision'] else {}

    def _write(self,row,ctx,bump=True):
        with self.inventory.group_lock,connect(self.inventory.database) as db:
            current=db.execute('SELECT revision FROM book_groups WHERE id=?',(row['id'],)).fetchone()
            if not current or current['revision']!=row['revision']:raise ValueError('Candidate changed; reload evidence before reviewing')
            revision=row['revision']+int(bump)
            if bump:db.execute('UPDATE book_groups SET revision=?,approved=0 WHERE id=?',(revision,row['id']))
            db.execute('INSERT OR REPLACE INTO candidate_context VALUES(?,?,?)',(row['id'],revision,json.dumps(ctx,ensure_ascii=False)))
        return self.enrich(self._row('Audiobooks',row['id']))

    def _keys(self,row):return [member_key(m['path']) for m in row['members']]

    def _cover(self,ctx):
        choice=next((c for c in ctx.get('cover_choices',[]) if c['id']==ctx.get('cover_id')),None)
        if choice:
            try:
                path=self.cover_file(choice['id'])
                if hashlib.sha256(self.cover_bytes(choice['id'])).hexdigest()!=choice['sha256']:return None
            except (ValueError,OSError):return None
        return choice

    def enrich(self,row,check_sources=True,allow_existing_job=False):
        row=copy.deepcopy(row); ctx=self._context(row); keys=self._keys(row)
        for m,key in zip(row['members'],keys):m['member_key']=key
        order=ctx.get('track_order',keys); included=ctx.get('included',keys)
        if set(order)!=set(keys) or not set(included)<=set(keys):order=keys;included=keys;ctx={}
        if check_sources:cover=self._cover(ctx)
        else:
            cover=next((c for c in ctx.get('cover_choices',[]) if c['id']==ctx.get('cover_id')),None)
            if cover and not any((self.cache/(cover['id']+suffix)).is_file() for suffix in ('.png','.jpg')):cover=None
        metadata_ok=bool(ctx.get('metadata_approved') and cover)
        track_ok=bool(ctx.get('source_coverage_confirmed') and ctx.get('order_confirmed') and ctx.get('source_hashes'))
        source_changed=False
        if track_ok and check_sources:
            try:
                for m in row['members']:
                    if m.get('intentionally_retired'):continue
                    key=member_key(m['path'])
                    if key not in included:continue
                    saved=ctx['source_hashes'][key];stat=fresh_stat(m['path'])
                    if identity(stat)!=(saved['size'],int(saved['modified']),saved['dev'],saved['ino']):track_ok=False;source_changed=True;break
            except (OSError,KeyError,ValueError):track_ok=False;source_changed=True
        reasons=[]
        if source_changed:reasons.append('Source changed — review required')
        if not metadata_ok:reasons.append('Approve canonical metadata with supporting evidence and choose a usable cover')
        if not track_ok:reasons.append('Review the exact source files and playback order')
        reasons.extend(row.get('conflicts',[]))
        if not included:reasons.append('Include at least one source audio file')
        prepare_chapters(row['members'])
        selected=[m for m in row['members'] if m['member_key'] in included]
        albums={str({k.casefold():v for k,v in m['metadata'].get('tags',{}).items()}.get('album') or '').strip().casefold() for m in selected}
        if len(row['members'])>1 and (len(albums)!=1 or not next(iter(albums),'').strip()):reasons.append('Establish one common book source context; loose files cannot establish recording membership')
        if any(m.get('error') or m.get('missing') for m in row['members']):reasons.append('Source files unavailable or unreadable')
        if len(selected)==1 and Path(selected[0]['path']).suffix.lower()=='.m4b':reasons.append('Single audiobook file')
        destination=row.get('preview',{}).get('path','')
        if not destination:reasons.append(row.get('preview',{}).get('reason') or 'Confirm output destination')
        elif check_sources and os.path.exists(destination):reasons.append('An audiobook already exists at this path. Review it or choose a different reviewed destination.')
        durations=[m.get('duration') for m in selected]
        duration=sum(durations) if durations and all(isinstance(d,(int,float)) for d in durations) else None
        job=None
        job_states=getattr(self.page_local,'jobs',None)
        if job_states is not None:job=job_states.get(row['id'])
        elif self.jobs and hasattr(self.jobs,'candidate_status'):
            job=self.jobs.candidate_status(row['id'])
        if job and not allow_existing_job:reasons.append('Audiobook job already exists; inspect its current status')
        if row.get('retired_source_count'):reasons.append('Original sources intentionally removed; use the created audiobook or guarded recovery')
        status='Ready to create' if not reasons else 'Single audiobook file' if 'Single audiobook file' in reasons else 'Source changed — review required' if row.get('changed') or source_changed else 'Needs metadata review' if not metadata_ok else 'Tracks need review'
        if job:status=job.get('state',status)
        row.update(metadata_approved=metadata_ok,matching=copy.deepcopy(self.matching.get(row['id'],ctx.get('matching',{'state':'idle','proposals':[],'error':''}))),
                   review_context={k:ctx.get(k,False if k in ('source_coverage_confirmed','order_confirmed','chapters') else '') for k in ('manual_note','proposal_id','cover_id','metadata_actor','metadata_utc','source_coverage_confirmed','order_confirmed','track_actor','track_utc','chapters')},
                   cover_choices=ctx.get('cover_choices',[]),selected_cover=cover,track_order=order,included=included,
                   creation={'status':status,'can_create':not reasons,'reasons':list(dict.fromkeys(reasons)),'destination':destination,'format':'M4B audiobook',
                             'duration_seconds':duration,'chapters_available':chapters_available(selected),'chapters_default':chapters_default(selected),
                             'chapters_description':('Chapter markers: '+str(len(selected))+' — one per included source track') if ctx.get('chapters',chapters_default(selected)) else 'Chapter markers: none',
                             'device':'Apple Books sync not checked','recording_completeness':'Recording completeness unknown','job':job})
        row['review_context']['chapters_choice_saved']='chapters' in ctx
        row['review_context']['metadata_evidence']=copy.deepcopy(ctx.get('metadata_evidence',[]))
        row['review_context']['track_evidence']=ctx.get('track_evidence','')
        policy={'enabled':bool(selected and all(Path(m['path']).suffix.lower()=='.mp3' for m in selected)),
                'recovery_root':str(self.jobs.cleanup.root) if self.jobs and hasattr(self.jobs,'cleanup') else ''}
        if job and not allow_existing_job:policy=job.get('cleanup_policy',{'enabled':False,'recovery_root':policy['recovery_root']})
        row['creation']['cleanup_policy']=policy
        row['cleanup']=job.get('cleanup') if job else None
        return row

    def page(self,limit=100,offset=0,search='',status='all'):
        if not isinstance(limit,int) or not 1<=limit<=1000 or not isinstance(offset,int) or offset<0:raise ValueError('Invalid page bounds')
        if status not in ('all','errors','changed','review','approved','ready','jobs','created','output_attention'):raise ValueError('Unknown candidate status')
        direct=status in ('all','errors','changed')
        result=self.inventory.candidates('Audiobooks',limit if direct else 1000000,offset if direct else 0,search,status if direct else 'all')
        with connect(self.inventory.database) as db:
            self.page_local.contexts={r['id']:{'revision':r['revision'],'data':json.loads(r['data'])} for r in db.execute('SELECT * FROM candidate_context')}
        self.page_local.jobs={}
        if self.jobs and hasattr(self.jobs,'jobs'):
            for job in self.jobs.jobs.status()['jobs']:
                state={'pending':'Queued','running':'Creating','completed':'Audiobook created','needs attention':'Output needs attention'}[job['state']]
                self.page_local.jobs[job['manifest']['candidate_id']]={'job_id':job['job_id'],'state':state,'stage':job['stage'],'reason':job['reason']}
                self.page_local.jobs[job['manifest']['candidate_id']]['cleanup_policy']=job['manifest'].get('cleanup_policy',{'enabled':False})
                if hasattr(self.jobs,'cleanup'):self.page_local.jobs[job['manifest']['candidate_id']]['cleanup']=self.jobs.cleanup.status(job['job_id'])
        def selected(row):
            saved=self.page_local.contexts.get(row['id']);ctx=saved['data'] if saved and saved['revision']==row['revision'] else {}
            choice=next((c for c in ctx.get('cover_choices',[]) if c['id']==ctx.get('cover_id')),None)
            approved=bool(ctx.get('metadata_approved') and choice and any((self.cache/(choice['id']+suffix)).is_file() for suffix in ('.png','.jpg')))
            job=self.page_local.jobs.get(row['id'])
            if status=='review':return not approved
            if status=='approved':return approved
            if status=='jobs':return bool(job and job['state'] in ('Queued','Creating'))
            if status=='created':return bool(job and job['state']=='Audiobook created')
            if status=='output_attention':return bool(job and job['state']=='Output needs attention')
            if status=='ready':
                included=ctx.get('included',[])
                if not approved or job or not ctx.get('source_coverage_confirmed') or not ctx.get('order_confirmed') or not ctx.get('source_hashes') or not included or row.get('conflicts') or not row.get('preview',{}).get('path'):return False
                members=[m for m in row['members'] if member_key(m['path']) in included]
                if len(members)==1 and Path(members[0]['path']).suffix.lower()=='.m4b':return False
                albums={str({k.casefold():v for k,v in m['metadata'].get('tags',{}).items()}.get('album') or '').strip().casefold() for m in members}
                return len(row['members'])==1 or len(albums)==1 and bool(next(iter(albums),''))
            raise ValueError('Unknown candidate status')
        try:
            if direct:chosen=result['rows'];total=result['total']
            else:
                chosen=[r for r in result['rows'] if selected(r)];total=len(chosen);chosen=chosen[offset:offset+limit]
            rows=[self.enrich(r,check_sources=False) for r in chosen]
        finally:
            del self.page_local.contexts;del self.page_local.jobs
        return {'rows':rows,'total':total}

    def _actor(self,actor,note):
        if actor not in ('user','assistant'):raise ValueError('Unknown reviewer actor')
        if not isinstance(note,str) or len(note)>16000:raise ValueError('Evidence note exceeds bound')
        if actor=='assistant' and len(note.strip())<20:raise ValueError('Assistant review requires concrete supporting evidence')

    def save(self,library,id,revision,review,approve=False,manual_note='',proposal_id=None,cover_id=None,actor='user',evidence=None):
        with self.lock:
            row=self._row(library,id,revision); ctx=self._context(row); self._actor(actor,manual_note)
            if not isinstance(review,dict) or len(json.dumps(review))>16000:raise ValueError('Invalid canonical metadata')
            review=copy.deepcopy(review)
            if set(review)-set(TEXT_FIELDS)-{'multi_author','anthology'}:raise ValueError('Unknown canonical metadata field')
            for field in TEXT_FIELDS:
                value=review.setdefault(field,'')
                if not isinstance(value,str) or len(value)>2000:raise ValueError('Canonical metadata fields must be bounded text')
            for field in ('multi_author','anthology'):
                if type(review.setdefault(field,False)) is not bool:raise ValueError('Canonical routing choices must be explicit booleans')
            records=[]
            if evidence is not None:
                if not isinstance(evidence,list) or len(evidence)>30:raise ValueError('Invalid per-field evidence')
                for record in evidence:
                    if not isinstance(record,dict):raise ValueError('Invalid evidence record')
                    records.append(manual_evidence(**{k:record[k] for k in ('field','cited_value','source_url','retrieved_utc','reviewer_actor','reviewer_identity','basis')}))
                if any(e['reviewer_actor']!=actor for e in records):raise ValueError('Evidence actor must match actual reviewer')
            if actor=='assistant' and approve:
                needed={'title','authors','original_language'}|({'series','number'} if review.get('series') else {'standalone'})
                if not needed<={r['field'] for r in records}:raise ValueError('Assistant approval requires per-field identity, author role, original language and series/standalone evidence')
                accepted={'title':review.get('title'),'authors':review.get('canonical_author'),'series':review.get('series'),'number':review.get('number'),'standalone':not bool(review.get('series'))}
                for field,value in accepted.items():
                    if field not in needed:continue
                    values=[r['cited_value'] for r in records if r['field']==field]
                    if not any(('; '.join(v) if isinstance(v,list) else str(v)).strip().casefold()==str(value).strip().casefold() for v in values):raise ValueError('Accepted metadata must match its cited evidence')
                langs=[str(r['cited_value']).strip().casefold() for r in records if r['field']=='original_language']
                if not langs or any(v in ('','unknown','other','unverified') for v in langs):raise ValueError('Establish the actual original-work language in evidence')
                russian=any(v in ('russian','ru','rus','русский') for v in langs)
                if russian!=(review.get('original_language')=='Russian'):raise ValueError('Original-work language contradicts cited evidence')
            if approve and (not manual_note.strip() or not (review.get('canonical_author') or '').strip()):raise ValueError('Confirm the author role and record metadata evidence')
            if cover_id is not None and not any(c['id']==cover_id for c in ctx.get('cover_choices',[])):raise ValueError('Choose a discovered local cover')
            trial=copy.deepcopy(ctx);trial['cover_id']=cover_id or ctx.get('cover_id')
            if approve and not self._cover(trial):raise ValueError('Choose a usable cover')
            preview=propose(row['members'][0]['path'],self.inventory.roots[library],'audiobook',row['metadata'],review)
            if approve and not preview['path']:raise ValueError(preview['reason'])
            if proposal_id is not None and not any(p['id']==proposal_id for p in self.matching.get(id,ctx.get('matching',{})).get('proposals',[])):raise ValueError('Unknown metadata proposal')
            changed=review!=row.get('review') or manual_note!=ctx.get('manual_note') or trial['cover_id']!=ctx.get('cover_id') or records!=ctx.get('metadata_evidence',[])
            fresh=self.inventory.save_candidate(library,id,revision,review,False)
            ctx.update(manual_note=manual_note,proposal_id=proposal_id,cover_id=trial['cover_id'],metadata_actor=actor,metadata_utc=utc(),metadata_evidence=records,metadata_approved=bool(approve))
            if changed:ctx.update(source_coverage_confirmed=False,order_confirmed=False,source_hashes={})
            return self._write(fresh,ctx)

    def match(self,library,id,revision):
        with self.lock:
            row=self._row(library,id,revision)
            if id in self.workers and self.workers[id].is_alive():return self.enrich(row)['matching']
            query=(row.get('review') or {}).get('title') or row['title_clue']
            author=(row.get('review') or {}).get('canonical_author') or ''
            self.matching[id]={'state':'finding','proposals':self._context(row).get('matching',{}).get('proposals',[]),'error':''}
            def lookup():
                try:
                    proposals=self.client.lookup(query,author)
                    for p in proposals:p['id']=str(uuid.uuid5(uuid.NAMESPACE_URL,p['public_url']))
                    result={'state':'found' if proposals else 'empty','proposals':proposals,'error':''}
                except SourceUnavailable as error:result={'state':'unavailable','proposals':self.matching[id]['proposals'],'error':str(error),'code':error.code}
                except Exception:result={'state':'unavailable','proposals':self.matching[id]['proposals'],'error':'Metadata source unavailable. Review cached evidence or enter verified metadata manually.'}
                with self.lock:
                    try:
                        current=self._row(library,id,revision);ctx=self._context(current);ctx['matching']=result
                        self._write(current,ctx,False);self.matching[id]=result
                    except ValueError:self.matching.pop(id,None)
            worker=threading.Thread(target=lookup,daemon=True);self.workers[id]=worker;worker.start()
            return copy.deepcopy(self.matching[id])

    def covers(self,library,id,revision):
        with self.lock:
            row=self._row(library,id,revision);ctx=self._context(row);choices=[]
            def add(data,label):
                if len(data)>MAX_COVER:raise ValueError('Cover exceeds8 MB')
                kind=image_kind(data);hash=hashlib.sha256(data).hexdigest();cover_id=str(uuid.uuid5(uuid.NAMESPACE_URL,id+hash))
                destination=self.cache/(cover_id+'.'+kind)
                with DirectoryBoundary(self.cache.anchor,self.cache) as boundary:
                    if boundary.identities!=self.cache_identity:raise ValueError('Cover cache identity changed')
                    if not destination.exists():
                        with open(destination,'xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
                    with ProtectedFiles([destination]):
                        if digest(destination)!=hash:raise ValueError('Cached artwork differs from selected source bytes')
                        decoder=shutil.which('ffmpeg')
                        if decoder and hash not in self._decoded:
                            run_owned([decoder,'-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1','-protocol_whitelist','file','-f','image2','-i',str(destination),'-frames:v','1','-f','null','-'],self.cache,threading.Event(),10,1024)
                            self._decoded.add(hash)
                if not any(c['id']==cover_id for c in choices):choices.append({'id':cover_id,'source_label':label,'source_url':'','evidence_kind':'Local artwork — edition unverified','thumbnail_url':'/api/cover?id='+cover_id,'sha256':hash})
            for companion in row.get('companions',[])[:50]:
                path=Path(companion['path'])
                if path.suffix.lower() not in ('.jpg','.jpeg','.png') or companion.get('error') or companion.get('missing'):continue
                try:
                    before=fresh_stat(path)
                    if before.st_size>MAX_COVER:continue
                    with open(path,'rb') as source:data=source.read(MAX_COVER+1)
                    if identity(before)!=identity(fresh_stat(path)):continue
                    add(data,path.name)
                except (OSError,ValueError,subprocess.TimeoutExpired):continue
            # Embedded artwork is extracted only when an attached picture is catalogued.
            ffmpeg=shutil.which('ffmpeg')
            if ffmpeg:
                with connect(self.inventory.database) as db:
                    for m in row['members'][:30]:
                        raw=db.execute('SELECT metadata FROM files WHERE root=? AND path=?',(self.inventory.roots[library],m['path'])).fetchone()
                        streams=json.loads(raw[0]).get('probe',{}).get('streams',[]) if raw else []
                        attached=next((s for s in streams if s.get('disposition',{}).get('attached_pic')==1),None)
                        if attached is None:continue
                        try:
                            before=fresh_stat(m['path'])
                            with DirectoryBoundary(self.cache.anchor,self.cache):
                                data=run_owned([ffmpeg,'-v','error','-nostdin','-threads','2','-filter_threads','1','-protocol_whitelist','file','-f',INPUT_FORMATS[Path(m['path']).suffix.lower()],'-i',m['path'],'-map','0:'+str(attached['index']),'-frames:v','1','-vf','scale=1200:1200:force_original_aspect_ratio=decrease','-f','image2pipe','-c:v','png','pipe:1'],self.cache,threading.Event(),15,MAX_COVER)
                            if identity(before)==identity(fresh_stat(m['path'])):add(data,'Embedded artwork: '+m['filename'])
                        except (OSError,ValueError,TimeoutError,subprocess.TimeoutExpired):pass
                        break
            changed=choices!=ctx.get('cover_choices',[])
            if changed:ctx['cover_choices']=choices
            if ctx.get('cover_id') and not any(c['id']==ctx['cover_id'] for c in choices):ctx.update(metadata_approved=False,source_hashes={})
            return self._write(row,ctx,bump=bool(changed and ctx.get('cover_id')))

    def cover_file(self,id):
        try:
            if str(uuid.UUID(id))!=id:raise ValueError()
        except (ValueError,TypeError,AttributeError):raise ValueError('Invalid cached cover identity') from None
        with DirectoryBoundary(self.cache.anchor,self.cache) as boundary:
            if boundary.identities!=self.cache_identity:raise ValueError('Cover cache identity changed')
            for suffix in ('.png','.jpg'):
                path=self.cache/(id+suffix)
                if path.is_file():
                    with ProtectedFiles([path]):
                        if path.stat().st_size>MAX_COVER:raise ValueError('Cached cover exceeds bound')
                        image_kind(path.read_bytes());return path
        raise ValueError('Cached cover unavailable')

    def cover_bytes(self,id):
        with DirectoryBoundary(self.cache.anchor,self.cache) as boundary:
            if boundary.identities!=self.cache_identity:raise ValueError('Cover cache identity changed')
            path=self.cover_file(id)
            with ProtectedFiles([path]):
                data=path.read_bytes()
                if len(data)>MAX_COVER:raise ValueError('Cached cover exceeds bound')
                image_kind(data);return data

    def source_cover(self,path,metadata):
        """Inspect one catalog source, never substitute another member's artwork."""
        path=ordinary(path);data=None
        before=fresh_stat(path)
        with ProtectedFiles([path]):
            if path.suffix.lower() in ('.png','.jpg','.jpeg'):
                if before.st_size>MAX_COVER:raise ValueError('Cover exceeds8 MB')
                data=path.read_bytes()
            elif path.suffix.lower() in ('.mp3','.m4a','.m4b','.flac','.ogg','.opus','.aac','.wav','.wma'):
                attached=next((s for s in metadata.get('probe',{}).get('streams',[]) if s.get('disposition',{}).get('attached_pic')==1),None)
                if attached:
                    ffmpeg=shutil.which('ffmpeg')
                    if not ffmpeg:raise ValueError('Installed ffmpeg is needed to inspect embedded artwork')
                    with DirectoryBoundary(self.cache.anchor,self.cache):
                        data=run_owned([ffmpeg,'-v','error','-nostdin','-threads','2','-filter_threads','1','-protocol_whitelist','file','-f',INPUT_FORMATS[path.suffix.lower()],'-i',str(path),'-map','0:'+str(attached['index']),'-frames:v','1','-vf','scale=1200:1200:force_original_aspect_ratio=decrease','-f','image2pipe','-c:v','png','pipe:1'],self.cache,threading.Event(),15,MAX_COVER)
            elif path.suffix.lower()=='.epub':
                import zipfile,posixpath
                from metadata import _xml,MAX_XML
                with zipfile.ZipFile(path) as book:
                    def read(name,bound):
                        entry=book.getinfo(name)
                        if entry.file_size>bound:raise ValueError('Embedded cover/package exceeds the inspection limit')
                        return book.read(entry)
                    container=_xml(read('META-INF/container.xml',MAX_XML))
                    package=next((n.attrib.get('full-path') for n in container.iter() if n.tag.split('}')[-1]=='rootfile'),None)
                    if package:
                        tree=_xml(read(package,MAX_XML));cover_id=next((n.attrib.get('content') for n in tree.iter() if n.attrib.get('name')=='cover'),None)
                        item=next((n for n in tree.iter() if n.tag.split('}')[-1]=='item' and ('cover-image' in n.attrib.get('properties','').split() or n.attrib.get('id')==cover_id)),None)
                        if item is not None:
                            href=item.attrib.get('href','')
                            if ':' in href or href.startswith('/'):raise ValueError('External cover references are not inspected')
                            data=read(posixpath.normpath(posixpath.join(posixpath.dirname(package),href)),MAX_COVER)
            elif path.suffix.lower()=='.fb2':
                import base64
                from metadata import _xml,MAX_XML
                if before.st_size>MAX_XML:raise ValueError('FB2 is too large for bounded cover inspection')
                tree=_xml(path.read_bytes());coverpage=next((n for n in tree.iter() if n.tag.split('}')[-1]=='coverpage'),None)
                if coverpage is not None:
                    image=next((n for n in coverpage.iter() if n.tag.split('}')[-1]=='image'),None)
                    reference=next((v for k,v in image.attrib.items() if k.split('}')[-1]=='href'),None) if image is not None else None
                    binary=next((n for n in tree.iter() if n.tag.split('}')[-1]=='binary' and '#'+n.attrib.get('id','')==reference),None)
                    if binary is not None:data=base64.b64decode(''.join((binary.text or '').split()),validate=True)
        if identity(before)!=identity(fresh_stat(path)):raise ValueError('Source changed during cover inspection')
        if data is None:return {'status':'No embedded cover' if path.suffix.lower() in ('.mp3','.m4a','.m4b','.epub','.fb2','.flac','.ogg','.opus','.aac','.wav','.wma') else 'Cover inspection unsupported for this format','label':'Source cover'}
        if len(data)>MAX_COVER:raise ValueError('Cover exceeds8 MB')
        kind=image_kind(data);hash=hashlib.sha256(data).hexdigest();id=str(uuid.uuid5(uuid.NAMESPACE_URL,str(path)+hash))
        cached=self.cache/(id+'.'+kind)
        with DirectoryBoundary(self.cache.anchor,self.cache) as boundary:
            if boundary.identities!=self.cache_identity:raise ValueError('Cover cache identity changed')
            if not cached.exists():
                with open(cached,'xb') as out:out.write(data);out.flush();os.fsync(out.fileno())
            with ProtectedFiles([cached]):
                if digest(cached)!=hash:raise ValueError('Cached source cover bytes changed')
        return {'id':id,'thumbnail_url':'/api/cover?id='+id,'label':'Embedded/source cover — edition unverified','status':'Source cover','sha256':hash}

    def tracks(self,library,id,revision,order,included,source_coverage_confirmed,order_confirmed,chapters,actor='user',evidence_note=''):
        with self.lock:
            row=self._row(library,id,revision);ctx=self._context(row);keys=self._keys(row);self._actor(actor,evidence_note)
            if not isinstance(order,list) or len(order)!=len(keys) or set(order)!=set(keys) or not isinstance(included,list) or len(set(included))!=len(included) or not set(included)<=set(keys):raise ValueError('Review the exact known member list and order')
            if any(type(v)is not bool for v in (source_coverage_confirmed,order_confirmed,chapters)):raise ValueError('Track confirmations must be explicit booleans')
            if (source_coverage_confirmed or order_confirmed) and not evidence_note.strip():raise ValueError('Record the membership and order review basis')
            titles=[m.get('track_title') for m in row['members'] if member_key(m['path']) in included]
            if chapters and not chapters_available([m for m in row['members'] if member_key(m['path']) in included]):raise ValueError('Chapter boundaries unavailable: source durations need checking')
            hashes={}
            if source_coverage_confirmed and order_confirmed:
                for m in row['members']:
                    key=member_key(m['path'])
                    if key not in included:continue
                    before=fresh_stat(m['path'])
                    if before.st_size!=m['size'] or before.st_mtime_ns!=int(m['modified']):raise ValueError('Source changed — review required')
                    hash=source_hash(m['path'],before);after=fresh_stat(m['path'])
                    if identity(before)!=identity(after):raise ValueError('Source changed — review required')
                    hashes[key]={'sha256':hash,'size':before.st_size,'modified':str(before.st_mtime_ns),'dev':before.st_dev,'ino':before.st_ino}
            ctx.update(track_order=order,included=included,source_coverage_confirmed=source_coverage_confirmed,order_confirmed=order_confirmed,chapters=chapters,track_actor=actor,track_utc=utc(),track_evidence=evidence_note,source_hashes=hashes)
            return self._write(row,ctx)

    def build_manifest(self,library,id,revision,allow_existing_job=False):
        with self.lock:
            row=self.enrich(self._row(library,id,revision),allow_existing_job=allow_existing_job);ctx=self._context(row)
            if not row['creation']['can_create']:raise ValueError('; '.join(row['creation']['reasons']))
            members={m['member_key']:m for m in row['members']};sources=[]
            for key in row['track_order']:
                if key not in row['included']:continue
                m=members[key];stored=ctx['source_hashes'][key];stat=fresh_stat(m['path'])
                if identity(stat)!=(stored['size'],int(stored['modified']),stored['dev'],stored['ino']) or source_hash(m['path'],stat)!=stored['sha256']:raise ValueError('Source changed — review required')
                sources.append({'path':m['path'],'size':stored['size'],'modified':stored['modified'],'sha256':stored['sha256'],'fingerprint':{'size':stored['size'],'modified':stored['modified']},'metadata':m['metadata']})
            cover=row['selected_cover'];cover=cover|{'path':str(self.cover_file(cover['id']))}
            comments=future_audio_tags(row['metadata'],row['review'])['COMMENTS']
            return {'job_id':str(uuid.uuid4()),'candidate_id':id,'candidate_revision':revision,'sources':sources,'metadata':copy.deepcopy(row['review']),
                    'root':self.inventory.roots[library],'destination':row['creation']['destination'],'profile':PROFILE,'encoding_policy':freeze_policy(sources),'cover':cover,'comments':comments,
                    'cleanup_policy':row['creation']['cleanup_policy'],
                    'evidence':{'metadata_actor':ctx['metadata_actor'],'metadata_utc':ctx['metadata_utc'],'manual_note':ctx['manual_note'],'metadata_fields':ctx.get('metadata_evidence',[]),'track_actor':ctx['track_actor'],'track_utc':ctx['track_utc'],'track_basis':ctx['track_evidence'],'recording_completeness':'unknown'},
                    'chapters':chapter_names([members[key] for key in row['track_order'] if key in row['included']]) if ctx.get('chapters') else []}
