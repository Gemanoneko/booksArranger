"""0.30.0: /api/state 'work' (background_work): every kind of background work as a row or a waiting item, and the blocker of a
queued action with its cause split out (Judy's BooksArranger_0.30.0_UX.md, Notes for Ender). A private catalog with only the
two tables the titles are read from; the engine's state is given as the fields MergeService.live_state() produces."""
import contextlib
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import background_work
from background_work import explain, view

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'background-work-tests'


def jobs_state(**values):
    base = {'state': 'Completed', 'queued': 0, 'queued_conversions': 0, 'cleanups_waiting': 0, 'cleanups_paused': 0, 'cleanups_pending': [],
            'current_job_id': None, 'current_book_id': None, 'current_title': '', 'progress': None, 'retry_checks': {'waiting': 0, 'worker': {}}}
    base.update(values)
    return base


class Engine:
    """The merge attributes background_work reads, over a private catalog."""
    def __init__(self, database):
        self.inventory = SimpleNamespace(database=database)
        self.jobs = SimpleNamespace(_pending_unreserved=lambda priority: [{'job_id': 'job-next'}])
        self.reviews = SimpleNamespace(matching={})


class WorkTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / 'catalog.sqlite3'
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT)')
            db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,evidence TEXT)')
            db.execute('CREATE TABLE book_decisions(request_id TEXT PRIMARY KEY,book_id TEXT,action TEXT,seq INTEGER,accepted_utc TEXT,state TEXT)')
            db.executemany('INSERT INTO book_decisions VALUES(?,?,?,?,?,?)', [('d1', 'book-a', 'names', 1, '2026-11-18T10:00', 'applying'),
                           ('d2', 'book-c', 'approve', 1, '2026-11-18T10:01', 'accepted'), ('d3', 'book-b', 'names', 1, '2026-11-18T09:00', 'applied')])
            for job, book, title in (('job-a', 'book-a', 'Дюна'), ('job-b', 'book-b', 'Похититель детей'), ('job-c', 'book-c', 'Оно'), ('job-next', 'book-n', 'Следующая')):
                db.execute('INSERT INTO audio_jobs VALUES(?,?)', (job, json.dumps({'candidate_id': book, 'metadata': {'title': title}}, ensure_ascii=False)))
                db.execute('INSERT INTO book_groups VALUES(?,?)', (book, json.dumps({'title_clue': title}, ensure_ascii=False)))
        self.engine = Engine(self.database)
        self.server = SimpleNamespace(merge=self.engine, active_library='Audiobooks')

    def work(self, jobs, automatic=None, queue=None, scan=None, roots=None, memo=None, now_ms=1000):
        return view(self.server, jobs, automatic or {'state': 'Idle'}, queue or {'queued_actions': [], 'queue_running': None}, scan is not None, scan, roots, memo, now_ms)

    def test_the_brom_case_names_the_whole_queue_and_every_row_has_its_own_id(self):
        # Sergei 2026-11-18: «Похититель детей» Retry cleanup queued behind one conversion with more waiting; the panel showed
        # research only and the row said "the conversion".
        jobs = jobs_state(state='Running', queued=4, queued_conversions=4, current_job_id='job-a', current_book_id='book-a', current_title='Дюна',
                          progress={'phase': 'encoding', 'completed': 30, 'total': 120, 'unit': 'seconds', 'started': 500})
        queue = {'queued_actions': [{'id': 'q1', 'action': 'cleanup', 'book_id': 'book-b', 'title': 'Похититель детей', 'position': 1, 'blocker': {'kind': 'jobs'}}], 'queue_running': None}
        background_work.explain_queue(queue, jobs, self.engine)
        self.assertEqual(queue['queued_actions'][0]['blocker'], {'kind': 'jobs', 'cause': 'conversion_queue', 'title': None, 'book_id': None, 'count': 5})
        work = self.work(jobs, automatic={'state': 'Running', 'phase': 'research', 'current': {'title': 'Оно', 'source': 'Litres', 'stage': 'searching'},
                                          'research_pass': {'completed': 4, 'total': 30}}, queue=queue)
        self.assertEqual(work['schema'], 'books-work-v1')
        self.assertEqual([(row['id'], row['kind'], row['subject'], row['state'], row['done'], row['total'], row['unit']) for row in work['rows']],
                         [('conversion:job-a', 'conversion', 'Дюна', 'running', 30, 120, 'seconds'), ('research', 'research', 'Оно', 'running', 4, 30, 'books')])
        self.assertEqual(work['rows'][0]['started'], 500, "the engine's own start")
        self.assertEqual(work['rows'][1]['step_text'], 'Litres / searching')
        self.assertEqual([(item['kind'], item['subject'], item['count'], item['ahead']) for item in work['waiting']],
                         [('action', 'Похититель детей', None, 0), ('conversions', 'Следующая', 4, None)])
        self.assertIs(work['waiting'][0]['blocker'], queue['queued_actions'][0]['blocker'], 'one blocker object for the row hint and the Waiting list')
        self.assertEqual(work['counts'], {'tasks_running': 2, 'queued_conversions': 4, 'cleanups_waiting': 0, 'cleanups_paused': 0, 'actions_waiting': 1, 'retry_checks_waiting': 0})
        for row in work['rows']:
            self.assertEqual(tuple(row), background_work.ROW_KEYS)
        for item in work['waiting']:
            self.assertEqual(tuple(item), background_work.ITEM_KEYS)

    def test_each_jobs_cause(self):
        running = dict(current_job_id='job-a', current_book_id='book-a', current_title='Дюна', progress={'phase': 'encoding'})
        cases = [
            (jobs_state(state='Running', **running), 'book-b', {'cause': 'conversion', 'title': 'Дюна', 'book_id': 'book-a', 'count': None}),
            (jobs_state(state='Running', queued_conversions=2, **running), 'book-b', {'cause': 'conversion_queue', 'title': None, 'book_id': None, 'count': 3}),
            (jobs_state(state='Running', **running), 'book-a', {'cause': 'own_conversion', 'title': None, 'book_id': None, 'count': None}),
            (jobs_state(state='Running', current_job_id='job-c', current_book_id='book-c', current_title='Оно', progress={'phase': 'originals'}), 'book-b',
             {'cause': 'cleanup_running', 'title': 'Оно', 'book_id': 'book-c', 'count': None}),
            (jobs_state(state='Running', current_job_id='job-b', current_book_id='book-b', current_title='Похититель детей', progress={'phase': 'originals'}), 'book-b',
             {'cause': 'own_cleanup', 'title': None, 'book_id': None, 'count': None}),
            (jobs_state(state='Paused', queued_conversions=3), 'book-b', {'cause': 'queue_paused', 'title': None, 'book_id': None, 'count': 3}),
            (jobs_state(state='Paused', cleanups_pending=[{'job_id': 'job-c', 'state': 'paused'}]), 'book-b', {'cause': 'cleanup_paused', 'title': 'Оно', 'book_id': 'book-c', 'count': None}),
            (jobs_state(state='Paused', cleanups_pending=[{'job_id': 'job-c', 'state': 'waiting'}]), 'book-b', {'cause': 'cleanup_waiting', 'title': 'Оно', 'book_id': 'book-c', 'count': None}),
            (jobs_state(state='Running'), 'book-b', {'cause': 'checking', 'title': None, 'book_id': None, 'count': None}),
            (jobs_state(state='Completed'), 'book-b', {'cause': 'unknown', 'title': None, 'book_id': None, 'count': None}),
        ]
        for jobs, book, expected in cases:
            queue = {'queued_actions': [{'id': 'q', 'action': 'cleanup', 'book_id': book, 'title': '', 'position': 1, 'blocker': {'kind': 'jobs'}}]}
            background_work.explain_queue(queue, jobs, self.engine)
            self.assertEqual(queue['queued_actions'][0]['blocker'], dict(kind='jobs', **expected), expected['cause'])
        self.assertEqual(explain('operation', {'book_id': 'x'}, jobs_state(), {'title': 'Дюна', 'book_id': 'book-a'}),
                         {'kind': 'operation', 'cause': 'action', 'title': 'Дюна', 'book_id': 'book-a', 'count': None})
        self.assertEqual(explain('operation', {'book_id': 'x'}, jobs_state())['cause'], 'operation', 'another press holds the engine')
        self.assertEqual(explain('retry_run', {}, jobs_state(retry_all={'state': 'running', 'done': 12, 'total': 80}))['count'], 68)
        for kind in ('scan', 'automatic', 'book', 'loading'):
            self.assertEqual(explain(kind, {}, jobs_state())['cause'], kind)

    def test_paused_work_has_rows_and_unstarted_work_waits(self):
        # Judy section 4: three paused cleanups and one queued conversion are 1 book waiting and 3 paused rows, never "4 books".
        jobs = jobs_state(state='Paused', queued=4, queued_conversions=1, cleanups_paused=2, cleanups_waiting=1,
                          current_job_id='job-a', current_book_id='book-a', current_title='Дюна', progress={'phase': 'originals', 'completed': 3, 'total': 9},
                          cleanups_pending=[{'job_id': 'job-a', 'state': 'paused', 'removed': 3, 'total': 9, 'active': True},
                                            {'job_id': 'job-b', 'state': 'paused', 'removed': 0, 'total': 37, 'active': False},
                                            {'job_id': 'job-c', 'state': 'waiting', 'removed': 0, 'total': 5, 'active': False}])
        work = self.work(jobs)
        self.assertEqual([(row['id'], row['state'], row['done'], row['total']) for row in work['rows']],
                         [('cleanup:job-a', 'paused', 3, 9), ('cleanup:job-b', 'paused', 0, 37), ('queue', 'paused', None, None)])
        self.assertEqual((work['rows'][2]['count'], work['rows'][2]['subject']), (1, 'Следующая'))
        self.assertEqual([(item['id'], item['subject']) for item in work['waiting']], [('cleanup:job-c', 'Оно')])
        self.assertEqual((work['counts']['tasks_running'], work['counts']['cleanups_paused'], work['counts']['cleanups_waiting']), (0, 2, 1))

    def test_a_stopped_job_the_status_still_shows_is_never_a_running_row(self):
        # 0.29.0: a job in 'Needs attention' is On hold on the page (read from the jobs fields), not a Running row; a cleanup
        # phase there was drawn as a running cleanup before this check.
        for phase in ('encoding', 'originals'):
            jobs = jobs_state(state='Needs attention', current_job_id='job-a', current_book_id='book-a', current_title='Дюна',
                              progress={'phase': phase, 'completed': 1, 'total': 9})
            self.assertEqual(self.work(jobs)['rows'], [], phase)
        jobs = jobs_state(state='Running', current_job_id='job-a', current_book_id='book-a', current_title='Дюна', progress={'phase': 'originals', 'completed': 1, 'total': 9})
        self.assertEqual([row['id'] for row in self.work(jobs)['rows']], ['cleanup:job-a'], 'positive control: a running cleanup is a row')

    def test_scan_and_research_both_have_rows_and_a_running_action_is_never_hidden(self):
        jobs = jobs_state(state='Running', current_job_id='job-a', current_book_id='book-a', current_title='Дюна', progress={'phase': 'encoding'})
        queue = {'queued_actions': [], 'queue_running': {'id': 'r1', 'action': 'delete', 'book_id': 'book-c', 'title': 'Оно', 'n': 8}}
        work = self.work(jobs, automatic={'state': 'Running', 'phase': 'research', 'current': {'title': 'Оно'}}, queue=queue,
                         scan={'checked': 10, 'pending': 30, 'current': 'Z:/a.mp3'})
        self.assertEqual([row['kind'] for row in work['rows']], ['conversion', 'action', 'scan', 'research'])
        action = work['rows'][1]
        self.assertEqual((action['label_key'], action['subject'], action['count']), ('delete', 'Оно', 8))
        self.assertEqual((work['rows'][2]['done'], work['rows'][2]['total']), (10, 40))
        self.assertEqual(work['rows'][0]['done'], None, 'no amount: the bar slides')

    def test_workers_outside_the_jobs_queue(self):
        release = threading.Event(); self.addCleanup(release.set)
        alive = threading.Thread(target=release.wait, args=(10,), daemon=True); alive.start()
        e = self.engine
        e.gap_fill = SimpleNamespace(thread=alive, status=lambda: {'title': 'Дюна', 'done': 2, 'total': 7})
        e.reviews = SimpleNamespace(matching={'book-c': {'state': 'finding'}, 'book-b': {'state': 'found'}}, _chapter_activity={'book-b': {'file': '01.mp3'}})
        e._repair_running = True; e._repair_pending = ['job-c', 'job-a']
        e._manual_recovery = ('job-b', {'count': 3}); e._manual_presses = [('job-c', {'count': 5})]
        e._regroup_thread = alive; e._move_recovery = alive
        e.decisions = SimpleNamespace(store=SimpleNamespace(database=self.database))
        e._source_progress = {'phase': 'checking', 'done': 120, 'total': 412, 'started': 77}
        e._cleanup_retry_at = {'job-a': time.monotonic() + 60, ('temporary', 'job-c'): time.monotonic() + 30, 'job-old': time.monotonic() - 1}
        work = self.work(jobs_state(maintenance={'state': 'checking', 'job_id': 'job-a', 'title': 'Дюна', 'phase': 'Checking finished-book cleanup'},
                                    series_update={'title': 'Оно', 'done': 1, 'total': 3, 'step': 'updating'},
                                    published_check={'kind': 'background', 'completed': 5, 'total': 50, 'started': 9},
                                    retry_checks={'waiting': 2, 'worker': {'state': 'checking', 'job_id': 'job-b'}},
                                    retry_all={'state': 'running', 'done': 1, 'total': 4, 'mode': 'selected'}))
        kinds = {row['kind']: row for row in work['rows']}
        self.assertEqual(sorted(kinds), sorted(['bulk', 'retry_check', 'maintenance', 'finished_check', 'series', 'gap_fill', 'lookup', 'chapter_check',
                                                'repair_check', 'recovery_delete', 'regroup', 'move_recovery', 'source_check', 'decisions']))
        self.assertEqual((kinds['decisions']['subject'], kinds['decisions']['label_key']), ('Дюна', 'decision_names'))
        self.assertEqual((kinds['gap_fill']['subject'], kinds['gap_fill']['done'], kinds['gap_fill']['total']), ('Дюна', 2, 7))
        self.assertEqual((kinds['lookup']['subject'], kinds['lookup']['label_key']), ('Оно', 'find_metadata'))
        self.assertEqual((kinds['chapter_check']['subject'], kinds['chapter_check']['step_text']), ('Похититель детей', '01.mp3'))
        self.assertEqual((kinds['repair_check']['subject'], kinds['repair_check']['count']), ('Оно', 2))
        self.assertEqual((kinds['retry_check']['subject'], kinds['bulk']['label_key'], kinds['bulk']['done']), ('Похититель детей', 'retry_selected', 1))
        self.assertEqual((kinds['source_check']['done'], kinds['source_check']['total'], kinds['source_check']['started']), (120, 412, 77))
        self.assertEqual((kinds['finished_check']['done'], kinds['series']['step']), (5, 'updating'))
        waiting = [(item['kind'], item['label_key'], item['subject'], item['count']) for item in work['waiting']]
        self.assertEqual(waiting, [('retry_checks', 'retry_checks', None, 2), ('cleanup_retry', 'cleanup_retry', 'Дюна', None),
                                   ('cleanup_retry', 'cleanup_retry_temporary', 'Оно', None), ('recovery_delete', 'recovery_delete', 'Оно', 5),
                                   ('decisions', 'decision_approve', 'Оно', None)])
        self.assertTrue(all(isinstance(item['at'], int) and item['at'] > time.time() * 1000 for item in work['waiting'] if item['kind'] == 'cleanup_retry'))
        self.assertEqual(work['unread'], [])

    def test_a_row_keeps_its_first_seen_time_and_a_source_that_fails_is_named_not_invented(self):
        memo = {}
        jobs = jobs_state(state='Running', current_job_id='job-a', current_book_id='book-a', current_title='Дюна', progress={'phase': 'encoding'})
        self.assertEqual(self.work(jobs, memo=memo, now_ms=1000)['rows'][0]['started'], 1000)
        self.assertEqual(self.work(jobs, memo=memo, now_ms=5000)['rows'][0]['started'], 1000, 'the first poll that saw it')
        self.work(jobs_state(), memo=memo, now_ms=6000)
        self.assertEqual(memo, {}, 'a row that ended leaves the memo')
        self.engine.gap_fill = SimpleNamespace(thread=None, status=lambda: 1 / 0)
        work = self.work(jobs, memo=memo, now_ms=7000)
        self.assertEqual(work['unread'], ['workers'])
        self.assertEqual([row['kind'] for row in work['rows']], ['conversion'], 'the other sources still read')

    def test_automatic_waits_drives_and_a_waiting_resume(self):
        work = self.work(jobs_state(start_waiting={'reason': 'pause'}),
                         automatic={'state': 'Running', 'phase': 'conversion', 'research': {'waiting': 3}, 'next_retry_at': 1795000000, 'start_pending': False},
                         roots=[{'path': 'Z:\\Audiobooks', 'available': False}, {'path': 'Y:\\', 'available': True, 'empty': True}, {'path': 'X:\\', 'available': True}])
        self.assertEqual([(item['kind'], item['label_key'], item['subject']) for item in work['waiting']],
                         [('metadata_sources', 'metadata_sources', None), ('drive', 'drive', 'Z:\\Audiobooks'), ('drive', 'drive_empty', 'Y:\\'),
                          ('resume', 'resume', None), ('automatic', 'automatic_conversion', None)])
        self.assertEqual((work['waiting'][0]['count'], work['waiting'][0]['at']), (3, 1795000000000))


