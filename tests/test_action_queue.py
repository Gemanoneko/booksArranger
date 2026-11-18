"""Queued Retry, Repair and Delete book (0.22.1, backlog items 2 and 3; Judy's spec, section 1).

A press while another operation runs is accepted and queued, not refused: one queue, first in first out, one action at
a time, kept across a restart since 0.30.0 (PersistentQueueTests). The run goes through the same call the press makes, so its checks
run again; each outcome is kept until the page acknowledges it. Stub services and a stub server; the real delete and
the HTTP routes are in test_book_delete.QueuedDeleteTests and test_web."""
import threading, time, unittest, uuid
from types import SimpleNamespace
from unittest import mock

import action_queue
import audio_jobs
import book_delete
from action_queue import ActionQueue


class DurableDecisionLedgerTests(unittest.TestCase):
    def setUp(self):
        import pathlib,tempfile
        from durable_decisions import Decisions
        self.temp=tempfile.TemporaryDirectory(prefix='durable-decisions-');self.addCleanup(self.temp.cleanup)
        self.database=pathlib.Path(self.temp.name)/'catalog.sqlite3';self.store=Decisions(self.database)
        self.book=str(uuid.uuid4());self.fp='a'*64

    def accept(self,action='names',effects=None,predecessor=None,**extra):
        options={'request_id':str(uuid.uuid4()),'book_id':self.book,'action':action,'revision':1,
                 'fingerprint':self.fp,'payload':{'value':'private choice'},'effects':effects or ['names.title'],
                 'predecessor':predecessor,'current_revision':1,'current_fingerprint':self.fp}
        options.update(extra);return self.store.accept(**options)

    def finish(self,request_id,generation,label='saved'):
        from scanner import connect
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE')
            self.store.application(request_id,generation).commit_step(db,'final',{'value':'private choice'},{'outcome':label},final=True,applied_revision=2)

    def test_acceptance_is_independent_of_worker_locks_and_survives_reopen(self):
        from durable_decisions import Decisions
        held=threading.Lock();held.acquire()
        try:answer=self.accept()
        finally:held.release()
        self.assertEqual(answer['state'],'accepted')
        reopened=Decisions(self.database).get(answer['request_id'],include_payload=True)
        self.assertEqual(reopened['payload'],{'value':'private choice'})

    def test_acceptance_does_not_wait_for_actual_merge_review_group_or_queue_locks(self):
        from durable_decisions import Decisions
        from test_merge_service import MergeTests
        fixture=MergeTests();fixture.setUp();self.addCleanup(fixture.tearDown)
        row=fixture.inv.candidates('Audiobooks')['rows'][0]
        store=Decisions(fixture.inv.database);entered=threading.Event();release=threading.Event()
        def hold():
            with fixture.service.operation_lock,fixture.service.reviews.lock,fixture.inv.group_lock,fixture.service.jobs._lock:
                entered.set();release.wait(5)
        holder=threading.Thread(target=hold);holder.start();self.assertTrue(entered.wait(2))
        try:
            start=time.monotonic()
            saved=store.accept(request_id=str(uuid.uuid4()),book_id=row['id'],action='names',revision=row['revision'],fingerprint=row['fingerprint'],
                               payload={'names':{'title':'Saved despite unrelated work'}},effects=['names.title'],
                               current_revision=row['revision'],current_fingerprint=row['fingerprint'])
            self.assertLess(time.monotonic()-start,1.0);self.assertTrue(holder.is_alive());self.assertEqual(saved['state'],'accepted')
        finally:release.set();holder.join(5)
        self.assertFalse(holder.is_alive())

    def test_sqlite_writer_contention_is_bounded_and_same_request_reconciles_once(self):
        import sqlite3
        from scanner import connect
        request=str(uuid.uuid4())
        with connect(self.database) as writer:
            writer.execute('BEGIN IMMEDIATE');start=time.monotonic()
            with self.assertRaises(sqlite3.OperationalError):self.accept(request_id=request)
            self.assertLess(time.monotonic()-start,1.0)
            self.assertIsNone(self.store.get(request),'A failed commit cannot claim durable acceptance')
        first=self.accept(request_id=request);second=self.accept(request_id=request)
        self.assertEqual(first,second);self.assertEqual(len(self.store.pending()),1)

    def test_disjoint_names_and_tracks_are_both_preserved_under_new_head_fence(self):
        from durable_decisions import DecisionChanged
        from scanner import connect
        names=self.accept();old_head=self.store.head(self.book)
        tracks=self.accept('tracks',['tracks'],names['request_id']);head=self.store.head(self.book)
        self.assertEqual(set(head['effects'].values()),{names['request_id'],tracks['request_id']})
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE')
            with self.assertRaises(DecisionChanged):self.store.application(names['request_id'],old_head['generation']).check(db)
        self.finish(names['request_id'],head['generation']);self.finish(tracks['request_id'],head['generation'])
        self.assertEqual(self.store.get(names['request_id'])['state'],'applied')
        self.assertEqual(self.store.get(tracks['request_id'])['state'],'applied')

    def test_incompatible_late_request_is_saved_without_moving_valid_head(self):
        first=self.accept();second=self.accept('tracks',['tracks'],first['request_id']);head=self.store.head(self.book)
        late=self.accept('review',['review.topic'],first['request_id'])
        self.assertEqual(late['state'],'needs_review');self.assertEqual(self.store.head(self.book),head)
        self.assertIn(second['request_id'],{item['request_id'] for item in self.store.pending()})

    def test_transaction_rollback_has_no_effect_or_step_receipt_then_recovery_applies_once(self):
        from scanner import connect
        accepted=self.accept();scope=self.store.application(accepted['request_id'],self.store.head(self.book)['generation'])
        with connect(self.database) as db:db.execute('CREATE TABLE private_values(value TEXT)')
        with self.assertRaisesRegex(RuntimeError,'private crash'):
            with connect(self.database) as db:
                db.execute('BEGIN IMMEDIATE');db.execute("INSERT INTO private_values VALUES('chosen')")
                scope.commit_step(db,'names',{'field':'title'},{'press_id':'owned'})
                raise RuntimeError('private crash')
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE')
            self.assertIsNone(scope.prior_step(db,'names',{'field':'title'}));self.assertEqual(db.execute('SELECT count(*) FROM private_values').fetchone()[0],0)
            db.execute("INSERT INTO private_values VALUES('chosen')")
            scope.commit_step(db,'names',{'field':'title'},{'press_id':'owned'})
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE');self.assertEqual(scope.prior_step(db,'names',{'field':'title'}),{'press_id':'owned'})
            self.assertEqual(db.execute('SELECT count(*) FROM private_values').fetchone()[0],1)

    def test_applied_payload_is_purged_but_request_reconciliation_and_conflict_guard_survive(self):
        from durable_decisions import DecisionChanged
        accepted=self.accept();self.finish(accepted['request_id'],self.store.head(self.book)['generation'])
        self.assertEqual(self.store.purge_fulfilled(),1);saved=self.store.get(accepted['request_id'],include_payload=True)
        self.assertIsNone(saved['payload']);self.assertEqual(saved['result'],{'outcome':'saved'})
        duplicate=self.accept(request_id=accepted['request_id']);self.assertEqual(duplicate['state'],'applied')
        with self.assertRaises(DecisionChanged):self.accept(request_id=accepted['request_id'],payload={'value':'different'})

    def test_save_then_approve_waits_for_its_captured_names_receipt(self):
        names=self.accept();approval=self.accept('approve',['approval'],names['request_id'])
        self.assertNotIn(approval['request_id'],{item['request_id'] for item in self.store.pending()})
        self.finish(names['request_id'],self.store.head(self.book)['generation'])
        self.assertIn(approval['request_id'],{item['request_id'] for item in self.store.pending()})
        newer=self.accept('tracks',['tracks'],approval['request_id'])
        self.assertEqual(newer['state'],'accepted');self.assertEqual(self.store.get(approval['request_id'])['state'],'needs_review')

    def test_approve_overlapping_names_does_not_depend_on_its_superseded_owner(self):
        names=self.accept(effects=['names.title','names.series'])
        approval=self.accept('approve',['approval','names.title','names.series'],names['request_id'])
        self.assertEqual(self.store.get(names['request_id'])['state'],'superseded')
        self.assertIn(approval['request_id'],{item['request_id'] for item in self.store.pending()})

    def test_approve_still_waits_for_disjoint_predecessor_names(self):
        names=self.accept(effects=['names.title','names.series'])
        approval=self.accept('approve',['approval','names.title'],names['request_id'])
        self.assertEqual(self.store.get(names['request_id'])['state'],'accepted')
        self.assertNotIn(approval['request_id'],{item['request_id'] for item in self.store.pending()})
        self.finish(names['request_id'],self.store.head(self.book)['generation'])
        self.assertIn(approval['request_id'],{item['request_id'] for item in self.store.pending()})

    def test_new_approval_keeps_disjoint_names_from_an_older_approval_without_replaying_its_approve(self):
        from scanner import connect
        first=self.accept('approve',['approval','names.series'],payload={'names':{'series':'Accepted earlier series'}})
        second=self.accept('approve',['approval','names.title'],first['request_id'],payload={'title':'Accepted later title'})
        pending=self.store.pending();self.assertEqual([item['request_id'] for item in pending],[first['request_id']])
        self.assertEqual(pending[0]['active_effects'],['names.series'])
        scope=self.store.application(first['request_id'],self.store.head(self.book)['generation'])
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE');scope.bind_names(db,self.book,self.fp,{'series':'Accepted earlier series'})
            scope.commit_step(db,'names',{}, {'outcome':'names_saved_approval_superseded'},final=True,applied_revision=1)
        self.assertEqual([item['request_id'] for item in self.store.pending()],[second['request_id']])

    def test_approval_enqueue_and_applied_receipt_share_one_commit(self):
        import json
        import groups
        from durable_decisions import Application
        from scanner import connect
        queue=audio_jobs.AudioJobs(self.database,None,lambda value:True,lambda value:True);self.addCleanup(queue.close)
        accepted=self.accept('approve',['approval'],payload={'author':'William Gibson'});scope=self.store.application(accepted['request_id'],self.store.head(self.book)['generation'])
        checkpoint={'automatic_pending':{'matcher_version':'private','work_id':'private'},'metadata_approved':True}
        approved={'metadata_approved':True,'automatic_approval':{'matcher_version':'private','work_id':'private'}}
        with connect(self.database) as db:
            groups.setup(db)
            db.execute('INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence,review) VALUES(?,?,?,?,?,?,?)',(self.book,str(self.database.parent),self.book,1,self.fp,'{}','{}'))
            db.execute('CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT)')
            db.execute('INSERT INTO candidate_context VALUES(?,?,?)',(self.book,1,json.dumps(checkpoint)))
        manifest={'job_id':str(uuid.uuid4()),'candidate_id':self.book,'candidate_revision':1,
                  'sources':[{'path':str(self.database.parent/'private.mp3'),'sha256':'b'*64,'fingerprint':{'size':1,'modified':'1'}}],
                  'metadata':{'title':'Private book'},'destination':str(self.database.parent/'private.m4b'),'profile':'private','evidence':{},'cover':{}}
        import local_identity
        args={'approval_context':(self.book,1,checkpoint,approved),'decision':scope,
              'decision_rules':[{'kind':'same_as','credit':'Уильям Гибсон','target':local_identity.surname_first('William Gibson')[0],'title':'Private book'}]}
        with mock.patch.object(Application,'commit_step',side_effect=RuntimeError('private enqueue commit interruption')):
            with self.assertRaisesRegex(RuntimeError,'private enqueue commit interruption'):queue.enqueue(manifest,**args)
        with connect(self.database) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM audio_jobs').fetchone()[0],0)
            self.assertEqual(json.loads(db.execute('SELECT data FROM candidate_context').fetchone()[0]),checkpoint)
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='author_rules'").fetchone(),'Rule schema/write must roll back with the failed receipt')
        self.assertEqual(self.store.get(accepted['request_id'])['state'],'accepted')
        self.assertEqual(queue.enqueue(manifest,**args),manifest['job_id'])
        receipt=self.store.get(accepted['request_id']);self.assertEqual(receipt['state'],'applied');self.assertEqual(receipt['result']['job_id'],manifest['job_id'])
        with connect(self.database) as db:
            self.assertEqual(db.execute('SELECT state FROM audio_jobs').fetchone()[0],'pending')
            self.assertEqual(json.loads(db.execute('SELECT data FROM candidate_context').fetchone()[0]),approved)
            self.assertEqual(db.execute('SELECT count(*) FROM author_rules').fetchone()[0],1)
        self.assertEqual(self.store.purge_fulfilled(),1)
        self.assertEqual(self.store.get(accepted['request_id'])['result']['job_id'],manifest['job_id'])

    def test_replaced_payload_is_retained_until_explicit_successor_applies(self):
        old=self.accept();new=self.accept(predecessor=old['request_id'],payload={'value':'new explicit choice'})
        self.assertEqual(self.store.get(old['request_id'])['state'],'superseded')
        self.assertEqual(self.store.purge_fulfilled(),0)
        self.finish(new['request_id'],self.store.head(self.book)['generation'])
        self.assertEqual(self.store.purge_fulfilled(),2)

    def test_runtime_transient_catalog_scan_failure_keeps_owner_alive_and_retries(self):
        import sqlite3
        from decision_runtime import DecisionRuntime
        owner=DecisionRuntime(SimpleNamespace(inventory=SimpleNamespace(database=self.database)))
        busy=sqlite3.OperationalError('Private catalog writer contention');busy.sqlite_errorcode=sqlite3.SQLITE_BUSY
        retried=threading.Event()
        calls=[]
        def scan():
            calls.append(1)
            if len(calls)==1:raise busy
            retried.set();owner.stop.set();return []
        with mock.patch.object(owner.store,'pending',side_effect=scan):
            owner.start()
            try:self.assertTrue(retried.wait(2))
            finally:owner.close()
        self.assertEqual(len(calls),2);self.assertIsNone(owner.status()['error'])

    def test_runtime_permanent_failure_is_visible_and_does_not_replay_unknown_work(self):
        from decision_runtime import DecisionRuntime
        owner=DecisionRuntime(SimpleNamespace(inventory=SimpleNamespace(database=self.database)))
        accepted=self.accept()
        recovered=threading.Event();allow_recovery=threading.Event();scanned=threading.Event()
        def scan():
            scanned.set()
            if not allow_recovery.is_set():raise sqlite3.DatabaseError('Private permanent failure')
            recovered.set();owner.stop.set();return []
        import sqlite3
        with mock.patch.object(owner.store,'pending',side_effect=scan):
            owner.start()
            try:
                self.assertTrue(scanned.wait(1));deadline=time.monotonic()+1
                while owner.status()['error'] is None and time.monotonic()<deadline:time.sleep(.01)
                self.assertEqual(owner.status()['state'],'needs_review');self.assertTrue(owner.thread.is_alive())
                self.assertIn('Private permanent failure',owner.status()['error']['message'])
                self.assertEqual(self.store.get(accepted['request_id'])['state'],'accepted')
                allow_recovery.set();self.assertTrue(recovered.wait(3),'Recovery must not require another click')
            finally:owner.close()
        self.assertIsNone(owner.status()['error'])


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

    def test_quit_and_updates_stop_the_queue_without_running_or_dropping_it(self):
        # 0.30.0 (Sergei, Q4: remember): Quit and Restart to update no longer drop the waiting actions; nothing runs while the
        # app closes, and a cancelled update runs them as before. Only a queued move is taken back (its own journal).
        self.server.scanning = True
        self.retry(0); self.delete(1)
        move = self.queue.enqueue('move', self.book[2], 'Book 2', {'move_id': 'move-1'})
        cancelled = []; self.server.merge.cancel_move = cancelled.append
        self.server.closing = True  # Quit or an update has begun
        self.queue.drop()
        self.server.scanning = False
        time.sleep(.2)
        self.assertEqual([item['action'] for item in self.queue.view()['queued_actions']], ['retry', 'delete'], 'kept, the move taken back')
        self.assertEqual((self.server.merge.calls, cancelled), ([], ['move-1']))
        self.assertTrue(move['queued'])
        with self.assertRaises(ValueError):
            self.retry(3)  # no new press while closing
        self.server.closing = False  # the update was cancelled
        self.assertTrue(until(lambda: len(self.server.merge.calls) == 2), 'the same queue runs once the app is not closing')
        self.assertEqual([name for name, _ in self.server.merge.calls], ['retry', 'delete'])

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

    def test_a_scan_waits_for_a_source_check_pass_s_m9(self):
        # 0.30.0 (Senua S-m9, overlap half): a scan pressed while a check pass runs waits for it, then runs.
        self.server.jobs_active = lambda: False
        self.server.merge._source_checking = True
        self.assertEqual(self.queue.blocker('scan_start', 'library:Audiobooks'), 'operation')
        self.assertEqual(self.queue.blocker('scan_resume', 'library:Audiobooks'), 'operation')
        self.server.merge._source_checking = False
        self.assertIsNone(self.queue.blocker('scan_start', 'library:Audiobooks'), 'positive control: nothing else holds it')

    def test_retry_cleanup_is_never_held_by_its_own_books_cleanup_only_by_another_books(self):
        # 0.30.0 (action_queue.py:113): Retry cleanup is queued under the book's candidate id with its job in the args; the
        # check compared that candidate id with each cleanup's job id, so the book's own waiting or paused cleanup held it.
        own, other = self.job[0], self.job[1]
        cleanups = [{'job_id': own, 'state': 'paused'}]
        self.server.merge.jobs = SimpleNamespace(_thread=None, status=lambda: {'jobs': []})
        self.server.merge.cleanup = SimpleNamespace(thread=None, status=lambda: list(cleanups))
        args = {'identity_retry': True, 'revision': 3, 'job_id': own, 'cleanup_id': str(uuid.uuid4())}
        item = {'action': 'cleanup', 'book_id': self.book[0], 'args': args}
        self.assertEqual(self.queue.blocker('cleanup', self.book[0]), 'jobs', 'positive control: the candidate id alone matches no cleanup')
        self.assertIsNone(self.queue.item_blocker(item), 'its own paused cleanup')
        cleanups[0]['state'] = 'waiting'
        self.assertIsNone(self.queue.item_blocker(item), 'its own waiting cleanup')
        cleanups.append({'job_id': other, 'state': 'paused'})
        self.assertEqual(self.queue.item_blocker(item), 'jobs', "another book's paused cleanup still holds it")
        del cleanups[1]
        self.assertIsNone(self.queue.enqueue('cleanup', self.book[0], 'Book 0', args), 'nothing else waits: the press runs at once')
        # Clean up (historical) is queued under the job id itself, with the same job in its args: unchanged.
        self.assertIsNone(self.queue.blocker('cleanup', own))
        self.assertIsNone(self.queue.item_blocker({'action': 'cleanup', 'book_id': own, 'args': {'job_id': own}}))
        self.assertEqual(self.queue.blocker('cleanup', other), 'jobs')


