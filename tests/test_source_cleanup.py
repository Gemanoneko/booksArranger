"""Private Windows fixtures only: actual handle removal and recoverability."""
import contextlib
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_cleanup import CleanupJobs, packed
from native_io import DirectoryBoundary, VerifiedFile, BoundaryError
from scanner import connect

class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cleanup-',dir=Path(__file__).resolve().parents[1]/'scratch')
        self.base=Path(self.temp.name);self.library=self.base/'library';self.library.mkdir();self.db=self.base/'catalog.sqlite3';self.good=True
        self.sources=[]
        for i in range(2):
            p=self.library/(str(i)+'.mp3');p.write_bytes(bytes([65+i])*2048);stat=p.stat()
            self.sources.append({'path':str(p),'size':stat.st_size,'modified':str(stat.st_mtime_ns),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        final=self.library/'book.m4b';final.write_bytes(b'validated fixture output')
        with DirectoryBoundary(self.library,final.parent) as boundary:identity=boundary.identities
        self.job={'job_id':'test','state':'completed','manifest':{'root':str(self.library),'sources':self.sources,'cover':{'path':str(final),'sha256':hashlib.sha256(final.read_bytes()).hexdigest()}},
            'output':{'final_path':str(final),'size':final.stat().st_size,'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'parent_identity':identity,'validation':{'passed':True}}}
        self.job['manifest'].update(profile='fixture',metadata={'title':'Fixture','canonical_author':'Author'},chapters=[])
        self.job['output']['validation'].update(checks='Output checks passed',profile='fixture',sha256=self.job['output']['sha256'],size=final.stat().st_size,
            tags={'media_type':'2','title':'Fixture','artist':'Author'},source_pcm_frames=[100,100],source_pcm_rate=100,decoded_duration=2,duration_tolerance=.01,chapters=[])
        with connect(self.db) as db:db.execute('CREATE TABLE owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER)')
        self.worker=CleanupJobs(self.db,self.base/'recovery',lambda db,intent:self.good,contextlib.nullcontext)
        self.id=self.worker.enroll(self.job,{})
    def tearDown(self):
        self.worker.close();self.temp.cleanup()
    def test_actual_removal_and_exact_restore(self):
        self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['removed'],2)
        self.assertTrue(all(not Path(s['path']).exists() for s in self.sources))
        self.worker.restore(self.id)
        for s in self.sources:
            p=Path(s['path']);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),s['sha256']);self.assertEqual(p.stat().st_mtime_ns,int(s['modified']))
    def test_output_change_preserves_all_originals(self):
        Path(self.job['output']['final_path']).write_bytes(b'changed')
        with self.assertRaises(BoundaryError):self.worker.run(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_changed_review_blocks_before_delete(self):
        self.good=False
        with self.assertRaises(BoundaryError):self.worker.run(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_pause_after_all_backups_before_first_delete(self):
        self.worker.stop.set();self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['state'],'paused')
        self.assertEqual(len(list((self.base/'recovery'/self.id).glob('*.mp3'))),2)
        self.worker.stop.clear();self.worker.run(self.id);self.assertEqual(self.worker.status('test')['removed'],2)
    def test_native_mutation_denied_while_held(self):
        p=Path(self.sources[0]['path'])
        with DirectoryBoundary(self.library,p.parent),VerifiedFile(p,delete=True) as held:
            with self.assertRaises(PermissionError):p.write_bytes(b'wrong')
            held.dispose()
        self.assertFalse(p.exists())
    def test_unknown_disposition_restorable_without_false_success(self):
        self.worker.stop.set();self.worker.run(self.id);self.worker.stop.clear()
        s=self.sources[0]
        with connect(self.db) as db:db.execute("UPDATE cleanup_members SET state='removal_intended' WHERE cleanup_id=? AND path=?",(self.id,s['path']))
        with DirectoryBoundary(self.library,Path(s['path']).parent),VerifiedFile(s['path'],delete=True) as held:held.dispose()
        with self.assertRaisesRegex(BoundaryError,'unknown outcome'):self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['removed'],0)
        self.worker.restore(self.id);self.assertTrue(Path(s['path']).exists())
    def test_restore_commit_crash_reconciles_exact_owned_identity(self):
        self.worker.run(self.id);original=self.worker._restored
        def crash(id,path):raise RuntimeError('simulated after publication')
        self.worker._restored=crash
        with self.assertRaises(RuntimeError):self.worker.restore(self.id)
        self.worker._restored=original;self.worker.restore(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_restore_collision_preserves_replacement(self):
        self.worker.run(self.id);p=Path(self.sources[0]['path']);p.write_bytes(b'unrelated')
        with self.assertRaises(FileExistsError):self.worker.restore(self.id)
        self.assertEqual(p.read_bytes(),b'unrelated')
    def test_all_backups_flush_before_any_source_removed(self):
        real=VerifiedFile.flush;calls=[]
        def failed_second(handle):
            calls.append(handle.path)
            if len(calls)==2:raise BoundaryError('simulated storage flush failure')
            return real(handle)
        with patch.object(VerifiedFile,'flush',failed_second):
            with self.assertRaisesRegex(BoundaryError,'flush failure'):self.worker.run(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_reused_backups_must_flush_again(self):
        self.worker.stop.set();self.worker.run(self.id);self.worker.stop.clear()
        with patch.object(VerifiedFile,'flush',side_effect=BoundaryError('reused flush denied')):
            with self.assertRaisesRegex(BoundaryError,'reused flush'):self.worker.run(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_hardlink_alias_refused_before_removal(self):
        import os
        os.link(self.sources[0]['path'],self.library/'other-name.mp3')
        with self.assertRaisesRegex(BoundaryError,'alias layout'):self.worker.run(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_missing_full_validation_cannot_enroll(self):
        changed=json.loads(packed(self.job));changed['job_id']='another';changed['output']['validation'].pop('source_pcm_frames')
        with self.assertRaisesRegex(ValueError,'decoded-audio'):self.worker.enroll(changed,{})
    def test_selected_cleanup_does_not_drain_other_work_or_encode(self):
        from unittest.mock import Mock
        other=json.loads(packed(self.job));other['job_id']='other';other_id=self.worker.enroll(other,{})
        called=[];self.worker.run=lambda id:called.append(id);self.worker.after_drain=Mock()
        self.worker.resume([self.id],follow_audio=False);self.worker.thread.join(5)
        self.assertEqual(called,[self.id]);self.worker.after_drain.assert_not_called()
        self.assertEqual(self.worker.status('other')['state'],'waiting')

if __name__=='__main__':unittest.main()
