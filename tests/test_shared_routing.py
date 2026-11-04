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


if __name__ == '__main__':
    unittest.main()
