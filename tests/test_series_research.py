"""v0.16.11 series research (Sergei 2026-10-18): Goodreads is the series source (its book page, no API,
politely paced and cached); FantLab's cycle is the fallback, counted from the cycle order, co-written
works accepted; Goodreads wins when both answer; the source is recorded on the metadata.
Private fixture pages shaped like the real ones; no network."""
import json,tempfile,unittest,urllib.error,urllib.parse
from html import escape
from pathlib import Path
import public_research
from public_research import PublicClient,PublicResearch,goodreads_book,goodreads_results,goodreads_series,host_policy
from standing_metadata import validate_policy
from test_local_identity import AREA,SERGEI,candidate,catalogue

def search_page(*rows):
    """rows: (book id, title as shown, [names])."""
    blocks=''.join('<tr itemscope itemtype="http://schema.org/Book"><td><a class="bookTitle" itemprop="url" href="/book/show/%s?from_search=true&amp;rank=1">\n'
                   "<span itemprop='name' role='heading' aria-level='4'>%s</span></a><br>%s</td></tr>"%(
                   book,title,''.join('<a class="authorName" itemprop="url" href="https://www.goodreads.com/author/show/1._"><span itemprop="name">%s</span></a>'%n for n in names))
                   for book,title,names in rows)
    return ('<html><body><table class="tableList">%s</table></body></html>'%blocks).encode()

def book_page(book,title,names,series=None,position='10'):
    state={'ROOT_QUERY':{'getBookByLegacyId({"legacyId":"%s"})'%book:{'__ref':'Book:b'}},
           'Book:b':{'__typename':'Book','legacyId':int(book),'title':title,
                     'primaryContributorEdge':{'node':{'__ref':'Contributor:0'},'role':'Author'},
                     'secondaryContributorEdges':[{'node':{'__ref':'Contributor:%d'%i},'role':'Author'} for i in range(1,len(names))]+[{'node':{'__ref':'Contributor:x'},'role':'Translator'}],
                     'bookSeries':[{'userPosition':position,'series':{'__ref':'Series:s'}}] if series else []},
           'Series:s':{'__typename':'Series','title':series or '','webUrl':'https://www.goodreads.com/series/1'},
           'Contributor:x':{'name':'Not An Author'}}
    for index,name in enumerate(names):state['Contributor:%d'%index]={'__typename':'Contributor','name':name}
    data={'props':{'pageProps':{'apolloState':state}}}
    return ('<html><script id="__NEXT_DATA__" type="application/json">%s</script></html>'%json.dumps(data,ensure_ascii=False)).encode()

TITLE='Призраки белых ночей';AUTHORS='Лена Обухова, Наталья Тимошенко'

def series_page(position='10',shown_position='10',primary='Наталья Тимошенко',book='55108791'):
    """Reduced fixture of the captured real SeriesHeader/SeriesList props shape.

    Two independent chunks deliberately make list index different from the explicit position.
    """
    def component(kind,data):return '<div data-react-class="ReactComponents.%s" data-react-props="%s"></div>'%(kind,escape(json.dumps(data,ensure_ascii=False),quote=True))
    item={'book':{'bookId':book,'bookUrl':'/book/show/'+book,'title':TITLE+' (Нормальное аномальное, #'+shown_position+')','bookTitleBare':TITLE,'author':{'name':primary}}}
    first=[{'book':{'bookId':str(i),'bookUrl':'/book/show/'+str(i),'title':'Earlier '+str(i),'bookTitleBare':'Earlier '+str(i),'author':{'name':'Лена Обухова'}}} for i in (1,2)]
    return ('<html><link rel="canonical" href="https://www.goodreads.com/series/249925">'+
            component('SeriesHeader',{'title':'Нормальное аномальное Series'})+
            component('SeriesList',{'series':first,'seriesHeaders':['Book 1','Book 2']})+
            component('SeriesList',{'series':[item],'seriesHeaders':['Book '+position]})+'</html>').encode()

