"""Queued Retry, Repair and Delete book (0.22.1, backlog items 2 and 3; Judy's spec, section 1).

A press while another operation ran was refused ("Another operation is in progress.", or a scan's refusal) or waited
inside its request past the page's 15 s, which then said "Connection interrupted". Now Retry, Repair and Delete book are
accepted and queued: one queue, first in first out, one action at a time, held by the engine (Sergei, Q1, 0.22.1: Quit
and updates dropped it; since 0.30.0 it is kept across a restart, below). An action runs when nothing blocks it,
through the same call its press makes, so every check runs again at run time: Retry and Repair the revision and the job,
Delete book the revision, the confirmed files and folders, shared files, Sorted and the source drive. A delete the
book or the files no longer match is cancelled before the first file. Each outcome is kept for the page until it
acknowledges it or 24 h pass, so a reload still shows it.

Blocker kinds (Judy 1.2; the page words them): 'scan' a library scan runs; 'retry_run' Retry all or Retry selected
runs (Retry and Repair only); 'book' the book itself is converting, queued for conversion or being researched (Delete
only); 'operation' another operation holds the app's operation lock (Delete only: Retry and Repair take no lock), or
another queued action runs. A fresh press while others wait goes to the back even when nothing blocks it.

0.30.0 (Sergei, Q4: remember): the waiting actions are kept in the catalog (QueueStore) and come back at the next start
(restore), across Quit, Restart to update and a crash. Quit and an update stop the queue (nothing runs while the app
closes) but no longer drop it. Each restored action runs its checks again when it runs, as always, and never starts the
conversion queue or the cleanup backlog itself (MergeService.restored_press): whether they start after a restart is the
restart intent's decision alone (Senua R-M1..R-M3, S-m8). A saved queue another session closed over (an older version run
in between, a rollback round trip) is dropped, each action with an outcome. Moves keep their own journal (book_move) and are
never saved here: Quit and an update cancel a queued move as the app closes (drop(): its journal says cancelled, the row
its own line). Only a cancel that fails there is left to the next start's move recovery (book_move.recover), which does not
run in retained-runtime mode (Senua's 0.30.0 review, M3)."""
import contextlib
import copy
import datetime
import json
import sqlite3
import sys
import threading
import time
import uuid

ACTIONS = ('retry', 'repair', 'delete',
           # Ruling 35 (Sergei 2026-10-26): every press that acts on a book is accepted, queued when something else is happening.
           'approve', 'convert', 'separate', 'scan_again', 'dismiss', 'copy', 'names', 'names_forget', 'scan_start', 'scan_resume',
           # Ruling 37 (the rest of ruling 35): historical cleanup and restore, route-only, wait for a scan and for audiobook work.
           'cleanup', 'restore',
           # Rulings 69 and 71h (Sergei 2026-10-29): Choose folder / Use computed folder, and the move of a finished book.
           'destination', 'move',
           # 0.30.0 item D: Join into one book (book_join), queued under its first part, holding every part's row.
           'join')
KINDS = ('operation', 'scan', 'retry_run', 'approve_run', 'book', 'loading', 'jobs', 'automatic')
# The presses a library scan holds back (their checks read the catalog the scan regroups), as their routes refused them.
SCAN_WAITS = ('retry', 'repair', 'delete', 'approve', 'convert', 'separate', 'scan_again', 'copy', 'join')
# Always queued, even with nothing in the way: their checks (every file probed and hashed) take the time a page must not
# wait for; the row shows it running and its outcome (ruling 35). A join regroups the catalog.
ALWAYS = ('approve', 'convert', 'move', 'join')
# Run by the server (run_queued): the same call the press makes, every check again at run time.
SERVER_RUN = ('approve', 'convert', 'separate', 'scan_again', 'dismiss', 'copy', 'names', 'names_forget', 'scan_start', 'scan_resume', 'cleanup', 'restore',
              'destination', 'move', 'join')
# Queued presses a join takes over: a part's Retry or Repair is cancelled by the join (Judy 8.5), never refused.
JOIN_CANCELS = ('retry', 'repair')


