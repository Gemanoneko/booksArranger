"""0.22.2 identity items on the live rows (names and tags as the catalog holds them, 2026-10-26).

- Senua's 0.22.1 review W17: a single file with no title tag kept in its title a co-author its author tag did not name
  («С. Лукьяненко, И. Кузнецов - Печать сумрака» tagged only Лукьяненко) and could convert with no question.
- W18: _title_credit compared every author-tag person of every file with every library reader, eagerly (21.3 s for a
  240-file book with 1,000 readers).
- «Призрак дома на холме» (Sergei 2026-10-26: "There was an author in the name."): the album tag «Ширли Джексон -
  Призрак дома на холме», the only credit a reader (Пухов), the composer tag and the folder name the author. The row said
  "No author in the tags, file name or folder name" and the title kept «Ширли Джексон - ».
- «Джек из Тени» (Zelazny): «Роджер Желязны» never matched the library's «Roger Zelazny» (Ж is a Latin Z, «Роджер» was
  no first name), so the destination showed a Russian folder for an English author.
- Futaba's 0.22.1 QA m-14: the Same author? card on «Robert_Heinlein» showed and filed the underscores.
- Ruling 33 (Sergei 2026-10-26, m-13): a Latin "Given Surname" name is filed surname first; one person gets one folder,
  picked by writing language; where the language is unknown the row asks.
Catalog rows only; no file, no network."""
import contextlib, sqlite3, time, unittest
from pathlib import Path
from unittest.mock import patch

import author_rules
import local_identity
from test_folder_structure import Base, ROOT, SORTED, file_row


class TitleCreditCostTests(Base):
    def test_a_240_file_book_with_1000_library_readers_reads_its_folders_in_well_under_a_second(self):
        # W18: one entry per file and per reader, compared pairwise (240 x 1,000 same_person calls).
        rows = [file_row('Clive Barker\\Books of Blood\\3. Сын целлулоида\\%03d.mp3' % n, title='Сын целлулоида', album='Сын целлулоида',
                         artist='Clive Barker', narrator='Игорь Князев', track='%d' % n) for n in range(1, 241)]
        row = self.catalog(rows)[ROOT + '\\Clive Barker\\Books of Blood\\3. Сын целлулоида']
        index = {'readers': frozenset('Чтец Номер%04d' % n for n in range(1000))}
        calls = []
        real = local_identity.same_person
        with patch.object(local_identity, 'same_person', lambda a, b: calls.append(1) or real(a, b)):
            started = time.perf_counter()
            structure = local_identity.folder_structure(row, ROOT, index)
            took = time.perf_counter() - started
        self.assertEqual((structure['series'], structure['position'], structure['title']), ('Books of Blood', '3', 'Сын целлулоида'))
        self.assertLess(len(calls), 3000, 'each distinct credit is compared with each distinct reader at most once')
        self.assertLess(took, 1.0)
        # Positive control: a reader before the title is still a credit of this book and leaves the title.
        rows = [file_row('Clive Barker\\Books of Blood\\3. Игорь Князев - Ревущий мясник.m4b', artist='Clive Barker', narrator='Игорь Князев')]
        row = next(iter(self.catalog(rows).values()))
        self.assertEqual(local_identity.folder_structure(row, ROOT, index)['title'], 'Ревущий мясник')


