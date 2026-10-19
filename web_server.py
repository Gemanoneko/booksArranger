"""Loopback-only browser interface for inventory, reviewed metadata and audiobook jobs."""
import contextlib
import argparse
import copy
import time
import json
import os
from pathlib import Path
import secrets
import signal
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from catalog_owner import BASE, catalog_lock
from merge_service import QUIET_MAX_AGE, StatusUnavailable
from metadata import GENRES
from scanner import DEFAULT_ROOTS, Inventory, connect

PORT = 5210
MAX_BODY = 256 * 1024

def version():
    # package.json is the single version source; packaged backends carry a generated VERSION.
    try:
        value = json.loads((BASE / 'package.json').read_text(encoding='utf-8'))['version']
        if isinstance(value, str) and value.strip():
            return value.strip()
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        return (BASE / 'VERSION').read_text(encoding='utf-8').strip()
    except OSError:
        return 'prototype'

CLEANUP_STEPS = {'recovery copies', 'originals', 'temporary', 'folders', 'former outputs', 'verifying replacement', 'retiring former outputs'}
# Conversion steps as the four steps shown to the user (Step N of 4); measured sub-steps share their step.
CONVERSION_STEPS = {'checking sources': 1, 'preparing': 1, 'source copies': 1, 'checking audio': 2, 'matching format': 2, 'normalizing': 2,
                    'joined audio': 2, 'creating': 3, 'encoding': 3, 'checking': 4, 'copying': 4, 'publishing': 4}
ACTIVITY_STATES = {'Running': 'running', 'Pausing': 'pausing', 'Paused': 'paused', 'Needs attention': 'attention'}
ACTIVITY_ORDER = {'conversion': 0, 'cleanup': 1, 'identity': 2, 'series': 3, 'scan': 4}


def _measure(source, unit=None):
    """done/total/unit (+item/items) when they form a real measurement; otherwise indeterminate."""
    done = source.get('completed') if isinstance(source, dict) else None
    total = source.get('total') if isinstance(source, dict) else None
    if type(done) not in (int, float) or type(total) not in (int, float) or not total > 0 or not 0 <= done <= total:
        return {'indeterminate': True}
    value = {'done': done, 'total': total, 'unit': source.get('unit') or unit, 'indeterminate': False}
    fraction = source.get('fraction')
    if type(fraction) in (int, float) and 0 <= fraction <= 1:
        value['fraction'] = fraction
    if type(source.get('item')) is int and type(source.get('items')) is int and 1 <= source['item'] <= source['items']:
        value.update(item=source['item'], items=source['items'])
    return value


