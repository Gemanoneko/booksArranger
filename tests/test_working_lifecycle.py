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
        # v0.16.7: no normalized WAVs exist any more; the generated M4B candidates are the held working files.
        self.assertTrue(list(stage.glob('*.m4b')))
        self.f.service.close()
        with patch('storage_cleanup.StorageCleanup.working_files',side_effect=AssertionError('startup must remain inactive')):
            self.f.service=MergeService(self.f.inv,self.f.base/'cache')
        self.assertTrue(list(stage.glob('*.m4b')));self.assertFalse(self.f.service.jobs._thread)
        self.f.service.resume();self.f.wait()
        self.assertEqual(list(stage.glob('*.m4b')),[]);self.assertEqual(list(stage.glob('normalized*.wav')),[])
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


# 0.21.3: this module's fixtures publish inside their own library; see sorted_fixture (Sergei's deletion rule).
def setUpModule():
    global _sorted_fixture
    from sorted_fixture import patch_merge_service
    _sorted_fixture = patch_merge_service()


def tearDownModule():
    _sorted_fixture.stop()

class ReferenceSearchTests(unittest.TestCase):
    """Ruling 75a: the after-conversion reference check finds candidate rows in SQL. Every row the old full scan flags
    (normalized(packed(row)) holds normalized(path)) must be among them; the decision itself is unchanged."""
    def setUp(self):
        import tempfile,uuid as uuid_module
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'scratch');self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/'refs.sqlite3';self.job=str(uuid_module.uuid4());self.attempt=str(uuid_module.uuid4())
        self.path='C:\\Users\\Sergei\\AppData\\Local\\Books Arranger\\data\\merge-cache\\audio-staging\\'+self.job+'\\'+self.attempt+'\\source00000.m4b'
        self.sql('CREATE TABLE owned_artifacts(path,job_id,kind,sha256,size)')
    def sql(self,statement,values=(),many=False,rows=False,call=None):
        import contextlib,sqlite3
        with contextlib.closing(sqlite3.connect(self.db)) as db:
            db.row_factory=sqlite3.Row
            if call:return call(db)
            result=db.executemany(statement,values) if many else db.execute(statement,values)
            found=[dict(r) for r in result] if rows else None
            db.commit()
            return found
    def rows(self):
        import random
        p=self.path;q=json.dumps
        hits=[p,p.upper(),p.replace('\\','/'),q({'path':p}),q(q({'path':p})),'prefix '+p+' suffix',p.replace('\\','\\\\\\\\'),
              q({'nested':[{'s':p}]},ensure_ascii=False),p.replace('source','SOURCE'),
              p.replace('Local','LOCAL').replace(self.attempt,self.attempt.upper())]
        # Shapes only the old normalization sees through: control characters (json escapes them), a NUL, and characters
        # whose casefold is ASCII: the Kelvin sign is 'k', the ff ligature is 'ff', long s is 's'.
        kelvin,ligature,long_s=chr(0x212a),chr(0xfb00),chr(0x17f)
        tricky=[p+'\x1f',p+'\x00tail','\x01'+p,p.replace('Books','Boo'+kelvin+'s'),p.replace('source',''+long_s+'ource'),
                p.replace('Books','Boo'+kelvin+'s').replace('Sergei','SERGEI')]
        if 'ff' in self.attempt:tricky.append(p.replace(self.attempt,self.attempt.replace('ff',ligature,1)))
        misses=['C:\\elsewhere\\'+str(i)+'.m4b' for i in range(30)]+[p.replace('Users','ÜSERS'),p.replace(self.attempt,'0'*36),self.attempt,'source00000.m4b',12345,1.5e-05,None]
        out=[]
        for value in hits+tricky+misses:
            row=[None,None,None,None,None];row[random.randrange(5)]=value;out.append(tuple(row))
        out.append((b'binary',None,None,None,None))
        return out,len(hits)+len(tricky)
    def old_flags(self,row,wanted):
        from working_lifecycle import normalized
        from source_cleanup import packed
        return any(path in normalized(packed(row)) for path in wanted)
    def test_every_row_the_full_scan_flags_is_a_candidate_and_unrelated_rows_are_not(self):
        from working_lifecycle import normalized,reference_candidates
        rows,expected=self.rows()
        self.sql('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)',rows,many=True)
        wanted=[normalized(self.path),normalized(self.path.replace('source00000.m4b','normalized00000.wav'))]
        every=self.sql('SELECT * FROM owned_artifacts',rows=True)
        found=self.sql(None,call=lambda db:[dict(r) for r in reference_candidates(db,'owned_artifacts',wanted)])
        flagged,unpacked=[],0
        for row in every:
            try:
                if self.old_flags(row,wanted):flagged.append(row)
            except TypeError:
                unpacked+=1;self.assertIn(row,found,'a row packed() refuses still reaches it, so it raises as before')
        self.assertEqual(len(flagged),expected,'every planted shape is one the old check flags (positive control)')
        for row in flagged:self.assertIn(row,found)
        self.assertEqual(unpacked,1)
        self.assertLess(len(found),len(every)-25,'unrelated rows stay in SQLite')
    def test_a_casefold_character_inside_the_search_token_is_still_found(self):
        # The token of this path is "kafka books"; the stored text spells its K with the Kelvin sign and its S with the long
        # s. The old check matches (casefold), a plain instr(lower()) does not: the fallback for such characters must.
        from working_lifecycle import normalized,reference_candidates,search_token
        path='C:\\Library\\Kafka Books\\track.mp3';stored='C:\\Library\\'+chr(0x212a)+'afka Book'+chr(0x17f)+'\\track.mp3'
        wanted=[normalized(path)];token=search_token(wanted[0])
        self.assertEqual(token,'kafka books');self.assertTrue(self.old_flags({'path':stored},wanted),'positive control: the old check flags it')
        self.sql('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)',[(stored,None,None,None,None),('C:\\Library\\Other\\x.mp3',None,None,None,None)],many=True)
        self.assertEqual(self.sql('SELECT instr(lower(path),?) AS found FROM owned_artifacts',(token,),rows=True)[0]['found'],0,'the token search alone misses it')
        found=self.sql(None,call=lambda db:[dict(r) for r in reference_candidates(db,'owned_artifacts',wanted)])
        self.assertEqual([row['path'] for row in found],[stored])
    def test_unsearchable_paths_fall_back_to_the_full_scan(self):
        from working_lifecycle import reference_candidates,search_token
        self.assertIsNone(search_token('no-slash'));self.assertIsNone(search_token('c:/a"b'))
        self.assertEqual(search_token('c:/books arranger/'+self.job+'/'+self.attempt+'/source00000.m4b'),self.attempt)
        self.sql('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)',[('x',None,None,None,None),('y',None,None,None,None)],many=True)
        self.assertEqual(self.sql(None,call=lambda db:len(reference_candidates(db,'owned_artifacts',['no-slash']).fetchall())),2)
        self.assertEqual(self.sql(None,call=lambda db:len(reference_candidates(db,'owned_artifacts',['c:/'+str(i) for i in range(70)],limit=64).fetchall())),2)
    def test_the_check_raises_for_the_same_rows_as_before(self):
        from working_lifecycle import WorkingLifecycle
        life=WorkingLifecycle.__new__(WorkingLifecycle);life.database=self.db
        attempt={'job_id':self.job,'attempt_id':self.attempt}
        life._published_references(attempt,[self.path])  # nothing names it
        for value in (json.dumps({'path':self.path}),self.path.upper()+'\x1f',self.path.replace('Books','Boo'+chr(0x212a)+'s')):
            self.sql('DELETE FROM owned_artifacts');self.sql('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)',(value,'other','x','',0))
            with self.assertRaisesRegex(BoundaryError,'another durable dependency: owned_artifacts'):life._published_references(attempt,[self.path])

if __name__=='__main__':unittest.main()
