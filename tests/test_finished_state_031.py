"""0.31.0 step 4b and 4c (Sergei 2026-11-22: "How do I know that the app finished its queue and has nothing to do anymore?").

/api/state 'work' gains one finished-state value per poll, the counts behind it, the two background look-ups' own numbers
and plain facts per kind of work (Judy's BooksArranger_0.31.0_UX.md, table 1.1 and Notes for Ender). The engine's state is
given as the fields MergeService.live_state() produces; the look-ups are stand-ins with the real summary() shape."""
import unittest
from types import SimpleNamespace

import background_work
from background_work import KIND_FACTS, STATES, finished_state, view
from test_background_work import Engine, WorkTests, jobs_state

SERIES = {'known': True, 'left': 0, 'to_look_up': 0, 'between_tries': 0, 'next_at': None, 'write_waiting': 0, 'writes': [], 'writing': 0, 'moves_waiting': 0,
          'blocked': 0, 'settled': 903, 'with_series': 87, 'without': 700, 'gave_up': 46, 'left_alone': 70, 'done': 903, 'total': 903,
          'tries': {'per_source': 3, 'spacing_seconds': 21600, 'failures': 3}}
DETAILS = {'known': True, 'left': 0, 'to_look_up': 0, 'between_tries': 0, 'next_at': None, 'done': 407, 'total': 407, 'found': 199, 'none': 208, 'tries': None}


class Lookup:
    def __init__(self, value):
        self.value = value

    def summary(self):
        return dict(self.value)


