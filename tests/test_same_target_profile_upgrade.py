"""Same-target upgrade profile authority; private native fixture, retained on disk."""
import contextlib,hashlib,json,os,sqlite3,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import storage_lifecycle as lifecycle

@unittest.skipUnless(os.name=='nt','Native profile authority requires Windows')
class SameTargetProfileTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=Path(os.environ['BOOKS_PROFILE_REGRESSION_ROOT'])/str(uuid.uuid4())
  cls.root.mkdir(parents=True)
  cls.app=cls.root/'Application';cls.app.mkdir()
  cls.profile=cls.root/'Profile';data=cls.root/'Data';data.mkdir()
  db=data/'inventory.sqlite3'
  with contextlib.closing(sqlite3.connect(db)) as connection:
   connection.executescript('CREATE TABLE jobs(root TEXT);CREATE TABLE queue(path TEXT);CREATE TABLE files(root TEXT,path TEXT,size INTEGER,modified INTEGER,kind TEXT);');connection.commit()
  cls.environment=patch.dict(os.environ,dict(APPDATA=str(cls.root/'Roaming'),LOCALAPPDATA=str(cls.root/'Local'),TEMP=str(cls.root),TMP=str(cls.root),BOOKS_WORK_TEMP=str(cls.root)))
  cls.environment.start()
  cls.scanner=staticmethod(lifecycle.registered_bootstraps)
  cls.registry=patch.object(lifecycle,'registered_bootstraps',return_value=[]);cls.registry.start()
  plan=lifecycle.selection_plan('existing',str(db),application_dir=str(cls.app),profile_dir=str(cls.profile),config_paths=[])
  sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  result=lifecycle.commit_selection(plan,sha,require_package=False,process_name='BooksProfileFixtureNeverRunning.exe')
  cls.bootstrap=Path(result['bootstrap'])
 @classmethod
 def tearDownClass(cls):
  cls.registry.stop();cls.environment.stop()
 def test_existing_bootstrap_without_uninstall_location(self):
  # NSIS already supplied its separately registered InstallLocation. The
  # Uninstall scanner returns no bootstrap when that key lacks InstallLocation.
  result=lifecycle.legacy_update_plan(str(self.app),'0.28.6',process_name='BooksProfileFixtureNeverRunning.exe')
  authority=result['plan']['selection']['profile_source_authority']
  self.assertEqual(authority['bootstrap'],str(self.bootstrap))
  self.assertEqual(authority['profile'],str(self.profile))
  lifecycle._validate_profile_source_authority(self.profile,authority)
 def test_wrong_profile_or_account_refused(self):
  authority=lifecycle._profile_source_authority(self.profile,reviewed_bootstrap=self.bootstrap)
  for invalid in (dict(authority,profile=str(self.root/'Other')),dict(authority,account_sid='S-1-0-0')):
   with self.assertRaises(lifecycle.LifecycleRefused) as caught:lifecycle._validate_profile_source_authority(self.profile,invalid)
   self.assertEqual(caught.exception.code,'profile_account_not_confirmed')
 def test_uninstall_key_missing_location_is_not_discovered(self):
  class Key:
   def __enter__(self):return self
   def __exit__(self,*args):pass
  def value(key,name):
   if name=='DisplayName':return ('Books Arranger 0.28.6',1)
   raise FileNotFoundError(name)
  registry=SimpleNamespace(KEY_WOW64_64KEY=1,KEY_WOW64_32KEY=2,KEY_READ=4,HKEY_CURRENT_USER=0,
   OpenKey=lambda *args:Key(),QueryInfoKey=lambda key:(1,0,0),EnumKey=lambda key,index:'fixture',QueryValueEx=value)
  # Invoke the original scanner through the patch's saved callable, with a
  # private model of registry reads. No real registration is written.
  with patch.dict('sys.modules',winreg=registry):self.assertEqual(self.scanner(),[])

if __name__=='__main__':unittest.main()
