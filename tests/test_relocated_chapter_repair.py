"""Actual AAC/chapter consumer checks in private fixtures; no live relocation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import threading
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_merge_service as fixtures
from test_relocated_replacement import install_binding
from audio_pipeline import digest
from chapter_repair import restore,recover
from publication_binding import PublicationBindings

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'relocated-chapter'
AREA.mkdir(parents=True,exist_ok=True)


class RelocatedChapter(unittest.TestCase):
    ready=fixtures.MergeTests.ready
    wait=fixtures.MergeTests.wait

    def setUp(self):
        def retained(*args,**kwargs):
            kwargs['dir']=AREA
            return SimpleNamespace(name=tempfile.mkdtemp(*args,**kwargs),cleanup=lambda:None)
        with patch.object(fixtures,'AREA',AREA),patch.object(fixtures.tempfile,'TemporaryDirectory',side_effect=retained):fixtures.MergeTests.setUp(self)

    def tearDown(self):fixtures.MergeTests.tearDown(self)

    def test_actual_repair_uses_effective_root_and_cleanup_requires_own_relocated_journal(self):
        row=self.ready()
        row=self.service.reviews.tracks('Audiobooks',row['id'],row['revision'],row['track_order'],row['included'],True,True,False,evidence_note='Private exact source navigation proof')
        build=self.service.reviews.build_manifest
        def retain(*args,**kwargs):
            manifest=build(*args,**kwargs);manifest['cleanup_policy']['enabled']=False;return manifest
        with patch.object(self.service.reviews,'build_manifest',side_effect=retain):
            self.service.create('Audiobooks',row['id'],row['revision']);status=self.wait()
        self.assertEqual(status['completed'],1,status)
        parent=status['jobs'][0];frozen=copy.deepcopy(parent);manifest=parent['manifest'];validation=parent['output']['validation']
        bindings=PublicationBindings(self.inv.database)
        target=self.base/'sorted'/'Author'/'Book.m4b'
        install_binding(self.inv.database,parent['job_id'],'base',parent['output'],target)
        boundaries={'tracks':[{'source_path':source['path'],'sha256':source['sha256'],'pcm_frames':round(duration*44100),'pcm_rate':44100,'title':f'Часть {index+1}'} for index,(source,duration) in enumerate(zip(manifest['sources'],validation['source_durations']))]}
        repairs=self.base/'chapter-repairs'
        result=restore(parent,boundaries,repairs,threading.Event(),lambda:True,bindings=bindings)
        self.assertEqual(parent,frozen);self.assertEqual(Path(result['output']).parent,target.parent)
        self.assertEqual(digest(target),parent['output']['sha256']);self.assertEqual(len(result['validation']['chapters']),2)
        intent=json.loads(Path(result['journal']).read_text(encoding='utf-8').splitlines()[0])['data']
        self.assertEqual(intent['parent_output'],parent['output']['final_path']);self.assertEqual(intent['parent_effective_output'],str(target))
        self.assertEqual(intent['output_root'],str(target.parent));self.assertIsNotNone(intent['parent_location'])
        self.assertTrue(recover(result['journal'],repairs,threading.Event(),lambda:True,bindings=bindings)['recovered_from_owned_intent'])
        parent_view={'job_id':parent['job_id'],'manifest':manifest,'output':parent['output']}
        publication=self.service.publications._repairs(parent_view)[0]
        final=self.base/'sorted-repair'/'Independent Chapters.m4b'
        install_binding(self.inv.database,parent['job_id'],'Chaptersv2',publication['record'],final,publication['journal_sha256'])
        with self.assertRaises(ValueError):recover(result['journal'],repairs,threading.Event(),lambda:True,bindings=bindings)
        recovered=recover(result['journal'],repairs,threading.Event(),lambda:True,bindings=self.service.publication_bindings,publication_authorizer=self.service._repair_publication)
        self.assertEqual(recovered['output'],str(final));self.assertEqual(digest(final),publication['record']['sha256'])
        checked=Path(result['journal']).parent/'checked.m4b';checked_hash=digest(checked);checked_size=checked.stat().st_size
        with patch.object(self.service.storage_cleanup,'repair_location_guard',return_value=False),self.assertRaises(ValueError):
            self.service.storage_cleanup.discard_repair_copy(parent['job_id'],checked,checked_hash,checked_size)
        self.assertTrue(checked.exists());self.assertEqual(digest(checked),checked_hash)
        self.service.storage_cleanup.discard_repair_copy(parent['job_id'],checked,checked_hash,checked_size)
        self.assertFalse(checked.exists());self.assertEqual(digest(final),publication['record']['sha256'])
        self.assertEqual([digest(p) for p in self.sources],self.hashes)


if __name__=='__main__':unittest.main()
