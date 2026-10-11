"""Anonymous, bounded public research. Search results are leads, never approval evidence.
No paid connector, arbitrary host, model confidence or model-invented field is used.
"""
import base64
import datetime as dt
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import http.client
import ssl
import ipaddress
import json
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from scanner import connect
from source_identity import clues,filename_identity,norm,source_gate,text,VERSION

MAX_BYTES=2*1024*1024
APP_HOST_REQUESTS=100
APP_HOST_WINDOW=3600
APP_LIMIT_REASON='Books public research hourly host request bound reached'
LEGACY_APP_LIMIT_REASON='Books public research daily request bound reached'
SOURCE_PAUSE_REASON='Public source requested a pause; no bypass attempted'
PRIMARY_HOSTS={'ast.ru','www.oupjapan.co.jp','magazines.gorky.media','www.kodansha.co.jp','www.penguinrandomhouse.com','www.harpercollins.com','www.simonandschuster.com','www.hachettebookgroup.com','us.macmillan.com'}
RECORDING_HOSTS={'akniga.org','booklis.com','livelib.ru','av3715.ru','t.me'}
CREDIT_HOSTS=PRIMARY_HOSTS|RECORDING_HOSTS
HOSTS=CREDIT_HOSTS|{'www.wikidata.org','html.duckduckgo.com','api.fantlab.ru','fantlab.ru','openlibrary.org','covers.openlibrary.org','en.wikipedia.org','ru.wikipedia.org','ja.wikipedia.org'}

RESEARCH_VERSION='standing-17-v1'

class ResearchWait(Exception):
    def __init__(self,source,reason,retry_at,kind='source_unavailable',scope=None):
        self.source=source;self.reason=reason;self.retry_at=retry_at;self.kind=kind;self.scope=scope
        super().__init__(reason)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def allowed_url(url):
    if not isinstance(url,str) or len(url)>2048 or any(ord(c)<33 for c in url):raise ValueError('Unsupported public evidence URL')
    try:
        p=urllib.parse.urlsplit(url)
        if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443) or p.fragment:raise ValueError()
    except ValueError:raise ValueError('Unsupported public evidence URL') from None
    if p.hostname=='t.me' and not p.path.startswith('/s/'):raise ValueError('Only public creator post pages are admitted')
    return url

DNS_CODE="import json,socket,sys; print(json.dumps(socket.getaddrinfo(sys.argv[1],443,type=socket.SOCK_STREAM)))"

def _resolve(host,deadline,stop=None):
    """The Windows resolver is an owned fixed child, bounded by the fetch deadline."""
    from native_io import OwnedProcessJob
    if host not in HOSTS:raise ValueError('Unsupported resolver host')
    if stop and stop.is_set():raise InterruptedError('Automatic public research paused')
    if time.monotonic()>=deadline:raise TimeoutError('Public request deadline reached')
    child=subprocess.Popen([sys.executable,'-I','-B','-c',DNS_CODE,host],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True,creationflags=0x08000000|0x00004000|4)
    child._books_suspended=True;streams=[{},{}];threads=[]
    def drain(pipe,state):
        raw=bytearray();total=0
        try:
            while block:=pipe.read(4096):
                total+=len(block)
                if len(raw)<16384:raw.extend(block[:16384-len(raw)])
        finally:pipe.close()
        state.update(raw=bytes(raw),overflow=total>16384)
    try:
        with OwnedProcessJob(child):
            for pipe,state in zip((child.stdout,child.stderr),streams):
                thread=threading.Thread(target=drain,args=(pipe,state),daemon=True);thread.start();threads.append(thread)
            while child.poll() is None:
                if stop and stop.is_set():raise InterruptedError('Automatic public research paused')
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('Public request deadline reached')
                try:child.wait(timeout=min(.05,remaining))
                except subprocess.TimeoutExpired:pass
    finally:
        if child.poll() is None:child.terminate() # Exact owned/suspended process handle only.
        child.wait(timeout=2)
        for thread in threads:
            thread.join(2)
            if thread.is_alive():raise RuntimeError('Owned resolver output did not finish')
        for pipe in (child.stdout,child.stderr):
            if not pipe.closed:pipe.close()
    if child.returncode or any(s.get('overflow') for s in streams):raise ValueError('Public resolver unavailable')
    values=strict_json(streams[0].get('raw',b''))
    if not isinstance(values,list) or not values or len(values)>128:raise ValueError('Invalid resolver response')
    for item in values:
        if not isinstance(item,list) or len(item)!=5 or item[0] not in (socket.AF_INET,socket.AF_INET6) or item[1]!=socket.SOCK_STREAM or not isinstance(item[4],list) or len(item[4]) not in (2,4) or item[4][1]!=443:raise ValueError('Invalid resolver address')
        item[4]=tuple(item[4])
    return values

