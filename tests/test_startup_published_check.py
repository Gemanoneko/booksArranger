"""Routine checks of published books never block health, Pause, Quit or Start; their guarantees hold."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from audio_jobs import AudioJobs
from encoding_policy import PROFILE
import web_server

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'startup-published-check-tests'
AREA.mkdir(parents=True, exist_ok=True)


def manifest():
    return {'job_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
            'sources': [{'sha256': 'a' * 64, 'fingerprint': {}}], 'metadata': {}, 'destination': 'fixture',
            'profile': PROFILE, 'evidence': {}, 'cover': {}}


def record(job_id):
    return {'job_id': job_id, 'final_path': 'fixture.m4b', 'owned_temp': 'fixture.partial',
            'sha256': 'b' * 64, 'size': 1, 'validation': {'passed': True}}


class StartupPublishedCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.db = Path(self.temp.name) / 'db.sqlite3'
        seed = AudioJobs(self.db, None, lambda m: True, lambda r: True)
        self.completed, self.publishing, self.running = manifest(), manifest(), manifest()
        for item in (self.completed, self.publishing, self.running):
            seed.enqueue(item)
        seed._update(self.completed['job_id'], state='completed', stage='completed', output=json.dumps(record(self.completed['job_id'])))
        seed._update(self.publishing['job_id'], state='running', stage='publishing',
                     journal=json.dumps({'attempt_id': 'x', 'history': [], 'publication_intent': record(self.publishing['job_id'])}))
        seed._update(self.running['job_id'], state='running', stage='creating')
        seed.close()

    def tearDown(self):
        self.temp.cleanup()

    def states(self, queue):
        return {job['job_id']: (job['state'], job['reason']) for job in queue.status()['jobs']}

    def test_construction_settles_crashed_rows_without_hashing_published_books(self):
        checked = []
        queue = AudioJobs(self.db, None, lambda m: True, lambda r: checked.append(r['job_id']) or True)
        # Only the crash-interrupted publication is verified synchronously; the published book is not read.
        self.assertEqual(checked, [self.publishing['job_id']])
        states = self.states(queue)
        self.assertEqual(states[self.publishing['job_id']][0], 'completed')
        self.assertEqual(states[self.running['job_id']], ('pending', 'Interrupted book restarts on explicit resume'))
        self.assertEqual(states[self.completed['job_id']][0], 'completed')
        queue.close()

    def test_deferred_check_flags_a_changed_published_book_exactly_like_startup_did(self):
        valid = {self.publishing['job_id']}
        queue = AudioJobs(self.db, None, lambda m: True, lambda r: r['job_id'] in valid)
        queue.start_published_check(); queue._verifier.join(5)
        self.assertFalse(queue._verifier.is_alive())
        self.assertEqual(self.states(queue)[self.completed['job_id']],
                         ('needs attention', 'Recorded output is missing, changed, or failed validation'))
        queue.start_published_check()  # once per process
        self.assertFalse(queue._verifier.is_alive())
        queue.close()

    def test_deferred_check_never_writes_after_close(self):
        entered, release = threading.Event(), threading.Event()

        def slow(r):
            if r['job_id'] == self.completed['job_id']:
                entered.set(); release.wait(5)
                return False
            return True
        queue = AudioJobs(self.db, None, lambda m: True, slow)
        queue.start_published_check()
        self.assertTrue(entered.wait(5))
        queue.close(timeout=0.2)  # bounded: a book still being hashed never blocks Quit
        release.set(); queue._verifier.join(5)
        self.assertEqual(self.states(queue)[self.completed['job_id']][0], 'completed')

    def test_resume_takes_over_and_the_deferred_check_never_overwrites_it(self):
        entered, release = threading.Event(), threading.Event()
        calls = []

        def validator(r):
            calls.append(threading.current_thread().name)
            if threading.current_thread().name == 'BooksArrangerPublishedCheck':
                entered.set(); release.wait(5)
                return False  # stale verdict that must not land after resume
            return True
        queue = AudioJobs(self.db, None, lambda m: True, validator)
        queue.start_published_check()
        self.assertTrue(entered.wait(5))
        with patch.object(queue, '_work', lambda: None):
            queue.resume()  # verifies every published book itself, under the queue lock
        self.assertTrue(queue._verify_stop.is_set())
        release.set(); queue._verifier.join(5)
        self.assertEqual(self.states(queue)[self.completed['job_id']][0], 'completed')
        self.assertIn('MainThread', calls)
        queue.close()

    def test_a_row_changed_after_reading_is_never_overwritten(self):
        entered, release = threading.Event(), threading.Event()

        def slow(r):
            if r['job_id'] == self.completed['job_id']:
                entered.set(); release.wait(5)
                return False
            return True
        queue = AudioJobs(self.db, None, lambda m: True, slow)
        queue.start_published_check()
        self.assertTrue(entered.wait(5))
        queue._update(self.completed['job_id'], reason='changed by another owner')
        release.set(); queue._verifier.join(5)
        self.assertEqual(self.states(queue)[self.completed['job_id']], ('completed', 'changed by another owner'))
        queue.close()


class ServerWiringTests(unittest.TestCase):
    def test_server_starts_the_check_after_construction_and_health_is_immediate(self):
        started = threading.Event(); release = threading.Event()

        class FakeMerge:
            def __init__(self, inventory, cache):
                self.calls = []
            def start_retention(self, admission):
                self.calls.append('retention')
            def start_published_check(self):
                self.calls.append('published')
                threading.Thread(target=lambda: (started.set(), release.wait(5)), daemon=True).start()
            def close(self):
                self.calls.append('close')
        inventory = type('Inventory', (), {'database': str(AREA / 'unused.sqlite3')})()
        t = time.perf_counter()
        server = web_server.BrowserServer(('127.0.0.1', 0), inventory, FakeMerge)
        try:
            self.assertLess(time.perf_counter() - t, 2)
            self.assertEqual(server.merge.calls, ['retention', 'published'])
            self.assertTrue(started.wait(5))
            self.assertEqual(server.health()['application'], 'Books Arranger')
        finally:
            release.set(); server.server_close()


class StartCheckTests(unittest.TestCase):
    """Start (resume) re-checks published books without holding the queue lock; Pause and Quit win."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.db = Path(self.temp.name) / 'db.sqlite3'
        seed = AudioJobs(self.db, None, lambda m: True, lambda r: True)
        self.done, self.queued = manifest(), manifest()
        seed.enqueue(self.done); seed.enqueue(self.queued)
        seed._update(self.done['job_id'], state='completed', stage='completed', output=json.dumps(record(self.done['job_id'])))
        seed.close()

    def tearDown(self):
        self.temp.cleanup()

    def states(self, queue):
        return {job['job_id']: (job['state'], job['reason']) for job in queue.status()['jobs']}

    def blocking_queue(self):
        entered, release = threading.Event(), threading.Event()

        def current(r, stop, pace):
            entered.set()
            while not release.is_set():  # a long hash that honours its stop between blocks
                if stop is not None and stop.is_set():
                    raise InterruptedError('stopped')
                time.sleep(.01)
            return True
        queue = AudioJobs(self.db, None, lambda m: True, lambda r: True)
        queue.output_current = current
        return queue, entered, release

    def test_pause_during_the_start_check_answers_at_once_and_nothing_starts(self):
        queue, entered, release = self.blocking_queue()
        starter = threading.Thread(target=queue.resume); starter.start()
        self.assertTrue(entered.wait(5))
        t = time.perf_counter(); queue.pause()
        self.assertLess(time.perf_counter() - t, .5, 'Pause must not wait for the published-book check')
        starter.join(5); self.assertFalse(starter.is_alive())
        self.assertIsNone(queue._thread, 'Pause during the Start check wins; the worker never starts')
        self.assertEqual(queue.status()['state'], 'Paused')
        release.set(); queue.close()

    def test_quit_mid_start_check_is_honoured_within_seconds(self):
        queue, entered, release = self.blocking_queue()
        starter = threading.Thread(target=queue.resume); starter.start()
        self.assertTrue(entered.wait(5))
        t = time.perf_counter(); queue.drain(); queue.close(timeout=5)
        starter.join(5)
        self.assertLess(time.perf_counter() - t, 2)
        self.assertFalse(starter.is_alive()); self.assertIsNone(queue._thread)
        self.assertEqual(self.states(queue)[self.done['job_id']][0], 'completed', 'An interrupted check writes nothing')
        release.set()

    def test_start_still_rechecks_a_changed_book_before_any_new_work(self):
        order = []
        queue = AudioJobs(self.db, None, lambda m: True, lambda r: True)
        queue.output_current = lambda r, stop, pace: order.append(('checked', r['job_id'])) or False
        with patch.object(queue, '_work', lambda: order.append(('worker',))):
            queue.resume(); queue._thread.join(5)
        self.assertEqual(order, [('checked', self.done['job_id']), ('worker',)])
        self.assertEqual(self.states(queue)[self.done['job_id']],
                         ('needs attention', 'Recorded output is missing, changed, or failed validation'))
        queue.close()