class Sources:
    """Private Goodreads and FantLab answers; every request is recorded."""
    def __init__(self):
        self.calls=[];self.closed=set();self.goodreads_search=search_page();self.goodreads_books={};self.goodreads_series={};self.fantlab=[];self.extended={}
    def fetch(self,url,*_):
        self.calls.append(url);parsed=urllib.parse.urlsplit(url)
        if parsed.hostname in self.closed:raise urllib.error.HTTPError(url,503,'private fixture',{},None)
        if parsed.hostname=='www.goodreads.com':
            if parsed.path=='/search':return self.goodreads_search
            if parsed.path.startswith('/series/'):return self.goodreads_series[parsed.path]
            return self.goodreads_books[parsed.path.rsplit('/',1)[1]]
        if parsed.hostname=='api.fantlab.ru':
            if parsed.path=='/search-works':return json.dumps(self.fantlab).encode()
            return json.dumps(self.extended[parsed.path]).encode()
        if parsed.hostname=='www.wikidata.org':return json.dumps({'search':[]}).encode()
        return b'{"items":[],"results":[],"docs":[]}'
    def hosts(self):return [urllib.parse.urlsplit(u).hostname for u in self.calls]

def fantlab_cycle(sources,position_extra=True):
    """FantLab: the work in an inner cycle of an outer cycle; one unnumbered extra ("plus") comes before it."""
    sources.fantlab=[{'work_id':1073600,'name':'','rusname':TITLE,'all_autor_name':'','all_autor_rusname':'Наталья Тимошенко, Лена Обухова'}]
    sources.extended['/work/1073600/extended']={'work_id':1073600,'work_name':TITLE,'work_type_id':1,'authors':[{'type':'autor','name':'Наталья Тимошенко'},{'type':'autor','name':'Лена Обухова'}],
        'parents':{'cycles':[[{'work_id':1209707,'work_name':'Секретное досье','work_type_id':4},{'work_id':1006801,'work_name':'Секретное досье. Мистические романы','work_type_id':4}]],'digest':[]}}
    children=[{'work_id':1,'work_type_id':1,'deep':1},{'work_id':2,'work_type_id':1,'deep':1,'plus':1 if position_extra else None},{'work_id':3,'work_type_id':5,'deep':1},
              {'work_id':4,'work_type_id':1,'deep':2},{'work_id':1073600,'work_type_id':1,'deep':1}]
    sources.extended['/work/1006801/extended']={'work_id':1006801,'children':children}

class Base(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name);self.now=[100000.0]
        self.sources=Sources();self.client=PublicClient(self.base/'catalog.sqlite3',fetch=self.sources.fetch,clock=lambda:self.now[0])
        class ClockStop:
            def is_set(_self):return False
            def wait(_self,seconds):self.now[0]+=seconds;return False
        self.stop=ClockStop();self.research=PublicResearch(self.client,leads=[])
    def gap(self,author=AUTHORS):
        local={'gaps':['series'],'fields':{'author':{'partial':False}}}
        return self.research._gap_fill(local,TITLE,author,self.stop,{'remaining':12},[],lambda *_:None,{'sources':[]})
    def goodreads(self,series='Нормальное аномальное',position='10',shown=None):
        self.sources.goodreads_search=search_page(('55108791',shown or TITLE+' (%s, #%s)'%(series,position),['Наталья Тимошенко','Лена Обухова']),
                                                  ('220837262',TITLE,['Лена Обухова','Наталья Тимошенко']))
        self.sources.goodreads_books['55108791']=book_page('55108791',TITLE,['Наталья Тимошенко','Лена Обухова'],series,position)

class ParserTests(unittest.TestCase):
    def test_search_rows_and_the_book_record(self):
        rows=goodreads_results(search_page(('7','A &amp; B (S, #2)',['Ann One','Bob Two'])))
        self.assertEqual(rows,[('7','A & B (S, #2)',['Ann One','Bob Two'])])
        self.assertEqual(goodreads_book(book_page('7','A',['Ann One','Bob Two'],'S','2'),'7'),('A',['Ann One','Bob Two'],[('S','2')]),'translators are not credited people')
        self.assertIsNone(goodreads_book(book_page('7','A',['Ann One'],'S'),'8'),'another book id is not this page')
        self.assertIsNone(goodreads_book(b'<html>no record</html>','7'))

