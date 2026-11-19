"""Join into one book (0.30.0 item D; Judy's 0.30.0 spec, section 8; Sergei's answers, round 2: 8 review, 9 yes).

The real case, «Впусти меня»: five single-file .m4b parts, one album, tracks 1/5 to 5/5, each its own part title and its own
chapters starting again at chapter 1, so part_sets.decide keeps them as separate volumes. Sergei joins them: the join
records one book (A12), sets aside the parts' queued and failed jobs, withdraws accepted Retry and Repair requests, drops
approvals, all in one transaction, and waits for a part that converts now. Answer 9: Cancel withdraws an accepted Retry or
Repair that has not started. Synthetic tags and tiny private audio (ffmpeg); no network, no library access."""
import json, threading, time, unittest, uuid
from pathlib import Path
from unittest import mock

import background_work
import book_join
import groups
import m4b_readmission
import test_approve_as_is
from action_queue import ActionQueue
from scanner import connect
from test_m4b_join import part
from test_split_books import row as catalog_row

ALBUM, ARTIST = 'Впусти меня', 'John Ajvide Lindqvist'


class GroupingTests(unittest.TestCase):
    """groups.build with a join record: Sergei's join wins over the planners and the separate-volume facts."""
    def files(self):
        return [catalog_row('Lindqvist/Впусти меня/Впусти меня. Часть %d.m4b' % n, {'album': ALBUM, 'artist': ARTIST,
                'title': 'Впусти меня. Часть %d' % n, 'track': '%d/3' % n}) for n in (1, 2, 3)]

    def test_joined_files_are_one_book_in_his_order_over_the_volume_facts(self):
        rows = self.files(); paths = [r['path'] for r in rows]
        volumes = frozenset(paths)
        self.assertEqual(len(groups.build(rows, volumes=volumes)), 3, 'positive control: separate volumes without the join')
        order = (paths[2], paths[0], paths[1])
        built = groups.build(rows, volumes=volumes, joins={'j1': (order, ALBUM)})
        self.assertEqual(len(built), 1, list(built))
        scope, group = next(iter(built.items()))
        self.assertEqual(scope, book_join.scope(order, 'j1'))
        self.assertEqual([m['path'] for m in group['members']], list(order))
        self.assertEqual([m['track'] for m in group['members']], [1, 2, 3])
        self.assertEqual(group['joined']['join_id'], 'j1'); self.assertEqual(group['title_clue'], ALBUM)
        self.assertEqual(group['grouping'], book_join.GROUPING)
        self.assertFalse([c for c in group['conflicts'] if 'clues' in c or 'Series' in c], group['conflicts'])

    def test_a_join_with_a_file_gone_lapses_and_a_named_anthology_keeps_its_stories(self):
        rows = self.files(); paths = [r['path'] for r in rows]
        built = groups.build(rows[:2], joins={'j1': (tuple(paths), ALBUM)})
        self.assertFalse(any(g.get('joined') for g in built.values()), 'a file of the join is not in the catalog: no joined book')