class CoAuthorTitleTests(Base):
    DOZORY = 'Сергей Лукьяненко\\Вселенная Дозоров - Межавторский цикл\\'

    def test_a_co_author_the_tag_does_not_name_is_asked_never_filed_in_the_title(self):
        # W17: no title tag, the author tag names only one of the two people the file name credits.
        row = next(iter(self.catalog([file_row(self.DOZORY + '05 - С. Лукьяненко, И. Кузнецов - Печать сумрака (август 2003 - апрель 2004).m4b',
                                               artist='Сергей Лукьяненко')]).values()))
        result = self.lookup(row)
        self.assertTrue(result['reasons'], 'held, never filed by itself')
        self.assertEqual(result['ask']['kind'], 'author_unclear')
        self.assertEqual(result['ask']['fields']['title']['proposal'], 'Печать сумрака', 'the people are no part of the title')
        names = [c['name'] for c in result['ask']['candidates']]
        self.assertTrue(any('Кузнецов' in name for name in names), names)
        self.assertNotIn('Лукьяненко', self.approved(row)['title'])
        # Controls: both people tagged (live «Печать сумрака» carries both) is the two-people question as before; the
        # book's own author alone before the title is a credit; a person who is neither stays in the title (W8).
        row = next(iter(self.catalog([file_row(self.DOZORY + '05 - С. Лукьяненко, И. Кузнецов - Печать сумрака (август 2003 - апрель 2004).m4b',
                                               title='Печать сумрака', artist='С. Лукьяненко, И. Кузнецов', album='Печать сумрака')]).values()))
        self.assertEqual(self.lookup(row)['ask']['why'], 'two_people')
        row = next(iter(self.catalog([file_row(self.DOZORY + '10 - Сергей Лукьяненко - Сумеречный дозор (лето 2003).m4b', artist='Сергей Лукьяненко')]).values()))
        self.assertEqual(self.approved(row)['title'], 'Сумеречный дозор')
        row = next(iter(self.catalog([file_row('Стефан Цвейг\\Биографии\\03 - Жозеф Фуше - Портрет политического деятеля.m4b', artist='Стефан Цвейг')]).values()))
        self.assertEqual(self.approved(row)['title'], 'Жозеф Фуше - Портрет политического деятеля')


class ReaderOnlyCreditTests(Base):
    LIVE = dict(title='Призрак дома на холме', artist='Пухов Сергей', album='Ширли Джексон - Призрак дома на холме', comment='https://vk.com/puhovsergey',
                genre='Audiobook', date='2017', composer='Ширли Джексон', album_artist='Пухов Сергей')

    def test_shirley_jackson_is_the_author_and_leaves_the_title_and_the_file_name_is_the_original_title(self):
        row = next(iter(self.catalog([file_row('Shirley Jackson\\The Haunting of Hill House.m4b', **self.LIVE)]).values()))
        record, _ = self.research.identity(row, ROOT)
        self.assertNotEqual((record.get('ask') or {}).get('why'), 'author_missing', 'the name names the author')
        shown = self.approved(row)
        self.assertEqual(shown['author'], 'Ширли Джексон', 'the row shows the author it resolved')
        self.assertNotIn('Ширли Джексон', shown['title'])
        # Ruling 29: the file name carries the English original, so nothing waits for it.
        self.assertEqual(shown['title'], 'The Haunting of Hill House')
        self.assertEqual(self.goes_to(row, self.research.approved(row, ROOT)), SORTED + '\\Jackson Shirley\\The Haunting of Hill House - Jackson Shirley.m4b')
        self.assertIn('Призрак дома на холме', local_identity.title_forms(record), 'the translation stays an alias')

    def test_a_leading_name_counts_when_the_folder_or_the_composer_names_the_same_person(self):
        # A first name no list knows: the folder or the composer tag corroborates the person before the dash.
        for folder, composer in (('Лорна Кук', ''), ('Unsorted', 'Лорна Кук')):
            tags = dict(self.LIVE, album='Лорна Кук - Забытый сад', title='Забытый сад', composer=composer)
            row = next(iter(self.catalog([file_row(folder + '\\Забытый сад.m4b', **tags)]).values()))
            shown = self.approved(row)
            self.assertEqual(shown['title'], 'Забытый сад', folder)
            self.assertIn('Кук', shown['author'], folder)
        # Control: nothing corroborates the piece and no list knows the name: the title is kept, nothing is guessed.
        tags = dict(self.LIVE, album='Лорна Кук - Забытый сад', title='Забытый сад', composer='')
        row = next(iter(self.catalog([file_row('Unsorted\\Забытый сад.m4b', **tags)]).values()))
        self.assertNotEqual(self.approved(row)['author'], 'Кук Лорна')


