import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from scanner import Inventory,connect
from review_backend import CandidateReviewService

AREA=Path(__file__).resolve().parents[1]/'scratch'/'review-tests'
AREA.mkdir(parents=True,exist_ok=True)
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);audio=self.base/'audio';audio.mkdir()
        self.roots={'Audiobooks':str(audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        folder=audio/'One';folder.mkdir()
        self.sources=[]
        for i in (1,2):
            path=folder/(str(i)+'.mp3');path.write_bytes(b'private audio fixture'+bytes([i]));self.sources.append(path)
        (folder/'cover.png').write_bytes(PNG)
        def reader(path,kind,stop):return {'title':'Book','track_title':'Chapter '+Path(path).stem,'tags':{'album':'Book','comment':'Original comment'},'probe':{'format':{'duration':'1.0'}},'method':'fixture'}
        self.inventory=Inventory(self.base/'catalog.sqlite3',self.roots,reader)
        self.inventory.launch('Audiobooks');self.inventory.worker.join(5)
        self.service=CandidateReviewService(self.inventory,self.base/'cover-cache')
        self.review={'title':'Book','author':'Author Name','canonical_author':'Name Author','original_language':'Other','series':'','number':'','genre':'Fantasy','multi_author':False,'anthology':False,'narrator':'Reader','topic':''}
        self.row=self.service.page()['rows'][0]

    def approved(self):
        self.row=self.service.covers('Audiobooks',self.row['id'],self.row['revision'])
        cover=self.row['cover_choices'][0]['id']
        self.row=self.service.save('Audiobooks',self.row['id'],self.row['revision'],self.review,True,'Reviewed book credits and original-work bibliography',cover_id=cover)
        return self.row

    def ready(self):
        self.approved();self.row=self.service.tracks('Audiobooks',self.row['id'],self.row['revision'],self.row['track_order'],self.row['included'],True,True,False,evidence_note='Reviewed the exact source recording and playback order')
        return self.row

    def test_ready_manifest_keeps_unknown_external_completeness(self):
        row=self.ready();self.assertTrue(row['creation']['can_create'],row['creation']['reasons'])
        self.assertEqual(row['creation']['recording_completeness'],'Recording completeness unknown')
        manifest=self.service.build_manifest('Audiobooks',row['id'],row['revision'])
        self.assertEqual(len(manifest['sources']),2)
        self.assertEqual(manifest['evidence']['metadata_actor'],'user')
        self.assertIn('Original comment',manifest['comments']);self.assertIn('Narrator: Reader',manifest['comments'])
        self.assertEqual(manifest['chapters'],[])
        self.assertEqual(self.service.page(limit=1,status='ready')['total'],1)

    def test_source_change_invalidates_exact_revision(self):
        row=self.ready();self.sources[0].write_bytes(b'changed private fixture content')
        with self.assertRaisesRegex(ValueError,'Source changed'):
            self.service.build_manifest('Audiobooks',row['id'],row['revision'])
        self.inventory.launch('Audiobooks');self.inventory.worker.join(5)
        fresh=self.service.page()['rows'][0]
        self.assertFalse(fresh['metadata_approved']);self.assertFalse(fresh['creation']['can_create'])

    def test_review_context_survives_restart_and_edits_invalidate_tracks(self):
        row=self.ready();service=CandidateReviewService(self.inventory,self.base/'cover-cache')
        self.assertTrue(service.page()['rows'][0]['creation']['can_create'])
        changed=dict(self.review,title='Renamed')
        fresh=service.save('Audiobooks',row['id'],row['revision'],changed,False,'Reviewed renamed title',cover_id=row['selected_cover']['id'])
        self.assertFalse(fresh['creation']['can_create']);self.assertFalse(fresh['review_context']['order_confirmed'])
        with self.assertRaisesRegex(ValueError,'Candidate changed'):service.tracks('Audiobooks',row['id'],row['revision'],row['track_order'],row['included'],True,True,False,evidence_note='Old review')

    def test_assistant_requires_per_field_evidence_and_actor_is_honest(self):
        self.row=self.service.covers('Audiobooks',self.row['id'],self.row['revision']);cover=self.row['cover_choices'][0]['id']
        with self.assertRaisesRegex(ValueError,'per-field'):
            self.service.save('Audiobooks',self.row['id'],self.row['revision'],self.review,True,'Concrete publisher evidence identifying the book',cover_id=cover,actor='assistant')
        evidence=[]
        for field,value in [('title','Book'),('authors',['Name Author']),('original_language','English'),('standalone',True)]:
            evidence.append({'field':field,'cited_value':value,'source_url':'https://publisher.example/book','retrieved_utc':'2026-10-09T12:00:00Z','reviewer_actor':'assistant','reviewer_identity':'Ender','basis':'Publisher record identifies this accepted field'})
        row=self.service.save('Audiobooks',self.row['id'],self.row['revision'],self.review,True,'Publisher record establishes identity and original English work',cover_id=cover,actor='assistant',evidence=evidence)
        self.assertEqual(row['review_context']['metadata_actor'],'assistant')

    def test_cover_serving_cannot_escape_cache_and_missing_cover_blocks(self):
        row=self.approved();self.assertEqual(self.service.cover_file(row['selected_cover']['id']).parent,self.base/'cover-cache')
        with self.assertRaises(ValueError):self.service.cover_file('../catalog.sqlite3')
        self.service.cover_file(row['selected_cover']['id']).unlink()
        self.assertFalse(self.service.page()['rows'][0]['metadata_approved'])

    def test_loose_sources_block_even_after_explicit_confirmation(self):
        with connect(self.inventory.database) as db:
            for path in self.sources:
                raw=json.loads(db.execute('SELECT metadata FROM files WHERE path=?',(str(path),)).fetchone()[0]);raw['tags'].pop('album')
                db.execute('UPDATE files SET metadata=? WHERE path=?',(json.dumps(raw),str(path)))
        self.row=self.service.page()['rows'][0];row=self.ready()
        self.assertFalse(row['creation']['can_create']);self.assertTrue(any('common book source' in r for r in row['creation']['reasons']))

    def test_order_inclusion_requires_exact_keys(self):
        with self.assertRaises(ValueError):self.service.tracks('Audiobooks',self.row['id'],self.row['revision'],['wrong'],[],True,True,False,evidence_note='Reviewed')

    def test_async_proposal_cannot_overwrite_draft(self):
        class Client:
            def lookup(self,query,author=''):
                self.query,self.author=query,author
                return [{'title':'Possible work','authors':['Catalog author'],'public_url':'https://openlibrary.org/works/OL1W'}]
        client=Client();self.service.client=client
        row=self.service.save('Audiobooks',self.row['id'],self.row['revision'],self.review,False,'Manual identity work in progress')
        self.service.match('Audiobooks',row['id'],row['revision']);self.service.workers[row['id']].join(5)
        fresh=self.service.page()['rows'][0]
        self.assertEqual(fresh['review']['title'],'Book');self.assertEqual(fresh['matching']['state'],'found')
        self.assertEqual(client.author,'Name Author');self.assertFalse(fresh['metadata_approved'])

    def test_equal_fingerprint_changed_bytes_fail_hash_check(self):
        row=self.ready();path=self.sources[0];stat=path.stat();data=path.read_bytes()
        path.write_bytes(b'X'+data[1:]);os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        with self.assertRaisesRegex(ValueError,'Source changed'):
            self.service.build_manifest('Audiobooks',row['id'],row['revision'])

    def test_single_existing_m4b_never_ready_for_concatenation(self):
        for path in self.sources:path.unlink()
        new=self.sources[0].with_suffix('.m4b');new.write_bytes(b'private existing audiobook')
        self.inventory.launch('Audiobooks');self.inventory.worker.join(5)
        # Historical missing members remain blocking alongside the single-file guard.
        row=self.service.page()['rows'][0]
        self.assertFalse(row['creation']['can_create'])

    def test_filter_is_applied_before_page_and_chapter_names_are_explicit(self):
        row=self.ready()
        row=self.service.tracks('Audiobooks',row['id'],row['revision'],list(reversed(row['track_order'])),row['included'],True,True,True,evidence_note='Reviewed one chapter per selected file and exact chapter names')
        manifest=self.service.build_manifest('Audiobooks',row['id'],row['revision'])
        self.assertEqual(manifest['chapters'],['Chapter 2','Chapter 1'])
        self.assertEqual(self.service.page(limit=1,offset=1,status='ready')['total'],1)
        self.assertEqual(self.service.page(limit=1,offset=1,status='ready')['rows'],[])


if __name__=='__main__':unittest.main()
