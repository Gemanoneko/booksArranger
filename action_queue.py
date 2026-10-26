"""Queued Retry, Repair and Delete book (0.22.1, backlog items 2 and 3; Judy's spec, section 1).

A press while another operation ran was refused ("Another operation is in progress.", or a scan's refusal) or waited
inside its request past the page's 15 s, which then said "Connection interrupted". Now Retry, Repair and Delete book are
accepted and queued: one queue, first in first out, one action at a time, held by the engine in memory only (Sergei,
Q1: Quit and updates drop it; nothing is deleted or started while he is away). An action runs when nothing blocks it,
through the same call its press makes, so every check runs again at run time: Retry and Repair the revision and the job,
Delete book the revision, the confirmed files and folders, shared files, Sorted and the source drive. A delete the
book or the files no longer match is cancelled before the first file. Each outcome is kept for the page until it
acknowledges it or 24 h pass, so a reload still shows it.

Blocker kinds (Judy 1.2; the page words them): 'scan' a library scan runs; 'retry_run' Retry all or Retry selected
runs (Retry and Repair only); 'book' the book itself is converting, queued for conversion or being researched (Delete
only); 'operation' another operation holds the app's operation lock (Delete only: Retry and Repair take no lock), or
another queued action runs. A fresh press while others wait goes to the back even when nothing blocks it."""
import copy
import threading
import time
import uuid

ACTIONS = ('retry', 'repair', 'delete')
KINDS = ('operation', 'scan', 'retry_run', 'approve_run', 'book')
KEEP = 24 * 3600     # an outcome nobody acknowledged is forgotten after a day
POLL = 0.5           # how often a blocked head is looked at again
LIMIT = 1000         # queued actions; a press beyond it is refused, never dropped silently


class QueueFull(ValueError):
    pass


def _free(lock):
    """True when no other thread holds lock (an RLock: the probe holds it for an instant, never waits)."""
    if lock is None:
        return True
    if lock.acquire(blocking=False):
        lock.release()
        return True
    return False


