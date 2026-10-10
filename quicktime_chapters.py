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

def transform(data,delta=None,chapter=False,receipt=None,depth=0,sort_title=None,normalize_chapters=True):
    if depth>16:raise ChapterFormatError('Movie metadata nesting exceeds its bound')
    output=[]
    for kind,value in boxes(data):
        payload=value[8:]
        if kind==b'trak':value=box(kind,transform(payload,delta,handler(value)==b'text',receipt,depth+1,sort_title,normalize_chapters))
        elif kind in CONTAINERS or (kind==b'udta' and sort_title is not None):value=box(kind,transform(payload,delta,chapter,receipt,depth+1,sort_title,normalize_chapters))
        elif kind==b'meta' and sort_title is not None:
            if payload[:4]!=b'\0'*4:raise ChapterFormatError('Unsupported metadata full-box flags')
            value=box(kind,payload[:4]+transform(payload[4:],delta,chapter,receipt,depth+1,sort_title,normalize_chapters))
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
            media=hashlib.sha256()
            with destination.open('xb') as outgoing:
                for kind,at,length in top:
                    incoming.seek(at)
                    if kind==b'moov':outgoing.write(changed);continue
                    remaining=length
                    while remaining:
                        if stop.is_set():raise InterruptedError('Chapter normalization stopped; originals remain unchanged')
                        block=incoming.read(min(1024*1024,remaining))
                        if not block:raise ChapterFormatError('Media copy ended early')
                        outgoing.write(block)
                        if kind==b'mdat':media.update(block)
                        remaining-=len(block)
                outgoing.flush();os.fsync(outgoing.fileno())
            receipt.update(metadata_growth=delta,media_atom_sha256=media.hexdigest(),output_size=destination.stat().st_size)
            return receipt
