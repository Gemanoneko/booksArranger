"""How far a running press has got, by the thread that runs it (0.30.0, Futaba's QA A).

An Approve of a 300-file book ran for minutes showing only "Saving the approval" with a sliding bar. The press runs on the
action queue's worker thread, and its slow part (checking each source file against its recorded hash) runs on that same
thread, so the step reports its count here and the queue's view of its running action reads it: no argument is threaded
through the call layers between them. A thread that reports nothing has no count, and the row slides as before.
"""
import threading

_LOCK = threading.Lock()
_DONE = {}


def report(done, total, unit='files', step=None):
    """The calling thread's press has done `done` of `total` (whole numbers, 0 <= done <= total). step names the pass when a
    press goes over its files more than once (an Approve: reading, covers, checking, confirming; Futaba's QA A delta, 2),
    so a count that starts again reads as the next step."""
    if type(done) is int and type(total) is int and 0 <= done <= total and total > 0:
        with _LOCK:
            _DONE[threading.get_ident()] = (done, total, unit, step)


def clear(ident=None):
    """Forget the count of a thread (the caller's by default): its press ended."""
    with _LOCK:
        _DONE.pop(threading.get_ident() if ident is None else ident, None)


def read(ident):
    """(done, total, unit, step) the thread last reported, or None."""
    with _LOCK:
        return _DONE.get(ident)