def published(root, name, data):
    from native_io import DirectoryBoundary
    path = Path(root) / name
    path.write_bytes(data)
    with DirectoryBoundary(Path(root), path.parent) as boundary:
        parent = [list(i) for i in boundary.identities]
    import hashlib
    return {'job_id': str(uuid.uuid4()), 'root': str(root), 'final_path': str(path), 'owned_temp': str(path) + '.partial',
            'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data), 'parent_identity': parent,
            'validation': {'passed': True, 'profile': PROFILE}}


class RoutineIdentityTests(unittest.TestCase):
    """The routine check skips the full hash only while the file identity equals its last full verification."""

    def setUp(self):
        import sqlite3
        from types import SimpleNamespace
        import merge_service
        self.ms = merge_service
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        root = Path(self.temp.name) / 'Audiobooks'; root.mkdir()
        self.db = Path(self.temp.name) / 'catalog.sqlite3'
        import contextlib
        with contextlib.closing(sqlite3.connect(self.db)) as db, db:
            db.execute('CREATE TABLE verified_outputs(path TEXT, sha256 TEXT, job_id TEXT, identity TEXT, verified TEXT, PRIMARY KEY(path, sha256))')
        self.service = merge_service.MergeService.__new__(merge_service.MergeService)
        self.service.inventory = SimpleNamespace(database=str(self.db), roots={'Audiobooks': str(root)})
        self.service._validated_outputs = {}
        self.record = published(root, 'Book.m4b', b'x' * (3 * 1024 * 1024 + 7))
        self.hashes = []
        real = merge_service.verify_digest
        self.patcher = patch.object(merge_service, 'verify_digest', lambda *a, **k: self.hashes.append(a[0]) or real(*a, **k))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop(); self.temp.cleanup()

    def test_first_check_hashes_then_unchanged_identity_skips_the_hash(self):
        self.assertTrue(self.service._output_current(dict(self.record)))
        self.assertEqual(len(self.hashes), 1)
        self.assertTrue(self.service._output_current(dict(self.record)))
        self.assertEqual(len(self.hashes), 1, 'unchanged identity must not re-read the book')
        self.assertIn(self.record['job_id'], self.service._validated_outputs)

    def test_changed_file_is_hashed_in_full_and_fails(self):
        self.assertTrue(self.service._output_current(dict(self.record)))
        path = Path(self.record['final_path'])
        time.sleep(.05); path.write_bytes(b'y' * self.record['size'])  # same size, new bytes and time
        self.assertFalse(self.service._output_current(dict(self.record)))
        self.assertEqual(len(self.hashes), 2)

    def test_removal_paths_keep_the_full_hash(self):
        self.assertTrue(self.service._output_current(dict(self.record)))
        self.assertTrue(self.service._output_valid(dict(self.record)))
        self.assertEqual(len(self.hashes), 2, '_output_valid always reads the whole book')

    def test_a_stop_is_raised_never_reported_invalid(self):
        stop = threading.Event(); stop.set()
        with self.assertRaises(InterruptedError):
            self.service._output_current(dict(self.record), stop)
        self.assertEqual(self.service._known_identity(self.record['final_path'], self.record['sha256']), None)


