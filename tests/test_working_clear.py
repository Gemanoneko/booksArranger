"""Leftover working files (RefusedRetry follow-up 2, section 2; Sergei's decisions A and B, O10, 2026-10-19).

The live state of a job's leftover working files (cleanable or blocked), the Clear working files action through the
app's verified disposal, Retry and Repair clearing first, and the hard safety rule: before anything is deleted the target
must be inside the app's own staging root, owned by that job and never an original. Every escape attempt below must
delete nothing. Real Windows file handles and receipts, synthetic bytes, no library.
"""
import _winapi
import hashlib
import json
import os
import shutil
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import audio_jobs
import groups
import m4b_readmission
import m4b_repair
import merge_service
from audio_jobs import AudioJobs, RetryRefused, RETRY_BOOK_CHANGED, RETRY_NOT_CLEARED, REPAIR_NOT_CLEARED
from audio_pipeline import copy_owned, generated_artifacts, plan_generated
from merge_service import MergeService
from native_io import BoundaryError
from scanner import connect
from source_cleanup import packed
from working_lifecycle import WorkingLifecycle
import test_merge_http

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'working-clear-tests'
AREA.mkdir(parents=True, exist_ok=True)
REFUSED = 'M4B preservation requires review: Unsupported structural box'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@unittest.skipUnless(os.name == 'nt', 'Actual Windows native file fixtures required')
class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(self.temp.cleanup)
        base = self.base = Path(self.temp.name)
        self.library = base / 'library'
        self.library.mkdir()
        self.stage_root = base / 'merge-cache' / 'audio-staging'
        self.stage_root.mkdir(parents=True)
        self.db = base / 'catalog.sqlite3'
        self.jobs = AudioJobs(self.db, None, lambda manifest: True, lambda record: False)
        self.addCleanup(self.jobs.close)
        with connect(self.db) as db:
            groups.setup(db)
            db.execute('CREATE TABLE IF NOT EXISTS candidate_context(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL)')
        self.life = WorkingLifecycle(self.db, self.stage_root)
        patcher = patch.object(MergeService, '_check_repairs')
        patcher.start()
        self.addCleanup(patcher.stop)
        checks = patch.dict(audio_jobs.REPAIR_CHECKS)
        checks.start()
        self.addCleanup(checks.stop)
        s = MergeService.__new__(MergeService)
        s.jobs = self.jobs
        s.operation_lock = threading.RLock()
        s.draining = False
        s.inventory = SimpleNamespace(worker=None, database=self.db, group_lock=threading.RLock(), roots={'Audiobooks': str(self.library)})
        s.reviews = SimpleNamespace(lock=threading.RLock())
        s.working = self.life
        s.stage_root = self.stage_root
        s.cleanup = SimpleNamespace(status=lambda job_id=None: None, thread=None, current=None)
        s.automatic = SimpleNamespace(stop_event=threading.Event())
        s.resume = Mock()
        s._resume_later = Mock()
        s.invalidate_status = Mock()
        s.jobs.m4b_working_clear = s._m4b_working_clear
        s.jobs.repair_check_failed = s._repair_check_failed
        s.jobs.working_state = s._working_state
        self.s = s

    def book(self, name='book', data=b'original audiobook bytes ' * 64):
        folder = self.library / name
        folder.mkdir()
        source = folder / 'book.m4b'
        source.write_bytes(data)
        cover = folder / 'cover.jpg'
        cover.write_bytes(b'\xff\xd8\xff fixture cover ' + name.encode())
        info = source.stat()
        candidate = str(uuid.uuid4())
        manifest = {'job_id': str(uuid.uuid4()), 'candidate_id': candidate, 'candidate_revision': 1, 'root': str(self.library),
                    'sources': [{'path': str(source), 'size': info.st_size, 'modified': str(info.st_mtime_ns), 'sha256': digest(source),
                                 'fingerprint': {'size': info.st_size, 'modified': str(info.st_mtime_ns)}}],
                    'cover': {'path': str(cover), 'sha256': digest(cover)}, 'metadata': {'title': 'Fixture ' + name},
                    'destination': str(self.base / 'out' / (name + '.m4b')), 'profile': 'fixture', 'evidence': {}, 'source_chapters': [],
                    'cleanup_policy': {'enabled': False}}
        job_id = self.jobs.enqueue(manifest)
        with connect(self.db) as db:
            db.execute('INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence,review) VALUES(?,?,?,?,?,?,?)',
                       (candidate, str(self.library), str(folder), 1, 'fp', json.dumps({'members': [{'path': str(source)}]}), ''))
            db.execute('INSERT INTO candidate_context VALUES(?,?,?)', (candidate, 1, '{}'))
        self.fail_job(job_id)
        audio_jobs.remember_repair_check(audio_jobs.repair_check_key(self.row(job_id)), {'state': 'intact', 'reason': '', 'damage': [], 'repairs': []})
        return job_id, manifest, source, cover

    def fail_job(self, job_id):
        self.jobs._update(job_id, state='needs attention', stage='checking', reason=REFUSED,
                          journal=json.dumps({'failure': {'exception_class': 'ValidationError', 'retryable': False, 'at': 1}}))

    def stage(self, job_id, manifest, source, cover):
        """One receipt-owned, closed attempt, as a failed conversion leaves it (the lifecycle's own producer path)."""
        attempt = str(uuid.uuid4())
        self.jobs._update(job_id, state='running', attempt_id=attempt, journal=json.dumps({'attempt_id': attempt, 'history': []}))
        self.life.begin(dict(manifest, attempt_id=attempt))
        parent = self.stage_root / job_id
        parent.mkdir(exist_ok=True)
        marker = parent / 'ownership.json'
        if not marker.exists():
            marker.write_text(packed({'job_id': job_id, 'manifest': manifest}), encoding='utf8')
        directory = parent / attempt
        directory.mkdir()
        with generated_artifacts(directory, self.life):
            copy_owned(source, directory / 'source00000.m4b', manifest['sources'][0]['sha256'], threading.Event())
            copy_owned(cover, directory / 'cover.jpg', manifest['cover']['sha256'], threading.Event())
            plan_generated(directory / 'checked.m4b')
            (directory / 'checked.m4b').write_bytes(b'failed generated output')
        self.fail_job(job_id)
        return attempt, directory

    def row(self, job_id):
        return self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))[0]

    def summary(self, job_id):
        return self.s.attention_summary().get(job_id)

    def files(self, directory):
        return sorted(path.name for path in Path(directory).iterdir()) if Path(directory).exists() else []

    def clear(self, manifest, job_id, revision=1):
        return self.s.clear_working_files('Audiobooks', manifest['candidate_id'], revision, job_id)


