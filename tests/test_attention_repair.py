"""v0.16.7 M4B re-admission (Retry), user-requested damage Repair and the server-side Retry all.

Real AudioJobs ledgers and the real repair_damaged_m4b admission; the review service, resume and
the worker are doubles. No library, no Z:, no media encoding.
"""
import copy,hashlib,json,tempfile,threading,time,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

import audio_jobs
import failed_m4b_retry
import m4b_readmission
import m4b_repair
from audio_jobs import AudioJobs,RetryRefused,repair_record,RETRY_WORKER_BUSY,REPAIR_WORKER_BUSY,REPAIR_SCANNING,RETRY_BOOK_CHANGED,RETRY_ALL_RUNNING,RETRY_ALL_NONE,RETRY_SCANNING
from merge_service import MergeService
from review_backend import CandidateReviewService
from test_m4b_preservation import TEXT_SOURCE,dangling,fixture
import test_blocked_retry

AREA=Path(__file__).resolve().parents[1]/'scratch'/'attention-repair-tests';AREA.mkdir(parents=True,exist_ok=True)
LEGACY='Remux changed the decoder configuration or relative audio packet timing'
REFUSED='M4B preservation requires review: Unsupported structural box'
OUTSIDE='M4B preservation requires review: Fixture shape outside REASONS'  # never in his REASONS
ALIVE=SimpleNamespace(is_alive=lambda:True)
REAL_CHECK=MergeService._check_repairs


class Ledger:
    """One catalog file holding the jobs ledger and the candidate tables, as in the app."""
    def __init__(self,folder):
        self.base=Path(folder);self.db=self.base/'catalog.sqlite3';self.library=self.base/'library';self.library.mkdir()
        self.jobs=AudioJobs(self.db,None,lambda manifest:True,lambda record:False)
        with self.jobs._db() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS book_groups(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT);CREATE TABLE IF NOT EXISTS candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT);')

    def failed(self,reason=LEGACY,source=b'fixture',name='book',validation=True,candidate=None):
        folder=self.library/name;folder.mkdir(exist_ok=True);path=folder/'source.m4b';path.write_bytes(source)
        candidate=candidate or str(uuid.uuid4())
        manifest={'job_id':str(uuid.uuid4()),'candidate_id':candidate,'candidate_revision':1,'root':str(self.library),
            'sources':[{'path':str(path),'sha256':hashlib.sha256(source).hexdigest(),'fingerprint':{'size':len(source),'modified':1}}],
            'metadata':{'title':'Approved '+name},'destination':str(self.base/'out'/(name+'.m4b')),'profile':'test frozen profile',
            'evidence':{'approved':True},'cover':{},'source_chapters':[],'cleanup_policy':{'enabled':False}}
        with self.jobs._db() as db:
            db.execute('INSERT OR REPLACE INTO book_groups VALUES(?,?,?)',(candidate,1,'frozen'))
            db.execute('INSERT OR REPLACE INTO candidate_context VALUES(?,?,?)',(candidate,1,'{"approved":true}'))
        job_id=self.jobs.enqueue(manifest)
        journal={'failure':{'exception_class':'ValidationError','retryable':False,'at':1}} if validation else {}
        self.jobs._update(job_id,state='needs attention',stage='checking',reason=reason,journal=json.dumps(journal))
        return job_id,manifest

    def row(self,job_id):return self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))[0]
    def count(self):return len(self.jobs._rows())


