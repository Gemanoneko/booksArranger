import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from scanner import Inventory,connect
from scan_wait import finish_scan
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
        self.inventory.launch('Audiobooks');finish_scan(self.inventory)
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
        self.inventory.launch('Audiobooks');finish_scan(self.inventory)
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

    def test_list_rows_carry_the_decided_author_not_the_tag(self):
        # Ruling 74f (Judy 0.24.1 section 3): the Author / reader column reads row.credits, the saved review's author (the folder
        # name it files under, else its Artist-tag author) and reader; no review yet is "not decided", whatever the tags say.
        self.assertEqual(self.row['credits'],{'author':'','reader':'','decided':False})
        self.service.save('Audiobooks',self.row['id'],self.row['revision'],self.review,False,'')
        self.assertEqual(self.service.page()['rows'][0]['credits'],{'author':'Author Name','reader':'Reader','decided':True})
        from review_backend import decided_credits
        self.assertEqual(decided_credits({'review':{'author':' ','canonical_author':'Stephen King','narrator':''},'artists':['Reader Tag']}),{'author':'Stephen King','reader':'','decided':True})
        self.assertEqual(decided_credits({'review':None,'artists':['Пухов Сергей']}),{'author':'','reader':'','decided':False})
        self.assertEqual(decided_credits({'review':{'author':'Без автора'}})['author'],'Без автора','an approval without an author shows where it files')

    def test_m3_a_books_names_are_never_saved_from_the_panel(self):
        # Ruling 40 (Senua's 0.22.3 review, M3): the six name fields hidden in a book's panel were still sent and saved,
        # as an "Entered by you" source, so a stale title held the book against his newer Edit names.
        import manual_metadata
        row=self.service.save('Audiobooks',self.row['id'],self.row['revision'],self.review,False,'')
        stale=dict(self.review,title='Stale hidden title',author='Stale Folder',series='Old series',number='3',universe='Old universe',anthology=True,narrator='New reader')
        fresh=self.service.save('Audiobooks',row['id'],row['revision'],stale,False,'',names_row_only=True)
        self.assertEqual({k:fresh['review'].get(k) for k in ('title','author','series','number','universe','anthology')},
                         {'title':'Book','author':'Author Name','series':'','number':'','universe':'','anthology':False},'the saved draft keeps its names')
        self.assertEqual(fresh['review']['narrator'],'New reader','the other fields are saved')
        with connect(self.inventory.database) as db:latest=manual_metadata.records(db,fresh)[-1]
        self.assertFalse(set(latest['values'])&{'title','author','series','number','universe','anthology'},latest['values'])
        self.assertEqual(latest['values'].get('narrator'),'New reader')

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

    def test_shifted_file_ids_with_identical_content_are_not_a_change(self):
        # v0.16.9 ("Cabal"): the share reported other file IDs later; the bytes match the frozen hash exactly.
        row=self.ready();before=self.service.build_manifest('Audiobooks',row['id'],row['revision'])
        with connect(self.inventory.database) as db:
            data=db.execute('SELECT data FROM candidate_context WHERE id=?',(row['id'],)).fetchone()[0]
            ctx=json.loads(data)
            for saved in ctx['source_hashes'].values():saved['dev']+=1;saved['ino']+=7
            db.execute('UPDATE candidate_context SET data=? WHERE id=?',(json.dumps(ctx),row['id']))
        fresh=self.service.enrich(self.service._row('Audiobooks',row['id'],row['revision']))
        self.assertTrue(fresh['creation']['can_create'],fresh['creation']['reasons']);self.assertNotIn('Source changed — review required',fresh['creation']['reasons'])
        after=self.service.build_manifest('Audiobooks',row['id'],row['revision'])
        self.assertEqual({k:v for k,v in after.items() if k!='job_id'},{k:v for k,v in before.items() if k!='job_id'},'the frozen manifest is the same, so the job guard passes')
        # The content still decides: same size and time with other bytes, or another size, is a change.
        path=self.sources[0];stat=path.stat();data=path.read_bytes()
        path.write_bytes(b'X'+data[1:]);os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        with self.assertRaisesRegex(ValueError,'Source changed'):self.service.build_manifest('Audiobooks',row['id'],row['revision'])
        path.write_bytes(data+b'longer')
        with self.assertRaisesRegex(ValueError,'Source changed'):self.service.build_manifest('Audiobooks',row['id'],row['revision'])
        self.assertIn('Source changed — review required',self.service.enrich(self.service._row('Audiobooks',row['id'],row['revision']))['creation']['reasons'])

    def test_single_existing_m4b_never_ready_for_concatenation(self):
        for path in self.sources:path.unlink()
        new=self.sources[0].with_suffix('.m4b');new.write_bytes(b'private existing audiobook')
        self.inventory.launch('Audiobooks');finish_scan(self.inventory)
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

    def test_completion_flag_uses_exact_single_authority_snapshot(self):
        row=self.ready();identity=row['id']
        other=Path(self.roots['Audiobooks'])/'Another';other.mkdir()
        (other/'01.mp3').write_bytes(b'another private recording')
        self.inventory.launch('Audiobooks');finish_scan(self.inventory)
        job={'job_id':'fixture','state':'completed','stage':'published','reason':'','manifest':{'candidate_id':identity,'cleanup_policy':{'enabled':True}}}
        authority=Mock(return_value={'converted_ids':{identity}})
        self.service.jobs=SimpleNamespace(progress_books=authority,
            jobs=SimpleNamespace(status=lambda:{'jobs':[job]}),cleanup=SimpleNamespace(status=lambda _id:None,root=self.base/'recovery'),
            candidate_status=lambda id:{'state':'Audiobook created'} if id==identity else None)
        page=self.service.page()
        self.assertEqual(len(page['rows']),2)
        self.assertEqual({r['id']:r['audiobook_ready'] for r in page['rows']},{r['id']:r['id']==identity for r in page['rows']})
        authority.assert_called_once_with()
        self.assertTrue(self.service.enrich(self.service._row('Audiobooks',identity))['audiobook_ready'])
        authority.return_value={'converted_ids':set()}
        self.sources[0].write_bytes(b'changed source after authority snapshot')
        fresh=self.service.enrich(self.service._row('Audiobooks',identity))
        self.assertFalse(fresh['audiobook_ready'])
        self.assertIn('Source changed',fresh['creation']['reasons'][0])


if __name__=='__main__':unittest.main()
