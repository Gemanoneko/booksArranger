"""Status polling cannot pile up: one shared state computation, cheap per-row idle checks."""
import json
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import replacement_jobs
from audio_jobs import AudioJobs
import merge_service
from desktop_backend import DesktopControl, handler_class
from merge_service import MergeService, SharedSnapshot, StatusUnavailable
from replacement_jobs import Replacements
from scan_wait import finish_thread
from web_server import BrowserServer, Handler

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'status-snapshot-tests'
AREA.mkdir(parents=True, exist_ok=True)


class Clock:
    def __init__(self): self.value = 100.0
    def __call__(self): return self.value


class SharedSnapshotTests(unittest.TestCase):
    def test_concurrent_callers_share_one_computation_and_get_private_copies(self):
        calls = []
        gate = threading.Event()
        def compute():
            calls.append(1); gate.wait(5); return {'state': 'Paused', 'nested': {'queued': 3}}
        shared = SharedSnapshot()
        results = []
        threads = [threading.Thread(target=lambda: results.append(shared.get(compute, 1.0))) for _ in range(24)]
        for t in threads: t.start()
        time.sleep(.3)  # every caller has arrived while the first computation is still running
        gate.set()
        for t in threads: t.join(5)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(results), 24)
        self.assertTrue(all(r == {'state': 'Paused', 'nested': {'queued': 3}} for r in results))
        results[0]['nested']['queued'] = 99
        self.assertEqual(results[1]['nested']['queued'], 3)

    def test_finished_answer_is_reused_only_for_max_age(self):
        clock = Clock(); shared = SharedSnapshot(clock); compute = Mock(side_effect=[{'n': 1}, {'n': 2}])
        self.assertEqual(shared.get(compute, 1.0), {'n': 1})
        clock.value += 0.9
        self.assertEqual(shared.get(compute, 1.0), {'n': 1})
        clock.value += 0.2
        self.assertEqual(shared.get(compute, 1.0), {'n': 2})
        self.assertEqual(compute.call_count, 2)

    def test_failure_reaches_every_waiter_and_is_never_cached(self):
        gate = threading.Event(); calls = []
        def failing():
            calls.append(1); gate.wait(5); raise RuntimeError('catalog busy')
        shared = SharedSnapshot(); errors = []
        def call():
            try: shared.get(failing, 1.0)
            except RuntimeError as error: errors.append(str(error))
        threads = [threading.Thread(target=call) for _ in range(6)]
        for t in threads: t.start()
        time.sleep(.2); gate.set()
        for t in threads: t.join(5)
        self.assertEqual(errors, ['catalog busy'] * 6)
        self.assertEqual(len(calls), 1)
        self.assertEqual(shared.get(lambda: {'ok': True}, 1.0), {'ok': True})

    def test_answer_age_counts_from_the_start_of_its_computation(self):
        # M1: a computation that took 0.8 s is 1.1 s old 0.3 s after it finished.
        clock = Clock(); shared = SharedSnapshot(clock); values = iter([{'n': 1}, {'n': 2}]); calls = []
        def slow():
            calls.append(1); clock.value += 0.8; return next(values)
        self.assertEqual(shared.get(slow, 1.0), {'n': 1})
        clock.value += 0.3
        self.assertEqual(shared.get(slow, 1.0), {'n': 2})
        self.assertEqual(len(calls), 2)

    def test_invalidate_detaches_a_running_computation_so_it_never_refills_or_is_joined(self):
        # M1: a computation that started before a control can neither be cached nor joined after it.
        clock = Clock(); shared = SharedSnapshot(clock)
        entered = {1: threading.Event(), 2: threading.Event()}; gates = {1: threading.Event(), 2: threading.Event()}
        counter = iter([1, 2, 3]); calls = []
        def compute():
            n = next(counter); calls.append(n); entered[n].set(); gates[n].wait(5); return {'n': n}
        results = {}
        before = threading.Thread(target=lambda: results.__setitem__('before', shared.get(compute, 1.0)))
        before.start(); self.assertTrue(entered[1].wait(5))
        shared.invalidate()
        after = threading.Thread(target=lambda: results.__setitem__('after', shared.get(compute, 1.0)))
        after.start()
        self.assertTrue(entered[2].wait(5), 'a reader after invalidate must start its own computation')
        gates[2].set(); after.join(5)
        gates[1].set(); before.join(5)  # the pre-control computation finishes last
        self.assertEqual(results, {'before': {'n': 1}, 'after': {'n': 2}})
        self.assertEqual(shared.get(compute, 1.0), {'n': 2}, 'the late pre-control answer must not replace the newer one')
        self.assertEqual(calls, [1, 2])

    def test_a_waiter_gives_up_after_its_bound_without_a_second_computation(self):
        # m3: a hung computation parks only its own thread; every other poll answers within the bound.
        clock = Clock(); shared = SharedSnapshot(clock, wait=0.2)
        entered = threading.Event(); gate = threading.Event(); calls = []
        def hung():
            calls.append(1); entered.set(); gate.wait(10); return {'state': 'Paused'}
        owner = threading.Thread(target=lambda: shared.get(hung, 1.0)); owner.start()
        self.assertTrue(entered.wait(5))
        for _ in range(3):
            started = time.monotonic()
            with self.assertRaises(StatusUnavailable): shared.get(hung, 1.0)
            self.assertLess(time.monotonic() - started, 2.0)
        self.assertEqual(len(calls), 1)
        gate.set(); owner.join(5)
        self.assertEqual(shared.get(hung, 1.0), {'state': 'Paused'}); self.assertEqual(len(calls), 1)
        self.assertLess(merge_service.STATUS_WAIT, 5.0, 'the bound must stay below the desktop shell request timeout')


