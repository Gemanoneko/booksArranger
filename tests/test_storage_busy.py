"""Private native files/SQLite contention only; no media processes/live library."""
import contextlib,hashlib,json,sqlite3,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
import sqlite_retry
from scanner import connect
from native_io import BoundaryError,VerifiedFile
import test_storage_cleanup as fixture

class StorageBusyTests(unittest.TestCase):
    setUp=fixture.RetentionTests.setUp
    tearDown=fixture.RetentionTests.tearDown
    assert_preserved=fixture.RetentionTests.assert_preserved
    retire=fixture.RetentionTests.retire
    def receipt(self,stack):
        path=self.stage/'checked.m4b'
        return self.storage._prepare(stack,self.job_id,'staging',path,self.stage_root,(self.output['sha256'],self.output['size']))
    def writer(self):
        db=sqlite3.connect(self.db,check_same_thread=False);db.execute('BEGIN IMMEDIATE');return db
    def completed_unchanged(self):
        with connect(self.db) as db:
            self.assertEqual(db.execute('SELECT state FROM audio_jobs WHERE job_id=?',(self.job_id,)).fetchone()[0],'completed')
        self.assertEqual(hashlib.sha256(Path(self.output['final_path']).read_bytes()).hexdigest(),self.output['sha256'])
    def test_real_busy_release_commits_one_receipt_and_disposes_once(self):
        with contextlib.ExitStack() as stack:
            prepared=self.receipt(stack);writer=self.writer();timer=threading.Timer(.4,lambda:(writer.rollback(),writer.close()));timer.start()
            native=prepared[1].dispose;calls=[]
            def dispose():calls.append(1);return native()
            try:
                with patch.object(prepared[1],'dispose',side_effect=dispose),patch.object(sqlite_retry,'connect',wraps=sqlite_retry.connect) as connects:
                    self.storage._dispose([prepared])
                self.assertGreaterEqual(connects.call_count,4)  # Three transitions plus at least one real lock retry.
            finally:timer.join(2)
            self.assertEqual(len(calls),1);self.assertFalse(prepared[0].exists())
        self.completed_unchanged()
    def test_busy_exhaustion_before_intent_retains_file(self):
        with contextlib.ExitStack() as stack:
            prepared=self.receipt(stack);writer=self.writer()
            try:
                with patch.object(prepared[1],'dispose',side_effect=AssertionError('unexpected disposal')),patch.object(sqlite_retry,'BUSY_SECONDS',.1):
                    with self.assertRaises(sqlite3.OperationalError) as caught:self.storage._dispose([prepared])
                self.assertEqual(caught.exception.sqlite_errorcode&255,sqlite3.SQLITE_BUSY);self.assertTrue(prepared[0].exists())
            finally:writer.rollback();writer.close()
        self.completed_unchanged()
    def test_busy_after_dispose_preserves_intent_and_never_replays_disposal(self):
        with contextlib.ExitStack() as stack:
            prepared=self.receipt(stack);real=self.storage._file_state;writers=[];calls=[];native=prepared[1].dispose
            def state(path,nextstate):
                if nextstate=='disposition_set':writers.append(self.writer())
                return real(path,nextstate)
            def dispose():calls.append(1);return native()
            try:
                with patch.object(self.storage,'_file_state',side_effect=state),patch.object(prepared[1],'dispose',side_effect=dispose),patch.object(sqlite_retry,'BUSY_SECONDS',.1):
                    with self.assertRaises(sqlite3.OperationalError):self.storage._dispose([prepared])
            finally:
                for db in writers:db.rollback();db.close()
            self.assertEqual(calls,[1])
            with connect(self.db) as db:self.assertEqual(db.execute('SELECT state FROM storage_cleanup_files WHERE path=?',(str(prepared[0]),)).fetchone()[0],'removal_intended')
        self.assertFalse(prepared[0].exists());self.completed_unchanged()
    def test_full_file_provenance_cas_refuses_changed_receipt(self):
        with contextlib.ExitStack() as stack:
            prepared=self.receipt(stack)
            with connect(self.db) as db:db.execute('UPDATE storage_cleanup_files SET size=size+1 WHERE path=?',(str(prepared[0]),))
            with self.assertRaises(BoundaryError):self.storage._file_state(prepared[0],'removal_intended')
            self.assertTrue(prepared[0].exists())
    def test_exact_same_file_state_revalidates_database_provenance(self):
        with contextlib.ExitStack() as stack:
            prepared=self.receipt(stack);old=self.storage._file_state(prepared[0],'verified')
            self.assertEqual(old,self.storage._receipts[str(prepared[0])])
            with connect(self.db) as db:db.execute("UPDATE storage_cleanup_files SET facts='changed' WHERE path=?",(str(prepared[0]),))
            with self.assertRaises(BoundaryError):self.storage._file_state(prepared[0],'verified')
    def test_terminal_file_receipt_never_regresses(self):
        with contextlib.ExitStack() as stack:
            prepared=self.receipt(stack);self.storage._dispose([prepared])
            with self.assertRaises(BoundaryError):self.storage._file_state(prepared[0],'verified')
    def test_job_completed_not_overwritten_by_stale_attention(self):
        digest=self.output['sha256'];self.storage._set(self.job_id,digest,'checking');self.storage._set(self.job_id,digest,'removing');self.storage._set(self.job_id,digest,'completed')
        self.storage._set(self.job_id,digest,'needs_attention','late error')
        self.assertEqual(self.storage.status()[0]['state'],'completed')
        with self.assertRaises(BoundaryError):self.storage._set(self.job_id,digest,'completed','different reason')
    def test_removing_crash_resume_revalidates_without_regression(self):
        digest=self.output['sha256'];self.storage._set(self.job_id,digest,'checking');self.storage._set(self.job_id,digest,'removing');before=self.storage.status()[0]
        self.assertEqual(self.storage._set(self.job_id,digest,'checking'),before)
        self.storage.run(self.job_id)
        self.assertEqual(self.storage.status()[0]['state'],'completed');self.completed_unchanged()
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_unknown_output_provenance_cannot_overwrite_job(self):
        self.storage._set(self.job_id,self.output['sha256'],'checking')
        with self.assertRaises(BoundaryError):self.storage._set(self.job_id,'changed','needs_attention')
    def test_native_locked_is_not_retried(self):
        error=sqlite3.OperationalError('locked');error.sqlite_errorcode=sqlite3.SQLITE_LOCKED;calls=[]
        def fault(db):calls.append(1);raise error
        with self.assertRaises(sqlite3.OperationalError) as caught:sqlite_retry.transaction(self.db,fault)
        self.assertIs(caught.exception,error);self.assertEqual(calls,[1])
    def test_unknown_message_busy_is_not_retried(self):
        error=sqlite3.OperationalError('database is locked');calls=[]
        def fault(db):calls.append(1);raise error
        with self.assertRaises(sqlite3.OperationalError) as caught:sqlite_retry.transaction(self.db,fault)
        self.assertIs(caught.exception,error);self.assertEqual(calls,[1])
    def test_secondary_diagnostic_failures_do_not_mask_original(self):
        primary=BoundaryError('exact output changed')
        with patch.object(self.storage,'protected_output',side_effect=primary),patch('storage_cleanup.transaction',side_effect=sqlite3.OperationalError('secondary')):
            with self.assertRaises(BoundaryError) as caught:self.storage.run(self.job_id)
        self.assertIs(caught.exception,primary);diagnostic=self.storage.last_errors[self.job_id]
        self.assertEqual(diagnostic['exception_class'],'BoundaryError');self.assertEqual(len(diagnostic['secondary']),2);self.completed_unchanged();self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_additive_diagnostic_catalog_compatibility(self):
        from storage_cleanup import StorageCleanup
        before=self.queue.status()
        with connect(self.db) as db:db.execute('DROP TABLE storage_cleanup_errors')
        StorageCleanup(self.db,self.stage_root,self.source.root)
        self.assertEqual(self.queue.status(),before)
        self.storage._phase='commit removal intent';self.storage._disposition='not_started'
        error=sqlite3.OperationalError('native busy');error.sqlite_errorcode=sqlite3.SQLITE_BUSY;error.sqlite_errorname='SQLITE_BUSY'
        self.storage._diagnose(self.job_id,self.output['sha256'],error)
        with connect(self.db) as db:
            rows=db.execute('SELECT * FROM storage_cleanup_errors').fetchall();self.assertEqual(len(rows),1);d=json.loads(rows[0]['diagnostic'])
        self.assertEqual(d['sqlite_errorcode'],sqlite3.SQLITE_BUSY);self.assertEqual(d['phase'],'commit removal intent');self.assertEqual(d['disposition'],'not_started');self.completed_unchanged()
    def test_unproven_preoutput_failure_upgrades_only_after_verified_output(self):
        self.storage._set(self.job_id,'','needs_attention','pre-output failure')
        self.storage.run(self.job_id)
        row=self.storage.status()[0];self.assertEqual(row['state'],'completed');self.assertEqual(row['output_hash'],self.output['sha256'])
        with self.assertRaises(BoundaryError):self.storage._set(self.job_id,'','needs_attention','stale unproven failure')
        self.completed_unchanged()
    def test_failure_preserves_completed_recovery_and_exact_24_hour_expiry(self):
        from recovery_retention import RecoveryRetention,moment
        self.retire();retention=RecoveryRetention(self.storage)
        with connect(self.db) as db:before=dict(db.execute('SELECT * FROM recovery_retention WHERE job_id=?',(self.job_id,)).fetchone())
        self.assertEqual((moment(before['expires_at'])-moment(before['completed_at'])).total_seconds(),86400)
        self.assertEqual(before['state'],'retained')
        original=BoundaryError('receipt refusal before disposal')
        with patch.object(self.storage,'_dispose',side_effect=original):
            with self.assertRaises(BoundaryError) as caught:self.storage.run(self.job_id)
        self.assertIs(caught.exception,original)
        with connect(self.db) as db:after=dict(db.execute('SELECT * FROM recovery_retention WHERE job_id=?',(self.job_id,)).fetchone())
        self.assertEqual(after,before);self.assertTrue(all(p.exists() for p in (self.source.root/self.cleanup_id).iterdir()));self.completed_unchanged()
