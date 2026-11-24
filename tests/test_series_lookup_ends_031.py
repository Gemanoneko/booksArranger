"""0.31.0 step 4a (Sergei 2026-11-22): the series look-up of finished books comes to an end.

The reported shape, measured on a copy of the live catalog: 745 of 907 ledger rows deferred, 576 more than 1,000 times
(one 3,287), because a book was settled only when every source answered in one pass and DuckDuckGo sat behind a human
check; 129 more waited for a cleanup that was on hold. Here: a book with an unreachable source, the app's own limit, a
source whose answer cannot be used, a look-up that keeps failing, a book deferred thousands of times before the update,
and a book whose cleanup is on hold. The real ledger and scheduler over a private catalog; no media, no network."""
import contextlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import series_backfill
from public_research import CHALLENGE_REASON, LANE_LIMIT_REASON, ResearchWait
from scanner import connect
from series_backfill import SOURCE_TRIES, TRY_SPACING, FAILURE_TRIES, SeriesBackfill

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'series-lookup-ends-tests'


def human_check(clock, host='html.duckduckgo.com'):
    def closed(*_):
        raise ResearchWait(host, CHALLENGE_REASON, clock() + 3600, 'source_pause', 'host')
    return closed


def unavailable(clock, host='html.duckduckgo.com'):
    """A source that does not answer (no human check): a try, three of them six hours apart (R9). Ruling R32 made
    DuckDuckGo's human check "nothing found" at once, so the cases about tries use this instead (HumanCheckTests)."""
    def closed(*_):
        raise ResearchWait(host, 'Public source unavailable; no bypass attempted', clock() + 300, 'source_unavailable', 'host')
    return closed


class Sources:
    """The five series sources; each a function the test sets, with the titles it was asked about."""
    def __init__(self):
        self.asked = []
        self.answers = {}

    def __getattr__(self, name):
        if not name.startswith('_series_'):
            raise AttributeError(name)
        source = name.removeprefix('_series_')

        def ask(title, *args):
            self.asked.append((source, title))
            answer = self.answers.get(source)
            return answer(title, *args) if callable(answer) else answer
        return ask


class Fixture(unittest.TestCase):
    TITLES = ('Тёмный лес',)

    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / 'catalog.sqlite3'
        self.now = [1000.0]
        with connect(self.db) as db:
            db.execute('CREATE TABLE audio_jobs(job_id TEXT,manifest TEXT,output TEXT,state TEXT,created TEXT,updated TEXT)')
            for index, title in enumerate(self.TITLES):
                manifest = {'candidate_id': 'book-%d' % index, 'metadata': {'title': title, 'canonical_author': 'Cixin Liu', 'series': ''}}
                db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?)', (str(index), json.dumps(manifest, ensure_ascii=False), '{}', 'completed', str(index), str(index)))
        self.sources = Sources()
        merge = SimpleNamespace(inventory=SimpleNamespace(database=self.db), stage_root=Path(temp.name) / 'stage')
        self.backfill = SeriesBackfill(merge, research=self.sources, clock=lambda: self.now[0])
        self.backfill.unsafe = lambda *_: ''
        self.applied = []
        self.backfill.apply = lambda job, found: (self.applied.append((job, found['name'], found['number'])), self.backfill._set(job, 'done'))

    def entry(self, job='0'):
        return self.backfill.entry(job)

    def passes(self, count, step=TRY_SPACING + 1):
        """Run a pass, then move the clock on and run the next, as the scheduler would over days."""
        for n in range(count):
            if n:
                self.now[0] += step
            self.backfill.run_pass()

    def asked(self, source):
        return sum(1 for name, _ in self.sources.asked if name == source)


