"""Ruling 19 (Sergei 2026-10-24): the parts of a bigger book are joined into that book, in one folder, when they carry
the same album and name one author; an anthology and other folders are never joined (numbered .m4b parts without
chapters of their own were already joined by split_books; parts with their own chapters stay separate books). Real private
audio fixtures, the grouping and the identity steps; no network."""
import subprocess, shutil, unittest
from pathlib import Path

import test_approve_as_is
from test_approve_as_is import tone


class JoinPartsTests(test_approve_as_is.ApproveFixture):
    def books(self):
        rows = self.start()
        return sorted((row['title_clue'], sorted(m['filename'] for m in row['members'])) for row in rows)

    def research_all(self):
        outcomes = {}
        for row in self.service.reviews.page()['rows']:
            result = self.research(row)
            outcomes[tuple(sorted(m['filename'] for m in row['members']))] = result.get('reasons') or []
        return outcomes

    def test_one_book_split_by_two_spellings_of_its_author_is_joined(self):
        tone(self.audio / 'Unsorted' / 'Тихий ветер' / '01.mp3', self.cover, album='Тихий ветер', artist='Иван Петров', track='1/2')
        tone(self.audio / 'Unsorted' / 'Тихий ветер' / '02.mp3', self.cover, album='Тихий ветер', artist='Петров Иван', track='2/2')
        self.assertEqual(self.books(), [('Тихий ветер', ['01.mp3', '02.mp3'])], 'positive control: before ruling 19 these were two "Part of a bigger book" rows')
        self.assertEqual(self.research_all(), {('01.mp3', '02.mp3'): []}, 'the joined book is identified and converts')
        # A group stored by an earlier build: the details panel still shows the new wording (Judy's part-sets copy check).
        import json
        from scanner import connect
        with connect(self.inv.database) as db:
            for identity, evidence in db.execute('SELECT id,evidence FROM book_groups WHERE superseded=0').fetchall():
                stored = dict(json.loads(evidence), grouping='One book (Sergei 2026-10-24, ruling 19): files of one folder with the same album and one author (the parts of one book)')
                db.execute('UPDATE book_groups SET evidence=? WHERE id=?', (json.dumps(stored, ensure_ascii=False), identity))
        self.assertEqual([row['grouping'] for row in self.service.reviews.page()['rows']], ['One book: files of one folder with the same album and one author.'])

    def test_readers_in_the_album_artist_tag_do_not_split_the_book(self):
        for n in (1, 2, 3):
            extra = {'album_artist': 'Михаил Прокопов, Анна Прокопова'} if n == 2 else {}
            tone(self.audio / 'Unsorted' / 'Плюшевая голова' / ('%d.mp3' % n), self.cover, album='Плюшевая голова', artist='Влад Райбер', track='%d/3' % n, **extra)
        self.assertEqual(self.books(), [('Плюшевая голова', ['1.mp3', '2.mp3', '3.mp3'])])

    def test_cd_numbers_in_the_album_do_not_split_the_book(self):
        tone(self.audio / 'Unsorted' / 'Good Omens' / 'CD1 - 01.mp3', self.cover, album='Good Omens CD1', artist='Neil Gaiman', track='1')
        tone(self.audio / 'Unsorted' / 'Good Omens' / 'CD2 - 01.mp3', self.cover, album='Good Omens CD2', artist='Neil Gaiman', track='1')
        self.assertEqual([files for _, files in self.books()], [['CD1 - 01.mp3', 'CD2 - 01.mp3']])

    def test_an_anthology_and_other_folders_are_never_joined(self):
        # Different authors under one album: separate stories, never one author's book.
        tone(self.audio / 'Unsorted' / 'Самая страшная книга' / '03.mp3', self.cover, album='Самая страшная книга', artist='Станислав Миллер')
        tone(self.audio / 'Unsorted' / 'Самая страшная книга' / '04.mp3', self.cover, album='Самая страшная книга', artist='Максим Кабир')
        # The same album in two folders.
        tone(self.audio / 'Unsorted' / 'A' / 'Книга.mp3', self.cover, album='Книга', artist='Анна Смирнова')
        tone(self.audio / 'Unsorted' / 'B' / 'Книга.mp3', self.cover, album='Книга', artist='Анна Смирнова')
        files = [files for _, files in self.books()]
        self.assertEqual(sorted(files), sorted([['03.mp3'], ['04.mp3'], ['Книга.mp3'], ['Книга.mp3']]))

    def test_two_books_of_one_series_on_their_own_discs_are_held_as_files_unclear(self):
        # Senua's 0.22.0 early review, probe A / G3: this converted on its own into "Ведьмак" and removed all four originals.
        for disc, (work, reader) in enumerate((('Последнее желание', 'Чтец Один'), ('Меч предназначения', 'Чтец Два')), 1):
            for n in (1, 2):
                tone(self.audio / 'Unsorted' / 'Ведьмак' / ('%d-%d.mp3' % (disc, n)), self.cover, album='Ведьмак', artist='Анджей Сапковский',
                     album_artist=reader, disc=str(disc), track=str(n), title='%s %d' % (work, n))
        self.assertEqual([len(files) for _, files in self.books()], [4])
        outcomes = self.research_all()
        self.assertIn('Source membership uncertain', outcomes[('1-1.mp3', '1-2.mp3', '2-1.mp3', '2-2.mp3')], 'held: never converted on its own')
        row = self.service.reviews.page()['rows'][0]
        self.service.automatic._record(row, 'Held', dict(self.research(row), until_change=True), None)
        listed = self.service.reviews.page(status='output_attention', group='files_unclear')['rows']
        self.assertEqual(len(listed), 1)
        ask = listed[0]['ask']
        self.assertEqual((ask['kind'], ask['cause']), ('files_unclear', 'works'))
        self.assertEqual(ask['facts']['works'], [{'name': 'Последнее желание', 'files': 2}, {'name': 'Меч предназначения', 'files': 2}])


if __name__ == '__main__':
    unittest.main()
