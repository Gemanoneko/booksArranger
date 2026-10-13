"""Local-agreement identity, gap-only search and scheduling. Private fixtures only:
no production network, inventory, library or live catalog access."""
import json,tempfile,threading,time,unittest,urllib.error,urllib.parse
from pathlib import Path
from unittest.mock import Mock
import groups
from local_identity import agreement,compare_names,summary,revalidate
from public_research import PublicClient,PublicResearch,ResearchWait,_wait,CHALLENGE_REASON,host_policy,APP_HOST_REQUESTS
from scanner import connect
from standing_metadata import validate_policy
import test_automatic_processing as automatic_fixtures
AREA=automatic_fixtures.AREA

def member(path,**tags):
    return {'path':str(path),'filename':Path(path).name,'metadata':{'tags':tags}}

def candidate(base,files):
    """files: (relative path, tags). Builds one real group from inventory-shaped rows."""
    rows=[]
    for relative,tags in files:
        path=Path(base)/relative;metadata={'title':tags.get('title',''),'artist':tags.get('artist',''),'tags':tags,'probe':{'format':{'duration':'1'}}}
        rows.append({'root':str(path.parent),'path':str(path),'kind':'audiobook','size':10,'modified':10,'metadata':json.dumps(metadata),'error':'','missing':0})
    built=groups.build(rows)
    assert len(built)==1,built
    return next(iter(built.values()))|{'fingerprint':'private-fixture-fingerprint'}

def catalogue(database,root,row):
    """Put a fixture candidate's files into the private catalog, as the scanner would."""
    with connect(database) as db:
        for m in row['members']:
            db.execute("INSERT OR REPLACE INTO files(root,path,size,modified,kind,metadata,error,missing) VALUES(?,?,?,?,'audiobook',?,'',0)",
                (str(root),m['path'],m.get('size',10),m.get('modified',10),json.dumps(m['metadata'])))
    return row

SERGEI=[('Rollins James/Око Бога/01.mp3',{'album':'Око Бога','artist':'Джеймс Роллинс','track':'1/2'}),
        ('Rollins James/Око Бога/02.mp3',{'album':'Око Бога','artist':'Джеймс Роллинс','track':'2/2'})]

class NameMatchingTests(unittest.TestCase):
    def test_same_person_across_scripts_and_word_order(self):
        for latin,cyrillic in (('Rollins James','Джеймс Роллинс'),('Stephen King','Кинг Стивен'),('Isaac Asimov','Айзек Азимов'),('Terry Pratchett','Терри Пратчетт'),
                ('Robert Heinlein','Роберт Хайнлайн'),('Harry Harrison','Гарри Гаррисон'),('Stephen Hawking','Стивен Хокинг'),('Dmitry Glukhovsky','Дмитрий Глуховский'),('George R. R. Martin','Джордж Мартин')):
            with self.subTest(latin=latin):
                match=compare_names(latin,cyrillic);self.assertEqual(match['match'],'cross',match);self.assertIn('transliteration',match['how'])
        self.assertEqual(compare_names('Роллинс Джеймс','Джеймс Роллинс')['match'],'same')
        self.assertEqual(compare_names('Лукьяненко Сергей Васильевич','Сергей Лукьяненко')['match'],'same')
    def test_irregular_english_spelling_is_a_documented_miss(self):
        # "Michael" is pronounced with no vowel where it is written "ae"; such names stay a research case.
        self.assertIsNone(compare_names('Michael Crichton','Майкл Крайтон'))
    def test_different_people_or_translated_names_do_not_match(self):
        for left,right in (('Петров Иван','Иван Петрова'),('Стивен Кинг','Ричард Бахман'),('John Writer','Джон Писатель'),('Rollins James','Rollins Jane'),('Роллинс','Джеймс Ролинсон')):
            with self.subTest(left=left):self.assertIsNone(compare_names(left,right))

