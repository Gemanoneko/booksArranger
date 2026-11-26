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
import itertools
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


# Senua's re-review at 520ee66, M6 (her P7): what Windows answers when an SMB server cannot be reached, and Python raises
# as FileNotFoundError (ERROR_BAD_NETPATH, ERROR_BAD_NET_NAME). OSError(64, ...) never takes that class.
UNREACHABLE_AS_NOT_FOUND = (53, 67)


def network_error(path, code):
    """The error os.lstat raises for this Windows error code, as Python builds it (the class follows the code)."""
    return OSError(0, ctypes.FormatError(code).strip(), str(path), code)


@contextlib.contextmanager
def lstat_fails(path, code, times=None):
    """os.lstat of exactly this path fails with this Windows error (times: only the first so many calls)."""
    real, wanted, left = os.lstat, key(path), [times]

    def lstat(name, *args, **kwargs):
        if key(name) == wanted and (left[0] is None or left[0] > 0):
            if left[0] is not None:
                left[0] -= 1
            raise network_error(name, code)
        return real(name, *args, **kwargs)
    with mock.patch.object(os, 'lstat', lstat):
        yield


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
        identity = base.create_temp(temp, b'unproven partial write')
        with nas_library(lib.root), as_0312():
            with self.assertRaises(FileRemovalRetained):
                series_backfill.SeriesBackfill._dispose_temporary(temp, identity)
        self.assertTrue(temp.exists(), 'control: 0.31.2 kept it')
        with nas_library(lib.root), methods() as used:
            series_backfill.SeriesBackfill._dispose_temporary(temp, identity)
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
        identity = base.create_temp(temp, b'unproven partial write')
        with nas_library(book.lib.root), as_0312():
            with self.assertRaises(FileRemovalRetained):
                NameWrite._dispose_temporary(temp, identity)
        self.assertTrue(temp.exists(), 'control: 0.31.2 kept it (the two temporaries left on Z:)')
        with nas_library(book.lib.root), methods() as used:
            NameWrite._dispose_temporary(temp, identity)
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
        LeftoverTemporaryTests.legacy_temp_hold(book.writer, book.lib.job_id, temp)
        self.assertEqual(book.state(), ('held', 'The names could not be written; the audiobook is unchanged: Safe removal of “' + str(temp) + LIVE_SUFFIX),
                         'the two live holds, word for word')
        with connect(book.lib.db) as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT job_id,kind FROM owned_artifacts WHERE path=?', (str(temp),))], [(book.lib.job_id, 'temporary')])
        return temp

    @staticmethod
    def legacy_temp_hold(writer, job_id, temp):
        # The old writer tried to dispose an occupying file. Seed its exact persisted result;
        # the current writer must never repeat that unauthenticated second disposition.
        record = writer.entry(job_id)['record']
        record.pop('temp_identity', None)
        writer._set(job_id, 'held', writer.APPLY_HOLD + retained_text(temp), record)

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
        self.assertEqual((state, reason), ('held', 'Couldn’t update the names. The audiobook is unchanged. The new names did not read back: title'))
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

    def series_leftover(self):
        """A series write held on its own leftover temporary file, as 0.31.2 left one (none exists live; Judy's m6 table)."""
        lib = Library(Path(tempfile.mkdtemp(dir=base.AREA)))
        self.addCleanup(lambda: __import__('shutil').rmtree(lib.base, True))
        backfill = lib.backfill()
        with nas_library(lib.root), as_0312(), mock.patch.object(series_backfill.SeriesBackfill, '_read_back', side_effect=series_backfill.Held('Series tags did not read back: album')):
            backfill.run_pass()
        temp = lib.path.parent / (series_backfill.TEMP_PREFIX + lib.job_id + '.m4b')
        self.assertTrue(temp.exists())
        LeftoverTemporaryTests.legacy_temp_hold(backfill, lib.job_id, temp)
        self.assertEqual(lib.state(backfill), ('held', series_backfill.APPLY_HOLD + retained_text(temp)))
        return lib, backfill, temp

    def test_the_series_writes_own_leftover_is_removed_the_same_way(self):
        lib, backfill, temp = self.series_leftover()
        with nas_library(lib.root):
            backfill.run_pass()
        self.assertFalse(temp.exists())
        self.assertEqual(backfill.entry(lib.job_id)['record']['temp_removed']['method'], native_io.NAS_LEGACY)
        self.assertEqual(sha(lib.path), lib.original)
        # Judy's m6 table: the engine's opening stays, the false tail goes; the book stays held (no fresh try for a series write).
        self.assertEqual(lib.state(backfill), ('held', 'Series update failed; the audiobook is unchanged.'))

    def test_a_series_writes_leftover_kept_by_a_proof_says_where_it_is(self):
        lib, backfill, temp = self.series_leftover()
        later = __import__('time').time() + 120
        os.utime(temp, (later, later))  # written after the hold: a proof keeps it
        with nas_library(lib.root):
            backfill.run_pass()
        self.assertTrue(temp.exists())
        self.assertEqual(backfill.entry(lib.job_id)['record']['temp_kept']['reason'], series_backfill.TEMP_WRITTEN_AFTER)
        self.assertEqual(lib.state(backfill), ('held', 'Series update failed; the audiobook is unchanged. A temporary file is still there: ' + str(temp)))


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
        identity = base.create_temp(temp, b'unproven')
        with mock.patch.object(VerifiedFile, 'dispose', lambda handle, **kwargs: None):
            with self.assertRaises(native_io.BoundaryError) as caught:
                series_backfill.SeriesBackfill._dispose_temporary(temp, identity)
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
    def _merge(series, names, own, scan=False):
        merge = type('Merge', (), {})()
        merge.series_backfill = FakeLedger(series, **own)
        merge.name_write = FakeLedger(names)
        if scan:  # a library scan running now (Futaba's m6: the Waiting item lasts only as long as the scan)
            merge.inventory = type('Inventory', (), {'worker': type('Scan', (), {'is_alive': lambda self: True})()})()
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
        scan = self.work(self._merge(counts, {'total': 0, 'removed': 0, 'kept': 0, 'freed': 0}, {'_cleanup_waiting': True, '_cleanup_started': 99}, scan=True))
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

    def test_m1_both_quit_routes_set_the_stop_the_loops_read(self):
        """Futaba's B1 (= M1): the desktop Quit (/api/desktop/quit: DesktopBackend._stop_work -> MergeService.stop_background)
        and the plain shutdown (/api/shutdown: finish_shutdown -> MergeService.close -> _close_lookups) both set the stop of
        both passes before they wait for a file change; the loops read it between books."""
        import time
        from merge_service import MergeService
        backfill = self.lib.backfill()
        merge = backfill.merge
        names = NameWrite(merge, stage=self.lib.base / 'names-stage')
        merge.series_backfill, merge.name_write = backfill, names
        MergeService.stop_background(merge)
        self.assertTrue(backfill.stop.is_set() and names.stop.is_set(), 'the desktop Quit, at its first step')
        for worker in (backfill, names):
            worker.stop.clear()
            MergeService._close_lookups(worker, time.monotonic())
            self.assertTrue(worker.stop.is_set(), 'the plain shutdown, before close waits for a file change')

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

    def test_futaba_m4_a_new_file_gone_before_the_retry_reads_row_3(self):
        """Futaba's QA m4: the new file deleted before the retry was held as engine speech ("Series recovery could not verify
        the files; remaining copies kept: Cannot protect exact file: [WinError 2] ..."). Judy's check 4 expects row 3."""
        lib = self.lib
        self.hold()
        lib.target.unlink()  # the new file, gone
        with nas_library(lib.root):
            lib.backfill().run_pass()
        self.assertEqual(lib.state(lib.backfill()), ('held', 'The new file changed or is missing; the old file is kept.'))
        self.assertEqual(sha(lib.path), lib.original, 'the old file is kept')
        self.assertEqual(lib.backfill()._cleanup_counts()['kept'], 1)

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
        """Senua's re-review at 520ee66, M6 (her P9): the network error is one Python raises as FileNotFoundError (53, 67:
        what Windows answers when the SMB server cannot be reached). The OSError(64) this case used could never reach that
        branch, so it passed while a real one burned the retry as N7."""
        import os as real_os
        for code in UNREACHABLE_AS_NOT_FOUND:
            with self.subTest(winerror=code):
                lib = self.lib = Library(Path(tempfile.mkdtemp(dir=self.temp.name)))
                self.hold()
                old = os.path.normcase(str(lib.path))
                real_exists, real_lstat = Path.exists, real_os.lstat

                def exists(path, *args, **kwargs):  # the bundled Python 3.14 answers False on any OSError (a network error)
                    return False if os.path.normcase(str(path)) == old else real_exists(path, *args, **kwargs)

                def lstat(path, *args, **kwargs):
                    if os.path.normcase(str(path)) == old:
                        raise network_error(path, code)
                    return real_lstat(path, *args, **kwargs)
                with nas_library(lib.root), mock.patch.object(Path, 'exists', exists), mock.patch.object(real_os, 'lstat', lstat):
                    lib.backfill().run_pass()
                entry = lib.backfill().entry(lib.job_id)
                self.assertEqual(entry['state'], 'cataloged', 'not recorded as removed, and not held N7: it waits')
                self.assertEqual(entry['reason'], series_backfill.FOLDER_WAIT)
                self.assertTrue(lib.path.exists(), 'the old file is still there')
                self.assertEqual(lib.backfill()._cleanup_counts()['removed'], 0)
                with nas_library(lib.root):
                    self.later(lib).run_pass()
                self.assertEqual(lib.state(lib.backfill()), ('done', ''), 'removed once it can be seen again')
                self.assertFalse(lib.path.exists())

    def test_m3_a_removal_is_never_confirmed_by_a_network_error(self):
        """M3's pattern in the removals' own last check (os.path.lexists answers False on any OSError): a file that is still
        there and cannot be seen is never taken as removed. Senua's re-review, M6: with the codes Python raises as
        FileNotFoundError (53, 67), not OSError(64), which never reached that branch."""
        import os as real_os
        real_lstat, real_lexists = real_os.lstat, real_os.path.lexists
        for (owner, prefix), code in itertools.product(((series_backfill.SeriesBackfill, series_backfill.TEMP_PREFIX), (NameWrite, name_write.TEMP_PREFIX)),
                                                       UNREACHABLE_AS_NOT_FOUND):
            temp = self.lib.path.parent / (prefix + self.lib.job_id + '.m4b')
            identity = base.create_temp(temp, b'unproven')
            key = os.path.normcase(str(temp))

            def lstat(path, *args, **kwargs):
                if os.path.normcase(str(path)) == key:
                    raise network_error(path, code)
                return real_lstat(path, *args, **kwargs)

            def lexists(path):  # as Python answers on a network error: False
                return False if os.path.normcase(str(path)) == key else real_lexists(path)
            with mock.patch.object(VerifiedFile, 'dispose', lambda handle, **kwargs: None), mock.patch.object(real_os, 'lstat', lstat), \
                    mock.patch.object(real_os.path, 'lexists', lexists):
                with self.assertRaises(OSError, msg='%s, WinError %d' % (owner.__name__, code)):
                    owner._dispose_temporary(temp, identity)
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


