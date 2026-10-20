"""Narrow writable-parent capability; default ancestry sharing never widens."""
import ctypes
import os
from pathlib import Path
import tempfile
import unittest
from native_io import DirectoryBoundary,BoundaryError,kernel,FileInfo
from ctypes import wintypes as W
AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'directory-flush'

class DirectoryFlushTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True,exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.parent=self.root/'target';self.parent.mkdir()
    def flush(self,b):
        kernel.FlushFileBuffers.argtypes=[W.HANDLE];kernel.FlushFileBuffers.restype=W.BOOL
        return bool(kernel.FlushFileBuffers(b.handles[-1]))
    def test_default_remains_readonly_and_write_parent_flushes_exact_identity(self):
        with DirectoryBoundary(self.root,self.parent) as default:
            original=default.identities;self.assertFalse(default.writable_parent);self.assertFalse(self.flush(default))
        with DirectoryBoundary(self.root,self.parent,writable_parent=True) as writable:
            self.assertEqual(writable.identities,original);self.assertTrue(self.flush(writable));writable.revalidate()
        self.assertEqual(writable.handles,[])
    def test_nested_same_parent_refuses_both_orders(self):
        for outer,inner in ((False,True),(True,False),(True,True)):
            with self.subTest(outer=outer,inner=inner),DirectoryBoundary(self.root,self.parent,writable_parent=outer):
                with self.assertRaises(BoundaryError):
                    with DirectoryBoundary(self.root,self.parent,writable_parent=inner):pass
        with DirectoryBoundary(self.root,self.parent,writable_parent=True):pass
    def test_held_write_parent_blocks_descendant_boundary_reopen(self):
        child=self.parent/'child';child.mkdir()
        with DirectoryBoundary(self.root,self.parent,writable_parent=True):
            with self.assertRaises(BoundaryError):
                with DirectoryBoundary(self.root,child):pass
        with DirectoryBoundary(self.root,child,writable_parent=True) as boundary:self.assertTrue(self.flush(boundary))
    def test_readonly_ancestor_and_distinct_writable_child_are_compatible(self):
        child=self.parent/'child';child.mkdir()
        with DirectoryBoundary(self.root,self.parent),DirectoryBoundary(self.root,child,writable_parent=True) as writable:
            self.assertTrue(self.flush(writable))
        with DirectoryBoundary(self.root,self.parent),DirectoryBoundary(self.root,self.parent):pass
    def test_distinct_sibling_boundaries_and_rename_denial(self):
        sibling=self.root/'other';sibling.mkdir()
        with DirectoryBoundary(self.root,self.parent,writable_parent=True),DirectoryBoundary(self.root,sibling,writable_parent=True):
            with self.assertRaises(OSError):self.parent.rename(self.root/'replaced')
        self.parent.rename(self.root/'after-close');self.assertTrue((self.root/'after-close').is_dir())
    def test_explicit_capability_rejects_nonboolean(self):
        for value in (1,None,'yes'):
            with self.assertRaises(BoundaryError):DirectoryBoundary(self.root,self.parent,writable_parent=value)
