"""RefusedRetry spec (Judy, 2026-10-19): typed refusal records, the group and offer each fix gives, the
server gate, re-offer when the deciding code changes, and the one-time conversion of v0.18.0 records.

Synthetic catalogs and synthetic M4B bytes only; the worker's admission runs the real read-only plan().
"""
import contextlib
import json
import os
import threading
import unittest
import uuid
from unittest.mock import Mock, patch

import audio_jobs
import m4b_readmission
import m4b_repair
import retry_refusal
from audio_jobs import RetryRefused, RETRY_ALL_NONE, RETRY_BOOK_CHANGED, RETRY_FILES_PRESENT
from merge_service import MergeService
from test_attention_repair import Base, REFUSED
from test_m4b_preservation import fixture, with_iods

# An iods naming a track (ES_ID_Inc): refused by plan() as 'Unsupported object descriptor'.
TRACK_IODS = bytes.fromhex('0000001e696f647300000000108080800d004fffffffffff0e0400000001')
OLD_KEY = 'm4b_preservation:' + '0' * 64


class RefusalCase(Base):
    def setUp(self):
        super().setUp()
        self.s = self.service()
        self.s.reviews.build_manifest = self.build
        self.edited = False

    def build(self, library, identity, revision, allow_existing_job=False, stop=None):
        rows = self.l.jobs._rows("SELECT manifest FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? ORDER BY created", (identity,))
        fresh = json.loads(rows[0]['manifest'])
        fresh['job_id'] = str(uuid.uuid4())
        if self.edited:
            fresh['metadata']['title'] = 'Edited after the failure'
        return fresh

    def press(self, job_id, manifest):
        return self.s.retry_blocked_job('Audiobooks', manifest['candidate_id'], 1, job_id)

    def refused(self, source=None, name='book'):
        """A failed M4B row, a Retry press, then the worker's real admission refusing it. The row's dry run is recorded
        as passed first: since the 2026-10-19 follow-up a row still being checked offers no Retry."""
        job_id, manifest = self.l.failed(REFUSED, source if source is not None else with_iods(fixture(), TRACK_IODS), name=name)
        self.passed(job_id)
        self.assertTrue(self.press(job_id, manifest)['queued_next'])
        self.assertIsNone(self.s._next_m4b_readmission(), 'refused: the normal queue runs')
        return job_id, manifest

    def stored(self, job_id):
        with self.l.jobs._db() as db:
            return tuple(db.execute('SELECT state,detail FROM m4b_readmissions WHERE parent_job_id=?', (job_id,)).fetchone())

    def summary(self, job_id, retry=True):
        return self.s.attention_summary(retry=retry)[job_id]

    def set_key(self, job_id, key):
        state, detail = self.stored(job_id)
        record = json.loads(detail) | {'key': key}
        with self.l.jobs._db() as db:
            db.execute('UPDATE m4b_readmissions SET detail=? WHERE parent_job_id=?', (json.dumps(record), job_id))


