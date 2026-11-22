"""0.31.0 steps 2 and 3 (Sergei 2026-11-22, rulings R1-R5, R18, R21-R23, R25): the look-up before review, Wikidata as a
working source, the one certain-or-doubtful rule, the one title rule and the order of a Latin author name.

No network. tests/lookup_fixture_031.json holds the recorded answers of Wikidata and FantLab for ten books (reduced to the
fields the adapters read; recorded 2026-11-22 through the app's own adapters, so every URL is the one the app asks):
the two Sprawl books, «Тёмный лес» (Liu Cixin, a Chinese original), «Метро 2034» and «Гибель богов» (Russian originals with
a FantLab cycle; the first points at a universe on Wikidata, the second has no English title), «Оно» (a common word),
«Стража! Стража!» (two series on one book), «Автостопом по галактике» (the author's English name only under "mul"),
«Ночной дозор» and «Крещение огнём» (FantLab and Wikidata number it differently)."""
import contextlib
import json
import sqlite3
import tempfile
import threading
import unittest
import unittest.mock
import urllib.error
import urllib.parse
from pathlib import Path
from types import SimpleNamespace

import author_rules
import canonical_names
import gap_fill
import metadata_choices
import public_research
import series_certainty
import wikidata_books
from local_identity import title_key
from public_research import PublicClient, PublicResearch, ResearchWait, _name_matches, _people
from test_folder_structure import AREA, Base, ROOT, SORTED, file_row

FIXTURE = json.loads(Path(__file__).with_name('lookup_fixture_031.json').read_text(encoding='utf-8'))
ENTITIES = {key: value for answer in FIXTURE.values() if isinstance(answer, dict) and 'entities' in answer for key, value in answer['entities'].items()}


class Stop:
    def is_set(self):
        return False

    def wait(self, seconds):
        return False


def fetcher(closed=(), calls=None, missing=None):
    """A PublicClient fetch that answers from the recorded fixture. Goodreads knows nothing; a host in closed asks for a
    pause; a Wikidata or FantLab URL that was not recorded is noted in missing (a test asserts it stays empty)."""
    def fetch(url, *_):
        if calls is not None:
            calls.append(url)
        host = urllib.parse.urlsplit(url).hostname
        if host in closed:
            raise urllib.error.HTTPError(url, 429, 'private fixture', {'Retry-After': '3600'}, None)
        if url in FIXTURE:
            return json.dumps(FIXTURE[url], ensure_ascii=False).encode('utf-8')
        if host == 'www.goodreads.com':
            return b'<html></html>'
        if host == 'api.fantlab.ru' and '/search-works' in url:
            return b'[]'
        if host == 'www.wikidata.org' and 'wbsearchentities' in url:
            return b'{"search":[]}'
        if missing is not None:
            missing.append(url)
        raise ValueError('not in the recorded fixture')
    return fetch


def recorded(test, closed=()):
    """(research, calls, missing) over a private catalog; the clock moves a minute at every read, so no pacing waits."""
    temp = tempfile.TemporaryDirectory(dir=AREA)
    test.addCleanup(temp.cleanup)
    calls, missing = [], []
    minutes = iter(range(10 ** 6, 10 ** 9, 60))
    client = PublicClient(Path(temp.name) / 'research.sqlite3', fetch=fetcher(closed, calls, missing), clock=lambda: next(minutes))
    return PublicResearch(client, leads=[]), calls, missing


def asked(gaps, **more):
    return dict({'gaps': list(gaps), 'fields': {'author': {'partial': False}}, 'skip': ('publisher', 'litres')}, **more)


def wikidata(title, author):
    """wikidata_books.book over the recorded answers, as PublicResearch._wikidata_book asks."""
    found = wikidata_books.search_ids(FIXTURE[wikidata_books.search_url(title)])
    candidates = wikidata_books.entities(FIXTURE[wikidata_books.entities_url(found)], found)
    exact = {key: entity for key, entity in candidates.items() if title_key(title) in {title_key(name) for name in wikidata_books.names(entity)}}
    links = wikidata_books.related_ids(exact.values())
    related = wikidata_books.entities(FIXTURE[wikidata_books.entities_url(links)], links)
    return wikidata_books.book(exact, related, title, author, title_key, _name_matches, _people), found, exact


class WikidataMatchTests(unittest.TestCase):
    """A match needs the title, every credited author and "is a written work": never the title alone (Makoto's findings)."""

    def test_the_dark_forest_gives_the_english_title_the_language_the_author_and_the_series(self):
        record, found, _ = wikidata('Тёмный лес', 'Лю Цысинь')
        self.assertGreater(len(found), 1, 'positive control: the search alone returns several items with this name')
        self.assertEqual((record['work_id'], record['english_title'], record['language']), ('Q607276', 'The Dark Forest', 'zh'))
        self.assertEqual(record['authors'][0]['name_en'], 'Liu Cixin')
        series = wikidata_books.series(record)
        self.assertEqual((series['name'], series['number'], series.get('doubt')), ("Remembrance of Earth's Past", '2', None))

    def test_the_title_alone_never_matches(self):
        for title, author in (('Оно', 'Дин Кунц'), ('Тёмный лес', 'Уильям Гибсон'), ('Граф Ноль', 'Стивен Кинг')):
            with self.subTest(title=title, author=author):
                record, found, exact = wikidata(title, author)
                self.assertTrue(exact, 'positive control: items with this very name exist')
                self.assertIsNone(record, 'another author: no match')

    def test_a_common_word_finds_the_novel_among_its_namesakes(self):
        record, found, exact = wikidata('Оно', 'Стивен Кинг')
        self.assertGreater(len(exact), 1, 'positive control: several items are named «Оно»')
        self.assertEqual((record['work_id'], record['english_title'], record['language']), ('Q602288', 'It', 'en'))
        self.assertIsNone(wikidata_books.series(record), 'a standalone novel: no series')

    def test_an_english_name_under_the_mul_label_is_read(self):
        adams = ENTITIES['Q42']
        self.assertNotIn('en', adams['labels'], 'positive control: Douglas Adams has no English label of his own')
        self.assertEqual(wikidata_books.english(adams), 'Douglas Adams')
        record, _, _ = wikidata('Автостопом по галактике', 'Дуглас Адамс')
        self.assertEqual((record['authors'][0]['name_en'], record['english_title']), ('Douglas Adams', "The Hitchhiker's Guide to the Galaxy"))

    def test_two_series_on_one_book_and_a_universe_are_doubtful_shapes(self):
        guards = wikidata_books.series(wikidata('Стража! Стража!', 'Терри Пратчетт')[0])
        self.assertEqual((guards['doubt'], len(guards['series_ids'])), ('several_series', 2))
        metro = wikidata_books.series(wikidata('Метро 2034', 'Дмитрий Глуховский')[0])
        self.assertEqual((metro['doubt'], metro['name']), ('universe', 'Вселенная Метро 2033'))

    def test_a_book_with_no_english_title_says_so(self):
        record, _, _ = wikidata('Гибель богов', 'Ник Перумов')
        self.assertEqual((record['language'], record['english_title']), ('ru', ''))

    def test_the_family_name_field_orders_a_name_the_app_cannot(self):
        record, _, _ = wikidata('Тёмный лес', 'Лю Цысинь')
        author = record['authors'][0]
        self.assertTrue(author['family_ids'], 'the person carries a family name (P734)')
        order = wikidata_books.name_order(author, ENTITIES)
        self.assertEqual(order['family'], 'Liu')


