"""Private candidate-only source refresh: no whole-scan or source mutation."""
import hashlib,json,os,tempfile,threading,unittest,uuid
from pathlib import Path
from scanner import Inventory,connect,fresh_stat
import groups

AREA=Path(__file__).resolve().parents[1]/'scratch'/'candidate-refresh-tests'

class CandidateRefreshTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True,exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
        self.area=Path(self.temp.name);self.root=self.area/'library';self.root.mkdir();(self.root/'Podcasts').mkdir()
        self.source=self.root/'01.mp3';self.source.write_bytes(b'old source')
        self.reads=[]
        def reader(path,kind,stop):
            self.reads.append(path)
            return {'title':'Fixture Book','author':'Fixture Author','tags':{'album':'Fixture Book','artist':'Fixture Author','comment':Path(path).read_bytes().decode('ascii')}}
        self.inventory=Inventory(self.area/'catalog.sqlite3',{'Audiobooks':str(self.root),'Podcasts':str(self.root/'Podcasts')},reader)
        with connect(self.inventory.database) as db:
            stat=fresh_stat(self.source)
            db.execute("INSERT INTO files(root,path,size,modified,seen,kind,arrival,metadata) VALUES(?,?,?,?,3,'audiobook',0,?)",(str(self.root),str(self.source),stat.st_size,stat.st_mtime_ns,json.dumps(reader(str(self.source),'audiobook',threading.Event()))))
            db.execute("INSERT INTO jobs(root,label,generation,state,checked,reused,errors,current) VALUES(?,'Audiobooks',3,'completed with errors',17,4,1,'preserved')",(str(self.root),))
            db.execute("INSERT INTO queue(root,generation,path,directory,state) VALUES(?,3,?,0,'error')",(str(self.root),str(self.source)))
            db.execute("INSERT INTO scan_outcomes VALUES(?,3,?,0,'error','historical failure','original time','original details')",(str(self.root),str(self.source)))
            groups.sync(db,str(self.root));self.group=dict(db.execute('SELECT * FROM book_groups').fetchone())
        self.reads.clear()
    def saved(self):
        with connect(self.inventory.database) as db:
            return {table:[dict(row) for row in db.execute('SELECT * FROM '+table)] for table in ('files','jobs','queue','scan_outcomes','book_groups')}
    def refresh(self,**kwargs):return self.inventory.refresh_candidate_sources('Audiobooks',self.group['id'],self.group['revision'],**kwargs)
    def test_changed_source_refresh_preserves_reviews_scan_history_and_group(self):
        with connect(self.inventory.database) as db:db.execute('UPDATE files SET review=?',(json.dumps({'title':'Manual file title'}),))
        before=self.saved();self.source.write_bytes(b'new source content');source_bytes=self.source.read_bytes()
        result=self.refresh();after=self.saved()
        self.assertEqual(result['state'],'refreshed');self.assertEqual(result['old_fingerprint'],self.group['fingerprint'])
        self.assertEqual(result['observed_paths'],[str(self.source)]);self.assertEqual(result['refreshed_paths'],[str(self.source)])
        self.assertEqual(result['source_receipts'][0]['sha256'],hashlib.sha256(source_bytes).hexdigest())
        self.assertEqual(self.source.read_bytes(),source_bytes)
        for table in ('jobs','queue','scan_outcomes','book_groups'):self.assertEqual(before[table],after[table])
        self.assertEqual(before['files'][0]['review'],after['files'][0]['review']);self.assertEqual(after['files'][0]['seen'],3)
    def test_repaired_read_error_and_missing_clear_only_current_file(self):
        with connect(self.inventory.database) as db:db.execute("UPDATE files SET error='old read failure',missing=1")
        before=self.saved();result=self.refresh();after=self.saved()
        self.assertEqual(result['state'],'refreshed');self.assertEqual(after['files'][0]['error'],'');self.assertEqual(after['files'][0]['missing'],0)
        for table in ('jobs','queue','scan_outcomes','book_groups'):self.assertEqual(before[table],after[table])
    def test_unchanged_does_not_reread_metadata(self):
        before=self.saved();result=self.refresh()
        self.assertEqual(result['state'],'unchanged');self.assertEqual(self.reads,[]);self.assertEqual(before,self.saved())
    def test_force_refresh_handles_same_size_same_mtime_content_change(self):
        old=fresh_stat(self.source);self.source.write_bytes(b'new source');os.utime(self.source,ns=(old.st_atime_ns,old.st_mtime_ns))
        # The bytes change but cached size/time AND embedded title/credits stay
        # identical; the fresh native receipt must still advance source evidence.
        with connect(self.inventory.database) as db:prior_metadata=json.loads(db.execute('SELECT metadata FROM files').fetchone()[0])
        self.inventory.reader=lambda path,kind,stop:dict(prior_metadata)
        result=self.refresh(force=True)
        self.assertEqual(result['state'],'refreshed');self.assertEqual(result['source_receipts'][0]['sha256'],hashlib.sha256(b'new source').hexdigest())
        with connect(self.inventory.database) as db:
            metadata=json.loads(db.execute('SELECT metadata FROM files').fetchone()[0])
            self.assertEqual(metadata['source_refresh']['sha256'],hashlib.sha256(b'new source').hexdigest())
            groups.sync(db,str(self.root));new=dict(db.execute('SELECT * FROM book_groups WHERE id=?',(self.group['id'],)).fetchone())
        self.assertGreater(new['revision'],self.group['revision']);self.assertNotEqual(new['fingerprint'],self.group['fingerprint'])
    def test_manual_or_approved_candidate_is_held_without_mutation(self):
        for column,value in [('approved',1),('review',json.dumps({'title':'Manual candidate'}))]:
            with connect(self.inventory.database) as db:db.execute('UPDATE book_groups SET '+column+'=?',(value,))
            before=self.saved();self.assertEqual(self.refresh(force=True)['state'],'held');self.assertEqual(before,self.saved())
            with connect(self.inventory.database) as db:db.execute("UPDATE book_groups SET approved=0,review=''")
    def test_pending_or_manual_context_is_held(self):
        for data in [{'automatic_pending':{'review':'pending'}},{'manual_draft_active':True},{'metadata_approved':True}]:
            with connect(self.inventory.database) as db:
                db.execute('CREATE TABLE IF NOT EXISTS candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT)')
                db.execute('INSERT OR REPLACE INTO candidate_context VALUES(?,?,?)',(self.group['id'],self.group['revision'],json.dumps(data)))
            before=self.saved();self.assertEqual(self.refresh(force=True)['state'],'held');self.assertEqual(before,self.saved())
        # Browser draft leases are separate from the review context. An active
        # exact-revision lease must preserve sources; an expired lease is harmless.
        import time
        with connect(self.inventory.database) as db:
            db.execute('DELETE FROM candidate_context')
            db.execute('CREATE TABLE automatic_manual_drafts(id TEXT PRIMARY KEY,revision INTEGER,expires REAL)')
            db.execute('INSERT INTO automatic_manual_drafts VALUES(?,?,?)',(self.group['id'],self.group['revision'],time.time()+300))
        before=self.saved();self.assertEqual(self.refresh(force=True)['state'],'held');self.assertEqual(before,self.saved())
        with connect(self.inventory.database) as db:db.execute('UPDATE automatic_manual_drafts SET expires=?',(time.time()-1,))
        self.assertEqual(self.refresh(force=True)['state'],'refreshed')
    def test_stale_automatic_unapproved_review_is_preserved_and_refreshable(self):
        with connect(self.inventory.database) as db:
            db.execute('CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT)')
            db.execute('INSERT INTO candidate_context VALUES(?,?,?)',(self.group['id'],self.group['revision'],json.dumps({'automatic_approval':{'prior':'evidence'}})))
            db.execute('UPDATE book_groups SET review=?',(json.dumps({'title':'Old automatic suggestion'}),))
        before=self.saved();result=self.refresh(force=True)
        self.assertEqual(result['state'],'refreshed');self.assertEqual(before['book_groups'],self.saved()['book_groups'])
    def test_job_backed_candidate_and_journals_are_preserved(self):
        with connect(self.inventory.database) as db:
            db.execute('CREATE TABLE audio_jobs(id TEXT PRIMARY KEY,manifest TEXT,state TEXT)')
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?)',('job',json.dumps({'candidate_id':self.group['id'],'sources':[{'path':str(self.source)}]}),'failed'))
        before=self.saved();self.assertEqual(self.refresh(force=True)['state'],'held');self.assertEqual(before,self.saved())
        with connect(self.inventory.database) as db:self.assertEqual(db.execute('SELECT state FROM audio_jobs').fetchone()[0],'failed')
    def test_missing_source_holds_without_erasing_saved_evidence(self):
        before=self.saved();self.source.unlink();result=self.refresh()
        self.assertEqual(result['state'],'held');self.assertEqual(before,self.saved())
    def test_cancelled_and_budget_exceeded_are_atomic_holds(self):
        stopped=threading.Event();stopped.set();before=self.saved()
        self.assertEqual(self.refresh(stop=stopped)['hold_code'],'cancelled')
        self.assertEqual(self.refresh(force=True,max_bytes=1)['hold_code'],'budget_exceeded');self.assertEqual(before,self.saved())
    def test_source_is_leased_and_concurrent_catalog_edit_aborts_refresh(self):
        original_reader=self.inventory.reader
        def reader(path,kind,stop):
            with self.assertRaises(PermissionError):Path(path).write_bytes(b'unsafe write')
            with connect(self.inventory.database) as db:db.execute('UPDATE files SET review=?',(json.dumps({'title':'Concurrent review'}),))
            return original_reader(path,kind,stop)
        self.inventory.reader=reader
        before=self.source.read_bytes();result=self.refresh(force=True)
        self.assertEqual(result['state'],'held');self.assertEqual(result['hold_code'],'catalog_changed');self.assertEqual(before,self.source.read_bytes())
        with connect(self.inventory.database) as db:self.assertIn('Concurrent review',db.execute('SELECT review FROM files').fetchone()[0])
        # A new browser lease arising during the protected metadata read must
        # likewise abort the final atomic catalog update.
        import time
        with connect(self.inventory.database) as db:
            db.execute("UPDATE files SET review=''")
            db.execute('CREATE TABLE automatic_manual_drafts(id TEXT PRIMARY KEY,revision INTEGER,expires REAL)')
        def draft_reader(path,kind,stop):
            with connect(self.inventory.database) as db:
                db.execute('INSERT INTO automatic_manual_drafts VALUES(?,?,?)',(self.group['id'],self.group['revision'],time.time()+300))
            return original_reader(path,kind,stop)
        self.inventory.reader=draft_reader;before=self.saved();result=self.refresh(force=True)
        self.assertEqual(result['state'],'held');self.assertIn('editing lease',result['reason']);self.assertEqual(before,self.saved())
    def test_real_mp3_tags_and_native_bytes_are_refreshed(self):
        import shutil
        from audio_pipeline import run_owned
        from metadata import read_metadata
        generated=self.area/'tagged.mp3'
        run_owned([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=0.25',
                   '-c:a','libmp3lame','-metadata','album=Fixture Book','-metadata','artist=Fixture Author',str(generated)],self.area,threading.Event(),30)
        self.source.write_bytes(generated.read_bytes());before=self.source.read_bytes();self.inventory.reader=read_metadata
        result=self.refresh();self.assertEqual(result['state'],'refreshed')
        self.assertEqual(result['source_receipts'][0]['sha256'],hashlib.sha256(before).hexdigest());self.assertEqual(before,self.source.read_bytes())
        with connect(self.inventory.database) as db:metadata=json.loads(db.execute('SELECT metadata FROM files').fetchone()[0])
        self.assertIn('Fixture Book',str(metadata));self.assertIn('Fixture Author',str(metadata))
    def test_retirement_and_owned_recovery_are_never_refreshed(self):
        with connect(self.inventory.database) as db:
            db.execute('CREATE TABLE source_retirements(root TEXT,path TEXT,state TEXT)')
            db.execute('INSERT INTO source_retirements VALUES(?,?,?)',(str(self.root),str(self.source),'removed'))
        before=self.saved();self.assertEqual(self.refresh(force=True)['state'],'held');self.assertEqual(before,self.saved())
        with connect(self.inventory.database) as db:
            db.execute('DELETE FROM source_retirements')
            db.execute('CREATE TABLE owned_artifacts(path TEXT,kind TEXT)')
            db.execute('INSERT INTO owned_artifacts VALUES(?,?)',(str(self.source),'recovery'))
        before=self.saved();self.assertEqual(self.refresh(force=True)['state'],'held');self.assertEqual(before,self.saved())
    def test_active_scan_is_held_without_touching_scan_progress(self):
        with connect(self.inventory.database) as db:db.execute("UPDATE jobs SET state='scanning'")
        before=self.saved();self.assertEqual(self.refresh(force=True)['state'],'held');self.assertEqual(before,self.saved())

if __name__=='__main__':unittest.main()
