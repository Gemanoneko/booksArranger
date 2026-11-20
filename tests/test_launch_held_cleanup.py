"""0.30.0 R2-1 (Futaba's delta QA on 03041ee): the held-cleanup re-check ran at app launch and ignored a saved Pause.

Sergei's Brom shape: a converted book whose source cleanup was held under 0.29.0 with "Persisted recovery ancestry
changed" (needs attention, that reason, no hold cause, recovery copies made, originals in place). Futaba paused, quit
and relaunched: the held cleanup ran at once with nothing pressed, the originals and copies went, and the jobs line
went from Paused to Running.

Each test builds that book through the real pipeline (a real scan of FFmpeg-made MP3s, a real review, a real conversion,
the real inline cleanup stopped before its first removal), sets the row exactly as 0.29.0's hold() left it, closes
that engine, then relaunches the real engine (web_server.py) as a SEPARATE PROCESS on a private port with this private
data, and talks to it over HTTP as the page does. Never port 5210, never Sergei's data.
"""
import contextlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import unittest
import uuid

import test_merge_service as fixtures
from action_queue import QueueStore
from scanner import Inventory
from merge_service import MergeService
from source_cleanup import LEGACY_IDENTITY_HOLD

REPO = Path(__file__).resolve().parents[1]
REFUSED = 'Persisted recovery ancestry changed'
LAUNCH_WATCH = 15.0  # seconds a relaunch is watched with nothing pressed (03041ee ran the held cleanup within 2)


def free_port():
    with contextlib.closing(socket.socket()) as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