class NameMatcherTests(Base):
    def test_zhelyazny_is_zelazny_and_roger_is_a_first_name(self):
        self.assertTrue(local_identity.same_person('Роджер Желязны', 'Roger Zelazny'))
        self.assertTrue(local_identity.looks_like_person('Роджер Желязны'))
        self.assertTrue(local_identity.looks_like_person('Ширли Джексон'))
        self.assertTrue(local_identity.same_person('Ширли Джексон', 'Shirley Jackson'))
        # Controls: Ж is still the zh sound, and different names stay different.
        self.assertTrue(local_identity.same_person('Жуков Георгий', 'Zhukov Georgy'))
        self.assertFalse(local_identity.same_person('Желязны Роджер', 'Zelenski Roger'))

    def test_jack_of_shadows_files_under_the_english_folder_of_its_author(self):
        rows = [file_row('Roger Zelazny\\Джек из Тени.m4b', album='Джек из Тени', artist='Роджер Желязны', title='Джек из Тени',
                         genre='Научная фэнтези', composer='Дмитрий Оргин', album_artist='Роджер Желязны')]
        row = next(iter(self.catalog(rows).values()))
        self.assertEqual(self.goes_to(row, self.research.approved(row, ROOT)), SORTED + '\\Zelazny Roger\\Джек из Тени - Zelazny Roger.m4b')


class SameAuthorUnderscoreTests(Base):
    def test_the_same_author_card_never_shows_or_files_underscores(self):
        # Futaba's lab: "Heinlein Robert A" is the seeded rules' folder for «Роберт Хайнлайн»; no other book of his is in the catalog.
        rows = [file_row('Unsorted\\Robert_Heinlein - Dver_v_leto\\%02d.m4a' % n, title='Дверь в лето', album='Дверь в лето', track='%d' % n) for n in (1, 2)]
        books = self.catalog(rows)
        row = books[ROOT + '\\Unsorted\\Robert_Heinlein - Dver_v_leto']
        result = self.lookup(row)
        ask = result.get('ask') or {}
        self.assertEqual(ask.get('kind'), 'same_author', result['reasons'])
        self.assertEqual(ask['new'], 'Robert Heinlein')
        self.assertNotIn('_', ask['fields']['author']['proposal'])
        # Different author: the cleaned name, surname first.
        different = self.research.approved(row, ROOT, chosen=ask['new'])
        self.assertEqual(self.goes_to(row, different), SORTED + '\\Heinlein Robert\\Дверь в лето - Heinlein Robert.m4b')


