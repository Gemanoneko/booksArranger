"""Ruling 35 (Sergei 2026-10-26): every action queues; nothing is refused for being busy.

- Approve (and Convert what's there) is accepted at once and always queued with Sergei's values: its checks (every file
  probed and hashed) run in the queue's worker, never in a page request waiting up to 600 s. It runs at once when nothing
  is in the way, after a scan or loading otherwise, every check made again then.
- Keep as separate books, Scan again, Remove from list, Remove this copy, Save and Forget names, Start and Resume scanning
  queue behind what holds them (a scan, loading, the book converting, conversion or automatic processing for a scan).
- A refusal names its gate ("Spящие красавицы": every Approve gate has its own code), never the bare sentence.
Stub services and a stub server with the real run_queued; the HTTP entry is Handler.queue_press."""
import threading, time, unittest, uuid
from types import SimpleNamespace

import web_server
from action_queue import ActionQueue


class Merge:
    def __init__(self):
        self.calls, self.answers = [], {}
        self.operation_lock = threading.RLock()
        self.reviews = SimpleNamespace(_row=lambda library, identity, revision=None: {'id': identity})
        self.converting = set()
        self.automatic = SimpleNamespace(status=lambda: {'state': self.automatic_state})
        self.automatic_state = 'Idle'

    def _answer(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        value = self.answers.get(name, {})
        if isinstance(value, BaseException):
            raise value
        return value

    def approve_book(self, *args, **kwargs):
        return self._answer('approve', *args, **kwargs)

    def keep_separate(self, *args):
        return self._answer('separate', *args)

    def scan_again(self, *args):
        return self._answer('scan_again', *args)

    def dismiss_attention(self, *args):
        return self._answer('dismiss', *args)

    def names_save(self, *args):
        return self._answer('names', *args)

    def _names_job(self, identity):
        return {'state': 'running' if identity in self.converting else 'none'}


class Server:
    run_queued = web_server.BrowserServer.run_queued

    def __init__(self):
        self.merge = Merge()
        self.scanning = False
        self.closing = False
        self.jobs = False
        self.loading = None
        self.control_lock = threading.Lock()
        self.control_condition = threading.Condition(self.control_lock)
        self.merge_admissions = 0
        self.launched = []
        self.active_library = None
        self.inventory = SimpleNamespace(roots={'Audiobooks': r'Z:\Audiobooks'}, launch=lambda library, resume=False: self.launched.append((library, resume)))
        self.actions = ActionQueue(self, poll=.02)

    def scan_active(self):
        return self.scanning

    def jobs_active(self):
        return self.jobs

    def invalidate_status(self):
        pass


def until(check, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(.01)
    return False


class QueuedPressTests(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.queue = self.server.actions
        self.addCleanup(self.queue.close)
        self.book = str(uuid.uuid4())

    def outcomes(self, n=1):
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) >= n), self.queue.view())
        return self.queue.view()['queue_outcomes']

    def approve(self, **args):
        values = {'revision': 3, 'title': None, 'author': 'King Stephen and King Owen', 'choice': None, 'path': 'King Stephen\\Book.m4b', 'names': {'series': 'S', 'number': '1'}}
        values.update(args)
        return self.queue.enqueue('approve', self.book, 'Спящие красавицы', values)

    def test_approve_is_always_queued_with_his_values_and_runs_at_once_when_nothing_is_in_the_way(self):
        self.server.merge.answers['approve'] = {'job_id': 'job-1', 'row': {}}
        answer = self.approve()
        self.assertEqual((answer['queued'], answer['position']), (True, 1), 'accepted, never run inside the page request')
        outcome = self.outcomes()[0]
        self.assertEqual((outcome['action'], outcome['result'], outcome['answer']), ('approve', 'done', {'job_id': 'job-1'}))
        name, args, kwargs = self.server.merge.calls[0]
        self.assertEqual(args, (self.book, 3, None, 'King Stephen and King Owen'))
        self.assertEqual(kwargs, {'without_missing': False, 'choice': None, 'path': 'King Stephen\\Book.m4b', 'names': {'series': 'S', 'number': '1'}}, 'exactly what was pressed')

    def test_approve_pressed_during_a_scan_waits_and_runs_when_the_scan_ends(self):
        self.server.merge.answers['approve'] = {'job_id': 'job-2'}
        self.server.scanning = True
        self.assertEqual(self.approve()['blocker'], {'kind': 'scan'})
        time.sleep(.1)
        self.assertEqual(self.server.merge.calls, [], 'nothing runs while the library scan regroups the catalog')
        self.server.scanning = False
        self.assertEqual(self.outcomes()[0]['result'], 'done')

    def test_a_refused_approve_names_its_gate(self):
        self.server.merge.answers['approve'] = ValueError('Split book parts are different recordings (audio profiles differ)')
        self.approve()
        outcome = self.outcomes()[0]
        self.assertEqual((outcome['result'], outcome['code']), ('refused', 'profiles'))
        self.assertIn('audio profiles differ', outcome['error'], "the engine's own sentence travels to the row")

    def test_every_approve_gate_has_its_own_code(self):
        cases = {'Destination changed since it was shown: it is now X. Nothing was changed.': 'moved',
                 'An audiobook already exists at this path; nothing was overwritten': 'name_taken', 'Audiobook job already exists': 'job_exists',
                 'Book parts carry their own chapters; joining them would drop those chapters': 'chapters', 'Cover not verified': 'cover',
                 'Source files unavailable or unreadable': 'sources', 'Manual draft retained': 'draft', 'Books Arranger is closing. Nothing was changed.': 'closing',
                 'Source files changed': 'changed', 'Audio format needs an encoding decision': 'format', 'Type a title first.': 'title',
                 "Approve was not accepted: the app couldn't read this book's identity from its files. Type its title and author, then approve. Nothing was changed.": 'identity',
                 'Something new': 'refused'}
        self.assertEqual({text: web_server.approve_code(text) for text in cases}, cases)

    def test_a_press_while_loading_waits_for_loading_to_finish(self):
        self.server.loading = SimpleNamespace(finished=False)
        answer = self.queue.enqueue('separate', self.book, 'Book', {'revision': 2})
        self.assertEqual(answer['blocker'], {'kind': 'loading'})
        time.sleep(.1); self.assertEqual(self.server.merge.calls, [])
        self.server.loading.finished = True
        self.assertEqual(self.outcomes()[0]['result'], 'done')
        self.assertEqual(self.server.merge.calls[0][:2], ('separate', (self.book, 2)))

    def test_save_names_waits_while_its_book_converts(self):
        self.server.merge.converting.add(self.book)
        answer = self.queue.enqueue('names', self.book, 'Book', {'revision': 2, 'names': {'series': 'S', 'number': '1'}})
        self.assertEqual(answer['blocker'], {'kind': 'book'}, 'was refused: "This book is converting. Its names can\'t change now."')
        self.server.merge.converting.clear()
        self.assertEqual(self.outcomes()[0]['result'], 'done')

    def test_a_scan_pressed_while_converting_or_while_automatic_processing_runs_starts_when_they_end(self):
        self.server.jobs = True
        answer = self.queue.enqueue('scan_start', 'library:Audiobooks', 'Audiobooks', {'library': 'Audiobooks'})
        self.assertEqual(answer['blocker'], {'kind': 'jobs'}, 'was refused: "Pause audiobook work before starting a scan"')
        self.server.merge.automatic_state = 'Running'
        time.sleep(.1); self.assertEqual(self.server.launched, [])
        self.server.jobs = False; time.sleep(.1)
        self.assertEqual(self.server.launched, [], 'automatic processing owns discovery while it runs')
        self.server.merge.automatic_state = 'Completed'
        self.assertEqual(self.outcomes()[0]['result'], 'done')
        self.assertEqual((self.server.launched, self.server.active_library), ([('Audiobooks', False)], 'Audiobooks'))

    def test_scan_again_and_remove_from_list_run_at_once_when_nothing_is_in_the_way(self):
        self.assertIsNone(self.queue.enqueue('scan_again', self.book, 'Book', {'revision': 2}), 'the caller runs it in its own request')
        self.server.scanning = True
        self.assertEqual(self.queue.enqueue('scan_again', self.book, 'Book', {'revision': 2})['blocker'], {'kind': 'scan'})


