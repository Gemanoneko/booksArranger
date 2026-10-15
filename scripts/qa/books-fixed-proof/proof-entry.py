"""Fixed 13-case proof, trusted-bootstrap then exact frozen import/read fence."""
import sys, os, json, hashlib, tempfile, unittest, importlib.machinery
from pathlib import Path
ROOT=Path(r'C:\Antigravity Projects\Studio Illuminati\WIP\Books Arranger\scratch\resume-2026-10-15\proof-inputs-13')
OUTPUT=Path(r'C:\Antigravity Projects\Studio Illuminati\WIP\Books Arranger\scratch\resume-2026-10-15\proof-run-13-01')
MANIFEST=Path(__file__).with_name('input-manifest.json')
EXPECTED_MANIFEST_SHA='0d8039294b5e3fd07fba733f3eab6188b8b175eb315e55d5b38381132a5fafba'
raw=MANIFEST.read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED_MANIFEST_SHA:raise RuntimeError('Exact frozen import map changed')
manifest=json.loads(raw)
allowed={Path(tree['root']).joinpath(r['path']).resolve() for tree in manifest['trees'] if tree['root'].replace('\\','/').casefold() in (str(ROOT).replace('\\','/').casefold(),'c:/python314') for r in tree['records']}
allowed.update((Path(__file__).resolve(),MANIFEST.resolve()))
if Path.cwd().resolve()!=ROOT.resolve() or not (OUTPUT/'tmp').is_dir() or Path(tempfile.gettempdir()).resolve()!=(OUTPUT/'tmp').resolve():raise RuntimeError('Fixed cwd/private TEMP changed')
def canonical(value):
    p=Path(os.fsdecode(value))
    if not p.is_absolute():p=Path.cwd()/p
    return p.resolve()
def private_data(value):
    p=canonical(value)
    if p!=OUTPUT.resolve() and not p.is_relative_to(OUTPUT.resolve()):raise RuntimeError('Write outside owned proof output')
    return p
def audit(event,args):
    if event in ('subprocess.Popen','os.system','os.startfile','socket.__new__','socket.connect','os.add_dll_directory'):
        raise RuntimeError('Process/network/loader path modification forbidden in focused proof')
    if event=='open' and not isinstance(args[0],int):
        mode=args[1] or '';flags=args[2] or 0;p=canonical(args[0])
        writing=any(c in str(mode) for c in 'wax+') or bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        if writing:private_data(p)
        elif p not in allowed and p!=OUTPUT.resolve() and not p.is_relative_to(OUTPUT.resolve()):
            # SourceFileLoader treats an absent unlisted cache as a cache miss.
            raise FileNotFoundError('Unlisted source/runtime/cache read refused: '+str(p))
    elif event=='sqlite3.connect':private_data(args[0])
    elif event in ('os.remove','os.rmdir','os.mkdir'):private_data(args[0])
    elif event in ('os.rename','os.link','os.symlink'):
        private_data(args[0]);private_data(args[1])
class FrozenPathFinder:
    @classmethod
    def find_spec(cls,fullname,path=None,target=None):
        spec=importlib.machinery.PathFinder.find_spec(fullname,path,target)
        if spec is not None:
            if spec.origin is None:
                raise ModuleNotFoundError('Unenrolled namespace import refused: '+fullname)
            if spec.origin not in ('built-in','frozen') and canonical(spec.origin) not in allowed:
                raise ModuleNotFoundError('Unlisted executable import origin refused: '+fullname)
        return spec
sys.addaudithook(audit)
sys.meta_path=[FrozenPathFinder if f is importlib.machinery.PathFinder else f for f in sys.meta_path]
sys.path.insert(0,str(ROOT))
# Refusal controls create only trusted private fixture bytes; none may execute.
canary=OUTPUT/'unlisted_books_canary.py'
canary.write_text("raise AssertionError('UNLISTED CODE EXECUTED')\n",encoding='utf8')
sys.path.insert(0,str(OUTPUT))
try:
    try:__import__('unlisted_books_canary')
    except ModuleNotFoundError:pass
    else:raise RuntimeError('Unlisted shadow import was accepted')
finally:sys.path.remove(str(OUTPUT))
try:
    sys.audit('open',str(ROOT/'__pycache__'/'unlisted_books_cache.cpython-314.pyc'),'r',0)
except FileNotFoundError as error:
    if not str(error).startswith('Unlisted source/runtime/cache read refused: '):raise
else:raise RuntimeError('Unlisted cache read was accepted')
print('Books import fence controls: unlisted shadow import/cache audit refused',flush=True)
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_attention_failure_policy.py')
if suite.countTestCases()!=13:raise RuntimeError('Expected exact 13 focused cases')
result=unittest.TextTestRunner(verbosity=2).run(suite)
ok=result.wasSuccessful() and result.testsRun==13 and not result.skipped
print('Books focused maintenance proof: tests=%d skipped=%d ok=%s'%(result.testsRun,len(result.skipped),ok),flush=True)
raise SystemExit(0 if ok else 1)
