"""Manual research evidence: discovery and honest non-override, no network."""
import copy
import unittest
from unittest.mock import patch
import manual_metadata as m
from public_research import PublicResearch
from scan_wait import finish_scan

class ManualResearchTests(unittest.TestCase):
    def setUp(self):
        self.row={'id':'candidate','fingerprint':'source-fingerprint','members':[{'path':'C:/private/audio/001.mp3','filename':'001.mp3','metadata':{'tags':{}},'missing':False,'error':''}]}
        record=m.capture(self.row,{'title':'Entered title','canonical_author':'Writer'},'Credits');record['status']='current'
        self.row['_manual_metadata_sources']=[record]
        self.engine=object.__new__(PublicResearch)
    def test_agreeing_manual_source_is_attributed_not_independent_verification(self):
        result={'sources':[{'kind':'catalog_work','verified_identity':True}],'work':{'titles':['Entered title'],'author_aliases':['Writer']},'review':{'title':'Entered title','canonical_author':'Writer'},'reasons':[]}
        original=copy.deepcopy(result)
        with patch.object(PublicResearch,'_lookup',return_value=copy.deepcopy(result)):
            checked=self.engine.lookup(self.row,'C:/private/audio')
        self.assertEqual(checked['review'],original['review']|{'organization_policy':'books-hierarchy-v2'});self.assertEqual(checked['reasons'],[])
        self.assertEqual(checked['sources'][-1]['kind'],'manual_metadata');self.assertFalse(checked['sources'][-1]['verified_identity'])
    def test_disagreement_holds_and_never_overwrites_provider(self):
        result={'sources':[],'work':{'titles':['Other title'],'author_aliases':['Writer']},'review':{'title':'Other title'},'reasons':[]}
        with patch.object(PublicResearch,'_lookup',return_value=result):checked=self.engine.lookup(self.row,'C:/private/audio')
        self.assertEqual(checked['review']['title'],'Other title');self.assertTrue(checked['reasons'])
        self.assertEqual(checked['metadata_holds'][0]['cause'],'metadata_conflict')
    def test_stale_human_source_does_not_participate(self):
        self.row['_manual_metadata_sources'][0]['status']='stale'
        with patch.object(PublicResearch,'_lookup',return_value={'sources':[],'reasons':['Book identity uncertain']}) as lookup:
            checked=self.engine.lookup(self.row,'C:/private/audio')
        self.assertNotIn('manual_metadata_sources',checked)
    def test_human_title_is_positive_discovery_input_without_fake_approval(self):
        from types import SimpleNamespace
        calls=[]
        def query(url,*args):calls.append(url);return []
        self.engine.client=SimpleNamespace(json=query,discover=lambda *args:[],wikipedia=lambda *args:{'sources':[],'leads':[]})
        self.engine.local_agreement=False;self.engine._siblings=lambda *args:([],None)
        self.engine._independent_catalog=lambda *args:None
        with patch('local_identity.agreement',return_value={'accepted':False,'route':None}),patch('local_identity.summary',return_value={}):
            checked=self.engine.lookup(self.row,'C:/private/audio')
        self.assertTrue(any('Entered+title' in url for url in calls),calls)
        self.assertIn('Book identity uncertain',checked['reasons'])
        self.assertFalse(checked['sources'][-1]['verified_identity'])

class LocalPolicyRecheckTests(unittest.TestCase):
    def test_supported_start_rechecks_old_local_gate_hold_and_retains_manual_source(self):
        import time
        from scanner import connect
        from test_automatic_processing import AutoTests
        fx=AutoTests('test_uncertain_work_is_revisited_until_user_stop');fx.setUp()
        try:
            calls=[]
            def lookup(*args):calls.append(args[0]['id']);return {'reasons':['Book identity uncertain'],'sources':[]}
            auto,merge,inv=fx.fake_merge(lookup);inv.launch('Audiobooks');finish_scan(inv)
            row=inv.candidates('Audiobooks')['rows'][0]
            with connect(inv.database) as db:
                m.initialize(db);m.append(db,m.capture(row,{'title':'Human source retained'},'Credits'))
            auto._record(row,'Held',{'reasons':['Sources disagree on the title or author'],'metadata_facts':{'identity_basis':'local_agreement'},'local_source_gate_version':'old'},time.time()+86400)
            old=auto.candidate(row);self.assertIsNone(auto._refresh_wait(row,old)['retry_at'])
            unrelated=dict(old,reasons=['Playback order uncertain']);self.assertEqual(auto._refresh_wait(row,unrelated)['retry_at'],unrelated['retry_at'])
            auto.start();state=fx.wait_auto(auto)
            self.assertEqual(calls,[row['id']]);self.assertEqual(state['state'],'Completed')  # ruling 5: held until changed
            with connect(inv.database) as db:self.assertEqual(m.records(db,row)[0]['values']['title'],'Human source retained')
        finally:
            # The borrowed setUp starts a class-wide patch of PublicResearch.local_agreement; without its cleanups it leaked
            # into every later module of the same process (0.22.0 gate, batch 0).
            fx.tearDown();fx.doCleanups()

if __name__=='__main__':unittest.main()