class UnreachableSourceTests(Fixture):
    def test_a_book_with_an_unreachable_source_is_settled_after_the_tries(self):
        # Three sources answer "no series"; the two that go through DuckDuckGo find it not answering every time (its human
        # check is "nothing found" at once since R32: HumanCheckTests).
        self.sources.answers.update(publisher=unavailable(lambda: self.now[0]), litres=unavailable(lambda: self.now[0]))
        self.passes(1)
        first = self.entry()
        self.assertEqual(first['state'], 'deferred')
        self.assertEqual(first['record']['next_attempt'], 1000.0 + TRY_SPACING, 'not before the spacing, however soon the source says to come back')
        self.assertEqual({name: first['record']['sources'][name].get('answer') for name in ('goodreads', 'fantlab', 'wikidata')}, dict.fromkeys(('goodreads', 'fantlab', 'wikidata'), 'none'))
        self.passes(SOURCE_TRIES, step=TRY_SPACING + 1)
        settled = self.entry()
        self.assertEqual(settled['state'], 'none', 'it ends')
        self.assertEqual(settled['record']['unreached'], ['publisher', 'litres'])
        self.assertTrue(settled['reason'].startswith(series_backfill.UNREACHED), settled['reason'])
        self.assertNotIn('next_attempt', settled['record'])
        self.assertEqual((self.asked('publisher'), self.asked('litres')), (SOURCE_TRIES, SOURCE_TRIES), 'the tries, and no more')
        self.assertEqual((self.asked('goodreads'), self.asked('fantlab'), self.asked('wikidata')), (1, 1, 1), 'a source that answered is never asked again')
        before = list(self.sources.asked)
        self.passes(5, step=30 * 86400)
        self.assertEqual(self.sources.asked, before, 'settled: no request for this book, months later')
        self.assertEqual(self.backfill.candidates(), [])

    def test_before_this_rule_the_same_book_never_ended(self):
        # Positive control: the rule being replaced (every source asked again each pass, settled only when all answered in
        # one pass) keeps the same book deferred for as many passes as it is given.
        self.sources.answers.update(publisher=human_check(lambda: self.now[0]), litres=human_check(lambda: self.now[0]))

        def old_lookup(manifest, memory=None):
            waits = []
            for name in series_backfill.SOURCES:
                try:
                    if getattr(self.sources, '_series_' + name)(manifest['metadata']['title']):
                        return {}
                except ResearchWait as wait:
                    waits.append({'source': wait.source, 'reason': wait.reason, 'retry_at': wait.retry_at, 'kind': wait.kind, 'scope': wait.scope})
            if waits:
                raise series_backfill.Later('closed', min(w['retry_at'] for w in waits), waits)
            return None
        self.backfill.lookup = old_lookup
        self.passes(40, step=3601)
        self.assertEqual((self.entry()['state'], self.entry()['record']['deferrals']), ('deferred', 40))
        self.assertEqual(self.asked('goodreads'), 40, 'and it asked every source again every time')

    def test_between_tries_a_pass_asks_nothing(self):
        self.sources.answers.update(litres=unavailable(lambda: self.now[0]))
        self.passes(1)
        asked = len(self.sources.asked)
        for _ in range(20):
            self.now[0] += 600  # the ten-minute pass
            self.backfill.run_pass()
        self.assertEqual(len(self.sources.asked), asked, 'the book sleeps until its next try')
        self.assertEqual(self.entry()['record']['deferrals'], 1)

    def test_a_series_found_later_by_another_source_still_wins(self):
        self.sources.answers.update(goodreads=unavailable(lambda: self.now[0], 'www.goodreads.com'))
        self.passes(1)
        self.sources.answers['goodreads'] = {'provider': 'goodreads', 'name': "Remembrance of Earth's Past", 'number': '2', 'source_url': 'https://www.goodreads.com/book/show/1'}
        self.passes(2)
        self.assertEqual(self.applied, [('0', "Remembrance of Earth's Past", '2')])
        self.assertEqual(self.entry()['state'], 'done')


