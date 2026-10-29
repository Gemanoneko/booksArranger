"""v0.22.0 identity (Sergei 2026-10-24, rulings 6, 6a, 13, 14, 15): title + author from one local
source identify a book; four guards stay (a reader is never an author, parts stay together, a
collection or editor credit is not an author, garbled text is not used); what the files cannot
settle is a question for Sergei, never an Internet search. Real names from the library as
fixtures; private catalog in a temporary SQLite file; no network, no library access."""
import contextlib,json,sqlite3,tempfile,threading,unittest
from pathlib import Path
import groups
import local_identity
identify=lambda *a,**k:local_identity.identify(*a,**k)
garbled=lambda value:local_identity.garbled(value)
IDENTITY_VERSION="local-one-v5"
from public_research import PublicResearch,ResearchWait
from source_identity import source_gate

AREA=Path(__file__).resolve().parents[1]/'scratch'/'identity-v5-tests';AREA.mkdir(parents=True,exist_ok=True)
ROOT='Z:\\Audiobooks'


def member(relative,ext_tags=None,**tags):
    path=ROOT+'\\'+relative.replace('/','\\')
    tags=dict(tags,**(ext_tags or {}))
    return {'path':path,'filename':Path(path).name,'metadata':{'tags':tags},'size':1,'modified':'1','error':'','missing':False,'track':None,'disc':None}


class Offline:
    """Every public source is closed; identity must not need it."""
    def __init__(self,database):self.database=database;self.calls=[]
    def _closed(self,url,*_,**__):
        self.calls.append(url);raise ResearchWait('offline','private fixture',0)
    json=read=_closed
    def discover(self,query,*_):self.calls.append(query);raise ResearchWait('offline','private fixture',0)
    def wikipedia(self,query,*_):self.calls.append(query);raise ResearchWait('offline','private fixture',0)
    def receipt(self,url):return {'url':url}


class Catalog:
    """A private catalog 'files' table holding the given rows plus other library books."""
    def __init__(self,test,rows,library=()):
        temp=tempfile.TemporaryDirectory(dir=AREA);test.addCleanup(temp.cleanup)
        self.database=Path(temp.name)/'catalog.sqlite3'
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute("CREATE TABLE files(root TEXT,path TEXT,kind TEXT,metadata TEXT,missing INTEGER DEFAULT 0,PRIMARY KEY(root,path))")
            for item in [m for row in rows for m in row['members']]+list(library):
                db.execute("INSERT OR REPLACE INTO files VALUES(?,?,'audiobook',?,0)",(ROOT,item['path'],json.dumps(item['metadata'],ensure_ascii=False)))
            db.commit()

    def lookup(self,row):
        research=PublicResearch(Offline(str(self.database)),leads=[])
        return research.lookup(dict(row,_manual_metadata_sources=[]),ROOT,threading.Event())

    def approved(self,row):
        """What Sergei's Approve files (rulings 6b and 11a)."""
        return PublicResearch(Offline(str(self.database)),leads=[]).approved(row,ROOT)


def book(*members,identity='book-1'):
    return {'id':identity,'revision':1,'fingerprint':'fp-'+identity,'source_root':ROOT,'members':list(members)}


def reader_elsewhere(name,index=0):
    """Another library book on which this name is credited as the reader."""
    return member('Другие/Книга %d/01.mp3'%index,album='Другая книга %d'%index,artist='Кто-то Другой',album_artist='читает '+name)


class OneSourceIsEnough(unittest.TestCase):
    def test_tag_title_and_author_identify_a_book_without_a_second_source_watchers(self):
        row=book(member('Dean Koontz/Watchers.m4b',album='Ангелы-хранители',artist='Кунц Дин'))
        result=Catalog(self,[row]).lookup(row)
        self.assertEqual(result['reasons'],[],result.get('reasons'))
        self.assertEqual(result['review']['title'],'Ангелы-хранители')
        self.assertEqual(result['local_agreement']['version'],IDENTITY_VERSION)
        self.assertEqual(result['local_agreement']['author']['basis'],'tag')

    def test_book_in_the_library_root_is_identified_from_its_tags(self):
        row=book(member('Кровавые иллюзии.m4b',album='Кровавые иллюзии',artist='Диана Удовиченко'))
        result=Catalog(self,[row]).lookup(row)
        self.assertEqual(result['reasons'],[],result.get('reasons'));self.assertIn('Удовиченко',result['review']['canonical_author'])

    def test_title_from_file_name_and_author_from_folder_when_there_are_no_tags(self):
        row=book(member('Unsorted/Страуд Джонатан - Пустая могила (Прудникова)/Пустая могила.mp3'))
        record=identify(row,ROOT,[],())
        self.assertTrue(record['accepted'],record)
        self.assertEqual((record['fields']['title']['value'],record['fields']['author']['value']),('Пустая могила','Страуд Джонатан'))

    def test_the_tag_title_wins_over_a_differently_worded_file_name(self):
        row=book(member('John Harwood/John Harwood - Asylum.m4b',album='Мой загадочный двойник',artist='Харвуд Джон'))
        result=Catalog(self,[row]).lookup(row)
        self.assertEqual(result['reasons'],[],result.get('reasons'));self.assertEqual(result['review']['title'],'Мой загадочный двойник')

    def test_no_internet_request_decides_identity(self):
        row=book(member('Dean Koontz/Watchers.m4b',album='Ангелы-хранители',artist='Кунц Дин'))
        catalog=Catalog(self,[row]);research=PublicResearch(Offline(str(catalog.database)),leads=[])
        result=research.lookup(dict(row,_manual_metadata_sources=[]),ROOT,threading.Event())
        self.assertEqual(result['reasons'],[]);self.assertIsNone(result.get('wait'))


