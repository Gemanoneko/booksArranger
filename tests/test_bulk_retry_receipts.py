"""Retry submission receipts versus actual jobs. In-memory only; execution awaits approved QA route."""
import contextlib, json, sqlite3, sys, threading, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import m4b_readmission as requests
from merge_service import MergeService
from audio_jobs import AudioJobs

class BulkReceiptTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,state TEXT,reason TEXT)')
        requests.ensure(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    @contextlib.contextmanager
    def connection(self):
        try:yield self.db;self.db.commit()
        except BaseException:self.db.rollback();raise
    def request(self,parent='parent'):
        self.db.execute('INSERT INTO audio_jobs VALUES(?,?,?)',(parent,'needs attention','old failure'));self.db.commit()
        requests.request(self.db,parent,'retry',1);self.db.commit()
    def test_accepted_request_is_not_queued_job(self):
        self.request();p=requests.target_progress(self.db,['parent'])
        self.assertEqual(p['counts'],dict(waiting=1,checking=0,queued=0,running=0,completed=0,stopped=0))
        self.assertIsNone(p['targets'][0]['child_job_id'])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM audio_jobs WHERE state='pending'").fetchone()[0],0)
    def test_same_target_moves_through_real_child_states(self):
        self.request();self.db.execute("INSERT INTO audio_jobs VALUES('child','pending','')")
        self.db.execute("UPDATE m4b_readmissions SET state='admitted',child_job_id='child'")
        for saved,expected in [('pending','queued'),('running','running'),('completed','completed'),('needs attention','stopped')]:
            self.db.execute('UPDATE audio_jobs SET state=? WHERE job_id=?',(saved,'child'))
            p=requests.target_progress(self.db,['parent']);self.assertEqual(p['counts'][expected],1);self.assertEqual(sum(p['counts'].values()),1)
    def test_checking_is_current_worker_only(self):
        self.request();self.assertEqual(requests.target_progress(self.db,['parent'],'parent')['counts']['checking'],1)
        self.assertEqual(requests.target_progress(self.db,['parent'],'other')['counts']['waiting'],1)
    def test_scan_deferral_keeps_request_and_reason(self):
        self.request();events=[]
        self.assertIsNone(requests.next_job(self.connection,lambda *_:dict(defer=True,reason='Scan still running'),2,events.append))
        self.assertEqual(events[-1]['state'],'waiting');self.assertEqual(requests.pending_count(self.db),1)
        self.assertEqual(requests.describe(self.db,'parent')['waiting_reason'],'Scan still running')
        self.assertIsNone(self.db.execute('SELECT child_job_id FROM m4b_readmissions').fetchone()[0])
    def test_start_failure_is_durable_without_admission(self):
        self.request();requests.record_waiting(self.db,'database is locked');self.db.commit()
        self.assertEqual(requests.describe(self.db,'parent')['waiting_reason'],'database is locked')
        self.assertEqual(requests.target_progress(self.db,['parent'])['targets'][0]['reason'],'database is locked')
        self.assertEqual(requests.pending_count(self.db),1)
    def test_worker_admission_rejection_keeps_typed_failure(self):
        self.request();requests.next_job(self.connection,lambda *_:dict(requeued=False,reason='Review changed',cause='unknown'),2)
        p=requests.target_progress(self.db,['parent']);self.assertEqual(p['counts']['stopped'],1)
        self.assertEqual(p['targets'][0]['reason'],'Review changed');self.assertEqual(requests.pending_count(self.db),0)
    def test_latest_all_or_selected_replaces_previous_receipt(self):
        for id,stamp,mode in [('all','1','all'),('selected','2','selected')]:requests.save_bulk(self.db,dict(id=id,created=stamp,mode=mode,accepted_ids=[]))
        self.assertEqual(requests.latest_bulk(self.db)['id'],'selected')
    def test_priority_only_work_is_unfinished(self):
        self.request();queue=AudioJobs.__new__(AudioJobs);queue._db=self.connection
        self.assertTrue(queue.has_unfinished())
    def test_bulk_start_failure_is_not_swallowed_or_called_queued(self):
        service=MergeService.__new__(MergeService);service.draining=False
        service._retry_one=Mock(return_value='next');service._save_bulk_receipt=Mock(return_value=True)
        service.resume=Mock(side_effect=RuntimeError('actual start failure'))
        run=dict(start_generation=0,state='running',total=1,done=0,accepted=0,queued=0,next=0,refused=0,accepted_ids=[])
        service._retry_all_work(run,[dict(job_id='parent',kind='retry')],threading.Event())
        self.assertEqual(run['accepted'],1);self.assertEqual(run['start_outcome'],dict(state='blocked',reason='actual start failure'))
        self.assertEqual(run['state'],'done');self.assertEqual(service._save_bulk_receipt.call_count,2)
    def test_pause_does_not_resume_accepted_requests(self):
        service=MergeService.__new__(MergeService);service.draining=False
        stop=threading.Event()
        def accept(*_,**kwargs):stop.set();return 'next'
        service._retry_one=accept;service._save_bulk_receipt=Mock(return_value=True);service.resume=Mock()
        run=dict(start_generation=0,state='running',total=1,done=0,accepted=0,queued=0,next=0,refused=0,accepted_ids=[])
        service._retry_all_work(run,[dict(job_id='parent')],stop)
        service.resume.assert_not_called();self.assertEqual(run['start_outcome']['state'],'paused')

if __name__=='__main__':unittest.main()
