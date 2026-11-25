"""0.31.3 (Sergei 2026-11-25): late writes into finished audiobooks (a series found later, an English title or author name
found later: series_backfill, name_write) on the NAS.

Root cause of the 24-25 Nov holds, measured on Sergei's machine (2026-11-25, read only): Z:\\Audiobooks Sorted is an SMB
share (\\\\NAS3247BD\\Public). For a handle there GetFinalPathNameByHandleW(VOLUME_NAME_GUID) fails (Windows error 3), so the
hardened disposition's _local_provider raises RemoteProviderRefused before any removal; the handle is SMB, not loopback,
on a DRIVE_REMOTE drive, so native_io.remote_handle is True. The late writes called VerifiedFile.dispose() with no
remote_legacy, so every refusal became FileRemovalRetained ("Safe removal of ... could not be verified. The file was
kept."): 82 series writes and 33 writes of names kept both files. Source cleanup had Sergei's 2026-11-16 NAS ruling (the
pre-0.28 exact-handle method after the caller's last checks repeat) and removed 1,383 originals on Z: that way.

Real audiobooks made by ffmpeg (test_series_backfill's Library, test_name_write_031's Book) in private folders under the
worker's scratch. nas_library() makes only the library folder read as Z: does to the disposition (both answers above); the
proof stage and the catalog stay local, as installed. Each case has its control: the same steps as 0.31.2 called dispose
(no NAS method) hold the book with the live reason, word for word."""
import contextlib
import ctypes
from ctypes import wintypes
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import book_move
import native_io
import quicktime_chapters
import runtime_file_disposition as runtime
import series_backfill
import name_write
import sorting_moves
from native_io import FileRemovalRetained, VerifiedFile, retained_text
from name_write import NameWrite
from scanner import connect
import test_series_backfill as base
from test_series_backfill import Library, sha

LIVE_PREFIX = 'Series recovery could not verify the files; remaining copies kept: Safe removal of \u201c'
LIVE_SUFFIX = '\u201d could not be verified. The file was kept.'


def setUpModule():
    # As test_series_backfill: these writes are in the book's own folder; the guard that holds such a write for Sergei's
    # approval (test_series_write_guard_031) is opened here.
    global _GUARD
    _GUARD = series_backfill.WRITE_WITHOUT_APPROVAL
    series_backfill.WRITE_WITHOUT_APPROVAL = 'allow'


def tearDownModule():
    series_backfill.WRITE_WITHOUT_APPROVAL = _GUARD


def _final_path(handle):
    """The handle's own path (VOLUME_NAME_DOS), never a name the caller passed."""
    final = native_io.kernel.GetFinalPathNameByHandleW
    final.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    final.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(32768)
    size = final(handle, buffer, len(buffer), 0)
    value = buffer.value if size and size < len(buffer) else ''
    return value[4:] if value.startswith('\\\\?\\') else value


@contextlib.contextmanager
def nas_library(root):
    """Inside root, every handle reads to the disposition as one on Sergei's NAS does (module text); elsewhere as before."""
    root = os.path.normcase(str(Path(root).resolve())).rstrip('\\') + '\\'
    real = runtime._local_provider

    def inside(path):
        return os.path.normcase(str(path)).startswith(root)

    def provider(handle):
        if inside(_final_path(handle)):
            raise runtime.RemoteProviderRefused(runtime.REMOTE_PROVIDER_REFUSAL)
        return real(handle)

    def remote(handle, path):
        return inside(_final_path(handle)) and inside(path)
    with mock.patch.object(runtime, '_local_provider', provider), mock.patch.object(native_io, 'remote_handle', remote):
        yield


@contextlib.contextmanager
def methods():
    """{normcased path: the method that removed it (VerifiedFile.disposition_method), None when nothing was removed}."""
    real = VerifiedFile.dispose
    seen = {}

    def dispose(handle, **kwargs):
        try:
            return real(handle, **kwargs)
        finally:
            seen[os.path.normcase(str(handle.path))] = getattr(handle, 'disposition_method', None)
    with mock.patch.object(VerifiedFile, 'dispose', dispose):
        yield seen


@contextlib.contextmanager
def as_0312():
    """VerifiedFile.dispose as the late writes called it in 0.31.2: never with the NAS method."""
    real = VerifiedFile.dispose

    def dispose(handle, **kwargs):
        kwargs.pop('remote_legacy', None)
        return real(handle, **kwargs)
    with mock.patch.object(VerifiedFile, 'dispose', dispose):
        yield


def like_0312(database, table, job_id):
    """The record as 0.31.2 stored it: since 0.31.3 (Senua m3) a removal this version starts carries 'removal_version', so
    a hold made here by running today's code under as_0312() is not one 0.31.2 left. Drop that mark to model the live hold."""
    with connect(database) as db:
        record = json.loads(db.execute('SELECT record FROM ' + table + ' WHERE job_id=?', (job_id,)).fetchone()[0])
        record.pop('removal_version', None)
        db.execute('UPDATE ' + table + ' SET record=? WHERE job_id=?', (json.dumps(record, ensure_ascii=False), job_id))


def key(path):
    return os.path.normcase(str(path))


class SeriesWriteOnNasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=base.AREA)
        self.addCleanup(self.temp.cleanup)
        self.lib = Library(Path(self.temp.name))

    def output(self):
        return json.loads(self.lib.row()['output'])

    def hold_as_0312(self):
        """The live state of the 82 books: the series written, the file renamed and recorded, the former file kept."""
        lib = self.lib
        backfill = lib.backfill()
        with nas_library(lib.root), as_0312():
            backfill.run_pass()
        like_0312(lib.db, 'series_backfill', lib.job_id)
        state, reason = lib.state(backfill)
        self.assertEqual(state, 'held')
        self.assertEqual(reason, LIVE_PREFIX + str(lib.path) + LIVE_SUFFIX, 'the reason Sergei\'s catalog holds, word for word')
        self.assertEqual(reason, series_backfill.RECOVERY_HOLD + retained_text(lib.path))
        self.assertTrue(lib.path.exists() and lib.target.exists(), 'both files kept')
        self.assertEqual((self.output()['final_path'], self.output()['sha256']), (str(lib.target), sha(lib.target)), 'the catalog names the new file')
        return backfill

    def test_control_0312_holds_the_book_with_the_live_reason_and_keeps_both_files(self):
        record = self.hold_as_0312().entry(self.lib.job_id)['record']
        self.assertIs(record['removal_intended'], True)
        self.assertNotIn('removal_retry', record)

    def test_the_former_file_on_the_nas_is_removed_by_the_nas_method(self):
        lib = self.lib
        backfill = lib.backfill()
        with nas_library(lib.root), methods() as used:
            backfill.run_pass()
        self.assertEqual(lib.state(backfill), ('done', ''))
        self.assertFalse(lib.path.exists(), 'no second copy')
        self.assertTrue(lib.target.exists())
        self.assertEqual(used[key(lib.path)], native_io.NAS_LEGACY)
        local = {path: method for path, method in used.items() if not path.startswith(key(lib.root))}
        self.assertTrue(local and set(local.values()) == {native_io.HARDENED_LOCAL}, 'control: the local proof stage keeps the hardened method')
        self.assertTrue(lib.merge()._output_valid(self.output()))

    def test_a_0312_hold_is_finished_once_by_0313_and_the_new_file_is_the_one_kept(self):
        lib = self.lib
        self.hold_as_0312()
        recorded = self.output()['sha256']
        backfill = lib.backfill()
        with nas_library(lib.root), methods() as used:
            backfill.run_pass()
        self.assertEqual(lib.state(backfill), ('done', ''))
        self.assertFalse(lib.path.exists())
        self.assertEqual(sha(lib.target), recorded, 'the file kept is the one the catalog names, unchanged')
        self.assertEqual(used[key(lib.path)], native_io.NAS_LEGACY)
        self.assertEqual(backfill.entry(lib.job_id)['record']['removal_retry'], series_backfill.REMOVAL_RETRY)
        self.assertTrue(lib.merge()._output_valid(self.output()))
        backfill.run_pass()
        self.assertEqual(lib.state(backfill), ('done', ''))
        self.assertEqual(sha(lib.target), recorded)

    def test_a_changed_former_file_is_kept_and_tried_once(self):
        lib = self.lib
        self.hold_as_0312()
        data = bytearray(lib.path.read_bytes())
        data[-20] ^= 1
        lib.path.write_bytes(data)
        changed = sha(lib.path)
        backfill = lib.backfill()
        with nas_library(lib.root):
            backfill.run_pass()
        entry = backfill.entry(lib.job_id)
        self.assertEqual(entry['state'], 'held')
        self.assertEqual(entry['reason'], 'The old file changed since the app checked it; both files kept.', "Judy 5.1 row 2a, no engine prefix")
        self.assertEqual(entry['record']['removal_retry'], series_backfill.REMOVAL_RETRY)
        self.assertEqual(sha(lib.path), changed, 'kept as it is')
        self.assertTrue(lib.target.exists())
        with nas_library(lib.root), mock.patch.object(SeriesBackfillSpy, 'calls', []):
            with mock.patch.object(series_backfill.SeriesBackfill, '_resume_protected', SeriesBackfillSpy.record):
                backfill.run_pass()
            self.assertEqual(SeriesBackfillSpy.calls, [], 'tried once per version: no second try')
        self.assertEqual(backfill.entry(lib.job_id), entry)

    def test_the_former_file_stays_unless_the_catalog_names_the_new_file(self):
        lib = self.lib
        self.hold_as_0312()
        with connect(lib.db) as db:
            output = json.loads(db.execute('SELECT output FROM audio_jobs WHERE job_id=?', (lib.job_id,)).fetchone()[0])
            db.execute('UPDATE audio_jobs SET output=? WHERE job_id=?', (json.dumps(dict(output, final_path=str(lib.path), sha256=lib.original)), lib.job_id))
        backfill = lib.backfill()
        with nas_library(lib.root):
            backfill.run_pass()
        state, reason = lib.state(backfill)
        self.assertEqual(state, 'held')
        self.assertEqual(reason, 'The catalog does not match the new file; both files kept.', 'Judy 5.1 row 1, no engine prefix')
        self.assertEqual(sha(lib.path), lib.original)
        self.assertTrue(lib.target.exists())

    def test_a_hold_for_another_reason_is_not_tried_again(self):
        lib = self.lib
        backfill = self.hold_as_0312()
        other = series_backfill.RECOVERY_HOLD + 'The new file is gone; the audiobook is unchanged'
        with connect(lib.db) as db:
            db.execute('UPDATE series_backfill SET reason=? WHERE job_id=?', (other, lib.job_id))
        before = backfill.entry(lib.job_id)
        with nas_library(lib.root):
            lib.backfill().run_pass()
        self.assertEqual(backfill.entry(lib.job_id), before)
        self.assertTrue(lib.path.exists() and lib.target.exists())

    def test_its_own_temporary_file_on_the_nas_is_removed(self):
        lib = self.lib
        temp = lib.path.parent / (series_backfill.TEMP_PREFIX + lib.job_id + '.m4b')
        temp.write_bytes(b'unproven partial write')
        with nas_library(lib.root), as_0312():
            with self.assertRaises(FileRemovalRetained):
                series_backfill.SeriesBackfill._dispose_temporary(temp)
        self.assertTrue(temp.exists(), 'control: 0.31.2 kept it')
        with nas_library(lib.root), methods() as used:
            series_backfill.SeriesBackfill._dispose_temporary(temp)
        self.assertFalse(temp.exists())
        self.assertEqual(used[key(temp)], native_io.NAS_LEGACY)


class SeriesBackfillSpy:
    calls = []

    @staticmethod
    def record(self, job_id, *args, **kwargs):
        SeriesBackfillSpy.calls.append(job_id)


class NameWriteOnNasTests(unittest.TestCase):
    """The writes of names (an English title the detail look-up found later, item 3) on the NAS: the same steps after the write
    as the series write's, so the same root cause and the same fix."""

    def book(self):
        from test_name_write_031 import Book
        return Book(self)

    def test_an_english_title_found_later_is_written_into_the_finished_book_on_the_nas(self):
        from test_name_write_031 import ENGLISH
        book = self.book()
        item = book.plan_item()
        self.assertEqual(item['names'], {'title': ENGLISH}, 'the title the detail look-up found later')
        book.approve()
        with nas_library(book.lib.root), methods() as used:
            book.writer.run_pass()
        self.assertEqual(book.state(), ('done', ''))
        record = book.writer.entry(book.lib.job_id)['record']
        self.assertFalse(book.path.exists(), 'no second copy')
        self.assertTrue(Path(record['new_path']).exists())
        self.assertEqual(used[key(book.path)], native_io.NAS_LEGACY)
        self.assertEqual(book.manifest()['metadata']['title'], ENGLISH)

    def test_a_0312_hold_of_names_is_finished_once_by_0313(self):
        book = self.book()
        book.approve()
        with nas_library(book.lib.root), as_0312():
            book.writer.run_pass()
        like_0312(book.lib.db, 'name_writes', book.lib.job_id)
        state, reason = book.state()
        self.assertEqual((state, reason), ('held', LIVE_PREFIX + str(book.path) + LIVE_SUFFIX), 'control: the reason of the 33 live holds')
        new = Path(book.writer.entry(book.lib.job_id)['record']['new_path'])
        self.assertTrue(book.path.exists() and new.exists())
        digest = sha(new)
        with nas_library(book.lib.root), methods() as used:
            book.writer.run_pass()
        self.assertEqual(book.state(), ('done', ''))
        self.assertFalse(book.path.exists())
        self.assertEqual(sha(new), digest)
        self.assertEqual(used[key(book.path)], native_io.NAS_LEGACY)

    def test_a_finished_retry_moves_the_book_to_its_folder_once(self):
        """As live: the rules dispatched the write, 0.31.2 held it on the NAS and the rules closed its entry as failed. The
        retry finishes it, its approved move follows, and a later pass of the rules (past its spacing) adds no second move."""
        from test_name_write_031 import Book, ORDERED
        book = Book(self, english=None, author_rule=ORDERED)
        final = book.lib.root / ORDERED / ('%s - %s.m4b' % (book.title, ORDERED))
        self.assertEqual(book.plan_item()['to'], str(final))
        book.filing.tick()
        with nas_library(book.lib.root), as_0312():
            book.writer.run_pass()
        like_0312(book.lib.db, 'name_writes', book.lib.job_id)
        self.assertEqual(book.state()[0], 'held')
        book.filing.tick()
        with connect(book.lib.db) as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT state,step FROM rule_filings')], [('failed', 'names')], 'as live: one failed entry')
        placed = Path(book.writer.entry(book.lib.job_id)['record']['new_path'])
        self.assertTrue(book.path.exists() and placed.exists())
        with nas_library(book.lib.root):
            book.writer.run_pass()
        entry = book.writer.entry(book.lib.job_id)
        self.assertEqual((entry['state'], entry['record']['follow_up']['state']), ('done', 'move_queued'))
        self.assertFalse(book.path.exists())
        book.filing.clock = lambda: 2_000_000_000.0
        book.filing.tick()
        self.assertEqual(len(book.queue), 1, 'one move')
        book.run_queue()
        book.filing.tick()
        self.assertEqual((final.exists(), placed.exists(), book.path.exists()), (True, False, False))
        self.assertEqual(book.resolve()['final_path'], str(final))
        self.assertEqual(book.plan_item(), None, 'moved once: nothing left')
        with connect(book.lib.db) as db:
            self.assertEqual([r[0] for r in db.execute('SELECT state FROM book_moves')], ['complete'])

    def test_its_own_temporary_file_on_the_nas_is_removed(self):
        book = self.book()
        temp = book.path.parent / (name_write.TEMP_PREFIX + book.lib.job_id + '.m4b')
        temp.write_bytes(b'unproven partial write')
        with nas_library(book.lib.root), as_0312():
            with self.assertRaises(FileRemovalRetained):
                NameWrite._dispose_temporary(temp)
        self.assertTrue(temp.exists(), 'control: 0.31.2 kept it (the two temporaries left on Z:)')
        with nas_library(book.lib.root), methods() as used:
            NameWrite._dispose_temporary(temp)
        self.assertFalse(temp.exists())
        self.assertEqual(used[key(temp)], native_io.NAS_LEGACY)

    def test_a_move_begun_during_the_write_on_the_nas_removes_the_rewritten_copy(self):
        book = self.book()
        book.approve()
        with mock.patch.object(NameWrite, 'catalog', side_effect=sqlite3.OperationalError('database is locked')):
            with nas_library(book.lib.root):
                book.writer.run_pass()
        self.assertEqual(book.state()[0], 'renamed')
        new = Path(book.writer.entry(book.lib.job_id)['record']['new_path'])
        with connect(book.lib.db) as db:
            move = book_move.plan(db, job_id=book.lib.job_id, kind='base', candidate_id=book.lib.candidate, start=book_move.location(book.resolve()),
                                  folder=str(book.lib.root / 'Mine'), root=str(book.lib.root), origin='user', override_id='his')
            db.execute("UPDATE book_moves SET state='rename_intent' WHERE move_id=?", (move['move_id'],))
        book.writer.clock = lambda: 2_000_000_000.0
        with nas_library(book.lib.root), methods() as used:
            book.writer.run_pass()
        state, reason = book.state()
        self.assertEqual(state, 'held')
        self.assertEqual(reason, 'The audiobook was moved meanwhile; the catalog is unchanged; the new file was removed.', "N9's success variant")
        self.assertFalse(new.exists(), 'no second copy')
        self.assertEqual(sha(book.path), book.original, 'the file the move starts from')
        self.assertEqual(used[key(new)], native_io.NAS_LEGACY)