class LatinGivenSurnameTests(Base):
    """Ruling 33 (Sergei 2026-10-26)."""

    def test_a_latin_given_surname_name_is_filed_surname_first_and_typed_names_are_never_flipped_back(self):
        self.assertEqual(local_identity.surname_first('Ilya Marchenko')[0], 'Marchenko Ilya')
        self.assertEqual(local_identity.surname_first('Hanna Kovalska')[0], 'Kovalska Hanna')
        self.assertEqual(local_identity.surname_first('Marchenko Ilya')[0], 'Marchenko Ilya')
        self.assertEqual(local_identity.surname_first('Robert Heinlein')[0], 'Heinlein Robert')  # control

    def test_one_person_one_folder_by_writing_language(self):
        # The library already files «Марченко Илья» in Cyrillic in Audiobooks Sorted (a converted book): the Latin credit joins
        # that folder, never a second "Marchenko Ilya" one.
        rows = [file_row('Unsorted\\Ilya Marchenko - Zvezda.m4b', title='Звезда', artist='Ilya Marchenko', album='Звезда')]
        books = self.catalog(rows)
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY, manifest TEXT, updated TEXT)')
            db.execute("INSERT INTO audio_jobs VALUES('done', ?, '2026-10-26T00:00:00Z')", ('{"metadata": {"author": "Марченко Илья"}}',))
            db.commit()
        row = books[ROOT + '\\Unsorted\\Ilya Marchenko - Zvezda.m4b']
        result = self.lookup(row)
        self.assertFalse(result['reasons'], result.get('ask'))
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Марченко Илья\\Звезда - Марченко Илья.m4b')

    def test_m1_his_answer_to_the_spelling_question_decides_the_folder(self):
        # Futaba's 0.22.2 QA, M-1 (rulings 6a and 33): choosing «Марченко Илья» for the credit "Ilya Marchenko" filed the
        # book under "Marchenko Ilya": the library's Latin spelling won the vote over his answer.
        rows = [file_row('Unsorted\\Ilya Marchenko - Zvezda.m4b', title='Звезда', artist='Ilya Marchenko', album='Звезда')]
        row = next(iter(self.catalog(rows).values()))
        self.assertEqual(self.lookup(row)['ask']['why'], 'name_language', 'positive control: the row asks')
        for typed, folder in (('Марченко Илья', 'Марченко Илья'), ('Илья Марченко', 'Марченко Илья'), ('Ilya Marchenko', 'Marchenko Ilya'), ('Marchenko Ilya', 'Marchenko Ilya')):
            with self.subTest(typed=typed):
                result = self.research.approved(row, ROOT, author=typed)
                self.assertFalse(result['reasons'], result['reasons'])
                self.assertEqual(self.goes_to(row, result), SORTED + '\\%s\\Звезда - %s.m4b' % (folder, folder))
        # Control: an approval without a typed author still takes the library's spelling (one person, one folder).
        self.assertEqual(self.goes_to(row, self.research.approved(row, ROOT)), SORTED + '\\Marchenko Ilya\\Звезда - Marchenko Ilya.m4b')

    def test_an_unknown_writing_language_is_asked_with_both_spellings(self):
        rows = [file_row('Unsorted\\Ilya Marchenko - Zvezda.m4b', title='Звезда', artist='Ilya Marchenko', album='Звезда')]
        row = next(iter(self.catalog(rows).values()))
        result = self.lookup(row)
        self.assertEqual((result['ask']['kind'], result['ask']['why']), ('author_unclear', 'name_language'))
        self.assertEqual([c['name'] for c in result['ask']['candidates']], ['Marchenko Ilya', 'Марченко Илья'])
        self.assertEqual(result['ask']['fields']['author']['proposal'], 'Marchenko Ilya')
        self.assertTrue(result['ask'].get('odd_name'), 'each is answered on its own row, never by bulk Approve as is')
        # Controls: an English given name in Latin letters is filed as before, with no question.
        rows = [file_row('Unsorted\\Richard Matheson - I Am Legend.m4b', title='I Am Legend', artist='Richard Matheson', album='I Am Legend')]
        row = next(iter(self.catalog(rows).values()))
        result = self.lookup(row)
        self.assertFalse(result['reasons'], result.get('ask'))
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Matheson Richard\\I Am Legend - Matheson Richard.m4b')


if __name__ == '__main__':
    unittest.main()


