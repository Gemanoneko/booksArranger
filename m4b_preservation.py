"""Bounded metadata-only M4B construction; callers own immutable input/private sink.

No decoder, remuxer, filesystem opening or publication occurs here. Every original
track and mdat byte remains at its original offset. Only approved Apple metadata
items change, and blank metadata is dropped in four exact shapes (clean_items and
udta_padding, recorded in the receipt); the prior moov becomes same-extent free and a new
moov is appended.

Writer-family allowances are exact observed shapes, never wider tolerances. Damage
repair is a separate explicit mode (plan(repair=...)): the caller names each repair
kind, and only those exact damage shapes are accepted; everything else is refused.
"""
import hashlib
import struct
from dataclasses import dataclass

MAX_MOOV=32*1024*1024
MAX_BOXES=65536
MAX_TRACKS=32
# Work bound, not a proof rule: every chunk is still individually proven inside retained mdat,
# non-overlapping and fully mapped. 2**19 covers the largest library book (322,966 chunks) with
# headroom. Measured: 2**19 one-sample chunks plan in 23 s / 181 MiB peak; the largest book
# (322,966 chunks, 1.6M samples) in 53 s / 241 MiB. Time follows MAX_SAMPLES, not chunks.
MAX_CHUNKS=524288
MAX_SAMPLES=8_000_000
MAX_TAG=64*1024
MAX_COVER=8*1024*1024
BRANDS={b'M4A ',b'M4B ',b'isom',b'iso2',b'mp41',b'mp42',b'qt  '}
MAJOR_BRANDS=(b'M4A ',b'M4B ',b'isom',b'mp42')
# iTunes-style writers pad the compatible-brand list with an all-zero slot; it asserts nothing.
ZERO_BRAND=bytes(4)
# Whole ftyp payloads accepted verbatim: Chapter and Verse 1.5 writes a NUL-terminated major.
EXACT_FTYP={b'M4A\0'+bytes(4)+b'3gp5'+b'isom'}
# QuickTime "media is in this file" data reference: version 0, flags 1, no alias record.
SELF_REFERENCE=bytes((0,0,0,1))
# MPEG-4 initial object descriptor (moov/iods), the one observed form: 24 bytes, full box version 0
# flags 0, one MP4_IOD descriptor (tag 0x10, 4-byte length 7) naming object descriptor 1 with no URL
# and no inline-profile flag, then its five profile-level bytes. Seven bytes leave no room for an
# ES_ID_Inc, so this form references no track. Copied unchanged; any other iods is refused.
IODS_FORM=bytes.fromhex('00000018'+'696f6473'+'00000000'+'10'+'80808007'+'004f')
IODS_PROFILE_BYTES=5
# Track user data holding a single empty 'name' (FAAC 1.28): nothing to change. Copied unchanged.
EMPTY_TRACK_NAME=bytes.fromhex('00000010'+'75647461'+'00000008'+'6e616d65')
# Damage repairs (explicit, user-requested only). See plan(repair=...).
REPAIR_DANGLING_CHAPTER='dangling_chapter_reference'
REPAIR_TAIL_OVERRUN='mdat_tail_overrun'
REPAIR_TRUNCATED_FRAMES='truncated_final_frames'
REPAIR_MDAT_UNDERSTATED='mdat_size_understated'
REPAIRS=frozenset({REPAIR_DANGLING_CHAPTER,REPAIR_TAIL_OVERRUN,REPAIR_TRUNCATED_FRAMES,REPAIR_MDAT_UNDERSTATED})
MAX_TAIL_PAD=4096
# Silence repair bounds: the file may end at most 64 KiB early, and the frames that reach past
# EOF (only the final audio frames, AAC-LC 1024-sample, mono/stereo) may total at most 1 second.
MAX_TRUNCATED_TAIL=64*1024
MAX_SILENCE_SECONDS=1
AAC_FRAME=1024
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

def dref(minf,handler):
    dinf=one(minf,b'dinf');parts=boxes(dinf.payload);profile(parts,{b'dref'})
    data=one(parts,b'dref').payload;full(data)
    refs=boxes(data[8:]);need(u32(data,4)==1 and len(refs)==1,'Data reference profile')
    # QuickTime chapter text and chapter image tracks say "this file" with an empty self alias
    # ('alis', flags 1); same meaning as 'url ' flags 1. Any alias record, other flags or an audio
    # alias is refused.
    kinds=(b'url ',b'alis') if handler in (b'text',b'vide') else (b'url ',)
    need(refs[0].kind in kinds and refs[0].payload==SELF_REFERENCE,'External/reference data refused')

def sample_description(payload,handler):
    full(payload);entries=boxes(payload[8:]);need(u32(payload,4)==1 and len(entries)==1,'Single sample description required')
    entry=entries[0];p=entry.payload
    # Index 0 on a chapter text entry can only resolve to the single self-contained data
    # reference dref() has already proven; audio and image entries must name entry 1.
    index=p[6:8];indexes=(b'\0\1',b'\0\0') if handler==b'text' else (b'\0\1',)
    need(len(p)>=8 and p[:6]==bytes(6) and index in indexes,'Sample data reference')
    if handler==b'soun':
        need(entry.kind==b'mp4a' and len(p)>=28 and p[8:16]==bytes(8),'Unsupported audio sample entry')
        sub=boxes(p[28:]);profile(sub,{b'esds',b'btrt',b'chan'})
        esds=one(sub,b'esds');full(esds.payload);need(len(esds.payload)>4,'Missing decoder description')
    elif handler==b'vide':
        need(entry.kind in (b'mjpg',b'jpeg') and len(p)>=78,'Unsupported chapter image sample entry')
        extensions=boxes(p[78:]);profile(extensions,{b'fiel'})
        need(len(extensions)<=1 and all(b.payload==bytes((1,0)) for b in extensions),'Unknown chapter image field extension')
    else:
        # 51 bytes, or QuickTime 7's 52 with one trailing empty (zero-length) font-name byte.
        need(handler==b'text' and entry.kind==b'text' and (len(p)==51 or len(p)==52 and p[51]==0),'Unsupported chapter text entry')
    return entry.kind

