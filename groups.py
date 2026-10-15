"""Persistent provisional audiobook groups assembled from catalog evidence only."""
import hashlib
import json
from pathlib import Path
import re
import uuid
import math
from metadata import propose, future_audio_tags
from collections import Counter
from source_identity import partition, clues, VERSION as SOURCE_VERSION
import split_books
# Changing the grouping algorithm re-syncs every root once (split books, v0.15.0).
GROUP_VERSION = SOURCE_VERSION + '+' + split_books.VERSION

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

def build(rows,protected=None,chaptered=frozenset()):
    protected=protected or {};assigned={m['path']:scope for scope,e in protected.items() for m in e['members']};buckets={}
    audio=[row for row in rows if row['kind']=='audiobook' and not json.loads(row['metadata']).get('arranger_output')]
    members={row['path']:member(row) for row in audio}
    scopes={path:assigned.get(path) or partition(item) for path,item in members.items()}
    # Only whole .m4b files (always single-file candidates by partition) are re-filed as their own
    # books; an .m4a may sit in a multi-file group and would be re-encoded (Senua R2-M1).
    chaptered=frozenset(path for path in chaptered if Path(path).suffix.lower()=='.m4b')
    for path in chaptered:
        # Its own book (Sergei 2026-10-13): a new scope, so a part that sat in a joined split book
        # becomes a new candidate that a running automatic pass picks up.
        if path in scopes and path not in assigned:scopes[path]=str(Path(path))+'\x1fPart with its own chapters'
    split={}
    taken=set(scopes.values())
    for found in _split_plan(members,scopes,assigned,chaptered):
        # Senua M7: a plan whose scope is already used (a reviewed split book retagged beside new
        # files with its old title) is not grouped; its files keep their own held candidates.
        if found['scope'] in taken:continue
        for item in found['members']:scopes[item['path']]=found['scope']
        split[found['scope']]=found
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
    return output

def sync(connection,root):
    setup(connection)
    revision=connection.execute('SELECT revision FROM book_catalog_revision WHERE id=1').fetchone()[0]
    saved=connection.execute('SELECT revision FROM book_group_sync WHERE root=?',(root,)).fetchone()
    if saved and saved[0]==revision:return
    rows=connection.execute('SELECT * FROM files WHERE root=? ORDER BY path',(root,)).fetchall()
    retired=retired_sources(connection,root)
    protected={}
    jobs=set()
    if connection.execute("SELECT 1 FROM sqlite_master WHERE name='audio_jobs'").fetchone():
        jobs={json.loads(r[0])['candidate_id'] for r in connection.execute('SELECT manifest FROM audio_jobs')}
    for r in connection.execute('SELECT * FROM book_groups WHERE root=?',(root,)):
        if r['approved'] or r['review'] or r['id'] in jobs:protected[r['scope']]=json.loads(r['evidence'])
    groups=build(rows,protected,chaptered_parts(connection,root))
    for scope,evidence in groups.items():
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
    return evidence | {'id':row['id'],'revision':row['revision'],'fingerprint':row['fingerprint'],
      'review':review,'metadata_approved':approved,'status':status,'changed':bool(row['changed']),
      'preview':preview,'tag_preview':future_audio_tags(evidence['metadata'],review),
      'approval_reason':'; '.join(reasons),'can_approve':not reasons and not retired_count,
      'retired_source_count':retired_count,'all_sources_retired':retired_count==len(evidence['members']),
      'active_members':[m for m in evidence['members'] if not m['intentionally_retired']],
      'coverage':'Scanned scope complete; recording completeness unverified' if coverage else 'Based on files scanned so far'}

def page(connection,root,limit=100,offset=0,search='',status='all',coverage=False):
    sync(connection,root)
    retired=retired_sources(connection,root)
    if status=='all' and not search:
        total=connection.execute('SELECT count(*) FROM book_groups WHERE root=? AND superseded=0',(root,)).fetchone()[0]
        rows=connection.execute('SELECT * FROM book_groups WHERE root=? AND superseded=0 ORDER BY scope LIMIT ? OFFSET ?',(root,limit,offset))
        return {'rows':[render(row,root,coverage,retired) for row in rows],'total':total}
    values=[render(row,root,coverage,retired) for row in connection.execute('SELECT * FROM book_groups WHERE root=? AND superseded=0 ORDER BY scope',(root,))]
    filters={'all':lambda row:True,'review':lambda row:not row['metadata_approved'],
      'approved':lambda row:row['metadata_approved'],'errors':lambda row:any(item['error'] for item in row['members']),
      'changed':lambda row:row['changed']}
    if status not in filters:raise ValueError('Unknown candidate status')
    values=[row for row in values if filters[status](row) and search.casefold() in (' '.join([row['title_clue'],row['scope']]+[item['path'] for item in row['members']])).casefold()]
    return {'rows':values[offset:offset+limit],'total':len(values)}

def save(connection,root,identity,revision,review,approve=False):
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
