"""Persistent provisional audiobook groups assembled from catalog evidence only."""
import hashlib
import sqlite3
import json
from pathlib import Path
import re
import uuid
import math
from metadata import propose, future_audio_tags
from collections import Counter
from source_identity import partition, clues, VERSION as SOURCE_VERSION
import split_books
# Changing the grouping algorithm re-syncs every root once (split books, v0.15.0; same-title sets, v0.22.0).
SAME_TITLE_VERSION = 'same-title-v4'  # v2: Senua's 0.22.0 review G1, G2; v3: N4 (generic titles, the file-name works check); v4: N10 (chapter names are no works)
# Ruling 19 (Sergei 2026-10-24): the parts of one book in one folder are joined (same album, one author).
SAME_ALBUM_VERSION = 'same-album-v4'  # v2: Senua's 0.22.0 review G3; v3: N6 (the works check for a plain album group too); v4: N11 (chapter-named title tags are no works)
# Ruling 19a (Sergei 2026-10-24): explicitly marked .m4b parts with their own chapters are joined, chapters kept; the
# other .m4b sets of one folder, album and artist are one candidate whose chapters decide (part_sets.decide).
M4B_PARTS_VERSION = 'm4b-parts-v2'
GROUP_VERSION = SOURCE_VERSION + '+' + split_books.VERSION + '+' + SAME_TITLE_VERSION + '+' + SAME_ALBUM_VERSION + '+' + M4B_PARTS_VERSION
DISC_SUFFIX = re.compile(r'[\s_.,:;-]*[\(\[]?(?:cd|disc|disk|диск)[\s_.-]*\d+[\)\]]?\s*$', re.I)

