"""Rulings 19 and 19a, extended 2026-10-24 (Sergei): whole .m4b parts without an explicit part marker. Their chapters decide:
one book split into files is joined (chapters kept, re-encoded once), separate volumes stay separate books (ruling 15), a set
the evidence does not settle is a "Part of a bigger book" row with the proposed order and "Approve as one book", and parts
the track numbers say are missing are a Missing files row naming them. Synthetic fixtures built from the library's real
patterns (Геном, Задача трёх тел, Pern, Торадора!, Чёрная звезда, Хранители, Террор, Сундучок сказок, Незнакомцы, Миры
Джорджа Мартина, Хроники Нарнии). Real private audio through research, Approve, conversion and Sorted; no network."""
import threading, unittest
from pathlib import Path

import groups
import part_sets
import test_approve_as_is
from test_m4b_join import part
from test_split_books import row as catalog_row


def parts(*chapter_lists, titles=None, tracks=None, hours=8.0, credits=None, names=None):
    count = len(chapter_lists)
    return [{'name': (names or ['Запись %d' % n for n in range(1, count + 1)])[i], 'title': (titles or [''] * count)[i],
             'track': (tracks or ['%d/%d' % (n, count) for n in range(1, count + 1)])[i], 'hours': hours,
             'credits': (credits or [''] * count)[i], 'chapters': list(c)} for i, c in enumerate(chapter_lists)]


def glavy(first, last, prefix='Глава %d'):
    return [prefix % n for n in range(first, last + 1)]


