"""One fixed Books proof. Executed only by its authenticated native loader."""
import ctypes as C, hashlib, json, os, subprocess, sys, threading, time
from pathlib import Path
if len(sys.argv)!=1 or not all(k in globals() for k in ('FIXED_POLICY','FIXED_POLICY_SHA','VERIFY_ONLY','K','handles','BOOTSTRAP_STARTED')):
    raise RuntimeError('Authenticated fixed loader required')
ROOT=Path(r'C:\Antigravity Projects\Studio Illuminati\WIP\Books Arranger\scratch\resume-2026-10-15\maintenance-worktree\scripts\qa\books-fixed-proof')
STUDIO=Path(r'C:\Antigravity Projects\Studio Illuminati')
SNAPSHOT=Path(r'C:\Antigravity Projects\Studio Illuminati\WIP\Books Arranger\scratch\resume-2026-10-15\proof-inputs-13')
CONTROL=Path(r'C:\Antigravity Projects\Studio Illuminati\WIP\Books Arranger\scratch\resume-2026-10-15\proof-control-13')
OUTPUT=Path(r'C:\Antigravity Projects\Studio Illuminati\WIP\Books Arranger\scratch\resume-2026-10-15\proof-run-13-01')
PYTHON=r'C:\Python314\python.exe'
NODE=r'C:\Program Files\nodejs\node.exe'
EXPECTED_ENV={'SystemRoot':r'C:\Windows','WINDIR':r'C:\Windows','ComSpec':r'C:\Windows\System32\cmd.exe','PATH':r'C:\Python314;C:\Windows\System32','PATHEXT':'.COM;.EXE;.BAT;.CMD','TEMP':str(OUTPUT/'tmp'),'TMP':str(OUTPUT/'tmp')}
def expired():
    os.write(2,b'Books fixed proof whole-invocation deadline; closure unproved\n')
    os._exit(124)
operation_deadline=BOOTSTRAP_STARTED+(6 if VERIFY_ONLY else 600)
timer=threading.Timer(max(0,operation_deadline-time.monotonic()),expired)
timer.daemon=True
timer.start()
def bootstrap_read(filename,maximum=4194304):
    p=Path(filename)
    for q in [*reversed(p.parents),p]:
        if os.stat(q,follow_symlinks=False).st_file_attributes&0x400:raise RuntimeError('Reparse bootstrap input')
        h=K.CreateFileW(str(q),0x81 if q!=p else 0x80000000,1,None,3,0x00200000|(0x02000000 if q!=p else 0),None)
        if h==C.c_void_p(-1).value:raise RuntimeError('Bootstrap lease unavailable')
        handles.append(h)
        b=C.create_unicode_buffer(32768);n=K.GetFinalPathNameByHandleW(h,b,len(b),0)
        if not 0<n<len(b) or os.path.normcase(b.value[4:].rstrip(chr(92)))!=os.path.normcase(str(q).rstrip(chr(92))):raise RuntimeError('Bootstrap canonical path mismatch')
    parts=[];total=0
    while True:
        b=C.create_string_buffer(65536);n=C.c_ulong()
        if not K.ReadFile(handles[-1],b,len(b),C.byref(n),None):raise RuntimeError('Bootstrap read failure')
        if not n.value:return b''.join(parts)
        total+=n.value
        if total>maximum:raise RuntimeError('Bootstrap input bound')
        parts.append(b.raw[:n.value])
policy_raw=bootstrap_read(FIXED_POLICY)
if hashlib.sha256(policy_raw).hexdigest()!=FIXED_POLICY_SHA:raise RuntimeError('Policy changed')
policy=json.loads(policy_raw)
def validate(p):
    expected_keys={'schema','entry','root','guard_cwd','cwd','control','output','executable','argv','environment','deadline_ms','pins','manifest','fallback','evaluator'}
    if set(p)!=expected_keys or p['schema']!=1 or p['entry']!='books-maintenance-13-fixed' or p['root']!=str(ROOT) or p['guard_cwd']!=str(STUDIO) or p['cwd']!=str(SNAPSHOT) or p['control']!=str(CONTROL) or p['output']!=str(OUTPUT) or p['executable']!=PYTHON or p['argv']!=['-I','-S','-B',str(ROOT/'proof-entry.py')] or p['environment']!=EXPECTED_ENV or p['deadline_ms']!=600000:raise RuntimeError('Unknown fixed Books contract')
    if len({r['path'].casefold() for r in p['pins']})!=len(p['pins']):raise RuntimeError('Duplicate immutable pin')
    for r in p['pins']:
        if set(r)!={'path','sha256'} or not Path(r['path']).is_absolute() or len(r['sha256'])!=64:raise RuntimeError('Malformed fixed pin')
    if p['manifest']['path']!=str(ROOT/'input-manifest.json'):raise RuntimeError('Unknown complete input map')