class PersistentQueueTests(unittest.TestCase):
    """0.30.0 (Sergei, Q4: remember): the waiting actions are kept in a private catalog and come back at the next start."""
    def setUp(self):
        import pathlib, tempfile
        area = pathlib.Path(__file__).resolve().parents[1] / 'scratch' / 'action-queue-store-tests'
        area.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=area); self.addCleanup(self.temp.cleanup)
        self.database = str(pathlib.Path(self.temp.name) / 'catalog.sqlite3')
        self.book = [str(uuid.uuid4()) for _ in range(4)]
        self.job = [str(uuid.uuid4()) for _ in range(4)]

    def server(self, started=True):
        """One launch: its queue, restored at once (as the server does when loading ends) unless started=False."""
        server = Server(); server.inventory = SimpleNamespace(database=self.database)
        queue = ActionQueue(server, poll=.02); self.addCleanup(queue.close)
        if started:
            queue.restore()
        return server, queue

    def press(self, queue, n, action='retry'):
        return queue.enqueue(action, self.book[n], 'Book %d' % n, {'revision': 3, 'job_id': self.job[n]})

    def saved(self):
        return [(item['action'], item['book_id']) for item in action_queue.QueueStore(self.database).load()[0]]

    def shutdown(self, when):
        from scanner import connect
        import pause_state
        with connect(self.database) as db:
            pause_state.record_shutdown(db, 'quit')
            db.execute('UPDATE desktop_shutdown SET at=?', (when.isoformat(),))

    def test_waiting_actions_are_saved_and_come_back_in_order_after_a_restart(self):
        server, queue = self.server()
        server.scanning = True
        self.press(queue, 0); self.press(queue, 1, 'repair'); self.press(queue, 2)
        self.assertEqual(self.saved(), [('retry', self.book[0]), ('repair', self.book[1]), ('retry', self.book[2])])
        queue.cancel(queue.view()['queued_actions'][1]['id'])
        self.assertEqual(self.saved(), [('retry', self.book[0]), ('retry', self.book[2])], 'Cancel takes it out of the saved queue too')
        self.shutdown(action_queue._now() - __import__('datetime').timedelta(seconds=5))  # the shell's record, before the close
        queue.close()
        self.assertEqual(self.saved(), [('retry', self.book[0]), ('retry', self.book[2])], 'Quit keeps it')
        # The next start: a press made while loading keeps its place behind the restored ones, and is not saved over them.
        later, again = self.server(started=False)
        later.scanning = True
        self.press(again, 3)
        self.assertEqual(again.restore(), 2)
        self.assertEqual(again.restore(), 0, 'once per start')
        view = again.view()['queued_actions']
        self.assertEqual([(item['book_id'], item.get('restored', False)) for item in view],
                         [(self.book[0], True), (self.book[2], True), (self.book[3], False)])
        restored = []
        later.merge.restored_press = lambda: mock.MagicMock(__enter__=lambda *_: restored.append(len(later.merge.calls)), __exit__=lambda *_: False)
        later.merge.answers = {'retry': {'position': 1}}
        later.scanning = False
        self.assertTrue(until(lambda: len(later.merge.calls) == 3))
        self.assertEqual([args[1] for _name, args in later.merge.calls], [self.book[0], self.book[2], self.book[3]], 'checks again, in order')
        self.assertEqual(restored, [0, 1], 'only the restored ones run as restored presses (they start nothing)')
        self.assertTrue(until(lambda: self.saved() == []), 'what ran is no longer saved')

    def test_a_saved_queue_another_session_closed_over_is_dropped_with_an_outcome(self):
        # Senua R-M3's shape: saved here, then a version that keeps no queue ran and quit (its shutdown record is later),
        # then this version again. The presses from before that are not run.
        import datetime
        server, queue = self.server()
        server.scanning = True
        self.press(queue, 0); self.press(queue, 1)
        queue.close()
        self.shutdown(action_queue._now() + datetime.timedelta(seconds=5))
        later, again = self.server(started=False)
        self.assertEqual(again.restore(), 0)
        self.assertEqual(again.view()['queued_actions'], [])
        self.assertEqual([(item['book_id'], item['result'], item['code']) for item in again.view()['queue_outcomes']],
                         [(self.book[0], 'refused', 'restore_stale'), (self.book[1], 'refused', 'restore_stale')])
        self.assertEqual(self.saved(), [])
        self.assertEqual(later.merge.calls, [])
        # Positive control: a crash (no clean close, the last shutdown record from before) keeps them.
        self.shutdown(action_queue._now() - datetime.timedelta(seconds=60))
        server, queue = self.server(); server.scanning = True
        self.press(queue, 2)
        later, again = self.server(started=False); later.scanning = True
        self.assertEqual(again.restore(), 1)

    def test_an_action_is_taken_out_of_the_saved_queue_when_it_starts(self):
        server, queue = self.server()
        server.scanning = True
        self.press(queue, 0)
        server.merge.gate = gate = threading.Event(); self.addCleanup(gate.set)
        server.scanning = False
        self.assertTrue(until(lambda: queue.view()['queue_running'] is not None))
        self.assertTrue(until(lambda: self.saved() == []), 'running: never run twice after a crash')
        gate.set()

    def test_a_restored_press_starts_no_queue(self):
        from merge_service import MergeService
        merge = MergeService.__new__(MergeService)
        merge._capture_start_generation = mock.Mock(side_effect=RuntimeError('a start began'))
        with merge.restored_press():
            self.assertIsNone(merge._resume_later())
            self.assertEqual(merge.resume(), {'state': 'held', 'reason': 'restored press'})
        merge._capture_start_generation.assert_not_called()
        for start in (merge._resume_later, merge.resume):  # positive control: outside it, the real start path runs
            with self.assertRaisesRegex(RuntimeError, 'a start began'):
                start()


if __name__ == '__main__':
    unittest.main()
