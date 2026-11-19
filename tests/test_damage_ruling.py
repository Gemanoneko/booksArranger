"""Sergei's ruling on damaged parts (2026-11-19), on top of 0.30.0 item C.

1. A damaged file the app can't repair, whose damage blocks conversion or whose audio is damaged: the row tells him plainly to
   re-acquire the book; no Retry.
2. Damage that doesn't block conversion, with the audio intact (container or metadata damage the app works around): the file is
   not treated as damaged: no damaged label, no hold, no Repair prompt; it converts normally. The audio is proven intact by full
   strict decodes, never assumed.

Each damage shape the app knows is made here on real FFmpeg-made private parts and classified: container-only (a dangling
chapter reference, a final mdat declaring bytes past the end, an understated final mdat) or audio damage (the file cut inside
its last frames). Real pipeline, real ledger rows; no library, no network."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

import audio_jobs
import audio_pipeline as pipeline
import m4b_preservation
import m4b_repair
from test_damaged_part_repair import FFMPEG, make_part, truncate, corrupt, facts
from test_m4b_preservation import relocate, edit, is_audio, atom

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'damage-ruling'


def dangling(path):
    """The audio track's chapter list also names a track that does not exist (track 99): only movie-box bytes change."""
    data = path.read_bytes()
    top = m4b_preservation.boxes(data)
    old = next(box for box in top if box.kind == b'moov')
    movie = atom(b'moov', edit(old.payload, [b'trak', b'tref', b'chap'], lambda payload: payload + struct.pack('>I', 99), where=is_audio))
    movie = relocate(movie, len(movie) - len(old.raw))
    path.write_bytes(b''.join(movie if box is old else box.raw for box in top))


def overrun(path, missing=8):
    """The final mdat declares `missing` bytes past the end of the file; no sample uses them."""
    data = bytearray(path.read_bytes())
    mdat = [box for box in m4b_preservation.boxes(bytes(data)) if box.kind == b'mdat'][-1]
    assert mdat.header == 8 and mdat.start + mdat.size == len(data)
    struct.pack_into('>I', data, mdat.start, mdat.size + missing)
    path.write_bytes(bytes(data))


def understated(path, short=32):
    """The final mdat's size field ends `short` bytes early; those bytes are the final audio frame's own bytes."""
    data = bytearray(path.read_bytes())
    mdat = [box for box in m4b_preservation.boxes(bytes(data)) if box.kind == b'mdat'][-1]
    assert mdat.header == 8 and mdat.start + mdat.size == len(data)
    struct.pack_into('>I', data, mdat.start, mdat.size - short)
    path.write_bytes(bytes(data))


CONTAINER = {'dangling_chapter_reference': dangling, 'mdat_tail_overrun': overrun, 'mdat_size_understated': understated}


