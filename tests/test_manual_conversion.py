"""Manual conversion lifecycle with disposable, private source fixtures."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from merge_service import MergeService
from scanner import Inventory, connect
from scan_wait import finish_scan


AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'manual-conversion-20261111' / 'ender'


@unittest.skipUnless(os.name == 'nt' and shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Windows and FFmpeg required')
class ManualConversionTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.folder = self.source / 'Автор' / 'Сборник'
        self.nested = self.folder / 'nested'
        self.nested.mkdir(parents=True)
        self.output = self.root / 'chosen'
        self.output.mkdir()
        self.data = self.root / 'data'
        self.roots = {label: str(path) for label, path in [('Audiobooks', self.source), ('Podcasts', self.root / 'podcasts'), ('Ebooks', self.root / 'ebooks')]}
        self.first = self.media(self.folder / '2.mp3', 330)
        self.second = self.media(self.folder / '10.mp3', 440)
        self.unrelated = self.media(self.folder / '11.mp3', 550)
        self.other = self.media(self.nested / '1.mp3', 660)
        self.open()

    def media(self, path, frequency):
        subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i',
                        f'sine=frequency={frequency}:duration=0.7', '-c:a', 'libmp3lame', '-metadata',
                        'album=Collection', '-metadata', 'album_artist=Known Author', str(path)], check=True, timeout=20)
        return path

    def open(self):
        self.inventory = Inventory(self.data / 'catalog.sqlite3', self.roots)
        self.service = MergeService(self.inventory, self.data / 'cache')
        self.addCleanup(self.service.close)
        self.manual = self.service.manual_conversions

    def wait_worker(self):
        deadline = time.monotonic() + 75
        while self.service.jobs._thread and self.service.jobs._thread.is_alive() and time.monotonic() < deadline:
            self.service.jobs._thread.join(.15)
        self.assertTrue(self.service.drained())

    def request(self, source, tracks, name='chosen name.m4b'):
        return {'id': str(uuid.uuid4()), 'revision': 0, 'source': source, 'tracks': tracks,
                'metadata': {'title': 'A collection', 'author': 'Known Author', 'series': 'Saga', 'number': '2',
                             'universe': 'World', 'collection': 'Stories', 'anthology': True},
                'destination': str(self.output / name)}

    def fake_auto_job(self, paths, candidate=None):
        items = []
        for path in paths:
            stat = path.stat()
            fingerprint = {'size': stat.st_size, 'modified': str(stat.st_mtime_ns)}
            items.append(fingerprint | {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                        'fingerprint': fingerprint})
        manifest = {'job_id': str(uuid.uuid4()), 'candidate_id': candidate or str(uuid.uuid4()), 'candidate_revision': 1,
                    'sources': items, 'metadata': {}, 'destination': str(self.output / 'automatic.m4b'),
                    'profile': 'test', 'evidence': {}, 'cover': {}, 'root': str(self.source)}
        self.service.jobs.enqueue(manifest)
        return manifest

    def test_draft_order_metadata_reservation_discard_and_restart(self):
        pick = self.manual.inspect({'kind': 'folder', 'path': str(self.folder)})
        self.assertEqual([Path(track['path']).name for track in pick['tracks']], ['2.mp3', '10.mp3', '11.mp3'])
        self.assertEqual(pick['suggestions']['title'], 'Collection')
        self.assertEqual(pick['suggestions']['author'], 'Known Author')
        job = self.fake_auto_job([self.first])
        other = self.fake_auto_job([self.other])
        request = self.request(pick['source'], list(reversed(pick['tracks'])))
        request['metadata_touched'] = ['title', 'author']
        saved = self.manual.save(request)['draft']
        self.assertEqual(saved['metadata_touched'], ['author', 'title'])
        self.assertEqual(saved, self.manual.save(request)['draft'])
        self.assertEqual([row['job_id'] for row in self.service.jobs._pending_unreserved(None)], [other['job_id']])
        self.service.close()
        self.open()
        self.assertEqual(self.manual.list(), {'drafts': [saved]})
        with self.assertRaisesRegex(ValueError, 'reserved'):
            self.fake_auto_job([self.second])
        discard = {'id': saved['id'], 'revision': saved['revision']}
        self.assertEqual(self.manual.discard(discard), self.manual.discard(discard))
        self.assertEqual([row['job_id'] for row in self.service.jobs._pending_unreserved(job['job_id'])], [job['job_id']])

    def test_verified_export_exact_name_order_and_selected_originals_only(self):
        self.inventory.launch('Audiobooks')
        finish_scan(self.inventory)
        candidate = next(row for row in self.inventory.candidates('Audiobooks')['rows']
                         if any(item['path'] == str(self.first) for item in row['members']))
        automatic = self.fake_auto_job([self.first, self.unrelated], candidate['id'])
        pick = self.manual.inspect({'kind': 'files', 'paths': [str(self.first), str(self.second)]})
        request = self.request(pick['source'], list(reversed(pick['tracks'])))
        with patch.object(self.service, 'resume'):
            queued = self.manual.queue(request)['draft']
            self.assertEqual(queued['state'], 'queued')
        self.service.close()
        self.open()
        self.assertEqual(self.manual.queue(request)['draft']['job_id'], queued['job_id'])
        self.assertTrue(self.first.exists() and self.second.exists())
        seen = []
        run_storage = self.service.storage_cleanup.run

        def poll_before_storage(job_id):
            seen.append(self.manual.list()['drafts'][0]['state'])
            return run_storage(job_id)

        with patch.object(self.service.storage_cleanup, 'run', side_effect=poll_before_storage):
            self.service.resume()
            self.wait_worker()
        self.assertIn('cleanup', seen)
        snapshot = self.manual.list()['drafts'][0]
        self.assertEqual(snapshot['state'], 'converted', snapshot)
        self.assertFalse(self.first.exists() or self.second.exists())
        self.assertTrue(self.unrelated.exists() and self.other.exists())
        path = Path(request['destination'])
        probe = subprocess.run([shutil.which('ffprobe'), '-v', 'error', '-show_format', '-show_chapters',
                                '-of', 'json', str(path)], check=True, timeout=20, capture_output=True)
        output = json.loads(probe.stdout)
        self.assertEqual(output['format']['tags']['title'], 'A collection')
        self.assertIn('Universe: World', output['format']['tags']['comment'])
        self.assertIn('Collection: Stories', output['format']['tags']['comment'])
        self.assertEqual([chapter['tags']['title'] for chapter in output['chapters']], ['10', '2'])
        self.assertIn(request['id'], self.service.converted_ids(max_age=0))
        self.assertIn(request['id'], {row['id'] for row in self.service.reviews.page(100, 0, '', 'converted')['rows']})
        self.assertNotIn(automatic['job_id'], {job['job_id'] for job in self.service.jobs.status()['jobs']})
        with connect(self.inventory.database) as db:
            self.assertEqual({row[0] for row in db.execute('SELECT path FROM source_retirements WHERE job_id=?', (queued['job_id'],))},
                             {str(self.first), str(self.second)})

    def test_path_collision_and_running_overlap_leave_saved_draft_unchanged(self):
        pick = self.manual.inspect({'kind': 'files', 'paths': [str(self.first)]})
        request = self.request(pick['source'], pick['tracks'])
        job = self.fake_auto_job([self.first])
        self.assertEqual(self.service.jobs._claim(self.service.jobs._pending_unreserved(None)[0]), 'claimed')
        with self.assertRaisesRegex(ValueError, job['job_id']):
            self.manual.save(request)
        self.service.jobs._claimed = None
        saved = self.manual.save(request)['draft']
        request['revision'] = saved['revision']
        output = Path(request['destination'])
        output.write_bytes(b'existing private file')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.manual.queue(request)
        self.assertEqual(output.read_bytes(), b'existing private file')
        with self.assertRaisesRegex(ValueError, 'outside the source'):
            self.manual.queue(request | {'destination': str(self.folder / 'export.m4b')})
        self.assertEqual(self.manual.list(), {'drafts': [saved]})
        self.assertTrue(self.first.exists())

    def test_external_folder_and_blank_author_use_the_same_verified_cleanup(self):
        external = self.root / 'external'
        external.mkdir()
        original = self.media(external / 'Chapter.mp3', 220)
        pick = self.manual.inspect({'kind': 'folder', 'path': str(external)})
        request = self.request(pick['source'], pick['tracks'], 'external export.m4b')
        request['metadata']['author'] = ''
        draft = self.manual.queue(request)['draft']
        self.service.jobs._thread.join(60)
        self.assertFalse(self.service.jobs._thread.is_alive())
        self.assertFalse(original.exists(), self.manual.list())
        self.assertTrue(external.is_dir())
        self.assertIn(draft['candidate_id'], self.service.converted_ids(max_age=0))

    def late_collision(self):
        self.service.pause_work()
        pick = self.manual.inspect({'kind': 'files', 'paths': [str(self.first)]})
        request = self.request(pick['source'], pick['tracks'])
        queued = self.manual.queue(request)['draft']
        self.assertEqual(queued['state'], 'queued')
        path = Path(request['destination'])
        path.write_bytes(b'existing private output')
        self.service.resume()
        self.wait_worker()
        failed = self.manual.list()['drafts'][0]
        self.assertEqual(failed['state'], 'failed', failed)
        self.assertTrue(failed['retry_allowed'] and failed['reopen_allowed'], failed)
        self.assertTrue(self.first.exists())
        self.assertEqual(path.read_bytes(), b'existing private output')
        return request, failed, path

    def test_explicit_retry_runs_immediately_after_late_collision_clears(self):
        _, failed, path = self.late_collision()
        retry = {'id': failed['id'], 'revision': failed['revision']}
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.manual.retry(retry)
        path.rename(path.with_suffix('.existing'))  # only this owned fixture's sentinel
        self.manual.retry(retry)
        self.wait_worker()
        self.assertEqual(self.manual.list()['drafts'][0]['state'], 'converted')
        self.assertFalse(self.first.exists())
        self.assertEqual(path.with_suffix('.existing').read_bytes(), b'existing private output')

    def test_reopen_late_collision_reserves_inputs_and_allows_new_export(self):
        request, failed, path = self.late_collision()
        reopen = {'id': failed['id'], 'revision': failed['revision']}
        draft = self.manual.reopen(reopen)['draft']
        self.assertEqual(draft, self.manual.reopen(reopen)['draft'])
        self.assertEqual(draft['state'], 'draft')
        self.assertEqual(draft['revision'], failed['revision'] + 1)
        self.assertNotIn('job_id', draft)
        with self.assertRaisesRegex(ValueError, 'reserved'):
            self.fake_auto_job([self.first])
        request.update(revision=draft['revision'], destination=str(self.output / 'new.m4b'))
        new = self.manual.queue(request)['draft']
        self.wait_worker()
        self.assertNotEqual(new['job_id'], failed['job_id'])
        self.assertEqual(self.manual.list()['drafts'][0]['state'], 'converted')
        self.assertTrue(Path(request['destination']).exists())
        self.assertEqual(path.read_bytes(), b'existing private output')

    def test_scan_settlement_starts_manual_work_and_later_pause_wins(self):
        for path, pause in ((self.first, True), (self.second, False)):
            release = threading.Event()
            self.addCleanup(release.set)
            scan = threading.Thread(target=release.wait, args=(30,), daemon=True)
            self.inventory.worker = scan
            scan.start()
            pick = self.manual.inspect({'kind': 'files', 'paths': [str(path)]})
            request = self.request(pick['source'], pick['tracks'], f'{path.stem}.m4b')
            draft = self.manual.queue(request)['draft']
            self.assertEqual(draft['state'], 'queued')
            self.assertIn('scan', draft['reason'])
            if pause:
                self.service.pause_work()
            release.set()
            scan.join(3)
            deadline = time.monotonic() + 5
            while self.service.__dict__.get('_start_waiting') and time.monotonic() < deadline:
                time.sleep(.1)
            if pause:
                self.assertTrue(path.exists())
                self.assertEqual(self.manual.list()['drafts'][0]['state'], 'queued')
                self.service.resume()
            while not self.service.jobs._thread or not self.service.jobs._thread.is_alive():
                if Path(request['destination']).exists() or time.monotonic() >= deadline:
                    break
                time.sleep(.1)
            self.wait_worker()
            self.assertEqual(self.manual.list()['drafts'][0]['state'], 'converted')
