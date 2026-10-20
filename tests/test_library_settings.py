import os
"""Source settings are additive, and offline sources do not block safe startup selection."""
import json
from pathlib import Path
import tempfile
import unittest
from desktop_settings import configure_sources
from scanner import DEFAULT_ROOTS
import web_server

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'library-settings-tests'

class SourceSettingsTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True,exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.audio=self.base/'audio';self.audio.mkdir()
        self.roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
    def test_new_source_file_preserves_existing_data_settings_and_refuses_overwrite(self):
        old=self.base/'desktop-settings.json';old.write_bytes(b'{"dataDir":"PRIVATE ORIGINAL","catalogMode":"existing"}')
        target=self.base/'audiobook-sources.json';extra=str(self.base/'offline');output=str(self.base/'sorted')
        configure_sources(target,self.roots,[str(self.audio),extra],output)
        self.assertEqual(json.loads(target.read_text())['audiobook_sources'],[str(self.audio),extra])
        before=old.read_bytes();created=target.read_bytes()
        with self.assertRaises(Exception):configure_sources(target,self.roots,[str(self.audio)],None)
        self.assertEqual(old.read_bytes(),before);self.assertEqual(target.read_bytes(),created)
    def test_invalid_overlap_creates_no_settings(self):
        target=self.base/'audiobook-sources.json'
        with self.assertRaises(ValueError):configure_sources(target,self.roots,[str(self.audio),str(self.audio/'child')],None)
        self.assertFalse(target.exists())
    def test_startup_guard_names_offline_second_source_and_output_without_opening_them(self):
        roots=self.base/'roots.json';roots.write_text(json.dumps(self.roots));database=self.base/'data';database.mkdir()
        extra=self.base/'offline';output=self.base/'sorted';seen=[]
        class Selected(Exception):pass
        def guard(db,configured,port):seen.append(configured);raise Selected()
        with self.assertRaises(Selected):web_server.main(['--database',str(database/'inventory.sqlite3'),'--roots-json',str(roots),'--audiobook-source',str(self.audio),'--audiobook-source',str(extra),'--audiobook-output-root',str(output)],startup_guard=guard,create_data=False)
        self.assertIn(str(extra),seen[0].values());self.assertIn(str(output),seen[0].values())
        self.assertFalse(extra.exists());self.assertFalse(output.exists());self.assertFalse((database/'inventory.sqlite3').exists())
    def test_real_packaged_catalog_guard_keeps_offline_source_readable(self):
        from scanner import Inventory
        from desktop_catalog import inspect_folder
        data=self.base/'data';data.mkdir();database=data/'inventory.sqlite3'
        extra=self.base/'offline';output=self.base/'sorted'
        inventory=Inventory(database,self.roots,audiobook_sources=[str(self.audio),str(extra)],output_root=str(output))
        inventory.stop()
        guarded=dict(self.roots,additional_audiobooks=str(extra),audiobook_output=str(output))
        result=inspect_folder(data,'existing',guarded)
        self.assertEqual(result['mode'],'existing')
        self.assertFalse(extra.exists());self.assertFalse(output.exists())
        self.assertEqual(inventory.candidates('Audiobooks')['total'],0)
if __name__=='__main__':unittest.main()
