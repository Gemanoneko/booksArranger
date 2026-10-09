import copy
import os
from pathlib import Path
import tempfile
import unittest

from metadata import propose, future_audio_tags
from scanner import Inventory

SCRATCH=Path(__file__).resolve().parents[1]/'scratch'/'anthology-tests'
SCRATCH.mkdir(parents=True,exist_ok=True)

class AnthologyTests(unittest.TestCase):
    def setUp(self):
        self.root=os.path.join(str(SCRATCH),'Audiobooks')
        self.path=os.path.join(self.root,'existing.mp3')
        self.review={'original_language':'Russian','title':'Рассказы','author':'Сохраненное имя автора',
                     'series':'','number':'','genre':'','topic':'','multi_author':False,
                     'anthology':True,'canonical_author':'Проверенные авторы','narrator':'Проверенный чтец'}

    def test_confirmed_standalone_and_series_collections(self):
        standalone=propose(self.path,self.root,'audiobook',{},self.review)
        self.assertEqual(standalone['path'],os.path.join(self.root,'Сборники','Рассказы - Проверенные авторы.m4b'))
        self.review.update(series='Пять Вечеров',number='2',multi_author=True)
        series=propose(self.path,self.root,'audiobook',{},self.review)
        self.assertEqual(series['path'],os.path.join(self.root,'Сборники','Пять Вечеров','Пять Вечеров - 2 - Рассказы - Проверенные авторы.m4b'))
        self.assertEqual(self.review['author'],'Сохраненное имя автора')
        self.assertTrue(self.review['multi_author'])

    def test_anthology_unused_folder_and_missing_credit_are_conservative(self):
        self.review['author']=''
        self.assertEqual(propose(self.path,self.root,'audiobook',{},self.review)['confidence'],'Reviewed preview')
        self.review['canonical_author']=''
        self.assertEqual(propose(self.path,self.root,'audiobook',{},self.review)['confidence'],'Needs review')
        self.assertEqual(propose(self.path,self.root,'audiobook',{},self.review)['path'],'')
        self.review['canonical_author']='Проверенные авторы'
        self.review['series']='Пять Вечеров'
        self.assertEqual(propose(self.path,self.root,'audiobook',{},self.review)['path'],'')

    def test_single_author_and_multi_author_novels_keep_their_routes(self):
        self.review['anthology']=False
        self.assertEqual(propose(self.path,self.root,'audiobook',{},self.review)['path'],os.path.join(self.root,'Сохраненное имя автора','Рассказы - Сохраненное имя автора.m4b'))
        self.review.update(series='Цикл романов',number='1',multi_author=True)
        self.assertEqual(propose(self.path,self.root,'audiobook',{},self.review)['path'],os.path.join(self.root,'Цикл романов','Цикл романов - 1 - Рассказы - Сохраненное имя автора.m4b'))

    def test_ebook_podcast_and_unreviewed_evidence_never_route_as_anthology(self):
        self.review['genre']='Horror'
        ebook=propose(self.path,self.root,'ebook',{},self.review)
        self.assertNotIn('Сборники',ebook['path'])
        self.assertIn(os.path.join('Horror','Сохраненное имя автора'),ebook['path'])
        self.assertEqual(propose(self.path,self.root,'podcast',{},self.review)['path'],self.path)
        self.assertEqual(propose(self.path,self.root,'audiobook',{'artist':'Several names','tags':{'genre':'Anthology'}})['path'],'')

    def test_roles_ignore_source_reader_and_preserve_all_comment_values(self):
        metadata={'author':'SOURCE READER','artist':'SOURCE READER','album_artist':'SOURCE READER',
                  'tags':{'artist':'SOURCE READER','comment':'Original comment\r\nSecond line',
                          'COMMENTS':['Other comment','Supplemental reader clue'],'private':'Unchanged'}}
        frozen=copy.deepcopy(metadata)
        unknown=future_audio_tags(metadata)
        self.assertEqual(unknown['ARTIST'],'')
        self.assertEqual(unknown['narrator'],'')
        reviewed=future_audio_tags(metadata,self.review)
        self.assertEqual(reviewed['ARTIST'],'Проверенные авторы')
        self.assertNotEqual(reviewed['ARTIST'],'Проверенный чтец')
        self.assertIn('Original comment\r\nSecond line',reviewed['COMMENTS'])
        self.assertIn('Other comment',reviewed['COMMENTS'])
        self.assertIn('Narrator: Проверенный чтец',reviewed['COMMENTS'])
        self.assertEqual(len(reviewed['comment_fields']),3)
        self.assertFalse(reviewed['artist_from_folder'])
        self.assertEqual(future_audio_tags(metadata,self.review),reviewed)
        self.assertEqual(metadata,frozen)
        metadata['tags']['comment']+='\nNarrator: Проверенный чтец'
        self.assertFalse(future_audio_tags(metadata,self.review)['narrator_appended'])

    def test_legacy_review_json_defaults_remain_compatible_and_durable(self):
        legacy={key:value for key,value in self.review.items() if key not in {'anthology','canonical_author','narrator'}}
        self.assertNotIn('Сборники',propose(self.path,self.root,'audiobook',{},legacy)['path'])
        tags=future_audio_tags({'tags':{'comment':'Keep this'}},legacy)
        self.assertEqual(tags['ARTIST'],legacy['author'])
        self.assertTrue(tags['artist_from_folder'])
        self.assertEqual(tags['COMMENTS'],'Keep this')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            base=Path(folder)
            roots={'Audiobooks':str(base/'audio'),'Podcasts':str(base/'audio'/'Podcasts'),'Ebooks':str(base/'ebooks')}
            for root in roots.values():Path(root).mkdir(parents=True,exist_ok=True)
            source=Path(roots['Audiobooks'])/'book.mp3';source.write_bytes(b'fixture')
            reader=lambda *args:{'artist':'SOURCE READER','author':'SOURCE READER','tags':{'comment':'Keep this'}}
            inventory=Inventory(base/'state'/'inventory.sqlite3',roots,reader)
            inventory.launch('Audiobooks');inventory.worker.join(5)
            inventory.save_review(roots['Audiobooks'],str(source),legacy)
            old=inventory.rows('Audiobooks')[0]
            self.assertEqual(old['tag_preview']['ARTIST'],legacy['author'])
            inventory.save_review(roots['Audiobooks'],str(source),self.review)
            restored=Inventory(base/'state'/'inventory.sqlite3',roots,reader).rows('Audiobooks')[0]
            self.assertTrue(restored['review']['anthology'])
            self.assertEqual(restored['review']['canonical_author'],'Проверенные авторы')
            self.assertEqual(restored['review']['narrator'],'Проверенный чтец')
            self.assertEqual(source.read_bytes(),b'fixture')

if __name__=='__main__':unittest.main()
