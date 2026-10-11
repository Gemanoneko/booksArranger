"""Positive named collection contents bound to exact current local sources."""
import hashlib,json,os,re,uuid
from html.parser import HTMLParser
from pathlib import Path
from source_identity import norm,filename_identity,author_matches,text

class Contents(HTMLParser):
    EXCLUDED={'header','footer','nav','aside','script','style'}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events=[];self.links=[];self.skip=0;self.heading=None;self.heading_text=[]
        self.paragraph=False;self.paragraph_text=[];self.table_depth=0;self.table_rows=[]
        self.row_depth=0;self.current=[];self.anchors=[];self.anchor=None;self.nested=False
    def handle_starttag(self,tag,attrs):
        if tag in self.EXCLUDED:self.skip+=1;return
        if self.skip:return
        attrs=dict(attrs)
        if tag in ('h1','h2','h3','h4','h5','h6'):
            self.heading=tag;self.heading_text=[]
        if tag=='p' and not self.table_depth:self.paragraph=True;self.paragraph_text=[]
        if tag=='table':
            if not self.table_depth:self.table_rows=[];self.nested=False
            else:self.nested=True
            self.table_depth+=1
        if tag=='tr' and self.table_depth:
            if not self.row_depth:self.current=[];self.anchors=[]
            self.row_depth+=1
        if tag=='a':self.anchor={'href':attrs.get('href',''),'text':''}
    def handle_data(self,data):
        if self.skip:return
        if self.heading:self.heading_text.append(data)
        if self.paragraph:self.paragraph_text.append(data)
        if self.row_depth:self.current.append(data)
        if self.anchor:self.anchor['text']+=data
    def handle_endtag(self,tag):
        if tag in self.EXCLUDED:
            if self.skip:self.skip-=1
            return
        if self.skip:return
        if tag==self.heading:
            self.events.append(('heading',' '.join(' '.join(self.heading_text).split())));self.heading=None
        if tag=='p' and self.paragraph:
            self.events.append(('paragraph',' '.join(' '.join(self.paragraph_text).split())));self.paragraph=False
        if tag=='a' and self.anchor:
            self.links.append(self.anchor)
            if self.row_depth:self.anchors.append(self.anchor)
            self.anchor=None
        if tag=='tr' and self.row_depth:
            self.row_depth-=1
            if not self.row_depth:self.table_rows.append((' '.join(' '.join(self.current).split()),self.anchors))
        if tag=='table' and self.table_depth:
            self.table_depth-=1
            if not self.table_depth:self.events.append(('table',None if self.nested else self.table_rows))

def parse_contents(raw,title):
    if not isinstance(raw,bytes) or len(raw)>2*1024*1024:raise ValueError('Collection page exceeds supported bounds')
    parser=Contents();parser.feed(raw.decode('utf8','replace'));records=[]
    named=[i for i,(kind,value) in enumerate(parser.events) if kind=='heading' and
        (norm(title)==norm(value) or norm(value).startswith(norm(title)) and re.search(r'выпуск|том|volume',value,re.I))]
    if len(named)!=1:raise ValueError('Collection page identity unverified')
    begin=named[0]+1;end=next((i for i in range(begin,len(parser.events)) if parser.events[i][0]=='heading'),len(parser.events))
    region=parser.events[begin:end]
    # Provenance is the immediate paragraph associated with this named heading,
    # followed by exactly one contents table. Footer/sidebar text is excluded.
    if len(region)<2 or region[0][0]!='paragraph' or region[1][0]!='table' or sum(kind=='table' for kind,_ in region)!=1:
        raise ValueError('Associated collection contents/provenance unavailable')
    provenance=region[0][1]
    fan=r'самодельн|любительск|сетевая публикация|fan-made|fan collection|self-made'
    if len(provenance)>1200 or not re.search(fan,provenance,re.I) or re.search(r'(?:\bnot\b|\bno\b|\bне\b).{0,30}(?:'+fan+')',provenance,re.I):
        raise ValueError('Fan assembly provenance unavailable')
    rows=region[1][1]
    if rows is None:raise ValueError('Collection nested contents unsupported')
    for line,links in rows:
        order=re.match(r'^\s*(\d{1,3})[.)\s]+',line)
        works=[a for a in links if re.fullmatch(r'(?:https://fantlab.ru)?/work[1-9][0-9]{0,9}',a['href'])]
        authors=[a for a in links if re.fullmatch(r'(?:https://fantlab.ru)?/autor[1-9][0-9]{0,9}',a['href'])]
        if not order:
            if works or authors or re.match(r'^\s*(?:#|№)?\s*\d',line):raise ValueError('Collection component row unsupported')
            continue # Only noncomponent headers may be ignored.
        if len(works)!=1 or not authors or len(authors)>30:raise ValueError('Collection component row unsupported')
        identity=int(re.search(r'work([0-9]+)$',works[0]['href'])[1])
        records.append({'order':int(order[1]),'work_id':identity,'title':text(works[0]['text']),'authors':[text(a['text']) for a in authors],'basis':line[:1800]})
    if not records or len(records)>100:raise ValueError('Collection ordered contents unavailable')
    if [r['order'] for r in records]!=list(range(1,len(records)+1)) or len({r['work_id'] for r in records})!=len(records):raise ValueError('Collection order or component identity conflicts')
    return records,parser.links

