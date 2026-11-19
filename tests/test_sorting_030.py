"""0.30.0 sorting (Sergei 2026-11-18, backlog "Why books aren't sorted — library-wide", items 2-8).

Fixtures are the diagnosis' own examples: Harry Potter 3 and 7 («Harry Potter\\64. Книга 3 - …», «Роулинг Джоан\\»,
«J. K. Rowling\\»), «Darwin's Blade 1/2», «Террор» 1-4 at 32.2 h, «Sprawl Trilogy». Catalog rows, synthetic files in
the test scratch area; no network, no real library."""
import contextlib
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

import groups
import part_sets
from test_folder_structure import Base, file_row, ROOT, SORTED

HP3 = 'Harry Potter\\64. Книга 3 - Гарри Поттер и узник Азкабана (Александр Клюквин)\\'
HP7 = 'Harry Potter\\68. Книга 7 - Гарри Поттер и Дары Смерти (Александр Клюквин)\\'


def hp_rows(folder, album, artist='Джоан Роулинг', count=2):
    return [file_row(folder + '%02d.mp3' % n, track='%d/%d' % (n, count), album=album, artist=artist, title='%s %02d' % (album, n))
            for n in range(1, count + 1)]


class RootSeriesFolderTests(Base):
    """Item 4: a root-level <Series>\\NN. Книга N - <Title> (<Reader>) folder is a series and number clue, never the author."""

    def test_harry_potter_3_takes_its_series_and_number_from_the_root_series_folder(self):
        row = self.catalog(hp_rows(HP3, 'Гарри Поттер и узник Азкабана'))[ROOT + '\\' + HP3.rstrip('\\')]
        result = self.lookup(row)
        local = result['local_agreement']
        self.assertEqual((local['series']['value'], local['number']['value']), ('Harry Potter', '3'), local)
        self.assertEqual(local['author']['value'], 'Rowling J. K', 'the series folder is never the author')
        self.assertEqual(result['reasons'], [])
        review = result['review']
        self.assertEqual((review['series'], review['number'], review['canonical_author']), ('Harry Potter', '3', 'Rowling J. K'))
        self.assertEqual(self.goes_to(row, result),
                         SORTED + '\\Rowling J. K\\Harry Potter\\Harry Potter - 3 - Гарри Поттер и узник Азкабана - Rowling J. K.m4b')

    def test_a_root_folder_of_one_authors_books_is_still_no_series(self):
        # «Stephen King\\930. Коробка в форме сердца (Михаил Прокопов)»: no "Книга N", the first folder names a person: as before.
        rows = [file_row('Stephen King\\930. Коробка в форме сердца (Михаил Прокопов)\\%02d.mp3' % n, track='%d/2' % n,
                         album='Коробка в форме сердца', artist='Стивен Кинг', title='%02d' % n) for n in (1, 2)]
        row = self.catalog(rows)[ROOT + '\\Stephen King\\930. Коробка в форме сердца (Михаил Прокопов)']
        local = self.lookup(row)['local_agreement']
        self.assertEqual(local['series']['value'], '', local)


class Answering:
    """Every public source answers, and none knows a series (an empty search, an empty catalog answer)."""
    def __init__(self, database):
        self.database = database; self.calls = []

    def read(self, url, *_, **__):
        self.calls.append(url); return b'[]'

    def json(self, url, *_, **__):
        self.calls.append(url); return {'search': []} if 'wikidata' in url else []

    def discover(self, query, *_):
        self.calls.append(query); return []
    wikipedia = discover

    def receipt(self, url):
        return {'url': url}


class RateLimited(Answering):
    """Every public source is at a request limit (the app's hourly bound): only rate-limited, nothing answered."""
    def _limited(self, url, *_, **__):
        from public_research import APP_LIMIT_REASON, ResearchWait
        self.calls.append(url); raise ResearchWait('www.goodreads.com', APP_LIMIT_REASON, 5000, 'app_limit', 'host')
    read = json = discover = wikipedia = _limited


