import os
import unittest
from organization import plan,POLICY

class OrganizationTests(unittest.TestCase):
    def setUp(self):self.root=os.path.abspath('synthetic-output');self.review={'title':'Book','canonical_author':'Writer','series':'Cycle','number':'2'}
    def path(self,**changes):return plan(self.root,dict(self.review,**changes))['relative_path'].replace(os.sep,'/')
    def test_single_author_cycle(self):self.assertEqual(self.path(),'Writer/Cycle/Cycle - 2 - Book - Writer.m4b')
    def test_multi_author_cycle(self):self.assertEqual(self.path(multi_author=True),'Cycle/Cycle - 2 - Book - Writer.m4b')
    def test_universe_cycle(self):self.assertEqual(self.path(universe='Universe'),'Universe/Cycle/Cycle - 2 - Book - Writer.m4b')
    def test_universe_standalone(self):self.assertEqual(self.path(universe='Universe',series='',number=''),'Universe/Book - Writer.m4b')
    def test_cycle_collection(self):self.assertEqual(self.path(anthology=True,number=''),'Writer/Cycle/Book - Cycle - Short Stories.m4b')
    def test_collection_with_its_series_and_position_files_under_the_collections_folder(self):
        # 0.22.2 (Sergei 2026-10-26, «Протоколы SCP»): Сборники\<Series>\<Series> - <N> - <Title> - <Author>.m4b.
        self.assertEqual(self.path(anthology=True,title='Сейф №1',canonical_author='Разные авторы',series='Протоколы SCP',number='1'),
                         'Сборники/Протоколы SCP/Протоколы SCP - 1 - Сейф №1 - Разные авторы.m4b')
    def test_universe_collection(self):self.assertEqual(self.path(anthology=True,universe='Universe',series='',number=''),'Universe/Book - Universe - Short Stories.m4b')
    def test_multi_author_collection(self):self.assertEqual(self.path(anthology=True,multi_author=True),'Cycle/Book - Cycle - Short Stories.m4b')
    def test_collection_without_title(self):self.assertEqual(self.path(anthology=True,title=''),'Writer/Cycle/Cycle - Short Stories.m4b')
    def test_standalone_legacy_behavior(self):self.assertEqual(self.path(series='',number=''),'Writer/Book - Writer.m4b')
    def test_distinct_folder_author_keeps_legacy_path_and_artist_credit(self):
        from metadata import future_audio_tags
        review=dict(self.review,author='Folder Writer',canonical_author='Artist Credit')
        result=plan(self.root,review)
        self.assertEqual(result['relative_path'].replace(os.sep,'/'),'Folder Writer/Cycle/Cycle - 2 - Book - Folder Writer.m4b')
        self.assertEqual(future_audio_tags({},review)['ARTIST'],'Artist Credit')
        self.assertEqual(review['canonical_author'],'Artist Credit')
    def test_distinct_folder_author_standalone(self):
        self.assertEqual(self.path(author='Folder Writer',canonical_author='Artist Credit',series='',number=''),'Folder Writer/Book - Folder Writer.m4b')
    def test_blank_folder_author_falls_back_to_canonical(self):
        self.assertEqual(self.path(author='  '),'Writer/Cycle/Cycle - 2 - Book - Writer.m4b')
    def test_unassigned_collection_legacy(self):self.assertEqual(self.path(anthology=True,series='',number=''),'Сборники/Book - Writer.m4b')
    def test_missing_number_holds_normal_book(self):
        with self.assertRaises(ValueError):self.path(number='')
    def test_unsafe_name_is_sanitized_and_remains_contained(self):
        result=plan(self.root,dict(self.review,universe='../escape',title='CON'))
        self.assertEqual(os.path.commonpath([self.root,result['path']]),self.root)
        self.assertNotIn('../',result['relative_path'].replace(os.sep,'/'))
    def test_policy_is_recorded_without_mutating_input(self):
        before=dict(self.review);result=plan(self.root,self.review)
        self.assertEqual(result['policy_version'],POLICY);self.assertEqual(self.review,before)


