"""0.30.0 item F (seen on Sergei's machine 2026-11-18): Quit left the engine answering "closing" for over an hour.

Reproduction with the real classes: a live-sized catalog (tests/live_sized.py), audiobook jobs paused, nothing converting,
no queued action, automatic processing idle, and a status computation in flight when Quit is pressed (the page's poll just
before it), slowed as under load. The shell's own Quit watch polls the desktop status every second meanwhile.

Before the fix: phase 'blocked' after 30 s ("Status computations are still closing their catalog reads"): close waited for
the read, then gave up with the engine half closed, and the shell left it so.
"""
import sys
import threading
import time
import traceback
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import live_sized
import merge_service
import web_server
from action_queue import ActionQueue
from automatic_processing import AutomaticProcessing
from desktop_backend import DesktopControl
from merge_service import MergeService, SharedSnapshot
from test_approve_as_is import ApproveFixture, tone
from test_lock_timing import SlowLookup

READS = ('books-status', 'books-desktop-status', 'fixture-page-poll')


def frames():
    """Every thread's stack, for a close that does not finish (what it waits on)."""
    names = {thread.ident: thread.name for thread in threading.enumerate()}
    lines = []
    for ident, frame in sys._current_frames().items():
        lines.append('--- %s' % names.get(ident, ident))
        lines.extend(line.rstrip() for line in traceback.format_stack(frame)[-6:])
    return '\n'.join(lines)