class StateTests(Base):
    def test_a_receipt_owned_attempt_is_cleanable_and_its_row_keeps_its_state(self):
        job_id, manifest, source, cover = self.book()
        attempt, directory = self.stage(job_id, manifest, source, cover)
        value = self.summary(job_id)
        size = sum(path.stat().st_size for path in directory.iterdir())
        self.assertEqual((value['group'], value['retry'], value['working']['state'], value['working']['bytes']), ('retry', {'allowed': True, 'reason': ''}, 'cleanable', size))
        self.assertEqual(value['working_folder'], os.path.abspath(self.stage_root / job_id))
        self.assertNotIn('stops', value['working'])
        counts, cleanable = merge_service.attention_counts(self.s.attention_summary(retry=False))
        self.assertEqual((counts['retry'], cleanable), (1, 1), "Retry all's dialog reads k from the status")
        self.assertEqual(self.s.quiet_max_age(), merge_service.WORKING_MAX_AGE, 'rows with files are re-read within a minute')

    def test_files_the_app_cannot_prove_are_blocked_and_stop_the_row(self):
        job_id, manifest, source, cover = self.book('legacy')
        legacy = self.stage_root / job_id / str(uuid.uuid4())
        legacy.mkdir(parents=True)
        (legacy / 'source00000.m4b').write_bytes(b'an older attempt with no receipt')
        value = self.summary(job_id)
        self.assertEqual((value['group'], value['working']['state'], value['working']['stops'], 'retry' in value), ('other', 'blocked', True, False))
        self.assertIn('ownership', value['working']['reason'])
        with self.assertRaises(RetryRefused) as caught:
            self.clear(manifest, job_id)
        self.assertEqual(caught.exception.cause, 'not_safe')
        with self.assertRaises(RetryRefused) as caught:
            self.s.retry_blocked_job('Audiobooks', manifest['candidate_id'], 1, job_id)
        self.assertEqual(str(caught.exception), audio_jobs.RETRY_GATE_STOPS % 'Retry', 'S9; a forced press on a blocked row changes nothing')
        self.assertEqual(self.files(legacy), ['source00000.m4b'], 'nothing deleted')

    def test_an_ownership_record_without_receipts_or_receipts_without_one_are_blocked(self):
        job_id, manifest, source, cover = self.book('half')
        legacy = self.stage_root / job_id / str(uuid.uuid4())
        legacy.mkdir(parents=True)
        (legacy / 'source00000.m4b').write_bytes(b'an older attempt with no receipt')
        (self.stage_root / job_id / 'ownership.json').write_text(packed({'job_id': job_id, 'manifest': manifest}), encoding='utf8')
        value = self.s._working_state(self.row(job_id), True, fresh=True)
        self.assertEqual(value['state'], 'blocked')
        self.assertIn('earlier attempt has no ownership record', value['reason'])
        shutil.rmtree(legacy)
        other, other_manifest, other_source, other_cover = self.book('no-marker')
        attempt, directory = self.stage(other, other_manifest, other_source, other_cover)
        (self.stage_root / other / 'ownership.json').unlink()
        value = self.s._working_state(self.row(other), True, fresh=True)
        self.assertEqual(value['state'], 'blocked')
        self.assertIn('working folder has no ownership record', value['reason'])

    def test_an_unknown_file_or_an_unreachable_original_is_blocked(self):
        job_id, manifest, source, cover = self.book('unknown')
        attempt, directory = self.stage(job_id, manifest, source, cover)
        (directory / 'stray.wav').write_bytes(b'not the app')
        self.assertEqual(self.summary(job_id)['working']['state'], 'blocked')
        with self.assertRaises(RetryRefused):
            self.clear(manifest, job_id)
        self.assertIn('stray.wav', self.files(directory))
        self.assertIn('checked.m4b', self.files(directory), 'nothing removed when the folder cannot be proven')
        (directory / 'stray.wav').unlink()
        moved = source.with_name('moved.m4b')
        source.rename(moved)
        value = self.s._working_state(self.row(job_id), True, fresh=True)
        self.assertEqual((value['state'], value.get('cause')), ('blocked', 'originals_unreachable'))
        self.assertEqual(self.summary(job_id)['group'], 'other')
        moved.rename(source)  # the drive is back: cleanable again with no step from Sergei
        self.assertEqual(self.s._working_state(self.row(job_id), True, fresh=True)['state'], 'cleanable')

    def test_an_old_working_files_record_with_no_files_reads_ready(self):
        job_id, manifest, source, cover = self.book('old-record')
        with connect(self.db) as db:
            m4b_readmission.ensure(db)
            db.execute('INSERT INTO m4b_readmissions VALUES(?,?,?,?,?,?,?,?)', (job_id, 'retry', 1, 'refused', None,
                       'Prior audio working files need verified disposal before another source copy', 'a', 'b'))
        value = self.summary(job_id)
        self.assertEqual((value['group'], value['retry'], 'working' in value), ('retry', {'allowed': True, 'reason': ''}, False))
        self.assertEqual(value['readmission']['cause'], 'working_files', 'kept for the Technical detail line only')
        self.assertEqual(self.s.quiet_max_age(), merge_service.QUIET_MAX_AGE, 'positive control: no files, the usual bound')


