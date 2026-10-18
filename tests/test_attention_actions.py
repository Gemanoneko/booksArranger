"""v0.16.7: needs-attention classes and Retry for resolvable failures, the fast book list, and held rows.

Private SQLite/folder fixtures and doubles; no library, catalog copy or media tools.
"""
import copy,errno,json,sqlite3,sys,tempfile,threading,time,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import audio_jobs
from audio_jobs import AudioJobs,RetryRefused,failure_cause,_failure_details,RETRY_SPACE
from audio_pipeline import StepProgress
from automatic_processing import AutomaticProcessing
from scanner import connect
from test_blocked_retry import Queue,AREA
from web_server import activities


def typed(code=sqlite3.SQLITE_BUSY):
    error=sqlite3.OperationalError('database is locked');error.sqlite_errorcode=code;error.sqlite_errorname='SQLITE_BUSY';return error


class CauseTests(unittest.TestCase):
    def failed(self,error,reason=None):
        return {'reason':reason if reason is not None else str(error)},{'failure':_failure_details(error,'checking sources')}
    def test_typed_and_exact_legacy_shapes_only(self):
        self.assertEqual(failure_cause(*self.failed(typed())),'busy')
        for code in (sqlite3.SQLITE_LOCKED,517):self.assertEqual(failure_cause(*self.failed(typed(code))),'busy')
        legacy={'failure':{'exception_class':'OperationalError','retryable':False,'stage':'checking sources'}}
        self.assertEqual(failure_cause({'reason':'database is locked'},legacy),'busy','the untyped SQLITE_BUSY record (Horus Rising)')
        for reason in ('Database is locked','database is locked: x','disk I/O error'):self.assertIsNone(failure_cause({'reason':reason},legacy),reason)
        self.assertEqual(failure_cause(*self.failed(OSError(errno.ENOSPC,'Insufficient working space'))),'space')
        self.assertEqual(_failure_details(OSError(errno.ENOSPC,'x'),'queued')['errno'],errno.ENOSPC,'new records are typed')
        old={'failure':{'exception_class':'OSError','retryable':True,'stage':'queued'}}
        self.assertEqual(failure_cause({'reason':'[Errno 28] Insufficient working space; need 62699883954 bytes before snapshotting; originals retained'},old),'space')
        self.assertIsNone(failure_cause({'reason':'[Errno 13] Permission denied'},old));self.assertIsNone(failure_cause(*self.failed(OSError(errno.EACCES,'denied'))))
        self.assertIsNone(failure_cause({'reason':'x'},{'failure':{'exception_class':'ValidationError'}}));self.assertIsNone(failure_cause({'reason':'x'},{}))