class TypedRefusalTests(RefusalCase):
    def test_an_unsupported_file_is_recorded_with_cause_fix_version_and_preservation_key(self):
        job_id, _ = self.refused()
        state, detail = self.stored(job_id)
        record = json.loads(detail)
        self.assertEqual(state, 'refused')
        self.assertEqual({key: record[key] for key in ('reason', 'cause', 'fix', 'app_version', 'key')},
                         {'reason': 'Failed M4B retained: Unsupported object descriptor', 'cause': 'unsupported_file', 'fix': 'update',
                          'app_version': retry_refusal.app_version(), 'key': 'm4b_preservation:' + retry_refusal.preservation_sha256()})
        self.assertTrue(record['at'])

    def test_unsupported_file_leaves_can_retry_and_offers_no_retry(self):
        job_id, _ = self.refused()
        other, _ = self.l.failed(REFUSED, fixture(), name='other')  # positive control: never tried, still offered
        self.passed(other)
        summary = self.s.attention_summary()
        self.assertEqual(summary[other], {'group': 'retry', 'cause': None, 'originals_untouched': True, 'precheck': 'passed', 'retry': {'allowed': True, 'reason': ''}})
        value = summary[job_id]
        self.assertEqual((value['group'], 'retry' in value, value['originals_untouched']), ('unsupported', False, True))
        self.assertEqual({key: value['readmission'][key] for key in ('accepted', 'queued_next', 'cause', 'fix', 'stale', 'app_version')},
                         {'accepted': False, 'queued_next': False, 'cause': 'unsupported_file', 'fix': 'update', 'stale': False, 'app_version': retry_refusal.app_version()})
        self.assertEqual(self.s.attention_summary(retry=False)[job_id]['group'], 'unsupported', 'the counts read the same group')

    def test_a_press_from_an_outdated_view_and_retry_all_queue_nothing(self):
        job_id, manifest = self.refused()
        before = self.stored(job_id)
        with self.assertRaises(RetryRefused) as caught:
            self.press(job_id, manifest)
        self.assertEqual(str(caught.exception), RETRY_BOOK_CHANGED)
        self.assertEqual(self.stored(job_id), before, 'no new attempt, the refusal kept')
        self.assertIsNone(self.s._retry_one(job_id), 'Retry all\'s per-book path refuses it too')
        other, _ = self.l.failed(REFUSED, fixture(), name='other')
        self.passed(other)
        self.assertEqual([key for key, item in self.s.attention_summary(retry=False).items() if item['group'] == 'retry'], [other],
                         'Retry all takes the server group, which no longer holds the refused book')

    def test_each_fix_decides_the_group_and_the_offer(self):
        # working_files: since follow-up 2 (section 2.2) the record no longer decides the row; the live state of the
        # files does. Files the app cannot prove its own (no ownership record) are blocked: no Retry, group Other.
        job_id, manifest = self.l.failed(REFUSED, fixture(), name='files')
        self.passed(job_id)
        self.press(job_id, manifest)
        attempt = self.s.stage_root / job_id / str(uuid.uuid4())
        attempt.mkdir(parents=True)
        leftover = attempt / 'source00000.m4b'
        leftover.write_bytes(b'unfinished copy')  # appears after the press: the worker's admission refuses on it
        self.assertIsNone(self.s._next_m4b_readmission())
        value = self.summary(job_id)
        self.assertEqual((value['group'], value['readmission']['cause'], value['working']['state'], value['working']['stops'], 'retry' in value),
                         ('other', 'working_files', 'blocked', True, False))
        with self.assertRaises(RetryRefused) as caught:
            self.press(job_id, manifest)
        self.assertEqual(str(caught.exception), RETRY_BOOK_CHANGED, 'a press from an outdated view changes nothing')
        leftover.unlink()
        self.assertNotIn('working', self.summary(job_id))
        self.assertEqual(self.summary(job_id)['retry'], {'allowed': True, 'reason': ''}, 'enabled once the files are gone')
        self.assertTrue(self.press(job_id, manifest)['queued_next'])
        # source_changed (fix review): no control; a press is refused.
        self.edited = True
        changed, changed_manifest = self.refused(fixture(), name='changed')
        value = self.summary(changed)
        self.assertEqual((value['group'], value['readmission']['cause'], 'retry' in value), ('other', 'source_changed', False))
        with self.assertRaises(RetryRefused):
            self.press(changed, changed_manifest)
        self.edited = False
        # file_problem (fix user): Retry stays enabled.
        missing, missing_manifest = self.l.failed(REFUSED, fixture(), name='missing')
        self.passed(missing)
        self.press(missing, missing_manifest)
        source = self.l.library / 'missing' / 'source.m4b'
        source.unlink()
        self.assertIsNone(self.s._next_m4b_readmission())
        value = self.summary(missing)
        self.assertEqual((value['group'], value['readmission']['cause'], value['retry']), ('other', 'file_problem', {'allowed': True, 'reason': ''}))
        # unknown (no cause sent): no control, like an update-only cause.
        odd, odd_manifest = self.l.failed(REFUSED, fixture(), name='odd')
        self.passed(odd)
        self.press(odd, odd_manifest)
        with patch.object(MergeService, '_retry_preserved_m4b', return_value={'requeued': False, 'reason': 'Something new'}):
            self.assertIsNone(self.s._next_m4b_readmission())
        value = self.summary(odd)
        self.assertEqual((value['group'], value['readmission']['cause'], value['readmission']['fix'], 'retry' in value), ('other', 'unknown', 'update', False))

    def test_a_refused_repair_follows_the_same_rule(self):
        job_id, manifest = self.l.failed(REFUSED, fixture(), name='repair')
        with self.l.jobs._db() as db:
            m4b_readmission.request(db, job_id, 'repair', 100)
        with patch.object(MergeService, '_repair_damaged_m4b', return_value={'requeued': False, 'reason': 'Repair refused: x', 'cause': 'file_problem'}):
            self.assertIsNone(self.s._next_m4b_readmission())
        value = self.summary(job_id)
        self.assertEqual((value['group'], value['readmission']['kind'], value['repair'], 'retry' in value), ('other', 'repair', {'allowed': True, 'reason': ''}, False))


