import os,pathlib,sys,unittest
root=pathlib.Path(__file__).resolve().parent
source=root/'src'
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
os.chdir(source)
sys.path[:0]=[str(source),str(source/'tests')]
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())