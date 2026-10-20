"""v0.14.0 review fixes (Senua C1-C3, M1-M4; Futaba F1-F10) with the real failing names as
fixtures. Private fixtures only: no network, no live catalog, no library access."""
import contextlib,json,sqlite3,tempfile,time,unittest,urllib.parse
from pathlib import Path
from unittest.mock import patch
import groups
import public_research
from local_identity import agreement,compare_names,same_person,clean_title,folder_siblings,catalog_readers,UNREADABLE
from public_research import PublicClient,PublicResearch
from scanner import connect
from source_identity import source_gate
import test_automatic_processing as automatic_fixtures
AREA=automatic_fixtures.AREA
ROOT='Z:\\Audiobooks'

def member(relative,**tags):
    path=ROOT+'\\'+relative.replace('/','\\')
    return {'path':path,'filename':Path(path).name,'metadata':{'tags':tags}}

def record(files,siblings=None):
    return agreement({'members':[member(path,**tags) for path,tags in files]},ROOT,siblings)

class C1ReaderAndCollectionCredits(unittest.TestCase):
    """Narrators and compilers are never authors; collections go to research."""
    LIVE=[('Роман Волков','Недобрый глаз'),('Наташа Белкина','Странный бал'),('Дмитрий Шабров','Таинственная свеча'),
          ('Анастасия Стряпко','Бледная невеста'),('Радион Нечаев','Прогулка домового')]
    def test_c1_reader_credit_never_author_live_antologiya_rows(self):
        for reader,title in self.LIVE:
            with self.subTest(reader=reader):
                tags={'album':title,'artist':'Сборник','album_artist':'читает '+reader,'comment':'исп. '+reader}
                local=record([('Сборники/АНТОЛОГИЯ РУССКОЙ МИСТИКИ/01 читает %s - %s.mp3'%(reader,title),tags)])
                self.assertFalse(local['accepted']);self.assertEqual(local['fields']['author']['state'],'red')
                self.assertNotIn('читает',local['fields']['author']['value'])
                # Even outside a collection folder and without the "Сборник" credit, a reader is never the author.
                tags={'album':title,'album_artist':'читает '+reader}
                local=record([('Мистика/01 читает %s - %s.mp3'%(reader,title),tags)])
                self.assertFalse(local['accepted'])
    def test_c1_collection_credit_never_falls_through_golovin(self):
        tags={'album':'Месяц научной фантастики. Сборник рассказов','artist':'Разные авторы','album_artist':'Кирилл Головин','comment':'читает: Кирилл Головин'}
        local=record([('Сборники/Кирилл Головин - Месяц научной фантастики. Сборник рассказов.m4b',tags)])
        self.assertFalse(local['accepted']);self.assertEqual(local['fields']['author']['state'],'red')
        self.assertIn('names a collection',local['fields']['author']['how'])
        # The collection credit alone, with an agreeing reader-free folder, still holds (no fall-through).
        local=record([('Кирилл Головин/Кирилл Головин - Звёзды.m4b',{'album':'Звёзды','artist':'Разные авторы','album_artist':'Кирилл Головин'})])
        self.assertFalse(local['accepted'])
    def test_c1_reader_named_in_comment_is_held_buldakov(self):
        for title in ('Пока все дома. Новогодняя серия','ТЁМНЫЕ АЛЛЕИ 2.1: Жестокость','Тёмные Аллеи в Кино'):
            with self.subTest(title=title):
                tags={'album':title,'artist':'Олег Булдаков','comment':'Читает Олег Булдаков'}
                local=record([('Булдаков Олег/Олег Булдаков - %s.m4b'%title.replace(':',''),tags)])
                self.assertFalse(local['accepted']);self.assertNotEqual(local['fields']['author']['value'],'Олег Булдаков')
                self.assertTrue(any('reader' in i['why'] for i in local['ignored']),local['ignored'])
        # The Lovecraft episode: composer (the reader) differs; held by the collection folder.
        tags={'album':'Тёмные аллеи 2.2 - Ктулху и аколиты','artist':'Лавкрафт Говард Филлипс','composer':'Булдаков Олег'}
        local=record([('Сборники/Тёмные аллеи/Лавкрафт Говард Филлипс - Тёмные аллеи 2.2 - Ктулху и аколиты.m4b',tags)])
        self.assertFalse(local['accepted'])
    def test_c1_collection_folder_and_title_held_knyazev(self):
        for title in ('Коллекция рождественского хоррора','неSplatterpunk stories 2','Русский русский Хоррор 2 - ПОХОРОНЫ'):
            with self.subTest(title=title):
                local=record([('Сборники/Владимир Князев - %s.m4b'%title,{'album':title,'artist':'Владимир Князев'})])
                self.assertFalse(local['accepted']);self.assertIn('collection',local['fields']['title']['how'])
        # A compiler-like credit inside a collection folder stays a research case (ruling 1 needs a reader signal).

