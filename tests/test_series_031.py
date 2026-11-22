"""0.31.0 step 1, "use what the files say" (Sergei 2026-11-22, Docs/BooksArranger_0.31.0_Scope.md; rulings R4 and R7).

1a  a volume the app separated itself is named from its own title tag, as one Sergei kept separate is;
1b  the series and the book's number are read from the sort-album and grouping tags, and file the book without asking.

Fixtures are the tags of his own files, read from a copy of the live catalog on 2026-11-22: the two Sprawl volumes held as
"Part of a bigger book" and going to one destination, «Тёмный лес» with no series, and every sort-album and grouping shape
that carries a book number on his 1,510 current books. Catalog rows only; no file, no network."""
import contextlib
import sqlite3
import unittest

import author_rules
import groups
import local_identity
from test_folder_structure import Base, file_row, ROOT, SORTED

GIBSON = 'William Gibson\\'
SPRAWL = {'neuromancer': GIBSON + 'Уильям Гибсон - 01-Нейромант.m4b', 'count zero': GIBSON + 'Уильям Гибсон - 02-Граф Ноль.m4b',
          'mona lisa': GIBSON + 'Уильям Гибсон - 03-Мона Лиза овердрайв.m4b'}
DARK_FOREST = 'ПАМЯТЬ О ПРОШЛОМ ЗЕМЛИ\\Лю Цысинь - Тёмный лес (Оробчук С.)\\'


def sprawl_rows():
    # The first file carries no album tag (Sergei approved it by hand as Neuromancer, Sprawl Trilogy 1).
    return [file_row(SPRAWL['neuromancer'], disc='1', title='Sprawl Trilogy 01 - Neuromancer', artist='William Gibson', date='2015'),
            file_row(SPRAWL['count zero'], disc='2', title='Sprawl Trilogy 02 - Count Zero', artist='William Gibson', album='Sprawl Trilogy', date='2015'),
            file_row(SPRAWL['mona lisa'], disc='3', title='Sprawl Trilogy 03 - Mona Lisa Overdrive', artist='William Gibson', album='Sprawl Trilogy', date='2015')]


def dark_forest_rows():
    return [file_row(DARK_FOREST + 'Тёмный лес %d.m4b' % n, album='Тёмный лес', artist='Лю Цысинь', title='Тёмный лес', composer='Сергей Оробчук', genre='Фантастика',
                     comment='Для библиотеки WWW.AUDIOKNIGA.ORG (shniferson)', sort_album='Память о прошлом Земли. Книга 2', track='%d/2' % n) for n in (1, 2)]


class Fixture(Base):
    def shelf(self, rows, volumes=(), kept=()):
        """{file or folder: row} as the catalog groups them, with the recorded separate volumes (part_volumes)."""
        self.catalog(rows)
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            # His lasting answer for this credit, as the live catalog holds it (ruling 12): «Лю Цысинь» is filed as Cixin Liu.
            author_rules.append(db, 'same_as', 'Лю Цысинь', target='Cixin Liu', source='test')
            db.commit()
        found = {}
        for n, (scope, group) in enumerate(groups.build(rows, volumes=frozenset(volumes), kept=frozenset(kept)).items()):
            row = dict(group, id='book-%d' % n, revision=1, fingerprint='fp-%d' % n, source_root=ROOT)
            found[group['members'][0]['path'] if len(group['members']) == 1 else scope] = row
        return found


