"""The three hold rows of the to-do list (Judy 2026-10-24, 0.22.0 review B3-B5): Part of a bigger book, Files unclear,
Order unclear, each with its typed cause and the files Approve will use; Approve uses an order Sergei saved; every current
book is listed or accounted for. Pure causes on member dicts; end to end on real private audio. No network."""
import json, os, unittest
from pathlib import Path

import test_approve_as_is
from test_approve_as_is import tone
import todo_causes
from review_backend import member_key
from scanner import connect


def member(path, **tags):
    return {'path': path, 'filename': Path(path).name, 'metadata': {'tags': tags}}


class CauseTests(unittest.TestCase):
    """One case per cause in Judy's B4 tables, from the members already in a row."""
    def test_order_causes(self):
        self.assertEqual(todo_causes.order_cause([member('a/Пролог.mp3'), member('a/Глава 1.mp3')])['cause'], 'no_tracks')
        some = todo_causes.order_cause([member('a/1.mp3', track='1'), member('a/x.mp3'), member('a/y.mp3')])
        self.assertEqual((some['cause'], some['missing'], some['total']), ('some_missing', 2, 3))
        self.assertEqual(todo_causes.order_cause([member('a/1.mp3', track='1'), member('a/2.mp3', track='1')])['cause'], 'tied')
        self.assertEqual(todo_causes.order_cause([member('a/1.mp3', track='2'), member('a/2.mp3', track='3')])['cause'], 'gaps')
        self.assertEqual(todo_causes.order_cause([member('a/1.mp3', track='1'), member('a/2.mp3', track='3')])['cause'], 'gaps')
        # Measured on the live catalog copy (2026-10-24): 40 of 120 Order unclear rows have file names and track tags that
        # number the files differently, 32 have track tags that are not plain numbers; 'unknown' is left for the rest.
        conflict = [dict(member('a/02 x.mp3', track='1'), order_conflict=True), member('a/01 y.mp3', track='2')]
        self.assertEqual(todo_causes.order_cause(conflict)['cause'], 'conflict')
        self.assertEqual(todo_causes.order_cause([member('a/1.mp3', track='1.'), member('a/2.mp3', track='2')])['cause'], 'odd_tracks')
        self.assertEqual(todo_causes.order_cause([member('a/1.mp3', track='1'), member('a/2.mp3', track='2')])['cause'], 'unknown')

    def test_files_causes(self):
        M, X = todo_causes.MEMBERSHIP, todo_causes.MIXED
        total = todo_causes.files_cause([member('a/1.mp3', track='1/12'), member('a/2.mp3', track='2/12')], [M])
        self.assertEqual((total['cause'], total['tags_say'], total['here']), ('track_total', 12, 2))
        discs = todo_causes.files_cause([member('a/1.mp3', track='1/1', disc='1/3')], [M])
        self.assertEqual(discs['cause'], 'disc_total')
        one = todo_causes.files_cause([member('a/7.mp3', track='7/20')], [M])
        self.assertEqual((one['cause'], one['index'], one['total']), ('one_of_many', 7, 20))
        lack = todo_causes.files_cause([member('Дюна/01.mp3', album='Дюна'), member('Дюна/02.mp3', album='Дюна'), member('x/Реклама.mp3', album='Реклама')], [M], 'Дюна')
        self.assertEqual((lack['cause'], lack['missing'], lack['total'], lack['flagged']), ('lack_title', 1, 3, ['x/Реклама.mp3']))
        mixed = todo_causes.files_cause([member('a/1.mp3', album='A', artist='P'), member('a/2.mp3', album='A', artist='P'), member('a/3.mp3', album='B', artist='P')], [X])
        self.assertEqual((mixed['cause'], mixed['albums'], mixed['artists']), ('mixed', [{'name': 'A', 'files': 2}, {'name': 'B', 'files': 1}], []))
        artists = todo_causes.files_cause([member('a/1.mp3', album='A', artist='P'), member('a/2.mp3', album='A', artist='Q')], [X])
        self.assertEqual((artists['albums'], [a['name'] for a in artists['artists']]), ([], ['P', 'Q']))
        self.assertEqual(todo_causes.files_cause([member('a/1.mp3'), member('a/2.mp3')], [M], split=True)['cause'], 'parts')
        self.assertEqual(todo_causes.files_cause([member('a/1.mp3'), member('a/2.mp3')], [M])['cause'], 'unknown')

    def test_piece_causes(self):
        cause = lambda piece: todo_causes.piece_cause({'kind': 'piece', 'piece': piece})
        self.assertEqual(cause({'piece': 'chapter'})['cause'], 'chapter')
        self.assertEqual(cause({'piece': 'part_title'})['cause'], 'chapter')
        self.assertEqual(cause({'piece': 'numbered_part'})['cause'], 'numbered_part')
        self.assertEqual(cause({'piece': 'siblings', 'count': 3}), {'cause': 'siblings', 'beside': 3})
        self.assertEqual(cause({'piece': 'part_set', 'position': 2, 'parts': 5, 'set': 'Торадора!'}), {'cause': 'part_set', 'index': 2, 'total': 5, 'set': 'Торадора!'})
        self.assertEqual(cause({'piece': 'unreadable'})['cause'], 'unreadable')
        self.assertEqual(todo_causes.piece_cause({'kind': 'piece'})['cause'], 'unknown')

    def test_several_holds_count_once_in_order(self):
        record = {'reasons': ['Playback order uncertain', 'Source membership uncertain'], 'identity_hold': None}
        self.assertEqual(todo_causes.holds(record), ['files_unclear', 'order_unclear'])
        self.assertEqual(todo_causes.holds({'reasons': [todo_causes.PIECE], 'identity_hold': {'kind': 'piece'}}), ['part_of_book'])