class AgreementTests(unittest.TestCase):
    root=r'Z:\Audiobooks'
    def record(self,files,siblings=None):return agreement({'members':[member(self.root+'\\Unsorted\\'+path.replace('/','\\'),**tags) for path,tags in files]},self.root,siblings)
    def test_sergei_example_folder_latin_tag_cyrillic_is_agreement(self):
        local=self.record(SERGEI);self.assertTrue(local['accepted'])
        self.assertEqual((local['fields']['title']['state'],local['fields']['author']['state']),('green','yellow'))
        author=summary(local)['author'];self.assertEqual(author['value'],'Джеймс Роллинс')
        self.assertEqual([s['kind'] for s in author['sources']],['embedded','parent folder']);self.assertIn('word order ignored',author['how'])
        self.assertEqual(local['gaps'],['original_title','series'])
    def test_same_script_structured_folder_and_narrator_credit(self):
        local=self.record([('Роллинс Джеймс - Око Бога (читает Иванов Игорь)/01 Око Бога.mp3',{'album':'Око Бога','artist':'Иванов Игорь','album_artist':'Джеймс Роллинс','narrator':'Иванов Игорь'})])
        self.assertTrue(local['accepted']);self.assertEqual(local['fields']['author']['state'],'green')
        self.assertTrue(any(i['field']=='artist' for i in local['ignored']))
    def test_local_conflicts_are_red_and_hold(self):
        cases={'title':[('Роллинс Джеймс - Песчаный дьявол/01.mp3',{'album':'Око Бога','artist':'Джеймс Роллинс'})],
               'author':[('Иванов Игорь - Око Бога/01.mp3',{'album':'Око Бога','artist':'Джеймс Роллинс'})]}
        for field,files in cases.items():
            with self.subTest(field=field):
                local=self.record(files);self.assertFalse(local['accepted']);self.assertEqual(local['fields'][field]['state'],'red')
        # Author and narrator in two credits, file name naming the narrator, folder the author (James S. A. Corey pattern).
        local=self.record([('James S. A. Corey/9. Падение Левиафана/Кирилл Головин - Падение Левиафана.m4b',{'album':'Падение Левиафана','artist':'Джеймс Кори','album_artist':'Кирилл Головин'})])
        self.assertFalse(local['accepted']);self.assertEqual(local['fields']['author']['state'],'red')
        # Only the author folder names one credit and the other appears nowhere: resolved, the other is recorded.
        local=self.record([('Clive Barker/Абарат/1. Абарат.m4b',{'album':'Абарат','artist':'Баркер Клайв','album_artist':'Булдаков Олег'})])
        self.assertTrue(local['accepted']);self.assertEqual(local['fields']['author']['value'],'Баркер Клайв')
        self.assertTrue(any(i['value']=='Булдаков Олег' for i in local['ignored']))
        # A credit listing two people never matches one of them as a fuller name.
        self.assertIsNone(compare_names('Александр Варго - Пухов Сергей','Варго Александр'))
        local=self.record([('Роллинс Джеймс - Око Бога/0%d.mp3'%i,{'album':'Око Бога','artist':'Джеймс Роллинс','series':'Отряд Сигма','series-part':str(i)}) for i in (1,2)])
        self.assertFalse(local['accepted']);self.assertEqual(local['fields']['number']['state'],'red')
    def test_a_file_beside_others_with_the_same_title_is_not_the_whole_book(self):
        files=[('Dan Brown/Deception Point/Дэн Браун - Точка обмана - 21 - Глава 20.m4b',{'album':'Точка обмана','title':'Глава 20','artist':'Дэн Браун'})]
        sibling={'path':'x','filename':'Дэн Браун - Точка обмана - 22 - Глава 21.m4b','tags':{'album':'Точка обмана','title':'Глава 21'}}
        # Tagged only "Глава 20": a chapter even with no catalogued sibling (Futaba round 2 residual).
        self.assertFalse(self.record(files)['accepted'])
        local=self.record(files,[sibling])
        self.assertFalse(local['accepted']);self.assertEqual(local['fields']['title']['state'],'red');self.assertIn('only part of the book',local['fields']['title']['how'])
        other={'path':'y','filename':'Дэн Браун - Код да Винчи.m4b','tags':{'album':'Код да Винчи'}}
        self.assertFalse(self.record(files,[other])['accepted'])
        whole=[('Dan Brown/Deception Point/Дэн Браун - Точка обмана.m4b',{'album':'Точка обмана','title':'Точка обмана','artist':'Дэн Браун'})]
        self.assertTrue(self.record(whole,[other])['accepted'])
        self.assertFalse(self.record(files,[{'unreadable':True,'path':'','filename':'','tags':{}}])['accepted'])
        part=[('James S. A. Corey/5. Игры Немезиды/5. Игры Немезиды 1.m4b',{'album':'Игры Немезиды 1','artist':'Джеймс Кори'})]
        self.assertFalse(self.record(part)['accepted'])
        self.assertFalse(self.record(part,[{'path':'z','filename':'5. Игры Немезиды 2.m4b','tags':{'album':'Игры Немезиды 2'}}])['accepted'])
    def test_collection_credit_is_not_a_person(self):
        local=self.record([('Сборник - Самая страшная книга 2022/01.mp3',{'album':'Самая страшная книга 2022','artist':'Сборник'})])
        self.assertFalse(local['accepted']);self.assertEqual(local['fields']['author']['state'],'red')
        self.assertIn('names a collection',local['fields']['author']['how'])
    def test_single_source_fields_are_grey_not_agreement(self):
        local=self.record([('CD1/01.mp3',{'album':'Око Бога','artist':'Джеймс Роллинс'})])
        self.assertFalse(local['accepted']);self.assertEqual((local['fields']['title']['state'],local['fields']['author']['state']),('grey','grey'))
    def test_series_needs_tag_and_path_and_number_stays_bound(self):
        local=self.record([('Роллинс Джеймс/Отряд Сигма 03 - Око Бога/01.mp3',{'album':'Око Бога','artist':'Джеймс Роллинс','series':'Отряд Сигма','series-part':'3'})])
        self.assertTrue(local['accepted']);self.assertEqual(local['series'],{'name':'Отряд Сигма','number':'3'});self.assertNotIn('series',local['gaps'])
        local=self.record([('Роллинс Джеймс/Отряд Сигма 04 - Око Бога/01.mp3',{'album':'Око Бога','artist':'Джеймс Роллинс','series':'Отряд Сигма','series-part':'3'})])
        self.assertEqual(local['fields']['number']['state'],'grey');self.assertEqual(local['series'],{})
    def test_surname_only_is_a_required_gap(self):
        local=self.record([('Роллинс - Око Бога/01.mp3',{'album':'Око Бога','artist':'Роллинс'})])
        self.assertTrue(local['accepted']);self.assertIn('author_full',local['gaps'])
        local=self.record([('Rollins James - Око Бога/01.mp3',{'album':'Око Бога','artist':'Роллинс'})])
        self.assertNotIn('author_full',local['gaps']);self.assertEqual(local['fields']['author']['value'],'Rollins James')