class PressCountTests(unittest.TestCase):
    """0.30.0 (Futaba's QA A): a running press that reports its count (press_progress) has an amount on its row."""

    def test_the_running_press_count_reaches_its_row(self):
        import press_progress, threading
        from action_queue import ActionQueue
        queue = ActionQueue.__new__(ActionQueue)
        queue._runner_ident = threading.get_ident()
        press_progress.clear()  # an earlier test on this thread (the gate runs many modules in one process) may have reported
        self.assertEqual(queue._progress(), {}, 'nothing reported: no amount')
        press_progress.report(3, 300)
        try:
            self.assertEqual(queue._progress(), {'done': 3, 'total': 300, 'unit': 'files'})
        finally:
            press_progress.clear()
        self.assertEqual(queue._progress(), {}, 'cleared when the press ends')
        database = Path(tempfile.mkdtemp(dir=AREA)) / 'catalog.sqlite3'
        with contextlib.closing(sqlite3.connect(database)) as db, db:
            db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT)')
            db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,evidence TEXT)')
        server = SimpleNamespace(merge=Engine(database), active_library='Audiobooks')
        running = {'id': 'q1', 'action': 'approve', 'book_id': 'b1', 'title': 'Дюна', 'done': 3, 'total': 300, 'unit': 'files'}
        work = view(server, jobs_state(), {'state': 'Idle'}, {'queued_actions': [], 'queue_running': running}, False, None, None, None, 1000)
        row = next(row for row in work['rows'] if row['id'] == 'action:q1')
        self.assertEqual((row['done'], row['total'], row['unit']), (3, 300, 'files'))


