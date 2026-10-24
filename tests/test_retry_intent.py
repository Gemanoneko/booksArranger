"""Real legacy approval -> explicit new hierarchy intent, retaining old job bytes."""
import copy,json,os,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import test_merge_service as fixtures
from scanner import connect,Inventory
from merge_service import MergeService
from retry_intent import bind,validate,digest

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'retry-intent'
class RetryIntent(unittest.TestCase):
    ready=fixtures.MergeTests.ready;wait=fixtures.MergeTests.wait
    def setUp(self):
        AREA.mkdir(parents=True,exist_ok=True)
        def retained(*args,**kwargs):
            kwargs['dir']=AREA;return SimpleNamespace(name=tempfile.mkdtemp(*args,**kwargs),cleanup=lambda:None)
        with patch.object(fixtures,'AREA',AREA),patch.object(fixtures.tempfile,'TemporaryDirectory',side_effect=retained):fixtures.MergeTests.setUp(self)
    def tearDown(self):self.service.close()
    def parent(self):
        row=self.ready()
        # Explicit pre-v2 persisted-review fixture, preserving the user's accepted
        # identity and all real source/order/cover evidence across this upgrade.
        with connect(self.inv.database) as db:
            review=json.loads(db.execute('SELECT review FROM book_groups WHERE id=?',(row['id'],)).fetchone()[0]);review.pop('organization_policy',None);review.pop('universe',None)
            db.execute('UPDATE book_groups SET review=? WHERE id=?',(json.dumps(review),row['id']))
        manifest=self.service.reviews.build_manifest('Audiobooks',row['id'],row['revision']);manifest.pop('output_root');job=self.service.jobs.enqueue(manifest);self.service.jobs._update(job,state='needs attention',reason='Admission hold')
        parent=self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job,))[0]
        return row,parent
    def activate(self,target):
        target.mkdir();additional=self.base/'OLD_Audiobooks';additional.mkdir()
        roots=dict(self.inv.roots);database=self.inv.database;self.service.close()
        self.inv=Inventory(database,roots,audiobook_sources=[roots['Audiobooks'],str(additional)],output_root=str(target))
        self.service=MergeService(self.inv,self.base/'cache')
        self.assertEqual(len(self.inv.source_roots('Audiobooks')),2)
    def test_legacy_retry_actual_child_uses_sorted_hierarchy_and_ready(self):
        row,parent=self.parent();target=self.base/'Audiobooks Sorted';self.activate(target)
        admitted=self.service._admit_new_retry(parent);self.assertTrue(admitted['requeued'],admitted);self.assertNotEqual(admitted['job_id'],parent['job_id'])
        child=self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(admitted['job_id'],))[0];manifest=json.loads(child['manifest'])
        self.assertEqual(Path(manifest['destination']).parent,target/'Author Name'/'Series');self.assertTrue(self.service._guard(manifest))
        self.service.jobs.resume();status=self.wait();created=next(job for job in status['jobs'] if job['job_id']==admitted['job_id']);self.assertEqual(created['state'],'completed',status)
        self.assertEqual(self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],))[0],parent)
        self.assertTrue(Path(created['output']['final_path']).is_file());self.assertEqual(self.service.progress_books()['converted'],1)
        self.assertEqual(self.service.current_audiobook(row['id'])['state'],'verified')
    def recovery_child(self):
        from producer_recovery import CLAIM
        from source_cleanup import packed
        from audio_pipeline import digest as file_digest
        row,parent=self.parent();job=parent['job_id'];attempt=str(uuid.uuid4());manifest=json.loads(parent['manifest'])
        self.service.jobs._update(job,state='running',attempt_id=attempt)
        self.service.working.begin(dict(manifest,attempt_id=attempt))
        old=self.service.stage_root/job/attempt;old.mkdir(parents=True);(old.parent/'ownership.json').write_text(packed({'job_id':job,'manifest':manifest}),encoding='utf8')
        old_file=old/'source00000.mp3';self.service.working.planned(old,old_file);old_file.write_bytes(self.sources[0].read_bytes())
        self.service.jobs._update(job,state='needs attention',reason='Working cleanup requires an unclosed producer')
        parent=self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job,))[0]
        target=self.base/'sorted-recovery';self.activate(target)
        recovery=self.service.producer_recovery;clock=[100000]
        recovery.platform=lambda:{'schema':'books-windows-startup-v1','machine_guid':'private-fixture','computer':'private','windows_directory':'C:/Windows','system_volume_serial':'fixture','uptime_ms':clock[0]}
        recovery.record_origin(job,{'actor':'user','claim':CLAIM,'evidence':'Explicit synthetic local history; not a production human fact'})
        recovery.prepare(job);clock[0]=5000
        before=old_file.read_bytes()
        admitted=self.service._admit_new_retry(parent,recovery=True);self.assertTrue(admitted['requeued'],admitted)
        return row,parent,old_file,before,admitted,attempt

    def test_later_boot_recovery_fresh_conversion_retains_old_namespace_and_sources(self):
        from audio_pipeline import digest as file_digest
        row,parent,old_file,before,admitted,attempt=self.recovery_child()
        original=self.service._run_media;attempted=[]
        def guarded(*args,**kwargs):
            with self.assertRaises(OSError):old_file.write_bytes(b'must be denied while actual child runs')
            attempted.append(True);return original(*args,**kwargs)
        with patch.object(self.service,'_run_media',side_effect=guarded):
            self.service.jobs.resume();status=self.wait()
        self.assertEqual(attempted,[True]);created=next(item for item in status['jobs'] if item['job_id']==admitted['job_id']);self.assertEqual(created['state'],'completed',status)
        self.assertNotEqual(created['job_id'],parent['job_id']);self.assertNotEqual(created['attempt_id'],attempt)
        self.assertEqual(old_file.read_bytes(),before);self.assertEqual([file_digest(path) for path in self.sources],self.hashes)
        self.assertEqual(self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],))[0],parent)
        self.assertFalse(created['manifest']['cleanup_policy']['enabled']);self.assertIsNone(self.service.cleanup.status(created['job_id']))
        self.assertEqual(self.service.progress_books()['converted'],1);self.assertEqual(self.service.current_audiobook(row['id'])['state'],'verified')
        page=self.service.reviews.page()['rows'][0];self.assertEqual(page['producer_recovery_retained']['count'],1)
        with self.assertRaisesRegex(ValueError,'retained'):self.service.working.retire(parent['job_id'],attempt)

    def test_queued_recovery_child_refuses_old_namespace_drift_at_actual_admission(self):
        from audio_pipeline import digest as file_digest
        row,parent,old_file,before,admitted,attempt=self.recovery_child()
        old_file.write_bytes(b'external drift after enqueue; retain it')
        self.service.jobs.resume();status=self.wait();child=next(item for item in status['jobs'] if item['job_id']==admitted['job_id'])
        self.assertEqual(child['state'],'needs attention');self.assertIsNone(child['attempt_id'])
        self.assertFalse((self.service.stage_root/child['job_id']).exists());self.assertEqual(old_file.read_bytes(),b'external drift after enqueue; retain it')
        self.assertEqual([file_digest(path) for path in self.sources],self.hashes)
        self.assertEqual(self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],))[0],parent)

    def test_bound_user_universe_migration_keeps_current_view_and_ready(self):
        from catalog_owner import catalog_lock
        from migration_planning import prepare,write_plan
        from migration_operation import MigrationOperation
        from publication_locations import _digest
        from audio_pipeline import digest as file_digest
        row=self.ready();self.service.create('Audiobooks',row['id'],row['revision']);status=self.wait();parent=status['jobs'][0];self.assertEqual(parent['state'],'completed',status)
        with connect(self.inv.database) as db:
            raw=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],)).fetchone());saved=dict(db.execute('SELECT * FROM book_groups WHERE id=?',(row['id'],)).fetchone())
        decision={'candidate_id':row['id'],'fingerprint':saved['fingerprint'],'review_sha256':_digest(json.loads(saved['review'])),'actor':'user','evidence':'Explicit private-fixture universe routing choice','values':{'universe':'Fixture Universe'}}
        original=Path(parent['output']['final_path']);old_hash=file_digest(original);target=self.base/'Sorted Universe';target.mkdir();roots=dict(self.inv.roots);self.service.close()
        with catalog_lock(self.inv.database,dict(roots,**{'Audiobook output':str(target)})):plan=prepare(self.inv.database,roots,[roots['Audiobooks']],str(target),[decision])
        self.assertEqual(plan['held'],[],plan);self.assertEqual(len(plan['publications']),1);entry=plan['publications'][0];self.assertEqual(Path(entry['destination']).parent,target/'Fixture Universe'/'Series')
        plans=AREA/'reviewed-route-plans';plans.mkdir(exist_ok=True);receipt=write_plan(plans/(str(uuid.uuid4())+'.json'),plan)
        result=MigrationOperation(self.inv.database,plan['roots'],receipt['plan'],receipt['sha256']).run(entry['publication_id']);self.assertEqual(result['outcome'],'moved');self.assertFalse(original.exists());self.assertEqual(file_digest(entry['destination']),old_hash)
        self.inv=Inventory(self.inv.database,roots,output_root=str(target));self.service=MergeService(self.inv,self.base/'cache')
        self.service.start_published_check();self.service.jobs._verifier.join(5)
        self.assertFalse(self.service.jobs._verifier.is_alive())
        self.assertEqual(self.service.current_audiobook(row['id'])['state'],'verified');self.assertEqual(self.service.current_audiobook(row['id'])['path'],entry['destination']);self.assertEqual(self.service.progress_books()['converted'],1)
        page=self.service.reviews.page(status='converted');self.assertEqual(page['total'],1);self.assertEqual(page['rows'][0]['current_audiobook']['path'],entry['destination'])
        with connect(self.inv.database) as db:self.assertEqual(dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],)).fetchone()),raw)

    def test_changed_identity_is_not_routing_authorization(self):
        row,parent=self.parent();fresh=self.service.reviews.build_manifest('Audiobooks',row['id'],row['revision'],allow_existing_job=True);fresh['metadata']['title']='Different work'
        with self.assertRaisesRegex(ValueError,'changed'):bind(parent,fresh,str(self.base/'sorted'))
    def test_changed_destination_and_retention_are_not_generic_waivers(self):
        row,parent=self.parent();fresh=self.service.reviews.build_manifest('Audiobooks',row['id'],row['revision'],allow_existing_job=True);child=bind(parent,fresh,str(self.base/'sorted'))
        self.assertTrue(validate(child,fresh,str(self.base/'sorted')))
        altered=copy.deepcopy(child);altered['destination']=str(self.base/'elsewhere.m4b');self.assertFalse(validate(altered,fresh,str(self.base/'sorted')))
        altered=copy.deepcopy(child);altered['cleanup_policy']['enabled']=False;self.assertFalse(validate(altered,fresh,str(self.base/'sorted')))

# 0.21.3: this module's fixtures publish inside their own library; see sorted_fixture (Sergei's deletion rule).
def setUpModule():
    global _sorted_fixture
    from sorted_fixture import patch_merge_service
    _sorted_fixture = patch_merge_service()


def tearDownModule():
    _sorted_fixture.stop()

if __name__=='__main__':unittest.main()
