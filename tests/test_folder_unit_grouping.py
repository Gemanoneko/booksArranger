"""0.24.0 (POST-023, rulings 68, 71a, 71b): one source folder is one book; mis-encoded tags read repaired; narrator, author
prefix and quoted titles in identity; the ruling-39 lookup for Tolkien. Fixtures only: no file, no network."""
import json,threading,unittest
from pathlib import Path
from types import SimpleNamespace

import folder_unit
import groups
import local_identity
import tag_text
import public_research
from public_research import PublicResearch,edition_volume,_local_latin
from source_identity import source_gate

ROOT='Z:\\Audiobooks'


def rows(files,start=0):
    found=[]
    for index,(relative,tags) in enumerate(files,start):
        path=ROOT+'\\'+relative.replace('/','\\')
        metadata={'tags':tags}
        if 'duration' in tags:metadata={'tags':{k:v for k,v in tags.items() if k!='duration'},'probe':{'format':{'duration':tags['duration']}}}
        found.append({'root':ROOT,'path':path,'size':100+index,'modified':1000+index,'kind':'audiobook','metadata':json.dumps(metadata,ensure_ascii=False),'error':'','missing':0})
    return found


def sizes(built):
    return sorted(len(g['members']) for g in built.values())


LYONS='Unsorted/WH40K/Стив Лайонс - Криг + рассказы (Casper Valter)'


def lyons():
    stories=('Брошенный умирать','Исход','Сильные среди нас','Среди мертвецов')
    files=[('%s/%02d. Криг.mp3'%(LYONS,n),{'album':'Криг','artist':'Стив Лайонс','track':'%02d/38'%n}) for n in range(1,35)]
    files+=[('%s/%02d. %s.mp3'%(LYONS,n,name),{'album':name,'artist':'Стив Лайонс','track':'%02d/38'%n}) for n,name in zip(range(35,39),stories)]
    return files


