"""0.29.0 items 1, 3 and 5: one housekeeping check pass over the catalog (Judy's 0.29.0 UX spec, section 0).

Sergei 2026-11-17: "If the folder/file is not available, I probably deleted it. Check on startup and delete from the list."

- Item 1 (list-only): a book every source file of which is gone, in a library root that answers with content, leaves the
  list at once: the pass writes the record Remove from list writes (attention_dismissals) and its own (source_gone, the
  book's fingerprint and file paths). Needs attention skips a book in source_gone in every group, not only Missing files
  (Senua S-M2), while the catalog still says the same: the same fingerprint (no scan since), or, after a scan, the same
  files all marked missing (the scan changes the fingerprint; Futaba M-3: the book came back). Every pass tests the files
  of these books again (their root answering) and lists again any book with a file back, also when the files came back
  unchanged (a Recycle Bin restore, a folder moved back, a short drive drop at startup; Senua D-M1: their fingerprint is
  the recorded one, so the catalog alone cannot tell "still gone" from "back"); a scan that finds a file again does too.
  Listing again drops both records the pass wrote. No file is touched. A book with any audiobook job (queued,
  converting, converted, stopped) is never a candidate: a converted book stays in the converted list. No mass-drop
  guard (Sergei: no).
- Unavailable root: a root that does not answer, or answers with an empty listing (a failed mount until proven otherwise),
  keeps every book and folder under it. The page says so per root; the pass runs for it once it answers again.
- Item 5: the source folders of the books this pass found gone are watched. A watched folder with no audio left loses
  its known safe leftovers (storage_cleanup.SAFE_LEFTOVERS / leftover_verdict) and goes, then any parent left empty, up
  to and never including the library root (Sergei: folders directly inside a library folder go too). Anything else (a
  document, an archive, a subfolder, a link) keeps the folder, silently (Sergei, Q7: no row), and it stays watched, so it
  goes on a later pass once that file is gone. A folder is removed only when an earlier pass saw it audio-free at least
  FOLDER_GRACE_SECONDS before, and never on window focus. Each removed file is recorded first (ruling 77c table).
- Item 3: a book held as Name taken whose destination no longer exists is checked again (its automatic record reads
  Pending, as after Let the app handle it, and the pass takes it again).

Triggers (Judy section 0): start, a finished scan and a drive that answers again run every part, the drive's part for that
root only (Senua S-M3); window focus runs item 3 only (books=False, folders=False; Futaba m-1).

A pass never decides from scan results: each path is tested now, and a root is probed again before any book under it is
dropped (Senua S-m4: a drive that went away during the pass decides nothing).
"""
import datetime
import json
import os
import threading
import time
from pathlib import Path

from scanner import connect

PROBE_SECONDS = 10
FOLDER_GRACE_SECONDS = 600
LISTED = 10  # Details lists at most this many books and folders, then "+ N more"
WATCH_TABLE = ('CREATE TABLE IF NOT EXISTS source_folder_watch(folder TEXT PRIMARY KEY,root TEXT NOT NULL,candidate_id TEXT,'
               'first_free REAL,updated TEXT NOT NULL)')
CHECK_JOB = 'source-check'  # job_id of the leftover rows this pass records in source_folder_removed_files
GONE_TABLE = ('CREATE TABLE IF NOT EXISTS source_gone(candidate_id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,paths TEXT NOT NULL,'
              'at TEXT NOT NULL)')


def _key(path):
    return os.path.normcase(os.path.normpath(str(path)))


def _inside(path, root):
    path, root = _key(path), _key(root)
    return path != root and path.startswith(root.rstrip('\\/') + os.sep)


def probe(root, timeout=PROBE_SECONDS):
    """{'path', 'available', 'empty'}: the root answered (its listing worked) within timeout, and whether it was empty. A
    drive that hangs is unavailable; its listing thread is left to finish on its own."""
    found = {}

    def look():
        try:
            with os.scandir(root) as listing:
                found['empty'] = next(listing, None) is None
            found['ok'] = True
        except OSError:
            found['ok'] = False

    worker = threading.Thread(target=look, name='books-root-probe', daemon=True)
    worker.start()
    worker.join(timeout)
    available = found.get('ok') is True
    return {'path': str(root), 'available': available, 'empty': bool(available and found.get('empty'))}