class MergeStatusTests(unittest.TestCase):
    def test_status_snapshot_runs_one_state_for_a_burst_of_pollers(self):
        merge = MergeService.__new__(MergeService)
        def slow_state():
            time.sleep(.4); return {'state': 'Paused', 'queued': 194}
        merge.state = Mock(side_effect=slow_state)
        results = []
        threads = [threading.Thread(target=lambda: results.append(merge.status_snapshot())) for _ in range(40)]
        for t in threads: t.start()
        for t in threads: t.join(10)
        self.assertEqual(merge.state.call_count, 1)
        self.assertEqual(results, [{'state': 'Paused', 'queued': 194}] * 40)

    def recovery_merge(self, unfinished):
        merge = MergeService.__new__(MergeService)
        merge.inventory = SimpleNamespace(worker=None); merge._retention_stop = threading.Event()
        merge._post_current = None
        merge.jobs = SimpleNamespace(_thread=None, has_unfinished=Mock(return_value=unfinished), status=Mock(side_effect=AssertionError('full job load')))
        merge.cleanup = SimpleNamespace(thread=None, current=None, _rows=Mock(return_value=[]))
        return merge

    def test_recovery_idle_never_waits_for_queued_or_running_books(self):
        # v0.16.8 (Sergei, 2026-10-18): a verified book's copies go at once; queued or converting work no
        # longer holds them, and the check reads no job at all. Only a source cleanup in progress waits.
        busy = self.recovery_merge(True); busy.jobs._thread = SimpleNamespace(is_alive=lambda: True)
        busy._recovery_idle()
        busy.jobs.status.assert_not_called(); busy.jobs.has_unfinished.assert_not_called()
        busy.cleanup.current = 'cleanup-1'
        with self.assertRaisesRegex(ValueError, 'source cleanup'): busy._recovery_idle()

    def test_has_unfinished_matches_the_full_status_scan(self):
        with tempfile.TemporaryDirectory(dir=AREA) as folder:
            db_path = Path(folder) / 'catalog.sqlite3'
            jobs = AudioJobs(db_path, Mock(), Mock(), Mock())
            try:
                def insert(job_id, state):
                    with sqlite3.connect(db_path) as db:
                        db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)', (job_id, '{}', '', state, 'queued', None, '{}', None, '', '2026-10-16T00:00:00+00:00', '2026-10-16T00:00:00+00:00'))
                    db.close()
                def full_scan():
                    return any(j['state'] in ('pending', 'running') for j in jobs.status()['jobs'])
                self.assertEqual(jobs.has_unfinished(), full_scan()); self.assertFalse(jobs.has_unfinished())
                insert('a', 'completed'); insert('b', 'needs attention')
                self.assertEqual(jobs.has_unfinished(), full_scan()); self.assertFalse(jobs.has_unfinished())
                insert('c', 'running')
                self.assertEqual(jobs.has_unfinished(), full_scan()); self.assertTrue(jobs.has_unfinished())
                with sqlite3.connect(db_path) as db: db.execute("UPDATE audio_jobs SET state='pending' WHERE job_id='c'")
                db.close()
                self.assertEqual(jobs.has_unfinished(), full_scan()); self.assertTrue(jobs.has_unfinished())
            finally:
                jobs.close()

    def test_one_state_computation_reads_replacement_relations_once(self):
        merge = MergeService.__new__(MergeService)
        private = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(private.cleanup)
        merge.jobs = AudioJobs(Path(private.name) / 'bulk-status.sqlite3', None, lambda m: True, lambda r: True)
        self.addCleanup(merge.jobs.close)
        merge.replacements = SimpleNamespace(snapshot=Mock())
        entered = []
        class Context:
            def __enter__(self): entered.append('in')
            def __exit__(self, *a): entered.append('out')
        merge.replacements.snapshot.return_value = Context()
        merge._state = Mock(return_value={'state': 'Paused'})
        self.assertEqual(merge.state(), {'state': 'Paused'})
        self.assertEqual(entered, ['in', 'out'])


