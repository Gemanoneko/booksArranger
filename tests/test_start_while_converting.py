"""Ruling 34 (Sergei 2026-10-26, option A): Start automatic processing works while audiobooks convert. It used to refuse with
"Audiobook conversion is running. Pause audiobook jobs before starting automatic processing." Now the books already in the
catalog are researched at once, without a scan, and a fresh run's scan waits until conversion is idle (the run's
_idle_jobs rule, as before). T5. Private catalog, a conversion that "runs" until the test lets it end; no network."""
import tempfile, threading, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scan_wait import close_scan, finish_scan, finish_thread
from scanner import Inventory

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'start-while-converting-tests'
AREA.mkdir(parents=True, exist_ok=True)


class StartWhileConvertingTests(unittest.TestCase):
    def setUp(self):
        from merge_service import MergeService
        temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        roots = {name: str(base / name) for name in ('Audiobooks', 'Podcasts', 'Ebooks')}
        for path in roots.values():
            Path(path).mkdir()
        (base / 'sorted').mkdir()
        self.audio = Path(roots['Audiobooks'])
        for name in ('John Writer - A Book.mp3', 'Jane Author - B Book.mp3'):
            (self.audio / name).write_bytes(b'fixture only')
        self.inventory = Inventory(base / 'catalog.sqlite3', roots, self.read, output_root=str(base / 'sorted'))
        self.inventory.launch('Audiobooks'); finish_scan(self.inventory)
        self.merge = MergeService(self.inventory, base / 'cache')
        self.addCleanup(self.close)

    def close(self):
        automatic = self.merge.__dict__.get('automatic')
        if automatic is not None:
            automatic.close()
        close_scan(self.inventory)
        self.merge.close()

    @staticmethod
    def read(path, kind, stop):
        title = Path(path).stem.split(' - ')[1]
        return {'title': title, 'artist': 'Writer', 'tags': {'title': title, 'artist': 'Writer', 'album': title, 'track': '1'}, 'probe': {'format': {'duration': '1'}}}

    def test_t5_start_researches_at_once_while_converting_and_the_scan_waits_for_conversion_to_go_idle(self):
        from automatic_processing import AutomaticProcessing
        converting = threading.Event(); converting.set()
        real_state = self.merge.state
        jobs = lambda *a, **k: {'state': 'Running', 'queued': 1, 'cleanup_active': False} if converting.is_set() else real_state(*a, **k)
        researched, scans = [], []
        def lookup(row, root, stop, progress=None):
            researched.append((row['title_clue'], converting.is_set()))
            return {'reasons': ['Book identity uncertain'], 'sources': []}
        research = SimpleNamespace(client=SimpleNamespace(retry_wait=lambda wait: dict(wait)), lookup=lookup)
        automatic = AutomaticProcessing(self.merge, research)
        self.merge.automatic = automatic
        real_launch = self.inventory.launch
        def launch(*args, **kwargs):
            scans.append(converting.is_set()); return real_launch(*args, **kwargs)
        (self.audio / 'New Author - C Book.mp3').write_bytes(b'fixture only')  # arrives after the last scan
        with patch.object(self.merge, 'state', jobs), patch.object(self.merge, 'resume', lambda **kw: {}), patch.object(self.inventory, 'launch', launch):
            self.assertTrue(automatic.status(jobs=self.merge.state(), scanning=False)['can_start'], 'a running conversion no longer blocks Start')
            automatic.start()  # used to raise "Pause audiobook jobs before starting automatic processing."
            end = time.monotonic() + 30
            while time.monotonic() < end and len(researched) < 2:
                time.sleep(0.05)
            self.assertEqual(sorted(title for title, _ in researched[:2]), ['A Book', 'B Book'], 'the catalogued books are researched at once')
            self.assertTrue(all(during for _, during in researched[:2]), 'while the conversion runs')
            time.sleep(0.5)
            self.assertEqual(scans, [], 'no scan while the conversion runs')
            converting.clear()  # the conversion ends
            end = time.monotonic() + 30
            while time.monotonic() < end and not any(title == 'C Book' for title, _ in researched):
                time.sleep(0.05)
        automatic.stop(); finish_thread(automatic.thread, 'the automatic run')
        self.assertEqual(scans, [False], 'one scan, once conversion was idle')
        self.assertIn(('C Book', False), researched, 'the book the deferred scan found is researched in this run')


if __name__ == '__main__':
    unittest.main()
