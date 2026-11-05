import copy
import unittest

from shared_routing import POLICY, RoutingEvidenceError, build, resolve


class SharedRoutingTests(unittest.TestCase):
    def setUp(self):
        self.review = {'title': 'The Omen', 'author': 'Seltzer David',
                       'canonical_author': 'David Seltzer', 'series': 'Omen', 'number': '1'}
        self.facts = {'source_fingerprint': 'source-one', 'work_ids': ['catalog:book-1'],
                      'authors': ['David Seltzer']}
        self.series = {'id': 'https://example.org/series/omen', 'name': 'Omen',
                       'basis': 'catalog', 'evidence': ['https://example.org/series/omen'],
                       'members': [{'work_id': 'catalog:book-1', 'authors': ['David Seltzer']},
                                   {'work_id': 'catalog:book-2', 'authors': ['Joseph Howard']}]}

    def frozen(self, **kwargs):
        return dict(self.facts, shared_routing=build(self.review, self.facts, **kwargs))

    def test_independently_bound_books_with_distinct_authors_establish_shared_series(self):
        facts = self.frozen(series=self.series)
        self.assertEqual(facts['shared_routing']['policy_version'], POLICY)
        self.assertEqual(resolve(self.review, facts), {'multi_author_series': True, 'shared_world': False})

    def test_one_coauthored_book_does_not_establish_shared_series(self):
        self.review['canonical_author'] = 'David Seltzer; Joseph Howard'
        self.facts['authors'].append('Joseph Howard')
        self.series['members'] = [{'work_id': 'catalog:book-1', 'authors': list(self.facts['authors'])}]
        self.assertFalse(resolve(self.review, self.frozen(series=self.series))['multi_author_series'])

    def test_same_complete_coauthor_team_on_two_books_keeps_author_folder(self):
        self.review['canonical_author'] = 'David Seltzer; Joseph Howard'
        self.facts['authors'].append('Joseph Howard')
        for member in self.series['members']:
            member['authors'] = list(reversed(self.facts['authors']))
        self.assertFalse(resolve(self.review, self.frozen(series=self.series))['multi_author_series'])

    def test_different_complete_coauthor_teams_establish_shared_series(self):
        self.series['members'][1]['authors'] = ['David Seltzer', 'Joseph Howard']
        self.assertTrue(resolve(self.review, self.frozen(series=self.series))['multi_author_series'])

    def test_author_case_or_spacing_alone_is_not_another_author(self):
        self.series['members'][1]['authors'] = [' DAVID   SELTZER ']
        self.assertFalse(resolve(self.review, self.frozen(series=self.series))['multi_author_series'])

    def test_narrator_never_counts_as_a_book_author(self):
        self.review['narrator'] = 'Joseph Howard'
        self.series['members'][1]['authors'] = ['David Seltzer']
        self.assertFalse(resolve(self.review, self.frozen(series=self.series))['multi_author_series'])

    def test_world_with_two_series_by_one_author_is_shared(self):
        self.review['universe'] = 'World'
        world = copy.deepcopy(self.series)
        world.update(id='https://example.org/world/one', name='World')
        for index, member in enumerate(world['members'], 1):
            member.update(authors=['David Seltzer'], series_id='catalog:series-' + str(index))
        facts = self.frozen(universe=world)
        self.assertTrue(resolve(self.review, facts)['shared_world'])
        self.assertFalse(resolve(self.review, facts)['multi_author_series'])

    def test_world_with_different_authors_in_one_series_is_shared(self):
        self.review['universe'] = 'World'
        world = copy.deepcopy(self.series)
        world.update(id='https://example.org/world/one', name='World')
        for member in world['members']:
            member['series_id'] = self.series['id']
        self.assertTrue(resolve(self.review, self.frozen(universe=world))['shared_world'])

    def test_standalone_world_member_omits_a_series_identity(self):
        self.review.update(series='', number='', universe='World')
        world = copy.deepcopy(self.series)
        world.update(id='https://example.org/world/one', name='World')
        for member in world['members']:
            member['series_id'] = None
        self.assertTrue(resolve(self.review, self.frozen(universe=world))['shared_world'])

    def test_world_and_series_proofs_must_agree_on_current_membership(self):
        self.review['universe'] = 'World'
        world = copy.deepcopy(self.series)
        world.update(id='https://example.org/world/one', name='World')
        for member in world['members']:
            member['series_id'] = self.series['id']
        self.assertTrue(resolve(self.review, self.frozen(series=self.series, universe=world))['shared_world'])
        world['members'][0]['series_id'] = 'catalog:unrelated-series'
        with self.assertRaisesRegex(RoutingEvidenceError, 'disagree on this book'):
            self.frozen(series=self.series, universe=world)
        world['members'][0]['series_id'] = None
        with self.assertRaisesRegex(RoutingEvidenceError, 'no longer matches'):
            self.frozen(universe=world)

    def test_single_author_world_with_one_series_is_not_claimed_shared(self):
        self.review['universe'] = 'World'
        world = copy.deepcopy(self.series)
        world.update(id='https://example.org/world/one', name='World')
        for member in world['members']:
            member.update(authors=['David Seltzer'], series_id=self.series['id'])
        self.assertFalse(resolve(self.review, self.frozen(universe=world))['shared_world'])

    def test_same_name_other_identity_cannot_supply_the_current_work(self):
        self.series['id'] = 'https://example.org/series/unrelated-omen'
        self.series['members'][0]['work_id'] = 'catalog:unrelated-book'
        with self.assertRaisesRegex(RoutingEvidenceError, 'does not identify this book'):
            self.frozen(series=self.series)

    def test_duplicate_work_cannot_manufacture_multiple_authors(self):
        self.series['members'][1]['work_id'] = 'catalog:book-1'
        with self.assertRaisesRegex(RoutingEvidenceError, 'repeats or conflicts'):
            self.frozen(series=self.series)

    def test_omitted_coauthor_refuses_the_identity_join(self):
        self.review['canonical_author'] = 'David Seltzer; Joseph Howard'
        self.facts['authors'].append('Joseph Howard')
        with self.assertRaisesRegex(RoutingEvidenceError, 'every credited author'):
            self.frozen(series=self.series)

    def test_changed_binding_fails_safe_with_actionable_question(self):
        facts = self.frozen(series=self.series)
        for field, value in [('title', 'Other title'), ('series', 'Another series'),
                             ('number', '2'), ('author', 'Other folder author'),
                             ('universe', 'Another world')]:
            with self.subTest(field=field):
                with self.assertRaisesRegex(RoutingEvidenceError, 'Confirm this book.*Edit names'):
                    resolve(dict(self.review, **{field: value}), facts)
        for field, value in [('source_fingerprint', 'changed'), ('work_ids', ['catalog:book-2'])]:
            with self.subTest(field=field):
                with self.assertRaises(RoutingEvidenceError):
                    resolve(self.review, dict(facts, **{field: value}))

    def test_explicit_user_membership_uses_its_durable_decision_identity(self):
        self.series.update(basis='user', id='user:omen-series-confirmed-2026-11-01',
                           evidence=['user:decision-2026-11-01'])
        self.assertTrue(resolve(self.review, self.frozen(series=self.series))['multi_author_series'])

    def test_name_only_and_missing_or_malformed_evidence_are_refused(self):
        for change in [{'id': 'Omen'}, {'evidence': []}, {'basis': 'name_match'},
                       {'members': []}, {'name': 'The Omen'}, {'extra': True}]:
            with self.subTest(change=change):
                with self.assertRaises(RoutingEvidenceError):
                    self.frozen(series=dict(self.series, **change))
        with self.assertRaises(RoutingEvidenceError):
            resolve(self.review, dict(self.facts, shared_routing=None))

    def test_absent_proof_preserves_legacy_behavior(self):
        expected = {'multi_author_series': False, 'shared_world': False}
        self.assertEqual(resolve(self.review, None), expected)
        self.assertEqual(resolve(self.review, self.facts), expected)

    def test_proof_is_a_detached_snapshot_and_inputs_are_unchanged(self):
        before = copy.deepcopy((self.review, self.facts, self.series))
        facts = self.frozen(series=self.series)
        self.assertEqual((self.review, self.facts, self.series), before)
        self.series['members'][1]['authors'][0] = 'Changed later'
        self.assertEqual(facts['shared_routing']['series']['members'][1]['authors'], ['Joseph Howard'])
        frozen_before = copy.deepcopy(facts)
        resolve(self.review, facts)
        self.assertEqual(facts, frozen_before)