class DecideTests(unittest.TestCase):
    def decision(self, *a, **k):
        found = part_sets.decide(parts(*a, **k))
        return found['decision'], found['basis']

    def test_chapter_numbers(self):
        for title, number in (('Глава 12. Холден', 12), ('Глава седьмая. Дети и динозавры', 7), ('016. Глава 9', 9), ('10 ГЛАВА', 10),
                              ('Часть вторая. Глава 65', 65), ('Эпизод - 23', 23), ('Глава 7. Эпизод 2', 7), ('16-03. Эпизод', 16),
                              ('Часть 11', 11), ('Глава IV. Ворота', 4), ('Пролог', None), ('Голубой карбункул', None)):
            with self.subTest(title=title):
                self.assertEqual(part_sets.chapter_number(title), number)

    def test_continuing_chapter_numbers_join_genom(self):
        self.assertEqual(self.decision(['Пролог'] + glavy(1, 35), glavy(36, 52) + ['От автора', 'Выражения признательности'], titles=['Геном 1', 'Геном 2']),
                         ('join', 'chapter numbering continues'))
        # Section names before the chapter word ("Часть вторая. Глава 65"; "Глава 7. Эпизод 2" going on from "Глава 7. Эпизод 1").
        self.assertEqual(self.decision(['Часть первая. Пролог'] + glavy(1, 64), ['Часть вторая. Глава 65'] + glavy(66, 70) + ['Эпилог'])[0], 'join')
        self.assertEqual(self.decision(['Глава 6. Эпизод 2', 'Глава 7. Эпизод 1'], ['Глава 7. Эпизод 2', 'Глава 8. Эпизод 1'], hours=3)[0], 'join')

    def test_end_matter_only_in_the_last_file_with_one_title_joins_three_body(self):
        first = ['Предисловие переводчика', 'Действующие лица', '«Красный берег» IV']
        last = ['Задача трех тел', 'Три тела: Ньютон, фон Нейман', 'Послесловие автора к американскому изданию']
        self.assertEqual(self.decision(first, last, titles=['Задача трех тел'] * 2), ('join', 'end matter only in the last file'))

    def test_every_file_starting_again_is_separate_volumes_pern(self):
        self.assertEqual(self.decision(['Пролог'] + glavy(1, 13), glavy(1, 11), titles=['Песни Перна', 'Певица Перна']),
                         ('volumes', 'each file starts again at chapter 1'))

    def test_every_file_ending_with_its_own_afterword_is_separate_volumes_toradora(self):
        self.assertEqual(self.decision(glavy(1, 6) + ['Послесловие автора'], ['Пролог'] + glavy(1, 7) + ['Послесловие автора'],
                                       titles=['Торадора! Том 1', 'Торадора! Том 2'])[0], 'volumes')

    def test_cautions_are_asked_never_joined(self):
        seasons = self.decision(['s01e%02d' % n for n in range(1, 11)], ['s02e%02d' % n for n in range(1, 11)], titles=['Чёрная звезда'] * 2)
        self.assertEqual(seasons, ('ask', 'seasons'))
        tolkien = self.decision(['Вступление', 'Пролог. О хоббитах', 'Глава I. Неожиданная вечеринка'], ['Глава I. Нежданные гости', 'Глава II. Совет'],
                                titles=['Хранители. Книга первая', 'Хранители. Книга вторая'])
        self.assertEqual(tolkien, ('ask', 'book_words'))
        terror = self.decision(['01. Крозье', '15. Франклин'], ['16. Крозье', '28. Пеглар'], ['29. Ирвинг', '47. Пеглар'], ['48. Гудсир', '67. Талириктуг'],
                               titles=['Террор 1', 'Террор 2', 'Террор 3', 'Террор 4'])
        self.assertEqual(terror, ('ask', 'long'), 'continuing, but four 8-hour files: over 30 hours')
        chest = self.decision(['Маленький Мук', 'Карлик Нос'], ['Конек-горбунок'], titles=['Сундучок первый', 'Сундучок второй'],
                              credits=['Вильгельм Гауф | Чтец Один', 'Пётр Ершов | Чтец Два'], hours=2)
        self.assertEqual(chest, ('ask', 'authors'))
        martin = self.decision(['Лечение мартышками', 'Человек в форме груши'], ['И смерть его наследие', 'Башня Пепла'],
                               titles=['Миры Джорджа Мартина 1', 'Миры Джорджа Мартина 2'], hours=6)
        self.assertEqual(martin, ('ask', 'unclear'), 'a story collection split in two: the chapters do not settle it')

    def test_review_n3_episodes_tomes_and_several_works_are_asked_never_joined(self):
        # Senua's 0.22.0 review, N3: three routes joined where ruling 19b asks (season/episode markers; book or volume
        # words; joins holding several works).
        episodes = self.decision(['Эпизод %d' % n for n in range(1, 11)], ['Эпизод %d' % n for n in range(11, 21)], titles=['Тёмный город'] * 2, hours=3)
        self.assertEqual(episodes, ('ask', 'seasons'), 'continuing episode numbers are episodes, not chapters')
        tomes = self.decision(glavy(1, 10), glavy(11, 20), titles=['Собрание сочинений. Том 1', 'Собрание сочинений. Том 2'], hours=3)
        self.assertEqual(tomes, ('ask', 'book_words'), '"Том 1 / 2" like "Книга 1 / 2"')
        self.assertEqual(self.decision(glavy(1, 10), glavy(11, 20), titles=['Собрание сочинений. Книга 1', 'Собрание сочинений. Книга 2'], hours=3),
                         ('ask', 'book_words'), 'the "Книга" twin, as before')
        works = self.decision(['01. Начало', '02. Дорога'], ['03. Дом', '04. Сад'], ['05. Лес', '06. Река'], ['07. Поле', '08. Конец'],
                              titles=['Альфа 1', 'Альфа 2', 'Бета', 'Гамма'], hours=3)
        self.assertEqual(works, ('ask', 'works'), 'three works in four files')
        # Positive controls: the same chapters under one work, an episode inside a chapter, and tome-named volumes.
        self.assertEqual(self.decision(['01. Начало', '02. Дорога'], ['03. Дом', '04. Сад'], ['05. Лес', '06. Река'], ['07. Поле', '08. Конец'],
                                       titles=['Альфа 1', 'Альфа 2', 'Альфа 3', 'Альфа 4'], hours=3), ('join', 'chapter numbering continues'))
        self.assertEqual(self.decision(glavy(1, 10), glavy(11, 20), titles=['Собрание сочинений 1', 'Собрание сочинений 2'], hours=3)[0], 'join')
        self.assertEqual(self.decision(['Глава 6. Эпизод 2', 'Глава 7. Эпизод 1'], ['Глава 7. Эпизод 2', 'Глава 8. Эпизод 1'], hours=3)[0], 'join')
        self.assertEqual(self.decision(['Пролог'] + glavy(1, 5), glavy(1, 6), titles=['Торадора! Том 1', 'Торадора! Том 2'])[0], 'volumes')
        # The work is a precise basis; the row shows the "chapters don't settle it" sentence for it.
        import todo_causes
        self.assertEqual(todo_causes.piece_cause({'piece': {'piece': 'set', 'cause': 'works', 'parts': 4}})['cause'], 'set_unclear')

    def test_review_n9_a_file_starting_at_chapter_one_never_continues(self):
        # Senua's 0.22.0 review, N9 (M18): "continues" needs the next file to start past chapter 1.
        self.assertEqual(self.decision(['Вступление', 'Глава 1'], ['Глава 1', 'Глава 2'], titles=['Ночь'] * 2, hours=3), ('ask', 'unclear'))
        self.assertEqual(self.decision(['Вступление', 'Глава 1'], ['Глава 2', 'Глава 3'], titles=['Ночь'] * 2, hours=3)[0], 'join', 'positive control')

    def test_review_n9_every_file_ending_with_its_own_afterword_is_volumes_even_when_chapters_continue(self):
        # Senua's 0.22.0 review, N9 (M22): the Toradora case passes through the restart rule; this one only the afterword rule decides.
        found = self.decision(['Глава 5', 'Глава 6', 'Послесловие автора'], ['Глава 7', 'Глава 8', 'Послесловие автора'], titles=['Хроники'] * 2, hours=3)
        self.assertEqual(found, ('volumes', 'each file ends with its own afterword'))
        self.assertEqual(self.decision(['Глава 5', 'Глава 6'], ['Глава 7', 'Глава 8', 'Послесловие автора'], titles=['Хроники'] * 2, hours=3)[0], 'join', 'positive control')

    def test_missing_parts_are_named_strangers(self):
        found = part_sets.decide(parts(['Часть I. Глава 1', 'Глава 2'], ['Глава 3', 'Глава 4'], titles=['Незнакомцы 1', 'Незнакомцы 2'], tracks=['1/3', '2/3']))
        self.assertEqual((found['decision'], found['missing'], found['total']), ('missing', [3], 3))


