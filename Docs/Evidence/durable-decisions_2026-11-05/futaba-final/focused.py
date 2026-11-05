import os,pathlib,sys,unittest
root=pathlib.Path(__file__).resolve().parent
source=root/'src'
arena=pathlib.Path('C:/Antigravity Projects/d26')
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
os.chdir(arena);sys.path[:0]=[str(source),str(source/'tests')]
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
for name,module in list(sys.modules.items()):
    if not name.startswith('test_'):continue
    value=getattr(module,'AREA',None)
    if isinstance(value,pathlib.Path):
        mapped=arena/'f'/name;mapped.mkdir(parents=True,exist_ok=True);setattr(module,'AREA',mapped)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())