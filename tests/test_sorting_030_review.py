"""Senua's 0.30.0 review of the sorting moves (2026-11-19): M2 (a refused follow-up move stranded an approved series move),
M3 (sorting moves and their recovery in retained-runtime mode), m1 (trailing part numbers), m2 (author merges: initials in
another order; scoped and keep rules), m3 (two listed books with one target). Private catalogs and files in the test
scratch area; no library, no network."""
import contextlib
import json
import sqlite3
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import groups
from test_sorting_030 import SeriesFolderBackfillTests, SortedCatalog, m4b_row


class TrailingPartNumberTests(unittest.TestCase):
    """m1: only a one- or two-digit number set apart by a space or a separator is a part number."""

    def test_a_longer_number_is_part_of_the_title(self):
        for album, base in (('metro 2033', 'metro 2033'), ('book 1984', 'book 1984'), ('warhammer 40000', 'warhammer 40000'), ('1408', '1408'),
                            ("dale stewart 04 - darwin's blade 1", "dale stewart 04 - darwin's blade"), ('торадора! том 12', 'торадора! том'),
                            ('catch22', 'catch22')):
            with self.subTest(album=album):
                self.assertEqual(groups._without_part_number(album), base)

    def test_metro_2033_and_2034_stay_two_books(self):
        rows = [m4b_row('Glukhovsky/%s.m4b' % album, album=album, title=album, artist='Дмитрий Глуховский') for album in ('Metro 2033', 'Metro 2034')]
        built = groups.build(rows)
        self.assertEqual(len(built), 2, list(built))
        self.assertFalse(any(group.get('part_set') for group in built.values()))
        rows = [m4b_row("Darwin/Darwin's Blade %d.m4b" % n, album="Darwin's Blade %d" % n, title="Darwin's Blade %d" % n, artist='Дэн Симмонс') for n in (1, 2)]
        self.assertEqual(len(groups.build(rows)), 1, 'positive control: a real part number still joins')


def rules(*rows, known=()):
    import author_rules
    return author_rules.Rules([dict({'rule_id': 'r%d' % n, 'credit_key': author_rules.key(row[1]), 'credit_as_seen': row[1], 'target': row[2] if len(row) > 2 else '',
                                     'scope': row[3] if len(row) > 3 else '', 'options': '{}', 'actor': 'user', 'saved_utc': str(n)}, kind=row[0])
                               for n, row in enumerate(rows, 1)], known_authors=known)


class AuthorMergeTests(unittest.TestCase):
    """m2: the same words in the same order (surname first), never initials in another order; a scoped rule counts in its
    folder; a keep rule keeps the spelling as it is."""

    def test_initials_in_another_order_are_another_author(self):
        import canonical_names
        known = rules(known=['Parker J. K.'])
        self.assertFalse(canonical_names.same_author('K. J. Parker', 'Parker J. K.', known))
        self.assertEqual(canonical_names.author('K. J. Parker', known)[0], 'Parker K. J.', 'surname first, its own initials, not the J. K. folder')
        self.assertEqual(canonical_names.author('J. K. Parker', known)[0], 'Parker J. K.', 'positive control: the same initials in the same order merge')
        self.assertTrue(canonical_names.same_author('J. K. Rowling', 'Rowling J. K.', None))
        self.assertTrue(canonical_names.same_author('Tove Jansson', 'Jansson Tove', None), 'full words in either order are still one name')

    def test_a_scoped_rule_counts_in_its_folder_only(self):
        import canonical_names
        scoped = rules(('same_as', 'Anon Writer', 'Real Writer', 'Тёмная серия'))
        self.assertEqual(canonical_names.author('Anon Writer', scoped, 'Z:\\Audiobooks\\Тёмная серия\\Книга 1')[0], 'Real Writer')
        self.assertEqual(canonical_names.author('Anon Writer', scoped, 'Z:\\Audiobooks\\Другое')[0], 'Anon Writer')

    def test_a_kept_latin_spelling_stays_as_it_is(self):
        import canonical_names
        self.assertEqual(canonical_names.author('Stephen King', rules(('keep', 'Stephen King'), known=['King Stephen']))[0], 'Stephen King',
                         'his kept spelling, even with "King Stephen" in the library')
        self.assertEqual(canonical_names.author('Stephen King', None)[0], 'King Stephen', 'positive control: without the rule, surname first')


