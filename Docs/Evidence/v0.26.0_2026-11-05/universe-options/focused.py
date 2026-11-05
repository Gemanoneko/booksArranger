import os,pathlib,sys,unittest
root=pathlib.Path(__file__).parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r1')
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
sys.path[:0]=[str(source),str(source/'tests')];os.chdir(source)
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
for name,module in list(sys.modules.items()):
 if name.startswith('test_'):
  for attr in ('AREA','ROOT','SCRATCH'):
   value=getattr(module,attr,None)
   if isinstance(value,pathlib.Path) and 'scratch' in value.parts:
    location=root/'f'/name;location.mkdir(parents=True,exist_ok=True);setattr(module,attr,location)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
