"""Four live rows from Sergei's screen on 0.22.1 (2026-10-26), with the names and tags the catalog holds.

- «1408» (Z:\\Audiobooks\\Stephen King\\1408.m4b): the artist tag "sk 1408" was the author, so it went to
  sk 1408\\1408 - sk 1408.m4b, and the file was held as one chapter. Initials and the title's number are no author; the
  folder names him (King Stephen); a single file titled with a number is the whole book (backlog item 10 b).
- «11.22.63» (three parts "11.22.63 - 1/2/3.m4b", tagged "11/22/63"): held as one numbered part. The title, three numbers
  joined by slashes, has no letters and was read as a bare part number before the parts rule (ruling 19) could run.
- «Голиаф» (Steampunk\\Голиаф.m4b, Скотт Вестерфельд): "Files unclear: the tags say 3 discs, but 1 is here". Disc 3/3 is
  its number in the Leviathan trilogy (sort album "Левиафан. Книга 3"), the VanderMeer bug in another shape; and the
  English author went to a Russian folder. A translation (ruling 29) that waits for its English title, filed under the
  English spelling of the name the same answer gives.
- «Ветер сквозь замочную скважину» (Dark Tower 4.5, two parts): "As one book ... Dark Tower - 4.5 - The Wind Through the
  Keyhole". Right; kept.
Catalog rows only; no file, no network."""
import unittest

from test_folder_structure import Base, ROOT, SORTED, file_row

KING = 'Stephen King\\'


