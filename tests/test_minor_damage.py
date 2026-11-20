"""Sergei's ruling on damaged audio (2026-11-20, Futaba 0.30.0 slice D follow-up 4): "If a file plays through with only a short
glitch, the app should publish it as a good file. You can add that it has minor damage."

A short glitch (audio_pipeline.play_through): after the strict full decode failed, FFmpeg's ordinary decode plays the file to its
end, at most MINOR_LOST_SECONDS (1.0 s) of audio are missing in all, and no digital silence longer than MINOR_SILENCE_SECONDS (5 s)
follows the first damaged frame. One rule for every path: a single file edited in place or copied (a manual conversion takes the
copy flow), and the parts of a Join. Below the threshold the book publishes with a minor-damage note; above it, or when the file
does not play through, the book stops with its decode failure ("Need to reacquire"). Real FFmpeg-made private media."""
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

import audio_pipeline as pipeline

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'minor-damage'
FFMPEG = shutil.which('ffmpeg')
HIDE = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def book(path, seconds=20, chapters=None, work=None):
    """An AAC .m4b of `seconds` of a tone over quiet noise, 64 kbps stereo (an audiobook's usual rate), optional chapters."""
    path.parent.mkdir(parents=True, exist_ok=True)
    extra, maps = [], ['-map_chapters', '-1']
    if chapters:
        meta = Path(work) / (uuid.uuid4().hex + '.txt'); meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(';FFMETADATA1\n' + ''.join(f'[CHAPTER]\nTIMEBASE=1/1000\nSTART={a}\nEND={b}\ntitle={t}\n' for a, b, t in chapters), encoding='utf-8')
        extra, maps = ['-f', 'ffmetadata', '-i', str(meta)], ['-map_chapters', '2']
    subprocess.run([FFMPEG, '-hide_banner', '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i', f'sine=frequency=440:sample_rate=44100:duration={seconds}',
                    '-f', 'lavfi', '-i', f'anoisesrc=color=pink:amplitude=0.02:sample_rate=44100:duration={seconds}', *extra,
                    '-filter_complex', '[0][1]amix=inputs=2:normalize=0,volume=0.5', *maps, '-ac', '2', '-c:a', 'aac', '-b:a', '64k',
                    '-movflags', '+faststart+disable_chpl', str(path)], check=True, timeout=60, creationflags=HIDE)
    return path


def damage(path, size):
    """`size` random bytes over the middle of the audio data, as a bad disk block or a broken download would leave them."""
    data = bytearray(path.read_bytes()); at = 0
    while at < len(data):
        box = int.from_bytes(data[at:at + 4], 'big'); kind = bytes(data[at + 4:at + 8])
        if kind == b'mdat':break
        at += box
    start = at + 8; middle = start + (at + box - start) // 2
    random.seed(size); data[middle:middle + size] = bytes(random.getrandbits(8) for _ in range(size))
    path.write_bytes(bytes(data))


