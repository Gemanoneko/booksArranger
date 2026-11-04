import unittest

from organization import plan
from public_research import attach_shared_routing
from test_shared_routing import TrilogyDecisionTests
from tolkien_trilogy import pending_changed


class LegacyT1Tests(unittest.TestCase):
    def candidate(self, value='Властелин колец', saved=None, typed=False):
        item=TrilogyDecisionTests().result(1, local=True)
        item['review']['series']=value
        item['metadata_facts']['entered_names']={'fields':['series']}
        if saved is not None:
            item['metadata_facts']['entered_names']['saved_utc']={'series':saved}
        item['approval']={'names':{'series':value},'entered':['series'],
                          'typed_names':['series'] if typed else []}
        return item

    def test_legacy_and_cutoff_replan_while_later_choices_stay(self):
        for stamp in (None,'2026-11-04T19:52:40Z','2026-11-04T19:52:41Z'):
            with self.subTest(old_saved_utc=stamp):
                old=self.candidate(saved=stamp)
                old['review']['title']='My Fellowship title'
                old['metadata_facts']['destination_override']={
                    'id':'saved-choice','folder':'C:\\private\\Sorted\\My chosen folder',
                    'identity':{'volume':1,'high':0,'low':2}}
                corrected=attach_shared_routing(old)
                self.assertEqual(corrected['review']['series'],'Lord of the Rings')
                self.assertEqual(corrected['review']['title'],'My Fellowship title')
                self.assertEqual(corrected['metadata_facts']['destination_override'],
                                 old['metadata_facts']['destination_override'])
                destination=plan('C:\\private\\Sorted',corrected['review'],
                                 facts=corrected['metadata_facts'])['path']
                self.assertIn('My chosen folder\\Lord of the Rings - 1 - My Fellowship title',destination)
                manifest={'metadata':old['review'],'metadata_facts':old['metadata_facts'],
                          'evidence':{'metadata_fields':[{'field':'series',
                                      'source_url':'https://fantlab.ru/work1693'}]}}
                self.assertTrue(pending_changed(manifest))
        for value,stamp,typed in (
            ('Властелин колец','2026-11-04T19:52:42Z',False),
            ('My later series','2026-11-05T00:00:00Z',False),
            ('Властелин колец',None,True)):
            with self.subTest(later_value=value,saved_utc=stamp,typed=typed):
                current=self.candidate(value=value,saved=stamp,typed=typed)
                self.assertEqual(attach_shared_routing(current)['review']['series'],value)
