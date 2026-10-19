"""Start over, "Let the app handle it", the combined press, the bulk release and the pending start (Judy's RefusedRetry
follow-ups 2-4; Sergei, 2026-10-19).

A real catalog (book groups, candidate context, the jobs ledger, the refusal ledger, the automatic tables) and a real
AutomaticProcessing; its worker is a double that waits, so no research, scan or conversion runs. No library, no media.
"""
import hashlib
import json
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import automatic_processing
import book_restart
import groups
import m4b_readmission
import retry_refusal
from audio_jobs import AudioJobs, RetryRefused, RETRY_BOOK_CHANGED
from automatic_processing import AutomaticProcessing
from merge_service import MergeService
from review_backend import member_key
from scanner import connect
from web_server import Handler
import test_merge_http

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'start-over-tests'
AREA.mkdir(parents=True, exist_ok=True)
REFUSED = 'M4B preservation requires review: Unsupported structural box'


class Catalog:
    """One catalog file: groups, context, jobs, refusals and the automatic tables, as in the app."""
    def __init__(self, folder):
        self.base = Path(folder)
        self.db = self.base / 'catalog.sqlite3'
        self.library = self.base / 'library'
        self.library.mkdir()
        self.jobs = AudioJobs(self.db, None, lambda manifest: True, lambda record: False)
        with connect(self.db) as db:
            groups.setup(db)
            db.execute('CREATE TABLE IF NOT EXISTS candidate_context(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL)')

    def book(self, name, files=('book.m4b',), revision=2, review=True, context=None, approved_by_app=False):
        folder = self.library / name
        folder.mkdir()
        paths = []
        for file in files:
            path = folder / file
            path.write_bytes(b'original ' + name.encode() + file.encode())
            paths.append(str(path))
        identity = str(uuid.uuid4())
        evidence = {'members': [{'path': path, 'metadata': {}} for path in paths], 'metadata': {}, 'conflicts': []}
        text = json.dumps({'title': 'Reviewed ' + name}) if review else ''
        with connect(self.db) as db:
            db.execute('INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence,review,approved,changed) VALUES(?,?,?,?,?,?,?,?,?)',
                       (identity, str(self.library), str(folder), revision, 'fp-' + name, json.dumps(evidence), text, 0, 0))
            data = dict(context or {})
            if approved_by_app:
                data['automatic_approval'] = {'matcher_version': 'v', 'work_id': 'w'}
            if data:
                db.execute('INSERT INTO candidate_context VALUES(?,?,?)', (identity, revision, json.dumps(data)))
        return identity, paths

    def stuck(self, identity, paths, frozen_revision=1):
        """The book's failed M4B job, frozen at an older revision, with a current source_changed refusal."""
        manifest = {'job_id': str(uuid.uuid4()), 'candidate_id': identity, 'candidate_revision': frozen_revision, 'root': str(self.library),
                    'sources': [{'path': path, 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(), 'fingerprint': {'size': 1, 'modified': 1}} for path in paths],
                    'metadata': {'title': 'Frozen'}, 'destination': str(self.base / 'out.m4b'), 'profile': 'p', 'evidence': {}, 'cover': {},
                    'source_chapters': [], 'cleanup_policy': {'enabled': False}}
        job_id = self.jobs.enqueue(manifest)
        self.jobs._update(job_id, state='needs attention', stage='checking', reason=REFUSED,
                          journal=json.dumps({'failure': {'exception_class': 'ValidationError', 'retryable': False, 'at': 1}}))
        self.refusal(job_id, 'source_changed')
        return job_id

    def refusal(self, job_id, cause, kind='retry'):
        record = retry_refusal.record('Failed M4B retained: Frozen review/source/cover/policy changed; failed job preserved', cause, '2026-10-19T08:00:00+00:00')
        with connect(self.db) as db:
            m4b_readmission.ensure(db)
            seq = db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM m4b_readmissions').fetchone()[0]
            db.execute('INSERT OR REPLACE INTO m4b_readmissions VALUES(?,?,?,?,?,?,?,?)', (job_id, kind, seq, 'refused', None, json.dumps(record), 'a', 'b'))

    def held(self, identity, reason=book_restart.MANUAL_DRAFT, revision=None):
        group = self.group(identity)
        with connect(self.db) as db:
            db.execute('INSERT OR REPLACE INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',
                       (identity, revision or group['revision'], group['fingerprint'], 'Held', json.dumps({'reasons': [reason], 'research_history': [{'attempt': 1}]}), time.time() + 300, 'at', 'v'))

    def lease(self, identity, seconds=300):
        with connect(self.db) as db:
            db.execute('INSERT OR REPLACE INTO automatic_manual_drafts VALUES(?,?,?)', (identity, self.group(identity)['revision'], time.time() + seconds))

    def group(self, identity):
        with connect(self.db) as db:
            return dict(db.execute('SELECT * FROM book_groups WHERE id=?', (identity,)).fetchone())

    def context(self, identity):
        with connect(self.db) as db:
            row = db.execute('SELECT revision,data FROM candidate_context WHERE id=?', (identity,)).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def automatic_row(self, identity):
        with connect(self.db) as db:
            row = db.execute('SELECT * FROM automatic_candidates WHERE id=?', (identity,)).fetchone()
        return dict(row) if row else None

    def job_row(self, job_id):
        return self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))[0]

    def set_aside(self):
        with connect(self.db) as db:
            return [tuple(row) for row in db.execute('SELECT job_id,candidate_id FROM audio_job_set_aside')]


