"""Anonymous, bounded public research. Search results are leads, never approval evidence.
No paid connector, arbitrary host, model confidence or model-invented field is used.
"""
import base64
import copy
import datetime as dt
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import http.client
import ssl
import sqlite3
import ipaddress
import json
import ntpath
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
from sqlite_retry import transaction
from source_identity import clues,filename_identity,norm,source_gate,text,VERSION
import original_titles

MAX_BYTES=2*1024*1024
APP_HOST_REQUESTS=100
APP_HOST_WINDOW=3600
# App-owned per-host pacing: (requests per rolling hour, minimum spacing in seconds).
# Raised only where the vendor publishes a limit; every other host keeps the default.
#  openlibrary.org: openlibrary.org/developers/api publishes 1 request/second for
#    requests without a contact e-mail (3/s with one). We send no e-mail, so we stay
#    under 1/s: 1.1 s spacing and at most 1800/hour.
#  itunes.apple.com: Apple's iTunes Search API page publishes "approximately 20 calls
#    per minute (subject to change)": 3.5 s spacing (about 17/min), at most 900/hour.
#  www.googleapis.com (Books): no published anonymous number; Google's documented
#    courtesy quota is about 1,000/day, so 40/hour keeps under it.
#  api.fantlab.ru, Wikimedia and DuckDuckGo publish no numeric limit: unchanged 100/hour.
#  www.goodreads.com (series pages, Sergei 2026-10-18): no API; read politely, one request every
#    5 s at most and 120 per hour, cached for 7 days like every response.
HOST_POLICY={'openlibrary.org':(1800,1.1),'itunes.apple.com':(900,3.5),'www.googleapis.com':(40,1.1),'html.duckduckgo.com':(APP_HOST_REQUESTS,3),'www.goodreads.com':(120,5.0)}
WIKIMEDIA_HOSTS={'www.wikidata.org','en.wikipedia.org','ru.wikipedia.org','ja.wikipedia.org'}
def host_policy(host):return HOST_POLICY.get(host,(APP_HOST_REQUESTS,1.1))
# 0.22.1 (backlog item 8, rulings 5 and 6): research never waits for optional fields any more; the background passes that
# fill them (series backfill, gap fill) each reserve at most BACKGROUND_SHARE of a site's hourly bound under their own
# lane, so neither can take the whole bound from research or from the other. Research may use the whole bound.
LANES=('research','series','gap')
BACKGROUND_SHARE=0.4
LANE_LIMIT_REASON='Background share of the hourly site bound reached'
# The optional fields gap_fill.GapFill fills after approval (series: series backfill).
BACKGROUND_GAPS=('original_title','author_full')
# Identify the app with a public contact, as Open Library and Wikimedia ask; no e-mail is sent.
USER_AGENT='BooksArranger/automatic-public-research (+https://github.com/Gemanoneko/booksArranger)'
CACHE_ENTRIES=5000
CACHE_BYTES=64*1024*1024
CHALLENGE_PAUSE=3600
APP_LIMIT_REASON='Books public research hourly host request bound reached'
LEGACY_APP_LIMIT_REASON='Books public research daily request bound reached'
SOURCE_PAUSE_REASON='Public source requested a pause; no bypass attempted'
CHALLENGE_REASON='Public source presented a human check; no bypass attempted'
PAUSE_REASONS=(SOURCE_PAUSE_REASON,CHALLENGE_REASON)
CHALLENGE_MARKERS=(b'anomaly.js',b'bots use duckduckgo',b'verify you are human',b'cf-chl-',b'challenge-platform')
PRIMARY_HOSTS={'ast.ru','www.oupjapan.co.jp','magazines.gorky.media','www.kodansha.co.jp','www.penguinrandomhouse.com','www.harpercollins.com','www.simonandschuster.com','www.hachettebookgroup.com','us.macmillan.com'}
RECORDING_HOSTS={'akniga.org','booklis.com','livelib.ru','av3715.ru','t.me'}
RETAIL_HOSTS={'www.litres.ru'}
CREDIT_HOSTS=PRIMARY_HOSTS|RECORDING_HOSTS|RETAIL_HOSTS
HOSTS=CREDIT_HOSTS|{'www.wikidata.org','html.duckduckgo.com','api.fantlab.ru','fantlab.ru','openlibrary.org','covers.openlibrary.org','en.wikipedia.org','ru.wikipedia.org','ja.wikipedia.org','www.googleapis.com','itunes.apple.com','www.goodreads.com','archive.org'}
# Research stages: a candidate can progress only when every stage it needs has an open source.
STAGES={'catalog':{'api.fantlab.ru','www.wikidata.org','openlibrary.org','www.googleapis.com','itunes.apple.com'},
    'discovery':{'html.duckduckgo.com','en.wikipedia.org','ru.wikipedia.org','ja.wikipedia.org'},'credit':CREDIT_HOSTS|{'fantlab.ru'}}

# 18: local agreement identity and gap-only search; older results get one fresh pass.
# standing-21-v1 (0.22.0): identity v5 and research only on change (Sergei 2026-10-24): every held or waiting book is
# researched once more under the new rules, then only when it changes.
# standing-22-v1 (0.22.1, items 9 and 10): the folder structure, a clean file-name order and the number-titled whole book; every
# held or waiting book is researched once more under them (research is local only since 0.22.1, so this costs no request).
# standing-22.2-v1 (0.22.2): co-authors and readers before a title (Senua W17, «Призрак дома на холме»), Ж as a Latin Z and
# more first names («Джек из Тени»), the original title in the file name, Latin "Given Surname" names (ruling 33): every held
# or waiting book is researched once more under them, locally.
# standing-24-v1 (0.24.0, POST-023): rulings 39, 49, 52, 58 and 59 changed in 0.22.3 and 0.23.0 without a new version, so
# 289 held books kept verdicts from before them («Джин Вулф» filed in Cyrillic). Every held or waiting book is researched
# once more under: one source folder is one book (ruling 68), repaired tags, narrator credits never a title, the author
# lookup for unknown first names, Wikidata person names and local Latin spellings, and edition volume titles
# («Хранители. Летопись первая») looked up by their book title.
RESEARCH_VERSION='standing-24-v1'
# 0.31.0 step 1d (Sergei 2026-11-22): the two local rules of step 1 (a separated volume named from its own title tag; the
# series read from the sort-album and grouping tags, R4) change what the files alone decide for a held book of two
# shapes: one held as a part of a bigger book beside files that carry its title, and one asked about the series its
# name carries. Each such book is read once more under them, from its files only: a held book makes no online request
# (_lookup returns before any), and a book the rules now settle goes on as any new book does. Not a new RESEARCH_VERSION:
# that would read every held and waiting book again and re-open the ruling-71f check of queued jobs. Measured on a copy
# of the live catalog (2026-11-22): 58 of 276 held books have these shapes.
LOCAL_RECHECK='local-031-v1'
RECHECK_PIECES=('siblings','part_title','numbered_part','part_set')

def needs_local_recheck(result):
    """True for a recorded held result of the step 1d shapes that was read before the 0.31.0 local rules."""
    if not isinstance(result,dict) or result.get('local_recheck')==LOCAL_RECHECK:return False
    hold=result.get('identity_hold') if isinstance(result.get('identity_hold'),dict) else {}
    piece=hold.get('piece') if isinstance(hold.get('piece'),dict) else {}
    ask=result.get('ask') if isinstance(result.get('ask'),dict) else {}
    # R22 (Sergei 2026-11-22): a book asked "Number unclear" is read once more too; neither question is asked any more.
    return bool(hold.get('kind')=='piece' and piece.get('piece') in RECHECK_PIECES or ask.get('why') in ('title_series','number_unclear'))

class ChallengeDetected(ValueError):pass

# 0.22.2 (a live SQLITE_BUSY stop): a catalog busy for longer than a connection waits (a regroup inside one write
# transaction took 10.3-10.5 s on the live copy) is a short wait for that book or request, never the end of a run.
CATALOG_BUSY_REASON='The catalog was busy; this book is checked again in a minute'
CATALOG_BUSY_WAIT=60
# 0.30.0 item 3 (Sergei 2026-11-18): a book whose every series source was only closed waits for its series, at most this
# many times in a row; then it is published without one as before (series backfill looks it up later).
SERIES_WAIT_REASON='Waiting for the series: its sources are busy. The app tries again by itself.'
SERIES_WAIT_LIMIT=3
# 0.31.0 step 2 (Sergei 2026-11-22, rulings R2 and R5; it replaces "the book must not wait", 0.22.1, for these fields): the
# look-up before review. Every book with a gap (no series, or a title not in Latin letters whose original title and
# language no source has named yet) asks the sources BEFORE it is reviewed or converted: the series and its number, the
# original language and title, the English title. A book may wait for the answer, bounded:
#   - the sources asked before review are LOOKUP_SOURCES. The publisher and Litres adapters need DuckDuckGo, which has
#     sat behind a human check for weeks and has supplied no series; they stay with the look-up of finished books;
#   - each source's answer is kept with the book: a source that answered is not asked about it again;
#   - the app's own hourly limits and a busy catalog are no try: the book waits for the limit and goes on from there;
#   - a source that could not be reached is tried SOURCE_TRIES times for that book (series_backfill's number, R9), the next
#     try when the source says it reopens, never sooner than LOOKUP_RETRY_MIN and never later than TRY_SPACING (6 hours:
#     R9's spacing is the cap here, not the spacing, so a ten-second network error does not hold a new book six hours);
#   - no book waits longer than LOOKUP_MAX_WAIT in all (twelve hours: R9's worst case, three tries six hours apart);
#   - then it converts as before, and the look-ups of finished books fill what is missing.
# A book held for Sergei (a review-list row) is looked up the same way, in the 'gap' lane (LANES): its look-up never takes
# the hourly bound from a book that can convert, and gap_fill's background pass goes on with it between tries.
# The numbers are product numbers Sergei may overrule; the record kept with the book carries them for the page.
LOOKUP_POLICY='lookup-before-review-031-v1'
LOOKUP_SOURCES=('fantlab','wikidata','goodreads')
LOOKUP_GAPS=('original_title','series','series_name')  # 'series_name': the English name of a series the files themselves name (R1)
LOOKUP_SERVES={'original_title':('fantlab','wikidata'),'series':('goodreads','fantlab','wikidata'),'series_name':('fantlab','wikidata')}
LOOKUP_BUDGET=12
LOOKUP_RETRY_MIN=600
LOOKUP_MAX_WAIT=12*3600
LOOKUP_WAIT_REASON='Waiting for the original title: its sources are busy. The app tries again by itself.'
LOOKUP_OUTCOMES=('answered','nothing_found','no_answer','waiting')


