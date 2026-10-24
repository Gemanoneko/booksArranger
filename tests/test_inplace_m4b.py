"""0.21.0 single-M4B in-place metadata edit: eligible path, fallbacks, crash recovery, audio-untouched proof.

Real AAC/ALAC fixtures through the installed FFmpeg; no decode is part of the edited path.
"""
import ast, base64, contextlib, copy, hashlib, importlib, inspect, json, os, shutil, sqlite3, stat, struct, subprocess, sys, tempfile, threading, time, unittest, uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import audio_pipeline as ap
import inplace_m4b
import m4b_preservation as mp
import m4b_repair
import native_io
import zone_identifier
from audio_pipeline import create_private, digest, fingerprint, run_owned, source_chapters, ValidationError
from encoding_policy import AUTOMATIC_PROFILE, freeze_automatic_policy
from native_io import BoundaryError, VerifiedFile

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'inplace-m4b-tests'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
CHAPTERS = ';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=700\ntitle=First\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=700\nEND=1500\ntitle=Second\n'
MARKER = b'[ZoneTransfer]\r\nZoneId=3\r\nHostUrl=https://example.invalid/book.m4b\r\n'
# Child process for a real kill: edit in place, publish, and park right after the OS rename, before its receipt is journaled.
KILLED_AFTER_RENAME = r'''
import contextlib, json, sys, threading, time
sys.path[:0] = [sys.argv[1], sys.argv[2]]
from types import SimpleNamespace
from unittest.mock import patch
import inplace_m4b, native_io
from audio_pipeline import create_private
from merge_service import MergeService
manifest = json.loads(open(sys.argv[3], encoding='utf-8').read()); real = native_io.rename_no_replace
def park(*args, **kwargs):
    real(*args, **kwargs); print('RENAMED', flush=True); time.sleep(300)
edited, validation = create_private(manifest, sys.argv[5], threading.Event(), in_place=inplace_m4b.Session(sys.argv[4], manifest['job_id'], manifest['attempt_id']))
fake = SimpleNamespace(_held_sources={}, _review_boundary=contextlib.nullcontext, _guard=lambda manifest: True, _register=lambda *args: None)
with patch('native_io.rename_no_replace', side_effect=park):
    MergeService._publish_in_place(fake, manifest, edited, validation, lambda *args: None)
print('NOT KILLED', flush=True)
'''


class Crash(BaseException):
    """A process death at a named step: no in-process handler runs."""


def published(fake, manifest, edited, validation, checkpoint):
    from merge_service import MergeService
    return MergeService._publish_in_place(fake, manifest, edited, validation, checkpoint)