class Reviews:
    """The review service's context read (its own rule: the context only at the book's current revision)."""
    def __init__(self, db):
        self.db = db
        self.lock = threading.RLock()

    def _context(self, row):
        with connect(self.db) as db:
            saved = db.execute('SELECT revision,data FROM candidate_context WHERE id=?', (row['id'],)).fetchone()
        return json.loads(saved[1]) if saved and saved[0] == row['revision'] else {}

    def _row(self, library, identity, revision=None):
        raise ValueError('Candidate no longer current')


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(self.temp.cleanup)
        self.c = Catalog(self.temp.name)
        self.addCleanup(self.c.jobs.close)
        patcher = patch.object(MergeService, '_check_repairs')
        patcher.start()
        self.addCleanup(patcher.stop)
        s = MergeService.__new__(MergeService)
        s.jobs = self.c.jobs
        s.operation_lock = threading.RLock()
        s.draining = False
        s.inventory = SimpleNamespace(worker=None, database=self.c.db, group_lock=threading.RLock(), roots={'Audiobooks': str(self.c.library)}, stop=lambda: None)
        s.reviews = Reviews(self.c.db)
        s.working = SimpleNamespace(admission_clear=lambda row: None)
        s.stage_root = self.c.base / 'staging'
        s.stage_root.mkdir()
        s.cleanup = SimpleNamespace(status=lambda job_id=None: None)
        self.jobs_state = {'state': 'Idle', 'queued': 0, 'failed': 0}
        s.state = lambda: dict(self.jobs_state)
        s.status_snapshot = lambda: dict(self.jobs_state)  # the real one keeps a monitor connection open
        s.pause = Mock()
        s.invalidate_status = Mock()
        s.jobs.m4b_working_clear = s._m4b_working_clear
        s.jobs.repair_check_failed = s._repair_check_failed
        self.s = s
        self.release_worker = threading.Event()
        self.worker_runs = []
        def work(auto, run_id):
            self.worker_runs.append(run_id)
            self.release_worker.wait(30)
        worker = patch.object(AutomaticProcessing, '_work', work)
        worker.start()
        self.addCleanup(worker.stop)
        s.automatic = AutomaticProcessing(s, research=SimpleNamespace(client=None))
        self.addCleanup(self.finish)

    def finish(self):
        self.release_worker.set()
        thread = self.s.automatic.thread
        if thread:
            thread.join(10)
        self.s.automatic.closed = True
        self.s.automatic._pending_wake.set()
        pending = self.s.automatic._pending_thread
        if pending:
            pending.join(10)
        thread = self.s.automatic.thread  # the pending start may have started one meanwhile
        if thread:
            thread.join(10)

    def summary(self, job_id):
        return self.s.attention_summary([job_id]).get(job_id)

    def press(self, identity, job_id, revision=2, discard=False):
        return self.s.start_over('Audiobooks', identity, revision, job_id, discard)


