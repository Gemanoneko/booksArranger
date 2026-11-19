"""0.30.0 sort-1: a job queued before the storage moves passes the pre-conversion check after them.

Sergei's 263 unsorted books: jobs queued before the 14 Nov portable move recorded application-data paths (the reviewed
cover in merge-cache\\covers) under the original data folder. The worker's revision guard (MergeService._guard) rebuilds
the book's manifest, whose cover now lies in the new data folder, and compared the two as plain text, so 246+ jobs were
refused with "Source changed — review required" though nothing had changed. Retry ran the same check and was refused too.

The moves are replayed on private folders with real native identities (test_recovery_ancestry_moves.MovesReplay: the
operator's census and manifest for the explicit relocation, portable_storage_migration's own census and binding producer
for the portable move). Only a location the relocation records prove is bridged: a library path, a cover no move
explains, a different cover or a source whose bytes changed is still refused.
"""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid

from audio_jobs import REVISION_GUARD_REFUSAL, RETRY_REVIEW_CHANGED, RetryRefused
from manifest_compatibility import equivalent_manifest
from merge_service import JOB_ONLY_FIELDS, MergeService
import retry_intent
import storage_relocation_native as native
from test_blocked_retry import Queue
from test_recovery_ancestry_moves import SCOPE, MovesReplay

COVER = str(uuid.uuid4())