class QueuePressEntryTests(unittest.TestCase):
    """Handler.queue_press: the press's own validation, nothing of the engine read (so it works while loading)."""
    def handler(self):
        server = Server(); self.addCleanup(server.actions.close)
        server.scanning = True
        handler = object.__new__(web_server.Handler); handler.server = server
        return handler, server

    def test_an_approve_keeps_the_values_typed_and_the_goes_to_line_shown(self):
        handler, server = self.handler()
        book = str(uuid.uuid4())
        answer = handler.queue_press('/api/candidate/approve', {'library': 'Audiobooks', 'id': book, 'revision': 4, 'title': 'Сейф №1', 'path': 'Сборники\\x.m4b',
                                                                'names': {'series': 'Протоколы SCP', 'number': '1'}, 'queue': True, 'label': 'Пртоколы SCP. Сейф №1'})
        self.assertTrue(answer['queued'])
        item = server.actions.view()['queued_actions'][0]
        self.assertEqual((item['action'], item['title']), ('approve', 'Пртоколы SCP. Сейф №1'))
        self.assertEqual(server.actions.items[0]['args'], {'revision': 4, 'title': 'Сейф №1', 'author': None, 'choice': None, 'path': 'Сборники\\x.m4b',
                                                           'names': {'series': 'Протоколы SCP', 'number': '1'}})
        with self.assertRaises(ValueError):
            handler.queue_press('/api/candidate/approve', {'library': 'Audiobooks', 'id': book, 'revision': 4, 'queue': True, 'unknown': 1})

    def test_convert_whats_there_queues_as_its_own_action(self):
        handler, server = self.handler()
        handler.queue_press('/api/candidate/approve', {'library': 'Audiobooks', 'id': str(uuid.uuid4()), 'revision': 4, 'without_missing': True, 'queue': True})
        self.assertEqual(server.actions.view()['queued_actions'][0]['action'], 'convert')


