"""Finite native owner for installer build/release workers (Windows only).
Bootstrap runtime is a development prerequisite, never part of installed app.
"""
import ctypes
from ctypes import wintypes
import contextlib
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

PYTHON_SHA256 = 'd718435b892db4ad5b547d12fec61be7baa7faf7a58d857ea58053be24c7a000'  # Python 3.14.10 (ruling 72g, 2026-10-30); scripts/guarded-io.mjs pins the same
ROOT = Path(__file__).absolute().parent.parent
# Bootstrap native API is self-contained; no checkout modules run until leased.
K = None  # Loaded only by bootstrap, so manifest validation has no native side effects.
class Info(ctypes.Structure):
    _fields_ = [('attributes',wintypes.DWORD),('creation',wintypes.FILETIME),('access',wintypes.FILETIME),('write',wintypes.FILETIME),('volume',wintypes.DWORD),('size_high',wintypes.DWORD),('size_low',wintypes.DWORD),('links',wintypes.DWORD),('index_high',wintypes.DWORD),('index_low',wintypes.DWORD)]

def bootstrap(stack):
    global K
    if K is None and os.name == 'nt': K = ctypes.WinDLL('kernel32', use_last_error=True)
    if K is None: raise RuntimeError('Native installer guard requires Windows')
    K.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];K.CreateFileW.restype=wintypes.HANDLE
    K.GetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_void_p];K.GetFileInformationByHandle.restype=wintypes.BOOL
    K.CloseHandle.argtypes=[wintypes.HANDLE]
    def hold(path,directory):
        h=K.CreateFileW(str(path),0x81,1,None,3,0x00200000|(0x02000000 if directory else 0),None)
        if h==ctypes.c_void_p(-1).value: raise RuntimeError('Bootstrap identity cannot be retained')
        stack.callback(K.CloseHandle,h);i=Info()
        if not K.GetFileInformationByHandle(h,ctypes.byref(i)) or i.attributes&0x400 or bool(i.attributes&0x10)!=directory or not directory and i.links!=1: raise RuntimeError('Bootstrap reparse/link/type refused')
    for path in [ROOT,Path(sys.executable).absolute().parent]:
        for p in reversed([path,*path.parents]): hold(p,True)
    hold(Path(sys.executable),False)
    if hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()!=PYTHON_SHA256: raise RuntimeError('Bootstrap Python fingerprint changed')
    for name in ['native_io.py','desktop_host.py','scripts/build_fs_guard.py','scripts/build_external_tools.py','scripts/build_native.py']:
        p=ROOT/name
        for d in reversed([p.parent,*p.parent.parents]): hold(d,True)
        hold(p,False)
    sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))