class Catalog:
    """Private catalog responses keyed by host; closed hosts raise like a vendor 503."""
    def __init__(self):
        self.calls=[];self.closed=set();self.fantlab=[];self.extended={};self.openlibrary=[]
    def fetch(self,url,*_):
        self.calls.append(url);parsed=urllib.parse.urlsplit(url)
        if parsed.hostname in self.closed:raise urllib.error.HTTPError(url,503,'private fixture',{},None)
        if parsed.hostname=='api.fantlab.ru':
            if parsed.path=='/search-works':return json.dumps(self.fantlab).encode()
            return json.dumps(self.extended[parsed.path]).encode()
        if parsed.hostname=='www.wikidata.org':return json.dumps({'search':[]}).encode()
        if parsed.hostname=='openlibrary.org':return json.dumps({'docs':self.openlibrary}).encode()
        if parsed.hostname in ('www.googleapis.com','itunes.apple.com'):return b'{"items":[],"results":[]}'
        raise AssertionError('Identity research must not run for local agreement: '+url)

class GapSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name);self.now=[100000.0]
        self.catalog=Catalog();self.client=PublicClient(self.base/'catalog.sqlite3',fetch=self.catalog.fetch,clock=lambda:self.now[0])
        class ClockStop:
            def is_set(_self):return False
            def wait(_self,seconds):self.now[0]+=seconds;return False
        self.stop=ClockStop()
    def lookup(self,files):
        self.row=catalogue(self.client.database,self.base,candidate(self.base,files))
        return PublicResearch(self.client,leads=[]).lookup(self.row,str(self.base),self.stop)
    def test_agreeing_local_sources_approve_without_identity_research(self):
        self.catalog.closed={'api.fantlab.ru','www.wikidata.org'}
        result=self.lookup(SERGEI)
        self.assertEqual(result['reasons'],[],result);self.assertEqual(result['metadata_facts']['identity_basis'],'local_agreement')
        self.assertEqual(result['review']['title'],'Око Бога');self.assertEqual(result['review']['canonical_author'],'Rollins James')
        self.assertEqual(result['review']['original_language'],'Unknown');self.assertEqual(result['metadata_facts']['series_state'],'omitted_unknown')
        self.assertEqual(result['metadata_facts']['title_basis'],'local_agreement');self.assertTrue(result['work']['id'].startswith('local:'))
        hosts={urllib.parse.urlsplit(u).hostname for u in self.catalog.calls}
        self.assertLessEqual(hosts,{'api.fantlab.ru','www.wikidata.org'},self.catalog.calls)
        self.assertIsNone(result['wait']);self.assertIn(result['gap_wait']['source'],('api.fantlab.ru','www.wikidata.org'))
        self.assertEqual(result['sources'][0]['kind'],'local_agreement');self.assertTrue(result['sources'][0]['verified_identity'])
        local=[e for e in result['evidence'] if e['source_url']=='']
        self.assertEqual({e['field'] for e in local},{'title','authors'});self.assertIn('Rollins James',local[0]['basis'])
        validate_policy(self.row,result['review'],result['metadata_facts'])
    def test_catalog_fills_only_missing_original_title_and_language(self):
        self.catalog.fantlab=[{'work_id':42,'name':'Sandstorm','rusname':'Око Бога','all_autor_name':'James Rollins','all_autor_rusname':'Джеймс Роллинс'}]
        self.catalog.extended['/work/42/extended']={'work_id':42,'work_name':'Око Бога','work_name_orig':'The Eye of God','lang_code':'en','work_type_name':'Роман',
            'authors':[{'type':'autor','name':'Джеймс Роллинс','name_orig':'James Rollins'}]}
        result=self.lookup(SERGEI)
        self.assertEqual(result['reasons'],[],result);self.assertEqual(result['review']['title'],'The Eye of God');self.assertEqual(result['review']['canonical_author'],'Rollins James')
        self.assertEqual(result['work']['id'],'fantlab:42');self.assertEqual(result['metadata_facts']['original_language'],{'value':'en','status':'verified'})
        cited={e['field']:e['source_url'] for e in result['evidence'] if e['source_url']}
        self.assertEqual(cited,{'title':'https://fantlab.ru/work42','authors':'https://fantlab.ru/work42','original_language':'https://fantlab.ru/work42'})
        self.assertFalse(any('duckduckgo' in u or 'wikipedia' in u for u in self.catalog.calls))
    def test_catalog_with_a_different_author_is_never_adopted(self):
        self.catalog.fantlab=[{'work_id':43,'name':'Око Бога','rusname':'Око Бога','all_autor_name':'Other Writer','all_autor_rusname':'Другой Автор'}]
        result=self.lookup(SERGEI)
        self.assertEqual(result['reasons'],[]);self.assertEqual(result['review']['canonical_author'],'Rollins James');self.assertEqual(len([u for u in self.catalog.calls if '/extended' in u]),0)
    def test_local_conflict_keeps_the_existing_research_path(self):
        result=self.lookup([('Роллинс Джеймс - Песчаный дьявол/01.mp3',{'album':'Око Бога','artist':'Джеймс Роллинс','track':'1'})])
        self.assertEqual(result['local_agreement']['title']['state'],'red');self.assertTrue(result['reasons'])
        self.assertIsNone(result['review']);self.assertTrue(any('duckduckgo' in u for u in self.catalog.calls),self.catalog.calls)
    def test_missing_full_author_name_is_searched_and_required(self):
        files=[('Роллинс - Око Бога/01.mp3',{'album':'Око Бога','artist':'Роллинс','track':'1'})]
        self.catalog.closed={'api.fantlab.ru','www.wikidata.org'}
        self.catalog.openlibrary=[{'key':'/works/OL7W','title':'Око Бога','author_name':['Джеймс Роллинс']}]
        result=self.lookup(files)
        self.assertEqual(result['reasons'],[],result);self.assertEqual(result['review']['canonical_author'],'Роллинс Джеймс')
        self.assertEqual(next(e for e in result['evidence'] if e['field']=='authors')['source_url'],'https://openlibrary.org/works/OL7W')
        self.catalog.openlibrary=[];self.catalog.closed|={'openlibrary.org','www.googleapis.com','itunes.apple.com'}
        with connect(self.client.database) as db:db.execute('DELETE FROM public_research_cache')
        result=self.lookup(files)
        self.assertIn('Author full name not established',result['reasons']);self.assertIsNotNone(result['wait'])
    def test_revalidation_refuses_changed_local_sources(self):
        result=self.lookup(SERGEI);recorded=result['metadata_facts']['local_agreement']
        revalidate(self.row,str(self.base),recorded)
        changed=json.loads(json.dumps(self.row));changed['members'][0]['metadata']['tags']['artist']='Клайв Касслер';changed['members'][1]['metadata']['tags']['artist']='Клайв Касслер'
        with self.assertRaises(ValueError):revalidate(changed,str(self.base),recorded)

