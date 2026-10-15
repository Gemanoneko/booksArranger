"""Pure structural M4B preservation fixtures; opaque packets do not prove decoding."""
import hashlib
import struct
import unittest
from m4b_preservation import Refused,boxes,build,plan,stream_candidate

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

if __name__=='__main__':unittest.main()