class Base(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
        self.l=Ledger(self.temp.name);self.addCleanup(self.l.jobs.close)
        # The background repair check reads sources; tests that need it call it explicitly.
        patcher=patch.object(MergeService,'_check_repairs');self.checks=patcher.start();self.addCleanup(patcher.stop)
        checks=patch.dict(audio_jobs.REPAIR_CHECKS);checks.start();self.addCleanup(checks.stop)  # passed() entries end with the test

    def passed(self,*job_ids):
        """A finished read-only dry run that passed, as the background check records it. Since the 2026-10-19
        follow-up an M4B row is "ready to retry" only after it; until then it is Checking."""
        for job_id in job_ids:audio_jobs.remember_repair_check(audio_jobs.repair_check_key(self.l.row(job_id)),{'state':'intact','reason':'','damage':[],'repairs':[]})

    def service(self):
        s=MergeService.__new__(MergeService);s.jobs=self.l.jobs;s.operation_lock=threading.RLock();s.draining=False
        s.inventory=SimpleNamespace(worker=None,database=self.l.db,group_lock=threading.RLock(),roots={'Audiobooks':str(self.l.library)});s.reviews=SimpleNamespace(lock=threading.RLock())
        s.working=SimpleNamespace(admission_clear=lambda row:None);s.stage_root=self.l.base/'staging';s.stage_root.mkdir(exist_ok=True)
        from producer_recovery import ProducerRecovery
        s.producer_recovery=ProducerRecovery(self.l.db,s.stage_root)
        s.cleanup=SimpleNamespace(status=lambda job_id=None:None);s.automatic=SimpleNamespace(stop_event=threading.Event())
        s.resume=Mock(return_value={'state':'Running'});s._state=Mock(return_value={'state':'Running'});s._resume_later=Mock()
        s.jobs.m4b_working_clear=s._m4b_working_clear  # as MergeService.__init__ wires it
        s.jobs.repair_check_failed=s._repair_check_failed
        s.jobs.working_state=s._working_state  # leftover working files decide the row live (RefusedRetry follow-up 2)
        return s

    def summary(self,service=None):return (service or self.service()).attention_summary()


class ClassificationTests(Base):
    def test_m4b_reasons_from_the_module_are_can_retry_with_new_child_retry_data(self):
        job_id,_=self.l.failed();self.passed(job_id)
        self.assertEqual(self.summary()[job_id],{'group':'retry','cause':None,'originals_untouched':True,'precheck':'passed','retry':{'allowed':True,'reason':''}})
        self.l.jobs._thread=ALIVE
        try:self.assertEqual(self.summary()[job_id]['retry'],{'allowed':True,'reason':''},'accepted while a book is being created')
        finally:self.l.jobs._thread=None
        with self.l.jobs._db() as db:m4b_readmission.request(db,job_id,'retry',100)
        self.assertEqual(self.summary()[job_id]['readmission']['queued_next'],True)
        self.assertEqual(self.summary()[job_id]['readmission']['position'],1,'its place survives every status read')
        self.assertNotIn(OUTSIDE,failed_m4b_retry.REASONS)
        other,_=self.l.failed(OUTSIDE,name='other');self.passed(other)
        self.assertEqual(self.summary()[other]['group'],'unsupported','a reason outside REASONS stays out')
        with patch.object(failed_m4b_retry,'REASONS',failed_m4b_retry.REASONS|{OUTSIDE}):
            self.assertEqual(self.summary()[other]['group'],'retry','REASONS is read from his module, never a copy')

    def test_provable_damage_is_can_repair_never_retry(self):
        job_id,_=self.l.failed()
        found={'state':'repairable','reason':REFUSED,'damage':['The chapter list pointed to missing track 3.'],
               'repairs':[{'kind':'dangling_chapter_reference','track_id':1,'removed':[3],'kept':[2],'description':'The chapter list pointed to missing track 3.'}]}
        with patch.object(m4b_repair,'classify',return_value=found):
            value=self.summary()[job_id]
            self.assertEqual(value['group'],'repair');self.assertNotIn('retry',value)
            self.assertEqual(value['damage'],[{'kind':'dangling_chapter_reference','removed':[3],'description':'The chapter list pointed to missing track 3.'}])
            self.assertEqual(value['repair'],{'allowed':True,'reason':''})
            self.l.jobs._thread=ALIVE
            try:self.assertEqual(self.summary()[job_id]['repair'],{'allowed':True,'reason':''},'accepted while a book is being created')
            finally:self.l.jobs._thread=None
        # 2026-10-19 (Sergei-approved pre-check): "ready to retry" only after the read-only dry run passed; a source
        # this build refuses is an M4B the app cannot convert now.
        for state,group in (('intact','retry'),('refused','unsupported')):
            with patch.object(m4b_repair,'classify',return_value={'state':state,'reason':'x'}):
                self.assertEqual(self.summary()[job_id]['group'],group,state)

    def test_unchecked_rows_are_checked_off_the_request_thread_once(self):
        job_id,_=self.l.failed();s=self.service()
        self.assertNotIn('repair_check',s.attention_summary()[job_id],'the internal flag never reaches the page')
        self.checks.assert_called_once_with([job_id])
        seen=[];real=m4b_repair.check
        with patch.object(MergeService,'_check_repairs',REAL_CHECK),patch.object(m4b_repair,'check',side_effect=lambda row,stop=None:(seen.append(row['job_id']),real(row,stop))[1]):
            s.attention_summary();deadline=time.monotonic()+10
            while s.__dict__.get('_repair_running') and time.monotonic()<deadline:time.sleep(.02)
            s._repair_thread.join(10)  # the flag clears before the worker's last catalog write; wait for that write too
        self.assertEqual(seen,[job_id]);self.assertEqual(m4b_repair.classify(self.l.row(job_id))['state'],'refused','the fixture source is no M4B movie')
        s.attention_summary();self.assertEqual(self.checks.call_count,1,'a checked row is never read again')

    def test_superseded_failures_are_history_not_attention(self):
        job_id,manifest=self.l.failed();parent=self.l.row(job_id)
        child=copy.deepcopy(manifest);child['job_id']=str(uuid.uuid4());child['metadata']['title']='Newer'
        self.l.jobs.enqueue(child)
        self.assertNotIn(job_id,self.summary(),'the book shows its newer job')

    def test_repair_record_follows_the_job(self):
        self.assertIsNone(repair_record({'manifest':{}}))
        binding={'schema':m4b_repair.SCHEMA,'repairs':[{'kind':'mdat_tail_overrun','padding':8,'description':'d'}],'note':'The audio container declared 8 bytes past the end.'}
        queued=repair_record({'manifest':{'m4b_repair':binding}})
        self.assertEqual(queued,{'applied':False,'patched':[{'kind':'mdat_tail_overrun','padding':8}],'detail':binding['note']})
        done=repair_record({'manifest':{'m4b_repair':binding},'output':{'validation':{'damage_repair':{'note':'applied note','repairs':[{'kind':'mdat_tail_overrun','padding':8}]}}}})
        self.assertEqual(done,{'applied':True,'patched':[{'kind':'mdat_tail_overrun','padding':8}],'detail':'applied note'})
        self.assertIsNone(repair_record({'manifest':{'m4b_repair':{'schema':failed_m4b_retry.SCHEMA}}}),'a preserved-M4B retry child is no repair')
        silence={'schema':m4b_repair.SCHEMA,'note':'n','repairs':[{'kind':'truncated_final_frames','track_id':1,'first_frame':9,'frames':1,'replaced_ticks':1024,'timescale':44100,'silent_frame':'00c80007','description':'d'}]}
        self.assertEqual(repair_record({'manifest':{'m4b_repair':silence}})['patched'],[{'kind':'truncated_final_frames','frames':1,'replaced_ticks':1024,'timescale':44100}],'the amount the panel shows')
        # 0.22.0 (ruling 10, Judy's to-do spec section 2): the "Needs your answer" reasons come first, Missing files first of all.
        self.assertEqual(CandidateReviewService.ATTENTION_ORDER,{'files_missing':-8,'title_author':-7,'author_unclear':-6,'same_author':-5,'name_taken':-4,'part_of_book':-3,'files_unclear':-2,'order_unclear':-1,
                                                                 'retry':0,'repair':1,'reacquire':1.5,'checking':2,'changed':3,'audiobook':4,'other':5,'unsupported':6},'Reacquire follows Can repair and precedes Checking')


class RetryRouteTests(Base):
    """A Retry click is accepted at once, even while a book converts, and runs right after it (m4b_readmission)."""
    def child(self,manifest):
        fresh=copy.deepcopy(manifest);fresh['job_id']=str(uuid.uuid4());fresh['metadata']['title']+=' (retry)';return self.l.jobs.enqueue(fresh)

    def test_click_queues_next_and_the_worker_admits_through_the_proof_route(self):
        job_id,manifest=self.l.failed();other,other_manifest=self.l.failed(name='other');self.passed(job_id,other);s=self.service();self.l.jobs._thread=ALIVE
        try:
            with patch.object(MergeService,'_retry_preserved_m4b') as admit:
                result=s.retry_blocked_job('Audiobooks',manifest['candidate_id'],1,job_id)
                again=s.retry_blocked_job('Audiobooks',manifest['candidate_id'],1,job_id)
                second=s.retry_blocked_job('Audiobooks',other_manifest['candidate_id'],1,other)
            admit.assert_not_called()  # nothing is proven or admitted on the request thread
        finally:self.l.jobs._thread=None
        self.assertEqual({key:result[key] for key in ('job_id','requeued','accepted','queued_next','position','kind','state')},
                         {'job_id':job_id,'requeued':False,'accepted':True,'queued_next':True,'position':1,'kind':'retry','state':'queued'})
        self.assertNotIn('audiobook_jobs',result,'no status computed in the reply');self.assertEqual(again['position'],1,'a second press keeps its place');self.assertEqual(second['position'],2)
        self.assertEqual(s._resume_later.call_count,2,'a repeat press changes nothing (v0.16.12)');s.resume.assert_not_called()
        # Between books the worker admits the head request through the unchanged proof route, then runs its child next.
        calls=[]
        def admit(service,parent,now,in_worker=False):calls.append((parent['job_id'],in_worker));return {'requeued':True,'job_id':self.child(json.loads(parent['manifest']))}
        with patch.object(MergeService,'_retry_preserved_m4b',admit):child=s._next_m4b_readmission()
        self.assertEqual(calls,[(job_id,True)]);self.assertEqual(self.l.row(child)['state'],'pending')
        self.assertNotIn(job_id,s.attention_summary(),'the parent is history once its child exists')
        status=s.candidate_status(manifest['candidate_id'])
        self.assertEqual((status['state'],status['readmission']['queued_next'],status['readmission']['position']),('Queued',True,1),'the child keeps its place')
        self.assertEqual(s.attention_summary()[other]['readmission']['position'],2)

    def test_refusals_are_per_book_and_stale_views_change_nothing(self):
        job_id,manifest=self.l.failed();self.passed(job_id);s=self.service();before=self.l.row(job_id)
        with patch.object(MergeService,'_retry_preserved_m4b') as admit:
            for identity,revision in ((manifest['candidate_id'],2),(str(uuid.uuid4()),1)):
                with self.assertRaises(RetryRefused) as caught:s.retry_blocked_job('Audiobooks',identity,revision,job_id)
                self.assertEqual(str(caught.exception),RETRY_BOOK_CHANGED)
            admit.assert_not_called()
        s.resume.assert_not_called();self.assertNotIn('readmission',s.attention_summary()[job_id])
        reason='Prior audio working files need verified disposal before another source copy'
        s.retry_blocked_job('Audiobooks',manifest['candidate_id'],1,job_id)
        with patch.object(MergeService,'_retry_preserved_m4b',return_value={'retryable':True,'requeued':False,'reason':reason,'cause':'working_files'}):
            self.assertIsNone(s._next_m4b_readmission(),'the normal queue runs')
        value=s.attention_summary()[job_id]
        self.assertEqual({key:value['readmission'].get(key) for key in ('queued_next','accepted','reason','cause','fix','stale')},
                         {'queued_next':False,'accepted':False,'reason':reason,'cause':'working_files','fix':'wait','stale':False})
        # Follow-up 2 (section 2.2): a working-files record no longer decides the row; with no files left it reads as if
        # there were no record (ready to retry, in Can retry).
        self.assertEqual(value['group'],'retry');self.assertEqual(value['retry'],{'allowed':True,'reason':''},'the button comes back');self.assertEqual(self.l.row(job_id),before)
        self.assertTrue(s.retry_blocked_job('Audiobooks',manifest['candidate_id'],1,job_id)['queued_next'],'a refused book can be pressed again')
        # During a library scan the request keeps its place for the next resume.
        s.inventory.worker=ALIVE
        try:self.assertIsNone(s._next_m4b_readmission())
        finally:s.inventory.worker=None
        self.assertTrue(s.attention_summary()[job_id]['readmission']['queued_next'])


class RepairAdmissionTests(Base):
    """repair_damaged_m4b end to end on a real damaged M4B: the admission test the other Ender could not run."""
    def setUp(self):
        super().setUp()
        self.source=dangling(TEXT_SOURCE(),[3,2])
        self.job_id,self.manifest=self.l.failed(REFUSED,self.source)
        self.path=Path(self.manifest['sources'][0]['path']);self.parent=self.l.row(self.job_id)
        self.s=self.service();self.s.reviews.build_manifest=self.build

    def build(self,library,identity,revision,allow_existing_job=False,stop=None):
        fresh=copy.deepcopy(self.manifest);fresh['job_id']=str(uuid.uuid4());return fresh

    def children(self):return [row for row in self.l.jobs._rows() if row['job_id']!=self.job_id]

    def test_one_proven_child_with_the_approved_repair_and_untouched_originals(self):
        before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        result=self.s._repair_damaged_m4b(self.l.row(self.job_id),100,in_worker=True)
        self.assertTrue(result['requeued'],result);self.assertEqual(result['parent_job_id'],self.job_id);self.assertTrue(result['damage'])
        [child]=self.children();stored=json.loads(child['manifest'])
        self.assertEqual(child['state'],'pending');self.assertEqual(m4b_repair.approved_repairs(stored),{'dangling_chapter_reference'})
        self.assertTrue(stored['m4b_repair']['user_requested']);self.assertEqual(self.l.row(self.job_id),self.parent,'the failed parent row is kept unchanged')
        with self.l.jobs._db() as db:self.assertEqual(db.execute('SELECT parent_job_id,child_job_id FROM audio_repair_admissions').fetchall()[0][:],(self.job_id,child['job_id']))
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before,'Repair only reads the original')
        self.s.resume.assert_not_called()  # the worker runs it next itself
        # One child per failed parent: a second admission admits nothing.
        again=self.s._repair_damaged_m4b(self.l.row(self.job_id),101,in_worker=True)
        self.assertFalse(again['requeued']);self.assertIn('Repair refused',again['reason']);self.assertEqual(len(self.children()),1)
        # The book now shows the queued repair, permanently, from the child's own manifest.
        status=self.s.candidate_status(self.manifest['candidate_id'])
        self.assertEqual(status['state'],'Queued');self.assertFalse(status['repaired']['applied'])
        self.assertEqual([item['kind'] for item in status['repaired']['patched']],['dangling_chapter_reference'])
        self.assertNotIn(self.job_id,self.s.attention_summary(),'the parent left the attention list')

    def test_refusals_admit_nothing_and_change_nothing(self):
        attempt=self.s.stage_root/self.job_id/str(uuid.uuid4());attempt.mkdir(parents=True);snapshot=attempt/'source00000.m4b';snapshot.write_bytes(b'unfinished copy')
        admit=lambda:self.s._repair_damaged_m4b(self.l.row(self.job_id),100,in_worker=True)
        self.assertIn('Prior audio working files',admit()['reason']);self.assertEqual(snapshot.read_bytes(),b'unfinished copy')
        snapshot.unlink()
        self.l.jobs._thread=ALIVE
        try:self.assertEqual(self.s._repair_damaged_m4b(self.l.row(self.job_id),100)['reason'],REPAIR_WORKER_BUSY,'outside the worker the busy rule stays')
        finally:self.l.jobs._thread=None
        def changed(*args,**kwargs):fresh=self.build(*args,**kwargs);fresh['metadata']['title']='Edited';return fresh
        self.s.reviews.build_manifest=changed
        self.assertIn('Frozen review',admit()['reason'])
        self.assertEqual(self.children(),[]);self.assertEqual(self.l.row(self.job_id),self.parent);self.s.resume.assert_not_called()

    def test_an_intact_source_has_no_repair(self):
        job_id,_=self.l.failed(REFUSED,fixture(),name='intact')
        self.assertEqual(self.s._repair_damaged_m4b(self.l.row(job_id),100,in_worker=True),{'requeued':False,'reason':'No provable repair: the source is intact','cause':'unknown'})

    def test_button_request_rules(self):
        identity=self.manifest['candidate_id']
        for args,message in (((identity,2),RETRY_BOOK_CHANGED),((str(uuid.uuid4()),1),RETRY_BOOK_CHANGED)):
            with self.assertRaises(RetryRefused) as caught:self.s.repair_blocked_job('Audiobooks',*args,self.job_id)
            self.assertEqual(str(caught.exception),message)
        self.s.inventory.worker=ALIVE
        with self.assertRaises(RetryRefused) as caught:self.s.repair_blocked_job('Audiobooks',identity,1,self.job_id)
        self.assertEqual(str(caught.exception),REPAIR_SCANNING);self.s.inventory.worker=None
        self.assertEqual(self.children(),[])
        self.l.jobs._thread=ALIVE
        try:result=self.s.repair_blocked_job('Audiobooks',identity,1,self.job_id)
        finally:self.l.jobs._thread=None
        self.assertEqual((result['accepted'],result['queued_next'],result['position'],result['kind'],result['requeued']),(True,True,1,'repair',False),'accepted while a book converts')
        self.assertNotIn('audiobook_jobs',result);self.assertEqual(self.children(),[],'nothing is admitted on the request thread')
        # Between books the worker re-diagnoses and admits the child, which runs next.
        child=self.s._next_m4b_readmission()
        [row]=self.children();self.assertEqual(child,row['job_id']);self.assertEqual(m4b_repair.approved_repairs(json.loads(row['manifest'])),{'dangling_chapter_reference'})
        status=self.s.candidate_status(identity);self.assertEqual((status['readmission']['queued_next'],status['readmission']['kind']),(True,'repair'))
        with self.assertRaisesRegex(RetryRefused,'A retry request is already saved for this book'):
            self.s.repair_damaged_m4b(self.job_id,100)
        self.assertEqual([job['job_id'] for job in self.children()],[child],'duplicate repair admits no second child')


