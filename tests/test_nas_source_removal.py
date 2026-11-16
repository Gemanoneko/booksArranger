"""Sergei, 2026-11-16: NAS originals are removed by the pre-0.28 exact-handle method once every check passes.

Private fixtures only (repository scratch); no live catalog, library, NAS share or installed app. A remote volume is
simulated by the provider's own remote/unverifiable refusal plus positive remote proof, and once for real through
this machine's own loopback SMB share when it is reachable.
"""
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import native_io
from native_io import DirectoryBoundary, VerifiedFile, BoundaryError, FileRemovalRetained
import runtime_file_disposition as runtime
import runtime_disposition_owners
from runtime_disposition_owners import support_dispositions
from scanner import connect
import source_cleanup
from source_cleanup import CleanupJobs, RETAINED_HOLD
from storage_relocation import RelocationRefused

SCRATCH=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',str(Path(__file__).resolve().parents[1]/'scratch')))
RESTORED='Originals restored; recovery copies retained. Cleanup is not automatically repeated.'
WNNC_NET_DAV=0x002E0000  # a non-SMB redirector (WebDAV), for the m1 protocol check


def remote_refusal(handle):
    raise runtime.RemoteProviderRefused(runtime.REMOTE_PROVIDER_REFUSAL)


@contextlib.contextmanager
def nas_volume(proof=None):
    """The target volume as the hardened provider sees the NAS: refused as remote, positively a network handle."""
    with patch.object(runtime,'_local_provider',remote_refusal),patch.object(native_io,'remote_handle',side_effect=proof or (lambda handle,path:True)):
        yield


@contextlib.contextmanager
def smb_from_another_machine():
    """Real loopback SMB handles read as if the share were on another machine: only the loopback bit is cleared.

    Yields every real (protocol, flags) seen, so a test can prove the handles were real loopback SMB handles."""
    real=native_io.remote_protocol;seen=[]
    def protocol(handle):
        found=real(handle)
        if found is not None:seen.append(found);found=(found[0],found[1]&~native_io.REMOTE_PROTOCOL_FLAG_LOOPBACK)
        return found
    with patch.object(native_io,'remote_protocol',protocol):yield seen


def final_name(handle):
    """The file name behind a raw native handle (its last path component)."""
    api=native_io.kernel.GetFinalPathNameByHandleW
    api.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD];api.restype=wintypes.DWORD
    buffer=ctypes.create_unicode_buffer(32768);api(handle,buffer,len(buffer),0)
    return buffer.value.rsplit('\\',1)[-1]


class DeniedDelete:
    """native_io's kernel32, except that setting a delete (FileDispositionInfo) on the given raw handles is denied
    with ERROR_ACCESS_DENIED, as a NAS denies it."""
    def __init__(self,real,handles):
        self.real=real;self.handles=handles;self.denied=[]
        real.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        real.SetFileInformationByHandle.restype=wintypes.BOOL
    def __getattr__(self,name):
        value=getattr(self.real,name)
        if name!='SetFileInformationByHandle':return value
        def call(handle,kind,buffer,size):
            if kind==4 and handle in self.handles:
                self.denied.append(handle);ctypes.set_last_error(5);return False
            return value(handle,kind,buffer,size)
        return call


class LostReply:
    """native_io's kernel32, except that setting a delete (FileDispositionInfo) on a matching raw handle really sets it,
    then reports a network error (WinError 64), as when an SMB reply is lost after the server applied it (Senua P6)."""
    def __init__(self,real,match):
        self.real=real;self.match=match;self.lost=[]
        real.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        real.SetFileInformationByHandle.restype=wintypes.BOOL
    def __getattr__(self,name):
        value=getattr(self.real,name)
        if name!='SetFileInformationByHandle':return value
        def call(handle,kind,buffer,size):
            if kind==4 and self.match(handle):
                if not value(handle,kind,buffer,size):return False
                self.lost.append(handle);ctypes.set_last_error(64);return False
            return value(handle,kind,buffer,size)
        return call


@contextlib.contextmanager
def stale_withdraw_answers(match,pending_too):
    """Inside _withdraw_intent only, the held handle of a matching original answers as an SMB client may from its cache
    after a lost reply: one link, and also no pending delete when pending_too. Yields, per such withdraw, the answers
    its checks would read (same identity, links, pending delete, name present) and whether it withdrew."""
    real=CleanupJobs._withdraw_intent;seen=[]
    def withdraw(db,id,source,original,facts):
        if not match(source['path']):return real(db,id,source,original,facts)
        fresh=VerifiedFile.refresh;pending=VerifiedFile.delete_pending
        original.refresh=lambda:dict(fresh(original),links=1)
        original.delete_pending=(lambda:False) if pending_too else (lambda:pending(original))
        try:
            now=original.refresh()
            record={'same_identity':all(now.get(k)==facts.get(k) for k in ('identity','identity_method','dev','ino')),'links':now['links'],
                    'pending':original.delete_pending(),'name_present':os.path.lexists(source['path'])}
            record['withdrawn']=real(db,id,source,original,facts)
        finally:del original.refresh,original.delete_pending
        seen.append(record);return record['withdrawn']
    with patch.object(CleanupJobs,'_withdraw_intent',staticmethod(withdraw)):yield seen


def restore_temporaries(folder):
    return sorted(p.name for p in Path(folder).glob('.books-restore-*'))


def loopback(path):
    """This machine's own administrative SMB share for a local fixture path, or None when it is unreachable."""
    anchor=Path(path).anchor
    if len(anchor)<2 or anchor[1]!=':':return None
    remote=Path('\\\\localhost\\'+anchor[0]+'$\\'+str(path)[len(anchor):])
    return remote if os.path.isdir(remote) else None


