"""Recorded Litres main-record schema (2026-10-28), reduced to factual identity/series fields; no network."""
import json,threading,unittest
from litres_evidence import book,book_url
from public_research import PublicResearch,ResearchWait,allowed_url,parse_page,_page_credit
from public_work_identity import EvidenceConflict

URL='https://www.litres.ru/audiobook/vladimir-torin-32271438/mister-vechnyy-kanun-ueliholn-68057546/'
TEXT='https://www.litres.ru/book/vladimir-torin-32271438/mister-vechnyy-kanun-ueliholn-68042654/'
TITLE='Мистер Вечный Канун. Уэлихолн';PEOPLE=['Олег Яковлев','Владимир Торин'];AUTHOR=', '.join(PEOPLE)

def page(url=URL,position='1',total='2',names=None,canonical=None,series=True):
    data={'@context':'https://schema.org','@type':'Audiobook' if '/audiobook/' in url else 'Book','name':TITLE,'url':url,
          'author':[{'@type':'Person','name':name} for name in (PEOPLE if names is None else names)],
          'readBy':{'@type':'Person','name':'Ярослав Хорошков'},
          'isRelatedTo':{'@type':'Book','name':TITLE,'url':TEXT,'readBy':{'@type':'Person','name':'Not An Author'}}}
    block='<div data-testid="art__inSeries--title"><div>%s книга из %s в серии <a href="/series/mister-vechnyy-kanun-806276/?art_types=audiobook">«Мистер Вечный Канун»</a></div></div>'%(position,total) if series else ''
    return ('<link rel="canonical" href="%s"><script type="application/ld+json">%s</script>'
            '<script type="application/ld+json">{"@type":"Product","name":"Same product"}</script>'
            '<div>{"position":4,"numberOfItems":2}</div>%s'%(canonical or url,json.dumps(data,ensure_ascii=False),block)).encode()

class Client:
    database='private-unused.sqlite'
    def __init__(self,pages=None):self.pages=pages or {URL:page()};self.calls=[];self.queries=[];self.wait=False
    def discover(self,query,*_):
        self.queries.append(query)
        if self.wait:raise ResearchWait('html.duckduckgo.com','Public source presented a human check; no bypass attempted',123,'challenge','host')
        return list(self.pages)
    def read(self,url,*_):self.calls.append(url);return self.pages[url]
    def receipt(self,url):return {'url':url,'sha256':'fixture','retrieved_utc':'2026-10-28T00:00:00Z'}

