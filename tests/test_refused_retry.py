"""RefusedRetry spec (Judy, 2026-10-19): typed refusal records, the group and offer each fix gives, the
server gate, re-offer when the deciding code changes, and the one-time conversion of v0.18.0 records.

Synthetic catalogs and synthetic M4B bytes only; the worker's admission runs the real read-only plan().
"""
import json
import unittest
import uuid
from unittest.mock import patch

import m4b_readmission
import retry_refusal
from audio_jobs import RetryRefused, RETRY_BOOK_CHANGED, RETRY_FILES_PRESENT
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
        """A failed M4B row, a Retry press, then the worker's real admission refusing it."""
        job_id, manifest = self.l.failed(REFUSED, source if source is not None else with_iods(fixture(), TRACK_IODS), name=name)
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
        summary = self.s.attention_summary()
        self.assertEqual(summary[other], {'group': 'retry', 'cause': None, 'originals_untouched': True, 'retry': {'allowed': True, 'reason': ''}})
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
        self.assertEqual([key for key, item in self.s.attention_summary(retry=False).items() if item['group'] == 'retry'], [other],
                         'Retry all takes the server group, which no longer holds the refused book')

    def test_each_fix_decides_the_group_and_the_offer(self):
        # working_files (fix wait): disabled with the reason until the listing passes, then enabled.
        job_id, manifest = self.l.failed(REFUSED, fixture(), name='files')
        attempt = self.s.stage_root / job_id / str(uuid.uuid4())
        attempt.mkdir(parents=True)
        leftover = attempt / 'source00000.m4b'
        leftover.write_bytes(b'unfinished copy')
        self.press(job_id, manifest)
        self.assertIsNone(self.s._next_m4b_readmission())
        value = self.summary(job_id)
        self.assertEqual((value['group'], value['readmission']['cause'], value['readmission']['fix']), ('other', 'working_files', 'wait'))
        self.assertEqual(value['retry'], {'allowed': False, 'reason': RETRY_FILES_PRESENT})
        with self.assertRaises(RetryRefused) as caught:
            self.press(job_id, manifest)
        self.assertEqual(str(caught.exception), RETRY_FILES_PRESENT)
        leftover.unlink()
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
        self.press(missing, missing_manifest)
        source = self.l.library / 'missing' / 'source.m4b'
        source.unlink()
        self.assertIsNone(self.s._next_m4b_readmission())
        value = self.summary(missing)
        self.assertEqual((value['group'], value['readmission']['cause'], value['retry']), ('other', 'file_problem', {'allowed': True, 'reason': ''}))
        # unknown (no cause sent): no control, like an update-only cause.
        odd, odd_manifest = self.l.failed(REFUSED, fixture(), name='odd')
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
        attempt = self.s.stage_root / files / str(uuid.uuid4())
        attempt.mkdir(parents=True)
        (attempt / 'normalized00000.wav').write_bytes(b'x')
        self.press(files, manifest)
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
        self.assertEqual(self.summary(job_id), {'group': 'retry', 'cause': None, 'originals_untouched': True, 'retry': {'allowed': True, 'reason': ''}})
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
            self.assertEqual(self.summary(job_id)['group'], 'retry', 'not held back by the old build\'s check')

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
        self.press(intact, manifest)
        with patch.object(MergeService, '_retry_preserved_m4b', return_value={'requeued': False, 'reason': 'Failed M4B retained: Unsupported structural box', 'cause': 'unsupported_file'}):
            self.assertIsNone(self.s._next_m4b_readmission())
        self.set_key(intact, OLD_KEY)
        self.assertEqual(self.check(intact)['state'], 'intact')
        value = self.summary(intact)
        self.assertEqual((value['group'], value['retry'], value['readmission']['stale']), ('retry', {'allowed': True, 'reason': ''}, True), 'passes now: Stopped — try again')
        self.assertTrue(self.press(intact, manifest)['queued_next'])


if __name__ == '__main__':
    unittest.main()
