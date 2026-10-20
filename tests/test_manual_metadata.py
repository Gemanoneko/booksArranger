import os
import sqlite3
import unittest
import manual_metadata as m

class ManualMetadataTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close);m.initialize(self.db)
        self.row={'id':'book-a','fingerprint':'source-v1'}
    def save(self,values,note='Credits checked'):
        m.append(self.db,m.capture(self.row,values,note));return m.records(self.db,self.row)
    def test_draft_deletion_and_restart_preserve_source(self):
        self.db.execute('CREATE TABLE candidate_context(id TEXT PRIMARY KEY,data TEXT)')
        self.db.execute('INSERT INTO candidate_context VALUES(?,?)',('book-a','draft'))
        self.save({'title':'Book','canonical_author':'Author'})
        self.db.execute('DELETE FROM candidate_context');m.initialize(self.db)
        self.assertEqual(m.records(self.db,self.row)[0]['values']['title'],'Book')
    def test_new_binding_marks_stale_and_never_reuses_as_proposal(self):
        self.save({'title':'Book'});self.row['fingerprint']='different-source'
        records=m.records(self.db,self.row)
        self.assertEqual(records[0]['status'],'stale');self.assertEqual(m.proposals(records),[])
    def test_missing_optional_fields_are_not_conflicts(self):
        own=m.proposals(self.save({'title':' Book ','series':'','original_language':'Unknown'}))
        self.assertNotIn('original_language',own[0]['per_field_evidence']['values'])
        self.assertEqual(m.compare(own,[{'title':'book','series':'A cycle'}]),[])
    def test_conflicting_source_stays_explicit_without_override(self):
        own=m.proposals(self.save({'title':'Book','canonical_author':'Writer A'}))
        other=[{'id':'public-1','title':'Book','authors':['Writer B']}]
        conflicts=m.compare(own,other)
        self.assertEqual(len(conflicts),1);self.assertEqual(conflicts[0]['field'],'authors');self.assertEqual(conflicts[0]['manual_value'],'Writer A');self.assertEqual(conflicts[0]['other_value'],'Writer B');self.assertEqual(conflicts[0]['other_source_id'],'public-1');self.assertEqual(conflicts[0]['manual_source_id'],own[0]['id'])
        self.assertEqual(other[0]['authors'],['Writer B'])
    def test_resave_deduplicates_but_change_retains_history(self):
        self.save({'title':'Book'});self.save({'title':'Book'})
        self.assertEqual(len(m.records(self.db,self.row)),1)
        self.save({'title':'New book title'});records=m.records(self.db,self.row)
        self.assertEqual(len(records),2);self.assertEqual(m.proposals(records)[0]['title'],'New book title')
    def test_empty_boolean_does_not_claim_standalone_or_no_universe(self):
        own=self.save({'title':'Book','multi_author':False,'anthology':False})
        self.assertEqual(own[0]['values'],{'title':'Book'})



    def test_explicit_user_acceptance_is_bound_to_metadata_and_source(self):
        row=dict(self.row,review={'title':'Book','canonical_author':'Writer'})
        ctx={'metadata_approved':True,'metadata_actor':'user','manual_note':'Credits checked','manual_metadata_acceptance':m.acceptance(row,row['review'])}
        self.assertTrue(m.approved(row,ctx));self.assertFalse(m.approved(dict(row,fingerprint='new-source'),ctx))
        self.assertFalse(m.approved(dict(row,review={'title':'Different'}),ctx))
        self.assertFalse(m.approved(row,dict(ctx,metadata_actor='assistant')))

