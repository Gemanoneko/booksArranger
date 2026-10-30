"""Rulings 69, 71h and 71k (Sergei 2026-10-29): moving a finished audiobook to the folder Sergei chose.

Real files and a real catalog in a private temporary folder; the volume seam picks the strategy (one disk here), the fault
hook stands for a crash at each journal boundary. Nothing converts: no job row is written and no encoder runs."""
import copy
import ctypes
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
import uuid
from ctypes import wintypes
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import book_delete
import book_move
import native_io
import publication_locations as p
from native_io import DirectoryBoundary, VerifiedFile
from publication_binding import PublicationBindings
from scanner import connect

JOBS = ('CREATE TABLE IF NOT EXISTS audio_jobs (job_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_hash TEXT NOT NULL, state TEXT NOT NULL,'
        ' stage TEXT NOT NULL, attempt_id TEXT, journal TEXT NOT NULL, output TEXT, reason TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL)')


class Crash(RuntimeError):
    pass


class MoveFixture(unittest.TestCase):
    payload = b'ID3 fixture audiobook bytes ' * 4096

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='bm'))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.library = self.base / 'lib'
        self.sorted = self.base / 'srt'
        self.other = self.base / 'out'
        for folder in (self.library, self.sorted / 'Author' / 'Series', self.other):
            folder.mkdir(parents=True)
        self.old = self.sorted / 'Author' / 'Series' / 'Book - Author.m4b'
        self.old.write_bytes(self.payload)
        (self.base / 'data').mkdir()
        self.db = str(self.base / 'data' / 'c.sqlite3')
        with DirectoryBoundary(self.sorted, self.old.parent) as boundary:
            parents = [list(i) for i in boundary.identities]
        self.job_id = str(uuid.uuid4())
        self.candidate = str(uuid.uuid4())
        self.output = {'job_id': self.job_id, 'root': str(self.sorted), 'final_path': str(self.old), 'sha256': hashlib.sha256(self.payload).hexdigest(),
                       'size': len(self.payload), 'parent_identity': parents, 'validation': {'passed': True}}
        self.manifest = {'job_id': self.job_id, 'candidate_id': self.candidate, 'candidate_revision': 1, 'root': str(self.library),
                         'sources': [{'path': str(self.library / 'a.mp3')}], 'metadata_facts': {'source_fingerprint': 'fp'}}
        with connect(self.db) as db:
            db.execute(JOBS)
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (self.job_id, p._packed(self.manifest), p._digest(self.manifest), 'completed', 'completed', None,
                        p._packed({'publication_intent': self.output}), p._packed(self.output), '', 'now', 'now'))
        self.bindings = PublicationBindings(self.db)
        self.volume = book_move.default_same_volume
        self.crash_at = None

    def fault(self, stage):
        if stage == self.crash_at:
            raise Crash(stage)

    def resolve(self, job_id, kind):
        record = json.loads(self.read('SELECT output FROM audio_jobs WHERE job_id=?', (job_id,))[0])
        return self.bindings.current(record, kind)[0]

    def read(self, sql, args=()):
        with connect(self.db) as db:
            return db.execute(sql, args).fetchone()

    def mover(self):
        return book_move.Mover(lambda: connect(self.db), self.resolve, sources=lambda: (str(self.library),), output_root=str(self.sorted),
                               same_volume=lambda a, b: self.volume(a, b), fault=self.fault, remove_folder=book_delete._remove_folder,
                               protected_roots=lambda: (str(self.library), str(self.sorted)))

    def plan(self, folder, root=None):
        start = book_move.location(self.resolve(self.job_id, 'base'))
        with connect(self.db) as db:
            return book_move.plan(db, job_id=self.job_id, kind='base', candidate_id=self.candidate, start=start, folder=str(folder),
                                  root=str(root or (self.sorted if str(folder).startswith(str(self.sorted)) else folder)))

    def effective(self):
        return self.resolve(self.job_id, 'base')

    def jobs(self):
        with connect(self.db) as db:
            return [tuple(r) for r in db.execute('SELECT job_id,state,stage,output FROM audio_jobs')]