class StartOverTests(Base):
    def test_the_job_is_set_aside_kept_and_the_book_goes_back_to_automatic_processing(self):
        identity, paths = self.c.book('auto', approved_by_app=True)
        job_id = self.c.stuck(identity, paths)
        self.c.held(identity, 'Approved automatically')  # an old record that must not read Queued/Held after the press
        working = self.s.stage_root / job_id / str(uuid.uuid4())
        working.mkdir(parents=True)
        (working / 'source00000.m4b').write_bytes(b'kept')
        before = self.c.job_row(job_id)
        failed = self.c.jobs.status()['failed']
        value = self.summary(job_id)
        self.assertEqual((value['startover'], value['release_ok'], 'retry' in value), ('automatic', False, False))
        answer = self.press(identity, job_id)
        self.assertEqual((answer['set_aside'], answer['released'], answer['outcome']), (True, False, 'automatic'))
        self.assertEqual(answer['pass'], {'action': 'started', 'visit': 'this_run'}, 'nothing was running: Start over starts it (O9)')
        # Kept: the row, its journal and its working files; it is only no longer the book's current job.
        self.assertEqual(self.c.job_row(job_id), before)
        self.assertTrue((working / 'source00000.m4b').is_file())
        self.assertEqual(self.c.set_aside(), [(job_id, identity)])
        self.assertIsNone(self.s.candidate_status(identity), 'no job for the book, so the pass can approve and queue it')
        self.assertNotIn(job_id, self.s.attention_summary(), 'out of Output needs attention')
        self.assertEqual(self.c.jobs.status()['failed'], failed - 1)
        self.assertNotIn(job_id, [job['job_id'] for job in self.c.jobs.status()['jobs']])
        record = self.c.automatic_row(identity)
        self.assertEqual((record['state'], json.loads(record['result'])['reasons'], record['retry_at'], record['revision']), ('Pending', [], None, 2))
        self.assertEqual(json.loads(record['result'])['research_history'], [{'attempt': 1}], 'research history kept')
        with connect(self.c.db) as db:
            marker = book_restart.markers(db)[identity]
        self.assertEqual((marker['kind'], marker['job_id'], marker['visit']), ('start_over', job_id, 'this_run'))
        self.assertEqual(book_restart.state(marker, None, None)['state'], 'waiting')
        self.assertTrue(self.s.automatic.thread.is_alive(), 'the pass is running')

    def test_presses_from_an_outdated_view_change_nothing(self):
        identity, paths = self.c.book('stale')
        job_id = self.c.stuck(identity, paths)
        for revision in (1, 3):
            with self.assertRaises(RetryRefused) as caught:
                self.press(identity, job_id, revision=revision)
            self.assertEqual((str(caught.exception), caught.exception.cause), (RETRY_BOOK_CHANGED, 'changed'))
        with self.assertRaises(RetryRefused):
            self.s.start_over('Audiobooks', str(uuid.uuid4()), 2, job_id)  # another book's id
        self.assertEqual(self.c.set_aside(), [], 'nothing set aside')
        # A refusal of another cause offers no Start over.
        other, other_paths = self.c.book('other')
        other_job = self.c.stuck(other, other_paths)
        self.c.refusal(other_job, 'unsupported_file')
        self.assertNotIn('startover', self.summary(other_job))
        with self.assertRaises(RetryRefused):
            self.press(other, other_job)
        # A newer job for the book: the stuck one is history, not the book's current job.
        newer, newer_paths = self.c.book('newer')
        stuck = self.c.stuck(newer, newer_paths)
        manifest = json.loads(self.c.job_row(stuck)['manifest'])
        manifest['job_id'] = str(uuid.uuid4())
        manifest['metadata'] = {'title': 'Newer work'}
        self.c.jobs.enqueue(manifest)
        with self.assertRaises(RetryRefused):
            self.press(newer, stuck)
        # Positive control, then a second press from the same (now outdated) view.
        self.press(identity, job_id)
        with self.assertRaises(RetryRefused) as caught:
            self.press(identity, job_id)
        self.assertEqual(str(caught.exception), RETRY_BOOK_CHANGED)
        self.assertEqual(self.c.set_aside(), [(job_id, identity)])

    def test_the_transaction_rechecks_every_rule_even_when_the_offer_was_made(self):
        def offered(job_id):
            return patch.object(MergeService, 'attention_summary', lambda service, job_ids=None, retry=True: {job_id: {'startover': 'automatic'}})
        identity, paths = self.c.book('newer')
        stuck = self.c.stuck(identity, paths)
        manifest = json.loads(self.c.job_row(stuck)['manifest'])
        manifest['job_id'] = str(uuid.uuid4())
        manifest['metadata'] = {'title': 'Newer work'}
        self.c.jobs.enqueue(manifest)
        with offered(stuck), self.assertRaises(RetryRefused):
            self.press(identity, stuck)  # a newer job exists
        other, other_paths = self.c.book('other')
        other_job = self.c.stuck(other, other_paths)
        self.c.refusal(other_job, 'unsupported_file')
        with offered(other_job), self.assertRaises(RetryRefused):
            self.press(other, other_job)  # the refusal is not source_changed
        queued, queued_paths = self.c.book('queued')
        queued_job = self.c.stuck(queued, queued_paths)
        self.c.jobs._update(queued_job, state='pending', stage='queued')
        with offered(queued_job), self.assertRaises(RetryRefused):
            self.press(queued, queued_job)  # the job no longer needs attention
        self.assertEqual(self.c.set_aside(), [])

    def test_a_set_aside_job_can_never_be_retried_or_repaired(self):
        identity, paths = self.c.book('aside')
        job_id = self.c.stuck(identity, paths)
        self.press(identity, job_id)
        with self.assertRaises(RetryRefused):
            self.s._m4b_parent(job_id, identity, 1, lambda row: True)  # not the book's current job any more
        # Retry's E6 (newest job) on a job refused before any attempt, the shape Retry requeues as itself.
        other, other_paths = self.c.book('held-before-start')
        held = self.c.stuck(other, other_paths)
        self.c.jobs._update(held, journal='{}')
        with self.c.jobs._db() as db:
            self.assertIsNotNone(self.c.jobs._retry_shape(db, self.c.job_row(held)), 'positive control: Retry would requeue it')
            book_restart.set_aside(db, held, other, 2)
            self.assertIsNone(self.c.jobs._retry_shape(db, self.c.job_row(held)))

    def test_the_failed_parent_of_a_set_aside_child_goes_with_it(self):
        identity, paths = self.c.book('chain')
        parent = self.c.stuck(identity, paths)
        manifest = json.loads(self.c.job_row(parent)['manifest'])
        manifest['job_id'] = str(uuid.uuid4())
        manifest['metadata'] = {'title': 'Retry child'}
        child = self.c.jobs.enqueue(manifest)
        self.c.jobs._update(child, state='needs attention', stage='checking', reason=REFUSED, journal=json.dumps({'failure': {'exception_class': 'ValidationError', 'retryable': False, 'at': 2}}))
        self.c.refusal(child, 'source_changed')
        with self.c.jobs._db() as db:
            self.assertEqual(self.c.jobs._newest_jobs(db, {identity}), {identity: child}, 'positive control: the child is current')
        before = {job_id: self.c.job_row(job_id) for job_id in (parent, child)}
        self.press(identity, child)
        self.assertEqual(sorted(self.c.set_aside()), sorted([(child, identity), (parent, identity)]))
        with self.c.jobs._db() as db:
            self.assertEqual(self.c.jobs._newest_jobs(db, {identity}), {}, 'the old parent does not become current again')
        self.assertIsNone(self.s.candidate_status(identity))
        self.assertEqual([key for key in self.s.attention_summary() if key in before], [])
        self.assertEqual({job_id: self.c.job_row(job_id) for job_id in before}, before, 'both rows kept as they were')

    def test_the_prediction_follows_the_saved_review_hold(self):
        auto, auto_paths = self.c.book('app', approved_by_app=True)
        manual, manual_paths = self.c.book('manual')
        multi, multi_paths = self.c.book('multi', files=('01.mp3', '02.mp3'))
        leased, leased_paths = self.c.book('leased', review=False)
        self.c.lease(leased)
        jobs = {identity: self.c.stuck(identity, paths) for identity, paths in ((auto, auto_paths), (manual, manual_paths), (multi, multi_paths), (leased, leased_paths))}
        expected = {auto: ('automatic', False), manual: ('manual_draft', True), multi: ('manual_draft', False), leased: ('manual_draft', False)}
        for identity, job_id in jobs.items():
            value = self.summary(job_id)
            self.assertEqual((value['startover'], value['release_ok']), expected[identity])
            # The same read-only test the pass runs (AutomaticProcessing.manual_draft).
            group = self.c.group(identity)
            row = {'id': identity, 'revision': group['revision'], 'review': json.loads(group['review']) if group['review'] else None}
            self.assertEqual(self.s.automatic.manual_draft(row), value['startover'] == 'manual_draft')

    def test_the_combined_press_is_one_transaction(self):
        identity, paths = self.c.book('combined', context={'manual_note': 'hand edit', 'cover_id': 'c'})
        job_id = self.c.stuck(identity, paths)
        self.assertEqual(self.summary(job_id)['release_ok'], True)
        # The discard fails: nothing changes, the job stays current.
        with patch.object(book_restart, 'discard_review', side_effect=book_restart.Changed('x')):
            with self.assertRaises(RetryRefused):
                self.press(identity, job_id, discard=True)
        self.assertEqual(self.c.set_aside(), [])
        self.assertEqual(self.c.group(identity)['review'], json.dumps({'title': 'Reviewed combined'}))
        with patch.object(book_restart, 'mark', side_effect=book_restart.Changed('late')):
            with self.assertRaises(RetryRefused):
                self.press(identity, job_id, discard=True)
        self.assertEqual((self.c.set_aside(), self.c.group(identity)['revision']), ([], 2), 'a late failure rolls the discard back too')
        source = Path(paths[0]).read_bytes()
        answer = self.press(identity, job_id, discard=True)
        self.assertEqual((answer['set_aside'], answer['released'], answer['outcome']), (True, True, 'automatic'))
        group = self.c.group(identity)
        self.assertEqual((group['review'], group['revision'], group['approved']), ('', 3, 0))
        self.assertIsNone(self.c.context(identity), 'notes, evidence, cover and track choices discarded')
        self.assertEqual(self.c.set_aside(), [(job_id, identity)])
        self.assertEqual(Path(paths[0]).read_bytes(), source, 'audio files untouched')

    def test_the_combined_press_needs_release_ok(self):
        multi, paths = self.c.book('multi', files=('01.mp3', '02.mp3'))
        job_id = self.c.stuck(multi, paths)
        with self.assertRaises(RetryRefused):
            self.press(multi, job_id, discard=True)
        leased, leased_paths = self.c.book('leased')
        leased_job = self.c.stuck(leased, leased_paths)
        self.c.lease(leased)
        with self.assertRaises(RetryRefused) as caught:
            self.press(leased, leased_job, discard=True)
        self.assertEqual((str(caught.exception), caught.exception.cause), (MergeService.EDITING, 'editing'))
        self.assertEqual(self.c.set_aside(), [])
        self.assertTrue(self.c.group(multi)['review'] and self.c.group(leased)['review'])


