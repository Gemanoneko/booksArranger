"""Ready compatibility requires the exact current reviewed hierarchy binding."""
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
import test_progress as fixture
from conversion_progress import completed_book
from publication_locations import _digest,publication_id
from organization import plan,POLICY
from review_backend import member_key,CandidateReviewService
from encoding_policy import PROFILE

class RelocationReadyTests(unittest.TestCase):
    def setUp(self):
        f=fixture.CompletionTests();f.setUp();self.row=f.row;self.ctx=f.ctx;self.job=f.job
        self.old=str(fixture.AREA/'old');self.new=str(fixture.AREA/'sorted')
        review={'title':'Book','author':'Author','canonical_author':'Author','series':'Cycle','number':'1','multi_author':False,'anthology':False}
        self.row.update(review=copy.deepcopy(review),fingerprint='source-fixture')
        self.job['manifest'].update(job_id=self.job['job_id'],metadata=copy.deepcopy(review),root=self.old,destination=str(Path(self.old)/'original.m4b'))
        self.job['output'].update(root=self.old,final_path=self.job['manifest']['destination'],sha256='a'*64,size=24,parent_identity=[[self.old,1,0,1]])
        self.row['preview']['path']=self.job['output']['final_path']
    def binding(self):
        route=plan(self.new,self.row['review']);original=self.job['output'];manifest=self.job['manifest']
        return {'original_receipt':copy.deepcopy(original),'publication_id':publication_id(self.job['job_id'],'base',original),
          'relocation':{'publication_kind':'base','job_id':self.job['job_id'],'candidate_id':self.row['id'],'source_fingerprint':self.row['fingerprint'],
           'immutable_receipt_sha256':_digest(original),'original_manifest_hash':_digest(manifest),'target_root':self.new,'planned_destination':route['path'],
           'accepted_routing_json':json.dumps({'routing_policy_version':POLICY,'accepted_candidate_revision':self.row['revision'],'accepted_review_sha256':_digest(self.row['review'])})}}
    def ready(self,envelope=None,current=True):
        done={'state':'completed'}
        return completed_book(self.row,self.ctx,self.job,done,done,done,current,member_key,PROFILE,location_envelope=envelope)
    def upgrade(self):
        self.row['revision']+=1;self.row['review'].update(universe='Recorded Universe',organization_policy=POLICY)
        self.row['preview']['path']=plan(self.new,self.row['review'])['path']
    def test_unmigrated_legacy_remains_ready_when_global_output_root_changes(self):
        service=CandidateReviewService.__new__(CandidateReviewService)
        service.inventory=SimpleNamespace(roots={'Audiobooks':self.old},output_root=self.new)
        row=dict(self.row,source_root=self.old)
        self.assertEqual(service._output_root(row),self.old)
        self.assertTrue(self.ready())
    def test_reviewed_routing_upgrade_needs_exact_binding_to_stay_ready(self):
        self.upgrade();self.assertFalse(self.ready());envelope=self.binding();self.assertTrue(self.ready(envelope))
        self.assertFalse(self.ready(envelope,current=False))
    def test_unrelated_preview_path_cannot_be_waived(self):
        self.upgrade();envelope=self.binding();self.row['preview']['path']=str(Path(self.new)/'unreviewed.m4b')
        self.assertFalse(self.ready(envelope))
    def test_changed_canonical_title_is_not_a_routing_upgrade(self):
        self.upgrade();self.row['review']['title']='Another work';self.row['preview']['path']=plan(self.new,self.row['review'])['path']
        self.assertFalse(self.ready(self.binding()))
    def test_stale_revision_fingerprint_and_receipt_cannot_waive_mismatch(self):
        self.upgrade();original=self.binding()
        for mutate in ('revision','fingerprint','receipt'):
            with self.subTest(mutate=mutate):
                envelope=copy.deepcopy(original)
                if mutate=='revision':
                    routing=json.loads(envelope['relocation']['accepted_routing_json']);routing['accepted_candidate_revision']-=1;envelope['relocation']['accepted_routing_json']=json.dumps(routing)
                elif mutate=='fingerprint':envelope['relocation']['source_fingerprint']='changed'
                else:envelope['original_receipt']['size']+=1
                self.assertFalse(self.ready(envelope))