def parts_of(item):
    """The books a queued action holds: a join every part (its args' items), any other action its own book."""
    if item.get('action') == 'join':
        args = item.get('args') if isinstance(item.get('args'), dict) else {}
        return [entry.get('id') for entry in args.get('items') or [] if isinstance(entry, dict)] or [item.get('book_id')]
    return [item.get('book_id')]
KEEP = 24 * 3600     # an outcome nobody acknowledged is forgotten after a day
POLL = 0.5           # how often a blocked head is looked at again
APPROVAL_RECEIPT_LIMIT = 4096
APPROVAL_LIFETIME_MS = 60000
LIMIT = 1000         # queued actions; a press beyond it is refused, never dropped silently


class QueueFull(ValueError):
    pass


# 0.30.0: what is kept across a restart. Not 'move': a move has its own journal and recovery (book_move.recover).
PERSIST = tuple(action for action in ACTIONS if action != 'move')
WRITER = 'action-queue-v1'


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


class QueueStore:
    """The waiting actions in the catalog: one row each, in queue order, and one meta row (writer, last save, clean close,
    and the saving session's instance and version)."""

    def __init__(self, database, instance=None, version=None):
        self.database = database
        self.instance = instance if isinstance(instance, str) else None  # this session's (BrowserServer.instance)
        self.version = version if isinstance(version, str) else None

    @contextlib.contextmanager
    def _db(self):
        from scanner import connect  # the catalog's own guards (never during a storage relocation) and busy wait
        with connect(self.database, timeout=5) as db:
            db.execute('CREATE TABLE IF NOT EXISTS action_queue_saved(position INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, action TEXT NOT NULL, '
                       'book_id TEXT NOT NULL, title TEXT NOT NULL, args TEXT NOT NULL, queued_at REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS action_queue_meta(id INTEGER PRIMARY KEY CHECK(id=1), writer TEXT NOT NULL, saved_at TEXT NOT NULL, closed_at TEXT, '
                       'instance TEXT, version TEXT)')
            have = {row[1] for row in db.execute('PRAGMA table_info(action_queue_meta)')}
            for column in ('instance', 'version'):  # a meta row saved before these were kept (0.30.0 builds before m6)
                if column not in have:
                    db.execute('ALTER TABLE action_queue_meta ADD COLUMN %s TEXT' % column)
            yield db

    def save(self, items, closing=False):
        """Replace the saved queue with items (oldest first). closing: the app is closing cleanly now (after the shell recorded
        its shutdown), so a later shutdown record that is not ours means another session ran since."""
        with self._db() as db:
            db.execute('DELETE FROM action_queue_saved')
            db.executemany('INSERT INTO action_queue_saved VALUES(?,?,?,?,?,?,?)',
                           [(n, item['id'], item['action'], item['book_id'], item.get('title') or '', json.dumps(item['args'], ensure_ascii=False),
                             float(item.get('queued_at') or time.time())) for n, item in enumerate(items)])
            stamp = _now().isoformat()
            db.execute('INSERT INTO action_queue_meta(id,writer,saved_at,closed_at,instance,version) VALUES(1,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                       'writer=excluded.writer,saved_at=excluded.saved_at,closed_at=excluded.closed_at,instance=excluded.instance,version=excluded.version',
                       (WRITER, stamp, stamp if closing else None, self.instance, self.version))

    def load(self, previous=None):
        """(items, why_dropped or None). why_dropped: 'foreign' (not this format's writer) or 'stale': another session ran in
        between, as after a rollback to a version that keeps no queue. Seen two ways: a desktop shutdown was recorded after the
        queue was last saved or cleanly closed; or (Senua's 0.30.0 review, m6) previous, the ownership record this start found
        left behind ({'instance', 'version'}: the last owner did not close cleanly, it crashed or was ended), is another
        session's, of another version than the one that saved the queue. Such a session leaves no shutdown record."""
        with self._db() as db:
            meta = db.execute('SELECT writer,saved_at,closed_at,instance,version FROM action_queue_meta WHERE id=1').fetchone()
            rows = db.execute('SELECT id,action,book_id,title,args,queued_at FROM action_queue_saved ORDER BY position').fetchall()
            shutdown = None
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='desktop_shutdown'").fetchone():
                found = db.execute('SELECT at FROM desktop_shutdown WHERE id=1').fetchone()
                shutdown = found[0] if found else None
        items = []
        for identity, action, book_id, title, args, queued_at in rows:
            try:
                values = json.loads(args)
            except ValueError:
                continue
            if action in PERSIST and isinstance(values, dict):
                items.append({'id': identity, 'action': action, 'book_id': book_id, 'title': title, 'args': values, 'queued_at': queued_at})
        if not items:
            return [], None
        if meta is None or meta[0] != WRITER:
            return items, 'foreign'
        last = max(stamp for stamp in (meta[1], meta[2]) if stamp)
        try:
            if shutdown and datetime.datetime.fromisoformat(shutdown) > datetime.datetime.fromisoformat(last):
                return items, 'stale'
        except ValueError:
            return items, 'stale'
        if isinstance(previous, dict) and meta[3] and previous.get('instance') != meta[3] and previous.get('version') != meta[4]:
            return items, 'stale'  # m6: a session of another version ran after the save and ended without closing
        return items, None