@unittest.skipUnless(os.name == 'nt' and FFMPEG and shutil.which('ffprobe'), 'Windows and FFmpeg required')
class MinorDamageTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.stop = threading.Event()

    def cover(self):
        cover = self.root / 'cover.png'
        if not cover.exists():
            subprocess.run([FFMPEG, '-hide_banner', '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i', 'color=c=blue:s=32x32:d=0.04', '-frames:v', '1', str(cover)],
                           check=True, timeout=30, creationflags=HIDE)
        return {'path': str(cover), 'sha256': pipeline.digest(cover), 'id': 'cover'}

    def manifest(self, paths, part_chapters=None):
        from encoding_policy import AUTOMATIC_PROFILE, freeze_automatic_policy
        sources = [{'path': str(p), 'sha256': pipeline.digest(p), **pipeline.fingerprint(p), 'metadata': {'tags': {}}} for p in paths]
        value = {'job_id': str(uuid.uuid4()), 'attempt_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
                 'root': str(self.root / 'library'), 'output_root': str(self.root), 'destination': str(self.root / 'Sorted' / 'Writer' / 'Book.m4b'),
                 'profile': AUTOMATIC_PROFILE, 'encoding_policy': freeze_automatic_policy(sources), 'sources': sources, 'cover': self.cover(),
                 'comments': '', 'chapters': [], 'metadata': {'title': 'Книга', 'canonical_author': 'Автор Тест'},
                 'cleanup_policy': {'enabled': True, 'empty_source_folders': True, 'recovery_retention_hours': 24, 'recovery_root': str(self.root / 'recovery')}}
        if len(paths) == 1:
            value['source_chapters'] = pipeline.source_chapters(Path(paths[0]), self.root, self.stop, float(pipeline.probe(Path(paths[0]), self.root, self.stop)['format']['duration']))
        elif part_chapters is not None:
            value['part_chapters'] = part_chapters
        return value

    def test_measured_glitches_classify_on_both_sides_of_the_threshold(self):
        expected = 20.0
        small = book(self.root / 'library' / 'small.m4b'); damage(small, 1024)
        large = book(self.root / 'library' / 'large.m4b'); damage(large, 16 * 1024)
        for path, minor in ((small, True), (large, False)):
            with self.assertRaises(pipeline.ValidationError) as caught:
                pipeline.decoded_duration(path, self.root, self.stop, expected)  # the strict check fails on both
            found = pipeline.play_through(path, self.root, self.stop, float(pipeline.probe(path, self.root, self.stop)['format']['duration']), caught.exception)
            self.assertEqual(found is not None, minor, (path.name, found))
            if found:
                self.assertLessEqual(found['lost_seconds'], pipeline.MINOR_LOST_SECONDS); self.assertGreater(found['lost_seconds'], 0)
                self.assertAlmostEqual(found['glitch_at_seconds'], expected / 2, delta=1.5, msg='the glitch is where the bytes were damaged')
                self.assertLess(found['longest_silence_seconds'], 1)

    def test_a_decoder_that_goes_silent_after_the_glitch_does_not_play_through(self):
        # The 256 KB case measured on a 10-minute book: the decoder outputs digital silence to the end. Simulated here at the
        # ordinary decode's output: 12 s of audio, a glitch at 2 s, then 6 s of exact zeros.
        audio = bytes([1, 0, 1, 0]) * 44100
        def silent_after(arguments, directory, stop, deadline, max_output=0, telemetry=None, diagnostic=None):
            for second in range(12):telemetry.feed(audio if second < 6 else bytes(len(audio)))
            if diagnostic:diagnostic(None, b'', b'error\n')
            return b''
        failure = pipeline.ValidationError('Full audio decode failed: x'); failure.media_decode_failed = True; failure.decoded_seconds = 2.0
        with patch.object(pipeline, 'run_owned', side_effect=silent_after):
            self.assertIsNone(pipeline.play_through(self.root / 'x.m4b', self.root, self.stop, 12.0, failure))
        tracker = pipeline._PlayThrough(4 * 44100)
        for block in (audio, bytes(1000), audio[:400] + bytes(44100 * 4), audio):tracker.feed(block)
        self.assertAlmostEqual(tracker.longest / 4 / 44100, 1.0, delta=.01)

    def test_a_single_file_with_a_short_glitch_publishes_with_its_note(self):
        source = book(self.root / 'library' / 'Книга.m4b'); damage(source, 1024); before = source.read_bytes()
        output, validation = pipeline.create_private(self.manifest([source]), self.root / 'stage', self.stop)  # the copy flow (and manual)
        self.assertEqual(source.read_bytes(), before)
        [note] = validation['minor_audio_damage']
        self.assertEqual((note['file'], note['source_index']), (source.name, 0)); self.assertLessEqual(note['lost_seconds'], 1)
        self.assertNotIn('damage_repair', validation)

    def test_a_single_file_over_the_threshold_stops_for_reacquire(self):
        source = book(self.root / 'library' / 'Книга.m4b'); damage(source, 16 * 1024)
        with self.assertRaises(pipeline.SourceDecodeError):
            pipeline.create_private(self.manifest([source]), self.root / 'stage', self.stop)

    def test_the_in_place_edit_decodes_first_and_applies_the_same_rule(self):
        import inplace_m4b
        database = str(self.root / 'catalog.sqlite3')
        def run(path):
            manifest = self.manifest([path])
            return pipeline.create_private(manifest, self.root / ('stage-' + path.stem), self.stop, in_place=inplace_m4b.Session(database, manifest['job_id'], manifest['attempt_id']))
        def edit(path):
            edited, validation = run(path)
            if isinstance(edited, inplace_m4b.Edited):  # put the original back whatever the assertions below say
                self.addCleanup(edited.close); self.addCleanup(edited.undo)
            return edited, validation
        small = book(self.root / 'library' / 'small.m4b'); damage(small, 1024)
        edited, validation = edit(small)  # positive control: before, published as good with no decode and no note
        self.assertIsInstance(edited, inplace_m4b.Edited)
        self.assertTrue(validation['in_place']['decoded'])
        self.assertEqual([item['file'] for item in validation.get('minor_audio_damage', [])], ['small.m4b'])
        large = book(self.root / 'library' / 'large.m4b'); damage(large, 16 * 1024); before = large.read_bytes()
        with self.assertRaises(pipeline.SourceDecodeError):  # positive control: before, edited in place and published as good
            edit(large)
        self.assertEqual(large.read_bytes(), before, 'never written')
        clean = book(self.root / 'library' / 'clean.m4b')
        edited, validation = edit(clean)
        self.assertTrue(validation['in_place']['decoded']); self.assertNotIn('minor_audio_damage', validation)

    def test_a_join_part_with_a_short_glitch_joins_with_its_note(self):
        chapters = [(0, 4000, 'First'), (4000, 10000, 'Last')]
        first = book(self.root / 'library' / '1.m4b', 10, chapters, self.root / 'work')
        second = book(self.root / 'library' / '2.m4b', 10, chapters, self.root / 'work'); damage(second, 1024)
        plans = [{'name': str(i), 'chapters': pipeline.part_chapter_plan(p, self.root, self.stop, float(pipeline.probe(p, self.root, self.stop)['format']['duration']))['chapters']}
                 for i, p in enumerate((first, second))]
        output, validation = pipeline.create_private(self.manifest([first, second], plans), self.root / 'stage', self.stop)
        self.assertEqual([item['file'] for item in validation['minor_audio_damage']], ['2.m4b'])
        self.assertEqual([c['title'] for c in validation['chapters']], ['First', 'Last', 'First', 'Last'])
        pipeline.decoded_duration(output, self.root, self.stop, 20)  # the joined output itself decodes strictly: the glitch is skipped
        bad = book(self.root / 'library' / '3.m4b', 10, chapters, self.root / 'work'); damage(bad, 16 * 1024)
        plans[1] = {'name': '1', 'chapters': pipeline.part_chapter_plan(bad, self.root, self.stop, float(pipeline.probe(bad, self.root, self.stop)['format']['duration']))['chapters']}
        with self.assertRaises(pipeline.SourceDecodeError):
            pipeline.create_private(self.manifest([first, bad], plans), self.root / 'stage-bad', self.stop)


if __name__ == '__main__':
    unittest.main()