class ReaderIsNeverAnAuthor(unittest.TestCase):
    """Guard 1 and ruling 14, in tags AND in file or folder names."""
    def test_bracketed_reader_in_the_artist_tag_gives_way_to_the_file_name_author_sanderson(self):
        row=book(member('Brandon Sanderson/Stormlight/Брендон Сандерсон - Архив Буресвета 4 - Ритм войны (Дружинин Степан).m4b',
                        album='Архив Буресвета 4 - Ритм войны',artist='Степан Дружинин'))
        catalog=Catalog(self,[row]);result=catalog.lookup(row)
        # Ruling 52: «Архив Буресвета 4 - …» is a series split nothing confirms, so the row asks with it filled in.
        self.assertEqual((result['ask']['why'],result['ask']['split']['series']),('title_series','Архив Буресвета'),result.get('reasons'))
        self.assertNotIn('Дружинин',result['ask']['fields']['author']['proposal'])
        # Ruling 3 (2026-10-13): the folder's English spelling is the canonical one.
        review=catalog.approved(row)['review']
        self.assertNotIn('Дружинин',review['canonical_author']);self.assertEqual(review['canonical_author'],'Sanderson Brandon')

    def test_reader_of_other_books_in_the_album_artist_tag_is_not_the_author_shrayber(self):
        row=book(member('Star Wars/Пухов Сергей - Джо Шрайбер - Солдаты смерти.m4b',album='Солдаты смерти',album_artist='Пухов Сергей',artist='Джо Шрайбер'))
        result=Catalog(self,[row],[reader_elsewhere('Сергей Пухов')]).lookup(row)
        self.assertEqual(result['reasons'],[],result.get('reasons'));self.assertEqual(result['review']['canonical_author'],'Шрайбер Джо')

    def test_reader_in_the_author_slot_of_a_file_name_is_never_the_author_troitsky(self):
        row=book(member('Firefly/Олег Троицкий - Firefly. Великолепная девятка.m4b',album='Firefly. Великолепная девятка'))
        result=Catalog(self,[row],[reader_elsewhere('Олег Троицкий',1)]).lookup(row)
        self.assertNotEqual(result['reasons'],[]);self.assertIsNone(result.get('review'))
        self.assertEqual(result['ask']['kind'],'author_unclear')
        self.assertEqual(result['ask']['candidates'][0]['name'],'Олег Троицкий');self.assertEqual(result['ask']['candidates'][0]['reader_count'],1)

    def test_reader_glued_to_the_author_tag_by_a_dash_is_removed_vargo(self):
        row=book(member('Варго Александр/Александр Варго - Пухов Сергей - Гример.m4b',album='Гример',album_artist='Александр Варго - Пухов Сергей'))
        result=Catalog(self,[row],[reader_elsewhere('Пухов Сергей',2)]).lookup(row)
        self.assertEqual(result['reasons'],[],result.get('reasons'));self.assertEqual(result['review']['canonical_author'],'Варго Александр')

    def test_g4_a_dash_joining_two_unknown_people_is_asked_never_filed_whole(self):
        # Senua's early 0.22.0 review (2026-10-24), G4 / ruling 14: an "Author - Reader" tag whose reader the library does not know.
        row=book(member('Unsorted/Гример.m4b',album='Гример',album_artist='Александр Варго - Иван Сидоров'))
        record=identify(row,ROOT,[],())
        self.assertFalse(record['accepted']);self.assertEqual((record['ask']['kind'],record['ask']['why']),('author_unclear','two_people'))
        self.assertNotIn(' - ',local_identity.shown(record)['author'])
        # A folder that names one of them decides it.
        row=book(member('Варго Александр/Гример.m4b',album='Гример',album_artist='Александр Варго - Иван Сидоров'))
        record=identify(row,ROOT,[],())
        self.assertTrue(record['accepted'],record);self.assertEqual(record['fields']['author']['value'],'Александр Варго')


    def test_review_n5_a_dash_joining_three_people_is_never_filed_whole(self):
        # Senua's 0.22.0 review, N5: G4's split handled exactly two names; three were accepted whole as the author.
        credit='Александр Варго - Иван Сидоров - Мария Петрова'
        row=book(member('Unsorted/Гример.m4b',album='Гример',album_artist=credit))
        record=identify(row,ROOT,[],())
        self.assertFalse(record['accepted'],record);self.assertEqual(record['ask']['kind'],'author_unclear')
        self.assertNotIn(' - ',local_identity.shown(record)['author'])
        row=book(member('Варго Александр/Гример.m4b',album='Гример',album_artist=credit))
        record=identify(row,ROOT,[],())
        self.assertTrue(record['accepted'],record);self.assertEqual(record['fields']['author']['value'],'Александр Варго')


