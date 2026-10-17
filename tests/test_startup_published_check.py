"""Startup never hashes published books before health; the deferred check keeps the old guarantees."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from audio_jobs import AudioJobs
from encoding_policy import PROFILE
import web_server

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'startup-published-check-tests'
AREA.mkdir(parents=True, exist_ok=True)


def manifest():
    return {'job_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
            'sources': [{'sha256': 'a' * 64, 'fingerprint': {}}], 'metadata': {}, 'destination': 'fixture',
            'profile': PROFILE, 'evidence': {}, 'cover': {}}


def record(job_id):
    return {'job_id': job_id, 'final_path': 'fixture.m4b', 'owned_temp': 'fixture.partial',
            'sha256': 'b' * 64, 'size': 1, 'validation': {'passed': True}}


class StartupPublishedCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.db = Path(self.temp.name) / 'db.sqlite3'
        seed = AudioJobs(self.db, None, lambda m: True, lambda r: True)
        self.completed, self.publishing, self.running = manifest(), manifest(), manifest()
        for item in (self.completed, self.publishing, self.running):
            seed.enqueue(item)
        seed._update(self.completed['job_id'], state='completed', stage='completed', output=json.dumps(record(self.completed['job_id'])))
        seed._update(self.publishing['job_id'], state='running', stage='publishing',
                     journal=json.dumps({'attempt_id': 'x', 'history': [], 'publication_intent': record(self.publishing['job_id'])}))
        seed._update(self.running['job_id'], state='running', stage='creating')
        seed.close()

    def tearDown(self):
        self.temp.cleanup()

    def states(self, queue):
        return {job['job_id']: (job['state'], job['reason']) for job in queue.status()['jobs']}

    def test_construction_settles_crashed_rows_without_hashing_published_books(self):
        checked = []
        queue = AudioJobs(self.db, None, lambda m: True, lambda r: checked.append(r['job_id']) or True)
        # Only the crash-interrupted publication is verified synchronously; the published book is not read.
        self.assertEqual(checked, [self.publishing['job_id']])
        states = self.states(queue)
        self.assertEqual(states[self.publishing['job_id']][0], 'completed')
        self.assertEqual(states[self.running['job_id']], ('pending', 'Interrupted book restarts on explicit resume'))
        self.assertEqual(states[self.completed['job_id']][0], 'completed')
        queue.close()

    def test_deferred_check_flags_a_changed_published_book_exactly_like_startup_did(self):
        valid = {self.publishing['job_id']}
        queue = AudioJobs(self.db, None, lambda m: True, lambda r: r['job_id'] in valid)
        queue.start_published_check(); queue._verifier.join(5)
        self.assertFalse(queue._verifier.is_alive())
        self.assertEqual(self.states(queue)[self.completed['job_id']],
                         ('needs attention', 'Recorded output is missing, changed, or failed validation'))
        queue.start_published_check()  # once per process
        self.assertFalse(queue._verifier.is_alive())
        queue.close()

    def test_deferred_check_never_writes_after_close(self):
        entered, release = threading.Event(), threading.Event()

        def slow(r):
            if r['job_id'] == self.completed['job_id']:
                entered.set(); release.wait(5)
                return False
            return True
        queue = AudioJobs(self.db, None, lambda m: True, slow)
        queue.start_published_check()
        self.assertTrue(entered.wait(5))
        queue.close(timeout=0.2)  # bounded: a book still being hashed never blocks Quit
        release.set(); queue._verifier.join(5)
        self.assertEqual(self.states(queue)[self.completed['job_id']][0], 'completed')

    def test_resume_takes_over_and_the_deferred_check_never_overwrites_it(self):
        entered, release = threading.Event(), threading.Event()
        calls = []

        def validator(r):
            calls.append(threading.current_thread().name)
            if threading.current_thread().name == 'BooksArrangerPublishedCheck':
                entered.set(); release.wait(5)
                return False  # stale verdict that must not land after resume
            return True
        queue = AudioJobs(self.db, None, lambda m: True, validator)
        queue.start_published_check()
        self.assertTrue(entered.wait(5))
        with patch.object(queue, '_work', lambda: None):
            queue.resume()  # verifies every published book itself, under the queue lock
        self.assertTrue(queue._verify_stop.is_set())
        release.set(); queue._verifier.join(5)
        self.assertEqual(self.states(queue)[self.completed['job_id']][0], 'completed')
        self.assertIn('MainThread', calls)
        queue.close()

    def test_a_row_changed_after_reading_is_never_overwritten(self):
        entered, release = threading.Event(), threading.Event()

        def slow(r):
            if r['job_id'] == self.completed['job_id']:
                entered.set(); release.wait(5)
                return False
            return True
        queue = AudioJobs(self.db, None, lambda m: True, slow)
        queue.start_published_check()
        self.assertTrue(entered.wait(5))
        queue._update(self.completed['job_id'], reason='changed by another owner')
        release.set(); queue._verifier.join(5)
        self.assertEqual(self.states(queue)[self.completed['job_id']], ('completed', 'changed by another owner'))
        queue.close()


class ServerWiringTests(unittest.TestCase):
    def test_server_starts_the_check_after_construction_and_health_is_immediate(self):
        started = threading.Event(); release = threading.Event()

        class FakeMerge:
            def __init__(self, inventory, cache):
                self.calls = []
            def start_retention(self, admission):
                self.calls.append('retention')
            def start_published_check(self):
                self.calls.append('published')
                threading.Thread(target=lambda: (started.set(), release.wait(5)), daemon=True).start()
            def close(self):
                self.calls.append('close')
        inventory = type('Inventory', (), {'database': str(AREA / 'unused.sqlite3')})()
        t = time.perf_counter()
        server = web_server.BrowserServer(('127.0.0.1', 0), inventory, FakeMerge)
        try:
            self.assertLess(time.perf_counter() - t, 2)
            self.assertEqual(server.merge.calls, ['retention', 'published'])
            self.assertTrue(started.wait(5))
            self.assertEqual(server.health()['application'], 'Books Arranger')
        finally:
            release.set(); server.server_close()


if __name__ == '__main__':
    unittest.main()
