"""v0.16.6 progress rows: measured conversion steps, finished-book check, cleanup counts and /api/state activities.

The conversion test runs the real automatic normalize pipeline and publication on private generated media
(FFmpeg on PATH, as in check-desktop); everything else uses private SQLite fixtures.
"""
import base64,contextlib,copy,json,shutil,sys,tempfile,threading,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import audio_pipeline
from audio_jobs import AudioJobs,MEASURED
from audio_pipeline import StepProgress,PcmSeconds,create_private,publish,digest,fingerprint,run_owned
from automatic_processing import AutomaticProcessing
from conversion_progress import phase_progress
from encoding_policy import AUTOMATIC_PROFILE,freeze_automatic_policy
from web_server import activities

AREA=Path(__file__).resolve().parents[1]/'scratch'/'progress-rows-tests';AREA.mkdir(parents=True,exist_ok=True)
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
STAGES={'Checking sources':'checking sources','Creating audio':'creating','Checking output':'checking'}


class Done(Exception):pass


class StepProgressTests(unittest.TestCase):
    def test_throttle_clamp_items_and_forced_boundaries(self):
        sent=[];clock=[0.0]
        step=StepProgress(sent.append,'normalizing',100,'seconds',3,clock=lambda:clock[0])
        step.update(10,1);step.update(20,1);clock[0]=.6;step.update(30,2);step.update(500,9,force=True);step.update(-5,0,force=True)
        self.assertEqual([(v['completed'],v['item']) for v in sent],[(10.0,1),(30.0,2),(100.0,3),(0.0,1)])
        self.assertEqual(sent[0],{'phase':'normalizing','completed':10.0,'total':100.0,'unit':'seconds','item':1,'items':3})
        StepProgress(None,'x',10,'bytes').update(5,force=True);StepProgress(sent.append,'x',0,'bytes').update(1,force=True);self.assertEqual(len(sent),4)
    def test_pcm_seconds_counts_decoded_audio(self):
        fed=[];seconds=[]
        meter=PcmSeconds(type('Inner',(),{'feed':lambda self,raw:fed.append(raw)})(),44100,2,8,seconds.append)
        meter.feed(b'\0'*44100*2*8);meter.feed(b'\0'*44100*2*4)
        self.assertEqual(seconds,[1.0,1.5]);self.assertEqual(len(fed),2)


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
    def run_attempt(self,steps):
        results=[];queue=None
        def runner(manifest,stop,checkpoint):
            for stage,value in steps:
                try:
                    checkpoint(stage,{'progress':value} if value is not None else None)
                    results.append(copy.deepcopy(queue._progress[manifest['job_id']]))
                except ValueError as error:results.append(str(error))
            stop.set();raise InterruptedError('fixture stop')
        queue=AudioJobs(Path(self.temp.name)/'catalog.sqlite3',runner,lambda m:True,lambda r:True);self.addCleanup(queue.close)
        manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'sources':[{'path':'C:/x/1.mp3','sha256':'a'*64,'fingerprint':{}}],
                  'metadata':{},'destination':'C:/x/out.m4b','profile':'fixture','evidence':{},'cover':{}}
        queue.enqueue(manifest);queue.resume()
        deadline=time.monotonic()+10
        while queue._thread and queue._thread.is_alive() and time.monotonic()<deadline:time.sleep(.02)
        return results
    def test_measured_steps_per_stage_are_accepted_and_others_refused(self):
        results=self.run_attempt([
            ('checking sources',{'phase':'preparing','completed':1.5,'total':3,'unit':'files','item':2,'items':3}),
            ('checking sources',{'phase':'normalizing','completed':10,'total':60}),
            ('creating',{'phase':'encoding','completed':5,'total':60}),
            ('copying',{'phase':'publishing','completed':100,'total':1000,'unit':'bytes'}),
            ('creating',{'phase':'normalizing','completed':1,'total':2}),
            ('checking sources',{'phase':'preparing','completed':1,'total':3,'unit':'bytes'}),
            ('checking sources',{'phase':'preparing','completed':4,'total':3}),
            ('checking sources',{'phase':'preparing','completed':1,'total':3,'item':4,'items':3}),
            ('checking sources',{'phase':'preparing','completed':1,'total':3,'secret':'x'}),
            ('checking',None)])
        self.assertEqual({k:v for k,v in results[0].items() if k not in ('attempt_id','started')},{'phase':'preparing','completed':1.5,'total':3,'unit':'files','item':2,'items':3})
        self.assertEqual(results[1]['unit'],'seconds');self.assertEqual(results[2]['phase'],'encoding');self.assertEqual(results[3]['unit'],'bytes')
        self.assertEqual(results[4:8],['Unsupported progress measurement','Unsupported progress measurement','Invalid progress denominator','Invalid progress item'])
        self.assertNotIn('secret',results[8]);self.assertEqual(results[9]['phase'],'checking')
        self.assertTrue(all(type(r['started']) is int for r in results if isinstance(r,dict)))
    def test_step_start_is_kept_while_the_same_step_reports(self):
        results=self.run_attempt([('checking sources',{'phase':'normalizing','completed':1,'total':60}),('checking sources',{'phase':'normalizing','completed':2,'total':60})])
        self.assertEqual(results[0]['started'],results[1]['started'])
    def test_phase_progress_passes_measurements_and_step_start(self):
        self.assertEqual(phase_progress('checking sources',{'phase':'normalizing','completed':1,'total':2,'unit':'seconds','item':1,'items':2,'started':5,'attempt_id':'x'}),
                         {'phase':'normalizing','completed':1,'total':2,'unit':'seconds','item':1,'items':2,'started':5})
        self.assertEqual(phase_progress('checking',{'phase':'checking','started':7}),{'phase':'checking','started':7})
        self.assertEqual(phase_progress('checking',None),{'phase':'checking'})


