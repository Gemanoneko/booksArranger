"""Delete book (Sergei's ruling 23, 2026-10-25; Judy's "Delete book - spec"): a book with missing parts or broken audio
is removed from disk and from every record, so a reacquired copy is a new book. The safety tests Jane named: a shared
file, a path outside the source roots, Sorted untouched, a partial failure, and a crash between the file and record
steps; plus every typed refusal, records last, no recovery copy, and reacquire as a new book. Real private files in a
temporary library with its own Sorted folder; no network, no library access."""
import _winapi, hashlib, json, os, shutil, sqlite3, threading, unittest, uuid
from pathlib import Path
from unittest import mock

import audio_jobs
import book_delete
import merge_service
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
                       ('other-book', 'other-job', str(self.audio), 'required',
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
        # Senua's 0.22.0 final review, N16: the same marker archived (its originals confirmed gone), of a book that is
        # gone, is history: a copy reacquired at its paths is not "shared" with a book that is not listed.
        with connect(self.inv.database) as db:
            db.execute("UPDATE reacquire_markers SET state='archived' WHERE candidate_id='other-book'")
        self.assertIsNone(self.service.delete_preview(row['id'], row['revision'])['refusal'], 'an archived marker of a gone book')
        # Another book's job holding the file: shared while that book is listed, or when the job made something; a stopped
        # job of a book that is gone is history (N16).
        sibling = next(r['id'] for r in self.service.reviews.page()['rows'] if [m['path'] for m in r['members']] == [str(self.sibling)])
        def job(candidate, state='needs attention', output=None):
            with connect(self.inv.database) as db:
                db.execute("DELETE FROM audio_jobs WHERE job_id='other-job'")
                db.execute('INSERT INTO audio_jobs(job_id,manifest,manifest_hash,state,stage,attempt_id,journal,output,reason,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                           ('other-job', json.dumps({'candidate_id': candidate, 'metadata': {'title': 'Чужая книга'}, 'sources': [{'path': str(self.parts[1])}]}), 'h',
                            state, 'checking sources', None, '{}', output, 'x', 't', 't'))
            return (self.service.delete_preview(row['id'], row['revision'])['refusal'] or {}).get('files')
        held = [{'path': str(self.parts[1]), 'other': 'Чужая книга'}]
        self.assertEqual(job(sibling), held, 'a listed book\'s stopped job')
        self.assertEqual(job('gone-book', 'pending'), held, 'a queued job of a gone book')
        self.assertEqual(job('gone-book', 'completed', '{}'), held, 'a finished job of a gone book')
        self.assertIsNone(job('gone-book'), 'a stopped job of a gone book is history')
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
        self.assertEqual(([f['path'] for f in preview['files']], preview['folders']), ([str(source)], [str(source.parent)]))
        result = self.service.delete_book(row['id'], row['revision'], [str(source)], preview['folders'])
        self.assertEqual((result['deleted'], result['forgotten'], result['folders']), (1, True, {'removed': 1, 'stayed': 0}))
        self.assertFalse(source.exists() or source.parent.exists(), 'the file, then its folder left empty (rulings 24, 24a)')
        with connect(self.inv.database) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM audio_jobs WHERE job_id='job-iron'").fetchone()[0], 0, 'its job and journal go')

    def with_leftovers(self, name='Железный ад', parts=1):
        """The "Source audio needs replacement" MP3 (parts=1), whose failed attempt left a working copy of each original on
        the app's drive: a real UUID job and attempt, made through the app's own working lifecycle (begin, copy_owned,
        closed), so its disposal can prove the copies. Returns (source, or the list of parts when parts > 1, row, job_id,
        attempt folder). A second call in one test adds another book."""
        from audio_pipeline import copy_owned, generated_artifacts
        from source_cleanup import packed
        from working_lifecycle import digest
        place = self.audio / 'Unsorted' / name
        sources = [tone(place / (name + '.mp3' if parts == 1 else '%s %d.mp3' % (name, n)), self.cover, album=name, artist='Иван Петров', track='%d/%d' % (n, parts)) for n in range(1, parts + 1)]
        if getattr(self, 'service', None) is None:
            self.start()
        else:
            self.inv.launch('Audiobooks'); self.inv.worker.join(10)
        row = next(r for r in self.service.reviews.page()['rows'] if r['title_clue'] == name)
        job_id, attempt = str(uuid.uuid4()), str(uuid.uuid4())
        manifest = {'job_id': job_id, 'candidate_id': row['id'], 'candidate_revision': row['revision'], 'root': str(self.audio), 'metadata': {'title': name},
                    'sources': [{'path': str(s), 'size': s.stat().st_size, 'modified': str(s.stat().st_mtime_ns), 'sha256': hashlib.sha256(s.read_bytes()).hexdigest()} for s in sources]}
        with connect(self.inv.database) as db:
            db.execute('INSERT INTO audio_jobs(job_id,manifest,manifest_hash,state,stage,attempt_id,journal,output,reason,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (job_id, json.dumps(manifest), digest(manifest), 'running', 'checking sources', attempt, '{}', None, '', 't', 't'))
        life = self.service.working
        life.begin(dict(manifest, attempt_id=attempt))
        folder = self.service.stage_root / job_id / attempt; folder.mkdir(parents=True)
        (folder.parent / 'ownership.json').write_text(packed({'job_id': job_id, 'manifest': manifest}), encoding='utf8')
        with generated_artifacts(folder, life):
            for index, s in enumerate(sources):
                copy_owned(s, folder / ('source%05d.mp3' % index), manifest['sources'][index]['sha256'], threading.Event())
        failure = {'exception_class': 'ValidationError', 'stage': 'checking sources', 'tag_repair_checked': True}
        with connect(self.inv.database) as db:
            db.execute("UPDATE audio_jobs SET state='needs attention',journal=?,reason='Full audio decode failed: Header missing' WHERE job_id=?", (json.dumps({'failure': failure}), job_id))
        self.service.invalidate_status()
        row = [r for r in self.service.reviews.page(status='output_attention')['rows'] if r['id'] == row['id']][0]
        if parts == 1:
            self.assertEqual(row['creation']['job']['attention'].get('delete'), {'kind': 'audio_damaged', 'present': 2}, 'positive control: offered; present counts the working copy')
        self.assertEqual(self.service._working_state(self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))[0], False, fresh=True)['state'], 'cleanable', 'positive control: leftovers')
        return (sources[0] if parts == 1 else sources), row, job_id, folder

    def working_left(self, job_id):
        """Working files of the job still on the app's drive (the ownership record aside), and its working records."""
        stage = self.service.stage_root / job_id
        files = sorted(p.name for p in stage.rglob('*') if p.is_file() and p.name != 'ownership.json') if stage.exists() else []
        with connect(self.inv.database) as db:
            records = sum(db.execute('SELECT count(*) FROM %s WHERE job_id=?' % t, (job_id,)).fetchone()[0] for t in ('working_attempts', 'working_files'))
        return files, records

    def shown(self, preview):
        return [(Path(f['path']).name, f['kind']) for f in preview['files']]

    def test_delete_lists_the_books_working_files_and_removes_them_with_the_book(self):
        # Rulings 26 and N15: the app's working files for the book are listed (kind "working"), counted and removed by the
        # same press. N15: they used to be cleared after the originals by the verified disposal, which keeps a copy whose
        # original it cannot prove, so Delete failed on them at every press and never forgot the book.
        source, row, job_id, folder = self.with_leftovers()
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual(self.shown(preview), [('Железный ад.mp3', 'audio'), ('source00000.mp3', 'working')])
        self.assertEqual((preview['bytes'], preview['last_copy']), (2 * source.stat().st_size, None), 'counted; originals here: no last-copy line')
        result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual((result['deleted'], result['failed'], result['forgotten']), (2, [], True))
        self.assertFalse(source.exists())
        self.assertEqual(self.working_left(job_id), ([], 0), 'no working file and no working record of the book left')

    def test_delete_removes_every_leftover_not_only_the_audio_an_m4b_retry_counts(self):
        # N15: for an M4B job the working state counts only .m4b and .wav leftovers (Retry's rule), so any other leftover
        # read as "nothing left": its records were deleted with the book and the file stayed on the app's drive.
        with mock.patch.object(merge_service.MergeService, '_working_kind', return_value=True):  # this job is an M4B job
            source, row, job_id, folder = self.with_leftovers()
            self.assertIsNone(self.service._working_state(self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))[0], True, fresh=True), 'positive control: Retry sees nothing left')
            preview = self.service.delete_preview(row['id'], row['revision'])
            result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual((result['deleted'], result['failed'], result['forgotten']), (2, [], True))
        self.assertEqual(self.working_left(job_id), ([], 0), 'the copy of the original went too')

    def test_working_files_the_app_cannot_prove_refuse_before_anything_is_deleted(self):
        # N15 with the N14 rule: a file in the attempt folder the app did not record makes its disposal refuse, so the
        # preview refuses before the dialog lists the book's files (it used to delete them, then stop on the working files).
        source, row, job_id, folder = self.with_leftovers()
        (folder / 'stray.wav').write_bytes(b'not the app')
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual((preview['files'], (preview['refusal'] or {}).get('code')), ([], 'refused'))
        with self.assertRaises(book_delete.DeleteRefused):
            self.service.delete_book(row['id'], row['revision'], [str(source)])
        self.assertTrue(source.exists(), 'nothing deleted')
        self.assertEqual(self.working_left(job_id)[0], ['source00000.mp3', 'stray.wav'])

    def test_the_last_copy_of_a_book_whose_original_is_gone_is_deleted_too(self):
        # Ruling 26: the original is already gone, so the app's working copy is the last copy of the book's audio. The app's
        # own disposal keeps such a copy ("never remove the last copy"); Delete book removes it, on this press only, and
        # says so ("all"). Before: refused (the working files read "blocked"), so the book could never be deleted.
        source, row, job_id, folder = self.with_leftovers()
        source.unlink()
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertIsNone(preview['refusal'])
        self.assertEqual((self.shown(preview), preview['last_copy']), ([('source00000.mp3', 'working')], 'all'))
        result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual((result['deleted'], result['failed'], result['forgotten']), (1, [], True))
        self.assertEqual(self.working_left(job_id), ([], 0))
        self.assertEqual(self.records(row['id'], [source]), {'book_groups': 0, 'candidate_context': 0, 'automatic_candidates': 0, 'files': 0})
        # The routine disposal still keeps such a copy: ruling 26 is this action's only.
        source2, row2, job2, folder2 = self.with_leftovers('Железный ад 2')
        source2.unlink()
        with self.assertRaises(audio_jobs.RetryRefused):
            self.service._clear_working(self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job2,))[0])
        self.assertEqual(self.working_left(job2)[0], ['source00000.mp3'], 'control: Clear working files keeps the last copy')

    def test_the_last_copy_line_says_some_when_only_some_originals_are_gone(self):
        # Ruling 26, "some": one of two originals is gone; its working copy holds the last copy of that audio.
        source, row, job_id, folder = self.with_leftovers(parts=2)
        source[1].unlink()
        with mock.patch.object(book_delete, 'offer', return_value={'kind': 'audio_damaged', 'present': 1}):  # a two-file damaged book
            preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual((self.shown(preview), preview['last_copy']), ([('Железный ад 1.mp3', 'audio'), ('source00000.mp3', 'working'), ('source00001.mp3', 'working')], 'some'))

    # ---------------------------------------------------------------- ruling 24: other files and folders left empty
    def alone(self, folder=('Сборники', 'Новая плоть (2016)')):
        """A three-part book alone in its folder, one part gone (a Missing files row), with a cover and a text file; by
        default in Сборники, which is directly inside the source folder (Judy's update spec 2.1 example)."""
        place = self.audio.joinpath(*folder)
        self.parts = [tone(place / ('Новая плоть %d.mp3' % n), self.cover, album='Новая плоть', artist='Иван Петров', track='%d/3' % n) for n in (1, 2, 3)]
        (place / 'cover.jpg').write_bytes(b'cover'); (place / 'info.txt').write_text('info', encoding='utf-8')
        (self.sorted / 'Петров Иван').mkdir(); (self.sorted / 'Петров Иван' / 'Другая книга - Петров Иван.m4b').write_bytes(b'finished')
        self.start()
        self.parts[2].unlink()
        self.inv.launch('Audiobooks'); self.inv.worker.join(10)
        rows = self.service.reviews.page(status='output_attention', group='files_missing')['rows']
        self.assertEqual(len(rows), 1, 'positive control: a Missing files row')
        return rows[0], place

    def test_delete_takes_the_cover_text_files_and_the_folder_it_leaves_empty(self):
        # Ruling 24: the other files of a folder that holds no other book go too, and so does the folder left empty, but
        # never a folder directly inside a source folder (Сборники stays). Before: only the audio, and the folder stayed.
        row, place = self.alone()
        self.assertEqual(row['ask']['delete'], {'kind': 'files_missing', 'present': 4}, 'present counts every file the press deletes')
        sorted_before = listing(self.sorted)
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual(self.shown(preview), [('Новая плоть 1.mp3', 'audio'), ('Новая плоть 2.mp3', 'audio'), ('cover.jpg', 'other'), ('info.txt', 'other')])
        self.assertEqual((preview['folders'], preview['stay'], preview['bytes']), ([str(place)], {'items': 0}, sum(p.stat().st_size for p in place.iterdir())))
        result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual((result['deleted'], result['failed'], result['forgotten'], result['folders']), (4, [], True, {'removed': 1, 'stayed': 0}))
        self.assertFalse(place.exists(), 'the book folder left empty is removed')
        self.assertTrue(place.parent.is_dir(), 'a folder directly inside the source folder stays')
        self.assertEqual(listing(self.sorted), sorted_before, 'Audiobooks Sorted untouched')
        with connect(self.inv.database) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM files WHERE path LIKE ?', (str(place) + '%',)).fetchone()[0], 0, 'their catalog rows go too')

    def test_ruling_24a_removes_the_emptied_folders_on_ntfs_where_the_native_disposition_still_refuses(self):
        # Ruling 24a (Sergei 2026-10-25, "Allow"): on NTFS and network drives (Z:) the app's exact-handle empty-folder
        # disposition refuses (a late directory stream could be lost), so before this no folder was ever listed or removed.
        # Delete book now removes the folders it leaves empty with a plain rmdir, cascading up to, never including, a
        # folder directly inside the source folder. Control: the native disposition still refuses on this same drive, so
        # source folder cleanup and every other path keep the old refusal.
        import native_io
        row, place = self.alone(folder=('Сборники', 'Петров Иван', 'Новая плоть'))
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual(preview['folders'], [str(place), str(place.parent)], 'the book folder, then its parent left empty; deepest first')
        result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual((result['failed'], result['forgotten'], result['folders']), ([], True, {'removed': 2, 'stayed': 0}))
        self.assertFalse(place.parent.exists(), 'both removed')
        self.assertTrue((self.audio / 'Сборники').is_dir(), 'never a folder directly inside the source folder')
        control = self.audio / 'Сборники' / 'empty'; control.mkdir()
        with self.assertRaises(native_io.DirectoryDispositionUnsupported):
            with native_io.DirectoryBoundary(self.audio, control.parent), native_io.VerifiedDirectory(control, delete=True) as target:
                target.dispose_empty()
        self.assertTrue(control.is_dir(), 'control: the old refusal still holds for every other path')

    def test_a_file_that_appears_before_the_folder_goes_keeps_the_folder_and_the_book_is_forgotten(self):
        # Ruling 24a: a file that arrives after the preview, while the press runs, makes the folder not empty: it stays
        # ("1 folder stayed."), the new file is untouched, and the book removal completes.
        row, place = self.alone()
        preview = self.service.delete_preview(row['id'], row['revision'])
        real = book_delete.remove
        def arriving(path, root, size):
            outcome = real(path, root, size)
            if not any(p.suffix == '.mp3' for p in place.iterdir()):
                (place / 'late.txt').write_text('arrived', encoding='utf-8')
            return outcome
        with mock.patch.object(book_delete, 'remove', arriving):
            result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual((result['failed'], result['forgotten'], result['folders']), ([], True, {'removed': 0, 'stayed': 1}))
        self.assertEqual(sorted(p.name for p in place.iterdir()), ['late.txt'])
        self.assertEqual(self.records(row['id'], [])['book_groups'], 0, 'the book is forgotten all the same')

    def test_the_folder_removal_is_a_plain_rmdir_never_recursive(self):
        # Ruling 24a: even if a file arrives between the emptiness check and the removal, the removal itself refuses a
        # folder that is not empty (rmdir semantics): the file and the folder stay.
        row, place = self.alone()
        preview = self.service.delete_preview(row['id'], row['revision'])
        real = book_delete.remove
        def arriving(path, root, size):
            outcome = real(path, root, size)
            if not any(p.suffix == '.mp3' for p in place.iterdir()):
                (place / 'late.txt').write_text('arrived', encoding='utf-8')
            return outcome
        with mock.patch.object(book_delete, 'remove', arriving), mock.patch.object(book_delete, '_empty', return_value=True):  # the check raced
            result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual((result['forgotten'], result['folders']), (True, {'removed': 0, 'stayed': 1}))
        self.assertEqual((place / 'late.txt').read_text(encoding='utf-8'), 'arrived')

    def test_a_folder_swapped_for_a_junction_during_the_press_is_not_removed(self):
        # Ruling 24a: only an ordinary folder is removed. Emptied, then replaced by a junction (to an empty folder) before
        # its removal: the junction is not removed; it stays, and so does its target.
        row, place = self.alone()
        preview = self.service.delete_preview(row['id'], row['revision'])
        real, target, moved = book_delete.remove, self.base / 'junction-target', self.base / 'emptied-book'
        target.mkdir()
        def swapping(path, root, size):
            outcome = real(path, root, size)
            if not any(place.iterdir()):
                place.rename(moved); _winapi.CreateJunction(str(target), str(place))
            return outcome
        self.addCleanup(lambda: os.path.isjunction(place) and os.rmdir(place))
        with mock.patch.object(book_delete, 'remove', swapping):
            result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual((result['forgotten'], result['folders']), (True, {'removed': 0, 'stayed': 1}))
        self.assertTrue(os.path.isjunction(place) and target.is_dir(), 'the junction and its target stay')

    def test_a_folder_holding_a_link_or_a_subfolder_is_not_left_empty(self):
        # Ruling 24a: the folder's listing must show no file, subfolder or link; a junction inside it stays, so does it.
        row, place = self.alone()
        target = self.base / 'elsewhere'; target.mkdir()
        _winapi.CreateJunction(str(target), str(place / 'link')); self.addCleanup(lambda: os.path.isjunction(place / 'link') and os.rmdir(place / 'link'))
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual((preview['folders'], preview['stay']), ([], {'items': 1}))
        self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertTrue(os.path.isjunction(place / 'link') and target.is_dir(), 'the link and its target untouched')

    def test_a_listed_folder_that_cannot_be_removed_stays_and_never_keeps_the_book(self):
        # Ruling 24 / Judy 2.1: a folder is housekeeping. Another program holds it (no delete sharing): it stays, reported,
        # and the book is forgotten all the same.
        row, place = self.alone()
        preview = self.service.delete_preview(row['id'], row['revision'])
        held = _winapi.CreateFile(str(place), 0x80000000, 0x1 | 0x2, 0, 3, 0x02000000, 0)  # read, share read+write, no delete
        try:
            result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        finally:
            _winapi.CloseHandle(held)
        self.assertEqual((result['failed'], result['forgotten'], result['folders']), ([], True, {'removed': 0, 'stayed': 1}))
        self.assertTrue(place.is_dir())

    def test_a_folder_with_two_books_keeps_its_cover_and_text_files(self):
        # Ruling 24: "Shared or ambiguous files stay, and the dialog says so": the folder holds another book's audio.
        row = self.book()
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual((self.shown(preview), preview['folders'], preview['stay']), ([('Новая плоть 1.mp3', 'audio'), ('Новая плоть 2.mp3', 'audio')], [], {'items': 3}))

    def test_a_cover_another_book_uses_stays_and_the_text_file_goes(self):
        # Ruling 24: a cover another book's job was made with is that book's too; it stays (and so does the folder), the
        # text file that is this book's alone goes.
        row, place = self.alone()
        with connect(self.inv.database) as db:
            db.execute('INSERT INTO audio_jobs(job_id,manifest,manifest_hash,state,stage,attempt_id,journal,output,reason,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       ('other-job', json.dumps({'candidate_id': 'other-book', 'metadata': {'title': 'Чужая книга'}, 'sources': [{'path': str(self.audio / 'Elsewhere' / 'x.mp3')}],
                                                 'cover': {'path': str(place / 'cover.jpg')}}), 'h', 'pending', 'queued', None, '{}', None, '', 't', 't'))
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual((self.shown(preview)[2:], preview['folders'], preview['stay']), ([('info.txt', 'other')], [], {'items': 1}))
        self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual(sorted(p.name for p in place.iterdir()), ['cover.jpg'])

    def test_a_cover_held_open_keeps_the_book_listed(self):
        # Futaba's check 3: the cover in use by another program is reported like any file; the book stays, records kept.
        row, place = self.alone()
        preview = self.service.delete_preview(row['id'], row['revision'])
        with open(place / 'cover.jpg', 'rb'):
            result = self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual(([(Path(f['path']).name, f['cause']) for f in result['failed']], result['forgotten'], result['folders']), ([('cover.jpg', 'in_use')], False, {'removed': 0, 'stayed': 0}))
        self.assertFalse(self.parts[0].exists())
        self.assertEqual(self.records(row['id'], [])['book_groups'], 1, 'no record deleted while a file is on disk')

    def test_a_file_added_after_the_dialog_opened_refuses_the_press(self):
        # Futaba's check 3: the list now differs from the one shown (a new file, or the folder no longer left empty).
        row, place = self.alone()
        preview = self.service.delete_preview(row['id'], row['revision'])
        (place / 'notes.txt').write_text('new', encoding='utf-8')
        with self.assertRaises(book_delete.DeleteRefused) as refused:
            self.service.delete_book(row['id'], row['revision'], [f['path'] for f in preview['files']], preview['folders'])
        self.assertEqual(refused.exception.code, 'files_changed')
        self.assertTrue(self.parts[0].exists(), 'nothing deleted')

    # ---------------------------------------------------------------- ruling 25: Remove this copy
    def arranged_with_copy(self, possible=False):
        """An audiobook the app arranged in Sorted (a real conversion and output check), and an exact copy of the two files
        it was arranged from put back in another folder with a cover: the "Needs you / Identical verified recording
        already arranged" row (Futaba's m-3). The recording review's verdict is recorded as _recording_review writes it
        (the reason and the context's duplicate_review), not researched. possible: "Possible duplicate recording"."""
        from public_research import RESEARCH_VERSION
        names = ['01.mp3', '02.mp3']
        sources = [tone(self.audio / 'Unsorted' / 'Утро снайпера' / name, self.cover, album='Утро снайпера', artist='Иван Петров', title='Глава %d' % n, track='%d/2' % n) for n, name in enumerate(names, 1)]
        kept = self.base / 'kept-copy'; kept.mkdir()
        for s in sources:
            shutil.copy2(s, kept / s.name)
        row = self.start()[0]
        approved = self.service.approve_book(row['id'], row['revision']); self.wait()
        job = next(j for j in self.service.jobs.status()['jobs'] if j['job_id'] == approved['job_id'])
        self.assertEqual(job['state'], 'completed', 'positive control: arranged')
        self.assertFalse(any(s.exists() for s in sources), 'positive control: the app removed the originals')
        place = self.audio / 'Unsorted' / 'Утро снайпера (копия)'; place.mkdir()
        for name in names:
            shutil.copy2(kept / name, place / name)
        (place / 'cover.jpg').write_bytes(b'cover')
        self.inv.launch('Audiobooks'); self.inv.worker.join(10)
        copy = next(r for r in self.service.reviews.page()['rows'] if r['members'] and Path(r['members'][0]['path']).parent == place)
        self.assertNotEqual(copy['id'], job['manifest']['candidate_id'], 'positive control: a new book, not the arranged one')
        reason = 'Possible duplicate recording — original sources preserved' if possible else 'Identical verified recording already arranged — duplicate sources preserved'
        verdict = {'state': 'possible' if possible else 'verified_identical', 'blocking': possible, 'related_ids': [job['job_id']], 'related': []}
        with connect(self.inv.database) as db:
            db.execute("INSERT OR REPLACE INTO automatic_candidates VALUES(?,?,?,'Held',?,NULL,'t','')", (copy['id'], copy['revision'], copy['fingerprint'], json.dumps({'reasons': [reason], 'research_version': RESEARCH_VERSION})))
            found = db.execute('SELECT data FROM candidate_context WHERE id=?', (copy['id'],)).fetchone()
            data = dict(json.loads(found[0]) if found else {}, duplicate_review=verdict)
            db.execute('INSERT OR REPLACE INTO candidate_context VALUES(?,?,?)', (copy['id'], copy['revision'], json.dumps(data)))
        self.service.invalidate_status(); self.service.__dict__.pop('_needs_cache', None)
        copy = next(r for r in self.service.reviews.page(status='output_attention')['rows'] if r['id'] == copy['id'])
        final = Path(job['output']['final_path'])
        self.assertTrue(final.is_file() and final.is_relative_to(self.sorted), 'positive control: the audiobook is in Sorted')
        return copy, place, final

    def test_remove_this_copy_is_offered_only_with_the_proof_and_removes_only_the_copy(self):
        # Ruling 25: the offer only where the app holds the proof; the preview proves it now and shows the audiobook; the
        # press removes the copy's files (its cover too, ruling 24) and its records, never the audiobook in Sorted.
        copy, place, final = self.arranged_with_copy()
        self.assertEqual((copy['ask'].get('duplicate'), copy['ask'].get('copy')), ('verified', {'kind': 'verified_duplicate', 'present': 3}))
        self.assertNotIn('delete', copy['ask'], 'never both buttons')
        sorted_before = listing(self.sorted)
        preview = self.service.delete_preview(copy['id'], copy['revision'], 'copy')
        self.assertIsNone(preview['refusal'])
        self.assertEqual(self.shown(preview), [('01.mp3', 'audio'), ('02.mp3', 'audio'), ('cover.jpg', 'other')])
        self.assertEqual((preview['sorted']['path'], preview['sorted']['size'], preview['last_copy']), (str(final), final.stat().st_size, None))
        self.assertTrue(preview['sorted']['verified_at'].endswith('+00:00'), 'the time of this check, in UTC')
        # The audiobook is held, with no write or delete sharing, while the copy's files go.
        real, opened = book_delete.remove, []
        def watched(path, root, size):
            try:
                with open(final, 'r+b'):
                    opened.append('writable')
            except PermissionError:
                opened.append('held')
            return real(path, root, size)
        with mock.patch.object(book_delete, 'remove', watched):
            result = self.service.delete_book(copy['id'], copy['revision'], [f['path'] for f in preview['files']], preview['folders'], 'copy')
        self.assertEqual((result['deleted'], result['failed'], result['forgotten']), (3, [], True))
        self.assertEqual(set(opened), {'held'}, 'the audiobook could not be opened for writing during the removal')
        self.assertEqual(listing(self.sorted), sorted_before, 'Audiobooks Sorted untouched')
        self.assertFalse(place.exists(), 'the copy folder left empty is removed too (ruling 24a)')
        self.assertEqual(self.records(copy['id'], [Path(m['path']) for m in copy['members']]), {'book_groups': 0, 'candidate_context': 0, 'automatic_candidates': 0, 'files': 0})

    def test_remove_this_copy_refuses_without_the_proof_and_touches_nothing(self):
        # Ruling 25, Judy's update spec 3.4: the audiobook gone from its place, the audiobook changed, a copy file changed,
        # a junction; each refused before the first file, nothing deleted. Control: restored, the press goes through.
        copy, place, final = self.arranged_with_copy()
        before, sorted_before = listing(place), listing(self.sorted)
        paths = [str(p) for p in sorted(place.iterdir())]
        def refusal():
            code = (self.service.delete_preview(copy['id'], copy['revision'], 'copy')['refusal'] or {}).get('code')
            with self.assertRaises(book_delete.DeleteRefused) as refused:
                self.service.delete_book(copy['id'], copy['revision'], paths, [], 'copy')
            self.assertEqual(listing(place), before, 'nothing deleted')
            return code, refused.exception.code
        away = final.with_name('away.m4b'); final.rename(away)
        self.assertEqual(refusal(), ('sorted_missing', 'sorted_missing'))
        away.rename(final)
        original = final.read_bytes(); stamp = final.stat().st_mtime_ns
        final.write_bytes(original[:-1] + bytes([original[-1] ^ 1])); os.utime(final, ns=(stamp, stamp))
        self.assertEqual(refusal(), ('sorted_changed', 'sorted_changed'))
        final.write_bytes(original); os.utime(final, ns=(stamp, stamp))
        self.assertEqual(listing(self.sorted), sorted_before)
        member = place / '02.mp3'; data = member.read_bytes()
        member.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        before = listing(place)
        self.assertEqual(refusal(), ('not_identical', 'not_identical'))
        member.write_bytes(data); before = listing(place)
        moved = self.base / 'moved-copy'; place.rename(moved)
        _winapi.CreateJunction(str(moved), str(place)); self.addCleanup(lambda: os.path.isjunction(place) and os.rmdir(place))
        self.assertEqual(refusal(), ('refused', 'refused'))
        os.rmdir(place); moved.rename(place)
        self.assertEqual(listing(self.sorted), sorted_before, 'Audiobooks Sorted untouched by every refusal')
        preview = self.service.delete_preview(copy['id'], copy['revision'], 'copy')
        result = self.service.delete_book(copy['id'], copy['revision'], [f['path'] for f in preview['files']], preview['folders'], 'copy')
        self.assertEqual((result['failed'], result['forgotten']), ([], True), 'control: with the proof whole, the press goes through')

    def test_a_possible_duplicate_has_no_remove_offer_and_is_refused(self):
        copy, place, final = self.arranged_with_copy(possible=True)
        self.assertEqual((copy['ask'].get('duplicate'), copy['ask'].get('copy')), ('possible', None))
        self.assertEqual(self.service.delete_preview(copy['id'], copy['revision'], 'copy')['refusal']['code'], 'refused')
        # Each guard alone: the stored verdict says identical, but the row's own reason is still "Possible duplicate".
        with connect(self.inv.database) as db:
            data = json.loads(db.execute('SELECT data FROM candidate_context WHERE id=?', (copy['id'],)).fetchone()[0])
            data['duplicate_review'].update(state='verified_identical', blocking=False)
            db.execute('UPDATE candidate_context SET data=? WHERE id=?', (json.dumps(data), copy['id']))
        self.assertEqual(self.service.delete_preview(copy['id'], copy['revision'], 'copy')['refusal']['code'], 'refused')
        self.assertEqual(len(list(place.iterdir())), 3)

    def test_a_book_folder_directly_inside_the_source_folder_stays(self):
        row, place = self.alone(folder=('Новая плоть',))
        preview = self.service.delete_preview(row['id'], row['revision'])
        self.assertEqual((len(preview['files']), preview['folders']), (4, []), 'its files go, the folder stays')

    def test_a_stopped_row_carries_its_jobs_destination_for_its_goes_to_line(self):
        # Futaba's m-3 (rest): the damaged-MP3 Stopped row had no "Goes to" line; Judy's to-do spec (1.6, section 4) puts one
        # on every row, Stopped rows included. The row's job now carries its own destination, relative to Sorted.
        source, row = self.damaged_mp3()
        self.assertIsNone(row['creation']['job'].get('destination'), 'positive control: a manifest naming no destination')
        target = self.sorted / 'Петров Иван' / 'Железный ад - Петров Иван.m4b'
        with connect(self.inv.database) as db:
            manifest = json.loads(db.execute("SELECT manifest FROM audio_jobs WHERE job_id='job-iron'").fetchone()[0])
            manifest.update(destination=str(target), output_root=str(self.sorted))
            db.execute("UPDATE audio_jobs SET manifest=? WHERE job_id='job-iron'", (json.dumps(manifest),))
        self.service.invalidate_status()
        row = next(r for r in self.service.reviews.page(status='output_attention')['rows'] if r['id'] == row['id'])
        self.assertEqual(row['creation']['job']['destination'], {'path': str(Path('Петров Иван') / 'Железный ад - Петров Иван.m4b'), 'absolute': str(target)})

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