class GroupingTests(unittest.TestCase):
    def rows(self, files):
        return [catalog_row(path, tags) for path, tags in files]

    def test_parts_that_fail_the_split_rules_are_still_one_set_narnia(self):
        files = [('Нарния/3.%d. Хроники Нарнии. Конь и его мальчик.m4b' % n, {'album': 'Конь и его мальчик', 'artist': 'Клайв Льюис',
                  'title': '3.%d. Хроники Нарнии. Конь и его мальчик' % n, 'track': '%d/2' % n}) for n in (2, 1)]
        built = groups.build(self.rows(files))
        self.assertEqual(len(built), 1, list(built)); group = next(iter(built.values()))
        self.assertTrue(group['part_set']); self.assertFalse(group.get('split_book'))
        self.assertEqual([Path(m['path']).name for m in group['members']], ['3.1. Хроники Нарнии. Конь и его мальчик.m4b', '3.2. Хроники Нарнии. Конь и его мальчик.m4b'])

    def test_recorded_volumes_are_books_of_their_own(self):
        files = [('Light Novels/Toradora!/Торадора! Том %d.m4b' % n, {'album': 'Торадора!', 'artist': 'Ююко Такэмия', 'title': 'Торадора! Том %d' % n,
                  'track': '%d/2' % n}) for n in (1, 2)]
        rows = self.rows(files)
        self.assertEqual(len(groups.build(rows)), 1, 'positive control: one set until its chapters are read')
        built = groups.build(rows, volumes=frozenset(r['path'] for r in rows))
        self.assertEqual(len(built), 2); self.assertTrue(all(scope.endswith('\x1fVolume of a series') for scope in built))

    def test_review_n9_parts_of_different_recordings_are_never_a_set(self):
        # Senua's 0.22.0 review, N9 (M19): admission re-checks audio profiles only for split books, and the automatic policy
        # resamples mixed rates and channels, so this grouping refusal is the only guard against joining two recordings.
        def files(profiles=(None, None), readers=('', '')):
            from test_split_books import AAC
            return [catalog_row('Pern/%s.m4b' % title, dict({'album': 'Перн', 'artist': 'Энн Маккефри', 'title': title, 'track': '%d/2' % n},
                                **({'narrator': readers[n - 1]} if readers[n - 1] else {})), profile=profiles[n - 1] or AAC)
                    for n, title in ((1, 'Песни Перна'), (2, 'Певица Перна'))]
        self.assertEqual([bool(g.get('part_set')) for g in groups.build(files()).values()], [True], 'positive control: one recording is one set')
        for label, rows in (('audio profiles differ', files(profiles=(None, ('aac', '22050', 2)))), ('readers differ', files(readers=('Чтец Один', 'Чтец Два')))):
            with self.subTest(label):
                built = groups.build(rows)
                self.assertEqual(len(built), 2, list(built)); self.assertFalse(any(g.get('part_set') for g in built.values()))

    def test_the_same_part_twice_is_never_a_set(self):
        # Live 2026-10-24: "Неисповедимый путь 1.m4b" and "2.m4b" each sit twice in one folder, once with the "й" composed and
        # once decomposed (two copies of each file); joining them would play the book twice.
        import unicodedata
        names = ['Неисповедимый путь 1', 'Неисповедимый путь 2']
        files = [('McCammon/%s.m4b' % form(name), {'album': 'Неисповедимый путь', 'artist': 'Роберт Маккаммон', 'track': '%d/2' % (i + 1)})
                 for form in (lambda v: unicodedata.normalize('NFC', v), lambda v: unicodedata.normalize('NFD', v)) for i, name in enumerate(names)]
        self.assertFalse(any(g.get('part_set') or g.get('split_book') for g in groups.build(self.rows(files)).values()))


