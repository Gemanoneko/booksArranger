"""Normalize FFmpeg's chapter-only text description to the documented QTFF layout.

This bounded transformation accepts only our unfragmented faststart MP4 profile.
All media payload bytes remain untouched; chunk positions are adjusted precisely.
Apple: https://developer.apple.com/documentation/quicktime-file-format/text_sample_description
"""
import hashlib,os,struct
from pathlib import Path
from native_io import DirectoryBoundary,ProtectedFiles,ordinary

MAX_MOOV=64*1024*1024
CONTAINERS={b'moov',b'trak',b'mdia',b'minf',b'stbl',b'tref',b'edts',b'dinf'}

class ChapterFormatError(ValueError):pass

def boxes(data):
    result=[];at=0
    while at<len(data):
        if at+8>len(data):raise ChapterFormatError('Truncated atom header')
        size,kind=struct.unpack_from('>I4s',data,at)
        if size<8 or at+size>len(data):raise ChapterFormatError('Unsupported or malformed atom size')
        result.append((kind,data[at:at+size]));at+=size
    return result

def box(kind,payload):return struct.pack('>I4s',8+len(payload),kind)+payload

def legacy_entry(header):
    if len(header)!=16 or header[4:8]!=b'text' or header[8:16]!=b'\0'*7+b'\1':raise ChapterFormatError('Unexpected chapter sample header')
    # QTFF legacy text fields, in their documented order and byte widths.
    body=(struct.pack('>Ii',0,0)+b'\0'*6+b'\0'*8+b'\0'*8+struct.pack('>HH',1,0)+
          b'\0'+b'\0'*2+struct.pack('>HHH',65535,65535,65535)+b'\x05Arial')
    return struct.pack('>I',16+len(body))+header[4:]+body

def description(entry):
    if len(entry)<60:raise ChapterFormatError('Legacy text sample description ends before its Pascal font-name byte')
    if entry[4:8]!=b'text' or entry[59]+60!=len(entry):raise ChapterFormatError('Invalid legacy text font-name bounds')
    if entry[38:46]!=b'\0'*8 or entry[50:53]!=b'\0'*3:raise ChapterFormatError('Legacy text reserved fields are invalid')
    return {'entry_size':len(entry),'format':'text','font_name':entry[60:].decode('ascii'),'font_name_offset':59,'layout':'Apple QTFF legacy text'}

def handler(trak):
    for kind,data in boxes(trak[8:]):
        if kind==b'mdia':
            for child,value in boxes(data[8:]):
                if child==b'hdlr':return value[16:20]
    return None

def text_tag(kind,value):
    """One Apple metadata item holding UTF-8 text (data type 1), as FFmpeg writes it."""
    encoded=value.encode('utf-8')
    if not value or len(encoded)>8000:raise ChapterFormatError('Metadata text must be bounded nonempty UTF-8')
    return box(kind,box(b'data',b'\0\0\0\1'+b'\0'*4+encoded))

def track_tag(number):
    """The track-number item (implicit data type): position, no total, as FFmpeg writes it."""
    if type(number) is not int or not 0<number<65536:raise ChapterFormatError('Track number out of range')
    return box(b'trkn',box(b'data',b'\0'*8+struct.pack('>HHHH',0,number,0,0)))

