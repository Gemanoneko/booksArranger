"""Private replacement proof fixtures; no real library, catalogue or UI access."""
import base64
import copy
import json
import array
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import threading
import unittest
import uuid
import wave

from audio_pipeline import create_private, decoded_duration, digest, fingerprint, run_owned, ValidationError
from encoding_policy import PROFILE
from quicktime_chapters import box, legacy_entry
from replacement_media import (prepare_replacement, verify_replacement, _plan,
                               _validate_receipt, _readback, _movie_accounting,
                               _milliseconds, EXPECTED_ENCODING, VERSION)

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'replacement-media-fixtures'
AREA.mkdir(parents=True, exist_ok=True)
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


def frozen_plan(sources, parentid, frames):
    tracks = []; total = 0
    for index, (source, count) in enumerate(zip(sources, frames), 1):
        start = _milliseconds(total); total += count
        tracks.append({'order': index, 'path': source['path'], 'size': source['size'], 'sha256': source['sha256'],
                       'pcm_rate': 44100, 'pcm_frames': count, 'title': f'Track {index:02}',
                       'start_ms': start, 'end_ms': _milliseconds(total)})
    return {'parent_job_id': parentid, 'source_count': 40, 'source_bytes': sum(s['size'] for s in sources),
            'source_policy': 'KEEP_ALL_40_ORIGINALS', 'encoding': {'profile': PROFILE, **EXPECTED_ENCODING},
            'pcm_rate': 44100, 'total_source_pcm_frames': total, 'total_decoded_source_seconds': total / 44100,
            'chapter_readback_tolerance_ms': 1, 'output_decoded_padding_tolerance_seconds': .25, 'tracks': tracks}


def sample_table(sizes=(11, 12, 13), uniform=0, declared=None):
    count = len(sizes) if declared is None else declared
    data = b'\0' * 4 + struct.pack('>II', uniform, count)
    return box(b'stsz', data + (b'' if uniform else b''.join(struct.pack('>I', s) for s in sizes)))


def track(handler, sample):
    header = box(b'hdlr', b'\0' * 8 + handler + b'\0' * 12)
    return box(b'trak', box(b'mdia', header + box(b'minf', box(b'stbl', sample))))


def movie(audio=None, text=None):
    audio = sample_table() if audio is None else audio
    entry = legacy_entry(struct.pack('>I4s', 16, b'text') + b'\0' * 7 + b'\1') if text is None else text
    chapter = box(b'stsd', b'\0' * 4 + struct.pack('>I', 1) + entry)
    return box(b'moov', track(b'soun', audio) + track(b'text', chapter))


class ReplacementProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.root = Path(self.temp.name)
        parentid = str(uuid.uuid4())
        sources = [{'path': str(self.root / f'{i:02}.mp3'), 'size': 100, 'modified': '1', 'sha256': 'a' * 64} for i in range(1, 41)]
        self.parent = {'state': 'completed', 'manifest': {'job_id': parentid, 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
                       'root': str(self.root), 'destination': str(self.root / 'original.m4b'), 'sources': sources,
                       'profile': 'aac-160k-stereo-44100-quicktime-v1', 'chapters': [], 'cleanup_policy': {'enabled': True},
                       'cover': {'path': str(self.root / 'cover.png'), 'sha256': 'b' * 64}, 'comments': 'Source note',
                       'metadata': {'title': 'The Eye of God', 'canonical_author': 'James Rollins', 'original_language': 'Other',
                                    'series': 'Sigma Force', 'number': '9', 'narrator': 'Андрей Леонов'}},
                       'output': {'final_path': str(self.root / 'original.m4b')}}
        self.plan = frozen_plan(sources, parentid, [44100] * 40)
        self.manifest = prepare_replacement(self.parent, str(uuid.uuid4()), self.plan)
        self.validation = {'profile': PROFILE, 'encoding': {**EXPECTED_ENCODING, 'selection': 'highest_verified_mp3_stream_bitrate', 'source_bitrates': [128000] * 40},
                           'source_pcm_rate': 44100, 'source_pcm_frames': [44100] * 40, 'expected_duration': 40., 'decoded_duration': 40.02,
                           'chapters': [{'start': t['start_ms'], 'end': t['end_ms'], 'title': t['title']} for t in self.plan['tracks']],
                           'size': 1000, 'sha256': 'c' * 64}
        tags = {'title': 'The Eye of God', 'artist': 'James Rollins', 'album_artist': 'James Rollins', 'media_type': '2', 'genre': 'Audiobook',
                'grouping': 'Sigma Force', 'album': 'Sigma Force - 9 - The Eye of God', 'track': '9', 'sort_name': 'Eye of God',
                'comment': 'Source note\nNarrator: Андрей Леонов'}
        self.raw = {'streams': [{'codec_type': 'audio', 'codec_name': 'aac', 'profile': 'LC', 'sample_rate': '44100', 'channels': 1, 'bit_rate': '127981'},
                               {'codec_type': 'video', 'codec_name': 'png', 'disposition': {'attached_pic': 1}}],
                    'format': {'duration': '40.02', 'tags': tags},
                    'chapters': [{'start_time': str(t['start_ms'] / 1000), 'end_time': str(t['end_ms'] / 1000), 'tags': {'title': t['title']}} for t in self.plan['tracks']]}

    def tearDown(self):
        self.temp.cleanup()

    def test_new_job_is_source_matched_keeps_originals_parent_and_frozen_plan(self):
        before = copy.deepcopy(self.parent); plan = copy.deepcopy(self.plan)
        result = prepare_replacement(self.parent, str(uuid.uuid4()), self.plan)
        self.assertEqual(self.parent, before); self.assertEqual(self.plan, plan)
        self.assertEqual(result['profile'], PROFILE); self.assertNotIn('cleanup_policy', result)
        self.assertEqual(Path(result['destination']).name, 'original - Final.m4b')
        self.assertEqual(result['chapters'], [f'Track {i:02}' for i in range(1, 41)])
        self.assertEqual(result['replacement_parent_job_id'], self.parent['manifest']['job_id'])
        result['sources'][0]['size'] = 99; self.assertEqual(self.parent['manifest']['sources'][0]['size'], 100)

    def test_parent_identity_state_and_published_path_must_agree(self):
        for field, value in [('state', 'running'), ('output', {'final_path': str(self.root / 'other.m4b')})]:
            changed = copy.deepcopy(self.parent); changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):prepare_replacement(changed, str(uuid.uuid4()), self.plan)
        with self.assertRaises(ValidationError):prepare_replacement(self.parent, self.parent['manifest']['job_id'], self.plan)

    def test_reordered_partial_or_duplicate_source_set_cannot_rebuild(self):
        for mutate in (lambda s: s.reverse(), lambda s: s.pop(), lambda s: s.__setitem__(1, copy.deepcopy(s[0]))):
            changed = copy.deepcopy(self.parent); mutate(changed['manifest']['sources'])
            with self.subTest(mutate=mutate), self.assertRaises(ValidationError):prepare_replacement(changed, str(uuid.uuid4()), self.plan)

    def test_aac_inputs_and_changed_original_byte_proofs_are_refused(self):
        for key, value in [('path', str(self.root / 'old.m4b')), ('sha256', 'd' * 64), ('size', 101), ('size', True)]:
            changed = copy.deepcopy(self.parent); changed['manifest']['sources'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValidationError):prepare_replacement(changed, str(uuid.uuid4()), self.plan)

    def test_saved_pcm_track_membership_endpoints_names_and_totals_cannot_change(self):
        changes = [('pcm_frames', 44101), ('pcm_rate', 48000), ('title', 'Invented literary chapter'), ('start_ms', 1), ('end_ms', 999), ('order', 2)]
        for key, value in changes:
            changed = copy.deepcopy(self.plan); changed['tracks'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):_plan(self.parent['manifest']['sources'], changed)
        changed = copy.deepcopy(self.plan); changed['total_source_pcm_frames'] += 1
        with self.assertRaises(ValidationError):_plan(self.parent['manifest']['sources'], changed)

    def test_profile_upmix_quality_reduction_and_original_cleanup_are_refused(self):
        for changed in (dict(self.manifest, profile=self.parent['manifest']['profile']), dict(self.manifest, cleanup_policy={'enabled': True})):
            with self.assertRaises(ValidationError):_validate_receipt(changed, self.validation)
        for key, value in [('bitrate', 160000), ('bitrate', 96000), ('channels', 2), ('sample_rate', 48000), ('mode', 'copy')]:
            changed = copy.deepcopy(self.validation); changed['encoding'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValidationError):_validate_receipt(self.manifest, changed)

    def test_fresh_frames_must_match_and_quarter_second_padding_is_the_bound(self):
        good = copy.deepcopy(self.validation); good['decoded_duration'] = 40.25
        _validate_receipt(self.manifest, good)
        for mutate in (lambda v: v['source_pcm_frames'].__setitem__(0, 44101), lambda v: v.__setitem__('decoded_duration', 40.251), lambda v: v.__setitem__('decoded_duration', float('nan'))):
            bad = copy.deepcopy(self.validation); mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(ValidationError):_validate_receipt(self.manifest, bad)

    def test_actual_readback_reports_bitrate_without_inventing_lossless_or_byte_cap(self):
        tracks, _ = _validate_receipt(self.manifest, self.validation)
        actual = _readback(self.manifest, self.raw, tracks, 40.)
        self.assertEqual(actual['actual_audio']['bit_rate'], '127981')
        self.assertEqual(len(actual['actual_chapters']), 40)

    def test_actual_codec_channel_sample_rate_and_stream_membership_are_checked(self):
        for key, value in [('codec_name', 'mp3'), ('channels', 2), ('sample_rate', '48000'), ('profile', 'HE-AAC')]:
            bad = copy.deepcopy(self.raw); bad['streams'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):_readback(self.manifest, bad, self.plan['tracks'], 40.)
        bad = copy.deepcopy(self.raw); bad['streams'].append(copy.deepcopy(bad['streams'][0]))
        with self.assertRaises(ValidationError):_readback(self.manifest, bad, self.plan['tracks'], 40.)

    def test_actual_tags_narrator_and_cover_membership_are_required(self):
        for key in ('title', 'artist', 'album_artist', 'grouping', 'track', 'sort_name', 'comment'):
            bad = copy.deepcopy(self.raw); bad['format']['tags'].pop(key)
            with self.subTest(key=key), self.assertRaises(ValidationError):_readback(self.manifest, bad, self.plan['tracks'], 40.)
        bad = copy.deepcopy(self.raw); bad['streams'].pop()
        with self.assertRaises(ValidationError):_readback(self.manifest, bad, self.plan['tracks'], 40.)
        # Narration language uses the existing explicit edition comment, not the
        # original-work language or a fabricated MP4 audio language tag.
        explicit = copy.deepcopy(self.manifest); explicit['metadata']['edition_language'] = 'Russian'
        with self.assertRaisesRegex(ValidationError, 'recording-language'):_readback(explicit, self.raw, self.plan['tracks'], 40.)
        tagged = copy.deepcopy(self.raw); tagged['format']['tags']['comment'] += '\nRecording language: Russian'
        result = _readback(explicit, tagged, self.plan['tracks'], 40.)
        self.assertEqual(result['recording_language_comment_lines'], ['Recording language: Russian'])
        conflict = copy.deepcopy(tagged); conflict['format']['tags']['comment'] += '\nRecording language: English'
        with self.assertRaisesRegex(ValidationError, 'recording-language'):_readback(explicit, conflict, self.plan['tracks'], 40.)
        self.assertEqual(_readback(self.manifest, self.raw, self.plan['tracks'], 40.)['recording_language_comment_lines'], [])

    def test_actual_chapters_check_one_millisecond_names_order_and_count(self):
        good = copy.deepcopy(self.raw); good['chapters'][0]['end_time'] = '1.001'
        _readback(self.manifest, good, self.plan['tracks'], 40.)
        for mutate in (lambda r: r['chapters'].pop(), lambda r: r['chapters'].reverse(), lambda r: r['chapters'][0].__setitem__('end_time', '1.002'), lambda r: r['chapters'][0].__setitem__('start_time', 'NaN')):
            bad = copy.deepcopy(self.raw); mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(ValidationError):_readback(self.manifest, bad, self.plan['tracks'], 40.)

    def test_actual_quicktime_text_layout_and_payload_accounting(self):
        result = _movie_accounting(movie(), 1000, 800)
        self.assertEqual((result['audio_payload_bytes'], result['nonaudio_bytes']), (36, 964))
        self.assertEqual(result['chapter_description']['entry_size'], 65)
        self.assertEqual(_movie_accounting(movie(sample_table(uniform=7)), 1000, 800)['audio_payload_bytes'], 21)

    def test_audio_sample_tables_reject_truncation_zero_count_and_excess_payload(self):
        for table in (sample_table(declared=4), sample_table(sizes=()), sample_table(sizes=(0, 2)), sample_table(uniform=999)):
            with self.subTest(table=table), self.assertRaises(ValidationError):_movie_accounting(movie(table), 1000, 800)

    def test_legacy_text_and_duplicate_audio_tracks_are_refused(self):
        old = struct.pack('>I4s', 59, b'text') + b'\0' * 51
        with self.assertRaises(ValueError):_movie_accounting(movie(text=old), 1000, 800)
        duplicate = box(b'moov', movie()[8:] + track(b'soun', sample_table()))
        with self.assertRaises(ValidationError):_movie_accounting(duplicate, 1000, 800)