class StaleRefusalTests(RefusalCase):
    def test_changed_deciding_code_offers_the_book_again_for_one_attempt(self):
        job_id, manifest = self.refused()
        with patch.object(retry_refusal, 'preservation_sha256', lambda: 'f' * 64):  # a build whose preservation module changed
            value = self.summary(job_id)
            self.assertEqual((value['group'], value['retry'], value['readmission']['stale']), ('retry', {'allowed': True, 'reason': ''}, True))
            self.assertTrue(self.press(job_id, manifest)['queued_next'], 'pressed once under the new build')
            self.assertIsNone(self.s._next_m4b_readmission(), 'the same file is refused again')
            record = json.loads(self.stored(job_id)[1])
            self.assertEqual((record['key'], record['cause']), ('m4b_preservation:' + 'f' * 64, 'unsupported_file'))
            value = self.summary(job_id)
            self.assertEqual((value['group'], 'retry' in value, value['readmission']['stale']), ('unsupported', False, False), 'one attempt per book per build')
            with self.assertRaises(RetryRefused):
                self.press(job_id, manifest)

    def test_a_swapped_key_is_stale_and_only_update_fixes_go_stale(self):
        job_id, _ = self.refused()
        self.set_key(job_id, OLD_KEY)
        self.assertEqual((self.summary(job_id)['group'], self.summary(job_id)['readmission']['stale']), ('retry', True))
        files, manifest = self.l.failed(REFUSED, fixture(), name='files')
        self.passed(files)
        self.press(files, manifest)
        attempt = self.s.stage_root / files / str(uuid.uuid4())
        attempt.mkdir(parents=True)
        (attempt / 'normalized00000.wav').write_bytes(b'x')
        self.assertIsNone(self.s._next_m4b_readmission())
        self.set_key(files, OLD_KEY)
        self.assertEqual((self.summary(files)['group'], self.summary(files)['readmission']['stale']), ('other', False), 'a wait fix is checked live, never by build')


