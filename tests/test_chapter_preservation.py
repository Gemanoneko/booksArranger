import unittest
from chapter_plan import names,prepare,default,available

def member(n,title='',album='Book'):
    return {'path':str(n)+'.mp3','source_track':str(n),'metadata':{'track_title':title,'tags':{'album':album}},'duration':1}

class Plans(unittest.TestCase):
    def test_missing_names_keep_reliable_original_numbers_after_reorder(self):
        self.assertEqual(names([member(40),member(0),member(1)]),['Track 40','Track 00','Track 01'])
    def test_unicode_names_and_repeated_descriptions_preserved(self):
        self.assertEqual(names([member(1,'Начало'),member(2,'Начало')]),['Начало','Начало'])
    def test_book_title_not_invented_chapter(self):
        self.assertEqual(names([member(1,'Book')]),['Track 01'])
    def test_duplicate_track_numbers_use_playback_order(self):
        self.assertEqual(names([member(5),member(5)]),['Track 01','Track 02'])
    def test_default_only_multiple_available_mp3(self):
        self.assertTrue(default([member(1),member(2)]));self.assertFalse(default([member(1)]))
        m=member(1);m['duration']=None;self.assertFalse(available([m]))

if __name__=='__main__':unittest.main()
