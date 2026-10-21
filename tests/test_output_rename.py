"""Isolated real native moves, journal restart and exact duplicate cleanup.

Reuses the one tiny AAC fixture. No live catalog, NAS, app or source audio.
"""
import contextlib
import copy
import hashlib
import json
import os
import sqlite3
import unittest
from unittest.mock import patch

import publication_locations as locations
from output_rename import RenameWorker
from native_io import DirectoryBoundary,VerifiedFile
from test_output_migration import Harness,SimulatedCrash,native_id
import test_output_migration as migration_fixture


class OutputRenameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):migration_fixture.OutputMigrationTests.setUpClass.__func__(cls)

    def harness(self):
        h=Harness(self.seed,self.validation);self.addCleanup(h.close);return h

    def worker(self,h,action='rename'):
        @contextlib.contextmanager
        def lease(pubid):
            with h.lease(pubid) as owned:
                yield dict(owned,operation_strategy='rename',operation_plan_sha256='b'*64,move_action=action)
        def media(path,receipt,stop):
            # Same supported sealed-media contract as production. The worker
            # proves bytes on its retained handle; this callback never reopens
            # the name against its own protected DELETE capability.
            return {'kind':'sealed_media_proof_reused','supported_validation_contract':'books-audio-output-v1',
                'passed':True,'immutable_receipt_sha256':locations._digest(receipt),
                'validation_sha256':locations._digest(receipt['validation']),
                'full_content_sha256':receipt['sha256'],'size':receipt['size'],
                'details':{'actual_private_aac_validation':copy.deepcopy(receipt['validation'])}}
        return RenameWorker(h.database,operation_lease=lease,media_verify=media,invalidate=h.invalidate,fault=h.fault)

    def test_real_rename_keeps_native_file_and_immutable_history_without_copy(self):
        h=self.harness();before=dict(h.job);old_id=native_id(h.old)
        with patch('output_migration.MigrationWorker._copy',side_effect=AssertionError('No copy allowed')):
            result=self.worker(h).run(h.pubid)
        self.assertEqual(result['outcome'],'moved');self.assertTrue(result['verified'])
        self.assertFalse(h.old.exists());self.assertEqual(native_id(h.final),old_id)
        self.assertEqual(h.final.read_bytes(),self.seed);self.assertEqual(h.job,before);h.assert_sources(self)
        stages=[r[0] for r in h.db.execute("SELECT to_stage FROM migration_events WHERE outcome='transition' ORDER BY event_id")]
        self.assertEqual(stages,['planned','rename_intent','renamed','location_committed','complete'])
        repeated=self.worker(h).run(h.pubid);self.assertEqual(repeated['outcome'],'moved')
        self.assertEqual(h.db.execute('SELECT count(*) FROM invalidations').fetchone()[0],1)

    def test_every_durable_move_boundary_and_native_gap_reconcile_exact_file(self):
        for point in ('after_rename_intent','after_native_rename_before_journal','after_renamed','before_location_committed_commit','after_location_committed','after_complete'):
            with self.subTest(point=point):
                h=self.harness();original_id=native_id(h.old);h.fault_at=point
                with self.assertRaises(SimulatedCrash):self.worker(h).run(h.pubid)
                self.assertTrue(h.old.exists() or h.final.exists());self.assertFalse(h.old.exists() and h.final.exists())
                result=self.worker(h).run(h.pubid)
                self.assertEqual(result['outcome'],'moved');self.assertFalse(h.old.exists())
                self.assertEqual(native_id(h.final),original_id);self.assertEqual(h.final.read_bytes(),self.seed);h.assert_sources(self)

    def test_unknown_collision_and_same_bytes_replacement_are_never_adopted(self):
        h=self.harness();h.final.write_bytes(self.seed)
        with self.assertRaisesRegex(ValueError,'destination exists'):self.worker(h).run(h.pubid)
        self.assertEqual(h.current()['stage'],'planned');self.assertEqual(h.old.read_bytes(),self.seed)
        h=self.harness();h.fault_at='after_native_rename_before_journal'
        with self.assertRaises(SimulatedCrash):self.worker(h).run(h.pubid)
        # Preserve the actual intended file under another name so the filesystem
        # cannot recycle its ID for the deliberately unrelated same-byte file.
        h.final.rename(h.final.with_suffix('.held'));h.final.write_bytes(self.seed)
        with self.assertRaisesRegex(ValueError,'exact intended native source'):self.worker(h).run(h.pubid)
        self.assertEqual(h.current()['stage'],'rename_intent');self.assertEqual(h.final.read_bytes(),self.seed)

    def test_original_corruption_refuses_before_rename_intent(self):
        h=self.harness();h.old.write_bytes(bytes([self.seed[0]^1])+self.seed[1:])
        with self.assertRaisesRegex(ValueError,'full held content differs'):self.worker(h).run(h.pubid)
        self.assertTrue(h.old.exists());self.assertFalse(h.final.exists());self.assertEqual(h.current()['stage'],'planned')

    def test_explicit_duplicate_cleanup_protects_sorted_and_reenters_after_delete_gap(self):
        for point in (None,'after_duplicate_cleanup_intent','after_duplicate_disposition','after_duplicate_removed'):
            with self.subTest(point=point):
                h=self.harness();h.directory_unavailable=True
                retained=h.worker().run(h.pubid);self.assertEqual(retained['outcome'],'copied_verified_original_retained')
                final_id=native_id(h.final);self.assertNotEqual(final_id,native_id(h.old));prefix=h.db.execute('SELECT * FROM migration_events ORDER BY event_id').fetchall()
                h.fault_at=point
                if point:
                    with self.assertRaises(SimulatedCrash):self.worker(h,'remove_verified_duplicate').run(h.pubid)
                result=self.worker(h,'remove_verified_duplicate').run(h.pubid)
                self.assertEqual(result['outcome'],'moved');self.assertFalse(h.old.exists())
                self.assertEqual(native_id(h.final),final_id);self.assertEqual(h.final.read_bytes(),self.seed);h.assert_sources(self)
                self.assertEqual(h.db.execute('SELECT * FROM migration_events ORDER BY event_id').fetchall()[:len(prefix)],prefix)

    def test_duplicate_cleanup_refuses_changed_sorted_before_old_disposition(self):
        h=self.harness();h.directory_unavailable=True;h.worker().run(h.pubid)
        h.final.write_bytes(bytes([self.seed[0]^1])+self.seed[1:])
        with self.assertRaisesRegex(ValueError,'full held content differs'):self.worker(h,'remove_verified_duplicate').run(h.pubid)
        self.assertEqual(h.old.read_bytes(),self.seed);self.assertEqual(h.current()['stage'],'complete')

    def test_exact_persisted_cache_avoids_hash_only_for_same_held_identity(self):
        h=self.harness();worker=self.worker(h)
        with h.lease(h.pubid) as lease:
            worker.db=h.db;worker.lease=lease;worker.current=h.current();worker.original=h.original;worker.publication_id=h.pubid
            with DirectoryBoundary(h.oldroot,h.old.parent) as boundary,VerifiedFile(h.old,delete=True) as file:
                facts=file.facts();observed=[h.old.stat().st_dev,h.old.stat().st_ino,h.old.stat().st_size,h.old.stat().st_mtime_ns]
                self.assertEqual(observed,[facts['dev'],facts['ino'],facts['size'],facts['modified']])
                h.db.execute('CREATE TABLE verified_outputs(path TEXT,sha256 TEXT,job_id TEXT,identity TEXT)')
                h.db.execute('INSERT INTO verified_outputs VALUES(?,?,?,?)',(os.path.normcase(str(h.old)),h.original['sha256'],h.current()['job_id'],json.dumps(observed)));h.db.commit()
                with patch.object(file,'chunks',side_effect=AssertionError('Exact accepted cache should avoid another hash')):
                    proof=worker._content(file,h.old,boundary,cached=True)
                self.assertEqual(proof['content_basis']['kind'],'accepted_persisted_verification_cache')
                observed[-1]+=1;h.db.execute('UPDATE verified_outputs SET identity=?',(json.dumps(observed),));h.db.commit()
                with patch.object(file,'chunks',wraps=file.chunks) as chunks:
                    proof=worker._content(file,h.old,boundary,cached=True);self.assertTrue(chunks.called)
                self.assertEqual(proof['content_basis']['kind'],'fresh_full_held_hash')