class SplitBookShortcutTests(unittest.TestCase):
    """Measured on the live catalog copy (2026-10-25): Dan Brown's chapter-file books (108-155 .m4b files without chapters)
    came back "chapters unreadable" when one probe of 155 failed, and were asked instead of joined as before."""
    def test_a_split_book_with_no_known_chapters_is_joined_as_before(self):
        from unittest import mock
        from public_research import PublicResearch
        research = PublicResearch.__new__(PublicResearch)
        row = {'split_book': {'parts': 40}, 'members': [{'path': 'Z:\\Books\\%02d.m4b' % n, 'metadata': {'tags': {}}, 'duration': 60} for n in range(40)]}
        with mock.patch('part_sets.read_chapters', side_effect=AssertionError('the chapter files of one book are not probed')):
            self.assertIsNone(research._part_set(row, 'Z:\\Books', None))
        row['members'] = row['members'][:3]
        with mock.patch('part_sets.read_chapters', return_value={m['path']: (None if i == 1 else []) for i, m in enumerate(row['members'])}):
            self.assertIsNone(research._part_set(row, 'Z:\\Books', None), 'one unreadable probe: joined as before; admission probes again')
        with mock.patch('part_sets.read_chapters', return_value={m['path']: (['A', 'B'] if i == 1 else []) for i, m in enumerate(row['members'])}):
            self.assertEqual(research._part_set(row, 'Z:\\Books', None)['decision'], 'ask', 'positive control: a part with chapters is decided')


