"""Delete book (Sergei's ruling 23, 2026-10-25; Judy's "Delete book - spec" in Docs/BooksArranger_AttentionTodo_UX_2026-10-24.md).

A book with missing parts or audio the app cannot repair is deleted on Sergei's confirmation: its own audio files are
removed from disk and every record the app holds about it is deleted, so a reacquired copy is found as a new book.
Ruling 23 is his explicit exception to ruling 2 (a source goes only after its result is in Sorted), for these books only.

Guarantees (each refused before the first file is touched, with a typed code; Senua red-teams them):
  - only the book's own catalogued audio files, each inside a configured Audiobooks SOURCE root and never inside the
    configured Sorted (output) folder; covers, text files, other books' files and folders are never touched;
  - no file that any other book, job or reacquire record also holds ('shared');
  - no book with a finished or published audiobook, a replacement lineage or a recorded source cleanup ('sorted');
  - no book being converted, cleaned up or researched right now ('busy'); a changed revision ('changed'); a file list
    that differs from the one confirmed ('files_changed'); an unreachable source root ('offline').
Files go first, one at a time, through the exact-handle disposal source cleanup uses (native_io), with NO recovery
copy (ruling 23: fully removed). A file that fails does not stop the others. The records go last, in one catalog
transaction, and only when every listed file is confirmed gone (a file already absent counts as gone). On any failure
no record is deleted, so the book stays listed and nothing is half-forgotten; a crash between the steps ends the same."""
import json
import os
import stat
from pathlib import Path

from metadata import AUDIO
from native_io import BoundaryError, DirectoryBoundary, FileInUse, VerifiedFile, ordinary
from scanner import connect, inside

CODES = ('changed', 'files_changed', 'shared', 'sorted', 'offline', 'busy', 'refused')
CAUSES = ('in_use', 'denied', 'unreachable', 'other')
BUSY = 'This book is being processed. Nothing was deleted.'  # Judy's "Book is being processed" line
REFUSED = 'Delete was not accepted. Nothing was deleted.'  # Judy's "Any other typed refusal" line
_UNREACHABLE = ('[WinError 53]', '[WinError 51]', '[WinError 59]', '[WinError 64]', '[WinError 67]', '[WinError 121]',
                '[WinError 1222]', '[WinError 1231]', '[WinError 3]')


class DeleteRefused(ValueError):
    """A typed refusal, issued only before any file was touched. code is one of CODES."""
    def __init__(self, code, message, files=None, root=None):
        super().__init__(message)
        self.code, self.files, self.root = code, files or [], root

    def payload(self):
        value = {'code': self.code, 'message': str(self)}
        if self.files:
            value['files'] = self.files
        if self.root:
            value['root'] = self.root
        return value


def _table(db, name):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def _key(path):
    return os.path.normcase(os.path.normpath(str(path)))


def _title(evidence):
    try:
        value = json.loads(evidence) if isinstance(evidence, str) else evidence or {}
    except (TypeError, ValueError):
        value = {}
    return str(value.get('title_clue') or '') if isinstance(value, dict) else ''


def offer(service, row):
    """The typed offer for this row, or None: {'kind': 'files_missing' | 'audio_damaged', 'present': n}. The server alone
    decides (Judy, section 2): a Missing files row, a Need to reacquire row, or a single MP3 whose full audio check
    failed after the app's own repair or Retry ran ("Source audio needs replacement"). Never a duplicate-recording row,
    Files unclear, a book the app can still fix, or a book with a finished audiobook."""
    present = sum(1 for m in row.get('members') or [] if not m.get('missing'))
    entry = service.needs_you().get(row['id']) or {}
    if entry.get('group') == 'files_missing':
        return {'kind': 'files_missing', 'present': present}
    job = _newest_failed_job(service, row['id'])
    if job is None:
        return None
    attention = (service.attention_summary(job_ids=[job['job_id']], retry=False) or {}).get(job['job_id']) or {}
    if attention.get('group') == 'reacquire' or (attention.get('remedy') or {}).get('kind') == 'replace_source':
        return {'kind': 'audio_damaged', 'present': present}
    return None


def _jobs(db, identity):
    if not _table(db, 'audio_jobs'):
        return []
    return [dict(r) for r in db.execute("SELECT * FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? ORDER BY created DESC, job_id DESC", (identity,))]


def _newest_failed_job(service, identity):
    with connect(service.inventory.database) as db:
        jobs = _jobs(db, identity)
    return jobs[0] if jobs and jobs[0]['state'] == 'needs attention' else None


