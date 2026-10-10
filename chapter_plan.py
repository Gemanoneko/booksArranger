"""Source-track navigation, independent of literary chapter identification."""
import re
from pathlib import Path
from collections import Counter

def prepare(members):
    numbers=[]
    for member in members:
        value=str(member.get('source_track') or '')
        match=re.fullmatch(r'\s*(\d+)(?:/\d+)?\s*',value)
        numbers.append(int(match[1]) if match and not member.get('order_conflict') else None)
    counts=Counter(n for n in numbers if n is not None)
    for member,number in zip(members,numbers):
        metadata=member.get('metadata',{})
        tags={str(k).casefold():str(v) for k,v in metadata.get('tags',{}).items()}
        title=str(metadata.get('track_title') or tags.get('title') or '').strip()
        album=tags.get('album','').strip()
        # Whole-book labels repeated on every track are not chapter names.
        if title.casefold()==album.casefold():title=''
        member.update(chapter_name=title,chapter_name_source='source' if title else 'generated',
                      chapter_number=number if number is not None and counts[number]==1 else None)
    return members

def names(members):
    prepare(members)
    return [m['chapter_name'] or 'Track '+str(m['chapter_number'] if m['chapter_number'] is not None else i+1).zfill(2)
            for i,m in enumerate(members)]

def available(members):
    return bool(members and all(isinstance(m.get('duration'),(int,float)) and m['duration']>0 and not m.get('error') and not m.get('missing') for m in members))

def default(members):
    return len(members)>1 and all(Path(m['path']).suffix.lower()=='.mp3' for m in members) and available(members)