class ActualFortySourceReplacementTests(unittest.TestCase):
    def windows(self, frozen):
        result = []; offset = 0
        for track in frozen['tracks']:
            center = offset + track['pcm_frames'] // 2
            result.append((center - 2205, center + 2205))  # 100ms interior landmarks.
            offset += track['pcm_frames']
        return result

    def assert_presentation_order(self, pcm, frozen, frequencies):
        samples = array.array('h'); samples.frombytes(pcm)
        self.assertGreaterEqual(len(samples), frozen['total_source_pcm_frames'] - 11025)
        self.assertLessEqual(len(samples), frozen['total_source_pcm_frames'] + 11025)
        for index, ((start, end), frequency) in enumerate(zip(self.windows(frozen), frequencies), 1):
            segment = samples[start:end]
            self.assertEqual(len(segment), 4410)
            self.assertGreater(max(abs(value) for value in segment), 500, f'Track {index} became silence')
            crossings = sum(before <= 0 < after for before, after in zip(segment, segment[1:]))
            observed = crossings * 44100 / len(segment)
            self.assertLessEqual(abs(observed - frequency), 20, f'Track {index} presentation was replaced or reordered: {observed} vs {frequency}')

    def test_one_source_matched_encode_with_forty_correct_chapters_and_substitution_guard(self):
        with tempfile.TemporaryDirectory(dir=AREA) as name:
            root = Path(name); stop = threading.Event(); sources = []; frames = []; frequencies = []
            for index in range(1, 41):
                # Every source has independently encoded distinct content AND
                # duration. A duplicate/order bug cannot pass by preserving totals.
                frequency = 200 + index * 51; frequencies.append(frequency)
                source_wave = root / f'{index:02}.wav'; count = (index + 8) * 1152
                samples = array.array('h', (round(12000 * math.sin(2 * math.pi * frequency * n / 44100)) for n in range(count)))
                with wave.open(str(source_wave), 'wb') as wav:
                    wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(44100); wav.writeframes(samples.tobytes())
                source = root / f'{index:02}.mp3'
                subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-f', 'wav', '-i', str(source_wave),
                                '-ar', '44100', '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '128000', '-write_xing', '0', str(source)],
                               check=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                frames.append(round(decoded_duration(source, root, stop, count / 44100) * 44100))
                sources.append({'path': str(source), **fingerprint(source), 'sha256': digest(source)})
            cover = root / 'cover.png'; cover.write_bytes(PNG); parentid = str(uuid.uuid4())
            parent = {'state': 'completed', 'manifest': {'job_id': parentid, 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
                      'root': str(root), 'destination': str(root / 'parent.m4b'), 'sources': sources, 'profile': 'aac-160k-stereo-44100-quicktime-v1',
                      'cover': {'path': str(cover), 'sha256': digest(cover)}, 'comments': '', 'metadata': {'title': 'The Eye of God', 'canonical_author': 'James Rollins',
                      'original_language': 'Other', 'edition_language': 'Russian', 'series': 'Sigma Force', 'number': '9', 'narrator': 'Private Reader'}}, 'output': {'final_path': str(root / 'parent.m4b')}}
            self.assertEqual(len(set(frames)), 40)
            frozen = frozen_plan(sources, parentid, frames)
            manifest = prepare_replacement(parent, str(uuid.uuid4()), frozen)
            output, validation = create_private(manifest, root / 'private-stage', stop)
            checked = verify_replacement(manifest, validation, output, output.parent, stop)
            proof = checked['replacement_media']
            self.assertEqual((checked['encoding']['bitrate'], checked['encoding']['channels'], checked['encoding']['sample_rate']), (128000, 1, 44100))
            self.assertEqual(len(proof['actual_chapters']), 40); self.assertEqual(proof['chapter_description']['entry_size'], 65)
            self.assertEqual(proof['audio_payload_bytes'] + proof['nonaudio_bytes'], checked['size'])
            self.assertEqual(proof['cover_sha256'], manifest['cover']['sha256'])
            self.assertEqual(proof['recording_language_comment_lines'], ['Recording language: Russian'])
            self.assertEqual(proof['source_policy'], 'KEEP_ALL_40_ORIGINALS'); self.assertNotIn('cleanup_policy', manifest)
            self.assertTrue(all(digest(source['path']) == source['sha256'] for source in sources))
            self.assertFalse(Path(manifest['destination']).exists())
            # Decode the ONE AAC result at its actual native rate/channel. These
            # private tone landmarks check ordering/content without claiming that
            # arbitrary lossy speech/music is perceptually or bit-identically equal.
            pcm = run_owned([shutil.which('ffmpeg'), '-v', 'error', '-xerror', '-nostdin', '-protocol_whitelist', 'file', '-f', 'mov', '-i', str(output),
                             '-map', '0:a:0', '-ar', '44100', '-ac', '1', '-c:a', 'pcm_s16le', '-f', 's16le', 'pipe:1'],
                            output.parent, stop, 60, max_output=8 * 1024 * 1024)
            self.assert_presentation_order(pcm, frozen, frequencies)
            window = self.windows(frozen); first = slice(window[0][0] * 2, window[0][1] * 2); last = slice(window[-1][0] * 2, window[-1][1] * 2)
            swapped = bytearray(pcm); swapped[first], swapped[last] = pcm[last], pcm[first]
            with self.assertRaises(AssertionError):self.assert_presentation_order(bytes(swapped), frozen, frequencies)
            duplicated = bytearray(pcm); duplicated[first] = pcm[last]
            with self.assertRaises(AssertionError):self.assert_presentation_order(bytes(duplicated), frozen, frequencies)
            missing = bytearray(pcm); missing[first] = b'\0' * (window[0][1] - window[0][0]) * 2
            with self.assertRaises(AssertionError):self.assert_presentation_order(bytes(missing), frozen, frequencies)
            with output.open('r+b') as stream:
                stream.seek(-1, 2); original = stream.read(1); stream.seek(-1, 2); stream.write(bytes([original[0] ^ 1]))
            with self.assertRaisesRegex(ValidationError, 'bytes changed'):verify_replacement(manifest, validation, output, output.parent, stop)


if __name__ == '__main__':
    unittest.main()
