"""0.22.1, ruling 27 (Sergei 2026-10-25, "updates must not fail"): the engine's side of Restart to update.

0.21.1's update request computed a fresh, unbounded full state while the shell waited 5 s for it; the shell gave up,
the engine finished the fence anyway, shut down, and the app closed without installing. Nothing undid the fence. Now
the request answers at once, the work stops at its safe points within bounds, the engine ends only with nothing left
running and no file change half done, and Cancel or the bound undo everything. A fake engine; the busy-engine matrix
of the proposal (section 5E) that does not need a packaged build."""
import io
from pathlib import Path
import tempfile
import threading
import time
from email.message import Message
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import critical_sections
from desktop_backend import DesktopControl, UpdateStarted, handler_class
from scan_wait import close_scan, finish_scan
from web_server import Handler

TOKEN = 'd' * 64
AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'desktop-update-tests'
AREA.mkdir(parents=True, exist_ok=True)


class Worker:
    """A thread stand-in: alive until stopped (after `lag` seconds), or never when `stubborn`."""
    def __init__(self, alive=True, lag=0.0, stubborn=False):
        self.alive, self.lag, self.stubborn = alive, lag, stubborn

    def stop(self):
        if self.stubborn or not self.alive:
            return
        if self.lag:
            threading.Timer(self.lag, lambda: setattr(self, 'alive', False)).start()
        else:
            self.alive = False

    def is_alive(self):
        return self.alive

    def join(self, timeout=None):
        end = time.monotonic() + (timeout if timeout is not None else 1e9)
        while self.alive and time.monotonic() < end:
            time.sleep(0.01)


def engine(*, converting=False, scanning=False, automatic=False, stubborn=False, admissions=0, slow_state=0.0):
    """A fake server/merge with the attributes the update reads."""
    jobs = Worker(converting, lag=0.2, stubborn=stubborn)
    scan = Worker(scanning, lag=0.2)
    research = Worker(automatic, lag=0.2)
    lock = threading.Lock()
    calls = []
    merge = SimpleNamespace(jobs=SimpleNamespace(_thread=jobs), cleanup=SimpleNamespace(current=None, thread=None), _post_current=None,
                            inventory=SimpleNamespace(database=':memory:'))
    merge.pause = Mock(side_effect=lambda: (calls.append('pause'), jobs.stop()))
    merge.resume = Mock(side_effect=lambda **kw: calls.append(('resume', kw)))
    auto = SimpleNamespace(thread=research, current={'stage': 'Researching work identity'} if automatic else None)
    auto.stop = Mock(side_effect=lambda force=False: (calls.append(('automatic stop', force)), research.stop()))
    auto.start = Mock(side_effect=lambda: calls.append('automatic start'))
    auto.status = Mock(return_value={'state': 'Running' if automatic else 'Idle'})
    merge.automatic = auto
    inventory = SimpleNamespace(worker=scan, stop=Mock(side_effect=lambda: (calls.append('scan stop'), scan.stop())),
                                launch=Mock(side_effect=lambda library, resume=False: calls.append(('scan resume', library, resume))))
    def state(*args, **kwargs):
        time.sleep(slow_state); return {'state': 'Paused'}
    server = SimpleNamespace(merge=merge, inventory=inventory, closing=False, control_lock=lock, control_condition=threading.Condition(lock),
                             merge_admissions=admissions, scan_active=lambda: scan.is_alive(), active_library='Audiobooks' if scanning else None,
                             finish_shutdown=Mock(side_effect=lambda: calls.append('shutdown')), state=Mock(side_effect=state))
    return server, calls


def control(server, safe=5.0, force=5.0, resume=0.5):
    value = DesktopControl(server)
    value.UPDATE_SAFE, value.UPDATE_FORCE, value.UPDATE_POLL, value.UPDATE_RESUME = safe, force, 0.02, resume
    return value


def finish(value, timeout=10):
    value.thread.join(timeout)
    return value.status()


