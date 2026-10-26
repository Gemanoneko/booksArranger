"""Queued Retry, Repair and Delete book (0.22.1, backlog items 2 and 3; Judy's spec, section 1).

A press while another operation runs is accepted and queued, not refused: one queue, first in first out, one action at
a time, in memory only (Quit and updates drop it). The run goes through the same call the press makes, so its checks
run again; each outcome is kept until the page acknowledges it. Stub services and a stub server; the real delete and
the HTTP routes are in test_book_delete.QueuedDeleteTests and test_web."""
import threading, time, unittest, uuid
from types import SimpleNamespace
from unittest import mock

import action_queue
import audio_jobs
import book_delete
from action_queue import ActionQueue


class Merge:
    """Records each call; answers what the test sets."""
    def __init__(self):
        self.calls, self.answers = [], {}
        self.operation_lock = threading.RLock()
        self.busy_books = set()
        self.reviews = SimpleNamespace(_row=self._row)
        self.listed = True
        self.gate = None

    def _row(self, library, identity, revision=None):
        if not self.listed:
            raise ValueError('Candidate changed; reload evidence before reviewing')
        return {'id': identity}

    def _answer(self, name, *args):
        self.calls.append((name, args))
        if self.gate is not None:
            self.gate.wait(5)
        value = self.answers.get(name, {})
        if isinstance(value, BaseException):
            raise value
        return value(*args) if callable(value) else value

    def retry_blocked_job(self, *args):
        return self._answer('retry', *args)

    def repair_blocked_job(self, *args):
        return self._answer('repair', *args)

    def delete_book(self, *args):
        return self._answer('delete', *args)


class Server:
    def __init__(self):
        self.merge = Merge()
        self.scanning = False
        self.closing = False
        self.control_lock = threading.Lock()
        self.control_condition = threading.Condition(self.control_lock)
        self.merge_admissions = 0
        self.invalidated = 0

    def scan_active(self):
        return self.scanning

    def invalidate_status(self):
        self.invalidated += 1