class QuitWithinSecondsTests(ApproveFixture):
    BOUND = 5.0     # seconds from Quit to phase 'exiting'
    LIMIT = 90.0    # how long the reproduction watches before it reports what still waits
    ANSWER = 1.0    # seconds a desktop status poll may take while Quit runs (it answered after a state computation)

    def setUp(self):
        super().setUp()
        # Registered after the fixture folder's cleanup, so it runs first: a status read Quit no longer waits for still holds
        # the fixture catalog open for a moment after the test.
        self.addCleanup(self.reads_done)

    @staticmethod
    def reads_done():
        for thread in threading.enumerate():
            if thread.name in READS:
                thread.join(120)

    def serve(self):
        server = web_server.BrowserServer(('127.0.0.1', 0), self.inv, lambda inventory, cache, progress=None: self.service)
        serving = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05}, name='fixture-serve', daemon=True)
        serving.start()

        def stop():
            if serving.is_alive():
                server.shutdown()
            server.socket.close()
        self.addCleanup(stop)
        return server

    def test_quit_with_jobs_paused_and_a_slow_status_computation_in_flight_exits_within_seconds(self):
        tone(self.audio / 'Unsorted' / 'Ясно' / 'Ясно.mp3', self.cover, album='Ясно', artist='Иван Петров')
        row = self.start()[0]; self.service.approve_book(row['id'], row['revision']); self.start_and_wait()
        live_sized.grow(self.inv)
        self.service.pause_work(origin='user')  # Sergei's audiobook jobs were paused
        server = self.serve()
        control = DesktopControl(server); server.desktop = control
        with SlowLookup(self.service, 0.1) as slow:  # a status computation of about a minute, as under load
            poll = threading.Thread(target=lambda: server.state('Audiobooks', cached=True), name='fixture-page-poll', daemon=True)
            poll.start()
            self.assertTrue(slow.started.wait(30), 'positive control: a status computation is in flight before Quit')
            seen = []
            watching = threading.Event()

            def shell_watch():  # desktop/main.js watchQuit: the desktop status every second
                while not watching.is_set():
                    asked = time.monotonic()
                    try:
                        value = control.status()
                        seen.append((value['phase'], value.get('waiting_for'), time.monotonic() - asked))
                    except Exception as error:
                        seen.append((type(error).__name__, None, time.monotonic() - asked))
                    watching.wait(1)
            started = time.monotonic()
            self.assertEqual(control.quit()['phase'], 'finishing')
            watcher = threading.Thread(target=shell_watch, name='fixture-shell-watch', daemon=True); watcher.start()
            self.addCleanup(watching.set)
            dump = ''
            while control.phase not in ('exiting', 'blocked') and time.monotonic() - started < self.LIMIT:
                if not dump and time.monotonic() - started > self.BOUND + 1:
                    dump = frames()
                time.sleep(.05)
            took = time.monotonic() - started
            watching.set(); watcher.join(10)
            print('\nQuit: phase %s after %.1f s; error %r; shell saw %s' % (control.phase, took, control.error, seen[-5:]), file=sys.stderr)
            if dump:
                print(dump, file=sys.stderr)
        self.assertEqual(control.phase, 'exiting', control.error)
        self.assertLess(took, self.BOUND)
        self.assertTrue(poll.is_alive() or any(thread.name == 'books-status' for thread in threading.enumerate()),
                        'positive control: the status computation was still running when Quit finished')
        self.assertTrue(seen, 'the shell watch polled')
        self.assertLess(max(answer for _, _, answer in seen), self.ANSWER, 'a desktop status poll during Quit answers at once')
        # The background sweeps Quit tells to stop may show for an instant; nothing real is left to wait for in Sergei's case.
        waits = [waiting for phase, waiting, _ in seen if phase in ('finishing', 'parking')]
        self.assertEqual(waits[-1:], [[]], seen)

    def wait_for(self, check, seconds=10):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            value = check()
            if value:
                return value
            time.sleep(.05)
        self.fail('condition not reached: ' + repr(check()))

    def test_a_press_in_flight_is_named_waited_for_and_a_safe_stop_ends_the_close_within_its_bound(self):
        # Real work is waited for and said (waiting_for); the shell's safe stop (stop-now) takes over the wait; a close that
        # cannot finish says 'blocked' with what still runs, and Quit again closes once the press has ended.
        tone(self.audio / 'Unsorted' / 'Ясно' / 'Ясно.mp3', self.cover, album='Ясно', artist='Иван Петров')
        self.start()
        server = self.serve()
        control = DesktopControl(server); server.desktop = control
        entered, release = threading.Event(), threading.Event()

        def press():  # a press admitted as Handler.do_POST admits one, held while it runs (as a Delete book's file loop)
            with server.control_condition:
                server.merge_admissions += 1
            entered.set()
            try:
                release.wait(60)
            finally:
                with server.control_condition:
                    server.merge_admissions -= 1
                    server.control_condition.notify_all()
        presser = threading.Thread(target=press, name='fixture-press', daemon=True); presser.start()
        self.addCleanup(release.set)
        self.assertTrue(entered.wait(5))
        self.assertEqual(control.quit()['phase'], 'finishing')
        self.wait_for(lambda: control.status()['waiting_for'] == [{'kind': 'press', 'title': ''}] and control.phase == 'parking')
        self.assertTrue(server.health()['closing'])
        with patch.object(web_server.BrowserServer, 'ADMISSIONS_CLOSE', 1.0):
            started = time.monotonic()
            self.assertEqual(control.stop_now()['phase'], 'stopping')
            self.wait_for(lambda: control.phase in ('blocked', 'exiting'))
            self.assertLess(time.monotonic() - started, 5, 'the safe stop waits for a press only for its bound')
        self.assertFalse(control.thread.is_alive(), 'the Quit wait ended when the safe stop took over')
        value = control.status()
        self.assertEqual((value['phase'], value['waiting_for']), ('blocked', [{'kind': 'press', 'title': ''}]), 'the shell is told what still runs')
        self.assertIn('A press is still running', value['error'])
        # Futaba's 0.30.0 slice A delta: once the press has ended, the close runs again by itself (before: only a second
        # Quit closed it, and with no shell left nothing did).
        release.set(); presser.join(10)
        started = time.monotonic()
        self.wait_for(lambda: control.phase == 'exiting', seconds=15)
        self.assertLess(time.monotonic() - started, self.BOUND + DesktopControl.RETRY_AFTER)

    def press_holding(self, server, stop=None):
        """A press admitted as Handler.do_POST admits one, running until released, or until its stop is set (an approval
        still checking its files stops at its next checkpoint). Returns the release event and the thread."""
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def press():
            with server.control_condition:
                server.merge_admissions += 1
            entered.set()
            try:
                while not release.is_set() and not (stop is not None and stop.is_set()):
                    release.wait(.05)
            finally:
                with server.control_condition:
                    server.merge_admissions -= 1
                    server.control_condition.notify_all()
        presser = threading.Thread(target=press, name='fixture-press', daemon=True); presser.start()
        self.assertTrue(entered.wait(5))
        return release, presser

    def test_a_safe_stop_during_an_approval_tells_it_to_stop_and_exits_within_seconds(self):
        # Futaba's 0.30.0 slice A delta: a safe stop (sign-out, the shell's pipe closing, stop-now) during a 160 s Approve went
        # 'blocked' at 30 s: nothing told the approval to stop until close, which comes after the presses end.
        tone(self.audio / 'Unsorted' / 'Ясно' / 'Ясно.mp3', self.cover, album='Ясно', artist='Иван Петров')
        self.start()
        server = self.serve()
        control = DesktopControl(server); server.desktop = control
        approval = threading.Event()
        self.service.__dict__.setdefault('_approve_stops', set()).add(approval)  # as approve_book registers its checks
        self.press_holding(server, stop=approval)
        with patch.object(web_server.BrowserServer, 'ADMISSIONS_CLOSE', 1.0):
            started = time.monotonic()
            self.assertEqual(control.stop_now('shell_pipe_closed')['phase'], 'stopping')
            self.wait_for(lambda: control.phase in ('blocked', 'exiting'), seconds=15)
        self.assertEqual(control.phase, 'exiting', control.error)
        self.assertLess(time.monotonic() - started, self.BOUND)
        self.assertTrue(approval.is_set(), 'the approval was told to stop')
        self.assertTrue(self.service._presses_stopped, 'an approval reaching its checks later stops at once')

    def test_a_safe_stop_during_a_press_that_cannot_stop_closes_by_itself_once_it_has_ended(self):
        # The same, with a press that cannot be told to stop: the close fails at its bound ('blocked', naming only the press:
        # the background sweeps were never stopped, so 'cleanup' and 'decisions' stayed named for good), then runs again by
        # itself once the press has ended. Before: blocked for good (420+ s in Futaba's run) with no shell to Quit again.
        tone(self.audio / 'Unsorted' / 'Ясно' / 'Ясно.mp3', self.cover, album='Ясно', artist='Иван Петров')
        self.start()
        server = self.serve()
        control = DesktopControl(server); server.desktop = control
        release, presser = self.press_holding(server)
        with patch.object(web_server.BrowserServer, 'ADMISSIONS_CLOSE', 1.0):
            self.assertEqual(control.stop_now('shell_pipe_closed')['phase'], 'stopping')
            self.wait_for(lambda: control.phase == 'blocked', seconds=15)
            self.wait_for(lambda: control.status()['waiting_for'] == [{'kind': 'press', 'title': ''}], seconds=10)
            time.sleep(3)
            self.assertEqual(control.phase, 'blocked', 'still blocked while the press runs: it is not cut short')
            self.assertTrue(server.health()['closing'])
            release.set(); presser.join(10)
            started = time.monotonic()
            self.wait_for(lambda: control.phase == 'exiting', seconds=15)
        self.assertLess(time.monotonic() - started, self.BOUND + DesktopControl.RETRY_AFTER, 'closed by itself after the press')