class CertaintyTests(unittest.TestCase):
    """The one rule (series_certainty.judge): certain, or doubtful and so treated as not found."""
    FOUND = {'provider': 'fantlab', 'name': 'Колесо Времени', 'number': '3', 'number_from': 'counted', 'source_url': 'https://fantlab.ru/work1'}

    def verdict(self, candidate, local=None, others=()):
        answer = series_certainty.judge(candidate, local, others)
        return answer['verdict'], answer['why'], (answer['series'] or {}).get('number'), answer['number_from']

    def test_one_source_with_a_number_is_certain_whether_given_or_counted(self):
        self.assertEqual(self.verdict(self.FOUND), ('certain', '', '3', 'counted'))  # R21: FantLab alone, a counted number
        self.assertEqual(self.verdict(dict(self.FOUND, provider='wikidata', number_from='source')), ('certain', '', '3', 'source'))

    def test_the_number_may_come_from_the_books_own_names(self):
        unnumbered = dict(self.FOUND, number='', number_from='')
        self.assertEqual(self.verdict(unnumbered, {'hint': {'series': 'Колесо времени', 'number': '03'}}), ('certain', '', '3', 'names'))
        self.assertEqual(self.verdict(unnumbered, {'volume': 2}), ('certain', '', '2', 'names'))
        self.assertEqual(self.verdict(unnumbered, {'series': 'Колесо времени', 'number': '3'}), ('certain', '', '3', 'tags'))
        self.assertEqual(self.verdict(unnumbered)[:2], ('doubtful', 'no_number'))

    def test_the_doubtful_shapes(self):
        cases = ((dict(self.FOUND, doubt='several_series'), None, (), 'several_series'),
                 (dict(self.FOUND, doubt='universe'), None, (), 'universe'),
                 (dict(self.FOUND, doubt='source_conflict'), None, (), 'source_conflict'),
                 (self.FOUND, {'volume': 1}, (), 'number_mismatch'),
                 (self.FOUND, {'hint': {'series': 'Колесо времени', 'number': '5'}}, (), 'number_mismatch'),
                 (self.FOUND, {'hint': {'series': 'Ведьмак', 'number': '3'}}, (), 'contradicts_local'),
                 (self.FOUND, {'series': 'Меч Истины', 'number': '3'}, (), 'contradicts_local'),
                 (self.FOUND, {'series': 'Колесо времени', 'number': '4'}, (), 'contradicts_local'),
                 (self.FOUND, None, [{'provider': 'wikidata', 'number': '5'}], 'sources_disagree'))
        for candidate, local, others, why in cases:
            with self.subTest(why=why, local=local):
                answer = series_certainty.judge(candidate, local, others)
                self.assertEqual((answer['verdict'], answer['why'], answer['series']), ('doubtful', why, None))
                self.assertEqual(series_certainty.dropped(answer)['why'], why)

    def test_names_in_two_alphabets_do_not_contradict_and_a_shorter_name_agrees(self):
        self.assertEqual(self.verdict(dict(self.FOUND, name='The Wheel of Time'), {'hint': {'series': 'Колесо времени', 'number': '3'}})[0], 'certain')
        self.assertTrue(series_certainty.names_agree('Sprawl', 'Sprawl Trilogy'))
        self.assertFalse(series_certainty.names_agree('Колесо времени', 'Меч Истины'))


class TitleRuleTests(unittest.TestCase):
    """R1 and R3 in one place (canonical_names.book_title), and the same rule for a series' name."""

    def test_the_title_rule(self):
        rule = canonical_names.book_title
        self.assertEqual(rule('Метро 2034', {'language': 'ru', 'title_native': 'Метро 2034', 'english_title': 'Metro 2034'}), ('Метро 2034', 'russian_original'))
        self.assertEqual(rule('Тёмный лес', {'language': 'zh', 'original_title': '黑暗森林', 'english_title': 'The Dark Forest'}), ('The Dark Forest', 'english'))
        self.assertEqual(rule('Граф Ноль', {'language': 'en', 'original_title': 'Count Zero'}), ('Count Zero', 'english'))
        self.assertEqual(rule('Крещение огнём', {'language': 'pl', 'original_title': 'Chrzest ognia'}), ('Крещение огнём', 'no_english_title'), 'R3: kept, nobody asked')
        self.assertEqual(rule('Тёмный лес', {}), ('Тёмный лес', 'unknown_language'))
        self.assertEqual(rule('Мой заголовок', {'language': 'zh', 'english_title': 'The Dark Forest'}, his=True), ('Мой заголовок', 'his'))

    def test_the_series_name_rule(self):
        name = canonical_names.series_name
        fantlab = {'name': 'В память о прошлом Земли', 'name_russian': 'В память о прошлом Земли'}
        self.assertEqual(name(dict(fantlab, name_english="Remembrance of Earth's Past"), 'zh'), ("Remembrance of Earth's Past", 'english'))
        self.assertEqual(name(fantlab, 'zh'), ('В память о прошлом Земли', 'no_english_name'), 'no English name found: the name the source gives')
        self.assertEqual(name({'name': 'Wiedźmin', 'name_russian': 'Ведьмак Геральт'}, 'pl'), ('Wiedźmin', 'english'), '0.30.0 item 6: the Latin original name')
        self.assertEqual(name({'name': 'МЕТРО', 'name_russian': 'МЕТРО', 'name_english': 'Metro'}, 'ru'), ('МЕТРО', 'russian_original'))
        self.assertEqual(name(fantlab, ''), ('В память о прошлом Земли', 'unknown_language'))