def aac_lc_layout(esds_payload):
    """(sampling_index, channels) for a plain 2-byte AAC-LC AudioSpecificConfig, else refused.

    Silence repair only: 1024-sample frames, no SBR/PS or other extension, mono or stereo.
    """
    p=esds_payload;full(p);at=4
    def descriptor(at,tag):
        need(at<len(p) and p[at]==tag,'Silence repair needs an AAC-LC decoder description');at+=1;length=0
        for _ in range(4):
            need(at<len(p),'Decoder description truncated');value=p[at];at+=1;length=(length<<7)|(value&0x7f)
            if not value&0x80:break
        need(at+length<=len(p),'Decoder description truncated');return at,length
    at,_=descriptor(at,3);need(at+3<=len(p),'Decoder description truncated');flags=p[at+2];at+=3
    if flags&0x80:at+=2
    if flags&0x40:need(at<len(p),'Decoder description truncated');at+=1+p[at]
    if flags&0x20:at+=2
    at,_=descriptor(at,4);need(at+13<=len(p) and p[at]==0x40,'Silence repair needs MPEG-4 audio');at+=13
    # 2 bytes, or 5 where the tail is exactly the sync extension 0x2b7/AOT_SBR/sbrPresentFlag=0
    # ("explicitly no SBR", written by FFmpeg). Any SBR/PS signalling stays refused.
    at,length=descriptor(at,5);need(length==2 or length==5 and p[at+2:at+5]==b'\x56\xe5\x00','Silence repair needs a plain AAC-LC configuration')
    bits=int.from_bytes(p[at:at+2],'big');kind,index,channels,rest=bits>>11,(bits>>7)&15,(bits>>3)&15,bits&7
    need(kind==2 and index<13 and channels in (1,2) and rest==0,'Silence repair needs AAC-LC mono/stereo with 1024-sample frames')
    return index,channels

def silent_aac_frame(channels):
    """One raw AAC-LC frame of digital silence (ISO/IEC 14496-3 raw_data_block).

    SCE (mono) or CPE without common window (stereo); each channel: global_gain 100,
    ONLY_LONG_SEQUENCE, max_sfb 0 (no sections, scalefactors or spectral data), no pulse/TNS/
    gain control; then END. Decodes to zero spectrum for 1024 samples.
    """
    need(channels in (1,2),'Silence repair needs mono or stereo')
    bits=[]
    def put(value,width):bits.extend((value>>(width-1-i))&1 for i in range(width))
    def channel_stream():put(100,8);put(0,1);put(0,2);put(0,1);put(0,6);put(0,1);put(0,3)
    if channels==1:put(0,3);put(0,4);channel_stream()
    else:put(1,3);put(0,4);put(0,1);channel_stream();channel_stream()
    put(7,3);bits.extend([0]*(-len(bits)%8))
    return bytes(int(''.join(map(str,bits[i:i+8])),2) for i in range(0,len(bits),8))

def validate_track(box,mdat_extents,chunk_budget,eof=None):
    # free/skip carry no semantics at any level (QuickTime 7 writers leave them inside trak).
    parts=boxes(box.payload);profile(parts,{b'tkhd',b'edts',b'mdia',b'tref',b'udta',b'free',b'skip'})
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
    dref(minf,handler)
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
    # Strictly increasing first chunks within 1..nchunks already bound the row count by the
    # proven chunk count; QuickTime 7 writes one row whenever the chunk size changes.
    sc=one(stbl,b'stsc').payload;nsc=table(sc,12,maximum=nchunks);need(nsc>0,'No chunk map')
    runs=[struct.unpack_from('>III',sc,a) for a in range(8,len(sc),12)]
    need(runs[0][0]==1 and all(1<=a<=nchunks and b>0 and c==1 for a,b,c in runs) and [r[0] for r in runs]==sorted(set(r[0] for r in runs)),'Chunk map profile')
    spans=[];sample=0;ri=0;cut=[]
    for index in range(nchunks):
        while ri+1<len(runs) and runs[ri+1][0]<=index+1:ri+=1
        count=runs[ri][1];need(sample+count<=samples,'Chunk/sample overflow')
        if fixed:length=fixed*count
        else:
            length=0
            for j in range(sample,sample+count):
                size=u32(sizes,12+4*j);need(size>0,'Zero sample');length+=size
        at=8+index*width;start=int.from_bytes(p[at:at+width],'big');end=start+length
        if eof is not None and end>eof:
            # Silence repair only: name each sample of this chunk that reaches past the file end.
            need(handler==b'soun','Truncated chapter samples cannot be repaired')
            need(not fixed,'Truncated fixed-size samples cannot be repaired');position=start
            for j in range(sample,sample+count):
                size=u32(sizes,12+4*j)
                if position+size>eof:cut.append(j)
                position+=size
        need(length>0 and any(lo<=start<end<=hi for lo,hi in mdat_extents),'Chunk outside retained mdat')
        spans.append((start,end));sample+=count
    need(sample==samples,'Unmapped samples')
    refs=[];tref=one(parts,b'tref',True);chap_boxes=0
    if tref:
        refsbox=boxes(tref.payload);profile(refsbox,{b'chap'});chap_boxes=len(refsbox)
        for ref in refsbox:
            need(0<len(ref.payload)<=4*MAX_TRACKS and len(ref.payload)%4==0,'Chapter reference size')
            refs.extend(u32(ref.payload,i) for i in range(0,len(ref.payload),4))
    # Track-local user data has no allowed mutable field in this profile; only the exact empty-name
    # shape is kept, byte for byte (the whole trak is compared after the rewrite).
    local=one(parts,b'udta',True);need(local is None or local.raw==EMPTY_TRACK_NAME,'Unsupported track-local user data')
    return {'id':identity,'handler':handler,'codec':codec,'chap':refs,'chap_boxes':chap_boxes,'samples':samples,'spans':spans,'cut':cut,'sha256':hashlib.sha256(box.raw).hexdigest()}