@unittest.skipUnless(os.name == 'nt' and FFMPEG and shutil.which('ffprobe'), 'Windows and FFmpeg required')
class DamageRulingMediaTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.work = self.root / 'work'
        self.stop = threading.Event()

    def part(self, name, damage=None, **options):
        folder = self.root / 'library' / 'Впусти меня'; folder.mkdir(parents=True, exist_ok=True)
        path = make_part(folder / name, self.work, **options)
        if damage:
            damage(path)
        return path

    def cover(self):
        cover = self.root / 'cover.png'
        if not cover.exists():
            pipeline.run_owned([FFMPEG, '-hide_banner', '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i', 'color=c=blue:s=32x32:d=0.04', '-frames:v', '1', '-threads', '1',
                                str(cover)], self.root, self.stop, 30)
        return {'path': str(cover), 'sha256': pipeline.digest(cover)}

    def manifest(self, paths, part_chapters=None):
        from encoding_policy import AUTOMATIC_PROFILE, freeze_automatic_policy
        sources = [{'path': str(p), 'sha256': pipeline.digest(p), **pipeline.fingerprint(p), 'metadata': {'tags': {}}} for p in paths]
        value = {'job_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1, 'root': str(self.root / 'library'),
                 'destination': str(self.root / 'library' / 'final.m4b'), 'profile': AUTOMATIC_PROFILE, 'encoding_policy': freeze_automatic_policy(sources),
                 'sources': sources, 'cover': self.cover(), 'comments': '', 'chapters': [],
                 'metadata': {'title': 'Впусти меня', 'canonical_author': 'Линдквист Йон Айвиде'}}
        if len(paths) == 1:
            duration = float(pipeline.probe(Path(paths[0]), self.root, self.stop)['format']['duration'])
            value['source_chapters'] = pipeline.source_chapters(Path(paths[0]), self.root, self.stop, duration)
        else:
            plans = [pipeline.part_chapter_plan(Path(item['path']), self.root, self.stop, float(pipeline.probe(Path(item['path']), self.root, self.stop)['format']['duration']),
                                                source=item) for item in sources]
            value['part_chapters'] = [{'name': str(i), 'chapters': plan['chapters'], **({'repaired_terminal': True} if plan.get('repaired_terminal') else {})} for i, plan in enumerate(plans)]
        return value

    def test_every_known_shape_is_classified_and_the_container_ones_decode_intact(self):
        # Container-only: the diagnosis names only container kinds, and the damaged original itself decodes completely.
        for kind, damage in CONTAINER.items():
            path = self.part(kind + '.m4b', damage)
            diagnosis = m4b_repair.diagnose_path(path)
            self.assertEqual((diagnosis['state'], [item['kind'] for item in diagnosis['repairs']]), ('repairable', [kind]), kind)
            self.assertTrue(m4b_repair.container_only(diagnosis), kind)
            pipeline.decoded_duration(path, self.root, self.stop, 2)  # a full strict decode of the damaged original: the audio reads
        # Audio damage: the file is cut inside its last frame; the repair replaces it with silence. Repairable, never container-only.
        cut = self.part('cut.m4b', truncate)
        diagnosis = m4b_repair.diagnose_path(cut)
        self.assertEqual([item['kind'] for item in diagnosis['repairs']], [m4b_preservation.REPAIR_TRUNCATED_FRAMES])
        self.assertFalse(m4b_repair.container_only(diagnosis))
        # Can't repair: frames overwritten in the middle; the container is whole, so no repair applies, and the decode fails.
        broken = self.part('broken.m4b', corrupt)
        self.assertEqual(m4b_repair.diagnose_path(broken)['state'], 'intact')
        with self.assertRaises(pipeline.ValidationError):
            pipeline.decoded_duration(broken, self.root, self.stop, 2)
        self.assertFalse(m4b_repair.container_only({'state': 'repairable', 'repairs': [{'kind': 'dangling_chapter_reference'}, {'kind': 'truncated_final_frames'}]}),
                         'any audio damage makes the whole file damaged')

    def test_a_single_file_with_container_only_damage_converts_normally_with_its_audio_proven(self):
        for kind, damage in CONTAINER.items():
            with self.subTest(kind=kind):
                path = self.part(kind + '-single.m4b', damage)
                before = facts(path)
                manifest = self.manifest([path])
                # Positive control: before the ruling this stopped as "M4B preservation requires review" (a Repair row).
                output, validation = pipeline.create_private(manifest, self.root / ('stage-' + kind), self.stop)
                self.assertEqual(facts(path), before, 'the original is only read')
                self.assertNotIn('damage_repair', validation, 'no damage label')
                fix = validation['container_fix']
                self.assertEqual([item['kind'] for item in fix['repairs']], [kind])
                encoding = validation['encoding']
                self.assertEqual(fix['audio_intact']['native_pcm'], pipeline.native_pcm_evidence(path, self.root, self.stop, 2, encoding),
                                 'the output decodes to exactly the original audio')
                self.assertEqual(fix['audio_intact']['packets']['packet_count'], fix['audio_intact']['samples'])

    def test_a_join_fixes_a_container_only_part_quietly_and_still_repairs_audio_damage_as_before(self):
        first = self.part('Впусти меня 1.m4b', frequency=440)
        second = self.part('Впусти меня 2.m4b', overrun, frequency=660)
        third = self.part('Впусти меня 3.m4b', truncate, frequency=880)
        manifest = self.manifest([first, second, third]); reports = []
        before = {p.name: facts(p) for p in (first, second, third)}
        output, validation = pipeline.create_private(manifest, self.root / 'stage', self.stop, progress=lambda stage, info: reports.append(json.loads(json.dumps(info))))
        self.assertEqual({p.name: facts(p) for p in (first, second, third)}, before)
        measures = [info['progress'] for info in reports if (info.get('progress') or {}).get('phase') == 'repairing']
        self.assertEqual({(m['file'], m['total']) for m in measures}, {(third.name, 1)}, 'only the part with damaged audio is "Repairing a damaged part"')
        proofs = {item['file']: item for item in validation['source_working_repairs'] if item.get('kind') == 'm4b_part_repair'}
        self.assertTrue(proofs[second.name]['container_only']); self.assertEqual(proofs[second.name]['audio_intact']['packets']['packet_count'], proofs[second.name]['audio_intact']['samples'])
        self.assertFalse(proofs[third.name]['container_only'])
        record = audio_jobs.repair_record({'manifest': manifest, 'output': {'validation': validation}})
        self.assertEqual([item['kind'] for item in record['patched']], [m4b_preservation.REPAIR_TRUNCATED_FRAMES], 'the Repaired list names the audio repair only')
        self.assertEqual(record['parts'], 1)
        # A join whose only damage is container-only shows no Repaired list at all.
        quiet = self.manifest([first, second]); quiet['job_id'] = str(uuid.uuid4())
        _, quiet_validation = pipeline.create_private(quiet, self.root / 'stage-quiet', self.stop)
        self.assertIsNone(audio_jobs.repair_record({'manifest': quiet, 'output': {'validation': quiet_validation}}))

    def test_m5_the_plan_never_copies_a_damaged_part_and_the_conversion_repairs_it_once(self):
        # Senua's 0.30.0 review M5: part_chapter_plan made a full repaired copy on every call; build_manifest runs it up to four
        # times per book under group_lock (the converter's guard), and the attempt repaired the part again.
        first = self.part('Впусти меня 1.m4b', frequency=440)
        second = self.part('Впусти меня 2.m4b', lambda path: truncate(path), frequency=660, terminal=True)  # the reported case
        third = self.part('Впусти меня 3.m4b', overrun, frequency=880, terminal=True)  # container-only, last chapter past its audio
        real = pipeline._repair_part_copy; made = []
        def counted(source, workdir, *args, **kwargs):
            made.append((Path(source).name, Path(workdir).name))
            return real(source, workdir, *args, **kwargs)
        with patch.object(pipeline, '_repair_part_copy', side_effect=counted):
            plans = []
            for _ in range(4):  # the approval and the guard's rebuilds
                for path in (first, second, third):
                    duration = float(pipeline.probe(path, self.root, self.stop)['format']['duration'])
                    plans.append(pipeline.part_chapter_plan(path, self.root, self.stop, duration, source={'sha256': pipeline.digest(path), **pipeline.fingerprint(path)}))
            self.assertEqual(made, [], 'positive control: four copies of each damaged part before the fix')
            self.assertEqual([p.get('repaired_terminal') for p in plans[:3]], [None, True, True])
            self.assertEqual(plans[:3], plans[-3:], 'every rebuild gives the same plan (the guard compares them)')
            self.assertEqual([p for p in self.root.rglob('*') if p.name.startswith(pipeline.PART_REPAIR_PREFIX)], [], 'nothing left in the cache')
            manifest = self.manifest([first, second, third])
            output, validation = pipeline.create_private(manifest, self.root / 'stage', self.stop)
        self.assertEqual(sorted(name for name, _ in made), sorted([second.name, third.name]), 'one repair per damaged part, in the attempt')
        self.assertTrue(all(workdir != self.root.name for _, workdir in made), 'only in the attempt stage')
        self.assertEqual([c['title'] for c in validation['chapters']], ['First', 'Last'] * 3)
        corrected = {Path(item['source_path']).name for item in validation['terminal_end_corrections'] if item.get('repaired_part')}
        self.assertEqual(corrected, {second.name, third.name}, 'the last end is proven on each repaired copy')
        # A plan whose other boundaries differ from the repaired copy is still refused.
        broken = json.loads(json.dumps(manifest)); broken['job_id'] = str(uuid.uuid4())
        broken['part_chapters'][1]['chapters'][0]['title'] = 'Changed'
        with self.assertRaisesRegex(pipeline.ValidationError, 'Part chapters differ from the frozen plan'):
            pipeline.create_private(broken, self.root / 'stage-broken', self.stop)

    def test_a_container_fix_whose_audio_is_not_proven_intact_is_not_treated_as_undamaged(self):
        path = self.part('overrun-unproven.m4b', overrun)
        manifest = self.manifest([path])
        real = pipeline.native_pcm_evidence
        def decode(target, *args, **kwargs):
            value = real(target, *args, **kwargs)
            return value | {'sha256': '0' * 64} if Path(target).name == pipeline.PRESERVATION_CANDIDATE_NAME else value
        with patch.object(pipeline, 'native_pcm_evidence', side_effect=decode), self.assertRaisesRegex(pipeline.ValidationError, 'complete native decoded audio'):
            pipeline.create_private(manifest, self.root / 'stage', self.stop)


