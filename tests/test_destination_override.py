"""Rulings 69, 70 and 71h-k (Sergei 2026-10-29): the folder Sergei chooses for a book.

Validation (the engine is the only validator), precedence over every computed folder in every planner caller, the stored
choice (per book, retractable, frozen at approval), the claim check that replans a pending job, the row payload, the
finished-book path that queues a move (never a conversion), the 71h Sorted rule for a chosen folder, the queued HTTP press
and Open folder's sentence. Real temporary folders; the writable probe, the picker and Explorer are seams."""
import copy
import json
import os
import shutil
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import book_move
import destination_admission
import destination_overrides as overrides
import entered_names
import organization
import source_config
from merge_service import MergeService
from scanner import connect
import test_book_move as fixture


def review(**fields):
    value = {'title': 'Крадущийся', 'author': 'Петров Иван', 'canonical_author': 'Петров Иван', 'series': '', 'number': '', 'universe': '',
             'anthology': False, 'multi_author': False, 'original_language': 'Russian', 'organization_policy': 'books-hierarchy-v2'}
    value.update(fields)
    return value


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='do'))
        self.addCleanup(shutil.rmtree, self.base, True)
        (self.base / 'src').mkdir(); (self.base / 'data').mkdir(); (self.base / 'ok').mkdir()

    def cause(self, folder, **options):
        options.setdefault('sources', (str(self.base / 'src'),))
        options.setdefault('data_dir', str(self.base / 'data'))
        options.setdefault('probe', lambda folder: None)
        with self.assertRaises(overrides.Refused) as raised:
            overrides.validate(str(folder), **options)
        return raised.exception.cause

    def test_each_refusal_has_its_typed_cause(self):
        self.assertEqual(self.cause(self.base / 'missing'), 'unavailable')
        file = self.base / 'file.txt'; file.write_text('x')
        self.assertEqual(self.cause(file), 'unavailable')
        self.assertEqual(self.cause('relative\\folder'), 'unavailable')

        def refuse(folder):
            raise PermissionError('denied')
        self.assertEqual(self.cause(self.base / 'ok', probe=refuse), 'not_writable')
        (self.base / 'src' / 'inner').mkdir()
        self.assertEqual(self.cause(self.base / 'src' / 'inner'), 'unsafe')
        self.assertEqual(self.cause(self.base / 'src'), 'unsafe')
        self.assertEqual(self.cause(self.base / 'data'), 'unsafe')
        self.assertEqual(self.cause(self.base / 'ok', name='x' * 240 + '.m4b'), 'not_writable')

    def test_a_junction_is_refused(self):
        import _winapi
        link = self.base / 'link'
        _winapi.CreateJunction(str(self.base / 'ok'), str(link))
        self.assertEqual(self.cause(link), 'unsafe')

    def test_an_ordinary_folder_is_accepted_with_its_native_identity_and_the_real_probe_leaves_nothing(self):
        folder, identity = overrides.validate(str(self.base / 'ok'), sources=(str(self.base / 'src'),), data_dir=str(self.base / 'data'))
        self.assertEqual(folder, str(self.base / 'ok'))
        self.assertTrue(identity['volume'] and (identity['high'] or identity['low']))
        self.assertEqual(list((self.base / 'ok').iterdir()), [])
        self.assertTrue(overrides.same_identity(identity, overrides.current_identity(folder)))
        (self.base / 'ok').rmdir(); (self.base / 'ok').mkdir()  # replaced by a new folder of the same name
        self.assertFalse(overrides.same_identity(identity, overrides.current_identity(folder)))

    def test_a_source_or_data_folder_under_another_spelling_is_refused_by_where_it_really_is(self):
        # Senua 0.24.0 M2: on the NAS one share is both \\NAS\share and Z:; here a junction gives the second spelling. The
        # text never matches, the folder is the same: refused before the probe writes anything.
        import _winapi
        real = self.base / 'real'
        for name in ('src/inner', 'data', 'mine'):
            (real / name).mkdir(parents=True)
        _winapi.CreateJunction(str(real), str(self.base / 'alias'))
        written = []
        alias_src, alias_data = str(self.base / 'alias' / 'src'), str(self.base / 'alias' / 'data')
        for chosen, sources, data in ((real / 'src' / 'inner', (alias_src,), str(self.base / 'data')),
                                      (real / 'src', (alias_src,), str(self.base / 'data')),
                                      (real / 'data', (str(self.base / 'src'),), alias_data)):
            with self.subTest(chosen=chosen):
                self.assertEqual(self.cause(chosen, sources=sources, data_dir=data, probe=written.append), 'unsafe')
        self.assertEqual(written, [], 'refused before the probe writes')
        # Positive control: a folder beside them, under the same spellings, is accepted.
        folder, _ = overrides.validate(str(real / 'mine'), sources=(alias_src,), data_dir=alias_data, probe=written.append)
        self.assertEqual((folder, written), (str(real / 'mine'), [str(real / 'mine')]))

    def test_an_unsafe_folder_says_which_folder_or_why(self):
        """Judy 2026-10-30: the refusal names the source folder the chosen one is inside, or says it is the app's own, or a
        link or junction; the page shows the sentence as sent. By path text and by where the folder really is (M2)."""
        import _winapi
        real = self.base / 'real'
        for name in ('src/inner', 'data', 'ok/sub'):
            (real / name).mkdir(parents=True)
        _winapi.CreateJunction(str(real), str(self.base / 'alias'))
        _winapi.CreateJunction(str(real / 'ok'), str(self.base / 'link'))
        source, alias_src, alias_data = str(self.base / 'src'), str(self.base / 'alias' / 'src'), str(self.base / 'alias' / 'data')
        inside = 'That folder is inside %s, one of your source folders. Choose another folder.'
        app, link = 'That folder belongs to the app. Choose another folder.', 'That folder is a link or junction. Choose an ordinary folder.'
        (self.base / 'src' / 'inner').mkdir()
        for chosen, options, said in ((self.base / 'src' / 'inner', {}, inside % source),
                                      (self.base / 'data', {}, app),
                                      (self.base / 'link', {}, link),  # the folder itself is a junction
                                      (self.base / 'link' / 'sub', {}, link),  # a junction above it
                                      (real / 'src' / 'inner', {'sources': (alias_src,)}, inside % alias_src),
                                      (real / 'data', {'data_dir': alias_data}, app)):
            with self.subTest(chosen=chosen):
                options = dict({'sources': (source,), 'data_dir': str(self.base / 'data'), 'probe': lambda folder: None}, **options)
                with self.assertRaises(overrides.Refused) as raised:
                    overrides.validate(str(chosen), **options)
                self.assertEqual((raised.exception.cause, str(raised.exception)), ('unsafe', said))

    def test_a_place_that_cannot_be_told_refuses_with_its_name_and_a_missing_one_holds_nothing(self):
        import ctypes
        away = 'Q:\\Away\\Audiobooks'

        def resolve(place):
            if str(place).startswith('Q:'):
                raise ctypes.WinError(53)  # ERROR_BAD_NETPATH: the share is away
            return overrides.resolved_identity(place)
        with self.assertRaises(overrides.Refused) as raised:
            overrides.validate(str(self.base / 'ok'), sources=(str(self.base / 'src'), away), data_dir=str(self.base / 'data'),
                               probe=lambda folder: None, resolve=resolve)
        self.assertEqual(raised.exception.cause, 'unchecked')
        self.assertEqual(str(raised.exception), away + " isn't available, so the app can't tell whether that folder is inside it. Connect the drive and try again.")
        # Judy 2026-10-30, each case its own sentence. (b) A place that gives no file index: only a folder on another volume
        # is provably elsewhere. (a) A place whose drive reports volume serial 0: refused even for a folder on another drive.
        volume = overrides.resolved_identity(self.base)[0]
        source, data = str(self.base / 'src'), str(self.base / 'data')
        index_said = ("The app can't tell whether that folder is inside %s, because both are on a drive that can't confirm which "
                      "folder is which. Choose a folder on another drive." % source)
        serial_said = ("No folder can be chosen while %s is one of your source folders: its drive can't confirm which folder is "
                       "which. Source folders can't be removed in the app." % source)
        app_said = "The app's data folder is on a drive that can't confirm which folder is which, so no folder can be chosen."
        for place, found, said in ((source, (volume, 0, 0), index_said),  # (b)
                                   (source, (volume + 1, 0, 0), None),  # (b) control: on another volume, accepted
                                   (source, (0, 1, 2), serial_said),  # (a) a source folder
                                   (data, (0, 1, 2), app_said)):  # (a) the data folder
            with self.subTest(place=place, found=found):
                options = dict(sources=(source,), data_dir=data, probe=lambda folder: None,
                               resolve=lambda path, place=place, found=found: found if path == place else overrides.resolved_identity(path))
                if said:
                    with self.assertRaises(overrides.Refused) as raised:
                        overrides.validate(str(self.base / 'ok'), **options)
                    self.assertEqual((raised.exception.cause, str(raised.exception)), ('unchecked', said))
                else:
                    self.assertEqual(overrides.validate(str(self.base / 'ok'), **options)[0], str(self.base / 'ok'))

        # (c) The chosen folder gives no file index on the source folder's volume: the same sentence as (b).
        class NoIndex(overrides.DirectoryBoundary):
            def __enter__(self):
                held = super().__enter__()
                held.identities[-1] = held.identities[-1][:2] + (0, 0)
                return held
        with self.assertRaises(overrides.Refused) as raised:
            overrides.validate(str(self.base / 'ok'), sources=(source,), data_dir=data, probe=lambda folder: None, boundary=NoIndex)
        self.assertEqual((raised.exception.cause, str(raised.exception)), ('unchecked', index_said))
        # A source folder that is simply not there (its parent opens) holds nothing: accepted, as before.
        folder, _ = overrides.validate(str(self.base / 'ok'), sources=(str(self.base / 'src'), str(self.base / 'gone' / 'deeper')),
                                       data_dir=str(self.base / 'data'), probe=lambda folder: None)
        self.assertEqual(folder, str(self.base / 'ok'))


