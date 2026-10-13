"""Exclusive catalog ownership shared by every Books Arranger interface.

Kept free of GUI imports so the browser backend also runs on the Windows
embeddable Python bundled with the desktop app, which has no Tkinter.
"""
from contextlib import contextmanager
import os
from pathlib import Path

from scanner import inside

BASE = Path(__file__).resolve().parent

@contextmanager
def catalog_lock(database, roots):
    """Prevent a second application resetting the first application's live queue."""
    if any(inside(database, root) for root in roots.values()):
        raise ValueError('Keep the inventory database outside source libraries')
    lock_path = Path(str(database) + '.lock')
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
