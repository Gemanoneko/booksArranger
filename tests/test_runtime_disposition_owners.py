"""Actual catalog-owner worker admission and common native guard integration."""
import os
from pathlib import Path
import sqlite3
import threading
import unittest
import uuid

from catalog_owner import catalog_lock
from native_io import VerifiedFile,BoundaryError
from runtime_disposition_owners import admit_catalog,context_for


@unittest.skipUnless(os.name=='nt','Native Windows owner registry')
class RuntimeOwnerTests(unittest.TestCase):
    def setUp(self):
        import runtime_disposition_owners as owners
        from unittest.mock import patch
        isolation=patch.object(owners,'_support',[]);isolation.start();self.addCleanup(isolation.stop)
        root=Path(os.environ['BOOKS_QA_FIXTURE_ROOT'])
        self.area=root/('runtime-owner-'+uuid.uuid4().hex);self.area.mkdir()
        self.data=self.area/'Data';self.data.mkdir();self.database=self.data/'inventory.sqlite3'
        db=sqlite3.connect(self.database)
        try:db.execute('CREATE TABLE fixture(value)');db.commit()
        finally:db.close()
        self.source=self.area/'Source';self.source.mkdir()
        self.file=self.source/'book.bin';self.file.write_bytes(b'representative private book')

    def test_lease_without_normal_admission_has_no_journal_and_no_disposal(self):
        with catalog_lock(self.database,{'source':self.source}):
            with VerifiedFile(self.file,delete=True) as held:
                from native_io import FileRemovalRetained
                with self.assertRaises(FileRemovalRetained) as result:held.dispose()
                self.assertIn('admitted native catalog owner',result.exception.native_reason)
            self.assertFalse((self.data/'file-disposition-ledger').exists())
        self.assertEqual(self.file.read_bytes(),b'representative private book')

    def test_worker_thread_disposes_through_actual_retained_owner_and_restarts(self):
        errors=[]
        with catalog_lock(self.database,{'source':self.source}):
            self.assertTrue(admit_catalog(self.database))
            def worker():
                try:
                    with VerifiedFile(self.file,delete=True) as held:
                        handle=held.handle;held.dispose();self.assertEqual(held.handle,handle)
                except BaseException as error:errors.append(error)
            thread=threading.Thread(target=worker);thread.start();thread.join(10)
            self.assertFalse(thread.is_alive());self.assertFalse(errors,repr(errors))
            self.assertFalse(self.file.exists())
            self.assertEqual(len(list((self.data/'file-disposition-ledger').glob('*.closed.json'))),1)
        with self.assertRaisesRegex(RuntimeError,'admitted native catalog owner'):context_for(self.file)
        with catalog_lock(self.database,{'source':self.source}):self.assertTrue(admit_catalog(self.database))

    def test_unknown_scope_and_replaced_catalog_refused(self):
        renamed=self.database.with_suffix('.old')
        self.database.rename(renamed);renamed.rename(self.database)
        with catalog_lock(self.database,{'source':self.source}):
            admit_catalog(self.database)
            with self.assertRaisesRegex(RuntimeError,'admitted native catalog owner'):context_for(self.area/'foreign.bin')
            with self.assertRaises(OSError):self.database.rename(self.database.with_suffix('.old'))
        self.database.rename(renamed);renamed.rename(self.database)
