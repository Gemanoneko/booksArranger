"""Windows-only disposable fixtures; no real library/service operations."""
from sorted_fixture import library_is_sorted  # 0.21.3: fixtures publish inside their library
import contextlib, hashlib, json, os, subprocess, sys, tempfile, unittest, uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audio_jobs import AudioJobs
from native_io import BoundaryError,DirectoryBoundary,VerifiedDirectory,DirectoryNotEmptyError,DirectoryDispositionUnsupported,kernel
from scanner import connect
from source_cleanup import CleanupJobs,packed
from storage_cleanup import StorageCleanup

@unittest.skipUnless(os.name=='nt','Exact native directory fixtures require Windows')
class SourceFolderTests(unittest.TestCase):
    # Ruling 74e (2026-10-31): the book's own folder goes once no audio is left in it, its non-audio files with it, with a
    # plain non-recursive rmdir that also works on real NTFS (ruling 24a's removal). The patched-capability tests below
    # come from the exact-handle disposition model; the post-conversion cleanup no longer asks for that capability.
    def setUp(self):
        scratch=Path(__file__).resolve().parents[1]/'scratch/progress-folders-2026-10-10/empty-folder-fixtures'
        scratch.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='case-',dir=scratch)
        self.base=Path(self.temp.name);self.library=self.base/'library';self.library.mkdir()
        self.folder=self.library/'Author'/'Old Book'/'Disc';self.folder.mkdir(parents=True)
        self.db=self.base/'inventory.sqlite3';self.job_id=str(uuid.uuid4());self.sources=[]
        for index in range(2):
            path=self.folder/f'{index}.mp3';path.write_bytes(bytes([65+index])*512);facts=path.stat()
            self.sources.append({'path':str(path),'size':facts.st_size,'modified':str(facts.st_mtime_ns),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fingerprint':{'size':facts.st_size,'modified':str(facts.st_mtime_ns)}})
        self.final=self.library/'book.m4b';self.final.write_bytes(b'validated fixture audiobook');sha=hashlib.sha256(self.final.read_bytes()).hexdigest()
        with DirectoryBoundary(self.library,self.final.parent) as boundary:parent_identity=boundary.identities
        self.manifest={'job_id':self.job_id,'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'root':str(self.library),'sources':self.sources,'destination':str(self.final),'profile':'fixture','metadata':{'title':'Fixture','canonical_author':'Author'},'chapters':[],'evidence':[],'cover':{'path':str(self.final),'sha256':sha},'cleanup_policy':{'enabled':True}}
        validation={'passed':True,'checks':'Output checks passed','profile':'fixture','sha256':sha,'size':self.final.stat().st_size,'tags':{'media_type':'2','title':'Fixture','artist':'Author'},'source_pcm_frames':[100,100],'source_pcm_rate':100,'decoded_duration':2,'duration_tolerance':.01,'chapters':[]}
        self.output={'job_id':self.job_id,'final_path':str(self.final),'owned_temp':str(self.library/'absent.partial'),'size':self.final.stat().st_size,'sha256':sha,'parent_identity':parent_identity,'validation':validation}
        self.queue=AudioJobs(self.db,None,None,lambda r:True);self.queue.enqueue(self.manifest);self.queue._update(self.job_id,state='completed',stage='completed',output=json.dumps(self.output))
        with connect(self.db) as db:db.execute('CREATE TABLE owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER)')
        self.source=CleanupJobs(self.db,self.base/'source-recovery',lambda db,intent:True,contextlib.nullcontext,output_policy=library_is_sorted(self.library))
        self.stage_root=self.base/'merge-cache/audio-staging';self.stage_root.mkdir(parents=True)
        self.job=self.stage_root/self.job_id;self.job.mkdir();(self.job/'ownership.json').write_text(packed({'job_id':self.job_id,'manifest':self.manifest}),encoding='utf-8')
        self.storage=StorageCleanup(self.db,self.stage_root,self.source.root)
        self.full={'job_id':self.job_id,'state':'completed','manifest':self.manifest,'output':self.output}
    def tearDown(self):
        self.source.close();self.queue.close();self.temp.cleanup()
    def retire(self,purge=True):
        self.cleanup_id=self.source.enroll(self.full,{})
        self.source.run(self.cleanup_id)
        if purge:self.storage.run(self.job_id)
    def receipt(self,path):
        return self.storage._folder_known(self.job_id,path)
    def assert_output(self):
        self.assertEqual(hashlib.sha256(self.final.read_bytes()).hexdigest(),self.output['sha256'])
    @patch.object(VerifiedDirectory,'require_empty_disposition',return_value={'fixture_only_simulated_streamless_provider':True})
    def test_empty_source_ancestors_removed_bottom_up_root_output_preserved(self,_capability):
        self.retire();phases=[];status=self.storage.run_folders(self.job_id,phases.append)
        # Audit m2 (0.21.3): the book's own folders go; the author folder, a direct child of the source root, stays.
        self.assertEqual(phases,['folders']);self.assertEqual(status['state'],'completed');self.assertEqual(status['removed'],2)
        self.assertFalse((self.library/'Author'/'Old Book').exists());self.assertTrue((self.library/'Author').is_dir());self.assertEqual(list((self.library/'Author').iterdir()),[])
        self.assertIsNone(self.receipt(self.library/'Author'),'never even a candidate');self.assertTrue(self.library.exists());self.assertIsNone(self.receipt(self.library));self.assert_output()
        self.assertEqual(self.storage.run_folders(self.job_id)['removed'],2)
        self.assertEqual(len(self.storage.folder_status()),1)
    def test_nonempty_hidden_sidecar_cover_and_unselected_source_preserved(self):
        for name in ('.hidden','cover.jpg','unselected.mp3'):(self.folder/name).write_bytes(b'UNIQUE USER CONTENT')
        kernel.SetFileAttributesW(str(self.folder/'.hidden'),2)
        self.retire();status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['state'],'completed');self.assertEqual(status['removed'],0);self.assertEqual(status['retained'],2)  # Disc and Old Book; Author is no candidate (m2)
        for name in ('.hidden','cover.jpg','unselected.mp3'):self.assertEqual((self.folder/name).read_bytes(),b'UNIQUE USER CONTENT')
        self.assert_output()
    def test_directory_alternate_stream_is_nonempty_and_preserved(self):
        self.retire()
        with open(str(self.folder)+':keep','wb') as stream:stream.write(b'UNIQUE DIRECTORY STREAM')
        status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['state'],'completed');self.assertEqual(status['removed'],0)
        with open(str(self.folder)+':keep','rb') as stream:self.assertEqual(stream.read(),b'UNIQUE DIRECTORY STREAM')
    def test_nested_git_ancestor_blocks_all_folder_dispositions(self):
        self.retire();(self.folder.parent/'.git').mkdir()
        with self.assertRaisesRegex(BoundaryError,'Git'):self.storage.run_folders(self.job_id)
        self.assertTrue(self.folder.exists());self.assert_output();self.assertEqual(self.storage.folder_status(self.job_id)['state'],'needs_attention')
    def test_reparse_source_ancestor_is_rejected_without_following(self):
        self.retire();held=self.base/'preserved';self.folder.rename(held)
        result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(self.folder),str(held)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        with self.assertRaisesRegex(BoundaryError,'junction|reparse'):self.storage.run_folders(self.job_id)
        self.assertTrue(held.exists());self.assertTrue(os.path.isjunction(self.folder));self.assert_output()
    def test_incomplete_retirement_and_incomplete_purge_are_ineligible(self):
        self.cleanup_id=self.source.enroll(self.full,{})
        with self.assertRaisesRegex(BoundaryError,'retirement must complete'):self.storage.run_folders(self.job_id)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
        self.source.run(self.cleanup_id)
        with self.assertRaisesRegex(BoundaryError,'temporary-copy cleanup must complete'):self.storage.run_folders(self.job_id)
        self.assertEqual(len(list((self.source.root/self.cleanup_id).iterdir())),2);self.assertTrue(self.folder.exists())
    def test_unenrolled_legacy_job_never_gets_folder_cleanup(self):
        self.assertIsNone(self.storage.run_folders(self.job_id));self.assertIsNone(self.storage.folder_status(self.job_id))
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
        with connect(self.db) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM source_cleanup').fetchone()[0],0)
    def test_changed_output_or_retirement_correspondence_blocks(self):
        self.retire();original=self.final.read_bytes();self.final.write_bytes(b'changed output')
        with self.assertRaisesRegex(BoundaryError,'output bytes'):self.storage.run_folders(self.job_id)
        self.assertTrue(self.folder.exists());self.final.write_bytes(original)
        with connect(self.db) as db:db.execute("UPDATE source_retirements SET source_hash='changed' WHERE job_id=?",(self.job_id,))
        with self.assertRaisesRegex(BoundaryError,'correspondence'):self.storage.run_folders(self.job_id)
        self.assertTrue(self.folder.exists());self.assert_output()
    def test_replacement_original_blocks_even_after_verified_purge(self):
        self.retire();replacement=Path(self.sources[0]['path']);replacement.write_bytes(b'NEW ORIGINAL')
        with self.assertRaisesRegex(BoundaryError,'replacement original'):self.storage.run_folders(self.job_id)
        self.assertEqual(replacement.read_bytes(),b'NEW ORIGINAL');self.assertTrue(self.folder.exists())
    def test_file_arriving_between_empty_check_and_removal_survives(self):
        # 74e: the plain rmdir itself refuses a folder that is no longer empty; nothing recursive ever runs.
        self.retire();real=os.rmdir;arrived=[]
        def arrival(path,*args,**kwargs):
            if Path(path)==self.folder and not arrived:
                late=self.folder/'arrived.txt';late.write_bytes(b'NEW SIDECAR');arrived.append(late)
            return real(path,*args,**kwargs)
        with patch('os.rmdir',arrival):status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['state'],'completed');self.assertEqual(status['removed'],0);self.assertEqual(arrived[0].read_bytes(),b'NEW SIDECAR')
        self.assertEqual(self.receipt(self.folder)['state'],'retained_nonempty');self.assert_output()
    def test_native_atomic_disposition_preserves_new_directory_stream(self):
        import ctypes
        from ctypes import wintypes
        self.retire()
        with DirectoryBoundary(self.library,self.folder.parent),VerifiedDirectory(self.folder,delete=True) as target:
            self.assertTrue(target.empty())
            handle=kernel.CreateFileW(str(self.folder)+':late',0x40000000,7,None,2,0x00200000,None)
            self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
            try:
                kernel.WriteFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p];kernel.WriteFile.restype=wintypes.BOOL
                data=b'UNIQUE LATE DIRECTORY STREAM';written=wintypes.DWORD()
                self.assertTrue(kernel.WriteFile(handle,data,len(data),ctypes.byref(written),None));self.assertEqual(written.value,len(data))
            finally:kernel.CloseHandle(handle)
            with patch.object(target,'empty',return_value=True):
                with self.assertRaisesRegex(DirectoryDispositionUnsupported,'named data streams'):target.dispose_empty()
        self.assertTrue(self.folder.exists())
        with open(str(self.folder)+':late','rb') as stream:self.assertEqual(stream.read(),b'UNIQUE LATE DIRECTORY STREAM')
    def test_real_named_stream_volume_removes_emptied_source_folders(self):
        # 74e (Legends' empty folder on Z:): a real NTFS volume, which reports named streams, no longer keeps the folders.
        self.retire();status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['state'],'completed');self.assertEqual(status['removed'],2);self.assertEqual(status['unsupported'],0)
        self.assertFalse((self.library/'Author'/'Old Book').exists());self.assertTrue((self.library/'Author').is_dir());self.assertTrue(self.library.exists())
        self.assertIsNone(self.receipt(self.library/'Author'));self.assertIsNone(self.receipt(self.library));self.assert_output()
        self.assertEqual(self.storage.status()[0]['state'],'completed');self.assertEqual(self.source.status(self.job_id)['state'],'completed')
        self.assertEqual(self.storage.run_folders(self.job_id)['state'],'completed')
    def test_cover_hidden_and_text_files_go_with_the_folder_when_no_audio_is_left(self):
        # 74e (Логово's .jpg): the book's own folder loses its non-audio files, then goes; the author folder stays (m2).
        for name in ('.hidden','cover.jpg','notes.txt'):(self.folder/name).write_bytes(b'LEFTOVER')
        kernel.SetFileAttributesW(str(self.folder/'.hidden'),2)
        self.retire();status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['state'],'completed');self.assertEqual(status['removed'],2);self.assertEqual(status['retained'],0)
        self.assertFalse(self.folder.exists());self.assertFalse((self.library/'Author'/'Old Book').exists());self.assertTrue((self.library/'Author').is_dir())
        self.assertEqual(self.receipt(self.folder)['state'],'removed');self.assert_output()
    def test_audio_in_any_format_keeps_the_folder_and_every_file(self):
        for name,data in (('bonus.ape',b'OTHER RECORDING'),('cover.jpg',b'COVER')):(self.folder/name).write_bytes(data)
        self.retire();status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['removed'],0);self.assertEqual(status['retained'],2)
        self.assertEqual((self.folder/'bonus.ape').read_bytes(),b'OTHER RECORDING');self.assertEqual((self.folder/'cover.jpg').read_bytes(),b'COVER')
        self.assertIn('Audio files remain',self.receipt(self.folder)['reason']);self.assert_output()
    def test_subfolder_keeps_the_folder_and_its_files(self):
        (self.folder/'Scans').mkdir();(self.folder/'Scans'/'page.jpg').write_bytes(b'SCAN');(self.folder/'cover.jpg').write_bytes(b'COVER')
        self.retire();status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['removed'],0);self.assertEqual((self.folder/'Scans'/'page.jpg').read_bytes(),b'SCAN');self.assertEqual((self.folder/'cover.jpg').read_bytes(),b'COVER')
        self.assertIn('subfolder',self.receipt(self.folder)['reason'])
    def test_ancestor_folder_keeps_its_own_files(self):
        # Only a folder a source sat in loses its other files; a series or book folder above it goes only when empty.
        (self.folder.parent/'series.jpg').write_bytes(b'SERIES');(self.folder/'cover.jpg').write_bytes(b'COVER')
        self.retire();status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['removed'],1);self.assertEqual(status['retained'],1);self.assertFalse(self.folder.exists())
        self.assertEqual((self.folder.parent/'series.jpg').read_bytes(),b'SERIES');self.assertEqual(self.receipt(self.folder.parent)['state'],'retained_nonempty')
    def test_file_another_unfinished_job_names_keeps_the_folder(self):
        cover=self.folder/'cover.jpg';cover.write_bytes(b'COVER');self.retire()
        other=dict(self.manifest,job_id=str(uuid.uuid4()),candidate_id=str(uuid.uuid4()),sources=[],cover={'path':str(cover),'sha256':'0'*64})
        with connect(self.db) as db:db.execute('INSERT INTO audio_jobs(job_id,state,stage,manifest,manifest_hash,created,updated,journal,reason) VALUES(?,?,?,?,?,?,?,?,?)',
                                               (other['job_id'],'pending','queued',json.dumps(other),'x','2026-10-31','2026-10-31','{}',''))
        status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['removed'],0);self.assertEqual(cover.read_bytes(),b'COVER');self.assertIn('Another book or job',self.receipt(self.folder)['reason'])
    def test_file_with_a_second_name_keeps_the_folder(self):
        (self.folder/'cover.jpg').write_bytes(b'COVER');os.link(self.folder/'cover.jpg',self.base/'elsewhere.jpg')
        self.retire();status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['removed'],0);self.assertEqual((self.folder/'cover.jpg').read_bytes(),b'COVER');self.assertIn('second name',self.receipt(self.folder)['reason'])
    def test_leftover_that_cannot_be_removed_keeps_the_folder(self):
        (self.folder/'cover.jpg').write_bytes(b'COVER');(self.folder/'notes.txt').write_bytes(b'NOTES')
        self.retire()
        with patch('book_delete.remove',return_value=('in_use','[WinError 32] in use')):status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['removed'],0);self.assertTrue(self.folder.exists());self.assertIn('could not be removed',self.receipt(self.folder)['reason'])
    def test_unknown_volume_capability_refuses_native_disposition(self):
        self.retire()
        with DirectoryBoundary(self.library,self.folder.parent),VerifiedDirectory(self.folder,delete=True) as target,patch.object(kernel,'GetVolumeInformationByHandleW',return_value=0):
            with self.assertRaisesRegex(DirectoryDispositionUnsupported,'capability is unavailable'):target.dispose_empty()
        self.assertTrue(self.folder.exists());self.assert_output()
    def test_unknown_provider_refuses_even_reported_streamless_capability(self):
        import ctypes
        from ctypes import wintypes
        self.retire()
        with DirectoryBoundary(self.library,self.folder.parent),VerifiedDirectory(self.folder,delete=True) as target:
            def capability(handle,name,namesize,serial,maximum,flags,filesystem,capacity):
                self.assertEqual(handle,target.handle)
                ctypes.cast(serial,ctypes.POINTER(wintypes.DWORD)).contents.value=target.info.volume
                ctypes.cast(maximum,ctypes.POINTER(wintypes.DWORD)).contents.value=255
                ctypes.cast(flags,ctypes.POINTER(wintypes.DWORD)).contents.value=0
                filesystem.value='fixture-streamless';return 1
            with patch.object(kernel,'GetVolumeInformationByHandleW',side_effect=capability),patch.object(kernel,'GetFinalPathNameByHandleW',return_value=0):
                with self.assertRaisesRegex(DirectoryDispositionUnsupported,'provider cannot be established'):target.dispose_empty()
        self.assertTrue(self.folder.exists());self.assert_output()
    def test_strict_volume_guid_checked_for_reported_streamless_provider(self):
        import ctypes
        from ctypes import wintypes
        self.retire()
        with DirectoryBoundary(self.library,self.folder.parent),VerifiedDirectory(self.folder,delete=True) as target:
            def capability(handle,name,namesize,serial,maximum,flags,filesystem,capacity):
                ctypes.cast(serial,ctypes.POINTER(wintypes.DWORD)).contents.value=target.info.volume
                ctypes.cast(maximum,ctypes.POINTER(wintypes.DWORD)).contents.value=255
                filesystem.value='fixture-streamless';return 1
            def provider(handle,buffer,capacity,flags):
                # Prefix alone must never establish a local exact-volume identity.
                buffer.value=chr(92)*2+'?'+chr(92)+'Volume{unverified}'+chr(92)+'library';return len(buffer.value)
            with patch.object(kernel,'GetVolumeInformationByHandleW',side_effect=capability),patch.object(kernel,'GetFinalPathNameByHandleW',side_effect=provider):
                with self.assertRaisesRegex(DirectoryDispositionUnsupported,'provider identity is ambiguous'):target.dispose_empty()
        self.assertTrue(self.folder.exists());self.assert_output()
    def test_ambiguous_volume_identity_refuses_native_disposition(self):
        self.retire()
        with DirectoryBoundary(self.library,self.folder.parent),VerifiedDirectory(self.folder,delete=True) as target,patch.object(kernel,'GetVolumeInformationByHandleW',return_value=1):
            with self.assertRaisesRegex(DirectoryDispositionUnsupported,'identity is ambiguous'):target.dispose_empty()
        self.assertTrue(self.folder.exists());self.assert_output()
    @patch.object(VerifiedDirectory,'require_empty_disposition',return_value={'fixture_only_simulated_streamless_provider':True})
    def test_native_atomic_nonempty_check_even_if_enumeration_was_stale(self,_capability):
        self.retire();(self.folder/'arrived.txt').write_bytes(b'NEW SIDECAR')
        with DirectoryBoundary(self.library,self.folder.parent),VerifiedDirectory(self.folder,delete=True) as target,patch.object(target,'empty',return_value=True):
            with self.assertRaises(DirectoryNotEmptyError):target.dispose_empty()
        self.assertEqual((self.folder/'arrived.txt').read_bytes(),b'NEW SIDECAR')
    @patch.object(VerifiedDirectory,'require_empty_disposition',return_value={'fixture_only_simulated_streamless_provider':True})
    def test_delete_pending_directory_refuses_new_children_until_close(self,_capability):
        self.retire()
        with DirectoryBoundary(self.library,self.folder.parent),VerifiedDirectory(self.folder,delete=True) as target:
            target.dispose_empty()
            with self.assertRaises(OSError):(self.folder/'late.txt').write_bytes(b'late')
        self.assertFalse(self.folder.exists());self.assert_output()
    @patch.object(VerifiedDirectory,'require_empty_disposition',return_value={'fixture_only_simulated_streamless_provider':True})
    def test_crash_after_native_disposition_reconciles_durable_intent(self,_capability):
        self.retire();real=self.storage._folder_state;failed=[]
        def crash(job_id,path,state,reason=''):
            if state=='disposition_set' and not failed:failed.append(path);raise RuntimeError('simulated crash after disposition')
            return real(job_id,path,state,reason)
        with patch.object(self.storage,'_folder_state',side_effect=crash):
            with self.assertRaisesRegex(RuntimeError,'simulated'):self.storage.run_folders(self.job_id)
        self.assertFalse(failed[0].exists());status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['state'],'completed');self.assertEqual(status['absent_after_intent'],1);self.assertEqual(status['removed'],1);self.assert_output()  # Disc, Old Book (m2)
    def test_crash_before_disposition_rejects_replaced_empty_directory(self):
        self.retire()
        with patch('os.rmdir',side_effect=RuntimeError('simulated before disposition')):
            with self.assertRaises(RuntimeError):self.storage.run_folders(self.job_id)
        saved=self.base/'old-empty';self.folder.rename(saved);self.folder.mkdir()
        with self.assertRaisesRegex(BoundaryError,'identity changed'):self.storage.run_folders(self.job_id)
        self.assertTrue(saved.exists());self.assertTrue(self.folder.exists());self.assert_output()
    def test_unknown_absence_of_verified_only_directory_is_not_success(self):
        self.retire()
        with patch.object(self.storage,'_remove_folder',side_effect=RuntimeError('before intent')):
            with self.assertRaises(RuntimeError):self.storage.run_folders(self.job_id)
        self.folder.rmdir()
        with self.assertRaisesRegex(BoundaryError,'without verified removal intent'):self.storage.run_folders(self.job_id)
        self.assertEqual(self.receipt(self.folder)['state'],'verified');self.assertEqual(self.storage.folder_status(self.job_id)['state'],'needs_attention')
    @patch.object(VerifiedDirectory,'require_empty_disposition',return_value={'fixture_only_simulated_streamless_provider':True})
    def test_terminal_completed_receipt_preserves_replacement_without_rehash(self,_capability):
        self.retire();prior=self.storage.run_folders(self.job_id);self.folder.mkdir(parents=True)
        with patch.object(self.storage,'protected_output',side_effect=AssertionError('Terminal folder receipt must not rehash output')):
            self.assertEqual(self.storage.run_folders(self.job_id),prior)
        self.assertTrue(self.folder.exists());self.assert_output()
    def test_terminal_unsupported_receipt_returns_without_output_rehash(self):
        # A receipt an earlier version left 'unsupported' (an empty folder kept on NTFS) is final: 74e applies to cleanups
        # from 0.24.1 on and never re-runs a finished one.
        self.retire();self.storage._folder_set(self.job_id,self.output['sha256'],'unsupported','Empty source folder retained: NTFS supports named data streams')
        prior=self.storage.run_folders(self.job_id);self.assertEqual(prior['state'],'unsupported')
        with patch.object(self.storage,'protected_output',side_effect=AssertionError('Deferred folder receipt must not rehash output')):
            self.assertEqual(self.storage.run_folders(self.job_id),prior)
        self.assertTrue(self.folder.exists());self.assert_output()

    @patch.object(VerifiedDirectory,'require_empty_disposition',return_value={'fixture_only_simulated_streamless_provider':True})
    def test_unrelated_sibling_prevents_ancestor_removal(self,_capability):
        self.retire();sibling=self.library/'Author'/'Other Book';sibling.mkdir();(sibling/'keep.txt').write_bytes(b'keep')
        status=self.storage.run_folders(self.job_id)
        self.assertEqual(status['removed'],2);self.assertEqual(status['retained'],0);self.assertEqual((sibling/'keep.txt').read_bytes(),b'keep');self.assertTrue(self.library.exists())  # Author is no candidate (m2)

if __name__=='__main__':unittest.main()
