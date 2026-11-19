"""0.22.1, ruling 27 (Sergei 2026-10-25: "updates must not fail"): the steps an update never interrupts.

Restart to update stops the engine's work at its next safe point and waits, bounded, for the rest. A few steps change a
file and its catalog record together and must end on their own once started: the in-place M4B tag edit (it writes
inside an original), a source-cleanup disposal, the Delete book file loop, and a file rename in Audiobooks Sorted.
They mark themselves here; the update reports them ("Finishing a tag edit first") and never stops the engine while one
is open. In memory only: a step that is open belongs to this process.
"""
import collections
import contextlib
import threading

_LOCK = threading.Lock()
_OPEN = collections.Counter()

TAG_EDIT = 'a tag edit'
CLEANUP = 'a cleanup'
DELETE = 'a delete'
RENAME = 'a file rename'


@contextlib.contextmanager
def critical(name):
    """Mark one step that must finish once started."""
    with _LOCK:
        _OPEN[name] += 1
    try:
        yield
    finally:
        with _LOCK:
            _OPEN[name] -= 1
            if _OPEN[name] <= 0:
                del _OPEN[name]


def open_sections():
    """The names of the steps open now, sorted."""
    with _LOCK:
        return sorted(_OPEN)


# Senua's 0.30.0 review, M4: a close (Quit, Quit anyway, a sign-out, the shell's pipe closing) waits for a step open here to
# reach its own end, never past this ceiling. Each step is one bounded file operation (two writes of a few MB, one
# original's removal with its checks, one book's delete loop, one rename): seconds, a minute on a slow share. Past the
# ceiling the step is treated as hung and the close goes on, so an accepted Quit always ends. The shell keeps the same
# bound (desktop/quit-watch.js FILE_CHANGE_BOUND_MS).
FILE_CHANGE_BOUND = 300.0


def wait_closed(deadline, poll=.1):
    """Wait until no step is open, or until time.monotonic() reaches deadline. True when none is open."""
    import time
    while open_sections():
        left = deadline - time.monotonic()
        if left <= 0:
            return False
        time.sleep(min(poll, left))
    return True