class OrderTests(unittest.TestCase):
    """Judy 8.3 and 8.4 on synthetic parts (no catalog)."""
    def part(self, name, track=None, total=None, title=None, album=''):
        tags = {'album': album, 'title': title or name}
        if track is not None:
            tags['track'] = '%d/%d' % (track, total) if total else str(track)
        row = {'members': [{'path': 'Z:\\Books\\%s.m4b' % name, 'metadata': {'tags': tags}, 'duration': 3600}], 'title_clue': name}
        found_track, found_total = book_join.track_of(row)
        return {'row': row, 'title': book_join.part_title(row), 'track': found_track, 'track_total': found_total}

    def test_album_tracks_order_every_part_and_say_what_is_missing_or_claimed_twice(self):
        parts = [self.part('c', 3, 5), self.part('a', 1, 5), self.part('b', 2, 5), self.part('e', 5, 5), self.part('d', 4, 5)]
        ordered, basis = book_join.order(parts)
        self.assertEqual([p['track'] for p in ordered], [1, 2, 3, 4, 5])
        self.assertEqual(basis, {'basis': 'album_tracks', 'first': 1, 'last': 5, 'total': 5, 'missing': [], 'duplicate': None})
        ordered, basis = book_join.order([p for p in parts if p['track'] != 3])
        self.assertEqual((basis['missing'], basis['total']), ([3], 5), 'a missing part warns; it does not refuse')
        ordered, basis = book_join.order(parts + [self.part('b2', 2, 5)])
        self.assertEqual(basis['duplicate'], 2)

    def test_file_names_then_no_evidence(self):
        ordered, basis = book_join.order([self.part('Впусти меня 5'), self.part('Впусти меня 2'), self.part('Впусти меня 10')])
        self.assertEqual(basis['basis'], 'file_names')
        self.assertEqual([p['title'] for p in ordered], ['Впусти меня 2', 'Впусти меня 5', 'Впусти меня 10'])
        ordered, basis = book_join.order([self.part('Бета'), self.part('Альфа')])
        self.assertEqual((basis['basis'], [p['title'] for p in ordered]), ('none', ['Альфа', 'Бета']), 'file-name order')

    def test_proposed_title_is_the_shared_album_else_the_shared_words_without_part_numbers(self):
        self.assertEqual(book_join.proposed_title([self.part('a', album=ALBUM), self.part('b', album=ALBUM + ' CD2')]), ALBUM)
        self.assertEqual(book_join.proposed_title([self.part('Впусти меня 5'), self.part('Впусти меня')]), ALBUM)
        self.assertEqual(book_join.proposed_title([self.part('x', title='Впусти меня. Часть 1'), self.part('y', title='Впусти меня. Часть 2')]), ALBUM)
        self.assertEqual(book_join.proposed_title([self.part('Альфа'), self.part('Бета')]), '', 'nothing shared: empty, Type a title first')


class JoinFixture(test_approve_as_is.ApproveFixture):
    """The «Впусти меня» shape through the real catalog: the set is researched, found to be volumes, and regrouped."""
    def folder(self):
        return self.audio / 'Unsorted' / 'Линдквист - Впусти меня'

    def parts(self, numbers=(1, 2, 3, 4, 5), total=5):
        return [part(self.folder() / ('Впусти меня %d.m4b' % n), 'Впусти меня %d' % n, n,
                     [(0, 500, 'Глава 1'), (500, 1000, 'Глава 2 (часть %d)' % n)], album=ALBUM, artist=ARTIST, total=total) for n in numbers]

    def volumes(self, numbers=(1, 2, 3, 4, 5), total=5):
        sources = self.parts(numbers, total)
        rows = self.start()
        self.assertEqual([len(r['members']) for r in rows], [len(numbers)], 'one set until its chapters are read')
        result = self.research(rows[0])
        self.assertEqual(result['part_set']['decision'], 'volumes', 'positive control: the real case is kept as separate volumes')
        rows = self.rows()
        self.assertEqual(len(rows), len(numbers), 'each part its own book')
        by_track = {book_join.track_of(r)[0]: r for r in rows}
        return sources, [by_track[n] for n in numbers]

    def rows(self):
        return self.service.reviews.page()['rows']

    def items(self, rows):
        return [{'id': r['id'], 'revision': r['revision']} for r in rows]


