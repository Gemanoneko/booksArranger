"""Rulings 69, 70 and 71h-k (Sergei 2026-10-29): the folder Sergei chooses for a book, through the Windows folder picker.

Only the folder is his (71i): the file name stays the planner's. A choice is saved per book, never learned for other books,
and it outranks every folder the app computes. Choosing is not approving (71j). Before conversion a choice is keyed like
his names, by the book's files (entered_names.book_key); once the book is finished it is keyed by its completed job (the
publication), because its sources may be gone and a regroup may change its files. "Use computed folder" retracts it.

The backend is the only validator: the page never types a path. A chosen folder must be an ordinary existing directory (no
junction or symlink anywhere above it), writable (a zero-byte probe, through a seam in tests), never inside a source
folder or the app's data folder, and its full output path stays within the 240-character limit. Its native identity is
recorded so a folder renamed or replaced later is refused (fails closed), never followed by name.

Rows are append-only in spirit: a new choice retracts the older live ones; nothing is ever deleted."""
import datetime
import json
import ntpath
import os
import uuid

from native_io import AncestorUnavailable, BoundaryError, DirectoryBoundary, ordinary

TABLE = ('CREATE TABLE IF NOT EXISTS destination_overrides(override_id TEXT PRIMARY KEY, book_key TEXT, candidate_id TEXT, job_id TEXT,'
         ' folder TEXT NOT NULL, identity TEXT NOT NULL, actor TEXT NOT NULL, created_utc TEXT NOT NULL, retracted_utc TEXT)')
INDEXES = ('CREATE INDEX IF NOT EXISTS destination_overrides_by_book ON destination_overrides(book_key)',
           'CREATE INDEX IF NOT EXISTS destination_overrides_by_job ON destination_overrides(job_id)')
MAX_PATH = 240
# Typed causes (Judy's 0.23.1 spec, section 18.2); the page maps each to its own sentence.
CAUSES = ('target_exists', 'unavailable', 'not_writable', 'no_space', 'in_use', 'source_missing', 'unsafe', 'partial', 'changed')
PROBE_PREFIX = '.books-arranger-probe-'


class Refused(ValueError):
    """Nothing was saved or moved. cause is one of CAUSES."""

    def __init__(self, cause, message):
        super().__init__(message)
        self.cause = cause
        self.code = cause


MESSAGES = {
    'unavailable': "That folder isn't available. Connect the drive or choose another folder.",
    'not_writable': "The app can't write to that folder. Choose another folder.",
    'no_space': "There isn't enough free space on that drive.",
    'unsafe': 'That folder holds original files the app reads. Choose another folder.',
    'changed': 'This book changed. Review its details and try again.',
}


def refuse(cause, message=None):
    raise Refused(cause, message or MESSAGES.get(cause, 'Folder was not accepted.'))


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def setup(db):
    db.execute(TABLE)
    for statement in INDEXES:
        db.execute(statement)


