"""Sergei, 2026-10-18: once a book's output is verified and its originals matched, all its backups go, in any case.

The purge mechanics (full output verification, missing copies, rerun, catalog state) are tested on real
fixtures in test_recovery_retention, test_cleanup_resume and test_replacement_jobs. These tests pin the
service wiring: the sweep never waits for queued or converting books, and marker-held cleanups finish.
"""
import contextlib
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from audio_jobs import RetryRefused
from merge_service import MergeService
from recovery_retention import AUDIOBOOK_MISSING, AUDIOBOOK_UNVERIFIED, kept_reason


def service():
    s = MergeService.__new__(MergeService)
    s.operation_lock = threading.RLock(); s.inventory = SimpleNamespace(worker=None)
    s._retention_stop = threading.Event(); s._retention_wake = threading.Event(); s._retention_thread = None
    s._manual_recovery = None; s._post_current = None; s.storage_cleanup = None
    s.working = SimpleNamespace(reconcile=lambda **kwargs: None, schedule_published=lambda job_id: None)
    s.jobs = SimpleNamespace(_thread=SimpleNamespace(is_alive=lambda: True), has_unfinished=lambda: True, status=lambda: {'jobs': [{'state': 'pending'}]})
    s.cleanup = SimpleNamespace(thread=None, current=None, _rows=lambda *args: [], resume=Mock())
    return s


@contextlib.contextmanager
def running(s):
    s.start_retention(contextlib.nullcontext)
    try: yield
    finally:
        s._retention_stop.set(); s._retention_wake.set(); s._retention_thread.join(10)


class SweepTests(unittest.TestCase):
    def test_every_set_is_purged_while_books_convert_and_wait(self):
        s = service(); purged = []; done = threading.Event()
        s.recovery = SimpleNamespace(due=lambda: ['job-a', 'job-b'], purge=lambda job_id, *rest: (purged.append(job_id), len(purged) == 2 and done.set()), _set=Mock())
        with running(s): self.assertTrue(done.wait(10))
        self.assertEqual(purged, ['job-a', 'job-b']); s.recovery._set.assert_not_called()

    def test_a_failed_set_is_kept_flagged_and_tried_once_per_run(self):
        s = service(); calls = []; done = threading.Event()
        def purge(job_id, *rest):
            calls.append(job_id); done.set(); raise ValueError('Completed output bytes changed; copies retained')
        s.recovery = SimpleNamespace(due=lambda: ['job-a'], purge=purge, _set=Mock())
        with running(s):
            self.assertTrue(done.wait(10)); s._retention_wake.set(); s._retention_wake.set()
        self.assertEqual(calls, ['job-a'], 'never retried in a loop')
        s.recovery._set.assert_called_once_with('job-a', 'needs_attention', 'Completed output bytes changed; copies retained')


class HeldCleanupTests(unittest.TestCase):
    def test_marker_held_cleanups_finish_on_their_own_once(self):
        s = service(); s.jobs._thread = None; s._purge_tried = set()
        s.cleanup._rows = lambda *args: [{'id': 'c1', 'reason': 'Download marker native identity differs'},
                                         {'id': 'c2', 'reason': 'Unknown download marker contents preserved'},
                                         {'id': 'c3', 'reason': 'Download marker native identity differs'}]
        s._finish_held_cleanups(); s._finish_held_cleanups()
        s.cleanup.resume.assert_called_once_with(['c1', 'c2', 'c3'], follow_audio=False)

    def test_they_wait_while_a_book_converts(self):
        s = service(); s._purge_tried = set()
        s.cleanup._rows = lambda *args: [{'id': 'c1', 'reason': 'Download marker native identity differs'}]
        s._finish_held_cleanups(); s.cleanup.resume.assert_not_called()