class Fixture(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup); self.database = str(self.root / 'catalog.sqlite3'); self.stop = threading.Event()

    def media(self, name='Book.m4b', codec='aac', cover=False, chapters=True, folder=None):
        plain = self.root / ('plain-' + name); path = Path(folder or self.root / 'Unsorted') / name; path.parent.mkdir(parents=True, exist_ok=True)
        run_owned([shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1.5',
                   '-ar', '44100', '-ac', '1', '-c:a', codec, '-metadata', 'title=Old title', str(plain)], self.root, self.stop, 30)
        extra = []
        if chapters:
            (self.root / 'chapters.txt').write_text(CHAPTERS, encoding='utf8'); extra += ['-f', 'ffmetadata', '-i', str(self.root / 'chapters.txt')]
        if cover:
            (self.root / 'old.png').write_bytes(PNG); extra += ['-i', str(self.root / 'old.png')]
        args = [shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-i', str(plain), *extra, '-map', '0:a:0']
        if cover:args += ['-map', str(2 if chapters else 1) + ':v:0', '-c:v', 'png', '-disposition:v:0', 'attached_pic']
        args += ['-map_chapters', '1' if chapters else '-1', '-c:a', 'copy', str(path)]
        run_owned(args, self.root, self.stop, 30)
        return path

    def manifest(self, path, destination=None, root=None):
        cover = self.root / 'approved.png'
        if not cover.exists():cover.write_bytes(PNG)
        sources = [{'path': str(path), **fingerprint(path), 'sha256': digest(path), 'metadata': {'tags': {}}}]
        return {'job_id': str(uuid.uuid4()), 'attempt_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
                'root': str(root or self.root), 'output_root': str(self.root),
                'destination': str(destination or self.root / 'Sorted' / 'Writer John' / (path.stem + ' - John Writer.m4b')),
                'profile': AUTOMATIC_PROFILE, 'encoding_policy': freeze_automatic_policy(sources), 'sources': sources,
                'cover': {'path': str(cover), 'sha256': digest(cover), 'id': 'cover'}, 'comments': 'Original comment', 'chapters': [],
                'cleanup_policy': {'enabled': True, 'empty_source_folders': True, 'recovery_retention_hours': 24, 'recovery_root': str(self.root / 'recovery')},
                'source_chapters': source_chapters(path, self.root, self.stop, 1.5),
                'metadata': {'title': 'The Book', 'canonical_author': 'John Writer', 'series': 'Saga', 'number': '2'}}

    def session(self, manifest):
        return inplace_m4b.Session(self.database, manifest['job_id'], manifest['attempt_id'])

    def rows(self):
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.row_factory = sqlite3.Row; inplace_m4b.ensure(db)
            return [dict(r) for r in db.execute('SELECT * FROM inplace_edits')]

    def snapshot(self, path):
        return Path(path).read_bytes(), os.stat(path).st_mtime_ns

    def stage(self, name):
        stage = self.root / ('stage-' + name); stage.mkdir(); return stage

    def mark(self, path, raw=MARKER):
        """A browser's download marker on the file (it moves the file's write time, so call it before any snapshot)."""
        with open(str(path) + ':Zone.Identifier', 'wb') as stream:stream.write(raw)

    def exact(self, path):
        """Everything an undo must give back: the bytes, the ns write time, and the download marker (None: no marker)."""
        names = [name for name, _ in zone_identifier.streams(path)]; marker = None
        self.assertLessEqual(set(names), {'::$DATA', zone_identifier.MARKER})
        if zone_identifier.MARKER in names:
            with open(str(path) + ':Zone.Identifier', 'rb') as stream:marker = stream.read()
        return (*self.snapshot(path), marker)

    def run_in_place(self, manifest):
        return create_private(manifest, self.root / 'stage', self.stop, in_place=self.session(manifest))

    def fake(self):
        return SimpleNamespace(_held_sources={}, _review_boundary=contextlib.nullcontext, _guard=lambda manifest: True,
                               _register=lambda *args: None)

    def crash(self, point, manifest):
        def fault(name, handle=None):
            if name == point:raise Crash(name)
        with patch('inplace_m4b._fault', side_effect=fault), self.assertRaises(Crash):self.run_in_place(manifest)

    def rewrite(self, path, size):
        """Foreign bytes written over the same file (its native ID kept), as another program might after a crash."""
        with open(path, 'r+b') as stream:stream.truncate(size); stream.seek(0); stream.write(b'\x5a' * size)
        return self.snapshot(path)


class EligiblePathTests(Fixture):
    def test_edit_moves_original_and_equals_copy_flow_output_bytes(self):
        source = self.media(cover=True); twin = self.root / 'Unsorted' / 'Twin.m4b'; shutil.copy2(source, twin)
        original = source.read_bytes(); manifest = self.manifest(source)
        edited, validation = self.run_in_place(manifest)
        self.assertIsInstance(edited, inplace_m4b.Edited)
        self.assertEqual(validation['encoding']['selection'], inplace_m4b.SELECTION)
        self.assertEqual(validation['publication_mode'], 'in_place'); self.assertFalse(validation['in_place']['decoded'])
        stages = []
        record = published(self.fake(), manifest, edited, validation, lambda stage, details: stages.append((stage, details)))
        final = Path(record['final_path'])
        self.assertFalse(source.exists()); self.assertTrue(final.is_file()); self.assertEqual(stages[0][0], 'publishing')
        self.assertEqual(digest(final), validation['sha256']); self.assertEqual(record['owned_temp'], str(source))
        # The copy flow, given identical source bytes, publishes exactly the same file.
        twin_manifest = self.manifest(twin, self.root / 'Sorted' / 'twin.m4b')
        checked, proof = create_private(twin_manifest, self.root / 'stage-copy', self.stop)
        self.assertEqual(proof['encoding']['selection'], 'existing_m4b_audio_stream_copy')
        self.assertEqual(digest(checked), digest(final))
        self.assertEqual(proof['tags'], validation['tags']); self.assertEqual(proof['chapters'], validation['chapters'])
        # Audio untouched: with the 4 type bytes reverted, the original extent is the original file.
        data = bytearray(final.read_bytes()); at = validation['in_place']['type_offset']
        self.assertEqual(bytes(data[at:at + 4]), b'free'); data[at:at + 4] = b'moov'
        self.assertEqual(bytes(data[:len(original)]), original)
        self.assertEqual(validation['metadata_preservation']['source_sha256'], hashlib.sha256(original).hexdigest())
        row = self.rows()[0]; self.assertEqual(row['state'], 'published')
        self.assertEqual(json.loads(row['detail'])['rename']['old_path'], str(source))
        from source_cleanup import CleanupJobs
        CleanupJobs._validation_contract(manifest, record)  # the in-place byte proof satisfies the cleanup contract
        # ...and nothing short of it does (Senua 0.21.0 F5): a missing, unverified or foreign proof is refused.
        for part, key, value in (('in_place', 'original_sha256', None), ('in_place', 'original_sha256', '0' * 64),
                                 ('in_place', 'all_retained_bytes_verified', False), ('metadata_preservation', 'source_sha256', '0' * 64)):
            with self.subTest(part=part, key=key, value=value):
                broken = copy.deepcopy(record); broken['validation'][part][key] = value
                if value is None:del broken['validation'][part][key]
                with self.assertRaisesRegex(ValueError, 'Exact in-place byte proof'):CleanupJobs._validation_contract(manifest, broken)

    def test_cover_and_tags_on_the_published_file(self):
        source = self.media(); manifest = self.manifest(source); edited, validation = self.run_in_place(manifest)
        record = published(self.fake(), manifest, edited, validation, lambda *a: None); final = Path(record['final_path'])
        raw = ap.probe(final, self.root, self.stop); tags = {k.lower(): v for k, v in raw['format']['tags'].items()}
        self.assertEqual((tags['title'], tags['artist'], tags['album'], tags['grouping']), ('The Book', 'John Writer', 'Saga - 2 - The Book', 'Saga'))
        picture = self.root / 'extracted.png'
        run_owned([shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-i', str(final), '-map', '0:v:0', '-c:v', 'copy', '-frames:v', '1', str(picture)], self.root, self.stop, 30)
        self.assertEqual(picture.read_bytes(), PNG)
        self.assertEqual([c['title'] for c in source_chapters(final, self.root, self.stop, 1.5)], ['First', 'Second'])

    def test_download_marker_removed_and_journaled(self):
        source = self.media(); marker = b'[ZoneTransfer]\r\nZoneId=3\r\n'
        with open(str(source) + ':Zone.Identifier', 'wb') as stream:stream.write(marker)
        manifest = self.manifest(source); edited, validation = self.run_in_place(manifest)
        self.assertTrue(validation['in_place']['zone_marker_removed'])
        record = published(self.fake(), manifest, edited, validation, lambda *a: None)
        import zone_identifier
        self.assertEqual(zone_identifier.streams(record['final_path']), [('::$DATA', validation['size'])])
        detail = json.loads(self.rows()[0]['detail'])
        self.assertEqual(base64.b64decode(detail['zone_marker']['marker_bytes_base64']), marker)
        self.assertEqual(base64.b64decode(json.loads(self.rows()[0]['intent'])['zone_marker']), marker)  # before the first write

    def test_publication_failure_before_rename_restores_original(self):
        source = self.media(); before = self.snapshot(source); manifest = self.manifest(source)
        edited, validation = self.run_in_place(manifest); fake = self.fake(); fake._guard = lambda manifest: False
        with self.assertRaisesRegex(ValueError, 'Candidate review changed'):
            published(fake, manifest, edited, validation, lambda *a: None)
        self.assertEqual(self.snapshot(source), before); self.assertFalse(Path(manifest['destination']).exists())
        self.assertEqual(self.rows()[0]['state'], 'rolled_back'); self.assertEqual(fake._held_sources, {})

    def test_zero_padding_box_is_admitted_by_both_paths_and_neither_output_carries_it(self):
        # Макс Фрай 01 and 04 (Sergei, 2026-10-24): moov/udta holds a box whose type and payload are all zero bytes.
        source = with_udta_child(self.media(cover=True), struct.pack('>I', 4096) + bytes(4092))
        twin = self.root / 'Unsorted' / 'Twin.m4b'; shutil.copy2(source, twin); original = source.read_bytes()
        audio = decoded(source, self.root, self.stop); dropped = [{'item': 'udta', 'removed': 'zero_padding', 'bytes': 4096}]
        manifest = self.manifest(source); edited, validation = self.run_in_place(manifest)
        self.assertIsInstance(edited, inplace_m4b.Edited, 'edited in place, not the copy-flow fallback')
        self.assertEqual(validation['metadata_preservation']['metadata_dropped'], dropped)
        final = Path(published(self.fake(), manifest, edited, validation, lambda *a: None)['final_path'])
        data = bytearray(final.read_bytes()); at = validation['in_place']['type_offset']; data[at:at + 4] = b'moov'
        self.assertEqual(bytes(data[:len(original)]), original, 'every original byte is where it was')
        checked, proof = create_private(self.manifest(twin, self.root / 'Sorted' / 'twin.m4b'), self.root / 'stage-copy', self.stop)
        self.assertEqual(proof['encoding']['selection'], 'existing_m4b_audio_stream_copy')
        self.assertEqual(proof['metadata_preservation']['metadata_dropped'], dropped)
        self.assertEqual(digest(checked), digest(final))
        for output in (final, checked):
            udta = [box for box in mp.boxes(live_movie(output).payload) if box.kind == b'udta'][0]
            self.assertFalse([box for box in mp.boxes(udta.payload) if mp.blank(box)], 'the output movie has no zero box')
            self.assertEqual(decoded(output, self.root, self.stop), audio, 'decoded audio identical to the source')

    def test_zero_padding_with_a_non_zero_byte_is_still_refused_by_both_paths(self):
        source = with_udta_child(self.media(), struct.pack('>I', 4096) + bytes(4091) + b'\1'); manifest = self.manifest(source)
        notes = []
        self.assertIsNone(inplace_m4b.edit(manifest, self.stage('probe'), self.stop, lambda stage, info: notes.append(info), self.session(manifest)))
        self.assertIn('Unsupported structural box', notes[-1]['in_place']['fallback'])
        with self.assertRaisesRegex(ValidationError, 'M4B preservation requires review: Unsupported structural box'):self.run_in_place(manifest)


def with_udta_child(path, child):
    """Put child first in the file's moov/udta; chunk offsets are shifted when moov precedes mdat. Returns path."""
    data = path.read_bytes(); top = mp.boxes(data); kinds = [box.kind for box in top]
    delta = len(child) if kinds.index(b'moov') < kinds.index(b'mdat') else 0
    def rebuild(payload, depth):
        parts = []
        for box in mp.boxes(payload):
            if box.kind in (b'trak', b'mdia', b'minf', b'stbl'):parts.append(mp.build(box.kind, rebuild(box.payload, depth + 1)))
            elif box.kind in (b'stco', b'co64') and delta:
                width = 4 if box.kind == b'stco' else 8; p = box.payload
                parts.append(mp.build(box.kind, p[:8] + b''.join((int.from_bytes(p[a:a + width], 'big') + delta).to_bytes(width, 'big') for a in range(8, len(p), width))))
            elif box.kind == b'udta' and depth == 0:parts.append(mp.build(b'udta', child + box.payload))
            else:parts.append(box.raw)
        return b''.join(parts)
    path.write_bytes(b''.join(mp.build(b'moov', rebuild(box.payload, 0)) if box.kind == b'moov' else box.raw for box in top))
    return path


def live_movie(path):
    return [box for box in mp.boxes(Path(path).read_bytes()) if box.kind == b'moov'][0]


def decoded(path, directory, stop):
    """SHA-256 of the complete decoded audio (lossless float PCM); a decode error fails the run."""
    return run_owned([shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-xerror', '-i', str(path), '-map', '0:a:0', '-c:a', 'pcm_f32le',
                      '-f', 'hash', '-hash', 'sha256', '-'], directory, stop, 60).strip()


class FallbackTests(Fixture):
    def assert_fallback(self, manifest, source):
        before = self.snapshot(source); notes = []
        result = inplace_m4b.edit(manifest, self.root / 'probe-stage', self.stop, lambda stage, info: notes.append(info), self.session(manifest))
        self.assertIsNone(result); self.assertEqual(self.snapshot(source), before)
        self.assertFalse(any(r['state'] in inplace_m4b.OPEN for r in self.rows()))
        return notes

    def setUp(self):
        super().setUp(); (self.root / 'probe-stage').mkdir()

    def test_alac_is_not_edited_in_place(self):
        source = self.media('Lossless.m4b', 'alac'); notes = self.assert_fallback(self.manifest(source), source)
        self.assertIn('fallback', notes[-1]['in_place'])  # refused by the copy flow's own preservation profile
        output, proof = self.run_in_place(self.manifest(source))
        self.assertIsInstance(output, Path); self.assertEqual(proof['encoding']['codec'], 'alac')  # the unchanged copy flow

    def test_repair_and_replacement_jobs_are_not_offered(self):
        source = self.media(); manifest = self.manifest(source)
        with patch('m4b_repair.approved_repairs', return_value=frozenset({mp.REPAIR_TAIL_OVERRUN})):self.assertFalse(inplace_m4b.offered(manifest))
        self.assertFalse(inplace_m4b.offered(dict(manifest, replacement_id='r')))
        self.assertFalse(inplace_m4b.offered(dict(manifest, sources=manifest['sources'] * 2)))
        self.assertTrue(inplace_m4b.offered(manifest))

    def test_sources_kept_by_policy_are_never_moved(self):
        # A manually approved M4B and a Retry child with a retained checkpoint freeze cleanup off: the original stays.
        source = self.media(); manifest = self.manifest(source); before = self.snapshot(source)
        for policy in ({'enabled': False}, {}, None):
            with self.subTest(policy=policy):
                kept = dict(manifest, cleanup_policy=policy)
                self.assertFalse(inplace_m4b.offered(kept))
                self.assertIsNone(inplace_m4b.edit(kept, self.root / 'probe-stage', self.stop, lambda *a: None, self.session(kept)))
        kept = dict(manifest, cleanup_policy={'enabled': False})
        output, proof = create_private(kept, self.root / 'stage-kept', self.stop, in_place=self.session(kept))
        self.assertIsInstance(output, Path); self.assertEqual(proof['encoding']['selection'], 'existing_m4b_audio_stream_copy')
        self.assertEqual(self.snapshot(source), before); self.assertEqual(self.rows(), [])

    def test_existing_destination_other_volume_foreign_stream_and_read_only(self):
        source = self.media(); manifest = self.manifest(source)
        Path(manifest['destination']).parent.mkdir(parents=True); Path(manifest['destination']).write_bytes(b'existing')
        self.assert_fallback(manifest, source); Path(manifest['destination']).unlink()
        with patch('inplace_m4b._same_volume', return_value=False):self.assert_fallback(manifest, source)
        with open(str(source) + ':extra', 'wb') as stream:stream.write(b'foreign')
        self.assert_fallback(self.manifest(source), source)
        clean = self.media('Second.m4b'); os.chmod(clean, stat.S_IREAD); self.addCleanup(os.chmod, clean, stat.S_IWRITE | stat.S_IREAD)
        self.assert_fallback(self.manifest(clean), clean)

    def test_planner_refusal_falls_back_to_the_identical_copy_flow_refusal(self):
        source = self.media()
        with open(source, 'ab') as stream:stream.write(mp.build(b'moof', b''))
        manifest = self.manifest(source); self.assert_fallback(manifest, source)
        with self.assertRaisesRegex(ValidationError, 'M4B preservation requires review'):self.run_in_place(manifest)

    def test_changed_source_and_changed_chapters_fall_back(self):
        source = self.media(); manifest = self.manifest(source)
        changed = copy.deepcopy(manifest); changed['sources'][0]['sha256'] = 'f' * 64; changed['encoding_policy'] = freeze_automatic_policy(changed['sources'])
        self.assert_fallback(changed, source)
        with self.assertRaisesRegex(ValidationError, 'Source changed'):self.run_in_place(changed)
        chapters = dict(manifest, source_chapters=[{'start': 0, 'end': 1500, 'title': 'Invented'}]); self.assert_fallback(chapters, source)

    def test_cover_gate_still_refuses_after_an_in_place_fallback(self):
        # Senua 0.21.0 F1: the fallback reuses the stage's cover copy, never its skipped probe, dimension check or decode.
        source = self.media(); before = self.snapshot(source); big = self.root / 'big.png'; notes = []
        run_owned([shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i', 'color=c=red:s=4100x4100', '-frames:v', '1', str(big)], self.root, self.stop, 60)
        manifest = dict(self.manifest(source), cover={'path': str(big), 'sha256': digest(big), 'id': 'cover'})
        with self.assertRaisesRegex(ValidationError, 'cover dimensions are invalid or too large'):
            create_private(manifest, self.root / 'stage', self.stop, lambda stage, info: notes.append(info), in_place=self.session(manifest))
        self.assertIn('cover dimensions', next(n for n in notes if 'in_place' in n)['in_place']['fallback'])  # in place fell back first
        self.assertEqual(self.snapshot(source), before); self.assertEqual(self.rows(), [])

    def test_a_selected_cover_changed_during_the_edit_is_refused_as_the_copy_flow_refuses_it(self):
        # Sergei, 2026-10-23: the fast path runs every check the copy flow runs. The copy flow re-reads the selected cover
        # file after creating its output; the edit now does so after its writes, undoes, and the copy flow then refuses.
        source = self.media(); before = self.snapshot(source); manifest = self.manifest(source)
        def changed(point, handle=None):
            if point == 'checked':Path(manifest['cover']['path']).write_bytes(PNG + b'changed')
        with patch('inplace_m4b._fault', side_effect=changed), self.assertRaisesRegex(ValidationError, 'Selected cover changed'):
            self.run_in_place(manifest)
        self.assertEqual(self.snapshot(source), before); self.assertEqual(self.rows()[0]['state'], 'rolled_back')

    def test_post_write_check_failure_undoes_then_copy_flow_runs(self):
        source = self.media(); before = self.snapshot(source); manifest = self.manifest(source); actual = ap.copied_audio_evidence; calls = []
        def contradictory(*args, **kwargs):
            evidence = actual(*args, **kwargs); calls.append(1)
            if len(calls) == 2:evidence = dict(evidence, presentation=dict(evidence['presentation'], start_pts=-1))
            return evidence
        with patch('audio_pipeline.copied_audio_evidence', side_effect=contradictory):
            output, proof = self.run_in_place(manifest)
        self.assertIsInstance(output, Path); self.assertEqual(proof['encoding']['selection'], 'existing_m4b_audio_stream_copy')
        self.assertEqual(self.snapshot(source), before); self.assertEqual(self.rows()[0]['state'], 'rolled_back')


class CrashRecoveryTests(Fixture):
    POINTS = ('before_append', 'appended', 'before_type_patch', 'type_patched', 'checked', 'reacquired')

    def test_crash_at_each_step_after_intent_is_undone_by_recovery(self):
        for point in self.POINTS:
            with self.subTest(point=point):
                source = self.media(point + '.m4b'); before = self.snapshot(source); manifest = self.manifest(source)
                self.crash(point, manifest)
                row = next(r for r in self.rows() if r['job_id'] == manifest['job_id'])
                self.assertIn(row['state'], ('intended', 'written'))
                self.assertEqual(inplace_m4b.recover_all(self.database)[-1][0], 'rolled_back')
                self.assertEqual(self.snapshot(source), before)
                inplace_m4b.clear(self.database, manifest)  # nothing open for this source any more

    def test_a_torn_append_of_full_length_is_undone(self):
        # Senua 0.21.0 F12: a power loss mid-append can persist the new length before its bytes (a zero-filled tail). The head
        # proof alone shows the undo restores the reviewed original, so the tail is cut off whatever it holds.
        source = self.media(); before = self.snapshot(source); manifest = self.manifest(source); self.crash('appended', manifest)
        intent = json.loads(self.rows()[0]['intent'])
        with open(source, 'r+b') as stream:stream.seek(intent['size']); stream.write(b'\0' * intent['appended_size'])
        self.assertEqual(os.path.getsize(source), intent['output_size'])
        self.assertEqual([state for state, _ in inplace_m4b.recover_all(self.database)], ['rolled_back'])
        self.assertEqual(self.snapshot(source), before)

    def test_cleanup_proves_a_move_only_with_the_old_path_absent_and_into_the_current_output(self):
        # Senua 0.21.0 F14: three edges of confirm_move that no test needed (mutants N5, N9 and N10 survived).
        source = self.media(); manifest = self.manifest(source); edited, validation = self.run_in_place(manifest)
        final = Path(published(self.fake(), manifest, edited, validation, lambda *a: None)['final_path'])
        def unreceipted(state):
            with contextlib.closing(sqlite3.connect(self.database)) as db, db:
                detail = json.loads(db.execute('SELECT detail FROM inplace_edits').fetchone()[0]); detail.pop('rename', None)
                db.execute('UPDATE inplace_edits SET state=?, detail=?', (state, json.dumps(detail)))
        def confirmed(output):
            return inplace_m4b.confirm_move(self.database, manifest['job_id'], str(source), str(output))
        with self.subTest('N5: a file is at the old path'):
            unreceipted('publishing'); shutil.copy2(final, source)
            self.assertIsNone(confirmed(final)); self.assertEqual(self.rows()[0]['state'], 'publishing'); source.unlink()
        with self.subTest('N9: startup recovery left the row unresolved'):
            unreceipted('unresolved'); self.assertIsNotNone(confirmed(final)); self.assertEqual(self.rows()[0]['state'], 'published')
        with self.subTest('N10: the output was relocated before its cleanup'):
            unreceipted('publishing'); moved = final.with_name('Relocated.m4b'); final.rename(moved); receipt = confirmed(moved)
            self.assertIsNotNone(receipt); self.assertEqual(os.path.normcase(receipt['final_path']), os.path.normcase(str(moved)))

    def test_cleanup_refuses_a_damaged_row_on_its_own_book_instead_of_raising(self):
        # Coordinator follow-up, 2026-10-23: published_move and confirm_move parsed rows with no shape check, so a damaged
        # row raised TypeError/KeyError/AttributeError into source cleanup. It now proves no move, and cleanup refuses that
        # book with its own reason.
        from source_cleanup import CleanupJobs
        source = self.root / 'Unsorted' / 'Book.m4b'; final = self.root / 'Sorted' / 'Book.m4b'
        receipt = {'old_path': str(source), 'final_path': str(final), 'identity': [1, 2, 3], 'old_absent': True}
        rows = {'published, detail JSON null': ('published', '{}', 'null', str(source)),
                'published, detail SQL NULL': ('published', '{}', None, str(source)),
                'published, rename not an object': ('published', '{}', json.dumps({'rename': ['x']}), str(source)),
                'published, receipt without final path or identity': ('published', '{}', json.dumps({'rename': {'old_path': str(source), 'old_absent': True}}), str(source)),
                'published, receipt without old path': ('published', '{}', json.dumps({'rename': dict(receipt, old_path=None)}), str(source)),
                'published, path NULL': ('published', '{}', json.dumps({'rename': receipt}), None),
                'publishing, intent damaged': ('publishing', '{}', '{}', str(source)),
                'unresolved, intent and path NULL': ('unresolved', None, '{}', None)}
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            inplace_m4b.ensure(db)
            for label, (state, intent, detail, path) in rows.items():
                db.execute('INSERT INTO inplace_edits VALUES(?,?,?,?,?,?,?)', (label, 'attempt', path, state, intent, detail, 'x'))
        retired = []
        cleanup = SimpleNamespace(database=self.database, root=self.root / 'recovery', review_boundary=contextlib.nullcontext,
                                  guard=lambda db, intent: True, _set=lambda *a: retired.append(a), _retire=lambda *a: retired.append(a))
        for label in rows:
            with self.subTest(row=label):
                self.assertIsNone(inplace_m4b.published_move(self.database, label, str(source)))
                self.assertIsNone(inplace_m4b.confirm_move(self.database, label, str(source), str(final)))
                manifest = {'job_id': label, 'sources': [{'path': str(source), 'size': 1, 'modified': 1, 'sha256': '0' * 64}]}
                with self.assertRaisesRegex(BoundaryError, 'In-place move receipt is missing; nothing retired'):
                    CleanupJobs._retire_moved(cleanup, 'cleanup', {'job_id': label}, manifest, {'final_path': str(final)})
        self.assertEqual(retired, [])

    def test_every_undo_puts_back_the_download_marker_it_removed(self):
        # Futaba 0.21.0 m-3: the edit removes the marker before its last checks, and no undo put it back. Its bytes are now in
        # the intent, journaled before the first write, and every undo restores them before the write time.
        source = self.media(); self.mark(source); before = self.exact(source)
        def cover_changed(point, handle=None):  # Futaba's repro B: the selected cover changes after the marker is gone
            if point == 'reacquired':Path(manifest['cover']['path']).write_bytes(PNG + b'changed')
        manifest = self.manifest(source)
        with patch('inplace_m4b._fault', side_effect=cover_changed):
            self.assertIsNone(inplace_m4b.edit(manifest, self.stage('cover'), self.stop, lambda *a: None, self.session(manifest)))
        self.assertEqual(self.exact(source), before); self.assertEqual(self.rows()[-1]['state'], 'rolled_back')
        changed = MARKER + b'ReferrerUrl=https://example.invalid/\r\n'; manifest = self.manifest(source)
        def marker_changed(point, handle=None):  # only the marker the undo would put back is ever removed
            if point == 'checked':self.mark(source, changed)
        with patch('inplace_m4b._fault', side_effect=marker_changed):
            self.assertIsNone(inplace_m4b.edit(manifest, self.stage('marker'), self.stop, lambda *a: None, self.session(manifest)))
        self.assertEqual(self.exact(source), before[:2] + (changed,)); self.assertEqual(self.rows()[-1]['state'], 'rolled_back')
        self.mark(source); before = self.exact(source); manifest = self.manifest(source)
        self.crash('reacquired', manifest)  # Futaba's repro D: the process dies after the marker removal
        row = next(r for r in self.rows() if r['job_id'] == manifest['job_id']); self.assertIsNone(self.exact(source)[2])
        legacy = source.with_name('Journaled by 0.21.0.m4b'); shutil.copyfile(source, legacy)  # its intent has no marker
        intent = {k: v for k, v in json.loads(row['intent']).items() if k != 'zone_marker'} | {'path': str(legacy)}
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            db.execute('INSERT INTO inplace_edits VALUES(?,?,?,?,?,?,?)', ('legacy', 'attempt', str(legacy), row['state'], json.dumps(intent), row['detail'], 'x'))
        self.assertEqual([state for state, _ in inplace_m4b.recover_all(self.database)], ['rolled_back', 'rolled_back'])
        self.assertEqual(self.exact(source), before); self.assertEqual(self.exact(legacy), before)

    def test_a_write_time_or_attributes_its_undo_cannot_set_writes_nothing(self):
        # Futaba 0.21.0 m-4: such values passed the type check, and the undo cut the file and patched its type before
        # restore_metadata refused them. Every value the undo needs is now checked before its first write.
        source = self.media(); manifest = self.manifest(source); self.crash('appended', manifest); good = json.loads(self.rows()[0]['intent'])
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:db.execute('DELETE FROM inplace_edits')
        values = [('modified', good['modified'], 'rolled_back'), ('modified', 2 ** 70, 'unresolved'), ('modified', -5, 'unresolved'),
                  ('modified', -116444736000000000 * 100, 'unresolved'), ('attributes', 2 ** 70, 'unresolved'),
                  ('attributes', -1, 'unresolved'), ('attributes', 0x1, 'unresolved')]
        for i, (key, value, expected) in enumerate(values):
            with self.subTest(key=key, value=value):
                path = source.with_name(f'Copy {i}.m4b'); shutil.copyfile(source, path); found = self.exact(path)
                with contextlib.closing(sqlite3.connect(self.database)) as db, db:
                    db.execute('INSERT INTO inplace_edits VALUES(?,?,?,?,?,?,?)', (f'job {i}', 'attempt', str(path), 'written', json.dumps(dict(good, path=str(path), **{key: value})), '{}', 'x'))
                inplace_m4b.recover_all(self.database); row = next(r for r in self.rows() if r['job_id'] == f'job {i}')
                self.assertEqual(row['state'], expected)
                if expected == 'unresolved':  # left exactly as found, with the damaged-record reason
                    self.assertEqual(json.loads(row['detail'])['reason'], inplace_m4b.DAMAGED); self.assertEqual(self.exact(path), found)
                else:  # the positive control: the same copy and row with a usable value is undone
                    self.assertEqual(self.snapshot(path)[0], source.read_bytes()[:good['size']])

    def test_torn_type_patch_is_restored(self):
        source = self.media(); before = self.snapshot(source); manifest = self.manifest(source); self.crash('type_patched', manifest)
        intent = json.loads(self.rows()[0]['intent'])
        with open(source, 'r+b') as stream:stream.seek(intent['type_offset']); stream.write(b'frov')
        inplace_m4b.recover_all(self.database); self.assertEqual(self.snapshot(source), before)

    def test_kill_after_rename_is_recovered_with_a_receipt_cleanup_accepts(self):
        # Senua 0.21.0 F2 / Futaba M1: a real process death between the rename and its journaled receipt. (The test this
        # replaces rewrote a receipted row back to 'publishing', which hid that recovery left cleanup no receipt.)
        source = self.media(); manifest = self.manifest(source); spec = self.root / 'manifest.json'; tests = Path(__file__).resolve().parent
        spec.write_text(json.dumps(manifest), encoding='utf-8'); lines = []
        child = subprocess.Popen([sys.executable, '-I', '-B', '-c', KILLED_AFTER_RENAME, str(tests.parent), str(tests), str(spec), self.database,
                                  str(self.root / 'stage')], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            reader = threading.Thread(target=lambda: lines.append(child.stdout.readline()), daemon=True); reader.start(); reader.join(120)
        finally:
            child.kill(); errors = child.communicate(timeout=30)[1]  # TerminateProcess: no handler, no journal write runs
        self.assertEqual(lines, ['RENAMED\n'], errors[-3000:])
        destination = Path(manifest['destination']); row = self.rows()[0]; intent = json.loads(row['intent'])
        self.assertFalse(source.exists()); self.assertEqual(digest(destination), intent['output_sha256'])
        self.assertEqual(row['state'], 'publishing'); self.assertIsNone(inplace_m4b.published_move(self.database, manifest['job_id'], str(source)))
        self.assertEqual([state for state, _ in inplace_m4b.recover_all(self.database)], ['published'])
        receipt = inplace_m4b.published_move(self.database, manifest['job_id'], str(source))  # exactly what _retire_moved requires
        self.assertIsNotNone(receipt, 'Recovery recorded the move without the receipt source cleanup needs')
        self.assertEqual(os.path.normcase(receipt['final_path']), os.path.normcase(str(destination)))
        self.assertEqual((receipt['sha256'], receipt['old_absent']), (intent['output_sha256'], True))

    def test_recovery_never_trusts_a_destination_of_the_right_size(self):
        # Senua 0.21.0 F7: a move is recorded only on the planned output's full hash, never on its size.
        source = self.media(); manifest = self.manifest(source); edited, validation = self.run_in_place(manifest)
        edited.undo(); edited.close(); intent = json.loads(self.rows()[0]['intent'])
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:db.execute("UPDATE inplace_edits SET state='publishing'")
        source.rename(source.with_name('Moved elsewhere.m4b')); destination = Path(manifest['destination'])
        destination.parent.mkdir(parents=True); destination.write_bytes(b'\0' * intent['output_size'])
        self.assertEqual([state for state, _ in inplace_m4b.recover_all(self.database)], ['unresolved'])
        self.assertIsNone(inplace_m4b.published_move(self.database, manifest['job_id'], str(source)))

    def test_recovery_writes_nothing_into_a_file_it_cannot_prove(self):
        # Senua 0.21.0 F3 / Futaba m2 (h6, h7): same file ID, foreign bytes of the original or the edited length.
        for size in ('size', 'output_size'):
            with self.subTest(size=size):
                source = self.media(size + '.m4b'); manifest = self.manifest(source); self.crash('type_patched', manifest)
                intent = json.loads(next(r for r in self.rows() if r['job_id'] == manifest['job_id'])['intent'])
                foreign = self.rewrite(source, intent[size]); inplace_m4b.recover_all(self.database)
                self.assertEqual(next(r for r in self.rows() if r['job_id'] == manifest['job_id'])['state'], 'unresolved')
                self.assertEqual(self.snapshot(source), foreign)

    def test_undo_writes_nothing_into_a_file_rewritten_while_it_was_released(self):
        # Senua 0.21.0 F3: an undo reopens its writer by path after releasing the DELETE handle; a rewrite in that gap is refused.
        source = self.media(); manifest = self.manifest(source); real = inplace_m4b.VerifiedFile; armed = []; foreign = []
        def fault(name, handle=None):
            if name == 'reacquired':armed.append(1); raise ValidationError('A check failed after the reacquire (simulated)')
        def opened(path, **kwargs):
            if armed and kwargs.get('writable'):armed.clear(); foreign.append(self.rewrite(path, os.path.getsize(path)))
            return real(path, **kwargs)
        with patch('inplace_m4b._fault', side_effect=fault), patch('inplace_m4b.VerifiedFile', side_effect=opened):
            with self.assertRaisesRegex(inplace_m4b.Unresolved, 'not the edited original'):self.run_in_place(manifest)
        self.assertEqual(self.snapshot(source), foreign[0]); self.assertEqual(self.rows()[0]['state'], 'unresolved')

    def test_cleanup_refuses_to_retire_without_a_provable_move(self):
        # Senua 0.21.0 F5: no receipt, and an output that is not the planned one, retires nothing.
        from scanner import connect
        from source_cleanup import CleanupJobs, setup
        source = self.media(); manifest = self.manifest(source); edited, validation = self.run_in_place(manifest)
        record = published(self.fake(), manifest, edited, validation, lambda *a: None); final = Path(record['final_path'])
        with connect(self.database) as db:
            setup(db); detail = json.loads(db.execute('SELECT detail FROM inplace_edits').fetchone()['detail']); detail.pop('rename')
            db.execute("UPDATE inplace_edits SET state='publishing', detail=?", (json.dumps(detail),))
        data = final.read_bytes(); final.write_bytes(data[:-1] + bytes([data[-1] ^ 1])); retired = []
        cleanup = SimpleNamespace(database=self.database, root=self.root / 'recovery', review_boundary=contextlib.nullcontext,
                                  guard=lambda db, intent: True, _set=lambda *a: retired.append(a), _retire=lambda *a: retired.append(a))
        with self.assertRaisesRegex(BoundaryError, 'In-place move receipt is missing; nothing retired'):
            CleanupJobs._retire_moved(cleanup, 'cleanup', {'job_id': manifest['job_id']}, manifest, record)
        self.assertEqual(retired, []); self.assertIsNone(inplace_m4b.published_move(self.database, manifest['job_id'], str(source)))

    def test_unprovable_original_stays_journaled_and_blocks_new_attempts(self):
        source = self.media(); manifest = self.manifest(source); audio = source.read_bytes().index(b'mdat') + 20
        def corrupted(name, handle=None):
            if name == 'checked':handle.write_at(audio, b'\x55')  # an audio byte changes under the edit
        with patch('inplace_m4b._fault', side_effect=corrupted), self.assertRaises(inplace_m4b.Unresolved):self.run_in_place(manifest)
        self.assertEqual(self.rows()[0]['state'], 'unresolved')
        with self.assertRaises(inplace_m4b.Unresolved):inplace_m4b.clear(self.database, manifest)
        self.assertEqual(self.rows()[0]['state'], 'unresolved')


class RecoveryWiringTests(Fixture):
    """Senua 0.21.0 F4: the queue itself reaches recovery, at startup and before an attempt. No test here calls it directly."""
    def queue(self, runner=None):
        from audio_jobs import AudioJobs
        jobs = AudioJobs(self.database, runner, lambda manifest: True, lambda record: True); self.addCleanup(jobs.close)
        return jobs

    def enqueue(self, jobs, manifest, state=None):
        frozen = dict(copy.deepcopy(manifest), evidence={})
        for item in frozen['sources']:item['fingerprint'] = {'size': item['size'], 'modified': item['modified']}
        job_id = jobs.enqueue(frozen)
        if state:jobs._update(job_id, state=state, stage='creating', attempt_id=manifest['attempt_id'])  # the attempt a crash interrupted
        return job_id

    def job(self, jobs, job_id):
        return jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))[0]

    def test_startup_undoes_an_interrupted_edit(self):
        source = self.media(); before = self.snapshot(source); manifest = self.manifest(source); self.crash('type_patched', manifest)
        self.queue()  # the engine starts again
        self.assertEqual(self.snapshot(source), before); self.assertEqual(self.rows()[0]['state'], 'rolled_back')

    def test_startup_shows_an_edit_it_cannot_undo_on_its_book(self):
        source = self.media(); manifest = self.manifest(source); job_id = self.enqueue(self.queue(), manifest, 'running')
        self.crash('type_patched', manifest); foreign = self.rewrite(source, os.path.getsize(source))
        jobs = self.queue(); row = self.job(jobs, job_id)  # restart: the edit cannot be proven, so nothing is written
        self.assertEqual((row['state'], row['reason']), ('needs attention', inplace_m4b.ATTENTION + 'The file at the original path is not the edited original; it was not changed'))
        self.assertEqual(self.snapshot(source), foreign); self.assertEqual(self.rows()[0]['state'], 'unresolved')

    def test_startup_shows_a_journal_it_cannot_read_on_interrupted_in_place_books(self):
        source = self.media(); manifest = self.manifest(source); first = self.queue(); job_id = self.enqueue(first, manifest, 'running')
        kept = self.enqueue(first, dict(self.manifest(source), cleanup_policy={'enabled': False}), 'running')
        with patch('inplace_m4b._rows', side_effect=sqlite3.OperationalError('disk I/O error')):jobs = self.queue()
        self.assertEqual((self.job(jobs, job_id)['state'], self.job(jobs, job_id)['reason']), ('needs attention', inplace_m4b.ATTENTION + 'disk I/O error'))
        self.assertEqual(self.job(jobs, kept)['state'], 'pending')  # a book that is never edited in place just restarts

    def test_startup_shows_a_damaged_journal_row_on_its_book_and_still_starts(self):
        # Futaba 0.21.0 M1: a row of the wrong shape raised KeyError/TypeError out of startup, so the engine never started.
        # Each damaged row is now unresolved on its own book; a damaged detail never blocks the undo of an intact intent.
        # Whole-column damage and the bounds are here; each single key of a real row is DamagedRowTests' (0.21.1 F15).
        source = self.media(); before = self.snapshot(source); first = self.queue()
        intact = self.manifest(source); intact_id = self.enqueue(first, intact, 'running'); self.crash('appended', intact)
        good = json.loads(self.rows()[0]['intent'])
        rows = {'empty object': ('written', '{}', '{}'), 'JSON null': ('written', 'null', '{}'), 'SQL NULL': ('written', None, None),
                'not JSON': ('written', 'not json', '{}'), 'JSON list': ('intended', '[]', '[]'),
                # past the original's end: an unchecked undo would pass the head proof, then write 'moov' after the last byte
                'type offset outside the original': ('written', json.dumps(dict(good, type_offset=good['size'])), '{}'),
                'output not longer than the original': ('written', json.dumps(dict(good, output_size=good['size'])), '{}'),
                'unresolved, library root unreachable, detail NULL': ('unresolved', json.dumps(dict(good, path=str(self.root / 'Gone' / 'Book.m4b'), root=str(self.root / 'Gone'))), None)}
        manifests = {label: dict(copy.deepcopy(intact), job_id=str(uuid.uuid4()), attempt_id=str(uuid.uuid4()), candidate_id=str(uuid.uuid4())) for label in rows}
        jobs = {label: self.enqueue(first, m, 'running') for label, m in manifests.items()}
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            db.execute("UPDATE inplace_edits SET detail='null'")  # the intact row's detail is damaged too
            for label, (state, intent, detail) in rows.items():
                db.execute('INSERT INTO inplace_edits VALUES(?,?,?,?,?,?,?)', (manifests[label]['job_id'], manifests[label]['attempt_id'], str(source), state, intent, detail, 'x'))
        restarted = self.queue()  # the engine starts again
        for label, job_id in jobs.items():
            with self.subTest(row=label):
                row = self.job(restarted, job_id)
                self.assertEqual((row['state'], row['reason']), ('needs attention', inplace_m4b.ATTENTION + inplace_m4b.DAMAGED))
        self.assertEqual(self.job(restarted, intact_id)['state'], 'pending'); self.assertEqual(self.snapshot(source), before)
        kept = next(r for r in self.rows() if r['job_id'] == intact['job_id'])
        self.assertEqual((kept['state'], json.loads(kept['detail'])['damaged_detail']), ('rolled_back', 'null'))

    def test_startup_leaves_an_edit_open_only_while_its_library_root_cannot_be_seen(self):
        # Senua 0.21.0 F13: a library share not reconnected yet at startup is not a missing original. The book restarts with
        # no attention, and the next start that can see the library undoes the edit. 0.21.1 F17: offline is the library root
        # itself out of sight (this test used to rename the book folder, which is exactly the case it misread). A book
        # folder renamed or deleted in a visible library, or a file moved by hand, is a missing original.
        library = self.root / 'Library'; source = self.media(folder=library / 'Writer'); before = self.snapshot(source)
        manifest = self.manifest(source, root=library); job_id = self.enqueue(self.queue(), manifest, 'running')
        self.crash('type_patched', manifest); away = library.with_name('Library offline'); library.rename(away)
        journaled = self.rows()[0]['state']; jobs = self.queue(); row = self.job(jobs, job_id)
        self.assertEqual((row['state'], row['reason']), ('pending', 'Interrupted book restarts on explicit resume'))
        self.assertEqual(self.rows()[0]['state'], journaled)  # still open, nothing recorded
        inplace_m4b.clear(self.database, manifest); self.assertEqual(self.rows()[0]['state'], journaled)  # an attempt is not refused
        away.rename(library); self.queue()
        self.assertEqual(self.snapshot(source), before); self.assertEqual(self.rows()[0]['state'], 'rolled_back')
        for label, gone_by_hand in (('book folder renamed', lambda path: path.parent.rename(path.parent.with_name('Renamed by hand'))),
                                    ('file moved within its folder', lambda path: path.rename(path.with_name('Moved by hand.m4b')))):
            with self.subTest(label):
                gone = self.media(label + '.m4b', folder=library / label); missing = self.manifest(gone, root=library)
                gone_id = self.enqueue(jobs, missing, 'running'); self.crash('type_patched', missing); gone_by_hand(gone)
                row = self.job(self.queue(), gone_id)
                self.assertEqual((row['state'], row['reason']), ('needs attention', inplace_m4b.ATTENTION + 'The edited original is missing and its destination does not hold it'))

    def test_a_damaged_row_refuses_only_its_own_books_attempt(self):
        # Coordinator follow-up, 2026-10-23: clear() compared every open row's path column, so one row with a NULL path (and a
        # damaged intent, which keeps it open) raised TypeError in every book's attempt. It now refuses its own book only.
        seen = []
        def runner(manifest, stop, checkpoint):
            seen.append(manifest['job_id']); stop.set(); raise InterruptedError('Fixture stops at the runner')
        jobs = self.queue(runner); damaged, other = self.manifest(self.media()), self.manifest(self.media('Other.m4b'))
        damaged_id, other_id = self.enqueue(jobs, damaged), self.enqueue(jobs, other)
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            inplace_m4b.ensure(db)
            db.execute('INSERT INTO inplace_edits VALUES(?,?,?,?,?,?,?)', (damaged['job_id'], damaged['attempt_id'], None, 'unresolved', '{}', '{}', 'x'))
        for job_id in (other_id, damaged_id):
            jobs._stop.clear(); jobs._work_attempt(self.job(jobs, job_id))
        self.assertEqual(seen, [other['job_id']])  # the other book reached its runner; the damaged one never did
        row = self.job(jobs, damaged_id)
        self.assertEqual((row['state'], row['reason']), ('needs attention', inplace_m4b.ATTENTION + inplace_m4b.DAMAGED))

    def test_startup_does_not_swallow_a_programming_error(self):
        # Senua 0.21.0 F14 (N6): startup recovery catches only file-system, value and catalog errors; a bug still surfaces.
        with patch('inplace_m4b.recover_all', side_effect=AttributeError('a programming error')):
            with self.assertRaisesRegex(AttributeError, 'a programming error'):self.queue()

    def test_an_attempt_first_undoes_or_refuses_an_interrupted_edit_of_its_source(self):
        seen = []
        def runner(manifest, stop, checkpoint):
            seen.append(self.snapshot(manifest['sources'][0]['path'])); stop.set(); raise InterruptedError('Fixture stops at the runner')
        jobs = self.queue(runner)  # startup recovery has already run: these edits are left open after it
        for name, foreign in (('Undone.m4b', False), ('Unprovable.m4b', True)):
            with self.subTest(name=name):
                source = self.media(name); before = self.snapshot(source); manifest = self.manifest(source)
                job_id = self.enqueue(jobs, manifest); self.crash('type_patched', manifest); jobs._stop.clear()
                if foreign:before = self.rewrite(source, os.path.getsize(source))
                jobs._work_attempt(self.job(jobs, job_id))
                self.assertEqual(self.snapshot(source), before)
                if foreign:
                    self.assertEqual(self.job(jobs, job_id)['state'], 'needs attention'); self.assertEqual(len(seen), 1)  # never handed to the runner
                    self.assertTrue(self.job(jobs, job_id)['reason'].startswith(inplace_m4b.ATTENTION))
                else:
                    self.assertEqual(seen, [before])  # the runner saw the restored original


def key_paths(value, prefix=()):
    """Every key of a journaled JSON object, the keys of nested objects included, as a tuple of keys."""
    for key, inner in value.items():
        yield prefix + (key,)
        if isinstance(inner, dict):yield from key_paths(inner, prefix + (key,))


def damaged(value, keys, how):
    """A copy of value whose key at `keys` is deleted ('missing') or holds a value of another type."""
    value = copy.deepcopy(value); parent = value
    for key in keys[:-1]:parent = parent[key]
    if how == 'missing':del parent[keys[-1]]
    else:parent[keys[-1]] = 'x' if isinstance(parent[keys[-1]], list) else [parent[keys[-1]]]
    return value


RESTARTS = ('pending', 'Interrupted book restarts on explicit resume')
REFUSED = ('needs attention', inplace_m4b.ATTENTION + inplace_m4b.DAMAGED)
NO_RECEIPT = 'In-place move receipt is missing; nothing retired'


class DamagedRowTests(Fixture):
    """Futaba 0.21.0 M-1, Senua F15 and F16: damaged-row handling was fixed one field at a time, twice, because each test
    listed the fields its fix knew. Every case here is generated from a row the edit really wrote: each key deleted, and
    each given a value of another type (nested receipts included), plus a NULL key column. A field the edit starts writing
    is covered with no change here. Both world states (the edited original at its path; moved into its output) go through
    every reader: startup recovery, clear() before an attempt, and source cleanup's published_move and confirm_move.

    A damaged intent refuses only its own book, with the damaged-record reason, and writes nothing. A damaged detail
    never decides what the intact intent proves. The other book never notices, and no raw exception text appears."""
    queue, enqueue, job = RecoveryWiringTests.queue, RecoveryWiringTests.enqueue, RecoveryWiringTests.job

    def setUp(self):
        super().setUp(); self.seen = []

    def runner(self, manifest, stop, checkpoint):
        path = manifest['sources'][0]['path']
        self.seen.append((manifest['job_id'], self.exact(path) if os.path.exists(path) else None)); stop.set()
        raise InterruptedError('Fixture stops at the runner')

    def cases(self, row):
        """[(label, kind, part, keys, how)]. 'valid': the intent still proves the outcome. 'damaged': refused on its own book.
        'unaddressable' (attempt_id NULL) and 'orphan' (job_id NULL): the journal can settle neither (F16)."""
        found = [('intact row', 'valid', None, (), None)]
        for part in ('intent', 'detail'):
            for keys in key_paths(json.loads(row[part])):
                for how in ('missing', 'of another type'):
                    # Without its marker key an intent reads as one 0.21.0 wrote, whose marker is in its removal receipt.
                    valid = part == 'detail' or (keys, how) == (('zone_marker',), 'missing')
                    found.append((part + ' ' + '.'.join(keys) + ' ' + how, 'valid' if valid else 'damaged', part, keys, how))
        return found + [('attempt_id NULL', 'unaddressable', 'attempt_id', (), None), ('job_id NULL', 'orphan', 'job_id', (), None)]

    def take(self, manifest):
        """The row the edit wrote for this book, taken out of the journal so that each case is journaled on its own."""
        row = next(r for r in self.rows() if r['job_id'] == manifest['job_id'])
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:db.execute('DELETE FROM inplace_edits WHERE job_id=?', (row['job_id'],))
        return row

    def place(self, manifest, row, case, path, state=None):
        """Journal one case as a book of its own whose single source is `path`; returns that book's manifest."""
        label, kind, part, keys, how = case
        book = dict(copy.deepcopy(manifest), job_id=str(uuid.uuid4()), attempt_id=str(uuid.uuid4()), candidate_id=str(uuid.uuid4()))
        book['sources'][0]['path'] = str(path)
        intent = dict(json.loads(row['intent']), path=str(path), job_id=book['job_id'], attempt_id=book['attempt_id'])
        detail = json.loads(row['detail'])
        if 'rename' in detail:detail['rename']['old_path'] = str(path)
        if part == 'intent':intent = damaged(intent, keys, how)
        if part == 'detail':detail = damaged(detail, keys, how)
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            db.execute('INSERT INTO inplace_edits VALUES(?,?,?,?,?,?,?)', (None if part == 'job_id' else book['job_id'], None if part == 'attempt_id' else book['attempt_id'],
                       str(path), state or row['state'], json.dumps(intent), json.dumps(detail), 'x'))
        return book

    def other_book(self, first):
        """Another book's interrupted edit (killed mid-append), running when the engine stopped."""
        other = self.media('Other.m4b'); before = self.exact(other); manifest = self.manifest(other)
        job_id = self.enqueue(first, manifest, 'running'); self.crash('appended', manifest)
        return other, before, manifest, job_id

    def retire(self, book):
        """Source cleanup's in-place retirement of this book: 'completed' or its refusal, and the facts it retired."""
        from source_cleanup import CleanupJobs
        retired = []
        cleanup = SimpleNamespace(database=self.database, root=self.root / 'recovery', review_boundary=contextlib.nullcontext,
                                  guard=lambda db, intent: True, _set=lambda *a: None,
                                  _retire=lambda intent, source, member, db=None: retired.append(json.loads(member['facts'])))
        try:
            CleanupJobs._retire_moved(cleanup, 'cleanup ' + book['job_id'], {'job_id': book['job_id']}, book, {'final_path': book['destination']})
        except BoundaryError as error:
            return str(error), retired
        return 'completed', retired

    def assert_attempts(self, jobs, placed, reached):
        """clear() before each case's attempt: a valid one reaches its runner as `reached` says; every other is refused."""
        for (label, kind, *_), book, path, found in placed:
            with self.subTest(reader='attempt', case=label):
                job_id = self.enqueue(jobs, book); jobs._stop.clear(); jobs._work_attempt(self.job(jobs, job_id))
                seen = dict(self.seen)
                if kind == 'valid':
                    self.assertIn(book['job_id'], seen); reached(book, seen[book['job_id']])
                else:
                    self.assertNotIn(book['job_id'], seen); job = self.job(jobs, job_id)
                    self.assertEqual((job['state'], job['reason']), REFUSED)
                    if found is not None:self.assertEqual(self.exact(path), found)

    def test_every_damaged_field_of_an_edit_left_at_its_original_path(self):
        first = self.queue(); source = self.media(); self.mark(source); original = self.exact(source); manifest = self.manifest(source)
        self.crash('reacquired', manifest)  # edited and its download marker removed, then the process died
        row = self.take(manifest); cases = self.cases(row); other, other_before, other_manifest, other_id = self.other_book(first)
        def copies(phase):  # each case edits its own copy, so a wrong write shows on that case alone
            placed = []
            for i, case in enumerate(cases):
                path = source.with_name(f'{phase} {i}.m4b'); shutil.copyfile(source, path)
                placed.append((case, self.place(manifest, row, case, path), path, self.exact(path)))
            return placed
        placed = copies('Startup'); ids = [self.enqueue(first, book, 'running') for _, book, _, _ in placed]
        jobs = self.queue(self.runner)  # the engine starts again
        for ((label, kind, *_), book, path, found), job_id in zip(placed, ids):
            with self.subTest(reader='startup', case=label):
                job = self.job(jobs, job_id)
                self.assertEqual((job['state'], job['reason']), RESTARTS if kind in ('valid', 'orphan') else REFUSED)
                self.assertEqual(self.exact(path), original if kind == 'valid' else found)  # bytes, write time and marker
        job = self.job(jobs, other_id); self.assertEqual((job['state'], job['reason']), RESTARTS); self.assertEqual(self.exact(other), other_before)
        self.assert_attempts(jobs, copies('Attempt'), lambda book, state: self.assertEqual(state, original))
        jobs._stop.clear(); jobs._work_attempt(self.job(jobs, other_id)); self.assertEqual(self.seen[-1], (other_manifest['job_id'], other_before))
        from source_cleanup import setup
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:setup(db)
        edited = self.exact(source)
        for case in cases:  # 'unresolved', so that confirm_move reads every one of them
            with self.subTest(reader='cleanup', case=case[0]):
                self.assertEqual(self.retire(self.place(manifest, row, case, source, 'unresolved')), (NO_RECEIPT, []))
        self.assertEqual(self.exact(source), edited)

    def test_every_damaged_field_of_an_edit_moved_into_its_output(self):
        first = self.queue(); source = self.media(); self.mark(source); manifest = self.manifest(source)
        edited, validation = self.run_in_place(manifest); published(self.fake(), manifest, edited, validation, lambda *a: None)
        output = Path(manifest['destination']); kept = self.exact(output); row = self.take(manifest)
        self.assertEqual(json.loads(row['detail'])['rename']['schema'], 'books-native-no-copy-rename-v1')
        detail = json.loads(row['detail']); detail.pop('rename')
        killed = dict(row, state='publishing', detail=json.dumps(detail))  # a process death between the rename and its receipt
        cases = self.cases(killed); other, other_before, other_manifest, other_id = self.other_book(first)
        def moved(phase):  # each case's original has its own (absent) old path; all of them moved into the one output
            return [(case, self.place(manifest, killed, case, source.with_name(f'{phase} {i}.m4b')), None, None) for i, case in enumerate(cases)]
        def receipt(book):
            return inplace_m4b.published_move(self.database, book['job_id'], book['sources'][0]['path'])
        placed = moved('Startup'); ids = [self.enqueue(first, book, 'running') for _, book, _, _ in placed]
        jobs = self.queue(self.runner)  # the engine starts again
        for ((label, kind, *_), book, _, _), job_id in zip(placed, ids):
            with self.subTest(reader='startup', case=label):
                job = self.job(jobs, job_id)
                self.assertEqual((job['state'], job['reason']), RESTARTS if kind in ('valid', 'orphan') else REFUSED)
                if kind == 'valid':self.assertEqual(os.path.normcase(receipt(book)['final_path']), os.path.normcase(str(output)))
                else:self.assertIsNone(receipt(book))
        job = self.job(jobs, other_id); self.assertEqual((job['state'], job['reason']), RESTARTS); self.assertEqual(self.exact(other), other_before)
        self.assert_attempts(jobs, moved('Attempt'), lambda book, state: self.assertEqual(os.path.normcase(receipt(book)['final_path']), os.path.normcase(str(output))))
        from source_cleanup import setup
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:setup(db)
        for state, base in (('publishing', killed), ('published', row)):
            for i, (label, kind, *rest) in enumerate(self.cases(base)):
                with self.subTest(reader='cleanup', state=state, case=label):
                    book = self.place(manifest, base, (label, kind, *rest), source.with_name(f'Cleanup {state} {i}.m4b'), state)
                    outcome, retired = self.retire(book)
                    # A published row's own receipt proves its move whatever its intent says; after a kill there is no
                    # receipt, and a receipt cleanup cannot use is replaced, so the intent must prove the move again.
                    if kind in ('unaddressable', 'orphan') or state == 'publishing' and kind != 'valid':
                        self.assertEqual((outcome, retired), (NO_RECEIPT, []))
                        continue
                    self.assertEqual((outcome, len(retired)), ('completed', 1))
                    self.assertEqual(os.path.normcase(retired[0]['final_path']), os.path.normcase(str(output)))
                    self.assertTrue(isinstance(retired[0]['identity'], list) and len(retired[0]['identity']) == 3 and all(type(n) is int for n in retired[0]['identity']))
                    if (state, label) == ('published', 'intact row'):  # Senua 0.21.0 F20: the rename's own receipt, not a second proof
                        self.assertEqual(receipt(book)['schema'], 'books-native-no-copy-rename-v1')
        self.assertEqual(self.exact(output), kept)


class ByteProofTests(Fixture):
    def test_proof_accepts_the_plan_and_rejects_any_changed_audio_byte(self):
        source = self.media(); original = source.read_bytes(); tags = ap.preservation_tags(self.manifest(source))
        plan = mp.plan(len(original), lambda at, n: original[at:at + n], tags, PNG, frozenset())
        output = bytearray(original); at = plan.movie_offset + 4; output[at:at + 4] = b'free'; output += plan.appended_movie
        intent = {'type_offset': at, 'output_size': len(output), 'sha256': hashlib.sha256(original).hexdigest(),
                  'output_sha256': hashlib.sha256(output).hexdigest()}
        candidate = self.root / 'candidate.m4b'; candidate.write_bytes(output)
        with VerifiedFile(candidate) as handle:inplace_m4b._byte_proof(handle, plan, intent, self.stop)
        audio = plan.mdat_extents[0][0] + 5; output[audio] ^= 1; candidate.write_bytes(output)
        with VerifiedFile(candidate) as handle, self.assertRaisesRegex(ValidationError, 'changed retained source bytes'):
            inplace_m4b._byte_proof(handle, plan, intent, self.stop)


def gate_table(modules=('audio_pipeline', 'm4b_preservation', 'm4b_repair', 'encoding_policy', 'source_proofs', 'inplace_m4b')):
    """{(file, line): ['function: message', ...]}, every refusal guard in these modules as the code states it: an `if`
    whose own body or final else raises, and every need(condition, message). Messages are their constant text."""
    table = {}
    def text(node, args):
        found = next((a for a in args if isinstance(a, (ast.Constant, ast.JoinedStr, ast.BinOp))), node)
        while isinstance(found, ast.BinOp):found = found.left
        if isinstance(found, ast.JoinedStr):return ''.join(str(v.value) for v in found.values if isinstance(v, ast.Constant))
        return str(found.value) if isinstance(found, ast.Constant) else ast.unparse(found) if found is not None else 're-raise'
    def walk(node, function, path):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If):
                tail = [] if child.orelse[:1] and isinstance(child.orelse[0], ast.If) else child.orelse
                raised = next((s for s in child.body + tail if isinstance(s, ast.Raise)), None)
                if raised:table.setdefault((path, child.lineno), []).append(function + ': ' + text(raised.exc, getattr(raised.exc, 'args', ())))
            elif isinstance(child, ast.Call) and getattr(child.func, 'id', getattr(child.func, 'attr', '')) == 'need' and len(child.args) == 2:
                table.setdefault((path, child.lineno), []).append(function + ': ' + text(child.args[1], child.args[1:]))
            walk(child, child.name if isinstance(child, (ast.FunctionDef, ast.ClassDef)) else function, path)
    for name in modules:
        path = inspect.getsourcefile(importlib.import_module(name)); walk(ast.parse(Path(path).read_text(encoding='utf-8')), '<module>', path)
    return table


@contextlib.contextmanager
def gates_run(seen, paused=()):
    """Add to `seen` every gate a run evaluates (its guard line executes), except while `paused` is non-empty. Through
    sys.monitoring, every other line disables its own event after the first one, so the run keeps its normal speed."""
    table = gate_table(); monitoring = sys.monitoring; tool = next(i for i in (3, 4) if monitoring.get_tool(i) is None)
    def line(code, number):
        gates = table.get((code.co_filename, number))
        if gates is None or not paused:
            seen.update(gates or ()); return monitoring.DISABLE
    monitoring.use_tool_id(tool, 'in-place parity'); monitoring.restart_events()
    monitoring.register_callback(tool, monitoring.events.LINE, line); monitoring.set_events(tool, monitoring.events.LINE)
    try:yield seen
    finally:
        monitoring.set_events(tool, 0); monitoring.register_callback(tool, monitoring.events.LINE, None)
        monitoring.free_tool_id(tool); monitoring.restart_events()


NO_DECODE = 'no decode in place (Sergei, 2026-10-22): _byte_proof shows no audio byte moved'
NO_STAGE = 'nothing is staged in place: no source snapshot, no candidate file'
ONE_M4B = 'offered(): exactly one .m4b source in the automatic profile'
# Every copy-flow gate the in-place edit does not evaluate itself, as 'function: message prefix' (a bare 'function: ' covers
# machinery the edit has none of by design). The value is either 'in place: <the in-place gate doing its job>', which the
# edit must evaluate, or why there is no such job in place. An entry that no longer matches a skipped gate fails too.
COVERED = {
    '_create_private: Frozen automatic encoding policy changed': 'in place: _edit: Frozen automatic encoding policy changed',
    '_create_private: Protected cover differs from reviewed artwork': 'in place: _edit: Protected cover differs from reviewed artwork',
    '_create_private: Protected snapshot differs from reviewed source bytes': 'in place: _edit: Source changed',
    'snapshot_manifest: Protected snapshot differs from reviewed source bytes': 'in place: _edit: Source changed',
    'snapshot_manifest: No reviewed source files are included': ONE_M4B,
    'snapshot_manifest: This source format is not supported': ONE_M4B,
    'snapshot_manifest: Existing M4B parts carry their own chapters': ONE_M4B,
    'snapshot_manifest: Included files have incompatible': ONE_M4B,
    'same_source: Source changed': 'in place: _edit: Source changed',  # and the source is held deny-writers until the move
    'check_working_space: Source changed before working-space admission': 'in place: _edit: Source identity, links or attributes',
    'check_working_space: Source is outside the supported audiobook boundary': ONE_M4B + '; DirectoryBoundary(root, source.parent) refuses',
    'check_working_space: Destination is outside the audiobook library': 'in place: _edit: Destination is not a distinct library M4B',
    'check_working_space: Audiobook destination root is unavailable': 'in place: _edit: Destination exists or is on another volume',
    'check_working_space: Insufficient destination space': 'in place: _edit: Insufficient library space',
    'check_working_space: Insufficient staging space': NO_STAGE,
    'check_working_space: Insufficient working space': NO_STAGE,
    'output_space_required: ': NO_STAGE,
    'decoded_duration: ': NO_DECODE,
    '_encode_inputs: Staging space changed': 'in place: _edit: Insufficient library space',
    '_encode_inputs: Installed ffmpeg is required': 'the edit runs FFmpeg itself (probe, chapters, packet evidence) and falls back without it',
    '_preserve_single_m4b: Existing M4B chapters differ': 'in place: _edit: Existing M4B chapters differ',
    '_preserve_single_m4b: Protected cover differs from reviewed artwork': 'in place: _edit: Planned cover differs from reviewed artwork',
    '_preserve_single_m4b: Insufficient space for the single metadata candidate': 'in place: _edit: Insufficient library space',
    '_preserve_single_m4b: Preservation source differs from frozen bytes': 'in place: _edit: Source changed',
    '_preserve_single_m4b: Preservation source identity changed': 'in place: _edit: In-place source identity changed after the edit',
    '_preserve_single_m4b: Preservation candidate differs from its creation receipt': 'in place: _byte_proof: In-place edit changed retained source bytes',
    '_preserve_single_m4b: Preserved candidate identity changed': 'in place: _byte_proof: In-place edit changed retained source bytes',
    'stream_candidate: ': 'in place: _byte_proof: In-place edit changed retained source bytes',
    'verify_candidate: ': 'in place: _byte_proof: In-place edit changed retained source bytes',
    '_preserve_single_m4b: Preservation changed decoder, packets or presentation': 'in place: _edit: Preservation changed decoder, packets or presentation',
    '_preserve_single_m4b: Preservation changed complete native decoded audio': NO_DECODE,
    'result: Native M4B decoded frame proof is incomplete': NO_DECODE,
    '_preserve_single_m4b: Preserved output audio profile is incorrect': 'in place: _edit: Preserved output audio profile is incorrect',
    '_preserve_single_m4b: Preserved source chapter presentation changed': 'in place: _edit: Preserved source chapter presentation changed',
    '_preserve_single_m4b: Preserved output approved metadata differs': 'in place: _edit: Preserved output approved metadata differs',
    'confirm: Applied repair differs from the approved repair': 'in place: _edit: This book needs a repair',
    # Found by this test on 2026-10-23 and closed the same day (Sergei: the fast path runs every check the copy flow runs).
    '_preserve_single_m4b: Selected cover changed': 'in place: _edit: Selected cover changed',
}


class ParityTests(Fixture):
    """Futaba 0.21.0 pattern alert: twice the in-place path skipped a check the copy flow makes for the same manifest (the
    keep-sources policy, 8ba3af9; the cover gate after a fallback, 7321517). The copy flow's gate list is not copied here:
    gate_table() reads every refusal guard out of the code, and a line tracer records which ones each run evaluates. A gate
    added to the copy flow fails this test until the in-place path evaluates it too or COVERED states why it need not."""
    def test_the_in_place_path_skips_no_gate_the_copy_flow_runs_for_the_same_manifest(self):
        source = self.media(cover=True); twin = self.root / 'Unsorted' / 'Twin.m4b'; shutil.copy2(source, twin); (self.root / 'probe-stage').mkdir()
        alone, eligible = self.manifest(twin, self.root / 'Sorted' / 'twin.m4b'), self.manifest(source)  # built outside every trace
        with gates_run(set()) as copy_flow:create_private(alone, self.root / 'stage', self.stop)
        with gates_run(set()) as edit:edited, validation = self.run_in_place(eligible)
        self.assertIsInstance(edited, inplace_m4b.Edited); edited.undo(); edited.close()
        skipped = copy_flow - edit
        self.assertEqual(sorted(g for g in skipped if not any(g.startswith(key) for key in COVERED)), [], 'Copy-flow gates the edit skips')
        self.assertEqual(sorted(key for key in COVERED if not any(g.startswith(key) for g in skipped)), [], 'Stale COVERED entries')
        named = {value[len('in place: '):] for value in COVERED.values() if value.startswith('in place: ')}
        self.assertEqual(sorted(gate for gate in named if not any(g.startswith(gate) for g in edit)), [], 'Named in-place gates that never ran')
        # After the edit falls back, before its first write or after its undo, the copy flow runs every gate it runs alone.
        def failed_check(point, handle=None):
            if point == 'checked':raise ValidationError('Check failure (parity test)')
        for when, seam, effect in (('before the first write', 'inplace_m4b._hashes', inplace_m4b.Ineligible('Fallback (parity test)')),
                                   ('after the undo', 'inplace_m4b._fault', failed_check)):
            with self.subTest(fallback=when):
                inside = []; real = inplace_m4b.edit; manifest = self.manifest(source)
                def edit_only(*args):
                    inside.append(1)
                    try:return real(*args)
                    finally:inside.pop()
                with patch(seam, side_effect=effect), patch('inplace_m4b.edit', side_effect=edit_only), gates_run(set(), inside) as after:
                    output, proof = self.run_in_place(manifest)
                self.assertEqual(proof['encoding']['selection'], 'existing_m4b_audio_stream_copy')
                self.assertEqual(sorted(copy_flow - after), [], 'Copy-flow gates skipped after the fallback')
        # Decided outside create_private, so no gate exists to trace: the copy flow keeps the original unless source cleanup
        # is enrolled (merge_service: cleanup_policy.enabled), and keeps a replacement's or an approved repair's sources.
        base = self.manifest(source); before = self.snapshot(source); journal = self.rows()
        repair = {'schema': m4b_repair.SCHEMA, 'note': 'repair', 'repairs': [{'kind': mp.REPAIR_TAIL_OVERRUN}]}
        for change in ({'cleanup_policy': {'enabled': False}}, {'cleanup_policy': {}}, {'cleanup_policy': None},
                       {'replacement_id': 'replacement'}, {'m4b_repair': repair}):
            with self.subTest(change=change):
                result = inplace_m4b.edit(dict(base, **change), self.root / 'probe-stage', self.stop, lambda *a: None, self.session(base))
                self.assertIsNone(result); self.assertEqual(self.snapshot(source), before); self.assertEqual(self.rows(), journal)


class ServiceTests(unittest.TestCase):
    """The whole service: automatic approval, queue, guards, in-place move, cleanup, retention and counts."""
    def setUp(self):
        from test_automatic_processing import fixture_payload, AREA as AUTOMATIC
        from test_automatic_media import artwork
        from scanner import Inventory
        from merge_service import MergeService
        from public_research import PublicClient
        self.temp = tempfile.TemporaryDirectory(dir=AUTOMATIC); self.base = Path(self.temp.name); self.audio = self.base / 'audio'; self.audio.mkdir()
        self.cover = artwork(); stop = threading.Event(); plain = self.base / 'plain.m4b'; self.source = self.audio / 'A Book.m4b'
        run_owned([shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', '-ar', '44100', '-ac', '1', '-c:a', 'aac', str(plain)], self.base, stop, 30)
        (self.base / 'chapters.txt').write_text(CHAPTERS.replace('1500', '1000'), encoding='utf8')
        run_owned([shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-i', str(plain), '-f', 'ffmetadata', '-i', str(self.base / 'chapters.txt'),
                   '-map', '0:a:0', '-map_chapters', '1', '-c:a', 'copy', '-metadata', 'title=A Book', '-metadata', 'album=A Book', '-metadata', 'artist=John Writer', str(self.source)], self.base, stop, 30)
        roots = {'Audiobooks': str(self.audio), 'Podcasts': str(self.base / 'podcasts'), 'Ebooks': str(self.base / 'ebooks')}
        self.inv = Inventory(self.base / 'catalog.sqlite3', roots); self.inv.launch('Audiobooks'); self.inv.worker.join(10)
        self.service = MergeService(self.inv, self.base / 'cache')
        def fetch(url, *_):
            if '/search-works?' in url:return json.dumps([{'work_id': 42, 'name': 'A Book', 'rusname': 'Книга', 'all_autor_name': 'John Writer', 'all_autor_rusname': 'Джон Писатель'}]).encode()
            if '/work/42/extended' in url:return json.dumps(fixture_payload()).encode()
            if 'duckduckgo.com' in url:return b'<a class="result__a" href="https://ast.ru/book/example/">A Book</a>'
            if 'ast.ru' in url:return b'<p>John Writer. A Book</p>'
            if 'fantlab.ru/images/cover.jpg' in url:return self.cover
            raise AssertionError('Unexpected fixture public URL')
        self.client = PublicClient(self.inv.database, fetch=fetch)

    def tearDown(self):
        self.service.close(); self.temp.cleanup()

    def wait(self):
        limit = time.monotonic() + 60
        while True:
            state = self.service.state(); audio = self.service.jobs._thread; cleanup = self.service.cleanup.thread
            if not (audio and audio.is_alive() or cleanup and cleanup.is_alive() or state['state'] in ('Running', 'Pausing') or state.get('queued') or state.get('cleanup_active')):return
            if time.monotonic() > limit:self.fail('In-place service job exceeded 60 s')
            time.sleep(.05)

    def test_automatic_single_m4b_is_edited_moved_retired_and_counted(self):
        from public_research import PublicResearch
        from merge_service import MergeService
        original = self.source.read_bytes(); row = self.service.reviews.page()['rows'][0]
        result = PublicResearch(self.client).lookup(row, str(self.audio)); self.assertEqual(result['reasons'], [], result)
        real = inplace_m4b.confirm_move; proved = []
        def confirm(*args):
            proved.append(args); return real(*args)
        with patch('inplace_m4b.confirm_move', side_effect=confirm):
            fresh, job_id = self.service.approve_automatic(row, result, threading.Event(), self.client); self.wait()
        job = self.service.jobs.status()['jobs'][0]; self.assertEqual(job['state'], 'completed', job)
        validation = job['output']['validation']; final = Path(job['output']['final_path'])
        self.assertEqual(validation['encoding']['selection'], inplace_m4b.SELECTION)
        self.assertFalse(self.source.exists()); self.assertTrue(final.is_file()); self.assertTrue(self.service._output_valid(job['output']))
        data = bytearray(final.read_bytes()); at = validation['in_place']['type_offset']; data[at:at + 4] = b'moov'
        self.assertEqual(bytes(data[:len(original)]), original)
        cleanup = self.service.cleanup.status(job_id); self.assertEqual(cleanup['state'], 'completed', cleanup)
        self.assertEqual(cleanup['removed'], 1); self.assertEqual(cleanup['recovery']['state'], 'deleted', cleanup)
        self.assertFalse(cleanup['restore_available'])
        status = self.service.state(); self.assertEqual(status['converted_total'], 1, status)
        self.assertEqual(self.service.reviews.page(status='converted')['total'], 1)
        with connect_db(self.inv.database) as db:
            self.assertEqual(db.execute("SELECT state FROM inplace_edits").fetchall(), [('published',)])
            self.assertEqual(db.execute("SELECT state FROM source_retirements").fetchall(), [('removed',)])
            # Senua 0.21.0 F20: cleanup retired the book through the rename's own receipt, not by proving the move again
            # (a second full read of the output over the share, and a recovered receipt in place of the native one).
            receipt = json.loads(db.execute('SELECT detail FROM inplace_edits').fetchone()[0])['rename']
        self.assertEqual((proved, receipt['schema']), ([], 'books-native-no-copy-rename-v1'))
        self.service.close(); self.service = MergeService(self.inv, self.base / 'cache')
        self.assertEqual(self.service.jobs.status()['completed'], 1)

    def test_rename_postcondition_error_still_completes_source_cleanup(self):
        # Senua 0.21.0 F2 / Futaba M1 repro A: the OS renamed the book, then its postcondition proof raised, so no receipt was
        # journaled. The book completes and its cleanup proves the move itself instead of refusing forever.
        from public_research import PublicResearch
        real = native_io.rename_no_replace
        def unproved(*args, **kwargs):
            real(*args, **kwargs); raise native_io.RenamePostconditionError('OS rename accepted; postcondition unproved (simulated)')
        row = self.service.reviews.page()['rows'][0]; result = PublicResearch(self.client).lookup(row, str(self.audio))
        with patch('native_io.rename_no_replace', side_effect=unproved):
            fresh, job_id = self.service.approve_automatic(row, result, threading.Event(), self.client); self.wait()
        job = self.service.jobs.status()['jobs'][0]; self.assertEqual(job['state'], 'completed', job); self.assertFalse(self.source.exists())
        cleanup = self.service.cleanup.status(job_id); self.assertEqual(cleanup['state'], 'completed', cleanup); self.assertEqual(cleanup['removed'], 1)
        with connect_db(self.inv.database) as db:
            state, detail = db.execute('SELECT state, detail FROM inplace_edits').fetchone(); detail = json.loads(detail)
            self.assertEqual(state, 'published'); self.assertIn('postcondition', detail); self.assertTrue(detail['rename']['old_absent'])
            self.assertEqual(db.execute("SELECT state FROM source_retirements").fetchall(), [('removed',)])
        self.assertEqual(self.service.state()['converted_total'], 1)


@contextlib.contextmanager
def connect_db(path):
    with contextlib.closing(sqlite3.connect(path)) as db:yield db


if __name__ == '__main__':
    unittest.main()
