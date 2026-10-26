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

# Futaba's 0.22.1 QA, M-3: after the app was hard-killed while its engine wrote (a 24,000-book catalog), the next start
# said "Catalog integrity check failed; folder retained" though the catalog was healthy (a normal open: quick_check ok).
# The writer below is a real process with the catalog's own pragmas (WAL), ended by TerminateProcess in the middle of a
# checkpoint: the main file then holds the low pages of the new state and none of the pages past its old end.
WRITER=r'''
import os,sqlite3,sys
db=sqlite3.connect(sys.argv[1],isolation_level=None)
db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=NORMAL');db.execute('PRAGMA wal_autocheckpoint=0')
db.executescript('CREATE TABLE IF NOT EXISTS jobs(root);CREATE TABLE IF NOT EXISTS queue(root);CREATE TABLE IF NOT EXISTS files(root,path,size,modified,kind,metadata);CREATE INDEX IF NOT EXISTS files_path ON files(path)')
n=0
while True:
    db.execute('BEGIN')
    for i in range(4000):
        n+=1;db.execute('INSERT INTO files VALUES(?,?,?,?,?,?)',('Z:\\Audiobooks','Z:\\Audiobooks\\Author %d\\Book %d\\%05d.mp3'%(n%977,n%4013,n),n,n,'audiobook',os.urandom(300).hex()))
    db.execute('DELETE FROM files WHERE rowid%7=0 AND rowid>?',(n-4000,))
    db.execute('COMMIT')
    if n>=int(sys.argv[2]):
        print('CHECKPOINT',os.path.getsize(sys.argv[1]),db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0],flush=True)
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)');print('DONE',flush=True);sys.stdin.read()
'''
class CrashRecoveryTests(unittest.TestCase):
 def roots(self,base):return {'Audiobooks':str(base/'a'),'Podcasts':str(base/'p'),'Ebooks':str(base/'e')}
 def killed_mid_checkpoint(self,folder):
  """The catalog of a writer ended in the middle of a WAL checkpoint (main file part written, the WAL complete)."""
  import subprocess,sys,time
  db=folder/'inventory.sqlite3'
  # First commits checkpointed, so the main file is a real older state of the catalog.
  child=subprocess.Popen([sys.executable,'-I','-B','-c',WRITER,str(db),'20000'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   self.assertEqual(child.stdout.readline().split()[0],b'CHECKPOINT');self.assertEqual(child.stdout.readline().strip(),b'DONE')
  finally:child.kill();child.wait(30)
  child=subprocess.Popen([sys.executable,'-I','-B','-c',WRITER,str(db),'60000'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   line=child.stdout.readline().split();self.assertEqual(line[0],b'CHECKPOINT')
   before,final=int(line[1]),int(line[2]);self.assertGreater(final,before+4*1024*1024,'the checkpoint grows the main file')
   deadline=time.monotonic()+60
   while os.path.getsize(db)<before+(final-before)//3 and time.monotonic()<deadline:time.sleep(.001)
   child.kill()  # TerminateProcess, as taskkill /F: no close, no checkpoint end
   child.wait(30)
  finally:
   if child.poll() is None:child.kill();child.wait(30)
  size=os.path.getsize(db)
  self.assertTrue(before<size<final,'killed in the middle of the checkpoint (%d < %d < %d)'%(before,size,final))
  self.assertGreater(os.path.getsize(str(db)+'-wal'),0,'the WAL holds the committed state')
  return db
 def test_a_healthy_catalog_with_its_wal_is_opened_after_a_hard_kill_mid_write(self):
  with tempfile.TemporaryDirectory(dir=AREA) as t:
   base=Path(t);folder=base/'data';folder.mkdir();db=self.killed_mid_checkpoint(folder)
   main_before=hashlib.sha256(db.read_bytes()).hexdigest();wal_before=hashlib.sha256(Path(str(db)+'-wal').read_bytes()).hexdigest()
   # Positive control: the main file alone (what an immutable open reads) is not a valid catalog.
   with closing(sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True)) as alone:
    with self.assertRaises(sqlite3.DatabaseError):
     verdict=alone.execute('PRAGMA quick_check').fetchone()[0]
     if verdict!='ok':raise sqlite3.DatabaseError(verdict)
   self.assertEqual(inspect_folder(folder,'existing',self.roots(base))['mode'],'existing')
   # Read-only: the catalog and its WAL are untouched, so the engine's own open recovers every committed row.
   self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),main_before)
   self.assertEqual(hashlib.sha256(Path(str(db)+'-wal').read_bytes()).hexdigest(),wal_before)
   with closing(sqlite3.connect(db)) as c:
    self.assertEqual(c.execute('PRAGMA quick_check').fetchone()[0],'ok');self.assertGreaterEqual(c.execute('SELECT count(*) FROM files').fetchone()[0],50000)
 def test_a_damaged_catalog_is_still_refused(self):
  # Control: the same torn main file without its WAL is damaged, and the check still refuses it, changing nothing.
  with tempfile.TemporaryDirectory(dir=AREA) as t:
   base=Path(t);folder=base/'data';folder.mkdir();db=self.killed_mid_checkpoint(folder)
   for suffix in ('-wal','-shm'):Path(str(db)+suffix).unlink(missing_ok=True)
   raw=hashlib.sha256(db.read_bytes()).hexdigest()
   with self.assertRaisesRegex((ValueError,sqlite3.DatabaseError),'integrity|malformed'):inspect_folder(folder,'existing',self.roots(base))
   self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),raw)