class ReplacementSnapshotTests(unittest.TestCase):
    def test_snapshot_reads_relations_once_per_computation_on_its_own_thread(self):
        with tempfile.TemporaryDirectory(dir=AREA) as folder:
            db_path = str(Path(folder) / 'catalog.sqlite3')
            store = Replacements(db_path)
            real_connect = replacement_jobs.connect
            opened = []
            def counting(path, *args, **kwargs):
                opened.append(path); return real_connect(path, *args, **kwargs)
            with patch.object(replacement_jobs, 'connect', side_effect=counting):
                with store.snapshot():
                    first = store.rows(); first.append({'mutated': True})
                    for _ in range(50): store.get(new_job='missing')
                    other = []
                    worker = threading.Thread(target=lambda: other.append(len(opened)) or store.rows() or other.append(len(opened)))
                    worker.start(); finish_thread(worker, 'The other reader')
                    self.assertEqual(store.rows(), [])
                    with store.snapshot(): self.assertEqual(store.rows(), [])
                self.assertEqual(other[1] - other[0], 1)  # another thread still reads fresh
                reads_inside = opened.count(db_path) - 1
                store.rows()
            self.assertEqual(reads_inside, 1)
            self.assertEqual(opened.count(db_path), 3)


def full_state(converting=False):
    return {'audiobook_jobs': {'state': 'Running' if converting else 'Paused', 'current_title': 'Fixture', 'stage': 'creating', 'queued': 194, 'cleanup_active': False},
            'automatic_processing': {'state': 'Paused'}, 'active_library': None, 'stopping': False, 'recovery_active': False}


class DesktopStatusTests(unittest.TestCase):
    def server(self, state):
        lock = threading.Lock()
        merge = SimpleNamespace(state=Mock(side_effect=AssertionError('second full state')), status_snapshot=Mock(side_effect=AssertionError('second snapshot')),
                                automatic=SimpleNamespace(status=Mock(side_effect=AssertionError('second automatic status'))))
        return SimpleNamespace(merge=merge, state=state, closing=False, merge_admissions=0, control_lock=lock,
                               control_condition=threading.Condition(lock), scan_active=Mock(return_value=False))

    def test_one_shared_state_feeds_busy_and_idle(self):
        server = self.server(Mock(return_value=full_state()))
        value = DesktopControl(server).status()
        server.state.assert_called_once_with('Audiobooks', cached=True)
        self.assertEqual(value['busy'], {'converting': False, 'current_title': 'Fixture', 'stage': 'creating', 'queued': 194, 'automatic': 'Paused', 'scanning': False, 'approvals': 0})  # m-1: approvals in flight (f7395f4)
        self.assertTrue(value['idle'])

    def test_converting_snapshot_reports_busy_and_not_idle(self):
        server = self.server(Mock(return_value=full_state(converting=True)))
        value = DesktopControl(server).status()
        self.assertTrue(value['busy']['converting']); self.assertFalse(value['idle'])
        server.state.assert_called_once()

    def test_unavailable_state_is_not_idle_and_never_raises(self):
        server = self.server(Mock(side_effect=RuntimeError('catalog busy')))
        server.merge.status_snapshot = Mock(return_value={'state': 'Paused', 'queued': 1})
        server.merge.automatic.status = Mock(return_value={'state': 'Paused'})
        value = DesktopControl(server).status()
        self.assertFalse(value['idle']); self.assertEqual(value['busy']['queued'], 1)
        server.merge.status_snapshot.assert_called_once_with()

    def test_status_unavailable_answers_at_once_and_keeps_the_phase(self):
        # m3: no second wait; phase stays readable so Quit and its watcher keep working.
        server = self.server(Mock(side_effect=StatusUnavailable('Status computation is still running')))
        control = DesktopControl(server)
        value = control.status()
        self.assertEqual(value['phase'], 'running'); self.assertIsNone(value['busy'])
        self.assertFalse(value['idle']); self.assertEqual(value['status'], 'unavailable')
        server.state.assert_called_once_with('Audiobooks', cached=True)
        server.merge.status_snapshot.assert_not_called(); server.merge.state.assert_not_called()
        control.phase, control.error = 'blocked', 'Worker did not reach its checkpoint'
        value = control.status()
        self.assertEqual((value['phase'], value['error']), ('blocked', 'Worker did not reach its checkpoint'))


