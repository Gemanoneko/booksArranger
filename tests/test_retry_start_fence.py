"""Deterministic Pause/start controls. Written only; no admitted Python execution yet."""
import contextlib, json, sys, threading, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import audio_jobs, source_cleanup, merge_service
from audio_jobs import AudioJobs, StartRefused
from source_cleanup import CleanupJobs
from merge_service import MergeService
REAL_THREAD=threading.Thread

class FakeThread:
    created=[]
    def __init__(self,target=None,args=(),**kwargs):self.target=target;self.args=args;self.started=False;self.created.append(self)
    def start(self):self.started=True
    def is_alive(self):return self.started
    def join(self,timeout=None):self.joined=True;self.started=False

def queue():
    q=AudioJobs.__new__(AudioJobs);q._lock=threading.RLock();q._closed=False
    q._stop=threading.Event();q._drain=threading.Event();q._verify_stop=threading.Event()
    q._thread=None;q._resuming=False;q._check_progress=None
    q.status=Mock(side_effect=lambda:{'state':'Paused','jobs':[]})
    q._rows=Mock(return_value=[]);q._settle=Mock();q._apply_unchanged=Mock();q._work=Mock()
    return q

def cleanup():
    c=CleanupJobs.__new__(CleanupJobs);c.lock=threading.RLock();c.closed=False
    c.stop=threading.Event();c.thread=None;c.current=None;c.after_drain=None;c._rows=Mock(return_value=[])
    return c

def service():
    s=MergeService.__new__(MergeService);s.jobs=queue();s.cleanup=cleanup();s.draining=False
    s.operation_lock=threading.RLock();s._no_scan=Mock();s._prune_completed=Mock()
    s.state=Mock(side_effect=lambda:{'state':'Paused','jobs':[]})
    s._record_start_failure=Mock(side_effect=lambda e:{'state':getattr(e,'start_state','blocked'),'reason':str(e)})
    return s

