"""Actual same-volume original package retention, no recursive deletion."""
import os
from pathlib import Path
import tempfile
import unittest
import uuid

from directory_retention import retain_directory_no_replace,DirectoryRetentionRefused
from native_io import DirectoryBoundary,VerifiedFile


@unittest.skipUnless(os.name=='nt','Native directory retention')
class DirectoryRetentionTests(unittest.TestCase):
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