def activities(jobs, scan, scan_library, automatic, started_at=None, now_ms=None):
    """Every running activity as one row (ProgressRows spec): what it is doing now and, where measurable, how far.

    One row per kind, in the spec's fixed order: conversion, originals cleanup (and the temporary
    files after it), the finished-book identity check, and scan or research. step_started_at is
    exact where the work records it, else when this server first saw the step (started_at memo).
    Labels and step text are the UI's, except the research step, which is the research's own text.
    """
    import time
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    memo = started_at if started_at is not None else {}
    rows = []
    jobs = jobs if isinstance(jobs, dict) else {}
    progress = jobs.get('progress')
    if jobs.get('current_title') and isinstance(progress, dict) and progress.get('phase') and not progress.get('attention'):
        step = progress['phase']
        kind = 'cleanup' if step in CLEANUP_STEPS else 'conversion'
        unit = {'encoding': 'seconds', 'originals': 'files', 'recovery copies': 'files'}.get(step)
        row = {'id': kind, 'kind': kind, 'subject': jobs['current_title'], 'step': step,
               'state': ACTIVITY_STATES.get(jobs.get('state'), 'running'), 'reason': progress.get('reason', '')} | _measure(progress, unit)
        if kind == 'conversion':
            row.update(step_index=CONVERSION_STEPS.get(step, 1), step_count=4)
        if type(progress.get('started')) is int:
            row['step_started_at'] = progress['started']
        rows.append(row)
    held = jobs.get('attention_row')
    if isinstance(held, dict) and not any(row['kind'] == 'cleanup' for row in rows):
        rows.append({'id': 'cleanup', 'kind': 'cleanup', 'subject': held.get('title') or '', 'step': held.get('phase') or 'originals',
                     'state': 'attention', 'reason': held.get('reason') or ''} | _measure(held, 'files'))
    check = jobs.get('published_check')
    if isinstance(check, dict):
        row = {'id': 'identity', 'kind': 'identity', 'subject': '', 'step': 'identity', 'state': 'running'} | _measure(check, 'books')
        if type(check.get('started')) is int:
            row['step_started_at'] = check['started']
        rows.append(row)
    series = jobs.get('series_update')
    if isinstance(series, dict) and isinstance(series.get('title'), str) and series['title']:
        # v0.16.12 series backfill: "Updating series: <title> · N of M books".
        rows.append({'id': 'series', 'kind': 'series', 'subject': series['title'], 'step': 'series ' + ('updating' if series.get('step') == 'updating' else 'looking up'),
                     'state': 'running'} | _measure({'completed': series.get('done'), 'total': series.get('total')}, 'books'))
    if scan_library and isinstance(scan, dict):
        checked, pending = scan.get('checked'), scan.get('pending')
        measured = _measure({'completed': checked, 'total': checked + pending}, 'files') if type(checked) is int and type(pending) is int else {'indeterminate': True}
        rows.append({'id': 'scan', 'kind': 'scan', 'subject': scan_library, 'step': 'scanning', 'step_text': scan.get('current') or '', 'state': 'running'} | measured)
    elif isinstance(automatic, dict) and automatic.get('state') in ('Running', 'Stopping') and automatic.get('phase') == 'research':
        current = automatic.get('current') if isinstance(automatic.get('current'), dict) else {}
        text = ' - '.join(part for part in (current.get('source'), current.get('stage')) if isinstance(part, str) and part)
        rows.append({'id': 'scan', 'kind': 'scan', 'subject': current.get('title', '') if isinstance(current.get('title'), str) else '', 'step': 'researching',
                     'step_text': text, 'state': 'pausing' if automatic['state'] == 'Stopping' else 'running'} | _measure(automatic.get('research_pass'), 'books'))
    seen = set()
    for row in rows:
        # Research's subject is the book being researched; its step (the sweep) keeps one clock.
        key = (row['id'], row['step'], '' if row['step'] == 'researching' else row['subject'])
        seen.add(key)
        if 'step_started_at' not in row:
            row['step_started_at'] = memo.setdefault(key, now_ms)
    for key in [key for key in memo if key not in seen]:
        del memo[key]
    return sorted(rows, key=lambda row: ACTIVITY_ORDER[row['kind']])


class BrowserServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, address, inventory, merge_factory=None):
        if address[0] != '127.0.0.1':
            raise ValueError('Books Arranger only binds to IPv4 loopback')
        self.inventory = inventory
        self.token = secrets.token_urlsafe(32)
        self.instance = secrets.token_hex(16)
        self.loaded_version = version()
        self.restart_context = False
        self.active_library = None
        self.control_lock = threading.Lock()
        self.control_condition = threading.Condition(self.control_lock)
        self.merge_admissions = 0
        self.recovery_operations = 0
        self.merge = None
        self.closing = False
        super().__init__(address, Handler)
        try:
            if merge_factory is None:
                from merge_service import MergeService
                merge_factory = MergeService
            self.merge = merge_factory(inventory, Path(inventory.database).parent / 'merge-cache')
            # Whatever starts automatic processing (Start, Start over, release, a pending start), its scan is the
            # Audiobooks library's: the scan line and progress row follow it as after the Start button.
            automatic=getattr(self.merge,'automatic',None)
            if automatic is not None and hasattr(automatic,'on_started'):automatic.on_started=lambda:setattr(self,'active_library','Audiobooks')
            # A start that fires later (the O12 pending start) reads the server's closing flag at that moment, as the
            # control gate does for a press: nothing starts once Quit or shutdown has begun.
            if automatic is not None and hasattr(automatic,'server_closing'):automatic.server_closing=lambda:self.closing
            if hasattr(self.merge,'start_retention'):self.merge.start_retention(self.recovery_admission)
            # Published-book hashing reads every finished book from the library share; it must not delay health.
            if hasattr(self.merge,'start_published_check'):self.merge.start_published_check()
        except BaseException:
            super().server_close()
            raise

    @contextlib.contextmanager
    def recovery_admission(self):
        with self.control_condition:
            if self.closing or self.scan_active() or self.merge_admissions:raise ValueError('App is busy or closing; recovery deletion waits')
            self.merge_admissions+=1
            self.recovery_operations+=1
        try:yield
        finally:
            with self.control_condition:
                self.merge_admissions-=1;self.recovery_operations-=1;self.control_condition.notify_all()

    def server_close(self):
        if self.merge is not None:
            self.merge.close()
            self.merge = None
        super().server_close()

    def finish_shutdown(self):
        with self.control_condition:
            while self.merge_admissions:
                self.control_condition.wait(timeout=.5)
        self.inventory.stop()
        worker=self.inventory.worker
        if worker and worker.is_alive():
            worker.join(timeout=20)
            if worker.is_alive():raise TimeoutError('Inventory worker has not reached its safe checkpoint; ownership retained')
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
        return {'application': 'Books Arranger', 'version': self.loaded_version, 'instance': self.instance,
                'pid': os.getpid(), 'port': self.server_port, 'closing': self.closing, 'restart_context': self.restart_context, 'recovery_active':bool(self.recovery_operations)}

    def invalidate_status(self):
        """Called before every trusted control reply: polling reads after it never get a pre-control answer."""
        invalidate=getattr(self.merge,'invalidate_status',None)
        if invalidate:invalidate()

    def state(self, library, cached=False):
        """cached=True is for polling reads only; restart/update fences and control replies stay fresh.

        While the app is quiet (merge_service.status_snapshot), a poll also reuses the library and automatic
        status: together they read about 100 MB of the real catalog per poll.
        """
        active = bool(self.inventory.worker and self.inventory.worker.is_alive())
        quiet=getattr(self.merge,'_quiet_token',None) if cached else None
        token=quiet() if callable(quiet) else None
        jobs=self.merge.status_snapshot() if cached and hasattr(self.merge,'status_snapshot') else self.merge.state()
        key=(library,active,self.closing,self.active_library,json.dumps(jobs,sort_keys=True,default=str))
        kept=self.__dict__.get('_quiet_parts')
        bound=self.merge.quiet_max_age() if hasattr(self.merge,'quiet_max_age') else QUIET_MAX_AGE
        if token is not None and kept and kept[0]==(token,key) and 0<=time.monotonic()-kept[1]<bound:
            status,automatic=copy.deepcopy(kept[2])
        else:
            status=self.inventory.status(library)
            automatic=self.merge.automatic.status(jobs=jobs,scanning=active,server_closing=self.closing) if hasattr(self.merge,'automatic') else None
            if token is not None and quiet()==token:self._quiet_parts=((token,key),time.monotonic(),copy.deepcopy((status,automatic)))
        return self.health() | {'library': library, 'root': self.inventory.roots[library],
            'libraries': list(self.inventory.roots), 'genres': list(GENRES),
            'active_library': self.active_library if active else None,
            'stopping': active and self.inventory.stop_event.is_set(),
            'status': status, 'audiobook_jobs': jobs,
            'automatic_processing': automatic,
            'activities': activities(jobs, self.inventory.status(self.active_library) if active and self.active_library in self.inventory.roots else None,
                                     self.active_library if active else None, automatic, self.__dict__.setdefault('_activity_started', {}))}