class SeparatedVolumeTests(Fixture):
    """1a: Sergei's report 1. Two files, both titled "Sprawl Trilogy", both going to one file, offered "Approve as one book"."""

    def volumes(self, kept=False):
        rows = sprawl_rows()
        paths = [ROOT + '\\' + SPRAWL[name] for name in ('count zero', 'mona lisa')]
        books = self.shelf(rows, volumes=paths, kept=paths if kept else ())
        return [books[path] for path in paths]

    def test_the_two_sprawl_volumes_are_count_zero_and_mona_lisa_overdrive_in_their_series(self):
        found = []
        for row in self.volumes():
            self.assertEqual(row['volume_of_set'], {'kept': False}, 'positive control: separated by the app, not by Sergei')
            result = self.lookup(row)
            self.assertEqual(result['reasons'], [], 'no longer "One part of a bigger book"')
            self.assertIsNone(result.get('ask'), 'the album tag names the series the title tag carries: filed without a question (R4)')
            review = result['review']
            found.append((review['title'], review['series'], review['number'], self.goes_to(row, result)))
        self.assertEqual(found, [
            ('Count Zero', 'Sprawl Trilogy', '2', SORTED + '\\Gibson William\\Sprawl Trilogy\\Sprawl Trilogy - 2 - Count Zero - Gibson William.m4b'),
            ('Mona Lisa Overdrive', 'Sprawl Trilogy', '3', SORTED + '\\Gibson William\\Sprawl Trilogy\\Sprawl Trilogy - 3 - Mona Lisa Overdrive - Gibson William.m4b')])

    def test_the_fix_is_the_volume_fact_and_nothing_else(self):
        # Positive control: the same two rows read without their volume fact (before 0.31.0 only {'kept': True} took the
        # branch, so {'kept': False} read as no fact at all) are one part each, named from the album: the held record of
        # both live rows on 2026-11-22, word for word.
        for volume in self.volumes():
            row = {key: value for key, value in volume.items() if key != 'volume_of_set'}
            result = self.lookup(row)
            self.assertEqual(result['reasons'], ['One part of a bigger book'])
            self.assertEqual(result['identity_hold'], {'kind': 'piece', 'detail': '1 other file(s) beside it carry this title; this may be only part of the book',
                                                       'piece': {'piece': 'siblings', 'count': 1}})
            self.assertEqual(result['local_agreement']['title']['value'], 'Sprawl Trilogy')
        # And before the app separated them they were one row of two files (the row "Approve as one book" was offered on).
        together = self.shelf(sprawl_rows())
        self.assertEqual(sorted(len(row['members']) for row in together.values()), [1, 2])

    def test_a_volume_the_app_separated_reads_exactly_as_one_sergei_kept(self):
        def read(rows):
            return [(i['fields']['title']['value'], i['series'], i['accepted'], i['held'], i['series_unconfirmed']) for i in (self.research.identity(r, ROOT)[0] for r in rows)]
        separated = read(self.volumes())
        self.assertEqual(separated, read(self.volumes(kept=True)))
        self.assertEqual(separated[0], ('Count Zero', {'name': 'Sprawl Trilogy', 'number': '2'}, True, '', False))

    def test_a_title_tag_alone_still_asks_about_its_series(self):
        # Ruling 52 stands for a name nothing confirms: the first file has no album tag and is no volume of a set.
        row = self.shelf(sprawl_rows())[ROOT + '\\' + SPRAWL['neuromancer']]
        self.split_asked(row, 'Sprawl Trilogy', '1', 'Neuromancer')

    def test_a_volume_with_no_title_of_its_own_keeps_its_set_name_and_number(self):
        # Торадора! (ruling 13): the title tag only repeats the set and a volume number; named "Торадора! 1" as before.
        rows = [file_row('Light Novels\\Yuyuko Takemiya\\Toradora!\\Торадора! Том %d.m4b' % n, album='Торадора!', title='Торадора! Том %d' % n,
                         artist='Ююко Такэмия', track='%d/2' % n) for n in (1, 2)]
        books = self.shelf(rows, volumes=[r['path'] for r in rows])
        titles = [self.research.identity(books[r['path']], ROOT)[0]['fields']['title']['value'] for r in rows]
        self.assertEqual(titles, ['Торадора! 1', 'Торадора! 2'])


