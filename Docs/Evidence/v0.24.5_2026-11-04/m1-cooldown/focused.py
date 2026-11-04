import pathlib, sys, unittest, os
root=pathlib.Path(__file__).resolve().parent
src=root/'src'
os.chdir(src)
sys.path[:0]=[str(src),str(src/'tests')]
names=[
'test_gap_fill.ClientLockTests',
'test_status_snapshot.SharedSnapshotTests',
'test_attempt_working_lifecycle.WorkingLifecycleTests.test_retained_producer_holds_only_its_book_and_three_independent_jobs_finish',
'test_web.BrowserTests.test_malformed_payloads_and_configured_roots_only',
]
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:] or names)
for name,module in list(sys.modules.items()):
    if not name.startswith('test_'):continue
    for attr in ('AREA','SCRATCH','ROOT'):
        value=getattr(module,attr,None)
        if isinstance(value,pathlib.Path) and 'scratch' in value.parts:
            mapped=root/'fixtures'/name
            mapped.mkdir(parents=True,exist_ok=True)
            setattr(module,attr,mapped)
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())

