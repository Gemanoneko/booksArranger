import hashlib,json,os,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing
from desktop_catalog import inspect_folder
from native_io import BoundaryError
AREA=Path(__file__).resolve().parents[1]/'scratch'/'desktop-catalog-tests';AREA.mkdir(parents=True,exist_ok=True)
class CatalogSelectionTests(unittest.TestCase):
 def roots(self,base):return {'Audiobooks':str(base/'a'),'Podcasts':str(base/'p'),'Ebooks':str(base/'e')}
 def test_new_selection_probe_does_not_create_directory_or_database(self):
  with tempfile.TemporaryDirectory(dir=AREA) as t:
   base=Path(t);folder=base/'not-created';self.assertEqual(inspect_folder(folder,'new',self.roots(base))['mode'],'new');self.assertFalse(folder.exists())
 def test_existing_unknown_nonempty_and_corrupt_are_preserved(self):
  with tempfile.TemporaryDirectory(dir=AREA) as t:
   base=Path(t);folder=base/'data';folder.mkdir();db=folder/'inventory.sqlite3';raw=b'not a sqlite database';db.write_bytes(raw)
   for mode in ('existing','new'):
    with self.assertRaises((ValueError,sqlite3.DatabaseError)):inspect_folder(folder,mode,self.roots(base))
   self.assertEqual(db.read_bytes(),raw);self.assertEqual([p.name for p in folder.iterdir()],['inventory.sqlite3'])
 def test_recognized_existing_is_read_only_and_keeps_recovery_bytes(self):
  with tempfile.TemporaryDirectory(dir=AREA) as t:
   base=Path(t);folder=base/'data';folder.mkdir();db=folder/'inventory.sqlite3'
   with closing(sqlite3.connect(db)) as c:
    c.executescript('CREATE TABLE jobs(root);CREATE TABLE queue(root);CREATE TABLE files(root,path,size,modified,kind);')
   recovery=folder/'recovery';recovery.mkdir();(recovery/'receipt.json').write_bytes(b'unique recovery')
   digest=hashlib.sha256(db.read_bytes()).hexdigest();self.assertEqual(inspect_folder(folder,'existing',self.roots(base))['mode'],'existing');self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),digest);self.assertEqual((recovery/'receipt.json').read_bytes(),b'unique recovery');self.assertFalse(Path(str(db)+'-wal').exists())
 def test_source_or_install_location_refused_without_creation(self):
  with tempfile.TemporaryDirectory(dir=AREA) as t:
   base=Path(t);roots=self.roots(base)
   for folder,install in [(base/'a'/'data',()),(base/'install'/'data',(base/'install',))]:
    with self.assertRaises(ValueError):inspect_folder(folder,'new',roots,install)
    self.assertFalse(folder.exists())
 def test_hardlinked_database_is_not_adopted(self):
  with tempfile.TemporaryDirectory(dir=AREA) as t:
   base=Path(t);folder=base/'data';folder.mkdir();db=folder/'inventory.sqlite3';db.write_bytes(b'unverified');os.link(db,base/'alias')
   with self.assertRaises(ValueError):inspect_folder(folder,'existing',self.roots(base))
   self.assertEqual(db.read_bytes(),b'unverified')
 def test_extra_stream_database_is_not_adopted(self):
  with tempfile.TemporaryDirectory(dir=AREA) as t:
   base=Path(t);folder=base/'data';folder.mkdir();db=folder/'inventory.sqlite3';db.write_bytes(b'unverified');Path(str(db)+':Zone.Identifier').write_bytes(b'mark')
   with self.assertRaises(BoundaryError):inspect_folder(folder,'existing',self.roots(base))
   self.assertEqual(Path(str(db)+':Zone.Identifier').read_bytes(),b'mark')

class SettingsPreservationTests(unittest.TestCase):
 def test_settings_save_creates_only_explicit_profile_file(self):
  from desktop_settings import save
  with tempfile.TemporaryDirectory(dir=AREA) as t:
   base=Path(t);file=base/'profile'/'desktop-settings.json';folder=base/'uncreated-data'
   save(file,folder);self.assertEqual(json.loads(file.read_text())['dataDir'],str(folder));self.assertFalse(folder.exists())
 def test_existing_settings_are_never_overwritten(self):
  from desktop_settings import save
  with tempfile.TemporaryDirectory(dir=AREA) as t:
   base=Path(t);file=base/'desktop-settings.json';raw=b'unknown existing settings';file.write_bytes(raw)
   with self.assertRaises(RuntimeError):save(file,base/'data')
   self.assertEqual(file.read_bytes(),raw)
