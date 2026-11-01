"""Remaining 0.24.2 consumers: no media, network, app, or source access."""
import copy
import hashlib
import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from audio_jobs import _failure_details
from audio_pipeline import ChapterValidationError
from automatic_processing import AutomaticProcessing
from merge_service import MergeService
from organization import frozen_plan
from publication_locations import _digest
from reviewed_routing import for_relocation
from shared_routing import build, resolve
from web_server import BrowserServer


class IntegrationTests(unittest.TestCase):
    def chapter_error(self):
        error=ChapterValidationError({'file':'Part 2.m4b','path':'private/Part 2.m4b','chapter_index':2,'chapter_id':3,'chapter_title':'Final','predicate':'end_exceeds_audio','start':10,'end':500,'duration':20})
        error.admission_error={'chapter_diagnostic':error.chapter_diagnostic}
        return error

    def queued(self,error,origin='unknown'):
        merge=SimpleNamespace(approve_book=Mock(side_effect=error),candidate_status=lambda identity:{'job_origin':origin})
        server=SimpleNamespace(merge=merge,actions=SimpleNamespace(blocker=lambda *a,**kw:None))
        return BrowserServer.run_queued(server,{'action':'approve','book_id':'book','args':{'revision':1}})

    def test_queued_chapter_refusal_keeps_exact_source_predicate(self):
        error=self.chapter_error();answer=self.queued(error)
        self.assertEqual(answer['result'],'refused')
        self.assertEqual(answer['admission_error']['chapter_diagnostic'],error.chapter_diagnostic)
        self.assertEqual(answer['admission_error']['chapter_diagnostic']['file'],'Part 2.m4b')

    def test_queued_running_refusal_reports_immutable_origin(self):
        for origin in ('user','automatic','unknown'):
            with self.subTest(origin=origin):
                answer=self.queued(ValueError('This book is already converting. Your new names were not applied.'),origin)
                self.assertEqual((answer['code'],answer['job_origin']),('book_converting',origin))

    def test_typed_chapter_job_failure_retains_diagnostic_not_retry_authority(self):
        error=self.chapter_error();failure=_failure_details(error,'checking sources',now=1)
        self.assertEqual(failure['chapter_diagnostic'],error.chapter_diagnostic)
        self.assertFalse(failure['retryable'])
        error.chapter_diagnostic['predicate']='changed afterwards'
        self.assertEqual(failure['chapter_diagnostic']['predicate'],'end_exceeds_audio')

    def test_saved_names_hold_is_current_and_does_not_invent_membership_uncertainty(self):
        automatic=object.__new__(AutomaticProcessing)
        row={'id':'book','revision':4,'fingerprint':'same','review':None}
        context={'names_approval_pending':{'revision':4,'fingerprint':'same'}}
        automatic.merge=SimpleNamespace(reviews=SimpleNamespace(_context=lambda row:context))
        self.assertTrue(automatic.names_approval_pending(row));self.assertTrue(automatic._manual_draft(row))
        self.assertFalse(automatic.names_approval_pending(dict(row,revision=5)))
        self.assertFalse(automatic.names_approval_pending(dict(row,fingerprint='changed')))

    def test_terminal_audio_activity_maps_to_supported_job_stage(self):
        merge=object.__new__(MergeService)
        merge._require_sorted=Mock(side_effect=ValueError('private destination'))
        merge.stage_root='private';merge.working=None
        diagnostic={'reason':'terminal_chapter_end','chapter_title':'Final'};seen=[]
        class FinishedProof(Exception):pass
        def media(manifest,stage,stop,progress,**kw):
            progress('Checking source audio',{'chapter_check':diagnostic})
            raise FinishedProof()
        with patch('merge_service.create_private',side_effect=media):
            with self.assertRaises(FinishedProof):merge._run_media({'destination':'private/book.m4b'},threading.Event(),lambda stage,info:seen.append((stage,info)))
        self.assertEqual(seen,[('checking sources',{'chapter_check':diagnostic})])

    def routing_fixture(self):
        review={'title':'The Omen','canonical_author':'David Seltzer','series':'Omen','number':'1','universe':''}
        facts={'source_fingerprint':'source-one','work_ids':['catalog:book-1'],'authors':['David Seltzer']}
        series={'id':'catalog:omen','name':'Omen','basis':'catalog','evidence':['catalog:omen'],
                'members':[{'work_id':'catalog:book-1','authors':['David Seltzer']},{'work_id':'catalog:book-2','authors':['Joseph Howard']}]}
        facts['shared_routing']=build(review,facts,series=series)
        manifest={'candidate_id':'book','metadata':review,'metadata_facts':facts}
        target=dict(review,universe='A confirmed world')
        decision={'actor':'user','evidence':'Explicit reviewed move','candidate_id':'book','review_sha256':_digest(review),
                  'fingerprint':'source-one','values':{'universe':'A confirmed world'}}
        return manifest,target,decision

    def test_explicit_world_relocation_rebinds_shared_series_without_history_mutation(self):
        manifest,review,decision=self.routing_fixture();before=copy.deepcopy(manifest)
        planned=for_relocation(manifest,review,[decision])
        self.assertTrue(resolve(review,planned['metadata_facts'])['multi_author_series'])
        self.assertEqual(manifest,before);self.assertIsNot(planned,manifest)
        self.assertEqual(frozen_plan(planned,'C:/private/sorted',review)['accepted_routing']['universe'],'A confirmed world')

    def test_relocation_rejects_missing_stale_or_broader_decisions(self):
        manifest,review,decision=self.routing_fixture()
        for evidence,target in (([],review),([dict(decision,fingerprint='other')],review),([dict(decision,review_sha256='other')],review),([decision],dict(review,title='Another work'))):
            with self.subTest(evidence=evidence,target=target):
                with self.assertRaises(ValueError):for_relocation(manifest,target,evidence)

    def test_unchanged_shared_route_keeps_exact_frozen_manifest(self):
        manifest,review,decision=self.routing_fixture()
        self.assertIs(for_relocation(manifest,manifest['metadata'],[]),manifest)
        manifest['metadata_facts']['shared_routing']['binding']['source_fingerprint']='stale'
        with self.assertRaises(ValueError):for_relocation(manifest,manifest['metadata'],[])

    def test_joined_part_fingerprints_feed_frozen_recording_route(self):
        review={'title':'Book','canonical_author':'Author Name','series':'','number':'','universe':''}
        parts=[{'name':'First','chapters':[{'start':0,'end':1000,'title':'One'}]}, {'name':'Second','chapters':[{'start':0,'end':2000,'title':'Two'}]}]
        sources=[{'path':'C:/private/one.m4b','sha256':'a'*64,'size':10},{'path':'C:/private/two.m4b','sha256':'b'*64,'size':20}]
        facts={'destination_suffix':'Edition','recording_chapter_policy':'joined-chapters-v1','work_ids':['catalog:work'],'recording_language':{'value':'en','basis':'embedded'}}
        manifest={'candidate_id':'book','metadata':review,'metadata_facts':facts,'sources':sources,'part_chapters':parts}
        seen=[]
        with patch('recording_classification.destination_suffix',side_effect=lambda value:seen.append(value) or 'Edition'), patch('organization.append_recording_suffix',side_effect=lambda path,*a:path):
            frozen_plan(manifest,'C:/private/sorted')
        expected=[hashlib.sha256(json.dumps(part['chapters'],sort_keys=True,separators=(',',':')).encode()).hexdigest() for part in parts]
        self.assertEqual([track['chapter_sha256'] for track in seen[0]['manifest']['tracks']],expected)

    def real_recording_manifest(self,policy=None):
        from recording_classification import destination_suffix
        review={'title':'Book','canonical_author':'Author Name','series':'','number':'','universe':'','narrator':'Reader'}
        parts=[{'name':'First','chapters':[{'start':0,'end':1000,'title':'One'}]},{'name':'Second','chapters':[{'start':0,'end':2000,'title':'Two'}]}]
        sources=[{'path':'C:/private/one.m4b','sha256':'a'*64,'size':10},{'path':'C:/private/two.m4b','sha256':'b'*64,'size':20}]
        tracks=[{'source_sha256':source['sha256'],'size_bytes':source['size'],'chapter_sha256':hashlib.sha256(json.dumps(parts[index]['chapters'] if policy else [],sort_keys=True,separators=(',',':')).encode()).hexdigest()} for index,source in enumerate(sources)]
        candidate={'id':'book','identity_verified':True,'work_ids':['catalog:work'],'collection_kind':'single','series_volume':None,'narrator':{'value':'Reader','verified':True},'recording_language':{'value':'en','verified':True},'edition':{'value':'','verified':False},'manifest':{'complete':True,'observed_count':2,'tracks':tracks}}
        facts={'destination_suffix':destination_suffix(candidate),'policy_version':'standing-17-v1','source_fingerprint':'files','authors':['Author Name'],'work_ids':['catalog:work'],'recording_language':{'value':'en','basis':'embedded'}}
        if policy:facts['recording_chapter_policy']=policy
        return {'candidate_id':'book','metadata':review,'metadata_facts':facts,'sources':sources,'part_chapters':parts}

    def test_legacy_joined_recording_keeps_exact_destination_and_receipt(self):
        from organization import plan
        manifest=self.real_recording_manifest();before=copy.deepcopy(manifest)
        old_destination=plan('C:/private/sorted',manifest['metadata'],facts=manifest['metadata_facts'])['path']
        self.assertEqual(frozen_plan(manifest,'C:/private/sorted')['path'],old_destination)
        self.assertEqual(manifest,before)

    def test_new_joined_recording_checks_chapters_and_refuses_downgrade(self):
        manifest=self.real_recording_manifest('joined-chapters-v1')
        self.assertIn(manifest['metadata_facts']['destination_suffix'],frozen_plan(manifest,'C:/private/sorted')['path'])
        changed=copy.deepcopy(manifest);changed['part_chapters'][1]['chapters'][0]['end']+=1
        with self.assertRaisesRegex(ValueError,'suffix differs'):frozen_plan(changed,'C:/private/sorted')
        del manifest['metadata_facts']['recording_chapter_policy']
        with self.assertRaisesRegex(ValueError,'suffix differs'):frozen_plan(manifest,'C:/private/sorted')

    def test_unknown_recording_policy_does_not_fall_back_to_legacy(self):
        manifest=self.real_recording_manifest();manifest['metadata_facts']['recording_chapter_policy']='future-or-malformed'
        with self.assertRaisesRegex(ValueError,'Unsupported frozen'):frozen_plan(manifest,'C:/private/sorted')

    def test_new_distinct_recording_binds_chapter_policy_at_producer(self):
        merge=object.__new__(MergeService)
        merge.reviews=SimpleNamespace(source_chapter_plan=lambda *a,**kw:{'chapters':[]},_context=lambda row:{},_write=lambda *a,**kw:None)
        merge.jobs=SimpleNamespace(status=lambda:{'jobs':[]})
        row={'id':'book','members':[{'path':'C:/private/one.m4b','size':1,'modified':'time'},{'path':'C:/private/two.m4b','size':1,'modified':'time'}]}
        result={'review':{},'metadata_facts':{'work_ids':['catalog:work']}}
        with patch('merge_service.digest',return_value='a'*64),patch('recording_classification.classify_recording',return_value={'classification':'related_distinct','hold':False,'destination_suffix':'proof'}):
            merge._recording_review(row,result,threading.Event())
        self.assertEqual(result['metadata_facts']['recording_chapter_policy'],'joined-chapters-v1')


    def test_name_save_replans_exact_pending_job_with_truthful_hold_and_new_names(self):
        import tempfile,uuid
        from pathlib import Path
        import entered_names,groups
        from audio_jobs import AudioJobs
        from scanner import connect
        area=Path(__file__).resolve().parents[1]/'scratch'/'integration-242-names';area.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=area) as tmp:
            identity=str(uuid.uuid4());other_identity=str(uuid.uuid4())
            database=Path(tmp)/'catalog.sqlite3';jobs=AudioJobs(database,None,lambda manifest:True,lambda output:False)
            row={'id':identity,'revision':2,'fingerprint':'files','members':[{'path':str(Path(tmp)/'book.m4b'),'metadata':{}}]}
            context={'user_approval':{'values':{'title':'Old approved title','author':'Writer'}}}
            with connect(database) as db:
                groups.setup(db)
                db.execute('CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT)')
                db.execute('CREATE TABLE automatic_candidates(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,state TEXT,result TEXT,retry_at REAL,attempted TEXT,matcher_version TEXT)')
                db.execute('INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence,review,approved,changed) VALUES(?,?,?,?,?,?,?,?,?)',(identity,tmp,tmp,2,'files',json.dumps({'members':row['members']}),json.dumps({'title':'Old approved title'}),1,0))
                db.execute('INSERT INTO candidate_context VALUES(?,?,?)',(identity,2,json.dumps(context)))
            def manifest(name):return {'job_id':str(uuid.uuid4()),'candidate_id':identity if name=='book' else other_identity,'candidate_revision':2,'root':tmp,'sources':[{'path':row['members'][0]['path'],'sha256':'a'*64,'size':1,'fingerprint':{'size':1,'modified':1}}],'metadata':{'title':'Old approved title'},'destination':str(Path(tmp)/(name+'.m4b')),'profile':'p','evidence':{},'cover':{},'cleanup_policy':{'enabled':False}}
            selected=jobs.enqueue(manifest('book'));other=jobs.enqueue(manifest('other'))
            def job_row(identity):
                with connect(database) as db:return dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(identity,)).fetchone())
            before_other=job_row(other)
            merge=object.__new__(MergeService);merge.draining=False;merge.inventory=SimpleNamespace(database=database);merge.jobs=jobs
            def current_context(value):
                with connect(database) as db:return json.loads(db.execute('SELECT data FROM candidate_context WHERE id=?',(value['id'],)).fetchone()[0])
            merge.reviews=SimpleNamespace(_row=lambda *a:row,_context=current_context,_source_root=lambda value:tmp)
            merge.automatic=SimpleNamespace(research=object(),requeue=Mock(),request_start=Mock())
            merge._his_revision=lambda *a:2;merge._names_book=lambda *a:(row,tmp,merge.automatic.research)
            merge._names_state=lambda *a:({'title':'Old approved title','author':'Writer'},'',{key:{'value':value} for key,value in entered_names.book_values(database,row).items()},None)
            merge._names_others=lambda *a:[];merge.invalidate_status=Mock();merge._press_after=lambda *a,**kw:{}
            answer=merge.names_save(identity,2,{'title':'A newly chosen title'},fingerprint='files')
            self.assertEqual(answer['outcome'],'replanned')
            self.assertEqual(entered_names.book_values(database,row)['title'],'A newly chosen title')
            self.assertEqual(current_context(row)['names_approval_pending'],{'revision':2,'fingerprint':'files'})
            with connect(database) as db:
                held=db.execute('SELECT state,result FROM automatic_candidates WHERE id=?',(identity,)).fetchone()
                self.assertEqual(held['state'],'Held')
                self.assertEqual(json.loads(held['result'])['reasons'],['Names saved — waiting for your approval.'])
                self.assertEqual(db.execute('SELECT kind FROM audio_job_set_aside WHERE job_id=?',(selected,)).fetchone()[0],'names')
            self.assertEqual(job_row(other),before_other)
            self.assertEqual(job_row(selected)['state'],'needs attention')


if __name__=='__main__':unittest.main()
