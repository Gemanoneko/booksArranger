"""Pure structural M4B preservation fixtures; opaque packets do not prove decoding."""
import hashlib
import struct
import unittest
from m4b_preservation import Refused,boxes,build,plan,stream_candidate,verify_candidate

def atom(kind,payload):return struct.pack('>I4s',8+len(payload),kind)+payload

def fixture(wide=False, composition=False):
    def table(kind, values):
        return atom(kind, b'\0' * 4 + struct.pack('>I', len(values)) + b''.join(values))

    mvhd = bytearray(100)
    struct.pack_into('>II', mvhd, 12, 600, 36)
    tkhd = bytearray(84)
    tkhd[:4] = b'\0\0\0\3'
    struct.pack_into('>I', tkhd, 12, 1)
    struct.pack_into('>I', tkhd, 20, 36)
    mdhd = bytearray(24)
    struct.pack_into('>II', mdhd, 12, 44100, 3072)
    edits = table(b'elst', [struct.pack('>Iihh', 6, -1, 1, 0), struct.pack('>Iihh', 30, 128, 1, 0)])
    handler = atom(b'hdlr', b'\0' * 8 + b'soun' + b'\0' * 12)
    metadata = atom(b'udta', atom(b'meta', b'\0' * 4 +
                    atom(b'hdlr', b'\0' * 8 + b'mdir' + b'\0' * 12) +
                    atom(b'ilst', atom(b'sonm', atom(b'data', b'\0\0\0\1' + b'\0' * 4 + b'old')))))
    entry = b'\0' * 6 + b'\0\1' + b'\0' * 8 + struct.pack('>HHHHI', 2, 16, 0, 0, 44100 << 16)
    stsd = table(b'stsd', [atom(b'mp4a', entry + atom(b'esds', b'\0' * 4 + b'opaque-descriptor'))])
    stts = table(b'stts', [struct.pack('>II', 3, 1024)])
    ctts = table(b'ctts', [struct.pack('>II', 3, 7)]) if composition else b''
    stsc = table(b'stsc', [struct.pack('>III', 1, 1, 1)])
    stsz = atom(b'stsz', b'\0' * 4 + struct.pack('>II', 0, 3) + struct.pack('>III', 3, 4, 5))
    dinf = atom(b'dinf', table(b'dref', [atom(b'url ', b'\0\0\0\1')]))
    ftyp = atom(b'ftyp', b'M4A ' + b'\0' * 4 + b'isom')

    def movie(offsets):
        chunks = table(b'co64' if wide else b'stco', [v.to_bytes(8 if wide else 4, 'big') for v in offsets])
        stbl = atom(b'stbl', stsd + stts + ctts + stsc + stsz + chunks)
        minf = atom(b'minf', atom(b'smhd', b'\0' * 8) + dinf + stbl)
        mdia = atom(b'mdia', atom(b'mdhd', bytes(mdhd)) + handler + minf)
        trak = atom(b'trak', atom(b'tkhd', bytes(tkhd)) + atom(b'edts', edits) + mdia)
        return atom(b'moov', atom(b'mvhd', bytes(mvhd)) + trak + metadata)

    moov = movie([0, 0, 0])
    start = len(ftyp) + len(moov) + 8
    return ftyp + movie([start, start + 3, start + 7]) + atom(b'mdat', b'abcDEFG12345')


def unpack(source):
    items=boxes(source)
    return {b.kind:b for b in items}

def nested(data,kind,replacement):
    return b''.join(build(b.kind,replacement(b.payload)) if b.kind==kind else b.raw for b in boxes(data))

def relocate(data,delta):
    result=[]
    for box in boxes(data):
        if box.kind in (b'moov',b'trak',b'mdia',b'minf',b'stbl'):
            result.append(build(box.kind,relocate(box.payload,delta)))
        elif box.kind in (b'stco',b'co64'):
            width=4 if box.kind==b'stco' else 8;p=box.payload
            result.append(build(box.kind,p[:8]+b''.join((int.from_bytes(p[a:a+width],'big')+delta).to_bytes(width,'big') for a in range(8,len(p),width))))
        else:result.append(box.raw)
    return b''.join(result)

def change_movie(source,function):
    top=unpack(source);old=top[b'moov'];movie=build(b'moov',function(old.payload))
    delta=len(movie)-len(old.raw);movie=relocate(movie,delta)
    return top[b'ftyp'].raw+movie+top[b'mdat'].raw

def add_chapter_graph(source,video=True,bad_field=False):
    top=unpack(source);movie=top[b'moov'];audio=next(b for b in boxes(movie.payload) if b.kind==b'trak')
    text_payload=b'chapter';video_payload=b'opaque-jpeg'
    def table(kind,rows):return atom(kind,bytes(4)+struct.pack('>I',len(rows))+b''.join(rows))
    def track(identity,handler,entry,media,scale,duration,offset):
        tkhd=bytearray(84);tkhd[:4]=b'\0\0\0\3';struct.pack_into('>I',tkhd,12,identity);struct.pack_into('>I',tkhd,20,36)
        mdhd=bytearray(24);struct.pack_into('>II',mdhd,12,scale,duration)
        stbl=atom(b'stbl',table(b'stsd',[entry])+table(b'stts',[struct.pack('>II',1,duration)])+table(b'stsc',[struct.pack('>III',1,1,1)])+atom(b'stsz',bytes(4)+struct.pack('>II',len(media),1))+table(b'stco',[struct.pack('>I',offset)]))
        dinf=atom(b'dinf',table(b'dref',[atom(b'url ',b'\0\0\0\1')]))
        minf=atom(b'minf',atom(b'nmhd',bytes(4))+dinf+stbl)
        return atom(b'trak',atom(b'tkhd',bytes(tkhd))+atom(b'mdia',atom(b'mdhd',bytes(mdhd))+atom(b'hdlr',bytes(8)+handler+bytes(12))+minf))
    text_entry=atom(b'text',bytes(6)+b'\0\1'+bytes(43))
    image_entry=atom(b'mjpg',bytes(6)+b'\0\1'+bytes(70)+atom(b'fiel',b'\2\0' if bad_field else b'\1\0'))
    refs=struct.pack('>II',3,2) if video else struct.pack('>I',3)
    linked=build(b'trak',audio.payload+atom(b'tref',atom(b'chap',refs)))
    def movie_at(offset):
        chapters=track(3,b'text',text_entry,text_payload,1000,60,offset)
        if video:chapters+=track(2,b'vide',image_entry,video_payload,44100,3072,offset+len(text_payload))
        return build(b'moov',b''.join(linked if b.kind==b'trak' else b.raw for b in boxes(movie.payload))+chapters)
    tentative=movie_at(0);delta=len(tentative)-len(movie.raw)
    data_offset=len(top[b'ftyp'].raw)+len(tentative)+8
    output_movie=relocate(movie_at(data_offset+len(top[b'mdat'].payload)),delta)
    # relocate only the original audio track; chapter offsets were computed new.
    chunks=boxes(output_movie[8:]);correct=[]
    fresh=boxes(movie_at(data_offset+len(top[b'mdat'].payload))[8:]);fresh_by={b.payload[12:16]:b for b in fresh if b.kind==b'trak'}
    for b in chunks:
        if b.kind==b'trak':
            tk=next(x for x in boxes(b.payload) if x.kind==b'tkhd');identity=int.from_bytes(tk.payload[12:16],'big')
            if identity!=1:
                b=next(x for x in fresh if x.kind==b'trak' and int.from_bytes(next(z for z in boxes(x.payload) if z.kind==b'tkhd').payload[12:16],'big')==identity)
        correct.append(b.raw)
    return top[b'ftyp'].raw+build(b'moov',b''.join(correct))+atom(b'mdat',top[b'mdat'].payload+text_payload+(video_payload if video else b''))