@unittest.skipUnless(os.name == 'nt', 'Windows native identities and junctions')
class RelocatedJobPathTests(MovesReplay, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.move_explicitly()
        self.runtime = self.move_portably()
        self.admit(*self.runtime)
        self.library = self.area / 'Library' / 'Audiobooks'
        self.before = self.old_root / SCOPE  # the data folder every job queued before the moves recorded

    def job(self, data, candidate=None, sha='a' * 64, source='01.mp3', cover=COVER, **extra):
        """A frozen job manifest as build_manifest makes it: library sources, and the reviewed cover in `data`."""
        return {'job_id': str(uuid.uuid4()), 'candidate_id': candidate or str(uuid.uuid4()), 'candidate_revision': 1,
                'sources': [{'path': str(self.library / 'Book' / source), 'size': 3, 'modified': 1, 'sha256': sha,
                             'fingerprint': {'size': 3, 'modified': 1}, 'metadata': {}}],
                'metadata': {'title': 'Fixture', 'author': 'Author'}, 'root': str(self.library),
                'output_root': str(self.area / 'Library' / 'Audiobooks Sorted'), 'destination': 'Author\\Fixture.m4b',
                'profile': 'fixture', 'evidence': {}, 'cleanup_policy': {'enabled': False},
                'cover': {'id': cover, 'sha256': 'c' * 64, 'path': str(Path(data) / 'merge-cache' / 'covers' / (cover + '.jpg'))},
                **extra}

    @staticmethod
    def same(current, frozen):
        return equivalent_manifest(current, frozen, ignore_fields=JOB_ONLY_FIELDS)

    def test_a_job_queued_before_both_moves_passes_the_check_after_them(self):
        frozen = self.job(self.before)
        current = dict(self.job(self.data, frozen['candidate_id']), job_id=str(uuid.uuid4()))
        self.assertNotEqual(frozen['cover']['path'], current['cover']['path'])
        self.assertTrue(self.same(current, frozen), 'the 15 Nov refusal: same book, data folder moved twice')
        self.assertTrue(equivalent_manifest(frozen, current), 'either side may be the recorded one (M4B Retry and Repair)')
        between = self.job(self.new_root / SCOPE, frozen['candidate_id'])  # the first move's physical copy
        self.assertTrue(self.same(current, between))
        # The worker's own check, MergeService._guard, through the review's rebuilt manifest.
        self.assertTrue(self.guard(frozen, current))
        # The bridge is the relocation's records, nothing else: with no storage relocation selected it is plain text.
        native.close()
        self.assertFalse(self.same(current, frozen))

    def test_a_later_portable_move_extends_the_bridge(self):
        frozen = self.job(self.before)
        native.close()
        self.admit(*self.move_portably(self.runtime))
        self.assertTrue(self.same(self.job(self.data, frozen['candidate_id']), frozen))

    def test_real_changes_are_still_refused(self):
        frozen = self.job(self.before)
        candidate = frozen['candidate_id']
        changed = {
            'source bytes changed': self.job(self.data, candidate, sha='b' * 64),
            'source moved inside the library (library paths are never bridged)': self.job(self.data, candidate, source='02.mp3'),
            'another cover in the new data folder': self.job(self.data, candidate, cover=str(uuid.uuid4())),
            'a cover folder no recorded move explains': self.job(self.area / 'Elsewhere' / 'data', candidate),
            'a folder beside the relocated data folder': self.job(self.old_root / 'Projects' / 'Other', candidate),
        }
        for name, current in changed.items():
            with self.subTest(name):
                self.assertFalse(self.same(current, frozen))
                self.assertFalse(self.guard(frozen, current))

    def test_an_explicit_route_retry_bridges_the_frozen_parent(self):
        # retry_intent.bind/validate compare the failed parent's frozen manifest with the rebuilt one the same way.
        frozen = self.job(self.before)
        parent = {'manifest': json.dumps(frozen), 'manifest_hash': retry_intent.digest(frozen), 'state': 'needs attention',
                  'output': None, 'journal': '{}', 'job_id': frozen['job_id']}
        current = self.job(self.data, frozen['candidate_id'])
        root = str(self.area / 'Library' / 'Audiobooks Sorted')
        child = retry_intent.bind(parent, current, root)
        self.assertTrue(retry_intent.validate(child, current, root))
        with self.assertRaisesRegex(ValueError, 'Frozen approved source/review/cover/policy changed'):
            retry_intent.bind(parent, self.job(self.data, frozen['candidate_id'], sha='b' * 64), root)

    def guard(self, frozen, current):
        """MergeService._guard over a review that rebuilds `current` for the book."""
        reviews = SimpleNamespace(build_manifest=lambda library, identity, revision, **options: copy.deepcopy(current))
        service = SimpleNamespace(_reacquire_admission=lambda **options: None, _no_scan=lambda: None, reviews=reviews)
        return MergeService._guard(service, copy.deepcopy(frozen))

    def test_retry_returns_a_job_the_move_refused_and_not_a_changed_one(self):
        """The 246+ jobs refused on 15 Nov: Retry (and Retry all, which uses it) now requeues them; one whose source really
        changed is refused again and left exactly as it was."""
        queue = Queue(self.area / 'queue');self.addCleanup(queue.jobs.close);self.addCleanup(queue.release.set)
        honest, changed = (queue.manifest(book, **self.job(self.before, book)) for book in (str(uuid.uuid4()), str(uuid.uuid4())))
        rebuilt = {honest['candidate_id']: self.job(self.data, honest['candidate_id']),
                   changed['candidate_id']: self.job(self.data, changed['candidate_id'], sha='b' * 64)}
        for item in (honest, changed):queue.jobs.enqueue(item)
        # 15 Nov: the worker's guard refused both before any work (the shape it records is the same whatever the cause).
        queue.guard = lambda manifest: False
        queue.jobs.resume();queue.wait()
        for item in (honest, changed):
            row = queue.row(item['job_id'])
            self.assertEqual((row['state'], row['reason']), ('needs attention', REVISION_GUARD_REFUSAL))
            self.assertEqual(json.loads(row['journal'])['failure']['exception_class'], 'ValueError')
        queue.jobs._stop.clear()
        self.assertEqual({job: value['allowed'] for job, value in queue.statuses().items()},
                         {honest['job_id']: True, changed['job_id']: True}, 'both are offered Retry, as before')
        queue.guard = lambda manifest: self.guard(manifest, rebuilt[manifest['candidate_id']])
        self.assertEqual(queue.retry(honest['job_id']), {'job_id': honest['job_id'], 'requeued': True})
        before = queue.row(changed['job_id'])
        with self.assertRaises(RetryRefused) as refused:queue.retry(changed['job_id'])
        self.assertEqual(str(refused.exception), RETRY_REVIEW_CHANGED)
        self.assertEqual(queue.row(changed['job_id']), before, 'a refused Retry leaves the whole row byte-identical')
        queue.jobs.resume();queue.wait()
        self.assertEqual([run[0] for run in queue.runs], [honest['job_id']], 'the honest job converts; the changed one does not')
        self.assertEqual(queue.row(changed['job_id']), before)


if __name__ == '__main__':
    unittest.main()
