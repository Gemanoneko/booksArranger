"""Sergei's lasting author rules (ruling 12, 2026-10-24) and his answers to the new-author screen
(Team/Docs/BooksArranger_AuthorRulings_2026-10-24.md). Private catalog fixtures only; no network, no library."""
import contextlib,json,sqlite3,tempfile,threading,unittest
from pathlib import Path
import author_rules
import local_identity
from local_identity import identify
from public_research import PublicResearch
from test_identity_v5 import AREA,ROOT,member,book,Offline,Catalog,reader_elsewhere


class RulesCatalog(Catalog):
    """The identity fixture catalog plus Sergei's seeded rules (and any extra rows)."""
    def __init__(self,test,rows,library=(),extra=(),jobs=()):
        super().__init__(test,rows,library)
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            author_rules.seed(db)
            for kind,credit,target,scope in extra:author_rules.append(db,kind,credit,target=target,scope=scope,actor='user',source='test')
            if jobs:
                db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT,updated TEXT)')
                for index,author in enumerate(jobs):db.execute('INSERT INTO audio_jobs VALUES(?,?,?)',('job-%d'%index,json.dumps({'metadata':{'author':author}},ensure_ascii=False),'t%d'%index))
            db.commit()
        self.rules=author_rules.load(self.database)


class TableTests(unittest.TestCase):
    def database(self):
        temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(temp.cleanup);return Path(temp.name)/'catalog.sqlite3'

    def test_rules_are_append_only_and_the_newest_answer_wins(self):
        database=self.database()
        with contextlib.closing(sqlite3.connect(database)) as db:
            author_rules.setup(db);author_rules.append(db,'not_author','Иван Петров',actor='user',source='test');db.commit()
            for statement in ("UPDATE author_rules SET kind='keep'",'DELETE FROM author_rules'):
                with self.subTest(statement=statement),self.assertRaisesRegex(sqlite3.IntegrityError,'append-only'):db.execute(statement)
            author_rules.append(db,'keep','Петров Иван',actor='user',source='test');db.commit()
        rules=author_rules.load(database)
        self.assertTrue(rules.keep('иван ПЕТРОВ'));self.assertFalse(rules.not_author('Иван Петров'),'a changed mind is a newer row')

    def test_seeds_are_stored_once_with_sergeis_source(self):
        database=self.database()
        with contextlib.closing(sqlite3.connect(database)) as db:
            author_rules.seed(db);author_rules.seed(db);db.commit()
            rows=db.execute('SELECT source,actor,count(*) FROM author_rules GROUP BY source,actor').fetchall()
        self.assertEqual(rows,[('Sergei 2026-10-24','user',len(author_rules.SEEDS))])

    def test_a_credit_matches_in_any_word_order_case_and_yo_spelling(self):
        rules=author_rules.Rules([{'rule_id':'r','kind':'not_author','credit_key':author_rules.key('Потёмкин Макс'),'credit_as_seen':'Потёмкин Макс','target':'','scope':'','options':'{}','saved_utc':'1'}])
        for spelling in ('Макс Потемкин','МАКС ПОТЁМКИН','Потёмкин, Макс'):
            with self.subTest(spelling=spelling):self.assertTrue(rules.not_author(spelling))
        self.assertFalse(rules.not_author('Макс Фрай'))


