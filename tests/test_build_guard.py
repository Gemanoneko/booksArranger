import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import unittest
import uuid
import zipfile

ROOT=Path(__file__).absolute().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from build_fs_guard import BuildTree,remove_manifest_files,_native_receipt,capture_metadata,archive_metadata,publish_metadata,PriorBuild,producer_receipt,disposable_stage_receipts,retire_disposable_stage
from native_io import BoundaryError,OwnedProcessJob,VerifiedFile,publish_no_replace
BASE=ROOT.parent/'build-guard-probes'

def _remove_tree(path):
    """Removes a probe folder this run made. A junction or link inside it is removed as a link and never followed, so
    a probe that points outside (the junction tests) cannot reach what it points at."""
    try:info=os.lstat(path)
    except FileNotFoundError:return
    attributes=getattr(info,'st_file_attributes',0)
    if stat.S_ISLNK(info.st_mode) or attributes&stat.FILE_ATTRIBUTE_REPARSE_POINT:
        (os.rmdir if attributes&stat.FILE_ATTRIBUTE_DIRECTORY else os.unlink)(path);return
    if stat.S_ISDIR(info.st_mode):
        for entry in os.scandir(path):_remove_tree(entry.path)
        os.rmdir(path);return
    if not info.st_mode&stat.S_IWRITE:os.chmod(path,stat.S_IWRITE)
    os.unlink(path)

def _rmdir_quiet(path):
    try:os.rmdir(path)
    except OSError:pass

def discard(test,path):
    """Each probe folder goes when its test ends (2026-10-26: they used to stay beside the checkout for good), and the
    shared parent goes with the last one; another run's folders in it are left alone."""
    base=Path(path).parent
    def clean():
        _remove_tree(path)
        _rmdir_quiet(base)  # left when not empty: another probe or run still uses it
    test.addCleanup(clean);return path

class GuardTests(unittest.TestCase):
    def fixture(self):
        with BuildTree(ROOT.parent) as guard:
            return discard(self,guard.fresh(BASE))
    def test_fresh_native_write_and_collision(self):
        root=self.fixture()
        with BuildTree(root) as guard:
            fresh=guard.fresh(root/'builds');facts=guard.write(fresh/'a'/'b.bin',[b'hello'])
            self.assertEqual(facts,{'sha256':hashlib.sha256(b'hello').hexdigest(),'size':5})
            with self.assertRaises(BoundaryError):guard.write(fresh/'a'/'b.bin',[b'changed'])
        self.assertEqual((fresh/'a'/'b.bin').read_bytes(),b'hello')
    def test_junction_ancestor_refuses_without_touching_target(self):
        import _winapi
        root=self.fixture();outside=self.fixture();marker=outside/'keep.txt';marker.write_bytes(b'keep')
        _winapi.CreateJunction(str(outside),str(root/'build-cache'))
        with BuildTree(root) as guard:
            with self.assertRaises(BoundaryError):guard.directory(root/'build-cache'/'extract',create=True)
        self.assertEqual(marker.read_bytes(),b'keep');self.assertEqual(list(outside.iterdir()),[marker])
    def test_source_hardlink_refused(self):
        root=self.fixture();(root/'original').write_bytes(b'x');os.link(root/'original',root/'alias')
        with BuildTree(root) as guard:
            with self.assertRaises(BoundaryError):guard.protect(root/'alias')
        self.assertEqual((root/'original').read_bytes(),b'x')
    def test_exact_cleanup_preserves_unknown_and_refuses_mismatch(self):
        root=self.fixture()
        with BuildTree(root) as guard:
            fresh=guard.fresh(root/'builds');guard.write(fresh/'owned',[b'known']);manifest={'owned':_native_receipt(guard,fresh/'owned')}
        (fresh/'unknown').write_bytes(b'private')
        bad={'owned':{**manifest['owned'],'sha256':'0'*64}}
        with self.assertRaises(BoundaryError):remove_manifest_files(root,fresh,bad)
        self.assertEqual((fresh/'owned').read_bytes(),b'known')
        self.assertEqual(remove_manifest_files(root,fresh,manifest),1)
        self.assertEqual((fresh/'unknown').read_bytes(),b'private')
    def test_zip_traversal_rejected_before_any_member_write(self):
        root=self.fixture();archive=root/'bad.zip'
        with zipfile.ZipFile(archive,'w') as z:z.writestr('good',b'good');z.writestr('../outside',b'bad')
        with BuildTree(root) as guard:
            fresh=guard.fresh(root/'builds')
            with self.assertRaises(BoundaryError):guard.extract_zip(archive,fresh)
            self.assertEqual(list(fresh.iterdir()),[])
    def test_output_parent_swap_denied_while_held(self):
        root=self.fixture()
        with BuildTree(root) as guard:
            fresh=guard.fresh(root/'builds');guard.directory(fresh/'nested',create=True)
            with self.assertRaises(OSError):os.rename(fresh/'nested',fresh/'swapped')
            guard.write(fresh/'nested'/'safe',[b'safe'])
        self.assertEqual((fresh/'nested'/'safe').read_bytes(),b'safe')

