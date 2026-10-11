import contextlib
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import app_launcher as launcher
import install_app_entries as install
import web_server

SCRATCH=Path(__file__).resolve().parents[1]/'scratch'/'app-launch-tests'
SCRATCH.mkdir(parents=True,exist_ok=True)

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        self.current=Mock();self.owner=Mock();self.owner.wait_exit=Mock()
        process=self.stack.enter_context(patch.object(launcher,'WindowsProcess'))
        process.return_value.__enter__.return_value=self.current
        self.stack.enter_context(patch.object(sys,'executable','C:/Python314/pythonw.exe'))
        self.existing=self.stack.enter_context(patch.object(launcher,'verified_owner'))
        self.existing.side_effect=[contextlib.nullcontext(None),contextlib.nullcontext(None)]
        self.stack.enter_context(patch.object(launcher,'launch_lease',return_value=contextlib.nullcontext()))
        self.stack.enter_context(patch('native_io.DirectoryBoundary',return_value=contextlib.nullcontext()))
        self.stack.enter_context(patch.object(launcher.os.path,'lexists',return_value=False))
        self.port=self.stack.enter_context(patch.object(launcher,'reserve_port',return_value=contextlib.nullcontext()))
        self.stack.enter_context(patch('app.catalog_lock',return_value=contextlib.nullcontext()))
        self.records=self.stack.enter_context(patch.object(launcher,'completed_records',return_value={'safe':'validation-and-identity'}))
        self.requests=self.stack.enter_context(patch.object(launcher,'read_json'))
        self.token=self.stack.enter_context(patch.object(launcher,'restart_token',return_value='fixture-only-token'))
        self.browser=self.stack.enter_context(patch.object(launcher.webbrowser,'open'))
        self.main=self.stack.enter_context(patch.object(web_server,'main'))
        self.health={'version':web_server.version()}
        self.main.side_effect=lambda _args,ready:ready(SimpleNamespace(health=lambda:self.health))
        self.stack.enter_context(patch.object(launcher.RECORD.__class__,'exists',return_value=False))
    def test_healthy_reopen_reuses_without_restart_or_start(self):
        self.existing.side_effect=[contextlib.nullcontext((self.owner,{'instance':'a'*32}))]
        self.assertEqual(launcher.run(),'reused')
        self.browser.assert_called_once_with(launcher.URL)
        self.requests.assert_not_called();self.main.assert_not_called();self.records.assert_not_called()
    def test_job_membership_does_not_block_guarded_normal_start(self):
        self.current.outside_job.side_effect=launcher.LaunchError('Successful query: ordinary user app is in a Job')
        self.assertEqual(launcher.run(),'stopped')
        self.main.assert_called_once();self.port.assert_called_once()
        self.assertEqual(self.records.call_count,3)
        self.browser.assert_called_once_with(launcher.URL)
        self.requests.assert_not_called();self.current.outside_job.assert_not_called()
    def test_job_query_failure_does_not_block_verified_healthy_reuse(self):
        self.current.outside_job.side_effect=launcher.LaunchError('An irrelevant Job query failed')
        self.existing.side_effect=[contextlib.nullcontext((self.owner,{'instance':'a'*32}))]
        self.assertEqual(launcher.run(),'reused')
        self.browser.assert_called_once_with(launcher.URL)
        self.requests.assert_not_called();self.main.assert_not_called();self.records.assert_not_called()
        self.current.outside_job.assert_not_called()
    def test_mismatched_owner_leaves_it_untouched(self):
        self.existing.side_effect=launcher.LaunchError('identity changed')
        with self.assertRaises(launcher.LaunchError):launcher.run(restart=True)
        self.requests.assert_not_called();self.main.assert_not_called()
    def existing_owner(self):
        record={'instance':'a'*32}
        self.existing.side_effect=[contextlib.nullcontext((self.owner,record)),contextlib.nullcontext((self.owner,record))]
    def test_busy_research_rejects_without_shutdown(self):
        self.existing_owner()
        self.requests.return_value={'library':'Audiobooks','root':__import__('scanner').DEFAULT_ROOTS['Audiobooks'],'automatic_processing':{'state':'Running'},'audiobook_jobs':{'state':'Completed'}}
        with self.assertRaisesRegex(launcher.LaunchError,'Stop automatic'):launcher.run(restart=True)
        self.assertEqual(self.requests.call_count,1);self.token.assert_not_called();self.owner.wait_exit.assert_not_called();self.main.assert_not_called()
    def test_checkpoint_shutdown_and_exact_exit_precede_new_bind_and_ready(self):
        self.existing_owner();events=[]
        def request(path,**kwargs):
            events.append(path)
            if path=='api/shutdown':
                self.assertEqual(kwargs['data'],{'restart_instance':'a'*32})
                return {'stopping':True}
            return {'library':'Audiobooks','root':__import__('scanner').DEFAULT_ROOTS['Audiobooks'],'automatic_processing':{'state':'Paused'},'audiobook_jobs':{'state':'Completed','queued':0}}
        self.requests.side_effect=request
        self.owner.wait_exit.side_effect=lambda:events.append('exact exit')
        self.port.side_effect=lambda:events.append('exclusive bind') or contextlib.nullcontext()
        self.browser.side_effect=lambda _url:events.append('ready browser')
        launcher.run(restart=True)
        self.assertEqual(events,['api/state?library=Audiobooks','api/shutdown','exact exit','exclusive bind','ready browser'])
        self.assertFalse(any('automatic/start' in item for item in events))
    def test_shutdown_timeout_does_not_start_replacement(self):
        self.existing_owner()
        self.requests.side_effect=[{'library':'Audiobooks','root':__import__('scanner').DEFAULT_ROOTS['Audiobooks'],'automatic_processing':{'state':'Paused'},'audiobook_jobs':{'state':'Completed'}},{'stopping':True}]
        self.owner.wait_exit.side_effect=launcher.LaunchError('still stopping')
        with self.assertRaises(launcher.LaunchError):launcher.run(restart=True)
        self.port.assert_not_called();self.main.assert_not_called();self.browser.assert_not_called()
    def test_changed_completed_record_does_not_open_new_page(self):
        self.records.side_effect=[{'safe':1},{'safe':1},{'safe':2}]
        with self.assertRaisesRegex(launcher.LaunchError,'saved completed'):launcher.run()
        self.browser.assert_not_called()
    def test_failed_startup_does_not_show_success_page(self):
        self.main.side_effect=RuntimeError('private fixture startup failed')
        with self.assertRaises(RuntimeError):launcher.run()
        self.browser.assert_not_called()

