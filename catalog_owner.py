"""Exclusive catalog ownership shared by every Books Arranger interface.

Kept free of GUI imports so the browser backend also runs on the Windows
embeddable Python bundled with the desktop app, which has no Tkinter.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path

from scanner import inside

BASE = Path(__file__).resolve().parent
ACTIVE_CATALOG = ContextVar('books_owned_catalog', default=None)

@contextmanager
def catalog_lock(database, roots):
    """Prevent a second application resetting the first application's live queue."""
    if any(inside(database, root) for root in roots.values()):
        raise ValueError('Keep the inventory database outside source libraries')
    lock_path = Path(str(database) + '.lock')
    if os.name == 'nt':
        import ctypes
        from native_io import DirectoryBoundary, VerifiedFile, FileInfo, kernel
        from source_cleanup import single_stream
        with DirectoryBoundary(lock_path.anchor, lock_path.parent, create=True) as held_boundary:
            if not lock_path.exists():
                # CREATE_NEW, protected from birth. Never truncate an unknown entry.
                handle = kernel.CreateFileW(str(lock_path),0xC0000081,1,None,1,0x00200000,None)
                if handle == ctypes.c_void_p(-1).value:
                    raise RuntimeError('Catalog ownership file could not be created safely')
                kernel.CloseHandle(handle)
            with VerifiedFile(lock_path,writable=True) as held:
                if held.facts()['links'] != 1:
                    raise RuntimeError('Catalog ownership file must be unique')
                single_stream(lock_path)
                # Deny-write/delete sharing conflicts with both other native owners
                # and the legacy msvcrt open+write lock; no PID liveness inference.
                marker = ACTIVE_CATALOG.set(str(Path(database).absolute()))
                try:yield {'schema':'books-catalog-owner-v1','lock_path':str(lock_path),'lock_identity':held.facts()['identity'],'lock_facts':held.facts(),'lock_ancestry':held_boundary.identities,'held':True}
                finally:ACTIVE_CATALOG.reset(marker)
        return
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, 'a+b') as handle:
        handle.seek(0)
        handle.write(b'0')
        handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise RuntimeError('This catalog is already open in another Books Arranger window') from error
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
