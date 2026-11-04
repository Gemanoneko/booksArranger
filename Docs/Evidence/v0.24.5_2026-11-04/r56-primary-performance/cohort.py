import json,os,pathlib,subprocess,sys,time
root=pathlib.Path(__file__).resolve().parent
cases=[
'test_approve_as_is.ApproveAsIsTests.test_no_author_anywhere_approved_as_is_goes_to_bez_avtora_and_the_preview_path_is_the_one_used',
'test_approve_as_is.ApproveAsIsTests.test_typed_title_and_author_are_used_and_saved_as_entered_by_you',
'test_approve_as_is.ApproveAsIsTests.test_approve_overrides_an_order_hold_and_a_taken_name_is_never_overwritten',
'test_approve_as_is.ApproveAsIsTests.test_convert_whats_there_leaves_out_the_missing_file',
'test_approve_as_is.ApproveAsIsTests.test_saved_values_are_the_identity_without_any_other_source',
'test_set_release.SetReleaseTests.test_ruling_57_approve_one_does_not_release_the_other_even_after_start',
'test_set_release.SetReleaseTests.test_ruling_56_a_paused_run_stays_paused',
'test_set_release.SetReleaseTests.test_m12_discworld_correction_does_not_rename_other_folders',
'test_set_release.SetReleaseTests.test_m11_ruling_33_approve_as_shown',
'test_set_release.SetReleaseTests.test_m11_no_author_approve_as_shown',
'test_set_release.SetReleaseTests.test_m11_two_people_approve_as_shown',
'test_set_release.SavedSeriesReceiptTests.test_saved_answer_then_same_press_title_series_queues_only_until_explicit_start']
peer=r"""
import os,pathlib,sys,time,unittest
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
source=pathlib.Path(os.environ['R56_SOURCE'])
sys.path[:0]=[str(source),str(source/'tests')]
from test_approve_as_is import automatic_fixtures
automatic_fixtures.AREA=pathlib.Path(os.environ['R56_FIXTURE'])
stop=pathlib.Path(os.environ['R56_STOP'])
for name in sys.argv[1:]:
 if stop.exists():break
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(name))
 if not result.wasSuccessful():sys.exit(1)
"""
summaries={}
for phase in ('baseline','corrected'):
 base=root/phase;source=base/'src';stop=base/'stop';children=[];records=[];started=time.monotonic()
 commands=[('-c',peer,*(cases[index:]+cases[:index])) for index in range(12)]+[(str(root/'target.py'),)]
 try:
  for index,args in enumerate(commands):
   fixture=base/('f%x'%index);temp=base/('t%x'%index)
   fixture.mkdir();temp.mkdir()
   env=dict(os.environ,R56_SOURCE=str(source),R56_FIXTURE=str(fixture),R56_STOP=str(stop),R56_RESULT=str(base/'target.json'),
            BOOKS_QA_RUN_ROOT=str(source),BOOKS_QA_FIXTURE_ROOT=str(fixture),TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp))
   log=open(base/('worker-%02d.log'%index),'wb')
   child=subprocess.Popen([sys.executable,'-I','-B',*args],cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=0x08000000)
   children.append((index,child,log))
   if index==11:time.sleep(8)
  while children:
   if time.monotonic()-started>240:raise TimeoutError('Focused cohort did not close; stop without duplicate')
   for item in children[:]:
    index,child,log=item
    if child.poll() is None:continue
    records.append({'worker':index,'code':child.returncode,'seconds':time.monotonic()-started})
    if index==12:stop.touch()
    log.close();children.remove(item)
   time.sleep(.1)
 finally:
  for index,child,log in children:
   if child.poll() is None:child.terminate()
   child.wait(timeout=3);log.close()
 summaries[phase]={'children':records,'seconds':time.monotonic()-started,'target':json.loads((base/'target.json').read_text(encoding='utf-8'))}
 print(phase,json.dumps(summaries[phase]),flush=True)
(root/'cohort-summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
sys.exit(not all(value['target']['pass'] and all(row['code']==0 for row in value['children']) for value in summaries.values()))
