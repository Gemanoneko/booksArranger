"""A catalog with no audio-staging folder (RefusedRetry follow-up 3, section 6, 2026-10-19).

Before the fix the working-file listing refused the missing root itself, so every M4B Retry on such a catalog was
refused as a file problem ("Prior working-file ownership requires attention: An inspected destination ancestor is
unavailable"). Those records are converted once so they read as stale (one attempt each), not "Check the folder".
Synthetic catalogs and synthetic M4B bytes only; the worker's admission runs the real read-only plan().
"""
import json
import os
import uuid

import m4b_readmission
import retry_refusal
from native_io import BoundaryError
from test_attention_repair import REFUSED
from test_m4b_preservation import fixture
from test_refused_retry import RefusalCase

BUG_TEXT = 'Prior working-file ownership requires attention: An inspected destination ancestor is unavailable'


class MissingStagingRootTests(RefusalCase):
    def test_a_catalog_without_a_staging_root_admits_the_retry(self):
        job_id, manifest = self.l.failed(REFUSED, fixture(), name='nostage')
        self.passed(job_id)
        self.s.stage_root.rmdir()  # this catalog never created it
        self.assertFalse(os.path.lexists(self.s.stage_root))
        self.assertIs(self.s._m4b_prior_audio(job_id), False)
        self.assertIsNone(self.s._m4b_working_refusal(job_id), 'no working files, so no refusal of any cause')
        self.assertTrue(self.press(job_id, manifest)['queued_next'])
        child = self.s._next_m4b_readmission()
        self.assertIsNotNone(child, 'the real admission accepts it: the child runs next')
        self.assertEqual(self.stored(job_id)[0], 'admitted')
        self.assertFalse(os.path.lexists(self.s.stage_root), 'a read-only check: the root is not created by it')

    def test_positive_controls_the_root_still_guards_leftovers_and_a_missing_parent(self):
        job_id, _ = self.l.failed(REFUSED, fixture(), name='leftover')
        attempt = self.s.stage_root / job_id / str(uuid.uuid4())
        attempt.mkdir(parents=True)
        (attempt / 'source00000.m4b').write_bytes(b'copy')
        self.assertIs(self.s._m4b_prior_audio(job_id), True, 'an existing root is still listed')
        self.assertEqual(self.s._m4b_working_refusal(job_id)['cause'], 'working_files')
        # The parent (the cache folder) missing too is not "no files": it cannot be proven and stays a file problem.
        self.s.stage_root = self.l.base / 'no-such-cache' / 'audio-staging'
        with self.assertRaises(BoundaryError):
            self.s._m4b_prior_audio(job_id)
        self.assertEqual(self.s._m4b_working_refusal(job_id)['cause'], 'file_problem')


class ResolvedConversionTests(RefusalCase):
    def seed(self, text, name, kind='retry'):
        job_id, manifest = self.l.failed(REFUSED, fixture(), name=name)
        self.passed(job_id)
        record = retry_refusal.record(text, 'file_problem', '2026-10-19T08:00:00+00:00')
        with self.l.jobs._db() as db:
            m4b_readmission.ensure(db)
            seq = db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM m4b_readmissions').fetchone()[0]
            db.execute('INSERT INTO m4b_readmissions VALUES(?,?,?,?,?,?,?,?)',
                       (job_id, kind, seq, 'refused', None, json.dumps(record), '2026-10-19T08:00:00+00:00', '2026-10-19T08:00:00+00:00'))
        return job_id, manifest

    def test_records_from_the_missing_root_defect_read_stale_once_converted(self):
        bug, manifest = self.seed(BUG_TEXT, 'bug')
        other, _ = self.seed('Failed M4B retained: [WinError 32] The process cannot access the file', 'locked')
        legacy, _ = self.l.failed(REFUSED, fixture(), name='legacy')  # a v0.18.0 plain-text record of the same defect
        self.passed(legacy)
        with self.l.jobs._db() as db:
            db.execute('INSERT INTO m4b_readmissions VALUES(?,?,?,?,?,?,?,?)', (legacy, 'retry', 99, 'refused', None, BUG_TEXT, 'a', 'b'))
        before = self.summary(bug)
        self.assertEqual((before['group'], before['readmission']['cause'], before['readmission']['stale']), ('other', 'file_problem', False))
        with self.l.jobs._db() as db:
            self.assertEqual(m4b_readmission.convert_legacy(db), 3, 'one legacy text typed, then two defect records resolved')
            self.assertEqual(m4b_readmission.convert_legacy(db), 0, 'once')
        for job_id in (bug, legacy):
            value = self.summary(job_id)
            self.assertEqual((value['group'], value['retry'], value['readmission']['stale'], value['readmission']['reason']),
                             ('retry', {'allowed': True, 'reason': ''}, True, BUG_TEXT), 'stale: back in Can retry, text kept for Technical detail')
            self.assertEqual(json.loads(self.stored(job_id)[1])['resolved'], 'missing_staging_root')
        value = self.summary(other)
        self.assertEqual((value['group'], value['readmission']['stale']), ('other', False), 'positive control: another file problem is untouched')
        self.assertIn(bug, [key for key, item in self.s.attention_summary(retry=False).items() if item['group'] == 'retry'], 'Retry all takes it')
        # One attempt per book: the press stores a new record (here admitted), so nothing stays resolved.
        self.assertTrue(self.press(bug, manifest)['queued_next'])
        self.assertIsNotNone(self.s._next_m4b_readmission())
        self.assertEqual(self.stored(bug)[0], 'admitted')
