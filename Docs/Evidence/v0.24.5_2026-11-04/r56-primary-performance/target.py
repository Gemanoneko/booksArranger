import collections,functools,json,os,pathlib,subprocess,sys,threading,time,unittest
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
source=pathlib.Path(os.environ['R56_SOURCE']);fixture=pathlib.Path(os.environ['R56_FIXTURE'])
sys.path[:0]=[str(source),str(source/'tests')];os.chdir(source)
import native_io,audio_jobs,audio_pipeline,merge_service
from test_set_release import SetReleaseTests
from test_approve_as_is import automatic_fixtures
automatic_fixtures.AREA=fixture
stats=collections.defaultdict(list);began=time.perf_counter()
def wrap(owner,name):
 original=getattr(owner,name)
 @functools.wraps(original)
 def timed(*args,**kwargs):
  started=time.perf_counter()
  try:return original(*args,**kwargs)
  finally:stats[name].append(time.perf_counter()-started)
 setattr(owner,name,timed)
for owner,names in ((native_io,('resume_owned_primary',)),(native_io.kernel,('CreateToolhelp32Snapshot',)),(audio_jobs.AudioJobs,('_work_attempt',)),(audio_pipeline,('run_owned',)),(merge_service.MergeService,('_after_completed','resume_press','state'))):
 for name in names:wrap(owner,name)
original=subprocess.Popen.__init__
def popen(self,*args,**kwargs):
 started=time.perf_counter()
 try:return original(self,*args,**kwargs)
 finally:stats['Popen'].append(time.perf_counter()-started)
subprocess.Popen.__init__=popen
case=SetReleaseTests('test_ruling_56_an_approve_leaves_unrelated_paused_jobs_pending_until_start')
result=unittest.TextTestRunner(verbosity=2).run(case)
report={'pass':result.wasSuccessful(),'seconds':time.perf_counter()-began,'case':case.id(),
'stats':{name:{'count':len(values),'seconds':sum(values),'max':max(values)} for name,values in stats.items()}}
pathlib.Path(os.environ['R56_RESULT']).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
sys.exit(not result.wasSuccessful())