class SeriesWaitTests(Base):
    """Item 3: a translation whose every series source was only rate-limited waits for its series (HP 7, 25 Oct); one a
    source answered ("no series") or could not reach is published as before; the wait is bounded."""

    def book(self, client=RateLimited):
        from public_research import PublicResearch
        rows = [file_row('Rowling\\Гарри Поттер и Дары Смерти (Клюквин)\\%02d.mp3' % n, track='%d/2' % n, album='Гарри Поттер и Дары Смерти',
                         artist='Джоан Роулинг', title='%02d' % n) for n in (1, 2)]
        row = self.catalog(rows)[ROOT + '\\Rowling\\Гарри Поттер и Дары Смерти (Клюквин)']
        if client is not None:
            self.research = PublicResearch(client(self.research.client.database), leads=[])
        return row

    def test_a_source_that_cannot_be_reached_publishes_as_now(self):
        result = self.lookup(self.book(client=None))  # the Offline client: unreachable, not rate-limited
        self.assertEqual(result['reasons'], [])
        self.assertIsNone(result['wait'])

    def test_every_series_source_only_rate_limited_waits_for_the_series(self):
        import public_research
        row = self.book()
        result = self.lookup(row)
        self.assertIsNotNone(result['wait'], 'it waits, and says why and when it tries again (was: published without a series)')
        self.assertEqual(result['reasons'], [public_research.SERIES_WAIT_REASON], result['reasons'])
        self.assertIn('retry_at', result['wait'])
        self.assertEqual(result['series_waits'], 1)
        self.assertEqual(result['review']['series'], '')
        self.assertEqual(result['metadata_facts']['gap_search']['series_wait']['tries'], 1)

    def test_a_source_that_answers_no_series_publishes_as_now(self):
        row = self.book(client=Answering)
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [], 'positive control: the sources answered, nothing waits')
        self.assertIsNone(result['wait'])
        self.assertEqual(result['review']['series'], '')

    def test_the_wait_ends_after_three_tries(self):
        import public_research
        row = dict(self.book(), _series_waits=public_research.SERIES_WAIT_LIMIT)
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [], 'published without a series, as before; series backfill looks it up later')
        self.assertIsNone(result['wait'])
        self.assertTrue(result['metadata_facts']['gap_search']['series_wait']['published_without'])


def glavy(first, last):
    return ['Глава %d' % n for n in range(first, last + 1)]


def set_parts(*chapter_lists, titles, hours, tracks=None):
    count = len(chapter_lists)
    return [{'name': titles[i], 'title': titles[i], 'track': (tracks or ['%d/%d' % (n, count) for n in range(1, count + 1)])[i],
             'hours': hours, 'credits': '', 'chapters': list(c)} for i, c in enumerate(chapter_lists)]


class NoHourLimitTests(unittest.TestCase):
    """Item 8 (Sergei: remove the 30-hour limit): the total duration never holds a part set; the other clues decide."""

    def test_terror_four_8_hour_parts_continuing_is_one_book(self):
        terror = set_parts(['01. Крозье', '15. Франклин'], ['16. Крозье', '28. Пеглар'], ['29. Ирвинг', '47. Пеглар'], ['48. Гудсир', '67. Талириктуг'],
                           titles=['Террор 1', 'Террор 2', 'Террор 3', 'Террор 4'], hours=8.05)
        found = part_sets.decide(terror)
        self.assertEqual((found['decision'], found['basis']), ('join', 'chapter numbering continues'), '32.2 h: no longer asked as "long"')

    def test_the_other_clues_still_hold_a_long_set(self):
        # Sprawl Trilogy (Neuromancer, Count Zero, Mona Lisa Overdrive): each file names its own work: volumes, at any length.
        sprawl = set_parts(['Глава 1', 'Глава 2'], ['Глава 1', 'Глава 2'], ['Глава 1', 'Глава 2'],
                           titles=['Sprawl Trilogy 01 - Neuromancer', 'Sprawl Trilogy 02 - Count Zero', 'Sprawl Trilogy 03 - Mona Lisa Overdrive'],
                           hours=12, tracks=['', '', ''])
        self.assertEqual(part_sets.decide(sprawl)['decision'], 'volumes')
        # Book words (Tolkien) and seasons stay questions however long.
        tolkien = set_parts(['Пролог', 'Глава I'], ['Глава I', 'Глава II'], titles=['Хранители. Книга первая', 'Хранители. Книга вторая'], hours=20)
        self.assertEqual(part_sets.decide(tolkien)['decision'], 'ask')
        unclear = set_parts(['Лечение мартышками'], ['Башня Пепла'], titles=['Миры 1', 'Миры 2'], hours=20)
        self.assertEqual((part_sets.decide(unclear)['decision'], part_sets.decide(unclear)['basis']), ('ask', 'unclear'))
        self.assertFalse(hasattr(part_sets, 'LONG_HOURS'), 'no replacement limit')

    def test_a_book_held_only_by_the_removed_limit_is_researched_again(self):
        from automatic_processing import AutomaticProcessing
        from public_research import RESEARCH_VERSION
        held = {'state': 'Held', 'until_change': True, 'retry_at': None, 'research_version': RESEARCH_VERSION, 'reasons': ['One part of a bigger book'],
                'identity_hold': {'kind': 'piece', 'detail': '', 'piece': {'piece': 'set', 'cause': 'long', 'parts': 4, 'hours': 32.2}}}
        again = AutomaticProcessing._refresh_wait(None, {'id': 'terror'}, held)
        self.assertFalse(again['until_change'], 'the next Start researches it again')
        other = dict(held, identity_hold={'kind': 'piece', 'detail': '', 'piece': {'piece': 'set', 'cause': 'unclear', 'parts': 2}})
        self.assertTrue(AutomaticProcessing._refresh_wait(None, {'id': 'miry'}, other)['until_change'], 'any other hold stays as it was')


