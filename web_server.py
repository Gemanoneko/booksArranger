"""Loopback-only browser interface for inventory, reviewed metadata and audiobook jobs."""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from app import BASE, catalog_lock
from metadata import GENRES
from scanner import DEFAULT_ROOTS, Inventory, connect

PORT = 5210
MAX_BODY = 256 * 1024

def version():
    try:
        return (BASE / 'VERSION').read_text(encoding='utf-8').strip()
    except OSError:
        return 'prototype'

class BrowserServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, address, inventory, merge_factory=None):
        if address[0] != '127.0.0.1':
            raise ValueError('Books Arranger only binds to IPv4 loopback')
        self.inventory = inventory
        self.token = secrets.token_urlsafe(32)
        self.instance = secrets.token_hex(16)
        self.active_library = None
        self.control_lock = threading.Lock()
        self.control_condition = threading.Condition(self.control_lock)
        self.merge_admissions = 0
        self.merge = None
        self.closing = False
        super().__init__(address, Handler)
        try:
            if merge_factory is None:
                from merge_service import MergeService
                merge_factory = MergeService
            self.merge = merge_factory(inventory, Path(inventory.database).parent / 'merge-cache')
        except BaseException:
            super().server_close()
            raise

    def server_close(self):
        if self.merge is not None:
            self.merge.close()
            self.merge = None
        super().server_close()

    def finish_shutdown(self):
        with self.control_condition:
            while self.merge_admissions:
                self.control_condition.wait(timeout=.5)
        self.merge.close()
        self.shutdown()

    def scan_active(self):
        return bool(self.inventory.worker and self.inventory.worker.is_alive())

    def jobs_active(self):
        return self.merge.state().get('state') in {'Running','Pausing','running','pausing'}

    def server_bind(self):
        import socket
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    @property
    def origins(self):
        return {f'http://127.0.0.1:{self.server_port}', f'http://localhost:{self.server_port}'}

    def health(self):
        return {'application': 'Books Arranger', 'version': version(), 'instance': self.instance,
                'pid': os.getpid(), 'port': self.server_port, 'closing': self.closing}

    def state(self, library):
        active = bool(self.inventory.worker and self.inventory.worker.is_alive())
        return self.health() | {'library': library, 'root': self.inventory.roots[library],
            'libraries': list(self.inventory.roots), 'genres': list(GENRES),
            'active_library': self.active_library if active else None,
            'stopping': active and self.inventory.stop_event.is_set(),
            'status': self.inventory.status(library), 'audiobook_jobs': self.merge.state()}

