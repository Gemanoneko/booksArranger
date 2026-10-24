"""0.21.1 Iron Inferno (legacy MP3 decode failure retried with the tag repair) and Сказка (Confirm and convert: the
no-restart proof and the verified removal of the interrupted attempt's own files). Fixture catalogs only: no origin
statement is ever recorded in a real catalog, and no real boot, library or Z: path is used."""
import contextlib,json,os,shutil,sqlite3,subprocess,time,unittest,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import Mock,patch
import test_producer_recovery as core
import test_retry_intent as intent
from producer_recovery import ProducerRecovery,CLAIM,BOOT_MARGIN_MS,verify_retained,protected_dependency,packed

NOW=int(time.time()*1000);T0=NOW-3*86400000  # the old attempt ran three days ago
def iso(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()
def now():return int(time.time()*1000)
def boot(started,wall=None):
    """A synthetic Windows reading whose startup is `started` (ms); wall is the clock now (default: the real one)."""
    def reading():
        clock=now() if wall is None else wall;return {'schema':'books-windows-boot-v1','wall_ms':clock,'uptime_ms':clock-started}
    return reading

class BootProofAndDisposal(unittest.TestCase):
    connection=core.RecoveryTests.connection;snapshot=core.RecoveryTests.snapshot
    def setUp(self):
        core.RecoveryTests.setUp(self)
        self.second=self.file.parent/'checked.m4b';self.second.write_bytes(b'old working output')
        with self.connection() as db:
            db.execute('INSERT INTO working_files VALUES(?,?,?,?,?,?,?,?,?,?)',(self.job,self.attempt,self.second.name,str(self.second),'generated','creation_intended','',0,'{}','before'))
            db.execute('UPDATE working_attempts SET updated=?',(iso(T0),));db.execute('UPDATE working_files SET updated=?',(iso(T0+60000),))
            db.execute('UPDATE audio_jobs SET journal=?',(json.dumps({'history':[{'stage':'checking sources','at':iso(T0)}]}),))
        for path in (self.file,self.second):os.utime(path,ns=((T0+300000)*1000000,)*2)
        self.recovery.boot=boot(NOW-86400000)  # a later startup: yesterday
    def origin(self):return self.recovery.record_origin(self.job,{'actor':'user','claim':CLAIM,'evidence':'Synthetic fixture statement; never a production attestation'})
    def child(self,checkpoint,state='completed',passed=True,disposal=True,relation=True,bound=None):
        child=str(uuid.uuid4());binding={'parent_job_id':self.job,'retained_checkpoint_id':bound or checkpoint,**({'retained_disposal':True} if disposal else {})}
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS audio_retry_intents(parent_job_id TEXT PRIMARY KEY,child_job_id TEXT UNIQUE NOT NULL,binding TEXT NOT NULL,created TEXT NOT NULL)')
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?)',(child,state,json.dumps({'job_id':child,'validation':{'passed':passed}}),'{}',None,'',json.dumps({'retry_intent':binding})))
            if relation:db.execute('INSERT OR REPLACE INTO audio_retry_intents VALUES(?,?,?,?)',(self.job,child,json.dumps(binding,sort_keys=True),'now'))
        return child
    def isolated(self):
        self.origin();self.assertEqual(self.recovery.status(self.job)['basis'],'boot_after_attempt');return self.recovery.isolate(self.job)['checkpoint_id']
    def state(self):
        with self.connection() as db:return [row[0] for row in db.execute('SELECT state FROM producer_recovery_checkpoints')]

    def test_origin_is_the_sole_blocker_offers_confirmation_with_the_deletion_size(self):
        status=self.recovery.status(self.job)
        self.assertEqual((status['state'],status['cause'],status['can_confirm_origin']),('unsupported','origin_unproved',True))
        self.assertEqual(status['disposal'],{'bytes':self.file.stat().st_size+self.second.stat().st_size,'originals':1})
        (self.file.parent/'unknown').write_bytes(b'kept');self.assertFalse(self.recovery.status(self.job)['can_confirm_origin'])
        self.recovery.boot=None;(self.file.parent/'unknown').unlink();self.assertFalse(self.recovery.status(self.job)['can_confirm_origin'])

    def test_later_boot_isolates_with_a_recomputed_bound_proof(self):
        before=self.snapshot();checkpoint=self.isolated();self.assertEqual(before[2:],self.snapshot()[2:])
        with self.connection() as db:
            db.row_factory=sqlite3.Row;record=verify_retained(db,self.job,self.attempt);proof=record['proof']
            self.assertEqual((proof['basis'],proof['started_ms'],proof['margin_ms']),('boot_after_attempt',NOW-86400000,BOOT_MARGIN_MS))
            self.assertEqual(proof['last_activity_ms'],T0+300000);self.assertTrue(protected_dependency(db,[self.source]))
        self.assertIs(self.recovery.retained(self.candidate)['attempts'][0]['removed_after_verification'],True)
        with self.connection() as db:
            db.row_factory=sqlite3.Row
            for key,value in (('started_ms',proof['started_ms']+1),('last_activity_ms',T0),('basis',None),('boot',dict(proof['boot'],uptime_ms=10**12))):
                db.execute('UPDATE producer_recovery_checkpoints SET proof=?',(packed(dict(proof,**{key:value})),))
                with self.subTest(tampered=key),self.assertRaises(ValueError):verify_retained(db,self.job,self.attempt)
        self.assertEqual(self.recovery.status(self.job)['state'],'unsupported')

    def test_no_restart_unreadable_or_inconsistent_times_refuse_and_keep_everything(self):
        cases=[('same boot',boot(T0-86400000),'waiting_restart','restart_unproven'),('inside the margin',boot(T0+300000+BOOT_MARGIN_MS-1),'waiting_restart','restart_unproven'),
               ('clock behind the attempt',boot(T0-86400000,wall=T0),'unsupported','startup_unavailable'),('malformed reading',lambda:{'schema':'books-windows-boot-v1','wall_ms':NOW,'uptime_ms':-1},'unsupported','startup_unavailable'),
               ('unavailable reading',Mock(side_effect=OSError('no counter')),'unsupported','startup_unavailable')]
        self.origin();before=self.snapshot()
        for name,provider,state,cause in cases:
            with self.subTest(name):
                self.recovery.boot=provider;status=self.recovery.status(self.job)
                self.assertEqual((status['state'],status['cause'],status['can_retry']),(state,cause,False))
                with self.assertRaises(ValueError):self.recovery.isolate(self.job)
                self.assertEqual(self.snapshot(),before);self.assertEqual(self.state(),[])
    def test_a_file_written_after_the_startup_is_no_proof(self):
        os.utime(self.second,ns=((NOW-3600000)*1000000,)*2);self.origin()  # the producer may still be running
        self.assertEqual(self.recovery.status(self.job)['cause'],'restart_unproven')
        with self.assertRaises(ValueError):self.recovery.isolate(self.job)
    def test_recovery_child_keeps_the_copy_flow(self):
        import inplace_m4b
        base={'profile':inplace_m4b.AUTOMATIC_PROFILE,'sources':[{'path':'Z:/a.m4b'}],'cleanup_policy':{'enabled':True}}
        self.assertTrue(inplace_m4b.offered(base));self.assertFalse(inplace_m4b.offered(dict(base,retry_intent={'retained_checkpoint_id':'checkpoint'})))
    def test_unreadable_attempt_time_is_unavailable(self):
        with self.connection() as db:db.execute('UPDATE working_attempts SET updated=?',('2026-10-19 09:45',))
        self.origin();self.assertEqual(self.recovery.status(self.job)['cause'],'startup_unavailable')

    def test_verified_child_removes_exactly_the_fenced_files(self):
        checkpoint=self.isolated();child=self.child(checkpoint);outside=self.base/'outside.bin';outside.write_bytes(b'not ours')
        marker=self.file.parent.parent/'ownership.json';kept=(self.source.read_bytes(),outside.read_bytes(),marker.read_bytes())
        self.assertEqual(self.recovery.dispose(self.job,child,[self.base/'Audiobooks']),{'removed':2,'bytes':len(b'unknown snapshot retained')+len(b'old working output')})
        self.assertFalse(self.file.exists() or self.second.exists());self.assertEqual((self.source.read_bytes(),outside.read_bytes(),marker.read_bytes()),kept)
        self.assertEqual(self.state(),['disposed']);self.assertEqual(self.recovery.dispose(self.job,child),{'removed':0,'bytes':0})
        with self.connection() as db:
            db.row_factory=sqlite3.Row;self.assertFalse(protected_dependency(db,[self.source]))
            self.assertEqual(verify_retained(db,self.job,self.attempt,('disposed',))['checkpoint_id'],checkpoint)
            with self.assertRaises(ValueError):verify_retained(db,self.job,self.attempt)

    def test_every_refusal_keeps_every_file(self):
        # The relation keys on the parent, so each case gets its own freshly bound verified child.
        checkpoint=self.isolated();good=lambda:self.child(checkpoint)
        unverified,outside='not verified','outside the private staging'
        refusals={'child not completed':(lambda:self.child(checkpoint,state='needs attention'),(),unverified),'output not verified':(lambda:self.child(checkpoint,passed=False),(),unverified),
            'no saved relation':(lambda:self.child(checkpoint,relation=False),(),unverified),'no removal consent':(lambda:self.child(checkpoint,disposal=False),(),unverified),
            'another checkpoint':(lambda:self.child(checkpoint,bound=str(uuid.uuid4())),(),unverified),'stage inside a library':(good,[self.stage],outside),
            'library inside the stage':(good,[self.file.parent/'x'],outside),'library holds the stage':(good,[self.base],outside)}
        for name,(make,roots,reason) in refusals.items():
            with self.subTest(name):
                with self.assertRaisesRegex(ValueError,reason):self.recovery.dispose(self.job,make(),roots)
                self.assertTrue(self.file.exists() and self.second.exists());self.assertEqual(self.state(),['isolated_retained'])
        for name,damage,undo,reason in (('unknown file',lambda:(self.file.parent/'new.txt').write_bytes(b'x'),lambda:(self.file.parent/'new.txt').unlink(),'unknown file'),
                                 ('changed bytes',lambda:self.second.write_bytes(b'old working outpuX'),None,'changed since'),('missing file',lambda:self.second.unlink(),None,'is missing')):
            with self.subTest(name):
                damage()
                with self.assertRaisesRegex(ValueError,reason):self.recovery.dispose(self.job,good())
                self.assertTrue(self.file.exists());self.assertEqual(self.state(),['isolated_retained'])
                if undo:undo()
    def test_replaced_identity_is_not_removed(self):
        checkpoint=self.isolated();good=self.child(checkpoint);data=self.second.read_bytes();self.second.unlink();self.second.write_bytes(data)
        with self.assertRaisesRegex(ValueError,'changed'):self.recovery.dispose(self.job,good)
        self.assertTrue(self.second.exists() and self.file.exists())
    def test_checkpoint_basis_never_removes(self):
        self.recovery.boot=None;self.origin();self.recovery.prepare(self.job);self.uptime=5000;checkpoint=self.recovery.isolate(self.job)['checkpoint_id']
        with self.assertRaisesRegex(ValueError,'not verified'):self.recovery.dispose(self.job,self.child(checkpoint))
        self.assertTrue(self.file.exists());self.assertNotIn('removed_after_verification',self.recovery.retained(self.candidate)['attempts'][0])
    def test_interrupted_removal_resumes_from_its_durable_intent(self):
        checkpoint=self.isolated();good=self.child(checkpoint);real=ProducerRecovery.dispose
        from native_io import VerifiedFile
        calls=[0];original=VerifiedFile.dispose
        def crash(handle):
            calls[0]+=1
            if calls[0]==2:raise OSError('simulated power loss')
            return original(handle)
        with patch.object(VerifiedFile,'dispose',crash),self.assertRaises(OSError):real(self.recovery,self.job,good)
        self.assertEqual(self.state(),['disposing']);self.assertEqual(sum(path.exists() for path in (self.file,self.second)),1)
        self.assertEqual(self.recovery.dispose(self.job,good)['removed'],2);self.assertFalse(self.file.exists() or self.second.exists());self.assertEqual(self.state(),['disposed'])