def transport(url,timeout,max_bytes,stop=None):
    """Pin the validated address to the TLS connection; never resolve a second time."""
    p=urllib.parse.urlsplit(allowed_url(url));deadline=time.monotonic()+timeout
    addresses=_resolve(p.hostname,deadline,stop)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('Public source address unavailable')
    class PinnedHTTPS(http.client.HTTPSConnection):
        def connect(self):
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Public request deadline reached')
            family,kind,protocol,_,address=addresses[0]
            native=socket.socket(family,kind,protocol)
            try:
                native.settimeout(remaining);native.connect(address)
                native.settimeout(max(.001,deadline-time.monotonic()))
                self.sock=self._context.wrap_socket(native,server_hostname=self.host)
            except BaseException:native.close();raise
    connection=PinnedHTTPS(p.hostname,443,timeout=max(.001,deadline-time.monotonic()),context=ssl.create_default_context())
    response=None
    try:
        connection.request('GET',urllib.parse.urlunsplit(('', '',p.path or '/',p.query,'')),headers={'User-Agent':'BooksArranger/automatic-public-research','Accept':'application/json,text/html;q=0.9,image/jpeg;q=0.8','Connection':'close'})
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('Public request deadline reached')
        connection.sock.settimeout(remaining)
        response=connection.getresponse()
        if response.status!=200:raise urllib.error.HTTPError(url,response.status,'Public source unavailable',response.headers,None)
        raw=bytearray()
        while response.fp is not None:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Public request deadline reached')
            # HTTPResponse owns the same socket after Connection:close detaches it.
            response.fp.raw._sock.settimeout(remaining)
            block=response.read1(min(65536,max_bytes+1-len(raw)))
            if not block:break
            raw.extend(block)
            if len(raw)>max_bytes:raise ValueError('Public response exceeds bound')
        return bytes(raw)
    finally:
        if response is not None:response.close()
        connection.close()

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.hidden=0;self.blocks=[];self.current=[];self.links=[];self.link=None
    def flush(self):
        value=' '.join(' '.join(self.current).split());self.current=[]
        if value:self.blocks.append(value[:10000])
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','style','noscript'):self.hidden+=1
        if tag in ('p','li','tr','div','h1','h2','h3','br'):self.flush()
        if tag=='a' and 'result__a' in a.get('class',''):self.link={'url':a.get('href',''),'title':''}
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'):self.hidden=max(0,self.hidden-1)
        if tag in ('p','li','tr','div','h1','h2','h3'):self.flush()
        if tag=='a' and self.link:self.links.append(self.link);self.link=None
    def handle_data(self,data):
        if not self.hidden:self.current.append(data)
        if self.link and not self.hidden:self.link['title']+=data

def parse_page(raw):
    page=Page();page.feed(raw.decode('utf-8','replace'));page.flush();return page

def phrase(value):
    words=re.findall(r'[^\W_]+',str(value).casefold().replace('ё','е'))
    return r'(?<!\w)'+r'\W+'.join(re.escape(w) for w in words)+r'(?!\w)' if words else r'(?!)'

def credited_pair(page,titles,authors):
    """Explicit adjacent credits, refusing typed translation/reader roles or contradiction."""
    separator=r'[\s.,:;–—\-()«»“”"\x27]{1,30}'
    roles=r'(?:translator|translated|translation|editor|edited|illustrator|narrator|reader|переводчик|перевод|редактор|иллюстратор|чтец|читает)'
    for block in page.blocks:
        original=block.casefold().replace('ё','е')
        # A typed conflicting author credit overrides an otherwise plausible adjacency.
        labels=re.findall(r'(?:author|автор)\s*:\s*([^.;()]+)',original)
        if labels and any(not any(_credit_matches(label,name) for name in authors) for label in labels):continue
        for title in titles:
            if not str(title).strip():continue
            for author in authors:
                if not str(author).strip():continue
                author_pattern='(?P<author>'+phrase(author)+')'
                for pattern in (author_pattern+separator+phrase(title),phrase(title)+separator+author_pattern):
                    match=re.search(pattern,original)
                    if not match:continue
                    before=original[max(0,match.start('author')-60):match.start('author')]
                    after=original[match.end('author'):match.end('author')+80]
                    if re.search(roles+r'\s*[:–—-]?\s*$',before) or re.match(r'[\s,.():;–—-]*'+roles+r'\b',after):continue
                    return {'title':title,'author':author,'excerpt':block[:1800]}
    return None

def strict_json(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('Duplicate public evidence field')
            value[key]=item
        return value
    def constant(value):raise ValueError('Nonfinite public evidence value')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)

def author_variants(names):
    values=[]
    for name in names:
        name=text(name)
        if not name:continue
        if name not in values:values.append(name)
        parts=name.split()
        if len(parts)==2 and all(re.fullmatch(r"[^\W\d_]+(?:[-'][^\W\d_]+)*",p) for p in parts):
            reverse=' '.join(reversed(parts))
            if reverse not in values:values.append(reverse)
    return values

def source_leads():
    """Known citations are discovery leads only; their fetched content must pass all gates."""
    from pathlib import Path
    path=Path(__file__).with_name('public_source_leads.json')
    raw=path.read_bytes()
    if len(raw)>65536:raise ValueError('Public citation index exceeds bound')
    values=strict_json(raw)
    if not isinstance(values,list) or len(values)>100:raise ValueError('Invalid citation index')
    return values


