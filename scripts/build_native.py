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

PYTHON_SHA256 = '434b361fe0c5960d404974feed493db47f2603a1ace2574312104fbed0182c6f'
ROOT = Path(__file__).absolute().parent.parent
# Bootstrap native API is self-contained; no checkout modules run until leased.
K = ctypes.WinDLL('kernel32', use_last_error=True) if os.name == 'nt' else None
class Info(ctypes.Structure):
    _fields_ = [('attributes',wintypes.DWORD),('creation',wintypes.FILETIME),('access',wintypes.FILETIME),('write',wintypes.FILETIME),('volume',wintypes.DWORD),('size_high',wintypes.DWORD),('size_low',wintypes.DWORD),('links',wintypes.DWORD),('index_high',wintypes.DWORD),('index_low',wintypes.DWORD)]

def bootstrap(stack):
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