class OwnLimitTests(Fixture):
    def test_the_apps_own_hourly_limit_is_no_try_and_never_repeats_an_answer(self):
        limited = {'until': 5}

        def wikidata(title, *args):
            if limited['until'] > 0:
                limited['until'] -= 1
                raise ResearchWait('www.wikidata.org', LANE_LIMIT_REASON, self.now[0] + 900, 'app_limit', 'lane')
            return None
        self.sources.answers['wikidata'] = wikidata
        self.passes(5, step=901)
        entry = self.entry()
        self.assertEqual(entry['state'], 'deferred', 'five limits in a row: still waiting, nothing given up')
        self.assertNotIn('tries', entry['record']['sources']['wikidata'])
        self.assertEqual(entry['record']['next_attempt'], self.now[0] + 900, "the limit's own time, not the six-hour spacing")
        self.passes(2, step=901)
        self.assertEqual((self.entry()['state'], self.entry()['reason']), ('none', series_backfill.NO_SERIES))
        self.assertNotIn('unreached', self.entry()['record'])
        self.assertEqual((self.asked('goodreads'), self.asked('fantlab'), self.asked('publisher'), self.asked('litres')), (1, 1, 1, 1))

    def test_one_trys_request_budget_is_no_try_and_the_next_pass_goes_on(self):
        def spent(title, author, stop, budget, result):
            raise ResearchWait('www.goodreads.com', 'Public research request bound reached', self.now[0] + 86400, 'app_limit', 'candidate')
        self.sources.answers['goodreads'] = spent
        self.passes(1)
        self.assertEqual(self.entry()['record']['next_attempt'], 1000.0 + series_backfill.PASS_WAIT, 'the next pass has a new budget; never a day')


class FailureTests(Fixture):
    def test_an_answer_that_cannot_be_used_is_tried_and_then_given_up(self):
        def ambiguous(*_):
            raise ValueError('Ambiguous series work identities')
        self.sources.answers['wikidata'] = ambiguous
        self.passes(SOURCE_TRIES)
        entry = self.entry()
        self.assertEqual((entry['state'], entry['record']['unreached']), ('none', ['wikidata']))
        self.assertEqual(self.asked('wikidata'), SOURCE_TRIES)

    def test_a_lookup_that_cannot_finish_is_held_after_the_tries(self):
        calls = []

        def broken(manifest, memory=None):
            calls.append(self.now[0]); raise RuntimeError('unexpected')
        self.backfill.lookup = broken
        self.passes(1)
        self.assertEqual((self.entry()['state'], self.entry()['record']['failures'], self.entry()['record']['next_attempt']), ('deferred', 1, 1000.0 + TRY_SPACING))
        self.passes(FAILURE_TRIES + 3)
        entry = self.entry()
        self.assertEqual(entry['state'], 'held')
        self.assertIn('tried %d times' % FAILURE_TRIES, entry['reason'])
        self.assertEqual(len(calls), FAILURE_TRIES, 'held is final: not tried again')

    def test_a_book_deferred_thousands_of_times_before_the_update_gets_one_last_try(self):
        # The live row a2fd5b4c (3,226 deferrals): its last waits, as recorded.
        waits = [{'source': 'www.goodreads.com', 'reason': 'Public source unavailable; no bypass attempted', 'retry_at': 900, 'kind': 'source_unavailable', 'scope': 'host'},
                 {'source': 'api.fantlab.ru', 'reason': LANE_LIMIT_REASON, 'retry_at': 900, 'kind': 'app_limit', 'scope': 'lane'},
                 {'source': 'www.wikidata.org', 'reason': LANE_LIMIT_REASON, 'retry_at': 900, 'kind': 'app_limit', 'scope': 'lane'},
                 {'source': 'html.duckduckgo.com', 'reason': CHALLENGE_REASON, 'retry_at': 900, 'kind': 'source_pause', 'scope': 'host'}]
        self.backfill._set('0', 'deferred', 'closed', {'deferrals': 3226, 'last_attempt': 800, 'next_attempt': 900, 'waits': waits})
        memory = self.backfill._memory(self.entry()['record'])
        self.assertEqual({name: value['tries'] for name, value in memory.items()}, {'goodreads': SOURCE_TRIES - 1, 'publisher': SOURCE_TRIES - 1, 'litres': SOURCE_TRIES - 1},
                         "the app's own limits (FantLab, Wikidata) were never a source's failure")
        unreachable = lambda *_: (_ for _ in ()).throw(ResearchWait('www.goodreads.com', 'Public source unavailable; no bypass attempted', self.now[0] + 300, 'source_unavailable', 'host'))
        self.sources.answers.update(goodreads=unreachable, publisher=human_check(lambda: self.now[0]), litres=human_check(lambda: self.now[0]))
        self.passes(1)
        entry = self.entry()
        # R32: DuckDuckGo's human check is "nothing found" for publisher and Litres (not given up); Goodreads' last try ends it.
        self.assertEqual((entry['state'], entry['record']['unreached']), ('none', ['goodreads']), 'settled in one pass')
        self.assertEqual((entry['record']['sources']['publisher']['answer'], entry['record']['sources']['litres']['answer']), ('none', 'none'))
        self.assertEqual((self.asked('fantlab'), self.asked('wikidata')), (1, 1))
        fresh = self.backfill._memory({'deferrals': 2, 'waits': waits})
        self.assertEqual(fresh, {}, 'a book deferred fewer times starts its tries from the beginning')


