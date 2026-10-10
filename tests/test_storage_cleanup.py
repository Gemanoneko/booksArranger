"""Actual Windows handle fixtures; no real library paths or media tools."""
import contextlib,hashlib,json,os,sys,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audio_jobs import AudioJobs
from native_io import BoundaryError,DirectoryBoundary,VerifiedFile
from source_cleanup import CleanupJobs,packed
from storage_cleanup import StorageCleanup
from scanner import connect

class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='retention-',dir=Path(__file__).resolve().parents[1]/'scratch')
        self.base=Path(self.temp.name);self.library=self.base/'library';self.library.mkdir()
        self.db=self.base/'inventory.sqlite3';self.job_id=str(uuid.uuid4());self.candidate=str(uuid.uuid4())
        self.sources=[]
        for i in range(2):
            p=self.library/f'{i}.mp3';p.write_bytes(bytes([65+i])*2048);st=p.stat()
            self.sources.append({'path':str(p),'size':st.st_size,'modified':str(st.st_mtime_ns),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'fingerprint':{'size':st.st_size,'modified':str(st.st_mtime_ns)}})
        final=self.library/'book.m4b';final.write_bytes(b'validated fixture output');sha=hashlib.sha256(final.read_bytes()).hexdigest()
        with DirectoryBoundary(self.library,final.parent) as boundary:identity=boundary.identities
        self.manifest={'job_id':self.job_id,'candidate_id':self.candidate,'candidate_revision':1,'root':str(self.library),'sources':self.sources,'destination':str(final),
            'profile':'fixture','metadata':{'title':'Fixture','canonical_author':'Author'},'chapters':[],'evidence':[], 'cover':{'path':str(final),'sha256':sha}}
        validation={'passed':True,'checks':'Output checks passed','profile':'fixture','sha256':sha,'size':final.stat().st_size,'tags':{'media_type':'2','title':'Fixture','artist':'Author'},
            'source_pcm_frames':[100,100],'source_pcm_rate':100,'decoded_duration':2,'duration_tolerance':.01,'chapters':[]}
        self.output={'job_id':self.job_id,'final_path':str(final),'owned_temp':str(self.library/'absent.partial'),'size':final.stat().st_size,'sha256':sha,'parent_identity':identity,'validation':validation}
        self.queue=AudioJobs(self.db,None,None,lambda r:True);self.queue.enqueue(self.manifest);self.queue._update(self.job_id,state='completed',stage='completed',output=json.dumps(self.output))
        with connect(self.db) as db:db.execute('CREATE TABLE owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER)')
        self.source=CleanupJobs(self.db,self.base/'source-recovery',lambda db,intent:True,contextlib.nullcontext)
        self.stage_root=self.base/'merge-cache/audio-staging';self.stage_root.mkdir(parents=True)
        self.job=self.stage_root/self.job_id;self.job.mkdir();(self.job/'ownership.json').write_text(packed({'job_id':self.job_id,'manifest':self.manifest}),encoding='utf-8')
        self.stage=self.job/str(uuid.uuid4());self.stage.mkdir()
        for i,s in enumerate(self.sources):(self.stage/f'source{i:05d}.mp3').write_bytes(Path(s['path']).read_bytes())
        (self.stage/'checked.m4b').write_bytes(final.read_bytes());(self.stage/'inputs.txt').write_text('owned input plan')
        (self.stage/(uuid.uuid4().hex+'.stderr')).write_text('')
        self.output['validation']['staging_artifacts']={'attempt_id':self.stage.name,'files':{p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in self.stage.iterdir()}}
        self.queue._update(self.job_id,output=json.dumps(self.output))
        self.storage=StorageCleanup(self.db,self.stage_root,self.source.root)
        self.full={'job_id':self.job_id,'state':'completed','manifest':self.manifest,'output':self.output}
    def tearDown(self):
        self.source.close();self.queue.close();self.temp.cleanup()
    def retire(self):
        self.cleanup_id=self.source.enroll(self.full,{})
        self.source.run(self.cleanup_id)
    def assert_preserved(self):
        self.assertTrue((self.stage/'checked.m4b').exists())
        self.assertEqual(hashlib.sha256(Path(self.output['final_path']).read_bytes()).hexdigest(),self.output['sha256'])
    def test_success_discards_staging_preserves_originals_and_output(self):
        self.storage.run(self.job_id,include_recovery=True)
        self.assertEqual(list(self.stage.iterdir()),[])
        self.assertTrue((self.job/'ownership.json').exists())
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
        self.assertEqual(self.storage.status()[0]['state'],'completed')
        self.storage.run(self.job_id,include_recovery=True)
    def test_completed_retirement_discards_exact_recovery_and_correct_status(self):
        self.retire();self.storage.run(self.job_id,include_recovery=True)
        self.assertEqual(list((self.source.root/self.cleanup_id).iterdir()),[])
        receipt=self.source.status(self.job_id)
        self.assertEqual(receipt['recovery_bytes'],0);self.assertEqual(receipt['temporary_cleanup'],'completed')
        self.assertEqual(receipt['status'],'Originals removed; verified temporary recovery and working copies removed')
        self.assertFalse(receipt['restore_available'])
        with self.assertRaisesRegex(BoundaryError,'cannot be restored'):self.source.restore(self.cleanup_id)
    def test_invalid_output_preserves_copies(self):
        Path(self.output['final_path']).write_bytes(b'changed')
        with self.assertRaisesRegex(BoundaryError,'output bytes'):self.storage.run(self.job_id,include_recovery=True)
        self.assertTrue((self.stage/'checked.m4b').exists())
        self.assertEqual(self.storage.status()[0]['state'],'needs_attention')
    def test_pending_or_failed_audio_cannot_discard(self):
        for state in ('pending','running','needs attention'):
            self.queue._update(self.job_id,state=state)
            with self.assertRaisesRegex(BoundaryError,'completed'):self.storage.run(self.job_id,include_recovery=True)
            self.assert_preserved()
    def test_paused_source_removal_preserves_recovery_and_staging(self):
        self.cleanup_id=self.source.enroll(self.full,{});self.source.stop.set();self.source.run(self.cleanup_id);self.source.stop.clear()
        with self.assertRaisesRegex(BoundaryError,'incomplete'):self.storage.run(self.job_id,include_recovery=True)
        self.assert_preserved();self.assertEqual(len(list((self.source.root/self.cleanup_id).iterdir())),2)
    def test_changed_retained_source_preserves_staging(self):
        Path(self.sources[0]['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(BoundaryError,'source changed'):self.storage.run(self.job_id,include_recovery=True)
        self.assert_preserved()
    def test_unknown_staging_content_blocks_before_any_disposition(self):
        self.retire();(self.stage/'unique.txt').write_text('unique work')
        with self.assertRaisesRegex(BoundaryError,'Unknown staging'):self.storage.run(self.job_id,include_recovery=True)
        self.assert_preserved();self.assertEqual(len(list((self.source.root/self.cleanup_id).iterdir())),2)
    def test_unknown_recovery_content_blocks_before_any_disposition(self):
        self.retire();(self.source.root/self.cleanup_id/'unique.txt').write_text('keep')
        with self.assertRaisesRegex(BoundaryError,'Unknown recovery'):self.storage.run(self.job_id,include_recovery=True)
        self.assert_preserved()
    def test_hardlinked_copy_is_not_discarded(self):
        os.link(self.stage/'checked.m4b',self.base/'alias.m4b')
        with self.assertRaisesRegex(BoundaryError,'alias'):self.storage.run(self.job_id,include_recovery=True)
        self.assert_preserved()
    def test_nested_git_is_not_touched(self):
        (self.stage/'.git').mkdir()
        with self.assertRaisesRegex(BoundaryError,'Unknown staging'):self.storage.run(self.job_id,include_recovery=True)
        self.assert_preserved()
    def test_crash_after_disposition_reconciles_only_durable_intent(self):
        real=self.storage._file_state;failed=[]
        def crash(path,state):
            if state=='disposition_set' and not failed:
                failed.append(path);raise RuntimeError('simulated crash after native disposition')
            real(path,state)
        with patch.object(self.storage,'_file_state',side_effect=crash):
            with self.assertRaisesRegex(RuntimeError,'simulated'):self.storage.run(self.job_id,include_recovery=True)
        self.assertFalse(failed[0].exists());self.assertEqual(self.storage.status()[0]['state'],'needs_attention')
        self.storage.run(self.job_id,include_recovery=True)
        with connect(self.db) as db:self.assertEqual(db.execute('SELECT state FROM storage_cleanup_files WHERE path=?',(str(failed[0]),)).fetchone()['state'],'absent_after_intent')
        self.assertEqual(list(self.stage.iterdir()),[])
    def test_crash_before_disposition_preserves_changed_replacement(self):
        with patch.object(VerifiedFile,'dispose',side_effect=RuntimeError('simulated before disposition')):
            with self.assertRaisesRegex(RuntimeError,'simulated'):self.storage.run(self.job_id,include_recovery=True)
        p=next(p for p in self.stage.iterdir() if p.name.startswith('source'));p.write_bytes(b'unrelated replacement')
        with self.assertRaises(BoundaryError):self.storage.run(self.job_id,include_recovery=True)
        self.assertEqual(p.read_bytes(),b'unrelated replacement');self.assert_preserved()
    def test_verified_only_receipt_cannot_turn_unknown_absence_into_success(self):
        real=self.storage._dispose
        with patch.object(self.storage,'_dispose',side_effect=RuntimeError('before removal intent')):
            with self.assertRaises(RuntimeError):self.storage.run(self.job_id,include_recovery=True)
        p=next(self.stage.iterdir());p.unlink()
        with self.assertRaisesRegex(BoundaryError,'without verified removal intent'):self.storage.run(self.job_id,include_recovery=True)
        self.assertEqual(self.storage.status()[0]['state'],'needs_attention')
    def test_enrolled_policy_without_retirement_is_preserved(self):
        m=dict(self.manifest,cleanup_policy={'enabled':True});encoded=packed(m)
        with connect(self.db) as db:db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=? WHERE job_id=?',(encoded,hashlib.sha256(encoded.encode()).hexdigest(),self.job_id))
        with self.assertRaisesRegex(BoundaryError,'has not completed'):self.storage.run(self.job_id,include_recovery=True)
        self.assert_preserved()

    def test_known_name_substitutions_are_preserved(self):
        for name in ('checked.m4b','inputs.txt'):
            p=self.stage/name;original=p.read_bytes();p.write_bytes(b'UNIQUE USER CONTENT')
            with self.assertRaisesRegex(BoundaryError,'approved bytes'):self.storage.run(self.job_id,include_recovery=True)
            self.assertEqual(p.read_bytes(),b'UNIQUE USER CONTENT')
            self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
            p.write_bytes(original)
        p=self.stage/'compatible.m4b';p.write_bytes(b'producer original')
        self.output['validation']['staging_artifacts']['files'][p.name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
        self.queue._update(self.job_id,output=json.dumps(self.output));p.write_bytes(b'UNIQUE USER CONTENT')
        with self.assertRaisesRegex(BoundaryError,'approved bytes'):self.storage.run(self.job_id,include_recovery=True)
        self.assertEqual(p.read_bytes(),b'UNIQUE USER CONTENT')
    def test_unregistered_named_output_is_never_adopted(self):
        self.output['validation'].pop('staging_artifacts');self.queue._update(self.job_id,output=json.dumps(self.output))
        p=self.stage/'checked.m4b';p.write_bytes(b'UNIQUE USER CONTENT')
        with self.assertRaisesRegex(BoundaryError,'approved bytes'):self.storage.run(self.job_id,include_recovery=True)
        self.assertEqual(p.read_bytes(),b'UNIQUE USER CONTENT')
    def test_metadata_substitution_after_source_retirement_keeps_recovery(self):
        self.retire();(self.stage/'inputs.txt').write_bytes(b'UNIQUE USER CONTENT')
        with self.assertRaisesRegex(BoundaryError,'approved bytes'):self.storage.run(self.job_id,include_recovery=True)
        self.assertEqual(len(list((self.source.root/self.cleanup_id).iterdir())),2)
    def test_preflight_failure_keeps_complete_recovery_restorable(self):
        self.retire();(self.stage/'inputs.txt').write_bytes(b'UNIQUE USER CONTENT')
        with self.assertRaises(BoundaryError):self.storage.run(self.job_id,include_recovery=True)
        self.assertTrue(self.source.status(self.job_id)['restore_available'])
        self.source.restore(self.cleanup_id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))

if __name__=='__main__':unittest.main()
