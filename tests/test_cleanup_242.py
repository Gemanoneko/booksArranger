"""0.24.2 cleanup scheduling/ownership contracts, isolated memory and mocked workers."""
import contextlib
import json
import os
import sqlite3
import sys
import threading
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cleanup_retry
from cleanup_ownership import OwnershipIndex
from merge_service import MergeService, operation

class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        area=Path(__file__).resolve().parents[1]/'scratch'/'maintenance-242-tests';area.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=area);self.addCleanup(self.temp.cleanup)
        self.database=Path(self.temp.name)/'catalog.sqlite3'
        from scanner import connect
        with connect(self.database) as db:
            db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT)')
            db.execute('INSERT INTO audio_jobs VALUES(?,?)',('finished',json.dumps({'metadata':{'title':'Actual finished book'}})))
    def service(self):
        value=MergeService.__new__(MergeService)
        value.operation_lock=threading.RLock();value.draining=False
        value.inventory=SimpleNamespace(database=self.database)
        value.jobs=SimpleNamespace(_stop=threading.Event(),_thread=None)
        value.cleanup=SimpleNamespace(thread=None,current=None)
        value._retention_stop=threading.Event();value._update_hold=threading.Event()
        value._no_scan=Mock();value._retention_wake=threading.Event()
        return value
    def test_resume_admits_without_hashing_completed_books(self):
        value=self.service();value._resume_guarded=Mock(return_value={'start_admission':{'state':'running'}})
        value._recheck_finished=Mock(side_effect=AssertionError('unrelated full pass'))
        self.assertEqual(value.resume()['start_admission']['state'],'running')
        value._resume_guarded.assert_called_once_with(0,None,False)
        self.assertTrue(value._retention_wake.is_set())
    def test_initial_paused_queue_does_not_strand_old_folder_work(self):
        value=self.service();value.jobs._stop.set()
        with value._maintenance_book('finished'):
            value._storage_guard();self.assertEqual(value._maintenance['state'],'checking')
            self.assertEqual(value._maintenance['title'],'Actual finished book')
        self.assertIsNone(value._maintenance)
    def test_user_pause_interrupts_maintenance_at_checkpoint(self):
        value=self.service()
        with value._maintenance_book('finished'):
            value._maintenance_paused=True
            with self.assertRaises(InterruptedError):value._storage_guard()
            self.assertTrue(value._maintenance['cancel_requested'])
        self.assertIsNone(value._maintenance)
    def test_scan_holds_maintenance_without_erasing_it(self):
        value=self.service();value._no_scan.side_effect=ValueError('scan active')
        with self.assertRaises(ValueError):
            with value._maintenance_book('finished'):self.fail('scan must prevent work')
        self.assertTrue(value.operation_lock.acquire(blocking=False));value.operation_lock.release()
    def test_closing_and_update_preempt_protected_read(self):
        for field in ('_closing','draining','_update_hold','_retention_stop'):
            value=self.service()
            with value._maintenance_book('finished'):
                if field.endswith('hold') or field.endswith('stop'):getattr(value,field).set()
                else:setattr(value,field,True)
                with self.assertRaises(InterruptedError):value._storage_guard()
    def test_foreground_operation_preempts_background_owner(self):
        value=self.service();entered=threading.Event();stopped=threading.Event();errors=[]
        def background():
            try:
                with value._maintenance_book('finished'):
                    entered.set()
                    until=time.monotonic()+2
                    while time.monotonic()<until:
                        value._storage_guard();stopped.wait(.001)
                    errors.append('foreground never preempted read')
            except InterruptedError:stopped.set()
        worker=threading.Thread(target=background);value._retention_thread=worker;worker.start()
        self.assertTrue(entered.wait(1))
        result=operation(lambda owner:'admitted')(value)
        worker.join(3)
        self.assertFalse(worker.is_alive());self.assertTrue(stopped.is_set());self.assertEqual(result,'admitted');self.assertEqual(errors,[])
        self.assertEqual(value._foreground_waiters,0)
    def test_foreground_failure_releases_waiter_marker(self):
        value=self.service()
        def fail(owner):raise ValueError('refused')
        with self.assertRaises(ValueError):operation(fail)(value)
        self.assertEqual(value._foreground_waiters,0)
    def test_transient_retry_runs_again_after_deadline(self):
        value=self.service()
        with patch('merge_service.time.monotonic',return_value=100):value._cleanup_failed(('folder','one'),PermissionError(13,'open'))
        with patch('merge_service.time.monotonic',return_value=159):self.assertFalse(value._cleanup_due(('folder','one')))
        with patch('merge_service.time.monotonic',return_value=160):self.assertTrue(value._cleanup_due(('folder','one')))
    def test_proof_refusal_and_interruption_are_not_transient_retry_promises(self):
        value=self.service();value._cleanup_failed('proof',ValueError('Source retirement correspondence changed'))
        self.assertFalse(value._cleanup_due('proof'))
        value._cleanup_failed('stop',InterruptedError('closing'));self.assertTrue(value._cleanup_due('stop'))
    def test_retry_copy_requires_an_actual_scheduled_owner_and_pause_scope(self):
        value=self.service();value._retention_thread=SimpleNamespace(is_alive=lambda:True)
        value._cleanup_retry_at={('folder','book'):100,'recovery-book':100}
        self.assertTrue(value._retry_view(('folder','book'))['retryable'])
        value._maintenance_paused=True
        self.assertFalse(value._retry_view(('folder','book'))['retryable'])
        self.assertIsNone(value._retry_view(('folder','book'))['retry_at'])
        self.assertTrue(value._retry_view('recovery-book')['retryable'])
        value._maintenance_paused=False;value._update_hold.set()
        self.assertFalse(value._retry_view('recovery-book')['retryable'])
        value._update_hold.clear();value._retention_thread=SimpleNamespace(is_alive=lambda:False)
        self.assertFalse(value._retry_view(('folder','book'))['retryable'])

    def test_native_wrapper_retry_classification_is_specific(self):
        for reason in ('Destination directory cannot be protected: [WinError 32] sharing violation','[WinError 5] Access denied','database is locked','Folder cleanup tries again later: offline'):
            self.assertTrue(cleanup_retry.transient(reason),reason)
        for reason in ('Native identity changed','Retirement proof differs','[WinError 87] invalid parameter','[WinError 32] open [WinError 87] bad'):
            self.assertFalse(cleanup_retry.transient(reason),reason)