def setup(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS book_groups(
      id TEXT PRIMARY KEY, root TEXT, scope TEXT, revision INTEGER, fingerprint TEXT,
      evidence TEXT, review TEXT DEFAULT '', approved INTEGER DEFAULT 0,
      changed INTEGER DEFAULT 0, UNIQUE(root,scope))''')
    if 'superseded' not in {r[1] for r in connection.execute('PRAGMA table_info(book_groups)')}:connection.execute('ALTER TABLE book_groups ADD COLUMN superseded INTEGER NOT NULL DEFAULT 0')
    connection.execute('CREATE TABLE IF NOT EXISTS book_group_algorithm(id INTEGER PRIMARY KEY,version TEXT)')
    prior=connection.execute('SELECT version FROM book_group_algorithm WHERE id=1').fetchone()
    if not prior or prior[0]!=GROUP_VERSION:
        connection.execute('DELETE FROM book_group_sync') if connection.execute("SELECT 1 FROM sqlite_master WHERE name='book_group_sync'").fetchone() else None
        connection.execute('INSERT OR REPLACE INTO book_group_algorithm VALUES(1,?)',(GROUP_VERSION,))
    connection.execute('CREATE TABLE IF NOT EXISTS book_catalog_revision(id INTEGER PRIMARY KEY, revision INTEGER NOT NULL)')
    # An initialized status poll must not reserve the SQLite writer merely to
    # ignore the already-present seed. Bootstrap/concurrent initializers retain
    # the same idempotent INSERT when the singleton is genuinely absent.
    if connection.execute('SELECT 1 FROM book_catalog_revision WHERE id=1').fetchone() is None:
        connection.execute('INSERT OR IGNORE INTO book_catalog_revision VALUES(1,0)')
    connection.execute('CREATE TABLE IF NOT EXISTS book_group_sync(root TEXT PRIMARY KEY, revision INTEGER NOT NULL)')
    for operation in ('INSERT','DELETE'):
        connection.execute(f'CREATE TRIGGER IF NOT EXISTS book_files_{operation.lower()} AFTER {operation} ON files BEGIN UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1; END')
    columns=('root','path','size','modified','kind','metadata','error','missing')
    changed=' OR '.join('OLD.'+c+' IS NOT NEW.'+c for c in columns)
    connection.execute('CREATE TRIGGER IF NOT EXISTS book_files_update AFTER UPDATE OF '+','.join(columns)+' ON files WHEN '+changed+' BEGIN UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1; END')
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_retirements'").fetchone():
        for operation in ('INSERT','UPDATE','DELETE'):
            connection.execute(f'CREATE TRIGGER IF NOT EXISTS book_retirements_{operation.lower()} AFTER {operation} ON source_retirements BEGIN UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1; END')
    setup_part_chapters(connection)
    setup_part_volumes(connection)
    setup_group_member_index(connection)


def setup_group_member_index(connection):
    """Transactionally project exact group membership once, then maintain it on writes.

    This index contains identities only. The scanner still compares the complete
    matching group and context rows, including overlaps and newly added members.
    """
    fresh=not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_group_members'").fetchone()
    connection.execute('CREATE TABLE IF NOT EXISTS catalog_group_members(root TEXT NOT NULL,path TEXT NOT NULL,group_id TEXT NOT NULL,PRIMARY KEY(root,path,group_id))')
    connection.execute('CREATE INDEX IF NOT EXISTS catalog_group_members_by_group ON catalog_group_members(group_id)')
    for operation in ('INSERT','UPDATE','DELETE'):
        remove="DELETE FROM catalog_group_members WHERE group_id=OLD.id;" if operation!='INSERT' else "DELETE FROM catalog_group_members WHERE group_id=NEW.id;"
        insert="INSERT INTO catalog_group_members(root,path,group_id) SELECT DISTINCT NEW.root,json_extract(value,'$.path'),NEW.id FROM json_each(NEW.evidence,'$.members');" if operation!='DELETE' else ''
        connection.execute(f'CREATE TRIGGER IF NOT EXISTS catalog_group_members_{operation.lower()} AFTER {operation} ON book_groups BEGIN {remove}{insert} END')
    if fresh:
        connection.execute("INSERT INTO catalog_group_members(root,path,group_id) SELECT DISTINCT g.root,json_extract(m.value,'$.path'),g.id FROM book_groups g,json_each(g.evidence,'$.members') m")

def setup_part_chapters(connection):
    """M4B parts found at admission to carry their own chapters (Sergei 2026-10-13: each such part
    is its own book). A fact holds only while the file keeps its size and modification time; any
    change to the facts regroups the catalog."""
    connection.execute('CREATE TABLE IF NOT EXISTS part_chapters(root TEXT, path TEXT, size INTEGER, modified TEXT, chapters INTEGER NOT NULL, checked TEXT NOT NULL, PRIMARY KEY(root,path))')
    for operation in ('INSERT','UPDATE','DELETE'):
        connection.execute(f'CREATE TRIGGER IF NOT EXISTS book_part_chapters_{operation.lower()} AFTER {operation} ON part_chapters BEGIN UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1; END')

def chaptered_parts(connection,root):
    """Paths of catalogued files whose recorded own-chapter fact still matches the file."""
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='part_chapters'").fetchone():return frozenset()
    return frozenset(r[0] for r in connection.execute("""SELECT c.path FROM part_chapters c JOIN files f ON f.root=c.root AND f.path=c.path
        WHERE c.root=? AND c.chapters>1 AND c.size=f.size AND c.modified=CAST(f.modified AS TEXT) AND f.error='' AND f.missing=0""",(root,)))

def setup_part_volumes(connection):
    """Ruling 19, 2026-10-24: .m4b files of one set found to be separate volumes of a series (part_sets.decide, from their
    chapters): each is its own book (ruling 15 names it). A fact holds only while the file keeps its size and time;
    any change to the facts regroups the catalog."""
    connection.execute('CREATE TABLE IF NOT EXISTS part_volumes(root TEXT, path TEXT, size INTEGER, modified TEXT, basis TEXT NOT NULL, checked TEXT NOT NULL, PRIMARY KEY(root,path))')
    for operation in ('INSERT','UPDATE','DELETE'):
        connection.execute(f'CREATE TRIGGER IF NOT EXISTS book_part_volumes_{operation.lower()} AFTER {operation} ON part_volumes BEGIN UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1; END')

def volume_parts(connection,root):
    """Paths of catalogued files whose recorded separate-volume fact still matches the file."""
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='part_volumes'").fetchone():return frozenset()
    return frozenset(r[0] for r in connection.execute("""SELECT v.path FROM part_volumes v JOIN files f ON f.root=v.root AND f.path=v.path
        WHERE v.root=? AND v.size=f.size AND v.modified=CAST(f.modified AS TEXT) AND f.error='' AND f.missing=0""",(root,)))

KEPT_BASIS='Kept separate by you'

def kept_parts(connection,root):
    """The recorded volumes Sergei kept separate himself ("Keep as separate books"), still matching their files."""
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='part_volumes'").fetchone():return frozenset()
    return frozenset(r[0] for r in connection.execute("""SELECT v.path FROM part_volumes v JOIN files f ON f.root=v.root AND f.path=v.path
        WHERE v.root=? AND v.basis LIKE ? AND v.size=f.size AND v.modified=CAST(f.modified AS TEXT) AND f.error='' AND f.missing=0""",(root,KEPT_BASIS+'%')))

def separate_books(connection,root,paths):
    """How many of these files are each a current book of its own ("Volume of a series") in the stored groups."""
    count=0
    for path in paths:
        found=connection.execute("""SELECT g.scope,g.evidence FROM catalog_group_members c JOIN book_groups g ON g.id=c.group_id
            WHERE c.root=? AND c.path=? AND g.root=? AND g.superseded=0""",(root,path,root)).fetchall()
        if len(found)==1 and found[0]['scope'].endswith('\x1fVolume of a series') and [m['path'] for m in json.loads(found[0]['evidence'])['members']]==[path]:count+=1
    return count

def record_volumes(connection,root,members,basis):
    """Record the members of a set as separate volumes (their current size and time). Regroups the catalog."""
    import datetime
    connection.execute('CREATE TABLE IF NOT EXISTS part_volumes(root TEXT, path TEXT, size INTEGER, modified TEXT, basis TEXT NOT NULL, checked TEXT NOT NULL, PRIMARY KEY(root,path))')
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    for m in members:
        connection.execute('INSERT OR REPLACE INTO part_volumes VALUES(?,?,?,?,?,?)',(root,m['path'],int(m['size']),str(m['modified']),str(basis)[:200],now))

def retired_sources(connection,root):
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_retirements'").fetchone():return {}
    rows=connection.execute("""SELECT r.* FROM source_retirements r JOIN files f ON f.root=r.root AND f.path=r.path
        WHERE r.root=? AND r.state='removed' AND r.size=f.size AND r.modified=CAST(f.modified AS TEXT) AND f.error='' AND f.missing=0
        ORDER BY r.cleanup_id""",(root,)).fetchall()
    return {r['path']:dict(r) for r in rows}

def _preserve_retired_evidence(old,evidence,retired):
    """Keep the completed group's ordered provenance when active members did not change."""
    previous=json.loads(old['evidence'])
    prior={m['path']:m for m in previous['members']}
    current={m['path']:m for m in evidence['members']}
    if not (set(prior)&set(retired)) or set(prior)!=set(current):return evidence
    if any(prior[path]!=current[path] for path in prior if path not in retired):return evidence
    # Retirement is an external durable fact. Do not bake it into group fingerprint,
    # replace the original member list, or invalidate an already completed revision.
    return previous

def normalized(value):
    return ' '.join(str(value or '').casefold().split())

def numeric(value):
    match=re.match(r'^\s*(\d+)(?:/\d+)?\s*$',str(value or ''))
    return int(match[1]) if match else None

def natural(value):
    return [int(item) if item.isdigit() else item.casefold() for item in re.split(r'(\d+)',value)]

def member(row):
    metadata=json.loads(row['metadata'])
    tags={key.casefold():value for key,value in metadata.get('tags',{}).items()}
    disc=numeric(tags.get('disc') or tags.get('discnumber'))
    track=numeric(tags.get('track') or tags.get('tracknumber'))
    filename=Path(row['path']).name
    filename_match=re.match(r'^(\d+)(?:[-_. ](\d+))?',filename)
    filename_number=int(filename_match[1]) if filename_match else None
    evidence='Embedded disc / track number' if track is not None else 'Filename number; unverified' if filename_number is not None else 'Filename sorting only; order unclear'
    conflict=track is not None and filename_number is not None and track!=filename_number
    if conflict:evidence+=' · Embedded and filename numbers conflict'
    duration=metadata.get('probe',{}).get('format',{}).get('duration')
    try:duration=float(duration) if duration is not None else None
    except (ValueError,TypeError):duration=None
    if duration is not None and (not math.isfinite(duration) or duration<0):duration=None
    return {'path':row['path'],'size':row['size'],'modified':str(row['modified']),
      'error':row['error'],'missing':bool(row['missing']),'metadata':metadata,
      'track_title':metadata.get('track_title') or filename,'filename':filename,
      'source_disc':str(tags.get('disc') or tags.get('discnumber') or ''),
      'source_track':str(tags.get('track') or tags.get('tracknumber') or ''),
      'disc':disc,'track':track if track is not None else filename_number,
      'duration':duration,'order_evidence':evidence,'order_conflict':conflict}

def _legacy_build(rows,split=None):
    """split: {path: (disc, position)} of one proven split book; all its files form one batch."""
    audio=[row for row in rows if row['kind']=='audiobook' and not json.loads(row['metadata']).get('arranger_output')]
    companions=[row for row in rows if row['kind']=='companion']
    companions_by_folder={}
    for index,row in enumerate(companions):
        clue={'path':row['path'],'size':row['size'],'modified':str(row['modified']),'error':row['error'],'missing':bool(row['missing'])}
        companions_by_folder.setdefault(str(Path(row['path']).parent),[]).append((index,clue))
    batches={}
    for row in audio:
        item=member(row)
        parent=Path(row['path']).parent
        tags={key.casefold():value for key,value in item['metadata'].get('tags',{}).items()}
        album=str(tags.get('album') or '').strip()
        # Disc siblings may share a candidate only when an explicit album clue agrees.
        disc_folder=re.fullmatch(r'(?:cd|disc|disk|диск)[ _.-]*(\d+)',parent.name,re.I)
        if split is not None:
            # Positions were proven by split_books.check; filename/tag clues stay in the record.
            scope=split_books.unit(row['path'])[0]+'\x1fSplit book'
            item['disc'],item['track']=split[row['path']][:2]
            item['order_evidence']='Split book part %d%s; %s'%(item['track'],'' if item['disc']==1 else ' of disc %d'%item['disc'],split[row['path']][2])
            item['order_conflict']=False
            grouping='Split book: the parts of one book, grouped by matching title, credits, audio profile and gap-free numbering'
        elif Path(row['path']).suffix.lower()=='.m4b':
            scope=str(Path(row['path']))+'\x1fSingle audiobook file'
            grouping='Existing single audiobook file; it is not a chapter merge candidate'
        elif disc_folder and album:
            scope=str(parent.parent)+'\x1f'+normalized(album)
            if item['disc'] is None:
                item['disc']=int(disc_folder[1]);item['source_disc']='Folder '+disc_folder[1]
                item['order_evidence']+=' · Disc folder number; unverified'
            grouping='Disc folders with matching album clues; membership remains unverified'
        else:
            scope=str(parent)
            grouping='Source folder and album/title clues; membership remains unverified'
        group=batches.setdefault(scope,{'scope':scope,'grouping':grouping,'members':[]})
        group['members'].append(item)
    for group in batches.values():
        members=group['members']
        members.sort(key=lambda item:(item['disc'] if item['disc'] is not None else 0,
            item['track'] is None,item['track'] if item['track'] is not None else 0,natural(item['filename']),item['path']))
        positions={}
        for index,item in enumerate(members,1):
            item['order']=index
            if item['track'] is not None:positions.setdefault((item['disc'] or 0,item['track']),[]).append(item)
        for tied in positions.values():
            if len(tied)>1:
                for item in tied:item['order_conflict']=True;item['order_evidence']+=' · Tied position; order unclear'
        titles=set();artists=set();languages=set();series=set();comments=[]
        for item in members:
            metadata=item['metadata'];tags={key.casefold():value for key,value in metadata.get('tags',{}).items()}
            if tags.get('album'):titles.add(str(tags['album']))
            artist=metadata.get('artist') or metadata.get('author')
            if artist:artists.add(str(artist))
            if metadata.get('edition_language'):languages.add(metadata['edition_language'])
            if metadata.get('series') or metadata.get('number'):series.add((metadata.get('series',''),metadata.get('number','')))
            for key,value in metadata.get('tags',{}).items():
                if key.casefold() in {'comment','comments','©cmt'}:
                    for entry in value if isinstance(value,list) else [value]:
                        if str(entry) not in comments:comments.append(str(entry))
        conflicts=[]
        if len(titles)>1:conflicts.append('Different book album/title clues may indicate mixed works')
        if len(languages)>1:conflicts.append('Different edition languages may indicate mixed recordings')
        if len(artists)>1:conflicts.append('Different author / reader clues; recording unverified')
        if len(series)>1:conflicts.append('Series position conflicts')
        if any(item['error'] or item['missing'] for item in members):conflicts.append('Source files unavailable or unreadable')
        folders={str(Path(item['path']).parent) for item in members}
        related=[clue for index,clue in sorted((item for folder in folders for item in companions_by_folder.get(folder,[])),key=lambda item:item[0])]
        title=next(iter(titles)) if len(titles)==1 else Path(group['scope'].split('\x1f')[0]).name
        metadata={'title':title,'author':'; '.join(sorted(artists)),'artist':'; '.join(sorted(artists)),
          'edition_language':'; '.join(sorted(languages)), 'series':'; '.join(sorted({v[0] for v in series})),
          'number':'; '.join(sorted({v[1] for v in series})), 'tags':{'comments':comments},
          'method':'Catalog grouping evidence','notes':['Author tag may name the reader','Edition / recording unverified']}
        group.update(title_clue=title,artists=sorted(artists),languages=sorted(languages),
          title_evidence=sorted(titles),series_clues=[list(pair) for pair in sorted(series)],
          conflicts=conflicts,companions=related,metadata=metadata,
          order_unverified=True,membership_unverified=True,completeness_unverified=True)
    return batches

def _split_group(items,companions,scope,verdict):
    """One candidate for a proven split book; verdict comes from split_books.check."""
    positions={m['path']:(disc,track,verdict['basis']) for m,(disc,track) in zip(verdict['members'],verdict['positions'])}
    legacy=_legacy_build(items+companions,split=positions)
    group=next(iter(legacy.values()))
    group['scope']=scope
    group['split_book']={'version':split_books.VERSION,'parts':len(group['members']),'order_basis':verdict['basis'],'book_name':verdict['book_name']}
    if not group['title_evidence'] and verdict['book_name']:
        from source_identity import filename_identity
        group['title_clue']=filename_identity(verdict['book_name']+'.x')['title'] or group['title_clue']
    group['local_clues']=[{'path':m['path'],'clues':clues(m)} for m in group['members']]
    return group

def _split_plan(members,scopes,assigned,chaptered=frozenset()):
    """Single-file candidates that are provably the parts of one book (split_books.plan).
    members: {path: member}; scopes: {path: partition scope}; assigned: protected paths;
    chaptered: parts known to carry their own chapters (never joined)."""
    counts=Counter(scope for path,scope in scopes.items() if path not in assigned)
    free=lambda path:path not in assigned and path not in chaptered and counts[scopes[path]]==1
    eligible=[item for path,item in members.items() if free(path)]
    blocked=[item for path,item in members.items() if not free(path)]
    found,_=split_books.plan(eligible,blocked,chaptered)
    return found

def _same_title_sets(members,scopes,assigned,chaptered,taken):
    """Guard 2 (Sergei 2026-10-24, "parts stay together"): files of one folder that are each still a
    book on their own become one book when
      - every one carries the same title tag and the same author/artist tags and no album tag
        (77 chapter files of "Пастушья корона", each tagged "Пастушья корона"), or
      - every one is numbered at the start of its name and shares the part before " - "
        ("01 Моногатари короткие истории - Вступление от переводчика"), and that shared part is
        not a person (an author folder of "NN Author - Title" files holds separate books).
    Whole .m4b files, protected files and parts with their own chapters are never joined here.
    Senua's 0.22.0 review: a junk or garbled title tag ("Аудиокнига", "Без имени") joins nothing (G2); the shared start
    is checked against the people the library credits, a bare surname included (G1); and numbered files whose file-name
    titles name different works ("01 Сапковский - Последнее желание", "02 Сапковский - Меч предназначения") are joined
    only when their folder names an author who is not the shared start (Monogatari: "Нисио Исин - Monogatari Series").
    Returns [{'scope', 'members', 'name', 'basis'}]."""
    from source_identity import filename_identity,norm
    from local_identity import title_key,looks_like_person,clean_title,garbled,JUNK_TITLES,tag_index,work_name,chapter_works
    counts=Counter(scopes[path] for path in scopes)
    folders={}
    for path,item in members.items():
        if path in assigned or path in chaptered or Path(path).suffix.lower()=='.m4b' or counts[scopes[path]]!=1:continue
        folders.setdefault(str(Path(path).parent),[]).append(item)
    found=[];index=None
    for folder,items in folders.items():
        if len(items)<2:continue
        by_title={}
        by_name={}
        for item in items:
            tags={k.casefold():str(v) for k,v in item['metadata'].get('tags',{}).items()}
            if tags.get('album','').strip():continue
            raw=tags.get('title','')
            title='' if garbled(raw) or norm(clean_title(raw)) in JUNK_TITLES else title_key(raw)
            if title:
                credit=tuple(norm(tags.get(k,'')) for k in ('author','album_artist','albumartist','artist'))
                by_title.setdefault((title,credit),[]).append(item)
            numbered=re.match(r'^\s*(\d{1,4})[ _.-]+',item['filename'])
            parsed=filename_identity(item['filename'])
            start=parsed.get('author') or ''
            if numbered and start and not garbled(start) and norm(clean_title(start)) not in JUNK_TITLES:
                by_name.setdefault(norm(start),[]).append((item,start,parsed.get('title') or ''))
        used=set()
        for (title,_),group in sorted(by_title.items(),key=lambda kv:repr(kv[0])):
            if len(group)<2:continue
            # Senua's 0.22.0 review, N4: a generic title tag no list knows ("Запись с диктофона" on "Кинг - Оно" and
            # "Кинг - Мизери") joins nothing when the file names name two or more works besides the tag's own.
            # N10: chapter names are no works ("Пастушья корона 01. Глава 1. Там где ветер", "Пастушья корона 02").
            tag_title=str({k.casefold():v for k,v in group[0]['metadata'].get('tags',{}).items()}.get('title',''))
            tagged=norm(work_name(tag_title))
            if len(set(chapter_works([filename_identity(item['filename']).get('title') or '' for item in group],tag_title))-{'',tagged})>1:continue
            scope=folder+'\x1fSame title '+title
            if scope in taken:continue
            name=' '.join(str({k.casefold():v for k,v in group[0]['metadata'].get('tags',{}).items()}.get('title','')).split())
            found.append({'scope':scope,'members':group,'name':name,'basis':'same title tag'})
            used.update(item['path'] for item in group)
        for key,group in sorted(by_name.items()):
            group=[entry for entry in group if entry[0]['path'] not in used]
            if len(group)<2:continue
            start=group[0][1]
            if index is None:index=tag_index(m['metadata'].get('tags') for m in members.values())
            if looks_like_person(start,index,surname=True):continue  # an author folder of "NN Author - Title" books
            works={norm(work_name(title)) for _,_,title in group}-{''}
            if len(works)>1 and not _folder_names_another_author(group[0][0]['path'],start,index):continue
            scope=folder+'\x1fNumbered set '+key
            if scope in taken:continue
            found.append({'scope':scope,'members':[item for item,_,_ in group],'name':start,'basis':'shared start of the numbered file names'})
    return found

def _folder_names_another_author(path,start,index):
    """True when the file's folder or its parent names an author ("Нисио Исин - Monogatari Series - Сто историй") who is
    not the shared start of its file names: the start is then the book, not the author."""
    from source_identity import filename_identity
    from local_identity import looks_like_person,_person_like,same_person,compare_names,_shares_surname,clean_title
    for folder in (Path(path).parent.name,Path(path).parent.parent.name):
        parsed=filename_identity(folder+'.x')
        who=clean_title(parsed['author'] if parsed.get('author') else folder)
        if not who or not (looks_like_person(who,index) or parsed.get('author') and _person_like(who)):continue
        return not (same_person(who,start) or compare_names(who,start) or _shares_surname(who,start))
    return False

PART_SET_MAX = 30
# Split-rule refusals no chapter list can answer: the files stay books of their own.
HARD_REFUSALS = ('parts are in different places', 'a part is unavailable or unreadable', 'mixed ', 'audio profile unknown',
                 'a part has no known duration', 'duplicate part numbers', 'only one part', 'more than')

def _part_sets(members,scopes,assigned,separate,taken):
    """Ruling 19 (Sergei 2026-10-24, "parts of a bigger book are connected in the correct order"): the whole .m4b files of
    one folder that share their album and artist tags and are each still a book of their own form one candidate, in the
    order their track numbers (else the numbers in their names) give. Their chapters decide in research what it is
    (part_sets.decide: one book, separate volumes, a question, or missing parts); files already found to be separate
    volumes are left out, and so is a folder holding the same part twice (two copies of a name). A set the split rules
    refuse for a reason the chapters cannot answer stays files of their own: different recordings (audio profiles,
    readers or credits), duplicate or unplaced parts, unreadable parts; and so does a folder of more than PART_SET_MAX
    files (chapter files of one book, the split rules' work). Returns [{'scope', 'members', 'positions', 'basis',
    'book_name'}]."""
    import unicodedata
    counts=Counter(scopes.values())
    clusters={}
    for path,item in members.items():
        if path in assigned or path in separate or Path(path).suffix.lower()!='.m4b' or counts[scopes[path]]!=1:continue
        tags={k.casefold():' '.join(str(v).split()) for k,v in item['metadata'].get('tags',{}).items()}
        album=unicodedata.normalize('NFC',tags.get('album','')).casefold()
        if not album:continue
        artist=unicodedata.normalize('NFC',tags.get('artist','')).casefold()
        clusters.setdefault((split_books.unit(path)[0],album,artist),[]).append(item)
    found=[]
    for (unit,album,artist),items in sorted(clusters.items(),key=lambda kv:repr(kv[0])):
        if len(items)<2:continue
        if len(items)>PART_SET_MAX:continue
        stems=[unicodedata.normalize('NFC',Path(m['path']).stem).casefold() for m in items]
        if len(set(stems))!=len(stems):continue  # the same part twice (two copies under one name)
        reasons=split_books.check(sorted(items,key=lambda m:m['path']))['reasons']
        if any(r.startswith(HARD_REFUSALS) for r in reasons):continue
        def number(value):
            match=re.match(r'^\s*(\d{1,4})',str(value or ''))
            return int(match[1]) if match else None
        tags=[{k.casefold():v for k,v in m['metadata'].get('tags',{}).items()} for m in items]
        tracks=[(number(t.get('disc') or t.get('discnumber')) or 1,number(t.get('track') or t.get('tracknumber'))) for t in tags]
        if all(t is not None for _,t in tracks) and len(set(tracks))==len(tracks):
            positions,basis=tracks,'embedded track numbers'
        else:
            named=[re.findall(r'\d{1,4}',Path(m['path']).stem) for m in items]
            positions=[(1,int(n[-1])) if n else None for n in named];basis='numbers in the file names'
            if None in positions or len(set(positions))!=len(positions):continue
        order=sorted(range(len(items)),key=lambda i:positions[i])
        scope=unit+'\x1fPart set '+album+'\x1f'+artist
        if scope in taken:continue
        found.append({'scope':scope,'members':[items[i] for i in order],'positions':[positions[i] for i in order],'basis':basis,'book_name':''})
    return found

def _same_album_parts(members,scopes,assigned,chaptered,taken):
    """Ruling 19 (Sergei 2026-10-24, "parts of a bigger book are joined into that book"): files of one folder that carry
    the same album tag (a trailing CD / disc number aside) and name one author are one book, even when their author or
    album-artist tags are spelled differently or the album-artist tag names the readers (which split them by partition).
    The order is not decided here: the source gate checks the joined book's numbering, and an unclear order or a gap is
    a question on its row with the joined order. Never joined: whole .m4b files (their own chapters would be lost),
    protected or chaptered files, files whose author tags name different people (an anthology, mixed recordings) and
    files in different folders or sources. Returns [{'scope', 'members', 'name', 'basis'}]."""
    from source_identity import norm
    from local_identity import same_person,compare_names
    found=[];albums={}
    for path,item in members.items():
        if path in assigned or path in chaptered or Path(path).suffix.lower()=='.m4b' or '\x1fAlbum ' not in scopes[path]:continue
        tags={k.casefold():str(v) for k,v in item['metadata'].get('tags',{}).items()}
        album=' '.join(str(tags.get('album') or '').split())
        key=norm(DISC_SUFFIX.sub('',album)) or norm(album)
        if key:albums.setdefault((scopes[path].split('\x1fAlbum ')[0],key),[]).append((item,album,tags))
    for (base,key),entries in sorted(albums.items(),key=lambda kv:repr(kv[0])):
        if len({scopes[item['path']] for item,_,_ in entries})<2:continue  # already one book
        # The author credit of each file (author, else artist); the album-artist tag often names the readers.
        credits=list(dict.fromkeys(c for c in (' '.join(str(tags.get('author') or tags.get('artist') or '').split()) for _,_,tags in entries) if c))
        if any(not (norm(a)==norm(b) or same_person(a,b) or compare_names(a,b)) for a in credits for b in credits):continue  # several authors: never joined
        scope=base+'\x1fSame album '+key
        if scope in taken:continue
        name=DISC_SUFFIX.sub('',entries[0][1]).strip() or entries[0][1]
        found.append({'scope':scope,'members':[item for item,_,_ in entries],'name':name,'basis':'same album and one author',
                      'works':_works(sorted(entries,key=lambda e:e[0]['path']),scopes,name)})
    return found

def _works(entries,scopes,name):
    """Senua's 0.22.0 review, G3: the works the title tags of one album's files name, part numbers aside. A work is a
    title that two or more files carry ("Последнее желание 1", "Последнее желание 2") or the one title every file of an
    original group carries; chapter labels and the album's own title (name, its disc number aside) are not works. Two or
    more works: the files may be several books (the Ведьмак disc case), so the joined book is held as Files unclear.
    N11: a chapter label is the whole title's label ("Глава 1. Дом, милый дом - 1", "Часть первая. Фрагмент 2"), and the
    album's own title and a number is a chapter in a set of chapters (local_identity.chapter_works). Returns
    [{'name', 'files'}] or []."""
    from source_identity import norm
    from local_identity import work_name,chapter_works
    album=norm(work_name(name))
    titles=[tags.get('title') or '' for _,_,tags in entries]
    named=[];per_scope={}
    for (item,_,_),title,key in zip(entries,titles,chapter_works(titles,name)):
        named.append((key,work_name(title)));per_scope.setdefault(scopes[item['path']],set()).add(key)
    counts=Counter(key for key,_ in named if key and key!=album)
    works={key for key,n in counts.items() if n>=2}
    works|={next(iter(keys)) for keys in per_scope.values() if len(keys)==1 and next(iter(keys)) not in ('',album)}
    if len(works)<2:return []
    shown={}
    for key,title in named:
        if key in works:shown.setdefault(key,title)
    return [{'name':shown[key],'files':counts[key] or 1} for key in shown]

# The details panel prints a group's 'grouping' line (Judy's part-sets copy check, 2026-10-25): no names, dates or rule
# numbers on screen. Groups stored by an earlier build keep their text until regrouped; shown_grouping() words them the same.
PART_SET_GROUPING='Parts of one folder that share their album and artist. Their chapters decide whether they are one book.'
_OLD_GROUPING=re.compile(r'^One book \((?:Sergei [^)]*)\): files of one folder with the (.*?)(?: \(the parts of one book\))?$')

def shown_grouping(text):
    """The grouping line as the details panel shows it, whichever build stored the group."""
    text=str(text or '')
    if text=='Parts of one folder that share their album and artist: their chapters decide whether they are one book (ruling 19)':return PART_SET_GROUPING
    match=_OLD_GROUPING.match(text)
    return 'One book: files of one folder with the '+match[1]+'.' if match else text

def build(rows,protected=None,chaptered=frozenset(),volumes=frozenset(),kept=frozenset()):
    protected=protected or {};assigned={m['path']:scope for scope,e in protected.items() for m in e['members']};buckets={}
    audio=[row for row in rows if row['kind']=='audiobook' and not json.loads(row['metadata']).get('arranger_output')]
    members={row['path']:member(row) for row in audio}
    scopes={path:assigned.get(path) or partition(item) for path,item in members.items()}
    # Only whole .m4b files (always single-file candidates by partition) are re-filed as their own
    # books; an .m4a may sit in a multi-file group and would be re-encoded (Senua R2-M1).
    # Rulings 19 and 19a (Sergei 2026-10-24): a whole .m4b part with its own chapters stays in its set; the set's chapters
    # decide whether it is one book (part_sets.decide). Only files found to be separate volumes are books of their own:
    # a new scope, so a running automatic pass picks each up (the 2026-10-13 rule filed every chaptered part alone).
    chaptered=frozenset(path for path in volumes if Path(path).suffix.lower()=='.m4b')
    for path in chaptered:
        if path in scopes and path not in assigned:scopes[path]=str(Path(path))+'\x1fVolume of a series'
    split={}
    taken=set(scopes.values())
    for found in _split_plan(members,scopes,assigned,chaptered):
        # Senua M7: a plan whose scope is already used (a reviewed split book retagged beside new
        # files with its old title) is not grouped; its files keep their own held candidates.
        if found['scope'] in taken:continue
        for item in found['members']:scopes[item['path']]=found['scope']
        split[found['scope']]=found
    sets={}
    for found in _same_title_sets(members,scopes,assigned,chaptered,taken|set(split)):
        for item in found['members']:scopes[item['path']]=found['scope']
        sets[found['scope']]=found
    joined={}
    for found in _same_album_parts(members,scopes,assigned,chaptered,taken|set(split)|set(sets)):
        for item in found['members']:scopes[item['path']]=found['scope']
        joined[found['scope']]=found
    part_sets={}
    for found in _part_sets(members,scopes,assigned,chaptered,taken|set(split)|set(sets)|set(joined)):
        for item in found['members']:scopes[item['path']]=found['scope']
        part_sets[found['scope']]=found
    for row in audio:
        buckets.setdefault(scopes[row['path']],[]).append(row)
    output={};companions=[r for r in rows if r['kind']=='companion']
    # Senua R2-M2: same-title neighbours of reviewed split books from one index, built once per
    # build and only when such books exist (no catalog-wide scan per book).
    neighbours=None
    if any(protected[scope].get('split_book') for scope in buckets if scope in protected):
        neighbours={}
        for path,item in members.items():
            neighbours.setdefault((split_books.unit(path)[::2],split_books.book_key(item)),[]).append(item)
    for scope,items in buckets.items():
        if scope in part_sets and {r['path'] for r in items}=={m['path'] for m in part_sets[scope]['members']}:
            group=_split_group(items,companions,scope,part_sets[scope]);parts=group.pop('split_book')
            group['part_set']={'version':M4B_PARTS_VERSION,'parts':parts['parts'],'order_basis':parts['order_basis']}
            group['grouping']=PART_SET_GROUPING
            output[scope]=group
            continue
        if scope in split:
            verdict=split[scope]
            if {r['path'] for r in items}=={m['path'] for m in verdict['members']}:
                output[scope]=_split_group(items,companions,scope,verdict)
                continue
            # Never reached after the collision guard above; fail closed rather than raise: every
            # file goes through the generic path below and stays visible as a held subgroup.
        if scope in protected and protected[scope].get('split_book'):
            # A reviewed split book keeps its scope only while its parts still prove one book,
            # and while no other file beside it carries its book title (Senua minor).
            old=protected[scope];ordered=sorted((member(r) for r in items),key=lambda m:m['path'])
            own={m['path'] for m in ordered};keys={(split_books.unit(m['path'])[::2],split_books.book_key(m)) for m in ordered}
            others=[m for key in sorted(keys,key=repr) for m in neighbours.get(key,()) if m['path'] not in own]
            verdict=split_books.check(ordered,others)
            if verdict['ok']:
                verdict['members']=ordered
                found=_split_group(items,companions,scope,verdict)
                output[scope]=old if found['members']==old['members'] and found['companions']==old['companions'] else found
            else:
                # Fail closed: every member stays visible and the book is held for review.
                merged=[m for value in _legacy_build(items+companions).values() for m in value['members']]
                found=dict(old);found['members']=sorted(merged,key=lambda m:m['path'])
                for order,item in enumerate(found['members'],1):item['order']=order
                found['source_partition_uncertain']=True
                found['conflicts']=list(old.get('conflicts',[]))+['Split book parts no longer prove one book: '+'; '.join(verdict['reasons'][:3])]
                output[scope]=found
            continue
        legacy=_legacy_build(items+companions)
        if scope in protected:
            old=protected[scope]
            if len(legacy)!=1:
                # A reviewed source set retains all its members; no first-subgroup selection.
                merged=[m for value in legacy.values() for m in value['members']]
                prior={m['path']:{k:v for k,v in m.items() if k!='order'} for m in old['members']}
                current={m['path']:{k:v for k,v in m.items() if k!='order'} for m in merged}
                if current==prior:output[scope]=old
                else:
                    found=dict(old);found['members']=sorted(merged,key=lambda m:(m.get('disc') or 0,m.get('track') is None,m.get('track') or 0,m['path']))
                    for order,item in enumerate(found['members'],1):item['order']=order
                    found['source_partition_uncertain']=True;found['conflicts']=list(old.get('conflicts',[]))+['Recording grouping needs stronger evidence']
                    output[scope]=found
                continue
            found=next(iter(legacy.values()));found['scope']=scope;found['grouping']=old['grouping']
            if found['members']==old['members'] and found['companions']==old['companions']:output[scope]=old
            else:
                if 'local_clues' in old:found['local_clues']=[{'path':m['path'],'clues':clues(m)} for m in found['members']]
                output[scope]=found
        else:
            # Punctuation-normalized identity can span differently tagged disc folders.
            # Keep every discovered subgroup visible and held; do not silently omit any.
            for legacy_scope,group in legacy.items():
                selected_scope=scope if len(legacy)==1 else scope+'\x1fProvisional subgroup '+legacy_scope
                group['scope']=selected_scope
                group['grouping']='Per-file embedded/filename identity partition; recording remains unverified'
                group['local_clues']=[{'path':m['path'],'clues':clues(m)} for m in group['members']]
                if len(legacy)>1:
                    group['source_partition_uncertain']=True;group['conflicts'].append('Recording grouping needs stronger evidence')
                if len(group['members'])==1 and not group['title_evidence']:
                    from source_identity import filename_identity
                    group['title_clue']=filename_identity(group['members'][0]['filename'])['title']
                output[selected_scope]=group
    for scope,found in sets.items():
        if scope in output:
            output[scope]['numbered_set']={'version':SAME_TITLE_VERSION,'name':found['name'],'basis':found['basis']}
            output[scope]['grouping']='One book: files of one folder with the '+found['basis']+'.'
            if not output[scope]['title_evidence'] and found['name']:output[scope]['title_clue']=found['name']
    for scope,group in output.items():
        if scope.endswith('\x1fVolume of a series') and len(group['members'])==1:
            # Its own book: the set question was answered (kept: by Sergei's "Keep as separate books", else by its chapters).
            group['volume_of_set']={'kept':group['members'][0]['path'] in kept}
    for scope,found in joined.items():
        if scope in output:
            output[scope]['joined_parts']={'version':SAME_ALBUM_VERSION,'name':found['name'],'basis':found['basis'],'works':found['works']}
            output[scope]['grouping']='One book: files of one folder with the '+found['basis']+'.'
            if found['works']:
                # G3: never converted on its own; the row lists the works so Sergei can approve or choose the files.
                output[scope]['source_partition_uncertain']=True
                output[scope].setdefault('conflicts',[]).append('The title tags name more than one book: '+'; '.join(w['name'] for w in found['works'][:4]))
    # Senua's 0.22.0 review, N6: G3's works check for a plain album group too (one folder, one album, one artist: "Последнее
    # желание 1/2" and "Меч предназначения 1/2" under the album "Ведьмак"). Held as Files unclear listing the works; never
    # converted on its own. Reviewed, approved or queued groups and the other grouping routes keep their own rules.
    # N11: chapter-named title tags ("Глава 1. Дом, милый дом - 1") are no works (_works).
    for scope,group in output.items():
        if scope in protected or scope in split or scope in sets or scope in joined or scope in part_sets:continue
        if '\x1fAlbum ' not in scope or len(group['members'])<2 or group.get('source_partition_uncertain'):continue
        entries=[(m,'',{k.casefold():str(v) for k,v in m['metadata'].get('tags',{}).items()}) for m in sorted(group['members'],key=lambda m:m['path'])]
        album=' '.join(entries[0][2].get('album','').split())
        works=_works(entries,{m['path']:scope for m in group['members']},DISC_SUFFIX.sub('',album).strip() or album)
        if works:
            group['album_works']=works;group['source_partition_uncertain']=True
            group.setdefault('conflicts',[]).append('The title tags name more than one book: '+'; '.join(w['name'] for w in works[:4]))
    return output

def current(connection,root):
    """True when the stored groups match the catalog revision, so page() and sync() write nothing. Read-only."""
    try:
        revision=connection.execute('SELECT revision FROM book_catalog_revision WHERE id=1').fetchone()
        saved=connection.execute('SELECT revision FROM book_group_sync WHERE root=?',(root,)).fetchone()
    except sqlite3.OperationalError:return False  # not set up yet: the first page sets it up
    return bool(revision and saved and saved[0]==revision[0])

def sync(connection,root):
    setup(connection)
    revision=connection.execute('SELECT revision FROM book_catalog_revision WHERE id=1').fetchone()[0]
    saved=connection.execute('SELECT revision FROM book_group_sync WHERE root=?',(root,)).fetchone()
    if saved and saved[0]==revision:return
    rows=connection.execute('SELECT * FROM files WHERE root=? ORDER BY path',(root,)).fetchall()
    retired=retired_sources(connection,root)
    import reacquire_sources
    archived=reacquire_sources.archived_ids(connection,root)
    frozen={json.loads(item['snapshot'])['group']['scope']:json.loads(item['snapshot']) for item in reacquire_sources.markers(connection,root) if item['state']=='required'}
    frozen_paths={member['path'] for item in frozen.values() for member in item['members']}
    rows=[row for row in rows if row['path'] not in frozen_paths]
    protected={}
    jobs=set()
    if connection.execute("SELECT 1 FROM sqlite_master WHERE name='audio_jobs'").fetchone():
        jobs={json.loads(r[0])['candidate_id'] for r in connection.execute('SELECT manifest FROM audio_jobs')}
    for r in connection.execute('SELECT * FROM book_groups WHERE root=?',(root,)):
        if r['id'] in archived:continue
        if r['approved'] or r['review'] or r['id'] in jobs:protected[r['scope']]=json.loads(r['evidence'])
    groups=build(rows,protected,chaptered_parts(connection,root),volume_parts(connection,root),kept_parts(connection,root))
    for scope,item in frozen.items():groups[scope]=json.loads(item['group']['evidence'])
    for scope,evidence in groups.items():
        if scope in frozen:continue
        old=connection.execute('SELECT * FROM book_groups WHERE root=? AND scope=?',(root,scope)).fetchone()
        if old:
            evidence=_preserve_retired_evidence(old,evidence,retired)
            connection.execute('UPDATE book_groups SET superseded=0 WHERE id=?',(old['id'],))
        fingerprint=hashlib.sha256(json.dumps(evidence,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
        if old is None:
            connection.execute('INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence) VALUES(?,?,?,?,?,?)',
                (str(uuid.uuid4()),root,scope,1,fingerprint,json.dumps(evidence,ensure_ascii=False)))
        elif old['fingerprint']!=fingerprint:
            connection.execute('UPDATE book_groups SET revision=revision+1,fingerprint=?,evidence=?,approved=0,changed=1 WHERE id=?',
                (fingerprint,json.dumps(evidence,ensure_ascii=False),old['id']))
    # A formerly indexed group no longer present retains evidence but cannot stay approved.
    for old in connection.execute('SELECT * FROM book_groups WHERE root=?',(root,)).fetchall():
        if old['id'] in archived or old['scope'] in frozen:continue
        former=json.loads(old['evidence'])['members']
        all_retired=bool(former) and all(m['path'] in retired for m in former)
        if old['scope'] not in groups and old['scope'] not in protected:
            connection.execute('UPDATE book_groups SET superseded=1,approved=0 WHERE id=?',(old['id'],))
        if old['scope'] not in groups and old['approved'] and not all_retired:
            connection.execute('UPDATE book_groups SET approved=0,changed=1,revision=revision+1 WHERE id=?',(old['id'],))
    connection.execute('INSERT OR REPLACE INTO book_group_sync VALUES(?,?)',(root,revision))

def render(row,root,coverage,retired=None):
    evidence=json.loads(row['evidence'])
    review=json.loads(row['review']) if row['review'] else None
    first=evidence['members'][0]
    preview=propose(first['path'],root,'audiobook',evidence['metadata'],review)
    reasons=list(evidence['conflicts'])
    if not preview['path']:reasons.append(preview['reason'])
    approved=bool(row['approved'])
    status='Metadata approved; tracks need review' if approved else 'Candidate changed — review required' if row['changed'] else 'Needs review'
    if reasons:approved=False
    for item in evidence['members']:item['metadata'].pop('probe',None)
    retired=retired or {}
    for item in evidence['members']:
        item['intentionally_retired']=item['path'] in retired
        if item['intentionally_retired']:
            item['retirement']={key:retired[item['path']][key] for key in ('cleanup_id','job_id','source_hash','state')}
    retired_count=sum(m['intentionally_retired'] for m in evidence['members'])
    return evidence | {'id':row['id'],'source_root':row['root'],'revision':row['revision'],'fingerprint':row['fingerprint'],
      'review':review,'metadata_approved':approved,'status':status,'changed':bool(row['changed']),
      'preview':preview,'tag_preview':future_audio_tags(evidence['metadata'],review),
      'approval_reason':'; '.join(reasons),'can_approve':not reasons and not retired_count,
      'retired_source_count':retired_count,'all_sources_retired':retired_count==len(evidence['members']),
      'active_members':[m for m in evidence['members'] if not m['intentionally_retired']],
      'coverage':'Scanned scope complete; recording completeness unverified' if coverage else 'Based on files scanned so far'}

def page(connection,root,limit=100,offset=0,search='',status='all',coverage=False,ids=None):
    """ids: only these candidates are rendered (the caller prefiltered them cheaply); None renders all."""
    sync(connection,root)
    retired=retired_sources(connection,root)
    if ids is not None:
        # Only the prefiltered rows are read (a full read was about 120 MB on the real catalog).
        chosen=json.dumps(sorted(str(identity) for identity in ids))
        values=[render(row,root,coverage,retired) for row in connection.execute('SELECT * FROM book_groups WHERE root=? AND superseded=0 AND id IN (SELECT value FROM json_each(?)) ORDER BY scope',(root,chosen))]
        return {'rows':values[offset:offset+limit],'total':len(values)}
    if status=='all' and not search:
        total=connection.execute('SELECT count(*) FROM book_groups WHERE root=? AND superseded=0',(root,)).fetchone()[0]
        rows=connection.execute('SELECT * FROM book_groups WHERE root=? AND superseded=0 ORDER BY scope LIMIT ? OFFSET ?',(root,limit,offset))
        return {'rows':[render(row,root,coverage,retired) for row in rows],'total':total}
    values=[render(row,root,coverage,retired) for row in connection.execute('SELECT * FROM book_groups WHERE root=? AND superseded=0 ORDER BY scope',(root,))]
    filters={'all':lambda row:True,'review':lambda row:not row['metadata_approved'],
      'approved':lambda row:row['metadata_approved'],'errors':lambda row:any(item['error'] and not item['missing'] for item in row['members']),
      'changed':lambda row:row['changed']}
    if status not in filters:raise ValueError('Unknown candidate status')
    values=[row for row in values if filters[status](row) and search.casefold() in (' '.join([row['title_clue'],row['scope']]+[item['path'] for item in row['members']])).casefold()]
    return {'rows':values[offset:offset+limit],'total':len(values)}

def page_sources(connection,roots,limit=100,offset=0,search='',status='all',coverage=None,ids=None):
    """All-source page from the caller's transaction, preserving source identity.

    Unfiltered pages render only the requested rows. Filtered pages share the
    same predicate for returned rows and total; ids are an optional intersection.
    """
    for root in roots:sync(connection,root)
    coverage=coverage or {}
    marks=','.join('?' for _ in roots)
    clause=f'root IN ({marks}) AND superseded=0'
    args=tuple(roots)
    if ids is not None:
        clause+=' AND id IN (SELECT value FROM json_each(?))'
        args+=(json.dumps(sorted(str(identity) for identity in ids)),)
    order=' ORDER BY scope COLLATE NOCASE,root,id'
    if status=='all' and not search:
        total=connection.execute('SELECT count(*) FROM book_groups WHERE '+clause,args).fetchone()[0]
        records=connection.execute('SELECT * FROM book_groups WHERE '+clause+order+' LIMIT ? OFFSET ?',args+(limit,offset)).fetchall()
    else:
        total=None
        records=connection.execute('SELECT * FROM book_groups WHERE '+clause+order,args).fetchall()
    retirements={root:retired_sources(connection,root) for root in {row['root'] for row in records}}
    values=[render(row,row['root'],coverage.get(row['root'],False),retirements[row['root']]) for row in records]
    if total is not None:return {'rows':values,'total':total}
    filters={'all':lambda row:True,'review':lambda row:not row['metadata_approved'],
      'approved':lambda row:row['metadata_approved'],'errors':lambda row:any(item['error'] and not item['missing'] for item in row['members']),
      'changed':lambda row:row['changed']}
    if status not in filters:raise ValueError('Unknown candidate status')
    values=[row for row in values if filters[status](row) and search.casefold() in
            (' '.join([row['title_clue'],row['scope']]+[item['path'] for item in row['members']])).casefold()]
    return {'rows':values[offset:offset+limit],'total':len(values)}

def save(connection,root,identity,revision,review,approve=False):
    import reacquire_sources
    value=reacquire_sources.marker(connection,identity)
    if value and value['state']=='archived':raise ValueError('Damaged-source entry archived; use the newly discovered replacement')
    sync(connection,root)
    row=connection.execute('SELECT * FROM book_groups WHERE root=? AND id=?',(root,identity)).fetchone()
    if row is None or row['revision']!=revision:raise ValueError('Candidate changed; reload evidence before reviewing')
    changed=review!=(json.loads(row['review']) if row['review'] else None)
    connection.execute('UPDATE book_groups SET review=?,approved=0,changed=0,revision=revision+? WHERE id=?',
      (json.dumps(review,ensure_ascii=False),int(changed),identity))
    fresh=connection.execute('SELECT * FROM book_groups WHERE id=?',(identity,)).fetchone()
    if approve:
        proposed=render(fresh,root,False,retired_sources(connection,root))
        if not proposed['can_approve']:raise ValueError(proposed['approval_reason'])
        connection.execute('UPDATE book_groups SET approved=1 WHERE id=?',(identity,))
    return render(connection.execute('SELECT * FROM book_groups WHERE id=?',(identity,)).fetchone(),root,False,retired_sources(connection,root))