class SharedOrganizationTests(unittest.TestCase):
    def setUp(self):
        self.root = os.path.abspath('synthetic-output')
        self.review = {'title': 'The Omen', 'author': 'Seltzer David',
                       'canonical_author': 'David Seltzer', 'series': 'Omen', 'number': '1'}
        self.facts = {'source_fingerprint': 'source-one', 'work_ids': ['catalog:book-1'],
                      'authors': ['David Seltzer']}
        self.authority = {'id': 'user:omen-series-2026-11-01', 'name': 'Omen', 'basis': 'user',
                          'evidence': ['user:decision-2026-11-01'],
                          'members': [{'work_id': 'catalog:book-1', 'authors': ['David Seltzer']},
                                      {'work_id': 'catalog:book-2', 'authors': ['Joseph Howard']}]}

    def freeze(self):
        from shared_routing import build
        self.facts['shared_routing'] = build(self.review, self.facts, series=self.authority)

    def test_omen_books_go_directly_under_the_shared_series_with_their_own_credits(self):
        from metadata import future_audio_tags
        for title, folder_author, author, number in [('The Omen', 'Seltzer David', 'David Seltzer', '1'),
                                                      ('Damien', 'Howard Joseph', 'Joseph Howard', '2')]:
            with self.subTest(title=title):
                self.review.update(title=title, author=folder_author, canonical_author=author, number=number)
                self.facts.update(work_ids=['catalog:book-' + number], authors=[author])
                self.freeze()
                planned = plan(self.root, self.review, facts=self.facts)
                self.assertEqual(planned['relative_path'].replace(os.sep, '/'),
                                 'Omen/Omen - ' + number + ' - ' + title + ' - ' + folder_author + '.m4b')
                self.assertEqual(future_audio_tags({}, self.review)['ARTIST'], author)
                self.assertEqual(planned['accepted_routing']['author'], folder_author)
                self.assertTrue(planned['accepted_routing']['multi_author_cycle'])
                self.assertNotIn('multi_author', self.review)

    def test_shared_world_retains_series_level_and_existing_filename(self):
        self.review['universe'] = 'Shared World'
        self.freeze()
        planned = plan(self.root, self.review, facts=self.facts)
        self.assertEqual(planned['relative_path'].replace(os.sep, '/'),
                         'Shared World/Omen/Omen - 1 - The Omen - Seltzer David.m4b')

    def test_same_named_series_without_identity_proof_keeps_the_author_folder(self):
        planned = plan(self.root, self.review, facts=self.facts)
        self.assertEqual(planned['relative_path'].replace(os.sep, '/'),
                         'Seltzer David/Omen/Omen - 1 - The Omen - Seltzer David.m4b')

    def test_shared_series_keeps_recording_distinction_in_the_filename(self):
        self.freeze()
        self.facts.update(policy_version='standing-17-v1', destination_suffix='recording-0123456789abcdef')
        planned = plan(self.root, self.review, facts=self.facts)
        self.assertEqual(planned['relative_path'].replace(os.sep, '/'),
                         'Omen/Omen - 1 - The Omen - Seltzer David - recording-0123456789abcdef.m4b')

    def test_custom_folder_inside_root_still_wins_and_keeps_the_filename(self):
        self.freeze()
        chosen = os.path.join(self.root, 'Chosen')
        self.facts['destination_override'] = {'id': 'choice', 'folder': chosen, 'identity': {}}
        planned = plan(self.root, self.review, facts=self.facts)
        self.assertEqual(planned['path'], os.path.join(chosen, 'Omen - 1 - The Omen - Seltzer David.m4b'))

    def test_custom_folder_outside_root_preserves_safe_publish_then_move_policy(self):
        self.freeze()
        self.facts['destination_override'] = {'id': 'choice', 'folder': os.path.abspath('other-output'), 'identity': {}}
        planned = plan(self.root, self.review, facts=self.facts)
        self.assertEqual(planned['relative_path'].replace(os.sep, '/'), 'Omen/Omen - 1 - The Omen - Seltzer David.m4b')

    def test_preview_frozen_plan_and_old_manifest_keep_their_own_paths(self):
        import copy
        from organization import frozen_plan
        old_manifest = {'metadata': copy.deepcopy(self.review), 'metadata_facts': copy.deepcopy(self.facts)}
        old_before = copy.deepcopy(old_manifest)
        old_path = frozen_plan(old_manifest, self.root)['path']
        self.freeze()
        fresh = {'metadata': self.review, 'metadata_facts': self.facts}
        self.assertEqual(frozen_plan(fresh, self.root), plan(self.root, self.review, facts=self.facts))
        self.assertNotEqual(frozen_plan(fresh, self.root)['path'], old_path)
        self.assertEqual(frozen_plan(old_manifest, self.root)['path'], old_path)
        self.assertEqual(old_manifest, old_before)

    def test_changed_source_or_series_does_not_silently_reuse_shared_routing(self):
        self.freeze()
        with self.assertRaisesRegex(ValueError, 'Confirm this book'):
            plan(self.root, dict(self.review, series='Another Omen'), facts=self.facts)
        with self.assertRaisesRegex(ValueError, 'Confirm this book'):
            plan(self.root, self.review, facts=dict(self.facts, source_fingerprint='changed'))

    def test_shared_fact_keeps_existing_numbered_anthology_filename_and_folder(self):
        self.review['anthology'] = True
        self.freeze()
        self.assertEqual(plan(self.root, self.review, facts=self.facts)['relative_path'].replace(os.sep, '/'),
                         'Сборники/Omen/Omen - 1 - The Omen - Seltzer David.m4b')

if __name__=='__main__':unittest.main()
