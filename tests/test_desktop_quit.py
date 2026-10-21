"""Desktop shell contract: finish-then-quit drain, desktop control auth, version source."""
import io
import json
from email.message import Message
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

from audio_jobs import AudioJobs, StartRefused
from desktop_backend import DesktopControl, handler_class
from encoding_policy import PROFILE
from merge_service import MergeService
import web_server
from web_server import Handler

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'desktop-quit-tests'
AREA.mkdir(parents=True, exist_ok=True)
TOKEN = 'd' * 64


def manifest():
    return {'job_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
            'sources': [{'sha256': 'a' * 64, 'fingerprint': {}}], 'metadata': {}, 'destination': 'fixture',
            'profile': PROFILE, 'evidence': {}, 'cover': {}}


class DrainTests(unittest.TestCase):
    def test_current_book_finishes_uninterrupted_and_next_book_stays_queued(self):
        with tempfile.TemporaryDirectory(dir=AREA) as temp:
            started = threading.Event(); release = threading.Event(); seen = []

            def runner(job, stop, checkpoint):
                seen.append(job['job_id']); started.set()
                release.wait(5)
                self.assertFalse(stop.is_set(), 'drain must not interrupt the book in progress')
                record = {'job_id': job['job_id'], 'final_path': 'fixture.m4b', 'owned_temp': 'fixture.partial',
                          'sha256': 'b' * 64, 'size': 1, 'validation': {'passed': True}}
                checkpoint('publishing', record)
                return record

            queue = AudioJobs(Path(temp) / 'db.sqlite3', runner, lambda m: True, lambda r: True)
            first, second = manifest(), manifest()
            queue.enqueue(first); queue.enqueue(second); queue.resume()
            self.assertTrue(started.wait(5))
            queue.drain()
            self.assertEqual(queue.status()['state'], 'Running')
            release.set(); queue._thread.join(5)
            self.assertFalse(queue._thread.is_alive())
            states = {job['job_id']: job['state'] for job in queue.status()['jobs']}
            self.assertEqual(states[first['job_id']], 'completed')
            self.assertEqual(states[second['job_id']], 'pending')
            self.assertEqual(seen, [first['job_id']])
            with self.assertRaises(StartRefused) as closing:
                queue.resume()  # typed closing refusal; nothing new starts
            self.assertEqual(closing.exception.start_state, 'closing')
            queue._thread.join(5)
            self.assertEqual(seen, [first['job_id']])
            self.assertEqual({job['job_id']: job['state'] for job in queue.status()['jobs']}, states)
            queue.close()

    def test_merge_pause_and_resume_are_inert_while_draining(self):
        merge = MergeService.__new__(MergeService)
        merge.draining = False
        merge.jobs = SimpleNamespace(drain=Mock(), pause=Mock(), _thread=None)
        merge.cleanup = SimpleNamespace(pause=Mock(), thread=None, current=None)
        merge._post_current = None
        merge.operation_lock = threading.RLock()
        merge.state = Mock(return_value={'state': 'Running'})
        merge.drain()
        self.assertTrue(merge.draining); merge.jobs.drain.assert_called_once_with()
        merge.pause()
        with self.assertRaises(StartRefused) as closing:
            merge.resume()
        self.assertEqual(closing.exception.start_state, 'closing')
        merge.jobs.pause.assert_not_called(); merge.cleanup.pause.assert_not_called()
        self.assertTrue(merge.drained())
        merge.cleanup.current = 'cleanup-in-progress'
        self.assertFalse(merge.drained())


def fake_server(*, converting=False, finish=None):
    lock = threading.Lock()
    jobs_thread = SimpleNamespace(is_alive=Mock(return_value=converting))
    merge = SimpleNamespace(jobs=SimpleNamespace(_thread=jobs_thread), drain=Mock(), drained=Mock(return_value=not converting),
                            state=Mock(return_value={'state': 'Running' if converting else 'Paused', 'current_title': 'Fixture', 'stage': 'creating', 'queued': 2}))
    merge.automatic = SimpleNamespace(stop=Mock(), status=Mock(return_value={'state': 'Running'}), thread=None)
    server = SimpleNamespace(merge=merge, inventory=SimpleNamespace(stop=Mock()), closing=False, control_lock=lock,
                             control_condition=threading.Condition(lock), scan_active=Mock(return_value=False),
                             finish_shutdown=finish or Mock(), shutdown=Mock())
    return server, jobs_thread


