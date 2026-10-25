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


class UpdateStarted(RuntimeError):
    """Cancel arrived after the engine began ending for the update: too late to cancel."""


class DesktopControl:
    """Quit drain: the book in progress finishes, nothing new starts, then the process exits."""

    # After a successful shutdown (every worker reached its checkpoint and the server closed) the process
    # must end. A thread left behind kept it alive, so its native host never exited and the shell waited
    # forever with no window (v0.16.8 item 2). The desktop main arms this; tests leave it off.
    EXIT_AFTER = 20.0

    def __init__(self, server, exit_bound=None, exit_process=None):
        self.server = server
        self.lock = threading.Lock()
        self.phase = 'running'
        self.requested_at = None
        self.error = ''
        self.thread = None
        self.exit_bound = exit_bound
        self.exit_process = exit_process or os._exit

    def _bound_exit(self):
        """Shutdown succeeded: if this process is still alive after exit_bound, report what kept it and end it."""
        if self.exit_bound is None:
            return None
        def watchdog():
            time.sleep(self.exit_bound)
            lingering = [thread.name for thread in threading.enumerate() if not thread.daemon and thread is not threading.main_thread()]
            try:
                print('Books Arranger engine exit forced after a completed shutdown; still running: ' + (', '.join(lingering) or 'main thread'), file=sys.stderr, flush=True)
            except Exception:
                pass
            self.exit_process(0)
        thread = threading.Thread(target=watchdog, name='books-exit-bound', daemon=True)
        thread.start()
        return thread

    def _automatic(self):
        return getattr(self.server.merge, 'automatic', None)

    STATUS_ANSWER = 4.0  # seconds; the shell gives each desktop status request 5 s, Quit included

    def _bounded_state(self):
        """Desktop status answers within STATUS_ANSWER whatever the engine is doing.

        A slow state computation keeps running in its helper thread (and is shared by the next poll
        through the status snapshot); this request reports "unavailable" instead of making the shell's
        Quit time out.
        """
        from merge_service import StatusUnavailable
        box = {}

        def compute():
            try:
                box['value'] = self.server.state('Audiobooks', cached=True)
            except BaseException as error:
                box['error'] = error
        worker = threading.Thread(target=compute, name='books-desktop-status', daemon=True)
        worker.start()
        worker.join(self.STATUS_ANSWER)
        if worker.is_alive():
            raise StatusUnavailable('Status computation is still running')
        if 'error' in box:
            raise box['error']
        return box['value']

    def busy(self, snapshot=None):
        """Derive busy facts from the caller's state snapshot; compute one only when none is supplied."""
        if snapshot is not None and isinstance(snapshot.get('audiobook_jobs'), dict):
            jobs = snapshot['audiobook_jobs']
            automatic_state = (snapshot.get('automatic_processing') or {}).get('state', 'Idle')
        else:
            merge = self.server.merge
            jobs = merge.status_snapshot() if hasattr(merge, 'status_snapshot') else merge.state()
            automatic = self._automatic()
            automatic_state = automatic.status()['state'] if automatic is not None else 'Idle'
        return {'converting': jobs['state'] in ('Running', 'Pausing'),
                'current_title': jobs.get('current_title', ''),
                'stage': jobs.get('stage', ''),
                'queued': jobs.get('queued', 0),
                'automatic': automatic_state,
                'scanning': self.server.scan_active()}

    def status(self):
        with self.lock:
            value = {'phase': self.phase, 'error': self.error, 'requested_at': self.requested_at}
            if self.update is not None:
                value.update(self._update_answer())
            if self.phase in self.UPDATE_PHASES:
                # Stopping for an update: answer at once from what the update tracks; no state computation.
                value['busy'] = None
                value['idle'] = False
                return value
        # One shared state computation per poll feeds both busy and idle (was two full computations).
        from merge_service import StatusUnavailable
        unavailable = False
        try:
            snapshot = self._bounded_state()
        except StatusUnavailable:
            # A slow computation is still running: answer "unknown" now rather than wait again.
            # Phase stays readable, so Quit and its watch keep working.
            snapshot, unavailable = None, True
            value['status'] = 'unavailable'
        except Exception:
            snapshot = None
        if self.phase in ('running', 'finishing', 'parking'):
            try:
                value['busy'] = None if unavailable else self.busy(snapshot)
            except Exception:
                value['busy'] = None
        try:
            from app_launcher import verify_idle
            if snapshot is None:raise RuntimeError('Status unavailable')
            verify_idle(snapshot)
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
        self._bound_exit()
        return True

    # ------------------------------------------------------------------ Restart to update (ruling 27, 0.22.1)
    # Sergei 2026-10-25: "There should be steps to make update fail-less." 0.21.1's Restart to update computed a fresh,
    # unbounded state inside the request (the full-idle fence) while the shell gave it 5 s; the shell gave up, the engine
    # finished the fence anyway and shut down, and the app closed without installing. Nothing ever undid the fence.
    # Now the request answers at once; the work stops at its next safe point (bounded), the engine exits only when
    # nothing is left running and no file change is half done (critical_sections), and Cancel, or the bound, undoes
    # every step: the app runs on as before.
    UPDATE_SAFE = 90.0    # T_safe: seconds for the running work to reach its next safe point
    UPDATE_FORCE = 60.0   # T_force: then presses in flight are stopped too; a file change still finishes by itself
    UPDATE_POLL = 0.25
    UPDATE_PHASES = ('pausing', 'forcing', 'updating')

    def prepare_update(self):
        """POST /api/desktop/update: starts stopping for the update and answers at once (no state computation here).
        A repeated request answers the update in progress. Raises RuntimeError while a Quit is under way."""
        with self.lock:
            if self.phase in self.UPDATE_PHASES or self.phase == 'exiting' and self.update is not None:
                return self._update_answer()
            if self.phase not in ('running', 'blocked') or (self.thread and self.thread.is_alive()):
                raise RuntimeError('Books Arranger is closing; the update can start once it has closed')
            self.update = {'requested_at': time.time(), 'started': time.monotonic(), 'before': self._update_before(),
                           'cancel': threading.Event(), 'waiting': [], 'critical': [], 'forced': False, 'outcome': None}
            self.phase = 'pausing'
            self.error = ''
        with self.server.control_condition:
            # New controls are refused from here on; reads and polling keep working.
            self.server.closing = True
        self.thread = threading.Thread(target=self._update_park, name='books-desktop-update', daemon=True)
        self.thread.start()
        return self._update_answer()

    update = None

    def _update_before(self):
        """What runs now, read cheaply (no state computation): Cancel and the bound start it again."""
        merge = self.server.merge
        automatic = self._automatic()
        jobs_thread = getattr(getattr(merge, 'jobs', None), '_thread', None)
        cleanup = getattr(merge, 'cleanup', None)
        title = ''
        try:
            from scanner import connect
            with connect(self.server.merge.inventory.database) as db:
                row = db.execute("SELECT manifest FROM audio_jobs WHERE state='running' LIMIT 1").fetchone()
            title = (json.loads(row[0]).get('metadata') or {}).get('title', '') if row else ''
        except Exception:
            title = ''
        return {'automatic': bool(automatic is not None and getattr(automatic, 'thread', None) and automatic.thread.is_alive()),
                'converting': bool(jobs_thread and jobs_thread.is_alive()), 'title': str(title)[:200],
                'cleanup': bool(cleanup is not None and (getattr(cleanup, 'current', None) or getattr(cleanup, 'thread', None) and cleanup.thread.is_alive())),
                'scanning': bool(self.server.scan_active()), 'library': getattr(self.server, 'active_library', None)}

    def _update_answer(self):
        """The update part of desktop status (also the POST answers)."""
        update = self.update or {}
        elapsed = max(0.0, time.monotonic() - update['started']) if update.get('started') else 0.0
        return {'phase': self.phase, 'update': {'phase': self.phase if self.phase in self.UPDATE_PHASES + ('exiting', 'blocked') else 'running',
                'waiting': [dict(item) for item in update.get('waiting') or []], 'critical': list(update.get('critical') or []),
                'elapsed': round(elapsed, 1), 'safe_seconds': self.UPDATE_SAFE, 'force_seconds': self.UPDATE_FORCE,
                'outcome': dict(update['outcome']) if update.get('outcome') else None}}

    def _update_waiting(self):
        """[{kind, title}] of what the update still waits for: the conversion of a book, its cleanup, the library scan,
        research or automatic processing, an approval or another press, series or optional-field lookups, and any open
        file change (critical_sections)."""
        import critical_sections
        merge = self.server.merge
        waiting = []
        jobs_thread = getattr(getattr(merge, 'jobs', None), '_thread', None)
        if jobs_thread and jobs_thread.is_alive():
            waiting.append({'kind': 'conversion', 'title': (self.update or {}).get('before', {}).get('title', '')})
        cleanup = getattr(merge, 'cleanup', None)
        if cleanup is not None and (getattr(cleanup, 'current', None) or getattr(cleanup, 'thread', None) and cleanup.thread.is_alive()) \
                or getattr(merge, '_post_current', None):
            waiting.append({'kind': 'cleanup', 'title': ''})
        if self.server.scan_active():
            waiting.append({'kind': 'scan', 'title': ''})
        automatic = self._automatic()
        if automatic is not None and getattr(automatic, 'thread', None) and automatic.thread.is_alive():
            waiting.append({'kind': 'research' if (getattr(automatic, 'current', None) or {}).get('stage', '').startswith('Research') else 'automatic', 'title': ''})
        if getattr(self.server, 'merge_admissions', 0):
            waiting.append({'kind': 'approval' if getattr(merge, '__dict__', {}).get('_approve_stops') else 'press', 'title': ''})
        for name in ('series_backfill', 'gap_fill'):
            worker = getattr(getattr(merge, '__dict__', {}).get(name), 'thread', None)
            if worker is not None and worker.is_alive():
                waiting.append({'kind': 'lookups', 'title': ''})
                break
        for name in critical_sections.open_sections():
            waiting.append({'kind': 'critical', 'title': name})
        return waiting

    def _update_park(self):
        """Stop the work at its safe points, wait (bounded), then end the engine; Cancel or the bound undo it all."""
        import critical_sections
        update = self.update
        merge = self.server.merge
        try:
            automatic = self._automatic()
            if automatic is not None:
                automatic.stop()  # saves the research checkpoint; pauses the queue when a run is active
            self.server.inventory.stop()  # the scan stops at its checkpoint (Resume scanning continues it)
            merge.pause()  # the book in progress stops at its next checkpoint and starts again later
            for name in ('series_backfill', 'gap_fill'):
                background = getattr(merge, '__dict__', {}).get(name)
                if background is not None:
                    background.stop.set(); background.wake.set()
            safe = update['started'] + self.UPDATE_SAFE
            last = safe + self.UPDATE_FORCE
            while True:
                if update['cancel'].is_set():
                    return self._resume_after_update('cancelled')
                waiting = self._update_waiting()
                with self.lock:
                    update['waiting'] = waiting
                    update['critical'] = critical_sections.open_sections()
                if not waiting:
                    break
                now = time.monotonic()
                if now >= last:
                    return self._resume_after_update('bound')
                if now >= safe and not update['forced']:
                    with self.lock:
                        self.phase = 'forcing'
                        update['forced'] = True
                    self._force_update_stops()
                time.sleep(self.UPDATE_POLL)
            # Nothing runs and no file change is open: closing refuses new presses and every worker has stopped, so
            # none can open one now. Cancel still wins until this point.
            with self.lock:
                cancelled = update['cancel'].is_set()
                if not cancelled:
                    self.phase = 'updating'
            if cancelled:
                return self._resume_after_update('cancelled')
            if not self._shutdown():
                # A close that failed before the engine ended undoes the update too (proposal 5B6): the app runs on.
                return self._resume_after_update('blocked', self.error)
        except Exception as error:
            with self.lock:
                self.phase = 'blocked'
                self.error = str(error)[:512] or type(error).__name__
                update['outcome'] = {'result': 'error', 'reason': self.error}

    def _force_update_stops(self):
        """After T_safe: presses still running (an approval checking files) are stopped too. A file change that has
        started is never stopped; the update waits for it."""
        merge = self.server.merge
        for press in list(getattr(merge, '__dict__', {}).get('_approve_stops', ())):
            press.set()
        pending = getattr(merge, '__dict__', {}).get('_retry_all_stop')
        if pending:
            pending.set()
        automatic = self._automatic()
        if automatic is not None:
            try:
                automatic.stop(force=True)
            except Exception:
                pass

    def _resume_after_update(self, result, reason=''):
        """Cancel, the bound or a failed close: undo the update's stops and start again what was running. The app runs
        on as before."""
        update = self.update
        before = update.get('before') or {}
        with self.server.control_condition:
            self.server.closing = False
            self.server.control_condition.notify_all()
        problems = []
        merge = self.server.merge
        automatic = self._automatic()
        try:
            if before.get('automatic') and automatic is not None:
                automatic.start()  # continues the saved run, which starts the queue again
            elif before.get('converting') or before.get('cleanup'):
                resume = merge.resume
                try:
                    resume(recheck=False)
                except TypeError:
                    resume()
        except Exception as error:
            problems.append(str(error)[:300] or type(error).__name__)
        try:
            if before.get('scanning') and not before.get('automatic') and before.get('library'):
                self.server.inventory.launch(before['library'], resume=True)
                self.server.active_library = before['library']
        except Exception as error:
            problems.append(str(error)[:300] or type(error).__name__)
        for name in ('series_backfill', 'gap_fill'):
            background = getattr(merge, '__dict__', {}).get(name)
            if background is not None:
                try:
                    background.start()
                except Exception as error:
                    problems.append(str(error)[:300])
        with self.lock:
            self.phase = 'running'
            self.error = ''
            update['outcome'] = {'result': result, 'waiting': [dict(item) for item in update.get('waiting') or []], 'at': time.time(),
                                 'reason': reason, 'resume_problems': problems}
        return update['outcome']

    def cancel_update(self):
        """POST /api/desktop/update-cancel: the update stops; everything it stopped starts again. Raises UpdateStarted
        once the engine is ending (too late to cancel)."""
        with self.lock:
            if self.phase in ('pausing', 'forcing') and self.update is not None:
                self.update['cancel'].set()
                thread = self.thread
            elif self.phase in ('updating', 'exiting', 'stopping'):
                raise UpdateStarted('The update has started; Books Arranger is closing to install it')
            else:
                return self._update_answer()
        if thread is not None and thread is not threading.current_thread():
            thread.join(30)
        with self.lock:
            return self._update_answer()

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
            if path not in ('/api/desktop/quit', '/api/desktop/stop-now', '/api/desktop/update', '/api/desktop/update-cancel'):
                return super().do_POST()
            if not self.desktop_trusted():
                return
            self.status_control = True  # Desktop controls also drop the shared status answer (Handler.response).
            try:
                if urlsplit(self.path).query or self.body():
                    raise ValueError('Desktop controls take an empty JSON object')
            except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as error:
                return self.fail(400, str(error))
            control = self.server.desktop
            if path.endswith('/update-cancel'):
                try:
                    return self.response(200, control.cancel_update())
                except UpdateStarted as error:
                    return self.response(409, {'error': str(error), 'code': 'started'})
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
    if control.phase in ('running', 'finishing', 'parking', 'pausing', 'forcing'):
        control.stop_now()


def _process_running(pid):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)  # SYNCHRONIZE | QUERY_LIMITED_INFORMATION
    if not handle:
        return ctypes.get_last_error() != 87  # only "invalid parameter" proves no such process
    try:
        status=kernel.WaitForSingleObject(handle,0)
        if status==0:return False  # WAIT_OBJECT_0: exact retained process has exited.
        if status==0x102:return True  # WAIT_TIMEOUT: still running.
        raise RuntimeError('Previous app lifetime cannot be verified; ownership record preserved')
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
        server.desktop = DesktopControl(server, exit_bound=DesktopControl.EXIT_AFTER)
        threading.Thread(target=watch_shell, args=(server.desktop,), name='books-desktop-shell', daemon=True).start()

    def startup_guard(database, roots, port):
        from desktop_catalog import inspect_folder
        inspect_folder(Path(database).parent,mode,roots,(Path(__file__).resolve().parent,))
    web_server.main(argv, ready=ready, before_start=retire_stale_record,
                    startup_guard=startup_guard,create_data=mode=='new')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
