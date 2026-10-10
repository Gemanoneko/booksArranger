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
        self.service.cleanup.resume.assert_called_once_with(['owned'],follow_audio=False)
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