def m4b_row(path, **tags):
    from test_split_books import row as catalog_row
    return catalog_row(path, tags)


class TrailingPartAlbumTests(unittest.TestCase):
    """Item 7: M4B parts whose album tags differ only by a trailing part number are one set («Darwin's Blade 1», «… 2»)."""

    def test_darwins_blade_1_and_2_are_one_part_set(self):
        folder = "Dan Simmons/Dale Stewart Mike O'Rourke/"
        rows = [m4b_row(folder + "Dale Stewart 04 - Darwin's Blade %d.m4b" % n, album="Dale Stewart 04 - Darwin's Blade %d" % n,
                        title="Dale Stewart 04 - Darwin's Blade %d" % n, artist='Дэн Симмонс') for n in (1, 2)]
        built = groups.build(rows)
        self.assertEqual(len(built), 1, list(built))
        group = next(iter(built.values()))
        self.assertTrue(group['part_set'])
        self.assertEqual([Path(m['path']).name for m in group['members']], ["Dale Stewart 04 - Darwin's Blade 1.m4b", "Dale Stewart 04 - Darwin's Blade 2.m4b"])

    def test_albums_naming_different_books_are_never_one_set(self):
        rows = [m4b_row('Pern/%s.m4b' % album, album=album, title=album, artist='Энн Маккефри') for album in ('Песни Перна', 'Певица Перна')]
        self.assertEqual(len(groups.build(rows)), 2)
        rows = [m4b_row('Misc/%s.m4b' % album, album=album, title=album, artist='Автор Один') for album in ('1408', '1409')]
        self.assertEqual(len(groups.build(rows)), 2, 'a title that is only a number is no part number')


AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'sorting-030-tests'
AREA.mkdir(parents=True, exist_ok=True)
JOBS = ('CREATE TABLE audio_jobs (job_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_hash TEXT NOT NULL, state TEXT NOT NULL,'
        ' stage TEXT NOT NULL, attempt_id TEXT, journal TEXT NOT NULL, output TEXT, reason TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL)')
BACKFILL = ('CREATE TABLE series_backfill(job_id TEXT PRIMARY KEY,state TEXT NOT NULL,reason TEXT NOT NULL,record TEXT NOT NULL,updated TEXT NOT NULL)')
CACHE = 'CREATE TABLE public_research_cache(url TEXT PRIMARY KEY, raw TEXT, sha256 TEXT, fetched REAL)'


def cycle(db, cycle_id, name, original, language):
    """A FantLab cycle record in the research cache, as research fetched it."""
    import base64, hashlib
    raw = json.dumps({'work_id': cycle_id, 'work_name': name, 'work_name_orig': original, 'lang_code': language, 'work_type_id': 4}, ensure_ascii=False).encode('utf-8')
    db.execute('INSERT INTO public_research_cache VALUES(?,?,?,?)', ('https://api.fantlab.ru/work/%d/extended' % cycle_id, base64.b64encode(raw).decode('ascii'),
                                                                     hashlib.sha256(raw).hexdigest(), 1.0))