class SchedulingTests(unittest.TestCase):
    def wait(self,host,at):return ResearchWait(host,'closed',at)
    def test_blocked_stage_waits_for_the_source_that_can_answer(self):
        waits=[self.wait('html.duckduckgo.com',300),self.wait('api.fantlab.ru',3600),self.wait('www.wikidata.org',4000)]
        self.assertEqual(_wait(waits)['retry_at'],3600)
        self.assertEqual(_wait(waits,{'www.wikidata.org'})['retry_at'],300)
        both=[self.wait('html.duckduckgo.com',5000),self.wait('en.wikipedia.org',6000),self.wait('api.fantlab.ru',3600)]
        self.assertEqual(_wait(both)['retry_at'],5000)
    def test_vendor_published_pacing_only(self):
        self.assertEqual(host_policy('openlibrary.org'),(1800,1.1));self.assertEqual(host_policy('itunes.apple.com'),(900,3.5))
        self.assertEqual(host_policy('api.fantlab.ru'),(APP_HOST_REQUESTS,1.1));self.assertEqual(host_policy('www.wikidata.org')[0],100)
    def test_duckduckgo_human_check_is_a_long_pause_not_a_retry(self):
        temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(temp.cleanup);now=[1000.0]
        def fetch(url,*_):raise urllib.error.HTTPError(url,202,'anomaly',{},None)
        client=PublicClient(Path(temp.name)/'c.sqlite3',fetch=fetch,clock=lambda:now[0])
        with self.assertRaises(ResearchWait) as raised:client.read('https://html.duckduckgo.com/html/?q=x')
        self.assertEqual((raised.exception.reason,raised.exception.kind,raised.exception.retry_at),(CHALLENGE_REASON,'source_pause',4600.0))