class LegacyConversionTests(RefusalCase):
    TEXTS = {'Failed M4B retained: Unsupported structural box': 'unsupported_file',
             'Prior audio working files need verified disposal before another source copy': 'working_files',
             'Failed M4B retained: Frozen review/source/cover/policy changed; failed job preserved': 'source_changed',
             'Repair refused: [WinError 32] The process cannot access the file': 'file_problem',
             'Failed M4B retained: database is locked': 'unknown'}

    def legacy_rows(self):
        made = {}
        jobs = [self.l.failed(REFUSED, fixture(), name='legacy%d' % index)[0] for index in range(len(self.TEXTS))]
        self.passed(*jobs)  # each source's dry run passed under this build, so a stale record is offered again
        with self.l.jobs._db() as db:
            m4b_readmission.ensure(db)
            for index, (job_id, (text, cause)) in enumerate(zip(jobs, self.TEXTS.items()), 1):
                db.execute('INSERT INTO m4b_readmissions VALUES(?,?,?,?,?,?,?,?)',
                           (job_id, 'repair' if text.startswith('Repair') else 'retry', index, 'refused', None, text,
                            '2026-10-18T18:43:13+00:00', '2026-10-18T20:32:23+00:00'))
                made[job_id] = (text, cause)
        return made

    def rows(self):
        with self.l.jobs._db() as db:
            return {row[0]: tuple(row) for row in db.execute('SELECT * FROM m4b_readmissions')}

    def test_v0180_records_are_converted_once_keyed_to_the_v0180_code_and_lose_nothing(self):
        made = self.legacy_rows()
        before = self.rows()
        unconverted = {job_id: self.summary(job_id)['readmission'] for job_id in made}
        with self.l.jobs._db() as db:
            self.assertEqual(m4b_readmission.convert_legacy(db), 5)
            self.assertEqual(m4b_readmission.convert_legacy(db), 0, 'once')
        after = self.rows()
        for job_id, (text, cause) in made.items():
            old, new = before[job_id], after[job_id]
            self.assertEqual(old[:5] + old[6:], new[:5] + new[6:], 'state, kind, order, child and times kept')
            record = json.loads(new[5])
            key = 'm4b_preservation:' + retry_refusal.LEGACY_PRESERVATION_SHA256 if cause == 'unsupported_file' else 'app:0.18.0'
            self.assertEqual(record, {'reason': text, 'cause': cause, 'fix': retry_refusal.FIXES[cause], 'app_version': '0.18.0',
                                      'key': key, 'at': '2026-10-18T20:32:23+00:00', 'converted': True})
            self.assertEqual(self.summary(job_id)['readmission'], unconverted[job_id], 'an unconverted record reads exactly as converted')
        # The preservation module changed since v0.18.0, so a converted structural-box refusal is offered again.
        structural = next(job_id for job_id, (text, cause) in made.items() if cause == 'unsupported_file')
        self.assertNotEqual(retry_refusal.preservation_sha256(), retry_refusal.LEGACY_PRESERVATION_SHA256)
        self.assertEqual((self.summary(structural)['readmission']['stale'], self.summary(structural)['group']), (True, 'retry'))
        unknown = next(job_id for job_id, (text, cause) in made.items() if cause == 'unknown')
        self.assertEqual(self.summary(unknown)['readmission']['stale'], retry_refusal.app_version() != '0.18.0', 'unknown causes are keyed on the app version')

    def test_converted_records_still_go_stale_only_on_changed_code(self):
        made = self.legacy_rows()
        with self.l.jobs._db() as db:
            m4b_readmission.convert_legacy(db)
        structural = next(job_id for job_id, (text, cause) in made.items() if cause == 'unsupported_file')
        with patch.object(retry_refusal, 'preservation_sha256', lambda: retry_refusal.LEGACY_PRESERVATION_SHA256):
            value = self.summary(structural)
            self.assertEqual((value['readmission']['stale'], value['group'], 'retry' in value), (False, 'unsupported', False), 'not stale under the v0.18.0 code')

    def test_typed_records_are_not_reconverted(self):
        job_id, _ = self.refused()
        before = self.stored(job_id)
        with self.l.jobs._db() as db:
            self.assertEqual(m4b_readmission.convert_legacy(db), 0)
        self.assertEqual(self.stored(job_id), before)