class RequestTests(unittest.TestCase):
    def test_the_request_answers_at_once_even_when_the_state_computation_is_slow(self):
        # The live failure: a fresh state took longer than the shell's 5 s on the 706 MB catalog.
        server, _ = engine(slow_state=10.0)
        value = control(server)
        started = time.monotonic()
        with patch('app_launcher.verify_idle'):
            answer = value.prepare_update()
        self.assertLess(time.monotonic() - started, 1.0, 'the request computed state before answering')
        self.assertIn(answer['phase'], ('pausing', 'updating', 'exiting'))
        self.assertTrue(server.closing, 'new presses are refused from the request on')
        server.state.assert_not_called()
        finish(value)

    def test_a_repeated_request_answers_the_update_in_progress(self):
        server, _ = engine(converting=True, stubborn=True)
        value = control(server)
        first = value.prepare_update(); thread = value.thread
        second = value.prepare_update()
        self.assertEqual((first['phase'], second['phase']), ('pausing', 'pausing'))
        self.assertIs(value.thread, thread, 'one update, not two')
        value.cancel_update()

    def test_the_confirm_names_the_queued_actions_and_quit_or_the_update_drops_them(self):
        # 0.22.1 (Judy 1.8 and 2.4; Sergei, Q1): queued Retry and Delete presses are counted for the update's confirm, the
        # app is not idle while any waits, and Restart to update or Quit drops them without running one.
        from action_queue import ActionQueue
        for leave in ('update', 'quit'):
            server, _ = engine(scanning=True)
            server.actions = ActionQueue(server, poll=.02)
            server.merge.drain, server.merge.drained = Mock(), Mock(return_value=True)
            self.addCleanup(server.actions.close)
            self.assertTrue(server.actions.enqueue('retry', 'book-1', 'Book', {'revision': 1, 'job_id': 'job-1'})['queued'])
            self.assertTrue(server.actions.enqueue('retry', 'book-2', 'Book', {'revision': 1, 'job_id': 'job-2'})['queued'])
            value = control(server)
            with patch('app_launcher.verify_idle'):
                status = value.status()
            self.assertEqual((status['queued_actions'], status['idle']), (2, False), leave)
            if leave == 'update':
                value.prepare_update()
            else:
                value.quit()
            self.assertEqual(server.actions.count(), 0, leave)
            self.assertEqual(server.actions.view()['queued_actions'], [], leave)
            if leave == 'update':
                value.cancel_update()
            else:
                finish(value)

    def test_status_during_the_update_answers_without_a_state_computation(self):
        server, _ = engine(converting=True, stubborn=True, slow_state=10.0)
        value = control(server)
        value.prepare_update()
        started = time.monotonic(); status = value.status()
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual(status['update']['phase'], 'pausing'); self.assertIsNone(status['busy'])
        value.cancel_update()


