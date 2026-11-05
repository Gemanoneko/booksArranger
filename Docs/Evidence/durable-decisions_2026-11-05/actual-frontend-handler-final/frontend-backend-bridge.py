"""Private actual frontend transport / actual Handler bridge; no installed app."""
import hashlib,json,os,pathlib,subprocess,sys,threading,time
from http.server import ThreadingHTTPServer
from unittest.mock import patch
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
root=pathlib.Path(__file__).parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/durable-decisions-20261105')
sys.path[:0]=[str(source),str(source/'tests')]
import test_merge_service
from web_server import Handler
test_merge_service.AREA=root/'bridge-fixtures';test_merge_service.AREA.mkdir(exist_ok=True)
bridge=pathlib.Path(sys.argv[1]);assert bridge.is_file()
participants=[bridge,bridge.parents[1]/'web/app.js',bridge.parents[1]/'web/index.html',bridge.parent/'test_retry_frontend.js']+[source/name for name in ('decision_contract.py','decision_runtime.py','merge_service.py','web_server.py','durable_decisions.py','decision_effects.py','review_backend.py','audio_jobs.py')]
before={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in participants}
results=[]
for action in ('names','review','tracks','metadata_choices','approve','file_review'):
 fixture=test_merge_service.MergeTests();fixture.setUp()
 server=None;thread=None;holder=None;release=threading.Event();entered=threading.Event()
 try:
  row=fixture.service.reviews.page()['rows'][0];snapshot=fixture.service.reviews.metadata_questions(row,fixture.service.reviews._context(row))
  choices=[{'question_id':question['id'],'mode':'unresolved'} for question in snapshot['questions']]
  payload={'names':{'title':'Сохранённое название — Ѣ'}} if action=='names' else {'review':fixture.review,'approve':False,'names_row_only':True} if action=='review' else {
   'order':row['track_order'],'included':row['included'],'source_coverage_confirmed':True,'order_confirmed':True,'chapters':False} if action=='tracks' else {
   'signature':snapshot['signature'],'choices':choices} if action=='metadata_choices' else {'title':'Private approved title','author':'Private Author','names':None,'without_missing':False,'choice':None,'path':None}
  if action=='file_review':
   path=fixture.sources[0];stat=path.stat();payload={'path':str(path),'size':stat.st_size,'modified':str(stat.st_mtime_ns),'review':fixture.review}
   row={'path':str(path),'size':stat.st_size,'modified':str(stat.st_mtime_ns),'kind':'audiobook','review':fixture.review,'metadata':{}}
  original=[path.read_bytes() for path in fixture.sources]
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  address=server.server_address
  server.server_address=address;server.server_port=address[1];server.inventory=fixture.inv;server.merge=fixture.service
  server.token='private-bridge-token';server.instance='private-bridge';server.closing=False
  server.origins={'http://127.0.0.1:'+str(address[1]),'http://localhost:'+str(address[1])}
  server.active_library=None;server.loaded_version='private-bridge';server.restart_context=None;server.recovery_operations=0
  server.control_lock=threading.Lock();server.control_condition=threading.Condition(server.control_lock);server.merge_admissions=0
  thread=threading.Thread(target=server.serve_forever,name='PrivateDecisionHTTPBridge');thread.start()
  def hold():
   with fixture.service.operation_lock,fixture.service.reviews.lock,fixture.inv.group_lock,fixture.service.jobs._lock:entered.set();release.wait(30)
  holder=threading.Thread(target=hold,name='PrivateUnrelatedBook');holder.start();assert entered.wait(2)
  config={'baseURL':'http://127.0.0.1:'+str(address[1]),'token':server.token,'row':row,'action':action,'payload':payload,'library':'Audiobooks'}
  config_path=root/('bridge-'+action+'.json');config_path.write_text(json.dumps(config,ensure_ascii=False)+'\n',encoding='utf-8')
  with patch.object(fixture.service,'_approval_result',side_effect=ValueError('Private source-identity review required')):
   started=time.monotonic()
   child=subprocess.run(['C:/Program Files/nodejs/node.exe',str(bridge),str(config_path)],cwd=str(bridge.parents[1]),capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   output=child.stdout.decode('utf-8');error=child.stderr.decode('utf-8')
   (root/('bridge-'+action+'.stdout.log')).write_text(output,encoding='utf-8');(root/('bridge-'+action+'.stderr.log')).write_text(error,encoding='utf-8')
   if child.returncode:raise RuntimeError(action+' frontend bridge failed: '+output+'\n'+error)
   results.append({'action':action,'seconds':round(time.monotonic()-started,4),'frontend_exit':child.returncode,'stdout_sha256':hashlib.sha256(child.stdout).hexdigest(),'output':output})
  assert [path.read_bytes() for path in fixture.sources]==original
  # Actual HTTP proof completed while all four locks were still held. Close
  # this private application owner before releasing the holder, then inspect;
  # the observer must not wait on the same intentionally held jobs lock.
  fixture.service.decisions.close();release.set();holder.join(5);assert not holder.is_alive()
  assert fixture.service.jobs.status()['jobs']==[]
 finally:
  fixture.service.decisions.close();release.set()
  if holder:holder.join(5);assert not holder.is_alive()
  if server:server.shutdown();server.server_close()
  if thread:thread.join(5);assert not thread.is_alive()
  fixture.tearDown()
after={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in participants};assert before==after,'A bridge participant changed during the owned run'
print('ACTUAL_FRONTEND_HANDLER_BRIDGE '+json.dumps({'participants':before,'results':results},ensure_ascii=True))