class Handler(BaseHTTPRequestHandler):
    server_version = 'BooksArranger'

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *_args):
        # Avoid logging source filenames or canonical metadata to a console/server log.
        pass

    def response(self, status, body, content_type='application/json; charset=utf-8'):
        # A trusted control drops the shared status answer BEFORE its reply leaves, so the
        # page's follow-up /api/state read cannot receive the pre-control snapshot.
        invalidate=getattr(self.server,'invalidate_status',None) if self.__dict__.pop('status_control',False) else None
        if invalidate:invalidate()
        raw = json.dumps(body, ensure_ascii=False).encode('utf-8') if isinstance(body,(dict,list)) else body
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' blob:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True

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
            elif path in {'/app.js','/desktop-ui.js','/style.css'}:
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
                allowed = {'library'} if path == '/api/state' else {'library','offset','search','status','view','group'}
                if set(query)-allowed:
                    raise ValueError('Unknown query parameters')
                library = self.library(query.get('library'))
                if path == '/api/state':
                    self.response(200,self.server.state(library,cached=True))
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
                        group=query.get('group') or None
                        if group is not None and group not in {'all','retry','repair','checking','changed','audiobook','other','unsupported'}:raise ValueError('Unknown attention group')
                        pager=getattr(self.server.merge,'cached_page',None)  # a quiet app reuses the identical page
                        if callable(pager):result=pager(100,int(offset),search,selected_status,group)
                        else:result=self.server.merge.reviews.page(100,int(offset),search,selected_status,group) if group else self.server.merge.reviews.page(100,int(offset),search,selected_status)
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
        except StatusUnavailable:
            self.fail(503,'Status is still updating; retrying')
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

    def automatic_status(self):
        """A fresh automatic-processing status for a control's answer (the page takes it at once, as after Start)."""
        merge=self.server.merge
        jobs=merge.status_snapshot() if hasattr(merge,'status_snapshot') else merge.state()
        return merge.automatic.status(jobs=jobs,scanning=self.server.scan_active(),server_closing=self.server.closing)

    def refused(self,error,identity=None):
        """409 for a Start over, release or Clear working files press that changed nothing: the message, its typed
        cause (the page picks its words from it) and the book's refreshed row."""
        body={'error':str(error)}
        if getattr(error,'cause',None):body['cause']=error.cause
        if identity:
            row=self.server.merge.restart_row(identity) if hasattr(self.server.merge,'restart_row') else None
            if row is not None:body['row']=row
        self.response(409,body)

    def merge_request(self,path,data):
        if path=='/api/automatic/cancel-start':
            # Cancel automatic start (O12): the pending start ends; books keep waiting for a press.
            if data:raise ValueError('Automatic controls require an empty object; scope is Audiobooks')
            self.server.merge.automatic.cancel_start()
            self.response(202,{'automatic_processing':self.automatic_status()});return
        if path=='/api/audiobook/startover':
            # Start over: set the stuck job aside (kept) and send the book back to automatic processing, which starts if
            # it is not running. discard_review: "Start over and let the app handle it", one transaction.
            self.shape(data,{'library','id','revision','job_id'},{'discard_review'})
            library,id,revision=self.candidate_identity({key:data[key] for key in ('library','id','revision')})
            job_id=self.uuid_value(data['job_id']);discard=data.get('discard_review',False)
            if type(discard) is not bool:raise ValueError('discard_review must be an explicit boolean')
            from audio_jobs import RetryRefused
            try:result=self.server.merge.start_over(library,id,revision,job_id,discard,server_closing=self.server.closing)
            except RetryRefused as error:
                self.refused(error,id);return
            self.response(202,result|{'automatic_processing':self.automatic_status()});return
        if path=='/api/audiobook/clear-working':
            # Clear working files: verified disposal of an earlier attempt's leftovers; originals are never touched.
            self.shape(data,{'library','id','revision','job_id'})
            library,id,revision=self.candidate_identity({key:data[key] for key in ('library','id','revision')})
            job_id=self.uuid_value(data['job_id'])
            from audio_jobs import RetryRefused
            try:result=self.server.merge.clear_working_files(library,id,revision,job_id)
            except RetryRefused as error:
                self.refused(error,id);return
            self.response(202,result);return
        if path=='/api/audiobook/release':
            # "Let the app handle it": discard the held book's saved review and let automatic processing take it.
            self.shape(data,{'library','id','revision'})
            library,id,revision=self.candidate_identity(data)
            from audio_jobs import RetryRefused
            try:result=self.server.merge.release(library,id,revision,server_closing=self.server.closing)
            except RetryRefused as error:
                self.refused(error,id);return
            self.response(202,result|{'automatic_processing':self.automatic_status()});return
        if path=='/api/audiobook/release-selected':
            # "Let the app handle selected": one call, each book through its own compare-and-set, one start after the last.
            self.shape(data,{'library','items'})
            if data['library']!='Audiobooks':raise ValueError('Audiobook operations apply only to Audiobooks')
            items=data['items']
            if not isinstance(items,list) or not 1<=len(items)<=1000:raise ValueError('Select between 1 and 1000 books')
            checked=[]
            for item in items:
                if not isinstance(item,dict):raise ValueError('Each selected book needs its identity and revision')
                self.shape(item,{'id','revision'})
                checked.append(self.candidate_identity({'library':'Audiobooks',**item})[1:])
            if len({identity for identity,_ in checked})!=len(checked):raise ValueError('Each book may be selected once')
            result=self.server.merge.release_selected('Audiobooks',checked,server_closing=self.server.closing)
            self.response(202,result|{'automatic_processing':self.automatic_status()});return
        if path in {'/api/automatic/start','/api/automatic/stop','/api/automatic/draft'}:
            automatic=self.server.merge.automatic
            if path.endswith('/draft'):
                self.shape(data,{'id','revision','active'})
                identity=self.uuid_value(data['id']);revision=data['revision']
                if type(revision) is not int or revision<1:raise ValueError('Invalid candidate revision')
                self.response(200,automatic.draft(identity,revision,data['active']));return
            if data:raise ValueError('Automatic controls require an empty object; scope is Audiobooks')
            if path.endswith('/start'):
                try:value=automatic.start(server_closing=self.server.closing)
                except ValueError as error:
                    current=automatic.status(jobs=self.server.merge.state(),scanning=self.server.scan_active(),server_closing=self.server.closing)
                    self.response(409,{'error':current.get('start_block_reason') or str(error),'automatic_processing':current});return
                self.server.active_library='Audiobooks'
            else:value=automatic.stop()
            self.response(202,{'automatic_processing':value});return
        reviews=self.server.merge.reviews
        if path=='/api/audiobook/retry':
            self.shape(data,{'library','id','revision','job_id'})
            library,id,revision=self.candidate_identity({key:data[key] for key in ('library','id','revision')})
            job_id=self.uuid_value(data['job_id'])
            from audio_jobs import RetryRefused
            try:result=self.server.merge.retry_blocked_job(library,id,revision,job_id)
            except RetryRefused as error:
                if getattr(error,'cause',None):self.refused(error);return  # Retry's clear-first did not finish: typed
                self.fail(409,str(error));return  # Nothing changed; the message is shown as written.
            self.response(202,result);return
        if path=='/api/audiobook/repair':
            # Repair button: the same request shape and answers as Retry.
            self.shape(data,{'library','id','revision','job_id'})
            library,id,revision=self.candidate_identity({key:data[key] for key in ('library','id','revision')})
            job_id=self.uuid_value(data['job_id'])
            from audio_jobs import RetryRefused
            try:result=self.server.merge.repair_blocked_job(library,id,revision,job_id)
            except RetryRefused as error:
                if getattr(error,'cause',None):self.refused(error);return
                self.fail(409,str(error));return
            self.response(202,result);return
        if path=='/api/audiobook/keep':
            # Keep files: the kept files stop being flagged; nothing is deleted.
            self.shape(data,{'library','id','revision','job_id'})
            library,id,revision=self.candidate_identity({key:data[key] for key in ('library','id','revision')})
            job_id=self.uuid_value(data['job_id'])
            from audio_jobs import RetryRefused
            try:result=self.server.merge.keep_files(library,id,revision,job_id)
            except RetryRefused as error:
                self.fail(409,str(error));return
            self.response(202,result);return
        if path=='/api/audiobook/retry-all':
            # Retry all: the whole Can retry group, server side; progress arrives in the status payload.
            self.shape(data,{'library'})
            if data['library']!='Audiobooks':raise ValueError('Audiobook operations apply only to Audiobooks')
            from audio_jobs import RetryRefused
            try:run=self.server.merge.retry_all()
            except RetryRefused as error:
                self.fail(409,str(error));return
            self.response(202,{'retry_all':run});return
        if path=='/api/audiobook/replace':
            self.shape(data,{'library','id','revision','parent_job_id'})
            library,id,revision=self.candidate_identity({key:data[key] for key in ('library','id','revision')})
            parent=self.uuid_value(data['parent_job_id'])
            self.response(202,self.server.merge.replace_audiobook(library,id,revision,parent));return
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
            self.response(200,(self.server.merge.automatic.stop() if hasattr(self.server.merge,'automatic') and self.server.merge.automatic.status()['state'] in ('Running','Stopping') else self.server.merge.pause()) if path.endswith('/pause') else self.server.merge.resume())
            return
        if path=='/api/audiobook/recovery/delete':
            if set(data)!={'job_id','token','count','bytes'}:raise ValueError('Recovery deletion requires the displayed book and recovery scope')
            job_id=data['job_id']
            if not isinstance(job_id,str) or str(uuid.UUID(job_id))!=job_id:raise ValueError('Invalid audiobook identity')
            if not isinstance(data['token'],str) or len(data['token'])!=64 or any(c not in '0123456789abcdef' for c in data['token']):raise ValueError('Invalid recovery scope token')
            if type(data['count']) is not int or not 0<data['count']<=10000 or type(data['bytes']) is not int or not 0<=data['bytes']<=9223372036854775807:raise ValueError('Invalid recovery scope count or bytes')
            self.response(202,self.server.merge.delete_recovery(job_id,data['token'],data['count'],data['bytes']));return
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
        self.status_control=True # Consumed by response(); see there.
        admitted=False
        try:
            path,query=self.query()
            if query: raise ValueError('Control requests do not accept query parameters')
            data=self.body()
            merge_routes={'/api/automatic/start','/api/automatic/stop','/api/automatic/draft','/api/inspect','/api/open-folder','/api/candidate/review','/api/candidate/match','/api/candidate/covers','/api/candidate/tracks','/api/audiobook/create','/api/audiobook/replace','/api/audiobook/queue','/api/audiobook/pause','/api/audiobook/resume','/api/audiobook/cleanup','/api/audiobook/restore','/api/audiobook/recovery/delete','/api/audiobook/retry','/api/audiobook/repair','/api/audiobook/retry-all','/api/audiobook/keep',
                         '/api/audiobook/startover','/api/audiobook/release','/api/audiobook/release-selected','/api/automatic/cancel-start',
                         '/api/audiobook/clear-working'}
            with self.server.control_lock:
                if self.server.closing:
                    self.fail(409,'The local server is stopping or stopped. Start is unavailable.' if path=='/api/automatic/start' else 'Server is shutting down');return
                if path in {'/api/scan/start','/api/scan/resume','/api/scan/stop'}:
                    if set(data)!={'library'}: raise ValueError('Scan controls require only a library')
                    library=self.library(data['library'])
                    if hasattr(self.server.merge,'automatic') and self.server.merge.automatic.status()['state'] in ('Running','Stopping'):
                        self.fail(409,'Automatic processing owns discovery; use Stop automatic processing');return
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
                    if data:
                        if set(data)!={'restart_instance'} or data['restart_instance']!=self.server.instance:
                            raise ValueError('Restart requires the current owned app instance')
                        if self.server.merge_admissions:
                            self.fail(409,'Books Arranger is working with recovery copies. Wait for it to finish, then choose Restart Books Arranger.' if self.server.recovery_operations else 'Books Arranger could not verify the app to restart. The restart was cancelled.');return
                        from app_launcher import verify_idle
                        try:verify_idle(self.server.state('Audiobooks'))
                        except RuntimeError as error:
                            self.fail(409,str(error));return
                    self.server.closing=True;self.server.inventory.stop()
                    self.response(200,{'stopping':True})
                    threading.Thread(target=self.server.finish_shutdown,daemon=True).start();return
                if path in merge_routes:
                    if path in {'/api/audiobook/create','/api/audiobook/queue','/api/audiobook/resume','/api/audiobook/cleanup','/api/audiobook/restore','/api/audiobook/recovery/delete'} and self.server.scan_active():
                        self.fail(409,'Stop scanning before queueing or resuming audiobook jobs');return
                    if path in {'/api/audiobook/retry','/api/audiobook/retry-all','/api/audiobook/repair'} and self.server.scan_active():
                        from audio_jobs import RETRY_SCANNING,REPAIR_SCANNING
                        self.fail(409,REPAIR_SCANNING if path=='/api/audiobook/repair' else RETRY_SCANNING);return
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