def _free(lock):
    """True when no other thread holds lock (an RLock: the probe holds it for an instant, never waits)."""
    if lock is None:
        return True
    if lock.acquire(blocking=False):
        lock.release()
        return True
    return False


class ActionQueue:
    def __init__(self, server, poll=POLL, store=None):
        self.server = server
        self.poll = poll
        self.lock = threading.Lock()
        self.changed = threading.Condition(self.lock)
        self.items = []
        self.running = None
        self.outcomes = []
        self.approval_receipts = {}
        self.thread = None
        self.closed = False
        # 0.30.0: the catalog keeps the waiting actions (QueueStore). Default: the server's catalog; none without one.
        database = getattr(getattr(server, 'inventory', None), 'database', None)
        self.store = store if store is not None else QueueStore(database, getattr(server, 'instance', None), getattr(server, 'loaded_version', None)) \
            if isinstance(database, (str, bytes)) or hasattr(database, '__fspath__') else None
        self._save_lock = threading.Lock()
        # 0.30.0: (kind, item) -> the blocker object /api/state gives (background_work.explain_one), for a press's own answer
        # (the server sets it); without it a press's answer carries the kind alone.
        self.explainer = None
        self._version = 0
        self._saved = 0
        self.restored = False

    # ------------------------------------------------------------------ what an action waits for
    def blocker(self, action, book_id, held=0, job_id=None, parts=None):
        """The kind that keeps this action from running now, or None. Reads only: the loading flag, a thread probe, the scan
        flag, the Retry all run and, for Delete, the book's own jobs and research row. held: the control admissions the
        caller holds itself (the worker holds one while it runs an action: run_queued passes 1). job_id: the audiobook job
        the action is for (its args' job_id); a cleanup action's own source cleanup never blocks it. parts: a join's books
        (0.30.0 item D): it waits ('book') while one of them converts or its retry check runs, never aborting it."""
        server = self.server
        loading = getattr(server, 'loading', None)
        if loading is not None and not loading.finished or getattr(server, 'merge', None) is None:
            return 'loading'
        merge = server.merge
        if action in ('scan_start', 'scan_resume'):
            # Ruling 34: a scan waits for conversion to go idle; automatic processing owns discovery while it runs.
            automatic = getattr(merge, 'automatic', None)
            if automatic is not None and automatic.status().get('state') in ('Running', 'Stopping'):
                return 'automatic'
            if server.scan_active():
                return 'scan'
            # 0.30.0 (Senua S-m9, overlap half): nor beside a source check pass. A pass refuses to start beside a scan; a scan
            # started during a pass regrouped the books the pass was testing.
            if getattr(merge, '__dict__', {}).get('_source_checking'):
                return 'operation'
            try:
                if server.jobs_active():
                    return 'jobs'
            except Exception:
                return 'jobs'
            # Senua's 0.22.2 review, M4: the direct route refuses a scan beside any other admitted request (a Delete, an
            # Approve, a Retry) and beside the retention worker's recovery purge; queued, the scan waits for them.
            if getattr(server, 'merge_admissions', 0) > held:
                return 'operation'
            return None
        if action in SCAN_WAITS and server.scan_active():
            return 'scan'
        if action == 'join':
            import book_join
            return 'book' if book_join.busy(merge, parts or [book_id]) else None
        if action in ('cleanup', 'restore'):
            # Historical cleanup removes originals and restore puts them back: never beside a scan or audiobook work (their
            # engine checks); cleanup also waits for queued books and for other source cleanups (it is finite and alone).
            if server.scan_active():
                return 'scan'
            jobs, cleanup = getattr(merge, 'jobs', None), getattr(merge, 'cleanup', None)
            alive = lambda thread: thread is not None and thread.is_alive()
            if alive(getattr(jobs, '_thread', None)) or alive(getattr(cleanup, 'thread', None)):
                return 'jobs'
            if action == 'cleanup':
                # 0.30.0: a source cleanup is keyed by its audiobook job. Retry cleanup is queued under the book's candidate
                # id with the job in its args, so comparing the candidate id never matched and the book's own cleanup
                # blocked it; Clean up (historical) is queued under the job id itself.
                own = job_id or book_id
                try:
                    if jobs is not None and any(j['state'] in ('pending', 'running') for j in jobs.status()['jobs']):
                        return 'jobs'
                    if cleanup is not None and any(c['job_id'] != own and c['state'] in ('waiting', 'checking', 'removing', 'pausing', 'paused')
                                                   for c in cleanup.status()):
                        return 'jobs'
                except Exception:
                    return 'jobs'  # unknown: it waits, never removes originals beside work it can't see
            return None
        if action == 'move':
            # A move (ruling 69) never runs beside its own book's conversion, a source cleanup or another operation; it
            # changes where the audiobook is, which they read under their own leases.
            import book_delete
            if book_delete.processing(merge, book_id):
                return 'book'
            cleanup = getattr(merge, 'cleanup', None)
            alive = lambda thread: thread is not None and thread.is_alive()
            if cleanup is not None and (alive(getattr(cleanup, 'thread', None)) or getattr(cleanup, 'current', None)):
                return 'jobs'
            if not _free(getattr(merge, 'operation_lock', None)):
                return 'operation'
            return None
        if action in ('names', 'names_forget'):
            job = merge._names_job(book_id) if hasattr(merge, '_names_job') else {'state': 'none'}
            return 'book' if job.get('state') == 'running' else None
        if action not in ('retry', 'repair', 'delete', 'copy'):
            return None
        if action in ('retry', 'repair'):
            run = merge.__dict__.get('_retry_all_run') if hasattr(merge, '__dict__') else None
            return 'retry_run' if isinstance(run, dict) and run.get('state') == 'running' else None
        import book_delete
        if book_delete.processing(merge, book_id):
            return 'book'
        if not _free(getattr(merge, 'operation_lock', None)):
            return 'operation'
        return None

    def waiting(self, action, book_id, parts=None):
        """The kind a press made now would wait for, or None when it would run at once (the Delete preview's
        'blocked', Judy 1.5; the join dialog's, 0.30.0)."""
        kind = self.blocker(action, book_id, parts=parts)
        with self.lock:
            if kind is None and (self.items or self.running is not None):
                kind = self._head_kind()
        return kind

    def _head_kind(self):
        if self.running is not None:
            return 'operation'
        return (self.items[0]['blocker'] or 'operation') if self.items else 'operation'  # behind a head that waits for nothing: the head

    # ------------------------------------------------------------------ presses
    def enqueue(self, action, book_id, title, args, always=False, receipt=None):
        """None when the queue is empty and nothing blocks the action: the caller runs it now, in its own request, as
        before. Otherwise the action is queued and the answer is {'queued': True, 'id', 'position', 'blocker'}. A second
        press of the same action for a book that already waits answers that action; another action for it is refused
        (one queued action per row, Judy 1.1)."""
        if action not in ACTIONS:
            raise ValueError('Only Retry, Repair and Delete book are queued')
        pressed = {'action': action, 'book_id': book_id, 'args': args}
        kind = self.blocker(action, book_id, job_id=args.get('job_id') if isinstance(args, dict) else None, parts=parts_of(pressed))
        with self.lock:
            if self.closed or self.server.closing:
                raise ValueError('Server is shutting down')
            if receipt is not None:
                key, expires = receipt
                now = self._receipt_clock(expires)
                if expires <= now:raise ValueError('Approval submission expired. Try again.')
                old = self.approval_receipts.get(key)
                if old is not None:
                    if old[:3] != (book_id, action, expires) or old[3] is None:
                        raise ValueError('Approval submission was closed. Try again.')
                    answer=self._approval_answer(old[3])
                    if answer.get('unknown'):raise ValueError('That approval already reached the queue. Check the book before trying again.')
                    return answer
                self._receipt_room()
            same = next((item for item in self.items if item['book_id'] == book_id and (action != 'join' or item['action'] == 'join')), None)
            if action in ('approve','convert') and self.running is not None and self.running['book_id']==book_id:
                same=self.running
            # 0.30.0 item D: a join holds every part's row; a part's queued Retry or Repair is the join's to cancel.
            books = set(parts_of(pressed))
            held = [item for item in self.items + ([self.running] if self.running is not None else [])
                    if item is not same and books & set(parts_of(item)) and not (action == 'join' and item['action'] in JOIN_CANCELS)]
            if held and not (same is not None and same['action'] == action):
                raise ValueError('This book already has a queued action. Cancel it first.')  # one per row (Judy 1.1)
            if same is not None and same['action'] == action:
                if action in ('approve','convert') and same['args'] != args:
                    raise ValueError('An approval with different choices is already queued or running for this book.')
                if action == 'join' and same['args'] != args:
                    raise ValueError('This book already has a queued action. Cancel it first.')
                if receipt is not None:self.approval_receipts[key]=(book_id,action,expires,same['id'])
                return self._answer(same)
            if same is not None:
                raise ValueError('This book already has a queued action. Cancel it first.')  # one per row (Judy 1.1)
            if kind is None and not self.items and self.running is None and not (always or action in ALWAYS):
                return None
            if len(self.items) >= LIMIT:
                raise QueueFull('Too many queued actions. Wait for some to run.')
            item = {'id': str(uuid.uuid4()), 'action': action, 'book_id': book_id, 'title': title, 'args': copy.deepcopy(args),
                    'queued_at': time.time(), 'blocker': kind or (self._head_kind() if self.items or self.running is not None else None)}
            # QA D1 (0.30.0): nothing blocks it and nothing is ahead (an always-queued Approve or Join): it waits for nothing.
            # It named the queue's own 'operation', and the answer then named the action itself as what it waited for.
            if receipt is not None:self.approval_receipts[key]=(book_id,action,expires,item['id'])
            self.items.append(item)
            self._start()
            self.changed.notify_all()
            answer = self._answer(item)
        self._persist()
        return self._explained(answer, item)

    def _explained(self, answer, item):
        explainer = self.explainer
        if not callable(explainer) or not isinstance(answer.get('blocker'), dict):
            return answer
        try:
            return answer | {'blocker': explainer(answer['blocker'].get('kind'), item)}
        except Exception:
            return answer  # the kind alone: the page's fallback wording

    def _answer(self, item):
        if item is self.running:return {'queued':True,'id':item['id'],'running':True}
        return {'queued': True, 'id': item['id'], 'position': self.items.index(item) + 1, 'blocker': {'kind': item['blocker']} if item['blocker'] else None}

    def _receipt_clock(self, expires):
        now = int(time.time()*1000)
        if type(expires) is not int or expires > now+APPROVAL_LIFETIME_MS:
            raise ValueError('Invalid approval submission deadline')
        self.approval_receipts = {key:value for key,value in self.approval_receipts.items() if value[2]+APPROVAL_LIFETIME_MS > now}
        return now

    def _receipt_room(self):
        if len(self.approval_receipts)>=APPROVAL_RECEIPT_LIMIT:
            raise QueueFull('Too many approval submissions. Wait and try again.')

    def _approval_answer(self, identity):
        if identity is None:return {'queued':False}
        for item in self.items:
            if item['id']==identity:return self._answer(item)
        if self.running is not None and self.running['id']==identity:return self._answer(self.running)
        outcome=next((item for item in self.outcomes if item['id']==identity),None)
        if outcome is not None:return {'queued':True,'id':identity,'outcome':copy.deepcopy(outcome)}
        return {'unknown':True}

    def reconcile_approval(self, key, book_id, action, expires):
        """Read the exact receipt, or close the still-live submission before it can arrive late."""
        with self.lock:
            now=self._receipt_clock(expires)
            receipt=self.approval_receipts.get(key)
            if receipt is not None:
                if receipt[:3]!=(book_id,action,expires):raise ValueError('Approval receipt does not match')
                return self._approval_answer(receipt[3])
            if expires<=now:return {'unknown':True}
            self._receipt_room()
            self.approval_receipts[key]=(book_id,action,expires,None)
            return {'queued':False}

    def cancel(self, identity):
        """{'cancelled': True}, or None when it is no longer waiting (it started, ended or never was): too late."""
        with self.lock:
            found = next((index for index, item in enumerate(self.items) if item['id'] == identity), None)
            if found is None:
                return None
            item = self.items.pop(found)
            self.changed.notify_all()
        self._persist()
        self._forget_move(item)
        return {'cancelled': True}

    def _forget_move(self, item):
        """A queued move taken back (Cancel, Quit, an update): its journal says cancelled, so the row stops saying queued."""
        if item.get('action') != 'move':
            return
        merge = getattr(self.server, 'merge', None)
        try:
            if merge is not None and hasattr(merge, 'cancel_move'):
                merge.cancel_move(item['args'].get('move_id'))
        except Exception:
            pass  # the next start reconciles a queued move as cancelled (book_move.recover)

    def acknowledge(self, identities):
        with self.lock:
            wanted = set(identities)
            self.outcomes = [item for item in self.outcomes if item['id'] not in wanted]
        return {'acknowledged': True}

    def book_action(self, book_id):
        """The action queued or running for this book ('retry', 'repair', 'delete'), else None (Edit names is inert while
        one waits: one queued action per row, Judy 0.22.2 1.4). A join holds every part's row."""
        with self.lock:
            for item in ([self.running] if self.running is not None else []) + self.items:
                if book_id in parts_of(item):
                    return item['action']
        return None

    def book_actions(self):
        """{book id: action} of every queued or running action (a join under each of its parts), for the join dialog."""
        with self.lock:
            found = {}
            for item in ([self.running] if self.running is not None else []) + self.items:
                for book in parts_of(item):
                    found.setdefault(book, item['action'])
        return found

    def drop_presses(self, book_ids, actions=JOIN_CANCELS):
        """0.30.0 item D: a join that ran takes its parts' queued Retry and Repair presses out of the queue (Judy 8.5: they
        are cancelled, counted in the join's outcome). Returns how many."""
        wanted = set(book_ids)
        with self.lock:
            dropped = [item for item in self.items if item['action'] in actions and item['book_id'] in wanted]
            if not dropped:
                return 0
            self.items = [item for item in self.items if item not in dropped]
            self.changed.notify_all()
        self._persist()
        return len(dropped)

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
            queued = [self._shown(item) | {'position': index + 1, 'blocker': {'kind': item['blocker']} if item['blocker'] else None} for index, item in enumerate(self.items)]
            running = None if self.running is None else self._shown(self.running) | self._progress()
            outcomes = copy.deepcopy(self.outcomes)
        return {'queued_actions': queued, 'queue_running': running, 'queue_outcomes': outcomes}

    @staticmethod
    def _shown(item):
        """What the page shows of an action: n is a delete's confirmed file count ("Deleting 8 files…")."""
        value = {key: item[key] for key in ('id', 'action', 'book_id', 'title')}
        if item['action'] in ('delete', 'copy'):
            value['n'] = len(item['args'].get('paths') or [])
        if item['action'] == 'join':
            value['parts'] = parts_of(item)  # 0.30.0 item D: every part's row shows the queued join
            value['n'] = len(value['parts'])
        if item.get('restored'):
            value['restored'] = True  # 0.30.0: queued before the last restart
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
        """Quit or Restart to update has begun: nothing waiting runs while the app closes (the worker waits while the server
        closes). 0.30.0 (Sergei, Q4: remember): the waiting actions are kept, saved, for the next start, and a cancelled
        update runs them as before. Only a queued move is taken back here: its journal says cancelled, as before."""
        with self.lock:
            moves = [item for item in self.items if item['action'] == 'move']
            self.items = [item for item in self.items if item['action'] != 'move']
            self.changed.notify_all()
        if moves or self.unsaved():
            self._persist()  # 0.30.0 item F: nothing changed, nothing written (close() saves the queue once, with its stamp)
        for item in moves:
            self._forget_move(item)

    def close(self):
        """Quit, update and shutdown: nothing waiting runs any more; the queue is saved with a clean-close stamp (after the
        shell recorded its shutdown), so the next start takes it back. One already running finishes (it holds a control
        admission, which shutdown waits for); if it comes back to wait (refused while closing), it is saved in its place.

        Senua's 0.30.0 review, M1: this cleared the waiting actions after saving them. A safe stop (Quit anyway, a Windows
        sign-out, the shell's pipe closing) closes the queue while an action may still run; when that one came back to wait,
        the worker put it into the emptied list and saved it alone, over the others (1 of 3 kept). They stay in memory now
        (closed: nothing runs them), and every save after close is a clean-close one (_persist)."""
        with self.lock:
            self.closed = True
            self.changed.notify_all()
            thread = self.thread
        self._persist(closing=True)
        if thread is not None and thread is not threading.current_thread():
            thread.join(1)

    # ------------------------------------------------------------------ kept across a restart (0.30.0)
    def _persist(self, closing=False):
        """Save the waiting actions (in order, moves left out). Never raises: a catalog that cannot take it now is tried
        again by the worker; the queue in memory is unchanged either way."""
        if self.store is None or not self.restored:
            return  # never before restore(): it would write over the queue the last session saved
        with self.lock:
            self._version += 1
            version = self._version
            items = [copy.deepcopy(item) for item in self.items if item['action'] in PERSIST]
            closing = closing or self.closed  # M1: once closed, a save keeps the clean-close stamp
        with self._save_lock:
            if version < self._saved:
                return  # a newer snapshot is already saved
            try:
                self.store.save(items, closing=closing)
                self._saved = version
            except Exception as error:
                try:
                    print(f'Books Arranger could not save the queued actions: {error}', file=sys.stderr, flush=True)
                except Exception:
                    pass

    def unsaved(self):
        with self.lock:
            return self.store is not None and self.restored and self._saved < self._version

    def restore(self):
        """0.30.0: the actions saved before the last close come back, oldest first, ahead of any press made since (while
        loading). Each runs every check again when its turn comes and never starts the queue itself (restored). A saved queue
        another session closed over ('stale') or in another format ('foreign') is dropped, each action with an outcome (code
        restore_stale, restore_foreign). Returns the number taken back. Once per server."""
        if self.store is None or self.restored:
            return 0
        previous = getattr(self.server, 'previous_owner', None)  # m6: the ownership record this start found left behind
        try:
            saved, why = self.store.load(previous=previous) if isinstance(previous, dict) else self.store.load()
        except Exception as error:
            # Not marked restored: nothing is saved over a queue that could not be read (this launch keeps it in memory).
            try:
                print(f'Books Arranger could not read the queued actions saved before: {error}', file=sys.stderr, flush=True)
            except Exception:
                pass
            return 0
        self.restored = True
        now = time.time()
        with self.lock:
            kept = []
            if why:
                for item in saved:
                    self.outcomes.append({'id': item['id'], 'action': item['action'], 'book_id': item['book_id'], 'title': item['title'], 'at': now,
                                          'result': 'refused', 'code': 'restore_' + why})
            else:
                taken = {entry['book_id'] for entry in self.items} | ({self.running['book_id']} if self.running is not None else set())
                kept = [dict(item, restored=True, blocker='loading') for item in saved if item['book_id'] not in taken]
                # m6: a saved press for a book that got a new press while loading (one action per row) is not taken back,
                # and says so with an outcome, as a dropped saved queue does (code restore_replaced; it was dropped silently).
                for item in saved:
                    if item['book_id'] in taken:
                        self.outcomes.append({'id': item['id'], 'action': item['action'], 'book_id': item['book_id'], 'title': item['title'], 'at': now,
                                              'result': 'refused', 'code': 'restore_replaced'})
                self.items[0:0] = kept
            self._prune()
            if kept:
                self._start()
                self.changed.notify_all()
        self._persist()
        return len(kept)

    def _work(self):
        while True:
            with self.lock:
                while not self.closed and not self.items:
                    # A save the catalog refused (a cancelled last action, say) is tried again every poll until it lands.
                    self.changed.wait(self.poll if self.store is not None and self._saved < self._version else None)
                    if self.store is not None and self._saved < self._version:
                        break
                if self.closed:
                    return
                if not self.items or self.server.closing:
                    head = None
                    if self.server.closing:
                        self.changed.wait(self.poll)  # Quit or an update has begun: nothing runs; the queue is kept (0.30.0)
                else:
                    head = self.items[0]
            if self.unsaved():
                self._persist()  # a save the catalog refused is tried again
            if head is None:
                continue
            kind = self.item_blocker(head)
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
            self._persist()  # it runs now: an action is never run twice after a crash
            if not self._admit():
                with self.lock:
                    self.running = None
                    self.items.insert(0, head)  # the app began closing meanwhile: it waits, kept for the next start
                self._persist()
                continue
            try:
                outcome = self._run(head)
                blocker = self.blocker_after(head) if outcome is None else None
                with self.lock:
                    self.running = None
                    if outcome is None:
                        head['blocker'] = blocker
                        self.items.insert(0, head)  # a blocker came back between the look and the run: it waits again
                    else:
                        self.outcomes.append(outcome)
                        self._prune()
                if outcome is None:
                    # M1: saved before the admission is released, so a shutdown (which waits for admissions) never ends
                    # the process between the action coming back to wait and its save.
                    self._persist()
            finally:
                self._release()
            invalidate = getattr(self.server, 'invalidate_status', None)
            if callable(invalidate):
                try:
                    invalidate()
                except Exception:
                    pass

    def item_blocker(self, item, held=0):
        """blocker() for a queued action, with the job its args name."""
        args = item.get('args')
        return self.blocker(item['action'], item['book_id'], held=held, job_id=args.get('job_id') if isinstance(args, dict) else None, parts=parts_of(item))

    def blocker_after(self, item):
        """The blocker of an action that came back to wait, read while it still holds its own admission (held=1, M1)."""
        try:
            return self.item_blocker(item, held=1) or 'operation'
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

    def _progress(self):
        """0.30.0 (Futaba's QA A): how far the running press has got, as its worker thread reported it (press_progress):
        {'done', 'total', 'unit'}, or nothing."""
        import press_progress
        found = press_progress.read(self.__dict__.get('_runner_ident'))
        return {'done': found[0], 'total': found[1], 'unit': found[2]} if found else {}

    def _run(self, item):
        """The outcome for the page, or None when a blocker refused it (it is queued again at the front)."""
        import press_progress
        self._runner_ident = threading.get_ident()
        press_progress.clear()
        try:
            return self._run_counted(item)
        finally:
            press_progress.clear()

    def _run_counted(self, item):
        merge = self.server.merge
        # 0.30.0: an action restored from before a restart does its own work only; the conversion queue and the cleanup
        # backlog start after a restart only by the restart intent's rules (Senua R-M1..R-M3, S-m8).
        quiet = getattr(merge, 'restored_press', None) if item.get('restored') else None
        with quiet() if callable(quiet) else contextlib.nullcontext():
            return self._run_now(item, merge)

    def _run_now(self, item, merge):
        args = item['args']
        outcome = {'id': item['id'], 'action': item['action'], 'book_id': item['book_id'], 'title': item['title'], 'at': time.time()}
        if item['action'] in SERVER_RUN:
            try:
                found = self.server.run_queued(item)
            except Exception as error:
                return outcome | {'result': 'refused', 'code': 'failed', 'error': (str(error) or type(error).__name__)[:300]}
            return None if found is None else outcome | found
        if item['action'] in ('retry', 'repair'):
            from audio_jobs import RetryRefused, RETRY_BOOK_CHANGED
            call = merge.retry_blocked_job if item['action'] == 'retry' else merge.repair_blocked_job
            try:
                result = call('Audiobooks', item['book_id'], args['revision'], args['job_id'])
            except RetryRefused as error:
                if self.server.closing or self.item_blocker(item):
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
            # The engine's sentence too: a cause the page has no line for is shown in its own words (S6), never bare.
            return outcome | {'result': 'refused', **{key: payload[key] for key in ('code', 'files', 'root', 'message') if key in payload}}
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