class M4BPreservationTests(unittest.TestCase):
    def transform(self,source,tags=None,cover=None):
        read=lambda at,count:source[at:at+count]
        p=plan(len(source),read,tags or {'title':'Approved title'},cover)
        output=[];receipt=stream_candidate(p,read,output.append)
        candidate=b''.join(output)
        self.assertEqual(receipt['source_sha256'],hashlib.sha256(source).hexdigest())
        self.assertEqual(receipt['sha256'],hashlib.sha256(candidate).hexdigest())
        expected=source[:p.movie_offset+4]+b'free'+source[p.movie_offset+8:]+p.appended_movie
        self.assertEqual(candidate,expected)
        old_tracks=[b.raw for b in boxes(unpack(source)[b'moov'].payload) if b.kind==b'trak']
        new_tracks=[b.raw for b in boxes(unpack(candidate)[b'moov'].payload) if b.kind==b'trak']
        self.assertEqual(new_tracks,old_tracks)
        self.assertFalse(receipt['pcm_verified']);self.assertFalse(receipt['fast_start_preserved'])
        return p,candidate,receipt
    def refuse(self,source):
        with self.assertRaises(Refused):plan(len(source),lambda a,n:source[a:a+n],{'title':'Approved'})
    def test_non1000_clock_and_nonzero_empty_edits_remain_byte_exact(self):self.transform(fixture())
    def test_unicode_tag_growth_and_shrink_do_not_move_original_offsets(self):
        for title in ('x','Unicode Книга'*20):self.transform(fixture(),{'title':title})
    def test_co64_and_signed_composition_table_preserved(self):self.transform(fixture(wide=True,composition=True))
    def test_quicktime_text_and_chapter_thumbnail_reference_graph_preserved(self):
        p,_,_=self.transform(add_chapter_graph(fixture()))
        self.assertEqual(p.tracks[0]['chap'],[3,2]);self.assertEqual(len(p.tracks),3)
    def test_text_only_chapter_graph_preserved(self):self.transform(add_chapter_graph(fixture(),video=False))
    def test_unapproved_gapless_freeform_and_legacy_chpl_preserved(self):
        gapless=atom(b'----',atom(b'mean',bytes(4)+b'com.apple.iTunes')+atom(b'name',bytes(4)+b'iTunSMPB')+atom(b'data',bytes(8)+b'opaque-gapless'))
        source=change_movie(fixture(),lambda p:nested(p,b'udta',lambda u:nested(u,b'meta',lambda m:m[:4]+nested(m[4:],b'ilst',lambda i:i+gapless))+atom(b'chpl',b'opaque-original-chapters')))
        _,candidate,_=self.transform(source)
        self.assertIn(gapless,unpack(candidate)[b'moov'].raw);self.assertIn(atom(b'chpl',b'opaque-original-chapters'),unpack(candidate)[b'moov'].raw)
    def test_approved_artwork_changes_only_covr_metadata(self):
        self.transform(fixture(),cover=b'\x89PNG\r\n\x1a\nopaque-structural-only')
    def test_external_data_reference_refused(self):self.refuse(fixture().replace(b'url \0\0\0\1',b'url \0\0\0\0',1))
    def test_fragment_and_unknown_top_level_offset_box_refused(self):
        self.refuse(fixture()+atom(b'moof',b''));self.refuse(fixture()+atom(b'sidx',bytes(20)))
    def test_duplicate_movie_and_eof_size_refused(self):
        self.refuse(fixture()+unpack(fixture())[b'moov'].raw)
        self.refuse(bytes(4)+fixture()[4:])
    def test_auxiliary_offsets_refused(self):
        source=change_movie(fixture(),lambda p:nested(p,b'trak',lambda t:nested(t,b'mdia',lambda m:nested(m,b'minf',lambda n:nested(n,b'stbl',lambda s:s+atom(b'saio',bytes(12)))))))
        self.refuse(source)
    def test_outside_mdat_chunk_refused(self):
        source=bytearray(fixture());at=source.index(b'stco')+12;struct.pack_into('>I',source,at,0);self.refuse(bytes(source))
    def test_overlapping_chunks_refused(self):
        source=bytearray(fixture());at=source.index(b'stco')+12;struct.pack_into('>I',source,at+4,struct.unpack_from('>I',source,at)[0]);self.refuse(bytes(source))
    def test_changed_decode_duration_refused(self):
        source=bytearray(fixture());at=source.index(b'stts')+16;struct.pack_into('>I',source,at,1025);self.refuse(bytes(source))
    def test_unknown_chapter_image_extension_refused(self):self.refuse(add_chapter_graph(fixture(),bad_field=True))
    def test_unreferenced_chapter_video_refused(self):
        source=add_chapter_graph(fixture()).replace(b'chap'+struct.pack('>II',3,2),b'chap'+struct.pack('>II',3,3),1);self.refuse(source)
    def test_duplicate_approved_tag_refused(self):
        item=atom(b'\xa9nam',atom(b'data',bytes((0,0,0,1))+bytes(4)+b'old'))
        source=change_movie(fixture(),lambda p:nested(p,b'udta',lambda u:nested(u,b'meta',lambda m:m[:4]+nested(m[4:],b'ilst',lambda i:i+item+item))))
        self.refuse(source)
    def test_invalid_or_oversized_approval_refused(self):
        for tags in ({'unknown':'x'},{'title':'x'*65537},{'media_type':'1'}):
            source=fixture()
            with self.assertRaises(Refused):plan(len(source),lambda a,n:source[a:a+n],tags)
    def test_cancellation_does_not_modify_source(self):
        source=fixture();p=plan(len(source),lambda a,n:source[a:a+n],{'title':'x'});sink=[]
        with self.assertRaises(InterruptedError):stream_candidate(p,lambda a,n:source[a:a+n],sink.append,lambda:True)
        self.assertEqual(sink,[]);self.assertEqual(source,fixture())
    def test_short_read_refused(self):
        source=fixture()
        with self.assertRaises(Refused):plan(len(source),lambda a,n:source[a:a+n-1],{'title':'x'})
    def test_independent_reread_checks_all_retained_bytes(self):
        source=fixture();p,candidate,receipt=self.transform(source)
        actual=verify_candidate(p,lambda a,n:source[a:a+n],len(candidate),lambda a,n:candidate[a:a+n])
        self.assertEqual(actual['sha256'],receipt['sha256']);self.assertTrue(actual['all_retained_bytes_verified'])
    def test_reread_rejects_corrupt_audio_metadata_padding_and_extent(self):
        source=fixture();p,candidate,_=self.transform(source)
        for at in (0,p.movie_offset+4,len(source)-1,len(source)+8):
            broken=bytearray(candidate);broken[at]^=1
            with self.assertRaises(Refused):verify_candidate(p,lambda a,n:source[a:a+n],len(broken),lambda a,n:bytes(broken[a:a+n]))
        with self.assertRaises(Refused):verify_candidate(p,lambda a,n:source[a:a+n],len(candidate)+1,lambda a,n:candidate[a:a+n])
    def test_reread_rejects_partial_writer_and_cancellation(self):
        source=fixture();p,candidate,_=self.transform(source)
        with self.assertRaises(Refused):verify_candidate(p,lambda a,n:source[a:a+n],len(candidate),lambda a,n:candidate[a:a+n-1])
        with self.assertRaises(InterruptedError):verify_candidate(p,lambda a,n:source[a:a+n],len(candidate),lambda a,n:candidate[a:a+n],lambda:True)
    def roll_fixture(self,description=None,mapping=None):
        description=bytes.fromhex('01000000726f6c6c0000000200000001ffff') if description is None else description
        mapping=bytes.fromhex('00000000726f6c6c000000010000000300000001') if mapping is None else mapping
        return change_movie(fixture(),lambda p:nested(p,b'trak',lambda t:nested(t,b'mdia',lambda m:nested(m,b'minf',lambda n:nested(n,b'stbl',lambda s:s+atom(b'sgpd',description)+atom(b'sbgp',mapping))))))
    def test_exact_aac_roll_preroll_groups_preserved(self):self.transform(self.roll_fixture())
    def test_unknown_roll_group_type_count_distance_and_reference_refused(self):
        for description in (bytes.fromhex('01000000726f6c6c0000000200000001fffe'),bytes.fromhex('0100000070726f6c0000000200000001ffff')):
            self.refuse(self.roll_fixture(description=description))
        for mapping in (bytes.fromhex('00000000726f6c6c000000010000000200000001'),bytes.fromhex('00000000726f6c6c000000010000000300000002')):
            self.refuse(self.roll_fixture(mapping=mapping))
    def test_empty_wide_placeholder_before_mdat_preserves_all_original_offsets(self):
        top=unpack(fixture())
        source=top[b'ftyp'].raw+relocate(top[b'moov'].raw,8)+atom(b'wide',b'')+top[b'mdat'].raw
        self.transform(source)
    def test_wide_payload_extended_header_and_wrong_successor_refused(self):
        for wide in (atom(b'wide',b'x'),build(b'wide',b'',extended=True)):
            top=unpack(fixture());source=top[b'ftyp'].raw+relocate(top[b'moov'].raw,len(wide))+wide+top[b'mdat'].raw
            with self.assertRaisesRegex(Refused,'wide placeholder extent'):plan(len(source),lambda a,n:source[a:a+n],{'title':'x'})
        self.refuse(fixture()+atom(b'wide',b''))
    def test_metadata_free_reservation_is_retained_byte_exact(self):
        reservation=atom(b'free',b'original reserved metadata bytes'*23)
        source=change_movie(fixture(),lambda p:nested(p,b'udta',lambda u:nested(u,b'meta',lambda m:m+reservation)))
        _,candidate,_=self.transform(source)
        self.assertIn(reservation,unpack(candidate)[b'moov'].raw)
    def test_unknown_metadata_structural_box_remains_refused(self):
        source=change_movie(fixture(),lambda p:nested(p,b'udta',lambda u:nested(u,b'meta',lambda m:m+atom(b'saio',bytes(12)))))
        self.refuse(source)


