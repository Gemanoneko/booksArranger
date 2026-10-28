"""Local audiobook clues and conservative source partitioning; never canonical metadata."""
import re
from pathlib import Path

VERSION='public-auto-v1'
LOCAL_SOURCE_GATE_VERSION='local-source-gate-v2'
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

SERIES_POSITION_TAGS=('sort_album','sortalbum','albumsort','sort_name','sortname','titlesort','grouping','contentgroup','series-part','series_part')
SERIES_POSITION=re.compile(r'(?:книга|кн\.|book|том|vol\.?|volume|#)\s*№?\s*0*(\d{1,3})(?!\d)',re.I)
def series_positions(tags):
    """The book's numbers in a series its own tags name: "Левиафан. Книга 3" (sort album), "Цикл: Левиафан. Книга 2"
    (grouping), a series-part tag. Part and chapter numbers are not series positions."""
    found=set()
    for key in SERIES_POSITION_TAGS:
        value=str(tags.get(key) or '')
        if key in ('series-part','series_part') and re.fullmatch(r'\s*0*(\d{1,3})\s*',value):found.add(int(value));continue
        found.update(int(m) for m in SERIES_POSITION.findall(value))
    return found

def source_gate(row,work):
    """Observed-source scope only; does not claim commercial recording completeness."""
    members=row['members'];reasons=[];known_anthology=None
    standing=work.get('policy_version')=='standing-17-v1'
    formats={'.mp3','.m4a','.m4b','.aac','.flac','.ogg','.opus','.wav','.wma'} if standing else {'.mp3'}
    if not members or len(members)>500:return ['Source membership uncertain']
    if row.get('source_partition_uncertain'):reasons.append('Source membership uncertain')
    if row.get('anthology_ownership_conflict'):
        reasons.append('Collection source/component binding changed')
    if row.get('anthology_volume'):
        import anthology_volumes
        known_anthology=anthology_volumes.identity(row)
        if not known_anthology:reasons.append('Collection source/component binding changed')
    if any(m.get('missing') or m.get('error') for m in members):reasons.append('Source files unavailable or unreadable')
    if any(Path(m['path']).suffix.lower() not in formats for m in members):reasons.append('Audio format needs an encoding decision')
    if work.get('collection'):
        from collection_identity import bind_collection
        try:
            collection,_=bind_collection(row,work['titles'][0],work['collection_records'],{int(k):v for k,v in work['collection_work_facts'].items()})
            if collection!=work['collection']:reasons.append('Collection source/component binding changed')
        except (KeyError,TypeError,ValueError) as error:reasons.append(str(error))
        return list(dict.fromkeys(reasons))
    aliases={norm(v) for v in work.get('titles',[]) if norm(v)}
    author_aliases={norm(v) for v in work.get('author_aliases',[]) if norm(v)}
    local=work.get('identity_basis')=='local_agreement'
    # v5 (Sergei 2026-10-24, title + author is enough): identity was decided once by
    # local_identity.identify(), with readers, collection credits and garbled tags already set
    # aside; a file name or tag that names a reader or another wording of the title no longer
    # disagrees. Scope, order and format checks below are unchanged.
    one_source=bool(local and work.get('identity_rule'))
    def same_title(raw):
        # Local agreement already compared these names segment by segment (brackets,
        # "Series 03. Title", "Title - 01" chapter names); other paths keep exact matching.
        if title_matches(raw,aliases,work.get('author_aliases',[])):return True
        if not local:return False
        from local_identity import title_segments_match
        return title_segments_match(raw,work.get('titles',[]))
    def source_author(value):
        if author_matches(value,author_aliases) or bool(standing and work.get('full_author_verified') and norm(value) in {norm(v) for v in work.get('source_surnames',[])}):return True
        # Local identity: the same name rules as the agreement (initials such as "Robert J. Sawyer").
        if work.get('identity_basis')=='local_agreement':
            from local_identity import compare_names
            return any(compare_names(value,alias) for alias in work.get('author_aliases',[]))
        return False
    # Split book (v0.15.0): the parts are re-proven from the current row with the same pure
    # check that grouped them; their verified positions replace per-file order clues.
    split=None
    if row.get('split_book'):
        from split_books import check
        split=check(sorted(members,key=lambda m:m['path']),media=False)
        if not split['ok']:reasons.append('Source membership uncertain')
        else:
            proven=dict(zip(sorted(m['path'] for m in members),split['positions']))
            if any(proven[m['path']]!=((m.get('disc') or 1),m.get('track')) for m in members):reasons.append('Playback order uncertain')
    # 0.22.1, item 9 (Sergei 2026-10-25). A clean file-name sequence (track_order) decides the order: the tags of a few
    # files never override it. A disc tag that only repeats the book's place in its series ("Книга 1" folder, disc 1/3:
    # book 1 of 3) is no disc: the series came from the folder structure (local_identity, Author\Series\N. Title).
    import track_order
    sequence=track_order.filename_sequence(track_order.member_names(members)) if len(members)>1 else None
    series_number=str((work.get('verified_series') or {}).get('number') or '') if (work.get('verified_series') or {}).get('folder') else ''
    def series_disc(tags):
        # «Голиаф» (Sergei 2026-10-26; the VanderMeer bug again): disc 3/3 on the third book of a trilogy, its sort-album tag
        # "Левиафан. Книга 3". A disc number that is the book's number in its series, named by the folder structure or by
        # any of its own tags, is no missing disc.
        match=re.fullmatch(r'0*(\d+)(?:/\d+)?',str(tags.get('disc') or tags.get('discnumber') or '').strip())
        if not match:return False
        if series_number and series_number.isdigit() and int(match[1])==int(series_number):return True
        return int(match[1]) in series_positions(tags)
    common_folder=len({str(Path(m['path']).parent) for m in members})==1
    folder_title=filename_identity(Path(members[0]['path']).parent.name).get('title','') if common_folder else ''
    folder_context=bool(common_folder and (title_matches(folder_title,aliases,work.get('author_aliases',[])) or local and same_title(Path(members[0]['path']).parent.name)))
    # A numbered set grouped by its shared file names (groups.py, guard 2) is one folder's book.
    if one_source and common_folder and row.get('numbered_set'):folder_context=True
    # Confirmed anthology binding re-proves this exact folder and every source, including explicitly blank-tag books.
    # This supplies book context only; recording, source availability and playback-order checks still run.
    if known_anthology:folder_context=True
    for m in members:
        tags={k.casefold():v for k,v in m['metadata'].get('tags',{}).items()}
        album=norm(tags.get('album'))
        # A split part's own name adds its number and chapter label to the book name.
        named=filename_identity(split['book_name']+'.x') if split and split['ok'] and split['book_name'] else {'title':'','author':''} if split else filename_identity(m['filename'])
        if one_source:
            # One title source is enough; each file still needs a name or tag that carries the book title
            # (or, for a grouped numbered set, the set's shared name).
            own=[v for v in (tags.get('album'),tags.get('title'),named.get('title'),named.get('author') if row.get('numbered_set') else '',Path(m['path']).parent.name) if v]
            if not any(same_title(v) for v in own) and not (len(members)==1 or folder_context):reasons.append('Source membership uncertain')
            if m.get('order_conflict') and len(members)>1 and not sequence:reasons.append('Playback order uncertain')  # one file: nothing to order
            if len(members)==1 and not work.get('part_book') and not work.get('numbered_part'):
                denominator=re.fullmatch(r'\d+/(\d+)',str(tags.get('track') or tags.get('tracknumber') or '').strip())
                if denominator and int(denominator[1])>1:reasons.append('Source membership uncertain')
                disc_total=re.fullmatch(r'\d+/(\d+)',str(tags.get('disc') or tags.get('discnumber') or '').strip())
                if disc_total and int(disc_total[1])>1 and not series_disc(tags):reasons.append('Source membership uncertain')
            series=work.get('verified_series') or {}
            for key in ('series','series-part','series_part'):
                value=text(tags.get(key))
                if value and series.get('name') and series.get('number') and norm(value)!=norm(series['name'] if key=='series' else series['number']):
                    reasons.append('Source series or position conflicts with verified work')
            continue
        if album and not (same_title(tags.get('album')) if local else title_matches(album,aliases,work.get('author_aliases',[]))):reasons.append('Sources disagree on the title or author')
        if named.get('author'):
            filename_ok=(same_title(named['title']) if local else norm(named['title']) in aliases) and source_author(named['author'])
            if local:
                from local_identity import NARRATOR_MARKER
                # A recorded collection may explicitly carry its reader credit
                # among aliases. Generic name matching cannot turn a different
                # narrator-marked filename into an author identity.
                if NARRATOR_MARKER.search(named['author']) and norm(named['author']) not in author_aliases:
                    filename_ok=False
            if local and not filename_ok:
                from local_identity import filename_matches_local_work
                embedded_authors=[tags[key] for key in ('author','artist') if tags.get(key)]
                filename_ok=filename_matches_local_work(
                    split['book_name']+'.x' if split and split['ok'] and split['book_name'] else m['filename'],
                    work.get('titles',[]),work.get('author_aliases',[]),embedded_authors)
            if not filename_ok:reasons.append('Sources disagree on the title or author')
        # A source recording needs its own title evidence in addition to a filename clue.
        source_title=album or norm(tags.get('title')) if len(members)==1 else album
        if standing and not source_title:
            source_title=norm(named['title']) if len(members)==1 else norm(folder_title) if folder_context else ''
        if not source_title or not (title_matches(source_title,aliases,work.get('author_aliases',[])) or local and source_title in {norm(v) for v in (tags.get('album'),tags.get('title'),named.get('title'),Path(m['path']).parent.name) if v and same_title(v)}):reasons.append('Source membership uncertain')
        if m.get('order_conflict') and len(members)>1 and not sequence:reasons.append('Playback order uncertain')
        # One part of a multi-part set filed as its own book (Sergei 2026-10-13): its set totals are
        # the set's, not this book's. Re-derived at admission (local_identity.revalidate) and
        # admitted only when the part carries its own chapters (merge_service).
        if len(members)==1 and not (local and work.get('part_book')):
            denominator=re.fullmatch(r'\d+/(\d+)',str(tags.get('track') or tags.get('tracknumber') or '').strip())
            if denominator and int(denominator[1])>1:reasons.append('Source membership uncertain')
            disc_total=re.fullmatch(r'\d+/(\d+)',str(tags.get('disc') or tags.get('discnumber') or '').strip())
            if disc_total and int(disc_total[1])>1 and not series_disc(tags):reasons.append('Source membership uncertain')
        if tags.get('author') and not source_author(tags['author']):reasons.append('Sources disagree on the title or author')
        series=work.get('verified_series') or {}
        for key in ('series','series-part','series_part'):
            value=text(tags.get(key))
            if not value:continue
            if not standing:reasons.append('Series position uncertain')
            elif series.get('name') and series.get('number'):
                expected=series['name'] if key=='series' else series['number']
                if norm(value)!=norm(expected):reasons.append('Source series or position conflicts with verified work')
    if len(members)>1:
        tags=[{k.casefold():v for k,v in m['metadata'].get('tags',{}).items()} for m in members]
        albums={norm(t.get('album')) for t in tags};artists={norm(t.get('artist')) for t in tags}
        if known_anthology:artists={'confirmed anthology story credits'}
        if len(artists)>1 and local:
            # Ruling 19 (joined parts): one person spelled two ways ("Иван Петров" / "Петров Иван") is one artist.
            from local_identity import same_person,compare_names
            spelled=list(dict.fromkeys(text(t.get('artist')) for t in tags))
            if '' not in spelled and all(same_person(spelled[0],v) or compare_names(spelled[0],v) for v in spelled[1:]):artists={artists.pop()}
        if (len(albums)!=1 or not next(iter(albums),'')) and not (standing and folder_context) or len(artists)>1:reasons.append('Mixed recordings in this group')
        filename_positions=[]
        for m in members:
            match=re.match(r'^(\d{1,4})[ _.-]+',m['filename'])
            filename_positions.append(int(match[1]) if match else None)
        use_filenames=bool(standing and (folder_context or len(albums)==1 and next(iter(albums),'')) and all(p is not None for p in filename_positions))
        named_order=bool(sequence and standing and (folder_context or len(albums)==1 and next(iter(albums),'')))
        if split:
            # Proven above (embedded track numbers, part numbers in the names or disc folders).
            use_filenames=bool(standing and split['ok'])
            positions=[(m.get('disc') or 1,m.get('track')) for m in members]
        elif named_order:
            use_filenames=True;positions=[(1,position) for position in sequence]
        else:positions=[(1 if series_disc(t) else m.get('disc') or 1,m.get('track') if m.get('track') is not None else filename_positions[i] if use_filenames else None) for i,(m,t) in enumerate(zip(members,tags))]
        if any(p[1] is None for p in positions) or len(set(positions))!=len(positions):reasons.append('Playback order uncertain')
        # No natural filename sort can certify a gap-free recording.
        for disc in {p[0] for p in positions}:
            tracks=sorted(p[1] for p in positions if p[0]==disc and p[1] is not None)
            if tracks and (tracks[0] not in (0,1) or tracks!=list(range(tracks[0],tracks[-1]+1))):reasons.append('Playback order uncertain')
        discs=sorted({p[0] for p in positions})
        if discs!=list(range(1,len(discs)+1)):reasons.append('Playback order uncertain')
        for t in tags:
            total_discs=re.fullmatch(r'\d+/(\d+)',str(t.get('disc') or t.get('discnumber') or '').strip())
            if total_discs and int(total_discs[1])!=len(discs) and not named_order and not series_disc(t):reasons.append('Source membership uncertain')
        # Embedded track numbers must establish order, filename numbering alone remains a clue.
        if not use_filenames and any(not re.fullmatch(r'\d+(?:/\d+)?',str(t.get('track') or t.get('tracknumber') or '').strip()) for t in tags):reasons.append('Playback order uncertain')
        totals=[]
        for t,m in zip(tags,members):
            match=re.fullmatch(r'\d+/(\d+)',str(t.get('track') or t.get('tracknumber') or '').strip())
            if match:totals.append((int(match[1]),m.get('disc') or 1 if not (named_order or series_disc(t)) else 1))
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
