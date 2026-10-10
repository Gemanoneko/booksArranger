"""Local audiobook clues and conservative source partitioning; never canonical metadata."""
import re
from pathlib import Path

VERSION='public-auto-v1'
def norm(value):
    return ''.join(c for c in str(value or '').casefold().replace('ё','е') if c.isalnum())

def text(value):
    return ' '.join(str(value or '').split())[:300]

def filename_identity(value):
    value=Path(value).stem
    value=re.sub(r'\s*\[[^\]]{0,100}\]\s*',' ',value)
    value=re.sub(r'\s*[-–—]\s*(?:19|20)\d{2}\s*$','',value)
    value=re.sub(r'^\s*\d{1,4}[ _.-]+','',value).strip()
    pieces=re.split(r'\s+[–—-]\s+',value,maxsplit=1)
    if len(pieces)==2 and all(len(norm(p))>=3 for p in pieces):
        return {'author':text(pieces[0]),'title':text(pieces[1])}
    return {'title':text(value),'author':''}

def clues(member,root=''):
    metadata=member.get('metadata',{});tags={k.casefold():v for k,v in metadata.get('tags',{}).items()};result=[]
    def add(kind,field,value):
        value=text(value)
        if value:result.append({'kind':kind,'field':field,'value':value,'verified':False})
    for field in ('album','title','artist','album_artist','albumartist','author','narrator','reader','series','language','track','disc'):
        add('embedded',field,tags.get(field,''))
    parsed=filename_identity(member['filename'])
    for field,value in parsed.items():add('filename',field,value)
    parent=Path(member['path']).parent
    for folder in (parent,parent.parent):
        if root and norm(str(folder))==norm(str(Path(root))):continue
        parsed=filename_identity(folder.name)
        for field,value in parsed.items():add('folder',field,value)
    return result

def partition(member):
    """Contradictory identities cannot become one folder-derived book."""
    tags={k.casefold():v for k,v in member['metadata'].get('tags',{}).items()}
    album=text(tags.get('album'));artist=text(tags.get('album_artist') or tags.get('albumartist') or tags.get('artist'))
    parent=Path(member['path']).parent
    if Path(member['path']).suffix.lower()=='.m4b':return str(Path(member['path']))+'\x1fSingle audiobook file'
    if album:
        disc=re.fullmatch(r'(?:cd|disc|disk|диск)[ _.-]*(\d+)',parent.name,re.I)
        base=parent.parent if disc else parent
        return str(base)+'\x1fAlbum '+norm(album)+'\x1fArtist '+norm(artist)
    parsed=filename_identity(member['filename'])
    if parsed.get('author'):
        return str(parent)+'\x1fFilename work '+norm(parsed['author'])+'\x1f'+norm(parsed['title'])
    # Numbered files remain one provisional set, held until recording/order evidence exists.
    if re.match(r'^\d{1,4}[ _.-]',member['filename']):return str(parent)+'\x1fUnverified numbered source set'
    return str(Path(member['path']))+'\x1fStandalone source'