# Writer-family allowances (exact observed shapes) and explicit damage repair.
def handler_of(box):
    mdia=next(x for x in boxes(box.payload) if x.kind==b'mdia')
    return next(x for x in boxes(mdia.payload) if x.kind==b'hdlr').payload[8:12]

def edit(data,path,function,where=lambda box:True):
    """Rebuild the box at path (first level filtered by where); offsets are fixed by change_movie."""
    return b''.join(build(b.kind,function(b.payload) if len(path)==1 else edit(b.payload,path[1:],function)) if b.kind==path[0] and where(b) else b.raw for b in boxes(data))

is_text=lambda box:handler_of(box)==b'text'
is_audio=lambda box:handler_of(box)==b'soun'
STSD_PATH=[b'trak',b'mdia',b'minf',b'stbl',b'stsd']
DREF_PATH=[b'trak',b'mdia',b'minf',b'dinf',b'dref']

def with_ftyp(source,payload):
    top=unpack(source);ftyp=atom(b'ftyp',payload)
    return ftyp+relocate(top[b'moov'].raw,len(ftyp)-len(top[b'ftyp'].raw))+top[b'mdat'].raw

def text_entry(source,payload):
    return change_movie(source,lambda p:edit(p,STSD_PATH,lambda s:s[:8]+atom(b'text',payload),where=is_text))

