from chapter_plan import prepare as prepare_chapters, names as chapter_names, available as chapters_available, default as chapters_default
"""Revision-bound candidate review. Source audio is opened read-only."""
import contextlib
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import subprocess
import threading
import uuid
import manual_metadata
from metadata import propose, future_audio_tags
from metadata_sources import MetadataClient, SourceUnavailable, manual_evidence, local_evidence
from native_io import DirectoryBoundary, ProtectedFiles, ordinary
from audio_pipeline import run_owned, INPUT_FORMATS
from scanner import connect, fresh_stat, inside

from encoding_policy import PROFILE, freeze_policy, AUTOMATIC_PROFILE, freeze_automatic_policy
TEXT_FIELDS=('title','author','canonical_author','original_language','series','number','genre','topic','narrator','universe')
MAX_COVER=8*1024*1024


def job_destination(manifest):
    """A job's own destination, for its Stopped row's "Goes to" line (Judy's to-do spec 1.6 and section 4: every row,
    Stopped rows included; Futaba's m-3): {'path' relative to the output folder, 'absolute'}, or None when the manifest
    names none inside its output folder (an older manifest)."""
    destination,root=manifest.get('destination'),manifest.get('output_root')
    if not isinstance(destination,str) or not destination or not isinstance(root,str) or not root or not inside(destination,root):return None
    return {'path':os.path.relpath(destination,root),'absolute':destination}
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def member_key(path): return str(uuid.uuid5(uuid.NAMESPACE_URL,os.path.normcase(os.path.abspath(path))))
def digest(path):
    result=hashlib.sha256()
    with open(path,'rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):result.update(block)
    return result.hexdigest()
def identity(stat): return (stat.st_size,stat.st_mtime_ns,stat.st_dev,stat.st_ino)
# Across time, only size and modification time screen a reviewed source; its content hash decides. Windows file
# IDs are not stable on the library's SMB share (the same cause as the 0.16.8 Zone.Identifier fix), so a source
# whose recorded file ID shifted but whose bytes match is unchanged. Same-moment checks still use identity().
def unchanged_screen(stat,saved):return (stat.st_size,stat.st_mtime_ns)==(saved['size'],int(saved['modified']))
def source_hash(path,expected,stop=None):
    if stop and stop.is_set():raise InterruptedError('Automatic source hashing paused')
    result=hashlib.sha256()
    with open(path,'rb') as source:
        before=os.fstat(source.fileno())
        if identity(before)!=identity(expected):raise ValueError('Source changed — review required')
        for block in iter(lambda:source.read(1024*1024),b''):
            if stop and stop.is_set():raise InterruptedError('Automatic source hashing paused')
            result.update(block)
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


# The Output needs attention groups (the chips), the one list every route and count reads. Futaba's 0.22.0 QA blocker:
# web_server checked `group` against its own older set, so every new chip (and Reacquire) answered 400 "Unknown attention
# group" while page() accepted it. NEEDS_GROUPS are the books only Sergei can move on (MergeService.needs_you), in their
# list order (Judy 2026-10-24, B3); JOB_GROUPS the stopped jobs (AudioJobs.attention_summary), with their order.
NEEDS_GROUPS=('files_missing','title_author','author_unclear','same_author','name_taken','part_of_book','files_unclear','order_unclear')
JOB_ORDER={'retry':0,'repair':1,'reacquire':1.5,'checking':2,'changed':3,'audiobook':4,'other':5,'unsupported':6}
JOB_GROUPS=tuple(JOB_ORDER)
ATTENTION_GROUPS=frozenset(('all',)+NEEDS_GROUPS+JOB_GROUPS)


class CandidateReviewService:
    def __init__(self,inventory,cache_dir,client=None,jobs=None):
        self.inventory=inventory; self.cache=ordinary(cache_dir)
        if any(inside(self.cache,root) for root in (inventory.all_source_roots() if hasattr(inventory,'all_source_roots') else inventory.roots.values())):raise ValueError('Cover cache must be outside source libraries')
        with DirectoryBoundary(self.cache.anchor,self.cache,create=True) as boundary:
            self.cache_identity=boundary.identities
        self.client=client or MetadataClient(); self.jobs=jobs
        self._decoded=set()
        self.lock=threading.RLock(); self.matching={}; self.workers={}
        self.page_local=threading.local()
        with connect(inventory.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS candidate_context(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL)')
            manual_metadata.initialize(db)
            # Preserve existing user drafts before any release/start-over can clear canonical context.
            prior_drafts=db.execute('SELECT g.id,g.fingerprint,g.review,g.revision,c.revision AS context_revision,c.data FROM book_groups g JOIN candidate_context c ON c.id=g.id') if db.execute("SELECT 1 FROM sqlite_master WHERE name='book_groups' AND type='table'").fetchone() else []
            for saved in prior_drafts:
                context=json.loads(saved['data'])
                if context.get('metadata_actor')=='user' and saved['review']:
                    prior=db.execute('SELECT 1 FROM manual_metadata_sources WHERE candidate_id=? LIMIT 1',(saved['id'],)).fetchone()
                    if not prior:
                        binding=dict(saved)
                        if saved['revision']!=saved['context_revision']:binding['fingerprint']='legacy-unbound:'+str(saved['context_revision'])
                        manual_metadata.append(db,manual_metadata.capture(binding,json.loads(saved['review']),context.get('manual_note','')))

    def set_jobs(self,jobs):self.jobs=jobs

    @contextlib.contextmanager
    def without_ready(self):
        """No converted-books read on this thread for one operation (Senua 0.21.2 F31).

        enrich() marks audiobook_ready from progress_books(): every job, cleanup and publication record plus one
        library stat per converted book, 10-25 s on the live catalog (2026-10-24), under group_lock, which the status
        poll and the book list wait on. An automatic approval decides nothing from that flag (creation, the context and
        the files decide), so inside this scope enrich() leaves it unset. Nested scopes keep the outer setting."""
        previous=getattr(self.page_local,'ready_skip',False);self.page_local.ready_skip=True
        try:yield
        finally:self.page_local.ready_skip=previous

    def _row(self,library,id,revision=None):
        if library!='Audiobooks':raise ValueError('Only Audiobooks have candidate review')
        with connect(self.inventory.database) as db:
            import reacquire_sources
            marker=reacquire_sources.marker(db,id)
            if marker and marker['state']=='archived':raise ValueError('Damaged-source entry archived; use the newly discovered replacement')
        row=self.inventory.candidate(library,id) if hasattr(self.inventory,'candidate') else next((r for r in self.inventory.candidates(library,limit=1000000)['rows'] if r['id']==id),None)
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

    def _write(self,row,ctx,bump=True,manual_source=None,decision_record=None):
        with self.inventory.group_lock,connect(self.inventory.database) as db:
            import reacquire_sources
            marker=reacquire_sources.marker(db,row['id'])
            if marker and marker['state']=='archived':raise ValueError('Damaged-source entry archived; use the newly discovered replacement')
            current=db.execute('SELECT revision FROM book_groups WHERE id=?',(row['id'],)).fetchone()
            if not current or current['revision']!=row['revision']:raise ValueError('Candidate changed; reload evidence before reviewing')
            revision=row['revision']+int(bump)
            if bump:db.execute('UPDATE book_groups SET revision=?,approved=0 WHERE id=?',(revision,row['id']))
            db.execute('INSERT OR REPLACE INTO candidate_context VALUES(?,?,?)',(row['id'],revision,json.dumps(ctx,ensure_ascii=False)))
            manual_metadata.append(db,manual_source)
            if decision_record is not None:
                import metadata_choices
                metadata_choices.append(db,decision_record,applied_revision=revision)
        return self.enrich(self._row('Audiobooks',row['id']))

    def _source_root(self,row,library='Audiobooks'):
        if row.get('source_root'):return row['source_root']
        if hasattr(self.inventory,'source_root_for_candidate'):return self.inventory.source_root_for_candidate(row['id'])
        return self.inventory.roots[library]

    def _output_root(self,row,review=None,library='Audiobooks'):
        review=review if review is not None else row.get('review') or {}
        configured=getattr(self.inventory,'output_root',None)
        return configured if configured and review.get('organization_policy')=='books-hierarchy-v2' else self._source_root(row,library)

    def _keys(self,row):return [member_key(m['path']) for m in row['members']]

    def _cover(self,ctx):
        choice=next((c for c in ctx.get('cover_choices',[]) if c['id']==ctx.get('cover_id')),None)
        if choice:
            try:
                path=self.cover_file(choice['id'])
                if hashlib.sha256(self.cover_bytes(choice['id'])).hexdigest()!=choice['sha256']:return None
            except (ValueError,OSError):return None
        return choice

    def enrich(self,row,check_sources=True,allow_existing_job=False,allow_automatic_pending=False,held=None,ready=True):
        """ready=False (build_manifest, and every enrich inside without_ready()) skips the converted-books read and
        leaves audiobook_ready unset; nothing that builds or guards a job reads it."""
        row=copy.deepcopy(row); ctx=self._context(row); keys=self._keys(row); held=held or {}
        from groups import shown_grouping
        row['grouping']=shown_grouping(row.get('grouping'))  # no names or rule numbers in the panel, whichever build stored it
        with connect(self.inventory.database) as db:row['manual_metadata_sources']=manual_metadata.records(db,row)
        facts=ctx.get('metadata_facts')
        if facts:
            from standing_metadata import validate_policy
            validate_policy(row,row.get('review',{}),facts)
            row['preview']=propose(row['members'][0]['path'],self._output_root(row),'audiobook',row['metadata'],row['review'],automatic_facts=facts)
        if (row.get('review') or {}).get('organization_policy')=='books-hierarchy-v2':row['preview']=propose(row['members'][0]['path'],self._output_root(row),'audiobook',row['metadata'],row['review'],automatic_facts=facts)
        row['metadata_facts']=copy.deepcopy(facts)
        row['duplicate_review']=copy.deepcopy(ctx.get('duplicate_review'))
        for m,key in zip(row['members'],keys):m['member_key']=key
        order=ctx.get('track_order',keys); included=ctx.get('included',keys)
        if set(order)!=set(keys) or not set(included)<=set(keys):order=keys;included=keys;ctx={}
        if check_sources:cover=self._cover(ctx)
        else:
            cover=next((c for c in ctx.get('cover_choices',[]) if c['id']==ctx.get('cover_id')),None)
            if cover and not any((self.cache/(cover['id']+suffix)).is_file() for suffix in ('.png','.jpg')):cover=None
        metadata_ok=bool(ctx.get('metadata_approved') and cover and (not ctx.get('automatic_pending') or allow_automatic_pending))
        track_ok=bool(ctx.get('source_coverage_confirmed') and ctx.get('order_confirmed') and ctx.get('source_hashes'))
        source_changed=False
        if track_ok and check_sources:
            try:
                for m in row['members']:
                    if m.get('intentionally_retired'):continue
                    key=member_key(m['path'])
                    if key not in included:continue
                    if os.path.normcase(os.path.abspath(m['path'])) in held:continue  # proven by its in-place publication
                    saved=ctx['source_hashes'][key];stat=fresh_stat(m['path'])
                    if not unchanged_screen(stat,saved):track_ok=False;source_changed=True;break
            except (OSError,KeyError,ValueError):track_ok=False;source_changed=True
        reasons=[]
        if source_changed:reasons.append('Source changed — review required')
        if not metadata_ok:reasons.append('Approve canonical metadata with supporting evidence and choose a usable cover')
        if not track_ok:reasons.append('Review the exact source files and playback order')
        # Ruling 6b: Sergei's Approve overrides the grouping's confidence holds (mixed clues, grouping evidence); the
        # unavailable-file check on the files being converted stays below.
        reasons.extend([] if ctx.get('user_approval') else row.get('conflicts',[]))
        if not included:reasons.append('Include at least one source audio file')
        prepare_chapters(row['members'])
        selected=[m for m in row['members'] if m['member_key'] in included]
        albums={str({k.casefold():v for k,v in m['metadata'].get('tags',{}).items()}.get('album') or '').strip().casefold() for m in selected}
        if len(row['members'])>1 and (len(albums)!=1 or not next(iter(albums),'').strip()) and not facts:reasons.append('Establish one common book source context; loose files cannot establish recording membership')
        # Only the files being converted: Convert what's there (ruling 10) leaves the missing ones out of the tracks.
        if any(m.get('error') or m.get('missing') for m in selected):reasons.append('Source files unavailable or unreadable')
        if len(selected)==1 and Path(selected[0]['path']).suffix.lower()=='.m4b' and not facts and not manual_metadata.approved(row,ctx):reasons.append('Single audiobook file')
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
        if row.get('retired_source_count'):reasons.append('Original sources intentionally removed; use the created audiobook')
        status='Ready to create' if not reasons else 'Single audiobook file' if 'Single audiobook file' in reasons else 'Source changed — review required' if row.get('changed') or source_changed else 'Needs metadata review' if not metadata_ok else 'Tracks need review'
        if job:status=job.get('state',status)
        row.update(metadata_approved=metadata_ok,matching=copy.deepcopy(self.matching.get(row['id'],ctx.get('matching',{'state':'idle','proposals':[],'error':''}))),
                   review_context={k:ctx.get(k,False if k in ('source_coverage_confirmed','order_confirmed','chapters') else '') for k in ('manual_note','proposal_id','cover_id','metadata_actor','metadata_utc','source_coverage_confirmed','order_confirmed','track_actor','track_utc','chapters')},
                   cover_choices=ctx.get('cover_choices',[]),selected_cover=cover,track_order=order,included=included,
                   creation={'status':status,'can_create':not reasons,'reasons':list(dict.fromkeys(reasons)),'destination':destination,'format':'M4B audiobook',
                             'duration_seconds':duration,'chapters_available':chapters_available(selected),'chapters_default':chapters_default(selected),
                             'chapters_description':('Chapter markers: '+str(len(selected))+' — one per included source track') if ctx.get('chapters',chapters_default(selected)) else 'Chapter markers: none',
                             'device':'Apple Books sync not checked','recording_completeness':'Recording completeness unknown','job':job})
        automatic=self.jobs.automatic.candidate(row) if self.jobs and hasattr(self.jobs,'automatic') else None
        row['automatic']=automatic
        row['metadata_holds']=manual_metadata.holds(automatic)
        if automatic:
            if not facts:row['metadata_facts']=copy.deepcopy(automatic.get('metadata_facts'))
            if not row['duplicate_review']:row['duplicate_review']=copy.deepcopy(automatic.get('duplicate_review'))
        if ready and not getattr(self.page_local,'ready_skip',False):
            ready_ids=getattr(self.page_local,'ready_ids',None)  # a page computes its set once (page())
            if ready_ids is None:ready_ids=self.jobs.progress_books()['converted_ids'] if self.jobs and hasattr(self.jobs,'progress_books') else set()
            row['audiobook_ready']=row['id'] in ready_ids
        audiobooks=getattr(self.page_local,'audiobooks',None)
        if audiobooks is not None and row['id'] in audiobooks:row['current_audiobook']=audiobooks[row['id']]
        elif self.jobs and hasattr(self.jobs,'current_audiobook'):row['current_audiobook']=self.jobs.current_audiobook(row['id'])
        row['review_context']['automatic_approval']=copy.deepcopy(ctx.get('automatic_approval'))
        if automatic and not job and automatic['state'] in ('Researching','Waiting for source','Held','Needs attention','Approved automatically','Queued'):
            row['status']=automatic['state']+(' — '+automatic['reasons'][0].lower() if automatic['state']=='Needs attention' and automatic['reasons'] else ' — '+automatic['reasons'][0] if automatic['state']=='Held' and automatic['reasons'] else '')
        row['review_context']['chapters_choice_saved']='chapters' in ctx
        row['review_context']['metadata_evidence']=copy.deepcopy(ctx.get('metadata_evidence',[]))
        row['review_context']['track_evidence']=ctx.get('track_evidence','')
        policy={'enabled':bool(selected and (facts or all(Path(m['path']).suffix.lower()=='.mp3' for m in selected))),
                'recovery_retention_hours':24,
                'empty_source_folders':bool(selected and (facts or all(Path(m['path']).suffix.lower()=='.mp3' for m in selected))),
                'recovery_root':str(self.jobs.cleanup.root) if self.jobs and hasattr(self.jobs,'cleanup') else ''}
        if job and not allow_existing_job:policy=job.get('cleanup_policy',{'enabled':False,'recovery_root':policy['recovery_root']})
        row['creation']['cleanup_policy']=policy
        row['cleanup']=job.get('cleanup') if job else None
        row['metadata_questions']=self.metadata_questions(row,ctx)
        if self.jobs and hasattr(self.jobs,'producer_retention'):row['producer_recovery_retained']=self.jobs.producer_retention(row['id'])
        return row

    def metadata_questions(self,row,ctx):
        """Compare current evidence without treating a decision as new evidence."""
        import metadata_choices
        matching=self.matching.get(row['id'],row.get('matching') or ctx.get('matching') or {})
        automatic=row.get('automatic')
        if automatic is None and self.jobs and hasattr(self.jobs,'automatic'):automatic=self.jobs.automatic.candidate(row)
        conflicts=list(matching.get('conflicts') or [])+list((automatic or {}).get('manual_metadata_conflicts') or [])
        with connect(self.inventory.database) as db:
            entered=manual_metadata.records(db,row)
            return metadata_choices.present(db,row,matching.get('proposals') or [],entered,conflicts)

    def choose_metadata(self,library,id,revision,signature,choices,manual_note=''):
        """Save an explicit evidence-scoped draft choice; never approve or queue."""
        import metadata_choices
        with self.lock:
            try:row=self._row(library,id,revision)
            except ValueError:raise metadata_choices.ChoiceChanged() from None
            ctx=self._context(row);snapshot=self.metadata_questions(row,ctx)
            prepared=metadata_choices.prepare(row,snapshot,signature,choices,actor='user',note=manual_note)
            if prepared['record']['choices'] and all(choice['mode']=='unresolved' for choice in prepared['record']['choices']):
                held=copy.deepcopy(ctx);held['metadata_approved']=False
                saved=self._write(row,held,decision_record=prepared['record'])
                questions=saved.get('metadata_questions') or self.metadata_questions(saved,self._context(saved))
                return {'row':saved,'unresolved_count':questions['unresolved_count'],'decision':prepared['record']}
            review=copy.deepcopy(row.get('review') or {})
            patch=prepared['patch']
            if 'original_language' in patch:
                language=patch['original_language'].strip().casefold()
                patch['original_language']='Unknown' if language in {'','unknown','und','unverified'} else 'Russian' if language in {'ru','rus','russian','русский'} else 'Other'
            review.update(patch)
            saved=self.save(library,id,revision,review,approve=False,manual_note=manual_note or ctx.get('manual_note',''),
                proposal_id=ctx.get('proposal_id') or None,cover_id=ctx.get('cover_id') or None,actor='user',
                capture_manual=bool(prepared['corrected_values']),manual_source_values=prepared['corrected_values'],decision_record=prepared['record'])
            questions=saved.get('metadata_questions') or self.metadata_questions(saved,self._context(saved))
            return {'row':saved,'unresolved_count':questions['unresolved_count'],'decision':prepared['record']}

    # Judy 2026-10-24, section 1: the "Needs your answer" set first (missing files first: deleted files can be recovered
    # only while the recycle bin keeps them), then the Stopped set in its existing order.
    # 0.22.0 review (Judy 2026-10-24, B3): the three hold chips follow Name taken in the same set.
    ATTENTION_ORDER={**{group:n-len(NEEDS_GROUPS) for n,group in enumerate(NEEDS_GROUPS)},**JOB_ORDER}  # files_missing -8 ... order_unclear -1

    def _names_lines(self,rows):
        """Edit names (Judy 0.22.2 sections 2 and 9), the shown page only: each row's 'place' {universe, series, number,
        collection} and 'entered' [field...], from stored values alone (the book's saved review and Sergei's saved names;
        no research per row). An unreadable store leaves the lines out."""
        import entered_names
        try:
            stored=entered_names._rows(self.inventory.database)
            for row in rows:
                saved=entered_names.book_values(self.inventory.database,row,stored)
                review=row.get('review') if isinstance(row.get('review'),dict) and row.get('review') else {}
                facts=((row.get('automatic') or {}).get('metadata_facts') or row.get('metadata_facts') or {}) if not review else {}
                # A book not approved yet: its research record's facts (a collection the research filed as one).
                place={'universe':str(review.get('universe') or ''),'series':str(review.get('series') or ''),'number':str(review.get('number') or ''),
                       'collection':review.get('anthology') is True or isinstance(facts,dict) and bool((facts.get('collection') or {}).get('kind'))}
                for field in ('universe','series','number','collection'):
                    if field in saved:place[field]=saved[field] if field=='collection' else str(saved[field])
                if not (place['series'] and place['number']):place['series']=place['number']=''
                row['place']=place
                row['entered']=entered_names.entered(saved)
        except (sqlite3.Error,OSError,KeyError,TypeError):
            for row in rows:row.pop('place',None);row.pop('entered',None)

    def page(self,limit=100,offset=0,search='',status='all',group=None):
        """One page of the book list; replacement relations are read once for the page, not once per lookup."""
        snapshot=getattr(getattr(self.jobs,'replacements',None),'snapshot',None) if self.jobs else None
        if snapshot is None:return self._page(limit,offset,search,status,group)
        with snapshot():return self._page(limit,offset,search,status,group)

    def _page(self,limit=100,offset=0,search='',status='all',group=None):
        """One page of the book list.

        Speed (v0.16.7): job, ready, held and attention filters are decided per candidate id first, so
        only matching groups are rendered; per-book extras (cleanup, Retry data, current audiobook)
        are computed for the shown page only, from one jobs list; the converted set comes from the
        last status computation when fresh. group (Output needs attention only): one of ATTENTION_GROUPS; that
        list is ordered by ATTENTION_ORDER, then by scope.
        A job made by Repair carries 'repaired' (audio_jobs.repair_record) in every state.
        """
        if not isinstance(limit,int) or not 1<=limit<=1000 or not isinstance(offset,int) or offset<0:raise ValueError('Invalid page bounds')
        if status not in ('all','errors','changed','review','approved','ready','jobs','created','converted','output_attention','held','recording_review','restarted'):raise ValueError('Unknown candidate status')
        if group is not None and group not in ATTENTION_GROUPS or group not in (None,'all') and status!='output_attention':raise ValueError('Unknown attention group')
        direct=status in ('all','errors','changed')
        with connect(self.inventory.database) as db:
            self.page_local.contexts={r['id']:{'revision':r['revision'],'data':json.loads(r['data'])} for r in db.execute('SELECT * FROM candidate_context')}
        self.page_local.jobs={};job_rows=None;attention={}
        if self.jobs and hasattr(self.jobs,'jobs'):
            job_rows=self.jobs.jobs.status()['jobs']
            for job in job_rows:
                state={'pending':'Queued','running':'Creating','completed':'Audiobook created','needs attention':'Output needs attention'}[job['state']]
                self.page_local.jobs[job['manifest']['candidate_id']]={'job_id':job['job_id'],'state':state,'stage':job['stage'],'reason':job['reason'],
                    'cleanup_policy':job['manifest'].get('cleanup_policy',{'enabled':False}),'destination':job_destination(job['manifest'])}
                if isinstance(job['manifest'].get('retry_intent'),dict):self.page_local.jobs[job['manifest']['candidate_id']]['retry_parent_job_id']=job['manifest']['retry_intent'].get('parent_job_id')
                if job['manifest'].get('m4b_repair'):
                    from audio_jobs import repair_record;repaired=repair_record(job)
                    if repaired:self.page_local.jobs[job['manifest']['candidate_id']]['repaired']=repaired
            if status=='output_attention' and hasattr(self.jobs,'attention_summary'):attention=self.jobs.attention_summary(retry=False)
        converted=(self.jobs.converted_ids() if hasattr(self.jobs,'converted_ids') else self.jobs.progress_books()['converted_ids']) if self.jobs and hasattr(self.jobs,'progress_books') else set()
        needs={}
        if status=='output_attention' and self.jobs and hasattr(self.jobs,'needs_you'):
            # The one predicate (Judy 2026-10-24, section 1): stale job rows out, the books only Sergei can move on in.
            if hasattr(self.jobs,'stale_attention') and job_rows is not None:attention=self.jobs.stale_attention(attention,job_rows,set(converted))
            needs=self.jobs.needs_you()
        self.page_local.ready_ids=converted
        automatic=self.jobs.automatic.index() if self.jobs and hasattr(self.jobs,'automatic') and hasattr(self.jobs.automatic,'index') and status in ('held','recording_review','restarted') else None
        # Started over (RefusedRetry follow-up 3, section 2.3): books Start over or release sent back to automatic
        # processing that it has not queued yet, ordered failed, waiting, working, held; global counts for the summary.
        restart,restart_counts=self.jobs.restart_index(self.page_local.jobs,automatic) if status=='restarted' and self.jobs and hasattr(self.jobs,'restart_index') else ({},None)
        def approved_context(cid):
            saved=self.page_local.contexts.get(cid);ctx=saved['data'] if saved else {}
            return bool(not ctx.get('automatic_pending') and ctx.get('metadata_approved'))
        def held_or_waiting(item):
            # Judy 0.22.2 section 4: "Waiting for the original title" (ruling 29) is an automatic wait, not a to-do; it is
            # listed under Held, beside the books held until they change.
            import original_titles
            return item['state']=='Held' or item['state']=='Waiting for source' and original_titles.WAIT_REASON in (item.get('reasons') or [])
        def group_of(cid):
            job=self.page_local.jobs.get(cid)
            if job:return (attention.get(job['job_id']) or {}).get('group','other')
            return needs[cid]['group'] if cid in needs else None
        filtered=status=='output_attention' and hasattr(self.jobs,'stale_attention') and job_rows is not None
        def attention_listed(cid):
            """Listed in Output needs attention: a job row the stale rule keeps (the summary holds every needs-attention
            job, newest per book), or a book only Sergei can move on."""
            job=self.page_local.jobs.get(cid)
            if job:return job['job_id'] in attention if filtered else job['state']=='Output needs attention' or job['job_id'] in attention
            return cid in needs
        ids=None
        if not direct and not search:
            # Cheap per-id prefilter; selected() below still decides every rendered row exactly.
            jobs=self.page_local.jobs
            if status=='jobs':ids={cid for cid,job in jobs.items() if job['state'] in ('Queued','Creating')}
            elif status=='created':ids={cid for cid,job in jobs.items() if job['state']=='Audiobook created'}
            elif status=='output_attention':ids={cid for cid in set(jobs)|set(needs) if attention_listed(cid) and group in (None,'all',group_of(cid))}
            elif status=='converted':ids=set(converted)
            elif status in ('approved','ready'):ids={cid for cid in self.page_local.contexts if approved_context(cid)}
            elif status=='held' and automatic is not None:ids={cid for cid,item in automatic.items() if held_or_waiting(item)}
            elif status=='recording_review' and automatic is not None:ids={cid for cid,item in automatic.items() if item['duplicate_review']}|{cid for cid,saved in self.page_local.contexts.items() if saved['data'].get('duplicate_review')}
            elif status=='restarted':ids=set(restart)
        result=self.inventory.candidates('Audiobooks',limit if direct else 1000000,offset if direct else 0,search,status if direct else 'all',ids=ids) if ids is not None else \
            self.inventory.candidates('Audiobooks',limit if direct else 1000000,offset if direct else 0,search,status if direct else 'all')
        def current_auto(row):
            if automatic is not None:
                item=automatic.get(row['id'])
                return item if item and item['revision']==row['revision'] and item['fingerprint']==row['fingerprint'] else None
            return self.jobs.automatic.candidate(row) if self.jobs and hasattr(self.jobs,'automatic') else None
        def selected(row):
            saved=self.page_local.contexts.get(row['id']);ctx=saved['data'] if saved and saved['revision']==row['revision'] else {}
            choice=next((c for c in ctx.get('cover_choices',[]) if c['id']==ctx.get('cover_id')),None)
            approved=bool(not ctx.get('automatic_pending') and ctx.get('metadata_approved') and choice and any((self.cache/(choice['id']+suffix)).is_file() for suffix in ('.png','.jpg')))
            job=self.page_local.jobs.get(row['id'])
            if status=='recording_review':
                auto=current_auto(row)
                return bool(ctx.get('duplicate_review') or auto and auto.get('duplicate_review'))
            if status=='held':
                auto=current_auto(row)
                return bool(auto and held_or_waiting(auto))
            if status=='restarted':return row['id'] in restart
            if status=='review':return not approved
            if status=='approved':return approved
            if status=='jobs':return bool(job and job['state'] in ('Queued','Creating'))
            if status=='converted':return row['id'] in converted
            if status=='created':return bool(job and job['state']=='Audiobook created')
            if status=='output_attention':return bool(attention_listed(row['id']) and group in (None,'all',group_of(row['id'])))
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
                chosen=[r for r in result['rows'] if selected(r)];total=len(chosen)
                if status=='output_attention':
                    # Judy 2026-10-24, section 1: by reason, then source folder, then title, numbers in natural order (the
                    # parts of one set sit together: part 2 before part 10).
                    import re
                    natural=lambda text:[(0,int(t),'') if t.isdigit() else (1,0,t.casefold()) for t in re.split(r'(\d+)',str(text or ''))]
                    chosen.sort(key=lambda r:(self.ATTENTION_ORDER.get(group_of(r['id']),1),natural(r.get('scope')),natural(r.get('title_clue'))))
                if status=='restarted':chosen.sort(key=lambda r:restart.get(r['id'],9))
                chosen=chosen[offset:offset+limit]
            # Per-book extras for the shown page only.
            shown=[self.page_local.jobs[r['id']] for r in chosen if r['id'] in self.page_local.jobs]
            if shown and self.jobs and hasattr(self.jobs,'cleanup'):
                statuses=self.jobs.cleanup_statuses([job['job_id'] for job in shown]) if hasattr(self.jobs,'cleanup_statuses') else {job['job_id']:self.jobs.cleanup.status(job['job_id']) for job in shown}
                for job in shown:job['cleanup']=statuses[job['job_id']]
            waiting=[job['job_id'] for job in shown if job['state'] in ('Output needs attention','Audiobook created')]
            if waiting and hasattr(self.jobs,'attention_summary'):
                details=self.jobs.attention_summary(waiting)
                for job in shown:
                    item=details.get(job['job_id'])
                    if item:
                        if 'retry' in item:job['retry']=item.pop('retry')
                        if 'repair' in item:job['repair']=item.pop('repair')
                        if 'readmission' in item:job['readmission']=item.pop('readmission')
                        if 'keep' in item:job['keep']=item.pop('keep')
                        job['attention']=item
            created=[job['job_id'] for job in shown if job['state']=='Audiobook created' and 'attention' not in job]
            if created and hasattr(self.jobs,'kept_by_choice'):
                kept=self.jobs.kept_by_choice(created)
                for job in shown:
                    if job['job_id'] in kept:job['kept']=True
            queued=[job['job_id'] for job in shown if job['state']=='Queued']
            if queued and hasattr(self.jobs,'readmission_status'):
                # A Retry/Repair child waiting to run right after the current book: its place, after any refresh.
                found=self.jobs.readmission_status(queued)
                for job in shown:
                    if job['job_id'] in found:job['readmission']=found[job['job_id']]
            if job_rows is not None and self.jobs and hasattr(self.jobs,'current_audiobook'):
                self.page_local.audiobooks={r['id']:self.jobs.current_audiobook(r['id'],jobs=job_rows) for r in chosen}
            rows=[self.enrich(r,check_sources=False) for r in chosen]
            for row in rows:
                if row['id'] in needs:
                    # The shown page only: the question, its proposals and the destination (Judy's section 11).
                    try:row['ask']=self.jobs.ask_payload(row,needs[row['id']])
                    except (ValueError,OSError,sqlite3.Error) as error:row['ask']={'kind':needs[row['id']]['group'],'reasons':needs[row['id']]['reasons'],'fields':{},'candidates':[],'destination':{'path':'','taken':False,'reason':str(error)[:200]}}
                elif ((row.get('automatic') or {}).get('wait') or {}).get('kind')=='original_title' and self.jobs and hasattr(self.jobs,'approval_preview'):
                    # Judy 0.22.2 section 4 (ruling 29): "If none is found, goes to" what Approve would file now; shown rows only.
                    import original_titles
                    try:
                        preview=self.jobs.approval_preview(row['id'],row['revision'])
                        destination={'path':preview['path'],'absolute':preview['absolute'],'taken':preview['taken'],'reason':preview['reason']}
                        fields={'title':{'proposal':preview['title'],'basis':''},'author':{'proposal':preview['author'],'basis':''}}
                    except (ValueError,OSError,sqlite3.Error) as error:
                        destination={'path':'','absolute':'','taken':False,'reason':str(error)[:200]};fields={}
                    row['original_title']={'state':'waiting','destination':destination}
                    # The row's own Approve (rulings 6b and 29) through the to-do row's machinery; never in bulk.
                    row['ask']={'kind':'original_title','why':'','reasons':[original_titles.WAIT_REASON],'fields':fields,'candidates':[],'destination':destination,'odd_name':True}
            self._names_lines(rows)
            import book_delete
            recheck=False
            for row in rows:
                # Delete book (ruling 23; Judy's spec, sections 2 and 9): the server's typed offer, never guessed by the page.
                # Missing files rows (ask.delete) and the two broken-audio Stopped rows (attention.delete); present, every
                # file the press would delete (rulings 24 and 26: other files, working files too), picks the tooltip.
                # Remove this copy (ruling 25, Judy's update spec 3.1): ask.copy, only where the app holds the proof.
                # Each press re-checks every refusal and the proof itself (book_delete.plan).
                ask=row.get('ask');job=(row.get('creation') or {}).get('job') or {};attention=job.get('attention') if isinstance(job,dict) else None
                if isinstance(ask,dict) and ask.get('kind')=='files_missing':ask['delete']={'kind':'files_missing','present':book_delete.present(self.jobs,row)}
                elif isinstance(attention,dict) and job.get('state')=='Output needs attention' and (attention.get('group')=='reacquire' or (attention.get('remedy') or {}).get('kind')=='replace_source'):
                    attention['delete']={'kind':'audio_damaged','present':book_delete.present(self.jobs,row)}
                elif isinstance(ask,dict) and ask.get('duplicate')=='verified':
                    try:source=book_delete.copy_source(self.jobs,row,exists=False)
                    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error):source=None
                    if source and os.path.isfile(source['final']):ask['copy']={'kind':'verified_duplicate','present':book_delete.present(self.jobs,row)}
                    # Futaba's 0.22.0 QA, m-15: with the audiobook out of reach (its drive away) there is no offer, and the
                    # drive coming back is no catalog commit, so a quiet list kept the page without it for 5 minutes. A
                    # page like this is read again sooner (MergeService.cached_page).
                    elif source:recheck=True
            if self.jobs and hasattr(self.jobs,'restart_view'):self.jobs.restart_view(rows)  # Started over marker, release
        finally:
            del self.page_local.contexts;del self.page_local.jobs;del self.page_local.ready_ids
            if hasattr(self.page_local,'audiobooks'):del self.page_local.audiobooks
        return {'rows':rows,'total':total,'reacquire_archives':result.get('reacquire_archives',[])}|({'restart_counts':restart_counts} if restart_counts is not None else {})|({'recheck':True} if recheck else {})

    def _actor(self,actor,note):
        if actor not in ('user','assistant'):raise ValueError('Unknown reviewer actor')
        if not isinstance(note,str) or len(note)>16000:raise ValueError('Evidence note exceeds bound')
        if actor=='assistant' and len(note.strip())<20:raise ValueError('Assistant review requires concrete supporting evidence')

    def routing_preview(self,library,id,revision,review):
        with self.lock:
            row=self._row(library,id,revision)
            if not isinstance(review,dict) or len(json.dumps(review))>16000:raise ValueError('Invalid preview metadata')
            if set(review)-set(TEXT_FIELDS)-{'multi_author','anthology'}:raise ValueError('Unknown preview field')
            draft=copy.deepcopy(review)
            for field in TEXT_FIELDS:
                value=draft.setdefault(field,'')
                if not isinstance(value,str) or len(value)>2000:raise ValueError('Preview fields must be bounded text')
            for field in ('multi_author','anthology'):
                if type(draft.setdefault(field,False)) is not bool:raise ValueError('Routing choices must be explicit booleans')
            draft['organization_policy']='books-hierarchy-v2'
            return propose(row['members'][0]['path'],self._output_root(row,draft,library),'audiobook',row['metadata'],draft,automatic_facts=self._context(row).get('metadata_facts'))

    def save(self,library,id,revision,review,approve=False,manual_note='',proposal_id=None,cover_id=None,actor='user',evidence=None,automatic_pending=None,automatic_facts=None,capture_manual=True,manual_source_values=None,decision_record=None,user_approval=False):
        """user_approval: Sergei's Approve through the private admission (MergeService.approve_book, ruling 6b): the
        user actor may carry the admission checkpoint and standing facts, and open metadata questions do not refuse."""
        with self.lock:
            row=self._row(library,id,revision); ctx=self._context(row); self._actor(actor,manual_note)
            if not isinstance(review,dict) or len(json.dumps(review))>16000:raise ValueError('Invalid canonical metadata')
            review=copy.deepcopy(review)
            review['organization_policy']='books-hierarchy-v2'
            ctx.pop('automatic_approval',None);ctx.pop('automatic_pending',None)
            if not user_approval:ctx.pop('user_approval',None)  # a later save is not covered by an earlier Approve
            private=actor=='assistant' or user_approval is True and actor=='user'
            if automatic_pending is not None:
                if not private or not approve or not isinstance(automatic_pending,dict) or set(automatic_pending)!={'matcher_version','work_id'} or not all(isinstance(v,str) and v for v in automatic_pending.values()):raise ValueError('Invalid private automatic approval checkpoint')
                ctx['automatic_pending']=copy.deepcopy(automatic_pending)
            if set(review)-set(TEXT_FIELDS)-{'multi_author','anthology','organization_policy'}:raise ValueError('Unknown canonical metadata field')
            for field in TEXT_FIELDS:
                value=review.setdefault(field,'')
                if not isinstance(value,str) or len(value)>2000:raise ValueError('Canonical metadata fields must be bounded text')
            for field in ('multi_author','anthology'):
                if type(review.setdefault(field,False)) is not bool:raise ValueError('Canonical routing choices must be explicit booleans')
            if automatic_facts is not None:
                if not private or automatic_pending is None:raise ValueError('Standing policy is private to automatic admission')
                from standing_metadata import validate_policy
                automatic_facts=validate_policy(row,review,automatic_facts)
            records=[]
            if evidence is not None:
                if not isinstance(evidence,list) or len(evidence)>30:raise ValueError('Invalid per-field evidence')
                # Local-file citations exist only for the private local-agreement admission.
                local=bool(automatic_facts is not None and automatic_facts.get('identity_basis')=='local_agreement')
                for record in evidence:
                    if not isinstance(record,dict):raise ValueError('Invalid evidence record')
                    if local and record.get('source_url')=='':
                        records.append(local_evidence(**{k:record[k] for k in ('field','cited_value','retrieved_utc','reviewer_actor','reviewer_identity','basis')}))
                    else:records.append(manual_evidence(**{k:record[k] for k in ('field','cited_value','source_url','retrieved_utc','reviewer_actor','reviewer_identity','basis')}))
                if any(e['reviewer_actor']!=actor for e in records):raise ValueError('Evidence actor must match actual reviewer')
            if actor=='assistant' and approve:
                needed=({'title','authors'}|({'original_language'} if automatic_facts['original_language']['value'] else set())|({'series','number'} if review.get('series') else set())) if automatic_facts else {'title','authors','original_language'}|({'series','number'} if review.get('series') else {'standalone'})
                if not needed<={r['field'] for r in records}:raise ValueError('Assistant approval requires per-field identity, author role, original language and series/standalone evidence')
                accepted={'title':automatic_facts['original_title'] if automatic_facts else review.get('title'),'authors':review.get('canonical_author'),'series':review.get('series'),'number':review.get('number'),'standalone':not bool(review.get('series'))}
                for field,value in accepted.items():
                    if field not in needed:continue
                    values=[r['cited_value'] for r in records if r['field']==field]
                    if not any(('; '.join(v) if isinstance(v,list) else str(v)).strip().casefold()==str(value).strip().casefold() for v in values):raise ValueError('Accepted metadata must match its cited evidence')
                langs=[str(r['cited_value']).strip().casefold() for r in records if r['field']=='original_language']
                if ('original_language' in needed) and (not langs or any(v in ('','unknown','other','unverified') for v in langs)):raise ValueError('Establish the actual original-work language in evidence')
                russian=any(v in ('russian','ru','rus','русский') for v in langs)
                if 'original_language' in needed and russian!=(review.get('original_language')=='Russian'):raise ValueError('Original-work language contradicts cited evidence')
            if approve and not user_approval:
                import metadata_choices
                metadata_choices.admission(self.metadata_questions(row,ctx),review)
            # Ruling 36 (Sergei 2026-10-26): his entries are final (ruling 6a); nothing asks him for evidence. The assistant's
            # own approvals still carry theirs (_actor).
            if approve and (actor=='assistant' and not manual_note.strip() or not (review.get('canonical_author') or '').strip()):raise ValueError('Confirm the author first.' if actor=='user' else 'Confirm the author role and record metadata evidence')
            if cover_id is not None and not any(c['id']==cover_id for c in ctx.get('cover_choices',[])):raise ValueError('Choose a discovered local cover')
            trial=copy.deepcopy(ctx);trial['cover_id']=cover_id or ctx.get('cover_id')
            if approve and not self._cover(trial):raise ValueError('Choose a usable cover')
            preview=propose(row['members'][0]['path'],self._output_root(row,review,library),'audiobook',row['metadata'],review,automatic_facts=automatic_facts)
            if approve and not preview['path']:raise ValueError(preview['reason'])
            if proposal_id is not None and not any(p['id']==proposal_id for p in self.matching.get(id,ctx.get('matching',{})).get('proposals',[])):raise ValueError('Unknown metadata proposal')
            changed=review!=row.get('review') or manual_note!=ctx.get('manual_note') or trial['cover_id']!=ctx.get('cover_id') or records!=ctx.get('metadata_evidence',[])
            fresh=self.inventory.save_candidate(library,id,revision,review,False)
            if automatic_facts is not None:ctx['metadata_facts']=copy.deepcopy(automatic_facts)
            else:ctx.pop('metadata_facts',None);ctx.pop('duplicate_review',None)
            ctx.update(manual_note=manual_note,proposal_id=proposal_id,cover_id=trial['cover_id'],metadata_actor=actor,metadata_utc=utc(),metadata_evidence=records,metadata_approved=bool(approve and automatic_pending is None))
            ctx.pop('manual_metadata_acceptance',None)
            if actor=='user' and approve:ctx['manual_metadata_acceptance']=manual_metadata.acceptance(fresh,review)
            if changed:ctx.update(source_coverage_confirmed=False,order_confirmed=False,source_hashes={})
            return self._write(fresh,ctx,manual_source=manual_metadata.capture(fresh,manual_source_values if manual_source_values is not None else review,manual_note) if actor=='user' and capture_manual else None,decision_record=decision_record)

    def match(self,library,id,revision):
        with self.lock:
            row=self._row(library,id,revision)
            if id in self.workers and self.workers[id].is_alive():return self.enrich(row)['matching']
            with connect(self.inventory.database) as db:entered=manual_metadata.proposals(manual_metadata.records(db,row))
            query=(row.get('review') or {}).get('title') or (entered[0].get('title') if entered else '') or row['title_clue']
            author=(row.get('review') or {}).get('canonical_author') or (entered[0].get('authors') if entered else '') or ''
            self.matching[id]={'state':'finding','proposals':self._context(row).get('matching',{}).get('proposals',[]),'error':''}
            def lookup():
                try:
                    proposals=self.client.lookup(query,author)
                    for p in proposals:p['id']=str(uuid.uuid5(uuid.NAMESPACE_URL,p['public_url']))
                    conflicts=manual_metadata.compare(entered,proposals)
                    result={'state':'found' if proposals or entered else 'empty','proposals':entered+proposals,'conflicts':conflicts,'error':''}
                except SourceUnavailable as error:result={'state':'unavailable','proposals':entered+[p for p in self.matching[id]['proposals'] if not p.get('manual_source')],'error':str(error),'code':error.code}
                except Exception:result={'state':'unavailable','proposals':entered+[p for p in self.matching[id]['proposals'] if not p.get('manual_source')],'error':'Metadata source unavailable. Review cached evidence or enter verified metadata manually.'}
                with self.lock:
                    try:
                        current=self._row(library,id,revision);ctx=self._context(current);ctx['matching']=result
                        self._write(current,ctx,False);self.matching[id]=result
                    except ValueError:self.matching.pop(id,None)
            worker=threading.Thread(target=lookup,daemon=True);self.workers[id]=worker;worker.start()
            return copy.deepcopy(self.matching[id])

    def covers(self,library,id,revision,all_embedded=False,stop=None):
        with self.lock:
            stop=stop or threading.Event()
            if stop.is_set():raise InterruptedError('Automatic cover inspection paused')
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
                            run_owned([decoder,'-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1','-protocol_whitelist','file','-f','image2','-i',str(destination),'-frames:v','1','-f','null','-'],self.cache,stop,10,1024)
                            self._decoded.add(hash)
                if not any(c['id']==cover_id for c in choices):choices.append({'id':cover_id,'source_label':label,'source_url':'','evidence_kind':'Local artwork — edition unverified','thumbnail_url':'/api/cover?id='+cover_id,'sha256':hash})
            for companion in row.get('companions',[])[:50]:
                if stop.is_set():raise InterruptedError('Automatic cover inspection paused')
                path=Path(companion['path'])
                if path.suffix.lower() not in ('.jpg','.jpeg','.png') or companion.get('error') or companion.get('missing'):continue
                try:
                    before=fresh_stat(path)
                    if before.st_size>MAX_COVER:continue
                    with open(path,'rb') as source:data=source.read(MAX_COVER+1)
                    if identity(before)!=identity(fresh_stat(path)):continue
                    add(data,path.name)
                except InterruptedError:raise
                except (OSError,ValueError,subprocess.TimeoutExpired):continue
            # Embedded artwork is extracted only when an attached picture is catalogued.
            ffmpeg=shutil.which('ffmpeg')
            if ffmpeg:
                with connect(self.inventory.database) as db:
                    for m in (row['members'] if all_embedded else row['members'][:30]):
                        if stop.is_set():raise InterruptedError('Automatic cover inspection paused')
                        raw=db.execute('SELECT metadata FROM files WHERE root=? AND path=?',(self._source_root(row,library),m['path'])).fetchone()
                        streams=json.loads(raw[0]).get('probe',{}).get('streams',[]) if raw else []
                        attached=next((s for s in streams if s.get('disposition',{}).get('attached_pic')==1),None)
                        if attached is None:continue
                        try:
                            before=fresh_stat(m['path'])
                            with DirectoryBoundary(self.cache.anchor,self.cache):
                                data=run_owned([ffmpeg,'-v','error','-nostdin','-threads','2','-filter_threads','1','-protocol_whitelist','file','-f',INPUT_FORMATS[Path(m['path']).suffix.lower()],'-i',m['path'],'-map','0:'+str(attached['index']),'-frames:v','1','-vf','scale=1200:1200:force_original_aspect_ratio=decrease','-f','image2pipe','-c:v','png','pipe:1'],self.cache,stop,15,MAX_COVER)
                            if identity(before)==identity(fresh_stat(m['path'])):add(data,'Embedded artwork: '+m['filename'])
                        except InterruptedError:raise
                        except (OSError,ValueError,TimeoutError,subprocess.TimeoutExpired):pass
                        if not all_embedded:break
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

    def tracks(self,library,id,revision,order,included,source_coverage_confirmed,order_confirmed,chapters,actor='user',evidence_note='',stop=None,keep_pending=False):
        """keep_pending: Sergei's Approve (MergeService.approve_book) keeps its pending admission through this step."""
        with self.lock:
            row=self._row(library,id,revision);ctx=self._context(row);keys=self._keys(row);self._actor(actor,evidence_note)
            if actor=='user' and not keep_pending:ctx.pop('automatic_approval',None);ctx.pop('automatic_pending',None)
            if not isinstance(order,list) or len(order)!=len(keys) or set(order)!=set(keys) or not isinstance(included,list) or len(set(included))!=len(included) or not set(included)<=set(keys):raise ValueError('Review the exact known member list and order')
            if any(type(v)is not bool for v in (source_coverage_confirmed,order_confirmed,chapters)):raise ValueError('Track confirmations must be explicit booleans')
            # Futaba's 0.22.0 QA, m-7 (ruling 6b removed mandatory notes): Sergei's own track review needs no typed note;
            # an assistant review still records concrete evidence (_actor).
            if actor!='user' and (source_coverage_confirmed or order_confirmed) and not evidence_note.strip():raise ValueError('Record the membership and order review basis')
            titles=[m.get('track_title') for m in row['members'] if member_key(m['path']) in included]
            if chapters and not chapters_available([m for m in row['members'] if member_key(m['path']) in included]):raise ValueError('Chapter boundaries unavailable: source durations need checking')
            hashes={}
            if source_coverage_confirmed and order_confirmed:
                for m in row['members']:
                    key=member_key(m['path'])
                    if key not in included:continue
                    before=fresh_stat(m['path'])
                    if before.st_size!=m['size'] or before.st_mtime_ns!=int(m['modified']):raise ValueError('Source changed — review required')
                    hash=source_hash(m['path'],before,stop) if stop is not None else source_hash(m['path'],before);after=fresh_stat(m['path'])
                    if identity(before)!=identity(after):raise ValueError('Source changed — review required')
                    hashes[key]={'sha256':hash,'size':before.st_size,'modified':str(before.st_mtime_ns),'dev':before.st_dev,'ino':before.st_ino}
            ctx.update(track_order=order,included=included,source_coverage_confirmed=source_coverage_confirmed,order_confirmed=order_confirmed,chapters=chapters,track_actor=actor,track_utc=utc(),track_evidence=evidence_note,source_hashes=hashes)
            return self._write(row,ctx)

    def build_manifest(self,library,id,revision,allow_existing_job=False,allow_automatic_pending=False,stop=None,held=None):
        """held (0.21.0 in-place publication only): {normcase path: {'sha256','source_chapters'}} for a source the
        converting job holds deny-writers after proving its reviewed bytes in full; its metadata edit changes size."""
        import reacquire_sources,source_proofs
        with connect(self.inventory.database) as db:reacquire_sources.require_admission(db,id)
        with self.lock:
            held=held or {}
            # ready=False: the converter's revision guard (_guard) runs this up to four times per book under group_lock (F31).
            row=self.enrich(self._row(library,id,revision),allow_existing_job=allow_existing_job,allow_automatic_pending=allow_automatic_pending,held=held,ready=False);ctx=self._context(row)
            if not row['creation']['can_create']:raise ValueError('; '.join(row['creation']['reasons']))
            members={m['member_key']:m for m in row['members']};sources=[]
            for key in row['track_order']:
                if key not in row['included']:continue
                m=members[key];stored=ctx['source_hashes'][key];proof=held.get(os.path.normcase(os.path.abspath(m['path'])))
                if proof is not None:
                    if proof['sha256']!=stored['sha256']:raise ValueError('Source changed — review required')
                else:
                    stat=fresh_stat(m['path'])
                    if not unchanged_screen(stat,stored):raise ValueError('Source changed — review required')
                    # One full hash per attempt; later checks in it compare size, ns mtime, volume and file ID (source_proofs).
                    if not source_proofs.unchanged(m['path'],stored['sha256'],stat):
                        if (source_hash(m['path'],stat,stop) if stop is not None else source_hash(m['path'],stat))!=stored['sha256']:raise ValueError('Source changed — review required')
                        source_proofs.remember(m['path'],stored['sha256'],stat)
                sources.append({'path':m['path'],'size':stored['size'],'modified':stored['modified'],'sha256':stored['sha256'],'fingerprint':{'size':stored['size'],'modified':stored['modified']},'metadata':m['metadata']})
            cover=row['selected_cover'];cover=cover|{'path':str(self.cover_file(cover['id']))}
            comments=future_audio_tags(row['metadata'],row['review'])['COMMENTS']
            manual_m4b=bool(len(sources)==1 and Path(sources[0]['path']).suffix.lower()=='.m4b' and manual_metadata.approved(row,ctx))
            automatic_profile=bool(ctx.get('metadata_facts')) or manual_m4b
            profile=AUTOMATIC_PROFILE if automatic_profile else PROFILE
            encoding=freeze_automatic_policy(sources) if automatic_profile else freeze_policy(sources)
            manifest={'job_id':str(uuid.uuid4()),'candidate_id':id,'candidate_revision':revision,'sources':sources,'metadata':copy.deepcopy(row['review']),
                    'root':self._source_root(row,library),'output_root':self._output_root(row,library=library),'destination':row['creation']['destination'],'profile':profile,'encoding_policy':encoding,'cover':cover,'comments':comments,
                    'cleanup_policy':row['creation']['cleanup_policy'],
                    'evidence':{'metadata_actor':ctx['metadata_actor'],'metadata_utc':ctx['metadata_utc'],'manual_note':ctx['manual_note'],'metadata_fields':ctx.get('metadata_evidence',[]),'track_actor':ctx['track_actor'],'track_utc':ctx['track_utc'],'track_basis':ctx['track_evidence'],'recording_completeness':'unknown'},
                    'chapters':chapter_names([members[key] for key in row['track_order'] if key in row['included']]) if ctx.get('chapters') else []}
            if ctx.get('metadata_facts'):
                manifest['metadata_facts']=copy.deepcopy(ctx['metadata_facts'])
                manifest['duplicate_review']=copy.deepcopy(ctx.get('duplicate_review'))
            if manual_m4b:
                manifest['evidence']['manual_metadata_acceptance']=copy.deepcopy(ctx['manual_metadata_acceptance'])
            if automatic_profile:
                if len(sources)==1 and Path(sources[0]['path']).suffix.lower()=='.m4b':
                    from audio_pipeline import source_chapters
                    proof=held.get(os.path.normcase(os.path.abspath(sources[0]['path'])))
                    # A held in-place source is open for DELETE (no reader may open it); its chapters were re-probed after the edit.
                    manifest['source_chapters']=copy.deepcopy(proof['source_chapters']) if proof is not None else source_chapters(sources[0]['path'],self.cache,stop or threading.Event(),row['creation']['duration_seconds'])
                else:
                    from groups import PART_SET_MAX
                    chosen=[members[key] for key in row['track_order'] if key in row['included']]
                    if 1<len(chosen)<=PART_SET_MAX and all(Path(m['path']).suffix.lower()=='.m4b' for m in chosen):
                        # Rulings 19 and 19a: joined .m4b parts keep every part's own chapters, frozen here and proven again
                        # on each protected snapshot; parts without any chapters (and a book's many chapter files) keep one
                        # chapter per part as before.
                        from audio_pipeline import source_chapters,part_chapter_name
                        plan=[{'name':part_chapter_name(m),'chapters':source_chapters(m['path'],self.cache,stop or threading.Event(),float(m.get('duration') or 0))}
                              for m in chosen]
                        if any(part['chapters'] for part in plan):manifest['part_chapters']=plan
            return manifest
