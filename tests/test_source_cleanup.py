"""Private Windows fixtures only: actual handle removal and recoverability."""
import contextlib
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_cleanup import CleanupJobs, packed
from native_io import DirectoryBoundary, VerifiedFile, BoundaryError
from scanner import connect

class UnreachableOutputFolderTests(unittest.TestCase):
    """Senua 0.21.3 F3: os.path.realpath raises OSError for some network errors (an NAS outage)."""
    def test_an_unreachable_output_folder_reads_as_unavailable_and_never_raises(self):
        import source_config
        def down(path,*args,**kwargs):raise OSError(64,'The specified network name is no longer available')
        with patch.object(source_config.os.path,'realpath',down):
            self.assertEqual(source_config.sorted_problem('Z:\\Audiobooks Sorted',('Z:\\Audiobooks',)),'The output folder cannot be reached')
            with self.assertRaisesRegex(ValueError,'cannot be reached; the source files are kept'):
                source_config.require_sorted('Z:\\Audiobooks Sorted\\A\\B.m4b','Z:\\Audiobooks Sorted',('Z:\\Audiobooks',))
        self.assertIn('The output folder cannot be reached; the source files are kept',source_config.CONFIGURATION_REFUSALS)

class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cleanup-',dir=Path(__file__).resolve().parents[1]/'scratch')
        self.base=Path(self.temp.name);self.library=self.base/'library';self.library.mkdir();self.db=self.base/'catalog.sqlite3';self.good=True
        self.sources=[]
        for i in range(2):
            p=self.library/(str(i)+'.mp3');p.write_bytes(bytes([65+i])*2048);stat=p.stat()
            self.sources.append({'path':str(p),'size':stat.st_size,'modified':str(stat.st_mtime_ns),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        # Sergei, rulings 2 and 1a (2026-10-24): the output is in the sorted folder, outside the source library. Until
        # 0.21.3 this fixture published into the library itself and its originals were still removed (audit C2).
        self.sorted=self.base/'sorted';self.sorted.mkdir();self.output_root=str(self.sorted);self.policy_calls=0
        final=self.sorted/'book.m4b';final.write_bytes(b'validated fixture output')
        with DirectoryBoundary(self.sorted,final.parent) as boundary:identity=boundary.identities
        self.job={'job_id':'test','state':'completed','manifest':{'root':str(self.library),'output_root':str(self.sorted),'sources':self.sources,'cover':{'path':str(final),'sha256':hashlib.sha256(final.read_bytes()).hexdigest()}},
            'output':{'root':str(self.sorted),'final_path':str(final),'size':final.stat().st_size,'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'parent_identity':identity,'validation':{'passed':True}}}
        self.job['manifest'].update(profile='fixture',metadata={'title':'Fixture','canonical_author':'Author'},chapters=[])
        self.job['output']['validation'].update(checks='Output checks passed',profile='fixture',sha256=self.job['output']['sha256'],size=final.stat().st_size,
            tags={'media_type':'2','title':'Fixture','artist':'Author'},source_pcm_frames=[100,100],source_pcm_rate=100,decoded_duration=2,duration_tolerance=.01,chapters=[])
        with connect(self.db) as db:db.execute('CREATE TABLE owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER)')
        self.worker=CleanupJobs(self.db,self.base/'recovery',lambda db,intent:self.good,contextlib.nullcontext,output_policy=self.policy)
        self.id=self.worker.enroll(self.job,{})
    def policy(self):
        self.policy_calls+=1
        return self.output_root,(str(self.library),)
    def tearDown(self):
        self.worker.close();self.temp.cleanup()
    def assert_all_kept(self):
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
        self.assertEqual(self.worker.status('test')['removed'],0)
    # Sergei, rulings 2 and 1a (2026-10-24): a source is removed only when its verified result is in the sorted folder.
    def test_output_in_the_source_library_is_not_enrolled(self):
        inside=json.loads(packed(self.job));inside['job_id']='inside';final=self.library/'book.m4b';final.write_bytes(b'validated fixture output')
        inside['output'].update(final_path=str(final),root=str(self.library));inside['manifest']['output_root']=str(self.library)
        with self.assertRaisesRegex(ValueError,'not in the sorted output folder'):self.worker.enroll(inside,{})
    def test_no_output_folder_keeps_every_original(self):
        self.output_root=None
        with self.assertRaisesRegex(BoundaryError,'No sorted output folder'):self.worker.run(self.id)
        self.assert_all_kept();self.assertFalse(list((self.base/'recovery').rglob('*.mp3')),'refused before any copy')
        with self.assertRaisesRegex(ValueError,'No sorted output folder'):self.worker.enroll(dict(self.job,job_id='another'),{})
    def test_output_folder_overlapping_a_source_keeps_every_original(self):
        for overlapping in (str(self.base),str(self.library),str(self.library/'Sorted')):
            with self.subTest(output=overlapping):
                self.output_root=overlapping
                with self.assertRaisesRegex(BoundaryError,'overlaps a source'):self.worker.run(self.id)
                self.assert_all_kept()
    def test_rule_is_read_again_before_each_removal(self):
        # The configuration changes after every recovery copy is made and before the first removal.
        real=self.policy
        def changing():
            value=real()
            return (None,value[1]) if self.policy_calls>=3 else value  # enroll, run start, then the first removal
        self.worker.output_policy=changing
        with self.assertRaisesRegex(BoundaryError,'No sorted output folder'):self.worker.run(self.id)
        self.assertEqual(len(list((self.base/'recovery'/self.id).glob('*.mp3'))),2,'positive control: it got to the removals')
        self.assert_all_kept()
    def test_a_refusal_right_before_a_removal_records_no_removal_intent_and_restore_finds_no_collision(self):
        # Senua 0.21.3 F2: before, the check ran after removal_intended was committed, so restore() met the
        # still-present original as a collision ("Restore collision; existing file preserved").
        real=self.policy
        def changing():
            value=real()
            return (None,value[1]) if self.policy_calls>=3 else value  # enroll, run start, then the first removal
        self.worker.output_policy=changing
        with self.assertRaisesRegex(BoundaryError,'No sorted output folder'):self.worker.run(self.id)
        with connect(self.db) as db:states=[r[0] for r in db.execute('SELECT state FROM cleanup_members WHERE cleanup_id=?',(self.id,))]
        self.assertEqual(sorted(states),['backup_verified','backup_verified'],'positive control: both recovery copies were made')
        self.worker.restore(self.id)
        self.assert_all_kept()
    def test_a_cleanup_refused_for_a_missing_output_folder_runs_again_once_it_is_set(self):
        # Senua 0.21.3 F1: before, the refusal parked the cleanup for good (needs_attention is terminal), even after
        # the setting came back.
        self.output_root=None
        self.worker._work(follow_audio=False)
        self.assertEqual(self.worker.status('test')['state'],'needs_attention');self.assertIn('No sorted output folder',self.worker.status('test')['reason'])
        self.assert_all_kept()
        self.output_root=str(self.sorted)
        self.worker._work(follow_audio=False)
        self.assertEqual(self.worker.status('test')['state'],'completed');self.assertEqual(self.worker.status('test')['removed'],2)
    def test_a_cleanup_refused_because_its_output_is_outside_sorted_stays_parked(self):
        # The F1 retry covers only the process configuration, never a book whose output really is elsewhere.
        from source_config import CONFIGURATION_REFUSALS
        self.assertNotIn('The audiobook is not in the sorted output folder; the source files are kept',CONFIGURATION_REFUSALS)
    def test_startup_enrolment_without_an_output_folder_parks_nothing(self):
        from types import SimpleNamespace
        from merge_service import MergeService
        parked=[]
        def refused(job_id):raise ValueError('No sorted output folder is set; the source files are kept')
        fake=SimpleNamespace(_dispose_retained=lambda job_id:None,enroll_cleanup=refused,_enrollment_attention=lambda job,error:parked.append(str(error)))
        MergeService._enroll_completed_without_start(fake,{'job_id':'j'})
        self.assertEqual(parked,[],'the next start with the setting enrols the book')
        def other(job_id):raise ValueError('Complete output validation is required')
        fake.enroll_cleanup=other;MergeService._enroll_completed_without_start(fake,{'job_id':'j'})
        self.assertEqual(parked,['Complete output validation is required'])
    def test_without_a_policy_nothing_is_removed(self):
        self.worker.output_policy=None
        with self.assertRaisesRegex(BoundaryError,'No sorted output folder'):self.worker.run(self.id)
        self.assert_all_kept()
    def test_actual_removal_and_exact_restore(self):
        self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['removed'],2)
        self.assertTrue(all(not Path(s['path']).exists() for s in self.sources))
        self.worker.restore(self.id)
        for s in self.sources:
            p=Path(s['path']);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),s['sha256']);self.assertEqual(p.stat().st_mtime_ns,int(s['modified']))
    def test_an_update_waits_for_each_removal_it_began(self):
        # 0.22.1 ruling 27: Restart to update never ends the engine between an original's removal and its record.
        import critical_sections
        seen=[];real=self.worker._retire
        def retire(*args):seen.append(critical_sections.open_sections());return real(*args)
        with patch.object(self.worker,'_retire',side_effect=retire):self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['removed'],2)
        self.assertEqual(seen,[['a cleanup']]*2);self.assertEqual(critical_sections.open_sections(),[])
    def test_output_change_preserves_all_originals(self):
        Path(self.job['output']['final_path']).write_bytes(b'changed')
        with self.assertRaises(BoundaryError):self.worker.run(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_changed_review_blocks_before_delete(self):
        self.good=False
        with self.assertRaises(BoundaryError):self.worker.run(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_pause_after_all_backups_before_first_delete(self):
        self.worker.stop.set();self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['state'],'paused')
        self.assertEqual(len(list((self.base/'recovery'/self.id).glob('*.mp3'))),2)
        self.worker.stop.clear();self.worker.run(self.id);self.assertEqual(self.worker.status('test')['removed'],2)
    def test_native_mutation_denied_while_held(self):
        p=Path(self.sources[0]['path'])
        with DirectoryBoundary(self.library,p.parent),VerifiedFile(p,delete=True) as held:
            with self.assertRaises(PermissionError):p.write_bytes(b'wrong')
            held.dispose()
        self.assertFalse(p.exists())
    def test_unknown_disposition_restorable_without_false_success(self):
        self.worker.stop.set();self.worker.run(self.id);self.worker.stop.clear()
        s=self.sources[0]
        with connect(self.db) as db:db.execute("UPDATE cleanup_members SET state='removal_intended' WHERE cleanup_id=? AND path=?",(self.id,s['path']))
        with DirectoryBoundary(self.library,Path(s['path']).parent),VerifiedFile(s['path'],delete=True) as held:held.dispose()
        with self.assertRaisesRegex(BoundaryError,'unknown outcome'):self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['removed'],0)
        self.worker.restore(self.id);self.assertTrue(Path(s['path']).exists())
    def test_restore_commit_crash_reconciles_exact_owned_identity(self):
        self.worker.run(self.id);original=self.worker._restored
        def crash(id,path):raise RuntimeError('simulated after publication')
        self.worker._restored=crash
        with self.assertRaises(RuntimeError):self.worker.restore(self.id)
        self.worker._restored=original;self.worker.restore(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_restore_collision_preserves_replacement(self):
        self.worker.run(self.id);p=Path(self.sources[0]['path']);p.write_bytes(b'unrelated')
        with self.assertRaises(FileExistsError):self.worker.restore(self.id)
        self.assertEqual(p.read_bytes(),b'unrelated')
    def test_all_backups_flush_before_any_source_removed(self):
        real=VerifiedFile.flush;calls=[]
        def failed_second(handle):
            calls.append(handle.path)
            if len(calls)==2:raise BoundaryError('simulated storage flush failure')
            return real(handle)
        with patch.object(VerifiedFile,'flush',failed_second):
            with self.assertRaisesRegex(BoundaryError,'flush failure'):self.worker.run(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_reused_backups_must_flush_again(self):
        self.worker.stop.set();self.worker.run(self.id);self.worker.stop.clear()
        with patch.object(VerifiedFile,'flush',side_effect=BoundaryError('reused flush denied')):
            with self.assertRaisesRegex(BoundaryError,'reused flush'):self.worker.run(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    # Audit m3: a download marker removed before the backups is put back when the run stops or holds with the original
    # still in place; the original's bytes and write time come back exactly.
    MARKER=b'[ZoneTransfer]' + bytes([13,10]) + b'ZoneId=3' + bytes([13,10])
    def marked(self):
        import zone_identifier,os
        for s in self.sources:
            with open(s['path']+':Zone.Identifier','wb') as stream:stream.write(self.MARKER)
            os.utime(s['path'],ns=(int(s['modified']),int(s['modified'])))  # writing the stream moves the write time
        return zone_identifier
    def assert_marked(self,zone):
        for s in self.sources:
            p=Path(s['path']);self.assertIn((zone.MARKER,len(self.MARKER)),zone.streams(p))
            with open(s['path']+':Zone.Identifier','rb') as stream:self.assertEqual(stream.read(),self.MARKER)
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),s['sha256']);self.assertEqual(p.stat().st_mtime_ns,int(s['modified']))
    def test_markers_are_put_back_when_the_run_pauses_before_removal(self):
        zone=self.marked();self.worker.stop.set();self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['state'],'paused');self.assert_marked(zone)
        with connect(self.db) as db:self.assertEqual(db.execute('SELECT count(*) FROM source_zone_marker_intents').fetchone()[0],2,'the receipts stay')
        self.worker.stop.clear();self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['removed'],2);self.assertTrue(all(not Path(s['path']).exists() for s in self.sources))
    def test_markers_are_put_back_when_the_run_holds(self):
        zone=self.marked();real=VerifiedFile.flush;calls=[]
        def failed_second(handle):
            calls.append(handle.path)
            if len(calls)==2:raise BoundaryError('simulated storage flush failure')
            return real(handle)
        with patch.object(VerifiedFile,'flush',failed_second):
            with self.assertRaisesRegex(BoundaryError,'flush failure'):self.worker.run(self.id)
        self.assertGreaterEqual(len(calls),2,'positive control: it got past the marker removal');self.assert_marked(zone)

    def test_markers_a_killed_run_removed_are_put_back_by_the_next_run(self):
        # Senua 0.21.3 F4: m3 put markers back only for a run that paused or held, never after a crash.
        zone=self.marked();real=VerifiedFile.flush;calls=[]
        def failed_second(handle):
            calls.append(handle.path)
            if len(calls)==2:raise BoundaryError('simulated storage flush failure')
            return real(handle)
        # The killed run: it removed the markers and never reached its own put-back.
        with patch.object(VerifiedFile,'flush',failed_second),patch.object(CleanupJobs,'_put_back_markers',lambda *_:None):
            with self.assertRaisesRegex(BoundaryError,'flush failure'):self.worker.run(self.id)
        self.assertFalse(any(zone.MARKER in {n for n,_ in zone.streams(Path(s['path']))} for s in self.sources),'positive control: the markers are gone')
        # The next run stops at its first review check, before it touches any marker itself.
        self.good=False
        with self.assertRaisesRegex(BoundaryError,'review changed'):self.worker.run(self.id)
        self.assert_marked(zone)

    def test_output_gone_before_a_removal_keeps_every_original(self):
        # Audit m1: the held handle blocks a delete over SMB, not one made on the NAS itself, so the output is read
        # again right before each removal. Here its path stops resolving once every recovery copy is made.
        import os,source_cleanup
        final=os.path.normcase(self.job['output']['final_path']);real=source_cleanup.os.path.lexists
        with patch.object(source_cleanup.os.path,'lexists',side_effect=lambda p:False if os.path.normcase(str(p))==final else real(p)):
            with self.assertRaisesRegex(BoundaryError,'gone before source removal'):self.worker.run(self.id)
        self.assertEqual(len(list((self.base/'recovery'/self.id).glob('*.mp3'))),2,'positive control: it got to the removals')
        self.assert_all_kept()

    def test_hardlink_alias_refused_before_removal(self):
        import os
        os.link(self.sources[0]['path'],self.library/'other-name.mp3')
        with self.assertRaisesRegex(BoundaryError,'alias layout'):self.worker.run(self.id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
    def test_missing_full_validation_cannot_enroll(self):
        changed=json.loads(packed(self.job));changed['job_id']='another';changed['output']['validation'].pop('source_pcm_frames')
        with self.assertRaisesRegex(ValueError,'decoded-audio'):self.worker.enroll(changed,{})
    def test_selected_cleanup_does_not_drain_other_work_or_encode(self):
        from unittest.mock import Mock
        other=json.loads(packed(self.job));other['job_id']='other';other_id=self.worker.enroll(other,{})
        called=[];self.worker.run=lambda id:called.append(id);self.worker.after_drain=Mock()
        self.worker.resume([self.id],follow_audio=False);self.worker.thread.join(5)
        self.assertEqual(called,[self.id]);self.worker.after_drain.assert_not_called()
        self.assertEqual(self.worker.status('other')['state'],'waiting')

if __name__=='__main__':unittest.main()

class OutputIdentityRetryTests(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self):
        f=CleanupTest();f.setUp()
        try:yield f
        finally:f.tearDown()

    def hold_at_second_output_check(self,f,legacy=False):
        from native_io import kernel
        real=f.worker._output_present;calls=[]
        def fail(output,out,final):
            calls.append(str(final))
            if len(calls)==2:
                kernel.CloseHandle(output.handle)
                try:return real(output,out,final)
                finally:output.handle=None
            return real(output,out,final)
        with patch.object(f.worker,'_output_present',side_effect=fail):f.worker.run_with_retry(f.id)
        self.assertEqual(f.worker.status('test')['state'],'needs_attention');f.assert_all_kept()
        if legacy:
            with connect(f.db) as db:db.execute('UPDATE source_cleanup SET reason=? WHERE id=?',('Cannot refresh protected file identity',f.id));db.execute('DELETE FROM source_cleanup_holds WHERE cleanup_id=?',(f.id,))

    def retry(self,f):
        f.worker.resume([f.id],follow_audio=False,identity_retry=f.id);f.worker.thread.join(10)
        self.assertFalse(f.worker.thread.is_alive(),'private retry reached its checkpoint')

    def test_legacy_intent_retry_reopens_and_verifies_every_copy_before_first_delete(self):
        with self.fixture() as f:
            self.hold_at_second_output_check(f,legacy=True)
            cap=f.worker.status('test')['identity_retry'];self.assertTrue(cap['allowed']);self.assertIsNone(cap['diagnostic']);self.assertEqual(cap['output_path'],f.job['output']['final_path'])
            with connect(f.db) as db:states=[r[0] for r in db.execute('SELECT state FROM cleanup_members WHERE cleanup_id=?',(f.id,))]
            self.assertEqual(sorted(states),['backup_verified','removal_intended'])
            hashed=[];real_hash=VerifiedFile.sha256;real_dispose=VerifiedFile.dispose;disposed=[]
            required={s['path'] for s in f.sources}|{str(p) for p in (f.base/'recovery'/f.id).glob('*.mp3')}|{f.job['output']['final_path']}
            def hash_file(h):hashed.append(str(h.path));return real_hash(h)
            def dispose(h):
                self.assertTrue(required<=set(hashed),'all fresh byte proofs precede every new source disposal');disposed.append(str(h.path));return real_dispose(h)
            with patch.object(VerifiedFile,'sha256',hash_file),patch.object(VerifiedFile,'dispose',dispose):self.retry(f)
            self.assertEqual(set(disposed),{s['path'] for s in f.sources});self.assertEqual(f.worker.status('test')['state'],'completed');self.assertEqual(f.worker.status('test')['removed'],2)
            self.assertIsNone(f.worker.status('test')['identity_retry'])
            with connect(f.db) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM source_cleanup').fetchone()[0],1)

    def test_real_windows_error_is_preserved_and_other_refusal_does_not_inherit_retry(self):
        with self.fixture() as f:
            self.hold_at_second_output_check(f)
            cap=f.worker.status('test')['identity_retry'];self.assertTrue(cap['allowed']);self.assertEqual(cap['diagnostic']['windows_error'],6);self.assertEqual(cap['diagnostic']['api'],'GetFileInformationByHandle');self.assertIn('Windows error 6',f.worker.status('test')['reason'])
            self.assertEqual(cap['diagnostic']['path'],f.job['output']['final_path'])
            f.worker.hold(f.id,BoundaryError('Original bytes differ from reviewed sources'))
            self.assertIsNone(f.worker.identity_retry(f.id));f.assert_all_kept()

    def test_changed_or_missing_output_refuses_before_any_new_deletion(self):
        for missing in (False,True):
            with self.subTest(missing=missing),self.fixture() as f:
                self.hold_at_second_output_check(f,legacy=True);final=Path(f.job['output']['final_path'])
                if missing:final.unlink()
                else:final.write_bytes(b'changed output')
                self.retry(f);f.assert_all_kept();self.assertEqual(f.worker.status('test')['state'],'needs_attention')

    def test_changed_or_missing_recovery_and_changed_source_never_delete_another_file(self):
        for changed in ('backup','missing_backup','source'):
            with self.subTest(changed=changed),self.fixture() as f:
                self.hold_at_second_output_check(f,legacy=True)
                backup=next((f.base/'recovery'/f.id).glob('*.mp3'))
                if changed=='missing_backup':backup.unlink()
                elif changed=='backup':backup.write_bytes(b'changed backup')
                else:Path(f.sources[0]['path']).write_bytes(b'changed original')
                self.retry(f);f.assert_all_kept();self.assertEqual(f.worker.status('test')['state'],'needs_attention');self.assertIsNone(f.worker.identity_retry(f.id))

    def test_missing_original_after_removal_intent_remains_unknown_not_adopted(self):
        with self.fixture() as f:
            self.hold_at_second_output_check(f,legacy=True);Path(f.sources[0]['path']).unlink()
            self.retry(f);self.assertTrue(Path(f.sources[1]['path']).is_file());self.assertEqual(f.worker.status('test')['removed'],0);self.assertIn('unknown outcome',f.worker.status('test')['reason'])

    def test_explicit_retry_is_single_owner_and_pause_keeps_the_checkpoint(self):
        import threading
        with self.fixture() as f:
            self.hold_at_second_output_check(f,legacy=True);entered=threading.Event();release=threading.Event();real=f.worker._run
            def waiting(*args):entered.set();release.wait(3);return real(*args)
            with patch.object(f.worker,'_run',side_effect=waiting):
                f.worker.resume([f.id],follow_audio=False,identity_retry=f.id);self.assertTrue(entered.wait(2));first=f.worker.thread
                try:
                    with self.assertRaisesRegex(ValueError,'no longer offers'):f.worker.resume([f.id],follow_audio=False,identity_retry=f.id)
                    self.assertIs(f.worker.thread,first);f.worker.pause()
                finally:release.set();first.join(5)
            self.assertFalse(first.is_alive());f.assert_all_kept();self.assertEqual(f.worker.status('test')['state'],'paused')