class SortedCatalog(unittest.TestCase):
    """A private Audiobooks Sorted folder (empty .m4b files) and a catalog of finished books in it."""

    def setUp(self):
        import author_rules
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.sorted = self.base / 'Sorted'
        self.library = self.base / 'Library'
        self.sorted.mkdir()
        self.library.mkdir()
        self.database = str(self.base / 'catalog.sqlite3')
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute(JOBS)
            db.execute(BACKFILL)
            db.execute(CACHE)
            author_rules.seed(db)  # Sergei's 2026-10-24 answers: «Роулинг Джоан», «Джоан Роулинг» -> Rowling J. K
            db.commit()
        self.count = 0

    def book(self, relative, author, title, series='', number='', language='Other', source=None, entered=(), root=None, create=True):
        """One finished job whose output is <root>\\relative (an empty file), named as the app named it."""
        root = Path(root or self.sorted)
        path = root / relative
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'')
        self.count += 1
        job_id, candidate = 'job-%d' % self.count, 'book-%d' % self.count
        facts = {'policy_version': 'standing-17-v1', 'authors': [author], 'series_state': 'verified' if series else 'omitted_unknown'}
        if source:
            facts['series_source'] = source
        if entered:
            facts['entered_names'] = {'digest': 'x', 'fields': list(entered), 'saved_utc': {}}
        manifest = {'job_id': job_id, 'candidate_id': candidate, 'root': str(self.library), 'output_root': str(root),
                    'metadata': {'title': title, 'author': author, 'canonical_author': author, 'series': series, 'number': number,
                                 'original_language': language, 'organization_policy': 'books-hierarchy-v2', 'anthology': False, 'multi_author': False},
                    'metadata_facts': facts}
        output = {'job_id': job_id, 'root': str(root), 'final_path': str(path), 'sha256': '0' * 64, 'size': 0}
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)', (job_id, json.dumps(manifest, ensure_ascii=False), 'h', 'completed', 'completed', None,
                                                                              '{}', json.dumps(output, ensure_ascii=False), '', '2026-11-0%d' % min(self.count, 9), 'now'))
            db.commit()
        return job_id

    def held(self, job_id, series, number, url, provider='fantlab'):
        """Series backfill found a series and held the book on the old bug (item 2)."""
        record = {'series': series, 'number': number, 'provider': provider, 'source_url': url, 'research_receipts': []}
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute("INSERT INTO series_backfill VALUES(?,'held',?,?,'now')", (job_id, 'The recorded series paths do not share their original parent',
                                                                                 json.dumps(record, ensure_ascii=False)))
            db.commit()

    def plan(self):
        import author_rules, sorting_moves
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            return sorting_moves.plan(db, str(self.sorted), author_rules.load(self.database))

    def harry_potter_7(self):
        job = self.book('J. K. Rowling\\Harry Potter and the Deathly Hallows - J. K. Rowling.m4b', 'J. K. Rowling', 'Harry Potter and the Deathly Hallows')
        self.held(job, 'Гарри Поттер', '7', 'https://fantlab.ru/work3650')
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            cycle(db, 3650, 'Гарри Поттер', 'Harry Potter', 'en')
            db.commit()
        return job