class CollectionsAndGarbledTags(unittest.TestCase):
    def test_collection_credit_files_the_book_under_collections_even_in_an_author_folder(self):
        row=book(member('George R. R. Martin/Миры Джорджа Мартина 1.m4b',album='Миры Джорджа Мартина 1',artist='Сборник'))
        result=Catalog(self,[row]).lookup(row)
        self.assertEqual(result['reasons'],[],result.get('reasons'))
        self.assertTrue(result['review']['anthology']);self.assertEqual(result['review']['canonical_author'],'Разные авторы')

    def test_long_author_list_is_a_collection(self):
        row=book(member('Сборники/Адамово яблоко.m4b',album='Адамово яблоко',artist='Мьевиль Ч., Лансдэйл Дж., Буковски Ч., Айриш У.'))
        record=identify(row,ROOT,[],())
        self.assertTrue(record['accepted']);self.assertEqual(record['route']['credit'],'Разные авторы')

    def test_garbled_tags_are_detected(self):
        for value in ('Ìàêñ Áðóêñ','Òåððè Ïðàò÷åòò','��������� �������','РўРµСЂСЂРё РџСЂР°С‚С‡РµС‚С‚'):
            with self.subTest(value=value):self.assertTrue(garbled(value))
        for value in ('Макс Брукс','Jarosław Grzędowicz','Jesper Ersgård','Émile Zola'):
            with self.subTest(value=value):self.assertFalse(garbled(value))

    def test_garbled_tags_are_not_used_and_the_folder_name_is(self):
        # POST-023-04 (0.24.0): cp1251 read as Latin-1 is read repaired (tag_text); the repaired tags name the book.
        row=book(member('Брукс Макс - Мировая война Z/01.mp3',album='ÌÈÐÎÂÀß ÂÎÉÍÀ Z',artist='Ìàêñ Áðóêñ'),
                 member('Брукс Макс - Мировая война Z/02.mp3',album='ÌÈÐÎÂÀß ÂÎÉÍÀ Z',artist='Ìàêñ Áðóêñ'))
        record=identify(row,ROOT,[],())
        self.assertTrue(record['accepted'],record)
        self.assertEqual(local_identity.title_key(record['fields']['title']['value']),local_identity.title_key('Мировая война Z'))
        self.assertTrue(local_identity.compare_names(record['fields']['author']['value'],'Брукс Макс'),record['fields']['author'])
        self.assertFalse(any('garbled' in i['why'] for i in record['ignored']))
        # Bytes that are lost (replacement characters) stay unused: the folder names the book.
        row=book(member('Брукс Макс - Мировая война Z/01.mp3',album='��� Z',artist='���'),
                 member('Брукс Макс - Мировая война Z/02.mp3',album='��� Z',artist='���'))
        record=identify(row,ROOT,[],())
        self.assertEqual((record['fields']['title']['value'],record['fields']['author']['value']),('Мировая война Z','Брукс Макс'))
        self.assertTrue(any('garbled' in i['why'] for i in record['ignored']))

    def test_the_title_in_the_artist_tag_is_not_an_author(self):
        row=book(member('Stephen King/Потаённое окно в потаённый сад.m4b',artist='Потаённое окно в потаённый сад'))
        record=identify(row,ROOT,[],())
        self.assertTrue(record['accepted'],record);self.assertEqual(record['fields']['author']['value'],'Stephen King')

    def test_a_title_glued_into_the_author_tag_is_removed_and_the_full_name_kept(self):
        row=book(member('Stephen King/Легенда о пуле.m4b',artist='Кинг___Легенда_о_пуле'))
        record=identify(row,ROOT,[],())
        self.assertTrue(record['accepted'],record);self.assertEqual(record['fields']['author']['value'],'Stephen King')


class QuestionsForSergei(unittest.TestCase):
    """Ruling 6a: what the files cannot settle is asked; never researched on the Internet."""
    def test_no_author_anywhere_asks_for_the_author(self):
        row=book(member('Unsorted/Ужасы и трэшатинка/Сборник 4/Утро снайпера.mp3',title='Утро снайпера'))
        result=Catalog(self,[row]).lookup(row)
        self.assertEqual(result['reasons'],['Title or author missing']);self.assertEqual(result['ask']['kind'],'title_author')
        self.assertEqual(result['ask']['fields']['title']['proposal'],'Утро снайпера');self.assertEqual(result['ask']['fields']['author']['proposal'],'')
        self.assertIsNone(result['wait'])

    def test_tag_author_and_file_name_author_that_differ_ask_which_one(self):
        row=book(member('Unsorted/Михаил Михеев - Тайна.m4b',album='Тайна',artist='Лев Толстой'))
        result=Catalog(self,[row]).lookup(row)
        self.assertEqual(result['reasons'],['Author unclear']);self.assertEqual(result['ask']['why'],'tag_and_name')
        self.assertEqual([c['name'] for c in result['ask']['candidates']],['Лев Толстой','Михаил Михеев'])
        self.assertEqual(result['ask']['fields']['author']['proposal'],'Лев Толстой')

    def test_two_people_in_the_tags_ask_which_one(self):
        row=book(member('Unsorted/Тайна.m4b',album='Тайна',artist='Лев Толстой',album_artist='Антон Чехов'))
        result=Catalog(self,[row]).lookup(row)
        self.assertEqual(result['ask']['kind'],'author_unclear');self.assertEqual(result['ask']['why'],'two_people')

    def test_a_series_name_in_the_author_slot_never_contradicts_the_tags_wheel_of_time(self):
        row=book(member('Wheel of Time/Колесо времени - 01. Око мира/Око мира.m4b',album='Колесо времени - 01. Око мира',album_artist='Джордан Роберт'))
        catalog=Catalog(self,[row]);result=catalog.lookup(row)
        # Ruling 52: the series split is asked, filled in (nothing confirms «Колесо времени»); the author is the tags'.
        self.assertEqual((result['ask']['why'],result['ask']['fields']['author']['proposal']),('title_series','Джордан Роберт'),result.get('reasons'))
        self.assertEqual(catalog.approved(row)['review']['canonical_author'],'Джордан Роберт')

    def test_the_same_surname_written_with_initials_is_not_a_contradiction_tolkien(self):
        row=book(member('J. R. R. Tolkien/Дж. Р.Р. Толкин - Хоббит, или Туда и обратно.m4b',album='Хоббит, или Туда и обратно',album_artist='Джон Рональд Руэл Толкин'))
        record=identify(row,ROOT,[],())
        self.assertTrue(record['accepted'],record)


