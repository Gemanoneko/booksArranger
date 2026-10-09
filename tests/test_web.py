import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from app import catalog_lock
from metadata import ScanStopped
from scanner import Inventory
from web_server import BrowserServer

SCRATCH = Path(__file__).resolve().parents[1] / 'scratch' / 'web-2026-10-09' / 'tests'
SCRATCH.mkdir(parents=True,exist_ok=True)

class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.base = Path(self.temp.name)
        self.roots = {'Audiobooks':str(self.base/'audio'),'Podcasts':str(self.base/'audio'/'Podcasts'),'Ebooks':str(self.base/'ebooks')}
        for root in self.roots.values():
            Path(root).mkdir(parents=True,exist_ok=True)
        self.database = self.base/'state'/'inventory.sqlite3'
        self.read_delay = 0
        def reader(path,kind,stop):
            if self.read_delay and stop.wait(self.read_delay):
                raise ScanStopped()
            return {'title':'Existing title','author':'Existing artist','tags':{'description':'Сведения <script>test</script>'}}
        self.inventory = Inventory(self.database,self.roots,reader)
        self.server = BrowserServer(('127.0.0.1',0),self.inventory)
        self.thread = threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.02},daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.inventory.stop()
        if self.inventory.worker:
            self.inventory.worker.join(5)
            self.assertFalse(self.inventory.worker.is_alive())
        self.server.shutdown()
        self.thread.join(5)
        self.server.server_close()
        self.temp.cleanup()

    def call(self,path,data=None,headers=None,authorized=True):
        values={'X-Books-Token':self.server.token} if authorized else {}
        if data is not None:
            values['Content-Type']='application/json'
        values.update(headers or {})
        request=urllib.request.Request(self.url+path, data=json.dumps(data).encode() if data is not None else None,headers=values)
        try:
            with urllib.request.urlopen(request,timeout=5) as response:
                return response.status,response.headers,response.read()
        except urllib.error.HTTPError as error:
            try:
                return error.code,error.headers,error.read()
            finally:
                error.close()

    def json_call(self,*args,**kwargs):
        status,headers,raw=self.call(*args,**kwargs)
        return status,json.loads(raw)

    def wait_scan(self):
        self.inventory.worker.join(5)
        self.assertFalse(self.inventory.worker.is_alive())

    def test_health_page_identity_and_source_files_not_served(self):
        code,data=self.json_call('/api/health',authorized=False)
        self.assertEqual(code,200)
        self.assertEqual(data['application'],'Books Arranger')
        self.assertEqual(data['instance'],self.server.instance)
        code,headers,body=self.call('/',authorized=False)
        self.assertEqual(code,200)
        self.assertIn(self.server.token.encode(),body)
        self.assertIn("default-src 'none'",headers['Content-Security-Policy'])
        for path in ('/../../scanner.py','/data/inventory.sqlite3','/api/file?path=Z:/Audiobooks','/VERSION'):
            self.assertEqual(self.call(path)[0],404)

    def test_cross_origin_host_and_token_rejected(self):
        path='/api/state?library=Audiobooks'
        self.assertEqual(self.call(path,authorized=False)[0],403)
        self.assertEqual(self.call(path,headers={'Origin':'https://untrusted.example'})[0],403)
        self.assertEqual(self.call(path,headers={'Host':'untrusted.example'})[0],403)
        self.assertEqual(self.call(path,headers={'Sec-Fetch-Site':'cross-site'})[0],403)
        self.assertEqual(self.call('/api/scan/start',{'library':'Audiobooks'},headers={'Origin':'null'})[0],403)
        self.assertEqual(self.inventory.status('Audiobooks')['state'],'not scanned')

    def test_malformed_payloads_and_configured_roots_only(self):
        for body in ({'library':'Z:/Secret'},{'library':'Audiobooks','command':'ignored'},[],{'library':'Audiobooks','padding':'x'*17000}):
            self.assertEqual(self.call('/api/scan/start',body)[0],400)
        self.assertEqual(self.call('/api/scan/start',{'library':'Audiobooks'},headers={'Content-Type':'text/plain'})[0],400)
        self.assertEqual(self.call('/api/inventory?library=Audiobooks&offset=-1')[0],400)
        self.assertEqual(self.call('/api/state?library=Audiobooks&library=Ebooks')[0],400)
        self.assertEqual(self.call('/api/state?library=Audiobooks&path=anything')[0],400)

    def test_api_incremental_inventory_and_exact_review_fingerprint(self):
        source=Path(self.roots['Ebooks'])/'old.epub'
        source.write_bytes(b'fixture bytes')
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        self.assertEqual(self.call('/api/scan/start',{'library':'Ebooks'})[0],200)
        self.wait_scan()
        code,data=self.json_call('/api/inventory?library=Ebooks')
        self.assertEqual(code,200)
        row=data['rows'][0]
        self.assertIsInstance(row['modified'],str)
        self.assertEqual(int(row['modified']),source.stat().st_mtime_ns)
        review={'original_language':'Other','title':'Book','author':'King Stephen','series':'','number':'','genre':'Horror','topic':'','multi_author':False}
        body={'library':'Ebooks','path':row['path'],'size':row['size'],'modified':row['modified'],'review':review}
        self.assertEqual(self.call('/api/review',body)[0],200)
        preview=self.json_call('/api/inventory?library=Ebooks')[1]['rows'][0]['preview']
        self.assertEqual(preview['confidence'],'Reviewed preview')
        self.assertIn('Horror',preview['path'])
        self.assertEqual(self.call('/api/review',body|{'path':str(self.base/'unknown.epub')})[0],400)
        self.assertEqual(self.call('/api/review',body|{'modified':str(int(row['modified'])+1)})[0],400)
        self.assertEqual(self.call('/api/scan/start',{'library':'Ebooks'})[0],200)
        self.wait_scan()
        self.assertEqual(self.json_call('/api/state?library=Ebooks')[1]['status']['reused'],1)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)

    def test_scan_stop_resume_and_only_one_active_scan(self):
        for index in range(20):
            (Path(self.roots['Audiobooks'])/f'{index:02}.mp3').write_bytes(b'fixture')
        self.read_delay=.1
        self.assertEqual(self.call('/api/scan/start',{'library':'Audiobooks'})[0],200)
        self.assertEqual(self.call('/api/scan/start',{'library':'Ebooks'})[0],400)
        time.sleep(.15)
        self.assertEqual(self.call('/api/scan/stop',{'library':'Audiobooks'})[0],200)
        self.wait_scan()
        before=self.inventory.status('Audiobooks')['count']
        self.assertEqual(self.inventory.status('Audiobooks')['state'],'stopped')
        self.assertEqual(self.call('/api/scan/start',{'library':'Audiobooks'})[0],400)
        self.read_delay=0
        self.assertEqual(self.call('/api/scan/resume',{'library':'Audiobooks'})[0],200)
        self.wait_scan()
        self.assertGreater(self.inventory.status('Audiobooks')['count'],before)
        self.assertEqual(self.inventory.status('Audiobooks')['count'],20)

    def test_catalog_owner_lock_and_strict_port(self):
        with catalog_lock(self.database,self.roots):
            with self.assertRaises((RuntimeError,BlockingIOError)):
                with catalog_lock(self.database,self.roots):
                    self.fail('Two catalog owners were allowed')
        with self.assertRaises(OSError):
            BrowserServer(('127.0.0.1',self.server.server_port),self.inventory)
        with self.assertRaises(ValueError):
            BrowserServer(('0.0.0.0',0),self.inventory)

    def test_shutdown_is_protected_and_controlled(self):
        self.assertEqual(self.call('/api/shutdown',{},authorized=False)[0],403)
        self.assertTrue(self.thread.is_alive())
        self.assertEqual(self.call('/api/shutdown',{'unexpected':True})[0],400)
        self.assertEqual(self.call('/api/shutdown',{})[0],200)
        self.thread.join(5)
        self.assertFalse(self.thread.is_alive())

if __name__=='__main__':
    unittest.main()
