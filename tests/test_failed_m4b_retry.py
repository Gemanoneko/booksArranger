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

    def test_old_remux_presentation_bounds_failure_is_eligible(self):
        self.assertTrue(eligible(self.parent|{'reason':'M4B presentation bounds cannot be verified'}))

    def test_writer_family_and_coverless_failures_are_eligible_but_other_reviews_are_not(self):
        for reason in ('M4B preservation requires review: Unsupported/ambiguous brand',
                       'M4B preservation requires review: Unsupported structural box',
                       'Preservation changed decoder, packets or presentation',
                       'M4B preservation requires review: Table count/extent'):
            self.assertTrue(eligible(self.parent|{'reason':reason}),reason)
        for reason in ('M4B preservation requires review: Top-level extent invalid',
                       'M4B preservation requires review: Unresolved chapter reference',
                       'Preservation changed complete native decoded audio'):
            self.assertFalse(eligible(self.parent|{'reason':reason}),reason)

    def test_user_requested_damage_repair_uses_the_one_child_ledger(self):
        import m4b_repair
        from test_m4b_preservation import TEXT_SOURCE,dangling
        source=dangling(TEXT_SOURCE(),[3,2])
        diagnosis=m4b_repair.diagnose(len(source),lambda offset,count:source[offset:offset+count])
        self.assertTrue(m4b_repair.eligible(self.parent|{'reason':'M4B preservation requires review: Unresolved chapter reference'}))
        child=self.jobs.enqueue(m4b_repair.bind(self.parent,self.fresh,diagnosis,'b'*64),repair_context=self.context)
        stored=json.loads(self.jobs._rows('SELECT manifest FROM audio_jobs WHERE job_id=?',(child,))[0]['manifest'])
        self.assertEqual(m4b_repair.approved_repairs(stored),{'dangling_chapter_reference'})
        child_row=self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(child,))[0]|{'state':'needs attention'}
        self.assertFalse(eligible(child_row|{'reason':'Remux changed the decoder configuration or relative audio packet timing'}))
        self.assertFalse(m4b_repair.eligible(child_row))
        other=copy.deepcopy(self.fresh);other['job_id']=str(uuid.uuid4())
        with self.assertRaises(ValueError):self.jobs.enqueue(m4b_repair.bind(self.parent,other,diagnosis,'b'*64),repair_context=self.context)
        with self.jobs._db() as db:self.assertEqual(db.execute('SELECT count(*) FROM audio_repair_admissions').fetchone()[0],1)


class PriorityReadmissionTests(unittest.TestCase):
    """Retry/Repair clicks are accepted while a book runs and run next, in click order."""
    def setUp(self):
        RepairAdmissionTests.setUp(self)
        self.parents=[self.parent['job_id']]+[self.failed() for _ in range(2)]
        self.normal=self.queued_job()  # an older ordinary queued book
        self.made={};self.calls=[]
    def failed(self):
        manifest=copy.deepcopy(self.manifest);manifest['job_id']=str(uuid.uuid4());manifest['candidate_id']=str(uuid.uuid4())
        self.jobs.enqueue(manifest);self.jobs._update(manifest['job_id'],state='needs attention',stage='checking',reason='Remux changed the decoder configuration or relative audio packet timing')
        return manifest['job_id']
    def queued_job(self):
        manifest=copy.deepcopy(self.manifest);manifest['job_id']=str(uuid.uuid4());manifest['candidate_id']=str(uuid.uuid4())
        return self.jobs.enqueue(manifest)
    def admit(self,parent,kind,refuse=()):
        self.calls.append((parent,kind))
        if parent in refuse:return {'requeued':False,'reason':'Prior audio working files need verified disposal before another source copy'}
        child=self.queued_job();self.made[parent]=child;return {'requeued':True,'job_id':child,'reason':'admitted'}
    def request(self,parent,kind='retry'):
        import m4b_readmission
        with self.jobs._db() as db:return m4b_readmission.request(db,parent,kind,1000)
    def describe(self,job_id):
        import m4b_readmission
        with self.jobs._db() as db:return m4b_readmission.describe(db,job_id)
    def next_job(self,admit=None):
        import m4b_readmission
        return m4b_readmission.next_job(self.jobs._db,admit or self.admit,1000)

    def test_clicks_are_accepted_in_click_order_and_repeated_clicks_keep_their_place(self):
        a,b,c=self.parents
        self.assertEqual([self.request(b)['position'],self.request(a,'repair')['position'],self.request(c)['position']],[1,2,3])
        again=self.request(b);self.assertEqual((again['accepted'],again['queued_next'],again['position']),(True,True,1))
        self.assertEqual(self.describe(a)['kind'],'repair')
        with self.assertRaises(ValueError):self.request(a,'loosen')
    def test_worker_admits_the_head_and_its_child_runs_before_the_normal_queue(self):
        a,b,c=self.parents;self.request(b);self.request(a,'repair')
        first=self.next_job();self.assertEqual(self.calls,[(b,'retry')]);self.assertEqual(first,self.made[b])
        self.assertNotEqual(first,self.normal)  # the older ordinary book waits
        self.assertEqual(self.describe(first)|{},self.describe(b));self.assertEqual(self.describe(first)['position'],1)
        self.assertEqual(self.next_job(),first);self.assertEqual(len(self.calls),1)  # not admitted twice
        self.jobs._update(first,state='running')
        second=self.next_job();self.assertEqual(self.calls[-1],(a,'repair'));self.assertEqual(second,self.made[a])
        self.jobs._update(second,state='running');self.assertIsNone(self.next_job())
    def test_a_refused_book_is_recorded_alone_and_the_next_click_proceeds(self):
        a,b,c=self.parents;self.request(b);self.request(a);self.request(c)
        child=self.next_job(lambda parent,kind:self.admit(parent,kind,refuse={b}))
        self.assertEqual(child,self.made[a])
        refused=self.describe(b);self.assertFalse(refused['accepted']);self.assertIn('Prior audio working files',refused['reason'])
        self.assertEqual(self.request(b)['position'],3)  # a new click joins the end: a's child, c, b
    def test_deferred_or_interrupted_admission_keeps_its_place(self):
        a,b,c=self.parents;self.request(b)
        self.assertIsNone(self.next_job(lambda parent,kind:{'defer':True}));self.assertEqual(self.describe(b)['position'],1)
        def stopped(parent,kind):raise InterruptedError('stop')
        with self.assertRaises(InterruptedError):self.next_job(stopped)
        self.assertEqual(self.describe(b)['position'],1)
        self.assertEqual(self.next_job(),self.made[b])