def lease_check(proof):
    # Open the exact process generation and image; never interpret a numeric PID
    # alone as authority. This operation performs no mutation/process termination.
    K.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];K.OpenProcess.restype=wintypes.HANDLE
    K.GetProcessTimes.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME)];K.GetProcessTimes.restype=wintypes.BOOL
    K.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)];K.QueryFullProcessImageNameW.restype=wintypes.BOOL
    K.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];K.WaitForSingleObject.restype=wintypes.DWORD
    h=K.OpenProcess(0x100000|0x1000|0x400,False,proof['supervisor']['pid'])
    if not h:raise RuntimeError('Supervisor proof unavailable')
    try:
        c,e,k,u=(wintypes.FILETIME() for _ in range(4));image=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(image))
        if not K.GetProcessTimes(h,ctypes.byref(c),ctypes.byref(e),ctypes.byref(k),ctypes.byref(u)) or not K.QueryFullProcessImageNameW(h,0,image,ctypes.byref(size)) or K.WaitForSingleObject(h,0)!=258:raise RuntimeError('Supervisor ended or identity unavailable')
        if ((c.dwHighDateTime<<32)|c.dwLowDateTime)!=int(proof['supervisor']['creation_filetime']) or os.path.normcase(image.value)!=os.path.normcase(str(Path(sys.executable).absolute())):raise RuntimeError('Supervisor generation/image mismatch')
        # Bind image to the fixed supervisor program, not merely any Python PID.
        nt=ctypes.WinDLL('ntdll');nt.NtQueryInformationProcess.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.ULONG,ctypes.POINTER(wintypes.ULONG)];nt.NtQueryInformationProcess.restype=wintypes.LONG
        needed=wintypes.ULONG();nt.NtQueryInformationProcess(h,60,None,0,ctypes.byref(needed))
        if not needed.value or needed.value>131072:raise RuntimeError('Supervisor command identity unavailable')
        buffer=ctypes.create_string_buffer(needed.value)
        if nt.NtQueryInformationProcess(h,60,buffer,len(buffer),ctypes.byref(needed))<0:raise RuntimeError('Supervisor command identity refused')
        class Unicode(ctypes.Structure):_fields_=[('length',wintypes.USHORT),('maximum',wintypes.USHORT),('buffer',ctypes.c_void_p)]
        command=Unicode.from_buffer(buffer)
        text=ctypes.wstring_at(command.buffer,command.length//2)
        shell=ctypes.WinDLL('shell32');shell.CommandLineToArgvW.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_int)];shell.CommandLineToArgvW.restype=ctypes.POINTER(wintypes.LPWSTR)
        argc=ctypes.c_int();argv=shell.CommandLineToArgvW(text,ctypes.byref(argc))
        try:
            args=[argv[n] for n in range(argc.value)]
            expected=[str(Path(sys.executable).absolute()),'-I','-B',str(ROOT/'scripts'/'build_native.py')]
            if [os.path.normcase(a) for a in args]!=[os.path.normcase(a) for a in expected]:raise RuntimeError('Supervisor program identity mismatch')
        finally:
            K.LocalFree.argtypes=[ctypes.c_void_p];K.LocalFree(ctypes.cast(argv,ctypes.c_void_p))
        from build_fs_guard import BuildTree
        with BuildTree(ROOT) as tree:
            lease=tree.child(proof['lease_path']);tree.directory(lease.parent)
            # Supervisor retains a read handle denying write/delete. A plain
            # unleased JSON file cannot confer the capability.
            write=K.CreateFileW(str(lease),0x40000000,7,None,3,0x00200000,None)
            if write!=ctypes.c_void_p(-1).value:
                K.CloseHandle(write);raise RuntimeError('Lease is not natively retained')
            if ctypes.get_last_error()!=32:raise RuntimeError('Lease retention cannot be established')
            tree.protect(lease)
            actual=json.loads(lease.read_text('utf8'))
            if actual!=proof or proof['root']!=str(ROOT) or proof['deadline']<=time.time()*1000 or proof['deadline']>time.time()*1000+605000:raise RuntimeError('Lease nonce/context/expiration mismatch')
    finally:K.CloseHandle(h)

def protect_tree(tree, folder):
    tree.directory(folder)
    for entry in os.scandir(folder):
        p=Path(entry.path)
        if p==ROOT and False:continue
        if entry.is_dir(follow_symlinks=False):protect_tree(tree,p)
        else:tree.protect(p)