def stand_in(converting=False):
    """A desktop engine stand-in: a book converting (or not), presses (merge_admissions), every read a mock that fails."""
    lock = threading.Lock()
    jobs_thread = SimpleNamespace(is_alive=Mock(return_value=converting))
    merge = SimpleNamespace(jobs=SimpleNamespace(_thread=jobs_thread), drain=Mock(), stop_background=Mock(),
                            automatic=SimpleNamespace(stop_work=Mock(), stop=Mock(), thread=None))
    server = SimpleNamespace(merge=merge, inventory=SimpleNamespace(stop=Mock()), closing=False, merge_admissions=0, control_lock=lock,
                             control_condition=threading.Condition(lock), scan_active=Mock(return_value=False), finish_shutdown=Mock(),
                             state=Mock(side_effect=AssertionError('no state computation while Quit runs')))
    return server, jobs_thread


class QuitWaitsOnlyForRealWorkTests(unittest.TestCase):
    wait_for = QuitWithinSecondsTests.wait_for

    def test_quit_status_names_what_it_waits_for_at_once_and_never_computes_a_state(self):
        server, jobs_thread = stand_in(converting=True)
        control = DesktopControl(server)
        with patch.object(DesktopControl, '_read_running_title', return_value='Дюна'):
            self.assertEqual(control.quit()['phase'], 'finishing')
            self.wait_for(lambda: server.merge.automatic.stop_work.called)
            server.merge.stop_background.assert_called_once_with()  # the background sweeps are told at once
            value = control.status()
            self.assertEqual((value['phase'], value['busy'], value['idle']), ('finishing', None, False))
            self.assertEqual(value['waiting_for'], [{'kind': 'conversion', 'title': 'Дюна'}])
            server.merge_admissions = 1
            self.assertEqual(control.status()['waiting_for'], [{'kind': 'conversion', 'title': 'Дюна'}, {'kind': 'press', 'title': ''}])
            jobs_thread.is_alive.return_value = False
            self.wait_for(lambda: control.status()['phase'] == 'parking')
            self.assertEqual(control.status()['waiting_for'], [{'kind': 'press', 'title': ''}])
            server.finish_shutdown.assert_not_called()
            server.merge_admissions = 0
            control.thread.join(5)
        self.assertEqual(control.status()['phase'], 'exiting')
        server.finish_shutdown.assert_called_once_with()
        server.state.assert_not_called()

    def test_a_safe_stop_takes_over_a_waiting_quit_and_the_close_runs_once(self):
        server, _ = stand_in(converting=True)
        control = DesktopControl(server)
        control.quit()
        self.wait_for(lambda: server.merge.automatic.stop_work.called)
        self.assertEqual(control.stop_now()['phase'], 'stopping')
        control.thread.join(5)
        self.assertFalse(control.thread.is_alive(), 'the Quit wait ended')
        self.wait_for(lambda: control.phase == 'exiting')
        time.sleep(DesktopControl.QUIT_POLL * 2)
        server.finish_shutdown.assert_called_once_with()
        self.assertEqual(control.stop_now()['phase'], 'exiting', 'a second safe stop starts nothing')

    def test_quit_never_waits_behind_a_press_that_holds_the_control_lock(self):
        # A scan control answers with a full status computation under the control lock (minutes under load).
        server, _ = stand_in()
        control = DesktopControl(server)
        held, release = threading.Event(), threading.Event()

        def press():
            with server.control_lock:
                held.set(); release.wait(10)
        threading.Thread(target=press, daemon=True).start()
        self.addCleanup(release.set)
        self.assertTrue(held.wait(5))
        started = time.monotonic()
        self.assertEqual(control.quit()['phase'], 'finishing')
        self.assertLess(time.monotonic() - started, DesktopControl.CLOSING_LOCK + 1)
        self.assertTrue(server.closing)
        release.set()
        control.thread.join(5)
        self.assertEqual(control.phase, 'exiting')