class C1CatalogReaders(unittest.TestCase):
    """A name the library credits as a reader on other books is held as an author (Роман Волков)."""
    def test_c1_author_who_reads_other_books_is_held_volkov(self):
        temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(temp.cleanup);database=Path(temp.name)/'catalog.sqlite3'
        with contextlib.closing(sqlite3.connect(database)) as db:
            db.execute("CREATE TABLE files(root TEXT, path TEXT, kind TEXT, metadata TEXT, missing INTEGER DEFAULT 0, PRIMARY KEY(root,path))")
            for index in range(3):
                db.execute("INSERT INTO files VALUES(?,?,'audiobook',?,0)",(ROOT,ROOT+'\\Unsorted\\Фриц Лейбер - Матерь тьмы [Роман Волков]\\%02d.mp3'%index,
                    json.dumps({'tags':{'album':'Матерь тьмы','artist':'Фриц Лейбер','album_artist':'Читает Роман Волков'}})))
            db.commit()
        readers=catalog_readers(database,ROOT);self.assertIn('Роман Волков',readers)
        row={'members':[member('Роман Волков/Легенды школы №4/1 Пионер.m4b',album='Пионер',artist='Роман Волков')]}
        local=agreement(row,ROOT,[],readers);self.assertFalse(local['accepted']);self.assertIn('reader on other books',local['fields']['author']['how'])
        self.assertTrue(agreement({'members':[member('Фриц Лейбер/Фриц Лейбер - Матерь тьмы.m4b',album='Матерь тьмы',artist='Фриц Лейбер')]},ROOT,[],readers)['accepted'])

class C2SurnamesAndMerging(unittest.TestCase):
    def test_c2_ich_surnames_stay_distinct(self):
        for left,right in (('Дмитрий Костюкевич','Дмитрий Хазанович'),('Ярослав Гжендович','Ярослав Хорошков'),('Ярослав Гжендович','Ярослав Гашек'),
                           ('Светлана Алексиевич','Светлана Иванова'),('Roman Abramovich','Roman Polanski'),('Владимир Несторович','Владимир Васильев')):
            with self.subTest(left=left):self.assertIsNone(compare_names(left,right))
    def test_c2_patronymic_dropped_only_from_three_word_names(self):
        self.assertTrue(compare_names('Лукьяненко Сергей Васильевич','Сергей Лукьяненко'))
        self.assertTrue(compare_names('Кабир Максим Ахмадович','Максим Кабир'))
        self.assertIsNone(compare_names('Гжендович','Ярослав Хорошков'))
    def test_c2_credits_merge_only_on_full_match(self):
        self.assertFalse(same_person('Ярослав Гжендович','Ярослав Хорошков'))
        self.assertFalse(same_person('Гжендович','Ярослав Гжендович'))
        self.assertTrue(same_person('Гжендович Ярослав','Ярослав Гжендович'))
        # Senua's synthetic row: the narrator must never become the author.
        local=record([('Ярослав Гжендович/Ярослав Гжендович - Гелий-3.m4b',{'album':'Гелий-3','artist':'Ярослав Гжендович','album_artist':'Ярослав Хорошков'})])
        self.assertNotEqual(local['fields']['author']['value'],'Ярослав Хорошков')
        if local['accepted']:self.assertEqual(local['fields']['author']['value'],'Ярослав Гжендович')
        # Futaba H16: folder "Ярослав Гашек" never supports tag "Ярослав Гжендович".
        self.assertFalse(record([('Ярослав Гашек/Ярослав Гашек - Пепел и пыль.m4b',{'album':'Пепел и пыль','artist':'Ярослав Гжендович'})])['accepted'])
    def test_c2_initial_pairs_with_given_name(self):
        # Futaba F6 false hold "Таксидермист": folder "Гжендович Я." is the same author.
        # It agrees, but an initial standing for a first name is never merged as the same spelling (R2-2).
        self.assertTrue(compare_names('Гжендович Я.','Ярослав Гжендович'));self.assertFalse(same_person('Гжендович Я.','Ярослав Гжендович'))
        local=record([('Гжендович Я./Таксидермист.m4b',{'album':'Таксидермист','artist':'Ярослав Гжендович'})])
        self.assertTrue(local['accepted'],local['conflicts']);self.assertEqual(local['fields']['author']['value'],'Ярослав Гжендович')

