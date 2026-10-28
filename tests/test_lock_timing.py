"""0.22.1, backlog items 6-8 (Ender's diagnosis, 2026-10-25): presses must never wait behind background work.

On the live catalog the status computation held Inventory.group_lock for about 500 publication lookups (15 s), on every
research step and every poll; the list, Scan again, Remove from list, Delete and approvals queued behind it (54-100 s),
and an approval ran Start's re-check of every finished book under the operation lock (4-5 min). Real private audio
fixtures; the slow lookup is a stub that sleeps. No network, no library access."""
import threading, time, unittest
from pathlib import Path
from unittest.mock import patch

from merge_service import MergeService
from scanner import connect
from scan_wait import finish_scan, finish_thread as finish


def finish_thread(thread):
    finish(thread, 'A test thread')
from test_approve_as_is import ApproveFixture, tone


class SlowLookup:
    """Every publication lookup sleeps `seconds` first (the live catalog's 433 relocations took 19 s in all)."""
    def __init__(self, service, seconds):
        self.service, self.seconds, self.started = service, seconds, threading.Event()
        self.real = service.publication_bindings.lookup

    def __call__(self, db, record, *args, **kwargs):
        self.started.set(); time.sleep(self.seconds)
        return self.real(db, record, *args, **kwargs)

    def __enter__(self):
        self.service.__dict__.pop('_lookups', None)  # no answer kept from before
        self.patch = patch.object(self.service.publication_bindings, 'lookup', self)
        self.patch.start(); return self

    def __exit__(self, *exc):
        self.patch.stop()


