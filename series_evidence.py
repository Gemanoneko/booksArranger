"""Conservative series-only evidence; edition collections and list order are not cycles."""
import re
import json
import urllib.parse
from html import unescape
from html.parser import HTMLParser
from public_work_identity import claims, ids, names, item, label, EvidenceConflict

NARRATIVE_TYPES={'Q1667921','Q13593966'}  # novel series; literary trilogy
EDITORIAL_TYPE='Q20655472'
WORK_TYPES={'Q7725634'}  # literary work (other work types retain the existing adapter)

def _reference(statement):
    """A reference belongs to THIS claim. Imported-from alone is not an order source."""
    references=statement.get('references',[])
    if not isinstance(references,list) or len(references)>20:return False
    for reference in references:
        snaks=reference.get('snaks',{}) if isinstance(reference,dict) else {}
        if not isinstance(snaks,dict):continue
        for prop in ('P248','P854'):
            values=snaks.get(prop,[])
            if not isinstance(values,list):continue
            for snak in values:
                if not isinstance(snak,dict) or snak.get('property')!=prop or snak.get('snaktype')!='value':continue
                value=snak.get('datavalue',{}).get('value')
                if prop=='P248' and isinstance(value,dict) and item(value.get('id')):return True
                if prop=='P854' and isinstance(value,str) and re.fullmatch(r'https://[^\s<>]{1,1800}',value):return True
    return False

def wikidata_series(work,related,title,author,title_key,same_people):
    """Exact work/all authors, explicit narrative type, referenced same-claim ordinal.

    Related labels help match the already explicit relationships; language and original
    title are independent gaps. Arbitrary reference URLs are retained, never followed.
    """
    if not isinstance(work,dict) or not item(work.get('id')) or ids(work,'P629'):return None
    if title_key(title) not in {title_key(v) for v in names(work)}:return None
    if not WORK_TYPES.intersection(ids(work,'P31')):return None
    people=ids(work,'P50')
    if not people or len(people)>6:return None
    # Require a complete bijection, not a subset of the credited people.
    import itertools
    from public_research import _people
    local=_people(author)
    if len(local)!=len(people):return None
    if not any(all(any(same_people(wanted,[alias]) for alias in names(related.get(person,{})))
                   for wanted,person in zip(local,order)) for order in itertools.permutations(people)):return None
    relations=claims(work,'P179')
    if len(relations)!=1:return None
    relation=relations[0]
    if not isinstance(relation.get('id'),str) or not relation['id'].startswith(work['id']+'$') or not _reference(relation):return None
    snak=relation.get('mainsnak',{})
    if snak.get('property')!='P179' or snak.get('snaktype')!='value':return None
    series_id=item(snak.get('datavalue',{}).get('value',{}).get('id'))
    series=related.get(series_id,{})
    types=ids(series,'P31')
    if EDITORIAL_TYPE in types or not NARRATIVE_TYPES.intersection(types):return None
    qualifiers=relation.get('qualifiers',{})
    if not isinstance(qualifiers,dict) or set(qualifiers)!={'P1545'}:return None
    ordinal=qualifiers['P1545']
    if not isinstance(ordinal,list) or len(ordinal)!=1 or not isinstance(ordinal[0],dict):return None
    ordinal=ordinal[0]
    number=ordinal.get('datavalue',{}).get('value')
    if ordinal.get('property')!='P1545' or ordinal.get('snaktype')!='value' or not isinstance(number,str) or not re.fullmatch(r'[1-9]\d{0,3}',number):return None
    name=label(series,'ru') or label(series,'en')
    if not name or type(work.get('lastrevid')) is not int or work['lastrevid']<=0 or type(series.get('lastrevid')) is not int:return None
    return {'provider':'wikidata','name':name,'number':number,'source_url':'https://www.wikidata.org/wiki/'+work['id'],
            'work_id':work['id'],'series_id':series_id,'statement_id':relation['id'],
            'work_revision':work['lastrevid'],'series_revision':series['lastrevid'],
            'references':relation['references'],'numbering_scheme':'referenced narrative-series statement'}

class PublisherDocument(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.canonical=[];self.scripts=[];self.current=None
        self.descriptions=[];self.description_depth=0
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='link' and attrs.get('rel')=='canonical':self.canonical.append(attrs.get('href'))
        if tag=='script' and attrs.get('type')=='application/ld+json':self.current=[]
        if tag=='div':
            if self.description_depth:self.description_depth+=1
            elif attrs.get('id')=='book-description-copy':self.descriptions.append([]);self.description_depth=1
    def handle_data(self,value):
        if self.current is not None:self.current.append(value)
        if self.description_depth:self.descriptions[-1].append(value)
    def handle_endtag(self,tag):
        if tag=='script' and self.current is not None:self.scripts.append(''.join(self.current));self.current=None
        if tag=='div' and self.description_depth:self.description_depth-=1

def prh_series(raw,url,title,author,title_key,same_people):
    """The publisher's Book record explicitly names the cycle and numbered novel.

    This intentionally supports the captured PRH mainEntity schema only. A position
    in breadcrumbs, recommendation cards or an edition list never authorizes order.
    """
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname!='www.penguinrandomhouse.com' or parsed.query or not re.fullmatch(r'/books/[1-9]\d{0,11}/[a-z0-9-]+/',parsed.path):return None
    if not isinstance(raw,bytes) or len(raw)>2*1024*1024:return None
    document=PublisherDocument();document.feed(raw.decode('utf-8','strict'))
    if document.canonical!=[url]:return None
    books=[]
    from public_research import strict_json,_people
    for script in document.scripts:
        data=strict_json(script.encode('utf-8'))
        if isinstance(data,dict) and data.get('@type')=='WebPage':
            book=data.get('mainEntity')
            if isinstance(book,dict) and book.get('@type')=='Book':books.append(book)
    if len(books)!=1:return None
    book=books[0];credited=book.get('author')
    if isinstance(credited,str):credited=[credited]
    elif isinstance(credited,list):credited=[value.get('name') if isinstance(value,dict) and value.get('@type')=='Person' else value for value in credited]
    if not isinstance(credited,list) or not all(isinstance(v,str) for v in credited) or not same_people(author,credited) or not same_people(', '.join(credited),_people(author)):return None
    series=book.get('isPartOf');shown=book.get('name');isbn=book.get('isbn')
    if not isinstance(series,dict) or series.get('@type')!='BookSeries' or not isinstance(shown,str) or not isinstance(isbn,str) or not re.fullmatch(r'\d{13}',isbn):return None
    name=series.get('name');series_url=series.get('url')
    if not isinstance(name,str) or not name or not isinstance(series_url,str) or not re.fullmatch(r'https://www\.penguinrandomhouse\.com/series/[A-Z0-9]{1,20}/[a-z0-9-]+',series_url):return None
    match=re.fullmatch(re.escape(name)+r':\s*(.+?)\s*\(Book ([1-9]\d{0,3})\)',shown)
    if not match or title_key(match[1])!=title_key(title):return None
    if len(document.descriptions)!=1:return None
    description=' '.join(' '.join(document.descriptions[0]).split())
    if not re.search(r'\b(?:sequel|continuation)\b',description,re.I) or not re.search(r'\bfantasy classics of\s+'+re.escape(name)+r'\s*:',description,re.I):return None
    if re.search(r'\b(?:anthology|collection|omnibus|boxed set)\b',description,re.I):return None
    return {'provider':'publisher','name':name,'number':match[2],'source_url':url,'isbn':isbn,
            'series_url':series_url,'numbering_scheme':'publisher explicitly numbered novel'}
