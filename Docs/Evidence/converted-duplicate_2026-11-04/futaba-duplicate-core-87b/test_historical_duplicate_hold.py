"""Private QA: an old same-generation hold passes through normal Start."""
import json
import threading
from pathlib import Path
from unittest.mock import patch

from scanner import Inventory, connect
from scan_wait import finish_scan
from merge_service import MergeService
from public_research import PublicResearch
from test_automatic_media import AutomaticMediaTests


class HistoricalDuplicateHoldQA(AutomaticMediaTests):
    def test_old_hold_start_admits_child_without_parent_publication(self):
        self.service.close()
        roots = {'Audiobooks': str(self.audio), 'Podcasts': str(self.base / 'podcasts'),
                 'Ebooks': str(self.base / 'ebooks')}
        sorted_root = self.base / 'Sorted'
        sorted_root.mkdir()
        self.inv = Inventory(self.base / 'catalog.sqlite3', roots, output_root=str(sorted_root))
        self.inv.launch('Audiobooks')
        finish_scan(self.inv)
        self.service = MergeService(self.inv, self.base / 'cache')
        self.service.automatic.research = PublicResearch(self.client)

        originals = [source.read_bytes() for source in self.sources]
        row, result = self.result()
        _, parent_id = self.service.approve_automatic(row, result, threading.Event(), self.client)
        self.wait()
        parent = next(job for job in self.service.jobs.status()['jobs'] if job['job_id'] == parent_id)
        self.assertEqual(parent['state'], 'completed', parent)
        final = Path(parent['output']['final_path'])
        output_bytes = final.read_bytes()
        with connect(self.inv.database) as db:
            parent_before = dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (parent_id,)).fetchone())

        extra = self.audio / 'Extra e\u0301'
        extra.mkdir()
        duplicate = []
        for index, data in enumerate(originals, 1):
            source = extra / (str(index).zfill(2) + '.mp3')
            source.write_bytes(data)
            duplicate.append(source)
        self.inv.launch('Audiobooks')
        finish_scan(self.inv)
        current = next(row for row in self.service.reviews.page()['rows']
                       if any(member['path'] == str(duplicate[0]) for member in row['members']))

        old_reason = 'Identical verified recording already arranged \u2014 duplicate sources preserved'
        self.service.automatic._record(current, 'Held', {'reasons': [old_reason], 'until_change': True})
        with connect(self.inv.database) as db:
            saved = db.execute('SELECT result FROM automatic_candidates WHERE id=?', (current['id'],)).fetchone()
            prior = json.loads(saved['result'])
            prior.pop('duplicate_cleanup_policy')
            db.execute('UPDATE automatic_candidates SET result=? WHERE id=?', (json.dumps(prior), current['id']))
        initial = self.service.automatic.candidate(current)
        self.assertEqual(initial['state'], 'Held')
        self.assertTrue(initial['until_change'])
        self.assertIsNone(initial['duplicate_cleanup_policy'])

        with patch.object(self.service, '_run_media', side_effect=AssertionError('No second conversion')):
            self.service.automatic.start()
            self.service.automatic.thread.join(90)
            self.assertFalse(self.service.automatic.thread.is_alive(), 'Automatic Start did not finish')
            self.wait()
        self.assertEqual(self.service.automatic.status()['state'], 'Completed')
        child = next(job for job in self.service.jobs.status()['jobs']
                     if job['job_id'] != parent_id and job['manifest'].get('task_kind') == 'duplicate_source_cleanup')
        self.assertEqual(child['state'], 'completed', child)
        self.assertEqual(self.service.cleanup.status(child['job_id'])['removed'], 2)
        self.assertTrue(all(not source.exists() for source in duplicate))
        self.assertEqual(final.read_bytes(), output_bytes)
        with connect(self.inv.database) as db:
            self.assertEqual(dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (parent_id,)).fetchone()), parent_before)
        self.assertEqual(self.service.state()['converted_total'], 1)
