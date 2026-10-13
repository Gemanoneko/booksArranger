"""Real private publication, blocked retirement, explicit retry and pressure fixtures."""
import errno,json,shutil,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
import test_automatic_media as fixtures
from native_io import BoundaryError
from merge_service import MergeService
from scanner import connect

class WorkingLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.AutomaticMediaTests('test_confident_no_manual_form_to_verified_chapters_retained_recovery');self.f.setUp()
    def tearDown(self):self.f.tearDown()
    def test_publication_cleans_working_before_blocked_retirement_and_ready_stays_false(self):
        observed=[]
        def blocked(cleanup_id):
            row=self.f.service.cleanup._rows('SELECT job_id FROM source_cleanup WHERE id=?',(cleanup_id,))[0]
            job=next(j for j in self.f.service.jobs.status()['jobs'] if j['job_id']==row['job_id'])
            stage=self.f.service.stage_root/job['job_id']/job['output']['validation']['staging_artifacts']['attempt_id']
            observed.append(stage)
            self.assertEqual(list(stage.glob('normalized*.wav')),[])
            self.assertTrue(all((stage/f'source{i:05d}.mp3').is_file() for i in range(2)))
            raise BoundaryError('private retirement hold')
        row,result=self.f.result()
        with patch.object(self.f.service.cleanup,'run',side_effect=blocked):
            _,job_id=self.f.service.approve_automatic(row,result,threading.Event(),self.f.client);self.f.wait()
        self.assertTrue(observed);self.assertTrue(all(source.is_file() for source in self.f.sources))
        self.assertEqual(self.f.service.cleanup.status(job_id)['state'],'needs_attention')
        self.assertEqual(self.f.service.state()['converted_total'],0)
        self.assertFalse(self.f.service.storage_cleanup.working_pending(job_id))
        self.assertTrue(Path(self.f.service.jobs.status()['jobs'][0]['output']['final_path']).is_file())
    def test_startup_does_not_cleanup_or_start_but_explicit_resume_retries_published_attention(self):
        row,result=self.f.result()
        with patch.object(self.f.service.storage_cleanup,'working_files',side_effect=BoundaryError('private working interruption')),patch.object(self.f.service.cleanup,'run',side_effect=BoundaryError('private retirement hold')):
            _,job_id=self.f.service.approve_automatic(row,result,threading.Event(),self.f.client);self.f.wait()
        job=self.f.service.jobs.status()['jobs'][0];stage=self.f.service.stage_root/job_id/job['output']['validation']['staging_artifacts']['attempt_id']
        self.assertTrue(list(stage.glob('normalized*.wav')))
        self.f.service.close()
        with patch('storage_cleanup.StorageCleanup.working_files',side_effect=AssertionError('startup must remain inactive')):
            self.f.service=MergeService(self.f.inv,self.f.base/'cache')
        self.assertTrue(list(stage.glob('normalized*.wav')));self.assertFalse(self.f.service.jobs._thread)
        self.f.service.resume();self.f.wait()
        self.assertEqual(list(stage.glob('normalized*.wav')),[])
        self.assertEqual(self.f.service.cleanup.status(job_id)['state'],'needs_attention')
        self.assertTrue(all(source.exists() for source in self.f.sources));self.assertEqual(self.f.service.state()['converted_total'],0)
    def test_short_space_holds_before_snapshots_normalization_or_output(self):
        row,result=self.f.result()
        def no_space(path):return shutil._ntuple_diskusage(100,100,0)
        with patch('audio_pipeline.shutil.disk_usage',side_effect=no_space):
            _,job_id=self.f.service.approve_automatic(row,result,threading.Event(),self.f.client);self.f.wait()
        job=self.f.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'needs attention')
        self.assertIn('space',job['reason']);self.assertTrue(all(source.exists() for source in self.f.sources));self.assertEqual(job['output'],None)
        stage=self.f.service.stage_root/job_id/job['attempt_id']
        self.assertEqual(list(stage.glob('source*.mp3')),[]);self.assertEqual(list(stage.glob('normalized*.wav')),[]);self.assertEqual(list(stage.glob('*.m4b')),[])
        self.assertTrue(self.f.service.jobs._stop.is_set());self.assertFalse(self.f.service.automatic.next_retry_at)
    def test_destination_space_hold_prevents_source_copies(self):
        row,result=self.f.result();real=shutil.disk_usage
        def pressure(path):
            path=Path(path)
            return shutil._ntuple_diskusage(100,100,0) if path==self.f.audio else real(path)
        with patch('audio_pipeline.shutil.disk_usage',side_effect=pressure):
            _,job_id=self.f.service.approve_automatic(row,result,threading.Event(),self.f.client);self.f.wait()
        job=self.f.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'needs attention')
        self.assertIn('destination space',job['reason']);stage=self.f.service.stage_root/job_id/job['attempt_id']
        self.assertEqual(list(stage.glob('source*.mp3')),[]);self.assertTrue(all(source.exists() for source in self.f.sources))

if __name__=='__main__':unittest.main()