def probe_roots(roots, timeout=PROBE_SECONDS):
    """Every root at once, so one slow drive costs one timeout, not one per root."""
    results = [None] * len(roots)

    def one(index, root):
        results[index] = probe(root, timeout)

    threads = [threading.Thread(target=one, args=(i, r), daemon=True, name='books-root-probes') for i, r in enumerate(roots)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout + 1)
    return [result or {'path': str(root), 'available': False, 'empty': False} for result, root in zip(results, roots)]


def answers(root_state):
    return bool(root_state and root_state['available'] and not root_state['empty'])


def _tables(db):
    return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _path_keys(paths):
    return sorted({_key(p) for p in paths})


def still_gone(db, have=None):
    """{candidate id} of the current books a pass found gone that the catalog still shows as gone: the same fingerprint as
    when the pass saw it (no scan since), or every file of the book marked missing by a scan, the same files as then.
    MergeService._todo skips these in every group (Senua S-M2), and a later pass does not report them again (Futaba M-3).
    Read-only."""
    have = _tables(db) if have is None else have
    if 'source_gone' not in have or 'book_groups' not in have:
        return set()
    found = set()
    for r in db.execute('SELECT s.candidate_id,s.paths,CASE WHEN g.fingerprint=s.fingerprint THEN NULL ELSE g.evidence END AS changed '
                        'FROM source_gone s JOIN book_groups g ON g.id=s.candidate_id WHERE g.superseded=0'):
        if r['changed'] is None:
            found.add(r['candidate_id'])
            continue
        try:
            members = json.loads(r['changed'] or '{}').get('members') or []
            recorded = json.loads(r['paths'])
        except (TypeError, ValueError, AttributeError):
            continue
        paths = [m.get('path') for m in members if isinstance(m, dict) and m.get('path')]
        if paths and len(paths) == len(members) and all(m.get('missing') is True for m in members) and _path_keys(paths) == recorded:
            found.add(r['candidate_id'])
    return found


def _forget(db, ids):
    """The book is listed again: its source_gone record goes, and so does the Remove-from-list record the pass wrote with
    it (same book, the fingerprint the record keeps). Left behind, that record hid the book again once its files hashed
    to that fingerprint again (Senua D-M1)."""
    have = _tables(db)
    if 'source_gone' not in have:
        return
    for identity in ids:
        row = db.execute('SELECT fingerprint FROM source_gone WHERE candidate_id=?', (identity,)).fetchone()
        if row is None:
            continue
        if 'attention_dismissals' in have:
            db.execute('DELETE FROM attention_dismissals WHERE candidate_id=? AND fingerprint=?', (identity, row[0]))
        db.execute('DELETE FROM source_gone WHERE candidate_id=?', (identity,))


def hidden(db, have=None):
    """{candidate id} the check pass took off the list that the catalog still shows as gone (still_gone) and that have no
    audiobook job: All candidates and the candidate count leave them out as Needs attention does (Sergei, Futaba M-5;
    list-only). A book with any job, a converted one among them, is never hidden. Read-only."""
    have = _tables(db) if have is None else have
    gone = still_gone(db, have)
    if gone and 'audio_jobs' in have:
        gone -= {r[0] for r in db.execute("SELECT DISTINCT json_extract(manifest,'$.candidate_id') FROM audio_jobs")}
    return gone


def _books(database, roots):
    """[{id, revision, fingerprint, root, title, paths}] of every current book under these roots, with the set of books
    that have an audiobook job, the (candidate, fingerprint) pairs already off the list, and the books an earlier pass
    found gone that are still gone (still_gone). A source_gone record that no longer applies (a scan found the files
    again) is dropped here with its Remove-from-list record (_forget), so neither hides the book later."""
    with connect(database) as db:
        have = _tables(db)
        if 'book_groups' not in have:
            return [], set(), set(), set()
        jobs = {r[0] for r in db.execute("SELECT DISTINCT json_extract(manifest,'$.candidate_id') FROM audio_jobs")} if 'audio_jobs' in have else set()
        gone = still_gone(db, have)
        if 'source_gone' in have:
            stale = [r[0] for r in db.execute('SELECT candidate_id FROM source_gone') if r[0] not in gone]
            if stale:
                _forget(db, stale)
        dismissed = {(r[0], r[1]) for r in db.execute('SELECT candidate_id,fingerprint FROM attention_dismissals')} if 'attention_dismissals' in have else set()
        rows = db.execute('SELECT id,revision,fingerprint,root,scope,evidence FROM book_groups WHERE superseded=0').fetchall()
    keys = {_key(root): str(root) for root in roots}
    books = []
    for row in rows:
        root = keys.get(_key(row['root']))
        if root is None:
            continue
        try:
            evidence = json.loads(row['evidence'] or '{}')
        except (TypeError, ValueError):
            continue
        paths = [str(m.get('path')) for m in evidence.get('members') or [] if isinstance(m, dict) and m.get('path')]
        if not paths or not all(_inside(p, root) for p in paths):
            continue  # only a book whose every file lies under its library root is ever decided
        title = str(evidence.get('title_clue') or '').strip() or Path(paths[0]).parent.name
        books.append({'id': row['id'], 'revision': row['revision'], 'fingerprint': row['fingerprint'], 'root': root, 'title': title, 'paths': paths})
    return books, jobs, dismissed, gone


