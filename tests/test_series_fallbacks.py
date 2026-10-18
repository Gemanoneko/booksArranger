"""Reduced real PRH schema and explicit Wikidata claim fixtures; no network."""
import copy,json,tempfile,unittest,urllib.parse
from pathlib import Path
from public_research import PublicClient,PublicResearch,_same_people,ResearchWait,CHALLENGE_REASON
from scanner import connect
from local_identity import title_key
from series_evidence import wikidata_series,prh_series

URL='https://www.penguinrandomhouse.com/books/136455/his-dark-materials-the-subtle-knife-book-2-by-philip-pullman/'
# Reduced from legitimate installed-client raw SHA725b6ba15a47485d5d146c1b19771776497b4343939a847f412242a38b6ee477.
BOOK={'@type':'Book','author':'Philip Pullman','isbn':'9780375823466','name':'His Dark Materials: The Subtle Knife (Book 2)',
      'isPartOf':{'@type':'BookSeries','name':'His Dark Materials','url':'https://www.penguinrandomhouse.com/series/HDM/his-dark-materials'}}
def publisher(book=None,description=True,canonical=URL):
    data={'@type':'WebPage','mainEntity':BOOK if book is None else book}
    scoped='<div id="book-description-copy"><div>The spellbinding sequel. Look for the modern fantasy classics of HIS DARK MATERIALS:</div></div>' if description else '<div>Greatest Novel; other unrelated sequel.</div>'
    return ('<link rel="canonical" href="'+canonical+'"><script type="application/ld+json">'+json.dumps(data)+'</script>'+scoped).encode()

def claim(prop,value):return {'rank':'normal','mainsnak':{'property':prop,'snaktype':'value','datavalue':{'value':value}}}
def entity(id,name,props):return {'id':id,'lastrevid':123,'labels':{'en':{'value':name}},'aliases':{},'claims':props}
def wikidata():
    relation=claim('P179',{'id':'Q129240'})|{'id':'Q472208$statement-guid','qualifiers':{'P1545':[{'property':'P1545','snaktype':'value','datavalue':{'value':'2'}}]},
        'references':[{'snaks':{'P854':[{'property':'P854','snaktype':'value','datavalue':{'value':URL}}]}}]}
    work=entity('Q472208','The Subtle Knife',{'P31':[claim('P31',{'id':'Q7725634'})],'P50':[claim('P50',{'id':'Q1868'})],'P179':[relation]})
    related={'Q1868':entity('Q1868','Philip Pullman',{}),'Q129240':entity('Q129240','His Dark Materials',{'P31':[claim('P31',{'id':'Q1667921'})]})}
    return work,related

class EvidenceTests(unittest.TestCase):
    def test_publisher_explicit_work_scoped_continuation_and_ordinal(self):
        found=prh_series(publisher(),URL,'The Subtle Knife','Philip Pullman',title_key,_same_people)
        self.assertEqual((found['name'],found['number']),('His Dark Materials','2'))
        self.assertIsNone(prh_series(publisher(description=False),URL,'The Subtle Knife','Philip Pullman',title_key,_same_people),'award novel/whole-page cooccurrence is not narrative proof')
        for prop,value in (('author','Another Author'),('name','His Dark Materials: The Subtle Knife (Book 2-3)'),('isbn','wrong')):
            book=copy.deepcopy(BOOK);book[prop]=value
            self.assertIsNone(prh_series(publisher(book),URL,'The Subtle Knife','Philip Pullman',title_key,_same_people))
        self.assertIsNone(prh_series(publisher(canonical=URL+'other'),URL,'The Subtle Knife','Philip Pullman',title_key,_same_people))
        self.assertIsNone(prh_series(publisher(),URL,'The Subtle Knife','Philip Pullman, Other Writer',title_key,_same_people))
    def test_wikidata_series_only_without_original_language_and_complete_reference(self):
        work,related=wikidata();found=wikidata_series(work,related,'The Subtle Knife','Philip Pullman',title_key,_same_people)
        self.assertEqual((found['number'],found['statement_id']),('2','Q472208$statement-guid'));self.assertEqual(found['work_revision'],123)
        self.assertNotIn('language',found)
    def test_wikidata_rejects_editorial_unreferenced_partial_author_and_wrong_claim_ordinal(self):
        for change in ('editorial','missing_reference','wiki_import_only','wrong_author','other_claim','extra_qualifier','edition'):
            work,related=wikidata();relation=work['claims']['P179'][0]
            if change=='editorial':related['Q129240']['claims']['P31']=[claim('P31',{'id':'Q20655472'})]
            elif change=='missing_reference':relation['references']=[]
            elif change=='wiki_import_only':relation['references']=[{'snaks':{'P143':[{'property':'P143','snaktype':'value','datavalue':{'value':{'id':'Q328'}}}]}}]
            elif change=='wrong_author':work['claims']['P50'].append(claim('P50',{'id':'Q123'}))
            elif change=='other_claim':work['claims']['P179'].append(copy.deepcopy(relation))
            elif change=='extra_qualifier':relation['qualifiers']['P518']=[claim('P518',{'id':'Q1'})]
            else:work['claims']['P629']=[claim('P629',{'id':'Q1'})]
            with self.subTest(change=change):self.assertIsNone(wikidata_series(work,related,'The Subtle Knife','Philip Pullman',title_key,_same_people))