class DryRunTests(RefusalCase):
    """Sergei-approved pre-check: an M4B row is "ready to retry" only after the read-only plan() dry run on its source
    (the repair check, m4b_repair.check) passed under this build. The check opens the source read-only."""
    def check(self, job_id):
        import m4b_repair
        return m4b_repair.check(self.l.row(job_id))

    def source(self, name):
        path = self.l.library / name / 'source.m4b'
        return path, (path.read_bytes(), path.stat().st_mtime_ns)

    def test_a_passed_dry_run_keeps_the_book_ready_and_reads_only(self):
        job_id, _ = self.l.failed(REFUSED, fixture(), name='intact')
        path, before = self.source('intact')
        self.assertEqual(self.check(job_id)['state'], 'intact')
        self.assertEqual(self.summary(job_id), {'group': 'retry', 'cause': None, 'originals_untouched': True, 'precheck': 'passed', 'retry': {'allowed': True, 'reason': ''}})
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before, 'the source is only read')

    def test_a_refused_dry_run_is_m4b_not_supported_and_queues_nothing(self):
        job_id, manifest = self.l.failed(REFUSED, with_iods(fixture(), TRACK_IODS), name='refusing')
        path, before = self.source('refusing')
        self.assertEqual(self.check(job_id)['state'], 'refused')
        value = self.summary(job_id)
        self.assertEqual((value['group'], 'retry' in value, 'readmission' in value), ('unsupported', False, False))
        with self.assertRaises(RetryRefused) as caught:
            self.press(job_id, manifest)
        self.assertEqual(str(caught.exception), RETRY_BOOK_CHANGED)
        with self.l.jobs._db() as db:
            m4b_readmission.ensure(db)
            self.assertIsNone(db.execute('SELECT 1 FROM m4b_readmissions WHERE parent_job_id=?', (job_id,)).fetchone(), 'nothing queued')
        self.assertIsNone(self.s._retry_one(job_id))
        self.assertNotIn(job_id, [key for key, item in self.s.attention_summary(retry=False).items() if item['group'] == 'retry'], 'Retry all leaves it out')
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before, 'the source is only read')
        import m4b_repair
        with patch.object(m4b_repair, '_MODULE_SHA256', 'f' * 64):  # a build whose preservation module changed
            self.assertEqual(self.summary(job_id)['group'], 'checking', 'checked again under the new build (follow-up section 2), not held back by the old build\'s check')

    def test_an_unreadable_source_is_not_taken_for_a_refusal(self):
        job_id, _ = self.l.failed(REFUSED, fixture(), name='gone')
        (self.l.library / 'gone' / 'source.m4b').unlink()
        result = self.check(job_id)
        self.assertEqual((result['state'], result.get('unavailable')), ('refused', True))
        self.assertNotEqual(self.summary(job_id)['group'], 'unsupported')

    def test_a_stale_refusal_follows_this_builds_dry_run(self):
        job_id, _ = self.refused()  # unsupported_file, current
        self.set_key(job_id, OLD_KEY)  # the deciding code changed since
        self.assertEqual(self.check(job_id)['state'], 'refused')
        value = self.summary(job_id)
        self.assertEqual((value['group'], 'retry' in value, value['readmission']['stale']), ('unsupported', False, True), 'refused again by this build: not offered')
        intact, manifest = self.l.failed(REFUSED, fixture(), name='intact')
        self.passed(intact)
        self.press(intact, manifest)
        with patch.object(MergeService, '_retry_preserved_m4b', return_value={'requeued': False, 'reason': 'Failed M4B retained: Unsupported structural box', 'cause': 'unsupported_file'}):
            self.assertIsNone(self.s._next_m4b_readmission())
        self.set_key(intact, OLD_KEY)
        self.assertEqual(self.check(intact)['state'], 'intact')
        value = self.summary(intact)
        self.assertEqual((value['group'], value['retry'], value['readmission']['stale'], value['precheck']), ('retry', {'allowed': True, 'reason': ''}, True, 'passed'),
                         'passes now: ready to retry, "this M4B now passes its check"')
        self.assertTrue(self.press(intact, manifest)['queued_next'])


# The spec's words (RefusedRetry follow-up, 2026-10-19), pinned here rather than imported from the code under test.
CHECKING = 'The app is checking this M4B before offering Retry. The row updates itself.'
REPAIR_FILES = 'Working files from an earlier attempt are still present. Repair after they are cleared.'


