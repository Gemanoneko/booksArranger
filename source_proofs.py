"""Attempt-scoped source fingerprints (0.21.0): one full hash per source per attempt, then cheap identity.

A conversion attempt still hashes every source in full at its first revision check. A later check in
the SAME attempt skips the re-read only when the source's size, integer-nanosecond modification time,
volume serial and file ID all equal the values observed around that successful full hash. Any
difference re-reads and re-hashes exactly as before, with the same refusals. Outside an attempt
(review, queueing, admission, repair, cleanup) nothing is remembered or skipped.

Deletion and retirement proofs (source cleanup, the in-place pre-write hash and byte proof) never
consult this registry. Accepted residual risk (Sergei, 2026-10-22): a change inside one attempt that
keeps size, modification time and file identity identical is not detected by the skipped checks.
"""
import contextlib
import os
import threading

_local = threading.local()


def facts(stat):
    return (stat.st_size, stat.st_mtime_ns, stat.st_dev, stat.st_ino)


def _key(path, sha256):
    return (os.path.normcase(os.path.abspath(str(path))), sha256)


@contextlib.contextmanager
def attempt(token):
    """Bind fingerprints to one job attempt on this thread; nothing outlives it."""
    previous = getattr(_local, 'scope', None)
    _local.scope = (token, {})
    try:
        yield
    finally:
        _local.scope = previous


def unchanged(path, sha256, stat):
    """True only inside an attempt that fully proved these exact bytes with this exact identity."""
    scope = getattr(_local, 'scope', None)
    return scope is not None and scope[1].get(_key(path, sha256)) == facts(stat)


def remember(path, sha256, before, after=None):
    """Record a successful full hash; an identity that moved during the read is not remembered."""
    scope = getattr(_local, 'scope', None)
    if scope is not None and (after is None or facts(before) == facts(after)):
        scope[1][_key(path, sha256)] = facts(before)


def forget(path):
    """The in-place edit is about to change this file; no fingerprint of it may be reused."""
    scope = getattr(_local, 'scope', None)
    if scope is not None:
        name = os.path.normcase(os.path.abspath(str(path)))
        for key in [key for key in scope[1] if key[0] == name]:
            del scope[1][key]


def stat_of(path):
    """Identity of the opened file, without reading its contents (scanner.fresh_stat semantics)."""
    with open(path, 'rb') as stream:
        return os.fstat(stream.fileno())