class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT,state TEXT,progress REAL);CREATE TABLE book_groups(id TEXT PRIMARY KEY,superseded INTEGER);CREATE TABLE catalog_group_members(path TEXT,group_id TEXT);CREATE TABLE reacquire_markers(snapshot TEXT,state TEXT);')
        self.index=OwnershipIndex();self.name=os.path.normcase('C:/library/Автор/Обложка.JPG')
    def tearDown(self):self.db.close()
    def held(self,job='own',candidate='mine'):
        tables={row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return self.index.held(self.db,tables,job,candidate,{self.name})
    def add_job(self,id='other',state='pending'):
        self.db.execute('INSERT INTO audio_jobs VALUES(?,?,?,0)',(id,json.dumps({'sources':[],'cover':{'path':'C:/library/Автор/Обложка.JPG'}}),state));self.db.commit()
    def test_other_active_cover_is_held_with_unicode_case(self):
        self.add_job();self.assertEqual(self.held(),{self.name})
    def test_same_job_reference_is_not_another_owner(self):
        self.add_job('own');self.assertEqual(self.held(),set())
    def test_progress_and_cleanup_receipts_reuse_projection(self):
        self.add_job();self.held();token=self.index.token
        self.db.execute('UPDATE audio_jobs SET progress=50');self.db.commit()
        with patch('cleanup_ownership.json.loads',side_effect=AssertionError('no reparse for progress')):self.assertEqual(self.held(),{self.name})
        self.assertEqual(token,self.index.token)
    def test_manifest_change_invalidates_before_next_file(self):
        self.add_job();self.held()
        self.db.execute('UPDATE audio_jobs SET manifest=?',(json.dumps({'sources':[],'cover':None}),));self.db.commit()
        self.assertEqual(self.held(),set())
    def test_new_candidate_and_supersession_invalidate(self):
        self.assertEqual(self.held(),set())
        self.db.execute("INSERT INTO book_groups VALUES('another',0)")
        self.db.execute('INSERT INTO catalog_group_members VALUES(?,?)',(self.name,'another'));self.db.commit()
        self.assertEqual(self.held(),{self.name})
        self.db.execute("UPDATE book_groups SET superseded=1 WHERE id='another'");self.db.commit()
        self.assertEqual(self.held(),set())
    def test_set_aside_history_does_not_hold_cover(self):
        self.add_job();self.assertEqual(self.held(),{self.name})
        self.db.execute('CREATE TABLE audio_job_set_aside(job_id TEXT PRIMARY KEY)');self.db.execute("INSERT INTO audio_job_set_aside VALUES('other')");self.db.commit()
        self.assertEqual(self.held(),set())
    def test_reacquire_record_holds_until_archived(self):
        self.held();self.db.execute('INSERT INTO reacquire_markers VALUES(?,?)',(json.dumps({'members':[{'path':self.name}]}),'needed'));self.db.commit()
        self.assertEqual(self.held(),{self.name})
        self.db.execute("UPDATE reacquire_markers SET state='archived'");self.db.commit();self.assertEqual(self.held(),set())
    def test_current_candidate_reference_is_not_another_owner(self):
        self.db.execute("INSERT INTO book_groups VALUES('mine',0)");self.db.execute('INSERT INTO catalog_group_members VALUES(?,?)',(self.name,'mine'));self.db.commit()
        self.assertEqual(self.held(),set())

if __name__=='__main__':unittest.main()
