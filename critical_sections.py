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