def chunked(count,extra_row=False,variable=False,per_chunk=1):
    """One-byte samples, one chunk each, one stsc row per chunk (QuickTime 7 shape); or, with
    per_chunk>1, one compact row and `per_chunk` samples per chunk."""
    def table(kind,rows):return atom(kind,bytes(4)+struct.pack('>I',len(rows))+b''.join(rows))
    mvhd=bytearray(100);struct.pack_into('>II',mvhd,12,44100,count*1024)
    tkhd=bytearray(84);tkhd[:4]=b'\0\0\0\3';struct.pack_into('>I',tkhd,12,1);struct.pack_into('>I',tkhd,20,count*1024)
    mdhd=bytearray(24);struct.pack_into('>II',mdhd,12,44100,count*1024)
    entry=bytes(6)+b'\0\1'+bytes(8)+struct.pack('>HHHHI',2,16,0,0,44100<<16)
    stsd=table(b'stsd',[atom(b'mp4a',entry+atom(b'esds',bytes(4)+b'opaque-descriptor'))])
    chunks=count//per_chunk
    rows=([struct.pack('>III',i+1,1,1) for i in range(count)] if per_chunk==1 else [struct.pack('>III',1,per_chunk,1)])+([struct.pack('>III',chunks+1,1,1)] if extra_row else [])
    sizes=atom(b'stsz',bytes(4)+struct.pack('>II',0,count)+struct.pack('>I',1)*count) if variable else atom(b'stsz',bytes(4)+struct.pack('>II',1,count))
    def movie(base):
        stbl=atom(b'stbl',stsd+table(b'stts',[struct.pack('>II',count,1024)])+table(b'stsc',rows)+sizes+table(b'stco',[struct.pack('>I',base+i*per_chunk) for i in range(chunks)]))
        minf=atom(b'minf',atom(b'smhd',bytes(8))+atom(b'dinf',table(b'dref',[atom(b'url ',b'\0\0\0\1')]))+stbl)
        trak=atom(b'trak',atom(b'tkhd',bytes(tkhd))+atom(b'mdia',atom(b'mdhd',bytes(mdhd))+atom(b'hdlr',bytes(8)+b'soun'+bytes(12))+minf))
        return atom(b'moov',atom(b'mvhd',bytes(mvhd))+trak)
    ftyp=atom(b'ftyp',b'M4A '+bytes(4)+b'isom')
    return ftyp+movie(len(ftyp)+len(movie(0))+8)+atom(b'mdat',bytes(count))

def dangling(source,refs):
    return change_movie(source,lambda p:edit(p,[b'trak',b'tref',b'chap'],lambda c:b''.join(struct.pack('>I',i) for i in refs),where=is_audio))

def overrun(source,missing):
    """Declare `missing` more mdat bytes than the file holds (the final box is mdat)."""
    top=unpack(source);mdat=top[b'mdat'];data=bytearray(source)
    struct.pack_into('>I',data,len(source)-mdat.size,mdat.size+missing);return bytes(data)

TEXT_SOURCE=lambda:add_chapter_graph(fixture(),video=False)

class WriterFamilyAllowanceTests(unittest.TestCase):
    """Each allowance accepts one observed writer shape; the neighbouring shapes stay refused."""
    transform=M4BPreservationTests.transform;refuse=M4BPreservationTests.refuse
    def test_itunes_zero_compatible_brand_preserved(self):
        self.transform(with_ftyp(fixture(),b'M4B '+bytes(4)+b'M4B mp42isom'+bytes(4)))
    def test_zero_major_or_unknown_brand_beside_zero_slot_refused(self):
        self.refuse(with_ftyp(fixture(),bytes(8)+b'isom'))
        self.refuse(with_ftyp(fixture(),b'M4B '+bytes(4)+b'M4B 3gp5'+bytes(4)))
    def test_chapter_and_verse_exact_ftyp_preserved(self):
        self.transform(with_ftyp(fixture(),b'M4A\0'+bytes(4)+b'3gp5isom'))
    def test_chapter_and_verse_neighbouring_ftyps_refused(self):
        for payload in (b'M4A '+bytes(4)+b'3gp5isom',b'M4A\0'+bytes(4)+b'isom',b'M4A\0'+bytes(4)+b'3gp5isommp42'):
            self.refuse(with_ftyp(fixture(),payload))
    def test_quicktime_self_alias_on_chapter_text_preserved(self):
        source=change_movie(TEXT_SOURCE(),lambda p:edit(p,DREF_PATH,lambda d:d[:8]+atom(b'alis',b'\0\0\0\1'),where=is_text))
        p,_,_=self.transform(source);self.assertEqual([t['handler'] for t in p.tracks],[b'soun',b'text'])
    def test_alias_on_audio_or_alias_not_self_refused(self):
        self.refuse(fixture().replace(b'url \0\0\0\1',b'alis\0\0\0\1',1))
        self.refuse(change_movie(TEXT_SOURCE(),lambda p:edit(p,DREF_PATH,lambda d:d[:8]+atom(b'alis',b'\0\0\0\0'),where=is_text)))
        self.refuse(change_movie(TEXT_SOURCE(),lambda p:edit(p,DREF_PATH,lambda d:d[:8]+atom(b'alis',b'\0\0\0\1opaque-alias-record'),where=is_text)))
    def test_chapter_text_entry_index_zero_preserved(self):
        self.transform(text_entry(TEXT_SOURCE(),bytes(8)+bytes(43)))
    def test_audio_entry_index_zero_refused(self):
        self.refuse(fixture().replace(b'mp4a'+bytes(6)+b'\0\1',b'mp4a'+bytes(8),1))
    def test_quicktime_52_byte_text_entry_with_empty_name_preserved(self):
        self.transform(text_entry(TEXT_SOURCE(),bytes(6)+b'\0\1'+bytes(44)))
    def test_other_text_entry_lengths_refused(self):
        self.refuse(text_entry(TEXT_SOURCE(),bytes(6)+b'\0\1'+bytes(43)+b'\1'))
        self.refuse(text_entry(TEXT_SOURCE(),bytes(6)+b'\0\1'+bytes(45)))
    def test_free_and_skip_inside_track_preserved_byte_exact(self):
        for kind in (b'free',b'skip'):
            padding=atom(kind,b'\0\1\0\0\0\x4a\x9e\xa2')
            source=change_movie(fixture(),lambda p:edit(p,[b'trak'],lambda t:t+padding))
            _,candidate,_=self.transform(source);self.assertIn(padding,unpack(candidate)[b'moov'].raw)
    def test_free_deeper_than_track_still_refused(self):
        self.refuse(change_movie(fixture(),lambda p:edit(p,[b'trak',b'mdia'],lambda m:m+atom(b'free',bytes(4)))))
    def test_chunk_map_rows_bounded_by_chunk_count_not_4096(self):
        p,_,_=self.transform(chunked(5000));self.assertEqual(p.tracks[0]['samples'],5000)
    def test_chunk_map_rows_beyond_chunk_count_refused(self):self.refuse(chunked(5000,extra_row=True))
    def test_chunk_cap_is_an_exact_bound_and_covers_the_largest_library_book(self):
        import m4b_preservation
        self.assertEqual(m4b_preservation.MAX_CHUNKS,524288);self.assertGreater(m4b_preservation.MAX_CHUNKS,322966)
        original=m4b_preservation.MAX_CHUNKS;source=chunked(5000)
        try:
            m4b_preservation.MAX_CHUNKS=5000;self.transform(source)
            m4b_preservation.MAX_CHUNKS=4999;self.refuse(source)
        finally:m4b_preservation.MAX_CHUNKS=original
    def test_nero_tag_store_retained_verbatim(self):
        nero=atom(b'tags',atom(b'meta',b'opaque-nero-values')+atom(b'cvrx',b'opaque-cover')+atom(b'tseg',atom(b'tshd',bytes(4))+b'chapter-1')+atom(b'tseg',atom(b'tshd',b'\0\0\0\1')+b'chapter-2'))
        source=change_movie(fixture(),lambda p:nested(p,b'udta',lambda u:u+nero))
        _,candidate,_=self.transform(source);self.assertIn(nero,unpack(candidate)[b'moov'].raw)
    def test_unknown_nero_child_or_user_data_box_refused(self):
        self.refuse(change_movie(fixture(),lambda p:nested(p,b'udta',lambda u:u+atom(b'tags',atom(b'saio',bytes(12))))))
        self.refuse(change_movie(fixture(),lambda p:nested(p,b'udta',lambda u:u+atom(b'XTRA',bytes(12)))))


