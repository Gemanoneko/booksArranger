"""v0.16.7 QA NO-GO: an idle app re-read the whole catalog on every poll (about 270 MB/s on the real catalog).

Per-book lookups scanned whole tables, every connection re-ran the schema, the book list read every book
group and every replacement relation per row, and a quiet app recomputed every poll. These tests pin the
fixes: indexes used, schema once per catalog file, prefiltered rows only, one relation read per page,
and reuse while nothing runs and no catalog commit happened.
"""
import contextlib
import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import audio_jobs
import merge_service
import scanner
from audio_jobs import AudioJobs
from merge_service import MergeService
from storage_cleanup import StorageCleanup

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'quiet-status-tests'
AREA.mkdir(parents=True, exist_ok=True)
ALIVE = SimpleNamespace(is_alive=lambda: True)


def opened(path):
    """A connection that is closed on exit (Windows keeps an open catalog file from being removed)."""
    @contextlib.contextmanager
    def scope():
        db = sqlite3.connect(path)
        try:
            with db: yield db
        finally: db.close()
    return scope()


def plan(db, sql):
    return ' '.join(row[-1] for row in db.execute('EXPLAIN QUERY PLAN ' + sql))


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.db = self.base / 'catalog.sqlite3'


class IndexTests(Base):
    def test_per_book_lookups_use_indexes(self):
        jobs = AudioJobs(self.db, None, lambda manifest: True, lambda record: False); self.addCleanup(jobs.close)
        StorageCleanup(self.db, self.base / 'stage', self.base / 'recovery')
        with opened(self.db) as db:
            self.assertIn('storage_cleanup_files_job', plan(db, "SELECT * FROM storage_cleanup_files WHERE job_id='j' AND kind='recovery'"))
            self.assertIn('storage_cleanup_preserved_job', plan(db, "SELECT path FROM storage_cleanup_preserved WHERE job_id='j'"))
            self.assertIn('audio_jobs_state', plan(db, "SELECT * FROM audio_jobs WHERE state='needs attention'"))
            self.assertIn('audio_jobs_candidate', plan(db, "SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id') IN (SELECT value FROM json_each('[]'))"))

    def test_newest_jobs_for_named_books_only(self):
        jobs = AudioJobs(self.db, None, lambda manifest: True, lambda record: False); self.addCleanup(jobs.close)
        with jobs._db() as db:
            for job_id, candidate, created in (('a', 'book-1', '1'), ('b', 'book-1', '2'), ('c', 'book-2', '1')):
                db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)', (job_id, json.dumps({'candidate_id': candidate}), 'h', 'needs attention', 's', None, '{}', None, '', created, created))
            self.assertEqual(jobs._newest_jobs(db, {'book-1'}), {'book-1': 'b'})
            self.assertEqual(jobs._newest_jobs(db), {'book-1': 'b', 'book-2': 'c'})


class ConnectTests(Base):
    def test_schema_is_ensured_once_per_catalog_file(self):
        with scanner.connect(self.db) as db: db.execute('SELECT 1 FROM files').fetchall()
        with patch.object(scanner.ClosingConnection, 'executescript', side_effect=AssertionError('schema again')):
            with scanner.connect(self.db) as db:
                self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
                self.assertEqual(db.execute('PRAGMA busy_timeout').fetchone()[0], 10000)
        os.remove(self.db)
        with scanner.connect(self.db) as db:  # a replaced file is a new identity: the base tables exist again
            self.assertEqual(db.execute('SELECT count(*) FROM files').fetchone()[0], 0)