class CloseBoundTests(unittest.TestCase):
    def test_a_status_computation_still_running_is_left_after_the_read_bound_and_close_never_raises(self):
        shared = SharedSnapshot(wait=.01)
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def compute():
            entered.set(); release.wait(10); return {}
        with self.assertRaises(merge_service.StatusUnavailable):
            shared.get(compute, 0)
        self.assertTrue(entered.wait(5))
        started = time.monotonic()
        left = shared.close(time.monotonic() + .2)
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertEqual(len(left), 1); self.assertTrue(left[0].is_alive(), 'the read still runs; close went on')
        started = time.monotonic()
        self.assertEqual(shared.close(), left)
        self.assertLess(time.monotonic() - started, .5, 'a second close (server_close) waits no more')
        release.set(); left[0].join(5)

    def test_lookups_are_left_after_the_read_bound_but_a_rename_they_began_is_waited_for(self):
        import critical_sections
        release = threading.Event()
        self.addCleanup(release.set)
        thread = threading.Thread(target=lambda: release.wait(10), daemon=True); thread.start()
        background = SimpleNamespace(stop=threading.Event(), wake=threading.Event(), thread=thread,
                                     close=Mock(side_effect=AssertionError('the 30 s join')))
        started = time.monotonic()
        MergeService._close_lookups(background, time.monotonic() + .2)
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertTrue(background.stop.is_set() and background.wake.is_set())
        with critical_sections.critical(critical_sections.RENAME):
            threading.Timer(.5, release.set).start()
            started = time.monotonic()
            MergeService._close_lookups(background, time.monotonic())
            self.assertGreaterEqual(time.monotonic() - started, .4, 'a rename it began is waited for')
        self.assertFalse(thread.is_alive())
        legacy = SimpleNamespace(close=Mock())
        MergeService._close_lookups(legacy, 0)
        legacy.close.assert_called_once_with()

    def test_a_press_still_running_fails_the_shutdown_after_its_bound_instead_of_holding_it_forever(self):
        server = object.__new__(web_server.BrowserServer)
        lock = threading.Lock()
        server.control_lock, server.control_condition = lock, threading.Condition(lock)
        server.merge_admissions, server.loading, server.merge = 1, None, None
        server.inventory = SimpleNamespace(stop=Mock(), worker=None)
        server.shutdown = Mock()
        with patch.object(web_server.BrowserServer, 'ADMISSIONS_CLOSE', .3):
            started = time.monotonic()
            with self.assertRaisesRegex(TimeoutError, 'A press is still running'):
                server.finish_shutdown()
            self.assertLess(time.monotonic() - started, 2)
            server.shutdown.assert_not_called()

            def done():
                time.sleep(.1)
                with server.control_condition:
                    server.merge_admissions = 0; server.control_condition.notify_all()
            threading.Thread(target=done, daemon=True).start()
            server.finish_shutdown()
        server.shutdown.assert_called_once_with()

    def test_quit_writes_the_saved_queue_only_when_it_changed(self):
        store = Mock()
        queue = ActionQueue(SimpleNamespace(closing=False, inventory=None), store=store)
        queue.restored = True
        queue.drop()
        store.save.assert_not_called()
        queue.close()
        store.save.assert_called_once_with([], closing=True)