class IronInferno(unittest.TestCase):
    setUp=intent.RetryIntent.setUp;tearDown=intent.RetryIntent.tearDown;wait=intent.RetryIntent.wait;activate=intent.RetryIntent.activate
    def failed(self):
        from scanner import connect
        r=self.service.reviews;row=r.page()['rows'][0];row=r.covers('Audiobooks',row['id'],row['revision'])
        row=r.save('Audiobooks',row['id'],row['revision'],self.review,True,'Fixture bibliography establishes identity and author role',cover_id=row['cover_choices'][0]['id'])
        row=r.tracks('Audiobooks',row['id'],row['revision'],row['track_order'],row['included'][:1],True,True,True,evidence_note='One fixture MP3 is the whole book')
        manifest=r.build_manifest('Audiobooks',row['id'],row['revision']);manifest.pop('output_root');job=self.service.jobs.enqueue(manifest)
        failure={'exception_class':'ValidationError','at':time.time(),'retryable':False,'stage':'checking sources'}
        self.service.jobs._update(job,state='needs attention',journal=json.dumps({'history':[],'failure':failure}),reason='Full audio decode failed: [mp3float] Header missing')
        return row,self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job,))[0]
    def readmission(self,job):
        import m4b_readmission
        with self.service.jobs._db() as db:return m4b_readmission.describe(db,job)

    def test_classifier_marker_and_summary(self):
        from audio_jobs import tag_repair_retry,_failure_details
        from audio_pipeline import ValidationError,_source_duration
        row,parent=self.failed();self.assertTrue(tag_repair_retry(parent))
        item=self.service.attention_summary([parent['job_id']])[parent['job_id']]
        self.assertEqual((item['group'],item['remedy']['kind'],item['retry']),('retry','tag_repair',{'allowed':True,'reason':''}))
        for changed in ({'output':'{}'},{'manifest':json.dumps(dict(json.loads(parent['manifest']),retry_intent={}))},{'journal':json.dumps({'failure':dict(json.loads(parent['journal'])['failure'],tag_repair_checked=True)})}):
            self.assertFalse(tag_repair_retry(dict(parent,**changed)))
        error=ValidationError('Full audio decode failed: x')
        with patch('audio_pipeline.decoded_duration',side_effect=error),patch('audio_pipeline.m4b_repair.silence_approved',return_value=False),self.assertRaises(ValidationError):_source_duration({},{'path':'a.mp3','sha256':'0'},Path('a.mp3'),Path('.'),None,1.0)
        self.assertTrue(_failure_details(error,'checking sources')['tag_repair_checked']);self.assertNotIn('tag_repair_checked',_failure_details(ValidationError('x'),'checking sources'))
        # The same failure recorded by this version (the repair was weighed): no second retry, the replacement copy stays.
        self.service.jobs._update(parent['job_id'],journal=json.dumps({'history':[],'failure':dict(json.loads(parent['journal'])['failure'],tag_repair_checked=True)}))
        item=self.service.attention_summary([parent['job_id']])[parent['job_id']]
        self.assertEqual((item['group'],item['remedy']['kind'],'retry' in item),('other','replace_source',False))
        with patch.object(self.service,'_resume_later'),self.assertRaises(ValueError):self.service.retry_blocked_job('Audiobooks',row['id'],row['revision'],parent['job_id'])
        self.assertIsNone(self.readmission(parent['job_id']))

    def test_press_admits_a_separate_child_through_the_retry_route(self):
        row,parent=self.failed();self.activate(self.base/'Sorted')
        with patch.object(self.service,'_resume_later'):answer=self.service.retry_blocked_job('Audiobooks',row['id'],row['revision'],parent['job_id'])
        self.assertTrue(answer['queued_next']);self.assertNotIn('origin',self.readmission(parent['job_id']))
        self.service.jobs.resume();status=self.wait();child=[job for job in status['jobs'] if job['job_id']!=parent['job_id']]
        self.assertEqual([job['state'] for job in child],['completed'],status);self.assertEqual(child[0]['manifest']['retry_intent']['parent_job_id'],parent['job_id'])
        self.assertTrue(child[0]['manifest']['cleanup_policy']['enabled']);self.assertEqual(self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],))[0],parent)
        self.assertNotIn(parent['job_id'],self.service.attention_summary())

    def repaired_retry(self,**patches):
        # Iron's ID3v1 title holds CP1251 "яя" (0xFF 0xFF), a false frame sync that fails the strict decode. This tag does the
        # same with a generic title. Until the ledger and cleanup admitted tag-repair-<hex>.mp3/.json, the repair was refused.
        import mp3_tag_repair
        ff=shutil.which('ffmpeg');source=self.sources[0];tag=b'TAG'+'Синяя книга'.encode('cp1251').ljust(30,b'\0')+b'\0'*60+b'2021'+b'\0'*30+b'\xff'
        subprocess.run([ff,'-v','error','-y','-nostdin','-f','lavfi','-i','sine=frequency=440:duration=0.3','-ar','44100','-ac','1','-c:a','libmp3lame','-b:a','128k','-write_xing','0','-id3v2_version','0','-write_id3v1','0',str(source)],check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        source.write_bytes(source.read_bytes()+tag)
        strict=subprocess.run([ff,'-hide_banner','-v','error','-xerror','-nostdin','-f','mp3','-i',str(source),'-map','0:a:0','-c:a','pcm_s16le','-f','s16le','pipe:1'],capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertNotEqual(strict.returncode,0);self.assertEqual(mp3_tag_repair.plan(source.read_bytes()).receipt()['removed_bytes'],128)  # it needs the repair
        self.inv.launch('Audiobooks');self.inv.worker.join(30)
        row,parent=self.failed()
        with patch.object(self.service,'_resume_later'):self.assertTrue(self.service.retry_blocked_job('Audiobooks',row['id'],row['revision'],parent['job_id'])['queued_next'])
        with contextlib.ExitStack() as held:
            for name,value in patches.items():held.enter_context(patch.object(self.service,name,value))
            self.service.jobs.resume();status=self.wait()
        child=next(job for job in status['jobs'] if job['job_id']!=parent['job_id']);self.assertEqual(child['state'],'completed',status)
        self.assertEqual([(p['removed_bytes'],p['decision'],p['affected_audio_seconds']) for p in child['output']['validation']['source_working_repairs']],[(128,'repairable',0)])
        return child,source

    def test_a_needed_tag_repair_converts_and_every_working_file_is_cleaned(self):
        child,source=self.repaired_retry()
        with self.service.jobs._db() as db:
            attempt=db.execute('SELECT state FROM working_attempts WHERE job_id=?',(child['job_id'],)).fetchone()[0]
            ledger={r[0]:r[1] for r in db.execute('SELECT name,state FROM working_files WHERE job_id=?',(child['job_id'],))}
        self.assertEqual(attempt,'retired');self.assertEqual(sorted(n.rsplit('.',1)[1] for n in ledger if n.startswith('tag-repair-')),['json','mp3'])
        self.assertTrue(all(state in ('removed','absent_after_intent') for state in ledger.values()),ledger)
        self.assertEqual([p.name for p in (self.service.stage_root/child['job_id']).rglob('*') if p.is_file()],['ownership.json'])
        self.assertFalse(source.exists());self.assertEqual(self.service.cleanup.status(child['job_id'])['state'],'completed')  # normal source cleanup

    def test_staging_cleanup_alone_also_removes_the_repair_files(self):
        # The fallback when the published working-file pass did not run (interrupted): StorageCleanup.run's staging check.
        child,source=self.repaired_retry(_prune_working=lambda job_id:None)
        storage=next(r for r in self.service.storage_cleanup.status() if r['job_id']==child['job_id'])
        self.assertEqual(storage['state'],'completed',storage)
        self.assertEqual([p.name for p in (self.service.stage_root/child['job_id']).rglob('tag-repair-*')],[])

    def test_automatic_pass_requests_once_and_bulk_accepts(self):
        import m4b_readmission
        row,parent=self.failed();job=parent['job_id']
        self.assertEqual(self.service.retry_automatic_job(job,time.time(),resume=False),{'retryable':False,'requeued':False,'accepted':True})
        self.assertEqual(self.readmission(job)['origin'],'automatic')
        with self.service.jobs._db() as db:m4b_readmission.record_waiting(db,'Scan still running');db.commit()
        self.assertEqual((self.readmission(job)['origin'],self.readmission(job)['waiting_reason']),('automatic','Scan still running'))
        self.assertEqual(self.service.retry_automatic_job(job,time.time(),resume=False)['accepted'],False)
        with self.service.jobs._db() as db:db.execute("UPDATE m4b_readmissions SET state='refused'");db.commit()
        self.assertEqual(self.service.retry_automatic_job(job,time.time(),resume=False)['accepted'],False)  # never repeated after a refusal
        with self.service.jobs._db() as db:db.execute('DELETE FROM m4b_readmissions');db.commit()
        self.assertEqual(self.service._retry_one(job,'retry',{'id':row['id'],'revision':row['revision'],'job_id':job,'kind':'retry'}),'next')


class SkazkaConfirmAndConvert(unittest.TestCase):
    setUp=intent.RetryIntent.setUp;tearDown=intent.RetryIntent.tearDown;wait=intent.RetryIntent.wait;activate=intent.RetryIntent.activate;parent=intent.RetryIntent.parent;ready=intent.RetryIntent.ready
    def interrupted(self):
        from source_cleanup import packed as pack
        row,parent=self.parent();job=parent['job_id'];attempt=str(uuid.uuid4());manifest=json.loads(parent['manifest'])
        self.service.jobs._update(job,state='running',attempt_id=attempt);self.service.working.begin(dict(manifest,attempt_id=attempt))
        old=self.service.stage_root/job/attempt;old.mkdir(parents=True);(old.parent/'ownership.json').write_text(pack({'job_id':job,'manifest':manifest}),encoding='utf8')
        self.old=old/'source00000.mp3';self.service.working.planned(old,self.old);self.old.write_bytes(self.sources[0].read_bytes())
        self.service.jobs._update(job,state='needs attention',reason='Working cleanup requires attention: A prior producer is not durably closed')
        self.activate(self.base/'sorted-recovery');recovery=self.service.producer_recovery
        recovery.platform=lambda:{'schema':'books-windows-startup-v1','machine_guid':'private-fixture','computer':'private','windows_directory':'C:/Windows','system_volume_serial':'fixture','uptime_ms':5000}
        recovery.boot=boot(now()+3600000,wall=now()+7200000)  # a startup an hour after this fixture's attempt
        return row,self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job,))[0]
    def confirm(self,row,parent,statements=None):
        from merge_service import MergeService
        with patch.object(self.service,'_resume_later'):return self.service.confirm_origin_and_convert('Audiobooks',row['id'],row['revision'],parent['job_id'],statements or list(MergeService.ORIGIN_STATEMENTS))
    def facts(self,job):
        with self.service.jobs._db() as db:return db.execute('SELECT count(*) FROM producer_origin_facts WHERE job_id=?',(job,)).fetchone()[0]

    def test_confirm_and_convert_then_verified_removal_and_normal_cleanup(self):
        from audio_pipeline import digest
        row,parent=self.interrupted();job=parent['job_id'];self.assertTrue(self.service.producer_recovery.status(job)['can_confirm_origin'])
        answer=self.confirm(row,parent);self.assertEqual((answer['origin_recorded'],answer['queued_next'],answer['producer_recovery']['basis']),(True,True,'boot_after_attempt'))
        with self.service.jobs._db() as db:fact=json.loads(db.execute('SELECT record FROM producer_origin_facts WHERE job_id=?',(job,)).fetchone()[0])['evidence']
        self.assertEqual((fact['actor'],fact['claim'],fact['statements']),('user',CLAIM,list(self.service.ORIGIN_STATEMENTS)))
        self.service.jobs.resume();status=self.wait()
        child=next(item for item in status['jobs'] if item['job_id']!=job);self.assertEqual(child['state'],'completed',status)
        self.assertEqual(self.service.progress_books()['converted'],1);self.service.close()
        self.assertTrue(child['manifest']['retry_intent']['retained_disposal']);self.assertTrue(child['manifest']['cleanup_policy']['enabled'])
        self.assertFalse(self.old.exists());self.assertTrue((self.old.parent.parent/'ownership.json').exists())
        with self.service.jobs._db() as db:self.assertEqual(db.execute('SELECT state FROM producer_recovery_checkpoints').fetchone()[0],'disposed')
        cleanup=self.service.cleanup.status(child['job_id']);self.assertEqual(cleanup['state'],'completed',cleanup);self.assertEqual(cleanup['removed'],len(self.sources))
        self.assertTrue(all(not path.exists() for path in self.sources));self.assertIn(cleanup['recovery']['state'],{'retained','deleted'})  # the normal recovery-copy path
        self.assertEqual(child['manifest']['cleanup_policy'],json.loads(parent['manifest'])['cleanup_policy'])

    def test_refused_removal_keeps_the_old_files_and_the_original(self):
        row,parent=self.interrupted();self.confirm(row,parent)
        with patch.object(ProducerRecovery,'dispose',side_effect=ValueError('simulated changed old file')):self.service.jobs.resume();status=self.wait()
        child=next(item for item in status['jobs'] if item['job_id']!=parent['job_id']);self.assertEqual(child['state'],'completed',status)
        cleanup=self.service.cleanup.status(child['job_id']);self.assertEqual(cleanup['state'],'needs_attention');self.assertIn('original is kept',cleanup['reason'])
        self.assertTrue(self.old.exists() and all(path.exists() for path in self.sources))
        with self.service.jobs._db() as db:self.assertEqual(db.execute('SELECT state FROM producer_recovery_checkpoints').fetchone()[0],'isolated_retained')

    def test_refusals_change_nothing_and_a_failed_proof_keeps_the_statement(self):
        from audio_jobs import RetryRefused
        row,parent=self.interrupted();job=parent['job_id']
        with self.assertRaises(ValueError):self.confirm(row,parent,['The interrupted conversion ran on this PC.','Something else.'])
        with self.assertRaisesRegex(RetryRefused,'changed') as caught:self.confirm(dict(row,revision=row['revision']+1),parent)
        self.assertEqual(caught.exception.cause,'book_changed')
        (self.old.parent/'extra.log').write_bytes(b'kept')
        with self.assertRaisesRegex(RetryRefused,'changed'):self.confirm(row,parent)
        (self.old.parent/'extra.log').unlink()
        self.service.inventory.worker=Mock(is_alive=Mock(return_value=True))
        with self.assertRaisesRegex(RetryRefused,'Convert when it stops'):self.confirm(row,parent)
        self.service.inventory.worker=None
        with self.assertRaises(RetryRefused) as caught:self.service.retry_blocked_job('Audiobooks',row['id'],row['revision'],job)
        self.assertEqual(caught.exception.cause,'origin_unconfirmed');self.assertEqual(self.facts(job),0)
        self.service.producer_recovery.boot=boot(now()-86400000)  # no startup since the attempt
        answer=self.confirm(row,parent);self.assertEqual((answer['accepted'],answer['origin_recorded'],answer['producer_recovery']['cause']),(False,True,'restart_unproven'))
        self.assertIsNone(intent_status(self.service,job));self.assertTrue(self.old.exists());self.assertEqual(self.facts(job),1)
        self.service.producer_recovery.boot=boot(now()+3600000,wall=now()+7200000)  # K3: after the restart the kept statement suffices
        status=self.service.attention_summary([job])[job];self.assertEqual((status['group'],status['retry']['allowed'],status['producer_recovery']['basis']),('retry',True,'boot_after_attempt'))
        with patch.object(self.service,'_resume_later'):self.assertTrue(self.service.retry_blocked_job('Audiobooks',row['id'],row['revision'],job)['queued_next'])

def intent_status(service,job):
    import m4b_readmission
    with service.jobs._db() as db:return m4b_readmission.describe(db,job)


# 0.21.3: this module's fixtures publish inside their own library; see sorted_fixture (Sergei's deletion rule).
def setUpModule():
    global _sorted_fixture
    from sorted_fixture import patch_merge_service
    _sorted_fixture = patch_merge_service()


def tearDownModule():
    _sorted_fixture.stop()

if __name__=='__main__':unittest.main()
