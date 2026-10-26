"""Private candidate-record contention and Start-gate regressions; no live libraries.
Import creates only the declared isolated fixture parent. Execute only through a
separately reviewed owned graph; this module is preparation until then.
"""
import contextlib
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import Mock,patch
import scanner
import sqlite_retry
from automatic_processing import AutomaticProcessing

AREA=Path(__file__).resolve().parents[1]/'scratch'/'automatic-record-retry-fixtures'
AREA.mkdir(parents=True,exist_ok=True)

class AutomaticRecordRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA)
        self.database=Path(self.temp.name)/'private.sqlite3'
        self.holders=[];self.threads=[]
        self.inventory=SimpleNamespace(database=self.database,roots={'Audiobooks':str(Path(self.temp.name)/'sources')},output_root=str(Path(self.temp.name)/'sorted'),worker=None,stop=Mock())
        self.merge=SimpleNamespace(inventory=self.inventory,state=Mock(return_value={'state':'Completed','queued':0,'cleanup_active':False}),_no_scan=Mock(),pause=Mock(),approve_automatic=Mock(),candidate_status=Mock(return_value=None))
        self.research=SimpleNamespace(lookup=Mock(),client=object())
        self.auto=AutomaticProcessing(self.merge,research=self.research)
        self.row={'id':str(uuid.uuid4()),'revision':2,'fingerprint':'new-fingerprint','title_clue':'Private fixture','members':[]}
        self.run=str(uuid.uuid4());self.checkpoint=json.dumps({'pending':[self.row['id']],'done':['protected-book']})
        with scanner.connect(self.database) as db:
            db.execute('INSERT INTO automatic_runs VALUES(?,?,?,?,?,?,?,0)',(self.run,'Running','research',self.checkpoint,'','1','1'))
            db.execute('CREATE TABLE protected_outputs(id TEXT PRIMARY KEY,proof TEXT)')
            db.execute("INSERT INTO protected_outputs VALUES('protected-book','exact-publication-proof')")
    def tearDown(self):
        self.auto.stop_event.set()
        for db in self.holders:
            try:db.rollback();db.close()
            except sqlite3.ProgrammingError:pass
        for thread in self.threads:
            thread.join(3);self.assertFalse(thread.is_alive(),'Private fixture thread did not close')
        self.temp.cleanup()
    def holder(self):
        db=sqlite3.connect(self.database,check_same_thread=False)
        db.execute('BEGIN IMMEDIATE');self.holders.append(db);return db
    def release_later(self,db,commit=False):
        def release():
            time.sleep(.4)
            db.commit() if commit else db.rollback()
            db.close()
        thread=threading.Thread(target=release);self.threads.append(thread);thread.start()
    def seed(self,result=None,revision=None,fingerprint=None):
        result=result or {'research_attempt':2,'research_history':[{'attempt':2,'state':'Held'}]}
        with scanner.connect(self.database) as db:
            db.execute('INSERT OR REPLACE INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',(self.row['id'],revision or self.row['revision'],fingerprint or self.row['fingerprint'],'Held',json.dumps(result),123,'old-time','old-version'))
    def saved(self):
        with scanner.connect(self.database) as db:
            candidate=db.execute('SELECT * FROM automatic_candidates WHERE id=?',(self.row['id'],)).fetchone()
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM protected_outputs')],[('protected-book','exact-publication-proof')])
            self.assertEqual(db.execute('SELECT checkpoint FROM automatic_runs WHERE id=?',(self.run,)).fetchone()[0],self.checkpoint)
            self.assertEqual(db.execute('SELECT count(*) FROM automatic_errors').fetchone()[0],0)
        return dict(candidate) if candidate else None
    def set_paused(self):
        with scanner.connect(self.database) as db:db.execute("UPDATE automatic_runs SET state='Paused' WHERE id=?",(self.run,))

    def test_real_writer_commits_fresh_history_before_one_record(self):
        self.seed();holder=self.holder()
        latest={'research_attempt':7,'research_history':[{'attempt':7,'state':'Held'}],'source_refresh':{'revision':2,'evidence':'retained'}}
        holder.execute('UPDATE automatic_candidates SET result=? WHERE id=?',(json.dumps(latest),self.row['id']))
        self.release_later(holder,commit=True)
        supplied={'reasons':['Uncertain'],'sources':[{'url':'https://example.org/private','sha256':'proof','kind':'fixture'}]};original=copy.deepcopy(supplied)
        self.auto._record(self.row,'Held',supplied,456)
        value=self.saved();result=json.loads(value['result'])
        self.assertEqual(result['research_attempt'],8);self.assertEqual([h['attempt'] for h in result['research_history']],[7,8])
        self.assertEqual(result['source_refresh'],latest['source_refresh']);self.assertEqual(supplied,original);self.assertEqual(value['retry_at'],456)
    def test_retry_after_partial_insert_rolls_back_attempt_and_history(self):
        self.seed();original_connect=sqlite_retry.connect;inserts=[]
        error=sqlite3.OperationalError('native busy fixture');error.sqlite_errorcode=sqlite3.SQLITE_BUSY
        @contextlib.contextmanager
        def connection(*args,**kwargs):
            with original_connect(*args,**kwargs) as db:
                class Proxy:
                    def execute(_,sql,*values):
                        result=db.execute(sql,*values)
                        if sql.startswith('INSERT OR REPLACE INTO automatic_candidates'):
                            inserts.append(1)
                            if len(inserts)==1:raise error
                        return result
                yield Proxy()
        with patch.object(sqlite_retry,'connect',connection):self.auto._record(self.row,'Held',{'reasons':['Uncertain']})
        result=json.loads(self.saved()['result'])
        self.assertEqual(len(inserts),2);self.assertEqual(result['research_attempt'],3)
        self.assertEqual([h['attempt'] for h in result['research_history']],[2,3])
    def test_persistent_busy_preserves_existing_candidate_and_checkpoint(self):
        self.seed();before=self.saved();holder=self.holder()
        with patch.object(sqlite_retry,'BUSY_SECONDS',.2),patch.object(sqlite_retry,'BUSY_ATTEMPTS',1):
            with self.assertRaises(sqlite3.OperationalError) as caught:self.auto._record(self.row,'Queued',{'reasons':[]})
        self.assertEqual(caught.exception.sqlite_errorcode&255,sqlite3.SQLITE_BUSY)
        holder.rollback();holder.close();self.assertEqual(self.saved(),before)
    def test_stop_during_worker_busy_wait_never_records_or_restarts(self):
        self.seed();before=self.saved();holder=self.holder();caught=[]
        def worker():
            try:self.auto._record(self.row,'Held',{'reasons':['must not commit']})
            except BaseException as error:caught.append(error)
        thread=threading.Thread(target=worker);self.auto.thread=thread;self.threads.append(thread);thread.start()
        time.sleep(.05);self.auto.stop_event.set();thread.join(2)
        self.assertFalse(thread.is_alive());self.assertEqual(len(caught),1);self.assertIsInstance(caught[0],InterruptedError)
        holder.rollback();holder.close();self.assertEqual(self.saved(),before);self.research.lookup.assert_not_called();self.merge.approve_automatic.assert_not_called()
    def test_nonworker_record_preserves_existing_stop_semantics(self):
        self.auto.stop_event.set();self.auto._record(self.row,'Pending')
        self.assertEqual(self.saved()['state'],'Pending');self.assertIsNone(self.auto.thread)
    def test_locked_corrupt_and_message_only_errors_are_not_replayed(self):
        self.seed();before=self.saved();original_connect=sqlite_retry.connect
        for code in (sqlite3.SQLITE_LOCKED,sqlite3.SQLITE_CORRUPT,None):
            error=sqlite3.OperationalError('database is locked')
            if code is not None:error.sqlite_errorcode=code
            calls=[]
            @contextlib.contextmanager
            def connection(*args,**kwargs):
                with original_connect(*args,**kwargs) as db:
                    class Proxy:
                        def execute(_,sql,*values):
                            if sql.startswith('SELECT revision,fingerprint'):
                                calls.append(1);raise error
                            return db.execute(sql,*values)
                    yield Proxy()
            with self.subTest(code=code),patch.object(sqlite_retry,'connect',connection):
                with self.assertRaises(sqlite3.OperationalError):self.auto._record(self.row,'Held')
            self.assertEqual(len(calls),1);self.assertEqual(self.saved(),before)
    def test_revision_change_retains_old_provenance_without_old_refresh(self):
        self.seed({'research_attempt':3,'research_history':[],'reasons':['old reason'],'sources':[{'url':'https://example.org/old','sha256':'old','kind':'fixture'}],'source_refresh':{'old':True}},revision=1,fingerprint='old-fingerprint')
        self.auto._record(self.row,'Waiting for source',{'reasons':['new reason']},500)
        value=json.loads(self.saved()['result']);self.assertEqual(value['research_attempt'],4)
        self.assertEqual(len(value['research_history']),2);self.assertEqual(value['research_history'][0]['fingerprint'],'old-fingerprint')
        self.assertEqual(value['research_history'][0]['sources'][0]['sha256'],'old');self.assertNotIn('source_refresh',value)
    def test_history_cap_and_explicit_refresh_survive_retry(self):
        self.seed({'research_attempt':25,'research_history':[{'attempt':i} for i in range(1,26)],'source_refresh':{'old':True}})
        self.auto._record(self.row,'Queued',{'source_refresh':{'new':True}})
        value=json.loads(self.saved()['result']);self.assertEqual(value['research_attempt'],26);self.assertEqual(len(value['research_history']),20)
        self.assertEqual(value['research_history'][-1]['attempt'],26);self.assertEqual(value['source_refresh'],{'new':True})
    def test_actual_worker_does_not_refetch_or_readmit_after_record_busy(self):
        self.merge.reviews=SimpleNamespace(_row=lambda *_:self.row)
        self.auto.manual_draft=lambda _:False;self.auto._refresh_observed_sources=lambda *_:None
        def lookup(*_):
            holder=self.holder();self.release_later(holder)
            return {'reasons':['Uncertain private evidence'],'sources':[]}
        self.research.lookup.side_effect=lookup
        original=self.auto._record
        def record(row,state,*args):
            original(row,state,*args)
            if state=='Held':self.auto.stop_event.set()
        self.auto._record=record
        thread=threading.Thread(target=self.auto._work,args=(self.run,));self.auto.thread=thread;self.threads.append(thread);thread.start();thread.join(3)
        self.assertFalse(thread.is_alive());self.research.lookup.assert_called_once();self.merge.approve_automatic.assert_not_called()
        with scanner.connect(self.database) as db:
            candidate=dict(db.execute('SELECT * FROM automatic_candidates WHERE id=?',(self.row['id'],)).fetchone())
            run=dict(db.execute('SELECT * FROM automatic_runs WHERE id=?',(self.run,)).fetchone())
            self.assertEqual(db.execute('SELECT count(*) FROM automatic_errors').fetchone()[0],0)
        self.assertEqual(candidate['state'],'Held');self.assertEqual(json.loads(candidate['result'])['research_attempt'],1)
        self.assertEqual(run['state'],'Paused');checkpoint=json.loads(run['checkpoint'])
        # Ruling 5 (2026-10-24): a held book is held until it changes, so it is done for this run, not deferred.
        self.assertIn(self.row['id'],checkpoint['done']);self.assertIn('protected-book',checkpoint['done'])

    def test_running_and_pausing_audio_disable_start_without_changing_lifecycle(self):
        self.set_paused()
        for state,reason in [('Pausing','Audiobook jobs are pausing.')]:
            value=self.auto.status(jobs={'state':state},scanning=False)
            self.assertEqual(value['state'],'Paused');self.assertFalse(value['can_start']);self.assertTrue(value['start_block_reason'].startswith(reason))
        # Ruling 34 (Sergei 2026-10-26, option A): a running conversion no longer disables Start.
        value=self.auto.status(jobs={'state':'Running'},scanning=False)
        self.assertEqual(value['state'],'Paused');self.assertTrue(value['can_start']);self.assertEqual(value['start_block_reason'],'')
    def test_discovery_closed_failed_checkpoint_and_unknown_gates(self):
        self.set_paused()
        cases=[({'jobs':{'state':'Paused'},'scanning':True},'Discovery is in progress.'),({'jobs':{'state':'Paused'},'server_closing':True},'The local server is stopping or stopped.'),({'jobs':{'state':'unrecognized'}},'Start availability is unknown.')]
        for args,reason in cases:
            value=self.auto.status(**args);self.assertFalse(value['can_start']);self.assertTrue(value['start_block_reason'].startswith(reason))
        self.auto.volatile_failure={'diagnostic':{'candidate_id':self.row['id']},'reason':'unsaved'}
        value=self.auto.status(jobs={'state':'Paused'},scanning=False)
        self.assertFalse(value['can_start']);self.assertIn('failure record could not be saved',value['start_block_reason'])
    def test_available_status_uses_supplied_snapshot_without_merge_lock(self):
        self.set_paused();self.merge.state.side_effect=AssertionError('status must not acquire merge snapshot/locks')
        with self.auto.lock:value=self.auto.status(jobs={'state':'Paused'},scanning=False)
        self.assertTrue(value['can_start']);self.assertEqual(value['start_block_reason'],'');self.merge.state.assert_not_called()
    def test_running_stopping_and_missing_telemetry_do_not_advertise_start(self):
        value=self.auto.status(jobs={'state':'Paused'});self.assertFalse(value['can_start']);self.assertEqual(value['start_block_reason'],'Automatic processing is already running.')
        with scanner.connect(self.database) as db:db.execute("UPDATE automatic_runs SET state='Stopping'")
        value=self.auto.status(jobs={'state':'Paused'});self.assertFalse(value['can_start']);self.assertTrue(value['start_block_reason'].startswith('Automatic processing is stopping.'))
        self.set_paused();value=self.auto.status();self.assertFalse(value['can_start']);self.assertTrue(value['start_block_reason'].startswith('Start availability is unknown.'))
    def test_start_revalidates_new_audio_conflict_before_any_mutation(self):
        self.set_paused();self.assertTrue(self.auto.status(jobs={'state':'Paused'},scanning=False)['can_start'])
        # Ruling 34 (Sergei 2026-10-26): a running conversion no longer blocks Start; jobs still pausing do.
        self.merge.state.return_value={'state':'Pausing'}
        with self.assertRaisesRegex(ValueError,'Audiobook jobs are pausing'):self.auto.start()
        self.assertIsNone(self.auto.thread);self.research.lookup.assert_not_called();self.merge.approve_automatic.assert_not_called()
        self.assertEqual(self.auto._run_row()['state'],'Paused')
    def test_start_revalidates_scan_before_any_worker_or_checkpoint(self):
        self.set_paused();self.inventory.worker=SimpleNamespace(is_alive=lambda:True)
        with self.assertRaisesRegex(ValueError,'Discovery is in progress'):self.auto.start()
        self.assertIsNone(self.auto.thread);self.assertEqual(self.auto._run_row()['state'],'Paused')