class PublicClient:
    def __init__(self,database,fetch=None,clock=time.time):
        self.database=database;self.fetch=fetch or transport;self.clock=clock;self.lock=threading.Lock()
        with connect(database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS public_research_cache(url TEXT PRIMARY KEY,raw TEXT,sha256 TEXT,fetched REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS public_research_requests(host TEXT,at REAL)')
            db.execute('CREATE INDEX IF NOT EXISTS public_research_requests_host_at ON public_research_requests(host,at)')
            db.execute('CREATE TABLE IF NOT EXISTS public_research_limits(host TEXT PRIMARY KEY,next_at REAL,reason TEXT)')
            db.execute('DELETE FROM public_research_cache WHERE fetched<=?',(self.clock()-7*86400,))
            db.execute('DELETE FROM public_research_requests WHERE at<?',(self.clock()-7*86400,))
    def _host_ready(self,db,host,now):
        reservations=db.execute('SELECT at FROM public_research_requests WHERE host=? AND at>? ORDER BY at',(host,now-APP_HOST_WINDOW)).fetchall()
        # If old/in-flight reservations exceed the bound, enough must expire first.
        return reservations[len(reservations)-APP_HOST_REQUESTS]['at']+APP_HOST_WINDOW if len(reservations)>=APP_HOST_REQUESTS else now
    def retry_wait(self,wait):
        """Recalculate only our known local host bound, never an external pause."""
        value=dict(wait or {});host=value.get('source')
        local=value.get('reason')==LEGACY_APP_LIMIT_REASON or (value.get('reason')==APP_LIMIT_REASON and value.get('kind')=='app_limit' and value.get('scope')=='host')
        if not local or host not in HOSTS:return value
        now=self.clock()
        with connect(self.database) as db:
            limit=db.execute('SELECT next_at,reason FROM public_research_limits WHERE host=?',(host,)).fetchone()
            host_ready=self._host_ready(db,host,now);retry=max(host_ready,limit['next_at'] if limit else now)
        if limit and limit['reason'] and limit['next_at']>now and limit['next_at']>=host_ready:
            value.update(retry_at=retry,kind='source_pause' if limit['reason']==SOURCE_PAUSE_REASON else 'source_unavailable',scope='host',reason=limit['reason'])
        else:value.update(retry_at=retry,kind='app_limit',scope='host',reason=APP_LIMIT_REASON)
        return value
    def read(self,url,stop=None,budget=None):
        url=allowed_url(url);host=urllib.parse.urlsplit(url).hostname
        if stop and stop.is_set():raise InterruptedError('Automatic processing paused')
        with self.lock:
            now=self.clock()
            with connect(self.database) as db:
                db.execute('DELETE FROM public_research_cache WHERE fetched<=?',(now-7*86400,))
                cached=db.execute('SELECT * FROM public_research_cache WHERE url=? AND fetched>?',(url,now-7*86400)).fetchone()
                if cached:
                    raw=base64.b64decode(cached['raw'],validate=True)
                    if len(raw)<=MAX_BYTES and hashlib.sha256(raw).hexdigest()==cached['sha256']:return raw
                    raise ValueError('Cached evidence changed')
                if budget is not None:
                    if budget['remaining']<=0:raise ResearchWait(host,'Public research request bound reached',now+86400,'app_limit','candidate')
                # Complete cache housekeeping before reserving the request atomically.
                db.commit()
                # Reservation is atomic across Books request threads; Comics budgets are untouched.
                db.execute('BEGIN IMMEDIATE')
                wait=db.execute('SELECT * FROM public_research_limits WHERE host=?',(host,)).fetchone()
                delay=max(0,(wait['next_at'] if wait else 0)-now)
                if delay>5:raise ResearchWait(host,wait['reason'] or 'Public source cooling down',now+delay,'source_pause' if wait['reason']==SOURCE_PAUSE_REASON else 'source_unavailable','host')
                ready=self._host_ready(db,host,now)
                if ready>now:raise ResearchWait(host,APP_LIMIT_REASON,ready,'app_limit','host')
                db.execute('INSERT INTO public_research_requests VALUES(?,?)',(host,now+delay))
                db.execute('INSERT OR REPLACE INTO public_research_limits VALUES(?,?,?)',(host,now+delay+(3 if host=='html.duckduckgo.com' else 1.1),''))
                db.execute('DELETE FROM public_research_requests WHERE at<?',(now-7*86400,))
                if budget is not None:budget['remaining']-=1
            if delay and (stop.wait(delay) if stop else time.sleep(delay)):raise InterruptedError('Automatic processing paused')
            try:
                raw=self.fetch(url,10,MAX_BYTES,stop=stop) if self.fetch is transport else self.fetch(url,10,MAX_BYTES)
                if not isinstance(raw,bytes) or len(raw)>MAX_BYTES:raise ValueError()
                if any(marker in raw[:MAX_BYTES].lower() for marker in (b'anomaly.js',b'bots use duckduckgo',b'verify you are human',b'cf-chl-',b'challenge-platform')):raise ValueError()
            except InterruptedError:raise
            except Exception as error:
                now=self.clock();http_error=isinstance(error,urllib.error.HTTPError);paused=http_error and error.code in (403,429)
                retry=now+(3600 if paused else 300)
                if http_error and error.headers:
                    after=error.headers.get('Retry-After','')
                    if not isinstance(after,str):after=''
                    try:
                        if re.fullmatch(r'\d{1,12}',after.strip()):requested=now+int(after)
                        else:
                            date=parsedate_to_datetime(after)
                            requested=date.timestamp() if date.tzinfo else date.replace(tzinfo=dt.timezone.utc).timestamp()
                        retry=max(retry,requested);paused=paused or requested>now
                    except (ValueError,TypeError,OverflowError):pass
                reason=SOURCE_PAUSE_REASON if paused else 'Public source unavailable; no bypass attempted'
                with connect(self.database) as db:
                    db.execute('BEGIN IMMEDIATE')
                    existing=db.execute('SELECT next_at,reason FROM public_research_limits WHERE host=?',(host,)).fetchone()
                    if existing and existing['next_at']>=retry:
                        retry=existing['next_at']
                        if existing['reason']:reason=existing['reason']
                    db.execute('INSERT OR REPLACE INTO public_research_limits VALUES(?,?,?)',(host,retry,reason))
                raise ResearchWait(host,reason,retry,'source_pause' if reason==SOURCE_PAUSE_REASON else 'source_unavailable','host') from None
            with connect(self.database) as db:
                db.execute('INSERT OR REPLACE INTO public_research_cache VALUES(?,?,?,?)',(url,base64.b64encode(raw).decode('ascii'),hashlib.sha256(raw).hexdigest(),self.clock()))
                db.execute('DELETE FROM public_research_cache WHERE url IN (SELECT url FROM public_research_cache ORDER BY fetched DESC LIMIT -1 OFFSET 100)')
            return raw
    def json(self,url,stop,budget):return strict_json(self.read(url,stop,budget))
    def receipt(self,url):
        with connect(self.database) as db:record=db.execute('SELECT sha256,fetched FROM public_research_cache WHERE url=?',(allowed_url(url),)).fetchone()
        if not record:raise ValueError('Fetched evidence receipt unavailable')
        return {'url':url,'sha256':record['sha256'],'retrieved_utc':dt.datetime.fromtimestamp(record['fetched'],dt.timezone.utc).isoformat().replace('+00:00','Z')}
    def wikipedia(self,query,stop,budget):
        """Fetched article revisions/references are leads, never work or recording proof."""
        if not isinstance(query,str) or not query.strip() or len(query)>500:raise ValueError('Invalid research query')
        host='ru.wikipedia.org' if re.search('[А-Яа-яЁё]',query) else ('ja.wikipedia.org' if re.search('[\u3040-\u30ff\u3400-\u9fff]',query) else 'en.wikipedia.org')
        url='https://'+host+'/w/api.php?'+urllib.parse.urlencode({'action':'query','generator':'search','gsrsearch':query,'gsrnamespace':0,'gsrlimit':2,'prop':'extlinks|langlinks|revisions','ellimit':10,'lllimit':5,'rvprop':'ids','format':'json','formatversion':2})
        data=self.json(url,stop,budget)
        if not isinstance(data,dict) or 'error' in data:raise ValueError('Wikipedia discovery unavailable')
        pages=data.get('query',{}).get('pages',[])
        if not isinstance(pages,list):raise ValueError('Malformed Wikipedia evidence')
        sources=[];leads=[]
        for page in pages[:2]:
            if not isinstance(page,dict) or type(page.get('pageid')) is not int or page.get('ns')!=0:continue
            revisions=page.get('revisions',[])
            if not isinstance(revisions,list) or not revisions or type(revisions[0].get('revid')) is not int:continue
            article='https://'+host+'/?curid='+str(page['pageid'])
            languages=[{'language':text(l.get('lang')),'title':text(l.get('title'))} for l in page.get('langlinks',[])[:5] if isinstance(l,dict)]
            sources.append(self.receipt(url)|{'url':article,'api_url':url,'kind':'encyclopedia_lead','title':text(page.get('title')),'page_id':page['pageid'],'revision_id':revisions[0]['revid'],'language_links':languages,'verified_identity':False})
            for link in page.get('extlinks',[])[:10]:
                value=link.get('url') if isinstance(link,dict) else None
                try:allowed_url(value)
                except ValueError:continue
                if urllib.parse.urlsplit(value).hostname in CREDIT_HOSTS and value not in leads:leads.append(value)
        return {'sources':sources,'leads':leads[:3]}
    def discover(self,query,stop,budget):
        if not isinstance(query,str) or not query.strip() or len(query)>500:raise ValueError('Invalid research query')
        url='https://html.duckduckgo.com/html/?'+urllib.parse.urlencode({'q':query})
        page=parse_page(self.read(url,stop,budget));result=[]
        for item in page.links[:10]:
            link=urllib.parse.urljoin('https://html.duckduckgo.com',item['url']);redirect=urllib.parse.parse_qs(urllib.parse.urlsplit(link).query).get('uddg')
            if redirect:link=redirect[0]
            try:allowed_url(link)
            except ValueError:continue
            if urllib.parse.urlsplit(link).hostname in CREDIT_HOSTS and link not in result:result.append(link)
        return result[:3]

class PublicResearch:
    def __init__(self,client,leads=None):self.client=client;self.leads=source_leads() if leads is None else leads
    def _independent_catalog(self,candidates,stop,budget,waits,progress,result):
        """Try independent work entities even when FantLab has exhausted its own budget."""
        from public_work_identity import ids,names,wikidata_work,openlibrary_matches,EvidenceConflict
        title,author=candidates[0] if candidates else ('','')
        if not title or not author:return None
        evidence=[];matches=[]
        def fetched(url):
            value=self.client.json(url,stop,budget);record=self.client.receipt(url);evidence.append(record);result['sources'].append(record|{'kind':'catalog_work','verified_identity':False});return value
        def entities(ids):
            if not ids or len(ids)>20 or any(not re.fullmatch(r'Q[1-9][0-9]{0,11}',id) for id in ids):raise ValueError('Invalid work entities')
            url='https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode({'action':'wbgetentities','ids':'|'.join(ids),'props':'labels|aliases|claims','languages':'en|ru|ja','format':'json'})
            value=fetched(url)
            records=value.get('entities') if isinstance(value,dict) else None
            if not isinstance(records,dict):raise ValueError('Malformed Wikidata work evidence')
            found={}
            for id in ids:
                entity=records.get(id,{})
                if not isinstance(entity,dict) or entity.get('id')!=id or any(not isinstance(entity.get(k,{}),dict) for k in ('labels','aliases','claims')):continue
                found[id]=entity
            return found
        progress('Wikidata','Checking independent work and original language')
        try:
            language='ru' if re.search('[А-Яа-яЁё]',title) else 'en'
            url='https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode({'action':'wbsearchentities','search':title,'language':language,'uselang':language,'type':'item','limit':5,'format':'json'})
            data=fetched(url);search=data.get('search') if isinstance(data,dict) else None
            if not isinstance(search,list):raise ValueError('Malformed Wikidata search evidence')
            ids_found=list(dict.fromkeys(r['id'] for r in search[:5] if isinstance(r,dict) and re.fullmatch(r'Q[1-9][0-9]{0,11}',str(r.get('id','')))))
            works=entities(ids_found) if ids_found else {}
            exact=[work for work in works.values() if norm(title) in {norm(v) for v in names(work)}]
            links=list(dict.fromkeys(id for work in exact for property in ('P50','P407','P31','P179') for id in ids(work,property)))
            related=entities(links) if links else {}
            for work in exact:
                match=wikidata_work(work,related,title,author,norm,_credit_matches)
                if match:matches.append(match)
        except ResearchWait as wait:waits.append(wait)
        except EvidenceConflict as error:result['reasons'].append(str(error));return None
        except (ValueError,TypeError):pass
        if len(matches)>1:
            result['reasons'].append('Independent catalogs disagree on the work identity');return None
        selected=matches[0] if matches else None
        # Open Library edition languages are deliberately not used as original-work language.
        progress('Open Library','Checking independent work and author records')
        try:
            titles=selected['work_name_alts'] if selected else [title]
            authors=selected['author_aliases'] if selected else [author]
            query=selected['work_name_orig'] if selected else title
            query_author=selected['authors'][0]['name_orig'] if selected else author
            url='https://openlibrary.org/search.json?'+urllib.parse.urlencode({'title':query,'author':query_author,'limit':5,'fields':'key,title,author_name,author_key,cover_i'})
            records=openlibrary_matches(fetched(url),titles,authors,norm,_credit_matches)
            if len(records)>1:
                result['reasons'].append('Independent catalog work identity is ambiguous');return None
            if records:
                record=records[0];work=fetched('https://openlibrary.org'+record['key']+'.json')
                if not isinstance(work,dict) or work.get('key')!=record['key'] or norm(work.get('title')) not in {norm(v) for v in titles}:raise EvidenceConflict('Open Library work identity changed')
                credits=work.get('authors',[])
                if not isinstance(credits,list) or len(credits)!=1 or not isinstance(credits[0],dict) or credits[0].get('role','author') not in ('author',None):raise EvidenceConflict('Open Library author relationship is ambiguous')
                key=credits[0].get('author',{}).get('key') if isinstance(credits[0],dict) and isinstance(credits[0].get('author'),dict) else None
                if not isinstance(key,str) or not re.fullmatch('/authors/OL[1-9][0-9]{0,11}A',key):raise ValueError('Open Library author relationship unverified')
                person=fetched('https://openlibrary.org'+key+'.json')
                if not isinstance(person,dict) or person.get('key')!=key or not any(_credit_matches(person.get('name',''),name) for name in authors):raise EvidenceConflict('Independent catalog author contradiction')
                if not selected:
                    selected={'provider':'openlibrary','work_id':record['key'],'work_name':work['title'],'work_name_orig':work['title'],'work_name_alts':[work['title']],
                        'lang_code':'','image':'','work_type_name':'book','authors':[{'type':'autor','name':person['name'],'name_orig':person['name']}],
                        'parents':{'cycles':None,'digest':{}},'work_root_saga':[],'translations':[],
                        'source_url':'https://openlibrary.org'+record['key'],'standalone_confirmed':False}
                cover=record.get('cover_i')
                if type(cover) is int and 0<cover<10**12:selected['image']='https://covers.openlibrary.org/b/id/'+str(cover)+'-L.jpg'
        except ResearchWait as wait:waits.append(wait)
        except EvidenceConflict as error:result['reasons'].append(str(error));return None
        except (ValueError,TypeError):pass
        return selected

    def _collection_lookup(self,row,data,source_url,stop,budget,result):
        """Bounded fetched table adapter: every constituent and local source must agree."""
        from collection_identity import Contents,parse_contents,bind_collection
        from standing_metadata import build_policy
        title=text(data.get('work_name') or data.get('work_name_orig'))
        work_url='https://fantlab.ru/work'+str(data['work_id'])
        raw=self.client.read(work_url,stop,budget);links=Contents();links.feed(raw.decode('utf8','replace'))
        pages=[work_url]+list(dict.fromkeys('https://fantlab.ru'+a['href'] if a['href'].startswith('/') else a['href'] for a in links.links if re.fullmatch(r'(?:https://fantlab.ru)?/edition[1-9][0-9]{0,9}',a['href'])))[:2]
        errors=[]
        for url in pages:
            raw=self.client.read(url,stop,budget)
            try:records,_=parse_contents(raw,title)
            except ValueError as error:errors.append(str(error));continue
            works={}
            for record in records:
                if stop.is_set():raise InterruptedError()
                endpoint='https://api.fantlab.ru/work/'+str(record['work_id'])+'/extended'
                value=self.client.json(endpoint,stop,budget)
                if not isinstance(value,dict):raise ValueError('Collection component evidence malformed')
                # Keep only the fields consumed by binding; full response remains deduplicated cache evidence.
                works[record['work_id']]={k:value.get(k) for k in ('work_id','work_name','work_name_orig','work_name_alts','authors','lang_code')}
                result['sources'].append(self.client.receipt(endpoint)|{'kind':'component_work','verified_identity':True,'work_id':'fantlab:'+str(record['work_id'])})
            try:collection,authors=bind_collection(row,title,records,works)
            except ValueError as error:errors.append(str(error));continue
            work={'id':'fantlab:'+str(data['work_id']),'titles':[title],'original_title':title,'author_aliases':authors,'original_language':'','work_type':'fan_assembly','policy_version':'standing-17-v1',
                'collection':collection,'collection_records':records,'collection_work_facts':works,'cover_url':''}
            review,facts,reasons=build_policy(row,work,title,authors,collection=collection)
            facts['work_ids']=[c['work_id'] for c in collection['components']]
            result.update(work=work,review=review,metadata_facts=facts,reasons=reasons)
            result['sources'].append(self.client.receipt(url)|{'kind':'collection_manifest','verified_identity':True,'collection_title':title,'component_count':len(records)})
            for field,value in {'title':title,'authors':'; '.join(authors)}.items():
                result['evidence'].append({'field':field,'cited_value':value,'source_url':url,'retrieved_utc':_stamp(),'reviewer_actor':'assistant','reviewer_identity':'Books Arranger positive component identity','basis':'Fetched self-made/network collection contents, independently fetched constituent author/work relations and exact local track title/order/source binding. No official Russian publication asserted.'})
            return result
        result['reasons']=list(dict.fromkeys(errors or ['Collection components and source order need positive evidence']))
        return result

    def lookup(self,row,root,stop=None,progress=lambda *_:None):
        stop=stop or threading.Event();budget={'remaining':12};all_clues=[c for m in row['members'] for c in clues(m,root)]
        candidates=[]
        for m in row['members']:
            p=filename_identity(m['filename']);tags={k.casefold():v for k,v in m['metadata'].get('tags',{}).items()}
            author=p.get('author') or text(tags.get('author') or tags.get('album_artist') or tags.get('artist'))
            if p.get('author') and (p['title'],author) not in candidates:candidates.append((p['title'],author))
            title=text(tags.get('album') or (tags.get('title') if len(row['members'])==1 else '') or (p['title'] if len(row['members'])==1 else ''))
            if title and (title,author) not in candidates:candidates.append((title,author))
        for m in row['members'][:1]:
            for folder in ( __import__('pathlib').Path(m['path']).parent, __import__('pathlib').Path(m['path']).parent.parent):
                if str(folder)==str(__import__('pathlib').Path(root)):continue
                parsed=filename_identity(folder.name)
                if parsed.get('author') and (parsed['title'],parsed['author']) not in candidates:candidates.append((parsed['title'],parsed['author']))
        result={'research_version':RESEARCH_VERSION,'matcher_version':VERSION,'local_clues':all_clues,'sources':[],'work':None,'review':None,'evidence':[],'reasons':[]}
        if len(candidates)>3:return result|{'reasons':['Mixed recordings in this group']}
        attempt=row.get('_research_attempt',0)
        if type(attempt) is not int or not 0<=attempt<=100000:raise ValueError('Invalid research history')
        if candidates and attempt:candidates=candidates[attempt%len(candidates):]+candidates[:attempt%len(candidates)]
        works={};waits=[]
        strong_authors={norm(c['value']) for c in all_clues if c['field']=='author' and c['kind'] in ('filename','embedded')}
        for title,author in candidates[:3]:
            progress('FantLab','Finding work and translation identity')
            try:
                url='https://api.fantlab.ru/search-works?'+urllib.parse.urlencode({'q':title,'onlymatches':1})
                records=self.client.json(url,stop,budget)
                if not isinstance(records,list):raise ValueError()
                clean_title=' '.join(re.findall(r'[^\W_]+',title))
                if not records and clean_title and clean_title!=title:
                    url='https://api.fantlab.ru/search-works?'+urllib.parse.urlencode({'q':clean_title,'onlymatches':1})
                    records=self.client.json(url,stop,budget)
                    if not isinstance(records,list):raise ValueError()
                for record in records[:5]:
                    if not isinstance(record,dict) or type(record.get('work_id')) is not int:continue
                    aliases=[record.get('name'),record.get('rusname'),record.get('altname')]
                    names=[record.get('all_autor_name'),record.get('all_autor_rusname')]
                    if norm(title) not in {norm(a) for a in aliases if a}:continue
                    id=record['work_id']
                    if not 0<id<10**10:continue
                    work_url='https://api.fantlab.ru/work/'+str(id)+'/extended'
                    work=self.client.json(work_url,stop,budget)
                    if isinstance(work,dict) and work.get('work_id')==id:works[id]=work
            except ResearchWait as wait:waits.append(wait)
            except (ValueError,TypeError,json.JSONDecodeError):pass
        if not works:
            alternate=self._independent_catalog(candidates,stop,budget,waits,progress,result)
            if alternate:works[alternate['provider']+':'+str(alternate['work_id'])]=alternate
        if len(works)!=1:
            # Still fetch primary pages even if the structured catalog is unavailable.
            for title,author in candidates[:1]:
                progress('Public publisher/journal pages','Fetching independent identity evidence')
                try:
                    leads=[]
                    try:leads=self.client.discover('"'+title+'" '+author,stop,budget)
                    except ResearchWait as wait:waits.append(wait)
                    try:
                        wiki=self.client.wikipedia('"'+title+'" '+author,stop,budget)
                        result['sources'].extend(wiki['sources'])
                        leads=list(dict.fromkeys(leads+wiki['leads']))[:3]
                    except ResearchWait as wait:waits.append(wait)
                    except (ValueError,TypeError):pass
                    for url in leads:
                        raw=self.client.read(url,stop,budget);page=parse_page(raw)
                        pair=credited_pair(page,[title],[author]) if author else None
                        result['sources'].append(_page_record(url,raw,pair))
                except ResearchWait as wait:waits.append(wait)
            reason='Sources disagree on the title or author' if len(works)>1 else 'Book identity uncertain'
            return result|{'reasons':list(dict.fromkeys(result['reasons']+[reason])),'wait':_wait(waits)}
        data=next(iter(works.values()));id=data['work_id'];provider=data.get('provider','fantlab');source_url=data.get('source_url') or 'https://fantlab.ru/work'+str(id)
        if not isinstance(data.get('authors'),list) or not isinstance(data.get('work_name_alts',[]),list) or not isinstance(data.get('parents',{}),dict):return result|{'reasons':['Book identity uncertain — malformed public evidence']}
        if any(marker in text(data.get('work_type_name')).casefold() for marker in ('antholog','collection','сборник')):
            try:return self._collection_lookup(row,data,source_url,stop,budget,result)
            except ResearchWait as wait:
                return result|{'reasons':['Collection component source unavailable'],'wait':_wait(waits+[wait])}
            except (ValueError,TypeError) as error:
                return result|{'reasons':[str(error)[:300] or 'Collection component evidence uncertain'],'wait':_wait(waits)}
        authors=[a for a in data.get('authors',[]) if isinstance(a,dict) and a.get('type')=='autor']
        titles=[data.get('work_name'),data.get('work_name_orig')]+data.get('work_name_alts',[])
        names=[a.get('name') for a in authors]+[a.get('name_orig') for a in authors]
        latin_names=[_latin_credit(a.get('name_orig')) for a in authors]
        names=author_variants(names+latin_names)
        work={'id':provider+':'+str(id),'titles':[text(v) for v in titles if v],'author_aliases':[text(v) for v in names if v],
              'cover_url':text(data.get('image')),'original_language':{'jp':'ja'}.get(text(data.get('lang_code')),text(data.get('lang_code'))),'work_type':text(data.get('work_type_name')),
              'contained_story':bool(data.get('parents',{}).get('digest')),'recording_completeness':'unknown'}
        result['work']=work
        if provider=='fantlab':result['sources'].append(self.client.receipt('https://api.fantlab.ru/work/'+str(id)+'/extended')|{'url':source_url,'api_url':'https://api.fantlab.ru/work/'+str(id)+'/extended','kind':'catalog_work','work_id':work['id']})
        primary=[]
        for title,author in candidates[:1]:
            progress('Public publisher/journal pages','Fetching independent author/work credits')
            try:
                leads=[]
                for lead in self.leads:
                    if lead.get('work_id')==work['id']:
                        for url in lead.get('urls',[]):
                            allowed_url(url)
                            if urllib.parse.urlsplit(url).hostname in CREDIT_HOSTS and url not in leads:leads.append(url)
                catalog_author=(authors[0].get('name') if re.search('[А-Яа-яЁё]',title) else _latin_credit(authors[0].get('name_orig'))) if len(authors)==1 else author
                try:
                    for url in self.client.discover(('"'+title+'" '+(catalog_author or author)) if attempt%3==0 else ('"'+title+'" '+(catalog_author or author)+' translation Russian name') if attempt%3==1 else ('"'+title+'" '+(catalog_author or author)+' audiobook translation credits'),stop,budget):
                        if url not in leads:leads.append(url)
                except ResearchWait as wait:waits.append(wait)
                # Wikipedia pages/cross-language labels remain discovery only; fetch referenced primary pages.
                if not leads or not primary:
                    progress('Wikipedia','Finding article reference leads')
                    try:
                        wiki=self.client.wikipedia('"'+title+'" '+(catalog_author or author),stop,budget)
                        result['sources'].extend(wiki['sources'])
                        for url in wiki['leads']:
                            if url not in leads:leads.append(url)
                    except ResearchWait as wait:waits.append(wait)
                    except (ValueError,TypeError):pass
                for url in leads[:4]:
                    raw=self.client.read(url,stop,budget);page=parse_page(raw);pair=credited_pair(page,work['titles'],work['author_aliases'])
                    if urllib.parse.urlsplit(url).hostname in RECORDING_HOSTS:
                        from standing_metadata import russian_source_title
                        alias=russian_source_title(row)
                        bridge=recording_alias(page,alias,work) if alias else None
                        if bridge:
                            work['titles'].append(alias);pair=bridge
                            work['recording_alias']={'title':alias,'source_url':url,'basis':bridge['excerpt']}

                    result['sources'].append(_page_record(url,raw,pair))
                    if pair:primary.append(pair|{'url':url})
            except ResearchWait as wait:waits.append(wait)
        reasons=list(result['reasons'])
        if not primary:reasons.append('Author and work not independently verified')
        primary_fact_sources={}
        if provider!='fantlab':
            from public_work_identity import primary_fields
            details=[(pair,primary_fields(pair,phrase)) for pair in primary]
            languages={facts['language'] for _,facts in details if facts['language']}
            if len(languages)>1 or languages and work['original_language'] and work['original_language'] not in languages:
                reasons.append('Original work language evidence conflicts')
            elif not work['original_language'] and len(languages)==1:
                work['original_language']=next(iter(languages));primary_fact_sources['original_language']=next(pair['url'] for pair,facts in details if facts['language'])
            standalone=[pair for pair,facts in details if facts['standalone']]
            if standalone and data.get('known_series'):
                reasons.append('Series and standalone evidence conflicts')
            elif standalone and data.get('parents',{}).get('cycles') is None:
                data['parents']['cycles']=[];primary_fact_sources['standalone']=standalone[0]['url']
        language=work['original_language']
        if language and not re.fullmatch(r'[a-z]{2,3}',language):reasons.append('Original work language evidence invalid')
        # A known conflict is held; absent language/series facts are honest unknowns.
        canonical_title=text(data.get('work_name') if language=='ru' else data.get('work_name_orig'))
        author_names=[text(a.get('name') if language=='ru' else _latin_credit(a.get('name_orig')) or a.get('name_orig') or a.get('name')) for a in authors]
        if not author_names or any(not n for n in author_names):reasons.append('Author identity unverified')
        canonical_author='; '.join(author_names)
        english_verified=False;english_title_source=None
        if language not in ('ru','en'):
            english=[]
            for tr in data.get('translations',[]):
                if isinstance(tr,dict) and tr.get('lang_code')=='en':
                    for translation in tr.get('translations',[]):
                        english.extend(text(t.get('title')) for t in translation.get('titles',[]) if isinstance(t,dict) and t.get('title'))
            english=list(dict.fromkeys(english))
            if len(english)==1:
                progress('English publisher pages','Checking published English title')
                try:
                    for url in self.client.discover('"'+english[0]+'" '+canonical_author,stop,budget):
                        raw=self.client.read(url,stop,budget);pair=credited_pair(parse_page(raw),english,work['author_aliases'])
                        result['sources'].append(_page_record(url,raw,pair))
                        if pair and urllib.parse.urlsplit(url).hostname in PRIMARY_HOSTS:
                            english_verified=True;canonical_title=english[0];primary.append(pair|{'url':url})
                            english_title_source=url;primary_fact_sources['authors']=url
                except ResearchWait as wait:waits.append(wait)
        work['original_title']=text(data.get('work_name_orig') or data.get('work_name'))
        work['full_author_verified']=bool(primary and author_names)
        work['source_surnames']=[name.split()[-1] for name in author_names if len(name.split())==2]
        work['policy_version']='standing-17-v1'
        if not canonical_title or not canonical_author:reasons.append('Canonical title or author unverified')
        if any(marker in work['work_type'].casefold() for marker in ('antholog','collection')):
            reasons.append('Collection components and source order need positive evidence')
        from standing_metadata import build_policy
        series=data.get('verified_series') or {}
        work['verified_series']=series
        review,facts,policy_reasons=build_policy(row,work,canonical_title,author_names,english_verified=english_verified,series=series.get('name',''),number=series.get('number',''))
        reasons.extend(policy_reasons)
        # Source-derived names are not asserted to be published translations.
        # Only fetched catalog aliases or an explicit translation bridge enter identity aliases.
        reasons.extend(source_gate(row,work))
        result['review']=review;result['metadata_facts']=facts
        basis='Fetched original-work/author relationship corroborated by associated author/title credit. Recording aliases and source-derived output labels do not assert an official Russian edition.'
        values={'title':work['original_title'],'authors':canonical_author}
        if language:values['original_language']=language
        if review['series']:
            values.update(series=review['series'],number=review['number'])
            primary_fact_sources.update(series=series['source_url'],number=series['source_url'])
        for field,value in values.items():
            result['evidence'].append({'field':field,'cited_value':value,'source_url':primary_fact_sources.get(field,source_url),'retrieved_utc':_stamp(),'reviewer_actor':'assistant','reviewer_identity':'Books Arranger public evidence '+VERSION,'basis':basis})
        if english_verified:
            result['evidence'].append({'field':'title','cited_value':canonical_title,'source_url':english_title_source,'retrieved_utc':_stamp(),'reviewer_actor':'assistant','reviewer_identity':'Books Arranger public evidence '+VERSION,'basis':'Published English title and author matched in the fetched associated publisher credit; separate from the original-work title.'})
        result['reasons']=list(dict.fromkeys(reasons));result['wait']=_wait(waits)
        return result

def recording_alias(page,source_title,work):
    """A fetched unofficial translation credit can bridge a source alias, not invent an edition."""
    pair=credited_pair(page,[source_title],work.get('author_aliases',[]))
    if not pair:return None
    block=pair['excerpt'].casefold().replace('ё','е')
    for original in work.get('titles',[]):
        if norm(original)==norm(source_title):continue
        if re.search(r'(?:original title|original work|название оригинала|оригинальное название|перевод (?:рассказа|романа|произведения))\s*[:–—-]?\s*[«"“]?'+phrase(original),block):return pair
    return None

def _folder_author(value):
    parts=value.split()
    # Bounded pilot: unambiguous catalog two-part personal credit; complex names stay held.
    if len(parts)!=2 or any(len(p)<2 or not re.fullmatch(r"[^\W\d_]+(?:[-'][^\W\d_]+)*",p) for p in parts):return ''
    return parts[-1]+' '+parts[0]
def _credit_matches(a,b):
    at=[norm(t) for t in re.split(r'[\s,;]+',str(a)) if norm(t)];bt=[norm(t) for t in re.split(r'[\s,;]+',str(b)) if norm(t)]
    return len(at)>=2 and all(len(t)>1 for t in at) and sorted(at)==sorted(bt)
def _stamp():return dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z')
def _page_record(url,raw,pair):return {'url':url,'kind':'recording_credit' if urllib.parse.urlsplit(url).hostname in RECORDING_HOSTS else 'publisher_or_journal','sha256':hashlib.sha256(raw).hexdigest(),'retrieved_utc':_stamp(),'credit':pair,'verified_identity':bool(pair)}
def _wait(waits):
    if not waits:return None
    wait=min(waits,key=lambda w:w.retry_at)
    return {'source':wait.source,'reason':wait.reason,'retry_at':wait.retry_at,'kind':wait.kind,'scope':wait.scope}


def _latin_credit(value):
    value=text(value)
    if not re.search('[\u3040-\u30ff\u3400-\u9fff]',value):return value
    words=re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ]+)*",value)
    return ' '.join(words) if len(words)==2 else ''