class ReleaseTests(Base):
    def releasable(self, name='one', **kwargs):
        identity, paths = self.c.book(name, context={'manual_note': 'hand edit'}, **kwargs)
        self.c.held(identity)
        return identity, paths

    def test_release_discards_the_saved_review_and_sends_the_book_back(self):
        identity, paths = self.releasable()
        older = self.c.stuck(identity, paths)
        self.press(identity, older)  # an older job, set aside: kept
        self.c.held(identity, revision=2)
        source = Path(paths[0]).read_bytes()
        answer = self.s.release('Audiobooks', identity, 2)
        self.assertEqual((answer['released'], answer['outcome'], answer['pass']['action'], answer['pass']['visit']), (True, 'automatic', 'running', 'this_run'))
        group = self.c.group(identity)
        self.assertEqual((group['review'], group['revision']), ('', 3))
        self.assertIsNone(self.c.context(identity))
        self.assertEqual((self.c.automatic_row(identity)['state'], self.c.automatic_row(identity)['revision']), ('Pending', 3))
        self.assertEqual(Path(paths[0]).read_bytes(), source)
        self.assertEqual(self.c.set_aside(), [(older, identity)], 'the older job is kept')
        with connect(self.c.db) as db:
            self.assertEqual(book_restart.markers(db)[identity]['kind'], 'release')
        self.assertIn(identity, self.s.automatic._requeued, 'the running run reaches it next')

    def test_release_refuses_every_book_it_does_not_cover(self):
        def refused(identity, revision=2):
            with self.assertRaises(RetryRefused) as caught:
                self.s.release('Audiobooks', identity, revision)
            return caught.exception.cause
        multi, _ = self.releasable('multi', files=('01.mp3', '02.mp3'))
        self.assertEqual(refused(multi), 'changed', 'a multi-file book can be queued by hand')
        leased, _ = self.releasable('leased')
        self.c.lease(leased)
        self.assertEqual(refused(leased), 'editing')
        other, _ = self.c.book('other-hold', context={'manual_note': 'x'})
        self.c.held(other, 'Cover source unavailable')
        self.assertEqual(refused(other), 'changed', 'held for another reason')
        approved, _ = self.c.book('approved', approved_by_app=True)
        self.c.held(approved)
        self.assertEqual(refused(approved), 'changed', 'an approval record at its revision: not held for a saved review')
        with_job, job_paths = self.releasable('job')
        self.c.stuck(with_job, job_paths)
        self.assertEqual(refused(with_job), 'changed', 'a book with a job')
        current, _ = self.releasable('outdated')
        self.assertEqual(refused(current, revision=1), 'changed')
        for identity in (multi, leased, other, approved, with_job, current):
            self.assertTrue(self.c.group(identity)['review'], 'nothing discarded')
        with patch.object(book_restart, 'discard_review', side_effect=__import__('sqlite3').OperationalError('database is locked')):
            self.assertEqual(refused(current), 'busy')

    def test_release_selected_takes_each_book_alone_and_starts_once(self):
        books = [self.releasable('b%d' % index)[0] for index in range(3)]
        multi, _ = self.releasable('multi', files=('01.mp3', '02.mp3'))
        changed, _ = self.releasable('changed')
        with patch.object(AutomaticProcessing, 'request_start', return_value={'action': 'started'}) as start:
            answer = self.s.release_selected('Audiobooks', [(identity, 2) for identity in books] + [(multi, 2), (changed, 1)])
        self.assertEqual(answer['released'], 3)
        self.assertEqual(sorted((item['id'], item['cause']) for item in answer['refused']), sorted([(multi, 'changed'), (changed, 'changed')]))
        self.assertEqual(start.call_count, 1, 'one start, after the last book')
        self.assertEqual(answer['pass'], {'action': 'started', 'visit': 'this_run'})
        self.assertEqual([self.c.group(identity)['review'] for identity in books], ['', '', ''])


