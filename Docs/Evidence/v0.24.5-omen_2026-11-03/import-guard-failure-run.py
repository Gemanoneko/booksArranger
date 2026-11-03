import json, os, pathlib, socket, subprocess, sys, unittest
root = pathlib.Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(root / 'source'), str(root / 'source' / 'tests')]
os.environ['BOOKS_TEST_ROOT'] = str(root / 'fixtures')
(root / 'fixtures').mkdir(exist_ok=True)
def deny(*args, **kwargs):
    raise AssertionError('Unexpected process/network access in metadata-only tests')
subprocess.Popen = deny
os.system = deny
socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
def audit(event, args):
    if event in ('subprocess.Popen', 'socket.connect', 'os.system'):
        deny()
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = os.fsdecode(args[0])
        if path.lower().startswith(('z:', '\\\\')) or pathlib.Path(path).suffix.lower() in ('.m4b', '.mp3', '.flac', '.wav'):
            raise AssertionError('Unexpected media/live file open: ' + path)
sys.addaudithook(audit)
selectors = ['test_omen_0245', 'test_series_identity_242', 'test_shared_routing', 'test_organization']
suite = unittest.defaultTestLoader.loadTestsFromNames(selectors)
count = suite.countTestCases()
result = unittest.TextTestRunner(verbosity=2).run(suite)
summary = {'selectors': selectors, 'loaded': count, 'executed': result.testsRun, 'skipped': len(result.skipped),
           'failures': len(result.failures), 'errors': len(result.errors)}
(root / 'test-summary.json').write_text(json.dumps(summary), encoding='utf8')
print(json.dumps(summary))
sys.exit(0 if result.wasSuccessful() and count > 0 and result.testsRun == count and not result.skipped else 1)
