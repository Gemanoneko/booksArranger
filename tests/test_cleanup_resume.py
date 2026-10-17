"""v0.16.5: a source cleanup stranded by a busy catalog pauses, resumes and finishes.

Actual Windows handle fixtures on private files under scratch/; no real library, catalog or media tools.
"""
import contextlib,hashlib,json,sqlite3,sys,tempfile,threading,time,unittest,uuid
from datetime import datetime,timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import source_cleanup
from audio_jobs import AudioJobs
from merge_service import MergeService
from native_io import BoundaryError,DirectoryBoundary,VerifiedFile
from recovery_retention import RecoveryRetention
from scanner import connect
from source_cleanup import CleanupJobs,catalog_busy,packed
from storage_cleanup import StorageCleanup

AREA=Path(__file__).resolve().parents[1]/'scratch'/'cleanup-resume-tests';AREA.mkdir(parents=True,exist_ok=True)
LOCKED='database is locked'
STREAM_HELD='Additional filesystem streams require review; original retained'
RESTORED='Originals restored; recovery copies retained. Cleanup is not automatically repeated.'


def typed(code=sqlite3.SQLITE_BUSY,name='SQLITE_BUSY'):
    """An OperationalError carrying SQLite's typed code, as the sqlite3 module raises it."""
    error=sqlite3.OperationalError(LOCKED);error.sqlite_errorcode=code;error.sqlite_errorname=name;return error