class ProductionMoveIntegrationTests(unittest.TestCase):
    def test_conversion_to_reviewed_native_move_keeps_job_receipt_and_recovery(self):
        from pathlib import Path
        import tempfile
        import test_merge_service as fixture
        from catalog_owner import catalog_lock
        from migration_planning import prepare,write_plan
        from migration_operation import MigrationOperation
        from publication_binding import PublicationBindings
        f=fixture.MergeTests();f.setUp();self.addCleanup(f.tearDown)
        book=f.ready();f.service.create('Audiobooks',book['id'],book['revision']);status=f.wait()
        self.assertEqual(status['completed'],1,status);output=copy.deepcopy(status['jobs'][0]['output'])
        f.service.close()
        recovery_root=f.service.cleanup.root
        recovery={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in recovery_root.rglob('*') if path.is_file()}
        with contextlib.closing(sqlite3.connect(f.inv.database)) as db:
            db.row_factory=sqlite3.Row;before=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(output['job_id'],)).fetchone())
            recovery_tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%cleanup%' OR name LIKE '%recovery%') ORDER BY name")]
            recovery_records={table:[tuple(r) for r in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid')] for table in recovery_tables}
        self.assertTrue(recovery_records) # Actual retention may already be empty after supported temporary cleanup.
        target=f.base/'Sorted Output';target.mkdir()
        with catalog_lock(f.inv.database,f.inv.roots):plan=prepare(f.inv.database,f.inv.roots,[f.inv.roots['Audiobooks']],str(target))
        self.assertEqual(len(plan['publications']),1,plan)
        plan['operation_strategy']=locations.RENAME_STRATEGY
        entry=plan['publications'][0];entry.update(move_action='rename',initial_generation=0)
        area=Path(tempfile.mkdtemp(dir=f.base.parent));published=write_plan(area/'reviewed-native-move.json',plan)
        old_id=native_id(Path(entry['source']))
        operation=MigrationOperation(f.inv.database,plan['roots'],published['plan'],published['sha256'],strategy='rename')
        with patch('output_migration.MigrationWorker._copy',side_effect=AssertionError('Copy prohibited')):
            result=operation.run(entry['publication_id'])
        self.assertEqual(result['outcome'],'moved');self.assertFalse(Path(entry['source']).exists())
        self.assertEqual(native_id(Path(entry['destination'])),old_id)
        self.assertEqual(operation.run(entry['publication_id'])['outcome'],'moved')
        with contextlib.closing(sqlite3.connect(f.inv.database)) as db:
            db.row_factory=sqlite3.Row;after=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(output['job_id'],)).fetchone())
            self.assertEqual(after,before)
            effective,envelope=PublicationBindings(f.inv.database).lookup(db,output,'base')
            self.assertEqual(effective['final_path'],entry['destination']);self.assertEqual(envelope['relocation']['stage'],'complete')
            self.assertEqual({table:[tuple(r) for r in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid')] for table in recovery_tables},recovery_records)
        self.assertEqual({str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in recovery_root.rglob('*') if path.is_file()},recovery)
        # The live profile already has Sorted configured before offline moves.
        # Reconstruct that effective policy; an old Inventory instance still
        # permitting only the old library must correctly reject another root.
        from scanner import Inventory
        from merge_service import MergeService
        from source_config import load_source_config
        extra=f.base/'OLD Audiobooks';extra.mkdir()
        settings_file=f.base/'audiobook-sources.json'
        settings_file.write_text(json.dumps({'audiobook_sources':[f.inv.roots['Audiobooks'],str(extra)],'audiobook_output_root':str(target)}),encoding='utf-8')
        config=load_source_config(json.loads(settings_file.read_text(encoding='utf-8')),f.inv.roots)
        f.inv=Inventory(f.inv.database,f.inv.roots,audiobook_sources=config.audiobook_sources,output_root=config.audiobook_output_root)
        f.service=MergeService(f.inv,f.base/'cache')
        self.assertEqual(f.inv.source_roots('Audiobooks'),config.audiobook_sources)
        self.assertEqual(f.inv.output_root,str(target))
        self.assertTrue(f.service._output_valid(output))
