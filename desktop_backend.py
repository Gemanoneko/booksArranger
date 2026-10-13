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
        return value

    def quit(self):
        with self.lock:
            if self.phase != 'running':
                return {'phase': self.phase}
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
            # Never leave the shell waiting forever on a monitoring failure; the
            # shutdown below still stops every worker at its safe checkpoint.
            self.error = type(error).__name__
        with self.lock:
            self.phase = 'exiting'
        self._shutdown()

    def _shutdown(self):
        try:
            self.server.finish_shutdown()
        except Exception as error:
            self.error = self.error or type(error).__name__
        finally:
            # finish_shutdown stops serving only after a clean close; always stop serving.
            self.server.shutdown()

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
            if path not in ('/api/desktop/quit', '/api/desktop/stop-now'):
                return super().do_POST()
            if not self.desktop_trusted():
                return
            try:
                if urlsplit(self.path).query or self.body():
                    raise ValueError('Desktop controls take an empty JSON object')
            except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as error:
                return self.fail(400, str(error))
            control = self.server.desktop
            self.response(202, control.quit() if path.endswith('/quit') else control.stop_now())

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


def retire_stale_record(database):
    """Move aside an ownership record whose recorded process is gone (the app was ended abruptly).

    A record that cannot be read, or whose process still runs, is left in place, and the
    normal startup refuses as before. The stale record is kept beside it as evidence.
    """
    record = Path(database).parent / 'web-instance.json'
    try:
        raw = record.read_bytes() if record.is_file() and not record.is_symlink() else None
    except OSError:
        return None
    if raw is None or len(raw) > 4096:
        return None
    try:
        pid = json.loads(raw.decode('utf-8'))['pid']
    except (ValueError, KeyError, TypeError, UnicodeError):
        return None
    if type(pid) is not int or pid <= 0 or pid == os.getpid() or _process_running(pid):
        return None
    aside = record.with_name(f'web-instance.stale-{time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())}-pid{pid}.json')
    try:
        os.rename(record, aside)  # never replaces an existing file
    except OSError:
        return None  # another starter moved it first, or it is in use: normal startup decides
    print(f'Previous Books Arranger process {pid} had ended without closing; its record was kept as {aside.name}', flush=True)
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
    retire_stale_record(database)
    import web_server

    def ready(server):
        server.RequestHandlerClass = handler_class(web_server.Handler, token)
        server.desktop = DesktopControl(server)
        threading.Thread(target=watch_shell, args=(server.desktop,), name='books-desktop-shell', daemon=True).start()

    web_server.main(argv, ready=ready)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