validate(policy)
if policy['evaluator']!={'path':r'C:\Antigravity Projects\Studio Monday\.claude\hooks\dispatch.mjs','sha256':'5246fe90e99948dc97eff6d7139c92eb35d596d9a314dbe576339e581eedbdaf'}:raise RuntimeError('Original evaluator identity changed')
owner=next(r for r in policy['pins'] if r['path']==str(ROOT/'windows-owner.py'))
owner_raw=bootstrap_read(owner['path'])
if hashlib.sha256(owner_raw).hexdigest()!=owner['sha256']:raise RuntimeError('Native owner changed')
FIXED_CHILD_ENV=dict(EXPECTED_ENV)
exec(compile(owner_raw,owner['path'],'exec'),globals())
def tree_names(root,kind='complete'):
    if kind=='node-bootstrap':return sorted(p.name for p in root.iterdir() if p.is_file() and (p.name=='node.exe' or p.suffix.lower()=='.dll'))
    if kind!='complete':raise RuntimeError('Unknown runtime tree kind')
    result=[]
    for directory,dirs,files in os.walk(root,followlinks=False):
        if time.monotonic()>=STARTED+600:raise TimeoutError('Complete inventory deadline')
        for name in dirs+files:
            p=Path(directory)/name;st=os.stat(p,follow_symlinks=False)
            if st.st_file_attributes&0x400:raise RuntimeError('Input tree reparse')
        result.extend((Path(directory)/name).relative_to(root).as_posix() for name in files)
    return sorted(result)
