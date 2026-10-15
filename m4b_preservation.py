"""Bounded metadata-only M4B construction; callers own immutable input/private sink.

No decoder, remuxer, filesystem opening or publication occurs here. Every original
track and mdat byte remains at its original offset. Only approved Apple metadata
items change; the prior moov becomes same-extent free and a new moov is appended.
"""
import hashlib
import struct
from dataclasses import dataclass

MAX_MOOV=32*1024*1024
MAX_BOXES=65536
MAX_TRACKS=32
MAX_CHUNKS=262144
MAX_SAMPLES=8_000_000
MAX_TAG=64*1024
MAX_COVER=8*1024*1024
class Refused(ValueError):pass

def need(value,reason):
    if not value:raise Refused(reason)

def u32(data,at):
    need(0<=at and at+4<=len(data),'Truncated integer')
    return int.from_bytes(data[at:at+4],'big')

@dataclass(frozen=True)
class Box:
    kind:bytes
    start:int
    size:int
    header:int
    raw:bytes
    @property
    def payload(self):return self.raw[self.header:]

def boxes(data):
    need(isinstance(data,bytes) and len(data)<=MAX_MOOV,'Container byte bound')
    result=[];at=0
    while at<len(data):
        need(len(result)<MAX_BOXES and at+8<=len(data),'Box count/header bound')
        size=u32(data,at);header=8;kind=data[at+4:at+8]
        need(size!=0,'EOF-sized boxes unsupported')
        if size==1:
            need(at+16<=len(data),'Truncated extended box')
            size=int.from_bytes(data[at+8:at+16],'big');header=16
        need(size>=header and at+size<=len(data),'Box extent invalid')
        result.append(Box(kind,at,size,header,data[at:at+size]));at+=size
    return result

def build(kind,payload,extended=False):
    size=len(payload)+(16 if extended else 8)
    need(size<=MAX_MOOV and len(kind)==4,'New metadata box size bound')
    if extended:return struct.pack('>I4sQ',1,kind,size)+payload
    need(size<2**32,'32-bit box overflow')
    return struct.pack('>I4s',size,kind)+payload

def repack(box,payload):return build(box.kind,payload,box.header==16)

def one(items,kind,optional=False):
    matches=[b for b in items if b.kind==kind]
    need(len(matches)<=1 and (optional or len(matches)==1),'Missing/duplicate '+repr(kind))
    return matches[0] if matches else None

def profile(items,allowed):
    need(all(b.kind in allowed for b in items),'Unsupported structural box')

def full(payload,versions=(0,)):
    need(len(payload)>=4 and payload[0] in versions and payload[1:4]==bytes(3),'Full-box version/flags')

def table(payload,width,versions=(0,),maximum=MAX_SAMPLES):
    full(payload,versions);count=u32(payload,4)
    need(count<=maximum and len(payload)==8+count*width,'Table count/extent')
    return count

def clock(payload):
    full(payload,(0,1));at=12 if payload[0]==0 else 20;width=4 if payload[0]==0 else 8
    need(at+4+width<=len(payload),'Clock header')
    scale=u32(payload,at);duration=int.from_bytes(payload[at+4:at+4+width],'big')
    need(scale>0 and duration>0,'Zero clock/duration')
    return scale,duration

def dref(minf):
    dinf=one(minf,b'dinf');parts=boxes(dinf.payload);profile(parts,{b'dref'})
    data=one(parts,b'dref').payload;full(data)
    refs=boxes(data[8:]);need(u32(data,4)==1 and len(refs)==1,'Data reference profile')
    need(refs[0].kind==b'url ' and refs[0].payload==bytes((0,0,0,1)),'External/reference data refused')

def sample_description(payload,handler):
    full(payload);entries=boxes(payload[8:]);need(u32(payload,4)==1 and len(entries)==1,'Single sample description required')
    entry=entries[0];p=entry.payload
    need(len(p)>=8 and p[:6]==bytes(6) and p[6:8]==bytes((0,1)),'Sample data reference')
    if handler==b'soun':
        need(entry.kind==b'mp4a' and len(p)>=28 and p[8:16]==bytes(8),'Unsupported audio sample entry')
        sub=boxes(p[28:]);profile(sub,{b'esds',b'btrt',b'chan'})
        esds=one(sub,b'esds');full(esds.payload);need(len(esds.payload)>4,'Missing decoder description')
    elif handler==b'vide':
        need(entry.kind in (b'mjpg',b'jpeg') and len(p)>=78,'Unsupported chapter image sample entry')
        extensions=boxes(p[78:]);profile(extensions,{b'fiel'})
        need(len(extensions)<=1 and all(b.payload==bytes((1,0)) for b in extensions),'Unknown chapter image field extension')
    else:need(handler==b'text' and entry.kind==b'text' and len(p)==51,'Unsupported chapter text entry')
    return entry.kind