class MatrixTests(unittest.TestCase):
    """The busy-engine matrix of the proposal: each ends with the engine stopped safely, or cancelled and running."""
    def test_idle_engine_stops_and_exits(self):
        server, calls = engine()
        value = control(server); value.prepare_update()
        status = finish(value)
        self.assertEqual(status['phase'], 'exiting'); self.assertIn('shutdown', calls)

    def test_a_conversion_stops_at_its_checkpoint_then_the_engine_exits(self):
        server, calls = engine(converting=True)
        value = control(server); value.prepare_update()
        time.sleep(0.05)
        self.assertIn('conversion', [w['kind'] for w in value.status()['update']['waiting']], 'what it waits for, by name')
        status = finish(value)
        self.assertEqual(status['phase'], 'exiting'); self.assertLess(calls.index('pause'), calls.index('shutdown'))

    def test_research_and_a_scan_stop_at_their_checkpoints(self):
        server, calls = engine(scanning=True, automatic=True)
        value = control(server); value.prepare_update()
        status = finish(value)
        self.assertEqual(status['phase'], 'exiting')
        self.assertIn(('automatic stop', False), calls); self.assertIn('scan stop', calls)

    def test_an_approval_in_flight_finishes_or_is_stopped_after_the_safe_wait(self):
        server, calls = engine(admissions=1)
        press = threading.Event(); server.merge._approve_stops = {press}
        def ended():
            press.wait(10)
            with server.control_condition:
                server.merge_admissions = 0
        threading.Thread(target=ended, daemon=True).start()
        value = control(server, safe=0.3, force=5.0); value.prepare_update()
        time.sleep(0.1)
        self.assertEqual(value.status()['update']['waiting'][0]['kind'], 'approval')
        status = finish(value)
        self.assertTrue(press.is_set(), 'after T_safe the press in flight is stopped')
        self.assertEqual(status['phase'], 'exiting')

    def test_an_open_file_change_is_never_interrupted(self):
        server, calls = engine()
        opened, release, closed = threading.Event(), threading.Event(), []
        def edit():
            with critical_sections.critical(critical_sections.TAG_EDIT):
                opened.set(); release.wait(10)
            closed.append(time.monotonic())
        threading.Thread(target=edit, daemon=True).start(); self.assertTrue(opened.wait(5))
        server.finish_shutdown.side_effect = lambda: calls.append(('shutdown', time.monotonic()))
        value = control(server, safe=0.1, force=10.0); value.prepare_update()
        time.sleep(0.4)
        status = value.status()
        self.assertEqual(status['update']['critical'], ['a tag edit']); self.assertEqual(status['update']['phase'], 'forcing')
        self.assertFalse([c for c in calls if isinstance(c, tuple) and c[0] == 'shutdown'], 'the engine stopped inside a tag edit')
        release.set(); finish(value)
        shutdown = next(c[1] for c in calls if isinstance(c, tuple) and c[0] == 'shutdown')
        self.assertGreaterEqual(shutdown, closed[0])

    def test_cancel_while_waiting_starts_everything_again(self):
        # Cancel arrives while the work is still stopping (each worker ends 0.2 s after its stop): it is started again
        # once it has ended, never while it still stops (Senua's 0.22.1 review, W3; the real workers are below).
        server, calls = engine(converting=True, automatic=True)
        value = control(server); value.prepare_update()
        time.sleep(0.05)
        answer = value.cancel_update()
        self.assertEqual(answer['phase'], 'running'); self.assertFalse(server.closing, 'presses work again')
        self.assertEqual(answer['update']['outcome']['result'], 'cancelled')
        self.assertEqual(answer['update']['outcome']['resume_problems'], [])
        self.assertIn('automatic start', calls, 'the automatic run continues')
        self.assertFalse(server.merge.automatic.thread.is_alive() or server.merge.jobs._thread.is_alive(), 'started only after they ended')
        self.assertNotIn('shutdown', calls)

    def test_a_cancel_restarts_the_queue_and_the_scan_that_ran(self):
        server, calls = engine(converting=True, scanning=True)
        value = control(server); value.prepare_update(); time.sleep(0.05)
        value.cancel_update()
        self.assertIn(('resume', {'recheck': False}), calls)
        self.assertIn(('scan resume', 'Audiobooks', True), calls)

    def test_work_that_has_not_stopped_in_time_is_named_and_not_started(self):
        # A conversion that will not stop: Cancel waits UPDATE_RESUME for it, then says what did not start again.
        server, calls = engine(converting=True, automatic=True, stubborn=True)
        value = control(server, resume=0.3); value.prepare_update(); time.sleep(0.05)
        outcome = value.cancel_update()['update']['outcome']
        self.assertEqual([(p['kind'], p['cause']) for p in outcome['resume_problems']], [('automatic', 'still_stopping')])
        self.assertNotIn('automatic start', calls, 'automatic processing cannot start beside a queue that is still pausing')

    def test_the_bound_cancels_and_keeps_the_app_running(self):
        # The last resort without proof that every write path survives a forced end: cancel and say what did not stop.
        server, calls = engine(converting=True, stubborn=True)
        value = control(server, safe=0.2, force=0.3); value.prepare_update()
        status = finish(value)
        self.assertEqual(status['phase'], 'running'); self.assertFalse(server.closing)
        outcome = status['update']['outcome']
        self.assertEqual(outcome['result'], 'bound'); self.assertEqual([w['kind'] for w in outcome['waiting']], ['conversion'])
        self.assertEqual([(p['kind'], p['cause']) for p in outcome['resume_problems']], [('conversion', 'still_stopping')], 'never "as before"')
        self.assertNotIn('shutdown', calls)

    def test_too_late_to_cancel_once_the_engine_is_ending(self):
        server, _ = engine()
        value = control(server); value.prepare_update(); finish(value)
        with self.assertRaises(UpdateStarted):
            value.cancel_update()

    def test_a_failed_close_undoes_the_update_and_says_why(self):
        server, calls = engine(automatic=True)
        server.finish_shutdown.side_effect = TimeoutError('worker still at checkpoint')
        value = control(server); value.prepare_update()
        status = finish(value)
        self.assertEqual(status['phase'], 'running'); self.assertFalse(server.closing)
        outcome = status['update']['outcome']
        self.assertEqual((outcome['result'], outcome['reason']), ('blocked', 'worker still at checkpoint'))
        self.assertIn('automatic start', calls)

    def test_quit_is_refused_while_an_update_runs(self):
        server, _ = engine(converting=True, stubborn=True)
        value = control(server); value.prepare_update()
        self.assertEqual(value.quit()['phase'], 'pausing'); value.cancel_update()


