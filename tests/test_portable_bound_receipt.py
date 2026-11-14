"""Small prebuild checks for bounded migration diagnostics and CLI identity."""
import contextlib,hashlib,json,sqlite3,subprocess,sys,unittest
from pathlib import Path
from portable_catalog_paths import migrate

class BoundReceiptTests(unittest.TestCase):
 def test_compact_summary_keeps_mutation_and_manifest(self):
  with contextlib.closing(sqlite3.connect(':memory:')) as db:
   db.executescript('CREATE TABLE working_files(path TEXT);CREATE TABLE audio_jobs(manifest TEXT);')
   db.execute('INSERT INTO working_files VALUES(?)',(r'C:\old\cover.png',));db.execute('INSERT INTO audio_jobs VALUES(?)',('immutable history',))
   result=migrate(db,[r'C:\old'],r'I:\new')
   self.assertEqual(result['count'],1);self.assertFalse(result['authority']);self.assertLess(len(json.dumps(result)),1024)
   self.assertEqual(db.execute('SELECT path FROM working_files').fetchone()[0],r'I:\new\cover.png')
   self.assertEqual(db.execute('SELECT manifest FROM audio_jobs').fetchone()[0],'immutable history')
 def test_cli_import_shares_typed_exception(self):
  source=Path(__file__).resolve().parents[1]/'storage_lifecycle.py'
  code="import runpy,sys,contextlib,io;sys.argv=[sys.argv[1],'--help']\ntry:\n with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(sys.argv[0],run_name='__main__')\nexcept SystemExit as e:\n assert e.code==0\nimport storage_lifecycle as m\nassert m.LifecycleRefused.__module__=='__main__'\nimport portable_storage_migration as p\ntry:m._need(False,'typed_probe')\nexcept m.LifecycleRefused as e:assert e.code=='typed_probe'\nprint('canonical CLI module identity OK')"
  result=subprocess.run([sys.executable,'-I','-B','-X','utf8','-c',code,str(source)],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  self.assertIn('canonical CLI module identity OK',result.stdout)

if __name__=='__main__':unittest.main()
