"""0.31.0 ruling R27 in the rules' pass (rule_filing): a finished book that needs a series write, a write of its names and a
move gets them as one sequence, once (the series write carries the names: the file is rewritten once), and the guards of
the automatic filing hold for the new job: names he typed, a doubtful or missing English title, his chosen folder, a book
the app moved before, Pause, loading, two books in hand and three tries an hour apart. The record says what went into the
file. Real audiobooks (test_name_write_031's Book) and the rules' own fixture shelf (test_rule_filing_031's Shelf).

Each behaviour has its control: the same case without the rule gives another result (named in the test)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import name_write
import publication_locations as p
import quicktime_chapters
import rule_filing
import series_backfill
from name_write import NameWrite
from scanner import connect
from series_backfill import SeriesBackfill
from test_name_write_031 import ENGLISH, ORDERED, ROOT, SHORT, Book, probe, sha, tags


class OnePassTests(unittest.TestCase):
    """Item 2: a book that needs a series write, a write of names and a move gets them as one sequence, once: the file is
    rewritten once (the series write carries the names) and moved once to its final name."""

    def test_series_and_english_title_are_one_rewrite_then_one_move(self):
        from test_sorting_030 import cycle
        book = Book(self)
        with connect(book.lib.db) as db:
            db.execute('CREATE TABLE IF NOT EXISTS public_research_cache(url TEXT PRIMARY KEY, raw TEXT, sha256 TEXT, fetched REAL)')
            cycle(db, 777, 'Нормальное аномальное', 'Normal Abnormal', 'en')
            db.execute('DELETE FROM series_backfill')
        research = SimpleNamespace(_series_goodreads=lambda *a: None, _series_wikidata=lambda *a: None, _series_publisher=lambda *a: None, _series_litres=lambda *a: None,
                                   _series_fantlab=lambda *a: {'provider': 'fantlab', 'name': 'Нормальное аномальное', 'number': '10', 'number_from': 'counted',
                                                               'source_url': 'https://fantlab.ru/work777'})
        backfill = book.merge.series_backfill = SeriesBackfill(book.merge, research=research, stage=book.lib.base / 'proof-stage')
        backfill.run_pass()  # the look-up finds the series and holds the book (the rules approve)
        final = book.lib.root / book.author / 'Normal Abnormal' / ('Normal Abnormal - 10 - %s - %s.m4b' % (ENGLISH, book.author))
        value = book.filing.tick()
        self.assertEqual((value['writes_waiting'], value['renames_waiting'], value['moves_waiting'], value['left']), (1, 0, 0, 1), 'one book, one write')
        entry = backfill.entry(book.lib.job_id)
        self.assertEqual((entry['record']['approved_names'], entry['record']['approved_target']), ({'title': ENGLISH}, str(final)))
        self.assertIsNone(book.writer.entry(book.lib.job_id), 'no second writer for the same file')
        calls = []
        real = quicktime_chapters.retag
        with mock.patch.object(quicktime_chapters, 'retag', lambda *a: calls.append(a) or real(*a)):
            backfill.run_pass()
        self.assertEqual((len(calls), backfill.entry(book.lib.job_id)['state']), (1, 'done'), 'the file is rewritten once')
        placed = Path(backfill.entry(book.lib.job_id)['record']['new_path'])
        now = tags(probe(placed))
        self.assertEqual((now['title'], now['grouping'], now['album']), (ENGLISH, 'Normal Abnormal', 'Normal Abnormal - 10 - ' + ENGLISH), 'series and title in one rewrite')
        manifest = book.manifest()
        self.assertEqual((manifest['metadata']['title'], manifest['metadata']['series']), (ENGLISH, 'Normal Abnormal'))
        journal = json.loads(book.row()['journal'])
        self.assertEqual(p._digest(journal['publication_intent']), p._digest(book.output()), 'the names written: the receipt is the publication intent')
        book.run_queue()
        value = book.filing.tick()
        self.assertEqual((value['left'], value['record']['count'], final.exists()), (0, 1, True))
        found = book.filing.record()['entries'][0]
        self.assertEqual((found['from'], found['to'], found['title'], found['kinds'], found['written']), (str(book.path), str(final), ENGLISH, ['series', 'title'], ['series', 'title']))
        self.assertEqual(len(calls), 1)

    def test_an_english_title_alone_is_a_rename_job_of_its_own_and_a_record_entry(self):
        book = Book(self)
        value = book.filing.tick()
        self.assertEqual((value['renames_waiting'], value['writes_waiting'], value['moves_waiting'], value['left']), (1, 0, 0, 1))
        self.assertEqual(value['next_rename']['title'], book.title, 'the title the list shows until the write lands')
        self.assertEqual(book.state()[0], 'pending')
        self.assertEqual(book.filing.summary()['renames_running'], 0)
        book.writer.run_pass()
        value = book.filing.tick()
        self.assertEqual((value['left'], value['record']['count'], value['renames_waiting']), (0, 1, 0))
        found = book.filing.record()['entries'][0]
        new = book.writer.entry(book.lib.job_id)['record']['new_path']
        self.assertEqual((found['from'], found['to'], found['title'], found['kinds'], found['written']), (str(book.path), new, ENGLISH, ['title'], ['title']),
                         'Was in and Now in: the same folder, the file name shows the change')
        self.assertEqual(found['reasons'], [{'kind': 'title', 'title': ENGLISH, 'provider': 'wikidata', 'source_url': 'https://www.wikidata.org/wiki/Q42'}])
        self.assertEqual(book.filing.record(search=ENGLISH)['matching'], 1)

    def test_control_a_move_alone_writes_nothing_into_the_file(self):
        book = Book(self, english=None, author_rule=ORDERED)
        with mock.patch.object(name_write, 'WRITE_NAMES', 'off'):
            value = book.filing.tick()
            self.assertEqual((value['renames_waiting'], value['moves_waiting']), (0, 1))
            book.run_queue()
            book.filing.tick()
        found = book.filing.record()['entries'][0]
        self.assertEqual((found['written'], found['kinds']), ([], ['author']))
        self.assertEqual(sha(found['to']), book.original, 'the verified move keeps every byte: the tags still hold the old credit')

    def test_a_failed_tag_write_is_tried_three_times_an_hour_apart_then_listed_with_its_cause(self):
        book = Book(self)
        clock = [1_900_000_000.0]
        book.filing.clock = book.writer.clock = lambda: clock[0]
        with mock.patch.object(name_write, 'check', side_effect=series_backfill.Held('The new names did not read back: title')):
            for attempt in range(1, 4):
                book.filing.tick()
                book.writer.run_pass()
                value = book.filing.tick()
                could = book.filing.could_not()['entries']
                self.assertEqual([(e['key'], e['cause'], e['tries']) for e in could], [(rule_filing.DID_NOT_FINISH, 'tags_not_written', attempt)])
                self.assertEqual(sha(book.path), book.original)
                book.filing.tick()
                self.assertEqual(book.state()[0], 'held', 'not tried again within the hour')
                clock[0] += rule_filing.SPACING + 1
        value = book.filing.tick()
        self.assertEqual((value['left'], value['could_not'], book.filing.could_not()['entries'][0]['retries']), (0, 1, False), 'three tries, then listed for good')


class GuardTests(unittest.TestCase):
    """Item 3 on the rules' own fixture shelf (test_rule_filing_031): names he typed, a doubtful or missing English title,
    his chosen folder, Pause, loading, and the pacing."""

    def shelf(self):
        import test_rule_filing_031 as base
        shelf = base.Shelf('setUp')
        shelf.setUp()
        self.addCleanup(shelf.doCleanups)
        engine = shelf.engine
        engine.name_write = NameWrite(engine, stage=shelf.base / 'names')
        engine.sorting_target = lambda job_id, series=None, placed=None: ''
        return shelf

    def items(self, shelf):
        return {item['job_id']: item for item in shelf.engine.sorting_moves()['items']}

    def test_a_title_or_author_he_typed_is_never_overridden(self):
        shelf = self.shelf()
        typed = shelf.book('Gibson William', 'Граф Ноль')
        control = shelf.book('Gibson William', 'Мона Лиза овердрайв')
        for job, title in ((typed, 'Count Zero'), (control, 'Mona Lisa Overdrive')):
            shelf.english_title(job, title)
        with connect(shelf.db) as db:
            manifest = json.loads(db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?', (typed,)).fetchone()[0])
            manifest['metadata_facts']['entered_names'] = {'fields': ['title', 'author']}
            db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=? WHERE job_id=?', (p._packed(manifest), p._digest(manifest), typed))
        items = self.items(shelf)
        self.assertNotIn(typed, items, 'his title: nothing to change, nothing written')
        self.assertEqual(items[control]['names'], {'title': 'Mona Lisa Overdrive'}, 'control: the same book without his title')

    def test_a_doubtful_or_missing_english_title_changes_nothing(self):
        shelf = self.shelf()
        missing = shelf.book('Gibson William', 'Граф Ноль')
        doubtful = shelf.book('Лю Цысинь', 'Задача трёх тел')
        russian = shelf.book('Лукьяненко Сергей', 'Ночной дозор', language='Russian')
        shelf.english_title(russian, 'Night Watch', language='ru')  # a Russian original keeps its Russian title (R1)
        shelf.english_title(doubtful, 'Задача трёх тел', language='zh')  # no title in Latin letters: not an English title
        with connect(shelf.db) as db:
            db.execute("INSERT OR REPLACE INTO gap_fill VALUES(?,?,'none','',?,'now')", (missing, 'c', json.dumps({})))
        self.assertEqual(self.items(shelf), {}, 'no English title found (R3) or a doubtful one: no change, no write')
        shelf.english_title(missing, 'Count Zero')
        self.assertEqual(self.items(shelf)[missing]['names'], {'title': 'Count Zero'}, 'control: found for certain, it is written')

    def test_his_chosen_folder_is_kept(self):
        shelf = self.shelf()
        job = shelf.book('Gibson William', 'Граф Ноль')
        shelf.english_title(job, 'Count Zero')
        with connect(shelf.db) as db:
            manifest = json.loads(db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?', (job,)).fetchone()[0])
            manifest['metadata_facts']['destination_override'] = {'folder': str(shelf.sorted / 'Mine')}
            db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=? WHERE job_id=?', (p._packed(manifest), p._digest(manifest), job))
        answer = shelf.engine.sorting_moves()
        self.assertEqual(([i['job_id'] for i in answer['items']], [i['refused_key'] for i in answer['refused']]), ([], ['chosen_folder']))
        value = shelf.filing.tick()
        self.assertEqual((value['renames_waiting'], shelf.engine.name_write.entry(job)), (0, None))

    def test_a_book_the_app_moved_before_keeps_the_move_alone(self):
        shelf = self.shelf()
        job = shelf.book('Gibson William', 'Граф Ноль')
        shelf.settle()  # nothing to do yet
        moved = shelf.sorted / 'Gibson William' / 'Elsewhere - Gibson William.m4b'
        shelf.engine._sorting_move(job, str(moved), origin='rules')
        shelf.engine.run_queue()
        shelf.english_title(job, 'Count Zero')
        item = self.items(shelf)[job]
        self.assertNotIn('names', item, 'its place is a chain on top of its receipt: a rewrite would break it')
        self.assertEqual(rule_filing.route(item), 'move')

    def test_pause_holds_the_job_and_two_books_are_in_hand_at_a_time(self):
        shelf = self.shelf()
        jobs = [shelf.book('Gibson William', title) for title in ('Граф Ноль', 'Мона Лиза овердрайв', 'Нейромант', 'Сожжение Хром', 'Джонни Мнемоник')]
        for job, title in zip(jobs, ('Count Zero', 'Mona Lisa Overdrive', 'Neuromancer', 'Burning Chrome', 'Johnny Mnemonic')):
            shelf.english_title(job, title)
        shelf.engine.paused = True
        value = shelf.filing.tick()
        self.assertEqual((value['paused'], value['renames_waiting'], value['left']), (True, 5, 5))
        self.assertEqual([shelf.engine.name_write.entry(job) for job in jobs], [None] * 5, 'paused: nothing is put in hand')
        shelf.engine.paused = False
        value = shelf.filing.tick()
        in_hand = [job for job in jobs if shelf.engine.name_write.entry(job)]
        self.assertEqual((len(in_hand), value['renames_waiting'], value['left']), (rule_filing.FEED, 5, 5), 'two in hand, every book counted once')
        self.assertEqual({filing['step'] for filing in shelf.filings('open') if filing['job_id'] in in_hand}, {'names'})
        # A Pause after they were put in hand holds the write itself (series_backfill._idle).
        shelf.engine.paused = True
        shelf.engine.name_write.run_pass()
        self.assertEqual({shelf.engine.name_write.entry(job)['state'] for job in in_hand}, {'deferred'})
        self.assertEqual({shelf.engine.name_write.entry(job)['reason'] for job in in_hand}, {'Audiobook jobs are paused'})

    def test_nothing_starts_before_loading_finishes(self):
        self.assertGreaterEqual(name_write.START_DELAY, series_backfill.START_DELAY)
        source = (ROOT / 'merge_service.py').read_text(encoding='utf-8')
        self.assertIn("for name in ('series_backfill','name_write','gap_fill','rule_filing'):\n            background=self.__dict__.get(name)\n            if background is not None:background.start()", source,
                      'started with the series look-up, after the catalog has loaded')
        shelf = self.shelf()
        job = shelf.book('Gibson William', 'Граф Ноль')
        shelf.english_title(job, 'Count Zero')
        shelf.engine.name_write.run_pass()
        self.assertIsNone(shelf.engine.name_write.entry(job), 'the write runs only what the rules approved')

class RecordColumnTests(unittest.TestCase):
    """The one schema change of R27: rule_filings.written (what went into the file), added once to a table an earlier 0.31.0
    build made; 0.30.1 has no rule_filings table at all, so a rollback ignores it."""

    def test_the_record_column_is_added_once_to_a_table_made_before_it(self):
        base = Path(tempfile.mkdtemp(dir=SHORT if SHORT.exists() else None, prefix='rf'))
        self.addCleanup(shutil.rmtree, base, True)
        database = str(base / 'c.sqlite3')
        old = rule_filing.TABLE.replace(', written TEXT)', ')')
        self.assertNotEqual(old, rule_filing.TABLE)
        with connect(database) as db:
            db.execute(old)
            db.execute("INSERT INTO rule_filings(filing_id,job_id,candidate_id,state,step,from_path,to_path,kinds,reasons,title,author,created_utc,updated_utc,done_utc)"
                       " VALUES('f0','j0','c','done','','a','b','[]','[]','t','a','now','now','now')")
            rule_filing.setup(db)
            rule_filing.setup(db)
            self.assertEqual([r[1] for r in db.execute('PRAGMA table_info(rule_filings)')][-1], 'written')
            self.assertEqual(rule_filing.record(db)['entries'][0]['written'], [], 'an entry made before it wrote nothing into a file')



class RouteTests(unittest.TestCase):
    def test_the_list_item_decides_the_route(self):
        self.assertEqual(rule_filing.route({'items': ['series', 'title'], 'names': {'title': 'T'}}), 'write', 'the series write carries the names')
        self.assertEqual(rule_filing.route({'items': ['title'], 'names': {'title': 'T'}}), 'names')
        self.assertEqual(rule_filing.route({'items': ['title'], 'names': {'title': 'T'}}, names_writer=False), 'move', 'an engine without the job')
        self.assertEqual(rule_filing.route({'items': ['title'], 'names': {'title': 'T'}, 'placed': True}), 'move', 'written already: it only moves')
        self.assertEqual(rule_filing.route({'items': ['author']}), 'move', 'a folder name alone is the move\'s')
        book = Book(self)
        with mock.patch.object(name_write, 'WRITE_NAMES', 'off'):
            self.assertEqual(rule_filing.route(book.plan_item()), 'move', 'switched off: milestone B, exactly')
        self.assertEqual(rule_filing.route(book.plan_item()), 'names', 'control: on')


class WorkViewTests(unittest.TestCase):
    """Item 5, the engine's side: /api/state work carries the rename row while a write of names runs, one rename_write item per
    book whose write waits (its blocker as a queued action's), the filing counts with renames, and the record's 'written'."""

    def view(self, book, jobs=None):
        import background_work
        return background_work.view(SimpleNamespace(merge=book.merge, active_library=''), jobs or {}, {}, {}, False, None)

    def test_the_rename_row_its_waiting_item_and_the_counts(self):
        import background_work
        import pause_state
        book = Book(self)
        book.filing.tick()  # in hand: approved by the rules
        with connect(book.lib.db) as db:
            pause_state.record(db, 'jobs', 'user', 'Audiobook jobs paused')
        book.writer.run_pass()  # held by the Pause before anything is read: a write that waits
        book.filing.tick()  # the pass's numbers at the poll after it
        work = self.view(book)
        items = [item for item in work['lookups_waiting'] if item['kind'] == 'rename_write']
        self.assertEqual([(item['subject'], item['book_id'], item['job_id'], item['background']) for item in items], [(book.title, book.lib.candidate, book.lib.job_id, False)])
        self.assertEqual(items[0]['blocker']['kind'], 'jobs', 'it waits for the queue, as a series write does')
        filing = work['filing']
        self.assertEqual((filing['renames_waiting'], filing['renames_running'], filing['left'], filing['next_rename']['title']), (1, 0, 1, book.title))
        self.assertEqual(filing['next_rename']['blocker']['cause'], 'queue_paused', 'paused: the blocker says so')
        self.assertEqual(work['pending']['filing'], 1, 'main work: never all done while it waits')
        self.assertNotIn('rename', [row['kind'] for row in work['rows']], 'no running row while it waits')
        with connect(book.lib.db) as db:
            pause_state.clear(db, 'jobs')
        seen = []
        real = NameWrite.apply

        def watch(writer, job_id, found=None):
            seen.append(self.view(book))
            return real(writer, job_id, found)
        book.writer.clock = lambda: 2_000_000_000.0
        with mock.patch.object(NameWrite, 'apply', watch):
            book.writer.run_pass()
        rows = [row for row in seen[0]['rows'] if row['kind'] == 'rename']
        self.assertEqual([(row['id'], row['subject'], row['step'], row['background'], row['done']) for row in rows], [('rename', book.title, 'updating', False, None)])
        self.assertEqual(seen[0]['state'], 'working', 'a write of names is main work (1.1)')
        self.assertEqual(background_work.KIND_FACTS['rename'], {'background': False, 'about': 'finished', 'writes_finished_files': True})
        self.assertEqual(background_work.KIND_FACTS['rename_write'], {'background': False, 'about': 'finished', 'writes_finished_files': True})
        self.assertNotIn('rename', [row['kind'] for row in self.view(book)['rows']], 'and gone when it is done')
        self.assertEqual(book.filing.tick()['record']['count'], 1)
        self.assertEqual(book.filing.record()['entries'][0]['written'], ['title'])

    def test_control_an_engine_without_the_job_sends_neither(self):
        import background_work
        book = Book(self)
        del book.merge.name_write
        book.filing.tick()
        work = background_work.view(SimpleNamespace(merge=book.merge, active_library=''), {}, {}, {}, False, None)
        self.assertEqual(([row for row in work['rows'] if row['kind'] == 'rename'], [i for i in work['lookups_waiting'] if i['kind'] == 'rename_write']), ([], []))
        self.assertEqual((work['filing']['renames_waiting'], work['filing']['moves_waiting']), (0, 1), 'the 0.31.0 milestone B move, exactly')


if __name__ == '__main__':
    unittest.main()