class TrilogyDecisionTests(unittest.TestCase):
    TITLES=('The Fellowship of the Ring','The Two Towers','The Return of the King')

    def result(self,number=1,local=False):
        title=self.TITLES[number-1];work='local:accepted-fellowship' if local else 'fantlab:'+str(1666+number)
        return {'work':{'id':work,'original_title':title,'verified_series':{'provider':'fantlab','name':'Властелин колец','number':str(number),'source_url':'https://fantlab.ru/work1693'}},
                'review':{'title':title,'author':'Tolkien J. R. R.','canonical_author':'Tolkien J. R. R.','series':'Властелин колец','number':str(number),'universe':''},
                'metadata_facts':{'source_fingerprint':'source-'+str(number),'work_ids':[work],'original_title':title,'authors':['Tolkien J. R. R.'],'series_state':'verified'},'evidence':[]}

    def test_confirmed_three_books_get_the_decided_series_and_author_world_route(self):
        from public_research import attach_shared_routing
        from organization import plan
        for number in (1,2,3):
            result=attach_shared_routing(self.result(number,local=number==1))
            self.assertEqual((result['review']['series'],result['review']['number'],result['review']['universe']),('Lord of the Rings',str(number),'Middle-earth'))
            path=plan('C:\\private\\Sorted',result['review'],facts=result['metadata_facts'])['path']
            self.assertTrue(path.startswith('C:\\private\\Sorted\\Tolkien J. R. R\\Middle-earth\\Lord of the Rings\\'),path)
            self.assertIn('Lord of the Rings - '+str(number)+' - '+self.TITLES[number-1],path)

    def test_chosen_return_folder_and_title_remain_authoritative(self):
        from public_research import attach_shared_routing
        from organization import plan
        source=self.result(3);source['review']['title']='The Return of the King (my edition)'
        source['metadata_facts']['destination_override']={'id':'saved-choice','folder':'C:\\private\\Sorted\\My chosen folder','identity':{'volume':1,'high':0,'low':2}}
        result=attach_shared_routing(source);path=plan('C:\\private\\Sorted',result['review'],facts=result['metadata_facts'])['path']
        self.assertTrue(path.startswith('C:\\private\\Sorted\\My chosen folder\\Lord of the Rings - 3 - The Return of the King (my edition)'),path)
        self.assertEqual(source['review']['series'],'Властелин колец','the original cached/provider record is not mutated')

    def test_similar_titles_other_authors_or_unproved_series_do_not_gain_the_exception(self):
        from public_research import attach_shared_routing
        controls=[]
        for field,value in [('id','fantlab:999'),('original_title','Unrelated Tolkien novel')]:
            source=self.result();source['work'][field]=value;source['metadata_facts']['work_ids']=[source['work']['id']];controls.append(source)
        source=self.result();source['work']['verified_series']['source_url']='https://fantlab.ru/work999';controls.append(source)
        source=self.result();source['review']['canonical_author']=source['review']['author']='Another Author';source['metadata_facts']['authors']=['Another Author'];controls.append(source)
        for source in controls:
            with self.subTest(source=source):
                result=attach_shared_routing(source);self.assertNotEqual(result['review']['series'],'Lord of the Rings')

    def test_old_pending_trilogy_is_replanned_but_started_or_finished_history_is_not_rewritten(self):
        import json
        from types import SimpleNamespace
        from merge_service import MergeService
        source=self.result(1,local=True)
        manifest={'candidate_id':'candidate','candidate_revision':5,'metadata':source['review'],
                  'metadata_facts':source['metadata_facts'],
                  'evidence':{'metadata_fields':[{'field':'series','source_url':'https://fantlab.ru/work1693'}]}}
        service=SimpleNamespace(reviews=SimpleNamespace(_row=lambda *args:{'revision':5,'fingerprint':'source-1'}))
        job={'job_id':'pending','state':'pending','attempt_id':None,'output':None,'journal':'{}','manifest':json.dumps(manifest)}
        before=copy.deepcopy(job)
        self.assertTrue(MergeService._trilogy_stale(service,job));self.assertEqual(job,before,'the old immutable manifest stays in history')
        for change in ({'state':'running'},{'state':'completed'},{'attempt_id':'already-started'},{'output':'{}'},{'journal':'{"publication_intent":{}}'}):
            self.assertFalse(MergeService._trilogy_stale(service,dict(job,**change)))
        service.reviews._row=lambda *args:{'revision':6,'fingerprint':'source-1'}
        self.assertFalse(MergeService._trilogy_stale(service,job),'a stale candidate never gets a blind name replan')

    def test_pending_revision_advance_requires_complete_current_source_receipts(self):
        import json
        from types import SimpleNamespace
        from merge_service import MergeService,member_key
        source=self.result(1,local=True);path='C:\\private\\source.mp3';key=member_key(path)
        manifest={'candidate_id':'candidate','candidate_revision':4,'sources':[{'path':path,'sha256':'a'*64,'size':123,'modified':'456'}],
                  'metadata':source['review'],'metadata_facts':source['metadata_facts'],
                  'evidence':{'metadata_fields':[{'field':'series','source_url':'https://fantlab.ru/work1693'}]}}
        row={'revision':5,'fingerprint':'new-records-same-files','members':[{'path':path,'size':123,'modified':456}]}
        ctx={'track_order':[key],'included':[key],'source_hashes':{key:{'sha256':'a'*64,'size':123,'modified':'456'}}}
        service=SimpleNamespace(reviews=SimpleNamespace(_row=lambda *args:row,_context=lambda *args:ctx))
        job={'job_id':'pending','state':'pending','attempt_id':None,'output':None,'journal':'{}','manifest':json.dumps(manifest)}
        self.assertTrue(MergeService._trilogy_stale(service,job),'same complete sources can replan after a name/review revision')
        ctx['source_hashes'][key]['sha256']='b'*64
        self.assertFalse(MergeService._trilogy_stale(service,job),'a changed source retains its existing safety admission')

    def test_superseding_decision_replans_old_saved_russian_series_but_respects_later_choices(self):
        from public_research import attach_shared_routing
        from tolkien_trilogy import pending_changed
        old=self.result();old['metadata_facts']['entered_names']={'fields':['series'],'saved_utc':{'series':'2026-10-29T12:00:00Z'}}
        old['approval']={'names':{'series':'Властелин колец'},'entered':['series'],'typed_names':[]}
        corrected=attach_shared_routing(old)
        self.assertEqual(corrected['review']['series'],'Lord of the Rings')
        manifest={'metadata':old['review'],'metadata_facts':old['metadata_facts'],
                  'evidence':{'metadata_fields':[{'field':'series','source_url':'https://fantlab.ru/work1693'}]}}
        self.assertTrue(pending_changed(manifest),'the old saved Russian series cannot leave its pending job on the old route')
        for value in ('My later series','Властелин колец'):
            later=copy.deepcopy(old);later['review']['series']=value;later['metadata_facts']['entered_names']['saved_utc']['series']='2026-11-05T00:00:00Z'
            self.assertEqual(attach_shared_routing(later)['review']['series'],value,'later saved choices remain authoritative')
        typed=copy.deepcopy(old);typed['approval']['typed_names']=['series']
        self.assertEqual(attach_shared_routing(typed)['review']['series'],'Властелин колец','a new explicit press is not an old saved spelling')