class RealConversionTests(unittest.TestCase):
    """The real automatic normalize path (mixed MP3 + FLAC) and publication, through the real queue checkpoint."""
    def setUp(self):
        if not shutil.which('ffmpeg'):self.skipTest('FFmpeg is required')  # check-desktop always provides it
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.root=Path(self.temp.name);self.addCleanup(self.temp.cleanup)
    def media(self,name,codec,rate,channels,seconds=2):
        path=self.root/'library'/name;path.parent.mkdir(exist_ok=True)
        run_owned([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i',f'sine=frequency=440:duration={seconds}','-ar',str(rate),'-ac',str(channels),'-c:a',codec,str(path)],self.root,threading.Event(),30)
        return path
    def test_every_step_reports_valid_monotonic_measurements(self):
        paths=[self.media('01.mp3','libmp3lame',22050,1),self.media('02.flac','flac',48000,2)]
        cover=self.root/'cover.png';cover.write_bytes(PNG)
        sources=[{'path':str(p),**fingerprint(p),'fingerprint':fingerprint(p),'sha256':digest(p),'metadata':{'tags':{}}} for p in paths]
        manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'root':str(self.root/'library'),'destination':str(self.root/'library'/'Book'/'Book.m4b'),
                  'profile':AUTOMATIC_PROFILE,'encoding_policy':freeze_automatic_policy(sources),'sources':sources,'cover':{'path':str(cover),'sha256':digest(cover)},
                  'comments':'','chapters':[],'metadata':{'title':'Private Book','canonical_author':'Verified Author'},'evidence':{}}
        seen=[];queue=None;published=[]
        def runner(frozen,stop,checkpoint):
            def progress(stage,info):
                checkpoint(STAGES[stage],info);seen.append(copy.deepcopy(queue._progress[frozen['job_id']]))
            output,validation=create_private(frozen,self.root/'stage',stop,progress)
            published.append(publish(output,frozen,validation,stop,lambda stage,details:None,lambda:True,
                                     report=lambda value:(checkpoint('copying',{'progress':value}),seen.append(copy.deepcopy(queue._progress[frozen['job_id']])))))
            raise Done()
        queue=AudioJobs(self.root/'catalog.sqlite3',runner,lambda m:True,lambda r:True);self.addCleanup(queue.close)
        queue.enqueue(manifest);queue.resume()
        deadline=time.monotonic()+240
        while queue._thread and queue._thread.is_alive() and time.monotonic()<deadline:time.sleep(.05)
        row=queue._rows()[0];failure=json.loads(row['journal']).get('failure',{})
        self.assertEqual(failure.get('exception_class'),'Done',row['reason'])  # no measurement was refused
        self.assertTrue(Path(published[0]).is_file())
        measured=[v for v in seen if 'completed' in v]
        phases=[]
        for value in measured:
            if not phases or phases[-1]!=value['phase']:phases.append(value['phase'])
        for expected in ('preparing','source copies','checking audio','normalizing','joined audio','encoding','publishing'):self.assertIn(expected,phases)
        self.assertLess(phases.index('preparing'),phases.index('source copies'));self.assertLess(phases.index('normalizing'),phases.index('joined audio'))
        self.assertLess(phases.index('joined audio'),phases.index('encoding'));self.assertLess(phases.index('encoding'),phases.index('publishing'))
        runs={}
        for value in measured:
            self.assertLessEqual(value['completed'],value['total']);self.assertEqual(value['unit'],MEASURED['copying' if value['phase']=='publishing' else 'creating' if value['phase']=='encoding' else 'checking sources'][value['phase']])
            if value['phase']!='matching format':
                previous=runs.get(value['phase'],-1);self.assertGreaterEqual(value['completed'],previous,value['phase']);runs[value['phase']]=value['completed']
        final={value['phase']:value for value in measured}
        self.assertEqual(final['preparing']['completed'],2);self.assertEqual(final['preparing']['items'],2)
        for phase in ('source copies','normalizing','joined audio','publishing'):self.assertEqual(final[phase]['completed'],final[phase]['total'],phase)
        self.assertAlmostEqual(final['normalizing']['total'],4,delta=.2)


class LockedQueueTests(RealConversionTests):
    """Senua m1: a progress report never waits for the queue lock, so a held lock cannot fail a conversion step."""
    def test_every_step_reports_valid_monotonic_measurements(self):pass  # Covered once above.
    def test_normalize_completes_while_the_queue_lock_is_held(self):
        paths=[self.media('01.mp3','libmp3lame',22050,1),self.media('02.flac','flac',48000,2)]
        cover=self.root/'cover.png';cover.write_bytes(PNG)
        sources=[{'path':str(p),**fingerprint(p),'fingerprint':fingerprint(p),'sha256':digest(p),'metadata':{'tags':{}}} for p in paths]
        manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'root':str(self.root/'library'),'destination':str(self.root/'library'/'Book'/'Book.m4b'),
                  'profile':AUTOMATIC_PROFILE,'encoding_policy':freeze_automatic_policy(sources),'sources':sources,'cover':{'path':str(cover),'sha256':digest(cover)},
                  'comments':'','chapters':[],'metadata':{'title':'Private Book','canonical_author':'Verified Author'},'evidence':{}}
        queue=None;held=threading.Event();release=threading.Event();waits=[]
        def holder():
            with queue._lock:held.set();release.wait(6)  # longer than run_owned's 3 s drain join
        def runner(frozen,stop,checkpoint):
            def progress(stage,info):
                value=(info or {}).get('progress') or {}
                # The m1 case: the lock is taken while an FFmpeg drain thread (not the worker) is reporting.
                if value.get('phase')=='normalizing' and threading.current_thread().name=='BooksArrangerEncodingProgress' and not held.is_set():
                    threading.Thread(target=holder,daemon=True).start();held.wait(5)
                    threading.Timer(4,release.set).start()
                started=time.monotonic();checkpoint(STAGES[stage],info);waits.append((value.get('phase'),time.monotonic()-started,threading.current_thread().name))
            create_private(frozen,self.root/'stage',stop,progress);raise Done()
        queue=AudioJobs(self.root/'catalog.sqlite3',runner,lambda m:True,lambda r:True);self.addCleanup(queue.close)
        original=StepProgress.update  # Unthrottled, so the FFmpeg drain threads report while the lock is held.
        with patch.object(StepProgress,'update',lambda step,completed,item=None,force=False:original(step,completed,item,True)):
            queue.enqueue(manifest);queue.resume()
            deadline=time.monotonic()+240
            while queue._thread and queue._thread.is_alive() and time.monotonic()<deadline:time.sleep(.05)
        release.set();row=queue._rows()[0];failure=json.loads(row['journal']).get('failure',{})
        self.assertTrue(held.is_set(),'positive control: the lock really was held during normalizing')
        self.assertEqual(failure.get('exception_class'),'Done',row['reason'])
        drained=[seconds for phase,seconds,thread in waits if phase in ('normalizing','joined audio','checking audio') and thread!=queue._thread.name]
        self.assertTrue(drained,'reports came from FFmpeg drain threads');self.assertLess(max(drained),.5,'no drain-thread report waited for the lock')
    def test_failing_reporter_never_fails_a_step(self):
        def broken(value):raise RuntimeError('display failed')
        step=StepProgress(broken,'normalizing',10,'seconds',1);step.update(5,force=True)
        meter=PcmSeconds(type('Inner',(),{'feed':lambda self,raw:None})(),1,1,1,broken);meter.feed(b'ab')
        audio_pipeline.EncodingProgress(10,broken).feed(b'out_time_us=1000000'+bytes([10]))


class PublishedCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
    def test_background_and_start_checks_report_books_done(self):
        seen=[];queue=None
        def current(record,stop,pace):
            seen.append(copy.deepcopy(queue.status()['published_check']));return True
        queue=AudioJobs(Path(self.temp.name)/'catalog.sqlite3',None,lambda m:True,lambda r:True);self.addCleanup(queue.close);queue.output_current=current
        for index in range(3):
            manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'sources':[{'path':f'C:/x/{index}.mp3','sha256':'a'*64,'fingerprint':{}}],
                      'metadata':{},'destination':f'C:/x/{index}.m4b','profile':'fixture','evidence':{},'cover':{}}
            job=queue.enqueue(manifest)
            record={'job_id':job,'final_path':f'C:/x/{index}.m4b','sha256':'b'*64,'size':1,'validation':{'passed':True,'checks':'Output checks passed','sha256':'b'*64,'size':1}}
            queue._update(job,state='completed',stage='completed',output=json.dumps(record))
        with patch.object(queue,'_validate_record'):
            queue.start_published_check();queue._verifier.join(10)
            self.assertEqual([(s['kind'],s['completed'],s['total']) for s in seen],[('background',0,3),('background',1,3),('background',2,3)])
            self.assertEqual(len({s['started'] for s in seen}),1);self.assertIsNone(queue.status()['published_check'])
            seen.clear();queue.resume();queue._thread.join(10)
        self.assertEqual([(s['kind'],s['completed']) for s in seen],[('start',0),('start',1),('start',2)]);self.assertIsNone(queue.status()['published_check'])