class LeftoverTemporaryTests(unittest.TestCase):
    """Sergei 2026-11-25 (0.31.3): the two temporary files 0.31.2's writes of names left on the NAS are removed by the app,
    once, only after every proof (SeriesBackfill._remove_leftover); any doubt keeps the file with why. The live state is
    made as it happened: a write that failed after its new file was written kept that file (0.31.2's removal was refused
    on the NAS), and the next try was held on that file's refused removal."""

    def leave(self, book):
        from series_backfill import Held
        book.approve()
        with nas_library(book.lib.root), as_0312(), mock.patch.object(NameWrite, '_read_back', side_effect=Held('The new names did not read back: title')):
            book.writer.run_pass()
        self.assertEqual(book.state(), ('held', 'The new names did not read back: title'))
        temp = book.path.parent / (name_write.TEMP_PREFIX + book.lib.job_id + '.m4b')
        self.assertTrue(temp.exists(), 'control: 0.31.2 kept the written temporary file')
        book.approve()
        with nas_library(book.lib.root), as_0312():
            book.writer.run_pass()
        self.assertEqual(book.state(), ('held', 'The names could not be written; the audiobook is unchanged: Safe removal of “' + str(temp) + LIVE_SUFFIX),
                         'the two live holds, word for word')
        with connect(book.lib.db) as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT job_id,kind FROM owned_artifacts WHERE path=?', (str(temp),))], [(book.lib.job_id, 'temporary')])
        return temp

    def owned(self, book, temp):
        with connect(book.lib.db) as db:
            return [tuple(r) for r in db.execute('SELECT job_id,kind FROM owned_artifacts WHERE path=?', (str(temp),))]

    def test_the_leftover_temporary_is_removed_after_its_proofs_then_the_names_get_one_fresh_try(self):
        from test_name_write_031 import Book, ENGLISH
        book = Book(self)
        temp = self.leave(book)
        digest, size = sha(temp), temp.stat().st_size
        with nas_library(book.lib.root), mock.patch.object(series_backfill, '_log') as log:
            book.writer.run_pass()
        self.assertFalse(temp.exists())
        record = book.writer.entry(book.lib.job_id)['record']
        removed = record['temp_removed']
        self.assertEqual((removed['path'], removed['size'], removed['sha256'], removed['method']), (str(temp), size, digest, native_io.NAS_LEGACY))
        self.assertEqual(record['temp_retry'], series_backfill.REMOVAL_RETRY)
        self.assertNotIn('temp_kept', record)
        self.assertEqual(self.owned(book, temp), [], 'its ownership row goes with it')
        logged = [call.args[0] for call in log.call_args_list]
        self.assertIn('Removed a leftover temporary file of an unfinished update: ' + book.title + ' (' + series_backfill.size_text(size) + '): ' + str(temp), logged,
                      'one normal-level engine log line (Judy 6)')
        # Sergei's ruling 4: its tries were used up by the NAS bug; the names get one fresh try, with every proof of a write.
        self.assertEqual(book.state(), ('done', ''), 'the write succeeded: the book leaves the held list')
        self.assertEqual(record['names_retry'], series_backfill.REMOVAL_RETRY)
        self.assertEqual(book.manifest()['metadata']['title'], ENGLISH)
        new = Path(record['new_path'])
        self.assertTrue(new.exists())
        self.assertFalse(book.path.exists(), 'the old file went after the new one was proven, as in any write')
        before = book.writer.entry(book.lib.job_id)
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertEqual(book.writer.entry(book.lib.job_id), before, 'once: nothing more')

    def test_a_failed_fresh_try_stays_held_with_section_6s_sentence_and_is_not_tried_again(self):
        from test_name_write_031 import Book
        from series_backfill import Held
        book = Book(self)
        temp = self.leave(book)
        with nas_library(book.lib.root), mock.patch.object(NameWrite, '_read_back', side_effect=Held('The new names did not read back: title')):
            book.writer.run_pass()
        self.assertFalse(temp.exists(), 'the leftover went first')
        state, reason = book.state()
        self.assertEqual((state, reason), ('held', 'The names could not be written; the audiobook is unchanged. The new names did not read back: title'))
        record = book.writer.entry(book.lib.job_id)['record']
        self.assertEqual((record['names_retry'], record['temp_retry']), (series_backfill.REMOVAL_RETRY, series_backfill.REMOVAL_RETRY))
        self.assertEqual(sha(book.path), book.original, 'the book is unchanged')
        self.assertEqual(book.temps(), [], 'the failed try left no temporary file (0.31.3 removes its own on the NAS)')
        self.assertEqual(sorting_moves.reason_key(reason, sorting_moves.NAMES_NOT_WRITTEN_KEYS), 'tags_not_written', 'its key still reads')
        before = book.writer.entry(book.lib.job_id)
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertEqual(book.writer.entry(book.lib.job_id), before, 'one try only')

    def kept(self, book, temp, why):
        with nas_library(book.lib.root):
            book.writer.run_pass()
        entry = book.writer.entry(book.lib.job_id)
        record = entry['record']
        self.assertTrue(temp.exists(), 'kept')
        self.assertEqual(record['temp_kept']['reason'], why)
        self.assertNotIn('temp_removed', record)
        self.assertNotIn('names_retry', record, 'no fresh try when the file stayed')
        self.assertEqual(record['temp_retry'], series_backfill.REMOVAL_RETRY)
        self.assertEqual((entry['state'], entry['reason']), ('held', 'The names could not be written; the audiobook is unchanged. A temporary file is still there: ' + str(temp)),
                         "Judy 6: the kept variant, with the file's path")
        before = book.writer.entry(book.lib.job_id)
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertEqual(book.writer.entry(book.lib.job_id), before, 'tried once: nothing more')
        self.assertTrue(temp.exists())
        return record

    def test_a_temporary_written_after_the_hold_is_kept(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = self.leave(book)
        later = __import__('time').time() + 120
        os.utime(temp, (later, later))
        self.kept(book, temp, 'The temporary file changed after the app last handled it; it was left in place.')

    def test_a_temporary_another_record_names_is_kept(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = self.leave(book)
        with connect(book.lib.db) as db:
            db.execute("UPDATE owned_artifacts SET kind='output' WHERE path=?", (str(temp),))
        self.kept(book, temp, 'Another record of the app uses this file; it was left in place.')

    def test_a_temporary_whose_audio_is_not_the_books_is_kept(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = self.leave(book)
        stat = temp.stat()
        top, _index, _moves = quicktime_chapters._layout(temp)
        at, length = next((at, length) for kind, at, length in top if kind == b'mdat')
        data = bytearray(temp.read_bytes())
        data[at + length // 2] ^= 1  # one audio byte, the time put back: only the media proof can see it
        temp.write_bytes(data)
        os.utime(temp, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        with mock.patch.object(series_backfill, '_log') as log:
            self.kept(book, temp, "The temporary file's audio differs from the book's; it was left in place.")
        self.assertTrue(any('Media bytes changed' in call.args[0] for call in log.call_args_list), 'the exact media error goes to the log only')

    def test_a_temporary_is_kept_when_the_books_own_file_does_not_match_its_record(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = self.leave(book)
        data = bytearray(book.path.read_bytes())
        data[-20] ^= 1
        book.path.write_bytes(data)
        self.kept(book, temp, "The book's file changed since the app checked it; the temporary file was left in place.")

    def test_a_hold_for_another_reason_is_not_touched(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = self.leave(book)
        with connect(book.lib.db) as db:
            db.execute('UPDATE name_writes SET reason=? WHERE job_id=?', (name_write.NAMES_FAILED + 'Another failure', book.lib.job_id))
        before = book.writer.entry(book.lib.job_id)
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertEqual(book.writer.entry(book.lib.job_id), before)
        self.assertTrue(temp.exists())

    def test_the_series_writes_own_leftover_is_removed_the_same_way(self):
        lib = Library(Path(tempfile.mkdtemp(dir=base.AREA)))
        self.addCleanup(lambda: __import__('shutil').rmtree(lib.base, True))
        backfill = lib.backfill()
        with nas_library(lib.root), as_0312(), mock.patch.object(series_backfill.SeriesBackfill, '_read_back', side_effect=series_backfill.Held('Series tags did not read back: album')):
            backfill.run_pass()
        temp = lib.path.parent / (series_backfill.TEMP_PREFIX + lib.job_id + '.m4b')
        self.assertTrue(temp.exists())
        with connect(lib.db) as db:  # tried again, as an approval does: 0.31.2 holds it on its own leftover
            db.execute("UPDATE series_backfill SET state='pending' WHERE job_id=?", (lib.job_id,))
        with nas_library(lib.root), as_0312():
            backfill.run_pass()
        self.assertEqual(lib.state(backfill), ('held', series_backfill.APPLY_HOLD + retained_text(temp)))
        with nas_library(lib.root):
            backfill.run_pass()
        self.assertFalse(temp.exists())
        self.assertEqual(backfill.entry(lib.job_id)['record']['temp_removed']['method'], native_io.NAS_LEGACY)
        self.assertEqual(sha(lib.path), lib.original)


class HoldReasonTests(unittest.TestCase):
    """Judy's late-write clean-up spec, section 5 (Sergei's ruling 3): the thirteen hold reasons in "old file" and "new file",
    stored without the engine's prefix, at every place that raises them; section 6's kept-file reasons. Driven where a
    fixture can cause one; read as the exact string where none can (N3: the old file's own check fails first)."""

    SPEC = {'CATALOG_MISMATCH': 'The catalog does not match the new file; both files kept.',
            'NEW_CHANGED_OR_MISSING': 'The new file changed or is missing; the old file is kept.',
            'TEMP_CHANGED': 'The temporary file changed since the app made it; it was left in place.',
            'TEMP_OTHER_NAME': 'The temporary file is also stored under another name; it was left in place.',
            'SAME_FILE': 'The old and new files are the same file; nothing was removed.',
            'FOLDER_CHANGED': "The book's folder changed since the app checked it; nothing was removed.",
            'NOT_ONE_FOLDER': 'The old and new files are not recorded in the same folder; nothing was removed.',
            'OLD_STILL_THERE': 'The old file is still there after removal; both files kept.',
            'OLD_MISSING': 'The old file is missing, and the app did not remove it.',
            'TEMP_STILL_THERE': 'The temporary file is still there after removal; it was left in place.',
            'WITHDRAW_KEPT': 'The audiobook was moved meanwhile; the catalog is unchanged. The new file could not be removed; both files kept.',
            'WITHDRAWN': 'The audiobook was moved meanwhile; the catalog is unchanged; the new file was removed.',
            'TEMP_NAMED': 'Another record of the app uses this file; it was left in place.',
            'TEMP_BOOK_UNNAMED': "The catalog does not match the book's file; the temporary file was left in place.",
            'TEMP_BOOK_CHANGED': "The book's file changed since the app checked it; the temporary file was left in place.",
            'TEMP_AUDIO_DIFFERS': "The temporary file's audio differs from the book's; it was left in place.",
            'TEMP_WRITTEN_AFTER': 'The temporary file changed after the app last handled it; it was left in place.',
            'TEMP_CHANGED_DURING': 'The temporary file changed while the app checked it; it was left in place.'}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=base.AREA)
        self.addCleanup(self.temp.cleanup)
        self.lib = Library(Path(self.temp.name))

    def park(self):
        """The write left at 'cataloged' (the catalog committed, the old file not yet removed), as a crash leaves it."""
        backfill, real = self.lib.backfill(), series_backfill.SeriesBackfill.catalog

        def committed(self, job_id, record):
            real(self, job_id, record)
            raise sqlite3.OperationalError('crash after the catalog commit')
        with mock.patch.object(series_backfill.SeriesBackfill, 'catalog', committed):
            backfill.run_pass()
        self.assertEqual(self.lib.state(backfill)[0], 'cataloged')
        return backfill

    def record(self, **changes):
        with connect(self.lib.db) as db:
            record = json.loads(db.execute('SELECT record FROM series_backfill WHERE job_id=?', (self.lib.job_id,)).fetchone()[0])
            record.update(changes)
            db.execute('UPDATE series_backfill SET record=? WHERE job_id=?', (json.dumps(record, ensure_ascii=False), self.lib.job_id))
        return record

    def held(self, backfill, expected):
        backfill.resume(self.lib.job_id)
        state, reason = self.lib.state(backfill)
        self.assertEqual((state, reason), ('held', expected), 'stored as it is: no "Series recovery could not verify the files" before it')
        self.assertTrue(self.lib.path.exists() or expected == series_backfill.OLD_MISSING)

    def test_the_strings_are_the_specs(self):
        for name, text in self.SPEC.items():
            self.assertEqual(getattr(series_backfill, name), text, name)
        self.assertEqual(series_backfill.CHANGED, {'old': 'The old file changed since the app checked it; both files kept.',
                                                   'new': 'The new file changed since the app checked it; both files kept.'})
        self.assertEqual(series_backfill.OTHER_NAME['old'], 'The old file is also stored under another name; both files kept.')
        self.assertEqual((name_write.NAMES_UNCHANGED, name_write.TEMP_LEFT), ('The names could not be written; the audiobook is unchanged.', ' A temporary file is still there: '))
        # Judy 5.3: the constants that find the holds older versions stored keep their words.
        self.assertEqual(series_backfill.RECOVERY_HOLD, 'Series recovery could not verify the files; remaining copies kept: ')
        self.assertEqual(series_backfill.OLD_FOLDER_REASON, 'The recorded series paths do not share their original parent')
        import ast
        source = Path(series_backfill.__file__).read_text(encoding='utf-8')
        self.assertIn('raise Held(SAME_FILE)', source)
        # Every string the code passes in a call (what it raises, stores or logs; not its comments and docstrings).
        said = [node.value for call in ast.walk(ast.parse(source)) if isinstance(call, ast.Call)
                for node in ast.walk(call) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
        self.assertTrue(any('not in the sorted output folder' in text for text in said), 'control: the scan sees the strings the code passes')
        for old in ('verified identity and bytes', 'filesystem alias', 'identify the same file', 'disposition has not completed',
                    'without a removal receipt', 'rewritten copy', 'parent identity changed',
                    'do not share their original parent', 'does not name the rewritten'):
            self.assertFalse([text for text in said if old in text], old)
        # 5.3, the dependency: file_changed is found by the new words, and by the old ones of the holds already stored.
        for text in (series_backfill.CHANGED['old'], series_backfill.CHANGED['new'], 'The old file no longer matches its verified identity and bytes'):
            self.assertEqual(sorting_moves.reason_key(text, sorting_moves.NOT_MOVED_KEYS), 'file_changed', text)

    def test_the_new_file_changed(self):  # 2b at _protected
        backfill = self.park()
        stat = self.lib.target.stat()
        data = bytearray(self.lib.target.read_bytes())
        data[-20] ^= 1
        self.lib.target.write_bytes(data)
        os.utime(self.lib.target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.held(backfill, series_backfill.CHANGED['new'])

    def test_the_old_file_under_another_name(self):  # N1
        backfill = self.park()
        os.link(self.lib.path, self.lib.path.with_name('second name.m4b'))
        self.held(backfill, series_backfill.OTHER_NAME['old'])

    def test_the_folder_changed(self):  # N4
        backfill = self.park()
        self.record(parent_identity=[[1, 2, 3]])
        self.held(backfill, series_backfill.FOLDER_CHANGED)

    def test_not_recorded_in_one_folder(self):  # N5
        backfill = self.park()
        self.record(temp=str(self.lib.base / 'elsewhere' / 'x.m4b'))
        self.held(backfill, series_backfill.NOT_ONE_FOLDER)

    def test_the_old_file_still_there_after_removal(self):  # N6
        backfill = self.park()
        with mock.patch.object(VerifiedFile, 'dispose', lambda handle, **kwargs: None):
            self.held(backfill, series_backfill.OLD_STILL_THERE)

    def test_the_old_file_missing(self):  # N7
        backfill = self.park()
        self.lib.path.unlink()
        self.held(backfill, series_backfill.OLD_MISSING)

    def test_a_raw_error_keeps_the_engines_prefix(self):  # 5.3: not specced; the prefix stays, and so does the 115's matching
        backfill = self.park()
        with mock.patch.object(series_backfill.SeriesBackfill, '_names_rewritten', side_effect=native_io.BoundaryError('raw refusal')):
            backfill.resume(self.lib.job_id)
        self.assertEqual(self.lib.state(backfill), ('held', series_backfill.RECOVERY_HOLD + 'raw refusal'))

    def test_last_checks_rows_2a_and_3(self):
        class Held:
            def __init__(self, facts, digest=None):
                self.facts_, self.digest = facts, digest

            def refresh(self):
                return dict(self.facts_)

            def sha256(self):
                return self.digest
        record = {'old_identity': [1, 2, 3], 'old_size': 10, 'old_sha256': 'a', 'new_identity': [1, 2, 4], 'new_size': 11, 'new_sha256': 'b'}
        folder = mock.Mock()
        old = Held({'identity': [1, 2, 3], 'size': 10, 'links': 1, 'attributes': 0x80}, 'a')
        kept = Held({'identity': [1, 2, 4], 'size': 11, 'links': 1, 'attributes': 0x80})
        here = self.lib.path
        series_backfill.SeriesBackfill._last_checks(old, record, 'old', folder, kept, here)  # control: passes
        with self.assertRaises(series_backfill.Held) as caught:
            series_backfill.SeriesBackfill._last_checks(Held(dict(old.facts_, size=9), 'a'), record, 'old', folder, kept, here)
        self.assertEqual(str(caught.exception), series_backfill.CHANGED['old'])
        for kept_now, path in ((Held(dict(kept.facts_, identity=[9, 9, 9])), here), (kept, self.lib.base / 'gone.m4b')):
            with self.assertRaises(series_backfill.Held) as caught:
                series_backfill.SeriesBackfill._last_checks(old, record, 'old', folder, kept_now, path)
            self.assertEqual(str(caught.exception), series_backfill.NEW_CHANGED_OR_MISSING)

    def test_remove_owned_row_4_and_n2(self):
        class Owned:
            def __init__(self, links, later):
                self.links, self.later = links, later

            def facts(self):
                return {'identity': [1, 1, 1], 'links': self.links, 'attributes': 0x80}

            def refresh(self):
                return {'identity': self.later, 'links': 1, 'attributes': 0x80}

            def dispose(self, remote_legacy=None):
                remote_legacy(self)
        for owned, expected in ((Owned(2, [1, 1, 1]), series_backfill.TEMP_OTHER_NAME), (Owned(1, [9, 9, 9]), series_backfill.TEMP_CHANGED)):
            with self.assertRaises(native_io.BoundaryError) as caught:
                series_backfill.remove_owned(owned)
            self.assertEqual(str(caught.exception), expected)
        series_backfill.remove_owned(Owned(1, [1, 1, 1]))  # control: its own check passes

    def test_the_temporary_still_there_after_removal(self):  # N8
        temp = self.lib.path.parent / (series_backfill.TEMP_PREFIX + self.lib.job_id + '.m4b')
        temp.write_bytes(b'unproven')
        with mock.patch.object(VerifiedFile, 'dispose', lambda handle, **kwargs: None):
            with self.assertRaises(native_io.BoundaryError) as caught:
                series_backfill.SeriesBackfill._dispose_temporary(temp)
        self.assertEqual(str(caught.exception), series_backfill.TEMP_STILL_THERE)

    def test_withdraw_kept(self):  # N9
        from test_name_write_031 import Book
        book = Book(self)
        book.approve()
        with mock.patch.object(NameWrite, 'catalog', side_effect=sqlite3.OperationalError('database is locked')):
            book.writer.run_pass()
        new = Path(book.writer.entry(book.lib.job_id)['record']['new_path'])
        with connect(book.lib.db) as db:
            move = book_move.plan(db, job_id=book.lib.job_id, kind='base', candidate_id=book.lib.candidate, start=book_move.location(book.resolve()),
                                  folder=str(book.lib.root / 'Mine'), root=str(book.lib.root), origin='user', override_id='his')
            db.execute("UPDATE book_moves SET state='rename_intent' WHERE move_id=?", (move['move_id'],))
        book.writer.clock = lambda: 2_000_000_000.0
        with mock.patch.object(VerifiedFile, 'dispose', side_effect=native_io.BoundaryError('denied')), mock.patch.object(series_backfill, '_log') as log:
            book.writer.run_pass()
        self.assertEqual(book.state(), ('held', series_backfill.WITHDRAW_KEPT), 'one whole sentence')
        self.assertTrue(new.exists() and book.path.exists())
        self.assertTrue(any('denied' in call.args[0] for call in log.call_args_list), 'why: the log only')


class FakeLedger:
    def __init__(self, counts, **own):
        self.counts = counts
        self.__dict__.update(own)

    def _cleanup_counts(self):
        return dict(self.counts)


class CleanupViewTests(unittest.TestCase):
    """Judy's spec 2-4 and 7.1-7.4: the row, the Waiting item, main work, and the end for the status line."""

    @staticmethod
    def _merge(series, names, own):
        merge = type('Merge', (), {})()
        merge.series_backfill = FakeLedger(series, **own)
        merge.name_write = FakeLedger(names)
        return merge

    def test_counts_sum_both_writes_and_the_end_is_fixed_once(self):
        merge = self._merge({'total': 82, 'removed': 40, 'kept': 1, 'freed': 1000}, {'total': 33, 'removed': 1, 'kept': 0, 'freed': 50},
                            {'_cleanup_hand': 'The Name of the Wind', '_cleanup_started': 1234})
        view = series_backfill.cleanup_view(merge)
        self.assertEqual({key: view[key] for key in ('total', 'done', 'kept', 'left', 'title', 'in_hand', 'active', 'started', 'waiting')},
                         {'total': 115, 'done': 42, 'kept': 1, 'left': 73, 'title': 'The Name of the Wind', 'in_hand': True, 'active': True, 'started': 1234, 'waiting': False})
        self.assertEqual(series_backfill.outcome_view(merge)['last_age_ms'], None, 'no end while books are left')
        merge.series_backfill.counts = {'total': 82, 'removed': 77, 'kept': 5, 'freed': 9000}
        merge.name_write.counts = {'total': 33, 'removed': 33, 'kept': 0, 'freed': 3000}
        merge.series_backfill._cleanup_hand = None
        self.assertEqual(series_backfill.cleanup_view(merge)['left'], 0)
        end = series_backfill.outcome_view(merge)
        self.assertEqual((end['removed'], end['kept'], end['freed_bytes']), (110, 5, 12000))
        self.assertLess(end['last_age_ms'], 1000)
        series_backfill.cleanup_view(merge)  # a later poll does not restart its hour
        with mock.patch.object(series_backfill.time, 'monotonic', return_value=__import__('time').monotonic() + 3600):
            self.assertEqual(series_backfill.outcome_view(merge)['removed'], 0, 'gone after its hour')
        fresh = self._merge({'total': 82, 'removed': 77, 'kept': 5, 'freed': 9000}, {'total': 33, 'removed': 33, 'kept': 0, 'freed': 3000}, {})
        series_backfill.cleanup_view(fresh)
        self.assertEqual(series_backfill.outcome_view(fresh), {'removed': 0, 'kept': 0, 'freed_bytes': 0, 'last_age_ms': None},
                         'a relaunch after the end shows none: this engine never saw a book left')

    def work(self, merge):
        import background_work
        server = type('Server', (), {})()
        server.merge = merge
        return background_work.view(server, {}, {}, {}, False, None)

    def test_the_row_the_waiting_item_and_before_the_start(self):
        counts = {'total': 12, 'removed': 3, 'kept': 1, 'freed': 0}
        work = self.work(self._merge(counts, {'total': 0, 'removed': 0, 'kept': 0, 'freed': 0}, {'_cleanup_hand': 'Book', '_cleanup_started': 99}))
        row = next(row for row in work['rows'] if row['kind'] == 'late_cleanup')
        self.assertEqual({key: row[key] for key in ('subject', 'done', 'total', 'unit', 'kept', 'started', 'state', 'background')},
                         {'subject': 'Book', 'done': 4, 'total': 12, 'unit': 'books', 'kept': 1, 'started': 99, 'state': 'running', 'background': False})
        self.assertFalse(any(item['kind'] == 'late_cleanup' for item in work['waiting']))
        between = self.work(self._merge(counts, {'total': 0, 'removed': 0, 'kept': 0, 'freed': 0}, {'_cleanup_hand': None, '_cleanup_started': 99}))
        self.assertEqual(next(row for row in between['rows'] if row['kind'] == 'late_cleanup')['subject'], '', 'between two books the row stays')
        scan = self.work(self._merge(counts, {'total': 0, 'removed': 0, 'kept': 0, 'freed': 0}, {'_cleanup_waiting': True, '_cleanup_started': 99}))
        self.assertFalse(any(row['kind'] == 'late_cleanup' for row in scan['rows']), 'never both')
        item = next(item for item in scan['waiting'] if item['kind'] == 'late_cleanup')
        self.assertEqual((item['count'], item['blocker']['cause'], item['background']), (8, 'scan', False))
        before = self.work(self._merge(counts, {'total': 0, 'removed': 0, 'kept': 0, 'freed': 0}, {}))
        self.assertFalse(any(entry['kind'] == 'late_cleanup' for entry in before['rows'] + before['waiting']), 'nothing before the first book is in hand')
        done = self.work(self._merge({'total': 12, 'removed': 11, 'kept': 1, 'freed': 0}, {'total': 0, 'removed': 0, 'kept': 0, 'freed': 0},
                                     {'_cleanup_hand': None, '_cleanup_started': 99}))
        self.assertFalse(any(entry['kind'] == 'late_cleanup' for entry in done['rows'] + done['waiting']), 'gone once none is left')

    def test_main_work_never_all_done_over_books_left(self):
        import background_work
        quiet = lambda **more: background_work.finished_state([], [], {}, {}, {}, [], None, **more)[1]
        self.assertEqual(quiet(), 'all_done', 'control')
        self.assertEqual(quiet(late_left=73), 'continues', 'before the first book is in hand too')
        row = background_work._row(id='late_cleanup', kind='late_cleanup', subject='Book', done=1, total=2, unit='books', kept=0)
        self.assertEqual(background_work.finished_state([row], [], {}, {}, {}, [], None, late_left=1)[1], 'working')
        item = background_work._item(id='late_cleanup', kind='late_cleanup', count=1)
        self.assertEqual(background_work.finished_state([], [item], {}, {}, {}, [], None, late_left=1)[1], 'continues')
        self.assertFalse(background_work.is_background(row))

    def test_a_real_run_counts_from_the_ledger(self):
        lib = Library(Path(tempfile.mkdtemp(dir=base.AREA)))
        self.addCleanup(lambda: __import__('shutil').rmtree(lib.base, True))
        backfill = lib.backfill()
        with nas_library(lib.root), as_0312():
            backfill.run_pass()
        like_0312(lib.db, 'series_backfill', lib.job_id)
        merge = backfill.merge
        merge.series_backfill = backfill
        seen = []
        real = series_backfill.SeriesBackfill.resume

        def resume(self, job_id):
            seen.append(series_backfill.cleanup_view(merge))
            return real(self, job_id)
        retry = lib.backfill(merge)
        merge.series_backfill = retry
        with nas_library(lib.root), mock.patch.object(series_backfill.SeriesBackfill, 'resume', resume):
            retry.run_pass()
        self.assertEqual({key: seen[0][key] for key in ('total', 'done', 'left', 'in_hand', 'title')},
                         {'total': 1, 'done': 0, 'left': 1, 'in_hand': True, 'title': base.TITLE}, 'the book in hand, read from the ledger')
        old_size = retry.entry(lib.job_id)['record']['old_size']
        after = series_backfill.cleanup_view(merge)
        self.assertEqual((after['total'], after['removed'], after['kept'], after['freed_bytes'], after['in_hand']), (1, 1, 0, old_size, False))
        end = series_backfill.outcome_view(merge)
        self.assertEqual((end['removed'], end['kept'], end['freed_bytes']), (1, 0, old_size), 'the end, fixed when the last book settled')


class HeldBook:
    """A book in 0.31.2's held state on the simulated NAS (setUp, hold, later), for the review's cases."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=base.AREA)
        self.addCleanup(self.temp.cleanup)
        self.lib = Library(Path(self.temp.name))

    def hold(self):
        """The live state: 0.31.2's hold, both files on the (simulated) NAS."""
        lib = self.lib
        backfill = lib.backfill()
        with nas_library(lib.root), as_0312():
            backfill.run_pass()
        like_0312(lib.db, 'series_backfill', lib.job_id)
        self.assertEqual(lib.state(backfill), ('held', series_backfill.RECOVERY_HOLD + retained_text(lib.path)))
        return backfill

    def later(self, lib):
        """A pass an hour on: whatever waited for a minute is due."""
        backfill = lib.backfill()
        backfill.clock = lambda: __import__('time').time() + 3600
        return backfill


class ReviewMajorTests(HeldBook, unittest.TestCase):
    """Senua's 0.31.3 review at db4b366 (Docs/BooksArranger_CodeReview_v0.31.3_2026-11-25.md), M1-M4; Sergei 2026-11-25: fix all
    four in 0.31.3. Her probes P1-P3 are the first three repros. Each case failed on db4b366."""

    # M1: the clean-up stops for Quit and for "Restart to update" between two books (P3).
    def test_m1_a_stop_before_the_pass_touches_no_book(self):
        lib = self.lib
        before = self.hold().entry(lib.job_id)
        backfill = lib.backfill()
        backfill.stop.set()
        with nas_library(lib.root):
            backfill.run_pass()
        self.assertEqual(backfill.entry(lib.job_id), before, 'not sent back, not removed')
        self.assertTrue(lib.path.exists() and lib.target.exists())
        with nas_library(lib.root):
            lib.backfill().run_pass()
        self.assertEqual(lib.state(backfill), ('done', ''), 'control: without stop the clean-up runs')

    def test_m1_the_series_loop_stops_between_books(self):
        lib = self.lib
        self.hold()
        with connect(lib.db) as db:
            db.execute("INSERT INTO series_backfill VALUES('another','cataloged','',?,'now')", (json.dumps({'removal_retry': series_backfill.REMOVAL_RETRY}),))
        backfill, seen = lib.backfill(), []

        def finish(self, job_id, entry):
            seen.append(job_id)
            self.stop.set()  # Quit pressed while this book runs
        with mock.patch.object(series_backfill.SeriesBackfill, '_finish_active', finish):
            backfill.run_pass()
        self.assertEqual(len(seen), 1, 'the next book is not started')

    def test_m1_the_names_loop_stops_between_books(self):
        from test_name_write_031 import Book
        book = Book(self)
        with connect(book.lib.db) as db:
            for job in ('one', 'two'):
                db.execute("INSERT INTO name_writes VALUES(?,'cataloged','',?,'now')", (job, json.dumps({'removal_retry': series_backfill.REMOVAL_RETRY})))
        seen = []

        def finish(self, job_id, entry):
            seen.append(job_id)
            self.stop.set()
        with mock.patch.object(series_backfill.SeriesBackfill, '_finish_active', finish):
            book.writer.run_pass()
        self.assertEqual(len(seen), 1)

    # M2: a drive that does not answer waits; it never uses up the one-time retry (P2).
    def test_m2_a_drive_away_at_the_start_sends_back_nothing_and_the_retry_runs_when_it_answers(self):
        lib = self.lib
        before = self.hold().entry(lib.job_id)
        with nas_library(lib.root), mock.patch.object(series_backfill.SeriesBackfill, '_answers', staticmethod(lambda root: False), create=True):
            lib.backfill().run_pass()
        self.assertEqual(lib.backfill().entry(lib.job_id), before, 'still the 0.31.2 hold: not sent back while the drive is away')
        with nas_library(lib.root):
            lib.backfill().run_pass()
        self.assertEqual(lib.state(lib.backfill()), ('done', ''))
        self.assertFalse(lib.path.exists())

    def test_m2_a_drive_lost_during_a_book_waits_instead_of_holding(self):
        lib = self.lib
        self.hold()

        def away(self):
            raise native_io.AncestorUnavailable('An inspected destination ancestor is unavailable')
        with nas_library(lib.root), mock.patch.object(native_io.DirectoryBoundary, '__enter__', away):
            lib.backfill().run_pass()
        entry = lib.backfill().entry(lib.job_id)
        self.assertEqual((entry['state'], entry['record'].get('removal_retry')), ('cataloged', series_backfill.REMOVAL_RETRY), 'waits at its last step, not held')
        self.assertTrue(lib.path.exists() and lib.target.exists())
        self.assertEqual(lib.backfill()._cleanup_counts()['kept'], 0)
        with nas_library(lib.root):
            self.later(lib).run_pass()
        self.assertEqual(lib.state(lib.backfill()), ('done', ''), 'finished once the drive is back')
        self.assertFalse(lib.path.exists())

    def test_m2_card_and_hobb_keep_their_fresh_try_through_a_drive_drop(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = LeftoverTemporaryTests.leave(self, book)
        before = book.writer.entry(book.lib.job_id)

        def away(self):
            raise native_io.AncestorUnavailable('An inspected destination ancestor is unavailable')
        with nas_library(book.lib.root), mock.patch.object(native_io.DirectoryBoundary, '__enter__', away):
            book.writer.run_pass()
        self.assertEqual(book.writer.entry(book.lib.job_id), before, 'no mark, no try used: it waits for the drive')
        self.assertTrue(temp.exists())
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertFalse(temp.exists())
        self.assertEqual(book.state(), ('done', ''), 'the leftover goes and the fresh try runs once the drive answers')

    def test_m2_a_drive_drop_during_the_fresh_try_does_not_use_it_up(self):
        from test_name_write_031 import Book, ENGLISH
        book = Book(self)
        temp = LeftoverTemporaryTests.leave(self, book)

        def away(*args, **kwargs):
            raise native_io.AncestorUnavailable('An inspected destination ancestor is unavailable')
        with nas_library(book.lib.root), mock.patch.object(NameWrite, '_write', away):
            book.writer.run_pass()
        self.assertFalse(temp.exists(), 'the leftover went')
        entry = book.writer.entry(book.lib.job_id)
        self.assertIn(entry['state'], ('pending', 'deferred'), 'the fresh try waits for the drive; it is not used up')
        self.assertEqual(sha(book.path), book.original)
        book.writer.clock = lambda: __import__('time').time() + 3600
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertEqual(book.state(), ('done', ''))
        self.assertEqual(book.manifest()['metadata']['title'], ENGLISH)

    # M3: an old file that cannot be proven gone is never recorded as removed (P1).
    def test_m3_an_old_file_already_missing_is_held_n7_and_not_counted_removed(self):
        lib = self.lib
        self.hold()
        lib.path.unlink()  # removed by hand after 0.31.2
        with nas_library(lib.root):
            lib.backfill().run_pass()
        self.assertEqual(lib.state(lib.backfill()), ('held', series_backfill.OLD_MISSING))
        counts = lib.backfill()._cleanup_counts()
        self.assertEqual((counts['removed'], counts['kept'], counts['freed']), (0, 1, 0))

    def test_m3_an_old_file_that_cannot_be_seen_is_never_recorded_removed(self):
        import os as real_os
        lib = self.lib
        self.hold()
        old = os.path.normcase(str(lib.path))
        real_exists, real_lstat = Path.exists, real_os.lstat

        def exists(path, *args, **kwargs):  # the bundled Python 3.14 answers False on any OSError (a network error)
            return False if os.path.normcase(str(path)) == old else real_exists(path, *args, **kwargs)

        def lstat(path, *args, **kwargs):
            if os.path.normcase(str(path)) == old:
                raise OSError(64, 'The specified network name is no longer available')
            return real_lstat(path, *args, **kwargs)
        with nas_library(lib.root), mock.patch.object(Path, 'exists', exists), mock.patch.object(real_os, 'lstat', lstat):
            lib.backfill().run_pass()
        entry = lib.backfill().entry(lib.job_id)
        self.assertNotEqual(entry['state'], 'done', 'not recorded as removed')
        self.assertTrue(lib.path.exists(), 'the old file is still there')
        self.assertEqual(lib.backfill()._cleanup_counts()['removed'], 0)
        with nas_library(lib.root):
            self.later(lib).run_pass()
        self.assertEqual(lib.state(lib.backfill()), ('done', ''), 'removed once it can be seen again')
        self.assertFalse(lib.path.exists())

    def test_m3_a_removal_is_never_confirmed_by_a_network_error(self):
        """M3's pattern in the removals' own last check (os.path.lexists answers False on any OSError): a file that is still
        there and cannot be seen is never taken as removed."""
        import os as real_os
        real_lstat, real_lexists = real_os.lstat, real_os.path.lexists
        for owner, prefix in ((series_backfill.SeriesBackfill, series_backfill.TEMP_PREFIX), (NameWrite, name_write.TEMP_PREFIX)):
            temp = self.lib.path.parent / (prefix + self.lib.job_id + '.m4b')
            temp.write_bytes(b'unproven')
            key = os.path.normcase(str(temp))

            def lstat(path, *args, **kwargs):
                if os.path.normcase(str(path)) == key:
                    raise OSError(64, 'The specified network name is no longer available')
                return real_lstat(path, *args, **kwargs)

            def lexists(path):  # as Python answers on a network error: False
                return False if os.path.normcase(str(path)) == key else real_lexists(path)
            with mock.patch.object(VerifiedFile, 'dispose', lambda handle, **kwargs: None), mock.patch.object(real_os, 'lstat', lstat), \
                    mock.patch.object(real_os.path, 'lexists', lexists):
                with self.assertRaises(OSError, msg=owner.__name__):
                    owner._dispose_temporary(temp)
            self.assertTrue(temp.exists(), 'still there, and not reported removed')
            temp.unlink()

    # M4: a refused removal of a write's own temporary file is logged and recorded, never swallowed.
    def test_m4_a_refused_temporary_removal_is_logged_and_recorded(self):
        lib = self.lib
        backfill = lib.backfill()
        with nas_library(lib.root), as_0312(), mock.patch.object(series_backfill, '_log') as log, \
                mock.patch.object(series_backfill.SeriesBackfill, '_read_back', side_effect=series_backfill.Held('Series tags did not read back: album')):
            backfill.run_pass()
        temp = lib.path.parent / (series_backfill.TEMP_PREFIX + lib.job_id + '.m4b')
        self.assertTrue(temp.exists(), 'refused on the NAS as 0.31.2 refused it')
        left = backfill.entry(lib.job_id)['record'].get('temp_left') or {}
        self.assertEqual(left.get('path'), str(temp), 'recorded with the hold')
        self.assertEqual(left.get('reason'), retained_text(temp))
        self.assertTrue(any(str(temp) in call.args[0] and retained_text(temp) in call.args[0] for call in log.call_args_list), 'one log line with why and where')


class ReviewMinorTests(HeldBook, unittest.TestCase):
    """Senua's 0.31.3 review, m1-m5 (Sergei 2026-11-25: in this batch too). m6 needs a sentence Judy words (not built).
    Each case failed before its fix."""

    def test_m1_a_write_during_the_count_read_never_leaves_a_stale_count(self):  # P4
        import contextlib as ctx
        lib = self.lib
        self.hold()
        backfill = lib.backfill()
        backfill._retry_retained_removals()
        self.assertEqual(backfill.entry(lib.job_id)['state'], 'cataloged')
        real, fired = series_backfill.connect, []

        @ctx.contextmanager
        def racing(path):
            with real(path) as db:
                yield db
            if not fired:
                fired.append(1)
                backfill._set(lib.job_id, 'done', '', backfill.entry(lib.job_id)['record'])  # the other thread's book settles meanwhile
        backfill.__dict__['_cleanup_cache'] = None
        with mock.patch.object(series_backfill, 'connect', racing):
            backfill._cleanup_counts()
        self.assertEqual(backfill._cleanup_counts()['removed'], 1, 'the count is read again, never the stale one')

    def test_m2_one_book_is_cleaned_up_by_one_write_at_a_time(self):
        lib = self.lib
        backfill = self.hold()
        names = NameWrite(backfill.merge, stage=lib.base / 'names-stage')
        series_record = backfill.entry(lib.job_id)['record']
        with connect(lib.db) as db:  # the same book also held at its last step in the names ledger
            db.execute('INSERT INTO name_writes VALUES(?,?,?,?,?)', (lib.job_id, 'held', series_backfill.RECOVERY_HOLD + retained_text(series_record['old_path']),
                                                                    json.dumps(series_record, ensure_ascii=False), 'now'))
        with nas_library(lib.root):
            names._retry_retained_removals()
            self.assertEqual(names.entry(lib.job_id)['state'], 'held', 'the series write goes first')
            backfill._retry_retained_removals()
            names._retry_retained_removals()
        self.assertEqual((backfill.entry(lib.job_id)['state'], names.entry(lib.job_id)['state']), ('cataloged', 'held'), 'never both at once')
        with connect(lib.db) as db:
            db.execute("UPDATE name_writes SET state='cataloged' WHERE job_id=?", (lib.job_id,))
        with mock.patch.object(NameWrite, 'resume') as resume, mock.patch.object(series_backfill, 'cleanup_view'):
            names._finish_active(lib.job_id, names.entry(lib.job_id))
        resume.assert_not_called()
        self.assertGreater(names.entry(lib.job_id)['record'].get('next_attempt', 0), 0, 'it waits for the series write to settle')

    def test_m3_a_hold_this_version_made_never_joins_the_run(self):
        lib = self.lib
        backfill = lib.backfill()
        with nas_library(lib.root), as_0312():
            backfill.run_pass()  # a removal refused by 0.31.3 itself: the same words as 0.31.2's hold
        self.assertEqual(lib.state(backfill), ('held', series_backfill.RECOVERY_HOLD + retained_text(lib.path)))
        with nas_library(lib.root):
            lib.backfill().run_pass()
        entry = lib.backfill().entry(lib.job_id)
        self.assertEqual((entry['state'], entry['record'].get('removal_retry')), ('held', None), 'not sent back: the run is fixed at its start')
        self.assertEqual(lib.backfill()._cleanup_counts()['total'], 0)
        self.assertTrue(lib.path.exists() and lib.target.exists())

    def test_m4_a_count_error_is_logged_and_never_stops_the_pass(self):
        lib = self.lib
        self.hold()
        with nas_library(lib.root), mock.patch.object(series_backfill, 'cleanup_view', side_effect=sqlite3.OperationalError('database is locked')), \
                mock.patch.object(series_backfill, '_log') as log:
            lib.backfill().run_pass()
        self.assertEqual(lib.state(lib.backfill()), ('done', ''), 'the book finished; the count error did not replace anything')
        self.assertTrue(any('database is locked' in call.args[0] for call in log.call_args_list), 'one log line')

    def test_m5_the_selection_does_not_follow_the_display_wording(self):
        from test_name_write_031 import Book
        lib = self.lib
        self.hold()
        entry = lib.backfill().entry(lib.job_id)
        self.assertTrue(series_backfill.SeriesBackfill._removal_retained(entry), 'control')
        with mock.patch.object(series_backfill, 'RECOVERY_HOLD', 'Reworded: '), mock.patch.object(native_io, 'retained_text', lambda path: 'Reworded ' + str(path)):
            self.assertTrue(series_backfill.SeriesBackfill._removal_retained(entry), 'a 0.31.2 hold is found by what 0.31.2 stored, whatever the screen now says')
        book = Book(self)
        temp = LeftoverTemporaryTests.leave(self, book)
        held = book.writer.entry(book.lib.job_id)
        self.assertEqual(book.writer._leftover_temporary(held), temp, 'control')
        with mock.patch.object(NameWrite, 'APPLY_HOLD', 'Reworded: '), mock.patch.object(name_write, 'NAMES_FAILED', 'Reworded: '), \
                mock.patch.object(native_io, 'retained_text', lambda path: 'Reworded ' + str(path)):
            self.assertEqual(book.writer._leftover_temporary(held), temp)


class KeptOldFileKeyTests(unittest.TestCase):
    """Judy's spec 4: a book of the clean-up whose old file a check kept is listed in "Could not be renamed or moved" under
    old_file_kept, whatever refusal or try put it there; any other book keeps its key."""

    def test_the_key(self):
        import rule_filing
        from test_name_write_031 import Book
        book = Book(self)
        with connect(book.lib.db) as db:
            db.execute("INSERT OR REPLACE INTO name_writes VALUES(?,?,?,?,?)", (book.lib.job_id, 'held', series_backfill.CHANGED['old'],
                                                                              json.dumps({'removal_retry': series_backfill.REMOVAL_RETRY}), 'now'))
            db.execute("INSERT OR REPLACE INTO name_writes VALUES(?,?,?,?,?)", ('other', 'held', 'x', json.dumps({}), 'now'))
        self.assertIn('old_file_kept', rule_filing.COULD_NOT_KEYS)
        self.assertEqual(book.filing._kept_old_files(), {book.lib.job_id})
        refused = lambda job: {'job_id': job, 'from': str(book.path), 'to': str(book.path) + 'x', 'refused': 'No.', 'refused_key': 'not_app_name', 'items': []}
        answer = {'items': [], 'refused': [refused(book.lib.job_id), refused('other')], 'output_root': str(book.lib.root)}
        with mock.patch.object(type(book.merge), 'sorting_moves', lambda self: answer, create=True):
            book.filing.tick(dispatch=False)
        keys = {entry['job_id']: entry['key'] for entry in book.filing.could_not()['entries']}
        self.assertEqual(keys, {book.lib.job_id: 'old_file_kept', 'other': 'not_app_name'})


if __name__ == '__main__':
    unittest.main()