class DamageRulingRowTests(unittest.TestCase):
    """The rows: re-acquire wording for what the app can't repair; a row held before the ruling as "Damaged — can repair" whose
    damage is container-only becomes "ready to retry", and Retry takes the normal route (a new job), nothing starting by itself."""
    def setUp(self):
        import test_attention_repair as harness
        AREA.mkdir(parents=True, exist_ok=True)
        self.harness = harness
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(self.temp.cleanup)
        self.l = harness.Ledger(self.temp.name); self.addCleanup(self.l.jobs.close)
        from merge_service import MergeService
        patcher = patch.object(MergeService, '_check_repairs'); patcher.start(); self.addCleanup(patcher.stop)
        checks = patch.dict(audio_jobs.REPAIR_CHECKS); checks.start(); self.addCleanup(checks.stop)

    def service(self):
        return self.harness.Base.service(self)

    def test_unrepairable_damage_tells_him_to_reacquire(self):
        manifest = {'sources': [{'path': 'X:/a/1.m4b'}, {'path': 'X:/a/2.m4b'}]}
        journal = {'failure': {'stage': 'checking sources', 'part_repair': {'kind': 'unrepairable', 'source_index': 1, 'source_path': 'X:/a/2.m4b'}}}
        for kind in ('unrepairable', 'failed'):
            journal['failure']['part_repair']['kind'] = kind
            media = audio_jobs.media_failure({'output': None}, journal, manifest, 'other')
            self.assertEqual((media['status'], media['hint']), ('Need to reacquire', '2.m4b is damaged and cannot be repaired safely. Delete the book, then get a new copy.'), kind)
        single = {'sources': [{'path': 'X:/a/book.m4b'}]}
        media = audio_jobs.media_failure({'output': None, 'reason': 'Full audio decode failed: x'}, {'failure': {'stage': 'checking sources', 'exception_class': 'ValidationError'}}, single, 'other')
        self.assertEqual((media['code'], media['status'], media['hint']), ('invalid_m4b_source', 'Need to reacquire', 'book.m4b is damaged and cannot be repaired safely. Delete the book, then get a new copy.'))
        import manual_conversion
        self.assertFalse(manual_conversion.retry_offered({'failure': {'retryable': True, 'part_repair': {'kind': 'failed'}}}), 'no Retry')

    def test_a_held_container_only_row_is_ready_to_retry_and_retry_takes_the_normal_route(self):
        from test_m4b_preservation import TEXT_SOURCE, dangling as synthetic_dangling
        job_id, manifest = self.l.failed(self.harness.REFUSED, synthetic_dangling(TEXT_SOURCE(), [3, 2]))
        row = self.l.row(job_id)
        found = m4b_repair.check(row)  # the background check, read-only
        s = self.service()
        value = s.attention_summary()[job_id]
        # Positive control: before the ruling this row was group 'repair' ("Damaged — can repair") with a Repair offer.
        self.assertEqual((value['group'], value.get('retry')), ('retry', {'allowed': True, 'reason': ''}))
        self.assertTrue(m4b_repair.container_only(found), found)
        self.assertNotIn('damage', value); self.assertNotIn('repair', value); self.assertNotIn('media_failure', value)
        self.assertTrue(audio_jobs.container_fix_retry(row))
        result = s.retry_blocked_job('Audiobooks', manifest['candidate_id'], 1, job_id)
        self.assertEqual((result['accepted'], result['queued_next'], result['kind']), (True, True, 'retry'), 'queued as a Retry, never a Repair')
        self.assertEqual(self.l.count(), 1, 'nothing is admitted on the press')
        with patch.object(type(s), '_admit_new_retry', autospec=True, return_value={'requeued': True, 'job_id': 'child'}) as normal, \
                patch.object(type(s), '_repair_damaged_m4b', autospec=True) as repair:
            s._admit_m4b_readmission(job_id, 'retry')
        normal.assert_called_once(); repair.assert_not_called()
        # Audio damage keeps its Repair row.
        cut, _ = self.l.failed(self.harness.REFUSED, b'cut', name='cut')
        with patch.object(m4b_repair, 'classify', return_value={'state': 'repairable', 'reason': 'x', 'damage': ['d'], 'repairs': [{'kind': 'truncated_final_frames', 'description': 'd'}]}):
            self.assertEqual(s.attention_summary()[cut]['group'], 'repair')
            self.assertFalse(audio_jobs.container_fix_retry(self.l.row(cut)))


if __name__ == '__main__':
    unittest.main()