class PrecheckStateTests(RefusalCase):
    """Follow-up section 2: an M4B row reads "ready to retry" only after its read-only dry run passed. Before that it
    is Checking (Retry disabled, out of Retry all); a check that cannot open the source, or that stops with an error,
    reads "can't open" (Retry enabled, group Other) and never "checking" forever (findings F2, F3a, F3b)."""
    def setUp(self):
        super().setUp()
        cache = patch.dict(m4b_repair._CACHE)  # this run's in-memory check results end with the test
        cache.start()
        self.addCleanup(cache.stop)

    def run_checker(self, *job_ids, check=None):
        """The real background pass (MergeService._repair_check_work), on this thread."""
        self.s._repair_pending = list(job_ids)
        self.s.__dict__.setdefault('_repair_skipped', set())
        self.s._repair_running = True
        self.s.invalidate_status = Mock()
        with patch.object(m4b_repair, 'check', check) if check else contextlib.nullcontext():
            self.s._repair_check_work(threading.Event())

    def queued(self, job_id):
        with self.l.jobs._db() as db:
            m4b_readmission.ensure(db)
            return db.execute('SELECT 1 FROM m4b_readmissions WHERE parent_job_id=?', (job_id,)).fetchone() is not None

    def test_an_unchecked_row_is_checking_with_retry_disabled_until_the_check_ends(self):
        job_id, manifest = self.l.failed(REFUSED, fixture(), name='pending')
        value = self.summary(job_id)
        self.assertEqual({key: value.get(key) for key in ('group', 'precheck', 'retry')},
                         {'group': 'checking', 'precheck': 'pending', 'retry': {'allowed': False, 'reason': CHECKING}})
        self.assertEqual(self.s.attention_summary(retry=False)[job_id]['group'], 'checking', 'the counts read the same group')
        self.checks.assert_called_with([job_id])  # the background check is asked for, off the request thread
        with self.assertRaises(RetryRefused) as caught:
            self.s.retry_all()
        self.assertEqual(str(caught.exception), RETRY_ALL_NONE, 'not in Can retry, so not in the Retry all dialog')
        with self.assertRaises(RetryRefused) as caught:
            self.press(job_id, manifest)
        self.assertEqual(str(caught.exception), RETRY_BOOK_CHANGED, 'a forced press is refused')
        self.assertIsNone(self.s._retry_one(job_id))
        self.assertFalse(self.queued(job_id), 'and queues nothing')
        # The check ends. Passed: ready in place, Retry back. Refused: M4B not supported.
        refusing, _ = self.l.failed(REFUSED, with_iods(fixture(), TRACK_IODS), name='refusing')
        self.run_checker(job_id, refusing)
        value = self.summary(job_id)
        self.assertEqual((value['group'], value['precheck'], value['retry']), ('retry', 'passed', {'allowed': True, 'reason': ''}))
        self.assertEqual((self.summary(refusing)['group'], 'precheck' in self.summary(refusing)), ('unsupported', False))
        self.assertTrue(self.press(job_id, manifest)['queued_next'])

    def test_a_source_the_check_cannot_open_reads_cant_open_and_never_checking_again(self):
        job_id, manifest = self.l.failed(REFUSED, fixture(), name='gone')
        present, _ = self.l.failed(REFUSED, fixture(), name='present')  # positive control: same pass, source there
        (self.l.library / 'gone' / 'source.m4b').unlink()
        self.run_checker(job_id, present)
        value = self.summary(job_id)
        self.assertEqual((value['group'], value['precheck'], value['retry']), ('other', 'unavailable', {'allowed': True, 'reason': ''}))
        self.assertTrue(value['precheck_reason'].startswith('Source unavailable: '), value['precheck_reason'])
        self.assertEqual(self.summary(present)['precheck'], 'passed')
        self.assertEqual([key for key, item in self.s.attention_summary(retry=False).items() if item['group'] == 'retry'], [present], 'Retry all leaves it out')
        m4b_repair._CACHE.clear()  # the module's own cache forgets (it is bounded); this run still knows
        self.assertEqual((self.summary(job_id)['group'], self.summary(job_id)['precheck']), ('other', 'unavailable'), 'never back to checking')
        self.assertTrue(self.press(job_id, manifest)['queued_next'], 'enabled: a press (or Retry selected) does the real read')

    def test_a_check_that_throws_reads_cant_open_and_is_not_read_again(self):
        job_id, _ = self.l.failed(REFUSED, fixture(), name='throws')
        self.run_checker(job_id, check=Mock(side_effect=ValueError('fixture parse failure')))
        value = self.summary(job_id)
        self.assertEqual((value['group'], value['precheck'], value['precheck_reason'], value['retry']),
                         ('other', 'unavailable', 'Source check failed: ValueError: fixture parse failure', {'allowed': True, 'reason': ''}))
        self.assertIn(job_id, self.s._repair_skipped, 'never re-read in a loop')

    def test_precedence_refusal_then_cant_open_then_checking_then_stale_then_ready(self):
        job_id, _ = self.refused()  # unsupported_file, current
        audio_jobs.REPAIR_CHECKS.pop(audio_jobs.repair_check_key(self.l.row(job_id)))  # not checked under this build
        value = self.summary(job_id)
        self.assertEqual((value['group'], 'precheck' in value), ('unsupported', False), 'a current refusal comes first')
        self.set_key(job_id, OLD_KEY)  # the deciding code changed since: the refusal is stale
        self.assertEqual((self.summary(job_id)['group'], self.summary(job_id)['precheck']), ('checking', 'pending'), 'stale, not yet checked: Checking')
        self.s._repair_failed = {job_id: 'Source unavailable: fixture'}
        self.assertEqual((self.summary(job_id)['group'], self.summary(job_id)['precheck']), ('other', 'unavailable'), "stale, cannot open: can't open")
        self.passed(job_id)
        value = self.summary(job_id)
        self.assertEqual((value['group'], value['precheck'], value['readmission']['stale'], value['retry']), ('retry', 'passed', True, {'allowed': True, 'reason': ''}),
                         'stale, check passed: ready again (a finished check wins over an earlier failure)')