class FutabaMinorTests(HeldBook, unittest.TestCase):
    """Futaba's 0.31.3 QA minors m2, m6 and m8 (Sergei 2026-11-25: every minor in 0.31.3). Each case failed before its fix."""

    def test_m2_a_state_read_does_not_end_the_start_delay(self):
        import time
        backfill = self.lib.backfill()
        passes = []
        backfill.run_pass = lambda: passes.append(time.monotonic())
        with mock.patch.object(series_backfill, 'START_DELAY', 2.0):
            begun = time.monotonic()
            backfill.start()
            try:
                while time.monotonic() - begun < 1.0:
                    backfill.summary()  # the page's /api/state, every poll: nothing is counted yet
                    time.sleep(0.05)
                self.assertEqual(passes, [], 'no pass (and no clean-up) before the start delay, whatever reads the state')
                while not passes and time.monotonic() - begun < 10:
                    time.sleep(0.05)
            finally:
                backfill.close()
        self.assertTrue(passes, 'the first pass runs once the delay is over')
        self.assertGreaterEqual(passes[0] - begun, 1.9)

    def test_m8_the_total_covers_both_writes_from_the_start(self):
        lib = self.lib
        backfill = self.hold()
        merge = backfill.merge
        names = NameWrite(merge, stage=lib.base / 'names-stage')
        merge.series_backfill, merge.name_write = backfill, names
        series_record = backfill.entry(lib.job_id)['record']
        with connect(lib.db) as db:  # a hold 0.31.2 left in the names ledger too (as the 33)
            db.execute('INSERT INTO name_writes VALUES(?,?,?,?,?)', (lib.job_id, 'held', series_backfill.RECOVERY_HOLD + retained_text(series_record['old_path']),
                                                                    json.dumps(series_record, ensure_ascii=False), 'now'))
        totals = [series_backfill.cleanup_view(merge)['total']]  # at launch: nothing sent back yet
        with nas_library(lib.root):
            backfill._retry_retained_removals()  # the series pass queues its books first
            totals.append(series_backfill.cleanup_view(merge)['total'])
            names._retry_retained_removals()  # the names pass waits for the series write of the same book (Senua m2)
            totals.append(series_backfill.cleanup_view(merge)['total'])
            backfill.run_pass()
            done = series_backfill.cleanup_view(merge)
            totals.append(done['total'])
            names._retry_retained_removals()  # now the names pass queues its book
            totals.append(series_backfill.cleanup_view(merge)['total'])
        self.assertEqual(names.entry(lib.job_id)['record'].get('removal_retry'), series_backfill.REMOVAL_RETRY, 'control: both were queued')
        self.assertEqual(totals, [2, 2, 2, 2, 2], 'the total never grows during the run')
        self.assertEqual((done['done'], done['left']), (1, 1), 'the bar only moves forward')

    def test_m6_when_the_scan_ends_the_row_replaces_the_waiting_item_at_once(self):
        import threading
        lib = self.lib
        backfill = self.hold()
        backfill._retry_retained_removals()
        scanning = threading.Event()
        scanning.set()
        backfill.merge.inventory.worker = type('Scan', (), {'is_alive': lambda self: scanning.is_set()})()
        with mock.patch.object(series_backfill.SeriesBackfill, 'resume') as resume:
            backfill._finish_active(lib.job_id, backfill.entry(lib.job_id))
        resume.assert_not_called()
        page = type('Merge', (), {})()  # what /api/state reads
        page.series_backfill, page.inventory = backfill, backfill.merge.inventory

        def late(work):
            return ([row for row in work['rows'] if row['kind'] == 'late_cleanup'], [item for item in work['waiting'] if item['kind'] == 'late_cleanup'])
        rows, items = late(CleanupViewTests.work(self, page))
        self.assertEqual((len(rows), len(items)), (0, 1), 'while the scan runs: the Waiting item')
        scanning.clear()  # the scan ends; the book's next try is up to a minute away
        rows, items = late(CleanupViewTests.work(self, page))
        self.assertEqual((len(rows), len(items)), (1, 0), 'the row replaces the item in the same update')
        self.assertEqual({key: rows[0][key] for key in ('subject', 'done', 'total')}, {'subject': '', 'done': 0, 'total': 1})
        self.assertIsInstance(rows[0]['started'], int, 'its elapsed time ticks from when the clean-up was taken up')