def transform(data,delta=None,chapter=False,receipt=None,depth=0,sort_title=None,normalize_chapters=True,tags=None):
    if depth>16:raise ChapterFormatError('Movie metadata nesting exceeds its bound')
    output=[];metadata=sort_title is not None or bool(tags)
    for kind,value in boxes(data):
        payload=value[8:]
        if kind==b'trak':value=box(kind,transform(payload,delta,handler(value)==b'text',receipt,depth+1,sort_title,normalize_chapters,tags))
        elif kind in CONTAINERS or (kind==b'udta' and metadata):value=box(kind,transform(payload,delta,chapter,receipt,depth+1,sort_title,normalize_chapters,tags))
        elif kind==b'meta' and metadata:
            if payload[:4]!=b'\0'*4:raise ChapterFormatError('Unsupported metadata full-box flags')
            value=box(kind,payload[:4]+transform(payload[4:],delta,chapter,receipt,depth+1,sort_title,normalize_chapters,tags))
        elif kind==b'ilst' and tags:
            # v0.16.12 series backfill: the named items are replaced or added; every other item is kept as is.
            kept=[v for k,v in boxes(payload) if k not in tags]
            value=box(kind,b''.join(kept)+b''.join(tags[k] for k in sorted(tags)))
            receipt['tag_lists']=receipt.get('tag_lists',0)+1
        elif kind==b'ilst' and sort_title is not None:
            entries=boxes(payload)
            value=box(kind,b''.join(v for k,v in entries if k!=b'sonm')+box(b'sonm',box(b'data',b'\0\0\0\1'+b'\0'*4+sort_title.encode('utf-8'))))
            receipt['sort_atoms']=receipt.get('sort_atoms',0)+1
        elif kind==b'stsd' and chapter and normalize_chapters:
            if len(payload)<8 or payload[:8]!=b'\0\0\0\0\0\0\0\1':raise ChapterFormatError('Chapter track must have one sample description')
            entries=boxes(payload[8:])
            if len(entries)!=1 or entries[0][0]!=b'text':raise ChapterFormatError('Chapter sample type is unsupported')
            original=entries[0][1];replacement=legacy_entry(original[:16])
            receipt['original_size']=len(original);receipt['description']=description(replacement);receipt['tracks']+=1
            value=box(kind,payload[:8]+replacement)
        elif kind in (b'stco',b'co64') and delta is not None:
            if len(payload)<8 or payload[:4]!=b'\0'*4:raise ChapterFormatError('Unsupported chunk offset table')
            count=int.from_bytes(payload[4:8],'big');width=4 if kind==b'stco' else 8
            if len(payload)!=8+count*width:raise ChapterFormatError('Chunk offset count differs')
            changed=bytearray(payload)
            for i in range(count):
                at=8+i*width;old=int.from_bytes(payload[at:at+width],'big')
                if not receipt['old_mdat_start']<=old<receipt['old_file_size']:raise ChapterFormatError('Chunk points outside the supported media payload')
                new=old+delta
                if not 0<=new<1<<(8*width):raise ChapterFormatError('Relocated chunk offset overflows; encoding review required')
                changed[at:at+width]=new.to_bytes(width,'big')
            value=box(kind,changed);receipt['chunk_offsets']+=count
        output.append(value)
    return b''.join(output)

def normalize(source,destination,stop,sort_title=None,normalize_chapters=True):
    source=ordinary(source);destination=ordinary(destination)
    if source.parent!=destination.parent or source==destination:raise ChapterFormatError('Normalization requires a distinct owned same-directory output')
    with DirectoryBoundary(source.parent,source.parent),ProtectedFiles([source]):
        size=source.stat().st_size
        with source.open('rb') as incoming:
            top=[];at=0
            while at<size:
                incoming.seek(at);header=incoming.read(8)
                if len(header)!=8:raise ChapterFormatError('Truncated top-level atom')
                length,kind=struct.unpack('>I4s',header)
                if length<8 or at+length>size:raise ChapterFormatError('Unsupported top-level atom size')
                top.append((kind,at,length));at+=length
            if [t[0] for t in top]!=[b'ftyp',b'moov',b'free',b'mdat']:raise ChapterFormatError('Only the owned unfragmented faststart MP4 profile is supported')
            moov=top[1];mdat=top[3]
            if moov[2]>MAX_MOOV:raise ChapterFormatError('Movie metadata exceeds the normalization bound')
            incoming.seek(moov[1]);original=incoming.read(moov[2])
            receipt={'tracks':0,'chunk_offsets':0,'old_mdat_start':mdat[1]+8,'old_file_size':size}
            if sort_title is not None and (not isinstance(sort_title,str) or not sort_title or len(sort_title.encode('utf-8'))>8000):raise ChapterFormatError('Sort title must be bounded nonempty UTF-8 text')
            measured=transform(original,receipt=receipt,sort_title=sort_title,normalize_chapters=normalize_chapters)
            if normalize_chapters and receipt['tracks']!=1:raise ChapterFormatError('Exactly one chapter text track is required')
            if sort_title is not None and receipt.get('sort_atoms')!=1:raise ChapterFormatError('Exactly one Apple metadata list is required')
            delta=len(measured)-len(original);receipt['tracks']=0;receipt['sort_atoms']=0
            changed=transform(original,delta,receipt=receipt,sort_title=sort_title,normalize_chapters=normalize_chapters)
            if len(changed)!=len(measured):raise ChapterFormatError('Metadata relocation size differs')
            media=hashlib.sha256();input_hash=hashlib.sha256()
            with destination.open('xb') as outgoing:
                for kind,at,length in top:
                    incoming.seek(at)
                    if kind==b'moov':input_hash.update(original);outgoing.write(changed);continue
                    remaining=length
                    while remaining:
                        if stop.is_set():raise InterruptedError('Chapter normalization stopped; originals remain unchanged')
                        block=incoming.read(min(1024*1024,remaining))
                        if not block:raise ChapterFormatError('Media copy ended early')
                        input_hash.update(block);outgoing.write(block)
                        if kind==b'mdat':media.update(block)
                        remaining-=len(block)
                outgoing.flush();os.fsync(outgoing.fileno())
            receipt.update(input_sha256=input_hash.hexdigest(),metadata_growth=delta,media_atom_sha256=media.hexdigest(),output_size=destination.stat().st_size)
            return receipt

