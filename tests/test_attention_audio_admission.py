"""Read-only stream admission and exact text-table repair negative controls."""
import contextlib,hashlib,os,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import m4b_preservation as m
import zone_identifier as z
from native_io import VerifiedFile,DirectoryBoundary,BoundaryError
from source_cleanup import single_stream
from test_m4b_preservation import fixture,add_chapter_graph,unpack

SCRATCH=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'attention-audio-admission'

class ReadAdmissionTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True,exist_ok=True)
        self.path=Path(tempfile.mkdtemp(prefix='audio-read-',dir=SCRATCH))/'source.m4b';self.path.write_bytes(b'original audio')
    def marker(self,raw=b'[ZoneTransfer]\r\nZoneId=3\r\n\x00'):
        Path(str(self.path)+':Zone.Identifier').write_bytes(raw)
    @contextlib.contextmanager
    def admitted(self):
        with DirectoryBoundary(self.path.parent,self.path.parent),VerifiedFile(self.path) as held,z.readable_source_streams(self.path,held) as check:yield check
    def test_observed_marker_and_source_preserved_and_cleanup_still_strict(self):
        self.marker();before=z.streams(self.path)
        with self.admitted() as check:
            check()
            with self.assertRaises(PermissionError):Path(str(self.path)+':Zone.Identifier').write_bytes(b'changed')
            with self.assertRaises(PermissionError):self.path.write_bytes(b'changed')
        self.assertEqual(z.streams(self.path),before);self.assertEqual(self.path.read_bytes(),b'original audio')
        self.assertEqual(Path(str(self.path)+':Zone.Identifier').read_bytes(),b'[ZoneTransfer]\r\nZoneId=3\r\n\x00')
        with self.assertRaises(BoundaryError):single_stream(self.path)
    def test_unknown_and_multiple_streams_refused(self):
        self.marker();Path(str(self.path)+':Other').write_bytes(b'unique')
        with self.assertRaises(BoundaryError),self.admitted():pass
        self.assertEqual(Path(str(self.path)+':Other').read_bytes(),b'unique')
    def test_unknown_marker_schema_and_size_refused(self):
        for raw in (b'x',b'[ZoneTransfer]\nZoneId=3\nUnknown=secret',b'[ZoneTransfer]\r\nZoneId=3\r\n\x00\x00',b'x'*8193):
            self.marker(raw)
            with self.subTest(raw=raw[:50]),self.assertRaises(BoundaryError),self.admitted():pass
            self.assertEqual(Path(str(self.path)+':Zone.Identifier').read_bytes(),raw)
    def test_markerless_source_admitted(self):
        with self.admitted() as check:check()
    def test_base_alias_is_refused_without_stream_changes(self):
        import os
        self.marker();os.link(self.path,self.path.parent/'alias.m4b')
        with self.assertRaisesRegex(BoundaryError,'unique'),self.admitted():pass
        self.assertEqual(Path(str(self.path)+':Zone.Identifier').read_bytes(),bytes.fromhex('5b5a6f6e655472616e736665725d0d0a5a6f6e6549643d330d0a00'))
    def test_stream_enumeration_drift_refused(self):
        self.marker();real=z.streams
        with self.assertRaises(BoundaryError),self.admitted() as check:
            with patch.object(z,'streams',return_value=real(self.path)+[(':Late:$DATA',1)]):check()

def damaged():
    source=add_chapter_graph(fixture(),video=False)
    old=m.build(b'stsd',bytes(4)+struct.pack('>I',1)+m.build(b'text',bytes(6)+bytes([0,1])+bytes(43)))
    observed=m.build(b'stsd',bytes.fromhex('00000000000000010000003b7465787400000000000000010000000400000001ffffffffffff0000000000000000000000000010000d00000000000d00000000000000'))
    source=source.replace(old,observed);top=unpack(source)
    def rewrite(raw):
        result=[]
        for box in m.boxes(raw):
            if box.kind in {b'moov',b'trak',b'mdia',b'minf',b'stbl'}:result.append(m.repack(box,rewrite(box.payload)))
            elif box.kind==b'stsz' and box.payload==bytes(4)+struct.pack('>II',7,1):result.append(m.repack(box,bytes(4)+struct.pack('>II',16,0)))
            else:result.append(box.raw)
        return b''.join(result)
    return top[b'ftyp'].raw+rewrite(top[b'moov'].raw)+m.build(b'mdat',top[b'mdat'].payload[:-7]+bytes.fromhex('000230310000000c656e636400000100'))

class ChapterCountProfileTests(unittest.TestCase):
    def plan(self,source,repair=frozenset()):return m.plan(len(source),lambda a,n:source[a:a+n],{'title':'Approved'},None,repair)
    def test_observed_profile_preserves_every_native_track_byte(self):
        source=damaged()
        plan=self.plan(source);self.assertFalse(plan.repairs);self.assertEqual(len(plan.profile_notes),1)
        self.assertEqual(plan.profile_notes[0]['mapped_samples'],1);self.assertEqual(plan.profile_notes[0]['preserved_count'],0)
        old=[b.raw for b in m.boxes(unpack(source)[b'moov'].payload) if b.kind==b'trak']
        new=[b.raw for b in m.boxes(plan.appended_movie[8:]) if b.kind==b'trak']
        self.assertEqual(old,new)
        output=[];m.stream_candidate(plan,lambda a,n:source[a:a+n],output.append)
        self.assertFalse(self.plan(b''.join(output)).repairs);self.assertEqual(self.plan(b''.join(output)).profile_notes,plan.profile_notes)
    def test_unknown_chapter_payload_refused(self):
        source=damaged();source=source[:-1]+b'X'
        with self.assertRaisesRegex(m.Refused,'label bytes differ'):self.plan(source)
    def test_mismatched_timing_remains_refused(self):
        source=damaged();needle=m.build(b'stts',bytes(4)+struct.pack('>III',1,1,60))
        bad=source.replace(needle,m.build(b'stts',bytes(4)+struct.pack('>III',1,2,60)))
        with self.assertRaisesRegex(m.Refused,'Decode count/media clock mismatch'):self.plan(bad)
    def test_nonzero_wrong_count_and_audio_table_never_allowed(self):
        source=damaged();needle=m.build(b'stsz',bytes(4)+struct.pack('>II',16,0))
        bad=source.replace(needle,m.build(b'stsz',bytes(4)+struct.pack('>II',16,2)))
        with self.assertRaisesRegex(m.Refused,'Sample size table'):self.plan(bad)
        source=fixture();needle=m.build(b'stsz',bytes(4)+struct.pack('>II',0,3)+struct.pack('>III',3,4,5))
        bad=source.replace(needle,m.build(b'stsz',bytes(4)+struct.pack('>II',16,0))+bytes(len(needle)-20))
        with self.assertRaises(m.Refused):self.plan(bad)

if __name__=='__main__':unittest.main()