def validate_track(box,mdat_extents,chunk_budget):
    parts=boxes(box.payload);profile(parts,{b'tkhd',b'edts',b'mdia',b'tref',b'udta'})
    tkhd=one(parts,b'tkhd').payload
    need(len(tkhd)>=4 and tkhd[0] in (0,1),'Track header version')
    identity=u32(tkhd,12 if tkhd[0]==0 else 20);need(identity>0,'Track identity')
    edit=one(parts,b'edts',True)
    if edit:
        es=boxes(edit.payload);profile(es,{b'elst'});p=one(es,b'elst').payload
        n=table(p,12 if p[0]==0 else 20,(0,1),4096);w=4 if p[0]==0 else 8
        for i in range(n):
            row=p[8+i*(2*w+4):8+(i+1)*(2*w+4)]
            need(int.from_bytes(row[:w],'big')>0 and int.from_bytes(row[w:2*w],'big',signed=True)>=-1 and row[2*w:]==bytes((0,1,0,0)),'Unsupported edit list rate/value')
    media=boxes(one(parts,b'mdia').payload);profile(media,{b'mdhd',b'hdlr',b'minf'})
    _,duration=clock(one(media,b'mdhd').payload)
    h=one(media,b'hdlr').payload;full(h);need(len(h)>=24,'Handler header');handler=h[8:12]
    need(handler in (b'soun',b'text',b'vide'),'Unsupported track handler')
    minf=boxes(one(media,b'minf').payload);profile(minf,{b'smhd',b'vmhd',b'nmhd',b'gmhd',b'dinf',b'stbl',b'hdlr'})
    dref(minf)
    stbl=boxes(one(minf,b'stbl').payload)
    profile(stbl,{b'stsd',b'stts',b'ctts',b'stsc',b'stsz',b'stco',b'co64',b'stss',b'sdtp',b'sgpd',b'sbgp'})
    for kind in {b'stsd',b'stts',b'stsc',b'stsz'}:one(stbl,kind)
    codec=sample_description(one(stbl,b'stsd').payload,handler)
    timing=one(stbl,b'stts').payload;nr=table(timing,8);samples=0;ticks=0
    for at in range(8,len(timing),8):
        count,delta=struct.unpack_from('>II',timing,at);need(count>0 and delta>0,'Invalid decode run');samples+=count;ticks+=count*delta
    need(0<samples<=MAX_SAMPLES and ticks==duration,'Decode count/media clock mismatch')
    description=one(stbl,b'sgpd',True);mapping=one(stbl,b'sbgp',True)
    if description is not None or mapping is not None:
        # Narrow FFmpeg AAC preroll profile: one -1 roll descriptor applied
        # to every sample. These address-free bytes remain wholly unchanged.
        # libavformat/movenc.c mov_preroll_write_stbl_atoms (FFmpeg 8.1).
        need(handler==b'soun' and codec==b'mp4a' and description is not None and mapping is not None,'Unsupported sample group pair')
        need(description.payload==bytes.fromhex('01000000726f6c6c0000000200000001ffff'),'Unsupported AAC roll description')
        p=mapping.payload
        need(len(p)==20 and p[:12]==bytes.fromhex('00000000726f6c6c00000001') and u32(p,12)==samples and u32(p,16)==1,'AAC roll mapping count/reference')
    composition=one(stbl,b'ctts',True)
    if composition:
        p=composition.payload;table(p,8,(0,1));need(sum(u32(p,a) for a in range(8,len(p),8))==samples,'Composition sample count')
    sync=one(stbl,b'stss',True)
    if sync:
        p=sync.payload;table(p,4);values=[u32(p,a) for a in range(8,len(p),4)]
        need(all(1<=v<=samples for v in values) and values==sorted(set(values)),'Sync sample bounds')
    deps=one(stbl,b'sdtp',True)
    if deps:full(deps.payload);need(len(deps.payload)==4+samples,'Dependency sample count')
    sizes=one(stbl,b'stsz').payload;full(sizes);fixed=u32(sizes,4)
    need(u32(sizes,8)==samples and len(sizes)==12+(0 if fixed else samples*4),'Sample size table')
    offsets=[b for b in stbl if b.kind in (b'stco',b'co64')];need(len(offsets)==1,'Ambiguous chunk offset table')
    p=offsets[0].payload;width=4 if offsets[0].kind==b'stco' else 8;nchunks=table(p,width,maximum=chunk_budget)
    need(nchunks>0,'No chunks')
    sc=one(stbl,b'stsc').payload;nsc=table(sc,12,maximum=4096);need(nsc>0,'No chunk map')
    runs=[struct.unpack_from('>III',sc,a) for a in range(8,len(sc),12)]
    need(runs[0][0]==1 and all(1<=a<=nchunks and b>0 and c==1 for a,b,c in runs) and [r[0] for r in runs]==sorted(set(r[0] for r in runs)),'Chunk map profile')
    spans=[];sample=0;ri=0
    for index in range(nchunks):
        while ri+1<len(runs) and runs[ri+1][0]<=index+1:ri+=1
        count=runs[ri][1];need(sample+count<=samples,'Chunk/sample overflow')
        if fixed:length=fixed*count
        else:
            length=0
            for j in range(sample,sample+count):
                size=u32(sizes,12+4*j);need(size>0,'Zero sample');length+=size
        at=8+index*width;start=int.from_bytes(p[at:at+width],'big');end=start+length
        need(length>0 and any(lo<=start<end<=hi for lo,hi in mdat_extents),'Chunk outside retained mdat')
        spans.append((start,end));sample+=count
    need(sample==samples,'Unmapped samples')
    refs=[];tref=one(parts,b'tref',True)
    if tref:
        refsbox=boxes(tref.payload);profile(refsbox,{b'chap'})
        for ref in refsbox:
            need(0<len(ref.payload)<=4*MAX_TRACKS and len(ref.payload)%4==0,'Chapter reference size')
            refs.extend(u32(ref.payload,i) for i in range(0,len(ref.payload),4))
    # Track-local user data has no allowed mutable field in this profile.
    need(one(parts,b'udta',True) is None,'Unsupported track-local user data')
    return {'id':identity,'handler':handler,'codec':codec,'chap':refs,'samples':samples,'spans':spans,'sha256':hashlib.sha256(box.raw).hexdigest()}

