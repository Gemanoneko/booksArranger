import os,pathlib,sys,unittest
root=pathlib.Path(__file__).resolve().parent
source=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/converted-duplicate-qa-20261104/src')
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
os.chdir(source);sys.path[:0]=[str(source),str(source/'tests')]
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
for name,module in list(sys.modules.items()):
    if not name.startswith('test_'):continue
    for attr in ('AREA','SCRATCH','ROOT'):
        value=getattr(module,attr,None)
        if isinstance(value,pathlib.Path) and 'scratch' in value.parts:
            mapped=root/'fixtures'/name;mapped.mkdir(parents=True,exist_ok=True);setattr(module,attr,mapped)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
