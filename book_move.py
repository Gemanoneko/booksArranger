"""Moving a finished audiobook to the folder Sergei chose (rulings 69, 71h, 71k; Sergei 2026-10-29).

A move never converts again: no job row, no encoder, no source-cleanup intent. It moves the one current published file.

Location chain. The original receipt (audio_jobs.output) and the offline relocation protocol (publication_locations,
one relocation per publication) stay exactly as they are. A move is a new generation layered on top of them: each row
binds the exact effective location it starts from (from_json) and, once committed, the verified location it ends at
(final_json). PublicationBindings.lookup() follows the chain, so every consumer that already resolves a publication
through the bindings (Delete book, Remove this copy, chapter repair, replacements, the current-audiobook view, Open book
folder, startup and routine verification, source cleanup) follows a move too. A chain that does not link (a move whose
start differs from the location before it) is refused, never guessed: the book then reads as unavailable.

Strategies (one per move, chosen by the native volume of the held file and of the target folder):
  - same volume: a handle-bound no-replace native rename of the exact held file (native_io.rename_no_replace) after a
    full hash on that same deny-writer handle; when Windows refuses that rename as another device (two shares of one NAS
    volume report the same volume serial), nothing was renamed and the move goes on as a copy below;
  - another volume: a copy to an owned temporary in the target folder, flushed, its full SHA-256 and size equal to the
    receipt, a no-replace publication, the location commit, then exact-handle removal of the old file (held deny-writer
    since it was hashed). Any doubt keeps both files and reports 'partial'.

Journal. Every state is written (and committed) before the side effect it announces; events are append-only. A restart
reconciles in the engine (recover()), from what is on disk and the journal, never by refusing to start:
  queued                        -> cancelled (nothing ran)
  rename_intent                 -> renamed and verified: committed then complete; untouched: failed (nothing moved);
                                   renamed but not openable now: left as it is (Unopened raised); other bytes: 'changed'
  copy_intent / copied          -> owned temporary removed; failed (nothing moved)
  publish_intent                -> published and verified: committed, then the old removal below; published but not
                                   openable now: left as it is (Unopened raised); absent or other bytes: temporary removed
  committed / old_removal_intent-> the old file removed once proven to be the same bytes, else 'partial' (both kept)
An OS, catalog or boundary error a step did not type is reconciled the same way in the session (Mover._settle: at once,
then after each pause); so is any failure after a copy is placed in the target folder (Senua 0.24.0 D1, D1r), reported as
"nothing moved" only when the placed file is gone or is not the receipt's bytes. An error that outlasts every pause (the
catalog unwritable, the placed copy still unopenable) raises Unfinished and leaves the move journaled until recover() at
the next start; while no one runs it, the row reads 'unfinished' with why (view(), ruling 73k), never "moving".

After a move the old folder is removed if its listing is empty (71k), then each empty parent up to, never including, the
output folder; never a source or output root, never anything recursive."""
import contextlib
import datetime
import json
import ntpath
import os
import shutil
import sqlite3
import time
import unicodedata
import uuid

from native_io import (NOT_SAME_DEVICE, AncestorUnavailable, BoundaryError, DirectoryBoundary, FileInUse, RenamePostconditionError,
                       RenameRefused, VerifiedFile, ordinary, publish_no_replace, rename_no_replace)

SCHEMA = 'books-book-move-v1'
ENVELOPE = 'books-book-move-envelope-v1'
TABLE = ('CREATE TABLE IF NOT EXISTS book_moves(move_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, kind TEXT NOT NULL, candidate_id TEXT NOT NULL,'
         ' generation INTEGER NOT NULL, state TEXT NOT NULL, strategy TEXT, target_folder TEXT NOT NULL, target_root TEXT NOT NULL,'
         ' target_path TEXT NOT NULL, from_json TEXT NOT NULL, final_json TEXT, temp_path TEXT, cause TEXT, detail TEXT, progress INTEGER,'
         ' override_id TEXT, created_utc TEXT NOT NULL, updated_utc TEXT NOT NULL, UNIQUE(job_id,kind,generation))')
EVENTS = ('CREATE TABLE IF NOT EXISTS book_move_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT, move_id TEXT NOT NULL,'
          ' from_state TEXT, to_state TEXT NOT NULL, proof_json TEXT, created_utc TEXT NOT NULL)')
INDEXES = ('CREATE INDEX IF NOT EXISTS book_moves_by_job ON book_moves(job_id,kind,generation)',
           'CREATE INDEX IF NOT EXISTS book_moves_by_candidate ON book_moves(candidate_id)')
ACTIVE = ('rename_intent', 'copy_intent', 'copied', 'publish_intent', 'committed', 'old_removal_intent')
EFFECTIVE = ('committed', 'old_removal_intent', 'complete', 'partial')
TERMINAL = ('complete', 'partial', 'failed', 'cancelled')
KINDS = ('base', 'replacement')
TEMP_PREFIX = '.books-arranger-move-'
LOCATION_KEYS = ('root', 'final_path', 'sha256', 'size', 'parent_identity', 'identity')


class Refused(ValueError):
    def __init__(self, cause, message):
        super().__init__(message)
        self.cause = cause
        self.code = cause


class Unsettled(Exception):
    """The OS accepted a rename whose postcondition could not be proven: recovery decides from what is on disk."""


