"""Private policy and real SQLite CAS checks; codec proof is a separate fixture."""
import copy,hashlib,json,tempfile,unittest,uuid
from pathlib import Path
from audio_jobs import AudioJobs
from failed_m4b_retry import eligible,bind,SCHEMA

AREA=Path(__file__).resolve().parents[1]/'scratch'/'m4b-retry-tests'
AREA.mkdir(parents=True,exist_ok=True)
def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))

class RepairAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
        self.jobs=AudioJobs(Path(self.temp.name)/'catalog.sqlite3',None,lambda m:True,lambda r:False)
        self.addCleanup(self.jobs.close)
        self.manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,
            'sources':[{'path':str(Path(self.temp.name)/'source.m4b'),'sha256':'a'*64,'fingerprint':{'size':3,'modified':1}}],
            'metadata':{'title':'Approved title'},'destination':str(Path(self.temp.name)/'output.m4b'),
            'profile':'test frozen profile','evidence':{'approved':True},'cover':{},'source_chapters':[],
            'cleanup_policy':{'enabled':False}}
        self.jobs.enqueue(self.manifest)
        self.jobs._update(self.manifest['job_id'],state='needs attention',stage='checking',reason='Remux changed the decoder configuration or relative audio packet timing')
        self.parent=self.jobs._rows()[0]
        with self.jobs._db() as db:
            db.executescript('CREATE TABLE book_groups(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT);CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT);')
            db.execute('INSERT INTO book_groups VALUES(?,?,?)',(self.manifest['candidate_id'],1,'frozen'))
            db.execute('INSERT INTO candidate_context VALUES(?,?,?)',(self.manifest['candidate_id'],1,'{"approved":true}'))
        self.fresh=copy.deepcopy(self.manifest);self.fresh['job_id']=str(uuid.uuid4())
        self.proof={'schema':SCHEMA,'module_sha256':'b'*64,'tracks':[{'id':1,'sha256':'c'*64}]}
        self.context=(self.parent,(1,'frozen'),(1,'{"approved":true}'))

    def child(self):return bind(self.parent,self.fresh,self.proof)
    def test_original_row_and_journal_survive_new_child(self):
        child=self.jobs.enqueue(self.child(),repair_context=self.context)
        self.assertNotEqual(child,self.parent['job_id'])
        self.assertEqual(self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(self.parent['job_id'],))[0],self.parent)
        with self.jobs._db() as db:self.assertEqual(tuple(db.execute('SELECT parent_job_id,child_job_id FROM audio_repair_admissions').fetchone()),(self.parent['job_id'],child))

    def test_unknown_failure_is_preserved(self):
        for reason in ('unrelated failure','Source changed','Remux changed full native decoded audio samples or decoder trim effects'):
            self.assertFalse(eligible(self.parent|{'reason':reason}))

    def test_publication_or_output_blocks_admission(self):
        self.assertFalse(eligible(self.parent|{'output':'{}'}))
        self.assertFalse(eligible(self.parent|{'journal':'{"publication_intent":{}}'}))

    def test_changed_manifest_hash_blocks_policy(self):
        self.assertFalse(eligible(self.parent|{'manifest_hash':'0'*64}))

    def test_existing_repair_is_not_recursively_repaired(self):
        manifest=copy.deepcopy(self.manifest);manifest['m4b_repair']={'parent':'other'}
        raw=encoded(manifest)
        self.assertFalse(eligible(self.parent|{'manifest':raw,'manifest_hash':hashlib.sha256(raw.encode()).hexdigest()}))

    def test_new_review_or_source_or_cleanup_policy_is_not_silently_adopted(self):
        for field,value in [('metadata',{'title':'Changed'}),('sources',[]),('cleanup_policy',{'enabled':True}),('cover',{'id':'new'})]:
            with self.subTest(field=field),self.assertRaises(ValueError):bind(self.parent,self.fresh|{field:value},self.proof)

    def test_missing_preservation_profile_is_refused(self):
        for proof in ({},self.proof|{'tracks':[]},self.proof|{'schema':'unknown'}):
            with self.assertRaises(ValueError):bind(self.parent,self.fresh,proof)

    def test_parent_change_cas_rolls_back_child_and_relation(self):
        self.jobs._update(self.parent['job_id'],reason='changed concurrently')
        with self.assertRaises(ValueError):self.jobs.enqueue(self.child(),repair_context=self.context)
        self.assertEqual(len(self.jobs._rows()),1)
        with self.jobs._db() as db:self.assertEqual(db.execute('SELECT count(*) FROM audio_repair_admissions').fetchone()[0],0)

    def test_context_change_cas_refuses(self):
        with self.jobs._db() as db:db.execute('UPDATE candidate_context SET data=?',('{"approved":false}',))
        with self.assertRaises(ValueError):self.jobs.enqueue(self.child(),repair_context=self.context)
        self.assertEqual(len(self.jobs._rows()),1)

    def test_group_change_cas_refuses(self):
        with self.jobs._db() as db:db.execute('UPDATE book_groups SET revision=2')
        with self.assertRaises(ValueError):self.jobs.enqueue(self.child(),repair_context=self.context)

    def test_second_child_is_refused_without_overwriting_parent(self):
        self.jobs.enqueue(self.child(),repair_context=self.context)
        other=copy.deepcopy(self.fresh);other['job_id']=str(uuid.uuid4())
        with self.assertRaises(ValueError):self.jobs.enqueue(bind(self.parent,other,self.proof),repair_context=self.context)
        self.assertEqual(len(self.jobs._rows()),2)

    def test_repair_and_automatic_approval_cannot_mix(self):
        with self.assertRaises(ValueError):self.jobs.enqueue(self.child(),repair_context=self.context,approval_context=())

    def test_legacy_audio_debt_blocks_another_source_copy(self):
        from merge_service import MergeService
        service=MergeService.__new__(MergeService);service.jobs=self.jobs
        service.stage_root=Path(self.temp.name)/'staging';service.stage_root.mkdir()
        attempt=service.stage_root/self.parent['job_id']/str(uuid.uuid4());attempt.mkdir(parents=True)
        snapshot=attempt/'source00000.m4b';snapshot.write_bytes(b'unfinished original copy')
        result=service._retry_preserved_m4b(self.parent,100)
        self.assertFalse(result['requeued'])
        self.assertIn('Prior audio working files',result['reason'])
        self.assertEqual(snapshot.read_bytes(),b'unfinished original copy')
        self.assertEqual(len(self.jobs._rows()),1)

    def test_real_preservation_plan_is_json_safe_through_bind_and_enqueue(self):
        from failed_m4b_retry import profile_proof
        from m4b_preservation import plan
        from test_m4b_preservation import fixture
        source=fixture(composition=True)
        profile=plan(len(source),lambda offset,count:source[offset:offset+count],{'title':'Approved title'},None)
        proof=profile_proof(profile,'b'*64)
        child=self.jobs.enqueue(bind(self.parent,self.fresh,proof),repair_context=self.context)
        stored=self.jobs._rows('SELECT manifest FROM audio_jobs WHERE job_id=?',(child,))[0]
        track=json.loads(stored['manifest'])['m4b_repair']['source_profile']['tracks'][0]
        self.assertEqual(track['handler'],'soun');self.assertEqual(track['codec'],'mp4a')
        self.assertEqual(track['sha256'],profile.tracks[0]['sha256'])