def until(check, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(.01)
    return False


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.queue = ActionQueue(self.server, poll=.02)
        self.addCleanup(self.queue.close)
        processing = mock.patch.object(book_delete, 'processing', lambda merge, identity: identity in merge.busy_books)
        processing.start(); self.addCleanup(processing.stop)
        self.book = [str(uuid.uuid4()) for _ in range(4)]
        self.job = [str(uuid.uuid4()) for _ in range(4)]

    def retry(self, n, action='retry'):
        return self.queue.enqueue(action, self.book[n], 'Book %d' % n, {'revision': 3, 'job_id': self.job[n]})

    def delete(self, n, paths=('Z:/a.mp3',)):
        return self.queue.enqueue('delete', self.book[n], 'Book %d' % n, {'revision': 2, 'paths': list(paths), 'folders': []})

    def test_nothing_blocks_and_nothing_waits_so_the_press_runs_at_once(self):
        self.assertIsNone(self.retry(0), 'the caller runs it now, as before 0.22.1')
        self.assertIsNone(self.delete(1))
        self.assertEqual(self.queue.view(), {'queued_actions': [], 'queue_running': None, 'queue_outcomes': []})
        self.assertIsNone(self.queue.thread, 'no worker until something waits')

    def test_a_press_during_a_scan_is_queued_and_runs_in_order_when_the_scan_ends(self):
        self.server.scanning = True
        first = self.retry(0)
        self.assertEqual((first['queued'], first['position'], first['blocker']), (True, 1, {'kind': 'scan'}))
        second, third = self.delete(1), self.retry(2, 'repair')
        self.assertEqual((second['position'], third['position']), (2, 3))
        self.assertEqual(self.retry(0)['id'], first['id'], 'one queued action per row: a second press answers the first')
        with self.assertRaises(ValueError):
            self.delete(0)  # another action for a book that already waits: refused, the queue unchanged
        self.assertEqual(len(self.queue.view()['queued_actions']), 3)
        view = self.queue.view()
        self.assertEqual([(i['action'], i['position'], i['blocker']['kind'], i['title']) for i in view['queued_actions']],
                         [('retry', 1, 'scan', 'Book 0'), ('delete', 2, 'scan', 'Book 1'), ('repair', 3, 'scan', 'Book 2')])
        self.assertEqual(view['queued_actions'][1]['n'], 1, "a delete's confirmed file count")
        time.sleep(.1)
        self.assertEqual(self.server.merge.calls, [], 'nothing runs while the scan runs')
        self.server.merge.answers = {'retry': {'job_id': self.job[0], 'position': 1, 'queued_next': True, 'state': 'queued'},
                                     'delete': {'deleted': 1, 'bytes': 10, 'failed': [], 'forgotten': True, 'folders': {'removed': 0, 'stayed': 0}},
                                     'repair': {'job_id': self.job[2]}}
        self.server.scanning = False
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 3))
        self.assertEqual([name for name, _ in self.server.merge.calls], ['retry', 'delete', 'repair'], 'first in, first out')
        self.assertEqual(self.server.merge.calls[0][1], ('Audiobooks', self.book[0], 3, self.job[0]), 'the press as it was made: revision and job')
        self.assertEqual(self.server.merge.calls[1][1], (self.book[1], 2, ['Z:/a.mp3'], [], 'delete'), 'exactly the paths confirmed')
        outcomes = self.queue.view()['queue_outcomes']
        self.assertEqual([(o['action'], o['result'], o['title']) for o in outcomes], [('retry', 'done', 'Book 0'), ('delete', 'done', 'Book 1'), ('repair', 'done', 'Book 2')])
        self.assertEqual(outcomes[0]['answer'], {'position': 1, 'queued_next': True, 'state': 'queued'})
        self.assertEqual((outcomes[1]['deleted'], outcomes[1]['n'], outcomes[1]['failed']), (1, 1, []))
        self.assertEqual(self.queue.view()['queued_actions'], [])
        self.assertGreaterEqual(self.server.invalidated, 3, 'every run refreshes the status the page polls')
        self.assertEqual(self.server.merge_admissions, 0, 'each run held a control admission and gave it back')

    def test_one_action_at_a_time_and_a_fresh_press_goes_to_the_back_even_when_nothing_blocks_it(self):
        self.server.scanning = True
        self.retry(0)
        self.server.merge.gate = gate = threading.Event()
        self.server.scanning = False
        self.assertTrue(until(lambda: self.queue.view()['queue_running'] is not None))
        running = self.queue.view()['queue_running']
        self.assertEqual((running['action'], running['book_id']), ('retry', self.book[0]))
        later = self.retry(1)
        self.assertEqual((later['queued'], later['position'], later['blocker']), (True, 1, {'kind': 'operation'}), 'behind the running one')
        self.assertEqual(self.server.merge_admissions, 1, 'a running action holds an admission: shutdown waits for it')
        time.sleep(.1)
        self.assertEqual(len(self.server.merge.calls), 1, 'one at a time')
        gate.set()
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 2))

    def test_cancel_takes_a_waiting_action_out_and_is_too_late_once_it_started(self):
        self.server.scanning = True
        first, second = self.retry(0), self.delete(1)
        self.assertEqual(self.queue.cancel(second['id']), {'cancelled': True})
        self.assertEqual([i['id'] for i in self.queue.view()['queued_actions']], [first['id']])
        self.server.merge.gate = gate = threading.Event()
        self.server.scanning = False
        self.assertTrue(until(lambda: self.queue.view()['queue_running'] is not None))
        self.assertIsNone(self.queue.cancel(first['id']), 'too late: it has started')
        self.assertIsNone(self.queue.cancel(str(uuid.uuid4())), 'an id the queue does not hold')
        gate.set()
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 1))
        self.assertEqual([name for name, _ in self.server.merge.calls], ['retry'], 'the cancelled delete never ran')

    def test_a_refused_retry_is_cancelled_with_its_typed_cause_and_a_changed_status_is_named(self):
        self.server.scanning = True
        self.retry(0); self.retry(1); self.retry(2)
        refusals = iter([audio_jobs.RetryRefused(audio_jobs.RETRY_BOOK_CHANGED), audio_jobs.RetryRefused(audio_jobs.RETRY_NOT_CLEARED, 'busy'),
                         ValueError('Recovery book changed')])
        def refuse(*args):
            raise next(refusals)
        self.server.merge.answers = {'retry': refuse}
        self.server.scanning = False
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 3))
        found = [(o['result'], o['code'], o.get('error')) for o in self.queue.view()['queue_outcomes']]
        self.assertEqual(found, [('refused', 'changed', audio_jobs.RETRY_BOOK_CHANGED), ('refused', 'busy', audio_jobs.RETRY_NOT_CLEARED), ('refused', 'changed', None)])

    def test_a_scan_that_starts_again_before_the_run_puts_the_action_back_at_the_front(self):
        self.server.scanning = True
        self.retry(0); self.retry(1)
        tries = []
        def scan_again(*args):
            tries.append(args)
            if len(tries) == 1:
                self.server.scanning = True  # a scan began between the look and the run: the retry is refused as scanning
                raise audio_jobs.RetryRefused(audio_jobs.RETRY_SCANNING)
            return {'job_id': args[3]}
        self.server.merge.answers = {'retry': scan_again}
        self.server.scanning = False
        self.assertTrue(until(lambda: len(tries) == 1))
        self.assertTrue(until(lambda: [i['book_id'] for i in self.queue.view()['queued_actions']] == [self.book[0], self.book[1]]), 'back at the front')
        self.assertEqual(self.queue.view()['queue_outcomes'], [], 'no refusal is shown for a wait')
        self.server.scanning = False
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 2))
        self.assertEqual([o['result'] for o in self.queue.view()['queue_outcomes']], ['done', 'done'])

    def test_retry_waits_for_retry_all_and_delete_waits_for_the_book_and_the_operation_lock(self):
        self.server.merge._retry_all_run = {'state': 'running'}
        self.assertEqual(self.retry(0)['blocker'], {'kind': 'retry_run'})
        self.assertEqual(self.queue.blocker('delete', self.book[1]), None, 'Retry all does not hold Delete itself')
        later = self.delete(1)
        self.assertEqual((later['position'], later['blocker']), (2, {'kind': 'retry_run'}), 'but a press goes behind what waits (FIFO)')
        self.server.merge._retry_all_run = {'state': 'done'}
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 2))
        self.queue.acknowledge([o['id'] for o in self.queue.view()['queue_outcomes']])
        self.server.merge.busy_books.add(self.book[2])
        self.assertEqual(self.delete(2)['blocker'], {'kind': 'book'}, 'the book itself is converting or researched')
        self.server.merge.busy_books.clear()
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 1))
        held, release = threading.Event(), threading.Event()
        def hold():
            with self.server.merge.operation_lock:
                held.set(); release.wait(5)
        holder = threading.Thread(target=hold); holder.start(); self.addCleanup(holder.join); self.addCleanup(release.set)
        self.assertTrue(held.wait(5))
        self.assertIsNone(self.queue.blocker('retry', self.book[0]), 'Retry takes no lock: the lock does not hold it')
        self.assertEqual(self.delete(3)['blocker'], {'kind': 'operation'}, 'another operation holds the lock')
        time.sleep(.1)
        self.assertEqual([name for name, _ in self.server.merge.calls], ['retry', 'delete', 'delete'], 'the last delete waits for the lock')
        release.set()
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 2))

    def test_delete_outcomes_say_what_happened_and_nothing_when_refused_first(self):
        self.server.scanning = True
        for n in range(4):
            self.delete(n, paths=('Z:/a.mp3', 'Z:/b.mp3'))
        answers = iter([book_delete.DeleteRefused('files_changed', 'x'), book_delete.DeleteRefused('shared', 'x', [{'path': 'Z:/a.mp3', 'other': 'Другая'}]),
                        {'deleted': 1, 'bytes': 5, 'failed': [{'path': 'Z:/b.mp3', 'cause': 'in_use', 'detail': '[WinError 32] raw'}], 'forgotten': False},
                        book_delete.DeleteRefused('changed', 'x')])
        def answer(*args):
            value = next(answers)
            if isinstance(value, BaseException):
                if value.code == 'changed':
                    self.server.merge.listed = False
                raise value
            return value
        self.server.merge.answers = {'delete': answer}
        self.server.scanning = False
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 4))
        found = self.queue.view()['queue_outcomes']
        self.assertEqual([(o['result'], o.get('code')) for o in found], [('refused', 'files_changed'), ('refused', 'shared'), ('partial', None), ('refused', 'not_listed')])
        self.assertEqual(found[1]['files'], [{'path': 'Z:/a.mp3', 'other': 'Другая'}])
        self.assertEqual((found[2]['deleted'], found[2]['n'], found[2]['failed']), (1, 2, [{'path': 'Z:/b.mp3', 'cause': 'in_use'}]), 'no raw detail')

    def test_a_busy_refusal_while_a_blocker_is_back_waits_again(self):
        self.server.scanning = True
        self.delete(0)
        tries = []
        def busy(*args):
            tries.append(1)
            if len(tries) == 1:
                self.server.merge.busy_books.add(self.book[0])
                raise book_delete.DeleteRefused('busy', book_delete.BUSY)
            return {'deleted': 1, 'bytes': 1, 'failed': [], 'forgotten': True}
        self.server.merge.answers = {'delete': busy}
        self.server.scanning = False
        self.assertTrue(until(lambda: len(tries) == 1))
        self.assertTrue(until(lambda: self.queue.view()['queued_actions'] and self.queue.view()['queued_actions'][0]['blocker']['kind'] == 'book'))
        self.server.merge.busy_books.clear()
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 1))
        self.assertEqual(self.queue.view()['queue_outcomes'][0]['result'], 'done')

    def test_quit_and_updates_drop_the_queue_without_running_anything(self):
        self.server.scanning = True
        self.retry(0); self.delete(1)
        self.assertEqual(self.queue.count(), 2)
        self.queue.drop()
        self.server.scanning = False
        time.sleep(.1)
        self.assertEqual((self.queue.view()['queued_actions'], self.server.merge.calls), ([], []))
        # Control: a queue that is not dropped runs.
        self.server.scanning = True
        self.retry(2)
        self.server.closing = True  # Quit or an update has begun: the worker drops what waits
        self.server.scanning = False
        self.assertTrue(until(lambda: self.queue.view()['queued_actions'] == []))
        self.assertEqual(self.server.merge.calls, [])
        with self.assertRaises(ValueError):
            self.retry(3)
        self.server.closing = False
        self.server.scanning = True
        self.retry(3); self.server.scanning = False
        self.assertTrue(until(lambda: len(self.server.merge.calls) == 1), 'positive control: the same queue runs when nothing closes it')

    def test_outcomes_stay_until_acknowledged_or_a_day_passes(self):
        self.server.scanning = True
        self.retry(0); self.retry(1)
        self.server.scanning = False
        self.assertTrue(until(lambda: len(self.queue.view()['queue_outcomes']) == 2))
        first, second = self.queue.view()['queue_outcomes']
        self.queue.acknowledge([first['id']])
        self.assertEqual([o['id'] for o in self.queue.view()['queue_outcomes']], [second['id']])
        with mock.patch.object(action_queue.time, 'time', return_value=second['at'] + action_queue.KEEP + 1):
            self.assertEqual(self.queue.view()['queue_outcomes'], [])

    def test_retry_all_leaves_queued_presses_out(self):
        self.server.scanning = True
        self.retry(0); self.delete(1)
        self.assertEqual(self.queue.queued_jobs(), {self.job[0]})

    def test_a_full_queue_refuses_a_press_instead_of_dropping_one(self):
        self.server.scanning = True
        with mock.patch.object(action_queue, 'LIMIT', 2):
            self.retry(0); self.retry(1)
            with self.assertRaises(action_queue.QueueFull):
                self.retry(2)
        self.assertEqual(len(self.queue.view()['queued_actions']), 2)


if __name__ == '__main__':
    unittest.main()