class PassTests(Base):
    """The pass reaches a book put back (n), and the press starts it or waits for its blocker (O9, O12)."""
    def test_requeue_while_running_paused_and_after_the_last_research_step(self):
        auto = self.s.automatic
        auto.start()
        self.assertEqual(auto.requeue('book-a'), 'this_run')
        checkpoint = {'pending': ['x'], 'done': ['book-a', 'y'], 'deferred': ['book-a']}
        deferred = checkpoint['deferred']
        self.assertTrue(auto._take_requeued(checkpoint))
        self.assertEqual(checkpoint, {'pending': ['book-a', 'x'], 'done': ['y'], 'deferred': []})
        self.assertIs(checkpoint['deferred'], deferred, 'changed in place: the worker holds that list')
        auto._closing_run = True
        self.assertEqual(auto.requeue('book-b'), 'next_run')
        self.release_worker.set()
        auto.thread.join(10)
        # A paused run continues from its saved checkpoint: the book is put back on it.
        with connect(self.c.db) as db:
            db.execute("UPDATE automatic_runs SET state='Paused',phase='research',checkpoint=?", (json.dumps({'pending': ['x'], 'done': ['book-c'], 'deferred': []}),))
        self.assertEqual(auto.requeue('book-c'), 'this_run')
        self.assertEqual(json.loads(auto._run_row()['checkpoint']), {'pending': ['book-c', 'x'], 'done': [], 'deferred': []})

    def test_a_book_put_back_during_the_conversion_wait_is_researched_in_the_same_run(self):
        visited = []
        rows = Mock(side_effect=lambda library, identity, revision=None: visited.append(identity) or (_ for _ in ()).throw(ValueError('gone')))
        auto = AutomaticProcessing.__new__(AutomaticProcessing)
        auto.__dict__.update(self.s.automatic.__dict__)
        merge = SimpleNamespace(reviews=SimpleNamespace(_row=rows), candidate_status=lambda identity: None, resume=Mock())
        calls = {'n': 0}
        def state():
            calls['n'] += 1
            if calls['n'] == 3:  # the conversion wait's idle check (two reads before it look for queued work)
                auto.requeue('late-book')  # a Start over press while the run waits for conversions
            return {'state': 'Idle', 'queued': 0, 'cleanup_active': False, 'failed': 0}
        merge.state = state
        auto.merge = merge
        auto.thread = threading.current_thread()  # requeue takes the running path
        with connect(self.c.db) as db:
            db.execute("INSERT INTO automatic_runs VALUES('run','Running','research',?,'','a','b',0)", (json.dumps({'pending': [], 'done': [], 'deferred': []}),))
        worker = threading.Thread(target=REAL_WORK, args=(auto, 'run'), daemon=True)
        worker.start()
        worker.join(10)
        if worker.is_alive():
            auto.stop_event.set()
            worker.join(10)
            self.fail('the run never finished')
        self.assertEqual(visited, ['late-book'])
        self.assertEqual(auto._run_row()['state'], 'Completed')

    def test_request_start_outcomes(self):
        auto = self.s.automatic
        self.assertEqual(auto.request_start(), {'action': 'started'})
        self.assertEqual(auto.request_start(), {'action': 'running'})
        self.release_worker.set()
        auto.thread.join(10)
        with connect(self.c.db) as db:
            db.execute("UPDATE automatic_runs SET state='Paused',phase='research'")
        self.release_worker.clear()
        self.assertEqual(auto.request_start(), {'action': 'continued'})
        self.release_worker.set()
        auto.thread.join(10)
        self.assertEqual(auto.request_start(server_closing=True)['action'], 'blocked', 'a blocker that cannot clear')
        self.assertIsNone(auto.start_pending)

    def test_a_blocked_press_leaves_one_pending_start_that_fires_when_the_blocker_clears(self):
        auto = self.s.automatic
        notified = Mock()
        auto.on_change = notified
        self.jobs_state['state'] = 'Running'
        with patch.object(automatic_processing, 'PENDING_POLL', 0.05):
            first = auto.request_start()
            self.assertEqual((first['action'], first['pending_kind']), ('pending', 'conversion'))
            self.assertEqual(auto.request_start()['action'], 'pending')
            self.assertEqual(auto.start_pending, {'kind': 'conversion'}, 'one pending start for the app')
            status = auto.status(jobs=dict(self.jobs_state))
            self.assertEqual((status['start_pending'], status['start_block']), ({'kind': 'conversion'}, {'kind': 'conversion', 'clears': True}))
            time.sleep(0.3)
            self.assertIsNone(auto.thread, 'still waiting while the blocker holds')
            self.jobs_state['state'] = 'Paused'  # the jobs were paused: the blocker cleared
            deadline = time.monotonic() + 5
            while not (auto.thread and auto.thread.is_alive()) and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(auto.thread and auto.thread.is_alive(), 'started by itself, with no press')
            self.assertIsNone(auto.start_pending)
            self.assertTrue(notified.called, 'the next poll shows it')

    def test_every_start_tells_the_server_which_library_it_scans(self):
        auto = self.s.automatic
        server = SimpleNamespace(active_library=None)
        auto.on_started = lambda: setattr(server, 'active_library', 'Audiobooks')
        self.assertEqual(auto.request_start(), {'action': 'started'})
        self.assertEqual(server.active_library, 'Audiobooks', 'a pass started by Start over shows its scan as Start does')

    def test_cancel_another_blocker_and_a_blocker_that_cannot_clear(self):
        auto = self.s.automatic
        self.jobs_state['state'] = 'Running'
        with patch.object(automatic_processing, 'PENDING_POLL', 0.05):
            auto.request_start()
            auto.cancel_start()
            self.assertIsNone(auto.start_pending)
            self.jobs_state['state'] = 'Paused'
            time.sleep(0.3)
            self.assertIsNone(auto.thread, 'cancelled: it does not start when the blocker clears')
            # Conversion, then a scan: it keeps waiting and changes kind.
            self.jobs_state['state'] = 'Running'
            auto.request_start()
            self.s.inventory.worker = SimpleNamespace(is_alive=lambda: True)
            self.jobs_state['state'] = 'Paused'
            deadline = time.monotonic() + 5
            while auto.start_pending == {'kind': 'conversion'} and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertEqual(auto.start_pending, {'kind': 'scan'})
            # A blocker that cannot clear ends it.
            auto.volatile_failure = {'diagnostic': {}, 'reason': 'x', 'candidate_result': {}}
            deadline = time.monotonic() + 5
            while auto.start_pending is not None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertIsNone(auto.start_pending)
            self.assertIsNone(auto.thread)