def read_instance_record(path):
    """Read exact ordinary ownership bytes, compatible with the live write-denying owner."""
    import ctypes
    from native_io import ordinary, VerifiedFile, FileInfo, kernel
    held=VerifiedFile(ordinary(path))
    # Request READ only; permit the already-existing service's WRITE access.
    held.handle=kernel.CreateFileW(str(held.path),0x81,3,None,3,0x00200000,None)
    if held.handle==ctypes.c_void_p(-1).value:
        held.handle=None;raise RuntimeError('The app ownership record could not be read safely')
    try:
        held.info=FileInfo()
        if not kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)) or held.info.attributes&(0x400|0x10):raise RuntimeError('The app ownership record is not an ordinary file')
        before=held.facts()
        if before['links']!=1 or before['size']>4096:raise RuntimeError('The app ownership record is not a bounded unique file')
        raw=b''.join(held.chunks())
        if not kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)) or held.facts()!=before:raise RuntimeError('The app ownership record changed during reading')
        return raw
    finally:held.__exit__(None,None,None)

@contextlib.contextmanager
def owned_instance_record(path, health):
    """Protect a new record from birth; preserve substitutions at retirement."""
    import ctypes
    from ctypes import wintypes
    from native_io import ordinary, VerifiedFile, FileInfo, kernel
    from source_cleanup import single_stream
    path=ordinary(path);held=VerifiedFile(path,writable=True)
    # CREATE_NEW refuses all existing entries; deny outside WRITE/DELETE from birth.
    held.handle=kernel.CreateFileW(str(path),0xC0000081,1,None,1,0x00200000,None)
    if held.handle==ctypes.c_void_p(-1).value:
        held.handle=None;raise RuntimeError('Books Arranger ownership record already exists or could not be created safely')
    try:
        held.info=FileInfo()
        if not kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)) or held.info.attributes&(0x400|0x10) or held.info.links!=1:raise RuntimeError('Books Arranger ownership record is not an ordinary unique file')
        raw=json.dumps(health,ensure_ascii=False).encode('utf-8')
        if len(raw)>4096:raise RuntimeError('Books Arranger ownership record is too large')
        kernel.WriteFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p];kernel.WriteFile.restype=wintypes.BOOL
        buffer=ctypes.create_string_buffer(raw);count=wintypes.DWORD()
        if not kernel.WriteFile(held.handle,buffer,len(raw),ctypes.byref(count),None) or count.value!=len(raw):raise RuntimeError('Books Arranger ownership record could not be saved')
        held.flush()
        yield
    finally:
        # These are proven producer bytes: born CREATE_NEW and continuously write/delete-denied.
        try:
            if not kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)):raise RuntimeError('The owned instance identity could not be checked')
            produced=held.facts();produced_hash=held.sha256()
        finally:held.__exit__(None,None,None)
        with VerifiedFile(path,delete=True) as current:
            now=current.facts()
            if any(now[key]!=produced[key] for key in ('dev','ino','identity_method')) or now['links']!=1 or now['size']!=produced['size'] or current.sha256()!=produced_hash:raise RuntimeError('Changed ownership record retained for recovery')
            single_stream(path)
            current.dispose()