class FolderIsOneBook(unittest.TestCase):
    def test_lyons_novel_plus_stories_is_one_book_with_its_stories_listed(self):
        built=groups.build(rows(lyons()))
        self.assertEqual(sizes(built),[38],list(built))
        group=next(iter(built.values()))
        self.assertEqual(group['folder_unit']['kind'],'one');self.assertFalse(group.get('source_partition_uncertain'))
        contents=folder_unit.contents(group['members'])
        self.assertEqual([s['title'] for s in contents['stories']],['Брошенный умирать','Исход','Сильные среди нас','Среди мертвецов'])
        self.assertEqual(contents['other_authors'],0)
        work={'policy_version':'standing-17-v1','titles':['Криг'],'author_aliases':['Стив Лайонс','Лайонс Стив'],'identity_basis':'local_agreement','identity_rule':'local-one-v5'}
        self.assertNotIn('Source membership uncertain',source_gate(group,work))
        self.assertNotIn('Mixed recordings in this group',source_gate(group,work))
        record=local_identity.identify(dict(group,id='g',revision=1,fingerprint='f',source_root=ROOT),ROOT,[],())
        self.assertEqual(record['fields']['title']['value'],'Криг')

    def test_positive_control_two_folders_stay_two_books(self):
        files=lyons();files=[(path.replace(LYONS,LYONS+' 2') if n>=34 else path,tags) for n,(path,tags) in enumerate(files)]
        self.assertEqual(sizes(groups.build(rows(files))),[4,34])

    def test_wolfe_two_album_halves_numbered_by_their_names_are_one_book(self):
        folder='Unsorted/Джин Вулф - Меч и Цитадель'
        files=[('%s/03-%02d Меч ликтора.mp3'%(folder,n),{'album':'Меч и Цитадель - Меч ликтора','artist':'Джин Вулф','disc':'03','track':'%02d'%n}) for n in range(1,39)]
        files+=[('%s/04-%02d Цитадель Автарха.mp3'%(folder,n),{'album':'Меч и Цитадель - Цитадель Автарха','artist':'Джин Вулф','disc':'04','track':'%02d'%n}) for n in range(39,79)]
        built=groups.build(rows(files));self.assertEqual(sizes(built),[78])
        group=next(iter(built.values()));self.assertEqual(group['folder_unit']['basis'],'the file names number the whole folder')
        work={'policy_version':'standing-17-v1','titles':['Меч и Цитадель'],'author_aliases':['Джин Вулф'],'identity_basis':'local_agreement','identity_rule':'local-one-v5'}
        self.assertNotIn('Playback order uncertain',source_gate(group,work))

    def test_abnett_numbered_parts_are_one_book(self):
        folder='Unsorted/WH40K/Дэн Абнетт - Первый и Единственный'
        names=('Часть Первая - Нубилийский Пролив','Часть Вторая - Город','Часть Третья - Ночь','Часть Четвертая - Пирит','Часть Пятая - Эмпирей',
               'Часть Пятая - Эмпирей 2','Часть Пятая - Эмпирей 3','Часть Шестая - Финал','Часть Шестая - Финал 2','Часть Шестая - Финал 3')
        files=[('%s/%02d_%s.mp3'%(folder,n,name),{'artist':'Дэн Абнетт «Первый и Единственный»'}) for n,name in enumerate(names,1)]
        built=groups.build(rows(files));self.assertEqual(sizes(built),[10])
        record=local_identity.identify(dict(next(iter(built.values())),id='g',revision=1,fingerprint='f',source_root=ROOT),ROOT,[],())
        self.assertEqual(record['fields']['title']['value'],'Первый и Единственный','POST-023-02: the quoted title in the artist tag')

    def test_pratchett_mis_encoded_subset_is_read_repaired_and_one_book(self):
        folder='Unsorted/Terry Pratchet/Т. Пратчетт. Шляпа полная небес .(чит Капитан Абр и Nelly)'
        readable={'album':'исп. Капитан Абр и Nelly','artist':'Терри Пратчетт. Шляпа , полная небес'}
        garbled={'album':'èñï. Êàïèòàí Àáð è Nelly','artist':'Òåððè Ïðàò÷åòò. Øëÿïà , ïîëíàÿ íåáåñ'}
        files=[('%s/%03d-01.MP3'%(folder,n),dict(garbled if n in (4,5,6,8,17) else readable)) for n in range(1,21)]
        built=groups.build(rows(files));self.assertEqual(sizes(built),[20],list(built))
        group=next(iter(built.values()))
        self.assertNotIn('è',group['title_clue']);self.assertTrue(all('Ò' not in a for a in group['artists']))
        record=local_identity.identify(dict(group,id='g',revision=1,fingerprint='f',source_root=ROOT),ROOT,[],())
        self.assertEqual(record['fields']['title']['value'],'Шляпа полная небес',record['fields']['title'])
        self.assertTrue(any(i['why']=='names the reader, not the book' for i in record['ignored']))

    def test_stroud_novel_with_its_glossary_is_one_book(self):
        folder='Unsorted/Джонатан Страуд - Кричащая лестница'
        files=[('%s/%02d.mp3'%(folder,n),{'album':'Кричащая лестница','artist':'Джонатан Страуд','track':str(n)}) for n in range(1,27)]
        files.append(('%s/Словарь.mp3'%folder,{'album':'Словарь','artist':'Джонатан Страуд'}))
        built=groups.build(rows(files));self.assertEqual(sizes(built),[27])
        self.assertEqual(next(iter(built.values()))['folder_unit']['basis'],'one book with a few extra files')

    def test_separately_tagged_novels_of_one_author_stay_one_book_each_71b(self):
        folder='OLD_Audiobooks/Клайв Стейплз Льюис - Космическая трилогия'
        files=[]
        for year,book,count in ((1938,'Книга 1. За пределы безмолвной планеты',4),(1943,'Книга 2. Переландра',3),(1945,'Книга 3. Мерзейшая мощь',3)):
            files+=[('%s/%d_%02d.mp3'%(folder,year,n),{'album':'Космическая трилогия. '+book,'artist':'Олег Исаев'}) for n in range(1,count+1)]
        self.assertEqual(sizes(groups.build(rows(files))),[3,3,4])

    def test_whole_books_one_per_file_stay_separate_71a(self):
        files=[('Unsorted/Warcraft/%s.mp3'%name,{'album':name,'artist':author,'duration':str(9*3600)}) for name,author in (('Гробница','Кристи Голден'),('Восход Орды','Кристи Голден'))]
        self.assertEqual(sizes(groups.build(rows(files))),[1,1])
        # Positive control: the same two short files are stories of one folder, asked.
        files=[(path,dict(tags,duration='1800')) for path,tags in files]
        built=groups.build(rows(files));self.assertEqual(sizes(built),[2]);self.assertEqual(next(iter(built.values()))['folder_unit']['kind'],'ask')

    def test_whole_m4b_folders_keep_one_book_per_file(self):
        files=[('Сборники/Глубина/Глубина %d.m4b'%n,{'album':'Глубина %d'%n,'artist':'Сборник'}) for n in (1,2,3)]
        self.assertEqual(sizes(groups.build(rows(files))),[1,1,1])

    def test_ambiguous_folder_is_one_held_question_listing_its_books(self):
        files=[('Unsorted/Разное/%s.mp3'%name,{'album':name,'artist':'Автор Один'}) for name in ('Альфа','Бета')]
        built=groups.build(rows(files));self.assertEqual(sizes(built),[2])
        group=next(iter(built.values()))
        self.assertEqual(group['folder_unit']['kind'],'ask');self.assertTrue(group['source_partition_uncertain'])
        self.assertEqual([b['name'] for b in group['folder_unit']['books']],['Альфа','Бета'])
        self.assertIn('Source membership uncertain',source_gate(group,{'policy_version':'standing-17-v1','titles':['Альфа'],'author_aliases':[]}))

    def test_kept_separate_answer_keeps_the_books_apart(self):
        files=rows([('Unsorted/Разное/%s.mp3'%name,{'album':name,'artist':'Автор Один'}) for name in ('Альфа','Бета')])
        self.assertEqual(sizes(groups.build(files,kept=frozenset(r['path'] for r in files))),[1,1])

    def test_partly_bound_folder_holds_the_rest_and_never_joins_the_bound_book(self):
        files=rows(lyons())
        bound=groups._legacy_build([files[34]]);old=next(iter(bound.values()));old['scope']='bound-story';old['title_clue']='Брошенный умирать'
        built=groups.build(files[:34]+files[35:]+[files[34]],protected={'bound-story':old})
        self.assertIs(built['bound-story'],old,'the bound book is untouched')
        rest=[g for scope,g in built.items() if scope!='bound-story']
        self.assertEqual([len(g['members']) for g in rest],[37])
        self.assertEqual(rest[0]['folder_unit']['kind'],'remainder');self.assertTrue(rest[0]['source_partition_uncertain'])
        self.assertTrue(any('«Брошенный умирать»' in c for c in rest[0]['conflicts']))

    def test_named_anthology_volume_claims_are_untouched(self):
        import anthology_volumes
        folder='Unsorted/'+anthology_volumes.STORY_FOLDER+'/Сборник'
        files=rows([('%s/%s.mp3'%(folder,name),{'album':'','artist':'home2'}) for name in ('Бритва','Сепсис')])
        built=groups.build(files)
        self.assertTrue(all(g.get('anthology_volume') or g.get('anthology_ownership_conflict') for g in built.values()))
        self.assertFalse(any(g.get('folder_unit') for g in built.values()))