class StrategyTests(MoveFixture):
    def test_same_volume_rename_moves_the_exact_file_and_removes_the_empty_old_folders(self):
        target = self.sorted / 'Horror'
        target.mkdir()
        with VerifiedFile(self.old) as held:
            before = held.facts()['identity']
        jobs = self.jobs()
        move = self.mover().run(self.plan(target)['move_id'])
        self.assertEqual((move['state'], move['strategy']), ('complete', 'rename'))
        new = target / self.old.name
        self.assertTrue(new.exists())
        self.assertFalse(self.old.exists())
        with VerifiedFile(new) as held:
            self.assertEqual(held.facts()['identity'], before)  # the same native file, renamed, never copied
        self.assertEqual(self.effective()['final_path'], str(new))
        # Ruling 71k: the folders it left are removed when empty, up to (never) the output folder.
        self.assertFalse((self.sorted / 'Author').exists())
        self.assertTrue(self.sorted.exists())
        self.assertEqual(self.jobs(), jobs)  # never converted: the job row is untouched

    def test_another_volume_copies_verifies_publishes_then_removes_the_old_file(self):
        self.volume = lambda a, b: False
        (self.sorted / 'Author' / 'cover.jpg').write_bytes(b'cover')  # the author folder keeps another file
        move = self.mover().run(self.plan(self.other)['move_id'])
        self.assertEqual((move['state'], move['strategy']), ('complete', 'copy'))
        new = self.other / self.old.name
        self.assertEqual(new.read_bytes(), self.payload)
        self.assertFalse(self.old.exists())
        self.assertFalse((self.sorted / 'Author' / 'Series').exists())
        self.assertTrue((self.sorted / 'Author').exists())  # not empty: kept
        self.assertEqual([p.name for p in self.other.iterdir()], [self.old.name])  # no temporary left
        effective = self.effective()
        self.assertEqual((effective['root'], effective['final_path']), (str(self.other), str(new)))
        self.assertEqual(effective['sha256'], self.output['sha256'])

    def test_a_move_up_into_an_ancestor_folder_is_copied_not_renamed(self):
        move = self.mover().run(self.plan(self.sorted / 'Author')['move_id'])
        self.assertEqual((move['state'], move['strategy']), ('complete', 'copy'))
        self.assertTrue((self.sorted / 'Author' / self.old.name).exists())
        self.assertFalse((self.sorted / 'Author' / 'Series').exists())

    def test_never_reconverts(self):
        import audio_pipeline
        with patch.object(audio_pipeline, 'create_private', side_effect=AssertionError('encoder called')):
            move = self.mover().run(self.plan(self.other)['move_id'])
        self.assertEqual(move['state'], 'complete')
        self.assertEqual(len(self.jobs()), 1)


class RefusalTests(MoveFixture):
    def test_same_name_is_never_overwritten(self):
        (self.other / self.old.name.upper()).write_bytes(b'someone else')
        move = self.mover().run(self.plan(self.other)['move_id'])
        self.assertEqual((move['state'], move['cause']), ('failed', 'target_exists'))
        self.assertEqual(self.old.read_bytes(), self.payload)
        self.assertEqual((self.other / self.old.name.upper()).read_bytes(), b'someone else')
        self.assertEqual(self.effective()['final_path'], str(self.old))

    def test_current_folder_is_a_no_op(self):
        self.assertIsNone(self.plan(self.old.parent))

    def test_changed_bytes_move_nothing(self):
        move = self.plan(self.other)
        self.old.write_bytes(self.payload[:-1] + b'!')
        done = self.mover().run(move['move_id'])
        self.assertEqual((done['state'], done['cause']), ('failed', 'changed'))
        self.assertTrue(self.old.exists())
        self.assertEqual(list(self.other.iterdir()), [])

    def test_open_elsewhere_is_in_use(self):
        move = self.plan(self.other)
        with VerifiedFile(self.old):  # another program holds it without delete sharing
            done = self.mover().run(move['move_id'])
        self.assertEqual((done['state'], done['cause']), ('failed', 'in_use'))
        self.assertTrue(self.old.exists())

    def test_folder_gone_is_unavailable_and_inside_a_source_is_unsafe(self):
        gone = self.base / 'gone'
        gone.mkdir()
        move = self.plan(gone)
        gone.rmdir()
        self.assertEqual(self.mover().run(move['move_id'])['cause'], 'unavailable')
        inside = self.library / 'inside'
        inside.mkdir()
        done = self.mover().run(self.plan(inside)['move_id'])
        self.assertEqual(done['cause'], 'unsafe')
        # Judy 2026-10-30: the row shows the engine's sentence, which names the source folder.
        self.assertEqual(book_move.view(done)['message'], 'That folder is inside %s, one of your source folders. Choose another folder.' % self.library)
        self.assertTrue(self.old.exists())

    def test_queued_move_cancels_and_a_new_choice_supersedes_it(self):
        first = self.plan(self.other)
        second = self.plan(self.sorted)
        self.assertEqual(self.read('SELECT state FROM book_moves WHERE move_id=?', (first['move_id'],))[0], 'cancelled')
        with connect(self.db) as db:
            self.assertTrue(book_move.cancel(db, second['move_id']))
            self.assertFalse(book_move.cancel(db, second['move_id']))
        self.assertEqual(self.mover().run(second['move_id'])['state'], 'cancelled')
        self.assertTrue(self.old.exists())

    def test_chapter_updates_are_not_moved(self):
        with connect(self.db) as db:
            with self.assertRaises(book_move.Refused):
                book_move.plan(db, job_id=self.job_id, kind='Chaptersv2', candidate_id=self.candidate, start=self.output, folder=str(self.other), root=str(self.other))


