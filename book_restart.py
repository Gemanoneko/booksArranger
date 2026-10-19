"""Start over and "Let the app handle it" (Judy's RefusedRetry follow-ups 2-4; Sergei, 2026-10-19).

Start over sets a stuck job aside: the job row, its journal and its working files are kept; the job is only no longer
the book's current job (audio_jobs skips set-aside rows wherever it decides a book's newest job). "Let the app handle
it" discards a book's saved review (its review text and its candidate context: notes, evidence, cover and track
choices) so the automatic pass can research and approve it again. Both leave a "Started over" marker on the book
until automatic processing has queued it.

Everything here is catalog rows inside one caller transaction. No file is opened, moved or deleted: the cover cache,
the sources and every working file stay where they are.
"""
import datetime
import json
import time
from pathlib import Path

SET_ASIDE = ('CREATE TABLE IF NOT EXISTS audio_job_set_aside(job_id TEXT PRIMARY KEY,candidate_id TEXT NOT NULL,'
             'revision INTEGER NOT NULL,kind TEXT NOT NULL,at TEXT NOT NULL)')
MARKERS = ('CREATE TABLE IF NOT EXISTS automatic_restarts(id TEXT PRIMARY KEY,kind TEXT NOT NULL,job_id TEXT,'
           "run_id TEXT,visit TEXT NOT NULL DEFAULT 'this_run',at TEXT NOT NULL)")
MANUAL_DRAFT = 'Manual draft retained'  # the automatic pass's own hold reason for a book with a saved review
KINDS = ('start_over', 'release')
ORDER = {'failed': 0, 'waiting': 1, 'working': 2, 'held': 3}  # Started over filter: the ones that need Sergei first


class Changed(ValueError):
    """The book, its review or its job is not what the press was made on; nothing was changed."""


class Editing(ValueError):
    """An editing lease is active on the book; nothing was changed."""


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def ensure(db):
    db.execute(SET_ASIDE)
    db.execute(MARKERS)


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _columns(db, name):
    return {row[1] for row in db.execute('PRAGMA table_info(' + name + ')')}


def book(db, identity, now=None):
    """Facts about one current book, read-only: the Start over prediction and the release rules. None when the book is
    not current.

    manual_draft mirrors AutomaticProcessing.manual_draft exactly: an editing lease (expires in the future), or a saved
    review whose candidate context at the book's current revision holds neither an automatic approval nor a pending
    one (or marks a manual draft active). saved_review is that second half alone (a lease-only hold ends by itself).
    single_m4b: exactly one included source, an .m4b (the included set as the review page reads it).
    """
    if not _table(db, 'book_groups'):
        return None
    columns = _columns(db, 'book_groups')
    row = db.execute('SELECT * FROM book_groups WHERE id=?', (identity,)).fetchone()
    if row is None or 'superseded' in columns and row['superseded']:
        return None
    row = dict(row)
    review_text = row.get('review') or ''
    try:
        review = json.loads(review_text) if review_text else None
    except (TypeError, ValueError):
        review = None
    try:
        evidence = json.loads(row.get('evidence') or '{}')
    except (TypeError, ValueError):
        evidence = {}
    members = [m['path'] for m in evidence.get('members', []) if isinstance(m, dict) and isinstance(m.get('path'), str)] if isinstance(evidence, dict) else []
    context = {}
    if _table(db, 'candidate_context'):
        saved = db.execute('SELECT revision,data FROM candidate_context WHERE id=?', (identity,)).fetchone()
        if saved and saved[0] == row['revision']:
            try:
                context = json.loads(saved[1])
            except (TypeError, ValueError):
                context = {}
    context = context if isinstance(context, dict) else {}
    from review_backend import member_key
    keys = [member_key(path) for path in members]
    order, included = context.get('track_order', keys), context.get('included', keys)
    if not isinstance(order, list) or not isinstance(included, list) or set(order) != set(keys) or not set(included) <= set(keys):
        included = keys  # the review page's own fallback (CandidateReviewService.enrich)
    chosen = [path for path, key in zip(members, keys) if key in included]
    lease = False
    if _table(db, 'automatic_manual_drafts'):
        lease = db.execute('SELECT 1 FROM automatic_manual_drafts WHERE id=? AND expires>?', (identity, time.time() if now is None else now)).fetchone() is not None
    saved_review = bool(review and not (context.get('automatic_approval') or context.get('automatic_pending'))) or bool(context.get('manual_draft_active'))
    return {'id': identity, 'revision': row['revision'], 'fingerprint': row.get('fingerprint'), 'review_text': review_text,
            'review': bool(review), 'single_m4b': len(chosen) == 1 and Path(chosen[0]).suffix.lower() == '.m4b',
            'lease': lease, 'saved_review': saved_review, 'manual_draft': lease or saved_review}


def release_ok(facts):
    """A saved review that only "Let the app handle it" can release: exactly one included .m4b (a multi-file book can be
    queued by hand), a saved review that holds it, and no editing lease now."""
    return bool(facts and facts['review'] and facts['saved_review'] and facts['single_m4b'] and not facts['lease'])


def current_job(db, identity):
    """The book's newest job that is not set aside, else None."""
    if not _table(db, 'audio_jobs'):
        return None
    aside = ' AND job_id NOT IN (SELECT job_id FROM audio_job_set_aside)' if _table(db, 'audio_job_set_aside') else ''
    found = db.execute("SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=?" + aside +
                       ' ORDER BY created DESC, job_id DESC LIMIT 1', (identity,)).fetchone()
    return found[0] if found else None


