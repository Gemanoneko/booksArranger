"""0.31.0 step 1c (Sergei 2026-11-22): two books never share one destination.

The reported shape: his two Sprawl volumes, both planning "Gibson William\\Sprawl Trilogy - Gibson William.m4b", each row
showing that name free because only the disk was checked. Here: two rows planning one name, a row and a book waiting to
convert, and the cases that share a name by design (the book's own job, a set-aside job, a cleanup task, a replacement).
A private catalog with the three tables the check reads; the engine's own methods on a bare MergeService. No files."""
import contextlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import destination_clash
from merge_service import MergeService
from web_server import approve_code

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'destination-clash-tests'
SORTED = 'Z:\\Audiobooks Sorted'
SHARED = SORTED + '\\Gibson William\\Sprawl Trilogy - Gibson William.m4b'
GIBSON = 'Z:\\Audiobooks\\William Gibson\\'
COUNT_ZERO, MONA_LISA = GIBSON + 'Уильям Гибсон - 02-Граф Ноль.m4b', GIBSON + 'Уильям Гибсон - 03-Мона Лиза овердрайв.m4b'


def book(identity, path, revision=1):
    return {'id': identity, 'revision': revision, 'fingerprint': 'fp-' + identity, 'members': [{'path': path}]}


class ClashTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(temp.cleanup)
        self.database = Path(temp.name) / 'catalog.sqlite3'
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,superseded INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT,state TEXT,output TEXT,created TEXT)')
            db.execute('CREATE TABLE audio_job_set_aside(job_id TEXT PRIMARY KEY,candidate_id TEXT,revision INTEGER,kind TEXT,at TEXT)')
        self.count_zero, self.mona_lisa = book('count-zero', COUNT_ZERO), book('mona-lisa', MONA_LISA)
        for row in (self.count_zero, self.mona_lisa):
            self.current(row)
        self.service = MergeService.__new__(MergeService)
        self.service.inventory = SimpleNamespace(database=str(self.database))

    def current(self, row, superseded=0):
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            db.execute('INSERT OR REPLACE INTO book_groups VALUES(?,?,?,?)', (row['id'], row['revision'], row['fingerprint'], superseded))

    def job(self, job_id, candidate, destination=SHARED, state='pending', output=None, **manifest):
        value = dict({'candidate_id': candidate, 'destination': destination, 'metadata': {'title': 'Sprawl Trilogy', 'author': 'Gibson William'},
                      'sources': [{'path': MONA_LISA}]}, **manifest)
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?)', (job_id, json.dumps(value, ensure_ascii=False), state, output, job_id))

    def shared(self, row, path=SHARED):
        return self.service._destination_shared(row, path, path[len(SORTED) + 1:])

    def test_two_rows_planning_one_destination_are_both_held_and_name_each_other(self):
        names = {'title': 'Sprawl Trilogy', 'author': 'Gibson William'}
        self.assertIsNone(self.shared(self.count_zero), 'positive control: alone, the name is free')
        self.service._planned_note(self.count_zero, SHARED, names)
        self.assertIsNone(self.shared(self.count_zero), 'a row never clashes with itself')
        self.service._planned_note(self.mona_lisa, SHARED, names)
        first, second = self.shared(self.count_zero), self.shared(self.mona_lisa)
        self.assertEqual(first, {'kind': 'same_destination', 'detail': '', 'destination': 'Gibson William\\Sprawl Trilogy - Gibson William.m4b', 'absolute': SHARED, 'count': 1,
                                 'others': [{'book_id': 'mona-lisa', 'kind': 'row', 'name': '03-Мона Лиза овердрайв', 'title': 'Sprawl Trilogy', 'author': 'Gibson William'}]})
        self.assertEqual([(o['book_id'], o['kind'], o['name']) for o in second['others']], [('count-zero', 'row', '02-Граф Ноль')],
                         "the other book's own file name tells it apart; the titles are the same")
        self.assertNotEqual(first['kind'], 'piece', 'its own reason, never "Part of a bigger book"')

    def test_the_clash_ends_when_one_name_changes_or_the_other_row_is_no_longer_current(self):
        for row in (self.count_zero, self.mona_lisa):
            self.service._planned_note(row, SHARED)
        self.assertEqual(self.shared(self.count_zero)['count'], 1, 'positive control')
        self.service._planned_note(self.mona_lisa, SORTED + '\\Gibson William\\Sprawl Trilogy\\Sprawl Trilogy - 3 - Mona Lisa Overdrive - Gibson William.m4b')
        self.assertIsNone(self.shared(self.count_zero), 'the other row plans another name now')
        self.service._planned_note(self.mona_lisa, SHARED)
        self.current(dict(self.mona_lisa, revision=2))
        self.assertIsNone(self.shared(self.count_zero), 'a note for an older revision of the other row is not its plan')
        self.current(self.mona_lisa, superseded=1)
        self.assertIsNone(self.shared(self.count_zero), 'a regrouped row plans nothing')
        self.service._planned_note(self.mona_lisa, '')
        self.assertNotIn('mona-lisa', self.service._planned)

    def test_the_same_name_in_another_case_or_with_other_slashes_is_the_same_file(self):
        self.service._planned_note(self.mona_lisa, SHARED)
        self.assertEqual(self.shared(self.count_zero, SHARED.upper().replace('\\', '/').replace('Z:/', 'Z:\\'))['count'], 1)

    def test_a_book_waiting_to_convert_has_the_name_and_the_newcomer_is_held(self):
        self.job('job-mona', 'mona-lisa')
        found = self.shared(self.count_zero)
        self.assertEqual(found['others'], [{'book_id': 'mona-lisa', 'kind': 'queued', 'job_id': 'job-mona', 'name': '03-Мона Лиза овердрайв',
                                            'title': 'Sprawl Trilogy', 'author': 'Gibson William'}])
        self.assertIsNone(self.shared(self.mona_lisa), "the waiting book's own job is no other book")
        # A note for a book that has a job is not counted twice (the job is the one that holds the name).
        self.service._planned_note(self.mona_lisa, SHARED)
        self.assertEqual(self.shared(self.count_zero)['count'], 1)

    def test_a_stopped_job_still_holds_the_name_and_a_finished_or_set_aside_one_does_not(self):
        self.job('job-stopped', 'mona-lisa', state='needs attention')
        self.assertEqual(self.shared(self.count_zero)['others'][0]['job_id'], 'job-stopped')
        with contextlib.closing(sqlite3.connect(self.database)) as db, db:
            db.execute("INSERT INTO audio_job_set_aside VALUES('job-stopped','mona-lisa',1,'names','now')")
        self.assertIsNone(self.shared(self.count_zero), 'a job set aside will never run as planned')
        self.job('job-done', 'other-book', state='completed', output='{}')
        self.assertIsNone(self.shared(self.count_zero), 'a finished book is the disk check\'s ("Name taken"), as before')

    def test_jobs_that_share_a_name_by_design_never_hold_it(self):
        self.job('job-task', 'other-a', task_kind='duplicate_source_cleanup')
        self.job('job-replacement', 'other-b', replacement_id='r1')
        self.job('job-child', 'other-c', replacement_parent_job_id='job-parent')
        self.job('job-elsewhere', 'other-d', destination=SORTED + '\\Gibson William\\Neuromancer - Gibson William.m4b')
        self.assertIsNone(self.shared(self.count_zero))
        self.job('job-real', 'other-e')
        self.assertEqual([o['book_id'] for o in self.shared(self.count_zero)['others']], ['other-e'], 'positive control: a plain waiting book is found')

    def test_a_set_approved_as_one_book_is_never_blocked_by_its_own_pieces(self):
        # Judy's question (0.31.0 spec, G9): the two volumes as one row (the set "Approve as one book" is offered on), and an
        # older stopped job of one of its own files from before they were grouped. That job is a piece of this row.
        whole = {'id': 'the-set', 'revision': 1, 'fingerprint': 'fp-the-set', 'members': [{'path': COUNT_ZERO}, {'path': MONA_LISA}]}
        self.current(whole)
        self.job('job-own-piece', 'old-piece', state='needs attention')  # its source is MONA_LISA, a member of the set
        self.assertIsNone(self.shared(whole), 'its own piece never refuses the set')
        self.assertEqual(self.shared(self.count_zero)['others'][0]['job_id'], 'job-own-piece', 'positive control: for another row the same job holds the name')
        # A job that also converts a file outside the set is another book, and so is another row planning the name.
        self.job('job-other', 'other-book', sources=[{'path': MONA_LISA}, {'path': GIBSON + 'Elsewhere.m4b'}])
        self.assertEqual([o['job_id'] for o in self.shared(whole)['others']], ['job-other'])
        self.service._planned_note(book('stranger', GIBSON + 'copy\\Sprawl.m4b'), SHARED)
        self.current(book('stranger', GIBSON + 'copy\\Sprawl.m4b'))
        self.assertEqual(sorted(o['book_id'] for o in self.shared(whole)['others']), ['other-book', 'stranger'])

    def test_several_others_are_counted_and_the_waiting_book_comes_first(self):
        self.job('job-mona', 'mona-lisa')
        for n in range(12):
            row = book('row-%02d' % n, GIBSON + 'copy %02d\\Sprawl.m4b' % n)
            self.current(row); self.service._planned_note(row, SHARED)
        found = self.shared(self.count_zero)
        self.assertEqual((found['count'], len(found['others']), found['others'][0]['kind']), (13, destination_clash.LISTED, 'queued'))

    def test_an_unreadable_catalog_never_refuses_a_book(self):
        self.service.inventory = SimpleNamespace(database=str(self.database.parent / 'missing' / 'catalog.sqlite3'))
        self.assertIsNone(self.shared(self.count_zero))

    def test_the_refusal_has_its_own_reason_and_code(self):
        self.service._planned_note(self.mona_lisa, SHARED)
        error = destination_clash.Shared(self.shared(self.count_zero))
        self.assertIsInstance(error, ValueError, 'every existing Approve and automatic refusal path handles it')
        self.assertEqual(error.identity_hold['others'][0]['book_id'], 'mona-lisa')
        self.assertEqual(approve_code(str(error)), 'same_name')
        self.assertEqual(approve_code('An audiobook already exists at this path; nothing was overwritten'), 'name_taken', 'the disk check keeps its code')
        self.assertTrue(str(error).endswith('Nothing was changed.'))

    def test_a_row_that_asks_another_question_says_where_its_title_came_from(self):
        # 0.31.0 (Judy 4.5; R1): the Title line of a row that asks something else. The question carries the preview's own
        # title_origin, so the page knows the English title a source gave replaced the files' own title.
        english = {'origin': 'source', 'rule': 'english', 'split': False, 'provider': 'wikidata', 'source_url': 'https://www.wikidata.org/wiki/Q607112'}
        live = {'path': 'Gibson William\Count Zero - Gibson William.m4b', 'absolute': SHARED, 'taken': False, 'reason': '', 'title': 'Count Zero',
                'author': 'Gibson William', 'shared': None, 'title_origin': english}
        self.service.approval_preview = lambda *_, **__: dict(live)
        self.service._identity_lines = self.service._membership_lines = self.service._hold_payload = lambda *_: None
        asked = lambda entry: self.service.ask_payload(self.count_zero, dict({'reasons': ['x'], 'ask': None}, **entry))
        for entry in ({'group': 'author_unclear', 'ask': {'kind': 'author_unclear', 'why': ''}}, {'group': 'title_author', 'ask': {'kind': 'title_author', 'why': ''}},
                      {'group': 'part_of_book', 'hold': {'kind': 'piece', 'detail': 'x', 'piece': {'piece': 'siblings', 'count': 1}}}):
            payload = asked(entry)
            self.assertEqual(payload['title_origin'], english, entry['group'])
            self.assertEqual(payload['fields']['title']['proposal'], 'Count Zero', 'the title Approve files it under is the one the fact is about')
        payload['title_origin']['rule'] = 'changed'
        self.assertEqual(live['title_origin']['rule'], 'english', 'a copy: the preview is not changed through the row')
        # The files' own title: the fact says so, and the page shows no Title line for it.
        live['title_origin'] = {'origin': 'files', 'rule': 'no_english_title', 'split': False}
        self.assertEqual(asked({'group': 'title_author', 'ask': {'kind': 'title_author', 'why': ''}})['title_origin']['origin'], 'files')
        # Negative controls: a preview that says nothing adds nothing; a row with no preview (every file missing) has none.
        del live['title_origin']
        self.assertNotIn('title_origin', asked({'group': 'title_author', 'ask': {'kind': 'title_author', 'why': ''}}))
        live['title_origin'] = 'english'
        self.assertNotIn('title_origin', asked({'group': 'title_author', 'ask': {'kind': 'title_author', 'why': ''}}), 'never a value of another shape')

    def test_the_to_do_row_says_why_the_engine_itself_holds_it(self):
        # Judy's 0.31.0 spec 4.1 as amended (G9): destination.shared comes on every row whose name another book also has
        # (its kind reads same_destination on all of them), so the page needs the row's own hold to tell a row held for the
        # clash alone from a real piece of one book that is named after its set.
        self.service._planned_note(self.mona_lisa, SHARED, {'title': 'Sprawl Trilogy', 'author': 'Gibson William'})
        hold = self.shared(self.count_zero)
        live = {'path': 'Gibson William\\Sprawl Trilogy - Gibson William.m4b', 'absolute': SHARED, 'taken': False, 'reason': '', 'title': 'Sprawl Trilogy',
                'author': 'Gibson William', 'shared': hold}
        self.service.approval_preview = lambda *_, **__: dict(live)
        self.service._identity_lines = self.service._membership_lines = self.service._hold_payload = lambda *_: None
        asked = lambda entry: self.service.ask_payload(self.count_zero, dict({'reasons': ['x'], 'ask': None}, **entry))
        clash = asked({'group': 'name_taken', 'reasons': [destination_clash.REASON], 'hold': hold})
        self.assertEqual(clash['hold'], {'kind': 'same_destination', 'count': 1, 'others': hold['others']})
        self.assertEqual(clash['destination']['shared'], hold)
        piece = asked({'group': 'part_of_book', 'hold': {'kind': 'piece', 'detail': 'x', 'piece': {'piece': 'siblings', 'count': 1}}})
        self.assertEqual(piece['hold'], {'kind': 'piece'}, 'its own question: Part of a bigger book stays')
        self.assertEqual(piece['destination']['shared']['kind'], 'same_destination', 'positive control: the shared object reads the same on both')
        self.assertEqual(asked({'group': 'name_taken', 'reasons': ['An audiobook already exists at this path']})['hold'], {'kind': ''}, 'a file on disk: no hold of its own')
        self.assertEqual(asked({'group': 'title_author', 'ask': {'why': 'title_series'}})['hold'], {'kind': ''})
        # The live check names no other book any more (the other row changed its name): what was recorded still words the row.
        live['shared'] = None
        ended = asked({'group': 'name_taken', 'reasons': [destination_clash.REASON], 'hold': hold})
        self.assertIsNone(ended['destination']['shared'])
        self.assertEqual([other['name'] for other in ended['hold']['others']], ['03-Мона Лиза овердрайв'])

    def test_the_name_that_tells_a_book_apart(self):
        self.assertEqual(destination_clash.name_of([COUNT_ZERO]), '02-Граф Ноль')
        self.assertEqual(destination_clash.name_of(['Z:\\Audiobooks\\Misc\\1408.m4b']), '1408')
        self.assertEqual(destination_clash.name_of(['Z:\\Audiobooks\\King\\Оно (Клюквин)\\01.mp3', 'Z:\\Audiobooks\\King\\Оно (Клюквин)\\02.mp3']), 'Оно (Клюквин)')
        self.assertEqual(destination_clash.name_of([]), '')


if __name__ == '__main__':
    unittest.main()