class SettlingStartTests(unittest.TestCase):
    """The rest of ruling 35 (Sergei, ruling 37, 2026-10-26): Resume audiobook jobs pressed while a Pause or an earlier
    start is still settling refused "… Retry Start after it stops." It is now kept and made when it settles; a Pause
    pressed after it, Cancel (the same button again) and closing take it back. The real MergeService methods on a bare
    instance; resume() stubbed to refuse while the pause settles, as _capture_start_generation does."""

    def service(self):
        import merge_service
        from audio_jobs import StartRefused
        s = merge_service.MergeService.__new__(merge_service.MergeService)
        s.draining = False; s._pause_depth = 0; s._start_generation = 1
        s.jobs = SimpleNamespace(_thread=None, _stop=threading.Event(), report_priority=lambda value: self.recorded.append(value), _db=None)
        s.cleanup = SimpleNamespace(thread=None, stop=threading.Event())
        s.state = lambda: {'state': 'Paused'}
        self.started, self.recorded = [], []

        def resume(*_, **__):
            if s._pause_depth:
                raise StartRefused('busy', 'Pause is still reaching the queue checkpoints. Retry Start after it completes.')
            self.started.append(s._start_generation)
            return {'state': 'Running'}
        s.resume = resume
        return s

    def test_resume_while_a_pause_settles_starts_when_it_settles(self):
        s = self.service()
        s._pause_depth = 1
        answer = s.resume_press()
        self.assertEqual(answer['start_admission'], {'state': 'waiting', 'reason': 'pause'}, 'kept, never "Retry Start after it completes"')
        token = s._start_waiting['token']
        self.assertEqual(s.resume_press()['start_admission']['state'], 'waiting')
        self.assertIs(s._start_waiting['token'], token, 'a second press joins the waiting start')
        time.sleep(.3)
        self.assertEqual(self.started, [], 'nothing starts while the pause settles')
        s._pause_depth = 0
        self.assertTrue(until(lambda: self.started == [1] and s.__dict__.get('_start_waiting') is None))
        self.assertEqual(self.recorded, [], 'no start failure is recorded')

    def test_a_pause_pressed_after_it_cancel_and_closing_take_it_back(self):
        from audio_jobs import StartRefused
        s = self.service()
        s._pause_depth = 1
        s.resume_press()
        s._start_generation += 1  # Pause pressed after Resume: the later press wins
        s._pause_depth = 0
        self.assertTrue(until(lambda: s.__dict__.get('_start_waiting') is None))
        time.sleep(.3)
        self.assertEqual(self.started, [])
        s._pause_depth = 1
        s.resume_press()
        self.assertEqual(s.cancel_waiting_start(), {'cancelled': True})
        self.assertIsNone(s.cancel_waiting_start(), 'nothing waits any more')
        s._pause_depth = 0
        time.sleep(.4)
        self.assertEqual(self.started, [], 'a cancelled start never starts')
        s._closing = True
        with self.assertRaises(StartRefused):
            s.start_when_settled()

    def test_a_retry_pressed_while_a_pause_settles_starts_the_queue_after_it(self):
        s = self.service()
        s._pause_depth = 1
        value = s._record_start_failure(__import__('audio_jobs').StartRefused('busy', 'Pause is still reaching the queue checkpoints.'))
        self.assertEqual(value, {'state': 'waiting', 'reason': 'pause'})
        s._pause_depth = 0
        self.assertTrue(until(lambda: self.started == [1]))
        self.assertEqual(self.recorded, [], 'never saved as "Retry Start after it stops"')

    def test_the_state_says_a_start_waits(self):
        import merge_service
        s = merge_service.MergeService.__new__(merge_service.MergeService)
        s._state = lambda: {'state': 'Pausing'}
        s._bulk_retry_view = lambda: None
        s._start_waiting = {'generation': 1, 'reason': 'pause', 'since': 0, 'token': object()}
        self.assertEqual(s.state()['start_waiting'], {'reason': 'pause'})


class ResumeRouteTests(unittest.TestCase):
    def test_resume_answers_the_kept_start_and_the_same_button_again_cancels_it(self):
        server = Server()
        server.merge.resume_press = lambda: {'state': 'Paused', 'start_admission': {'state': 'waiting', 'reason': 'pause'}}
        answers = iter([{'cancelled': True}, None])
        server.merge.cancel_waiting_start = lambda: next(answers)
        handler = web_server.Handler.__new__(web_server.Handler)
        handler.server = server
        sent = []
        handler.response = lambda status, body: sent.append((status, body))
        handler.merge_request('/api/audiobook/resume', {})
        handler.merge_request('/api/audiobook/resume-cancel', {})
        handler.merge_request('/api/audiobook/resume-cancel', {})
        self.assertEqual(sent, [(200, {'state': 'Paused', 'start_admission': {'state': 'waiting', 'reason': 'pause'}}), (200, {'cancelled': True}),
                                (409, {'error': 'It has already started.', 'code': 'started'})])


if __name__ == '__main__':
    unittest.main()
