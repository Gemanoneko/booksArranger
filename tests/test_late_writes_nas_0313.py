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
        self.assertIn('no longer matches', entry['reason'])
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
        self.assertIn('The catalog does not name the rewritten file', reason)
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
        self.assertIn('the rewritten copy was removed', reason)
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

    def test_the_leftover_temporary_is_removed_after_its_proofs_and_the_book_is_unchanged(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = self.leave(book)
        digest, size = sha(temp), temp.stat().st_size
        reason = book.state()[1]
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertFalse(temp.exists())
        record = book.writer.entry(book.lib.job_id)['record']
        removed = record['temp_removed']
        self.assertEqual((removed['path'], removed['size'], removed['sha256'], removed['method']), (str(temp), size, digest, native_io.NAS_LEGACY))
        self.assertEqual(record['temp_retry'], series_backfill.REMOVAL_RETRY)
        self.assertNotIn('temp_kept', record)
        self.assertEqual(self.owned(book, temp), [], 'its ownership row goes with it')
        self.assertEqual(book.state(), ('held', reason), 'the write itself did not happen: it stays held')
        self.assertEqual(sha(book.path), book.original, "the book's own file is untouched")
        self.assertEqual((book.output()['final_path'], book.output()['sha256']), (str(book.path), book.original))
        before = book.writer.entry(book.lib.job_id)
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertEqual(book.writer.entry(book.lib.job_id), before, 'once: nothing more')

    def kept(self, book, temp, why):
        with nas_library(book.lib.root):
            book.writer.run_pass()
        record = book.writer.entry(book.lib.job_id)['record']
        self.assertTrue(temp.exists(), 'kept')
        self.assertIn(why, record['temp_kept']['reason'])
        self.assertNotIn('temp_removed', record)
        self.assertEqual(record['temp_retry'], series_backfill.REMOVAL_RETRY)
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
        self.kept(book, temp, 'written after the app kept it')

    def test_a_temporary_another_record_names_is_kept(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = self.leave(book)
        with connect(book.lib.db) as db:
            db.execute("UPDATE owned_artifacts SET kind='output' WHERE path=?", (str(temp),))
        self.kept(book, temp, 'Another record names the temporary file')

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
        self.kept(book, temp, 'Media bytes changed')

    def test_a_temporary_is_kept_when_the_books_own_file_does_not_match_its_record(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = self.leave(book)
        data = bytearray(book.path.read_bytes())
        data[-20] ^= 1
        book.path.write_bytes(data)
        self.kept(book, temp, "The book's own file does not match its record")

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


if __name__ == '__main__':
    unittest.main()