def _gone(paths):
    """True only when every source file of the book is absent now (its folder may still hold leftovers)."""
    folders = {os.path.dirname(p) for p in paths}
    if not any(os.path.isdir(folder) for folder in folders):
        return True
    return not any(os.path.lexists(p) for p in paths)


def _dismiss(database, book):
    with connect(database) as db:
        db.execute('CREATE TABLE IF NOT EXISTS attention_dismissals(candidate_id TEXT NOT NULL,fingerprint TEXT NOT NULL,dismissed_utc TEXT NOT NULL,PRIMARY KEY(candidate_id,fingerprint))')
        db.execute('INSERT OR IGNORE INTO attention_dismissals VALUES(?,?,?)', (book['id'], book['fingerprint'], _stamp()))
        db.execute(GONE_TABLE)
        db.execute('INSERT OR REPLACE INTO source_gone VALUES(?,?,?,?)', (book['id'], book['fingerprint'], json.dumps(_path_keys(book['paths']), ensure_ascii=False), _stamp()))


def _stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _watch(database, folders):
    with connect(database) as db:
        db.execute(WATCH_TABLE)
        for folder, root, candidate in folders:
            db.execute('INSERT OR IGNORE INTO source_folder_watch(folder,root,candidate_id,first_free,updated) VALUES(?,?,?,NULL,?)',
                       (folder, root, candidate, _stamp()))


def _watched(database):
    with connect(database) as db:
        db.execute(WATCH_TABLE)
        return [dict(r) for r in db.execute('SELECT folder,root,candidate_id,first_free FROM source_folder_watch ORDER BY folder')]


def _set_watch(database, folder, first_free=None, drop=False):
    with connect(database) as db:
        if drop:
            db.execute('DELETE FROM source_folder_watch WHERE folder=?', (folder,))
        else:
            db.execute('UPDATE source_folder_watch SET first_free=?,updated=? WHERE folder=?', (first_free, _stamp(), folder))


def folder_verdict(folder):
    """(leftovers, reason): the folder's entries when every one is a known safe leftover (reason None), else the reason it
    is kept ('audio' when audio is in it). None for a folder whose listing fails (never deleted, never reported)."""
    from storage_cleanup import leftover_verdict
    leftovers = []
    try:
        with os.scandir(folder) as listing:
            for entry in listing:
                reason = leftover_verdict(entry)
                if reason:
                    return [], 'audio' if reason.startswith('Audio files remain') else reason
                stat = entry.stat(follow_symlinks=False)
                leftovers.append({'path': entry.path, 'name': entry.name, 'size': stat.st_size, 'modified_ns': str(stat.st_mtime_ns)})
    except OSError:
        return None
    return leftovers, None


def remove_leftover(path, root, size):
    """One safe leftover through its exact handle, inside the library root (book_delete.remove's checks). On a network
    drive such as Z:, where the hardened local disposition refuses, the pre-0.28 exact-handle method source cleanup uses
    there (Sergei, 2026-11-16) removes it after the same checks again. None when it is gone, else the reason."""
    from native_io import BoundaryError, DirectoryBoundary, VerifiedFile, ordinary
    p = ordinary(path)
    if not os.path.lexists(p):
        return None

    def again(handle):
        facts = handle.facts()
        if facts['links'] != 1 or facts['size'] != size:
            raise BoundaryError('The file changed or has another name since it was listed')

    try:
        with DirectoryBoundary(ordinary(root), p.parent), VerifiedFile(p, delete=True) as handle:
            again(handle)
            handle.dispose(remote_legacy=again)
    except (BoundaryError, OSError) as error:
        return str(error)[:500]
    return 'The file is still there after its removal' if os.path.lexists(p) else None