class ClearTests(Base):
    def test_clear_removes_the_leftovers_through_verified_disposal_and_never_an_original(self):
        job_id, manifest, source, cover = self.book()
        attempt, directory = self.stage(job_id, manifest, source, cover)
        before = (digest(source), digest(cover), self.row(job_id))
        size = sum(path.stat().st_size for path in directory.iterdir())
        answer = self.clear(manifest, job_id)
        self.assertEqual((answer['cleared'], answer['bytes']), (True, size))
        self.assertEqual(self.files(directory), [])
        self.assertEqual((digest(source), digest(cover), self.row(job_id)), before, 'originals and the job row untouched')
        self.assertEqual(self.life._attempt(job_id, attempt)['state'], 'retired')
        self.assertNotIn('working', self.summary(job_id))
        self.s.invalidate_status.assert_called()
        again = self.clear(manifest, job_id)
        self.assertEqual((again['cleared'], again['bytes'], again['already']), (True, 0, True), 'Working files were already cleared.')

    def test_an_outdated_view_changes_nothing(self):
        job_id, manifest, source, cover = self.book()
        attempt, directory = self.stage(job_id, manifest, source, cover)
        for identity, revision in ((manifest['candidate_id'], 2), (str(uuid.uuid4()), 1)):
            with self.assertRaises(RetryRefused) as caught:
                self.s.clear_working_files('Audiobooks', identity, revision, job_id)
            self.assertEqual(caught.exception.cause, 'changed')
        self.assertEqual(len(self.files(directory)), 3)

    def test_a_failed_disposal_keeps_the_folder_blocked_until_it_changes(self):
        job_id, manifest, source, cover = self.book()
        attempt, directory = self.stage(job_id, manifest, source, cover)
        with patch.object(WorkingLifecycle, 'retire', side_effect=BoundaryError('Closed working-file native identity or bytes changed')):
            with self.assertRaises(RetryRefused) as caught:
                self.clear(manifest, job_id)
        self.assertEqual(caught.exception.cause, 'not_safe')
        value = self.summary(job_id)
        self.assertEqual((value['working']['state'], value['group']), ('blocked', 'other'), 'never "cleanable" again for the same folder')
        self.assertIn('native identity', value['working']['reason'])
        (directory / 'checked.m4b').unlink()  # the folder changed: classified again
        self.assertEqual(self.s._working_state(self.row(job_id), True, fresh=True)['state'], 'blocked', 'a missing recorded file without intent')
        with patch.object(WorkingLifecycle, 'retire', side_effect=OSError(32, 'in use')):
            self.s._working_failed.clear()
            with self.assertRaises(RetryRefused) as caught:
                self.clear(manifest, job_id)
        self.assertEqual(caught.exception.cause, 'not_safe', 'the folder is not cleanable now, so nothing is tried')

    def test_a_file_that_cannot_be_removed_is_a_file_problem(self):
        job_id, manifest, source, cover = self.book()
        attempt, directory = self.stage(job_id, manifest, source, cover)
        with patch.object(WorkingLifecycle, 'retire', side_effect=OSError(32, 'The process cannot access the file')):
            with self.assertRaises(RetryRefused) as caught:
                self.clear(manifest, job_id)
        self.assertEqual(caught.exception.cause, 'file_problem')
        self.s.inventory.worker = SimpleNamespace(is_alive=lambda: True)
        with self.assertRaises(RetryRefused) as caught:
            self.clear(manifest, job_id)
        self.assertEqual(caught.exception.cause, 'busy', 'a library scan is running')

    def test_a_file_held_open_by_another_program_is_a_file_problem_and_clears_once_released(self):
        """Futaba Minor 1 (c2abd97): a file held open without delete sharing (an antivirus scan can) is a sharing
        violation, which proves nothing unsafe: "try again", and the row recovers once the file is released, with no
        restart. Before the fix it read not_safe and the folder stayed blocked until the app restarted."""
        from native_io import FileInUse, VerifiedFile
        job_id, manifest, source, cover = self.book()
        attempt, directory = self.stage(job_id, manifest, source, cover)
        held = open(directory / 'checked.m4b', 'rb')  # Python shares read and write, never delete
        try:
            with self.assertRaises(FileInUse) as typed:
                with VerifiedFile(directory / 'checked.m4b', delete=True):
                    pass
            self.assertIsInstance(typed.exception, BoundaryError, 'every other caller still refuses exactly as before')
            with self.assertRaises(RetryRefused) as caught:
                self.clear(manifest, job_id)
            self.assertEqual((str(caught.exception), caught.exception.cause), (audio_jobs.WORKING_FILE_PROBLEM, 'file_problem'))
            self.assertEqual(len(self.files(directory)), 3, 'nothing removed')
            value = self.summary(job_id)
            self.assertEqual((value['working']['state'], value['group'], value['retry']), ('cleanable', 'retry', {'allowed': True, 'reason': ''}),
                             'still cleanable: Retry and Clear stay offered')
            with self.assertRaises(RetryRefused) as caught:
                self.s.retry_blocked_job('Audiobooks', manifest['candidate_id'], 1, job_id)
            self.assertEqual((str(caught.exception), caught.exception.cause), (RETRY_NOT_CLEARED, 'file_problem'))
            with connect(self.db) as db:
                self.assertIsNone(m4b_readmission.describe(db, job_id), 'nothing queued')
        finally:
            held.close()
        answer = self.clear(manifest, job_id)  # released: the next press clears, no restart
        self.assertTrue(answer['cleared'])
        self.assertEqual(self.files(directory), [])
        self.assertEqual(digest(source), manifest['sources'][0]['sha256'], 'the original is untouched')