class LiveCaseTests(Base):
    def test_1408_is_a_whole_book_by_the_folders_author_and_sk_1408_is_no_author(self):
        # The live folder: a sibling whose title tag is the junk "1" (its file name names the book) is no numbered part.
        rows = [file_row(KING + '1408.m4b', artist='sk 1408', comment='fre:ac - free audio converter <https://www.freac.org/>'),
                file_row(KING + 'Мизери.m4b', title='Мизери', album='Мизери', artist='Стивен Кинг'),
                file_row(KING + 'Stephen King - A Face in the Crowd.m4b', title='1', album='A Face in the Crowd', artist='Stephen King')]
        row = self.catalog(rows)[ROOT + '\\' + KING + '1408.m4b']
        record, _ = self.research.identity(row, ROOT)
        self.assertEqual((record['fields']['title']['value'], record['fields']['author']['value']), ('1408', 'Stephen King'))
        self.assertIn('sk 1408', [i['value'] for i in record['ignored']], 'the label is set aside, with its reason')
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [], 'no chapter hold: a single file titled with a number is the whole book')
        self.assertEqual(self.goes_to(row, result), SORTED + '\\King Stephen\\1408 - King Stephen.m4b', 'was sk 1408\\1408 - sk 1408.m4b')

    def test_a_person_named_with_letters_stays_an_author_and_01_stays_a_chapter(self):
        import local_identity
        self.assertFalse(local_identity.numbered_credit('Стивен Кинг', ['1408']))
        self.assertTrue(local_identity.numbered_credit('sk 1408', []))
        self.assertTrue(local_identity.numbered_credit('Stephen King 1408', ['1408']), 'the title\'s own number in a credit')
        self.assertFalse(local_identity.numbered_credit('Stephen King 2', ['1408']), 'one digit, not the title\'s: left to the other rules')
        rows = [file_row('Unsorted\\Книга\\05.mp3', album='Книга', artist='Иван Петров'), file_row('Unsorted\\Книга\\06.mp3', album='Книга', artist='Иван Петров')]
        self.assertFalse(local_identity.lone_number({'members': [rows[0]]}, '05'), 'control: "05" is a chapter number')

    def test_11_22_63_is_one_book_in_three_parts_never_a_numbered_part(self):
        rows = [file_row(KING + '11.22.63\\11.22.63 - %d.m4b' % n, title='11/22/63 %d' % n, album='11/22/63', artist='Стивен Кинг', album_artist='Стивен Кинг',
                         composer='Валерий Смекалов', track='%d/3' % n, genre='Фантастика') for n in (1, 2, 3)]
        row = next(iter(self.catalog(rows).values()))
        self.assertEqual(len(row['members']), 3, 'one candidate of three parts')
        record, _ = self.research.identity(row, ROOT)
        self.assertEqual(record['fields']['title']['value'], '11/22/63')
        self.assertFalse(record.get('held'), 'the date title is a name, not a part number')
        result = self.lookup(row)
        self.assertNotIn('One part of a bigger book', result['reasons'])
        self.assertEqual(result['review']['canonical_author'], 'King Stephen')
        # Ruling 37 (Sergei 2026-10-26): filed as «11.22.63», the folder's spelling; the title tag keeps its slashes.
        self.assertEqual(result['review']['title'], '11/22/63')
        self.assertEqual(self.goes_to(row, result), SORTED + '\\King Stephen\\11.22.63 - King Stephen.m4b', 'was 11_22_63')

    def test_a_title_of_numbers_joined_by_slashes_is_written_with_dots_and_any_other_slash_stays_an_underscore(self):
        from metadata import safe_name
        self.assertEqual(safe_name('11/22/63'), '11.22.63')
        self.assertEqual(safe_name('1/2/2020'), '1.2.2020')
        self.assertEqual(safe_name('AC/DC'), 'AC_DC', 'control: letters')
        self.assertEqual(safe_name('Часть 1/2'), 'Часть 1_2', 'control: not only numbers')
        self.assertEqual(safe_name('King Stephen'), 'King Stephen')

    DOZORY = 'Сергей Лукьяненко\\Вселенная Дозоров - Межавторский цикл\\'

    def test_a_dozory_book_files_in_its_universe_and_in_one_numbered_series(self):
        # Rulings 30 and 37 (Sergei 2026-10-26): the folder «Вселенная Дозоров - Межавторский цикл» is the universe «Вселенная
        # Дозоров» (Universe > Series > Book) and in it the one numbered series «Межавторский цикл». Live names and tags.
        rows = [file_row(self.DOZORY + '16 - Сергей Недоруб - Севастопольский дозор (08_00-20_00 16 мая 2016).m4b', title='Севастопольский дозор',
                         album='Севастопольский дозор', artist='Сергей Недоруб', genre='Фантастика', date='2016', album_artist='Воронецкий Станислав'),
                file_row(self.DOZORY + 'Виталий Каплан - Корона (июнь 2004).m4b', title='Корона', album='Корона', artist='Виталий Каплан'),
                file_row(self.DOZORY + '27 - Валерий Пылаев - Запах Сумрака (август-сентябрь 2010).m4b', title='Дозоры. Запах Сумрака',
                         album='Дозоры. Запах Сумрака', artist='Валерий Пылаев', genre='Фантастика', date='2018', album_artist='Алексей Данков')]
        books = self.catalog(rows)
        universe = SORTED + '\\Вселенная Дозоров\\'
        row = books[rows[0]['path']]
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertEqual((result['review']['universe'], result['review']['series'], result['review']['number']), ('Вселенная Дозоров', 'Межавторский цикл', '16'))
        self.assertEqual(self.goes_to(row, result), universe + 'Межавторский цикл\\Межавторский цикл - 16 - Севастопольский дозор - Недоруб Сергей.m4b',
                         'was Недоруб Сергей\\Вселенная Дозоров - Межавторский - 16 - …')
        self.assertEqual(self.goes_to(row, self.research.approved(row, ROOT)), self.goes_to(row, result), 'Approve files it where the row says')
        self.assertEqual(self.research.names_read(row, ROOT)[0]['universe'], 'Вселенная Дозоров', 'Edit names reads the universe')
        # A book of the universe with no number in its name is in the universe, in no series.
        row = books[rows[1]['path']]
        self.assertEqual(self.goes_to(row, self.research.approved(row, ROOT)), universe + 'Корона - Каплан Виталий.m4b')
        row = books[rows[2]['path']]
        # Its clean title tag stays the title (Senua's 0.22.1 review, W1).
        self.assertEqual(self.goes_to(row, self.research.approved(row, ROOT)), universe + 'Межавторский цикл\\Межавторский цикл - 27 - Дозоры. Запах Сумрака - Пылаев Валерий.m4b')

    def test_a_series_folder_that_is_no_universe_files_under_its_author_as_before(self):
        rows = [file_row('Clive Barker\\Books of Blood\\3. Сын целлулоида.m4b', title='Сын целлулоида', album='Сын целлулоида', artist='Clive Barker')]
        row = next(iter(self.catalog(rows).values()))
        result = self.research.approved(row, ROOT)
        self.assertFalse(result['review'].get('universe'))
        self.assertTrue(self.goes_to(row, result).startswith(SORTED + '\\Barker Clive\\Books of Blood\\Books of Blood - 3 - '), self.goes_to(row, result))

    def test_goliath_disc_3_of_3_is_its_place_in_the_trilogy_and_it_converts_without_waiting(self):
        from unittest.mock import patch
        rows = [file_row('Steampunk\\Голиаф.m4b', title='Голиаф', album='Голиаф', artist='Скотт Вестерфельд', composer='Cubear', track='1/1', disc='3/3',
                         genre='Фантастика, Стимпанк', sort_album='Левиафан. Книга 3'),
                file_row('Steampunk\\Левиафан.m4b', title='Левиафан', album='Левиафан', artist='Вестерфельд Скотт', album_artist='Вестерфельд Скотт', track='1',
                         grouping='Цикл: Левиафан. Книга 1')]
        row = self.catalog(rows)[ROOT + '\\Steampunk\\Голиаф.m4b']
        result = self.lookup(row)
        self.assertNotIn('Source membership uncertain', result['reasons'], 'disc 3/3 is book 3 of the trilogy, no missing disc')
        # Ruling 38 (Sergei 2026-10-27): an English author's translation never waits for its English title. Ruling 39: with
        # no English spelling of the author anywhere (offline: no Latin folder, no catalog answer, no lookup), Sergei is
        # asked for it, never a transliteration.
        self.assertEqual(result['reasons'], ['Author unclear'])
        self.assertEqual((result['ask']['why'], result['ask']['credit']), ('english_spelling', 'Вестерфельд Скотт'))
        catalog = {'language': 'en', 'original_title': 'Goliath', 'title_native': 'Голиаф', 'author_native': 'Скотт Вестерфельд', 'author_latin': 'Scott Westerfeld',
                   'source_url': 'https://fantlab.ru/work2'}
        with patch.object(self.research, '_gap_fill', return_value={'catalog': catalog, 'closed': [], 'unfilled': []}):
            result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertTrue(self.goes_to(row, result).startswith(SORTED + '\\Westerfeld Scott\\'), 'a catalog answer: the English title and spelling')
        self.assertIn('Goliath - Westerfeld Scott.m4b', self.goes_to(row, result))

    def test_a_real_missing_disc_is_still_held(self):
        rows = [file_row('Unsorted\\Шторм.m4b', title='Шторм', album='Шторм', artist='Иван Петров', track='1/1', disc='2/3')]
        row = next(iter(self.catalog(rows).values()))
        self.assertIn('Source membership uncertain', self.lookup(row)['reasons'], 'control: no tag names it a series position')

    def test_the_wind_through_the_keyhole_stays_as_one_book_in_the_dark_tower(self):
        rows = [file_row(KING + 'Dark Tower\\4.5 The Wind Through the Keyhole\\Ветер сквозь замочную скважину %d.m4b' % n, title='Ветер сквозь замочную скважину %d' % n,
                         album='Ветер сквозь замочную скважину', artist='Стивен Кинг', album_artist='Стивен Кинг', composer='Vargtroms Studio', track='%d/2' % n,
                         sort_album='Тёмная Башня. Книга 4.5', sort_name='Тёмная Башня. Книга 4.5', sort_artist='Тёмная Башня', grouping='Темная башняю Книга 4.5') for n in (1, 2)]
        row = next(iter(self.catalog(rows).values()))
        # The parts' chapters are this test's own (0.22.3): the case used to probe the live Z: files, so it passed only while
        # Sergei's two parts were still there, and read his library. Chapters that don't settle it: "As one book" is asked.
        from unittest.mock import patch
        import part_sets
        chapters = lambda paths, *a, **k: {path: ['Пролог', 'Ветер сквозь замочную скважину'] if path.endswith('1.m4b') else ['Ключ', 'Буря'] for path in paths}
        with patch.object(part_sets, 'read_chapters', side_effect=chapters):
            result = self.lookup(row)
            self.assertEqual(result['identity_hold']['piece']['piece'], 'set', 'asked "As one book"')
            self.assertEqual(self.goes_to(row, self.research.approved(row, ROOT)),
                             SORTED + '\\King Stephen\\Dark Tower\\Dark Tower - 4.5 - The Wind Through the Keyhole - King Stephen.m4b')