class PrecedenceTests(unittest.TestCase):
    root = 'Z:\\Audiobooks Sorted'

    def plan(self, value, folder):
        facts = {'destination_override': {'id': 'o', 'folder': folder, 'identity': {}}} if folder else None
        return organization.plan(self.root, value, facts=facts)

    def test_the_chosen_folder_outranks_every_computed_folder_and_keeps_the_file_name(self):
        cases = {'no author': review(author=organization.NO_AUTHOR, canonical_author=''),
                 'collection': review(anthology=True, series='Глубина', number='3', title='Глубина 3', author='Разные авторы', canonical_author='Разные авторы'),
                 'universe': review(universe='Вселенная Дозоров', series='Межавторский цикл', number='4'),
                 'series': review(series='Цикл', number='2'),
                 'author': review()}
        chosen = self.root + '\\Мои\\Разное'
        for name, value in cases.items():
            with self.subTest(name):
                computed = self.plan(value, None)['path']
                found = self.plan(value, chosen)
                self.assertEqual(found['path'], os.path.join(chosen, os.path.basename(computed)))
                self.assertEqual(found['relative_path'], os.path.relpath(found['path'], self.root))
                self.assertEqual(found['accepted_routing']['destination_folder'], chosen)

    def test_a_folder_outside_the_output_root_keeps_the_computed_path_for_the_conversion(self):
        value = review()
        self.assertEqual(self.plan(value, 'D:\\Books')['path'], self.plan(value, None)['path'])

    def test_frozen_plan_and_the_queued_route_check_agree_with_the_chosen_folder(self):
        value = review()
        facts = {'destination_override': {'id': 'o', 'folder': self.root + '\\Мои', 'identity': {}}}
        destination = organization.plan(self.root, value, facts=facts)['path']
        manifest = {'root': 'Z:\\Audiobooks', 'output_root': self.root, 'destination': destination, 'metadata': value, 'metadata_facts': facts,
                    'candidate_id': 'c', 'sources': []}
        self.assertEqual(organization.frozen_plan(manifest, self.root)['path'], destination)
        policy = destination_admission.policy({'Audiobooks': 'Z:\\Audiobooks'}, ['Z:\\Audiobooks'], self.root)
        self.assertIsNone(destination_admission.observe(manifest, policy))
        # The same job planned before the choice now reads as needing review: the claim check replans it first.
        manifest['metadata_facts'] = {}
        self.assertIsNotNone(destination_admission.observe(manifest, policy))

    def test_a_malformed_choice_refuses(self):
        with self.assertRaises(ValueError):
            organization.plan(self.root, review(), facts={'destination_override': {'folder': 'relative'}})


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='ds'))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.db = str(self.base / 'c.sqlite3')

    def test_choice_per_book_survives_a_revision_and_retracts(self):
        row = {'id': 'a', 'revision': 1, 'members': [{'path': 'Z:\\A\\01.mp3'}, {'path': 'Z:\\A\\02.mp3'}]}
        key = entered_names.book_key(row)
        with connect(self.db) as db:
            overrides.choose(db, folder='D:\\One', identity={'volume': 1, 'high': 0, 'low': 2}, book_key=key, candidate_id='a')
            overrides.choose(db, folder='D:\\Two', identity={'volume': 1, 'high': 0, 'low': 3}, book_key=key, candidate_id='a')
            again = dict(row, revision=7, members=list(reversed(row['members'])))
            self.assertEqual(overrides.live(db, book_key=entered_names.book_key(again))['folder'], 'D:\\Two')
            self.assertEqual(overrides.folders(db), ('D:\\One', 'D:\\Two'))
            self.assertEqual(overrides.retract(db, book_key=key), 1)
            self.assertIsNone(overrides.live(db, book_key=key))

    def test_a_finished_book_keeps_its_conversion_choice_until_its_own_is_made_or_reset(self):
        with connect(self.db) as db:
            overrides.choose(db, folder='D:\\Before', identity={}, book_key='k', candidate_id='a')
            self.assertEqual(overrides.live(db, book_key='k', job_id='j')['folder'], 'D:\\Before')
            overrides.choose(db, folder='D:\\After', identity={}, book_key='k', candidate_id='a', job_id='j')
            self.assertEqual(overrides.live(db, book_key='k', job_id='j')['folder'], 'D:\\After')
            overrides.retract(db, book_key='k', job_id='j')
            self.assertIsNone(overrides.live(db, book_key='k', job_id='j'))