class CuratedDecisionEvidenceTests(unittest.TestCase):
    def result(self,legacy=False):
        from public_research import attach_shared_routing
        source=TrilogyDecisionTests().result(2)
        if legacy:
            # Existing normalized credit reaches the older exact-work world branch.
            source['review']['author']=source['review']['canonical_author']='Tolkien J. R. R'
            source['metadata_facts']['authors']=['Tolkien J. R. R']
        return attach_shared_routing(source)

    def test_curated_time_and_user_attribution_are_not_a_public_fetch(self):
        from curated_decisions import validate
        for legacy in (False,True):
            result=self.result(legacy);facts=result['metadata_facts'];row={'fingerprint':facts['source_fingerprint']}
            records=[r for r in result['evidence'] if r.get('source_kind')=='curated_user_decision']
            self.assertEqual({r['field'] for r in records},{'universe'} if legacy else {'series','universe'})
            for record in records:
                self.assertNotIn('retrieved_utc',record);self.assertEqual(record['source_url'],'')
                self.assertEqual(record['decision_actor'],'user');self.assertEqual(record['decision_identity'],'Sergei')
                self.assertEqual(record['recorded_utc'],'2026-11-01T11:36:38Z' if legacy else '2026-11-04T19:52:41Z')
                self.assertEqual(validate(record,row,result['review'],facts),record)

    def test_unknown_decision_field_time_actor_or_any_binding_change_refuses(self):
        from curated_decisions import validate
        for legacy in (False,True):
            result=self.result(legacy);facts=result['metadata_facts'];row={'fingerprint':facts['source_fingerprint']}
            record=next(r for r in result['evidence'] if r.get('source_kind')=='curated_user_decision')
            for change in ('ref','time','field','value','actor','identity','url','retrieval','source','work','cycle','title','authors','accepted'):
                bad=copy.deepcopy(record)
                if change=='ref':bad['decision_ref']='user:unknown'
                if change=='time':bad['recorded_utc']='2026-11-05T00:00:00Z'
                if change=='field':bad['field']='title'
                if change=='value':bad['cited_value']='My unverified series'
                if change=='actor':bad['decision_actor']='assistant'
                if change=='identity':bad['decision_identity']='Someone else'
                if change=='url':bad['source_url']='https://fantlab.ru/work1693'
                if change=='retrieval':bad['retrieved_utc']='2026-11-05T00:00:00Z'
                if change=='source':bad['binding']['source_fingerprint']='changed'
                if change=='work':bad['binding']['work_ids']=['fantlab:999']
                if change=='cycle':bad['binding']['catalog_cycle']='https://fantlab.ru/work999'
                if change=='title':bad['binding']['original_title']='Other novel'
                if change=='authors':bad['binding']['authors']=['Another Writer']
                if change=='accepted':bad['binding']['review']['title']='Other title'
                with self.subTest(legacy=legacy,change=change),self.assertRaises(ValueError):validate(bad,row,result['review'],facts)
            wrong=copy.deepcopy(facts);wrong['source_fingerprint']='changed'
            with self.assertRaises(ValueError):validate(record,row,result['review'],wrong)
            wrong=copy.deepcopy(facts)
            if legacy:wrong['shared_routing']['universe']['members'][0]['series_id']='https://fantlab.ru/work999'
            else:wrong['trilogy_routing']['binding']['source_fingerprint']='changed'
            with self.assertRaises(ValueError):validate(record,row,result['review'],wrong)

    def test_generic_manual_rules_keep_https_time_and_field_requirements(self):
        from metadata_sources import manual_evidence
        record={'field':'series','cited_value':'Lord of the Rings','source_url':'https://fantlab.ru/work1693',
            'retrieved_utc':'2026-11-04T19:52:41Z','reviewer_actor':'assistant','reviewer_identity':'Fixture reviewer','basis':'Public catalog identifies this series'}
        self.assertEqual(manual_evidence(**record)['source_url'],record['source_url'])
        for changed in ({'field':'universe'},{'source_url':''},{'retrieved_utc':None},{'retrieved_utc':'2026-11-04T19:52:41+02:00'}):
            with self.subTest(changed=changed),self.assertRaises(ValueError):manual_evidence(**dict(record,**changed))