class TranslationNoWaitTests(Base):
    """Ruling 38 (Sergei 2026-10-27; it replaces the waiting part of ruling 29): a translation with only its Russian title
    never waits. Research uses the English original title when it has it (the research cache's catalog answer); else
    the book converts right away under the title it has, its author folder English for a non-Russian author. The
    background pass still asks for the English title once it is converted (the rename pass applies it later)."""
    JACK = [file_row('Roger Zelazny\\Джек из Тени.m4b', album='Джек из Тени', artist='Роджер Желязны', title='Джек из Тени', album_artist='Роджер Желязны')]
    CATALOG = {'language': 'en', 'original_title': 'Jack of Shadows', 'title_native': 'Джек из Тени', 'author_native': 'Роджер Желязны',
               'author_latin': 'Roger Zelazny', 'source_url': 'https://fantlab.ru/work1'}

    def test_a_translation_with_no_english_title_converts_now_under_its_title_in_the_english_author_folder(self):
        row = next(iter(self.catalog(self.JACK).values()))
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [], 'no "Waiting for the original title"')
        self.assertFalse(result.get('wait'), 'no wait of any kind')
        self.assertEqual(result['review']['title'], 'Джек из Тени')
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Zelazny Roger\\Джек из Тени - Zelazny Roger.m4b', 'the author folder stays English')
        self.assertEqual(result['metadata_facts']['original_title_lookup'], {'state': 'none', 'title': ''}, 'the details panel: not found, filed under its title')
        self.assertIn('original_title', result['metadata_facts']['gap_search']['background'], 'asked in the background once converted (the rename pass, later)')
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='original_titles'").fetchone(), 'research writes nothing to wait on')

    def test_an_english_title_the_research_has_is_used(self):
        row = next(iter(self.catalog(self.JACK).values()))
        with patch.object(self.research, '_gap_fill', return_value={'catalog': dict(self.CATALOG), 'closed': [], 'unfilled': []}):
            result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Zelazny Roger\\Jack of Shadows - Zelazny Roger.m4b')
        self.assertEqual(result['metadata_facts']['original_title_lookup'], {'state': 'found', 'title': 'Jack of Shadows'})

    def test_sergeis_approve_files_it_as_shown_and_a_russian_author_converts_with_no_lookup_fact(self):
        row = next(iter(self.catalog(self.JACK).values()))
        approved = self.research.approved(row, ROOT)
        self.assertEqual(approved['reasons'], [], 'Approve files it as shown')
        self.assertEqual(approved['review']['title'], 'Джек из Тени')
        row = next(iter(self.catalog([file_row('Лукьяненко Сергей\\Лабиринт отражений.m4b', title='Лабиринт отражений', artist='Сергей Лукьяненко', album='Лабиринт отражений')]).values()))
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [], 'written in Russian: converts now')
        self.assertNotIn('original_title_lookup', result['metadata_facts'], 'no translation, no "Original title" fact')