def _record(database, folder, candidate, item, state, detail=''):
    from storage_cleanup import REMOVED_FILES_TABLE
    with connect(database) as db:
        db.execute(REMOVED_FILES_TABLE)
        if state == 'removing':
            cursor = db.execute('INSERT INTO source_folder_removed_files(job_id,candidate_id,folder,path,size,modified_ns,state,detail,at,updated) VALUES(?,?,?,?,?,?,?,?,?,?)',
                                (CHECK_JOB, candidate, folder, item['path'], item['size'], item['modified_ns'], state, detail, _stamp(), _stamp()))
            return cursor.lastrowid
        db.execute('UPDATE source_folder_removed_files SET state=?,detail=?,updated=? WHERE id=?', (state, detail, _stamp(), item))


def _identity(folder):
    """(volume, file id, type) of the folder itself, or None when it cannot be read."""
    import stat
    try:
        facts = os.lstat(folder)
    except OSError:
        return None
    return facts.st_dev, facts.st_ino, stat.S_IFMT(facts.st_mode)


_OWNERSHIP = {}


def _held(database, folder, candidate, leftovers):
    """Senua S-m1: the guards the reviewed folder cleanup (storage_cleanup, ruling 74e) applies before a leftover goes, as a
    reason to keep the folder, else None: more entries than its LEFTOVER_LIMIT, a retained recovery's sources or stage in or
    under the folder (producer_recovery.protected_dependency), and a leftover another current book, an unfinished job (its
    sources or reviewed cover) or a reacquire record names (cleanup_ownership). An unreadable catalog keeps the folder."""
    from storage_cleanup import StorageCleanup
    if len(leftovers) > StorageCleanup.LEFTOVER_LIMIT:
        return 'Folder holds too many entries to clear; retained'
    try:
        from cleanup_ownership import OwnershipIndex
        from producer_recovery import protected_dependency
        with connect(database) as db:
            if protected_dependency(db, [folder]):
                return 'Isolated old files and source dependencies are retained'
            # One index per catalog for every pass: it rebuilds only when that catalog's owners change.
            index = _OWNERSHIP.setdefault(_key(database), OwnershipIndex())
            held = index.held(db, _tables(db), None, candidate, {os.path.normcase(str(item['path'])) for item in leftovers})
    except Exception:
        return "Ownership of the folder's files could not be read; retained"
    return 'Another book or job uses a file in this folder; retained' if held else None


def _remove_folder(database, watched, leftovers):
    """The folder's safe leftovers, each recorded first, then the folder and each parent left empty, never the root. The
    reviewed guards (_held) come first; the folder must still be the one listed (_identity) when it goes. (gone, names
    of the leftover files removed): a folder that stayed may still have lost files (Senua S-m7)."""
    from book_delete import _remove_folder as rmdir_if_empty
    folder, root = watched['folder'], watched['root']
    identity = _identity(folder)
    if identity is None or _held(database, folder, watched['candidate_id'], leftovers):
        return False, []
    removed = []
    for item in leftovers:
        # Senua D-m1: the guards again just before each file goes, as the reviewed cleanup does (storage_cleanup, per item):
        # an Approve that names a leftover after the check above keeps it, and the folder.
        if _held(database, folder, watched['candidate_id'], [item]):
            return False, removed
        row = _record(database, folder, watched['candidate_id'], item, 'removing')
        failed = remove_leftover(item['path'], root, item['size'])
        _record(database, folder, watched['candidate_id'], row, 'not_removed' if failed else 'removed', failed or '')
        if failed:
            return False, removed
        removed.append(item['name'])
    if _identity(folder) != identity or not rmdir_if_empty(folder, root):
        return False, removed
    parent = os.path.dirname(folder)
    while _inside(parent, root) and rmdir_if_empty(parent, root):
        parent = os.path.dirname(parent)
    return True, removed


