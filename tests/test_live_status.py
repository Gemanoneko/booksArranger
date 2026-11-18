"""0.30.0 (Sergei 2026-11-18: every running job visible, named, with a progress bar).

The jobs panel's conversion and cleanup rows came from the shared status computation, which a poll reuses until a newer one
ends: on a live-sized catalog one took about 19 s alone, and the panel lagged the queue by 24 s (median) to 36 s. Now the
running part of that answer (MergeService.LIVE_FIELDS) is read at every poll by live_jobs(), from the workers' memory and a
few small catalog reads; state() computes the same fields with the same function (_running), so the two cannot disagree.

Real MergeService over a private fixture catalog with real private audio (FFmpeg) and offline research. No library, no
network, no window."""
import os
import shutil
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import merge_service
import web_server
from scanner import connect
from test_approve_as_is import ApproveFixture, tone


@unittest.skipUnless(os.name == 'nt' and shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Windows and FFmpeg required')
class LiveStatusTests(ApproveFixture):
    def books(self, *titles):
        for title in titles:
            tone(self.audio / 'Unsorted' / title / '01.mp3', self.cover, album=title, artist='Иван Петров')
        return {Path(row['members'][0]['path']).parent.name: row for row in self.start()}

    def same(self, why):
        """live_jobs() gives exactly the LIVE_FIELDS of state(), with the same values."""
        full = self.service.state()
        live, _current = self.service.live_jobs()
        self.assertEqual(set(live), set(merge_service.MergeService.LIVE_FIELDS), why)
        self.assertEqual(live, {key: full[key] for key in live}, why)
        return live

    def cleanup_state(self, state, reason=''):
        with connect(self.inv.database) as db:
            db.execute('UPDATE source_cleanup SET state=?,reason=?', (state, reason))

    def test_the_live_read_says_what_the_full_status_computation_says(self):
        rows = self.books('Ясно', 'Книга 2')
        first, second = rows['Ясно'], rows['Книга 2']
        self.service.approve_book(first['id'], first['revision'], author='Петров Иван')
        live = self.same('one book approved, no Start yet')
        self.assertEqual((live['state'], live['queued'], live['queued_conversions'], live['cleanup_active']), ('Paused', 1, 1, False))
        self.start_and_wait()
        live = self.same('converted and cleaned up')
        self.assertEqual((live['state'], live['queued'], live['current_job_id']), ('Completed', 0, None))
        self.service.approve_book(second['id'], second['revision'], author='Петров Иван')
        # The first book's cleanup paused, waiting, then held, beside the second book waiting to convert.
        self.cleanup_state('paused')
        live = self.same('a paused cleanup beside a waiting book')
        self.assertEqual((live['state'], live['queued'], live['queued_conversions'], live['cleanups_paused'], live['cleanups_waiting']), ('Paused', 2, 1, 1, 0))
        self.assertEqual((live['current_title'], live['progress']['phase'], live['cleanup_active']), ('Ясно', 'originals', True))
        self.cleanup_state('waiting')
        live = self.same('a cleanup not started')
        self.assertEqual((live['cleanups_paused'], live['cleanups_waiting'], live['stage']), (0, 1, 'Waiting for output checks'))
        self.cleanup_state('needs_attention', 'The app could not read file information for Ясно.m4b')
        live = self.same('a held cleanup')
        self.assertEqual((live['attention_row']['title'], live['attention_row']['phase'], live['attention_row']['held_total']), ('Ясно', 'originals', 1))
        self.assertEqual(live['queued'], 1)
        self.cleanup_state('completed')
        self.same('nothing held')

    def test_a_poll_shows_the_running_conversion_while_the_shared_answer_is_still_old(self):
        rows = self.books('Ясно')
        book = rows['Ясно']
        self.service.approve_book(book['id'], book['revision'], author='Петров Иван')
        stale = self.service.state()  # the shared answer a poll would reuse while a newer computation runs
        self.assertEqual((stale['state'], stale['current_title']), ('Paused', ''), 'positive control: nothing runs in it')
        # The converter has claimed the book and is encoding it (its thread is a stand-in that waits).
        release = threading.Event(); self.addCleanup(release.set)
        worker = threading.Thread(target=release.wait, args=(30,), daemon=True); worker.start()
        with connect(self.inv.database) as db:
            job = db.execute("SELECT job_id FROM audio_jobs WHERE state='pending'").fetchone()['job_id']
            db.execute("UPDATE audio_jobs SET state='running',stage='encoding' WHERE job_id=?", (job,))
        self.service.jobs._progress[job] = {'phase': 'encoding', 'completed': 30, 'total': 120, 'unit': 'seconds', 'started': 1}
        self.service.jobs._thread = worker

        def restore():
            release.set(); worker.join(5); self.service.jobs._thread = None; self.service.jobs._progress.pop(job, None)
            with connect(self.inv.database) as db:
                db.execute("UPDATE audio_jobs SET state='pending',stage='queued' WHERE job_id=?", (job,))
        self.addCleanup(restore)
        # On the class: a status_snapshot set on the instance is a stand-in's, which live_state leaves as it is.
        snapshot = patch.object(merge_service.MergeService, 'status_snapshot', lambda service: dict(stale)); snapshot.start(); self.addCleanup(snapshot.stop)
        server = web_server.BrowserServer.__new__(web_server.BrowserServer)
        server.inventory = self.inv; server.merge = self.service; server.loading = None; server.closing = False
        server.active_library = None; server.loaded_version = 'fixture'; server.instance = 'fixture'; server.restart_context = False
        server.recovery_operations = 0; server.server_port = 0; server.merge_admissions = 0
        server.control_lock = threading.Lock(); server.control_condition = threading.Condition(server.control_lock)
        state = server.state('Audiobooks', cached=True)
        jobs = state['audiobook_jobs']
        self.assertEqual((jobs['state'], jobs['current_title'], jobs['current_job_id'], jobs['queued']), ('Running', 'Ясно', job, 0))
        row = next(row for row in state['activities'] if row['kind'] == 'conversion')
        self.assertEqual((row['subject'], row['state'], row['done'], row['total']), ('Ясно', 'running', 30, 120))
        self.assertEqual(jobs['approved_total'], stale['approved_total'], 'the counts are still the shared answer\'s')
        work = state['work']
        self.assertEqual([(row['id'], row['subject'], row['done'], row['total']) for row in work['rows']], [('conversion:' + job, 'Ясно', 30, 120)])
        self.assertEqual((work['counts']['tasks_running'], work['unread']), (1, []))
        self.same('the live read and a fresh full computation agree while it converts')


if __name__ == '__main__':
    unittest.main()
