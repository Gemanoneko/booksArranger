"""Synthetic catalog contention regressions. Written for the declared QA graph; no live catalog."""
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import catalog_contention as contention
import groups
import scanner
import sqlite_retry
from scanner import Inventory,connect

SCRATCH=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'catalog-contention'


def busy(code=sqlite3.SQLITE_BUSY):
    error=sqlite3.OperationalError('synthetic database contention')
    error.sqlite_errorcode=code
    return error


class CatalogContentionTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True,exist_ok=True)
        self.base=Path(tempfile.mkdtemp(prefix='case-',dir=SCRATCH))
        self.root=self.base/'audio';self.root.mkdir()
        self.roots={'Audiobooks':str(self.root),'Podcasts':str(self.root/'Podcasts'),'Ebooks':str(self.base/'ebooks')}
        self.db=self.base/'state'/'inventory.sqlite3';self.calls=[]
        def reader(path,kind,stop):
            self.calls.append(path)
            return {'title':'Book','author':'Writer','tags':{'album':'Book','artist':'Writer'}}
        self.inv=Inventory(self.db,self.roots,reader,output_root=str(self.base/'sorted'))
        self.path=self.root/'Book'/'01.mp3';self.path.parent.mkdir();self.path.write_bytes(b'synthetic audio')
        with connect(self.db) as db:
            db.execute("INSERT INTO jobs(root,label,generation,state) VALUES(?,?,1,'scanning')",(str(self.root),'Audiobooks'))
            db.execute("INSERT INTO queue(root,generation,path,directory,state) VALUES(?,1,?,0,'running')",(str(self.root),str(self.path)))
            db.execute("INSERT INTO files(root,path,size,modified,seen,kind,arrival,metadata,error,missing,review) VALUES(?,?,0,0,0,'audiobook',0,'{}','',0,'saved-review')",(str(self.root),str(self.path)))
            db.execute('CREATE TABLE tally(n INTEGER)');db.execute('INSERT INTO tally VALUES(0)')
        self.short=patch.multiple(sqlite_retry,BUSY_SECONDS=.2,BUSY_ATTEMPTS=3);self.short.start();self.addCleanup(self.short.stop)

    def row(self,table):
        with connect(self.db) as db:return dict(db.execute('SELECT * FROM '+table).fetchone())

    def inject_after_write_once(self):
        original=contention.write;attempts=[]
        def replay(database,operation,stop=None):
            def wrapped(db):
                result=operation(db);attempts.append(1)
                if len(attempts)==1:raise busy()
                return result
            return original(database,wrapped,stop)
        return patch.object(contention,'write',side_effect=replay),attempts

    def test_transient_busy_rolls_back_before_replaying_only_sql(self):
        attempts=[]
        def operation(db):
            db.execute('UPDATE tally SET n=n+1');attempts.append(1)
            if len(attempts)==1:raise busy()
        contention.write(self.db,operation)
        self.assertEqual(len(attempts),2);self.assertEqual(self.row('tally')['n'],1)

    def test_real_other_connection_writer_can_release_without_losing_increment(self):
        acquired=threading.Event();release=threading.Event();errors=[]
        def holder():
            try:
                with connect(self.db) as db:
                    db.execute('BEGIN IMMEDIATE');acquired.set()
                    if not release.wait(2):raise AssertionError('private writer fixture exceeded bound')
            except BaseException as error:errors.append(error);acquired.set()
        thread=threading.Thread(target=holder);thread.start()
        self.assertTrue(acquired.wait(1));timer=threading.Timer(.05,release.set);timer.start()
        try:contention.write(self.db,lambda db:db.execute('UPDATE tally SET n=n+1'))
        finally:release.set();thread.join(2);timer.join(1)
        self.assertFalse(thread.is_alive());self.assertEqual(errors,[]);self.assertEqual(self.row('tally')['n'],1)

    def test_permanent_busy_is_typed_hold_not_media_error(self):
        with self.assertRaises(contention.CatalogHold):
            contention.write(self.db,lambda db:(_ for _ in ()).throw(busy()))
        self.assertEqual(self.row('jobs')['errors'],0);self.assertEqual(self.row('files')['review'],'saved-review')

    def test_locked_and_untyped_database_errors_are_not_retried(self):
        for error in (busy(sqlite3.SQLITE_LOCKED),sqlite3.OperationalError('database is locked')):
            calls=[]
            def operation(db):calls.append(1);raise error
            with self.assertRaises(sqlite3.OperationalError):contention.write(self.db,operation)
            self.assertEqual(calls,[1])

    def test_stop_before_transaction_runs_no_operation(self):
        stop=threading.Event();stop.set();calls=[]
        with self.assertRaises(InterruptedError):contention.write(self.db,lambda db:calls.append(1),stop)
        self.assertEqual(calls,[])

    def test_obsolete_generation_refuses_captured_file_write(self):
        with connect(self.db) as db:expected=contention.file_token(db,str(self.root),str(self.path))
        with connect(self.db) as db:db.execute('UPDATE jobs SET generation=2')
        with self.assertRaises(contention.CatalogHold):
            contention.scan_write(self.inv,str(self.root),1,str(self.path),lambda db:db.execute("UPDATE files SET review=''"),expected)
        self.assertEqual(self.row('files')['review'],'saved-review')

    def test_file_metadata_read_once_despite_sql_rollback_retry(self):
        injected,attempts=self.inject_after_write_once()
        with injected,connect(self.db) as db:self.inv._file(db,'Audiobooks',str(self.root),1,str(self.path))
        self.assertEqual(self.calls,[str(self.path)]);self.assertEqual(len(attempts),2)
        self.assertEqual(self.row('jobs')['checked'],1);self.assertEqual(self.row('queue')['state'],'done')
        self.assertEqual(self.row('scan_outcomes')['outcome'],'success')

    def test_manual_group_context_change_during_read_preserves_review_and_pending(self):
        evidence={'members':[{'path':str(self.path)}]}
        with connect(self.db) as db:
            groups.setup(db)
            db.execute('CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT)')
            db.execute("INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence,review,approved,changed,superseded) VALUES('book',?,'scope',1,'fp',?,'review',1,0,0)",(str(self.root),json.dumps(evidence)))
            db.execute("INSERT INTO candidate_context VALUES('book',1,'{}')")
            db.execute("UPDATE queue SET state='pending'")
        def changed(path,kind,stop):
            self.calls.append(path)
            with connect(self.db) as db:db.execute("UPDATE candidate_context SET data=? WHERE id='book'",(json.dumps({'manual':'new'}),))
            return {'title':'Book','author':'Writer'}
        self.inv.reader=changed
        with patch('reacquire_sources.root_scan_lease',return_value=contextlib.nullcontext(None)):
            self.inv._run('Audiobooks',str(self.root),1)
        self.assertEqual(self.calls,[str(self.path)]);self.assertEqual(self.row('files')['review'],'saved-review')
        self.assertEqual(self.row('jobs')['checked'],0);self.assertEqual(self.row('jobs')['errors'],0)
        self.assertEqual(self.row('queue')['state'],'pending');self.assertEqual(self.row('jobs')['state'],'failed')
        self.assertEqual(json.loads(self.row('candidate_context')['data']),{'manual':'new'})

    def test_old_worker_cannot_replace_new_generation_failure_state(self):
        with connect(self.db) as db:db.execute("UPDATE jobs SET generation=2,current='new worker'")
        with patch('reacquire_sources.root_scan_lease',side_effect=contention.CatalogHold('old worker')):
            self.inv._run('Audiobooks',str(self.root),1)
        self.assertEqual(self.row('jobs')['generation'],2);self.assertEqual(self.row('jobs')['current'],'new worker')
        self.assertEqual(self.row('jobs')['state'],'scanning')

    def test_directory_enumeration_not_repeated_when_entry_sql_retries(self):
        directory=self.root/'Book'
        with connect(self.db) as db:
            db.execute('DELETE FROM queue')
            db.execute("INSERT INTO queue VALUES(?,1,?,1,'running')",(str(self.root),str(directory)))
        original=os.scandir;enumerations=[]
        def scandir(path):enumerations.append(path);return original(path)
        injected,_=self.inject_after_write_once()
        with injected,patch('scanner.os.scandir',side_effect=scandir),connect(self.db) as db:
            self.inv._directory(db,'Audiobooks',str(self.root),1,str(directory))
        self.assertEqual(enumerations,[str(directory)])
        with connect(self.db) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM queue WHERE path=?',(str(self.path),)).fetchone()[0],1)
            self.assertEqual(db.execute('SELECT state FROM queue WHERE path=?',(str(directory),)).fetchone()[0],'done')

    def test_reacquire_native_completion_not_replayed_by_sql_retry(self):
        with connect(self.db) as db:db.execute('DELETE FROM queue')
        injected,_=self.inject_after_write_once()
        with injected,patch('reacquire_sources.root_scan_lease',return_value=contextlib.nullcontext(None)),patch('reacquire_sources.reconcile_scan') as reconcile:
            self.inv._run('Audiobooks',str(self.root),1)
        self.assertEqual(reconcile.call_count,1);self.assertEqual(self.row('jobs')['state'],'completed')

    def test_failed_busy_checkpoint_is_ram_only_not_saved_success(self):
        with connect(self.db) as db:db.execute("UPDATE queue SET state='pending'")
        original=contention.write;calls=[]
        def blocked(database,operation,stop=None):
            calls.append(1)
            if len(calls)>1:
                error=contention.CatalogHold('bounded busy refusal');error.__cause__=busy();raise error
            return original(database,operation,stop)
        with patch.object(contention,'write',side_effect=blocked),patch('reacquire_sources.root_scan_lease',return_value=contextlib.nullcontext(None)):
            self.inv._run('Audiobooks',str(self.root),1)
        self.assertEqual(self.calls,[str(self.path)])
        self.assertEqual(self.row('files')['review'],'saved-review');self.assertEqual(self.row('jobs')['state'],'scanning')
        status=self.inv.source_status(str(self.root))
        self.assertEqual(status['state'],'failed');self.assertIs(status['failure_durable'],False);self.assertEqual(status['pending'],1)
        self.assertEqual(status['errors'],0)

    def test_ram_only_failure_requires_matching_generation_and_ended_worker(self):
        root=str(self.root)
        self.inv._catalog_failures={root:{'root':root,'generation':1,'message':'busy checkpoint unsaved','failure_durable':False}}
        status=self.inv.source_status(root)
        self.assertEqual(status['state'],'failed');self.assertIs(status['failure_durable'],False)
        self.assertEqual(status['pending'],1)
        with connect(self.db) as db:db.execute('UPDATE jobs SET generation=2')
        self.assertEqual(self.inv.source_status(root)['state'],'scanning')
        self.inv._catalog_failures[root]['generation']=2
        self.inv.worker=SimpleNamespace(is_alive=lambda:True)
        self.assertEqual(self.inv.source_status(root)['state'],'scanning')

    def test_ram_failure_does_not_invent_generation_when_catalog_read_fails(self):
        root=str(self.root);self.inv._catalog_failures={root:{'root':root,'generation':1,'message':'unsaved','failure_durable':False}}
        with patch('scanner.connect',side_effect=busy()),self.assertRaisesRegex(contention.CatalogHold,'status unknown'):
            self.inv.source_status(root)

    def test_current_group_revision_and_algorithm_never_reserve_writer(self):
        with connect(self.db) as db:
            groups.setup(db)
            revision=db.execute('SELECT revision FROM book_catalog_revision').fetchone()[0]
            db.execute('INSERT INTO book_group_sync VALUES(?,?)',(str(self.root),revision))
        with patch.object(contention,'write',side_effect=AssertionError('current read acquired writer')):
            with self.inv.group_lock:contention.synchronize_groups(self.inv,[str(self.root)])

    def test_algorithm_change_uses_fresh_immediate_transaction_and_rechecks(self):
        with connect(self.db) as db:
            groups.setup(db);db.execute("UPDATE book_group_algorithm SET version='old'")
            db.execute('INSERT INTO book_group_sync VALUES(?,0)',(str(self.root),))
        original=groups.sync;calls=[]
        def synchronize(db,root):
            self.assertTrue(db.in_transaction)
            # A different connection cannot acquire the writer while stale grouping is changed.
            other=sqlite3.connect(self.db,timeout=0)
            try:
                with self.assertRaises(sqlite3.OperationalError):other.execute('BEGIN IMMEDIATE')
            finally:other.close()
            calls.append(root);return original(db,root)
        with patch('groups.sync',side_effect=synchronize):
            with self.inv.group_lock:contention.synchronize_groups(self.inv,[str(self.root)])
        self.assertEqual(calls,[str(self.root)])


