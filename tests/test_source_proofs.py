"""0.21.0 attempt-scoped source fingerprints: one full hash per source per attempt, cheap identity afterwards."""
import collections, contextlib, hashlib, os, shutil, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

import audio_pipeline
import source_proofs
from audio_pipeline import ValidationError, fingerprint, same_source
from native_io import BoundaryError, VerifiedFile
from source_cleanup import CleanupJobs

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'source-proof-tests'


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'track.mp3'; self.path.write_bytes(b'reviewed audio bytes' * 1000)
        self.item = {'path': str(self.path), **fingerprint(self.path), 'sha256': hashlib.sha256(self.path.read_bytes()).hexdigest()}
        self.reads = []; real = audio_pipeline.digest
        def counted(path, *args, **kwargs):
            self.reads.append(str(path)); return real(path, *args, **kwargs)
        patcher = patch('audio_pipeline.digest', side_effect=counted); patcher.start(); self.addCleanup(patcher.stop)

    def rewrite(self, data, replace=False, keep_time=True):
        stamp = os.stat(self.path).st_mtime_ns
        if replace:
            fresh = self.path.with_suffix('.new'); fresh.write_bytes(data); os.replace(fresh, self.path)  # new file ID
        else:
            with open(self.path, 'r+b') as stream:stream.write(data)  # same file ID
        if keep_time:os.utime(self.path, ns=(stamp, stamp))

    def test_unchanged_file_skips_the_rehash_inside_one_attempt_only(self):
        with source_proofs.attempt('a'):
            same_source(self.item, None); same_source(self.item, None); same_source(self.item, None)
        self.assertEqual(len(self.reads), 1)
        same_source(self.item, None); same_source(self.item, None)  # outside an attempt every check reads in full
        self.assertEqual(len(self.reads), 3)
        with source_proofs.attempt('b'):same_source(self.item, None)  # a new attempt starts with a full hash
        self.assertEqual(len(self.reads), 4)

    def test_file_id_change_forces_the_rehash_with_unchanged_strictness(self):
        original = self.path.read_bytes()
        with source_proofs.attempt('a'):
            same_source(self.item, None)
            self.rewrite(original, replace=True); same_source(self.item, None)  # same bytes, new identity: re-read and accepted
            self.assertEqual(len(self.reads), 2)
            self.rewrite(b'X' + original[1:], replace=True)  # same size and mtime, new identity, other bytes
            with self.assertRaisesRegex(ValidationError, 'Source changed'):same_source(self.item, None)
            self.assertEqual(len(self.reads), 3)

    def test_size_or_mtime_change_is_refused(self):
        with source_proofs.attempt('a'):
            same_source(self.item, None)
            self.rewrite(self.path.read_bytes(), keep_time=False); os.utime(self.path, ns=(1, 10**18))
            with self.assertRaisesRegex(ValidationError, 'Source changed'):same_source(self.item, None)
        with source_proofs.attempt('b'):
            os.utime(self.path, ns=(int(self.item['modified']), int(self.item['modified'])))
            same_source(self.item, None)
            with open(self.path, 'ab') as stream:stream.write(b'more')
            with self.assertRaisesRegex(ValidationError, 'Source changed'):same_source(self.item, None)

    def test_identity_moved_during_the_hash_is_not_remembered(self):
        with source_proofs.attempt('a'):
            stat = source_proofs.stat_of(self.path)
            source_proofs.remember(self.path, self.item['sha256'], stat, os.stat_result((1,) * 10))
            self.assertFalse(source_proofs.unchanged(self.path, self.item['sha256'], stat))
            source_proofs.remember(self.path, self.item['sha256'], stat); self.assertTrue(source_proofs.unchanged(self.path, self.item['sha256'], stat))
            source_proofs.forget(self.path); self.assertFalse(source_proofs.unchanged(self.path, self.item['sha256'], stat))

    def test_change_keeping_size_mtime_and_id_is_the_accepted_risk_but_still_blocks_deletion(self):
        with source_proofs.attempt('a'):
            same_source(self.item, None)
            self.rewrite(b'Y')  # in-place byte change; size, mtime and file ID unchanged
            same_source(self.item, None)  # skipped: Sergei accepted this residual risk for revision checks
            self.assertEqual(len(self.reads), 1)
            source = {'size': self.item['size'], 'modified': self.item['modified'], 'sha256': self.item['sha256']}
            with VerifiedFile(self.path) as handle, self.assertRaisesRegex(BoundaryError, 'Original bytes differ'):
                CleanupJobs._match(handle, source)  # the deletion proof always hashes in full


class WholeBookReadTests(unittest.TestCase):
    """Every book: count full source hashes through one real copy-flow conversion, with and without the cut."""
    def run_book(self, cut):
        from test_merge_service import MergeTests
        import review_backend
        harness = MergeTests('test_unreviewed_book_cannot_enqueue'); harness.setUp(); self.addCleanup(harness.tearDown)
        sources = {os.path.normcase(str(p)) for p in harness.sources}; counts = collections.Counter()
        def counter(kind, real):
            def wrapped(*args, **kwargs):
                path = args[0].path if kind == 'held' else args[0]
                if os.path.normcase(str(path)) in sources:counts[kind] += 1
                return real(*args, **kwargs)
            return wrapped
        patches = [patch('review_backend.source_hash', side_effect=counter('guard', review_backend.source_hash)),
                   patch('audio_pipeline.digest', side_effect=counter('pipeline', audio_pipeline.digest)),
                   patch.object(VerifiedFile, 'sha256', autospec=True, side_effect=counter('held', VerifiedFile.sha256))]
        if not cut:patches.append(patch('source_proofs.unchanged', return_value=False))
        with contextlib.ExitStack() as active:
            for item in patches:active.enter_context(item)
            row = harness.ready(); counts.clear()
            harness.service.create('Audiobooks', row['id'], row['revision']); status = harness.wait()
            self.assertEqual(status['completed'], 1, status)
            harness.service.close()
        self.assertEqual(harness.service.cleanup.status(status['jobs'][0]['job_id'])['state'], 'completed')
        return {kind: counts[kind] // len(sources) for kind in ('guard', 'pipeline', 'held')}

    def test_one_full_revision_hash_per_attempt_and_full_deletion_proof(self):
        before = self.run_book(cut=False); after = self.run_book(cut=True)
        # Queueing and the first attempt check still hash in full; later revision checks compare fingerprints.
        self.assertEqual(after['guard'], 2); self.assertGreater(before['guard'], after['guard'])
        self.assertEqual(after['pipeline'], 0); self.assertGreater(before['pipeline'], 0)
        # The removal decision keeps its own full hash of every original.
        self.assertGreaterEqual(after['held'], 1)
        print('Full source hashes per source, before/after the cut:', before, after)



# 0.21.3: this module's fixtures publish inside their own library; see sorted_fixture (Sergei's deletion rule).
def setUpModule():
    global _sorted_fixture
    from sorted_fixture import patch_merge_service
    _sorted_fixture = patch_merge_service()


def tearDownModule():
    _sorted_fixture.stop()

if __name__ == '__main__':
    unittest.main()