class LockTimingTests(ApproveFixture):
    def converted(self, title='Ясно'):
        tone(self.audio / 'Unsorted' / title / (title + '.mp3'), self.cover, album=title, artist='Иван Петров')

    def approve_all(self, folder='Ясно'):
        for row in self.service.reviews.page()['rows']:
            if all(Path(m['path']).parent.name == folder for m in row['members']):
                self.service.approve_book(row['id'], row['revision'])
        self.start_and_wait()
        jobs = self.service.jobs.status()['jobs']
        self.assertTrue(jobs and all(job['state'] == 'completed' for job in jobs), jobs)
        return jobs

    def timed(self, call):
        started = time.monotonic(); value = call(); return value, time.monotonic() - started

    def in_thread(self, call):
        thread = threading.Thread(target=call, daemon=True); thread.start()
        self.addCleanup(finish_thread, thread)
        return thread

    def test_another_thread_gets_the_group_lock_within_100_ms_during_a_slow_publication_lookup(self):
        self.converted(); self.start(); self.approve_all()
        with SlowLookup(self.service, 2.0) as slow:
            status = self.in_thread(self.service.progress_books)
            self.assertTrue(slow.started.wait(15), 'positive control: the status computation looks the book up')
            got, waited = self.timed(lambda: self.inv.group_lock.acquire(timeout=1.5))
            if got: self.inv.group_lock.release()
            self.assertTrue(got, 'the lookup held group_lock')
            self.assertLess(waited, 0.1)
            finish_thread(status)
        # Positive control: stale groups (the catalog changed) are still rebuilt under the lock, before the read.
        with connect(self.inv.database) as db: db.execute('UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1')
        held, release = threading.Event(), threading.Event()
        def approval():
            with self.inv.group_lock: held.set(); release.wait(30)
        self.in_thread(approval); self.assertTrue(held.wait(5)); self.addCleanup(release.set)
        rebuild = self.in_thread(self.service.progress_books); rebuild.join(1)
        self.assertTrue(rebuild.is_alive(), 'a rebuild waits for the lock')
        release.set(); finish_thread(rebuild)

    def test_the_second_status_reuses_each_lookup_and_a_relocation_change_looks_again(self):
        self.converted(); self.start(); self.approve_all()
        calls = []
        real = self.service.publication_bindings.lookup
        self.service.__dict__.pop('_lookups', None)  # the status polls of wait() kept their answer
        with patch.object(self.service.publication_bindings, 'lookup', lambda db, record, *a, **k: calls.append(1) or real(db, record, *a, **k)):
            first = self.service.progress_books()
            self.assertEqual(len(calls), 1, 'positive control: one finished book, one lookup')
            self.assertEqual(self.service.progress_books(), first); self.assertEqual(len(calls), 1, 'reused: nothing it depends on changed')
            with connect(self.inv.database) as db:
                db.execute('CREATE TABLE IF NOT EXISTS series_backfill(job_id TEXT PRIMARY KEY,state TEXT NOT NULL,reason TEXT NOT NULL,record TEXT NOT NULL,updated TEXT NOT NULL)')
                db.execute("INSERT OR REPLACE INTO series_backfill VALUES('other','done','','{}','2026-10-25T00:00:00Z')")
            self.assertEqual(self.service.progress_books(), first); self.assertEqual(len(calls), 2, 'a completed series backfill looks again')

    def test_remove_from_list_and_the_delete_check_answer_within_1_s_during_a_status_calculation(self):
        self.converted()
        gone = [tone(self.audio / 'Unsorted' / 'Засор' / ('%02d.mp3' % n), self.cover, album='Засор', artist='Михаил Павлов', track='%d/2' % n) for n in (1, 2)]
        self.start(); self.approve_all()
        for path in gone: path.unlink()
        self.inv.launch('Audiobooks'); finish_scan(self.inv)
        missing = [entry for entry in self.service.needs_you().items() if entry[1]['group'] == 'files_missing']
        self.assertEqual(len(missing), 1, 'positive control: the All files missing row')
        identity = missing[0][0]; revision = self.inv.candidate('Audiobooks', identity)['revision']
        with SlowLookup(self.service, 4.0) as slow:
            status = self.in_thread(self.service.state)
            self.assertTrue(slow.started.wait(15))
            preview, took = self.timed(lambda: self.service.delete_preview(identity, revision))
            self.assertIsNone(preview['refusal'], preview); self.assertEqual(preview['files'], [], 'no file is left to delete')
            self.assertLess(took, 1.0, 'the delete check waited behind the status computation')
            removed, took = self.timed(lambda: self.service.dismiss_attention(identity, revision))
            self.assertEqual(removed, {'removed': True}); self.assertLess(took, 1.0, 'Remove from list waited behind the status computation')
            self.assertTrue(status.is_alive(), 'both answered while the status computation was still running')
            finish_thread(status)
        self.assertNotIn(identity, self.service.needs_you(), 'removed from the list')

    def test_scan_again_reads_without_the_group_lock(self):
        tone(self.audio / 'Unsorted' / 'Засор' / '01.mp3', self.cover, album='Засор', artist='Михаил Павлов', track='1/2')
        tone(self.audio / 'Unsorted' / 'Засор' / '02.mp3', self.cover, album='Засор', artist='Михаил Павлов', track='2/2')
        row = self.start()[0]
        held, release = threading.Event(), threading.Event()
        def approval():
            with self.inv.group_lock: held.set(); release.wait(30)
        self.in_thread(approval); self.assertTrue(held.wait(5)); self.addCleanup(release.set)
        receipt, took = self.timed(lambda: self.inv.refresh_candidate_sources('Audiobooks', row['id'], row['revision'], force=False))
        self.assertEqual(receipt['state'], 'unchanged', receipt); self.assertLess(took, 1.0, 'Scan again waited for group_lock')
        # Positive control: a file that changed on disk is written, and the write takes the lock.
        with open(self.audio / 'Unsorted' / 'Засор' / '02.mp3', 'ab') as stream: stream.write(b'\0' * 16)
        results = []
        writer = self.in_thread(lambda: results.append(self.inv.refresh_candidate_sources('Audiobooks', row['id'], row['revision'], force=False)))
        writer.join(1); self.assertTrue(writer.is_alive(), 'the write waits for the lock')
        release.set(); finish_thread(writer)
        self.assertEqual(results[0]['state'], 'refreshed', results)