class SortedRuleTests(unittest.TestCase):
    """Ruling 71h: a chosen folder counts as Sorted for the book filed directly in it; a source folder never does."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='sr'))
        self.addCleanup(shutil.rmtree, self.base, True)
        for name in ('src', 'srt', 'mine'):
            (self.base / name).mkdir()

    def test_require_sorted_accepts_the_chosen_folder_only(self):
        src, srt, mine = (str(self.base / n) for n in ('src', 'srt', 'mine'))
        source_config.require_sorted(os.path.join(srt, 'a', 'b.m4b'), srt, (src,))
        with self.assertRaises(ValueError):
            source_config.require_sorted(os.path.join(mine, 'b.m4b'), srt, (src,))
        source_config.require_sorted(os.path.join(mine, 'b.m4b'), srt, (src,), (mine,))
        with self.assertRaises(ValueError):
            source_config.require_sorted(os.path.join(mine, 'deeper', 'b.m4b'), srt, (src,), (mine,))
        with self.assertRaises(ValueError):
            source_config.require_sorted(os.path.join(src, 'b.m4b'), srt, (src,), (src,))


def merge_double(fix, finished=True, computed=None):
    """A MergeService whose engine parts are the fixture's: its real ruling-69 methods on a real catalog and real files."""
    names = ('destination_choose', '_queue_move', '_destination_answer', '_override_rows', '_live_override', '_with_override', '_chosen_display', '_shown_path',
             '_move_root', '_override_stale', 'destination_view', '_chosen_folders', '_chosen_root', '_job_manifest', '_mover', 'run_move',
             '_after_move', 'cancel_move', '_publication_location', '_all_source_roots', '_destination_changed', '_start_move_recovery',
             '_move_to_chosen', '_approval_destination', '_move_running', '_unfinished_move', '_renamed_waiting', 'open_folder', 'OVERRIDE_REPLANNED', 'OVERRIDE_UNAVAILABLE',
             'FOLDER_UNAVAILABLE')
    Double = type('Double', (), {name: MergeService.__dict__[name] for name in names})
    double = Double()
    row = {'id': fix.candidate, 'revision': 1, 'title_clue': 'Book', 'members': [{'path': str(fix.library / 'a.mp3')}], 'metadata': {}}
    double.row = row
    double.inventory = SimpleNamespace(database=fix.db, output_root=str(fix.sorted), all_source_roots=lambda: (str(fix.library),))
    double.cache_dir = fix.base / 'data' / 'merge-cache'
    double.operation_lock = threading.RLock()
    double.draining = False
    double.folder_probe = lambda folder: None
    double.move_same_volume = None
    double.move_fault = None
    double.move_requester = None
    double.publication_bindings = fix.bindings
    double._validated_outputs = {}
    with connect(fix.db) as db:
        db.execute('CREATE TABLE IF NOT EXISTS owned_artifacts(path TEXT PRIMARY KEY, job_id TEXT, kind TEXT, sha256 TEXT, size INTEGER)')
    double.verified = []
    double._publication_verified = lambda record: double.verified.append(record)
    double.invalidate_status = lambda: None
    double.reviews = SimpleNamespace(_row=lambda library, identity, revision=None: copy.deepcopy(row), _output_root=lambda row, review=None: str(fix.sorted))
    publication = {'kind': 'original', 'parent': {'job_id': fix.job_id}}
    double._finished = lambda identity, jobs=None: (publication, 'base', fix.job_id) if finished else None
    target = computed or str(fix.sorted / 'Без автора' / fix.old.name)
    double._computed_destination = lambda row, manifest=None: target
    return double