def validate_pack_inputs(config, lock):
    """Validate the finite, checked-in pack input inventory without touching files."""
    import re
    if not isinstance(config,dict) or not isinstance(lock,dict): raise RuntimeError('Pack inventory and lock must be objects')
    if config.get('schema') != 'books-pack-inputs-v1' or lock.get('lockfileVersion') != 3:
        raise RuntimeError('Unsupported pack input inventory')
    if config.get('seedDirectory') != 'build-cache/pack-inputs':
        raise RuntimeError('Unexpected pack seed directory')
    def relative(name):
        return isinstance(name,str) and bool(name) and not any(c in name for c in ('\\', ':', '\0')) and all(p not in ('', '.', '..') for p in name.split('/'))
    for field in ('files', 'productionFiles'):
        values = config.get(field)
        if not isinstance(values,dict) or not values: raise RuntimeError('Empty pack file inventory')
        seen=set()
        for name,facts in values.items():
            if not relative(name) or name.casefold() in seen: raise RuntimeError('Unsafe/duplicate pack member')
            seen.add(name.casefold())
            if not isinstance(facts,dict) or set(facts)!= {'size','sha256'} or type(facts['size']) is not int or facts['size']<0 or not re.fullmatch('[0-9a-f]{64}',str(facts['sha256'])):
                raise RuntimeError('Malformed pack file fingerprint')
    packages=config.get('productionPackages')
    if not isinstance(packages,list) or not packages: raise RuntimeError('Empty production graph')
    locked=lock.get('packages')
    if not isinstance(locked,dict): raise RuntimeError('Malformed locked package graph')
    for name,value in locked.items():
        if not isinstance(name,str) or name and not relative(name) or not isinstance(value,dict) or not isinstance(value.get('version'),str) or not value['version'] or 'dev' in value and type(value['dev']) is not bool:
            raise RuntimeError('Malformed locked package record')
    expected={name:value['version'] for name,value in locked.items() if name and value.get('dev') is not True}
    actual={}
    for item in packages:
        if not isinstance(item,dict) or set(item)!={'path','version'} or not relative(item['path']) or not item['path'].startswith('node_modules/') or item['path'] in actual:
            raise RuntimeError('Malformed production package membership')
        actual[item['path']]=item['version']
    if actual!=expected: raise RuntimeError('Production package graph differs from lockfile')
    for name in config['productionFiles']:
        owners=[p for p in actual if name.startswith(p+'/')]
        if not owners: raise RuntimeError('Production file has no approved package')
        owner=max(owners,key=len)
        if '/node_modules/' in '/'+name[len(owner)+1:]: raise RuntimeError('Unapproved nested production package')
    if any(p+'/package.json' not in config['productionFiles'] for p in actual):
        raise RuntimeError('Production package metadata missing')
    tools=config.get('tools',{})
    expected_tools={'electron':'electron/electron-v44.4.5-win32-x64.zip','nsis':'nsis/Bin/makensis.exe','nsisRoot':'nsis','nsisResources':'nsis-resources','seven':'seven/bin/7za.exe','icons':'icons/icon-tool.js','npm':'npm/bin/npm-cli.js'}
    if tools!=expected_tools or any(tools[k] not in config['files'] for k in ('electron','nsis','seven','icons','npm')):
        raise RuntimeError('Unexpected pack tool entrypoints')
    if (config.get('electronVersion'),config.get('builderVersion'),config.get('iconConverterVersion'))!=('44.4.5','26.15.3','1.2.3'):
        raise RuntimeError('Pack tool version changed')
    return config


def strict_json(text):
    def pairs(items):
        result={}
        for name,value in items:
            if name in result: raise RuntimeError('Duplicate JSON member')
            result[name]=value
        return result
    try:return json.loads(text,object_pairs_hook=pairs)
    except (ValueError,TypeError) as error:raise RuntimeError('Malformed pack JSON') from error


def load_pack_inputs(root=ROOT):
    config=strict_json((root/'scripts/build-inputs.json').read_text('utf8'))
    if not isinstance(config,dict): raise RuntimeError('Pack inventory must be an object')
    lock_bytes=(root/'package-lock.json').read_bytes()
    if hashlib.sha256(lock_bytes).hexdigest()!=config.get('packageLockSha256'):
        raise RuntimeError('Pack lockfile fingerprint changed')
    return validate_pack_inputs(config,strict_json(lock_bytes))


def retain_pack_inputs(tree):
    config=load_pack_inputs()
    seed=ROOT/config['seedDirectory']
    # Exact membership, ordinary files and native deny-write/delete holds persist
    # in the supervisor's existing BuildTree until its owned Job closes.
    if tree.tree_manifest(seed)!=config['files']:
        raise RuntimeError('Private pack inputs differ or contain unapproved files')
    for relative,facts in config['productionFiles'].items():
        tree.protect(ROOT/relative,facts)
    return {'root':str(seed),'config_sha256':hashlib.sha256((ROOT/'scripts/build-inputs.json').read_bytes()).hexdigest()}