def set_aside(db, job_id, identity, revision, kind='start_over'):
    """The job stays in audio_jobs untouched; this row only takes it out of the book's current job.

    The book's older unpublished failures go with it (kind 'history'). They were already history, superseded by this
    newer job (a Retry or Repair child's failed parent, say); left current, the newest of them would become the book's
    job again and the book would be stuck the same way. Their rows, journals and working files are kept too."""
    ensure(db)
    at = stamp()
    db.execute('INSERT INTO audio_job_set_aside VALUES(?,?,?,?,?)', (job_id, identity, revision, kind, at))
    for (older,) in db.execute("SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? AND job_id!=? AND state='needs attention'"
                               " AND output IS NULL AND job_id NOT IN (SELECT job_id FROM audio_job_set_aside)", (identity, job_id)).fetchall():
        db.execute('INSERT INTO audio_job_set_aside VALUES(?,?,?,?,?)', (older, identity, revision, 'history', at))


def discard_review(db, facts):
    """Discard the saved review and its context as read (compare-and-set on revision and review text), and any editing
    lease. The revision moves on, so a view of the old revision is refused. Returns the new revision."""
    superseded = ' AND superseded=0' if 'superseded' in _columns(db, 'book_groups') else ''
    changed = db.execute("UPDATE book_groups SET review='',approved=0,changed=0,revision=revision+1 WHERE id=? AND revision=? AND review=?" + superseded,
                         (facts['id'], facts['revision'], facts['review_text'])).rowcount
    if changed != 1:
        raise Changed('Book changed')
    if _table(db, 'candidate_context'):
        db.execute('DELETE FROM candidate_context WHERE id=?', (facts['id'],))
    if _table(db, 'automatic_manual_drafts'):
        db.execute('DELETE FROM automatic_manual_drafts WHERE id=?', (facts['id'],))
    return facts['revision'] + 1


def reset_automatic(db, identity, revision, fingerprint):
    """The book's automatic record reads Pending at its current revision: no reasons, no retry time, so nothing says
    Queued, Approved or Held for it (Follow-up 2, section 1.1 item 3). Its research history is kept."""
    if not _table(db, 'automatic_candidates'):
        return
    old = db.execute('SELECT * FROM automatic_candidates WHERE id=?', (identity,)).fetchone()
    if old is None:
        return
    try:
        result = json.loads(old['result'] or '{}')
    except (TypeError, ValueError):
        result = {}
    result = result if isinstance(result, dict) else {}
    for key in ('reasons', 'wait', 'job_id', 'job_retry', 'gap_deferrals'):
        result.pop(key, None)
    result['reasons'] = []
    result['restarted_utc'] = stamp()
    db.execute('INSERT OR REPLACE INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',
               (identity, revision, fingerprint, 'Pending', json.dumps(result, ensure_ascii=False), None, old['attempted'], old['matcher_version']))


def mark(db, identity, kind, job_id=None):
    """Start the book's marker (one per book; a new press replaces it)."""
    if kind not in KINDS:
        raise ValueError('Unknown restart kind')
    ensure(db)
    db.execute("INSERT OR REPLACE INTO automatic_restarts VALUES(?,?,?,?,?,?)", (identity, kind, job_id, None, 'this_run', stamp()))


def set_visit(db, identity, visit, run_id):
    """Whether the run that was active at the press will still reach the book ('this_run') or has passed it."""
    if _table(db, 'automatic_restarts'):
        db.execute('UPDATE automatic_restarts SET visit=?,run_id=? WHERE id=?', (visit if visit in ('this_run', 'next_run') else 'this_run', run_id, identity))


def markers(db):
    """{book id: marker row} for every marker. Read-only."""
    if not _table(db, 'automatic_restarts'):
        return {}
    return {row['id']: dict(row) for row in db.execute('SELECT * FROM automatic_restarts')}


def state(marker, job_state, automatic, facts=None, run=None):
    """The marker's state on the book list (Follow-up 3, section 2.2), or None once it ended.

    job_state: the book's current job state as the list shows it ('Queued', 'Creating', 'Audiobook created', 'Output
    needs attention') or None. automatic: the book's automatic record at its current revision, {'state', 'reasons'} or
    None. The marker ends when the new job is created or needs attention; while it is Queued or Creating it reads
    'queued' (the book has left the Started over filter).
    """
    if marker is None:
        return None
    if job_state:
        return {'state': 'queued', 'kind': marker['kind'], 'at': marker['at']} if job_state in ('Queued', 'Creating') else None
    current = automatic.get('state') if isinstance(automatic, dict) else None
    reasons = automatic.get('reasons') or [] if isinstance(automatic, dict) else []
    value = {'state': 'waiting', 'kind': marker['kind'], 'at': marker['at']}
    if current == 'Researching':
        value['state'] = 'working'
    elif current == 'Waiting for source':
        value.update(state='working', source_wait=True)
    elif current == 'Held':
        value['state'] = 'held'
        if MANUAL_DRAFT in reasons:
            value['hold'] = 'manual_draft'
    elif current == 'Needs attention':
        value['state'] = 'failed'
    if value['state'] in ('waiting', 'working') and facts and facts.get('manual_draft'):
        value['expect'] = 'hold'
        value['release_expected'] = bool(facts.get('saved_review') and facts.get('single_m4b') and not facts.get('lease'))
    if marker.get('visit') == 'next_run' and isinstance(run, dict) and run.get('id') == marker.get('run_id') and run.get('state') in ('Running', 'Stopping'):
        value['visit'] = 'next_run'
    return value