class C3SiblingGuard(unittest.TestCase):
    """The split-part guard sees every direct sibling and the book's other disc/part folders."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);self.database=Path(self.temp.name)/'catalog.sqlite3'
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('''CREATE TABLE files(root TEXT, path TEXT, size INTEGER, modified INTEGER, seen INTEGER, kind TEXT, arrival INTEGER,
                metadata TEXT, error TEXT DEFAULT '', missing INTEGER DEFAULT 0, review TEXT DEFAULT '', PRIMARY KEY(root,path))''')
            rows=[]
            # 2,500 nested files that sort before the root files (the old LIMIT 2000 hid the root siblings).
            for index in range(2500):rows.append((ROOT,ROOT+'\\A Library\\Book %04d\\%02d.mp3'%(index,index%7),'Другая книга %d'%index))
            for index in range(42):rows.append((ROOT,ROOT+'\\Корневой файл %02d.m4b'%index,'Отдельная %d'%index))
            rows.append((ROOT,ROOT+'\\Пётр Сидоров - Длинная книга (Часть 2).m4b','Длинная книга'))
            for folder in ('CD1','CD2'):rows.append((ROOT,ROOT+'\\Unsorted\\Пётр Сидоров - Длинная книга\\%s\\Длинная книга.m4b'%folder,'Длинная книга'))
            for part in ('часть 1','часть 2'):rows.append((ROOT,ROOT+'\\Unsorted\\Пётр Сидоров\\Длинная книга (%s)\\Длинная книга.m4b'%part,'Длинная книга'))
            rows.append((ROOT,ROOT+'\\Пётр Сидоров - Длинная книга (Часть 1).m4b','Длинная книга'))
            db.executemany("INSERT INTO files(root,path,kind,metadata,missing) VALUES(?,?,'audiobook',?,0)",[(r,p,json.dumps({'tags':{'album':a,'artist':'Пётр Сидоров'}})) for r,p,a in rows])
            db.commit()
    def candidate(self,path):
        return {'members':[{'path':path,'filename':Path(path).name,'metadata':{'tags':{'album':'Длинная книга','artist':'Пётр Сидоров'}}}]}
    def test_c3_root_level_siblings_exact_without_cap(self):
        row=self.candidate(ROOT+'\\Пётр Сидоров - Длинная книга (Часть 1).m4b')
        siblings=folder_siblings(self.database,row,ROOT)
        self.assertEqual(len(siblings),43);self.assertTrue(all(Path(s['path']).parent==Path(ROOT) for s in siblings))
        local=agreement(row,ROOT,siblings);self.assertFalse(local['accepted']);self.assertIn('only part of the book',local['fields']['title']['how'])
    def test_c3_disc_and_part_folders_see_each_other(self):
        for path in (ROOT+'\\Unsorted\\Пётр Сидоров - Длинная книга\\CD1\\Длинная книга.m4b',ROOT+'\\Unsorted\\Пётр Сидоров\\Длинная книга (часть 1)\\Длинная книга.m4b'):
            with self.subTest(path=path):
                row=self.candidate(path);siblings=folder_siblings(self.database,row,ROOT)
                self.assertEqual(len(siblings),1);self.assertFalse(agreement(row,ROOT,siblings)['accepted'])
    def test_c3_root_string_mismatch_fails_closed(self):
        row=self.candidate(ROOT+'\\Пётр Сидоров - Длинная книга (Часть 1).m4b')
        for wrong in (ROOT+'\\',ROOT.lower(),'Z:\\Other'):
            with self.subTest(root=wrong):self.assertEqual(folder_siblings(self.database,row,wrong),[UNREADABLE])
    def test_c3_fails_closed(self):
        many={'members':[{'path':ROOT+'\\F%02d\\x.mp3'%i,'filename':'x.mp3','metadata':{'tags':{}}} for i in range(21)]}
        self.assertEqual(folder_siblings(self.database,many,ROOT),[UNREADABLE])
        self.assertEqual(folder_siblings(self.database,self.candidate(ROOT+'\\a.m4b'),''),[UNREADABLE])
        class NoCatalog:pass
        self.assertEqual(PublicResearch(NoCatalog(),leads=[],local_index=self.database.parent/'openlibrary-index')._siblings(self.candidate(ROOT+'\\a.m4b'),ROOT)[0],[UNREADABLE])

class CrossScriptNeedsVowels(unittest.TestCase):
    def test_cross_script_requires_vowels(self):
        for left,right in (('Stephen King','Стивен Хокинг'),('Stephen Hawking','Стивен Кинг'),('Stephen Hawking','Бахман Ричард \\ Кинг Стивен'),('Kong','Кинг'),
                           ('Wild Cards','О. С. Кард'),('Simonova','Семёнова'),('Nina Petrova','Анна Петрова')):
            with self.subTest(left=left):self.assertIsNone(compare_names(left,right))
        for left,right in (('Stephen Hawking','Стивен Хокинг'),('Stephen King','Кинг Стивен'),('Andrzej Sapkowski','Анджей Сапковский'),('Dean Kuntz','Дин Кунц'),
                           ('Graham McNeill','Грэм Макнилл'),('R.L.Stine','Роберт Лоуренс Стайн'),('Robert E. Howard','Говард Роберт'),('Timothy Zahn','Тимоти Зан')):
            with self.subTest(left=left):self.assertEqual(compare_names(left,right)['match'],'cross')
    def test_futaba_controls_hawking_king_and_wild_cards_are_held(self):
        self.assertFalse(record([('Stephen King/Краткая история времени.m4b',{'album':'Краткая история времени','author':'Стивен Хокинг'})])['accepted'])
        self.assertFalse(record([('Stephen Hawking/Оно.m4b',{'album':'Оно','author':'Стивен Кинг'})])['accepted'])
        self.assertFalse(record([('Wild Cards/Игра Эндера.m4b',{'album':'Игра Эндера','artist':'О. С. Кард'})])['accepted'])
        self.assertTrue(record([('Rollins James/Око Бога/01.mp3',{'album':'Око Бога','artist':'Джеймс Роллинс'})])['accepted'])

class MajorFixes(unittest.TestCase):
    def test_m_series_name_is_not_the_title_traun(self):
        local=record([('Timothy Zahn/Траун/Тимоти Зан - Траун. Союзники.m4b',{'album':'Траун','artist':'Тимоти Зан'})])
        self.assertFalse(local['accepted'])
        local=record([('Timothy Zahn/Тимоти Зан - Траун. Союзники.m4b',{'album':'Союзники','artist':'Тимоти Зан'})])
        self.assertTrue(local['accepted']);self.assertEqual(local['fields']['title']['value'],'Союзники')
    def test_m_lone_numbered_part_or_chapter_is_held(self):
        # The live tags (Senua round 2): only the file name carries the part number.
        live={'title':'Игры Немезиды','artist':'Джеймс Кори','album':'Игры Немезиды','album_artist':'Кирилл Головин'}
        local=record([('James S. A. Corey/5. Игры Немезиды/5. Игры Немезиды 1.m4b',live)])
        self.assertFalse(local['accepted']);self.assertIn('numbers this file as one part',local['fields']['title']['how'])
        self.assertFalse(record([('Пётр Сидоров/Пётр Сидоров - Длинная книга (Часть 1).m4b',{'album':'Длинная книга','artist':'Пётр Сидоров'})])['accepted'])
        self.assertFalse(record([('Пётр Сидоров/Длинная книга (часть 2)/01.mp3',{'album':'Длинная книга','artist':'Пётр Сидоров'})])['accepted'])
        for rel,tags in (('James S. A. Corey/5. Игры Немезиды/5. Игры Немезиды 1.m4b',{'album':'Игры Немезиды 1','artist':'Джеймс Кори'}),
                         ('Дэн Браун/Дэн Браун - Глава 01.m4b',{'album':'Глава 01','artist':'Дэн Браун'}),
                         ('Дэн Браун/Дэн Браун - 01.m4b',{'album':'01','artist':'Дэн Браун'})):
            with self.subTest(rel=rel):self.assertFalse(record([(rel,tags)])['accepted'])
        self.assertTrue(record([('Ярослав Гжендович/Ярослав Гжендович - Гелий-3.m4b',{'album':'Гелий-3','artist':'Ярослав Гжендович'})])['accepted'])
        self.assertTrue(record([('Максим Кабир/Максим Кабир - Самая страшная книга 2022.m4b',{'album':'Самая страшная книга 2022','artist':'Максим Кабир'})])['accepted'])
    def test_m_title_cleaned_of_invisible_and_stray_quotes(self):
        self.assertEqual(clean_title('Голос»\u200e'),'Голос');self.assertEqual(clean_title('Отпрыски бури»\u200e'),'Отпрыски бури')
        self.assertEqual(clean_title('«Голос»'),'«Голос»')
    def test_m_bare_first_name_does_not_support_full_author(self):
        self.assertIsNone(compare_names('Владимир','Владимир Васильев'))
        self.assertFalse(record([('Владимир/Лик Чёрной Пальмиры.m4b',{'album':'Лик Чёрной Пальмиры','artist':'Владимир Васильев'})])['accepted'])
        self.assertTrue(compare_names('Роллинс','Джеймс Роллинс'))
    def test_m_middle_initial_author_passes_source_gate(self):
        work={'titles':['Flashforward'],'author_aliases':['Robert J. Sawyer'],'policy_version':'standing-17-v1','identity_basis':'local_agreement'}
        row={'members':[member('Robert J. Sawyer/Robert J. Sawyer - Flashforward.m4b',album='Flashforward',author='Robert J. Sawyer',title='Flashforward')]}
        row['members'][0].update(size=1,modified=1)
        self.assertNotIn('Sources disagree on the title or author',source_gate(row,work))

class M3CacheEviction(unittest.TestCase):
    def test_m3_eviction_uses_the_small_index_and_keeps_newest(self):
        temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(temp.cleanup);now=[1000.0]
        client=PublicClient(Path(temp.name)/'c.sqlite3',fetch=lambda url,*_:('{"n":"%s"}'%url[-6:]).encode(),clock=lambda:now[0])
        with patch.object(public_research,'CACHE_ENTRIES',50),patch.object(public_research,'CACHE_BYTES',10**9):
            for index in range(60):
                now[0]+=10;client.read('https://openlibrary.org/search.json?q=%06d'%index)
        with connect(client.database) as db:
            count=db.execute('SELECT count(*) FROM public_research_cache').fetchone()[0]
            self.assertLessEqual(count,50);self.assertEqual(db.execute('SELECT count(*) FROM public_research_cache_index').fetchone()[0],count)
            self.assertTrue(db.execute("SELECT 1 FROM public_research_cache WHERE url LIKE '%000059'").fetchone())
            plan=' '.join(str(tuple(r)) for r in db.execute('EXPLAIN QUERY PLAN DELETE FROM public_research_cache WHERE fetched<=?',(0,)))
            self.assertIn('public_research_cache_fetched',plan)
            plan=' '.join(str(tuple(r)) for r in db.execute('EXPLAIN QUERY PLAN SELECT count(*),total(size) FROM public_research_cache_index'))
            self.assertNotIn('public_research_cache ',plan+' ')

class M4DefaultRuleCoverage(unittest.TestCase):
    """The research-path classes now run with the production default; their fixtures name the
    author only in the tags. A fixture whose tag and file name agree is accepted locally."""
    def test_m4_research_classes_run_with_the_default_rule(self):
        import test_public_work_identity
        self.assertTrue(automatic_fixtures.AutoTests.local_agreement_default)
        self.assertTrue(test_public_work_identity.FallbackTests.local_agreement_default)
    def test_m4_agreeing_research_fixture_is_accepted_with_the_tag_author(self):
        temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(temp.cleanup);base=Path(temp.name);calls=[]
        def fetch(url,*_):
            calls.append(url)
            if 'api.fantlab.ru' in url or 'wikidata' in url:return b'[]' if 'fantlab' in url else b'{"search":[]}'
            raise AssertionError('identity research must not run: '+url)
        client=PublicClient(base/'catalog.sqlite3',fetch=fetch,clock=lambda:100000.0)
        row=next(iter(groups.build([automatic_fixtures.row(base/'John Writer – A Book.mp3','A Book')]).values()))|{'fingerprint':'private-fixture-fingerprint'}
        from test_local_identity import catalogue
        catalogue(client.database,base,row)
        result=PublicResearch(client,leads=[]).lookup(row,str(base))
        self.assertEqual(result['reasons'],[],result);self.assertEqual(result['metadata_facts']['identity_basis'],'local_agreement')
        self.assertEqual(result['review']['canonical_author'],'Writer John');self.assertEqual(result['review']['title'],'A Book')

class SergeiRulings20261013(unittest.TestCase):
    """Sergei's rulings on the local-agreement edge cases (StandingRules, 2026-10-13)."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
        self.client=PublicClient(self.base/'catalog.sqlite3',fetch=self.closed,clock=lambda:100000.0)
    @staticmethod
    def closed(url,*_):
        import urllib.error
        raise urllib.error.HTTPError(url,503,'private fixture',{},None)
    def lookup(self,files):
        rows=[]
        for relative,tags in files:
            path=self.base/relative;metadata={'title':tags.get('title',''),'artist':tags.get('artist',''),'tags':tags,'probe':{'format':{'duration':'1'}}}
            rows.append({'root':str(path.parent),'path':str(path),'kind':'audiobook','size':10,'modified':10,'metadata':json.dumps(metadata),'error':'','missing':0})
        row=next(iter(groups.build(rows).values()))|{'fingerprint':'private-fixture-fingerprint'}
        from test_local_identity import catalogue
        catalogue(self.client.database,self.base,row)
        return row,PublicResearch(self.client,leads=[]).lookup(row,str(self.base))
    def test_r1_narrator_collection_filed_under_collections_root(self):
        from metadata import propose
        row,result=self.lookup([('Сборники/АНТОЛОГИЯ РУССКОЙ МИСТИКИ/01 читает Роман Волков - Недобрый глаз.mp3',
            {'album':'Недобрый глаз','artist':'Сборник','album_artist':'читает Роман Волков','comment':'исп. Роман Волков','track':'1'})])
        self.assertEqual(result['reasons'],[],result);review=result['review']
        self.assertTrue(review['anthology']);self.assertEqual(review['canonical_author'],'Разные авторы');self.assertEqual(review['narrator'],'Роман Волков')
        self.assertEqual(result['metadata_facts']['collection']['kind'],'narrator_collection')
        path=propose(row['members'][0]['path'],str(self.base),'audiobook',{},review,automatic_facts=result['metadata_facts'])['path']
        self.assertEqual(Path(path).relative_to(self.base).parts,('Сборники','Недобрый глаз - Разные авторы.m4b'))
        # Головин: the tag's own collection credit is kept; the reader is only the narrator.
        row,result=self.lookup([('Сборники/Кирилл Головин - Месяц научной фантастики. Сборник рассказов.m4b',
            {'album':'Месяц научной фантастики. Сборник рассказов','artist':'Разные авторы','album_artist':'Кирилл Головин','comment':'читает: Кирилл Головин'})])
        self.assertEqual(result['reasons'],[],result);self.assertEqual(result['review']['canonical_author'],'Разные авторы');self.assertEqual(result['review']['narrator'],'Кирилл Головин')
    def test_r1_unclear_collection_stays_research(self):
        # One signal only (the credited person reads it), no collection folder or title: research path.
        local=record([('Мистика/Олег Булдаков - Пока все дома.m4b',{'album':'Пока все дома','artist':'Олег Булдаков','comment':'Читает Олег Булдаков'})])
        self.assertFalse(local['accepted']);self.assertIsNone(local['route'])
    def test_r2_tag_wins_on_spelling_slip(self):
        local=record([('Иванов Алексей/Иванов Алексей - Географ глобус пропил.m4b',{'album':'ГЕограф глобус пропил','artist':'Алексей Иванов'})])
        self.assertTrue(local['accepted']);self.assertEqual(local['fields']['title']['value'],'ГЕограф глобус пропил')
        local=record([('Иванов Алексей/Иванов Алексей - Географ глобус пропил.m4b',{'album':'Географ глобус прапил','artist':'Алексей Иванов'})])
        self.assertTrue(local['accepted']);self.assertEqual(local['fields']['title']['value'],'Географ глобус прапил');self.assertIn('tag spelling wins',local['fields']['title']['how'])
        # A different volume number or a short title is never a spelling slip.
        self.assertFalse(record([('Кори/Джеймс Кори - Игры Немезиды 3.m4b',{'album':'Игры Немезиды 2','artist':'Джеймс Кори'})])['accepted'])
        self.assertFalse(record([('Кинг Стивен/Стивен Кинг - Она.m4b',{'album':'Оно','artist':'Стивен Кинг'})])['accepted'])
    def test_r3_one_spelling_per_author_deterministic_and_recorded(self):
        from local_identity import canonical_author,catalog_index,surname_first
        database=self.base/'spellings.sqlite3'
        with contextlib.closing(sqlite3.connect(database)) as db:
            db.execute("CREATE TABLE files(root TEXT, path TEXT, kind TEXT, metadata TEXT, missing INTEGER DEFAULT 0, PRIMARY KEY(root,path))")
            for spelling,count in (('Stephen King',7),('Кинг Стивен',13),('Стивен Кинг',13)):
                for index in range(count):
                    db.execute("INSERT INTO files VALUES(?,?,'audiobook',?,0)",(ROOT,ROOT+'\\Shelf\\%s %02d\\01.mp3'%(spelling,index),json.dumps({'tags':{'artist':spelling,'album':'Книга %d'%index}})))
            db.commit()
        index=catalog_index(database,ROOT)
        name,record_=canonical_author('Стивен Кинг',['Стивен Кинг'],index,'')
        self.assertEqual(name,'King Stephen');self.assertEqual(record_['spelling'],'Stephen King');self.assertIn('English spelling exists locally',record_['why'])
        self.assertEqual(canonical_author('Стивен Кинг',['Стивен Кинг'],index,'')[0],name)
        name,record_=canonical_author('Стивен Кинг',['Стивен Кинг'],index,'ru')
        # Russian original: Cyrillic pool; the 13/13 tie is broken alphabetically, the same for every book.
        self.assertEqual(name,'Кинг Стивен');self.assertEqual(record_['spelling'],'Кинг Стивен');self.assertEqual(record_['order'],'already surname first')
        self.assertEqual(canonical_author('Кинг Стивен',['Кинг Стивен'],index,'ru')[0],name)
        self.assertEqual(surname_first('Александр Варго ( Сергей Давиденко)')[0],'Варго Александр')
        caps={'spellings':{'РОБЕРТ ХАЙНЛАЙН':9,'Роберт Хайнлайн':4},'keys':{}}
        for spelling in caps['spellings']:
            for key in __import__('local_identity')._spelling_keys(spelling):caps['keys'].setdefault(key,[]).append(spelling)
        self.assertEqual(canonical_author('Роберт Хайнлайн',['Роберт Хайнлайн'],caps,'')[0],'Хайнлайн Роберт')
        self.assertEqual(surname_first('Сергей Лукьяненко')[0],'Лукьяненко Сергей');self.assertEqual(surname_first('Лена Обухова, Наталья Тимошенко')[0],'Лена Обухова, Наталья Тимошенко')
    def test_r4_generic_title_accepted_when_author_agrees(self):
        local=record([('Andrzej Sapkowski/Анджей Сапковский - Сборник рассказов.m4b',{'album':'Сборник рассказов','artist':'Анджей Сапковский'})])
        self.assertTrue(local['accepted'],local['conflicts'])
        # Author-safety fixes still apply: a reader or a collection credit is never accepted as the author.
        self.assertFalse(record([('Рассказы/читает Роман Волков - Сборник рассказов.m4b',{'album':'Сборник рассказов','album_artist':'читает Роман Волков'})])['accepted'])
        self.assertFalse(record([('Сборники/Владимир Князев - Сборник рассказов.m4b',{'album':'Сборник рассказов','artist':'Владимир Князев'})])['accepted'])