class RealWorkerResumeTests(unittest.TestCase):
    """Senua's 0.22.1 review, W3, with the real workers and their real restarts: MergeService and its AudioJobs queue,
    AutomaticProcessing, the Inventory scan, SeriesBackfill and GapFill on a private catalog. Each worker takes LAG
    seconds to stop after the update stops it (the step it is in reaches its checkpoint), so Cancel always arrives while
    it is still stopping: the case the fakes above could not show, because their restarts always succeeded. Before the
    fix every one stayed stopped: the queue's resume was refused ("still pausing"), the scan's ("already running"), and
    automatic processing and the lookups returned without starting."""
    LAG = 0.6

    def setUp(self):
        from merge_service import MergeService
        from scanner import Inventory
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        roots = {name: str(base / name) for name in ('Audiobooks', 'Podcasts', 'Ebooks')}
        for path in roots.values():
            Path(path).mkdir()
        (base / 'sorted').mkdir()
        (Path(roots['Audiobooks']) / 'John Writer - A Book.mp3').write_bytes(b'fixture only')
        self.reads = []
        self.slow_read = False
        self.inventory = Inventory(base / 'catalog.sqlite3', roots, self.read, output_root=str(base / 'sorted'))
        self.merge = MergeService(self.inventory, base / 'cache')
        self.addCleanup(self.close)
        lock = threading.Lock()
        self.server = SimpleNamespace(merge=self.merge, inventory=self.inventory, closing=False, control_lock=lock, control_condition=threading.Condition(lock),
                                      merge_admissions=0, scan_active=lambda: bool(self.inventory.worker and self.inventory.worker.is_alive()),
                                      active_library=None, finish_shutdown=Mock(), state=Mock())

    def close(self):
        for name in ('series_backfill', 'gap_fill'):
            worker = self.merge.__dict__.get(name)
            if worker is not None:
                worker.close()
        automatic = self.merge.__dict__.get('automatic')
        if automatic is not None:
            automatic.close()
        close_scan(self.inventory)
        self.merge.close()

    def read(self, path, kind, stop):
        """The scan's tag reader: the first read takes LAG to reach its checkpoint once the scan is stopped."""
        self.reads.append(path)
        if self.slow_read and len(self.reads) == 1:
            self.assertTrue(wait_until(stop.is_set, 10), 'the update stopped the scan')
            time.sleep(self.LAG)
        return {'title': 'A Book', 'artist': 'John Writer', 'tags': {'title': 'A Book', 'artist': 'John Writer', 'album': 'A Book', 'track': '1'},
                'probe': {'format': {'duration': '1'}}}

    def cancel_while_stopping(self, entered, value=None, meanwhile=None):
        """Restart to update once the worker is in its slow step, then Cancel while it is still stopping. meanwhile:
        the positive control, run while it stops: the restart the old code made at once."""
        self.assertTrue(entered.wait(10), 'the worker reached its slow step')
        value = value or control(self.server, resume=10.0)
        value.prepare_update()
        time.sleep(0.1)
        if meanwhile is not None:
            meanwhile()
        return value, value.cancel_update()

    def test_the_conversion_queue_starts_again_once_its_worker_has_stopped(self):
        jobs = self.merge.jobs
        entered, passes = threading.Event(), []
        def pending():
            # Called by each start of the real queue worker (and by state(), which is not counted).
            if threading.current_thread().name != 'BooksArrangerAudioJobs':
                return []
            passes.append(threading.current_thread())
            return ['fixture-job'] if len(passes) == 1 else []
        def postprocess(job_id):
            entered.set()
            self.assertTrue(wait_until(jobs._stop.is_set, 10), 'the update paused the queue')
            time.sleep(self.LAG)  # the book in progress reaches its checkpoint
            raise InterruptedError('Paused; the book restarts')
        jobs.pending_postprocessing, jobs.postprocessing = pending, postprocess
        self.merge.resume(recheck=False)
        def refused():
            # Positive control: the restart the old code made at once is refused by the real queue while it stops.
            from audio_jobs import StartRefused
            with self.assertRaisesRegex(StartRefused, 'still pausing'):
                self.merge.resume(recheck=False)
        value, answer = self.cancel_while_stopping(entered, meanwhile=refused)
        outcome = answer['update']['outcome']
        self.assertEqual((answer['phase'], outcome['result'], outcome['resume_problems']), ('running', 'cancelled', []))
        self.assertTrue(wait_until(lambda: len(passes) == 2, 10), 'the real queue worker ran again')
        self.assertIsNot(passes[0], passes[1], 'a new worker thread, started after the stopped one ended')
        self.assertFalse(jobs._stop.is_set())

    def test_automatic_processing_continues_its_run_once_it_has_stopped(self):
        from automatic_processing import AutomaticProcessing
        entered, calls = threading.Event(), []
        def lookup(row, root, stop, progress=None):
            calls.append(row['id'])
            if len(calls) == 1:
                entered.set()
                self.assertTrue(wait_until(stop.is_set, 10), 'the update stopped automatic processing')
                time.sleep(self.LAG)  # research reaches its checkpoint
            return {'reasons': ['Book identity uncertain'], 'sources': []}
        research = SimpleNamespace(client=SimpleNamespace(retry_wait=lambda wait: dict(wait)), lookup=lookup)
        automatic = AutomaticProcessing(self.merge, research)
        self.merge.automatic = automatic
        automatic.start()
        def skipped():
            # Positive control: while the old thread lives the real start returns without starting anything.
            thread = automatic.thread
            automatic.start()
            self.assertIs(automatic.thread, thread)
        value, answer = self.cancel_while_stopping(entered, meanwhile=skipped)
        self.assertEqual(answer['update']['outcome']['resume_problems'], [])
        self.assertTrue(wait_until(lambda: automatic.thread is not None and not automatic.thread.is_alive() and automatic.status()['state'] == 'Completed', 10),
                        'the run went on to its end, not left Paused: ' + automatic.status()['state'])
        self.assertEqual(len(calls), 2, 'the stopped book was researched again')

    def test_the_library_scan_resumes_once_it_has_stopped(self):
        self.slow_read = True
        self.inventory.launch('Audiobooks')
        self.server.active_library = 'Audiobooks'
        entered = threading.Event()
        threading.Thread(target=lambda: wait_until(lambda: self.reads, 10) and entered.set(), daemon=True).start()
        def refused():
            # Positive control: the real scan refuses to resume while its stopped worker still runs.
            with self.assertRaisesRegex(ValueError, 'already running'):
                self.inventory.launch('Audiobooks', resume=True)
        value, answer = self.cancel_while_stopping(entered, meanwhile=refused)
        self.assertEqual(answer['update']['outcome']['resume_problems'], [])
        finish_scan(self.inventory)
        self.assertEqual(self.inventory.status('Audiobooks')['state'], 'completed', 'the scan went on to its end')
        self.assertEqual(len(self.reads), 2, 'the stopped file was read again')

    def test_background_lookups_start_again_once_they_have_stopped(self):
        import gap_fill, series_backfill
        entered, passes = threading.Event(), []
        def lookups(worker):
            def run_pass():
                passes.append(worker)
                if passes.count(worker) == 1:
                    entered.set()
                    self.assertTrue(wait_until(worker.stop.is_set, 10), 'the update stopped the lookups')
                    time.sleep(self.LAG)  # the request in flight answers
                    raise InterruptedError()
                wait_until(worker.stop.is_set, 10)
            return run_pass
        with patch.object(series_backfill, 'START_DELAY', 0), patch.object(gap_fill, 'START_DELAY', 0):
            for name, cls in (('series_backfill', series_backfill.SeriesBackfill), ('gap_fill', gap_fill.GapFill)):
                worker = cls(self.merge)
                worker.run_pass = lookups(worker)
                setattr(self.merge, name, worker)
            self.merge.series_backfill.start(); self.merge.gap_fill.start()
            self.assertTrue(wait_until(lambda: len(passes) == 2, 10))
            def skipped():
                # Positive control: while the old thread lives the real start returns without starting anything.
                for worker in (self.merge.series_backfill, self.merge.gap_fill):
                    thread = worker.thread
                    worker.start()
                    self.assertIs(worker.thread, thread)
            value, answer = self.cancel_while_stopping(entered, meanwhile=skipped)
            self.assertEqual(answer['update']['outcome']['resume_problems'], [])
            for worker in (self.merge.series_backfill, self.merge.gap_fill):
                self.assertTrue(wait_until(lambda: passes.count(worker) == 2, 10), 'a new pass started')
                self.assertTrue(worker.thread.is_alive())
                self.assertFalse(worker.stop.is_set())

    def test_a_new_engine_leaves_the_queue_the_scan_and_automatic_processing_stopped(self):
        # Judy 12.4, offer 2: when the engine ends and the update does not install, the shell starts a new engine and names
        # what stays stopped. Checked here on the real classes: a new engine (MergeService, Inventory, AutomaticProcessing
        # on the same catalog) starts none of the three by itself; the lookups start with every engine.
        import contextlib
        from merge_service import MergeService
        from scanner import Inventory, connect
        import uuid
        from encoding_policy import PROFILE
        self.merge.jobs.enqueue({'job_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1, 'sources': [{'sha256': 'a' * 64, 'fingerprint': {}}],
                                 'metadata': {}, 'destination': 'fixture', 'profile': PROFILE, 'evidence': {}, 'cover': {}})
        self.slow_read = True
        self.inventory.launch('Audiobooks')
        self.assertTrue(wait_until(lambda: self.reads, 10))
        close_scan(self.inventory)
        self.assertEqual(self.inventory.status('Audiobooks')['state'], 'stopped', 'positive control: a stopped scan')
        with connect(self.inventory.database) as db:
            db.execute("INSERT INTO automatic_runs VALUES('run-1','Running','research','{}','','now','now',0)")
        stopped = {'automatic': True, 'converting': True, 'scanning': True}
        self.assertEqual(DesktopControl._stopped_kinds(stopped), ['automatic'], 'automatic processing starts the queue and its scan again itself')
        self.assertEqual(DesktopControl._stopped_kinds({'converting': True, 'scanning': True}), ['conversion', 'scan'])
        self.assertEqual(DesktopControl._stopped_kinds({}), [])
        base = Path(self.temp.name)
        inventory = Inventory(self.inventory.database, self.inventory.roots, self.read, output_root=str(base / 'sorted'))
        merge = MergeService(inventory, base / 'cache')
        try:
            automatic = merge.automatic
            merge.start_retention(contextlib.nullcontext)
            self.assertIsNone(merge.jobs._thread, 'the queue waits for Resume audiobook jobs')
            self.assertEqual(merge.jobs.status()['state'], 'Paused')
            self.assertIsNone(inventory.worker); self.assertEqual(inventory.status('Audiobooks')['state'], 'stopped', 'the scan waits for Resume scanning')
            self.assertEqual(automatic.status()['state'], 'Paused', 'automatic processing waits for Start')
            self.assertTrue(merge.series_backfill.thread.is_alive() and merge.gap_fill.thread.is_alive(), 'the lookups start by themselves')
        finally:
            merge.close()

    def test_the_update_answer_says_what_it_stops_that_a_new_engine_leaves_stopped(self):
        server, _ = engine(converting=True, scanning=True, stubborn=True)
        value = control(server)
        self.assertEqual(value.prepare_update()['update']['stopped'], ['conversion', 'scan'])
        value.cancel_update()
        server, _ = engine(automatic=True, converting=True)
        value = control(server)
        self.assertEqual(value.prepare_update()['update']['stopped'], ['automatic'])
        finish(value)

    def test_work_still_stopping_at_the_bound_is_named_never_as_before(self):
        jobs = self.merge.jobs
        entered, release = threading.Event(), threading.Event()
        def postprocess(job_id):
            entered.set(); release.wait(10)
            raise InterruptedError()
        jobs.pending_postprocessing, jobs.postprocessing = (lambda: ['fixture-job']), postprocess
        self.addCleanup(release.set)
        self.merge.resume(recheck=False)
        _, answer = self.cancel_while_stopping(entered, control(self.server, resume=0.3))
        problems = answer['update']['outcome']['resume_problems']
        self.assertEqual([(p['kind'], p['cause']) for p in problems], [('conversion', 'still_stopping')])
        release.set()