class ForeignCyrillicAuthorTests(Base):
    """Ruling 39 (Sergei 2026-10-27, "2 and then 3 if not found in 2"): a foreign author credited only in Cyrillic. Research
    looks the author's original-language name up online (FantLab, Wikidata, Goodreads, through the client); what it
    finds is a lasting rule for that credit (once per author). Nothing found: Sergei is asked once per author (Author
    unclear), never a transliteration."""
    GOLIATH = file_row('Steampunk\\Голиаф.m4b', title='Голиаф', album='Голиаф', artist='Скотт Вестерфельд')
    LEVIATHAN = file_row('Steampunk\\Левиафан.m4b', title='Левиафан', album='Левиафан', artist='Вестерфельд Скотт')
    ENTRY = {'provider': 'fantlab', 'work_id': 'fantlab:2', 'source_url': 'https://fantlab.ru/work2', 'language': 'en', 'original_title': 'Goliath',
             'title_native': 'Голиаф', 'author_native': 'Скотт Вестерфельд', 'author_latin': 'Scott Westerfeld'}

    def rules(self):
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            return [tuple(r) for r in db.execute("SELECT kind, credit_key, target, actor FROM author_rules WHERE rule_id NOT LIKE 'seed-%' ORDER BY saved_utc")]

    def online(self, entries):
        """_gap_fantlab answering only a request that may go online (research's budget), never the cache-only pass."""
        asked = []
        def fantlab(title, author, partial, stop, budget, result):
            if (budget or {}).get('remaining', 0) <= 0:
                return None
            asked.append(title)
            return dict(entries[title]) if title in entries else None
        return patch.object(self.research, '_gap_fantlab', side_effect=fantlab), asked

    def test_nothing_found_online_asks_once_per_author_and_never_transliterates(self):
        books = self.catalog([self.GOLIATH])
        row = next(iter(books.values()))
        result = self.lookup(row)
        self.assertEqual(result['reasons'], ['Author unclear'], 'held for his answer, not filed under the Cyrillic credit')
        ask = result['ask']
        self.assertEqual((ask['kind'], ask['why'], ask['credit']), ('author_unclear', 'english_spelling', 'Вестерфельд Скотт'))
        self.assertEqual([c['name'] for c in ask['candidates']], ['Вестерфельд Скотт'], 'keep it, or type the English spelling')
        self.assertTrue(ask['odd_name'], 'never in a bulk Approve')
        self.assertEqual(local_identity.script(ask['fields']['author']['proposal']), 'cyrillic', 'no transliteration proposed')
        calls = ' '.join(self.research.client.calls)
        for host in ('api.fantlab.ru', 'wikidata.org', 'goodreads.com'):
            self.assertIn(host, calls, 'looked up online first: ' + host)
        self.assertEqual(self.rules(), [], 'nothing learned from nothing')

    def test_a_name_found_online_files_the_book_and_every_other_book_of_the_author(self):
        books = self.catalog([self.GOLIATH, self.LEVIATHAN])
        goliath, leviathan = books[ROOT + '\\Steampunk\\Голиаф.m4b'], books[ROOT + '\\Steampunk\\Левиафан.m4b']
        online, asked = self.online({'Голиаф': self.ENTRY})
        with online:
            result = self.lookup(goliath)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(self.goes_to(goliath, result), SORTED + '\\Westerfeld Scott\\Goliath - Westerfeld Scott.m4b', 'the English name and title the record gives')
        self.assertEqual(result['metadata_facts']['original_title_lookup'], {'state': 'found', 'title': 'Goliath'})
        self.assertEqual(self.rules(), [('same_as', author_rules.key('Скотт Вестерфельд'), 'Westerfeld Scott', 'assistant')], 'learned once, for the credit')
        online, asked = self.online({})
        with online:
            result = self.lookup(leviathan)
        self.assertEqual(asked, [], 'the author\'s next book needs no lookup')
        self.assertEqual(result['reasons'], [])
        self.assertEqual(self.goes_to(leviathan, result), SORTED + '\\Westerfeld Scott\\Левиафан - Westerfeld Scott.m4b', 'no English title for it: its own')

    def test_a_work_written_in_russian_keeps_the_cyrillic_name(self):
        row = next(iter(self.catalog([file_row('Перумов Ник\\Эльфийская стража.m4b', title='Эльфийская стража', album='Эльфийская стража', artist='Ник Перумов')]).values()))
        online, asked = self.online({'Эльфийская стража': {'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work3', 'language': 'ru', 'original_title': 'Эльфийская стража',
                                                            'author_native': 'Ник Перумов', 'author_latin': 'Nick Perumov'}})
        with online:
            result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Перумов Ник\\Эльфийская стража - Перумов Ник.m4b')
        self.assertEqual(self.rules(), [('keep', author_rules.key('Ник Перумов'), '', 'assistant')], 'never asked or looked up again')

    def test_ruling_59_approve_keeps_the_english_question_without_lookup_and_typed_english_decides(self):
        row = next(iter(self.catalog([self.GOLIATH]).values()))
        online, asked = self.online({'Голиаф': self.ENTRY})
        with online:
            shown = self.research.approved(row, ROOT)
            typed = self.research.approved(row, ROOT, author='Scott Westerfeld')
        self.assertEqual(asked, [], 'Approve makes no request (rulings 39 and 59)')
        self.assertEqual(shown['ask']['why'], 'english_spelling')
        self.assertIsNone(shown['review'], 'unresolved English spelling cannot plan a Cyrillic filing')
        self.assertEqual(typed['reasons'], [])
        self.assertEqual(self.goes_to(row, typed), SORTED + '\\Westerfeld Scott\\Голиаф - Westerfeld Scott.m4b')