def catalog_busy(error):
    """True for SQLite's busy or locked answer (another connection holds the write lock)."""
    import sqlite3
    if not isinstance(error,sqlite3.OperationalError):return False
    code=getattr(error,'sqlite_errorcode',None)
    if type(code) is int and code&255 in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED):return True
    message=str(error).casefold()
    return 'database is locked' in message or 'database is busy' in message or 'database table is locked' in message


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
    if p.hostname in RETAIL_HOSTS:
        from litres_evidence import book_url
        if book_url(url)!=url:raise ValueError('Only query-free canonical Litres book pages are admitted')
    if p.hostname=='t.me' and not p.path.startswith('/s/'):raise ValueError('Only public creator post pages are admitted')
    if p.hostname=='archive.org':
        match=re.fullmatch(r'/metadata/ol_dump_(20\d{2}-\d{2}-\d{2})',p.path)
        if not match or p.query or p.port or p.netloc!='archive.org':raise ValueError('Only the dated official Open Library metadata manifest is admitted')
        try:dt.date.fromisoformat(match[1])
        except ValueError:raise ValueError('Invalid dump snapshot date') from None
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
        connection.request('GET',urllib.parse.urlunsplit(('', '',p.path or '/',p.query,'')),headers={'User-Agent':USER_AGENT,'Accept':'application/json,text/html;q=0.9,image/jpeg;q=0.8','Connection':'close'})
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
        self._dispatch_locks={};self._last_dispatch={}
        with connect(database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS public_research_cache(url TEXT PRIMARY KEY,raw TEXT,sha256 TEXT,fetched REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS public_research_requests(host TEXT,at REAL)')
            db.execute('CREATE INDEX IF NOT EXISTS public_research_requests_host_at ON public_research_requests(host,at)')
            db.execute('CREATE TABLE IF NOT EXISTS public_research_limits(host TEXT PRIMARY KEY,next_at REAL,reason TEXT)')
            # 0.22.1: the background passes' own share of each site's hourly bound (LANES); a separate table, so an older
            # version reading public_research_requests is unaffected.
            db.execute('CREATE TABLE IF NOT EXISTS public_research_lanes(host TEXT NOT NULL,at REAL NOT NULL,lane TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS public_research_lanes_lane_host_at ON public_research_lanes(lane,host,at)')
            # Small side index (url, fetched, size): expiry and eviction never read the raw
            # responses, so the shared catalog's write lock is held only for a few row edits.
            db.execute('CREATE TABLE IF NOT EXISTS public_research_cache_index(url TEXT PRIMARY KEY,fetched REAL NOT NULL,size INTEGER NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS public_research_cache_index_fetched ON public_research_cache_index(fetched)')
            db.execute('CREATE INDEX IF NOT EXISTS public_research_cache_fetched ON public_research_cache(fetched)')
            # One-time backfill for responses cached before this index existed.
            db.execute('INSERT OR IGNORE INTO public_research_cache_index SELECT url,fetched,length(raw) FROM public_research_cache WHERE url NOT IN (SELECT url FROM public_research_cache_index)')
            db.execute('DELETE FROM public_research_cache_index WHERE url NOT IN (SELECT url FROM public_research_cache)')
            self._expire(db,self.clock())
            db.execute('DELETE FROM public_research_requests WHERE at<?',(self.clock()-7*86400,))
            db.execute('DELETE FROM public_research_lanes WHERE at<?',(self.clock()-APP_HOST_WINDOW,))
    @staticmethod
    def _expire(db,now):
        # Both deletes are index range scans (fetched is indexed in both tables).
        db.execute('DELETE FROM public_research_cache WHERE fetched<=?',(now-7*86400,))
        db.execute('DELETE FROM public_research_cache_index WHERE fetched<=?',(now-7*86400,))
    @staticmethod
    def _evict(db):
        """Keep the newest responses within CACHE_ENTRIES and CACHE_BYTES, evicting in one batch
        down to 90% of the bound so this runs rarely, not on every fetch."""
        count,total=db.execute('SELECT count(*),total(size) FROM public_research_cache_index').fetchone()
        if count<=CACHE_ENTRIES and total<=CACHE_BYTES:return
        # Rare path: drop index rows whose response is already gone, then recount.
        db.execute('DELETE FROM public_research_cache_index WHERE url NOT IN (SELECT url FROM public_research_cache)')
        count,total=db.execute('SELECT count(*),total(size) FROM public_research_cache_index').fetchone()
        if count<=CACHE_ENTRIES and total<=CACHE_BYTES:return
        victims=[]
        for url,size in db.execute('SELECT url,size FROM public_research_cache_index ORDER BY fetched,url'):
            if count<=CACHE_ENTRIES*0.9 and total<=CACHE_BYTES*0.9:break
            victims.append(url);count-=1;total-=size
        for index in range(0,len(victims),500):
            batch=victims[index:index+500];marks=','.join('?'*len(batch))
            db.execute('DELETE FROM public_research_cache WHERE url IN ('+marks+')',batch)
            db.execute('DELETE FROM public_research_cache_index WHERE url IN ('+marks+')',batch)
    def _host_ready(self,db,host,now):
        reservations=db.execute('SELECT at FROM public_research_requests WHERE host=? AND at>? ORDER BY at',(host,now-APP_HOST_WINDOW)).fetchall()
        bound=host_policy(host)[0]
        # If old/in-flight reservations exceed the bound, enough must expire first.
        return reservations[len(reservations)-bound]['at']+APP_HOST_WINDOW if len(reservations)>=bound else now
    def _wikimedia_ready(self,db,now):
        """One provider across sites, including reservations made by older versions."""
        hosts=sorted(WIKIMEDIA_HOSTS);marks=','.join('?'*len(hosts))
        reservations=[r['at'] for r in db.execute('SELECT at FROM public_research_requests WHERE host IN ('+marks+') AND at>? ORDER BY at',(*hosts,now-APP_HOST_WINDOW))]
        ready=now
        if reservations:ready=max(ready,reservations[-1]+6.1)
        if len(reservations)>=100:ready=max(ready,reservations[-100]+APP_HOST_WINDOW)
        minute=[at for at in reservations if at>now-60]
        if len(minute)>=10:ready=max(ready,minute[-10]+60)
        holds=db.execute('SELECT next_at,reason FROM public_research_limits WHERE host IN ('+marks+') AND next_at>? AND reason!="" ORDER BY next_at DESC LIMIT 1',(*hosts,now)).fetchone()
        if holds:raise ResearchWait('www.wikidata.org',holds['reason'],holds['next_at'],'source_pause' if holds['reason'] in PAUSE_REASONS else 'source_unavailable','host')
        return ready
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
            value.update(retry_at=retry,kind='source_pause' if limit['reason'] in PAUSE_REASONS else 'source_unavailable',scope='host',reason=limit['reason'])
        else:value.update(retry_at=retry,kind='app_limit',scope='host',reason=APP_LIMIT_REASON)
        return value
    def _lane_ready(self,db,host,lane,now):
        """When a background lane (series backfill, gap fill) may next reserve a request at this site: each uses at most
        BACKGROUND_SHARE of the site's hourly bound (of the 100/hour Wikimedia family for its hosts). Research is never
        limited by a lane."""
        if lane=='research':return now
        family=host in WIKIMEDIA_HOSTS
        hosts=sorted(WIKIMEDIA_HOSTS) if family else [host]
        share=max(1,int((100 if family else host_policy(host)[0])*BACKGROUND_SHARE))
        marks=','.join('?'*len(hosts))
        rows=[r[0] for r in db.execute('SELECT at FROM public_research_lanes WHERE lane=? AND host IN ('+marks+') AND at>? ORDER BY at',(lane,*hosts,now-APP_HOST_WINDOW))]
        return rows[len(rows)-share]+APP_HOST_WINDOW if len(rows)>=share else now
    def read(self,url,stop=None,budget=None):
        """budget: {'remaining': n, 'lane': one of LANES (default 'research')}; remaining 0 reads the cache only."""
        url=allowed_url(url);host=urllib.parse.urlsplit(url).hostname
        lane=budget.get('lane','research') if isinstance(budget,dict) else 'research'
        if lane not in LANES:raise ValueError('Unknown public research lane')
        if stop and stop.is_set():raise InterruptedError('Automatic processing paused')
        fetching=self.__dict__.setdefault('_fetching',{})  # url -> Event: a request in flight, set once it has ended
        while True:
            pending=None;reserved=False
            with self.lock:
                now=self.clock()
                with connect(self.database) as db:
                    # 0.22.2 (the 7th SQLITE_BUSY stop since 10-11): a cache read never writes. Expiry ran here on every
                    # read, cache-only ones included, so a read waited 10 s for the write lock behind a regroup and the
                    # whole automatic run stopped. It runs at start and with each new answer (cache_fetched); an expired
                    # answer is never returned either way (fetched > now - 7 days).
                    cached=db.execute('SELECT * FROM public_research_cache WHERE url=? AND fetched>?',(url,now-7*86400)).fetchone()
                    if cached:
                        raw=base64.b64decode(cached['raw'],validate=True)
                        if len(raw)<=MAX_BYTES and hashlib.sha256(raw).hexdigest()==cached['sha256']:
                            if budget is not None:budget.setdefault('answered',set()).add(host)
                            return raw
                        raise ValueError('Cached evidence changed')
                    if budget is not None:
                        if budget['remaining']<=0:raise ResearchWait(host,'Public research request bound reached',now+86400,'app_limit','candidate')
                    # Senua's 0.22.1 review, W12: with the fetch outside the lock, a second thread (research beside a
                    # background lane) missed the cache for the same URL and reserved and fetched it again: two requests
                    # against the site's bound. It now waits for the request in flight and reads its answer from the cache.
                    pending=fetching.get(url)
                    if pending is None:
                        db.commit()
                        # Reservation is atomic across Books request threads; Comics budgets are untouched. 0.22.2: a busy
                        # catalog here is a short wait for this source (CATALOG_BUSY_WAIT), never an error that stops a run.
                        try:db.execute('BEGIN IMMEDIATE')
                        except sqlite3.OperationalError as error:
                            if not catalog_busy(error):raise
                            raise ResearchWait(host,CATALOG_BUSY_REASON,now+CATALOG_BUSY_WAIT,'source_unavailable','host') from None
                        wait=db.execute('SELECT * FROM public_research_limits WHERE host=?',(host,)).fetchone()
                        delay=max(0,(wait['next_at'] if wait else 0)-now)
                        if delay>5:raise ResearchWait(host,wait['reason'] or 'Public source cooling down',now+delay,'source_pause' if wait['reason'] in PAUSE_REASONS else 'source_unavailable','host')
                        ready=self._host_ready(db,host,now)
                        if host in WIKIMEDIA_HOSTS:
                            family_ready=self._wikimedia_ready(db,now)
                            if family_ready-now>7:raise ResearchWait(host,APP_LIMIT_REASON,family_ready,'app_limit','provider')
                            delay=max(delay,family_ready-now)
                        if ready>now:raise ResearchWait(host,APP_LIMIT_REASON,ready,'app_limit','host')
                        lane_ready=self._lane_ready(db,host,lane,now)
                        if lane_ready>now:raise ResearchWait(host,LANE_LIMIT_REASON,lane_ready,'app_limit','lane')
                        db.execute('INSERT INTO public_research_requests VALUES(?,?)',(host,now+delay))
                        db.execute('INSERT OR REPLACE INTO public_research_limits VALUES(?,?,?)',(host,now+delay+host_policy(host)[1],''))
                        db.execute('DELETE FROM public_research_requests WHERE at<?',(now-7*86400,))
                        if lane!='research':
                            db.execute('INSERT INTO public_research_lanes VALUES(?,?,?)',(host,now+delay,lane))
                            db.execute('DELETE FROM public_research_lanes WHERE at<?',(now-APP_HOST_WINDOW,))
                        reserved=True
                # Senua's 0.22.1 review, W13: the in-flight mark was set inside the block above, before its exit commits the
                # reservation; a commit that raised left the URL marked with an Event nobody sets, and every later reader of
                # that URL waited until its stop (or for ever). The mark and the budget now follow the commit, still under
                # the lock, so no reader can see the reservation without its mark.
                if reserved:
                    if budget is not None:budget['remaining']-=1
                    flight=fetching[url]=threading.Event()
            if pending is None:break
            # Another thread fetches this URL (its pacing wait and the fetch: well under a minute): its answer is cached
            # when it ends; a failed request leaves no answer, and this thread then asks for itself (and is paced).
            while not pending.wait(.25):
                if stop and stop.is_set():raise InterruptedError('Automatic processing paused')
        try:
            return self._fetch_reserved(url,host,delay,stop,budget)
        finally:
            with self.lock:
                if fetching.get(url) is flight:del fetching[url]
            flight.set()
    def _fetch_reserved(self,url,host,delay,stop,budget):
        # 0.22.1: the pacing wait and the fetch (up to 15 s) run outside the lock; the reservation above already paces the
        # site. A cached answer another thread (research) needs no longer waits behind a background pass's request.
        # 0.31.0 (Judy's spec 2.2): a caller that shows a running row (series back-fill) is told when the client only waits
        # for a site's pacing, so the row is not drawn as work that makes no progress. budget['pacing'](seconds); 0 when done.
        pacing=budget.get('pacing') if isinstance(budget,dict) and callable(budget.get('pacing')) else None
        if pacing and delay:pacing(delay)
        if delay and (stop.wait(delay) if stop else time.sleep(delay)):raise InterruptedError('Automatic processing paused')
        family='wikimedia' if host in WIKIMEDIA_HOSTS else host
        with self.lock:dispatch=self._dispatch_locks.setdefault(family,threading.Lock())
        while not dispatch.acquire(timeout=.25):
            if stop and stop.is_set():raise InterruptedError('Automatic processing paused')
        try:
            # A reservation precedes its SQLite commit and thread scheduling. Those
            # delays can compress actual starts, so also pace dispatch at the host.
            spacing=6.1 if host in WIKIMEDIA_HOSTS else host_policy(host)[1]
            remaining=self._last_dispatch.get(family,float('-inf'))+spacing-self.clock()
            if pacing and remaining>0:pacing(remaining)
            if remaining>0 and (stop.wait(remaining) if stop else time.sleep(remaining)):
                raise InterruptedError('Automatic processing paused')
            if pacing:pacing(0)
            if stop and stop.is_set():raise InterruptedError('Automatic processing paused')
            # A different URL may have reserved before the preceding request
            # received a pause. Keep that pause visible before handing off dispatch.
            hosts=sorted(WIKIMEDIA_HOSTS) if host in WIKIMEDIA_HOSTS else [host]
            marks=','.join('?' for _ in hosts)
            with connect(self.database) as db:
                wait=db.execute('SELECT next_at,reason FROM public_research_limits WHERE host IN ('+marks+') AND next_at>? AND reason!="" ORDER BY next_at DESC LIMIT 1',(*hosts,self.clock())).fetchone()
            if wait:
                raise ResearchWait(host,wait['reason'],wait['next_at'],'source_pause' if wait['reason'] in PAUSE_REASONS else 'source_unavailable','host')
            self._last_dispatch[family]=self.clock()
            raw=self.fetch(url,10,MAX_BYTES,stop=stop) if self.fetch is transport else self.fetch(url,10,MAX_BYTES)
            if not isinstance(raw,bytes) or len(raw)>MAX_BYTES:raise ValueError()
            if any(marker in raw[:MAX_BYTES].lower() for marker in CHALLENGE_MARKERS):raise ChallengeDetected()
        except (InterruptedError,ResearchWait):raise
        except Exception as error:
            now=self.clock();http_error=isinstance(error,urllib.error.HTTPError);paused=http_error and error.code in (403,429)
            # DuckDuckGo answers automated HTML queries with HTTP 202 and its anomaly
            # page: a human check. Respect it like a pause instead of retrying in 5 min.
            challenge=isinstance(error,ChallengeDetected) or (http_error and error.code==202 and host=='html.duckduckgo.com')
            retry=now+(CHALLENGE_PAUSE if challenge else 3600 if paused else 300)
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
            reason=CHALLENGE_REASON if challenge else SOURCE_PAUSE_REASON if paused else 'Public source unavailable; no bypass attempted'
            with connect(self.database) as db:
                db.execute('BEGIN IMMEDIATE')
                existing=db.execute('SELECT next_at,reason FROM public_research_limits WHERE host=?',(host,)).fetchone()
                if existing and existing['next_at']>=retry:
                    retry=existing['next_at']
                    if existing['reason']:reason=existing['reason']
                db.execute('INSERT OR REPLACE INTO public_research_limits VALUES(?,?,?)',(host,retry,reason))
            raise ResearchWait(host,reason,retry,'source_pause' if reason in PAUSE_REASONS else 'source_unavailable','host') from None
        finally:dispatch.release()
        def cache_fetched(db):
            encoded=base64.b64encode(raw).decode('ascii');fetched=self.clock()
            self._expire(db,fetched)  # 0.22.2: expiry with each new answer, in this retried transaction (never on a read)
            db.execute('INSERT OR REPLACE INTO public_research_cache VALUES(?,?,?,?)',(url,encoded,hashlib.sha256(raw).hexdigest(),fetched))
            db.execute('INSERT OR REPLACE INTO public_research_cache_index VALUES(?,?,?)',(url,fetched,len(encoded)))
            # Keep the newest responses within both an entry and a byte bound, so
            # revisits reuse evidence instead of refetching it (was 100 entries).
            self._evict(db)
        transaction(self.database,cache_fetched,stop)
        if budget is not None:budget.setdefault('answered',set()).add(host)
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
        url='https://'+host+'/w/api.php?'+urllib.parse.urlencode({'action':'query','generator':'search','gsrsearch':query,'gsrnamespace':0,'gsrlimit':2,'prop':'extlinks|langlinks|revisions','ellimit':10,'lllimit':5,'rvprop':'ids','format':'json','formatversion':2,'maxlag':5})
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
    # Sergei decision 2026-10-12. Tests of the Internet research path switch this off
    # explicitly so they keep exercising that path with locally agreeing fixtures.
    local_agreement=True
    # 0.31.0 step 2 (rulings R2 and R5): the look-up before review (LOOKUP_POLICY). Always on in the app. The identity,
    # structure and admission suites written before it switch it off with the fixture they already share
    # (tests/original_title_fixture.py), so their results stay about the rules they test.
    lookup_before_review=True
    def __init__(self,client,leads=None,local_index=None):
        from pathlib import Path
        self.client=client;self.leads=source_leads() if leads is None else leads
        self.local_index=Path(local_index) if local_index is not None else Path(client.database).parent/'openlibrary-index'
        self._watch=threading.local()  # the recording rules of a lookup() on each thread (Senua's 0.22.0 review, G6)
    def rules(self):
        """Sergei's lasting author rules (author_rules, ruling 12), read-only; None while the catalog has none. Inside
        lookup() on this thread: the recording copy, so the research knows which credits and folders it asked about."""
        watch=getattr(self.__dict__.get('_watch'),'rules',None)
        if watch is not None:return watch
        import author_rules
        database=getattr(getattr(self,'client',None),'database',None)
        return author_rules.load(database) if database else None
    def identity(self,row,root):
        """(identity record, catalog index) of one book from the files alone (v5), read-only."""
        import local_identity
        siblings,index=self._siblings(row,root)
        return local_identity.identify(row,root,siblings,index['readers'] if index else None,index,self.rules()),index
    def light_novel(self,result,row,root,typed=None):
        """0.29.0 item 4: the review files under Light Novels when Sergei says so (typed now, else saved in Edit names), else
        when the book's files are in a source folder named Light Novels or Ранобэ. A collection is never one. The key is set
        only when True, so an older review reads exactly as before."""
        review=result.get('review') if isinstance(result,dict) else None
        if not isinstance(review,dict):return result
        import light_novels,entered_names
        value=bool(typed['light_novel']) if isinstance(typed,dict) and 'light_novel' in typed else None
        database=getattr(getattr(self,'client',None),'database',None)
        if value is None and database:
            saved=entered_names.book_values(database,row)
            if 'light_novel' in saved:value=bool(saved['light_novel'])
        if value is None:value=light_novels.from_row(row,root)
        if review.get('anthology') is True:value=False
        if value:review['light_novel']=True
        else:review.pop('light_novel',None)
        return result
    def names_read(self,row,root,local=None):
        """(read, scope, record): the values the app reads for the editor (Judy 0.22.2 section 1) before Sergei's corrections,
        where a name fix from this book reaches (entered_names.scope_of), and the identity record. A collection's author
        reads Разные авторы (Judy 2: the Author field of a collection)."""
        import local_identity,entered_names
        record=local if local is not None else self.identity(row,root)[0]
        shown=local_identity.shown(record)
        series=record.get('series') or {}
        collection=bool(shown['collection'])
        import light_novels
        read={'title':shown['title'],'author':local_identity.COLLECTION_LABEL if collection else shown['author'],'series':series.get('name','') if series.get('number') else '',
              'number':series.get('number','') if series.get('name') else '','universe':record.get('universe',''),'collection':collection}
        if light_novels.from_row(row,root) and not collection:read['light_novel']=True  # 0.29.0: the folder pre-tick
        return read,entered_names.scope_of(row,shown['author'],collection),record
    def with_names(self,row,root,local,typed=None):
        """The identity record with Sergei's saved names (Edit names, entered_names) and any values typed now (typed:
        {field: value}; typed wins). Title and author become his (state entered, rulings 6a and 6b); series and number
        are his series (state entered); universe and collection are carried in record['names'] for the policy.
        record['names_digest'] is entered_names.digest_for the book (stored with the job: a job planned under other names
        never starts, AudioJobs' claim check). Unchanged when nothing may reach the book and nothing is typed."""
        import local_identity,entered_names
        import copy
        database=self.client.database
        rows=entered_names._rows(database)
        stamp=entered_names.digest_for(database,row,rows)
        found={}
        if stamp!=entered_names.NONE:
            read,scope,_=self.names_read(row,root,local)
            found=entered_names.effective(database,row,read,scope,rows)
        values={field:item['value'] for field,item in found.items()}
        values.update({field:value for field,value in (typed or {}).items() if value is not None})
        if not values and stamp==entered_names.NONE:return local
        if stamp==entered_names.NONE:read,scope,_=self.names_read(row,root,local)
        from organization import NO_AUTHOR
        record=copy.deepcopy(local)
        record['names_digest']=stamp
        if not values:
            record['names_entered']=[]
            return record
        collection=bool(values['collection']) if 'collection' in values else read['collection']
        title=local_identity.text(values.get('title',read['title']));author=local_identity.text(values.get('author',read['author']))
        if collection and author==local_identity.COLLECTION_LABEL:author=''
        changed={field for field in ('title','author') if field in values and (field in found or local_identity.text(values[field])!=local_identity.text(read[field]))}
        if title and (changed or collection!=read['collection']):
            record=local_identity.settled(local,title,author or ('' if collection else NO_AUTHOR),'entered',changed,collection=collection,rules=self.rules(),
                                          folder='\\'.join(reversed(local_identity._ancestors(row,root))))
            if collection and not record.get('route'):
                # Marked a collection by Sergei: filed under Сборники like a collection the files show.
                record['route']={'kind':'narrator_collection','signals':['entered by you'],'narrators':[],'credit':local_identity.COLLECTION_LABEL,'credit_basis':'Entered by you'}
        if 'series' in values or 'number' in values:
            name=local_identity.text(values.get('series',read['series']));number=local_identity.text(values.get('number',read['number']))
            record['series']={'name':name,'number':number,'provider':'entered'} if name and number else None
            for field,value in (('series',name),('number',number)):
                record['fields'][field]={'state':'entered' if value else 'grey','value':value if name and number else '','basis':'entered','how':'Entered by you (Sergei 2026-10-24, ruling 6a)',
                                         'sources':[{'kind':'entered by you','value':value}] if value else [],'partial':False}
            record['gaps']=[gap for gap in record.get('gaps') or [] if gap not in ('series','number')]
        names={field:local_identity.text(values[field]) for field in ('series','number','universe') if field in values}
        if names:record['names']=names
        record['names_entered']=[field for field in entered_names.FIELDS if field in found]
        record['names_digest']=stamp
        record['names_saved_utc']={field:item['saved'] for field,item in found.items() if isinstance(item.get('saved'),str)}
        return record
    def approved(self,row,root,title=None,author=None,chosen=None,names=None,retained=None):
        """Sergei's Approve (rulings 6a, 6b, 11a): the book's identity is the title and author shown on its row, his
        typed values winning (None: nothing typed; '' for the author: no author), with no Internet request, so the
        destination shown before the press is exactly the one used. An empty author files a collection under
        Сборники when the row is one, else under Без автора. chosen: the author his Same author? answer gives (not a
        typed value, Senua's 0.22.0 review m3). names (Edit names, Judy 0.22.2 section 1): the editor's series, number,
        universe and collection, over his saved names. Raises ValueError('Type a title first.')."""
        import local_identity
        from organization import NO_AUTHOR
        record,index=self.identity(row,root)
        typed_names={field:value for field,value in (names or {}).items() if field in ('series','number','universe','collection','light_novel')}
        record=self.with_names(row,root,record,typed=typed_names)
        shown=local_identity.shown(record)
        retained_fields=retained_gap_fields(row,record,retained)
        rules=self.rules()
        if retained_fields and rules is not None and hasattr(rules,'changed_for') and rules.changed_for(retained['result']):retained_fields=None
        typed=set()
        if title is not None and text(title):typed.add('title')
        if author is not None and text(author):typed.add('author')
        typed|={field for field in record.get('names_entered') or () if field in ('title','author')}
        final_title=text(title) if title is not None and text(title) else shown['title']
        final_author=text(author) if author is not None else text(chosen) if chosen is not None else shown['author']
        if not final_title:raise ValueError('Type a title first.')
        # Ruling 49 (Sergei 2026-10-27): a Russian edition of a foreign book files under its original English title, on
        # Approve as automatically (_local_lookup's preferred title); a title he typed or entered wins.
        # 0.31.0 (A1): what the look-up before review found for this held row, kept with its record (the research cache
        # forgets an answer after seven days; a review-list row may wait longer for him).
        known=retained_fields or _held_lookup_fields(row,retained,shown['title'],shown['author']) or _confirmed_corbett_fields(record,shown['title'],shown['author'])
        if known and (author is not None or chosen is not None) and not _exact_people(final_author,[shown['author']]):known=None
        english=self._english_original(record,final_title,known=known) if 'title' not in typed else None
        if english:final_title=english['english_title']
        collection=not final_author and shown['collection']
        if not final_author and not collection:final_author=NO_AUTHOR
        settled=local_identity.settled(record,final_title,final_author,'approved',typed,collection=collection,rules=self.rules(),
                                       folder='\\'.join(reversed(local_identity._ancestors(row,root))),answered=author is None and chosen is not None)
        for key in ('names','names_entered','names_digest','names_saved_utc'):
            if key in record:settled[key]=copy.deepcopy(record[key])
        if english and english.get('series') and not settled.get('series') and not {'series','number'}&(set(record.get('names_entered') or [])|set(typed_names)):
            settled['series']=dict(english['series'])  # found with the Russian title (_english_original); never his own values
            settled['gaps']=[gap for gap in settled.get('gaps') or [] if gap not in ('series','number')]
        if english:
            settled['fields']['title']=dict(settled['fields']['title'],how=settled['fields']['title']['how']+'; the English title (rulings 49 and R1) of "%s"'%shown['title'],
                                            sources=list(settled['fields']['title']['sources'])+[{'kind':'catalog original title','value':english['english_title'],'url':english.get('english_source') or english.get('source_url','')}])
        result={'research_version':RESEARCH_VERSION,'matcher_version':VERSION,'local_clues':[],'sources':[],'work':None,'review':None,'evidence':[],'reasons':[]}
        result['local_agreement']=local_identity.summary(settled)
        result=self._local_collection(row,settled,result) if collection else self._local_lookup(row,settled,threading.Event(),{'remaining':0},lambda *_:None,result,index,retained_fields=known)
        result['approval']={'title':final_title,'author':'' if collection else final_author,'typed':sorted(typed),'collection':collection,'shown':shown,
                            'names':dict(record.get('names') or {}),'entered':list(record.get('names_entered') or []),'typed_names':sorted(typed_names),
                            # R22 (Sergei 2026-11-22): a series the name only looks like, and a number the title and a source
                            # disagree on, are doubtful: treated as not found (series_certainty) and never asked. Both
                            # keys stay for the engine that read them (rulings 52, 53 and 74b); they are always False now.
                            'series_question':False,'number_question':False,
                            # The name that only looks like "Series N. Title" (local_identity.identify), for the look-up.
                            'series_hint':copy.deepcopy(record.get('series_hint'))}
        if isinstance(retained,dict) and isinstance((retained.get('result') or {}).get('lookup'),dict):
            result['lookup']=copy.deepcopy(retained['result']['lookup'])  # the look-up's record of this row, for the page (A6)
        return attach_shared_routing(self.light_novel(result,row,root,typed_names))
    def _english_original(self,record,title,known=None):
        """Rulings 49 and R1 through the one title rule (canonical_names.book_title): the catalog record the research cache
        holds for this book (no request: the same cache-only gap fill automatic filing uses, asked as automatic filing
        asks: with the identity's author, after Sergei's rules, «Grossman Lev» for «Лев Гроссман»), with 'english_title',
        when the work was not written in Russian and a source names its English title; else None (the title shown is
        filed: R3). A title in Latin letters is left as it is. known: the answers kept with the book's own record (the
        look-up of a held row, or a retained approval), used where the cache has none. The record carries 'series' when
        the book has none of its own and a source names a certain one."""
        import local_identity,canonical_names
        if local_identity.script(title)=='latin':return None
        credit=text(((record.get('fields') or {}).get('author') or {}).get('value'))
        scratch={'sources':[],'evidence':[],'reasons':[]}
        # 2026-10-29 (Tolkien): the series is asked with the same Russian title. Approve then files under the English
        # title, which the catalogs know by another record; an edition volume's series is found only by its own title.
        # The series is always read (the cache only), so a record that numbers this volume differently is recognised and
        # its English title is not used (_gap_fill_once); it is filed only where it was asked for before.
        wanted='series' in (record.get('gaps') or ()) and not record.get('series')
        try:filled=self._gap_fill(dict(record,gaps=['original_title','series']),title,credit,threading.Event(),{'remaining':0},[],lambda *_:None,scratch)
        except Exception:filled={}  # nothing known: the title shown is filed
        if known and not (filled or {}).get('doubtful'):
            for field in ('catalog','series'):
                if not filled.get(field) and known.get(field):filled[field]=copy.deepcopy(known[field])
        catalog=(filled or {}).get('catalog') or {}
        english,rule=canonical_names.book_title(text(filled.get('split_title')) or title,catalog)
        if rule!='english':return None
        found=dict(catalog,english_title=english)
        return dict(found,series=dict(filled['series'])) if wanted and isinstance(filled.get('series'),dict) and filled['series'].get('name') and filled['series'].get('number') else found
    def local_generation(self):
        from openlibrary_index import generation
        return generation(self.local_index)
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
        import manual_metadata
        entered=manual_metadata.proposals(row.get('_manual_metadata_sources',[]))
        decision=self._part_set(row,root,stop)
        if decision and decision['decision'] in ('volumes','missing'):return self._part_set_hold(row,root,decision)
        rules=self.rules()
        watch=rules.recording() if rules is not None and hasattr(rules,'recording') else None
        if self.__dict__.get('_watch') is None:self._watch=threading.local()
        self._watch.rules=watch
        try:result=self._lookup(row,root,stop,progress)
        finally:self._watch.rules=None
        # A held book is researched again when Sergei's rules change (ruling 5, option B; ruling 12); since Senua's 0.22.0
        # review (G6) only when a new rule decides one of the credits or folders this research asked about.
        result['rules_generation']=rules.generation if rules else ''
        if watch is not None:
            result.update(watch.record() if hasattr(watch,'record') else {})
        if decision:
            result['part_set']=decision
            if decision['decision']=='ask':
                # "Part of a bigger book" with the proposed order and "Approve as one book"; never joined on its own.
                import local_identity
                # 0.31.0 step 2: a wait for the look-up before review is no reason of a book held for him. The look-up's record
                # stays with the row, and gap_fill's pass goes on with it (GapFill.look_up_held).
                result['reasons']=list(dict.fromkeys([reason for reason in result.get('reasons') or [] if reason not in (SERIES_WAIT_REASON,LOOKUP_WAIT_REASON)]+[local_identity.PIECE_REASON]))
                result.pop('series_waits',None)
                hold=dict(result.get('identity_hold') or {'kind':'piece','detail':''})
                if hold.get('kind')=='piece':hold['piece']={'piece':'set','cause':decision['basis'],'parts':len(row.get('members') or []),
                                                            'hours':round(sum(float(m.get('duration') or 0) for m in row.get('members') or [])/3600,1)}
                result['identity_hold']=hold;result['wait']=None
        self._held_lookup(row,root,result,stop or threading.Event())
        if result.get('review'):result['review']['organization_policy']='books-hierarchy-v2'
        self.light_novel(result,row,root)
        from source_identity import LOCAL_SOURCE_GATE_VERSION
        result['local_source_gate_version']=LOCAL_SOURCE_GATE_VERSION
        result['local_recheck']=LOCAL_RECHECK  # 0.31.0 step 1d: read under the current local rules
        result=attach_shared_routing(result)
        if not entered:return result
        # Human values guide discovery and remain attributed evidence. They never count
        # as an independent fetched publisher/catalog or as local-file agreement.
        result['manual_metadata_sources']=copy.deepcopy(row['_manual_metadata_sources'])
        result['sources'].extend({'kind':'manual_metadata','source_id':p['id'],'provider':'Entered by you',
                                 'verified_identity':False,'fingerprint':row['fingerprint'],
                                 'values':copy.deepcopy(p['per_field_evidence']['values'])} for p in entered)
        conflicts=manual_metadata.compare_research(entered,result)
        result['manual_metadata_conflicts']=conflicts
        if conflicts:
            result['reasons']=list(dict.fromkeys(result.get('reasons',[])+['Saved manual metadata disagrees with researched identity']))
            result['metadata_holds']=[{'cause':'metadata_conflict','fields':sorted({c['field'] for c in conflicts}),
                                       'reason':'Saved manual metadata disagrees with researched identity'}]
        return result

    HELD_TRANSLATION_BUDGET=LOOKUP_BUDGET  # requests per book and visit, as research and the background gap fill have

    def _bounded_lookup(self,row,local,title,author,gaps,stop,progress,result,lane='research'):
        """0.31.0 step 2 (rulings R2 and R5; the rule and its numbers are at LOOKUP_POLICY): ask the sources about this
        book's gaps before it is reviewed or converted, bounded per book. row['_lookup'] is the record of the book's
        earlier visits (the automatic run and gap_fill's pass hand it back); a record made for another title or author is
        not continued. Returns (found, record). found: as _gap_fill, read from the research cache exactly as Approve and
        its preview read it. record, kept with the book for its next visit and for the page:
          'asked'    {'title', 'author', 'gaps'}: what is asked
          'sources'  {source: {'answered'} | {'tries', 'next', 'reason'} | {'gave_up'}}: what each source did so far
          'tries', 'limit'  the most tries any source has had for this book, and the limit (SOURCE_TRIES)
          'first_at', 'last_at', 'until', 'visits', 'requests' (this visit's), 'spacing' (the numbers, in seconds)
          'fields'   {gap: one of LOOKUP_OUTCOMES}: 'answered', 'nothing_found' (every source asked had none), 'no_answer'
                     (a source never answered within the limit) or 'waiting'
          'waiting', 'next_at', 'wait'  it waits for a source: when the next try is, and the wait as the run records it
          'ended'    '' | 'time' (LOOKUP_MAX_WAIT passed) | 'waits' (it had waited SERIES_WAIT_LIMIT times under 0.30.0's rule)
          'doubtful' the series a source named that were dropped as doubtful (series_certainty), with why
          'found'    the answers themselves with their receipts (a held row keeps them past the cache's seven days)."""
        from gap_fill import remember,settled
        from series_backfill import SOURCE_TRIES,TRY_SPACING
        now=getattr(self.client,'clock',time.time)()
        asked={'title':text(title),'author':text(author),'gaps':list(gaps)}
        prior=row.get('_lookup') if isinstance(row.get('_lookup'),dict) else {}
        same=prior.get('policy')==LOOKUP_POLICY and isinstance(prior.get('asked'),dict) and (prior['asked'].get('title'),prior['asked'].get('author'))==(asked['title'],asked['author'])
        memory={name:dict(value) for name,value in ((prior.get('sources') or {}) if same else {}).items() if name in LOOKUP_SOURCES and isinstance(value,dict)}
        first=prior['first_at'] if same and isinstance(prior.get('first_at'),(int,float)) else now
        waited=row.get('_series_waits',0);waited=waited if type(waited) is int and 0<=waited<1000 else 0
        ended='time' if now-first>=LOOKUP_MAX_WAIT else 'waits' if not same and waited>=SERIES_WAIT_LIMIT else ''
        never={'publisher','litres'}  # not asked before review (LOOKUP_SOURCES)
        idle={name for name,state in memory.items() if settled(state) or isinstance(state.get('next'),(int,float)) and state['next']>now}
        requests=0;waits=[]
        if not ended and not stop.is_set() and set(LOOKUP_SOURCES)-idle:
            budget={'remaining':LOOKUP_BUDGET,'lane':lane};scratch={'sources':[],'evidence':[],'reasons':[]}
            answer=None
            try:answer=self._gap_fill(dict(local,gaps=list(gaps),skip=tuple(sorted(never|idle))),title,author,stop,budget,waits,progress,scratch)
            except InterruptedError:raise  # a pause stops research here, as any request does
            except Exception:pass  # best effort: the book goes on with what the cache has
            requests=LOOKUP_BUDGET-budget['remaining']
            if answer is not None:remember(memory,answer,now,floor=LOOKUP_RETRY_MIN,ceiling=TRY_SPACING,tries=SOURCE_TRIES,candidate_wait=LOOKUP_RETRY_MIN)
        again={'sources':[]}
        found=self._gap_fill(dict(local,gaps=list(local.get('gaps') or gaps),skip=tuple(sorted(never))),title,author,stop,{'remaining':0},[],progress,again)
        known={(source.get('url'),source.get('api_url')) for source in result.get('sources') or []}
        result.setdefault('sources',[]).extend(source for source in again['sources'] if (source.get('url'),source.get('api_url')) not in known)
        fields={};open_sources=set()
        for gap in gaps:
            serving=[name for name in LOOKUP_SERVES.get(gap,()) if name in memory]
            unsettled=[name for name in serving if not settled(memory[name])]
            if gap not in (found.get('unfilled') or ()):fields[gap]='answered'
            elif unsettled and not ended:
                fields[gap]='waiting';open_sources.update(unsettled)
            elif unsettled or ended=='waits' or any(memory[name].get('gave_up') for name in serving):fields[gap]='no_answer'
            else:fields[gap]='nothing_found'
        waiting=bool(open_sources)
        due=[memory[name]['next'] for name in open_sources if isinstance(memory[name].get('next'),(int,float))]
        # The next visit: when the first open source is due, and every other one due within LOOKUP_RETRY_MIN of it (sources
        # that failed in one visit are due seconds apart: one visit tries them together, not one visit each).
        together=max(value for value in due if value<=min(due)+LOOKUP_RETRY_MIN) if due else None
        next_at=min(max(now+1,together) if due else now+LOOKUP_RETRY_MIN,first+LOOKUP_MAX_WAIT) if waiting else None
        base=_wait(waits) or {'source':sorted(open_sources)[0] if open_sources else 'lookup','reason':'Waiting for its next try','kind':'source_unavailable','scope':'book'}
        answers={key:copy.deepcopy(found[key]) for key in ('catalog','series','split_title') if found.get(key)}
        if answers:answers['receipts']=[dict(source) for source in again['sources'] if isinstance(source,dict) and source.get('sha256')][:12]
        next_try=max([int(memory[name].get('tries') or 0) for name in open_sources] or [0])+1 if waiting else None
        record={'policy':LOOKUP_POLICY,'asked':asked,'lane':lane,'sources':memory,'first_at':first,'last_at':now,'until':first+LOOKUP_MAX_WAIT,
                # 'next_try' of 'limit': the number of the next try and the tries in all, so "Try 2 of 3" is literally true (the
                # app's own hourly limit is no try: a book that waited only for it still has try 1 ahead). 'waiting_for': the
                # sources that are still to answer, and 'asking': the gaps that still wait.
                'next_try':next_try,'waiting_for':sorted(open_sources),'asking':[gap for gap,outcome in fields.items() if outcome=='waiting'],
                'visits':(int(prior.get('visits') or 0) if same else 0)+1,'requests':requests,
                'tries':max([int(state.get('tries') or 0) for state in memory.values()] or [0]),'limit':SOURCE_TRIES,
                'spacing':{'min_seconds':LOOKUP_RETRY_MIN,'max_seconds':TRY_SPACING,'max_wait_seconds':LOOKUP_MAX_WAIT},
                'fields':fields,'waiting':waiting,'next_at':next_at,'ended':ended,'wait':dict(base,retry_at=next_at) if waiting else None,
                'doubtful':[dict(item) for item in found.get('doubtful') or [] if isinstance(item,dict)][:6],'found':answers}
        return found,record

    def _review_lookup(self,row,local,title,author,filled,stop,progress,result):
        """The look-up before review of a book its files identify (0.31.0 step 2; it replaces the one-time lookup of a
        translation, Futaba's 0.24.0 QA B1, and 0.30.0 item 3's series wait). Every such book with a gap asks the sources
        now: the original title and language of a title not in Latin letters, and the series. Never a title Sergei
        entered or approved, never a part of a bigger book. Returns the cache's answers (filled when nothing is asked)
        with 'lookup': the book's record (_bounded_lookup), which says whether it waits."""
        import local_identity
        fields=local['fields']
        if not self.lookup_before_review or stop.is_set() or local.get('version')!=local_identity.IDENTITY_VERSION or local.get('part_book'):return filled
        his=fields['title'].get('state') in ('entered','approved') or any(s.get('kind')=='entered by you' for s in fields['title'].get('sources') or ())
        gaps=[gap for gap in LOOKUP_GAPS if gap in (filled.get('unfilled') or ()) and not (gap=='original_title' and his)]
        if not gaps:return filled
        found,record=self._bounded_lookup(row,local,title,author,gaps,stop,progress,result)
        # The 0.24.0 record of this lookup, kept for what reads it (the title and author asked, the requests made).
        result['translation_lookup']={'title':edition_volume(title)[0],'author':author,'gaps':gaps,'requests':record['requests'],
                                      'sources':[source.get('url','') for source in (record.get('found') or {}).get('receipts') or []][:8]}
        return dict(found,lookup=record)

    def held_lookup(self,row,root,prior=None,stop=None,progress=lambda *_:None):
        """The look-up before review of a book held for Sergei (a review-list row; 0.31.0 step 2, it replaces the one-time
        lookup of a held translation, 2026-10-29). The sources are asked about the book as its row shows it now: the title
        the files give and the author Approve would file it under. Nothing is filed or changed here: the row's preview and
        Approve read the answers from the research cache and from the record this returns (_held_lookup_fields). A title
        or series Sergei entered is never looked up. prior: the row's record so far (gap_fill's pass hands it back).
        Returns the record (_bounded_lookup), or {'policy', 'nothing': True, ...} when the row has nothing to ask about:
        no title or author yet, a collection, or no gap."""
        import local_identity
        from organization import NO_AUTHOR
        stop=stop or threading.Event()
        nothing={'policy':LOOKUP_POLICY,'nothing':True,'fields':{},'waiting':False,'next_at':None,'sources':{},'tries':0,'doubtful':[],'found':{}}
        try:preview=self.approved(row,root)
        except ValueError:return nothing
        approval=preview.get('approval') or {};review=preview.get('review') or {}
        shown=approval.get('shown') if isinstance(approval.get('shown'),dict) else {}
        entered=set(approval.get('typed') or [])|set(approval.get('entered') or [])|set(approval.get('names') or {})
        title=text(approval.get('title') if 'title' in entered else shown.get('title'));author=text(approval.get('author'))
        if not title or not author or author==NO_AUTHOR or approval.get('collection'):return nothing
        gaps=[]
        if 'title' not in entered and local_identity.script(title)!='latin':gaps.append('original_title')
        own=self._own_series(preview)
        if not {'series','number'}&entered and not own:gaps.append('series')
        local={'gaps':gaps,'fields':{'author':{'partial':False}},'series_hint':approval.get('series_hint')}
        if own and not {'series','number'}&entered and local_identity.script(text(review.get('series')))!='latin':
            # R1: the English name of a series the files themselves name, in case the book is a translation.
            gaps.append('series_name');local['series']={'name':text(review.get('series')),'number':text(review.get('number'))}
        if not gaps:return nothing
        _,record=self._bounded_lookup(dict(row,_lookup=prior if prior is not None else row.get('_lookup')),local,title,author,gaps,stop,progress,{'sources':[]},lane='gap')
        return record

    @staticmethod
    def _own_series(preview):
        """True when the series a preview shows is the book's own (its tags, his folders, what he entered), not one a source
        found: only a book without a series of its own has a series to look up."""
        review=preview.get('review') or {}
        if not text(review.get('series')):return False
        source=((preview.get('metadata_facts') or {}).get('series_source') or {}).get('provider')
        return source in (None,'','local','entered')

    def _held_lookup(self,row,root,result,stop):
        """A book research has just held for Sergei is looked up at once (held_lookup), so its row has the series and the
        English title when he first sees it. Best effort: any failure leaves the row as it was, and gap_fill's pass looks
        it up later."""
        if not self.lookup_before_review or not result.get('reasons') or result.get('wait') or not result.get('local_agreement') or stop.is_set():return
        try:record=self.held_lookup(row,root,None,stop)
        except Exception:return
        result['lookup']=record
        if not record.get('nothing'):
            result['translation_lookup']={'title':record['asked']['title'],'author':record['asked']['author'],'gaps':list(record['asked']['gaps']),'requests':record['requests'],
                                          'sources':[source.get('url','') for source in (record.get('found') or {}).get('receipts') or []][:8]}

    def _part_set(self,row,root,stop):
        """Rulings 19 and 19a (Sergei 2026-10-24): whole .m4b parts of one set: their chapters decide whether they are one
        book (part_sets.decide). None for any other row, an explicitly marked split book (joined) and a split book whose
        parts carry no chapters (joined as before)."""
        from pathlib import Path
        import groups,part_sets,split_books
        members=row.get('members') or []
        if len(members)<2 or not (row.get('part_set') or row.get('split_book')) or any(Path(m['path']).suffix.lower()!='.m4b' for m in members):return None
        # 0.30.0 item D: Sergei joined these parts into one book (book_join): his answer, never asked again or split by the
        # chapters (the «Впусти меня» parts each name their own work).
        if row.get('joined'):return {'decision':'join','basis':'joined by you','version':part_sets.VERSION,'parts':len(members)}
        # 0.22.1, item 9 (Sergei 2026-10-25, VanderMeer): the parts in one book folder of Sergei's structure
        # ("Annihilation\478. Книга 2. Консолидация") whose album tags all name that book are that one book, whatever the parts'
        # own titles say. Its sibling folders are the other books of the series, never parts of this one.
        import local_identity
        confirmed=part_sets.confirmed_edition(row)
        if confirmed:return confirmed
        structure=local_identity.folder_structure(row,root)
        albums={local_identity.title_key(local_identity.text(local_identity._tags(m).get('album'))) for m in members}
        if structure and structure['book']=='folder' and albums=={local_identity.title_key(structure['title'])}:
            return {'decision':'join','basis':'one book folder','version':part_sets.VERSION,'parts':len(members)}
        if row.get('split_book') and split_books.joinable_parts(members):return None
        # A split book of many files is a book's chapter files (Dan Brown's 108-155): joined as before, never probed one by one.
        if row.get('split_book') and len(members)>groups.PART_SET_MAX:return None
        chapters=part_sets.read_chapters([m['path'] for m in members],stop)
        # A split book whose parts show no chapters is joined as before; admission probes every part again and refuses
        # joining own chapters without a decision.
        if row.get('split_book') and not any(chapters.values()):return None
        return part_sets.decide(part_sets.parts_of(row,chapters))
    def _part_set_hold(self,row,root,decision):
        """Separate volumes are recorded (the catalog regroups them, each its own book, ruling 15); missing parts are a
        Missing files row naming them. Either way this candidate is held with the reason."""
        import groups
        result={'research_version':RESEARCH_VERSION,'matcher_version':VERSION,'local_clues':[],'sources':[],'work':None,'review':None,'evidence':[],'wait':None,'part_set':decision}
        if decision['decision']=='volumes':
            with connect(self.client.database) as db:groups.record_volumes(db,root,row.get('members') or [],decision['basis'])
            return result|{'reasons':['Separate books of a series'],'identity_hold':{'kind':'piece','detail':decision['basis'],'piece':{'piece':'volumes','parts':len(row.get('members') or [])}}}
        return result|{'reasons':['Parts of this book are missing'],'identity_hold':{'kind':'missing_parts','missing':list(decision.get('missing') or []),'total':decision.get('total')}}
    def _lookup(self,row,root,stop=None,progress=lambda *_:None):
        stop=stop or threading.Event();budget={'remaining':12};all_clues=[c for m in row['members'] for c in clues(m,root)]
        candidates=[]
        # A split book's parts share one book name; their own numbers and chapter labels are not titles.
        split_name=None
        if row.get('split_book'):
            from split_books import book_name
            split_name=book_name(row['members'])
        for m in row['members']:
            p=(filename_identity(split_name+'.x') if split_name else {'title':'','author':''}) if split_name is not None else filename_identity(m['filename'])
            tags={k.casefold():v for k,v in m['metadata'].get('tags',{}).items()}
            author=p.get('author') or text(tags.get('author') or tags.get('album_artist') or tags.get('artist'))
            if p.get('author') and (p['title'],author) not in candidates:candidates.append((p['title'],author))
            title=text(tags.get('album') or (tags.get('title') if len(row['members'])==1 else '') or (p['title'] if len(row['members'])==1 else ''))
            if title and (title,author) not in candidates:candidates.append((title,author))
        for m in row['members'][:1]:
            for folder in ( __import__('pathlib').Path(m['path']).parent, __import__('pathlib').Path(m['path']).parent.parent):
                if str(folder)==str(__import__('pathlib').Path(root)):continue
                parsed=filename_identity(folder.name)
                if parsed.get('author') and (parsed['title'],parsed['author']) not in candidates:candidates.append((parsed['title'],parsed['author']))
        observed_candidate_count=len(candidates)
        import manual_metadata
        entered=manual_metadata.proposals(row.get('_manual_metadata_sources',[]))
        for proposal in reversed(entered):
            title=proposal.get('title');author=proposal.get('authors') or ''
            if title and (title,author) not in candidates:candidates.insert(0,(title,author))
        result={'research_version':RESEARCH_VERSION,'matcher_version':VERSION,'local_clues':all_clues,'sources':[],'work':None,'review':None,'evidence':[],'reasons':[]}
        # Sergei decision 2026-10-12: tags, file name and folder that agree are the identity.
        # Only missing optional fields are searched; a local conflict keeps the research path.
        import local_identity
        siblings,index=self._siblings(row,root)
        if self.local_agreement:
            # Sergei 2026-10-24 (rulings 6, 6a): title + author from one local source identify the book.
            # What the files cannot settle is a question for Sergei; the Internet never decides identity
            # and a held book is not researched again until it changes (ruling 5, option B).
            local=local_identity.identify(row,root,siblings,index['readers'] if index else None,index,self.rules())
            if entered and (entered[0].get('title') or entered[0].get('authors')):
                # Ruling 6a: Sergei is a source; what he entered is the identity, with no other source needed.
                shown=local_identity.shown(local)
                title=entered[0].get('title') or shown['title'];author=entered[0].get('authors') or shown['author']
                typed={name for name,value in (('title',entered[0].get('title')),('author',entered[0].get('authors'))) if value}
                if title and (author or shown['collection']):
                    local=local_identity.settled(local,title,author,'entered',typed,collection=not author and shown['collection'],rules=self.rules(),
                                                 folder='\\'.join(reversed(local_identity._ancestors(row,root))))
            local=self.with_names(row,root,local)  # Edit names (Judy 0.22.2 section 1): his corrections come first
            if entered and (entered[0].get('series') or entered[0].get('number')):
                # R22: a series or number he saved as metadata is a local fact. A source that names another is doubtful
                # and dropped (series_certainty), so "Sources disagree" is never asked about a series.
                local=dict(local,manual_series={'series':text(entered[0].get('series')),'number':text(entered[0].get('number'))})
            result['local_agreement']=local_identity.summary(local)
            if local.get('route'):return self._local_collection(row,local,result)
            if local['accepted']:
                result=self._local_lookup(row,local,stop,budget,progress,result,index)
                if result.get('author_learned'):result=self._agreement_after_learning(row,root,siblings,index,result)
                return result
            ask=local.get('ask')
            reason=local_identity.ASK_REASONS[ask['kind']] if ask else local_identity.PIECE_REASON
            hold={'kind':ask['kind'] if ask else 'piece','detail':local.get('held') or ''}
            if not ask and local.get('piece'):hold['piece']=copy.deepcopy(local['piece'])  # the typed cause of the to-do row
            return result|{'reasons':[reason],'ask':copy.deepcopy(ask),'identity_hold':hold,'wait':None}
        local=local_identity.agreement(row,root,siblings,index['readers'] if index else None)
        result['local_agreement']=local_identity.summary(local)
        if observed_candidate_count>3:return result|{'reasons':['Mixed recordings in this group']}
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
                        pair=_page_credit(url,raw,page,[title],[author]) if author else None
                        result['sources'].append(_page_record(url,raw,pair))
                except ResearchWait as wait:waits.append(wait)
            reason='Sources disagree on the title or author' if len(works)>1 else 'Book identity uncertain'
            return result|{'reasons':list(dict.fromkeys(result['reasons']+[reason])),'wait':_wait(waits,budget.get('answered'))}
        data=next(iter(works.values()));id=data['work_id'];provider=data.get('provider','fantlab');source_url=data.get('source_url') or 'https://fantlab.ru/work'+str(id)
        if not isinstance(data.get('authors'),list) or not isinstance(data.get('work_name_alts',[]),list) or not isinstance(data.get('parents',{}),dict):return result|{'reasons':['Book identity uncertain — malformed public evidence']}
        if any(marker in text(data.get('work_type_name')).casefold() for marker in ('antholog','collection','сборник')):
            try:return self._collection_lookup(row,data,source_url,stop,budget,result)
            except ResearchWait as wait:
                return result|{'reasons':['Collection component source unavailable'],'wait':_wait(waits+[wait],budget.get('answered'))}
            except (ValueError,TypeError) as error:
                return result|{'reasons':[str(error)[:300] or 'Collection component evidence uncertain'],'wait':_wait(waits,budget.get('answered'))}
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
                    raw=self.client.read(url,stop,budget);page=parse_page(raw);pair=_page_credit(url,raw,page,work['titles'],work['author_aliases'])
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
        primary_fact_sources={};series_doubt=''
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
                # R25 (Sergei 2026-11-22; it follows R22): one source lists the book in a series and another calls it a
                # standalone book. A doubtful series is treated as not found: the book gets no series and goes on. It used
                # to be held with 'Series and standalone evidence conflicts'.
                data['verified_series']=None;series_doubt='source_conflict'
                result.setdefault('series_dropped',[]).append({'provider':text(provider),'name':'','number':'','why':'source_conflict','source_url':text(source_url)})
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
        if not reasons and not _tagged_series(row) and canonical_title and canonical_author and not series_doubt:
            # Series is optional: a source that is unavailable or unsure never holds the book.
            try:
                found=self._series_goodreads(canonical_title,canonical_author,stop,budget,result)
                if not found and not series:
                    found=self._series_fantlab(canonical_title,canonical_author,False,stop,budget,result,data if type(data.get('work_id')) is int else None)
                if found:series=found
            except (ResearchWait,ValueError,TypeError,KeyError,AttributeError):pass
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
            facts['series_source']=series_source(series)
        for field,value in values.items():
            result['evidence'].append({'field':field,'cited_value':value,'source_url':primary_fact_sources.get(field,source_url),'retrieved_utc':_stamp(),'reviewer_actor':'assistant','reviewer_identity':'Books Arranger public evidence '+VERSION,'basis':basis})
        if english_verified:
            result['evidence'].append({'field':'title','cited_value':canonical_title,'source_url':english_title_source,'retrieved_utc':_stamp(),'reviewer_actor':'assistant','reviewer_identity':'Books Arranger public evidence '+VERSION,'basis':'Published English title and author matched in the fetched associated publisher credit; separate from the original-work title.'})
        result['reasons']=list(dict.fromkeys(reasons));result['wait']=_wait(waits,budget.get('answered'))
        return result

    # ------------------------------------------------------------ local agreement
    def _siblings(self,row,root):
        """Files beside this candidate and the library's reader names, from the app's own catalog.
        Fails closed: an unreadable catalog yields the unreadable marker and holds the book."""
        from local_identity import folder_siblings,catalog_index,UNREADABLE
        database=getattr(self.client,'database',None)
        if not database:return [dict(UNREADABLE)],None
        try:return folder_siblings(database,row,root),catalog_index(database,root)
        except Exception:return [dict(UNREADABLE)],None

    def _agreement_after_learning(self,row,root,siblings,index,result):
        """Futaba's 0.22.3 QA, M-1: research that learns an author rule (ruling 39, or a cached catalog's Latin name) files
        the book by it, but the local agreement it recorded was read before the rule existed («Лев Гроссман»). The approval
        then re-derives the identity with the rule (Grossman Lev), sees the author differ and holds the book "Local identity
        evidence changed", with no question, run after run. The agreement is read again with the rules as they are now,
        the same way the approval reads it; nothing else in the result changes."""
        import local_identity,author_rules
        database=getattr(self.client,'database',None)
        rules=author_rules.load(database) if database else None
        if rules is None:return result
        relearned=self.with_names(row,root,local_identity.identify(row,root,siblings,index['readers'] if index else None,index,rules))
        if not relearned.get('accepted'):return result  # the rule changed what the files say: the next research asks
        summary=local_identity.summary(relearned)
        result['local_agreement']=summary
        facts=result.get('metadata_facts')
        if isinstance(facts,dict) and 'local_agreement' in facts:facts['local_agreement']=copy.deepcopy(summary)
        return result

    def _local_collection(self,row,local,result):
        """Ruling 1 (Sergei 2026-10-13): a collection compiled or read by a narrator, clear from two
        local signals, is filed under the collections root; the narrator is recorded only as narrator."""
        import local_identity
        from standing_metadata import build_policy
        route=local['route'];title=local['fields']['title']['value']
        credits=set(route['narrators'])|{route['credit']}
        for member in row['members']:
            tags={k.casefold():v for k,v in member['metadata'].get('tags',{}).items()}
            credits.update(text(tags.get(k)) for k in local_identity.AUTHOR_TAGS if text(tags.get(k)))
            named=filename_identity(member['filename'])
            if named.get('author'):credits.add(named['author'])
        work={'id':local_identity.work_id(local),'titles':local_identity.title_forms(local),'author_aliases':author_variants(sorted(c for c in credits if c)),
            'original_language':'','original_title':title,'policy_version':'standing-17-v1','full_author_verified':True,'source_surnames':[],'verified_series':{},
            'identity_basis':'local_agreement','cover_url':'','work_type':'','contained_story':False,'recording_completeness':'unknown'}
        if local.get('version')==local_identity.IDENTITY_VERSION:work['identity_rule']=local_identity.IDENTITY_VERSION
        collection={'kind':'narrator_collection','narrators':list(route['narrators']),'signals':list(route['signals']),'credit_basis':route['credit_basis']}
        summary=local_identity.summary(local)
        saved_names=local.get('names') or {}
        # Edit names (0.22.2; Sergei, «Протоколы SCP»): a collection in a series, with its position, files under Сборники/<Series>.
        review,facts,reasons=build_policy(row,work,title,[route['credit']],collection=collection,local=summary,series=(local.get('series') or {}).get('name','') if ('series' in saved_names or 'number' in saved_names or row.get('anthology_volume')) else '',number=(local.get('series') or {}).get('number','') if ('series' in saved_names or 'number' in saved_names or row.get('anthology_volume')) else '')
        review['narrator']='; '.join(route['narrators'])
        if 'universe' in saved_names and saved_names['universe'] is not None:review['universe']=saved_names['universe']
        elif local.get('universe'):review['universe']=local['universe']  # rulings 30 and 37
        facts['work_ids']=[work['id']]
        if 'names_digest' in local:facts['entered_names']={'digest':local['names_digest'],'fields':list(local.get('names_entered') or []),'saved_utc':dict(local.get('names_saved_utc') or {})}  # Edit names: the job's names
        reasons=list(reasons)+source_gate(row,work)
        result['work']=work
        result['sources'].insert(0,{'url':'','kind':'local_agreement','verified_identity':True,'agreement':summary})
        identity='Books Arranger local agreement '+local_identity.AGREEMENT_VERSION
        basis=('Collection compiled or read by a narrator (Sergei decision 2026-10-13): filed under the collections root. Signals: '+'; '.join(route['signals'])+
            '. Title agrees: '+summary['title']['value']+' ('+summary['title']['how']+'). Narrator recorded only as narrator: '+(', '.join(route['narrators']) or 'not named')+
            '. Author credit "'+route['credit']+'" ('+route['credit_basis']+').')
        for field,value in (('title',title),('authors',review['canonical_author'])):
            result['evidence'].append({'field':field,'cited_value':value,'source_url':'','retrieved_utc':_stamp(),'reviewer_actor':'assistant','reviewer_identity':identity,'basis':basis[:3900]})
        result.update(review=review,metadata_facts=facts,reasons=list(dict.fromkeys(reasons)),wait=None,gap_wait=None)
        return result

    def _local_lookup(self,row,local,stop,budget,progress,result,index=None,retained_fields=None):
        """Identity from agreeing local sources; the Internet fills only missing fields.

        0.22.1 (Sergei's backlog item 8; rulings 5 and 6): the book is approved on its local identity at once. Its missing
        fields come from answers already in the research cache only: no request is made and nothing waits or defers the
        book. The gaps nothing answered are recorded (metadata_facts gap_search 'background') and filled later by the
        background pass (gap_fill.GapFill; series positions by series backfill). It used to wait 5-7 s per site, plus
        downloads, and to defer the book up to 3 times while sources cooled down.

        0.31.0 step 2 (rulings R2 and R5; they replace "nothing waits" for the series and the original title): a research
        pass asks the sources about those two gaps before the book is filed (_review_lookup), and the book may wait for the
        answer, bounded (LOOKUP_POLICY). Approve and its preview (budget 0) still read the cache only."""
        import local_identity,canonical_names
        from standing_metadata import build_policy
        fields=local['fields'];title=fields['title']['value'];author=fields['author']['value']
        # 0.31.0 step 3 (R1): a series the book's own files name in letters other than Latin (its tags, its title tag,
        # a folder) is asked about for its English name, in case the book is a translation ('series_name'). Never a
        # series he typed or saved: that name is his and is never renamed.
        own_series=local.get('series') if isinstance(local.get('series'),dict) else {}
        his_series=own_series.get('provider')=='entered' or bool({'series','number'}&(set(local.get('names_entered') or [])|set(local.get('names') or {})))
        asked=dict(local,gaps=list(local['gaps'])+['series_name']) if own_series.get('name') and own_series.get('number') and not his_series \
            and local_identity.script(own_series['name'])!='latin' and not local.get('part_book') else local
        waits=[];filled=self._gap_fill(asked,title,author,stop,{'remaining':0},[],progress,result) if asked['gaps'] else {'closed':[],'unfilled':[]}
        confirmed = _confirmed_corbett_fields(local,title,author)
        durable = retained_fields or confirmed
        def kept(filled):
            # The answers kept with the book itself (a retained approval, a held row's look-up, a confirmed decision) fill
            # what the cache no longer has; never beside a series this read dropped as doubtful.
            if durable and not filled.get('doubtful'):
                for field in ('catalog','series'):
                    if not filled.get(field) and durable.get(field):filled[field]=copy.deepcopy(durable[field])
                filled['unfilled']=[gap for gap in filled.get('unfilled',[]) if not (gap=='original_title' and filled.get('catalog') and not filled.get('english_pending') or gap=='series' and filled.get('series'))]
            return filled
        filled=kept(filled)
        if durable and not filled.get('doubtful'):result['sources'].extend(copy.deepcopy(durable.get('retained_sources') or []))
        if budget.get('remaining',0)>0:filled=kept(self._review_lookup(row,asked,title,author,filled,stop,progress,result))
        catalog=filled.get('catalog') or {}
        language=catalog.get('language','')
        # The part after the series and number of a name that only looks like "Series N. Title", once a source has
        # confirmed that series for it (_gap_fill): the book's own title. Else the title the files give.
        split=text(filled.get('split_title'))
        titles=local_identity.title_forms(local)
        if split and split not in titles:titles.append(split)
        part=local.get('part_book')
        if part and part['set_title'] not in titles:
            # One part of a multi-part set, its own book (Sergei 2026-10-13): the set's album is
            # its parent work and a valid source title.
            titles.append(part['set_title'])
        authors=local_identity.author_forms(local)
        if retained_fields:
            titles += [value for value in (retained_fields.get('retained_work') or {}).get('titles',[]) if value not in titles]
            authors += [value for value in (retained_fields.get('retained_work') or {}).get('author_aliases',[]) if value not in authors]
        local_script=local_identity.script(author)
        rules=self.rules()
        if language!='ru' and local_script=='cyrillic' and local_identity.foreign_given(author) and rules is not None and rules.keep(author):
            # Rulings 58/59: an old keep is not permission to file a foreign author in Cyrillic.
            # A Russian original still keeps Cyrillic; otherwise the existing English lookup/question runs below.
            fields=dict(fields,author=dict(fields['author'],rule=''))
        names=[author]
        name_source=''
        # Futaba's 0.22.2 QA, M-1 (rulings 6a and 33): an author Sergei typed or picked on the row ("Entered by you",
        # settled()) is his answer. Its spelling and script decide the folder: «Марченко Илья» chosen for the credit
        # "Ilya Marchenko" files in Cyrillic. Neither a catalog nor the library's other spellings replace it; only the
        # order is the library's (surname first, ruling 3). His same_as rules were applied before (settled()).
        typed_author=any(source.get('kind')=='entered by you' for source in fields['author'].get('sources') or ())
        if typed_author:
            pass
        elif catalog and language and not fields['author'].get('rule'):
            # Futaba's 0.24.0 QA, B1 (Tolkien): an author a rule names (Sergei's, or one research learned for this credit)
            # keeps the rule's spelling. The catalog's own form of the same person ("J. R. R. Tolkien") replaced it, so one
            # author filed under both "Tolkien J. R. R" and "J. R. R. Tolkien" (rulings 3 and 33: one spelling, surname first).
            names=[catalog['author_native'] if language=='ru' else catalog['author_latin'] or catalog['author_native']]
            name_source=catalog['source_url']
        elif filled.get('author_full'):
            names=[filled['author_full']['name']];name_source=filled['author_full']['source_url']
        elif catalog and fields['author'].get('partial'):
            chosen=catalog['author_native'] if local_script=='cyrillic' else catalog['author_latin']
            if chosen:names=[chosen];name_source=catalog['source_url']
        names=[text(n) for n in names if text(n)]
        reasons=[]
        one_source=local.get('version')==local_identity.IDENTITY_VERSION
        if not names or len(local_identity.words(names[0]))<2 and fields['author'].get('partial') and not one_source:
            # v5 (Sergei 2026-10-24): a one-word author ("Баошу") is an author; a full name is optional.
            reasons.append('Author full name not established')
            names=names or [author]
        # Futaba's 0.22.2 QA, m-2 (ruling 39): the research cache's catalog record of a foreign work names its author in
        # Latin while the files credit him only in Cyrillic ("Lev Grossman" for «Лев Гроссман»). That is the English
        # spelling ruling 39 looks up: filed surname first (ruling 33) and learned as a lasting rule for the credit, so his
        # other books (no record of their own) follow, and no Cyrillic folder of the library or spelling vote replaces it.
        # It used to take the vote or the library's Cyrillic folder, and no rule was learned.
        if one_source and not reasons and not typed_author and language and language!='ru' and not fields['author'].get('rule') \
                and fields['author'].get('state') not in ('entered','approved') and local_script=='cyrillic' and names \
                and names[0]==text(catalog.get('author_latin')) and local_identity.script(names[0])=='latin':
            ruled=self.rules()
            if ruled is not None and ruled.taken_back(author):
                names=[author]  # he took this match back: ruling 39's question asks him (below), the catalog never decides again
            else:
                # Futaba's 0.24.0 QA, B1: ruling 39's first step comes first here too. A Latin spelling the library itself
                # holds for this person (a folder of the book, an author it files: _local_latin) wins over the catalog's
                # own form ("J. R. R. Tolkien" over FantLab's "John Ronald Reuel Tolkien"), as in the lookup below.
                known=[spelling for spelling,_ in (ruled.known_authors.values() if ruled is not None else [])]
                own=_local_latin(author,folders=_ancestor_folders(row),known=known)
                cited=own['source_url'] if own else catalog.get('source_url','')
                latin=_latin_surname_first(own['name'] if own else names[0],author,None if own else _order_evidence(catalog))
                self._learn_author('same_as',author,latin,cited,title)
                result['author_learned']={'credit':author,'name':latin,'source_url':cited}
                if latin not in authors:authors.append(latin)
                names=[latin];fields=dict(fields,author=dict(fields['author'],rule='catalog-latin'))
        elif one_source and not reasons and not typed_author and budget.get('remaining',0)>0 and fields['author'].get('rule') and text(catalog.get('author_latin')):
            # 0.31.0 step 3 (Sergei 2026-11-22, "Cixin Liu"): a rule research itself learned by the old guess (a two-word
            # name turned around without evidence) is corrected when this book's own catalog record shows the order on
            # evidence (canonical_names.latin_order). Only a rule the app learned (actor 'assistant'), only the same
            # words in another order, never Sergei's own answer; the newest rule for the credit wins (author_rules).
            ruled=self.rules()
            learned=next((r for r in (ruled.rules if ruled is not None else []) if r.get('kind')=='same_as' and r.get('actor')=='assistant'
                          and text(r.get('target')).casefold()==text(author).casefold() and text(r.get('credit_as_seen'))),None)
            if learned and canonical_names._order_key(catalog['author_latin'])==canonical_names._order_key(author):
                ordered,why=canonical_names.latin_order(catalog['author_latin'],learned['credit_as_seen'],_order_evidence(catalog))
                if why!=canonical_names.ORDER_UNKNOWN and ordered!=text(author) and canonical_names._order_key(ordered)==canonical_names._order_key(author):
                    self._learn_author('same_as',learned['credit_as_seen'],ordered,catalog.get('source_url',''),title)
                    result['author_learned']={'credit':learned['credit_as_seen'],'name':ordered,'source_url':catalog.get('source_url',''),'corrected':text(author),'why':why}
                    if ordered not in authors:authors.append(ordered)
                    names=[ordered]
        spelling=None
        from organization import NO_AUTHOR
        rules=self.rules() if one_source else None
        if one_source and not reasons and not fields['author'].get('rule') and names[0]!=NO_AUTHOR and fields['author'].get('state') not in ('entered','approved'):
            spelled,_=local_identity.canonical_author(names[0],authors+names,index,language)
            # Futaba's 0.22.1 QA, m-14 (Judy 0.22.2 section 8): a credit with underscores ("Robert_Heinlein") is asked, shown,
            # remembered and filed without them; the rule's credit key is the same either way.
            if '_' in spelled:spelled=local_identity.text(spelled.replace('_',' '))
            question=local_identity.same_author_question(spelled,authors+names,rules)
            if question and question['kind']=='merge':
                # Same full name as an author the library has: that folder (the language rule's answer).
                names=[question['existing']];question=None;fields=dict(fields,author=dict(fields['author'],rule='known-author'))
            if question:
                # Ruling 12: a new folder name that looks like an author the library has is asked once; the answer is a rule.
                question['fields']={'title':{'proposal':title,'basis':fields['title'].get('basis','')},'author':{'proposal':question['new'] if '_' in names[0] else names[0],'basis':fields['author'].get('basis','')}}
                return result|{'reasons':[local_identity.ASK_REASONS['same_author']],'ask':question,'identity_hold':{'kind':'same_author','detail':''},'wait':None,
                               'rules_generation':rules.generation if rules else ''}
        if not reasons and names[0]!=NO_AUTHOR and not fields['author'].get('rule') and typed_author:
            # M-1: his spelling, surname first. (The vote below took the library's Latin "Ilya Marchenko" over it.)
            chosen,order=local_identity.surname_first(names[0])
            spelling={'chosen':chosen,'spelling':names[0],'why':'entered by you (rulings 6a and 33): your spelling decides the folder','order':order,'counts':[[names[0],1]]}
            names=[chosen]
        elif not reasons and names[0]!=NO_AUTHOR and not fields['author'].get('rule'):
            # Ruling 3 (Sergei 2026-10-13): one canonical spelling per author across the library.
            canonical,spelling=local_identity.canonical_author(names[0],authors+names,index,language)
            if spelling['spelling']!=names[0] or canonical!=names[0]:
                # Reordering keeps the citation; a different local spelling is cited as local.
                if local_identity.text(spelling['spelling'])!=local_identity.text(names[0]):name_source=''
                names=[canonical]
            if spelling.get('confirmed_by'):
                # v0.15.0: the library-wide confirmed spelling cites its fetched catalog page.
                name_source=spelling['confirmed_by'][0]
        for value in (catalog.get('original_title'),catalog.get('title_native')):
            if value and value not in titles:titles.append(value)
        for value in names+([catalog.get('author_native'),catalog.get('author_latin')] if catalog else []):
            if value and value not in authors:authors.append(value)
        series=dict(local['series']) if local['series'] else dict(filled.get('series') or {})
        saved_names=local.get('names') or {}
        if 'series' in saved_names or 'number' in saved_names:
            # Edit names (Judy 0.22.2 section 1): his series and number (with_names); an empty series makes the book standalone.
            series=dict(local['series']) if local.get('series') else {}
        # R1: the English name of a series the files themselves name, where a source gave it (the work is the files' own:
        # work['verified_series'] below keeps their name; the review and the folder carry the English one).
        named=filled.get('series_english') if isinstance(filled.get('series_english'),dict) else None
        filed_series=dict(series)
        if named and text(named.get('name')) and own_series.get('name') and not his_series and language not in ('','ru'):
            filed_series=dict(series,name=text(named['name']),name_rule='english',name_provider=text(named.get('provider')),name_url=text(named.get('source_url')),name_local=text(series.get('name')))
        work_ids=[catalog['work_id']] if catalog.get('work_id') else [local_identity.work_id(local)]
        work={'id':work_ids[0],'titles':titles,'author_aliases':author_variants(authors),'original_language':language,
            'original_title':(catalog.get('original_title') or split or title) if language else split or title,'policy_version':'standing-17-v1','full_author_verified':True,
            'source_surnames':[],'verified_series':series,'identity_basis':'local_agreement','cover_url':'','work_type':'','contained_story':False,
            'recording_completeness':'unknown','part_book':bool(part)}
        if one_source:
            work['identity_rule']=local_identity.IDENTITY_VERSION
            # Rulings 13 and 15: a numbered part filed as its own book under "set name + number".
            if fields['title'].get('basis')=='number_rule':work['numbered_part']=True
        # 0.31.0 step 3 (rulings R1 and R3): the one title rule. A Russian original keeps its Russian title, any other
        # original language gets the English title a source names, and with none found the title in the files stays and
        # nobody is asked. His own title is never replaced.
        his_title=fields['title'].get('state') in ('entered','approved')
        preferred,title_rule=canonical_names.book_title(title if his_title else split or title,catalog,his=his_title)
        sergei=fields['title'].get('state') in ('entered','approved') or fields['author'].get('state') in ('entered','approved')
        folders={name for member in row.get('members') or [] for name in (ntpath.basename(ntpath.dirname(member['path'])),ntpath.basename(ntpath.dirname(ntpath.dirname(member['path']))))}
        # R22 (Sergei 2026-11-22): a title that only looks like a series name and number is no longer asked about
        # ("Title unclear"): the doubtful series is treated as not found and the title is filed as the files give it.
        odd=None if not one_source or reasons or sergei or part else local_identity.odd_identity(preferred,names[0],author,NO_AUTHOR,ruled=bool(fields['author'].get('rule')),folders=sorted(folders),series=False)
        if odd:
            # 0.22.1: a name the app should not file without asking (local_identity.odd_identity): a question on the to-do
            # list with the existing rows; the row shows what the app read, nothing is renamed, Approve files what it shows.
            # odd_name: the page keeps it out of Select all and bulk Approve as is (Judy 11.4, item 2).
            ask={'kind':odd['kind'],'why':odd['why'],'odd_name':True,'fields':{'title':{'proposal':preferred,'basis':fields['title'].get('basis','')},
                 'author':{'proposal':odd.get('proposal',names[0]),'basis':fields['author'].get('basis','')}}}
            if odd.get('candidates'):
                ask['candidates']=[{'name':name,'source':'author tag','reader_count':0} for name in odd['candidates']]
                ask['fields']['author']['proposal']=odd['candidates'][0]
            return result|{'reasons':[local_identity.ASK_REASONS[odd['kind']]],'ask':ask,'identity_hold':{'kind':odd['kind'],'detail':''},'wait':None,
                           'rules_generation':rules.generation if rules else ''}
        spellings=[] if not one_source or reasons or sergei or part or language or fields['author'].get('rule') else local_identity.name_language(names[0])
        if spellings:
            # Ruling 33 (Sergei 2026-10-26): one person, one folder, picked by the language he writes in. A Latin name with a
            # Russian first name and nothing that says which ("Ilya Marchenko"): asked with both spellings, each a choice.
            ask={'kind':'author_unclear','why':'name_language','odd_name':True,'candidates':[{'name':name,'source':'spelling','reader_count':0} for name in spellings],
                 'fields':{'title':{'proposal':preferred,'basis':fields['title'].get('basis','')},'author':{'proposal':spellings[0],'basis':fields['author'].get('basis','')}}}
            return result|{'reasons':[local_identity.ASK_REASONS['author_unclear']],'ask':ask,'identity_hold':{'kind':'author_unclear','detail':''},'wait':None,
                           'rules_generation':rules.generation if rules else ''}
        english_title=False
        if one_source and not reasons and not part and names[0]!=NO_AUTHOR and not fields['author'].get('rule') and language!='ru' \
                and local_identity.script(names[0])=='cyrillic' and (original_titles.translation(preferred,names[0]) or local_identity.unknown_given(names[0])
                    or rules is not None and (rules.taken_back(names[0]) or rules.keep(names[0]) and local_identity.foreign_given(names[0]))):
            # Ruling 39 (Sergei 2026-10-27): a foreign author credited only in Cyrillic (a foreign first name, no Latin
            # spelling in the library, the cache or a rule). The author's original-language name is looked up now, in the
            # work's catalog records (FantLab, Wikidata, Goodreads; the client's cache, per-site bounds and research lane),
            # and what is found is learned as a lasting rule for that credit, so the author's other books follow without a
            # lookup. Inconclusive (nothing matched, a source closed, the budget spent): Sergei is asked once per author
            # (Author unclear); only that author's books wait for his answer, which becomes his rule. Never transliterated.
            # 0.22.3 (Judy's question 1, its default): a learned rule Sergei took back is never looked up again; he is asked.
            # Approve/preview is read-only and never looks up an unresolved name; it keeps the English question.
            # A normal research pass still looks up after unrelated entered fields (M15).
            approving=any(fields[field].get('state')=='approved' for field in ('title','author'))
            # 2026-10-29 (Tolkien): the book's own folders and the authors the library already files are read first, and
            # an edition's volume title («Хранители. Летопись первая») is also looked up by its book title.
            ancestors=_ancestor_folders(row)
            known=[spelling for spelling,_ in (rules.known_authors.values() if rules is not None else [])]
            hinted=[text(local['series_hint'].get('title'))] if isinstance(local.get('series_hint'),dict) and text(local['series_hint'].get('title')) not in ('',text(title)) else []
            found=None if approving or rules is not None and rules.taken_back(names[0]) else self._author_latin(title,names[0],stop,budget,result,folders=ancestors,known=known,**({'also':hinted} if hinted else {}))
            if found and found['state']=='found':
                latin=_latin_surname_first(found['name'],names[0],found.get('order'))
                self._learn_author('same_as',names[0],latin,found['source_url'],preferred)
                result['author_learned']={'credit':names[0],'name':latin,'source_url':found['source_url']}
                if latin not in authors:authors.append(latin)
                names=[latin];name_source=found['source_url'];work['author_aliases']=author_variants(authors)
                title_entered='title' in set(local.get('names_entered') or []) or any(s.get('kind')=='entered by you' for s in fields['title'].get('sources') or [])
                # Senua's 74b review, r2, kept since R22 withdrew the question: when a source numbers this volume differently
                # from its own title, the record may be another book, so its English title is not taken either.
                other_book=any(item.get('why')=='number_mismatch' for item in filled.get('doubtful') or [] if isinstance(item,dict))
                if found.get('title') and not title_entered and not other_book:
                    # The same record names the English title: rulings 38 and R1 file the book under it. The record says
                    # which language the work was written in (English, unless it names another).
                    russian=preferred;preferred=found['title'];english_title=True;title_rule='english'
                    if russian not in titles:titles.append(russian)
                    if preferred not in titles:titles.insert(0,preferred)
                    found_language=text(found.get('language')) if re.fullmatch('[a-z]{2,3}',text(found.get('language'))) and found.get('language')!='ru' else 'en'
                    work.update(titles=titles,original_title=text(found.get('original_title')) or preferred,original_language=found_language)
            elif found and found['state']=='russian':
                # The work's catalog says it was written in Russian: the Cyrillic name is right (the folder language rule).
                self._learn_author('keep',names[0],'',found['source_url'],preferred)
                result['author_learned']={'credit':names[0],'name':names[0],'source_url':found['source_url']}
            elif isinstance(filled.get('lookup'),dict) and filled['lookup'].get('waiting'):
                # 0.31.0 step 2: the sources that could name this author did not answer yet and the look-up before review
                # still has tries left: the book waits for them (below) instead of asking Sergei now. He is asked only
                # once the look-up has ended without the name.
                pass
            else:
                ask={'kind':'author_unclear','why':'english_spelling','odd_name':True,'credit':names[0],
                     'candidates':[{'name':names[0],'source':'spelling','reader_count':0}],
                     'fields':{'title':{'proposal':preferred,'basis':fields['title'].get('basis','')},'author':{'proposal':names[0],'basis':fields['author'].get('basis','')}}}
                return result|{'reasons':[local_identity.ASK_REASONS['author_unclear']],'ask':ask,'identity_hold':{'kind':'author_unclear','detail':''},'wait':None,
                               'rules_generation':rules.generation if rules else ''}
        # R22 (Sergei 2026-11-22; it replaces rulings 52 and 74b's questions): a series the name only looks like ("Series N.
        # Title" nothing confirms) and a number the book's title and a source disagree on are doubtful, and a doubtful
        # series is treated as not found: neither is asked ("Title unclear", "Number unclear"), the book goes on without
        # the series. series_certainty.judge decides it, where the sources are read (_gap_fill_once); what was dropped is
        # recorded below (facts gap_search 'series_doubt'). A series or number Sergei saved or approved is his and stays.
        original=None
        if one_source and not reasons and not sergei and not part and names[0]!=NO_AUTHOR and language!='ru':
            # Ruling 38 (Sergei 2026-10-27; it replaces ruling 29's wait) with R1 and R3: a translation is filed under the
            # English title a source names (the one title rule: preferred, above), else under the title it has. Recorded
            # for the details panel's "Original title" fact (Judy 0.22.2 section 4).
            if title_rule=='english' and local_identity.script(title)=='cyrillic' and local_identity.script(preferred)=='latin':
                original={'state':'found','title':preferred}
            elif original_titles.translation(preferred,names[0]):
                original={'state':'none','title':''}
        result['work']=work
        if original is not None:result['original_title']=original
        if names and names[0]!=NO_AUTHOR and not typed_author and fields['author'].get('state') not in ('entered','approved'):
            # 0.30.0 item 5 (Sergei 2026-11-18): one author folder per author, the Latin surname-first form the library
            # already uses ("Rowling J. K"), whichever source answered: a rule's name, or the same words surname first
            # (canonical_names.author; never a guess). His typed or approved spelling is his answer and stays.
            import canonical_names
            # Senua's 0.30.0 review, m2: a rule Sergei scoped to a folder counts in the book's own folder.
            folder=ntpath.dirname(str((row.get('members') or [{}])[0].get('path') or ''))
            # A rule this research has just learned or corrected is in the catalog, not in the copy read at its start.
            current_rules=self.rules()
            if result.get('author_learned'):
                import author_rules
                current_rules=author_rules.load(self.client.database) or current_rules
            filed,_=canonical_names.author(names[0],current_rules,folder)
            if filed and filed!=names[0]:
                names=[filed]+names[1:]
                if filed not in authors:authors.append(filed);work['author_aliases']=author_variants(authors)
        review,facts,policy_reasons=build_policy(row,work,preferred,names,series=filed_series.get('name',''),number=filed_series.get('number',''),local=local_identity.summary(local))
        facts['work_ids']=work_ids
        facts['research_version']=RESEARCH_VERSION  # ruling 71f: a job planned under this research needs no re-check
        # 0.31.0 (A6): the four states of the details panel's "English title" fact, as the engine knows them. 'found' (the
        # title, with its source) and 'none' (the sources answered and have no English title: filed under the title in the
        # files, R3) are 0.22.2's; new: 'no_answer' (a source never answered within the limit, with the tries made and
        # their limit) and 'entered' (the title is his). A Russian original has no such fact, as before.
        lookup_record=filled.get('lookup') if isinstance(filled.get('lookup'),dict) else {}
        if his_title:result['original_title']={'state':'entered','title':''}
        elif result.get('original_title') and result['original_title'].get('state')=='found':
            result['original_title'].update(provider=text(catalog.get('english_provider') or catalog.get('provider')) if catalog and not english_title else series_source({'source_url':name_source})['provider'],
                                            url=text(catalog.get('english_source') or catalog.get('source_url')) if catalog and not english_title else name_source)
        elif result.get('original_title') and (lookup_record.get('fields') or {}).get('original_title')=='no_answer':
            result['original_title']={'state':'no_answer','title':'','tries':lookup_record.get('tries'),'limit':lookup_record.get('limit')}
        if 'names_digest' in local:facts['entered_names']={'digest':local['names_digest'],'fields':list(local.get('names_entered') or []),'saved_utc':dict(local.get('names_saved_utc') or {})}  # Edit names: the job's names
        if result.get('original_title'):facts['original_title_lookup']=dict(result['original_title'])  # ruling 38: the details panel's fact
        if spelling:facts['author_spelling']=spelling
        # background: the gaps the background pass fills later (gap_fill), with what it asks the sources about. Series
        # positions are series backfill's (it looks every finished book without a series up and renames it in Sorted).
        background=[gap for gap in filled.get('unfilled',[]) if gap in BACKGROUND_GAPS]
        facts['gap_search']={'gaps':list(local['gaps']),'unfilled':list(filled.get('unfilled',[])),'closed_sources':[],'from_cache':True,
                             'background':background}
        if background:facts['gap_search']['ask']={'title':title,'author':author,'partial':bool(fields['author'].get('partial'))}
        reasons.extend(policy_reasons);reasons.extend(source_gate(row,work))
        result['sources'].insert(0,{'url':'','kind':'local_agreement','verified_identity':True,'agreement':facts['local_agreement']})
        agreed=local_identity.summary(local)
        def described(name):
            value=agreed[name]
            return value['value']+' ('+value['how']+'; '+', '.join(s['kind']+(' '+s['field'] if s.get('field') else '')+' "'+s['value']+'"' for s in value['sources'])+')'
        basis='Local agreement '+local_identity.AGREEMENT_VERSION+' (Sergei decision 2026-10-12): embedded tags and file/folder names agree. Title: '+described('title')+'. Author: '+described('author')+'. No Internet confirmation required.'
        if one_source:basis='Local identity '+local_identity.IDENTITY_VERSION+' (Sergei 2026-10-24: title + author is enough): title and author each from one local source, readers, collection credits and garbled tags excluded. Title: '+described('title')+'. Author: '+described('author')+'. No Internet confirmation required.'
        if part:basis+=' One part %d of a %d-part M4B set "%s", filed as its own book (Sergei 2026-10-13); it must carry its own chapters.'%(part['position'],part['parts'],part['set_title'])
        identity='Books Arranger local agreement '+local_identity.AGREEMENT_VERSION
        def evidence(field,value,url,why):
            result['evidence'].append({'field':field,'cited_value':value,'source_url':url,'retrieved_utc':_stamp(),'reviewer_actor':'assistant','reviewer_identity':identity,'basis':why[:3900]})
        evidence('title',title,'',basis)
        if facts['original_title']!=title:
            evidence('title',facts['original_title'],catalog.get('source_url',''),'Original-work title from the catalog record matching the locally agreed title and author; it only fills a field missing locally.')
        spelled=('' if not spelling else ' Canonical spelling (Sergei 2026-10-13): "'+spelling['chosen']+'" from "'+spelling['spelling']+'"; '+spelling['why']+'; '+spelling['order']+'.')
        confirmed_note='Author spelling confirmed by fetched catalog evidence for this author elsewhere in the library (library-wide confirmed-spelling list); the locally agreed identity is unchanged.'
        evidence('authors',review['canonical_author'],name_source,(basis if not name_source else confirmed_note if spelling and spelling.get('confirmed_by') else 'Full author name from the catalog record matching the locally agreed title and author; it only fills a field missing locally.')+spelled)
        if language:
            evidence('original_language',language,catalog.get('source_url',''),'Original-work language from the catalog record matching the locally agreed title and author.')
        elif english_title:
            # Futaba's 0.24.0 QA, B1: the ruling-39 record that named the English title says which language the work was
            # written in (_author_latin: English unless it names another). The policy records that language, and approval
            # refused a book with no evidence for it ("Assistant approval requires ... original language"), holding it 15
            # minutes until the cache answered.
            evidence('original_language',work['original_language'] or 'en',name_source,'Original-work language from the catalog record that named the author\'s English spelling and the English title (ruling 39).')
        if review['series']:
            url=series.get('source_url','')
            why=(SERIES_WHY.get(series.get('provider'),'Series and position from the catalog record matching the locally agreed title and author.') if url else
                'Series and number entered by you (Edit names; Sergei 2026-10-24, ruling 6a): '+review['series']+'; '+review['number']+'.' if series.get('provider')=='entered' else
                'Embedded series tags repeated in the folder/file name: '+described('series')+'; '+described('number')+'.')
            if filed_series.get('name_provider') and filed_series.get('name_local'):
                why+=' The series is named in English (ruling R1): "%s" for the files\' "%s", from %s.'%(review['series'],filed_series['name_local'],filed_series.get('name_url') or filed_series['name_provider'])
            evidence('series',review['series'],url,why);evidence('number',review['number'],url,why)
            facts['series_source']=series_source(filed_series)
        # 0.31.0 (A6): where the title came from, as keys the page words: 'rule' is the title rule's own answer
        # (canonical_names.TITLE_RULES); a title a source named carries that source.
        facts['title_source']={'rule':title_rule,'provider':text(catalog.get('english_provider') or catalog.get('provider')) if title_rule in ('english','russian_original') and catalog else '',
                               'url':text(catalog.get('english_source') or catalog.get('source_url')) if title_rule in ('english','russian_original') and catalog else '',
                               'split':bool(split and not his_title)}
        if english_title and not facts['title_source']['url']:facts['title_source'].update(provider=series_source({'source_url':name_source})['provider'],url=name_source)
        # A doubtful series that was dropped (series_certainty): what the source named and why it is doubtful.
        doubtful=[dict(item) for item in filled.get('doubtful') or [] if isinstance(item,dict)]
        if doubtful and not review['series']:facts['gap_search']['series_doubt']=doubtful[:6]
        # Edit names (his universe, also an empty one) over the universe the book's folders name (rulings 30 and 37).
        if 'universe' in saved_names and saved_names['universe'] is not None:review['universe']=saved_names['universe']
        elif local.get('universe'):review['universe']=local['universe']
        result.update(review=review,metadata_facts=facts)
        result['reasons']=list(dict.fromkeys(reasons))
        result['wait']=None
        result['gap_wait']=None
        lookup=filled.get('lookup')
        if isinstance(lookup,dict):
            # 0.31.0 step 2 (rulings R2 and R5): the look-up before review asked the sources (_review_lookup). While a
            # source that could still answer a missing field is closed and has a try left, the book waits ("Waiting for
            # source", the next try's time) instead of being filed without the answer; the wait is bounded (LOOKUP_POLICY)
            # and then the book is filed as before. A source that answered "none" never makes it wait.
            result['lookup']=lookup
            waited=row.get('_series_waits',0)
            waited=waited if type(waited) is int and 0<=waited<1000 else 0
            closed=sorted(name for name,state in (lookup.get('sources') or {}).items() if not (state.get('answered') or state.get('gave_up')))
            facts['gap_search']['lookup']={key:copy.deepcopy(lookup.get(key)) for key in ('policy','fields','tries','limit','next_at','waiting','ended','visits')}
            if lookup.get('waiting') and not result['reasons']:
                # 'series_waits' and gap_search 'series_wait' are 0.30.0 item 3's facts, kept: how many times in a row
                # the book has waited, and for which sources.
                result['reasons']=[SERIES_WAIT_REASON if lookup['fields'].get('series')=='waiting' else LOOKUP_WAIT_REASON]
                result['wait']=dict(lookup['wait']);result['series_waits']=waited+1
                facts['gap_search']['series_wait']={'sources':closed,'tries':waited+1}
            elif lookup['fields'].get('series')=='no_answer' and not review['series']:
                facts['gap_search']['series_wait']={'sources':closed,'tries':waited,'published_without':True}
        return result

    def fill_gaps(self,ask,gaps,stop,budget,progress=lambda *_:None,skip=()):
        """The background gap fill's request (gap_fill.GapFill, 0.22.1): ask the sources about these missing fields of a
        book identified locally as ask['title'] by ask['author'] ('partial': a surname only). budget carries the lane.
        Returns (found, result): found as _gap_fill (catalog, author_full, series, unfilled, closed) plus 'wait', when
        a closed source could still answer an unfilled field; result['sources'] holds the fetched receipts.
        0.31.0 (R16): skip names the sources the look-up has settled for this book or that are not due yet (not asked);
        found['asked'] lists the sources asked this time and found['closures'] each one that was closed, with the wait's
        kind, so the look-up can count its tries per source."""
        result={'sources':[],'evidence':[]};waits=[]
        local={'gaps':list(gaps),'fields':{'author':{'partial':bool(ask.get('partial'))}},'skip':tuple(skip or ())}
        found=self._gap_fill(local,ask['title'],ask['author'],stop,budget,waits,progress,result)
        found['wait']=_wait(waits,budget.get('answered')) if found.get('closed') else None
        return found,result

    def _gap_fill(self,local,title,author,stop,budget,waits,progress,result):
        """Ask only the sources that can answer a field missing locally; never block. Up to three passes, each for the
        fields the passes before left unfilled:
          1. the title as the files give it;
          2. an edition's volume title («Хранители. Летопись первая») no catalog knows, by its book title («Хранители»;
             2026-10-29, Tolkien);
          3. a name that only looks like "Series N. Title" (local['series_hint'], local_identity.identify), by the part after
             the number: when a source names a certain series for it whose number is the name's own, that confirms the
             series, and the part after the number is the book's title (found['split_title']).
        Whether a series a source names is certain is decided in one place (series_certainty.judge, through
        _gap_fill_once): a number the book's own title or name does not give, more than one series, a universe and a
        conflict are doubtful, and a doubtful series is treated as not found (rulings R18, R21, R22; it replaces the
        questions of rulings 52 and 74b). found['doubtful'] lists what was dropped, with why."""
        facts=self._series_facts(local,title)
        found=self._gap_fill_once(dict(local,series_facts=facts),title,author,stop,budget,waits,progress,result)
        base,_=edition_volume(title)
        if base!=text(title) and found.get('unfilled') and not stop.is_set():
            again=self._gap_fill_once(dict(local,gaps=list(found['unfilled']),series_facts=facts),base,author,stop,budget,waits,progress,result)
            found=self._merge_passes(found,again)
        hint=local.get('series_hint') if isinstance(local.get('series_hint'),dict) else None
        if hint and text(hint.get('title')) and text(hint['title'])!=text(title) and 'series' in (found.get('unfilled') or ()) and not stop.is_set():
            asked=dict(facts,hint={'series':text(hint.get('series')),'number':text(hint.get('number'))})
            again=self._gap_fill_once(dict(local,gaps=[gap for gap in ('series','original_title') if gap in found['unfilled']],series_facts=asked),text(hint['title']),author,stop,budget,waits,progress,result)
            if again.get('series'):
                found=self._merge_passes(found,again);found['split_title']=text(hint['title'])
            else:
                # Nothing confirms the series the name looks like: the book goes on without it, under the title the
                # files give. What this pass learned of the part after the number is not the book's (no catalog used).
                again={key:value for key,value in again.items() if key not in ('catalog','author_full','series')}
                found=self._merge_passes(found,again)
        if hint and 'series' in (found.get('unfilled') or ()) and 'series' in (local.get('gaps') or ()):
            # The series the name only looks like (or mentions in brackets) stays unconfirmed: dropped, and said so.
            found['doubtful'].append({'provider':'','name':text(hint.get('series')),'number':text(hint.get('number')),'why':'unconfirmed_name','source_url':''})
        return found

    @staticmethod
    def _series_facts(local,title):
        """What the book's own files say of its series, for series_certainty.judge: a series they name (tags, his folders,
        what he entered or saved) and the number the title itself gives («Летопись первая» -> 1)."""
        own=local.get('series') if isinstance(local.get('series'),dict) else {}
        saved=local.get('manual_series') if isinstance(local.get('manual_series'),dict) else {}
        # A series the title mentions in brackets («Солнце и Замок (Книга Нового Солнца #3)») is the book's own word on
        # its number: a source that numbers it differently is doubtful. (A name split "Series N. Title" is asked about
        # by the part after the number, with its own hint: _gap_fill's third pass.)
        hint=local.get('series_hint') if isinstance(local.get('series_hint'),dict) else {}
        mentioned={'series':text(hint.get('series')),'number':text(hint.get('number'))} if hint and text(hint.get('title'))==text(title) else None
        return {'series':text(own.get('name') or saved.get('series')),'number':text(own.get('number') or saved.get('number')),'volume':edition_volume(title)[1],'hint':mentioned}

    @staticmethod
    def _merge_passes(found,again):
        taken=not found.get('catalog') and bool(again.get('catalog'))
        for key in ('catalog','series','author_full','series_english'):
            if again.get(key) and not found.get(key):found[key]=again[key]
        if taken:found['english_pending']=bool(again.get('english_pending'))
        for key in ('asked','closures','doubtful','series_asked'):found[key]=list(found.get(key) or [])+list(again.get(key) or [])  # 0.31.0 (R16)
        found['closed']=list(dict.fromkeys(list(found.get('closed') or [])+list(again.get('closed') or [])))
        found['unfilled']=[field for field in found['unfilled'] if not (field=='original_title' and found.get('catalog') and not found.get('english_pending') or field=='series' and found.get('series')
                                                                      or field=='series_name' and found.get('series_english') or field=='author_full' and (found.get('author_full') or found.get('catalog')))]
        found['closed']=[source for source in found['closed'] if found['unfilled']]
        return found

    def _gap_fill_once(self,local,title,author,stop,budget,waits,progress,result):
        import series_certainty,canonical_names,wikidata_books
        gaps=set(local['gaps']);found={'closed':[],'asked':[],'closures':[],'doubtful':[]}
        partial=bool(local['fields']['author'].get('partial'))
        facts=local.get('series_facts') if isinstance(local.get('series_facts'),dict) else {'volume':edition_volume(title)[1]}
        # 0.31.0 (R16, the detail look-up's bounded tries): a source it has settled for this book, or that is not due yet,
        # is not asked; each source asked is named, and each closure keeps why (the app's own limit and a busy catalog are
        # no try of the source).
        skip=set(local.get('skip') or ())
        def closure(source,wait,kind=None):
            found['closures'].append({'source':source,'reason':wait.reason,'retry_at':wait.retry_at,'kind':kind or wait.kind,'scope':wait.scope})
        def attempt(source,function):
            if source in skip:return None
            found['asked'].append(source)
            try:return function()
            except ResearchWait as wait:waits.append(wait);found['closed'].append(source);closure(source,wait)
            except sqlite3.OperationalError as error:
                # 0.22.2: a busy catalog is a closed source for now, never the end of the run (the live stop at _expire).
                if not catalog_busy(error):raise
                busy=ResearchWait(source,CATALOG_BUSY_REASON,getattr(self.client,'clock',time.time)()+CATALOG_BUSY_WAIT,'source_unavailable','host')
                waits.append(busy);found['closed'].append(source);closure(source,busy,'catalog_busy')
            except (ValueError,TypeError,KeyError,AttributeError):pass
            return None
        if gaps&{'original_title','author_full'}:
            progress('FantLab','Filling missing original title')
            catalog=attempt('fantlab',lambda:self._gap_fantlab(title,author,partial,stop,budget,result))
            if catalog:found['catalog']=catalog
        # 0.30.0 item 3: what each series source did: 'answered' (a series, "none", or an answer it could not use),
        # 'limited' (only rate-limited: the app's own request bounds, the site's pause or its pacing) or 'closed' (any
        # other closure: unreachable, the catalog busy).
        asked=found['series_asked']=[]
        def series_attempt(source,function):
            before,seen=len(found['closed']),len(waits)
            value=attempt(source,function)
            if source in skip:return value
            if len(found['closed'])==before:asked.append((source,'answered'))
            else:
                wait=waits[-1] if len(waits)>seen else None
                limited=wait is not None and (wait.kind in ('app_limit','source_pause') or wait.reason=='Public source cooling down')
                asked.append((source,'limited' if limited else 'closed'))
            return value
        def certain(candidate,others=()):
            # The one rule (series_certainty): a doubtful series is treated as not found, and what was dropped is kept.
            if not candidate:return None
            verdict=series_certainty.judge(candidate,facts,others)
            if verdict['verdict']==series_certainty.CERTAIN:return verdict['series']
            found['doubtful'].append(series_certainty.dropped(verdict))
            return None
        series=None
        if 'series' in gaps:
            # Sergei 2026-10-18: Goodreads is the series source; FantLab's cycle only when Goodreads has none.
            progress('Goodreads','Filling missing series position')
            series=certain(series_attempt('goodreads',lambda:self._series_goodreads(title,author,stop,budget,result)))
            if not series:
                progress('FantLab','Filling missing series position')
                series=certain(series_attempt('fantlab',lambda:self._series_fantlab(title,author,partial,stop,budget,result)))
        # Wikidata, the work's own record (0.31.0 step 2): asked for the original-work facts when FantLab has none; for the
        # English title of a work written in neither Russian nor English (FantLab names such a work only in its own
        # language, ruling R1); for the series when the sources before it have none; and for the English name of a series
        # FantLab names in another language. One look-up serves all four (_wikidata_book; its answers are cached).
        catalog=found.get('catalog') or {}
        needs_english=bool(catalog) and catalog.get('language') not in ('','ru','en') and not catalog.get('english_title')
        series_language=text(catalog.get('language')) or text((series or {}).get('language'))
        needs_name=bool(series) and series.get('provider')=='fantlab' and series_language not in ('','ru','en')
        wants_catalog='original_title' in gaps and (not catalog or needs_english)
        wants_series='series' in gaps and not series
        # 0.31.0 step 3 (R1): a translated book whose own files name its series in Russian («Память о прошлом Земли. Книга
        # 2») is asked about for the series' English name only ('series_name'); the series and its number stay the files'.
        naming_asked='series_name' in gaps and 'series' not in gaps
        naming=naming_asked and text(catalog.get('language')) not in ('','ru')
        if naming and text(catalog.get('language'))=='en':
            # A work written in English: FantLab's cycle carries its original, English name.
            candidate=attempt('fantlab',lambda:self._series_fantlab(title,author,partial,stop,budget,result))
            verdict=series_certainty.judge(candidate,facts) if candidate else None
            if verdict and verdict['verdict']==series_certainty.CERTAIN and text(candidate.get('name_english')):
                found['series_english']={'name':series_spelling(candidate['name_english']),'provider':'fantlab','source_url':text(candidate.get('source_url'))}
        record=None
        if wants_catalog or wants_series or needs_name or naming and not found.get('series_english'):
            progress('Wikidata','Filling missing original-work facts')
            record=(series_attempt if wants_series else attempt)('wikidata',lambda:self._wikidata_book(title,author,partial,stop,budget,result))
        # A work written in neither Russian nor English whose English title only Wikidata can give, and Wikidata did not
        # answer now (closed, limited): the original-title gap is not filled yet, so the book waits for that answer too.
        english_pending=needs_english and 'wikidata' in found['closed']
        disagreed=False
        if record and record.get('conflict'):
            found['doubtful'].append({'provider':'wikidata','name':'','number':'','why':'source_conflict','source_url':''});record=None
        if record:
            entry=self._wikidata_catalog(record,title)
            if not catalog and entry.get('language'):found['catalog']=catalog=entry
            elif needs_english and entry.get('english_title') and entry.get('language')==catalog.get('language'):
                # The same work in both sources (the title, the author and the language agree): Wikidata's English title.
                found['catalog']=catalog=dict(catalog,english_title=entry['english_title'],english_source=entry['source_url'],english_provider='wikidata')
                for key in ('author_latin','author_family','author_given'):
                    if entry.get(key) and not re.search('[A-Za-z]',text(catalog.get(key))):catalog[key]=entry[key]  # FantLab names him in his own letters
            own=wikidata_books.series(record)
            if series and series.get('provider')!='wikidata' and own and not own.get('doubt') and own.get('number') \
                    and not series_certainty.same_number(series.get('number'),own['number']):
                # Two sources in hand number the book differently, and which source wins is not ruled: doubtful.
                found['doubtful'].append({'provider':text(series.get('provider'))+', wikidata','name':text(series.get('name')),'number':text(series.get('number'))+' / '+text(own['number']),
                                          'why':'sources_disagree','source_url':text(series.get('source_url'))})
                series=None;disagreed=True
            elif wants_series and own:series=certain(own)
            elif series and own and not own.get('doubt') and own.get('name_english'):
                # The series' English name comes from another source than the series itself: said so (A6).
                series=dict(series,name_english=own['name_english'],name_provider='wikidata',name_url=text(own.get('source_url')))
            # R1 for a series the book's own files name (its tags, its title tag, a folder): the series itself is the
            # files'; its English name is Wikidata's when the work's one series statement has the files' number.
            naming=naming_asked and text((found.get('catalog') or {}).get('language')) not in ('','ru')  # the language may be Wikidata's own answer
            if naming and own and own.get('name_english') and series_certainty.judge(own,facts)['verdict']==series_certainty.CERTAIN:
                found['series_english']={'name':series_spelling(own['name_english']),'provider':'wikidata','source_url':text(own.get('source_url'))}
        if 'series' in gaps and not series and not disagreed:
            series=certain(series_attempt('publisher',lambda:self._series_publisher(title,author,stop,budget,result)))
            if not series:series=certain(series_attempt('litres',lambda:self._series_litres(title,author,stop,budget,result)))
        if any(item.get('why')=='number_mismatch' for item in found['doubtful']):
            # Ruling 74b's caution (Senua's review, r2), kept: a record that numbers this book differently may be another
            # book, so nothing else this pass found is used either (its English title: «Хранители. Летопись первая» was
            # offered as "The Two Towers"); the title stays as it is.
            found.pop('catalog',None);series=None
        if series:
            # R1: the series is named by the same rule as the title (canonical_names.series_name).
            name,rule=canonical_names.series_name(series,text((found.get('catalog') or {}).get('language')) or text(series.get('language')))
            found['series']=dict(series,name=series_spelling(name),name_rule=rule)
        if 'author_full' in gaps and not found.get('catalog'):
            for source,function in (('openlibrary',self._gap_openlibrary),('googlebooks',self._gap_googlebooks),('itunes',self._gap_itunes)):
                progress({'openlibrary':'Open Library','googlebooks':'Google Books','itunes':'iTunes'}[source],'Filling missing full author name')
                name=attempt(source,lambda:function(title,author,stop,budget,result))
                if name:found['author_full']=name;break
        unfilled=[]
        if english_pending and found.get('catalog') and not found['catalog'].get('english_title'):found['english_pending']=True
        if 'original_title' in gaps and (not found.get('catalog') or found.get('english_pending')):unfilled.append('original_title')
        if 'series' in gaps and not found.get('series'):unfilled.append('series')
        # Open until a source says the work was written in Russian (nothing to name in English then) or gives the name.
        if naming_asked and text((found.get('catalog') or {}).get('language'))!='ru' and not found.get('series_english'):unfilled.append('series_name')
        if 'author_full' in gaps and not (found.get('author_full') or found.get('catalog')):unfilled.append('author_full')
        serves={'fantlab':{'original_title','author_full','series','series_name'},'wikidata':{'original_title','series','series_name'},'publisher':{'series'},'goodreads':{'series'},'openlibrary':{'author_full'},'googlebooks':{'author_full'},'itunes':{'author_full'},'litres':{'series'}}
        goodreads_waited='goodreads' in found['closed']
        found['closed']=[source for source in found['closed'] if serves[source]&set(unfilled)]
        # Goodreads decides the series: a fallback answer still waits a little for it (gap deferral).
        if goodreads_waited and (found.get('series') or {}).get('provider')!='goodreads' and 'goodreads' not in found['closed']:found['closed'].append('goodreads')
        found['unfilled']=unfilled
        return found

    @staticmethod
    def _wikidata_catalog(record,title):
        """A Wikidata work record (wikidata_books.book) as the catalog record research reads: the language, the original and
        English titles, and the one author's names (with the family and given names Wikidata's own fields give, for the
        folder's name order)."""
        authors=record.get('authors') or []
        one=authors[0] if len(authors)==1 else {}
        order=record.get('author_order') or {}
        return {'provider':'wikidata','work_id':'wikidata:'+record['work_id'],'source_url':record['source_url'],'language':record.get('language') or '',
                'original_title':record.get('original_title') or record.get('english_title') or record.get('title_ru') or text(title),
                'english_title':record.get('english_title') or '','title_native':record.get('title_ru') or '',
                'author_native':text(one.get('name_ru')),'author_latin':text(one.get('name_en')),
                'author_family':text(order.get('family')),'author_given':text(order.get('given'))}

    def _wikidata_book(self,title,author,partial,stop,budget,result):
        """0.31.0 step 2: the one written work Wikidata holds under this title by this author (wikidata_books.book: the
        title, every credited author and "is a written work", never the title alone), or None; {'conflict': why} when two
        works fit. Three requests (the search, its candidates, the items they point to), through the client: its cache,
        the Wikimedia bounds and pauses. A fourth only for an author whose name order the app cannot tell, for Wikidata's
        own family-name field (canonical_names.latin_order)."""
        import wikidata_books,canonical_names
        from local_identity import title_key
        search=wikidata_books.search_url(title)
        found=wikidata_books.search_ids(self.client.json(search,stop,budget))
        if not found:return None
        first=wikidata_books.entities_url(found)
        candidates=wikidata_books.entities(self.client.json(first,stop,budget),found)
        wanted=title_key(title)
        exact={key:entity for key,entity in candidates.items() if wanted in {title_key(name) for name in wikidata_books.names(entity)}}
        if not exact:return None
        links=wikidata_books.related_ids(exact.values())
        second=wikidata_books.entities_url(links) if links else ''
        related=wikidata_books.entities(self.client.json(second,stop,budget),links) if links else {}
        record=wikidata_books.book(exact,related,title,author,title_key,_name_matches,_people,partial)
        if not record or record.get('conflict'):return record
        authors=record['authors']
        if len(authors)==1 and len(authors[0]['name_en'].split())>=2 and canonical_names.latin_order(authors[0]['name_en'])[1]==canonical_names.ORDER_UNKNOWN:
            keys=list(dict.fromkeys(authors[0]['family_ids']+authors[0]['given_ids']))[:6]
            if keys:
                third=wikidata_books.entities_url(keys)
                record['author_order']=wikidata_books.name_order(authors[0],wikidata_books.entities(self.client.json(third,stop,budget),keys))
        for url in (first,second) if second else (first,):
            self._gap_receipt(url,result,record['source_url'],['title','authors','original_title','original_language','series','number'])
        return record

    # ------------------------------------------------------------ series (Sergei 2026-10-18)

    def _series_wikidata(self,title,author,stop,budget,result):
        """The series Wikidata's own record of this work names (0.31.0 step 2), as a candidate for series_certainty.judge,
        or None when it knows no such work or the work is in no series. The work is matched by its title, every credited
        author and its type (_wikidata_book), never by the title alone. Ruling R5: one source naming a series is enough,
        so the statement needs no reference of its own any more (0 of 151 series came from the referenced-only adapter).
        The candidate carries 'doubt' for the doubtful shapes Wikidata shows: two series on one book, a universe in place
        of a series, two works that fit; a series named without a number has number ''."""
        import wikidata_books
        record=self._wikidata_book(title,author,False,stop,budget,result)
        if not record:return None
        if record.get('conflict'):return {'provider':'wikidata','name':'','number':'','doubt':'source_conflict','source_url':''}
        return wikidata_books.series(record)

    def series_verdict(self,candidate,title):
        """The one rule (series_certainty.judge) for the series look-up of finished books (series_backfill.lookup): the
        candidate a source's adapter returned, against the number the book's own title gives. Returns judge()'s answer."""
        import series_certainty
        return series_certainty.judge(candidate,{'volume':edition_volume(title)[1]})

    def _series_publisher(self,title,author,stop,budget,result):
        from local_identity import title_key
        from series_evidence import prh_series
        urls=[]
        from openlibrary_index import lookup
        local=lookup(self.local_index,title)
        result['local_openlibrary']={'status':local['status'],'purpose':'identity and primary-page discovery; edition series is not narrative order'}
        local_match=None
        if local['status']=='covered':
            import itertools
            people=_people(author);matches=[]
            for work in local['works']:
                authors=work['authors']
                if not 0<len(authors)==len(people)<=6:continue
                if any(all(any(_same_people(person,[alias]) for alias in entry['names']) for person,entry in zip(people,order)) for order in itertools.permutations(authors)):matches.append(work)
            if len(matches)==1:
                local_match=matches[0];urls.extend(local_match['links'])
                result['local_openlibrary']['work_id']=local_match['id']
        for lead in self.leads:
            if title_key(lead.get('title',''))==title_key(title) and _same_people(author,lead.get('authors') or []):
                urls.extend(lead.get('publisher_urls') or [])
        urls=[url for url in urls if re.fullmatch(r'https://www\.penguinrandomhouse\.com/books/[1-9]\d{0,11}/[a-z0-9-]+/',str(url))]
        if not urls:
            # Wikipedia's fetched revision/reference bridge is discovery only. Its
            # text, infobox or list positions do not authorize an ordinal here.
            wiki_wait=None
            try:
                wiki=self.client.wikipedia('"'+title+'" '+author,stop,budget)
                result['sources'].extend(wiki['sources']);urls.extend(wiki['leads'])
            except ResearchWait as wait:wiki_wait=wait
            if not urls:
                try:urls.extend(self.client.discover('"'+title+'" '+author+' publisher',stop,budget))
                except ResearchWait:
                    if wiki_wait:raise wiki_wait
                    raise
            if not urls and wiki_wait:raise wiki_wait
        for url in list(dict.fromkeys(urls))[:2]:
            if not re.fullmatch(r'https://www\.penguinrandomhouse\.com/books/[1-9]\d{0,11}/[a-z0-9-]+/',str(url)):continue
            raw=self.client.read(url,stop,budget)
            found=prh_series(raw,url,title,author,title_key,_same_people)
            if found:
                self._gap_receipt(url,result,url,['title','authors','series','number'])
                if local_match:found['local_identity']={'work':local_match,'index_sha256':local['receipt']['sha256'],'source_manifest':local['receipt']['source_manifest']}
                return found
        return None

    def _series_litres(self,title,author,stop,budget,result):
        """Last optional fallback: indexed discovery leads to query-free Litres pages, never its blocked search route.
        The canonical main record must match this exact title and ALL authors; a book-specific explicit ordinal decides.
        Edition metadata does not assert the original-work language, and never overrides entered names.
        """
        from litres_evidence import book_url,book
        from local_identity import title_key
        from public_work_identity import EvidenceConflict
        urls=[]
        for lead in self.leads:
            if not isinstance(lead,dict) or title_key(lead.get('title',''))!=title_key(title) or not _same_people(author,lead.get('authors') or []):continue
            urls.extend(lead.get('series_urls') or []);urls.extend(lead.get('publisher_urls') or [])
        urls=list(dict.fromkeys(url for value in urls if (url:=book_url(value))))
        if not urls:urls=list(dict.fromkeys(url for value in self.client.discover('site:litres.ru "'+title+'" '+author,stop,budget) if (url:=book_url(value))))
        matches=[]
        for url in urls[:2]:
            raw=self.client.read(url,stop,budget);record=book(raw,url)
            if not record or title_key(record['title'])!=title_key(title) or not _exact_people(author,record['authors']):continue
            self._gap_receipt(url,result,url,['title','authors']+(['series','number'] if record['series'] else []))
            result['sources'][-1].update(provider='Litres',identity_basis='Canonical Litres main book record: exact title and complete author list; readBy and related products excluded')
            if record['series']:matches.append(record['series'])
        if len({(v['name'],v['number']) for v in matches})>1:raise EvidenceConflict('Litres editions disagree on series or position')
        return matches[0] if matches else None

    def _series_goodreads(self,title,author,stop,budget,result):
        """Series name and number from the Goodreads book page, or None. The search page is a lead only: a
        result whose title, without its "(Series, #N)", is this title and whose credits are this book's
        people. The book page's own record then decides; a position that is not one whole number
        ("1-3", "0.5", blank) is no position. At most two requests, paced and cached by the client."""
        from local_identity import title_key
        from public_work_identity import EvidenceConflict
        people=_people(author)
        url='https://www.goodreads.com/search?'+urllib.parse.urlencode({'q':title+' '+(people[0] if people else author),'search_type':'books'})
        search=goodreads_results(self.client.read(url,stop,budget))[:10]
        # A citation is discovery only. Search must independently bind this work
        # to its exact book id and every author before a series entry can decide.
        identities=[]
        for book_id,shown,names in search:
            match=GOODREADS_SERIES.match(shown)
            bare=match[1] if match else shown
            if title_key(bare)==title_key(title) and _same_people(author,names) \
                    and _same_people(', '.join(names),_people(author)) and book_id not in identities:
                identities.append(book_id)
        if identities:
            for lead in self.leads:
                if not isinstance(lead,dict) or title_key(lead.get('title',''))!=title_key(title) \
                        or not _same_people(author,lead.get('authors') or []):continue
                for citation in (lead.get('series_urls') or [])[:2]:
                    if not isinstance(citation,str) or not re.fullmatch(r'https://www\.goodreads\.com/series/[1-9]\d{0,11}',citation):continue
                    raw=self.client.read(citation,stop,budget)
                    matches=[value for book_id in identities if (value:=goodreads_series(raw,citation,book_id,title,author))]
                    if len(matches)>1:raise EvidenceConflict('Goodreads series entries disagree on the exact edition identity')
                    if len(matches)==1:
                        found=matches[0]
                        self._gap_receipt(url,result,url,['title','authors'])
                        self._gap_receipt(citation,result,citation,['series','number'])
                        result['sources'][-1]['identity_basis']='Exact Goodreads search book id, title and all authors joined to the explicit series entry'
                        return found
        leads=[]
        for book_id,shown,names in search:
            match=GOODREADS_SERIES.match(shown)
            if match and title_key(match[1])==title_key(title) and _same_people(author,names) and book_id not in leads:leads.append(book_id)
        if not leads:return None  # Goodreads lists no series for this book
        page='https://www.goodreads.com/book/show/'+leads[0]
        found=goodreads_book(self.client.read(page,stop,budget),leads[0])
        if not found:return None
        shown,names,series=found
        if title_key(shown)!=title_key(title) or not _same_people(author,names) or not series:return None
        if len({text(entry[0]).casefold() for entry in series if text(entry[0])})>1:
            # 0.31.0 (series_certainty): the book page lists the book in more than one series. Doubtful: never the first.
            return {'provider':'goodreads','name':'; '.join(text(entry[0]) for entry in series if text(entry[0]))[:300],'number':'','doubt':'several_series','source_url':page}
        name,position=series[0]
        if not name or not re.fullmatch(r'[1-9]\d{0,3}',position):return None
        self._gap_receipt(page,result,page,['series','number'])
        return {'provider':'goodreads','name':series_spelling(name),'number':position,'source_url':page}

    def _series_fantlab(self,title,author,partial,stop,budget,result,work=None):
        """Fallback: the innermost FantLab cycle holding the work, or None. FantLab gives no number, so the
        position is counted in the cycle's own order among its works of the same kind; works FantLab marks
        as extras ("plus") are not numbered. Co-written works are accepted when every credited person
        matches. work: the already verified extended record (catalog path), else it is searched."""
        from local_identity import title_key
        if work is None:
            url='https://api.fantlab.ru/search-works?'+urllib.parse.urlencode({'q':title,'onlymatches':1})
            records=self.client.json(url,stop,budget)
            if not isinstance(records,list):raise ValueError('Malformed catalog search')
            ids=[]
            for record in records[:5]:
                if not isinstance(record,dict) or type(record.get('work_id')) is not int or not 0<record['work_id']<10**10:continue
                if title_key(title) not in {title_key(v) for v in _fantlab_names(record)}:continue
                if not _same_people(author,_people(record.get('all_autor_rusname'))+_people(record.get('all_autor_name')),partial):continue
                if record['work_id'] not in ids:ids.append(record['work_id'])
            if len(ids)!=1:return None
            work=self.client.json('https://api.fantlab.ru/work/'+str(ids[0])+'/extended',stop,budget)
            if not isinstance(work,dict) or work.get('work_id')!=ids[0]:raise ValueError('Catalog work changed')
        # The innermost parent that numbers its books: a cycle (work type 4) or a novel-epic (13: «Властелин Колец», whose
        # three novels are its volumes; 2026-10-29, Tolkien). Its forewords and appendices are extras ("plus").
        chains=(work.get('parents') or {}).get('cycles') or []
        cycles=[chain[-1] for chain in chains if isinstance(chain,list) and chain and isinstance(chain[-1],dict) and chain[-1].get('work_type_id') in (4,13) and type(chain[-1].get('work_id')) is int]
        work_url='https://fantlab.ru/work'+str(work.get('work_id'))
        if len(cycles)>1:
            # 0.31.0 (series_certainty): the work sits in several unrelated cycles (FantLab's "conditional" cycles group
            # books by their setting: «Оно» is in «Дерри» and «Касл-Рок»). Doubtful: never the first one.
            return {'provider':'fantlab','name':'; '.join(text(c.get('work_name')) for c in cycles if text(c.get('work_name')))[:300],'number':'','doubt':'several_series','source_url':work_url}
        if not cycles:return None
        api='https://api.fantlab.ru/work/'+str(cycles[0]['work_id'])+'/extended'
        cycle=self.client.json(api,stop,budget)
        if not isinstance(cycle,dict) or not isinstance(cycle.get('children'),list):raise ValueError('Malformed catalog cycle')
        numbered=[c for c in cycle['children'] if isinstance(c,dict) and c.get('deep')==1 and c.get('work_type_id')==work.get('work_type_id') and not c.get('plus')]
        position=next((index for index,child in enumerate(numbered,1) if child.get('work_id')==work['work_id']),None)
        # 0.30.0 item 6 (Sergei 2026-11-18): the series in the language it was written in ("Harry Potter", not «Гарри Поттер»).
        # 0.31.0 (R1): the candidate also carries the cycle's Russian name and its language, for the one naming rule
        # (canonical_names.series_name, applied where the sources are read).
        import canonical_names
        russian=text(cycles[0].get('work_name') or cycle.get('work_name'))
        name=text(canonical_names.series_original(cycle) or russian)
        if not name:return None
        citation='https://fantlab.ru/work'+str(cycles[0]['work_id'])
        self._gap_receipt(api,result,citation,['series','number'])
        language=_language_code(cycle.get('lang_code'))
        found={'provider':'fantlab','name':series_spelling(name),'number':str(position) if position else '','number_from':'counted' if position else '','source_url':citation,
               'name_russian':series_spelling(russian),'language':language}
        if language=='en' and name!=russian:found['name_english']=name
        if any(marker in text(cycle.get('work_type_name') or cycle.get('work_type')).casefold() for marker in ('условный','вселенная','conditional','universe')):
            found['doubt']='universe'  # a setting or a universe in place of a series
        # R21: the number is counted from the cycle order. A work FantLab does not number (an extra, another kind of work)
        # has none here; the book's own name may still give it (series_certainty).
        return found

    def _gap_receipt(self,url,result,citation,fields):
        result['sources'].append(self.client.receipt(url)|{'url':citation,'api_url':url,'kind':'catalog_gap','verified_identity':False,'fields':fields})

    def _gap_fantlab(self,title,author,partial,stop,budget,result):
        from local_identity import title_key
        url='https://api.fantlab.ru/search-works?'+urllib.parse.urlencode({'q':title,'onlymatches':1})
        records=self.client.json(url,stop,budget)
        if not isinstance(records,list):raise ValueError('Malformed catalog search')
        ids=[]
        for record in records[:5]:
            if not isinstance(record,dict) or type(record.get('work_id')) is not int or not 0<record['work_id']<10**10:continue
            if title_key(title) not in {title_key(v) for v in _fantlab_names(record)}:continue
            if not any(isinstance(v,str) and _name_matches(author,v,partial) for v in (record.get('all_autor_name'),record.get('all_autor_rusname'))):continue
            if record['work_id'] not in ids:ids.append(record['work_id'])
        if len(ids)!=1:return None
        api='https://api.fantlab.ru/work/'+str(ids[0])+'/extended'
        data=self.client.json(api,stop,budget)
        if not isinstance(data,dict) or data.get('work_id')!=ids[0]:raise ValueError('Catalog work changed')
        if any(marker in text(data.get('work_type_name')).casefold() for marker in ('antholog','collection','сборник','цикл','cycle','эпопея')):return None
        authors=[a for a in data.get('authors',[]) if isinstance(a,dict) and a.get('type')=='autor'] if isinstance(data.get('authors'),list) else []
        if len(authors)!=1:return None
        native=text(authors[0].get('name'));latin=_latin_credit(authors[0].get('name_orig')) or text(authors[0].get('name_orig'))
        if not any(v and _name_matches(author,v,partial) for v in (native,latin)):return None
        language=_language_code(data.get('lang_code'))
        original=text(data.get('work_name_orig') or data.get('work_name'))
        if not original:return None
        citation='https://fantlab.ru/work'+str(ids[0])
        self._gap_receipt(api,result,citation,['original_title','original_language','author'])
        # 0.31.0 (R1): the English title, where FantLab has it: the original itself for a work written in English, else
        # the one English title its translations list (two different ones are not chosen between).
        english=original if language=='en' and re.search('[A-Za-z]',original) and not re.search('[А-Яа-яЁё]',original) else ''
        if not english and language not in ('','ru','en'):
            listed=[]
            for entry in data.get('translations') or []:
                if isinstance(entry,dict) and entry.get('lang_code')=='en':
                    for translation in entry.get('translations') or []:
                        listed.extend(text(t.get('title')) for t in (translation.get('titles') or []) if isinstance(t,dict) and text(t.get('title'))) if isinstance(translation,dict) else None
            listed=list(dict.fromkeys(listed))
            if len(listed)==1 and re.search('[A-Za-z]',listed[0]) and not re.search('[А-Яа-яЁё]',listed[0]):english=listed[0]
        return {'provider':'fantlab','work_id':'fantlab:'+str(ids[0]),'source_url':citation,'language':language,
            'original_title':original,'english_title':english,'title_native':text(data.get('work_name')),'author_native':native,'author_latin':latin}

    def _gap_wikidata(self,title,author,partial,stop,budget,result):
        """The catalog record of this work from Wikidata (0.31.0 step 2: _wikidata_book, matched by the title, every
        credited author and its type), or None: {'provider', 'work_id', 'source_url', 'language', 'original_title',
        'english_title', 'title_native', 'author_native', 'author_latin', 'author_family', 'author_given'}. Only a record
        that says what language the work was written in is one."""
        record=self._wikidata_book(title,author,partial,stop,budget,result)
        if not record or record.get('conflict'):return None
        entry=self._wikidata_catalog(record,title)
        return entry if entry.get('language') else None

    def _author_latin(self,title,author,stop,budget,result,folders=(),known=(),also=()):
        """Ruling 39: the original-language name of a foreign author credited only in Cyrillic. In order: the Latin name
        the book's own folders or the library's filed authors give for a credit with a foreign first name (no request);
        this work's catalog records (FantLab's original name, Wikidata's), looked up by the title and, for an edition's
        volume title («Хранители. Летопись первая»), by its book title («Хранители»); the person's own Wikidata record
        (its Russian label or alias is the credit, its writing language says which spelling is right); then a Goodreads
        search. Every request goes through the client (its cache, per-site bounds and lane). {'state': 'found', 'name',
        'source_url'}; {'state': 'russian', 'source_url'} when the work or person writes in Russian; None when
        inconclusive (nothing matched, a source closed, the budget spent). A name a source gives, never a transliteration."""
        import local_identity
        def attempt(function):
            try:return function()
            except ResearchWait:return None
            except sqlite3.OperationalError as error:
                if not catalog_busy(error):raise
                return None
            except (ValueError,TypeError,KeyError,AttributeError):return None
        local=_local_latin(author,folders,known)
        if local:return local
        # also: other titles the work may be known by (0.31.0: the part after the number of a name that only looks like
        # "Series N. Title"; since R22 the title itself stays whole, and no catalog knows the whole name).
        titles=list(dict.fromkeys(t for t in (title,edition_volume(title)[0],*[text(value) for value in also or ()]) if t))
        functions=[]
        for value in titles:
            functions.append(lambda value=value:self._gap_fantlab(value,author,False,stop,budget,result))
        functions.append(lambda:self._author_wikidata(author,stop,budget,result))
        for value in titles:
            functions.append(lambda value=value:self._gap_wikidata(value,author,False,stop,budget,result))
        for function in functions:
            entry=attempt(function)
            if not entry:continue
            if entry.get('state') in ('found','russian'):return entry
            if entry.get('language')=='ru':return {'state':'russian','source_url':entry.get('source_url','')}
            latin=text(entry.get('author_latin'))
            # The record already matched this work's author by the Cyrillic name (its native name) or the Latin one.
            if latin and local_identity.script(latin)=='latin':
                # 0.31.0 step 3: the English title by the one title rule (any original language but Russian, R1), with the
                # work's language, and what the record shows of the name's order (never a guess: canonical_names.latin_order).
                import canonical_names
                english,rule=canonical_names.book_title('',entry)
                return {'state':'found','name':latin,'source_url':entry.get('source_url',''),'title':english if rule=='english' else '',
                        'language':text(entry.get('language')),'original_title':text(entry.get('original_title')),'order':_order_evidence(entry)}
        for value in titles:
            found=attempt(lambda value=value:self._author_goodreads(value,author,stop,budget))
            if found:return found
        return None
    def _author_wikidata(self,author,stop,budget,result):
        """Ruling 39 (2026-10-29, Tolkien): the person's own Wikidata record. Searched by the credit as written with the
        first name first («Джон Рональд Руэл Толкин»), then by the surname; kept only when exactly one human's Russian
        label or alias is this very name (the same words, any order; no initial standing for a word) and the record says
        the language the person writes in (P6886, else P1412). Writes in Russian: 'russian'. Writes in another language:
        its English label, which must be in Latin letters. Anything else: None (the question is asked, ruling 51)."""
        import local_identity
        from public_work_identity import ids
        tokens=text(author).split()
        if len(tokens)<2:return None
        given_first=' '.join(tokens[1:]+tokens[:1]) if local_identity.surname_first(author)[1]=='already surname first' else text(author)
        def search(value):
            url='https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode({'action':'wbsearchentities','search':value,'language':'ru','uselang':'ru','type':'item','limit':7,'format':'json'})
            data=self.client.json(url,stop,budget);hits=data.get('search') if isinstance(data,dict) else None
            if not isinstance(hits,list):raise ValueError('Malformed Wikidata search evidence')
            return list(dict.fromkeys(str(h.get('id')) for h in hits[:7] if isinstance(h,dict) and re.fullmatch(r'Q[1-9][0-9]{0,11}',str(h.get('id','')))))
        def same(name):
            match=local_identity.compare_names(author,name)
            return bool(match and match['match']=='same' and not match['subset'] and match.get('exact'))
        for value in dict.fromkeys((given_first,tokens[0] if local_identity.surname_first(author)[1]=='already surname first' else tokens[-1])):
            found=search(value)
            if not found:continue
            url='https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode({'action':'wbgetentities','ids':'|'.join(found),'props':'labels|aliases|claims','languages':'en|ru','format':'json'})
            records=self.client.json(url,stop,budget).get('entities')
            if not isinstance(records,dict):raise ValueError('Malformed Wikidata person evidence')
            people=[]
            for key in found:
                entity=records.get(key)
                if not isinstance(entity,dict) or entity.get('id')!=key or 'Q5' not in ids(entity,'P31'):continue
                names=[text((entity.get('labels') or {}).get('ru',{}).get('value'))]+[text(a.get('value')) for a in (entity.get('aliases') or {}).get('ru',[]) if isinstance(a,dict)]
                if any(n and same(n) for n in names):people.append(entity)
            if len(people)>1:return None
            if not people:continue
            entity=people[0];languages=ids(entity,'P6886') or ids(entity,'P1412')
            citation='https://www.wikidata.org/wiki/'+entity['id']
            self._gap_receipt(url,result,citation,['author'])
            if not languages:return None
            if 'Q7737' in languages:return {'state':'russian','source_url':citation}
            latin=text((entity.get('labels') or {}).get('en',{}).get('value'))
            if latin and local_identity.script(latin)=='latin' and not re.search(r'[\d()]',latin):
                # 0.31.0 step 3: a name whose order the app cannot tell is ordered by the person's own family-name field
                # (P734), one more request; without it the name stays as Wikidata writes it (never a guess).
                import canonical_names,wikidata_books
                order={}
                if len(latin.split())>=2 and canonical_names.latin_order(latin)[1]==canonical_names.ORDER_UNKNOWN:
                    person={'family_ids':wikidata_books.ids(entity,'P734'),'given_ids':wikidata_books.ids(entity,'P735')}
                    keys=list(dict.fromkeys(person['family_ids']+person['given_ids']))[:6]
                    if keys:
                        try:order=wikidata_books.name_order(person,wikidata_books.entities(self.client.json(wikidata_books.entities_url(keys),stop,budget),keys))
                        except (ResearchWait,ValueError,TypeError):order={}
                return {'state':'found','name':latin,'source_url':citation,'title':'','order':order}
            return None
        return None
    def _author_goodreads(self,title,author,stop,budget):
        """Ruling 39: the Latin credit of this work's Goodreads search results: a result titled as this book whose one
        Latin-script author is the same person as the Cyrillic credit (compare_names). None unless exactly one."""
        from local_identity import title_key,script
        url='https://www.goodreads.com/search?'+urllib.parse.urlencode({'q':title+' '+author,'search_type':'books'})
        names=set()
        for _,shown,credited in goodreads_results(self.client.read(url,stop,budget))[:10]:
            match=GOODREADS_SERIES.match(shown)
            if title_key(match[1] if match else shown)!=title_key(title):continue
            names.update(name for name in credited if script(name)=='latin' and _name_matches(author,name))
        return {'state':'found','name':names.pop(),'source_url':url} if len(names)==1 else None
    def _learn_author(self,kind,credit,target,source_url,title):
        """Ruling 39: what the lookup found, kept once per author as a lasting author rule (actor 'assistant', the source
        cited), so the author's other books follow without a lookup; Sergei's own answer or a retraction replaces it.
        Research's only write: at most 1 s behind another writer, and a busy catalog never fails the lookup (the book is
        filed by this research all the same; the next book of the author looks again)."""
        import author_rules
        try:
            with connect(self.client.database,timeout=1) as db:
                author_rules.setup(db)
                author_rules.append(db,kind,credit,target=target,actor='assistant',source=source_url or 'public research',question=title)
        except sqlite3.OperationalError as error:
            if not catalog_busy(error):raise
    def _full_name(self,title,author,candidates,citation_for):
        """One unique full name whose words include the local partial name."""
        from local_identity import title_key,words,compare_names
        chosen={}
        for record_title,record_authors,citation in candidates:
            if not isinstance(record_title,str) or title_key(record_title)!=title_key(title):continue
            if not isinstance(record_authors,list) or len(record_authors)!=1 or not isinstance(record_authors[0],str):continue
            name=text(record_authors[0]);match=compare_names(author,name)
            if match and len(words(name))>=2:chosen.setdefault(name,citation)
        if len(chosen)!=1:return None
        name,citation=next(iter(chosen.items()))
        return {'name':name,'source_url':citation}

    def _gap_openlibrary(self,title,author,stop,budget,result):
        from openlibrary_index import lookup
        local=lookup(self.local_index,title)
        result['local_openlibrary']={'status':local['status'],'purpose':'work/author identity only; not narrative order'}
        if local['status']=='covered':
            candidates=[]
            for record in local['works']:
                if len(record['authors'])==1:
                    for name in record['authors'][0]['names']:
                        candidates.append((record['title'],[name],'https://openlibrary.org'+record['id']))
            found=self._full_name(title,author,candidates,lambda item:item)
            if found:
                found['local_index_receipt']=local['receipt'];result['local_openlibrary']['matched']=found
                return found
        url='https://openlibrary.org/search.json?'+urllib.parse.urlencode({'title':title,'author':author,'limit':5,'fields':'key,title,author_name'})
        data=self.client.json(url,stop,budget);docs=data.get('docs') if isinstance(data,dict) else None
        if not isinstance(docs,list):raise ValueError('Malformed catalog search')
        candidates=[(d.get('title'),d.get('author_name'),'https://openlibrary.org'+d['key']) for d in docs[:5] if isinstance(d,dict) and re.fullmatch('/works/OL[1-9][0-9]{0,11}W',str(d.get('key','')))]
        found=self._full_name(title,author,candidates,None)
        if found:self._gap_receipt(url,result,found['source_url'],['author'])
        return found

    def _gap_googlebooks(self,title,author,stop,budget,result):
        url='https://www.googleapis.com/books/v1/volumes?'+urllib.parse.urlencode({'q':'intitle:'+title+' inauthor:'+author,'maxResults':5,'printType':'books','fields':'items(id,volumeInfo(title,authors))'})
        data=self.client.json(url,stop,budget);items=data.get('items',[]) if isinstance(data,dict) else None
        if not isinstance(items,list):raise ValueError('Malformed catalog search')
        candidates=[]
        for item in items[:5]:
            info=item.get('volumeInfo') if isinstance(item,dict) else None
            if isinstance(info,dict) and isinstance(item.get('id'),str) and re.fullmatch(r'[A-Za-z0-9_-]{4,40}',item['id']):
                candidates.append((info.get('title'),info.get('authors'),'https://books.google.com/books?id='+item['id']))
        found=self._full_name(title,author,candidates,None)
        if found:self._gap_receipt(url,result,found['source_url'],['author'])
        return found

    def _gap_itunes(self,title,author,stop,budget,result):
        country='RU' if re.search('[А-Яа-яЁё]',title+author) else 'US'
        url='https://itunes.apple.com/search?'+urllib.parse.urlencode({'term':title+' '+author,'media':'audiobook','entity':'audiobook','limit':5,'country':country})
        data=self.client.json(url,stop,budget);items=data.get('results') if isinstance(data,dict) else None
        if not isinstance(items,list):raise ValueError('Malformed catalog search')
        candidates=[]
        for item in items[:5]:
            if not isinstance(item,dict) or type(item.get('collectionId')) is not int:continue
            candidates.append((item.get('collectionName'),[item.get('artistName')],'https://books.apple.com/audiobook/id'+str(item['collectionId'])))
        found=self._full_name(title,author,candidates,None)
        if found:self._gap_receipt(url,result,found['source_url'],['author'])
        return found

SERIES_WHY={
    'wikidata':'Series and position from the one series statement of the Wikidata work matching the locally agreed title, every credited author and its type as a written work (ruling R5, Sergei 2026-11-22: one source naming a series is enough).',
    'litres':'Series and explicit position on the canonical Litres book page matching the exact title and all credited authors; not the series total or retailer card order.',
    'goodreads':'Series and position from the Goodreads book record or explicit series entry, joined to the exact book id, title and all locally agreed authors (Sergei 2026-10-18: Goodreads is the series source).',
    'fantlab':'Series from the FantLab cycle holding the work matching the locally agreed title and author; FantLab gives no number, so the position is counted in the cycle order (Goodreads listed no series).'}

def series_source(series):
    """Where the series and number came from, recorded on the metadata facts."""
    url=series.get('source_url','')
    found={'provider':series.get('provider') or ('wikidata' if 'wikidata.org' in url else 'local' if not url else 'catalog'),'url':url}
    # 0.31.0 (A6): where the number came from ('source', 'counted' from FantLab's cycle order, 'names' or 'tags': the
    # book's own, series_certainty.NUMBER_FROM) and which naming rule named the series (canonical_names.series_name).
    # 'name_provider' (and 'name_url'): the source the series' English name came from, where that is another source than
    # the one the series and its number came from (the files' own tags, or FantLab with Wikidata's English name).
    for key in ('number_from','name_rule','name_provider','name_url'):
        if series.get(key):found[key]=str(series[key])
    return found

GOODREADS_SERIES=re.compile(r'^(.*\S)\s*\(([^()]*\S),\s*#([^()]*)\)\s*$')

def goodreads_results(raw):
    """Search result rows (book id, title as shown, credited names). Leads only; the book page decides."""
    from html import unescape
    rows=[]
    for block in raw.decode('utf-8','replace').split('itemtype="http://schema.org/Book"')[1:]:
        link=re.search(r'class="bookTitle"[^>]*href="/book/show/(\d{1,12})[^"]*"[^>]*>\s*<span[^>]*>([^<]*)</span>',block)
        if not link:continue
        names=[text(unescape(name)) for name in re.findall(r'class="authorName"[^>]*>\s*<span itemprop="name">([^<]*)</span>',block)]
        rows.append((link[1],text(unescape(link[2])),[name for name in names if name]))
    return rows

def goodreads_book(raw,book_id):
    """(title, credited names, [(series title, position)]) from the book page's own embedded record, or None."""
    found=re.search(rb'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',raw,re.S)
    if not found:return None
    try:
        state=strict_json(found[1])['props']['pageProps']['apolloState']
        book=state[state['ROOT_QUERY']['getBookByLegacyId({"legacyId":"%s"})'%book_id]['__ref']]
        if str(book.get('legacyId'))!=str(book_id):return None
        edges=[book.get('primaryContributorEdge')]+list(book.get('secondaryContributorEdges') or [])
        names=[text(state[edge['node']['__ref']].get('name')) for edge in edges if isinstance(edge,dict) and edge.get('role','Author')=='Author' and edge.get('node')]
        series=[(text(state[item['series']['__ref']].get('title')),text(item.get('userPosition'))) for item in book.get('bookSeries') or [] if isinstance(item,dict) and item.get('series')]
        return text(book.get('title')),[name for name in names if name],series
    except (KeyError,TypeError,AttributeError):return None

def goodreads_series(raw,url,book_id,title,author):
    """Provider-owned explicit position, joined to an independently bound search book id.

    The series UI often shows only a primary coauthor. It may confirm that one
    known person, but never substitutes series-level credits for book authors.
    The caller must establish every author on the same search result book id.
    """
    from local_identity import title_key
    class Props(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=True);self.headers=[];self.lists=[];self.canonical=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a.get('href'))
            kind=a.get('data-react-class')
            if kind in ('ReactComponents.SeriesHeader','ReactComponents.SeriesList'):
                data=strict_json(a.get('data-react-props','').encode('utf-8'))
                (self.headers if kind.endswith('SeriesHeader') else self.lists).append(data)
    try:
        page=Props();page.feed(raw.decode('utf-8','strict'))
        if page.canonical!=[url] or len(page.headers)!=1:return None
        name=text(page.headers[0]['title']).removesuffix(' Series')
        if not name:return None
        found=[]
        for data in page.lists:
            books,positions=data['series'],data['seriesHeaders']
            if not isinstance(books,list) or not isinstance(positions,list) or len(books)!=len(positions):return None
            for entry,position in zip(books,positions):
                book=entry.get('book',{})
                if str(book.get('bookId'))!=str(book_id):continue
                number=re.fullmatch(r'Book ([1-9]\d{0,3})',position) if isinstance(position,str) else None
                shown=GOODREADS_SERIES.match(text(book.get('title')))
                if not number or not shown or shown[3]!=number[1] or title_key(shown[2])!=title_key(name):return None
                if title_key(book.get('bookTitleBare'))!=title_key(title) or title_key(shown[1])!=title_key(title):return None
                if not re.fullmatch(r'/book/show/'+re.escape(str(book_id))+r'(?:[.-][^/?#]+)?',str(book.get('bookUrl',''))):return None
                primary=text((book.get('author') or {}).get('name'))
                if not primary or not any(_same_people(person,[primary]) for person in _people(author)):return None
                found.append({'provider':'goodreads','name':name,'number':number[1],'source_url':url,
                              'book_id':str(book_id),'position_basis':'explicit_series_header_and_matching_book_title'})
        return found[0] if len(found)==1 else None
    except (ValueError,UnicodeError,KeyError,TypeError,AttributeError):return None

def _people(value):
    """The people in a credit such as "Лена Обухова, Наталья Тимошенко"."""
    return [name for name in (text(part) for part in re.split(r'\s*(?:[,;&]|\sи\s|\sand\s)\s*',str(value or ''))) if name]

def _same_people(local,others,partial=False):
    """Every locally credited person is one of the source's credited people (any script or word order)."""
    names=_people(local)
    return bool(names) and all(any(_name_matches(name,other,partial) for other in others) for name in names)

def _tagged_series(row):
    """The sources carry their own series tags (source_gate compares them with the verified series)."""
    return any(text({k.casefold():v for k,v in m.get('metadata',{}).get('tags',{}).items()}.get(key)) for m in row.get('members',[]) for key in ('series','series-part','series_part'))

def _name_matches(local,other,partial=False):
    """Same person in any script or word order; a surname-only local name may match a full one."""
    from local_identity import compare_names
    match=compare_names(local,other)
    return bool(match) and (partial or not match['subset'] or len(str(other).split())<len(str(local).split()))

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
def _exact_people(author,names):
    return bool(names) and len(_people(author))==len(names) and _same_people(author,names) and _same_people(', '.join(names),_people(author))

def _page_credit(url,raw,page,titles,authors):
    if urllib.parse.urlsplit(url).hostname not in RETAIL_HOSTS:return credited_pair(page,titles,authors)
    from litres_evidence import book
    from local_identity import title_key
    record=book(raw,url)
    people=[]
    for alias in authors:
        for name in _people(alias):
            if not any(_name_matches(name,known) and _name_matches(known,name) for known in people):people.append(name)
    if record and title_key(record['title']) in {title_key(t) for t in titles} and _exact_people(', '.join(people),record['authors']):
        return {'title':record['title'],'author':', '.join(record['authors']),'excerpt':'Litres main Book/Audiobook author relationship; narrator/related products excluded'}
    return None

def _page_record(url,raw,pair):return {'url':url,'kind':'recording_credit' if urllib.parse.urlsplit(url).hostname in RECORDING_HOSTS else 'publisher_or_journal','sha256':hashlib.sha256(raw).hexdigest(),'retrieved_utc':_stamp(),'credit':pair,'verified_identity':bool(pair)}|({'provider':'Litres'} if urllib.parse.urlsplit(url).hostname in RETAIL_HOSTS else {})
def _wait(waits,answered=()):
    """Retry when the candidate can actually progress, not when any one source reopens.

    A stage is blocked when every source it tried was closed and none answered.
    The candidate needs all its blocked stages open again, so it waits for the
    latest of their earliest reopenings. When no stage is blocked the closed
    sources are optional alternatives and the earliest reopening is used.
    """
    if not waits:return None
    answered=set(answered or ())
    blocked=[]
    for hosts in STAGES.values():
        closed=[w for w in waits if w.source in hosts]
        if closed and not answered&hosts:blocked.append(min(closed,key=lambda w:w.retry_at))
    other=[w for w in waits if not any(w.source in hosts for hosts in STAGES.values())]
    if other:blocked.append(min(other,key=lambda w:w.retry_at))
    wait=max(blocked,key=lambda w:w.retry_at) if blocked else min(waits,key=lambda w:w.retry_at)
    return {'source':wait.source,'reason':wait.reason,'retry_at':wait.retry_at,'kind':wait.kind,'scope':wait.scope}


_ORDINALS={'перв':1,'втор':2,'трет':3,'четверт':4,'четвёрт':4,'пят':5,'шест':6,'седьм':7,'восьм':8,'девят':9,'десят':10}
_VOLUME_WORDS=r'(?:летопись|хроника|книга|том|часть|volume|vol\.|book)'
_VOLUME_NUMBER=r'(\d{1,3}|[ivx]{1,5}|(?:перв|втор|трет|четв[её]рт|пят|шест|седьм|восьм|девят|десят)[а-яё]{0,3})'
_TRAILING_VOLUME=re.compile(r'^(.*?\S)\s*[.,:;–—-]\s*'+_VOLUME_WORDS+r'\s+'+_VOLUME_NUMBER+r'\s*\.?$',re.I)
_LEADING_VOLUME=re.compile(r'^\s*'+_VOLUME_WORDS+r'\s+'+_VOLUME_NUMBER+r'\s*[.:–—-]\s*(\S.*)$',re.I)

def _volume_number(value):
    value=value.casefold()
    if value.isdigit():return int(value)
    roman={'i':1,'ii':2,'iii':3,'iv':4,'v':5,'vi':6,'vii':7,'viii':8,'ix':9,'x':10}
    if value in roman:return roman[value]
    return next((n for stem,n in _ORDINALS.items() if value.startswith(stem.replace('ё','е')) or value.startswith(stem)),None)

def edition_volume(title):
    """(book title, volume number or None) of an edition's volume title: «Хранители. Летопись первая» -> («Хранители», 1),
    «Книга 2. Меч ликтора» -> («Меч ликтора», 2). The title as it is (None) when it names no volume. Used only to look a
    book up by the title catalogs know it by; the volume number is evidence to check a found series position against,
    never a series position by itself (rulings 50 and 52)."""
    value=text(title)
    match=_TRAILING_VOLUME.match(value)
    if match and re.search(r'[^\W\d_]{2}',match[1]):return match[1].strip(' .,:;'),_volume_number(match[2])
    match=_LEADING_VOLUME.match(value)
    if match and re.search(r'[^\W\d_]{2}',match[2]):return match[2].strip(' .,:;'),_volume_number(match[1])
    return value,None

# Ruling 72b (Sergei 2026-10-29): a series name Sergei spells differently from the sources that capitalise it (FantLab and
# Goodreads write «Властелин Колец»). Keys are the name casefolded, «ё» as «е»; any other name is kept as the source gives it.
SERIES_SPELLINGS={'властелин колец':'Властелин колец'}

def series_spelling(name):
    value=text(name)
    return SERIES_SPELLINGS.get(value.casefold().replace('ё','е'),value)

def _fantlab_names(record):
    """A FantLab search record's names: its original and Russian names, and each of its other names, which come as one
    text («Хранители кольца; Хранители; Дружество кольца», 2026-10-29, Tolkien)."""
    names=[v for v in (record.get('name'),record.get('rusname'),record.get('altname')) if isinstance(v,str) and v]
    alt=record.get('altname') if isinstance(record.get('altname'),str) else ''
    return names+[part for part in re.split(r'\s*;\s*|\s+/\s+',alt) if part]

def _ancestor_folders(row):
    """The names of a book's folders, up to four levels above each file (ruling 39's first step reads them: _local_latin)."""
    ancestors=[]
    for member in row.get('members') or []:
        folder=ntpath.dirname(member['path'])
        for _ in range(4):
            name=ntpath.basename(folder)
            if not name or name in ancestors:break
            ancestors.append(name);folder=ntpath.dirname(folder)
    return ancestors

def _local_latin(author,folders=(),known=()):
    """Ruling 39, 2026-10-29 (Tolkien): a foreign author's Latin spelling the library itself already holds, read before any
    request: a folder of this book named for the person in Latin letters («J. R. R. Tolkien» above «Джон Рональд Руэл
    Толкин»), else an author the library already files in Latin letters. The name must be the credit's person (the
    surname in the other script and every first name or initial paired, compare_names), exactly one such spelling must
    exist, and only a credit whose first name is a foreign one counts: a Russian or unknown first name says nothing about
    the language the person writes in. None otherwise."""
    import local_identity
    if not local_identity.foreign_given(author):return None
    for kind,values in (('folder',folders),('known',known)):
        found={}
        for value in values:
            value=text(value)
            if local_identity.script(value)!='latin' or not 2<=len(value.split())<=5:continue
            if local_identity.garbled(value) or re.search(r'[\d\[\]()]',value):continue
            match=local_identity.compare_names(author,value)
            if match and not match['subset'] and match['match']=='cross':
                found.setdefault(local_identity.norm(value),value)
        if len(found)==1:
            name=next(iter(found.values()))
            return {'state':'found','name':name,'source_url':('library folder: ' if kind=='folder' else 'library author: ')+name,'title':''}
        if len(found)>1:return None
    return None

def _latin_surname_first(latin,credit,evidence=None):
    """Ruling 33 for the Latin name a source gives a Cyrillic credit (ruling 39): surname first, on evidence only
    (canonical_names.latin_order: the source's own family-name field, a first name the app knows, a Chinese name's own
    order, or the credit in the files showing which word is the surname). evidence: {'family', 'given', 'language'} from
    the record that named the author (_order_evidence). With no evidence the name stays as the source writes it. Until
    0.31.0 a two-word name was turned around whenever the credit's own order was known, whichever way that was: "Liu
    Cixin" (credit «Лю Цысинь», surname first) became "Cixin Liu"."""
    import canonical_names
    return canonical_names.latin_order(latin,credit,evidence)[0]


def _order_evidence(catalog):
    """What a catalog record shows of its author's name order: Wikidata's family and given names, and the work's language."""
    catalog=catalog if isinstance(catalog,dict) else {}
    return {'family':text(catalog.get('author_family')),'given':text(catalog.get('author_given')),'language':text(catalog.get('language'))}


def _language_code(value):
    """A source's language code as research records it: FantLab's own codes for Japanese and Chinese are 'jp' and 'cn'."""
    code={'jp':'ja','cn':'zh'}.get(text(value).casefold(),text(value).casefold())
    return code if re.fullmatch('[a-z]{2,3}',code) else ''


def _held_lookup_fields(row,envelope,title,author):
    """0.31.0 step 2: what the look-up before review found for a held row, from the record kept with it (the research
    cache forgets an answer after seven days; a review-list row may wait longer for Sergei): the same shape as
    retained_gap_fields, or None. Only the record of this very book (id, revision, fingerprint) made for the title and
    author its row shows now."""
    if not isinstance(envelope,dict) or any(envelope.get(key)!=row.get(field) for key,field in (('candidate_id','id'),('revision','revision'),('fingerprint','fingerprint'))):
        return None
    lookup=envelope['result'].get('lookup') if isinstance(envelope.get('result'),dict) else None
    if not isinstance(lookup,dict) or lookup.get('policy')!=LOOKUP_POLICY or not isinstance(lookup.get('found'),dict) or not isinstance(lookup.get('asked'),dict):
        return None
    if (lookup['asked'].get('title'),lookup['asked'].get('author'))!=(text(title),text(author)):
        return None
    found=lookup['found']
    if not found.get('catalog') and not found.get('series'):
        return None
    return {'catalog':copy.deepcopy(found.get('catalog') or {}),'series':copy.deepcopy(found.get('series') or {}),'closed':[],'unfilled':[],
            'retained_sources':copy.deepcopy(found.get('receipts') or [])}


def _latin_credit(value):
    value=text(value)
    if not re.search('[\u3040-\u30ff\u3400-\u9fff]',value):return value
    words=re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ]+)*",value)
    return ' '.join(words) if len(words)==2 else ''


