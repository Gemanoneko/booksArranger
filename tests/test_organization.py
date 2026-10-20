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
    def test_universe_collection(self):self.assertEqual(self.path(anthology=True,universe='Universe',series='',number=''),'Universe/Book - Universe - Short Stories.m4b')
    def test_multi_author_collection(self):self.assertEqual(self.path(anthology=True,multi_author=True),'Cycle/Book - Cycle - Short Stories.m4b')
    def test_collection_without_title(self):self.assertEqual(self.path(anthology=True,title=''),'Writer/Cycle/Cycle - Short Stories.m4b')
    def test_standalone_legacy_behavior(self):self.assertEqual(self.path(series='',number=''),'Writer/Book - Writer.m4b')
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
if __name__=='__main__':unittest.main()