def profile_zero_chapter_count(box,mdat_extents,chunk_budget,read_at):
    """Recognize only the observed zero-count QuickTime text writer quirk.

    A virtual count validates existing sample addresses; no native box is ever
    rewritten. All original track bytes and externally visible chapter
    presentation must remain unchanged. This does not claim the count valid.
    """
    parts=boxes(box.payload);mdia=one(parts,b'mdia');media=boxes(mdia.payload)
    if one(media,b'hdlr').payload[8:12]!=b'text':return None
    minf=one(media,b'minf');children=boxes(minf.payload);stbl=one(children,b'stbl');tables=boxes(stbl.payload)
    sizes=one(tables,b'stsz')
    if sizes.payload!=bytes(4)+struct.pack('>II',16,0):return None
    observed_stsd=bytes.fromhex('00000000000000010000003b7465787400000000000000010000000400000001ffffffffffff0000000000000000000000000010000d00000000000d00000000000000')
    need(one(tables,b'stsd').payload==observed_stsd,'Zero-count text profile sample description differs')
    offsets=one(tables,b'stco',True)
    need(offsets is not None and one(tables,b'co64',True) is None,'Zero-count text profile needs observed32-bit offsets')
    count=table(offsets.payload,4);need(0<count<=99,'Zero-count text profile label bound')
    need(one(tables,b'stsc').payload==bytes(4)+struct.pack('>IIII',1,1,1,1),'Zero-count text profile needs one sample per chunk')
    # Independent count comes from chunk entries, not inferred chapter timing.
    patched_sizes=repack(sizes,sizes.payload[:8]+struct.pack('>I',count))
    def replace(container,kind,raw):return repack(container,b''.join(raw if child.kind==kind else child.raw for child in boxes(container.payload)))
    new_stbl=replace(stbl,b'stsz',patched_sizes);new_minf=replace(minf,b'stbl',new_stbl)
    new_mdia=replace(mdia,b'minf',new_minf);patched=replace(box,b'mdia',new_mdia)
    track=validate_track(boxes(patched)[0],mdat_extents,chunk_budget)
    need(track['handler']==b'text' and track['codec']==b'text' and track['samples']==count,'Zero-count text profile identity mismatch')
    payload_hash=hashlib.sha256()
    for index,(start,end) in enumerate(track['spans'],1):
        need(end-start==16,'Zero-count text profile needs fixed16-byte samples')
        raw=read_at(start,16)
        need(raw==b'\x00\x02'+f'{index:02d}'.encode('ascii')+bytes.fromhex('0000000c656e636400000100'),'Zero-count text profile label bytes differ')
        payload_hash.update(raw)
    track['sha256']=hashlib.sha256(box.raw).hexdigest()
    facts={'schema':'quicktime-zero-fixed-text-count-preserved-v1','track_id':track['id'],
           'invalid_field':'stsz.sample_count','preserved_count':0,'mapped_samples':count,
           'fixed_sample_bytes':16,'chapter_payload_sha256':payload_hash.hexdigest(),
           'unchanged_trak_sha256':track['sha256'],'native_track_bytes_unchanged':True,
           'note':'Observed zero text sample count preserved byte for byte; virtual count validates existing chunk extents only. Chapter presentation must match the source; no chapter repair or synthesis.'}
    return track,facts