def main():
    if Path.cwd()!=STUDIO:raise RuntimeError('Actual fixed-loader cwd changed')
    with LockedFiles() as locks:
        locks.open(CONTROL,directory=True)
        lease=create_file(str(CONTROL/'operation.lock'),0xC0000000,0,None,4,0x00200000,None)
        if lease==INVALID:raise RuntimeError('Duplicate fixed operation')
        try:
            info=(W.DWORD*13)()
            require(api('GetFileInformationByHandle',W.BOOL,HANDLE,C.c_void_p)(lease,C.byref(info)),'Lease native facts')
            if info[0]&0x400 or info[10]!=1 or handle_read(lease,64) not in (b'',b'CLOSED'):raise RuntimeError('Unresolved or changed lease')
            for r in policy['pins']:locks.open(r['path'],r['sha256'])
            manifest=json.loads(locks.open(policy['manifest']['path'],policy['manifest']['sha256']))
            if manifest['schema']!='books-fixed-inputs-v1' or [r['root'].replace('/','\\') for r in manifest['trees']]!=[str(SNAPSHOT),r'C:\Python314',r'C:\Program Files\nodejs',r'C:\Antigravity Projects\Studio Monday\.claude\hooks']:raise RuntimeError('Wrong complete import/runtime roots')
            if not VERIFY_ONLY:
                for tree in manifest['trees']:
                    root=Path(tree['root']);locks.open(root,directory=True)
                    names=[r['path'] for r in tree['records']]
                    if tree.get('kind')=='node-bootstrap' and sorted(p.name for p in root.iterdir())!=tree['root_members']:raise RuntimeError('Node bootstrap directory membership changed')
                    if names!=tree_names(root,tree['kind']) or len(names)!=tree['count'] or len(names)!=len(set(names)):raise RuntimeError('Added/missing input or cache')
                    for r in tree['records']:
                        rel=r['path']
                        if not isinstance(rel,str) or not rel or '\\' in rel or ':' in rel or rel.startswith('/') or any(part in ('','.','..') for part in rel.split('/')):raise RuntimeError('Unsafe input map path')
                        if type(r['size']) is not int or not 0<=r['size']<=268435456 or not isinstance(r['sha256'],str) or len(r['sha256'])!=64 or any(c not in '0123456789abcdef' for c in r['sha256']):raise RuntimeError('Malformed input file record')
                        p=root/rel
                        raw=locks.open(p,r['sha256'],maximum=r['size'])
                        if len(raw)!=r['size']:raise RuntimeError('Input size changed')
            # Host envelope is exact-classified by the authenticated adapter.
            # Standalone verifier derives its fixed logical envelope; never blocks on stdin.
            logical=subprocess.list2cmdline([PYTHON,*policy['argv']])
            evaluator=policy['evaluator']
            envelope={'hook_event_name':'PreToolUse','tool_name':'Bash','cwd':str(STUDIO),'tool_input':{'command':logical,'timeout':600000}}
            lease_state(lease,b'RUNNING')
            for label,data in [('sentinel',{**envelope,'tool_input':{'command':'electron-builder --win --publish never'}}),('logical',envelope)]:
                result=owned_job(NODE,[evaluator['path']],STUDIO,CONTROL/(label+'-'+str(time.time_ns())),min(operation_deadline,time.monotonic()+1.5),lease,input_bytes=json.dumps(data).encode())
                if result['reason']!='completed' or result['root_exit']!=0 or result['active_after']!=0 or result.get('total_processes')!=1 or result.get('root_signaled') is not True or result.get('drains_closed') is not True or result.get('native_handles_closed') is not True:raise RuntimeError('Direct P9 evaluator sanity failed')
                decision=json.loads(result['stdout']) if result['stdout'].strip() else {}
                if not isinstance(decision,dict) or decision.get('systemMessage') or decision.get('decision')=='block' or 'self-test' in (result['stdout']+result['stderr']).lower() or 'untrusted' in (result['stdout']+result['stderr']).lower():raise RuntimeError('Direct P9 evaluator reports untrusted/self-test failure')
                denied=decision.get('hookSpecificOutput',{}).get('permissionDecision')=='deny'
                if label=='sentinel':
                    if not denied or '[P9:long-command-timeout]' not in decision.get('hookSpecificOutput',{}).get('permissionDecisionReason',''):raise RuntimeError('Fallback P9 denial unproved')
                elif denied:raise RuntimeError('Logical fixed proof denied')
            if VERIFY_ONLY:
                lease_state(lease,b'CLOSED')
                return {'verified':True,'source_verified':False,'deadline_ms':600000,'logical_command':logical,'guard_stdout':result['stdout'],'guard_stderr':result['stderr']},0
            mkdir=api('CreateDirectoryW',W.BOOL,W.LPCWSTR,C.c_void_p)
            locks.open(OUTPUT.parent,directory=True)
            require(mkdir(str(OUTPUT),None),'Fresh exclusive proof output')
            locks.open(OUTPUT,directory=True)
            require(mkdir(str(OUTPUT/'tmp'),None),'Fresh private TEMP')
            locks.open(OUTPUT/'tmp',directory=True)
            result=owned_job(PYTHON,policy['argv'],SNAPSHOT,OUTPUT/'child',STARTED+600,lease)
            # Reinventory after every child and all descendants are known closed.
            for tree in manifest['trees']:
                if tree.get('kind')=='node-bootstrap' and sorted(p.name for p in Path(tree['root']).iterdir())!=tree['root_members']:raise RuntimeError('Node bootstrap membership changed after child')
                if tree_names(Path(tree['root']),tree['kind'])!=[r['path'] for r in tree['records']]:raise RuntimeError('Input tree membership changed')
            ok=result['reason']=='completed' and result['root_exit']==0 and result['active_after']==0 and result.get('total_processes')==1 and result.get('root_signaled') is True and result.get('drains_closed') is True and result.get('native_handles_closed') is True
            result.update(ok=ok,entry=policy['entry'],source_manifest_sha256=policy['manifest']['sha256'],policy_sha256=FIXED_POLICY_SHA)
            lease_state(lease,b'CLOSED')
            return result,0 if ok else 1
        finally:close(lease)
try:
    result,status=main()
    print(json.dumps(result,ensure_ascii=True),flush=True)
    raise SystemExit(status)
finally:
    timer.cancel()