class Book:
    """Three reviewed originals, a verified output and a completed audio job with original removal enabled."""
    def __init__(self,folder,count=3):
        self.base=Path(folder);self.library=self.base/'library';self.library.mkdir()
        self.db=self.base/'inventory.sqlite3';self.job_id=str(uuid.uuid4());candidate=str(uuid.uuid4())
        self.sources=[]
        for i in range(count):
            p=self.library/f'{i}.mp3';p.write_bytes(bytes([65+i])*4096);st=p.stat()
            self.sources.append({'path':str(p),'size':st.st_size,'modified':str(st.st_mtime_ns),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                                 'fingerprint':{'size':st.st_size,'modified':str(st.st_mtime_ns)}})
        final=self.library/'book.m4b';final.write_bytes(b'validated fixture output');sha=hashlib.sha256(final.read_bytes()).hexdigest()
        with DirectoryBoundary(self.library,final.parent) as boundary:identity=boundary.identities
        self.manifest={'job_id':self.job_id,'candidate_id':candidate,'candidate_revision':1,'root':str(self.library),'sources':self.sources,'destination':str(final),
            'profile':'fixture','metadata':{'title':'Fixture','canonical_author':'Author'},'chapters':[],'evidence':[],'cover':{'path':str(final),'sha256':sha},
            'cleanup_policy':{'enabled':True}}
        validation={'passed':True,'checks':'Output checks passed','profile':'fixture','sha256':sha,'size':final.stat().st_size,'tags':{'media_type':'2','title':'Fixture','artist':'Author'},
            'source_pcm_frames':[100]*count,'source_pcm_rate':100,'decoded_duration':count,'duration_tolerance':.01,'chapters':[]}
        self.output={'job_id':self.job_id,'final_path':str(final),'owned_temp':str(self.library/'absent.partial'),'size':final.stat().st_size,'sha256':sha,'parent_identity':identity,'validation':validation}
        self.queue=AudioJobs(self.db,None,None,lambda r:True);self.queue.enqueue(self.manifest)
        with connect(self.db) as db:db.execute('CREATE TABLE IF NOT EXISTS owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER)')
        self.stage_root=self.base/'merge-cache/audio-staging';self.stage_root.mkdir(parents=True)
        self.job=self.stage_root/self.job_id;self.job.mkdir();(self.job/'ownership.json').write_text(packed({'job_id':self.job_id,'manifest':self.manifest}),encoding='utf-8')
        self.stage=self.job/str(uuid.uuid4());self.stage.mkdir()
        for i,s in enumerate(self.sources):(self.stage/f'source{i:05d}.mp3').write_bytes(Path(s['path']).read_bytes())
        (self.stage/'checked.m4b').write_bytes(final.read_bytes());(self.stage/'inputs.txt').write_text('owned input plan')
        self.output['validation']['staging_artifacts']={'attempt_id':self.stage.name,'files':{p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in self.stage.iterdir()}}
        self.queue._update(self.job_id,state='completed',stage='completed',output=json.dumps(self.output))
        self.recovery_root=self.base/'source-recovery'
        self.cleanup=self.cleanup_jobs()
        self.storage=StorageCleanup(self.db,self.stage_root,self.cleanup.root)
        self.full={'job_id':self.job_id,'state':'completed','manifest':self.manifest,'output':self.output}
        # A real enrollment carries a non-empty review binding and the recovery-root identity.
        self.binding={'revision':1,'review':self.manifest['metadata'],'context':{}}
        self.extra=[]

    def cleanup_jobs(self):
        jobs=CleanupJobs(self.db,self.recovery_root,lambda db,intent:True,contextlib.nullcontext)
        if hasattr(self,'extra'):self.extra.append(jobs)
        return jobs

    def close(self):
        for jobs in [self.cleanup,*self.extra]:
            try:jobs.close()
            except Exception:pass
        self.queue.close()

    def enroll(self):
        self.cleanup_id=self.cleanup.enroll(self.full,self.binding);return self.cleanup_id

    def strand(self):
        """The 2026-10-15 shape: track 0 removed, track 1 disposed but not retired, track 2 copied; untyped 'database is locked'."""
        self.enroll();original=CleanupJobs._retire;second=self.sources[1]['path']
        def retire(jobs,intent,source,member,db=None):
            if source['path']==second:raise sqlite3.OperationalError(LOCKED)
            return original(jobs,intent,source,member,db)
        with patch.object(CleanupJobs,'_retire',retire):
            try:self.cleanup.run(self.cleanup_id)
            except sqlite3.OperationalError:pass
            else:raise AssertionError('Fixture cleanup did not stop at the second retirement')
        # The pre-v0.16.5 failure handler wrote the bare message as the reason.
        self.cleanup._set(self.cleanup_id,'needs_attention',LOCKED)
        return self.cleanup_id

    def row(self):
        with connect(self.db) as db:return dict(db.execute('SELECT * FROM source_cleanup WHERE id=?',(self.cleanup_id,)).fetchone())

    def members(self):
        with connect(self.db) as db:return [dict(r) for r in db.execute('SELECT * FROM cleanup_members WHERE cleanup_id=? ORDER BY path',(self.cleanup_id,))]

    def holds(self):
        with connect(self.db) as db:return [dict(r) for r in db.execute('SELECT * FROM source_cleanup_holds WHERE cleanup_id=? ORDER BY at',(self.cleanup_id,))]

    def sql(self,statement,params=()):
        with connect(self.db) as db:db.execute(statement,params)

    def backup(self,index):
        return self.cleanup.root/self.cleanup_id/f'{index:05d}.mp3'


class Counting:
    """Counts native opens, hashes and dispositions without changing them."""
    def __init__(self):
        self.opened=[];self.hashed=[];self.disposed=[]
        enter,sha,dispose=VerifiedFile.__enter__,VerifiedFile.sha256,VerifiedFile.dispose
        counter=self
        def counted_enter(handle):counter.opened.append(str(handle.path));return enter(handle)
        def counted_sha(handle):counter.hashed.append(str(handle.path));return sha(handle)
        def counted_dispose(handle):counter.disposed.append(str(handle.path));return dispose(handle)
        self.patches=[patch.object(VerifiedFile,'__enter__',counted_enter),patch.object(VerifiedFile,'sha256',counted_sha),patch.object(VerifiedFile,'dispose',counted_dispose)]
    def __enter__(self):
        for item in self.patches:item.start()
        return self
    def __exit__(self,*_):
        for item in self.patches:item.stop()