TEXT_TAGS={'title':b'\xa9nam','album':b'\xa9alb','artist':b'\xa9ART','album_artist':b'aART','genre':b'\xa9gen','comment':b'\xa9cmt','grouping':b'\xa9grp','sort_album':b'soal','sort_name':b'sonm'}
def approved_items(tags,cover):
    need(isinstance(tags,dict) and set(tags)<=set(TEXT_TAGS)|{'media_type','track'},'Unknown approved tag')
    result={}
    for key,value in tags.items():
        if key in TEXT_TAGS:
            need(isinstance(value,str),'Text tag type');payload=value.encode('utf8');need(len(payload)<=MAX_TAG,'Text tag bound');kind=TEXT_TAGS[key];dtype=1
        elif key=='media_type':need(str(value)=='2','Audiobook media type');kind=b'stik';dtype=21;payload=b'\x02'
        else:
            need(str(value).isdigit() and 0<int(value)<65536,'Track number bound');kind=b'trkn';dtype=0;payload=struct.pack('>HHHH',0,int(value),0,0)
        result[kind]=build(kind,build(b'data',struct.pack('>II',dtype,0)+payload))
    if cover is not None:
        need(isinstance(cover,bytes) and 0<len(cover)<=MAX_COVER,'Artwork bound')
        dtype=14 if cover.startswith(b'\x89PNG\r\n\x1a\n') else 13 if cover.startswith(b'\xff\xd8\xff') else None
        need(dtype is not None,'Artwork format');result[b'covr']=build(b'covr',build(b'data',struct.pack('>II',dtype,0)+cover))
    need(result,'No approved metadata changes');return result