class Round2Criticals(unittest.TestCase):
    """Senua round 2 (a7d9b42): R2-1 route never drops a person; R2-2 initials pair letter for letter."""
    def test_r2_1_route_never_drops_a_person(self):
        # 1. King with one "Сборник" tag: tags and folder agree on King, never "Разные авторы".
        local=record([('Сборники/Стивен Кинг - Ночная смена/01.mp3',{'album':'Ночная смена','artist':'Стивен Кинг','album_artist':'Сборник','track':'1'})])
        self.assertIsNone(local['route'])
        local=record([('Сборники/Стивен Кинг - Ночная смена/01.mp3',{'album':'Ночная смена. Сборник рассказов','artist':'Стивен Кинг','author':'Сборник'})])
        self.assertIsNone(local['route'])
        # 2. Глуховский reads his own books elsewhere: a research hold, never a collection.
        readers=frozenset({'Дмитрий Глуховский','Олег Булдаков'})
        local=agreement({'members':[member('Глуховский Дмитрий/Дмитрий Глуховский - Рассказы о Родине.m4b',album='Рассказы о Родине',artist='Дмитрий Глуховский')]},ROOT,[],readers)
        self.assertIsNone(local['route']);self.assertFalse(local['accepted']);self.assertIn('reader on other books',local['fields']['author']['how'])
        # 3. King with "читает Князев" under Сборники: King is not dropped; the reader is not the author.
        local=record([('Сборники/Ночная смена/01.mp3',{'album':'Ночная смена','artist':'Стивен Кинг','album_artist':'читает Игорь Князев','track':'1'})])
        self.assertIsNone(local['route']);self.assertFalse(local['accepted'])
        # A collection with no person credit at all still routes (ruling 1).
        local=record([('Сборники/АНТОЛОГИЯ РУССКОЙ МИСТИКИ/01 читает Роман Волков - Недобрый глаз.mp3',{'album':'Недобрый глаз','artist':'Сборник','album_artist':'читает Роман Волков'})])
        self.assertIsNotNone(local['route']);self.assertEqual(local['route']['narrators'],['Роман Волков'])
    def test_r2_2_conflicting_initials_stay_distinct(self):
        from local_identity import canonical_author
        for left,right in (('Стругацкий А.','Стругацкий Б.'),('А. Стругацкий','Б. Стругацкий'),('Толстой А.Н.','Толстой Л.Н.'),('Robert J. Sawyer','Robert K. Sawyer'),('Толстой Л.Н.','Алексей Толстой')):
            with self.subTest(left=left):self.assertIsNone(compare_names(left,right))
        self.assertFalse(record([('Стругацкий Б./Стругацкий Б. - Понедельник начинается в субботу.m4b',{'album':'Понедельник начинается в субботу','artist':'Стругацкий А.'})])['accepted'])
        def index(spellings):
            keys={}
            for spelling in spellings:
                for key in __import__('local_identity')._spelling_keys(spelling):keys.setdefault(key,[]).append(spelling)
            return {'spellings':dict(spellings),'keys':keys}
        self.assertEqual(canonical_author('Толстой А.Н.',['Толстой А.Н.'],index({'Толстой Л.Н.':12,'Толстой А.Н.':2}),'')[1]['spelling'],'Толстой А.Н.')
        self.assertEqual(canonical_author('Стругацкий А.',['Стругацкий А.'],index({'Стругацкий Б.':9,'Аркадий Стругацкий':4}),'')[1]['spelling'],'Стругацкий А.')
        self.assertEqual(canonical_author('Иванов А.',['Иванов А.'],index({'Иванов Андрей':5,'Иванов Алексей':3}),'')[1]['spelling'],'Иванов А.')
        self.assertEqual(canonical_author('Robert J. Sawyer',['Robert J. Sawyer'],index({'Robert K. Sawyer':8}),'')[1]['spelling'],'Robert J. Sawyer')

