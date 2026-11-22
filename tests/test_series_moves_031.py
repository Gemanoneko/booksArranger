"""0.31.0 step 4d (Sergei 2026-11-22; Judy's BooksArranger_0.31.0_UX.md, section 3 and Notes for Ender): what a page control
needs to list and approve the pending series moves, beside the 0.30.0 plan and its approval, which already answer a page
(POST /api/sorting-moves and /api/sorting-moves/apply). Per book: its id, title, author, the paths as shown under Audiobooks
Sorted, a reason key for a book left where it is, the answer of an approval as a code, and a book whose approved move could
not run listed again. Harry Potter 7 from the 0.30.0 diagnosis; a private Sorted folder of empty files; nothing moves."""
import contextlib
import hashlib
import json
import sqlite3

import series_backfill
import sorting_moves
from test_sorting_030 import GateTests, SortedCatalog

HP7 = 'J. K. Rowling\\Harry Potter and the Deathly Hallows - J. K. Rowling.m4b'
HP7_TO = 'Rowling J. K\\Harry Potter\\Harry Potter - 7 - Harry Potter and the Deathly Hallows - Rowling J. K.m4b'


class ListTests(SortedCatalog):
    def test_each_listed_book_carries_what_the_page_shows(self):
        job = self.harry_potter_7()
        found = self.plan()
        item = next(i for i in found['items'] if i['job_id'] == job)
        self.assertEqual({key: item[key] for key in ('book_id', 'title', 'author', 'from_shown', 'to_shown', 'kept', 'approved_not_moved')},
                         {'book_id': 'book-1', 'title': 'Harry Potter and the Deathly Hallows', 'author': 'J. K. Rowling', 'from_shown': HP7, 'to_shown': HP7_TO,
                          'kept': False, 'approved_not_moved': None})
        self.assertEqual((item['from'], item['to']), (str(self.sorted / HP7), str(self.sorted / HP7_TO)), 'the whole paths, as before')
        self.assertEqual(item['series'], {'name': 'Harry Potter', 'number': '7', 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work3650'},
                         'the source name and address of "found on FantLab"')
        self.assertEqual(item['items'], ['series', 'author'], 'which kinds of move it is')

    def test_the_new_fields_do_not_change_the_digest_he_approves(self):
        self.harry_potter_7()
        found = self.plan()
        signed = [[i['job_id'], i['from'], i['to'], i['items']] for i in found['items']]
        expected = hashlib.sha256(json.dumps([sorting_moves.SCHEMA, str(self.sorted), signed], ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
        self.assertEqual(found['digest'], expected, 'a list seen before the update is the same list after it')
        self.assertEqual(found['schema'], 'books-sorting-moves-v1')

    def test_a_book_left_where_it_is_has_a_reason_key(self):
        stray = self.book('Elsewhere\\J. K. Rowling - Stray.m4b', 'J. K. Rowling', 'Stray Book')
        taken = self.book('Роулинг Джоан\\Taken - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Taken', language='Unknown')
        (self.sorted / 'Rowling J. K').mkdir()
        (self.sorted / 'Rowling J. K' / 'Taken - Rowling J. K.m4b').write_bytes(b'')
        gone = self.book('Роулинг Джоан\\Gone - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Gone', language='Unknown', create=False)
        legacy = self.book('Роулинг Джоан\\Legacy - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Legacy', language='Unknown', root=self.library)
        refused = {i['job_id']: i for i in self.plan()['refused']}
        self.assertEqual({job: refused[job]['refused_key'] for job in (stray, taken, gone, legacy)},
                         {stray: 'not_app_name', taken: 'name_exists', gone: 'not_where_recorded', legacy: 'not_in_sorted'})
        self.assertEqual((refused[taken]['title'], refused[taken]['book_id'], refused[taken]['from_shown'], refused[taken]['kept']),
                         ('Taken', 'book-2', 'Роулинг Джоан\\Taken - Роулинг Джоан.m4b', False))
        self.assertTrue(all(isinstance(item['refused'], str) for item in refused.values()), 'the sentence stays for the script and the dry-run list')

    def test_every_refusal_sentence_the_plan_can_give_has_its_key(self):
        sentences = {'A file with the new name is already there': 'name_exists', sorting_moves.SAME_TARGET: 'same_target',
                     'You chose its folder; left as it is': 'chosen_folder', 'Already moved to a folder you chose; left as it is': 'chosen_folder',
                     'Not in Audiobooks Sorted; left as it is': 'not_in_sorted', "Its name does not follow the app's naming; left as it is": 'not_app_name',
                     'The audiobook is not where the catalog says': 'not_where_recorded',
                     'The audiobook is not where its series update put it; left as it is': 'not_where_recorded',
                     'Part of a replacement or a newer version; left as it is': 'newer_version', 'Files kept at your choice; left as they are': 'kept_files',
                     sorting_moves.RETAINED: 'data_move', 'No name for it: unknown': 'no_name', 'Could not be planned: KeyError': 'no_name',
                     'Series sources need review: Qualified work identity relationship needs stronger evidence': 'sources_disagree',
                     'Something the app has no key for': 'other', '': 'other', None: 'other'}
        for sentence, key in sentences.items():
            with self.subTest(sentence=sentence):
                self.assertEqual(sorting_moves.reason_key(sentence), key)

    def two_books_one_target(self):
        first = self.book('Роулинг Джоан\\Twin - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Twin', language='Unknown')
        second = self.book('Джоан Роулинг\\Twin - Джоан Роулинг.m4b', 'Джоан Роулинг', 'Twin', language='Unknown')
        return first, second

    def test_two_listed_books_with_one_target_are_both_left_with_that_key(self):
        first, second = self.two_books_one_target()
        found = self.plan()
        self.assertEqual(found['items'], [])
        self.assertEqual({i['job_id']: i['refused_key'] for i in found['refused']}, {first: 'same_target', second: 'same_target'})


class ApprovedNotMovedTests(SortedCatalog):
    """Judy 3.3: an approved move never fails in silence. Today such a book dropped out of the plan."""

    def hold_approved(self, job, reason, approved_failed=True):
        record = {'series': 'Гарри Поттер', 'number': '7', 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work3650', 'move_approved': True,
                  'approved_found': {'name': 'Harry Potter', 'number': '7', 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work3650'},
                  'approved_target': str(self.sorted / HP7_TO)}
        if approved_failed:
            record['approved_failed'] = {'reason': reason, 'at': 'now'}
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute("UPDATE series_backfill SET state='held',reason=?,record=? WHERE job_id=?", (reason, json.dumps(record, ensure_ascii=False), job))
            db.commit()

    def test_a_book_whose_approved_move_could_not_run_is_listed_again_with_why(self):
        job = self.harry_potter_7()
        for reason, key in (('The book changed since you approved its move; nothing was changed', 'file_changed'),
                            ('The published audiobook changed since it was verified; left as it is', 'file_changed'),
                            ('The planned place changed since you approved it; look at the list again. Nothing was changed', 'place_changed'),
                            ('A file with the series name already exists: x.m4b', 'name_exists'), ('Series tags did not read back: album', 'other')):
            with self.subTest(reason=reason):
                self.hold_approved(job, reason)
                item = next(i for i in self.plan()['items'] if i['job_id'] == job)
                self.assertEqual(item['approved_not_moved'], {'key': key, 'reason': reason})
                self.assertEqual((item['to_shown'], item['series']['name']), (HP7_TO, 'Harry Potter'), 'approvable again, as it was')

    def test_before_this_its_series_move_dropped_out_of_the_list(self):
        # Positive control: the same hold without the record 0.31.0 writes is read as 0.30.0 read it. The series move is
        # gone from the plan; the book is listed only for its other move (its author folder), with no series and no word
        # that an approved move did not run.
        job = self.harry_potter_7()
        self.hold_approved(job, 'The book changed since you approved its move; nothing was changed', approved_failed=False)
        found = self.plan()
        item = next(i for i in found['items'] if i['job_id'] == job)
        self.assertEqual((item['items'], 'series' in item, item['approved_not_moved']), (['author'], False, None))
        self.assertNotIn('Harry Potter\\', item['to_shown'], 'no series folder is offered')

    def test_the_lookup_records_why_an_approved_move_was_held_and_a_new_approval_clears_it(self):
        from types import SimpleNamespace
        job = self.harry_potter_7()
        backfill = series_backfill.SeriesBackfill(SimpleNamespace(inventory=SimpleNamespace(database=self.database), stage_root=self.base / 'stage'),
                                                 research=SimpleNamespace(), clock=lambda: 1000.0)
        backfill.unsafe = lambda *_: ''
        backfill._set(job, 'held', series_backfill.MOVE_WAITS, backfill.entry(job)['record'])
        backfill.approve(job, {'name': 'Harry Potter', 'number': '7', 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work3650'}, str(self.sorted / HP7_TO))
        with contextlib.closing(sqlite3.connect(self.database)) as db:  # the book changes after his approval
            manifest = json.loads(db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?', (job,)).fetchone()[0])
            manifest['metadata']['narrator'] = 'changed'
            db.execute('UPDATE audio_jobs SET manifest=? WHERE job_id=?', (json.dumps(manifest, ensure_ascii=False), job))
            db.commit()
        backfill.run_pass()
        entry = backfill.entry(job)
        self.assertEqual((entry['state'], entry['reason']), ('held', 'The book changed since you approved its move; nothing was changed'))
        self.assertEqual(entry['record']['approved_failed']['reason'], entry['reason'])
        self.assertEqual(next(i for i in self.plan()['items'] if i['job_id'] == job)['approved_not_moved']['key'], 'file_changed')
        self.assertEqual(backfill.summary()['moves_waiting'], 1, 'it counts as a move waiting for him again')
        backfill.approve(job, {'name': 'Harry Potter', 'number': '7', 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work3650'}, str(self.sorted / HP7_TO))
        self.assertNotIn('approved_failed', backfill.entry(job)['record'])


class ApproveAnswerTests(GateTests):
    def test_each_book_answers_accepted_or_refused_with_a_reason_key(self):
        hp7 = self.harry_potter_7()
        taken = self.book('Роулинг Джоан\\Taken - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Taken', language='Unknown')
        (self.sorted / 'Rowling J. K').mkdir()
        (self.sorted / 'Rowling J. K' / 'Taken - Rowling J. K.m4b').write_bytes(b'')
        merge = self.merge([], [])
        seen = merge.sorting_moves()
        answer = merge.sorting_moves_apply(seen['digest'], [hp7, taken, 'no-such-job'])
        self.assertEqual({r['job_id']: (r['code'], r.get('reason_key')) for r in answer['results']},
                         {hp7: ('accepted', None), taken: ('refused', 'name_exists'), 'no-such-job': ('refused', 'not_listed')})
        self.assertEqual({r['job_id']: r['state'] for r in answer['results']}, {hp7: 'series_update_queued', taken: 'refused', 'no-such-job': 'not_listed'},
                         'the 0.30.0 state values are unchanged')

    def test_a_refusal_at_the_move_itself_has_a_code_too(self):
        hp2 = self.book('Роулинг Джоан\\Гарри Поттер и тайная комната - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Гарри Поттер и тайная комната', language='Unknown')
        merge = self.merge([], [])

        def refuse(job_id, target):
            raise ValueError('This audiobook has a newer version; it was not moved')
        merge._sorting_move = refuse
        answer = merge.sorting_moves_apply(merge.sorting_moves()['digest'])
        self.assertEqual([(r['job_id'], r['code'], r['reason_key']) for r in answer['results']], [(hp2, 'refused', 'other')])


del GateTests, SortedCatalog  # only their fixtures are reused; their own cases run in test_sorting_030

if __name__ == '__main__':
    import unittest
    unittest.main()