class RetryAllTests(Base):
    def wait(self,s):
        # The public terminal state precedes the worker's final SQLite receipt write.
        # Join this exact worker before assertions or temporary-catalog disposal.
        worker=s._retry_all_thread
        worker.join(10)
        self.assertFalse(worker.is_alive(),'Retry all worker did not close')
        self.assertNotEqual(s._retry_all_run['state'],'running')

    def test_the_whole_group_one_at_a_time_then_the_queue_starts_once(self):
        ids=[self.l.failed(name='b%d'%index)[0] for index in range(3)];self.l.failed(OUTSIDE,name='unsupported');self.passed(*ids)
        s=self.service();events=[];real=MergeService._request_m4b_readmission
        s.resume=Mock(side_effect=lambda **_:events.append('resume'))
        def request(service,job_id,kind):
            events.append(job_id)
            return {'accepted':False,'reason':'refused fixture'} if job_id==ids[1] else real(service,job_id,kind)
        with patch.object(MergeService,'_request_m4b_readmission',request),patch.object(MergeService,'_retry_preserved_m4b') as admit:
            run=s.retry_all();self.wait(s)
        admit.assert_not_called()
        self.assertEqual((run['total'],run['state']),(3,'running'),'the server group, not a visible page')
        self.assertEqual(events,ids+['resume'],'each book in order, then one queue start')
        self.assertEqual({key:s._retry_all_run[key] for key in ('state','total','done','queued','next','refused')},{'state':'done','total':3,'done':3,'queued':2,'next':2,'refused':1})
        summary=s.attention_summary();self.assertEqual([summary[job_id]['readmission']['position'] for job_id in (ids[0],ids[2])],[1,2],'click order')
        self.assertEqual(s.state()['retry_all']['queued'],2,'the count reaches the status payload')

    def test_one_run_at_a_time_and_gates(self):
        s=self.service()
        with self.assertRaises(RetryRefused) as caught:s.retry_all()
        self.assertEqual(str(caught.exception),RETRY_ALL_NONE)
        self.passed(self.l.failed()[0],self.l.failed(name='second')[0]);gate=threading.Event()
        with patch.object(MergeService,'_request_m4b_readmission',lambda service,job_id,kind:(gate.wait(10),{'accepted':True})[1]):
            s.retry_all()
            with self.assertRaises(RetryRefused) as caught:s.retry_all()
            self.assertEqual(str(caught.exception),RETRY_ALL_RUNNING)
            s.draining=True;gate.set();self.wait(s)
        self.assertEqual((s._retry_all_run['state'],s._retry_all_run['done']),('stopped',1),'Quit stops before the next book')
        s.resume.assert_not_called()
        s.draining=False;s.inventory.worker=ALIVE
        with self.assertRaises(RetryRefused) as caught:s.retry_all()
        self.assertEqual(str(caught.exception),RETRY_SCANNING)