class Numbers(unittest.TestCase):
    def member(self,name,**tags):
        return {'path':'x\\'+name,'filename':name,'metadata':{'tags':tags}}

    def test_names_skips_are_printed_as_the_names_show_them(self):
        found=folder_unit.numbers([self.member('%03d-01.MP3'%n) for n in (4,5,6,8,17)])
        self.assertEqual((found['source'],found['first'],found['last'],found['skipped']),('names','004','017',['007','009-016']))

    def test_contiguous_from_one_prints_nothing(self):
        self.assertIsNone(folder_unit.numbers([self.member('%02d.mp3'%n) for n in range(1,6)]))

    def test_one_disc_that_is_not_disc_one_prints_disc_and_track(self):
        # Wolfe «Солнце и Замок»: every file disc 05, tracks 1-70 (71e: the disc numbers the novel, not a missing disc).
        found=folder_unit.numbers([self.member('Глава %s.mp3'%name,disc='05',track=str(n)) for n,name in ((1,'а'),(2,'б'),(3,'в'))])
        self.assertEqual((found['source'],found['first'],found['last'],found['skipped']),('tags','05-01','05-03',[]))

    def test_late_start_without_skips(self):
        found=folder_unit.numbers([self.member('%02d_Часть.mp3'%n) for n in (5,6,7)])
        self.assertEqual((found['first'],found['last'],found['skipped']),('05','07',[]))


