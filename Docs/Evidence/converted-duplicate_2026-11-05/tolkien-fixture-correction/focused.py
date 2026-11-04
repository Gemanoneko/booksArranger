import os,pathlib,sys,unittest
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/tolkien-fixtures-025-20261105')
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
# All source/output paths in this module are nonexistent metadata-only strings.
# A short existing cwd keeps those strings inside the unchanged Windows path bound.
os.chdir('C:/Antigravity Projects/Studio Illuminati')
sys.path[:0]=[str(source),str(source/'tests')]
suite=unittest.defaultTestLoader.loadTestsFromNames(['test_series_identity_242'])
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