class ChooseTests(fixture.MoveFixture):
    def test_finished_book_choice_queues_a_move_never_a_conversion(self):
        merge = merge_double(self)
        jobs = self.jobs()
        answer = merge.destination_choose(self.candidate, 1, str(self.other))
        self.assertEqual(answer['outcome'], 'move_queued')
        self.assertEqual(answer['move']['state'], 'moved')
        self.assertEqual(self.effective()['final_path'], str(self.other / self.old.name))
        self.assertEqual(self.jobs(), jobs)
        self.assertEqual(merge.verified[-1]['final_path'], str(self.other / self.old.name))  # its last full verification
        with connect(self.db) as db:
            owned = db.execute("SELECT kind FROM owned_artifacts WHERE path=?", (str(self.other / self.old.name),)).fetchone()
        self.assertEqual(owned[0], 'output')
        # Same folder again: nothing to do.
        self.assertEqual(merge.destination_choose(self.candidate, 1, str(self.other))['outcome'], 'unchanged')

    def test_use_computed_folder_on_a_finished_book_moves_it_back(self):
        merge = merge_double(self, computed=str(self.old))
        merge.destination_choose(self.candidate, 1, str(self.other))
        answer = merge.destination_choose(self.candidate, 1, None)
        self.assertEqual(answer['move']['state'], 'moved')
        self.assertEqual(self.effective()['final_path'], str(self.old))

    def test_queued_through_the_requester_and_cancelled_before_it_runs(self):
        merge = merge_double(self)
        queued = []
        merge.move_requester = lambda move, title: queued.append(move) or {'queued': True, 'id': 'q1'}
        answer = merge.destination_choose(self.candidate, 1, str(self.other))
        self.assertEqual((answer['move']['state'], answer['move']['queue']['id']), ('queued', 'q1'))
        self.assertTrue(self.old.exists())
        self.assertTrue(merge.cancel_move(queued[0]['move_id']))
        self.assertIsNone(merge.destination_view([dict(merge.row)]) or None)

    def test_a_move_whose_retries_ran_out_reads_unfinished_on_every_list_read_73k(self):
        """Ruling 73k (Judy): the state is the engine's, not the page's. While the move is journaled and not running, every
        list read (a page reload) gives 'unfinished' with the target folder, why ('copy': the placed copy couldn't be opened;
        'catalog': its progress couldn't be saved) and the raw error; a new choice says to restart; recovery finishes it."""
        import native_io
        import sqlite3
        real, writes = book_move.VerifiedFile, book_move.Mover._write
        for cause in ('copy', 'catalog'):
            with self.subTest(cause=cause):
                if cause == 'catalog':
                    self.setUp()
                merge = merge_double(self)
                merge.move_same_volume = lambda a, b: False  # the copy strategy
                target = self.other / self.old.name

                def unopenable(path, *args, **kwargs):
                    if Path(str(path)) == target and target.exists():
                        raise native_io.FileInUse('Cannot protect exact file: in use')
                    return real(path, *args, **kwargs)

                def unwritable(mover, move_id, state, **values):
                    if state == 'committed':
                        raise sqlite3.OperationalError('disk I/O error')
                    return writes(mover, move_id, state, **values)
                fault = patch.object(book_move, 'VerifiedFile', unopenable) if cause == 'copy' else patch.object(book_move.Mover, '_write', unwritable)
                with fault, patch.object(book_move, 'time', SimpleNamespace(sleep=lambda seconds: None)):
                    answer = merge.destination_choose(self.candidate, 1, str(self.other))
                line = answer['move']
                self.assertEqual((answer['outcome'], line['state'], line['cause'], line['folder']), ('move_queued', 'unfinished', cause, str(self.other)))
                for _ in range(2):  # the page reloads: each list read asks the engine again
                    row = dict(merge.row, current_audiobook={'state': 'verified', 'path': str(self.old)})
                    merge.destination_view([row])
                    self.assertEqual((row['move']['state'], row['move']['cause'], row['move']['folder']), ('unfinished', cause, str(self.other)))
                    self.assertEqual(row['output']['absolute'], str(self.old), 'Now in: the old file, still the book')
                self.assertIn('Cannot protect exact file' if cause == 'copy' else 'disk I/O error', row['move']['detail'])
                self.assertTrue(target.exists() and self.old.exists(), 'both files kept')
                # A new choice for the book says to restart, never "being moved now".
                elsewhere = self.base / 'elsewhere'
                elsewhere.mkdir(exist_ok=True)
                with self.assertRaises(book_move.Refused) as raised:
                    merge.destination_choose(self.candidate, 1, str(elsewhere))
                self.assertEqual((raised.exception.cause, str(raised.exception)), ('unfinished', book_move.UNFINISHED))
                # While it runs (here: marked running) it reads 'moving', as before.
                merge.__dict__.setdefault('_moves_running', set()).add(line['move_id'])
                row = dict(merge.row)
                merge.destination_view([row])
                self.assertEqual(row['move']['state'], 'moving')
                merge._moves_running.clear()
                # Recovery at the next start finishes it.
                merge._start_move_recovery()
                merge._move_recovery.join(60)
                row = dict(merge.row)
                merge.destination_view([row])
                self.assertEqual(row['move']['state'], 'moved')
                self.assertEqual(self.effective()['final_path'], str(target))

    def test_a_renamed_book_waiting_for_a_restart_stays_finished_and_opens_its_new_folder_D1r3(self):
        """Senua 0.24.0 D1r3 and Judy's two checks, while the renamed file is in the new folder and the move is not
        committed. The catalog still names the old path, which is gone, so describe() reads the book unavailable and the
        converted check reads it not ready. (a) The row stays a finished book in the destination block, "Now in" the new
        place. (b) Open book folder opens the new folder, never the old, empty one; with nothing waiting it opens nothing."""
        import native_io
        real_rename, real_file = book_move.rename_no_replace, book_move.VerifiedFile
        merge = merge_double(self)  # one volume here: the rename strategy
        target = self.other / self.old.name

        def accepted_unproven(*args, **kwargs):
            real_rename(*args, **kwargs)
            raise native_io.RenamePostconditionError('Renamed audiobook could not be re-opened: in use')

        def in_use(path, *args, **kwargs):
            if Path(str(path)) == target:
                raise native_io.FileInUse('Cannot protect exact file: in use')
            return real_file(path, *args, **kwargs)
        with patch.object(book_move, 'rename_no_replace', accepted_unproven), patch.object(book_move, 'VerifiedFile', in_use), \
                patch.object(book_move, 'time', SimpleNamespace(sleep=lambda seconds: None)):
            answer = merge.destination_choose(self.candidate, 1, str(self.other))
        self.assertEqual((answer['move']['state'], answer['move']['cause'], answer['move']['folder']), ('unfinished', 'renamed', str(self.other)))
        self.assertFalse(self.old.exists(), 'positive control: the old file is gone')
        self.assertTrue(target.exists())
        # (a) A list read as the engine makes it now.
        row = dict(merge.row, audiobook_ready=False, current_audiobook={'state': 'unavailable', 'reason': 'Cannot protect exact file'})
        merge.destination_view([row])
        self.assertEqual((row['move']['state'], row['move']['cause']), ('unfinished', 'renamed'))
        self.assertIs(row['audiobook_ready'], True, 'still a finished book')
        self.assertEqual((row['output']['absolute'], row['output']['folder']), (str(target), str(self.other)), 'Now in the new place')
        # (b) Open book folder.
        opened = []
        merge.inventory.roots = {'Audiobooks': str(self.library)}
        merge.jobs = SimpleNamespace(status=lambda: {'jobs': []})
        merge.publications = SimpleNamespace(describe=lambda jobs, identity: {'state': 'unavailable', 'reason': 'Cannot protect exact file'})
        merge.dispatch_folder = opened.append
        self.assertEqual(merge.open_folder('Audiobooks', 'candidates', self.candidate, 'output'), {'opened': True, 'directory': str(self.other)})
        self.assertEqual(opened, [str(self.other)])
        merge._move_unfinished.clear()  # control: nothing known to wait for a restart opens nothing
        with self.assertRaises(ValueError) as refused:
            merge.open_folder('Audiobooks', 'candidates', self.candidate, 'output')
        self.assertEqual((str(refused.exception), opened), (MergeService.FOLDER_UNAVAILABLE, [str(self.other)]))

    def test_not_finished_saves_the_choice_and_approves_nothing(self):
        merge = merge_double(self, finished=False)
        answer = merge.destination_choose(self.candidate, 1, str(self.other))
        self.assertEqual(answer['outcome'], 'saved')
        self.assertEqual(answer['destination_override']['folder'], str(self.other))
        self.assertTrue(answer['destination_override']['outside_sorted'])
        self.assertEqual(answer['preview'], None if not isinstance(answer['preview'], dict) else answer['preview'])
        self.assertEqual(self.jobs()[0][1], 'completed')  # nothing queued or written for a job
        self.assertEqual(merge.destination_choose(self.candidate, 1, None)['outcome'], 'cleared')

    def test_refusals_carry_their_cause_and_save_nothing(self):
        merge = merge_double(self, finished=False)
        app = 'That folder belongs to the app. Choose another folder.'  # Judy 2026-10-30: the page shows these as sent
        for folder, cause, said in ((str(self.base / 'missing'), 'unavailable', None),
                                    (str(self.library), 'unsafe', 'That folder is inside %s, one of your source folders. Choose another folder.' % self.library),
                                    (str(self.base / 'data'), 'unsafe', app)):
            with self.subTest(folder):
                with self.assertRaises(overrides.Refused) as raised:
                    merge.destination_choose(self.candidate, 1, folder)
                self.assertEqual(raised.exception.cause, cause)
                if said:
                    self.assertEqual(str(raised.exception), said)
        merge.cache_dir.mkdir(parents=True)
        with self.assertRaises(overrides.Refused) as raised:
            merge.destination_choose(self.candidate, 1, str(merge.cache_dir))
        self.assertEqual((raised.exception.cause, str(raised.exception)), ('unsafe', app))
        with connect(self.db) as db:
            self.assertEqual(overrides.folders(db), ())

    def test_row_payload(self):
        merge = merge_double(self, finished=False)
        merge.row['id'] = str(uuid.uuid4())  # a book with no completed job: its Goes to line names the chosen folder
        merge.destination_choose(self.candidate, 1, str(self.sorted / 'Author'))
        row = dict(merge.row, preview={'path': str(self.sorted / 'Без автора' / 'x.m4b')}, ask={'destination': {'path': 'Без автора\\x.m4b', 'absolute': 'Z:\\x', 'taken': False}})
        merge.destination_view([row])
        expected = str(self.sorted / 'Author' / self.old.name)
        self.assertEqual(row['destination_override'], {'folder': str(self.sorted / 'Author'), 'computed_folder': 'Без автора',
                                                       'computed_path': str(self.sorted / 'Без автора' / self.old.name), 'outside_sorted': False})
        self.assertEqual((row['preview']['path'], row['preview']['absolute']), (expected, expected))
        # The ask row's own destination comes from approval_preview (planned with the choice) and is what Approve sends back.
        self.assertEqual(row['ask']['destination']['path'], 'Без автора\\x.m4b')
        self.assertIsNone(row['output']); self.assertIsNone(row['move'])
        plain = dict(merge.row, current_audiobook={'state': 'verified', 'path': str(self.old)})
        merge.destination_view([plain])
        self.assertEqual(plain['output'], {'path': os.path.relpath(str(self.old), str(self.sorted)), 'absolute': str(self.old), 'folder': str(self.old.parent)})

    def test_pending_job_planned_with_another_folder_is_replanned(self):
        merge = merge_double(self, finished=False)
        job = {'job_id': 'j', 'manifest': json.dumps({'candidate_id': self.candidate, 'metadata_facts': {}})}
        self.assertFalse(merge._override_stale(job))
        merge.destination_choose(self.candidate, 1, str(self.other))
        self.assertTrue(merge._override_stale(job))
        self.assertEqual(merge._replan_reasons['j'], MergeService.OVERRIDE_REPLANNED)
        facts = merge._with_override(merge.row, {}, strict=True)
        frozen = {'job_id': 'k', 'manifest': json.dumps({'candidate_id': self.candidate, 'metadata_facts': facts})}
        self.assertFalse(merge._override_stale(frozen))
        self.other.rmdir(); self.other.mkdir()  # the chosen folder replaced: fails closed
        self.assertTrue(merge._override_stale(frozen))
        with self.assertRaisesRegex(ValueError, "isn't available"):
            merge._with_override(merge.row, {}, strict=True)

    def test_published_before_its_chosen_folder_is_moved_after_completion(self):
        merge = merge_double(self, finished=True)
        merge.jobs = SimpleNamespace(status=lambda: {'jobs': [{'job_id': self.job_id, 'state': 'completed', 'manifest': self.manifest}]})
        with connect(self.db) as db:
            identity = overrides.validate(str(self.other), probe=lambda f: None)[1]
            overrides.choose(db, folder=str(self.other), identity=identity, book_key=entered_names.book_key(merge.row), candidate_id=self.candidate)
        merge._move_to_chosen(self.job_id)
        self.assertEqual(self.effective()['final_path'], str(self.other / self.old.name))

    def test_chosen_folders_feed_the_roots_a_book_may_live_in(self):
        merge = merge_double(self)
        merge.destination_choose(self.candidate, 1, str(self.other))
        self.assertIn(str(self.other), merge._chosen_folders())
        self.assertTrue(merge._chosen_root(str(self.other), str(self.other / self.old.name)))
        self.assertFalse(merge._chosen_root(str(self.other), str(self.other / 'deeper' / self.old.name)))

    def test_moved_book_resolves_for_delete_book_and_the_current_audiobook_view(self):
        import book_delete
        from current_audiobook import CurrentAudiobooks
        merge = merge_double(self)
        merge.destination_choose(self.candidate, 1, str(self.other))
        service = SimpleNamespace(publication_bindings=self.bindings)
        record, final = book_delete._sorted_record(service, self.output)  # Delete book and Remove this copy read it so
        self.assertEqual(final, str(self.other / self.old.name))
        replacements = SimpleNamespace(representative=lambda jobs, candidate: ({'job_id': self.job_id, 'state': 'completed', 'manifest': dict(self.manifest, cover={'path': 'c.jpg', 'sha256': '0' * 64}), 'output': self.output}, None))
        current = CurrentAudiobooks((str(self.library), str(self.sorted)), self.base / 'repairs', replacements, bindings=self.bindings)
        jobs = [{'job_id': self.job_id}]
        self.assertEqual(current.describe(jobs, self.candidate)['state'], 'unavailable')  # outside every root it knows
        current.chosen_roots = merge._chosen_folders
        found = current.describe(jobs, self.candidate)
        self.assertIn(found["state"], ("verifying", "verified"), found)
        current.close()


