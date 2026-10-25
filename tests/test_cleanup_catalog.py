"""Intentional-retirement continuity using disposable, private source fixtures only."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from scanner import Inventory,connect
from scan_wait import finish_scan

AREA=Path(__file__).resolve().parents[1]/'scratch'/'cleanup-catalog-tests'
AREA.mkdir(parents=True,exist_ok=True)


class CleanupCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.audio=self.base/'audio';self.book=self.audio/'Book';self.book.mkdir(parents=True)
        self.roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        self.paths=[];self.calls=[]
        for n in (1,2):
            path=self.book/f'{n:02}.mp3';path.write_bytes(b'private source'+bytes([n]));self.paths.append(path)
        self.cover=self.book/'cover.jpg';self.cover.write_bytes(b'private companion fixture')
        def reader(path,kind,stop):
            self.calls.append(path)
            return {'title':'Book','track_title':Path(path).stem,'method':'fixture','tags':{'album':'Book','track':Path(path).stem if kind=='audiobook' else ''}}
        self.inventory=Inventory(self.base/'catalog.sqlite3',self.roots,reader)
        with connect(self.inventory.database) as db:
            db.execute('''CREATE TABLE source_retirements(root TEXT,path TEXT,cleanup_id TEXT,job_id TEXT,
                source_hash TEXT,size INTEGER,modified TEXT,state TEXT,PRIMARY KEY(root,path,cleanup_id))''')
        self.scan()
        row=self.inventory.candidates('Audiobooks')['rows'][0]
        self.review={'title':'Book','author':'Author Name','canonical_author':'Name Author','original_language':'Other','series':'','number':''}
        self.original=self.inventory.save_candidate('Audiobooks',row['id'],row['revision'],self.review,True)

    def scan(self,resume=False):
        self.inventory.launch('Audiobooks',resume);finish_scan(self.inventory)
        self.assertEqual(self.inventory.status('Audiobooks')['state'],'completed',self.inventory.last_error)

    def retire(self,paths):
        with connect(self.inventory.database) as db:
            for path in paths:
                row=db.execute('SELECT * FROM files WHERE path=?',(str(path),)).fetchone()
                db.execute('INSERT INTO source_retirements VALUES(?,?,?,?,?,?,?,?)',(str(self.audio),str(path),'cleanup','job','fixturehash',row['size'],str(row['modified']),'removed'))
                path.unlink() # Private fixture only, simulating the separately owned native cleanup.
                db.execute("UPDATE files SET missing=0,error='' WHERE path=?",(str(path),))

    def row(self):return self.inventory.candidates('Audiobooks')['rows'][0]

    def test_all_retired_remain_history_without_missing_or_revision_loss(self):
        self.retire(self.paths);self.scan()
        row=self.row()
        self.assertEqual(row['revision'],self.original['revision'])
        self.assertEqual(row['fingerprint'],self.original['fingerprint'])
        self.assertTrue(row['metadata_approved']);self.assertTrue(row['all_sources_retired'])
        self.assertEqual(row['active_members'],[]);self.assertFalse(row['can_approve'])
        self.assertEqual([m['path'] for m in row['members']],[str(p) for p in self.paths])
        files=self.inventory.rows('Audiobooks')
        self.assertTrue(all(not r['missing'] and not r['error'] for r in files))
        self.assertEqual(self.inventory.status('Audiobooks')['unresolved_errors'],0)

    def test_partial_retirement_keeps_exact_ordered_provenance(self):
        self.retire(self.paths[:1]);self.scan()
        row=self.row();self.assertEqual(row['revision'],self.original['revision'])
        self.assertEqual(row['retired_source_count'],1)
        self.assertEqual([m['path'] for m in row['active_members']],[str(self.paths[1])])
        self.assertEqual([m['path'] for m in row['members']],[str(p) for p in self.paths])
        self.assertFalse(row['all_sources_retired'])

    def test_paused_queue_with_retired_name_resumes_without_read_error(self):
        self.retire(self.paths[:1])
        with connect(self.inventory.database) as db:
            db.execute("UPDATE jobs SET state='stopped' WHERE root=?",(str(self.audio),))
            db.execute("INSERT OR REPLACE INTO queue VALUES(?,1,?,0,'pending')",(str(self.audio),str(self.paths[0])))
        self.scan(True)
        self.assertEqual(self.inventory.status('Audiobooks')['unresolved_errors'],0)
        with connect(self.inventory.database) as db:
            result=db.execute('SELECT details FROM scan_outcomes WHERE path=?',(str(self.paths[0]),)).fetchone()[0]
        self.assertIn('intentionally retired',result)

    def test_equal_size_ns_new_arrival_is_read_and_supersedes_old_retirement(self):
        stat=self.paths[0].stat();self.retire(self.paths[:1]);self.calls.clear()
        self.paths[0].write_bytes(b'X'+b'private source'[1:]+bytes([1]))
        os.utime(self.paths[0],ns=(stat.st_atime_ns,stat.st_mtime_ns))
        self.scan()
        self.assertIn(str(self.paths[0]),self.calls,'Equal-fingerprint reappearance must not reuse old metadata')
        with connect(self.inventory.database) as db:
            self.assertEqual(db.execute('SELECT state FROM source_retirements').fetchone()[0],'superseded')
        row=self.row();self.assertEqual(row['retired_source_count'],0)
        self.assertEqual(len(row['active_members']),2)

    def test_failed_new_arrival_does_not_claim_superseded_success(self):
        self.retire(self.paths[:1]);self.paths[0].write_bytes(b'new unreadable metadata fixture')
        def bad(*args):raise ValueError('fixture metadata failure')
        self.inventory.reader=bad
        self.inventory.launch('Audiobooks');finish_scan(self.inventory)
        with connect(self.inventory.database) as db:
            self.assertEqual(db.execute('SELECT state FROM source_retirements').fetchone()[0],'removed')
            self.assertIn('metadata failure',db.execute('SELECT error FROM files WHERE path=?',(str(self.paths[0]),)).fetchone()[0])

    def test_failed_equal_fingerprint_arrival_remains_visible_active_error(self):
        stat=self.paths[0].stat();data=self.paths[0].read_bytes();self.retire(self.paths[:1])
        self.paths[0].write_bytes(data);os.utime(self.paths[0],ns=(stat.st_atime_ns,stat.st_mtime_ns))
        def bad(path,kind,stop):
            if path==str(self.paths[0]):raise ValueError('new arrival metadata error')
            return {'title':'Book','track_title':Path(path).stem,'method':'fixture','tags':{'album':'Book'}}
        self.inventory.reader=bad
        self.inventory.launch('Audiobooks');finish_scan(self.inventory)
        row=self.row()
        self.assertGreater(row['revision'],self.original['revision'])
        self.assertEqual(row['retired_source_count'],0)
        self.assertTrue(any(m['error'] for m in row['active_members']))

    def test_saved_queue_recovery_asset_never_becomes_catalog_source(self):
        path=self.audio/'owned-snapshot.mp3';path.write_bytes(b'private owned recovery')
        with connect(self.inventory.database) as db:
            db.execute('CREATE TABLE owned_artifacts(path TEXT,kind TEXT)')
            db.execute('INSERT INTO owned_artifacts VALUES(?,?)',(str(path),'recovery'))
            db.execute("UPDATE jobs SET state='stopped' WHERE root=?",(str(self.audio),))
            db.execute("INSERT OR REPLACE INTO queue VALUES(?,1,?,0,'pending')",(str(self.audio),str(path)))
        self.scan(True)
        self.assertNotIn(str(path),{r['path'] for r in self.inventory.rows('Audiobooks')})

    def test_restored_record_does_not_suppress_real_missing_file(self):
        self.retire(self.paths[:1])
        with connect(self.inventory.database) as db:db.execute("UPDATE source_retirements SET state='restored'")
        self.scan()
        missing=next(r for r in self.inventory.rows('Audiobooks') if r['path']==str(self.paths[0]))
        self.assertEqual(missing['missing'],1)

    def test_recovery_ownership_is_exact_not_filename_pattern(self):
        recovery=self.audio/'registered-recovery';recovery.mkdir()
        (recovery/'snapshot.mp3').write_bytes(b'owned recovery')
        ordinary=self.audio/'source-recovery.mp3';ordinary.write_bytes(b'unregistered legitimate arrival')
        with connect(self.inventory.database) as db:
            db.execute('CREATE TABLE owned_artifacts(path TEXT,kind TEXT)')
            db.execute('INSERT INTO owned_artifacts VALUES(?,?)',(str(recovery),'recovery'))
        self.scan()
        paths={r['path'] for r in self.inventory.rows('Audiobooks')}
        self.assertNotIn(str(recovery/'snapshot.mp3'),paths)
        self.assertIn(str(ordinary),paths)

    def test_remaining_active_source_change_still_invalidates_group(self):
        self.retire(self.paths[:1]);self.paths[1].write_bytes(b'changed remaining source')
        self.scan();row=self.row()
        self.assertGreater(row['revision'],self.original['revision'])
        self.assertTrue(row['changed']);self.assertFalse(row['metadata_approved'])


if __name__=='__main__':unittest.main()