class RulesInIdentityTests(unittest.TestCase):
    """Each answer applies to future books too (ruling 12); before 0.22.0 none of them existed."""
    def setUp(self):
        temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(temp.cleanup);database=Path(temp.name)/'c.sqlite3'
        with contextlib.closing(sqlite3.connect(database)) as db:author_rules.seed(db);db.commit()
        self.rules=author_rules.load(database)

    def ident(self,row):return identify(row,ROOT,[],(),None,self.rules)

    def test_a_reader_named_in_a_file_name_gives_way_to_the_folder_author_troitsky(self):
        record=self.ident(book(member('Lovegrove James/Олег Троицкий - Firefly. Великолепная девятка.m4b',album='Firefly. Великолепная девятка')))
        self.assertTrue(record['accepted'],record);self.assertEqual(record['fields']['author']['value'],'Lovegrove James')

    def test_one_t_pratchet_and_the_russian_spelling_file_under_pratchett_terry(self):
        for credit in ('Terry Pratchet','Терри Пратчетт'):
            with self.subTest(credit=credit):
                record=self.ident(book(member('Terry Pratchet/Discworld/Night Watch.m4b',album='Night Watch',artist=credit)))
                self.assertEqual(record['fields']['author']['value'],'Pratchett Terry');self.assertTrue(record['fields']['author']['rule'])

    def test_a_garbled_tag_with_an_answer_is_fixed_and_the_output_carries_the_corrected_author(self):
        record=self.ident(book(member('Война Z 1/001 ВВЕДЕНИЕ.mp3',album='Мировая война Z',artist='Ìàêñ Áðóêñ')))
        self.assertTrue(record['accepted'],record);self.assertEqual(record['fields']['author']['value'],'Brooks Max')

    def test_an_anthology_series_name_is_a_collection(self):
        record=self.ident(book(member('Сборники/Созвездие Льва/Созвездие Льва 2.m4b',album='Созвездие Льва 2',artist='Созвездие Льва')))
        self.assertTrue(record['accepted']);self.assertEqual(record['route']['credit'],'Разные авторы')

    def test_a_folder_named_answer_gives_the_author_grobnica_sargerasa(self):
        record=self.ident(book(member('Unsorted/Warcraft/Гробница Саргераса/ГробницаСаргераса1.mp3')))
        self.assertTrue(record['accepted'],record);self.assertEqual(record['fields']['author']['value'],'Brooks Robert')

    def test_a_kept_reader_is_the_author_only_in_his_own_folder_volkov(self):
        readers=('Роман Волков',)
        kept=identify(book(member('Волков Роман/Легенды школы №4 г. Пензы/Военрук.m4b',album='Военрук',artist='Роман Волков')),ROOT,[],readers,None,self.rules)
        self.assertTrue(kept['accepted'],kept);self.assertEqual(kept['fields']['author']['value'],'Роман Волков')
        elsewhere=identify(book(member('Unsorted/Другая книга.m4b',album='Другая книга',artist='Роман Волков')),ROOT,[],readers,None,self.rules)
        self.assertFalse(elsewhere['accepted']);self.assertEqual(elsewhere['ask']['why'],'reader')

    def test_folk_tales_go_to_collections_unless_a_compiler_is_credited(self):
        tags={'album':'Самые страшные русские народные сказки','artist':'Народный фольклор','composer':'Владимир Князев','description':'Самые страшные русские народные сказки в исполнении Владимира Князева.'}
        record=self.ident(book(member('Сборники/Самые страшные русские народные сказки.m4b',**tags)))
        self.assertTrue(record['accepted']);self.assertEqual(record['route']['credit'],'Разные авторы')
        tags['description']='Русские народные сказки в обработке Алексея Толстого.'
        record=self.ident(book(member('Сборники/Русские сказки.m4b',**dict(tags,album='Русские сказки'))))
        self.assertTrue(record['accepted'],record);self.assertIsNone(record['route']);self.assertEqual(record['fields']['author']['value'],'Алексея Толстого')