class HoldRowTests(test_approve_as_is.ApproveFixture):
    def research_all(self):
        for row in self.service.reviews.page()['rows']:
            result = self.research(row)
            state = 'Held' if result.get('reasons') and not result.get('wait') else 'Waiting for source' if result.get('wait') else 'Queued'
            self.service.automatic._record(row, state, dict(result, until_change=state == 'Held'), None)

    def listed(self, group=None):
        page = self.service.reviews.page(status='output_attention', group=group)
        return {row['title_clue']: row for row in page['rows']}

    def order_book(self):
        # Three chapters of one book with no track numbers: the order comes only from the file names.
        return [tone(self.audio / 'Unsorted' / 'Око мира' / name, self.cover, album='Око мира', artist='Роберт Джордан', title=name[:-4])
                for name in ('Пролог.mp3', 'Глава 1.mp3', 'Глава 2.mp3')]

    def test_order_unclear_is_its_own_row_with_the_order_approve_uses(self):
        self.order_book()
        self.start(); self.research_all()
        rows = self.listed('order_unclear')
        self.assertEqual(list(rows), ['Око мира'], 'positive control: before the 0.22.0 review it was a "Needs you" row under Other')
        ask = rows['Око мира']['ask']
        self.assertEqual((ask['kind'], ask['cause'], ask['file_count']), ('order_unclear', 'no_tracks', 3))
        self.assertEqual([f['name'] for f in ask['files']], [m['filename'] for m in rows['Око мира']['members']], 'the catalog order Approve uses')
        self.assertEqual(self.service.state()['attention_counts']['order_unclear'], 1)
        self.assertEqual(self.listed('other'), {}, 'no "Needs you" row')

    def test_approve_uses_the_order_sergei_saved(self):
        self.order_book()
        self.start(); self.research_all()
        row = self.listed('order_unclear')['Око мира']
        keys = [m['member_key'] for m in row['members']]; reversed_keys = list(reversed(keys))
        self.service.reviews.tracks('Audiobooks', row['id'], row['revision'], reversed_keys, reversed_keys, False, False, True, actor='user')
        row = self.listed('order_unclear')['Око мира']  # still listed: the same files, a saved order
        self.assertTrue(row['ask']['saved_tracks'])
        self.assertEqual([f['name'] for f in row['ask']['files']], [m['filename'] for m in reversed(row['members'])])
        self.service.approve_book(row['id'], row['revision'])
        job = self.service.jobs.status()['jobs'][0]
        self.assertEqual([Path(s['path']).name for s in job['manifest']['sources']], [m['filename'] for m in reversed(row['members'])],
                         'Approve used the saved order (it used to rebuild the catalog order)')

    def test_files_unclear_names_the_track_total(self):
        for n in (1, 2):
            tone(self.audio / 'Unsorted' / 'Дюна' / ('%02d.mp3' % n), self.cover, album='Дюна', artist='Фрэнк Герберт', track='%d/12' % n)
        self.start(); self.research_all()
        rows = self.listed('files_unclear')
        causes = {title: (row['ask']['cause'], row['ask']['facts']) for title, row in rows.items()}
        self.assertEqual(causes.get('Дюна'), ('track_total', {'tags_say': 12, 'here': 2}), causes)

    def test_part_of_a_bigger_book(self):
        tone(self.audio / 'Unsorted' / 'Метро 2033' / 'Глава 5.mp3', self.cover, album='Метро 2033', artist='Дмитрий Глуховский', title='Глава 5')
        self.start(); self.research_all()
        rows = self.listed('part_of_book')
        self.assertEqual(len(rows), 1, self.listed())
        ask = next(iter(rows.values()))['ask']
        self.assertEqual((ask['kind'], ask['cause']), ('part_of_book', 'chapter'))
        self.assertEqual(ask['files'][0]['name'], 'Глава 5.mp3')

    def test_part_of_a_bigger_book_beside_files_with_the_same_title(self):
        tone(self.audio / 'Unsorted' / 'Тихий ветер' / '01.mp3', self.cover, album='Тихий ветер', artist='Иван Петров', track='1/2')
        tone(self.audio / 'Unsorted' / 'Тихий ветер' / '02.mp3', self.cover, album='Тихий ветер', artist='Петров Иван', track='2/2')
        self.start(); self.research_all()
        causes = sorted((row['ask']['cause'], row['ask']['facts']) for row in self.service.reviews.page(status='output_attention', group='part_of_book')['rows'])
        self.assertEqual(causes, [('chapter', {}), ('siblings', {'beside': 1})])

    def test_every_current_book_is_listed_or_accounted_for(self):
        tone(self.audio / 'Unsorted' / 'Утро снайпера' / '01.mp3', self.cover, album='Утро снайпера')  # a question
        self.order_book()  # a hold
        tone(self.audio / 'Unsorted' / 'Старый' / 'Старый.mp3', self.cover, album='Старый дом', artist='Анна Смирнова')  # an old record
        tone(self.audio / 'Unsorted' / 'Новый' / 'Новый.mp3', self.cover, album='Новый сад', artist='Анна Смирнова')  # never researched
        rows = self.start()
        for row in rows:
            if row['title_clue'] in ('Утро снайпера', 'Око мира'):
                result = self.research(row); self.service.automatic._record(row, 'Held', dict(result, until_change=True), None)
            elif row['title_clue'] == 'Старый дом':
                # Held before 0.22.0: no until_change, an older research version. Automatic processing researches it again.
                self.service.automatic._record(row, 'Held', {'reasons': ['Playback order uncertain'], 'research_version': 'standing-20-v1'}, None)
        coverage = self.service.todo_coverage()
        self.assertEqual((coverage['listed'], coverage['still_checking'], coverage['removed'], coverage['with_job']), (2, 2, 0, 0), coverage)
        self.assertEqual(coverage['listed'] + coverage['still_checking'], len(rows), 'every current book is somewhere')
        self.assertEqual(self.service.state()['todo_still_checking'], 2)

    def test_scan_again_on_a_hold_row_says_whether_anything_changed(self):
        paths = self.order_book()
        self.start(); self.research_all()
        row = self.listed('order_unclear')['Око мира']
        result = self.service.scan_again(row['id'], row['revision'])
        self.assertEqual((result['found'], result['changed'], result['scan_started']), (True, False, False))
        paths[0].unlink(); tone(paths[0], self.cover, album='Око мира', artist='Роберт Джордан', title='Пролог', track='1')
        result = self.service.scan_again(row['id'], row['revision'])
        self.assertEqual((result['found'], result['changed']), (True, True))
        self.assertEqual(self.listed('order_unclear'), {}, 'changed files: the book is checked again (still checking)')


if __name__ == '__main__':
    unittest.main()
