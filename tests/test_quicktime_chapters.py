import unittest,struct,threading,tempfile
from pathlib import Path
from quicktime_chapters import boxes,box,description,legacy_entry,normalize,ChapterFormatError

AREA=Path(__file__).resolve().parents[1]/'scratch/qt-tests';AREA.mkdir(parents=True,exist_ok=True)

class Layout(unittest.TestCase):
    def test_documented_legacy_offsets_and_font_length(self):
        entry=legacy_entry(struct.pack('>I4s',59,b'text')+b'\0'*7+b'\1')
        self.assertEqual(len(entry),65);self.assertEqual(entry[59:],b'\x05Arial')
        self.assertEqual(entry[38:46],b'\0'*8);self.assertEqual(description(entry)['font_name'],'Arial')
    def test_generated_stub_is_rejected_by_legacy_layout(self):
        with self.assertRaises(ChapterFormatError):description(b'\0'*59)
    def test_malformed_boxes_and_headers_fail_closed(self):
        with self.assertRaises(ChapterFormatError):boxes(struct.pack('>I4s',1,b'moov'))
        with self.assertRaises(ChapterFormatError):legacy_entry(b'\0'*16)
    def test_both_chunk_widths_relocate_and_payload_exact(self):
        for kind,width in ((b'stco',4),(b'co64',8)):
            with tempfile.TemporaryDirectory(dir=AREA) as folder:
                folder=Path(folder);header=struct.pack('>I4s',59,b'text')+b'\0'*7+b'\1'
                stub=header+b'\0'*43
                def movie(offset):
                    stsd=box(b'stsd',b'\0'*4+struct.pack('>I',1)+stub)
                    table=box(kind,b'\0'*4+struct.pack('>I',1)+offset.to_bytes(width,'big'))
                    handler=box(b'hdlr',b'\0'*8+b'text'+b'\0'*12)
                    return box(b'moov',box(b'trak',box(b'mdia',handler+box(b'minf',box(b'stbl',stsd+table)))))
                prefix=box(b'ftyp',b'isom\0\0\2\0isomiso2mp41');free=box(b'free',b'');media=box(b'mdat',b'\0\x08Track 01MEDIA')
                offset=len(prefix)+len(movie(0))+len(free)+8
                source=folder/'source.m4b';source.write_bytes(prefix+movie(offset)+free+media)
                output=folder/'output.m4b';receipt=normalize(source,output,threading.Event())
                self.assertEqual(receipt['metadata_growth'],6);self.assertEqual(receipt['chunk_offsets'],1)
                self.assertTrue(output.read_bytes().endswith(media))
                self.assertIn((offset+6).to_bytes(width,'big'),output.read_bytes())
                with self.assertRaises(FileExistsError):normalize(source,output,threading.Event())

if __name__=='__main__':unittest.main()