def retained_gap_fields(row, local, envelope):
    """Validated durable research inputs, independent of evictable HTTP bodies.

    The caller also checks dependency-aware author rules against current rules.
    Rebuilding metadata remains mandatory: this never returns an old approval.
    """
    import local_identity, entered_names
    from standing_metadata import validate_policy
    from source_identity import LOCAL_SOURCE_GATE_VERSION
    if not isinstance(envelope, dict) or any(envelope.get(key) != row.get(field) for key, field in
            (('candidate_id', 'id'), ('revision', 'revision'), ('fingerprint', 'fingerprint'))):
        return None
    saved = envelope.get('result')
    if not isinstance(saved, dict) or saved.get('research_version') != RESEARCH_VERSION:
        return None
    if saved.get('local_source_gate_version', LOCAL_SOURCE_GATE_VERSION) != LOCAL_SOURCE_GATE_VERSION:
        return None
    facts = saved.get('metadata_facts'); review = saved.get('review'); work = saved.get('work')
    if not all(isinstance(value, dict) for value in (facts, review, work)):
        return None
    if saved.get('metadata_holds') or saved.get('manual_metadata_conflicts') or (saved.get('identity_hold') or {}).get('kind') not in (None, 'piece'):
        return None
    if any(reason != local_identity.PIECE_REASON for reason in saved.get('reasons') or []):
        return None
    try:
        validate_policy(row, review, facts)
    except (ValueError, TypeError, KeyError):
        return None
    if work.get('policy_version') != facts.get('policy_version') or work.get('id') not in facts['work_ids'] or work.get('part_book'):
        return None
    current_names = local.get('names_digest', entered_names.NONE)
    saved_names = (facts.get('entered_names') or {}).get('digest', entered_names.NONE)
    if current_names != saved_names:
        return None
    fields = local.get('fields') or {}
    title = text((fields.get('title') or {}).get('value'))
    author = text((fields.get('author') or {}).get('value'))
    if local_identity.title_key(title) not in {local_identity.title_key(alias) for alias in work.get('titles') or []}:
        return None
    if not _same_people(author, work.get('author_aliases') or []) or not _same_people(author, facts['authors']):
        return None
    receipts = [source for source in saved.get('sources') or [] if isinstance(source, dict)
                and re.fullmatch(r'[0-9a-f]{64}', str(source.get('sha256', ''))) and source.get('retrieved_utc')]
    original = text(work.get('original_title'))
    language = (facts.get('original_language') or {}).get('value')
    if original != facts.get('original_title') or language != work.get('original_language'):
        return None
    original_sources = [source for source in receipts if 'original_title' in (source.get('fields') or [])
                        or source.get('kind') == 'catalog_work' and source.get('work_id') == work['id']]
    if not original_sources or not original or not language:
        return None
    source = original_sources[0]
    # The stored work ID must match its provider receipt; a receipt for another book is no bridge.
    if work['id'].startswith('fantlab:') and source.get('url') != 'https://fantlab.ru/work' + work['id'].split(':', 1)[1]:
        return None
    found = {'catalog': {'work_id': work['id'], 'original_title': original, 'language': language,
                        'author_native': author, 'author_latin': review['canonical_author'] if local_identity.script(review['canonical_author']) == 'latin' else '',
                        'title_native': title, 'source_url': source['url']}, 'closed': [], 'unfilled': [],
             'retained_sources': copy.deepcopy(receipts), 'retained_work': copy.deepcopy(work)}
    series = work.get('verified_series') or {}
    if facts.get('series_state') == 'verified':
        if series.get('name') != review.get('series') or str(series.get('number')) != review.get('number'):
            return None
        if not any(source.get('url') == series.get('source_url') and {'series', 'number'} <= set(source.get('fields') or []) for source in receipts):
            return None
        _, volume = edition_volume(title)
        if volume is not None and str(volume) != str(series.get('number')):
            return None
        own = local.get('series') or {}
        entered = set(local.get('names_entered') or []) | set(local.get('names') or {})
        if not {'series', 'number'} & entered:
            if own and (local_identity.title_key(own.get('name', '')) != local_identity.title_key(series['name']) or str(own.get('number')) != str(series['number'])):
                return None
            found['series'] = copy.deepcopy(series)
    return found


