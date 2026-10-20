"""In-memory transactional reconciliation and mocked held-source proof; no media tools."""
import copy,hashlib,json,sqlite3,sys,threading,types,unittest
from pathlib import Path
from unittest.mock import patch
import reacquire_sources as r

class ReacquireTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        self.root=str(Path('C:/fixture'));self.path=str(Path(self.root)/'one.mp3');self.old=hashlib.sha256(b'old').hexdigest()
        self.db.executescript('''CREATE TABLE book_groups(id TEXT PRIMARY KEY,root TEXT,scope TEXT UNIQUE,revision INTEGER,fingerprint TEXT,evidence TEXT,review TEXT,approved INTEGER,changed INTEGER,superseded INTEGER);
CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT);
CREATE TABLE files(root TEXT,path TEXT,size INTEGER,modified INTEGER,seen INTEGER,kind TEXT,metadata TEXT,error TEXT,missing INTEGER,review TEXT);
CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT,manifest_hash TEXT,state TEXT,stage TEXT,attempt_id TEXT,journal TEXT,output TEXT,reason TEXT,created TEXT,updated TEXT);
CREATE TABLE jobs(root TEXT,generation INTEGER,state TEXT,errors INTEGER);
CREATE TABLE queue(root TEXT,generation INTEGER,path TEXT,directory INTEGER,state TEXT);
CREATE TABLE book_catalog_revision(id INTEGER PRIMARY KEY,revision INTEGER);
CREATE TABLE book_group_sync(root TEXT PRIMARY KEY,revision INTEGER);''')
        source={'path':self.path,'size':3,'modified':7,'sha256':self.old}
        manifest={'candidate_id':'book','sources':[source]}
        self.db.execute('INSERT INTO book_groups VALUES(?,?,?,?,?,?,?,?,?,?)',('book',self.root,self.root+'-scope',1,'fp',json.dumps({'members':[source]}),'{}',0,0,0))
        self.db.execute('INSERT INTO candidate_context VALUES(?,?,?)',('book',1,'{}'))
        self.db.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?,?,?)',(self.root,self.path,3,7,2,'audiobook','{}','',0,'old source review'))
        self.db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',('job',json.dumps(manifest),'manifest','needs attention','checking sources','attempt','{}',None,'held','2026','2026'))
        self.db.execute('INSERT INTO jobs VALUES(?,?,?,?)',(self.root,2,'scanning',0));self.db.execute('INSERT INTO queue VALUES(?,?,?,?,?)',(self.root,2,self.root,1,'done'))
        self.db.execute('INSERT INTO book_catalog_revision VALUES(1,1)');self.db.execute('INSERT INTO book_group_sync VALUES(?,1)',(self.root,));r.ensure(self.db)
        self.snapshot=r._current(self.db,'book')
        self.analysis={'reason':'Actual measured damage','repair_limit':'Speech cannot safely be reconstructed','analysis_id':'analysis','verdict':'unsafe_meaningful_audio_repair'}
        self.db.execute('INSERT INTO reacquire_markers VALUES(?,?,?,?,?,?,?)',('book','job',self.root,'required',json.dumps(self.snapshot),json.dumps(self.analysis),''));self.db.commit()
        self.world={};self.reads=0
        test=self
        class Boundary:
            def __init__(self,*args):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def revalidate(self):pass
        class File:
            def __init__(self,path):self.path=str(path)
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def facts(self):return {'links':1,'size':len(test.world[self.path]),'identity':[1,2,3]}
            def chunks(self):test.reads+=1;yield test.world[self.path]
            def sha256(self):return hashlib.sha256(test.world[self.path]).hexdigest()
        native=types.SimpleNamespace(ordinary=lambda p:Path(p),DirectoryBoundary=Boundary,VerifiedFile=File,single_stream=lambda p:None)
        self.patches=[patch.dict(sys.modules,{'native_io':native}),patch.object(Path,'stat',lambda path,*a,**k: object() if str(path) in test.world or str(path)==test.root else (_ for _ in ()).throw(FileNotFoundError())),patch.object(Path,'exists',lambda path:str(path)==test.root or str(path) in test.world)]
        for p in self.patches:p.start()
        self.inventory=types.SimpleNamespace(stop_event=threading.Event(),reader=lambda *args:{'title':'Fresh replacement'})
        self.boundary=Boundary()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.db.close()
    def reconcile(self):return r.reconcile_scan(self.db,self.inventory,self.root,2,self.boundary)[0]
    def test_all_absent_archives_only_active_identity_and_preserves_history(self):
        before=dict(self.db.execute('SELECT * FROM audio_jobs').fetchone());result=self.reconcile();self.assertTrue(result['archived'],result)
        self.assertEqual(dict(self.db.execute('SELECT * FROM audio_jobs').fetchone()),before)
        old=self.db.execute('SELECT * FROM book_groups').fetchone();self.assertEqual(old['superseded'],1);self.assertNotEqual(old['scope'],self.snapshot['group']['scope'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM files').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT data FROM candidate_context').fetchone()[0],'{}')
        self.assertEqual(r.markers(self.db)[0]['state'],'archived');self.assertEqual(r.reconcile_scan(self.db,self.inventory,self.root,2,self.boundary),[])
    def test_same_path_same_stat_new_bytes_preserves_replacement_and_forces_research(self):
        self.world[self.path]=b'new';result=self.reconcile();self.assertTrue(result['archived'],result);self.assertGreaterEqual(self.reads,3)
        row=self.db.execute('SELECT * FROM files').fetchone();self.assertEqual(row['path'],self.path);self.assertEqual(row['review'],'');self.assertIn('Fresh replacement',row['metadata'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM book_group_sync').fetchone()[0],0)
        self.assertGreater(self.db.execute('SELECT revision FROM book_catalog_revision').fetchone()[0],1)
        self.db.execute('INSERT INTO book_groups VALUES(?,?,?,?,?,?,?,?,?,?)',('new-book',self.root,self.snapshot['group']['scope'],1,'new','{}','',0,0,0))
        self.assertIsNone(r.admission_hold(self.db,'new-book'));self.assertIsNone(self.db.execute("SELECT * FROM candidate_context WHERE id='new-book'").fetchone())
    def test_new_native_object_with_old_bytes_is_not_displacement(self):
        self.world[self.path]=b'old';result=self.reconcile();self.assertFalse(result['archived']);self.assertIn('original source content',result['reason']);self.assertEqual(r.marker(self.db,'book')['state'],'required')
    def test_offline_error_stopped_or_incomplete_generation_refuses(self):
        for state,errors in [('offline',0),('failed',0),('stopped',0),('scanning',1)]:
            self.db.execute('UPDATE jobs SET state=?,errors=?',(state,errors));self.db.commit();self.assertFalse(self.reconcile()['archived'])
        self.db.execute("UPDATE jobs SET state='scanning',errors=0");self.db.execute("UPDATE queue SET state='pending'");self.db.commit();self.assertFalse(self.reconcile()['archived'])
    def test_source_reader_failure_never_clears_candidate(self):
        self.world[self.path]=b'new';self.inventory.reader=lambda *a:(_ for _ in ()).throw(PermissionError('denied'))
        self.assertFalse(self.reconcile()['archived']);self.assertEqual(self.db.execute('SELECT superseded FROM book_groups').fetchone()[0],0)
    def test_empty_publication_intent_and_historical_output_protect(self):
        for journal,output in [('{"publication_intent":{}}',None),('{}','{}')]:
            self.db.execute('UPDATE audio_jobs SET journal=?,output=?',(journal,output));self.db.commit();self.assertFalse(self.reconcile()['archived'])
    def test_archive_collision_and_changed_context_roll_back(self):
        self.db.execute('UPDATE candidate_context SET data=?',('{"changed":true}',));self.db.commit();self.assertFalse(self.reconcile()['archived'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM files').fetchone()[0],1)
    def test_dependency_and_overlap_hold(self):
        self.db.execute('CREATE TABLE storage_cleanup_jobs(job_id TEXT)');self.db.execute("INSERT INTO storage_cleanup_jobs VALUES('job')");self.db.commit();self.assertFalse(self.reconcile()['archived'])
    def test_no_imported_json_or_caller_boolean_marking(self):
        for value in ({'native_closed':True},True,self.analysis):
            with self.assertRaises(ValueError):r.record_assessment(self.db,'book',value)
        with self.assertRaises(ValueError):r.AssessedDamage(object(),self.analysis)
    def test_active_and_archived_old_id_admission_refuses(self):
        with self.assertRaisesRegex(ValueError,'Need to reacquire'):r.require_admission(self.db,'book')
        self.assertTrue(self.reconcile()['archived'])
        with self.assertRaisesRegex(ValueError,'archived'):r.require_admission(self.db,'book')
    def test_unknown_root_lease_refuses(self):
        with self.assertRaisesRegex(ValueError,'root identity'):r.reconcile_scan(self.db,self.inventory,self.root,2,None)

    def test_shared_anthology_sibling_inventory_survives_archive(self):
        sibling=str(Path(self.root)/'unrelated.mp3')
        self.db.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?,?,?)',(self.root,sibling,5,8,2,'audiobook','{}','',0,'sibling review'));self.db.commit()
        self.assertTrue(self.reconcile()['archived']);row=self.db.execute('SELECT * FROM files').fetchone();self.assertEqual(row['path'],sibling);self.assertEqual(row['review'],'sibling review')
    def test_new_marker_or_candidate_edit_during_metadata_read_refuses(self):
        self.world[self.path]=b'new'
        def read(*args):
            self.db.execute('UPDATE candidate_context SET data=?',('{"edited":true}',));self.db.commit();return {'title':'New'}
        self.inventory.reader=read;result=self.reconcile();self.assertFalse(result['archived']);self.assertEqual(r.marker(self.db,'book')['state'],'required')
    def test_marker_blocks_create_without_using_english_error_text(self):
        self.db.execute('DELETE FROM reacquire_markers');self.db.execute("UPDATE audio_jobs SET reason='Header missing; damaged audio'");self.db.commit()
        self.assertIsNone(r.admission_hold(self.db,'book'));self.assertIsNone(r.project(self.db,'job'))
    def test_archive_scope_collision_refuses_without_changing_any_original_row(self):
        scope=self.snapshot['group']['scope']+'\x1freacquired:book'
        self.db.execute('INSERT INTO book_groups VALUES(?,?,?,?,?,?,?,?,?,?)',('collision',self.root,scope,1,'fp','{"members":[]}','',0,0,1));self.db.commit()
        result=self.reconcile();self.assertFalse(result['archived']);self.assertEqual(r.marker(self.db,'book')['state'],'required');self.assertEqual(self.db.execute('SELECT count(*) FROM files').fetchone()[0],1)

    def test_source_reappearance_before_final_absence_check_refuses(self):
        calls={'count':0};root=self.root;target=self.path
        def stat(path,*args,**kwargs):
            if str(path)==target:
                calls['count']+=1
                if calls['count']==1:raise FileNotFoundError()
                return object()
            if str(path)==root:return object()
            raise FileNotFoundError()
        with patch.object(Path,'stat',stat):result=self.reconcile()
        self.assertFalse(result['archived']);self.assertIn('reappeared',result['reason']);self.assertEqual(r.marker(self.db,'book')['state'],'required')
    def test_changed_scan_generation_during_read_refuses(self):
        self.world[self.path]=b'new'
        def read(*args):
            self.db.execute('UPDATE jobs SET generation=3');self.db.commit();return {'title':'New'}
        self.inventory.reader=read;self.assertFalse(self.reconcile()['archived'])

    def test_marker_requires_exact_closed_attempt_not_callback_invocation(self):
        self.db.execute('DELETE FROM reacquire_markers');self.db.commit()
        accepted=r.AssessedDamage(r._TOKEN,dict(self.analysis,snapshot_sha256=r.digest(r._current(self.db,'book'))))
        self.db.execute('BEGIN IMMEDIATE')
        with self.assertRaisesRegex(ValueError,'closure is unavailable'):r.record_assessment(self.db,'book',accepted)
        self.db.rollback();self.assertEqual(r.markers(self.db),[])
    def test_fixed_internal_producer_and_frozen_source_binding_required(self):
        class ActualType:
            def __init__(self,data):self.data=data
        source=self.snapshot['sources'][0]
        data=dict(schema=r.SCHEMA,outcome='uncertain_audio_loss',decision='reacquire',context_completed=True,job_id='job',manifest_sha256='manifest',candidate_id='book',candidate_revision=1,source_fingerprint='fp',sources=[dict(path=self.path,sha256=self.old,size=3,modified='7')],analysis_version='audio-damage-v1',reason='Measured incomplete audio',repair_limit='Cannot prove silence',analysis_id='analysis',script_sha256='a'*64,tool_sha256='b'*64,argv=['fixed diagnostic'])
        self.world[self.path]=b'old'
        with patch.dict(sys.modules,{'mp3_tag_repair':types.SimpleNamespace(SourceDamageAssessment=ActualType)}):
            with self.assertRaisesRegex(ValueError,'internal diagnostic'):
                with r.assess_live_sources(self.snapshot,data):pass
            wrong=dict(data,source_fingerprint=None)
            with self.assertRaisesRegex(ValueError,'evidence changed'):
                with r.assess_live_sources(self.snapshot,ActualType(wrong)):pass
            with r.assess_live_sources(self.snapshot,ActualType(data)) as accepted:
                self.assertIsInstance(accepted,r.AssessedDamage)
                self.assertIn('handle-close unverified',accepted.analysis['closure_basis'])
            safe=dict(data,outcome='repairable',decision='repairable')
            with self.assertRaisesRegex(ValueError,'No supported'):
                with r.assess_live_sources(self.snapshot,ActualType(safe)):pass
