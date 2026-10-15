"""Initialized catalog reads under a real private SQLite writer; no user data."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
import groups
import scanner
from merge_service import MergeService
from web_server import BrowserServer

AREA=Path(__file__).resolve().parents[1]/'scratch'/'status-read-contention-fixtures'
AREA.mkdir(parents=True,exist_ok=True)

class StatusReadContentionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA)
        self.root=Path(self.temp.name)
        self.database=self.root/'private.sqlite3'
        self.roots={name:str(self.root/name) for name in ('Audiobooks','Podcasts','Ebooks')}
        for root in self.roots.values():Path(root).mkdir()
        self.inventory=scanner.Inventory(self.database,self.roots)
        with scanner.connect(self.database) as db:
            groups.sync(db,self.roots['Audiobooks'])
        self.holder=None;self.server=None
    def tearDown(self):
        if self.holder:
            self.holder.rollback();self.holder.close()
        if self.server:
            self.server.merge.automatic.close(2)
            self.server.merge.jobs.close(2)
            self.server.server_close()
        self.temp.cleanup()
    def writer(self):
        self.holder=sqlite3.connect(self.database,timeout=.05)
        self.holder.execute('BEGIN IMMEDIATE')
        self.holder.execute('UPDATE book_catalog_revision SET revision=revision WHERE id=1')
    def test_initialized_setup_does_not_request_writer_reservation(self):
        self.writer()
        with scanner.connect(self.database,timeout=.05) as db:
            before=db.total_changes
            groups.setup(db)
            self.assertEqual(db.total_changes,before)
            self.assertEqual(db.execute('SELECT revision FROM book_catalog_revision WHERE id=1').fetchone()[0],0)
    def test_initialized_group_sync_succeeds_query_only(self):
        with scanner.connect(self.database) as db:
            db.execute('PRAGMA query_only=ON')
            groups.sync(db,self.roots['Audiobooks'])
            self.assertEqual(db.total_changes,0)
    def test_missing_singleton_is_still_initialized_without_resetting_existing(self):
        with scanner.connect(self.database) as db:
            db.execute('DELETE FROM book_catalog_revision WHERE id=1')
            groups.setup(db)
            self.assertEqual(db.execute('SELECT revision FROM book_catalog_revision WHERE id=1').fetchone()[0],0)
            db.execute('UPDATE book_catalog_revision SET revision=9 WHERE id=1')
            groups.setup(db)
            self.assertEqual(db.execute('SELECT revision FROM book_catalog_revision WHERE id=1').fetchone()[0],9)
    def test_real_server_state_succeeds_while_private_writer_remains_held(self):
        def factory(inventory,cache):
            merge=MergeService(inventory,cache)
            merge.start_retention=lambda admission:None
            return merge
        self.server=BrowserServer(('127.0.0.1',0),self.inventory,factory)
        self.assertNotEqual(self.server.server_port,5210)
        before=self.server.state('Audiobooks')
        self.writer()
        during=self.server.state('Audiobooks')
        self.assertTrue(self.holder.in_transaction)
        self.assertEqual(during['automatic_processing'],before['automatic_processing'])
        self.assertEqual(during['audiobook_jobs'],before['audiobook_jobs'])

if __name__=='__main__':unittest.main()
