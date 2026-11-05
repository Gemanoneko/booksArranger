import os,pathlib,sys,unittest
root=pathlib.Path(__file__).resolve().parent
source=root/'src'
arena=pathlib.Path('C:/Antigravity Projects/f26')
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
os.chdir(arena);sys.path[:0]=[str(source),str(source/'tests')]
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
for name,module in list(sys.modules.items()):
    if name.startswith('test_') and isinstance(getattr(module,'AREA',None),pathlib.Path):
        module.AREA=arena/'f';module.AREA.mkdir(exist_ok=True)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())