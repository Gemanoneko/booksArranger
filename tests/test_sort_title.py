import json,unittest,sys,threading,subprocess,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import test_merge_service as fixtures
from metadata import audiobook_sort_title,future_audio_tags
from quicktime_chapters import boxes,box,transform,ChapterFormatError

class SortTitleTests(unittest.TestCase):
    def test_sort_atom_replacement_unicode_and_offset_widths(self):
        for kind,width in ((b'stco',4),(b'co64',8)):
            offsets=box(kind,b'\0'*4+(1).to_bytes(4,'big')+(123).to_bytes(width,'big'))
            old=box(b'sonm',box(b'data',b'\0\0\0\1'+b'\0'*4+b'Old'))
            source=box(b'moov',box(b'trak',box(b'mdia',box(b'minf',box(b'stbl',offsets))))+box(b'udta',box(b'meta',b'\0'*4+box(b'ilst',old))))
            receipt={'old_mdat_start':100,'old_file_size':500,'chunk_offsets':0}
            measured=transform(source,receipt=receipt,sort_title='Éye of God',normalize_chapters=False)
            delta=len(measured)-len(source)
            receipt={'old_mdat_start':100,'old_file_size':500,'chunk_offsets':0}
            actual=transform(source,delta,receipt=receipt,sort_title='Éye of God',normalize_chapters=False)
            self.assertEqual(actual.count(b'sonm'),1);self.assertIn('Éye of God'.encode('utf-8'),actual)
            self.assertIn((123+delta).to_bytes(width,'big'),actual)
            self.assertEqual(receipt['sort_atoms'],1)

    def test_whole_word_only_and_language_scope(self):
        for title,wanted in [('The Eye of God','Eye of God'),('THE Eye of God','Eye of God'),('the Eye of God','Eye of God'),('Theatre','Theatre'),('The','The'),('The-Eye','The-Eye'),('A Book','A Book'),('An Eye','An Eye'),('Eye of God','Eye of God')]:
            review={'title':title,'original_language':'Other'}
            self.assertEqual(audiobook_sort_title(review),wanted)
            self.assertEqual(future_audio_tags({},review)['SORTTITLE'],wanted)
            self.assertEqual(review['title'],title)
        self.assertEqual(audiobook_sort_title({'title':'The Eye','original_language':'Russian'}),'The Eye')
        self.assertEqual(audiobook_sort_title({'title':'The Eye'}),'The Eye')

    def test_actual_review_export_roundtrip_with_and_without_chapters(self):
        for chapters in (True,False):
            fixture=fixtures.MergeTests();fixture.setUp()
            try:
                fixture.review.update(title='The Eye of God')
                row=fixture.ready()
                if not chapters:
                    row=fixture.service.reviews.tracks('Audiobooks',row['id'],row['revision'],row['track_order'],row['included'],True,True,False,evidence_note='Fixture intended source set and order reviewed')
                fixture.service.create('Audiobooks',row['id'],row['revision']);status=fixture.wait()
                self.assertEqual(status['completed'],1,status)
                out=status['jobs'][0]['output'];tags=out['validation']['tags']
                self.assertEqual(tags['title'],'The Eye of God')
                self.assertEqual(tags['sort_name'],'Eye of God')
                self.assertEqual(tags['artist'],'Name Author');self.assertEqual(tags['media_type'],'2')
                self.assertEqual(len(out['validation']['chapters']),2 if chapters else 0)
                data=Path(out['final_path']).read_bytes()
                moov=next(v for k,v in boxes(data) if k==b'moov')
                udta=next(v for k,v in boxes(moov[8:]) if k==b'udta')
                meta=next(v for k,v in boxes(udta[8:]) if k==b'meta')
                ilst=next(v for k,v in boxes(meta[12:]) if k==b'ilst')
                sonm=[v for k,v in boxes(ilst[8:]) if k==b'sonm']
                self.assertEqual(len(sonm),1)
                payload=boxes(sonm[0][8:])[0][1]
                self.assertEqual(payload[8:16],b'\0\0\0\1'+b'\0'*4)
                self.assertEqual(payload[16:].decode('utf-8'),'Eye of God')
                self.assertEqual([fixtures.digest(p) for p in fixture.sources],fixture.hashes)
            finally:fixture.tearDown()

if __name__=='__main__':unittest.main()
