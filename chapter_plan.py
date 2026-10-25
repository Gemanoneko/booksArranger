"""Source-track navigation, independent of literary chapter identification."""
import re
from pathlib import Path
from collections import Counter

_SEPARATORS = ' ._-–—:'


def _after(name, prefix):
    """(text, number) of a file name after the book's shared prefix (case-insensitive), its separators and a leading
    track number ("Пастушья корона 01. Глава 1. Там где ветер" after "Пастушья корона": "Глава 1. Там где ветер", 1;
    "Пастушья корона 02": "", 2). None when the name does not start with the prefix."""
    if not prefix or not name.casefold().startswith(prefix.casefold()):
        return None
    rest = name[len(prefix):].lstrip(_SEPARATORS)
    match = re.match(r'(\d+)(?=[\s._\-–—:)]|$)[\s._\-–—:)]*', rest)
    if match:
        return rest[match.end():].strip(), int(match[1])
    return rest.strip(), None


def prepare(members):
    numbers=[]
    for member in members:
        value=str(member.get('source_track') or '')
        match=re.fullmatch(r'\s*(\d+)(?:/\d+)?\s*',value)
        numbers.append(int(match[1]) if match and not member.get('order_conflict') else None)
    counts=Counter(n for n in numbers if n is not None)
    titles,albums=[],[]
    for member in members:
        metadata=member.get('metadata',{})
        tags={str(k).casefold():str(v) for k,v in metadata.get('tags',{}).items()}
        titles.append(str(metadata.get('track_title') or tags.get('title') or '').strip())
        albums.append(tags.get('album','').strip())
    stems=[Path(str(member.get('path',''))).stem for member in members]
    # Futaba's 0.22.0 QA, m-12: one title tag on every file that every file name also starts with ("Пастушья корона" on 77
    # files named "Пастушья корона 01. Глава 1. Там где ветер") is the book's shared prefix, not a chapter name: each
    # chapter is named from its file name after that prefix. A description repeated on files whose names do not carry
    # it ("Начало" on 1.mp3 and 2.mp3) is still each chapter's name.
    shared=titles[0] if len(members)>1 and titles[0] and all(t.casefold()==titles[0].casefold() for t in titles) and all(s.casefold().startswith(titles[0].casefold()) for s in stems) else ''
    named=[]
    for title,album,stem in zip(titles,albums,stems):
        # Whole-book labels repeated on every track are not chapter names; the file name after the label may be.
        if shared or title.casefold()==album.casefold():
            named.append(_after(stem,shared or album) or ('',None))
        else:
            named.append((title,None))
    own=Counter(n for text,n in named if n is not None and not text)
    for member,number,(title,from_name) in zip(members,numbers,named):
        if number is None and from_name is not None and not title and own[from_name]==1:
            number,unique=from_name,True  # "Пастушья корона 02": the file's own number names its chapter
        else:
            unique=number is not None and counts[number]==1
        member.update(chapter_name=title,chapter_name_source='source' if title else 'generated',
                      chapter_number=number if unique else None)
    return members

def names(members):
    prepare(members)
    return [m['chapter_name'] or 'Track '+str(m['chapter_number'] if m['chapter_number'] is not None else i+1).zfill(2)
            for i,m in enumerate(members)]

def available(members):
    return bool(members and all(isinstance(m.get('duration'),(int,float)) and m['duration']>0 and not m.get('error') and not m.get('missing') for m in members))

def default(members):
    return len(members)>1 and all(Path(m['path']).suffix.lower()=='.mp3' for m in members) and available(members)