def rewrite_metadata(movie,tags,cover):
    desired=approved_items(tags,cover);parts=boxes(movie.payload);udta=one(parts,b'udta',True)
    up=boxes(udta.payload) if udta else [];profile(up,{b'meta',b'chpl',b'cprt'})
    meta=one(up,b'meta',True)
    mp=boxes(meta.payload[4:]) if meta else []
    if meta:full(meta.payload);profile(mp,{b'hdlr',b'ilst',b'free'})
    hd=one(mp,b'hdlr',True)
    if hd:full(hd.payload);need(len(hd.payload)>=24 and hd.payload[8:12]==b'mdir','Metadata handler profile')
    else:hd=Box(b'hdlr',0,0,8,build(b'hdlr',bytes(8)+b'mdir'+bytes(12)))
    ilst=one(mp,b'ilst',True);items=boxes(ilst.payload) if ilst else [];need(len(items)<=4096,'Metadata item bound')
    for item in items:
        sub=boxes(item.payload);profile(sub,{b'data',b'mean',b'name'})
        need(all(len(b.payload)>=4 for b in sub),'Metadata item format')
    for key in desired:need(sum(i.kind==key for i in items)<=1,'Duplicate approved metadata item')
    rewritten=b''.join(desired.pop(i.kind) if i.kind in desired else i.raw for i in items)+b''.join(desired.values())
    newilst=repack(ilst,rewritten) if ilst else build(b'ilst',rewritten)
    metadata_children=b''.join(newilst if i.kind==b'ilst' else i.raw for i in mp)
    if hd not in mp:metadata_children=hd.raw+metadata_children
    if ilst is None:metadata_children+=newilst
    newmeta=build(b'meta',bytes(4)+metadata_children,meta.header==16 if meta else False)
    newudta=build(b'udta',b''.join(newmeta if i.kind==b'meta' else i.raw for i in up)+(newmeta if meta is None else b''),udta.header==16 if udta else False)
    payload=b''.join(newudta if i.kind==b'udta' else i.raw for i in parts)+(newudta if udta is None else b'')
    return repack(movie,payload)

@dataclass(frozen=True)
class Plan:
    source_size:int
    movie_offset:int
    movie_size:int
    movie_sha256:str
    appended_movie:bytes
    tracks:tuple
    mdat_extents:tuple

def plan(source_size,read_at,tags,cover=None):
    need(type(source_size) is int and 0<source_size<2**63,'Source size')
    at=0;top=[];movie=None;extents=[];header_reads=0
    def read(offset,count):
        nonlocal header_reads
        need(0<=offset<=source_size and 0<=count<=MAX_MOOV and offset+count<=source_size and header_reads+count<=MAX_MOOV+65536,'Metadata read bound')
        data=read_at(offset,count);need(isinstance(data,bytes) and len(data)==count,'Short protected read');header_reads+=count;return data
    while at<source_size:
        need(len(top)<128,'Top-level box count');head=read(at,8);size=u32(head,0);kind=head[4:8];header=8
        need(size!=0,'EOF-sized box unsupported')
        if size==1:size=int.from_bytes(read(at+8,8),'big');header=16
        need(size>=header and at+size<=source_size,'Top-level extent invalid')
        need(kind in {b'ftyp',b'moov',b'mdat',b'free',b'skip',b'wide'},'Unsupported top-level reference/fragment box')
        # Apple's wide atom is exactly an empty8byte header reserving room for
        # a future extended mdat header. Keep it at its original offset.
        if top and top[-1]==b'wide':need(kind==b'mdat','Wide placeholder must precede retained mdat')
        if kind==b'wide':need(size==8 and header==8,'Unsupported wide placeholder extent')
        if kind==b'ftyp':
            need(at==0 and size<=1024,'File type location/bound');p=read(at+header,size-header)
            need(len(p)>=8 and len(p)%4==0,'File type payload')
            brands={p[:4],*(p[i:i+4] for i in range(8,len(p),4))}
            need(brands<={b'M4A ',b'M4B ',b'isom',b'iso2',b'mp41',b'mp42',b'qt  '} and p[:4] in (b'M4A ',b'M4B ',b'isom',b'mp42'),'Unsupported/ambiguous brand')
        elif kind==b'moov':
            need(movie is None and size<=MAX_MOOV,'Multiple/oversized movie');movie=Box(kind,at,size,header,read(at,size))
        elif kind==b'mdat':extents.append((at+header,at+size))
        top.append(kind);at+=size
    need(top.count(b'ftyp')==1 and movie is not None and extents and top[-1]!=b'wide','Required top-level boxes/wide successor')
    parts=boxes(movie.payload);profile(parts,{b'mvhd',b'trak',b'udta'});clock(one(parts,b'mvhd').payload)
    track_boxes=[b for b in parts if b.kind==b'trak'];need(0<len(track_boxes)<=MAX_TRACKS,'Track count')
    tracks=[];remaining_chunks=MAX_CHUNKS
    for track_box in track_boxes:
        track=validate_track(track_box,extents,remaining_chunks);remaining_chunks-=len(track['spans']);tracks.append(track)
    ids=[t['id'] for t in tracks];need(len(set(ids))==len(ids),'Duplicate track identity')
    audio=[t for t in tracks if t['handler']==b'soun'];need(len(audio)==1,'Exactly one audio track required')
    referenced=set(audio[0]['chap']);need(referenced<=set(ids)-{audio[0]['id']},'Unresolved chapter reference')
    need(all(t['handler']==b'soun' or t['id'] in referenced for t in tracks),'Unreferenced chapter/video track')
    spans=sorted(span for t in tracks for span in t['spans'])
    need(all(left[1]<=right[0] for left,right in zip(spans,spans[1:])),'Overlapping sample payload')
    appended=rewrite_metadata(movie,tags,cover)
    # The entire trak bytes, not rounded timestamps, establish preservation.
    need([b.raw for b in boxes(appended[16:] if appended[:4]==b'\0\0\0\1' else appended[8:]) if b.kind==b'trak']==[b.raw for b in parts if b.kind==b'trak'],'Track bytes changed')
    return Plan(source_size,movie.start,movie.size,hashlib.sha256(movie.raw).hexdigest(),appended,tuple({k:v for k,v in t.items() if k!='spans'} for t in tracks),tuple(extents))