class DamageRepairTests(unittest.TestCase):
    """Repair runs only for kinds the caller names, and only for the exact damage shape."""
    def plan_for(self,source,repair=frozenset()):
        return plan(len(source),lambda a,n:source[a:a+n],{'title':'Approved'},None,repair)
    def produce(self,source,repair):
        p=self.plan_for(source,repair);read=lambda a,n:source[a:a+n];sink=[]
        receipt=stream_candidate(p,read,sink.append);candidate=b''.join(sink)
        verified=verify_candidate(p,read,len(candidate),lambda a,n:candidate[a:a+n])
        self.assertEqual(verified['sha256'],receipt['sha256']);self.assertEqual(receipt['size'],len(candidate))
        self.assertEqual(receipt['repairs'],[dict(r) for r in p.repairs])
        return p,candidate
    def test_dangling_chapter_reference_refused_unless_requested(self):
        source=dangling(TEXT_SOURCE(),[3,2])
        for repair in (frozenset(),{'mdat_tail_overrun'}):
            with self.assertRaisesRegex(Refused,'Unresolved chapter reference'):self.plan_for(source,repair)
    def test_dangling_chapter_reference_dropped_rest_of_track_byte_exact(self):
        source=dangling(TEXT_SOURCE(),[3,2]);p,candidate=self.produce(source,{'dangling_chapter_reference'})
        self.assertEqual([(r['kind'],r['removed'],r['kept']) for r in p.repairs],[('dangling_chapter_reference',[2],[3])])
        old=[b for b in boxes(unpack(source)[b'moov'].payload) if b.kind==b'trak']
        new=[b for b in boxes(unpack(candidate)[b'moov'].payload) if b.kind==b'trak']
        self.assertEqual(new[1].raw,old[1].raw)
        self.assertEqual([b.raw for b in boxes(new[0].payload) if b.kind!=b'tref'],[b.raw for b in boxes(old[0].payload) if b.kind!=b'tref'])
        tref=next(b for b in boxes(new[0].payload) if b.kind==b'tref')
        self.assertEqual(tref.raw,atom(b'tref',atom(b'chap',struct.pack('>I',3))))
        self.assertEqual(candidate[:len(source)],source[:p.movie_offset+4]+b'free'+source[p.movie_offset+8:])
    def test_all_dangling_references_drop_the_reference_box(self):
        source=change_movie(fixture(),lambda p:edit(p,[b'trak'],lambda t:t+atom(b'tref',atom(b'chap',struct.pack('>I',5)))))
        _,candidate=self.produce(source,{'dangling_chapter_reference'})
        new=next(b for b in boxes(unpack(candidate)[b'moov'].payload) if b.kind==b'trak')
        old=next(b for b in boxes(unpack(source)[b'moov'].payload) if b.kind==b'trak')
        self.assertEqual([b.raw for b in boxes(new.payload)],[b.raw for b in boxes(old.payload) if b.kind!=b'tref'])
    def test_self_reference_or_split_chapter_boxes_stay_refused_in_repair(self):
        repair={'dangling_chapter_reference'}
        for refs in ([3,1],[1,9]):
            with self.assertRaises(Refused):self.plan_for(dangling(TEXT_SOURCE(),refs),repair)
        split=change_movie(TEXT_SOURCE(),lambda p:edit(p,[b'trak',b'tref'],lambda t:t+atom(b'chap',struct.pack('>I',2)),where=is_audio))
        with self.assertRaises(Refused):self.plan_for(split,repair)
    def test_mdat_tail_overrun_refused_unless_requested(self):
        source=overrun(fixture(),8)
        for repair in (frozenset(),{'dangling_chapter_reference'}):
            with self.assertRaisesRegex(Refused,'Top-level extent invalid'):self.plan_for(source,repair)
    def test_mdat_tail_overrun_completed_with_zero_bytes_all_original_bytes_kept(self):
        source=overrun(fixture(),8);p,candidate=self.produce(source,{'mdat_tail_overrun'})
        self.assertEqual(p.tail_padding,8);self.assertEqual(p.repairs[0]['padding'],8)
        self.assertEqual(candidate,source[:p.movie_offset+4]+b'free'+source[p.movie_offset+8:]+bytes(8)+p.appended_movie)
        self.assertEqual([b.kind for b in boxes(candidate)],[b'ftyp',b'free',b'mdat',b'moov'])
    def test_verifier_rejects_nonzero_padding_and_missing_padding(self):
        source=overrun(fixture(),8);p,candidate=self.produce(source,{'mdat_tail_overrun'});read=lambda a,n:source[a:a+n]
        broken=bytearray(candidate);broken[len(source)+3]=1
        with self.assertRaisesRegex(Refused,'padding'):verify_candidate(p,read,len(broken),lambda a,n:bytes(broken[a:a+n]))
        short=candidate[:len(source)]+candidate[len(source)+8:]
        with self.assertRaises(Refused):verify_candidate(p,read,len(short),lambda a,n:short[a:a+n])
    def test_overrun_reaching_sample_bytes_or_too_long_or_not_mdat_refused(self):
        repair={'mdat_tail_overrun'}
        with self.assertRaisesRegex(Refused,'Chunk outside retained mdat'):self.plan_for(fixture()[:-1],repair)
        with self.assertRaisesRegex(Refused,'Top-level extent invalid'):self.plan_for(overrun(fixture(),4097),repair)
        with self.assertRaisesRegex(Refused,'Top-level extent invalid'):self.plan_for((fixture()+atom(b'free',bytes(16)))[:-8],repair)
    def test_unknown_repair_kind_refused(self):
        with self.assertRaisesRegex(Refused,'Unknown repair'):self.plan_for(fixture(),{'loosen'})


