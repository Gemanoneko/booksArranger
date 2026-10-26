import contextlib
import hashlib
import sys
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import Mock, patch

from catalog_owner import catalog_lock
from metadata import ScanStopped
from scanner import Inventory, connect
from scan_wait import close_scan, finish_scan
from web_server import BrowserServer, Handler

SCRATCH = Path(__file__).resolve().parents[1] / 'scratch' / 'web-2026-10-09' / 'tests'
SCRATCH.mkdir(parents=True,exist_ok=True)

class ResponseWriteTests(unittest.TestCase):
    def handler(self):
        handler=Handler.__new__(Handler)
        handler.close_connection=False
        handler.send_response=Mock()
        handler.send_header=Mock()
        handler.end_headers=Mock()
        handler.wfile=Mock()
        handler.trusted=Mock(return_value=True)
        handler.query=Mock(return_value=('/api/health',{}))
        handler.server=SimpleNamespace(health=lambda:{'application':'Books Arranger'})
        return handler

    def test_disconnected_headers_do_not_trigger_second_error_reply(self):
        handler=self.handler()
        handler.end_headers.side_effect=ConnectionAbortedError(10053,'Fixture disconnected client')
        handler.do_GET()
        handler.send_response.assert_called_once_with(200)
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_not_called()
        self.assertTrue(handler.close_connection)

    def test_disconnected_body_closes_only_that_request(self):
        for exception in (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
            with self.subTest(exception=exception.__name__):
                handler=self.handler()
                handler.wfile.write.side_effect=exception('Fixture disconnected client')
                handler.do_GET()
                handler.send_response.assert_called_once_with(200)
                handler.wfile.write.assert_called_once()
                self.assertTrue(handler.close_connection)

    def test_connected_backend_failure_keeps_existing_error_response(self):
        handler=self.handler()
        handler.query.return_value=('/api/state',{'library':'Audiobooks'})
        handler.library=Mock(return_value='Audiobooks')
        handler.server.state=Mock(side_effect=RuntimeError('Fixture backend failure'))
        handler.do_GET()
        handler.send_response.assert_called_once_with(500)
        body=json.loads(handler.wfile.write.call_args.args[0])
        self.assertEqual(body,{'error':'Local catalog request failed; source files remain untouched'})
        self.assertFalse(handler.close_connection)

    def test_unexpected_io_error_is_not_silenced_as_disconnect(self):
        handler=self.handler()
        failure=OSError(5,'Fixture unexpected I/O error')
        handler.end_headers.side_effect=failure
        with self.assertRaises(OSError) as caught:
            handler.response(200,{'ok':True})
        self.assertIs(caught.exception,failure)
        handler.wfile.write.assert_not_called()
        self.assertFalse(handler.close_connection)

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
        # These HTTP fixtures do not exercise retention. Its startup admission
        # must not race a request that deliberately expects an idle server.
        with patch('merge_service.MergeService.start_retention'):
            self.server = BrowserServer(('127.0.0.1',0),self.inventory)
        self.thread = threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.02},daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        close_scan(self.inventory)
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
        finish_scan(self.inventory)

    def test_every_attention_chip_is_served_through_the_http_route(self):
        # Futaba's 0.22.0 QA blocker: the route checked `group` against its own older set, so every "Needs your answer"
        # chip (and Reacquire) answered 400 "Unknown attention group" and bulk Approve as is could not be reached; the tests
        # called review_backend directly. Every chip the page sends (web/app.js attentionKeys) goes through the real route.
        import re
        script=(Path(__file__).resolve().parents[1]/'web'/'app.js').read_text('utf8')
        needs=re.search(r"const NEEDS_KEYS=\[([^\]]*)\]",script)[1]
        chips=re.findall(r"'([a-z_]+)'",re.search(r"const attentionKeys=\[([^\]]*)\]",script)[1].replace('...NEEDS_KEYS',needs))
        self.assertGreaterEqual(len(chips),17,chips)
        for group in chips:
            code,page=self.json_call('/api/inventory?library=Audiobooks&view=candidates&status=output_attention&group='+group)
            self.assertEqual(code,200,(group,page));self.assertEqual(page['rows'],[],group)
        code,page=self.json_call('/api/inventory?library=Audiobooks&view=candidates&status=output_attention&group=no_such_chip')
        self.assertEqual((code,page['error']),(400,'Unknown attention group'),'positive control: an unknown chip is still refused')
        # One list: the server's chips are exactly the page's, and the counts in the status carry every one of them.
        from review_backend import ATTENTION_GROUPS
        self.assertEqual(sorted(chips),sorted(ATTENTION_GROUPS))
        self.assertEqual(set(self.server.merge.state()['attention_counts']),ATTENTION_GROUPS-{'all'})

    def test_delete_book_routes_answer_typed_refusals_over_http(self):
        # Ruling 23 (Delete book): both routes through the real server, with the token, typed. A book that is not current
        # is a typed refusal before anything is touched: 200 with the refusal for the preview, 409 with its code for delete.
        import uuid
        identity=str(uuid.uuid4())
        code,preview=self.json_call('/api/candidate/delete-preview',{'library':'Audiobooks','id':identity,'revision':1})
        self.assertEqual((code,preview['files'],preview['refusal']['code']),(200,[],'changed'))
        code,refused=self.json_call('/api/candidate/delete',{'library':'Audiobooks','id':identity,'revision':1,'paths':[]})
        self.assertEqual((code,refused['code']),(409,'changed'))
        self.assertEqual(self.call('/api/candidate/delete',{'library':'Audiobooks','id':identity,'revision':1,'paths':'Z:/x'})[0],400,'paths must be a list')
        # Remove this copy (ruling 25) is mode 'copy' on the same routes; folders (ruling 24) are listed paths too.
        code,preview=self.json_call('/api/candidate/delete-preview',{'library':'Audiobooks','id':identity,'revision':1,'mode':'copy'})
        self.assertEqual((code,preview['refusal']['code'],preview['sorted']),(200,'changed',None))
        code,refused=self.json_call('/api/candidate/delete',{'library':'Audiobooks','id':identity,'revision':1,'paths':[],'folders':[],'mode':'copy'})
        self.assertEqual((code,refused['code']),(409,'changed'))
        self.assertEqual(self.call('/api/candidate/delete-preview',{'library':'Audiobooks','id':identity,'revision':1,'mode':'everything'})[0],400,'a known mode only')
        self.assertEqual(self.call('/api/candidate/delete',{'library':'Audiobooks','id':identity,'revision':1,'paths':[],'folders':'Z:/x'})[0],400,'folders must be a list')
        self.assertEqual(self.call('/api/candidate/delete-preview',{'library':'Audiobooks','id':identity,'revision':1,'folders':[]})[0],400,'the preview takes no folders')
        # Senua's 0.22.0 final review, N13: while a library scan runs both routes refuse like Keep and Convert, typed (busy),
        # so the dialog says "Nothing was deleted"; the service is not asked at all.
        with patch.object(self.server,'scan_active',return_value=True),patch.object(self.server.merge,'delete_preview',return_value={'files':[],'bytes':0,'kind':'files_missing','refusal':None}) as asked_preview,patch.object(self.server.merge,'delete_book',return_value={'deleted':0,'bytes':0,'failed':[],'forgotten':True}) as asked_delete:
            code,preview=self.json_call('/api/candidate/delete-preview',{'library':'Audiobooks','id':identity,'revision':1})
            self.assertEqual((code,preview['files'],preview['refusal']),(200,[],{'code':'busy','message':'This book is being processed. Nothing was deleted.'}))
            code,refused=self.json_call('/api/candidate/delete',{'library':'Audiobooks','id':identity,'revision':1,'paths':[]})
            self.assertEqual((code,refused['code'],refused['message']),(409,'busy','This book is being processed. Nothing was deleted.'))
            asked_preview.assert_not_called();asked_delete.assert_not_called()
        # A refused POST reads its body before the 403 (Handler.refuse), so the client gets the 403, not a reset. Without it a
        # 200 KB body was reset (ConnectionAbortedError, WinError 10053) in 2 of 3 runs alone, and two gate runs failed so.
        for _ in range(20):
            self.assertEqual(self.call('/api/candidate/delete',{'library':'Audiobooks','id':identity,'revision':1,'paths':['x'*4000]*50},authorized=False)[0],403,'the token is required')

    def test_retry_repair_and_delete_queue_over_http_while_a_scan_runs(self):
        # 0.22.1 (backlog 2 and 3; Judy's spec section 1 and 6): with queue: true the three presses are accepted and queued
        # while a scan runs (202 queued, position, blocker); /api/state carries the queue; Cancel takes one out, and is
        # too late (409 started) once it is gone. Without queue: true the scan refusals stand (control).
        import uuid
        book,job,other=str(uuid.uuid4()),str(uuid.uuid4()),str(uuid.uuid4())
        merge=self.server.merge
        with patch.object(self.server,'scan_active',return_value=True),patch.object(merge,'retry_blocked_job') as retried,patch.object(merge,'repair_blocked_job') as repaired,patch.object(merge,'delete_book') as deleted,\
             patch.object(merge,'delete_preview',return_value={'files':[{'path':'Z:/a.mp3','size':1,'kind':'audio'}],'bytes':1,'folders':[],'stay':{'items':0},'last_copy':None,'sorted':None,'kind':'files_missing','refusal':None,'blocked':{'kind':'scan'}}) as previewed:
            code,refused=self.json_call('/api/audiobook/retry',{'library':'Audiobooks','id':book,'revision':1,'job_id':job})
            self.assertEqual((code,refused['error']),(409,'Scanning is running. Retry when it stops.'),'control: a press without queue is refused as before')
            code,first=self.json_call('/api/audiobook/retry',{'library':'Audiobooks','id':book,'revision':1,'job_id':job,'queue':True,'title':'Лабиринты Ехо 3'})
            self.assertEqual((code,first['queued'],first['position'],first['blocker']),(202,True,1,{'kind':'scan'}))
            code,preview=self.json_call('/api/candidate/delete-preview',{'library':'Audiobooks','id':other,'revision':2,'queue':True})
            self.assertEqual((code,preview['refusal'],preview['blocked'],len(preview['files'])),(200,None,{'kind':'scan'},1),'the list and what it waits for, not a busy refusal')
            self.assertEqual(previewed.call_args.kwargs,{'wait':True})
            code,second=self.json_call('/api/candidate/delete',{'library':'Audiobooks','id':other,'revision':2,'paths':['Z:/a.mp3'],'folders':[],'queue':True,'title':'Новая плоть'})
            self.assertEqual((code,second['position'],second['blocker']),(202,2,{'kind':'scan'}))
            retried.assert_not_called();deleted.assert_not_called();repaired.assert_not_called()
            code,state=self.json_call('/api/state?library=Audiobooks')
            self.assertEqual([(item['id'],item['action'],item['book_id'],item['position'],item['title']) for item in state['queued_actions']],
                             [(first['id'],'retry',book,1,'Лабиринты Ехо 3'),(second['id'],'delete',other,2,'Новая плоть')])
            self.assertEqual((state['queue_running'],state['queue_outcomes']),(None,[]))
            self.assertEqual(self.json_call('/api/queue/cancel',{'id':second['id']}),(200,{'cancelled':True}))
            self.assertEqual(self.json_call('/api/queue/cancel',{'id':second['id']}),(409,{'error':'It has already started.','code':'started'}),'gone: too late')
            self.server.actions.drop()
        self.assertEqual(self.call('/api/audiobook/retry',{'library':'Audiobooks','id':book,'revision':1,'job_id':job,'queue':'yes'})[0],400,'an explicit boolean')
        self.assertEqual(self.call('/api/candidate/delete-preview',{'library':'Audiobooks','id':other,'revision':2,'queue':True,'mode':'copy'})[0],400,'Remove this copy does not queue')
        # Retry all leaves queued presses out (Judy 1.3); with nothing queued it is asked exactly as before.
        with patch.object(merge,'retry_all',return_value={'id':'run','state':'running','total':2}) as asked,patch.object(self.server.actions,'queued_jobs',return_value={job}):
            self.assertEqual(self.call('/api/audiobook/retry-all',{'library':'Audiobooks'})[0],202)
            asked.assert_called_once_with(skip={job})
        # Nothing waits and nothing blocks: the press runs at once and answers as before.
        with patch.object(merge,'retry_blocked_job',return_value={'job_id':job,'requeued':True}) as retried:
            code,ran=self.json_call('/api/audiobook/retry',{'library':'Audiobooks','id':book,'revision':1,'job_id':job,'queue':True})
            self.assertEqual((code,ran),(202,{'job_id':job,'requeued':True}))
            retried.assert_called_once_with('Audiobooks',book,1,job)

    def test_a_refused_post_stops_draining_its_body_after_two_seconds_in_all(self):
        # Senua's 0.22.0 final review, N17: the drain before a 403 timed out per read, so a sender trickling its body held
        # the handler for as long as it kept sending. The 2 s are now a total: the 403 arrives while bytes still trickle.
        import socket
        port=self.server.server_port
        sender=socket.create_connection(('127.0.0.1',port),timeout=6);self.addCleanup(sender.close)
        sender.sendall(('POST /api/candidate/delete HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nContent-Type: application/json\r\nContent-Length: 200000\r\n\r\n'%port).encode('ascii'))
        stop=threading.Event();self.addCleanup(stop.set)
        def trickle():
            while not stop.is_set():
                try:sender.send(b' ')
                except OSError:return
                stop.wait(.2)
        threading.Thread(target=trickle,daemon=True).start()
        started=time.monotonic();reply=b''
        try:
            while b'\r\n' not in reply:
                chunk=sender.recv(1024)
                if not chunk:break
                reply+=chunk
        except socket.timeout:pass
        elapsed=time.monotonic()-started;stop.set()
        self.assertIn(b' 403 ',reply.split(b'\r\n')[0],reply[:80])
        self.assertLess(elapsed,4,'the 403 came at the drain\'s total deadline, not when the sender stopped')

    def test_filtered_inventory_and_candidate_review_revision_contract(self):
        root=self.roots['Audiobooks']
        with connect(self.database) as connection:
            for i in range(105):
                path=str(Path(root)/'Book'/f'{i:03}.mp3')
                connection.execute('INSERT INTO files(root,path,size,modified,kind,metadata,error) VALUES(?,?,?,?,?,?,?)',
                    (root,path,10,1700000000000000101,'audiobook',json.dumps({'title':'Book','author':'Reader','tags':{'album':'Book','track':str(i)}}),'unreadable' if i>=100 else ''))
        code,page=self.json_call('/api/inventory?library=Audiobooks&status=errors')
        self.assertEqual(code,200);self.assertEqual(page['total'],5)
        self.assertEqual(len(page['rows']),5)
        self.assertEqual(page['rows'][0]['modified'],'1700000000000000101')
        code,page=self.json_call('/api/inventory?library=Audiobooks&view=candidates')
        self.assertEqual(code,200);self.assertEqual(page['total'],1)
        row=page['rows'][0]
        review={'title':'Book','author':'Writer Jane','canonical_author':'Jane Writer','narrator':'Reader',
            'original_language':'Other','series':'','number':'','genre':'','topic':'','multi_author':False,'anthology':False,'universe':'QA Universe'}
        payload={'library':'Audiobooks','id':row['id'],'revision':row['revision'],'review':review,'approve':False}
        code,saved=self.json_call('/api/candidate/review',payload)
        self.assertEqual(code,200);self.assertGreater(saved['row']['revision'],row['revision'])
        self.assertEqual(saved['row']['review']['universe'],'QA Universe')
        self.assertEqual(saved['row']['review']['canonical_author'],'Jane Writer')
        self.assertIn('QA Universe',saved['row']['preview']['path'])
        self.assertEqual(self.json_call('/api/candidate/review',payload)[0],400)
        payload['revision']=saved['row']['revision'];payload['approve']=True
        self.assertEqual(self.json_call('/api/candidate/review',payload)[0],400,'Unreadable members block approval')
        self.assertEqual(self.json_call('/api/inventory?library=Ebooks&view=candidates')[0],400)
        self.assertEqual(self.json_call('/api/inventory?library=Audiobooks&status=invented')[0],400)

    def test_file_review_universe_optional_bounded_and_unknown_fields_refused(self):
        source=Path(self.roots['Audiobooks'])/'universe.mp3';source.write_bytes(b'fixture')
        self.assertEqual(self.call('/api/scan/start',{'library':'Audiobooks'})[0],200)
        self.wait_scan()
        row=self.json_call('/api/inventory?library=Audiobooks')[1]['rows'][0]
        review={'original_language':'Other','title':'Book','author':'Folder Author','canonical_author':'Artist Author',
                'narrator':'','series':'Cycle','number':'2','genre':'','topic':'','multi_author':False,'anthology':False}
        body={'library':'Audiobooks','path':row['path'],'size':row['size'],'modified':row['modified'],'review':review}
        self.assertEqual(self.call('/api/review',body)[0],200,'Legacy clients may omit universe')
        saved=self.json_call('/api/inventory?library=Audiobooks')[1]['rows'][0]
        self.assertEqual(saved['review']['universe'],'')
        review=review|{'universe':'QA Universe'};body=body|{'review':review}
        self.assertEqual(self.call('/api/review',body)[0],200)
        saved=self.json_call('/api/inventory?library=Audiobooks')[1]['rows'][0]
        self.assertEqual(saved['review']['universe'],'QA Universe')
        self.assertIn('Folder Author',saved['preview']['path'],'File-level previews retain their existing legacy routing policy')
        self.assertEqual(saved['tag_preview']['ARTIST'],'Artist Author')
        for bad in (True,123,None,[],{},'x'*1001):
            with self.subTest(value=bad):
                self.assertEqual(self.call('/api/review',body|{'review':review|{'universe':bad}})[0],400)
        self.assertEqual(self.call('/api/review',body|{'review':review|{'unknown_field':'refuse'}})[0],400)
        missing=dict(review);missing.pop('title')
        self.assertEqual(self.call('/api/review',body|{'review':missing})[0],400)
        final=self.json_call('/api/inventory?library=Audiobooks')[1]['rows'][0]
        self.assertEqual(final['review'],saved['review'],'Rejected values cannot alter the saved review')
        self.assertEqual(source.read_bytes(),b'fixture')

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
        import os
        from native_io import BoundaryError
        rejected=BoundaryError if os.name=='nt' else (RuntimeError,BlockingIOError)
        with catalog_lock(self.database,self.roots):
            with self.assertRaises(rejected):
                with catalog_lock(self.database,self.roots):
                    self.fail('Two catalog owners were allowed')
        # A denied nested owner must not leak a lease beyond the outer owner.
        with catalog_lock(self.database,self.roots):pass
        with self.assertRaises(OSError):
            BrowserServer(('127.0.0.1',self.server.server_port),self.inventory)
        with self.assertRaises(ValueError):
            BrowserServer(('0.0.0.0',0),self.inventory)

    def test_health_reports_loaded_version_after_file_version_changes(self):
        loaded=self.server.health()['version']
        with patch('web_server.version',return_value='99.0.0'):
            self.assertEqual(self.json_call('/api/health')[1]['version'],loaded)

    def test_restart_guard_rejects_wrong_instance_busy_admission_and_active_research(self):
        self.assertEqual(self.call('/api/shutdown',{'restart_instance':'wrong'})[0],400)
        self.assertFalse(self.server.closing)
        with self.server.control_lock:self.server.merge_admissions=1
        self.assertEqual(self.call('/api/shutdown',{'restart_instance':self.server.instance})[0],409)
        with self.server.control_lock:self.server.merge_admissions=0
        with patch.object(self.server,'state',return_value={'automatic_processing':{'state':'Running'}}):
            self.assertEqual(self.call('/api/shutdown',{'restart_instance':self.server.instance})[0],409)
        self.assertFalse(self.server.closing)
        self.assertEqual(self.call('/api/shutdown',{'restart_instance':self.server.instance},authorized=False)[0],403)
        self.assertEqual(self.call('/api/shutdown',{'restart_instance':self.server.instance})[0],200)
        # The 200 starts the server's own background shutdown (merge.close, then serve_forever ends).
        # Wait for it: tearDown's second close must not overlap it while catalog handles are still open.
        self.thread.join(5)
        self.assertFalse(self.thread.is_alive())

    def test_shutdown_is_protected_and_controlled(self):
        self.assertEqual(self.call('/api/shutdown',{},authorized=False)[0],403)
        self.assertTrue(self.thread.is_alive())
        self.assertEqual(self.call('/api/shutdown',{'unexpected':True})[0],400)
        self.assertEqual(self.call('/api/shutdown',{})[0],200)
        self.thread.join(5)
        self.assertFalse(self.thread.is_alive())

    def test_anthology_author_roles_are_durable_and_audiobook_only(self):
        source=Path(self.roots['Audiobooks'])/'collection.mp3';source.write_bytes(b'fixture')
        self.inventory.reader=lambda *args:{'title':'Source title','author':'Reader Name','artist':'Reader Name','tags':{'artist':'Reader Name','comment':'Original comment'}}
        self.assertEqual(self.call('/api/scan/start',{'library':'Audiobooks'})[0],200)
        self.wait_scan()
        row=self.json_call('/api/inventory?library=Audiobooks')[1]['rows'][0]
        self.assertEqual(row['tag_preview']['ARTIST'],'')
        review={'original_language':'Other','title':'Stories','author':'','series':'','number':'','genre':'','topic':'',
                'multi_author':True,'anthology':True,'canonical_author':'Verified Authors','narrator':'Reader Name'}
        body={'library':'Audiobooks','path':row['path'],'size':row['size'],'modified':row['modified'],'review':review}
        self.assertEqual(self.call('/api/review',body)[0],200)
        saved=self.json_call('/api/inventory?library=Audiobooks')[1]['rows'][0]
        self.assertIn('Сборники',saved['preview']['path'])
        self.assertEqual(saved['tag_preview']['ARTIST'],'Verified Authors')
        self.assertEqual(saved['tag_preview']['COMMENTS'],'Original comment\nNarrator: Reader Name')
        self.assertTrue(saved['review']['anthology'])
        self.assertEqual(self.call('/api/review',body|{'review':review|{'anthology':'true'}})[0],400)
        ebook=Path(self.roots['Ebooks'])/'book.epub';ebook.write_bytes(b'fixture')
        self.assertEqual(self.call('/api/scan/start',{'library':'Ebooks'})[0],200)
        self.wait_scan()
        item=self.json_call('/api/inventory?library=Ebooks')[1]['rows'][0]
        self.assertEqual(self.call('/api/review',body|{'library':'Ebooks','path':item['path'],'size':item['size'],'modified':item['modified']})[0],400)


    def test_automatic_start_status_matches_audio_conflict_and_preserves_run(self):
        with patch.object(self.server.merge,'state',return_value={'state':'Running'}) as jobs:
            status,value=self.json_call('/api/state?library=Audiobooks')
            self.assertEqual(status,200);automatic=value['automatic_processing']
            self.assertFalse(automatic['can_start']);self.assertEqual(automatic['start_block_reason'],'Audiobook conversion is running. Pause audiobook jobs before starting automatic processing.')
            status,rejected=self.json_call('/api/automatic/start',{})
            self.assertEqual(status,409);self.assertEqual(rejected['error'],automatic['start_block_reason'])
            self.assertEqual(rejected['automatic_processing']['state'],automatic['state'])
            self.assertIsNone(self.server.merge.automatic.thread)

    def test_automatic_start_rechecks_conflict_after_available_snapshot(self):
        with patch.object(self.server.merge,'state',return_value={'state':'Paused'}) as jobs:
            status,available=self.json_call('/api/state?library=Audiobooks')
            self.assertEqual(status,200);self.assertTrue(available['automatic_processing']['can_start'])
            jobs.return_value={'state':'Pausing'}
            status,rejected=self.json_call('/api/automatic/start',{})
            self.assertEqual(status,409);self.assertFalse(rejected['automatic_processing']['can_start'])
            self.assertEqual(rejected['error'],'Audiobook jobs are pausing. Wait for them to pause before starting automatic processing.')
            self.assertIsNone(self.server.merge.automatic.thread)

    def test_automatic_discovery_and_closing_explanations_match_status(self):
        with patch.object(self.inventory,'worker',SimpleNamespace(is_alive=lambda:True)),patch.object(self.server.merge,'state',return_value={'state':'Paused'}):
            status,value=self.json_call('/api/state?library=Audiobooks')
            self.assertEqual(status,200);self.assertFalse(value['automatic_processing']['can_start'])
            status,rejected=self.json_call('/api/automatic/start',{})
            self.assertEqual(status,409);self.assertEqual(rejected['error'],value['automatic_processing']['start_block_reason'])
            self.assertEqual(rejected['error'],'Discovery is in progress. Wait for it to stop before starting automatic processing.')
        self.server.closing=True
        try:
            status,value=self.json_call('/api/state?library=Audiobooks')
            self.assertEqual(status,200);self.assertFalse(value['automatic_processing']['can_start'])
            status,rejected=self.json_call('/api/automatic/start',{})
            self.assertEqual(status,409);self.assertEqual(rejected['error'],value['automatic_processing']['start_block_reason'])
        finally:self.server.closing=False