class FutabaRound2(unittest.TestCase):
    """Futaba round 2 (a7d9b42) non-blocking items folded in."""
    def test_n1_identical_duplicate_credit_is_one_person(self):
        for credit in ('Robert J. Sawyer','Кабир Максим Ахмадович','Максим Кабир, Парфенов М.С.'):
            with self.subTest(credit=credit):
                local=record([('%s/%s - Книга.m4b'%(credit,credit),{'album':'Книга','artist':credit,'album_artist':credit})])
                self.assertTrue(local['accepted'],local['conflicts'])
        # The R2-2 initials fix still holds: different initials are different people.
        self.assertFalse(same_person('Стругацкий А.','Стругацкий Б.'));self.assertFalse(same_person('Толстой А.Н.','Толстой Л.Н.'))
    def test_residual_lone_chapter_file_is_held(self):
        # Futaba H9: "Глава 5" alone in its folder, album = the book, no catalogued sibling.
        local=record([('Иванов Алексей/Тобол/Глава 5.m4b',{'album':'Тобол','title':'Глава 5','artist':'Алексей Иванов'})],[])
        self.assertFalse(local['accepted']);self.assertIn('one chapter',local['fields']['title']['how'])
        local=record([('Иванов Алексей/Тобол/05.m4b',{'album':'Тобол','artist':'Алексей Иванов'})],[])
        self.assertFalse(local['accepted'])
        self.assertTrue(record([('Иванов Алексей/Тобол/Тобол.m4b',{'album':'Тобол','title':'Тобол','artist':'Алексей Иванов'})],[])['accepted'])
        # A lone "01" is how some rips name a one-file book: allowed.
        self.assertTrue(record([('Иванов Алексей/Тобол/01.m4b',{'album':'Тобол','artist':'Алексей Иванов'})],[])['accepted'])

