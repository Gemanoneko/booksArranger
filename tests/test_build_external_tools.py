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
    def refused_access(self,path,access,private):
        # OPEN_EXISTING only. Even unexpected success performs no write/delete.
        ctypes.set_last_error(0);handle=kernel.CreateFileW(str(path),access,7,None,3,0x00200000,None)
        if handle!=ctypes.c_void_p(-1).value:
            kernel.CloseHandle(handle);self.fail('Unexpected requested mutation handle opened: '+str(path))
        error=ctypes.get_last_error();self.assertIn(error,(32,) if private else (5,32));return error
    def test_fixed_real_git_aliases_retained_without_mutation(self):
        observations=[]
        with contextlib.ExitStack() as stack:
            self.assertEqual(Path(tools.retain_git(stack)),tools.GIT)
            for path in (*tools.GIT_ALIASES,*tools.CORE_ALIASES,*(tools.CORE.parent/name for name in tools.CORE_DLLS)):
                for access in (0x40000000,0x10000):observations.append({'path':str(path),'access':access,'refused_error':self.refused_access(path,access,False)})
        self.assertEqual(hashlib.sha256(tools.GIT.read_bytes()).hexdigest(),tools.GIT_WRAPPER_SHA256)
        print('ACTUAL_FIXED_GIT_REQUESTED_HANDLE_PROOF '+json.dumps(observations),flush=True)
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