def wait_until(check, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.02)
    return bool(check())


class RouteTests(unittest.TestCase):
    def call(self, server, path):
        cls = handler_class(Handler, TOKEN)
        h = cls.__new__(cls); h.server = server; h.path = path
        h.headers = Message(); h.headers['Host'] = '127.0.0.1:5211'; h.headers['X-Books-Desktop'] = TOKEN
        h.headers['Content-Type'] = 'application/json'; h.headers['Content-Length'] = '2'; h.rfile = io.BytesIO(b'{}')
        h.result = None
        h.response = lambda status, value, content_type='application/json': setattr(h, 'result', (status, value))
        h.do_POST()
        return h.result

    def test_the_cancel_route_answers_and_says_when_it_is_too_late(self):
        server, _ = engine()
        server.server_port = 5211; server.token = 'page-token'; server.origins = {'http://127.0.0.1:5211'}
        server.desktop = SimpleNamespace(cancel_update=Mock(return_value={'phase': 'running'}))
        self.assertEqual(self.call(server, '/api/desktop/update-cancel'), (200, {'phase': 'running'}))
        server.desktop.cancel_update.side_effect = UpdateStarted('started')
        status, value = self.call(server, '/api/desktop/update-cancel')
        self.assertEqual((status, value['code']), (409, 'started'))


if __name__ == '__main__':
    unittest.main()