class ApprovalPlanTests(fixture.MoveFixture):
    """The Goes to line, the approval preview and Approve's own check plan with the chosen folder (one function)."""

    def test_inside_sorted_is_planned_there_outside_is_shown_there(self):
        merge = merge_double(self, finished=False)
        result = {'review': review(author=organization.NO_AUTHOR, canonical_author=''), 'metadata_facts': None}
        relative, absolute, reason = merge._approval_destination(merge.row, result)
        self.assertEqual(relative, os.path.join(organization.NO_AUTHOR, 'Крадущийся.m4b'))
        inside = self.sorted / 'Мои'
        inside.mkdir()
        merge.destination_choose(self.candidate, 1, str(inside))
        relative, absolute, reason = merge._approval_destination(merge.row, result)
        self.assertEqual((relative, absolute), (os.path.join('Мои', 'Крадущийся.m4b'), str(inside / 'Крадущийся.m4b')))
        merge.destination_choose(self.candidate, 1, str(self.other))
        relative, absolute, reason = merge._approval_destination(merge.row, result)
        self.assertEqual((relative, absolute), (str(self.other / 'Крадущийся.m4b'),) * 2)
        # The conversion itself still publishes inside Sorted (then the book is moved): the frozen plan keeps that path.
        facts = merge._with_override(merge.row, {}, strict=True)
        self.assertEqual(organization.plan(str(self.sorted), result['review'], facts=facts)['path'], str(self.sorted / organization.NO_AUTHOR / 'Крадущийся.m4b'))

    def test_a_moved_book_is_not_planned_for_an_offline_relocation(self):
        import publication_locations as p
        merge = merge_double(self)
        merge.destination_choose(self.candidate, 1, str(self.other))
        with connect(self.db) as db:
            p.initialize(db)
            job = dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (self.job_id,)).fetchone())
            with self.assertRaisesRegex(p.PublicationRefused, 'folder you chose'):
                p.plan(db, job, 'base', self.output, str(self.sorted), str(self.sorted / 'x.m4b'), {'routing_policy_version': 'v', 'source_fingerprint': 'fp'})