LAYOUT_ATOMS={b'ftyp',b'free',b'wide',b'skip',b'mdat',b'moov'}

def _layout(path):
    """Top-level atoms [(kind, offset, length)], the movie atom's index, and whether media follows it (its chunk
    offsets then move with the metadata). One movie atom, media on one side of it only, nothing unknown."""
    size=path.stat().st_size;top=[];at=0
    with path.open('rb') as stream:
        while at<size:
            stream.seek(at);header=stream.read(16)
            if len(header)<8:raise ChapterFormatError('Truncated top-level atom')
            length,kind=struct.unpack('>I4s',header[:8])
            if length==1:
                if len(header)<16 or kind==b'moov':raise ChapterFormatError('Unsupported extended atom size')
                length=int.from_bytes(header[8:16],'big')
            if length<8 or at+length>size:raise ChapterFormatError('Unsupported top-level atom size')
            top.append((kind,at,length));at+=length
    kinds=[t[0] for t in top]
    if not kinds or kinds[0]!=b'ftyp' or kinds.count(b'moov')!=1 or b'mdat' not in kinds or any(k not in LAYOUT_ATOMS for k in kinds):
        raise ChapterFormatError('Only an unfragmented audiobook with one movie atom is supported')
    index=kinds.index(b'moov')
    before=b'mdat' in kinds[:index];after=b'mdat' in kinds[index+1:]
    if before and after:raise ChapterFormatError('Media on both sides of the movie atom is not supported')
    if top[index][2]>MAX_MOOV:raise ChapterFormatError('Movie metadata exceeds the rewrite bound')
    return top,index,after