class NumberedParts(unittest.TestCase):
    """Rulings 13 and 15: a numbered part with no title of its own is named after its set plus
    its number, automatically."""
    def test_m4b_part_set_with_no_own_titles_names_each_part_set_plus_number_toradora(self):
        parts=[member('Light Novels/Toradora!/Торадора! Том %d.m4b'%n,album='Торадора!',title='Торадора! Том %d'%n,artist='Yuyuko Takemiya',track='%d/3'%n) for n in (1,2,3)]
        row=book(parts[1]);siblings=[{'path':p['path'],'filename':p['filename'],'tags':p['metadata']['tags']} for p in (parts[0],parts[2])]
        record=identify(row,ROOT,siblings,())
        self.assertTrue(record['accepted'],record)
        self.assertEqual(record['fields']['title']['value'],'Торадора! 2');self.assertEqual(record['fields']['title']['basis'],'number_rule')
        self.assertEqual(record['series'],{},'the name already carries the set and the number')
        # Before v0.22.0 the whole set was held ("how to name it needs a rule").
        self.assertFalse(local_identity.agreement(row,ROOT,siblings,())['accepted'])

    def test_single_numbered_m4b_whose_set_cannot_be_proven_is_named_set_plus_number(self):
        one=member('Dean Koontz/Незнакомцы 1.m4b',album='Незнакомцы',title='Незнакомцы 1',artist='Кунц Дин')
        two=member('Dean Koontz/Незнакомцы 2.m4b',album='Незнакомцы',title='Незнакомцы 2',artist='Дин Кунц',composer='другой чтец')
        record=identify(book(one),ROOT,[{'path':two['path'],'filename':two['filename'],'tags':two['metadata']['tags']}],())
        self.assertTrue(record['accepted'],record);self.assertEqual(record['fields']['title']['value'],'Незнакомцы 1')

    def test_a_numbered_m4b_filed_as_its_own_book_passes_the_source_gate_despite_its_track_total(self):
        one=member('Dean Koontz/Незнакомцы 1.m4b',album='Незнакомцы',title='Незнакомцы 1',artist='Кунц Дин',track='1/2')
        two=member('Dean Koontz/Незнакомцы 2.m4b',album='Незнакомцы',title='Незнакомцы 2',artist='Дин Кунц',track='2/2')
        result=Catalog(self,[book(one),book(two,identity='b2')]).lookup(book(one))
        self.assertEqual(result['reasons'],[],result.get('reasons'));self.assertEqual(result['review']['title'],'Незнакомцы 1')

    def test_a_chapter_file_on_its_own_stays_held(self):
        row=book(member('Прогулка Богов/Глава 4.m4b',album='Прогулка Богов',title='Глава 4',artist='Ольга Громыко'))
        others=[member('Прогулка Богов/Глава %d.m4b'%n,album='Прогулка Богов',title='Глава %d'%n,artist='Ольга Громыко') for n in (3,5)]
        result=Catalog(self,[row,book(*others,identity='b2')]).lookup(row)
        self.assertEqual(result['reasons'],['One part of a bigger book']);self.assertIsNone(result.get('ask'))