class GroupsTests(unittest.TestCase):
    def test_prefiltered_page_reads_only_the_listed_rows(self):
        import groups
        db = sqlite3.connect(':memory:'); db.row_factory = sqlite3.Row; seen = []
        db.execute('CREATE TABLE book_groups(id TEXT, root TEXT, superseded INTEGER, scope TEXT)')
        db.executemany('INSERT INTO book_groups VALUES(?,?,?,?)', [('a', 'r', 0, '1'), ('b', 'r', 0, '2'), ('c', 'r', 0, '3'), ('d', 'r', 1, '4')])
        with patch.object(groups, 'sync'), patch.object(groups, 'retired_sources', return_value=set()), \
             patch.object(groups, 'render', side_effect=lambda row, *rest: (seen.append(row['id']), {'id': row['id']})[1]):
            queries = []; db.set_trace_callback(queries.append)
            result = groups.page(db, 'r', ids={'c', 'a', 'd'})
        self.assertEqual(result, {'rows': [{'id': 'a'}, {'id': 'c'}], 'total': 2}); self.assertEqual(seen, ['a', 'c'], 'no other row is rendered')
        self.assertTrue(any('json_each' in query for query in queries), 'the database returns only the listed rows')


class QuietTests(Base):
    """A quiet app (nothing running, no catalog commit since) reuses polling answers; anything else recomputes."""
    def service(self):
        with opened(self.db) as db: db.execute('CREATE TABLE IF NOT EXISTS t(x)')
        s = MergeService.__new__(MergeService)
        s.inventory = SimpleNamespace(database=str(self.db), worker=None)
        s.jobs = SimpleNamespace(_thread=None, _check_progress=None, _resuming=False)
        s.cleanup = SimpleNamespace(thread=None, current=None); s._post_current = None; s.draining = False
        self.computed = 0
        def state():
            self.computed += 1; return {'computed': self.computed}
        s.state = state
        s.reviews = SimpleNamespace(page=Mock(side_effect=lambda *args: {'rows': [], 'total': self.computed}))
        self.addCleanup(lambda: s.__dict__.get('_monitor') and s.__dict__.pop('_monitor').close())
        return s

    def commit(self):
        with opened(self.db) as db: db.execute('INSERT INTO t VALUES(1)')

    def test_status_is_reused_until_a_commit_a_control_or_the_bound(self):
        s = self.service()
        self.assertEqual(s.status_snapshot(0), {'computed': 1})
        self.assertEqual(s.status_snapshot(0), {'computed': 1}, 'quiet: no recomputation, even past the 1 s reuse')
        self.commit(); self.assertEqual(s.status_snapshot(0), {'computed': 2}, 'a catalog commit by any connection')
        s.invalidate_status(); self.assertEqual(s.status_snapshot(0), {'computed': 3}, 'a control')
        with patch.object(merge_service, 'QUIET_MAX_AGE', 0.0):self.assertEqual(s.status_snapshot(0), {'computed': 4}, 'the age bound')
        s.jobs._check_progress = {'kind': 'background', 'completed': 1, 'total': 9}
        self.assertEqual(s.status_snapshot(0), {'computed': 5}, 'the published-book check moved on one book')
        self.assertEqual(s.status_snapshot(0), {'computed': 5})

    def test_running_work_is_never_reused(self):
        s = self.service()
        for field, value in (('jobs', '_thread'), ('cleanup', 'thread'), ('inventory', 'worker')):
            with self.subTest(field=field):
                setattr(getattr(s, field), value, ALIVE); before = self.computed
                s.status_snapshot(0); s.status_snapshot(0); self.assertEqual(self.computed, before + 2)
                self.assertIsNone(s._quiet_token()); setattr(getattr(s, field), value, None)
        s._post_current = ('job', 'temporary'); self.assertIsNone(s._quiet_token()); s._post_current = None

    def test_book_list_page_is_reused_while_quiet(self):
        s = self.service()
        first = s.cached_page(100, 0, '', 'converted'); s.cached_page(100, 0, '', 'converted')
        self.assertEqual(s.reviews.page.call_count, 1); self.assertEqual(first, {'rows': [], 'total': 0})
        s.cached_page(100, 0, '', 'output_attention', 'retry')
        s.reviews.page.assert_called_with(100, 0, '', 'output_attention', 'retry')
        self.commit(); s.cached_page(100, 0, '', 'converted'); self.assertEqual(s.reviews.page.call_count, 3)

    def test_converted_ids_and_cleanup_statuses_follow_the_quiet_state(self):
        s = self.service()
        self.assertIsNone(s._quiet_token(), 'no monitor until a poll opens it: a direct state() stays fresh')
        token = s._quiet_token(True); old = time.monotonic() - 60
        s._converted_cache = (old, {'a'}, token); s._cleanup_kept = (old, token, {'j': {'state': 'completed'}})
        s.progress_books = Mock(return_value={'converted_ids': {'b'}}); s.cleanup = SimpleNamespace(thread=None, current=None, status=Mock(return_value={'state': 'fresh'}))
        self.assertEqual(s.converted_ids(), {'a'}); self.assertEqual(s.cleanup_statuses(['j']), {'j': {'state': 'completed'}})
        self.commit()
        self.assertEqual(s.converted_ids(), {'b'}); self.assertEqual(s.cleanup_statuses(['j']), {'j': {'state': 'fresh'}})


