"""Fixed Git alias holds: real requested handles only; mutation private only."""
import contextlib,ctypes,hashlib,json,os,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import build_external_tools as tools
from native_io import BoundaryError,kernel
from build_fs_guard import BuildTree

class GitAliasTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='git-alias-',dir=ROOT/'scratch');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.primary=self.root/'git.exe';self.alias=self.root/'git-lfs.exe'
        shutil.copyfile(tools.GIT,self.primary);os.link(self.primary,self.alias)
    def profile(self,stack):return tools._retain_profile(stack,self.primary,(self.primary,self.alias),tools.GIT_WRAPPER_SHA256)
    def refused_access(self,path,access,private,directory=False):
        # OPEN_EXISTING only. Even unexpected success performs no write/delete.
        flags=0x00200000|(0x02000000 if directory else 0)
        ctypes.set_last_error(0);handle=kernel.CreateFileW(str(path),access,7,None,3,flags,None)
        if handle!=ctypes.c_void_p(-1).value:
            kernel.CloseHandle(handle);self.fail('Unexpected requested mutation handle opened: '+str(path))
        error=ctypes.get_last_error();self.assertIn(error,(32,) if private else (5,32));return error
    def released_access(self,path,access,directory=False):
        # Private fixtures only: positive control that the same request opens once holds are released.
        handle=kernel.CreateFileW(str(path),access,7,None,3,0x00200000|(0x02000000 if directory else 0),None)
        self.assertNotEqual(handle,ctypes.c_void_p(-1).value,'Released private fixture still refused: '+str(path))
        kernel.CloseHandle(handle)
    def dependency_fixture(self,second=('libexec','git-core')):
        # Private copy of one pinned DLL; the real installed file is only read.
        name='zlib1.dll';core=self.root/'libexec'/'git-core';core.mkdir(parents=True);(self.root/'bin').mkdir()
        primary=self.root/'bin'/name;shutil.copyfile(tools.CORE.parent/name,primary)
        if second is not None:
            alias=self.root.joinpath(*second,name);alias.parent.mkdir(parents=True,exist_ok=True);os.link(primary,alias)
        return primary,(primary,core/name),tools.CORE_DLLS[name]
    def test_fixed_real_git_aliases_retained_without_mutation(self):
        observations=[]
        with contextlib.ExitStack() as stack:
            self.assertEqual(Path(tools.retain_git(stack)),tools.GIT)
            for path in (*tools.GIT_ALIASES,*tools.CORE_ALIASES,*(folder/name for name in tools.CORE_DLLS for folder in tools.CORE_DLL_DIRS)):
                for access in (0x40000000,0x10000):observations.append({'path':str(path),'access':access,'refused_error':self.refused_access(path,access,False)})
        self.assertEqual(hashlib.sha256(tools.GIT.read_bytes()).hexdigest(),tools.GIT_WRAPPER_SHA256)
        for name,digest in tools.CORE_DLLS.items():
            for folder in tools.CORE_DLL_DIRS:self.assertEqual(hashlib.sha256((folder/name).read_bytes()).hexdigest(),digest)
        print('ACTUAL_FIXED_GIT_REQUESTED_HANDLE_PROOF '+json.dumps(observations),flush=True)
    def test_private_dependency_both_names_and_folders_deny_mutation_then_release(self):
        primary,aliases,digest=self.dependency_fixture();before=primary.read_bytes()
        with contextlib.ExitStack() as stack:
            self.assertEqual(Path(tools._retain_dependency(stack,primary,aliases,digest)),primary)
            for path in aliases:
                self.refused_access(path,0x40000000,True);self.refused_access(path,0x10000,True)
                self.refused_access(path.parent,0x10000,True,directory=True)
                with self.assertRaises(PermissionError):path.write_bytes(b'changed')
                with self.assertRaises(PermissionError):path.rename(path.with_name('moved.dll'))
                with self.assertRaises(PermissionError):path.unlink()
            for path in aliases:self.assertEqual(path.read_bytes(),before)
        # Positive release controls distinguish sharing protection from ACLs.
        for path in aliases:
            self.released_access(path,0x10000);self.released_access(path.parent,0x10000,directory=True)
        with open(aliases[1],'r+b') as stream:stream.write(b'changed')
        self.assertEqual(primary.read_bytes()[:7],b'changed')
    def test_private_dependency_missing_second_name_refused(self):
        primary,aliases,digest=self.dependency_fixture(second=None)
        with contextlib.ExitStack() as stack:
            with self.assertRaisesRegex(BoundaryError,'dependency hash/link'):tools._retain_dependency(stack,primary,aliases,digest)
    def test_private_dependency_unexpected_third_name_refused(self):
        primary,aliases,digest=self.dependency_fixture();os.link(primary,self.root/'unknown.dll')
        with contextlib.ExitStack() as stack:
            with self.assertRaisesRegex(BoundaryError,'dependency hash/link'):tools._retain_dependency(stack,primary,aliases,digest)
        self.assertEqual(hashlib.sha256(primary.read_bytes()).hexdigest(),digest)
    def test_private_dependency_wrong_folder_second_name_refused(self):
        primary,aliases,digest=self.dependency_fixture(second=('libexec','other'))
        with contextlib.ExitStack() as stack:
            with self.assertRaisesRegex(BoundaryError,'dependency alias membership'):tools._retain_dependency(stack,primary,aliases,digest)
    def test_private_both_aliases_deny_mutation_then_release(self):
        before=self.primary.read_bytes()
        with contextlib.ExitStack() as stack:
            self.profile(stack)
            for path in (self.primary,self.alias):
                self.refused_access(path,0x40000000,True);self.refused_access(path,0x10000,True)
                with self.assertRaises(PermissionError):path.write_bytes(b'changed')
                with self.assertRaises(PermissionError):path.rename(self.root/(path.name+'.moved'))
                with self.assertRaises(PermissionError):path.unlink()
            self.assertEqual(self.primary.read_bytes(),before);self.assertEqual(self.alias.read_bytes(),before)
        # Positive release controls distinguish sharing protection from ACLs.
        with open(self.alias,'r+b') as stream:stream.write(b'changed')
        self.assertEqual(self.primary.read_bytes()[:7],b'changed')
        moved=self.alias.rename(self.root/'moved.exe');self.primary.unlink();moved.unlink()
        self.assertEqual(list(self.root.iterdir()),[])
    def test_unexpected_third_alias_refused(self):
        os.link(self.primary,self.root/'unknown.exe')
        with contextlib.ExitStack() as stack:
            with self.assertRaisesRegex(BoundaryError,'hash/link'):self.profile(stack)
        self.assertEqual(hashlib.sha256(self.primary.read_bytes()).hexdigest(),tools.GIT_WRAPPER_SHA256)
    def test_wrong_alias_name_refused(self):
        self.alias.rename(self.root/'unexpected.exe')
        with contextlib.ExitStack() as stack:
            with self.assertRaisesRegex(BoundaryError,'membership'):self.profile(stack)
    def test_wrong_hash_refused(self):
        with contextlib.ExitStack() as stack:
            with self.assertRaisesRegex(BoundaryError,'hash/link'):tools._retain_profile(stack,self.primary,(self.primary,self.alias),'0'*64)
    def test_build_input_output_hardlink_policy_remains_strict(self):
        with BuildTree(self.root) as tree:
            with self.assertRaisesRegex(BoundaryError,'hardlink refused'):tree.protect(self.primary)

if __name__=='__main__':unittest.main()