class ResearchTests(test_approve_as_is.ApproveFixture):
    def folder(self, name):
        return self.audio / 'Unsorted' / name

    def rows(self):
        return self.service.reviews.page()['rows']

    def test_continuing_chapters_are_joined_with_every_chapter_kept(self):
        sources = [part(self.folder('Геном') / 'Геном 1.m4b', 'Геном 1', 1, [(0, 500, 'Пролог'), (500, 1000, 'Глава 1')], album='Геном', artist='Э. Г. Риддл', total=2),
                   part(self.folder('Геном') / 'Геном 2.m4b', 'Геном 2', 2, [(0, 500, 'Глава 2'), (500, 1000, 'От автора')], album='Геном', artist='Э. Г. Риддл', total=2)]
        rows = self.start(); self.assertEqual([len(r['members']) for r in rows], [2])
        result = self.research(rows[0])
        self.assertEqual(result['reasons'], [], result.get('reasons')); self.assertEqual(result['part_set']['decision'], 'join')
        self.service.approve_automatic(rows[0], result, threading.Event(), self.service.automatic.research.client); self.wait()
        job = self.service.jobs.status()['jobs'][0]; self.assertEqual(job['state'], 'completed', job)
        self.assertEqual([c['title'] for c in job['output']['validation']['chapters']], ['Пролог', 'Глава 1', 'Глава 2', 'От автора'])
        self.assertTrue(all(not p.exists() for p in sources), 'removed after the joined book was verified in Sorted')

    def test_a_part_set_the_split_rules_refuse_is_joined_when_its_chapters_continue_narnia(self):
        folder = self.folder('Хроники Нарнии') / '3. Конь и его мальчик'
        for n, chapters in ((1, [(0, 500, 'Глава 1.'), (500, 1000, 'Глава 2.')]), (2, [(0, 500, 'Глава 2. Продолжение.'), (500, 1000, 'Глава 3.')])):
            part(folder / ('3.%d. Хроники Нарнии. Конь и его мальчик.m4b' % n), '3.%d. Хроники Нарнии. Конь и его мальчик' % n, n, chapters,
                 album='Хроники Нарнии. Конь и его мальчик', artist='Клайв Стейплз Льюис', total=2)
        rows = self.start(); self.assertEqual([bool(r.get('part_set')) for r in rows], [True])
        result = self.research(rows[0])
        self.assertEqual((result['reasons'], result['part_set']['decision']), ([], 'join'), result.get('reasons'))
        self.service.approve_automatic(rows[0], result, threading.Event(), self.service.automatic.research.client); self.wait()
        job = self.service.jobs.status()['jobs'][0]; self.assertEqual(job['state'], 'completed', job)
        self.assertEqual([c['title'] for c in job['output']['validation']['chapters']], ['Глава 1.', 'Глава 2.', 'Глава 2. Продолжение.', 'Глава 3.'])

    def test_volumes_become_books_of_their_own(self):
        for n in (1, 2):
            part(self.folder('Торадора') / ('Торадора! Том %d.m4b' % n), 'Торадора! Том %d' % n, n, [(0, 600, 'Глава 1'), (600, 1000, 'Послесловие автора')],
                 album='Торадора!', artist='Ююко Такэмия', total=2)
        rows = self.start(); self.assertEqual([len(r['members']) for r in rows], [2])
        result = self.research(rows[0])
        self.assertEqual((result['reasons'], result['part_set']['decision']), (['Separate books of a series'], 'volumes'))
        self.assertEqual(sorted(len(r['members']) for r in self.rows()), [1, 1], 'regrouped: each volume is its own book')
        # Senua's 0.22.0 review, N9 (M21): volumes the chapters decided are not "kept by you", so each still takes the
        # part-of-a-set rule at admission; only Sergei's Keep skips it (the Keep tests check the other side).
        self.assertEqual([r.get('volume_of_set') for r in self.rows()], [{'kept': False}] * 2)

    def test_a_set_the_chapters_do_not_settle_is_asked_and_approved_as_one_book(self):
        for n in (1, 2):
            part(self.folder('Чёрная звезда') / ('Black Star Season %d.m4b' % n), 'Чёрная звезда', n, [(0, 500, 's0%de01' % n), (500, 1000, 's0%de02' % n)],
                 album='Чёрная звезда', artist='Еспер Эрсгорд', total=2)
        row = self.start()[0]
        result = self.research(row)
        self.assertIn('One part of a bigger book', result['reasons']); self.assertEqual(result['part_set']['basis'], 'seasons')
        self.service.automatic._record(row, 'Held', dict(result, until_change=True), None)
        listed = self.service.reviews.page(status='output_attention', group='part_of_book')['rows']
        self.assertEqual([(r['ask']['cause'], r['ask']['file_count']) for r in listed], [('set_seasons', 2)])
        self.assertEqual([f['name'] for f in listed[0]['ask']['files']], ['Black Star Season 1.m4b', 'Black Star Season 2.m4b'], 'the proposed order')
        self.service.approve_book(row['id'], row['revision']); self.wait()
        job = self.service.jobs.status()['jobs'][0]; self.assertEqual(job['state'], 'completed', job)
        self.assertEqual([c['title'] for c in job['output']['validation']['chapters']], ['s01e01', 's01e02', 's02e01', 's02e02'])

    def seasons(self, names=('Black Star Season 1', 'Black Star Season 2')):
        folder = self.folder('Чёрная звезда')
        return [part(folder / (name + '.m4b'), 'Чёрная звезда', n, [(0, 500, 's0%de01' % n), (500, 1000, 's0%de02' % n)], album='Чёрная звезда',
                     artist='Еспер Эрсгорд', total=len(names)) for n, name in enumerate(names, 1)]

    def asked(self):
        row = self.start()[0]
        self.service.automatic._record(row, 'Held', dict(self.research(row), until_change=True), None)
        listed = self.service.reviews.page(status='output_attention', group='part_of_book')['rows']
        self.assertEqual([r['ask']['cause'] for r in listed], ['set_seasons'], 'positive control: asked as one set')
        return listed[0]

    def test_keep_as_separate_books_records_each_file_and_approves_nothing(self):
        # Judy's "Keep as separate books" spec (2026-10-25).
        sources = self.seasons()
        before = [(p.stat().st_size, p.stat().st_mtime_ns) for p in sources]
        row = self.asked()
        self.assertEqual((self.service.todo_coverage()['listed'], self.service.todo_coverage()['still_checking']), (1, 0))
        self.assertEqual(self.service.keep_separate(row['id'], row['revision']), {'kept': 2})
        self.assertEqual([(p.stat().st_size, p.stat().st_mtime_ns) for p in sources], before, 'no file touched')
        self.assertEqual(list(self.sorted.iterdir()), [], 'nothing filed'); self.assertEqual(self.service.jobs.status()['jobs'], [])
        # Confirm 2: the new books count as "Still checking" at the next poll; the set row is gone.
        coverage = self.service.todo_coverage()
        self.assertEqual((coverage['listed'], coverage['still_checking']), (0, 2), coverage)
        rows = self.rows(); self.assertEqual(sorted(len(r['members']) for r in rows), [1, 1])
        self.assertEqual([r.get('volume_of_set') for r in rows], [{'kept': True}] * 2, 'kept by Sergei')
        # Confirm 1: neither file comes back as "Part of a bigger book" for this set.
        for new in rows:
            result = self.research(new)
            self.assertNotIn('One part of a bigger book', result['reasons'], (new['title_clue'], result['reasons']))
            self.assertIsNone(result.get('part_set'))
        # Remembered per file: a library scan with the files unchanged forms no set again.
        self.inv.launch('Audiobooks'); self.inv.worker.join(10)
        self.assertEqual(sorted(len(r['members']) for r in self.rows()), [1, 1])

    def test_keep_splits_a_set_whose_panel_values_were_saved(self):
        # Senua's 0.22.0 review, N1: a Save in the details panel protected the set's group, so Keep recorded the files,
        # answered {'kept': 2} and changed nothing; the set was asked again at the next research, and again after each Keep.
        self.seasons()
        row = self.asked()
        self.service.reviews.save('Audiobooks', row['id'], row['revision'], {'title': 'Чёрная звезда', 'canonical_author': 'Еспер Эрсгорд'}, False, 'Panel Save')
        listed = self.service.reviews.page(status='output_attention', group='part_of_book')['rows']
        self.assertEqual([r['id'] for r in listed], [row['id']], 'positive control: still asked after the Save')
        self.assertTrue(listed[0]['review'], 'positive control: the panel values are saved on the set')
        self.assertEqual(self.service.keep_separate(listed[0]['id'], listed[0]['revision']), {'kept': 2})
        rows = self.rows()
        self.assertEqual(sorted(len(r['members']) for r in rows), [1, 1], 'really split: each file its own book')
        # The set's saved values described the joined book: they are not carried to the new books.
        self.assertEqual([r.get('review') for r in rows], [None, None])
        for new in rows:
            result = self.research(new)
            self.assertNotIn('One part of a bigger book', result['reasons'], result['reasons'])
        self.assertEqual(self.service.reviews.page(status='output_attention', group='part_of_book')['rows'], [])

    def test_review_n9_keep_refuses_a_set_the_app_did_not_ask_about(self):
        # Senua's 0.22.0 review, N9 (M07): the UI shows Keep only on asked set rows, so this server check is the only guard
        # against a stale or hand-made request on a set the app has not asked about (here: not researched yet).
        self.seasons()
        row = self.start()[0]
        self.assertEqual((len(row['members']), bool(row.get('part_set'))), (2, True), 'positive control: a set row')
        with self.assertRaisesRegex(ValueError, 'not a set of parts asked about'):
            self.service.keep_separate(row['id'], row['revision'])
        from scanner import connect
        with connect(self.inv.database) as db:
            recorded = db.execute("SELECT count(*) FROM sqlite_master WHERE name='part_volumes'").fetchone()[0] and db.execute('SELECT count(*) FROM part_volumes').fetchone()[0]
        self.assertEqual(recorded, 0, 'nothing recorded'); self.assertEqual([len(r['members']) for r in self.rows()], [2])

    def test_keep_never_reports_success_without_the_split(self):
        # N1: whatever keeps the set together, Keep refuses with nothing recorded instead of answering "Kept as 2".
        from unittest import mock
        self.seasons()
        row = self.asked()
        with mock.patch('groups.sync'), self.assertRaisesRegex(ValueError, 'not accepted. Nothing was changed'):
            self.service.keep_separate(row['id'], row['revision'])
        from scanner import connect
        with connect(self.inv.database) as db:
            recorded = db.execute("SELECT count(*) FROM sqlite_master WHERE name='part_volumes'").fetchone()[0] and db.execute('SELECT count(*) FROM part_volumes').fetchone()[0]
        self.assertEqual(recorded, 0, 'nothing recorded')
        self.assertEqual([len(r['members']) for r in self.rows()], [2], 'the set is as it was')

    def test_review_n12_a_refused_keep_keeps_the_saved_review(self):
        # Senua's 0.22.0 release review, N12: Keep clears a set's saved panel values only inside the transaction that splits
        # the set. A refused Keep leaves them, the approval, the revision and the "Entered by you" record exactly as they were.
        from unittest import mock
        from scanner import connect
        self.seasons()
        row = self.asked()
        self.service.reviews.save('Audiobooks', row['id'], row['revision'], {'title': 'Чёрная звезда', 'canonical_author': 'Еспер Эрсгорд'}, False, 'Panel Save')
        listed = self.service.reviews.page(status='output_attention', group='part_of_book')['rows']
        self.assertTrue(listed[0]['review'], 'positive control: the panel values are saved on the set')

        def stored():
            with connect(self.inv.database) as db:
                group = tuple(db.execute('SELECT review,approved,revision,fingerprint,superseded FROM book_groups WHERE id=?', (row['id'],)).fetchone())
                entered = [tuple(r) for r in db.execute('SELECT * FROM manual_metadata_sources ORDER BY source_id')]
            return group, entered
        before = stored()
        self.assertTrue(before[0][0] and before[1], 'positive control: a saved review and its "Entered by you" record')
        with mock.patch('groups.sync'), self.assertRaisesRegex(ValueError, 'not accepted. Nothing was changed'):
            self.service.keep_separate(listed[0]['id'], listed[0]['revision'])
        self.assertEqual(stored(), before, 'the saved review, approval, revision and "Entered by you" record are as they were')
        again = self.service.reviews.page(status='output_attention', group='part_of_book')['rows']
        self.assertEqual([(r['id'], r['review']) for r in again], [(row['id'], listed[0]['review'])], 'still asked, with its saved values')

    def test_kept_files_without_a_number_or_a_title_of_their_own_never_return_as_parts(self):
        sources = self.seasons(names=('Тёмный лес', 'Холодный ветер'))
        row = self.asked()
        self.service.keep_separate(row['id'], row['revision'])
        titles = []
        for new in self.rows():
            result = self.research(new)
            self.assertNotIn('One part of a bigger book', result['reasons'], result['reasons'])
            titles.append(result['local_agreement']['title']['value'])
        self.assertEqual(sorted(titles), ['Тёмный лес', 'Холодный ветер'], 'the title from its file name')

    def test_a_kept_file_is_a_whole_book_at_admission_not_one_part_of_a_set(self):
        # One kept file carries a single chapter: as one part of a set it would be refused ("one part is not the whole
        # book"); kept by Sergei it is a book of its own and converts like any other.
        folder = self.folder('Чёрная звезда')
        part(folder / 'Black Star Season 1.m4b', 'Чёрная звезда', 1, [(0, 500, 's01e01'), (500, 1000, 's01e02')], album='Чёрная звезда', artist='Еспер Эрсгорд', total=2)
        second = part(folder / 'Black Star Season 2.m4b', 'Чёрная звезда', 2, [(0, 1000, 's02e01')], album='Чёрная звезда', artist='Еспер Эрсгорд', total=2)
        row = self.asked()
        self.service.keep_separate(row['id'], row['revision'])
        new = next(r for r in self.rows() if r['members'][0]['path'] == str(second))
        result = self.research(new)
        self.assertEqual(result['reasons'], [], result['reasons'])
        self.service.approve_automatic(new, result, threading.Event(), self.service.automatic.research.client); self.wait()
        job = self.service.jobs.status()['jobs'][0]; self.assertEqual(job['state'], 'completed', job)

    def test_a_kept_file_that_changes_is_judged_alone_and_the_set_is_not_asked_again(self):
        sources = self.seasons(names=('Black Star Season 1', 'Black Star Season 2', 'Black Star Season 3'))
        row = self.asked()
        self.service.keep_separate(row['id'], row['revision'])
        sources[0].unlink(); part(sources[0], 'Чёрная звезда', 1, [(0, 400, 's01e01'), (400, 1000, 's01e02')], album='Чёрная звезда', artist='Еспер Эрсгорд', total=3, seconds=2)
        self.inv.launch('Audiobooks'); self.inv.worker.join(10)
        self.assertEqual(sorted(len(r['members']) for r in self.rows()), [1, 1, 1], 'one changed file alone forms no set')

    def test_keep_refuses_anything_but_an_asked_set_and_a_stale_row(self):
        tone = test_approve_as_is.tone
        tone(self.audio / 'Unsorted' / 'Тайна' / 'Тайна.mp3', self.cover, album='Тайна', artist='Лев Толстой')
        self.seasons()
        rows = self.start()
        single = next(r for r in rows if len(r['members']) == 1)
        with self.assertRaises(ValueError): self.service.keep_separate(single['id'], single['revision'])
        held = next(r for r in rows if len(r['members']) == 2)
        self.service.automatic._record(held, 'Held', dict(self.research(held), until_change=True), None)
        with self.assertRaisesRegex(ValueError, 'changed'): self.service.keep_separate(held['id'], held['revision'] + 1)
        from scanner import connect
        with connect(self.inv.database) as db:
            recorded = db.execute("SELECT count(*) FROM sqlite_master WHERE name='part_volumes'").fetchone()[0] and db.execute('SELECT count(*) FROM part_volumes').fetchone()[0]
        self.assertEqual(recorded, 0, 'nothing recorded')

    def test_missing_parts_are_a_missing_files_row_and_convert_whats_there_joins_the_rest(self):
        for n in (1, 2):
            part(self.folder('Dean Koontz') / ('Незнакомцы %d.m4b' % n), 'Незнакомцы %d' % n, n, [(0, 500, 'Глава %d' % (2 * n - 1)), (500, 1000, 'Глава %d' % (2 * n))],
                 album='Незнакомцы', artist='Дин Кунц', total=3)
        row = self.start()[0]
        result = self.research(row)
        self.assertEqual((result['reasons'], result['identity_hold']['missing']), (['Parts of this book are missing'], [3]))
        self.service.automatic._record(row, 'Held', dict(result, until_change=True), None)
        listed = self.service.reviews.page(status='output_attention', group='files_missing')['rows']
        self.assertEqual(len(listed), 1); missing = listed[0]['ask']['missing']
        self.assertEqual(([Path(f).name for f in missing['files']], missing['present'], missing['total']), (['Part 3 of 3'], 2, 3))
        self.service.approve_book(row['id'], row['revision'], without_missing=True); self.wait()
        job = self.service.jobs.status()['jobs'][0]; self.assertEqual(job['state'], 'completed', job)
        self.assertEqual(len(job['manifest']['sources']), 2)


if __name__ == '__main__':
    unittest.main()
