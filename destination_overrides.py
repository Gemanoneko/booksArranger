"""Rulings 69, 70 and 71h-k (Sergei 2026-10-29): the folder Sergei chooses for a book, through the Windows folder picker.

Only the folder is his (71i): the file name stays the planner's. A choice is saved per book, never learned for other books,
and it outranks every folder the app computes. Choosing is not approving (71j). Before conversion a choice is keyed like
his names, by the book's files (entered_names.book_key); once the book is finished it is keyed by its completed job (the
publication), because its sources may be gone and a regroup may change its files. "Use computed folder" retracts it.

The backend is the only validator: the page never types a path. A chosen folder must be an ordinary existing directory (no
junction or symlink anywhere above it), writable (a zero-byte probe, through a seam in tests), never inside a source
folder or the app's data folder, and its full output path stays within the 240-character limit. Its native identity is
recorded so a folder renamed or replaced later is refused (fails closed), never followed by name.

"Inside a source folder" is decided by where the folders really are, not by how their paths are spelled (Senua 0.24.0
M2): a folder picked through Network under the NAS share's UNC name and the same folder under its mapped drive letter are
one place. Every folder from the chosen one up to its drive or share is compared, by native identity (volume serial and
file index), with each source folder and the data folder, opened with every link followed. When that cannot be told (a
source folder that is away, or a share that gives no file index) the choice is refused with the reason, never allowed.

Rows are append-only in spirit: a new choice retracts the older live ones; nothing is ever deleted."""
import ctypes
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
# Typed causes (Judy's 0.23.1 spec, section 18.2); the page maps each to its own sentence. 'unchecked' (M2: a source or
# data folder whose place can't be told now) has none of its own: the page shows the engine's sentence, which names it.
CAUSES = ('target_exists', 'unavailable', 'not_writable', 'no_space', 'in_use', 'source_missing', 'unsafe', 'partial', 'changed', 'unchecked')
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


NOT_FOUND = (2, 3)  # ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND
UNCHECKED_AWAY = "The app can't check whether that folder is inside {place}: it isn't available now. Connect it and try again."
UNCHECKED_INDEX = "The app can't check whether that folder is inside {place}: that drive doesn't report folder identities. Choose a folder on another drive."


def resolved_identity(path):
    """(volume serial, index high, index low) of the folder path names now, with every link and mapping followed: where
    it really is, however its path is spelled. Opens it for attributes only (no sharing conflict, nothing written).
    Raises OSError (winerror set) when it can't be opened."""
    from native_io import FileInfo, kernel
    handle = kernel.CreateFileW(str(path), 0x80, 7, None, 3, 0x02000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = FileInfo()
        if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        return info.volume, info.index_high, info.index_low
    finally:
        kernel.CloseHandle(handle)


def _network_drive(drive):
    """A drive letter Windows knows as a network drive, connected or remembered while away."""
    try:
        if ctypes.windll.kernel32.GetDriveTypeW(drive + '\\') == 4:  # DRIVE_REMOTE
            return True
        size = ctypes.c_ulong(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        return ctypes.windll.mpr.WNetGetConnectionW(drive, buffer, ctypes.byref(size)) in (0, 1201)  # connected, remembered
    except (OSError, AttributeError):
        return True  # unknown: treated as away, so the choice is refused rather than allowed


def _absent(place, resolve):
    """True when place provably does not exist, so nothing can be inside it: a folder above it opens and the rest is not
    there, or it is on a drive letter that is not there and is no network drive (an away network drive is not absent)."""
    current = ntpath.normpath(str(place))
    while True:
        parent = ntpath.dirname(current)
        if parent == current:
            drive = ntpath.splitdrive(current)[0]
            return len(drive) == 2 and drive[1] == ':' and not _network_drive(drive)
        try:
            resolve(parent)
            return True
        except OSError as error:
            if getattr(error, 'winerror', None) not in NOT_FOUND:
                return False
        current = parent


def _inside_by_identity(chain, places, resolve):
    """Senua 0.24.0 M2: refuse when a folder of the chosen folder's chain (itself and every folder above it, opened without
    following links) is one of places (source folders, the data folder) by native identity. A place that can't be
    resolved, or a match that can't be trusted (no file index on that volume), refuses with the reason."""
    held = [(item[1], item[2], item[3]) for item in chain]
    for place in places:
        if not place:
            continue
        try:
            found = resolve(place)
        except OSError as error:
            if getattr(error, 'winerror', None) in NOT_FOUND and _absent(place, resolve):
                continue
            refuse('unchecked', UNCHECKED_AWAY.format(place=place))
        volume, high, low = found
        found = (volume, high, low)
        if not volume or not (high or low):
            # No usable identity for the place: only a folder on another volume is provably elsewhere.
            if not volume or any(item[0] == volume for item in held):
                refuse('unchecked', UNCHECKED_INDEX.format(place=place))
            continue
        for item in held:
            if item[0] != volume:
                continue
            if not (item[1] or item[2]):
                refuse('unchecked', UNCHECKED_INDEX.format(place=place))
            if item == found:
                refuse('unsafe')


def default_probe(folder):
    """Create and remove one uniquely named zero-byte file in folder (user-initiated at runtime; tests inject a seam)."""
    path = os.path.join(str(folder), PROBE_PREFIX + uuid.uuid4().hex + '.tmp')
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_BINARY', 0))
    try:
        os.close(descriptor)
    finally:
        os.remove(path)


def validate(folder, *, sources=(), data_dir=None, name='', probe=None, boundary=DirectoryBoundary, resolve=resolved_identity):
    """(folder as an ordinary absolute path string, identity {'volume', 'high', 'low', 'chain'}) or Refused. resolve: where
    a source or the data folder really is (resolved_identity; a seam in tests)."""
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
    # Before the probe writes anything: a source or the data folder under another spelling (Senua 0.24.0 M2).
    _inside_by_identity(chain, [*(sources or ()), data_dir], resolve)
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