def silence_final_frames(box,track,media_offset):
    """Repair only: the audio trak whose cut final samples point to silent frames at media_offset.

    Sample timing (stts/ctts/edts), the sample description and every intact sample's chunk
    offset and size stay exactly as in the source; only stsz entries of the cut samples and the
    chunk map/offsets of the final chunk change. Returns (trak bytes, silent frame, facts).
    """
    cut=track['cut'];n=track['samples'];k=len(cut);first=n-k
    need(0<k and cut==list(range(first,n)),'Only the final audio frames can be silenced')
    parts=boxes(box.payload);mdia=one(parts,b'mdia');media=boxes(mdia.payload)
    minf=one(media,b'minf');info=boxes(minf.payload);stbl=one(info,b'stbl');tables=boxes(stbl.payload)
    scale,_=clock(one(media,b'mdhd').payload)
    entry=boxes(one(tables,b'stsd').payload[8:])[0]
    _,channels=aac_lc_layout(one(boxes(entry.payload[28:]),b'esds').payload);silent=silent_aac_frame(channels)
    stts=one(tables,b'stts').payload;ticks=0;remaining=k
    for at in range(len(stts)-8,7,-8):
        count,delta=struct.unpack_from('>II',stts,at);take=min(count,remaining);ticks+=take*delta;remaining-=take
        if not remaining:break
    need(ticks<=MAX_SILENCE_SECONDS*scale,'Silence repair would replace more than one second of audio')
    sizes=one(tables,b'stsz');need(u32(sizes.payload,4)==0,'Truncated fixed-size samples cannot be repaired')
    chunks=next(b for b in tables if b.kind in (b'stco',b'co64'));width=4 if chunks.kind==b'stco' else 8;cp=chunks.payload
    offsets=[int.from_bytes(cp[8+i*width:8+(i+1)*width],'big') for i in range(u32(cp,4))]
    rows=[struct.unpack_from('>III',one(tables,b'stsc').payload,at) for at in range(8,len(one(tables,b'stsc').payload),12)]
    counts=[];row=0
    for index in range(len(offsets)):
        while row+1<len(rows) and rows[row+1][0]<=index+1:row+=1
        counts.append(rows[row][1])
    seen=0
    for boundary,count in enumerate(counts):
        if seen+count>first:break
        seen+=count
    kept=first-seen
    need(width==8 or media_offset+k*len(silent)<2**32,'Silence repair needs 64-bit chunk offsets')
    newcounts=counts[:boundary]+([kept] if kept else [])+[k]
    newoffsets=offsets[:boundary]+([offsets[boundary]] if kept else [])+[media_offset]
    newrows=[]
    for index,count in enumerate(newcounts):
        if not newrows or newrows[-1][1]!=count:newrows.append((index+1,count,1))
    replaced={b'stsc':repack(one(tables,b'stsc'),bytes(4)+struct.pack('>I',len(newrows))+b''.join(struct.pack('>III',*r) for r in newrows)),
        b'stsz':repack(sizes,sizes.payload[:12+4*first]+struct.pack('>I',len(silent))*k),
        chunks.kind:repack(chunks,bytes(4)+struct.pack('>I',len(newoffsets))+b''.join(v.to_bytes(width,'big') for v in newoffsets))}
    newstbl=repack(stbl,b''.join(replaced.get(b.kind,b.raw) for b in tables))
    newminf=repack(minf,b''.join(newstbl if b.kind==b'stbl' else b.raw for b in info))
    newmdia=repack(mdia,b''.join(newminf if b.kind==b'minf' else b.raw for b in media))
    repaired=repack(box,b''.join(newmdia if b.kind==b'mdia' else b.raw for b in parts))
    # Intact-prefix proof on the encoded tables: same sizes for samples before the cut, same
    # offsets and sample counts for every chunk before it (and for the kept part of its chunk).
    stbl_after=boxes(one(boxes(one(boxes(one(boxes(repaired[box.header:]),b'mdia').payload),b'minf').payload),b'stbl').payload)
    need([b.raw for b in stbl_after if b.kind not in replaced]==[b.raw for b in tables if b.kind not in replaced],'Silence repair changed a timing or description table')
    need(one(stbl_after,b'stsz').payload[:12+4*first]==sizes.payload[:12+4*first],'Silence repair changed an intact sample size')
    need(newoffsets[:boundary+(1 if kept else 0)]==offsets[:boundary+(1 if kept else 0)] and newcounts[:boundary]==counts[:boundary],'Silence repair moved an intact sample')
    facts={'kind':REPAIR_TRUNCATED_FRAMES,'track_id':track['id'],'first_frame':first,'frames':k,'replaced_ticks':ticks,'timescale':scale,
           'channels':channels,'silent_frame':silent.hex()}
    return repaired,silent,facts

def drop_chapter_references(box,keep):
    """Repair only: the same trak with its single tref/chap rewritten to `keep` (order kept).

    Every other child of the track, and every child of its media, stays byte-identical.
    """
    parts=boxes(box.payload);tref=one(parts,b'tref');refs=boxes(tref.payload)
    need(len(refs)==1 and refs[0].kind==b'chap','Chapter reference repair profile')
    newtref=repack(tref,repack(refs[0],b''.join(struct.pack('>I',i) for i in keep))) if keep else b''
    repaired=repack(box,b''.join(newtref if b.kind==b'tref' else b.raw for b in parts))
    after=boxes(repaired[box.header:])
    need([b.raw for b in after if b.kind!=b'tref']==[b.raw for b in parts if b.kind!=b'tref'],'Chapter reference repair changed track media')
    return repaired

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

def blank(box):
    """A blank box: its size field is intact and every byte after it, the type included, is zero."""
    return box.header==8 and not any(box.raw[4:])

def plain_data(box):
    """One Apple metadata value box: 'data', version 0, then its type and locale (8 bytes) and value."""
    return box.kind==b'data' and box.header==8 and len(box.payload)>=8 and box.payload[0]==0

def clean_items(found):
    """(items, dropped) for the ilst children: blank metadata is dropped in exactly two shapes.

    An item whose only child is blank says nothing: the whole item is dropped. An item holding blank
    children beside exactly one valid data box keeps that data box alone. Any other mix is refused.
    Every removal is reported, so the job's receipt records it.
    """
    items=[];dropped=[]
    for item in found:
        sub=boxes(item.payload);blanks=[b for b in sub if blank(b)]
        if blanks:
            name=item.kind.decode('latin-1')
            if len(sub)==1:
                dropped.append({'item':name,'removed':'item','bytes':item.size});continue
            kept=[b for b in sub if not blank(b)]
            need(len(kept)==1 and plain_data(kept[0]),'Blank metadata child beside other content')
            raw=repack(item,kept[0].raw);item=Box(item.kind,item.start,len(raw),item.header,raw);sub=kept
            dropped.append({'item':name,'removed':'blank_children','count':len(blanks),'bytes':sum(b.size for b in blanks)})
        profile(sub,{b'data',b'mean',b'name'})
        need(all(len(b.payload)>=4 for b in sub),'Metadata item format')
        items.append(item)
    return items,dropped

