import copy
import unittest
from recording_classification import classify_recording, destination_suffix


def book(identifier='candidate', **changes):
    value = {'id': identifier, 'identity_verified': True, 'work_ids': ['work-1'],
             'collection_kind': 'single', 'series_volume': None,
             'recording_language': {'value': 'ru', 'verified': True},
             'narrator': {'value': 'Narrator A', 'verified': True},
             'edition': {'value': 'Fan edition', 'verified': True},
             'manifest': {'complete': True, 'observed_count': 1,
                          'tracks': [{'source_sha256': 'a'*64, 'size_bytes': 100,
                                      'packet_sha256': 'b'*64, 'chapter_sha256': 'c'*64}]},
             'approved': True, 'completed_verified': True, 'current_output_valid': True}
    value.update(changes)
    return value


class RecordingTests(unittest.TestCase):
    def test_new_verified_recording(self):
        result = classify_recording(book(), [])
        self.assertEqual(result['classification'], 'new')
        self.assertFalse(result['hold'])

    def test_identical_completed_current_output_can_reuse(self):
        result = classify_recording(book(), [book('previous')])
        self.assertEqual(result['reuse_job_id'], 'previous')
        self.assertEqual(result['duplicate_review']['state'], 'verified_identical')
        self.assertFalse(result['hold'])

    def test_unfinished_unapproved_or_stale_output_cannot_reuse(self):
        for field in ('approved', 'completed_verified', 'current_output_valid'):
            with self.subTest(field=field):
                result = classify_recording(book(), [book('previous', **{field: False})])
                self.assertIsNone(result['reuse_job_id'])
                self.assertTrue(result['hold'])

    def test_encoded_packet_difference_is_not_distinct_proof(self):
        previous = book('previous')
        previous['manifest']['tracks'][0].update(source_sha256='d'*64, packet_sha256='e'*64)
        self.assertEqual(classify_recording(book(), [previous])['classification'], 'possible')

    def test_verified_different_narrator_retained_and_marked(self):
        previous = book('previous', narrator={'value': 'Narrator B', 'verified': True})
        previous['manifest']['tracks'][0].update(source_sha256='d'*64, packet_sha256='e'*64)
        result = classify_recording(book(), [previous])
        self.assertEqual(result['classification'], 'related_distinct')
        self.assertTrue(result['review_required'])
        self.assertFalse(result['hold'])
        self.assertIsNone(result['reuse_job_id'])

    def test_identical_content_conflicting_credits_is_held(self):
        previous = book('previous', narrator={'value': 'Narrator B', 'verified': True})
        self.assertTrue(classify_recording(book(), [previous])['hold'])

    def test_unverified_narrator_cannot_prove_distinct(self):
        previous = book('previous', narrator={'value': 'Narrator B', 'verified': False})
        previous['manifest']['tracks'][0].update(source_sha256='d'*64, packet_sha256='e'*64)
        self.assertEqual(classify_recording(book(), [previous])['classification'], 'possible')

    def test_packets_and_chapters_without_full_bytes_cannot_prove_identity(self):
        previous = book('previous')
        previous['manifest']['tracks'][0]['source_sha256'] = 'd'*64
        result = classify_recording(book(), [previous])
        self.assertIsNone(result['reuse_job_id'])
        self.assertEqual(result['classification'], 'possible')
        self.assertTrue(result['hold'])

    def test_missing_chapter_proof_blocks_reuse_even_same_source(self):
        previous = book('previous')
        del previous['manifest']['tracks'][0]['chapter_sha256']
        self.assertTrue(classify_recording(book(), [previous])['hold'])

    def test_incomplete_or_inconsistent_manifest_is_held(self):
        for change in ({'complete': False}, {'observed_count': 2}, {'observed_count': True}):
            candidate = book()
            candidate['manifest'].update(change)
            self.assertTrue(classify_recording(candidate, [])['hold'])

    def test_same_title_different_verified_work_not_duplicate(self):
        candidate = book(title='Same title')
        previous = book('previous', title='Same title', work_ids=['work-2'])
        self.assertEqual(classify_recording(candidate, [previous])['classification'], 'new')

    def test_collection_not_reused_as_constituent(self):
        candidate = book(collection_kind='fan_assembly', work_ids=['work-1', 'work-2'])
        self.assertEqual(classify_recording(candidate, [book('previous')])['classification'], 'new')

    def test_component_order_and_unknown_volume_hold(self):
        candidate = book(collection_kind='fan_assembly', work_ids=['work-1', 'work-2'])
        previous = book('previous', collection_kind='fan_assembly', work_ids=['work-2', 'work-1'])
        self.assertTrue(classify_recording(candidate, [previous])['hold'])
        self.assertTrue(classify_recording(book(), [book('previous', series_volume='1')])['hold'])

    def test_verified_different_volume_not_same_book(self):
        self.assertEqual(classify_recording(book(series_volume='1'),
                         [book('previous', series_volume='2')])['classification'], 'new')

    def test_ambiguous_relationship_overrides_reusable_job(self):
        previous = book('uncertain')
        previous['manifest']['tracks'][0].update(source_sha256='d'*64, packet_sha256='e'*64)
        result = classify_recording(book(), [book('completed'), previous])
        self.assertTrue(result['hold'])
        self.assertIsNone(result['reuse_job_id'])
        self.assertEqual(result['duplicate_review']['related_ids'], ['completed', 'uncertain'])

    def test_suffix_safe_deterministic_and_verified_only(self):
        candidate = book(narrator={'value': '../Unsafe:Name?', 'verified': True})
        suffix = destination_suffix(candidate)
        self.assertEqual(suffix, destination_suffix(copy.deepcopy(candidate)))
        self.assertFalse(any(char in suffix for char in '<>:"/\\|?*'))
        candidate['narrator']['verified'] = False
        self.assertNotIn('Unsafe', destination_suffix(candidate))

    def test_missing_or_invalid_candidate_fingerprints_hold(self):
        for change in ({'chapter_sha256': None}, {'source_sha256': 'invalid', 'packet_sha256': None}):
            candidate = book()
            candidate['manifest']['tracks'][0].update(change)
            self.assertTrue(classify_recording(candidate, [])['hold'])

    def test_same_packets_changed_decoder_or_timing_never_reused(self):
        for field, values in (('codec', ('aac', 'mp3')),
                              ('extradata_sha256', ('d'*64, 'e'*64)),
                              ('sample_rate', (44100, 48000)),
                              ('channel_layout', ('mono', 'stereo')),
                              ('timebase', ('1/44100', '1/48000')),
                              ('priming', (0, 1024)),
                              ('edit_list', ([], [1024])),
                              ('start', (0, 1)),
                              ('duration', (100, 99)),
                              ('packet_timing', ([0, 1], [1, 2]))):
            with self.subTest(field=field):
                candidate, previous = book(), book('previous')
                candidate['manifest']['tracks'][0][field] = values[0]
                previous['manifest']['tracks'][0][field] = values[1]
                previous['manifest']['tracks'][0]['source_sha256'] = 'f'*64
                result = classify_recording(candidate, [previous])
                self.assertIsNone(result['reuse_job_id'])
                self.assertTrue(result['hold'])
                self.assertEqual(result['duplicate_review']['state'], 'possible')

    def test_packets_only_even_claimed_complete_interpretation_is_held(self):
        candidate, previous = book(), book('previous')
        for value in (candidate, previous):
            del value['manifest']['tracks'][0]['source_sha256']
            value['manifest']['tracks'][0]['interpretation_complete'] = True
            value['manifest']['tracks'][0]['decoder_presentation_sha256'] = 'd'*64
        self.assertTrue(classify_recording(candidate, [previous])['hold'])

    def test_no_mutation(self):
        candidate, existing = book(), [book('previous')]
        before = copy.deepcopy((candidate, existing))
        classify_recording(candidate, existing)
        self.assertEqual((candidate, existing), before)


if __name__ == '__main__':
    unittest.main()