class Failed(Exception):
    """A move that stops with nothing moved (or, for 'partial', with both files kept); cause is typed."""

    def __init__(self, cause, detail=''):
        super().__init__(detail or cause or 'Move was not accepted')
        self.cause = cause
        self.detail = detail


class Unopened(ValueError):
    """Ruling 73k: a copy publish_intent already placed in the target folder could not be opened or read to prove it (D1r);
    cause 'renamed' (D1r3): the file a same-volume rename put there. A ValueError, so Mover._settle tries again and
    recover() leaves the move journaled, as for any other error."""

    def __init__(self, error, cause='copy'):
        super().__init__(str(error) or type(error).__name__)
        self.error = error
        self.cause = cause


class Unfinished(Exception):
    """Ruling 73k: a move whose error outlasted every settle attempt. It stays journaled (both files kept) for recover() at
    the next start. cause: 'copy' (the placed copy could not be opened), 'renamed' (D1r3: the renamed file, the only one,
    could not be opened to confirm it) or 'catalog' (its progress could not be saved);
    detail: the last attempt's raw error (Technical details only); move: the journal row as last read, or None; error:
    the error that started the settling."""

    def __init__(self, cause, detail, move=None, error=None):
        super().__init__(detail or cause)
        self.cause = cause
        self.detail = detail
        self.move = move
        self.error = error


# Ruling 73k (Judy): a new choice beside a move that waits for a restart, and Choose folder…'s tooltip, say the same.
UNFINISHED = 'Close and reopen Books Arranger to finish the move. Then you can choose another folder.'


def _absent(path):
    """Senua 0.24.0 D1r2: True only when path provably does not exist: lstat answers ERROR_FILE_NOT_FOUND or
    ERROR_PATH_NOT_FOUND and a folder above it opens (destination_overrides._absent). False when it is there. Any other
    error raises Unopened: os.path.lexists reads every error as absent, so a dropped share hid a placed copy."""
    import destination_overrides
    try:
        os.lstat(str(path))
        return False
    except OSError as error:
        if getattr(error, 'winerror', None) in destination_overrides.NOT_FOUND and destination_overrides._absent(str(path), lambda place: os.stat(place)):
            return True
        raise Unopened(error) from error


def _unfinished_cause(error):
    return getattr(error, 'cause', 'copy') if isinstance(error, Unopened) else 'catalog'


def _raw(error):
    return (str(error) or type(error).__name__)[:500]


class Placed(Exception):
    """Senua 0.24.0 D1: a copy move's file is already in the target folder under its final name, and a step after that
    failed (its re-open was in use, the share dropped). run() settles the move from publish_intent as recovery would
    (Mover._settle), proving the placed file before the old one is removed. While the placed file cannot be opened it is
    tried again after each pause (D1r); if it still cannot, Unfinished ('copy') is raised and the move stays at
    publish_intent for recover() at the next start, both files kept. "Nothing moved" only when the placed file is gone or
    is not the receipt's bytes."""

    def __init__(self, error):
        super().__init__(str(error) or type(error).__name__)
        self.error = error


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def setup(db):
    db.execute(TABLE)
    db.execute(EVENTS)
    for statement in INDEXES:
        db.execute(statement)
    for action in ('UPDATE', 'DELETE'):
        db.execute(f"CREATE TRIGGER IF NOT EXISTS book_move_events_no_{action.lower()} BEFORE {action} ON book_move_events BEGIN SELECT RAISE(ABORT,'Move events are append-only'); END")