class AuthorOrderTests(unittest.TestCase):
    """A Latin name is turned around only on evidence; with none it stays as the source writes it (R23: and nobody is asked)."""

    def test_liu_cixin_stays_as_the_sources_spell_him(self):
        order = canonical_names.latin_order
        self.assertEqual(order('Liu Cixin', 'Лю Цысинь', {'family': 'Liu'})[0], 'Liu Cixin')
        self.assertEqual(order('Liu Cixin', 'Лю Цысинь', {'language': 'zh'})[0], 'Liu Cixin')
        self.assertEqual(order('Liu Cixin', 'Лю Цысинь')[0], 'Liu Cixin', 'the credit is surname first, and «Лю» is "Liu"')
        self.assertEqual(order('Cixin Liu', '', {'family': 'Liu'})[0], 'Liu Cixin', 'the family-name field moves it to the front')
        self.assertEqual(public_research._latin_surname_first('Liu Cixin', 'Лю Цысинь'), 'Liu Cixin', 'it was "Cixin Liu" until 0.31.0')

    def test_the_evidence_that_still_turns_a_name_around(self):
        order = canonical_names.latin_order
        self.assertEqual(order('Lev Grossman', 'Лев Гроссман')[0], 'Grossman Lev', 'the credit shows which word is the surname')
        self.assertEqual(order('William Gibson')[0], 'Gibson William', 'a first name the app knows')
        self.assertEqual(order('Haruki Murakami', '', {'family': 'Murakami'})[0], 'Murakami Haruki')
        self.assertEqual(order('Tolkien J. R. R.')[0], 'Tolkien J. R. R.', 'a name ending in initials is surname first already')

    def test_without_evidence_the_name_is_kept_and_no_question_exists_for_it(self):
        name, why = canonical_names.latin_order('Haruki Murakami', 'Харуки Мураками')
        self.assertEqual((name, why), ('Haruki Murakami', canonical_names.ORDER_UNKNOWN))
        import local_identity
        self.assertIsNone(local_identity.odd_identity('Норвежский лес', 'Haruki Murakami'), 'R23: nothing asks about the order')

    def test_a_rules_own_target_wins_over_a_stale_order_the_library_still_files(self):
        rules = author_rules.Rules([{'rule_id': 'r2', 'kind': 'same_as', 'credit_key': author_rules.key('Лю Цысинь'), 'credit_as_seen': 'Лю Цысинь', 'target': 'Liu Cixin',
                                     'scope': '', 'options': '{}', 'actor': 'assistant', 'source': 'x', 'question': '', 'saved_utc': '2026-11-22T00:00:00+00:00'}],
                                   known_authors=['Cixin Liu', 'Cixin Liu'])
        self.assertEqual(canonical_names.author('Liu Cixin', rules)[0], 'Liu Cixin', 'two finished books under "Cixin Liu" do not undo the rule')


class LookupTests(unittest.TestCase):
    """PublicResearch._gap_fill over the recorded answers: what the look-up before review finds for each book."""

    def fill(self, title, author, gaps=('original_title', 'series'), closed=(), **local):
        research, calls, missing = recorded(self, closed)
        found = research._gap_fill(asked(gaps, **local), title, author, Stop(), {'remaining': 12}, [], lambda *_: None, {'sources': []})
        self.assertEqual(missing, [], 'every request the look-up makes is in the recorded fixture')
        return found, calls

    def test_the_dark_forest(self):
        found, calls = self.fill('Тёмный лес', 'Лю Цысинь')
        catalog, series = found['catalog'], found['series']
        self.assertEqual((catalog['language'], catalog['english_title'], catalog['author_latin']), ('zh', 'The Dark Forest', 'Liu Cixin'))
        self.assertEqual((series['name'], series['number'], series['provider'], series['number_from']), ("Remembrance of Earth's Past", '2', 'fantlab', 'counted'))
        self.assertEqual((series['name_provider'], series['name_rule']), ('wikidata', 'english'), 'the English name is Wikidata\'s, the series and number FantLab\'s')
        self.assertEqual((found['unfilled'], found['doubtful']), ([], []))
        self.assertLessEqual(len(calls), 8, 'one book: FantLab 3, Goodreads 1, Wikidata 3')

    def test_the_sprawl_books(self):
        for title, english, number in (('Граф Ноль', 'Count Zero', '2'), ('Мона Лиза овердрайв', 'Mona Lisa Overdrive', '3')):
            with self.subTest(title=title):
                found, calls = self.fill(title, 'Уильям Гибсон')
                self.assertEqual((found['catalog']['language'], found['catalog']['english_title']), ('en', english))
                self.assertEqual((found['series']['name'], found['series']['number'], found['series']['provider']), ('Sprawl', number, 'fantlab'))
                self.assertFalse([url for url in calls if 'wikidata' in url], 'FantLab answered everything: Wikidata is not asked')

    def test_a_russian_original_keeps_its_russian_series_from_fantlab_alone(self):
        found, _ = self.fill('Метро 2034', 'Дмитрий Глуховский')
        self.assertEqual((found['catalog']['language'], found['series']['name'], found['series']['number'], found['series']['name_rule']), ('ru', 'МЕТРО', '2', 'russian_original'))
        found, _ = self.fill('Гибель богов', 'Ник Перумов')
        self.assertEqual((found['series']['name'], found['series']['number']), ('Хроники Хьёрварда', '1'))

    def test_wikidata_alone_names_a_series_and_its_number(self):
        found, _ = self.fill('Автостопом по галактике', 'Дуглас Адамс')
        self.assertEqual((found['catalog']['provider'], found['catalog']['english_title']), ('wikidata', "The Hitchhiker's Guide to the Galaxy"))
        self.assertEqual((found['series']['provider'], found['series']['number'], found['series']['number_from']), ('wikidata', '1', 'source'))

    def test_two_series_on_one_book_is_treated_as_not_found(self):
        found, _ = self.fill('Стража! Стража!', 'Терри Пратчетт')
        self.assertNotIn('series', found)
        self.assertEqual([item['why'] for item in found['doubtful']], ['several_series'])
        self.assertEqual(found['catalog']['english_title'], 'Guards! Guards!', 'the title is still Wikidata\'s')

    def test_two_sources_that_number_the_book_differently_are_doubtful(self):
        found, _ = self.fill('Крещение огнём', 'Анджей Сапковский')
        self.assertNotIn('series', found, 'FantLab counts 3, Wikidata says 5: which source wins is not ruled')
        self.assertEqual([(item['why'], item['number']) for item in found['doubtful']], [('sources_disagree', '3 / 5')])
        self.assertEqual(found['catalog']['english_title'], 'Baptism of Fire')

    def test_a_number_the_books_own_title_does_not_give_is_doubtful_and_nothing_of_that_record_is_used(self):
        found, _ = self.fill('Тёмный лес. Книга 3', 'Лю Цысинь')
        self.assertNotIn('series', found)
        self.assertNotIn('catalog', found, 'ruling 74b\'s caution: the record may be another book')
        self.assertIn('number_mismatch', [item['why'] for item in found['doubtful']])
        positive, _ = self.fill('Тёмный лес. Книга 2', 'Лю Цысинь')
        self.assertEqual(positive['series']['number'], '2', 'positive control: the title\'s own number agrees')

    def test_a_name_that_only_looks_like_a_series_is_confirmed_by_a_source_or_dropped(self):
        hint = {'series': 'Память о прошлом Земли', 'number': '2', 'title': 'Тёмный лес', 'whole': 'Память о прошлом Земли 2. Тёмный лес', 'from': 'name'}
        found, _ = self.fill(hint['whole'], 'Лю Цысинь', series_hint=hint)
        self.assertEqual((found.get('split_title'), found['series']['number'], found['series']['name']), ('Тёмный лес', '2', "Remembrance of Earth's Past"))
        wrong, _ = self.fill('Память о прошлом Земли 5. Тёмный лес', 'Лю Цысинь', series_hint=dict(hint, number='5', whole='Память о прошлом Земли 5. Тёмный лес'))
        self.assertNotIn('series', wrong)
        self.assertNotIn('split_title', wrong)
        self.assertNotIn('catalog', wrong, 'nothing of the part after the number is used once its series is dropped')
        self.assertEqual({item['why'] for item in wrong['doubtful']}, {'number_mismatch', 'unconfirmed_name'})

    def test_a_series_the_files_name_gets_its_english_name_from_a_source(self):
        found, _ = self.fill('Тёмный лес', 'Лю Цысинь', gaps=('original_title', 'series_name'), series={'name': 'Память о прошлом Земли', 'number': '2'})
        self.assertEqual(found['series_english'], {'name': "Remembrance of Earth's Past", 'provider': 'wikidata', 'source_url': 'https://www.wikidata.org/wiki/Q607276'})
        other, _ = self.fill('Тёмный лес', 'Лю Цысинь', gaps=('original_title', 'series_name'), series={'name': 'Память о прошлом Земли', 'number': '3'})
        self.assertNotIn('series_english', other, 'the files say book 3, the source book 2: its name is not taken')
        russian, calls = self.fill('Метро 2034', 'Дмитрий Глуховский', gaps=('original_title', 'series_name'), series={'name': 'Метро', 'number': '2'})
        self.assertNotIn('series_english', russian)
        self.assertNotIn('series_name', russian['unfilled'], 'a Russian original: nothing to ask')

    def test_a_closed_wikidata_leaves_the_english_title_of_a_polish_book_waiting(self):
        research, calls, _ = recorded(self, closed=('www.wikidata.org',))
        fantlab = research._gap_fantlab('Крещение огнём', 'Анджей Сапковский', False, Stop(), {'remaining': 6}, {'sources': []})
        self.assertEqual(fantlab['english_title'], 'Baptism of Fire', 'FantLab lists one English title here: nothing waits for Wikidata')
        # A work FantLab names only in its own language: the original-title gap stays open while Wikidata is closed.
        with unittest.mock.patch.object(research, '_gap_fantlab', return_value=dict(fantlab, english_title='')):
            found = research._gap_fill(asked(('original_title',)), 'Крещение огнём', 'Анджей Сапковский', Stop(), {'remaining': 12}, [], lambda *_: None, {'sources': []})
        self.assertEqual((found['unfilled'], found['closed'], found.get('english_pending')), (['original_title'], ['wikidata'], True))