class PacingTests(unittest.TestCase):
    def test_shared_pacer_holds_the_rate_and_stops(self):
        from merge_service import Pacer
        clock = [0.0]
        pacer = Pacer(1000, clock=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s))
        for _ in range(10):
            pacer(500)
        self.assertAlmostEqual(clock[0], 4.5, places=6)  # 5000 bytes at 1000 B/s; the first block is free
        stop = threading.Event(); stop.set()
        with self.assertRaises(InterruptedError):
            pacer(500, stop)

    def test_verify_digest_matches_and_stops_between_blocks(self):
        import hashlib
        from merge_service import verify_digest
        with tempfile.TemporaryDirectory(dir=AREA) as temp:
            path = Path(temp) / 'b.bin'; data = b'z' * (2 * 1024 * 1024 + 3); path.write_bytes(data)
            self.assertEqual(verify_digest(path), hashlib.sha256(data).hexdigest())
            stop = threading.Event(); stop.set()
            with self.assertRaises(InterruptedError):
                verify_digest(path, stop)


class DesktopStatusTests(unittest.TestCase):
    def test_status_answers_within_bound_while_state_is_slow(self):
        from types import SimpleNamespace
        from desktop_backend import DesktopControl
        release = threading.Event()
        server = SimpleNamespace(state=lambda *a, **k: release.wait(10) or {}, closing=False, merge_admissions=0,
                                 merge=SimpleNamespace(), scan_active=lambda: False)
        control = DesktopControl(server)
        t = time.perf_counter(); value = control.status()
        self.assertLess(time.perf_counter() - t, DesktopControl.STATUS_ANSWER + 1)
        self.assertEqual(value.get('status'), 'unavailable'); self.assertFalse(value['idle']); self.assertEqual(value['phase'], 'running')
        release.set()


class CurrentAudiobookViewTests(unittest.TestCase):
    def view(self, verified):
        import contextlib
        from current_audiobook import CurrentAudiobooks
        with tempfile.TemporaryDirectory(dir=AREA) as temp:
            view = CurrentAudiobooks(temp, Path(temp) / 'repairs', None, verified=lambda r: verified)
        record = {'final_path': 'x.m4b', 'sha256': 'c' * 64, 'size': 1, 'validation': {'tags': {}}}
        view.publication = lambda jobs, candidate: {'id': 'p', 'kind': 'conversion', 'record': record, 'cover': None}

        @contextlib.contextmanager
        def protected(publication, display=False):  # 0.22.1: describe() asks for the display lookup
            yield None, 'key-1'
        view.protected = protected
        return view

    def test_unchanged_identity_is_verified_without_re_reading(self):
        view = self.view(True)
        self.assertEqual(view.describe([], 'c')['state'], 'verified')
        self.assertIsNone(view._thread, 'no background hash was queued')

    def test_unknown_identity_still_queues_the_full_check(self):
        view = self.view(False)
        self.assertEqual(view.describe([], 'c')['state'], 'verifying')
        view.close()


if __name__ == '__main__':
    unittest.main()