class FinishedStateTests(WorkTests):
    """The table of Judy's 1.1, one case per state, each next to the fact that moves it."""

    def lookups(self, series=None, details=None):
        self.engine.series_backfill = Lookup(dict(SERIES, **(series or {})))
        self.engine.gap_fill = Lookup(dict(DETAILS, **(details or {})))
        self.engine.gap_fill.thread = None

    def state(self, jobs=None, **more):
        work = self.work(jobs or jobs_state(), **more)
        self.assertIn(work['state'], STATES)
        self.assertEqual(work['pending']['any'], work['state'] != 'all_done')
        return work

    def test_all_done_only_when_nothing_at_all_is_pending(self):
        self.lookups()
        work = self.state()
        self.assertEqual((work['state'], work['rows'], work['waiting'], work['waits_for_you']), ('all_done', [], [], []))
        self.assertEqual(work['pending'], {'any': False, 'running': 0, 'paused': 0, 'waiting': 0, 'still_checking': 0, 'attention': 0, 'hold': 0, 'moves': 0,
                                           'drives': 0, 'lookups': {'series': 0, 'details': 0, 'all': 0}, 'same_name': 0})

    def test_each_thing_that_is_pending_gives_another_state(self):
        self.lookups()
        converting = jobs_state(state='Running', current_job_id='job-a', current_book_id='book-a', current_title='Дюна', progress={'phase': 'encoding'})
        cases = [
            ('working', dict(jobs=converting)),
            ('paused', dict(jobs=jobs_state(state='Paused', queued=1, queued_conversions=1))),
            ('continues', dict(jobs=jobs_state(state='Completed', queued=1, queued_conversions=1))),
            ('continues', dict(jobs=jobs_state(todo_still_checking=3))),
            ('continues', dict(jobs=jobs_state(timed_retry=True))),
            ('continues', dict(automatic={'state': 'Idle', 'start_pending': True})),
            ('continues', dict(queue={'queued_actions': [{'id': 'q1', 'action': 'approve', 'book_id': 'book-b', 'title': 'Оно', 'position': 1, 'blocker': None}], 'queue_running': None})),
            ('waiting_for_you', dict(jobs=jobs_state(attention_counts={'all': 2, 'name_taken': 1, 'stopped': 1}))),
            ('waiting_for_you', dict(jobs=jobs_state(attention_row={'title': 'Оно', 'held_total': 2}))),
            ('waiting_for_you', dict(roots=[{'path': 'Z:\\Audiobooks', 'available': False}])),
        ]
        for expected, arguments in cases:
            with self.subTest(expected=expected, arguments=sorted(arguments)):
                self.assertEqual(self.state(**arguments)['state'], expected)
        self.assertEqual(self.state()['state'], 'all_done', 'positive control: the same engine with none of them')

    def test_a_series_move_to_approve_waits_for_him(self):
        self.lookups(series={'moves_waiting': 55})
        work = self.state()
        self.assertEqual((work['state'], work['waits_for_you'], work['pending']['moves']), ('waiting_for_you', ['moves'], 55))

    def test_a_lookup_between_tries_is_background_only_and_shows_in_the_waiting_list(self):
        self.lookups(series={'left': 212, 'between_tries': 212, 'next_at': 1795343400.0, 'done': 691, 'total': 903}, details={'left': 31, 'between_tries': 31, 'next_at': 1795343460.0})
        work = self.state()
        self.assertEqual(work['state'], 'background_only')
        self.assertEqual(work['pending']['lookups'], {'series': 212, 'details': 31, 'all': 243})
        self.assertEqual([(item['kind'], item['count'], item['at']) for item in work['lookups_waiting']],
                         [('series_lookup', 212, 1795343400000), ('detail_lookup', 31, 1795343460000)])
        for item in work['lookups_waiting']:
            self.assertEqual(tuple(item), background_work.ITEM_KEYS, 'the Waiting list item shape')
        self.assertEqual(work['waiting'], [], 'the 0.30.0 page has no words for them: its Waiting list is drawn as before')
        self.assertEqual(work['pending']['waiting'], 0, 'the look-ups are not main work: nothing "continues by itself"')
        self.assertEqual((work['background']['series']['done'], work['background']['series']['total'], work['background']['series']['tries']['per_source']), (691, 903, 3))
        # Both at once: his action wins the badge; the look-ups stay counted.
        both = self.state(jobs=jobs_state(attention_counts={'stopped': 1}))
        self.assertEqual((both['state'], both['pending']['lookups']['all']), ('waiting_for_you', 243))

    def test_books_still_to_look_up_with_no_row_yet_are_not_all_done(self):
        self.lookups(series={'left': 4, 'to_look_up': 4})
        self.assertEqual(self.state()['state'], 'background_only', 'due at the next pass: the look-up has not ended')

    def test_a_running_lookup_row_alone_is_background_only(self):
        self.lookups(series={'left': 1, 'to_look_up': 1, 'done': 902, 'total': 903})
        row = {'title': 'Тёмный лес', 'done': 902, 'total': 903, 'step': 'looking up', 'pass_done': 0, 'pass_total': 1, 'pacing': False}
        work = self.state(jobs=jobs_state(series_update=row))
        self.assertEqual((work['state'], [(r['kind'], r['done'], r['total']) for r in work['rows']]), ('background_only', [('series', 902, 903)]))
        self.assertEqual(work['pending']['running'], 0, 'a look-up row is not main work')
        paced = self.state(jobs=jobs_state(series_update=dict(row, pacing=True)))
        self.assertEqual((paced['state'], paced['rows']), ('background_only', []), "only waiting for a site's pacing: no running row")

    def test_a_series_write_held_by_a_job_is_a_waiting_item_with_the_blocker(self):
        self.lookups(series={'write_waiting': 1, 'writes': ['job-c']})
        converting = jobs_state(state='Running', current_job_id='job-a', current_book_id='book-a', current_title='Дюна', progress={'phase': 'encoding'})
        work = self.state(jobs=converting)
        self.assertNotIn('series_write', [item['kind'] for item in work['waiting']])
        item = next(item for item in work['lookups_waiting'] if item['kind'] == 'series_write')
        self.assertEqual((item['subject'], item['book_id'], item['job_id']), ('Оно', 'book-c', 'job-c'))
        self.assertEqual(item['blocker'], {'kind': 'jobs', 'cause': 'conversion', 'title': 'Дюна', 'book_id': 'book-a', 'count': None})
        self.assertEqual(self.state()['state'], 'background_only', 'with nothing else running it is still a look-up that is left')

    def test_not_known_is_never_all_done(self):
        self.lookups(series={'known': False, 'left': None, 'to_look_up': None, 'total': None})
        work = self.state()
        self.assertEqual((work['state'], work['pending']['lookups']), ('unknown', {'series': None, 'details': 0, 'all': None}), 'before the first pass has counted')
        self.lookups()
        self.engine.gap_fill = SimpleNamespace(summary=lambda: 1 / 0, thread=None)
        unread = self.state()
        self.assertEqual((unread['state'], unread['unread']), ('unknown', ['lookups']))

    def test_an_engine_without_the_lookups_reports_none_and_can_be_all_done(self):
        work = self.state()
        self.assertEqual((work['state'], work['background'], work['lookups_waiting'], work['pending']['lookups']),
                         ('all_done', {}, [], {'series': 0, 'details': 0, 'all': 0}))

    def test_same_name_rows_are_counted(self):
        self.lookups()
        work = self.state(jobs=jobs_state(attention_counts={'name_taken': 2}, same_name_total=2))
        self.assertEqual((work['state'], work['pending']['same_name'], work['pending']['attention']), ('waiting_for_you', 2, 2))