class Handler(BaseHTTPRequestHandler):
    server_version = 'BooksArranger'

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *_args):
        # Avoid logging source filenames or canonical metadata to a console/server log.
        pass

    def response(self, status, body, content_type='application/json; charset=utf-8'):
        raw = json.dumps(body, ensure_ascii=False).encode('utf-8') if isinstance(body,(dict,list)) else body
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' blob:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def fail(self, status, message):
        self.response(status, {'error':message})

    def trusted(self, token=False):
        if self.headers.get('Host') not in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}:
            self.fail(403,'Invalid local host')
            return False
        origin = self.headers.get('Origin')
        if origin and origin not in self.server.origins:
            self.fail(403,'Cross-origin access is blocked')
            return False
        if self.headers.get('Sec-Fetch-Site') not in {None,'none','same-origin'}:
            self.fail(403,'Cross-site access is blocked')
            return False
        if token and not secrets.compare_digest(self.headers.get('X-Books-Token','').encode('utf-8'),self.server.token.encode('ascii')):
            self.fail(403,'Missing or invalid local request token')
            return False
        return True

    def query(self):
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query,keep_blank_values=True)
        if any(len(values) != 1 for values in query.values()):
            raise ValueError('Repeated query parameters are not accepted')
        return parsed.path,{key:values[0] for key,values in query.items()}

    def library(self, value):
        if not isinstance(value,str) or value not in self.server.inventory.roots:
            raise ValueError('Choose one configured library')
        return value

    def do_GET(self):
        if not self.trusted():
            return
        try:
            path,query = self.query()
            if path == '/api/health':
                if query:
                    raise ValueError('Health takes no query parameters')
                self.response(200,self.server.health())
            elif path == '/':
                if query:
                    raise ValueError('The application page takes no query parameters')
                page = (BASE / 'web' / 'index.html').read_text(encoding='utf-8').replace('{{REQUEST_TOKEN}}',self.server.token)
                self.response(200,page.encode('utf-8'),'text/html; charset=utf-8')
            elif path in {'/app.js','/style.css'}:
                content_type = 'text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8'
                self.response(200,(BASE / 'web' / path[1:]).read_bytes(),content_type)
            elif path == '/api/cover':
                if not self.trusted(token=True): return
                if set(query) != {'id'}: raise ValueError('Cover requires only its cached identity')
                id = self.uuid_value(query['id'])
                raw = self.server.merge.reviews.cover_bytes(id)
                if len(raw)>8 * 1024 * 1024: raise ValueError('Cached cover exceeds bound')
                if raw.startswith(b'\x89PNG\r\n\x1a\n'): content_type='image/png'
                elif raw.startswith(b'\xff\xd8\xff'): content_type='image/jpeg'
                else: raise ValueError('Cached cover format is unsupported')
                self.response(200,raw,content_type)
            elif path in {'/api/state','/api/inventory'}:
                if not self.trusted(token=True):
                    return
                allowed = {'library'} if path == '/api/state' else {'library','offset','search','status','view'}
                if set(query)-allowed:
                    raise ValueError('Unknown query parameters')
                library = self.library(query.get('library'))
                if path == '/api/state':
                    self.response(200,self.server.state(library))
                else:
                    offset = query.get('offset','0')
                    if not offset.isascii() or not offset.isdigit() or len(offset)>9:
                        raise ValueError('Offset must be a non-negative bounded integer')
                    search = query.get('search','')
                    if len(search)>500:
                        raise ValueError('Search is too long')
                    selected_status=query.get('status','all')
                    view=query.get('view','files')
                    if view not in {'files','candidates'}:raise ValueError('Unknown inventory view')
                    if view=='candidates':
                        if library!='Audiobooks': raise ValueError('Book candidates apply only to Audiobooks')
                        result=self.server.merge.reviews.page(100,int(offset),search,selected_status)
                        self.response(200,result | {'offset':int(offset),'page_size':100})
                        return
                    result = self.server.inventory.rows(library,100,int(offset),search,selected_status,page=True)
                    rows=result['rows']
                    # Probe internals are catalog evidence, not needed for rendering the browser table.
                    for row in rows:
                        row['record_id']=self.server.merge.file_id(library,row['path'])
                        row['metadata'].pop('probe',None)
                        # Nanosecond timestamps exceed JavaScript's exact integer range.
                        row['modified'] = str(row['modified'])
                    self.response(200,result | {'offset':int(offset),'page_size':100})
            else:
                self.fail(404,'No such Books Arranger route')
        except (ValueError,TypeError) as error:
            self.fail(400,str(error))
        except Exception:
            self.fail(500,'Local catalog request failed; source files remain untouched')

    def body(self):
        if self.headers.get('Content-Type','').split(';')[0].strip().lower() != 'application/json':
            raise ValueError('Request body must be application/json')
        raw_length = self.headers.get('Content-Length','')
        if len(self.headers.get_all('Content-Length',[])) != 1:
            raise ValueError('Exactly one content length is required')
        if not raw_length.isascii() or not raw_length.isdigit() or len(raw_length)>6 or int(raw_length)>MAX_BODY:
            raise ValueError('Request body missing or exceeds 256 KiB')
        if self.headers.get('Transfer-Encoding'):
            raise ValueError('Chunked requests are not accepted')
        raw = self.rfile.read(int(raw_length))
        if len(raw) != int(raw_length): raise ValueError('Request body is truncated')
        def pairs(items):
            result={}
            for key,value in items:
                if key in result: raise ValueError('Repeated JSON fields are not accepted')
                result[key]=value
            return result
        def invalid_constant(_value): raise ValueError('Non-finite JSON values are not accepted')
        data = json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=invalid_constant)
        if not isinstance(data,dict):
            raise ValueError('Request body must be a JSON object')
        return data

    @staticmethod
    def uuid_value(value):
        try:
            if not isinstance(value,str) or str(uuid.UUID(value)) != value: raise ValueError()
        except (ValueError,TypeError,AttributeError): raise ValueError('Identity must be a canonical UUID') from None
        return value

    @staticmethod
    def text_value(value, limit=16000, nullable=False):
        if nullable and value is None: return None
        if not isinstance(value,str) or len(value)>limit: raise ValueError('Text exceeds its allowed bound')
        return value

    def candidate_identity(self,data):
        library=self.library(data.get('library'))
        if library!='Audiobooks': raise ValueError('Audiobook operations apply only to Audiobooks')
        id=self.uuid_value(data.get('id'))
        revision=data.get('revision')
        if type(revision) is not int or not 1<=revision<=9223372036854775807: raise ValueError('Invalid candidate revision')
        return library,id,revision

    @staticmethod
    def shape(data,required,optional=()):
        if not set(required)<=set(data) or set(data)-set(required)-set(optional): raise ValueError('Request fields are incomplete or unknown')

    def merge_request(self,path,data):
        reviews=self.server.merge.reviews
        if path in {'/api/inspect','/api/open-folder'}:
            self.shape(data,{'library','view','id'}, {'folder_kind','directory_id'} if path=='/api/open-folder' else ())
            library=self.library(data['library'])
            view=data['view']
            if view not in {'files','candidates'}: raise ValueError('Invalid record view')
            if view=='candidates':
                if library!='Audiobooks': raise ValueError('Book candidates apply only to Audiobooks')
                identity=self.uuid_value(data['id'])
            else:
                identity=data['id']
                if not isinstance(identity,str) or len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity): raise ValueError('Invalid catalog record identity')
            if path=='/api/inspect':
                self.response(200,self.server.merge.inspect(library,view,identity));return
            kind=data.get('folder_kind','source')
            if kind not in {'source','output'}: raise ValueError('Invalid folder kind')
            directory_id=None if data.get('directory_id') is None else self.uuid_value(data['directory_id'])
            self.response(200,self.server.merge.open_folder(library,view,identity,folder_kind=kind,directory_id=directory_id));return
        if path in {'/api/audiobook/pause','/api/audiobook/resume'}:
            if data: raise ValueError('Audiobook job controls require an empty object')
            self.response(200,self.server.merge.pause() if path.endswith('/pause') else self.server.merge.resume())
            return
        if path in {'/api/audiobook/cleanup','/api/audiobook/restore'}:
            self.shape(data,{'job_id'})
            job_id=self.uuid_value(data['job_id'])
            if path.endswith('/cleanup'):
                result=self.server.merge.start_historical_cleanup(job_id)
                self.response(202,result)
            else:
                self.response(200,self.server.merge.restore_cleanup(job_id))
            return
        if path=='/api/audiobook/queue':
            self.shape(data,{'library','candidates'})
            library=self.library(data['library'])
            if library!='Audiobooks': raise ValueError('Queue applies only to Audiobooks')
            candidates=data['candidates']
            if not isinstance(candidates,list) or not 1<=len(candidates)<=100: raise ValueError('Select at most one visible page of candidates')
            ids=set()
            for item in candidates:
                if not isinstance(item,dict): raise ValueError('Invalid candidate selection')
                self.shape(item,{'id','revision'})
                self.candidate_identity({'library':library,**item})
                if item['id'] in ids: raise ValueError('Repeated candidate selection')
                ids.add(item['id'])
            self.response(200,self.server.merge.queue(library,candidates));return
        base={'library','id','revision'}
        if path=='/api/candidate/review':
            self.shape(data,base|{'review','approve'},{'manual_note','proposal_id','cover_id','actor','evidence'})
        elif path=='/api/candidate/tracks':
            self.shape(data,base|{'order','included','source_coverage_confirmed','order_confirmed','chapters'},{'actor','evidence_note'})
        else: self.shape(data,base)
        library,id,revision=self.candidate_identity(data)
        if path=='/api/candidate/match':
            self.response(202,{'matching':reviews.match(library,id,revision)});return
        if path=='/api/candidate/covers':
            self.response(200,{'row':reviews.covers(library,id,revision)});return
        if path=='/api/audiobook/create':
            self.response(202,{'job':self.server.merge.create(library,id,revision)});return
        actor=data.get('actor','user')
        if actor not in {'user','assistant'}: raise ValueError('Unknown review actor')
        if path=='/api/candidate/review':
            if type(data['approve']) is not bool: raise ValueError('Approval must be an explicit boolean')
            kwargs={'approve':data['approve'],'manual_note':self.text_value(data.get('manual_note','')),'actor':actor}
            for key in ('proposal_id','cover_id'):
                kwargs[key]=None if data.get(key) is None else self.uuid_value(data[key])
            evidence=data.get('evidence')
            if evidence is not None and (not isinstance(evidence,list) or len(evidence)>30 or any(not isinstance(item,dict) for item in evidence)): raise ValueError('Invalid evidence records')
            kwargs['evidence']=evidence
            row=reviews.save(library,id,revision,self.review_data(data['review']),**kwargs)
        else:
            for key in ('order','included'):
                values=data[key]
                if not isinstance(values,list) or len(values)>10000 or any(not isinstance(value,str) or not 1<=len(value)<=128 for value in values) or len(set(values))!=len(values): raise ValueError('Invalid bounded source member list')
            for key in ('source_coverage_confirmed','order_confirmed','chapters'):
                if type(data[key]) is not bool: raise ValueError('Track confirmations must be explicit booleans')
            row=reviews.tracks(library,id,revision,data['order'],data['included'],data['source_coverage_confirmed'],data['order_confirmed'],data['chapters'],actor=actor,evidence_note=self.text_value(data.get('evidence_note','')))
        self.response(200,{'saved':True,'row':row})

    def do_POST(self):
        if not self.trusted(token=True): return
        admitted=False
        try:
            path,query=self.query()
            if query: raise ValueError('Control requests do not accept query parameters')
            data=self.body()
            merge_routes={'/api/inspect','/api/open-folder','/api/candidate/review','/api/candidate/match','/api/candidate/covers','/api/candidate/tracks','/api/audiobook/create','/api/audiobook/queue','/api/audiobook/pause','/api/audiobook/resume','/api/audiobook/cleanup','/api/audiobook/restore'}
            with self.server.control_lock:
                if self.server.closing:
                    self.fail(409,'Server is shutting down');return
                if path in {'/api/scan/start','/api/scan/resume','/api/scan/stop'}:
                    if set(data)!={'library'}: raise ValueError('Scan controls require only a library')
                    library=self.library(data['library'])
                    if path.endswith('/stop'):
                        if self.server.active_library!=library or not self.server.scan_active():
                            self.fail(409,'This library has no active scan to stop');return
                        self.server.inventory.stop()
                    else:
                        if self.server.jobs_active() or self.server.merge_admissions:
                            self.fail(409,'Pause audiobook work before starting a scan');return
                        self.server.inventory.launch(library,resume=path.endswith('/resume'))
                        self.server.active_library=library
                    self.response(200,self.server.state(library));return
                if path=='/api/shutdown':
                    if data: raise ValueError('Shutdown takes an empty JSON object')
                    self.server.closing=True;self.server.inventory.stop()
                    self.response(200,{'stopping':True})
                    threading.Thread(target=self.server.finish_shutdown,daemon=True).start();return
                if path in merge_routes:
                    if path in {'/api/audiobook/create','/api/audiobook/queue','/api/audiobook/resume','/api/audiobook/cleanup','/api/audiobook/restore'} and self.server.scan_active():
                        self.fail(409,'Stop scanning before queueing or resuming audiobook jobs');return
                    self.server.merge_admissions+=1;admitted=True
                elif path!='/api/review':
                    self.fail(404,'No such Books Arranger control');return
            # Slow source/provider/cover operations never hold the global control lock.
            if path in merge_routes: self.merge_request(path,data)
            else: self.save_review(data)
        except (ValueError,TypeError,UnicodeError,json.JSONDecodeError,RecursionError) as error:
            self.fail(400,str(error))
        except Exception:
            self.fail(500,'Local control failed; inspect saved job and source cleanup status')
        finally:
            if admitted:
                with self.server.control_condition:
                    self.server.merge_admissions-=1
                    self.server.control_condition.notify_all()

    def save_review(self,data):
        if set(data) != {'library','path','size','modified','review'}:
            raise ValueError('Review requires a catalog file and its observed fingerprint')
        library = self.library(data['library'])
        if not isinstance(data['path'],str) or len(data['path'])>32767:
            raise ValueError('Invalid catalog path')
        if type(data['size']) is not int or data['size']<0 or not isinstance(data['modified'],str) or not data['modified'].isascii() or not data['modified'].isdigit() or len(data['modified'])>19 or int(data['modified'])>9223372036854775807:
            raise ValueError('Invalid source fingerprint')
        review = self.review_data(data['review'])
        root = self.server.inventory.roots[library]
        with connect(self.server.inventory.database) as connection:
            source=connection.execute('SELECT * FROM files WHERE root=? AND path=?',(root,data['path'])).fetchone()
        if source is None or source['kind'] not in {'audiobook','ebook'} or source['error'] or source['missing']:
            raise ValueError('Only available audiobook/ebook catalog rows can be reviewed')
        if source['kind']!='audiobook' and (review['anthology'] or review['canonical_author'] or review['narrator']):
            raise ValueError('Audiobook role and anthology fields do not apply to ebooks')
        self.server.inventory.save_review(root,data['path'],review,data['size'],int(data['modified']))
        self.response(200,{'saved':True,'source_changed':False})

    def review_data(self,review):
        names = {'title','author','original_language','series','number','genre','topic','multi_author'}
        additions = {'anthology','canonical_author','narrator'}
        if not isinstance(review,dict) or not names.issubset(review) or set(review)-names-additions:
            raise ValueError('Review fields are incomplete or unknown')
        review = {'anthology':False,'canonical_author':'','narrator':''} | review
        if any(not isinstance(review[key],str) or len(review[key])>1000 for key in (names-{'multi_author'}) | {'canonical_author','narrator'}):
            raise ValueError('Review text must be bounded strings')
        if type(review['multi_author']) is not bool or type(review['anthology']) is not bool or review['original_language'] not in {'Unknown','Russian','Other'} or review['genre'] not in {'',*GENRES}:
            raise ValueError('Invalid original language, genre or series flag')
        return review

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',default=str(BASE / 'data' / 'inventory.sqlite3'))
    parser.add_argument('--roots-json',help='Optional local fixture roots; not exposed through HTTP')
    args = parser.parse_args()
    roots = DEFAULT_ROOTS
    if args.roots_json:
        roots = json.loads(Path(args.roots_json).read_text(encoding='utf-8'))
        if set(roots)!=set(DEFAULT_ROOTS) or any(not isinstance(path,str) or not os.path.isabs(path) for path in roots.values()):
            parser.error('Root configuration must contain exactly the three absolute library paths')
    with catalog_lock(args.database,roots):
        inventory = Inventory(args.database,roots)
        try:
            server = BrowserServer(('127.0.0.1',PORT),inventory)
        except OSError as error:
            raise RuntimeError(f'Books Arranger cannot bind its assigned port {PORT}; stop the existing owner first. No fallback port is used.') from error
        instance_file = Path(args.database).parent / 'web-instance.json'
        instance_file.write_text(json.dumps(server.health() | {'url':f'http://127.0.0.1:{PORT}/'}),encoding='utf-8')
        def stop(_signal=None,_frame=None):
            inventory.stop()
            server.closing = True
            threading.Thread(target=server.finish_shutdown,daemon=True).start()
        signal.signal(signal.SIGINT,stop)
        if hasattr(signal,'SIGTERM'):
            signal.signal(signal.SIGTERM,stop)
        print(f'Books Arranger {version()} — http://127.0.0.1:{PORT}/ — PID {os.getpid()}',flush=True)
        try:
            server.serve_forever(poll_interval=.2)
        finally:
            inventory.stop()
            if inventory.worker and inventory.worker.is_alive():
                inventory.worker.join(timeout=20)
            server.server_close()
            if instance_file.exists():
                instance_file.unlink()

if __name__ == '__main__':
    main()