class RepairVerbAndFolderTests(RefusalCase):
    """Follow-up points 3b and 3c: a refused Repair's disabled reason says Repair, and a working-files refusal names the
    absolute working folder for the Technical detail line only."""
    def leftover(self, job_id):
        attempt = self.s.stage_root / job_id / str(uuid.uuid4())
        attempt.mkdir(parents=True)
        (attempt / 'source00000.m4b').write_bytes(b'unfinished copy')

    def test_a_refused_repair_on_working_files_says_repair(self):
        # Superseded in part by follow-up 2 (section 2.3): blocked files offer no Repair and no Retry (no disabled
        # ghost), and the blocked words have no verb. The record keeps its kind for the Technical detail line.
        job_id, manifest = self.l.failed(REFUSED, fixture(), name='repair-files')
        self.leftover(job_id)
        with self.l.jobs._db() as db:
            m4b_readmission.request(db, job_id, 'repair', 100)
        self.assertIsNone(self.s._next_m4b_readmission(), 'the real Repair admission refuses on the leftover files')
        value = self.summary(job_id)
        self.assertEqual((value['readmission']['kind'], value['readmission']['cause'], 'repair' in value, 'retry' in value, value['working']['state']),
                         ('repair', 'working_files', False, False, 'blocked'))
        self.assertEqual(REPAIR_FILES, audio_jobs.files_present('repair'), 'the server words still follow the kind')

    def test_a_working_files_refusal_names_the_absolute_working_folder(self):
        job_id, manifest = self.l.failed(REFUSED, fixture(), name='folder')
        self.passed(job_id)
        self.press(job_id, manifest)
        self.leftover(job_id)
        self.assertIsNone(self.s._next_m4b_readmission())
        folder = self.summary(job_id)['working_folder']
        self.assertTrue(os.path.isabs(folder), folder)
        self.assertEqual(folder, os.path.abspath(self.s.stage_root / job_id))
        other, other_manifest = self.l.failed(REFUSED, fixture(), name='no-folder')  # positive control: another cause
        self.passed(other)
        self.press(other, other_manifest)
        (self.l.library / 'no-folder' / 'source.m4b').unlink()
        self.assertIsNone(self.s._next_m4b_readmission())
        value = self.summary(other)
        self.assertEqual((value['readmission']['cause'], 'working_folder' in value), ('file_problem', False))