class MetadataTests(unittest.TestCase):
    fixture=GuardTests.fixture
    def make_pointer(self,root,guard,content=b'{"version":"old"}'):
        folder=guard.fresh(root/'builds');guard.write(folder/'pointer.json',[content]);return folder/'pointer.json'
    def test_repeated_pointer_native_archive_then_publish(self):
        root=self.fixture()
        with BuildTree(root) as guard:
            pointer=self.make_pointer(root,guard);old=pointer.read_bytes();plan=capture_metadata(guard,pointer)
            guard.write(pointer.parent/'artifact.bin',[b'prior installer'])
            artifact=_native_receipt(guard,pointer.parent/'artifact.bin')
            calls=[]
            def verify():
                self.assertEqual(_native_receipt(guard,pointer.parent/'artifact.bin'),artifact);calls.append(True)
            previous=archive_metadata(guard,plan,verify)
            self.assertEqual(Path(previous).read_bytes(),old)
            guard.write(pointer.parent/'new.json',[b'{"version":"new"}'])
            publish_metadata(guard,pointer.parent/'new.json',pointer)
            self.assertEqual(pointer.read_bytes(),b'{"version":"new"}')
            self.assertEqual((pointer.parent/'artifact.bin').read_bytes(),b'prior installer')
            self.assertEqual(calls,[True])
    def test_identical_byte_substitution_refuses(self):
        root=self.fixture()
        with BuildTree(root) as guard:
            pointer=self.make_pointer(root,guard);plan=capture_metadata(guard,pointer)
            def swap(path):
                replacement=path.with_name('replacement.json');replacement.write_bytes(path.read_bytes())
                with VerifiedFile(path,delete=True) as held:held.dispose()
                publish_no_replace(replacement,path,guard.directories[str(path.parent).casefold()])
            with self.assertRaises(BoundaryError):archive_metadata(guard,plan,lambda:None,before_open=swap)
            self.assertEqual(pointer.read_bytes(),b'{"version":"old"}')
            self.assertEqual(list(pointer.parent.glob('*.previous-*')),[])
    def test_corrupt_bytes_refuse(self):
        root=self.fixture()
        with BuildTree(root) as guard:
            pointer=self.make_pointer(root,guard);plan=capture_metadata(guard,pointer)
            with self.assertRaises(BoundaryError):archive_metadata(guard,plan,lambda:None,before_open=lambda p:p.write_bytes(b'corrupt'))
            self.assertEqual(pointer.read_bytes(),b'corrupt');self.assertEqual(list(pointer.parent.glob('*.previous-*')),[])
    def test_named_stream_pointer_refuses(self):
        root=self.fixture();folder=root/'pointer';folder.mkdir();pointer=folder/'runtime-pointer.json';pointer.write_bytes(b'{}')
        Path(str(pointer)+':unknown').write_bytes(b'preserve ADS')
        with BuildTree(root) as guard:
            with self.assertRaises(BoundaryError):capture_metadata(guard,pointer)
        self.assertEqual(Path(str(pointer)+':unknown').read_bytes(),b'preserve ADS')
    def test_arriving_pointer_ads_refuses_before_archive(self):
        root=self.fixture()
        with BuildTree(root) as guard:
            pointer=self.make_pointer(root,guard);plan=capture_metadata(guard,pointer)
            def add_stream(path):Path(str(path)+':arriving').write_bytes(b'preserve arrival')
            with self.assertRaises(BoundaryError):archive_metadata(guard,plan,lambda:None,before_open=add_stream)
            self.assertEqual(Path(str(pointer)+':arriving').read_bytes(),b'preserve arrival')
            self.assertEqual(list(pointer.parent.glob('*.previous-*')),[])
    def test_hardlinked_pointer_refuses(self):
        root=self.fixture();pointer=root/'runtime-pointer.json';pointer.write_bytes(b'{}');os.link(pointer,root/'alias')
        with BuildTree(root) as guard:
            with self.assertRaises(BoundaryError):capture_metadata(guard,pointer)
        self.assertEqual((root/'alias').read_bytes(),b'{}')
    def test_cleanup_identical_substitution_refuses(self):
        root=self.fixture()
        with BuildTree(root) as guard:
            folder=guard.fresh(root/'builds');guard.write(folder/'owned',[b'known']);receipt=_native_receipt(guard,folder/'owned')
        replacement=folder/'replacement';replacement.write_bytes(b'known');os.replace(replacement,folder/'owned')
        with self.assertRaises(BoundaryError):remove_manifest_files(root,folder,{'owned':receipt})
        self.assertEqual((folder/'owned').read_bytes(),b'known')