def scanning(service):
    """A library scan is running (the scanner's worker thread is alive)."""
    worker = getattr(service.inventory, 'worker', None)
    return bool(worker is not None and worker.is_alive())


def plan(service, identity, revision):
    """Read-only: what Delete book would remove now. {'files': [{'path', 'size', 'root'}], 'bytes', 'members', 'jobs',
    'kind', 'row'}. Raises DeleteRefused with every refusal check (Judy's preview runs them before the confirm)."""
    if scanning(service):
        # Senua's 0.22.0 final review, N13 (probe P1): a Delete while the scan held the book's queued files let the scan
        # find them gone, and with no catalog row it wrote each back as a new one-file book with a raw "[Errno 2]" error;
        # the scan then ended "completed with errors", which stops an automatic run. Keep, Approve, Scan again and Convert
        # already wait for the scan; Delete now does too, before it reads or touches anything.
        raise DeleteRefused('busy', BUSY)
    try:
        row = service.reviews._row('Audiobooks', identity, revision)
    except ValueError:
        raise DeleteRefused('changed', 'This book changed, so nothing was deleted. Review its details and try again.')
    inventory = service.inventory
    roots = [str(ordinary(r)) for r in inventory.source_roots('Audiobooks')]
    output = getattr(inventory, 'output_root', None)
    output = str(ordinary(output)) if output else None
    members = [m['path'] for m in row.get('members') or []]
    if not members:
        raise DeleteRefused('refused', 'Delete was not accepted. Nothing was deleted.')
    with connect(inventory.database) as db:
        jobs = _jobs(db, identity)
        if any(j['state'] in ('pending', 'running') for j in jobs):
            raise DeleteRefused('busy', BUSY)
        cleaned = set()
        if jobs and _table(db, 'source_cleanup'):
            cleaned = {r[0] for r in db.execute('SELECT job_id FROM source_cleanup WHERE job_id IN (%s)' % ','.join('?' * len(jobs)), [j['job_id'] for j in jobs])}
        for job in jobs:
            try:
                manifest = json.loads(job['manifest'])
            except (TypeError, ValueError):
                manifest = {}
            lineage = isinstance(manifest, dict) and any(k in manifest for k in ('replacement_id', 'replacement_parent_job_id'))
            if job['state'] == 'completed' or job['output'] or job['job_id'] in cleaned or lineage:
                raise DeleteRefused('sorted', 'A finished audiobook of this book is in %s. Nothing was deleted.' % (Path(output).name if output else 'Audiobooks Sorted'))
        if _table(db, 'automatic_candidates'):
            researching = db.execute("SELECT 1 FROM automatic_candidates WHERE id=? AND state='Researching'", (identity,)).fetchone()
            if researching:
                raise DeleteRefused('busy', BUSY)
        # A finished, queued or researched book was refused above with its own line; any other book without the
        # server's offer (one the app can still fix, a duplicate, Files unclear) is refused here.
        kind = offer(service, row)
        if kind is None:
            raise DeleteRefused('refused', 'Delete was not accepted. Nothing was deleted.')
        # Shared: another current book, any other book's job, or another book's reacquire record holds the file.
        keys = {_key(p): p for p in members}
        shared = {}
        if _table(db, 'catalog_group_members'):
            for r in db.execute('SELECT c.path,g.id,g.evidence FROM catalog_group_members c JOIN book_groups g ON g.id=c.group_id WHERE g.superseded=0 AND g.id!=?', (identity,)):
                if _key(r['path']) in keys:
                    shared.setdefault(keys[_key(r['path'])], _title(r['evidence']) or 'another book')
        if _table(db, 'audio_jobs'):
            for r in db.execute("SELECT manifest FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id') IS NOT ?", (identity,)):
                try:
                    manifest = json.loads(r['manifest'])
                except (TypeError, ValueError):
                    continue
                for source in manifest.get('sources') or [] if isinstance(manifest, dict) else []:
                    if isinstance(source, dict) and _key(source.get('path', '')) in keys:
                        shared.setdefault(keys[_key(source['path'])], str((manifest.get('metadata') or {}).get('title') or 'another book'))
        if _table(db, 'reacquire_markers'):
            for r in db.execute('SELECT candidate_id,snapshot FROM reacquire_markers WHERE candidate_id!=?', (identity,)):
                try:
                    snapshot = json.loads(r['snapshot'])
                except (TypeError, ValueError):
                    continue
                for member in snapshot.get('members') or []:
                    if isinstance(member, dict) and _key(member.get('path', '')) in keys:
                        shared.setdefault(keys[_key(member['path'])], _title((snapshot.get('group') or {}).get('evidence')) or 'another book')
    if shared:
        files = [{'path': p, 'other': other} for p, other in sorted(shared.items())]
        if len(files) == 1:
            raise DeleteRefused('shared', '"%s" also belongs to "%s". Nothing was deleted.' % (files[0]['path'], files[0]['other']), files)
        raise DeleteRefused('shared', '%d of this book\'s files also belong to other books. Nothing was deleted.' % len(files), files)
    files, used, guarded = [], set(), set()
    for path in members:
        try:
            p = ordinary(path)
        except BoundaryError:
            raise DeleteRefused('refused', REFUSED)
        root = next((r for r in roots if inside(str(p), r) and _key(p) != _key(r)), None)
        if root is None or output and inside(str(p), output) or p.suffix.lower() not in AUDIO:
            # Never outside a configured source root, never in Sorted, never anything but this book's audio.
            raise DeleteRefused('refused', REFUSED)
        if not os.path.isdir(root):
            raise DeleteRefused('offline', "Can't reach %s. Nothing was deleted." % root, root=root)
        used.add(root)
        try:
            facts = os.lstat(p)
        except FileNotFoundError:
            continue  # already gone: counts as gone
        except OSError:
            raise DeleteRefused('offline', "Can't reach %s. Nothing was deleted." % root, root=root)
        # Senua's 0.22.0 final review, N14 (probe P6): lstat follows a folder junction, so a book folder replaced by a
        # junction into Sorted listed Sorted's same-named files as "will be deleted"; removal then refused each one. The
        # preview now makes removal's own checks first: a single-link ordinary file, and every folder from the drive
        # root down held by the same DirectoryBoundary remove() uses (no junction, symlink or other reparse point).
        if not stat.S_ISREG(facts.st_mode) or getattr(facts, 'st_file_attributes', 0) & 0x400 or facts.st_nlink != 1:
            raise DeleteRefused('refused', REFUSED)
        if _key(p.parent) not in guarded:
            try:
                with DirectoryBoundary(ordinary(root), p.parent):
                    pass
            except (BoundaryError, OSError):
                raise DeleteRefused('refused', REFUSED)
            guarded.add(_key(p.parent))
        files.append({'path': str(p), 'size': facts.st_size, 'root': root})
    return {'files': files, 'bytes': sum(f['size'] for f in files), 'members': members, 'jobs': jobs, 'kind': kind, 'row': row}