def main(argv=None, *, ready=None, before_start=None, startup_guard=None, create_data=True):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',default=str(BASE / 'data' / 'inventory.sqlite3'))
    parser.add_argument('--roots-json',help='Optional local fixture roots; not exposed through HTTP')
    parser.add_argument('--port',type=int,default=PORT,help='Strict loopback port; no fallback when occupied')
    args = parser.parse_args(argv)
    if not 1024<=args.port<=65535:parser.error('Port must be between 1024 and 65535')
    port = args.port
    roots = DEFAULT_ROOTS
    if args.roots_json:
        roots = json.loads(Path(args.roots_json).read_text(encoding='utf-8'))
        if set(roots)!=set(DEFAULT_ROOTS) or any(not isinstance(path,str) or not os.path.isabs(path) for path in roots.values()):
            parser.error('Root configuration must contain exactly the three absolute library paths')
    from scanner import inside
    from native_io import DirectoryBoundary
    database_path = Path(args.database).absolute()
    if any(inside(database_path, root) for root in roots.values()):
        raise ValueError('Keep the inventory database outside source libraries')
    # Existing mode cannot create missing ancestry. Explicit new mode alone may
    # create the selected empty folder; the final guard runs before lock/schema.
    with DirectoryBoundary(database_path.anchor, database_path.parent, create=create_data):
        if startup_guard is not None:startup_guard(database_path, roots, port)
        with catalog_lock(args.database,roots):
            if before_start is not None:before_start(database_path, roots, port)
            return serve_owned(args, roots, port, ready)