def shutdown_stand_in(admissions=1):
    """A BrowserServer for finish_shutdown alone: presses held (merge_admissions), nothing else to close."""
    server = object.__new__(web_server.BrowserServer)
    lock = threading.Lock()
    server.control_lock, server.control_condition = lock, threading.Condition(lock)
    server.merge_admissions, server.loading, server.merge = admissions, None, None
    server.inventory = SimpleNamespace(stop=Mock(), worker=None)
    server.shutdown = Mock()
    return server


class FileChangeCloseTests(unittest.TestCase):
    """Senua's 0.30.0 review, M4 (ruling 27: a file change finishes once begun). A safe stop (Quit anyway, a sign-out, the
    shell's pipe closing) waits for an open file change to its own end, never past critical_sections.FILE_CHANGE_BOUND, so
    an accepted Quit still always ends."""

    def press_in(self, server, section, holds):
        """A press holding its admission, inside one file change (section) until holds is set."""
        import critical_sections
        opened = threading.Event()

        def press():
            with critical_sections.critical(section):
                opened.set(); holds.wait(10)
            with server.control_condition:
                server.merge_admissions -= 1; server.control_condition.notify_all()
        threading.Thread(target=press, name='fixture-press', daemon=True).start()
        self.assertTrue(opened.wait(5))

    def test_a_press_inside_a_file_change_is_waited_for_to_its_end_past_the_press_bound(self):
        import critical_sections
        server, holds = shutdown_stand_in(), threading.Event()
        self.addCleanup(holds.set)
        self.press_in(server, critical_sections.DELETE, holds)
        threading.Timer(1.2, holds.set).start()
        with patch.object(web_server.BrowserServer, 'ADMISSIONS_CLOSE', .3):
            started = time.monotonic()
            server.finish_shutdown()  # before: TimeoutError at 0.3 s, and the shell then ended the engine mid-delete
            self.assertGreaterEqual(time.monotonic() - started, 1.0, 'waited for the delete loop to end')
        server.shutdown.assert_called_once_with()

    def test_a_file_change_past_its_ceiling_still_ends_the_shutdown(self):
        import critical_sections
        server, holds = shutdown_stand_in(), threading.Event()
        self.addCleanup(holds.set)
        self.press_in(server, critical_sections.DELETE, holds)
        with patch.object(web_server.BrowserServer, 'ADMISSIONS_CLOSE', .2), patch.object(critical_sections, 'FILE_CHANGE_BOUND', .8):
            started = time.monotonic()
            with self.assertRaisesRegex(TimeoutError, 'A press is still running'):
                server.finish_shutdown()
            self.assertGreaterEqual(time.monotonic() - started, .7)
            self.assertLess(time.monotonic() - started, 2.5, 'the ceiling ends it: an accepted Quit always ends')
        server.shutdown.assert_not_called()

    def test_close_stops_the_file_workers_then_waits_for_an_open_change_to_end(self):
        import critical_sections
        merge = MergeService.__new__(MergeService)
        merge.jobs, merge.cleanup = SimpleNamespace(_stop=threading.Event()), SimpleNamespace(stop=threading.Event())
        holds, opened = threading.Event(), threading.Event()
        self.addCleanup(holds.set)

        def tag_edit():
            with critical_sections.critical(critical_sections.TAG_EDIT):
                opened.set(); holds.wait(10)
        threading.Thread(target=tag_edit, daemon=True).start()
        self.assertTrue(opened.wait(5))
        threading.Timer(.6, holds.set).start()
        started = time.monotonic()
        merge._close_file_changes()
        self.assertGreaterEqual(time.monotonic() - started, .5, 'the tag edit ended first')
        self.assertTrue(merge.jobs._stop.is_set() and merge.cleanup.stop.is_set(), 'no new file change begins')
        self.assertEqual(critical_sections.open_sections(), [])
        # The ceiling: a change that does not end is left after FILE_CHANGE_BOUND.
        stuck = threading.Event()
        self.addCleanup(stuck.set)
        opened.clear()

        def removal():
            with critical_sections.critical(critical_sections.CLEANUP):
                opened.set(); stuck.wait(10)
        hung = threading.Thread(target=removal, daemon=True); hung.start()
        self.assertTrue(opened.wait(5))
        with patch.object(critical_sections, 'FILE_CHANGE_BOUND', .3):
            started = time.monotonic()
            merge._close_file_changes()
            self.assertLess(time.monotonic() - started, 1.5)
        stuck.set(); hung.join(5)
        self.assertEqual(critical_sections.open_sections(), [])