def have(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='book_moves'").fetchone() is not None


def key(path):
    return ntpath.normcase(ntpath.normpath(unicodedata.normalize('NFC', str(path))))


def location(value):
    """The location fields of a record, lists for tuples (JSON shape)."""
    found = {k: value[k] for k in LOCATION_KEYS if k in value}
    if 'parent_identity' in found:
        found['parent_identity'] = [list(item) for item in found['parent_identity']]
    if found.get('identity') is not None:
        found['identity'] = list(found['identity'])
    return found


def same_location(a, b):
    """The same published bytes at the same place (path, content and size; native identity when both carry one)."""
    if not a or not b:
        return False
    if key(a.get('final_path', '')) != key(b.get('final_path', '')) or a.get('sha256') != b.get('sha256') or a.get('size') != b.get('size'):
        return False
    if a.get('identity') is not None and b.get('identity') is not None and list(a['identity']) != list(b['identity']):
        return False
    return True


def _row(record):
    if record is None:
        return None
    value = dict(record)
    for name in ('from_json', 'final_json', 'detail'):
        if value.get(name):
            try:
                value[name[:-5] if name.endswith('_json') else name] = json.loads(value[name])
            except (TypeError, ValueError):
                value[name[:-5] if name.endswith('_json') else name] = None
        elif name.endswith('_json'):
            value[name[:-5]] = None
    return value


def _event(db, move_id, before, after, proof=None):
    db.execute('INSERT INTO book_move_events(move_id,from_state,to_state,proof_json,created_utc) VALUES(?,?,?,?,?)',
               (move_id, before, after, json.dumps(proof, ensure_ascii=False, sort_keys=True) if proof is not None else None, stamp()))


def load(db, move_id):
    if not have(db):
        return None
    return _row(db.execute('SELECT * FROM book_moves WHERE move_id=?', (move_id,)).fetchone())


def latest(db, candidate_ids):
    """{candidate id: its newest move} for these books (the row's move line)."""
    if not have(db) or not candidate_ids:
        return {}
    found = {}
    marks = ','.join('?' for _ in candidate_ids)
    for record in db.execute('SELECT * FROM book_moves WHERE candidate_id IN (%s) ORDER BY created_utc, rowid' % marks, tuple(candidate_ids)):
        found[record['candidate_id']] = _row(record)
    return found


def chain(db, job_id, kind, base):
    """(effective location, {'move_id', 'generation'} of the last committed move or None). base: the location the
    receipt and any relocation give. Raises ValueError when the chain does not link (fail closed)."""
    if not have(db):
        return base, None
    rows = [_row(r) for r in db.execute("SELECT * FROM book_moves WHERE job_id=? AND kind=? AND state IN ('committed','old_removal_intent','complete','partial') ORDER BY generation",
                                        (job_id, kind))]
    current = base
    last = None
    for move in rows:
        if not same_location(move['from'], current):
            raise ValueError('Moved audiobook history does not link to its publication')
        final = move['final']
        if not isinstance(final, dict) or not final.get('final_path'):
            raise ValueError('Moved audiobook location is unavailable')
        current = dict(current, **{k: final[k] for k in LOCATION_KEYS if k in final})
        last = {'move_id': move['move_id'], 'generation': move['generation']}
    return current, last


def token(db):
    """What the chain depends on, for display caches (PublicationBindings.lookup_token)."""
    if not have(db):
        return None
    return tuple(db.execute('SELECT count(*),max(updated_utc) FROM book_moves').fetchone())


def apply(db, original, kind, effective, envelope):
    """PublicationBindings.lookup()'s answer with the committed moves applied: (effective record, envelope)."""
    if kind not in KINDS or not have(db):
        return effective, envelope
    moved, last = chain(db, original['job_id'], kind, location(effective))
    if last is None:
        return effective, envelope
    record = dict(effective)
    record.update({k: moved[k] for k in LOCATION_KEYS if k in moved})
    value = {'schema': ENVELOPE, 'generation': 'move-%d' % last['generation'], 'effective_location': location(moved),
             'stage': 'moved', 'outcome': 'moved', 'verified': False,
             'publication_id': (envelope or {}).get('publication_id'), 'relocation': (envelope or {}).get('relocation'),
             'original_receipt': (envelope or {}).get('original_receipt'),
             'book_move': dict(last, base=envelope)}
    return record, value


def split(envelope):
    """(the move part of an envelope or None, the base envelope)."""
    if isinstance(envelope, dict) and envelope.get('schema') == ENVELOPE:
        moved = dict(envelope['book_move'])
        base = moved.pop('base', None)
        return moved, base
    return None, envelope


def current(db, job_id, kind):
    """{'move_id', 'generation'} of the book's last committed move, else None (guard())."""
    if kind not in KINDS or not have(db):
        return None
    record = db.execute("SELECT move_id,generation FROM book_moves WHERE job_id=? AND kind=? AND state IN ('committed','old_removal_intent','complete','partial') ORDER BY generation DESC LIMIT 1",
                        (job_id, kind)).fetchone()
    return {'move_id': record[0], 'generation': record[1]} if record else None


def plan(db, *, job_id, kind, candidate_id, start, folder, root, override_id=None, running=None):
    """Queue one move of the book from its current location (start) into folder. None when it is already there (no-op).
    A queued move of the same book is superseded; a move already running is refused. running(move_id): whether that
    journaled move is running now (None: assume it is); one that is not waits for a restart (ruling 73k: 'unfinished')."""
    setup(db)
    if kind not in KINDS:
        raise Refused('changed', 'This audiobook cannot be moved: it is a chapter update of another file.')
    start = location(start)
    target = os.path.join(os.path.normpath(folder), ntpath.basename(start['final_path']))
    if key(target) == key(start['final_path']):
        return None
    if len(target) > 240:
        raise Refused('not_writable', "That folder's path is too long for this book's file name. Choose a shorter folder.")
    busy = db.execute('SELECT move_id,state FROM book_moves WHERE job_id=? AND kind=? AND state NOT IN (%s)' % ','.join('?' for _ in TERMINAL),
                      (job_id, kind, *TERMINAL)).fetchall()
    for move_id, state in busy:
        if state != 'queued':
            if running is not None and not running(move_id):
                raise Refused('unfinished', UNFINISHED)
            raise Refused('changed', 'This audiobook is being moved now. Choose another folder when it finishes.')
        _set(db, move_id, 'cancelled', detail={'reason': 'superseded'})
    generation = (db.execute('SELECT coalesce(max(generation),0) FROM book_moves WHERE job_id=? AND kind=?', (job_id, kind)).fetchone()[0] or 0) + 1
    move_id = str(uuid.uuid4())
    now = stamp()
    db.execute('INSERT INTO book_moves(move_id,job_id,kind,candidate_id,generation,state,strategy,target_folder,target_root,target_path,from_json,final_json,temp_path,cause,detail,progress,override_id,created_utc,updated_utc)'
               ' VALUES(?,?,?,?,?,?,NULL,?,?,?,?,NULL,NULL,NULL,NULL,NULL,?,?,?)',
               (move_id, job_id, kind, candidate_id, generation, 'queued', os.path.normpath(folder), str(root), target,
                json.dumps(start, ensure_ascii=False, sort_keys=True), override_id, now, now))
    _event(db, move_id, None, 'queued', {'start': start, 'target': target})
    return load(db, move_id)


def _set(db, move_id, state, *, expected=None, strategy=None, final=None, temp=None, cause=None, detail=None, progress=None, proof=None):
    row = db.execute('SELECT state FROM book_moves WHERE move_id=?', (move_id,)).fetchone()
    if row is None:
        raise ValueError('Move unavailable')
    before = row[0]
    if expected is not None and before not in ((expected,) if isinstance(expected, str) else expected):
        raise ValueError('Move state changed')
    fields = {'state': state, 'updated_utc': stamp()}
    if strategy is not None:
        fields['strategy'] = strategy
    if final is not None:
        fields['final_json'] = json.dumps(location(final), ensure_ascii=False, sort_keys=True)
    if temp is not None:
        fields['temp_path'] = temp
    if cause is not None:
        fields['cause'] = cause
    if detail is not None:
        fields['detail'] = json.dumps(detail, ensure_ascii=False, sort_keys=True)
    if progress is not None:
        fields['progress'] = progress
    db.execute('UPDATE book_moves SET ' + ','.join(k + '=?' for k in fields) + ' WHERE move_id=?', (*fields.values(), move_id))
    _event(db, move_id, before, state, proof)


def cancel(db, move_id):
    """A queued move taken back (its queued action was cancelled, or the app closed first): True when it was queued."""
    if not have(db):
        return False
    record = db.execute('SELECT state FROM book_moves WHERE move_id=?', (move_id,)).fetchone()
    if record is None or record[0] != 'queued':
        return False
    _set(db, move_id, 'cancelled', expected='queued')
    return True


def view(move, unfinished=None):
    """The row's move line (Judy 18.1): {state, target, folder, name, old_folder, progress, cause, message} or None.
    message: the engine's own sentence for a failure the page shows as sent ('unsafe' names the source folder).
    unfinished (ruling 73k): {'cause', 'detail'} for a journaled move that is not running (its retries ran out, or recovery
    at start could not finish it). The line is then 'unfinished', its cause 'copy', 'renamed' or 'catalog' (what the page
    words) and its detail the raw error (Technical details only). Without it a journaled move reads 'moving', as before."""
    if not move or move['state'] == 'cancelled':
        return None
    state = {'queued': 'queued', 'complete': 'moved', 'failed': 'failed', 'partial': 'failed'}.get(move['state'], 'moving')
    if state == 'moving' and unfinished:
        state = 'unfinished'
    start = move.get('from') or {}
    cause = (move.get('cause') or ('partial' if move['state'] == 'partial' else None)) if state == 'failed' else None
    if state == 'unfinished':
        cause = unfinished.get('cause') if unfinished.get('cause') in ('copy', 'renamed') else 'catalog'
    detail = move.get('detail') if isinstance(move.get('detail'), dict) else {}
    line = {'state': state, 'target': move['target_path'], 'folder': move['target_folder'], 'name': ntpath.basename(move['target_path']),
            'old_folder': ntpath.dirname(start.get('final_path') or ''), 'progress': move.get('progress') if state == 'moving' else None,
            'cause': cause, 'message': str(detail.get('reason') or '') if cause == 'unsafe' else '',
            'move_id': move['move_id']}
    if state == 'unfinished':
        line['detail'] = str(unfinished.get('detail') or '')[:500]
    return line


def _volume(identities):
    return identities[-1][1] if identities else None


def default_same_volume(old_volume, new_volume):
    return bool(old_volume) and old_volume == new_volume


def _taken(folder, name):
    """A file of that name (case-insensitive, normalised) is already in folder."""
    if os.path.lexists(os.path.join(folder, name)):
        return True
    wanted = key(name)
    try:
        with os.scandir(folder) as entries:
            return any(key(entry.name) == wanted for entry in entries)
    except OSError:
        return False


class Mover:
    """Runs one move at a time with injected policy (MergeService supplies it; tests inject fakes).

    connect(): a catalog connection (context manager, commits on success). resolve(job_id, kind): the publication's
    effective location now, through the bindings (moves included). sources(): source roots (never a target). roots(): the
    configured output root and roots a moved book may live in. same_volume(old, new): the strategy seam. fault(stage): a
    test hook raised at each journal boundary. progress(move_id, percent). remove_folder(folder, root): ruling 24a's plain
    empty-folder removal. output_root: the configured output folder (parents are removed up to it, never it)."""

    def __init__(self, connect, resolve, *, sources=lambda: (), output_root=None, same_volume=default_same_volume, fault=None,
                 progress=None, remove_folder=None, stop=None, protected_roots=lambda: ()):
        self.connect = connect
        self.resolve = resolve
        self.sources = sources
        self.output_root = output_root
        self.same_volume = same_volume
        self.fault = fault or (lambda stage: None)
        self.report = progress or (lambda move_id, percent: None)
        self.remove_folder = remove_folder
        self.stop = stop
        self.protected_roots = protected_roots
        self.unfinished = {}  # recover(): {move_id: {'cause', 'detail'}} for each move it could not finish (ruling 73k)

    # ------------------------------------------------------------------ journal
    def _write(self, move_id, state, **values):
        with self.connect() as db:
            _set(db, move_id, state, **values)

    def _load(self, move_id):
        with self.connect() as db:
            return load(db, move_id)

    def _fail(self, move, cause, detail=''):
        self._write(move['move_id'], 'failed', cause=cause or '', detail={'reason': str(detail)[:500]} if detail else None)
        return self._load(move['move_id'])

    # ------------------------------------------------------------------ run
    def run(self, move_id):
        """Run a queued move. Returns the move row after it (its state says what happened)."""
        move = self._load(move_id)
        if move is None:
            raise ValueError('Move unavailable')
        if move['state'] != 'queued':
            return move
        try:
            try:
                self._run(move)
                return self._load(move_id)  # after the old handle and folder closed (a copy completes there)
            except Unsettled:
                return self.reconcile(self._load(move_id))
            except Failed as failure:
                current = self._load(move_id)
                if current['state'] in ('queued', 'rename_intent', 'copy_intent', 'copied', 'publish_intent'):
                    return self._fail(current, failure.cause, failure.detail)
                if current['state'] in ('committed', 'old_removal_intent'):
                    self._write(move_id, 'partial', cause='partial', detail={'reason': str(failure.detail or failure)[:500]})
                    return self._load(move_id)
                return current
        except (OSError, sqlite3.Error, ValueError) as error:
            return self._settle(move_id, error)
        except Placed as placed:
            return self._settle(move_id, placed.error)

    # Pauses between attempts to end a move after an error (a catalog busy for a moment answers the next one).
    SETTLE_PAUSES = (0, 0.5, 2)

    def _settle(self, move_id, error):
        """Senua 0.24.0 M1: an OS, catalog or boundary error that no step typed (a network error on the temporary, a
        catalog write that failed) ends the move now, never "moving" until the next start. It is reconciled as a restart
        would reconcile it (reconcile(): from the journal and what is on disk): a move that had not committed fails with
        nothing moved, its owned temporary removed and the old file untouched; a committed one finishes, the old file
        removed only once proven to be the published bytes, or both are kept ('partial'). The error is recorded on the
        move. When the catalog stays unwritable, or a copy placed in the target folder stays unopenable (D1r), through every
        attempt, Unfinished is raised (ruling 73k: its cause 'catalog' or 'copy' from the last attempt) and recover() at
        the next start reconciles the journal, as before."""
        reason = ('The move stopped on an unexpected error: ' + (str(error) or type(error).__name__))[:500]
        last, seen = error, None
        for pause in self.SETTLE_PAUSES:
            if pause:
                if self.stop is not None and self.stop.is_set():
                    break
                time.sleep(pause)
            try:
                current = self._load(move_id)
                if current is None:
                    break
                seen = current
                if current['state'] in TERMINAL:
                    return current
                with self.connect() as db:
                    _event(db, move_id, current['state'], current['state'], {'error': reason})
                if current['state'] == 'queued':
                    return self._fail(current, '', reason)
                return self.reconcile(current)
            except (OSError, sqlite3.Error, ValueError, Failed) as attempt:
                last = attempt
                continue
        raise Unfinished(_unfinished_cause(last), _raw(last), seen, error) from error

    def _run(self, move):
        start = move['from']
        target = move['target_path']
        folder = move['target_folder']
        try:
            now = location(self.resolve(move['job_id'], move['kind']))
        except (ValueError, OSError, KeyError) as error:
            raise Failed('source_missing', str(error))
        if not same_location(now, start):
            raise Failed('changed', 'The audiobook is not where this move was planned from')
        import destination_overrides
        holder = next((source for source in self.sources() or () if source and destination_overrides.inside(folder, source)), None)
        if holder:
            raise Failed('unsafe', destination_overrides.UNSAFE_SOURCE.format(place=holder))  # the row shows it (view)
        if not os.path.isdir(folder) and self.output_root and destination_overrides.inside(folder, self.output_root)                 and key(move['target_root']) == key(self.output_root) and key(folder) != key(self.output_root):
            # Use computed folder: the planner's folder inside the output folder is made as a conversion makes it.
            try:
                with DirectoryBoundary(ordinary(self.output_root), ordinary(folder), create=True):
                    pass
            except (BoundaryError, OSError) as error:
                raise Failed('unavailable', str(error))
        if not os.path.isdir(folder):
            raise Failed('unavailable', 'The folder is not available')
        if _taken(folder, ntpath.basename(target)):
            raise Failed('target_exists', 'A file of that name is already in the folder')
        old = ordinary(start['final_path'])
        target_root = ordinary(move['target_root'])
        try:
            with DirectoryBoundary(target_root, ordinary(folder)) as probe:
                new_volume = _volume(probe.identities)
        except (BoundaryError, OSError) as error:
            raise Failed('unavailable', str(error))
        try:
            old_boundary_cm = DirectoryBoundary(ordinary(start['root']), old.parent)
            old_boundary = old_boundary_cm.__enter__()
        except (BoundaryError, OSError) as error:
            raise Failed('source_missing', str(error))
        settled = False
        try:
            try:
                held_cm = VerifiedFile(old, delete=True)
                held = held_cm.__enter__()
            except FileInUse as error:
                raise Failed('in_use', str(error))
            except (BoundaryError, OSError) as error:
                raise Failed('source_missing', str(error))
            try:
                facts = held.facts()
                if facts['links'] != 1 or facts['size'] != start['size']:
                    raise Failed('changed', 'The audiobook changed since it was verified')
                if start.get('identity') is not None and list(facts['identity']) != list(start['identity']):
                    raise Failed('changed', 'The audiobook was replaced since it was verified')
                # A rename into a folder the old file's own ancestry holds (moving up, into an ancestor) cannot share
                # that folder for writing: it is copied, verified and the old file removed instead.
                nested = any(key(item[0]) == key(folder) for item in old_boundary.identities)
                rename = self.same_volume(_volume(old_boundary.identities), new_volume) and not nested
                if self._hash(held, move, start['size'], 0, 100 if rename else 50) != start['sha256']:
                    raise Failed('changed', 'The audiobook bytes differ from its receipt')
                result = (self._rename if rename else self._copy)(move, start, held, facts, old_boundary, target_root)
                settled = True
                return result
            finally:
                held_cm.__exit__(None, None, None)
        finally:
            old_boundary_cm.__exit__(None, None, None)
            if settled:
                self._after_old_closed(move)  # only after a normal end: a fault (a crash) leaves the journal to recovery

    def _hash(self, held, move, size, offset, share):
        import hashlib
        value = hashlib.sha256()
        done = 0
        last = -1
        for block in held.chunks():
            if self.stop is not None and self.stop.is_set():
                raise Failed('', 'Books Arranger is closing')
            value.update(block)
            done += len(block)
            percent = offset + (share * done // size if size else share)
            if percent != last:
                last = percent
                self.report(move['move_id'], percent)
        return value.hexdigest()

    def _rename(self, move, start, held, facts, old_boundary, target_root):
        target = ordinary(move['target_path'])
        self._write(move['move_id'], 'rename_intent', expected='queued', strategy='rename',
                    proof={'old': start, 'old_native': facts, 'target': str(target)})
        self.fault('rename_intent')
        refused = None
        try:
            with DirectoryBoundary(target_root, target.parent, rename_destination=True) as destination:
                try:
                    receipt = rename_no_replace(held, target, old_boundary, destination, expected_identity=facts,
                                                expected_size=start['size'], expected_sha256=start['sha256'])
                except FileExistsError as error:
                    raise Failed('target_exists', str(error))
                except RenamePostconditionError:
                    raise  # the OS accepted the rename: recovery proves what is on disk
                except RenameRefused as error:
                    if error.winerror != NOT_SAME_DEVICE:
                        raise Failed('changed', str(error))
                    refused = str(error)
                except BoundaryError as error:
                    raise Failed('changed', str(error))
                if refused is None:
                    final = dict(start, root=str(target_root), final_path=str(target), parent_identity=[list(i) for i in destination.identities],
                                 identity=list(receipt['identity']))
        except RenamePostconditionError:
            raise Unsettled()
        except AncestorUnavailable as error:
            raise Failed('unavailable', str(error))
        if refused is not None:
            # Senua 0.24.0 M4: the same volume serial on two shares of one NAS volume is not one volume; Windows refused
            # the rename as another device and nothing was renamed (the held file is unchanged). The move goes on as a
            # copy: verified temporary, no-replace publication, location commit, then removal of the proven old file.
            return self._copy(move, start, held, facts, old_boundary, target_root, expected='rename_intent', refused=refused)
        self.fault('renamed')
        self._write(move['move_id'], 'committed', expected='rename_intent', final=final, proof={'rename': receipt})
        self.fault('committed')
        self._write(move['move_id'], 'complete', expected='committed', proof={'outcome': 'moved'})
        return self._load(move['move_id'])

    def _copy(self, move, start, held, facts, old_boundary, target_root, expected='queued', refused=None):
        target = ordinary(move['target_path'])
        temp = target.parent / (TEMP_PREFIX + move['move_id'] + '.partial')
        try:
            free = shutil.disk_usage(str(target.parent)).free
        except OSError as error:
            raise Failed('unavailable', str(error))
        if free < start['size'] + 16 * 1024 * 1024:
            raise Failed('no_space', 'Not enough free space')
        proof = {'old': start, 'old_native': facts, 'temporary': str(temp)}
        if refused is not None:
            proof['rename_refused'] = refused
        self._write(move['move_id'], 'copy_intent', expected=expected, strategy='copy', temp=str(temp), proof=proof)
        self.fault('copy_intent')
        import hashlib
        try:
            with DirectoryBoundary(target_root, target.parent) as destination:
                digest = hashlib.sha256()
                try:
                    descriptor = os.open(str(temp), os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_BINARY', 0))
                except FileExistsError as error:
                    raise Failed('changed', str(error))
                except PermissionError as error:
                    raise Failed('not_writable', str(error))
                done = 0
                try:
                    for block in held.chunks():
                        if self.stop is not None and self.stop.is_set():
                            raise Failed('', 'Books Arranger is closing')
                        os.write(descriptor, block)
                        digest.update(block)
                        done += len(block)
                        self.report(move['move_id'], 50 + (45 * done // start['size'] if start['size'] else 45))
                    os.fsync(descriptor)
                except OSError as error:
                    raise Failed('no_space' if getattr(error, 'errno', None) == 28 or getattr(error, 'winerror', None) in (39, 112) else 'not_writable', str(error))
                finally:
                    os.close(descriptor)
                if digest.hexdigest() != start['sha256'] or done != start['size']:
                    raise Failed('changed', 'The copy differs from the audiobook')
                with VerifiedFile(temp) as written:
                    temp_facts = written.facts()
                    if temp_facts['size'] != start['size'] or written.sha256() != start['sha256']:
                        raise Failed('changed', 'The copy differs from the audiobook')
                self._write(move['move_id'], 'copied', expected='copy_intent', proof={'temporary': str(temp), 'native': temp_facts})
                self.fault('copied')
                self._write(move['move_id'], 'publish_intent', expected='copied', proof={'temporary': str(temp), 'target': str(target)})
                self.fault('publish_intent')
                try:
                    publish_no_replace(temp, target, destination, start['sha256'], start['size'])
                except FileExistsError as error:
                    raise Failed('target_exists', str(error))
                except BoundaryError as error:
                    raise Failed('changed', str(error))
                # The copy is in the target folder now (publish_no_replace returns only after the rename). Any failure
                # from here on is settled from publish_intent (D1), never turned into Failed below.
                try:
                    with VerifiedFile(target) as published:
                        published_facts = published.facts()
                    final = dict(start, root=str(target_root), final_path=str(target), parent_identity=[list(i) for i in destination.identities],
                                 identity=list(published_facts['identity']))
                except Exception as error:
                    raise Placed(error) from error
        except Failed:
            self._discard_temp(temp)
            raise
        except AncestorUnavailable as error:
            self._discard_temp(temp)
            raise Failed('unavailable', str(error))
        except BoundaryError as error:
            self._discard_temp(temp)
            raise Failed('unavailable', str(error))
        self._write(move['move_id'], 'committed', expected='publish_intent', final=final, proof={'published': final})
        self.fault('committed')
        self._write(move['move_id'], 'old_removal_intent', expected='committed', proof={'old': start})
        self.fault('old_removal_intent')
        try:
            held.dispose()  # removed when the held handle closes (_run's finally); proven there
        except BoundaryError as error:
            self._write(move['move_id'], 'partial', expected='old_removal_intent', cause='partial', detail={'reason': str(error)[:500]})
        return self._load(move['move_id'])

    def _after_old_closed(self, move):
        """After the held old handle closed: a copy move whose old file was disposed is complete once it is gone; then
        the old folder is removed if it is empty (71k)."""
        current = self._load(move['move_id'])
        if current is None:
            return
        if current['state'] == 'old_removal_intent':
            old = current['from']['final_path']
            if os.path.lexists(old):
                self._write(move['move_id'], 'partial', expected='old_removal_intent', cause='partial', detail={'reason': 'The old file is still there'})
            else:
                self._write(move['move_id'], 'complete', expected='old_removal_intent', proof={'outcome': 'moved', 'old_absent': True})
            current = self._load(move['move_id'])
        if current['state'] == 'complete':
            removed = self.tidy(current)
            if removed:
                with self.connect() as db:
                    _event(db, move['move_id'], 'complete', 'complete', {'folders_removed': removed})

    def _discard_temp(self, temp):
        """Remove our own temporary (its owned name); never anything else."""
        try:
            if os.path.lexists(str(temp)) and ntpath.basename(str(temp)).startswith(TEMP_PREFIX):
                with VerifiedFile(temp, delete=True) as owned:
                    owned.dispose()
        except (BoundaryError, OSError):
            pass

    # ------------------------------------------------------------------ the old folder (71k)
    def tidy(self, move):
        """Remove the folder the book left if its listing is empty, then each empty parent below the output folder.
        Never a source root, the output root, a drive root or anything recursive. Returns the removed folders."""
        if self.remove_folder is None:
            return []
        old_folder = ntpath.dirname(move['from']['final_path'])
        if key(old_folder) == key(move['target_folder']):
            return []
        protected = {key(r) for r in (self.protected_roots() or ()) if r} | {key(r) for r in (self.sources() or ()) if r}
        if self.output_root:
            protected.add(key(self.output_root))
        removed = []
        folder = old_folder
        while True:
            parent = ntpath.dirname(folder)
            if not parent or key(parent) == key(folder) or key(folder) in protected:
                break
            inside_output = bool(self.output_root) and key(folder).startswith(key(self.output_root).rstrip('\\') + '\\')
            anchor = self.output_root if inside_output else os.path.splitdrive(folder)[0] + '\\'
            if not self.remove_folder(folder, anchor):
                break
            removed.append(folder)
            if not inside_output:
                break  # outside the output folder only the folder the book left is removed
            folder = parent
        return removed

    # ------------------------------------------------------------------ recovery (engine start)
    def recover(self):
        """Reconcile every move a restart interrupted. Returns the moves it touched; self.unfinished says why each move it
        could not finish stays journaled (ruling 73k)."""
        self.unfinished = {}
        with self.connect() as db:
            if not have(db):
                return []
            open_moves = [_row(r) for r in db.execute('SELECT * FROM book_moves WHERE state NOT IN (%s) ORDER BY created_utc' % ','.join('?' for _ in TERMINAL), TERMINAL)]
        done = []
        for move in open_moves:
            try:
                done.append(self.reconcile(move))
            except Exception as error:  # never stops startup; the move stays as it is, the book reads as before
                self.unfinished[move['move_id']] = {'cause': _unfinished_cause(error), 'detail': _raw(error)}
                with self.connect() as db:
                    _event(db, move['move_id'], move['state'], move['state'], {'recovery_error': str(error)[:500]})
        return done

    def reconcile(self, move):
        state = move['state']
        move_id = move['move_id']
        start = move['from']
        target = move['target_path']
        if state == 'queued':
            self._write(move_id, 'cancelled', expected='queued', detail={'reason': 'The app closed before the move ran'})
            return self._load(move_id)
        if state == 'rename_intent':
            old_there, new_there = os.path.lexists(start['final_path']), os.path.lexists(target)
            if old_there and not new_there:
                return self._fail(move, '', 'The move was interrupted before the file moved')
            if not old_there and new_there:
                # Senua 0.24.0 D1r3: the renamed file is the only one; the old name is gone. One that cannot be opened now
                # raises Unopened('renamed'): retried after the settle pauses, then Unfinished, the journal left for recover()
                # at the next start. One that opens with other bytes is 'changed'. Never 'partial': no old file is kept.
                final = self._prove(move, target, placed='renamed')
                if final is None:
                    return self._fail(move, 'changed', 'The renamed audiobook is not the bytes it was')
                self._write(move_id, 'committed', expected='rename_intent', final=final, proof={'recovered': True})
                self._write(move_id, 'complete', expected='committed', proof={'outcome': 'moved', 'recovered': True})
                current = self._load(move_id)
                self.tidy(current)
                return current
            if old_there and new_there:
                return self._fail(move, 'target_exists', 'Another file has that name')
            return self._fail(move, 'source_missing', 'Neither file is there')
        if state in ('copy_intent', 'copied'):
            if move.get('temp_path'):
                self._discard_temp(move['temp_path'])
            return self._fail(move, '', 'The move was interrupted before the file moved')
        if state == 'publish_intent':
            # Senua 0.24.0 D1r: a copy already in the target folder that cannot be opened or read now (in use, the share
            # dropped) raises, so Mover._settle tries again after its pauses, or recover() at the next start; it is never
            # failed as "nothing moved". The move fails only when the target is absent, or opens and is not the same bytes.
            # D1r2: absent means a definite "not found" with its folder answering (_absent); a share that is away raises.
            final = None if _absent(target) else self._prove(move, target, placed='copy')
            if final is None:
                if move.get('temp_path'):
                    self._discard_temp(move['temp_path'])
                return self._fail(move, '', 'The move was interrupted before the file moved')
            self._write(move_id, 'committed', expected='publish_intent', final=final, proof={'recovered': True})
            move = self._load(move_id)
            state = 'committed'
        if state in ('committed', 'old_removal_intent'):
            if state == 'committed':
                self._write(move_id, 'old_removal_intent', expected='committed', proof={'recovered': True})
            if move.get('strategy') == 'rename' or not os.path.lexists(start['final_path']):
                self._write(move_id, 'complete', expected='old_removal_intent', proof={'outcome': 'moved', 'recovered': True})
            else:
                self._remove_old(move)
            current = self._load(move_id)
            if current['state'] == 'complete':
                self.tidy(current)
            return current
        return move

    def _prove(self, move, path, *, placed=None):
        """The verified location of the moved file at path, or None when it is not the receipt's bytes (one link, size and
        full hash equal to the receipt). An error opening or reading it is None too, unless placed: 'copy' (a copy
        publish_intent already put there, Senua 0.24.0 D1r) or 'renamed' (the file a same-volume rename put there, D1r3).
        Then Unopened(placed) is raised, because the file is there but unproven yet."""
        try:
            target = ordinary(path)
            with DirectoryBoundary(ordinary(move['target_root']), target.parent) as boundary, VerifiedFile(target) as file:
                facts = file.facts()
                if facts['links'] != 1 or facts['size'] != move['from']['size'] or file.sha256() != move['from']['sha256']:
                    return None
                return dict(move['from'], root=str(ordinary(move['target_root'])), final_path=str(target),
                            parent_identity=[list(i) for i in boundary.identities], identity=list(facts['identity']))
        except (BoundaryError, OSError, ValueError) as error:
            if placed:
                raise Unopened(error, placed) from error
            return None

    def _remove_old(self, move):
        """Recovery: remove the old copy only when it is still exactly the published bytes; else keep both (partial)."""
        start = move['from']
        old = ordinary(start['final_path'])
        try:
            with DirectoryBoundary(ordinary(start['root']), old.parent), VerifiedFile(old, delete=True) as held:
                facts = held.facts()
                if facts['links'] != 1 or facts['size'] != start['size'] or held.sha256() != start['sha256']:
                    raise Failed('partial', 'The old file changed; both files were kept')
                held.dispose()
        except Failed as failure:
            self._write(move['move_id'], 'partial', expected='old_removal_intent', cause='partial', detail={'reason': failure.detail})
            return
        except (BoundaryError, OSError) as error:
            self._write(move['move_id'], 'partial', expected='old_removal_intent', cause='partial', detail={'reason': str(error)[:500]})
            return
        if os.path.lexists(str(old)):
            self._write(move['move_id'], 'partial', expected='old_removal_intent', cause='partial', detail={'reason': 'The old file is still there'})
        else:
            self._write(move['move_id'], 'complete', expected='old_removal_intent', proof={'outcome': 'moved', 'recovered': True})


def pending(db):
    """Moves a restart left unfinished (recover() reconciles them)."""
    if not have(db):
        return 0
    return db.execute('SELECT count(*) FROM book_moves WHERE state NOT IN (%s)' % ','.join('?' for _ in TERMINAL), TERMINAL).fetchone()[0]