def retag(source,destination,stop,tags):
    """v0.16.12: the same audiobook with the named Apple metadata items replaced, written as a new same-directory
    file. Every atom but the movie atom is copied byte for byte; when media follows the movie atom its chunk
    offsets move by exactly the metadata growth. The source is only read."""
    source=ordinary(source);destination=ordinary(destination)
    if source.parent!=destination.parent or source==destination:raise ChapterFormatError('Retagging requires a distinct same-directory output')
    if not tags:raise ChapterFormatError('No metadata to write')
    with DirectoryBoundary(source.parent,source.parent),ProtectedFiles([source]):
        size=source.stat().st_size
        top,index,moves=_layout(source)
        _,movie_at,movie_length=top[index]
        with source.open('rb') as incoming:
            incoming.seek(movie_at);original=incoming.read(movie_length)
            media_start=min(at for kind,at,_ in top if kind==b'mdat')+8
            receipt={'tracks':0,'chunk_offsets':0,'old_mdat_start':media_start,'old_file_size':size}
            measured=transform(original,receipt=receipt,normalize_chapters=False,tags=tags)
            if receipt.get('tag_lists')!=1:raise ChapterFormatError('Exactly one Apple metadata list is required')
            delta=len(measured)-len(original);receipt['tag_lists']=0
            changed=transform(original,delta if moves else None,receipt=receipt,normalize_chapters=False,tags=tags)
            if len(changed)!=len(measured):raise ChapterFormatError('Metadata relocation size differs')
            media=hashlib.sha256();input_hash=hashlib.sha256()
            with destination.open('xb') as outgoing:
                for kind,at,length in top:
                    incoming.seek(at)
                    if kind==b'moov':input_hash.update(original);outgoing.write(changed);continue
                    remaining=length
                    while remaining:
                        if stop.is_set():raise InterruptedError('Retagging stopped; the audiobook is unchanged')
                        block=incoming.read(min(1024*1024,remaining))
                        if not block:raise ChapterFormatError('Media copy ended early')
                        input_hash.update(block);outgoing.write(block)
                        if kind==b'mdat':media.update(block)
                        remaining-=len(block)
                outgoing.flush();os.fsync(outgoing.fileno())
        receipt.update(input_sha256=input_hash.hexdigest(),input_size=size,metadata_growth=delta,media_moved=moves,media_atom_sha256=media.hexdigest(),output_size=destination.stat().st_size)
        return receipt

def _without_metadata(data,delta,depth=0):
    """The movie atom without its user-data metadata, chunk offsets moved by delta: what must stay the same."""
    if depth>16:raise ChapterFormatError('Movie metadata nesting exceeds its bound')
    output=[]
    for kind,value in boxes(data):
        payload=value[8:]
        if kind==b'udta':continue
        if kind in CONTAINERS:value=box(kind,_without_metadata(payload,delta,depth+1))
        elif kind in (b'stco',b'co64') and delta:
            count=int.from_bytes(payload[4:8],'big');width=4 if kind==b'stco' else 8
            if payload[:4]!=b'\0'*4 or len(payload)!=8+count*width:raise ChapterFormatError('Unsupported chunk offset table')
            changed=bytearray(payload)
            for i in range(count):
                at=8+i*width;changed[at:at+width]=(int.from_bytes(payload[at:at+width],'big')+delta).to_bytes(width,'big')
            value=box(kind,changed)
        output.append(value)
    return b''.join(output)

def media_unchanged(original,changed,stop):
    """Independent byte proof that a metadata rewrite left every track's samples as they were: the media atom's
    bytes are identical, and the movie atom is identical apart from its user-data metadata and chunk offsets
    moved by exactly the metadata growth. Returns that growth; raises ChapterFormatError otherwise."""
    original=ordinary(original);changed=ordinary(changed)
    old,index,moves=_layout(original);new,new_index,new_moves=_layout(changed)
    if [t[0] for t in old]!=[t[0] for t in new] or index!=new_index or moves!=new_moves:raise ChapterFormatError('Atom layout changed')
    if any(o[2]!=n[2] for i,(o,n) in enumerate(zip(old,new)) if i!=index):raise ChapterFormatError('An atom other than the movie atom changed size')
    delta=new[index][2]-old[index][2]
    with original.open('rb') as a,changed.open('rb') as b:
        a.seek(old[index][1]);b.seek(new[index][1])
        before=a.read(old[index][2]);after=b.read(new[index][2])
        if _without_metadata(before[8:],delta if moves else 0)!=_without_metadata(after[8:],0):raise ChapterFormatError('Track structure or sample tables changed')
        for (_,at_a,length),(_,at_b,_) in (pair for i,pair in enumerate(zip(old,new)) if i!=index):
            a.seek(at_a);b.seek(at_b);remaining=length
            while remaining:
                if stop.is_set():raise InterruptedError('Media proof stopped; nothing changed')
                x=a.read(min(1024*1024,remaining));y=b.read(min(1024*1024,remaining))
                if not x or x!=y:raise ChapterFormatError('Media bytes changed')
                remaining-=len(x)
    return delta
