import os,pathlib,sys,unittest
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/approve-retrieved-20261105')
scratch=pathlib.Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
os.chdir('C:/Antigravity Projects/a26');sys.path[:0]=[str(source),str(source/'tests')]
names=sys.argv[2:]
if sys.argv[1]=='baseline':sys.path.insert(0,str(scratch/'baseline-source'))
suite=unittest.defaultTestLoader.loadTestsFromNames(names)
for name,module in list(sys.modules.items()):
    if name.startswith('test_') and isinstance(getattr(module,'AREA',None),pathlib.Path):
        module.AREA=pathlib.Path('C:/Antigravity Projects/a26/f');module.AREA.mkdir(exist_ok=True)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
