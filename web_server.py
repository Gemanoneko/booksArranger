"""Loopback-only browser interface for the existing read-only inventory engine."""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from app import BASE, catalog_lock
from metadata import GENRES
from scanner import DEFAULT_ROOTS, Inventory, connect

PORT = 5210
MAX_BODY = 16384

def version():
    try:
        return (BASE / 'VERSION').read_text(encoding='utf-8').strip()
    except OSError:
        return 'prototype'

class BrowserServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, address, inventory):
        if address[0] != '127.0.0.1':
            raise ValueError('Books Arranger only binds to IPv4 loopback')
        self.inventory = inventory
        self.token = secrets.token_urlsafe(32)
        self.instance = secrets.token_hex(16)
        self.active_library = None
        self.control_lock = threading.Lock()
        self.closing = False
        super().__init__(address, Handler)

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
            'status': self.inventory.status(library)}

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
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
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
            elif path in {'/api/state','/api/inventory'}:
                if not self.trusted(token=True):
                    return
                allowed = {'library'} if path == '/api/state' else {'library','offset','search'}
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
                    rows = self.server.inventory.rows(library,100,int(offset),search)
                    # Probe internals are catalog evidence, not needed for rendering the browser table.
                    for row in rows:
                        row['metadata'].pop('probe',None)
                        # Nanosecond timestamps exceed JavaScript's exact integer range.
                        row['modified'] = str(row['modified'])
                    self.response(200,{'rows':rows,'offset':int(offset),'page_size':100})
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
        if not raw_length.isascii() or not raw_length.isdigit() or len(raw_length)>6 or int(raw_length)>MAX_BODY:
            raise ValueError('Request body missing or exceeds 16 KB')
        if self.headers.get('Transfer-Encoding'):
            raise ValueError('Chunked requests are not accepted')
        raw = self.rfile.read(int(raw_length))
        data = json.loads(raw.decode('utf-8'))
        if not isinstance(data,dict):
            raise ValueError('Request body must be a JSON object')
        return data

    def do_POST(self):
        if not self.trusted(token=True):
            return
        try:
            path,query = self.query()
            if query:
                raise ValueError('Control requests do not accept query parameters')
            data = self.body()
            with self.server.control_lock:
                if self.server.closing:
                    self.fail(409,'Server is shutting down')
                    return
                if path in {'/api/scan/start','/api/scan/resume','/api/scan/stop'}:
                    if set(data) != {'library'}:
                        raise ValueError('Scan controls require only a library')
                    library = self.library(data['library'])
                    if path.endswith('/stop'):
                        if self.server.active_library != library or not (self.server.inventory.worker and self.server.inventory.worker.is_alive()):
                            self.fail(409,'This library has no active scan to stop')
                            return
                        self.server.inventory.stop()
                    else:
                        self.server.inventory.launch(library,resume=path.endswith('/resume'))
                        self.server.active_library = library
                    self.response(200,self.server.state(library))
                elif path == '/api/review':
                    self.save_review(data)
                elif path == '/api/shutdown':
                    if data:
                        raise ValueError('Shutdown takes an empty JSON object')
                    self.server.closing = True
                    self.server.inventory.stop()
                    self.response(200,{'stopping':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                else:
                    self.fail(404,'No such Books Arranger control')
        except (ValueError,TypeError,UnicodeError,json.JSONDecodeError) as error:
            self.fail(400,str(error))
        except Exception:
            self.fail(500,'Local control failed; source files remain untouched')

    def save_review(self,data):
        if set(data) != {'library','path','size','modified','review'}:
            raise ValueError('Review requires a catalog file and its observed fingerprint')
        library = self.library(data['library'])
        if not isinstance(data['path'],str) or len(data['path'])>32767:
            raise ValueError('Invalid catalog path')
        if type(data['size']) is not int or data['size']<0 or not isinstance(data['modified'],str) or not data['modified'].isascii() or not data['modified'].isdigit() or len(data['modified'])>19 or int(data['modified'])>9223372036854775807:
            raise ValueError('Invalid source fingerprint')
        review = data['review']
        names = {'title','author','original_language','series','number','genre','topic','multi_author'}
        if not isinstance(review,dict) or set(review)!=names:
            raise ValueError('Review fields are incomplete or unknown')
        if any(not isinstance(review[key],str) or len(review[key])>1000 for key in names-{'multi_author'}):
            raise ValueError('Review text must be bounded strings')
        if type(review['multi_author']) is not bool or review['original_language'] not in {'Unknown','Russian','Other'} or review['genre'] not in {'',*GENRES}:
            raise ValueError('Invalid original language, genre or series flag')
        root = self.server.inventory.roots[library]
        with connect(self.server.inventory.database) as connection:
            row = connection.execute('SELECT kind,error,missing FROM files WHERE root=? AND path=?',(root,data['path'])).fetchone()
        if not row or row['kind'] not in {'audiobook','ebook'} or row['error'] or row['missing']:
            raise ValueError('Only available audiobook/ebook catalog rows can be reviewed')
        self.server.inventory.save_review(root,data['path'],review,data['size'],int(data['modified']))
        self.response(200,{'saved':True,'source_changed':False})

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
            threading.Thread(target=server.shutdown,daemon=True).start()
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