class ProgressSnapshotTests(unittest.TestCase):
    def test_guards_use_one_snapshot_and_every_filesystem_check_follows_close(self):
        from merge_service import MergeService
        import merge_service
        SCRATCH.mkdir(parents=True,exist_ok=True)
        base=Path(tempfile.mkdtemp(prefix='progress-',dir=SCRATCH));database=base/'catalog.sqlite3'
        with connect(database) as db:
            groups.setup(db)
            db.execute('CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT)')
            db.execute('CREATE TABLE audiobook_replacements(id TEXT,candidate_id TEXT,replacement_job_id TEXT,state TEXT,created TEXT)')
            db.execute("INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence,review,approved,changed,superseded) VALUES('book','root','scope',1,'fp','{}','{}',1,0,0)")
            db.execute("INSERT INTO candidate_context VALUES('book',1,?)",(json.dumps({'metadata_approved':True,'cover_id':'cover'}),))
            db.execute("INSERT INTO audiobook_replacements VALUES('replacement','book','job','published','now')")
        group_lock=threading.RLock();progress_lock=threading.RLock();opened=[];proof_connections=[];fs_checks=[]
        class Tracked(sqlite3.Connection):
            def __enter__(self):opened.append(self);return self
            def __exit__(self,*args):
                try:return super().__exit__(*args)
                finally:opened.remove(self);self.close()
        def tracked(path,*args,**kwargs):
            db=sqlite3.connect(path,factory=Tracked);db.row_factory=sqlite3.Row;return db
        def no_database_io():
            self.assertEqual(opened,[]);self.assertFalse(group_lock._is_owned());self.assertTrue(progress_lock._is_owned());fs_checks.append(1)
        class CachePath:
            def __truediv__(self,part):return self
            def is_file(self):no_database_io();return True
        class Output:
            def stat(self):no_database_io();return SimpleNamespace(st_dev=1,st_ino=2,st_size=3,st_mtime_ns=4)
        class Replacements:
            def get(self,**kwargs):raise AssertionError('new relation read outside snapshot')
            def representative(self,*args):raise AssertionError('new relation read outside snapshot')
            def structural_guard(self,relation,*,db):
                self_outer.assertTrue(db.in_transaction);proof_connections.append(db);return True
        class Bindings:
            def lookup(self,db,record):proof_connections.append(db);return record,None
        self_outer=self;service=object.__new__(MergeService)
        service.inventory=SimpleNamespace(database=database,roots={'Audiobooks':'root'},group_lock=group_lock)
        service._progress_lock=progress_lock;service._approved_cache=None
        service.reviews=SimpleNamespace(cache=CachePath(),_output_root=lambda row:'output')
        service.replacements=Replacements();service.publication_bindings=Bindings();service._validated_outputs={'job':(1,2,3,4)}
        row={'id':'book','review':{},'members':[{'path':'input'}],'metadata':{}}
        job={'job_id':'job','manifest':{'candidate_id':'book','retry_intent':{'approved_manifest':{},'target_root':'root'}},'output':{'final_path':'output'}}
        def retry_guard(db,*args):proof_connections.append(db);return True
        with patch('catalog_contention.synchronize_groups'),patch('merge_service.connect',side_effect=tracked),patch('merge_service.groups.render',return_value=row),patch('merge_service.approved_scope',return_value=True),patch('merge_service.Path',return_value=Output()),patch('retry_intent.guard',side_effect=retry_guard),patch('merge_service.completed_book',return_value=True) as completed:
            result=service.progress_books([job],[],[],[])
        self.assertEqual(result['approved'],1);self.assertEqual(result['converted'],1)
        self.assertGreaterEqual(len(fs_checks),2);self.assertEqual(len({id(db) for db in proof_connections}),1)
        self.assertEqual(completed.call_args.kwargs['retry_binding'],True)
        self.assertEqual(completed.call_args.args[9]['id'],'replacement')
        self.assertEqual(opened,[])
