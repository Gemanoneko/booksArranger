"""0.21.0 single-M4B in-place metadata edit: eligible path, fallbacks, crash recovery, audio-untouched proof.

Real AAC/ALAC fixtures through the installed FFmpeg; no decode is part of the edited path.
"""
import base64, contextlib, copy, hashlib, json, os, shutil, sqlite3, stat, tempfile, threading, time, unittest, uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import audio_pipeline as ap
import inplace_m4b
import m4b_preservation as mp
from audio_pipeline import create_private, digest, fingerprint, run_owned, source_chapters, ValidationError
from encoding_policy import AUTOMATIC_PROFILE, freeze_automatic_policy
from native_io import VerifiedFile

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'inplace-m4b-tests'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
CHAPTERS = ';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=700\ntitle=First\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=700\nEND=1500\ntitle=Second\n'


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

    def media(self, name='Book.m4b', codec='aac', cover=False, chapters=True):
        plain = self.root / ('plain-' + name); path = self.root / 'Unsorted' / name; path.parent.mkdir(exist_ok=True)
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

    def manifest(self, path, destination=None):
        cover = self.root / 'approved.png'
        if not cover.exists():cover.write_bytes(PNG)
        sources = [{'path': str(path), **fingerprint(path), 'sha256': digest(path), 'metadata': {'tags': {}}}]
        return {'job_id': str(uuid.uuid4()), 'attempt_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
                'root': str(self.root), 'output_root': str(self.root),
                'destination': str(destination or self.root / 'Sorted' / 'Writer John' / (path.stem + ' - John Writer.m4b')),
                'profile': AUTOMATIC_PROFILE, 'encoding_policy': freeze_automatic_policy(sources), 'sources': sources,
                'cover': {'path': str(cover), 'sha256': digest(cover), 'id': 'cover'}, 'comments': 'Original comment', 'chapters': [],
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

    def run_in_place(self, manifest):
        return create_private(manifest, self.root / 'stage', self.stop, in_place=self.session(manifest))

    def fake(self):
        return SimpleNamespace(_held_sources={}, _review_boundary=contextlib.nullcontext, _guard=lambda manifest: True,
                               _register=lambda *args: None)


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

    def test_publication_failure_before_rename_restores_original(self):
        source = self.media(); before = self.snapshot(source); manifest = self.manifest(source)
        edited, validation = self.run_in_place(manifest); fake = self.fake(); fake._guard = lambda manifest: False
        with self.assertRaisesRegex(ValueError, 'Candidate review changed'):
            published(fake, manifest, edited, validation, lambda *a: None)
        self.assertEqual(self.snapshot(source), before); self.assertFalse(Path(manifest['destination']).exists())
        self.assertEqual(self.rows()[0]['state'], 'rolled_back'); self.assertEqual(fake._held_sources, {})


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

    def crash(self, point, manifest):
        def fault(name, handle=None):
            if name == point:raise Crash(name)
        with patch('inplace_m4b._fault', side_effect=fault), self.assertRaises(Crash):self.run_in_place(manifest)

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

    def test_torn_type_patch_is_restored(self):
        source = self.media(); before = self.snapshot(source); manifest = self.manifest(source); self.crash('type_patched', manifest)
        intent = json.loads(self.rows()[0]['intent'])
        with open(source, 'r+b') as stream:stream.seek(intent['type_offset']); stream.write(b'frov')
        inplace_m4b.recover_all(self.database); self.assertEqual(self.snapshot(source), before)

    def test_crash_after_rename_is_recognized_as_moved(self):
        source = self.media(); manifest = self.manifest(source); edited, validation = self.run_in_place(manifest)
        published(self.fake(), manifest, edited, validation, lambda *a: None)
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:db.execute("UPDATE inplace_edits SET state='publishing'")
        self.assertEqual(inplace_m4b.recover_all(self.database)[0][0], 'published')

    def test_unprovable_original_stays_journaled_and_blocks_new_attempts(self):
        source = self.media(); manifest = self.manifest(source); audio = source.read_bytes().index(b'mdat') + 20
        def corrupted(name, handle=None):
            if name == 'checked':handle.write_at(audio, b'\x55')  # an audio byte changes under the edit
        with patch('inplace_m4b._fault', side_effect=corrupted), self.assertRaises(inplace_m4b.Unresolved):self.run_in_place(manifest)
        self.assertEqual(self.rows()[0]['state'], 'unresolved')
        with self.assertRaises(inplace_m4b.Unresolved):inplace_m4b.clear(self.database, manifest)
        self.assertEqual(self.rows()[0]['state'], 'unresolved')


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
        self.service.close(); self.service = MergeService(self.inv, self.base / 'cache')
        self.assertEqual(self.service.jobs.status()['completed'], 1)


@contextlib.contextmanager
def connect_db(path):
    with contextlib.closing(sqlite3.connect(path)) as db:yield db


if __name__ == '__main__':
    unittest.main()