class ServerStateTests(Base):
    def test_poll_reuses_library_and_automatic_status_while_quiet(self):
        from web_server import BrowserServer
        server = BrowserServer.__new__(BrowserServer); server.closing = False; server.active_library = None
        server.inventory = SimpleNamespace(worker=None, roots={'Audiobooks': 'A'}, status=Mock(return_value={'state': 'completed'}), stop_event=threading.Event())
        token = [1]
        server.merge = SimpleNamespace(_quiet_token=lambda: token[0], status_snapshot=lambda: {'state': 'Paused'}, state=lambda: {'state': 'Paused'},
                                       automatic=SimpleNamespace(status=Mock(return_value={'state': 'Idle'})))
        server.health = lambda: {'version': 'x'}
        server.state('Audiobooks', cached=True); server.state('Audiobooks', cached=True)
        self.assertEqual((server.inventory.status.call_count, server.merge.automatic.status.call_count), (1, 1))
        token[0] = 2; server.state('Audiobooks', cached=True); self.assertEqual(server.inventory.status.call_count, 2)
        token[0] = None; server.state('Audiobooks', cached=True); server.state('Audiobooks', cached=True); self.assertEqual(server.inventory.status.call_count, 4, 'busy: fresh every poll')
        server.state('Audiobooks'); self.assertEqual(server.inventory.status.call_count, 5, 'controls stay fresh')


class RepairCheckTests(Base):
    def test_finished_checks_are_saved_once_per_pass_and_loaded_by_the_next_run(self):
        import m4b_repair
        jobs = AudioJobs(self.db, None, lambda manifest: True, lambda record: False); self.addCleanup(jobs.close)
        row = {'job_id': str(uuid.uuid4()), 'manifest_hash': 'h' * 64}
        key = (row['job_id'], row['manifest_hash'], m4b_repair._MODULE_SHA256)
        s = MergeService.__new__(MergeService); s.inventory = SimpleNamespace(database=str(self.db)); s.jobs = jobs
        s._repair_pending = [row['job_id']]; s._repair_skipped = set(); s._repair_running = True; s.invalidate_status = Mock()
        jobs._rows = Mock(return_value=[row])
        with patch.object(m4b_repair, 'classify', return_value={'state': 'unchecked'}), patch.object(m4b_repair, 'check', return_value={'state': 'intact', 'reason': '', 'damage': [], 'repairs': []}) as check, \
             patch.dict(audio_jobs.REPAIR_CHECKS, clear=True), patch.object(merge_service, 'connect', wraps=merge_service.connect) as connected:
            s._load_repair_checks(); writes_before = connected.call_count
            s._repair_check_work(threading.Event())
            self.assertEqual(check.call_count, 1); self.assertEqual(connected.call_count - writes_before, 1, 'one write, at the end of the pass')
            s.invalidate_status.assert_called_once_with()
            audio_jobs.REPAIR_CHECKS.clear()
            other = MergeService.__new__(MergeService); other.inventory = s.inventory
            other._load_repair_checks()
            self.assertEqual(audio_jobs.REPAIR_CHECKS[key]['state'], 'intact', 'the next run starts with the saved answer')
            fields, _ = audio_jobs._m4b_fields({'job_id': row['job_id'], 'manifest_hash': row['manifest_hash']})
            self.assertEqual(fields['state'], 'intact')


if __name__ == '__main__':
    unittest.main()
