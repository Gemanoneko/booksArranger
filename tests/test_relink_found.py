"""0.31.1 (Sergei 2026-11-24): a book the app delivered into Audiobooks Sorted is done. The published-book check no longer puts
a finished book in Needs attention; a book moved or renamed by hand is found again (same name, or same size and file ID; then
the file ID, size and full hash) and its new place recorded as a completed move of origin 'found'. A name alone is never
enough. A finished book that is gone (no file of its name and none with its file ID anywhere under the output folder, its
absence proven) is removed from the records: catalog only, no library or source file touched, never when the drive does not
answer or too many are missing at once, never while the app's own records hold it (Senua M1, m4). Private fixture libraries
only."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

from audio_jobs import AudioJobs
from encoding_policy import PROFILE

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'relink-found-tests'
AREA.mkdir(parents=True, exist_ok=True)
FLAG = 'Recorded output is missing, changed, or failed validation'


def manifest():
    return {'job_id': str(uuid.uuid4()), 'candidate_id': str(uuid.uuid4()), 'candidate_revision': 1,
            'sources': [{'sha256': 'a' * 64, 'fingerprint': {}}], 'metadata': {}, 'destination': 'fixture',
            'profile': PROFILE, 'evidence': {}, 'cover': {}}


@unittest.skipUnless(os.name == 'nt', 'Actual Windows native fixtures required')
class RelinkFoundTests(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        import merge_service
        from publication_binding import PublicationBindings
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        base = Path(self.temp.name)
        self.sources = base / 'Audiobooks'; self.sources.mkdir()
        self.sorted = base / 'Sorted'; self.sorted.mkdir()
        self.db = base / 'catalog.sqlite3'
        with contextlib.closing(sqlite3.connect(self.db)) as db, db:
            db.execute('CREATE TABLE verified_outputs(path TEXT, sha256 TEXT, job_id TEXT, identity TEXT, verified TEXT, PRIMARY KEY(path, sha256))')
            import book_move
            book_move.setup(db)  # as MergeService's construction makes it
        self.service = merge_service.MergeService.__new__(merge_service.MergeService)
        self.service.inventory = SimpleNamespace(database=str(self.db), roots={'Audiobooks': str(self.sources)},
                                                 source_roots=lambda library: (str(self.sources),), output_root=str(self.sorted))
        self.service._validated_outputs = {}
        self.service.publication_bindings = PublicationBindings(str(self.db))
        self.queue = AudioJobs(self.db, None, lambda m: True, self.service._output_valid)
        self.queue.output_current = self.service._output_current
        self.queue.relink = self.service._relink_found
        self.queue.remove_missing = self.service._remove_missing
        self.queue.pass_done = self.service._relink_pass_done
        self.addCleanup(self.queue.close)
        self.log = io.StringIO()
        stderr = patch('sys.stderr', self.log); stderr.start(); self.addCleanup(stderr.stop)

    def tearDown(self):
        self.temp.cleanup()

    def book(self, folder, name, data, flagged=True):
        """One finished book in Sorted/folder, fully checked once (its file ID recorded), then flagged as before 0.31.1."""
        from native_io import DirectoryBoundary
        folder = self.sorted / folder; folder.mkdir(parents=True, exist_ok=True)
        path = folder / name; path.write_bytes(data)
        with DirectoryBoundary(self.sorted, folder) as boundary:
            parent = [list(i) for i in boundary.identities]
        item = manifest(); self.queue.enqueue(item)
        record = {'job_id': item['job_id'], 'root': str(self.sorted), 'final_path': str(path), 'owned_temp': str(path) + '.partial',
                  'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data), 'parent_identity': parent,
                  'validation': {'passed': True, 'profile': PROFILE}}
        self.queue._update(item['job_id'], state='completed', stage='completed', output=json.dumps(record))
        self.assertTrue(self.service._output_current(dict(record)), 'positive control: the book checks at its place')
        if flagged:
            self.queue._update(item['job_id'], state='needs attention', reason=FLAG)
        return item, record

    def row(self, job_id):
        return self.queue._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))[0]

    def check(self):
        self.queue.start_published_check(); self.queue._verifier.join(60)
        self.assertFalse(self.queue._verifier.is_alive())

    def again(self):
        """The next pass, a minute later: a book found missing is looked at again then."""
        self.queue._published_retry_at.clear(); self.service._relink_index = None
        self.check()

    def files(self):
        """Every file under the fixture's libraries with its bytes: what a removal must never change."""
        return {str(path): path.read_bytes() for root in (self.sources, self.sorted) for path in root.rglob('*') if path.is_file()}

    def state(self, job_id):
        row = self.row(job_id)
        return row['state'], row['reason']

    def moves(self, job_id):
        with contextlib.closing(sqlite3.connect(self.db)) as db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute('SELECT * FROM book_moves WHERE job_id=? ORDER BY generation', (job_id,))]

    def journal_move(self, item, record, state, target):
        """A rules move of the book in the app's own journal, left in state (Senua M1: 'rename_intent' is the OS rename done,
        its commit not: the record still names the old path)."""
        import book_move
        now = book_move.stamp()
        with contextlib.closing(sqlite3.connect(self.db)) as db, db:
            db.execute('INSERT INTO book_moves(move_id,job_id,kind,candidate_id,generation,state,strategy,target_folder,target_root,target_path,'
                       'from_json,final_json,temp_path,cause,detail,progress,override_id,created_utc,updated_utc,origin)'
                       ' VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL,NULL,?,?,?)',
                       (str(uuid.uuid4()), item['job_id'], 'base', item['candidate_id'], 1, state, 'rename', str(target.parent),
                        str(self.sorted), str(target), json.dumps(book_move.location(record)), now, now, 'rules'))

    def replacement(self, parent, child):
        """A replacement link (replacement_jobs' table): child, a newer conversion, replaces parent."""
        with contextlib.closing(sqlite3.connect(self.db)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS audiobook_replacements(id TEXT PRIMARY KEY,parent_job_id TEXT UNIQUE NOT NULL,'
                       'replacement_job_id TEXT UNIQUE NOT NULL,candidate_id TEXT UNIQUE NOT NULL,candidate_revision INTEGER NOT NULL,'
                       'parent_record_sha256 TEXT NOT NULL,previous_publication_json TEXT NOT NULL,approval_json TEXT NOT NULL,'
                       "state TEXT NOT NULL,current_output_json TEXT NOT NULL DEFAULT '',failure_json TEXT NOT NULL DEFAULT '',"
                       'created TEXT NOT NULL,updated TEXT NOT NULL)')
            db.execute("INSERT INTO audiobook_replacements(id,parent_job_id,replacement_job_id,candidate_id,candidate_revision,"
                       "parent_record_sha256,previous_publication_json,approval_json,state,created,updated) VALUES(?,?,?,?,1,?,'{}','{}','completed',?,?)",
                       (str(uuid.uuid4()), parent, child, str(uuid.uuid4()), 'c' * 64, '2026-11-24', '2026-11-24'))

    def test_22_books_moved_into_series_folders_and_one_into_a_sibling_folder_clear_themselves(self):
        # Sergei's NAS on 2026-11-24, as a fixture: 22 books moved by hand from Сборники\ into series folders one level
        # down, and one into the sibling folder Warhammer 40K\. Each was flagged by the check before 0.31.1.
        books = []
        for index in range(23):
            data = ('Сборник %02d ' % index).encode('utf-8') * (40 + index)
            item, record = self.book('Сборники', 'Сборник %02d - Автор.m4b' % index, data)
            books.append((item, record))
        for index, (item, record) in enumerate(books):
            old = Path(record['final_path'])
            target = self.sorted / 'Warhammer 40K' if index == 22 else old.parent / ('Серия %d' % (index % 5))
            target.mkdir(exist_ok=True)
            os.replace(old, target / old.name)  # the same volume: Explorer's move keeps the file ID
        with patch('merge_service.verify_digest', wraps=__import__('merge_service').verify_digest) as hashed:
            self.check()
        self.assertEqual(hashed.call_count, 23, 'one full hash per book: only the one candidate of each name')
        for index, (item, record) in enumerate(books):
            row = self.row(item['job_id'])
            self.assertEqual((row['state'], row['reason']), ('completed', ''), index)
            moves = self.moves(item['job_id'])
            self.assertEqual([(m['origin'], m['state'], m['strategy']) for m in moves], [('found', 'complete', 'found')])
            now = json.loads(moves[0]['final_json'])['final_path']
            self.assertEqual(Path(now).parent.name, 'Warhammer 40K' if index == 22 else 'Серия %d' % (index % 5))
            # Every later step uses the new place: the bindings resolve it, and the next check needs no hash.
            effective, _ = self.service.publication_bindings.current(record)
            self.assertEqual(effective['final_path'], now)
            self.assertTrue(self.service._identity_current(dict(record)), 'remembered as after a full check')
        self.assertEqual(self.service.relinked_view()['count'], 23)
        self.assertIn('found again after a move outside the app', self.log.getvalue())

    def test_a_finished_book_that_is_gone_is_removed_from_the_records_and_no_file_is_touched(self):
        # Sergei 2026-11-24: "I don't want the book that I deleted from the Approved Books to be anywhere in the app."
        import finished_removal
        flagged, record = self.book('Author', 'Lost.m4b', b'lost book bytes' * 50)
        quiet, gone = self.book('Author', 'Gone.m4b', b'gone book bytes' * 50, flagged=False)
        kept, _ = self.book('Author', 'Kept.m4b', b'kept book bytes' * 50, flagged=False)
        for path in (record['final_path'], gone['final_path']):
            os.unlink(path)  # Sergei deletes them in Explorer
        before = self.files()
        self.check()
        self.assertEqual(self.files(), before, 'no file is touched')
        for item in (flagged, quiet):
            self.assertEqual(self.row(item['job_id'])['state'], 'removed')
            self.assertEqual(json.loads(self.row(item['job_id'])['output']), json.loads(self.queue._rows('SELECT output FROM audio_jobs WHERE job_id=?', (item['job_id'],))[0]['output']), 'the receipt stays')
        self.assertEqual(self.state(kept['job_id']), ('completed', ''))
        self.assertEqual([job['job_id'] for job in self.queue.status()['jobs']], [kept['job_id']], 'in no list and no count')
        with contextlib.closing(sqlite3.connect(self.db)) as db:
            db.row_factory = sqlite3.Row
            self.assertEqual(finished_removal.removed_candidates(db), {flagged['candidate_id'], quiet['candidate_id']})
            self.assertEqual({r['recorded_path'] for r in db.execute('SELECT * FROM finished_book_removals')}, {record['final_path'], gone['final_path']})
        self.assertEqual(self.service.removed_view()['count'], 2); self.assertFalse(self.service.removal_refused())
        self.assertEqual(self.log.getvalue().count('Finished book removed from the list (not found; library and source files untouched)'), 2, 'one normal-level line per book')
        self.assertEqual(self.row(flagged['job_id'])['reason'], finished_removal.REASON)
        self.assertEqual(finished_removal.REASON, 'Finished book not found; removed from the list. Library and source files were not touched.'
                         " The app's own recovery copies and working files for it are deleted later.", "Judy's spec, 8.2")
        # It never comes back: the file returning at its place changes nothing, and the check never looks at it again.
        Path(gone['final_path']).write_bytes(b'gone book bytes' * 50)
        self.again()
        self.assertEqual(self.row(quiet['job_id'])['state'], 'removed')

    def test_a_name_alone_is_never_enough(self):
        # A copy (same name, size and bytes, another file ID) in another folder, and a recorded ID that is absent: refused.
        item, record = self.book('Author', 'Copied.m4b', b'copied bytes' * 80, flagged=False)
        old = Path(record['final_path']); copy_folder = self.sorted / 'Elsewhere'; copy_folder.mkdir()
        (copy_folder / old.name).write_bytes(old.read_bytes()); old.unlink()
        self.check()
        self.assertEqual(self.moves(item['job_id']), [])
        self.assertEqual(self.row(item['job_id'])['state'], 'completed')
        unknown, other = self.book('Author', 'Unknown.m4b', b'never verified' * 80, flagged=False)
        with contextlib.closing(sqlite3.connect(self.db)) as db, db:
            db.execute('DELETE FROM verified_outputs WHERE job_id=?', (unknown['job_id'],))
        moved = self.sorted / 'Moved'; moved.mkdir(); os.replace(other['final_path'], moved / 'Unknown.m4b')
        # Moved after the pass's listing was taken: the removal lists again first, so a book moved meanwhile is never removed.
        self.check()
        self.assertEqual(self.row(unknown['job_id'])['state'], 'completed', 'a file of its name elsewhere: the book stays')
        self.service._relink_index = None
        self.assertFalse(self.service._relink_found(dict(other)), 'no file ID recorded: never relinked by its name, never removed')
        self.assertIn('no file ID was recorded', self.log.getvalue())

    def test_a_changed_book_at_its_place_is_not_flagged_and_not_searched_for(self):
        item, record = self.book('Author', 'Changed.m4b', b'original bytes' * 60, flagged=False)
        time.sleep(.05); Path(record['final_path']).write_bytes(b'changed bytes!' * 60)
        with patch.object(self.service, '_output_files', side_effect=AssertionError('searched for a book that is there')):
            self.check()
        self.assertEqual((self.row(item['job_id'])['state'], self.row(item['job_id'])['reason']), ('completed', ''))

    def test_recycle_bins_and_hidden_folders_are_never_searched(self):
        item, record = self.book('Author', 'Deleted.m4b', b'deleted bytes' * 70, flagged=False)
        self.book('Author', 'Other.m4b', b'other bytes' * 70, flagged=False)
        old = Path(record['final_path']); recycle = self.sorted / '#recycle' / 'Author'; recycle.mkdir(parents=True)
        os.replace(old, recycle / old.name)  # a NAS recycle bin keeps the file ID: still never "found"
        self.check()
        self.assertEqual(self.moves(item['job_id']), [])
        self.assertEqual(self.row(item['job_id'])['state'], 'removed', 'deleted into the recycle bin: gone')
        self.assertTrue((recycle / old.name).exists(), 'the recycle bin is not touched')

    def test_the_status_line_count_restarts_after_ten_quiet_minutes(self):
        import merge_service
        books = [self.book('Series', 'Book %d.m4b' % index, b'book %d ' % index * 90, flagged=False) for index in range(3)]
        for item, record in books[:2]:
            os.replace(record['final_path'], self.sorted / Path(record['final_path']).name)
        self.check()
        view = self.service.relinked_view()
        self.assertEqual(view['count'], 2); self.assertLess(view['last_age_ms'], 60000)
        self.service._relinked_last -= merge_service.RELINK_SHOW_MS / 1000
        self.assertEqual(self.service.relinked_view()['count'], 0, 'after 10 quiet minutes the part goes')
        self.service._relink_index = None
        item, record = books[2]
        os.replace(record['final_path'], self.sorted / Path(record['final_path']).name)
        self.assertTrue(self.service._relink_found(dict(record)))
        self.assertEqual(self.service.relinked_view()['count'], 0, "Judy's spec, 8.1: counted when its pass finishes")
        self.service._relink_pass_done()
        view = self.service.relinked_view()
        self.assertEqual(view['count'], 1, 'a new burst counts from 1')
        self.assertLess(view['last_age_ms'], 60000, 'its time starts when the pass finishes')

    def test_an_unreachable_output_folder_removes_nothing_and_the_page_says_so(self):
        # A NAS that is away, asleep or not mounted looks exactly like a thousand missing books (Judy's spec, 8.3).
        item, record = self.book('Author', 'Away.m4b', b'away bytes' * 60, flagged=False)
        self.book('Author', 'Stays.m4b', b'stays bytes' * 60, flagged=False)
        os.unlink(record['final_path'])
        away = self.sorted.with_name('Sorted-offline'); self.sorted.rename(away)  # the drive is gone
        self.check()
        self.assertEqual(self.row(item['job_id'])['state'], 'completed', 'nothing removed')
        self.assertTrue(self.service.removal_refused())
        self.assertIn('Missing finished books were not removed', self.log.getvalue())
        away.rename(self.sorted)  # the drive is back
        self.again()
        self.assertEqual(self.row(item['job_id'])['state'], 'removed', 'removed at the next pass that proves it')
        self.assertFalse(self.service.removal_refused(), 'the line goes at the first normal pass')

    def test_an_output_folder_that_answers_empty_is_a_failed_mount(self):
        item, record = self.book('Author', 'Only.m4b', b'only bytes' * 60, flagged=False)
        os.unlink(record['final_path']); Path(record['final_path']).parent.rmdir()  # the root lists nothing
        self.check()
        self.assertEqual(self.row(item['job_id'])['state'], 'completed')
        self.assertTrue(self.service.removal_refused())

    def test_a_folder_that_cannot_be_listed_makes_the_pass_remove_nothing(self):
        import merge_service
        item, record = self.book('Author', 'Gone.m4b', b'gone bytes' * 60, flagged=False)
        self.book('Locked', 'Other.m4b', b'other bytes' * 60, flagged=False)
        os.unlink(record['final_path'])
        locked = str(self.sorted / 'Locked'); real = os.scandir
        def scandir(path='.'):
            if os.path.normcase(str(path)) == os.path.normcase(locked):raise PermissionError(13, 'Access is denied', str(path))
            return real(path)
        with patch.object(merge_service.os, 'scandir', side_effect=scandir):
            self.check()
        self.assertEqual(self.row(item['job_id'])['state'], 'completed', 'an incomplete search proves nothing')
        self.assertTrue(self.service.removal_refused())
        self.assertIn('could not be listed', self.log.getvalue())
        self.again()
        self.assertEqual(self.row(item['job_id'])['state'], 'removed', 'removed once every folder answers')

    def test_many_missing_at_once_removes_none(self):
        books = [self.book('Many', 'Book %02d.m4b' % index, b'book %d ' % index * 60, flagged=False) for index in range(13)]
        for item, record in books[:11]:
            os.unlink(record['final_path'])
        self.check()
        self.assertEqual([self.row(item['job_id'])['state'] for item, _ in books], ['completed'] * 13, 'more than ten missing: none removed')
        self.assertTrue(self.service.removal_refused())
        self.assertIn('11 of 13 finished books are missing at once', self.log.getvalue())
        # Futaba's QA, minor 3: the passes that retry them, 20 s apart, say nothing new; the line is logged once.
        self.queue._published_retry_at.clear(); self.check(); self.queue._published_retry_at.clear(); self.check()
        self.assertTrue(self.service.removal_refused())
        self.assertEqual(self.log.getvalue().count('Missing finished books were not removed'), 1, 'once per change, not per pass')

    def test_most_of_a_small_library_missing_removes_none(self):
        books = [self.book('Few', 'Book %d.m4b' % index, b'few %d ' % index * 60, flagged=False) for index in range(4)]
        for item, record in books[:3]:
            os.unlink(record['final_path'])
        self.check()
        self.assertEqual([self.row(item['job_id'])['state'] for item, _ in books], ['completed'] * 4, 'three of four: none removed')
        self.assertTrue(self.service.removal_refused())

    def test_a_book_moved_in_the_same_pass_is_found_and_one_gone_is_removed(self):
        moved, record = self.book('Series', 'Moved.m4b', b'moved bytes' * 60, flagged=False)
        gone, lost = self.book('Series', 'Gone.m4b', b'gone bytes' * 60, flagged=False)
        self.book('Series', 'Stays.m4b', b'stays bytes' * 60, flagged=False)
        target = self.sorted / 'Series' / 'Book 1'; target.mkdir(); os.replace(record['final_path'], target / 'Moved.m4b')
        os.unlink(lost['final_path'])
        self.check()
        self.assertEqual(self.state(moved['job_id']), ('completed', ''))
        self.assertEqual(self.row(gone['job_id'])['state'], 'removed')
        self.assertEqual((self.service.relinked_view()['count'], self.service.removed_view()['count']), (1, 1))

    def test_a_book_a_start_finds_missing_is_removed_by_the_next_background_pass(self):
        # Judy's 8.5 (amended): confirmed books are not checked again mid-session; a Start checks them all, finds moved books
        # itself and hands a missing one to the next background pass, which removes it at its end.
        item, record = self.book('Author', 'Later.m4b', b'later bytes' * 60, flagged=False)
        self.book('Author', 'Stays.m4b', b'stays bytes' * 60, flagged=False)
        self.check()  # the launch pass confirms both
        self.assertIn(item['job_id'], self.queue._published_seen)
        os.unlink(record['final_path'])  # deleted mid-session
        self.again()
        self.assertEqual(self.state(item['job_id']), ('completed', ''), 'mid-session nothing changes')
        self.assertIsNone(self.queue._settle(self.row(item['job_id']), True), "a Start's check removes nothing itself")
        self.assertNotIn(item['job_id'], self.queue._published_seen)
        self.again()
        self.assertEqual(self.row(item['job_id'])['state'], 'removed', 'the next background pass removes it')

    def test_a_book_renamed_by_hand_is_found_by_its_file_id_0_31_1(self):
        # Sergei 2026-11-24 (Senua M2): a book renamed by hand, in its folder or anywhere under the library root, is recognised
        # by its recorded file ID among the files of the same size, confirmed by the full hash, and relinked like a move.
        # Before, "Typo Titel.m4b" renamed to "Fixed Title.m4b" in its own folder was removed from the list.
        here, record = self.book('Series', 'Typo Titel.m4b', b'typo bytes' * 64, flagged=False)
        away, other = self.book('Series', 'Second.m4b', b'second bytes' * 64, flagged=False)
        same, _ = self.book('Series', 'Same Size.m4b', b'SAME bytes' * 64, flagged=False)  # the first's size, another file
        fixed = Path(record['final_path']).with_name('Fixed Title.m4b'); os.replace(record['final_path'], fixed)
        elsewhere = self.sorted / 'Other Series' / 'Renamed Too.m4b'; elsewhere.parent.mkdir(); os.replace(other['final_path'], elsewhere)
        self.check()
        for item, now in ((here, fixed), (away, elsewhere)):
            self.assertEqual(self.state(item['job_id']), ('completed', ''))
            moves = self.moves(item['job_id'])
            self.assertEqual([(m['origin'], m['state']) for m in moves], [('found', 'complete')])
            self.assertEqual(json.loads(moves[0]['final_json'])['final_path'], str(now))
            with contextlib.closing(sqlite3.connect(self.db)) as db:
                proof = json.loads(db.execute("SELECT proof_json FROM book_move_events WHERE move_id=? AND to_state='complete'", (moves[0]['move_id'],)).fetchone()[0])
            self.assertEqual(proof['found']['matched'], ['file_id', 'size', 'sha256'], 'not matched by its name')
        self.assertEqual((self.state(same['job_id']), self.moves(same['job_id'])), (('completed', ''), []), 'a file of the same size is never taken for it')
        self.assertEqual(self.service.relinked_view()['count'], 2)
        self.assertIn('found again after a rename outside the app', self.log.getvalue())

    def test_a_file_of_the_same_size_does_not_keep_a_gone_book_unless_nothing_can_tell_them_apart_0_31_1(self):
        gone, record = self.book('Series', 'Gone.m4b', b'gone bytes' * 64, flagged=False)
        other, _ = self.book('Series', 'Other.m4b', b'OTHR bytes' * 64, flagged=False)
        self.book('Series', 'Third.m4b', b'third bytes' * 70, flagged=False)
        os.unlink(record['final_path'])
        self.check()
        self.assertEqual(self.row(gone['job_id'])['state'], 'removed', 'its file ID is under no name: it is gone')
        self.assertEqual(self.state(other['job_id']), ('completed', ''))
        # No file ID recorded: a file of its size may be it under another name; never removed.
        unknown, lost = self.book('Series', 'Unknown.m4b', b'unkn bytes' * 64, flagged=False)
        with contextlib.closing(sqlite3.connect(self.db)) as db, db:
            db.execute('DELETE FROM verified_outputs WHERE job_id=?', (unknown['job_id'],))
        os.unlink(lost['final_path'])
        self.again()
        self.assertEqual(self.row(unknown['job_id'])['state'], 'completed')
        self.assertIn('a file of its name or size is elsewhere but no file ID was recorded', self.log.getvalue())

    def test_a_book_the_app_was_moving_is_never_looked_for_and_never_removed_0_31_1(self):
        # Senua M1: a rules move whose rename happened but whose commit did not ('rename_intent'): the file is under its new
        # name, the record still at the old one. The app's own journal says why: the book is left as it is.
        import finished_removal
        item, record = self.book('Series', 'Old Name.m4b', b'moving bytes' * 60, flagged=False)
        gone, lost = self.book('Series', 'Moving Gone.m4b', b'moving gone' * 60, flagged=False)
        self.book('Series', 'Stays.m4b', b'stays bytes' * 70, flagged=False)
        self.book('Series', 'Stays Too.m4b', b'stays two!' * 70, flagged=False)
        target = self.sorted / 'Series' / 'Book 1' / 'New Name.m4b'; target.parent.mkdir()
        self.journal_move(item, record, 'rename_intent', target); os.replace(record['final_path'], target)
        self.journal_move(gone, lost, 'copied', self.sorted / 'Series' / 'Book 2' / 'Moving Gone.m4b'); os.unlink(lost['final_path'])
        with patch.object(self.service, '_output_files', side_effect=AssertionError('searched for a book its own move holds')):
            self.check()
        for book in (item, gone):
            self.assertEqual(self.state(book['job_id']), ('completed', ''))
            self.assertEqual([m['origin'] for m in self.moves(book['job_id'])], ['rules'], 'no move of its own recorded')
        self.assertIn('left as it is: a move of it has not finished', self.log.getvalue())
        # Read again in the removal's own transaction: a move begun after the pass found the book missing holds it too.
        with contextlib.closing(sqlite3.connect(self.db)) as db, db:
            db.row_factory = sqlite3.Row
            self.assertFalse(finished_removal.remove(db, gone['job_id'], json.loads(self.row(gone['job_id'])['output']), lost['final_path'], {}))
        self.assertEqual(self.row(gone['job_id'])['state'], 'completed')

    def test_a_replaced_book_and_its_replacement_are_never_removed_0_31_1(self):
        # Senua M1 and Sergei 2026-11-24 ("also cover the replaced-book case"): both sides of a replacement share one candidate,
        # so a tombstone on either would hide the other; neither is removed, whichever file is gone.
        import finished_removal
        parent, old = self.book('Series', 'Replaced.m4b', b'replaced bytes' * 60, flagged=False)
        child, new = self.book('Series', 'Replacement.m4b', b'replacement b!' * 61, flagged=False)
        for _ in range(3):
            self.book('Series', 'Stays %s.m4b' % uuid.uuid4().hex[:6], os.urandom(500), flagged=False)
        self.replacement(parent['job_id'], child['job_id'])
        os.unlink(old['final_path']); os.unlink(new['final_path'])
        self.check()
        for book in (parent, child):
            self.assertEqual(self.state(book['job_id']), ('completed', ''))
        self.assertIn('left as it is: it is linked to a replacement', self.log.getvalue())
        with contextlib.closing(sqlite3.connect(self.db)) as db, db:
            db.row_factory = sqlite3.Row
            self.assertFalse(finished_removal.remove(db, parent['job_id'], json.loads(self.row(parent['job_id'])['output']), old['final_path'], {}))
            self.assertEqual(finished_removal.removed_candidates(db), set())

    def test_a_few_books_missing_after_the_launch_pass_are_weighed_against_every_finished_book_0_31_1(self):
        # Senua m1: after the launch pass only the unconfirmed books are looked at again. Three missing among them were "3 of 3
        # finished books checked": the brake refused every later pass of the session. The share is of all finished books.
        books = [self.book('Shelf', 'Book %d.m4b' % index, b'shelf %d ' % index * 60, flagged=False) for index in range(8)]
        self.check()  # the launch pass confirms them all
        for item, record in books[:3]:
            os.unlink(record['final_path'])
            self.assertIsNone(self.queue._settle(self.row(item['job_id']), True))  # a Start finds each missing
        self.again()
        self.assertEqual([self.row(item['job_id'])['state'] for item, _ in books], ['removed'] * 3 + ['completed'] * 5)
        self.assertFalse(self.service.removal_refused())

    def test_a_folder_that_stays_unlistable_is_listed_again_only_every_few_minutes_0_31_1(self):
        # Senua m2: an incomplete listing is reused like a complete one: one listing for every missing book of a pass, and
        # none for the passes that retry them seconds later.
        import merge_service
        books = [self.book('Author', 'Gone %d.m4b' % index, b'gone %d ' % index * 60, flagged=False) for index in range(2)]
        self.book('Locked', 'Other.m4b', b'other bytes' * 60, flagged=False)
        for _, record in books:
            os.unlink(record['final_path'])
        locked = str(self.sorted / 'Locked'); real = os.scandir; refused = []
        def scandir(path='.'):
            if os.path.normcase(str(path)) == os.path.normcase(locked):
                refused.append(path); raise PermissionError(13, 'Access is denied', str(path))
            return real(path)
        with patch.object(merge_service.os, 'scandir', side_effect=scandir):
            self.check()
            self.assertEqual(len(refused), 1, 'one listing for both missing books')
            self.queue._published_retry_at.clear(); self.check()
            self.assertEqual(len(refused), 1, 'the pass that retries them reuses it')
        self.assertEqual([self.row(item['job_id'])['state'] for item, _ in books], ['completed'] * 2)
        self.assertTrue(self.service.removal_refused())

    def test_a_retained_runs_book_is_left_alone_0_31_1(self):
        # Senua m4 (the Brief's 0.30.0 item A): a retained run's job, in Needs attention too, is never looked for, never
        # removed and never cleared by a background pass.
        item, record = self.book('Author', 'Held.m4b', b'held bytes' * 60)  # flagged before 0.31.1: 'needs attention'
        self.book('Author', 'Stays.m4b', b'stays bytes' * 70, flagged=False)
        os.unlink(record['final_path'])
        with patch('storage_relocation_native.retained_runtime', return_value=True), \
             patch('storage_relocation_native.retained_job', side_effect=lambda database, job_id: job_id == item['job_id']):
            with patch.object(self.service, '_output_files', side_effect=AssertionError('searched for a retained job')):
                self.check()
            self.assertEqual(self.state(item['job_id']), ('needs attention', FLAG), 'left exactly as it was')
            proof = {'missing': True, 'recorded': record['final_path']}
            self.assertEqual(self.service._remove_missing([(self.row(item['job_id']), record, proof)], [], 2), 0)
            self.assertFalse(self.service._relink_found(dict(record)))
        self.assertEqual(self.state(item['job_id']), ('needs attention', FLAG))
        self.assertIn('left as it is: a retained run keeps it', self.log.getvalue())

    def test_a_found_book_is_where_sergei_put_it_for_the_rules_and_its_row(self):
        import book_move
        import sorting_moves
        item, record = self.book('Author', 'Placed.m4b', b'placed bytes' * 70, flagged=False)
        target = self.sorted / 'His folder'; target.mkdir(); os.replace(record['final_path'], target / 'Placed.m4b')
        self.check()
        with contextlib.closing(sqlite3.connect(self.db)) as db:
            db.row_factory = sqlite3.Row
            self.assertEqual(sorting_moves._last_move(db, item['job_id']), (str(target / 'Placed.m4b'), False), 'never filed back by the rules')
            found = book_move.latest(db, [item['candidate_id']])[item['candidate_id']]
            self.assertIsNone(book_move.view(found), 'nothing on the row')
            relinked = book_move.relinks(db, [item['candidate_id']])[item['candidate_id']]
            self.assertEqual((relinked['was'], relinked['now']), (record['final_path'], str(target / 'Placed.m4b')))
            with self.assertRaisesRegex(ValueError, 'Unknown move origin'):
                book_move.plan(db, job_id=item['job_id'], kind='base', candidate_id=item['candidate_id'], start=record,
                               folder=str(self.sorted), root=str(self.sorted), origin='found')



class RemovedBookEverywhereTests(unittest.TestCase):
    """A real conversion into a Sorted folder outside the library (test_automatic_media's fixture), its file then deleted
    by hand: the published-book check removes it, and it is in no total and no list (Sergei 2026-11-24: "I don't want the
    book that I deleted from the Approved Books to be anywhere in the app"), its candidate never offered again."""
    from test_automatic_media import AutomaticMediaTests as _media, RewrittenBookTests as _rewritten
    setUp = _media.setUp; tearDown = _media.tearDown; result = _media.result; wait = _media.wait
    convert = _rewritten.convert; assert_ready = _rewritten.assert_ready; job = _rewritten.job

    def passed(self):
        """One published-book check pass, as the recovery sweep starts it after loading."""
        self.service.jobs.start_published_check(); self.service.jobs._verifier.join(60)
        self.assertFalse(self.service.jobs._verifier.is_alive())

    def test_a_removed_book_is_in_no_total_and_no_list(self):
        job_id = self.convert()
        final = Path(self.job()['output']['final_path'])
        self.assertTrue(final.is_file())
        # A series look-up waits for a later try for this book (a ledger row between tries).
        import series_backfill
        with contextlib.closing(sqlite3.connect(self.inv.database)) as db, db:
            db.execute(series_backfill.TABLE)
            db.execute("INSERT INTO series_backfill VALUES(?,'deferred','',?,'2026-11-24T00:00:00Z')", (job_id, json.dumps({'next_attempt': time.time() + 3600})))
        self.assertEqual(self.service.series_backfill.summary()['between_tries'], 1, 'positive control: counted while the book is listed')
        os.unlink(final)  # Sergei deletes the book in Explorer
        with patch('sys.stderr', io.StringIO()):
            self.service.jobs._published_seen.clear(); self.passed()
        self.assertEqual(self.service.jobs._rows('SELECT state FROM audio_jobs WHERE job_id=?', (job_id,))[0]['state'], 'removed')
        self.service.invalidate_status()
        status = self.service.state()
        self.assertEqual((status['converted_total'], status['approved_total'], status['candidate_total']), (0, 0, 0), 'in no total')
        for status_filter in ('all', 'approved', 'ready', 'review', 'converted', 'created', 'jobs', 'output_attention', 'held', 'changed'):
            self.assertEqual(self.service.reviews.page(status=status_filter)['total'], 0, status_filter)
        self.assertEqual(self.service.jobs.status()['jobs'], [], 'no job row is listed')
        self.assertEqual(self.service.series_backfill.summary()['between_tries'], 0, "Futaba's QA, minor 1: in no look-up count")
        # Judy's spec, 8.2: the job reason is a record text; it reaches no list or panel on the page.
        import finished_removal
        self.assertEqual(self.service.jobs._rows('SELECT reason FROM audio_jobs WHERE job_id=?', (job_id,))[0]['reason'], finished_removal.REASON)
        seen = [json.dumps(status, default=str, ensure_ascii=False)]
        seen += [json.dumps(self.service.reviews.page(status=name), default=str, ensure_ascii=False) for name in
                 ('all', 'approved', 'ready', 'review', 'converted', 'created', 'jobs', 'output_attention', 'held', 'changed')]
        seen.append(json.dumps(self.service.kept_files(), default=str, ensure_ascii=False))
        self.assertFalse([text for text in seen if 'Finished book not found' in text], 'the job reason is on no page list')
        self.assertEqual(self.service.removed_view()['count'], 1)
        with patch('sys.stderr', io.StringIO()):
            self.service.jobs._published_seen.clear(); self.service.jobs._published_retry_at.clear(); self.passed()
        self.assertEqual(self.service.jobs._rows('SELECT count(*) AS n FROM audio_jobs')[0]['n'], 1, 'never converted again')


class MissingBookStaysListedTests(unittest.TestCase):
    """Futaba's 0.31.1 QA, minor 3: a refused removal changes nothing. A finished book whose file is not where the app has it
    (deleted while the library drive is away: the removal is refused) stays in its lists and totals, unchanged, until it
    is removed; then it leaves them."""
    from test_automatic_media import AutomaticMediaTests as _media, RewrittenBookTests as _rewritten
    setUp = _media.setUp; tearDown = _media.tearDown; result = _media.result; wait = _media.wait
    convert = _rewritten.convert; assert_ready = _rewritten.assert_ready; job = _rewritten.job
    passed = RemovedBookEverywhereTests.passed

    def listed(self):
        self.service.invalidate_status()
        status = self.service.state()
        return status['converted_total'], self.service.reviews.page(status='converted')['total']

    def test_a_book_held_by_a_refused_removal_stays_where_it_was(self):
        job_id = self.convert()
        final = Path(self.job()['output']['final_path'])
        self.assertEqual(self.listed(), (1, 1), 'positive control: converted and listed')
        os.unlink(final)  # Sergei deletes it, and then the library drive goes away
        away = self.sorted.with_name('S-away'); self.sorted.rename(away)
        with patch('sys.stderr', io.StringIO()):
            self.service.jobs._published_seen.clear(); self.passed()
        self.assertTrue(self.service.removal_refused(), 'positive control: the removal was refused')
        self.assertEqual(self.service.jobs._rows('SELECT state FROM audio_jobs WHERE job_id=?', (job_id,))[0]['state'], 'completed')
        self.assertEqual(self.listed(), (1, 1), 'a refusal changes nothing: still converted and listed')
        away.rename(self.sorted)  # the drive is back: the next pass removes it
        with patch('sys.stderr', io.StringIO()):
            self.service.jobs._published_retry_at.clear(); self.service._relink_index = None; self.passed()
        self.assertEqual(self.service.jobs._rows('SELECT state FROM audio_jobs WHERE job_id=?', (job_id,))[0]['state'], 'removed')
        self.assertEqual(self.listed(), (0, 0), 'removed: in no list and no total')


class StartFindsMovedBooksTests(unittest.TestCase):
    """Futaba's 0.31.1 QA, Major 2 (pattern PA-1: a behaviour tested below the real press): a finished book moved by hand
    while the app runs is found at Start. Driven through the page's own press, POST /api/audiobook/resume, on a real
    engine's MergeService, its real recovery sweep and its real background published-book check. Before, a Start ran no
    finished-book check and only a relaunch found the book."""
    from test_automatic_media import AutomaticMediaTests as _media, RewrittenBookTests as _rewritten
    setUp = _media.setUp; tearDown = _media.tearDown; result = _media.result; wait = _media.wait
    convert = _rewritten.convert; assert_ready = _rewritten.assert_ready; job = _rewritten.job
    passed = RemovedBookEverywhereTests.passed

    def press(self, path):
        """The page's POST, through the engine's own HTTP handler and its control gate (test_merge_http's harness)."""
        import threading
        from email.message import Message
        from web_server import BrowserServer, Handler
        server = BrowserServer.__new__(BrowserServer)
        server.inventory = self.inv; server.server_address = ('127.0.0.1', 5211); server.server_port = 5211
        server.token = 'fixture-token'; server.instance = 'fixture'; server.active_library = None
        server.loaded_version = 'fixture'; server.restart_context = None; server.recovery_operations = 0
        server.closing = False; server.control_lock = threading.Lock(); server.control_condition = threading.Condition(server.control_lock)
        server.merge_admissions = 0; server.merge = self.service
        handler = Handler.__new__(Handler); handler.server = server; handler.path = path
        handler.headers = Message(); handler.headers['Host'] = '127.0.0.1:5211'; handler.headers['X-Books-Token'] = server.token
        payload = b'{}'; handler.headers['Content-Type'] = 'application/json'; handler.headers['Content-Length'] = str(len(payload))
        handler.rfile = io.BytesIO(payload); handler.result = None
        handler.response = lambda status, body, content_type='application/json': setattr(handler, 'result', (status, body))
        handler.do_POST()
        return handler.result

    def test_resume_audiobook_jobs_finds_a_book_moved_while_the_app_runs(self):
        job_id = self.convert()
        output = self.job()['output']; final = Path(output['final_path'])
        with patch('sys.stderr', io.StringIO()):
            self.passed()  # the launch pass confirms it
            moved = final.parent / 'Moved by hand'; moved.mkdir(); os.replace(final, moved / final.name)
            self.service.jobs._published_retry_at.clear(); self.passed()
            self.assertEqual(self.service.relinked_view()['count'], 0, 'positive control: mid-session nothing looks at it again')
            import contextlib as context
            self.service.start_retention(context.nullcontext)  # the engine's sweep, as after loading
            status, answer = self.press('/api/audiobook/resume')
            self.assertEqual(status, 200, answer)
            deadline = time.monotonic() + 150
            while self.service.relinked_view()['count'] != 1:
                self.assertLess(time.monotonic(), deadline, 'Start never found the moved book')
                time.sleep(.25)
        effective, _ = self.service.publication_bindings.current(output)
        self.assertEqual(effective['final_path'], str(moved / final.name))
        self.assertEqual(self.service.jobs._rows('SELECT state FROM audio_jobs WHERE job_id=?', (job_id,))[0]['state'], 'completed')


if __name__ == '__main__':
    unittest.main()