class PlanReviewTests(SortedCatalog):
    def test_m3_two_listed_books_with_one_target_are_both_left_as_they_are(self):
        first = self.book('J. K. Rowling\\Same Book - J. K. Rowling.m4b', 'J. K. Rowling', 'Same Book')
        second = self.book('Роулинг Джоан\\Same Book - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Same Book', language='Unknown')
        found = self.plan()
        self.assertEqual(found['items'], [])
        self.assertEqual({i['job_id']: i['refused'] for i in found['refused']},
                         {first: 'Another listed book would get the same name; left as it is', second: 'Another listed book would get the same name; left as it is'})

    def test_m2_the_plan_reads_a_scoped_rule_in_the_books_own_folder(self):
        import author_rules
        job = self.book('Anon Writer\\Night - Anon Writer.m4b', 'Anon Writer', 'Night')
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            manifest = json.loads(db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?', (job,)).fetchone()[0])
            manifest['sources'] = [{'path': str(self.library / 'Тёмная серия' / 'Night' / '01.mp3')}]
            db.execute('UPDATE audio_jobs SET manifest=? WHERE job_id=?', (json.dumps(manifest, ensure_ascii=False), job))
            author_rules.append(db, 'same_as', 'Anon Writer', target='Writer Real', scope='Тёмная серия', actor='user', source='test')
            db.commit()
        item = next(i for i in self.plan()['items'] if i['job_id'] == job)
        self.assertEqual(item['to'], str(self.sorted / 'Writer Real' / 'Night - Writer Real.m4b'))

    def test_m3_retained_jobs_are_left_as_published(self):
        from merge_service import MergeService
        job = self.book('Роулинг Джоан\\Kept - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Kept', language='Unknown')
        other = self.book('Роулинг Джоан\\Free - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Free', language='Unknown')
        merge = MergeService.__new__(MergeService)
        merge.inventory = SimpleNamespace(database=self.database, output_root=str(self.sorted), worker=None)
        with mock.patch('storage_relocation_native.retained_job_ids', return_value=frozenset({job})):
            found = merge.sorting_moves()
        self.assertEqual([i['job_id'] for i in found['items']], [other])
        self.assertEqual([(i['job_id'], i['refused']) for i in found['refused']],
                         [(job, 'Kept as published while the data folder move is unfinished; left as it is')])


class QAFindingTests(SortedCatalog):
    """Futaba's 0.30.0 QA: C1 (the series language decided from FantLab's own cycle when the book's language is Unknown)
    and C3 (an unlisted or refused book in an approval says so)."""

    def test_c1_an_unknown_language_book_takes_the_cycles_original_name(self):
        import author_rules, sorting_moves
        from test_sorting_030 import cycle
        job = self.book("Rowling J. K\\Гарри Поттер и философский камень - Rowling J. K.m4b", 'Rowling J. K', 'Гарри Поттер и философский камень', language='Unknown')
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            cycle(db, 3650, 'Гарри Поттер', 'Harry Potter', 'en')
            cycle(db, 100, 'Дозоры', 'Дозоры', 'ru')
            db.commit()
            manifest = json.loads(db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?', (job,)).fetchone()[0])
            series = {'name': 'Гарри Поттер', 'number': '1', 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work3650'}
            review = sorting_moves.canonical(db, manifest, author_rules.load(self.database), series)[0]
            self.assertEqual(review['series'], 'Harry Potter', 'was «Гарри Поттер»: only an "Other" language was looked at')
            russian = sorting_moves.canonical(db, manifest, None, {'name': 'Дозоры', 'number': '1', 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work100'})[0]
            self.assertEqual(russian['series'], 'Дозоры', 'a cycle written in Russian keeps its name')
            manifest['metadata']['original_language'] = 'Russian'
            self.assertEqual(sorting_moves.canonical(db, manifest, None, series)[0]['series'], 'Гарри Поттер', 'a book recorded as a Russian original keeps it')

    def test_c3_an_unlisted_or_refused_book_in_an_approval_says_so(self):
        from merge_service import MergeService
        listed = self.book('Роулинг Джоан\\Listed - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Listed', language='Unknown')
        refused = self.book('Роулинг Джоан\\Gone - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Gone', language='Unknown', create=False)
        moved = []
        merge = MergeService.__new__(MergeService)
        merge.inventory = SimpleNamespace(database=self.database, output_root=str(self.sorted), worker=None)
        merge._sorting_move = lambda job_id, target: moved.append(job_id) or {'state': 'move_queued'}
        seen = merge.sorting_moves()
        answer = merge.sorting_moves_apply(seen['digest'], [listed, refused, 'job-unknown'])
        self.assertEqual(moved, [listed])
        self.assertEqual([(r['job_id'], r['state'], r.get('reason', '')) for r in answer['results']],
                         [(listed, 'move_queued', ''), (refused, 'refused', 'The audiobook is not where the catalog says'),
                          ('job-unknown', 'not_listed', 'Not in the list')])


class ScriptTests(unittest.TestCase):
    """scripts/sorting_moves.py: it names the app and port it talks to, and the list's digest and count, before it
    approves anything; any book not moved makes it exit with an error (C3)."""

    def run_script(self, argv, plan, results):
        import io, importlib.util
        spec = importlib.util.spec_from_file_location('sorting_moves_script', Path(__file__).resolve().parents[1] / 'scripts' / 'sorting_moves.py')
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
        calls = []

        def call(port, path, data, token):
            calls.append(path)
            return plan if path == '/api/sorting-moves' else {'digest': data['digest'], 'results': results}
        out = io.StringIO()
        with mock.patch.object(script, '_token', return_value='t'), mock.patch.object(script, '_call', side_effect=call), \
                mock.patch.object(script, '_health', return_value={'application': 'Books Arranger', 'version': '0.30.0', 'pid': 42, 'port': 5210}), \
                mock.patch('sys.stdout', out):
            code = script.main(argv)
        return code, out.getvalue(), calls

    def plan(self):
        return {'schema': 'books-sorting-moves-v1', 'output_root': 'Z:\\S', 'items': [{'job_id': 'a', 'from': 'x', 'to': 'y', 'items': ['author']}], 'refused': [],
                'counts': {'series': 0, 'author': 1, 'series_language': 0, 'moves': 1, 'refused': 0},
                'refused_counts': {'series': 0, 'author': 0, 'series_language': 0}, 'digest': 'd' * 64}

    def test_it_names_the_app_the_list_and_fails_when_a_book_did_not_move(self):
        code, text, calls = self.run_script(['--apply', 'd' * 64, '--job', 'a', '--job', 'zz'], self.plan(),
                                            [{'job_id': 'a', 'state': 'move_queued'}, {'job_id': 'zz', 'state': 'not_listed', 'reason': 'Not in the list'}])
        self.assertIn('127.0.0.1:5210', text)
        self.assertIn('Books Arranger 0.30.0', text)
        self.assertIn('d' * 64, text)
        self.assertIn('1 book', text)
        self.assertLess(text.index('127.0.0.1:5210'), text.index('zz not_listed'), 'named before anything is approved')
        self.assertEqual(calls, ['/api/sorting-moves', '/api/sorting-moves/apply'])
        self.assertNotEqual(code, 0, 'was 0: a book not moved said nothing')
        code, _, _ = self.run_script(['--apply', 'd' * 64], self.plan(), [{'job_id': 'a', 'state': 'move_queued'}])
        self.assertEqual(code, 0, 'positive control: everything moved')


class FollowUpRetryTests(SeriesFolderBackfillTests):
    """M2: a follow-up move refused for a passing reason (Quit, a move already running, the queue) is tried again by the
    next pass; only a lasting refusal is recorded."""

    def approved(self, answers):
        lib = self.lib
        calls = []

        def follow_up(job_id, approved, placed):
            calls.append(placed)
            answer = answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer
        merge = lib.merge()
        merge.sorting_follow_up = follow_up
        merge.sorting_target = lambda job_id, series=None: str(self.series_path)
        backfill = lib.backfill(merge=merge, found=None)
        backfill.apply(lib.job_id, self.found)
        backfill.approve(lib.job_id, self.found, str(self.series_path))
        return backfill, calls

    def test_a_passing_refusal_is_tried_again(self):
        backfill, calls = self.approved([{'state': 'later', 'reason': 'Books Arranger is closing. Nothing was moved.'},
                                         RuntimeError('database is locked'), {'state': 'move_queued'}])
        backfill.run_pass()
        entry = backfill.entry(self.lib.job_id)
        self.assertEqual(entry['state'], 'done')
        self.assertIsNone(entry['record'].get('follow_up'), 'not recorded: was "refused" for good')
        self.assertEqual(entry['record']['follow_up_wait']['reason'], 'Books Arranger is closing. Nothing was moved.')
        backfill.run_pass()
        self.assertIsNone(backfill.entry(self.lib.job_id)['record'].get('follow_up'), 'an unexpected error is tried again too')
        backfill.run_pass()
        record = backfill.entry(self.lib.job_id)['record']
        self.assertEqual(record['follow_up']['state'], 'move_queued')
        self.assertEqual(len(calls), 3)
        backfill.run_pass()
        self.assertEqual(len(calls), 3, 'recorded once done: never asked again')

    def test_a_lasting_refusal_is_recorded_once(self):
        backfill, calls = self.approved([{'state': 'refused', 'reason': 'The planned place changed since you approved it; the book stays where it is.'}])
        backfill.run_pass()
        backfill.run_pass()
        self.assertEqual(backfill.entry(self.lib.job_id)['record']['follow_up']['state'], 'refused')
        self.assertEqual(len(calls), 1)


class FollowUpAnswerTests(unittest.TestCase):
    """M2: MergeService.sorting_follow_up says 'later' for a passing refusal, 'refused' for a lasting one."""

    def merge(self, error=None, draining=False):
        from merge_service import MergeService
        merge = MergeService.__new__(MergeService)
        merge.draining = draining
        merge.sorting_target = lambda job_id, series=None, placed=None: 'Z:\\S\\A\\Book.m4b'

        def move(job_id, target):
            if error:
                raise error
            return {'state': 'move_queued'}
        merge._sorting_move = move
        return merge

    def test_answers(self):
        import book_move, destination_overrides
        self.assertEqual(self.merge(draining=True).sorting_follow_up('j', 'Z:\\S\\A\\Book.m4b')['state'], 'later')
        for error in (destination_overrides.Refused('changed', 'Move was not accepted. Nothing was moved.'), book_move.Refused('unfinished', book_move.UNFINISHED),
                      book_move.Refused('changed', 'This audiobook is being moved now. Choose another folder when it finishes.'),
                      ValueError('Books Arranger is closing. Nothing was moved.'), sqlite3.OperationalError('database is locked')):
            with self.subTest(error=str(error)):
                self.assertEqual(self.merge(error).sorting_follow_up('j', 'Z:\\S\\A\\Book.m4b')['state'], 'later')
        self.assertEqual(self.merge(ValueError('This audiobook has a newer version; it was not moved')).sorting_follow_up('j', 'Z:\\S\\A\\Book.m4b')['state'], 'refused')
        self.assertEqual(self.merge().sorting_follow_up('j', 'Z:\\S\\B\\Book.m4b')['state'], 'refused', 'the planned place changed')
        self.assertEqual(self.merge().sorting_follow_up('j', 'Z:\\S\\A\\Book.m4b')['state'], 'move_queued')


class RetainedRecoveryTests(unittest.TestCase):
    """M3: move recovery runs in retained-runtime mode; a move of a retained job or through a retained path is left
    journaled, as it was."""

    def setUp(self):
        import test_book_move
        self.case = test_book_move.StrategyTests('test_never_reconverts')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def interrupted(self):
        """A same-volume rename stopped after the rename, before its location commit."""
        import test_book_move
        case = self.case
        case.crash_at = 'renamed'
        target = case.sorted / 'Rowling J. K'
        target.mkdir()
        move = case.plan(target)
        with self.assertRaises(test_book_move.Crash):
            case.mover().run(move['move_id'])
        return move['move_id'], target / case.old.name

    def merge(self):
        from merge_service import MergeService
        merge = MergeService.__new__(MergeService)
        merge.inventory = SimpleNamespace(database=self.case.db, output_root=str(self.case.sorted), roots={'Audiobooks': str(self.case.library)}, worker=None)
        merge.move_same_volume = None
        merge.move_fault = None
        merge.__dict__['_after_move'] = lambda move: None
        return merge

    def recover(self, retained_path=None, retained_job=False):
        import book_move
        merge = self.merge()
        with mock.patch('storage_relocation_native.retained_runtime', return_value=True), \
                mock.patch('storage_relocation_native.retained_job', return_value=retained_job), \
                mock.patch('storage_relocation_native.retained_path', side_effect=lambda path, parent=False: path == retained_path):
            merge._start_move_recovery()
            merge._move_recovery.join(30)
        with __import__('scanner').connect(self.case.db) as db:
            return book_move.pending(db), merge

    def test_a_sorted_move_is_finished_in_retained_mode(self):
        _, new = self.interrupted()
        pending, _ = self.recover()
        self.assertEqual(pending, 0, 'finished: was never recovered in retained mode')
        self.assertTrue(new.exists())

    def test_a_move_through_a_retained_path_or_of_a_retained_job_stays_journaled(self):
        move_id, new = self.interrupted()
        pending, merge = self.recover(retained_path=str(new))
        self.assertEqual(pending, 1)
        self.assertIn(move_id, merge.__dict__.get('_move_unfinished', {}))
        pending, _ = self.recover(retained_job=True)
        self.assertEqual(pending, 1)


if __name__ == '__main__':
    unittest.main()