class PreviewTests(JoinFixture):
    def test_the_real_case_previews_in_album_order_with_title_author_and_goes_to(self):
        _sources, rows = self.volumes()
        shuffled = [rows[2], rows[0], rows[4], rows[1], rows[3]]
        found = self.service.join_preview(self.items(shuffled))
        self.assertEqual([p['track'] for p in found['parts']], [1, 2, 3, 4, 5])
        self.assertEqual([p['title'] for p in found['parts']], ['Впусти меня %d' % n for n in range(1, 6)])
        self.assertEqual(found['order'], {'basis': 'album_tracks', 'first': 1, 'last': 5, 'total': 5, 'missing': [], 'duplicate': None})
        self.assertEqual(found['title'], ALBUM)
        self.assertEqual(found['author'], 'Lindqvist John Ajvide', found['authors'])
        self.assertEqual(found['refusals'], [])
        self.assertEqual(found['effects'], {'queued': 0, 'failed': 0, 'requests': 0, 'approvals': 0})
        self.assertTrue(found['goes_to']['path'].endswith('Впусти меня - Lindqvist John Ajvide.m4b'), found['goes_to'])
        first = found['parts'][0]
        self.assertEqual((first['files'], first['track_total'], first['state'], first['has_queued_job']), (1, 5, 'candidate', False))
        self.assertGreater(first['hours'], 0)
        typed = self.service.join_preview(self.items(rows), title='Let Me In', author='John Ajvide Lindqvist')
        self.assertEqual(set(typed), {'goes_to'}); self.assertIn('Let Me In', typed['goes_to']['path'])

    def test_refusals_name_a_changed_a_gone_and_a_finished_part(self):
        _sources, rows = self.volumes((1, 2, 3), 3)
        items = self.items(rows)
        items[1]['revision'] += 1
        items.append({'id': str(uuid.uuid4()), 'revision': 1})
        found = self.service.join_preview(items)
        self.assertEqual(sorted(r['cause'] for r in found['refusals']), ['changed', 'gone'])
        with self.assertRaises(book_join.Refused) as refused:
            self.service.join_books(items, ALBUM)
        self.assertIn('Nothing was joined.', str(refused.exception))
        self.assertEqual(len(self.rows()), 3, 'nothing joined')


class JoinTests(JoinFixture):
    def test_the_join_records_one_candidate_that_research_never_splits_again_and_converts_every_chapter(self):
        sources, rows = self.volumes((1, 2, 3), 3)
        before = [(p.stat().st_size, p.stat().st_mtime_ns) for p in sources]
        answer = self.service.join_books(self.items(rows), ALBUM, 'John Ajvide Lindqvist')
        self.assertEqual((answer['title'], answer['parts'], answer['queued'], answer['failed'], answer['requests']), (ALBUM, 3, 0, 0, 0))
        listed = self.rows()
        self.assertEqual(len(listed), 1, [r['title_clue'] for r in listed])
        joined = listed[0]
        self.assertEqual(joined['id'], answer['book_id'])
        self.assertEqual([Path(m['path']).name for m in joined['members']], ['Впусти меня %d.m4b' % n for n in (1, 2, 3)])
        self.assertFalse(joined['metadata_approved'], 'answer 8: the joined book stays a candidate for Sergei to approve')
        self.assertEqual([(p.stat().st_size, p.stat().st_mtime_ns) for p in sources], before, 'A12: no file touched')
        ctx = self.service.reviews._context(joined)
        self.assertEqual(ctx['names_approval_pending'], {'revision': joined['revision'], 'fingerprint': joined['fingerprint']})
        self.assertTrue(self.service.automatic.manual_draft(joined), 'automatic processing holds it for his approval')
        result = self.research(joined)
        self.assertEqual(result['part_set']['decision'], 'join'); self.assertNotIn('Separate books of a series', result['reasons'])
        self.assertEqual(len(self.rows()), 1, 'research never splits the joined book again')
        # A13: M4B chapters are flat; each part keeps its own chapters in order (ruling 19a); nothing is nested.
        self.service.approve_book(joined['id'], joined['revision']); self.start_and_wait()
        job = self.service.jobs.status()['jobs'][0]; self.assertEqual(job['state'], 'completed', job)
        self.assertEqual(job['manifest']['metadata']['title'], ALBUM)
        self.assertEqual([c['title'] for c in job['output']['validation']['chapters']],
                         [title for n in (1, 2, 3) for title in ('Глава 1', 'Глава 2 (часть %d)' % n)])

    def test_a_kept_separate_answer_is_replaced_by_the_join_and_the_rows_regroup_the_same_after_a_rescan(self):
        _sources, rows = self.volumes((1, 2), 2)
        answer = self.service.join_books(self.items(rows), ALBUM)
        with connect(self.inv.database) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM part_volumes').fetchone()[0], 0, 'the volume facts are replaced')
            db.execute('DELETE FROM book_group_sync')
        listed = self.rows()
        self.assertEqual([r['id'] for r in listed], [answer['book_id']], 'a regroup keeps the joined book and its id')


