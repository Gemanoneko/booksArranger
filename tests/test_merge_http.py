"""HTTP route/control tests without sockets, encoders, providers or library access."""
import io
import json
from email.message import Message
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

from web_server import BrowserServer, Handler, MAX_BODY


ID=str(uuid.uuid4())
REVIEW={key:'' for key in ('title','author','series','number','genre','topic')}
REVIEW.update(original_language='Other',multi_author=False)


class MergeHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.calls=[]
        self.inventory=SimpleNamespace(database=Path(self.temp.name)/'catalog.sqlite3',roots={'Audiobooks':'fixture-audio','Podcasts':'fixture-podcasts','Ebooks':'fixture-ebooks'},worker=None,stop_event=threading.Event(),status=lambda lib:{'state':'completed'},launch=Mock(),stop=Mock())
        self.server=BrowserServer.__new__(BrowserServer)
        self.server.inventory=self.inventory;self.server.server_address=('127.0.0.1',5211);self.server.server_port=5211
        self.server.token='fixture-token';self.server.instance='fixture';self.server.active_library=None
        self.server.loaded_version='fixture';self.server.restart_context=None;self.server.recovery_operations=0
        self.server.closing=False;self.server.control_lock=threading.Lock();self.server.control_condition=threading.Condition(self.server.control_lock);self.server.merge_admissions=0
        self.jobs=SimpleNamespace(pause=Mock(return_value={'state':'Paused'}),resume=Mock(return_value={'state':'Running'}))
        self.reviews=SimpleNamespace(save=Mock(return_value={'id':ID,'revision':2}),tracks=Mock(return_value={'id':ID,'revision':2}),match=Mock(return_value={'state':'finding'}),covers=Mock(return_value={'id':ID}),page=Mock(return_value={'rows':[],'total':0}),cover_bytes=Mock())
        self.merge=SimpleNamespace(reviews=self.reviews,jobs=self.jobs,state=Mock(return_value={'state':'Paused','queued':1,'completed':0,'failed':0}),create=Mock(return_value={'job_id':ID}),queue=Mock(return_value={'queued':[ID],'excluded':[]}),close=Mock())
        self.server.merge=self.merge
        self.merge.inspect=Mock(return_value={'inspector':{'id':ID,'sections':[]}})
        self.merge.open_folder=Mock(return_value={'opened':True})
        self.merge.file_id=Mock(return_value='a'*64)
        self.merge.pause=self.jobs.pause;self.merge.resume=self.jobs.resume
        self.merge.enroll_cleanup=Mock(return_value={'cleanup_id':ID})
        self.merge.start_historical_cleanup=Mock(return_value={'cleanup_id':ID})
        self.merge.restore_cleanup=Mock(return_value={'state':'needs_attention'})

    def tearDown(self): self.temp.cleanup()

    def handler(self,path,data=None,raw=None,token=True,method='POST'):
        h=Handler.__new__(Handler);h.server=self.server;h.path=path
        h.headers=Message();h.headers['Host']='127.0.0.1:5211'
        if token:h.headers['X-Books-Token']=self.server.token
        payload=raw if raw is not None else json.dumps(data or {}).encode()
        h.headers['Content-Type']='application/json';h.headers['Content-Length']=str(len(payload));h.rfile=io.BytesIO(payload)
        h.result=None
        h.response=lambda status,body,content_type='application/json':setattr(h,'result',(status,body,content_type))
        return h

    def call(self,path,data=None,**kwargs):
        h=self.handler(path,data,**kwargs);h.do_POST();return h.result

    def identity(self):return {'library':'Audiobooks','id':ID,'revision':1}

    def test_automatic_controls_draft_token_shape_and_scanner_owner(self):
        automatic=SimpleNamespace(status=Mock(return_value={'state':'Idle'}),start=Mock(return_value={'state':'Running'}),stop=Mock(return_value={'state':'Stopping'}),draft=Mock(return_value={'protected':True}))
        self.merge.automatic=automatic
        for route in ('/api/automatic/start','/api/automatic/stop'):
            self.assertEqual(self.call(route,{},token=False)[0],403)
            self.assertEqual(self.call(route,{'library':'Ebooks'})[0],400)
        self.assertEqual(self.call('/api/automatic/start',{})[0],202);automatic.start.assert_called_once_with(server_closing=False)
        body={'id':ID,'revision':1,'active':True}
        self.assertEqual(self.call('/api/automatic/draft',body)[0],200);automatic.draft.assert_called_once_with(ID,1,True)
        for update in ({'revision':True},{'id':'../escape'},{'path':'Z:/anything'}):self.assertEqual(self.call('/api/automatic/draft',body|update)[0],400)
        automatic.status.return_value={'state':'Running'}
        self.assertEqual(self.call('/api/scan/start',{'library':'Audiobooks'})[0],409);self.inventory.launch.assert_not_called()
        self.assertEqual(self.call('/api/audiobook/pause',{})[0],200);automatic.stop.assert_called_once_with()

    def test_recovery_delete_scope_token_origin_and_scan_admission(self):
        self.merge.delete_recovery=Mock(return_value={'started':True})
        body={'job_id':ID,'token':'a'*64,'count':2,'bytes':4096}
        route='/api/audiobook/recovery/delete'
        self.assertEqual(self.call(route,body,token=False)[0],403)
        for bad in (dict(body,path='C:/foreign'),dict(body,count=True),dict(body,token='invalid')):self.assertEqual(self.call(route,bad)[0],400)
        h=self.handler(route,body);h.headers['Origin']='https://untrusted.example';h.do_POST();self.assertEqual(h.result[0],403)
        self.assertEqual(self.call(route,body)[0],202);self.merge.delete_recovery.assert_called_once_with(ID,'a'*64,2,4096)
        self.inventory.worker=SimpleNamespace(is_alive=lambda:True)
        self.assertEqual(self.call(route,body)[0],409)

    def test_approve_and_its_preview_routes(self):
        # Rulings 6a/6b/10/11a: Approve with the values shown (typed values win) and the "Goes to" line before it.
        self.merge.approval_preview=Mock(return_value={'path':'Без автора\\Тайна.m4b','absolute':'Z:\\S\\Без автора\\Тайна.m4b','taken':False,'title':'Тайна','author':'Без автора','collection':False,'reason':''})
        self.merge.approve_book=Mock(return_value={'job_id':ID,'row':{'id':ID,'revision':3}})
        self.reviews._row=Mock(return_value={'id':ID});self.reviews.enrich=Mock(return_value={'id':ID,'revision':2})
        status,body,_=self.call('/api/candidate/approve-preview',self.identity()|{'title':'Тайна'})
        self.assertEqual(status,200);self.assertEqual(body['preview']['path'],'Без автора\\Тайна.m4b');self.merge.approval_preview.assert_called_once_with(ID,1,'Тайна',None)
        status,body,_=self.call('/api/candidate/approve',self.identity()|{'author':'Антон Чехов','without_missing':True})
        self.assertEqual((status,body['job_id']),(200,ID));self.merge.approve_book.assert_called_once_with(ID,1,None,'Антон Чехов',without_missing=True)
        self.merge.approve_book=Mock(side_effect=ValueError('An audiobook already exists at this path. Review it or choose a different reviewed destination.'))
        status,body,_=self.call('/api/candidate/approve',self.identity())
        self.assertEqual((status,body['code']),(409,'name_taken'));self.assertEqual(body['row'],{'id':ID,'revision':2})
        self.merge.approve_book=Mock(side_effect=ValueError('Candidate changed; reload evidence before reviewing'))
        self.assertEqual(self.call('/api/candidate/approve',self.identity())[1]['code'],'changed')
        for bad in ({'without_missing':'yes'},{'title':'x'*1001},{'unknown':1}):
            with self.subTest(bad=bad):self.assertEqual(self.call('/api/candidate/approve',self.identity()|bad)[0],400)
        self.inventory.worker=SimpleNamespace(is_alive=lambda:True)
        self.assertEqual(self.call('/api/candidate/approve',self.identity())[0],409,'never while scanning')

    def test_existing_review_defaults_and_new_context(self):
        body=self.identity()|{'review':REVIEW,'approve':False}
        self.assertEqual(self.call('/api/candidate/review',body)[0],200)
        args,kwargs=self.reviews.save.call_args
        self.assertEqual(args[:3],('Audiobooks',ID,1));self.assertEqual(kwargs['actor'],'user');self.assertFalse(kwargs['approve']);self.assertEqual(kwargs['manual_note'],'');self.assertIsNone(kwargs['cover_id'])
        self.assertEqual(self.call('/api/candidate/review',body|{'actor':'assistant','manual_note':'Concrete title/author evidence','evidence':[{'field':'title'}]})[0],200)
        self.assertEqual(self.reviews.save.call_args.kwargs['actor'],'assistant')

    def test_matching_covers_tracks_create_and_queue_dispatch(self):
        self.assertEqual(self.call('/api/candidate/match',self.identity())[0],202)
        self.assertEqual(self.call('/api/candidate/covers',self.identity())[0],200)
        tracks=self.identity()|dict(order=['one','two'],included=['two'],source_coverage_confirmed=True,order_confirmed=True,chapters=False,actor='user',evidence_note='Reviewed exact source set/order')
        self.assertEqual(self.call('/api/candidate/tracks',tracks)[0],200)
        self.assertEqual(self.reviews.tracks.call_args.args[3:5],(['one','two'],['two']))
        self.assertEqual(self.call('/api/audiobook/create',self.identity())[0],202)
        self.assertEqual(self.call('/api/audiobook/queue',{'library':'Audiobooks','candidates':[{'id':ID,'revision':1}]})[0],200)

    def test_cleanup_restore_only_opaque_job_and_current_origin_token(self):
        for route in ('/api/audiobook/cleanup','/api/audiobook/restore'):
            self.assertEqual(self.call(route,{'job_id':ID},token=False)[0],403)
            for body in ({'job_id':'../x'},{'job_id':ID,'path':'Z:/other'},{}):self.assertEqual(self.call(route,body)[0],400)
            h=self.handler(route,{'job_id':ID});h.headers['Origin']='https://untrusted.example';h.do_POST();self.assertEqual(h.result[0],403)
        self.assertEqual(self.call('/api/audiobook/cleanup',{'job_id':ID})[0],202)
        self.merge.start_historical_cleanup.assert_called_once_with(ID)
        self.jobs.resume.assert_not_called()
        self.assertEqual(self.call('/api/audiobook/restore',{'job_id':ID})[0],200)
        self.merge.restore_cleanup.assert_called_once_with(ID)

    def test_unknown_fields_invalid_ids_types_duplicates_and_bounds(self):
        for update in ({'id':'../escape'},{'revision':True},{'revision':0},{'library':'Podcasts'},{'command':'ffmpeg'}):
            self.assertEqual(self.call('/api/audiobook/create',self.identity()|update)[0],400)
        self.assertEqual(self.call('/api/audiobook/queue',{'library':'Audiobooks','candidates':[{'id':ID,'revision':1}]*2})[0],400)
        self.assertEqual(self.call('/api/audiobook/queue',{'library':'Audiobooks','candidates':[{'id':str(uuid.uuid4()),'revision':1} for _ in range(101)]})[0],400)
        tracks=self.identity()|dict(order=['a'],included=['a'],source_coverage_confirmed=1,order_confirmed=True,chapters=False)
        self.assertEqual(self.call('/api/candidate/tracks',tracks)[0],400)
        tracks['source_coverage_confirmed']=True;tracks['order']=['a']*2
        self.assertEqual(self.call('/api/candidate/tracks',tracks)[0],400)
        self.assertEqual(self.call('/api/candidate/review',self.identity()|{'review':REVIEW,'approve':False,'manual_note':'x'*16001})[0],400)
        self.assertFalse(self.merge.create.called)

    def test_body_rejects_truncation_oversize_duplicates_nonfinite_and_transfer(self):
        h=self.handler('/api/audiobook/pause',raw=b'{}');h.headers.replace_header('Content-Length','5');h.do_POST();self.assertEqual(h.result[0],400)
        h=self.handler('/api/audiobook/pause',raw=b'{}');h.headers.replace_header('Content-Length',str(MAX_BODY+1));h.do_POST();self.assertEqual(h.result[0],400)
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'[]',b'bad json'):
            self.assertEqual(self.call('/api/audiobook/pause',raw=raw)[0],400)
        h=self.handler('/api/audiobook/pause');h.headers['Transfer-Encoding']='chunked';h.do_POST();self.assertEqual(h.result[0],400)
        h=self.handler('/api/audiobook/pause');h.headers['Content-Length']='2';h.do_POST();self.assertEqual(h.result[0],400)

    def test_scan_job_exclusion_and_pause_during_long_admission(self):
        self.inventory.worker=SimpleNamespace(is_alive=lambda:True)
        for route,data in [('/api/audiobook/create',self.identity()),('/api/audiobook/queue',{'library':'Audiobooks','candidates':[{'id':ID,'revision':1}]}),('/api/audiobook/resume',{})]:self.assertEqual(self.call(route,data)[0],409)
        self.assertEqual(self.call('/api/audiobook/pause',{})[0],200)
        self.inventory.worker=None;self.merge.state.return_value={'state':'Running'}
        self.assertEqual(self.call('/api/scan/start',{'library':'Audiobooks'})[0],409)
        self.merge.state.return_value={'state':'Paused'};self.server.merge_admissions=1
        self.assertEqual(self.call('/api/scan/start',{'library':'Audiobooks'})[0],409)
        self.assertEqual(self.call('/api/audiobook/pause',{})[0],200)
        self.assertEqual(self.server.merge_admissions,1)

    def test_slow_dispatch_releases_control_lock_and_balances_admission(self):
        def covers(*args):
            self.assertTrue(self.server.control_lock.acquire(blocking=False));self.server.control_lock.release()
            self.assertEqual(self.server.merge_admissions,1)
            return {'id':ID}
        self.reviews.covers.side_effect=covers
        self.assertEqual(self.call('/api/candidate/covers',self.identity())[0],200)
        self.assertEqual(self.server.merge_admissions,0)
        self.reviews.covers.side_effect=ValueError('Artwork unreadable')
        result=self.call('/api/candidate/covers',self.identity());self.assertEqual(result[0],400);self.assertIn('unreadable',result[1]['error']);self.assertEqual(self.server.merge_admissions,0)

    def test_protected_cover_and_candidate_page_enrichment(self):
        self.reviews.cover_bytes.return_value=b'\x89PNG\r\n\x1a\nfixture'
        h=self.handler('/api/cover?id='+ID,method='GET');h.do_GET();self.assertEqual(h.result[0],200);self.assertEqual(h.result[2],'image/png')
        h=self.handler('/api/cover?id='+ID,token=False,method='GET');h.do_GET();self.assertEqual(h.result[0],403)
        for route in ['/api/cover?id=../source','/api/cover?id='+ID+'&path=C:/source','/api/cover?id='+ID+'&id='+ID]:
            h=self.handler(route,method='GET');h.do_GET();self.assertEqual(h.result[0],400)
        h=self.handler('/api/inventory?library=Audiobooks&view=candidates&status=ready',method='GET');h.do_GET();self.assertEqual(h.result[0],200);self.reviews.page.assert_called_once_with(100,0,'','ready')
        self.assertIn('audiobook_jobs',self.server.state('Audiobooks'))

    def test_the_checking_attention_group_is_a_known_filter(self):
        # RefusedRetry follow-up section 2: the new Checking strip group reaches the page; an invented one is refused.
        h=self.handler('/api/inventory?library=Audiobooks&view=candidates&status=output_attention&group=checking',method='GET');h.do_GET()
        self.assertEqual(h.result[0],200);self.reviews.page.assert_called_once_with(100,0,'','output_attention','checking')
        h=self.handler('/api/inventory?library=Audiobooks&view=candidates&status=output_attention&group=invented',method='GET');h.do_GET()
        self.assertEqual(h.result[0],400);self.assertEqual(self.reviews.page.call_count,1)

    def test_service_creation_only_after_bind_and_close_before_socket(self):
        factory=Mock(return_value=self.merge)
        with patch('web_server.ThreadingHTTPServer.__init__',side_effect=OSError('occupied')):
            with self.assertRaises(OSError):BrowserServer(('127.0.0.1',5211),self.inventory,factory)
        factory.assert_not_called()
        events=[]
        with patch('web_server.ThreadingHTTPServer.__init__',side_effect=lambda *args:events.append('bound')),patch('web_server.ThreadingHTTPServer.server_close',side_effect=lambda:events.append('socket closed')):
            factory.side_effect=lambda *args:(events.append('service'),self.merge)[1]
            server=BrowserServer(('127.0.0.1',5211),self.inventory,factory)
            self.merge.close.side_effect=lambda:events.append('jobs closed')
            server.server_close()
        self.assertEqual(events,['bound','service','jobs closed','socket closed'])

    def test_shutdown_drains_admitted_work_then_closes_jobs(self):
        self.server.merge_admissions=1
        events=[];started=threading.Event()
        self.merge.close.side_effect=lambda:events.append('jobs closed')
        self.server.shutdown=lambda:events.append('shutdown')
        def drain():started.set();self.server.finish_shutdown()
        worker=threading.Thread(target=drain);worker.start();self.assertTrue(started.wait(1))
        with self.server.control_condition:
            self.assertEqual(events,[])
            self.server.merge_admissions=0;self.server.control_condition.notify_all()
        worker.join(2);self.assertFalse(worker.is_alive());self.assertEqual(events,['jobs closed','shutdown'])

    def test_auth_origin_and_cover_csp(self):
        for header,value in [('Host','example.org'),('Origin','https://example.org'),('Sec-Fetch-Site','cross-site')]:
            h=self.handler('/api/audiobook/pause')
            if header=='Host':h.headers.replace_header('Host',value)
            else:h.headers[header]=value
            h.do_POST();self.assertEqual(h.result[0],403)
        h=Handler.__new__(Handler);headers={};h.send_response=lambda status:None;h.send_header=lambda key,value:headers.update({key:value});h.end_headers=lambda:None;h.wfile=io.BytesIO()
        h.response(200,b'fixture','image/png')
        self.assertIn("img-src 'self' blob:",headers['Content-Security-Policy']);self.assertEqual(headers['X-Content-Type-Options'],'nosniff');self.assertEqual(headers['Cache-Control'],'no-store')

    def test_inspection_and_folder_use_only_opaque_record_identity(self):
        files={'library':'Ebooks','view':'files','id':'a'*64}
        self.assertEqual(self.call('/api/inspect',files)[0],200)
        self.merge.inspect.assert_called_once_with('Ebooks','files','a'*64)
        candidate={'library':'Audiobooks','view':'candidates','id':ID}
        directory=str(uuid.uuid4())
        self.assertEqual(self.call('/api/open-folder',candidate|{'folder_kind':'source','directory_id':directory})[0],200)
        self.merge.open_folder.assert_called_once_with('Audiobooks','candidates',ID,folder_kind='source',directory_id=directory)
        self.inventory.worker=SimpleNamespace(is_alive=lambda:True)
        self.assertEqual(self.call('/api/inspect',files)[0],200)
        self.assertEqual(self.call('/api/open-folder',files|{'folder_kind':'output'})[0],200)
        for bad in (files|{'id':'C:/source/book.mp3'},files|{'path':'C:/source'},files|{'view':'outputs'},candidate|{'directory_id':'../escape'},candidate|{'folder_kind':'preview'}):
            self.assertEqual(self.call('/api/open-folder',bad)[0],400)
        self.merge.open_folder.side_effect=ValueError('Folder unavailable. Connect the library drive and try again.')
        result=self.call('/api/open-folder',files);self.assertEqual(result[0],400);self.assertIn('Connect the library',result[1]['error'])


if __name__=='__main__':unittest.main()
