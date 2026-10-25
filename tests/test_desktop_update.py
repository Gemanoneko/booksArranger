"""0.22.1, ruling 27 (Sergei 2026-10-25, "updates must not fail"): the engine's side of Restart to update.

0.21.1's update request computed a fresh, unbounded full state while the shell waited 5 s for it; the shell gave up,
the engine finished the fence anyway, shut down, and the app closed without installing. Nothing undid the fence. Now
the request answers at once, the work stops at its safe points within bounds, the engine ends only with nothing left
running and no file change half done, and Cancel or the bound undo everything. A fake engine; the busy-engine matrix
of the proposal (section 5E) that does not need a packaged build."""
import io
import threading
import time
from email.message import Message
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import critical_sections
from desktop_backend import DesktopControl, UpdateStarted, handler_class
from web_server import Handler

TOKEN = 'd' * 64


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


def control(server, safe=5.0, force=5.0):
    value = DesktopControl(server)
    value.UPDATE_SAFE, value.UPDATE_FORCE, value.UPDATE_POLL = safe, force, 0.02
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
        server, calls = engine(converting=True, automatic=True, stubborn=True)
        value = control(server); value.prepare_update()
        time.sleep(0.1)
        answer = value.cancel_update()
        self.assertEqual(answer['phase'], 'running'); self.assertFalse(server.closing, 'presses work again')
        self.assertEqual(answer['update']['outcome']['result'], 'cancelled')
        self.assertIn('automatic start', calls, 'the automatic run continues')
        self.assertNotIn('shutdown', calls)

    def test_a_cancel_restarts_the_queue_and_the_scan_that_ran(self):
        server, calls = engine(converting=True, scanning=True, stubborn=True)
        value = control(server); value.prepare_update(); time.sleep(0.1)
        value.cancel_update()
        self.assertIn(('resume', {'recheck': False}), calls)
        self.assertIn(('scan resume', 'Audiobooks', True), calls)

    def test_the_bound_cancels_and_keeps_the_app_running(self):
        # The last resort without proof that every write path survives a forced end: cancel and say what did not stop.
        server, calls = engine(converting=True, stubborn=True)
        value = control(server, safe=0.2, force=0.3); value.prepare_update()
        status = finish(value)
        self.assertEqual(status['phase'], 'running'); self.assertFalse(server.closing)
        outcome = status['update']['outcome']
        self.assertEqual(outcome['result'], 'bound'); self.assertEqual([w['kind'] for w in outcome['waiting']], ['conversion'])
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
