$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$LASTEXITCODE = 2
try {
& 'C:\Python314\python.exe' -I -S -B -c 'import sys
try:
 sys.stdout.reconfigure(encoding=''utf-8'', errors=''strict'')
 sys.stderr.reconfigure(encoding=''utf-8'', errors=''backslashreplace'')
 import time
 BOOTSTRAP_STARTED=time.monotonic()
 """Isolated Windows fixed-contract candidate; not deployed."""
 import ctypes as C
 from ctypes import wintypes as W
 import hashlib
 import json
 import os
 from pathlib import Path
 import subprocess
 import sys
 import time
 
 PRODUCTION_DEADLINE_MS = 600000
 CONTRACT_ID = ''guard-safety-selftests''
 STARTED = globals().get(''BOOTSTRAP_STARTED'', time.monotonic())
 if os.name != ''nt'' or C.sizeof(C.c_void_p) != 8:
     raise RuntimeError(''Only reviewed Windows x64 is supported'')
 K = C.WinDLL(''kernel32'', use_last_error=True)
 HANDLE = W.HANDLE
 SIZE = C.c_size_t
 INVALID = C.c_void_p(-1).value
 
 class Security(C.Structure):
     _fields_ = [(''size'', W.DWORD), (''descriptor'', C.c_void_p), (''inherit'', W.BOOL)]
 class BasicLimit(C.Structure):
     _fields_ = [(''processTime'', C.c_longlong), (''jobTime'', C.c_longlong), (''flags'', W.DWORD), (''minWorking'', SIZE), (''maxWorking'', SIZE), (''activeLimit'', W.DWORD), (''affinity'', SIZE), (''priority'', W.DWORD), (''scheduling'', W.DWORD)]
 class Limits(C.Structure):
     _fields_ = [(''basic'', BasicLimit), (''io'', C.c_ulonglong * 6), (''processMemory'', SIZE), (''jobMemory'', SIZE), (''peakProcess'', SIZE), (''peakJob'', SIZE)]
 class Accounting(C.Structure):
     _fields_ = [(''times'', C.c_longlong * 4), (''faults'', W.DWORD), (''total'', W.DWORD), (''active'', W.DWORD), (''terminated'', W.DWORD)]
 class Startup(C.Structure):
     _fields_ = [(''cb'', W.DWORD), (''reserved'', W.LPWSTR), (''desktop'', W.LPWSTR), (''title'', W.LPWSTR), (''x'', W.DWORD), (''y'', W.DWORD), (''width'', W.DWORD), (''height'', W.DWORD), (''xchars'', W.DWORD), (''ychars'', W.DWORD), (''fill'', W.DWORD), (''flags'', W.DWORD), (''show'', W.WORD), (''reservedSize'', W.WORD), (''reservedBytes'', C.c_void_p), (''stdin'', HANDLE), (''stdout'', HANDLE), (''stderr'', HANDLE)]
 class StartupEx(C.Structure):
     _fields_ = [(''startup'', Startup), (''attributes'', C.c_void_p)]
 class ProcessInfo(C.Structure):
     _fields_ = [(''process'', HANDLE), (''thread'', HANDLE), (''pid'', W.DWORD), (''tid'', W.DWORD)]
 
 def api(name, result, *args):
     function = getattr(K, name)
     function.restype, function.argtypes = result, list(args)
     return function
 
 close = api(''CloseHandle'', W.BOOL, HANDLE)
 create_file = api(''CreateFileW'', HANDLE, W.LPCWSTR, W.DWORD, W.DWORD, C.c_void_p, W.DWORD, W.DWORD, HANDLE)
 read_file = api(''ReadFile'', W.BOOL, HANDLE, C.c_void_p, W.DWORD, C.POINTER(W.DWORD), C.c_void_p)
 final_path = api(''GetFinalPathNameByHandleW'', W.DWORD, HANDLE, W.LPWSTR, W.DWORD, W.DWORD)
 create_job = api(''CreateJobObjectW'', HANDLE, C.c_void_p, W.LPCWSTR)
 set_job = api(''SetInformationJobObject'', W.BOOL, HANDLE, C.c_int, C.c_void_p, W.DWORD)
 query_job = api(''QueryInformationJobObject'', W.BOOL, HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p)
 assign_job = api(''AssignProcessToJobObject'', W.BOOL, HANDLE, HANDLE)
 terminate_job = api(''TerminateJobObject'', W.BOOL, HANDLE, W.UINT)
 terminate_process = api(''TerminateProcess'', W.BOOL, HANDLE, W.UINT)
 resume_thread = api(''ResumeThread'', W.DWORD, HANDLE)
 wait_process = api(''WaitForSingleObject'', W.DWORD, HANDLE, W.DWORD)
 exit_code = api(''GetExitCodeProcess'', W.BOOL, HANDLE, C.POINTER(W.DWORD))
 init_attributes = api(''InitializeProcThreadAttributeList'', W.BOOL, C.c_void_p, W.DWORD, W.DWORD, C.POINTER(SIZE))
 update_attributes = api(''UpdateProcThreadAttribute'', W.BOOL, C.c_void_p, W.DWORD, SIZE, C.c_void_p, SIZE, C.c_void_p, C.c_void_p)
 delete_attributes = api(''DeleteProcThreadAttributeList'', None, C.c_void_p)
 create_process = api(''CreateProcessW'', W.BOOL, W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD, C.c_void_p, W.LPCWSTR, C.c_void_p, C.POINTER(ProcessInfo))
 write_file = api(''WriteFile'', W.BOOL, HANDLE, C.c_void_p, W.DWORD, C.POINTER(W.DWORD), C.c_void_p)
 seek_file = api(''SetFilePointerEx'', W.BOOL, HANDLE, C.c_longlong, C.c_void_p, W.DWORD)
 truncate_file = api(''SetEndOfFile'', W.BOOL, HANDLE)
 
 def handle_write(handle, raw):
     wrote = W.DWORD()
     require(write_file(handle, raw, len(raw), C.byref(wrote), None) and wrote.value == len(raw), ''Write exact owned bytes'')
 
 def handle_read(handle, maximum=1048576):
     require(seek_file(handle, 0, None, 0), ''Rewind held output'')
     chunks = []
     total = 0
     while True:
         buffer, count = C.create_string_buffer(65536), W.DWORD()
         require(read_file(handle, buffer, len(buffer), C.byref(count), None), ''Read held output'')
         if not count.value: return b''''.join(chunks)
         total += count.value
         if total > maximum: raise ValueError(''Owned output exceeds reviewed bound'')
         chunks.append(buffer.raw[:count.value])
 
 def lease_state(handle, state):
     require(seek_file(handle, 0, None, 0), ''Rewind lease state'')
     handle_write(handle, state)
     require(truncate_file(handle), ''Truncate exact lease state'')
     require(api(''FlushFileBuffers'', W.BOOL, HANDLE)(handle), ''Persist fail-closed state'')
 
 def require(ok, operation):
     if not ok:
         raise OSError(C.get_last_error(), operation)
 
 class LockedFiles:
     def __init__(self):
         self.handles = []
 
     def open(self, filename, expected=None, directory=False):
         filename = str(filename)
         if not Path(filename).is_absolute() or any(x in filename for x in (''\0'', ''\r'', ''\n'')):
             raise ValueError(''Invalid absolute path'')
         # Hold every ancestor against replacement; reject reparse points.
         for parent in reversed(Path(filename).parents):
             self._open(str(parent), directory=True)
         handle = self._open(filename, directory=directory)
         if directory:
             return handle
         chunks = []
         while True:
             buffer, size = C.create_string_buffer(65536), W.DWORD()
             require(read_file(handle, buffer, len(buffer), C.byref(size), None), ''Read locked source'')
             if not size.value:
                 break
             chunks.append(buffer.raw[:size.value])
         raw = b''''.join(chunks)
         if expected is not None and hashlib.sha256(raw).hexdigest() != expected:
             raise ValueError(''Pinned file hash mismatch: '' + filename)
         return raw
 
     def _open(self, filename, directory):
         if os.stat(filename, follow_symlinks=False).st_file_attributes & 0x400:
             raise ValueError(''Reparse path refused: '' + filename)
         handle = create_file(filename, 0 if directory else 0x80000000, 1, None, 3, 0x02000000 if directory else 0, None)
         if handle == INVALID:
             raise OSError(C.get_last_error(), ''Open share-read-only: '' + filename)
         self.handles.append(handle)
         buffer = C.create_unicode_buffer(32768)
         n = final_path(handle, buffer, len(buffer), 0)
         require(0 < n < len(buffer), ''Final handle identity'')
         actual = buffer.value.removeprefix(''\\?\\'')
         # Device prefix is exactly \\?\, not an arbitrary alias.
         if buffer.value.startswith(''\\\\?\\''):
             actual = buffer.value[4:]
         if os.path.normcase(actual.rstrip(''\\'')) != os.path.normcase(filename.rstrip(''\\'')):
             raise ValueError(''Canonical handle path differs: '' + filename)
         return handle
 
     def __enter__(self):
         return self
 
     def __exit__(self, *unused):
         for handle in reversed(self.handles):
             close(handle)
 
 def active(job):
     accounting = Accounting()
     require(query_job(job, 1, C.byref(accounting), C.sizeof(accounting), None), ''Query owned job'')
     return accounting.active
 
 def owned_job(executable, arguments, cwd, logs, deadline, lease, *, _assignment_supported=True, input_bytes=None):
     """Atomic Job + bounded anonymous pipes; one deadline includes final drains."""
     import threading
     job=create_job(None,None);require(job,''Create private job'')
     process=ProcessInfo();attributes=None;child_handles=[];read_handles=[];log_handles=[];threads=[]
     locks=LockedFiles();state={''bytes'':0,''overflow'':False,''error'':None};mutex=threading.Lock();captured=[[],[]];reason=None
     pipe=api(''CreatePipe'',W.BOOL,C.POINTER(HANDLE),C.POINTER(HANDLE),C.c_void_p,W.DWORD)
     set_handle=api(''SetHandleInformation'',W.BOOL,HANDLE,W.DWORD,W.DWORD)
     cap=16*1024*1024
     try:
         limits=Limits();limits.basic.flags=0x2000
         require(set_job(job,9,C.byref(limits),C.sizeof(limits)),''Set kill-on-close'')
         logs=Path(logs);logs.mkdir();locks.open(logs,directory=True)
         security=Security(C.sizeof(Security),None,True)
         stdin_name=''NUL'' if input_bytes is None else str(logs/''stdin.json'')
         stdin=create_file(stdin_name,0x80000000 if input_bytes is None else 0xC0000000,1,C.byref(security),3 if input_bytes is None else 1,0,None)
         if stdin==INVALID:raise OSError(C.get_last_error(),''Owned stdin'')
         child_handles.append(stdin)
         if input_bytes is not None:handle_write(stdin,input_bytes);require(seek_file(stdin,0,None,0),''Rewind input'')
         for name in [''stdout.log'',''stderr.log'']:
             read,write=HANDLE(),HANDLE()
             require(pipe(C.byref(read),C.byref(write),C.byref(security),4096),''Owned anonymous pipe'')
             require(set_handle(read,1,0),''Parent reader not inherited'')
             read_handles.append(read.value);child_handles.append(write.value)
             log=create_file(str(logs/name),0x40000000,1,None,1,0,None)
             if log==INVALID:raise OSError(C.get_last_error(),''Bounded evidence output'')
             log_handles.append(log)
         size=SIZE();init_attributes(None,2,0,C.byref(size));attributes=C.create_string_buffer(size.value)
         require(init_attributes(attributes,2,0,C.byref(size)),''Initialize attributes'')
         inherit=(HANDLE*3)(*child_handles)
         require(update_attributes(attributes,0,0x20002,inherit,C.sizeof(inherit),None,None),''Only stdio inherited'')
         if not _assignment_supported:raise OSError(''Atomic Job assignment unavailable'')
         job_list=(HANDLE*1)(job)
         require(update_attributes(attributes,0,0x2000D,job_list,C.sizeof(job_list),None,None),''Atomic Job list required'')
         startup=StartupEx();startup.startup.cb=C.sizeof(startup);startup.startup.flags=0x101
         startup.startup.stdin,startup.startup.stdout,startup.startup.stderr=child_handles
         startup.attributes=C.cast(attributes,C.c_void_p)
         scratch=str(logs.parent)
         environment={''SystemRoot'':r''C:\Windows'',''WINDIR'':r''C:\Windows'',''ComSpec'':r''C:\Windows\System32\cmd.exe'',''PATHEXT'':''.COM;.EXE;.BAT;.CMD'',
             ''PATH'':r''C:\Program Files\nodejs;C:\Windows\System32'',''TEMP'':scratch,''TMP'':scratch,''USERPROFILE'':scratch,''HOME'':scratch,''npm_config_cache'':str(Path(scratch)/''npm-cache'')}
         block=C.create_unicode_buffer(''\0''.join(k+''=''+v for k,v in sorted(environment.items(),key=lambda x:x[0].upper()))+''\0\0'')
         if time.monotonic()>=deadline-5:raise TimeoutError(''Setup consumed total budget'')
         command=C.create_unicode_buffer(subprocess.list2cmdline([str(executable),*arguments]))
         require(create_process(str(executable),command,None,None,True,0x08000000|0x4|0x400|0x80000,block,str(cwd),C.byref(startup),C.byref(process)),''Create hidden suspended owned child'')
         def drain(index):
             try:
                 while True:
                     buffer,count=C.create_string_buffer(65536),W.DWORD()
                     if not read_file(read_handles[index],buffer,len(buffer),C.byref(count),None):
                         if C.get_last_error()==109:return
                         raise OSError(C.get_last_error(),''Owned pipe drain'')
                     if not count.value:return
                     with mutex:
                         remaining=cap-state[''bytes''];accepted=min(count.value,max(0,remaining));state[''bytes'']+=accepted
                         if accepted:
                             chunk=buffer.raw[:accepted];captured[index].append(chunk);handle_write(log_handles[index],chunk)
                         if count.value>accepted:
                             state[''overflow'']=True
                             require(terminate_job(job,124),''Output cap closes owned producer'')
                             return
             except BaseException as error:
                 state[''error'']=str(error)
                 terminate_job(job,125)
         for index in range(2):
             thread=threading.Thread(target=drain,args=(index,),daemon=True);threads.append(thread);thread.start()
         if time.monotonic()>=deadline-5:raise TimeoutError(''Deadline before resume'')
         require(resume_thread(process.thread)!=0xFFFFFFFF,''Resume already assigned child'')
         # Parent closes writers immediately. Only owned descendants can keep a
         # pipe open; abrupt parent death closes the noninherited Job handle.
         for index in [1,2]:close(child_handles[index]);child_handles[index]=None
         identity=create_file(str(logs/''identity.json''),0x40000000,1,None,1,0,None)
         if identity==INVALID:raise OSError(C.get_last_error(),''Owned identity'')
         try:handle_write(identity,json.dumps({''runner_pid'':os.getpid(),''root_pid'':process.pid}).encode())
         finally:close(identity)
         while active(job):
             if time.monotonic()>=deadline-5:
                 reason=''deadline'';require(terminate_job(job,124),''Deadline closes owned tree'');break
             time.sleep(0.01)
         closure_end=min(deadline,time.monotonic()+5)
         while active(job) and time.monotonic()<closure_end:time.sleep(0.01)
         if active(job):raise RuntimeError(''Descendant closure unknown'')
         for thread in threads:thread.join(max(0,deadline-time.monotonic()))
         if any(thread.is_alive() for thread in threads):raise RuntimeError(''Stream closure unknown'')
         if state[''error'']:raise RuntimeError(''Drain failed: ''+state[''error''])
         if time.monotonic()>deadline:raise TimeoutError(''Postcondition exceeded total budget'')
         require(wait_process(process.process,max(0,int((deadline-time.monotonic())*1000)))==0,''Root terminated'')
         code=W.DWORD();require(exit_code(process.process,C.byref(code)),''Root exit identity'')
         if code.value==259:raise RuntimeError(''Root still active'')
         return {''reason'':''output-limit'' if state[''overflow''] else reason or ''completed'',''root_pid'':process.pid,''root_exit'':code.value,''active_after'':0,
             ''elapsed_ms'':round((time.monotonic()-STARTED)*1000),''production_deadline_ms'':600000,''output_bytes'':state[''bytes''],
             ''stdout'':b''''.join(captured[0]).decode(''utf-8'',errors=''replace''),''stderr'':b''''.join(captured[1]).decode(''utf-8'',errors=''replace'')}
     finally:
         if process.process:terminate_process(process.process,125)
         require(terminate_job(job,125),''Fail-closed termination'')
         while active(job) and time.monotonic()<deadline:time.sleep(0.01)
         known=active(job)==0
         for handle in child_handles:
             if handle:close(handle)
         for thread in threads:thread.join(max(0,deadline-time.monotonic()))
         if any(thread.is_alive() for thread in threads):known=False
         for handle in read_handles+log_handles:close(handle)
         close(job)
         if process.thread:close(process.thread)
         if process.process:close(process.process)
         if attributes is not None:delete_attributes(attributes)
         locks.__exit__()
         if not known:raise RuntimeError(''Owned tree/drain closure unproved'')
 
 import sys,json
 from pathlib import Path
 root=Path("C:\\Users\\AnGeLZzZ\\.codex\\hooks\\command-safety-route\\runtime-repair-20261013\\logs")
 root.mkdir(parents=True,exist_ok=True)
 raw=sys.stdin.buffer.read(1048577) if True else None
 if raw is not None and len(raw)>1048576:raise RuntimeError(''Oversized hook input'')
 result=owned_job("C:\\Python314\\python.exe",[''-I'',''-S'',''-B'',''-c'',"import ctypes as C,hashlib,json,os,pathlib,subprocess,sys\nK=C.WinDLL(''kernel32'',use_last_error=True)\nK.CreateFileW.argtypes=[C.c_wchar_p,C.c_ulong,C.c_ulong,C.c_void_p,C.c_ulong,C.c_ulong,C.c_void_p];K.CreateFileW.restype=C.c_void_p\nK.GetFinalPathNameByHandleW.argtypes=[C.c_void_p,C.c_wchar_p,C.c_ulong,C.c_ulong];K.GetFinalPathNameByHandleW.restype=C.c_ulong\nK.ReadFile.argtypes=[C.c_void_p,C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.c_void_p];K.CloseHandle.argtypes=[C.c_void_p]\nK.GetFileInformationByHandle.argtypes=[C.c_void_p,C.c_void_p];K.GetFileInformationByHandle.restype=C.c_int\nhandles=[]\nraw=sys.stdin.buffer.read(1048577)\nif len(raw)>1048576:raise RuntimeError(''Oversized hook input'')\ntry:command=json.loads(raw).get(''tool_input'',{}).get(''command'')\nexcept (ValueError,TypeError,AttributeError):command=None\nbooks=isinstance(command,str) and command.startswith(\"& ''C:\\\\Python314\\\\python.exe'' -I -S -B -c ''# Books fixed maintenance-13\\n\")\nold_records=[[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\scripts\\\\qa\\\\quicklaunch-dependency-route\\\\python-bootstrap-pins.json\",\"2413c208eb7d0e8085025e6bce250c26d8878f38389ca1196158445a8863155d\"],[\"C:\\\\Program Files\\\\nodejs\\\\node.exe\",\"a619e2e09eb0d50ef4c733d678b4d22689d2afef138cd67fd3fa107b535f8819\"],[\"C:\\\\Users\\\\AnGeLZzZ\\\\.codex\\\\hooks\\\\command-safety-route\\\\runtime-repair-20261013\\\\hook.mjs\",\"34edde5437cabc1d2600d1f415d5ec126f77dbe7d234a4fdb0e942877d02cb03\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\scripts\\\\qa\\\\quicklaunch-dependency-route\\\\contract.mjs\",\"ed77c944edcedfc2ae5663178c4e23019fd11fcb8bad0f60b78c6b4b6353b5b1\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\scripts\\\\qa\\\\quicklaunch-dependency-route\\\\hook.mjs\",\"5836fbcde7ec01fc31d174d659dc2acfb80337e874a5e3a1be4ae31731debf81\"],[\"C:\\\\Users\\\\AnGeLZzZ\\\\.codex\\\\hooks\\\\command-safety-route\\\\runtime-repair-20261013\\\\timeout-compatibility-hook.mjs\",\"1207c0bb0837d111e8b62642b1d13595a6e4d36333f07688fd3365685cb63184\"],[\"C:\\\\Users\\\\AnGeLZzZ\\\\.codex\\\\hooks\\\\command-safety-route\\\\runtime-repair-20261013\\\\observation-policy.capture-v1.json\",\"a612ab9002c463376a01550fd407f0f94344d40be41b6e6292a9be0a890a6f92\"],[\"C:\\\\Users\\\\AnGeLZzZ\\\\.codex\\\\hooks\\\\command-safety-route\\\\timeout-v1\\\\timeout-compatibility-hook.mjs\",\"eeddc99ee66975f2a287da371ab39b063b6af6f3236d47ce01b9e33ebd2c0f76\"],[\"C:\\\\Users\\\\AnGeLZzZ\\\\.codex\\\\hooks\\\\command-safety-route\\\\observer.mjs\",\"4eab19e937a28166f8af4e019b325f1118be7e3d644c1914d72351b541b2a171\"],[\"C:\\\\Users\\\\AnGeLZzZ\\\\.codex\\\\hooks\\\\command-safety-route\\\\observation-policy.capture-v1.json\",\"4b0101b90e67b741bc9011044520b87a8cd143780f9d35b52cac8d74855a0ec3\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\scripts\\\\qa\\\\quicklaunch-dependency-route\\\\policy.json\",\"2867c5dbfeb53b81213c74fc497be5280d0cf96af00772f761e401c890e2ed48\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\scripts\\\\qa\\\\quicklaunch-dependency-route\\\\frozen.json\",\"0598caa4452dd6af828da5ca38b70fa6c152d61a4f8dff750df688e8b2500d47\"],[\"C:\\\\Users\\\\AnGeLZzZ\\\\.codex\\\\hooks\\\\command-safety-route\\\\timeout-v1\\\\fixed-bootstrap-candidate.json\",\"fb695a60c92b8933521fa810ef870e11e5e0dc4dbaf1f85e5ec54220da64e222\"]]\nbooks_records=[[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\scripts\\\\qa\\\\quicklaunch-dependency-route\\\\python-bootstrap-pins.json\",\"2413c208eb7d0e8085025e6bce250c26d8878f38389ca1196158445a8863155d\"],[\"C:\\\\Program Files\\\\nodejs\\\\node.exe\",\"a619e2e09eb0d50ef4c733d678b4d22689d2afef138cd67fd3fa107b535f8819\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\WIP\\\\Books Arranger\\\\scratch\\\\resume-2026-10-15\\\\maintenance-worktree\\\\scripts\\\\qa\\\\books-fixed-proof\\\\runner.py\",\"a62a9ed2ee5a5098c82af36dfcc62e352a55427b8b37fc201b8c48f892070d5c\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\WIP\\\\Books Arranger\\\\scratch\\\\resume-2026-10-15\\\\maintenance-worktree\\\\scripts\\\\qa\\\\books-fixed-proof\\\\windows-owner.py\",\"525c9df2b22c732065cf1cd79cca7def1388885e99d58c4b0770cc5c09236bdd\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\WIP\\\\Books Arranger\\\\scratch\\\\resume-2026-10-15\\\\maintenance-worktree\\\\scripts\\\\qa\\\\books-fixed-proof\\\\proof-entry.py\",\"53fc9ef90d274d2c7f14eb4ff61be89bbe50b189ec59a72a66c2a1fde2597ce8\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\WIP\\\\Books Arranger\\\\scratch\\\\resume-2026-10-15\\\\maintenance-worktree\\\\scripts\\\\qa\\\\books-fixed-proof\\\\contract.mjs\",\"af7fa9c8d17bca1e4caaf7fb9b05d510a7a41082af1da523d1e24c82d297c1a0\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\WIP\\\\Books Arranger\\\\scratch\\\\resume-2026-10-15\\\\maintenance-worktree\\\\scripts\\\\qa\\\\books-fixed-proof\\\\hook-adapter.mjs\",\"1b6918ba86a2ea83285af55d91e39fb237ecc375450250c8ebbdf71ff94d0f4f\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\WIP\\\\Books Arranger\\\\scratch\\\\resume-2026-10-15\\\\maintenance-worktree\\\\scripts\\\\qa\\\\books-fixed-proof\\\\policy.json\",\"d7c1b8d4fd0e222b7769df357372529174675b5f1d57a435233339f18346f792\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\WIP\\\\Books Arranger\\\\scratch\\\\resume-2026-10-15\\\\maintenance-worktree\\\\scripts\\\\qa\\\\books-fixed-proof\\\\frozen.json\",\"a25faaa2929aaeaf987135cac6721064f7b8711a4e83f515c7532bc4a94b3b86\"],[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\WIP\\\\Books Arranger\\\\scratch\\\\resume-2026-10-15\\\\maintenance-worktree\\\\scripts\\\\qa\\\\books-fixed-proof\\\\input-manifest.json\",\"0d8039294b5e3fd07fba733f3eab6188b8b175eb315e55d5b38381132a5fafba\"]]\nrecords=(books_records if books else old_records)+[[\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\WIP\\\\Books Arranger\\\\scratch\\\\resume-2026-10-15\\\\maintenance-worktree\\\\scripts\\\\qa\\\\books-fixed-proof\\\\registration-proposal\\\\route.mjs\",\"ca10d28df11947cf3560adcb57623ec2570feed10dd259fb1e3b606e0b4e697b\"]]\ntry:\n for filename,expected in records:\n  p=pathlib.Path(filename)\n  for q in [*reversed(p.parents),p]:\n   if os.stat(q,follow_symlinks=False).st_file_attributes&0x400:raise RuntimeError(''Reparse checker refused'')\n   h=K.CreateFileW(str(q),(0x81 if books else 0) if q!=p else 0x80000000,1,None,3,(0x00200000 if books else 0)|(0x02000000 if q!=p else 0),None)\n   if h==C.c_void_p(-1).value:raise RuntimeError(''Checker unavailable'')\n   handles.append(h);b=C.create_unicode_buffer(32768);n=K.GetFinalPathNameByHandleW(h,b,len(b),0)\n   if not 0<n<len(b) or os.path.normcase(b.value[4:].rstrip(chr(92)))!=os.path.normcase(str(q).rstrip(chr(92))):raise RuntimeError(''Checker canonical identity refused'')\n   if books:\n    info=(C.c_ulong*13)()\n    if not K.GetFileInformationByHandle(h,C.byref(info)) or info[0]&0x400 or bool(info[0]&0x10)!=(q!=p) or (q==p and info[10]!=1):raise RuntimeError(''Books native kind/link fact refused'')\n  digest=hashlib.sha256();parts=[]\n  while True:\n   b=C.create_string_buffer(65536);n=C.c_ulong()\n   if not K.ReadFile(handles[-1],b,len(b),C.byref(n),None):raise RuntimeError(''Checker read failed'')\n   if not n.value:break\n   digest.update(b.raw[:n.value])\n   if filename==\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\scripts\\\\qa\\\\quicklaunch-dependency-route\\\\python-bootstrap-pins.json\":parts.append(b.raw[:n.value])\n  if digest.hexdigest()!=expected:raise RuntimeError(''Checker byte tamper'')\n  if filename==\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\scripts\\\\qa\\\\quicklaunch-dependency-route\\\\python-bootstrap-pins.json\":records.extend((x[''path''],x[''sha256'']) for x in json.loads(b''''.join(parts)))\n sys.exit(subprocess.run([\"C:\\\\Program Files\\\\nodejs\\\\node.exe\",\"C:\\\\Antigravity Projects\\\\Studio Illuminati\\\\WIP\\\\Books Arranger\\\\scratch\\\\resume-2026-10-15\\\\maintenance-worktree\\\\scripts\\\\qa\\\\books-fixed-proof\\\\registration-proposal\\\\route.mjs\"],input=raw,cwd=\"C:\\\\Antigravity Projects\\\\Studio Illuminati\").returncode)\nfinally:\n for h in reversed(handles):K.CloseHandle(h)\n"],"C:\\Antigravity Projects\\Studio Illuminati",root/(''outer-hook-''+str(time.time_ns())),BOOTSTRAP_STARTED+8,None,input_bytes=raw)
 if True:
  if result[''reason'']!=''completed'' or result[''active_after'']!=0:raise RuntimeError(''Hook worker ownership failed'')
  reason = ''''
  recognized_denial = False
  try:
   denial = json.loads(result[''stdout''])
   if isinstance(denial, dict) and set(denial) == {''hookSpecificOutput''}:
    specific = denial[''hookSpecificOutput'']
    if isinstance(specific, dict) and set(specific) == {''hookEventName'', ''permissionDecision'', ''permissionDecisionReason''} and specific[''hookEventName''] == ''PreToolUse'' and specific[''permissionDecision''] == ''deny'':
     recognized_denial = True
     reason = specific[''permissionDecisionReason'']
   elif isinstance(denial, dict) and set(denial) == {''decision'', ''reason''} and denial[''decision''] == ''block'':
    recognized_denial = True
    reason = denial[''reason'']
  except (ValueError, TypeError, AttributeError):
   pass
  if not isinstance(reason, str):
   reason = ''''
  if recognized_denial or result[''root_exit''] != 0:
   raise RuntimeError(reason.strip() or (''Guard worker denied'' if recognized_denial else result[''stderr''].strip() or (''Guard worker refused with exit '' + str(result[''root_exit'']))))
  sys.stdout.write(result[''stdout'']);sys.stderr.write(result[''stderr'']);sys.exit(0)
 else:
  print(json.dumps({k:result[k] for k in [''reason'',''root_exit'',''active_after'',''output_bytes'',''elapsed_ms'']}))
  sys.exit(0 if result[''reason'']==''completed'' and result[''root_exit'']==0 and result[''active_after'']==0 else 2)
 
except Exception as error:
 sys.stderr.write(''[studio-command-safety] '' + str(error)[:4096] + ''\n'')
 sys.exit(2)
'
$nativeExit = $LASTEXITCODE
if ($nativeExit -eq 0) { exit 0 }
[Console]::Error.WriteLine('[studio-command-safety-shell] Native checker exited ' + [string]$nativeExit)
exit 2
} catch {
$failure = [string]$_.Exception.Message
if ($failure.Length -gt 1024) { $failure = $failure.Substring(0,1024) }
[Console]::Error.WriteLine('[studio-command-safety-shell] ' + $failure)
exit 2
}