def preview(service, identity, revision):
    """POST /api/candidate/delete-preview: {'files': [{'path', 'size'}], 'bytes', 'kind', 'refusal': None | {...}}."""
    try:
        found = plan(service, identity, revision)
    except DeleteRefused as refusal:
        return {'files': [], 'bytes': 0, 'refusal': refusal.payload()}
    return {'files': [{'path': f['path'], 'size': f['size']} for f in found['files']], 'bytes': found['bytes'], 'kind': found['kind'], 'refusal': None}


def _cause(error):
    text = str(error)
    if isinstance(error, FileInUse) or '[WinError 32]' in text or '[WinError 33]' in text:
        return 'in_use'
    if '[WinError 5]' in text or 'Access is denied' in text or isinstance(error, PermissionError):
        return 'denied'
    if any(code in text for code in _UNREACHABLE):
        return 'unreachable'
    return 'other'


def remove(path, root, size):
    """Remove one listed file through its exact handle, inside its source root: None when it is gone, else (cause, raw
    text). The handle is opened for deletion, its single link and size are checked, then it is disposed; a file already
    absent is gone. Never a pathname delete, never a recovery copy."""
    p = ordinary(path)
    if not os.path.lexists(p):
        return None
    try:
        with DirectoryBoundary(ordinary(root), p.parent), VerifiedFile(p, delete=True) as handle:
            facts = handle.facts()
            if facts['links'] != 1 or facts['size'] != size:
                raise BoundaryError('The file changed or has another name since it was listed')
            handle.dispose()
    except (BoundaryError, OSError) as error:
        return _cause(error), str(error)[:500]
    if os.path.lexists(p):
        return 'other', 'The file is still there after its removal'
    return None