class ChainTests(MoveFixture):
    def test_second_and_third_moves_chain_and_a_broken_link_fails_closed(self):
        first, second = self.sorted / 'One', self.other / 'Two'
        first.mkdir(); second.mkdir()
        self.mover().run(self.plan(first)['move_id'])
        self.volume = lambda a, b: False
        self.mover().run(self.plan(second)['move_id'])
        self.volume = book_move.default_same_volume
        third = self.mover().run(self.plan(self.sorted)['move_id'])
        self.assertEqual(third['state'], 'complete')
        self.assertEqual(self.effective()['final_path'], str(self.sorted / self.old.name))
        self.assertEqual(self.read('SELECT max(generation) FROM book_moves')[0], 3)
        self.assertFalse(second.exists())  # 71k: emptied, outside the output folder: removed itself
        with connect(self.db) as db:
            db.execute('DROP TRIGGER IF EXISTS book_move_events_no_update')
            db.execute("UPDATE book_moves SET from_json=? WHERE generation=2", (json.dumps(dict(json.loads(db.execute('SELECT from_json FROM book_moves WHERE generation=2').fetchone()[0]), sha256='0' * 64)),))
        with self.assertRaisesRegex(ValueError, 'does not link'):
            self.effective()

    def test_guard_follows_the_generation(self):
        with self.bindings.protect(self.output) as (_, envelope):
            pass
        self.mover().run(self.plan(self.other)['move_id'])
        with connect(self.db) as db:
            self.assertFalse(self.bindings.guard(db, self.output, envelope))
        with self.bindings.protect(self.output) as (effective, envelope):
            with connect(self.db) as db:
                self.assertTrue(self.bindings.guard(db, self.output, envelope))
            self.assertEqual(envelope['effective_location']['final_path'], effective['final_path'])
            # Chapter repair binds its parent with this generation (protect_parent).
            proof = {'schema': 'books-repair-parent-location-v1', 'immutable_receipt_sha256': p._digest(self.output),
                     'generation': envelope['generation'], 'effective_location': envelope['effective_location']}
        with self.bindings.protect_parent(self.job_id, proof) as (parent, _):
            self.assertEqual(parent['final_path'], str(self.other / self.old.name))

    def test_a_relocated_book_can_be_moved(self):
        import test_publication_locations as ledger
        sorted2 = self.base / 'rel'
        sorted2.mkdir()
        relocated = sorted2 / self.old.name
        relocated.write_bytes(self.payload)
        helper = ledger.PublicationLocationsTests()
        helper.original = json.loads(p._packed(self.output))
        with DirectoryBoundary(sorted2, relocated.parent) as boundary, VerifiedFile(relocated) as file:
            helper.target_identity = file.facts()['identity']
            helper.target_parents = json.loads(p._packed(boundary.identities))
        with connect(self.db) as db:
            p.initialize(db)
            helper.db = db
            helper.target = str(sorted2)
            helper.destination = str(relocated)
            job = dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (self.job_id,)).fetchone())
            row = p.plan(db, job, 'base', self.output, str(sorted2), str(relocated), {'routing_policy_version': 'fixture', 'source_fingerprint': 'fp'})
            for stage in ('copy_intent', 'copied', 'temporary_verified', 'final_publish_intent', 'final_published', 'location_committed'):
                row = helper.next(row, stage)
        self.old.unlink()
        self.assertEqual(self.effective()['final_path'], str(relocated))
        move = self.mover().run(self.plan(self.other, root=self.other)['move_id'])
        self.assertEqual(move['state'], 'complete')
        self.assertEqual(self.effective()['final_path'], str(self.other / self.old.name))
        self.assertFalse(sorted2.exists())  # the relocated folder it left is empty: removed (71k)
        # The relocation row itself is untouched: one row per publication, as before.
        self.assertEqual(self.read('SELECT stage FROM output_relocations')[0], 'location_committed')


class RecoveryTests(MoveFixture):
    def crash(self, stage, volume=None):
        if volume is not None:
            self.volume = volume
        self.crash_at = stage
        move = self.plan(self.other)
        with self.assertRaises(Crash):
            self.mover().run(move['move_id'])
        self.crash_at = None
        return move['move_id']

    def state(self, move_id):
        return tuple(self.read('SELECT state,cause FROM book_moves WHERE move_id=?', (move_id,)))

    def test_copy_interrupted_before_publication_moves_nothing(self):
        for stage in ('copy_intent', 'copied', 'publish_intent'):
            with self.subTest(stage=stage):
                move_id = self.crash(stage, volume=lambda a, b: False)
                self.mover().recover()
                self.assertEqual(self.state(move_id)[0], 'failed')
                self.assertEqual(self.old.read_bytes(), self.payload)
                self.assertEqual(list(self.other.iterdir()), [])  # the owned temporary is gone
                self.assertEqual(self.effective()['final_path'], str(self.old))

    def test_copy_interrupted_after_commit_finishes_by_removing_the_proven_old_file(self):
        for stage in ('committed', 'old_removal_intent'):
            with self.subTest(stage=stage):
                if not self.old.exists():
                    self.setUp()
                move_id = self.crash(stage, volume=lambda a, b: False)
                self.assertEqual(self.effective()['final_path'], str(self.other / self.old.name))  # committed: the new place
                self.assertTrue(self.old.exists())
                self.mover().recover()
                self.assertEqual(self.state(move_id)[0], 'complete')
                self.assertFalse(self.old.exists())

    def test_old_copy_that_changed_is_kept_as_partial(self):
        move_id = self.crash('committed', volume=lambda a, b: False)
        self.old.write_bytes(b'changed meanwhile')
        self.mover().recover()
        self.assertEqual(self.state(move_id), ('partial', 'partial'))
        self.assertTrue(self.old.exists())
        self.assertEqual(book_move.view(self.load(move_id))['cause'], 'partial')

    def load(self, move_id):
        with connect(self.db) as db:
            return book_move.load(db, move_id)

    def test_rename_interrupted_before_and_after_the_rename(self):
        move_id = self.crash('rename_intent')
        self.mover().recover()
        self.assertEqual(self.state(move_id)[0], 'failed')
        self.assertTrue(self.old.exists())
        move_id = self.crash('renamed')
        self.assertTrue((self.other / self.old.name).exists())
        self.assertEqual(self.effective()['final_path'], str(self.old))  # not committed yet: the book reads the old place
        self.mover().recover()
        self.assertEqual(self.state(move_id)[0], 'complete')
        self.assertEqual(self.effective()['final_path'], str(self.other / self.old.name))

    def test_a_queued_move_is_cancelled_at_start(self):
        move = self.plan(self.other)
        self.mover().recover()
        self.assertEqual(self.state(move['move_id'])[0], 'cancelled')
        self.assertIsNone(book_move.view(self.load(move['move_id'])))