class RepairAdmissionContractTests(unittest.TestCase):
    """m4b_repair: detection, binding and the approved-equals-applied check."""
    def setUp(self):
        import json,uuid
        self.json=json
        self.manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,
            'sources':[{'path':'unused.m4b','sha256':'a'*64}],'metadata':{'title':'Approved'},'source_chapters':[]}
    def row(self,manifest,reason='Remux changed the decoder configuration or relative audio packet timing'):
        encoded=self.json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        return {'job_id':manifest['job_id'],'state':'needs attention','output':None,'reason':reason,'journal':'{}',
                'manifest':encoded,'manifest_hash':hashlib.sha256(encoded.encode()).hexdigest()}
    def diagnosis(self,source):
        import m4b_repair
        return m4b_repair.diagnose(len(source),lambda a,n:source[a:a+n])
    def test_diagnosis_states(self):
        self.assertEqual(self.diagnosis(fixture())['state'],'intact')
        damaged=self.diagnosis(dangling(TEXT_SOURCE(),[3,2]))
        self.assertEqual(damaged['state'],'repairable');self.assertIn('missing track 2',damaged['damage'][0])
        self.assertEqual(damaged['reason'],'Unresolved chapter reference')
        both=self.diagnosis(overrun(dangling(TEXT_SOURCE(),[3,2]),8))
        self.assertEqual(sorted(r['kind'] for r in both['repairs']),['dangling_chapter_reference','mdat_tail_overrun'])
        refused=self.diagnosis(fixture()[:-1]);self.assertEqual(refused['state'],'refused')
    def test_bind_approve_and_confirm_exact_repair(self):
        import copy,uuid,m4b_repair
        source=dangling(TEXT_SOURCE(),[3,2]);parent=self.row(self.manifest)
        fresh=copy.deepcopy(self.manifest);fresh['job_id']=str(uuid.uuid4())
        child=m4b_repair.bind(parent,fresh,self.diagnosis(source),'b'*64)
        child=self.json.loads(self.json.dumps(child))  # durable manifest round trip
        self.assertEqual(child['m4b_repair']['parent_job_id'],parent['job_id']);self.assertTrue(child['m4b_repair']['user_requested'])
        kinds=m4b_repair.approved_repairs(child);self.assertEqual(kinds,{'dangling_chapter_reference'})
        applied=plan(len(source),lambda a,n:source[a:a+n],{'title':'Approved'},None,kinds)
        self.assertIn('missing track 2',m4b_repair.confirm(child,applied)['note'])
        with self.assertRaisesRegex(Refused,'differs from the approved'):m4b_repair.confirm(child,plan(len(fixture()),lambda a,n:fixture()[a:a+n],{'title':'x'}))
        self.assertFalse(m4b_repair.eligible(self.row(child)))  # no repair of a repair
    def test_ordinary_jobs_have_no_repair_and_bind_refuses_intact_or_changed(self):
        import copy,uuid,m4b_repair
        self.assertEqual(m4b_repair.approved_repairs(self.manifest),frozenset())
        intact=plan(len(fixture()),lambda a,n:fixture()[a:a+n],{'title':'x'})
        self.assertIsNone(m4b_repair.confirm(self.manifest,intact))
        with self.assertRaisesRegex(Refused,'differs from the approved'):m4b_repair.confirm(self.manifest,self.diagnosis_plan())
        parent=self.row(self.manifest);fresh=copy.deepcopy(self.manifest);fresh['job_id']=str(uuid.uuid4())
        with self.assertRaisesRegex(ValueError,'no provable repair'):m4b_repair.bind(parent,fresh,self.diagnosis(fixture()),'b'*64)
        fresh['metadata']={'title':'Changed'}
        with self.assertRaisesRegex(ValueError,'Frozen review'):m4b_repair.bind(parent,fresh,self.diagnosis(dangling(TEXT_SOURCE(),[3,2])),'b'*64)
    def diagnosis_plan(self):
        source=dangling(TEXT_SOURCE(),[3,2])
        return plan(len(source),lambda a,n:source[a:a+n],{'title':'x'},None,{'dangling_chapter_reference'})
    def test_classify_is_cached_and_check_reads_the_source_once(self):
        import tempfile,m4b_repair
        from pathlib import Path
        area=Path(__file__).resolve().parents[1]/'scratch'/'m4b-repair-tests';area.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=area) as folder:
            path=Path(folder)/'damaged.m4b';path.write_bytes(overrun(fixture(),8))
            manifest=dict(self.manifest,sources=[{'path':str(path),'sha256':'a'*64}]);row=self.row(manifest,'M4B preservation requires review: Top-level extent invalid')
            self.assertEqual(m4b_repair.classify(row),{'state':'unchecked'})
            self.assertEqual(m4b_repair.check(row)['state'],'repairable')
            self.assertEqual(m4b_repair.classify(row)['repairs'][0]['padding'],8)
            self.assertIsNone(m4b_repair.classify(dict(row,state='completed')))