class SafetyTests(Base):
    """The hard safety rule: every escape attempt is refused before anything is deleted."""
    def staged(self, name='book'):
        job_id, manifest, source, cover = self.book(name)
        attempt, directory = self.stage(job_id, manifest, source, cover)
        return job_id, manifest, source, cover, attempt, directory

    def refused(self, manifest, job_id, *keep):
        before = {path: digest(path) for path in keep}
        with self.assertRaises(RetryRefused) as caught:
            self.clear(manifest, job_id)
        self.assertEqual(caught.exception.cause, 'not_safe')
        for path, value in before.items():
            self.assertEqual(digest(path), value, str(path))

    def test_a_receipt_pointing_at_the_original_is_refused(self):
        job_id, manifest, source, cover, attempt, directory = self.staged()
        with connect(self.db) as db:
            db.execute("UPDATE working_files SET path=? WHERE job_id=? AND attempt_id=? AND name='source00000.m4b'", (str(source), job_id, attempt))
        with self.assertRaises(BoundaryError):
            self.s._working_targets(self.row(job_id), self.s._working_listing(job_id)[0])
        self.refused(manifest, job_id, source, directory / 'source00000.m4b', directory / 'checked.m4b')

    def test_a_receipt_outside_its_attempt_folder_or_inside_a_library_is_refused(self):
        job_id, manifest, source, cover, attempt, directory = self.staged()
        outside = self.base / 'elsewhere'
        outside.mkdir()
        decoy = outside / 'checked.m4b'
        decoy.write_bytes(b'not a working file')
        for path in (decoy, self.library / 'checked.m4b'):
            with connect(self.db) as db:
                db.execute("UPDATE working_files SET path=? WHERE job_id=? AND attempt_id=? AND name='checked.m4b'", (str(path), job_id, attempt))
            with self.assertRaises(BoundaryError):
                self.s._working_targets(self.row(job_id), self.s._working_listing(job_id)[0])
        self.refused(manifest, job_id, decoy, directory / 'checked.m4b', source)

    def test_a_recorded_file_that_is_an_original_or_in_a_library_is_refused(self):
        job_id, manifest, source, cover, attempt, directory = self.staged()
        listing = self.s._working_listing(job_id)[0]
        crafted = dict(self.row(job_id))
        sources = json.loads(crafted['manifest'])
        sources['sources'][0]['path'] = str(directory / 'checked.m4b')  # a manifest naming a working file as its original
        crafted['manifest'] = json.dumps(sources)
        with self.assertRaises(BoundaryError) as caught:
            self.s._working_targets(crafted, listing)
        self.assertIn('an original or inside a library', str(caught.exception))
        self.s.inventory.roots = {'Audiobooks': str(self.base)}  # a library that contains the staging root
        with self.assertRaises(BoundaryError) as caught:
            self.s._working_targets(self.row(job_id), listing)
        self.assertIn('an original or inside a library', str(caught.exception))
        self.refused(manifest, job_id, directory / 'checked.m4b', source)

    def test_a_junction_out_of_the_staging_root_is_never_followed(self):
        job_id, manifest, source, cover, attempt, directory = self.staged()
        outside = self.base / 'outside-target'
        moved = self.base / 'moved-attempt'
        shutil.move(str(directory), str(moved))
        shutil.copytree(moved, outside)  # a look-alike folder: same names, same sizes, outside the app's staging root
        precious = outside / 'checked.m4b'
        _winapi.CreateJunction(str(outside), str(directory))
        self.addCleanup(lambda: os.path.isjunction(directory) and os.rmdir(directory))
        value = self.s._working_state(self.row(job_id), True, fresh=True)
        self.assertEqual(value['state'], 'blocked')
        self.assertIn('did not create', value['reason'], 'the listing never follows the junction')
        with self.assertRaises(BoundaryError) as caught:
            self.s._working_targets(self.row(job_id), [(attempt, [])])
        self.assertIn('link or junction', str(caught.exception))
        self.refused(manifest, job_id, precious, outside / 'source00000.m4b')
        self.assertEqual(sorted(path.name for path in outside.iterdir()), ['checked.m4b', 'cover.jpg', 'source00000.m4b'])

    def test_a_job_id_that_escapes_the_root_or_a_foreign_ownership_record_is_refused(self):
        job_id, manifest, source, cover, attempt, directory = self.staged()
        for bad in ('..', '..\\..', str(self.base)):
            row = dict(self.row(job_id), job_id=bad)
            self.assertIsNone(self.s._working_state(row, True), 'not a job identity: never listed')
            with self.assertRaises(BoundaryError) as caught:
                self.s._working_targets(row, [(attempt, [])])
            self.assertIn('not a job identity', str(caught.exception))
        with self.assertRaises(BoundaryError) as caught:
            self.s._working_targets(self.row(job_id), [('..', [])])
        self.assertIn('not an attempt identity', str(caught.exception))
        marker = self.stage_root / job_id / 'ownership.json'
        marker.write_text(packed({'job_id': str(uuid.uuid4()), 'manifest': manifest}), encoding='utf8')
        with self.assertRaises(BoundaryError) as caught:
            self.s._working_targets(self.row(job_id), self.s._working_listing(job_id)[0])
        self.assertIn('names another job', str(caught.exception))
        self.refused(manifest, job_id, directory / 'checked.m4b', source)

    def test_a_staging_root_that_is_a_junction_is_refused(self):
        job_id, manifest, source, cover, attempt, directory = self.staged()
        real = self.base / 'real-staging'
        shutil.move(str(self.stage_root), str(real))
        _winapi.CreateJunction(str(real), str(self.stage_root))
        self.addCleanup(lambda: os.path.isjunction(self.stage_root) and os.rmdir(self.stage_root))
        self.assertEqual(self.s._working_state(self.row(job_id), True, fresh=True)['state'], 'blocked')
        with self.assertRaises(BoundaryError):
            self.s._working_targets(self.row(job_id), [(attempt, [])])
        self.assertEqual(len(self.files(real / job_id / attempt)), 3)