def udta_padding(up):
    """(children, dropped) for moov/udta: one zero padding box is dropped (Sergei, 2026-10-24).

    The shape is blank(): an intact 32-bit size field, then a type and payload that are all zero bytes. Seen in
    Макс Фрай 01 and 04 beside the real meta (70,903 and 100,381 bytes), where a tagger blanked an old meta in place;
    every audio sample of both books lies in mdat, outside it. Only moov/udta's own children are checked here, and
    only one such box is admitted. A zero box anywhere else, two of them, or one with a non-zero byte is still refused.
    """
    padding=[b for b in up if blank(b)]
    need(len(padding)<=1,'Unsupported structural box')
    # Ruling 32 (Sergei, 2026-10-26), «Джек из Тени»: one empty Xtra box (an intact 32-bit size field of 8, the type
    # "Xtra", nothing after it) beside the real meta; the decoded audio is the same without it. Only that exact box,
    # once, directly here: any content, a 64-bit header, a second one or any other place is still refused.
    xtra=[b for b in up if empty_xtra(b)]
    # Sergei 2026-10-26 (0.22.2), «The Little Sisters of Eluria»: one Xtra box holding only Windows Explorer's star rating
    # (the single property WM/SharedUserRating, one 8-byte value of 0-99) beside the real meta; the decoded audio is the
    # same without it. Only that exact shape, once, directly here, and never beside the empty Xtra box: any other
    # property, a second value or entry, another type or size, a 64-bit header or any other place is still refused.
    rating=[b for b in up if windows_rating(b)]
    need(len(xtra)+len(rating)<=1,'Unsupported structural box')
    kept=[b for b in up if not blank(b) and not empty_xtra(b) and not windows_rating(b)]
    return kept,([{'item':'udta','removed':'zero_padding','bytes':b.size} for b in padding]+[{'item':'udta','removed':'empty_xtra','bytes':b.size} for b in xtra]
                 +[{'item':'udta','removed':'windows_rating','bytes':b.size} for b in rating])

def empty_xtra(box):
    """The empty Xtra box of ruling 32: 8 bytes, a 32-bit size of 8 and the type "Xtra"."""
    return box.kind==b'Xtra' and box.header==8 and box.size==8 and box.raw==b'\0\0\0\x08Xtra'

WINDOWS_RATING=b'WM/SharedUserRating'

def windows_rating(box):
    """The rating-only Xtra box (Windows Explorer's Rating): a 53-byte box, 32-bit header, one 45-byte entry whose name is
    WM/SharedUserRating, holding one 14-byte value of type 0x0013 with an 8-byte little-endian rating of 0 to 99."""
    if box.kind!=b'Xtra' or box.header!=8 or box.size!=53:return False
    p=box.payload;name=len(WINDOWS_RATING)
    return (len(p)==45 and int.from_bytes(p[0:4],'big')==45 and int.from_bytes(p[4:8],'big')==name and p[8:8+name]==WINDOWS_RATING
            and int.from_bytes(p[8+name:12+name],'big')==1 and int.from_bytes(p[12+name:16+name],'big')==14 and p[16+name:18+name]==b'\0\x13'
            and int.from_bytes(p[18+name:26+name],'little')<=99)

def rewrite_metadata(movie,tags,cover):
    """(new movie bytes, dropped blank metadata) for the approved tags and cover."""
    desired=approved_items(tags,cover);parts=boxes(movie.payload);udta=one(parts,b'udta',True)
    # 'tags' is Nero's private tag store (meta values, cvrx cover copy, one tseg per chapter);
    # it is kept verbatim like chpl. A zero padding box is not copied into the new moov (udta_padding).
    up,padding=udta_padding(boxes(udta.payload) if udta else []);profile(up,{b'meta',b'chpl',b'cprt',b'tags'})
    nero=one(up,b'tags',True)
    if nero:profile(boxes(nero.payload),{b'meta',b'cvrx',b'tseg'})
    meta=one(up,b'meta',True)
    mp=boxes(meta.payload[4:]) if meta else []
    if meta:full(meta.payload);profile(mp,{b'hdlr',b'ilst',b'free'})
    hd=one(mp,b'hdlr',True)
    if hd:full(hd.payload);need(len(hd.payload)>=24 and hd.payload[8:12]==b'mdir','Metadata handler profile')
    else:hd=Box(b'hdlr',0,0,8,build(b'hdlr',bytes(8)+b'mdir'+bytes(12)))
    ilst=one(mp,b'ilst',True);found=boxes(ilst.payload) if ilst else [];need(len(found)<=4096,'Metadata item bound')
    items,dropped=clean_items(found)
    for key in desired:need(sum(i.kind==key for i in items)<=1,'Duplicate approved metadata item')
    rewritten=b''.join(desired.pop(i.kind) if i.kind in desired else i.raw for i in items)+b''.join(desired.values())
    newilst=repack(ilst,rewritten) if ilst else build(b'ilst',rewritten)
    metadata_children=b''.join(newilst if i.kind==b'ilst' else i.raw for i in mp)
    if hd not in mp:metadata_children=hd.raw+metadata_children
    if ilst is None:metadata_children+=newilst
    newmeta=build(b'meta',bytes(4)+metadata_children,meta.header==16 if meta else False)
    newudta=build(b'udta',b''.join(newmeta if i.kind==b'meta' else i.raw for i in up)+(newmeta if meta is None else b''),udta.header==16 if udta else False)
    payload=b''.join(newudta if i.kind==b'udta' else i.raw for i in parts)+(newudta if udta is None else b'')
    return repack(movie,payload),padding+dropped

