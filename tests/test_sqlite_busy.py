"""Real private WAL contention; no live database, media or Internet access."""
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
from public_research import PublicClient

AREA=Path(__file__).resolve().parents[1]/'scratch'/'sqlite-busy-fixtures'
AREA.mkdir(parents=True,exist_ok=True)

class BusyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA)
        self.database=Path(self.temp.name)/'private.sqlite3'
        self.holders=[];self.threads=[]
        self.auto=AutomaticProcessing(SimpleNamespace(inventory=SimpleNamespace(database=self.database)),research=object())
        self.run='private-run'
        self.checkpoint=json.dumps({'pending':['private-book'],'done':['completed-1','completed-2','completed-3','completed-4']})
        with scanner.connect(self.database) as db:
            db.execute('INSERT INTO automatic_runs VALUES(?,?,?,?,?,?,?,0)',(self.run,'Running','research',self.checkpoint,'','1','1'))
            db.execute('CREATE TABLE protected_outputs(id TEXT PRIMARY KEY, proof TEXT)')
            db.executemany('INSERT INTO protected_outputs VALUES(?,?)',[(str(i),'immutable-proof-'+str(i)) for i in range(4)])
    def tearDown(self):
        for holder in self.holders:
            try:holder.rollback();holder.close()
            except sqlite3.ProgrammingError:pass
        for thread in self.threads:
            thread.join(3);self.assertFalse(thread.is_alive())
        self.temp.cleanup()
    def holder(self):
        db=sqlite3.connect(self.database,check_same_thread=False)
        db.execute('BEGIN IMMEDIATE');self.holders.append(db);return db
    def release_later(self,db):
        thread=threading.Thread(target=lambda:(time.sleep(.65),db.rollback(),db.close()))
        self.threads.append(thread);thread.start()
    def saved(self):
        with scanner.connect(self.database) as db:
            result=dict(db.execute('SELECT * FROM automatic_runs WHERE id=?',(self.run,)).fetchone())
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM protected_outputs ORDER BY id')],[(str(i),'immutable-proof-'+str(i)) for i in range(4)])
        return result
    def busy(self):
        holder=self.holder()
        db=sqlite3.connect(self.database,timeout=0)
        try:
            db.execute('UPDATE automatic_runs SET reason=?',('blocked',))
        except sqlite3.OperationalError as error:return error
        finally:db.close();holder.rollback();holder.close()
        self.fail('Real SQLITE_BUSY was not produced')
    def test_checkpoint_recovers_real_writer_lock_preserves_four_completed(self):
        holder=self.holder();self.release_later(holder)
        self.auto._update(self.run,reason='continued')
        saved=self.saved();self.assertEqual(saved['reason'],'continued');self.assertEqual(saved['checkpoint'],self.checkpoint)
    def test_checkpoint_stop_interrupts_wait_without_advancing(self):
        holder=self.holder();caught=[]
        def worker():
            try:self.auto._update(self.run,checkpoint='must-not-save')
            except BaseException as error:caught.append(error)
        thread=threading.Thread(target=worker);self.auto.thread=thread;self.threads.append(thread);thread.start()
        time.sleep(.1);self.auto.stop_event.set();thread.join(2);self.assertFalse(thread.is_alive())
        self.assertEqual(len(caught),1);self.assertIsInstance(caught[0],InterruptedError)
        holder.rollback();holder.close();self.assertEqual(self.saved()['checkpoint'],self.checkpoint)
    def test_paused_checkpoint_still_persists_with_stop_set(self):
        self.auto.stop_event.set();self.auto.thread=threading.current_thread()
        holder=self.holder();self.release_later(holder)
        self.auto._update(self.run,state='Paused',checkpoint=self.checkpoint)
        self.assertEqual(self.saved()['state'],'Paused')
    def test_restart_keeps_saved_progress_paused_never_starts_worker(self):
        second=AutomaticProcessing(SimpleNamespace(inventory=SimpleNamespace(database=self.database)),research=object())
        saved=self.saved();self.assertEqual(saved['state'],'Paused');self.assertEqual(saved['checkpoint'],self.checkpoint)
        self.assertIsNone(second.thread);self.assertTrue(saved['restart_paused'])
    def test_persistent_busy_bounded_and_checkpoint_unchanged(self):
        holder=self.holder();begin=time.monotonic()
        with patch.object(sqlite_retry,'BUSY_SECONDS',.45),patch.object(sqlite_retry,'BUSY_ATTEMPTS',3):
            with self.assertRaises(sqlite3.OperationalError) as caught:self.auto._update(self.run,checkpoint='must-not-save')
        self.assertEqual(caught.exception.sqlite_errorcode&255,sqlite3.SQLITE_BUSY)
        self.assertLess(time.monotonic()-begin,1.5)
        holder.rollback();holder.close();self.assertEqual(self.saved()['checkpoint'],self.checkpoint)
    def test_partial_transaction_rolls_back_before_one_successful_replay(self):
        error=self.busy();calls=[]
        def operation(db):
            calls.append(1);db.execute("UPDATE automatic_runs SET reason=reason||'x'")
            if len(calls)==1:raise error
        sqlite_retry.transaction(self.database,operation)
        self.assertEqual(len(calls),2);self.assertEqual(self.saved()['reason'],'x')
    def test_nonbusy_and_message_only_errors_never_retry(self):
        for error in (sqlite3.OperationalError('database is locked'),sqlite3.OperationalError('other')):
            calls=[]
            def operation(db):calls.append(1);raise error
            with self.assertRaises(sqlite3.OperationalError):sqlite_retry.transaction(self.database,operation)
            self.assertEqual(len(calls),1)
    def test_nonbusy_native_operational_error_never_retry(self):
        calls=[]
        def operation(db):calls.append(1);db.execute('SELECT * FROM absent_private_table')
        with self.assertRaises(sqlite3.OperationalError) as caught:sqlite_retry.transaction(self.database,operation)
        self.assertEqual(caught.exception.sqlite_errorcode,sqlite3.SQLITE_ERROR);self.assertEqual(len(calls),1)
    def test_failed_connection_initialization_is_closed(self):
        with scanner.connect(self.database) as db:db.execute('DROP TABLE scan_outcomes')
        holder=self.holder();connections=[];original=sqlite3.connect
        class Closing(scanner.ClosingConnection):
            def close(self):self.was_closed=True;super().close()
        def opened(*args,**kwargs):
            kwargs['factory']=Closing;db=original(*args,**kwargs);db.was_closed=False;connections.append(db);return db
        with patch.object(scanner.sqlite3,'connect',opened):
            with self.assertRaises(sqlite3.OperationalError):scanner.connect(self.database,timeout=.01)
        self.assertEqual(len(connections),1);self.assertTrue(connections[0].was_closed)
    def test_cache_retry_never_repeats_request_or_spends_budget_twice(self):
        calls=[]
        def fetch(*_):
            calls.append(1);holder=self.holder();self.release_later(holder);return b'private fetched evidence'
        client=PublicClient(self.database,fetch=fetch,clock=lambda:100000)
        budget={'remaining':2}
        self.assertEqual(client.read('https://ast.ru/book/private',budget=budget),b'private fetched evidence')
        self.assertEqual(client.read('https://ast.ru/book/private',budget=budget),b'private fetched evidence')
        self.assertEqual((len(calls),budget['remaining']),(1,1))
        with scanner.connect(self.database) as db:self.assertEqual(db.execute('SELECT count(*) FROM public_research_requests').fetchone()[0],1)
    def test_cache_stop_does_not_refetch_or_claim_evidence_receipt(self):
        stop=threading.Event();calls=[]
        def fetch(*_):calls.append(1);stop.set();return b'private fetched evidence'
        client=PublicClient(self.database,fetch=fetch,clock=lambda:100000)
        with self.assertRaises(InterruptedError):client.read('https://ast.ru/book/private',stop,{'remaining':2})
        with self.assertRaises(ValueError):client.receipt('https://ast.ru/book/private')
        self.assertEqual(len(calls),1)
    def test_failure_persistence_recovers_once_without_restarting(self):
        error=self.busy();holder=self.holder();self.release_later(holder)
        self.auto._failure(self.run,error,'research',None,None,True)
        self.assertIsNone(self.auto.volatile_failure);self.assertIsNone(self.auto.thread)
        self.assertEqual(self.saved()['state'],'Needs attention')
        with scanner.connect(self.database) as db:self.assertEqual(db.execute('SELECT count(*) FROM automatic_errors').fetchone()[0],1)
    def test_failure_persistence_exhaustion_stays_volatile_and_blocks_start(self):
        error=self.busy();holder=self.holder()
        with patch.object(sqlite_retry,'BUSY_SECONDS',.2),patch.object(sqlite_retry,'BUSY_ATTEMPTS',1):self.auto._failure(self.run,error,'research',None,None,True)
        self.assertIsNotNone(self.auto.volatile_failure)
        with self.assertRaisesRegex(ValueError,'Failure checkpoint could not be saved'):self.auto.start()
        holder.rollback();holder.close()
        self.assertEqual(self.saved()['checkpoint'],self.checkpoint)
        with scanner.connect(self.database) as db:self.assertEqual(db.execute('SELECT count(*) FROM automatic_errors').fetchone()[0],0)
    def test_supported_stop_recovers_busy_atomic_pause_and_restart_remains_paused(self):
        identity=str(uuid.uuid4());row={'id':identity,'revision':1,'fingerprint':'private','members':[],'title_clue':'Private book'}
        checkpoint={'pending':[identity],'done':['completed-1','completed-2','completed-3','completed-4']}
        self.auto._update(self.run,checkpoint=json.dumps(checkpoint))
        self.auto.inventory.roots={'Audiobooks':str(self.database.parent/'private-sources')}
        self.auto.inventory.worker=None;self.auto.inventory.stop=Mock()
        self.auto.merge.state=lambda:{'state':'Completed','queued':0,'cleanup_active':False}
        self.auto.merge._no_scan=lambda:None;self.auto.merge.pause=Mock()
        self.auto.merge.candidate_status=lambda _:None
        self.auto.merge.reviews=SimpleNamespace(_row=lambda *_:row)
        self.auto.manual_draft=lambda _:True
        self.auto.start();self.threads.append(self.auto.thread)
        deadline=time.monotonic()+3
        while self.auto.next_retry_at is None and time.monotonic()<deadline:time.sleep(.01)
        self.assertIsNotNone(self.auto.next_retry_at)
        original=self.auto._update
        def update(id,**fields):
            original(id,**fields)
            if fields.get('state')=='Stopping':
                holder=self.holder();self.release_later(holder)
        with patch.object(self.auto,'_update',update):self.auto.stop()
        self.auto.thread.join(3);self.assertFalse(self.auto.thread.is_alive())
        saved=self.saved();self.assertEqual(saved['state'],'Paused')
        final=json.loads(saved['checkpoint']);self.assertIn(identity,final['pending']);self.assertEqual(final['done'][:4],checkpoint['done'])
        self.assertIsNone(self.auto.volatile_failure);self.auto.inventory.stop.assert_called();self.auto.merge.pause.assert_called()
        second=AutomaticProcessing(SimpleNamespace(inventory=SimpleNamespace(database=self.database)),research=object())
        self.assertEqual(self.saved()['state'],'Paused');self.assertIsNone(second.thread)
    def test_atomic_pause_exhaustion_never_claims_saved_or_resets_candidate(self):
        with scanner.connect(self.database) as db:db.execute('INSERT INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',('private-book',1,'private','Researching','{}',None,'1','1'))
        holder=self.holder()
        with patch.object(sqlite_retry,'BUSY_SECONDS',.2),patch.object(sqlite_retry,'BUSY_ATTEMPTS',1):
            with self.assertRaises(sqlite3.OperationalError):self.auto._paused_checkpoint(self.run,{'pending':['must-not-save']})
        holder.rollback();holder.close()
        saved=self.saved();self.assertEqual(saved['state'],'Running');self.assertEqual(saved['checkpoint'],self.checkpoint)
        with scanner.connect(self.database) as db:self.assertEqual(db.execute('SELECT state FROM automatic_candidates').fetchone()[0],'Researching')
    def test_supported_stale_stop_cannot_overwrite_committed_paused_checkpoint(self):
        stale=self.auto._run_row()
        self.auto._paused_checkpoint(self.run,json.loads(self.checkpoint))
        self.auto.inventory.stop=Mock();self.auto.merge.pause=Mock()
        original=self.auto._run_row;reads=[]
        def read():reads.append(1);return stale if len(reads)==1 else original()
        with patch.object(self.auto,'_run_row',side_effect=read):state=self.auto.stop()
        self.assertEqual(state['state'],'Paused');self.assertTrue(self.auto.stop_event.is_set())
        saved=self.saved();self.assertEqual(saved['state'],'Paused');self.assertEqual(saved['checkpoint'],self.checkpoint)
        self.auto.inventory.stop.assert_called_once();self.auto.merge.pause.assert_called_once()

if __name__=='__main__':unittest.main()
