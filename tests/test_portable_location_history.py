"""Location-only portable generation matching; no producer authority supplied."""
import unittest
from types import SimpleNamespace
from storage_relocation_native import NativeContext

class PortableLocationHistoryTests(unittest.TestCase):
 def test_post_adoption_file_and_catalog_location(self):
  before=dict(identity=[1,0,10],dev=1,ino=10,identity_method='win32',identity_api_error=None,links=1,size=3,modified=1,attributes=32)
  after=dict(before,identity=[2,0,20],dev=2,ino=20)
  bridge=dict(current=after,prior=before,copied_from=before,location_history=[before])
  context=NativeContext.__new__(NativeContext)
  context.namespace=SimpleNamespace(file_binding=lambda path:bridge)
  context.require_normal_operation=lambda:None
  context.permitted=lambda path:True
  context.origin_location=lambda path:path
  context.manifest=SimpleNamespace(files={},relative=lambda path:path)
  context.database='new catalog'
  self.assertTrue(context.facts_match('new post-adoption file',after,before,'working-file'))
  self.assertTrue(context.identity_match('new post-adoption file',after,before['identity'],'file-disposition-control'))
  keys=('identity','dev','ino','identity_method','identity_api_error','links')
  self.assertTrue(context.catalog_identity_match({k:after[k] for k in keys},{k:before[k] for k in keys}))
  self.assertFalse(context.facts_match('new post-adoption file',dict(after,size=4),before,'working-file'))
  self.assertFalse(context.identity_match('new post-adoption file',dict(after,identity=[2,0,21]),before['identity'],'working-file'))

if __name__=='__main__':unittest.main()
