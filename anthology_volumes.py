"""Sergei's confirmed anthology books: Калейдоскоп, annual Самая страшная книга and Ужасы и трэшатинка.
No general mixed-author grouping or inferred order; every membership/identity is re-derived from current members.
"""
import re
from pathlib import Path
VERSION='named-anthology-volume-v3'
FAMILY='Калейдоскоп'
STORY_FOLDER='Ужасы и трэшатинка. Сборник рассказов'
STORY_FAMILY='Ужасы и трэшатинка'
_PATTERN=re.compile(r'^Калейдоскоп\s+0*([1-9]\d{0,2})$',re.I)
_ANNUAL=re.compile(r'^(?:Сборник\s*-\s*)?Самая\s+страшная\s+книга\s+((?:19|20)\d{2})(?:\s*\(Сборник\))?(?:\s*\[[^\[\]]+\])?$',re.I)

def tags(member):return {str(k).casefold():str(v) for k,v in member.get('metadata',{}).get('tags',{}).items()}
def folder(member):
    parent=Path(member['path']).parent;match=_PATTERN.fullmatch(' '.join(parent.name.split()))
    if match:return {'family':FAMILY,'number':str(int(match[1])),'title':FAMILY+' '+str(int(match[1])),'folder':str(parent)}
    volume=re.fullmatch(r'Сборник(?:\s*([234]))?',' '.join(parent.name.split()),re.I)
    if volume and ' '.join(parent.parent.name.casefold().split())==STORY_FOLDER.casefold():
        number=volume[1] or '1'
        return {'family':STORY_FAMILY,'number':number,'title':STORY_FAMILY+' '+number,'folder':str(parent)}
    annual=_ANNUAL.fullmatch(' '.join(parent.name.split()))
    if annual and ' '.join(parent.parent.name.casefold().split())=='самая страшная книга':
        # The year identifies this confirmed anthology book, not an invented position in a narrative series.
        return {'family':'','number':'','title':'Самая страшная книга '+annual[1],'folder':str(parent)}
    return None

def marker(members):
    if not members or len(members)>500:return None
    values=[folder(m) for m in members]
    if not values[0] or any(v!=values[0] for v in values):return None
    value=values[0]
    for member in members:
        album=' '.join(tags(member).get('album','').split());match=_PATTERN.fullmatch(album)
        if value['family']==FAMILY:
            if not match or str(int(match[1]))!=value['number']:return None
        elif value['family']==STORY_FAMILY:
            if album and album.casefold() not in {value['title'].casefold(),Path(value['folder']).name.casefold()}:return None
        elif album.casefold()!=value['title'].casefold():return None
    return dict(value,version=VERSION,paths=sorted(m['path'] for m in members))

def identity(row):
    if not isinstance(row.get('anthology_volume'),dict):return None
    actual=marker(row.get('members') or [])
    return actual if actual and row.get('anthology_volume')==actual else None

def chapter_credit(member,title):
    if not member.get('anthology_story') or not folder(member):return title
    seen=tags(member);credit=' '.join((seen.get('author') or seen.get('artist') or '').split())
    if folder(member)['family']==STORY_FAMILY:
        from local_identity import NOT_PEOPLE,NARRATOR_MARKER,JUNK_TITLES,garbled,norm
        if garbled(title) or norm(re.sub(r'\s+\d+$','',title)) in JUNK_TITLES:
            title=Path(member.get('filename') or member['path']).stem
        # home2 is the existing collection/uploader credit, never a confirmed story writer. Raw tags remain intact.
        if credit.casefold()=='home2' or norm(credit) in NOT_PEOPLE or NARRATOR_MARKER.search(credit):return title
    if not credit:return title
    norm=lambda s:' '.join(re.findall(r'[^\W_]+',s.casefold()))
    # Existing credited source titles are retained byte-for-byte; otherwise reuse the established Author. Story label.
    credited=re.sub(r'^\s*\d+\s*[.)\-:]?\s*','',title)
    if norm(credited)==norm(credit) or norm(credited).startswith(norm(credit)+' '):return title
    return credit+'. '+title if title else credit
