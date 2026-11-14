"""Typed cover operands preserve frozen jobs and only broaden cleanup holds."""
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

import audio_pipeline
from cleanup_ownership import OwnershipIndex,cover_protection_paths


class PortableCoverReads(unittest.TestCase):
    def setUp(self):
        self.old='C:\\private-origin\\data\\merge-cache\\cover.png'
        self.current='I:\\private-install\\Data\\merge-cache\\cover.png'
        self.external='Z:\\private-library\\source.m4b'
        self.manifest={'cover':{'path':self.old,'sha256':'a'*64},
                       'sources':[{'path':self.external}],
                       'destination':'Y:\\private-output\\book.m4b'}

    def test_read_operand_carries_cover_hash_without_rewriting_job(self):
        before=json.dumps(self.manifest,sort_keys=True)
        with patch.object(audio_pipeline,'managed_read_path',return_value=Path(self.current)) as resolve:
            self.assertEqual(audio_pipeline.reviewed_cover_path(self.manifest['cover']),Path(self.current))
            resolve.assert_called_once_with(self.old,'a'*64)
        self.assertEqual(json.dumps(self.manifest,sort_keys=True),before)

    def test_external_cover_read_is_not_relocated(self):
        with patch('storage_relocation_native.current',return_value=None):
            self.assertEqual(audio_pipeline.reviewed_cover_path({'path':self.external,'sha256':'b'*64}),Path(self.external))

    def test_ownership_index_protects_both_names_without_cover_io(self):
        namespace=SimpleNamespace(permitted=lambda path:path==self.old,current_path=Mock(return_value=self.current))
        with patch('storage_relocation_native.current',return_value=SimpleNamespace(namespace=namespace)):
            self.assertEqual(cover_protection_paths(self.manifest['cover']),(self.old,self.current))
            self.assertEqual(cover_protection_paths({'path':self.external}),(self.external,))
            with sqlite3.connect(':memory:') as db:
                db.execute('CREATE TABLE audio_jobs(job_id TEXT,manifest TEXT,state TEXT)')
                frozen=json.dumps(self.manifest,sort_keys=True)
                db.execute('INSERT INTO audio_jobs VALUES(?,?,?)',('queued-owner',frozen,'queued'))
                wanted={os.path.normcase(path) for path in (self.old,self.current,self.external)}
                self.assertEqual(OwnershipIndex().held(db,{'audio_jobs'},'another-job',None,wanted),wanted)
                self.assertEqual(db.execute('SELECT manifest FROM audio_jobs').fetchone()[0],frozen)


if __name__=='__main__':unittest.main()
