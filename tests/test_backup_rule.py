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
    s.cleanup = SimpleNamespace(thread=None, current=None, _rows=lambda *args: [], resume=Mock(return_value={'state':'started'}))
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
        # Senua F1: the reason keeps its prefix, so the book shows under "Audiobook problem".
        s.recovery._set.assert_called_once_with('job-a', 'needs_attention', AUDIOBOOK_UNVERIFIED + 'Completed output bytes changed; copies retained')


class HeldCleanupTests(unittest.TestCase):
    def test_marker_held_cleanups_finish_on_their_own_once(self):
        s = service(); s.jobs._thread = None; s._purge_tried = set(); s._kept_by_choice = lambda job_ids: set()
        s.cleanup._rows = lambda *args: [{'id': 'c1', 'job_id': 'j1', 'reason': 'Download marker native identity differs'},
                                         {'id': 'c2', 'job_id': 'j2', 'reason': 'Unknown download marker contents preserved'},
                                         {'id': 'c3', 'job_id': 'j3', 'reason': 'Download marker native identity differs'}]
        s._finish_held_cleanups(); s._finish_held_cleanups()
        s.cleanup.resume.assert_called_once()
        self.assertEqual(s.cleanup.resume.call_args.args, (['c1', 'c2', 'c3'],))
        self.assertFalse(s.cleanup.resume.call_args.kwargs['follow_audio'])
        self.assertEqual(s.cleanup.resume.call_args.kwargs['admission_token'], 0)
        self.assertTrue(s.cleanup.resume.call_args.kwargs['admission_check']())

    def test_a_kept_book_is_never_resumed_and_an_unreadable_record_resumes_nothing(self):
        rows = [{'id': 'c1', 'job_id': 'j1', 'reason': 'Download marker native identity differs'},
                {'id': 'c2', 'job_id': 'j2', 'reason': 'Download marker native identity differs'}]
        s = service(); s.jobs._thread = None; s._purge_tried = set(); s.cleanup._rows = lambda *args: rows
        s._kept_by_choice = lambda job_ids: {'j2'}
        s._finish_held_cleanups(); s.cleanup.resume.assert_called_once()
        self.assertEqual(s.cleanup.resume.call_args.args, (['c1'],))
        self.assertFalse(s.cleanup.resume.call_args.kwargs['follow_audio'])
        self.assertEqual(s.cleanup.resume.call_args.kwargs['admission_token'], 0)
        self.assertTrue(s.cleanup.resume.call_args.kwargs['admission_check']())
        s = service(); s.jobs._thread = None; s._purge_tried = set(); s.cleanup._rows = lambda *args: rows
        s._kept_by_choice = Mock(side_effect=sqlite3.OperationalError('database is locked'))
        s._finish_held_cleanups(); s.cleanup.resume.assert_not_called()

    def test_replacement_recoveries_of_a_kept_book_stay(self):
        s = service(); s._purge_tried = set(); s.retirement = SimpleNamespace(purge_recoveries=Mock(return_value=0))
        s.replacements = SimpleNamespace(rows=lambda: [{'id': 'r1', 'state': 'completed', 'replacement_job_id': 'j1'},
                                                       {'id': 'r2', 'state': 'completed', 'replacement_job_id': 'j2'}])
        s._kept_by_choice = lambda job_ids: {'j2'}
        s._purge_replacement_recoveries()
        self.assertEqual([call.args[0]['id'] for call in s.retirement.purge_recoveries.call_args_list], ['r1'])

    def test_they_wait_while_a_book_converts(self):
        s = service(); s._purge_tried = set(); s._kept_by_choice = lambda job_ids: set()
        s.cleanup._rows = lambda *args: [{'id': 'c1', 'job_id': 'j1', 'reason': 'Download marker native identity differs'}]
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


    def test_ruling_76b_old_folders_are_swept_only_while_nothing_converts(self):
        s = service(); s._purge_tried = set(); s.draining = False
        swept = []
        s.storage_cleanup = SimpleNamespace(folder_status=lambda: [], _folder_set=Mock(), run_folders=Mock(),
                                            old_folder_jobs=lambda: ['a', 'b', 'c'], sweep_folders=lambda job_id: swept.append(job_id) or 'completed')
        s._settle_folder_jobs()
        self.assertEqual(swept, [], 'a conversion is running: the sweep waits')
        s.jobs._thread = SimpleNamespace(is_alive=lambda: False)
        s._settle_folder_jobs()
        self.assertEqual(swept, ['a', 'b', 'c'], 'one book at a time, every pending one inside the budget')
        swept.clear(); s.draining = True; s._settle_folder_jobs(); self.assertEqual(swept, [], 'never while closing')
        s.draining = False; s.OLD_FOLDER_BUDGET = -1; s._settle_folder_jobs(); self.assertEqual(swept, [], 'the budget ends a pass')
        s.OLD_FOLDER_BUDGET = 20.0
        s.storage_cleanup.sweep_folders = Mock(side_effect=[InterruptedError('closing'), 'kept'])
        s._settle_folder_jobs(); self.assertEqual(s.storage_cleanup.sweep_folders.call_count, 1, 'closing stops the pass')

if __name__ == '__main__':
    unittest.main()