class TagRepair(unittest.TestCase):
    def test_cp1251_read_as_latin1_is_repaired(self):
        self.assertEqual(tag_text.repair('Òåððè Ïðàò÷åòò'),('Терри Пратчетт',True))
        self.assertEqual(tag_text.repair('èñï. Êàïèòàí Àáð è Nelly'),('исп. Капитан Абр и Nelly',True))

    def test_readable_and_lost_text_is_untouched(self):
        for value in ('Терри Пратчетт','Ángel Béjar','Émile Zola','Ãîëîâ \ufffd','abc'):
            with self.subTest(value=value):self.assertEqual(tag_text.repair(value),(value,False))

    def test_tags_reads_repaired_values_and_keeps_numbers(self):
        self.assertEqual(tag_text.tags({'tags':{'ALBUM':'Øëÿïà','track':'3/7'}}),{'album':'Шляпа','track':'3/7'})


class Identity(unittest.TestCase):
    def test_gene_wolfe_is_a_foreign_given_name_and_files_surname_first(self):
        self.assertTrue(local_identity.foreign_given('Джин Вулф'))
        self.assertEqual(local_identity.surname_first('Джин Вулф')[0],'Вулф Джин')

    def test_unknown_given_names_and_their_controls(self):
        self.assertTrue(local_identity.unknown_given('Кавабата Ясунарь'))
        for name in ('Иван Петров','Наиль Измайлов','Петров Иван Сергеевич','Разные авторы','Ильф Илья, Петров Евгений','Джин Вулф','Без автора'):
            with self.subTest(name=name):self.assertFalse(local_identity.unknown_given(name))

    def test_dzh_initial_pairs_with_j(self):
        self.assertTrue(local_identity.compare_names('Толкин Джон Рональд Руэл','J. R. R. Tolkien'))
        self.assertTrue(local_identity.compare_names('Дж. Р.Р. Толкин','Джон Рональд Руэл Толкин'))
        self.assertIsNone(local_identity.compare_names('Д. Смит','John Smith'),'Д is D, never J')

    def test_author_prefix_needs_a_person_of_the_book(self):
        members=[{'metadata':{'tags':{'artist':'Терри Пратчетт. Шляпа , полная небес'}}}]
        self.assertEqual(local_identity.author_prefix('Т. Пратчетт. Шляпа полная небес',members,[]),('Т. Пратчетт','Шляпа полная небес'))
        self.assertIsNone(local_identity.author_prefix('Firefly. Великолепная девятка',[],['Firefly']))
        self.assertIsNone(local_identity.author_prefix('Т. Пратчетт. Шляпа полная небес',[],[]),'no credit names that person')

    def test_series_mentioned_in_brackets_is_proposed_and_asked_never_filed_by_itself(self):
        # Rulings 51, 52, 71e: «Солнце и Замок (Книга Нового Солнца #3)»: the edition numbers its volumes 1/2/3.
        members=[{'path':ROOT+'\\Unsorted\\Солнце и Замок\\%02d.mp3'%n,'filename':'%02d.mp3'%n,'metadata':{'tags':{'album':'Солнце и Замок (Книга Нового Солнца #3)','artist':'Джин Вулф','track':str(n)}}} for n in (1,2)]
        record=local_identity.identify({'id':'g','revision':1,'fingerprint':'f','source_root':ROOT,'members':members},ROOT,[],())
        self.assertEqual((record['fields']['title']['value'],record['fields']['series']['value'],record['fields']['number']['value']),('Солнце и Замок','Книга Нового Солнца','3'))
        self.assertTrue(record['series_unconfirmed'],'asked with Series and Number filled in')

    def test_narrator_marker_without_a_full_stop_in_brackets(self):
        self.assertEqual(local_identity.narrator_names(['Шляпа полная небес .(чит Капитан Абр и Nelly)']),['Капитан Абр и Nelly'])
        self.assertEqual(local_identity.clean_title('Т. Пратчетт. Шляпа полная небес .(чит Капитан Абр и Nelly)'),'Т. Пратчетт. Шляпа полная небес')