class RetryStartFenceTests(unittest.TestCase):
    def setUp(self):FakeThread.created=[]
    def test_pause_before_delayed_audio_start_preserves_stop(self):
        s=service();g=s._capture_start_generation();s.pause()
        with patch.object(audio_jobs.threading,'Thread',FakeThread):
            with self.assertRaises(StartRefused):s.jobs.resume(lambda:s._start_allowed(g),g)
        self.assertTrue(s.jobs._stop.is_set());self.assertTrue(s.cleanup.stop.is_set());self.assertEqual(FakeThread.created,[])
    def test_pause_during_long_output_check_does_not_apply_stale_results(self):
        s=service();g=s._capture_start_generation();s.jobs._rows.return_value=[{'job_id':'completed'}]
        s.jobs._settle.side_effect=lambda *_:(s.pause(),{'state':'needs attention'})[1]
        with patch.object(audio_jobs.threading,'Thread',FakeThread):
            with self.assertRaises(StartRefused):s.jobs.resume(lambda:s._start_allowed(g),g)
        s.jobs._apply_unchanged.assert_not_called();self.assertEqual(FakeThread.created,[]);self.assertTrue(s.jobs._stop.is_set())
    def test_admission_already_holding_lock_may_start_before_pause_completes(self):
        s=service();g=s._capture_start_generation();invalidated=threading.Event();pause_done=threading.Event();threads=[]
        original_pause=s.cleanup.pause
        def cleanup_pause():original_pause();invalidated.set()
        s.cleanup.pause=cleanup_pause
        class InterleavedThread(FakeThread):
            def start(self):
                self.started=True
                t=REAL_THREAD(target=lambda:(s.pause(),pause_done.set()));threads.append(t);t.start()
                if not invalidated.wait(2):raise AssertionError('Pause did not reach queue boundary')
                if pause_done.is_set():raise AssertionError('Pause completed while audio lock was still held')
        with patch.object(audio_jobs.threading,'Thread',InterleavedThread):s.jobs.resume(lambda:s._start_allowed(g),g)
        for t in threads:t.join(2)
        self.assertTrue(pause_done.is_set());self.assertTrue(s.jobs._stop.is_set())
        with self.assertRaises(StartRefused):s.resume(start_generation=g)
    def test_old_checker_busy_then_new_explicit_start_succeeds(self):
        s=service();s.pause();s.jobs._resuming=True;s.jobs._resuming_token=0
        with patch.object(audio_jobs.threading,'Thread',FakeThread):
            with self.assertRaises(StartRefused) as caught:s.resume()
            self.assertEqual(caught.exception.start_state,'busy');self.assertTrue(s.jobs._stop.is_set())
            s.jobs._resuming=False
            self.assertEqual(s.resume()['start_admission']['state'],'started')
        self.assertEqual(len(FakeThread.created),1)
    def test_same_generation_checker_is_explicit_checking_not_second_worker(self):
        q=queue();q._resuming=True;q._resuming_token=7
        with patch.object(audio_jobs.threading,'Thread',FakeThread):answer=q.resume(lambda:True,7)
        self.assertEqual(answer['start_admission']['state'],'checking');self.assertEqual(FakeThread.created,[])
    def test_callback_exception_fails_before_any_stop_clear(self):
        q=queue();q._stop.set()
        def broken():raise ValueError('callback failed')
        with patch.object(audio_jobs.threading,'Thread',FakeThread):
            with self.assertRaisesRegex(ValueError,'callback failed'):q.resume(broken,1)
        self.assertTrue(q._stop.is_set());self.assertEqual(FakeThread.created,[])
    def test_cleanup_pause_uses_existing_lock(self):
        c=cleanup();done=threading.Event()
        with c.lock:
            t=REAL_THREAD(target=lambda:(c.pause(),done.set()));t.start()
            self.assertFalse(done.wait(.02))
        t.join(2);self.assertTrue(done.is_set());self.assertTrue(c.stop.is_set())
    def test_cleanup_stale_start_and_callback_exception_restore_stop(self):
        c=cleanup();c.stop.set()
        with patch.object(source_cleanup.threading,'Thread',FakeThread):
            with self.assertRaises(StartRefused):c.resume(admission_check=lambda:False)
            checks=iter([True,False])
            with self.assertRaises(StartRefused):c.resume(admission_check=lambda:next(checks))
        self.assertTrue(c.stop.is_set());self.assertEqual(FakeThread.created,[])
    def test_cleanup_handoff_carries_original_generation(self):
        s=service();s.cleanup._rows.return_value=[{'id':'cleanup','intent':'{}'}]
        with patch.object(source_cleanup.threading,'Thread',FakeThread):s.resume()
        [worker]=FakeThread.created;self.assertEqual(worker.args[:2],(None,True));handoff=worker.args[2]
        s.pause();s.cleanup._rows.return_value=[]
        # Directly exercise the captured per-worker handoff; no source/audio work is executed.
        result=handoff();self.assertEqual(result['start_admission']['state'],'stale')
        self.assertTrue(s.jobs._stop.is_set());self.assertEqual(len(FakeThread.created),1)
    def test_new_request_behind_old_pending_start_is_explicit_busy(self):
        s=service();owner=object();s._resume_pending=True;s._resume_pending_owner=owner
        with patch.object(merge_service.threading,'Thread',FakeThread):result=s._resume_later()
        self.assertEqual(result['state'],'busy');self.assertIs(s._resume_pending_owner,owner);self.assertEqual(FakeThread.created,[])
    def test_old_pending_finally_cannot_clear_different_owner(self):
        s=service();new_owner=object()
        def swapped(**kwargs):s._resume_pending_owner=new_owner;return {}
        s.resume=swapped
        with patch.object(merge_service.threading,'Thread',FakeThread):s._resume_later()
        [scheduled]=FakeThread.created;scheduled.target()
        self.assertTrue(s._resume_pending);self.assertIs(s._resume_pending_owner,new_owner)
    def test_delayed_async_after_pause_retains_request_and_reports_stale(self):
        s=service()
        with patch.object(merge_service.threading,'Thread',FakeThread):s._resume_later()
        [scheduled]=FakeThread.created;s.pause();scheduled.target()
        self.assertEqual(s._record_start_failure.call_args.args[0].start_state,'stale')
        self.assertFalse(s._resume_pending);self.assertTrue(s.jobs._stop.is_set())
    def test_drain_invalidates_before_delayed_start(self):
        s=service();g=s._capture_start_generation();s.jobs.drain=Mock();s.drain()
        self.assertFalse(s._start_allowed(g));s.jobs.drain.assert_called_once()
        with self.assertRaises(StartRefused):s.resume(start_generation=g)
    def test_close_is_permanent_before_first_component_close(self):
        s=service();g=s._capture_start_generation();s.series_backfill=SimpleNamespace(close=Mock(side_effect=RuntimeError('stop test before teardown')))
        with self.assertRaisesRegex(RuntimeError,'stop test'):s.close()
        self.assertTrue(s._closing);self.assertFalse(s._start_allowed(g))
        with self.assertRaises(StartRefused) as caught:s._capture_start_generation()
        self.assertEqual(caught.exception.start_state,'closing')
    def test_start_while_pause_in_progress_is_explicit_busy(self):
        s=service();s._pause_depth=1
        with self.assertRaises(StartRefused) as caught:s.resume()
        self.assertEqual(caught.exception.start_state,'busy');self.assertEqual(FakeThread.created,[])
    def test_optional_default_audio_and_cleanup_callers_still_start(self):
        q=queue();c=cleanup()
        with patch.object(audio_jobs.threading,'Thread',FakeThread):
            q.resume();c.resume(follow_audio=False)
        self.assertEqual(len(FakeThread.created),2)

    def test_historical_intent_is_captured_before_operation_wait(self):
        s=service();s.enroll_cleanup=Mock()
        class DelayedOperation:
            def __enter__(self):s.pause()
            def __exit__(self,*_):return False
        s.operation_lock=DelayedOperation()
        with patch.object(source_cleanup.threading,'Thread',FakeThread):
            with self.assertRaises(StartRefused):s.start_historical_cleanup('book')
        s.enroll_cleanup.assert_not_called();self.assertEqual(FakeThread.created,[])
    def test_pause_during_historical_enrollment_keeps_intent_without_start(self):
        s=service();s.cleanup.status=Mock(return_value=[])
        s.enroll_cleanup=Mock(side_effect=lambda *_args,**_kw:(s.pause(),{'cleanup_id':'saved'})[1])
        with patch.object(source_cleanup.threading,'Thread',FakeThread):
            with self.assertRaises(StartRefused):s.start_historical_cleanup('book')
        s.enroll_cleanup.assert_called_once();self.assertTrue(s.cleanup.stop.is_set());self.assertEqual(FakeThread.created,[])
    def test_new_historical_request_after_pause_is_finite_not_auto_renewal(self):
        s=service();s.pause();s.cleanup.status=Mock(return_value=[]);s.enroll_cleanup=Mock(return_value={'cleanup_id':'saved'})
        with patch.object(source_cleanup.threading,'Thread',FakeThread):s.start_historical_cleanup('book')
        self.assertEqual(len(FakeThread.created),1);self.assertEqual(getattr(s,'_automatic_cleanup_generation',0),0)
    def test_automatic_sweep_cannot_refresh_intent_after_pause_or_borrow_new_start(self):
        s=service();s._purge_tried=set();s._settle_folder_jobs=Mock();s._kept_by_choice=Mock(return_value=set())
        reason=next(iter(s.HELD_FOR_METADATA));held=[{'id':'held','job_id':'book','reason':reason}]
        s.cleanup._rows=Mock(side_effect=lambda query:[] if "state IN ('waiting','paused')" in query else held)
        old_trigger=0;s.pause()
        with patch.object(source_cleanup.threading,'Thread',FakeThread):
            s._finish_held_cleanups();self.assertEqual(FakeThread.created,[])
            s.resume();s.jobs._thread=None  # the private fake admitted audio worker has finished
            s._finish_held_cleanups(old_trigger);self.assertEqual(len(FakeThread.created),1,'old sweep cannot borrow new permission')
            s._finish_held_cleanups(s._automatic_cleanup_generation)
        self.assertEqual(len(FakeThread.created),2);self.assertEqual(s._purge_tried,{'held'})
    def test_cleanup_close_waits_for_start_lock_and_joins_exact_worker(self):
        c=cleanup();done=threading.Event()
        with patch.object(source_cleanup.threading,'Thread',FakeThread):
            with c.lock:
                closer=REAL_THREAD(target=lambda:(c.close(),done.set()));closer.start()
                self.assertFalse(done.wait(.02));c.resume(admission_check=lambda:True,admission_token=0)
        closer.join(2);self.assertTrue(done.is_set());self.assertTrue(c.closed)
        self.assertTrue(c.thread.joined);self.assertTrue(c.stop.is_set())
        with self.assertRaises(ValueError):c.resume()
    def test_pause_during_bulk_summary_prevents_new_event_and_receipt(self):
        s=service();s.inventory=SimpleNamespace(worker=None);s._save_bulk_receipt=Mock(return_value=True)
        s.attention_summary=Mock(side_effect=lambda **_:(s.pause(),{'parent':{'group':'retry'}})[1])
        with patch.object(merge_service.threading,'Thread',FakeThread):
            with self.assertRaises(StartRefused):s.retry_all()
        s._save_bulk_receipt.assert_not_called();self.assertEqual(FakeThread.created,[])
    def test_initial_receipt_save_holds_no_control_lock_and_pause_cancels_launch(self):
        s=service();s.inventory=SimpleNamespace(worker=None);s.attention_summary=Mock(return_value={'parent':{'group':'retry','retry':{'allowed':True,'reason':''}}})
        waiting=threading.Event();release=threading.Event();saves=[];answers=[];errors=[]
        def save(run):
            acquired=merge_service._BULK_LOCK.acquire(blocking=False)
            self.assertTrue(acquired,'SQLite persistence cannot own the control lock')
            if acquired:merge_service._BULK_LOCK.release()
            saves.append(dict(run))
            if len(saves)==1:
                waiting.set()
                if not release.wait(2):raise AssertionError('receipt barrier was not released')
            return True
        def submit():
            try:answers.append(s.retry_all())
            except BaseException as error:errors.append(error)
        s._save_bulk_receipt=save
        with patch.object(merge_service.threading,'Thread',FakeThread):
            caller=REAL_THREAD(target=submit);caller.start()
            try:
                self.assertTrue(waiting.wait(2));s.pause()
                self.assertTrue(s.jobs._stop.is_set(),'Pause completes while persistence remains blocked')
                self.assertTrue(s.cleanup.stop.is_set());self.assertEqual(answers,[])
            finally:release.set();caller.join(2)
        self.assertFalse(caller.is_alive());self.assertEqual(errors,[])
        [result]=answers
        self.assertEqual((result['state'],result['accepted'],result['done']),('stopped',0,0));self.assertEqual(FakeThread.created,[])
        self.assertEqual(result['start_outcome']['state'],'stale');self.assertEqual(len(saves),2)

    def test_per_target_rechecks_captured_generation_after_operation_wait(self):
        s=service();s.inventory=SimpleNamespace(worker=None);s._reacquire_admission=Mock();s.attention_summary=Mock()
        class DelayedOperation:
            def __enter__(self):s.pause()
            def __exit__(self,*_):return False
        s.operation_lock=DelayedOperation()
        with self.assertRaises(StartRefused):s._retry_one('parent',start_generation=0)
        s.attention_summary.assert_not_called()
    def test_invalidated_bulk_generation_never_submits_another_target(self):
        s=service();s._retry_one=Mock();s._save_bulk_receipt=Mock(return_value=True);s.resume=Mock();s.pause()
        run=dict(start_generation=0,state='running',total=1,done=0,accepted=0,queued=0,next=0,refused=0,accepted_ids=[])
        s._retry_all_work(run,[{'job_id':'parent'}],threading.Event())
        s._retry_one.assert_not_called();s.resume.assert_not_called();self.assertEqual((run['state'],run['accepted']),('stopped',0))

if __name__=='__main__':unittest.main()
