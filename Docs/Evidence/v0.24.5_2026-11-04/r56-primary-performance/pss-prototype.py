import ctypes, json, pathlib, subprocess, sys, time
from ctypes import wintypes
root=pathlib.Path(r"C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger")
sys.path[:0]=[str(root)]
import native_io
class Entry(ctypes.Structure):
 _fields_=[('exit',wintypes.DWORD),('teb',ctypes.c_void_p),('process',wintypes.DWORD),('thread',wintypes.DWORD),('affinity',ctypes.c_size_t),('priority',ctypes.c_int),('base',ctypes.c_int),('arg',ctypes.c_void_p),('syscall',wintypes.WORD),('created',wintypes.FILETIME),('exited',wintypes.FILETIME),('kernel',wintypes.FILETIME),('user',wintypes.FILETIME),('start',ctypes.c_void_p),('captured',wintypes.FILETIME),('flags',wintypes.DWORD),('suspend',wintypes.WORD),('context_size',wintypes.WORD),('context',ctypes.c_void_p)]
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.PssCaptureSnapshot.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)];k.PssCaptureSnapshot.restype=wintypes.DWORD
k.PssWalkMarkerCreate.argtypes=[ctypes.c_void_p,ctypes.POINTER(wintypes.HANDLE)];k.PssWalkMarkerCreate.restype=wintypes.DWORD
k.PssWalkSnapshot.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD];k.PssWalkSnapshot.restype=wintypes.DWORD
k.PssWalkMarkerFree.argtypes=[wintypes.HANDLE];k.PssWalkMarkerFree.restype=wintypes.DWORD
k.PssFreeSnapshot.argtypes=[wintypes.HANDLE,wintypes.HANDLE];k.PssFreeSnapshot.restype=wintypes.DWORD
k.GetCurrentProcess.argtypes=[];k.GetCurrentProcess.restype=wintypes.HANDLE
results=[]
for index in range(5):
 p=subprocess.Popen([sys.executable,'-I','-B','-c','pass'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000|4)
 p._books_suspended=False
 try:
  with native_io.OwnedProcessJob(p):
   snapshot=wintypes.HANDLE();marker=wintypes.HANDLE();rows=[];started=time.perf_counter()
   status=k.PssCaptureSnapshot(int(p._handle),0x80,0,ctypes.byref(snapshot))
   if status:raise RuntimeError(('capture',status))
   try:
    status=k.PssWalkMarkerCreate(None,ctypes.byref(marker))
    if status:raise RuntimeError(('marker',status))
    try:
     entry=Entry()
     while True:
      status=k.PssWalkSnapshot(snapshot,3,marker,ctypes.byref(entry),ctypes.sizeof(entry))
      if status==259:break
      if status:raise RuntimeError(('walk',status))
      rows.append({'process':entry.process,'thread':entry.thread,'suspend_count':entry.suspend,'flags':entry.flags})
    finally:
     status=k.PssWalkMarkerFree(marker)
     if status:raise RuntimeError(('marker free',status))
   finally:
    status=k.PssFreeSnapshot(k.GetCurrentProcess(),snapshot)
    if status:raise RuntimeError(('snapshot free',status))
   captured=time.perf_counter()-started
   started=time.perf_counter();native_io.resume_owned_primary(p.pid);old=time.perf_counter()-started
   p.communicate(timeout=5)
   results.append({'pid':p.pid,'capture_seconds':captured,'global_resume_seconds':old,'threads':rows,'exit':p.returncode})
 finally:
  if p.poll() is None:p.kill();p.wait()
  p.stdout.close();p.stderr.close()
print(json.dumps({'entry_size':ctypes.sizeof(Entry),'measurements':results},indent=2))