def source_gate(row,work):
    """Observed-source scope only; does not claim commercial recording completeness."""
    members=row['members'];reasons=[]
    if not members or len(members)>500:return ['Source membership uncertain']
    if row.get('source_partition_uncertain'):reasons.append('Source membership uncertain')
    if any(m.get('missing') or m.get('error') for m in members):reasons.append('Source files unavailable or unreadable')
    if any(Path(m['path']).suffix.lower()!='.mp3' for m in members):reasons.append('Audio format needs an encoding decision')
    aliases={norm(v) for v in work.get('titles',[]) if norm(v)}
    author_aliases={norm(v) for v in work.get('author_aliases',[]) if norm(v)}
    for m in members:
        tags={k.casefold():v for k,v in m['metadata'].get('tags',{}).items()}
        album=norm(tags.get('album'))
        named=filename_identity(m['filename'])
        if album and not title_matches(album,aliases,work.get('author_aliases',[])):reasons.append('Sources disagree on the title or author')
        if named.get('author') and (norm(named['title']) not in aliases or not author_matches(named['author'],author_aliases)):
            reasons.append('Sources disagree on the title or author')
        # A source recording needs its own title evidence in addition to a filename clue.
        source_title=album or norm(tags.get('title')) if len(members)==1 else album
        if not source_title or not title_matches(source_title,aliases,work.get('author_aliases',[])):reasons.append('Source membership uncertain')
        if m.get('order_conflict'):reasons.append('Playback order uncertain')
        if len(members)==1:
            denominator=re.fullmatch(r'\d+/(\d+)',str(tags.get('track') or tags.get('tracknumber') or '').strip())
            if denominator and int(denominator[1])>1:reasons.append('Source membership uncertain')
            disc_total=re.fullmatch(r'\d+/(\d+)',str(tags.get('disc') or tags.get('discnumber') or '').strip())
            if disc_total and int(disc_total[1])>1:reasons.append('Source membership uncertain')
        if tags.get('author') and not author_matches(tags['author'],author_aliases):reasons.append('Sources disagree on the title or author')
        for key in ('series','series-part','series_part'):
            if tags.get(key):reasons.append('Series position uncertain')
    if len(members)>1:
        tags=[{k.casefold():v for k,v in m['metadata'].get('tags',{}).items()} for m in members]
        albums={norm(t.get('album')) for t in tags};artists={norm(t.get('artist')) for t in tags}
        if len(albums)!=1 or not next(iter(albums),'') or len(artists)>1:reasons.append('Mixed recordings in this group')
        positions=[(m.get('disc') or 1,m.get('track')) for m in members]
        if any(p[1] is None for p in positions) or len(set(positions))!=len(positions):reasons.append('Playback order uncertain')
        # No natural filename sort can certify a gap-free recording.
        for disc in {p[0] for p in positions}:
            tracks=sorted(p[1] for p in positions if p[0]==disc and p[1] is not None)
            if tracks and (tracks[0] not in (0,1) or tracks!=list(range(tracks[0],tracks[-1]+1))):reasons.append('Playback order uncertain')
        discs=sorted({p[0] for p in positions})
        if discs!=list(range(1,len(discs)+1)):reasons.append('Playback order uncertain')
        for t in tags:
            total_discs=re.fullmatch(r'\d+/(\d+)',str(t.get('disc') or t.get('discnumber') or '').strip())
            if total_discs and int(total_discs[1])!=len(discs):reasons.append('Source membership uncertain')
        # Embedded track numbers must establish order, filename numbering alone remains a clue.
        if any(not re.fullmatch(r'\d+(?:/\d+)?',str(t.get('track') or t.get('tracknumber') or '').strip()) for t in tags):reasons.append('Playback order uncertain')
        totals=[]
        for t,m in zip(tags,members):
            match=re.fullmatch(r'\d+/(\d+)',str(t.get('track') or t.get('tracknumber') or '').strip())
            if match:totals.append((int(match[1]),m.get('disc') or 1))
        if totals and any(n!=sum(p[0]==disc for p in positions) for n,disc in totals):
            reasons.append('Source membership uncertain')
    return list(dict.fromkeys(reasons))

def author_matches(value,aliases):
    # Token order varies across filename/publisher credits; initials alone cannot establish identity.
    tokens=[norm(t) for t in re.split(r'[\s,;]+',str(value)) if norm(t)]
    if len(tokens)<2 or any(len(t)<2 for t in tokens):return False
    return norm(value) in aliases or norm(' '.join(reversed(tokens))) in aliases


def title_matches(value,titles,authors):
    value=norm(value)
    if value in titles:return True
    credits=set()
    for author in authors:
        tokens=[t for t in re.split(r'[\s,;]+',author) if t]
        if len(tokens)==2:
            credits.update((norm(author),norm(tokens[0][0]+tokens[1]),norm(tokens[1]+tokens[0][0])))
    return any(value in {credit+title,title+credit} for title in titles for credit in credits)