def main():
    with contextlib.ExitStack() as stack:
        bootstrap(stack)
        request=json.loads(sys.stdin.read())
        if sys.argv[1:]==['lease-check']:
            lease_check(request);print(json.dumps({'valid':True}));return
        mode=request.get('mode');script=request.get('script')
        fixed={'build':'scripts/build-step.mjs','release':'scripts/release.mjs','probe':'tests/guarded-owner-probe.mjs'}
        if mode not in fixed or script!=fixed[mode] or request.get('root')!=str(ROOT) or request.get('timeoutMs')!=600000:raise RuntimeError('Unallowlisted build/release request')
        from build_fs_guard import BuildTree
        from native_io import OwnedProcessJob
        from desktop_host import owner_proof
        with BuildTree(ROOT) as tree:
            for entry in os.scandir(ROOT):
                if entry.name in {'.git','scratch','dist','build-cache','data','Docs'}:continue
                p=Path(entry.path)
                if entry.is_dir(follow_symlinks=False):protect_tree(tree,p)
                else:tree.protect(p)
            if mode=='release':
                protect_tree(tree,ROOT/'dist')
                protect_tree(tree,ROOT/'Docs')
            owned=tree.fresh(ROOT/'build-cache'/'builds')
            # The proof helper binds retained process handles. For our own PID
            # acquire a real handle instead of fabricating a Popen generation.
            K.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];K.OpenProcess.restype=wintypes.HANDLE
            own=K.OpenProcess(0x100000|0x1000,False,os.getpid())
            try:
                class Self:pass
                self=Self();self._handle=own;self.pid=os.getpid()
                identity=owner_proof(self,sys.executable)
            finally:K.CloseHandle(own)
            proof={'schema':'books-build-lease-v1','mode':mode,'root':str(ROOT),'ownedRoot':str(owned),'lease_path':str(owned/'lease.json'),'nonce':secrets.token_hex(32),'deadline':int((time.time()+590)*1000),'supervisor':identity,'node':request['node']}
            from native_io import DirectoryBoundary,VerifiedFile
            externals={}
            tools={'git':'C:/Program Files/Git/cmd/git.exe'} if mode in {'build','release'} else {}
            if mode=='release':tools['gh']='C:/Program Files/GitHub CLI/gh.exe'
            for name,location in tools.items():
                if name=='git':
                    from build_external_tools import retain_git
                    externals[name]=retain_git(stack)
                    continue
                path=Path(location).absolute()
                stack.enter_context(DirectoryBoundary(path.anchor,path.parent))
                held=stack.enter_context(VerifiedFile(path))
                if held.facts()['links']!=1:raise RuntimeError('External tool hardlink refused')
                externals[name]=str(path)
            proof['executables']=externals
            if mode=='build':proof['pack_inputs']=retain_pack_inputs(tree)
            # Publish capability bytes only after external executables are held.
            node=Path(request['node']).absolute()
            tree.write(owned/'lease.json',[json.dumps(proof,sort_keys=True).encode()])
            # External Node runtime uses retained ordinary ancestry and image;
            # it is allowed only if it matches the invoker's explicit fingerprint.
            from native_io import DirectoryBoundary,VerifiedFile
            with DirectoryBoundary(node.anchor,node.parent),VerifiedFile(node) as executable:
                if executable.facts()['links']!=1 or executable.sha256()!=request['node_sha256']:raise RuntimeError('Node runtime changed')
                env={k:v for k,v in os.environ.items() if k.upper() not in {'NODE_OPTIONS','NODE_PATH','GH_TOKEN','GITHUB_TOKEN','GH_ENTERPRISE_TOKEN','GITHUB_ENTERPRISE_TOKEN'}}
                env.update({'TEMP':str(owned),'TMP':str(owned),'ELECTRON_BUILDER_CACHE':str(owned/'builder-cache'),'npm_config_cache':str(owned/'npm-cache')})
                if mode=='build':
                    # A finite environment; no user config, signing credentials,
                    # loader injection, network mirror or build override inherits.
                    env={'SystemRoot':os.environ.get('SystemRoot','C:\\Windows'),'WINDIR':os.environ.get('WINDIR','C:\\Windows'),'ComSpec':'C:\\Windows\\System32\\cmd.exe','PATH':str(node.parent)+';C:\\Program Files\\Git\\cmd;C:\\Windows\\System32',
                         'TEMP':str(owned),'TMP':str(owned),'USERPROFILE':str(owned/'profile'),'HOME':str(owned/'profile'),'APPDATA':str(owned/'profile/Roaming'),'LOCALAPPDATA':str(owned/'profile/Local'),
                         'ELECTRON_BUILDER_CACHE':str(owned/'builder-cache'),'npm_config_cache':str(owned/'npm-cache'),'npm_config_userconfig':str(owned/'empty.npmrc'),'npm_config_globalconfig':str(owned/'empty-global.npmrc'),'npm_config_update_notifier':'false','npm_config_audit':'false','npm_config_fund':'false'}
                    for directory in ['profile/Roaming','profile/Local','builder-cache','npm-cache']:tree.directory(owned/directory,create=True)
                    tree.write(owned/'empty.npmrc',[b'']);tree.write(owned/'empty-global.npmrc',[b''])
                child=subprocess.Popen([str(node),str(ROOT/script),'--owned-'+mode],cwd=ROOT,env=env,stdin=subprocess.PIPE,creationflags=0x08000000|4)
                child._books_suspended=True
                child_identity=None
                closure_verified=False
                try:
                    child_identity=owner_proof(child,node)
                    with OwnedProcessJob(child) as job:
                        child.communicate(json.dumps(proof).encode(),timeout=590)
                        class Accounting(ctypes.Structure):
                            _fields_=[('user',ctypes.c_longlong),('system',ctypes.c_longlong),('period_user',ctypes.c_longlong),('period_system',ctypes.c_longlong),('faults',wintypes.DWORD),('total',wintypes.DWORD),('active',wintypes.DWORD),('terminated',wintypes.DWORD)]
                        K.QueryInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p];K.QueryInformationJobObject.restype=wintypes.BOOL
                        accounting=Accounting()
                        # The console host (conhost.exe) of an exited CREATE_NO_WINDOW
                        # child is a Job member that exits a few ms after its client.
                        # Wait (bounded) for POSITIVE emptiness; a real survivor still fails.
                        settle=time.monotonic()+3
                        while True:
                            if not K.QueryInformationJobObject(job.handle,1,ctypes.byref(accounting),ctypes.sizeof(accounting),None):
                                raise RuntimeError('Cannot query native Job accounting: '+str(ctypes.WinError(ctypes.get_last_error())))
                            if not accounting.active or time.monotonic()>=settle:break
                            time.sleep(0.02)
                        if accounting.active:
                            raise RuntimeError('Build worker returned without a positively empty native Job')
                    # Native accounting was zero before closing the retained Job.
                    closure_verified=True
                    if child.returncode:raise RuntimeError('Owned worker failed: '+str(child.returncode))
                finally:
                    if child.poll() is None:
                        # This is the retained Popen HANDLE of our newly suspended
                        # child, never a PID lookup/foreign process tree.
                        child.terminate();child.wait(timeout=5)
                    tree.write(owned/'native-operation-result.json',[json.dumps({
                        'schema':'books-native-operation-result-v1','mode':mode,
                        'supervisor':identity,'worker':child_identity,
                        'root_exit_code':child.returncode,
                        'native_job_closed':closure_verified,
                        'active_processes_after':0 if closure_verified else None,
                        'completed_utc_seconds':time.time(),
                    },sort_keys=True).encode()])

if __name__=='__main__':
    try:main()
    except Exception as error:print('Native build guard: '+str(error),file=sys.stderr);sys.exit(1)
