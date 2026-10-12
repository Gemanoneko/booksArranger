"""Tiny exact native recovery fixtures; controlled clocks, no production paths."""
import contextlib,json,sys,threading,time,unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_storage_cleanup as fixture
from recovery_retention import RecoveryRetention,moment
from scanner import connect
from native_io import BoundaryError,VerifiedFile
from merge_service import MergeService

class RecoveryTests(unittest.TestCase):
    setUp=fixture.RetentionTests.setUp
    tearDown=fixture.RetentionTests.tearDown
    retire=fixture.RetentionTests.retire
    def ready(self):
        self.retire();self.storage.run(self.job_id)
        self.retention=RecoveryRetention(self.storage)
        self.initial=self.retention.status(self.job_id)
        self.now=moment(self.initial['completed_at']);self.retention.clock=lambda:self.now
        return self.initial
    def test_24h_boundary_restart_and_stage_independence(self):
        first=self.ready();self.assertEqual(first['count'],2);self.assertEqual(first['bytes'],4096)
        self.assertEqual(self.storage.status()[0]['state'],'completed');self.assertEqual(list(self.stage.iterdir()),[])
        self.now+=timedelta(hours=24,microseconds=-1);self.assertEqual(self.retention.due(),[])
        self.retention.purge(self.job_id);self.assertEqual(self.retention.status(self.job_id)['count'],2)
        again=RecoveryRetention(self.storage,clock=lambda:self.now);self.assertEqual(again.status(self.job_id)['expires_at'],first['expires_at'])
        self.now+=timedelta(microseconds=1);self.assertEqual(again.due(),[self.job_id])
        done=again.purge(self.job_id);self.assertEqual(done['state'],'deleted');self.assertEqual(done['bytes'],0);self.assertEqual(done['actor'],'automatic')
        self.assertEqual(again.purge(self.job_id),done)
        self.assertTrue(Path(self.output['final_path']).exists())
    def test_manual_scope_and_foreign_identity_are_preserved(self):
        first=self.ready();scope={k:first[k] for k in ('token','count','bytes')}
        with self.assertRaisesRegex(ValueError,'changed'):self.retention.purge(self.job_id,'manual',dict(scope,bytes=0))
        backup=next((self.source.root/self.cleanup_id).iterdir());raw=backup.read_bytes();backup.unlink();backup.write_bytes(raw)
        with self.assertRaises(BoundaryError):self.retention.purge(self.job_id,'manual')
        self.assertEqual(backup.read_bytes(),raw)
    def test_unknown_content_and_changed_output_block_before_deletion(self):
        first=self.ready();extra=self.source.root/self.cleanup_id/'foreign.txt';extra.write_text('preserve')
        with self.assertRaisesRegex(BoundaryError,'Unknown recovery'):self.retention.purge(self.job_id,'manual')
        self.assertEqual(self.retention.status(self.job_id)['count'],2);self.assertTrue(extra.exists())
    def test_changed_output_and_incomplete_retirement_preserve(self):
        self.ready();Path(self.output['final_path']).write_bytes(b'changed')
        with self.assertRaisesRegex(BoundaryError,'output bytes'):self.retention.purge(self.job_id,'manual')
        self.assertEqual(self.retention.status(self.job_id)['count'],2)
    def test_crash_reconciles_exact_intent_and_unknown_absence_does_not(self):
        self.ready();real=self.storage._file_state;hit=[]
        class Crash(BaseException):pass
        def crash(path,state):
            if state=='disposition_set' and not hit:hit.append(path);raise Crash()
            real(path,state)
        with patch.object(self.storage,'_file_state',side_effect=crash):
            with self.assertRaises(Crash):self.retention.purge(self.job_id,'manual')
        self.assertEqual(self.retention.due(),[self.job_id]);done=self.retention.purge(self.job_id)
        self.assertEqual(done['state'],'deleted');self.assertEqual(done['actor'],'manual')
        with connect(self.db) as db:self.assertEqual(db.execute('SELECT state FROM storage_cleanup_files WHERE path=?',(str(hit[0]),)).fetchone()[0],'absent_after_intent')
    def test_cooperative_shutdown_resumes_partial_exact_purge(self):
        self.ready();calls=[]
        def stop():
            calls.append(1)
            if len(calls)==3:raise InterruptedError('closing')
        self.retention.guard=stop
        with self.assertRaises(InterruptedError):self.retention.purge(self.job_id,'manual')
        self.assertEqual(self.retention.due(),[self.job_id]);self.assertEqual(self.retention.status(self.job_id)['count'],1)
        self.retention.guard=lambda:None
        self.assertEqual(self.retention.purge(self.job_id)['state'],'deleted')
    def test_unknown_absence_and_uncertain_legacy_age_preserve(self):
        self.ready();path=next((self.source.root/self.cleanup_id).iterdir());path.unlink()
        with self.assertRaises(BoundaryError):self.retention.purge(self.job_id,'manual')
        with connect(self.db) as db:
            db.execute('DELETE FROM recovery_retention');db.execute('DELETE FROM recovery_completion')
        legacy=RecoveryRetention(self.storage);self.assertEqual(legacy.due(),[]);self.assertFalse(legacy.status(self.job_id)['eligible'])
    def test_incomplete_source_retirement_blocks_all_copies(self):
        self.ready()
        with connect(self.db) as db:db.execute("UPDATE cleanup_members SET state='removal_intended' WHERE cleanup_id=?",(self.cleanup_id,))
        with self.assertRaisesRegex(BoundaryError,'correspondence'):self.retention.purge(self.job_id,'manual')
        self.assertEqual(self.retention.status(self.job_id)['count'],2)
    def test_mutable_completion_status_cannot_reset_deadline(self):
        first=self.ready()
        with connect(self.db) as db:db.execute("UPDATE source_cleanup SET updated='2099-01-01T00:00:00+00:00' WHERE id=?",(self.cleanup_id,))
        again=RecoveryRetention(self.storage);self.assertEqual(again.status(self.job_id)['expires_at'],first['expires_at'])
    def test_manual_success_before_expiry(self):
        first=self.ready();done=self.retention.purge(self.job_id,'manual',{k:first[k] for k in ('token','count','bytes')})
        self.assertEqual(done['state'],'deleted');self.assertEqual(done['actor'],'manual')