class AutomaticCloseTests(unittest.TestCase):
    def test_the_stopped_runs_last_wait_ends_when_the_app_closes(self):
        auto = AutomaticProcessing.__new__(AutomaticProcessing)
        auto.closed, auto.server_closing = False, None
        auto.merge = SimpleNamespace(draining=False, state=lambda: {'state': 'Pausing'})
        self.assertTrue(auto._still_pausing(), 'positive control: a Pause waits for its queue')
        auto.merge.draining = True
        self.assertFalse(auto._still_pausing(), 'Quit drains: the run saves its checkpoint now')
        auto.merge.draining, auto.server_closing = False, (lambda: True)
        self.assertFalse(auto._still_pausing(), 'an update or a safe stop')
        auto.server_closing, auto.closed = None, True
        self.assertFalse(auto._still_pausing())
        auto.closed, auto.merge.state = False, Mock(side_effect=RuntimeError('catalog busy'))
        self.assertFalse(auto._still_pausing(), 'a failed read ends the wait')

    def test_the_run_reads_its_queued_work_now_never_with_a_full_status_computation(self):
        merge = MergeService.__new__(MergeService)
        merge.live_jobs = lambda: ({'state': 'Paused', 'queued': 0, 'failed': 0}, None)
        merge.replacements = object()
        merge._pending_replacement_postprocessing = lambda: ['job']
        auto = AutomaticProcessing.__new__(AutomaticProcessing)
        auto.merge = merge
        with patch.object(MergeService, 'state', side_effect=AssertionError('a full status computation')):
            self.assertTrue(auto._queue_to_resume(), 'replacement postprocessing waits')
            merge._pending_replacement_postprocessing = lambda: []
            self.assertFalse(auto._queue_to_resume())
            merge.live_jobs = lambda: ({'state': 'Paused', 'queued': 2, 'failed': 0}, None)
            self.assertTrue(auto._queue_to_resume())


if __name__ == '__main__':
    unittest.main()