class PriorBundleTests(unittest.TestCase):
    fixture=GuardTests.fixture
    def make_bundle(self,guard,version):
        root=guard.root;owned=guard.fresh(root/'build-cache'/'builds');runtime=guard.directory(owned/'runtime',create=True)
        guard.write(runtime/'python'/'python.exe',[b'private runtime fixture'])
        output=guard.fresh(root/'dist'/'builds');unpacked=guard.directory(output/'win-unpacked',create=True)
        guard.write(unpacked/'app.exe',[b'private payload fixture'])
        artifacts=[]
        for name in ['Books-Arranger-Setup-'+version+'.exe','Books-Arranger-Setup-'+version+'.exe.blockmap','latest.yml']:
            facts=guard.write(output/name,[name.encode()]);artifacts.append({'path':'builds/'+output.name+'/'+name,**facts})
        runtime_files=guard.tree_manifest(runtime);payload_files=guard.tree_manifest(unpacked)
        manifest={'schema':'books-desktop-artifacts-v1','version':version,'source_head':'a'*40,'product_digest':'b'*64,'build_id':output.name,'unpacked':'builds/'+output.name+'/win-unpacked','payload':{'verified':True,'installer_equivalent':True,'shell_version':version,'backend_version':version,'files':payload_files},'artifacts':artifacts}
        pointer={'schema':'books-runtime-pointer-v1','build_id':output.name,'root':str(runtime),'files':runtime_files,'manifest_sha256':hashlib.sha256(json.dumps(runtime_files,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        guard.created[str(root/'dist').casefold()]=root/'dist';guard.created[str(root/'build-cache').casefold()]=root/'build-cache'
        manifest_temp=root/'dist'/('new-'+str(uuid.uuid4()));pointer_temp=root/'build-cache'/('new-'+str(uuid.uuid4()))
        guard.write(manifest_temp,[json.dumps(manifest,sort_keys=True).encode()]);guard.write(pointer_temp,[json.dumps(pointer,sort_keys=True).encode()])
        record=producer_receipt(guard,owned,manifest,pointer,manifest_temp,pointer_temp)
        guard.write(owned/'producer-receipt.json',[json.dumps(record,sort_keys=True).encode()])
        return manifest_temp,pointer_temp,runtime,output
    def initial(self,root):
        with BuildTree(root) as guard:
            m,p,runtime,output=self.make_bundle(guard,'0.16.0')
            publish_metadata(guard,m,root/'dist'/'release-artifacts.json');publish_metadata(guard,p,root/'build-cache'/'runtime-pointer.json')
        return runtime,output
    def test_repeated_bundle_validates_full_prior_then_publishes(self):
        root=self.fixture();old_runtime,old_output=self.initial(root)
        old_bytes=(root/'dist'/'release-artifacts.json').read_bytes()
        with BuildTree(root) as guard:
            prior=PriorBuild(guard);m,p,new_runtime,new_output=self.make_bundle(guard,'0.17.0')
            archives=prior.archive()
            publish_metadata(guard,p,root/'build-cache'/'runtime-pointer.json');publish_metadata(guard,m,root/'dist'/'release-artifacts.json')
            self.assertEqual(Path(archives['manifest']).read_bytes(),old_bytes)
            self.assertEqual(json.loads((root/'dist'/'release-artifacts.json').read_text())['version'],'0.17.0')
        with BuildTree(root) as guard:PriorBuild(guard).verify()
        self.assertEqual((old_runtime/'python'/'python.exe').read_bytes(),b'private runtime fixture')
        self.assertTrue((old_output/'Books-Arranger-Setup-0.16.0.exe').exists())
    def test_same_byte_manifest_identity_replacement_refuses(self):
        root=self.fixture();self.initial(root);manifest=root/'dist'/'release-artifacts.json';old=manifest.read_bytes()
        temporary=root/'dist'/'replacement';temporary.write_bytes(old);os.replace(temporary,manifest)
        with BuildTree(root) as guard:
            with self.assertRaises(BoundaryError):PriorBuild(guard)
        self.assertEqual(manifest.read_bytes(),old);self.assertEqual(list((root/'dist').glob('*.previous-*')),[])
    def test_changed_runtime_refuses_without_archival(self):
        root=self.fixture();runtime,output=self.initial(root);(runtime/'python'/'python.exe').write_bytes(b'corrupt')
        old=(root/'build-cache'/'runtime-pointer.json').read_bytes()
        with BuildTree(root) as guard:
            with self.assertRaises(BoundaryError):PriorBuild(guard)
        self.assertEqual((root/'build-cache'/'runtime-pointer.json').read_bytes(),old)
        self.assertEqual(list((root/'dist').glob('*.previous-*')),[])
    def test_redundant_new_stage_cleanup_preserves_runtime_artifacts_unknown(self):
        root=self.fixture()
        with BuildTree(root) as guard:
            m,p,runtime,output=self.make_bundle(guard,'0.16.0');owned=runtime.parent
            guard.write(owned/'backend'/'module.py',[b'copied source']);guard.write(owned/'downloads'/'pinned.zip',[b'private archive'])
            receipts=disposable_stage_receipts(guard,owned)
            guard.write(owned/'backend'/'unknown-after-proof',[b'preserve unknown'])
            self.assertEqual(retire_disposable_stage(guard,owned,receipts),2)
            self.assertFalse((owned/'backend'/'module.py').exists());self.assertEqual((owned/'backend'/'unknown-after-proof').read_bytes(),b'preserve unknown')
            self.assertEqual((runtime/'python'/'python.exe').read_bytes(),b'private runtime fixture')
            self.assertTrue((output/'Books-Arranger-Setup-0.16.0.exe').exists())
    def test_missing_producer_receipt_refuses_unknown_candidate(self):
        root=self.fixture();runtime,output=self.initial(root);receipt=runtime.parent/'producer-receipt.json';receipt.unlink()
        original=(root/'build-cache'/'runtime-pointer.json').read_bytes()
        with BuildTree(root) as guard:
            with self.assertRaises(BoundaryError):PriorBuild(guard)
        self.assertEqual((root/'build-cache'/'runtime-pointer.json').read_bytes(),original)
        self.assertEqual(list((root/'dist').glob('*.previous-*')),[])
    def test_runtime_junction_refuses_outside_marker_preserved(self):
        import _winapi
        root=self.fixture();runtime,output=self.initial(root);outside=self.fixture();(outside/'keep').write_bytes(b'outside')
        runtime.rename(runtime.with_name('original-runtime'));_winapi.CreateJunction(str(outside),str(runtime))
        with BuildTree(root) as guard:
            with self.assertRaises(BoundaryError):PriorBuild(guard)
        self.assertEqual((outside/'keep').read_bytes(),b'outside');self.assertEqual(list(outside.iterdir()),[outside/'keep'])
        self.assertTrue((root/'dist'/'release-artifacts.json').exists())
    def test_moved_checkout_validates_prior_build_by_native_identity(self):
        # git worktree move: every recorded absolute path changes, every file keeps its native identity.
        root=self.fixture();old_runtime,old_output=self.initial(root)
        moved=discard(self,root.with_name(str(uuid.uuid4())));os.rename(root,moved)
        recorded=json.loads((moved/'build-cache'/'runtime-pointer.json').read_text())['root']
        self.assertFalse(Path(recorded).is_relative_to(moved),'positive control: the pointer still names the old location')
        with BuildTree(moved) as guard:
            prior=PriorBuild(guard);prior.verify()
            self.assertEqual(prior.runtime,moved/'build-cache'/'builds'/old_runtime.parent.name/'runtime')
        self.assertEqual(list((moved/'dist').glob('*.previous-*')),[])
    def test_copied_checkout_is_refused_by_native_identity(self):
        import shutil
        root=self.fixture();self.initial(root)
        with BuildTree(root) as guard:PriorBuild(guard)  # positive control: the original location validates
        copied=discard(self,root.with_name(str(uuid.uuid4())));shutil.copytree(root,copied)
        before=(copied/'build-cache'/'runtime-pointer.json').read_bytes()
        with BuildTree(copied) as guard:
            with self.assertRaises(BoundaryError):PriorBuild(guard)
        self.assertEqual((copied/'build-cache'/'runtime-pointer.json').read_bytes(),before)
        self.assertEqual(list((copied/'dist').glob('*.previous-*')),[])
    def test_recorded_location_resolves_only_inside_this_checkout(self):
        from build_fs_guard import _owned_build_location
        root=self.fixture();build=str(uuid.uuid4());inside=root/'build-cache'/'builds'/build/'runtime'
        with BuildTree(root) as guard:
            self.assertEqual(_owned_build_location(guard,str(inside)),inside)
            self.assertEqual(_owned_build_location(guard,'D:\\Elsewhere\\old\\build-cache\\builds\\'+build+'\\runtime'),inside)
            self.assertEqual(_owned_build_location(guard,'C:\\x\\Build-Cache\\BUILDS\\'+build+'\\runtime'),inside)
            for bad in ('D:\\Elsewhere\\runtime','D:\\old\\build-cache\\builds\\..\\..\\escape','relative\\build-cache\\builds\\'+build,
                        '\\\\?\\C:\\old\\build-cache\\builds\\'+build,'D:\\old\\build-cache\\builds\\'+build+'\\runtime:stream'):
                with self.subTest(bad=bad),self.assertRaises(BoundaryError):_owned_build_location(guard,bad)
    def test_payload_ads_refuses_and_preserves_stream(self):
        root=self.fixture();runtime,output=self.initial(root);ads=Path(str(output/'win-unpacked'/'app.exe')+':unknown');ads.write_bytes(b'unknown data')
        with BuildTree(root) as guard:
            with self.assertRaises(BoundaryError):PriorBuild(guard)
        self.assertEqual(ads.read_bytes(),b'unknown data');self.assertTrue((root/'dist'/'release-artifacts.json').exists())

class ProbeCleanupTests(unittest.TestCase):
    """Nothing this module makes stays on disk: plain, junction, moved and copied probes (2026-10-26)."""
    def test_every_probe_folder_is_removed_and_a_junction_target_is_kept(self):
        import _winapi
        from unittest import mock
        base=ROOT.parent/'build-guard-probes'/('cleanup-check-'+str(uuid.uuid4()))
        outside=ROOT.parent/('build-guard-outside-'+str(uuid.uuid4()));outside.mkdir();(outside/'keep').write_bytes(b'keep')
        self.addCleanup(_rmdir_quiet,base.parent);self.addCleanup(_remove_tree,outside);self.addCleanup(_remove_tree,base)
        class Linked(unittest.TestCase):
            fixture=GuardTests.fixture
            def runTest(self):
                root=self.fixture();(root/'file').write_bytes(b'x');_winapi.CreateJunction(str(outside),str(root/'link'))
                self.assertEqual((root/'link'/'keep').read_bytes(),b'keep','positive control: the junction reaches outside')
        names=['test_junction_ancestor_refuses_without_touching_target','test_moved_checkout_validates_prior_build_by_native_identity','test_copied_checkout_is_refused_by_native_identity']
        tests=[Linked()]+[(GuardTests if name.startswith('test_junction') else PriorBundleTests)(name) for name in names]
        with mock.patch.dict(globals(),{'BASE':base}):
            for test in tests:
                result=unittest.TestResult();test.run(result)
                self.assertTrue(result.wasSuccessful(),result.errors+result.failures)
        self.assertFalse(base.exists(),'%d probe paths left behind' % len(list(base.rglob('*'))) if base.exists() else '')
        self.assertEqual((outside/'keep').read_bytes(),b'keep','a junction is removed as a link, never followed')

if __name__=='__main__':unittest.main()
