"""Real private Windows host/engine generation and graceful checkpoint integration."""
import ctypes,json,os,queue,subprocess,sys,tempfile,threading,time,unittest,urllib.request
from pathlib import Path
from desktop_host import owner_proof
from native_io import OwnedProcessJob
BASE=Path(__file__).resolve().parents[1];AREA=BASE/'scratch'/'desktop-host-tests';AREA.mkdir(parents=True,exist_ok=True)
class NativeHostTests(unittest.TestCase):
 def test_retained_handle_proves_exact_generation_and_runtime(self):
  p=subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(1)'],creationflags=0x4|subprocess.CREATE_NO_WINDOW)
  p._books_suspended=True
  with OwnedProcessJob(p):
   proof=owner_proof(p)
   self.assertEqual(proof['pid'],p.pid);self.assertEqual(Path(proof['image']).resolve(),Path(sys.executable).resolve());self.assertTrue(proof['creation_filetime'].isdigit());p.wait(5)
 def test_real_host_new_catalog_is_paused_and_quits_with_record_removed(self):
  with tempfile.TemporaryDirectory(dir=AREA) as temp:
   base=Path(temp);data=base/'data';roots={name:str(base/name) for name in ('Audiobooks','Podcasts','Ebooks')};rootsfile=base/'roots.json';rootsfile.write_text(json.dumps(roots));token='e'*64
   env=os.environ.copy();env['BOOKS_ARRANGER_DESKTOP_TOKEN']=token
   p=subprocess.Popen([sys.executable,'-I','-B',str(BASE/'desktop_host.py'),'--database',str(data/'inventory.sqlite3'),'--roots-json',str(rootsfile),'--port','5212','--catalog-mode=new'],cwd=BASE,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x4|subprocess.CREATE_NO_WINDOW)
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
    desktop=get('/api/desktop/status');self.assertTrue(desktop['idle']);self.assertEqual(desktop['busy']['queued'],0)
    record=data/'web-instance.json';self.assertTrue(record.exists())
    req=urllib.request.Request('http://127.0.0.1:5212/api/desktop/quit',data=b'{}',headers={'X-Books-Desktop':token,'Content-Type':'application/json'},method='POST');self.assertEqual(urllib.request.urlopen(req,timeout=2).status,202)
    p.wait(15);self.assertEqual(p.returncode,0);self.assertFalse(record.exists())
    self.assertTrue((data/'inventory.sqlite3').exists())
   for stream in (p.stdin,p.stdout,p.stderr):stream.close()
