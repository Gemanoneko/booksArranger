"""Actual private Windows snapshot disposition, not media/codec proof."""
from sorted_fixture import library_is_sorted  # 0.21.3: fixtures publish inside their library
import contextlib
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from types import SimpleNamespace
from merge_service import MergeService
from audio_jobs import AudioJobs
from audio_pipeline import generated_artifacts,copy_owned,plan_generated
from encoding_policy import AUTOMATIC_PROFILE
from native_io import BoundaryError,DirectoryBoundary,VerifiedFile
from recovery_retention import RecoveryRetention
from scanner import connect
from source_cleanup import CleanupJobs,packed
from storage_cleanup import StorageCleanup
from working_lifecycle import WorkingLifecycle

@unittest.skipUnless(os.name=='nt','Actual Windows native fixtures required')
class PublishedSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='books-working-')
        self.base=Path(self.temp.name)
        self.library=self.base/'library';self.library.mkdir()
        self.stage_root=self.base/'cache/audio-staging';self.stage_root.mkdir(parents=True)
        self.source=self.library/'source.mp3';self.source.write_bytes(b'protected source bytes'*128)
        self.cover=self.library/'cover.jpg';self.cover.write_bytes(b'\xff\xd8\xffprivate cover')
        info=self.source.stat()
        source={'path':str(self.source),'size':info.st_size,'modified':str(info.st_mtime_ns),
                'sha256':hashlib.sha256(self.source.read_bytes()).hexdigest(),
                'fingerprint':{'size':info.st_size,'modified':str(info.st_mtime_ns)}}
        self.job_id=str(uuid.uuid4())
        self.manifest={'job_id':self.job_id,'candidate_id':str(uuid.uuid4()),'candidate_revision':1,
                       'root':str(self.library),'sources':[source],'cover':{'path':str(self.cover),'sha256':hashlib.sha256(self.cover.read_bytes()).hexdigest()},
                       'metadata':{'title':'Private fixture','canonical_author':'Fixture'},'destination':str(self.library/'final.m4b'),
                       'profile':'fixture','chapters':[],'evidence':[]}
        self.db=self.base/'inventory.sqlite3'
        self.queue=AudioJobs(self.db,None,lambda manifest:True,lambda output:True)
        self.queue.enqueue(self.manifest)
        self.life=WorkingLifecycle(self.db,self.stage_root)
        self.queue.before_attempt=self.life.admit
        self.queue.after_attempt=self.life.terminal
        self.original=self.source.read_bytes()

    def tearDown(self):
        if hasattr(self,'cleanup'):self.cleanup.close()
        self.queue.close();self.temp.cleanup()

    def stage(self,extras=()):
        attempt=str(uuid.uuid4())
        journal={'attempt_id':attempt,'history':[],'failure':{'retryable':True,'at':0}}
        self.queue._update(self.job_id,state='running',attempt_id=attempt,journal=json.dumps(journal))
        manifest=dict(self.manifest,attempt_id=attempt)
        self.life.begin(manifest)
        parent=self.stage_root/self.job_id
        parent.mkdir(exist_ok=True)
        marker=parent/'ownership.json'
        if not marker.exists():marker.write_text(packed({'job_id':self.job_id,'manifest':self.manifest}),encoding='utf8')
        directory=parent/attempt;directory.mkdir()
        with generated_artifacts(directory,self.life) as receipts:
            for index,item in enumerate(self.manifest['sources']):  # one source unless a case adds more (more_sources)
                copy_owned(item['path'],directory/('source%05d.mp3'%index),item['sha256'],threading.Event())
            copy_owned(self.cover,directory/'cover.jpg',self.manifest['cover']['sha256'],threading.Event())
            for name,raw in [('checked.m4b',b'failed generated output'),('compatible.m4b',b'failed rewritten output')]+list(extras):
                plan_generated(directory/name);(directory/name).write_bytes(raw)
        self.queue._update(self.job_id,state='needs attention',reason='Private deliberate fixture failure')
        return attempt,directory,dict(receipts)

    def published(self, enrolled=False):
        self.manifest['profile']=AUTOMATIC_PROFILE
        if enrolled:self.manifest['cleanup_policy']={'enabled':True}
        encoded=packed(self.manifest)
        self.queue._update(self.job_id,manifest=encoded,manifest_hash=hashlib.sha256(encoded.encode()).hexdigest())
        attempt,stage,receipts=self.stage()
        final=Path(self.manifest['destination']);final.write_bytes(b'private validated output fixture')
        sha=hashlib.sha256(final.read_bytes()).hexdigest();size=final.stat().st_size
        with DirectoryBoundary(self.library,self.library) as boundary:parent_identity=boundary.identities
        validation={'passed':True,'checks':'Output checks passed','profile':AUTOMATIC_PROFILE,'sha256':sha,'size':size,
                    'tags':{'media_type':'2','title':self.manifest['metadata']['title'],'artist':self.manifest['metadata']['canonical_author']},
                    'source_pcm_frames':[100]*len(self.manifest['sources']),'source_pcm_rate':100,'decoded_duration':len(self.manifest['sources']),'duration_tolerance':.01,'chapters':[],
                    'staging_artifacts':{'attempt_id':attempt,'files':receipts}}
        output={'job_id':self.job_id,'final_path':str(final),'owned_temp':str(self.library/'absent.partial'),
                'sha256':sha,'size':size,'parent_identity':parent_identity,'validation':validation}
        self.queue._update(self.job_id,state='completed',output=json.dumps(output),journal=json.dumps({'publication_intent':output}))
        self.life.terminal(self.job_id,attempt)
        self.cleanup=CleanupJobs(self.db,self.base/'recovery',lambda *args:True,contextlib.nullcontext,output_policy=library_is_sorted(self.library))
        self.storage=StorageCleanup(self.db,self.stage_root,self.cleanup.root)
        with connect(self.db) as db:
            db.execute('CREATE TABLE IF NOT EXISTS owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER)')
            db.execute('CREATE TABLE IF NOT EXISTS files(root TEXT,path TEXT,missing INTEGER,error TEXT)')
        if enrolled:
            row=self.queue._rows('SELECT * FROM audio_jobs')[0]
            job=dict(row,manifest=self.manifest,output=output)
            self.cleanup_id=self.cleanup.enroll(job,{})
        self.storage.working_files(self.job_id)
        return attempt,stage,output

    def more_sources(self,count):
        """count more source files in the book, before published(): one snapshot each."""
        for index in range(1,count+1):
            path=self.library/('source%d.mp3'%index);path.write_bytes(b'more protected source bytes %d'%index*64);info=path.stat()
            self.manifest['sources'].append({'path':str(path),'size':info.st_size,'modified':str(info.st_mtime_ns),
                                             'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                             'fingerprint':{'size':info.st_size,'modified':str(info.st_mtime_ns)}})

    def retire_original(self):
        self.cleanup.run(self.cleanup_id)
        self.assertFalse(self.source.exists())
        retention=RecoveryRetention(self.storage)
        return retention

    def discharge(self, revisit=False):
        self.life.discharge_published(self.job_id,self.storage,revisit=revisit)


    def test_surviving_original_with_ads_and_enrolled_hold_releases_snapshot(self):
        # A download marker already present when the source was selected.
        # Adding ADS after manifest freeze changes NTFS last-write metadata.
        Path(str(self.source)+':Zone.Identifier').write_bytes(b'[ZoneTransfer]\nZoneId=3')
        modified=str(self.source.stat().st_mtime_ns)
        self.manifest['sources'][0]['modified']=modified
        self.manifest['sources'][0]['fingerprint']['modified']=modified
        attempt,stage,_=self.published(enrolled=True)
        with VerifiedFile(self.source) as original:
            self.assertEqual(str(original.facts()['modified']),modified)
            self.assertEqual(original.sha256(),self.manifest['sources'][0]['sha256'])
        self.cleanup._set(self.cleanup_id,'needs_attention','Original download marker held')
        self.discharge()
        self.assertEqual(list(stage.iterdir()),[])
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'retired')
        self.assertEqual(self.source.read_bytes(),self.original)
        self.assertTrue(Path(str(self.source)+':Zone.Identifier').exists())
        self.assertEqual(self.cleanup.status(self.job_id)['state'],'needs_attention')

    def test_missing_original_without_retirement_receipt_holds_snapshot(self):
        attempt,stage,_=self.published();self.source.unlink()
        with self.assertRaises(BoundaryError):self.discharge()
        self.assertEqual((stage/'source00000.mp3').read_bytes(),self.original)
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'published_held')

    def test_changed_original_without_retirement_holds_snapshot(self):
        _,stage,_=self.published();self.source.write_bytes(b'changed original')
        with self.assertRaises(BoundaryError):self.discharge()
        self.assertTrue((stage/'source00000.mp3').exists())

    def test_actual_original_retirement_and_surviving_recovery_release_snapshot(self):
        attempt,stage,_=self.published(enrolled=True);retention=self.retire_original()
        member=self.cleanup._rows('SELECT * FROM cleanup_members')[0]
        backup=Path(member['backup']);before=backup.read_bytes()
        self.discharge()
        self.assertEqual(list(stage.iterdir()),[])
        self.assertEqual(backup.read_bytes(),before)
        self.assertEqual(retention.status(self.job_id)['state'],'retained')
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'retired')

    def test_actual_terminal_recovery_purge_releases_snapshot_after_original_gone(self):
        attempt,stage,_=self.published(enrolled=True);retention=self.retire_original()
        retention.clock=lambda:datetime.now(timezone.utc)+timedelta(hours=25)
        status=retention.purge(self.job_id)
        self.assertEqual(status['state'],'deleted')
        self.discharge()
        self.assertEqual(list(stage.iterdir()),[])
        self.assertFalse(self.source.exists())
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'retired')

    def test_expired_time_without_actual_recovery_outcome_is_not_purge_proof(self):
        _,stage,_=self.published(enrolled=True);self.retire_original()
        member=self.cleanup._rows('SELECT * FROM cleanup_members')[0];Path(member['backup']).unlink()
        with connect(self.db) as db:
            db.execute("UPDATE recovery_retention SET expires_at=?,state='retained'",((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),))
        with self.assertRaises((OSError,BoundaryError)):self.discharge()
        self.assertTrue((stage/'source00000.mp3').exists())

    def test_false_deleted_retention_without_native_receipts_holds_snapshot(self):
        _,stage,_=self.published(enrolled=True);self.retire_original()
        member=self.cleanup._rows('SELECT * FROM cleanup_members')[0];Path(member['backup']).unlink()
        with connect(self.db) as db:db.execute("UPDATE recovery_retention SET state='deleted',actor='manual',deleted_at=?",(datetime.now(timezone.utc).isoformat(),))
        with self.assertRaises(BoundaryError):self.discharge()
        self.assertTrue((stage/'source00000.mp3').exists())

    def test_recovery_replacement_is_preserved_and_snapshot_held(self):
        _,stage,_=self.published(enrolled=True);self.retire_original()
        member=self.cleanup._rows('SELECT * FROM cleanup_members')[0];backup=Path(member['backup'])
        backup.unlink();backup.write_bytes(self.original)
        with self.assertRaises(BoundaryError):self.discharge()
        self.assertTrue((stage/'source00000.mp3').exists());self.assertEqual(backup.read_bytes(),self.original)

    def test_changed_published_output_holds_snapshot(self):
        _,stage,output=self.published();Path(output['final_path']).write_bytes(b'changed output')
        with self.assertRaises(BoundaryError):self.discharge()
        self.assertTrue((stage/'source00000.mp3').exists())

    def test_new_attempt_binding_holds_old_snapshot(self):
        _,stage,_=self.published();self.queue._update(self.job_id,attempt_id=str(uuid.uuid4()))
        with self.assertRaises(BoundaryError):self.discharge()
        self.assertTrue((stage/'source00000.mp3').exists())

    def test_cross_job_snapshot_reference_holds_copy(self):
        _,stage,_=self.published()
        other=dict(self.manifest,job_id=str(uuid.uuid4()),candidate_id=str(uuid.uuid4()))
        other['evidence']=[str(stage/'source00000.mp3').replace(chr(92),'/').upper()]
        self.queue.enqueue(other)
        with self.assertRaises(BoundaryError):self.discharge()
        self.assertTrue((stage/'source00000.mp3').exists())

    def test_one_reference_check_covers_every_snapshot_of_the_book_0_31_1(self):
        # Sergei 2026-11-24: each snapshot's removal ran the reference check again, and each run reads every reference table
        # (about 6 s on a 379 MB catalog): a 1,436-file book held the recovery cleanup's thread for over an hour. Now one
        # check before the hashing (unchanged) and one for all of the book's snapshots before the first removal.
        self.more_sources(3)
        attempt,stage,_=self.published()
        check,calls=self.life._published_references,[]
        with patch.object(self.life,'_published_references',side_effect=lambda found,paths:(calls.append(list(paths)),check(found,paths))[1]):
            self.discharge()
        self.assertEqual(list(stage.iterdir()),[])
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'retired')
        self.assertEqual(len(calls),2,'twice per book, never once per snapshot')
        self.assertEqual(sorted(Path(path).name for path in calls[1]),['source%05d.mp3'%index for index in range(4)])
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_a_reference_made_while_the_snapshots_are_hashed_keeps_them_0_31_1(self):
        # The check before the first removal sees a reference written after the first check (while the copies were hashed),
        # for any snapshot of the book; nothing of the book is removed.
        self.more_sources(3)
        attempt,stage,_=self.published()
        hashed,referenced=self.life._hash,[]
        def hash_then_reference(handle):
            if not referenced:
                referenced.append(True)
                other=dict(self.manifest,job_id=str(uuid.uuid4()),candidate_id=str(uuid.uuid4()))
                other['evidence']=[str(stage/'source00003.mp3').replace(chr(92),'/').upper()]
                self.queue.enqueue(other)
            return hashed(handle)
        with patch.object(self.life,'_hash',side_effect=hash_then_reference):
            with self.assertRaisesRegex(BoundaryError,'another durable dependency: audio_jobs'):self.discharge()
        self.assertTrue(referenced,'positive control: the reference was written after the first check')
        self.assertEqual(sorted(path.name for path in stage.glob('source*.mp3')),['source%05d.mp3'%index for index in range(4)])
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'published_held')

    def test_same_name_snapshot_replacement_is_not_adopted(self):
        _,stage,_=self.published();path=stage/'source00000.mp3';raw=path.read_bytes()
        path.unlink();path.write_bytes(raw)
        with self.assertRaises(BoundaryError):self.discharge()
        self.assertEqual(path.read_bytes(),raw)

    def test_crash_after_disposition_reconciles_only_durable_exact_intent(self):
        attempt,stage,_=self.published();setter=self.life._file_state
        def fail_once(entry,state,**fields):
            if state=='disposition_set':raise OSError('Private crash after actual native disposition')
            return setter(entry,state,**fields)
        with patch.object(self.life,'_file_state',side_effect=fail_once):
            with self.assertRaises(OSError):self.discharge()
        self.assertFalse((stage/'source00000.mp3').exists())
        self.discharge(revisit=True)
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'retired')
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_idle_reconciliation_is_bounded_and_held_rows_are_not_rehashed(self):
        attempt,stage,_=self.published();self.source.unlink()
        self.life.reconcile(limit=1,storage=self.storage)
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'published_held')
        with patch.object(self.life,'_hash',side_effect=AssertionError('Held input was rehashed')):
            self.assertEqual(self.life.reconcile(limit=1,storage=self.storage),[])
        self.assertTrue((stage/'source00000.mp3').exists())

    def test_unknown_member_stays_protected(self):
        _,stage,_=self.published();(stage/'personal.flac').write_bytes(b'not produced')
        with self.assertRaises(BoundaryError):self.discharge()
        self.assertTrue((stage/'source00000.mp3').exists());self.assertEqual((stage/'personal.flac').read_bytes(),b'not produced')

    def test_preemption_during_original_hash_does_not_fallback_or_mark_hold(self):
        attempt,stage,_=self.published();calls=[]
        def guard():
            calls.append(True)
            if len(calls)==4:raise InterruptedError('Private foreground work admitted')
        self.life.guard=guard
        with patch.object(self.storage,'_source_safety',side_effect=AssertionError('Preemption was treated as missing source')):
            with self.assertRaises(InterruptedError):self.discharge()
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'published')
        self.assertTrue((stage/'source00000.mp3').exists())

    def test_unknown_terminal_recovery_actor_is_not_disposition_authority(self):
        _,stage,_=self.published(enrolled=True);retention=self.retire_original()
        retention.clock=lambda:datetime.now(timezone.utc)+timedelta(hours=25)
        retention.purge(self.job_id)
        with connect(self.db) as db:db.execute("UPDATE recovery_retention SET actor='unknown-provider'")
        with self.assertRaises(BoundaryError):self.discharge()
        self.assertTrue((stage/'source00000.mp3').exists())

    def test_terminal_recovery_directory_legitimately_absent_does_not_strand_snapshot(self):
        attempt,stage,_=self.published(enrolled=True);retention=self.retire_original()
        retention.clock=lambda:datetime.now(timezone.utc)+timedelta(hours=25)
        retention.purge(self.job_id)
        self.assertFalse((self.cleanup.root/self.cleanup_id).exists(),'v0.16.8: the purge removes the emptied set folder')
        self.discharge()
        self.assertEqual(list(stage.iterdir()),[])
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'retired')

    def test_recovery_completion_schedules_without_hashing_then_idle_discharges(self):
        attempt,stage,_=self.published(enrolled=True);retention=self.retire_original()
        retention.clock=lambda:datetime.now(timezone.utc)+timedelta(hours=25)
        retention.purge(self.job_id)
        self.life._set_attempt(self.life._attempt(self.job_id,attempt),state='published_held',reason='Private deferred proof')
        with patch.object(self.life,'_hash',side_effect=AssertionError('Scheduling performed native hash IO')):
            self.life.schedule_published(self.job_id)
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'published')
        self.assertEqual(self.life.reconcile(limit=1,storage=self.storage),[])
        self.assertEqual(list(stage.iterdir()),[])
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'retired')

    def test_actual_resume_prune_adds_no_snapshot_hash_and_completion_only_schedules(self):
        attempt,stage,_=self.published();self.life._set_attempt(self.life._attempt(self.job_id,attempt),state='published_held',reason='Private held snapshot')
        service=MergeService.__new__(MergeService)
        service.working=self.life;service.inventory=SimpleNamespace(database=self.db)
        service.storage_cleanup=SimpleNamespace(working_pending=lambda job:False,status=lambda:[{'job_id':self.job_id,'state':'completed'}],run_folders=lambda *args,**kwargs:None)
        service.recovery=SimpleNamespace(sync=lambda:None)
        service.cleanup=SimpleNamespace(status=lambda job:None)
        with patch.object(self.life,'discharge_published',side_effect=AssertionError('Resume tried source hashing')),patch.object(self.life,'_hash',side_effect=AssertionError('Resume tried source hashing')):
            service._prune_completed(self.job_id)
            self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'published_held')
            service._prune_completed(self.job_id,source_completed=True)
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'published')
        self.assertTrue((stage/'source00000.mp3').exists())
