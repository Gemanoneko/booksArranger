"""0.31.1 (Sergei 2026-11-24): a book the app delivered into Audiobooks Sorted is done. The published-book check no longer puts
a finished book in Needs attention; a book moved by hand is found again (same name, file ID, size and full hash) and its new
place recorded as a completed move of origin 'found'. A name alone is never enough. A finished book that is gone (no file of its
name anywhere under the output folder, its absence proven) is removed from the records: catalog only, no file touched, never
when the drive does not answer or too many are missing at once. Private fixture libraries only."""
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
        self.assertEqual(self.log.getvalue().count('Finished book removed from the list (not found; no files touched)'), 2, 'one normal-level line per book')
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
        self.assertEqual(self.service.relinked_view()['count'], 1, 'a new burst counts from 1')

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
        self.assertIn('11 of 13 finished books checked are missing at once', self.log.getvalue())

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
        self.assertEqual(self.service.removed_view()['count'], 1)
        with patch('sys.stderr', io.StringIO()):
            self.service.jobs._published_seen.clear(); self.service.jobs._published_retry_at.clear(); self.passed()
        self.assertEqual(self.service.jobs._rows('SELECT count(*) AS n FROM audio_jobs')[0]['n'], 1, 'never converted again')


if __name__ == '__main__':
    unittest.main()
