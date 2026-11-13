"""Native finite file-fence disposition controls on private data."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

from storage_relocation import RelocationRefused
from storage_relocation_operator import NativeItem,Security
import lifecycle_file_cleanup as cleanup


@unittest.skipUnless(os.name=='nt','Native Windows file cleanup')
class FileCleanupTests(unittest.TestCase):
    def setUp(self):
        root=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',str(Path(__file__).resolve().parents[1]/'scratch')))
        self.area=root/('lifecycle-file-'+uuid.uuid4().hex);self.area.mkdir(parents=True)
        self.path=self.area/'owned.bin';self.path.write_bytes(b'owned bytes');self.receipt=self.area/'disposal.json'
        with NativeItem(self.path) as item:self.facts=item.facts;self.sha=item.sha256()
    def apply(self):return cleanup.dispose_owned_file(self.path,self.facts,self.sha,receipt_path=self.receipt)

    def test_security_descriptor_drift_refuses_before_fence_mutation(self):
        security=Security()
        with NativeItem(self.path,writable_security=True) as held:
            original=security.capture(held);planned=security.planned_write_fence_acl(original,False)
            changed=dict(original,sddl=original['sddl']+'foreign')
            with patch.object(security,'capture',return_value=changed):
                with self.assertRaisesRegex(Exception,'changed|drift|original'):
                    security.apply_planned_write_fence(held,original,planned)
            self.assertEqual(security.capture(held),original)

    def test_invalid_bounded_raw_security_descriptor_rejected(self):
        import base64,hashlib
        with NativeItem(self.path,writable_security=True) as held:original=Security().capture(held)
        damaged=dict(original);raw=b'\x01\x00\x00\x80'+b'\xff'*28
        damaged['bytes']=base64.b64encode(raw).decode('ascii');damaged['sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(Exception):Security().validate_capture(damaged)

    def test_finite_capability_rechecks_actual_provider_before_disposition(self):
        import runtime_file_disposition
        with patch.object(runtime_file_disposition,'_local_provider',side_effect=RuntimeError('unverifiable provider')):
            result=self.apply()
        self.assertFalse(result['removed']);self.assertIn('unverifiable provider',result['reason'])
        self.assertEqual(self.path.read_bytes(),b'owned bytes')
        self.path.write_bytes(b'original permissions restored')

    def test_ordinary_exact_file_removed_replay_retains_new_name(self):
        self.assertTrue(self.apply()['removed']);self.assertTrue(self.apply()['removed'])
        self.path.write_bytes(b'unrelated replacement')
        self.assertFalse(self.apply()['removed']);self.assertEqual(self.path.read_bytes(),b'unrelated replacement')

    def test_wrong_hash_native_identity_and_existing_ads_refuse(self):
        with self.assertRaises(RelocationRefused):
            cleanup.dispose_owned_file(self.path,self.facts,'0'*64,receipt_path=self.receipt)
        wrong=dict(self.facts,identity=[0,0,1])
        with self.assertRaises(RelocationRefused):cleanup.dispose_owned_file(self.path,wrong,self.sha,receipt_path=self.receipt)
        Path(str(self.path)+':existing').write_bytes(b'unknown stream')
        with self.assertRaises(Exception):self.apply()
        self.assertEqual(Path(str(self.path)+':existing').read_bytes(),b'unknown stream')
        self.assertFalse(self.receipt.exists())

    def test_competing_arriving_ads_base_write_and_rename_denied(self):
        ordinary=self.area/'ordinary';ordinary.write_bytes(b'allowed');Path(str(ordinary)+':ok').write_bytes(b'yes')
        ordinary.rename(self.area/'renamed')
        native="import ctypes,sys;from ctypes import wintypes;k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];k.CreateFileW.restype=wintypes.HANDLE;k.WriteFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p];k.CloseHandle.argtypes=[wintypes.HANDLE];h=k.CreateFileW(sys.argv[1],0x40000000,7,None,2,0,None);opened=h!=ctypes.c_void_p(-1).value;n=wintypes.DWORD();ok=opened and bool(k.WriteFile(h,b'arrival',7,ctypes.byref(n),None)) and n.value==7;k.CloseHandle(h);sys.exit(0 if ok else 8)"
        positive=subprocess.run([sys.executable,'-I','-B','-c',native,str(self.area/'renamed')+':native-ok'],timeout=30)
        self.assertEqual(positive.returncode,0)
        original=cleanup.LifecycleFileDelete.dispose
        def probe(deleting,*args,**kwargs):
            program="import pathlib,sys;p=pathlib.Path(sys.argv[1]);n=0\nfor op in (lambda:pathlib.Path(str(p)+':arrival').write_bytes(b'ADS'),lambda:p.write_bytes(b'changed'),lambda:p.rename(p.with_name('raced'))):\n try:op()\n except PermissionError:n+=1\nsys.exit(0 if n==3 else 9)"
            child=subprocess.run([sys.executable,'-I','-B','-c',program,str(deleting.path)],capture_output=True,timeout=30)
            self.assertEqual(child.returncode,0,child.stderr.decode(errors='replace'))
            actual=subprocess.run([sys.executable,'-I','-B','-c',native,str(deleting.path)+':native-arrival'],timeout=30)
            self.assertEqual(actual.returncode,8,'Finite DACL must deny native GENERIC_WRITE/share7 ADS creation')
            return original(deleting,*args,**kwargs)
        with patch.object(cleanup.LifecycleFileDelete,'dispose',probe):self.assertTrue(self.apply()['removed'])

    def test_present_failure_restores_original_permissions(self):
        with patch.object(cleanup.LifecycleFileDelete,'dispose',side_effect=RuntimeError('native refusal')):result=self.apply()
        self.assertFalse(result['removed']);self.assertTrue(result['security_restored'])
        self.path.write_bytes(b'writable again');self.assertEqual(self.apply()['phase'],'interrupted-held')

    def test_existing_intent_never_overwrites_foreign_changed_permissions(self):
        from storage_source_finalization import _acl
        with patch.object(cleanup.LifecycleFileDelete,'dispose',side_effect=RuntimeError('refused')):
            self.assertTrue(self.apply()['security_restored'])
        intent,_=cleanup._read(self.receipt);security=Security()
        with NativeItem(self.path,writable_security=True) as held:
            memory,pointer,_,_=_acl(security,intent['original_security'])
            self.assertEqual(security.api.SetSecurityInfo(held.handle,1,4|0x80000000,None,None,pointer,None),0)
            foreign=security.capture(held)
            try:
                result=self.apply();self.assertFalse(result['security_restored'])
                self.assertIn('foreign permissions',result['reason'])
                self.assertEqual(security.capture(held),foreign)
            finally:security.restore(held,intent['original_security'])

    def test_closed_without_registered_proof_is_not_adopted(self):
        original=cleanup._publish
        def fail(path,value):
            if value['phase']=='removed':raise RuntimeError('proof interruption')
            return original(path,value)
        with patch.object(cleanup,'_publish',fail):result=self.apply()
        self.assertFalse(result['removed']);self.assertTrue(result['held']);self.assertFalse(self.path.exists())
        self.assertEqual(self.apply()['phase'],'interrupted-held')

    def test_restore_failure_is_explicit_hold(self):
        with patch.object(cleanup.LifecycleFileDelete,'dispose',side_effect=RuntimeError('native refusal')),\
             patch.object(cleanup.Security,'restore',side_effect=RuntimeError('restore refused')):result=self.apply()
        self.assertFalse(result['security_restored']);self.assertIn('restoration held',result['reason'])
        intent,_=cleanup._read(self.receipt)
        with NativeItem(self.path,writable_security=True) as item:
            self.assertEqual(item.facts['identity'],self.facts['identity']);Security().restore(item,intent['original_security'])


if __name__=='__main__':unittest.main()