# Silence repair for a genuinely cut final audio frame (AAC-LC only, user-approved only).
def aac_esds(channels=1,index=4,kind=2,tail=b''):
    """A real esds: ES / DecoderConfig (MPEG-4 audio) / 2-byte AudioSpecificConfig (+tail)."""
    config=((kind<<11)|(index<<7)|(channels<<3)).to_bytes(2,'big')+tail
    specific=bytes((5,len(config)))+config
    decoder=bytes((4,13+len(specific),0x40,0x15))+bytes(11)+specific
    return bytes(4)+bytes((3,3+len(decoder)+3))+b'\0\1\0'+decoder+bytes((6,1,2))

def with_esds(source,payload):
    entry=bytes(6)+b'\0\1'+bytes(8)+struct.pack('>HHHHI',2,16,0,0,44100<<16)
    return change_movie(source,lambda p:edit(p,STSD_PATH,lambda s:s[:8]+atom(b'mp4a',entry+atom(b'esds',payload)),where=is_audio))

def sample_map(source):
    """Independent per-sample (offset, size) map of the audio track, for comparison only."""
    at=0
    while source[at+4:at+8]!=b'moov':at+=struct.unpack_from('>I',source,at)[0]  # tolerant of a cut final mdat
    movie=boxes(source[at:at+struct.unpack_from('>I',source,at)[0]])[0]
    trak=next(b for b in boxes(movie.payload) if b.kind==b'trak' and is_audio(b))
    stbl={b.kind:b.payload for b in boxes(next(x for x in boxes(next(x for x in boxes(next(x for x in boxes(trak.payload) if x.kind==b'mdia').payload) if x.kind==b'minf').payload) if x.kind==b'stbl').payload)}
    count=struct.unpack_from('>I',stbl[b'stsz'],8)[0];fixed=struct.unpack_from('>I',stbl[b'stsz'],4)[0]
    sizes=[fixed]*count if fixed else list(struct.unpack_from('>%dI'%count,stbl[b'stsz'],12))
    wide=b'co64' in stbl;table=stbl[b'co64' if wide else b'stco'];n=struct.unpack_from('>I',table,4)[0]
    offsets=list(struct.unpack_from(('>%dQ' if wide else '>%dI')%n,table,8))
    rows=[struct.unpack_from('>III',stbl[b'stsc'],8+12*i) for i in range(struct.unpack_from('>I',stbl[b'stsc'],4)[0])]
    result=[];sample=0
    for index,offset in enumerate(offsets):
        per=[r for r in rows if r[0]<=index+1][-1][1]
        for _ in range(per):result.append((offset,sizes[sample]));offset+=sizes[sample];sample+=1
    return result,{k:v for k,v in stbl.items() if k in (b'stsd',b'stts',b'ctts',b'sgpd',b'sbgp')}

SILENCE=frozenset({'truncated_final_frames'})

class SilenceRepairShapeTests(unittest.TestCase):
    plan_for=DamageRepairTests.plan_for;produce=DamageRepairTests.produce
    def test_cut_final_frame_refused_unless_silence_requested(self):
        source=with_esds(fixture(),aac_esds())[:-2]
        with self.assertRaisesRegex(Refused,'Top-level extent invalid'):self.plan_for(source)
        with self.assertRaisesRegex(Refused,'Chunk outside retained mdat'):self.plan_for(source,{'mdat_tail_overrun'})
    def test_cut_final_frame_becomes_silence_and_every_intact_frame_keeps_bytes_offset_and_timing(self):
        import m4b_preservation
        source=with_esds(fixture(),aac_esds())[:-2];p,candidate=self.produce(source,SILENCE)
        record=p.repairs[0]
        self.assertEqual((record['kind'],record['frames'],record['first_frame'],record['padding'],record['replaced_ticks']),('truncated_final_frames',1,2,2,1024))
        silent=m4b_preservation.silent_aac_frame(1);self.assertEqual(silent.hex(),record['silent_frame'])
        self.assertEqual(p.appended_media,atom(b'mdat',silent))
        self.assertEqual(candidate,source[:p.movie_offset+4]+b'free'+source[p.movie_offset+8:]+bytes(2)+p.appended_media+p.appended_movie)
        self.assertEqual([b.kind for b in boxes(candidate)],[b'ftyp',b'free',b'mdat',b'mdat',b'moov'])
        before,tables=sample_map(source);after,tables_after=sample_map(candidate)
        self.assertEqual(after[:2],before[:2]);self.assertEqual(tables_after,tables)
        self.assertEqual(after[2],(len(source)+2+8,len(silent)));self.assertEqual(candidate[after[2][0]:after[2][0]+after[2][1]],silent)
    def test_cut_inside_a_shared_chunk_keeps_the_intact_part_of_that_chunk(self):
        source=with_esds(chunked(10,variable=True,per_chunk=5),aac_esds(2))[:-2];p,candidate=self.produce(source,SILENCE)
        self.assertEqual((p.repairs[0]['first_frame'],p.repairs[0]['frames']),(8,2))
        before,_=sample_map(source);after,_=sample_map(candidate)
        self.assertEqual(after[:8],before[:8])
        self.assertEqual([size for _,size in after[8:]],[7,7]);self.assertTrue(all(offset>len(source) for offset,_ in after[8:]))
    def test_at_most_one_second_is_silenced(self):
        source=with_esds(chunked(100,variable=True),aac_esds())
        self.produce(source[:-43],SILENCE)  # 43 x 1024 / 44100 = 0.9985 s
        with self.assertRaisesRegex(Refused,'more than one second'):self.plan_for(source[:-44],SILENCE)
    def test_cut_chapter_sample_or_too_much_missing_refused(self):
        with self.assertRaisesRegex(Refused,'Truncated chapter samples'):self.plan_for(with_esds(TEXT_SOURCE(),aac_esds())[:-1],SILENCE)
        with self.assertRaisesRegex(Refused,'Top-level extent invalid'):self.plan_for(overrun(with_esds(fixture(),aac_esds()),64*1024+1),SILENCE)
    def test_only_plain_aac_lc_variable_size_frames_are_silenced(self):
        for esds,reason in ((bytes(4)+b'opaque-descriptor','decoder description'),(aac_esds(kind=5),'AAC-LC'),(aac_esds(channels=6),'AAC-LC'),
                            (aac_esds(tail=b'\x56\xe5\x80'),'plain AAC-LC'),(aac_esds(tail=b'\x00'),'plain AAC-LC')):
            with self.subTest(reason=reason),self.assertRaisesRegex(Refused,reason):self.plan_for(with_esds(fixture(),esds)[:-2],SILENCE)
        self.produce(with_esds(fixture(),aac_esds(tail=b'\x56\xe5\x00'))[:-2],SILENCE)  # explicit "no SBR" (FFmpeg)
        with self.assertRaisesRegex(Refused,'fixed-size'):self.plan_for(with_esds(chunked(10),aac_esds())[:-2],SILENCE)
    def test_verifier_rejects_altered_silent_frames(self):
        source=with_esds(fixture(),aac_esds())[:-2];p,candidate=self.produce(source,SILENCE)
        broken=bytearray(candidate);broken[len(source)+2+8]^=1
        with self.assertRaisesRegex(Refused,'silent frames'):verify_candidate(p,lambda a,n:source[a:a+n],len(broken),lambda a,n:bytes(broken[a:a+n]))
    def test_diagnosis_names_the_silence_repair(self):
        import m4b_repair
        source=with_esds(fixture(),aac_esds())[:-2];diagnosis=m4b_repair.diagnose(len(source),lambda a,n:source[a:a+n])
        self.assertEqual((diagnosis['state'],[r['kind'] for r in diagnosis['repairs']]),('repairable',['truncated_final_frames']))
        self.assertIn('2 bytes early',diagnosis['damage'][0])
    def test_only_an_approved_silence_repair_skips_the_strict_source_decode(self):
        import copy,json,uuid,m4b_repair
        source=with_esds(fixture(),aac_esds())[:-2];contract=RepairAdmissionContractTests();contract.setUp()
        parent=contract.row(contract.manifest);fresh=copy.deepcopy(contract.manifest);fresh['job_id']=str(uuid.uuid4())
        child=json.loads(json.dumps(m4b_repair.bind(parent,fresh,m4b_repair.diagnose(len(source),lambda a,n:source[a:a+n]),'b'*64)))
        self.assertTrue(m4b_repair.silence_approved(child));self.assertFalse(m4b_repair.silence_approved(contract.manifest))
        other=json.loads(json.dumps(m4b_repair.bind(parent,fresh,m4b_repair.diagnose(len(overrun(fixture(),8)),lambda a,n:overrun(fixture(),8)[a:a+n]),'b'*64)))
        self.assertFalse(m4b_repair.silence_approved(other))