def delete(service, identity, revision, paths):
    """POST /api/candidate/delete: {'deleted', 'bytes', 'failed': [{'path', 'cause', 'detail'}], 'forgotten'}. Raises
    DeleteRefused before touching any file. forgotten is True only after the records transaction committed."""
    if not isinstance(paths, list) or len(paths) > 10000 or any(not isinstance(p, str) or not 1 <= len(p) <= 1000 for p in paths):
        raise DeleteRefused('refused', 'Delete was not accepted. Nothing was deleted.')
    with service.operation_lock, service.inventory.group_lock:
        found = plan(service, identity, revision)
        if sorted(_key(f['path']) for f in found['files']) != sorted(_key(p) for p in paths) or len(set(map(_key, paths))) != len(paths):
            raise DeleteRefused('files_changed', "The folder doesn't match the list, so nothing was deleted. Press Delete book to see the current list.")
        deleted, removed_bytes, failed = 0, 0, []
        for item in found['files']:
            outcome = remove(item['path'], item['root'], item['size'])
            if outcome is None:
                deleted += 1
                removed_bytes += item['size']
            else:
                failed.append({'path': item['path'], 'cause': outcome[0], 'detail': outcome[1]})
        forgotten = False
        if not failed:
            # Every listed file is gone, or was already. Leftover working files of its failed jobs go first (the app's
            # own drive); a working folder that cannot be cleared keeps every record, like a source file that fails.
            working = _clear_working(service, found['jobs'])
            if working:
                failed.append(working)
            else:
                still = [m for m in found['members'] if os.path.lexists(m)]
                if still:
                    failed.extend({'path': p, 'cause': 'other', 'detail': 'Still on disk'} for p in still)
                else:
                    forget(service, identity, found['members'], found['jobs'])
                    forgotten = True
    service.after_delete(identity)
    return {'deleted': deleted, 'bytes': removed_bytes, 'failed': failed, 'forgotten': forgotten}


def _clear_working(service, jobs):
    clear = getattr(service, '_clear_working', None)
    for job in jobs:
        if job['state'] != 'needs attention' or job['output']:
            continue
        try:
            state = service._working_state(job, service._working_kind(job), fresh=True) if hasattr(service, '_working_state') else None
        except Exception:
            state = None
        if not state:
            continue
        try:
            if clear is None:
                raise BoundaryError('Working files cannot be cleared')
            clear(job)
        except Exception as error:
            return {'path': 'Working files of an earlier attempt (job %s)' % job['job_id'], 'cause': _cause(error), 'detail': str(error)[:500]}
    return None


# The records of one book, by candidate id, by its jobs and by its file paths. Author rules, settings, other books and
# finished audiobooks (verified_outputs, recovery of other jobs) are never in these lists.
_BY_CANDIDATE = (('book_groups', 'id'), ('candidate_context', 'id'), ('automatic_candidates', 'id'), ('automatic_manual_drafts', 'id'),
                 ('automatic_restarts', 'id'), ('attention_dismissals', 'candidate_id'), ('manual_metadata_sources', 'candidate_id'),
                 ('metadata_choices', 'candidate_id'), ('reacquire_markers', 'candidate_id'))
_BY_JOB = (('audio_jobs', 'job_id'), ('audio_destination_holds', 'job_id'), ('audio_failure_history', 'job_id'), ('audio_job_set_aside', 'job_id'),
           ('audio_repair_admissions', 'parent_job_id'), ('audio_retry_intents', 'parent_job_id'), ('m4b_readmissions', 'parent_job_id'),
           ('inplace_edits', 'job_id'), ('kept_files', 'job_id'), ('recovery_retention', 'job_id'), ('series_backfill', 'job_id'),
           ('source_folder_cleanup_jobs', 'job_id'), ('source_folder_cleanup_directories', 'job_id'), ('working_attempts', 'job_id'),
           ('working_diagnostics', 'job_id'), ('working_files', 'job_id'))
_BY_PATH = ('files', 'part_volumes', 'part_chapters', 'source_retirements', 'scan_outcomes')


def forget(service, identity, members, jobs):
    """One transaction: every record of this book. Its group goes, so its files never regroup as it; its file rows go,
    so a copy reacquired at the same paths is a new book with a new identity (Judy, section 5.6)."""
    job_ids = [j['job_id'] for j in jobs]
    with connect(service.inventory.database) as db:
        db.execute('BEGIN IMMEDIATE')
        have = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        columns = lambda table: {r[1] for r in db.execute('PRAGMA table_info(%s)' % table)}
        for table, column in _BY_CANDIDATE:
            if table in have and column in columns(table):
                db.execute('DELETE FROM %s WHERE %s=?' % (table, column), (identity,))
        if job_ids:
            marks = ','.join('?' * len(job_ids))
            for table, column in _BY_JOB:
                if table in have and column in columns(table):
                    db.execute('DELETE FROM %s WHERE %s IN (%s)' % (table, column, marks), job_ids)
        for table in _BY_PATH:
            if table in have and 'path' in columns(table):
                for path in members:
                    db.execute('DELETE FROM %s WHERE path=?' % table, (path,))