class Round3Critical(unittest.TestCase):
    """Senua round 3 (82bc67d): an author who reads his own book is never filed as a collection."""
    def test_r3_1_self_reading_author_is_held_not_routed(self):
        for tags in ({'album':'Рассказы о Родине','artist':'Дмитрий Глуховский','comment':'Читает Дмитрий Глуховский'},
                     {'album':'Рассказы о Родине','artist':'Дмитрий Глуховский','narrator':'Дмитрий Глуховский'}):
            with self.subTest(tags=sorted(tags)):
                local=record([('Глуховский Дмитрий/Рассказы о Родине.m4b',tags)],[])
                self.assertIsNone(local['route']);self.assertFalse(local['accepted'])
        # Without a collection folder there is no collection filing either.
        local=record([('Мистика/Сборник рассказов.m4b',{'album':'Сборник рассказов','artist':'Разные авторы','album_artist':'читает Роман Волков'})],[])
        self.assertIsNone(local['route'])
        # A real narrator-read collection under a collection folder still routes (ruling 1).
        local=record([('Сборники/АНТОЛОГИЯ РУССКОЙ МИСТИКИ/01 читает Роман Волков - Недобрый глаз.mp3',{'album':'Недобрый глаз','artist':'Сборник','album_artist':'читает Роман Волков'})],[])
        self.assertIsNotNone(local['route'])

if __name__=='__main__':unittest.main()