def run(merge, *, roots=None, folders=True, books=True, progress=None, now=None, stop=None, on_phase=None):
    """One pass. roots: the library roots to check (default: every Audiobooks source root). books=False: item 1 does not
    run and no root is probed (window focus, Futaba m-1). folders=False: never delete a folder (window focus). Returns the
    report the page shows: roots, books removed from the list, folders deleted, Name-taken rows checked again."""
    inventory = merge.inventory
    database = inventory.database
    now = time.time() if now is None else now
    report = {'roots': [], 'removed': [], 'returned': [], 'folders': [], 'files': [], 'cleared': []}
    if not books:
        report['cleared'] = recheck_rows(merge, [], {})
        return report
    every = list(inventory.source_roots('Audiobooks')) if hasattr(inventory, 'source_roots') else [inventory.roots['Audiobooks']]
    chosen = [r for r in every if roots is None or _key(r) in {_key(x) for x in roots}]
    states = {_key(s['path']): s for s in probe_roots(chosen)}
    listed, jobs, dismissed, gone = _books(database, chosen)
    # Senua D-M1: the books an earlier pass took off are tested again, their root answering; any with a file back is listed
    # again. Files that came back unchanged hash to the recorded fingerprint, so nothing else would ever release them. A
    # file must be seen to exist: a path that cannot be read now keeps the book off (the safe direction).
    back = []
    for book in listed:
        if stop is not None and stop.is_set():
            break
        if book['id'] in gone and answers(states.get(_key(book['root']))) and not _gone(book['paths']):
            back.append(book)
    if back:
        with connect(database) as db:
            _forget(db, [book['id'] for book in back])
        gone -= {book['id'] for book in back}
        dismissed -= {(book['id'], book['fingerprint']) for book in back}
        report['returned'] = [{'id': book['id'], 'title': book['title']} for book in back]
    listed = [b for b in listed if b['id'] not in gone]  # already off the list: never reported twice (Futaba M-3)
    counts = {}
    for book in listed:
        if (book['id'], book['fingerprint']) not in dismissed:
            counts[_key(book['root'])] = counts.get(_key(book['root']), 0) + 1
    for root in chosen:
        state = dict(states[_key(root)])
        state['books'] = counts.get(_key(root), 0)
        report['roots'].append(state)
    candidates = [b for b in listed if b['id'] not in jobs and (b['id'], b['fingerprint']) not in dismissed and answers(states.get(_key(b['root'])))]
    found = []
    for index, book in enumerate(candidates):
        if stop is not None and stop.is_set():
            break
        if progress is not None:
            progress(index, len(candidates))
        if _gone(book['paths']):
            found.append(book)
    if progress is not None:
        progress(len(candidates), len(candidates))
    if found:
        # Senua S-m4: a drive that stopped answering during the pass makes every later book look gone. Its root is probed
        # again; a root that does not answer now decides nothing (its books stay, its state says so).
        _probe_again({b['root'] for b in found}, states, report)
        gone_folders = []
        for book in found:
            if not answers(states.get(_key(book['root']))):
                continue
            _dismiss(database, book)
            report['removed'].append({'id': book['id'], 'title': book['title'], 'path': os.path.dirname(book['paths'][0])})
            for folder in sorted({os.path.dirname(p) for p in book['paths']}):
                if _inside(folder, book['root']) and os.path.isdir(folder):
                    gone_folders.append((folder, book['root'], book['id']))
        if gone_folders:
            _watch(database, gone_folders)
    if report['removed'] or report['returned']:
        merge.__dict__.pop('_needs_cache', None)
    if folders:
        if on_phase is not None:
            on_phase('folders')  # the jobs panel's "Removing source folders" row (Judy section 7)
        vanished = []
        for watched in _watched(database):
            if stop is not None and stop.is_set():
                break
            if not answers(states.get(_key(watched['root']))):
                continue  # its root is not checked now or does not answer: nothing is decided
            if not os.path.isdir(watched['folder']):
                vanished.append(watched)  # dropped below, once its root still answers
                continue
            verdict = folder_verdict(watched['folder'])
            if verdict is None:
                continue  # its listing failed: kept, not reported (the drive notice covers it)
            leftovers, reason = verdict
            if reason == 'audio':
                _set_watch(database, watched['folder'], drop=True)  # audio is back: the book is listed again by a scan
                continue
            if reason:
                _set_watch(database, watched['folder'], first_free=None)  # kept by another file; watched for when it goes
                continue
            if watched['first_free'] is None or now - watched['first_free'] < FOLDER_GRACE_SECONDS:
                if watched['first_free'] is None:
                    _set_watch(database, watched['folder'], first_free=now)
                continue
            went, removed = _remove_folder(database, watched, leftovers)
            if went:
                _set_watch(database, watched['folder'], drop=True)
                report['folders'].append({'path': watched['folder'], 'files': [item['name'] for item in leftovers]})
            elif removed:
                report['files'].append({'path': watched['folder'], 'files': removed})  # the folder stayed; these files went
        if vanished:
            # Senua D-m4: a folder that looks gone because its drive left after the probe would never be watched again (its
            # book is already recorded) and its leftovers would stay. Its root is probed again first, as for books (S-m4);
            # a root that does not answer now keeps every watch under it.
            _probe_again({w['root'] for w in vanished}, states, report)
            for watched in vanished:
                if answers(states.get(_key(watched['root']))):
                    _set_watch(database, watched['folder'], drop=True)
    report['cleared'] = recheck_rows(merge, chosen, states)
    return report