class MediaDeadlineTests(unittest.TestCase):
    setUp=AutomaticRecordRetryTests.setUp;tearDown=AutomaticRecordRetryTests.tearDown  # the same private fixture, not its tests
    """Sergei 2026-10-26 (0.22.2): «Потаённое окно в потаённый сад» and «Регуляторы» were "Needs you — This book needs
    your decision. Reason: Owned media operation exceeded its deadline". A media check that runs past its deadline (a busy
    machine, a slow library drive) is transient: the book waits and is tried again by itself, with backoff; only after
    MEDIA_TRIES in a row is it held, with a plain reason and what to do, never the raw text."""
    def attempt(self,error,previous=None):
        import audio_pipeline  # noqa: F401  the class the pipeline raises
        if previous is not None:
            with scanner.connect(self.database) as db:
                db.execute('INSERT OR REPLACE INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',(self.row['id'],self.row['revision'],self.row['fingerprint'],previous[0],json.dumps(previous[1]),1,'old-time','old-version'))
        self.merge.reviews=SimpleNamespace(_row=lambda *_:self.row)
        self.auto.manual_draft=lambda _:False;self.auto._refresh_observed_sources=lambda *_:None;self.auto.clock=lambda:1000.0
        self.research.lookup.side_effect=lambda *_:{'reasons':[],'sources':[{'kind':'local_agreement'}],'review':{'title':'T'}}
        self.merge.approve_automatic=Mock(side_effect=error)
        original=self.auto._record
        def record(row,state,*args):
            original(row,state,*args)
            if state in ('Held','Waiting for source'):self.auto.stop_event.set()
        self.auto._record=record
        thread=threading.Thread(target=self.auto._work,args=(self.run,));self.auto.thread=thread;self.threads.append(thread);thread.start();thread.join(5)
        self.assertFalse(thread.is_alive());self.merge.approve_automatic.assert_called_once()
        with scanner.connect(self.database) as db:
            candidate=dict(db.execute('SELECT * FROM automatic_candidates WHERE id=?',(self.row['id'],)).fetchone())
        return candidate,json.loads(candidate['result'])

    def test_a_media_deadline_waits_and_is_tried_again_by_itself(self):
        from audio_pipeline import MediaTimeout
        import automatic_processing
        candidate,result=self.attempt(MediaTimeout('Owned media operation exceeded its deadline'))
        self.assertEqual(candidate['state'],'Waiting for source','a wait, never a "Needs you" decision')
        self.assertEqual((result['wait']['kind'],result['media_timeouts']),('media_slow',1))
        self.assertEqual(result['reasons'],[automatic_processing.MEDIA_WAIT],'never the raw "Owned media operation exceeded its deadline"')
        self.assertEqual(candidate['retry_at'],1000.0+automatic_processing.MEDIA_BACKOFF,'tried again in two minutes')

    def test_the_backoff_doubles_and_after_repeated_deadlines_the_book_is_held_with_what_to_do(self):
        from audio_pipeline import MediaTimeout
        import automatic_processing
        previous={'research_attempt':3,'media_timeouts':2,'reasons':[automatic_processing.MEDIA_WAIT],'wait':{'kind':'media_slow'}}
        candidate,result=self.attempt(MediaTimeout('Owned media operation exceeded its deadline'),('Waiting for source',previous))
        self.assertEqual((candidate['state'],result['media_timeouts'],candidate['retry_at']),('Waiting for source',3,1000.0+automatic_processing.MEDIA_BACKOFF*4))
        self.auto.stop_event.clear();self.auto._record=AutomaticProcessing._record.__get__(self.auto)
        previous=dict(previous,media_timeouts=automatic_processing.MEDIA_TRIES-1)
        candidate,result=self.attempt(MediaTimeout('Owned media operation exceeded its deadline'),('Waiting for source',previous))
        self.assertEqual(candidate['state'],'Held')
        self.assertEqual(result['reasons'],[automatic_processing.MEDIA_HELD],'a plain reason with what to do')
        self.assertNotIn('Owned media operation', json.dumps(result['reasons']))

    def test_any_other_check_failure_is_held_as_before(self):
        candidate,result=self.attempt(ValueError('Source files changed'))
        self.assertEqual((candidate['state'],result['reasons']),('Held',['Source files changed']))
        self.assertNotIn('media_timeouts',result)

    def test_the_pipeline_raises_a_media_timeout_that_is_still_a_timeout(self):
        from audio_pipeline import MediaTimeout,run_owned
        self.assertTrue(issubclass(MediaTimeout,TimeoutError),'every existing TimeoutError handler still catches it')
        import sys
        stage=Path(self.temp.name)/'stage';stage.mkdir()
        with self.assertRaises(MediaTimeout):
            run_owned([sys.executable,'-c','import time;time.sleep(5)'],stage,threading.Event(),deadline=.3)

if __name__=='__main__':unittest.main()
