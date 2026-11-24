"""0.31.0 guard (Jane for Sergei, 2026-11-22): until he rules, the series look-up writes a series into no finished
audiobook and renames none without his approval, the flat-named books included (series_backfill.WRITE_WITHOUT_APPROVAL).

Before it, a book whose name with the series stays in its own folder was written and renamed at once: 296 of the 798
finished books without a series on a copy of the live catalog, 282 of them still to look up once the look-up ends its
repeats (step 4a). A real published audiobook made by ffmpeg in a private Sorted folder, named flat as those books are; the
catalog tables of the back-fill; no library, no network. The write itself is watched at its two doors (the retag that
makes the new file, and the rename), so the test fails if either opens while the guard holds."""
import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import series_backfill
import sorting_moves
from scanner import connect
from test_series_backfill import AREA, Library, TITLE

SERIES = ('Нормальное аномальное', '10')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(series_backfill.WRITE_WITHOUT_APPROVAL, 'hold', 'the default until Sergei rules')
        temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(temp.cleanup)
        self.lib = Library(Path(temp.name))
        merge = self.lib.merge()
        merge.inventory.output_root = str(self.lib.root)  # as the engine has it: the plan and an approval name places in Sorted
        self.backfill = self.lib.backfill(merge, found=SERIES)
        self.before = (sha(self.lib.path), sorted(p.name for p in self.lib.path.parent.iterdir()))

    def files(self):
        return sha(self.lib.path) if self.lib.path.exists() else None, sorted(p.name for p in self.lib.path.parent.iterdir())

    def doors(self):
        """The two calls every series write goes through, replaced by counters: (retag, rename)."""
        return patch.object(series_backfill.SeriesBackfill, '_write'), patch.object(series_backfill.SeriesBackfill, 'resume')

    def test_this_book_is_one_the_lookup_wrote_without_asking(self):
        # Positive control for the fixture: the series name stays in the book's own folder (the flat naming).
        self.assertEqual(self.lib.target.parent, self.lib.path.parent)
        self.assertNotEqual(self.lib.target.name, self.lib.path.name)

    def test_held_no_file_is_written_or_renamed_and_the_series_found_is_kept(self):
        write, rename = self.doors()
        with write as written, rename as renamed:
            self.backfill.run_pass()
        self.assertEqual((written.call_count, renamed.call_count), (0, 0), 'a write happened while the guard holds')
        self.assertEqual(self.files(), self.before, 'the published file and its folder are exactly as they were')
        self.assertEqual(self.lib.temps(), [], 'not even a temporary file')
        entry = self.backfill.entry(self.lib.job_id)
        self.assertEqual((entry['state'], entry['reason']), ('held', series_backfill.WRITE_WAITS))
        self.assertEqual((entry['record']['series'], entry['record']['number'], entry['record']['provider']), (*SERIES, 'goodreads'), 'the look-up still ran and ended')
        with connect(self.lib.db) as db:
            row = db.execute('SELECT manifest,output FROM audio_jobs WHERE job_id=?', (self.lib.job_id,)).fetchone()
        self.assertEqual((row['manifest'], row['output']), (self.lib.row()['manifest'], self.lib.row()['output']))
        self.assertNotIn('"series":"Нормальное', row['manifest'], 'the catalog does not say it has a series')

    def test_held_again_at_every_later_pass(self):
        write, rename = self.doors()
        with write as written, rename as renamed:
            for _ in range(5):
                self.backfill.run_pass()
        self.assertEqual((written.call_count, renamed.call_count), (0, 0))
        self.assertEqual(self.backfill.candidates(), [], 'held is settled for the look-up: it is not looked up again')
        self.assertEqual(self.files(), self.before)

    def test_without_the_guard_the_same_book_is_written(self):
        # Positive control: the 0.16.12 behaviour the guard holds back. The same pass reaches the write.
        write, rename = self.doors()
        with patch.object(series_backfill, 'WRITE_WITHOUT_APPROVAL', 'allow'), write as written, rename as renamed:
            self.backfill.run_pass()
        self.assertEqual((written.call_count, renamed.call_count), (1, 1), 'the check above can fail')
        self.assertEqual(written.call_args[0][5]['series'], SERIES[0])

    def test_any_value_but_allow_holds(self):
        for value in ('hold', '', None, 'ALLOW', 'yes', True):
            with self.subTest(value=value):
                lib = Library(Path(tempfile.mkdtemp(dir=AREA))); self.addCleanup(shutil.rmtree, lib.base, True)
                backfill = lib.backfill(found=SERIES)
                write, rename = self.doors()
                with patch.object(series_backfill, 'WRITE_WITHOUT_APPROVAL', value), write as written, rename as renamed:
                    backfill.run_pass()
                self.assertEqual((written.call_count, renamed.call_count, backfill.entry(lib.job_id)['reason']), (0, 0, series_backfill.WRITE_WAITS))

    def test_the_held_book_is_counted_as_waiting_for_him_and_listed_for_approval(self):
        self.backfill.run_pass()
        value = self.backfill.summary()
        self.assertEqual((value['moves_waiting'], value['writes_held'], value['write_without_approval'], value['left']), (1, 1, 'hold', 0))
        self.assertIs(value['applies_by_itself'], False)
        self.backfill._changed()
        with patch.object(series_backfill, 'WRITE_WITHOUT_APPROVAL', 'allow'):
            self.assertIs(self.backfill.summary()['applies_by_itself'], True, 'the one fact the series row\'s tooltip follows (Judy 2.1)')
        self.backfill._changed()
        with connect(self.lib.db) as db:
            plan = sorting_moves.plan(db, str(self.lib.root))
        item = next(i for i in plan['items'] if i['job_id'] == self.lib.job_id)
        self.assertEqual((item['to'], item['items'], item['title']), (str(self.lib.target), ['series'], TITLE))
        self.assertEqual(item['series']['name'], SERIES[0])

    def test_his_approval_opens_the_write_for_that_book_only(self):
        self.backfill.run_pass()
        found = {'name': SERIES[0], 'number': SERIES[1], 'provider': 'goodreads', 'source_url': 'https://www.goodreads.com/book/show/55108791'}
        self.backfill.approve(self.lib.job_id, found, str(self.lib.target))
        write, rename = self.doors()
        with write as written, rename as renamed:
            self.backfill.run_pass()
        self.assertEqual((written.call_count, renamed.call_count), (1, 1), 'approved: written, as the look-up wrote it before')
        self.assertEqual(Path(written.call_args[0][4]).parent, self.lib.path.parent, 'in its own folder')

    def test_an_approval_of_another_place_writes_nothing(self):
        self.backfill.run_pass()
        found = {'name': SERIES[0], 'number': SERIES[1], 'provider': 'goodreads', 'source_url': 'https://www.goodreads.com/book/show/55108791'}
        self.backfill.approve(self.lib.job_id, found, str(self.lib.path.parent / 'Somewhere else.m4b'))
        write, rename = self.doors()
        with write as written, rename as renamed:
            self.backfill.run_pass()
        entry = self.backfill.entry(self.lib.job_id)
        self.assertEqual((written.call_count, renamed.call_count, entry['state']), (0, 0, 'held'))
        self.assertIn('planned place changed', entry['reason'])
        self.assertEqual(entry['record']['approved_failed']['reason'], entry['reason'], 'and it comes back to the list with why')
        self.assertEqual(self.files(), self.before)


if __name__ == '__main__':
    unittest.main()