class BulkCapabilityTests(RefusalCase):
    def user_fixable(self, name='book', kind='retry'):
        job_id, manifest = self.l.failed(REFUSED, fixture(), name=name)
        self.passed(job_id)
        with self.l.jobs._db() as db:
            m4b_readmission.request(db, job_id, kind, 1)
        m4b_readmission.next_job(self.l.jobs._db, lambda *_: {
            'requeued': False, 'reason': 'Filesystem stream check refused the source', 'cause': 'file_problem'}, 2)
        return job_id, manifest

    def test_all_44_other_books_reach_worker_admission_without_changing_parents(self):
        ids = [self.user_fixable('other%d' % index)[0] for index in range(44)]
        before = {job_id: self.l.row(job_id) for job_id in ids}
        summary = self.s.attention_summary()
        self.assertEqual([(summary[job_id]['group'], summary[job_id]['retry']['allowed']) for job_id in ids], [('other', True)] * 44)
        self.s.retry_all()
        self.s._retry_all_thread.join(10)
        self.assertFalse(self.s._retry_all_thread.is_alive())
        self.assertEqual((self.s._retry_all_run['total'], self.s._retry_all_run['accepted'], self.s._retry_all_run['refused']), (44, 44, 0))
        with self.l.jobs._db() as db:
            self.assertEqual(m4b_readmission.pending_count(db), 44)
            progress = m4b_readmission.target_progress(db, ids)
        self.assertEqual((progress['counts']['waiting'], progress['counts']['queued']), (44, 0))
        # Request acceptance grants no native/stream bypass: the unchanged worker owns admission.
        with patch.object(MergeService, '_retry_preserved_m4b', return_value={
                'requeued': False, 'reason': 'Current stream check still refuses', 'cause': 'file_problem'}) as admit:
            self.assertIsNone(self.s._next_m4b_readmission())
        self.assertEqual([call.args[0]['job_id'] for call in admit.call_args_list], ids)
        self.assertTrue(all(call.kwargs == {'in_worker': True} for call in admit.call_args_list))
        self.assertEqual({job_id: self.l.row(job_id) for job_id in ids}, before)
        self.assertEqual(self.l.count(), 44, 'no child is invented for a refused admission')

    def test_selected_other_checks_identity_revision_and_newest_parent(self):
        job_id, manifest = self.user_fixable()
        target = {'id': manifest['candidate_id'], 'revision': 1, 'job_id': job_id, 'kind': 'retry'}
        self.assertIsNone(self.s._retry_one(job_id, target=target | {'revision': 2}))
        self.assertIsNone(self.s._retry_one(job_id, target=target | {'id': 'different-book'}))
        self.assertIsNone(self.s._retry_one(job_id, 'repair', target))
        self.assertEqual(self.s._retry_one(job_id, target=target), 'next')
        other, other_manifest = self.user_fixable('stale')
        self.l.failed(REFUSED, fixture(), name='newer', candidate=other_manifest['candidate_id'])
        self.assertIsNone(self.s._retry_one(other))
        self.assertEqual(self.stored(other)[0], 'refused')

    def test_selected_repair_keeps_its_mode_and_cannot_be_submitted_as_retry(self):
        job_id, manifest = self.user_fixable(kind='repair')
        self.assertTrue(self.s.attention_summary()[job_id]['repair']['allowed'])
        self.assertIsNone(self.s._retry_one(job_id, 'retry'))
        target = {'id': manifest['candidate_id'], 'revision': 1, 'job_id': job_id, 'kind': 'repair'}
        self.assertEqual(self.s._retry_one(job_id, 'repair', target), 'next')
        with self.l.jobs._db() as db:
            value = m4b_readmission.describe(db, job_id)
        self.assertEqual((value['kind'], value['state'], value['child_job_id']), ('repair', 'queued', None))


if __name__ == '__main__':
    unittest.main()