def serve_owned(args, roots, port, ready):
    inventory = Inventory(args.database,roots)
    try:
        server = BrowserServer(('127.0.0.1',port),inventory)
    except OSError as error:
        raise RuntimeError(f'Books Arranger cannot bind its assigned port {port}; stop the existing owner first. No fallback port is used.') from error
    instance_file = Path(args.database).parent / 'web-instance.json'
    try:
        from native_io import DirectoryBoundary
        with DirectoryBoundary(instance_file.anchor,instance_file.parent),owned_instance_record(instance_file,server.health() | {'url':f'http://127.0.0.1:{port}/'}):
            def stop(_signal=None,_frame=None):
                inventory.stop()
                server.closing = True
                threading.Thread(target=server.finish_shutdown,daemon=True).start()
            signal.signal(signal.SIGINT,stop)
            if hasattr(signal,'SIGTERM'):signal.signal(signal.SIGTERM,stop)
            if sys.stdout is not None:
                print(f'Books Arranger {server.loaded_version} — http://127.0.0.1:{port}/ — PID {os.getpid()}',flush=True)
            if ready is not None:ready(server)
            server.serve_forever(poll_interval=.2)
    finally:
        inventory.stop()
        if inventory.worker and inventory.worker.is_alive():inventory.worker.join(timeout=20)
        server.server_close()

if __name__ == '__main__':
    main()