class BrowserStateTests(unittest.TestCase):
    def server(self):
        server = BrowserServer.__new__(BrowserServer)
        server.inventory = SimpleNamespace(worker=None, roots={'Audiobooks': 'A'}, status=Mock(return_value={'count': 1}), stop_event=threading.Event())
        server.merge = SimpleNamespace(state=Mock(return_value={'state': 'fresh'}), status_snapshot=Mock(return_value={'state': 'shared'}),
                                       automatic=SimpleNamespace(status=Mock(return_value={'state': 'Paused'})))
        server.closing = False; server.active_library = None; server.loaded_version = '0'; server.instance = 'i'
        server.restart_context = False; server.recovery_operations = 0; server.server_port = 5299
        return server

    def test_polling_reads_share_the_snapshot_and_fences_stay_fresh(self):
        server = self.server()
        self.assertEqual(server.state('Audiobooks', cached=True)['audiobook_jobs'], {'state': 'shared'})
        server.merge.state.assert_not_called()
        self.assertEqual(server.state('Audiobooks')['audiobook_jobs'], {'state': 'fresh'})
        server.merge.status_snapshot.assert_called_once_with()

    def test_state_route_reports_unavailable_as_503(self):
        # m3: the page treats it like any failed poll and retries on its next poll.
        server = SimpleNamespace(inventory=SimpleNamespace(roots={'Audiobooks': 'A'}), state=Mock(side_effect=StatusUnavailable('still running')))
        replies = []
        h = reply_handler(Handler, server, '/api/state?library=Audiobooks', replies)
        h.do_GET()
        self.assertEqual(replies, [503])
        self.assertEqual(json.loads(h.wfile.write.call_args.args[0]), {'error': 'Status is still updating; retrying'})


def reply_handler(cls, server, path, events):
    h = cls.__new__(cls); h.server = server; h.path = path; h.close_connection = False
    h.send_response = Mock(side_effect=lambda status: events.append(status))
    h.send_header = Mock(); h.end_headers = Mock(); h.wfile = Mock()
    h.trusted = Mock(return_value=True)
    return h


class ControlInvalidationTests(unittest.TestCase):
    """M1: no poll after a control's reply can receive the snapshot computed before the control."""
    def server(self, events):
        server = BrowserServer.__new__(BrowserServer)
        server.inventory = SimpleNamespace(worker=None, roots={'Audiobooks': 'A'}, status=Mock(return_value={'count': 1}), stop_event=threading.Event(), stop=Mock())
        server.merge = MergeService.__new__(MergeService)
        server.merge.state = Mock(side_effect=[{'state': 'Running', 'n': n} for n in (1, 2, 3, 4)])
        real = server.merge.invalidate_status
        server.merge.invalidate_status = lambda: (events.append('invalidate'), real())
        lock = threading.Lock()
        server.control_lock = lock; server.control_condition = threading.Condition(lock)
        server.closing = False; server.active_library = 'Audiobooks'; server.scan_active = Mock(return_value=True)
        server.loaded_version = '0'; server.instance = 'i'; server.restart_context = False; server.recovery_operations = 0; server.server_port = 5299
        return server

    def poll(self, server):
        return server.state('Audiobooks', cached=True)['audiobook_jobs']['n']

    def test_a_control_drops_the_shared_answer_before_its_reply_is_sent(self):
        events = []; server = self.server(events)
        self.assertEqual(self.poll(server), 1); self.assertEqual(self.poll(server), 1)  # reused within 1 s
        h = reply_handler(Handler, server, '/api/scan/stop', events)
        h.body = Mock(return_value={'library': 'Audiobooks'})
        h.do_POST()
        server.inventory.stop.assert_called_once_with()
        self.assertEqual(events, ['invalidate', 200], 'invalidation must happen before the reply leaves')
        self.assertEqual(self.poll(server), 3, 'the poll after a control must not get the pre-control answer')

    def test_desktop_controls_also_drop_the_shared_answer_first(self):
        events = []; server = self.server(events)
        server.desktop = SimpleNamespace(quit=Mock(return_value={'phase': 'finishing'}))
        self.assertEqual(self.poll(server), 1)
        h = reply_handler(handler_class(Handler, 'a' * 64), server, '/api/desktop/quit', events)
        h.desktop_trusted = Mock(return_value=True); h.body = Mock(return_value={})
        h.do_POST()
        server.desktop.quit.assert_called_once_with()
        self.assertEqual(events, ['invalidate', 202])
        self.assertEqual(self.poll(server), 2)

    def test_untrusted_posts_and_reads_never_invalidate(self):
        events = []; server = self.server(events)
        self.assertEqual(self.poll(server), 1)
        h = reply_handler(Handler, server, '/api/scan/stop', events)
        h.trusted = Mock(side_effect=lambda token=False: h.fail(403, 'Missing or invalid local request token') or False)
        h.do_POST()
        h.trusted = Mock(return_value=True); h.path = '/api/health'
        h.do_GET()  # the same connection's next request is a read
        self.assertEqual(events, [403, 200])
        self.assertEqual(self.poll(server), 1)


if __name__ == '__main__':
    unittest.main()
