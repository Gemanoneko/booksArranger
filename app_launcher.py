"""Normal user-launched, windowless Books Arranger lifecycle (Windows only)."""
import contextlib
import ctypes
from ctypes import wintypes
import json
import hashlib
import os
from pathlib import Path
import re
import socket
import sqlite3
import sys
import time
import threading
import urllib.request
import webbrowser

BASE = Path(__file__).resolve().parent
DATABASE = BASE / 'data' / 'inventory.sqlite3'
RECORD = DATABASE.parent / 'web-instance.json'
URL = 'http://127.0.0.1:5210/'
MAX_REPLY = 256 * 1024

class LaunchError(RuntimeError):
    pass

class WindowsProcess:
    """Hold an exact process generation; never terminate it or launch a child."""
    def __init__(self, pid=None):
        if os.name != 'nt': raise LaunchError('Books Arranger requires Windows for its normal app launcher.')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        for name, args, result in (
            ('GetCurrentProcess', [], wintypes.HANDLE),
            ('GetProcessId', [wintypes.HANDLE], wintypes.DWORD),
            ('OpenProcess', [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD], wintypes.HANDLE),
            ('CloseHandle', [wintypes.HANDLE], wintypes.BOOL),
            ('QueryFullProcessImageNameW', [wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
            ('WaitForSingleObject', [wintypes.HANDLE,wintypes.DWORD], wintypes.DWORD),
        ):
            method = getattr(k,name);method.argtypes=args;method.restype=result
        self.owned = pid is not None
        self.handle = k.OpenProcess(0x100000 | 0x1000,False,pid) if self.owned else k.GetCurrentProcess()
        if not self.handle:
            error=ctypes.get_last_error()
            if pid is not None and error==87: raise ProcessLookupError(pid)
            raise LaunchError('The app process identity could not be checked.')
        self.pid=k.GetProcessId(self.handle)
        if not self.pid or pid is not None and self.pid != pid:
            self.close();raise LaunchError('The app process identity changed.')
    def close(self):
        if self.owned and self.handle: self.kernel.CloseHandle(self.handle)
        self.handle=None
    def __enter__(self): return self
    def __exit__(self,*_): self.close()
    def alive(self):
        result=self.kernel.WaitForSingleObject(self.handle,0)
        if result not in (0,258): raise LaunchError('Windows could not check whether the app is still running.')
        return result==258
    def wait_exit(self, timeout=60):
        result=self.kernel.WaitForSingleObject(self.handle,int(timeout*1000))
        if result!=0: raise LaunchError('Books Arranger is still stopping. Wait for shutdown to finish, then open Books Arranger.')
    def image(self):
        buffer=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(buffer))
        if not self.kernel.QueryFullProcessImageNameW(self.handle,0,buffer,ctypes.byref(size)):
            raise LaunchError('The app executable could not be verified.')
        return Path(buffer.value).resolve()

def local_request(path, data=None, token=None):
    headers={'Origin':URL.rstrip('/')}
    if token: headers['X-Books-Token']=token
    if data is not None: headers['Content-Type']='application/json'
    request=urllib.request.Request(URL+path.lstrip('/'),data=json.dumps(data).encode() if data is not None else None,headers=headers)
    # Do not route this local control through proxy configuration or redirects.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*_): return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(request,timeout=5) as response:
        raw=response.read(MAX_REPLY+1)
        if len(raw)>MAX_REPLY: raise LaunchError('The local app response was too large to verify.')
        return raw

def read_json(path, **kwargs):
    value=json.loads(local_request(path,**kwargs))
    if not isinstance(value,dict):raise LaunchError('The local app response could not be verified.')
    return value

def receipt():
    from web_server import read_instance_record
    value=json.loads(read_instance_record(RECORD))
    if not isinstance(value,dict) or value.get('application')!='Books Arranger' or value.get('port')!=5210 or value.get('url')!=URL or type(value.get('pid')) is not int or value['pid']<=0 or not re.fullmatch('[a-f0-9]{32}',str(value.get('instance',''))):
        raise LaunchError('Books Arranger could not verify the app to restart. The restart was cancelled.')
    return value

def same_owner(record, health):
    keys=('application','version','instance','pid','port')
    return all(record.get(key)==health.get(key) for key in keys) and not health.get('closing')

@contextlib.contextmanager
def verified_owner():
    if not os.path.lexists(RECORD):
        # Absence of a record is not proof that the port is available; new startup binds exclusively.
        yield None;return
    record=receipt()
    try: owner=WindowsProcess(record['pid'])
    except ProcessLookupError as error:
        raise LaunchError('Books Arranger has an old ownership record. Its previous exit needs recovery before a new app can start.') from error
    with owner:
        allowed={Path(sys.executable).resolve(),Path(sys.executable).resolve().with_name('python.exe'),Path(sys.executable).resolve().with_name('pythonw.exe')}
        if owner.image() not in allowed or not owner.alive() or not same_owner(record,read_json('api/health')) or receipt()!=record:
            raise LaunchError('Books Arranger could not verify the app to restart. The restart was cancelled.')
        yield (owner,record)

@contextlib.contextmanager
def launch_lease():
    """Own one session-local startup mutex; never write or supervise a service file."""
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
    kernel.ReleaseMutex.argtypes=[wintypes.HANDLE];kernel.ReleaseMutex.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    name='Local\\BooksArrangerStart-'+hashlib.sha256(str(DATABASE.resolve()).casefold().encode()).hexdigest()
    handle=kernel.CreateMutexW(None,False,name)
    if not handle:raise LaunchError('Books Arranger could not verify its startup permission.')
    acquired=False
    try:
        result=kernel.WaitForSingleObject(handle,0)
        if result not in (0,0x80):raise LaunchError('Books Arranger is already starting or restarting. Open it again after it is ready.')
        acquired=True
        yield
    finally:
        released=not acquired or bool(kernel.ReleaseMutex(handle))
        closed=bool(kernel.CloseHandle(handle))
        if not released or not closed:raise LaunchError('Books Arranger could not release its startup permission safely.')

def completed_records(database=DATABASE):
    """Compact read-only protection of published validation, metadata and candidate identity."""
    if not Path(database).exists():return {}
    with contextlib.closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as db:
        db.execute('PRAGMA query_only=ON');db.row_factory=sqlite3.Row
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='audio_jobs'").fetchone():return {}
        result={}
        for row in db.execute("SELECT job_id,manifest_hash,manifest,output FROM audio_jobs WHERE state='completed' ORDER BY job_id"):
            manifest=json.loads(row['manifest']);output=json.loads(row['output'])
            if not isinstance(output,dict) or output.get('validation',{}).get('passed') is not True:
                raise LaunchError('A completed audiobook record could not be verified. Automatic processing stays paused.')
            group=db.execute('SELECT id,revision,fingerprint FROM book_groups WHERE id=?',(manifest['candidate_id'],)).fetchone()
            context=db.execute('SELECT revision,data FROM candidate_context WHERE id=?',(manifest['candidate_id'],)).fetchone()
            if not group or not context:raise LaunchError('A completed audiobook identity could not be verified. Automatic processing stays paused.')
            result[row['job_id']]={'manifest_hash':row['manifest_hash'],'metadata':manifest['metadata'],'output':output,'candidate':dict(group),'context':{'revision':context['revision'],'data':json.loads(context['data'])}}
        return result

def restart_token(record):
    raw=local_request('');match=re.search(rb'<meta name="books-token" content="([A-Za-z0-9_-]{20,100})"',raw)
    if not match:raise LaunchError('The app restart permission could not be verified.')
    if not same_owner(record,read_json('api/health')):raise LaunchError('The app owner changed before restart. The restart was cancelled.')
    return match.group(1).decode('ascii')

def verify_idle(state):
    if state.get('active_library') or state.get('stopping'):raise LaunchError('Books Arranger is scanning. Stop scanning in the app, then choose Restart Books Arranger.')
    if state.get('recovery_active'):raise LaunchError('Books Arranger is working with recovery copies. Wait for it to finish, then choose Restart Books Arranger.')
    automatic=state.get('automatic_processing') or {}
    jobs=state.get('audiobook_jobs') or {}
    if jobs.get('cleanup_active') or jobs.get('state') in ('Running','Pausing'):
        action='Stop automatic processing and pause audiobook jobs in the app, then choose Restart Books Arranger.' if automatic.get('state') in ('Running','Stopping') else 'Pause audiobook jobs in the app, then choose Restart Books Arranger.'
        raise LaunchError('Books Arranger is processing an audiobook. '+action)
    if automatic.get('state') in ('Running','Stopping'):
        action='Stop automatic processing in the app, then choose Restart Books Arranger.'
        reason='Books Arranger is researching metadata. ' if automatic.get('phase')=='research' else 'Waiting for metadata sources; saved research retries automatically. ' if automatic.get('phase')=='waiting' and automatic.get('automatic_retry_enabled') else ''
        raise LaunchError(reason+action)
    if jobs.get('queued',0) and jobs.get('state')!='Paused':raise LaunchError('Books Arranger is processing an audiobook. Pause audiobook jobs in the app, then choose Restart Books Arranger.')

def reserve_port():
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        sock.bind(('127.0.0.1',5210))
        return sock
    except OSError as error:
        sock.close();raise LaunchError('Books Arranger could not start because another program is using its local address. Close that program, then open Books Arranger again.') from error

def run(restart=False, *, show=True):
    """An ordinary Pythonw process is the replacement itself, proved before old shutdown."""
    from scanner import DEFAULT_ROOTS
    from app import catalog_lock
    import web_server
    if Path(sys.executable).name.lower()!='pythonw.exe':raise LaunchError('Open Books Arranger from its Start menu entry to run without a console.')
    from native_io import DirectoryBoundary
    with contextlib.ExitStack() as startup:
        startup.enter_context(DirectoryBoundary(DATABASE.anchor,DATABASE.parent,create=True))
        startup.enter_context(launch_lease())
        with verified_owner() as existing:
            if existing and not restart:
                if show:webbrowser.open(URL)
                return 'reused'
        had_owner=False
        with verified_owner() as existing:
            expected=completed_records()
            if existing:
                owner,record=existing
                had_owner=True
                state=read_json('api/state?library=Audiobooks')
                if state.get('library')!='Audiobooks' or not isinstance(state.get('root'),str) or os.path.normcase(os.path.abspath(state['root']))!=os.path.normcase(os.path.abspath(DEFAULT_ROOTS['Audiobooks'])):
                    raise LaunchError('Books Arranger could not verify the app to restart. The restart was cancelled.')
                verify_idle(state)
                token=restart_token(record)
                answer=read_json('api/shutdown',data={'restart_instance':record['instance']},token=token)
                if answer!={'stopping':True}:raise LaunchError('The app did not acknowledge a safe restart. The restart was cancelled.')
                owner.wait_exit()
                if os.path.lexists(RECORD):raise LaunchError('The app ownership record did not close after restart. No replacement was started.')
        # Positive exclusive port and catalog proof; no uncertain connect timeout interpretation.
        with reserve_port(),catalog_lock(DATABASE,DEFAULT_ROOTS):
            if completed_records()!=expected:raise LaunchError('Saved completed audiobook records changed. The restart was cancelled.')
        def ready(server):
            if server.health()['version']!=web_server.version() or completed_records()!=expected:
                raise LaunchError('The new app could not verify its version and saved completed books. Automatic processing stays paused.')
            server.restart_context=bool(restart and had_owner)
            startup.close()
            if show:webbrowser.open(URL)
        try:web_server.main([],ready=ready)
        except Exception as error:
            if not had_owner:raise
            cause=str(error) if isinstance(error,LaunchError) else 'the new app startup checks failed'
            safe=False
            if not os.path.lexists(RECORD) and not any(t.is_alive() and not t.daemon and t is not threading.current_thread() for t in threading.enumerate()):
                try:
                    with reserve_port(),catalog_lock(DATABASE,DEFAULT_ROOTS):safe=completed_records()==expected
                except Exception:pass
            message='Books Arranger stopped, but could not restart: '+cause+'.'
            if safe:message+=' Open Books Arranger to retry.'
            raise LaunchError(message) from error
    return 'stopped'

def main(restart=False):
    try:
        if sys.version_info<(3,12):raise LaunchError('Books Arranger could not start. Python 3.12 or later is required.')
        run(restart)
    except Exception as error:
        # Do not show arbitrary tracebacks/source filenames/credentials in the normal app surface.
        message=str(error) if isinstance(error,LaunchError) else 'Books Arranger could not start. Its local startup checks failed.'
        surface=ctypes.WinDLL('user32',use_last_error=True).MessageBoxW
        surface.argtypes=[wintypes.HWND,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.UINT];surface.restype=ctypes.c_int
        surface(None,message[:600],'Books Arranger',0x10)
        return 1
    return 0
