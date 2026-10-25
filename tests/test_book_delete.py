"""Delete book (Sergei's ruling 23, 2026-10-25; Judy's "Delete book - spec"): a book with missing parts or broken audio
is removed from disk and from every record, so a reacquired copy is a new book. The safety tests Jane named: a shared
file, a path outside the source roots, Sorted untouched, a partial failure, and a crash between the file and record
steps; plus every typed refusal, records last, no recovery copy, and reacquire as a new book. Real private files in a
temporary library with its own Sorted folder; no network, no library access."""
import _winapi, json, os, shutil, sqlite3, threading, unittest
from pathlib import Path
from unittest import mock

import book_delete
import test_approve_as_is
from test_approve_as_is import tone
from scanner import connect


def listing(folder):
    """Every file under a folder with its size and modification time: proof that nothing there changed."""
    return sorted((str(p.relative_to(folder)), p.stat().st_size, p.stat().st_mtime_ns) for p in Path(folder).rglob('*') if p.is_file())


@unittest.skipUnless(os.name == 'nt', 'exact-handle disposal is Windows-only')
class DeleteBookTests(test_approve_as_is.ApproveFixture):
    def book(self):
        """A three-part book whose third part is gone (a Missing files row), a sibling book's file, a cover and a text
        file in the same folder, and a finished audiobook in Sorted."""
        folder = self.audio / 'Unsorted' / 'Новая плоть'
        self.parts = [tone(folder / ('Новая плоть %d.mp3' % n), self.cover, album='Новая плоть', artist='Иван Петров', track='%d/3' % n) for n in (1, 2, 3)]
        self.sibling = tone(folder / 'Другая.mp3', self.cover, album='Другая книга', artist='Анна Лесная')
        (folder / 'cover.jpg').write_bytes(b'cover'); (folder / 'info.txt').write_text('info', encoding='utf-8')
        (self.sorted / 'Петров Иван').mkdir(); (self.sorted / 'Петров Иван' / 'Другая книга - Петров Иван.m4b').write_bytes(b'finished')
        self.start()
        self.kept = self.base / 'kept'; self.kept.mkdir()
        for part in self.parts:
            shutil.copy2(part, self.kept / part.name)
        self.parts[2].unlink()
        self.inv.launch('Audiobooks'); self.inv.worker.join(10)
        rows = self.service.reviews.page(status='output_attention', group='files_missing')['rows']
        self.assertEqual([r['title_clue'] for r in rows], ['Новая плоть'], 'positive control: a Missing files row')
        return rows[0]

    def records(self, identity, paths):
        with connect(self.inv.database) as db:
            have = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            found = {}
            for table in ('book_groups', 'candidate_context', 'automatic_candidates'):
                if table in have:
                    found[table] = db.execute('SELECT count(*) FROM %s WHERE id=?' % table, (identity,)).fetchone()[0]
            found['files'] = sum(db.execute('SELECT count(*) FROM files WHERE path=?', (str(p),)).fetchone()[0] for p in paths)
        return found

    def test_delete_removes_only_this_books_files_then_every_record_and_a_reacquired_copy_is_new(self):
        row = self.book()
        self.assertEqual(row['ask']['delete'], {'kind': 'files_missing', 'present': 2}, 'the typed offer')
        sorted_before, recovery = listing(self.sorted), self.base / 'source-recovery'
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertIsNone(preview['refusal'])
        self.assertEqual([(Path(f['path']).name, f['size']) for f in preview['files']], [(p.name, (self.kept / p.name).stat().st_size) for p in self.parts[:2]])
        result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']])
        self.assertEqual((result['deleted'], result['failed'], result['forgotten']), (2, [], True))
        self.assertFalse(any(p.exists() for p in self.parts))
        folder = self.parts[0].parent
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['cover.jpg', 'info.txt', 'Другая.mp3'], 'the sibling book, the cover and the text file stay')
        self.assertEqual(listing(self.sorted), sorted_before, 'Audiobooks Sorted untouched')
        self.assertFalse(recovery.exists() and any(recovery.rglob('*')), 'no recovery copy')
        self.assertEqual(self.records(row['id'], self.parts), {'book_groups': 0, 'candidate_context': 0, 'automatic_candidates': 0, 'files': 0})
        self.assertNotIn('Новая плоть', [r['title_clue'] for r in self.service.reviews.page()['rows']])
        self.assertEqual(self.service.reviews.page(status='output_attention', group='files_missing')['rows'], [])
        # Reacquire: the same files back under the same names are a new book, with nothing of the old one.
        for part in self.parts:
            shutil.copy2(self.kept / part.name, part)
        self.inv.launch('Audiobooks'); self.inv.worker.join(10)
        new = [r for r in self.service.reviews.page()['rows'] if r['title_clue'] == 'Новая плоть']
        self.assertEqual([len(r['members']) for r in new], [3])
        self.assertNotEqual(new[0]['id'], row['id'], 'a new identity')
        self.assertIsNone(self.service.automatic.candidate(new[0]), 'no research record carried')
        self.assertFalse(new[0].get('review'))

    def test_a_shared_file_refuses_and_nothing_is_touched(self):
        self._share(self.book())

    def _share(self, row):
        with connect(self.inv.database) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='reacquire_markers'").fetchone():
                db.execute("CREATE TABLE reacquire_markers(candidate_id TEXT PRIMARY KEY,job_id TEXT NOT NULL,root TEXT NOT NULL,state TEXT NOT NULL,snapshot TEXT NOT NULL,analysis TEXT NOT NULL,receipt TEXT NOT NULL DEFAULT '')")
            db.execute("INSERT OR REPLACE INTO reacquire_markers VALUES(?,?,?,?,?,?,'')",
                       ('other-book', 'other-job', str(self.audio), 'archived',
                        json.dumps({'group': {'scope': 'x', 'evidence': json.dumps({'title_clue': 'Другая запись'})}, 'members': [{'path': str(self.parts[0])}]}), '{}'))
        before = listing(self.parts[0].parent)
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual(preview['refusal']['code'], 'shared')
        self.assertEqual(preview['refusal']['files'], [{'path': str(self.parts[0]), 'other': 'Другая запись'}])
        with self.assertRaises(book_delete.DeleteRefused) as refused:
            self.service.delete_book(row['id'], row['revision'], [str(p) for p in self.parts[:2]])
        self.assertEqual(refused.exception.code, 'shared')
        self.assertEqual(listing(self.parts[0].parent), before, 'nothing deleted')
        self.assertEqual(self.records(row['id'], [])['book_groups'], 1, 'no record deleted')
        # Another book's job holding the file refuses the same way; control: with neither, the delete goes through.
        with connect(self.inv.database) as db:
            db.execute('DELETE FROM reacquire_markers WHERE candidate_id=?', ('other-book',))
            db.execute('INSERT INTO audio_jobs(job_id,manifest,manifest_hash,state,stage,attempt_id,journal,output,reason,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       ('other-job', json.dumps({'candidate_id': 'other-book', 'metadata': {'title': 'Чужая книга'}, 'sources': [{'path': str(self.parts[1])}]}), 'h',
                        'needs attention', 'checking sources', None, '{}', None, 'x', 't', 't'))
        self.assertEqual(self.service.delete_preview(row['id'], row['revision'])['refusal']['files'], [{'path': str(self.parts[1]), 'other': 'Чужая книга'}])
        with connect(self.inv.database) as db:
            db.execute("DELETE FROM audio_jobs WHERE job_id='other-job'")
        self.assertIsNone(self.service.delete_preview(row['id'], row['revision'])['refusal'], 'control')

    def test_a_path_outside_the_source_roots_or_inside_sorted_is_refused(self):
        row = self.book()
        before = listing(self.parts[0].parent)
        elsewhere = self.base / 'elsewhere'; elsewhere.mkdir()
        with mock.patch.object(self.inv, 'source_roots', return_value=(str(elsewhere),)):
            self.assertEqual(self.service.delete_preview(row['id'], row['revision'])['refusal']['code'], 'refused')
            with self.assertRaises(book_delete.DeleteRefused) as refused:
                self.service.delete_book(row['id'], row['revision'], [str(p) for p in self.parts[:2]])
            self.assertEqual(refused.exception.code, 'refused')
        # The configured Sorted folder holding the book's folder: never deleted from.
        with mock.patch.object(self.inv, 'output_root', str(self.parts[0].parent.parent)):
            self.assertEqual(self.service.delete_preview(row['id'], row['revision'])['refusal']['code'], 'refused')
            with self.assertRaises(book_delete.DeleteRefused):
                self.service.delete_book(row['id'], row['revision'], [str(p) for p in self.parts[:2]])
        self.assertEqual(listing(self.parts[0].parent), before, 'nothing deleted')
        self.assertEqual(self.records(row['id'], [])['book_groups'], 1)
        # A path the dialog never showed (outside the book) is refused before anything is touched.
        with self.assertRaises(book_delete.DeleteRefused) as refused:
            self.service.delete_book(row['id'], row['revision'], [str(self.parts[0]), str(self.sibling)])
        self.assertEqual(refused.exception.code, 'files_changed')
        self.assertEqual(listing(self.parts[0].parent), before)

    def paused_scan(self, folder):
        """A library scan held right after it listed the book's folder and queued its files: the moment of Senua's probe
        P1 (0.22.0 final review, N13). Returns the event that lets it continue."""
        listed, release, real = threading.Event(), threading.Event(), self.inv._directory
        def pause(connection, label, root, generation, path):
            real(connection, label, root, generation, path)
            if os.path.normcase(path) == os.path.normcase(str(folder)):
                listed.set(); release.wait(30)
        patcher = mock.patch.object(self.inv, '_directory', pause); patcher.start(); self.addCleanup(patcher.stop)
        self.addCleanup(release.set)
        self.inv.launch('Audiobooks')
        self.assertTrue(listed.wait(15), 'positive control: the scan listed the book folder and queued its files')
        return release

    def test_delete_waits_while_a_library_scan_runs(self):
        # N13: Keep, Approve, Scan again and Convert wait for a library scan; Delete and its preview did not.
        row = self.book()
        before = listing(self.parts[0].parent)
        release = self.paused_scan(self.parts[0].parent)
        self.assertEqual(self.service.delete_preview(row['id'], row['revision'])['refusal'], {'code': 'busy', 'message': 'This book is being processed. Nothing was deleted.'})
        with self.assertRaises(book_delete.DeleteRefused) as refused:
            self.service.delete_book(row['id'], row['revision'], [str(p) for p in self.parts[:2]])
        self.assertEqual(refused.exception.code, 'busy')
        self.assertEqual(listing(self.parts[0].parent), before, 'nothing deleted')
        release.set(); self.inv.worker.join(15)
        self.assertEqual(self.inv.status('Audiobooks')['state'], 'completed')
        # Control: the same press after the scan goes through.
        row = self.service.reviews.page(status='output_attention', group='files_missing')['rows'][0]
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertIsNone(preview['refusal'])
        result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']])
        self.assertEqual((result['deleted'], result['failed'], result['forgotten']), (2, [], True))

    def test_files_deleted_while_a_scan_held_them_do_not_come_back_as_new_books(self):
        # Senua's probe P1 (N13), as she ran it: the scan listed the folder and queued the files, Delete removed them and
        # forgot the book, then the scan went on. Its queued reads found no file and no catalog row, wrote each back as a
        # one-file book ("Новая плоть 1", "Новая плоть 2") with "[Errno 2]", and ended "completed with errors", which stops
        # an automatic run. The same deletion can always happen outside the app, so the scan must take it quietly.
        row = self.book()
        preview = self.service.delete_preview(row['id'], row['revision'])
        release = self.paused_scan(self.parts[0].parent)
        with mock.patch.object(book_delete, 'scanning', return_value=False):  # Delete as it ran before the refusal
            result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']])
        self.assertEqual((result['deleted'], result['forgotten']), (2, True), 'positive control: P1 deleted and forgot the book mid-scan')
        release.set(); self.inv.worker.join(15)
        status = self.inv.status('Audiobooks')
        self.assertEqual((status['state'], status['errors'], status['unresolved_errors']), ('completed', 0, 0))
        self.assertEqual(self.records(row['id'], self.parts), {'book_groups': 0, 'candidate_context': 0, 'automatic_candidates': 0, 'files': 0})
        titles = [r['title_clue'] for r in self.service.reviews.page()['rows']]
        self.assertEqual([t for t in titles if t.startswith('Новая плоть')], [], titles)
        self.assertEqual(sorted(p.name for p in self.parts[0].parent.iterdir()), ['cover.jpg', 'info.txt', 'Другая.mp3'])

    def test_the_preview_refuses_a_folder_junction_into_sorted_before_listing_anything(self):
        # Senua's 0.22.0 final review, N14 (probe P6): the book's folder replaced by a junction into Audiobooks Sorted, which
        # holds same-named copies. The preview listed both files ("These 2 files will be deleted") because lstat follows a
        # folder junction; removal then refused each one. The preview now refuses first, with removal's own check.
        row = self.book()
        folder = self.parts[0].parent
        target = self.sorted / 'Петров Иван' / 'Новая плоть'; target.mkdir()
        for part in self.parts[:2]:
            shutil.copy2(self.kept / part.name, target / part.name)
        moved = self.base / 'moved-book'; folder.rename(moved)
        _winapi.CreateJunction(str(target), str(folder)); self.addCleanup(lambda: os.path.isjunction(folder) and os.rmdir(folder))
        self.assertTrue(os.path.isjunction(folder) and self.parts[0].is_file(), 'positive control: the book paths reach Sorted')
        sorted_before = listing(self.sorted)
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual((preview['files'], preview['refusal']), ([], {'code': 'refused', 'message': 'Delete was not accepted. Nothing was deleted.'}))
        with self.assertRaises(book_delete.DeleteRefused) as refused:
            self.service.delete_book(row['id'], row['revision'], [str(p) for p in self.parts[:2]])
        self.assertEqual(refused.exception.code, 'refused')
        self.assertEqual(listing(self.sorted), sorted_before, 'Audiobooks Sorted untouched')
        self.assertEqual(self.records(row['id'], [])['book_groups'], 1, 'no record deleted')
        # Control: the real folder back, the same press lists the two files.
        os.rmdir(folder); moved.rename(folder)
        self.assertEqual(len(self.service.delete_preview(row['id'], row['revision'])['files']), 2)

    def test_the_preview_refuses_a_file_with_another_name(self):
        # N14, the other check removal makes: a file with a second hard link (another name for the same data) is refused
        # by remove() ("has another name"), so the preview refuses it before the dialog says it will be deleted.
        row = self.book()
        other = self.base / 'second-name.mp3'; os.link(self.parts[0], other)
        self.assertEqual((self.service.delete_preview(row['id'], row['revision'])['refusal'] or {}).get('code'), 'refused')
        other.unlink()
        self.assertIsNone(self.service.delete_preview(row['id'], row['revision'])['refusal'], 'control: one name, listed')

    def test_a_partial_failure_keeps_every_record_and_the_next_press_finishes(self):
        row = self.book()
        preview = self.service.delete_preview(row['id'], row['revision'])
        with open(self.parts[1], 'rb'):  # held open without delete sharing: "In use by another program."
            result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']])
        self.assertEqual((result['deleted'], result['forgotten']), (1, False))
        self.assertEqual([(f['path'], f['cause']) for f in result['failed']], [(str(self.parts[1]), 'in_use')])
        self.assertFalse(self.parts[0].exists()); self.assertTrue(self.parts[1].exists())
        self.assertEqual(self.records(row['id'], [])['book_groups'], 1, 'no record deleted while a file is on disk')
        self.inv.launch('Audiobooks'); self.inv.worker.join(10)
        row = self.service.reviews.page(status='output_attention', group='files_missing')['rows'][0]
        self.assertEqual(row['ask']['delete'], {'kind': 'files_missing', 'present': 1}, 'listed with what remains')
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual([f['path'] for f in preview['files']], [str(self.parts[1])])
        result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']])
        self.assertEqual((result['deleted'], result['failed'], result['forgotten']), (1, [], True))

    def test_a_crash_between_the_files_and_the_records_forgets_nothing_and_a_later_press_finishes(self):
        row = self.book()
        preview = self.service.delete_preview(row['id'], row['revision'])
        with mock.patch.object(book_delete, 'forget', side_effect=RuntimeError('crash')), self.assertRaises(RuntimeError):
            self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']])
        self.assertFalse(any(p.exists() for p in self.parts), 'the files went first')
        self.assertEqual(self.records(row['id'], [])['book_groups'], 1, 'the records are still there: nothing half-forgotten')
        self.inv.launch('Audiobooks'); self.inv.worker.join(10)
        row = self.service.reviews.page(status='output_attention', group='files_missing')['rows'][0]
        self.assertEqual(row['ask']['delete'], {'kind': 'files_missing', 'present': 0})
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual(preview['files'], [])
        result = self.service.delete_book(row['id'], row['revision'], [])
        self.assertEqual((result['deleted'], result['forgotten']), (0, True))
        self.assertEqual(self.records(row['id'], self.parts), {'book_groups': 0, 'candidate_context': 0, 'automatic_candidates': 0, 'files': 0})

    def test_typed_refusals_touch_nothing(self):
        row = self.book()
        before = listing(self.parts[0].parent)
        paths = [str(p) for p in self.parts[:2]]
        with self.assertRaises(book_delete.DeleteRefused) as refused:
            self.service.delete_book(row['id'], row['revision'] + 1, paths)
        self.assertEqual(refused.exception.code, 'changed')
        with connect(self.inv.database) as db:
            db.execute("INSERT OR REPLACE INTO automatic_candidates VALUES(?,?,?,'Researching','{}',NULL,'t','')", (row['id'], row['revision'], row['fingerprint']))
        self.assertEqual(self.service.delete_preview(row['id'], row['revision'])['refusal']['code'], 'busy')
        with connect(self.inv.database) as db:
            db.execute('DELETE FROM automatic_candidates WHERE id=?', (row['id'],))
            db.execute('INSERT INTO audio_jobs(job_id,manifest,manifest_hash,state,stage,attempt_id,journal,output,reason,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       ('done-job', json.dumps({'candidate_id': row['id'], 'sources': []}), 'h', 'completed', 'done', None, '{}', '{}', '', 't', 't'))
        self.assertEqual(self.service.delete_preview(row['id'], row['revision'])['refusal']['code'], 'sorted')
        with connect(self.inv.database) as db:
            db.execute("DELETE FROM audio_jobs WHERE job_id='done-job'")
        offline = self.audio
        real = os.path.isdir
        with mock.patch.object(book_delete.os.path, 'isdir', side_effect=lambda p: False if str(p) == str(offline) else real(p)):
            refusal = self.service.delete_preview(row['id'], row['revision'])['refusal']
        self.assertEqual((refusal['code'], refusal['root']), ('offline', str(offline)))
        self.assertEqual(listing(self.parts[0].parent), before, 'nothing deleted by any refusal')
        self.assertEqual(self.records(row['id'], [])['book_groups'], 1)

    def test_its_reacquire_marker_goes_with_it_and_no_other_book_record_does(self):
        # A Need to reacquire book's marker (required, or archived: "Damaged-source entry archived; use the newly discovered
        # replacement") must not outlive it (Judy, 5.6); another book's marker stays.
        row = self.book()
        with connect(self.inv.database) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='reacquire_markers'").fetchone():
                db.execute("CREATE TABLE reacquire_markers(candidate_id TEXT PRIMARY KEY,job_id TEXT NOT NULL,root TEXT NOT NULL,state TEXT NOT NULL,snapshot TEXT NOT NULL,analysis TEXT NOT NULL,receipt TEXT NOT NULL DEFAULT '')")
            for identity in ('old-book', 'other-book'):
                db.execute("INSERT INTO reacquire_markers VALUES(?,?,?,?,?,?,'')", (identity, 'job-' + identity, str(self.audio), 'archived', json.dumps({'group': {'scope': identity}, 'members': []}), '{}'))
        book_delete.forget(self.service, 'old-book', [], [])
        with connect(self.inv.database) as db:
            self.assertEqual([r[0] for r in db.execute('SELECT candidate_id FROM reacquire_markers ORDER BY candidate_id')], ['other-book'])
        self.assertEqual(self.records(row['id'], [])['book_groups'], 1, 'another book is untouched')

    def damaged_mp3(self, repaired=True):
        """A single MP3 whose full audio check failed: after the app's own repair ran ("Source audio needs replacement"),
        or before it ("Retry checks it again": the app can still fix it)."""
        source = tone(self.audio / 'Unsorted' / 'Железный ад' / 'Железный ад.mp3', self.cover, album='Железный ад', artist='Иван Петров')
        row = self.start()[0]
        failure = {'exception_class': 'ValidationError', 'stage': 'checking sources'}
        if repaired:
            failure['tag_repair_checked'] = True
        with connect(self.inv.database) as db:
            db.execute('INSERT INTO audio_jobs(job_id,manifest,manifest_hash,state,stage,attempt_id,journal,output,reason,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       ('job-iron', json.dumps({'candidate_id': row['id'], 'sources': [{'path': str(source), 'sha256': 'x'}]}), 'h', 'needs attention', 'checking sources',
                        None, json.dumps({'failure': failure}), None, 'Full audio decode failed: Header missing', 't', 't'))
        self.service.invalidate_status()
        listed = [r for r in self.service.reviews.page(status='output_attention')['rows'] if r['id'] == row['id']]
        self.assertEqual(len(listed), 1, 'positive control: the Stopped row is listed')
        return source, listed[0]

    def test_source_audio_needs_replacement_offers_delete_and_removes_the_job_too(self):
        source, row = self.damaged_mp3()
        attention = row['creation']['job']['attention']
        self.assertEqual(((attention.get('remedy') or {}).get('kind'), attention.get('delete')), ('replace_source', {'kind': 'audio_damaged', 'present': 1}))
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual([f['path'] for f in preview['files']], [str(source)])
        result = self.service.delete_book(row['id'], row['revision'], [str(source)])
        self.assertEqual((result['deleted'], result['forgotten']), (1, True))
        self.assertFalse(source.exists())
        with connect(self.inv.database) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM audio_jobs WHERE job_id='job-iron'").fetchone()[0], 0, 'its job and journal go')

    def test_a_damaged_mp3_the_app_can_still_retry_has_no_offer(self):
        source, row = self.damaged_mp3(repaired=False)
        self.assertNotIn('delete', row['creation']['job']['attention'], '"Retry checks it again": Repair comes first')
        self.assertEqual(self.service.delete_preview(row['id'], row['revision'])['refusal']['code'], 'refused')
        self.assertTrue(source.exists())

    def test_no_offer_and_a_refusal_for_a_book_the_app_can_still_fix(self):
        tone(self.audio / 'Unsorted' / 'Утро снайпера' / '01.mp3', self.cover, album='Утро снайпера')
        row = self.start()[0]
        self.assertNotIn('delete', row.get('ask') or {})
        self.assertEqual(self.service.delete_preview(row['id'], row['revision'])['refusal']['code'], 'refused')
        self.assertTrue((self.audio / 'Unsorted' / 'Утро снайпера' / '01.mp3').exists())


if __name__ == '__main__':
    unittest.main()