class WindowlessMainTests(unittest.TestCase):
    def test_readiness_runs_before_serving_with_no_standard_streams(self):
        import web_server
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            database=Path(temp)/'inventory.sqlite3';events=[]
            inventory=Mock();inventory.worker=None
            server=Mock();server.loaded_version='fixture';server.health.return_value={'version':'fixture'}
            server.serve_forever.side_effect=lambda **_kwargs:events.append('serving')
            def ready(_server):
                self.assertTrue((database.parent/'web-instance.json').exists())
                events.append('ready')
            with patch.object(web_server,'catalog_lock',return_value=contextlib.nullcontext()),patch.object(web_server,'Inventory',return_value=inventory),patch.object(web_server,'BrowserServer',return_value=server),patch.object(web_server.signal,'signal'),patch.object(sys,'stdout',None),patch.object(sys,'stderr',None):
                web_server.main(['--database',str(database)],ready=ready)
            self.assertEqual(events,['ready','serving'])
            self.assertFalse((database.parent/'web-instance.json').exists())
            server.server_close.assert_called_once()

    def test_receipt_write_failure_closes_constructed_server_without_readiness(self):
        import web_server
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            database=Path(temp)/'inventory.sqlite3';inventory=Mock();inventory.worker=None
            server=Mock();server.health.return_value={'version':'fixture'};ready=Mock()
            with patch.object(web_server,'catalog_lock',return_value=contextlib.nullcontext()),patch.object(web_server,'Inventory',return_value=inventory),patch.object(web_server,'BrowserServer',return_value=server),patch.object(web_server,'owned_instance_record',side_effect=OSError('Fixture record-write failure')):
                with self.assertRaises(OSError):web_server.main(['--database',str(database)],ready=ready)
            server.server_close.assert_called_once();ready.assert_not_called();server.serve_forever.assert_not_called()


# 0.21.3: this module's fixtures publish inside their own library; see sorted_fixture (Sergei's deletion rule).
def setUpModule():
    global _sorted_fixture
    from sorted_fixture import patch_merge_service
    _sorted_fixture = patch_merge_service()


def tearDownModule():
    _sorted_fixture.stop()

if __name__=='__main__':
    unittest.main()