def bind_collection(row,title,records,works):
    members=row.get('members',[])
    if not members or len(members)!=len(records):raise ValueError('Collection source membership incomplete')
    if row.get('source_partition_uncertain') or any(m.get('missing') or m.get('error') or m.get('order_conflict') for m in members):raise ValueError('Collection sources or order uncertain')
    bound=[];names=[]
    for index,(member,record) in enumerate(zip(members,records),1):
        work=works.get(record['work_id'])
        if not work or work.get('work_id')!=record['work_id']:raise ValueError('Collection component identity unavailable')
        credits=[a for a in work.get('authors',[]) if isinstance(a,dict) and a.get('type')=='autor']
        author_names=[text(a.get('name') or a.get('name_orig')) for a in credits]
        aliases=[text(a.get('name')) for a in credits]+[text(a.get('name_orig')) for a in credits]
        titles=[text(work.get('work_name')),text(work.get('work_name_orig'))]+[text(v) for v in work.get('work_name_alts',[])]
        if not author_names or any(not author_matches(value,{norm(a) for a in aliases}) for value in record['authors']):raise ValueError('Collection component author role conflicts')
        if norm(record['title']) not in {norm(t) for t in titles}:raise ValueError('Collection component title conflicts')
        tags={k.casefold():v for k,v in member.get('metadata',{}).get('tags',{}).items()}
        local=filename_identity(member.get('filename',''));title_aliases={norm(t) for t in titles if norm(t)}
        track_title=text(tags.get('title'));filename_title=text(local['title'])
        # Every available identity-bearing clue must agree; a matching filename
        # cannot override a different explicit constituent title (or vice versa).
        named=bool(re.search(r'[^\W\d_]',filename_title))
        if track_title and norm(track_title) not in title_aliases:raise ValueError('Collection embedded title conflicts with its component')
        if named and norm(filename_title) not in title_aliases:raise ValueError('Collection filename title conflicts with its component')
        if not track_title and not named:raise ValueError('Collection track does not match its component')
        if tags.get('author') and not author_matches(tags['author'],{norm(a) for a in aliases}):raise ValueError('Collection local author conflicts')
        if local.get('author') and not author_matches(local['author'],{norm(a) for a in aliases}):raise ValueError('Collection filename author conflicts')
        numbered=re.match(r'^(\d{1,3})[ _.-]+',member['filename'])
        position=member.get('track') if member.get('track') is not None else int(numbered[1]) if numbered else None
        if position!=index or (member.get('disc') or 1)!=1:raise ValueError('Collection playback order unverified')
        duration=member.get('duration')
        if type(duration) not in (int,float) or duration<=0:raise ValueError('Collection local duration unavailable')
        key=str(uuid.uuid5(uuid.NAMESPACE_URL,os.path.normcase(os.path.abspath(member['path']))))
        bound.append({'work_id':'fantlab:'+str(record['work_id']),'title':text(work.get('work_name_orig') or work.get('work_name')),
            'authors':author_names,'order':index,'source_keys':[key],'source_spans':[{'source_key':key,'start_ms':0,'end_ms':round(duration*1000)}]})
        names.extend(n for n in author_names if n not in names)
    # Explicit common collection label is independent of individual story tags.
    albums={norm({k.casefold():v for k,v in m.get('metadata',{}).get('tags',{}).items()}.get('album')) for m in members}
    parents={str(Path(m['path']).parent) for m in members}
    if albums!={norm(title)} and not (len(parents)==1 and norm(Path(next(iter(parents))).name)==norm(title)):raise ValueError('Positive collection source context missing')
    return {'kind':'fan_assembly','component_count':len(bound),'components':bound},names