class CandidateEvidenceIntegration(unittest.TestCase):
    def test_saved_source_survives_canonical_clear_and_changed_binding(self):
        import json
        import os
        import tempfile
        from pathlib import Path
        from scanner import Inventory,connect
        from review_backend import CandidateReviewService
        area=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'manual-evidence-tests'
        area.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=area) as temp:
            base=Path(temp);audio=base/'audio';audio.mkdir();(audio/'book.mp3').write_bytes(b'private synthetic fixture')
            roots={'Audiobooks':str(audio),'Podcasts':str(base/'podcasts'),'Ebooks':str(base/'ebooks')}
            def reader(path,kind,stop):return {'title':'Book','track_title':'Book','tags':{'album':'Book'},'method':'fixture'}
            inventory=Inventory(base/'catalog.sqlite3',roots,reader);inventory.launch('Audiobooks');inventory.worker.join(5)
            service=CandidateReviewService(inventory,base/'cover-cache');row=service.page()['rows'][0]
            review={'title':'Entered book','canonical_author':'Writer','original_language':'Other'}
            saved=service.save('Audiobooks',row['id'],row['revision'],review,False,'Credits checked')
            self.assertEqual(saved['manual_metadata_sources'][-1]['values']['title'],'Entered book')
            from types import SimpleNamespace
            service.client=SimpleNamespace(lookup=lambda *args:[{'title':'Different book','authors':['Writer'],'public_url':'https://publisher.example/book'}])
            service.match('Audiobooks',saved['id'],saved['revision']);service.workers[saved['id']].join(5)
            matched=service.page()['rows'][0]
            self.assertTrue(matched['matching']['proposals'][0]['manual_source'])
            self.assertEqual(matched['matching']['conflicts'][0]['field'],'title')
            self.assertFalse(matched['metadata_approved'])
            def unavailable(*args):raise RuntimeError('Provider offline')
            service.client=SimpleNamespace(lookup=unavailable)
            service.match('Audiobooks',saved['id'],saved['revision']);service.workers[saved['id']].join(5)
            self.assertTrue(service.page()['rows'][0]['matching']['proposals'][0]['manual_source'])
            with connect(inventory.database) as db:
                db.execute('DELETE FROM candidate_context WHERE id=?',(row['id'],))
                db.execute('UPDATE book_groups SET review=? WHERE id=?',('',row['id']))
            restarted=CandidateReviewService(inventory,base/'cover-cache')
            fresh=restarted.page()['rows'][0]
            self.assertEqual(fresh['manual_metadata_sources'][-1]['values']['title'],'Entered book')
            self.assertFalse(fresh['review_context']['source_coverage_confirmed'])


    def test_single_m4b_requires_explicit_metadata_acceptance_and_keeps_media_gate(self):
        import base64
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from scanner import Inventory
        from review_backend import CandidateReviewService
        from encoding_policy import AUTOMATIC_PROFILE
        area=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'manual-evidence-tests';area.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=area) as temp:
            base=Path(temp);audio=base/'audio';audio.mkdir();(audio/'book.m4b').write_bytes(b'synthetic manifest admission fixture, not real audio')
            (audio/'cover.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='))
            roots={'Audiobooks':str(audio),'Podcasts':str(base/'podcasts'),'Ebooks':str(base/'ebooks')}
            def reader(path,kind,stop):return {'title':'Book','track_title':'Book','tags':{'album':'Book'},'method':'fixture','probe':{'format':{'duration':'1.0'}}}
            inv=Inventory(base/'catalog.sqlite3',roots,reader);inv.launch('Audiobooks');inv.worker.join(5)
            service=CandidateReviewService(inv,base/'cache');row=service.page()['rows'][0]
            row=service.covers('Audiobooks',row['id'],row['revision']);cover=row['cover_choices'][0]['id']
            review={'title':'Book','author':'Writer','canonical_author':'Writer','original_language':'Other'}
            draft=service.save('Audiobooks',row['id'],row['revision'],review,False,'Credits checked',cover_id=cover)
            self.assertIn('Single audiobook file',draft['creation']['reasons'])
            accepted=service.save('Audiobooks',draft['id'],draft['revision'],review,True,'Credits checked',cover_id=cover)
            self.assertFalse(accepted['creation']['can_create'])  # tracks still unconfirmed
            accepted=service.tracks('Audiobooks',accepted['id'],accepted['revision'],accepted['track_order'],accepted['included'],True,True,False,evidence_note='Reviewed exact original recording')
            self.assertTrue(accepted['creation']['can_create'],accepted['creation']['reasons'])
            with patch('audio_pipeline.source_chapters',return_value=[]) as chapters:
                manifest=service.build_manifest('Audiobooks',accepted['id'],accepted['revision'])
            chapters.assert_called_once();self.assertEqual(manifest['profile'],AUTOMATIC_PROFILE)
            self.assertNotIn('metadata_facts',manifest)
            self.assertEqual(manifest['evidence']['metadata_actor'],'user')
            self.assertEqual(manifest['source_chapters'],[])
            self.assertFalse(manifest['cleanup_policy']['enabled'])  # preserve original by existing manual policy



    def test_titleless_collection_uses_accepted_universe_through_review_and_manifest(self):
        import base64
        import tempfile
        from pathlib import Path
        from scanner import Inventory
        from review_backend import CandidateReviewService
        area=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'manual-evidence-tests';area.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=area) as temp:
            base=Path(temp);audio=base/'audio';audio.mkdir();output=base/'sorted';output.mkdir()
            (audio/'source.mp3').write_bytes(b'synthetic source scope fixture')
            (audio/'cover.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='))
            roots={'Audiobooks':str(audio),'Podcasts':str(base/'podcasts'),'Ebooks':str(base/'ebooks')}
            def reader(path,kind,stop):return {'title':'Unverified source label','track_title':'Track','tags':{'album':'Source collection'},'method':'fixture','probe':{'format':{'duration':'1.0'}}}
            inv=Inventory(base/'catalog.sqlite3',roots,reader,output_root=str(output));inv.launch('Audiobooks');inv.worker.join(5)
            service=CandidateReviewService(inv,base/'cache');row=service.page()['rows'][0];row=service.covers('Audiobooks',row['id'],row['revision'])
            review={'title':'','canonical_author':'Writer','author':'Writer','original_language':'Other','anthology':True,'universe':'Verified Universe','series':'','number':''}
            row=service.save('Audiobooks',row['id'],row['revision'],review,True,'Reviewed universe collection credits; no separate book title',cover_id=row['cover_choices'][0]['id'])
            self.assertTrue(row['can_approve'],row['approval_reason']);self.assertEqual(row['review']['title'],'')
            self.assertEqual(row['preview']['path'],str(output/'Verified Universe'/'Verified Universe - Short Stories.m4b'))
            row=service.tracks('Audiobooks',row['id'],row['revision'],row['track_order'],row['included'],True,True,False,evidence_note='Exact source collection/order reviewed')
            manifest=service.build_manifest('Audiobooks',row['id'],row['revision'])
            self.assertEqual(manifest['root'],str(audio));self.assertEqual(manifest['output_root'],str(output))
            self.assertEqual(manifest['metadata']['title'],'');self.assertEqual(manifest['metadata']['canonical_author'],'Writer')
            self.assertEqual(manifest['destination'],str(output/'Verified Universe'/'Verified Universe - Short Stories.m4b'))

if __name__=='__main__':unittest.main()
