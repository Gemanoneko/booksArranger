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