class Scripted:
    """A client whose sources do what the test says: 'closed' (unreachable), 'limited' (the app's own bound), or answer
    nothing. A clock the test moves."""
    def __init__(self, database, mode, now):
        self.database, self.mode, self.now, self.calls = database, mode, now, []

    def clock(self):
        return self.now[0]

    def _answer(self, url, budget=None):
        if isinstance(budget, dict):
            if budget.get('remaining', 1) <= 0:  # the cache only (it holds nothing): no request, as PublicClient.read
                raise ResearchWait('api.fantlab.ru', 'Public research request bound reached', self.now[0] + 86400, 'app_limit', 'candidate')
            budget['remaining'] -= 1
        self.calls.append(url)
        mode = self.mode[0]
        if mode == 'closed':
            raise ResearchWait('api.fantlab.ru', 'Public source unavailable; no bypass attempted', self.now[0] + 300, 'source_unavailable', 'host')
        if mode == 'limited':
            raise ResearchWait('api.fantlab.ru', public_research.APP_LIMIT_REASON, self.now[0] + 1800, 'app_limit', 'host')
        return {'search': []} if 'wikidata' in url else []

    def json(self, url, stop=None, budget=None):
        return self._answer(url, budget)

    def read(self, url, stop=None, budget=None):
        self._answer(url, budget)
        return b''

    def receipt(self, url):
        return {'url': url}