@dataclass(frozen=True)
class Plan:
    source_size:int
    movie_offset:int
    movie_size:int
    movie_sha256:str
    appended_movie:bytes
    tracks:tuple
    mdat_extents:tuple
    tail_padding:int=0
    repairs:tuple=()
    appended_media:bytes=b''
    header_patches:tuple=()
    metadata_dropped:tuple=()
    profile_notes:tuple=()

def plan(source_size,read_at,tags,cover=None,repair=frozenset()):
    """repair names the damage kinds the user approved; each applies only to its exact shape.

    REPAIR_TAIL_OVERRUN: the final top-level mdat declares at most MAX_TAIL_PAD bytes past EOF
    and no sample of any track uses them. Zero bytes complete the declared extent.
    REPAIR_DANGLING_CHAPTER: the audio track's single chap list names track IDs absent from
    the movie. Only those IDs are dropped; every other track byte is unchanged.
    REPAIR_MDAT_UNDERSTATED: at most MAX_TRUNCATED_TAIL bytes after the final mdat are not a box
    and are exactly the final audio frames' bytes up to EOF. Only that mdat's 32-bit size field is
    corrected; every sample byte stays at its offset.
    REPAIR_TRUNCATED_FRAMES: the final mdat ends at most MAX_TRUNCATED_TAIL bytes early inside
    the last audio frames only (AAC-LC, at most MAX_SILENCE_SECONDS). Those frames become silent
    frames in an appended mdat; every intact frame keeps its bytes, offset and timing.
    """
    need(type(source_size) is int and 0<source_size<2**63,'Source size')
    need(isinstance(repair,(set,frozenset)) and repair<=REPAIRS,'Unknown repair')
    at=0;top=[];movie=None;extents=[];header_reads=0;padding=0;repairs=[];declared_end=None;understated=None;last_mdat=None;patches=()
    def read(offset,count):
        nonlocal header_reads
        need(0<=offset<=source_size and 0<=count<=MAX_MOOV and offset+count<=source_size and header_reads+count<=MAX_MOOV+65536,'Metadata read bound')
        data=read_at(offset,count);need(isinstance(data,bytes) and len(data)==count,'Short protected read');header_reads+=count;return data
    def is_box(at):
        if source_size-at<8:return False
        head=read(at,8);size=u32(head,0);kind=head[4:8]
        if size==1:
            if source_size-at<16:return False
            size=int.from_bytes(read(at+8,8),'big');header=16
        else:header=8
        return size>=header and at+size<=source_size and kind in {b'ftyp',b'moov',b'mdat',b'free',b'skip',b'wide'}
    while at<source_size:
        if REPAIR_MDAT_UNDERSTATED in repair and top and top[-1]==b'mdat' and source_size-at<=MAX_TRUNCATED_TAIL and not is_box(at):
            # Repair shape only: what follows the final mdat is not a box. The sample check below
            # must prove those bytes are exactly the final audio frames, up to EOF.
            understated=(last_mdat[0],last_mdat[1],at);extents[-1]=(extents[-1][0],source_size);break
        need(len(top)<128,'Top-level box count');head=read(at,8);size=u32(head,0);kind=head[4:8];header=8
        need(size!=0,'EOF-sized box unsupported')
        if size==1:size=int.from_bytes(read(at+8,8),'big');header=16
        need(size>=header,'Top-level extent invalid')
        if at+size>source_size:
            # Repair shapes only: the last box is mdat, its header is present and the missing tail
            # is small. The sample check below decides between them: no sample past EOF (tail
            # overrun) or only the final audio frames past EOF (truncated frames).
            missing=at+size-source_size
            need(kind==b'mdat' and at+header<=source_size and (REPAIR_TAIL_OVERRUN in repair and missing<=MAX_TAIL_PAD or REPAIR_TRUNCATED_FRAMES in repair and missing<=MAX_TRUNCATED_TAIL),'Top-level extent invalid')
            padding=missing;overrun_start=at;declared_end=at+size;size=source_size-at
        need(kind in {b'ftyp',b'moov',b'mdat',b'free',b'skip',b'wide'},'Unsupported top-level reference/fragment box')
        # Apple's wide atom is exactly an empty8byte header reserving room for
        # a future extended mdat header. Keep it at its original offset.
        if top and top[-1]==b'wide':need(kind==b'mdat','Wide placeholder must precede retained mdat')
        if kind==b'wide':need(size==8 and header==8,'Unsupported wide placeholder extent')
        if kind==b'ftyp':
            need(at==0 and size<=1024,'File type location/bound');p=read(at+header,size-header)
            need(len(p)>=8 and len(p)%4==0,'File type payload')
            brands={p[:4],*(p[i:i+4] for i in range(8,len(p),4))}-{ZERO_BRAND}
            need(p in EXACT_FTYP or brands<=BRANDS and p[:4] in MAJOR_BRANDS,'Unsupported/ambiguous brand')
        elif kind==b'moov':
            need(movie is None and size<=MAX_MOOV,'Multiple/oversized movie');movie=Box(kind,at,size,header,read(at,size))
        elif kind==b'mdat':extents.append((at+header,at+size));last_mdat=(at,header)
        top.append(kind);at+=size
    need(top.count(b'ftyp')==1 and movie is not None and extents and top[-1]!=b'wide','Required top-level boxes/wide successor')
    parts=boxes(movie.payload);profile(parts,{b'mvhd',b'trak',b'udta',b'iods'});clock(one(parts,b'mvhd').payload)
    descriptor=one(parts,b'iods',True)
    need(descriptor is None or descriptor.header==8 and len(descriptor.raw)==len(IODS_FORM)+IODS_PROFILE_BYTES and descriptor.raw.startswith(IODS_FORM),'Unsupported object descriptor')
    track_boxes=[b for b in parts if b.kind==b'trak'];need(0<len(track_boxes)<=MAX_TRACKS,'Track count')
    tracks=[];remaining_chunks=MAX_CHUNKS;profile_notes=[]
    # Only the silence repair lets chunks reach the declared (missing) tail, and it names every
    # sample that does; without it, chunks must lie inside the bytes the file actually holds.
    silence=bool(padding) and REPAIR_TRUNCATED_FRAMES in repair
    checked=[(lo,declared_end if hi==source_size else hi) for lo,hi in extents] if silence else extents
    for track_box in track_boxes:
        fixed=profile_zero_chapter_count(track_box,checked,remaining_chunks,read)
        if fixed:
            track,facts=fixed;profile_notes.append(facts)
        else:track=validate_track(track_box,checked,remaining_chunks,source_size if silence else None)
        remaining_chunks-=len(track['spans']);tracks.append(track)
    ids=[t['id'] for t in tracks];need(len(set(ids))==len(ids),'Duplicate track identity')
    audio=[t for t in tracks if t['handler']==b'soun'];need(len(audio)==1,'Exactly one audio track required')
    audio=audio[0];expected=[b.raw for b in track_boxes];output_movie=movie;media=b''
    index=next(i for i,t in enumerate(tracks) if t is audio)
    if understated:
        start,header,declared=understated
        need(header==8 and source_size-start<2**32,'Size repair needs a 32-bit audio container header')
        tail=sorted(span for span in audio['spans'] if span[1]>declared)
        need(tail and tail[0][0]<=declared and tail[-1][1]==source_size and all(a[1]==b[0] for a,b in zip(tail,tail[1:])),'Bytes after the audio container are not exactly the final audio frames')
        need(all(span[1]<=declared for t in tracks if t is not audio for span in t['spans']),'Chapter samples lie past the audio container')
        patches=((start,struct.pack('>I',source_size-start)),)
        repairs.append({'kind':REPAIR_MDAT_UNDERSTATED,'mdat_offset':start,'declared_bytes':declared-start,'actual_bytes':source_size-start,'understated_by':source_size-declared,
            'description':f'The audio container\'s size field ended {source_size-declared} bytes before the file does; the final audio frames sit in those bytes. Only that size field was corrected; all audio is unchanged.'})
    if padding and not any(t['cut'] for t in tracks):
        need(REPAIR_TAIL_OVERRUN in repair and padding<=MAX_TAIL_PAD,'Top-level extent invalid')
        repairs.append({'kind':REPAIR_TAIL_OVERRUN,'declared_bytes':declared_end-overrun_start,'present_bytes':source_size-overrun_start,'padding':padding,
            'description':f'The audio container declared {padding} bytes past the end of the file. No audio frame uses them; {padding} zero bytes complete it. All audio is unchanged.'})
    elif padding:
        need(all(not t['cut'] for t in tracks if t is not audio),'Truncated chapter samples cannot be repaired')
        offset=source_size+padding+8;repaired,silent,facts=silence_final_frames(track_boxes[index],audio,offset)
        media=build(b'mdat',silent*facts['frames'])
        check=validate_track(boxes(repaired)[0],extents+[(offset,offset+len(media)-8)],MAX_CHUNKS)
        need(all(check[key]==audio[key] for key in ('id','handler','codec','chap','samples')),'Silence repair changed the track')
        expected[index]=repaired;seconds=facts['replaced_ticks']/facts['timescale']
        repairs.append(facts|{'missing_bytes':padding,'padding':padding,
            'description':f'The file ends {padding} bytes early, inside the last {facts["frames"]} audio frame(s). Those {seconds:.3f} s were replaced with silence of the same length; every other audio frame is unchanged.'})
    dangling=[i for i in audio['chap'] if i not in ids]
    if dangling:
        need(REPAIR_DANGLING_CHAPTER in repair and audio['chap_boxes']==1,'Unresolved chapter reference')
        keep=[i for i in audio['chap'] if i in ids]
        expected[index]=drop_chapter_references(boxes(expected[index])[0],keep)
        audio['chap']=keep
        repairs.append({'kind':REPAIR_DANGLING_CHAPTER,'track_id':audio['id'],'removed':dangling,'kept':keep,
            'repaired_trak_sha256':hashlib.sha256(expected[index]).hexdigest(),
            'description':'The chapter list pointed to missing track '+', '.join(map(str,dangling))+'. That pointer was removed; audio and chapters are unchanged.'})
    if expected!=[b.raw for b in track_boxes]:
        rebuilt=iter(expected);payload=b''.join(next(rebuilt) if b.kind==b'trak' else b.raw for b in parts)
        output_movie=Box(movie.kind,movie.start,movie.header+len(payload),movie.header,build(movie.kind,payload,movie.header==16))
    referenced=set(audio['chap']);need(referenced<=set(ids)-{audio['id']},'Unresolved chapter reference')
    need(all(t['handler']==b'soun' or t['id'] in referenced for t in tracks),'Unreferenced chapter/video track')
    spans=sorted(span for t in tracks for span in t['spans'])
    need(all(left[1]<=right[0] for left,right in zip(spans,spans[1:])),'Overlapping sample payload')
    appended,dropped=rewrite_metadata(output_movie,tags,cover)
    # The entire trak bytes, not rounded timestamps, establish preservation; a repaired
    # chapter reference is the only permitted difference and was rebuilt exactly above.
    need([b.raw for b in boxes(appended[16:] if appended[:4]==b'\0\0\0\1' else appended[8:]) if b.kind==b'trak']==expected,'Track bytes changed')
    return Plan(source_size,movie.start,movie.size,hashlib.sha256(movie.raw).hexdigest(),appended,
        tuple({k:v for k,v in t.items() if k not in ('spans','chap_boxes','cut')} for t in tracks),tuple(extents),padding,tuple(repairs),media,patches,tuple(dropped),tuple(profile_notes))

