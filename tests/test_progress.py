import copy,json,math,threading,unittest,uuid,tempfile
from pathlib import Path
from audio_pipeline import EncodingProgress
from audio_jobs import AudioJobs
from conversion_progress import approved_scope,completed_book
from encoding_policy import PROFILE,LEGACY_PROFILE
from review_backend import member_key
AREA=Path(__file__).resolve().parents[1]/'scratch'/'progress-folders-2026-10-10'/'progress-fixtures';AREA.mkdir(parents=True,exist_ok=True)

class TelemetryTests(unittest.TestCase):
    def test_split_malformed_bounded_and_monotonic(self):
        values=[];p=EncodingProgress(10,values.append)
        p.feed(b'out_time_us=20');p.feed(b'00000\nout_time_us=N/A\nout_time_us=-1\nout_time_us=1000000\n')
        self.assertEqual([v['completed'] for v in values],[2,2])
        p.feed(b'out_time_us='+b'9'*1000+b'\n');p.feed(b'out_time_us=20000000\n');self.assertEqual(values[-1]['completed'],10)
        p.feed(b'x'*100000);self.assertLessEqual(len(p.pending),65536)
    def test_unknown_denominator_never_reports_percent(self):
        for total in (0,-1,float('nan'),float('inf'),None,'10'):
            values=[];p=EncodingProgress(total,values.append);p.feed(b'out_time_us=5000000\n');self.assertEqual(values,[])

class CompletionTests(unittest.TestCase):
    def setUp(self):
        path=str(AREA/'track.mp3');key=member_key(path)
        self.row={'id':'book','revision':4,'metadata_approved':True,'review':{'title':'Book'},'preview':{'path':'output.m4b'},'members':[{'path':path,'size':9,'modified':'1','metadata':{}}]}
        self.ctx={'metadata_approved':True,'source_coverage_confirmed':True,'order_confirmed':True,'included':[key],'track_order':[key],'source_hashes':{key:{'sha256':'a'*64,'size':9,'modified':'1'}},'cover_id':'cover','cover_choices':[{'id':'cover'}]}
        self.job={'job_id':'job','state':'completed','manifest':{'candidate_id':'book','candidate_revision':4,'metadata':{'title':'Book'},'sources':[{'path':path,'sha256':'a'*64,'size':9,'modified':'1'}],'cover':{'id':'cover'},'profile':PROFILE,'cleanup_policy':{'enabled':True,'empty_source_folders':True}},'output':{'job_id':'job','final_path':'output.m4b','validation':{'passed':True}}}
    def complete(self,source=None,storage=None,folders=None,current=True):
        return completed_book(self.row,self.ctx,self.job,source,storage,folders,current,member_key,PROFILE)
    def test_unqueued_approved_scope_and_stale_membership(self):
        self.assertTrue(approved_scope(self.row,self.ctx,member_key))
        for key in ('metadata_approved','source_coverage_confirmed','order_confirmed'):
            ctx=copy.deepcopy(self.ctx);ctx[key]=False;self.assertFalse(approved_scope(self.row,ctx,member_key))
        self.row['members'][0]['modified']='2';self.assertFalse(approved_scope(self.row,self.ctx,member_key))
    def test_whole_book_waits_for_all_required_cleanup(self):
        done={'state':'completed'}
        self.assertTrue(self.complete(dict(done,recovery={'state':'retained','expires_at':'future'}),done,None));self.assertTrue(self.complete(done,done,{'state':'needs_attention'}))
        self.assertTrue(self.complete(done,done,{'state':'checking'}))
        self.assertTrue(self.complete(done,done,done))
        self.assertTrue(self.complete(done,done,{'state':'unsupported','reason':'Named stream namespace unsupported; folder retained'}))
        for source in ({'state':'paused'},{'state':'needs_attention'},None):self.assertFalse(self.complete(source,done,done))
        self.assertFalse(self.complete(done,{'state':'removing'},done));self.assertFalse(self.complete(done,done,done,current=False))
        self.job['state']='running';self.assertFalse(self.complete(done,done,done))
    def test_historical_policy_keeps_sources_without_retroactive_requirement(self):
        self.job['manifest']['profile']=LEGACY_PROFILE;self.job['manifest']['cleanup_policy']={'enabled':False}
        self.assertTrue(self.complete())
        self.assertFalse(self.complete({'state':'needs_attention'}))
        self.assertFalse(self.complete(storage={'state':'needs_attention'}))
    def test_changed_review_revision_and_cover_excluded(self):
        done={'state':'completed'}
        self.job['manifest']['candidate_revision']=3;self.assertFalse(self.complete(done,done,done))
        self.job['manifest']['candidate_revision']=4;self.ctx['cover_id']='replacement';self.assertFalse(self.complete(done,done,done))

class TransientJobsTests(unittest.TestCase):
    def test_ticks_do_not_write_durable_history_and_restart_resets_attempt(self):
        with tempfile.TemporaryDirectory(dir=AREA) as temp:
            calls=[];first=threading.Event();second=threading.Event();release=threading.Event();release_second=threading.Event()
            def runner(manifest,stop,checkpoint):
                calls.append(manifest['attempt_id']);checkpoint('creating',{})
                if len(calls)==1:
                    for i in range(100):checkpoint('creating',{'progress':{'phase':'encoding','completed':i,'total':100}})
                    first.set();release.wait(3)
                else:second.set();release_second.wait(3)
                raise InterruptedError('fixture pause')
            q=AudioJobs(Path(temp)/'db.sqlite3',runner,lambda m:True,lambda r:True)
            manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'sources':[{'sha256':'a'*64,'fingerprint':{}}],'metadata':{},'destination':'fixture','profile':PROFILE,'evidence':{},'cover':{}}
            q.enqueue(manifest);q.resume();self.assertTrue(first.wait(3))
            raw=q._rows()[0];self.assertEqual(len(json.loads(raw['journal'])['history']),1)
            self.assertEqual(q.status()['jobs'][0]['progress']['completed'],99)
            q.pause();release.set();q._thread.join(3);q.resume();self.assertTrue(second.wait(3));q.pause();release_second.set();q._thread.join(3)
            self.assertNotEqual(calls[0],calls[1]);self.assertNotIn('completed',q.status()['jobs'][0]['progress']);q.close()

if __name__=='__main__':unittest.main()
