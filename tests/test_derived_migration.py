"""Concrete private chapter migration; no synthetic receipt/cache/ledger proof."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

import test_merge_service as fixtures
from audio_pipeline import digest
from catalog_owner import catalog_lock
from chapter_repair import restore
from migration_operation import MigrationOperation
from migration_planning import prepare,write_plan
from scanner import connect

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'derived-migration'


class DerivedMigration(unittest.TestCase):
    ready=fixtures.MergeTests.ready
    wait=fixtures.MergeTests.wait

    def setUp(self):
        AREA.mkdir(parents=True,exist_ok=True)
        def retained(*args,**kwargs):
            kwargs['dir']=AREA
            return SimpleNamespace(name=tempfile.mkdtemp(*args,**kwargs),cleanup=lambda:None)
        with patch.object(fixtures,'AREA',AREA),patch.object(fixtures.tempfile,'TemporaryDirectory',side_effect=retained):fixtures.MergeTests.setUp(self)
        self.service_closed=False

    def tearDown(self):
        if not self.service_closed:self.service.close()
        # Session evidence is retained for Sergei's manual cleanup.

    def test_uncached_real_corrected_chapters_are_the_only_active_publication_moved(self):
        row=self.ready()
        row=self.service.reviews.tracks('Audiobooks',row['id'],row['revision'],row['track_order'],row['included'],True,True,False,evidence_note='Private original sources retained for exact corrected navigation')
        build=self.service.reviews.build_manifest
        def retain_sources(*args,**kwargs):
            manifest=build(*args,**kwargs);manifest['cleanup_policy']['enabled']=False;return manifest
        with patch.object(self.service.reviews,'build_manifest',side_effect=retain_sources):
            self.service.create('Audiobooks',row['id'],row['revision']);status=self.wait()
        self.assertEqual(status['completed'],1,status)
        parent=status['jobs'][0];frozen_parent=copy.deepcopy(parent);manifest=parent['manifest'];validation=parent['output']['validation']
        self.assertEqual(validation['chapters'],[])
        boundaries={'tracks':[{'source_path':source['path'],'sha256':source['sha256'],'pcm_frames':round(duration*44100),'pcm_rate':44100,'title':f'Часть {index+1}'} for index,(source,duration) in enumerate(zip(manifest['sources'],validation['source_durations']))]}
        corrected=restore(parent,boundaries,self.base/'chapter-repairs',threading.Event(),lambda:True)
        self.assertEqual(parent,frozen_parent);current=Path(corrected['output']);journal=Path(corrected['journal'])
        self.assertEqual(len(corrected['validation']['chapters']),2);self.assertEqual(digest(current),corrected['validation']['sha256'])
        journal_bytes=journal.read_bytes();journal_sha=hashlib.sha256(journal_bytes).hexdigest()
        base=Path(parent['output']['final_path']);base_bytes=base.read_bytes()
        with connect(self.inv.database) as db:
            original_job=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],)).fetchone())
            cached=db.execute('SELECT * FROM verified_outputs WHERE path=? AND sha256=?',(os.path.normcase(str(current)),corrected['validation']['sha256'])).fetchone()
        self.assertIsNone(cached,'Derived fixture must be genuinely uncached; do not seed verification to bypass admission')
        roots={name:str(path) for name,path in self.inv.roots.items()};target=self.base/'final-sorted';target.mkdir()
        self.service.close();self.service_closed=True
        guard_roots=dict(roots,**{'Audiobook output':str(target)})
        with catalog_lock(self.inv.database,guard_roots):
            plan=prepare(self.inv.database,roots,[roots['Audiobooks']],str(target))
        self.assertEqual(plan['held'],[],plan)
        self.assertEqual(len(plan['publications']),1,plan)
        entry=plan['publications'][0]
        self.assertEqual(entry['kind'],'Chaptersv2');self.assertEqual(entry['source'],str(current))
        self.assertEqual(plan['active_variant_counts'],{'Chaptersv2':1});self.assertEqual(plan['planned_bytes'],current.stat().st_size)
        self.assertNotIn(str(base),{item['source'] for item in plan['publications']})
        plans=AREA/'reviewed-plans';plans.mkdir(exist_ok=True)
        receipt=write_plan(plans/(str(uuid.uuid4())+'.json'),plan)
        operation=MigrationOperation(self.inv.database,plan['roots'],receipt['plan'],receipt['sha256'])
        with patch.object(operation,'_authorized_chapter',wraps=operation._authorized_chapter) as authorized:
            result=operation.run(entry['publication_id'])
        self.assertGreater(authorized.call_count,0,'Concrete operator must freshly authorize the real completed chapter journal')
        self.assertEqual(result['outcome'],'moved');self.assertTrue(result['verified']);self.assertEqual(result['stage'],'complete')
        destination=Path(entry['destination']);self.assertTrue(destination.is_file());self.assertFalse(current.exists())
        self.assertEqual(digest(destination),corrected['validation']['sha256']);self.assertEqual(base.read_bytes(),base_bytes)
        self.assertEqual(journal.read_bytes(),journal_bytes);self.assertEqual([digest(p) for p in self.sources],self.hashes)
        self.assertEqual(len(list(target.rglob('*.m4b'))),1)
        with connect(self.inv.database) as db:
            self.assertEqual(dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent['job_id'],)).fetchone()),original_job)
            relocation=dict(db.execute('SELECT * FROM output_relocations WHERE publication_id=?',(entry['publication_id'],)).fetchone())
            rows=list(db.execute('SELECT publication_kind FROM output_relocations'))
        self.assertEqual([item[0] for item in rows],['Chaptersv2'])
        proof=json.loads(relocation['destination_verification_json']);media=proof['media_validation']
        self.assertEqual(media['kind'],'sealed_media_proof_reused');self.assertEqual(media['supported_validation_contract'],'books-authorized-chapter-output-v1')
        self.assertEqual(media['authoritative_repair_journal_sha256'],journal_sha)
        self.assertEqual(media['source_full_hash']['sha256'],corrected['validation']['sha256']);self.assertEqual(media['destination_full_hash']['sha256'],corrected['validation']['sha256'])
        self.assertTrue(proof['filesystem_durability']['parent_directory']['same_retained_parent_handle'])
        self.assertTrue(proof['filesystem_durability']['parent_directory']['supported'])


if __name__=='__main__':unittest.main()