class CleanupFixture:
    """One completed two-track book; its library is seen through view() (locally, or through loopback SMB)."""
    def view(self,path):return path
    def arrange(self,sources):return sources
    def setUp(self):
        SCRATCH.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='nas-removal-',dir=SCRATCH)
        self.base=Path(self.temp.name);local=self.base/'library';local.mkdir();self.db=self.base/'catalog.sqlite3'
        try:self.library=self.view(local)
        except BaseException:self.temp.cleanup();raise
        self.sources=[]
        for i in range(2):
            p=local/(str(i)+'.mp3');p.write_bytes(bytes([65+i])*2048);stat=p.stat()
            self.sources.append({'path':str(self.library/p.name),'size':stat.st_size,'modified':str(stat.st_mtime_ns),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        self.sources=self.arrange(self.sources)
        self.sorted=self.base/'sorted';self.sorted.mkdir()
        final=self.sorted/'book.m4b';final.write_bytes(b'validated fixture output')
        with DirectoryBoundary(self.sorted,final.parent) as boundary:identity=boundary.identities
        self.job={'job_id':'test','state':'completed','manifest':{'root':str(self.library),'output_root':str(self.sorted),'sources':self.sources,'cover':{'path':str(final),'sha256':hashlib.sha256(final.read_bytes()).hexdigest()}},
            'output':{'root':str(self.sorted),'final_path':str(final),'size':final.stat().st_size,'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'parent_identity':identity,'validation':{'passed':True}}}
        self.job['manifest'].update(profile='fixture',metadata={'title':'Fixture','canonical_author':'Author'},chapters=[])
        self.job['output']['validation'].update(checks='Output checks passed',profile='fixture',sha256=self.job['output']['sha256'],size=final.stat().st_size,
            tags={'media_type':'2','title':'Fixture','artist':'Author'},source_pcm_frames=[100,100],source_pcm_rate=100,decoded_duration=2,duration_tolerance=.01,chapters=[])
        with connect(self.db) as db:
            db.execute('CREATE TABLE owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER)')
            db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,state TEXT)')
            db.execute("INSERT INTO audio_jobs VALUES('test','completed')")
        self.stack=contextlib.ExitStack()
        # The explicit owner every disposition needs; created before any provider is simulated.
        self.context=self.stack.enter_context(support_dispositions(self.base,[self.library]))
        self.worker=self.start();self.id=self.worker.enroll(self.job,{})
    def start(self):
        """A fresh CleanupJobs on the same catalog: what the app constructs at startup."""
        return CleanupJobs(self.db,self.base/'recovery',lambda db,intent:True,contextlib.nullcontext,
                           output_policy=lambda:(str(self.sorted),(str(self.library),)))
    def restart(self):
        self.worker.close();self.worker=self.start()
    def tearDown(self):
        try:self.worker.close()
        finally:
            try:self.stack.close()
            finally:self.temp.cleanup()
    def members(self):
        with connect(self.db) as db:return {r['path']:dict(r) for r in db.execute('SELECT path,state,removal_method FROM cleanup_members WHERE cleanup_id=?',(self.id,))}
    def latest_cause(self):
        with connect(self.db) as db:
            row=db.execute('SELECT cause FROM source_cleanup_holds WHERE cleanup_id=? ORDER BY at DESC LIMIT 1',(self.id,)).fetchone()
        return json.loads(row['cause'])
    def assert_originals_kept(self):
        for s in self.sources:
            p=Path(s['path']);self.assertTrue(p.is_file(),s['path'])
        self.assertEqual(self.worker.status('test')['removed'],0)
    def hold_as_before_the_ruling(self,provider=remote_refusal):
        """The 0.28.x outcome: the provider refuses the NAS original and dispose() is offered no NAS method. 0.28.x had
        no intent withdrawal either, so its catalog keeps the refused member in removal_intended (what Sergei's has)."""
        real=VerifiedFile.dispose
        def pre_ruling(handle,**options):return real(handle)
        with patch.object(runtime,'_local_provider',provider),patch.object(VerifiedFile,'dispose',pre_ruling),\
             patch.object(CleanupJobs,'_withdraw_intent',lambda *args:False,create=True):
            self.worker._work(follow_audio=False)
    def restore_order(self):
        """The order Restore reaches this cleanup's members in (the catalog's own order, not the manifest's)."""
        with connect(self.db) as db:return [r['path'] for r in db.execute('SELECT path FROM cleanup_members WHERE cleanup_id=?',(self.id,))]


@unittest.skipUnless(os.name=='nt','Native Windows disposition')
class NasSourceCleanupTests(CleanupFixture,unittest.TestCase):
    def test_nas_original_removed_by_legacy_method_and_recorded(self):
        with nas_volume():self.worker.run(self.id)
        status=self.worker.status('test');self.assertEqual(status['state'],'completed');self.assertEqual(status['removed'],2)
        self.assertTrue(all(not Path(s['path']).exists() for s in self.sources))
        self.assertEqual({m['removal_method'] for m in self.members().values()},{'nas_legacy'})
        self.assertEqual(list(self.context.control_root.glob('*.intent.json')),[],'the hardened journal took no part')
        self.assertEqual(len(list((self.base/'recovery'/self.id).glob('*.mp3'))),2,'recovery copies untouched by the removal itself')

    def test_nas_hash_mismatch_right_before_removal_keeps_every_original(self):
        # The accepted NAS race, caught when it happens before the last re-hash: bytes change after the copies.
        changed={'now':False};real_hash=VerifiedFile.sha256;paths={s['path'] for s in self.sources}
        def proof(handle,path):changed['now']=True;return True
        def hashed(handle):return '0'*64 if changed['now'] and str(handle.path) in paths else real_hash(handle)
        with nas_volume(proof),patch.object(VerifiedFile,'sha256',hashed):self.worker._work(follow_audio=False)
        status=self.worker.status('test');self.assertEqual(status['state'],'needs_attention')
        self.assertEqual(status['reason'],'Original bytes differ from reviewed sources')
        self.assertTrue(changed['now'],'positive control: the NAS method was reached')
        self.assert_originals_kept()
        for s in self.sources:self.assertEqual(hashlib.sha256(Path(s['path']).read_bytes()).hexdigest(),s['sha256'])
        self.assertEqual({m['removal_method'] for m in self.members().values()},{''})
        # Senua M1, P1: nothing was removed, so no member reads as an intended removal and Restore has nothing to refuse.
        self.assertEqual({m['state'] for m in self.members().values()},{'backup_verified'})
        self.worker.restore(self.id);self.assertEqual(self.worker.status('test')['reason'],RESTORED)
        for s in self.sources:self.assertEqual(hashlib.sha256(Path(s['path']).read_bytes()).hexdigest(),s['sha256'])

    def test_nas_removal_waits_for_a_present_recovery_copy(self):
        real_refresh=VerifiedFile.refresh
        def refreshed(handle):
            facts=real_refresh(handle)
            return dict(facts,links=0) if Path(handle.path).parent==self.base/'recovery'/self.id else facts
        with nas_volume(),patch.object(VerifiedFile,'refresh',refreshed):self.worker._work(follow_audio=False)
        self.assertEqual(self.worker.status('test')['reason'],'Recovery copy is not in place; originals retained')
        self.assert_originals_kept()

    def test_local_cleanup_still_uses_the_hardened_provider(self):
        with patch.object(native_io,'remote_handle',side_effect=AssertionError('a local volume never reaches the NAS method')):
            self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['state'],'completed')
        self.assertEqual({m['removal_method'] for m in self.members().values()},{'hardened_local'})
        self.assertEqual(len(list(self.context.control_root.glob('*.closed.json'))),2,'hardened journal proves each closed removal')

    def test_held_remote_cleanup_retries_at_startup_and_completes(self):
        self.hold_as_before_the_ruling()
        status=self.worker.status('test');self.assertEqual(status['state'],'needs_attention');self.assertEqual(status['reason'],RETAINED_HOLD)
        cause=self.latest_cause();self.assertEqual(cause['kind'],'originals_positively_retained');self.assertEqual(cause['diagnostic'],runtime.REMOTE_PROVIDER_REFUSAL)
        self.assertEqual(sorted(m['state'] for m in self.members().values()),['backup_verified','removal_intended'],'the 0.28.x leftover shape')
        self.assert_originals_kept()
        self.worker._work(follow_audio=False)
        self.assertEqual(self.worker.status('test')['state'],'needs_attention','not retried without the startup step')
        self.restart()
        self.assertEqual(self.worker.status('test')['state'],'paused')
        with nas_volume():self.worker._work(follow_audio=False)
        status=self.worker.status('test');self.assertEqual(status['state'],'completed');self.assertEqual(status['removed'],2)
        self.assertTrue(all(not Path(s['path']).exists() for s in self.sources))
        self.assertEqual({m['removal_method'] for m in self.members().values()},{'nas_legacy'})

    def test_held_remote_retry_with_changed_bytes_stays_held(self):
        self.hold_as_before_the_ruling()
        changed=Path(self.sources[1]['path']);changed.write_bytes(b'Z'*2048);os.utime(changed,ns=(int(self.sources[1]['modified']),)*2)
        self.restart();self.assertEqual(self.worker.status('test')['state'],'paused')
        with nas_volume():self.worker._work(follow_audio=False)
        status=self.worker.status('test');self.assertEqual(status['state'],'needs_attention')
        self.assertEqual(status['reason'],'Original bytes differ from reviewed sources')
        self.assert_originals_kept();self.assertEqual(changed.read_bytes(),b'Z'*2048)
        self.restart();self.assertEqual(self.worker.status('test')['state'],'needs_attention','a changed-bytes hold is never retried automatically')

    def test_other_provider_holds_are_not_retried(self):
        def not_ntfs(handle):raise RelocationRefused('Unsupported disposition provider: verified local NTFS required')
        self.hold_as_before_the_ruling(not_ntfs)
        self.assertEqual(self.worker.status('test')['reason'],RETAINED_HOLD)
        self.restart();self.assertEqual(self.worker.status('test')['state'],'needs_attention')
        self.assert_originals_kept()

    def test_owner_location_refusal_is_held_with_its_own_reason_and_never_revived(self):
        # Senua m3: a remote journal/owner location gives the same provider refusal text; it is not the file's own.
        refusal=runtime.RemoteProviderRefused(runtime.REMOTE_PROVIDER_REFUSAL)
        with nas_volume(),patch.object(runtime_disposition_owners,'context_for',side_effect=refusal):
            self.worker._work(follow_audio=False)
        self.assertEqual(self.worker.status('test')['reason'],RETAINED_HOLD)
        diagnostic=self.latest_cause()['diagnostic']
        self.assertTrue(diagnostic.startswith(native_io.OWNER_LOCATION_REFUSAL),diagnostic)
        self.assertNotEqual(diagnostic,runtime.REMOTE_PROVIDER_REFUSAL)
        self.assert_originals_kept()
        self.restart();self.assertEqual(self.worker.status('test')['state'],'needs_attention','never revived at app start')


@unittest.skipUnless(os.name=='nt','Native Windows disposition')
class PartialFailureRestoreTests(CleanupFixture,unittest.TestCase):
    """Senua M1 / P5. Manifest order 1.mp3, 0.mp3: 1.mp3 is removed first, then a check fails for 0.mp3, the first
    member Restore reaches (the catalog returns members in path order). Restore must bring 1.mp3 back and leave the
    original 0.mp3, which was never removed, as it is."""
    def arrange(self,sources):return list(reversed(sources))
    def setUp(self):
        super().setUp()
        self.removed,self.failing=self.sources
    def is_failing(self,path):return Path(str(path)).name==Path(self.failing['path']).name
    @contextlib.contextmanager
    def nas_failing(self,armed=None):
        """NAS volume; `armed` is set the moment the NAS method is about to check the failing track."""
        armed=armed if armed is not None else {}
        def proof(handle,path):
            if self.is_failing(path):armed['now']=True;armed['handle']=handle
            return True
        with nas_volume(proof):yield armed
    def assert_held_with_one_removed(self,reason,method='nas_legacy',failing_state='backup_verified'):
        status=self.worker.status('test');self.assertEqual(status['state'],'needs_attention');self.assertEqual(status['reason'],reason)
        self.assertEqual(status['removed'],1)
        members=self.members()
        self.assertEqual((members[self.removed['path']]['state'],members[self.removed['path']]['removal_method']),('removed',method))
        self.assertEqual((members[self.failing['path']]['state'],members[self.failing['path']]['removal_method']),(failing_state,''),
                         'the failing original was never removed, and its state says so (or, once the NAS delete call was issued, stays an intended removal)')
        self.assertFalse(Path(self.removed['path']).exists());self.assertTrue(Path(self.failing['path']).is_file())
        self.assertEqual(self.restore_order(),[self.failing['path'],self.removed['path']],'positive control (P5): the failing track is reached first')
    def assert_restore_brings_back_every_removed_track(self,failing_bytes=None):
        self.worker.restore(self.id)
        self.assertEqual(self.worker.status('test')['reason'],RESTORED)
        self.assertEqual(hashlib.sha256(Path(self.removed['path']).read_bytes()).hexdigest(),self.removed['sha256'],'the removed track is back')
        current=hashlib.sha256(Path(self.failing['path']).read_bytes()).hexdigest()
        self.assertEqual(current,failing_bytes or self.failing['sha256'],'the never-removed original is left as it is')
        members=self.members()
        self.assertEqual(members[self.removed['path']]['state'],'restored');self.assertEqual(members[self.failing['path']]['state'],'backup_verified')

    def test_p5_hash_mismatch_after_a_removed_track_then_restore(self):
        real_hash=VerifiedFile.sha256
        with self.nas_failing() as armed:
            def hashed(handle):return '0'*64 if armed.get('now') and self.is_failing(handle.path) else real_hash(handle)
            with patch.object(VerifiedFile,'sha256',hashed):self.worker._work(follow_audio=False)
        self.assertTrue(armed.get('now'),'positive control: the NAS check of the failing track ran')
        self.assert_held_with_one_removed('Original bytes differ from reviewed sources')
        self.assert_restore_brings_back_every_removed_track()

    def test_smb_read_error_during_the_re_hash_then_restore(self):
        real_hash=VerifiedFile.sha256
        with self.nas_failing() as armed:
            def hashed(handle):
                if armed.get('now') and self.is_failing(handle.path):raise BoundaryError('Protected file read failed')
                return real_hash(handle)
            with patch.object(VerifiedFile,'sha256',hashed):self.worker._work(follow_audio=False)
        self.assertTrue(armed.get('now'))
        self.assert_held_with_one_removed('Protected file read failed')
        self.assert_restore_brings_back_every_removed_track()

    def test_recovery_copy_check_failure_then_restore(self):
        real_refresh=VerifiedFile.refresh;recovery=self.base/'recovery'/self.id
        with self.nas_failing() as armed:
            def refreshed(handle):
                facts=real_refresh(handle)
                # The failing track's recovery copy is the second one made (manifest index 1).
                return dict(facts,links=0) if armed.get('now') and Path(handle.path)==recovery/'00001.mp3' else facts
            with patch.object(VerifiedFile,'refresh',refreshed):self.worker._work(follow_audio=False)
        self.assertTrue(armed.get('now'))
        self.assert_held_with_one_removed('Recovery copy is not in place; originals retained')
        self.assert_restore_brings_back_every_removed_track()

    def test_denied_delete_then_restore(self):
        handles=set()
        with self.nas_failing() as armed:
            def proof_handles():
                if armed.get('handle'):handles.add(armed['handle'])
            denied=DeniedDelete(native_io.kernel,handles)
            real_verify=CleanupJobs._nas_checks
            def checks(handle,source,facts,backup):
                real_verify(handle,source,facts,backup);proof_handles()  # deny only after every check passed
            with patch.object(native_io,'kernel',denied),patch.object(CleanupJobs,'_nas_checks',staticmethod(checks)):
                self.worker._work(follow_audio=False)
        self.assertEqual(len(denied.denied),1,'positive control: the delete call itself was denied, once')
        reason=self.worker.status('test')['reason']
        self.assertIn('Exact-handle removal is unsupported or denied',reason)
        # Senua m9: the NAS delete call was issued, so the member is never withdrawn; Restore's own check finds the
        # original never removed and leaves it as it is.
        self.assert_held_with_one_removed(reason,failing_state='removal_intended')
        self.assert_restore_brings_back_every_removed_track()

    def test_nas_delete_set_but_reported_failed_is_never_withdrawn(self):
        # Senua m9 / P6: the delete is applied but its answer is lost (WinError 64), and the SMB client answers the
        # withdraw checks from its cache (one link, no pending delete). Once the delete call was issued, never withdrawn.
        with self.nas_failing() as armed:
            lost=LostReply(native_io.kernel,lambda handle:handle==armed.get('handle'))
            with patch.object(native_io,'kernel',lost),stale_withdraw_answers(self.is_failing,pending_too=True) as seen:
                self.worker._work(follow_audio=False)
        self.assertEqual(len(lost.lost),1,'positive control: the delete was really set on the failing track, then reported failed')
        self.assertEqual(seen,[{'same_identity':True,'links':1,'pending':False,'name_present':True,'withdrawn':False}],
                         'positive control: every cached answer would pass; still not withdrawn')
        self.assertIn('Exact-handle removal is unsupported or denied',self.worker.status('test')['reason'])
        self.assertEqual(self.members()[self.failing['path']]['state'],'removal_intended')
        self.assertFalse(Path(self.failing['path']).exists(),'the delete that was really set removed the original at close')
        self.worker.restore(self.id)
        self.assertEqual(self.worker.status('test')['reason'],RESTORED)
        for s in self.sources:self.assertEqual(hashlib.sha256(Path(s['path']).read_bytes()).hexdigest(),s['sha256'],'both tracks are back')
        self.assertEqual({m['state'] for m in self.members().values()},{'restored'})

    def test_hardened_delete_set_but_reported_failed_is_caught_by_the_pending_delete_check(self):
        # Senua m10: the local hardened path, delete applied but reported failed, and the link count answers one (as a
        # cache would). Only the pending-delete check (FileStandardInfo.DeletePending) still sees the delete.
        lost=LostReply(native_io.kernel,lambda handle:final_name(handle)==Path(self.failing['path']).name)
        with patch.object(native_io,'kernel',lost),stale_withdraw_answers(self.is_failing,pending_too=False) as seen,\
             patch.object(native_io,'remote_handle',side_effect=AssertionError('a local volume never reaches the NAS method')):
            self.worker._work(follow_audio=False)
        self.assertEqual(len(lost.lost),1,'positive control: the delete was really set on the failing track, then reported failed')
        self.assertEqual(seen,[{'same_identity':True,'links':1,'pending':True,'name_present':True,'withdrawn':False}],
                         'positive control: identity, link count and name all pass; only the pending delete refuses')
        self.assertEqual(self.worker.status('test')['state'],'needs_attention')
        self.assertEqual(self.members()[self.failing['path']]['state'],'removal_intended')
        self.assertFalse(Path(self.failing['path']).exists(),'the delete that was really set removed the original at close')
        self.worker.restore(self.id)
        self.assertEqual(self.worker.status('test')['reason'],RESTORED)
        for s in self.sources:self.assertEqual(hashlib.sha256(Path(s['path']).read_bytes()).hexdigest(),s['sha256'],'both tracks are back')

    def test_failed_remote_proof_then_restore(self):
        def proof(handle,path):return not self.is_failing(path)
        with nas_volume(proof):self.worker._work(follow_audio=False)
        self.assertIn('not a verified network volume',self.latest_cause()['diagnostic'])
        self.assert_held_with_one_removed(RETAINED_HOLD)
        self.assertEqual(self.worker.status('test')['status'],'Held — some originals remain')
        self.assert_restore_brings_back_every_removed_track()

    def test_hardened_local_refusal_has_the_same_fix(self):
        # The same leftover came from hardened-local refusals since 0.28.0; the same withdrawal covers it.
        real=runtime._local_provider
        def provider(handle):
            if final_name(handle)==Path(self.failing['path']).name:raise RelocationRefused('Unsupported disposition provider: verified local NTFS required')
            return real(handle)
        with patch.object(runtime,'_local_provider',provider),\
             patch.object(native_io,'remote_handle',side_effect=AssertionError('a local volume never reaches the NAS method')):
            self.worker._work(follow_audio=False)
        self.assertEqual(self.latest_cause()['diagnostic'],'Unsupported disposition provider: verified local NTFS required')
        self.assert_held_with_one_removed(RETAINED_HOLD,method='hardened_local')
        self.assert_restore_brings_back_every_removed_track()

    def test_unprovable_withdrawal_still_restores_through_the_restore_check(self):
        # The held handle cannot prove the state (e.g. the SMB session dropped): removal_intended stays, and Restore's
        # own read-only check (stored identity, size, time, reviewed hash) finds the original never removed.
        real_hash=VerifiedFile.sha256
        with self.nas_failing() as armed:
            def hashed(handle):return '0'*64 if armed.get('now') and self.is_failing(handle.path) else real_hash(handle)
            with patch.object(VerifiedFile,'sha256',hashed),\
                 patch.object(VerifiedFile,'delete_pending',side_effect=BoundaryError('Cannot read the pending-removal state of the exact file'),create=True):
                self.worker._work(follow_audio=False)
        self.assertEqual(self.members()[self.failing['path']]['state'],'removal_intended','positive control: not withdrawn')
        self.assertEqual(self.restore_order(),[self.failing['path'],self.removed['path']],'positive control (P5): the failing track is reached first')
        self.assert_restore_brings_back_every_removed_track()

    def test_restore_still_preserves_a_changed_file_it_cannot_prove(self):
        real_hash=VerifiedFile.sha256
        with self.nas_failing() as armed:
            def hashed(handle):return '0'*64 if armed.get('now') and self.is_failing(handle.path) else real_hash(handle)
            with patch.object(VerifiedFile,'sha256',hashed),\
                 patch.object(VerifiedFile,'delete_pending',side_effect=BoundaryError('Cannot read the pending-removal state of the exact file'),create=True):
                self.worker._work(follow_audio=False)
        self.assertEqual(self.members()[self.failing['path']]['state'],'removal_intended')
        changed=Path(self.failing['path']);changed.write_bytes(b'Z'*2048);os.utime(changed,ns=(int(self.failing['modified']),)*2)
        with self.assertRaisesRegex(FileExistsError,'Restore collision; existing file preserved'):self.worker.restore(self.id)
        self.assertEqual(changed.read_bytes(),b'Z'*2048,'a file Restore cannot prove is the original is never replaced')


@unittest.skipUnless(os.name=='nt','Native Windows disposition')
class LoopbackSmbSourceCleanupTests(CleanupFixture,unittest.TestCase):
    """Real SMB handles, the provider's real refusal and real positive remote proof (the Z: shape). The share is this
    PC's own, so the only simulated fact is 'another machine': smb_from_another_machine() clears the loopback bit."""
    def view(self,path):
        remote=loopback(path)
        if remote is None:self.skipTest('Loopback administrative share is unavailable')
        return remote
    def assert_real_loopback(self,seen):
        self.assertTrue(seen,'positive control: real remote-protocol answers were read')
        self.assertTrue(all(p==native_io.WNNC_NET_SMB and f&native_io.REMOTE_PROTOCOL_FLAG_LOOPBACK for p,f in seen),seen)
    def test_held_smb_cleanup_retries_at_startup_and_completes_by_the_nas_method(self):
        real=VerifiedFile.dispose
        def pre_ruling(handle,**options):return real(handle)
        with patch.object(VerifiedFile,'dispose',pre_ruling):self.worker._work(follow_audio=False)
        self.assertEqual(self.worker.status('test')['reason'],RETAINED_HOLD)
        self.assertEqual(self.latest_cause()['diagnostic'],runtime.REMOTE_PROVIDER_REFUSAL,'the real provider refusal of an SMB original')
        self.assert_originals_kept()
        self.assertEqual({m['state'] for m in self.members().values()},{'backup_verified'},'Senua M1: withdrawn through a real SMB handle')
        self.restart();self.assertEqual(self.worker.status('test')['state'],'paused')
        with smb_from_another_machine() as seen:self.worker._work(follow_audio=False)
        self.assert_real_loopback(seen)
        status=self.worker.status('test');self.assertEqual(status['state'],'completed');self.assertEqual(status['removed'],2)
        self.assertTrue(all(not (self.base/'library'/Path(s['path']).name).exists() for s in self.sources))
        self.assertEqual({m['removal_method'] for m in self.members().values()},{'nas_legacy'})

    def test_loopback_smb_original_is_never_given_the_nas_method(self):
        # Senua m1: an SMB connection back to this PC reaches a local disk; it is held, not removed, and not revived.
        real=VerifiedFile.dispose
        def pre_ruling(handle,**options):return real(handle)
        with patch.object(VerifiedFile,'dispose',pre_ruling):self.worker._work(follow_audio=False)
        self.restart();self.assertEqual(self.worker.status('test')['state'],'paused')
        self.worker._work(follow_audio=False)
        self.assertEqual(self.worker.status('test')['reason'],RETAINED_HOLD)
        self.assertIn('not a verified network volume',self.latest_cause()['diagnostic'])
        self.assert_originals_kept()
        self.assertEqual({m['state'] for m in self.members().values()},{'backup_verified'})
        self.restart();self.assertEqual(self.worker.status('test')['state'],'needs_attention','held for its own reason, never revived')

    def p2_over_smb(self):
        """Senua M1 / P2 over real SMB: 0.mp3 is removed by the NAS method, then 1.mp3 fails its re-hash and is withdrawn
        through the real SMB handle. Returns (removed, failing)."""
        removed,failing=self.sources;armed={};real_hash=VerifiedFile.sha256
        real_proof=native_io.remote_handle
        def proof(handle,path):
            if Path(str(path)).name==Path(failing['path']).name:armed['now']=True
            return real_proof(handle,path)
        def hashed(handle):return '0'*64 if armed.get('now') and Path(str(handle.path)).name==Path(failing['path']).name else real_hash(handle)
        with smb_from_another_machine() as seen,patch.object(native_io,'remote_handle',side_effect=proof),patch.object(VerifiedFile,'sha256',hashed):
            self.worker._work(follow_audio=False)
        self.assert_real_loopback(seen);self.assertTrue(armed.get('now'))
        self.assertEqual(self.worker.status('test')['removed'],1)
        self.assertEqual(self.members()[failing['path']]['state'],'backup_verified')
        return removed,failing

    def test_restore_over_smb_brings_the_removed_track_back(self):
        # Senua M2: Restore over a real SMB handle. Before the fix every attempt failed with WinError 32 and left a .partial.
        removed,failing=self.p2_over_smb();local=self.base/'library'
        self.assertFalse((local/Path(removed['path']).name).exists())
        held=[];real=source_cleanup.DirectoryBoundary
        def boundary(root,parent,*args,**options):
            held.append((Path(str(parent)),options.get('rename_destination',False)));return real(root,parent,*args,**options)
        with patch.object(source_cleanup,'DirectoryBoundary',side_effect=boundary):self.worker.restore(self.id)
        self.assertEqual(self.worker.status('test')['reason'],RESTORED)
        self.assertEqual(hashlib.sha256((local/Path(removed['path']).name).read_bytes()).hexdigest(),removed['sha256'],'the removed track is back')
        self.assertEqual(hashlib.sha256((local/Path(failing['path']).name).read_bytes()).hexdigest(),failing['sha256'],'the kept original is as it was')
        members=self.members()
        self.assertEqual((members[removed['path']]['state'],members[failing['path']]['state']),('restored','backup_verified'))
        self.assertEqual(restore_temporaries(local),[],'no temporary left in the library folder')
        self.assertIn((self.library,True),held,'the SMB library folder is held sharing WRITE for the rename')

    def test_smb_restore_never_overwrites_and_removes_its_own_temporary(self):
        # Senua M2: a file that arrives at the original's name during Restore wins; the rename refuses (no-replace) and
        # this Restore removes its own .partial (NAS method, after proving it is the exact file it created).
        removed,_=self.p2_over_smb();local=self.base/'library';arrival=local/Path(removed['path']).name
        real=source_cleanup.publish_no_replace
        def racing(temporary,destination,*args):
            arrival.write_bytes(b'arrived during Restore');return real(temporary,destination,*args)
        with smb_from_another_machine() as seen,patch.object(source_cleanup,'publish_no_replace',side_effect=racing):
            with self.assertRaises(FileExistsError) as caught:self.worker.restore(self.id)
        self.assertIn(getattr(caught.exception,'rename_status',None),{80,183},'positive control: the rename call itself refused the collision')
        self.assert_real_loopback(seen)
        self.assertEqual(arrival.read_bytes(),b'arrived during Restore','never overwritten')
        self.assertEqual(restore_temporaries(local),[],'the failed Restore removed its own temporary')
        self.assertEqual(self.members()[removed['path']]['state'],'restore_intended')

    def test_p2_partial_failure_over_smb_withdraws_through_the_real_handle(self):
        # Senua M1 / P2 over real SMB: 0.mp3 is removed by the NAS method, then 1.mp3 fails its re-hash. The member is
        # withdrawn through the real SMB handle (pending-delete state read over SMB). Restore over SMB: the tests above.
        removed,failing=self.sources;armed={};real_hash=VerifiedFile.sha256
        real_proof=native_io.remote_handle
        def proof(handle,path):
            if Path(str(path)).name==Path(failing['path']).name:armed['now']=True
            return real_proof(handle,path)
        def hashed(handle):return '0'*64 if armed.get('now') and Path(str(handle.path)).name==Path(failing['path']).name else real_hash(handle)
        with smb_from_another_machine() as seen,patch.object(native_io,'remote_handle',side_effect=proof),patch.object(VerifiedFile,'sha256',hashed):
            self.worker._work(follow_audio=False)
        self.assert_real_loopback(seen);self.assertTrue(armed.get('now'))
        status=self.worker.status('test');self.assertEqual(status['reason'],'Original bytes differ from reviewed sources');self.assertEqual(status['removed'],1)
        members=self.members()
        self.assertEqual((members[removed['path']]['state'],members[removed['path']]['removal_method']),('removed','nas_legacy'))
        self.assertEqual(members[failing['path']]['state'],'backup_verified')
        self.assertFalse(Path(removed['path']).exists())
        self.assertEqual(hashlib.sha256(Path(failing['path']).read_bytes()).hexdigest(),failing['sha256'])


@unittest.skipUnless(os.name=='nt','Native Windows disposition')
class LocalRestoreTemporaryTests(CleanupFixture,unittest.TestCase):
    """Senua M2 on a local volume: Restore is held and published exactly as before, and a failed Restore removes its
    own .partial only when the rename provably did not happen, and only that exact file."""
    def setUp(self):
        super().setUp()
        self.worker.run(self.id)
        self.assertEqual(self.worker.status('test')['removed'],2,'positive control: both originals removed (hardened local)')
        self.first=min(self.sources,key=lambda s:s['path'])  # the member Restore reaches first
    def publishing(self,before):
        """publish_no_replace that first runs before(temporary, destination)."""
        real=source_cleanup.publish_no_replace
        def publish(temporary,destination,*args):
            before(Path(str(temporary)),Path(str(destination)));return real(temporary,destination,*args)
        return patch.object(source_cleanup,'publish_no_replace',side_effect=publish)

    def test_local_restore_holds_the_library_folder_as_before(self):
        held=[];real=source_cleanup.DirectoryBoundary
        def boundary(root,parent,*args,**options):
            held.append((Path(str(parent)),options.get('rename_destination',False)));return real(root,parent,*args,**options)
        drive_type=native_io.kernel.GetDriveTypeW;drive_type.argtypes=[wintypes.LPCWSTR];drive_type.restype=wintypes.UINT
        self.assertNotEqual(drive_type(self.library.anchor),4,'positive control: a local fixture drive, not DRIVE_REMOTE')
        with patch.object(source_cleanup,'DirectoryBoundary',side_effect=boundary):self.worker.restore(self.id)
        self.assertEqual(self.worker.status('test')['reason'],RESTORED)
        for s in self.sources:self.assertEqual(hashlib.sha256(Path(s['path']).read_bytes()).hexdigest(),s['sha256'])
        self.assertEqual([h for h in held if h[0]==self.library],[(self.library,False)]*2,'local library folder held without WRITE sharing, as before')
        self.assertEqual(restore_temporaries(self.library),[])

    def test_local_collision_at_the_rename_keeps_the_arrival_and_removes_the_temporary(self):
        arrival=Path(self.first['path'])
        def arrive(temporary,destination):
            if destination==arrival:arrival.write_bytes(b'arrived during Restore')
        with self.publishing(arrive),self.assertRaises(FileExistsError) as caught:self.worker.restore(self.id)
        self.assertIn(getattr(caught.exception,'rename_status',None),{80,183},'positive control: the rename call itself refused')
        self.assertEqual(arrival.read_bytes(),b'arrived during Restore','never overwritten')
        self.assertEqual(restore_temporaries(self.library),[],'the failed Restore removed its own temporary')
        self.assertEqual(self.members()[self.first['path']]['state'],'restore_intended')
        with self.assertRaisesRegex(FileExistsError,'unrelated replacement preserved'):self.worker.restore(self.id)
        self.assertEqual(arrival.read_bytes(),b'arrived during Restore')

    def test_failure_before_the_rename_removes_the_temporary(self):
        real=VerifiedFile.restore_metadata;failed=[]
        def metadata(handle,modified,attributes):
            if Path(handle.path).name.startswith('.books-restore-'):failed.append(handle.path);raise BoundaryError('Cannot preserve recovery timestamps/attributes')
            return real(handle,modified,attributes)
        with patch.object(VerifiedFile,'restore_metadata',metadata),self.assertRaisesRegex(BoundaryError,'timestamps'):self.worker.restore(self.id)
        self.assertEqual(len(failed),1,'positive control: the temporary was made, then failed')
        self.assertEqual(restore_temporaries(self.library),[])
        self.assertEqual(self.members()[self.first['path']]['state'],'removed','nothing was intended yet')
        self.worker.restore(self.id);self.assertEqual(self.worker.status('test')['reason'],RESTORED)
        self.assertEqual(restore_temporaries(self.library),[])

    def test_unknown_rename_outcome_keeps_the_temporary_until_the_next_restore(self):
        # v0.24.0 D1r4: after a network error the rename may have happened, so that attempt keeps its temporary. The
        # next Restore finds the original's name still free and the temporary still the same file, and removes it.
        def lost_reply(temporary,destination,boundary,sha256,size,before):
            with VerifiedFile(temporary) as made:identity=made.facts()['identity']
            before({'identity':identity,'sha256':sha256,'size':size})
            error=BoundaryError('Handle-bound no-replace publication failed: [WinError 64] The specified network name is no longer available.')
            error.rename_status=64;raise error
        with patch.object(source_cleanup,'publish_no_replace',side_effect=lost_reply),self.assertRaisesRegex(BoundaryError,'WinError 64'):
            self.worker.restore(self.id)
        kept=restore_temporaries(self.library)
        self.assertEqual(len(kept),1,'an unknown outcome keeps the temporary')
        self.assertEqual(self.members()[self.first['path']]['state'],'restore_intended')
        self.worker.restore(self.id);self.assertEqual(self.worker.status('test')['reason'],RESTORED)
        for s in self.sources:self.assertEqual(hashlib.sha256(Path(s['path']).read_bytes()).hexdigest(),s['sha256'])
        self.assertEqual(restore_temporaries(self.library),[],'the next Restore removed it')

    def test_a_temporary_that_is_no_longer_the_file_restore_made_is_kept(self):
        swapped={}
        def swap(temporary,destination):
            temporary.unlink();temporary.write_bytes(b'not the file Restore made');swapped['path']=temporary
            error=BoundaryError('Handle-bound no-replace publication failed: [WinError 32]');error.rename_status=32;raise error
        with self.publishing(swap),self.assertRaisesRegex(BoundaryError,'WinError 32'):self.worker.restore(self.id)
        self.assertEqual(swapped['path'].read_bytes(),b'not the file Restore made','cleanup removes only the exact file Restore made')
        swapped['path'].unlink()


@unittest.skipUnless(os.name=='nt','Native Windows disposition')
class NasDisposeTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='nas-dispose-',dir=SCRATCH)
        self.base=Path(self.temp.name);self.area=self.base/'area';self.area.mkdir()
        self.stack=contextlib.ExitStack()
    def tearDown(self):
        try:self.stack.close()
        finally:self.temp.cleanup()
    def owned(self,name):
        path=self.area/name;path.write_bytes(b'owned bytes '+name.encode());return path

    def test_unverifiable_local_volume_is_never_given_the_nas_method(self):
        self.stack.enter_context(support_dispositions(self.base,[self.area]))
        path=self.owned('local.bin');called=[]
        with patch.object(runtime,'_local_provider',remote_refusal):
            with VerifiedFile(path,delete=True) as held:
                with self.assertRaises(FileRemovalRetained) as caught:held.dispose(remote_legacy=called.append)
                self.assertFalse(hasattr(held,'disposition_method'))
        self.assertIn('not a verified network volume',caught.exception.native_reason)
        self.assertEqual(called,[]);self.assertTrue(path.is_file())

    def test_without_the_nas_option_a_remote_refusal_keeps_the_file_as_before(self):
        self.stack.enter_context(support_dispositions(self.base,[self.area]))
        path=self.owned('other-caller.bin')
        with nas_volume():
            with VerifiedFile(path,delete=True) as held:
                with self.assertRaises(FileRemovalRetained) as caught:held.dispose()
        self.assertEqual(caught.exception.native_reason,runtime.REMOTE_PROVIDER_REFUSAL);self.assertTrue(path.is_file())

    def test_real_loopback_smb_handle_takes_the_nas_method(self):
        remote_area=loopback(self.area)
        if remote_area is None:self.skipTest('Loopback administrative share is unavailable')
        self.stack.enter_context(support_dispositions(self.base,[remote_area]))
        removed=self.owned('removed.bin');kept=self.owned('kept.bin');plain=self.owned('plain.bin')
        expected=hashlib.sha256(removed.read_bytes()).hexdigest();checked=[]
        def checks(handle):checked.append(handle.sha256())
        with smb_from_another_machine() as seen:
            with VerifiedFile(remote_area/'removed.bin',delete=True) as held:
                held.dispose(remote_legacy=checks);self.assertEqual(held.disposition_method,'nas_legacy')
            self.assertEqual(checked,[expected]);self.assertFalse(removed.exists())
            def refuse(handle):raise BoundaryError('Original bytes differ from reviewed sources')
            with VerifiedFile(remote_area/'kept.bin',delete=True) as held:
                with self.assertRaisesRegex(BoundaryError,'differ from reviewed'):held.dispose(remote_legacy=refuse)
                self.assertFalse(held.delete_pending(),'a refused check sets no delete')
            self.assertTrue(kept.is_file())
        self.assertTrue(seen and all(f&native_io.REMOTE_PROTOCOL_FLAG_LOOPBACK for _,f in seen),'real loopback handles')
        with VerifiedFile(remote_area/'plain.bin',delete=True) as held:
            with self.assertRaises(FileRemovalRetained) as caught:held.dispose()
        self.assertEqual(caught.exception.native_reason,runtime.REMOTE_PROVIDER_REFUSAL,'the actual provider refusal for an SMB handle')
        self.assertTrue(plain.is_file())

    def test_real_loopback_smb_handle_is_not_a_network_volume(self):
        # Senua m1: SMB back to this PC reaches a local disk, so the NAS method is never offered for it.
        remote_area=loopback(self.area)
        if remote_area is None:self.skipTest('Loopback administrative share is unavailable')
        self.stack.enter_context(support_dispositions(self.base,[remote_area]))
        path=self.owned('loopback.bin');called=[]
        with VerifiedFile(remote_area/'loopback.bin',delete=True) as held:
            protocol,flags=native_io.remote_protocol(held.handle)
            self.assertEqual(protocol,native_io.WNNC_NET_SMB,'positive control: a real SMB handle');self.assertTrue(flags&native_io.REMOTE_PROTOCOL_FLAG_LOOPBACK)
            self.assertFalse(native_io.remote_handle(held.handle,held.path))
            with self.assertRaises(FileRemovalRetained) as caught:held.dispose(remote_legacy=called.append)
        self.assertIn('not a verified network volume',caught.exception.native_reason)
        self.assertEqual(called,[]);self.assertTrue(path.is_file())

    def test_only_an_smb_protocol_handle_counts_as_a_network_volume(self):
        # Senua m1: same real remote handle and DRIVE_REMOTE path; only the reported protocol/flags differ.
        remote_area=loopback(self.area)
        if remote_area is None:self.skipTest('Loopback administrative share is unavailable')
        self.owned('protocol.bin')
        with VerifiedFile(remote_area/'protocol.bin') as held:
            def judged(answer):
                with patch.object(native_io,'remote_protocol',return_value=answer):return native_io.remote_handle(held.handle,held.path)
            self.assertTrue(judged((native_io.WNNC_NET_SMB,0x30)),'positive control: SMB to another machine')
            self.assertFalse(judged((WNNC_NET_DAV,0x30)),'another redirector')
            self.assertFalse(judged((native_io.WNNC_NET_SMB,0x31)),'SMB loopback')
            self.assertFalse(judged(None),'not a redirected handle')

    def test_delete_pending_reads_the_exact_handle(self):
        path=self.owned('pending.bin')
        def disposition(held,value):
            flag=wintypes.BOOL(value)
            native_io.kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
            native_io.kernel.SetFileInformationByHandle.restype=wintypes.BOOL
            self.assertTrue(native_io.kernel.SetFileInformationByHandle(held.handle,4,ctypes.byref(flag),ctypes.sizeof(flag)))
        with VerifiedFile(path,delete=True) as held:
            self.assertFalse(held.delete_pending())
            disposition(held,True);self.assertTrue(held.delete_pending(),'positive control: a set delete is seen')
            disposition(held,False);self.assertFalse(held.delete_pending())
        self.assertTrue(path.is_file())

    def test_owner_location_refusal_never_offers_the_nas_method(self):
        # Senua m3: the journal/owner location refused as remote keeps the file with a distinct reason.
        path=self.owned('owner.bin');called=[]
        with nas_volume(),patch.object(runtime_disposition_owners,'context_for',side_effect=runtime.RemoteProviderRefused(runtime.REMOTE_PROVIDER_REFUSAL)):
            with VerifiedFile(path,delete=True) as held:
                with self.assertRaises(FileRemovalRetained) as caught:held.dispose(remote_legacy=called.append)
        self.assertEqual(caught.exception.native_reason,native_io.OWNER_LOCATION_REFUSAL+runtime.REMOTE_PROVIDER_REFUSAL)
        self.assertEqual(called,[]);self.assertTrue(path.is_file())


if __name__=='__main__':unittest.main()