class GapDeferralTests(unittest.TestCase):
    """Controller fixtures reuse the existing private fake merge/inventory helpers."""
    local_agreement_default=True
    setUp=automatic_fixtures.AutoTests.setUp;tearDown=automatic_fixtures.AutoTests.tearDown;fake_merge=automatic_fixtures.AutoTests.fake_merge
    def result(self):
        return {'reasons':[],'sources':[{'kind':'local_agreement','verified_identity':True}],'work':{'id':'local:x'},'review':{},'gap_wait':{'source':'api.fantlab.ru','retry_at':10**12}}
    def run_until_admitted(self,auto,merge):
        auto.start();deadline=time.monotonic()+10
        while auto.thread.is_alive() and time.monotonic()<deadline and not merge.approve_automatic.called:auto.thread.join(.02)
        auto.stop();auto.thread.join(5)
    def converter(self,auto,busy_after_lookups):
        """Deterministic converter: busy right after the given lookups, free once drained."""
        state={'lookups':0,'busy':False}
        def lookup(*_):
            state['lookups']+=1;state['busy']=state['lookups'] in busy_after_lookups
            return self.result()
        def idle():
            if state['busy']:state['busy']=False;return False
            return True
        auto.research.lookup=lookup;auto._idle_jobs=idle
        return state
    def history(self):
        with connect(self.db) as db:return json.loads(db.execute('SELECT result FROM automatic_candidates').fetchone()[0])['research_history']
    def test_busy_converter_defers_optional_gap_then_admits_when_free(self):
        auto,merge,inv=self.fake_merge();state=self.converter(auto,{1})
        self.run_until_admitted(auto,merge)
        merge.approve_automatic.assert_called_once();self.assertEqual(state['lookups'],2)
        deferred=[h for h in self.history() if h['state']=='Waiting for source']
        self.assertEqual(len(deferred),1);self.assertTrue(deferred[0]['reasons'][0].startswith('Optional metadata sources cooling down'))
    def test_deferral_is_bounded(self):
        auto,merge,inv=self.fake_merge();state=self.converter(auto,set(range(1,100)))
        self.run_until_admitted(auto,merge)
        merge.approve_automatic.assert_called_once();self.assertEqual(state['lookups'],4)
        self.assertEqual(sum(h['state']=='Waiting for source' for h in self.history()),3)
    def test_idle_converter_admits_immediately(self):
        auto,merge,inv=self.fake_merge();state=self.converter(auto,set())
        self.run_until_admitted(auto,merge);merge.approve_automatic.assert_called_once();self.assertEqual(state['lookups'],1)

if __name__=='__main__':unittest.main()