class SortingPlanTests(SortedCatalog):
    """Items 2, 5 and 6 for books already in Sorted: planned and listed, nothing moved (the diagnosis' own examples)."""

    def test_harry_potter_7_goes_to_its_series_folder_under_the_one_author_folder(self):
        job = self.harry_potter_7()
        found = self.plan()
        item = next(i for i in found['items'] if i['job_id'] == job)
        self.assertEqual(item['to'], str(self.sorted / 'Rowling J. K' / 'Harry Potter' / 'Harry Potter - 7 - Harry Potter and the Deathly Hallows - Rowling J. K.m4b'))
        self.assertEqual(item['items'], ['series', 'author'])
        self.assertEqual(item['series'], {'name': 'Harry Potter', 'number': '7', 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work3650'},
                         'item 6: the series in the language it was written in')
        self.assertTrue((self.sorted / 'J. K. Rowling').exists(), 'planning moves nothing')

    def test_harry_potter_2_under_the_cyrillic_folder_joins_the_one_author_folder(self):
        job = self.book('Роулинг Джоан\\Гарри Поттер и тайная комната - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Гарри Поттер и тайная комната', language='Unknown')
        item = next(i for i in self.plan()['items'] if i['job_id'] == job)
        self.assertEqual(item['to'], str(self.sorted / 'Rowling J. K' / 'Гарри Поттер и тайная комната - Rowling J. K.m4b'))
        self.assertEqual(item['items'], ['author'])

    def test_a_fantlab_series_of_a_non_russian_work_takes_its_original_name(self):
        job = self.book('Jansson Tove\\Муми-тролли\\Муми-тролли - 3 - Шляпа волшебника - Jansson Tove.m4b', 'Jansson Tove', 'Шляпа волшебника',
                        series='Муми-тролли', number='3', source={'provider': 'fantlab', 'url': 'https://fantlab.ru/work29124'})
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            cycle(db, 29124, 'Муми-тролли', 'Mumintrollen', 'sv')
            db.commit()
        item = next(i for i in self.plan()['items'] if i['job_id'] == job)
        self.assertEqual(item['to'], str(self.sorted / 'Jansson Tove' / 'Mumintrollen' / 'Mumintrollen - 3 - Шляпа волшебника - Jansson Tove.m4b'))
        self.assertEqual(item['items'], ['series_language'])

    def test_what_stays_as_it_is(self):
        # His typed series (Колесо времени, entered), a Russian original's cycle, a Goodreads series: never renamed.
        self.book('Jordan Robert\\Колесо времени\\Колесо времени - 1 - Око мира - Jordan Robert.m4b', 'Jordan Robert', 'Око мира', series='Колесо времени',
                  number='1', source={'provider': 'entered'}, entered=('series', 'number'))
        self.book('Лукьяненко Сергей\\Дозоры\\Дозоры - 1 - Ночной дозор - Лукьяненко Сергей.m4b', 'Лукьяненко Сергей', 'Ночной дозор', series='Дозоры', number='1',
                  language='Russian', source={'provider': 'fantlab', 'url': 'https://fantlab.ru/work100'})
        # Item 5's rule is conservative: an initial is never merged with a full first name, nor a Cyrillic name without a rule.
        self.book('Rowling Joanne\\Other Book - Rowling Joanne.m4b', 'Rowling Joanne', 'Other Book')
        self.book('Хилл Джо\\Страна Рождества - Хилл Джо.m4b', 'Хилл Джо', 'Страна Рождества', language='Unknown')
        found = self.plan()
        self.assertEqual(found['items'], [])
        self.assertEqual(found['refused'], [])

    def test_refusals_are_listed_with_their_reason(self):
        stray = self.book('Elsewhere\\J. K. Rowling - Stray.m4b', 'J. K. Rowling', 'Stray Book')  # not where the app named it
        taken = self.book('Роулинг Джоан\\Taken - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Taken', language='Unknown')
        (self.sorted / 'Rowling J. K').mkdir()
        (self.sorted / 'Rowling J. K' / 'Taken - Rowling J. K.m4b').write_bytes(b'')
        gone = self.book('Роулинг Джоан\\Gone - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Gone', language='Unknown', create=False)
        legacy = self.book('Роулинг Джоан\\Legacy - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Legacy', language='Unknown', root=self.library)
        found = self.plan()
        reasons = {i['job_id']: i['refused'] for i in found['refused']}
        self.assertEqual(found['items'], [])
        self.assertEqual(reasons, {stray: "Its name does not follow the app's naming; left as it is", taken: 'A file with the new name is already there',
                                   gone: 'The audiobook is not where the catalog says', legacy: 'Not in Audiobooks Sorted; left as it is'})

    def test_a_book_an_approved_move_took_there_is_not_listed_again(self):
        import book_move
        done = self.book('Роулинг Джоан\\Done - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Done', language='Unknown')
        chosen = self.book('Роулинг Джоан\\Chosen - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Chosen', language='Unknown')
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            book_move.setup(db)
            for n, (job, final) in enumerate(((done, self.sorted / 'Rowling J. K' / 'Done - Rowling J. K.m4b'), (chosen, self.base / 'Mine' / 'Chosen - Роулинг Джоан.m4b'))):
                db.execute("INSERT INTO book_moves(move_id,job_id,kind,candidate_id,generation,state,target_folder,target_root,target_path,from_json,final_json,created_utc,updated_utc)"
                           " VALUES(?,?,'base','c',1,'complete','f','r',?,'{}',?,'t','t')", ('m%d' % n, job, str(final), json.dumps({'final_path': str(final)})))
            db.commit()
        found = self.plan()
        self.assertEqual(found['items'], [])
        self.assertEqual([(i['job_id'], i['refused']) for i in found['refused']], [(chosen, 'Already moved to a folder you chose; left as it is')])

    def test_the_digest_names_the_exact_list(self):
        import sorting_moves
        self.harry_potter_7()
        first = self.plan()
        self.assertEqual(self.plan()['digest'], first['digest'])
        self.book('Роулинг Джоан\\New - Роулинг Джоан.m4b', 'Роулинг Джоан', 'New', language='Unknown')
        self.assertNotEqual(self.plan()['digest'], first['digest'], 'one more book: another list')
        text = sorting_moves.markdown(self.plan())
        self.assertIn('Harry Potter - 7 - Harry Potter and the Deathly Hallows - Rowling J. K.m4b', text)
        self.assertIn('| **Books** | **2** | **0** |', text)


class SameAuthorTests(unittest.TestCase):
    """Item 5's same-author rule (canonical_names): a rule, or exactly the same words; nothing else merges."""

    def test_the_rule(self):
        import author_rules, canonical_names
        rules = author_rules.Rules([{'rule_id': 'r1', 'kind': 'same_as', 'credit_key': author_rules.key('Роулинг Джоан'), 'credit_as_seen': 'Роулинг Джоан',
                                     'target': 'Rowling J. K', 'scope': '', 'options': '{}', 'actor': 'user', 'saved_utc': '1'}], known_authors=['Rowling J. K'])
        self.assertEqual(canonical_names.author('J. K. Rowling', rules)[0], 'Rowling J. K', 'the same words, the library\'s spelling')
        self.assertEqual(canonical_names.author('Роулинг Джоан', rules)[0], 'Rowling J. K', 'his rule')
        self.assertEqual(canonical_names.author('Rowling J. K', rules)[0], 'Rowling J. K', 'never turned around again')
        self.assertEqual(canonical_names.author('Tolkien J. R. R.', None)[0], 'Tolkien J. R. R.')
        self.assertEqual(canonical_names.author('Stephen King', None)[0], 'King Stephen', 'surname first')
        self.assertTrue(canonical_names.same_author('J. K. Rowling', 'Роулинг Джоан', rules))
        self.assertFalse(canonical_names.same_author('Joanne Rowling', 'J. K. Rowling', rules), 'an initial is not a full first name')
        self.assertFalse(canonical_names.same_author('Джо Хилл', 'Joe Hill', rules), 'another script needs a rule (never transliterated)')
        self.assertFalse(canonical_names.same_author('Rowling', 'J. K. Rowling', rules), 'never a surname alone')

    def test_series_original_name(self):
        import canonical_names
        self.assertEqual(canonical_names.series_original({'work_name': 'Гарри Поттер', 'work_name_orig': 'Harry Potter', 'lang_code': 'en'}), 'Harry Potter')
        self.assertEqual(canonical_names.series_original({'work_name': 'Дозоры', 'work_name_orig': 'Дозоры', 'lang_code': 'ru'}), '')
        self.assertEqual(canonical_names.series_original({'work_name': 'Монстр', 'work_name_orig': '怪物', 'lang_code': 'jp'}), '', 'another script: kept')
        self.assertEqual(canonical_names.series_original({'work_name': 'Властелин Колец', 'work_name_orig': 'The Lord of the Rings'}), '', 'no language: kept')


class GateTests(SortedCatalog):
    """Nothing moves without Sergei's approval of the exact list he saw (its digest)."""

    def merge(self, approved, moved):
        from types import SimpleNamespace
        from merge_service import MergeService
        merge = MergeService.__new__(MergeService)
        merge.inventory = SimpleNamespace(database=self.database, output_root=str(self.sorted), worker=None)
        merge.series_backfill = SimpleNamespace(approve=lambda job_id, found, target: approved.append((job_id, found, target)))
        merge._sorting_move = lambda job_id, target: moved.append((job_id, target)) or {'state': 'move_queued'}
        return merge

    def test_a_list_that_changed_moves_nothing_and_the_list_seen_moves_only_its_books(self):
        hp7 = self.harry_potter_7()
        hp2 = self.book('Роулинг Джоан\\Гарри Поттер и тайная комната - Роулинг Джоан.m4b', 'Роулинг Джоан', 'Гарри Поттер и тайная комната', language='Unknown')
        approved, moved = [], []
        merge = self.merge(approved, moved)
        seen = merge.sorting_moves()
        self.assertEqual((approved, moved), ([], []), 'listing moves nothing')
        with self.assertRaisesRegex(ValueError, 'changed'):
            merge.sorting_moves_apply('0' * 64)
        self.assertEqual((approved, moved), ([], []))
        answer = merge.sorting_moves_apply(seen['digest'])
        self.assertEqual([a[0] for a in approved], [hp7], 'item 2: its series is written first (series backfill)')
        self.assertEqual(approved[0][1]['name'], 'Harry Potter')
        self.assertEqual(moved, [(hp2, str(self.sorted / 'Rowling J. K' / 'Гарри Поттер и тайная комната - Rowling J. K.m4b'))])
        self.assertEqual({r['job_id']: r['state'] for r in answer['results']}, {hp7: 'series_update_queued', hp2: 'move_queued'})


class SeriesFolderBackfillTests(unittest.TestCase):
    """Item 2: a series found after publication files the book in its series folder (books-hierarchy-v2: Author\\Series\\).
    It never passed ("The recorded series paths do not share their original parent", 81 books). Now it waits for Sergei's
    approval; approved, the series is written in the book's own folder (the usual retag and its proofs) and the app's usual
    verified move (book_move) takes it to the approved path. A real audiobook file made by ffmpeg; private catalog."""

    def setUp(self):
        import test_series_backfill as base
        temp = tempfile.TemporaryDirectory(dir=base.AREA)
        self.addCleanup(temp.cleanup)
        original = base.Library.__init__.__globals__['propose']

        def v2(path, root, kind, metadata, review=None, automatic_facts=None):  # the Library's book as v2 files it
            return original(path, root, kind, metadata, dict(review or {}, organization_policy='books-hierarchy-v2'), automatic_facts)
        from unittest import mock
        with mock.patch.object(base, 'propose', v2):
            self.lib = base.Library(Path(temp.name), separate_sorted=True)
        with __import__('scanner').connect(self.lib.db) as db:
            row = db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?', (self.lib.job_id,)).fetchone()
            manifest = json.loads(row[0])
            manifest['metadata']['organization_policy'] = 'books-hierarchy-v2'
            text, digest = __import__('series_backfill').encoded(manifest)
            db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=? WHERE job_id=?', (text, digest, self.lib.job_id))
        self.found = {'name': 'Нормальное аномальное', 'number': '10', 'provider': 'goodreads', 'source_url': 'https://www.goodreads.com/book/show/55108791'}
        self.series_path = Path(original('', str(self.lib.root), 'audiobook', {}, dict(self.lib.review, organization_policy='books-hierarchy-v2',
                                                                                      series=self.found['name'], number='10'))['path'])

    def test_without_approval_the_book_is_held_unchanged_and_says_why(self):
        import series_backfill
        backfill = self.lib.backfill()
        backfill.apply(self.lib.job_id, self.found)
        self.assertEqual(self.lib.state(backfill), ('held', series_backfill.MOVE_WAITS), 'was: "The recorded series paths do not share their original parent"')
        self.assertNotEqual(self.series_path.parent, self.lib.path.parent, 'the series folder is another folder')
        self.assertEqual(sha(self.lib.path), self.lib.original)
        self.assertFalse(self.series_path.exists())
        self.assertEqual(backfill.entry(self.lib.job_id)['record']['series'], 'Нормальное аномальное', 'the plan reads the series it found')

    def test_approved_the_series_is_written_then_the_verified_move_takes_it_to_the_series_folder(self):
        import book_delete, book_move
        from publication_binding import PublicationBindings
        from scanner import connect
        lib = self.lib
        calls = []

        def resolve(job_id, kind):
            with connect(lib.db) as db:
                record = json.loads(db.execute('SELECT output FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()[0])
            return PublicationBindings(str(lib.db)).current(record, kind)[0]

        def follow_up(job_id, approved, placed):
            calls.append((approved, placed))
            start = book_move.location(resolve(job_id, 'base'))
            with connect(lib.db) as db:
                move = book_move.plan(db, job_id=job_id, kind='base', candidate_id=lib.candidate, start=start, folder=str(Path(approved).parent),
                                      root=str(lib.root), name=Path(approved).name)
            mover = book_move.Mover(lambda: connect(lib.db), resolve, sources=lambda: (str(lib.source_root),), output_root=str(lib.root),
                                    remove_folder=book_delete._remove_folder, protected_roots=lambda: (str(lib.root), str(lib.source_root)))
            return {'state': mover.run(move['move_id'])['state']}
        merge = lib.merge()
        merge.sorting_follow_up = follow_up
        merge.sorting_target = lambda job_id, series=None: str(self.series_path)
        backfill = lib.backfill(merge=merge, found=None)  # no lookup: the approved series is used
        backfill.apply(lib.job_id, self.found)
        self.assertEqual(lib.state(backfill)[0], 'held')
        backfill.approve(lib.job_id, self.found, str(self.series_path))
        self.assertEqual(lib.state(backfill), ('pending', ''))
        backfill.run_pass()
        entry = backfill.entry(lib.job_id)
        self.assertEqual(entry['state'], 'done', entry['reason'])
        placed = lib.path.parent / self.series_path.name
        self.assertEqual(calls, [(str(self.series_path), str(placed))], 'written in its own folder first, then moved')
        self.assertEqual(entry['record']['follow_up']['state'], 'complete')
        self.assertTrue(self.series_path.exists())
        self.assertFalse(lib.path.exists())
        self.assertFalse(placed.exists())
        self.assertEqual(resolve(lib.job_id, 'base')['final_path'], str(self.series_path), 'the catalog follows the move')
        self.assertEqual(json.loads(lib.row()['manifest'])['metadata']['series'], 'Нормальное аномальное')

    def test_a_book_held_by_the_old_bug_is_looked_up_once_more_and_then_waits_for_approval(self):
        import series_backfill
        backfill = self.lib.backfill()
        backfill._set(self.lib.job_id, 'held', series_backfill.OLD_FOLDER_REASON, {'series': 'Старое имя', 'number': '10', 'provider': 'fantlab'})
        self.assertEqual([r['job_id'] for r in backfill.candidates()], [self.lib.job_id], 'was: final, never looked at again')
        backfill.run_pass()
        self.assertEqual(self.lib.state(backfill), ('held', series_backfill.MOVE_WAITS))
        self.assertEqual(backfill.entry(self.lib.job_id)['record']['series'], 'Нормальное аномальное', 'the series found again, under the new rules')
        self.assertEqual(sha(self.lib.path), self.lib.original, 'a lookup only: the file is untouched')
        self.assertEqual(backfill.candidates(), [], 'then it waits for approval; never looked up again by itself')

    def test_approval_of_a_changed_place_changes_nothing(self):
        merge = self.lib.merge()
        merge.sorting_target = lambda job_id, series=None: str(self.lib.root / 'Elsewhere' / self.series_path.name)
        backfill = self.lib.backfill(merge=merge, found=None)
        backfill.apply(self.lib.job_id, self.found)
        backfill.approve(self.lib.job_id, self.found, str(self.series_path))
        backfill.run_pass()
        self.assertEqual(self.lib.state(backfill)[0], 'held')
        self.assertIn('changed since you approved', self.lib.state(backfill)[1])
        self.assertEqual(sha(self.lib.path), self.lib.original)


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class NamedMoveTests(unittest.TestCase):
    """The usual verified move (book_move) can give the book its new name in the new folder (items 5 and 6)."""

    def test_a_move_with_a_new_name_renames_the_exact_file(self):
        import test_book_move
        case = test_book_move.StrategyTests('test_never_reconverts')
        case.setUp()
        self.addCleanup(case.doCleanups)
        target = case.sorted / 'Rowling J. K'
        start = __import__('book_move').location(case.resolve(case.job_id, 'base'))
        with __import__('scanner').connect(case.db) as db:
            move = __import__('book_move').plan(db, job_id=case.job_id, kind='base', candidate_id=case.candidate, start=start, folder=str(target),
                                                root=str(case.sorted), name='Book - Rowling J. K.m4b')
        done = case.mover().run(move['move_id'])
        self.assertEqual(done['state'], 'complete')
        self.assertEqual((target / 'Book - Rowling J. K.m4b').read_bytes(), case.payload)
        self.assertFalse(case.old.exists())
        self.assertEqual(case.effective()['final_path'], str(target / 'Book - Rowling J. K.m4b'))
        with __import__('scanner').connect(case.db) as db, self.assertRaises(__import__('book_move').Refused):
            __import__('book_move').plan(db, job_id=case.job_id, kind='base', candidate_id=case.candidate, start=start, folder=str(target),
                                         root=str(case.sorted), name='..\\escape.m4b')


if __name__ == '__main__':
    unittest.main()