class ViewTests(MoveFixture):
    def test_row_line_states(self):
        move = self.plan(self.other)
        self.assertEqual(book_move.view(move)['state'], 'queued')
        done = self.mover().run(move['move_id'])
        line = book_move.view(done)
        self.assertEqual((line['state'], line['folder'], line['name'], line['old_folder']), ('moved', str(self.other), self.old.name, str(self.old.parent)))
        with connect(self.db) as db:
            self.assertEqual(book_move.latest(db, [self.candidate])[self.candidate]['move_id'], move['move_id'])

    def test_a_journaled_move_that_is_not_running_reads_unfinished_73k(self):
        """Ruling 73k (Judy): a journaled move whose retries ran out is 'unfinished', with the target folder, the reason the
        page words ('copy' or 'catalog') and the raw error for Technical details; while it runs it is 'moving' as before."""
        move = self.plan(self.other)
        with connect(self.db) as db:
            book_move._set(db, move['move_id'], 'publish_intent', strategy='copy')
            journaled = book_move.load(db, move['move_id'])
        self.assertEqual(book_move.view(journaled)['state'], 'moving', 'running (or unknown): as before')
        for cause in ('copy', 'catalog', 'renamed'):  # D1r3: 'renamed', a renamed file that could not be checked
            line = book_move.view(journaled, unfinished={'cause': cause, 'detail': 'Cannot protect exact file: in use'})
            self.assertEqual((line['state'], line['cause'], line['folder'], line['old_folder'], line['detail'], line['progress']),
                             ('unfinished', cause, str(self.other), str(self.old.parent), 'Cannot protect exact file: in use', None))
        for state, shown in (('queued', 'queued'), ('complete', 'moved'), ('failed', 'failed')):
            self.assertEqual(book_move.view(dict(journaled, state=state), unfinished={'cause': 'copy'})['state'], shown, state)

    def test_a_new_choice_beside_an_unfinished_move_says_to_restart_73k(self):
        move = self.plan(self.other)
        with connect(self.db) as db:
            book_move._set(db, move['move_id'], 'publish_intent', strategy='copy')
        start = book_move.location(self.resolve(self.job_id, 'base'))
        for running, cause, said in ((None, 'changed', 'This audiobook is being moved now. Choose another folder when it finishes.'),
                                     (lambda move_id: True, 'changed', 'This audiobook is being moved now. Choose another folder when it finishes.'),
                                     (lambda move_id: False, 'unfinished', book_move.UNFINISHED)):
            with connect(self.db) as db, self.assertRaises(book_move.Refused) as raised:
                book_move.plan(db, job_id=self.job_id, kind='base', candidate_id=self.candidate, start=start, folder=str(self.library),
                               root=str(self.library), running=running)
            self.assertEqual((raised.exception.cause, str(raised.exception)), (cause, said))
        self.assertEqual(book_move.UNFINISHED, 'Close and reopen Books Arranger to finish the move. Then you can choose another folder.')

    def test_events_are_append_only(self):
        move = self.plan(self.other)
        with connect(self.db) as db:
            with self.assertRaises(Exception):
                db.execute('DELETE FROM book_move_events WHERE move_id=?', (move['move_id'],))