class CuratedApprovalTests(unittest.TestCase):
    """Actual user Approve and pending persistence; no conversion or network."""
    def setUp(self):
        import os,tempfile
        from pathlib import Path
        self.temp=tempfile.TemporaryDirectory(dir=os.environ['BOOKS_QA_FIXTURE_ROOT']);self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.audio=self.base/'a';self.audio.mkdir();self.sorted=self.base/'s';self.sorted.mkdir()

    def approve(self,number,legacy=False,durable=False,interrupt=None):
        import json,threading,shutil
        from pathlib import Path
        from unittest.mock import patch
        from scanner import Inventory
        from scan_wait import finish_scan
        from merge_service import MergeService
        from public_research import PublicClient,PublicResearch,attach_shared_routing
        from standing_metadata import build_policy
        from audio_pipeline import run_owned
        source=self.audio/'book.m4b'
        run_owned([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=0.4',
            '-c:a','aac','-b:a','64k','-ar','44100','-ac','1','-metadata','album=Source recording','-metadata','title=Source recording',str(source)],self.base,threading.Event(),30)
        before=source.read_bytes()
        inv=Inventory(self.base/'catalog.sqlite3',{'Audiobooks':str(self.audio),'Podcasts':str(self.base/'p'),'Ebooks':str(self.base/'e')},output_root=str(self.sorted))
        inv.launch('Audiobooks');finish_scan(inv)
        service=MergeService(inv,self.base/'c');self.addCleanup(service.close)
        def offline(url,*args):raise AssertionError('Unexpected fixture network access: '+url)
        research=PublicResearch(PublicClient(inv.database,fetch=offline),leads=[]);service.automatic.research=research
        row=service.reviews.page()['rows'][0];title=TrilogyDecisionTests.TITLES[number-1]
        work={'id':'local:accepted-fellowship' if number==1 else 'fantlab:'+str(1666+number),'original_title':title,'titles':[title],
            'original_language':'en','author_aliases':['Tolkien J. R. R.'],'policy_version':'standing-17-v1',
            'verified_series':{'provider':'fantlab','name':'Властелин колец','number':str(number),'source_url':'https://fantlab.ru/work1693'}}
        credit='Tolkien J. R. R' if legacy else 'Tolkien J. R. R.'
        review,facts,reasons=build_policy(row,work,title,[credit],series='Властелин колец',number=str(number))
        result={'work':work,'review':review,'metadata_facts':facts,'reasons':reasons,'evidence':[],
            'sources':[{'kind':'publisher_or_journal','url':'https://publisher.example/tolkien','verified_identity':True}],
            'approval':{'title':title,'author':credit,'typed':[],'collection':False}}
        result=attach_shared_routing(result)
        extra={};saved=None
        if durable:
            import uuid
            service.decisions.close();store=service.decisions.store
            saved=store.accept(request_id=str(uuid.uuid4()),book_id=row['id'],action='approve',revision=row['revision'],fingerprint=row['fingerprint'],
                               payload={'title':None,'author':None,'names':None,'without_missing':False,'choice':None,'path':None},effects=['approval'],current_revision=row['revision'],current_fingerprint=row['fingerprint'])
            extra['decision']=store.application(saved['request_id'],store.head(row['id'])['generation'])
        def press():return service.approve_book(row['id'],service.reviews._row('Audiobooks',row['id'])['revision'],**extra)
        if interrupt:
            from decision_effects import Effect
            commit=Effect.commit;failed=[]
            def interrupted(effect,*args,**kwargs):
                if effect.step==interrupt and not failed:
                    failed.append(effect.step);raise RuntimeError('Private process interruption before '+interrupt+' receipt')
                return commit(effect,*args,**kwargs)
            with patch.object(service,'_approval_result',return_value=(row,result)),patch.object(service,'_english_spelling_answer',return_value=None),patch.object(Effect,'commit',new=interrupted):
                with self.assertRaisesRegex(RuntimeError,'Private process interruption'):press()
            self.assertEqual(failed,[interrupt]);self.assertEqual(service.jobs.status()['jobs'],[])
            self.assertEqual(store.get(saved['request_id'])['state'],'applying');service.close()
            # Reopen through the real constructor, retaining the durable request.
            # Keep only this test's scheduling deterministic; run_once is the
            # same production owner pass and uses no second accept/press.
            with patch('decision_runtime.DecisionRuntime.start'):service=MergeService(inv,self.base/'c')
            self.addCleanup(service.close);service.automatic.research=research
            with patch.object(service,'_approval_result',side_effect=lambda *args,**kwargs:(service.reviews._row('Audiobooks',row['id']),result)),patch.object(service,'_english_spelling_answer',return_value=None):
                service.decisions.run_once()
            recovered=store.get(saved['request_id']);self.assertEqual(recovered['state'],'applied',recovered)
            approved={'job_id':recovered['result']['job_id']}
        else:
            with patch.object(service,'_approval_result',return_value=(row,result)),patch.object(service,'_english_spelling_answer',return_value=None):approved=press()
        jobs=service.jobs.status()['jobs'];self.assertEqual(len(jobs),1);job=jobs[0]
        self.assertEqual(job['job_id'],approved['job_id']);self.assertEqual(job['state'],'pending')
        if durable:
            receipt=store.get(saved['request_id']);self.assertEqual(receipt['state'],'applied');self.assertEqual(receipt['result']['job_id'],job['job_id'])
        self.assertIsNone(job.get('output'));self.assertIsNone(job.get('attempt_id'))
        records=job['manifest']['evidence']['metadata_fields'];curated=[r for r in records if r.get('source_kind')=='curated_user_decision']
        self.assertEqual({r['field'] for r in curated},{'universe'} if legacy else {'series','universe'})
        self.assertTrue(all(r['reviewer_actor']=='user' and r['decision_actor']=='user' and r['decision_identity']=='Sergei' for r in curated))
        self.assertTrue(all('retrieved_utc' not in r for r in curated))
        fresh=service.reviews._row('Audiobooks',row['id']);ctx=service.reviews._context(fresh)
        self.assertEqual(ctx['metadata_evidence'],records);self.assertTrue(ctx['metadata_approved'])
        self.assertEqual(fresh['review']['universe'],'Middle-earth')
        self.assertEqual(fresh['review']['series'],'Властелин колец' if legacy else 'Lord of the Rings')
        from review_backend import CandidateReviewService
        restarted=CandidateReviewService(inv,self.base/'c')
        self.assertEqual(restarted._context(restarted._row('Audiobooks',row['id']))['metadata_evidence'],records)
        self.assertTrue(source.is_file());self.assertEqual(source.read_bytes(),before);self.assertFalse(Path(job['manifest']['destination']).exists())
        return service,row,result

    def test_return_king_actual_approve_persists_and_queues(self):self.approve(3)
    def test_two_towers_actual_approve_persists_and_queues(self):self.approve(2)
    def test_fellowship_actual_approve_persists_and_queues(self):self.approve(1)
    def test_legacy_middle_earth_actual_approve_persists_and_queues(self):self.approve(2,legacy=True)
    def test_durable_return_king_actual_approve_has_atomic_job_receipt(self):self.approve(3,durable=True)
    def test_durable_two_towers_actual_approve_has_atomic_job_receipt(self):self.approve(2,durable=True)
    def test_durable_approve_recovers_after_metadata_commit_without_another_press(self):self.approve(3,durable=True,interrupt='tracks')
    def test_durable_approve_recovers_after_track_commit_without_another_press(self):self.approve(2,durable=True,interrupt='approved_checkpoint')
    def test_private_review_consumer_refuses_malformed_or_mismatched_curated_records_before_writes(self):
        import json
        from scanner import connect
        service,row,result=self.approve(3)
        fresh=service.reviews._row('Audiobooks',row['id']);ctx=service.reviews._context(fresh)
        def stored():
            with connect(service.inventory.database) as db:
                return tuple(db.execute('SELECT revision,review FROM book_groups WHERE id=?',(row['id'],)).fetchone()),tuple(db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(row['id'],)).fetchone())
        before=stored();records=ctx['metadata_evidence']
        for change in ('schema','ref','time','source','field','no_private_admission'):
            bad=copy.deepcopy(records);record=next(r for r in bad if r.get('source_kind')=='curated_user_decision')
            if change=='schema':record['schema']='untrusted'
            if change=='ref':record['decision_ref']='user:unknown'
            if change=='time':record['recorded_utc']='2026-11-05T00:00:00Z'
            if change=='source':record['binding']['source_fingerprint']='changed'
            if change=='field':record['field']='title'
            with self.subTest(change=change),self.assertRaises(ValueError):
                service.reviews.save('Audiobooks',fresh['id'],fresh['revision'],fresh['review'],actor='user',evidence=bad,
                    **({'approve':False} if change=='no_private_admission' else {'approve':True,'user_approval':True,
                    'cover_id':ctx['cover_id'],'automatic_pending':{'matcher_version':'fixture','work_id':result['work']['id']},'automatic_facts':result['metadata_facts']}))
            self.assertEqual(stored(),before)


if __name__ == '__main__':
    unittest.main()
