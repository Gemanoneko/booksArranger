"""Finite anonymous-provider fixtures. No production network, inventory or library actions."""
import copy,json,tempfile,threading,unittest,urllib.parse,urllib.error
from pathlib import Path
from scanner import connect
from public_research import PublicClient,PublicResearch,APP_LIMIT_REASON
from public_work_identity import wikidata_work
from source_identity import norm
from public_research import _credit_matches
from test_automatic_processing import row
import groups
from unittest.mock import patch

AREA=Path(__file__).resolve().parents[1]/'scratch'/'public-work-identity-2026-10-11'
AREA.mkdir(parents=True,exist_ok=True)

def claim(property,value=None,novalue=False):
    snak={'property':property,'snaktype':'novalue' if novalue else 'value'}
    if not novalue:snak['datavalue']={'value':value}
    return {'rank':'normal','mainsnak':snak}

def entity(id,name,claims=None,russian=None):
    return {'id':id,'labels':{'en':{'value':name},'ru':{'value':russian or name}},'aliases':{},'claims':claims or {}}

class FallbackFixture:
    def __init__(self,cover=b''):
        self.cover=cover;self.calls=[];self.search=['Q100']
        self.work=entity('Q100','A Book',{'P50':[claim('P50',{'id':'Q200'})],
            'P407':[claim('P407',{'id':'Q300'})],'P31':[claim('P31',{'id':'Q400'})],
            'P1476':[claim('P1476',{'text':'A Book','language':'en'})],'P179':[claim('P179',novalue=True)]},'Книга')
        self.related={'Q200':entity('Q200','John Writer',russian='Джон Писатель'),
            'Q300':entity('Q300','English',{'P218':[claim('P218','en')]}),
            'Q301':entity('Q301','Russian',{'P218':[claim('P218','ru')]}),'Q400':entity('Q400','novel')}
        self.ol_author='John Writer';self.ol_languages=['eng','rus']
        self.page=b'<p>A Book - John Writer. A standalone novel. Original language: English.</p>'
    def fetch(self,url,*_):
        self.calls.append(url);parsed=urllib.parse.urlsplit(url);query=urllib.parse.parse_qs(parsed.query)
        if parsed.hostname=='api.fantlab.ru':raise AssertionError('Capped FantLab must never be fetched')
        if parsed.hostname=='www.wikidata.org':
            if query['action']==['wbsearchentities']:data={'search':[{'id':id} for id in self.search]}
            else:
                ids=query['ids'][0].split('|');records={}
                for id in ids:
                    if id in ('Q100','Q101'):records[id]=copy.deepcopy(self.work)|{'id':id}
                    elif id in self.related:records[id]=self.related[id]
                data={'entities':records}
            return json.dumps(data).encode()
        if parsed.hostname=='openlibrary.org':
            if parsed.path=='/search.json':data={'docs':[{'key':'/works/OL1W','title':'A Book','author_name':['John Writer'],'author_key':['OL1A'],'cover_i':99,'language':self.ol_languages}]}
            elif parsed.path=='/works/OL1W.json':data={'key':'/works/OL1W','title':'A Book','authors':[{'type':'/type/author_role','author':{'key':'/authors/OL1A'}}]}
            elif parsed.path=='/authors/OL1A.json':data={'key':'/authors/OL1A','name':self.ol_author}
            else:raise AssertionError('Unknown private catalog route')
            return json.dumps(data).encode()
        if parsed.hostname=='html.duckduckgo.com':return b'<a class="result__a" href="https://ast.ru/book/example/">discovery only</a>'
        if parsed.hostname.endswith('.wikipedia.org'):return b'{"query":{"pages":[]}}'
        if parsed.hostname=='ast.ru':return self.page
        if parsed.hostname=='covers.openlibrary.org':return self.cover
        raise AssertionError('Unknown private provider URL')

def cap_fantlab(database,now):
    with connect(database) as db:
        db.executemany('INSERT INTO public_research_requests(host,at) VALUES(?,?)',[('api.fantlab.ru',now-1)]*100)

class FallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name);self.now=[100000.0]
        # These cases exercise the Internet research path; local agreement is tested in test_local_identity.
        research_path=patch.object(PublicResearch,'local_agreement',False);research_path.start();self.addCleanup(research_path.stop)
        self.fixture=FallbackFixture();self.client=PublicClient(self.base/'catalog.sqlite3',fetch=self.fixture.fetch,clock=lambda:self.now[0]);cap_fantlab(self.client.database,self.now[0])
        class ClockStop:
            def is_set(_self):return False
            def wait(_self,seconds):self.now[0]+=seconds;return False
        self.stop=ClockStop()
        self.row=next(iter(groups.build([row(self.base/'John Writer - A Book.mp3','A Book')]).values()))|{'fingerprint':'private-fixture-fingerprint'}
    def lookup(self):return PublicResearch(self.client,leads=[]).lookup(self.row,str(self.base),self.stop)
    def test_host_cap_uses_independent_work_and_preserves_actual_credit_gate(self):
        result=self.lookup();self.assertEqual(result['reasons'],[],result)
        self.assertEqual(result['work']['id'],'wikidata:Q100');self.assertEqual(result['review']['title'],'A Book')
        self.assertEqual(result['work']['original_language'],'en');self.assertEqual(result['wait']['kind'],'app_limit')
        self.assertFalse(any('api.fantlab.ru' in url for url in self.fixture.calls))
        self.assertTrue(any(s.get('verified_identity') for s in result['sources'] if s['kind']=='publisher_or_journal'))
        with connect(self.client.database) as db:self.assertEqual(db.execute("SELECT count(*) FROM public_research_requests WHERE host='api.fantlab.ru'").fetchone()[0],100)
    def test_unavailable_search_uses_independent_wikipedia_primary_reference(self):
        fetch=self.fixture.fetch
        def alternate_lead(url,*args):
            host=urllib.parse.urlsplit(url).hostname
            if host=='html.duckduckgo.com':
                self.fixture.calls.append(url);raise urllib.error.HTTPError(url,503,'private fixture',{},None)
            if host.endswith('.wikipedia.org'):
                self.fixture.calls.append(url)
                return json.dumps({'query':{'pages':[{'pageid':41,'ns':0,'title':'A Book','revisions':[{'revid':99}],
                    'extlinks':[{'url':'https://ast.ru/book/example/'}]}]}}).encode()
            return fetch(url,*args)
        self.client.fetch=alternate_lead;result=self.lookup()
        self.assertEqual(result['reasons'],[],result)
        self.assertTrue(any(s['kind']=='encyclopedia_lead' and s['revision_id']==99 and not s['verified_identity'] for s in result['sources']))
        self.assertTrue(any(s['kind']=='publisher_or_journal' and s['verified_identity'] for s in result['sources']))
        with connect(self.client.database) as db:
            pause=db.execute("SELECT next_at,reason FROM public_research_limits WHERE host='html.duckduckgo.com'").fetchone()
        self.assertGreater(pause['next_at'],self.now[0]);self.assertIn('source unavailable',pause['reason'].lower())
    def test_translator_credit_is_not_independent_author_evidence(self):
        self.fixture.page=b'<p>A Book - John Writer: translator.</p>'
        self.assertIn('Author and work not independently verified',self.lookup()['reasons'])
    def test_edition_languages_and_missing_work_language_remain_held(self):
        self.fixture.work['claims']['P407']=[];self.fixture.page=b'<p>A Book - John Writer. A standalone novel.</p>'
        result=self.lookup();self.assertEqual(result['metadata_facts']['original_language'],{'value':None,'status':'unknown'})
        self.assertEqual(result['reasons'],[])
        self.assertEqual(result['work']['original_language'],'')
    def test_explicit_primary_language_can_complete_an_openlibrary_work(self):
        self.fixture.search=[];result=self.lookup()
        self.assertEqual(result['reasons'],[],result);self.assertTrue(result['work']['id'].startswith('openlibrary:'))
        language=next(e for e in result['evidence'] if e['field']=='original_language')
        self.assertEqual(language['source_url'],'https://ast.ru/book/example/')
    def test_conflicting_original_languages_and_titles_cannot_be_overridden(self):
        self.fixture.work['claims']['P407'].append(claim('P407',{'id':'Q301'}))
        self.assertIn('Conflicting original work languages',self.lookup()['reasons'])
    def test_two_same_credit_work_entities_remain_ambiguous(self):
        self.fixture.search=['Q100','Q101']
        self.assertIn('Independent catalogs disagree on the work identity',self.lookup()['reasons'])
    def test_fetched_author_contradiction_does_not_adopt_search_proposal(self):
        self.fixture.ol_author='Other Writer'
        self.assertIn('Independent catalog author contradiction',self.lookup()['reasons'])
    def test_unknown_series_and_disconnected_standalone_claim_remain_held(self):
        self.fixture.work['claims']['P179']=[]
        self.fixture.page=b'<p>A Book - John Writer.</p><p>Other Book is a standalone novel.</p>'
        result=self.lookup();self.assertEqual(result['reasons'],[]);self.assertEqual(result['metadata_facts']['series_state'],'omitted_unknown')
    def test_scoped_author_or_language_cannot_be_flattened_into_whole_work(self):
        for property,scope in (('P50','P3831'),('P407','P518')):
            with self.subTest(property=property):
                original=copy.deepcopy(self.fixture.work['claims'][property][0])
                self.fixture.work['claims'][property][0]['qualifiers']={scope:[{'snaktype':'value','property':scope,'datavalue':{'value':{'id':'Q999'}}}]}
                result=self.lookup()
                self.assertIn('Qualified work identity relationship needs stronger evidence',result['reasons'])
                self.assertIsNone(result['review'])
                self.fixture.work['claims'][property][0]=original
    def test_wrong_author_or_language_property_is_a_contradiction_not_fallback(self):
        for property,other in (('P50','P655'),('P407','P1412')):
            with self.subTest(property=property):
                self.fixture.work['claims'][property][0]['mainsnak']['property']=other
                result=self.lookup()
                self.assertIn('Conflicting catalog relationship property',result['reasons'])
                self.assertIsNone(result['review'])
                self.fixture.work['claims'][property][0]['mainsnak']['property']=property
    def test_deprecated_relationship_cannot_override_current_work_credit(self):
        old=claim('P50',{'id':'Q999'});old['rank']='deprecated';old['qualifiers']={'P3831':[]}
        self.fixture.work['claims']['P50'].append(old)
        self.assertEqual(self.lookup()['reasons'],[])
    def test_nonvalue_author_or_language_does_not_invent_a_work_relationship(self):
        for property in ('P50','P407'):
            for snaktype in ('novalue','somevalue'):
                with self.subTest(property=property,snaktype=snaktype):
                    work=copy.deepcopy(self.fixture.work)
                    work['claims'][property]=[{'rank':'normal','mainsnak':{'property':property,'snaktype':snaktype}}]
                    result=wikidata_work(work,self.fixture.related,'A Book','John Writer',norm,_credit_matches)
                    if property=='P50':self.assertIsNone(result)
                    else:self.assertEqual(result['lang_code'],'')
    def french_work(self,english_page=False):
        self.fixture.work['labels']['en']['value']='Souvenir'
        self.fixture.work['claims']['P1476']=[claim('P1476',{'text':'Souvenir','language':'fr'})]
        self.fixture.related['Q300']=entity('Q300','French',{'P218':[claim('P218','fr')]})
        self.fixture.page='<p>Книга - Джон Писатель. A standalone novel.</p>'.encode()
        self.row=next(iter(groups.build([row(self.base/'Джон Писатель - Книга.mp3','Книга','Джон Писатель')]).values()))|{'fingerprint':'private-fixture-fingerprint'}
        fetch=self.fixture.fetch
        def with_translation(url,*args):
            parsed=urllib.parse.urlsplit(url)
            if parsed.hostname=='html.duckduckgo.com' and 'Souvenir' in urllib.parse.parse_qs(parsed.query).get('q',[''])[0]:
                self.fixture.calls.append(url)
                return b'<a class="result__a" href="https://ast.ru/book/english-edition/">translation discovery only</a>' if english_page else b''
            if parsed.hostname=='ast.ru' and parsed.path=='/book/english-edition/':
                self.fixture.calls.append(url);return b'<p>Souvenir - John Writer.</p>'
            return fetch(url,*args)
        self.client.fetch=with_translation
    def test_same_latin_original_and_english_label_still_need_fetched_publication(self):
        self.french_work();result=self.lookup()
        self.assertEqual(result['review']['title'],'Книга');self.assertEqual(result['metadata_facts']['title_basis'],'source_russian')
        self.assertTrue(any(s.get('verified_identity') and s['url']=='https://ast.ru/book/example/' for s in result['sources']))
        self.assertEqual(result['reasons'],[])
        self.assertFalse(any(s.get('verified_identity') and s['url']=='https://ast.ru/book/english-edition/' for s in result['sources']))
    def test_verified_english_credit_cites_the_actual_publication(self):
        self.french_work(english_page=True);result=self.lookup()
        self.assertEqual(result['reasons'],[],result)
        titles=[e for e in result['evidence'] if e['field']=='title']
        self.assertEqual({e['source_url'] for e in titles},{'https://www.wikidata.org/wiki/Q100','https://ast.ru/book/english-edition/'})
        self.assertEqual(next(e for e in titles if e['source_url'].endswith('/wiki/Q100'))['cited_value'],result['metadata_facts']['original_title'])
        self.assertEqual(next(e for e in titles if e['source_url'].endswith('/english-edition/'))['cited_value'],result['review']['title'])
        self.assertEqual(next(e for e in result['evidence'] if e['field']=='authors')['source_url'],'https://ast.ru/book/english-edition/')
    def test_edition_entity_does_not_supply_original_work_language(self):
        self.fixture.work['claims']['P629']=[claim('P629',{'id':'Q900'})]
        self.fixture.page=b'<p>A Book - John Writer.</p>'
        result=self.lookup();self.assertEqual(result['metadata_facts']['original_language']['value'],None);self.assertFalse(any(e['field']=='original_language' for e in result['evidence']))

if __name__=='__main__':unittest.main()
