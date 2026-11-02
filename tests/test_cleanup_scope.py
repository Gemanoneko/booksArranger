"""Finite historical admission must never resume unrelated encoding/cleanup."""
from pathlib import Path
import sys,threading,unittest
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from merge_service import MergeService

class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.service=MergeService.__new__(MergeService);self.service.operation_lock=threading.RLock()
        self.service.inventory=SimpleNamespace(worker=None)
        self.service.jobs=SimpleNamespace(_thread=None,status=Mock(return_value={'jobs':[]}),resume=Mock())
        self.service.cleanup=SimpleNamespace(thread=None,status=Mock(return_value=[]),resume=Mock())
        self.service.enroll_cleanup=Mock(return_value={'cleanup_id':'owned'})
    def test_pending_audio_rejected_without_any_resume(self):
        self.service.jobs.status.return_value={'jobs':[{'state':'pending'}]}
        with self.assertRaisesRegex(ValueError,'queued audiobook'):self.service.start_historical_cleanup('approved')
        self.service.enroll_cleanup.assert_not_called();self.service.jobs.resume.assert_not_called();self.service.cleanup.resume.assert_not_called()
    def test_unrelated_paused_cleanup_rejected(self):
        self.service.cleanup.status.return_value=[{'job_id':'other','state':'paused'}]
        with self.assertRaisesRegex(ValueError,'Unrelated pending'):self.service.start_historical_cleanup('approved')
        self.service.enroll_cleanup.assert_not_called()
    def test_only_exact_enrolled_identity_and_no_audio_continuation(self):
        self.service.start_historical_cleanup('approved')
        # Since the start fence, the resume also carries the press's admission check and generation token (audit M1:
        # this suite was outside the gate, so the old expected call went stale unnoticed).
        self.service.cleanup.resume.assert_called_once()
        args,kwargs=self.service.cleanup.resume.call_args
        self.assertEqual((args,set(kwargs)),((['owned'],),{'follow_audio','admission_check','admission_token'}))
        self.assertIs(kwargs['follow_audio'],False);self.assertTrue(kwargs['admission_check'](),'the press that started it is still current')
        self.service.jobs.resume.assert_not_called()
    def test_scan_and_running_work_rejected(self):
        self.service.inventory.worker=SimpleNamespace(is_alive=lambda:True)
        with self.assertRaises(ValueError):self.service.start_historical_cleanup('approved')
        self.service.inventory.worker=None;self.service.cleanup.thread=SimpleNamespace(is_alive=lambda:True)
        with self.assertRaisesRegex(ValueError,'become idle'):self.service.start_historical_cleanup('approved')
    def test_admission_is_under_shared_operation_lock(self):
        observed=[]
        self.service.enroll_cleanup.side_effect=lambda *a,**k:(observed.append(self.service.operation_lock._is_owned()) or {'cleanup_id':'owned'})
        self.service.start_historical_cleanup('approved');self.assertEqual(observed,[True])

if __name__=='__main__':unittest.main()

class IdentityCleanupScopeTests(unittest.TestCase):
    def test_exact_scope_queue_shape_and_no_conversion_continuation(self):
        import json,uuid
        from web_server import Handler,BrowserServer
        def service():
            base=ScopeTests();base.setUp();s=base.service;s.draining=False;s._reacquire_admission=Mock();s.reviews=SimpleNamespace(_row=Mock(return_value={'revision':4}))
            s.jobs._rows=Mock(return_value=[{'state':'completed','manifest':json.dumps({'candidate_id':'book'})}])
            s.cleanup._rows=Mock(return_value=[{'id':'cleanup','job_id':'job'}]);s.cleanup.identity_retry=Mock(return_value={'allowed':True,'running':False});return s
        s=service();answer=s.retry_source_cleanup('Audiobooks','book',4,'job','cleanup');self.assertTrue(answer['accepted']);self.assertFalse(answer['requeued'])
        args,kw=s.cleanup.resume.call_args;self.assertEqual(args,(['cleanup'],));self.assertFalse(kw['follow_audio']);self.assertEqual(kw['identity_retry'],'cleanup');s.jobs.resume.assert_not_called();s.enroll_cleanup.assert_not_called()
        for change in ('revision','job','enrollment','hold','scan'):
            with self.subTest(change=change):
                s=service()
                if change=='revision':s.reviews._row.return_value={'revision':5}
                elif change=='job':s.jobs._rows.return_value=[{'state':'pending','manifest':json.dumps({'candidate_id':'book'})}]
                elif change=='enrollment':s.cleanup._rows.return_value=[]
                elif change=='hold':s.cleanup.identity_retry.return_value=None
                else:s.inventory.worker=SimpleNamespace(is_alive=lambda:True)
                with self.assertRaises(ValueError):s.retry_source_cleanup('Audiobooks','book',4,'job','cleanup')
                s.cleanup.resume.assert_not_called();s.jobs.resume.assert_not_called();s.enroll_cleanup.assert_not_called()
        candidate,job,cleanup=[str(uuid.uuid4()) for _ in range(3)]
        h=Handler.__new__(Handler);h.server=SimpleNamespace(inventory=SimpleNamespace(roots={'Audiobooks':'private-fixture'}),actions=SimpleNamespace(enqueue=Mock(return_value={'queued':True})))
        body={'library':'Audiobooks','id':candidate,'revision':4,'job_id':job,'cleanup_id':cleanup,'queue':True,'title':'Fixture'}
        h.queue_press('/api/audiobook/cleanup/retry',body);args,kwargs=h.server.actions.enqueue.call_args
        self.assertEqual(args[:3],('cleanup',candidate,'Fixture'));self.assertEqual(args[3],{'identity_retry':True,'revision':4,'job_id':job,'cleanup_id':cleanup})
        for invalid in ({**body,'extra':True},{k:v for k,v in body.items() if k!='cleanup_id'}):
            with self.assertRaises(ValueError):h.queue_press('/api/audiobook/cleanup/retry',invalid)
        merge=SimpleNamespace(retry_source_cleanup=Mock(return_value={'accepted':True}));BrowserServer.run_queued(SimpleNamespace(merge=merge),{'action':'cleanup','book_id':candidate,'args':args[3]});merge.retry_source_cleanup.assert_called_once_with('Audiobooks',candidate,4,job,cleanup)