class ApprovalStartTests(ApproveFixture):
    def test_an_approval_queues_without_start_or_finished_recheck_then_start_converts(self):
        for title in ('Ясно', 'Тихо'):
            tone(self.audio / 'Unsorted' / title / (title + '.mp3'), self.cover, album=title, artist='Иван Петров')
        rows = self.start()
        self.service.approve_book(rows[0]['id'], rows[0]['revision']); self.start_and_wait()
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'], 'completed', 'positive control: one finished book')
        checked = []
        real = MergeService._prune_completed
        def recheck(service, job_id, *args, **kwargs):
            checked.append(job_id); return real(service, job_id, *args, **kwargs)
        settled = []
        real_settle = type(self.service.jobs)._settle
        def settle(jobs, row, *args, **kwargs):
            settled.append(row['job_id']); return real_settle(jobs, row, *args, **kwargs)
        fresh = self.service.reviews.page()['rows']
        second = next(row for row in fresh if row['id'] == rows[1]['id'])
        with patch.object(MergeService, '_prune_completed', recheck), patch.object(type(self.service.jobs), '_settle', settle), \
                patch.object(MergeService, 'state', side_effect=AssertionError('no status computation on the approval path')):
            queued=self.service.approve_book(second['id'], second['revision'])
        self.assertEqual(next(j for j in self.service.jobs.status()['jobs'] if j['job_id']==queued['job_id'])['state'],'pending','Approve waits for Start')
        self.assertEqual(checked, [], 'the approval re-checked the finished books')
        self.assertEqual(settled, [], 'the approval re-checked the published outputs')
        self.start_and_wait()
        self.assertEqual([job['state'] for job in self.service.jobs.status()['jobs']], ['completed', 'completed'], 'Start converts the queued book')
        # Positive control: Start still re-checks every finished book.
        self.service.pause()
        with patch.object(MergeService, '_prune_completed', recheck):self.service.resume()
        self.wait(); self.assertEqual(len(checked), 2)

    def test_a_press_runs_between_two_books_of_starts_recheck(self):
        for title in ('Ясно', 'Тихо'):
            tone(self.audio / 'Unsorted' / title / (title + '.mp3'), self.cover, album=title, artist='Иван Петров')
        for row in self.start():
            self.service.approve_book(row['id'], row['revision'])
        self.start_and_wait(); self.service.pause()
        inside, releases, pressed = threading.Event(), [threading.Event(), threading.Event()], []
        real = MergeService._prune_completed
        def slow(service, job_id, *args, **kwargs):
            inside.set(); releases[len(seen)].wait(10); seen.append(job_id); return real(service, job_id, *args, **kwargs)
        seen = []
        with patch.object(MergeService, '_prune_completed', slow):
            start = threading.Thread(target=self.service.resume, daemon=True); start.start(); self.addCleanup(finish_thread, start)
            self.addCleanup(releases[1].set)
            self.assertTrue(inside.wait(10))
            def press():
                with self.service.operation_lock: pressed.append(time.monotonic())
            waiting = threading.Thread(target=press, daemon=True); waiting.start()
            time.sleep(.3); self.assertEqual(pressed, [], 'positive control: not during one book')
            began = time.monotonic(); releases[0].set(); waiting.join(2)
            self.assertTrue(pressed, 'the press waited for the whole re-check (the second book is still being checked)')
            self.assertLess(pressed[0] - began, 1.0)
            releases[1].set(); finish_thread(start)
        self.assertEqual(len(seen), 2, 'every finished book was still re-checked')


