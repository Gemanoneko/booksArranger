"""Pure/SQLite no-IO pre-attempt hold controls plus separate real service acceptance."""
import contextlib,copy,json,os,sqlite3,tempfile,threading,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from audio_jobs import AudioJobs
from merge_service import MergeService
import destination_admission as d

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'destination-admission'
class DestinationAdmission(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True,exist_ok=True);self.base=Path(tempfile.mkdtemp(dir=AREA));self.root=self.base/'audio';self.root.mkdir();self.target=self.base/'Sorted';self.target.mkdir();self.source=self.root/'original.mp3';self.source.write_bytes(b'original retained')
        self.metadata={'title':'Book','author':'Author Name','canonical_author':'Author Name','original_language':'Other','series':'Cycle','number':'1','multi_author':False,'anthology':False}
        self.manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'root':str(self.root),'destination':str(self.root/'Author Name'/'Cycle - 1 - Book - Author Name.m4b'),'sources':[{'path':str(self.source),'sha256':'a'*64,'fingerprint':{'size':17,'modified':1}}],'metadata':self.metadata,'profile':'fixture','evidence':{},'cover':{}}
        self.jobs=AudioJobs(self.base/'catalog.sqlite',Mock(side_effect=AssertionError('runner before hold')),lambda _:True,lambda _:False);self.addCleanup(self.jobs.close)
        self.jobs.enqueue(self.manifest)
        with self.jobs._db() as db:
            db.executescript('CREATE TABLE book_groups(id TEXT PRIMARY KEY,revision INTEGER,review TEXT,superseded INTEGER);CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER);')
            db.execute('INSERT INTO book_groups VALUES(?,?,?,?)',(self.manifest['candidate_id'],1,json.dumps(self.metadata),0));db.execute('INSERT INTO candidate_context VALUES(?,?)',(self.manifest['candidate_id'],1))
        self.service=MergeService.__new__(MergeService);self.service.inventory=SimpleNamespace(roots={'Audiobooks':str(self.root)},output_root=str(self.target),source_roots=lambda _: [str(self.root)])
        self.jobs.destination_policy=self.service._destination_policy;self.jobs.attempt_boundary=self.service._attempt_boundary
        self.jobs.before_attempt=Mock(side_effect=AssertionError('working cleanup before hold'));self.jobs._archive_attempt=Mock(side_effect=AssertionError('archive before hold'))
        self.row=self.jobs._rows()[0];self.observation=d.observe(self.manifest,self.jobs.destination_policy())
    def held(self):return self.jobs._rows()[0]
    def records(self):
        with self.jobs._db() as db:return [dict(r) for r in db.execute('SELECT * FROM audio_destination_holds')]
    def test_mismatch_holds_before_uuid_cleanup_copy_or_attempt(self):
        with patch('audio_jobs.uuid.uuid4',side_effect=AssertionError('UUID before hold')),patch('merge_service.DirectoryBoundary',side_effect=AssertionError('native IO before hold')):self.jobs._work()
        held=self.held();self.assertEqual(held['state'],'needs attention');self.assertIsNone(held['attempt_id'])
        for key in self.row:
            if key not in {'state','reason','updated'}:self.assertEqual(held[key],self.row[key],key)
        self.jobs.before_attempt.assert_not_called();self.jobs._archive_attempt.assert_not_called();self.jobs.runner.assert_not_called();self.assertFalse((self.base/'cache').exists());self.assertEqual(self.source.read_bytes(),b'original retained');self.assertEqual(len(self.records()),1)
        summary=self.jobs.attention_summary(lambda _:None,job_ids=[self.row['job_id']]);self.assertTrue(summary[self.row['job_id']]['destination_review']['can_retry'])
    def test_exact_actual_path_passes_old_label(self):
        from organization import plan
        manifest=copy.deepcopy(self.manifest);manifest['output_root']=str(self.target);manifest['destination']=plan(str(self.target),dict(self.metadata,organization_policy='books-hierarchy-v2'))['path']
        self.assertIsNone(d.observe(manifest,self.jobs.destination_policy()))
    def test_explicit_null_output_root_is_not_defaulted(self):
        with self.assertRaises(ValueError):d.observe(dict(self.manifest,output_root=None),self.jobs.destination_policy())
    def suffix_manifest(self,narrator='Reader One'):
        from recording_classification import destination_suffix
        import hashlib
        manifest=copy.deepcopy(self.manifest);manifest['sources'][0]['size']=17;manifest['metadata']['narrator']=narrator
        facts={'policy_version':'standing-17-v1','source_fingerprint':'frozen-fixture-fingerprint','work_ids':['work:one'],'authors':['Author Name'],'recording_language':{'value':'ru','basis':'embedded'}}
        candidate={'id':manifest['candidate_id'],'identity_verified':True,'work_ids':facts['work_ids'],'collection_kind':'single','series_volume':'1','narrator':{'value':narrator,'verified':True},'recording_language':{'value':'ru','verified':True},'edition':{'value':'','verified':False},'manifest':{'complete':True,'observed_count':1,'tracks':[{'source_sha256':manifest['sources'][0]['sha256'],'size_bytes':17,'chapter_sha256':hashlib.sha256(b'[]').hexdigest()}]}}
        facts['destination_suffix']=destination_suffix(candidate);manifest['metadata_facts']=facts
        return manifest
    def test_current_suffixed_v2_passes_and_distinct_recordings_stay_separate(self):
        from organization import frozen_plan
        one=self.suffix_manifest();two=self.suffix_manifest('Reader Two')
        for manifest in (one,two):
            manifest['metadata']['organization_policy']='books-hierarchy-v2';manifest['output_root']=str(self.target);manifest['destination']=frozen_plan(manifest,str(self.target))['path'];self.assertIsNone(d.observe(manifest,self.jobs.destination_policy()))
        self.assertNotEqual(one['destination'],two['destination'])
    def test_forged_suffix_source_or_identity_refuses(self):
        from organization import frozen_plan
        for change in ('suffix','source','author','policy'):
            manifest=self.suffix_manifest()
            if change=='suffix':manifest['metadata_facts']['destination_suffix']='recording-'+'a'*16
            if change=='source':manifest['sources'][0]['sha256']='b'*64
            if change=='author':manifest['metadata_facts']['authors']=['Other Author']
            if change=='policy':manifest['metadata_facts']['policy_version']='unknown'
            with self.assertRaises(ValueError,msg=change):frozen_plan(manifest,str(self.target))
    def test_changed_whole_pending_row_refuses_atomic_hold(self):
        self.jobs._update(self.row['job_id'],reason='concurrent change');before=self.held();self.assertFalse(self.jobs._hold_destination(self.row,self.observation));self.assertEqual(self.held(),before);self.assertEqual(self.records(),[])
    def test_changed_configuration_refuses_cas_and_projection(self):
        self.service.inventory.output_root=str(self.base/'Different');self.assertFalse(self.jobs._hold_destination(self.row,self.observation));self.assertEqual(self.held(),self.row);self.assertEqual(self.records(),[])
        self.service.inventory.output_root=str(self.target);self.assertTrue(self.jobs._hold_destination(self.row,self.observation));self.service.inventory.output_root=str(self.base/'Different')
        summary=self.jobs.attention_summary(lambda _:None,job_ids=[self.row['job_id']])[self.row['job_id']];self.assertEqual(summary['destination_review']['state'],'stale');self.assertNotIn('retry',summary)
    def test_pause_injected_before_cas_leaves_intent_untouched(self):
        original=self.jobs.destination_policy
        def pause():self.jobs._stop.set();return original()
        self.jobs.destination_policy=pause;self.assertFalse(self.jobs._hold_destination(self.row,self.observation));self.assertEqual(self.held(),self.row);self.assertEqual(self.records(),[])
    def test_empty_publication_intent_key_is_not_waived(self):
        self.jobs._update(self.row['job_id'],journal='{"publication_intent":{}}');row=self.held();self.assertFalse(self.jobs._hold_destination(row,self.observation));self.assertEqual(self.held(),row);self.assertEqual(self.records(),[])
    def test_previous_attempt_is_not_the_attempt_null_case(self):
        attempt=str(uuid.uuid4());self.jobs._update(self.row['job_id'],attempt_id=attempt);row=self.held();self.assertFalse(self.jobs._hold_destination(row,self.observation));self.assertEqual(self.held(),row);self.assertEqual(self.records(),[])
    def test_stale_revision_and_noncurrent_work_refuse(self):
        with self.jobs._db() as db:db.execute('UPDATE book_groups SET revision=2')
        self.assertFalse(self.jobs._hold_destination(self.row,self.observation));self.assertEqual(self.held(),self.row);self.assertEqual(self.records(),[])
    def test_newer_job_and_changed_saved_review_refuse(self):
        newer=dict(self.manifest,job_id=str(uuid.uuid4()),profile='different-frozen-profile');self.jobs.enqueue(newer)
        self.jobs._update(newer['job_id'],created='2999-01-01T00:00:00Z')
        before=self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(self.row['job_id'],))[0]
        self.assertFalse(self.jobs._hold_destination(before,self.observation));self.assertEqual(self.records(),[])
        with self.jobs._db() as db:db.execute('DELETE FROM audio_jobs WHERE job_id=?',(newer['job_id'],));db.execute('UPDATE book_groups SET review=?',(json.dumps(dict(self.metadata,title='Other')),))
        self.assertFalse(self.jobs._hold_destination(before,self.observation));self.assertEqual(self.records(),[])
    def test_pause_after_hold_prevents_next_pending_item(self):
        newer=dict(self.manifest,job_id=str(uuid.uuid4()),candidate_id=str(uuid.uuid4()));self.jobs.enqueue(newer)
        with self.jobs._db() as db:
            db.execute('INSERT INTO book_groups VALUES(?,?,?,?)',(newer['candidate_id'],1,json.dumps(self.metadata),0));db.execute('INSERT INTO candidate_context VALUES(?,?)',(newer['candidate_id'],1))
        original=self.jobs._hold_destination
        def pause(*args):
            result=original(*args);self.jobs._stop.set();return result
        with patch.object(self.jobs,'_hold_destination',side_effect=pause):self.jobs._work()
        states=[row['state'] for row in self.jobs._rows()];self.assertEqual(states.count('pending'),1);self.assertEqual(states.count('needs attention'),1);self.jobs.runner.assert_not_called()
    def test_commit_failure_rolls_back_both_hold_and_job(self):
        original=self.jobs._db
        class Fault:
            def __init__(self,db):self.db=db
            def __getattr__(self,k):return getattr(self.db,k)
            def execute(self,sql,args=()):
                if sql.startswith('INSERT OR REPLACE INTO audio_destination_holds'):raise sqlite3.OperationalError('injected write failure')
                return self.db.execute(sql,args)
        @contextlib.contextmanager
        def failing():
            with original() as db:yield Fault(db)
        with patch.object(self.jobs,'_db',side_effect=failing):self.assertFalse(self.jobs._hold_destination(self.row,self.observation))
        self.assertEqual(self.held(),self.row);self.assertEqual(self.records(),[])