class StateAndEntrypointTests(unittest.TestCase):
    def test_completed_protection_includes_validation_metadata_and_revision(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            dbpath=Path(temp)/'catalog.sqlite3'
            with contextlib.closing(sqlite3.connect(dbpath)) as db, db:
                db.executescript('CREATE TABLE audio_jobs(job_id,manifest_hash,manifest,output,state);CREATE TABLE book_groups(id,revision,fingerprint);CREATE TABLE candidate_context(id,revision,data);')
                manifest={'candidate_id':'book','metadata':{'title':'Fixture book'}}
                output={'validation':{'passed':True},'sha256':'a'*64}
                db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?)',('job','hash',json.dumps(manifest),json.dumps(output),'completed'))
                db.execute('INSERT INTO book_groups VALUES(?,?,?)',('book',4,'fingerprint'))
                db.execute('INSERT INTO candidate_context VALUES(?,?,?)',('book',4,json.dumps({'metadata_approved':True})))
            before=launcher.completed_records(dbpath)
            with contextlib.closing(sqlite3.connect(dbpath)) as db, db:db.execute('UPDATE book_groups SET revision=5')
            self.assertNotEqual(before,launcher.completed_records(dbpath))
            with contextlib.closing(sqlite3.connect(dbpath)) as db, db:db.execute('UPDATE audio_jobs SET output=?',(json.dumps({'validation':{'passed':False}}),))
            with self.assertRaises(launcher.LaunchError):launcher.completed_records(dbpath)
    def test_pyw_entries_explicitly_set_fixed_import_path_under_isolation(self):
        for filename,flag in (('launch-web.pyw',False),('restart-web.pyw',True)):
            source=(launcher.BASE/filename).read_text()
            fake_main=Mock(return_value=0)
            with patch.dict(sys.modules,{'app_launcher':SimpleNamespace(main=fake_main)}),patch.object(sys,'path',list(sys.path)):
                with self.assertRaises(SystemExit):exec(compile(source,filename,'exec'),{'__file__':str(launcher.BASE/filename)})
                self.assertEqual(sys.path[0],str(launcher.BASE))
            fake_main.assert_called_once_with(restart=flag)
    def test_idle_rejects_scan_audio_cleanup_and_active_automatic(self):
        for state in ({'active_library':'Ebooks'},{'audiobook_jobs':{'state':'Running'}},{'audiobook_jobs':{'cleanup_active':True}},{'automatic_processing':{'state':'Stopping'}}):
            with self.subTest(state=state),self.assertRaises(launcher.LaunchError):launcher.verify_idle(state)
        launcher.verify_idle({'automatic_processing':{'state':'Paused'},'audiobook_jobs':{'state':'Completed'}})
        launcher.verify_idle({'automatic_processing':{'state':'Paused'},'audiobook_jobs':{'state':'Paused','queued':3}})

    def test_native_mutex_contender_refuses_then_next_start_can_acquire(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp,patch.object(launcher,'DATABASE',Path(temp)/'catalog.sqlite3'):
            outcomes=[]
            def contender():
                try:
                    with launcher.launch_lease():outcomes.append('acquired')
                except launcher.LaunchError:outcomes.append('refused')
            with launcher.launch_lease():
                worker=threading.Thread(target=contender);worker.start();worker.join(5)
                self.assertFalse(worker.is_alive());self.assertEqual(outcomes,['refused'])
            with launcher.launch_lease():outcomes.append('later acquired')
            self.assertEqual(outcomes,['refused','later acquired'])

    def test_native_protected_receipt_all_recognized_readers_and_exact_retirement(self):
        from native_io import DirectoryBoundary
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            path=Path(temp)/'web-instance.json'
            health={'application':'Books Arranger','pid':123,'port':5210,'version':'fixture','instance':'a'*32,'url':launcher.URL}
            with DirectoryBoundary(path.anchor,path.parent),web_server.owned_instance_record(path,health):
                self.assertEqual(json.loads(path.read_text()),health)
                self.assertEqual(json.loads(web_server.read_instance_record(path)),health)
                with patch.object(launcher,'RECORD',path):self.assertEqual(launcher.receipt(),health)
                with self.assertRaises(OSError):path.write_text('unrelated replacement')
            self.assertFalse(path.exists())

    def test_existing_hardlinked_receipt_is_refused_and_preserved(self):
        import os
        from native_io import DirectoryBoundary
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            path=Path(temp)/'web-instance.json';other=Path(temp)/'other.json';path.write_bytes(b'unique existing metadata');os.link(path,other)
            with DirectoryBoundary(path.anchor,path.parent),self.assertRaises(RuntimeError):
                with web_server.owned_instance_record(path,{}):self.fail('An existing ownership record was overwritten')
            self.assertEqual(path.read_bytes(),b'unique existing metadata');self.assertEqual(other.read_bytes(),b'unique existing metadata')

    def test_dangling_record_is_not_treated_as_absent(self):
        with patch.object(launcher.os.path,'lexists',return_value=True),patch.object(launcher,'receipt',side_effect=launcher.LaunchError('nonordinary record')),patch.object(launcher,'WindowsProcess') as process:
            with self.assertRaises(launcher.LaunchError):
                with launcher.verified_owner():self.fail('A dangling entry was treated as absent')
            process.assert_not_called()

class ShortcutTests(unittest.TestCase):
    def test_native_private_shortcuts_roundtrip_reopen_without_overwrite(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            base=Path(temp);programs=base/'Programs';programs.mkdir()
            for name in ('launch-web.pyw','restart-web.pyw'):(base/name).write_text('# private shortcut target; never executed')
            runtime=Path(sys.executable).with_name('pythonw.exe')
            first=install.install(programs,base=base,runtime=runtime)
            self.assertEqual([item['action'] for item in first],['created','created'])
            hashes=[Path(item['path']).read_bytes() for item in first]
            second=install.install(programs,base=base,runtime=runtime)
            self.assertEqual([item['action'] for item in second],['reused','reused'])
            self.assertEqual(hashes,[Path(item['path']).read_bytes() for item in second])
            self.assertEqual(list((programs/'Books Arranger').glob('.books-arranger-*')),[])
    def test_unrelated_shortcut_refuses_both_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            base=Path(temp);programs=base/'Programs';programs.mkdir();folder=programs/'Books Arranger';folder.mkdir()
            for name in ('launch-web.pyw','restart-web.pyw'):(base/name).write_text('# never executed')
            conflict=folder/'Restart Books Arranger.lnk'
            with install.ShellLink() as link:
                link.set(sys.executable,'-I -B -c pass',base,'Unrelated private shortcut');link.save(conflict)
            before=conflict.read_bytes()
            with self.assertRaises(FileExistsError):install.install(programs,base=base)
            self.assertEqual(conflict.read_bytes(),before)
            self.assertFalse((folder/'Books Arranger.lnk').exists())

if __name__=='__main__':unittest.main()