class SilenceRepairDecodeTests(unittest.TestCase):
    """Real decoder: the silent frames are valid AAC-LC and decode to exact digital silence; a
    real encoded book cut inside its final frame passes the full decode proof."""
    def setUp(self):
        import shutil,tempfile,threading
        from pathlib import Path
        self.ffmpeg=shutil.which('ffmpeg');self.assertTrue(self.ffmpeg and shutil.which('ffprobe'),'bundled ffmpeg/ffprobe required on PATH')
        area=Path(__file__).resolve().parents[1]/'scratch'/'m4b-repair-tests';area.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=area);self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.stop=threading.Event()
    def test_silent_frames_decode_to_exact_zero(self):
        import subprocess,m4b_preservation
        for channels in (1,2):
            for index,rate in ((3,48000),(4,44100),(8,16000)):
                frame=m4b_preservation.silent_aac_frame(channels);length=len(frame)+7
                header=((0xFFF<<44)|(1<<40)|(1<<38)|(index<<34)|(channels<<30)|(length<<13)|(0x7FF<<2)).to_bytes(7,'big')
                done=subprocess.run([self.ffmpeg,'-hide_banner','-v','error','-xerror','-nostdin','-f','aac','-i','pipe:0','-c:a','pcm_f64le','-f','f64le','pipe:1'],
                    input=(header+frame)*8,capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                with self.subTest(channels=channels,rate=rate):
                    self.assertEqual(done.returncode,0,done.stderr);self.assertEqual(len(done.stdout),8*1024*channels*8)
                    self.assertTrue(all(value==0.0 for value in memoryview(done.stdout).cast('d')))
    def test_real_aac_cut_inside_final_frames_is_proven(self):
        import audio_pipeline,m4b_preservation,m4b_repair
        for channels,cut in ((1,3),(2,700)):
            with self.subTest(channels=channels,cut=cut):
                full=self.root/f'full{channels}.m4b';source=self.root/f'cut{channels}.m4b';output=self.root/f'candidate{channels}.m4b'
                audio_pipeline.run_owned([self.ffmpeg,'-hide_banner','-v','error','-xerror','-nostdin','-n','-f','lavfi','-i','sine=frequency=997:sample_rate=44100:duration=1.5',
                    '-ac',str(channels),'-c:a','aac','-b:a','64000','-movflags','+faststart',str(full)],self.root,self.stop,60)
                data=full.read_bytes()[:-cut];source.write_bytes(data);read=lambda a,n:data[a:a+n]
                p=m4b_preservation.plan(len(data),read,{'title':'Approved'},None,SILENCE)
                with open(output,'wb') as sink:m4b_preservation.stream_candidate(p,read,sink.write)
                made=output.read_bytes();m4b_preservation.verify_candidate(p,read,len(made),lambda a,n:made[a:a+n])
                encoding={'channels':channels,'sample_rate':44100,'channel_layout':'mono' if channels==1 else 'stereo'}
                _,pcm,proof=m4b_repair.prove_silenced_tail(source,output,p,self.root,self.stop,1.5,encoding,evidence=audio_pipeline.copied_audio_evidence,run=audio_pipeline.run_owned)
                self.assertEqual(proof['replaced_packets'],p.repairs[0]['frames']);self.assertGreater(proof['intact_samples'],0)
                reference=m4b_repair._Pcm(channels*8)
                audio_pipeline.run_owned([self.ffmpeg,'-hide_banner','-v','error','-xerror','-nostdin','-f','mov','-i',str(full),'-map','0:a:0','-c:a','pcm_f64le','-f','f64le','pipe:1'],self.root,self.stop,60,telemetry=reference)
                self.assertEqual(pcm['sample_count'],reference.bytes//(channels*8))  # same length as the undamaged recording
                with self.assertRaisesRegex(Refused,'Source damage differs'):
                    m4b_repair.prove_silenced_tail(full,output,p,self.root,self.stop,1.5,encoding,evidence=audio_pipeline.copied_audio_evidence,run=audio_pipeline.run_owned)

if __name__=='__main__':unittest.main()