def _patches(source_plan):
    """In-place header edits: the old moov's type becomes free, plus approved repair size fields."""
    return ((source_plan.movie_offset+4,b'free'),)+tuple(source_plan.header_patches)

def _patched(block,offset,patches):
    for at,data in patches:
        start=max(offset,at);end=min(offset+len(block),at+len(data))
        if start<end:block=block[:start-offset]+data[start-at:end-at]+block[end-offset:]
    return block

def stream_candidate(source_plan,read_at,write,stopped=lambda:False):
    """Copy to caller-owned private sink. No source writes or path operations."""
    source_hash=hashlib.sha256();candidate_hash=hashlib.sha256();offset=0;patches=_patches(source_plan)
    while offset<source_plan.source_size:
        if stopped():raise InterruptedError('Metadata preservation paused; source unchanged')
        count=min(1024*1024,source_plan.source_size-offset);block=read_at(offset,count)
        need(isinstance(block,bytes) and len(block)==count,'Short immutable stream read');source_hash.update(block)
        block=_patched(block,offset,patches)
        write(block);candidate_hash.update(block);offset+=count
    if stopped():raise InterruptedError('Metadata preservation paused; source unchanged')
    if source_plan.tail_padding:
        pad=bytes(source_plan.tail_padding);write(pad);candidate_hash.update(pad)
    if source_plan.appended_media:write(source_plan.appended_media);candidate_hash.update(source_plan.appended_media)
    write(source_plan.appended_movie);candidate_hash.update(source_plan.appended_movie)
    return receipt(source_plan,source_hash.hexdigest(),candidate_hash.hexdigest())