class RecoveryAtStartTests(fixture.MoveFixture):
    def test_engine_start_reconciles_an_interrupted_move(self):
        merge = merge_double(self)
        merge.move_same_volume = lambda a, b: False
        self.crash_at = 'committed'
        merge.move_fault = self.fault
        with self.assertRaises(fixture.Crash):
            merge.destination_choose(self.candidate, 1, str(self.other))
        merge.move_fault = None
        merge._start_move_recovery()
        merge._move_recovery.join(60)
        self.assertFalse(self.old.exists())
        with connect(self.db) as db:
            self.assertEqual(db.execute('SELECT state FROM book_moves').fetchone()[0], 'complete')


class QueueTests(unittest.TestCase):
    """The press through Handler.queue_press and the real run_queued, a stub engine (test_ruling35's pattern)."""

    def setUp(self):
        import test_ruling35 as base
        import web_server
        self.server = base.Server()
        merge = self.server.merge
        merge.destination_calls = []
        merge.destination_choose = lambda id, revision, folder: merge.destination_calls.append((id, revision, folder)) or {'outcome': 'saved'}
        merge.run_move = lambda move_id: {'state': 'moved', 'move_id': move_id}
        merge.cancelled = []
        merge.cancel_move = lambda move_id: merge.cancelled.append(move_id) or True
        self.base = base

    def test_destination_press_runs_through_the_queue_and_a_move_is_always_queued(self):
        from action_queue import ActionQueue, ACTIONS, ALWAYS, SERVER_RUN
        self.assertIn('destination', ACTIONS); self.assertIn('move', ALWAYS); self.assertIn('move', SERVER_RUN)
        queue = ActionQueue(self.server, poll=0.01)
        identity = str(uuid.uuid4())
        self.assertIsNone(queue.enqueue('destination', identity, 'Book', {'revision': 1, 'folder': 'D:\\Books'}))
        answer = self.server.run_queued({'action': 'destination', 'book_id': identity, 'args': {'revision': 1, 'folder': 'D:\\Books'}})
        self.assertEqual(answer, {'result': 'done', 'answer': {'outcome': 'saved'}})
        self.assertEqual(self.server.run_queued({'action': 'move', 'book_id': identity, 'args': {'move_id': 'm'}})['answer']['move']['state'], 'moved')
        queue.closed = True  # a queued move taken back says cancelled in its journal
        queue.items.append({'id': 'x', 'action': 'move', 'book_id': identity, 'title': '', 'args': {'move_id': 'm2'}, 'queued_at': 0, 'blocker': 'operation'})
        self.assertEqual(queue.cancel('x'), {'cancelled': True})
        self.assertEqual(self.server.merge.cancelled, ['m2'])

    def test_a_move_whose_retries_ran_out_is_an_unfinished_outcome_73k(self):
        """Ruling 73k: the queue outcome says 'unfinished' with the folder and the engine's move line (title is the queue's
        own), never code 'failed' with the raw OS error; the raw error stays in the move line's detail (Technical details)."""
        line = {'state': 'unfinished', 'cause': 'copy', 'folder': 'D:\\Books', 'target': 'D:\\Books\\Hat.m4b', 'move_id': 'm',
                'detail': 'Cannot protect exact file: in use'}
        self.server.merge.run_move = lambda move_id: dict(line)
        answer = self.server.run_queued({'action': 'move', 'book_id': 'b', 'args': {'move_id': 'm'}})
        self.assertEqual(answer, {'result': 'refused', 'cause': 'unfinished', 'code': 'unfinished', 'folder': 'D:\\Books', 'move': line})
        self.server.merge.run_move = lambda move_id: {'state': 'moved', 'move_id': move_id}  # control: a finished move
        self.assertEqual(self.server.run_queued({'action': 'move', 'book_id': 'b', 'args': {'move_id': 'm'}})['result'], 'done')

    def test_refusal_is_typed(self):
        merge = self.server.merge

        def refuse(*args):
            raise overrides.Refused('not_writable', 'nope')
        merge.destination_choose = refuse
        answer = self.server.run_queued({'action': 'destination', 'book_id': 'b', 'args': {'revision': 1, 'folder': 'D:\\X'}})
        self.assertEqual((answer['result'], answer['code']), ('refused', 'not_writable'))