class SeriesTests(Base):
    def cited(self):
        self.research.leads=[{'title':TITLE,'authors':['Лена Обухова','Наталья Тимошенко'],'series_urls':['https://www.goodreads.com/series/249925']}]
        self.sources.goodreads_search=search_page(('55108791',TITLE+' (Нормальное аномальное, #10)',['Наталья Тимошенко','Лена Обухова']),
                                                  ('220837262',TITLE,['Лена Обухова','Наталья Тимошенко']))
        self.sources.goodreads_series['/series/249925']=series_page()

    def test_cited_series_joins_all_author_search_identity_to_explicit_second_chunk_position(self):
        self.cited();result={'sources':[]}
        found=self.research._series_goodreads(TITLE,AUTHORS,self.stop,{'remaining':6},result)
        self.assertEqual((found['name'],found['number'],found['book_id']),('Нормальное аномальное','10','55108791'))
        self.assertEqual([urllib.parse.urlsplit(url).path for url in self.sources.calls],['/search','/series/249925'])
        self.assertEqual([r['fields'] for r in result['sources']],[['title','authors'],['series','number']])
        self.assertTrue(all(r['sha256'] for r in result['sources']))
        count=len(self.sources.calls);self.research._series_goodreads(TITLE,AUTHORS,self.stop,{'remaining':6},{'sources':[]})
        self.assertEqual(len(self.sources.calls),count,'both responses reused under the normal client cache')

    def test_series_entry_cannot_replace_missing_coauthor_identity_or_infer_position(self):
        self.cited();self.sources.goodreads_search=search_page(('55108791',TITLE+' (Нормальное аномальное, #10)',['Наталья Тимошенко']))
        self.assertIsNone(self.research._series_goodreads(TITLE,AUTHORS,self.stop,{'remaining':6},{'sources':[]}))
        self.assertEqual(len(self.sources.calls),1,'partial search authors cannot authorize series-page matching')
        for raw in (series_page(position='9'),series_page(position='1-3'),series_page(primary='Different Author'),series_page(book='8')):
            self.assertIsNone(goodreads_series(raw,'https://www.goodreads.com/series/249925','55108791',TITLE,AUTHORS))
        self.assertIsNone(goodreads_series(series_page(),'https://www.goodreads.com/series/8','55108791',TITLE,AUTHORS),'canonical URL must bind the exact page')

    def test_cited_series_obeys_shared_host_pause_without_another_provider_route(self):
        self.cited()
        # Prime only search, then pause the same existing host before the uncached series request.
        url='https://www.goodreads.com/search?'+urllib.parse.urlencode({'q':TITLE+' Лена Обухова','search_type':'books'})
        self.client.read(url,self.stop,{'remaining':1})
        from scanner import connect
        with connect(self.client.database) as db:db.execute('INSERT OR REPLACE INTO public_research_limits VALUES(?,?,?)',('www.goodreads.com',self.now[0]+3600,'Public source presented a human check; no bypass attempted'))
        before=len(self.sources.calls)
        with self.assertRaises(public_research.ResearchWait):self.research._series_goodreads(TITLE,AUTHORS,self.stop,{'remaining':6},{'sources':[]})
        self.assertEqual(len(self.sources.calls),before,'no alternate client, book-page retry or host-pause bypass')

    def test_goodreads_is_the_series_source_and_wins_over_fantlab(self):
        self.goodreads();fantlab_cycle(self.sources)
        found=self.gap()
        self.assertEqual(found['series'],{'provider':'goodreads','name':'Нормальное аномальное','number':'10','source_url':'https://www.goodreads.com/book/show/55108791'})
        self.assertNotIn('/work/1006801/extended',[urllib.parse.urlsplit(u).path for u in self.sources.calls],'FantLab is not asked when Goodreads answers')
        self.assertEqual(self.sources.hosts().count('www.goodreads.com'),2,'one search and one book page')
        # Cached: the same book again asks nobody.
        before=len(self.sources.calls);self.assertEqual(self.gap()['series']['number'],'10');self.assertEqual(len(self.sources.calls),before)

    def test_fantlab_cycle_is_the_fallback_counted_from_its_order(self):
        self.sources.goodreads_search=search_page(('220837262',TITLE,['Лена Обухова','Наталья Тимошенко']))  # Goodreads lists no series
        fantlab_cycle(self.sources)
        found=self.gap()
        # Numbered: work 1 and this one; the extra (plus), a story (another kind) and a nested work are not counted.
        self.assertEqual(found['series'],{'provider':'fantlab','name':'Секретное досье. Мистические романы','number':'2','source_url':'https://fantlab.ru/work1006801'})
        self.assertNotIn('/book/show/220837262',[urllib.parse.urlsplit(u).path for u in self.sources.calls],'no book page without a series lead')

    def test_unclear_goodreads_positions_and_other_people_are_not_used(self):
        fantlab_cycle(self.sources,position_extra=False)
        self.goodreads(position='1-3')
        self.assertEqual(self.gap()['series']['provider'],'fantlab','a range is no single position')
        self.setUp();fantlab_cycle(self.sources,position_extra=False)
        self.sources.goodreads_search=search_page(('9',TITLE+' (Other, #4)',['Somebody Else']))
        found=self.gap();self.assertEqual((found['series']['provider'],found['series']['number']),('fantlab','3'))
        self.assertNotIn('/book/show/9',[urllib.parse.urlsplit(u).path for u in self.sources.calls])
        # One of two credited people missing from FantLab's credit: no series at all.
        self.setUp();fantlab_cycle(self.sources);self.sources.fantlab[0]['all_autor_rusname']='Наталья Тимошенко'
        self.assertNotIn('series',self.gap())

    def test_goodreads_unavailable_uses_fantlab_and_still_waits_a_little_for_goodreads(self):
        self.sources.closed={'www.goodreads.com'};fantlab_cycle(self.sources)
        found=self.gap()
        self.assertEqual(found['series']['provider'],'fantlab');self.assertIn('goodreads',found['closed'],'the book may wait for Goodreads (gap deferral)')

    def test_goodreads_is_read_politely(self):
        requests,spacing=host_policy('www.goodreads.com')
        self.assertLessEqual(requests,120);self.assertGreaterEqual(spacing,3.0,'at most one request every few seconds')
        self.assertIn('BooksArranger',public_research.USER_AGENT);self.assertIn('www.goodreads.com',public_research.HOSTS)
        self.goodreads();start=self.now[0];self.gap()
        self.assertGreaterEqual(self.now[0]-start,spacing,'the second request waited for the spacing')