class Base(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.q=Queue(self.temp.name)
    def tearDown(self):
        self.q.release.set();self.q.jobs.close();self.temp.cleanup()
    def failed_job(self,error,reason=None,manifest=None,stage='checking sources'):
        manifest=manifest or self.q.manifest();job_id=self.q.jobs.enqueue(manifest);attempt=str(uuid.uuid4())
        journal={'attempt_id':attempt,'history':[{'stage':stage,'at':'2026-10-17T10:00:00+00:00','details':None}],'failure':_failure_details(error,stage)}
        if reason=='legacy':journal['failure'].pop('sqlite_errorcode',None);journal['failure'].pop('sqlite_errorname',None);journal['failure'].pop('errno',None)
        self.q.jobs._update(job_id,state='needs attention',attempt_id=attempt,journal=json.dumps(journal),reason=str(error) or type(error).__name__)
        return job_id,attempt


class RetryResolvableTests(Base):
    def test_busy_failure_is_retryable_and_requeues_the_same_job(self):
        job_id,attempt=self.failed_job(sqlite3.OperationalError('database is locked'),reason='legacy')
        held=self.q.row(job_id);self.assertEqual(self.q.statuses(),{job_id:{'allowed':True,'reason':''}})
        self.assertEqual(self.q.retry(job_id)['requeued'],True)
        row=self.q.row(job_id);self.assertEqual((row['state'],row['journal']),('pending',held['journal']))
        self.q.jobs.resume();self.q.wait()
        with connect(self.q.db) as db:self.assertEqual([tuple(r) for r in db.execute('SELECT job_id,attempt_id FROM audio_failure_history')],[(job_id,attempt)])
        self.assertEqual(self.q.runs[0][0],job_id);self.assertNotEqual(self.q.runs[0][1],attempt)
    def test_full_disk_failure_waits_for_free_space_and_is_rechecked_at_press(self):
        job_id,_=self.failed_job(OSError(errno.ENOSPC,'Insufficient working space; need 6.5 GB free before snapshotting; originals retained'))
        free={'ok':False};ready=lambda manifest:free['ok']
        self.assertEqual(self.q.jobs.retry_statuses(self.q.life.admission_clear,space_ready=ready),{job_id:{'allowed':False,'reason':RETRY_SPACE}})
        before=self.q.row(job_id);manifest=json.loads(before['manifest'])
        with self.assertRaises(RetryRefused) as caught:self.q.jobs.retry_admission_hold(job_id,manifest['candidate_id'],1,self.q.life.admission_clear,ready)
        self.assertEqual(str(caught.exception),RETRY_SPACE);self.assertEqual(self.q.row(job_id),before)
        free['ok']=True
        self.assertEqual(self.q.jobs.retry_statuses(self.q.life.admission_clear,space_ready=ready)[job_id]['allowed'],True)
        self.assertEqual(self.q.jobs.retry_admission_hold(job_id,manifest['candidate_id'],1,self.q.life.admission_clear,ready)['requeued'],True)
    def test_other_failures_stay_ineligible(self):
        for error in (audio_jobs.RetryRefused('x'),ValueError('Source changed — review required'),OSError(errno.EACCES,'denied'),sqlite3.OperationalError('disk I/O error')):
            with self.subTest(error=repr(error)):
                job_id,_=self.failed_job(error,reason='legacy')
                self.assertNotIn(job_id,self.q.statuses())
                with self.assertRaises(RetryRefused):self.q.retry(job_id)


class AttentionGroupTests(Base):
    def test_groups_cause_and_untouched_originals(self):
        hold,_,_=self.q.blocked(leftover=False)
        busy,_=self.failed_job(typed())
        space,_=self.failed_job(OSError(errno.ENOSPC,'full'))
        m4b=self.q.manifest();m4b['sources'][0]['path']=str(self.q.base/'library'/'book.m4b')
        unsupported,_=self.failed_job(audio_jobs.RetryRefused('M4B preservation requires review: Unsupported structural box'),manifest=m4b)
        self.q.jobs._update(unsupported,journal=json.dumps({'attempt_id':None,'history':[],'failure':{'exception_class':'ValidationError','retryable':False,'stage':'checking'}}))
        other,_=self.failed_job(ValueError('Source changed — review required'))
        with connect(self.q.db) as db:
            db.execute('CREATE TABLE IF NOT EXISTS source_cleanup(id TEXT PRIMARY KEY,job_id TEXT UNIQUE,intent TEXT NOT NULL,state TEXT NOT NULL,reason TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL)')
            db.execute("INSERT INTO source_cleanup VALUES('c',?,'{}','needs_attention','x','','')",(other,))
        summary=self.q.jobs.attention_summary(self.q.life.admission_clear,lambda manifest:True)
        self.assertEqual({k:(v['group'],v['cause']) for k,v in summary.items()},{hold:('retry','files'),busy:('retry','busy'),space:('retry','space'),unsupported:('unsupported',None),other:('other',None)})
        self.assertTrue(summary[unsupported]['originals_untouched']);self.assertFalse(summary[other]['originals_untouched'],'a cleanup row exists')
        self.assertEqual({k for k,v in summary.items() if 'retry' in v},{hold,busy,space})
        counts=self.q.jobs.attention_summary(retry=False);self.assertFalse(any('retry' in v for v in counts.values()),'counts never run the E8 checks')
        self.assertEqual(self.q.jobs.attention_summary(job_ids=[busy],retry=False).keys(),{busy});self.assertEqual(self.q.jobs.attention_summary(job_ids=[]),{})


class HeldRowAndResearchTests(unittest.TestCase):
    def test_held_cleanup_is_a_needs_attention_row_never_the_active_row(self):
        jobs={'state':'Running','current_title':'Хранительница болот','progress':{'phase':'originals','completed':0,'total':31,'reason':'Download marker native identity differs','attention':True},
              'attention_row':{'title':'Хранительница болот','phase':'originals','reason':'Download marker native identity differs','completed':0,'total':31}}
        rows=activities(jobs,None,None,None,{},now_ms=1)
        self.assertEqual([(r['kind'],r['state'],r['reason']) for r in rows],[('cleanup','attention','Download marker native identity differs')])
        converting=dict(jobs,current_title='Next book',progress={'phase':'encoding','completed':5,'total':60})
        rows=activities(converting,None,None,None,{},now_ms=2)
        self.assertEqual([(r['kind'],r['state']) for r in rows],[('conversion','running'),('cleanup','attention')],'stays while the next book converts')
        running_cleanup=dict(jobs,current_title='Other',progress={'phase':'originals','completed':3,'total':9})
        self.assertEqual([(r['kind'],r['state']) for r in activities(running_cleanup,None,None,None,{},now_ms=3)],[('cleanup','running')])
    def test_research_counts_visited_books_from_the_live_checkpoint_and_keeps_one_clock(self):
        run={'phase':'research','checkpoint':json.dumps({'done':['a'],'pending':['b','c','d'],'deferred':[]})}
        live={'done':['a','b'],'pending':['d'],'deferred':['c']}
        self.assertEqual(AutomaticProcessing._research_pass(run),{'completed':1,'total':4})
        self.assertEqual(AutomaticProcessing._research_pass(run,live),{'completed':3,'total':4},'deferred books were visited')
        memo={};automatic={'state':'Running','phase':'research','current':{'title':'Book 1','source':'x','stage':'y'},'research_pass':{'completed':3,'total':4}}
        first=activities({},None,None,automatic,memo,now_ms=1000)[0]['step_started_at']
        automatic['current']['title']='Book 2';self.assertEqual(activities({},None,None,automatic,memo,now_ms=9000)[0]['step_started_at'],first,'a new book is not a new step')
    def test_preparing_reports_whole_files_and_a_fraction(self):
        sent=[];StepProgress(sent.append,'preparing',4,'files',4).update(2.52,3,force=True)
        self.assertEqual((sent[0]['completed'],sent[0]['fraction']),(2.0,0.63))
        row=activities({'current_title':'B','state':'Running','progress':{'phase':'preparing','completed':2.0,'total':4,'unit':'files','fraction':0.63}},None,None,None,{},now_ms=1)[0]
        self.assertEqual((row['done'],row['fraction']),(2.0,0.63))


class BookListTests(unittest.TestCase):
    """page(): attention groups and order, per-id prefilters, one jobs list per page."""
    def setUp(self):
        from scanner import Inventory
        from review_backend import CandidateReviewService
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);base=Path(self.temp.name);audio=base/'audio'
        for name in ('Alpha','Beta','Gamma','Delta'):(audio/name).mkdir(parents=True);(audio/name/'01.mp3').write_bytes(name.encode()*10)
        roots={'Audiobooks':str(audio),'Podcasts':str(base/'podcasts'),'Ebooks':str(base/'ebooks')}
        self.inventory=Inventory(base/'catalog.sqlite3',roots,lambda path,kind,stop:{'title':Path(path).parent.name,'tags':{'album':Path(path).parent.name},'probe':{'format':{'duration':'1.0'}},'method':'fixture'})
        self.inventory.launch('Audiobooks');self.inventory.worker.join(10)
        self.service=CandidateReviewService(self.inventory,base/'covers');self.ids={r['title_clue']:r['id'] for r in self.service.page()['rows']}
        groups={'Alpha':'unsupported','Beta':'retry','Gamma':'other'}
        self.jobs=[{'job_id':'job-'+name,'state':'needs attention','stage':'checking','reason':'raw '+name,'manifest':{'candidate_id':self.ids[name],'cleanup_policy':{'enabled':False}}} for name in groups]
        self.jobs.append({'job_id':'job-Delta','state':'pending','stage':'queued','reason':'','manifest':{'candidate_id':self.ids['Delta'],'cleanup_policy':{'enabled':False}}})
        def summary(job_ids=None,retry=True):
            values={'job-'+name:{'group':group,'cause':'busy' if group=='retry' else None,'originals_untouched':True} for name,group in groups.items()}
            if retry:values['job-Beta']['retry']={'allowed':True,'reason':''}
            return {k:v for k,v in values.items() if job_ids is None or k in job_ids}
        self.status_calls=0
        def status():
            self.status_calls+=1;return {'jobs':copy.deepcopy(self.jobs)}
        self.audiobooks=Mock(side_effect=lambda identity,jobs=None:{'state':'none','identity':identity,'jobs_given':jobs is not None})
        self.service.jobs=SimpleNamespace(progress_books=lambda:{'converted_ids':set()},converted_ids=lambda:{self.ids['Alpha']},attention_summary=Mock(side_effect=summary),
            jobs=SimpleNamespace(status=status),cleanup=SimpleNamespace(status=lambda _id:None,root=base/'recovery'),current_audiobook=self.audiobooks)
    def names(self,page):return [r['title_clue'] for r in page['rows']]
    def test_attention_order_groups_and_classes(self):
        page=self.service.page(status='output_attention')
        self.assertEqual([r['creation']['job']['attention']['group'] for r in page['rows']],['retry','other','unsupported'])
        self.assertEqual(page['rows'][0]['creation']['job']['retry'],{'allowed':True,'reason':''});self.assertNotIn('retry',page['rows'][2]['creation']['job'])
        for group,expected in (('retry','retry'),('unsupported','unsupported'),('other','other')):
            rows=self.service.page(status='output_attention',group=group)['rows']
            self.assertEqual([r['creation']['job']['attention']['group'] for r in rows],[expected])
        self.assertEqual(self.service.page(status='output_attention',group='all')['total'],3)
        for bad in (('all','retry'),('output_attention','nope')):
            with self.assertRaises(ValueError):self.service.page(status=bad[0],group=bad[1])
    def test_kept_files_books_are_listed_until_kept(self):
        # v0.16.8: a completed book whose recovery copies the backup rule keeps joins the filter in its group.
        self.jobs[3].update(state='completed',stage='done')
        base=self.service.jobs.attention_summary.side_effect;kept=set()
        def summary(job_ids=None,retry=True):
            values=base(job_ids,retry)
            if 'job-Delta' not in kept and (job_ids is None or 'job-Delta' in job_ids):
                values['job-Delta']={'group':'changed','cause':None,'reason':'Original bytes differ from reviewed sources','originals_untouched':False}
                if retry:values['job-Delta']['keep']={'allowed':True,'reason':''}
            return values
        self.service.jobs.attention_summary.side_effect=summary
        self.service.jobs.kept_by_choice=lambda job_ids:{job_id for job_id in job_ids if job_id in kept}
        page=self.service.page(status='output_attention')
        self.assertEqual([r['creation']['job']['attention']['group'] for r in page['rows']],['retry','changed','other','unsupported'],'spec order')
        delta=page['rows'][1]['creation']['job']
        self.assertEqual((delta['state'],delta['keep']),('Audiobook created',{'allowed':True,'reason':''}));self.assertNotIn('kept',delta)
        self.assertEqual(self.names(self.service.page(status='output_attention',group='changed')),['Delta'])
        kept.add('job-Delta')
        self.assertEqual(self.service.page(status='output_attention')['total'],3,'a kept book leaves the filter')
        delta=next(r for r in self.service.page(status='all')['rows'] if r['title_clue']=='Delta')['creation']['job']
        self.assertTrue(delta['kept']);self.assertNotIn('attention',delta);self.assertNotIn('keep',delta)
    def test_job_filters_load_jobs_once_and_render_only_matches(self):
        import groups
        rendered=[];original=groups.render
        with patch.object(groups,'render',side_effect=lambda *args,**kwargs:(rendered.append(args[0]['id']),original(*args,**kwargs))[1]):
            page=self.service.page(status='jobs')
        self.assertEqual([r['id'] for r in page['rows']],[self.ids['Delta']]);self.assertEqual(rendered,[self.ids['Delta']],'only the matching candidate is rendered')
        self.assertEqual(self.status_calls,1,'one jobs list for the whole page')
        self.assertTrue(all(call.kwargs.get('jobs') is not None for call in self.audiobooks.call_args_list))
        self.assertEqual([r['id'] for r in self.service.page(status='converted')['rows']],[self.ids['Alpha']],'converted set from the cached status')


class StateTests(unittest.TestCase):
    def test_space_ready_uses_a_conservative_bound(self):
        from merge_service import MergeService
        s=MergeService.__new__(MergeService);s.stage_root=Path(tempfile.gettempdir())
        manifest={'sources':[{'size':10**9},{'size':10**9}]}
        with patch('merge_service.shutil.disk_usage',return_value=SimpleNamespace(free=12*10**9+64*1024*1024)):self.assertTrue(s._space_ready(manifest))
        with patch('merge_service.shutil.disk_usage',return_value=SimpleNamespace(free=12*10**9)):self.assertFalse(s._space_ready(manifest))
        self.assertFalse(s._space_ready({'sources':[{}]}))
    def test_recovery_idle_answer_is_shared_briefly_but_delete_rechecks(self):
        from merge_service import MergeService
        s=MergeService.__new__(MergeService);calls=[]
        s._recovery_idle=lambda:calls.append(1)
        self.assertIsNone(s._recovery_idle_reason());self.assertIsNone(s._recovery_idle_reason());self.assertEqual(len(calls),1)
        s._idle_cache=(time.monotonic()-2,None);s._recovery_idle_reason();self.assertEqual(len(calls),2)


if __name__=='__main__':unittest.main()
