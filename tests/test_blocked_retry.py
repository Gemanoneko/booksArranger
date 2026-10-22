"""v0.16.5 Retry for an audiobook job refused before any attempt started.

Private SQLite/Windows folder fixtures and HTTP handler doubles; no library, catalog copy or media tools.
"""
import base64,copy,hashlib,io,json,sys,tempfile,threading,time,unittest,uuid
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import audio_jobs
from audio_jobs import AudioJobs,RetryRefused,RETRY_FILES_PRESENT,RETRY_BOOK_CHANGED,RETRY_JOB_CHANGED,RETRY_REVIEW_CHANGED,RETRY_CLOSING,RETRY_SCANNING
from merge_service import MergeService
from scanner import connect
from working_lifecycle import WorkingLifecycle

AREA=Path(__file__).resolve().parents[1]/'scratch'/'blocked-retry-tests';AREA.mkdir(parents=True,exist_ok=True)
LEGACY='Working cleanup requires attention: Legacy attempt still contains working inputs; exact retirement review required before another snapshot'


class Queue:
    """A real AudioJobs ledger and WorkingLifecycle; the runner is a recorder that stops after admission."""
    def __init__(self,folder):
        self.base=Path(folder);self.db=self.base/'inventory.sqlite3';self.stage_root=self.base/'merge-cache'/'audio-staging';self.stage_root.mkdir(parents=True)
        self.guard_calls=[];self.guard=lambda manifest:(self.guard_calls.append(manifest),True)[1]
        self.runs=[];self.release=threading.Event();self.release.set()
        self.jobs=AudioJobs(self.db,self.runner,lambda manifest:self.guard(manifest),lambda record:True)
        self.life=WorkingLifecycle(self.db,self.stage_root)
        self.jobs.before_attempt=self.life.admit
        self.holds=[];self.jobs.on_working_hold=lambda:self.holds.append(1)
        with connect(self.db) as db:db.execute('CREATE TABLE IF NOT EXISTS book_groups(id TEXT PRIMARY KEY,revision INTEGER)')

    def runner(self,manifest,stop,checkpoint):
        self.runs.append((manifest['job_id'],manifest['attempt_id']));self.release.wait(10)
        stop.set();raise InterruptedError('Fixture stops after admission')

    def manifest(self,candidate=None,revision=1,**extra):
        candidate=candidate or str(uuid.uuid4())
        with connect(self.db) as db:db.execute('INSERT OR REPLACE INTO book_groups VALUES(?,?)',(candidate,revision))
        return {'job_id':str(uuid.uuid4()),'candidate_id':candidate,'candidate_revision':revision,'sources':[{'path':str(self.base/'library'/'01.mp3'),'sha256':'a'*64,'fingerprint':{'size':3,'modified':1}}],
                'metadata':{'title':'Fixture'},'destination':str(self.base/'library'/'Fixture.m4b'),'profile':'fixture','evidence':{},'cover':{},'cleanup_policy':{'enabled':False},**extra}

    def blocked(self,manifest=None,leftover=True):
        """The 644da7fc shape: an interrupted legacy attempt whose folder still had files, so the worker refused it.

        leftover=False then removes the file, as happened by hand on 2026-10-17.
        """
        manifest=manifest or self.manifest();job_id=self.jobs.enqueue(manifest);attempt=str(uuid.uuid4())
        journal={'attempt_id':attempt,'history':[{'stage':'checking sources','at':'2026-10-16T23:58:00+00:00','details':None}]}
        self.jobs._update(job_id,state='pending',stage='queued',attempt_id=attempt,journal=json.dumps(journal),reason='Interrupted book restarts on explicit resume')
        folder=self.stage_root/job_id/attempt;folder.mkdir(parents=True);(folder/'source00000.mp3').write_bytes(b'legacy working input')
        self.jobs.resume();self.wait()
        row=self.row(job_id)
        assert row['state']=='needs attention' and row['reason'].startswith('Working cleanup requires attention: Legacy attempt'),row
        self.jobs._stop.clear()
        if not leftover:(folder/'source00000.mp3').unlink()  # Sergei cleared the old folder by hand.
        return job_id,attempt,folder

    def row(self,job_id):
        return self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))[0]

    def wait(self):
        deadline=time.monotonic()+20
        while self.jobs._thread and self.jobs._thread.is_alive():
            if time.monotonic()>deadline:raise AssertionError('worker did not stop')
            time.sleep(.02)

    def statuses(self):return self.jobs.retry_statuses(self.life.admission_clear)

    def retry(self,job_id,revision=1):
        manifest=json.loads(self.row(job_id)['manifest'])
        return self.jobs.retry_admission_hold(job_id,manifest['candidate_id'],revision,self.life.admission_clear)


