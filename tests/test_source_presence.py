"""0.29.0 items 1, 3 and 5: the check pass (source_presence) on private fixture folders only. No library, no Z:."""
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_presence
from scanner import connect

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'source-presence-tests'
AREA.mkdir(parents=True, exist_ok=True)


class CheckPassTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        base = Path(self.temp.name)
        self.root = base / 'Audiobooks'
        self.root.mkdir()
        (self.root / 'other book').mkdir()
        (self.root / 'other book' / 'keep.mp3').write_bytes(b'audio')  # the root answers with content
        self.database = base / 'catalog.sqlite3'
        with connect(self.database) as db:
            db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,root TEXT,scope TEXT,revision INTEGER,fingerprint TEXT,evidence TEXT,superseded INTEGER DEFAULT 0)')
            db.execute('CREATE TABLE audio_jobs(job_id TEXT,manifest TEXT)')
        inventory = SimpleNamespace(database=str(self.database), roots={'Audiobooks': str(self.root)}, source_roots=lambda library: [str(self.root)],
                                    output_root=str(base / 'Sorted'))
        self.merge = SimpleNamespace(inventory=inventory, approval_preview=Mock(), automatic=SimpleNamespace(requeue=Mock()))

    def tearDown(self):
        self.temp.cleanup()

    def book(self, identity, files, folder=None, job=False, title=None):
        folder = self.root.joinpath(*(folder or ('Author', identity)))
        folder.mkdir(parents=True, exist_ok=True)
        paths = []
        for name in files:
            path = folder / name
            path.write_bytes(b'x' * 10)
            paths.append(str(path))
        evidence = {'title_clue': title or identity, 'members': [{'path': p} for p in paths]}
        with connect(self.database) as db:
            db.execute('INSERT INTO book_groups VALUES(?,?,?,?,?,?,0)', (identity, str(self.root), identity, 1, 'fp-' + identity, json.dumps(evidence)))
            if job:
                db.execute('INSERT INTO audio_jobs VALUES(?,?)', ('job-' + identity, json.dumps({'candidate_id': identity})))
        return folder, paths

    def dismissed(self):
        with connect(self.database) as db:
            try:
                return {r[0] for r in db.execute('SELECT candidate_id FROM attention_dismissals')}
            except sqlite3.OperationalError:
                return set()

    def run_pass(self, **options):
        return source_presence.run(self.merge, **options)

    def test_a_book_whose_files_are_all_gone_leaves_the_list_and_no_file_is_touched(self):
        folder, paths = self.book('gone', ['01.mp3', '02.mp3'])
        kept_folder, kept = self.book('some-left', ['01.mp3', '02.mp3'])
        for path in paths:
            os.remove(path)
        os.remove(kept[0])
        (folder / 'cover.jpg').write_bytes(b'jpg')
        report = self.run_pass()
        self.assertEqual([item['id'] for item in report['removed']], ['gone'])
        self.assertEqual(self.dismissed(), {'gone'}, 'list-only: the Remove from list record')
        self.assertTrue((folder / 'cover.jpg').exists(), 'no file is touched by the list removal')
        self.assertTrue(Path(kept[1]).exists())
        self.assertEqual(report['roots'][0], {'path': str(self.root), 'available': True, 'empty': False, 'books': 2})

    def test_a_folder_that_was_renamed_or_deleted_counts_as_gone(self):
        folder, _paths = self.book('renamed', ['01.mp3'])
        folder.rename(folder.parent / 'renamed (2)')
        self.assertEqual([item['id'] for item in self.run_pass()['removed']], ['renamed'])

    def test_a_book_with_a_job_is_never_a_candidate(self):
        _folder, paths = self.book('converted', ['01.mp3'], job=True)
        os.remove(paths[0])
        self.assertEqual(self.run_pass()['removed'], [])
        self.assertEqual(self.dismissed(), set(), 'a converted book stays in the converted list')

    def test_an_unavailable_or_empty_root_keeps_every_book(self):
        _folder, paths = self.book('away', ['01.mp3'])
        os.remove(paths[0])
        with patch.object(source_presence, 'probe_roots', return_value=[{'path': str(self.root), 'available': False, 'empty': False}]):
            report = self.run_pass()
        self.assertEqual((report['removed'], report['roots'][0]['available']), ([], False))
        with patch.object(source_presence, 'probe_roots', return_value=[{'path': str(self.root), 'available': True, 'empty': True}]):
            self.assertEqual(self.run_pass()['removed'], [], 'an empty root is a failed mount until proven otherwise')
        self.assertEqual(self.dismissed(), set())
        # Positive control: the same book once its root answers with content.
        self.assertEqual([item['id'] for item in self.run_pass()['removed']], ['away'])

    def test_a_root_that_does_not_exist_or_hangs_is_unavailable(self):
        self.assertEqual(source_presence.probe(str(self.root / 'missing')), {'path': str(self.root / 'missing'), 'available': False, 'empty': False})
        self.assertTrue(source_presence.answers(source_presence.probe(str(self.root))))
        import threading
        release = threading.Event()

        def hang(path):
            release.wait(5)
            raise OSError('the drive never answered')
        try:
            with patch.object(source_presence.os, 'scandir', side_effect=hang):
                self.assertFalse(source_presence.probe(str(self.root), timeout=.2)['available'])
        finally:
            release.set()

    def test_a_book_outside_its_root_is_never_decided(self):
        with connect(self.database) as db:
            db.execute('INSERT INTO book_groups VALUES(?,?,?,?,?,?,0)', ('foreign', str(self.root), 'x', 1, 'fp', json.dumps({'members': [{'path': 'Z:\\Audiobooks\\x.mp3'}]})))
        self.assertEqual(self.run_pass()['removed'], [])

    def test_a_leftover_only_folder_goes_after_the_grace_with_its_empty_parents_never_the_root(self):
        folder, paths = self.book('leftovers', ['01.mp3'], folder=('Author', 'Series', 'Book'))
        os.remove(paths[0])
        for name in ('cover.jpg', 'info.txt', 'Thumbs.db'):
            (folder / name).write_bytes(b'left')
        now = 1_000_000.0
        report = self.run_pass(now=now)
        self.assertEqual((len(report['removed']), report['folders']), (1, []), 'first seen audio-free: not deleted yet')
        self.assertEqual(self.run_pass(now=now + 60)['folders'], [], 'inside the grace: kept')
        self.assertEqual(self.run_pass(now=now + 61, folders=False)['folders'], [], 'never on window focus')
        report = self.run_pass(now=now + source_presence.FOLDER_GRACE_SECONDS + 1)
        self.assertEqual([item['path'] for item in report['folders']], [str(folder)])
        self.assertEqual(sorted(report['folders'][0]['files']), ['Thumbs.db', 'cover.jpg', 'info.txt'])
        self.assertFalse((self.root / 'Author').exists(), 'empty parents go too (Sergei: no empty folders anywhere)')
        self.assertTrue(self.root.is_dir(), 'the library root itself is never removed')
        with connect(self.database) as db:
            rows = db.execute("SELECT state FROM source_folder_removed_files WHERE job_id='source-check'").fetchall()
        self.assertEqual([r[0] for r in rows], ['removed'] * 3, 'each removed file recorded (ruling 77c)')

    def test_a_folder_directly_inside_the_library_folder_goes_too(self):
        folder, paths = self.book('top', ['01.mp3'], folder=('Robert R. McCammon',))
        os.remove(paths[0])
        (folder / 'folder.jpg').write_bytes(b'jpg')
        self.run_pass(now=0.0)
        self.assertEqual([item['path'] for item in self.run_pass(now=10_000.0)['folders']], [str(folder)])
        self.assertFalse(folder.exists())

    def test_any_other_file_keeps_the_folder_until_it_is_gone(self):
        folder, paths = self.book('notes', ['01.mp3'])
        os.remove(paths[0])
        (folder / 'Notes.pdf').write_bytes(b'pdf')
        (folder / 'cover.jpg').write_bytes(b'jpg')
        self.run_pass(now=0.0)
        self.assertEqual(self.run_pass(now=10_000.0)['folders'], [])
        self.assertTrue((folder / 'cover.jpg').exists() and (folder / 'Notes.pdf').exists(), 'nothing is deleted from a kept folder')
        (folder / 'Notes.pdf').unlink()
        self.run_pass(now=20_000.0)  # first seen leftover-only now
        self.assertEqual([item['path'] for item in self.run_pass(now=30_000.0)['folders']], [str(folder)])

    def test_audio_back_or_a_subfolder_keeps_the_folder(self):
        folder, paths = self.book('back', ['01.mp3'])
        os.remove(paths[0])
        (folder / 'cover.jpg').write_bytes(b'jpg')
        self.run_pass(now=0.0)
        (folder / 'new.m4b').write_bytes(b'audio')
        self.assertEqual(self.run_pass(now=10_000.0)['folders'], [])
        self.assertTrue((folder / 'new.m4b').exists() and (folder / 'cover.jpg').exists())
        other, other_paths = self.book('sub', ['01.mp3'])
        os.remove(other_paths[0])
        (other / 'Extras').mkdir()
        self.run_pass(now=20_000.0)
        self.assertEqual(self.run_pass(now=30_000.0)['folders'], [])
        self.assertTrue((other / 'Extras').is_dir())

    def test_name_taken_rows_whose_destination_is_free_are_checked_again(self):
        free = str(Path(self.temp.name) / 'Sorted' / 'Author' / 'Book.m4b')
        taken = Path(self.temp.name) / 'Sorted' / 'Author' / 'Taken.m4b'
        taken.parent.mkdir(parents=True)
        taken.write_bytes(b'm4b')
        with connect(self.database) as db:
            db.execute('CREATE TABLE automatic_candidates(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,state TEXT,result TEXT,retry_at REAL,attempted TEXT,matcher_version TEXT)')
            for identity in ('free', 'taken', 'other'):
                db.execute('INSERT INTO book_groups VALUES(?,?,?,?,?,?,0)', (identity, str(self.root), identity, 1, 'fp-' + identity, json.dumps({'members': []})))
                reason = 'Uncertain' if identity == 'other' else 'An audiobook already exists at this path; nothing was overwritten'
                db.execute('INSERT INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)', (identity, 1, 'fp-' + identity, 'Held', json.dumps({'reasons': [reason]}), None, '', ''))
        previews = {'free': {'absolute': free, 'taken': False, 'title': 'Неисповедимый путь 2'}, 'taken': {'absolute': str(taken), 'taken': True, 'title': 'Taken'}}
        self.merge.approval_preview = Mock(side_effect=lambda identity, revision, names=None: previews[identity])
        with patch.object(source_presence, '_check_again', return_value=True) as again:
            cleared = source_presence.recheck_rows(self.merge, [str(self.root)], {})
        self.assertEqual(cleared, [{'id': 'free', 'title': 'Неисповедимый путь 2', 'cause': 'name_taken'}])
        again.assert_called_once_with(self.merge, 'free', 1, 'fp-free')
        self.assertEqual(sorted(call.args[0] for call in self.merge.approval_preview.call_args_list), ['free', 'taken'], 'only Name taken rows are previewed')

    def test_open_source_folder_names_the_drive_while_its_root_does_not_answer(self):
        # Judy section 1, row side: "Z:\Audiobooks isn't available. Check that the drive is connected." instead of
        # "Couldn't open … Check that this folder is available."
        from merge_service import FolderOpenRefused, unavailable_root
        merge = SimpleNamespace(_source_report={'roots': [{'path': 'Z:\\Audiobooks', 'available': False, 'empty': False}]})
        self.assertEqual(unavailable_root(merge, 'Z:\\Audiobooks\\Unsorted\\Сборник'), 'Z:\\Audiobooks')
        self.assertIsNone(unavailable_root(merge, 'Y:\\Other'))
        self.assertIsNone(unavailable_root(SimpleNamespace(), 'Z:\\Audiobooks\\x'), 'no pass yet: the folder message as before')
        error = FolderOpenRefused('Z:\\Audiobooks\\Unsorted', FileNotFoundError(), 'Z:\\Audiobooks')
        self.assertEqual(str(error), 'Z:\\Audiobooks isn’t available. Check that the drive is connected.')
        self.assertEqual(error.payload()['code'], 'drive_unavailable')
        self.assertIn('Check that this folder is available', str(FolderOpenRefused('Z:\\Audiobooks\\Unsorted', FileNotFoundError())))

    def test_summary_lists_ten_then_counts_the_rest(self):
        removed = [{'id': str(i), 'title': 'T%d' % i, 'path': 'P%d' % i} for i in range(13)]
        view = source_presence.summary({'roots': [], 'removed': removed, 'folders': [], 'cleared': []})
        self.assertEqual((view['removed'], len(view['removed_list']), view['removed_more']), (13, 10, 3))


if __name__ == '__main__':
    unittest.main()
