"""Startup (ruling 28; Judy's 0.22.1 UX spec, section 3): the engine answers at once and loads in the background.

Sergei 2026-10-25: "Show me the screen and load whatever you want after." The engine used to open the whole catalog
before it answered anything (1 min 40 s on the 706 MB catalog, no window). Private fixture catalogs only."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from audio_jobs import AudioJobs
from desktop_backend import DesktopControl
from encoding_policy import PROFILE
import groups
import scanner
import web_server

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'startup-loading-tests'
AREA.mkdir(parents=True, exist_ok=True)


class SlowMerge:
    """A catalog service whose construction waits for the test, reporting each finished book like MergeService."""

    def __init__(self, inventory, cache, progress=None, gate=None, books=3, fail=None):
        self.inventory = inventory
        self.closed = False
        self.started = []
        for done in range(books):
            if progress is not None:
                progress(done, books)
            gate.wait(10)
        if fail:
            raise RuntimeError(fail)
        if progress is not None:
            progress(books, books)

    def status_snapshot(self):
        return {'state': 'Paused', 'queued': 0, 'jobs': [], 'attention_counts': {'retry': 0}}

    state = status_snapshot

    def cached_page(self, limit, offset, search, status, group=None):
        return {'rows': [], 'total': 0}

    def start_retention(self, admission):
        self.started.append('retention')

    def start_published_check(self):
        self.started.append('published')

    def close(self):
        self.closed = True


class LoadingServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        root = Path(self.temp.name)
        self.roots = {name: str(root / name) for name in ('Audiobooks', 'Podcasts', 'Ebooks')}
        for path in self.roots.values():
            Path(path).mkdir()
        self.inventory = scanner.Inventory(root / 'catalog.sqlite3', self.roots)
        with scanner.connect(self.inventory.database) as db:
            groups.sync(db, self.roots['Audiobooks'])  # stored groups current: loading writes nothing
        self.gate = threading.Event()
        self.server = None

    def tearDown(self):
        self.gate.set()
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        self.temp.cleanup()

    def serve(self, **options):
        factory = lambda inventory, cache, progress=None: SlowMerge(inventory, cache, progress, self.gate, **options)
        started = time.perf_counter()
        self.server = web_server.BrowserServer(('127.0.0.1', 0), self.inventory, factory, defer=True)
        threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .05}, daemon=True).start()
        self.server.start_loading()
        return started

    def call(self, method, route, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers = {'X-Books-Token': self.server.token, 'Host': f'127.0.0.1:{self.server.server_port}'}
        raw = None
        if body is not None:
            raw = json.dumps(body).encode('utf-8')
            headers.update({'Content-Type': 'application/json', 'Content-Length': str(len(raw))})
        connection.request(method, route, body=raw, headers=headers)
        response = connection.getresponse()
        value = json.loads(response.read().decode('utf-8'))
        connection.close()
        return response.status, value

    def wait_for(self, check, seconds=5):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            value = check()
            if value:
                return value
            time.sleep(.02)
        self.fail('condition not reached')

    def test_health_and_a_loading_state_answer_at_once_while_the_catalog_loads(self):
        started = self.serve()
        status, health = self.call('GET', '/api/health')
        self.assertEqual(status, 200)
        self.assertLess(time.perf_counter() - started, 2, 'the engine answers before the catalog is open')
        status, state = self.call('GET', '/api/state?library=Audiobooks')
        self.assertEqual(status, 200)
        loading = state['loading']
        self.assertIn(loading['step'], ('catalog', 'session'))
        self.assertEqual(loading['of'], 4)
        self.assertEqual(loading['parts'], {'library': True, 'status': True, 'books': False, 'attention': False, 'jobs': False})
        self.assertIsNone(loading['took_ms'])
        self.assertTrue(loading['restart_safe'])
        # A part that has not arrived is absent, never 0, [] or '' (Judy 3.5).
        for absent in ('audiobook_jobs', 'automatic_processing', 'activities'):
            self.assertNotIn(absent, state)
        self.assertEqual(state['source_roots'], [self.roots['Audiobooks']])
        self.assertIn('count', state['status'])
        status, page = self.call('GET', '/api/inventory?library=Audiobooks&view=candidates&status=converted')
        self.assertEqual((status, page.get('code')), (503, 'loading'))
        # The strip's shared states script is served beside app.js (the page loads it relative, as from disk).
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request('GET', '/load-state.js', headers={'Host': f'127.0.0.1:{self.server.server_port}'})
        response = connection.getresponse()
        self.assertEqual((response.status, response.getheader('Content-Type')), (200, 'text/javascript; charset=utf-8'))
        self.assertIn(b'booksLoadState', response.read())
        connection.close()

    def test_the_session_step_counts_each_finished_book_then_parts_arrive_and_loading_ends(self):
        self.serve(books=3)
        loading = self.wait_for(lambda: (lambda view: view if view['step'] == 'session' and view['total'] == 3 else None)(self.server.loading.view()))
        self.assertEqual((loading['n'], loading['unit'], loading['done']), (3, 'items', 0))
        self.assertLess(loading['progress_age_ms'], 5000)
        self.gate.set()
        self.wait_for(lambda: self.server.loading.finished)
        status, state = self.call('GET', '/api/state?library=Audiobooks')
        self.assertEqual(status, 200)
        self.assertEqual(state['loading']['parts'], dict.fromkeys(web_server.LOAD_PARTS, True))
        self.assertIsInstance(state['loading']['took_ms'], int)
        self.assertEqual(state['audiobook_jobs']['state'], 'Paused')
        # Background work starts once loading ends, never before the first status.
        self.assertEqual(self.server.merge.started, ['retention', 'published'])
        # The shell reads the completed load's time from the desktop status, to show it as "last load took" next start.
        self.assertEqual(DesktopControl(self.server).status()['loading']['took_ms'], state['loading']['took_ms'])
        status, _ = self.call('GET', '/api/inventory?library=Audiobooks&view=candidates&status=converted')
        self.assertEqual(status, 200)

    def test_rebuilding_stale_groups_is_the_catalog_step_and_offers_no_restart(self):
        import catalog_contention
        entered, release = threading.Event(), threading.Event()
        rebuild = catalog_contention.synchronize_groups
        with patch.object(catalog_contention, 'groups_current', return_value=False), \
             patch.object(catalog_contention, 'synchronize_groups', side_effect=lambda *a: (entered.set(), release.wait(5), rebuild(*a))):
            self.serve()
            self.assertTrue(entered.wait(5))
            status, state = self.call('GET', '/api/state?library=Audiobooks')
            self.assertEqual((status, state['loading']['step'], state['loading']['n']), (200, 'catalog', 2))
            self.assertFalse(state['loading']['restart_safe'], 'the engine is changing the catalog')
            release.set()
            self.wait_for(lambda: self.server.loading.view()['step'] == 'session')
        self.assertTrue(self.server.loading.view()['restart_safe'])

    def test_changing_controls_are_refused_while_loading_with_the_pages_sentence(self):
        self.serve()
        for route, body in (('/api/scan/start', {'library': 'Audiobooks'}), ('/api/automatic/start', {}),
                            ('/api/audiobook/retry', {'library': 'Audiobooks'}), ('/api/inspect', {})):
            status, answer = self.call('POST', route, body)
            self.assertEqual((status, answer), (409, {'error': web_server.NOT_YET, 'code': 'loading'}), route)
        self.assertIsNone(self.inventory.worker, 'no scan started')

    def test_quit_while_loading_stops_the_loader_and_closes_without_a_catalog_service(self):
        self.serve(books=50)
        self.wait_for(lambda: self.server.loading.view()['step'] == 'session')
        control = DesktopControl(self.server)
        self.assertEqual(control.status()['loading']['step'], 'session')
        self.assertIsNone(control.status()['busy'])
        with patch.object(self.server, 'shutdown', wraps=self.server.shutdown) as shutdown:
            self.assertEqual(control.quit()['phase'], 'stopping')
            self.gate.set()
            self.wait_for(lambda: shutdown.called)
        self.assertFalse(self.server.loader.is_alive())
        self.assertIsNone(self.server.merge)
        self.wait_for(lambda: control.status()['phase'] == 'exiting')
        self.server = None  # already shut down

    def test_an_update_while_loading_ends_the_engine_at_once(self):
        self.serve(books=50)
        self.wait_for(lambda: self.server.loading.view()['step'] == 'session')
        control = DesktopControl(self.server)
        with patch.object(self.server, 'shutdown', wraps=self.server.shutdown) as shutdown:
            answer = control.prepare_update()
            self.assertEqual(answer['update']['phase'], 'updating')
            self.gate.set()
            self.wait_for(lambda: shutdown.called)
        self.wait_for(lambda: control.status()['phase'] == 'exiting')
        self.server = None

    def test_a_failed_load_ends_the_engine_with_its_message(self):
        self.serve(books=1, fail='Pending output moves need recovery first')
        self.gate.set()
        self.wait_for(lambda: self.server.loading.error)
        self.assertEqual(self.server.loading.view()['error'], 'Pending output moves need recovery first')
        self.wait_for(lambda: self.server.closing)
        loader = self.server.loader
        loader.join(5)
        self.assertFalse(loader.is_alive())


def manifest():
    return {'job_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
            'sources': [{'sha256': 'a' * 64, 'fingerprint': {}}], 'metadata': {}, 'destination': 'fixture',
            'profile': PROFILE, 'evidence': {}, 'cover': {}}


class ConstructionTests(unittest.TestCase):
    """MergeService construction looks each finished book up once and seeds the first status's lookups."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        root = Path(self.temp.name)
        self.roots = {name: str(root / name) for name in ('Audiobooks', 'Podcasts', 'Ebooks')}
        for path in self.roots.values():
            Path(path).mkdir()
        self.database = root / 'catalog.sqlite3'
        self.inventory = scanner.Inventory(self.database, self.roots)
        seed = AudioJobs(self.database, None, lambda m: True, lambda r: True)
        self.done = [manifest() for _ in range(4)]
        for item in self.done:
            seed.enqueue(item)
            output = {'job_id': item['job_id'], 'final_path': str(root / 'Audiobooks' / (item['job_id'] + '.m4b')),
                      'owned_temp': 'fixture.partial', 'sha256': 'b' * 64, 'size': 1, 'validation': {'passed': True}}
            seed._update(item['job_id'], state='completed', stage='completed', output=json.dumps(output))
        seed.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_each_finished_book_is_looked_up_once_and_seeds_the_status_cache(self):
        from merge_service import MergeService
        from publication_binding import PublicationBindings
        from source_cleanup import CleanupJobs
        seen, per_book = [], []
        lookup = PublicationBindings.lookup
        with patch.object(PublicationBindings, 'current', side_effect=AssertionError('no leased lookup at startup')), \
             patch.object(PublicationBindings, 'lookup', autospec=True, side_effect=lambda *a, **k: (seen.append(a[2]['job_id']), lookup(*a, **k))[1]), \
             patch.object(CleanupJobs, 'status', autospec=True, side_effect=lambda cleanup, job_id=None: per_book.append(job_id) if job_id else []):
            progress = []
            merge = MergeService(self.inventory, Path(self.temp.name) / 'merge-cache', progress=lambda done, total: progress.append((done, total)))
        try:
            ids = sorted(item['job_id'] for item in self.done)
            self.assertEqual(sorted(seen), ids)
            self.assertEqual(per_book, [], 'enrollment is read once, not through each book\'s full cleanup status')
            self.assertEqual(sorted(merge._lookups), ids)
            self.assertEqual(progress, [(0, 4), (1, 4), (2, 4), (3, 4), (4, 4)])
            with scanner.connect(self.database) as db:
                self.assertEqual(sorted(r[0] for r in db.execute("SELECT job_id FROM owned_artifacts WHERE kind='output'")), ids)
            # The first status reuses every seeded lookup: nothing is resolved again.
            seen.clear()
            with patch.object(PublicationBindings, 'lookup', autospec=True, side_effect=lambda *a, **k: (seen.append(a[2]['job_id']), lookup(*a, **k))[1]):
                with scanner.connect(self.database) as db:
                    db.execute('BEGIN')
                    token = merge.publication_bindings.lookup_token(db)
                self.assertTrue(all(key[0] == token for key, _ in merge._lookups.values()))
                # The first book page's display lookups are the same answers: none is resolved again.
                for item in self.done:
                    with scanner.connect(self.database) as db:
                        row = db.execute('SELECT output FROM audio_jobs WHERE job_id=?', (item['job_id'],)).fetchone()
                    merge.publication_bindings.display(json.loads(row[0]), 'base')
                self.assertEqual(seen, [])
        finally:
            merge.automatic.close(2)
            merge.jobs.close(2)
            merge.close()

    def test_the_first_status_reads_each_enrolled_book_once_with_a_counter(self):
        from merge_service import MergeService
        from source_cleanup import CleanupJobs
        merge = MergeService(self.inventory, Path(self.temp.name) / 'merge-cache')
        try:
            enrolled = [self.done[1]['job_id'], self.done[0]['job_id']]
            with scanner.connect(self.database) as db:
                for second, job_id in enumerate(enrolled):
                    db.execute('INSERT INTO source_cleanup VALUES(?,?,?,?,?,?,?)', (str(uuid.uuid4()), job_id, json.dumps({'manifest': {'sources': []}}),
                               'completed', '', '2026-10-25T00:00:0%d' % second, ''))
            full = [row['job_id'] for row in merge.cleanup.status()]
            calls, progress = [], []
            status = CleanupJobs.status
            with patch.object(CleanupJobs, 'status', autospec=True, side_effect=lambda cleanup, job_id=None: (calls.append(job_id), status(cleanup, job_id))[1]):
                value = merge.warm_status(progress=lambda done, total: progress.append((done, total)))
            self.assertEqual(progress, [(0, 2), (1, 2), (2, 2)])
            self.assertEqual(calls, enrolled, 'one read per enrolled book; the status reuses them, no full read')
            self.assertEqual(full, enrolled)
            self.assertIn('attention_counts', value)
        finally:
            merge.automatic.close(2)
            merge.jobs.close(2)
            merge.close()



