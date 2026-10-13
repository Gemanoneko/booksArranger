"""Native owner for exactly one desktop engine; no numeric-PID cancellation.

The Electron shell owns this host through a private stdin pipe. The engine is
created suspended, assigned to a kill-on-close native job and retained by its
process HANDLE before it can execute. Normal Quit travels through the authenticated
engine API. Shell loss closes the engine's stdin for checkpoint shutdown. A worker timeout
retains this host, native job and catalog ownership; it is never a kill deadline.
"""
import ctypes,json,os,subprocess,sys,threading,time
from ctypes import wintypes
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_io import OwnedProcessJob

def owner_proof(process,expected_image=None):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
    kernel.GetProcessTimes.restype=wintypes.BOOL
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype=wintypes.BOOL
    times=[wintypes.FILETIME() for _ in range(4)];handle=wintypes.HANDLE(int(process._handle))
    kernel.GetProcessId.argtypes=[wintypes.HANDLE];kernel.GetProcessId.restype=wintypes.DWORD
    if kernel.GetProcessId(handle)!=process.pid:raise RuntimeError('Owned process PID differs from retained native handle')
    if not kernel.GetProcessTimes(handle,*[ctypes.byref(t) for t in times]):raise RuntimeError('Cannot prove owned engine generation')
    image=ctypes.create_unicode_buffer(32768);length=wintypes.DWORD(len(image))
    if not kernel.QueryFullProcessImageNameW(handle,0,image,ctypes.byref(length)):raise RuntimeError('Cannot prove owned engine runtime')
    if Path(image.value).resolve()!=Path(expected_image or sys.executable).resolve():raise RuntimeError('Owned process runtime differs')
    return {'type':'books-native-owner-v1','host_pid':os.getpid(),'pid':process.pid,
            'creation_filetime':str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime),'image':image.value}

def pump(source,target):
    try:
        while True:
            block=os.read(source.fileno(),16384)
            if not block:return
            target.buffer.write(block);target.buffer.flush()
    except (OSError,BrokenPipeError):pass

def shell_pipe(process,lost):
    # A close is evidence about our inherited pipe, not HTTP availability or PID.
    try:
        while os.read(sys.stdin.fileno(),4096):pass
    except OSError:pass
    lost.set()
    try:process.stdin.close()
    except (OSError,ValueError):pass

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if os.name!='nt':raise RuntimeError('Desktop process ownership requires Windows')
    backend=Path(__file__).resolve().with_name('desktop_backend.py')
    if not backend.is_file():raise RuntimeError('Desktop backend is missing')
    process=subprocess.Popen([sys.executable,'-I','-B',str(backend),*argv],cwd=backend.parent,
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        creationflags=0x00000004|subprocess.CREATE_NO_WINDOW,bufsize=0)
    process._books_suspended=True
    lost=threading.Event()
    with OwnedProcessJob(process):
        proof=owner_proof(process)
        print('BOOKS_ENGINE_OWNER '+json.dumps(proof),flush=True)
        pumps=[threading.Thread(target=pump,args=(process.stdout,sys.stdout),daemon=True),threading.Thread(target=pump,args=(process.stderr,sys.stderr),daemon=True)]
        for thread in pumps:thread.start()
        threading.Thread(target=shell_pipe,args=(process,lost),daemon=True).start()
        while process.poll() is None:
            time.sleep(.1)
        for thread in pumps:thread.join(timeout=2)
        return process.returncode

if __name__=='__main__':raise SystemExit(main())