class RevisionGuardTests(Base):
    """v0.16.10: a real Retry child and a real Repair child, admitted by the real proof routes, run through the real
    worker and the real revision guard (MergeService._guard). Until 0.16.10 the guard compared the job-only
    m4b_repair binding with the review's rebuild, so every such job stopped with "Source changed — review required"
    before any work. The review rebuild is the unchanged reviewed manifest (what build_manifest returns when nothing
    changed); a changed one must still stop the job."""
    def setUp(self):
        super().setUp()
        self.retry_parent,self.retry_manifest=self.l.failed(source=fixture(),name='retry')
        self.repair_parent,self.repair_manifest=self.l.failed(REFUSED,dangling(TEXT_SOURCE(),[3,2]),name='repair')
        self.s=self.service();self.s.reviews.build_manifest=self.rebuild;self.edited=set()
        self.ran=[];self.l.jobs.runner=self.runner;self.l.jobs.revision_guard=self.s._guard

    def rebuild(self,library,identity,revision,allow_existing_job=False,stop=None):
        frozen=next(m for m in (self.retry_manifest,self.repair_manifest) if m['candidate_id']==identity)
        fresh=copy.deepcopy(frozen);fresh['job_id']=str(uuid.uuid4())
        if identity in self.edited:fresh['metadata']['title']='Edited after admission'
        return fresh

    def runner(self,manifest,stop,checkpoint):
        self.ran.append(manifest['job_id']);raise ValueError('Fixture stops once the guard let it start')

    def children(self):
        retry=self.s._retry_preserved_m4b(self.l.row(self.retry_parent),100,in_worker=True)
        repair=self.s._repair_damaged_m4b(self.l.row(self.repair_parent),100,in_worker=True)
        self.assertTrue(retry['requeued'],retry);self.assertTrue(repair['requeued'],repair)
        for child in (retry['job_id'],repair['job_id']):self.assertIn('m4b_repair',json.loads(self.l.row(child)['manifest']),'a real child carries its binding')
        return retry['job_id'],repair['job_id']

    def work(self):
        self.l.jobs._stop.clear();self.l.jobs.resume();deadline=time.monotonic()+20
        while self.l.jobs._thread and self.l.jobs._thread.is_alive():
            if time.monotonic()>deadline:raise AssertionError('worker did not stop')
            time.sleep(.02)

    def test_retry_and_repair_children_pass_the_guard_and_start(self):
        retry,repair=self.children();self.work()
        self.assertEqual(sorted(self.ran),sorted([retry,repair]),'both children started: the guard passed')
        for child in (retry,repair):self.assertEqual(self.l.row(child)['reason'],'Fixture stops once the guard let it start')

    def test_a_review_changed_after_admission_still_stops_the_child(self):
        retry,repair=self.children();self.edited.add(self.retry_manifest['candidate_id']);self.work()
        self.assertEqual(self.ran,[repair],'positive control: the guard still compares the review')
        self.assertEqual((self.l.row(retry)['state'],self.l.row(retry)['reason']),('needs attention','Source changed — review required'))

    def test_children_stopped_by_the_old_guard_show_retry_and_repair_and_run(self):
        retry,repair=self.children()
        self.l.jobs.revision_guard=lambda manifest:False;self.work()  # the 0.16.9 guard refused every child
        for child in (retry,repair):self.assertEqual((self.l.row(child)['state'],self.l.row(child)['reason']),('needs attention','Source changed — review required'))
        summary=self.s.attention_summary()
        self.assertEqual((summary[retry]['group'],summary[retry]['retry']),('retry',{'allowed':True,'reason':''}))
        self.assertEqual((summary[repair]['group'],summary[repair]['repair']),('repair',{'allowed':True,'reason':''}))
        self.assertEqual([item['kind'] for item in summary[repair]['damage']],['dangling_chapter_reference'],'the approved repair, from its own binding')
        self.assertNotIn(self.retry_parent,summary);self.assertNotIn(self.repair_parent,summary)
        before=self.count()
        with self.assertRaises(RetryRefused):self.s.repair_blocked_job('Audiobooks',self.retry_manifest['candidate_id'],1,retry)  # Repair is only for a repair job
        self.assertTrue(self.s.retry_blocked_job('Audiobooks',self.retry_manifest['candidate_id'],1,retry)['queued_next'])
        self.assertTrue(self.s.repair_blocked_job('Audiobooks',self.repair_manifest['candidate_id'],1,repair)['queued_next'])
        self.assertEqual(self.count(),before,'requeued as themselves: no new job');self.assertEqual(json.loads(self.l.row(repair)['manifest'])['m4b_repair']['repairs'][0]['kind'],'dangling_chapter_reference')
        self.l.jobs.revision_guard=self.s._guard;self.work()
        self.assertEqual(sorted(self.ran),sorted([retry,repair]))

    def count(self):return self.l.count()


