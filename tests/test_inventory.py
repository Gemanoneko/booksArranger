import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import zipfile

from metadata import ScanStopped, propose, read_metadata, safe_name
from scanner import Inventory, connect

SCRATCH = Path(__file__).resolve().parents[1] / 'scratch' / 'test-fixtures'
SCRATCH.mkdir(parents=True, exist_ok=True)

class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.roots = {'Audiobooks': str(self.base / 'audio'),
                      'Podcasts': str(self.base / 'audio' / 'Podcasts'),
                      'Ebooks': str(self.base / 'ebooks')}
        for root in self.roots.values():
            Path(root).mkdir(parents=True, exist_ok=True)
        self.database = self.base / 'state' / 'inventory.sqlite3'
        self.calls = []
        def reader(path, kind, stop):
            self.calls.append(path)
            return {'title': Path(path).stem, 'author': 'Unverified Artist', 'tags': {'custom': 'Сведения'}}
        self.reader = reader

    def file(self, relative, data=b'fixture audio'):
        path = self.base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def run_scan(self, inventory, label='Audiobooks', resume=False):
        inventory.launch(label, resume)
        inventory.worker.join(timeout=10)
        self.assertFalse(inventory.worker.is_alive(), 'fixture scan exceeded its deadline')
        self.assertNotEqual(inventory.status(label)['state'], 'failed', inventory.last_error)

    def test_source_preservation_incremental_changes_and_deletion(self):
        first = self.file('audio/Unsorted/Book/01.mp3')
        second = self.file('audio/Old.mp3')
        podcast = self.file('audio/Podcasts/Show/Episode.mp3')
        hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (first,second,podcast)}
        inventory = Inventory(self.database, self.roots, self.reader)
        self.run_scan(inventory)
        rows = inventory.rows('Audiobooks')
        self.assertEqual({r['path'] for r in rows}, {str(first),str(second)})
        self.assertTrue(next(r for r in rows if r['path'] == str(first))['arrival'])
        self.assertTrue(all(r['preview']['confidence'] == 'Needs review' for r in rows))
        self.run_scan(inventory)
        self.assertEqual(inventory.status('Audiobooks')['reused'], 2)
        self.assertEqual(len(self.calls), 2)
        for path, expected in hashes.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
        inventory.save_review(self.roots['Audiobooks'],str(first), {'original_language':'Other','title':'Book','author':'King Stephen'})
        first.write_bytes(b'changed fixture content')
        second.unlink()  # Fixture only, never a real library.
        added = self.file('audio/New.mp3')
        self.run_scan(inventory)
        records = {r['path']:r for r in inventory.rows('Audiobooks')}
        self.assertEqual(records[str(second)]['missing'], 1)
        self.assertEqual(records[str(first)]['review'], None)
        self.assertIn(str(added), records)
        self.run_scan(inventory, 'Podcasts')
        self.assertEqual(inventory.rows('Podcasts')[0]['kind'], 'podcast')
        self.assertEqual(inventory.rows('Podcasts')[0]['preview']['path'], str(podcast))

    def test_stop_resume_after_restart_retains_completed_reads(self):
        first = self.file('audio/01.mp3')
        second = self.file('audio/02.mp3')
        entered = threading.Event()
        calls = []
        def controlled_reader(path, kind, stop):
            calls.append(path)
            if path == str(second):
                entered.set()
                if not stop.wait(timeout=5):
                    raise RuntimeError('test stop was never received')
                raise ScanStopped()
            return {'title': 'First', 'author': 'Existing author', 'tags': {}}
        inventory = Inventory(self.database,self.roots,controlled_reader)
        inventory.launch('Audiobooks')
        self.assertTrue(entered.wait(5))
        inventory.stop()
        inventory.worker.join(5)
        self.assertFalse(inventory.worker.is_alive())
        self.assertEqual(inventory.status('Audiobooks')['state'], 'stopped')
        self.assertEqual(len(inventory.rows('Audiobooks')), 1)
        resumed = Inventory(self.database,self.roots,self.reader)
        self.run_scan(resumed,resume=True)
        self.assertEqual(len(resumed.rows('Audiobooks')), 2)
        self.assertEqual(self.calls, [str(second)], 'completed first source should not be reread on continuation')
        self.assertEqual(calls.count(str(first)), 1)

    def test_offline_and_incomplete_scan_do_not_mark_missing(self):
        self.file('audio/01.mp3')
        inventory = Inventory(self.database,self.roots,self.reader)
        self.run_scan(inventory)
        audio = Path(self.roots['Audiobooks'])
        moved = self.base / 'offline-fixture'
        audio.rename(moved)
        self.run_scan(inventory)
        self.assertEqual(inventory.status('Audiobooks')['state'], 'offline')
        self.assertEqual(inventory.rows('Audiobooks')[0]['missing'], 0)
        audio.parent.mkdir(parents=True,exist_ok=True)
        moved.rename(audio)
        self.run_scan(inventory,resume=True)
        self.assertEqual(inventory.status('Audiobooks')['state'], 'completed')

    def test_crash_queue_recovery_and_database_source_guard(self):
        self.file('audio/01.mp3')
        inventory = Inventory(self.database,self.roots,self.reader)
        with connect(self.database) as connection:
            root = self.roots['Audiobooks']
            connection.execute("INSERT INTO jobs(root,label,generation,state) VALUES(?,?,1,'scanning')",(root,'Audiobooks'))
            connection.execute("INSERT INTO queue(root,generation,path,directory,state) VALUES(?,1,?,1,'running')",(root,root))
        recovered = Inventory(self.database,self.roots,self.reader)
        self.assertEqual(recovered.status('Audiobooks')['state'],'stopped')
        self.run_scan(recovered,resume=True)
        self.assertEqual(len(recovered.rows('Audiobooks')),1)
        with self.assertRaises(ValueError):
            Inventory(Path(self.roots['Audiobooks']) / 'illegal.sqlite3',self.roots)
        self.assertFalse((Path(self.roots['Audiobooks']) / 'illegal.sqlite3').exists())

    def test_metadata_error_visible_and_missing_reconciliation_suppressed(self):
        path = self.file('audio/bad.mp3')
        def bad_reader(*args):
            raise ValueError('fixture damaged metadata')
        inventory = Inventory(self.database,self.roots,bad_reader)
        self.run_scan(inventory)
        row = inventory.rows('Audiobooks')[0]
        self.assertEqual(row['preview']['confidence'], 'Read error')
        self.assertIn('fixture damaged', row['error'])
        self.assertEqual(inventory.status('Audiobooks')['state'],'completed with errors')
        self.assertTrue(path.exists())

    def test_stale_review_cannot_apply_to_changed_source(self):
        path = self.file('audio/book.mp3')
        inventory = Inventory(self.database,self.roots,self.reader)
        self.run_scan(inventory)
        row = inventory.rows('Audiobooks')[0]
        path.write_bytes(b'modified larger content')
        self.run_scan(inventory)
        with self.assertRaises(ValueError):
            inventory.save_review(row['root'],row['path'],{'title':'stale'},row['size'],row['modified'])

    def test_conflicting_ebook_editions_require_review(self):
        one = self.file('ebooks/one.epub')
        two = self.file('ebooks/two.epub')
        inventory = Inventory(self.database,self.roots,self.reader)
        self.run_scan(inventory,'Ebooks')
        review = {'original_language':'Other','title':'Book','author':'Author Name','series':'Cycle','number':'1','genre':'Fantasy','multi_author':True}
        for path in (one,two):
            inventory.save_review(self.roots['Ebooks'],str(path),review)
        self.assertTrue(all(r['preview']['confidence'] == 'Collision review' for r in inventory.rows('Ebooks')))

    def test_source_changing_during_read_invalidates_prior_review(self):
        path = self.file('audio/book.mp3')
        inventory = Inventory(self.database,self.roots,self.reader)
        self.run_scan(inventory)
        inventory.save_review(self.roots['Audiobooks'],str(path),{'original_language':'Other','title':'Old Book','author':'Old Author'})
        path.write_bytes(b'new arrival starts')
        def changing_reader(source,kind,stop):
            Path(source).write_bytes(b'new arrival continued downloading during metadata read')
            return {'title':'Different book','author':'Different author'}
        inventory.reader = changing_reader
        self.run_scan(inventory)
        row = inventory.rows('Audiobooks')[0]
        self.assertEqual(row['review'],None)
        self.assertEqual(row['preview']['confidence'],'Read error')
        self.assertEqual(row['preview']['path'],'')
        self.assertIn('changed during read',row['error'])

