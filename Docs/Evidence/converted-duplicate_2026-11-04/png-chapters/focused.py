import os,pathlib,sys,unittest
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/m4b-chapter-image-025-20261104')
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
os.chdir(source);sys.path[:0]=[str(source),str(source/'tests')]
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
module=sys.modules.get('test_m4b_preservation')
if module is not None:module.__file__=str(pathlib.Path(__file__).resolve().parent/'tests'/'test_m4b_preservation.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
