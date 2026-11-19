"""0.30.0 item C (Sergei 2026-11-18; Judy's spec section 9): a damaged M4B part is repaired before it is joined, in a manual
conversion and in an automatic one, with the proven repair the Repair action uses (m4b_preservation.plan with the repair kinds,
streamed to a working copy, re-read byte for byte, the silence repair's decode proof). The original is only read. A last chapter
that runs past its audio in a damaged part, which the strict chapter check refused, is repaired first; a part no repair applies to
stops the conversion with its name, and the original is kept.

Real private media (FFmpeg-made parts, damaged here), the real manual conversion service and pipeline; no library, no network."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

import audio_jobs
import audio_pipeline as pipeline
import background_work
import m4b_preservation
import m4b_repair

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'damaged-part-repair'
FFMPEG = shutil.which('ffmpeg')


def make_part(path, work, *, frequency=997, terminal=False):
    """A two-second AAC .m4b part with two chapters (First, Last). terminal: its last chapter runs far past its audio, as in
    test_terminal_chapters' native fixture (only the final text sample's duration and the text clocks change)."""
    work.mkdir(parents=True, exist_ok=True)
    chapters = work / (uuid.uuid4().hex + '.txt')
    chapters.write_text(';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=750\ntitle=First\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=750\nEND=2000\ntitle=Last\n', encoding='utf-8')
    subprocess.run([FFMPEG, '-hide_banner', '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i', f'sine=frequency={frequency}:sample_rate=44100:duration=2',
                    '-f', 'ffmetadata', '-i', str(chapters), '-map', '0:a:0', '-map_chapters', '1', '-c:a', 'aac', '-b:a', '64000',
                    '-metadata', 'album=Впусти меня', '-metadata', 'artist=Линдквист Йон Айвиде',
                    '-movflags', '+faststart+disable_chpl', str(path)], check=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    chapters.unlink()
    if terminal:
        data = bytearray(path.read_bytes())
        boxes = m4b_preservation.boxes
        movie = next(b for b in boxes(bytes(data)) if b.kind == b'moov')
        parts = boxes(movie.payload)
        movie_scale = int.from_bytes(next(b for b in parts if b.kind == b'mvhd').payload[12:16], 'big')
        for track in parts:
            if track.kind != b'trak':
                continue
            track_parts = boxes(track.payload)
            media = next(b for b in track_parts if b.kind == b'mdia')
            media_parts = boxes(media.payload)
            if next(b for b in media_parts if b.kind == b'hdlr').payload[8:12] != b'text':
                continue
            mdhd = next(b for b in media_parts if b.kind == b'mdhd')
            stbl = next(b for b in boxes(next(b for b in media_parts if b.kind == b'minf').payload) if b.kind == b'stbl')
            minf = next(b for b in media_parts if b.kind == b'minf')
            stts = next(b for b in boxes(stbl.payload) if b.kind == b'stts')
            media_base = movie.start + movie.header + track.start + track.header + media.start + media.header
            timing = media_base + minf.start + minf.header + stbl.start + stbl.header + stts.start + stts.header
            old = int.from_bytes(stts.payload[-4:], 'big'); new = 1_800_000_000
            struct.pack_into('>I', data, timing + len(stts.payload) - 4, new)
            duration = int.from_bytes(mdhd.payload[16:20], 'big') + new - old
            struct.pack_into('>I', data, media_base + mdhd.start + mdhd.header + 16, duration)
            presentation = duration * movie_scale // int.from_bytes(mdhd.payload[12:16], 'big')
            base = movie.start + movie.header + track.start + track.header
            tkhd = next(b for b in track_parts if b.kind == b'tkhd'); edts = next(b for b in track_parts if b.kind == b'edts')
            elst = next(b for b in boxes(edts.payload) if b.kind == b'elst')
            struct.pack_into('>I', data, base + tkhd.start + tkhd.header + 20, presentation)
            struct.pack_into('>I', data, base + edts.start + edts.header + elst.start + elst.header + 8, presentation)
            break
        else:
            raise AssertionError('The generated part has no QuickTime text chapter track')
        path.write_bytes(bytes(data))
    return path


def truncate(path, count=2):
    """The file ends early inside its last audio frame (a cut download)."""
    data = path.read_bytes(); path.write_bytes(data[:-count])


def corrupt(path):
    """Garbage over audio frames in the middle of the media data: no container repair applies."""
    data = bytearray(path.read_bytes())
    mdat = next(b for b in m4b_preservation.boxes(bytes(data)) if b.kind == b'mdat')
    middle = mdat.start + mdat.header + (mdat.size - mdat.header) // 2
    data[middle:middle + 1024] = b'\xff' * 1024
    path.write_bytes(bytes(data))


def facts(path):
    stat = path.stat()
    return hashlib.sha256(path.read_bytes()).hexdigest(), stat.st_size, stat.st_mtime_ns


@unittest.skipUnless(os.name == 'nt' and FFMPEG and shutil.which('ffprobe'), 'Windows and FFmpeg required')
class DamagedPartTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.work = self.root / 'work'
        self.stop = threading.Event()

    def manual_service(self):
        from merge_service import MergeService
        from scanner import Inventory
        self.source = self.root / 'source'
        self.output = self.root / 'chosen'; self.output.mkdir()
        roots = {label: str(path) for label, path in [('Audiobooks', self.source), ('Podcasts', self.root / 'podcasts'), ('Ebooks', self.root / 'ebooks')]}
        self.inventory = Inventory(self.root / 'data' / 'catalog.sqlite3', roots)
        self.service = MergeService(self.inventory, self.root / 'data' / 'cache')
        self.addCleanup(self.service.close)
        return self.service.manual_conversions

    def queue_folder(self, manual, folder):
        pick = manual.inspect({'kind': 'folder', 'path': str(folder)})
        request = {'id': str(uuid.uuid4()), 'revision': 0, 'source': pick['source'], 'tracks': pick['tracks'], 'inspections': pick['inspections'],
                   'metadata': {'title': 'Впусти меня', 'author': 'Линдквист Йон Айвиде'}, 'destination': str(self.output / 'Впусти меня.m4b')}
        with patch.object(self.service, 'resume'):
            return manual.queue(request)['draft']

    def run_queue(self):
        self.service.resume()
        deadline = time.monotonic() + 240
        while self.service.jobs._thread and self.service.jobs._thread.is_alive() and time.monotonic() < deadline:
            self.service.jobs._thread.join(.2)
        self.assertTrue(self.service.drained())

    def test_a_damaged_part_whose_last_chapter_runs_past_its_audio_is_repaired_on_a_copy_and_joined(self):
        manual = self.manual_service()
        folder = self.source / 'Линдквист' / 'Впусти меня'; folder.mkdir(parents=True)
        first = make_part(folder / 'Впусти меня 1.m4b', self.work, frequency=440)
        second = make_part(folder / 'Впусти меня 2.m4b', self.work, frequency=660, terminal=True)
        truncate(second)
        # The fixture is the reported case: the strict chapter check refuses the part, and the proven repair applies.
        raw = pipeline.probe(second, self.root, self.stop)
        duration = float(raw['format']['duration'])
        with self.assertRaises(pipeline.ValidationError):
            pipeline.verified_source_chapters(second, self.root, self.stop, duration)
        diagnosis = m4b_repair.diagnose_path(second)
        self.assertEqual(diagnosis['state'], 'repairable', diagnosis)
        self.assertIn(m4b_preservation.REPAIR_TRUNCATED_FRAMES, [item['kind'] for item in diagnosis['repairs']])
        before = {path.name: facts(path) for path in (first, second)}
        queued = self.queue_folder(manual, folder)  # positive control: refused here before 0.30.0 (the chapter check)
        self.assertEqual(queued['state'], 'queued')
        self.assertFalse([p for p in (self.root / 'data' / 'cache').rglob('*') if 'part-repair' in p.name], 'the plan check leaves no working copy behind')
        seen = {}
        completed = self.service.jobs.after_completed
        def at_completion(job_id):
            seen.update({path.name: facts(path) for path in (first, second)})
            seen['listing'] = sorted(path.name for path in folder.iterdir())
            return completed(job_id)
        with patch.object(self.service.jobs, 'after_completed', side_effect=at_completion):
            self.run_queue()
        draft = manual.list()['drafts'][0]
        self.assertEqual(draft['state'], 'converted', draft)
        self.assertEqual({name: seen[name] for name in before}, before, 'the originals are only read: same bytes, size and time')
        self.assertEqual(seen['listing'], sorted(before), 'no working copy beside the originals')
        self.assertEqual(draft['repaired_parts'], 1)
        job = next(job for job in self.service.jobs.status()['jobs'] if job['job_id'] == queued['job_id'])
        repairs = [item for item in job['output']['validation']['source_working_repairs'] if item.get('kind') == 'm4b_part_repair']
        self.assertEqual([(item['file'], item['source_index'], item['source_sha256']) for item in repairs], [(second.name, 1, before[second.name][0])])
        self.assertIn(m4b_preservation.REPAIR_TRUNCATED_FRAMES, [item['kind'] for item in repairs[0]['repairs']])
        self.assertTrue(repairs[0]['silence_proof'], 'the silence repair kept its decode proof')
        self.assertEqual(audio_jobs.repair_record(job)['applied'], True, "the book's Repaired list")
        self.assertIn('truncated_final_frames', [item['kind'] for item in audio_jobs.repair_record(job)['patched']])
        output = pipeline.probe(Path(queued['destination']), self.root, self.stop)
        self.assertEqual([c['tags']['title'] for c in output['chapters']], ['First', 'Last', 'First', 'Last'])

    def test_a_part_no_repair_applies_to_stops_with_its_name_and_the_original_kept(self):
        manual = self.manual_service()
        folder = self.source / 'Линдквист' / 'Впусти меня'; folder.mkdir(parents=True)
        first = make_part(folder / 'Впусти меня 1.m4b', self.work, frequency=440)
        second = make_part(folder / 'Впусти меня 3.m4b', self.work, frequency=660)
        corrupt(second)
        self.assertEqual(m4b_repair.diagnose_path(second)['state'], 'intact', 'the container is whole: no repair applies')
        before = {path.name: facts(path) for path in (first, second)}
        queued = self.queue_folder(manual, folder)
        self.run_queue()
        draft = manual.list()['drafts'][0]
        self.assertEqual(draft['state'], 'failed', draft)
        self.assertEqual(draft.get('part_repair'), {'kind': 'unrepairable', 'file': second.name}, draft)
        self.assertTrue(draft['originals_untouched'])
        self.assertEqual({path.name: facts(path) for path in (first, second)}, before)
        self.assertTrue(draft['reopen_allowed'])
        self.assertFalse(draft['retry_allowed'], 'the same bytes stop the same way; Reopen draft replaces or leaves out the file')
        job = next(job for job in self.service.jobs.status()['jobs'] if job['job_id'] == queued['job_id'])
        failure = json.loads(self.service.jobs._rows('SELECT journal FROM audio_jobs WHERE job_id=?', (job['job_id'],))[0]['journal'])['failure']
        self.assertEqual(failure['part_repair']['kind'], 'unrepairable')
        self.assertFalse(failure['retryable'], 'never retried by the hour on its own')
        media = self.service.jobs.attention_summary([job['job_id']])[job['job_id']].get('media_failure')
        self.assertEqual((media['code'], media['filename']), ('m4b_part_unrepairable', second.name))
        self.assertEqual(media['hint'], second.name + " is damaged and can't be repaired safely. Replace it with an intact copy.")

    def joined(self, damaged, *, terminal=True):
        """A joined-book manifest over private parts (as test_terminal_chapters' join), the second part damaged."""
        from encoding_policy import AUTOMATIC_PROFILE, freeze_automatic_policy
        folder = self.root / 'library' / 'Впусти меня'; folder.mkdir(parents=True)
        parts = [make_part(folder / 'Впусти меня 1.m4b', self.work, frequency=440), make_part(folder / 'Впусти меня 2.m4b', self.work, frequency=660, terminal=terminal)]
        damaged(parts[1])
        cover = self.root / 'cover.png'
        pipeline.run_owned([FFMPEG, '-hide_banner', '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i', 'color=c=blue:s=32x32:d=0.04', '-frames:v', '1', '-threads', '1', str(cover)],
                           self.root, self.stop, 30)
        sources = [{'path': str(p), 'sha256': pipeline.digest(p), **pipeline.fingerprint(p), 'metadata': {'tags': {}}} for p in parts]
        plans = [pipeline.part_chapter_plan(Path(item['path']), self.root, self.stop, float(pipeline.probe(Path(item['path']), self.root, self.stop)['format']['duration']), source=item)
                 for item in sources]
        manifest = {'job_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1, 'root': str(self.root / 'library'),
                    'destination': str(self.root / 'library' / 'final.m4b'), 'profile': AUTOMATIC_PROFILE, 'encoding_policy': freeze_automatic_policy(sources),
                    'sources': sources, 'cover': {'path': str(cover), 'sha256': pipeline.digest(cover)}, 'comments': '', 'chapters': [],
                    'part_chapters': [{'name': str(i), 'chapters': plan['chapters']} for i, plan in enumerate(plans)],
                    'metadata': {'title': 'Впусти меня', 'canonical_author': 'Линдквист Йон Айвиде'}}
        return manifest, parts

    def test_the_pipeline_reports_the_repair_step_in_parts_and_an_automatic_join_succeeds(self):
        manifest, parts = self.joined(truncate)
        before = facts(parts[1]); reports = []
        output, validation = pipeline.create_private(manifest, self.root / 'stage', self.stop, progress=lambda stage, info: reports.append((stage, json.loads(json.dumps(info)))))
        self.assertEqual(facts(parts[1]), before)
        measures = [info['progress'] for stage, info in reports if isinstance(info.get('progress'), dict) and info['progress'].get('phase') == 'repairing']
        self.assertTrue(measures, 'the repair is reported as its own measured step')
        self.assertTrue(all(stage == 'Checking sources' for stage, info in reports if (info.get('progress') or {}).get('phase') == 'repairing'))
        self.assertEqual({(m['unit'], m['total'], m['file']) for m in measures}, {('parts', 1, parts[1].name)})
        self.assertEqual((measures[0]['completed'], measures[-1]['completed']), (0, 1), 'done counts the parts repaired')
        self.assertEqual([c['title'] for c in validation['chapters']], ['First', 'Last', 'First', 'Last'])
        # The jobs panel reads the same measure: the audio_jobs checkpoint accepts it, the work row carries it.
        self.assertEqual(audio_jobs.MEASURED['checking sources']['repairing'], 'parts')

    def test_a_repaired_part_that_fails_its_check_stops_with_its_name(self):
        manifest, parts = self.joined(truncate, terminal=False)
        real = pipeline.decoded_duration
        def decode(path, *args, **kwargs):
            if Path(path).name.startswith('part-repair-'):
                raise pipeline.ValidationError('Full audio decode failed: fixture')
            return real(path, *args, **kwargs)
        with patch.object(pipeline, 'decoded_duration', side_effect=decode), self.assertRaises(pipeline.PartRepairError) as caught:
            pipeline.create_private(manifest, self.root / 'stage', self.stop)
        self.assertEqual({k: caught.exception.part_repair[k] for k in ('kind', 'file', 'source_index')}, {'kind': 'failed', 'file': parts[1].name, 'source_index': 1})
        details = audio_jobs._failure_details(caught.exception, 'checking sources')
        self.assertEqual(details['part_repair']['kind'], 'failed')

    def test_pause_during_a_repair_stops_it_and_the_book_restarts(self):
        manifest, parts = self.joined(truncate, terminal=False)
        stop = threading.Event()
        def tell(stage, info):
            if (info.get('progress') or {}).get('phase') == 'repairing':
                stop.set()
        with self.assertRaises(InterruptedError):
            pipeline.create_private(manifest, self.root / 'stage', stop, progress=tell)


class RepairRowTests(unittest.TestCase):
    def test_the_conversion_row_carries_the_repair_step_parts_and_the_file(self):
        AREA.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=AREA) as temp:
            import test_background_work as harness
            database = Path(temp) / 'catalog.sqlite3'
            with contextlib.closing(sqlite3.connect(database)) as db, db:
                db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT)')
                db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,evidence TEXT)')
                db.execute('INSERT INTO audio_jobs VALUES(?,?)', ('job-a', json.dumps({'candidate_id': 'book-a', 'metadata': {'title': 'Впусти меня'}}, ensure_ascii=False)))
            server = harness.SimpleNamespace(merge=harness.Engine(database), active_library='Audiobooks')
            for state in ('Running', 'Paused'):
                jobs = harness.jobs_state(state=state, current_job_id='job-a', current_book_id='book-a', current_title='Впусти меня',
                                          progress={'phase': 'repairing', 'completed': 1, 'total': 2, 'unit': 'parts', 'file': 'Впусти меня 3.m4b', 'started': 500})
                work = background_work.view(server, jobs, {'state': 'Idle'}, {'queued_actions': [], 'queue_running': None}, False, None, None, None, 1000)
                row = work['rows'][0]
                self.assertEqual((row['kind'], row['step'], row['done'], row['total'], row['unit'], row['step_text'], row['state']),
                                 ('conversion', 'repairing', 1, 2, 'parts', 'Впусти меня 3.m4b', state.lower()))


if __name__ == '__main__':
    unittest.main()