class Base(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.books=[]
    def tearDown(self):
        for book in self.books:book.close()
        self.temp.cleanup()
    def book(self,**options):
        folder=Path(self.temp.name)/str(len(self.books));folder.mkdir()
        book=Book(folder,**options);self.books.append(book);return book


class LegacyReclassificationTests(Base):
    def test_stranded_locked_cleanup_becomes_paused_at_startup_without_files_or_threads(self):
        b=self.book();b.strand()
        self.assertEqual([m['state'] for m in b.members()],['removed','disposition_set','backup_verified'])
        self.assertFalse(Path(b.sources[0]['path']).exists());self.assertFalse(Path(b.sources[1]['path']).exists());self.assertTrue(Path(b.sources[2]['path']).exists())
        threads=set(threading.enumerate())
        with Counting() as counts:fresh=b.cleanup_jobs()
        self.assertEqual(counts.opened,[],'startup reclassification must not open any file')
        self.assertEqual(counts.hashed,[]);self.assertEqual(counts.disposed,[])
        self.assertIsNone(fresh.thread);self.assertEqual(set(threading.enumerate())-threads,set())
        row=b.row();self.assertEqual((row['state'],row['reason']),('paused',''))
        holds=b.holds();self.assertEqual(len(holds),1)
        self.assertEqual((holds[0]['prior_state'],holds[0]['prior_reason']),('needs_attention',LOCKED))
        self.assertEqual(fresh.status(b.job_id)['status'],'Source cleanup paused: 1 of 3 removed')
        b.cleanup_jobs();self.assertEqual(len(b.holds()),1,'a later startup does not add another record')
        self.assertEqual(b.row()['state'],'paused')

    def test_only_the_exact_legacy_shape_is_reclassified(self):
        b=self.book();b.strand();before=b.row();intent=json.loads(before['intent'])
        no_binding=dict(intent,binding={});no_binding.pop('recovery_identity')
        variants={
            'stream-held reason':(lambda:b.sql('UPDATE source_cleanup SET reason=? WHERE id=?',(STREAM_HELD,b.cleanup_id)),),
            'restored reason':(lambda:b.sql('UPDATE source_cleanup SET reason=? WHERE id=?',(RESTORED,b.cleanup_id)),),
            'different case':(lambda:b.sql('UPDATE source_cleanup SET reason=? WHERE id=?',('Database is locked',b.cleanup_id)),),
            'trailing period':(lambda:b.sql('UPDATE source_cleanup SET reason=? WHERE id=?',(LOCKED+'.',b.cleanup_id)),),
            'trailing text':(lambda:b.sql('UPDATE source_cleanup SET reason=? WHERE id=?',(LOCKED+': retry',b.cleanup_id)),),
            'enrollment attention':(lambda:b.sql('UPDATE source_cleanup SET intent=? WHERE id=?',(packed(no_binding),b.cleanup_id)),),
            'other intent identity':(lambda:b.sql('UPDATE source_cleanup SET intent=? WHERE id=?',(packed(dict(intent,id=str(uuid.uuid4()))),b.cleanup_id)),),
            'restored member':(lambda:b.sql("UPDATE cleanup_members SET state='restored' WHERE cleanup_id=? AND path=?",(b.cleanup_id,b.sources[0]['path'])),),
            'restore intended':(lambda:b.sql("UPDATE cleanup_members SET state='restore_intended' WHERE cleanup_id=? AND path=?",(b.cleanup_id,b.sources[0]['path'])),),
            'restore intent recorded':(lambda:b.sql("UPDATE cleanup_members SET restore_intent=? WHERE cleanup_id=? AND path=?",('{"destination":"x"}',b.cleanup_id,b.sources[2]['path'])),),
            'audio not completed':(lambda:b.queue._update(b.job_id,state='needs attention'),),
        }
        members=b.members();job=b.queue._rows('SELECT * FROM audio_jobs WHERE job_id=?',(b.job_id,))[0]
        for name,(change,) in variants.items():
            with self.subTest(variant=name):
                change();shaped=b.row()
                b.cleanup_jobs()
                after=b.row();self.assertEqual(after,shaped,'the row must be left exactly as it was');self.assertEqual(after['state'],'needs_attention')
                self.assertEqual(b.holds(),[])
                # Restore the stranded shape for the next variant.
                b.sql('UPDATE source_cleanup SET state=?,reason=?,intent=?,updated=? WHERE id=?',(before['state'],before['reason'],before['intent'],before['updated'],b.cleanup_id))
                for m in members:b.sql('UPDATE cleanup_members SET state=?,restore_intent=? WHERE cleanup_id=? AND path=?',(m['state'],m['restore_intent'],b.cleanup_id,m['path']))
                b.queue._update(b.job_id,state=job['state'])
        b.cleanup_jobs();self.assertEqual(b.row()['state'],'paused','positive control: the restored legacy shape is reclassified')

    def test_catalog_without_audio_jobs_table_is_left_alone(self):
        folder=Path(self.temp.name)/'bare';folder.mkdir();db=folder/'inventory.sqlite3'
        with connect(db) as conn:
            source_cleanup.setup(conn)
            conn.execute('INSERT INTO source_cleanup VALUES(?,?,?,?,?,?,?)',('c','j',packed({'id':'c','binding':{'revision':1},'recovery_identity':[[1,2]]}),'needs_attention',LOCKED,'',''))
        jobs=CleanupJobs(db,folder/'recovery',lambda db,intent:True,contextlib.nullcontext);self.addCleanup(jobs.close)
        with connect(db) as conn:self.assertEqual(tuple(conn.execute('SELECT state,reason FROM source_cleanup').fetchone()),('needs_attention',LOCKED))


class ResumeTests(Base):
    def resumed(self,b):
        b.strand();b.cleanup.close();b.cleanup=b.cleanup_jobs();self.assertEqual(b.row()['state'],'paused');return b

    def test_resume_finishes_idempotently_and_starts_the_24_hour_clock_at_resume(self):
        b=self.resumed(self.book());completions=[]
        b.cleanup.on_completed=completions.append
        time.sleep(.01);start=datetime.now().astimezone()
        with Counting() as counts:b.cleanup._work(follow_audio=False)
        self.assertEqual(b.row()['state'],'completed');self.assertEqual(completions,[b.job_id])
        self.assertEqual(counts.disposed,[b.sources[2]['path']],'only the copied, not yet removed original is disposed')
        backups={str(b.backup(i)) for i in range(3)}
        self.assertEqual(backups-set(counts.hashed),set(),'every recovery copy is re-hashed')
        self.assertIn(b.sources[2]['path'],counts.hashed);self.assertIn(b.output['final_path'],counts.hashed)
        self.assertEqual([m['state'] for m in b.members()],['removed']*3)
        with connect(b.db) as db:
            retired=sorted(r[0] for r in db.execute("SELECT path FROM source_retirements WHERE cleanup_id=? AND state='removed'",(b.cleanup_id,)))
            completed=db.execute('SELECT completed_at FROM recovery_completion WHERE cleanup_id=?',(b.cleanup_id,)).fetchone()[0]
        self.assertEqual(retired,sorted(s['path'] for s in b.sources))
        self.assertGreaterEqual(datetime.fromisoformat(completed),start)
        retention=RecoveryRetention(b.storage);status=retention.status(b.job_id)
        self.assertEqual(status['state'],'retained')
        self.assertEqual(datetime.fromisoformat(status['expires_at']),datetime.fromisoformat(completed)+timedelta(hours=24))
        self.assertTrue(all(b.backup(i).is_file() for i in range(3)))

    def test_changed_recovery_copy_refuses_before_any_removal(self):
        b=self.resumed(self.book())
        raw=b.backup(0).read_bytes();b.backup(0).write_bytes(bytes([90])*len(raw))
        with Counting() as counts:b.cleanup._work(follow_audio=False)
        row=b.row();self.assertEqual(row['state'],'needs_attention');self.assertIn('Recovery bytes changed',row['reason'])
        self.assertEqual(counts.disposed,[]);self.assertTrue(Path(b.sources[2]['path']).is_file())
        self.assertEqual(b.holds()[1:],[],'a verification refusal is not a busy hold')

    def test_changed_remaining_original_refuses_and_is_kept(self):
        b=self.resumed(self.book());path=Path(b.sources[2]['path']);raw=path.read_bytes()
        path.write_bytes(raw[:-1]+b'Z')
        with Counting() as counts:b.cleanup._work(follow_audio=False)
        row=b.row();self.assertEqual(row['state'],'needs_attention')
        self.assertEqual(counts.disposed,[]);self.assertEqual(path.read_bytes(),raw[:-1]+b'Z')

    def test_unknown_outcome_guard_is_unchanged(self):
        b=self.resumed(self.book())
        b.sql("UPDATE cleanup_members SET state='removal_intended' WHERE cleanup_id=? AND path=?",(b.cleanup_id,b.sources[1]['path']))
        b.cleanup._work(follow_audio=False)
        row=b.row();self.assertEqual(row['state'],'needs_attention');self.assertIn('unknown outcome',row['reason'])
        self.assertTrue(Path(b.sources[2]['path']).is_file());self.assertTrue(b.backup(1).is_file())


class TypedBusyTests(Base):
    CODES=((sqlite3.SQLITE_BUSY,'SQLITE_BUSY'),(sqlite3.SQLITE_LOCKED,'SQLITE_LOCKED'),(517,'SQLITE_BUSY_SNAPSHOT'),(262,'SQLITE_LOCKED_SHAREDCACHE'))

    def test_typed_classification_never_reads_the_message(self):
        for code,name in self.CODES:self.assertTrue(catalog_busy(typed(code,name)),name)
        for error in (sqlite3.OperationalError(LOCKED),sqlite3.OperationalError('other'),RuntimeError(LOCKED),typed(sqlite3.SQLITE_ERROR,'SQLITE_ERROR'),typed(-5,'negative')):
            self.assertFalse(catalog_busy(error),repr(error))
        error=sqlite3.OperationalError(LOCKED);error.sqlite_errorcode='5';self.assertFalse(catalog_busy(error))

    def test_busy_retirement_pauses_with_one_record_per_attempt(self):
        for code,name in self.CODES:
            with self.subTest(code=name):
                b=self.book();b.enroll();original=CleanupJobs._retire;target=b.sources[1]['path']
                def retire(jobs,intent,source,member,db=None):
                    if source['path']==target:raise typed(code,name)
                    return original(jobs,intent,source,member,db)
                with patch.object(CleanupJobs,'_retire',retire),patch.object(CleanupJobs,'_retry_wait',return_value=False) as waits:
                    b.cleanup._work(follow_audio=False)
                row=b.row();self.assertEqual((row['state'],row['reason']),('paused',''))
                self.assertEqual([c.args[0] for c in waits.call_args_list],[5,15])
                holds=b.holds();self.assertEqual(len(holds),3);self.assertTrue(all(name in h['cause'] for h in holds),holds)
                self.assertTrue(Path(b.sources[2]['path']).is_file(),'the original after the failed retirement is kept')

    def test_busy_final_completion_write_pauses_then_resume_completes(self):
        b=self.book();b.enroll();original=CleanupJobs._set
        def failing(jobs,id,state,reason=''):
            if state=='completed':raise typed()
            return original(jobs,id,state,reason)
        with patch.object(CleanupJobs,'_set',failing),patch.object(CleanupJobs,'_retry_wait',return_value=False):
            b.cleanup._work(follow_audio=False)
        self.assertEqual(b.row()['state'],'paused');self.assertEqual([m['state'] for m in b.members()],['removed']*3)
        with connect(b.db) as db:self.assertIsNone(db.execute('SELECT 1 FROM recovery_completion WHERE cleanup_id=?',(b.cleanup_id,)).fetchone())
        with Counting() as counts:b.cleanup._work(follow_audio=False)
        self.assertEqual(b.row()['state'],'completed');self.assertEqual(counts.disposed,[])

    def test_untyped_locked_message_still_needs_attention_and_is_not_retried(self):
        b=self.book();b.enroll();calls=[]
        def run(jobs,id):calls.append(id);raise sqlite3.OperationalError(LOCKED)
        with patch.object(CleanupJobs,'run',run),patch.object(CleanupJobs,'_retry_wait',return_value=False) as waits:
            b.cleanup._work(follow_audio=False)
        row=b.row();self.assertEqual((row['state'],row['reason']),('needs_attention',LOCKED))
        self.assertEqual(len(calls),1);waits.assert_not_called();self.assertEqual(b.holds(),[])

    def test_busy_while_recording_the_hold_is_retried_not_raised(self):
        b=self.book();b.enroll()
        holder=sqlite3.connect(b.db,check_same_thread=False);holder.execute('BEGIN IMMEDIATE')
        probe=sqlite3.connect(b.db,timeout=0)
        try:
            with self.assertRaises(sqlite3.OperationalError) as caught:probe.execute("UPDATE source_cleanup SET reason='x'")
            self.assertTrue(catalog_busy(caught.exception),'positive control: the catalog really is write-locked')
        finally:probe.close()
        release=threading.Timer(.5,lambda:(holder.rollback(),holder.close()));release.start();started=time.monotonic()
        try:state=b.cleanup.hold(b.cleanup_id,typed())
        finally:release.join()
        self.assertEqual(state,'paused');self.assertGreaterEqual(time.monotonic()-started,.4)
        self.assertEqual(b.row()['state'],'paused');self.assertEqual(len(b.holds()),1)


class ShortRetryTests(Base):
    def test_one_busy_retirement_then_success_completes_with_each_original_disposed_once(self):
        b=self.book();b.enroll();original=CleanupJobs._retire;target=b.sources[1]['path'];failed=[]
        def retire(jobs,intent,source,member,db=None):
            if source['path']==target and not failed:failed.append(1);raise typed()
            return original(jobs,intent,source,member,db)
        states=[];hold=CleanupJobs.hold
        def watched(jobs,*args,**kwargs):states.append(args);return hold(jobs,*args,**kwargs)
        with Counting() as counts,patch.object(CleanupJobs,'_retire',retire),patch.object(CleanupJobs,'_retry_wait',return_value=False) as waits,patch.object(CleanupJobs,'hold',watched):
            b.cleanup._work(follow_audio=False)
        self.assertEqual(b.row()['state'],'completed');self.assertEqual(states,[],'the cleanup never needed attention or paused')
        self.assertEqual(sorted(counts.disposed),sorted(s['path'] for s in b.sources),'each original disposed exactly once')
        self.assertEqual([c.args[0] for c in waits.call_args_list],[5])
        holds=b.holds();self.assertEqual(len(holds),1);self.assertIn('attempt 1',holds[0]['cause'])

    def scripted(self,b,outcomes):
        calls=[]
        def run(jobs,id):
            calls.append(id);outcome=outcomes[len(calls)-1]
            if outcome is not None:raise outcome
        return calls,patch.object(CleanupJobs,'run',run)

    def test_three_busy_attempts_pause_with_three_records(self):
        b=self.book();b.enroll();calls,patched=self.scripted(b,[typed(),typed(),typed()])
        with patched,patch.object(CleanupJobs,'_retry_wait',return_value=False) as waits:b.cleanup.run_with_retry(b.cleanup_id)
        self.assertEqual(len(calls),3);self.assertEqual([c.args[0] for c in waits.call_args_list],[5,15])
        self.assertEqual(b.row()['state'],'paused');holds=b.holds();self.assertEqual(len(holds),3)
        self.assertEqual([('attempt 1' in h['cause'],'attempt 2' in h['cause'],'attempt 3' in h['cause']) for h in holds],[(True,False,False),(False,True,False),(False,False,True)])

    def test_pause_during_the_wait_returns_at_once_and_pauses(self):
        b=self.book();b.enroll();calls,patched=self.scripted(b,[typed(),None])
        timer=threading.Timer(.2,b.cleanup.stop.set);timer.start();started=time.monotonic()
        with patched:b.cleanup.run_with_retry(b.cleanup_id)
        timer.join();elapsed=time.monotonic()-started
        self.assertLess(elapsed,1.0,'the 5 s wait was cut short');self.assertEqual(len(calls),1)
        self.assertEqual(b.row()['state'],'paused');self.assertEqual(len(b.holds()),1,'one record for the one busy failure')

    def test_pause_before_the_record_still_leaves_one_record(self):
        b=self.book();b.enroll();calls,patched=self.scripted(b,[typed(),None]);b.cleanup.stop.set();started=time.monotonic()
        with patched:b.cleanup.run_with_retry(b.cleanup_id)
        self.assertLess(time.monotonic()-started,1.0);self.assertEqual(len(calls),1)
        self.assertEqual(b.row()['state'],'paused');holds=b.holds();self.assertEqual(len(holds),1);self.assertIn('attempt 1',holds[0]['cause'])

    def test_quit_during_the_wait_returns_at_once_and_pauses(self):
        b=self.book();b.enroll();calls,patched=self.scripted(b,[typed(),None]);quitting=threading.Event()
        b.cleanup.interrupt=quitting.is_set
        timer=threading.Timer(.2,quitting.set);timer.start();started=time.monotonic()
        with patched:b.cleanup.run_with_retry(b.cleanup_id)
        timer.join();self.assertLess(time.monotonic()-started,1.0);self.assertEqual(len(calls),1)
        self.assertEqual(b.row()['state'],'paused');self.assertFalse(b.cleanup.stop.is_set())

    def test_wait_runs_its_full_length_when_nothing_interrupts(self):
        b=self.book();started=time.monotonic()
        self.assertFalse(b.cleanup._retry_wait(.3));self.assertGreaterEqual(time.monotonic()-started,.29)
        b.cleanup.stop.set();started=time.monotonic()
        self.assertTrue(b.cleanup._retry_wait(5));self.assertLess(time.monotonic()-started,.5)

    def test_non_busy_error_on_the_second_attempt_needs_attention_without_a_third(self):
        b=self.book();b.enroll();calls,patched=self.scripted(b,[typed(),BoundaryError('Recovery bytes changed'),None])
        with patched,patch.object(CleanupJobs,'_retry_wait',return_value=False):b.cleanup.run_with_retry(b.cleanup_id)
        self.assertEqual(len(calls),2);row=b.row();self.assertEqual((row['state'],row['reason']),('needs_attention','Recovery bytes changed'))

    def test_message_only_locked_error_is_not_retried(self):
        b=self.book();b.enroll();calls,patched=self.scripted(b,[sqlite3.OperationalError(LOCKED),None])
        with patched,patch.object(CleanupJobs,'_retry_wait',return_value=False) as waits:b.cleanup.run_with_retry(b.cleanup_id)
        self.assertEqual(len(calls),1);waits.assert_not_called();self.assertEqual(b.row()['state'],'needs_attention')


class InlineAndStartTests(Base):
    def service(self,b):
        s=MergeService.__new__(MergeService)
        s.jobs=b.queue;s.cleanup=b.cleanup;s._post_current=None;s.operation_lock=threading.RLock()
        s.inventory=SimpleNamespace(worker=None);s.storage_cleanup=b.storage;s.recovery=RecoveryRetention(b.storage)
        s.working=SimpleNamespace(discharge_published=Mock(),schedule_published=Mock());s._prune_working=Mock()
        s.enroll_cleanup=lambda job_id:{'cleanup_id':b.enroll()}
        s.progress_books=lambda *args:{'approved':0,'converted':0,'converted_ids':set()}
        b.cleanup.on_completed=lambda job_id:s._prune_completed(job_id,source_completed=True)
        b.cleanup.interrupt=lambda:s.draining or s.jobs._drain.is_set()
        return s

    def test_inline_busy_pauses_then_resume_finishes_and_retires_working_copies(self):
        b=self.book();s=self.service(b);original=CleanupJobs._retire;target=b.sources[1]['path']
        def retire(jobs,intent,source,member,db=None):
            if source['path']==target:raise typed()
            return original(jobs,intent,source,member,db)
        with patch.object(CleanupJobs,'_retire',retire),patch.object(CleanupJobs,'_retry_wait',return_value=False) as waits:s._after_completed(b.job_id)
        self.assertEqual(b.queue._rows('SELECT state FROM audio_jobs WHERE job_id=?',(b.job_id,))[0]['state'],'completed')
        self.assertEqual(b.row()['state'],'paused');self.assertIsNone(b.cleanup.current)
        self.assertEqual([c.args[0] for c in waits.call_args_list],[5,15],'the inline cleanup retries before pausing')
        self.assertEqual(len(b.holds()),3);self.assertIn('attempt 3',b.holds()[-1]['cause'])
        state=s.state();self.assertEqual(state['state'],'Paused');self.assertGreaterEqual(state['queued'],1,'a paused cleanup counts as queued, so Start resumes it')
        order=[]
        b.cleanup.after_drain=lambda:order.append(('converter',b.row()['state']))
        s.state=lambda:{}
        s.resume();b.cleanup.thread.join(30);self.assertFalse(b.cleanup.thread.is_alive())
        self.assertEqual(order,[('converter','completed')],'the cleanup finishes before the converter is resumed')
        self.assertEqual(b.row()['state'],'completed')
        self.assertEqual(list(b.stage.iterdir()),[],'staging snapshots and generated files are retired')
        self.assertTrue((b.job/'ownership.json').is_file())
        self.assertTrue(all(b.backup(i).is_file() for i in range(3)),'24 h recovery copies are kept')
        with connect(b.db) as db:self.assertEqual(db.execute('SELECT state FROM storage_cleanup_jobs WHERE job_id=?',(b.job_id,)).fetchone()[0],'completed')

    def test_merge_service_wires_pause_and_quit_into_the_retry_wait(self):
        from scanner import Inventory
        base=Path(self.temp.name)/'service';base.mkdir()
        roots={'Audiobooks':str(base/'audio'),'Podcasts':str(base/'podcasts'),'Ebooks':str(base/'ebooks')}
        for root in roots.values():Path(root).mkdir()
        service=MergeService(Inventory(base/'catalog.sqlite3',roots,lambda path,kind,stop:{}),base/'cache')
        try:
            self.assertIs(service.cleanup.stop,service.jobs._stop,'Pause and Stop reach the cleanup wait')
            self.assertFalse(service.cleanup.interrupt())
            service.drain();self.assertTrue(service.cleanup.interrupt(),'Quit reaches the cleanup wait')
        finally:service.close()

    def test_quit_drain_cuts_the_inline_retry_wait_short(self):
        b=self.book();s=self.service(b);s.jobs._drain.set();calls=[]
        def run(jobs,id):calls.append(id);raise typed()
        started=time.monotonic()
        with patch.object(CleanupJobs,'run',run):s._after_completed(b.job_id)
        self.assertLess(time.monotonic()-started,1.0);self.assertEqual(len(calls),1)
        self.assertEqual(b.row()['state'],'paused')


if __name__=='__main__':unittest.main()