class EffectTests(JoinFixture):
    """Judy 8.5, each effect, and the one transaction."""
    def stage(self):
        """Three parts: 1 approved and queued, 2 approved with a failed job and an accepted Repair, 3 a plain candidate."""
        _sources, rows = self.volumes((1, 2, 3), 3)
        queued = self.service.approve_book(rows[0]['id'], rows[0]['revision'])['job_id']
        failed = self.service.approve_book(rows[1]['id'], rows[1]['revision'])['job_id']
        with connect(self.inv.database) as db:
            db.execute("UPDATE audio_jobs SET state='needs attention',reason='Damaged part' WHERE job_id=?", (failed,))
        with connect(self.inv.database) as db:
            m4b_readmission.request(db, failed, 'repair', time.time())
        current = {r['id']: r for r in self.rows()}
        return [current[r['id']] for r in rows], queued, failed

    def state(self, job_id):
        with connect(self.inv.database) as db:
            row = db.execute('SELECT state FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()
            aside = db.execute('SELECT kind FROM audio_job_set_aside WHERE job_id=?', (job_id,)).fetchone() if db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='audio_job_set_aside'").fetchone() else None
            request = db.execute('SELECT state FROM m4b_readmissions WHERE parent_job_id=?', (job_id,)).fetchone()
        return row[0], aside[0] if aside else None, request[0] if request else None

    def test_preview_counts_every_effect_and_the_join_does_each_one(self):
        rows, queued, failed = self.stage()
        found = self.service.join_preview(self.items(rows))
        self.assertEqual(found['effects'], {'queued': 1, 'failed': 1, 'requests': 1, 'approvals': 2})
        self.assertEqual([(p['has_queued_job'], p['has_failed_job'], p['has_repair_request'], p['has_approval']) for p in found['parts']],
                         [(True, False, False, True), (False, True, True, True), (False, False, False, False)])
        self.assertEqual(self.service.jobs.status()['queued'], 1, 'positive control: one conversion waits')
        self.assertEqual(self.service.jobs.status()['failed'], 1, 'positive control: one entry in Needs attention')
        answer = self.service.join_books(self.items(rows), ALBUM)
        self.assertEqual({k: answer[k] for k in ('queued', 'failed', 'requests', 'approvals')}, {'queued': 1, 'failed': 1, 'requests': 1, 'approvals': 2})
        self.assertEqual(self.state(queued), ('needs attention', 'join', None), 'taken off the queue; the record stays')
        self.assertEqual(self.state(failed), ('needs attention', 'join', 'withdrawn'), 'set aside; its accepted Repair withdrawn')
        status = self.service.jobs.status()
        self.assertEqual((status['queued'], status['failed']), (0, 0), 'they leave the queue, Needs attention and its counts')
        with connect(self.inv.database) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM audio_jobs').fetchone()[0], 2, 'history kept')
            reason = db.execute('SELECT reason FROM audio_jobs WHERE job_id=?', (queued,)).fetchone()[0]
        self.assertEqual(reason, book_join.JOIN_REASON)
        joined = self.rows()
        self.assertEqual(len(joined), 1); self.assertFalse(joined[0]['metadata_approved'], 'approvals removed; the joined book is not approved')

    def test_all_or_nothing(self):
        rows, queued, failed = self.stage()
        with mock.patch.object(m4b_readmission, 'withdraw', side_effect=RuntimeError('fault after the job writes')):
            with self.assertRaises(RuntimeError):
                self.service.join_books(self.items(rows), ALBUM)
        self.assertEqual(self.state(queued), ('pending', None, None))
        self.assertEqual(self.state(failed), ('needs attention', None, 'queued'))
        with connect(self.inv.database) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM sqlite_master WHERE name='book_joins'").fetchone()[0] and
                             db.execute('SELECT count(*) FROM book_joins').fetchone()[0], 0, 'no join recorded')
        self.assertEqual(sorted(r['id'] for r in self.rows()), sorted(r['id'] for r in rows), 'every part still its own book')
        self.service.join_books(self.items(rows), ALBUM)  # positive control: the same join goes through without the fault
        self.assertEqual(len(self.rows()), 1)

    def test_a_part_converting_now_makes_the_join_wait_never_refused_or_aborted(self):
        rows, queued, _failed = self.stage()
        ids = [r['id'] for r in rows]
        self.assertFalse(book_join.busy(self.service, ids), 'positive control: nothing converts')
        with self.service.jobs._lock:
            self.service.jobs._claimed = queued  # the worker took part 1's job: it converts now
        try:
            self.assertTrue(book_join.busy(self.service, ids))
            with self.assertRaises(book_join.Busy):
                self.service.join_books(self.items(rows), ALBUM)
            self.assertEqual(self.state(queued)[:2], ('pending', None), 'never set aside under the worker')
            server = mock.Mock(); server.loading = None; server.merge = self.service; server.scan_active.return_value = False
            self.assertEqual(ActionQueue(server, store=False).blocker('join', ids[0], parts=ids), 'book')
            blocker = background_work.explain('book', {'action': 'join', 'parts': ids}, {'current_book_id': ids[0], 'current_job_id': queued, 'current_title': 'Впусти меня 1'})
            self.assertEqual((blocker['cause'], blocker['title'], blocker['book_id']), ('conversion', 'Впусти меня 1', ids[0]))
        finally:
            with self.service.jobs._lock:
                self.service.jobs._claimed = None
        self.assertIsNone(ActionQueue(server, store=False).blocker('join', ids[0], parts=ids), 'it runs once the part is no longer converting')
        self.assertEqual(self.service.join_books(self.items(rows), ALBUM)['parts'], 3)


