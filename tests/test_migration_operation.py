"""Private operator ownership/scope checks; no migration side effects."""
import copy
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from catalog_owner import catalog_lock
from migration_operation import MigrationOperation,PLAN_SCHEMA,policy_roots,catalog_identity_lease
import publication_locations as p
import test_publication_locations as fixture

class MigrationOperationTests(unittest.TestCase):
    def setUp(self):
        area=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'migration-operation';area.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=area);self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
        data=self.base/'data';data.mkdir();self.database=data/'catalog.sqlite'
        f=fixture.PublicationLocationsTests();f.setUp();self.addCleanup(f.doCleanups);self.f=f
        review={'title':'Book'};f.manifest.update(metadata=review,cover={'id':'cover'},sources=[{'path':str(Path(f.root)/'source.mp3'),'sha256':'a'*64,'size':1,'modified':'1'}]);f.job['manifest']=p._packed(f.manifest);f.job['manifest_hash']=p._digest(f.manifest);f.store_job();f.routing.update(accepted_candidate_revision=3,accepted_review_sha256=p._digest(review))
        migration=f.plan();f.db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,superseded INTEGER,changed INTEGER,fingerprint TEXT,revision INTEGER,review TEXT)')
        f.db.execute('CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT)')
        f.db.execute('CREATE TABLE source_cleanup(job_id TEXT,state TEXT)')
        f.db.execute('INSERT INTO book_groups VALUES(?,?,?,?,?,?)',(f.manifest['candidate_id'],0,0,'source-fingerprint',3,json.dumps(review)))
        f.db.execute('INSERT INTO candidate_context VALUES(?,?,?)',(f.manifest['candidate_id'],3,json.dumps({'metadata_approved':True,'source_coverage_confirmed':True,'order_confirmed':True,'included':[__import__('review_backend').member_key(f.manifest['sources'][0]['path'])],'track_order':[__import__('review_backend').member_key(f.manifest['sources'][0]['path'])],'source_hashes':{__import__('review_backend').member_key(f.manifest['sources'][0]['path']):{'sha256':'a'*64,'size':1,'modified':'1'}},'cover_id':'cover'})))
        f.db.commit();db=sqlite3.connect(self.database);f.db.backup(db);db.close()
        self.pubid=migration['publication_id'];self.policy={'legacy_roots':{'Audiobooks':f.root},'audiobook_sources':[f.root],'audiobook_output_root':f.target};self.roots=policy_roots(self.policy)
        with catalog_identity_lease(self.database) as native_identity:self.native_identity=native_identity
        self.plan={'schema':PLAN_SCHEMA,'database':str(self.database),'roots':self.roots,'source_policy':self.policy,'source_policy_sha256':p._digest(self.policy),'catalog_identity':self.native_identity,'planning_inputs':{'configuration_sha256':p._digest({'database':str(self.database),**self.policy}),'routing_decisions_sha256':p._digest([])},'publications':[{'publication_id':self.pubid,'candidate_id':f.manifest['candidate_id'],'source':f.original['final_path'],'destination':f.destination,'size':f.original['size'],'kind':'base','frozen_binding_sha256':p._digest(p._frozen(migration))}]}
        self.path=self.base/'reviewed-plan.json';raw=json.dumps(self.plan).encode();self.path.write_bytes(raw);self.sha=hashlib.sha256(raw).hexdigest()
        self.operation=MigrationOperation(self.database,self.roots,self.path,self.sha)
    def test_native_owner_and_same_transaction_generation_guard(self):
        with self.operation.operation_lease(self.pubid) as lease:
            self.assertTrue(lease['drained']);self.assertTrue(lease['native_owner']['owner_handle_proof']['held'])
            self.assertFalse(lease['generation_guard'](self.pubid,0))
            lease['db'].execute('BEGIN IMMEDIATE');self.assertTrue(lease['generation_guard'](self.pubid,0));lease['db'].rollback()
            with self.assertRaises(Exception):
                with catalog_lock(self.database,self.roots):pass
        with catalog_lock(self.database,self.roots):pass
    def test_changed_plan_and_out_of_scope_publication_refused(self):
        with self.assertRaisesRegex(ValueError,'outside'):
            with self.operation.operation_lease('not-in-review'):pass
        self.path.write_text('changed')
        with self.assertRaisesRegex(ValueError,'plan changed'):
            with self.operation.operation_lease(self.pubid):pass
    def test_running_producer_and_changed_book_preserved(self):
        with contextlib.closing(sqlite3.connect(self.database)) as db:db.execute("UPDATE audio_jobs SET state='running'");db.commit()
        with self.assertRaisesRegex(ValueError,'Drain running'):
            with self.operation.operation_lease(self.pubid):pass
        with contextlib.closing(sqlite3.connect(self.database)) as db:db.execute("UPDATE audio_jobs SET state='completed'");db.execute("UPDATE book_groups SET fingerprint='changed'");db.commit()
        with self.assertRaisesRegex(ValueError,'source identity changed'):
            with self.operation.operation_lease(self.pubid):pass
    def test_unsealed_historical_media_receipt_is_not_fabricated(self):
        with self.operation.operation_lease(self.pubid):
            with self.assertRaisesRegex(ValueError,'not sealed'):self.operation.media_verify('unused',self.f.original,None)
    def test_scope_does_not_reset_pending_jobs_or_attempts(self):
        before=self.database.read_bytes()
        with self.operation.operation_lease(self.pubid):pass
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            state=db.execute('SELECT state FROM audio_jobs').fetchone()[0]
        self.assertEqual(state,'completed')

    def rewritten(self,plan,roots=None):
        raw=json.dumps(plan).encode();self.path.write_bytes(raw)
        return MigrationOperation(self.database,roots or self.roots,self.path,hashlib.sha256(raw).hexdigest())
    def test_each_reviewable_entry_field_is_authoritative(self):
        for field,value in (('source','C:/different.m4b'),('destination','C:/different-final.m4b'),('kind','Chaptersv2'),('candidate_id','different-candidate'),('size',42)):
            changed=copy.deepcopy(self.plan);changed['publications'][0][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'displayed scope'):
                with self.rewritten(changed).operation_lease(self.pubid):pass
    def test_root_policy_and_native_catalog_identity_are_exact(self):
        changed=copy.deepcopy(self.plan);changed['roots']['Audiobooks']='C:/Unreviewed'
        with self.assertRaisesRegex(ValueError,'roots differ'):
            with self.rewritten(changed).operation_lease(self.pubid):pass
        changed=copy.deepcopy(self.plan);changed['catalog_identity']['ino']+=1
        with self.assertRaisesRegex(ValueError,'native catalog identity'):
            with self.rewritten(changed).operation_lease(self.pubid):pass
        changed=copy.deepcopy(self.plan);changed['source_policy']['audiobook_output_root']='C:/Unreviewed'
        with self.assertRaisesRegex(ValueError,'roots differ'):
            with self.rewritten(changed).operation_lease(self.pubid):pass

    def test_catalog_identity_lease_blocks_path_replacement_and_allows_sqlite_writes(self):
        with catalog_identity_lease(self.database):
            with self.assertRaises(OSError):os.replace(self.database,self.database.with_name('replaced.sqlite'))
            with contextlib.closing(sqlite3.connect(self.database)) as db:
                db.execute('CREATE TABLE identity_writer_probe(value TEXT)');db.commit()
        self.assertTrue(self.database.exists())
    def test_consistent_but_wrong_source_policy_cannot_redirect_hidden_job(self):
        changed=copy.deepcopy(self.plan)
        changed['source_policy']['legacy_roots']['Audiobooks']='C:/Unreviewed'
        changed['source_policy']['audiobook_sources']=['C:/Unreviewed']
        changed['roots']=policy_roots(changed['source_policy']);changed['source_policy_sha256']=p._digest(changed['source_policy'])
        changed['planning_inputs']['configuration_sha256']=p._digest({'database':str(self.database),**changed['source_policy']})
        with self.assertRaisesRegex(ValueError,'source root is outside'):
            with self.rewritten(changed,changed['roots']).operation_lease(self.pubid):pass

    def test_malformed_or_unknown_selection_cannot_be_hidden_in_plan(self):
        for value in ('not-a-list',['unknown-current-candidate']):
            changed=copy.deepcopy(self.plan);changed['verification_selection']=value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'verification selection'):
                with self.rewritten(changed).operation_lease(self.pubid):pass

    def move_operation(self,plan):
        raw=json.dumps(plan).encode();self.path.write_bytes(raw)
        return MigrationOperation(self.database,self.roots,self.path,hashlib.sha256(raw).hexdigest(),strategy='rename')

    def test_native_strategy_requires_explicit_review_and_initial_generation(self):
        with self.assertRaisesRegex(ValueError,'strategy differ'):
            with self.move_operation(self.plan).operation_lease(self.pubid):pass
        plan=copy.deepcopy(self.plan);plan['operation_strategy']=p.RENAME_STRATEGY
        plan['publications'][0].update(move_action='rename',initial_generation=0)
        with self.move_operation(plan).operation_lease(self.pubid) as lease:
            self.assertEqual(lease['move_action'],'rename')
            self.assertEqual(lease['operation_strategy'],'rename')
        for field,value,reason in (('initial_generation',1,'initial stage/generation'),('initial_generation',True,'action/generation'),('move_action','copy','action/generation'),('move_action','remove_verified_duplicate','initial stage/generation')):
            changed=copy.deepcopy(plan);changed['publications'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaisesRegex(ValueError,reason):
                with self.move_operation(changed).operation_lease(self.pubid):pass
        raw=json.dumps(plan).encode();self.path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'strategy differ'):
            with MigrationOperation(self.database,self.roots,self.path,hashlib.sha256(raw).hexdigest()).operation_lease(self.pubid):pass