class ReReviewTests(HeldBook, unittest.TestCase):
    """Senua's 0.31.3 re-review at 520ee66 (Docs/BooksArranger_CodeReview_v0.31.3_2026-11-25.md, "Re-review at 520ee66"):
    M5, M6, m7 and m8, folded into 0.31.3 by Sergei's ruling 10 (2026-11-25). Her probes P5 and P7-P10 are the repros.
    Each case failed on 520ee66."""

    def at(self, hours):
        """A pass this many hours on: whatever waited for a minute is due."""
        backfill = self.lib.backfill()
        backfill.clock = lambda: __import__('time').time() + 3600 * hours
        return backfill

    # M6: only Windows error 2 says "not there" (P7); 3, 15, 53 and 67 are FileNotFoundError too, and are raised.
    def test_m6_only_error_2_reads_as_not_there(self):
        there = self.lib.path
        for code in (3, 15) + UNREACHABLE_AS_NOT_FOUND:
            with self.subTest(winerror=code), lstat_fails(there, code):
                self.assertIsInstance(network_error(there, code), FileNotFoundError, 'the class Python gives it')
                with self.assertRaises(OSError):
                    series_backfill.present(there)
        with lstat_fails(there, 2):
            self.assertIs(series_backfill.present(there), False, 'error 2: this name is not there')
        self.assertIs(series_backfill.present(there.with_name('missing.m4b')), False, 'a real missing name in a folder that answers')
        self.assertIs(series_backfill.present(there), True)

    def test_m6_a_removal_lost_to_a_drive_drop_is_never_recorded_done_on_a_network_error(self):
        """P8 (effect a): the NAS removal is lost to a drive drop (removal_intended stays True), then the next pass's one check
        of the old file gets 53 or 67. It was recorded done, removed and freed, with the old file still on the share."""
        lib = self.lib
        self.hold()
        dropped = []

        def lost(handle, verify, refusal):
            dropped.append(str(handle.path))
            raise native_io.BoundaryError('Exact-handle removal is unsupported or denied: [WinError 64] The specified network name is no longer available')
        with nas_library(lib.root), mock.patch.object(native_io.VerifiedFile, '_dispose_remote_legacy', lost), \
                mock.patch.object(series_backfill.SeriesBackfill, '_answers', staticmethod(lambda root: not dropped)):
            lib.backfill().run_pass()
        first = lib.backfill().entry(lib.job_id)
        self.assertEqual((first['state'], first['record'].get('removal_intended')), ('cataloged', True), 'control: the removal began and was lost')
        self.assertTrue(lib.path.exists())
        for hours, code in enumerate(UNREACHABLE_AS_NOT_FOUND, 1):
            with self.subTest(winerror=code):
                with nas_library(lib.root), lstat_fails(lib.path, code, times=1):
                    self.at(hours).run_pass()
                entry = lib.backfill().entry(lib.job_id)
                self.assertEqual(entry['state'], 'cataloged', 'never done while the old file is on the share')
                self.assertEqual(entry['reason'], series_backfill.FOLDER_WAIT)
                self.assertEqual(lib.backfill()._cleanup_counts()['removed'], 0)
                self.assertTrue(lib.path.exists())
        with nas_library(lib.root):
            self.at(3).run_pass()
        self.assertEqual(lib.state(lib.backfill()), ('done', ''))
        self.assertFalse(lib.path.exists(), 'removed for real once it can be seen')

    def test_m6_a_temporary_file_that_cannot_be_seen_keeps_its_record(self):
        """Effect c: _discard_temp forgot the record of a temporary file it could not see (53 or 67), with no log line."""
        lib = self.lib
        backfill = lib.backfill()
        temp = lib.path.parent / (series_backfill.TEMP_PREFIX + lib.job_id + '.m4b')
        temp.write_bytes(b'unproven')
        with connect(lib.db) as db:
            db.execute('INSERT OR REPLACE INTO owned_artifacts VALUES(?,?,?,?,?)', (str(temp), lib.job_id, 'temporary', '', 0))
        for code in UNREACHABLE_AS_NOT_FOUND:
            with self.subTest(winerror=code):
                record = {'temp': str(temp), 'root': str(lib.root), 'parent_identity': lib.output['parent_identity']}
                with lstat_fails(temp, code), mock.patch.object(series_backfill, '_log') as log:
                    backfill._discard_temp(lib.job_id, record)
                self.assertEqual((record.get('temp_left') or {}).get('path'), str(temp), 'recorded as kept')
                self.assertTrue(any(str(temp) in call.args[0] for call in log.call_args_list), 'said in the log')
                with connect(lib.db) as db:
                    self.assertEqual([tuple(r) for r in db.execute('SELECT job_id,kind FROM owned_artifacts WHERE path=?', (str(temp),))],
                                     [(lib.job_id, 'temporary')], 'its ownership row is kept')
                self.assertTrue(temp.exists())

    # M5: a folder that is gone while the drive answers is not a drive that is away (P5, P10).
    @staticmethod
    def rename_folder(path):
        folder = Path(path).parent
        moved = folder.with_name(folder.name + ' (renamed by hand)')
        os.rename(folder, moved)
        return moved

    @staticmethod
    def other_publication(lib):
        peer = lib.root / 'Another author' / 'Another book.m4b'
        peer.parent.mkdir()
        peer.write_bytes(b'other synthetic publication')
        with connect(lib.db) as db:
            db.execute('INSERT INTO verified_outputs VALUES(?,?,?,?,?)', (key(peer), sha(peer), 'peer', '[]', 'now'))
        return peer

    def test_m5_a_retried_book_whose_folder_is_gone_is_held_n4_and_the_run_ends(self):
        lib = self.lib
        self.hold()
        self.other_publication(lib)
        moved = self.rename_folder(lib.path)
        backfill = lib.backfill()
        backfill.merge.__dict__['series_backfill'] = backfill
        with nas_library(lib.root):
            backfill.run_pass()
        entry = backfill.entry(lib.job_id)
        self.assertEqual((entry['state'], entry['reason']), ('held', series_backfill.FOLDER_CHANGED), 'N4, not "The library drive is not answering" for good')
        counts = backfill._cleanup_counts()
        self.assertEqual((counts['total'], counts['removed'], counts['kept']), (1, 0, 1))
        self.assertEqual(series_backfill.cleanup_view(backfill.merge)['left'], 0, '"Removing old files" ends, so "All done" can show')
        self.assertTrue((moved / lib.path.name).exists() and (moved / lib.target.name).exists(), 'both files kept')
        with nas_library(lib.root):
            self.at(1).run_pass()
        self.assertEqual(lib.backfill().entry(lib.job_id), entry, 'settled: not tried again')

    def test_m5_a_write_of_names_whose_folder_is_gone_is_held_n4(self):
        from test_name_write_031 import Book
        book = Book(self)
        book.approve()
        moved = self.rename_folder(book.path)
        with nas_library(book.lib.root), mock.patch.object(series_backfill, '_log') as log:
            book.writer.run_pass()
        entry = book.writer.entry(book.lib.job_id)
        self.assertEqual((entry['state'], entry['reason']), ('held', series_backfill.FOLDER_CHANGED), 'not deferred for good')
        self.assertNotIn('temp_left', entry['record'], 'no temporary file is said kept where there is none')
        self.assertFalse(any('Temporary file kept' in call.args[0] for call in log.call_args_list))
        self.assertTrue((moved / book.path.name).exists())
        book.writer.clock = lambda: __import__('time').time() + 3600
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertEqual(book.writer.entry(book.lib.job_id), entry, 'settled')

    def test_m5_a_leftover_whose_folder_is_gone_settles(self):
        """An isolated renamed folder carries its copy with it. Both cleanup paths retain its last known path."""
        from test_name_write_031 import Book
        book = Book(self)
        temp = LeftoverTemporaryTests.leave(self, book)
        self.other_publication(book.lib)
        moved = self.rename_folder(book.path)
        logs = Path(self.temp.name) / 'Logs'
        logs.mkdir()
        with nas_library(book.lib.root), mock.patch.dict(os.environ, {series_backfill.LOG_DIR_ENV: str(logs)}):
            book.writer.run_pass()
            discard = book.writer.entry(book.lib.job_id)['record'].copy()
            book.writer._discard_temp(book.lib.job_id, discard)
        entry = book.writer.entry(book.lib.job_id)
        self.assertNotIn('temp_removed', entry['record'])
        self.assertNotIn('names_retry', entry['record'])
        self.assertEqual(discard['temp_left']['path'], str(temp))
        self.assertEqual(entry['record']['temp_kept']['reason'], series_backfill.TEMP_FOLDER_UNKNOWN)
        self.assertEqual(entry['state'], 'held')
        self.assertEqual(LeftoverTemporaryTests.owned(self, book, temp), [(book.lib.job_id, 'temporary')])
        self.assertEqual(len([line for line in CleanupLogFileTests.lines(logs) if str(temp) in line and series_backfill.TEMP_FOLDER_UNKNOWN in line]), 2)
        self.assertTrue((moved / temp.name).exists() and (moved / book.path.name).exists(), 'nothing was removed')
        book.writer.clock = lambda: __import__('time').time() + 3600
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertEqual(book.writer.entry(book.lib.job_id), entry, 'settled')

    def test_m5_the_drive_is_away_only_when_the_folder_cannot_be_told_gone(self):
        base_folder = Path(tempfile.mkdtemp(dir=self.temp.name))
        root = base_folder / 'Audiobooks Sorted'
        folder = root / 'Author' / 'Series'
        folder.mkdir(parents=True)
        record = {'root': str(root), 'old_path': str(folder / 'Book.m4b')}
        error = native_io.AncestorUnavailable('An inspected destination ancestor is unavailable')
        backfill = self.lib.backfill()
        self.assertTrue(backfill._drive_away(record, error), 'every folder there: a blip of the drive, it waits')
        with mock.patch.object(series_backfill.SeriesBackfill, '_answers', staticmethod(lambda root: False)):
            self.assertTrue(backfill._drive_away(record, error), 'the library folder does not answer: the drive')
        with lstat_fails(root / 'Author', 53):
            self.assertTrue(backfill._drive_away(record, error), 'a network error on the way: cannot be told, it waits')
        os.rename(root / 'Author', root / 'Author (renamed)')
        self.assertFalse(backfill._drive_away(record, error), 'a folder on the way is gone and the drive answers: it settles')
        with mock.patch.object(series_backfill.SeriesBackfill, '_answers', staticmethod(lambda root: False)):
            self.assertTrue(backfill._drive_away(record, error), 'the same with the library folder not answering: the drive')
        self.assertTrue(backfill._drive_away({'old_path': record['old_path']}, error), 'no root recorded: cannot be told, it waits')

    def test_later_page_of_catalog_witnesses_can_resolve_an_isolated_missing_folder(self):
        lib = self.lib
        before = self.hold().entry(lib.job_id)
        self.rename_folder(lib.path)
        with connect(lib.db) as db:
            for index in range(9):
                peer = lib.root / ('Peer-%02d' % index) / 'Book.m4b'
                db.execute('INSERT INTO verified_outputs VALUES(?,?,?,?,?)', (key(peer), 'synthetic', str(index), '[]', 'now'))
        peer.parent.mkdir()
        peer.write_bytes(b'only the ninth known witness is reachable')
        worker = lib.backfill()
        worker.run_pass()
        self.assertEqual(worker.entry(lib.job_id), before)
        worker.run_pass()
        self.assertEqual(lib.state(worker), ('held', series_backfill.FOLDER_CHANGED))

    def test_ancestor_refusal_with_secondary_network_code_reaches_terminal_hold(self):
        lib, worker = self.lib, self.hold()
        # The native boundary used exists() (False). The specific name probe can still retrieve Windows error 53.
        with mock.patch.object(worker, '_boundary', side_effect=native_io.AncestorUnavailable('ancestor unavailable')), \
                lstat_fails(lib.path.parent, 53), mock.patch.object(series_backfill, '_log') as log:
            for attempt in range(series_backfill.NETWORK_RETRIES + 1):
                worker.clock = lambda: 1000 + attempt * 60
                worker.run_pass()
        self.assertEqual(lib.state(worker), ('held', series_backfill.FOLDER_UNREACHABLE))
        self.assertTrue(lib.path.exists() and lib.target.exists())
        self.assertIn('WinError 53', log.call_args.args[0])

    def test_fresh_pre_catalog_network_hold_gets_names_sentence_and_one_audit(self):
        from test_name_write_031 import Book
        book = Book(self)
        LeftoverTemporaryTests.leave(self, book)
        with nas_library(book.lib.root):
            book.writer._clear_leftover_temporaries()
        with mock.patch.object(book.writer, '_write', side_effect=network_error(book.path, 59)), mock.patch.object(series_backfill, '_log') as log:
            for attempt in range(series_backfill.NETWORK_RETRIES + 1):
                book.writer.clock = lambda: 1000 + attempt * 60
                book.writer.run_pass()
        reason = name_write.FRESH_NAMES_FAILED + ' Couldn’t reach the book’s folder.'
        self.assertEqual(book.state(), ('held', reason))
        self.assertEqual(book.writer.fresh_failures(), {book.lib.job_id: reason})
        self.assertEqual(len(log.call_args_list), 1)
        self.assertIn('WinError 59', log.call_args.args[0])

    def test_network_error_after_disposal_never_claims_the_old_file_was_kept(self):
        lib, worker = self.lib, self.hold()
        present = series_backfill.present
        def unavailable_after_removal(path):
            if key(path) == key(lib.path) and not lib.path.exists():
                raise network_error(path, 59)
            return present(path)
        with nas_library(lib.root), mock.patch.object(series_backfill, 'present', unavailable_after_removal), \
                mock.patch.object(series_backfill, '_log') as log:
            for attempt in range(series_backfill.NETWORK_RETRIES + 1):
                worker.clock = lambda: 1000 + attempt * 60
                worker.run_pass()
        self.assertFalse(lib.path.exists(), 'the verified removal really happened')
        self.assertTrue(lib.target.exists())
        self.assertEqual(lib.state(worker), ('held', series_backfill.REMOVAL_UNCONFIRMED))
        self.assertEqual((worker._cleanup_counts()['removed'], worker._cleanup_counts()['freed']), (0, 0))
        self.assertIn('WinError 59', log.call_args.args[0])
        self.assertNotIn('kept', log.call_args.args[0])

    def write_lane(self, kind):
        if kind == 'names':
            from test_name_write_031 import Book
            book = Book(self)
            book.approve()
            return book.lib, book.writer
        lib = Library(Path(tempfile.mkdtemp(dir=self.temp.name)))
        return lib, lib.backfill()

    def test_collision_never_adopts_existing_file_or_replaces_prior_ownership(self):
        for kind, prior in itertools.product(('series', 'names'), (False, True)):
            with self.subTest(kind=kind, prior=prior):
                lib, writer = self.write_lane(kind)
                temp = lib.path.parent / (writer.TEMP_PREFIX + lib.job_id + '.m4b')
                temp.write_bytes(b'pre-existing occupant')
                with connect(lib.db) as db:
                    if prior:
                        db.execute('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)', (str(temp), 'another-job', 'temporary', 'existing', 7))
                    before = db.execute('SELECT * FROM owned_artifacts WHERE path=?', (str(temp),)).fetchall()
                with mock.patch.object(series_backfill, '_log') as log:
                    writer.run_pass()
                self.assertEqual(writer.entry(lib.job_id)['state'], 'held')
                self.assertEqual(temp.read_bytes(), b'pre-existing occupant')
                self.assertTrue(any(str(temp) in args.args[0] for args in log.call_args_list))
                with connect(lib.db) as db:
                    self.assertEqual(db.execute('SELECT * FROM owned_artifacts WHERE path=?', (str(temp),)).fetchall(), before)

    def test_abort_and_restart_keep_same_parent_replacement_and_path_only_records(self):
        class Crash(BaseException):
            pass
        for kind, phase in itertools.product(('series', 'names'), ('abort', 'restart', 'legacy')):
            with self.subTest(kind=kind, phase=phase):
                lib, writer = self.write_lane(kind)
                temp = lib.path.parent / (writer.TEMP_PREFIX + lib.job_id + '.m4b')
                retained = temp.with_suffix('.retained')
                def interrupt(*args):
                    if phase == 'abort':
                        raise series_backfill.Held('read-back stopped')
                    raise Crash()
                discard = writer._discard_temp
                def replace_before_discard(job_id, record):
                    # The exception released the write's held directory. Replace the file at the
                    # normal abort/discard boundary, immediately before it reacquires the folder.
                    temp.rename(retained)
                    temp.write_bytes(b'replacement')
                    return discard(job_id, record)
                with mock.patch.object(writer, '_read_back', interrupt):
                    if phase == 'abort':
                        with mock.patch.object(writer, '_discard_temp', replace_before_discard):
                            writer.run_pass()
                    else:
                        with self.assertRaises(Crash):
                            writer.run_pass()
                if phase == 'restart':
                    temp.rename(retained)
                    temp.write_bytes(b'replacement')
                if phase == 'legacy':
                    record = writer.entry(lib.job_id)['record']
                    record.pop('temp_identity')
                    writer._set(lib.job_id, 'writing', '', record)
                data = temp.read_bytes()
                writer.run_pass()
                entry = writer.entry(lib.job_id)
                self.assertEqual((entry['state'], entry['record']['temp_left']['reason']), ('held', series_backfill.TEMP_UNPROVEN))
                self.assertEqual(temp.read_bytes(), data)
                self.assertTrue(lib.path.is_file())
                with connect(lib.db) as db:
                    self.assertEqual(tuple(db.execute('SELECT job_id,kind FROM owned_artifacts WHERE path=?', (str(temp),)).fetchone()),
                                     (lib.job_id, 'temporary'))

    def test_recreated_parent_with_empty_original_name_never_confirms_temp_gone(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = LeftoverTemporaryTests.leave(self, book)
        moved = self.rename_folder(temp)
        temp.parent.mkdir()  # different directory at precisely the recorded name
        with nas_library(book.lib.root):
            book.writer.run_pass()
            record = book.writer.entry(book.lib.job_id)['record']
            temp.write_bytes(b'unrelated copy at the old name')
            book.writer._discard_temp(book.lib.job_id, record)
        self.assertEqual(record['temp_kept']['reason'], series_backfill.TEMP_FOLDER_UNKNOWN)
        self.assertEqual(record['temp_left']['reason'], series_backfill.TEMP_FOLDER_UNKNOWN)
        self.assertNotIn('names_retry', record)
        self.assertTrue((moved / temp.name).is_file())
        self.assertEqual(temp.read_bytes(), b'unrelated copy at the old name')
        self.assertEqual(LeftoverTemporaryTests.owned(self, book, temp), [(book.lib.job_id, 'temporary')])

    # m7: a short network error of another kind (not AncestorUnavailable, the library folder answering right after) waits.
    def waits_then_finishes(self, *patches):
        lib = self.lib
        self.hold()
        with nas_library(lib.root), contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            lib.backfill().run_pass()
        entry = lib.backfill().entry(lib.job_id)
        self.assertEqual((entry['state'], entry['reason']), ('cataloged', series_backfill.FOLDER_WAIT), 'reachable library, retry this file')
        self.assertTrue(lib.path.exists() and lib.target.exists())
        with nas_library(lib.root):
            self.at(1).run_pass()
        self.assertEqual(lib.state(lib.backfill()), ('done', ''), 'finished once the share answers')
        self.assertFalse(lib.path.exists())

    def test_m7_a_network_error_holding_the_folder_waits(self):
        def enter(boundary):  # native_io.DirectoryBoundary's own text, the code inside it
            raise native_io.BoundaryError(f'Destination directory cannot be protected: {ctypes.WinError(64)}')
        self.waits_then_finishes(mock.patch.object(native_io.DirectoryBoundary, '__enter__', enter))

    def test_m7_a_network_error_opening_the_old_file_waits(self):
        real, old = native_io.VerifiedFile.__enter__, key(self.lib.path)

        def enter(handle):
            if key(handle.path) == old:
                raise native_io.BoundaryError(f'Cannot protect exact file: {ctypes.WinError(121)}')
            return real(handle)
        self.waits_then_finishes(mock.patch.object(native_io.VerifiedFile, '__enter__', enter))

    def test_m7_a_network_error_rereading_the_old_files_identity_waits(self):
        real, old = native_io.VerifiedFile.refresh, key(self.lib.path)

        def refresh(handle):
            if key(handle.path) == old:
                raise native_io.ProtectedIdentityUnavailable(handle.path, 59)
            return real(handle)
        self.waits_then_finishes(mock.patch.object(native_io.VerifiedFile, 'refresh', refresh))

    def test_m7_a_network_error_on_the_kept_files_last_check_waits(self):
        """_last_checks read the kept file with os.path.lexists, which answers False on a network error: row 3, held for good."""
        real, new = native_io.VerifiedFile._dispose_remote_legacy, self.lib.target
        real_lexists = os.path.lexists

        def legacy(handle, verify, refusal):
            with lstat_fails(new, 64), mock.patch.object(os.path, 'lexists', lambda path: False if key(path) == key(new) else real_lexists(path)):
                return real(handle, verify, refusal)
        self.waits_then_finishes(mock.patch.object(native_io.VerifiedFile, '_dispose_remote_legacy', legacy))

    def test_m7_guard_an_error_that_is_not_the_network_still_holds(self):
        lib = self.lib
        self.hold()

        def enter(boundary):
            raise native_io.BoundaryError(f'Destination directory cannot be protected: {ctypes.WinError(5)}')
        with nas_library(lib.root), mock.patch.object(native_io.DirectoryBoundary, '__enter__', enter):
            lib.backfill().run_pass()
        state, reason = lib.state(lib.backfill())
        self.assertEqual((state, reason), ('held', series_backfill.RECOVERY_HOLD + 'Destination directory cannot be protected: ' + str(ctypes.WinError(5))))

    def test_m7_which_errors_are_the_network(self):
        network = series_backfill.network_lost
        cause = native_io.BoundaryError('Exact-handle removal is unsupported or denied')
        cause.__cause__ = OSError(0, 'x', None, 1231)
        for error in (OSError(0, 'x', None, 64), network_error('Z:\\a', 53), native_io.ProtectedIdentityUnavailable('Z:\\a', 121),
                      native_io.BoundaryError(f'Cannot protect exact file: {ctypes.WinError(59)}'), cause):
            self.assertTrue(network(error), repr(error))
        for error in (None, OSError(0, 'x', None, 5), network_error('Z:\\a', 2), network_error('Z:\\a', 3), native_io.BoundaryError('Cannot protect exact file: [WinError 32] in use'),
                      series_backfill.Held(series_backfill.FOLDER_CHANGED), KeyError('old_path')):
            self.assertFalse(network(error), repr(error))

    # m8: a crash between a leftover temporary file's removal and its record.
    def crash_after(self, book, temp, step):
        """The pass dies right after this step of the leftover's removal (the process ends: nothing after it runs, no
        handler sees it); the next run starts from what the catalog holds."""
        class Crash(BaseException):
            pass
        real = {'removed': series_backfill.remove_owned, 'forgotten': series_backfill.SeriesBackfill._forget_temporary}[step]

        def removed(handle):
            real(handle)
            raise Crash()

        def forgotten(writer, job_id, path):
            real(writer, job_id, path)
            if key(path) == key(temp):
                raise Crash()
        patch = mock.patch.object(series_backfill, 'remove_owned', removed) if step == 'removed' else \
            mock.patch.object(series_backfill.SeriesBackfill, '_forget_temporary', forgotten)
        with nas_library(book.lib.root), patch, self.assertRaises(Crash):
            book.writer.run_pass()
        self.assertFalse(temp.exists(), 'control: the file went')
        entry = book.writer.entry(book.lib.job_id)
        self.assertNotIn('temp_retry', entry['record'], 'control: its record was never written')
        self.assertEqual(entry['state'], 'held')

    def test_m8_a_crash_after_the_leftovers_removal_keeps_the_fresh_try(self):
        from test_name_write_031 import Book, ENGLISH
        for step in ('removed', 'forgotten'):  # before and after its ownership row went
            with self.subTest(crashed_after=step):
                book = Book(self)
                temp = LeftoverTemporaryTests.leave(self, book)
                self.crash_after(book, temp, step)
                with nas_library(book.lib.root), mock.patch.object(series_backfill, '_log') as log:
                    book.writer.run_pass()
                record = book.writer.entry(book.lib.job_id)['record']
                self.assertNotIn('temp_kept', record, 'not "kept": nothing is there')
                self.assertEqual({k: record['temp_removed'][k] for k in ('path', 'found_gone', 'method')}, {'path': str(temp), 'found_gone': True, 'method': None},
                                 'counted removed, and known as found gone (not removed by this pass)')
                self.assertFalse(any('A temporary file is still there' in call.args[0] for call in log.call_args_list))
                self.assertIn('Leftover temporary file already gone: ' + str(temp), [call.args[0] for call in log.call_args_list])
                self.assertEqual(LeftoverTemporaryTests.owned(self, book, temp), [], 'no ownership row is left for a file that is not there')
                self.assertEqual(book.state(), ('done', ''), "Sergei's ruling 4: the one fresh try ran")
                self.assertEqual(record['names_retry'], series_backfill.REMOVAL_RETRY)
                self.assertEqual(book.manifest()['metadata']['title'], ENGLISH)

    def test_m8_a_series_leftover_found_gone_drops_the_still_there_tail(self):
        lib, backfill, temp = LeftoverTemporaryTests.series_leftover(self)
        temp.unlink()  # gone after the hold (the crash window, or by hand)
        with nas_library(lib.root):
            backfill.run_pass()
        self.assertEqual(lib.state(backfill), ('held', series_backfill.SERIES_UNCHANGED), 'no false "A temporary file is still there"')
        self.assertTrue(backfill.entry(lib.job_id)['record']['temp_removed']['found_gone'])

    def test_m8_a_leftover_that_cannot_be_seen_is_never_taken_as_gone(self):
        """Guard, the other side: a network error on the leftover (53, 67) is doubt, never "found gone"; its proofs run as
        before and decide (here: written after the hold, so kept with why)."""
        from test_name_write_031 import Book
        for code in UNREACHABLE_AS_NOT_FOUND:
            with self.subTest(winerror=code):
                book = Book(self)
                temp = LeftoverTemporaryTests.leave(self, book)
                later = __import__('time').time() + 120
                os.utime(temp, (later, later))
                with nas_library(book.lib.root), lstat_fails(temp, code, times=1):
                    book.writer.run_pass()
                record = book.writer.entry(book.lib.job_id)['record']
                self.assertNotIn('temp_removed', record)
                self.assertNotIn('temp_retry', record)
                book.writer.clock = lambda: __import__('time').time() + 120
                with nas_library(book.lib.root):
                    book.writer.run_pass()
                self.assertEqual(book.writer.entry(book.lib.job_id)['record']['temp_kept']['reason'], series_backfill.TEMP_WRITTEN_AFTER)
                self.assertTrue(temp.exists())


class CleanupLogFileTests(HeldBook, unittest.TestCase):
    """0.31.3, Sergei's ruling 11 (Futaba's R-m1): the clean-up's log lines (series_backfill._log: a kept old file with its
    book's title, a removed or kept leftover, a kept temporary file) are kept on disk in the installation's own Logs folder,
    which the shell names (BOOKS_ARRANGER_LOGS_DIR, desktop/installation-paths.js childEnvironment). They went to stderr only,
    which the shell keeps as its last 16 KB in memory, so ruling 8's "count + log only" named the books in no log Sergei
    could open. Each case failed before the log file existed."""
    ENV = 'BOOKS_ARRANGER_LOGS_DIR'  # the shell's name for it; a contract across the two languages

    def logs(self):
        folder = Path(self.temp.name) / 'Logs'
        folder.mkdir()
        return folder

    @staticmethod
    def lines(folder, name='books-backend.log'):
        path = folder / name
        return path.read_text(encoding='utf-8').splitlines() if path.exists() else []

    def test_a_kept_books_line_with_its_title_is_in_the_log_file(self):
        lib = self.lib
        self.hold()
        lib.path.unlink()  # N7: the retried book is held again, and its line names it
        folder = self.logs()
        with mock.patch.dict(os.environ, {self.ENV: str(folder)}), nas_library(lib.root):
            lib.backfill().run_pass()
        self.assertEqual(lib.state(lib.backfill()), ('held', series_backfill.OLD_MISSING))
        lines = self.lines(folder)
        self.assertEqual(len(lines), 1, lines)
        self.assertRegex(lines[0], r'^Books Arranger \d{4}-\d\d-\d\d \d\d:\d\d:\d\d: Old file kept: ', 'the same line as stderr, with its time')
        self.assertTrue(lines[0].endswith(base.TITLE + ': ' + series_backfill.OLD_MISSING + ' (' + str(lib.path) + ')'), lines[0])

    def test_one_entry_is_one_line_in_utf8(self):
        folder = self.logs()
        with mock.patch.dict(os.environ, {self.ENV: str(folder)}):
            series_backfill._log('Old file kept: Сага теней: first\nsecond')
            series_backfill._log('Removed a leftover temporary file of an unfinished update')
        lines = self.lines(folder)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].endswith('Old file kept: Сага теней: first second'), lines[0])

    def test_source_refusal_and_late_write_share_rotation_and_escape_unencodable_text(self):
        import io
        from concurrent.futures import ThreadPoolExecutor
        folder, merge = self.logs(), self.lib.merge()
        stderr = io.StringIO()
        def refuse():
            for _ in range(2):
                merge._remove_missing([], [('job', {}, {'why': 'probe \udcff'})], 1)
        with mock.patch.dict(os.environ, {self.ENV: str(folder)}), mock.patch.object(series_backfill, 'LOG_LIMIT', 230), contextlib.redirect_stderr(stderr):
            series_backfill._log('start ' + 'x' * 155)
            with ThreadPoolExecutor(2) as workers:
                futures = [workers.submit(refuse), workers.submit(series_backfill._log, 'late write \ud800')]
                for future in futures:
                    future.result()
        lines = self.lines(folder, series_backfill.LOG_PREVIOUS) + self.lines(folder)
        self.assertEqual(sum('Missing finished books were not removed' in line for line in lines), 1)
        self.assertTrue(any(r'probe \udcff' in line for line in lines))
        self.assertTrue(any(r'late write \ud800' in line for line in lines))
        self.assertEqual(stderr.getvalue().count('Missing finished books were not removed'), 1)
        self.assertTrue((folder / series_backfill.LOG_PREVIOUS).is_file())

    def test_reachable_library_bounds_network_error_across_restarts(self):
        lib, folder = self.lib, self.logs()
        self.hold()
        for attempt in range(series_backfill.NETWORK_RETRIES + 1):
            worker = lib.backfill()
            worker.clock = lambda: 1000 + 60 * attempt
            with mock.patch.dict(os.environ, {self.ENV: str(folder)}), nas_library(lib.root), lstat_fails(lib.path, 59):
                worker.run_pass()
            entry = worker.entry(lib.job_id)
            if attempt < series_backfill.NETWORK_RETRIES:
                self.assertEqual((entry['state'], entry['reason'], entry['record']['next_attempt']), ('cataloged', series_backfill.FOLDER_WAIT, worker.clock() + 60))
        self.assertEqual((entry['state'], entry['reason']), ('held', series_backfill.FOLDER_UNREACHABLE))
        self.assertTrue(lib.path.is_file() and lib.target.is_file())
        self.assertEqual(worker._cleanup_counts(), {'total': 1, 'removed': 0, 'kept': 1, 'freed': 0})
        self.assertEqual(len(self.lines(folder)), 1)
        self.assertIn('WinError 59', self.lines(folder)[0])

    def test_leftover_has_bounded_network_retries_without_spending_names_try(self):
        from test_name_write_031 import Book
        book, logs = Book(self), self.logs()
        temp = LeftoverTemporaryTests.leave(self, book)
        for attempt in range(series_backfill.NETWORK_RETRIES + 1):
            book.writer.clock = lambda: 1000 + 60 * attempt
            with mock.patch.dict(os.environ, {self.ENV: str(logs)}), nas_library(book.lib.root), lstat_fails(temp, 53):
                book.writer.run_pass()
            entry = book.writer.entry(book.lib.job_id)
            if attempt < series_backfill.NETWORK_RETRIES:
                self.assertEqual(book.writer._next_wait(), 60)
                self.assertNotIn('temp_retry', entry['record'])
        self.assertEqual(entry['record']['temp_kept']['reason'], series_backfill.FOLDER_UNREACHABLE)
        self.assertNotIn('names_retry', entry['record'])
        self.assertTrue(temp.is_file() and book.path.is_file())
        self.assertEqual(LeftoverTemporaryTests.owned(self, book, temp), [(book.lib.job_id, 'temporary')])
        self.assertEqual(len(self.lines(logs)), 1)
        self.assertIn('WinError 53', self.lines(logs)[0])

    def test_empty_answering_share_preserves_retry_until_tree_returns(self):
        lib = self.lib
        before = self.hold().entry(lib.job_id)
        hidden = lib.base / 'detached volume'
        lib.root.rename(hidden)
        lib.root.mkdir()
        (lib.root / 'unrelated').mkdir()
        worker = lib.backfill()
        worker.merge.series_backfill = worker
        for _ in range(2):
            worker.run_pass()
            self.assertEqual(worker.entry(lib.job_id), before)
            self.assertEqual(worker._library_wait(before['record']), series_backfill.TREE_WAIT)
            self.assertEqual(worker._cleanup_counts(), {'total': 1, 'removed': 0, 'kept': 0, 'freed': 0})
            self.assertEqual(series_backfill.cleanup_view(worker.merge)['left'], 1)
            self.assertEqual(CleanupViewTests.work(self, worker.merge)['state'], 'continues')
        (lib.root / 'unrelated').rmdir()
        lib.root.rmdir()
        hidden.rename(lib.root)
        self.assertTrue(lib.path.exists() and lib.target.exists())
        with nas_library(lib.root):
            worker.run_pass()
        self.assertEqual(worker._cleanup_counts(), {'total': 1, 'removed': 1, 'kept': 0, 'freed': before['record']['old_size']})

    def test_fresh_names_failure_logs_book_and_cause_once_then_stays_held(self):
        from test_name_write_031 import Book
        book, logs = Book(self), self.logs()
        temp = LeftoverTemporaryTests.leave(self, book)
        ReReviewTests.other_publication(book.lib)
        real = book.writer._leftover_outcome
        def after_cleanup(entry, record, path):
            outcome = real(entry, record, path)
            ReReviewTests.rename_folder(book.path)
            return outcome
        with mock.patch.dict(os.environ, {self.ENV: str(logs)}), nas_library(book.lib.root), mock.patch.object(book.writer, '_leftover_outcome', after_cleanup):
            book.writer.run_pass()
            book.writer.run_pass()
        state, reason = book.state()
        self.assertEqual((state, reason), ('held', 'Couldn’t update the names. The audiobook is unchanged. The book’s folder changed since the app checked it.'))
        self.assertFalse(temp.exists())
        lines = [line for line in self.lines(logs) if 'Fresh names try failed' in line]
        self.assertEqual(len(lines), 1)
        self.assertIn(book.lib.job_id, lines[0])
        self.assertIn(reason, lines[0])
        book.filing.tick(dispatch=False)
        self.assertEqual(book.filing.could_not()['entries'][0]['names_failure'], reason)

    def test_fresh_names_wait_if_the_tree_disappears_after_temp_cleanup(self):
        from test_name_write_031 import Book
        book = Book(self)
        temp = LeftoverTemporaryTests.leave(self, book)
        with nas_library(book.lib.root):
            book.writer._clear_leftover_temporaries()
        self.assertFalse(temp.exists())
        hidden = book.lib.base / 'detached'
        book.lib.root.rename(hidden)
        book.lib.root.mkdir()
        book.writer.run_pass()
        self.assertEqual(book.state(), ('deferred', series_backfill.TREE_WAIT))
        book.lib.root.rmdir()
        hidden.rename(book.lib.root)
        book.writer.clock = lambda: __import__('time').time() + 120
        with nas_library(book.lib.root):
            book.writer.run_pass()
        self.assertEqual(book.state(), ('done', ''))

    def test_the_file_is_bounded_and_keeps_the_previous_one(self):
        folder = self.logs()
        with mock.patch.dict(os.environ, {self.ENV: str(folder)}), mock.patch.object(series_backfill, 'LOG_LIMIT', 400, create=True):
            for number in range(20):
                series_backfill._log('line %02d ' % number + 'x' * 60)
        current, previous = self.lines(folder), self.lines(folder, 'books-backend-1.log')
        self.assertTrue(current and previous, (current, previous))
        for name in ('books-backend.log', 'books-backend-1.log'):
            self.assertLessEqual((folder / name).stat().st_size, 400, name)
        self.assertIn('line 19 ', current[-1], 'the newest line is kept')
        numbers = [int(line.split('line ')[1][:2]) for line in previous + current]
        self.assertEqual(numbers, list(range(numbers[0], 20)), 'in order; the oldest lines go first')
        self.assertEqual(sorted(item.name for item in folder.iterdir()), ['books-backend-1.log', 'books-backend.log'], 'two files, never more')

    def test_its_names_are_ones_the_logs_folder_admits_as_the_apps_own(self):
        import storage_lifecycle
        self.assertEqual((series_backfill.LOG_FILE, series_backfill.LOG_PREVIOUS), ('books-backend.log', 'books-backend-1.log'))
        for name in (series_backfill.LOG_FILE, series_backfill.LOG_PREVIOUS):
            self.assertTrue(storage_lifecycle._runtime_name('created-logs-v1', name), 'uninstall and relocation know it as the app\'s: ' + name)

    def test_guard_no_folder_is_created_and_a_failed_write_never_stops_the_caller(self):
        missing = Path(self.temp.name) / 'Logs'
        with mock.patch.dict(os.environ, {self.ENV: str(missing)}):
            series_backfill._log('a line')
        self.assertFalse(missing.exists(), 'a folder that is not there is not made: stderr only')
        folder = self.logs()
        (folder / 'books-backend.log').mkdir()  # the file cannot be written
        with mock.patch.dict(os.environ, {self.ENV: str(folder)}):
            series_backfill._log('a line')  # no error reaches the clean-up


