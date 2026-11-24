"""0.31.1 (Sergei 2026-11-24): a book the app delivered into Audiobooks Sorted is done. The published-book check no longer puts
a finished book in Needs attention; a book moved by hand is found again (same name, file ID, size and full hash) and its new
place recorded as a completed move of origin 'found'. A name alone is never enough. Private fixture libraries only."""
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

    def test_a_finished_book_that_cannot_be_found_is_never_flagged(self):
        flagged, record = self.book('Author', 'Lost.m4b', b'lost book bytes' * 50)
        quiet, gone = self.book('Author', 'Gone.m4b', b'gone book bytes' * 50, flagged=False)
        for path in (record['final_path'], gone['final_path']):
            os.unlink(path)
        self.check()
        self.assertEqual((self.row(flagged['job_id'])['state'], self.row(flagged['job_id'])['reason']), ('completed', ''), 'the old flag is taken back')
        self.assertEqual((self.row(quiet['job_id'])['state'], self.row(quiet['job_id'])['reason']), ('completed', ''), 'no new flag')
        self.assertEqual(self.moves(flagged['job_id']), [])
        self.assertEqual(self.log.getvalue().count('not at its recorded path and not found again'), 2, 'one log line per book')
        self.assertEqual(self.service.relinked_view(), {'count': 0, 'last_age_ms': None})

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
        self.assertFalse(self.service._relink_found(dict(other)), 'no file ID recorded: never relinked by its name')
        self.assertIn('no file ID recorded', self.log.getvalue())

    def test_a_changed_book_at_its_place_is_not_flagged_and_not_searched_for(self):
        item, record = self.book('Author', 'Changed.m4b', b'original bytes' * 60, flagged=False)
        time.sleep(.05); Path(record['final_path']).write_bytes(b'changed bytes!' * 60)
        with patch.object(self.service, '_output_files', side_effect=AssertionError('searched for a book that is there')):
            self.check()
        self.assertEqual((self.row(item['job_id'])['state'], self.row(item['job_id'])['reason']), ('completed', ''))

    def test_recycle_bins_and_hidden_folders_are_never_searched(self):
        item, record = self.book('Author', 'Deleted.m4b', b'deleted bytes' * 70, flagged=False)
        old = Path(record['final_path']); recycle = self.sorted / '#recycle' / 'Author'; recycle.mkdir(parents=True)
        os.replace(old, recycle / old.name)  # a NAS recycle bin keeps the file ID: still never "found"
        self.check()
        self.assertEqual(self.moves(item['job_id']), [])
        self.assertEqual(self.row(item['job_id'])['state'], 'completed')

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


if __name__ == '__main__':
    unittest.main()