class WithdrawTests(JoinFixture):
    """Answer 9: Cancel on a row whose accepted Retry or Repair has not started (m4b_readmission.withdraw)."""
    def failed(self):
        _sources, rows = self.volumes((1, 2), 2)
        job = self.service.approve_book(rows[0]['id'], rows[0]['revision'])['job_id']
        with connect(self.inv.database) as db:
            db.execute("UPDATE audio_jobs SET state='needs attention',reason='Damaged part' WHERE job_id=?", (job,))
        with connect(self.inv.database) as db:
            m4b_readmission.request(db, job, 'repair', time.time())
        row = next(r for r in self.rows() if r['id'] == rows[0]['id'])
        return row, job

    def test_cancel_withdraws_an_accepted_repair_and_it_may_be_pressed_again(self):
        row, job = self.failed()
        with connect(self.inv.database) as db:
            self.assertTrue(m4b_readmission.describe(db, job)['queued_next'], 'positive control: accepted, waiting')
        self.assertEqual(self.service.withdraw_readmission('Audiobooks', row['id'], row['revision'], job), {'withdrawn': True, 'kind': 'repair'})
        with connect(self.inv.database) as db:
            self.assertIsNone(m4b_readmission.describe(db, job), 'reads as never pressed')
            self.assertEqual(m4b_readmission._order(db), [], 'out of the queue-next order')
            self.assertEqual(m4b_readmission.request(db, job, 'repair', time.time())['state'], 'queued', 'pressed again: accepted again')

    def test_too_late_once_its_check_began_or_its_child_exists(self):
        from audio_jobs import RetryRefused
        row, job = self.failed()
        with self.service.jobs._lock:
            self.service.jobs._priority_status = {'state': 'checking', 'job_id': job, 'reason': ''}
        try:
            with self.assertRaises(RetryRefused) as refused:
                self.service.withdraw_readmission('Audiobooks', row['id'], row['revision'], job)
            self.assertEqual(refused.exception.cause, 'started')
        finally:
            self.service.jobs.report_priority({'state': 'idle', 'job_id': None, 'reason': ''})
        child = str(uuid.uuid4())
        with connect(self.inv.database) as db:  # its check admitted a new job, which runs next: too late as well
            manifest = json.dumps({'candidate_id': row['id'], 'candidate_revision': row['revision']})
            db.execute("INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)", (child, manifest, 'x', 'pending', 'queued', None, '{}', None, '', 'z', 'z'))
            db.execute("UPDATE m4b_readmissions SET state='admitted',child_job_id=? WHERE parent_job_id=?", (child, job))
        with connect(self.inv.database) as db:
            self.assertTrue(m4b_readmission.describe(db, job)['queued_next'], 'positive control: still accepted, its new job waits')
        with self.assertRaises(RetryRefused) as refused:
            self.service.withdraw_readmission('Audiobooks', row['id'], row['revision'], job)
        self.assertEqual(refused.exception.cause, 'started')

    def test_a_request_withdrawn_while_its_check_admitted_a_child_never_runs_the_child(self):
        row, job = self.failed()
        child = str(uuid.uuid4())
        def admit(parent, kind):
            with connect(self.inv.database) as db:
                manifest = json.dumps({'candidate_id': row['id'], 'candidate_revision': row['revision']})
                db.execute("INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)", (child, manifest, 'x', 'pending', 'queued', None, '{}', None, '', 'z', 'z'))
                m4b_readmission.withdraw(db, parent, time.time())  # Cancel landed while the check ran
            return {'requeued': True, 'job_id': child}
        self.assertIsNone(m4b_readmission.next_job(self.service.jobs._db, admit, time.time()))
        with connect(self.inv.database) as db:
            state = db.execute('SELECT state FROM audio_jobs WHERE job_id=?', (child,)).fetchone()[0]
            aside = db.execute('SELECT kind FROM audio_job_set_aside WHERE job_id=?', (child,)).fetchone()
        self.assertEqual((state, aside[0] if aside else None), ('needs attention', 'withdrawn'))


