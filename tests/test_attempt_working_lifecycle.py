"""Private Windows file/SQLite fixtures; no real library or media tools.

Producer tests launch only this capsule's pinned Python with fixed inline code.
They exercise actual owned cancellation/disposition, not codec correctness.
"""
from sorted_fixture import library_is_sorted  # 0.21.3: fixtures publish inside their library
import errno
import base64
import contextlib
import ctypes
from ctypes import wintypes
import struct
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import sqlite3
from types import SimpleNamespace
import threading
import time
import unittest
import uuid
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audio_jobs import AudioJobs
from audio_pipeline import Paused, copy_owned, create_private, generated_artifacts, plan_generated, run_owned
from merge_service import MergeService
from native_io import BoundaryError, DirectoryBoundary, kernel
from scanner import connect
from source_cleanup import CleanupJobs, packed
from storage_cleanup import StorageCleanup
from encoding_policy import AUTOMATIC_PROFILE
from working_lifecycle import WorkingLifecycle, VerifiedFile


@unittest.skipUnless(os.name=='nt','Actual Windows native file fixtures required')
class WorkingLifecycleTests(unittest.TestCase):
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
            copy_owned(self.source,directory/'source00000.mp3',self.manifest['sources'][0]['sha256'],threading.Event())
            copy_owned(self.cover,directory/'cover.jpg',self.manifest['cover']['sha256'],threading.Event())
            for name,raw in [('checked.m4b',b'failed generated output'),('compatible.m4b',b'failed rewritten output')]+list(extras):
                plan_generated(directory/name);(directory/name).write_bytes(raw)
        self.queue._update(self.job_id,state='needs attention',reason='Private deliberate fixture failure')
        return attempt,directory,dict(receipts)

    def test_failed_generated_and_restageable_sources_removed_history_unchanged(self):
        attempt,stage,receipts=self.stage()
        before=self.queue._rows('SELECT * FROM audio_jobs')[0]
        self.life.terminal(self.job_id,attempt)
        self.assertEqual(list(stage.iterdir()),[])
        self.assertEqual(before,self.queue._rows('SELECT * FROM audio_jobs')[0])
        self.assertEqual(self.source.read_bytes(),self.original)
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'retired')

    def test_original_unavailable_frees_generated_but_keeps_unique_snapshot(self):
        attempt,stage,_=self.stage();self.source.unlink()
        self.life.terminal(self.job_id,attempt)
        self.assertFalse((stage/'checked.m4b').exists())
        self.assertEqual((stage/'source00000.mp3').read_bytes(),self.original)
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'sources_retained')
        with self.assertRaises(BoundaryError):self.life.admit(self.queue._rows('SELECT * FROM audio_jobs')[0])

    def test_changed_original_and_snapshot_prevent_all_disposition(self):
        attempt,stage,_=self.stage()
        self.source.write_bytes(b'changed original');(stage/'source00000.mp3').write_bytes(b'changed snapshot')
        with self.assertRaises(BoundaryError):self.life.terminal(self.job_id,attempt)
        self.assertTrue((stage/'checked.m4b').exists())

    def test_changed_target_identity_or_hash_is_preserved(self):
        attempt,stage,_=self.stage();target=stage/'checked.m4b';raw=target.read_bytes()
        target.unlink();target.write_bytes(raw)
        with self.assertRaises(BoundaryError):self.life.terminal(self.job_id,attempt)
        self.assertEqual(target.read_bytes(),raw)

    def test_active_or_publishing_attempt_cannot_dispose(self):
        attempt,stage,_=self.stage()
        self.queue._update(self.job_id,state='running')
        with self.assertRaises(BoundaryError):self.life.terminal(self.job_id,attempt)
        self.queue._update(self.job_id,state='needs attention',journal=json.dumps({'publication_intent':{'unresolved':True}}))
        with self.assertRaises(BoundaryError):self.life.terminal(self.job_id,attempt)
        self.assertTrue((stage/'checked.m4b').exists())

    def test_cross_job_forward_slash_reference_blocks(self):
        attempt,stage,_=self.stage()
        other=dict(self.manifest,job_id=str(uuid.uuid4()),candidate_id=str(uuid.uuid4()))
        other['evidence']=[str(stage/'checked.m4b').replace(chr(92),'/').upper()]
        self.queue.enqueue(other)
        with self.assertRaises(BoundaryError):self.life.terminal(self.job_id,attempt)
        self.assertTrue((stage/'checked.m4b').exists())

    def test_owned_artifact_and_cleanup_intent_dependencies_block(self):
        attempt,stage,_=self.stage()
        with connect(self.db) as db:
            db.execute('CREATE TABLE owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER)')
            db.execute('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)',(str(stage/'checked.m4b'),str(uuid.uuid4()),'temporary','',0))
        with self.assertRaises(BoundaryError):self.life.terminal(self.job_id,attempt)
        self.assertTrue((stage/'checked.m4b').exists())

    def test_extra_stream_is_retained(self):
        attempt,stage,_=self.stage();target=stage/'checked.m4b'
        Path(str(target)+':meaningful').write_bytes(b'preserved private stream')
        with self.assertRaises(BoundaryError):self.life.terminal(self.job_id,attempt)
        self.assertEqual(Path(str(target)+':meaningful').read_bytes(),b'preserved private stream')

    def test_hardlink_is_retained(self):
        attempt,stage,_=self.stage();target=stage/'checked.m4b';os.link(target,self.base/'alias.m4b')
        with self.assertRaises(BoundaryError):self.life.terminal(self.job_id,attempt)
        self.assertTrue(target.exists())

    def test_crash_after_intent_resumes_same_exact_file(self):
        attempt,stage,_=self.stage()
        with patch.object(VerifiedFile,'dispose',side_effect=RuntimeError('private crash before native disposition')):
            with self.assertRaises(RuntimeError):self.life.terminal(self.job_id,attempt)
        self.assertTrue((stage/'checked.m4b').exists())
        WorkingLifecycle(self.db,self.stage_root).reconcile(limit=1)
        self.assertEqual(list(stage.iterdir()),[])
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_crash_after_disposition_reconciles_durable_intent_absence(self):
        attempt,stage,_=self.stage();original=self.life._file_state
        def fail_receipt(entry,state,**fields):
            if state=='disposition_set':raise RuntimeError('private crash after native disposition')
            return original(entry,state,**fields)
        with patch.object(self.life,'_file_state',side_effect=fail_receipt):
            with self.assertRaises(RuntimeError):self.life.terminal(self.job_id,attempt)
        self.assertFalse((stage/'checked.m4b').exists())
        WorkingLifecycle(self.db,self.stage_root).reconcile(limit=1)
        self.assertEqual(list(stage.iterdir()),[])
        rows=self.life._files(self.job_id,attempt)
        self.assertEqual(next(row for row in rows if row['name']=='checked.m4b')['state'],'absent_after_intent')

    def test_terminal_name_replacement_not_adopted(self):
        attempt,stage,_=self.stage();self.life.terminal(self.job_id,attempt)
        (stage/'checked.m4b').write_bytes(b'replacement')
        with self.assertRaises(BoundaryError):self.life.admit(self.queue._rows('SELECT * FROM audio_jobs')[0])
        self.assertEqual((stage/'checked.m4b').read_bytes(),b'replacement')

    def test_retired_attempt_admission_does_not_hash_whole_library_again(self):
        attempt,stage,_=self.stage();self.life.terminal(self.job_id,attempt)
        with patch.object(self.life,'_hash',side_effect=AssertionError('unexpected repeated media hash')):
            self.life.admit(self.queue._rows('SELECT * FROM audio_jobs')[0])

    def test_success_handoff_reclaims_all_published_roles_despite_original_ads_hold(self):
        self.manifest['profile']=AUTOMATIC_PROFILE
        encoded=packed(self.manifest)
        self.queue._update(self.job_id,manifest=encoded,manifest_hash=hashlib.sha256(encoded.encode()).hexdigest())
        diagnostic=uuid.uuid4().hex+'.stdout'
        attempt,stage,receipts=self.stage(extras=[('normalized00000.wav',b'private exact PCM fixture'),
                                                ('inputs.txt',b'private input plan'),('chapters.txt',b'private chapter plan'),
                                                (diagnostic,b'private successful probe')])
        final=Path(self.manifest['destination']);final.write_bytes(b'private validated output fixture')
        sha=hashlib.sha256(final.read_bytes()).hexdigest();size=final.stat().st_size
        with DirectoryBoundary(self.library,self.library) as boundary:parent_identity=boundary.identities
        validation={'passed':True,'checks':'Output checks passed','profile':AUTOMATIC_PROFILE,'sha256':sha,'size':size,
                    'tags':{'media_type':'2','title':self.manifest['metadata']['title'],'artist':self.manifest['metadata']['canonical_author']},
                    'source_pcm_frames':[100],'source_pcm_rate':100,'decoded_duration':1,'duration_tolerance':.01,'chapters':[],
                    'staging_artifacts':{'attempt_id':attempt,'files':receipts}}
        output={'job_id':self.job_id,'final_path':str(final),'owned_temp':str(self.library/'absent.partial'),
                'sha256':sha,'size':size,'parent_identity':parent_identity,'validation':validation}
        self.queue._update(self.job_id,state='completed',output=json.dumps(output),journal=json.dumps({'publication_intent':output}))
        # The fixture supplies an already validated durable output contract;
        # this is actual native cleanup proof, not a claim of codec/media QA.
        cleanup=CleanupJobs(self.db,self.base/'recovery',lambda *args:True,contextlib.nullcontext,output_policy=library_is_sorted(self.library))
        try:
            storage=StorageCleanup(self.db,self.stage_root,cleanup.root)
            Path(str(self.source)+':Zone.Identifier').write_bytes(b'[ZoneTransfer]\nZoneId=3')
            self.life.terminal(self.job_id,attempt)
            self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'published')
            result=storage.working_files(self.job_id)
            self.assertEqual({Path(item['path']).name for item in result['files']},set(receipts)-{'source00000.mp3'})
            self.assertEqual({path.name for path in stage.iterdir()},{'source00000.mp3'})
            self.assertEqual(final.read_bytes(),b'private validated output fixture')
            self.assertEqual(self.source.read_bytes(),self.original)
            self.assertTrue(Path(str(self.source)+':Zone.Identifier').exists())
            with self.assertRaises(BoundaryError):self.life.retire(self.job_id,attempt)
        finally:cleanup.close()

    def test_incomplete_capture_never_adopts_later_same_name(self):
        attempt=str(uuid.uuid4());self.queue._update(self.job_id,state='running',attempt_id=attempt,journal='{}')
        self.life.begin(dict(self.manifest,attempt_id=attempt))
        parent=self.stage_root/self.job_id;parent.mkdir();(parent/'ownership.json').write_text(packed({'job_id':self.job_id,'manifest':self.manifest}),encoding='utf8')
        stage=parent/attempt;stage.mkdir()
        self.life.planned(stage,stage/'checked.m4b');(stage/'checked.m4b').write_bytes(b'uncaptured')
        with patch.object(self.life,'_hash',side_effect=OSError('capture failed')):
            with self.assertRaises(OSError):self.life.closed(stage)
        self.queue._update(self.job_id,state='needs attention')
        (stage/'checked.m4b').unlink();(stage/'checked.m4b').write_bytes(b'new replacement')
        self.life.reconcile(limit=1)
        self.assertEqual((stage/'checked.m4b').read_bytes(),b'new replacement')
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'attention')

    def test_uncertain_producer_closure_blocks_new_attempt(self):
        attempt,stage,_=self.stage()
        current=self.life._attempt(self.job_id,attempt)
        self.life._set_attempt(current,producer='uncertain',state='attention',reason='private failed native closure')
        self.life.reconcile(limit=1)
        with self.assertRaises(BoundaryError):self.life.admit(self.queue._rows('SELECT * FROM audio_jobs')[0])
        self.assertTrue((stage/'checked.m4b').exists())

    def test_unknown_attempt_file_is_not_claimed_by_retirement(self):
        attempt,stage,_=self.stage();unknown=stage/'unknown-personal.flac';unknown.write_bytes(b'not owned by producer')
        # Files arriving after capture are not ledger-owned and cannot be selected.
        self.life.terminal(self.job_id,attempt)
        self.assertEqual(unknown.read_bytes(),b'not owned by producer')
        self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'attention')
        with self.assertRaises(BoundaryError):self.life.admit(self.queue._rows('SELECT * FROM audio_jobs')[0])

    def test_insufficient_peak_space_creates_no_source_copy(self):
        def runner(manifest,stop,checkpoint):
            with patch('audio_pipeline.shutil.disk_usage',return_value=type('Usage',(),{'free':0})()):
                return create_private(manifest,self.stage_root,stop,artifact_observer=self.life)
        self.queue.runner=runner;self.queue._work()
        row=self.queue._rows('SELECT * FROM audio_jobs')[0]
        self.assertEqual(row['state'],'needs attention');self.assertTrue(self.queue._stop.is_set())
        self.assertFalse(any(self.stage_root.rglob('source00000.mp3')))
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_repeated_actual_owned_producer_failures_do_not_accumulate(self):
        def runner(manifest,stop,checkpoint):
            self.life.begin(manifest)
            parent=self.stage_root/self.job_id;parent.mkdir(exist_ok=True)
            marker=parent/'ownership.json'
            if not marker.exists():marker.write_text(packed({'job_id':self.job_id,'manifest':self.manifest}),encoding='utf8')
            stage=parent/manifest['attempt_id'];stage.mkdir()
            with generated_artifacts(stage,self.life):
                copy_owned(self.source,stage/'source00000.mp3',self.manifest['sources'][0]['sha256'],stop)
                target=stage/'checked.m4b';plan_generated(target)
                code='from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(b"private generated bytes")'
                run_owned([sys.executable,'-I','-S','-B','-c',code,str(target)],stage,stop,10)
                raise OSError(errno.EIO,'private deliberate retriable failure')
        self.queue.runner=runner
        for index in range(3):
            if index:
                result=self.queue.retry_failed(self.job_id,now=time.time()+7200)
                self.assertTrue(result['requeued'])
            self.queue._stop.clear();self.queue._work()
            self.assertFalse(any(self.stage_root.rglob('checked.m4b')))
            self.assertFalse(any(self.stage_root.rglob('source00000.mp3')))
            self.assertEqual(self.source.read_bytes(),self.original)
        with connect(self.db) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM audio_failure_history').fetchone()[0],2)

    def test_idle_reconciliation_is_one_attempt_not_a_full_library_sweep(self):
        first,first_stage,_=self.stage()
        self.job_id=str(uuid.uuid4())
        self.manifest=dict(self.manifest,job_id=self.job_id,candidate_id=str(uuid.uuid4()))
        self.queue.enqueue(self.manifest)
        second,second_stage,_=self.stage()
        self.life.reconcile(limit=1)
        states=self.life._rows('SELECT state FROM working_attempts')
        self.assertEqual(sorted(row['state'] for row in states),['closed','retired'])
        self.assertEqual(sum((stage/'checked.m4b').exists() for stage in (first_stage,second_stage)),1)
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_actual_cancel_keeps_job_pending_without_an_abandoned_audio_set(self):
        def runner(manifest,stop,checkpoint):
            self.life.begin(manifest)
            parent=self.stage_root/self.job_id;parent.mkdir()
            (parent/'ownership.json').write_text(packed({'job_id':self.job_id,'manifest':self.manifest}),encoding='utf8')
            stage=parent/manifest['attempt_id'];stage.mkdir()
            timer=threading.Timer(.2,stop.set)
            try:
                with generated_artifacts(stage,self.life):
                    copy_owned(self.source,stage/'source00000.mp3',self.manifest['sources'][0]['sha256'],stop)
                    target=stage/'checked.m4b';plan_generated(target)
                    code='from pathlib import Path; import sys,time; Path(sys.argv[1]).write_bytes(b"private cancel bytes"); time.sleep(10)'
                    timer.start()
                    run_owned([sys.executable,'-I','-S','-B','-c',code,str(target)],stage,stop,10)
            finally:
                timer.cancel()
                if timer.ident is not None:timer.join(3)
        self.queue.runner=runner;self.queue._work()
        row=self.queue._rows('SELECT * FROM audio_jobs')[0]
        self.assertEqual(row['state'],'pending')
        self.assertTrue(self.queue._stop.is_set())
        self.assertFalse(any(self.stage_root.rglob('checked.m4b')))
        self.assertFalse(any(self.stage_root.rglob('source00000.mp3')))
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_native_hashing_does_not_hold_a_sqlite_write_transaction(self):
        attempt,stage,_=self.stage()
        with connect(self.db) as db:db.execute('CREATE TABLE contention_probe(n INTEGER)')
        calls=[]
        def writer():
            with contextlib.closing(sqlite3.connect(self.db,timeout=.1)) as db:
                with db:
                    db.execute('BEGIN IMMEDIATE')
                    db.execute('INSERT INTO contention_probe VALUES(1)')
            calls.append(True)
        self.life.guard=writer
        self.life.terminal(self.job_id,attempt)
        self.assertGreater(len(calls),1)
        self.assertEqual(list(stage.iterdir()),[])

    def test_actual_resume_preempts_unrelated_background_hash_without_global_lock(self):
        attempt,stage,_=self.stage()
        other=dict(self.manifest,job_id=str(uuid.uuid4()),candidate_id=str(uuid.uuid4()))
        self.queue.enqueue(other)
        hash_entered=threading.Event();release_hash=threading.Event()
        running=threading.Event();finish=threading.Event()
        service=MergeService.__new__(MergeService)
        service.operation_lock=threading.RLock();service._retention_stop=threading.Event()
        service.jobs=self.queue;service.working=self.life;service._post_current=None
        service._no_scan=lambda:None
        service.cleanup=SimpleNamespace(thread=None,_rows=lambda *args:[])
        service.state=lambda:self.queue.status()
        self.life.guard=service._working_guard
        original_hash=self.life._hash
        def held_hash(handle):
            if self.life.in_background:
                hash_entered.set()
                if not release_hash.wait(3):raise RuntimeError('Private fixture hash wait expired')
            return original_hash(handle)
        def runner(manifest,stop,checkpoint):
            running.set()
            if not finish.wait(3):raise RuntimeError('Private fixture worker wait expired')
            raise OSError(errno.EIO,'Private unrelated job fixture')
        self.queue.runner=runner
        with patch.object(self.life,'_hash',side_effect=held_hash):
            background=threading.Thread(target=lambda:self.life.reconcile(limit=1))
            background.start()
            try:
                self.assertTrue(hash_entered.wait(3))
                self.assertEqual(self.life.reconcile(limit=1),[])  # Concurrent tick cannot overwrite background identity.
                service.resume()
                self.assertTrue(running.wait(2),'Resume waited for an unrelated working cleanup hash')
                release_hash.set();background.join(3)
                self.assertFalse(background.is_alive())
                self.assertEqual(self.life._attempt(self.job_id,attempt)['state'],'closed')
                self.assertTrue((stage/'checked.m4b').exists())
            finally:
                release_hash.set();finish.set();background.join(3)
                self.queue.close()

    def test_compact_actual_diagnostics_survive_generated_file_retirement(self):
        name=uuid.uuid4().hex+'.stdout'
        payload=json.dumps({'streams':[{'codec_type':'audio','codec_name':'aac','time_base':'1/22050','start_pts':2112}],
                            'format':{'duration':'123.456'},'padding':'x'*10000}).encode()
        attempt,stage,_=self.stage(extras=[(name,payload)])
        self.life.terminal(self.job_id,attempt)
        self.assertFalse((stage/name).exists())
        saved=self.life._rows('SELECT * FROM working_diagnostics WHERE name=?',(name,))[0]
        evidence=json.loads(saved['evidence'])
        self.assertEqual(saved['sha256'],hashlib.sha256(payload).hexdigest())
        self.assertTrue(evidence['truncated']);self.assertFalse(evidence['complete'])
        self.assertEqual(base64.b64decode(evidence['head']),payload[:4096])
        self.assertEqual(base64.b64decode(evidence['tail']),payload[-4096:])
        self.assertEqual(evidence['semantic']['streams'][0]['start_pts'],2112)
        self.assertEqual(evidence['semantic']['streams'][0]['time_base'],'1/22050')

    def test_real_junction_ancestry_refuses_disposition(self):
        attempt,stage,_=self.stage()
        actual=self.base/'moved-stage';stage.rename(actual);stage.mkdir()
        substitute=(chr(92)+'??'+chr(92)+str(actual)).encode('utf-16-le')
        printed=str(actual).encode('utf-16-le')
        names=substitute+b'\x00\x00'+printed+b'\x00\x00'
        payload=struct.pack('<HHHH',0,len(substitute),len(substitute)+2,len(printed))+names
        raw=struct.pack('<IHH',0xA0000003,len(payload),0)+payload
        handle=kernel.CreateFileW(str(stage),0x40000000,7,None,3,0x02000000|0x00200000,None)
        self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
        try:
            kernel.DeviceIoControl.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
            kernel.DeviceIoControl.restype=wintypes.BOOL
            buffer=ctypes.create_string_buffer(raw);written=wintypes.DWORD()
            if not kernel.DeviceIoControl(handle,0x900A4,buffer,len(raw),None,0,ctypes.byref(written),None):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:self.assertTrue(kernel.CloseHandle(handle))
        try:
            self.assertTrue(os.path.isjunction(stage))
            with self.assertRaises(BoundaryError):self.life.terminal(self.job_id,attempt)
            self.assertTrue((actual/'checked.m4b').exists())
            self.assertEqual(self.source.read_bytes(),self.original)
        finally:stage.rmdir()  # Remove this owned junction entry, never its target.

    def test_legacy_snapshot_without_retirement_receipt_blocks_new_copy(self):
        attempt=str(uuid.uuid4());stage=self.stage_root/self.job_id/attempt;stage.mkdir(parents=True)
        (stage/'source00000.mp3').write_bytes(self.original)
        self.queue._update(self.job_id,attempt_id=attempt,state='pending')
        with self.assertRaisesRegex(BoundaryError,'Legacy attempt'):
            self.life.admit(self.queue._rows('SELECT * FROM audio_jobs')[0])
        self.assertEqual((stage/'source00000.mp3').read_bytes(),self.original)

    def test_actual_owned_timeout_closes_producer_before_disposal(self):
        attempt=str(uuid.uuid4());self.queue._update(self.job_id,state='running',attempt_id=attempt,journal='{}')
        self.life.begin(dict(self.manifest,attempt_id=attempt))
        parent=self.stage_root/self.job_id;parent.mkdir();(parent/'ownership.json').write_text(packed({'job_id':self.job_id,'manifest':self.manifest}),encoding='utf8')
        stage=parent/attempt;stage.mkdir();stop=threading.Event()
        with self.assertRaises(TimeoutError):
            with generated_artifacts(stage,self.life):
                copy_owned(self.source,stage/'source00000.mp3',self.manifest['sources'][0]['sha256'],stop)
                target=stage/'checked.m4b';plan_generated(target)
                code='from pathlib import Path; import sys,time; Path(sys.argv[1]).write_bytes(b"private partial bytes"); time.sleep(10)'
                run_owned([sys.executable,'-I','-S','-B','-c',code,str(target)],stage,stop,2)
        checked=next(row for row in self.life._files(self.job_id,attempt) if row['name']=='checked.m4b')
        self.assertEqual(checked['state'],'closed');self.assertGreater(checked['size'],0)
        self.queue._update(self.job_id,state='needs attention')
        self.life.terminal(self.job_id,attempt)
        self.assertEqual(list(stage.iterdir()),[])
        self.assertEqual(self.source.read_bytes(),self.original)


if __name__=='__main__':unittest.main()