class PartsStayTogether(unittest.TestCase):
    """Guard 2: files of one folder that share a title and author are one book."""
    def rows(self,files):
        rows=[]
        for index,(relative,tags) in enumerate(files):
            path=ROOT+'\\'+relative.replace('/','\\')
            rows.append({'root':ROOT,'path':path,'size':100+index,'modified':1000+index,'kind':'audiobook','metadata':json.dumps({'tags':tags},ensure_ascii=False),'error':'','missing':0})
        return rows

    def test_chapter_files_with_one_title_tag_form_one_book_pratchett(self):
        folder='Unsorted/Terry Pratchet/Терри Пратчетт - Пастушья корона (Макс Потёмкин)'
        files=[('%s/Пастушья корона %02d.mp3'%(folder,n),{'title':'Пастушья корона ','artist':'Макс Потёмкин'}) for n in range(1,8)]
        built=groups.build(self.rows(files))
        self.assertEqual(len(built),1,list(built));group=next(iter(built.values()))
        self.assertEqual(len(group['members']),7);self.assertEqual(group['numbered_set']['basis'],'same title tag')

    def test_numbered_files_sharing_the_start_of_their_names_form_one_book_monogatari(self):
        folder='Unsorted/Нисио Исин - Monogatari Series - Сборник коротких историй (Adrenalin28)'
        files=[('%s/%02d Моногатари короткие истории - %s.mp3'%(folder,n,name),{}) for n,name in enumerate(('Вступление от переводчика','Буфет Хитаги','Песня Цубасы'),1)]
        built=groups.build(self.rows(files))
        self.assertEqual(len(built),1,list(built));group=next(iter(built.values()))
        self.assertEqual(group['numbered_set']['name'],'Моногатари короткие истории')
        row=dict(group,id='g',revision=1,fingerprint='f',source_root=ROOT)
        record=identify(row,ROOT,[],())
        self.assertTrue(record['accepted'],record)
        self.assertEqual((record['fields']['title']['value'],record['fields']['author']['value']),('Моногатари короткие истории','Нисио Исин'))

    def test_numbered_books_of_one_author_stay_separate_books(self):
        files=[('Stephen King/%02d Stephen King - %s.mp3'%(n,name),{}) for n,name in enumerate(('It','Carrie','Misery'),1)]
        self.assertEqual(len(groups.build(self.rows(files))),3)

    def test_files_with_different_title_tags_stay_separate(self):
        files=[('Сборник/%s.mp3'%name,{'title':'Рассказ %s'%name,'artist':'Автор Один'}) for name in ('Альфа','Бета')]
        # Ruling 68 (0.24.0): never divided, never joined silently: one candidate, held as a folder question.
        built=groups.build(self.rows(files));self.assertEqual(len(built),1)
        group=next(iter(built.values()));self.assertEqual(group['folder_unit']['kind'],'ask');self.assertTrue(group['source_partition_uncertain'])

    # Senua's early 0.22.0 review (2026-10-24), G1-G3: three ways two books became one group that converts on its own.
    def test_g1_numbered_books_under_a_bare_surname_stay_separate_books(self):
        # "Сапковский" is no known first name; the file-name titles name two books.
        files=[('Unsorted/Ведьмак/%02d Сапковский - %s.mp3'%(n,name),{}) for n,name in enumerate(('Последнее желание','Меч предназначения'),1)]
        self.assertEqual(len(groups.build(self.rows(files))),2)

    def test_g1_a_surname_the_library_credits_elsewhere_is_a_person(self):
        files=[('Unsorted/Дозоры/%02d Лукьяненко - Часть %d.mp3'%(n,n),{}) for n in (1,2)]
        built=groups.build(self.rows(files))
        self.assertEqual([len(g['members']) for g in built.values()],[2],'positive control: with no credit elsewhere the shared start names the book')
        files.append(('Other/Черновик/01.mp3',{'artist':'Сергей Лукьяненко','album':'Черновик'}))
        # Ruling 68 (0.24.0) with rulings 19c and 50: «Часть 1», «Часть 2» of one folder are one book whoever the start names.
        self.assertEqual(sorted(len(g['members']) for g in groups.build(self.rows(files)).values()),[1,2])

    def test_g1_numbered_files_with_different_titles_join_only_when_their_folder_names_another_author(self):
        names=('Вступление от переводчика','Буфет Хитаги','Песня Цубасы')
        files=[('Unsorted/Сборник/%02d Моногатари короткие истории - %s.mp3'%(n,name),{}) for n,name in enumerate(names,1)]
        # Ruling 68 (0.24.0): a numbered collection folder is one book (its file names number the whole folder).
        self.assertEqual(len(groups.build(self.rows(files))),1,'one collection folder, numbered 01-03')
        files=[('Unsorted/Сапковский Анджей - Ведьмак/%02d Сапковский - %s.mp3'%(n,name),{}) for n,name in enumerate(names,1)]
        # Ruling 68 (0.24.0): "Вступление от переводчика" is a chapter label, so no file names a work of its own: the folder
        # numbered 01-03 is one book.
        self.assertEqual(len(groups.build(self.rows(files))),1,'one numbered folder')

    def test_g2_a_junk_title_tag_never_joins_books(self):
        files=[('Unsorted/Кинг/Кинг - %s.mp3'%name,{'title':'Аудиокнига','artist':'Стивен Кинг','track':str(n)}) for n,name in enumerate(('Оно','Мизери'),1)]
        self.assertEqual(len(groups.build(self.rows(files))),2)
        # Live catalog 2026-10-24: 5 Сборник folders of stories each tagged "Без имени".
        files=[('Unsorted/Ужасы. Сборник рассказов/Сборник/%s.mp3'%name,{'title':'Без имени'}) for name in ('Бритва','Сепсис','Оплата')]
        # Ruling 68 (0.24.0): one folder of stories is one candidate, held as a folder question; the junk tag names nothing.
        built=groups.build(self.rows(files));self.assertEqual(len(built),1)
        group=next(iter(built.values()));self.assertEqual(group['folder_unit']['kind'],'ask');self.assertNotEqual(local_identity.norm(group['title_clue']),'безимени')

    def test_g2_a_junk_set_name_is_never_the_title(self):
        members=[member('Unsorted/Кинг/Кинг - %s.mp3'%name,title='Аудиокнига',artist='Стивен Кинг') for name in ('Оно','Мизери')]
        row=dict(book(*members),numbered_set={'version':'same-title-v1','name':'Аудиокнига','basis':'same title tag'})
        record=identify(row,ROOT,[],())
        self.assertNotEqual(local_identity.norm(record['fields']['title']['value']),'аудиокнига',record['fields']['title'])

    def test_review_n4_other_generic_title_tags_never_join_or_name_books(self):
        # Senua's 0.22.0 review, N4: G2 was a word list; "Неизвестно" and "Новая запись" still joined two King books into one
        # book titled "Неизвестно" that converted on its own.
        for junk in ('Неизвестно','Новая запись','Нет названия','Unknown title'):
            files=[('Unsorted/Кинг/Кинг - %s.mp3'%name,{'title':junk,'artist':'Стивен Кинг','track':str(n)}) for n,name in enumerate(('Оно','Мизери'),1)]
            self.assertEqual(len(groups.build(self.rows(files))),2,junk)
            members=[member('Unsorted/Кинг/Кинг - %s.mp3'%name,title=junk,artist='Стивен Кинг') for name in ('Оно','Мизери')]
            row=dict(book(*members),numbered_set={'version':'same-title-v2','name':junk,'basis':'same title tag'})
            record=identify(row,ROOT,[],())
            self.assertNotEqual(local_identity.norm(record['fields']['title']['value']),local_identity.norm(junk),record['fields']['title'])
            one=identify(book(member('Unsorted/Кинг/Кинг - Оно.mp3',title=junk,artist='Стивен Кинг')),ROOT,[],())
            self.assertEqual(one['fields']['title']['value'],'Оно','a single file is named from its file name, not the generic tag')
        # A generic title tag no list knows: the file names name two works, so the files stay separate books.
        files=[('Unsorted/Кинг/Кинг - %s.mp3'%name,{'title':'Запись с диктофона','artist':'Стивен Кинг','track':str(n)}) for n,name in enumerate(('Оно','Мизери'),1)]
        self.assertEqual(len(groups.build(self.rows(files))),2)
        # Positive control: chapter files of one title still join (the Pratchett case, the one live same-title set).
        files=[('Unsorted/Кинг/Оно %02d.mp3'%n,{'title':'Оно','artist':'Стивен Кинг'}) for n in (1,2,3)]
        self.assertEqual([len(g['members']) for g in groups.build(self.rows(files)).values()],[3])

    def test_review_n6_one_album_and_artist_whose_title_tags_name_two_books_is_held(self):
        # Senua's 0.22.0 review, N6: G3's works check covered only the new same-album join. One folder, album "Ведьмак",
        # one artist, no album artist: one partition group, accepted as "Ведьмак" and converted on its own.
        files=[('Unsorted/Ведьмак/%02d.mp3'%n,{'album':'Ведьмак','artist':'Анджей Сапковский','track':str(n),'title':title})
               for n,title in enumerate(('Последнее желание 1','Последнее желание 2','Меч предназначения 1','Меч предназначения 2'),1)]
        built=groups.build(self.rows(files))
        self.assertEqual(len(built),1,list(built));group=next(iter(built.values()))
        self.assertTrue(group.get('source_partition_uncertain'),'held: never converted on its own')
        self.assertEqual(group['album_works'],[{'name':'Последнее желание','files':2},{'name':'Меч предназначения','files':2}])
        self.assertIn('Source membership uncertain',source_gate(dict(group,id='g',revision=1,fingerprint='f'),{'titles':['Ведьмак'],'author_aliases':['Анджей Сапковский'],'identity_basis':'local_agreement','identity_rule':IDENTITY_VERSION,'policy_version':'standing-17-v1'}))
        import todo_causes
        self.assertEqual(todo_causes.files_cause(group['members'],['Source membership uncertain'],'Ведьмак',works=group['album_works'])['cause'],'works')
        # Positive controls: chapter titles, or one work in parts, are one book with no hold.
        for titles in (('Глава 1','Глава 2','Глава 3','Глава 4'),('Ведьмак 1','Ведьмак 2','Ведьмак 3','Ведьмак 4'),('Последнее желание 1','Последнее желание 2','Последнее желание 3','Последнее желание 4')):
            files=[('Unsorted/Ведьмак/%02d.mp3'%n,{'album':'Ведьмак','artist':'Анджей Сапковский','track':str(n),'title':title}) for n,title in enumerate(titles,1)]
            group=next(iter(groups.build(self.rows(files)).values()))
            self.assertFalse(group.get('source_partition_uncertain'),titles);self.assertFalse(group.get('album_works'),titles)

    # The 77 real file names of «Пастушья корона» (Z:\Audiobooks, one title tag "Пастушья корона ", no album): the part after
    # "Пастушья корона NN"; the other numbers are bare. "64.Глава" has no space and 73/74 end in a space, as on disk.
    PASTUSHYA={'0':'. Пролог. Корона Холмов','00':'. Словарь Нак-мак-фиглов','01':'. Глава 1. Там где ветер','05':'. Глава 2. Голос в темноте',
               '09':'. Глава 3. Мир вверх тармашками','15':'. Глава 4. В добрый путь и добро пожаловать','19':'. Глава 5. Новые времена',
               '24':'. Глава 6. Везде поспеть','27':'. Глава 7. Стихия','30':'. Глава 8. Баронский герб','33':'. Глава 9. Заклинатель коз',
               '35':'. Глава 10. Сокровище','41':'. Глава 11. Город','45':'. Глава 12. Эльф среди фиглов','48':'. Глава 13. Шалости и не только',
               '51':'. Глава 14. Повесть о двух королевах','56':'. Глава 15. Логово бога','60':'. Глава 16. Хохотун Вбоквелл',
               '64':'.Глава 17. Ведьмы спорят','66':'. Глава 18. Пастушья корона','71':'. Глава 19. Мир','73':'. Эпилог. Шёпот холмов ',
               '74':'. Послесловие ','75':'. Бонус'}

    def pastushya(self,extra=()):
        folder='Unsorted/Terry Pratchet/Discworld/Tiffany Aching/Терри Пратчетт - Пастушья корона (Макс Потёмкин)'
        names=['Пастушья корона %s%s'%(n,self.PASTUSHYA.get(n,'')) for n in ['0','00']+['%02d'%n for n in range(1,76)]]+list(extra)
        return [('%s/%s.mp3'%(folder,name),{'title':'Пастушья корона ','artist':'Терри Пратчетт'}) for name in names]

    def test_futaba_m12_the_joined_pratchett_chapters_are_named_from_their_file_names(self):
        # Futaba's 0.22.0 QA, m-12: the 77-file join had 77 chapters all named "Пастушья корона", the one title tag on every
        # file. That tag is the book's shared prefix of every file name; each chapter is named from its file name after it,
        # or, where the name carries only a number, by that number.
        from chapter_plan import names
        members=[{'path':path,'source_track':'','metadata':{'track_title':tags['title'],'tags':tags},'duration':1} for path,tags in self.pastushya()]
        got=names(members)
        self.assertEqual(len(set(got)),77,'one chapter per file')
        self.assertEqual(got[:6],['Пролог. Корона Холмов','Словарь Нак-мак-фиглов','Глава 1. Там где ветер','Track 02','Track 03','Track 04'])
        self.assertIn('Глава 13. Шалости и не только',got);self.assertNotIn('Пастушья корона',[n.strip() for n in got])
        # Controls (test_chapter_preservation): a description repeated on files whose names do not carry it stays, and a
        # book title equal to the album is no chapter name.
        plain=lambda n,title:{'path':'%d.mp3'%n,'source_track':str(n),'metadata':{'track_title':title,'tags':{'album':'Book'}}}
        self.assertEqual(names([plain(1,'Начало'),plain(2,'Начало')]),['Начало','Начало'])
        self.assertEqual(names([plain(1,'Book'),plain(2,'Book')]),['Track 01','Track 02'])

    def test_review_n10_the_real_pratchett_chapter_names_are_one_book(self):
        # Senua's 0.22.0 release review, N10: N4's file-name works check read each chapter name ("Пастушья корона 01. Глава 1.
        # Там где ветер", "Пастушья корона 00. Словарь Нак-мак-фиглов") as a work, so the one live same-title set became 77
        # lone files. Chapter labels and the tag's own title with a number name no other work.
        built=groups.build(self.rows(self.pastushya()))
        self.assertEqual([len(g['members']) for g in built.values()],[77],[s.split('\\')[-1] for s in built])
        self.assertEqual(next(iter(built.values()))['numbered_set']['basis'],'same title tag')
        # Two other works by their file names (no "Пастушья корона NN" start, no chapter label) still refuse the set.
        built=groups.build(self.rows(self.pastushya(extra=('Шляпа, полная неба','Зимних дел мастер'))))
        # Ruling 68 (0.24.0): one folder is never divided; two more works make it a held folder question, never one book.
        self.assertEqual([len(g['members']) for g in built.values()],[79],'one folder, one held question')
        group=next(iter(built.values()));self.assertEqual(group['folder_unit']['kind'],'ask');self.assertTrue(group['source_partition_uncertain'])
        # The tag's own title and a number is a chapter only in a set that shows chapters ("Пастушья корона 02", a "Глава"):
        # two books of a series under one series tag stay two books.
        files=[('Unsorted/Ведьмак/Ведьмак %d. %s.mp3'%(n,name),{'title':'Ведьмак','artist':'Анджей Сапковский'}) for n,name in ((1,'Последнее желание'),(2,'Меч предназначения'))]
        self.assertEqual(len(groups.build(self.rows(files))),2)

    def test_review_n11_chapter_named_title_tags_are_not_several_books(self):
        # Senua's 0.22.0 release review, N11: N6's album works check held albums whose title tags are chapter names, from the
        # live catalog: Мистер Вечный Канун, Schismatrix, Война миров, Книга осенних демонов. None is held now.
        albums={'Мистер Вечный Канун. Уэлихолн':('Глава 1. Дом, милый дом - 1','Глава 1. Дом, милый дом - 2','Глава 2. Когда не все дома',
                                                 'Глава 3. Человек в зеленом - 1','Глава 3. Человек в зеленом - 2'),
                'Схизматрица':('Вступление','Пролог','Часть 1. Бродяжья зона. Глава 01','Часть 1. Бродяжья зона. Глава 01',
                               'Часть 1. Бродяжья зона. Глава 02','Часть 2. Сообщающиеся анархии. Глава 01','Часть 2. Сообщающиеся анархии. Глава 01'),
                'Профессия: инквизитор 7. Война миров':('Пролог','Часть первая. Фрагмент 1','Часть первая. Фрагмент 2','Часть вторая. Фрагмент 1','Часть вторая. Фрагмент 2'),
                'Книга осенних демонов':('Пролог','Глава 1. Клуб абсолютной кредитной карточки_01','Глава 1. Клуб абсолютной кредитной карточки_02',
                                         'Глава 2. Рассказ психотерапевта_01','Глава 2. Рассказ психотерапевта_02')}
        for album,titles in albums.items():
            files=[('Unsorted/%s/%02d.mp3'%(album.replace(':',''),n),{'album':album,'artist':'Чтец','track':str(n),'title':title}) for n,title in enumerate(titles,1)]
            built=groups.build(self.rows(files))
            self.assertEqual(len(built),1,album);group=next(iter(built.values()))
            self.assertFalse(group.get('source_partition_uncertain'),album);self.assertFalse(group.get('album_works'),album)
        # Positive controls: two works with no chapter label are still held, numbered with the album's own title too, or with
        # book words ("Книга 1. …" is a book, not a chapter).
        for titles in (('Ведьмак 1. Последнее желание 1','Ведьмак 1. Последнее желание 2','Ведьмак 2. Меч предназначения 1','Ведьмак 2. Меч предназначения 2'),
                       ('Книга 1. Последнее желание 1','Книга 1. Последнее желание 2','Книга 2. Меч предназначения 1','Книга 2. Меч предназначения 2')):
            files=[('Unsorted/Ведьмак/%02d.mp3'%n,{'album':'Ведьмак','artist':'Анджей Сапковский','track':str(n),'title':title}) for n,title in enumerate(titles,1)]
            group=next(iter(groups.build(self.rows(files)).values()))
            self.assertTrue(group.get('source_partition_uncertain'),titles);self.assertEqual(len(group['album_works']),2,titles)

    def test_review_n10_n11_chapter_labels_name_no_work_book_words_do(self):
        works=local_identity.chapter_works
        for title in ('Глава 1. Там где ветер','Глава седьмая. Город','Chapter 3: The Wind','Часть 1. Бродяжья зона. Глава 01','Часть вторая. Фрагмент 2',
                      'Part II. The Return','Пролог. Корона Холмов','Эпилог. Шёпот холмов','01. Глава 2. Голос в темноте'):
            self.assertEqual(works([title]),[''],title)
        for title in ('Книга 2. Меч предназначения','Том 3. Адамант Хенны','Эпизод 4. Кровь','Тени Замбулы. Глава 1','Последнее желание 2','Глазами клоуна'):
            self.assertNotEqual(works([title]),[''],title)
        # The own title and a number: a chapter when the set shows chapters, else whatever the rest names.
        self.assertEqual(works(['Пастушья корона 00. Словарь Нак-мак-фиглов','Пастушья корона 02'],'Пастушья корона '),['',''])
        self.assertEqual(works(['Пастушья корона 00. Словарь Нак-мак-фиглов','Пастушья корона 01. Глава 1. Там где ветер'],'Пастушья корона'),['',''])
        self.assertEqual(len(set(works(['Ведьмак 1. Последнее желание','Ведьмак 2. Меч предназначения'],'Ведьмак'))-{''}),2)

    def witcher(self,disc_titles=(('Последнее желание','Чтец Один'),('Меч предназначения','Чтец Два'))):
        files=[]
        for disc,(work,reader) in enumerate(disc_titles,1):
            for n in (1,2):
                files.append(('Unsorted/Ведьмак/%d-%d.mp3'%(disc,n),{'album':'Ведьмак','artist':'Анджей Сапковский','album_artist':reader,'disc':str(disc),'track':str(n),'title':'%s %d'%(work,n)}))
        return files

    def test_the_grouping_line_names_no_person_or_ruling(self):
        # Judy's part-sets copy check, must-fix 1: the details panel prints this line; no names, dates or rule numbers.
        sets=[('Unsorted/Нисио Исин - Monogatari Series - Сто историй/%d Хякумоногатари - %s.mp3'%(n,t),{}) for n,t in ((1,'Предисловие переводчика'),(2,'Истории 1-17'))]
        joined=[('Unsorted/Тихий ветер/%02d.mp3'%n,{'album':'Тихий ветер','artist':a,'track':str(n)}) for n,a in ((1,'Иван Петров'),(2,'Петров Иван'))]
        parts=[('Нарния/3.%d. Хроники Нарнии. Конь и его мальчик.m4b'%n,{'album':'Конь и его мальчик','artist':'Клайв Льюис','title':'3.%d. Хроники Нарнии. Конь и его мальчик'%n,'track':'%d/2'%n}) for n in (1,2)]
        lines=[next(iter(groups.build(self.rows(files)).values()))['grouping'] for files in (sets,joined)]
        from test_split_books import row as catalog_row
        lines.append(next(iter(groups.build([catalog_row(p,t) for p,t in parts]).values()))['grouping'])
        self.assertEqual(lines,['One book: files of one folder with the shared start of the numbered file names.','One book: files of one folder with the same album and one author.',
                                'Parts of one folder that share their album and artist. Their chapters decide whether they are one book.'])
        # A group stored by an earlier build shows the same wording.
        for old,new in (('One book (Sergei 2026-10-24, ruling 19): files of one folder with the same album and one author (the parts of one book)',lines[1]),
                        ('One book (Sergei 2026-10-24, parts stay together): files of one folder with the same title tag','One book: files of one folder with the same title tag.'),
                        ('Parts of one folder that share their album and artist: their chapters decide whether they are one book (ruling 19)',lines[2]),
                        ('Per-file embedded/filename identity partition; recording remains unverified','Per-file embedded/filename identity partition; recording remains unverified')):
            self.assertEqual(groups.shown_grouping(old),new)

    def test_g3_one_album_whose_title_tags_name_two_books_is_held_as_files_unclear(self):
        built=groups.build(self.rows(self.witcher()))
        self.assertEqual(len(built),1,list(built));group=next(iter(built.values()))
        self.assertTrue(group['source_partition_uncertain'],'held: never converted on its own')
        self.assertEqual(group['joined_parts']['works'],[{'name':'Последнее желание','files':2},{'name':'Меч предназначения','files':2}])
        self.assertIn('Source membership uncertain',source_gate(dict(group,id='g',revision=1,fingerprint='f'),{'titles':['Ведьмак'],'author_aliases':['Анджей Сапковский'],'identity_basis':'local_agreement','identity_rule':IDENTITY_VERSION,'policy_version':'standing-17-v1'}))

    def test_g3_chapter_titles_and_one_work_in_parts_still_join_without_a_hold(self):
        files=[('Unsorted/Плюшевая голова/%d.mp3'%n,dict({'album':'Плюшевая голова','artist':'Влад Райбер','album_artist':'Михаил Прокопов','track':str(n),'title':title},
               **({'album_artist':'Михаил Прокопов, Анна Прокопова'} if n==4 else {}))) for n,title in enumerate(('Цапка','Призрак пустого вагона','Нектохеты ч.1','Нектохеты ч.2'),1)]
        built=groups.build(self.rows(files))
        self.assertEqual(len(built),1,list(built));group=next(iter(built.values()))
        self.assertFalse(group.get('source_partition_uncertain'));self.assertEqual(group['joined_parts'].get('works',[]),[])
        # One book per disc, each disc a single file with its own title: still two works.
        built=groups.build(self.rows([(p,t) for p,t in self.witcher() if p.endswith('-1.mp3')]))
        self.assertTrue(next(iter(built.values()))['source_partition_uncertain'])