class UnexpectedErrorTests(MoveFixture):
    """Senua 0.24.0 M1: an OS or catalog error no step typed ends the move in the session (never "moving" until a restart),
    from the journal and what is on disk, exactly as recovery at start would: the old file is kept until proven."""

    def events(self, move_id):
        with connect(self.db) as db:
            return [r[0] or '' for r in db.execute('SELECT proof_json FROM book_move_events WHERE move_id=? ORDER BY event_id', (move_id,))]

    def released(self):
        """The book is free again at once: a new choice is accepted and moves it."""
        again = self.mover().run(self.plan(self.other)['move_id'])
        self.assertEqual(again['state'], 'complete')
        self.assertEqual(self.effective()['final_path'], str(self.other / self.old.name))

    def test_network_error_on_the_temporary_fails_the_move_now_and_keeps_the_old_file(self):
        self.volume = lambda a, b: False
        real = os.open

        def lost(path, *args, **kwargs):
            if book_move.TEMP_PREFIX in str(path):
                raise ctypes.WinError(64)  # ERROR_NETNAME_DELETED: the share went away
            return real(path, *args, **kwargs)
        move = self.plan(self.other)
        with patch.object(book_move.os, 'open', lost):
            done = self.mover().run(move['move_id'])
        self.assertEqual((done['state'], book_move.view(done)['state']), ('failed', 'failed'))
        self.assertEqual(self.old.read_bytes(), self.payload)
        self.assertEqual(list(self.other.iterdir()), [])
        self.assertEqual(self.effective()['final_path'], str(self.old))
        self.assertTrue(any('unexpected error' in proof for proof in self.events(move['move_id'])), 'the error is on the move')
        self.released()

    def test_catalog_error_mid_move_fails_or_finishes_it_now_from_what_is_on_disk(self):
        real = book_move.Mover._write
        for stage, ends in (('copied', 'failed'), ('old_removal_intent', 'complete')):
            with self.subTest(stage=stage):
                if not self.old.exists():
                    self.setUp()
                self.volume = lambda a, b: False  # the copy strategy (setUp resets the seam)
                failed = []

                def flaky(mover, move_id, state, **values):
                    if state == stage and not failed:
                        failed.append(state)
                        raise sqlite3.OperationalError('disk I/O error')
                    return real(mover, move_id, state, **values)
                move = self.plan(self.other)
                with patch.object(book_move.Mover, '_write', flaky):
                    done = self.mover().run(move['move_id'])
                self.assertEqual(failed, [stage], 'positive control: the catalog write failed')
                self.assertEqual(done['state'], ends)
                if ends == 'failed':
                    # Not committed: nothing moved, the owned temporary is gone, the old file is untouched.
                    self.assertEqual(self.old.read_bytes(), self.payload)
                    self.assertEqual(list(self.other.iterdir()), [])
                    self.released()
                else:
                    # Committed: the new file is the book; the old one is removed only after it was proven the same bytes.
                    self.assertEqual((self.other / self.old.name).read_bytes(), self.payload)
                    self.assertFalse(self.old.exists())
                    self.assertEqual(self.effective()['final_path'], str(self.other / self.old.name))

    def test_a_failure_after_the_copy_is_placed_finishes_the_move_and_leaves_no_stray_copy(self):
        """Senua 0.24.0 D1: the copy is published into the folder, then the step after it fails (the re-open of the placed
        file in use for a moment, the share dropping, any other error). The move is settled from publish_intent as recovery
        settles it: the placed file proven, the catalog moved to it, the old file removed. Before: failed 'unavailable'
        ("Nothing was moved") with the new file left untracked in the folder."""
        real = book_move.VerifiedFile
        failures = (lambda: native_io.FileInUse('Cannot protect exact file: in use'),
                    lambda: native_io.BoundaryError('Cannot protect exact file: the network name is no longer available'),
                    lambda: KeyError('identity'))
        for index, make in enumerate(failures):
            with self.subTest(error=type(make()).__name__):
                if index:
                    self.setUp()  # a fresh library for each failure
                self.volume = lambda a, b: False  # the copy strategy (setUp resets the seam)
                target = self.other / self.old.name
                raised = []

                def once(path, *args, **kwargs):
                    if not raised and Path(str(path)) == target and target.exists():
                        raised.append(str(path))
                        raise make()
                    return real(path, *args, **kwargs)
                move = self.plan(self.other)
                with patch.object(book_move, 'VerifiedFile', once):
                    done = self.mover().run(move['move_id'])
                self.assertEqual(raised, [str(target)], 'positive control: the re-open of the placed copy failed')
                self.assertEqual((done['state'], done['strategy'], book_move.view(done)['state']), ('complete', 'copy', 'moved'))
                self.assertEqual(target.read_bytes(), self.payload)
                self.assertFalse(self.old.exists())
                self.assertEqual([p.name for p in self.other.iterdir()], [self.old.name])  # one file, no temporary
                self.assertEqual(self.effective()['final_path'], str(target))
                self.assertTrue(any('unexpected error' in proof for proof in self.events(move['move_id'])), 'the error is on the move')

    def test_a_placed_copy_still_unopenable_is_retried_after_a_pause_never_reported_as_nothing_moved(self):
        """Senua 0.24.0 D1r: the re-open of the placed copy fails two or three times in a row (in use for longer than a
        moment, the share dropped). The first settle attempt runs at once and meets the same error, so the move must be
        retried after the 0.5 s and 2 s pauses (Mover.SETTLE_PAUSES; recorded here, not slept) and complete. Four in a row
        outlast every pause: the move stays journaled at publish_intent with both files kept, and recovery at the next start
        finishes it. Before: failed, "Nothing was moved", the verified copy left untracked and the catalog on the old file."""
        real = book_move.VerifiedFile
        failures = (lambda: native_io.FileInUse('Cannot protect exact file: in use'),
                    lambda: native_io.BoundaryError('Cannot protect exact file: the network name is no longer available'))
        fresh = False
        for make in failures:
            for times in (2, 3, 4):
                with self.subTest(error=type(make()).__name__, failures=times):
                    if fresh:
                        self.setUp()  # a fresh library for each case
                    fresh = True
                    self.volume = lambda a, b: False  # the copy strategy (setUp resets the seam)
                    target = self.other / self.old.name
                    raised, slept = [], []

                    def busy(path, *args, **kwargs):
                        if len(raised) < times and Path(str(path)) == target and target.exists():
                            raised.append(str(path))
                            raise make()
                        return real(path, *args, **kwargs)
                    move = self.plan(self.other)
                    with patch.object(book_move, 'VerifiedFile', busy), patch.object(book_move, 'time', SimpleNamespace(sleep=slept.append)):
                        if times < 4:
                            done = self.mover().run(move['move_id'])
                        else:
                            with self.assertRaises(book_move.Unfinished) as ran_out:  # ruling 73k: typed, with its reason
                                self.mover().run(move['move_id'])
                            self.assertEqual((ran_out.exception.cause, ran_out.exception.move['move_id']), ('copy', move['move_id']))
                            self.assertIn('Cannot protect exact file', ran_out.exception.detail)
                            self.assertIsInstance(ran_out.exception.error, native_io.BoundaryError)
                            still = self.mover()

                            def unopenable(path, *args, **kwargs):
                                if Path(str(path)) == target:
                                    raise make()
                                return real(path, *args, **kwargs)
                            with patch.object(book_move, 'VerifiedFile', unopenable):
                                self.assertEqual(still.recover(), [])
                            self.assertEqual(still.unfinished[move['move_id']]['cause'], 'copy', 'recovery that cannot open it says why')
                    self.assertEqual(raised, [str(target)] * times, 'positive control: each re-open of the placed copy failed')
                    # The pauses the injected failures need, in order (a real transient on a fresh file may add one more).
                    self.assertEqual(slept[:times - 1], [0.5, 2][:times - 1], 'each retry came after its pause, never all at once')
                    self.assertTrue(any('unexpected error' in proof for proof in self.events(move['move_id'])), 'the error is on the move')
                    if times < 4:
                        self.assertEqual((done['state'], done['strategy'], book_move.view(done)['state']), ('complete', 'copy', 'moved'))
                    else:
                        # Every pause outlasted: never "nothing moved". Both files kept, the catalog on the old file until
                        # the placed copy is proven, and the journal left for recovery at the next start.
                        with connect(self.db) as db:
                            left = book_move.load(db, move['move_id'])
                        self.assertEqual((left['state'], book_move.view(left)['state']), ('publish_intent', 'moving'))
                        self.assertEqual(target.read_bytes(), self.payload)
                        self.assertEqual(self.old.read_bytes(), self.payload)
                        self.assertEqual(self.effective()['final_path'], str(self.old))
                        done = {m['move_id']: m for m in self.mover().recover()}[move['move_id']]
                        self.assertEqual((done['state'], done['strategy']), ('complete', 'copy'))
                    self.assertEqual(target.read_bytes(), self.payload)
                    self.assertFalse(self.old.exists())
                    self.assertEqual([p.name for p in self.other.iterdir()], [self.old.name])  # one file, no temporary
                    self.assertEqual(self.effective()['final_path'], str(target))

    def share_away(self, state):
        """The target folder's share dropped once state['away'] is set: lstat and stat of anything in it answer WinError 64
        (ERROR_NETNAME_DELETED), os.path.lexists and exists read it as absent (as they do for any error; they are native fast
        paths on 3.14, so they are replaced here, not reached through lstat), and its re-open fails the same way. Returns
        the patches, the VerifiedFile double last."""
        real_lstat, real_stat, real_file = os.lstat, os.stat, book_move.VerifiedFile
        real_lexists, real_exists = os.path.lexists, os.path.exists
        inside = str(self.other).lower()

        def gone(path):
            return state['away'] and str(path).lower().startswith(inside)

        def lstat(path, *args, **kwargs):
            if gone(path):
                raise ctypes.WinError(64)
            return real_lstat(path, *args, **kwargs)

        def stat(path, *args, **kwargs):
            if gone(path):
                raise ctypes.WinError(64)
            return real_stat(path, *args, **kwargs)

        def opened(path, *args, **kwargs):
            if gone(path):
                raise native_io.BoundaryError('Cannot protect exact file: [WinError 64] The specified network name is no longer available.')
            return real_file(path, *args, **kwargs)
        return (patch.object(book_move.os, 'lstat', lstat), patch.object(book_move.os, 'stat', stat),
                patch.object(book_move.os.path, 'lexists', lambda path: False if gone(path) else real_lexists(path)),
                patch.object(book_move.os.path, 'exists', lambda path: False if gone(path) else real_exists(path)),
                patch.object(book_move, 'VerifiedFile', opened))

    def test_a_placed_copy_behind_a_dropped_share_is_never_nothing_moved_D1r2(self):
        """Senua 0.24.0 D1r2: the share holding the placed copy drops, so the copy is invisible (os.path.lexists is False for
        any error), not merely unopenable. Only a definite "not found" with its folder answering is absent; anything else is
        retried and ends Unfinished('copy') with both files kept, and recovery leaves it journaled while the share is away.
        Before: failed "nothing moved", no pause taken, the copy left in the folder unrecorded, in the run and in recovery."""
        for case in ('drops during the move', 'still away at the next start'):
            with self.subTest(case=case):
                if case != 'drops during the move':
                    self.setUp()
                self.volume = lambda a, b: False  # the copy strategy
                target = self.other / self.old.name
                state, slept = {'away': False}, []
                away = self.share_away(state)
                share_file = away[-1].new  # the share's own VerifiedFile double (real while the share is there)

                def placed_then_away(path, *args, **kwargs):  # the placed copy's re-open fails; here the share drops too
                    if not state['away'] and Path(str(path)) == target and target.exists():
                        if case == 'drops during the move':
                            state['away'] = True
                        raise native_io.FileInUse('Cannot protect exact file: in use')
                    return share_file(path, *args, **kwargs)
                move = self.plan(self.other)
                with patch.object(book_move, 'time', SimpleNamespace(sleep=slept.append)), away[0], away[1], away[2], away[3], away[4]:
                    with patch.object(book_move, 'VerifiedFile', placed_then_away), self.assertRaises(book_move.Unfinished) as ran_out:
                        self.mover().run(move['move_id'])
                    self.assertEqual((ran_out.exception.cause, slept), ('copy', [0.5, 2]), 'retried after each pause, then unfinished')
                    state['away'] = True
                    self.assertFalse(os.path.lexists(target), 'positive control: the placed copy is invisible')
                    still = self.mover()
                    self.assertEqual(still.recover(), [], 'recovery while the share is away finishes nothing')
                    self.assertEqual(still.unfinished[move['move_id']]['cause'], 'copy')
                state['away'] = False
                with connect(self.db) as db:
                    self.assertEqual(book_move.load(db, move['move_id'])['state'], 'publish_intent', 'journaled, never failed')
                self.assertEqual((target.read_bytes(), self.old.read_bytes()), (self.payload, self.payload), 'both files kept')
                self.assertEqual(self.mover().recover()[0]['state'], 'complete', 'the share is back: recovery finishes it')
                self.assertEqual(self.effective()['final_path'], str(target))
                self.assertFalse(self.old.exists())

    def test_a_renamed_file_that_cannot_be_checked_is_unfinished_never_partial_D1r3(self):
        """Senua 0.24.0 D1r3: a same-volume rename the OS accepted, whose check of the renamed file is refused (in use). The
        old file is gone, so the move is never 'partial' (the row would say to delete an old file that is not there): the
        check is retried after the pauses; while it still fails the move ends Unfinished('renamed'), journaled for
        recovery; a renamed file that opens with other bytes fails 'changed'. Before: failed 'partial' at once."""
        real_rename, real_file, real_prove = book_move.rename_no_replace, book_move.VerifiedFile, book_move.Mover._prove
        for case in (2, 'always', 'other bytes'):
            with self.subTest(case=case):
                if case != 2:
                    self.setUp()
                target = self.other / self.old.name
                refused, slept = [], []

                def accepted_unproven(*args, **kwargs):  # the OS renamed it; its re-open by name was refused
                    real_rename(*args, **kwargs)
                    raise native_io.RenamePostconditionError('Renamed audiobook could not be re-opened: in use')

                def in_use(path, *args, **kwargs):
                    if Path(str(path)) == target and (case == 'always' or len(refused) < 2):
                        refused.append(str(path))
                        raise native_io.FileInUse('Cannot protect exact file: in use')
                    return real_file(path, *args, **kwargs)

                def other_bytes(mover, move, path, placed=None):  # it opens, but is not the receipt's bytes
                    return None if Path(str(path)) == target else real_prove(mover, move, path, placed=placed)
                move = self.plan(self.other)
                checks = patch.object(book_move.Mover, '_prove', other_bytes) if case == 'other bytes' else patch.object(book_move, 'VerifiedFile', in_use)
                with patch.object(book_move, 'rename_no_replace', accepted_unproven), checks, patch.object(book_move, 'time', SimpleNamespace(sleep=slept.append)):
                    if case == 'always':
                        with self.assertRaises(book_move.Unfinished) as ran_out:
                            self.mover().run(move['move_id'])
                        self.assertEqual((ran_out.exception.cause, slept), ('renamed', [0.5, 2]))
                        still = self.mover()
                        self.assertEqual(still.recover(), [], 'recovery while it is in use finishes nothing')
                        self.assertEqual(still.unfinished[move['move_id']]['cause'], 'renamed')
                    else:
                        done = self.mover().run(move['move_id'])
                self.assertFalse(self.old.exists(), 'positive control: the OS renamed it')
                self.assertEqual(target.read_bytes(), self.payload)
                with connect(self.db) as db:
                    line = book_move.load(db, move['move_id'])
                self.assertNotEqual((line['state'], line['cause']), ('failed', 'partial'), 'never partial: there is no old file')
                if case == 2:
                    self.assertEqual((line['state'], line['strategy'], slept), ('complete', 'rename', [0.5]), 'the check retried after a pause')
                    self.assertEqual(self.effective()['final_path'], str(target))
                elif case == 'always':
                    self.assertEqual(line['state'], 'rename_intent', 'journaled for recovery')
                    self.assertEqual(self.effective()['final_path'], str(self.old), 'the catalog moves only once the file is proven')
                    self.assertEqual(self.mover().recover()[0]['state'], 'complete', 'no longer in use: recovery finishes it')
                    self.assertEqual(self.effective()['final_path'], str(target))
                else:
                    self.assertEqual((done['state'], done['cause'], book_move.view(done)['cause']), ('failed', 'changed', 'changed'))

    def test_a_catalog_that_stays_unwritable_ends_unfinished_catalog_73k(self):
        """Ruling 73k: the other way the retries run out. The copy is placed and opens, but the catalog refuses its commit on
        every attempt: Unfinished with the reason 'catalog' (the page says the app couldn't save its progress), the journal
        left at publish_intent with both files kept, and recovery at the next start finishes it."""
        self.volume = lambda a, b: False  # the copy strategy
        real = book_move.Mover._write
        refused, slept = [], []

        def unwritable(mover, move_id, state, **values):
            if state == 'committed':
                refused.append(state)
                raise sqlite3.OperationalError('disk I/O error')
            return real(mover, move_id, state, **values)
        move = self.plan(self.other)
        with patch.object(book_move.Mover, '_write', unwritable), patch.object(book_move, 'time', SimpleNamespace(sleep=slept.append)):
            with self.assertRaises(book_move.Unfinished) as ran_out:
                self.mover().run(move['move_id'])
        self.assertEqual(len(refused), 4, 'positive control: the commit and each of the three settle attempts were refused')
        self.assertEqual((ran_out.exception.cause, ran_out.exception.detail, slept), ('catalog', 'disk I/O error', [0.5, 2]))
        with connect(self.db) as db:
            self.assertEqual(book_move.load(db, move['move_id'])['state'], 'publish_intent')
        self.assertEqual(((self.other / self.old.name).read_bytes(), self.old.read_bytes()), (self.payload, self.payload))
        self.assertEqual(self.mover().recover()[0]['state'], 'complete')