class PendingStartStopTests(Base):
    """Senua M1 and M2 (v0.19.0 review; probe senua-0190/probe_pending.py): Quit, Stop and the app's own safety stops
    end a pending start, and no start fires once Quit or shutdown has begun. Before the fix a pending start fired during
    the Quit drain (which could then hang Quit at "finishing") and after a disk-full or working-file hold."""
    def setUp(self):
        super().setUp()
        poll = patch.object(automatic_processing, 'PENDING_POLL', 0.05)
        poll.start()
        self.addCleanup(poll.stop)
        self.notified = Mock()
        self.s.automatic.on_change = self.notified

    def pending(self):
        """A book converts, so Start over leaves one pending start."""
        self.jobs_state['state'] = 'Running'
        answer = self.s.automatic.request_start()
        self.assertEqual((answer['action'], answer['pending_kind']), ('pending', 'conversion'))

    def never_starts(self, case):
        time.sleep(0.4)  # eight polls of the pending loop
        auto = self.s.automatic
        self.assertIsNone(auto.thread, case + ': nothing started by itself')
        self.assertIsNone(auto.start_pending, case)
        loop = auto._pending_thread
        if loop:
            loop.join(5)
            self.assertFalse(loop.is_alive(), case + ': the pending loop ended')

    def test_quit_ends_a_pending_start_and_quit_finishes(self):
        from desktop_backend import DesktopControl
        self.pending()
        self.s.cleanup.thread = None
        self.s.cleanup.current = None
        self.s._post_current = None
        lock = threading.Lock()
        server = SimpleNamespace(merge=self.s, inventory=self.s.inventory, closing=False, merge_admissions=0, control_lock=lock,
                                 control_condition=threading.Condition(lock), scan_active=lambda: False, finish_shutdown=Mock())
        self.s.automatic.server_closing = lambda: server.closing  # as BrowserServer wires it
        control = DesktopControl(server)
        self.assertEqual(control.quit()['phase'], 'finishing')  # the real Quit: closing, drain, scan stop, automatic.stop()
        self.assertTrue(self.s.draining)
        self.assertIsNone(self.s.automatic.start_pending, 'Quit ends the pending start')
        self.assertTrue(self.notified.called, 'the next poll shows it')
        self.jobs_state['state'] = 'Paused'  # the book in progress finished under the drain; the next stays queued
        self.never_starts('Quit')
        control.thread.join(5)
        self.assertFalse(control.thread.is_alive(), 'Quit does not hang at "finishing"')
        server.finish_shutdown.assert_called_once_with()

    def test_a_start_never_fires_once_quit_or_shutdown_has_begun(self):
        auto = self.s.automatic
        server = SimpleNamespace(closing=False)
        auto.server_closing = lambda: server.closing
        self.pending()
        # Web shutdown sets closing first; automatic.close() comes only after the scan is joined (finish_shutdown).
        # The blocker clears inside that window: the start re-reads the flag right before it fires.
        server.closing = True
        self.jobs_state['state'] = 'Paused'
        self.never_starts('shutdown')
        # A Start over press admitted before Quit reaches request_start after it, carrying the flag it read then.
        self.assertEqual(auto.request_start(server_closing=False)['action'], 'blocked')
        server.closing = False
        self.s.draining = True  # a desktop Quit drain, read from the merge service
        self.assertEqual(auto.request_start()['action'], 'blocked')
        self.assertIsNone(auto.thread)
        self.assertIsNone(auto.start_pending)
        self.assertEqual(auto.status(jobs=dict(self.jobs_state))['start_block']['kind'], 'closing')
        self.assertFalse(auto.status(jobs=dict(self.jobs_state))['can_start'])

    def test_stop_and_the_safety_stops_end_a_pending_start(self):
        auto = self.s.automatic
        for force, case in ((True, 'disk-full or working-file hold'), (False, 'Stop automatic processing')):
            self.notified.reset_mock()
            self.pending()
            auto.stop(force=force)  # jobs.on_space_hold and jobs.on_working_hold call stop(force=True)
            self.assertIsNone(auto.start_pending, case)
            self.assertTrue(self.notified.called, case + ': the next poll shows it')
            self.assertIsNone(auto.status(jobs={'state': 'Paused', 'queued': 1, 'failed': 0})['start_pending'],
                              case + ': no "waiting to start" row or notice')
            self.jobs_state['state'] = 'Paused'  # the jobs worker returned after the hold; the queue is kept
            self.never_starts(case)


