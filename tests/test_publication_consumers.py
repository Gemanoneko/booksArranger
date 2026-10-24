"""Native private cleanup fixtures using a separately bound output location.

The structural migration proof is synthetic setup, not migration-worker/media QA.
"""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import publication_locations as p
from publication_binding import PublicationBindings
from native_io import DirectoryBoundary,VerifiedFile,BoundaryError
from scanner import connect
import test_storage_cleanup as storage_fixture
import test_publication_locations as ledger_fixture

class RelocatedCleanupTests(unittest.TestCase):
    def setUp(self):
        self.f=storage_fixture.RetentionTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        f=self.f;f.output['root']=str(f.library)
        cover=f.base/'cover.jpg';cover.write_bytes(Path(f.output['final_path']).read_bytes());f.manifest['cover']['path']=str(cover)
        f.manifest['metadata_facts']={'source_fingerprint':'fixture-fingerprint'}
        with connect(f.db) as db:
            db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=?,output=?,journal=? WHERE job_id=?',
              (p._packed(f.manifest),p._digest(f.manifest),p._packed(f.output),p._packed({'publication_intent':f.output}),f.job_id))
            p.initialize(db)
        self.bindings=PublicationBindings(f.db)
        f.storage.output_location=self.bindings.current;f.storage.output_location_guard=self.bindings.guard
        f.source.output_location=self.bindings.current;f.source.output_location_guard=self.bindings.guard
        self.old=Path(f.output['final_path']);self.target=f.base/'sorted';self.target.mkdir();self.final=self.target/'book.m4b'
        f.source.output_policy=lambda:(str(self.target),(str(f.library),))  # relocated into the sorted folder, outside the source (rulings 2 and 1a)
        self.final.write_bytes(self.old.read_bytes())
        helper=ledger_fixture.PublicationLocationsTests();helper.original=json.loads(p._packed(f.output))
        with DirectoryBoundary(self.target,self.final.parent) as b,VerifiedFile(self.final) as file:
            helper.target_identity=file.facts()['identity'];helper.target_parents=json.loads(p._packed(b.identities))
        with connect(f.db) as db:
            helper.db=db;helper.target=str(self.target);helper.destination=str(self.final)
            job=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(f.job_id,)).fetchone())
            row=p.plan(db,job,'base',f.output,str(self.target),str(self.final),{'routing_policy_version':'fixture','source_fingerprint':'fixture-fingerprint'})
            for stage in ('copy_intent','copied','temporary_verified','final_publish_intent','final_published','location_committed'):row=helper.next(row,stage)
        self.old.unlink() # Synthetic post-relocation state; never production media.
        # Private ownership marker remains bound to the exact updated manifest.
        (f.job/'ownership.json').write_text(p._packed({'job_id':f.job_id,'manifest':f.manifest}),encoding='utf-8')
    def test_storage_uses_effective_file_but_keeps_original_receipt(self):
        frozen=copy.deepcopy(self.f.output)
        self.f.storage.run(self.f.job_id)
        self.assertEqual(list(self.f.stage.iterdir()),[])
        self.assertTrue(self.final.exists());self.assertFalse(self.old.exists())
        self.assertEqual(self.f.output,frozen)
        self.assertTrue(all(Path(s['path']).exists() for s in self.f.sources))
    def test_source_retirement_resolves_output_and_keeps_source_root(self):
        f=self.f;f.full.update(manifest=f.manifest,output=f.output)
        f.retire()
        self.assertTrue(self.final.exists());self.assertTrue(all(not Path(s['path']).exists() for s in f.sources))
        with connect(f.db) as db:
            intent=json.loads(db.execute('SELECT intent FROM source_cleanup WHERE job_id=?',(f.job_id,)).fetchone()[0])
        self.assertEqual(intent['output'],json.loads(p._packed(f.output)))
        self.assertEqual(intent['manifest']['root'],str(f.library))
    def test_generation_change_refuses_before_any_staging_disposition(self):
        with patch.object(self.f.storage,'output_location_guard',return_value=False):
            with self.assertRaisesRegex(BoundaryError,'publication changed'):self.f.storage.run(self.f.job_id)
        self.assertTrue((self.f.stage/'checked.m4b').exists());self.assertTrue(self.final.exists())

    def test_same_bytes_replacement_of_destination_is_not_adopted(self):
        replacement=self.target/'unowned-replacement.m4b';replacement.write_bytes(self.final.read_bytes());replacement.replace(self.final)
        with self.assertRaisesRegex(BoundaryError,'native identity'):self.f.storage.run(self.f.job_id)
        self.assertTrue((self.f.stage/'checked.m4b').exists())
        self.assertTrue(all(Path(s['path']).exists() for s in self.f.sources))

# 0.21.3: this module's fixtures publish inside their own library; see sorted_fixture (Sergei's deletion rule).
def setUpModule():
    global _sorted_fixture
    from sorted_fixture import patch_merge_service
    _sorted_fixture = patch_merge_service()


def tearDownModule():
    _sorted_fixture.stop()