class RulesInResearchTests(unittest.TestCase):
    def test_a_rules_target_skips_the_spelling_vote(self):
        # The library's majority spelling is the one-t "Pratchet" (the folder); the rule's target wins.
        row=book(member('Terry Pratchet/Discworld/Snuff.m4b',album='Snuff',artist='Terry Pratchet'))
        result=RulesCatalog(self,[row]).lookup(row)
        self.assertEqual(result['reasons'],[],result.get('reasons'));self.assertEqual(result['review']['canonical_author'],'Pratchett Terry')
        self.assertTrue(result['rules_generation'])

    def test_a_new_name_close_to_an_author_the_library_has_is_asked_once(self):
        row=book(member('Unsorted/Ticktock.m4b',album='Ticktock',artist='Dean Koonts'))
        result=RulesCatalog(self,[row],jobs=('Koontz Dean','Koontz Dean')).lookup(row)
        self.assertEqual(result['reasons'],['Same author?']);ask=result['ask']
        self.assertEqual((ask['kind'],ask['existing'],ask['existing_books'],ask['why']),('same_author','Koontz Dean',2,'near'))
        answered=RulesCatalog(self,[row],extra=[('keep','Dean Koonts','','')],jobs=('Koontz Dean',)).lookup(row)
        self.assertEqual(answered['reasons'],[],'never asked again once answered')

    def test_the_same_full_name_in_the_other_script_files_under_the_folder_the_library_has(self):
        row=book(member('Unsorted/Warcraft/Роберт Брукс - Варкрафт - Смерть с небес/001.mp3',album='Варкрафт - Смерть с небес',artist='Роберт Брукс'))
        result=RulesCatalog(self,[row]).lookup(row)
        self.assertEqual(result['reasons'],[],'the language rule answered it: not a question');self.assertEqual(result['review']['canonical_author'],'Brooks Robert')

    def test_one_letter_variants_and_a_doubled_credit_are_one_person(self):
        record=identify(book(member('Хроники Нарнии/1. Племянник чародея.m4b',album='Племянник чародея',artist='Клайв Стейплз Льюис',album_artist='Клайв Стейплс Льюис')),ROOT,[],(),None,None)
        self.assertTrue(record['accepted'],record)
        record=identify(book(member('Herbert Frank/Dune/Еретики Дюны.m4b',album='Еретики Дюны',artist='Герберт Фрэнк Герберт Фрэнк')),ROOT,[],(),None,None)
        self.assertEqual(record['fields']['author']['value'],'Герберт Фрэнк')

    def test_a_middle_name_written_out_on_one_side_only_joins_the_library_spelling(self):
        self.assertTrue(local_identity.compare_names('Ray Douglas Bradbury','Рэй Брэдбери'),'positive control: the matcher pairs these names')
        row=book(member('Ray Douglas Bradbury/Вино из одуванчиков.m4b',album='Вино из одуванчиков',artist='Рэй Брэдбери'))
        result=RulesCatalog(self,[row]).lookup(row)
        self.assertEqual(result['reasons'],[]);self.assertEqual(result['review']['canonical_author'],'Bradbury Ray Douglas')

    def test_a_clean_new_author_is_not_asked(self):
        row=book(member('Unsorted/Тайна.m4b',album='Тайна',artist='Иван Петров'))
        self.assertEqual(RulesCatalog(self,[row],jobs=('Koontz Dean',)).lookup(row)['reasons'],[])


class RulesChangeResearchAgainTests(unittest.TestCase):
    def test_a_held_book_is_researched_again_when_the_rules_change(self):
        import test_automatic_processing as fixtures
        case=fixtures.AutoTests('test_uncertain_work_is_revisited_until_user_stop');case.setUp();self.addCleanup(case.doCleanups);self.addCleanup(case.tearDown)
        calls=[]
        def lookup(row,*_):calls.append(1);return {'reasons':['Title or author missing'],'sources':[],'ask':{'kind':'title_author'},'rules_generation':generation[0]}
        auto,merge,inv=case.fake_merge(lookup)
        generation=['g1'];auto.research.rules=lambda:type('R',(),{'generation':generation[0]})()
        auto.start();case.wait_auto(auto);auto.start();case.wait_auto(auto);self.assertEqual(len(calls),1)
        generation[0]='g2'
        auto.start();case.wait_auto(auto);self.assertEqual(len(calls),2,'new rules: researched again');auto.close()


if __name__=='__main__':unittest.main()