class QuestionsOpenTheEditor(unittest.TestCase):
    def test_a_held_question_is_a_typed_metadata_hold(self):
        import manual_metadata
        for reason,fields in (('Title or author missing',['title','canonical_author']),('Author unclear',['canonical_author'])):
            with self.subTest(reason=reason):
                holds=manual_metadata.holds({'state':'Held','reasons':[reason],'metadata_holds':[]})
                self.assertEqual(holds,[{'cause':'identity_uncertain','fields':fields,'reason':reason}])


class SourceGateForOneSourceIdentity(unittest.TestCase):
    def test_a_reader_named_in_the_file_name_no_longer_disagrees(self):
        row=book(member('Brandon Sanderson/Брендон Сандерсон - Ритм войны (Дружинин Степан).m4b',album='Ритм войны',author='Степан Дружинин'))
        work={'titles':['Ритм войны'],'author_aliases':['Брендон Сандерсон'],'identity_basis':'local_agreement','identity_rule':IDENTITY_VERSION,'policy_version':'standing-17-v1'}
        self.assertEqual(source_gate(row,work),[])
        self.assertIn('Sources disagree on the title or author',source_gate(row,dict(work,identity_rule=None)))




def setUpModule():
    # Ruling 29 (0.22.2) has its own tests; these fixtures predate it (tests/original_title_fixture.py).
    global _no_original_title_wait
    from original_title_fixture import no_wait
    _no_original_title_wait = no_wait()


def tearDownModule():
    _no_original_title_wait.stop()


if __name__=='__main__':unittest.main()