class RecheckTests(SeparatedVolumeTests):
    """1d: existing held rows of these shapes are read once more from their files, with no online request."""

    # The held record of «02-Граф Ноль» as the live catalog stored it on 2026-11-01 (its fields that decide).
    HELD = {'state': 'Held', 'until_change': True, 'retry_at': None, 'research_version': 'standing-24-v1', 'reasons': ['One part of a bigger book'], 'ask': None,
            'identity_hold': {'kind': 'piece', 'detail': '1 other file(s) beside it carry this title; this may be only part of the book',
                              'piece': {'piece': 'siblings', 'count': 1}}}

    def test_which_recorded_holds_are_read_again(self):
        import public_research
        self.assertEqual(self.HELD['research_version'], public_research.RESEARCH_VERSION, 'no new research version: nothing else is read again')
        asked = dict(self.HELD, reasons=['Title or author missing'], identity_hold={'kind': 'title_author', 'detail': ''},
                     ask={'kind': 'title_author', 'why': 'title_series', 'split': {'series': 'Вымирание', 'number': '1', 'title': 'Код'}})
        for record in (self.HELD, asked):
            self.assertTrue(public_research.needs_local_recheck(record))
            self.assertFalse(public_research.needs_local_recheck(dict(record, local_recheck=public_research.LOCAL_RECHECK)), 'once')
        # Тёмный лес (a set its chapters do not settle), an author question and a book with no hold keep their record.
        others = (dict(self.HELD, identity_hold={'kind': 'piece', 'detail': '', 'piece': {'piece': 'set', 'cause': 'seasons', 'parts': 2}}),
                  dict(self.HELD, identity_hold={'kind': 'author_unclear', 'detail': ''}, ask={'kind': 'author_unclear', 'why': 'english_spelling'}),
                  dict(self.HELD, identity_hold=None), {}, None)
        for record in others:
            self.assertFalse(public_research.needs_local_recheck(record), record)

    def test_the_automatic_pass_reads_such_a_book_again_once(self):
        import public_research
        from automatic_processing import AutomaticProcessing
        again = AutomaticProcessing._refresh_wait(None, {'id': 'count-zero'}, dict(self.HELD))
        self.assertEqual((again['until_change'], again['retry_at']), (False, None), 'researched at the next visit although nothing about it changed')
        read = dict(self.HELD, local_recheck=public_research.LOCAL_RECHECK)
        self.assertTrue(AutomaticProcessing._refresh_wait(None, {'id': 'count-zero'}, read)['until_change'], 'a record read under the new rules waits for a change, as before')

    def test_the_new_reading_is_stamped_and_asks_no_online_source(self):
        import public_research
        for row in self.volumes():
            result = self.lookup(row)
            self.assertEqual((result['reasons'], result['local_recheck']), ([], public_research.LOCAL_RECHECK), 'the two Sprawl rows fix themselves')
            self.assertEqual(self.research.client.calls, [], 'read from the files only')
        # A book that stays held is stamped too (never read twice) and asks nothing either.
        row = {key: value for key, value in self.volumes()[0].items() if key != 'volume_of_set'}
        result = self.lookup(row)
        self.assertEqual((result['reasons'], result['local_recheck']), (['One part of a bigger book'], public_research.LOCAL_RECHECK))
        self.assertEqual(self.research.client.calls, [])