class FakeClient:
    """Answers by URL fragment; records every request. No network."""
    def __init__(self,answers):self.answers=answers;self.calls=[];self.database='unused.sqlite'
    def json(self,url,stop,budget):
        self.calls.append(url)
        for key,value in self.answers.items():
            if key in url:return value
        return {'search':[]} if 'wikidata' in url else []
    def read(self,url,stop,budget):
        self.calls.append(url);return ''


TOLKIEN={'id':'Q892','labels':{'en':{'value':'J. R. R. Tolkien'},'ru':{'value':'Джон Рональд Руэл Толкин'}},'aliases':{},
         'claims':{'P31':[{'mainsnak':{'property':'P31','snaktype':'value','datavalue':{'value':{'id':'Q5'}}}}],
                   'P1412':[{'mainsnak':{'property':'P1412','snaktype':'value','datavalue':{'value':{'id':'Q1860'}}}}]}}


class TolkienLookup(unittest.TestCase):
    """2026-10-29: «Джон Рональд Руэл Толкин» asked "no English spelling found" for Хранители / Две твердыни / Возвращение
    государя. FantLab and Wikidata were asked only for «Хранители. Летопись первая» (the edition's volume title, empty
    answers in the live cache) and Goodreads could not pair "J.R.R." with «Джон Рональд Руэл»."""
    def research(self,client):
        research=PublicResearch(SimpleNamespace(database='unused.sqlite'),leads=[])
        research.client=client;research._gap_receipt=lambda *a,**k:None
        return research

    def test_edition_volume_titles(self):
        self.assertEqual(edition_volume('Хранители. Летопись первая'),('Хранители',1))
        self.assertEqual(edition_volume('Возвращение государя. Летопись третья'),('Возвращение государя',3))
        self.assertEqual(edition_volume('Книга 2. Меч ликтора'),('Меч ликтора',2))
        self.assertEqual(edition_volume('Мастер и Маргарита'),('Мастер и Маргарита',None))

    def test_the_book_folder_in_latin_letters_names_the_author_without_a_request(self):
        found=_local_latin('Толкин Джон Рональд Руэл',['Хранители. Летопись первая','Джон Рональд Руэл Толкин','J. R. R. Tolkien'],[])
        self.assertEqual((found['state'],found['name']),('found','J. R. R. Tolkien'))
        self.assertEqual(public_research._latin_surname_first(found['name'],'Толкин Джон Рональд Руэл'),'Tolkien J. R. R.')
        client=FakeClient({});research=self.research(client)
        self.assertEqual(research._author_latin('Хранители. Летопись первая','Толкин Джон Рональд Руэл',threading.Event(),{'remaining':12},{},
                                                folders=['J. R. R. Tolkien'])['name'],'J. R. R. Tolkien')
        self.assertEqual(client.calls,[],'no request when the library already holds the spelling')

    def test_local_spelling_never_settles_a_russian_or_unknown_first_name(self):
        self.assertIsNone(_local_latin('Лукьяненко Сергей',['Sergei Lukyanenko'],[]))
        self.assertIsNone(_local_latin('Толкин Джон Рональд Руэл',['Christopher Tolkien','Tolkien Estate'],[]),'another person of the surname')
        self.assertEqual(_local_latin('Толкин Джон Рональд Руэл',[],['Tolkien J. R. R.','Pratchett Terry'])['name'],'Tolkien J. R. R.','an author the library files')

    def test_wikidata_person_record_gives_the_english_name(self):
        client=FakeClient({'wbsearchentities':{'search':[{'id':'Q892'}]},'wbgetentities':{'entities':{'Q892':TOLKIEN}}})
        found=self.research(client)._author_wikidata('Толкин Джон Рональд Руэл',threading.Event(),{'remaining':12},{})
        self.assertEqual((found['state'],found['name']),('found','J. R. R. Tolkien'))
        self.assertIn('search=%D0%94%D0%B6%D0%BE%D0%BD',client.calls[0],'searched first name first')

    def test_wikidata_person_writing_in_russian_keeps_cyrillic_and_unknown_language_asks(self):
        russian=json.loads(json.dumps(TOLKIEN));russian['claims']['P1412']=[{'mainsnak':{'property':'P1412','snaktype':'value','datavalue':{'value':{'id':'Q7737'}}}}]
        client=FakeClient({'wbsearchentities':{'search':[{'id':'Q892'}]},'wbgetentities':{'entities':{'Q892':russian}}})
        self.assertEqual(self.research(client)._author_wikidata('Толкин Джон Рональд Руэл',threading.Event(),{'remaining':12},{})['state'],'russian')
        silent=json.loads(json.dumps(TOLKIEN));silent['claims'].pop('P1412')
        client=FakeClient({'wbsearchentities':{'search':[{'id':'Q892'}]},'wbgetentities':{'entities':{'Q892':silent}}})
        self.assertIsNone(self.research(client)._author_wikidata('Толкин Джон Рональд Руэл',threading.Event(),{'remaining':12},{}))

    def test_another_person_with_the_surname_is_never_taken(self):
        other=json.loads(json.dumps(TOLKIEN));other['labels']['ru']['value']='Кристофер Толкин'
        client=FakeClient({'wbsearchentities':{'search':[{'id':'Q892'}]},'wbgetentities':{'entities':{'Q892':other}}})
        self.assertIsNone(self.research(client)._author_wikidata('Толкин Джон Рональд Руэл',threading.Event(),{'remaining':12},{}))

    def test_volume_title_is_also_looked_up_by_its_book_title(self):
        hit=[{'work_id':123,'name':'The Fellowship of the Ring','rusname':'Братство Кольца','altname':'Хранители; Содружество Кольца',
              'all_autor_name':'J.R.R. Tolkien','all_autor_rusname':'Джон Рональд Руэл Толкин'}]
        work={'work_id':123,'work_type_name':'Роман','authors':[{'type':'autor','name':'Джон Рональд Руэл Толкин','name_orig':'John Ronald Reuel Tolkien'}],
              'lang_code':'en','work_name_orig':'The Fellowship of the Ring','work_name':'Братство Кольца'}
        client=FakeClient({'search-works?q=%D0%A5%D1%80%D0%B0%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D0%B8&':hit,'/work/123/extended':work})
        found=self.research(client)._author_latin('Хранители. Летопись первая','Толкин Джон Рональд Руэл',threading.Event(),{'remaining':12},{})
        self.assertEqual((found['state'],found['name'],found['title']),('found','John Ronald Reuel Tolkien','The Fellowship of the Ring'))
        self.assertTrue(any('%D0%9B%D0%B5%D1%82%D0%BE%D0%BF%D0%B8%D1%81%D1%8C' in url for url in client.calls),'the full title is asked first')


if __name__=='__main__':
    unittest.main()