def _have(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='destination_overrides'").fetchone() is not None


def key(path):
    return ntpath.normcase(ntpath.normpath(str(path)))


def inside(folder, root):
    """True when folder is root or below it (case-insensitive, normalised)."""
    folder, root = key(folder), key(root)
    try:
        return ntpath.commonpath([folder, root]) == root
    except ValueError:
        return False


def default_probe(folder):
    """Create and remove one uniquely named zero-byte file in folder (user-initiated at runtime; tests inject a seam)."""
    path = os.path.join(str(folder), PROBE_PREFIX + uuid.uuid4().hex + '.tmp')
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_BINARY', 0))
    try:
        os.close(descriptor)
    finally:
        os.remove(path)


def validate(folder, *, sources=(), data_dir=None, name='', probe=None, boundary=DirectoryBoundary):
    """(folder as an ordinary absolute path string, identity {'volume', 'high', 'low', 'chain'}) or Refused."""
    if not isinstance(folder, str) or not folder or len(folder) > 1000 or '\x00' in folder:
        refuse('unavailable')
    try:
        path = ordinary(folder)
    except BoundaryError:
        refuse('unavailable')
    text = str(path)
    for source in sources or ():
        if source and inside(text, source):
            refuse('unsafe')
    if data_dir and inside(text, data_dir):
        refuse('unsafe')
    try:
        if not os.path.lexists(text):
            refuse('unavailable')
        if os.path.islink(text) or os.path.isjunction(text):
            refuse('unsafe')
        if not os.path.isdir(text):
            refuse('unavailable')
    except OSError:
        refuse('unavailable')
    if name and len(os.path.join(text, name)) > MAX_PATH:
        refuse('not_writable', "That folder's path is too long for this book's file name. Choose a shorter folder.")
    try:
        with boundary(path.anchor, path) as held:
            chain = [list(item) for item in held.identities]
    except AncestorUnavailable:
        refuse('unavailable')
    except BoundaryError:
        refuse('unsafe', 'That folder is a link or junction. Choose an ordinary folder.')
    except OSError:
        refuse('unavailable')
    try:
        (probe or default_probe)(text)
    except PermissionError:
        refuse('not_writable')
    except OSError as error:
        if getattr(error, 'errno', None) == 28 or getattr(error, 'winerror', None) in (39, 112):
            refuse('no_space')
        refuse('not_writable')
    last = chain[-1]
    return text, {'volume': last[1], 'high': last[2], 'low': last[3], 'chain': chain}


def current_identity(folder, boundary=DirectoryBoundary):
    """The folder's identity now, or None when it is gone or not an ordinary folder (no probe, no write)."""
    try:
        path = ordinary(folder)
        with boundary(path.anchor, path) as held:
            last = held.identities[-1]
            return {'volume': last[1], 'high': last[2], 'low': last[3]}
    except (BoundaryError, OSError, ValueError):
        return None


def same_identity(saved, now):
    return bool(saved and now and all(saved.get(k) == now.get(k) for k in ('volume', 'high', 'low')))


def _row(record):
    if record is None:
        return None
    value = dict(record)
    try:
        value['identity'] = json.loads(value['identity'])
    except (TypeError, ValueError):
        value['identity'] = {}
    return value


def rows(db):
    """Every choice, oldest first (a small table: one row per press)."""
    if not _have(db):
        return []
    return [_row(r) for r in db.execute('SELECT * FROM destination_overrides ORDER BY created_utc, rowid')]


def live_in(records, *, book_key=None, job_id=None):
    """live() over rows already read (the book list reads them once)."""
    if job_id:
        mine = [r for r in records if r.get('job_id') == job_id]
        current = [r for r in mine if r.get('retracted_utc') is None]
        if current:
            return current[-1]
        # A finished book keeps the choice it was converted with until one is made for the publication or it is reset.
        if mine:
            return None
    if book_key:
        current = [r for r in records if r.get('book_key') == book_key and not r.get('job_id') and r.get('retracted_utc') is None]
        return current[-1] if current else None
    return None


def live(db, *, book_key=None, job_id=None):
    """The book's live choice: by its finished job when given (a finished book), else by its files. None when none."""
    if not _have(db):
        return None
    return live_in(rows(db), book_key=book_key, job_id=job_id)


def choose(db, *, folder, identity, book_key=None, candidate_id=None, job_id=None, actor='user'):
    """Save one choice and retract the older live ones for the same book. Returns the new row."""
    setup(db)
    if not (book_key or job_id):
        raise ValueError('A choice needs its book')
    now = stamp()
    _retract(db, book_key=book_key, job_id=job_id, at=now)
    override_id = str(uuid.uuid4())
    db.execute('INSERT INTO destination_overrides(override_id,book_key,candidate_id,job_id,folder,identity,actor,created_utc,retracted_utc) VALUES(?,?,?,?,?,?,?,?,NULL)',
               (override_id, book_key if not job_id else book_key, candidate_id, job_id, folder, json.dumps(identity, sort_keys=True), actor, now))
    return _row(db.execute('SELECT * FROM destination_overrides WHERE override_id=?', (override_id,)).fetchone())


def _retract(db, *, book_key=None, job_id=None, at=None):
    at = at or stamp()
    count = 0
    if job_id:
        count += db.execute('UPDATE destination_overrides SET retracted_utc=? WHERE job_id=? AND retracted_utc IS NULL', (at, job_id)).rowcount
    elif book_key:
        count += db.execute('UPDATE destination_overrides SET retracted_utc=? WHERE book_key=? AND job_id IS NULL AND retracted_utc IS NULL', (at, book_key)).rowcount
    return count


def retract(db, *, book_key=None, job_id=None):
    """Use computed folder: the live choice is retracted (kept as history). For a finished book a retraction row is also
    written so its earlier, pre-conversion choice no longer applies. Returns how many choices it retracted."""
    if not _have(db):
        return 0
    now = stamp()
    count = _retract(db, book_key=book_key, job_id=job_id, at=now)
    if job_id:
        # A marker row: this publication's folder is the computed one again (live() then answers None).
        db.execute('INSERT INTO destination_overrides(override_id,book_key,candidate_id,job_id,folder,identity,actor,created_utc,retracted_utc) VALUES(?,?,?,?,?,?,?,?,?)',
                   (str(uuid.uuid4()), book_key, None, job_id, '', '{}', 'user', now, now))
    return count


def folders(db):
    """Every folder Sergei ever chose (append-only): roots a moved or published book may live in."""
    if not _have(db):
        return ()
    return tuple(sorted({row[0] for row in db.execute("SELECT DISTINCT folder FROM destination_overrides WHERE folder<>''")}, key=str.casefold))


def fact(override):
    """The frozen manifest/metadata-facts form of a live choice (organization.plan reads it)."""
    if not override or not override.get('folder'):
        return None
    identity = override.get('identity') or {}
    return {'id': override['override_id'], 'folder': override['folder'],
            'identity': {k: identity.get(k) for k in ('volume', 'high', 'low')}}


def check_fact(value):
    """The frozen form, validated (organization.plan); None for no choice."""
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - {'id', 'folder', 'identity'}:
        raise ValueError('Chosen destination folder record is malformed')
    folder = value.get('folder')
    if not isinstance(folder, str) or not folder or len(folder) > 1000 or not ntpath.isabs(folder) or '\x00' in folder:
        raise ValueError('Chosen destination folder record is malformed')
    return value