class LitresTests(unittest.TestCase):
    def test_captured_main_record_has_both_authors_not_reader_or_related_product(self):
        found=book(page(),URL)
        self.assertEqual((found['title'],found['authors']), (TITLE,PEOPLE))
        self.assertEqual(found['series'],{'provider':'litres','name':'Мистер Вечный Канун','number':'1','source_url':URL})
        self.assertNotIn('Ярослав Хорошков',found['authors'])
        self.assertEqual(book(page(url=TEXT),TEXT)['authors'],PEOPLE)
    def test_position_must_be_explicit_not_total_card_order_or_guess(self):
        self.assertIsNone(book(page(series=False),URL)['series'])
        for pos,total in [('','2'),('0','2'),('1-2','2'),('3','2')]:
            with self.subTest(pos=pos,total=total):self.assertIsNone(book(page(position=pos,total=total),URL))
    def test_canonical_and_main_identity_are_bound_to_exact_edition(self):
        self.assertIsNone(book(page(canonical=TEXT),URL))
        self.assertIsNone(book(page(),TEXT))
        self.assertIsNone(book(page(names=[]),URL))
        self.assertIsNone(book(page()+b'<div data-testid="art__inSeries--title">2</div>',URL))
    def test_only_query_free_public_book_paths_are_admitted(self):
        self.assertEqual(book_url(URL.replace('www.','')),URL)
        self.assertEqual(allowed_url(URL),URL)
        for url in ('https://www.litres.ru/search/?q=x',URL+'?art_types=text_book',URL+'#x','https://www.litres.ru/series/mister-vechnyy-kanun-806276/'):
            with self.subTest(url=url):
                self.assertFalse(book_url(url))
                with self.assertRaises(ValueError):allowed_url(url)
    def test_discovery_credit_receipt_and_complete_authors(self):
        client=Client();research=PublicResearch(client,leads=[]);result={'sources':[]}
        found=research._series_litres(TITLE,AUTHOR,threading.Event(),{'remaining':6},result)
        self.assertEqual((found['number'],found['source_url']),('1',URL))
        self.assertTrue(client.queries[0].startswith('site:litres.ru '))
        self.assertEqual(client.calls,[URL]);self.assertEqual(result['sources'][0]['fields'],['title','authors','series','number'])
        self.assertEqual(result['sources'][0]['provider'],'Litres')
        for names in ('Олег Яковлев','Ярослав Хорошков',AUTHOR+', Not An Author'):
            with self.subTest(names=names):self.assertIsNone(research._series_litres(TITLE,names,threading.Event(),{'remaining':6},{'sources':[]}))
        self.assertIsNone(research._series_litres('Other title',AUTHOR,threading.Event(),{'remaining':6},{'sources':[]}))
        self.assertIsNone(_page_credit(URL,page(),parse_page(page()),[TITLE],['Олег Яковлев']))
        self.assertEqual(_page_credit(URL,page(),parse_page(page()),[TITLE],PEOPLE)['author'],AUTHOR)
        from public_research import author_variants
        self.assertEqual(_page_credit(URL,page(),parse_page(page()),[TITLE],author_variants(PEOPLE))['author'],AUTHOR,'catalog aliases in both word orders are not extra coauthors')
    def test_closed_discovery_is_not_bypassed(self):
        client=Client();client.wait=True
        with self.assertRaises(ResearchWait):PublicResearch(client,leads=[])._series_litres(TITLE,AUTHOR,threading.Event(),{'remaining':6},{'sources':[]})
        self.assertEqual(client.calls,[])
    def test_conflicting_explicit_edition_positions_remain_uncertain(self):
        client=Client({URL:page(),TEXT:page(url=TEXT,position='2')})
        with self.assertRaises(EvidenceConflict):PublicResearch(client,leads=[])._series_litres(TITLE,AUTHOR,threading.Event(),{'remaining':6},{'sources':[]})
    def test_series_backfill_reaches_litres_only_after_existing_sources(self):
        from series_backfill import SeriesBackfill
        from types import SimpleNamespace
        calls=[]
        def empty(name):
            def lookup(*args):calls.append(name);return None
            return lookup
        def litres(title,author,stop,budget,result):
            self.assertEqual(budget,{'remaining':6,'lane':'series'});calls.append('litres')
            result['sources'].append({'provider':'Litres','url':URL})
            return {'provider':'litres','name':'Мистер Вечный Канун','number':'1','source_url':URL}
        backfill=object.__new__(SeriesBackfill);backfill.stop=threading.Event()
        backfill.research=SimpleNamespace(_series_goodreads=empty('goodreads'),_series_fantlab=empty('fantlab'),_series_wikidata=empty('wikidata'),_series_publisher=empty('publisher'),_series_litres=litres)
        found=backfill.lookup({'metadata':{'title':TITLE,'canonical_author':AUTHOR}})
        self.assertEqual(calls,['goodreads','fantlab','wikidata','publisher','litres'])
        self.assertEqual(found['provider'],'litres');self.assertEqual(found['receipts'],[{'provider':'Litres','url':URL}])

    def test_existing_provider_precedence_is_unchanged(self):
        research=PublicResearch(Client(),leads=[]);calls=[]
        research._series_goodreads=lambda *a: calls.append('goodreads') or {'provider':'goodreads','name':'Existing','number':'7','source_url':'https://www.goodreads.com/book/show/7'}
        research._series_litres=lambda *a: self.fail('Litres cannot override existing series source')
        found=research._gap_fill({'gaps':['series'],'fields':{'author':{'partial':False}}},TITLE,AUTHOR,threading.Event(),{'remaining':6},[],lambda *_:None,{'sources':[]})
        self.assertEqual(found['series']['provider'],'goodreads');self.assertEqual(calls,['goodreads'])

if __name__=='__main__':unittest.main()
