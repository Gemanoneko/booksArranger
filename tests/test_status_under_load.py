"""v0.16.8: status and controls under conversion load, and the engine's exit after Quit.

Live (v0.16.7, a book converting): half of the status polls answered 503 after 4 s, the page then called
the server unavailable and refused Retry; a Retry press computed a full status and re-read the book's
sources before answering. These tests pin the fixes.
"""
import json
import sqlite3
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import merge_service
from desktop_backend import DesktopControl
from merge_service import MergeService, SharedSnapshot, StatusUnavailable
from test_blocked_retry import Queue

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'status-under-load-tests'
AREA.mkdir(parents=True, exist_ok=True)
ALIVE = SimpleNamespace(is_alive=lambda: True)


class StaleWhileComputingTests(unittest.TestCase):
    def test_a_poll_gets_the_last_answer_while_a_new_one_computes(self):
        shared = SharedSnapshot(wait=4.0); gate = threading.Event(); calls = []
        def compute():
            calls.append(1)
            if len(calls) > 1: gate.wait(10)
            return {'n': len(calls)}
        self.assertEqual(shared.get(compute, 0.0), {'n': 1})
        started = time.monotonic()
        self.assertEqual(shared.get(compute, 0.0), {'n': 1}, 'the last good answer, not "still updating"')
        self.assertLess(time.monotonic() - started, 2.0, 'within the short stale bound, not the 4 s one')
        self.assertEqual(shared.get(compute, 0.0), {'n': 1}); self.assertEqual(len(calls), 2, 'one computation at a time')
        gate.set(); time.sleep(.2)
        self.assertEqual(shared.get(compute, 10.0), {'n': 2})

    def test_after_a_control_a_poll_waits_for_the_fresh_answer_then_never_503s(self):
        shared = SharedSnapshot(wait=0.3); gate = threading.Event(); calls = []
        def compute():
            calls.append(1)
            if len(calls) > 1: gate.wait(10)
            return {'n': len(calls)}
        shared.get(compute, 0.0); shared.invalidate()
        started = time.monotonic()
        self.assertEqual(shared.get(compute, 0.0), {'n': 1}, 'the pre-control answer after the full wait')
        self.assertGreaterEqual(time.monotonic() - started, 0.25)
        gate.set()

    def test_only_the_very_first_answer_can_be_unavailable(self):
        shared = SharedSnapshot(wait=0.2); gate = threading.Event()
        with self.assertRaises(StatusUnavailable): shared.get(lambda: gate.wait(10) and {'n': 1}, 1.0)
        gate.set()


class CatalogFactsTests(unittest.TestCase):
    """Cleanup status and the Ready totals are reused per catalog version while a book converts."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'catalog.sqlite3'
        connection = sqlite3.connect(self.db); connection.execute('CREATE TABLE t(x)'); connection.commit(); connection.close()
        s = MergeService.__new__(MergeService); s.inventory = SimpleNamespace(database=str(self.db), worker=None)
        s.jobs = SimpleNamespace(_thread=ALIVE, _check_progress=None)  # a book is converting
        s.cleanup = SimpleNamespace(thread=None, current=None); s._post_current = None; s.draining = False
        self.s = s; self.calls = 0
        s._catalog_version(True); self.addCleanup(lambda: s.__dict__.pop('_monitor').close())

    def compute(self):
        self.calls += 1; return {'calls': self.calls}

    def commit(self):
        connection = sqlite3.connect(self.db)
        with connection: connection.execute('INSERT INTO t VALUES(1)')
        connection.close()

    def test_reused_while_converting_recomputed_after_a_commit_or_during_cleanup(self):
        s = self.s
        self.assertIsNone(s._quiet_token(), 'converting: never "quiet"')
        self.assertEqual(s._catalog_cached('cleanups', self.compute), {'calls': 1})
        self.assertEqual(s._catalog_cached('cleanups', self.compute), {'calls': 1}, 'a converting book changes no cleanup fact')
        self.commit(); self.assertEqual(s._catalog_cached('cleanups', self.compute), {'calls': 2}, 'a commit')
        s.cleanup.current = 'cleanup-1'
        s._catalog_cached('cleanups', self.compute); s._catalog_cached('cleanups', self.compute); self.assertEqual(self.calls, 4, 'cleanup work: fresh every time')
        s.cleanup.current = None; s.invalidate_status = MergeService.invalidate_status.__get__(s)
        s._catalog_cached('cleanups', self.compute); s.invalidate_status(); s._catalog_cached('cleanups', self.compute); self.assertEqual(self.calls, 5, 'a control')
        with patch.object(merge_service, 'CATALOG_MAX_AGE', 0.0): s._catalog_cached('cleanups', self.compute)
        self.assertEqual(self.calls, 6, 'the age bound')


class FastPressTests(unittest.TestCase):
    """A Retry press answers at once: no operation lock, no source re-read, no status, queued next."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.q = Queue(self.temp.name)
        self.addCleanup(self.temp.cleanup); self.addCleanup(self.q.jobs.close); self.addCleanup(self.q.release.set)

    def service(self):
        s = MergeService.__new__(MergeService); s.jobs = self.q.jobs; s.working = self.q.life; s.operation_lock = threading.RLock()
        s.inventory = SimpleNamespace(worker=None, group_lock=threading.RLock()); s.reviews = SimpleNamespace(lock=threading.RLock())
        s.cleanup = SimpleNamespace(status=lambda job_id=None: None); s.draining = False
        s.resume = Mock(side_effect=AssertionError('the press never waits for Start')); s._resume_later = Mock()
        s.state = Mock(side_effect=AssertionError('the press computes no status'))
        return s

    def test_press_skips_the_source_re_read_and_queues_the_same_job_next(self):
        job_id, _, _ = self.q.blocked(leftover=False); s = self.service(); manifest = json.loads(self.q.row(job_id)['manifest'])
        self.q.guard = Mock(side_effect=AssertionError('E10 runs in the worker, not at the press'))
        held = threading.Event(); release = threading.Event()
        def long_operation():
            with s.operation_lock: held.set(); release.wait(10)
        threading.Thread(target=long_operation, daemon=True).start(); self.assertTrue(held.wait(5))
        try:
            started = time.monotonic(); result = s.retry_blocked_job('Audiobooks', manifest['candidate_id'], 1, job_id)
            self.assertLess(time.monotonic() - started, 2.0, 'a long operation never delays the press')
        finally: release.set()
        self.assertEqual((result['requeued'], result['queued_next'], result['position']), (True, True, 1))
        self.assertEqual(self.q.row(job_id)['state'], 'pending'); s._resume_later.assert_called_once_with()
        import m4b_readmission
        self.assertEqual(m4b_readmission.next_job(self.q.jobs._db, Mock(side_effect=AssertionError('no admission')), time.time()), job_id,
                         'the worker runs it right after the current book')


class ExitBoundTests(unittest.TestCase):
    def test_a_completed_shutdown_ends_the_process_if_something_lingers(self):
        ended = threading.Event(); codes = []
        control = DesktopControl(SimpleNamespace(), exit_bound=0.05, exit_process=lambda code: (codes.append(code), ended.set()))
        control._bound_exit(); self.assertTrue(ended.wait(5)); self.assertEqual(codes, [0])

    def test_off_unless_the_desktop_engine_arms_it(self):
        control = DesktopControl(SimpleNamespace(), exit_process=Mock(side_effect=AssertionError('never in tests')))
        self.assertIsNone(control._bound_exit())
        self.assertGreater(DesktopControl.EXIT_AFTER, 5, 'long enough for a normal exit')


if __name__ == '__main__':
    unittest.main()