def _probe_again(roots, states, report):
    """The roots probed once more; a root that does not answer now is recorded so in states and the report's roots."""
    for key, state in {_key(s['path']): s for s in probe_roots(sorted(roots))}.items():
        if not answers(state):
            states[key] = state
            for entry in report['roots']:
                if _key(entry['path']) == key:
                    entry.update(available=state['available'], empty=state['empty'])


def recheck_rows(merge, roots, states):
    """Item 3: Name taken rows whose destination is free again are checked again. [{id, title, cause}].
    0.31.0 (Judy's 0.31.0 spec 4.2): so is a row held because another book would get its name (identity_hold
    same_destination, listed under Name taken) once no other book plans that name any more; it leaves the list by the
    same rule and strip line instead of waiting for automatic processing's own retry timer."""
    database = merge.inventory.database
    with connect(database) as db:
        have = _tables(db)
        if 'automatic_candidates' not in have or 'book_groups' not in have:
            return []
        held = db.execute("SELECT c.id,c.result,g.revision,g.fingerprint FROM automatic_candidates c JOIN book_groups g ON g.id=c.id "
                          "WHERE c.state='Held' AND g.superseded=0 AND c.fingerprint=g.fingerprint").fetchall()
    cleared = []
    for row in held:
        try:
            recorded = json.loads(row['result'] or '{}')
            reasons = recorded.get('reasons') or []
            hold = recorded.get('identity_hold')
        except (TypeError, ValueError, AttributeError):
            continue
        clash = isinstance(hold, dict) and hold.get('kind') == 'same_destination'
        if not clash and not any(isinstance(r, str) and 'already exists at this path' in r for r in reasons):
            continue
        try:
            preview = merge.approval_preview(row['id'], row['revision'], names={})
        except (ValueError, OSError, KeyError):
            continue  # the book changed or cannot be previewed now: it keeps its row
        destination = preview.get('absolute') or ''
        # A name another book still plans, or a book waiting to convert still has, is not free (destination_clash).
        if preview.get('taken') or preview.get('shared') or not destination or os.path.lexists(destination):
            continue
        if not os.path.isdir(os.path.dirname(destination)) and not answers(_output_state(merge)):
            continue  # the output drive does not answer: a missing file there proves nothing
        if _check_again(merge, row['id'], row['revision'], row['fingerprint']):
            cleared.append({'id': row['id'], 'title': preview.get('title') or '', 'cause': 'name_taken'})
    if cleared:
        merge.__dict__.pop('_needs_cache', None)
    return cleared


def _output_state(merge):
    root = getattr(merge.inventory, 'output_root', None)
    return probe(root) if root else None


def _check_again(merge, identity, revision, fingerprint):
    import book_restart
    from sqlite_retry import transaction

    def write(db):
        facts = book_restart.book(db, identity)
        if not facts or facts['revision'] != revision or facts['fingerprint'] != fingerprint or facts['lease']:
            raise book_restart.Changed('Book changed')
        if book_restart.current_job(db, identity) is not None:
            raise book_restart.Changed('Book has a job')
        book_restart.reset_automatic(db, identity, revision, fingerprint)

    try:
        transaction(merge.inventory.database, write)
    except (book_restart.Changed, book_restart.Editing):
        return False
    automatic = getattr(merge, 'automatic', None)
    if automatic is not None and hasattr(automatic, 'requeue'):
        try:
            automatic.requeue(identity)
        except Exception:
            pass
    return True


def summary(report):
    """The page's view of one pass: per-root states, the removed books and deleted folders (Details: at most LISTED each,
    then how many more), and the rows checked again."""
    removed, folders = report.get('removed') or [], report.get('folders') or []
    # files_removed: leftover files removed from folders that then stayed (Senua S-m7): the line never says "No files were
    # touched" while it is above 0.
    return {'roots': report.get('roots') or [], 'removed': len(removed), 'removed_list': removed[:LISTED], 'removed_more': max(0, len(removed) - LISTED),
            'folders': len(folders), 'folder_list': folders[:LISTED], 'folders_more': max(0, len(folders) - LISTED),
            'files_removed': sum(len(item.get('files') or []) for item in report.get('files') or []),
            'cleared': report.get('cleared') or [], 'at': time.time()}