class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.service=MergeService.__new__(MergeService);s=self.service
        s.operation_lock=threading.RLock();s.inventory=SimpleNamespace(worker=None);s._retention_stop=threading.Event();s._retention_wake=threading.Event();s._manual_recovery=None;s._post_current=None
        s.jobs=SimpleNamespace(_thread=None,status=lambda:{'jobs':[]});s.cleanup=SimpleNamespace(thread=None,current=None,_rows=lambda *a:[])
        s.recovery=SimpleNamespace(status=lambda id:{'eligible':True,'token':'a'*64,'count':2,'bytes':4096,'reason':''})
    def test_manual_duplicate_stale_and_busy_no_action(self):
        s=self.service
        with self.assertRaisesRegex(ValueError,'changed'):s.delete_recovery('job','b'*64,2,4096)
        s.jobs.status=lambda:{'jobs':[{'state':'pending'}]}
        with self.assertRaisesRegex(ValueError,'queued'):s.delete_recovery('job','a'*64,2,4096)
        s.jobs.status=lambda:{'jobs':[]};s.delete_recovery('job','a'*64,2,4096)
        with self.assertRaisesRegex(ValueError,'queued'):s.delete_recovery('job','a'*64,2,4096)

    def test_idle_startup_worker_and_shutdown_and_scan_admission(self):
        s=self.service;called=threading.Event();s._retention_thread=None;s.jobs.close=Mock();s.cleanup.close=Mock()
        s.recovery.due=lambda:['owned'];s.recovery.purge=lambda *a:called.set();s.recovery._set=Mock()
        entries=[]
        @contextlib.contextmanager
        def admission():
            entries.append('admitted');yield
        s.start_retention(admission);self.assertTrue(called.wait(2));s.close();self.assertFalse(s._retention_thread.is_alive());self.assertEqual(entries,['admitted'])
        from web_server import BrowserServer
        server=BrowserServer.__new__(BrowserServer);server.control_condition=threading.Condition();server.closing=False;server.merge_admissions=0;server.recovery_operations=0;server.scan_active=lambda:False
        with server.recovery_admission():self.assertEqual(server.merge_admissions,1)
        self.assertEqual(server.merge_admissions,0);server.scan_active=lambda:True
        with self.assertRaises(ValueError):
            with server.recovery_admission():self.fail('Busy scan admitted')

if __name__=='__main__':unittest.main()
