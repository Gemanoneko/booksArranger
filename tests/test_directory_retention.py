"""Actual same-volume original package retention, no recursive deletion."""
import os
import ctypes
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from directory_retention import retain_directory_no_replace,DirectoryRetentionRefused
from native_io import DirectoryBoundary,VerifiedFile,kernel


@unittest.skipUnless(os.name=='nt','Native directory retention')
class DirectoryRetentionTests(unittest.TestCase):
    def test_native_rename_passes_terminated_utf16_with_byte_length(self):
        parent=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',Path(__file__).resolve().parents[1]/'scratch'))
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='retention-',dir=parent) as area:
            source=Path(area)/'Application';source.mkdir()
            retained=source.with_name('Retained-עברית-📚')
            with DirectoryBoundary(source.anchor,source) as boundary:
                identity=list(boundary.identities[-1][1:])
            expected=str(retained).encode('utf-16-le')
            api=kernel.SetFileInformationByHandle
            def inspect(handle,kind,buffer,size):
                self.assertEqual(kind,3)
                value=buffer._obj
                self.assertEqual(value.length,len(expected))
                self.assertFalse(value.flags)
                self.assertIsNone(value.root)
                self.assertGreaterEqual(size,type(value).name.offset+len(expected)+2)
                self.assertEqual(ctypes.string_at(ctypes.addressof(value)+type(value).name.offset,len(expected)+2),
                                 expected+b'\0\0')
                return api(handle,kind,buffer,size)
            with patch.object(kernel,'SetFileInformationByHandle',side_effect=inspect) as call:
                result=retain_directory_no_replace(source,retained,identity)
            call.assert_called_once()
            self.assertEqual(result['retained_identity'],identity)
            self.assertTrue(retained.is_dir())

    def test_original_native_file_ids_survive_with_known_members_held(self):
        parent=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',Path(__file__).resolve().parents[1]/'scratch'))
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='package-retention-',dir=parent) as area:
            root=Path(area);source=root/'Application';source.mkdir()
            known=source/'known.exe';known.write_bytes(b'private original package')
            (source/'unknown-user-file').write_bytes(b'preserved by whole directory retention')
            with DirectoryBoundary(source.anchor,source) as boundary:identity=list(boundary.identities[-1][1:])
            retained=root/('RetainedApplication-'+str(uuid.uuid4()))
            with VerifiedFile(known) as held:
                before=held.facts()
                with self.assertRaises(DirectoryRetentionRefused):retain_directory_no_replace(source,retained,identity)
                self.assertTrue(known.exists())
            result=retain_directory_no_replace(source,retained,identity)
            with VerifiedFile(retained/'known.exe') as held:
                self.assertTrue(result['original_preserved'])
                self.assertEqual(result['retained_identity'],identity)
                self.assertNotEqual(result['new_source_identity'],identity)
                self.assertEqual(held.facts(),before)
                with VerifiedFile(retained/'known.exe') as restored:self.assertEqual(restored.facts(),before)
                self.assertEqual((retained/'unknown-user-file').read_bytes(),b'preserved by whole directory retention')
                self.assertEqual(list(source.iterdir()),[])
            with self.assertRaises(DirectoryRetentionRefused):retain_directory_no_replace(source,retained,result['new_source_identity'])
            with self.assertRaises(DirectoryRetentionRefused):retain_directory_no_replace(source,root/'wrong-identity',[1,2,3])
            self.assertTrue((retained/'known.exe').exists())


if __name__=='__main__':unittest.main()
