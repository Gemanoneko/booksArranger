import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
import unittest.mock
import zipfile

from metadata import ScanStopped, propose, read_metadata, safe_name
from scanner import Inventory, connect
from scan_wait import finish_scan

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
        finish_scan(inventory)
        self.assertNotEqual(inventory.status(label)['state'], 'failed', inventory.last_error)

    def test_book_list_reads_without_the_write_lock_once_groups_are_current(self):
        # v0.16.12 (live): a book list (11-13 s on the real catalog) held the write lock, so every write, a Retry
        # press included, waited behind it. Now only a list that rebuilds the groups takes it.
        import groups,sqlite3
        self.file('audio/Author/Book/01.mp3');inventory=Inventory(self.database,self.roots,self.reader);self.run_scan(inventory)
        inventory.candidates('Audiobooks')  # the first list after a scan rebuilds the groups (writes)
        with connect(self.database) as db:self.assertTrue(groups.current(db,self.roots['Audiobooks']))
        inside=threading.Event();release=threading.Event();real=groups.page
        def slow(*args,**kwargs):inside.set();release.wait(10);return real(*args,**kwargs)
        results=[]
        with unittest.mock.patch.object(groups,'page',slow):
            reader=threading.Thread(target=lambda:results.append(inventory.candidates('Audiobooks')));reader.start()
            try:
                self.assertTrue(inside.wait(5))
                writer=connect(self.database,timeout=.5)
                try:writer.execute('BEGIN IMMEDIATE');writer.execute('CREATE TABLE IF NOT EXISTS probe_write(x)');writer.commit()
                finally:writer.close()
            finally:release.set();reader.join(10)
        self.assertEqual(len(results),1)
        # Positive control: when the groups must be rebuilt, the list takes the write lock as before.
        with connect(self.database) as db:db.execute('UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1')
        with connect(self.database) as db:self.assertFalse(groups.current(db,self.roots['Audiobooks']))
        inside.clear();release.clear()
        with unittest.mock.patch.object(groups,'page',slow):
            reader=threading.Thread(target=lambda:inventory.candidates('Audiobooks'));reader.start()
            try:
                self.assertTrue(inside.wait(5));writer=connect(self.database,timeout=.2)
                try:
                    with self.assertRaises(sqlite3.OperationalError):writer.execute('BEGIN IMMEDIATE')
                finally:writer.close()
            finally:release.set();reader.join(10)

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
        finish_scan(inventory)
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

    def paused_scan(self, inventory, folder):
        """Start a scan and hold it right after it listed folder and queued its files (Senua's probe P1, N13). Returns the
        event that lets it continue."""
        listed=threading.Event();release=threading.Event();real=inventory._directory
        def pause(connection,label,root,generation,path):
            real(connection,label,root,generation,path)
            if os.path.normcase(path)==os.path.normcase(str(folder)):listed.set();release.wait(20)
        patcher=unittest.mock.patch.object(inventory,'_directory',pause);patcher.start();self.addCleanup(patcher.stop)
        self.addCleanup(release.set)
        inventory.launch('Audiobooks')
        self.assertTrue(listed.wait(10),'positive control: the scan listed the folder and queued its files')
        return release

    def outcomes(self, inventory):
        with connect(self.database) as db:
            job=db.execute('SELECT * FROM jobs WHERE root=?',(self.roots['Audiobooks'],)).fetchone()
            errors=db.execute("SELECT path,error FROM scan_outcomes WHERE root=? AND generation=? AND outcome='error'",(self.roots['Audiobooks'],job['generation'])).fetchall()
            files={Path(r['path']).name:dict(r) for r in db.execute('SELECT * FROM files WHERE root=?',(self.roots['Audiobooks'],))}
        return dict(job),[dict(r) for r in errors],files

    def test_a_file_gone_mid_scan_is_skipped_quietly_and_a_complete_scan_marks_it_missing(self):
        # Senua's 0.22.0 final review, N13: a file the scan listed and that was gone before its read (deleted by Delete
        # book, or by Sergei outside the app) became a raw "[Errno 2]" read error, and a fresh catalog row when it had
        # none; the scan ended "completed with errors", which stops an automatic run. Now it is skipped quietly.
        kept=self.file('audio/Author/Book/01.mp3');lost=self.file('audio/Author/Book/02.mp3');renamed=self.file('audio/Author/Book/03.mp3')
        inventory=Inventory(self.database,self.roots,self.reader);self.run_scan(inventory)
        new=self.file('audio/Author/Book/04.mp3')  # listed by the next scan, never catalogued
        release=self.paused_scan(inventory,kept.parent)
        lost.unlink();new.unlink();renamed.rename(renamed.with_name('03 renamed.mp3'))
        release.set();finish_scan(inventory)
        job,errors,files=self.outcomes(inventory)
        self.assertEqual((job['state'],job['errors'],errors),('completed',0,[]),inventory.last_error)
        self.assertEqual(sorted(files),['01.mp3','02.mp3','03 renamed.mp3','03.mp3'],'no row for the file that was never catalogued')
        self.assertEqual({name:(row['missing'],row['error']) for name,row in files.items()},
                         {'01.mp3':(0,''),'02.mp3':(1,''),'03.mp3':(1,''),'03 renamed.mp3':(0,'')},
                         'the gone files are missing, not read errors; the renamed file is catalogued by the same scan')
        self.assertEqual(inventory.status('Audiobooks')['state'],'completed','automatic discovery continues past this scan')

    def test_a_folder_gone_mid_scan_is_skipped_quietly_and_its_files_are_marked_missing(self):
        # The same for a whole folder (Sergei deletes torrent folders outside the app): queued by the scan, gone before
        # its listing. It used to be a folder read error ("completed with errors", a scan issue), stopping automatic runs.
        gone_book=[self.file('audio/Author/Torrent Book/01.mp3'),self.file('audio/Author/Torrent Book/02.mp3')]
        moved=self.file('audio/Author/Other/01.mp3')
        inventory=Inventory(self.database,self.roots,self.reader);self.run_scan(inventory)
        release=self.paused_scan(inventory,moved.parent.parent)  # "Author" listed, its two folders queued
        import shutil;shutil.rmtree(gone_book[0].parent)
        moved.parent.rename(moved.parent.with_name('Other renamed'))
        release.set();finish_scan(inventory)
        job,errors,files=self.outcomes(inventory)
        self.assertEqual((job['state'],job['errors'],errors),('completed',0,[]),inventory.last_error)
        self.assertEqual(inventory.status('Audiobooks')['scan_issues'],[])
        with connect(self.database) as db:
            rows={str(Path(r['path']).relative_to(self.base/'audio')):r['missing'] for r in db.execute('SELECT path,missing FROM files')}
        self.assertEqual(rows,{str(Path('Author/Torrent Book/01.mp3')):1,str(Path('Author/Torrent Book/02.mp3')):1,
                               str(Path('Author/Other/01.mp3')):1,str(Path('Author/Other renamed/01.mp3')):0},
                         'the gone folder\'s files are missing; the renamed folder is catalogued by the same scan')

    def test_a_folder_queued_under_a_root_that_becomes_unreachable_is_still_an_error(self):
        # Negative control: with the source root itself gone (a dropped share) nothing proves the folder was removed.
        book=self.file('audio/Author/Book/01.mp3')
        inventory=Inventory(self.database,self.roots,self.reader);self.run_scan(inventory)
        audio=Path(self.roots['Audiobooks']);moved=self.base/'unreachable-folder-fixture'
        release=self.paused_scan(inventory,audio)  # the root listed, "Author" queued
        for attempt in range(50):
            try:audio.rename(moved);break
            except PermissionError:
                if attempt==49:raise
                time.sleep(.1)
        try:
            release.set();finish_scan(inventory)
        finally:
            moved.rename(audio)
        job,errors,files=self.outcomes(inventory)
        self.assertEqual(job['state'],'completed with errors')
        self.assertEqual([Path(e['path']).name for e in errors],['Author'])
        self.assertEqual([name for name,row in files.items() if row['missing']],[],'nothing marked missing')

    def test_a_source_that_becomes_unreachable_mid_scan_is_still_a_read_error(self):
        # Negative control for the above: "gone" needs a folder that lists without the name. A source root that cannot be
        # listed (a dropped share) proves nothing, so the reads fail as before and no file is marked missing.
        first=self.file('audio/Author/Book/01.mp3');self.file('audio/Author/Book/02.mp3')
        inventory=Inventory(self.database,self.roots,self.reader);self.run_scan(inventory)
        audio=Path(self.roots['Audiobooks']);moved=self.base/'unreachable-fixture'
        release=self.paused_scan(inventory,first.parent)
        for attempt in range(50):
            try:audio.rename(moved);break
            except PermissionError:
                if attempt==49:raise
                time.sleep(.1)
        try:
            release.set();finish_scan(inventory)
        finally:
            moved.rename(audio)
        job,errors,files=self.outcomes(inventory)
        self.assertEqual(job['state'],'completed with errors')
        self.assertEqual(sorted(Path(e['path']).name for e in errors),['01.mp3','02.mp3'])
        self.assertTrue(all('[WinError' in e['error'] or 'Errno' in e['error'] for e in errors),errors)
        self.assertEqual([name for name,row in files.items() if row['missing']],[],'nothing marked missing')

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