class ColdServePendingPageTests(unittest.TestCase):
    """Real serve_owned/HTTP/desktop-ready with 669 private existing-style cleanup rows.

    This is synthetic data, not Sergei's catalog. All source/output paths stay in
    the fixture; external/background work is withheld while testing readiness.
    """
    def setUp(self):
        from source_cleanup import setup
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.root = Path(self.temp.name)
        self.roots = {name: str(self.root / name) for name in ('Audiobooks','Podcasts','Ebooks')}
        for p in self.roots.values(): Path(p).mkdir()
        self.database = self.root / 'catalog.sqlite3'
        inventory = scanner.Inventory(self.database,self.roots)
        seed = AudioJobs(self.database,None,lambda m:True,lambda r:True)
        item = manifest();seed.enqueue(item)
        with scanner.connect(self.database) as db:
            setup(db);groups.sync(db,self.roots['Audiobooks'])
            template=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(item['job_id'],)).fetchone())
            db.execute('DELETE FROM audio_jobs')
            keys=list(template);sql='INSERT INTO audio_jobs('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')'
            # Only the reported-size cold case needs 669 rows; failure/abort use the same path with three.
            count=669 if self._testMethodName=='test_cold_669_row_startup_keeps_one_pending_page_worker_and_publishes_ready_only_after_completion' else 3
            for n in range(count):
                m=manifest();row=dict(template);row.update(job_id=m['job_id'],manifest=json.dumps(m),state='completed',stage='completed',output=json.dumps({'job_id':m['job_id'],'final_path':str(self.root/'Audiobooks'/f'{n}.m4b'),'sha256':'b'*64,'size':1,'validation':{'passed':True}}))
                db.execute(sql,[row[k] for k in keys])
                db.execute('INSERT INTO source_cleanup VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),m['job_id'],json.dumps({'job_id':m['job_id'],'manifest':{'sources':[],'root':str(self.root/'Audiobooks')},'output':json.loads(row['output'])}),'completed','',f'2026-11-02T00:00:{n:04d}',''))
        seed.close();self.server=None;self.release=threading.Event();self.started=threading.Event();self.finished=threading.Event();self.errors=[];self.workers=0;self.background=[]

    def tearDown(self):
        self.release.set()
        # Real status/page workers can outlive a bounded HTTP answer. Wait for
        # these owned fixture reads before closing/removing the private catalog.
        merge=getattr(self,'fixture_merge',None)
        if merge is not None:
            shared=[getattr(merge,'_status_shared',None),*merge.__dict__.get('_page_shared',{}).values()]
            for snapshot in shared:
                flight=getattr(snapshot,'_flight',None)
                if flight is not None:self.assertTrue(flight['done'].wait(30),'fixture shared read did not finish')
        if self.server and not self.finished.is_set():
            self.server.stop_loading();self.server.shutdown()
        if hasattr(self,'runner'):
            self.runner.join(30);self.assertFalse(self.runner.is_alive(),'fixture serve_owned did not close')
        self.temp.cleanup()

    def start(self, failure=None):
        from argparse import Namespace
        from merge_service import MergeService,SharedSnapshot
        real=web_server.BrowserServer
        owner=self
        def factory(inventory,cache,progress=None):
            merge=MergeService(inventory,cache,progress=progress);self.fixture_merge=merge
            original=merge.reviews.page
            def page(*a,**kw):
                owner.workers+=1;owner.started.set()
                if not owner.release.wait(10):raise RuntimeError('fixture release not supplied')
                if failure:raise RuntimeError(failure)
                return original(*a,**kw)
            merge.reviews.page=page
            merge._page_shared={(100,0,'','converted',None):SharedSnapshot(wait=.05,keep_flight=True)}
            merge.start_retention=lambda admission:owner.background.append('retention')
            merge.start_published_check=lambda:owner.background.append('published')
            return merge
        class Server(real):
            def __init__(self,*a,**kw):super().__init__(*a,merge_factory=factory,**kw)
        def ready(server):
            from desktop_backend import handler_class
            self.server=server;server.RequestHandlerClass=handler_class(web_server.Handler,'fixture-desktop-token');server.desktop=DesktopControl(server)
        def run():
            try:
                with patch.object(web_server,'BrowserServer',Server),patch.object(web_server.signal,'signal'):
                    web_server.serve_owned(Namespace(database=str(self.database)),self.roots,0,ready)
            except BaseException as error:self.errors.append(error)
            finally:self.finished.set()
        self.runner=threading.Thread(target=run,daemon=True);self.runner.start()
        self.assertTrue(self.started.wait(60),'cold loader must reach actual shared initial page')

    def call(self,route):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=6)
        c.request('GET',route,headers={'Host':f'127.0.0.1:{self.server.server_port}','X-Books-Token':self.server.token,'X-Books-Desktop':'fixture-desktop-token'})
        r=c.getresponse();answer=json.loads(r.read());c.close();return r.status,answer

    def test_cold_669_row_startup_keeps_one_pending_page_worker_and_publishes_ready_only_after_completion(self):
        self.start();time.sleep(.15)  # beyond several shortened reader bounds, not an artificial thrown exception
        self.assertEqual(self.errors,[])
        self.assertEqual(self.server.loading.error,'','pending shared page is not a failed catalog')
        self.assertFalse(self.finished.is_set())
        self.assertFalse(self.server.loading.finished)
        self.assertEqual((self.server.loading.done,self.server.loading.total),(669,669))
        self.assertEqual(self.call('/api/health')[0],200)
        code,state=self.call('/api/state?library=Audiobooks');self.assertEqual(code,200)
        self.assertFalse(state['loading']['parts']['books'])
        code,desktop=self.call('/api/desktop/status');self.assertEqual(code,200)
        self.assertIsNone(desktop['busy']);self.assertFalse(desktop['loading']['parts']['books'])
        self.assertEqual(self.workers,1);self.assertEqual(self.background,[])
        self.release.set();self.server.loader.join(10)
        self.assertTrue(self.server.loading.finished,self.server.loading.error)
        self.assertEqual(self.workers,1,'retry must join the same expensive page read')
        code,desktop=self.call('/api/desktop/status');self.assertEqual(code,200);self.assertIsInstance(desktop['loading']['took_ms'],int)
        self.assertEqual(self.background,['retention','published'])
        self.assertEqual(self.call('/api/inventory?library=Audiobooks&view=candidates&status=converted')[0],200)
        self.assertEqual(self.errors,[])

    def test_real_page_failure_remains_fatal_and_does_not_publish_ready(self):
        self.start(failure='fixture real page read failed');self.release.set()
        self.assertTrue(self.finished.wait(10))
        self.assertEqual([str(e) for e in self.errors],['fixture real page read failed'])
        self.assertIsInstance(self.errors[0],RuntimeError)
        self.assertFalse(self.server.loading.finished);self.assertEqual(self.background,[])

    def test_quit_during_pending_initial_page_interrupts_the_loader_without_starting_another_read(self):
        self.start();time.sleep(.15)
        self.assertEqual(self.server.loading.error,'')
        self.server.stop_loading();self.release.set();self.server.loader.join(5)
        self.assertFalse(self.server.loader.is_alive());self.assertFalse(self.server.loading.finished)
        self.assertEqual(self.workers,1);self.assertEqual(self.background,[])

if __name__ == '__main__':
    unittest.main()