class KindFactsTests(unittest.TestCase):
    """4c: plain facts per kind of work, so the page never guesses."""

    def test_every_row_and_waiting_kind_has_its_facts(self):
        for kind in background_work.KINDS + background_work.WAITING_KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(sorted(KIND_FACTS[kind]), ['about', 'background', 'writes_finished_files'])
                self.assertIn(KIND_FACTS[kind]['about'], ('new', 'finished', 'approved', 'any'))

    def test_the_two_background_lookups_and_what_they_write(self):
        self.assertEqual(sorted(kind for kind, fact in KIND_FACTS.items() if fact['background']), sorted(background_work.BACKGROUND_KINDS))
        self.assertEqual(KIND_FACTS['series'], {'background': True, 'about': 'finished', 'writes_finished_files': True})
        self.assertEqual(KIND_FACTS['series_lookup'], {'background': True, 'about': 'finished', 'writes_finished_files': False}, 'between tries nothing is written')
        self.assertEqual(KIND_FACTS['gap_fill'], {'background': True, 'about': 'approved', 'writes_finished_files': False})
        self.assertEqual(KIND_FACTS['research'], {'background': False, 'about': 'new', 'writes_finished_files': False})

    def test_the_waiting_list_orders_the_lookups_before_drives(self):
        order = background_work.WAITING_KINDS
        self.assertLess(order.index('metadata_sources'), order.index('series_lookup'))
        self.assertLess(order.index('series_write'), order.index('drive'))

    def test_the_schema_name_is_unchanged_and_the_old_keys_are_all_there(self):
        work = view(SimpleNamespace(merge=SimpleNamespace(), active_library=None), jobs_state(), {'state': 'Idle'}, {'queued_actions': [], 'queue_running': None}, False, None)
        self.assertEqual(work['schema'], 'books-work-v1')
        self.assertLessEqual({'rows', 'waiting', 'counts', 'snapshot_age_ms', 'refreshing', 'unread'}, set(work))
        self.assertEqual(sorted(set(work) - {'schema', 'rows', 'waiting', 'counts', 'snapshot_age_ms', 'refreshing', 'unread'}),
                         ['background', 'kinds', 'lookups_waiting', 'pending', 'state', 'waits_for_you'], 'the keys 0.31.0 adds')


del WorkTests  # only its fixture is reused; its own cases run in test_background_work

if __name__ == '__main__':
    unittest.main()
