"""Real private Windows host/engine generation and graceful checkpoint integration."""
import ctypes,json,os,queue,subprocess,sys,tempfile,threading,time,unittest,urllib.request
from pathlib import Path
from desktop_host import owner_proof
from native_io import OwnedProcessJob
BASE=Path(__file__).resolve().parents[1];AREA=BASE/'scratch'/'desktop-host-tests';AREA.mkdir(parents=True,exist_ok=True)
def stage_private_backend(base):
 import shutil
 installed=base/'installed-backend';installed.mkdir()
 # Exact small backend fixture, data is a sibling outside installation. This
 # exercises the production install-root exclusion without weakening it.
 for source in BASE.glob('*.py'):shutil.copyfile(source,installed/source.name)
 for name in ('replacement_eye_plan.json','public_source_leads.json','package.json'):shutil.copyfile(BASE/name,installed/name)
 return installed
class NativeHostTests(unittest.TestCase):
 def test_retained_handle_proves_exact_generation_and_runtime(self):
  p=subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(1)'],creationflags=0x4|subprocess.CREATE_NO_WINDOW)
  p._books_suspended=True
  with OwnedProcessJob(p):
   proof=owner_proof(p)
   self.assertEqual(proof['pid'],p.pid);self.assertEqual(Path(proof['image']).resolve(),Path(sys.executable).resolve());self.assertTrue(proof['creation_filetime'].isdigit());p.wait(5)
 def test_real_host_new_catalog_is_paused_and_quits_with_record_removed(self):
  with tempfile.TemporaryDirectory(dir=AREA) as temp:
   base=Path(temp);installed=stage_private_backend(base);data=base/'data';roots={name:str(base/name) for name in ('Audiobooks','Podcasts','Ebooks')};rootsfile=base/'roots.json';rootsfile.write_text(json.dumps(roots));token='e'*64
   env=os.environ.copy();env['BOOKS_ARRANGER_DESKTOP_TOKEN']=token
   p=subprocess.Popen([sys.executable,'-I','-B',str(installed/'desktop_host.py'),'--database',str(data/'inventory.sqlite3'),'--roots-json',str(rootsfile),'--port','5212','--catalog-mode=new'],cwd=BASE,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x4|subprocess.CREATE_NO_WINDOW)
   p._books_suspended=True
   with OwnedProcessJob(p):
    lines=queue.Queue();threading.Thread(target=lambda:[lines.put(line) for line in iter(p.stdout.readline,b'')],daemon=True).start()
    line=lines.get(timeout=10).decode();self.assertTrue(line.startswith('BOOKS_ENGINE_OWNER '));proof=json.loads(line.split(' ',1)[1]);self.assertEqual(proof['host_pid'],p.pid)
    def get(route):
     req=urllib.request.Request('http://127.0.0.1:5212'+route,headers={'X-Books-Desktop':token});return json.load(urllib.request.urlopen(req,timeout=2))
    deadline=time.monotonic()+25;health=None
    while time.monotonic()<deadline:
     if p.poll() is not None:raise AssertionError('Host startup failed: '+p.stderr.read().decode(errors='replace'))
     try:health=get('/api/health');break
     except OSError:time.sleep(.1)
    self.assertIsNotNone(health);self.assertEqual(health['pid'],proof['pid']);self.assertEqual(health['application'],'Books Arranger')
    # 0.22.1 (ruling 28): health answers while the catalog still loads; idle is reported once loading has ended.
    deadline=time.monotonic()+25;desktop=get('/api/desktop/status')
    while (desktop.get('loading') or {}).get('took_ms') is None and time.monotonic()<deadline:time.sleep(.1);desktop=get('/api/desktop/status')
    self.assertIsInstance(desktop['loading']['took_ms'],int);self.assertTrue(desktop['idle']);self.assertEqual(desktop['busy']['queued'],0)
    record=data/'web-instance.json';self.assertTrue(record.exists())
    req=urllib.request.Request('http://127.0.0.1:5212/api/desktop/quit',data=b'{}',headers={'X-Books-Desktop':token,'Content-Type':'application/json'},method='POST');self.assertEqual(urllib.request.urlopen(req,timeout=2).status,202)
    p.wait(15);self.assertEqual(p.returncode,0);self.assertFalse(record.exists())
    self.assertTrue((data/'inventory.sqlite3').exists())
    # The prior exact engine is gone. Its valid record is archived on the real
    # existing-folder startup before Inventory is reconstructed.
    old_record=json.dumps(health|{'url':'http://127.0.0.1:5212/'}).encode();record.write_bytes(old_record)
    second=subprocess.Popen([sys.executable,'-I','-B',str(installed/'desktop_host.py'),'--database',str(data/'inventory.sqlite3'),'--roots-json',str(rootsfile),'--port','5212','--catalog-mode=existing'],cwd=installed,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x4|subprocess.CREATE_NO_WINDOW)
    second._books_suspended=True
    with OwnedProcessJob(second):
     second_lines=queue.Queue();threading.Thread(target=lambda:[second_lines.put(line) for line in iter(second.stdout.readline,b'')],daemon=True).start()
     second_proof=json.loads(second_lines.get(timeout=10).decode().split(' ',1)[1]);deadline=time.monotonic()+25;current=None
     while time.monotonic()<deadline:
      if second.poll() is not None:raise AssertionError('Existing startup failed: '+second.stderr.read().decode(errors='replace'))
      try:current=get('/api/health');break
      except OSError:time.sleep(.1)
     self.assertIsNotNone(current);self.assertEqual(current['pid'],second_proof['pid']);self.assertNotEqual(current['pid'],proof['pid'])
     archived=list(data.glob('web-instance.stale-*'));self.assertEqual(len(archived),1);self.assertEqual(archived[0].read_bytes(),old_record)
     req=urllib.request.Request('http://127.0.0.1:5212/api/desktop/quit',data=b'{}',headers={'X-Books-Desktop':token,'Content-Type':'application/json'},method='POST');urllib.request.urlopen(req,timeout=2).close();second.wait(15);self.assertEqual(second.returncode,0);self.assertFalse(record.exists())
    for stream in (second.stdin,second.stdout,second.stderr):stream.close()
   for stream in (p.stdin,p.stdout,p.stderr):stream.close()