class CachedCatalogSpellingTests(Base):
    def test_a_cached_catalog_latin_name_files_english_and_is_learned_for_the_other_book(self):
        # Futaba's 0.22.2 QA, m-2 (ruling 39): the research cache holds FantLab's record for «Волшебники» (written in English,
        # "The Magicians", author "Lev Grossman"); the files credit only «Лев Гроссман». It went to «Гроссман Лев\The
        # Magicians» (or "Lev Grossman\..." as written), no rule was learned and «Волшебная страна» stayed Cyrillic.
        import contextlib, sqlite3
        from unittest.mock import patch
        catalog = {'provider': 'fantlab', 'work_id': 'fantlab:1', 'language': 'en', 'original_title': 'The Magicians', 'title_native': 'Волшебники',
                   'author_native': 'Лев Гроссман', 'author_latin': 'Lev Grossman', 'source_url': 'https://fantlab.ru/work1'}
        books = self.catalog([file_row('Fantasy\\Волшебники.m4b', title='Волшебники', album='Волшебники', artist='Лев Гроссман'),
                              file_row('Fantasy\\Волшебная страна.m4b', title='Волшебная страна', album='Волшебная страна', artist='Лев Гроссман')])
        magicians, land = books[ROOT + '\\Fantasy\\Волшебники.m4b'], books[ROOT + '\\Fantasy\\Волшебная страна.m4b']
        real = self.research._gap_fill
        gap = lambda local, title, *a, **k: {'catalog': dict(catalog), 'closed': [], 'unfilled': []} if title == 'Волшебники' else real(local, title, *a, **k)
        with patch.object(self.research, '_gap_fill', side_effect=gap):
            result = self.lookup(magicians)
            self.assertEqual(result['reasons'], [])
            self.assertEqual(self.goes_to(magicians, result), SORTED + '\\Grossman Lev\\The Magicians - Grossman Lev.m4b', 'English, surname first')
            self.assertEqual(result['author_learned'], {'credit': 'Лев Гроссман', 'name': 'Grossman Lev', 'source_url': 'https://fantlab.ru/work1'})
            with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
                self.assertEqual([tuple(r) for r in db.execute("SELECT kind, target, actor FROM author_rules WHERE rule_id NOT LIKE 'seed-%'")], [('same_as', 'Grossman Lev', 'assistant')])
            other = self.lookup(land)
        self.assertEqual(self.goes_to(land, other), SORTED + '\\Grossman Lev\\Волшебная страна - Grossman Lev.m4b', 'the other book follows the rule')
        # Control: a Russian original's record keeps the Cyrillic credit (the folder language rule).
        russian = dict(catalog, language='ru', original_title='Волшебники', author_latin='Lev Grossman')
        books = self.catalog([file_row('Fantasy\\Волшебники.m4b', title='Волшебники', album='Волшебники', artist='Лев Гроссман')])
        with patch.object(self.research, '_gap_fill', return_value={'catalog': russian, 'closed': [], 'unfilled': []}):
            result = self.lookup(next(iter(books.values())))
        self.assertNotIn('author_learned', result)
        self.assertTrue(self.goes_to(next(iter(books.values())), result).startswith(SORTED + '\\Гроссман Лев\\'))