def stream_candidate(source_plan,read_at,write,stopped=lambda:False):
    """Copy to caller-owned private sink. No source writes or path operations."""
    source_hash=hashlib.sha256();candidate_hash=hashlib.sha256();offset=0;patch=source_plan.movie_offset+4
    while offset<source_plan.source_size:
        if stopped():raise InterruptedError('Metadata preservation paused; source unchanged')
        count=min(1024*1024,source_plan.source_size-offset);block=read_at(offset,count)
        need(isinstance(block,bytes) and len(block)==count,'Short immutable stream read');source_hash.update(block)
        start=max(offset,patch);end=min(offset+count,patch+4)
        if start<end:block=block[:start-offset]+b'free'[start-patch:end-patch]+block[end-offset:]
        write(block);candidate_hash.update(block);offset+=count
    if stopped():raise InterruptedError('Metadata preservation paused; source unchanged')
    write(source_plan.appended_movie);candidate_hash.update(source_plan.appended_movie)
    return {'schema':'m4b-metadata-preservation-v1','source_sha256':source_hash.hexdigest(),'sha256':candidate_hash.hexdigest(),'size':source_plan.source_size+len(source_plan.appended_movie),'old_moov_offset':source_plan.movie_offset,'old_moov_size':source_plan.movie_size,'old_moov_sha256':source_plan.movie_sha256,'appended_moov_sha256':hashlib.sha256(source_plan.appended_movie).hexdigest(),'track_sha256':[t['sha256'] for t in source_plan.tracks],'source_offsets_preserved':True,'fast_start_preserved':False,'pcm_verified':False}

def verify_candidate(source_plan, source_read, candidate_size, candidate_read, stopped=lambda:False):
    """Independently reread both immutable streams; permit only the planned patch.

    This proves *all* retained bytes, including unknown mdat padding, rather than
    trusting a successful writer or comparing only selected audio packets.
    """
    need(candidate_size==source_plan.source_size+len(source_plan.appended_movie),'Candidate extent changed')
    offset=0;source_hash=hashlib.sha256();output_hash=hashlib.sha256()
    patch=source_plan.movie_offset+4
    while offset<source_plan.source_size:
        if stopped():raise InterruptedError('Preservation verification paused')
        count=min(1024*1024,source_plan.source_size-offset)
        original=source_read(offset,count);actual=candidate_read(offset,count)
        need(isinstance(original,bytes) and isinstance(actual,bytes) and len(original)==count and len(actual)==count,'Short verification read')
        source_hash.update(original);output_hash.update(actual)
        start=max(offset,patch);end=min(offset+count,patch+4)
        expected=original
        if start<end:expected=original[:start-offset]+b'free'[start-patch:end-patch]+original[end-offset:]
        need(actual==expected,'Candidate changed retained source bytes')
        offset+=count
    appended=candidate_read(offset,len(source_plan.appended_movie))
    need(appended==source_plan.appended_movie,'Candidate metadata differs from approved plan')
    output_hash.update(appended)
    return {'source_sha256':source_hash.hexdigest(),'sha256':output_hash.hexdigest(),'size':candidate_size,'all_retained_bytes_verified':True}