def _confirmed_corbett_fields(local, title, author):
    import local_identity
    confirmed = local_identity.confirmed_corbett(title, author)
    if not confirmed:
        return None
    own = local.get('series') or {}
    if own and (local_identity.title_key(own.get('name', '')) not in {local_identity.title_key('Matthew Corbett'), local_identity.title_key('Мэтью Корбетт')}
                or str(own.get('number')) != confirmed['number']):
        return None
    return {'catalog': {'work_id': 'user:corbett-' + confirmed['number'] + '-2026-11-01', 'original_title': confirmed['original_title'],
                        'language': 'en', 'author_native': author, 'author_latin': 'Robert R. McCammon',
                        'title_native': title, 'source_url': confirmed['source_url']},
            'series': {key: confirmed[key] for key in ('name', 'number', 'provider', 'source_url', 'decision_id')},
            'closed': [], 'unfilled': []}



def _routing_series_identity(result):
    """A provider series identity, never a coincidental title or a book-page URL."""
    review = result.get('review') or {}; facts = result.get('metadata_facts') or {}; work = result.get('work') or {}
    series = work.get('verified_series') or {}
    from tolkien_trilogy import author_world,CYCLE
    if author_world(review,facts):return CYCLE
    if facts.get('series_state') != 'verified' or series.get('name') != review.get('series') or str(series.get('number')) != review.get('number'):
        return None
    url = text(series.get('source_url'))
    if re.fullmatch(r'https://fantlab\.ru/work[1-9]\d*', url):
        return url
    match = re.fullmatch(r'https://www\.goodreads\.com/series/([1-9]\d*)(?:-[^/?#]+)?', url)
    return 'https://www.goodreads.com/series/' + match[1] if match else None