class ControlTests(unittest.TestCase):
    def test_quit_refuses_new_work_waits_for_book_then_shuts_down(self):
        server, jobs_thread = fake_server(converting=True)
        control = DesktopControl(server)
        self.assertTrue(control.status()['busy']['converting'])
        self.assertEqual(control.quit()['phase'], 'finishing')
        self.assertTrue(server.closing)
        server.merge.drain.assert_called_once_with(); server.inventory.stop.assert_called(); server.merge.automatic.stop.assert_called_once_with()
        time.sleep(.8)
        server.finish_shutdown.assert_not_called()  # the book is still converting
        self.assertEqual(control.quit()['phase'], 'finishing')  # a second Quit is idempotent
        jobs_thread.is_alive.return_value = False; server.merge.drained.return_value = True
        control.thread.join(5)
        server.finish_shutdown.assert_called_once_with(); server.shutdown.assert_not_called()
        self.assertEqual(control.status()['phase'], 'exiting')

    def test_shutdown_failure_retains_serving_and_can_retry_after_safe_checkpoint(self):
        server, _ = fake_server(finish=Mock(side_effect=TimeoutError('worker still at checkpoint')))
        control = DesktopControl(server)
        control.quit(); control.thread.join(5)
        server.shutdown.assert_not_called()
        self.assertEqual(control.status()['phase'], 'blocked')
        self.assertIn('worker still at checkpoint',control.status()['error'])
        server.finish_shutdown.side_effect=None
        control.quit(); control.thread.join(5)
        self.assertEqual(control.status()['phase'],'exiting')
        self.assertEqual(server.finish_shutdown.call_count,2)

    def test_stop_now_is_immediate_and_single(self):
        server, _ = fake_server(converting=True)
        control = DesktopControl(server)
        self.assertIn(control.stop_now()['phase'], ('stopping','exiting'))
        self.assertIn(control.stop_now()['phase'], ('stopping','exiting'))
        self.assertTrue(server.closing)
        time.sleep(.3)
        server.finish_shutdown.assert_called_once_with()

    def test_update_busy_admission_refuses_without_closing_or_shutdown(self):
        server,_=fake_server();server.merge_admissions=1;server.state=Mock()
        control=DesktopControl(server)
        with self.assertRaises(RuntimeError):control.prepare_update()
        self.assertFalse(server.closing);server.finish_shutdown.assert_not_called();server.state.assert_not_called()

    def test_update_checks_full_idle_under_admission_lock(self):
        server,_=fake_server();server.merge_admissions=0;server.state=Mock(return_value={'fixture':'full state'})
        control=DesktopControl(server)
        def verified(state):
            self.assertTrue(server.control_lock.locked());self.assertEqual(state,{'fixture':'full state'});self.assertFalse(server.closing)
        with patch('app_launcher.verify_idle',side_effect=verified):control.prepare_update()
        control.thread.join(5)
        self.assertTrue(server.closing);server.finish_shutdown.assert_called_once_with()
        self.assertEqual(control.phase,'exiting')

    def test_update_nonidle_keeps_owner_and_serving(self):
        server,_=fake_server();server.merge_admissions=0;server.state=Mock(return_value={})
        control=DesktopControl(server)
        with patch('app_launcher.verify_idle',side_effect=RuntimeError('Recovery work is active')):
            with self.assertRaisesRegex(RuntimeError,'Recovery'):control.prepare_update()
        self.assertFalse(server.closing);server.finish_shutdown.assert_not_called();self.assertEqual(control.phase,'running')


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.server, _ = fake_server()
        self.server.server_port = 5211; self.server.token = 'page-token'
        self.server.origins = {'http://127.0.0.1:5211', 'http://localhost:5211'}
        self.server.desktop = SimpleNamespace(status=Mock(return_value={'phase': 'running'}), quit=Mock(return_value={'phase': 'finishing'}),
                                              stop_now=Mock(return_value={'phase': 'stopping'}))
        self.cls = handler_class(Handler, TOKEN)

    def call(self, path, method='POST', body=b'{}', desktop=TOKEN, extra=None):
        h = self.cls.__new__(self.cls); h.server = self.server; h.path = path
        h.headers = Message(); h.headers['Host'] = '127.0.0.1:5211'
        if desktop is not None: h.headers['X-Books-Desktop'] = desktop
        for key, value in (extra or {}).items(): h.headers[key] = value
        h.headers['Content-Type'] = 'application/json'; h.headers['Content-Length'] = str(len(body)); h.rfile = io.BytesIO(body)
        h.result = None
        h.response = lambda status, value, content_type='application/json': setattr(h, 'result', (status, value))
        (h.do_POST if method == 'POST' else h.do_GET)()
        return h.result

    def test_desktop_routes_require_desktop_token_and_local_origin(self):
        self.assertEqual(self.call('/api/desktop/status', 'GET'), (200, {'phase': 'running'}))
        self.assertEqual(self.call('/api/desktop/quit'), (202, {'phase': 'finishing'}))
        self.assertEqual(self.call('/api/desktop/stop-now'), (202, {'phase': 'stopping'}))
        for desktop in (None, 'x' * 64, 'page-token'):
            self.assertEqual(self.call('/api/desktop/quit', desktop=desktop)[0], 403)
            self.assertEqual(self.call('/api/desktop/status', 'GET', desktop=desktop)[0], 403)
        self.assertEqual(self.call('/api/desktop/quit', extra={'Origin': 'https://example.com'})[0], 403)
        self.assertEqual(self.call('/api/desktop/quit', extra={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.assertEqual(self.call('/api/desktop/quit', body=b'{"now":true}')[0], 400)
        self.assertEqual(self.call('/api/desktop/status?x=1', 'GET')[0], 400)
        self.server.desktop.quit.assert_called_once_with(); self.server.desktop.stop_now.assert_called_once_with()

    def test_other_routes_keep_page_token_rules(self):
        result = self.call('/api/shutdown', desktop=None, extra={'X-Books-Token': 'wrong'})
        self.assertEqual(result[0], 403)


class StaleRecordTests(unittest.TestCase):
    def test_only_a_record_of_an_ended_process_is_moved_aside(self):
        import subprocess, sys
        from desktop_backend import retire_stale_record
        from catalog_owner import catalog_lock
        with tempfile.TemporaryDirectory(dir=AREA) as temp:
            database = Path(temp) / 'inventory.sqlite3'; record = Path(temp) / 'web-instance.json'
            roots={'Audiobooks':str(Path(temp)/'library'),'Podcasts':str(Path(temp)/'library/podcasts'),'Ebooks':str(Path(temp)/'ebooks')}
            def retire():
                with catalog_lock(database,roots):return retire_stale_record(database,roots,5211)
            def owner(pid):return {'application':'Books Arranger','pid':pid,'instance':'a'*32,'version':'0.16.0','url':'http://127.0.0.1:5211/'}
            ended = subprocess.run([sys.executable, '-c', 'import os;print(os.getpid())'], capture_output=True, text=True, check=True)
            dead_pid = int(ended.stdout)
            alive = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])
            try:
                record.write_text(json.dumps(owner(alive.pid)), encoding='utf-8')
                self.assertIsNone(retire()); self.assertTrue(record.exists())
                record.write_text('{not json', encoding='utf-8')
                with self.assertRaises(RuntimeError):retire()
                self.assertTrue(record.exists())
                record.write_text(json.dumps(owner(dead_pid)), encoding='utf-8')
                aside = retire()
                self.assertFalse(record.exists()); self.assertTrue(aside.exists())
                self.assertEqual(json.loads(aside.read_text(encoding='utf-8'))['pid'], dead_pid)
                self.assertIsNone(retire())  # nothing left to move
            finally:
                alive.kill(); alive.wait()

    def test_source_library_record_is_never_mutated_before_refusal(self):
        from desktop_backend import retire_stale_record
        from catalog_owner import catalog_lock
        with tempfile.TemporaryDirectory(dir=AREA) as temp:
            base=Path(temp); database=base/'inventory.sqlite3'; record=base/'web-instance.json'
            raw=b'{"pid":99999999}';record.write_bytes(raw)
            roots={'Audiobooks':str(base),'Podcasts':str(base/'p'),'Ebooks':str(base/'e')}
            with self.assertRaises(ValueError):
                with catalog_lock(database,roots):retire_stale_record(database,roots,5211)
            self.assertEqual(record.read_bytes(),raw)
            self.assertEqual(list(base.glob('web-instance.stale-*')),[])
            self.assertFalse(Path(str(database)+'.lock').exists())

    def test_unknown_record_and_extra_stream_are_preserved(self):
        from desktop_backend import retire_stale_record
        from catalog_owner import catalog_lock
        from native_io import BoundaryError
        with tempfile.TemporaryDirectory(dir=AREA) as temp:
            base=Path(temp); database=base/'inventory.sqlite3'; record=base/'web-instance.json'
            roots={'Audiobooks':str(base/'a'),'Podcasts':str(base/'p'),'Ebooks':str(base/'e')}
            record.write_text(json.dumps({'application':'Other','pid':99999999}),encoding='utf-8')
            before=record.read_bytes()
            with catalog_lock(database,roots):
                with self.assertRaises(RuntimeError):retire_stale_record(database,roots,5211)
            self.assertEqual(record.read_bytes(),before)
            Path(str(record)+':Zone.Identifier').write_bytes(b'fixture')
            with catalog_lock(database,roots):
                with self.assertRaises(BoundaryError):retire_stale_record(database,roots,5211)
            self.assertEqual(Path(str(record)+':Zone.Identifier').read_bytes(),b'fixture')

    def test_retirement_requires_catalog_lease(self):
        from desktop_backend import retire_stale_record
        with tempfile.TemporaryDirectory(dir=AREA) as temp:
            with self.assertRaises(RuntimeError):retire_stale_record(Path(temp)/'inventory.sqlite3',{},5211)


class VersionTests(unittest.TestCase):
    def test_package_json_is_the_version_source_with_generated_file_fallback(self):
        with tempfile.TemporaryDirectory(dir=AREA) as temp:
            base = Path(temp)
            with patch.object(web_server, 'BASE', base):
                self.assertEqual(web_server.version(), 'prototype')
                (base / 'VERSION').write_text('1.2.3\n', encoding='utf-8')
                self.assertEqual(web_server.version(), '1.2.3')
                (base / 'package.json').write_text(json.dumps({'version': '2.0.0'}), encoding='utf-8')
                self.assertEqual(web_server.version(), '2.0.0')
        repo = Path(__file__).resolve().parents[1]
        self.assertEqual(web_server.version(), json.loads((repo / 'package.json').read_text(encoding='utf-8'))['version'])


if __name__ == '__main__':
    unittest.main()