class OpenFolderTests(unittest.TestCase):
    """Ruling 70: a gone source folder answers Judy's sentence, or opens the converted file's folder for a finished book."""

    def double(self, folder, output=None):
        merge = SimpleNamespace(inventory=SimpleNamespace(roots={'Audiobooks': 'C:\\'}), FOLDER_UNAVAILABLE=MergeService.FOLDER_UNAVAILABLE,
                                reviews=SimpleNamespace(_row=lambda library, identity: {}), opened=[])
        merge._source_directories = lambda library, view, identity: [{'id': 'd', 'path': folder}]
        merge.dispatch_folder = lambda directory: merge.opened.append(directory)
        merge.jobs = SimpleNamespace(status=lambda: {'jobs': []})
        state = {'state': 'verified', 'path': output, 'identity': 'k'} if output else {'state': 'none', 'reason': 'No verified audiobook created yet'}
        merge.publications = SimpleNamespace(describe=lambda jobs, identity: state, publication=lambda jobs, identity: {},
                                             protected=lambda publication: _held('k'))
        merge._renamed_waiting = lambda identity: None  # no renamed move waits for a restart (D1r3)
        merge.open_folder = MergeService.open_folder.__get__(merge)
        return merge

    def test_gone_source_without_a_finished_book_says_unavailable(self):
        merge = self.double('C:\\definitely-gone-folder-0x1')
        with self.assertRaisesRegex(ValueError, '^Folder unavailable. Connect the library drive and try again.$'):
            merge.open_folder('Audiobooks', 'candidates', 'id')
        self.assertEqual(merge.opened, [])

    def test_gone_source_of_a_finished_book_opens_its_converted_files_folder(self):
        merge = self.double('C:\\definitely-gone-folder-0x1', output='D:\\Books\\Book.m4b')
        answer = merge.open_folder('Audiobooks', 'candidates', 'id')
        self.assertEqual((answer['directory'], answer['fallback']), ('D:\\Books', 'output'))
        self.assertEqual(merge.opened, ['D:\\Books'])


class _held:
    def __init__(self, key):
        self.key = key

    def __enter__(self):
        return None, self.key

    def __exit__(self, *_):
        return False
