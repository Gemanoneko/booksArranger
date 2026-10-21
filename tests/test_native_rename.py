"""Tiny private Windows rename fixtures; no installed library or NAS access.

The NAS64 case simulates only its existing documented identity fallback on a
local ordinary file. It does not certify a network provider's rename support.
"""
import copy
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_io as native

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'native-rename'


@unittest.skipUnless(os.name=='nt','Windows native rename required')
class NativeRename(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True,exist_ok=True)
        self.directory=Path(tempfile.mkdtemp(prefix='n-',dir=AREA))
        self.oldroot=self.directory/'old';self.newroot=self.directory/'sorted'
        self.oldroot.mkdir();self.newroot.mkdir()
        self.old=self.oldroot/'book.m4b';self.final=self.newroot/'Книга 🐉.m4b'
        self.content=b'private verified audiobook bytes\x00\x01';self.old.write_bytes(self.content)
        self.sha=hashlib.sha256(self.content).hexdigest()

    def invoke(self,source,old_boundary,new_boundary,**changes):
        arguments={'expected_identity':source.facts(),'expected_size':len(self.content),'expected_sha256':self.sha}
        arguments.update(changes)
        return native.rename_no_replace(source,self.final,old_boundary,new_boundary,**arguments)

    def leases(self):
        import contextlib
        @contextlib.contextmanager
        def held():
            with native.DirectoryBoundary(self.oldroot,self.oldroot) as old,native.DirectoryBoundary(self.newroot,self.newroot,rename_destination=True) as new,native.VerifiedFile(self.old,delete=True) as source:
                yield source,old,new
        return held()

    def test_real_same_volume_rename_preserves_held_handle_and_bytes(self):
        with self.leases() as (source,old,new):
            self.assertEqual(source.sha256(),self.sha)
            expected=source.facts()
            # Content was proved above; this primitive must not read/copy it again.
            with patch.object(native.VerifiedFile,'chunks',side_effect=AssertionError('Unexpected byte reread')):
                proof=self.invoke(source,old,new,expected_identity=expected)
            self.assertFalse(self.old.exists());self.assertEqual(source.sha256(),self.sha)
            self.assertEqual(source.facts(),expected)
            self.assertEqual(proof['source_native_before'],proof['destination_native'])
            self.assertTrue(proof['old_absent']);self.assertTrue(proof['no_replace']);self.assertFalse(proof['copy_fallback'])
            self.assertTrue(proof['source_delete_handle_still_held']);self.assertTrue(proof['named_read_handle_checked_closed'])
            with self.assertRaises(native.FileInUse):
                with native.VerifiedFile(self.final):pass
        self.assertEqual(self.final.read_bytes(),self.content)

    def test_rename_leaf_and_ancestors_still_deny_delete_rename_and_remove(self):
        def denied_delete(path):
            handle=native.kernel.CreateFileW(str(path),0x10000|0x81,7,None,3,0x02000000|0x00200000,None)
            error=ctypes.get_last_error()
            if handle!=ctypes.c_void_p(-1).value:
                native.kernel.CloseHandle(handle)
                self.fail('Protected directory unexpectedly grants DELETE')
            self.assertEqual(error,32)
        with self.leases() as (source,old,new):
            for directory in (self.newroot,self.directory):
                denied_delete(directory)
                with self.assertRaises(OSError) as caught:os.rename(directory,directory.with_name(directory.name+'-moved'))
                self.assertEqual(caught.exception.winerror,32)
            with self.assertRaises(OSError) as caught:os.rmdir(self.newroot)
            self.assertEqual(caught.exception.winerror,32)
            source.sha256();self.invoke(source,old,new)
            self.assertEqual(source.sha256(),self.sha)
            denied_delete(self.newroot);denied_delete(self.directory)

    def test_rename_option_changes_only_exact_destination_leaf_sharing(self):
        calls=[];original=native.kernel.CreateFileW
        def observe(path,access,share,*rest):
            calls.append((str(path),access,share))
            return original(path,access,share,*rest)
        with patch.object(native.kernel,'CreateFileW',side_effect=observe):
            with native.DirectoryBoundary(self.newroot,self.newroot,rename_destination=True) as boundary:
                boundary.revalidate()
        self.assertTrue(calls)
        for path,access,share in calls:self.assertEqual(share,3 if path==str(self.newroot) else 1)
        calls.clear()
        with patch.object(native.kernel,'CreateFileW',side_effect=observe):
            with native.DirectoryBoundary(self.newroot,self.newroot):pass
        self.assertTrue(all(share==1 for _,_,share in calls))
        with self.assertRaises(native.BoundaryError):native.DirectoryBoundary(self.newroot,self.newroot,rename_destination=1)
        with self.assertRaises(native.BoundaryError):native.DirectoryBoundary(self.newroot,self.newroot,writable_parent=True,rename_destination=True)

    def test_existing_destination_preserves_both(self):
        self.final.write_bytes(b'other output')
        with self.leases() as (source,old,new),self.assertRaises(FileExistsError):self.invoke(source,old,new)
        self.assertEqual(self.old.read_bytes(),self.content);self.assertEqual(self.final.read_bytes(),b'other output')

    def test_missing_delete_capability_refuses(self):
        with native.DirectoryBoundary(self.oldroot,self.oldroot) as old,native.DirectoryBoundary(self.newroot,self.newroot,rename_destination=True) as new,native.VerifiedFile(self.old) as source:
            with self.assertRaisesRegex(native.BoundaryError,'DELETE capability'):self.invoke(source,old,new)
        self.assertTrue(self.old.exists());self.assertFalse(self.final.exists())

    def test_changed_expected_identity_refuses(self):
        with self.leases() as (source,old,new):
            expected=copy.deepcopy(source.facts());expected['ino']+=1
            with self.assertRaisesRegex(native.BoundaryError,'complete checked identity'):self.invoke(source,old,new,expected_identity=expected)
        self.assertTrue(self.old.exists());self.assertFalse(self.final.exists())

    def test_hardlinked_source_refuses(self):
        os.link(self.old,self.oldroot/'other-link.m4b')
        with self.leases() as (source,old,new),self.assertRaisesRegex(native.BoundaryError,'unique ordinary'):self.invoke(source,old,new)
        self.assertTrue(self.old.exists());self.assertFalse(self.final.exists())

    def test_reparse_attribute_fault_refuses_before_rename(self):
        original=native.kernel.GetFileInformationByHandle
        with self.leases() as (source,old,new):
            expected=source.facts()
            def attributes(handle,info):
                result=original(handle,info)
                if handle==source.handle:ctypes.cast(info,ctypes.POINTER(native.FileInfo)).contents.attributes|=0x400
                return result
            with patch.object(native.kernel,'GetFileInformationByHandle',side_effect=attributes),self.assertRaisesRegex(native.BoundaryError,'unique ordinary'):
                self.invoke(source,old,new,expected_identity=expected)
        self.assertTrue(self.old.exists());self.assertFalse(self.final.exists())

    def test_native_parent_volume_mismatch_refuses(self):
        original=native.kernel.GetFileInformationByHandle
        with self.leases() as (source,old,new):
            expected=source.facts()
            def volume(handle,info):
                result=original(handle,info)
                if handle==new.handles[-1]:ctypes.cast(info,ctypes.POINTER(native.FileInfo)).contents.volume+=1
                return result
            with patch.object(new,'revalidate',return_value=None),patch.object(native.kernel,'GetFileInformationByHandle',side_effect=volume),self.assertRaisesRegex(native.BoundaryError,'matching native'):
                self.invoke(source,old,new,expected_identity=expected)
        self.assertTrue(self.old.exists());self.assertFalse(self.final.exists())

    def test_documented_rename_shape_root_null_absolute_utf16_and_no_fallback(self):
        captured={}
        class Header(ctypes.Structure):
            _fields_=[('replace',wintypes.BOOLEAN),('root',wintypes.HANDLE),('length',wintypes.DWORD),('name',wintypes.WCHAR*1)]
        def refuse(handle,kind,buffer,size):
            record=ctypes.cast(buffer,ctypes.POINTER(Header)).contents
            captured.update(kind=kind,replace=record.replace,root=record.root,length=record.length,
                path=ctypes.string_at(ctypes.addressof(record)+Header.name.offset,record.length).decode('utf-16-le'))
            ctypes.set_last_error(50);return False
        with self.leases() as (source,old,new),patch.object(native.kernel,'SetFileInformationByHandle',side_effect=refuse),patch.object(native.kernel,'MoveFileExW',side_effect=AssertionError('Copy/move fallback forbidden')):
            with self.assertRaisesRegex(native.BoundaryError,'Windows error 50'):self.invoke(source,old,new)
        self.assertEqual(captured,{'kind':3,'replace':0,'root':None,'length':len(str(self.final).encode('utf-16-le')),'path':str(self.final)})
        self.assertEqual(self.old.read_bytes(),self.content);self.assertFalse(self.final.exists())

    def test_os_cross_device_refusal_has_no_fallback(self):
        def refuse(*_):ctypes.set_last_error(17);return False
        with self.leases() as (source,old,new),patch.object(native.kernel,'SetFileInformationByHandle',side_effect=refuse):
            with self.assertRaisesRegex(native.BoundaryError,'Windows error 17'):self.invoke(source,old,new)
        self.assertTrue(self.old.exists());self.assertFalse(self.final.exists())

    def test_destination_collision_race_preserves_both(self):
        def collision(*_):
            self.final.write_bytes(b'arrived during rename');ctypes.set_last_error(183);return False
        with self.leases() as (source,old,new),patch.object(native.kernel,'SetFileInformationByHandle',side_effect=collision):
            with self.assertRaises(FileExistsError):self.invoke(source,old,new)
        self.assertEqual(self.old.read_bytes(),self.content);self.assertEqual(self.final.read_bytes(),b'arrived during rename')

    def test_post_rename_named_proof_failure_preserves_intent_without_recreation(self):
        original=native.kernel.CreateFileW
        def deny_name(path,*arguments):
            if str(path)==str(self.final):ctypes.set_last_error(5);return ctypes.c_void_p(-1).value
            return original(path,*arguments)
        with self.leases() as (source,old,new),patch.object(native.kernel,'CreateFileW',side_effect=deny_name):
            with self.assertRaisesRegex(native.RenamePostconditionError,'OS rename accepted'):self.invoke(source,old,new)
            self.assertEqual(source.sha256(),self.sha)
        self.assertFalse(self.old.exists());self.assertEqual(self.final.read_bytes(),self.content)

    def test_simulated_nas64_identity_floor_is_preserved_on_private_local_file(self):
        def unavailable(*_):ctypes.set_last_error(87);return False
        with self.leases() as (source,old,new),patch.object(native.kernel,'GetFileInformationByHandleEx',side_effect=unavailable):
            expected=source.facts()
            self.assertEqual(expected['identity_method'],'BY_HANDLE_FILE_INFORMATION64');self.assertEqual(expected['identity_api_error'],87)
            proof=self.invoke(source,old,new,expected_identity=expected)
            self.assertEqual(proof['destination_native'],expected)
        self.assertEqual(self.final.read_bytes(),self.content)

    def test_unknown_identity_error_refuses_without_rename(self):
        def unavailable(*_):ctypes.set_last_error(5);return False
        with self.leases() as (source,old,new):
            expected=source.facts()
            with patch.object(native.kernel,'GetFileInformationByHandleEx',side_effect=unavailable),self.assertRaises(native.BoundaryError):
                self.invoke(source,old,new,expected_identity=expected)
        self.assertTrue(self.old.exists());self.assertFalse(self.final.exists())


if __name__=='__main__':unittest.main(verbosity=2)