class StartupBoundaryIntegrationTests(unittest.TestCase):
 def invoke(self,base,data,mode):
  installed=stage_private_backend(base)
  roots={name:str(base/name) for name in ('Audiobooks','Podcasts','Ebooks')};rootsfile=base/'roots.json';rootsfile.write_text(json.dumps(roots));env=os.environ.copy();env['BOOKS_ARRANGER_DESKTOP_TOKEN']='f'*64
  return subprocess.run([sys.executable,'-I','-B',str(installed/'desktop_backend.py'),'--database',str(data/'inventory.sqlite3'),'--roots-json',str(rootsfile),'--port','5212','--catalog-mode='+mode],env=env,cwd=BASE,capture_output=True,text=True,timeout=20)
 def test_actual_saved_existing_missing_folder_is_not_recreated(self):
  with tempfile.TemporaryDirectory(dir=AREA) as temp:
   base=Path(temp);data=base/'missing-existing';result=self.invoke(base,data,'existing')
   self.assertNotEqual(result.returncode,0);self.assertFalse(data.exists())
 def test_actual_final_guard_refuses_changed_database_before_schema_or_lock_write(self):
  with tempfile.TemporaryDirectory(dir=AREA) as temp:
   base=Path(temp);data=base/'data';data.mkdir();db=data/'inventory.sqlite3';raw=b'changed unsupported catalog';db.write_bytes(raw)
   result=self.invoke(base,data,'existing');self.assertNotEqual(result.returncode,0);self.assertEqual(db.read_bytes(),raw);self.assertFalse(Path(str(db)+'.lock').exists());self.assertFalse((data/'web-instance.json').exists())
 def test_actual_stale_callback_runs_before_inventory_mutation_and_preserves_unknown_record(self):
  import sqlite3,hashlib
  from contextlib import closing
  with tempfile.TemporaryDirectory(dir=AREA) as temp:
   base=Path(temp);data=base/'data';data.mkdir();db=data/'inventory.sqlite3'
   with closing(sqlite3.connect(db)) as connection:connection.executescript('CREATE TABLE jobs(root);CREATE TABLE queue(root);CREATE TABLE files(root,path,size,modified,kind);')
   before=hashlib.sha256(db.read_bytes()).hexdigest();record=data/'web-instance.json';raw=b'{"application":"Other","pid":99999999}';record.write_bytes(raw)
   result=self.invoke(base,data,'existing');self.assertNotEqual(result.returncode,0);self.assertIn('Unknown ownership record',result.stderr);self.assertEqual(record.read_bytes(),raw);self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),before);self.assertEqual(list(data.glob('web-instance.stale-*')),[])
 def test_actual_explicit_new_rejects_existing_nonempty_folder_before_lock_write(self):
  with tempfile.TemporaryDirectory(dir=AREA) as temp:
   base=Path(temp);data=base/'data';data.mkdir();sentinel=data/'keep.txt';sentinel.write_bytes(b'unique')
   result=self.invoke(base,data,'new');self.assertNotEqual(result.returncode,0);self.assertEqual(sentinel.read_bytes(),b'unique');self.assertFalse((data/'inventory.sqlite3').exists());self.assertFalse((data/'inventory.sqlite3.lock').exists())