class HumanCheckTests(Fixture):
    """Ruling R32 (Sergei 2026-11-23; Futaba's 0.31.0 M2): a source that only answers with a human check (the publisher and
    Litres sources, through DuckDuckGo) counts as "nothing found" at once. Every newly converted book with no series was
    left between tries for 12 hours or more (three tries six hours apart), so "All done" did not show that day. The engine's
    finished state is read from this look-up's real summary (background_work.view, as /api/state sends it)."""

    def finished_state(self):
        from test_background_work import WorkTests, jobs_state
        from test_finished_state_031 import DETAILS, Lookup
        case = WorkTests('test_the_brom_case_names_the_whole_queue_and_every_row_has_its_own_id')
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.engine.series_backfill = Lookup(self.backfill.summary())
        case.engine.gap_fill = Lookup(dict(DETAILS))  # the detail look-up has ended: only this one is asked about
        case.engine.gap_fill.thread = None
        return case.work(jobs_state())['state']

    def test_r32_a_converted_book_with_no_series_is_settled_at_its_first_look_up_and_all_done_shows(self):
        self.sources.answers.update(publisher=human_check(lambda: self.now[0]), litres=human_check(lambda: self.now[0]))
        self.passes(1)
        entry = self.entry()
        self.assertEqual((entry['state'], entry['reason']), ('none', series_backfill.NO_SERIES), 'settled at its first look-up')
        self.assertEqual({name: entry['record']['sources'][name]['answer'] for name in series_backfill.SOURCES}, dict.fromkeys(series_backfill.SOURCES, 'none'))
        self.assertNotIn('next_attempt', entry['record'], 'no six-hour wait')
        value = self.backfill.summary()
        self.assertEqual((value['left'], value['between_tries'], value['next_at']), (0, 0, None))
        self.assertEqual(self.finished_state(), 'all_done', 'All done the same pass (was: background look-ups only for 12 hours or more)')
        self.passes(3, step=TRY_SPACING + 1)
        self.assertEqual((self.asked('publisher'), self.asked('litres')), (1, 1), 'never asked about this book again')

    def test_m1_goodreads_own_human_check_is_nothing_found_at_once_and_all_done_shows(self):
        # 0.31.0 M1 (Futaba's QA round 2): Goodreads answered with its own human check (its web firewall's challenge, read as
        # one by public_research.waf_challenge); the book waited six hours for each of three tries. This test asserted it
        # was a try (R32's control) before M1.
        self.sources.answers.update(goodreads=human_check(lambda: self.now[0], 'www.goodreads.com'))
        self.passes(1)
        entry = self.entry()
        self.assertEqual((entry['state'], entry['record']['sources']['goodreads'].get('answer')), ('none', 'none'), 'nothing found (was: deferred, a try)')
        self.assertNotIn('next_attempt', entry['record'], 'no six-hour wait')
        self.assertEqual(self.finished_state(), 'all_done', 'All done the same pass (was: background look-ups only for 6 hours or more)')
        self.passes(3, step=TRY_SPACING + 1)
        self.assertEqual(self.asked('goodreads'), 1, 'never asked about this book again')

    def test_control_a_human_check_from_another_host_is_still_a_try(self):
        self.sources.answers.update(fantlab=human_check(lambda: self.now[0], 'api.fantlab.ru'))
        self.passes(1)
        self.assertEqual((self.entry()['state'], self.entry()['record']['next_attempt']), ('deferred', 1000.0 + TRY_SPACING))
        self.assertEqual(self.finished_state(), 'background_only')

    def test_control_goodreads_not_answering_is_still_a_try(self):
        self.sources.answers.update(goodreads=unavailable(lambda: self.now[0], 'www.goodreads.com'))
        self.passes(1)
        self.assertEqual((self.entry()['state'], self.entry()['record']['sources']['goodreads']['tries']), ('deferred', 1))
        self.assertEqual(self.finished_state(), 'background_only')

    def test_control_duckduckgo_not_answering_is_still_a_try(self):
        self.sources.answers.update(publisher=unavailable(lambda: self.now[0]))
        self.passes(1)
        self.assertEqual((self.entry()['state'], self.entry()['record']['sources']['publisher']['tries']), ('deferred', 1))
        self.assertEqual(self.finished_state(), 'background_only')