class HTTPTests(unittest.TestCase):
    setUp=test_blocked_retry.HTTPTests.setUp;call=test_blocked_retry.HTTPTests.call

    def test_repair_route(self):
        self.merge.repair_blocked_job=Mock(return_value={'requeued':True,'job_id':'c'})
        status,body,_=self.call(self.body,path='/api/audiobook/repair');self.assertEqual((status,body['requeued']),(202,True))
        self.merge.repair_blocked_job.assert_called_once_with('Audiobooks',self.body['id'],4,self.body['job_id'])
        self.merge.repair_blocked_job.side_effect=RetryRefused('This book cannot be repaired.')
        self.assertEqual(self.call(self.body,path='/api/audiobook/repair')[:2],(409,{'error':'This book cannot be repaired.'}))
        self.assertEqual(self.call(self.body|{'extra':1},path='/api/audiobook/repair')[0],400)
        self.inventory.worker=SimpleNamespace(is_alive=lambda:True)
        self.assertEqual(self.call(self.body,path='/api/audiobook/repair')[:2],(409,{'error':REPAIR_SCANNING,'code':'scanning'}))  # typed: the page waits for the scan (ruling 35)

    def test_keep_route(self):
        # v0.16.8 Keep files: same request shape and answers as Retry; nothing is queued or deleted.
        self.merge.keep_files=Mock(return_value={'job_id':self.body['job_id'],'kept':True})
        status,body,_=self.call(self.body,path='/api/audiobook/keep');self.assertEqual((status,body['kept']),(202,True))
        self.merge.keep_files.assert_called_once_with('Audiobooks',self.body['id'],4,self.body['job_id'])
        self.merge.keep_files.side_effect=RetryRefused("This book's status changed. Check the updated status above.")
        self.assertEqual(self.call(self.body,path='/api/audiobook/keep')[:2],(409,{'error':"This book's status changed. Check the updated status above."}))
        self.assertEqual(self.call(self.body|{'extra':1},path='/api/audiobook/keep')[0],400)
        self.assertEqual(self.call(self.body,token=False,path='/api/audiobook/keep')[0],403)
        self.assertEqual(self.merge.keep_files.call_count,2,'refused shapes and tokens never reach the service')

    def test_retry_all_route(self):
        self.merge.retry_all=Mock(return_value={'id':'r','state':'running','total':3,'done':0,'queued':0,'refused':0})
        status,body,_=self.call({'library':'Audiobooks'},path='/api/audiobook/retry-all')
        self.assertEqual((status,body['retry_all']['total']),(202,3));self.merge.retry_all.assert_called_once_with()
        for bad in ({'library':'Ebooks'},{'library':'Audiobooks','job_ids':[]},{}):
            self.assertEqual(self.call(bad,path='/api/audiobook/retry-all')[0],400)
        self.merge.retry_all.side_effect=RetryRefused(RETRY_ALL_RUNNING)
        self.assertEqual(self.call({'library':'Audiobooks'},path='/api/audiobook/retry-all')[:2],(409,{'error':RETRY_ALL_RUNNING}))
        self.inventory.worker=SimpleNamespace(is_alive=lambda:True)
        self.assertEqual(self.call({'library':'Audiobooks'},path='/api/audiobook/retry-all')[:2],(409,{'error':RETRY_SCANNING,'code':'scanning'}))  # typed: the page waits for the scan
        self.assertEqual(self.merge.retry_all.call_count,2)


    def test_selected_retry_uses_same_correlated_run(self):
        self.merge.retry_all=Mock(return_value={'id':'selection','state':'running','accepted':0})
        item={key:self.body[key] for key in ('id','revision','job_id')}|{'kind':'repair'}
        status,body,_=self.call({'library':'Audiobooks','items':[item]},path='/api/audiobook/retry-all')
        self.assertEqual((status,body['retry_all']['id']),(202,'selection'))
        self.merge.retry_all.assert_called_once_with([item])
    def test_selected_retry_refuses_duplicate_and_malformed_before_service(self):
        self.merge.retry_all=Mock()
        item={key:self.body[key] for key in ('id','revision','job_id')}|{'kind':'retry'}
        for items in ([],[item,item],[item|{'kind':'delete'}],[item|{'extra':'ignored?'}],[item|{'job_id':'not-a-uuid'}]):
            self.assertEqual(self.call({'library':'Audiobooks','items':items},path='/api/audiobook/retry-all')[0],400)
        self.merge.retry_all.assert_not_called()


if __name__=='__main__':unittest.main()