class CleanupCountTests(unittest.TestCase):
    def test_checking_reports_originals_checked(self):
        from test_cleanup_resume import Book
        with tempfile.TemporaryDirectory(dir=AREA) as folder:
            book=Book(folder)
            try:
                book.enroll();seen=[];original=book.cleanup._match
                def match(handle,source,stored=None,approved=None):
                    seen.append((book.cleanup.status(book.job_id)['state'],book.cleanup.status(book.job_id)['checked']));return original(handle,source,stored,approved)
                with patch.object(book.cleanup,'_match',match):book.cleanup.run(book.cleanup_id)
                self.assertEqual([checked for state,checked in seen if state=='checking'],[0,1,2])
                self.assertEqual(book.cleanup.status(book.job_id)['state'],'completed');self.assertIsNone(book.cleanup.status(book.job_id)['checked'])
            finally:book.close()


class ActivityRowTests(unittest.TestCase):
    def test_rows_kinds_order_measurements_and_step_start(self):
        memo={}
        jobs={'state':'Running','current_title':'Book','progress':{'phase':'normalizing','completed':30,'total':60,'unit':'seconds','item':1,'items':2,'started':111},
              'published_check':{'kind':'background','completed':2,'total':9,'started':222}}
        automatic={'state':'Running','phase':'research','current':{'title':'Дюна','source':'Publisher','stage':'Fetching credits'},'research_pass':{'completed':3,'total':10}}
        rows=activities(jobs,None,None,automatic,memo,now_ms=1000)
        self.assertEqual([r['kind'] for r in rows],['conversion','identity','scan'])
        self.assertEqual(rows[0],{'id':'conversion','kind':'conversion','subject':'Book','step':'normalizing','state':'running','reason':'','done':30,'total':60,'unit':'seconds',
                                  'indeterminate':False,'item':1,'items':2,'step_index':2,'step_count':4,'step_started_at':111})
        self.assertEqual((rows[1]['done'],rows[1]['total'],rows[1]['unit'],rows[1]['step_started_at']),(2,9,'books',222))
        self.assertEqual((rows[2]['step'],rows[2]['step_text'],rows[2]['subject'],rows[2]['done'],rows[2]['step_started_at']),('researching','Publisher - Fetching credits','Дюна',3,1000))
        # The first-seen start is kept while the step continues and resets when it changes.
        self.assertEqual(activities(jobs,None,None,automatic,memo,now_ms=5000)[2]['step_started_at'],1000)
        automatic['current']['title']='Другая';self.assertEqual(activities(jobs,None,None,automatic,memo,now_ms=6000)[2]['step_started_at'],6000)
    def test_cleanup_temporary_scan_and_indeterminate_rows(self):
        rows=activities({'state':'Paused','current_title':'Book','progress':{'phase':'originals','completed':3,'total':9}},{'checked':10,'pending':30,'current':'Z:/a.mp3'},'Audiobooks',None,{},now_ms=1)
        self.assertEqual([(r['kind'],r['state']) for r in rows],[('cleanup','paused'),('scan','running')])
        self.assertEqual((rows[0]['unit'],rows[0]['done']),('files',3));self.assertNotIn('step_index',rows[0])
        self.assertEqual((rows[1]['done'],rows[1]['total'],rows[1]['step_text']),(10,40,'Z:/a.mp3'))
        for phase in ('temporary','folders','recovery copies'):
            self.assertEqual(activities({'state':'Running','current_title':'B','progress':{'phase':phase}},None,None,None,{},now_ms=1)[0]['kind'],'cleanup')
        row=activities({'state':'Needs attention','current_title':'B','progress':{'phase':'checking','reason':'Changed'}},None,None,None,{},now_ms=1)[0]
        self.assertEqual((row['kind'],row['state'],row['reason'],row['indeterminate'],row['step_index']),('conversion','attention','Changed',True,4))
        for bad in ({'completed':5,'total':3},{'completed':1,'total':0},{'completed':'1','total':3},{'completed':float('nan'),'total':3}):
            self.assertTrue(activities({'state':'Running','current_title':'B','progress':{'phase':'encoding',**bad}},None,None,None,{},now_ms=1)[0]['indeterminate'])
        self.assertEqual(activities({},None,None,{'state':'Paused','phase':'research'},{},now_ms=1),[])
    def test_research_pass_counts_this_pass(self):
        run={'phase':'research','checkpoint':json.dumps({'done':['a','b'],'pending':['c'],'deferred':['d','c']})}
        self.assertEqual(AutomaticProcessing._research_pass(run),{'completed':2,'total':4})
        self.assertIsNone(AutomaticProcessing._research_pass({'phase':'discovery','checkpoint':'{}'}));self.assertIsNone(AutomaticProcessing._research_pass(None))
        for raw in ('[1,2]','{"done":[[1]],"pending":{"a":1}}','not json',None,'{"done":"abc"}'):
            self.assertIn(AutomaticProcessing._research_pass({'phase':'research','checkpoint':raw}),(None,{'completed':0,'total':0}),raw)


if __name__=='__main__':unittest.main()
