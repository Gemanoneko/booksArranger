"""Preservation extends AAC copy mode without changing existing ALAC routing."""
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
import audio_pipeline as pipeline

class M4BDispatchTests(unittest.TestCase):
    def invoke(self,codec):
        manifest={'sources':[{'size':123,'path':'private/source.m4b'}],
                  'metadata':{'title':'Fixture','canonical_author':'Author'},'source_chapters':[]}
        encoding=pipeline.choose_automatic_encoding([(codec,'44100',2,'64000','stereo')],single_m4b=True)
        self.assertEqual(encoding['mode'],'copy');self.assertEqual(encoding['codec'],codec)
        return pipeline._encode_inputs(manifest,Path('private'),['source.m4b'],[1],Path('private/cover.png'),
          threading.Event(),lambda *_:None,encoding,['source.m4b'])
    def test_aac_single_m4b_uses_preservation_before_any_remux(self):
        with patch.object(pipeline.shutil,'disk_usage',return_value=type('Space',(),{'free':10**12})()),patch.object(pipeline.shutil,'which',return_value='private/ffmpeg.exe'),patch.object(pipeline,'write_generated'),patch.object(pipeline,'_preserve_single_m4b',return_value=('candidate','receipt')) as preserve,patch.object(pipeline,'run_owned') as remux:
            self.assertEqual(self.invoke('aac'),('candidate','receipt'))
            preserve.assert_called_once();remux.assert_not_called()
    def test_alac_keeps_existing_strict_remux_path(self):
        class ExistingRemuxReached(Exception):pass
        with patch.object(pipeline.shutil,'disk_usage',return_value=type('Space',(),{'free':10**12})()),patch.object(pipeline.shutil,'which',return_value='private/ffmpeg.exe'),patch.object(pipeline,'write_generated'),patch.object(pipeline,'source_chapters',return_value=[]),patch.object(pipeline,'_preserve_single_m4b') as preserve,patch.object(pipeline,'run_owned',side_effect=ExistingRemuxReached) as remux:
            with self.assertRaises(ExistingRemuxReached):self.invoke('alac')
            preserve.assert_not_called();remux.assert_called_once()
            arguments=remux.call_args.args[0]
            self.assertIn('-c:a',arguments);self.assertEqual(arguments[arguments.index('-c:a')+1],'copy')
    def test_single_candidate_uses_existing_lifecycle_and_cleanup_role_contract(self):
        from working_lifecycle import GENERATED
        from storage_cleanup import StorageCleanup
        name=pipeline.PRESERVATION_CANDIDATE_NAME
        self.assertIsNotNone(GENERATED.fullmatch(name))
        self.assertTrue(StorageCleanup.working_name({},name))

if __name__=='__main__':unittest.main()