class Base(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.q=Queue(self.temp.name)
    def tearDown(self):
        self.q.release.set();self.q.jobs.close();self.temp.cleanup()
    def assert_refused(self,job_id,message,call):
        before=self.q.row(job_id)
        with self.assertRaises(RetryRefused) as caught:call()
        self.assertEqual(str(caught.exception),message)
        self.assertEqual(self.q.row(job_id),before,'a refused Retry leaves the whole row byte-identical')


class EndToEndTests(Base):
    def test_refused_start_becomes_retryable_once_the_files_are_gone_and_runs_a_new_attempt(self):
        job_id,attempt,folder=self.q.blocked()
        self.assertEqual(len(self.q.holds),1,'the existing hold path stopped the queue')
        held=self.q.row(job_id);self.assertNotIn('failure',json.loads(held['journal']))
        self.assertEqual(self.q.statuses(),{job_id:{'allowed':False,'reason':RETRY_FILES_PRESENT}})
        self.assert_refused(job_id,RETRY_FILES_PRESENT,lambda:self.q.retry(job_id))
        (folder/'source00000.mp3').unlink()
        self.assertEqual(self.q.statuses(),{job_id:{'allowed':True,'reason':''}},'the next status read allows Retry')
        self.assertEqual(self.q.retry(job_id),{'job_id':job_id,'requeued':True})
        queued=self.q.row(job_id)
        self.assertEqual((queued['state'],queued['stage'],queued['attempt_id'],queued['journal'],queued['manifest']),('pending','queued',attempt,held['journal'],held['manifest']))
        self.assertEqual(self.q.statuses(),{},'a queued job has no Retry data')
        self.q.jobs.resume();self.q.wait()
        self.assertEqual(len(self.q.runs),1);self.assertEqual(self.q.runs[0][0],job_id);self.assertNotEqual(self.q.runs[0][1],attempt,'a new attempt id')
        with connect(self.q.db) as db:history=[tuple(r) for r in db.execute('SELECT job_id,attempt_id,record FROM audio_failure_history')]
        self.assertEqual(history,[(job_id,attempt,held['journal'])],'the old journal is archived exactly once')
        self.assertEqual(self.q.row(job_id)['attempt_id'],self.q.runs[0][1])

    def test_retry_never_requires_an_idle_queue_and_starts_no_second_worker(self):
        job_id,attempt,folder=self.q.blocked(leftover=False)
        other=self.q.jobs.enqueue(self.q.manifest());self.q.release.clear()
        self.q.jobs.resume()
        deadline=time.monotonic()+10
        while not self.q.runs and time.monotonic()<deadline:time.sleep(.02)
        self.assertEqual(self.q.runs[0][0],other,'another book is converting')
        self.assertEqual(self.q.retry(job_id)['requeued'],True)
        workers=[t for t in threading.enumerate() if t.name=='BooksArrangerAudioJobs'];self.assertEqual(len(workers),1)
        self.q.jobs._stop.clear()
        # The fixture runner stops the queue after each book; let the current one finish, then resume normally.
        self.q.release.set();self.q.wait();self.q.jobs._stop.clear();self.q.jobs.resume();self.q.wait()
        self.assertEqual([run[0] for run in self.q.runs],[other,job_id],'the retried book follows the current one')


class EligibilityTests(Base):
    def hidden(self,job_id):
        self.assertNotIn(job_id,self.q.statuses())
        self.assert_refused(job_id,RETRY_BOOK_CHANGED,lambda:self.q.retry(job_id))

    def test_runtime_failures_published_rows_and_tampered_rows_are_hidden(self):
        cases={
            'retryable failure':lambda row:{'journal':json.dumps(dict(json.loads(row['journal']),failure={'retryable':True,'at':0,'stage':'creating'}))},
            'classified failure':lambda row:{'journal':json.dumps(dict(json.loads(row['journal']),failure={'retryable':False,'at':0,'stage':'creating'}))},
            'output recorded':lambda row:{'output':json.dumps({'job_id':row['job_id']})},
            'publication intent':lambda row:{'journal':json.dumps(dict(json.loads(row['journal']),publication_intent={'job_id':row['job_id']}))},
            'manifest hash mismatch':lambda row:{'manifest_hash':'0'*64},
            'not needs attention':lambda row:{'state':'pending'},
        }
        for name,change in cases.items():
            with self.subTest(case=name):
                job_id,attempt,folder=self.q.blocked(leftover=False);row=self.q.row(job_id)
                self.assertIn(job_id,self.q.statuses(),'positive control: the unchanged shape is eligible')
                self.q.jobs._update(job_id,**change(row));self.hidden(job_id)

    def test_replacement_repair_and_superseded_jobs_are_hidden(self):
        job_id,_,_=self.q.blocked(self.q.manifest(replacement_id=str(uuid.uuid4())),leftover=False);self.hidden(job_id)
        job_id,_,_=self.q.blocked(self.q.manifest(m4b_repair={'parent_job_id':str(uuid.uuid4())}),leftover=False);self.hidden(job_id)
        parent,_,_=self.q.blocked(leftover=False)
        with connect(self.q.db) as db:db.execute('INSERT INTO audio_repair_admissions VALUES(?,?,?,?)',(parent,str(uuid.uuid4()),'{}','2026-10-17'))
        self.hidden(parent)
        older,_,_=self.q.blocked(leftover=False);candidate=json.loads(self.q.row(older)['manifest'])['candidate_id']
        newer=self.q.jobs.enqueue(self.q.manifest(candidate,metadata={'title':'Newer'}))
        self.assertNotEqual(newer,older);self.hidden(older)

    def test_conflicting_archived_attempt_is_hidden(self):
        job_id,attempt,_=self.q.blocked(leftover=False)
        with connect(self.q.db) as db:
            db.execute('CREATE TABLE IF NOT EXISTS audio_failure_history(job_id TEXT,attempt_id TEXT,record TEXT,at REAL,PRIMARY KEY(job_id,attempt_id))')
            db.execute('INSERT INTO audio_failure_history VALUES(?,?,?,?)',(job_id,attempt,'{"different":true}',0))
        self.hidden(job_id)

    def test_unretired_receipt_owned_attempt_disables_retry(self):
        job_id,_,_=self.q.blocked(leftover=False)
        with connect(self.q.db) as db:db.execute('INSERT INTO working_attempts VALUES(?,?,?,?,?,?,?,?)',(job_id,str(uuid.uuid4()),'{}','x','{}','closed','','2026-10-17'))
        self.assertEqual(self.q.statuses(),{job_id:{'allowed':False,'reason':RETRY_FILES_PRESENT}})
        self.assert_refused(job_id,RETRY_FILES_PRESENT,lambda:self.q.retry(job_id))
        with connect(self.q.db) as db:db.execute("UPDATE working_attempts SET state='retired' WHERE job_id=?",(job_id,))
        self.assertEqual(self.q.statuses()[job_id]['allowed'],True,'positive control: a retired attempt clears it')


class PressTimeTests(Base):
    def test_stale_screen_guard_drain_and_close_refuse_with_the_row_unchanged(self):
        closing,_,_=self.q.blocked(leftover=False)
        job_id,_,_=self.q.blocked(leftover=False);manifest=json.loads(self.q.row(job_id)['manifest'])
        self.assert_refused(job_id,RETRY_BOOK_CHANGED,lambda:self.q.jobs.retry_admission_hold(job_id,manifest['candidate_id'],2,self.q.life.admission_clear))
        self.assert_refused(job_id,RETRY_BOOK_CHANGED,lambda:self.q.jobs.retry_admission_hold(job_id,str(uuid.uuid4()),1,self.q.life.admission_clear))
        self.assert_refused(job_id,RETRY_BOOK_CHANGED,lambda:self.q.jobs.retry_admission_hold(str(uuid.uuid4()),manifest['candidate_id'],1,self.q.life.admission_clear))
        with connect(self.q.db) as db:db.execute('UPDATE book_groups SET revision=2 WHERE id=?',(manifest['candidate_id'],))
        self.assert_refused(job_id,RETRY_BOOK_CHANGED,lambda:self.q.retry(job_id))
        with connect(self.q.db) as db:db.execute('UPDATE book_groups SET revision=1 WHERE id=?',(manifest['candidate_id'],))
        self.q.guard=lambda manifest:False
        self.assert_refused(job_id,RETRY_REVIEW_CHANGED,lambda:self.q.retry(job_id))
        def broken(manifest):raise OSError('source unavailable')
        self.q.guard=broken;self.assert_refused(job_id,RETRY_REVIEW_CHANGED,lambda:self.q.retry(job_id))
        self.q.guard=lambda manifest:True
        self.q.jobs._drain.set();self.assert_refused(job_id,RETRY_CLOSING,lambda:self.q.retry(job_id));self.q.jobs._drain.clear()
        self.assertEqual(self.q.retry(job_id)['requeued'],True,'positive control: the same row is accepted once nothing blocks it')
        self.q.jobs.close();self.assert_refused(closing,RETRY_CLOSING,lambda:self.q.retry(closing))

    def test_row_changed_between_check_and_requeue_is_refused(self):
        job_id,_,_=self.q.blocked(leftover=False)
        def racing(manifest):
            self.q.jobs._update(job_id,reason='Changed by another writer');return True
        self.q.guard=racing
        with self.assertRaises(RetryRefused) as caught:self.q.retry(job_id)
        self.assertEqual(str(caught.exception),RETRY_JOB_CHANGED)
        row=self.q.row(job_id);self.assertEqual((row['state'],row['reason']),('needs attention','Changed by another writer'))

    def test_guard_runs_outside_the_queue_lock(self):
        job_id,_,_=self.q.blocked(leftover=False);free=[]
        def probe(manifest):
            acquired=[]
            thread=threading.Thread(target=lambda:acquired.append(self.q.jobs._lock.acquire(timeout=1) and (self.q.jobs._lock.release() or True)))
            thread.start();thread.join();free.append(acquired==[True]);return True
        self.q.guard=probe;self.q.retry(job_id)
        self.assertEqual(free,[True],'Pause and the running book are not blocked while sources are re-read')


class StatusCostTests(Base):
    def test_status_read_never_runs_the_guard_and_reads_once(self):
        job_id,_,_=self.q.blocked(leftover=False);self.q.guard_calls.clear()
        opened=[];original=self.q.jobs._db
        def counted():opened.append(1);return original()
        clear=Mock(side_effect=self.q.life.admission_clear)
        with patch.object(self.q.jobs,'_db',counted):statuses=self.q.jobs.retry_statuses(clear)
        self.assertEqual(statuses[job_id]['allowed'],True);self.assertEqual(len(opened),1);self.assertEqual(clear.call_count,1)
        self.assertEqual(self.q.guard_calls,[],'no revision guard (and so no source hashing) per poll')
        self.q.jobs._update(job_id,state='completed',output=json.dumps({'job_id':job_id}))
        opened.clear();clear.reset_mock()
        with patch.object(self.q.jobs,'_db',counted):self.assertEqual(self.q.jobs.retry_statuses(clear),{})
        self.assertEqual(len(opened),1);clear.assert_not_called()


class ServiceTests(Base):
    def service(self):
        s=MergeService.__new__(MergeService);s.jobs=self.q.jobs;s.working=self.q.life;s.operation_lock=threading.RLock()
        s.inventory=SimpleNamespace(database=self.q.db,roots={'Audiobooks':str(self.q.base/'library')},worker=None,group_lock=threading.RLock());s.reviews=SimpleNamespace(lock=threading.RLock())
        s.draining=False
        s.cleanup=SimpleNamespace(status=lambda job_id=None:None)
        s.resume=Mock(return_value={'state':'Running','queued':1});s._resume_later=Mock()
        return s

    def test_operation_requeues_and_resumes(self):
        job_id,_,_=self.q.blocked(leftover=False);s=self.service();manifest=json.loads(self.q.row(job_id)['manifest'])
        status=s.candidate_status(manifest['candidate_id']);self.assertEqual(status['retry'],{'allowed':True,'reason':''})
        self.assertEqual(status['state'],'Output needs attention');self.assertTrue(status['reason'].startswith('Working cleanup requires attention'))
        result=s.retry_blocked_job('Audiobooks',manifest['candidate_id'],1,job_id)
        # v0.16.8: the press answers at once (no status in the reply), the job runs next, the queue starts on its own thread.
        self.assertEqual({key:result[key] for key in ('job_id','requeued','queued_next','position','kind')},{'job_id':job_id,'requeued':True,'queued_next':True,'position':1,'kind':'retry'})
        self.assertNotIn('audiobook_jobs',result);s._resume_later.assert_called_once_with();s.resume.assert_not_called()
        self.assertNotIn('retry',s.candidate_status(manifest['candidate_id']))

    def test_real_single_and_bulk_enqueue_remain_queued_across_polls_during_current_book(self):
        first,_,_=self.q.blocked(leftover=False);second,_,_=self.q.blocked(leftover=False)
        current=self.q.jobs.enqueue(self.q.manifest());self.q.release.clear();self.q.jobs.resume()
        deadline=time.monotonic()+5
        while not self.q.runs and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(self.q.runs[0][0],current)
        s=self.service()
        s.attention_summary=lambda job_ids=None,retry=True:self.q.jobs.attention_summary(self.q.life.admission_clear,job_ids=job_ids,retry=retry)
        m=json.loads(self.q.row(first)['manifest']);answer=s.retry_blocked_job('Audiobooks',m['candidate_id'],1,first)
        self.assertTrue(answer['queued_next']);self.assertEqual(answer['position'],1)
        bulk=s.retry_all();s._retry_all_thread.join(5);self.assertFalse(s._retry_all_thread.is_alive())
        self.assertEqual((s._retry_all_run['queued'],s._retry_all_run['refused']),(1,0),s._retry_all_run)
        for _ in range(10):
            for index,job in enumerate((first,second),1):
                manifest=json.loads(self.q.row(job)['manifest']);status=s.candidate_status(manifest['candidate_id'])
                self.assertEqual(status['readmission']['queued_next'],True)
                self.assertEqual(status['readmission']['position'],index)
                self.assertNotIn('retry',status,'accepted requests cannot become retryable on a fresh poll')
        self.assertEqual(len(self.q.runs),1,'the current book remains the only running attempt')
        with connect(self.q.db) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM m4b_readmissions').fetchone()[0],2)
        self.assertEqual(s.retry_blocked_job('Audiobooks',m['candidate_id'],1,first)['position'],1)

    def test_repeated_presses_are_one_request_answered_alike_and_never_wait_on_the_review_lock(self):
        # v0.16.12 (Sergei, live): every Retry reports its place; a repeated press changes nothing and is not refused;
        # the press never waits for the review lock (held while a book's sources are re-read).
        job_id,_,_=self.q.blocked(leftover=False);s=self.service();manifest=json.loads(self.q.row(job_id)['manifest'])
        held=threading.Event();release=threading.Event()
        def hold():
            with s.reviews.lock,s.inventory.group_lock:held.set();release.wait(10)
        holder=threading.Thread(target=hold);holder.start();self.assertTrue(held.wait(5))
        try:
            started=time.monotonic();first=s.retry_blocked_job('Audiobooks',manifest['candidate_id'],1,job_id)
            self.assertLess(time.monotonic()-started,3,'accepted at once while the review lock is held')
        finally:release.set();holder.join(10)
        again=s.retry_blocked_job('Audiobooks',manifest['candidate_id'],1,job_id)
        self.assertEqual((first['queued_next'],first['position']),(True,1));self.assertEqual((again['accepted'],again['queued_next'],again['position']),(True,True,1))
        with connect(self.q.db) as db:
            ledger=[tuple(r) for r in db.execute('SELECT parent_job_id,seq,state,child_job_id FROM m4b_readmissions')]
            jobs=db.execute('SELECT count(*) FROM audio_jobs').fetchone()[0]
        self.assertEqual(len(ledger),1,'one queue entry');self.assertEqual(jobs,1,'no duplicate job')
        self.assertEqual(s._resume_later.call_count,1,'the repeat starts nothing')
        self.assertEqual(self.q.row(job_id)['state'],'pending')

    def test_operation_refuses_while_scanning_or_quitting_without_resuming(self):
        job_id,_,_=self.q.blocked(leftover=False);s=self.service();manifest=json.loads(self.q.row(job_id)['manifest'])
        s.inventory.worker=SimpleNamespace(is_alive=lambda:True)
        self.assert_refused(job_id,RETRY_SCANNING,lambda:s.retry_blocked_job('Audiobooks',manifest['candidate_id'],1,job_id))
        s.inventory.worker=None;s.draining=True
        self.assert_refused(job_id,RETRY_CLOSING,lambda:s.retry_blocked_job('Audiobooks',manifest['candidate_id'],1,job_id))
        s.resume.assert_not_called()

    def test_service_without_working_ledger_reports_no_retry(self):
        s=MergeService.__new__(MergeService);s.jobs=self.q.jobs
        self.assertEqual(s.retry_statuses(),{})


class PageTests(unittest.TestCase):
    def test_page_attaches_retry_once_per_page(self):
        from scanner import Inventory
        from review_backend import CandidateReviewService
        with tempfile.TemporaryDirectory(dir=AREA) as folder:
            base=Path(folder);audio=base/'audio';(audio/'Book').mkdir(parents=True);(audio/'Book'/'01.mp3').write_bytes(b'private fixture')
            roots={'Audiobooks':str(audio),'Podcasts':str(base/'podcasts'),'Ebooks':str(base/'ebooks')}
            inventory=Inventory(base/'catalog.sqlite3',roots,lambda path,kind,stop:{'title':'Book','tags':{'album':'Book'},'probe':{'format':{'duration':'1.0'}},'method':'fixture'})
            inventory.launch('Audiobooks');inventory.worker.join(5)
            service=CandidateReviewService(inventory,base/'covers');identity=service.page()['rows'][0]['id']
            job={'job_id':'job-a','state':'needs attention','stage':'queued','reason':LEGACY,'manifest':{'candidate_id':identity,'cleanup_policy':{'enabled':True}}}
            retry=Mock(side_effect=lambda job_ids=None,retry=True:{'job-a':{'group':'retry','cause':'files','originals_untouched':True,'retry':{'allowed':True,'reason':''}}} if retry and 'job-a' in (job_ids or ['job-a']) else {})
            service.jobs=SimpleNamespace(progress_books=lambda:{'converted_ids':set()},attention_summary=retry,
                jobs=SimpleNamespace(status=lambda:{'jobs':[job]}),cleanup=SimpleNamespace(status=lambda _id:None,root=base/'recovery'))
            row=service.page()['rows'][0]
            self.assertEqual(row['creation']['job']['retry'],{'allowed':True,'reason':''});self.assertEqual(row['creation']['job']['reason'],LEGACY)
            retry.assert_called_once_with(['job-a'])  # v0.16.7: only for the shown page's needs-attention jobs
            self.assertEqual(row['creation']['job']['attention'],{'group':'retry','cause':'files','originals_untouched':True})
            retry.side_effect=lambda job_ids=None,retry=True:{};self.assertNotIn('retry',service.page()['rows'][0]['creation']['job'])


class HTTPTests(unittest.TestCase):
    """Route contract through the real handler; the service is a double."""
    def setUp(self):
        from web_server import BrowserServer
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
        self.inventory=SimpleNamespace(database=Path(self.temp.name)/'catalog.sqlite3',roots={'Audiobooks':'fixture-audio','Podcasts':'fixture-podcasts','Ebooks':'fixture-ebooks'},worker=None,stop_event=threading.Event(),status=lambda lib:{'state':'completed'},launch=Mock(),stop=Mock())
        server=BrowserServer.__new__(BrowserServer)
        server.inventory=self.inventory;server.server_address=('127.0.0.1',5211);server.server_port=5211;server.token='fixture-token';server.instance='fixture';server.active_library=None
        server.closing=False;server.control_lock=threading.Lock();server.control_condition=threading.Condition(server.control_lock);server.merge_admissions=0
        self.merge=SimpleNamespace(reviews=SimpleNamespace(),retry_blocked_job=Mock(return_value={'job_id':'j','requeued':True,'audiobook_jobs':{'state':'Running'}}),state=Mock(return_value={'state':'Paused'}))
        server.merge=self.merge;self.server=server
        self.body={'library':'Audiobooks','id':str(uuid.uuid4()),'revision':4,'job_id':str(uuid.uuid4())}

    def call(self,data,token=True,path='/api/audiobook/retry',raw=None):
        from web_server import Handler
        h=Handler.__new__(Handler);h.server=self.server;h.path=path
        h.headers=Message();h.headers['Host']='127.0.0.1:5211'
        if token:h.headers['X-Books-Token']=self.server.token
        payload=raw if raw is not None else json.dumps(data).encode()
        h.headers['Content-Type']='application/json';h.headers['Content-Length']=str(len(payload));h.rfile=io.BytesIO(payload)
        h.result=None;h.response=lambda status,body,content_type='application/json':setattr(h,'result',(status,body,content_type))
        h.do_POST();return h.result

    def test_success_and_exact_arguments(self):
        status,body,_=self.call(self.body);self.assertEqual(status,202);self.assertEqual(body['requeued'],True)
        self.merge.retry_blocked_job.assert_called_once_with('Audiobooks',self.body['id'],4,self.body['job_id'])
        self.assertEqual(self.server.merge_admissions,0)

    def test_malformed_requests_are_400_and_never_reach_the_service(self):
        bad=[{k:v for k,v in self.body.items() if k!='job_id'},self.body|{'path':'Z:/x'},self.body|{'job_id':'../x'},self.body|{'id':'not-a-uuid'},self.body|{'revision':True},self.body|{'revision':0},self.body|{'library':'Ebooks'},self.body|{'job_id':self.body['job_id'].upper()}]
        for data in bad:
            with self.subTest(data=data):self.assertEqual(self.call(data)[0],400)
        self.assertEqual(self.call(self.body,path='/api/audiobook/retry?x=1')[0],400)
        self.merge.retry_blocked_job.assert_not_called()

    def test_refusal_is_409_with_the_message(self):
        self.merge.retry_blocked_job.side_effect=RetryRefused(RETRY_FILES_PRESENT)
        self.assertEqual(self.call(self.body)[:2],(409,{'error':RETRY_FILES_PRESENT}))

    def test_scan_closing_and_token_gates(self):
        self.inventory.worker=SimpleNamespace(is_alive=lambda:True)
        self.assertEqual(self.call(self.body)[:2],(409,{'error':RETRY_SCANNING}))
        self.inventory.worker=None;self.server.closing=True
        self.assertEqual(self.call(self.body)[0],409);self.server.closing=False
        self.assertEqual(self.call(self.body,token=False)[0],403)
        self.merge.retry_blocked_job.assert_not_called()


class CopyTests(unittest.TestCase):
    def test_retry_strings_meet_the_copy_standard(self):
        for text in (RETRY_FILES_PRESENT,RETRY_BOOK_CHANGED,RETRY_JOB_CHANGED,RETRY_REVIEW_CHANGED,RETRY_CLOSING,RETRY_SCANNING,audio_jobs.RETRY_QUEUED):
            with self.subTest(text=text):
                self.assertLessEqual(len(text),90);self.assertTrue(text[0].isupper());self.assertTrue(text.endswith('.'))
                self.assertLessEqual(text.count('. '),1,'at most two sentences')
                for term in ('job id','manifest','ownership','disposal','previously','no longer','legacy','receipt','refresh'):self.assertNotIn(term,text.lower())


if __name__=='__main__':unittest.main()
