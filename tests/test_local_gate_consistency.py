"""Actual eight hold shapes, with synthetic paths and no file/network access."""
import copy
from pathlib import Path
import unittest

from source_identity import source_gate

ROOT=Path('C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/local-gate-fixtures')
CONFLICT='Sources disagree on the title or author'

# Saved v0.19.0 title/author shapes, not a whitelist used by production code.
CASES=(
    ('Пратчетт Терри - Книги номов. 01. Угонщики','Книги номов. Кн. 01. Угонщики','Пратчетт Терри',['Пратчетт Терри','Терри Пратчетт','Pratchet Terry','Terry Pratchet']),
    ('Максим Кабир - Тантеом','Максим Кабир - Тантеом','Максим Кабир',['Максим Кабир','Кабир Максим']),
    ('Марьяна Романова - Мёртвые из Верхнего Лога','Марьяна Романова - Мёртвые из Верхнего Лога','Марьяна Романова',['Марьяна Романова','Романова Марьяна']),
    ('Witcher 9 - Вороний перекрёсток','Witcher 9 - Вороний перекрёсток','Сапковский Анджей',['Сапковский Анджей','Анджей Сапковский','Andrzej Sapkowski','Sapkowski Andrzej']),
    ('Dale Stewart 01 - Summer of Night','Dale Stewart 01 - Summer of Night','Симмонс Дэн',['Симмонс Дэн','Дэн Симмонс','Dan Simmons','Simmons Dan']),
    ('Dale Stewart 02 - Children of the Night','Children of the Night','Dan Simmons',['Dan Simmons','Simmons Dan','Дэн Симмонс','Симмонс Дэн']),
    ('Dale Stewart 02.1 - Fires of Eden','Dale Stewart 02.1 - Fires of Eden','Дэн Симмонс',['Дэн Симмонс','Симмонс Дэн','Dan Simmons','Simmons Dan']),
    ('Dale Stewart 03 - A Winter Haunting','Dale Stewart 03 - A Winter Haunting','Дэн Симмонс',['Дэн Симмонс','Симмонс Дэн','Dan Simmons','Simmons Dan']),
)


def fixture(filename,title,author,aliases):
    path=ROOT/author/(filename+'.m4b')
    member={'path':str(path),'filename':path.name,'metadata':{'tags':{'album':title,'artist':author}},'missing':False,'error':''}
    return {'members':[member]}, {'titles':[title],'author_aliases':aliases,'identity_basis':'local_agreement',
        'policy_version':'standing-17-v1','full_author_verified':True,'verified_series':{}}


class LocalFilenameGateTests(unittest.TestCase):
    def test_all_eight_saved_shapes_agree_through_local_source_gate(self):
        for case in CASES:
            with self.subTest(filename=case[0]):
                row,work=fixture(*case)
                self.assertEqual(source_gate(row,work),[])

    def test_general_numbered_cycle_label_is_not_an_author(self):
        row,work=fixture('The Copper Chronicle 12.3 - Evening Journey','Evening Journey','Alice Writer',['Alice Writer'])
        self.assertEqual(source_gate(row,work),[])

    def test_author_prefixed_album_retains_title_identity(self):
        row,work=fixture('Alice Writer - Evening Journey','Alice Writer - Evening Journey','Alice Writer',['Alice Writer'])
        self.assertEqual(source_gate(row,work),[])

    def test_different_real_filename_author_still_refused(self):
        row,work=fixture('Other Person - Evening Journey','Evening Journey','Alice Writer',['Alice Writer'])
        self.assertIn(CONFLICT,source_gate(row,work))

    def test_same_author_different_filename_book_still_refused(self):
        row,work=fixture('Alice Writer - Completely Different Work','Evening Journey','Alice Writer',['Alice Writer'])
        self.assertIn(CONFLICT,source_gate(row,work))

    def test_changed_volume_number_is_not_a_spelling_slip(self):
        row,work=fixture('Alice Writer - Chronicles. 02. Journey','Chronicles. 01. Journey','Alice Writer',['Alice Writer'])
        self.assertIn(CONFLICT,source_gate(row,work))

    def test_numbered_label_requires_real_embedded_author_match(self):
        for artist in ('','Other Person'):
            with self.subTest(artist=artist):
                row,work=fixture('Copper Cycle 07 - Evening Journey','Evening Journey',artist,['Alice Writer'])
                self.assertIn(CONFLICT,source_gate(row,work))

    def test_explicit_wrong_author_tag_is_not_overruled_by_matching_artist(self):
        row,work=fixture('Copper Cycle 07 - Evening Journey','Evening Journey','Alice Writer',['Alice Writer'])
        row['members'][0]['metadata']['tags']['author']='Other Person'
        self.assertIn(CONFLICT,source_gate(row,work))

    def test_nonlocal_provider_identity_does_not_get_local_relaxation(self):
        row,work=fixture('Copper Cycle 07 - Evening Journey','Evening Journey','Alice Writer',['Alice Writer'])
        work.pop('identity_basis')
        self.assertIn(CONFLICT,source_gate(row,work))

    def test_narrator_or_arbitrary_nonperson_prefix_does_not_become_an_author(self):
        for prefix in ('Read by Alice Writer 07','Various Authors','Chapter 03 extra'):
            with self.subTest(prefix=prefix):
                row,work=fixture(prefix+' - Evening Journey','Evening Journey','Alice Writer',['Alice Writer'])
                self.assertIn(CONFLICT,source_gate(row,work))

    def test_changed_embedded_album_remains_a_conflict(self):
        row,work=fixture('Alice Writer - Evening Journey','Evening Journey','Alice Writer',['Alice Writer'])
        row['members'][0]['metadata']['tags']['album']='Completely Different Work'
        self.assertIn(CONFLICT,source_gate(row,work))

    def test_nonidentity_admission_barriers_are_preserved(self):
        for change,reason in (({'missing':True},'Source files unavailable or unreadable'),
                              ({'error':'read failed'},'Source files unavailable or unreadable')):
            row,work=fixture(*CASES[3]);row['members'][0].update(change)
            self.assertIn(reason,source_gate(row,work))
        # 0.22.1, item 9 (Sergei 2026-10-25, "0 Those Who Seek Forgiveness"): one file has nothing to order.
        row,work=fixture(*CASES[3]);self.assertEqual(len(row['members']),1);row['members'][0]['order_conflict']=True
        self.assertNotIn('Playback order uncertain',source_gate(row,work))
        row,work=fixture(*CASES[3]);row['source_partition_uncertain']=True
        self.assertIn('Source membership uncertain',source_gate(row,work))
        row,work=fixture(*CASES[3]);row['members'][0]['metadata']['tags']['track']='1/2'
        self.assertIn('Source membership uncertain',source_gate(row,work))
        row,work=fixture(*CASES[3]);row['members'][0]['path']=str(ROOT/'bad.aiff')
        self.assertIn('Audio format needs an encoding decision',source_gate(row,work))

    def test_helper_does_not_mutate_input_metadata(self):
        row,work=fixture(*CASES[3]);before=copy.deepcopy((row,work))
        self.assertEqual(source_gate(row,work),[])
        self.assertEqual((row,work),before)


if __name__=='__main__':unittest.main()
