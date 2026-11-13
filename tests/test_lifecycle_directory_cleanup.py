"""Real native cleanup controls; private fixtures only."""
import contextlib
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

from storage_relocation import RelocationRefused
from storage_relocation_operator import NativeItem,Security
import lifecycle_directory_cleanup as cleanup


@unittest.skipUnless(os.name=='nt','Native Windows cleanup')
class DirectoryCleanupTests(unittest.TestCase):
    def test_existing_intent_never_overwrites_foreign_changed_permissions(self):
        from storage_source_finalization import _acl
        with patch.object(cleanup.SourceDirectoryDelete,'dispose',side_effect=RuntimeError('refused')):
            self.assertTrue(self.apply()['security_restored'])
        intent,_=cleanup._read(self.receipt);security=Security()
        with NativeItem(self.path,directory=True,writable_security=True) as held:
            memory,pointer,_,_=_acl(security,intent['original_security'])
            self.assertEqual(security.api.SetSecurityInfo(held.handle,1,4|0x80000000,None,None,pointer,None),0)
            foreign=security.capture(held)
            try:
                result=self.apply();self.assertFalse(result['security_restored'])
                self.assertIn('foreign permissions',result['reason'])
                self.assertEqual(security.capture(held),foreign)
            finally:security.restore(held,intent['original_security'])
    def setUp(self):
        root=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',str(Path(__file__).resolve().parents[1]/'scratch')))
        self.area=root/('lifecycle-directory-'+uuid.uuid4().hex);self.area.mkdir(parents=True)
        self.path=self.area/'owned';self.path.mkdir();self.receipt=self.area/'disposal.json'
        with NativeItem(self.path,directory=True) as item:self.identity=item.facts['identity']
    def apply(self):return cleanup.dispose_owned_empty_directory(self.path,self.identity,receipt_path=self.receipt)

    def test_ordinary_empty_directory_removed_and_replay_pinned(self):
        result=self.apply();self.assertTrue(result['removed']);self.assertFalse(self.path.exists())
        self.assertTrue(self.apply()['removed'])
        self.path.mkdir();(self.path/'foreign').write_bytes(b'keep')
        self.assertFalse(self.apply()['removed']);self.assertEqual((self.path/'foreign').read_bytes(),b'keep')

    def test_unknown_contents_ads_and_wrong_identity_preserved(self):
        (self.path/'unknown').write_bytes(b'keep')
        with self.assertRaises(RelocationRefused):self.apply()
        (self.path/'unknown').unlink();Path(str(self.path)+':unknown').write_bytes(b'ADS')
        with self.assertRaises(RelocationRefused):self.apply()
        self.assertEqual(Path(str(self.path)+':unknown').read_bytes(),b'ADS')
        wrong=list(self.identity);wrong[-1]+=1
        with self.assertRaises(RelocationRefused):
            cleanup.dispose_owned_empty_directory(self.path,wrong,receipt_path=self.receipt)
        self.assertFalse(self.receipt.exists())

    def test_competing_stream_child_subdirectory_and_rename_denied(self):
        ordinary=self.area/'ordinary';ordinary.mkdir()
        Path(str(ordinary)+':ok').write_bytes(b'yes');(ordinary/'child').write_bytes(b'yes');(ordinary/'sub').mkdir()
        renamed=self.area/'renamed';ordinary.rename(renamed);renamed.rename(ordinary)
        original=cleanup.SourceDirectoryDelete.dispose
        def probe(deleting,record,security):
            program="import pathlib,sys;p=pathlib.Path(sys.argv[1]);n=0\nfor op in (lambda:pathlib.Path(str(p)+':arrival').write_bytes(b'x'),lambda:(p/'child').write_bytes(b'x'),lambda:(p/'sub').mkdir(),lambda:p.rename(p.with_name('raced'))):\n try:op()\n except PermissionError:n+=1\nsys.exit(0 if n==4 else 9)"
            child=subprocess.run([sys.executable,'-I','-B','-c',program,str(deleting.path)],capture_output=True,timeout=30)
            self.assertEqual(child.returncode,0,child.stderr.decode(errors='replace'))
            return original(deleting,record,security)
        with patch.object(cleanup.SourceDirectoryDelete,'dispose',probe):self.assertTrue(self.apply()['removed'])

    def test_present_failure_restores_original_dacl(self):
        with patch.object(cleanup.SourceDirectoryDelete,'dispose',side_effect=RuntimeError('injected refusal')):
            result=self.apply()
        self.assertFalse(result['removed']);self.assertTrue(result['security_restored'])
        (self.path/'writable-again').write_bytes(b'kept')
        self.assertEqual(self.apply()['phase'],'interrupted-held')

    def test_absence_after_disposition_without_closed_receipt_is_held(self):
        original=cleanup._publish
        def fail_closed(path,value):
            if value['phase']=='removed':raise RuntimeError('closed receipt interruption')
            return original(path,value)
        with patch.object(cleanup,'_publish',fail_closed):result=self.apply()
        self.assertTrue(result['held']);self.assertFalse(result['removed']);self.assertFalse(self.path.exists())
        self.assertEqual(self.apply()['phase'],'interrupted-held')

    def test_restore_failure_explicitly_retained(self):
        with patch.object(cleanup.SourceDirectoryDelete,'dispose',side_effect=RuntimeError('dispose refused')),\
             patch.object(cleanup.Security,'restore',side_effect=RuntimeError('restore refused')):
            result=self.apply()
        self.assertFalse(result['security_restored']);self.assertIn('restoration held',result['reason'])
        # Restore this private fixture's exact recorded original ACL only.
        intent,_=cleanup._read(self.receipt)
        with NativeItem(self.path,directory=True,writable_security=True) as item:
            self.assertEqual(item.facts['identity'],self.identity);Security().restore(item,intent['original_security'])

    def test_baseline_file_handle_does_not_exclude_arriving_ads(self):
        from native_io import VerifiedFile
        file=self.area/'file.bin';file.write_bytes(b'original')
        program="import ctypes,sys;from ctypes import wintypes;k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];k.CreateFileW.restype=wintypes.HANDLE;k.WriteFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p];k.CloseHandle.argtypes=[wintypes.HANDLE];h=k.CreateFileW(sys.argv[1],0x40000000,7,None,2,0,None);ok=h!=ctypes.c_void_p(-1).value;n=wintypes.DWORD();ok=ok and bool(k.WriteFile(h,b'arrival',7,ctypes.byref(n),None)) and n.value==7;k.CloseHandle(h);sys.exit(0 if ok else 8)"
        ordinary=subprocess.run([sys.executable,'-I','-B','-c',program,str(file)+':ordinary'],timeout=30)
        self.assertEqual(ordinary.returncode,0)
        Path(str(file)+':ordinary').unlink()
        with VerifiedFile(file,delete=True) as held:
            from source_cleanup import single_stream
            single_stream(file)
            child=subprocess.run([sys.executable,'-I','-B','-c',program,str(file)+':arrival'],timeout=30)
        # Record the actual behavior, rather than pretending base-file sharing
        # also protects the distinct named-stream namespace.
        self.assertEqual(child.returncode,0,'Provider behavior changed: inspect file ADS guard')
        self.assertEqual(Path(str(file)+':arrival').read_bytes(),b'arrival')


if __name__=='__main__':unittest.main()
