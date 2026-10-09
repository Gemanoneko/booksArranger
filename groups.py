"""Persistent provisional audiobook groups assembled from catalog evidence only."""
import hashlib
import json
from pathlib import Path
import re
import uuid
import math
from metadata import propose, future_audio_tags

def setup(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS book_groups(
      id TEXT PRIMARY KEY, root TEXT, scope TEXT, revision INTEGER, fingerprint TEXT,
      evidence TEXT, review TEXT DEFAULT '', approved INTEGER DEFAULT 0,
      changed INTEGER DEFAULT 0, UNIQUE(root,scope))''')

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

def build(rows):
    audio=[row for row in rows if row['kind']=='audiobook' and not json.loads(row['metadata']).get('arranger_output')]
    companions=[row for row in rows if row['kind']=='companion']
    batches={}
    for row in audio:
        item=member(row)
        parent=Path(row['path']).parent
        tags={key.casefold():value for key,value in item['metadata'].get('tags',{}).items()}
        album=str(tags.get('album') or '').strip()
        # Disc siblings may share a candidate only when an explicit album clue agrees.
        disc_folder=re.fullmatch(r'(?:cd|disc|disk|диск)[ _.-]*(\d+)',parent.name,re.I)
        if Path(row['path']).suffix.lower()=='.m4b':
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
        related=[{'path':row['path'],'size':row['size'],'modified':str(row['modified']),'error':row['error'],'missing':bool(row['missing'])} for row in companions if str(Path(row['path']).parent) in folders]
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

def sync(connection,root):
    setup(connection)
    rows=connection.execute('SELECT * FROM files WHERE root=? ORDER BY path',(root,)).fetchall()
    groups=build(rows)
    for scope,evidence in groups.items():
        fingerprint=hashlib.sha256(json.dumps(evidence,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
        old=connection.execute('SELECT * FROM book_groups WHERE root=? AND scope=?',(root,scope)).fetchone()
        if old is None:
            connection.execute('INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence) VALUES(?,?,?,?,?,?)',
                (str(uuid.uuid4()),root,scope,1,fingerprint,json.dumps(evidence,ensure_ascii=False)))
        elif old['fingerprint']!=fingerprint:
            connection.execute('UPDATE book_groups SET revision=revision+1,fingerprint=?,evidence=?,approved=0,changed=1 WHERE id=?',
                (fingerprint,json.dumps(evidence,ensure_ascii=False),old['id']))
    # A formerly indexed group no longer present retains evidence but cannot stay approved.
    for old in connection.execute('SELECT * FROM book_groups WHERE root=?',(root,)).fetchall():
        if old['scope'] not in groups and old['approved']:
            connection.execute('UPDATE book_groups SET approved=0,changed=1,revision=revision+1 WHERE id=?',(old['id'],))

def render(row,root,coverage):
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
    return evidence | {'id':row['id'],'revision':row['revision'],'fingerprint':row['fingerprint'],
      'review':review,'metadata_approved':approved,'status':status,'changed':bool(row['changed']),
      'preview':preview,'tag_preview':future_audio_tags(evidence['metadata'],review),
      'approval_reason':'; '.join(reasons),'can_approve':not reasons,
      'coverage':'Scanned scope complete; recording completeness unverified' if coverage else 'Based on files scanned so far'}

def page(connection,root,limit=100,offset=0,search='',status='all',coverage=False):
    sync(connection,root)
    values=[render(row,root,coverage) for row in connection.execute('SELECT * FROM book_groups WHERE root=? ORDER BY scope',(root,))]
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
        proposed=render(fresh,root,False)
        if not proposed['can_approve']:raise ValueError(proposed['approval_reason'])
        connection.execute('UPDATE book_groups SET approved=1 WHERE id=?',(identity,))
    return render(connection.execute('SELECT * FROM book_groups WHERE id=?',(identity,)).fetchone(),root,False)