def _routing_member(result):
    review = result.get('review') or {}; facts = result.get('metadata_facts') or {}; work = result.get('work') or {}
    authors = facts.get('authors'); ids = facts.get('work_ids')
    if not isinstance(authors, list) or not authors or not isinstance(ids, list) or len(ids) != 1 or ids[0] != work.get('id'):
        return None
    if not all(isinstance(author, str) and author.strip() for author in authors) or review.get('canonical_author') != '; '.join(authors):
        return None
    return {'work_id': ids[0], 'authors': list(authors)}


def _drop_doubtful_series(result, why):
    """A series a source found turns out doubtful after the review was built (R25): take it out of the review, the facts,
    the work and the evidence, and record what was dropped (metadata_facts gap_search 'series_doubt'), in place. The book
    goes on without a series."""
    review = result.get('review') or {}; facts = result.get('metadata_facts') or {}; work = result.get('work') or {}
    found = work.get('verified_series') or {}
    dropped = {'provider': text(found.get('provider')), 'name': text(review.get('series')), 'number': text(review.get('number')), 'why': why,
               'source_url': text(found.get('source_url'))}
    review['series'] = ''; review['number'] = ''
    facts['series_state'] = 'omitted_unknown'
    facts.pop('series_source', None)
    search = facts.setdefault('gap_search', {}) if isinstance(facts.get('gap_search', {}), dict) else {}
    search['series_doubt'] = (list(search.get('series_doubt') or []) + [dropped])[:6]
    work['verified_series'] = {}
    result['evidence'] = [item for item in result.get('evidence') or [] if not (isinstance(item, dict) and item.get('field') in ('series', 'number'))]


