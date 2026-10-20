"""Actual native consumer fixtures, with synthetic relocation ledger histories.

These test consumers, generation guards and handle closure, not media migration
admission or durable filesystem guarantees. No live paths/catalog are used.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import shutil
import tempfile
import unittest
import uuid
from unittest.mock import patch

import test_replacement_jobs as fixtures
import test_publication_locations as ledger_fixtures
from publication_binding import PublicationBindings
import publication_locations as ledger
from native_io import DirectoryBoundary,VerifiedFile,BoundaryError
from scanner import connect
from replacement_media import prepare_replacement
from test_replacement_media import frozen_plan

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'relocated-replacement'
AREA.mkdir(parents=True,exist_ok=True)


def install_binding(database,job_id,kind,original,target,journal_sha=None):
    """Structural history fixture; real file identity/full bytes, no media clearance."""
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original['final_path'],target)
    driver=ledger_fixtures.PublicationLocationsTests()
    with connect(database) as db,DirectoryBoundary(target.parent,target.parent) as boundary,VerifiedFile(target) as file:
        ledger.initialize(db);driver.db=db;driver.job=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone())
        driver.original=copy.deepcopy(original);driver.target=str(target.parent);driver.destination=str(target)
        driver.target_identity=file.facts()['identity'];driver.target_parents=[list(v) for v in boundary.identities]
        routing={'routing_policy_version':'fixture-explicit-v2','source_fingerprint':'private-consumer-fixture'}
        if journal_sha:routing['repair_journal_sha256']=journal_sha
        row=ledger.plan(db,driver.job,kind,original,driver.target,driver.destination,routing)
        row=driver.advance(row,'location_committed')
        row=ledger.transition(db,row['publication_id'],row['generation'],'complete',{'outcome':'copied_verified_original_retained','reason':'Consumer fixture keeps original until its own guarded retirement'})
        return row


class RelocatedReplacement(unittest.TestCase):
    # Reuse the existing private SQL/native setup without inheriting its tests.
    record=fixtures.ReplacementTests.record
    insert_job=fixtures.ReplacementTests.insert_job
    admit=fixtures.ReplacementTests.admit
    publish=fixtures.ReplacementTests.publish

    def setUp(self):
        def owned(*args,**kwargs):
            kwargs['dir']=AREA
            return SimpleNamespace(name=tempfile.mkdtemp(*args,**kwargs),cleanup=lambda:None)
        with patch.object(fixtures.tempfile,'TemporaryDirectory',side_effect=owned):fixtures.ReplacementTests.setUp(self)
        self.bindings=PublicationBindings(self.db);self.publications.bindings=self.bindings;self.retire.bindings=self.bindings

    def tearDown(self):fixtures.ReplacementTests.tearDown(self)

    def relocate(self,relation):
        repairs=self.publications._repairs({'job_id':self.parent_id,'manifest':self.parent_manifest,'output':self.parent_output})
        records=[('base',self.parent_output,None)]+[('Chaptersv2' if r['corrected'] else 'Chapters',r['record'],r['journal_sha256']) for r in repairs]
        destinations={}
        for index,(kind,original,journal) in enumerate(records):
            target=self.root/'sorted'/kind/f'Independently routed {index}.m4b'
            install_binding(self.db,self.parent_id,kind,original,target,journal)
            destinations[original['final_path']]=target
        install_binding(self.db,self.new_id,'replacement',self.new_output,self.root/'sorted'/'replacement'/'Current.m4b')
        effective,_=self.bindings.current(self.new_output,'replacement')
        with connect(self.db) as db:db.execute('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)',(effective['final_path'],self.new_id,'output',self.new_output['sha256'],self.new_output['size']))
        return destinations

    def test_three_independent_locations_retire_without_rewriting_original_receipts(self):
        relation=self.publish();before=copy.deepcopy(relation);destinations=self.relocate(relation)
        with self.publications.protect_former(relation,self.parent_row) as former:
            self.assertEqual(set(former),{str(p) for p in self.old})
            self.assertEqual({v['kind'] for v in former.values()},{'base','Chapters','Chaptersv2'})
            self.assertEqual(len({v['envelope']['publication_id'] for v in former.values()}),3)
        result=self.retire.run(relation)
        self.assertEqual(result['state'],'completed');self.assertTrue(all(p.exists() for p in self.old))
        self.assertFalse(any(p.exists() for p in destinations.values()))
        for row in self.store.files(relation['id']):
            proof=json.loads(row['recovery_json']);self.assertTrue(proof['native_handle_closed'])
            self.assertEqual(proof['effective_retirement']['original']['final_path'],row['original_path'])
            self.assertEqual(proof['effective_retirement']['envelope']['generation'],7)
        self.assertEqual(result['approval_json'],before['approval_json']);self.assertEqual(result['previous_publication_json'],before['previous_publication_json'])
        with connect(self.db) as db:self.assertEqual(self.store.raw_job(db,self.parent_id),self.parent_row)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))

    def test_stale_independent_chapter_generation_refuses_before_native_disposal(self):
        relation=self.publish();destinations=self.relocate(relation)
        original=self.bindings.guard
        def stale(db,receipt,envelope,**kwargs):
            if kwargs.get('kind')=='Chapters':return False
            return original(db,receipt,envelope,**kwargs)
        with patch.object(self.bindings,'guard',side_effect=stale),self.assertRaises(BoundaryError):self.retire.run(relation)
        self.assertTrue(all(p.exists() for p in destinations.values()));self.assertTrue(all(p.exists() for p in self.old))

    def test_fresh_journal_hash_cannot_be_substituted_by_base_generation(self):
        relation=self.publish();destinations=self.relocate(relation)
        with connect(self.db) as db:
            row=dict(db.execute("SELECT * FROM output_relocations WHERE publication_kind='Chapters'").fetchone())
            accepted=json.loads(row['accepted_routing_json']);accepted['repair_journal_sha256']='f'*64
            db.execute('UPDATE output_relocations SET accepted_routing_json=? WHERE publication_id=?',(json.dumps(accepted),row['publication_id']))
        with self.assertRaises(ValueError):
            with self.publications.protect_former(relation,self.parent_row):pass
        self.assertTrue(all(p.exists() for p in destinations.values()))

    def test_replacement_plan_uses_exact_bound_destination_preserving_source_manifest(self):
        target=self.root/'sorted-plan'/'Renamed base.m4b'
        install_binding(self.db,self.parent_id,'base',self.parent_output,target)
        effective,envelope=self.bindings.current(self.parent_output,'base')
        parent={'state':'completed','manifest':copy.deepcopy(self.parent_manifest),'output':copy.deepcopy(self.parent_output)}
        before=copy.deepcopy(parent);plan=frozen_plan(self.sources,self.parent_id,[44100]*40)
        result=prepare_replacement(parent,str(uuid.uuid4()),plan,effective_output=effective,location_envelope=envelope)
        self.assertEqual(result['root'],self.parent_manifest['root']);self.assertEqual(result['output_root'],str(target.parent))
        self.assertEqual(result['destination'],str(target.with_name(target.stem+' - Final.m4b')));self.assertEqual(parent,before)
        changed=copy.deepcopy(effective);changed['final_path']=str(target.with_name('Unbound.m4b'))
        with self.assertRaises(ValueError):prepare_replacement(parent,str(uuid.uuid4()),plan,effective_output=changed,location_envelope=envelope)


if __name__=='__main__':unittest.main()