class LookupTests(Base):
    """End to end through the local-agreement lookup: the series, its number and its recorded source."""
    def test_local_agreement_gets_the_goodreads_series_with_its_source(self):
        title,author='Око Бога','James Rollins'
        self.sources.goodreads_search=search_page(('42','%s (Отряд Сигма, #8)'%title,[author]))
        self.sources.goodreads_books['42']=book_page('42',title,[author],'Отряд Сигма','8')
        row=catalogue(self.client.database,self.base,candidate(self.base,SERGEI))
        # 0.22.1 (backlog item 8): research asks no source; the book is approved without its series at once and series
        # backfill looks the series up later (in its own lane of the site's hourly bound).
        first=self.research.lookup(row,str(self.base),self.stop)
        self.assertEqual((first['reasons'],first['review']['series'],self.sources.calls),([],'',[]))
        self.assertTrue(self.research._series_goodreads(title,'Джеймс Роллинс',self.stop,{'remaining':6,'lane':'series'},{'sources':[]}))
        asked=len(self.sources.calls)
        # Research reads the cached answer: the series, its number and its source, with no new request.
        result=self.research.lookup(row,str(self.base),self.stop)
        self.assertEqual(len(self.sources.calls),asked)
        self.assertEqual(result['reasons'],[],result)
        self.assertEqual((result['review']['series'],result['review']['number']),('Отряд Сигма','8'))
        facts=result['metadata_facts'];self.assertEqual(facts['series_state'],'verified')
        self.assertEqual(facts['series_source'],{'provider':'goodreads','url':'https://www.goodreads.com/book/show/42'})
        cited=[e for e in result['evidence'] if e['field'] in ('series','number')]
        self.assertEqual({e['source_url'] for e in cited},{'https://www.goodreads.com/book/show/42'});self.assertIn('Goodreads',cited[0]['basis'])
        validate_policy(row,result['review'],facts)
        self.assertTrue(any(s.get('url')=='https://www.goodreads.com/book/show/42' for s in result['sources']),'a receipt for the fetched page')



def setUpModule():
    # Ruling 29 (0.22.2) has its own tests; these fixtures predate it (tests/original_title_fixture.py).
    global _no_original_title_wait
    from original_title_fixture import no_wait
    _no_original_title_wait = no_wait()


def tearDownModule():
    _no_original_title_wait.stop()


if __name__=='__main__':unittest.main()
