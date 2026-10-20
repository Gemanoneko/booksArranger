"""Actual private native copy/publication plus explicit crash/durability faults.

The delete-branch tests simulate directory-flush capability ONLY to exercise the
conditional native disposition protocol. They certify no installed filesystem's
power-loss durability. Other native handles/hash/copy/rename/delete are real.
"""
import contextlib
import copy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch

from catalog_owner import catalog_lock,ACTIVE_CATALOG
from native_io import DirectoryBoundary,FileInfo,VerifiedFile,kernel
import output_migration as migration
import publication_locations as locations

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'output-migration'


class SimulatedCrash(BaseException):pass


def native_id(path):
    handle=kernel.CreateFileW(str(path),0x80,7,None,3,0x00200000,None)
    if handle==ctypes.c_void_p(-1).value:raise RuntimeError('Private native fixture identity unavailable')
    try:
        info=FileInfo()
        if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)):raise RuntimeError('Private native fixture identity unavailable')
        return [int(info.volume),int(info.index_high),int(info.index_low)]
    finally:kernel.CloseHandle(handle)


class Harness:
    def __init__(self,seed,validation):
        self.directory=Path(tempfile.mkdtemp(prefix='case-',dir=AREA));self.oldroot=self.directory/'old-output';self.newroot=self.directory/'sorted';self.sourceroot=self.directory/'source';self.recoveryroot=self.directory/'recovery'
        for path in (self.oldroot,self.newroot,self.sourceroot,self.recoveryroot):path.mkdir()
        self.old=self.oldroot/'Verified book.m4b';self.old.write_bytes(seed);self.final=self.newroot/'Verified book.m4b'
        self.source=self.sourceroot/'original-input.mp3';self.source.write_bytes(b'Original source bytes never touched')
        self.recovery=self.recoveryroot/'recovery-copy';self.recovery.write_bytes(b'Existing recovery bytes never touched')
        self.database=self.directory/'inventory.sqlite3';self.db=sqlite3.connect(self.database)
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL');self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT,manifest_hash TEXT,journal TEXT,output TEXT,state TEXT)')
        self.db.execute('CREATE TABLE invalidations(publication_id TEXT,effective_path TEXT)')
        identity=str(uuid.uuid4());sha=hashlib.sha256(seed).hexdigest()
        with DirectoryBoundary(self.oldroot,self.old.parent) as boundary:
            ancestry=json.loads(migration.packed(boundary.identities))
        self.original={'job_id':identity,'root':str(self.oldroot),'final_path':str(self.old),'sha256':sha,'size':len(seed),'parent_identity':ancestry,
            'validation':dict(copy.deepcopy(validation),passed=True,profile='isolated-actual-aac-fixture',sha256=sha,size=len(seed))}
        manifest={'job_id':identity,'candidate_id':str(uuid.uuid4()),'candidate_revision':2,'root':str(self.sourceroot),
            'sources':[{'path':str(self.source)}],'metadata_facts':{'source_fingerprint':'private-source'}}
        self.job={'job_id':identity,'manifest':migration.packed(manifest),'manifest_hash':migration.digest(manifest),
            'journal':migration.packed({'publication_intent':self.original}),'output':migration.packed(self.original),'state':'completed'}
        self.db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?)',tuple(self.job[key] for key in ('job_id','manifest','manifest_hash','journal','output','state')))
        locations.initialize(self.db)
        self.planned=locations.plan(self.db,self.job,'base',self.original,str(self.newroot),str(self.final),{'routing_policy_version':'fixture-v1','source_fingerprint':'private-source'})
        self.pubid=self.planned['publication_id'];self.temporary=self.final.with_name('.'+self.pubid+'.'+self.planned['migration_id']+'.migration-partial')
        self.db.commit();self.held=False;self.closed=set();self.current_invocation=None;self.fault_at=None;self.triggered=False;self.allow_closure=False;self.bad_commit=False;self.bad_media=False;self.guards=[];self.directory_unavailable=False;self.sealed=False;self.bad_validation_digest=False

    def close(self):self.db.close()
    def current(self):return migration.row(self.db,'SELECT * FROM output_relocations WHERE publication_id=?',(self.pubid,))

    @contextlib.contextmanager
    def lease(self,pubid):
        invocation=str(uuid.uuid4());self.current_invocation=invocation
        try:
            with catalog_lock(self.database,{'Audiobooks':self.sourceroot}):
                self.held=True
                lock=Path(str(self.database)+'.lock')
                with DirectoryBoundary(lock.anchor,lock.parent) as boundary:
                    lockproof={'held':True,'lock_path':str(lock),'lock_identity':native_id(lock),'lock_ancestry':json.loads(migration.packed(boundary.identities))}
                owner={'schema':'books-migration-native-owner-v1','invocation_id':invocation,'catalog_identity':native_id(self.database),'owner_handle_proof':lockproof}
                yield {'db':self.db,'drained':True,'native_owner':owner,'generation_guard':self.guard,'durable_commit':self.commit,'removal_closure':self.removal_closure}
        finally:
            self.held=False;self.closed.add(invocation)

    def guard(self,pubid,generation):
        valid=self.held and self.db.in_transaction and ACTIVE_CATALOG.get()==str(self.database.absolute()) and self.current()['generation']==generation
        self.guards.append((generation,bool(self.db.in_transaction),valid));return valid

    def commit(self,db):
        db.commit();current=self.current();event=migration.row(db,'SELECT * FROM migration_events WHERE publication_id=? ORDER BY event_id DESC LIMIT 1',(self.pubid,))
        return {'schema':'books-migration-durable-commit-v1','publication_id':self.pubid,'generation':current['generation'],'relocation_sha256':migration.digest(current),
            'event_sha256':'f'*64 if self.bad_commit else migration.digest(event),'journal_mode':str(db.execute('PRAGMA journal_mode').fetchone()[0]).lower(),
            'synchronous':db.execute('PRAGMA synchronous').fetchone()[0],'committed':True,'owner_invocation_id':self.current_invocation}

    def invalidate(self,db,original,effective):
        if not db.in_transaction or not self.held:raise AssertionError('Invalidation escaped the location-commit transaction/lease')
        if original!=self.original:raise AssertionError('Original receipt was mutated')
        db.execute('INSERT INTO invalidations VALUES(?,?)',(self.pubid,effective['final_path']))

    def fault(self,point,state):
        if point==self.fault_at and not self.triggered:self.triggered=True;raise SimulatedCrash(point)

    def removal_closure(self,intent):
        if not self.allow_closure or intent.get('owner_invocation_id') not in self.closed:return None
        return {'schema':'books-migration-removal-closure-v1','removal_intent_sha256':migration.digest(intent),'native_owner_closed':True,'prior_owner_invocation_id':intent['owner_invocation_id'],'fixture_retained_owner_context_closed':True}

    def media(self,path,original,stop):
        if self.bad_media:return {'passed':True}
        if stop.is_set():raise InterruptedError('Stopped')
        raw=Path(path).read_bytes();sha=hashlib.sha256(raw).hexdigest()
        if self.sealed:
            if sha!=original['sha256'] or not original['validation'].get('complete_pcm_sha256') or original['validation'].get('codec')!='aac':raise ValueError('Actual sealed fixture validation does not match')
            return {'kind':'sealed_media_proof_reused','supported_validation_contract':'books-audio-output-v1','immutable_receipt_sha256':migration.digest(original),
                'validation_sha256':'f'*64 if self.bad_validation_digest else migration.digest(original['validation']),'passed':True,'full_content_sha256':sha,'size':len(raw),
                'details':{'sealed_actual_validation':copy.deepcopy(original['validation'])}}
        probe=subprocess.run([shutil.which('ffprobe'),'-v','error','-show_streams','-show_chapters','-of','json',str(path)],capture_output=True,timeout=20)
        if probe.returncode:raise ValueError('Private media probe failed')
        info=json.loads(probe.stdout);audio=[s for s in info['streams'] if s['codec_type']=='audio']
        if len(audio)!=1 or audio[0]['codec_name']!='aac':raise ValueError('Private fixture AAC profile changed')
        decoded=subprocess.run([shutil.which('ffmpeg'),'-v','error','-xerror','-nostdin','-i',str(path),'-map','0:a:0','-c:a','pcm_f64le','-f','f64le','pipe:1'],capture_output=True,timeout=20)
        if decoded.returncode or not decoded.stdout:raise ValueError('Private complete media decode failed')
        return {'kind':'fresh_full_media_verified','supported_validation_contract':'books-audio-output-v1','immutable_receipt_sha256':migration.digest(original),
            'validation_sha256':migration.digest(original['validation']),'passed':True,'full_content_sha256':sha,'size':len(raw),
            'details':{'codec':'aac','complete_pcm_sha256':hashlib.sha256(decoded.stdout).hexdigest(),'pcm_bytes':len(decoded.stdout),'chapters':info.get('chapters',[])}}

    def worker(self):
        worker=migration.MigrationWorker(self.database,operation_lease=self.lease,media_verify=self.media,invalidate=self.invalidate,fault=self.fault)
        if self.directory_unavailable:
            # Failure injection only; every successful flush uses the actual
            # initially retained write-capable native directory handle.
            worker._flush_parent=lambda boundary:{'schema':'books-directory-flush-v1','supported':False,'windows_error':5,'identity':list(boundary.identities[-1]),'same_retained_parent_handle':True,'failure_stage':'retained_capable_handle_flush','filesystem_support':'unproven','test_only_flush_failure':True}
        return worker

    def assert_sources(self,test):
        test.assertEqual(self.source.read_bytes(),b'Original source bytes never touched');test.assertEqual(self.recovery.read_bytes(),b'Existing recovery bytes never touched')


class OutputMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AREA.mkdir(parents=True,exist_ok=True);seed=AREA/'shared-tiny-aac.m4b'
        if not seed.exists():
            result=subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','anullsrc=r=22050:cl=mono','-t','0.1','-c:a','aac',str(seed)],capture_output=True,timeout=20)
            if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
        cls.seed=seed.read_bytes()
        probe=subprocess.run([shutil.which('ffprobe'),'-v','error','-show_streams','-show_chapters','-of','json',str(seed)],capture_output=True,timeout=20)
        decoded=subprocess.run([shutil.which('ffmpeg'),'-v','error','-xerror','-nostdin','-i',str(seed),'-map','0:a:0','-c:a','pcm_f64le','-f','f64le','pipe:1'],capture_output=True,timeout=20)
        if probe.returncode or decoded.returncode or not decoded.stdout:raise RuntimeError('Actual shared media validation fixture failed')
        info=json.loads(probe.stdout)
        cls.validation={'codec':'aac','complete_pcm_sha256':hashlib.sha256(decoded.stdout).hexdigest(),'pcm_bytes':len(decoded.stdout),'chapters':info.get('chapters',[])}

    def harness(self):
        value=Harness(self.seed,self.validation);self.addCleanup(value.close);return value

    def test_actual_native_copy_and_binding_retains_old_when_directory_durability_unavailable(self):
        h=self.harness();h.directory_unavailable=True;result=h.worker().run(h.pubid)
        self.assertEqual(result['stage'],'complete');self.assertTrue(result['verified']);self.assertEqual(h.final.read_bytes(),self.seed)
        self.assertEqual(h.db.execute('SELECT count(*) FROM invalidations').fetchone()[0],1);h.assert_sources(self)
        parent=json.loads(h.current()['destination_verification_json'])['filesystem_durability']['parent_directory']
        if parent['supported']:
            self.assertEqual(result['outcome'],'moved');self.assertFalse(h.old.exists())
        else:
            self.assertEqual(result['outcome'],'copied_verified_original_retained');self.assertEqual(h.old.read_bytes(),self.seed)
            self.assertEqual(parent['filesystem_support'],'unproven')
            self.assertIn(parent['failure_stage'],{'initial_capable_parent_unavailable','retained_capable_handle_flush'})
        self.assertTrue(all(item[1] and item[2] for item in h.guards))

    def test_conditional_native_delete_requires_exact_durable_intent_and_preserves_sources(self):
        h=self.harness();result=h.worker().run(h.pubid)
        self.assertEqual(result['outcome'],'moved');self.assertFalse(h.old.exists());self.assertEqual(h.final.read_bytes(),self.seed);h.assert_sources(self)
        stages=[r[0] for r in h.db.execute("SELECT to_stage FROM migration_events WHERE outcome='transition' ORDER BY event_id")]
        self.assertEqual(stages,list(locations.STAGES));self.assertTrue(h.current()['destination_verification_json'])

    def test_actual_same_retained_write_parent_flush_completes_native_delete_without_reopen(self):
        h=self.harness();worker=h.worker();actual=worker._flush_parent;observed=[]
        def flush(boundary):
            self.assertTrue(boundary.writable_parent);held=boundary.handles[-1];identity=list(boundary.identities[-1])
            with patch.object(migration.kernel,'CreateFileW',side_effect=AssertionError('No second directory open is permitted')):
                result=actual(boundary)
            self.assertEqual(boundary.handles[-1],held);boundary.revalidate()
            self.assertTrue(result['supported']);self.assertTrue(result['same_retained_parent_handle'])
            self.assertEqual(result['identity'],identity);self.assertEqual(result['filesystem_support'],'os_flush_succeeded')
            observed.append((held,identity));return result
        worker._flush_parent=flush;result=worker.run(h.pubid)
        self.assertEqual(result['outcome'],'moved');self.assertTrue(result['verified']);self.assertFalse(h.old.exists())
        self.assertGreaterEqual(len(observed),4);self.assertEqual(h.final.read_bytes(),self.seed);h.assert_sources(self)
        stored=json.loads(h.current()['destination_verification_json'])['filesystem_durability']['parent_directory']
        self.assertTrue(stored['supported']);self.assertTrue(stored['same_retained_parent_handle'])
        removed=h.db.execute("SELECT proof_json FROM migration_events WHERE to_stage='original_removed' AND outcome='transition'").fetchone()
        self.assertTrue(json.loads(removed[0])['native_owner_closed'])

    def test_readonly_parent_cannot_supply_flush_and_nested_read_lease_refuses_safely(self):
        h=self.harness();worker=h.worker()
        with DirectoryBoundary(h.newroot,h.final.parent) as readonly:
            with patch.object(migration.kernel,'FlushFileBuffers',side_effect=AssertionError('Readonly handles cannot certify flush')):
                proof=worker._flush_parent(readonly)
            self.assertFalse(proof['supported']);self.assertFalse(proof['same_retained_parent_handle'])
            self.assertEqual(proof['failure_stage'],'initial_capable_parent_unavailable')
            with self.assertRaises(migration.MigrationRefused) as error:worker.run(h.pubid)
        self.assertEqual(error.exception.code,'destination_parent_capability_unavailable')
        self.assertEqual(h.current()['stage'],'planned');self.assertFalse(h.final.exists());self.assertFalse(h.temporary.exists());self.assertEqual(h.old.read_bytes(),self.seed);h.assert_sources(self)

    def test_crash_after_each_durable_transition_resumes_without_premature_removal(self):
        for stage in locations.STAGES[1:]:
            with self.subTest(stage=stage):
                h=self.harness();h.fault_at='after_'+stage
                with self.assertRaises(SimulatedCrash):h.worker().run(h.pubid)
                self.assertEqual(h.current()['stage'],stage);h.assert_sources(self)
                if stage not in {'original_removed','complete'}:self.assertEqual(h.old.read_bytes(),self.seed)
                h.fault_at=None;result=h.worker().run(h.pubid)
                self.assertEqual(result['outcome'],'moved');self.assertEqual(h.final.read_bytes(),self.seed);h.assert_sources(self)

    def test_create_before_identity_journal_gap_is_never_adopted(self):
        h=self.harness();h.fault_at='created_before_journal'
        with self.assertRaises(SimulatedCrash):h.worker().run(h.pubid)
        self.assertTrue(h.temporary.exists());self.assertEqual(h.temporary.read_bytes(),b'');h.fault_at=None
        with self.assertRaises(migration.MigrationRefused) as error:h.worker().run(h.pubid)
        self.assertEqual(error.exception.code,'temporary_ownership_unproven');self.assertEqual(h.old.read_bytes(),self.seed);h.assert_sources(self)

    def test_created_identity_journal_allows_only_the_exact_owned_partial_to_resume(self):
        h=self.harness();h.fault_at='after_creation_journal'
        with self.assertRaises(SimulatedCrash):h.worker().run(h.pubid)
        h.fault_at=None;result=h.worker().run(h.pubid)
        self.assertTrue(result['verified']);self.assertEqual(h.final.read_bytes(),self.seed);h.assert_sources(self)

    def test_rename_before_final_receipt_gap_reconciles_exact_native_identity(self):
        h=self.harness();h.fault_at='after_native_publication'
        with self.assertRaises(SimulatedCrash):h.worker().run(h.pubid)
        self.assertEqual(h.current()['stage'],'final_publish_intent');self.assertTrue(h.final.exists());self.assertFalse(h.temporary.exists());self.assertTrue(h.old.exists())
        h.fault_at=None;self.assertTrue(h.worker().run(h.pubid)['verified']);h.assert_sources(self)

    def test_delete_gap_needs_exact_prior_native_owner_closure_not_path_absence(self):
        h=self.harness();h.fault_at='after_old_disposition'
        with self.assertRaises(SimulatedCrash):h.worker().run(h.pubid)
        self.assertEqual(h.current()['stage'],'old_removal_intent');self.assertFalse(h.old.exists());self.assertEqual(h.final.read_bytes(),self.seed)
        h.fault_at=None
        with self.assertRaises(migration.MigrationRefused) as error:h.worker().run(h.pubid)
        self.assertEqual(error.exception.code,'original_removal_closure_unproven')
        h.allow_closure=True;result=h.worker().run(h.pubid);self.assertEqual(result['outcome'],'moved');h.assert_sources(self)

    def test_same_name_replacement_after_delete_gap_is_preserved_and_refused(self):
        h=self.harness();h.fault_at='after_old_disposition'
        with self.assertRaises(SimulatedCrash):h.worker().run(h.pubid)
        h.old.write_bytes(self.seed);replacement_id=native_id(h.old);h.fault_at=None;h.allow_closure=True
        with self.assertRaises(migration.MigrationRefused):h.worker().run(h.pubid)
        self.assertEqual(native_id(h.old),replacement_id);self.assertEqual(h.old.read_bytes(),self.seed);h.assert_sources(self)

    def test_replaced_temp_even_identical_bytes_is_never_adopted(self):
        h=self.harness();h.fault_at='after_copied'
        with self.assertRaises(SimulatedCrash):h.worker().run(h.pubid)
        h.temporary.rename(h.temporary.with_suffix('.retained-evidence'));h.temporary.write_bytes(self.seed);h.fault_at=None
        with self.assertRaises(migration.MigrationRefused):h.worker().run(h.pubid)
        self.assertEqual(h.temporary.read_bytes(),self.seed);self.assertEqual(h.old.read_bytes(),self.seed);h.assert_sources(self)

    def test_committed_missing_destination_never_falls_back_or_removes_old(self):
        h=self.harness();h.fault_at='after_location_committed'
        with self.assertRaises(SimulatedCrash):h.worker().run(h.pubid)
        h.final.rename(h.final.with_suffix('.retained-evidence'));h.fault_at=None
        with self.assertRaises((migration.MigrationRefused,ValueError,OSError)):h.worker().run(h.pubid)
        self.assertEqual(h.old.read_bytes(),self.seed);self.assertEqual(h.current()['stage'],'location_committed');h.assert_sources(self)

    def test_bare_media_success_and_bad_commit_readback_never_remove_old(self):
        h=self.harness();h.bad_media=True
        with self.assertRaises(migration.MigrationRefused) as error:h.worker().run(h.pubid)
        self.assertEqual(error.exception.code,'media_verification_unproven');self.assertEqual(h.current()['stage'],'copied');self.assertEqual(h.old.read_bytes(),self.seed)
        other=self.harness();other.bad_commit=True
        with self.assertRaises(migration.MigrationRefused) as error:other.worker().run(other.pubid)
        self.assertEqual(error.exception.code,'catalog_not_durable');self.assertFalse(other.temporary.exists());self.assertEqual(other.old.read_bytes(),self.seed)

    def test_collision_stream_alias_and_weak_sqlite_policy_refuse(self):
        h=self.harness();h.final.write_bytes(b'unrelated destination')
        with self.assertRaises(migration.MigrationRefused):h.worker().run(h.pubid)
        self.assertEqual(h.final.read_bytes(),b'unrelated destination');self.assertEqual(h.old.read_bytes(),self.seed)
        stream=self.harness();Path(str(stream.old)+':Unresolved').write_bytes(b'Unknown stream')
        with self.assertRaises(ValueError):stream.worker().run(stream.pubid)
        self.assertEqual(Path(str(stream.old)+':Unresolved').read_bytes(),b'Unknown stream')
        weak=self.harness();weak.db.execute('PRAGMA synchronous=NORMAL')
        with self.assertRaises(migration.MigrationRefused) as error:weak.worker().run(weak.pubid)
        self.assertEqual(error.exception.code,'catalog_not_durable');self.assertEqual(weak.current()['stage'],'planned')

    def test_sealed_actual_media_reuse_binds_fresh_full_hashes_and_validation_digest(self):
        h=self.harness();h.sealed=True;result=h.worker().run(h.pubid);self.assertTrue(result['verified'])
        proof=json.loads(h.current()['destination_verification_json']);media=proof['media_validation']
        self.assertEqual(media['kind'],'sealed_media_proof_reused');self.assertEqual(media['source_full_hash']['sha256'],h.original['sha256']);self.assertEqual(media['destination_full_hash']['sha256'],h.original['sha256'])
        self.assertEqual(media['validation_sha256'],migration.digest(h.original['validation']));h.assert_sources(self)
        bad=self.harness();bad.sealed=True;bad.bad_validation_digest=True
        with self.assertRaises(migration.MigrationRefused) as error:bad.worker().run(bad.pubid)
        self.assertEqual(error.exception.code,'media_verification_unproven');self.assertEqual(bad.old.read_bytes(),self.seed)

    def test_location_commit_and_invalidation_are_one_rollback_unit(self):
        h=self.harness();worker=h.worker()
        def fail(db,original,effective):
            h.invalidate(db,original,effective);raise RuntimeError('Synthetic consumer invalidation failure')
        worker.invalidate=fail
        with self.assertRaisesRegex(RuntimeError,'invalidation failure'):worker.run(h.pubid)
        self.assertEqual(h.current()['stage'],'final_published');self.assertEqual(h.db.execute('SELECT count(*) FROM invalidations').fetchone()[0],0)
        self.assertEqual(h.old.read_bytes(),self.seed);self.assertEqual(h.final.read_bytes(),self.seed)
        self.assertTrue(h.worker().run(h.pubid)['verified']);h.assert_sources(self)

    def test_failed_write_retains_known_partial_and_original_for_resume(self):
        h=self.harness();worker=h.worker()
        with patch.object(worker,'_write_copy',side_effect=OSError('Synthetic disk full')):
            with self.assertRaisesRegex(OSError,'disk full'):worker.run(h.pubid)
        self.assertEqual(h.current()['stage'],'copy_intent');self.assertTrue(h.temporary.exists());self.assertEqual(h.old.read_bytes(),self.seed)
        self.assertTrue(h.worker().run(h.pubid)['verified']);h.assert_sources(self)

    def test_native_sharing_denial_retains_the_owned_original_after_verified_commit(self):
        h=self.harness()
        with VerifiedFile(h.old):result=h.worker().run(h.pubid)
        self.assertEqual(result['outcome'],'copied_verified_original_retained');self.assertEqual(h.old.read_bytes(),self.seed);self.assertEqual(h.final.read_bytes(),self.seed);h.assert_sources(self)

    def test_false_generation_guard_immediately_before_removal_never_disposes_old(self):
        h=self.harness();original=h.guard
        def guard(pubid,generation):return original(pubid,generation) and h.current()['stage']!='old_removal_intent'
        h.guard=guard
        with self.assertRaises(migration.MigrationRefused) as error:h.worker().run(h.pubid)
        self.assertEqual(error.exception.code,'relocation_generation_changed');self.assertEqual(h.current()['stage'],'old_removal_intent');self.assertEqual(h.old.read_bytes(),self.seed);h.assert_sources(self)

    def test_final_same_size_corruption_after_rename_never_binds_or_removes_old(self):
        h=self.harness();h.fault_at='after_native_publication'
        with self.assertRaises(SimulatedCrash):h.worker().run(h.pubid)
        damaged=bytearray(self.seed);damaged[-1]^=1;h.final.write_bytes(damaged);h.fault_at=None
        with self.assertRaises(migration.MigrationRefused) as error:h.worker().run(h.pubid)
        self.assertEqual(error.exception.code,'output_content_changed');self.assertEqual(h.current()['stage'],'final_publish_intent');self.assertEqual(h.old.read_bytes(),self.seed);h.assert_sources(self)

    def test_hardlink_original_and_unknown_temporary_stream_are_preserved(self):
        h=self.harness();os.link(h.old,h.old.with_name('Unrelated alias.m4b'))
        with self.assertRaises(migration.MigrationRefused):h.worker().run(h.pubid)
        self.assertEqual(h.current()['stage'],'planned');self.assertEqual(h.old.read_bytes(),self.seed)
        temp=self.harness();temp.fault_at='after_copied'
        with self.assertRaises(SimulatedCrash):temp.worker().run(temp.pubid)
        marker=Path(str(temp.temporary)+':Unresolved');marker.write_bytes(b'Unique named stream');temp.fault_at=None
        with self.assertRaises(ValueError):temp.worker().run(temp.pubid)
        self.assertEqual(marker.read_bytes(),b'Unique named stream');self.assertEqual(temp.old.read_bytes(),self.seed)


if __name__=='__main__':unittest.main()