class ClearFirstTests(Base):
    def test_retry_clears_first_then_queues(self):
        job_id, manifest, source, cover = self.book()
        attempt, directory = self.stage(job_id, manifest, source, cover)
        answer = self.s.retry_blocked_job('Audiobooks', manifest['candidate_id'], 1, job_id)
        self.assertTrue(answer['queued_next'])
        self.assertEqual(self.files(directory), [])
        self.assertEqual(digest(source), manifest['sources'][0]['sha256'])

    def test_when_the_clear_fails_nothing_is_queued(self):
        job_id, manifest, source, cover = self.book()
        attempt, directory = self.stage(job_id, manifest, source, cover)
        with patch.object(WorkingLifecycle, 'retire', side_effect=BoundaryError('kept')):
            with self.assertRaises(RetryRefused) as caught:
                self.s.retry_blocked_job('Audiobooks', manifest['candidate_id'], 1, job_id)
        self.assertEqual((str(caught.exception), caught.exception.cause), (RETRY_NOT_CLEARED, 'not_safe'))
        with connect(self.db) as db:
            self.assertIsNone(m4b_readmission.describe(db, job_id), 'nothing queued')
        self.assertEqual(len(self.files(directory)), 3)

    def test_repair_and_retry_all_clear_first(self):
        job_id, manifest, source, cover = self.book('repair')
        attempt, directory = self.stage(job_id, manifest, source, cover)
        found = {'state': 'repairable', 'reason': REFUSED, 'damage': ['d'], 'repairs': [{'kind': 'dangling_chapter_reference', 'description': 'd'}]}
        with patch.object(m4b_repair, 'classify', return_value=found):
            self.assertEqual((self.summary(job_id)['group'], self.summary(job_id)['repair']), ('repair', {'allowed': True, 'reason': ''}))
            with patch.object(WorkingLifecycle, 'retire', side_effect=BoundaryError('kept')):
                with self.assertRaises(RetryRefused) as caught:
                    self.s.repair_blocked_job('Audiobooks', manifest['candidate_id'], 1, job_id)
            self.assertEqual(str(caught.exception), REPAIR_NOT_CLEARED)
            self.s._working_failed.clear()
            self.assertTrue(self.s.repair_blocked_job('Audiobooks', manifest['candidate_id'], 1, job_id)['queued_next'])
        self.assertEqual(self.files(directory), [])
        other, other_manifest, other_source, other_cover = self.book('all')
        other_attempt, other_directory = self.stage(other, other_manifest, other_source, other_cover)
        self.assertEqual(self.s._retry_one(other), 'next')
        self.assertEqual(self.files(other_directory), [])