import test_retry_intent as retry_fixtures
class QueuedDestinationNative(unittest.TestCase):
    ready=retry_fixtures.RetryIntent.ready;wait=retry_fixtures.RetryIntent.wait;setUp=retry_fixtures.RetryIntent.setUp;tearDown=retry_fixtures.RetryIntent.tearDown;parent=retry_fixtures.RetryIntent.parent;activate=retry_fixtures.RetryIntent.activate
    def queued(self,target):
        row,parent=self.parent()
        self.service.jobs._update(parent['job_id'],state='pending',reason='')
        if target is not None:self.activate(target)
        else:
            roots=dict(self.inv.roots);database=self.inv.database;self.service.close()
            from scanner import Inventory
            self.inv=Inventory(database,roots);self.service=MergeService(self.inv,self.base/'cache')
        raw=self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],))[0]
        self.service.jobs.resume();status=self.wait()
        held=self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],))[0]
        self.assertEqual(held['state'],'needs attention',status);self.assertIsNone(held['attempt_id'])
        for key in raw:
            if key not in {'state','reason','updated'}:self.assertEqual(held[key],raw[key],key)
        return row,held
    def check_retry(self,target):
        row,parent=self.queued(target)
        with patch.object(self.service,'_resume_later'):
            ack=self.service.retry_blocked_job('Audiobooks',row['id'],row['revision'],parent['job_id'])
        self.assertTrue(ack.get('queued_next'),ack)
        self.service.resume();status=self.wait()
        children=[j for j in status['jobs'] if j['job_id']!=parent['job_id']]
        self.assertEqual(len(children),1,status);child=children[0]
        self.assertEqual(child['state'],'completed',status)
        expected=(target or Path(self.inv.roots['Audiobooks']))/'Author Name'/'Series'
        self.assertEqual(Path(child['output']['final_path']).parent,expected)
        self.assertNotEqual(child['attempt_id'],parent['attempt_id'])
        self.assertEqual(self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],))[0],parent)
        self.assertEqual(self.service.progress_books()['converted'],1)
        self.assertEqual(self.service.current_audiobook(row['id'])['state'],'verified')
        self.assertEqual(self.service.candidate_status(row['id'])['retry_parent_job_id'],parent['job_id'])
        self.assertEqual(self.service.reviews.page()['rows'][0]['creation']['job']['retry_parent_job_id'],parent['job_id'])
    def test_collision_does_not_create_child_or_overwrite(self):
        from organization import plan
        row,parent=self.queued(self.base/'Sorted Collision')
        target=Path(plan(self.inv.output_root,dict(json.loads(parent['manifest'])['metadata'],organization_policy='books-hierarchy-v2'))['path']);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'Unowned target stays')
        result=self.service._admit_new_retry(parent);self.assertFalse(result.get('requeued'),result);self.assertIn(str(target),result['reason']);self.assertEqual(target.read_bytes(),b'Unowned target stays');self.assertEqual(len(self.service.jobs._rows()),1);self.assertEqual(self.service.jobs._rows()[0],parent)
    def test_policy_change_refuses_explicit_retry(self):
        row,parent=self.queued(self.base/'Sorted Policy')
        self.inv.output_root=str(self.base/'Different')
        with self.assertRaisesRegex(ValueError,'destination or review changed'):self.service.retry_blocked_job('Audiobooks',row['id'],row['revision'],parent['job_id'])
        self.assertEqual(self.service.jobs._rows(),[parent])
    def suffixed_ready(self):
        from scanner import connect
        from recording_classification import destination_suffix
        import hashlib
        row=self.ready()
        facts={'policy_version':'standing-17-v1','source_fingerprint':row['fingerprint'],'work_ids':['fixture:related-work'],'authors':[row['review']['canonical_author']],'original_language':{'value':'en','status':'verified'},'title_basis':'published_english','series_state':'verified','author_folder_basis':'surname_first','cover':{'kind':'neutral'},'recording_language':{'value':'ru','basis':'embedded'}}
        with connect(self.inv.database) as db:
            saved=db.execute('SELECT data FROM candidate_context WHERE id=?',(row['id'],)).fetchone();ctx=json.loads(saved[0]);ctx['metadata_facts']=facts;db.execute('UPDATE candidate_context SET data=? WHERE id=?',(json.dumps(ctx),row['id']))
        manifest=self.service.reviews.build_manifest('Audiobooks',row['id'],row['revision'])
        tracks=[{'source_sha256':s['sha256'],'size_bytes':s['size'],'chapter_sha256':hashlib.sha256(b'[]').hexdigest()} for s in manifest['sources']]
        meta=manifest['metadata'];candidate={'id':row['id'],'identity_verified':True,'work_ids':facts['work_ids'],'collection_kind':'single','series_volume':meta.get('number') or None,'narrator':{'value':meta.get('narrator',''),'verified':bool(meta.get('narrator'))},'recording_language':{'value':'ru','verified':True},'edition':{'value':'','verified':False},'manifest':{'complete':True,'observed_count':len(tracks),'tracks':tracks}}
        facts['destination_suffix']=destination_suffix(candidate)
        with connect(self.inv.database) as db:
            ctx['metadata_facts']=facts;db.execute('UPDATE candidate_context SET data=? WHERE id=?',(json.dumps(ctx),row['id']))
        return self.service.reviews.enrich(self.service.reviews._row('Audiobooks',row['id'],row['revision']))
    def suffixed_parent(self):
        from scanner import connect
        row=self.suffixed_ready()
        with connect(self.inv.database) as db:
            review=json.loads(db.execute('SELECT review FROM book_groups WHERE id=?',(row['id'],)).fetchone()[0]);review.pop('organization_policy',None);review.pop('universe',None);db.execute('UPDATE book_groups SET review=? WHERE id=?',(json.dumps(review),row['id']))
        manifest=self.service.reviews.build_manifest('Audiobooks',row['id'],row['revision']);manifest.pop('output_root');job=self.service.jobs.enqueue(manifest);self.service.jobs._update(job,state='needs attention',reason='Admission hold')
        return row,self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job,))[0]
    def test_suffixed_new_root_retry_actual_ready(self):
        with patch.object(self,'parent',self.suffixed_parent):self.check_retry(self.base/'Sorted Recording')
        child=self.service.jobs.status()['jobs'][-1];self.assertIn(child['manifest']['metadata_facts']['destination_suffix'],child['output']['final_path'])
    def test_suffixed_same_root_retry_actual_ready(self):
        with patch.object(self,'parent',self.suffixed_parent):self.check_retry(None)
        child=self.service.jobs.status()['jobs'][-1];self.assertIn(child['manifest']['metadata_facts']['destination_suffix'],child['output']['final_path'])
    def test_suffixed_migration_actual_current_ready(self):
        original=self.ready
        with patch.object(self,'ready',side_effect=lambda: self.suffixed_ready_base(original)):
            retry_fixtures.RetryIntent.test_bound_user_universe_migration_keeps_current_view_and_ready(self)
        child=self.service.jobs.status()['jobs'][0];self.assertIn(child['manifest']['metadata_facts']['destination_suffix'],self.service.current_audiobook(child['manifest']['candidate_id'])['path'])
    def suffixed_ready_base(self,original):
        with patch.object(self,'ready',original):return self.suffixed_ready()
    def test_queued_old_root_explicit_retry_actual_ready(self):self.check_retry(self.base/'Sorted Queue')
    def test_queued_same_root_old_layout_explicit_retry_actual_ready(self):self.check_retry(None)