class SnapshotFreshnessTests(unittest.TestCase):
    """0.30.0 (Futaba's QA A; Sergei's answer 2, the cue "only when behind"): counts a quiet app reuses are confirmed
    current at every poll, so their age is 0; counts a computation the catalog has moved past keep their real age."""

    def service(self):
        import merge_service
        s = merge_service.MergeService.__new__(merge_service.MergeService)
        s.token = 't1'
        s._quiet_token = lambda create=False: s.token
        s.quiet_max_age = lambda: 300.0
        s.state = lambda: {'n': 1}
        return s

    def test_an_idle_app_reads_current_and_a_slow_refresh_shows_its_age(self):
        s = self.service()
        s.status_snapshot(max_age=0.0)
        token, kept_at, value, began = s._quiet_state
        s._quiet_state = (token, kept_at - 45, value, began - 45)  # computed 45 s ago; nothing changed since
        s.status_snapshot(max_age=0.0)
        self.assertLess(s.snapshot_info()['snapshot_age_ms'], 1000, 'quiet: the counts are current, no cue')
        # A commit since (a new token) and the shared computation still answering with the old one: its real age shows.
        s.token = 't2'
        s._status_shared = SimpleNamespace(get=lambda compute, max_age: ('t1', {'n': 1}, time.monotonic() - 45), _flight=object())
        s.status_snapshot(max_age=0.0)
        info = s.snapshot_info()
        self.assertGreaterEqual(info['snapshot_age_ms'], 44000, 'behind: the cue shows')
        self.assertTrue(info['refreshing'])


if __name__ == '__main__':
    unittest.main()