def _series_lane():
    from test_rule_filing_031 import SeriesWriteThenMoveTests as lane
    return lane


class SeriesFollowUpAfterTheCleanUpTests(unittest.TestCase):
    """Futaba's 0.31.3 QA, m1: a series book the clean-up finishes moves into its series folder, and its "Could not be renamed
    or moved" line clears. The lane keeps the ledger (follow_up / follow_up_wait): a real audiobook (ffmpeg), its series found,
    the write approved by the real rules' pass and held by 0.31.2 on the (simulated) NAS, the rules' entry closed as failed
    as live; then 0.31.3's retry, the follow-up the write asks for, the app's real verified move (book_move) and the rules'
    next pass. Uses test_rule_filing_031's SeriesWriteThenMoveTests set-up (its own tests are not run here)."""

    def setUp(self):
        _series_lane().setUp(self)

    def resolve(self, job_id, kind):
        return _series_lane().resolve(self, job_id, kind)

    def queue_move(self, job_id, target, origin='user'):
        return _series_lane().queue_move(self, job_id, target, origin)

    def run_queue(self):
        return _series_lane().run_queue(self)

    def moves(self):
        return _series_lane().moves(self)

    def could_not(self):
        return [(entry['key'], entry.get('cause')) for entry in self.filing.could_not()['entries']]

    def test_m1_the_finished_book_moves_to_its_series_folder_and_its_line_clears(self):
        lib, backfill = self.lib, self.backfill
        backfill.run_pass()  # the look-up finds the series; the book is held for the rules
        self.filing.tick()  # the rules approve its write
        with nas_library(lib.root), as_0312():
            backfill.run_pass()  # 0.31.2: written and renamed in its own folder, then the old file's removal refused
        like_0312(lib.db, 'series_backfill', lib.job_id)
        entry = backfill.entry(lib.job_id)
        self.assertEqual((entry['state'], entry['reason']), ('held', LIVE_PREFIX + str(lib.path) + LIVE_SUFFIX), 'control: the live hold')
        placed = Path(entry['record']['new_path'])
        self.assertEqual((placed.parent, placed.exists(), lib.path.exists()), (lib.path.parent, True, True))
        self.filing.tick()  # as live: the rules' entry is closed as failed
        with connect(lib.db) as db:
            self.assertEqual([tuple(row) for row in db.execute('SELECT state,step FROM rule_filings')], [('failed', 'write')])
        before = self.could_not()
        # 0.31.3 starts: a new engine on the same catalog sends the hold back and finishes it.
        retry = series_backfill.SeriesBackfill(self.merge, research=self.research, stage=lib.base / 'proof-stage')
        self.merge.series_backfill = retry
        with nas_library(lib.root):
            retry.run_pass()
        entry = retry.entry(lib.job_id)
        self.assertEqual((entry['state'], entry['record']['removal_retry'], lib.path.exists(), placed.exists()), ('done', series_backfill.REMOVAL_RETRY, False, True))
        self.assertEqual(entry['record']['follow_up']['state'], 'move_queued', 'the follow-up ran and queued the move')
        self.assertNotIn('follow_up_wait', entry['record'])
        self.assertEqual(self.moves(), [('queued', 'rules', str(self.final))], "the app's own move to the series folder")
        self.filing.tick()
        queued = self.could_not()
        self.run_queue()
        self.filing.tick()
        self.assertEqual((self.final.exists(), placed.exists()), (True, False), 'moved into its series folder')
        self.assertEqual(self.resolve(lib.job_id, 'base')['final_path'], str(self.final))
        self.assertEqual(self.could_not(), [], 'its line clears at the rules\' next pass after the move')
        self.assertEqual(self.moves(), [('complete', 'rules', str(self.final))], 'moved once')
        with nas_library(lib.root):
            retry.run_pass()
        self.assertEqual((self.filing.tick()['left'], len(self.moves())), (0, 1), 'and nothing more')
        self.assertEqual((before, queued), ([('not_app_name', None)], []), 'the lines the rules showed: before the clean-up, and while the move waits')

    def test_m1_a_follow_up_refused_for_now_is_asked_again_by_a_later_pass(self):
        """Futaba's control lane: the writes finished while her seeder's engine refused every move (RuntimeError, kit
        seed2.py), so each follow-up was noted 'later' (follow_up_wait), not recorded for good; the series pass's next pass
        asks again, and with the queue answering the book moves and its line clears."""
        lib, backfill = self.lib, self.backfill
        backfill.run_pass()
        self.filing.tick()
        real = self.merge._sorting_move
        self.merge._sorting_move = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('QA seeder: no move is run while seeding'))
        backfill.run_pass()  # written; the move refused for now
        entry = backfill.entry(lib.job_id)
        self.assertEqual((entry['state'], entry['record'].get('follow_up'), entry['record']['follow_up_wait']['state']), ('done', None, 'later'))
        self.assertEqual(self.moves(), [])
        self.merge._sorting_move = real
        backfill.run_pass()  # the next pass (every ten minutes, after the start delay at launch)
        entry = backfill.entry(lib.job_id)
        self.assertEqual((entry['record']['follow_up']['state'], 'follow_up_wait' in entry['record']), ('move_queued', False))
        self.run_queue()
        self.filing.tick()
        self.assertEqual((self.final.exists(), self.could_not()), (True, []))


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