class SharedPolicyTests(unittest.TestCase):
    def setUp(self):
        area=Path(__file__).resolve().parents[1]/'scratch'/'series-fallback-tests';area.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=area);self.addCleanup(self.temp.cleanup);self.now=[100000.];self.calls=[]
        def fetch(url,*_):self.calls.append(url);return b'{}'
        self.client=PublicClient(Path(self.temp.name)/'research.sqlite3',fetch=fetch,clock=lambda:self.now[0])
    def test_wikimedia_historical_sibling_reservations_and_hold_are_shared(self):
        with connect(self.client.database) as db:db.executemany('INSERT INTO public_research_requests VALUES(?,?)',[('ru.wikipedia.org',self.now[0]-100)]*100)
        with self.assertRaises(ResearchWait):self.client.read('https://www.wikidata.org/w/api.php?action=x',budget={'remaining':1})
        self.assertEqual(self.calls,[])
        with connect(self.client.database) as db:
            db.execute('DELETE FROM public_research_requests');db.execute('INSERT OR REPLACE INTO public_research_limits VALUES(?,?,?)',('ru.wikipedia.org',self.now[0]+1000,CHALLENGE_REASON))
        with self.assertRaises(ResearchWait):self.client.read('https://en.wikipedia.org/w/api.php?action=x',budget={'remaining':1})
        self.assertEqual(self.calls,[])
    def test_wikipedia_revision_lead_joins_independent_publisher_proof(self):
        def fetch(url,*_):
            self.calls.append(url)
            if urllib.parse.urlsplit(url).hostname.endswith('wikipedia.org'):
                return json.dumps({'query':{'pages':[{'pageid':420985,'ns':0,'title':'The Subtle Knife','revisions':[{'revid':1357431577}],'extlinks':[{'url':URL}]}]}}).encode()
            return publisher()
        self.client.fetch=fetch;result={'sources':[]}
        found=PublicResearch(self.client,leads=[])._series_publisher('The Subtle Knife','Philip Pullman',None,{'remaining':6},result)
        self.assertEqual(found['number'],'2');self.assertEqual(result['sources'][0]['revision_id'],1357431577)
        self.assertFalse(result['sources'][0]['verified_identity']);self.assertEqual(result['sources'][-1]['fields'],['title','authors','series','number'])
        self.assertNotEqual(result['sources'][0]['sha256'],result['sources'][-1]['sha256'],'Wikipedia lead is not an independent copy of order proof')
    def test_real_series_adapter_uses_explicit_referenced_entities_under_one_budget(self):
        work,related=wikidata()
        def fetch(url,*_):
            self.calls.append(url);query=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            if query['action']==['wbsearchentities']:return json.dumps({'search':[{'id':work['id']}]}).encode()
            records={work['id']:work}|related
            return json.dumps({'entities':{id:records[id] for id in query['ids'][0].split('|') if id in records}}).encode()
        self.client.fetch=fetch
        class Stop:
            def is_set(_self):return False
            def wait(_self,seconds):self.now[0]+=seconds;return False
        budget={'remaining':6};result={'sources':[]}
        found=PublicResearch(self.client,leads=[])._series_wikidata('The Subtle Knife','Philip Pullman',Stop(),budget,result)
        self.assertEqual(found['number'],'2');self.assertEqual(budget['remaining'],3)
        self.assertEqual(len(result['sources']),2);self.assertTrue(all('claims%7Cinfo' in r['api_url'] for r in result['sources']))
        count=len(self.calls);PublicResearch(self.client,leads=[])._series_wikidata('The Subtle Knife','Philip Pullman',Stop(),budget,{'sources':[]})
        self.assertEqual(len(self.calls),count,'normal cached entities spend no new quota or candidate allowance')
    def test_local_exact_all_author_identity_supplies_primary_discovery_without_remote_catalog(self):
        from unittest.mock import patch
        local={'status':'covered','works':[{'id':'/works/OL1W','title':'The Subtle Knife','authors':[{'id':'/authors/OL1A','names':['Philip Pullman']}],'links':[URL],'editions':[]}],
               'receipt':{'sha256':'a'*64,'source_manifest':{'sources':{'works':{},'authors':{}}}}}
        self.client.fetch=lambda url,*_:publisher()
        with patch('openlibrary_index.lookup',return_value=local):
            result={'sources':[]};found=PublicResearch(self.client,leads=[])._series_publisher('The Subtle Knife','Philip Pullman',None,{'remaining':6},result)
        self.assertEqual(found['local_identity']['work']['id'],'/works/OL1W');self.assertEqual(found['number'],'2')
        self.assertEqual(result['local_openlibrary']['purpose'],'identity and primary-page discovery; edition series is not narrative order')

if __name__=='__main__':unittest.main()