class TagSeriesTests(Fixture):
    """1b: the sort-album and grouping tags name the series and the number (R4: filed without asking)."""

    def test_every_measured_shape(self):
        named = {'Клейн. Книга 2': ('Клейн', '2'), 'Память о прошлом Земли. Книга 2': ('Память о прошлом Земли', '2'),
                 'Гарри Поттер - Книга 1': ('Гарри Поттер', '1'), 'Mass Effect - Книга 1': ('Mass Effect', '1'),
                 'Тёмная Башня. Книга 0.5': ('Тёмная Башня', '0.5'), 'Тёмная Башня. Книга 1.0': ('Тёмная Башня', '1'),
                 'Тёмная Башня. Книга 4,5': ('Тёмная Башня', '4.5'), 'Цикл: Левиафан. Книга 2': ('Левиафан', '2'), 'Подвал: Книга 1': ('Подвал', '1'),
                 'Чужие. Книга 04': ('Чужие', '4'), 'Sigma Force. Book 3': ('Sigma Force', '3')}
        for value, expected in named.items():
            with self.subTest(value=value):
                found = local_identity.tag_series_value(value)
                self.assertEqual((found['series'], found['number']), expected)
        refused = {'SCP Foundation. Протоколы SCP. Книга 5': 'two names',
                   'Боевые роботы. Трилогия о Нефритовом Фениксе. Книга 1': 'two names',
                   'Издательская серия «Хонкаку-детектив». Книга 2': "a publisher's series",
                   'Вселенная Метро 2033 - Книга 1': 'a universe, and a number of its own',
                   'Созвездие Льва. Книга 3. Том 2': 'a volume of a book',
                   'Темная башняю Книга 4.5': 'no separator before the book word',
                   'Клейн. Книга 0': 'book 0 by a tag alone', 'Книга 2': 'no series name', 'Том. Книга 2': 'a part word, not a series',
                   'Клейн': 'no number', 'Тёмный лес': 'a plain sort title', 'Sigmа Force. Книга 3': 'Latin and Cyrillic letters in one word'}
        for value, why in refused.items():
            with self.subTest(value=value):
                self.assertIsNone(local_identity.tag_series_value(value), why)
        self.assertIsNone(local_identity.tag_series_value('Стивен Кинг. Книга 2', author='Кинг Стивен'), "the author's own name is no series")

    def test_dark_forest_takes_its_series_and_number_from_its_sort_album_tag(self):
        row = next(iter(self.shelf(dark_forest_rows()).values()))
        self.assertEqual(len(row['members']), 2, 'positive control: the two parts are one book')
        identity, _ = self.research.identity(row, ROOT)
        self.assertEqual(identity['series'], {'name': 'Память о прошлом Земли', 'number': '2'})
        self.assertEqual(identity['fields']['series']['sources'], [{'kind': 'embedded', 'field': 'sort_album', 'value': 'Память о прошлом Земли. Книга 2'}])
        self.assertFalse(identity['series_unconfirmed'], 'R4: no question')
        self.assertNotIn('series', identity['gaps'], 'nothing is looked up online for it')
        self.assertEqual(identity['fields']['title']['value'], 'Тёмный лес', 'the title is step 3, not this build')
        # What the row's "Goes to" line and Approve file: the series folder and name (the English names are steps 2 and 3).
        self.assertIn('\\Память о прошлом Земли\\Память о прошлом Земли - 2 - Тёмный лес - ', self.approved_to(row))

    def test_without_the_tag_it_has_no_series(self):
        # Positive control for the test above: the same book as the app read it before (the tag was a number check only).
        rows = [file_row(DARK_FOREST + 'Тёмный лес %d.m4b' % n, album='Тёмный лес', artist='Лю Цысинь', title='Тёмный лес', track='%d/2' % n) for n in (1, 2)]
        row = next(iter(self.shelf(rows).values()))
        identity, _ = self.research.identity(row, ROOT)
        self.assertEqual(identity['series'], {})
        self.assertIn('series', identity['gaps'])

    def book(self, folder, count=2, **tags):
        rows = [file_row(folder + '\\%02d.mp3' % n, track='%d/%d' % (n, count), title='%02d' % n, **tags) for n in range(1, count + 1)]
        return next(iter(self.shelf(rows).values()))

    def test_a_tagged_series_files_the_book_without_a_question(self):
        row = self.book('Лукьяненко\\Клейн 2', album='Волшебник Линна', artist='Сергей Лукьяненко', sort_album='Клейн. Книга 2')
        result = self.lookup(row)
        self.assertEqual((result['reasons'], result.get('ask')), ([], None))
        self.assertEqual((result['review']['series'], result['review']['number'], result['review']['title']), ('Клейн', '2', 'Волшебник Линна'))
        self.assertEqual(result['work']['verified_series']['name'], 'Клейн')
        self.assertIn('\\Клейн\\Клейн - 2 - Волшебник Линна - ', self.goes_to(row, result))

    def test_the_tag_confirms_a_series_the_title_names_too(self):
        # «Вымирание 1. Код» was asked (ruling 52: nothing confirmed the series its name carries); its sort-album tag does.
        row = self.book('Лукьяненко\\Вымирание 1', album='Вымирание 1. Код', artist='Сергей Лукьяненко', sort_album='Вымирание. Книга 1')
        result = self.lookup(row)
        self.assertEqual((result['reasons'], result.get('ask')), ([], None))
        self.assertEqual((result['review']['series'], result['review']['number'], result['review']['title']), ('Вымирание', '1', 'Код'))
        untagged = self.book('Лукьяненко\\Вымирание 1', album='Вымирание 1. Код', artist='Сергей Лукьяненко')
        self.split_asked(untagged, 'Вымирание', '1', 'Код')  # positive control: without the tag it is still asked

    def test_grouping_and_a_half_number(self):
        row = self.book('Лукьяненко\\Бегемот', album='Бегемот', artist='Сергей Лукьяненко', grouping='Цикл: Левиафан. Книга 2')
        self.assertEqual(self.research.identity(row, ROOT)[0]['series'], {'name': 'Левиафан', 'number': '2'})
        row = self.book('Лукьяненко\\Сёстры', album='Смиренные сёстры Элурии', artist='Сергей Лукьяненко', sort_album='Тёмная Башня. Книга 0.5')
        self.assertEqual(self.research.identity(row, ROOT)[0]['series'], {'name': 'Тёмная Башня', 'number': '0.5'})

    def test_files_or_tags_that_disagree_name_no_series(self):
        rows = [file_row('Лукьяненко\\Стрелок\\%02d.mp3' % n, track='%d/2' % n, title='%02d' % n, album='Стрелок', artist='Сергей Лукьяненко',
                         sort_album='Тёмная Башня. Книга %d' % n) for n in (1, 2)]
        row = next(iter(self.shelf(rows).values()))
        self.assertEqual(self.research.identity(row, ROOT)[0]['series'], {}, 'the files disagree')
        row = self.book('Лукьяненко\\Стрелок', album='Стрелок', artist='Сергей Лукьяненко', sort_album='Тёмная Башня. Книга 1', grouping='Цикл: Стрелок. Книга 2')
        self.assertEqual(self.research.identity(row, ROOT)[0]['series'], {}, 'the two tags of one file disagree')
        rows = [file_row('Лукьяненко\\Стрелок\\01.mp3', track='1/2', title='01', album='Стрелок', artist='Сергей Лукьяненко', sort_album='Тёмная Башня. Книга 1'),
                file_row('Лукьяненко\\Стрелок\\02.mp3', track='2/2', title='02', album='Стрелок', artist='Сергей Лукьяненко')]
        row = next(iter(self.shelf(rows).values()))
        self.assertEqual(self.research.identity(row, ROOT)[0]['series'], {}, 'one file does not name it')

    def test_sergeis_own_series_folder_still_decides(self):
        # Author\Series\N. Title (0.22.1 item 9) is his own naming: the uploader's tag never replaces it.
        rows = [file_row('Сергей Лукьяненко\\The Dark Tower\\1. Стрелок\\%02d.mp3' % n, track='%d/2' % n, title='%02d' % n, album='Стрелок', artist='Сергей Лукьяненко',
                         sort_album='Тёмная Башня. Книга 1.0') for n in (1, 2)]
        row = next(iter(self.shelf(rows).values()))
        identity, _ = self.research.identity(row, ROOT)
        self.assertEqual(identity['series'], {'name': 'The Dark Tower', 'number': '1', 'folder': True})

    def test_a_series_folder_sorted_already_holds_gives_its_spelling(self):
        row = self.book('Лукьяненко\\Стрелок', album='Стрелок', artist='Сергей Лукьяненко', sort_album='Темная башня. Книга 1')
        self.in_sorted('Тёмная Башня', 'Лукьяненко Сергей')
        local_identity._INDEX.clear()
        self.assertEqual(self.research.identity(row, ROOT)[0]['series'], {'name': 'Тёмная Башня', 'number': '1'}, 'one folder, the one Sorted has')

    def test_an_author_question_still_lists_its_candidates(self):
        # Regression (found by test_approve_as_is before this shipped): the tag reading reused the name of the list of tag
        # credits, so a book whose tags credit two people raised instead of asking "Author unclear" with both.
        for tags in ({}, {'sort_album': 'Клейн. Книга 2'}):
            with self.subTest(tags=tags):
                row = self.book('Новое\\Империя', album='Империя атома', artist='Иван Петров', album_artist='Сергей Сидоров', **tags)
                identity, _ = self.research.identity(row, ROOT)
                self.assertEqual((identity['ask']['kind'], identity['ask']['why']), ('author_unclear', 'two_people'))
                self.assertEqual(sorted(c['name'] for c in identity['ask']['candidates']), ['Иван Петров', 'Сергей Сидоров'])


if __name__ == '__main__':
    unittest.main()
