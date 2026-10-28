"""Sergei's named Калейдоскоп family (ruling64): one numbered anthology volume, containing story credits.
No general mixed-author grouping or inferred order; every membership/identity is re-derived from current members.
"""
import re
from pathlib import Path
VERSION='named-anthology-volume-v1'
FAMILY='Калейдоскоп'
_PATTERN=re.compile(r'^Калейдоскоп\s+0*([1-9]\d{0,2})$',re.I)

def tags(member):return {str(k).casefold():str(v) for k,v in member.get('metadata',{}).get('tags',{}).items()}
def folder(member):
    parent=Path(member['path']).parent;match=_PATTERN.fullmatch(' '.join(parent.name.split()))
    return {'family':FAMILY,'number':str(int(match[1])),'title':FAMILY+' '+str(int(match[1])),'folder':str(parent)} if match else None

def marker(members):
    if not members or len(members)>500:return None
    values=[folder(m) for m in members]
    if not values[0] or any(v!=values[0] for v in values):return None
    value=values[0]
    for member in members:
        album=' '.join(tags(member).get('album','').split());match=_PATTERN.fullmatch(album)
        if not match or str(int(match[1]))!=value['number']:return None
    return dict(value,version=VERSION,paths=sorted(m['path'] for m in members))

def identity(row):
    if not isinstance(row.get('anthology_volume'),dict):return None
    actual=marker(row.get('members') or [])
    return actual if actual and row.get('anthology_volume')==actual else None

def chapter_credit(member,title):
    if not member.get('anthology_story') or not folder(member):return title
    seen=tags(member);credit=' '.join((seen.get('author') or seen.get('artist') or '').split())
    if not credit:return title
    norm=lambda s:' '.join(re.findall(r'[^\W_]+',s.casefold()))
    # Existing credited source titles are retained byte-for-byte; otherwise reuse the established Author. Story label.
    credited=re.sub(r'^\s*\d+\s*[.)\-:]?\s*','',title)
    if norm(credited)==norm(credit) or norm(credited).startswith(norm(credit)+' '):return title
    return credit+'. '+title if title else credit