@unittest.skipUnless(os.name == 'nt' and shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Windows and FFmpeg required')
class LaunchHeldCleanupTests(unittest.TestCase):
    ready = fixtures.MergeTests.ready
    wait = fixtures.MergeTests.wait

    def setUp(self):
        fixtures.MergeTests.setUp(self)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: self.service.close())
        self.engine = None

    # ------------------------------------------------------------------ the 0.29.0 book, built for real
    def held_book(self, paused, reason=REFUSED, queued=False):
        """The converted book with its cleanup held as 0.29.0 left Brom's; `paused`: Sergei paused before quitting. reason: the
        hold's (an identity hold offers Retry cleanup); queued: his Retry cleanup press was queued and saved at Quit."""
        self.sorted = self.base / 'Sorted';self.sorted.mkdir()
        roots = dict(self.inv.roots);database = self.inv.database;self.service.close()
        self.inv = Inventory(database, roots, audiobook_sources=[roots['Audiobooks']], output_root=str(self.sorted))
        self.service = MergeService(self.inv, self.base / 'cache')
        row = self.ready()
        job = self.service.jobs.enqueue(self.service.reviews.build_manifest('Audiobooks', row['id'], row['revision']))
        cleanup = self.service.cleanup;real = cleanup.output_policy;calls = []
        def stop_before_the_first_removal():  # enrolment, the run's start, then the first removal is refused
            calls.append(1);value = real()
            return (None, value[1]) if len(calls) >= 3 else value
        cleanup.output_policy = stop_before_the_first_removal
        self.service.jobs.resume();self.wait()
        cleanup.output_policy = real
        with self.catalog() as db:
            self.assertEqual(db.execute('SELECT state FROM audio_jobs WHERE job_id=?', (job,)).fetchone()[0], 'completed')
            self.id, state = db.execute('SELECT id,state FROM source_cleanup WHERE job_id=?', (job,)).fetchone()
            self.assertEqual(state, 'needs_attention', 'positive control: the real inline cleanup stopped before removing')
            self.assertEqual(db.execute('SELECT count(*) FROM source_cleanup_holds WHERE cleanup_id=?', (self.id,)).fetchone()[0], 0)
        # The row exactly as 0.29.0's hold() left Brom's after the refusal: needs attention, that reason, no hold cause.
        with contextlib.closing(sqlite3.connect(self.inv.database, timeout=10)) as db, db:
            db.execute("UPDATE source_cleanup SET state='needs_attention',reason=?,updated=? WHERE id=?",
                       (reason, '2026-11-18T10:09:00.000000+00:00', self.id))
        self.originals = [str(path) for path in self.sources]
        self.copies = sorted(str(path) for path in (self.base / 'source-recovery' / self.id).iterdir())
        self.assertEqual(len(self.copies), len(self.originals), 'positive control: every recovery copy is made')
        if queued:
            self.assertTrue((self.service.cleanup.identity_retry(self.id) or {}).get('allowed'), 'positive control: the hold offers Retry cleanup')
            revision = self.service.reviews._row('Audiobooks', row['id'])['revision']
        if paused:self.service.pause()  # Sergei's Pause, saved; then Quit
        self.service.close()
        if queued:  # his queued Retry cleanup, saved at Quit as the action queue saves it (ActionQueue._persist)
            press = {'id': str(uuid.uuid4()), 'action': 'cleanup', 'book_id': row['id'], 'title': 'Book', 'queued_at': time.time(),
                     'args': {'identity_retry': True, 'revision': revision, 'job_id': job, 'cleanup_id': self.id}}
            QueueStore(self.inv.database).save([press], closing=True)
        self.before = self.snapshot()
        self.roots_file = self.base / 'roots.json';self.roots_file.write_text(json.dumps(roots), encoding='utf-8')

    def catalog(self):
        return contextlib.closing(sqlite3.connect(Path(self.inv.database).as_uri() + '?mode=ro', uri=True, timeout=10))

    def snapshot(self):
        """What a run of the held cleanup changes: its row and members, the originals and the recovery copies."""
        with self.catalog() as db:
            row = db.execute('SELECT state,reason,updated FROM source_cleanup WHERE id=?', (self.id,)).fetchone()
            members = db.execute('SELECT path,state,backup_facts FROM cleanup_members WHERE cleanup_id=? ORDER BY path', (self.id,)).fetchall()
            holds = db.execute('SELECT count(*) FROM source_cleanup_holds WHERE cleanup_id=?', (self.id,)).fetchone()[0]
        files = [(path, os.path.exists(path)) for path in self.originals + self.copies]
        return {'row': tuple(row), 'members': [tuple(member) for member in members], 'holds': holds, 'files': files}

    # ------------------------------------------------------------------ the relaunch: another process, another port
    def relaunch(self):
        self.port = free_port();self.assertNotEqual(self.port, 5210, 'never Sergei\'s app port')
        log = open(self.base / 'engine.log', 'wb');self.addCleanup(log.close)
        # Embedded Python omits the script directory. Admit only this fixture's backend, as the packaged host does.
        bootstrap = 'import sys; sys.path.insert(0, sys.argv.pop(1)); import web_server; web_server.main()'
        command = [sys.executable, '-I', '-B', '-c', bootstrap, str(REPO), '--database', str(self.inv.database),
                   '--roots-json', str(self.roots_file), '--audiobook-source', self.inv.roots['Audiobooks'],
                   '--audiobook-output-root', str(self.sorted), '--port', str(self.port)]
        environment = {key: value for key, value in os.environ.items() if key not in ('PYTHONPATH', 'PYTHONHOME')}
        self.engine = subprocess.Popen(command, cwd=REPO, env=environment, stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.addCleanup(self.stop_engine)
        deadline = time.monotonic() + 120
        while True:
            self.assertIsNone(self.engine.poll(), 'the engine ended: ' + (self.base / 'engine.log').read_text('utf-8', 'replace')[-2000:])
            try:
                status, page = self.call('/', method='GET', token=False)
                if status == 200:break
            except OSError:pass
            self.assertLess(time.monotonic(), deadline, 'the engine never answered')
            time.sleep(.2)
        self.token = re.search(r'name="books-token" content="([^"]+)"', page).group(1)
        while True:  # the catalog has loaded and the launch's background passes have started
            status, state = self.call('/api/state?library=Audiobooks', method='GET')
            if status == 200 and isinstance(state, dict) and 'needs_you_only' in state:break  # only the loaded answer has it
            self.assertLess(time.monotonic(), deadline, 'the engine never finished loading: ' + json.dumps(state)[:500])
            time.sleep(.2)

    def call(self, route, body=None, method='POST', token=True):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=60)
        headers = {'Host': f'127.0.0.1:{self.port}'}
        if token:headers['X-Books-Token'] = self.token
        raw = None
        if body is not None:
            raw = json.dumps(body).encode('utf-8');headers.update({'Content-Type': 'application/json', 'Content-Length': str(len(raw))})
        try:
            connection.request(method, route, body=raw, headers=headers);response = connection.getresponse();data = response.read()
        finally:
            connection.close()
        text = data.decode('utf-8', 'replace')
        try:return response.status, json.loads(text)
        except ValueError:return response.status, text

    def jobs_state(self):
        """The jobs line: its state (Running while a worker runs) and who paused it (the saved Pause, None when none)."""
        status, state = self.call('/api/state?library=Audiobooks', method='GET')
        self.assertEqual(status, 200, state)
        jobs = state['audiobook_jobs'];pause = jobs.get('pause')
        return jobs['state'], pause.get('origin') if isinstance(pause, dict) else None

    def stop_engine(self):
        if self.engine is None or self.engine.poll() is not None:return
        try:self.call('/api/shutdown', {})
        except OSError:pass
        try:self.engine.wait(60)
        except subprocess.TimeoutExpired:
            self.engine.kill();self.engine.wait(30)

    def watch_launch(self, paused):
        """Nothing pressed for LAUNCH_WATCH seconds: the held cleanup must not run and the jobs line must not run."""
        deadline = time.monotonic() + LAUNCH_WATCH;seen = set()
        while time.monotonic() < deadline:
            seen.add(self.jobs_state())
            self.assertEqual(self.snapshot(), self.before, 'the held cleanup ran at launch with nothing pressed')
            time.sleep(.25)
        self.assertNotIn('Running', {state for state, _ in seen}, 'the jobs line went to Running at launch with nothing pressed')
        self.assertEqual({origin for _, origin in seen}, {'user'} if paused else {None},
                         'a saved Pause stays in force through a relaunch' if paused else 'nothing paused the jobs at launch')

    # ------------------------------------------------------------------ the three cases of the ruling
    def test_a_saved_pause_survives_a_relaunch_and_the_held_cleanup_waits(self):
        self.held_book(paused=True)
        self.relaunch()
        self.watch_launch(paused=True)

    def test_after_a_relaunch_with_a_saved_pause_start_rechecks_the_held_cleanup_and_it_finishes(self):
        self.held_book(paused=True)
        self.relaunch()
        self.watch_launch(paused=True)  # 03041ee: it already ran here
        status, answer = self.call('/api/audiobook/resume', {})
        self.assertEqual(status, 200, answer)
        deadline = time.monotonic() + 120
        while self.snapshot()['row'][0] != 'completed':
            self.assertLess(time.monotonic(), deadline, 'Start never re-checked the held cleanup: ' + repr(self.snapshot()['row']))
            time.sleep(.25)
        self.assertFalse(any(os.path.exists(path) for path in self.originals), 'the re-checked cleanup removed the originals')

    def test_without_a_saved_pause_a_relaunch_with_nothing_pressed_runs_nothing(self):
        self.held_book(paused=False)
        self.relaunch()
        self.watch_launch(paused=False)

    # ------------------------------------------------------------------ the coordinator's ruling on the other launch paths
    def queue(self):
        status, state = self.call('/api/state?library=Audiobooks', method='GET')
        self.assertEqual(status, 200, state)
        return state.get('queued_actions') or [], state.get('queue_outcomes') or []

    def test_a_restored_retry_cleanup_waits_for_start_under_a_saved_pause_then_runs(self):
        # Item 6: a press restored from before a restart that changes files waits for Start while a saved Pause is in force,
        # worded as the paused conversion queue, and runs after his Resume with its checks again.
        self.held_book(paused=True, reason=LEGACY_IDENTITY_HOLD, queued=True)
        self.relaunch()
        self.watch_launch(paused=True)  # 91ffe1e: the restored Retry cleanup ran here, removing the originals
        waiting, _ = self.queue()
        self.assertEqual([(item['action'], item.get('restored'), (item.get('blocker') or {}).get('cause')) for item in waiting],
                         [('cleanup', True, 'queue_paused')])
        status, answer = self.call('/api/audiobook/resume', {})
        self.assertEqual(status, 200, answer)
        deadline = time.monotonic() + 120
        while self.snapshot()['row'][0] != 'completed':
            self.assertLess(time.monotonic(), deadline, 'the restored press never ran after Resume: ' + repr(self.queue()))
            time.sleep(.25)
        self.assertFalse(any(os.path.exists(path) for path in self.originals), 'the Retry cleanup removed the originals')
        waiting, outcomes = self.queue()
        self.assertEqual(waiting, []);self.assertEqual([(item['action'], item['result']) for item in outcomes], [('cleanup', 'done')])

    def test_a_saved_pause_holds_the_finished_book_checks_at_launch_until_start(self):
        # Item 7: as an in-session Pause holds them. The published check and the recovery-copy purges run as before.
        self.service.pause()  # Sergei's Pause, saved; then Quit
        self.service.close()
        self.service = MergeService(self.inv, self.base / 'cache')  # the next launch's engine, over the same catalog
        with self.assertRaisesRegex(InterruptedError, 'Finished-book checks paused'):
            with self.service._maintenance_book('a-finished-book'):pass
        self.assertFalse(self.service.jobs.background_stop.is_set(), 'the published check is left as it was')
        self.service.resume();self.wait()  # his Start
        with self.service._maintenance_book('a-finished-book'):pass  # positive control: after Start they run


def setUpModule():
    global _owner
    from scratch_area import module_disposition_owner
    _owner = module_disposition_owner()  # the fixture's own removals, when this module runs alone (Senua 0.30.0 M1)


def tearDownModule():
    _owner.close()


if __name__ == '__main__':
    unittest.main()