class MarkerListTests(Base):
    """The Started over marker on list rows, the release flag, and the Started over filter (follow-up 3, sections 2 and 4)."""
    def auto(self, identity, state, reasons=()):
        group = self.c.group(identity)
        with connect(self.c.db) as db:
            db.execute('INSERT OR REPLACE INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',
                       (identity, group['revision'], group['fingerprint'], state, json.dumps({'reasons': list(reasons)}), None, 'at', 'v'))
        return {'state': state, 'reasons': list(reasons)}

    def marked(self, name, **kwargs):
        identity, paths = self.c.book(name, **kwargs)
        with connect(self.c.db) as db:
            book_restart.mark(db, identity, 'start_over', None)
        return identity

    def row(self, identity, automatic=None, job=None):
        return {'id': identity, 'automatic': automatic, 'creation': {'job': job}}

    def test_each_marker_state_on_a_list_row(self):
        app = self.marked('app', approved_by_app=True)
        cases = [(None, None, {'state': 'waiting'}), ('Researching', None, {'state': 'working'}),
                 ('Waiting for source', None, {'state': 'working', 'source_wait': True}),
                 ('Held', ['Cover source unavailable'], {'state': 'held'}), ('Held', [book_restart.MANUAL_DRAFT], {'state': 'held', 'hold': 'manual_draft'}),
                 ('Needs attention', ['x'], {'state': 'failed'})]
        for state, reasons, expected in cases:
            automatic = self.auto(app, state, reasons or ()) if state else None
            value = self.s.restart_view([self.row(app, automatic)])[0]['restart']
            self.assertEqual({key: value.get(key) for key in expected}, expected, state)
            self.assertEqual(value['kind'], 'start_over')
            self.assertNotIn('expect', value, 'an app-approved book is not held')
        self.assertEqual(self.s.restart_view([self.row(app, None, {'state': 'Queued'})])[0]['restart']['state'], 'queued')
        self.assertNotIn('restart', self.s.restart_view([self.row(app, None, {'state': 'Audiobook created'})])[0], 'ended')
        self.assertNotIn('restart', self.s.restart_view([self.row(app, None, {'state': 'Output needs attention'})])[0], 'ended')
        manual = self.marked('manual')
        value = self.s.restart_view([self.row(manual)])[0]['restart']
        self.assertEqual((value['expect'], value['release_expected']), ('hold', True))
        multi = self.marked('multi', files=('01.mp3', '02.mp3'))
        value = self.s.restart_view([self.row(multi)])[0]['restart']
        self.assertEqual((value['expect'], value['release_expected']), ('hold', False), 'a multi-file book never gets the button')
        self.assertNotIn('restart', self.s.restart_view([self.row(self.c.book('plain')[0])])[0], 'no marker, no state')

    def test_next_run_only_while_the_run_that_passed_the_book_runs(self):
        identity = self.marked('late')
        self.s.automatic.start()
        run = self.s.automatic._run_row()
        with connect(self.c.db) as db:
            book_restart.set_visit(db, identity, 'next_run', run['id'])
        self.assertEqual(self.s.restart_view([self.row(identity)])[0]['restart'].get('visit'), 'next_run')
        with connect(self.c.db) as db:
            book_restart.set_visit(db, identity, 'next_run', 'an-earlier-run')
        self.assertNotIn('visit', self.s.restart_view([self.row(identity)])[0]['restart'])

    def held(self, name, **kwargs):
        identity = self.c.book(name, **kwargs)[0]
        return identity, self.auto(identity, 'Held', [book_restart.MANUAL_DRAFT])

    def test_the_release_flag_follows_the_saved_review_hold(self):
        one, auto = self.held('one')
        row = self.s.restart_view([self.row(one, auto)])[0]
        self.assertEqual((row['release'], row['automatic']['hold'], row['automatic']['lease']), ({'allowed': True}, 'manual_draft', False))
        multi, auto = self.held('multi', files=('01.mp3', '02.mp3'))
        self.assertEqual(self.s.restart_view([self.row(multi, auto)])[0]['release'], {'allowed': False})
        leased, auto = self.held('leased')
        self.c.lease(leased)
        row = self.s.restart_view([self.row(leased, auto)])[0]
        self.assertEqual((row['release'], row['automatic']['lease']), ({'allowed': False}, True))
        busy, auto = self.held('busy')
        self.assertEqual(self.s.restart_view([self.row(busy, auto, {'state': 'Queued'})])[0]['release'], {'allowed': False}, 'a book with a job')
        other = self.c.book('other')[0]
        row = self.s.restart_view([self.row(other, self.auto(other, 'Held', ['Cover source unavailable']))])[0]
        self.assertNotIn('release', row, 'held for another reason')

    def test_the_started_over_filter_order_and_counts(self):
        waiting = self.marked('waiting')
        working = self.marked('working')
        self.auto(working, 'Researching')
        held = self.marked('held')
        self.auto(held, 'Held', [book_restart.MANUAL_DRAFT])
        failed = self.marked('failed')
        self.auto(failed, 'Needs attention', ['x'])
        queued = self.marked('queued')
        order, counts = self.s.restart_index({queued: {'state': 'Queued'}})
        self.assertEqual(sorted(order, key=lambda key: order[key]), [failed, waiting, working, held])
        self.assertNotIn(queued, order, 'queued by automatic processing: it has left the filter')
        self.assertEqual(counts, {'waiting': 1, 'working': 1, 'held': 1, 'failed': 1, 'next_run': 0, 'release': 1})
        self.c.lease(held)
        self.assertEqual(self.s.restart_index({})[1]['release'], 0, 'no release while an editor is open')

    def test_the_book_list_accepts_and_applies_the_filter(self):
        from review_backend import CandidateReviewService
        waiting = self.marked('waiting')
        plain = self.c.book('plain')[0]
        failed = self.marked('failed')
        self.auto(failed, 'Needs attention', ['x'])
        listed = []
        def candidates(label, limit=100, offset=0, search='', status='all', ids=None):
            listed.append(ids)
            return {'rows': [{'id': identity, 'revision': 2, 'fingerprint': 'fp-' + name} for identity, name in ((waiting, 'waiting'), (plain, 'plain'), (failed, 'failed'))
                             if ids is None or identity in ids], 'total': 3}
        reviews = CandidateReviewService.__new__(CandidateReviewService)
        reviews.inventory = SimpleNamespace(database=self.c.db, candidates=candidates)
        reviews.page_local = threading.local()
        reviews.jobs = self.s
        reviews.enrich = lambda row, check_sources=True: dict(row, automatic=None, creation={'job': None})
        self.s.converted_ids = lambda: set()
        page = reviews._page(status='restarted')
        self.assertEqual(([row['id'] for row in page['rows']], page['total']), ([failed, waiting], 2), 'failed first: it needs Sergei')
        self.assertEqual(page['rows'][1]['restart']['state'], 'waiting')
        self.assertEqual((page['restart_counts']['waiting'], page['restart_counts']['failed']), (1, 1))
        self.assertEqual(listed, [{waiting, failed}])
        searched = reviews._page(status='restarted', search='a')  # a search lists every match; the filter decides each row
        self.assertEqual([row['id'] for row in searched['rows']], [failed, waiting])
        self.assertNotIn('restart_counts', reviews._page(status='all'), 'counts only in this filter')