class MetadataTests(unittest.TestCase):
    def test_confirmed_paths_and_no_invented_canonical_metadata(self):
        root = str(Path(tempfile.gettempdir()) / 'fixture-books')
        source = os.path.join(root,'old.epub')
        self.assertEqual(propose(source,root,'ebook',{'title':'Русский перевод'})['path'],'')
        review = {'original_language':'Other','title':'The Stand','author':'King Stephen','series':'','number':'','genre':'Horror'}
        self.assertEqual(propose(source,root,'ebook',{},review)['path'],os.path.join(root,'Horror','King Stephen','The Stand','old.epub'))
        review.update(genre='Nonfiction',topic='Cinema')
        self.assertIn(os.path.join('Nonfiction','Cinema','King Stephen'),propose(source,root,'ebook',{},review)['path'])
        review.update(series='Shared Cycle',number='2',multi_author=True)
        self.assertEqual(propose(source,root,'ebook',{},review)['path'],os.path.join(root,'Shared Cycle','Shared Cycle - 2 - The Stand - King Stephen.epub'))
        self.assertEqual(propose(source,root,'audiobook',{},review)['path'],os.path.join(root,'Shared Cycle','Shared Cycle - 2 - The Stand - King Stephen.m4b'))
        review.update(title='Русский перевод')
        self.assertEqual(propose(source,root,'audiobook',{},review)['path'],'')
        review.update(original_language='Russian',title='Пикник на обочине',author='Стругацкие Аркадий и Борис',series='',multi_author=False)
        self.assertIn('Стругацкие',propose(source,root,'audiobook',{},review)['path'])
        self.assertEqual(safe_name('CON'), '_CON')
        self.assertNotIn('/',safe_name('A/B'))

    def test_epub_unicode_and_edition_language_are_read_only_evidence(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            path = Path(folder) / 'book.epub'
            with zipfile.ZipFile(path,'w') as book:
                book.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="content.opf"/></rootfiles></container>')
                book.writestr('content.opf','<package xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>Русский перевод</dc:title><dc:creator>Stephen King</dc:creator><dc:language>ru</dc:language></metadata></package>')
            before = path.read_bytes()
            data = read_metadata(str(path),'ebook',threading.Event())
            self.assertEqual(data['title'],'Русский перевод')
            self.assertEqual(data['edition_language'],'ru')
            self.assertNotIn('original_language',data)
            self.assertEqual(path.read_bytes(),before)

if __name__ == '__main__':
    unittest.main()
