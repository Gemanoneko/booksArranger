"""Effective publication consumers hold a catalog generation lease."""
import copy
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from publication_binding import PublicationBindings
import test_publication_locations as fixture_module

class PublicationBindingTests(unittest.TestCase):
    def setUp(self):
        area=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'publication-binding'
        area.mkdir(parents=True,exist_ok=True)
        self.folder=tempfile.TemporaryDirectory(dir=area);self.addCleanup(self.folder.cleanup)
        self.path=str(Path(self.folder.name)/'catalog.sqlite')
        self.fixture=fixture_module.PublicationLocationsTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        db=sqlite3.connect(self.path);self.fixture.db.commit();self.fixture.db.backup(db);self.fixture.db.close();self.fixture.db=db;self.addCleanup(db.close)
        self.bindings=PublicationBindings(self.path)
    def commit_location(self):
        f=self.fixture;row=f.plan()
        for stage in ('copy_intent','copied','temporary_verified','final_publish_intent','final_published','location_committed'):row=f.next(row,stage)
        f.db.commit();return row
    def test_legacy_receipt_is_unchanged_without_binding(self):
        original=copy.deepcopy(self.fixture.original)
        with self.bindings.protect(original) as (effective,envelope):
            self.assertEqual(effective,original);self.assertIsNone(envelope)
        self.assertEqual(original,self.fixture.original)
    def test_committed_location_is_separate_and_generation_is_held(self):
        row=self.commit_location();original=copy.deepcopy(self.fixture.original)
        with self.bindings.protect(original) as (effective,envelope):
            self.assertEqual(effective['final_path'],self.fixture.destination)
            self.assertEqual(envelope['generation'],row['generation'])
            self.assertEqual(envelope['original_receipt'],original)
            self.assertFalse(envelope['verified'])
            other=sqlite3.connect(self.path,timeout=.01)
            try:
                with self.assertRaises(sqlite3.OperationalError):other.execute('BEGIN IMMEDIATE')
            finally:other.close()
        self.assertEqual(original,self.fixture.original)
        other=sqlite3.connect(self.path,timeout=.01);other.execute('BEGIN IMMEDIATE');other.rollback();other.close()
    def test_changed_original_cannot_fallback_to_old_path(self):
        self.commit_location();changed=copy.deepcopy(self.fixture.original);changed['size']+=1
        with self.assertRaises(ValueError):
            with self.bindings.protect(changed):pass
    def test_precommit_uses_original_and_still_holds_generation(self):
        row=self.fixture.plan();self.fixture.db.commit()
        with self.bindings.protect(self.fixture.original) as (effective,envelope):
            self.assertEqual(effective['final_path'],self.fixture.original['final_path'])
            self.assertEqual(envelope['stage'],'planned')

    def test_nested_parent_lease_reuses_same_generation_reservation(self):
        row=self.commit_location();original=self.fixture.original
        proof={'schema':'books-repair-parent-location-v1','immutable_receipt_sha256':__import__('publication_locations')._digest(original),'generation':row['generation'],'effective_location':__import__('publication_locations').resolve(self.fixture.db,self.fixture.job,'base',original)['effective_location']}
        with self.bindings.protect(original):
            with self.bindings.protect_parent(original['job_id'],proof) as (effective,envelope):
                self.assertEqual(effective['final_path'],self.fixture.destination)
                self.assertEqual(envelope['generation'],row['generation'])

    def enable_wal(self):
        self.fixture.db.commit()
        self.assertEqual(self.fixture.db.execute('PRAGMA journal_mode=WAL').fetchone()[0],'wal')
        self.fixture.db.execute('CREATE TABLE unrelated_metadata (value TEXT)')
        self.fixture.db.commit()
    def test_wal_view_allows_unrelated_metadata_commit(self):
        self.enable_wal();self.commit_location()
        with self.bindings.protect(self.fixture.original):
            with contextlib.closing(sqlite3.connect(self.path,timeout=.1)) as other:
                other.execute('INSERT INTO unrelated_metadata VALUES (?)',('saved while hashing',));other.commit()
        self.assertEqual(self.fixture.db.execute('SELECT value FROM unrelated_metadata').fetchone()[0],'saved while hashing')
    def test_wal_view_fresh_connection_rejects_illegal_generation_change(self):
        self.enable_wal();row=self.commit_location()
        with self.assertRaises(ValueError):
            with self.bindings.protect(self.fixture.original):
                with contextlib.closing(sqlite3.connect(self.path,timeout=.1)) as other:
                    other.execute('UPDATE output_relocations SET generation=generation+1');other.commit()
    def test_nested_wal_views_share_snapshot_but_reject_external_drift(self):
        self.enable_wal();self.commit_location()
        with self.assertRaises(ValueError):
            with self.bindings.protect(self.fixture.original) as (_,outer):
                with self.bindings.protect(self.fixture.original) as (_,inner):
                    self.assertEqual(inner,outer)
                    with contextlib.closing(sqlite3.connect(self.path,timeout=.1)) as other:
                        other.execute('UPDATE output_relocations SET generation=generation+1');other.commit()
                    snapshot=self.bindings.lookup(self.bindings.local.db,self.fixture.original)[1]
                    self.assertEqual(snapshot,outer)
    def test_live_owner_refuses_supported_offline_writer(self):
        from catalog_owner import catalog_lock
        roots={'Audiobooks':str(Path(self.folder.name)/'source')}
        with catalog_lock(self.path,roots):
            with self.assertRaises((OSError,RuntimeError,ValueError)):
                with catalog_lock(self.path,roots):pass
