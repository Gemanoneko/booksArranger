import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
import zipfile

ROOT=Path(__file__).absolute().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from build_fs_guard import BuildTree,remove_manifest_files
from native_io import BoundaryError,OwnedProcessJob
BASE=ROOT.parent/'build-guard-probes'

class GuardTests(unittest.TestCase):
    def fixture(self):
        with BuildTree(ROOT.parent) as guard:
            return guard.fresh(BASE)
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
            fresh=guard.fresh(root/'builds');manifest={'owned':guard.write(fresh/'owned',[b'known'])}
        (fresh/'unknown').write_bytes(b'private')
        bad={'owned':{'size':5,'sha256':'0'*64}}
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

if __name__=='__main__':unittest.main()
