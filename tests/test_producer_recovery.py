"""Native private recovery checkpoints; explicit fixture origin is never production evidence."""
from unittest.mock import patch
import contextlib,hashlib,json,os,sqlite3,tempfile,unittest,uuid
from pathlib import Path
from producer_recovery import ProducerRecovery,CLAIM,digest,packed,verify_retained,protected_dependency
from working_lifecycle import WorkingLifecycle

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        base=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'producer-recovery';base.mkdir(parents=True,exist_ok=True);self.base=Path(tempfile.mkdtemp(prefix='producer-core-',dir=base));self.db=self.base/'catalog.sqlite';self.stage=self.base/'cache'/'audio-staging';self.stage.mkdir(parents=True)
        self.job=str(uuid.uuid4());self.attempt=str(uuid.uuid4());self.candidate=str(uuid.uuid4());self.source=self.base/'original.m4b';self.source.write_bytes(b'original intact')
        self.manifest={'job_id':self.job,'candidate_id':self.candidate,'root':str(self.base),'sources':[{'path':str(self.source),'sha256':hashlib.sha256(self.source.read_bytes()).hexdigest(),'size':self.source.stat().st_size}]}
        with self.connection() as db:
            db.executescript('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,state TEXT,output TEXT,journal TEXT,attempt_id TEXT,manifest_hash TEXT,manifest TEXT);CREATE TABLE book_groups(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,superseded INTEGER);')
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?)',(self.job,'needs attention',None,'{}',self.attempt,digest(self.manifest),packed(self.manifest)));db.execute('INSERT INTO book_groups VALUES(?,?,?,?)',(self.candidate,2,'fixture-fingerprint',0))
        self.working=WorkingLifecycle(self.db,self.stage)
        folder=self.stage/self.job/self.attempt;folder.mkdir(parents=True);(folder.parent/'ownership.json').write_text(packed({'job_id':self.job,'manifest':self.manifest}),encoding='utf8');self.file=folder/'source00000.m4b';self.file.write_bytes(b'unknown snapshot retained')
        with self.connection() as db:
            db.execute('INSERT INTO working_attempts VALUES(?,?,?,?,?,?,?,?)',(self.job,self.attempt,packed(self.manifest),digest(self.manifest),'active','producing','','before'))
            db.execute('INSERT INTO working_files VALUES(?,?,?,?,?,?,?,?,?,?)',(self.job,self.attempt,self.file.name,str(self.file),'source','creation_intended','',0,'{}','before'))
        self.uptime=100000;self.recovery=ProducerRecovery(self.db,self.stage,platform=lambda:{'schema':'books-windows-startup-v1','system_volume_serial':'fixture-volume','machine_guid':'explicit-private-machine','computer':'fixture','windows_directory':'C:/Windows','uptime_ms':self.uptime})
    @contextlib.contextmanager
    def connection(self):
        db=sqlite3.connect(self.db)
        try:
            yield db;db.commit()
        finally:db.close()
    def tearDown(self):pass # Session scratch is retained for Sergei.

    def origin(self):return self.recovery.record_origin(self.job,{'actor':'user','claim':CLAIM,'evidence':'Explicit synthetic fixture historical fact, never user production attestation'})
    def snapshot(self):
        with self.connection() as db:return db.execute('SELECT * FROM working_files').fetchall(),db.execute('SELECT * FROM audio_jobs').fetchall(),self.file.read_bytes(),self.source.read_bytes()
    def test_absent_fact_no_prepare(self):
        self.assertEqual(self.recovery.status(self.job)['cause'],'origin_unproved');before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'origin'):self.recovery.prepare(self.job)
        self.assertEqual(before,self.snapshot())
    def test_same_boot_no_closure(self):
        self.origin();self.assertTrue(self.recovery.status(self.job)['can_prepare']);self.recovery.prepare(self.job);self.assertEqual(self.recovery.status(self.job)['state'],'waiting_restart')
        with self.assertRaisesRegex(ValueError,'startup'):self.recovery.isolate(self.job)
    def test_later_boot_isolates_without_adoption_or_clear(self):
        self.origin();self.recovery.prepare(self.job);before=self.snapshot();self.uptime=5000
        self.assertEqual(self.recovery.status(self.job)['state'],'ready');result=self.recovery.isolate(self.job);self.assertEqual(result['state'],'isolated_retained');self.assertEqual(before,self.snapshot());self.assertEqual(self.recovery.status(self.job)['state'],'isolated_retained')
        with self.connection() as db:
            db.row_factory=sqlite3.Row;verify_retained(db,self.job,self.attempt);self.assertTrue(protected_dependency(db,[self.source]));self.assertTrue(protected_dependency(db,[self.file]));self.assertFalse(protected_dependency(db,[self.base/'other']))
        with self.assertRaisesRegex(ValueError,'retained'):self.working.retire(self.job,self.attempt)
        self.assertEqual(self.recovery.retained(self.candidate)['count'],1)
    def test_changed_old_bytes_refuse(self):
        self.origin();self.recovery.prepare(self.job);self.file.write_bytes(b'drift');self.uptime=5000
        with self.assertRaisesRegex(ValueError,'changed|differs'):self.recovery.isolate(self.job)
    def test_unknown_file_refuses(self):
        self.origin();(self.file.parent/'unknown').write_bytes(b'preserve')
        self.assertEqual(self.recovery.status(self.job)['state'],'unsupported')
    def test_active_current_producer_refuses(self):
        self.recovery.active=lambda *unused:True;self.assertEqual(self.recovery.status(self.job)['state'],'unsupported')

    def test_machine_change_is_not_restart_proof(self):
        self.origin();self.recovery.prepare(self.job);self.uptime=1000;original=self.recovery.platform
        self.recovery.platform=lambda:dict(original(),machine_guid='different-installation')
        self.assertFalse(self.recovery.status(self.job)['can_retry'])
        with self.assertRaisesRegex(ValueError,'startup'):self.recovery.isolate(self.job)
    def test_retained_namespace_drift_cannot_be_reused(self):
        self.origin();self.recovery.prepare(self.job);self.uptime=1000;self.recovery.isolate(self.job);self.file.write_bytes(b'changed after isolation')
        with self.assertRaisesRegex(ValueError,'changed'):
            with self.recovery.protect_retained(self.job):pass
    def test_retained_ledger_drift_refuses_all_authority(self):
        self.origin();self.recovery.prepare(self.job);self.uptime=1000;self.recovery.isolate(self.job)
        with self.connection() as db:db.execute("UPDATE working_files SET state='closed'")
        with self.connection() as db:
            db.row_factory=sqlite3.Row
            with self.assertRaisesRegex(ValueError,'history changed'):verify_retained(db,self.job,self.attempt)
        self.assertFalse(self.recovery.status(self.job)['can_retry'])
    def test_ordinary_storage_cleanup_refuses_isolated_old_file(self):
        from storage_cleanup import StorageCleanup
        self.origin();self.recovery.prepare(self.job);self.uptime=1000;self.recovery.isolate(self.job)
        storage=StorageCleanup(self.db,self.stage,self.base/'recovery')
        with contextlib.ExitStack() as held,self.assertRaisesRegex(ValueError,'retained'):storage._prepare(held,self.job,'temporary',self.file,self.stage)
        self.assertEqual(self.file.read_bytes(),b'unknown snapshot retained')

    def test_superseding_checkpoint_cannot_commit_old_isolation(self):
        self.origin();self.recovery.prepare(self.job);self.uptime=1000;before=self.snapshot();native=self.recovery._native;once=[True]
        @contextlib.contextmanager
        def interleaved(scope,*,hash_files=False):
            with native(scope,hash_files=hash_files) as fence:
                if hash_files and once[0]:
                    once[0]=False;self.recovery.prepare(self.job)
                yield fence
        with patch.object(self.recovery,'_native',side_effect=interleaved),self.assertRaisesRegex(ValueError,'superseded'):self.recovery.isolate(self.job)
        self.assertEqual(self.snapshot(),before)
        with self.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM producer_recovery_checkpoints WHERE state='isolated_retained'").fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM producer_recovery_checkpoints').fetchone()[0],2)
    def test_unplanned_artifact_stream_before_prepare_refuses(self):
        self.origin();Path(str(self.file)+':unplanned').write_bytes(b'unknown stream retained')
        with self.assertRaisesRegex(ValueError,'stream'):self.recovery.prepare(self.job)
    def test_unplanned_marker_stream_before_prepare_refuses(self):
        self.origin();Path(str(self.file.parent.parent/'ownership.json')+':unplanned').write_bytes(b'unknown marker stream')
        with self.assertRaisesRegex(ValueError,'stream'):self.recovery.prepare(self.job)
    def test_unplanned_stream_after_checkpoint_refuses_isolation(self):
        self.origin();self.recovery.prepare(self.job);self.uptime=1000;Path(str(self.file)+':unplanned').write_bytes(b'retained')
        with self.assertRaisesRegex(ValueError,'stream'):self.recovery.isolate(self.job)
    def test_unplanned_stream_after_isolation_refuses_new_attempt_fence(self):
        self.origin();self.recovery.prepare(self.job);self.uptime=1000;self.recovery.isolate(self.job);Path(str(self.file)+':unplanned').write_bytes(b'retained')
        with self.assertRaisesRegex(ValueError,'stream'):
            with self.recovery.protect_retained(self.job):pass

if __name__=='__main__':unittest.main()