class BoundedTriesTests(unittest.TestCase):
    """R2: a book may wait for the answer, a few tries; then it converts as before. The record says what the page needs."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(temp.cleanup)
        self.now, self.mode = [1_000_000.0], ['closed']
        self.client = Scripted(str(Path(temp.name) / 'research.sqlite3'), self.mode, self.now)
        self.research = PublicResearch(self.client, leads=[])
        self.record = None

    def visit(self, **row):
        _, self.record = self.research._bounded_lookup(dict(row, _lookup=self.record), asked(('original_title', 'series')), 'Тёмный лес', 'Лю Цысинь',
                                                       ['original_title', 'series'], Stop(), lambda *_: None, {'sources': []})
        return self.record

    def test_a_source_that_cannot_be_reached_is_tried_three_times_then_given_up(self):
        from series_backfill import SOURCE_TRIES, TRY_SPACING
        first = self.visit()
        self.assertEqual((first['waiting'], first['tries'], first['next_try'], first['limit']), (True, 1, 2, SOURCE_TRIES), '"Try 2 of 3" is literally true')
        self.assertEqual(first['fields'], {'original_title': 'waiting', 'series': 'waiting'})
        self.assertEqual(first['asking'], ['original_title', 'series'])
        self.assertEqual(first['next_at'], self.now[0] + public_research.LOOKUP_RETRY_MIN, 'the source said five minutes: never sooner than the floor')
        self.assertEqual(first['wait']['retry_at'], first['next_at'])
        asked_before = len(self.client.calls)
        self.now[0] += 60
        early = self.visit()
        self.assertEqual((len(self.client.calls), early['tries']), (asked_before, 1), 'not due yet: nothing is asked, no try is counted')
        self.now[0] = first['next_at'] + 1
        second = self.visit()
        self.assertEqual((second['waiting'], second['tries'], second['next_try']), (True, 2, 3))
        self.now[0] = second['next_at'] + 1
        third = self.visit()
        self.assertEqual((third['waiting'], third['tries'], third['next_at'], third['next_try']), (False, 3, None, None), 'the wait ends: it converts as before')
        self.assertEqual(third['fields'], {'original_title': 'no_answer', 'series': 'no_answer'})
        self.assertLess(third['last_at'] - first['first_at'], TRY_SPACING, 'three tries ten minutes apart, never six hours')
        self.now[0] += 86400
        self.assertEqual(self.visit()['requests'], 0, 'settled: never asked again')

    def test_the_apps_own_limit_is_no_try(self):
        self.mode[0] = 'limited'
        first = self.visit()
        self.assertEqual((first['waiting'], first['tries'], first['next_try']), (True, 0, 1), 'it waits for the limit; try 1 is still ahead')
        self.assertEqual(first['next_at'], self.now[0] + 1800, 'when the bound reopens')

    def test_sources_that_answer_nothing_never_make_the_book_wait(self):
        self.mode[0] = 'nothing'
        record = self.visit()
        self.assertEqual((record['waiting'], record['fields']), (False, {'original_title': 'nothing_found', 'series': 'nothing_found'}))

    def test_no_book_waits_longer_than_the_cap(self):
        self.mode[0] = 'limited'
        first = self.visit()
        self.assertEqual(first['until'], first['first_at'] + public_research.LOOKUP_MAX_WAIT)
        self.now[0] = first['until'] + 1
        late = self.visit()
        self.assertEqual((late['waiting'], late['ended'], late['fields']['series']), (False, 'time', 'no_answer'))

    def test_a_book_that_waited_three_times_under_the_old_rule_goes_on(self):
        record = self.visit(_series_waits=public_research.SERIES_WAIT_LIMIT)
        self.assertEqual((record['waiting'], record['ended'], self.client.calls), (False, 'waits', []))

    def test_a_record_made_for_another_title_is_not_continued(self):
        first = self.visit()
        _, other = self.research._bounded_lookup({'_lookup': first}, asked(('series',)), 'Другая книга', 'Лю Цысинь', ['series'], Stop(), lambda *_: None, {'sources': []})
        self.assertEqual((other['tries'], other['visits']), (1, 1), 'a new look-up for the new title')


class ReviewTests(Base):
    """Through PublicResearch.lookup, as the automatic run calls it: the row that reaches review or conversion."""

    def book(self, folder='Лю Цысинь\\Тёмный лес', album='Тёмный лес', artist='Лю Цысинь', closed=(), **tags):
        rows = [file_row(folder + '\\%02d.mp3' % n, track='%d/2' % n, album=album, artist=artist, title='%02d' % n, **tags) for n in (1, 2)]
        row = self.catalog(rows)[ROOT + '\\' + folder]
        self.calls, self.missing, self.now = [], [], [10.0 ** 6]

        def clock():  # ten seconds at every read, so nothing paces; a test may move it on (self.now)
            self.now[0] += 10
            return self.now[0]
        self.research = PublicResearch(PublicClient(self.research.client.database, fetch=fetcher(closed, self.calls, self.missing), clock=clock), leads=[])
        return row

    def until_the_wait_ends(self, row, result):
        """Visit the book again at each next try, handing its record back as the automatic run does, until it no longer waits."""
        visits = 0
        while result.get('lookup', {}).get('waiting'):
            visits += 1
            self.assertLess(visits, 6, 'the wait is bounded')
            self.now[0] = result['lookup']['next_at'] + 1
            result = self.lookup(dict(row, _lookup=result['lookup']))
        return result, visits

    def test_the_dark_forest_is_filed_under_its_english_names(self):
        row = self.book()
        result = self.lookup(row)
        review, facts = result['review'], result['metadata_facts']
        self.assertEqual(result['reasons'], [])
        self.assertEqual((review['title'], review['canonical_author'], review['series'], review['number']), ('The Dark Forest', 'Liu Cixin', "Remembrance of Earth's Past", '2'))
        self.assertEqual(self.goes_to(row, result), SORTED + "\\Liu Cixin\\Remembrance of Earth's Past\\Remembrance of Earth's Past - 2 - The Dark Forest - Liu Cixin.m4b")
        self.assertEqual(facts['title_source'], {'rule': 'english', 'provider': 'fantlab', 'url': 'https://fantlab.ru/work602240', 'split': False})
        self.assertEqual({key: facts['series_source'][key] for key in ('provider', 'number_from', 'name_rule', 'name_provider')},
                         {'provider': 'fantlab', 'number_from': 'counted', 'name_rule': 'english', 'name_provider': 'wikidata'})
        self.assertEqual((facts['original_title_lookup']['state'], facts['original_title_lookup']['title'], facts['original_title_lookup']['provider']), ('found', 'The Dark Forest', 'fantlab'))
        self.assertEqual((result['lookup']['fields'], result['lookup']['waiting']), ({'original_title': 'answered', 'series': 'answered'}, False))
        self.assertEqual(self.missing, [])
        from merge_service import MergeService
        self.assertEqual(MergeService.title_origin(result), {'origin': 'source', 'rule': 'english', 'split': False, 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work602240'})
        origin = MergeService.series_origin(result)
        self.assertEqual((origin['origin'], origin['provider'], origin['number_from'], origin['name_from']), ('source', 'fantlab', 'counted', 'wikidata'))

    def test_a_series_the_tags_name_keeps_its_number_and_gets_its_english_name(self):
        row = self.book(sort_album='Память о прошлом Земли. Книга 2')
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['local_agreement']['series']['value'], 'Память о прошлом Земли', 'the files\' own series is unchanged')
        self.assertEqual((result['review']['series'], result['review']['number'], result['review']['title']), ("Remembrance of Earth's Past", '2', 'The Dark Forest'))
        from merge_service import MergeService
        origin = MergeService.series_origin(result)
        self.assertEqual((origin['origin'], origin.get('name_from')), ('tags', 'wikidata'), 'from the file\'s tags, English name from Wikidata')

    def test_the_learned_rule_cixin_liu_is_corrected_on_evidence(self):
        row = self.book()
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            author_rules.append(db, 'same_as', 'Лю Цысинь', target='Cixin Liu', actor='assistant', source='https://fantlab.ru/work1014151', question='Шаровая молния')
            db.commit()
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['review']['canonical_author'], 'Liu Cixin')
        self.assertEqual((result['author_learned']['name'], result['author_learned']['corrected']), ('Liu Cixin', 'Cixin Liu'))
        self.assertEqual(author_rules.load(self.research.client.database).same_as('Лю Цысинь'), 'Liu Cixin', 'the newest rule for the credit wins')
        self.assertEqual(result['local_agreement']['author']['value'], 'Liu Cixin', 'the agreement is read again with the corrected rule')

    def test_his_own_rule_for_the_author_is_never_corrected(self):
        row = self.book()
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            author_rules.append(db, 'same_as', 'Лю Цысинь', target='Cixin Liu', actor='user', source='Sergei')
            db.commit()
        result = self.lookup(row)
        self.assertEqual((result['review']['canonical_author'], result.get('author_learned')), ('Cixin Liu', None))

    def test_a_book_waits_for_closed_sources_and_says_what_it_waits_for(self):
        import automatic_processing
        row = self.book(folder='William Gibson\\Граф Ноль', album='Граф Ноль', artist='William Gibson', closed=('api.fantlab.ru', 'www.wikidata.org', 'www.goodreads.com'))
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [public_research.SERIES_WAIT_REASON])
        lookup = result['lookup']
        self.assertEqual((lookup['waiting'], lookup['next_try'], lookup['limit'], lookup['asking']), (True, 2, 3, ['original_title', 'series']))
        self.assertEqual(result['wait']['retry_at'], lookup['next_at'])
        self.assertEqual(result['review']['title'], 'Граф Ноль', 'while it waits it carries the names from its files')
        self.assertEqual(automatic_processing.waits_for('Waiting for source', result), 'online_answer')
        self.assertEqual(automatic_processing.waits_for('Waiting for source', {'wait': {'kind': 'media_slow'}}), 'library')
        self.assertEqual(automatic_processing.waits_for('Waiting for source', {'wait': {'source': 'catalog'}}), 'catalog')
        self.assertIsNone(automatic_processing.waits_for('Held', result))
        # The next visit hands the record back; after the limit the book converts under the names from its files.
        final, visits = self.until_the_wait_ends(row, result)
        self.assertEqual((visits, final['reasons'], final['lookup']['fields']), (2, [], {'original_title': 'no_answer', 'series': 'no_answer'}), 'three tries in all')
        self.assertEqual(final['metadata_facts']['original_title_lookup']['state'], 'no_answer')
        self.assertEqual((final['metadata_facts']['original_title_lookup']['tries'], final['review']['title']), (3, 'Граф Ноль'))

    def test_the_author_question_waits_for_the_look_up_and_is_asked_only_after_it(self):
        # «Лю Цысинь» has no English spelling in the library: the sources that could name him are closed.
        row = self.book(closed=('api.fantlab.ru', 'www.wikidata.org', 'www.goodreads.com'))
        result = self.lookup(row)
        self.assertEqual((result['reasons'], result.get('ask')), ([public_research.SERIES_WAIT_REASON], None), 'it waits for the sources: no "Author unclear" yet')
        final, _ = self.until_the_wait_ends(row, result)
        self.assertEqual((final['reasons'], (final.get('ask') or {}).get('why')), (['Author unclear'], 'english_spelling'), 'the look-up ended without the name: now he is asked')

    def test_a_name_that_only_looks_like_a_series_is_not_asked_about(self):
        # R22: "Title unclear" for a title that only looks like a series name and number is gone.
        row = self.book(folder='William Gibson\\Sprawl 5. Граф Ноль', album='Sprawl 5. Граф Ноль', artist='William Gibson')
        result = self.lookup(row)
        self.assertEqual((result['reasons'], result.get('ask')), ([], None), 'no question')
        self.assertEqual((result['review']['title'], result['review']['series']), ('Sprawl 5. Граф Ноль', ''), 'F9: the whole text as the files have it, no series')
        self.assertEqual({item['why'] for item in result['metadata_facts']['gap_search']['series_doubt']}, {'number_mismatch', 'unconfirmed_name'})
        from merge_service import MergeService
        self.assertEqual({item['why'] for item in MergeService.series_dropped(result)}, {'number_mismatch', 'unconfirmed_name'})
        approval = self.research.approved(row, ROOT)['approval']
        self.assertEqual((approval['series_question'], approval['number_question']), (False, False))

    def test_the_same_name_with_the_sources_number_is_confirmed_and_filed(self):
        row = self.book(folder='William Gibson\\Sprawl 2. Граф Ноль', album='Sprawl 2. Граф Ноль', artist='William Gibson')
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['local_agreement']['title']['value'], 'Sprawl 2. Граф Ноль', 'the files\' title is unchanged')
        self.assertEqual((result['review']['title'], result['review']['series'], result['review']['number']), ('Count Zero', 'Sprawl', '2'))
        self.assertTrue(result['metadata_facts']['title_source']['split'])

    def test_a_held_row_is_looked_up_and_keeps_the_answer_past_the_cache(self):
        row = self.book(artist='', folder='Сборник\\Тёмный лес')  # no author in the files: held for him
        result = self.lookup(row)
        self.assertTrue(result['reasons'], 'positive control: the row is held')
        self.assertTrue(result['lookup'].get('nothing'), 'no author yet: nothing to ask about')
        record = self.research.held_lookup(dict(row), ROOT, None, Stop())
        self.assertTrue(record.get('nothing'))
        # With an author the same row is asked about, in the gap lane, and the record carries the answers themselves.
        named = self.book()
        with unittest.mock.patch.object(self.research, '_bounded_lookup', wraps=self.research._bounded_lookup) as bounded:
            record = self.research.held_lookup(dict(named), ROOT, None, Stop())
        self.assertEqual(bounded.call_args.kwargs.get('lane'), 'gap', 'a review-list row never takes the bound from a book that can convert')
        self.assertEqual((record['fields'], record['found']['catalog']['english_title'], record['found']['series']['number']),
                         ({'original_title': 'answered', 'series': 'answered'}, 'The Dark Forest', '2'))
        envelope = {'candidate_id': named['id'], 'revision': named['revision'], 'fingerprint': named['fingerprint'], 'result': {'lookup': record}}
        kept = public_research._held_lookup_fields(named, envelope, 'Тёмный лес', 'Лю Цысинь')
        self.assertEqual((kept['catalog']['english_title'], kept['series']['name']), ('The Dark Forest', "Remembrance of Earth's Past"))
        self.assertIsNone(public_research._held_lookup_fields(named, envelope, 'Другая книга', 'Лю Цысинь'), 'only the record made for the title the row shows')
        self.assertIsNone(public_research._held_lookup_fields(dict(named, fingerprint='changed'), envelope, 'Тёмный лес', 'Лю Цысинь'))


class WithdrawnStopsTests(unittest.TestCase):
    """R22 and R25: the stops about a doubtful series are gone; saved answers stay."""

    def result(self, authors, work_id='fantlab:1', series='Колесо Времени'):
        return {'review': {'title': 'Око мира', 'canonical_author': '; '.join(authors), 'author': '; '.join(authors), 'series': series, 'number': '1'},
                'metadata_facts': {'authors': list(authors), 'work_ids': [work_id], 'series_state': 'verified', 'gap_search': {}, 'series_source': {'provider': 'fantlab', 'url': 'https://fantlab.ru/work9'}},
                'work': {'id': work_id, 'verified_series': {'provider': 'fantlab', 'name': series, 'number': '1', 'source_url': 'https://fantlab.ru/work9'}},
                'evidence': [{'field': 'series', 'cited_value': series}, {'field': 'number', 'cited_value': '1'}, {'field': 'title', 'cited_value': 'Око мира'}]}

    def test_conflicting_author_credits_in_a_series_drop_the_series_and_the_book_goes_on(self):
        book = self.result(['Jordan Robert'])
        peer = self.result(['Sanderson Brandon'])
        out = public_research.attach_shared_routing(book, peers=[peer])  # it raised RoutingEvidenceError until R25
        self.assertEqual((out['review']['series'], out['review']['number'], out['metadata_facts']['series_state']), ('', '', 'omitted_unknown'))
        self.assertEqual(out['metadata_facts']['gap_search']['series_doubt'][0]['why'], 'source_conflict')
        self.assertEqual([item['field'] for item in out['evidence']], ['title'])
        self.assertNotIn('shared_routing', out['metadata_facts'])
        with unittest.mock.patch('shared_routing.build', return_value={'built': True}) as build:
            agreeing = public_research.attach_shared_routing(self.result(['Jordan Robert']), peers=[self.result(['Jordan Robert'], work_id='fantlab:2')])
        self.assertEqual((agreeing['review']['series'], len(build.call_args.kwargs['series']['members'])), ('Колесо Времени', 2), 'positive control: members that agree keep the series')

    def test_sources_disagree_is_not_asked_about_a_series_alone(self):
        row = {'id': 'book', 'fingerprint': 'fp', 'revision': 1}
        providers = [{'id': 'a', 'provider': 'FantLab', 'work_id': 'w1', 'title': 'Око мира', 'authors': 'Роберт Джордан', 'series': 'Колесо Времени', 'number': '1'},
                     {'id': 'b', 'provider': 'Goodreads', 'work_id': 'w1', 'title': 'Око мира', 'authors': 'Роберт Джордан', 'series': 'The Wheel of Time', 'number': '0'}]
        temp = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(temp.cleanup)
        with contextlib.closing(sqlite3.connect(Path(temp.name) / 'choices.sqlite3')) as db:
            db.row_factory = sqlite3.Row
            plain = metadata_choices.questions(row, providers, [], [])
            self.assertEqual(sorted(q['field'] for q in plain['questions']), ['number', 'series'], 'positive control: the sources differ in the series and the number only')
            shown = metadata_choices.present(db, row, providers, [], [])
            self.assertEqual((shown['questions'], shown['unresolved_count'], sorted(shown['dropped_as_doubtful'])), ([], 0, ['number', 'series']))
            self.assertTrue(metadata_choices.admission(shown, {'series': '', 'number': ''}))
            # A disagreement about the title is still asked, and so is a series question he has already answered.
            other = [dict(providers[0]), dict(providers[1], title='Глаз мира', series='Колесо Времени', number='1')]
            self.assertEqual([q['type'] for q in metadata_choices.present(db, row, other, [], [])['questions']], ['work_profile'])
            prepared = metadata_choices.prepare(row, plain, plain['signature'], [{'question_id': q['id'], 'option_id': q['options'][0]['id']} for q in plain['questions']])
            metadata_choices.append(db, prepared['record'])
            answered = metadata_choices.present(db, row, providers, [], [])
            self.assertEqual((len(answered['questions']), answered['unresolved_count']), (2, 0), 'his saved answer keeps its question and stays resolved')

    def test_the_series_look_up_of_finished_books_treats_a_conflict_as_not_found(self):
        from public_work_identity import EvidenceConflict
        import series_backfill
        asked_sources = []

        def source(name, answer):
            def call(*_):
                asked_sources.append(name)
                if isinstance(answer, Exception):
                    raise answer
                return answer
            return call
        fantlab = {'provider': 'fantlab', 'name': 'Колесо Времени', 'number': '1', 'number_from': 'counted', 'source_url': 'https://fantlab.ru/work9'}
        research = SimpleNamespace(_series_goodreads=source('goodreads', {'provider': 'goodreads', 'name': 'A; B', 'number': '', 'doubt': 'several_series', 'source_url': 'x'}),
                                   _series_fantlab=source('fantlab', fantlab), _series_wikidata=source('wikidata', EvidenceConflict('Qualified work identity relationship needs stronger evidence')),
                                   _series_publisher=source('publisher', None), _series_litres=source('litres', None))
        backfill = SimpleNamespace(research=research, stop=threading.Event(), clock=lambda: 1000.0)
        memory = {}
        found = series_backfill.SeriesBackfill.lookup(backfill, {'metadata': {'title': 'Око мира', 'canonical_author': 'Jordan Robert'}}, memory)
        self.assertEqual((found['name'], found['number'], asked_sources), ('Колесо Времени', '1', ['goodreads', 'fantlab']))
        self.assertEqual((memory['goodreads']['answer'], memory['goodreads']['doubt']), ('none', 'several_series'), 'doubtful: the source has answered "none"')
        research._series_fantlab = source('fantlab', None)
        memory = {}
        self.assertIsNone(series_backfill.SeriesBackfill.lookup(backfill, {'metadata': {'title': 'Око мира', 'canonical_author': 'Jordan Robert'}}, memory))
        self.assertEqual((memory['wikidata']['answer'], memory['wikidata']['doubt']), ('none', 'source_conflict'), 'it held the book "Series sources need review" until 0.31.0')

    def test_a_book_held_for_series_sources_need_review_is_looked_up_once_more(self):
        import series_backfill
        self.assertTrue(series_backfill.REVIEW_REASON)
        source = Path(series_backfill.__file__).read_text(encoding='utf-8')
        self.assertNotIn("raise Held('Series sources need review", source, 'the hold is gone: a conflict is a doubtful answer')

    def test_the_two_asks_are_no_longer_produced_and_rows_that_carry_them_are_read_again(self):
        source = Path(public_research.__file__).read_text(encoding='utf-8')
        for why in ("'why':'title_series'", "'why':'number_unclear'"):
            self.assertNotIn(why, source, 'research sends no such ask any more')
        for why in ('title_series', 'number_unclear'):
            self.assertTrue(public_research.needs_local_recheck({'reasons': ['Title or author missing'], 'ask': {'kind': 'title_author', 'why': why}}))
        self.assertFalse(public_research.needs_local_recheck({'ask': {'kind': 'title_author', 'why': 'title_bitrate'}}), 'positive control: another question stays')
        self.assertFalse(public_research.needs_local_recheck({'ask': {'kind': 'title_author', 'why': 'title_series'}, 'local_recheck': public_research.LOCAL_RECHECK}), 'once')


class HeldPassTests(unittest.TestCase):
    """gap_fill's pass goes on with the review-list rows: bounded, compare-and-swap, counted for the page."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(temp.cleanup)
        self.database = Path(temp.name) / 'catalog.sqlite3'
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT,state TEXT,created TEXT,updated TEXT)')
            db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,evidence TEXT,superseded INTEGER DEFAULT 0)')
            db.execute('CREATE TABLE automatic_candidates(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,state TEXT,result TEXT,retry_at REAL,attempted TEXT,matcher_version TEXT)')
            db.execute('CREATE TABLE automatic_result_revision(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL)')
            db.execute('INSERT INTO automatic_result_revision VALUES(1,0)')
            db.execute('CREATE TRIGGER bump AFTER UPDATE ON automatic_candidates BEGIN UPDATE automatic_result_revision SET revision=revision+1 WHERE id=1; END')
            for book in ('held', 'stale', 'queued'):
                db.execute('INSERT INTO book_groups VALUES(?,?,?,?,0)', (book, 1, 'fp-' + book, json.dumps({'title_clue': 'Тёмный лес'}, ensure_ascii=False)))
            db.execute("INSERT INTO automatic_candidates VALUES('held',1,'fp-held','Held',?,NULL,'t','v')", (json.dumps({'reasons': ['Author unclear']}),))
            db.execute("INSERT INTO automatic_candidates VALUES('stale',1,'older-fingerprint','Held',?,NULL,'t','v')", (json.dumps({'reasons': ['Author unclear']}),))
            db.execute("INSERT INTO automatic_candidates VALUES('queued',1,'fp-queued','Queued',?,NULL,'t','v')", (json.dumps({'reasons': []}),))
            db.commit()
        self.now = [5000.0]
        self.records = []
        rows = {book: {'id': book, 'revision': 1, 'fingerprint': 'fp-' + book} for book in ('held', 'stale', 'queued')}

        def held_lookup(row, root, prior, stop):
            self.records.append((row['id'], prior))
            return self.answer(prior)
        research = SimpleNamespace(fill_gaps=lambda *a, **k: ({}, {}), held_lookup=held_lookup)
        merge = SimpleNamespace(inventory=SimpleNamespace(database=self.database), automatic=SimpleNamespace(_candidate_root=lambda row: 'Z:\\Audiobooks'),
                                reviews=SimpleNamespace(_row=lambda library, book: dict(rows[book])))
        self.fill = gap_fill.GapFill(merge, research=research, clock=lambda: self.now[0])
        self.answer = lambda prior: {'policy': public_research.LOOKUP_POLICY, 'waiting': True, 'next_at': self.now[0] + 600, 'fields': {'series': 'waiting'}, 'sources': {}, 'tries': 1}

    def saved(self, book='held'):
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            return json.loads(db.execute('SELECT result FROM automatic_candidates WHERE id=?', (book,)).fetchone()[0])

    def test_only_the_current_held_rows_are_looked_up_and_the_record_is_kept_with_them(self):
        self.assertEqual([row['id'] for row in self.fill.held_candidates()], ['held'], 'not a stale record, not a queued book')
        self.assertEqual(self.fill.summary()['review'], {'left': 1, 'to_look_up': 1, 'between_tries': 0, 'next_at': None, 'done': 0, 'total': 1, 'nothing_to_ask': 0})
        self.fill.run_pass()
        self.assertEqual(self.records, [('held', None)])
        self.assertEqual((self.saved()['lookup']['waiting'], self.saved()['reasons']), (True, ['Author unclear']), 'the row\'s own result is untouched beside it')
        review = self.fill.summary()
        self.assertEqual((review['review']['between_tries'], review['review']['next_at'], review['between_tries'], review['left']), (1, 5600.0, 1, 1),
                         'inside the totals too: never "all done" while a review-list row is still to be asked about')
        self.fill.run_pass()
        self.assertEqual(len(self.records), 1, 'between tries: not asked again')
        self.now[0] = 5601.0
        self.answer = lambda prior: dict(prior, waiting=False, next_at=None, fields={'series': 'answered'})
        self.fill.run_pass()
        self.assertEqual((len(self.records), self.records[-1][1]['tries'], self.saved()['lookup']['fields']), (2, 1, {'series': 'answered'}), 'the record is handed back')
        self.assertEqual((self.fill.held_candidates(), self.fill.summary()['review']['done']), ([], 1), 'settled: never looked up again')

    def test_a_row_research_took_up_meanwhile_is_left_to_it(self):
        entry = self.fill.held_candidates()[0]

        def raced(prior):
            with contextlib.closing(sqlite3.connect(self.database)) as db:
                db.execute("UPDATE automatic_candidates SET result=? WHERE id='held'", (json.dumps({'reasons': ['Same author?']}),))
                db.commit()
            return {'policy': public_research.LOOKUP_POLICY, 'waiting': False, 'next_at': None, 'fields': {}, 'sources': {}}
        self.answer = raced
        self.assertEqual(self.fill.look_up_held(entry), 'changed')
        self.assertEqual(self.saved(), {'reasons': ['Same author?']}, 'compare-and-swap: research\'s newer result is not overwritten')

    def test_a_row_that_cannot_be_looked_up_is_not_tried_at_every_pass(self):
        def broken(prior):
            raise RuntimeError('unexpected')
        self.answer = broken
        self.fill.run_pass()
        self.assertEqual((self.saved()['lookup'].get('nothing'), self.saved()['lookup']['error']), (True, 'unexpected'))
        self.assertEqual(self.fill.held_candidates(), [])


if __name__ == '__main__':
    unittest.main()