class KeptFilesTests(unittest.TestCase):
    """The two keep-cases as attention groups (Judy's spec section 3) and the Keep files choice."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.addCleanup(folder.cleanup)
        self.database = os.path.join(folder.name, 'catalog.sqlite3')
        db = sqlite3.connect(self.database)
        try:
            with db:
                db.execute('CREATE TABLE source_cleanup(job_id TEXT PRIMARY KEY,state TEXT,reason TEXT)')
                db.execute('CREATE TABLE recovery_retention(job_id TEXT PRIMARY KEY,state TEXT,reason TEXT)')
                db.executemany('INSERT INTO source_cleanup VALUES(?,?,?)', [
                    ('a', 'needs_attention', 'Original bytes differ from reviewed sources'),
                    ('m', 'needs_attention', 'Download marker native identity differs'),
                    ('d', 'completed', '')])
                db.executemany('INSERT INTO recovery_retention VALUES(?,?,?)', [
                    ('b', 'needs_attention', AUDIOBOOK_MISSING + 'The system cannot find the file specified'),
                    ('c', 'needs_attention', AUDIOBOOK_UNVERIFIED + 'Completed output bytes changed'),
                    ('e', 'needs_attention', 'database is locked'),
                    ('f', 'deleted', '')])
        finally: db.close()
        s = service(); s.inventory = SimpleNamespace(worker=None, database=self.database)
        s.jobs = SimpleNamespace(_rows=lambda sql, args: [{'manifest': json.dumps({'candidate_id': 'cand-' + args[0]})}],
                                 attention_summary=lambda *args: {})
        s._load_repair_checks = lambda: None; s._space_ready = None; s.invalidate_status = Mock()
        self.s = s

    def test_only_a_content_mismatch_or_a_missing_or_unverified_audiobook_is_kept(self):
        kept = self.s.kept_files()
        self.assertEqual(sorted(kept), ['a', 'b', 'c'], 'marker, busy-catalog and finished rows are never kept files')
        self.assertEqual((kept['a']['group'], kept['a']['cause']), ('changed', None))
        self.assertEqual((kept['b']['group'], kept['b']['cause'], kept['b']['reason']), ('audiobook', 'missing', 'The system cannot find the file specified'))
        self.assertEqual((kept['c']['group'], kept['c']['cause']), ('audiobook', 'unverified'))
        self.assertEqual(kept['a']['keep'], {'allowed': True, 'reason': ''}); self.assertFalse(kept['a']['originals_untouched'])
        self.assertEqual(sorted(self.s.kept_files(['b', 'm'])), ['b'])

    def test_counts_and_rows_carry_the_groups_and_keep_only_where_it_is_offered(self):
        counted = self.s.attention_summary(retry=False)
        self.assertEqual({key: item['group'] for key, item in counted.items()}, {'a': 'changed', 'b': 'audiobook', 'c': 'audiobook'})
        self.assertTrue(all('keep' not in item for item in counted.values()), 'the count read carries no actions')
        self.assertIn('keep', self.s.attention_summary(['a'])['a'])

    def test_keep_files_stops_flagging_and_deletes_nothing(self):
        self.assertEqual(self.s.keep_files('Audiobooks', 'cand-a', 3, 'a'), {'job_id': 'a', 'kept': True})
        self.s.invalidate_status.assert_called_once_with()
        self.assertEqual(sorted(self.s.kept_files()), ['b', 'c']); self.assertEqual(self.s.kept_by_choice(['a', 'b']), {'a'})
        db = sqlite3.connect(self.database)
        try:
            self.assertEqual(db.execute("SELECT state,reason FROM source_cleanup WHERE job_id='a'").fetchone(), ('needs_attention', 'Original bytes differ from reviewed sources'), 'no cleanup is scheduled')
        finally: db.close()
        with self.assertRaises(RetryRefused): self.s.keep_files('Audiobooks', 'cand-a', 3, 'a')  # already kept: nothing to keep
        with self.assertRaises(RetryRefused): self.s.keep_files('Audiobooks', 'cand-x', 3, 'b')  # another book's identity
        with self.assertRaises(RetryRefused): self.s.keep_files('Audiobooks', 'cand-m', 3, 'm')  # not a kept-files book
        with self.assertRaises(ValueError): self.s.keep_files('Music', 'cand-b', 3, 'b')
        self.assertEqual(self.s.kept_by_choice(['a', 'b', 'm']), {'a'})

    def test_purge_failures_map_to_the_two_audiobook_causes(self):
        self.assertTrue(kept_reason(FileNotFoundError(2, 'The system cannot find the file specified')).startswith(AUDIOBOOK_MISSING))
        self.assertTrue(kept_reason(ValueError('Completed output destination changed; copies retained')).startswith(AUDIOBOOK_MISSING))
        self.assertTrue(kept_reason(ValueError('Completed output bytes changed; copies retained')).startswith(AUDIOBOOK_UNVERIFIED))
        self.assertEqual(kept_reason(ValueError('Recovery copy content changed')), 'Recovery copy content changed', 'positive control: other reasons stay as written')


class FolderJobTests(unittest.TestCase):
    """Empty source folders are housekeeping, not backups: none holds anything or shows as attention."""

    def test_gone_folders_complete_and_busy_catalog_jobs_rerun_once(self):
        s = service(); s._purge_tried = set()
        rows = [{'job_id': 'gone', 'state': 'needs_attention', 'reason': MergeService.FOLDER_ALREADY_GONE, 'output_hash': 'h1'},
                {'job_id': 'locked', 'state': 'needs_attention', 'reason': 'database is locked', 'output_hash': 'h2'},
                {'job_id': 'empty', 'state': 'unsupported', 'reason': 'Empty source folder retained: NTFS supports named data streams', 'output_hash': 'h3'},
                {'job_id': 'other', 'state': 'needs_attention', 'reason': 'Source folder changed', 'output_hash': 'h4'}]
        s.storage_cleanup = SimpleNamespace(folder_status=lambda: rows, _folder_set=Mock(), run_folders=Mock())
        s._settle_folder_jobs(); s._settle_folder_jobs()
        s.storage_cleanup._folder_set.assert_called_once_with('gone', 'h1', 'completed', 'Source folder was already gone')
        s.storage_cleanup.run_folders.assert_called_once_with('locked')

    def test_a_failed_rerun_stays_quiet(self):
        s = service(); s._purge_tried = set()
        s.storage_cleanup = SimpleNamespace(folder_status=lambda: [{'job_id': 'locked', 'state': 'needs_attention', 'reason': 'database is busy', 'output_hash': 'h'}],
                                            _folder_set=Mock(), run_folders=Mock(side_effect=sqlite3.OperationalError('database is locked')))
        s._settle_folder_jobs()
        s.storage_cleanup.run_folders.assert_called_once_with('locked')


if __name__ == '__main__':
    unittest.main()