class RenameAcrossSharesTests(MoveFixture):
    """Senua 0.24.0 M4: two shares of one NAS volume report one volume serial, so the strategy picks a rename that Windows
    refuses as another device (ERROR_NOT_SAME_DEVICE). Nothing was renamed: the move goes on as a verified copy."""

    def refuse_rename(self, code, calls):
        kernel = native_io.kernel
        real = kernel.SetFileInformationByHandle
        real.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        real.restype = wintypes.BOOL

        def refused(handle, kind, info, size):
            if kind == 3:  # FileRenameInfo: refused as the SMB server refuses a rename to another share
                calls.append(code)
                ctypes.set_last_error(code)
                return False
            return real(handle, kind, info, size)  # the old file's delete disposition (kind 4) is the real one
        return patch.object(kernel, 'SetFileInformationByHandle', refused)

    def test_rename_refused_as_another_device_is_copied_verified_and_the_old_file_removed(self):
        calls = []
        # Control: any other refusal still moves nothing and copies nothing.
        with self.refuse_rename(5, calls):
            done = self.mover().run(self.plan(self.other)['move_id'])
        self.assertEqual((calls, done['state'], done['strategy']), ([5], 'failed', 'rename'))
        self.assertEqual(self.old.read_bytes(), self.payload)
        self.assertEqual(list(self.other.iterdir()), [])
        with self.refuse_rename(17, calls):  # ERROR_NOT_SAME_DEVICE (native_io.NOT_SAME_DEVICE)
            move = self.plan(self.other)
            done = self.mover().run(move['move_id'])
        self.assertEqual(calls, [5, 17], 'positive control: the rename was tried and refused')
        self.assertEqual((done['state'], done['strategy']), ('complete', 'copy'))
        new = self.other / self.old.name
        self.assertEqual(new.read_bytes(), self.payload)
        self.assertFalse(self.old.exists())
        self.assertEqual([p.name for p in self.other.iterdir()], [self.old.name])  # no temporary left
        self.assertEqual(self.effective()['final_path'], str(new))
        with connect(self.db) as db:
            states = [r[0] for r in db.execute('SELECT to_state FROM book_move_events WHERE move_id=? ORDER BY event_id', (move['move_id'],))]
        self.assertEqual(states[:3], ['queued', 'rename_intent', 'copy_intent'])