class ApprovalPreviewTests(ApproveFixture):
    def test_the_goes_to_line_is_reused_until_the_book_or_the_rules_change_and_taken_stays_live(self):
        # The to-do list computes this for every held row it shows (0.3 s each on the live catalog: 11-30 s a page during
        # research). Reused while the book, the rules and the catalog facts it reads are unchanged.
        import author_rules
        tone(self.audio / 'Unsorted' / 'Утро снайпера' / '01.mp3', self.cover, album='Утро снайпера', title='Глава 1', track='1/1')
        row = self.start()[0]
        calls = []
        real = self.service.automatic.research.approved
        with patch.object(self.service.automatic.research, 'approved', lambda *a, **k: calls.append(1) or real(*a, **k)):
            first = self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(self.service.approval_preview(row['id'], row['revision']), first)
            self.assertEqual(len(calls), 1, 'reused')
            Path(first['absolute']).parent.mkdir(parents=True); Path(first['absolute']).write_bytes(b'x')
            self.assertTrue(self.service.approval_preview(row['id'], row['revision'])['taken'], 'the name on disk is checked live')
            self.assertEqual(len(calls), 1)
            self.service.approval_preview(row['id'], row['revision'], title='Утро снайпера 2')
            self.assertEqual(len(calls), 2, 'typed values are their own answer')
            with connect(self.inv.database) as db: author_rules.setup(db); author_rules.append(db, 'keep', 'Кто-то Новый', source='test')
            self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(len(calls), 3, 'a new rule computes it again')

    def test_the_goes_to_line_is_reused_while_a_job_only_reports_progress_and_computed_again_when_what_it_reads_changes(self):
        # 2026-10-26: the stamp read max(updated) of every job, which a converting job moves several times a second, so
        # the list computed every held row again while anything converted. Research reads the jobs' manifests (library
        # and confirmed spellings), never their progress. A taken-back rule and an approved book's metadata change it.
        import author_rules, datetime
        tone(self.audio / 'Unsorted' / 'Утро снайпера' / '01.mp3', self.cover, album='Утро снайпера', title='Глава 1', track='1/1')
        row = self.start()[0]
        with connect(self.inv.database) as db:
            author_rules.setup(db); rule = author_rules.append(db, 'keep', 'Кто-то Новый', source='test')
            db.execute('CREATE TABLE IF NOT EXISTS audio_jobs (job_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_hash TEXT NOT NULL, state TEXT NOT NULL, stage TEXT NOT NULL, attempt_id TEXT, journal TEXT NOT NULL, output TEXT, reason TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL)')
            db.execute("INSERT INTO audio_jobs VALUES('fixture-job','{\"candidate_id\":\"elsewhere\"}','h1','Running','encode',NULL,'[]',NULL,'','2026-10-26T00:00:00+00:00','2026-10-26T00:00:00+00:00')")
        calls = []
        real = self.service.automatic.research.approved
        def moment():
            return datetime.datetime.now(datetime.timezone.utc).isoformat()
        with patch.object(self.service.automatic.research, 'approved', lambda *a, **k: calls.append(1) or real(*a, **k)):
            first = self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(len(calls), 1)
            for _ in range(3):
                time.sleep(0.01)
                with connect(self.inv.database) as db: db.execute("UPDATE audio_jobs SET updated=?,stage='encode' WHERE job_id='fixture-job'", (moment(),))
                self.assertEqual(self.service.approval_preview(row['id'], row['revision']), first)
            self.assertEqual(len(calls), 1, 'progress of a job is not something the line reads')
            with connect(self.inv.database) as db: db.execute("UPDATE audio_jobs SET manifest_hash='h2' WHERE job_id='fixture-job'")
            self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(len(calls), 2, 'a rewritten manifest (series backfill) computes it again')
            with connect(self.inv.database) as db: author_rules.retract(db, rule, source='test')
            self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(len(calls), 3, 'a taken-back rule computes it again')
            with connect(self.inv.database) as db:
                db.execute('CREATE TABLE IF NOT EXISTS candidate_context(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,data TEXT NOT NULL)') if not db.execute("SELECT 1 FROM sqlite_master WHERE name='candidate_context'").fetchone() else None
                db.execute("INSERT INTO candidate_context(id,revision,data) VALUES('fixture-context',1,'{}')")
            self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(len(calls), 4, "another book's saved or approved metadata (confirmed spellings) computes it again")


class ListReadLimitTests(ApproveFixture):
    # The limit leaves the gate (seven workers at once) room: one page took 0.2-2.0 s alone on a live-sized catalog (1,572
    # books, 508 finished; see live_sized), and 21 s on 0.22.0 code during a status computation; the live list took 54-100 s.
    PAGE_LIMIT = 8.0
    timed = LockTimingTests.timed

    def test_the_book_list_answers_within_its_limit_on_a_live_sized_catalog_even_during_a_status_computation(self):
        import live_sized
        tone(self.audio / 'Unsorted' / 'Ясно' / 'Ясно.mp3', self.cover, album='Ясно', artist='Иван Петров')
        row = self.start()[0]; self.service.approve_book(row['id'], row['revision']); self.start_and_wait()
        live_sized.grow(self.inv)
        reviews = self.service.reviews
        self.assertEqual(reviews.page(100, 0, '', 'all')['total'], live_sized.LIVE['books'] + 1, 'positive control: a live-sized catalog')
        with SlowLookup(self.service, 0.02) as slow:  # about 10 s for 509 books (the live catalog's 433 relocations took 19 s)
            self.service.state()  # the first status computation after startup: every lookup once
            self.assertEqual(len(self.service.jobs.status()['jobs']), live_sized.LIVE['finished'] + 1)
            for status in ('converted', 'output_attention', 'all'):
                page, took = self.timed(lambda: reviews.page(100, 0, '', status))
                self.assertLess(took, self.PAGE_LIMIT, status)
            # A status computation that takes longer than the list's 30 s reuse window, as on the live catalog under load.
            self.service._converted_cache = (time.monotonic() - 31, self.service._converted_cache[1], None)
            self.service.__dict__.pop('_lookups', None); slow.started.clear()
            status = threading.Thread(target=self.service.state, daemon=True); status.start(); self.addCleanup(finish_thread, status)
            self.assertTrue(slow.started.wait(30))
            page, took = self.timed(lambda: reviews.page(100, 0, '', 'converted'))
            self.assertEqual(page['total'], 1, 'the converted fixture book')
            self.assertLess(took, self.PAGE_LIMIT, 'the list waited for the status computation')
            self.assertTrue(status.is_alive(), 'answered while the status computation was still running')
            finish_thread(status)


if __name__ == '__main__':
    unittest.main()
