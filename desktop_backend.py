"""Books Arranger desktop sidecar: the browser backend run by the Electron shell.

The shell starts this with the bundled Windows embeddable Python. It adds a small
desktop-only control surface (status, finish-then-quit, immediate safe stop) that
is authenticated by a per-launch secret the shell passes in the environment, and
it stops safely if the shell disappears (standard input closes).
"""
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

TOKEN_VARIABLE = 'BOOKS_ARRANGER_DESKTOP_TOKEN'


class DesktopControl:
    """Quit drain: the book in progress finishes, nothing new starts, then the process exits."""

    def __init__(self, server):
        self.server = server
        self.lock = threading.Lock()
        self.phase = 'running'
        self.requested_at = None
        self.error = ''
        self.thread = None

    def _automatic(self):
        return getattr(self.server.merge, 'automatic', None)

    def busy(self):
        merge = self.server.merge
        jobs = merge.state()
        automatic = self._automatic()
        return {'converting': jobs['state'] in ('Running', 'Pausing'),
                'current_title': jobs.get('current_title', ''),
                'stage': jobs.get('stage', ''),
                'queued': jobs.get('queued', 0),
                'automatic': automatic.status()['state'] if automatic is not None else 'Idle',
                'scanning': self.server.scan_active()}

    def status(self):
        with self.lock:
            value = {'phase': self.phase, 'error': self.error, 'requested_at': self.requested_at}
        if self.phase in ('running', 'finishing', 'parking'):
            try:
                value['busy'] = self.busy()
            except Exception:
                value['busy'] = None
        try:
            from app_launcher import verify_idle
            verify_idle(self.server.state('Audiobooks'))
            value['idle']=not self.server.closing and not self.server.merge_admissions
        except Exception:value['idle']=False
        return value

    def quit(self):
        with self.lock:
            if self.phase not in ('running', 'blocked') or (self.thread and self.thread.is_alive()):
                return {'phase': self.phase}
            self.error = ''
            self.phase = 'finishing'
            self.requested_at = time.time()
        with self.server.control_condition:
            # New controls are refused from here on; reads and polling keep working.
            self.server.closing = True
        merge = self.server.merge
        merge.drain()
        self.server.inventory.stop()
        automatic = self._automatic()
        if automatic is not None:
            automatic.stop()
        self.thread = threading.Thread(target=self._park, name='books-desktop-quit', daemon=True)
        self.thread.start()
        return {'phase': 'finishing'}

    def _parked(self):
        automatic = self._automatic()
        research = bool(automatic is not None and automatic.thread and automatic.thread.is_alive())
        return self.server.merge.drained() and not research and not self.server.scan_active()

    def _park(self):
        try:
            while not self._parked():
                if not (self.server.merge.jobs._thread and self.server.merge.jobs._thread.is_alive()):
                    with self.lock:
                        self.phase = 'parking'
                time.sleep(.5)
        except Exception as error:
            with self.lock:
                self.phase = 'blocked'
                self.error = str(error)[:512] or type(error).__name__
            return  # Keep server, native catalog lease and ownership record alive.
        self._shutdown()

    def _shutdown(self):
        try:
            self.server.finish_shutdown()
        except Exception as error:
            with self.lock:
                self.phase = 'blocked'
                self.error = str(error)[:512] or type(error).__name__
            return False  # A failed close is not authority to release ownership.
        with self.lock:
            self.phase = 'exiting'
        return True

    def prepare_update(self):
        """Atomic full-idle fence; normal Quit does not install updates."""
        from app_launcher import verify_idle
        with self.server.control_condition:
            if self.server.closing or self.server.merge_admissions:
                raise RuntimeError('Wait until all Books Arranger work is idle before restarting to update')
            verify_idle(self.server.state('Audiobooks'))
            self.server.closing=True
        with self.lock:
            self.phase='updating';self.error=''
        self.thread=threading.Thread(target=self._shutdown,name='books-desktop-update',daemon=True)
        self.thread.start()
        return {'phase':'updating'}

    def stop_now(self):
        """Immediate safe stop (Windows sign-out or shell loss): the book in progress restarts later."""
        with self.lock:
            if self.phase in ('stopping', 'exiting'):
                return {'phase': self.phase}
            self.phase = 'stopping'
        self.server.inventory.stop()
        with self.server.control_condition:
            self.server.closing = True
        threading.Thread(target=self._shutdown, name='books-desktop-stop', daemon=True).start()
        return {'phase': 'stopping'}


def handler_class(base, token):
    class DesktopHandler(base):
        def desktop_trusted(self):
            if not self.trusted():
                return False
            if not secrets.compare_digest(self.headers.get('X-Books-Desktop', '').encode('utf-8'), token.encode('ascii')):
                self.fail(403, 'Missing or invalid desktop control token')
                return False
            return True

        def do_GET(self):
            if urlsplit(self.path).path != '/api/desktop/status':
                return super().do_GET()
            if not self.desktop_trusted():
                return
            if urlsplit(self.path).query:
                return self.fail(400, 'Desktop status takes no query parameters')
            self.response(200, self.server.desktop.status())

        def do_POST(self):
            path = urlsplit(self.path).path
            if path not in ('/api/desktop/quit', '/api/desktop/stop-now', '/api/desktop/update'):
                return super().do_POST()
            if not self.desktop_trusted():
                return
            try:
                if urlsplit(self.path).query or self.body():
                    raise ValueError('Desktop controls take an empty JSON object')
            except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as error:
                return self.fail(400, str(error))
            control = self.server.desktop
            try:
                result=control.prepare_update() if path.endswith('/update') else control.quit() if path.endswith('/quit') else control.stop_now()
            except RuntimeError as error:return self.fail(409,str(error))
            self.response(202,result)

    return DesktopHandler


