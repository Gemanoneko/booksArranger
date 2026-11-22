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

    def test_the_row_can_say_where_the_series_and_the_title_came_from(self):
        # Judy's 0.31.0 spec, 4.3: "Series: Sprawl Trilogy · No. 2 · from the file's tags"; "Title from this file's own title tag."
        from merge_service import MergeService
        result = self.lookup(self.volumes()[0])
        self.assertEqual(MergeService.series_origin(result), {'origin': 'tags', 'title_from_title_tag': True})
        row = next(iter(self.shelf(dark_forest_rows()).values()))
        self.assertEqual(MergeService.series_origin(self.research.approved(row, ROOT)), {'origin': 'tags', 'title_from_title_tag': False},
                         'its title is the album tag; its series the sort-album tag')
        folders = {'local_agreement': {'series': {'state': 'green', 'value': 'Sigma Force', 'sources': [{'kind': 'folder structure', 'value': 'Sigma Force'}]}}}
        entered = {'local_agreement': {'series': {'state': 'entered', 'value': 'Sprawl Trilogy', 'basis': 'entered', 'sources': [{'kind': 'entered by you', 'value': 'Sprawl Trilogy'}]}}}
        online = {'local_agreement': {'series': {'state': 'grey', 'value': '', 'sources': []}},
                  'metadata_facts': {'series_source': {'provider': 'fantlab', 'url': 'https://fantlab.ru/work3650'}}}
        self.assertEqual(MergeService.series_origin(folders)['origin'], 'folders')
        self.assertEqual(MergeService.series_origin(entered)['origin'], 'entered')
        self.assertEqual(MergeService.series_origin(online), {'origin': 'source', 'title_from_title_tag': False, 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work3650'})
        self.assertEqual(MergeService.series_origin({})['origin'], 'unknown')
        # Judy 4.3 as amended with his answers: by where the series was really read; never a place it was not read from.
        named = lambda kind, **extra: {'local_agreement': {'series': {'state': 'green', 'value': 'Sprawl Trilogy', 'sources': [dict({'kind': kind, 'value': 'x'}, **extra)]}}}
        self.assertEqual(MergeService.series_origin(named('the title (tag)', field='title'))['origin'], 'title_tag')
        self.assertEqual(MergeService.series_origin(named('the title (tag)'))['origin'], 'tags', 'an album tag, or an older record: one of the file\'s tags')
        self.assertEqual(MergeService.series_origin(named('the title (file_name)'))['origin'], 'file_name')
        self.assertEqual(MergeService.series_origin(named('the title (folder_name)'))['origin'], 'folders')
        self.assertEqual(MergeService.series_origin(named('the title (number_rule)'))['origin'], 'unknown')
        # Amended after the final build (gap 5): the brackets rule's own origin, never 'tags' (BracketsOriginTests).
        self.assertEqual(MergeService.series_origin(named('brackets in the name'))['origin'], 'brackets')

    def test_the_list_row_carries_the_origin_its_place_line_prints(self):
        # Judy's 0.31.0 spec 4.3 as amended: a book filed without a question says where its series came from on the Place
        # line of its row, so the origin comes with the row's stored place (no research per row), as a key the page words.
        from types import SimpleNamespace
        from unittest import mock
        import entered_names
        from merge_service import MergeService
        from review_backend import CandidateReviewService
        volume = self.volumes()[0]
        result = self.lookup(volume)
        service = CandidateReviewService.__new__(CandidateReviewService)
        service.inventory = SimpleNamespace(database=self.research.client.database); service.jobs = MergeService

        def listed(review, facts, **extra):
            row = dict(volume, review=review, metadata_facts=facts, **extra)
            service._names_lines([row])
            return row
        facts = dict(result.get('metadata_facts') or {}, local_agreement=result['local_agreement'])
        row = listed(result['review'], facts)
        self.assertEqual((row['place']['series'], row['place']['number'], row['place']['origin']), ('Sprawl Trilogy', '2', 'tags'))
        self.assertNotIn('provider', row['place'])
        self.assertIs(row['title_from_title_tag'], True, "the details panel's line of a volume named from its own title tag")
        # The research record, when the row has no approved facts of its own.
        self.assertEqual(listed(result['review'], None, automatic={'metadata_facts': facts})['place']['origin'], 'tags')
        online = {'local_agreement': {'series': {'state': 'grey', 'value': '', 'sources': []}}, 'series_source': {'provider': 'fantlab', 'url': 'https://fantlab.ru/work3650'}}
        found = listed(result['review'], online)
        self.assertEqual((found['place']['origin'], found['place']['provider'], found['title_from_title_tag']), ('source', 'fantlab', False))
        folders = {'local_agreement': {'series': {'state': 'green', 'value': 'Sprawl Trilogy', 'sources': [{'kind': 'folder structure', 'value': 'Sprawl Trilogy'}]}}}
        self.assertEqual(listed(result['review'], folders)['place']['origin'], 'folders')
        self.assertEqual(listed(result['review'], {})['place']['origin'], 'unknown', 'an older record: the line prints no suffix')
        self.assertEqual(listed(result['review'], {'local_agreement': 'not a record'})['place']['origin'], 'unknown', 'an odd record never drops the line')
        # A series he saved himself is his, whatever the record said before.
        with mock.patch.object(entered_names, 'book_values', return_value={'series': 'Киберпространство', 'number': '2'}):
            mine = listed(result['review'], facts)
        self.assertEqual((mine['place']['series'], mine['place']['origin']), ('Киберпространство', 'entered'))
        # No series, no origin (the page prints the suffix only after "Series: … · No. …").
        self.assertNotIn('origin', listed(dict(result['review'], series='', number=''), facts)['place'])

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

    def test_a_title_tag_alone_shaped_series_nn_title_files_the_book_without_asking_r15(self):
        # R15 (Sergei 2026-11-22; it narrows ruling 52): the first Sprawl file has no album tag and is no volume of a set.
        # Its only clue is its own title tag, "Sprawl Trilogy 01 - Neuromancer": R4 covers it, so it is filed, not asked.
        from merge_service import MergeService
        row = self.shelf(sprawl_rows())[ROOT + '\\' + SPRAWL['neuromancer']]
        result = self.lookup(row)
        self.assertEqual((result['reasons'], result.get('ask')), ([], None), 'no question')
        review = result['review']
        self.assertEqual((review['title'], review['series'], review['number']), ('Neuromancer', 'Sprawl Trilogy', '1'), 'the title part only, never the whole tag')
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Gibson William\\Sprawl Trilogy\\Sprawl Trilogy - 1 - Neuromancer - Gibson William.m4b')
        # The row says where the series was really read (Judy 4.3 as amended): the title tag's own text, not "its tags".
        self.assertEqual(MergeService.series_origin(result), {'origin': 'title_tag', 'title_from_title_tag': True})
        # The two volumes beside it keep "from the file's tags": their album tag names the set too (R4, step 1a).
        self.assertEqual({MergeService.series_origin(self.lookup(volume))['origin'] for volume in self.volumes()}, {'tags'})

    def test_every_other_name_nothing_confirms_still_asks_r15_keeps_ruling_52(self):
        # The ruled shape only: one file, the title read from its own title tag, the number followed by a dash.
        import local_identity
        asked = {
            'a dot after the number': file_row(GIBSON + 'a.m4b', title='Sprawl Trilogy 1. Neuromancer', artist='William Gibson'),
            'a colon after the number': file_row(GIBSON + 'b.m4b', title='Sprawl Trilogy 1: Neuromancer', artist='William Gibson'),
            'a "#" before the number': file_row(GIBSON + 'c.m4b', title='Sprawl Trilogy #1 - Neuromancer', artist='William Gibson'),
            'the album tag, not the title tag': file_row(GIBSON + 'd.m4b', album='Sprawl Trilogy 01 - Neuromancer', title='01', artist='William Gibson'),
        }
        for why, row in asked.items():
            book = next(iter(self.shelf([row]).values()))
            ask = self.lookup(book).get('ask') or {}
            self.assertEqual((ask.get('why'), ask.get('split')), ('title_series', {'series': 'Sprawl Trilogy', 'number': '1', 'title': 'Neuromancer'}), why)
        # Positive control on the same fixture: the ruled shape files.
        filed = self.lookup(next(iter(self.shelf([file_row(GIBSON + 'e.m4b', title='Sprawl Trilogy 01 - Neuromancer', artist='William Gibson')]).values())))
        self.assertEqual((filed['reasons'], filed['review']['series']), ([], 'Sprawl Trilogy'))
        # The rule itself, on the shapes a fixture row cannot isolate.
        tag = lambda value: {'state': 'one', 'value': value, 'basis': 'tag', 'sources': [{'kind': 'embedded', 'field': 'title', 'value': value}]}
        one = [{'path': 'x.m4b'}]
        parts = lambda value, author='': local_identity.series_title_parts(value, author)
        whole = 'Sprawl Trilogy 01 - Neuromancer'
        self.assertTrue(local_identity.title_tag_series(tag(whole), one, parts(whole), 'William Gibson'))
        self.assertTrue(local_identity.title_tag_series(tag('Колесо Времени 03 — Возрождённый Дракон'), one, parts('Колесо Времени 03 — Возрождённый Дракон')), 'a long dash is a dash')
        self.assertFalse(local_identity.title_tag_series(tag(whole), one + one, parts(whole)), 'a book of several files: their title tags name chapters')
        self.assertFalse(local_identity.title_tag_series(dict(tag(whole), basis='file_name'), one, parts(whole)), 'a title from the file name')
        self.assertFalse(local_identity.title_tag_series(dict(tag(whole), sources=[{'kind': 'embedded', 'field': 'album', 'value': whole}]), one, parts(whole)), 'a title from the album tag')
        self.assertFalse(local_identity.title_tag_series(tag(whole), one, None), 'no split: nothing to confirm')
        heller = 'Catch 22 - Joseph Heller'
        self.assertFalse(local_identity.title_tag_series(tag(heller), one, {'series': 'Catch', 'number': '22', 'title': 'Joseph Heller'}, 'Joseph Heller'),
                         "the part after the dash is the author's name: a title and its author, not a series and a title")

    def test_a_volume_with_no_title_of_its_own_keeps_its_set_name_and_number(self):
        # Торадора! (ruling 13): the title tag only repeats the set and a volume number; named "Торадора! 1" as before.
        rows = [file_row('Light Novels\\Yuyuko Takemiya\\Toradora!\\Торадора! Том %d.m4b' % n, album='Торадора!', title='Торадора! Том %d' % n,
                         artist='Ююко Такэмия', track='%d/2' % n) for n in (1, 2)]
        books = self.shelf(rows, volumes=[r['path'] for r in rows])
        titles = [self.research.identity(books[r['path']], ROOT)[0]['fields']['title']['value'] for r in rows]
        self.assertEqual(titles, ['Торадора! 1', 'Торадора! 2'])

    def test_a_separated_part_book_keeps_the_name_the_part_rule_gave_it(self):
        # «Имаджика» (tests/test_split_books.PartBookAdmissionTests, on real files): two chaptered parts the app separated,
        # titled «Книга 1. Пятый Доминион» and «Книга 2. Примирение». The part-book rule names each from its own title tag
        # without the words that only number it; step 1a took the whole tag again, and the files were published as
        # «Имаджика - 1 - Книга 1. Пятый Доминион - Barker Clive.m4b».
        rows = [file_row('Clive Barker\\1290. Имаджика (Светлана Смелова)\\%d. %s.m4b' % (n, name), album='Имаджика', title='Книга %d. %s' % (n, name),
                         artist='Клайв Баркер', track='%d/2' % n) for n, name in ((1, 'Пятый Доминион'), (2, 'Примирение'))]
        books = self.shelf(rows, volumes=[r['path'] for r in rows])
        read = [self.research.identity(books[r['path']], ROOT)[0] for r in rows]
        self.assertEqual([(i['fields']['title']['value'], i['series']) for i in read],
                         [('Пятый Доминион', {'name': 'Имаджика', 'number': '1'}), ('Примирение', {'name': 'Имаджика', 'number': '2'})])


class BracketsOriginTests(Fixture):
    """Judy's 0.31.0 spec 4.3 as amended after the final build (gap 5, acceptance check 35): a series read from brackets
    in the book's name has an origin of its own. The brackets rule (rulings 51, 52, 71e: «Солнце и Замок (Книга Нового
    Солнца #3)») reads the album tag, the title tag or the folder's name and the record does not keep which, so the row
    must never say "from the file's tags" for it: the page words 'brackets' as " · from the brackets in its name"."""

    BOOK = 'Солнце и Замок (Книга Нового Солнца #3)'
    WOLFE = 'Джин Вулф\\'

    def read(self, rows):
        return self.lookup(next(iter(self.shelf(rows).values())))

    def parts(self, folder, album):
        return [file_row(self.WOLFE + folder + '\\%02d.mp3' % n, track='%d/2' % n, title='%02d' % n, album=album, artist='Джин Вулф') for n in (1, 2)]

    def test_each_place_the_rule_reads_gives_the_brackets_origin_and_never_tags(self):
        from merge_service import MergeService
        places = {"the folder's name": self.parts(self.BOOK, 'Солнце и Замок'),
                  'the album tag': self.parts('Солнце и Замок', self.BOOK),
                  'the title tag': [file_row(self.WOLFE + 'Солнце и Замок.m4b', title=self.BOOK, artist='Джин Вулф')]}
        for place, rows in places.items():
            with self.subTest(place=place):
                result = self.read(rows)
                series = result['local_agreement']['series']
                self.assertEqual((series['value'], result['local_agreement']['number']['value']), ('Книга Нового Солнца', '3'))
                self.assertEqual(series['sources'], [{'kind': 'brackets in the name', 'value': self.BOOK}], 'the record keeps the text, not which place carried it')
                self.assertEqual(MergeService.series_origin(result)['origin'], 'brackets')
        # Positive control: the same book with no brackets anywhere has no series and no origin to print.
        plain = self.read(self.parts('Солнце и Замок', 'Солнце и Замок'))
        self.assertEqual((plain['local_agreement']['series']['value'], MergeService.series_origin(plain)['origin']), ('', 'unknown'))

    def test_the_list_row_carries_it_to_the_place_line(self):
        # The row's stored place is what the Place line prints (review_backend._names_lines): 'brackets', with no provider.
        from types import SimpleNamespace
        from merge_service import MergeService
        from review_backend import CandidateReviewService
        book = next(iter(self.shelf(self.parts(self.BOOK, 'Солнце и Замок')).values()))
        result = self.lookup(book)
        service = CandidateReviewService.__new__(CandidateReviewService)
        service.inventory = SimpleNamespace(database=self.research.client.database); service.jobs = MergeService
        row = dict(book, review={'title': 'Солнце и Замок', 'series': 'Книга Нового Солнца', 'number': '3'}, metadata_facts={'local_agreement': result['local_agreement']})
        service._names_lines([row])
        self.assertEqual((row['place']['series'], row['place']['number'], row['place']['origin']), ('Книга Нового Солнца', '3', 'brackets'))
        self.assertNotIn('provider', row['place'])


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