class BlockedCleanupTests(Fixture):
    def setUp(self):
        super().setUp()
        del self.backfill.unsafe  # the real check
        self.backfill.merge.publications = None
        self.backfill.merge.jobs = SimpleNamespace(status=lambda: {'jobs': []})
        with connect(self.db) as db:
            db.execute('CREATE TABLE storage_cleanup_jobs(job_id TEXT PRIMARY KEY,output_hash TEXT,state TEXT,reason TEXT,updated TEXT)')
            db.execute('CREATE TABLE source_folder_cleanup_jobs(job_id TEXT PRIMARY KEY,output_hash TEXT,state TEXT,reason TEXT,updated TEXT)')
            db.execute("INSERT INTO storage_cleanup_jobs VALUES('0','','completed','','')")
            db.execute("INSERT INTO source_folder_cleanup_jobs VALUES('0','','needs_attention','A folder could not be removed','')")
            output = json.dumps({'validation': {'profile': __import__('encoding_policy').AUTOMATIC_PROFILE}})
            db.execute('UPDATE audio_jobs SET output=?', (output,))

    def folder_cleanup(self, state):
        with connect(self.db) as db:
            db.execute("UPDATE source_folder_cleanup_jobs SET state=? WHERE job_id='0'", (state,))

    def test_a_book_whose_cleanup_is_on_hold_is_blocked_not_deferred_without_end(self):
        self.passes(1)
        entry = self.entry()
        self.assertEqual((entry['state'], entry['reason']), ('blocked', series_backfill.BLOCKED))
        self.assertEqual(self.sources.asked, [], 'no source is asked for a book that cannot be changed yet')
        for _ in range(50):
            self.now[0] += 600
            self.backfill.run_pass()
        self.assertEqual(self.entry()['record'].get('deferrals', 0), 0, 'it was deferred every ten minutes, 3,287 times on the live copy')
        self.assertEqual(self.backfill.candidates(), [], 'out of the pass while the hold lasts')
        self.assertEqual((self.backfill.summary()['blocked'], self.backfill.summary()['left']), (1, 0), 'not counted as a look-up that is left')
        # The cleanup finishes (Sergei answered it): the book is looked up at the next pass.
        self.folder_cleanup('completed')
        self.assertEqual([row['job_id'] for row in self.backfill.candidates()], ['0'])
        self.passes(1, step=600)
        self.assertEqual(self.entry()['state'], 'none')
        self.assertEqual(self.asked('goodreads'), 1)

    def test_a_cleanup_still_running_waits_as_before(self):
        self.folder_cleanup('removing')
        self.passes(1)
        self.assertEqual((self.entry()['state'], self.entry()['reason']), ('deferred', 'Its cleanup is not finished yet'))