def watch_shell(control):
    """The shell keeps our standard input open; end of input means it is gone."""
    # Raw descriptor reads: a daemon thread parked inside the buffered stdin reader
    # holds its lock and crashes interpreter shutdown.
    try:
        descriptor = sys.stdin.fileno()
    except (AttributeError, OSError, ValueError):
        return
    try:
        while os.read(descriptor, 4096):
            pass
    except OSError:
        pass
    if control.phase in ('running', 'finishing', 'parking'):
        control.stop_now()


def _process_running(pid):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)  # SYNCHRONIZE | QUERY_LIMITED_INFORMATION
    if not handle:
        return ctypes.get_last_error() != 87  # only "invalid parameter" proves no such process
    try:
        return kernel.WaitForSingleObject(handle, 0) == 0x102  # WAIT_TIMEOUT: still running
    finally:
        kernel.CloseHandle(handle)


def retire_stale_record(database, roots, port):
    """Preserve one exact, valid dead-owner record under catalog/data ownership.

    Called only by web_server's guarded startup after source exclusion and the
    catalog lease. Unknown records are never adopted, renamed or deleted.
    """
    import hashlib, uuid
    from catalog_owner import ACTIVE_CATALOG
    if ACTIVE_CATALOG.get() != str(Path(database).absolute()):
        raise RuntimeError('Stale owner retirement requires the retained catalog lease')
    from scanner import inside
    from native_io import DirectoryBoundary, VerifiedFile, publish_no_replace
    from source_cleanup import single_stream
    database = Path(database).absolute()
    if any(inside(database, root) for root in roots.values()):
        raise ValueError('Keep the inventory database outside source libraries')
    record = database.parent / 'web-instance.json'
    with DirectoryBoundary(record.anchor, record.parent) as boundary:
        if not record.exists():
            return None
        with VerifiedFile(record, delete=True) as held:
            facts = held.facts()
            if facts['links'] != 1 or facts['size'] > 4096:
                raise RuntimeError('Previous ownership record is not a bounded unique file')
            single_stream(record)
            raw = b''.join(held.chunks())
            try:
                value = json.loads(raw.decode('utf-8'))
            except (ValueError, UnicodeError):
                raise RuntimeError('Unknown ownership record was preserved')
            if (not isinstance(value, dict) or value.get('application') != 'Books Arranger' or
                    type(value.get('pid')) is not int or value['pid'] <= 0 or
                    not isinstance(value.get('instance'), str) or len(value['instance']) != 32 or
                    any(c not in '0123456789abcdef' for c in value['instance']) or
                    not isinstance(value.get('version'), str) or
                    value.get('url') != f'http://127.0.0.1:{port}/'):
                raise RuntimeError('Unknown ownership record was preserved')
            pid = value['pid']
            if pid == os.getpid() or _process_running(pid):
                return None
            identity = [held.info.volume, held.info.index_high, held.info.index_low]
            digest = hashlib.sha256(raw).hexdigest()
        aside = record.with_name('web-instance.stale-' + uuid.uuid4().hex + '.json')
        def exact_generation(observed):
            if observed['identity'] != identity or _process_running(pid):
                raise RuntimeError('Changed or live ownership record was preserved')
            single_stream(record)
        publish_no_replace(record, aside, boundary, expected_sha256=digest,
                           expected_size=len(raw), before_rename=exact_generation)
        print('Previous dead Books Arranger ownership record retained as ' + aside.name, flush=True)
        return aside


def database_argument(argv):
    for index, value in enumerate(argv):
        if value == '--database' and index + 1 < len(argv):
            return argv[index + 1]
        if value.startswith('--database='):
            return value.split('=', 1)[1]
    return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    mode=None
    for value in list(argv):
        if value.startswith('--catalog-mode='):
            if mode is not None:raise SystemExit('Duplicate catalog selection mode')
            mode=value.split('=',1)[1];argv.remove(value)
    if mode not in ('existing','new'):raise SystemExit('Desktop catalog requires explicit Existing or New selection')
    token = os.environ.pop(TOKEN_VARIABLE, '')
    if len(token) < 32 or not token.isascii():
        raise SystemExit('Books Arranger desktop backend must be started by the Books Arranger app.')
    # The shell reads our output as UTF-8 whatever the Windows code page is.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    database = database_argument(argv)
    if not database:
        raise SystemExit('Books Arranger desktop backend needs --database.')
    import web_server

    def ready(server):
        server.RequestHandlerClass = handler_class(web_server.Handler, token)
        server.desktop = DesktopControl(server)
        threading.Thread(target=watch_shell, args=(server.desktop,), name='books-desktop-shell', daemon=True).start()

    def startup_guard(database, roots, port):
        from desktop_catalog import inspect_folder
        inspect_folder(Path(database).parent,mode,roots,(Path(__file__).resolve().parent,))
    web_server.main(argv, ready=ready, before_start=retire_stale_record,
                    startup_guard=startup_guard,create_data=mode=='new')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