class BromTests(Base):
    """0.22.3 (Sergei 2026-10-27, «Крампус. Повелитель Йоля»): the author publishes as Brom and his folder stays Brom. The
    live catalog: a lookup learned «Бром Джеральд» same as Brom; an older job is credited «Бром Джеральд»; the new book
    credits «Бром». It asked "Same author? «Бром» or «Бром Джеральд»", and either answer could give a second folder."""
    def library(self, *rules):
        import author_rules, contextlib, json, sqlite3
        books = self.catalog([file_row('Unsorted\\Бром - Крампус\\Крампус. Повелитель Йоля.m4b', title='Крампус. Повелитель Йоля', album='Крампус. Повелитель Йоля', artist='Бром')])
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            db.execute('CREATE TABLE audio_jobs(manifest TEXT, updated TEXT)')
            for author in ('Бром Джеральд', 'Brom', 'Brom'):
                db.execute('INSERT INTO audio_jobs VALUES(?,?)', (json.dumps({'metadata': {'author': author}}), '2026-10-27'))
            author_rules.append(db, 'same_as', 'Бром Джеральд', target='Brom', actor='assistant', source='https://fantlab.ru/work843689')
            for credit, target in rules:
                author_rules.append(db, 'same_as', credit, target=target, actor='user', source='Sergei (Same author?)')
            db.commit()
        return next(iter(books.values()))

    def test_brom_files_under_brom_without_a_question(self):
        row = self.library()
        result = self.lookup(row)
        self.assertEqual((result['reasons'], result.get('ask')), ([], None), 'Бром is Brom, the folder the library has')
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Brom\\Крампус. Повелитель Йоля - Brom.m4b')

    def test_a_same_author_answer_for_the_old_name_still_files_under_brom(self):
        # His answer on the old question ("Same author: use «Бром Джеральд»") is a rule to a name that is itself Brom.
        row = self.library(('Бром', 'Бром Джеральд'))
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Brom\\Крампус. Повелитель Йоля - Brom.m4b', 'never a «Бром Джеральд» folder')
        self.assertEqual(self.goes_to(row, self.research.approved(row, ROOT, chosen='Бром Джеральд')), SORTED + '\\Brom\\Крампус. Повелитель Йоля - Brom.m4b')

    def test_rules_follow_a_chain_and_stop_on_a_loop(self):
        import author_rules
        row = lambda n, credit, target: {'rule_id': 'r%d' % n, 'kind': 'same_as', 'credit_key': author_rules.key(credit), 'credit_as_seen': credit, 'target': target,
                                         'scope': '', 'options': '{}', 'actor': 'user', 'source': '', 'question': '', 'saved_utc': '2026-10-27T00:00:0%d' % n}
        rules = author_rules.Rules([row(1, 'Бром', 'Бром Джеральд'), row(2, 'Бром Джеральд', 'Brom')], ['Бром Джеральд'])
        self.assertEqual(rules.same_as('Бром'), 'Brom')
        self.assertEqual(rules.known_authors.get('brom'), ('Brom', 1), 'the old job counts as Brom')
        loop = author_rules.Rules([row(1, 'A Bee', 'C Dee'), row(2, 'C Dee', 'A Bee')])
        self.assertIn(loop.same_as('A Bee'), ('A Bee', 'C Dee'))


if __name__ == '__main__':
    unittest.main()
