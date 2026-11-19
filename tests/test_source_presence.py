"""0.29.0 items 1, 3 and 5: the check pass (source_presence) on private fixture folders only. No library, no Z:."""
import json
import os
import shutil
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_presence
from catalog_owner import catalog_lock
from runtime_disposition_owners import admit_catalog
from scanner import connect

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'source-presence-tests'
AREA.mkdir(parents=True, exist_ok=True)


class CheckPassTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(self.temp.cleanup)  # after the catalog owner below lets go of its files
        base = Path(self.temp.name)
        self.root = base / 'Audiobooks'
        self.root.mkdir()
        (self.root / 'other book').mkdir()
        (self.root / 'other book' / 'keep.mp3').write_bytes(b'audio')  # the root answers with content
        self.database = base / 'data' / 'catalog.sqlite3'  # its own data folder, as the app's
        self.database.parent.mkdir()
        # Where a test moves a book folder out of sight. The catalog owner below holds the library root's ancestors (this
        # fixture's base included) against writes, as the app's owner does, so it is a folder of its own.
        self.outside = base / 'outside';self.outside.mkdir()
        with connect(self.database) as db:
            db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,root TEXT,scope TEXT,revision INTEGER,fingerprint TEXT,evidence TEXT,superseded INTEGER DEFAULT 0)')
            db.execute("CREATE TABLE audio_jobs(job_id TEXT,manifest TEXT,state TEXT NOT NULL DEFAULT 'completed',updated TEXT)")
        inventory = SimpleNamespace(database=str(self.database), roots={'Audiobooks': str(self.root)}, source_roots=lambda library: [str(self.root)],
                                    output_root=str(base / 'Sorted'))
        self.merge = SimpleNamespace(inventory=inventory, approval_preview=Mock(), automatic=SimpleNamespace(requeue=Mock()))
        # The app runs this pass under its own admitted catalog owner (the web server's catalog_lock); the fixture
        # registers the same, so its leftover removals never borrow a test run's support owner (Senua 0.30.0 M1: run
        # alone, 8 cases failed with "Exact file removal requires one admitted native catalog owner").
        self.enterContext(catalog_lock(self.database, inventory.roots))
        self.assertTrue(admit_catalog(self.database))

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
                db.execute('INSERT INTO audio_jobs(job_id,manifest) VALUES(?,?)', ('job-' + identity, json.dumps({'candidate_id': identity})))
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
        report = self.run_pass(now=now + source_presence.FOLDER_GRACE_SECONDS + 1)
        self.assertEqual([item['path'] for item in report['folders']], [str(folder)])
        self.assertEqual(sorted(report['folders'][0]['files']), ['Thumbs.db', 'cover.jpg', 'info.txt'])
        self.assertFalse((self.root / 'Author').exists(), 'empty parents go too (Sergei: no empty folders anywhere)')
        self.assertTrue(self.root.is_dir(), 'the library root itself is never removed')
        with connect(self.database) as db:
            rows = db.execute("SELECT state FROM source_folder_removed_files WHERE job_id='source-check'").fetchall()
        self.assertEqual([r[0] for r in rows], ['removed'] * 3, 'each removed file recorded (ruling 77c)')

    def test_window_focus_checks_rows_only_never_books_or_folders_s_m6_m_1(self):
        # Senua S-m6: the focus guard is tested past the grace, where the folder phase would delete; Futaba m-1: focus
        # drops no book either (Judy section 0: focus re-checks rows only).
        folder, paths = self.book('leftovers', ['01.mp3'])
        os.remove(paths[0])
        (folder / 'cover.jpg').write_bytes(b'jpg')
        self.run_pass(now=0.0)  # dropped, folder first seen leftover-only
        _later, later = self.book('later', ['01.mp3'])
        os.remove(later[0])
        late = source_presence.FOLDER_GRACE_SECONDS * 10
        with patch.object(source_presence, 'probe_roots', side_effect=AssertionError('focus probes no root')):
            report = self.run_pass(now=late, books=False, folders=False)
        self.assertEqual((report['removed'], report['folders'], report['roots']), ([], [], []))
        self.assertTrue((folder / 'cover.jpg').exists(), 'past the grace, focus still deletes nothing')
        self.assertNotIn('later', self.dismissed(), 'focus drops no book')
        # Positive control: the same moment through a full pass deletes the folder and drops the book.
        report = self.run_pass(now=late)
        self.assertEqual(([item['id'] for item in report['removed']], [item['path'] for item in report['folders']]), (['later'], [str(folder)]))

    def test_a_scan_after_the_pass_keeps_the_book_off_and_it_is_reported_once_m_3(self):
        # Futaba M-3: the scan marks the gone files missing, which changes the book's fingerprint; the book stays off the
        # list and the next pass does not report it again. Files that come back list it again.
        folder, paths = self.book('gone', ['01.mp3', '02.mp3'])
        for path in paths:
            os.remove(path)
        self.assertEqual([item['id'] for item in self.run_pass()['removed']], ['gone'])
        with connect(self.database) as db:
            self.assertEqual(source_presence.still_gone(db), {'gone'}, 'no scan since: the same fingerprint')
            missing = {'title_clue': 'gone', 'members': [{'path': p, 'missing': True} for p in paths]}
            db.execute("UPDATE book_groups SET fingerprint='fp-scanned',revision=2,evidence=? WHERE id='gone'", (json.dumps(missing),))
            self.assertEqual(source_presence.still_gone(db), {'gone'}, 'the scan marked every file missing: still gone')
        self.assertEqual(self.run_pass()['removed'], [], 'reported once')
        with connect(self.database) as db:
            # Positive control: a scan that finds one file again lists the book again, and the record goes.
            back = {'title_clue': 'gone', 'members': [{'path': paths[0], 'missing': False}, {'path': paths[1], 'missing': True}]}
            db.execute("UPDATE book_groups SET fingerprint='fp-back',revision=3,evidence=? WHERE id='gone'", (json.dumps(back),))
            self.assertEqual(source_presence.still_gone(db), set())
        Path(paths[0]).write_bytes(b'x' * 10)
        self.run_pass()
        with connect(self.database) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM source_gone').fetchone()[0], 0, 'a record that no longer applies goes')

    def test_files_back_unchanged_list_the_book_again_d_m1(self):
        # Senua D-M1: files restored unchanged (Recycle Bin, a folder moved back, a short drive drop) hash to the recorded
        # fingerprint, so only testing the paths again can tell "back" from "still gone".
        folder, paths = self.book('back', ['01.mp3', '02.mp3'])
        away = self.outside / 'away'
        os.rename(folder, away)
        self.assertEqual([item['id'] for item in self.run_pass()['removed']], ['back'])
        self.assertEqual(self.dismissed(), {'back'})
        self.assertEqual(self.run_pass()['returned'], [], 'positive control: still away, still off')
        os.rename(away, folder)  # back with the same bytes: the catalog row and its fingerprint never changed
        report = self.run_pass()
        self.assertEqual((report['returned'], report['removed']), ([{'id': 'back', 'title': 'back'}], []))
        with connect(self.database) as db:
            self.assertEqual((source_presence.still_gone(db), db.execute('SELECT count(*) FROM source_gone').fetchone()[0]), (set(), 0))
        self.assertEqual(self.dismissed(), set(), 'the Remove-from-list record the pass wrote goes with it')
        self.assertEqual(self.run_pass()['returned'], [], 'released once')

    def test_files_back_after_a_scan_marked_them_missing_list_the_book_again_d_m1(self):
        folder, paths = self.book('scanned', ['01.mp3'])
        os.remove(paths[0])
        self.assertEqual([item['id'] for item in self.run_pass()['removed']], ['scanned'])
        with connect(self.database) as db:
            missing = {'title_clue': 'scanned', 'members': [{'path': paths[0], 'missing': True}]}
            db.execute("UPDATE book_groups SET fingerprint='fp-missing',revision=2,evidence=? WHERE id='scanned'", (json.dumps(missing),))
        Path(paths[0]).write_bytes(b'x' * 10)  # back before the next scan: the catalog still says missing
        self.assertEqual([item['id'] for item in self.run_pass()['returned']], ['scanned'])
        self.assertEqual(self.dismissed(), set())
        # A record dropped because a scan saw a file again takes its Remove-from-list record too, so files that later
        # hash to the old fingerprint again are not hidden by it.
        _folder, paths = self.book('partial', ['01.mp3', '02.mp3'])
        for path in paths:
            os.remove(path)
        self.run_pass()
        with connect(self.database) as db:
            back = {'title_clue': 'partial', 'members': [{'path': paths[0], 'missing': False}, {'path': paths[1], 'missing': True}]}
            # 0.30.0 (Senua F-m1a): the scan that found one file moves the fingerprint away from the recorded one, so the
            # release goes through the stale branch (_books), not the loop for books whose files came back.
            db.execute("UPDATE book_groups SET fingerprint='fp-partial-scanned',revision=2,evidence=? WHERE id='partial'", (json.dumps(back),))
        Path(paths[0]).write_bytes(b'x' * 10)  # the file that scan found
        self.assertEqual(self.dismissed(), {'partial'}, 'positive control: the pass wrote its Remove-from-list record')
        self.run_pass()
        self.assertEqual(self.dismissed(), set(), 'the stale record goes with its Remove-from-list record')
        # The other file comes back unchanged: the fingerprint is the recorded one again, and nothing hides the book.
        Path(paths[1]).write_bytes(b'x' * 10)
        with connect(self.database) as db:
            whole = {'title_clue': 'partial', 'members': [{'path': paths[0], 'missing': False}, {'path': paths[1], 'missing': False}]}
            db.execute("UPDATE book_groups SET fingerprint='fp-partial',revision=3,evidence=? WHERE id='partial'", (json.dumps(whole),))
        self.run_pass()
        with connect(self.database) as db:
            self.assertNotIn('partial', source_presence.hidden(db))
        self.assertEqual(self.dismissed(), set())

    def test_hidden_books_never_include_one_with_a_job_m_5(self):
        # Futaba M-5: All candidates and the count leave out what the pass took off; a book with any job (a converted one
        # among them) never, even with a record left from before its job.
        _folder, paths = self.book('gone', ['01.mp3'])
        _folder, done = self.book('done', ['01.mp3'], job=True)
        for path in paths + done:
            os.remove(path)
        self.run_pass()
        with connect(self.database) as db:
            db.execute(source_presence.GONE_TABLE)
            db.execute("INSERT OR REPLACE INTO source_gone VALUES('done','fp-done',?,'now')", (json.dumps(source_presence._path_keys(done)),))
            self.assertEqual(source_presence.still_gone(db), {'gone', 'done'}, 'positive control: both recorded')
            self.assertEqual(source_presence.hidden(db), {'gone'})

    def test_needs_attention_drops_a_gone_book_from_every_group_at_once_s_m2(self):
        # Senua S-M2 (probe P2): a Name taken book whose files Sergei deleted since the last scan left the list only after
        # a scan marked them missing; the pass's record now takes it off every group at once.
        from merge_service import MergeService
        _folder, paths = self.book('taken', ['01.mp3'])
        with connect(self.database) as db:
            db.execute('CREATE TABLE automatic_candidates(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,state TEXT,result TEXT,retry_at REAL,attempted TEXT,matcher_version TEXT)')
            from public_research import RESEARCH_VERSION
            db.execute('INSERT INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)', ('taken', 1, 'fp-taken', 'Held',
                       json.dumps({'reasons': ['An audiobook already exists at this path; nothing was overwritten'], 'research_version': RESEARCH_VERSION}), None, '1', ''))
        merge = MergeService.__new__(MergeService)
        merge.inventory = self.merge.inventory
        self.assertEqual({key: value['group'] for key, value in merge._todo()[0].items()}, {'taken': 'name_taken'}, 'positive control: listed')
        os.remove(paths[0])
        with patch.object(source_presence, 'recheck_rows', return_value=[]):
            self.assertEqual([item['id'] for item in source_presence.run(merge)['removed']], ['taken'])
        found, coverage = merge._todo()
        self.assertEqual((found, coverage['removed']), ({}, 1), 'off the list at once, no scan needed')

    def test_a_drive_that_stops_answering_during_the_pass_drops_nothing_s_m4(self):
        _folder, paths = self.book('maybe', ['01.mp3'])
        os.remove(paths[0])
        answering = {'path': str(self.root), 'available': True, 'empty': False}
        away = {'path': str(self.root), 'available': False, 'empty': False}
        with patch.object(source_presence, 'probe_roots', side_effect=[[answering], [away]]):
            report = self.run_pass()
        self.assertEqual((report['removed'], report['roots'][0]['available']), ([], False))
        self.assertEqual(self.dismissed(), set())
        with patch.object(source_presence, 'probe_roots', side_effect=[[answering], [answering]]):
            self.assertEqual([item['id'] for item in self.run_pass()['removed']], ['maybe'], 'positive control: still answering')

    def test_a_leftover_another_job_or_book_names_keeps_the_folder_s_m1(self):
        # Senua S-m1: the reviewed 74e guards apply: a leftover an unfinished job names (its reviewed cover here) keeps the
        # folder, every file in place.
        folder, paths = self.book('held', ['01.mp3'])
        os.remove(paths[0])
        cover = folder / 'cover.jpg'
        cover.write_bytes(b'jpg')
        with connect(self.database) as db:
            db.execute("INSERT INTO audio_jobs(job_id,manifest,state) VALUES('job-other',?,'pending')", (json.dumps({'candidate_id': 'other', 'sources': [], 'cover': {'path': str(cover)}}),))
        self.run_pass(now=0.0)
        self.assertEqual(self.run_pass(now=10_000.0)['folders'], [])
        self.assertTrue(cover.exists(), 'kept: another job still reads it')
        with connect(self.database) as db:
            recorded = db.execute("SELECT count(*) FROM sqlite_master WHERE name='source_folder_removed_files'").fetchone()[0]
            self.assertEqual(recorded and db.execute('SELECT count(*) FROM source_folder_removed_files').fetchone()[0], 0, 'nothing was removed or recorded')
            db.execute("UPDATE audio_jobs SET state='completed' WHERE job_id='job-other'")
        self.assertEqual([item['path'] for item in self.run_pass(now=20_000.0)['folders']], [str(folder)], 'positive control: the job finished')
        with patch.object(source_presence, '_identity', side_effect=[('v', 1, 0), ('v', 2, 0)]):
            other, other_paths = self.book('swapped', ['01.mp3'])
            os.remove(other_paths[0])
            (other / 'info.txt').write_bytes(b'txt')
            with connect(self.database) as db:
                db.execute("INSERT OR REPLACE INTO source_folder_watch(folder,root,candidate_id,first_free,updated) VALUES(?,?,?,0,'x')", (str(other), str(self.root), 'swapped'))
            self.assertEqual(source_presence._remove_folder(str(self.database), {'folder': str(other), 'root': str(self.root), 'candidate_id': 'swapped'},
                                                            source_presence.folder_verdict(str(other))[0]), (False, ['info.txt']))
        self.assertTrue(other.is_dir(), 'a folder that is no longer the one listed is never removed')

    def test_a_leftover_named_after_the_first_check_is_kept_d_m1(self):
        # Senua D-m1: an Approve whose job names a leftover lands while the folder's leftovers are going. The guards run
        # again just before each file goes, so that file stays, and so does the folder.
        folder, paths = self.book('racing', ['01.mp3'])
        os.remove(paths[0])
        for name in ('a-notes.txt', 'cover.jpg'):
            (folder / name).write_bytes(b'left')
        self.run_pass(now=0.0)
        real, named = source_presence.remove_leftover, []

        def remove(path, root, size):
            if not named:  # the first file goes; meanwhile a new job names the other one
                other = next(str(p) for p in folder.iterdir() if str(p) != str(path))
                named.append(other)
                with connect(self.database) as db:
                    db.execute("INSERT INTO audio_jobs(job_id,manifest,state) VALUES('job-new',?,'pending')", (json.dumps({'candidate_id': 'new', 'sources': [], 'cover': {'path': other}}),))
            return real(path, root, size)
        with patch.object(source_presence, 'remove_leftover', side_effect=remove):
            report = self.run_pass(now=10_000.0)
        self.assertEqual(report['folders'], [])
        self.assertTrue(Path(named[0]).exists(), 'the file the new job names is kept')
        self.assertTrue(folder.is_dir())
        self.assertEqual(len(report['files']), 1, 'the file that went before is reported (S-m7)')

    def test_a_folder_whose_drive_left_mid_phase_stays_watched_d_m4(self):
        # Senua D-m4: the folder phase dropped a watch whenever the folder looked absent, also when the drive had left after
        # the probe; that folder was then never checked again. Now its root is probed again first.
        folder, paths = self.book('watched', ['01.mp3'])
        os.remove(paths[0])
        (folder / 'cover.jpg').write_bytes(b'jpg')
        self.run_pass(now=0.0)
        watched = lambda: [w['folder'] for w in source_presence._watched(str(self.database))]
        self.assertEqual(watched(), [str(folder)])
        away = self.outside / 'away'
        os.rename(folder, away)  # the folder cannot be seen, as when the drive drops after the probe
        answering = {'path': str(self.root), 'available': True, 'empty': False}
        gone = {'path': str(self.root), 'available': False, 'empty': False}
        with patch.object(source_presence, 'probe_roots', side_effect=[[answering], [gone]]):
            report = self.run_pass(now=10_000.0)
        self.assertEqual(watched(), [str(folder)], 'the root no longer answers: the watch stays')
        self.assertEqual(report['roots'][0]['available'], False, 'and the page is told so')
        os.rename(away, folder)
        self.assertEqual([item['path'] for item in self.run_pass(now=20_000.0)['folders']], [str(folder)], 'checked again once it is back')
        # Positive control: a folder really gone while its root answers loses its watch.
        other, other_paths = self.book('deleted', ['01.mp3'])
        os.remove(other_paths[0])
        (other / 'cover.jpg').write_bytes(b'jpg')
        self.run_pass(now=30_000.0)
        shutil.rmtree(other)
        with patch.object(source_presence, 'probe_roots', side_effect=[[answering], [answering]]):
            self.run_pass(now=40_000.0)
        self.assertEqual(watched(), [])

    def test_files_removed_from_a_folder_that_stayed_are_reported_s_m7(self):
        # Senua S-m7: the leftovers went, the folder's rmdir then failed: the line must not say "No files were touched".
        folder, paths = self.book('stays', ['01.mp3'])
        os.remove(paths[0])
        (folder / 'cover.jpg').write_bytes(b'jpg')
        self.run_pass(now=0.0)
        with patch.object(source_presence, '_identity', side_effect=[('v', 1, 0), ('v', 2, 0)]):
            report = self.run_pass(now=10_000.0)
        self.assertEqual((report['folders'], report['files']), ([], [{'path': str(folder), 'files': ['cover.jpg']}]))
        self.assertEqual(source_presence.summary(report)['files_removed'], 1)
        self.assertEqual(source_presence.summary({'removed': [{'id': 'x'}]})['files_removed'], 0, 'positive control: nothing removed')

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

    def test_the_jobs_panel_sees_the_pass_and_its_folder_phase_0290_item_7(self):
        from merge_service import MergeService
        fake = SimpleNamespace(inventory=SimpleNamespace(worker=None))
        seen = []
        def run(merge, **options):
            options['progress'](120, 412); seen.append(dict(merge._source_progress))
            options['on_phase']('folders'); seen.append(dict(merge._source_progress))
            return {'roots': [], 'removed': [], 'folders': [], 'cleared': []}
        with patch.object(source_presence, 'run', side_effect=run):
            MergeService.check_sources(fake)
        self.assertEqual([(s['phase'], s.get('done'), s.get('total')) for s in seen], [('checking', 120, 412), ('folders', None, None)])
        self.assertIsNone(fake._source_progress, 'gone once the pass ends')
        import web_server
        server = SimpleNamespace(merge=SimpleNamespace(_source_progress={'phase': 'folders', 'started': 1}, source_check_view=lambda: None))
        self.assertEqual(web_server.BrowserServer._source_view(server), {'source_check_progress': {'phase': 'folders', 'started': 1}})

    def test_summary_lists_ten_then_counts_the_rest(self):
        removed = [{'id': str(i), 'title': 'T%d' % i, 'path': 'P%d' % i} for i in range(13)]
        view = source_presence.summary({'roots': [], 'removed': removed, 'folders': [], 'cleared': []})
        self.assertEqual((view['removed'], len(view['removed_list']), view['removed_more']), (13, 10, 3))


if __name__ == '__main__':
    unittest.main()
