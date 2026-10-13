"""Private native disposition fixtures for published working-only cleanup."""
import hashlib,json,os,unittest,uuid
from pathlib import Path
from unittest.mock import patch
import test_storage_cleanup as fixtures
from scanner import connect
from source_cleanup import packed
from native_io import BoundaryError
from encoding_policy import AUTOMATIC_PROFILE

class WorkingCleanupTests(unittest.TestCase):
    setUp=fixtures.RetentionTests.setUp
    tearDown=fixtures.RetentionTests.tearDown
    def normalized(self):
        self.manifest['profile']=AUTOMATIC_PROFILE
        self.output['validation']['profile']=AUTOMATIC_PROFILE
        path=self.stage/'normalized00000.wav';path.write_bytes(b'private exact normalized bytes')
        self.output['validation']['staging_artifacts']['files'][path.name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':path.stat().st_size}
        self.queue._update(self.job_id,manifest=packed(self.manifest),manifest_hash=hashlib.sha256(packed(self.manifest).encode()).hexdigest(),output=json.dumps(self.output))
        (self.job/'ownership.json').write_text(packed({'job_id':self.job_id,'manifest':self.manifest}),encoding='utf8')
        return path
    def test_retirement_pending_removes_working_preserves_snapshots_and_originals(self):
        self.source.enroll(self.full,{})
        plan=self.storage.working_files(self.job_id,dry_run=True)
        self.assertGreater(plan['bytes'],0)
        self.assertTrue((self.stage/'checked.m4b').exists())
        with connect(self.db) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM storage_cleanup_files').fetchone()[0],0)
        actual=self.storage.working_files(self.job_id)
        self.assertEqual(plan['files'],actual['files'])
        self.assertFalse((self.stage/'checked.m4b').exists())
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
        self.assertTrue(all((self.stage/f'source{i:05d}.mp3').exists() for i in range(2)))
        self.assertEqual(self.storage.status(),[])
        with self.assertRaises(BoundaryError):self.storage.run(self.job_id)
    def test_historical_normalized_only_leaves_every_other_file(self):
        wav=self.normalized();unknown=self.stage/'normalized99999.wav';unknown.write_bytes(b'unknown')
        before={p.name:p.read_bytes() for p in self.stage.iterdir() if p!=wav}
        plan=self.storage.working_files(self.job_id,True,True)
        self.assertEqual([Path(r['path']).name for r in plan['files']],[wav.name])
        self.storage.working_files(self.job_id,normalized_only=True)
        self.assertFalse(wav.exists())
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.stage.iterdir()})
        self.assertEqual(self.storage.working_files(self.job_id,normalized_only=True)['files'],[])
    def test_changed_output_blocks_before_disposition(self):
        wav=self.normalized();Path(self.output['final_path']).write_bytes(b'changed')
        with self.assertRaises(BoundaryError):self.storage.working_files(self.job_id,normalized_only=True)
        self.assertTrue(wav.exists())
    def test_changed_wav_receipt_blocks(self):
        wav=self.normalized();wav.write_bytes(b'changed')
        with self.assertRaises(BoundaryError):self.storage.working_files(self.job_id,normalized_only=True)
        self.assertTrue(wav.exists())
    def test_hardlink_blocks(self):
        wav=self.normalized();os.link(wav,self.base/'alias.wav')
        with self.assertRaises(BoundaryError):self.storage.working_files(self.job_id,normalized_only=True)
        self.assertTrue(wav.exists())
    def test_named_stream_blocks(self):
        wav=self.normalized();Path(str(wav)+':Zone.Identifier').write_bytes(b'zone')
        with self.assertRaises(BoundaryError):self.storage.working_files(self.job_id,normalized_only=True)
        self.assertTrue(wav.exists())
    def test_missing_without_removal_intent_blocks(self):
        wav=self.normalized();wav.unlink()
        with self.assertRaises(BoundaryError):self.storage.working_files(self.job_id,normalized_only=True)
    def test_terminal_path_recreated_with_identical_bytes_blocks(self):
        wav=self.normalized();raw=wav.read_bytes();self.storage.working_files(self.job_id,normalized_only=True);wav.write_bytes(raw)
        with self.assertRaises(BoundaryError):self.storage.working_files(self.job_id,normalized_only=True)
        self.assertEqual(wav.read_bytes(),raw)
    def test_crash_after_disposition_reconciles_absence(self):
        wav=self.normalized();real=self.storage._file_state
        def crash(path,state):
            if state=='removed':raise RuntimeError('private crash')
            return real(path,state)
        with patch.object(self.storage,'_file_state',side_effect=crash),self.assertRaises(RuntimeError):self.storage.working_files(self.job_id,normalized_only=True)
        self.assertFalse(wav.exists())
        self.assertEqual(self.storage.working_files(self.job_id,True,True)['files'],[])
        self.storage.working_files(self.job_id,normalized_only=True)
        self.assertEqual(self.storage._known(wav)['state'],'removed')
    def test_traversal_receipt_never_selected(self):
        wav=self.normalized();self.output['validation']['staging_artifacts']['files']['../normalized00000.wav']={'sha256':'a'*64,'size':1}
        self.queue._update(self.job_id,output=json.dumps(self.output))
        plan=self.storage.working_files(self.job_id,True,True)
        self.assertEqual(len(plan['files']),1);self.assertEqual(plan['files'][0]['path'],str(wav))
    def test_changed_dry_run_identity_blocks_before_any_disposition(self):
        wav=self.normalized();plan=self.storage.working_files(self.job_id,True,True)
        expected=plan['files'];expected[0]['facts']['ino']+=1
        with self.assertRaises(BoundaryError):self.storage.working_files(self.job_id,normalized_only=True,expected_plan=expected)
        self.assertTrue(wav.exists())
    def test_frozen_remaining_plan_resumes_only_receipted_absence(self):
        from cleanup_published_working import remaining_plan
        wav=self.normalized();plan=self.storage.working_files(self.job_id,True,True)
        self.storage.working_files(self.job_id,normalized_only=True)
        self.assertEqual(remaining_plan(self.storage,plan),[])
        wav.write_bytes(b'private exact normalized bytes')
        self.assertEqual(remaining_plan(self.storage,plan),plan['files'])
        with self.assertRaises(BoundaryError):self.storage.working_files(self.job_id,True,True)
    def test_frozen_remaining_plan_refuses_unreceipted_absence(self):
        from cleanup_published_working import remaining_plan
        wav=self.normalized();plan=self.storage.working_files(self.job_id,True,True);wav.unlink()
        with self.assertRaises(BoundaryError):remaining_plan(self.storage,plan)
    def test_wrong_ownership_blocks(self):
        wav=self.normalized();(self.job/'ownership.json').write_text('{}')
        with self.assertRaises(BoundaryError):self.storage.working_files(self.job_id,normalized_only=True)
        self.assertTrue(wav.exists())
    def test_unknown_attempt_preserved(self):
        wav=self.normalized();other=self.job/str(uuid.uuid4());other.mkdir();path=other/wav.name;path.write_bytes(wav.read_bytes())
        self.storage.working_files(self.job_id,normalized_only=True);self.assertTrue(path.exists())

if __name__=='__main__':unittest.main()
