"""Query-free Litres edition evidence: exact book/all authors and explicit book-specific series ordinal.
Schema captured on 2026-10-28; no search crawling, list-position inference or original-language assertion.
"""
import re
import urllib.parse
from html.parser import HTMLParser


def book_url(value):
    if not isinstance(value,str):return ''
    parsed=urllib.parse.urlsplit(value)
    if parsed.scheme!='https' or parsed.netloc not in ('litres.ru','www.litres.ru') or parsed.query or parsed.fragment:return ''
    if not re.fullmatch(r'/(?:book|audiobook)/[a-z0-9-]+/[a-z0-9-]+-[1-9]\d{0,11}/',parsed.path):return ''
    return 'https://www.litres.ru'+parsed.path


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.canonical=[];self.scripts=[];self.script=None;self.series=[];self.depth=0;self.anchor=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='link' and attrs.get('rel')=='canonical':self.canonical.append(attrs.get('href',''))
        if tag=='script' and attrs.get('type')=='application/ld+json':self.script=[]
        if tag=='div':
            if self.depth:self.depth+=1
            elif attrs.get('data-testid')=='art__inSeries--title':self.series.append({'text':[],'links':[]});self.depth=1
        if self.depth and tag=='a':self.anchor={'url':attrs.get('href',''),'text':[]};self.series[-1]['links'].append(self.anchor)
    def handle_data(self,value):
        if self.script is not None:self.script.append(value)
        if self.depth:self.series[-1]['text'].append(value)
        if self.anchor is not None:self.anchor['text'].append(value)
    def handle_endtag(self,tag):
        if tag=='script' and self.script is not None:self.scripts.append(''.join(self.script));self.script=None
        if tag=='a':self.anchor=None
        if tag=='div' and self.depth:self.depth-=1


def book(raw,url):
    """Return one canonical main Book/Audiobook record, preserving all author roles; related products are not authors."""
    canonical=book_url(url)
    if not canonical or not isinstance(raw,bytes) or len(raw)>2*1024*1024:return None
    doc=Document();doc.feed(raw.decode('utf-8','strict'))
    if doc.canonical!=[canonical]:return None
    from public_research import strict_json
    records=[]
    for script in doc.scripts:
        data=strict_json(script.encode('utf-8'))
        roots=data if isinstance(data,list) else data.get('@graph',[]) if isinstance(data,dict) and '@graph' in data else [data]
        for value in roots:
            if isinstance(value,dict) and value.get('@type') in ('Book','Audiobook'):records.append(value)
    if len(records)!=1:return None
    record=records[0]
    if record.get('url')!=canonical or not isinstance(record.get('name'),str) or not record['name'].strip():return None
    authors=record.get('author')
    if not isinstance(authors,list) or not 0<len(authors)<=6:return None
    if any(not isinstance(person,dict) or person.get('@type')!='Person' or not isinstance(person.get('name'),str) or not person['name'].strip() for person in authors):return None
    names=[' '.join(person['name'].split()) for person in authors]
    if len(set(names))!=len(names):return None
    found={'provider':'litres','title':' '.join(record['name'].split()),'authors':names,'source_url':canonical,'series':None}
    if not doc.series:return found
    if len(doc.series)!=1:return None
    section=doc.series[0];position=re.fullmatch(r'\s*([1-9]\d{0,3})\s+книг[аи]?\s+из\s+([1-9]\d{0,3})\s+в\s+серии\s+.+',' '.join(' '.join(section['text']).split()),re.I)
    if not position or int(position[1])>int(position[2]) or len(section['links'])!=1:return None
    link=section['links'][0];parsed=urllib.parse.urlsplit(urllib.parse.urljoin(canonical,link['url']))
    if parsed.scheme!='https' or parsed.netloc!='www.litres.ru' or not re.fullmatch(r'/series/[a-z0-9-]+-[1-9]\d{0,11}/',parsed.path) or parsed.fragment:return None
    name=' '.join(' '.join(link['text']).split()).strip('«»')
    if not name:return None
    found['series']={'provider':'litres','name':name,'number':position[1],'source_url':canonical}
    return found
