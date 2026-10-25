import base64,json,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from scanner import Inventory,connect
from review_backend import CandidateReviewService
from scan_wait import close_scan,finish_scan
AREA=Path(__file__).resolve().parents[1]/'scratch'/'paging-tests';AREA.mkdir(parents=True,exist_ok=True)
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')

class Paging(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name);audio=self.base/'audio';audio.mkdir()
        for n in range(127):
            folder=audio/f'Book{n:03}';folder.mkdir();(folder/'01.mp3').write_bytes(b'private fixture')
        def reader(path,kind,stop):
            n=int(Path(path).parent.name[4:])
            if n<125:raise ValueError('Private unreadable fixture')
            return {'title':'Book','track_title':'Chapter1','tags':{'album':'Book'},'method':'fixture'}
        self.inv=Inventory(self.base/'catalog.sqlite3',{'Audiobooks':str(audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')},reader)
        # 0.22.0 entry check (2026-10-25): a 10 s join returned silently under the gate's load, so the test read 119 of 127
        # books and the folder's removal then met the catalog the running scan still held open. Wait for the scan to end,
        # and close it before the folder goes (cleanups run last-in, first-out), even when setUp itself fails.
        self.addCleanup(close_scan,self.inv)
        self.inv.launch('Audiobooks');finish_scan(self.inv);self.service=CandidateReviewService(self.inv,self.base/'covers')
        self.rows=self.inv.candidates('Audiobooks',1000)['rows']
        cover=str(uuid.uuid4());(self.service.cache/(cover+'.png')).write_bytes(PNG)
        with connect(self.inv.database) as db:
            for row in self.rows[-2:]:
                ctx={'metadata_approved':True,'cover_id':cover,'cover_choices':[{'id':cover,'sha256':'fixture'}]}
                db.execute('INSERT INTO candidate_context VALUES(?,?,?)',(row['id'],row['revision'],json.dumps(ctx)))

    def test_global_error_and_approval_filters_before_paging_no_source_reads(self):
        with patch('review_backend.fresh_stat',side_effect=AssertionError('List source stat')),patch('review_backend.source_hash',side_effect=AssertionError('List source hash')),patch('review_backend.digest',side_effect=AssertionError('List file hash')),patch.object(self.service,'enrich',wraps=self.service.enrich) as enrich:
            errors=self.service.page(limit=100,offset=100,status='errors')
            self.assertEqual((errors['total'],len(errors['rows'])),(125,25));self.assertEqual(enrich.call_count,25)
            enrich.reset_mock();approved=self.service.page(limit=1,status='approved')
            self.assertEqual((approved['total'],len(approved['rows'])),(2,1));self.assertEqual(enrich.call_count,1)
            allrows=self.service.page(limit=100);self.assertEqual((allrows['total'],len(allrows['rows'])),(127,100))

    def test_unchanged_grouping_reused_but_catalog_mutation_invalidates(self):
        with patch('groups.build',side_effect=AssertionError('Unchanged catalog regrouped')):
            self.assertEqual(self.inv.candidates('Audiobooks',1)['total'],127)
        path=self.rows[-1]['members'][0]['path']
        with connect(self.inv.database) as db:
            # Not the album: since v0.9.0 the embedded album is part of the book's identity, so a new album is a new book.
            metadata=json.loads(db.execute('SELECT metadata FROM files WHERE path=?',(path,)).fetchone()[0]);metadata['track_title']='Changed source clue'
            db.execute('UPDATE files SET metadata=? WHERE path=?',(json.dumps(metadata),path))
        import groups
        with patch('groups.build',wraps=groups.build) as build:
            result=self.inv.candidates('Audiobooks',1000);self.assertEqual(build.call_count,1)
        row=next(r for r in result['rows'] if r['id']==self.rows[-1]['id']);self.assertGreater(row['revision'],self.rows[-1]['revision'])
        self.assertEqual(self.service.page(status='approved')['total'],1)

    def test_job_filter_finds_later_candidate_without_enriching_others(self):
        id=self.rows[-1]['id'];job={'job_id':str(uuid.uuid4()),'state':'pending','stage':'queued','reason':'','manifest':{'candidate_id':id}}
        self.service.jobs=SimpleNamespace(jobs=SimpleNamespace(status=lambda:{'jobs':[job]}))
        with patch.object(self.service,'enrich',wraps=self.service.enrich) as enrich:
            result=self.service.page(status='jobs',limit=1)
            self.assertEqual(result['total'],1);self.assertEqual(result['rows'][0]['id'],id);self.assertEqual(enrich.call_count,1)

if __name__=='__main__':unittest.main()