class SummaryTests(Fixture):
    TITLES = ('Тёмный лес', 'Вечная жизнь Смерти', 'Задача трёх тел', 'Шаровая молния')

    def test_counts_of_the_whole_lookup(self):
        self.assertEqual((self.backfill.summary()['known'], self.backfill.summary()['left'], self.backfill.summary()['total']), (False, None, None),
                         'before the first pass the books not visited are not known: never guessed, never 0')
        found = {'provider': 'fantlab', 'name': 'Память о прошлом Земли', 'number': '3', 'source_url': 'https://fantlab.ru/work1'}
        self.sources.answers['fantlab'] = lambda title, *a: found if title == 'Вечная жизнь Смерти' else None
        self.sources.answers['litres'] = lambda title, *a: unavailable(lambda: self.now[0])() if title == 'Задача трёх тел' else None
        self.assertEqual(len(self.backfill.candidates()), 4)
        counted = self.backfill.summary()
        self.assertEqual((counted['known'], counted['left'], counted['to_look_up'], counted['done'], counted['total']), (True, 4, 4, 0, 4))
        self.passes(1)
        value = self.backfill.summary()
        self.assertEqual({key: value[key] for key in ('left', 'to_look_up', 'between_tries', 'with_series', 'without', 'gave_up', 'done', 'total')},
                         {'left': 1, 'to_look_up': 0, 'between_tries': 1, 'with_series': 1, 'without': 2, 'gave_up': 0, 'done': 3, 'total': 4})
        self.assertEqual(value['next_at'], 1000.0 + TRY_SPACING)
        self.assertEqual(value['tries'], {'per_source': SOURCE_TRIES, 'spacing_seconds': TRY_SPACING, 'failures': FAILURE_TRIES})
        self.passes(SOURCE_TRIES)
        ended = self.backfill.summary()
        self.assertEqual((ended['left'], ended['between_tries'], ended['gave_up'], ended['done'], ended['total'], ended['next_at']), (0, 0, 1, 4, 4, None),
                         'the look-up has ended: nothing is left')

    def test_a_series_found_that_waits_for_approval_or_for_the_queue(self):
        self.passes(1)
        # A series 0.31.0's look-up judged (series_proof's number_from); one kept before that rule is looked up again (M3).
        self.backfill._set('0', 'held', series_backfill.MOVE_WAITS, {'series': 'Память о прошлом Земли', 'number': '2', 'series_proof': {'number_from': 'source'}})
        self.backfill._set('1', 'deferred', 'A book is being converted or cleaned up', {'found': {'name': 'S', 'number': '1'}, 'next_attempt': self.now[0] + 60})
        self.backfill._set('2', 'held', 'The book changed since you approved its move; nothing was changed', {'move_approved': True, 'approved_failed': {'reason': 'x'}})
        value = self.backfill.summary()
        self.assertEqual((value['moves_waiting'], value['write_waiting'], value['writes'], value['left']), (2, 1, ['1'], 0))
        # Third round (R18, R19; Judy 2.1 and 3.2): a series found and not applied is settled for the look-up (its bar ends
        # at the total); only a write that still has to run is left of the total.
        total = value['total']
        self.assertEqual((value['done'], total - value['done']), (value['settled'] + 2, 1), 'the two found books count as done; the write that waits does not')
        self.assertIs(value['applies_by_itself'], False, 'the guard is at hold: the page says a found series is recorded, nothing renamed or moved')

    def test_a_book_that_finishes_converting_makes_the_count_unknown_until_it_is_counted(self):
        self.passes(1)
        self.assertTrue(self.backfill.summary()['known'])
        with connect(self.db) as db:
            manifest = {'candidate_id': 'book-new', 'metadata': {'title': 'Новая', 'canonical_author': 'Cixin Liu', 'series': ''}}
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?)', ('9', json.dumps(manifest, ensure_ascii=False), '{}', 'completed', '9', '9'))
        self.assertEqual((self.backfill.summary()['known'], self.backfill.summary()['left']), (False, None))
        self.backfill.candidates()
        self.assertEqual((self.backfill.summary()['known'], self.backfill.summary()['left']), (True, 1))

    def test_the_rows_bar_is_the_whole_lookup_not_one_pass(self):
        self.passes(1)  # all four settled
        with connect(self.db) as db:
            manifest = {'candidate_id': 'book-new', 'metadata': {'title': 'Новая', 'canonical_author': 'Cixin Liu', 'series': ''}}
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?)', ('9', json.dumps(manifest, ensure_ascii=False), '{}', 'completed', '9', '9'))
        seen = []
        self.sources.answers['goodreads'] = lambda *a: seen.append(self.backfill.status())
        self.now[0] += 600
        self.backfill.run_pass()
        self.assertEqual([(s['title'], s['done'], s['total'], s['pass_done'], s['pass_total'], s['step'], s['pacing']) for s in seen],
                         [('Новая', 4, 5, 0, 1, 'looking up', False)], 'was "0 of 1 books" every pass')
        self.backfill._pacing(6.1)
        self.backfill.progress = {'title': 'Новая', 'done': 0, 'total': 1, 'step': 'looking up'}
        self.assertTrue(self.backfill.status()['pacing'], 'only waiting for a site\'s pacing')
        self.backfill._pacing(0)
        self.assertFalse(self.backfill.status()['pacing'])


if __name__ == '__main__':
    unittest.main()
