"""0.31.1 (Sergei 2026-11-24): a finished book that cannot be found is removed from the app's records.

"I don't want the book that I deleted from the Approved Books to be anywhere in the app." When the published-book check
cannot find a finished book at its recorded place and a complete search of the output folder finds no file of its name
and none with its recorded file ID (MergeService._relink_found, _remove_missing), the book is removed: catalog only, no file
is touched here. No library or source file is ever touched; the book's own recovery copies and working files are deleted
later by the recovery sweep (Sergei: a removed book leaves nothing behind).

The removal is a tombstone, never a deletion of records: the receipts and the event tables stay immutable (the move and
relocation events refuse UPDATE and DELETE). The job row keeps its manifest, receipt and journal; only its state becomes
'removed'. Every place the page reads leaves it out: the jobs status (AudioJobs.status), the converted and approved
totals and the book list (removed_candidates), the held cleanups and kept files (removed_jobs). Its candidate keeps the
job, so automatic processing never offers it for conversion again, and a file that reappears does not bring it back.
Its recovery copies are released by the recovery sweep (RecoveryRetention.purge, owners of a removed book).

Never removed while the app's own records say why it is not at its path (blocked: Senua M1): a move of it that has not
finished, or a replacement link.

Recoverable by hand, not by the app: deleting the tombstone row and setting the job's state back to 'completed' restores
the book exactly as it was (nothing else was changed).
"""
import datetime
import json

import book_move

STATE = 'removed'
TABLE = ('CREATE TABLE IF NOT EXISTS finished_book_removals(job_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL,'
         ' title TEXT NOT NULL, recorded_path TEXT NOT NULL, removed_utc TEXT NOT NULL, proof TEXT NOT NULL)')
REMOVABLE = ('completed', 'needs attention')  # a finished book: its row has an output receipt
REASON = ('Finished book not found; removed from the list. Library and source files were not touched. The app\'s own recovery'
          ' copies and working files for it are deleted later.')  # Judy's stuck-load spec, 8.2 (Senua M3)


def setup(db):
    db.execute(TABLE)


def _have(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='finished_book_removals'").fetchone() is not None


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def blocked(db, job_id):
    """Why the app's own records say this finished book is not simply gone, or None (Senua M1, Sergei 2026-11-24): a move of
    it that has not finished (the app may have renamed its file and not yet recorded where: 'rename_intent'), or a
    replacement link (the book a newer conversion replaces, or that conversion: both share one candidate, so a tombstone
    would hide both). Read-only; read again inside the removal's own transaction (remove)."""
    if _table(db, 'book_moves') and db.execute('SELECT 1 FROM book_moves WHERE job_id=? AND state NOT IN (%s) LIMIT 1' % ','.join('?' for _ in book_move.TERMINAL),
                                                (job_id, *book_move.TERMINAL)).fetchone():
        return 'a move of it has not finished'
    if _table(db, 'audiobook_replacements') and db.execute('SELECT 1 FROM audiobook_replacements WHERE parent_job_id=? OR replacement_job_id=? LIMIT 1',
                                                            (job_id, job_id)).fetchone():
        return 'it is linked to a replacement'
    return None


def removed_candidates(db):
    """{candidate id} of every removed finished book (the book list and the totals leave them out). Read-only."""
    return {row[0] for row in db.execute('SELECT candidate_id FROM finished_book_removals')} if _have(db) else set()


def removed_jobs(db):
    """{job id} of every removed finished book (held cleanups, kept files, the recovery sweep). Read-only."""
    return {row[0] for row in db.execute('SELECT job_id FROM finished_book_removals')} if _have(db) else set()


def removed(db, job_id):
    """The tombstone of this job, or None. A job is removed only with both its tombstone and the 'removed' state."""
    if not _have(db):
        return None
    row = db.execute('SELECT * FROM finished_book_removals WHERE job_id=?', (job_id,)).fetchone()
    state = db.execute('SELECT state FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()
    return dict(row) if row and state and state[0] == STATE else None


def remove(db, job_id, output, recorded_path, proof):
    """In the caller's write transaction: the tombstone and the 'removed' state, when the job is still this finished book
    (a finished state and the same receipt as when it was found missing) and nothing holds it (blocked). True when it was
    removed now."""
    setup(db)
    row = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()
    if row is None or row['state'] not in REMOVABLE or not row['output'] or json.loads(row['output']) != output:
        return False
    if blocked(db, job_id):
        return False
    manifest = json.loads(row['manifest'])
    title = str((manifest.get('metadata') or {}).get('title') or '')
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.execute('INSERT OR IGNORE INTO finished_book_removals VALUES(?,?,?,?,?,?)',
               (job_id, manifest.get('candidate_id') or '', title, str(recorded_path), now, json.dumps(proof, ensure_ascii=False, sort_keys=True)))
    db.execute("UPDATE audio_jobs SET state=?, stage=?, reason=?, updated=? WHERE job_id=? AND state=?",
               (STATE, STATE, REASON, now, job_id, row['state']))
    return True