REAL_WORK = AutomaticProcessing._work


class RouteTests(unittest.TestCase):
    setUp = test_merge_http.MergeHTTPTests.setUp
    tearDown = test_merge_http.MergeHTTPTests.tearDown
    handler = test_merge_http.MergeHTTPTests.handler
    call = test_merge_http.MergeHTTPTests.call
    identity = test_merge_http.MergeHTTPTests.identity

    def test_start_over_release_and_cancel_routes(self):
        job = str(uuid.uuid4())
        automatic = SimpleNamespace(status=Mock(return_value={'state': 'Running'}), cancel_start=Mock())
        self.merge.automatic = automatic
        self.merge.start_over = Mock(return_value={'set_aside': True, 'outcome': 'automatic', 'pass': {'action': 'started'}, 'row': None})
        self.merge.release = Mock(return_value={'released': True, 'pass': {'action': 'running'}, 'row': None})
        self.merge.release_selected = Mock(return_value={'released': 1, 'refused': [], 'pass': {'action': 'running'}})
        self.merge.restart_row = Mock(return_value={'id': test_merge_http.ID})
        self.server.scan_active = lambda: False
        status, body, _ = self.call('/api/audiobook/startover', self.identity() | {'job_id': job, 'discard_review': True})
        self.assertEqual((status, body['automatic_processing']), (202, {'state': 'Running'}))
        self.merge.start_over.assert_called_once_with('Audiobooks', test_merge_http.ID, 1, job, True, server_closing=False)
        self.assertEqual(self.call('/api/audiobook/startover', self.identity() | {'job_id': job, 'discard_review': 'yes'})[0], 400)
        self.assertEqual(self.call('/api/audiobook/startover', self.identity() | {'job_id': job, 'extra': 1})[0], 400)
        self.merge.start_over.side_effect = RetryRefused(RETRY_BOOK_CHANGED, 'changed')
        status, body, _ = self.call('/api/audiobook/startover', self.identity() | {'job_id': job})
        self.assertEqual((status, body), (409, {'error': RETRY_BOOK_CHANGED, 'cause': 'changed', 'row': {'id': test_merge_http.ID}}))
        self.assertEqual(self.call('/api/audiobook/release', self.identity())[0], 202)
        items = [{'id': str(uuid.uuid4()), 'revision': 2}, {'id': str(uuid.uuid4()), 'revision': 3}]
        self.assertEqual(self.call('/api/audiobook/release-selected', {'library': 'Audiobooks', 'items': items})[0], 202)
        self.assertEqual(self.merge.release_selected.call_args.args[1], [(items[0]['id'], 2), (items[1]['id'], 3)])
        self.assertEqual(self.call('/api/audiobook/release-selected', {'library': 'Audiobooks', 'items': items + items[:1]})[0], 400, 'each book once')
        self.assertEqual(self.call('/api/audiobook/release-selected', {'library': 'Audiobooks', 'items': []})[0], 400)
        self.assertEqual(self.call('/api/automatic/cancel-start', {})[0], 202)
        automatic.cancel_start.assert_called_once_with()
        self.assertEqual(self.call('/api/automatic/cancel-start', {'x': 1})[0], 400)