def receipt(source_plan,source_sha256,sha256):
    """The preservation receipt for these exact bytes; shared by the staged candidate and the 0.21.0 in-place edit."""
    receipt={'schema':'m4b-metadata-preservation-v1','source_sha256':source_sha256,'sha256':sha256,'size':source_plan.source_size+source_plan.tail_padding+len(source_plan.appended_media)+len(source_plan.appended_movie),'old_moov_offset':source_plan.movie_offset,'old_moov_size':source_plan.movie_size,'old_moov_sha256':source_plan.movie_sha256,'appended_moov_sha256':hashlib.sha256(source_plan.appended_movie).hexdigest(),'track_sha256':[t['sha256'] for t in source_plan.tracks],'source_offsets_preserved':True,'fast_start_preserved':False,'pcm_verified':False}
    if source_plan.profile_notes:receipt['source_profile_notes']=[dict(r) for r in source_plan.profile_notes]
    if source_plan.repairs:receipt.update(tail_padding=source_plan.tail_padding,repairs=[dict(r) for r in source_plan.repairs],
        appended_media_sha256=hashlib.sha256(source_plan.appended_media).hexdigest() if source_plan.appended_media else None)
    # Blank metadata the plan dropped (clean_items): kept in the job's validation with this receipt.
    if source_plan.metadata_dropped:receipt['metadata_dropped']=[dict(r) for r in source_plan.metadata_dropped]
    return receipt

def verify_candidate(source_plan, source_read, candidate_size, candidate_read, stopped=lambda:False):
    """Independently reread both immutable streams; permit only the planned patch.

    This proves *all* retained bytes, including unknown mdat padding, rather than
    trusting a successful writer or comparing only selected audio packets.
    """
    need(candidate_size==source_plan.source_size+source_plan.tail_padding+len(source_plan.appended_media)+len(source_plan.appended_movie),'Candidate extent changed')
    offset=0;source_hash=hashlib.sha256();output_hash=hashlib.sha256()
    patches=_patches(source_plan)
    while offset<source_plan.source_size:
        if stopped():raise InterruptedError('Preservation verification paused')
        count=min(1024*1024,source_plan.source_size-offset)
        original=source_read(offset,count);actual=candidate_read(offset,count)
        need(isinstance(original,bytes) and isinstance(actual,bytes) and len(original)==count and len(actual)==count,'Short verification read')
        source_hash.update(original);output_hash.update(actual)
        expected=_patched(original,offset,patches)
        need(actual==expected,'Candidate changed retained source bytes')
        offset+=count
    if source_plan.tail_padding:
        pad=candidate_read(offset,source_plan.tail_padding)
        need(pad==bytes(source_plan.tail_padding),'Candidate tail padding is not exactly zero bytes')
        output_hash.update(pad);offset+=source_plan.tail_padding
    if source_plan.appended_media:
        media=candidate_read(offset,len(source_plan.appended_media))
        need(media==source_plan.appended_media,'Candidate silent frames differ from approved plan')
        output_hash.update(media);offset+=len(media)
    appended=candidate_read(offset,len(source_plan.appended_movie))
    need(appended==source_plan.appended_movie,'Candidate metadata differs from approved plan')
    output_hash.update(appended)
    return {'source_sha256':source_hash.hexdigest(),'sha256':output_hash.hexdigest(),'size':candidate_size,'all_retained_bytes_verified':True}