def attach_shared_routing(result, peers=()):
    """Attach routing proof to newly accepted metadata, never to old job manifests.

    Peers must be caller-validated current research/approved results, with current
    source, saved-name and rule bindings. Stable series URLs establish membership;
    their shared display name alone never does. Explicit user decisions are
    scoped to exact works/authors and are attributed as user decisions.
    """
    import local_identity
    from shared_routing import build, RoutingEvidenceError
    from tolkien_trilogy import apply as trilogy_decision,author_world,DECISION
    out = trilogy_decision(result)
    review = out.get('review'); facts = out.get('metadata_facts'); work = out.get('work') or {}
    member = _routing_member(out)
    if not isinstance(review, dict) or not isinstance(facts, dict) or member is None:
        return out
    # This producer is also called again at approval. Revalidate only its exact
    # typed legacy decision before rebuilding, never retain an unbound world name.
    from curated_decisions import LEGACY_WORLD,validate as validate_curated_decision
    prior_legacy_world=False
    for record in out.get('evidence') or []:
        if isinstance(record,dict) and record.get('source_kind')=='curated_user_decision' and record.get('decision_ref')==LEGACY_WORLD:
            validate_curated_decision(record,{'fingerprint':facts.get('source_fingerprint')},review,facts)
            prior_legacy_world=True
    # A new review cannot carry a prior receipt whose name/source binding may be stale.
    facts.pop('shared_routing', None)
    series = None; universe = None
    sid = _routing_series_identity(out)
    if sid:
        members = {member['work_id']: member}
        for peer in peers:
            if not isinstance(peer, dict) or _routing_series_identity(peer) != sid:
                continue
            item = _routing_member(peer)
            if item is None:
                continue
            # Canonical credit ordering/initial variants of the same complete team
            # do not turn one author into a shared-author series.
            if _exact_people('; '.join(item['authors']), member['authors']) and _exact_people('; '.join(member['authors']), item['authors']):
                item['authors'] = list(member['authors'])
            if item['work_id'] in members and item != members[item['work_id']]:
                # R25 (Sergei 2026-11-22; it follows R22): the series' members carry conflicting author credits for one
                # work. That series is doubtful, and a doubtful series is treated as not found: the book gets no series
                # and goes on. It used to stop the book with 'Series membership has conflicting author credits. Confirm
                # this book in Edit names.' Only a series a source found reaches here (a series he typed or saved has no
                # source identity), so his own answers are never dropped.
                _drop_doubtful_series(out, 'source_conflict')
                sid = None
                break
            members[item['work_id']] = item
        if sid:
            series = {'id': sid, 'name': review['series'], 'basis': 'catalog', 'evidence': [sid], 'members': list(members.values())}
    # Exact Omen memberships confirmed on 2026-11-01 and 2026-11-02.
    omen = local_identity.CONFIRMED_OMEN_WORKS
    for number, title, author, _ in omen:
        if (local_identity.title_key(review.get('title', '')) == local_identity.title_key(title)
                and len(member['authors']) == 1 and _exact_people(member['authors'][0], [author])
                and review.get('number') == number and local_identity.title_key(review.get('series', '')) in {'omen', 'the omen'}):
            others = [{'work_id': 'user:omen-' + position + '-' + decided, 'authors': [credit]}
                      for position, _, credit, decided in omen if position != number]
            series = {'id': 'user:omen-series-2026-11-01', 'name': review['series'], 'basis': 'user',
                      'evidence': ['user:shared-series-decision-2026-11-01', 'user:omen-memberships-2026-11-02'],
                      'members': [member] + others}
            break
    names = (out.get('approval') or {}).get('names') or {}
    entered = set((facts.get('entered_names') or {}).get('fields') or [])
    expected = {'fantlab:1667': ('The Fellowship of the Ring', '1'), 'fantlab:1668': ('The Two Towers', '2'), 'fantlab:1669': ('The Return of the King', '3')}.get(work.get('id'))
    if (expected and work.get('original_title') == expected[0] and review.get('series') == 'Властелин колец'
            and review.get('number') == expected[1] and sid == 'https://fantlab.ru/work1693'
            and len(member['authors']) == 1 and any(_exact_people(member['authors'][0], [alias]) for alias in
                ('J. R. R. Tolkien', 'Tolkien J. R. R.', 'John Ronald Reuel Tolkien', 'Джон Рональд Руэл Толкин'))
            and 'universe' not in names and 'universe' not in entered
            and (not review.get('universe') or prior_legacy_world and review.get('universe')=='Middle-earth')):
        review['universe'] = 'Middle-earth'
        from curated_decisions import evidence as decision_evidence,LEGACY_WORLD
        item=decision_evidence(out,LEGACY_WORLD,'universe','Middle-earth')
        if item not in out.setdefault('evidence', []):out['evidence'].append(item)
        universe = {'id': 'user:middle-earth-2026-11-01', 'name': 'Middle-earth', 'basis': 'user',
                    'evidence': ['user:middle-earth-decision-2026-11-01'],
                    'members': [dict(member, series_id=sid)]}
    if author_world(review,facts):
        universe={'id':'user:middle-earth-trilogy-2026-11-04','name':'Middle-earth','basis':'user',
                  'evidence':[DECISION],'members':[dict(member,series_id=sid)]}
    # General worlds use an explicit identity-bound world membership, never just a
    # universe label. Providers/user-decision producers may retain this in the work.
    world = work.get('verified_world')
    if isinstance(world, dict) and world.get('name') == review.get('universe') and world.get('id') and world.get('basis') in ('catalog', 'user'):
        members = {member['work_id']: dict(member, series_id=sid)}
        for peer in peers:
            candidate = (peer.get('work') or {}).get('verified_world') if isinstance(peer, dict) else None
            item = _routing_member(peer) if isinstance(peer, dict) else None
            if not item or not isinstance(candidate, dict) or candidate.get('id') != world['id']:
                continue
            item = dict(item, series_id=_routing_series_identity(peer))
            if (peer.get('review') or {}).get('series') and item['series_id'] is None:
                continue
            if item['work_id'] in members and item != members[item['work_id']]:
                raise RoutingEvidenceError('World membership has conflicting book identities. Confirm this book in Edit names.')
            members[item['work_id']] = item
        universe = {'id': world['id'], 'name': world['name'], 'basis': world['basis'],
                    'evidence': list(world.get('evidence') or []), 'members': list(members.values())}
    if series is not None or universe is not None:
        facts['shared_routing'] = build(review, facts, series=series, universe=universe)
    return out