class HttpTests(JoinFixture):
    """The page's routes through the REAL server (the 0.29.0 PA-1 pattern): preview, the queued join and its outcome, and
    answer 9's Cancel."""
    def serve(self):
        import web_server
        from test_http_0290 import RealServerTests
        self.service.start_retention = lambda admission: None
        self.service.start_published_check = lambda: None
        self.server = web_server.BrowserServer(('127.0.0.1', 0), self.inv, lambda inventory, cache, progress=None: self.service)
        self.assertNotEqual(self.server.server_port, 5210, 'never Sergei\'s app port')
        threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .05}, daemon=True).start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close()))
        self.call = lambda route, body=None, method='POST': RealServerTests.call(self, route, body, method)

    def test_preview_then_the_queued_join_and_its_outcome(self):
        _sources, rows = self.volumes((1, 2, 3), 3)
        self.serve()
        items = self.items(rows)
        status, preview = self.call('/api/candidate/join-preview', {'library': 'Audiobooks', 'items': items})
        self.assertEqual(status, 200, preview)
        self.assertEqual(([p['track'] for p in preview['parts']], preview['title'], preview['blocked']), ([1, 2, 3], ALBUM, None))
        status, typed = self.call('/api/candidate/join-preview', {'library': 'Audiobooks', 'items': items, 'title': 'Let Me In', 'author': ''})
        self.assertEqual((status, set(typed)), (200, {'goes_to'}))
        status, answer = self.call('/api/candidate/join', {'library': 'Audiobooks', 'items': items, 'title': ALBUM, 'author': 'John Ajvide Lindqvist', 'queue': True})
        self.assertEqual(status, 202, answer); self.assertTrue(answer['queued'])
        deadline = time.monotonic() + 60
        while True:
            status, state = self.call('/api/state?library=Audiobooks', method='GET')
            outcome = next((o for o in (state or {}).get('queue_outcomes') or [] if o.get('action') == 'join'), None)
            if outcome:
                break
            self.assertLess(time.monotonic(), deadline, 'the queued join ran')
            time.sleep(.1)
        self.assertEqual((outcome['result'], outcome['answer']['parts'], outcome['answer']['title']), ('done', 3, ALBUM), outcome)
        self.assertEqual([r['id'] for r in self.rows()], [outcome['answer']['book_id']])
        status, refused = self.call('/api/candidate/join', {'library': 'Audiobooks', 'items': items, 'title': ALBUM})
        self.assertEqual((status, refused['code']), (409, 'gone'), 'the parts are gone now: nothing joined twice')
        status, bad = self.call('/api/candidate/join-preview', {'library': 'Audiobooks', 'items': items[:1]})
        self.assertEqual(status, 400, 'one book is no join')


def setUpModule():
    global _no_original_title_wait
    from original_title_fixture import no_wait
    _no_original_title_wait = no_wait()


def tearDownModule():
    _no_original_title_wait.stop()


if __name__ == '__main__':
    unittest.main()
