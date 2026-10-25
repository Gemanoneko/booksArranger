import base64,contextlib,json,shutil,sqlite3,subprocess,tempfile,time,unittest
from unittest.mock import patch
from pathlib import Path
from scanner import Inventory,connect
from scan_wait import finish_scan
from merge_service import MergeService
from audio_pipeline import digest
from encoding_policy import PROFILE

AREA=Path(__file__).resolve().parents[1]/'scratch'/'merge-tests';AREA.mkdir(parents=True,exist_ok=True)
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')

class NativeMoveStartupFenceTests(unittest.TestCase):
    def test_pending_move_blocks_both_entry_points_before_recovery_writes(self):
        from types import SimpleNamespace
        from publication_locations import PublicationRefused
        for stage in ('rename_intent','renamed','location_committed','duplicate_cleanup_intent','duplicate_removed'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory(dir=AREA) as area:
                base=Path(area);database=base/'catalog.sqlite';cache=base/'must-not-exist'
                with contextlib.closing(sqlite3.connect(database)) as db,db:
                    db.executescript('CREATE TABLE output_relocations(publication_id TEXT,stage TEXT);CREATE TABLE migration_events(publication_id TEXT,outcome TEXT,to_stage TEXT);CREATE TABLE audio_jobs(job_id TEXT,state TEXT);CREATE TABLE scan_jobs(id TEXT,state TEXT);')
                    db.execute('INSERT INTO output_relocations VALUES(?,?)',('owned-publication',stage))
                    db.execute('INSERT INTO migration_events VALUES(?,?,?)',('owned-publication','transition','duplicate_cleanup_intent' if stage.startswith('duplicate') else 'rename_intent'))
                    db.execute('INSERT INTO audio_jobs VALUES(?,?)',('saved-running-job','running'))
                    db.execute('INSERT INTO scan_jobs VALUES(?,?)',('saved-running-scan','running'))
                before=database.read_bytes()
                for entry in (lambda:Inventory(database,{}),lambda:MergeService(SimpleNamespace(database=database),cache)):
                    with self.assertRaises(PublicationRefused) as caught:entry()
                    self.assertEqual(caught.exception.code,'native_move_pending')
                    self.assertEqual(database.read_bytes(),before)
                    self.assertFalse(cache.exists())
                with contextlib.closing(sqlite3.connect(database)) as db:
                    self.assertEqual(db.execute('SELECT * FROM audio_jobs').fetchall(),[('saved-running-job','running')])
                    self.assertEqual(db.execute('SELECT * FROM scan_jobs').fetchall(),[('saved-running-scan','running')])

    def test_readonly_fence_preserves_new_and_legacy_catalogs(self):
        from publication_locations import require_no_pending_moves
        with tempfile.TemporaryDirectory(dir=AREA) as area:
            database=Path(area)/'new.sqlite';require_no_pending_moves(database);self.assertFalse(database.exists())
            with contextlib.closing(sqlite3.connect(database)) as db,db:db.execute('CREATE TABLE output_relocations(old_legacy_column TEXT)')
            before=database.read_bytes();require_no_pending_moves(database);self.assertEqual(database.read_bytes(),before)

class MergeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.base=Path(self.temp.name)
        self.audio=self.base/'audio';self.audio.mkdir();folder=self.audio/'Book';folder.mkdir()
        self.sources=[]
        for i in (1,2):
            path=folder/(str(i)+'.mp3')
            subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=0.3','-ar','44100','-ac','1','-c:a','libmp3lame','-b:a','128k',str(path)],check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.sources.append(path)
        (folder/'cover.png').write_bytes(PNG)
        roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        def reader(path,kind,stop):return {'title':'Book','track_title':'Chapter '+Path(path).stem,'tags':{'album':'Book','comment':'Original comment'},'probe':{'format':{'duration':'0.3'}},'method':'private fixture'}
        self.inv=Inventory(self.base/'catalog.sqlite3',roots,reader);self.inv.launch('Audiobooks');finish_scan(self.inv)
        self.service=MergeService(self.inv,self.base/'cache')
        self.review={'title':'Book','author':'Author Name','canonical_author':'Name Author','original_language':'Other','series':'Series','number':'2','genre':'Fantasy','multi_author':False,'anthology':False,'narrator':'Reader','topic':''}
        self.hashes=[digest(p) for p in self.sources]

    def tearDown(self):
        self.service.close();self.temp.cleanup()

    def ready(self):
        r=self.service.reviews;row=r.page()['rows'][0];row=r.covers('Audiobooks',row['id'],row['revision'])
        row=r.save('Audiobooks',row['id'],row['revision'],self.review,True,'Fixture bibliography establishes identity and author role',cover_id=row['cover_choices'][0]['id'])
        return r.tracks('Audiobooks',row['id'],row['revision'],row['track_order'],row['included'],True,True,True,evidence_note='All fixture sources have one recording, exact intended membership and track order')

    def wait(self):
        deadline=time.monotonic()+30
        while self.service.jobs._thread and self.service.jobs._thread.is_alive():
            if time.monotonic()>deadline:self.fail('Private merge exceeded test deadline')
            time.sleep(.05)
        return self.service.jobs.status()

    def test_approved_totals_and_converted_filter_share_cleanup_success(self):
        row=self.ready();initial=self.service.state()
        self.assertEqual(initial['approved_total'],1);self.assertEqual(initial['converted_total'],0)
        self.assertEqual(self.service.reviews.page(status='converted')['total'],0)
        self.service.create('Audiobooks',row['id'],row['revision']);status=self.wait();job=status['jobs'][0]
        final=self.service.state();self.assertEqual(final['converted_total'],1,final)
        self.assertEqual(final['approved_total'],1);filtered=self.service.reviews.page(status='converted')
        self.assertEqual(filtered['total'],1);self.assertEqual(filtered['rows'][0]['id'],row['id'])
        self.assertEqual(self.service.reviews.page(status='converted',search='not-present')['total'],0)
        self.assertEqual(self.service.reviews.page(status='converted',offset=1)['rows'],[])
        # A duplicate durable job record cannot inflate a unique candidate count.
        with patch.object(self.service.jobs,'status',return_value={**status,'jobs':[job,job]}):
            self.assertEqual(self.service.state()['converted_total'],1)
        with patch('merge_service.digest',side_effect=AssertionError('Progress polls must not hash media')):
            self.assertEqual(self.service.state()['converted_total'],1)
            self.assertEqual(self.service.reviews.page(status='converted')['total'],1)
        real=self.service.storage_cleanup.status()
        with patch.object(self.service.storage_cleanup,'status',return_value=[{**r,'state':'needs_attention','reason':'fixture cleanup blocked'} for r in real]):
            self.assertEqual(self.service.state()['converted_total'],0)
            self.assertEqual(self.service.reviews.page(status='created')['total'],1)
            self.assertEqual(self.service.reviews.page(status='converted')['total'],0)
        with connect(self.inv.database) as db:db.execute('UPDATE candidate_context SET revision=revision-1 WHERE id=?',(row['id'],))
        self.assertEqual(self.service.state()['approved_total'],0);self.assertEqual(self.service.reviews.page(status='converted')['total'],0)

    def test_review_to_validated_file_and_restart_reuse(self):
        row=self.ready();manifest=self.service.reviews.build_manifest('Audiobooks',row['id'],row['revision'])
        self.assertEqual(manifest['profile'],PROFILE)
        self.assertEqual(manifest['encoding_policy']['selection'],'highest_verified_mp3_stream_bitrate')
        self.assertNotIn('max_bytes',manifest['encoding_policy'])
        self.service.create('Audiobooks',row['id'],row['revision']);status=self.wait()
        self.assertEqual(status['completed'],1,status)
        output=status['jobs'][0]['output'];self.assertTrue(Path(output['final_path']).exists())
        self.assertEqual(output['validation']['profile'],PROFILE)
        self.assertEqual(output['validation']['encoding']['channels'],1)
        self.assertEqual(output['validation']['encoding']['bitrate'],128000)
        self.assertEqual(output['validation']['encoding']['sample_rate'],44100)
        self.assertTrue(self.service._output_valid(output));self.assertEqual(output['validation']['tags']['track'],'2')
        self.service.close() # Quiesce automatic HOURS=0 recovery purge before inspecting its actual outcome.
        cleanup=self.service.cleanup.status(status['jobs'][0]['job_id'])
        self.assertEqual(cleanup['state'],'completed',cleanup)
        self.assertEqual(cleanup['removed'],len(self.sources))
        self.assertTrue(all(not p.exists() for p in self.sources))
        self.assertEqual(cleanup['temporary_cleanup'],'completed')
        self.assertIn(cleanup['recovery']['state'],{'retained','deleted'},cleanup)
        if cleanup['recovery']['state']=='deleted':
            self.assertEqual(cleanup['recovery_bytes'],0);self.assertFalse(cleanup['restore_available'])
            recovery=self.service.cleanup.root/cleanup['id']
            self.assertFalse(recovery.exists() and any(recovery.iterdir()))
        else:
            self.assertGreater(cleanup['recovery_bytes'],0);self.assertTrue(cleanup['restore_available'])
            self.assertEqual(len(list((self.service.cleanup.root/cleanup['id']).iterdir())),len(self.sources))
        attempts=list((self.service.stage_root/status['jobs'][0]['job_id']).iterdir())
        self.assertTrue(all(not list(p.iterdir()) for p in attempts if p.is_dir()))
        self.assertTrue(output['validation']['staging_artifacts']['files'])
        self.assertEqual(self.service.candidate_status(row['id'])['state'],'Audiobook created')
        self.service.close();self.service=MergeService(self.inv,self.base/'cache')
        self.assertEqual(self.service.jobs.status()['completed'],1)
        self.inv.launch('Audiobooks');finish_scan(self.inv)
        with connect(self.inv.database) as db:
            created=db.execute('SELECT metadata FROM files WHERE path=?',(output['final_path'],)).fetchone()
            owned=db.execute("SELECT job_id,kind,sha256,size FROM owned_artifacts WHERE path=?",(output['final_path'],)).fetchone()
        # Owned outputs are excluded before new metadata discovery. A legacy
        # indexed row, if present, must also carry its exclusion marker.
        self.assertEqual(tuple(owned),(output['job_id'],'output',output['sha256'],output['size']))
        if created is not None:self.assertIn('arranger_output',json.loads(created[0]))
        self.assertEqual(self.service.reviews.page()['total'],1)
        deadline=time.monotonic()+5
        while self.service.current_audiobook(row['id'])['state']=='verifying' and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(self.service.current_audiobook(row['id'])['state'],'verified')
        inspected=self.service.inspect('Audiobooks','candidates',row['id'])['inspector']
        self.assertIn('Recovery location',[f['label'] for f in inspected['sections'][-1]['facts']])
        self.assertFalse(self.service.reviews.page()['rows'][0]['creation']['can_create'])

    def test_changed_review_blocks_frozen_job(self):
        row=self.ready();manifest=self.service.reviews.build_manifest('Audiobooks',row['id'],row['revision'])
        self.service.jobs.enqueue(manifest)
        self.service.reviews.save('Audiobooks',row['id'],row['revision'],dict(self.review,title='Changed'),False,'Changed fixture title needs new review')
        self.service.jobs.resume();status=self.wait();self.assertEqual(status['failed'],1)
        self.assertFalse(Path(manifest['destination']).exists())

    def test_unreviewed_book_cannot_enqueue(self):
        row=self.service.reviews.page()['rows'][0]
        inspector=self.service.inspect('Audiobooks','candidates',row['id'])['inspector']
        self.assertEqual(inspector['sections'][1]['kind'],'draft')
        with self.assertRaises(ValueError):self.service.create('Audiobooks',row['id'],row['revision'])
        self.assertFalse(self.service.jobs.status()['jobs'])

    def test_inspection_source_cover_and_preview_roles_are_distinct(self):
        row=self.ready();inspector=self.service.inspect('Audiobooks','candidates',row['id'])['inspector']
        self.assertEqual([s['kind'] for s in inspector['sections']],['source','approved'])
        self.assertFalse(inspector['output_folder_available'])
        self.assertTrue(inspector['sections'][0]['member_values'])
        self.assertEqual(inspector['sections'][1]['cover']['id'],row['selected_cover']['id'])
        image=self.sources[0].parent/'cover.png';id=self.service.file_id('Audiobooks',str(image))
        file=self.service.inspect('Audiobooks','files',id)['inspector']
        cover=file['sections'][0]['cover'];self.assertIn('id',cover)
        self.assertEqual(self.service.reviews.cover_bytes(cover['id']),PNG)

    def test_folder_action_uses_opaque_catalog_identity_and_mock_dispatch(self):
        row=self.service.reviews.page()['rows'][0]
        with patch.object(self.service,'dispatch_folder') as dispatch:
            self.assertEqual(self.service.open_folder('Audiobooks','candidates',row['id']),{'opened':True})
            dispatch.assert_called_once_with(str(self.sources[0].parent))
            with self.assertRaises(ValueError):self.service.open_folder('Audiobooks','candidates',row['id'],'source',str(self.base))
            with self.assertRaises(ValueError):self.service.open_folder('Ebooks','files',self.service.file_id('Audiobooks',str(self.sources[0])))
            with self.assertRaises(ValueError):self.service.open_folder('Audiobooks','candidates',row['id'],'output')
            self.assertEqual(dispatch.call_count,1)

if __name__=='__main__':unittest.main()