import test_replacement_jobs as replacement_fixtures
class QueuedReplacementRoute(unittest.TestCase):
    setUp=replacement_fixtures.ReplacementTests.setUp;tearDown=replacement_fixtures.ReplacementTests.tearDown;record=replacement_fixtures.ReplacementTests.record;insert_job=replacement_fixtures.ReplacementTests.insert_job;admit=replacement_fixtures.ReplacementTests.admit
    def test_exact_replacement_keeps_lineage_not_generic_route(self):
        relation=self.admit()
        with self.queue._db() as db:
            db.execute("UPDATE audio_jobs SET state='pending',output=NULL,journal='{}' WHERE job_id=?",(self.new_id,));row=self.store.raw_job(db,self.new_id)
        with self.service._attempt_boundary(row):pass
        self.assertEqual(self.store.get(new_job=self.new_id),relation)
        self.service.inventory.output_root=str(self.root/'Sorted')
        with self.assertRaisesRegex(ValueError,'exact replacement review'):
            with self.service._attempt_boundary(row):pass
        self.service.inventory.output_root=None
        forged=copy.deepcopy(row);manifest=json.loads(forged['manifest']);manifest['destination']=str(self.library/'arbitrary.m4b');forged['manifest']=json.dumps(manifest)
        with self.assertRaisesRegex(ValueError,'exact replacement review'):
            with self.service._attempt_boundary(forged):pass
        self.service.inventory.worker=None
        # Normal replacement guard independently checks the same immutable approval.
        self.assertFalse(self.service._guard(manifest))
        from retry_intent import bind
        parent=dict(row,state='needs attention');fresh=dict(manifest,job_id=str(uuid.uuid4()))
        with self.assertRaisesRegex(ValueError,'Replacement destination'):bind(parent,fresh,str(self.library))


# 0.21.3: this module's fixtures publish inside their own library; see sorted_fixture (Sergei's deletion rule).
def setUpModule():
    global _sorted_fixture
    from sorted_fixture import patch_merge_service
    _sorted_fixture = patch_merge_service()


def tearDownModule():
    _sorted_fixture.stop()

if __name__=='__main__':unittest.main()