class ActionQueue:
    def __init__(self, server, poll=POLL):
        self.server = server
        self.poll = poll
        self.lock = threading.Lock()
        self.changed = threading.Condition(self.lock)
        self.items = []
        self.running = None
        self.outcomes = []
        self.thread = None
        self.closed = False

    # ------------------------------------------------------------------ what an action waits for
    def blocker(self, action, book_id):
        """The kind that keeps this action from running now, or None. Reads only: a thread probe, the scan flag, the
        Retry all run and, for Delete, the book's own jobs and research row."""
        server = self.server
        if server.scan_active():
            return 'scan'
        merge = server.merge
        if action in ('retry', 'repair'):
            run = merge.__dict__.get('_retry_all_run') if hasattr(merge, '__dict__') else None
            return 'retry_run' if isinstance(run, dict) and run.get('state') == 'running' else None
        import book_delete
        if book_delete.processing(merge, book_id):
            return 'book'
        if not _free(getattr(merge, 'operation_lock', None)):
            return 'operation'
        return None

    def waiting(self, action, book_id):
        """The kind a press made now would wait for, or None when it would run at once (the Delete preview's
        'blocked', Judy 1.5)."""
        kind = self.blocker(action, book_id)
        with self.lock:
            if kind is None and (self.items or self.running is not None):
                kind = self._head_kind()
        return kind

    def _head_kind(self):
        if self.running is not None:
            return 'operation'
        return self.items[0]['blocker'] if self.items else 'operation'

    # ------------------------------------------------------------------ presses
    def enqueue(self, action, book_id, title, args):
        """None when the queue is empty and nothing blocks the action: the caller runs it now, in its own request, as
        before. Otherwise the action is queued and the answer is {'queued': True, 'id', 'position', 'blocker'}. A second
        press of the same action for a book that already waits answers that action; another action for it is refused
        (one queued action per row, Judy 1.1)."""
        if action not in ACTIONS:
            raise ValueError('Only Retry, Repair and Delete book are queued')
        kind = self.blocker(action, book_id)
        with self.lock:
            if self.closed or self.server.closing:
                raise ValueError('Server is shutting down')
            same = next((item for item in self.items if item['book_id'] == book_id), None)
            if same is not None and same['action'] == action:
                return self._answer(same)
            if same is not None:
                raise ValueError('This book already has a queued action. Cancel it first.')  # one per row (Judy 1.1)
            if kind is None and not self.items and self.running is None:
                return None
            if len(self.items) >= LIMIT:
                raise QueueFull('Too many queued actions. Wait for some to run.')
            item = {'id': str(uuid.uuid4()), 'action': action, 'book_id': book_id, 'title': title, 'args': copy.deepcopy(args),
                    'queued_at': time.time(), 'blocker': kind or self._head_kind()}
            self.items.append(item)
            self._start()
            self.changed.notify_all()
            return self._answer(item)

    def _answer(self, item):
        return {'queued': True, 'id': item['id'], 'position': self.items.index(item) + 1, 'blocker': {'kind': item['blocker']}}

    def cancel(self, identity):
        """{'cancelled': True}, or None when it is no longer waiting (it started, ended or never was): too late."""
        with self.lock:
            for index, item in enumerate(self.items):
                if item['id'] == identity:
                    del self.items[index]
                    self.changed.notify_all()
                    return {'cancelled': True}
        return None

    def acknowledge(self, identities):
        with self.lock:
            wanted = set(identities)
            self.outcomes = [item for item in self.outcomes if item['id'] not in wanted]
        return {'acknowledged': True}

    def book_action(self, book_id):
        """The action queued or running for this book ('retry', 'repair', 'delete'), else None (Edit names is inert while
        one waits: one queued action per row, Judy 0.22.2 1.4)."""
        with self.lock:
            for item in ([self.running] if self.running is not None else []) + self.items:
                if item.get('book_id') == book_id:
                    return item['action']
        return None

    def queued_jobs(self):
        """Job ids of the queued Retry and Repair presses: Retry all leaves them out (Judy 1.3, 1.8)."""
        with self.lock:
            return {item['args'].get('job_id') for item in self.items if item['action'] in ('retry', 'repair')}

    def count(self):
        with self.lock:
            return len(self.items) + (1 if self.running is not None else 0)

    def view(self):
        """For /api/state: the waiting actions in order, the one running, and the outcomes not yet acknowledged."""
        with self.lock:
            self._prune()
            queued = [self._shown(item) | {'position': index + 1, 'blocker': {'kind': item['blocker']}} for index, item in enumerate(self.items)]
            running = None if self.running is None else self._shown(self.running)
            outcomes = copy.deepcopy(self.outcomes)
        return {'queued_actions': queued, 'queue_running': running, 'queue_outcomes': outcomes}

    @staticmethod
    def _shown(item):
        """What the page shows of an action: n is a delete's confirmed file count ("Deleting 8 files…")."""
        value = {key: item[key] for key in ('id', 'action', 'book_id', 'title')}
        if item['action'] == 'delete':
            value['n'] = len(item['args'].get('paths') or [])
        return value

    def _prune(self):
        cutoff = time.time() - KEEP
        self.outcomes = [item for item in self.outcomes if item['at'] >= cutoff]

    # ------------------------------------------------------------------ the worker
    def _start(self):
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._work, name='books-action-queue', daemon=True)
            self.thread.start()

    def drop(self):
        """Quit or Restart to update has begun: every waiting action is dropped without running (Q1; the update's
        confirm said so). The worker stays: a cancelled update keeps the app running with an empty queue."""
        with self.lock:
            self.items.clear()
            self.changed.notify_all()

    def close(self):
        """Quit, update and shutdown: the waiting actions are dropped without running (Q1). One already running finishes
        (it holds a control admission, which shutdown waits for)."""
        with self.lock:
            self.closed = True
            self.items.clear()
            self.changed.notify_all()
            thread = self.thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(1)

    def _work(self):
        while True:
            with self.lock:
                while not self.closed and not self.items:
                    self.changed.wait()
                if self.closed:
                    return
                if self.server.closing:
                    self.items.clear()  # Quit or an update has begun: dropped, never run
                    continue
                head = self.items[0]
            kind = self.blocker(head['action'], head['book_id'])
            with self.lock:
                if self.closed:
                    return
                if not self.items or self.items[0] is not head:
                    continue  # cancelled meanwhile
                if kind is not None:
                    for item in self.items:
                        item['blocker'] = kind
                    self.changed.wait(self.poll)
                    continue
                self.items.pop(0)
                self.running = head
            if not self._admit():
                with self.lock:
                    self.running = None
                continue
            try:
                outcome = self._run(head)
            finally:
                self._release()
            with self.lock:
                self.running = None
                if outcome is None and not self.closed:
                    head['blocker'] = self.blocker_after(head)
                    self.items.insert(0, head)  # a blocker came back between the look and the run: it waits again
                elif outcome is not None:
                    self.outcomes.append(outcome)
                    self._prune()
            invalidate = getattr(self.server, 'invalidate_status', None)
            if callable(invalidate):
                try:
                    invalidate()
                except Exception:
                    pass

    def blocker_after(self, item):
        try:
            return self.blocker(item['action'], item['book_id']) or 'operation'
        except Exception:
            return 'operation'

    def _admit(self):
        server = self.server
        with server.control_condition:
            if server.closing:
                return False
            server.merge_admissions += 1
            return True

    def _release(self):
        server = self.server
        with server.control_condition:
            server.merge_admissions -= 1
            server.control_condition.notify_all()

    def _run(self, item):
        """The outcome for the page, or None when a blocker refused it (it is queued again at the front)."""
        merge = self.server.merge
        args = item['args']
        outcome = {'id': item['id'], 'action': item['action'], 'book_id': item['book_id'], 'title': item['title'], 'at': time.time()}
        if item['action'] in ('retry', 'repair'):
            from audio_jobs import RetryRefused, RETRY_BOOK_CHANGED
            call = merge.retry_blocked_job if item['action'] == 'retry' else merge.repair_blocked_job
            try:
                result = call('Audiobooks', item['book_id'], args['revision'], args['job_id'])
            except RetryRefused as error:
                if self.server.closing or self.blocker(item['action'], item['book_id']):
                    return None
                text = str(error)
                code = 'changed' if text == RETRY_BOOK_CHANGED else getattr(error, 'cause', None) or 'refused'
                return outcome | {'result': 'refused', 'code': code, 'error': text}
            except ValueError as error:
                return outcome | {'result': 'refused', 'code': 'changed' if 'changed' in str(error) else 'refused'}
            except Exception:
                return outcome | {'result': 'refused', 'code': 'failed'}
            answer = {key: result.get(key) for key in ('position', 'queued_next', 'state', 'kind') if isinstance(result, dict) and key in result}
            return outcome | {'result': 'done', 'answer': answer}
        import book_delete
        try:
            result = merge.delete_book(item['book_id'], args['revision'], args['paths'], args.get('folders', []), 'delete')
        except book_delete.DeleteRefused as refusal:
            if refusal.code == 'busy' and not self.server.closing and self.blocker('delete', item['book_id']):
                return None
            payload = refusal.payload()
            if refusal.code == 'changed' and not self._listed(merge, item['book_id']):
                payload['code'] = 'not_listed'
            return outcome | {'result': 'refused', **{key: payload[key] for key in ('code', 'files', 'root') if key in payload}}
        except Exception:
            return outcome | {'result': 'unknown'}
        failed = [{'path': entry.get('path', ''), 'cause': entry.get('cause', 'other')} for entry in result.get('failed') or []]
        state = 'done' if result.get('forgotten') is True and not failed else 'partial' if failed else 'unknown'
        return outcome | {'result': state, 'deleted': result.get('deleted', 0), 'bytes': result.get('bytes', 0), 'failed': failed,
                          'folders': result.get('folders') or {'removed': 0, 'stayed': 0}, 'n': len(args['paths'])}

    @staticmethod
    def _listed(merge, book_id):
        try:
            merge.reviews._row('Audiobooks', book_id)
        except Exception:
            return False
        return True