class CheckRefreshTests(Base):
    def test_finished_checks_refresh_the_status_during_the_pass(self):
        jobs = [self.book('check%d' % index)[0] for index in range(3)]
        audio_jobs.REPAIR_CHECKS.clear()
        self.s._repair_pending = list(jobs)
        self.s._repair_skipped = set()
        self.s._load_repair_checks()  # creates the saved-checks table, as the first status read does
        stop = threading.Event()
        with patch.object(m4b_repair, 'classify', return_value={'state': 'unchecked'}), \
             patch.object(m4b_repair, 'check', return_value={'state': 'intact', 'reason': '', 'damage': [], 'repairs': []}), \
             patch.object(merge_service, 'CHECK_REFRESH', 0.0):
            self.s._repair_check_work(stop)
        self.assertGreaterEqual(self.s.invalidate_status.call_count, 3, 'a refresh after each finished check, then the pass end')
        with connect(self.db) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM m4b_repair_checks').fetchone()[0], 3, 'saved in batches, none twice')


class RouteTests(unittest.TestCase):
    setUp = test_merge_http.MergeHTTPTests.setUp
    tearDown = test_merge_http.MergeHTTPTests.tearDown
    handler = test_merge_http.MergeHTTPTests.handler
    call = test_merge_http.MergeHTTPTests.call
    identity = test_merge_http.MergeHTTPTests.identity

    def test_clear_working_route_shape_and_typed_refusal(self):
        job = str(uuid.uuid4())
        self.merge.clear_working_files = Mock(return_value={'cleared': True, 'bytes': 5, 'row': None})
        self.merge.restart_row = Mock(return_value=None)
        self.assertEqual(self.call('/api/audiobook/clear-working', self.identity() | {'job_id': job})[:2], (202, {'cleared': True, 'bytes': 5, 'row': None}))
        self.assertEqual(self.call('/api/audiobook/clear-working', self.identity())[0], 400)
        self.merge.clear_working_files.side_effect = RetryRefused(audio_jobs.WORKING_NOT_SAFE, 'not_safe')
        status, body, _ = self.call('/api/audiobook/clear-working', self.identity() | {'job_id': job})
        self.assertEqual((status, body['cause'], body['error']), (409, 'not_safe', audio_jobs.WORKING_NOT_SAFE))
        self.merge.retry_blocked_job = Mock(side_effect=RetryRefused(RETRY_NOT_CLEARED, 'file_problem'))
        status, body, _ = self.call('/api/audiobook/retry', self.identity() | {'job_id': job})
        self.assertEqual((status, body['cause']), (409, 'file_problem'), "Retry's clear-first failure is typed too")

    def test_a_refused_clear_first_answers_with_the_refreshed_row(self):
        """Futaba Minor 2 (c2abd97): Retry's and Repair's clear-first refusal carries the book's refreshed row, as Clear's
        does, so the details panel stops offering Retry and Clear from the state before the press."""
        job = str(uuid.uuid4())
        fresh = {'id': self.identity()['id'], 'creation': {'job': None}}
        self.merge.restart_row = Mock(return_value=fresh)
        for route, name in (('/api/audiobook/retry', 'retry_blocked_job'), ('/api/audiobook/repair', 'repair_blocked_job')):
            setattr(self.merge, name, Mock(side_effect=RetryRefused(RETRY_NOT_CLEARED, 'not_safe')))
            self.merge.restart_row.reset_mock()
            status, body, _ = self.call(route, self.identity() | {'job_id': job})
            self.assertEqual((status, body['cause'], body.get('row')), (409, 'not_safe', fresh), route)
            self.merge.restart_row.assert_called_once_with(self.identity()['id'])
        self.merge.retry_blocked_job = Mock(side_effect=RetryRefused(RETRY_BOOK_CHANGED))
        status, body, _ = self.call('/api/audiobook/retry', self.identity() | {'job_id': job})
        self.assertEqual((status, body.get('row')), (409, None), 'an untyped refusal is unchanged')
