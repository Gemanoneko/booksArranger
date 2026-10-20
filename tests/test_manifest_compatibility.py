"""Pure legacy receipt comparisons; no catalog, media, native or queue actions."""
import copy
import hashlib
import json
import os
from pathlib import Path
import unittest
import uuid

import failed_m4b_retry
import m4b_repair
from manifest_compatibility import equivalent_manifest,normalized_output_root

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'manifest-compatibility'


def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


class ManifestCompatibility(unittest.TestCase):
    def setUp(self):
        self.root=str(AREA/'original-library')
        self.legacy={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':4,
            'root':self.root,'destination':str(Path(self.root)/'Author'/'Book.m4b'),
            'sources':[{'path':str(Path(self.root)/'Unsorted'/'source.m4b'),'sha256':'a'*64,'size':1234,'modified':4321,'fingerprint':{'size':1234,'modified':4321}}],
            'metadata':{'title':'Книга','canonical_author':'Author'},'cover':{'id':'approved-cover','sha256':'c'*64},
            'source_chapters':[{'title':'First','start':0,'end':1},{'title':'Second','start':1,'end':2}],
            'profile':'frozen-profile','chapters':['First','Second'],'options':{'preserve':True},'cleanup_policy':{'enabled':False}}
        raw=encoded(self.legacy)
        self.parent={'job_id':self.legacy['job_id'],'state':'needs attention','reason':'Remux changed the decoder configuration or relative audio packet timing',
            'manifest':raw,'manifest_hash':hashlib.sha256(raw.encode()).hexdigest(),'journal':encoded({'history':[{'stage':'checking'}]}),'output':None}
        self.fresh=copy.deepcopy(self.legacy);self.fresh.update(job_id=str(uuid.uuid4()),output_root=self.root)
        self.profile={'schema':failed_m4b_retry.SCHEMA,'module_sha256':'d'*64,'tracks':[{'id':1,'sha256':'e'*64}]}
        self.diagnosis={'state':'repairable','repairs':[{'kind':'dangling_chapter_reference'}],'damage':['Exact dangling chapter reference']}

    def binders(self):
        return [('preservation',lambda value:failed_m4b_retry.bind(self.parent,value,self.profile)),
                ('repair',lambda value:m4b_repair.bind(self.parent,value,self.diagnosis,'f'*64))]

    def test_actual_legacy_absence_and_current_explicit_same_root_bind_both_children(self):
        # This is the old comparison itself: otherwise identical manifests fail
        # solely because the current builder makes the old default explicit.
        remove=lambda value:{key:item for key,item in value.items() if key!='job_id'}
        self.assertNotEqual(remove(self.legacy),remove(self.fresh))
        parent_before=copy.deepcopy(self.parent);fresh_before=copy.deepcopy(self.fresh)
        for name,bind in self.binders():
            with self.subTest(name=name):
                child=bind(self.fresh)
                self.assertEqual(child['output_root'],self.root);self.assertEqual(child['destination'],self.legacy['destination'])
                self.assertEqual(child['m4b_repair']['parent_manifest_hash'],self.parent['manifest_hash'])
                self.assertEqual(child['m4b_repair']['parent_journal_sha256'],hashlib.sha256(self.parent['journal'].encode()).hexdigest())
        self.assertEqual(self.parent,parent_before);self.assertEqual(self.fresh,fresh_before)
        self.assertNotIn('output_root',json.loads(self.parent['manifest']))

    def test_explicit_different_sorted_root_and_destination_never_gain_compatibility(self):
        for updates in ({'output_root':str(AREA/'Sorted')},{'root':str(AREA/'Other')},
                {'destination':str(AREA/'Sorted'/'Book.m4b')},{'output_root':self.root+'/.'},
                {'root':self.root.lower()},{'destination':self.legacy['destination']+'.new'}):
            for name,bind in self.binders():
                with self.subTest(name=name,updates=updates),self.assertRaisesRegex(ValueError,'Frozen review'):
                    bind(self.fresh|updates)

    def test_all_nondefault_fields_remain_exact_including_order_hash_options_policy(self):
        for field,value in [('sources',list(reversed(self.fresh['sources']))+[copy.deepcopy(self.fresh['sources'][0])]),
                ('sources',[self.fresh['sources'][0]|{'sha256':'0'*64}]),('source_chapters',list(reversed(self.fresh['source_chapters']))),
                ('chapters',['Second','First']),('options',{'preserve':False}),('cleanup_policy',{'enabled':True}),
                ('metadata',{'title':'Other'}),('cover',{'id':'different'}),('candidate_revision',5),('profile','new-profile')]:
            for name,bind in self.binders():
                with self.subTest(name=name,field=field),self.assertRaisesRegex(ValueError,'Frozen review'):
                    bind(self.fresh|{field:value})

    def test_explicit_null_empty_or_malformed_output_roots_are_not_defaulted(self):
        for value in (None,'',False,0,[],{},['root']):
            candidate=self.fresh|{'output_root':value}
            self.assertIs(normalized_output_root(candidate)['output_root'],value)
            self.assertFalse(equivalent_manifest(self.legacy,candidate))
            for name,bind in self.binders():
                with self.subTest(name=name,value=value),self.assertRaisesRegex(ValueError,'Frozen review'):bind(candidate)

    def test_normalizer_is_nonmutating_and_missing_or_malformed_root_is_not_none(self):
        before=copy.deepcopy(self.legacy);normalized=normalized_output_root(self.legacy)
        self.assertIsNot(normalized,self.legacy);self.assertEqual(normalized['output_root'],self.root);self.assertEqual(self.legacy,before)
        for value in ({},{'root':None},{'root':''},{'root':[]},{'root':'  '}):
            with self.subTest(value=value),self.assertRaises(ValueError):normalized_output_root(value)
        self.assertTrue(equivalent_manifest({'job_id':'old','minimal':1},{'job_id':'new','minimal':1}))
        self.assertFalse(equivalent_manifest({'minimal':1},{'minimal':1,'output_root':None}))
        self.assertFalse(equivalent_manifest(None,self.fresh))

    def test_no_other_new_key_is_silently_ignored_and_distinct_child_still_required(self):
        for name,bind in self.binders():
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'Frozen review'):bind(self.fresh|{'new_policy':True})
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'distinct job'):bind(self.fresh|{'job_id':self.parent['job_id']})


if __name__=='__main__':unittest.main()
