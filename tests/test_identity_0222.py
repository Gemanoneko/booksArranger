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
