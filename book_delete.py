"""Delete book and Remove this copy (Sergei's rulings 23-26, 2026-10-25; Judy's "Delete book - spec" and "Delete book
update and Remove this copy - spec" in Docs/BooksArranger_AttentionTodo_UX_2026-10-24.md).

Delete book (mode 'delete'): a book with missing parts or audio the app cannot repair is deleted on Sergei's confirmation,
so a reacquired copy is found as a new book. It removes:
  1. the book's own catalogued audio files;
  2. the other files of its folder (cover, text, anything not audio) only when the folder holds no other book (ruling 24);
  3. the app's own working files for its stopped jobs, the copies of its originals included even when the originals are
     already gone and they are the last copy of its audio (ruling 26: this explicit action only);
  4. each folder this press leaves empty, up to but never a folder directly inside a source folder (ruling 24);
and then every record the app holds about it. Ruling 23 is his explicit exception to ruling 2 for these books only.

Remove this copy (mode 'copy', ruling 25): a book whose files the app has proven are an exact copy of an audiobook it
already arranged in Sorted. The proof is checked again in the preview and once more right before the first file goes:
the audiobook is where the app put it with its recorded size and checksum, and every file of the copy matches, in order,
a source the audiobook was arranged from. Items 1, 2 and 4 as above (Judy's default under ruling 24; the copy has no
job, so no working files), then every record of the copy. The audiobook is held open (no write or delete sharing) while
the copy's files go.

Guarantees (each refused before the first file is touched, with a typed code; Senua red-teams them):
  - only this book's or copy's own files: catalogued audio, plus non-audio files of a folder no other book uses and no
    other book holds; every path inside a configured Audiobooks source root and never inside the configured Sorted
    folder; no junction, symlink or other reparse point from the drive root down, no file with a second name;
  - no file that any other book, job or reacquire record also holds ('shared'; history of a gone book does not count);
  - Delete: no book with a finished or published audiobook, a replacement lineage or a recorded source cleanup
    ('sorted'); leftover working files only when the app can prove each is its own ('refused' otherwise);
  - Remove this copy: the audiobook missing ('sorted_missing') or changed ('sorted_changed'), a copy file that no longer
    matches ('not_identical'), a listed file that is the audiobook's own file ('refused');
  - nothing while a library scan runs, a job or research runs on it ('busy'); a changed revision ('changed'); a list
    that differs from the one confirmed, files or folders ('files_changed'); an unreachable root ('offline').
Files go one at a time through the exact-handle disposal source cleanup uses (native_io), with NO recovery copy; working
files through the working lifecycle's exact-handle discard. A file that fails does not stop the others. Records go last,
in one catalog transaction, only when every listed file is confirmed gone; on any failure no record is deleted, so the
book stays listed and nothing is half-forgotten. A folder is housekeeping: one that cannot be removed is reported and
never keeps the book listed. Ruling 24a (Sergei 2026-10-25, "Allow"): for these two explicit actions only, a folder left
empty is removed with a plain, non-recursive directory removal (rmdir: it fails unless the folder is empty), also on
NTFS and network drives such as Z:, where the app's exact-handle empty-folder disposition refuses (a late directory
stream could be lost: Docs/BooksArranger_EmptyFolders_Safety_v0.7.0_2026-10-10.md). Every other path, source folder
cleanup and Clear working files included, keeps that refusal: nothing here changes native_io."""
import contextlib
import critical_sections
import datetime
import json
import os
import re
import stat
import threading
from pathlib import Path

from metadata import AUDIO
from native_io import BoundaryError, DirectoryBoundary, FileInUse, VerifiedFile, ordinary
from scanner import connect, inside

CODES = ('changed', 'files_changed', 'shared', 'sorted', 'offline', 'busy', 'refused', 'sorted_missing', 'sorted_changed', 'not_identical',
         'link', 'working', 'is_sorted', 'no_files', 'has_job', 'not_offered', 'outside', 'second_name', 'invalid')
# S6 (ruling 35's refusal texts; Sergei 2026-10-26): eight safety refusals said only "Delete was not accepted. Nothing was
# deleted." Each now names its cause (provisional copy, sent to Judy). They stay refusals: each guards what a delete reaches.
WHY = {'link': "A folder on the way to these files is a link or a junction, so the app can't prove what deleting would reach. Nothing was deleted.",
       'working': "The app's working folder for this book holds something it didn't make (a link or an unknown item), so it can't list what to delete. Nothing was deleted.",
       'is_sorted': 'A listed file is the finished audiobook in Audiobooks Sorted itself. Nothing was deleted.',
       'no_files': 'This book has no files left in the catalog, so there is nothing to delete.',
       'has_job': "This copy has an audiobook job of its own, so it isn't a spare copy. Nothing was deleted.",
       'not_offered': {'delete': "Delete book isn't offered for this book any more: the app can still fix it. Nothing was deleted. Check its row.",
                       'copy': "This book is no longer a proven copy of a finished audiobook. Nothing was deleted. Check its row."},
       'outside': "A listed file isn't an audio file in your library folders, or it's in Audiobooks Sorted. Nothing was deleted.",
       'second_name': "A file of this book is a link or has a second name on disk (a hard link), so deleting it wouldn't remove it safely. Nothing was deleted.",
       'invalid': 'The delete request was incomplete. Nothing was deleted. Reload the page and try again.'}


def refused(code, mode='delete'):
    """The typed refusal for one of WHY's causes."""
    text = WHY[code]
    return DeleteRefused(code, text[mode] if isinstance(text, dict) else text)
CAUSES = ('in_use', 'denied', 'unreachable', 'other')
MODES = ('delete', 'copy')
BUSY = 'This book is being processed. Nothing was deleted.'  # Judy's "Book is being processed" line
REFUSED = 'Delete was not accepted. Nothing was deleted.'  # Judy's "Any other typed refusal" line
CHANGED = 'This book changed, so nothing was deleted. Review its details and try again.'
WORKING = "The app's working files"  # the failed working files' "path" (Judy's update spec 2.3)
IDENTICAL = 'Identical verified recording already arranged'  # merge_service._recording_review's reasons
POSSIBLE = 'Possible duplicate recording'
_TEXT = {'delete': {'refused': REFUSED, 'files_changed': "The folder doesn't match the list, so nothing was deleted. Press Delete book to see the current list."},
         'copy': {'refused': 'Remove was not accepted. Nothing was deleted.', 'files_changed': "The folder doesn't match the list, so nothing was deleted. Press Remove this copy to see the current list."}}
_UNREACHABLE = ('[WinError 53]', '[WinError 51]', '[WinError 59]', '[WinError 64]', '[WinError 67]', '[WinError 121]',
                '[WinError 1222]', '[WinError 1231]', '[WinError 3]')
_SNAPSHOT = re.compile(r'source(\d{5})\.[^.\\/]+')
# Senua's 0.22.0 review, N18: "the folder holds no other book" counts audio in any format the app might not read, not
# only the formats it converts (metadata.AUDIO): a recording beside the book in .ape or .wv is another book's, not a
# file of this one.
SOUND = AUDIO | {'.ape', '.wv', '.mka', '.mp4', '.m4p', '.m4r', '.mp2', '.mpc', '.tta', '.tak', '.ofr', '.shn', '.ac3', '.dts',
                 '.aif', '.aiff', '.aifc', '.alac', '.amr', '.awb', '.caf', '.oga', '.spx', '.ra', '.rm', '.ram', '.dsf', '.dff',
                 '.webm', '.mkv', '.3gp', '.3ga'}
_WALK = 2000  # entries read below one book folder before it counts as holding something else


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


def _sorted_name(output):
    return Path(output).name if output else 'Audiobooks Sorted'


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


def duplicate(entry):
    """'verified' or 'possible' for a duplicate-recording row (needs_you entry), else None: the server's own reasons."""
    reasons = [str(r) for r in (entry or {}).get('reasons') or []]
    if any(r.startswith(IDENTICAL) for r in reasons):
        return 'verified'
    if any(r.startswith(POSSIBLE) for r in reasons):
        return 'possible'
    return None


def _sorted_record(service, output):
    """(effective record, its final path) of an arranged audiobook, through the publication bindings (a relocated
    output resolves to where it is now); (None, None) when it cannot be resolved."""
    bindings = getattr(service, 'publication_bindings', None)
    try:
        lease = bindings.protect(output) if bindings else contextlib.nullcontext((output, None))
        with lease as (effective, _envelope):
            return dict(effective), str(effective['final_path'])
    except Exception:
        return None, None


def copy_source(service, row, exists=True):
    """The audiobook this book is a verified copy of, from the app's own records, else None (Judy's update spec 3.1): the
    row is a "Needs you" book whose recording review is identical verified (every file matches, in order, a source of
    one audiobook) with no missing file, and that audiobook's job is completed, passed its output check and its file is
    in Sorted. {'job', 'output', 'record', 'final'}. A cheap check (one stat); plan() proves it in full. exists=False (the
    press): the file's presence is left to the proof, so a missing audiobook is refused as such ('sorted_missing')."""
    entry = service.needs_you().get(row['id']) or {}
    if entry.get('group') != 'other' or duplicate(entry) != 'verified':
        return None
    members = row.get('members') or []
    if not members or any(m.get('missing') for m in members):
        return None
    try:
        review = service.reviews._context(row).get('duplicate_review') or {}
    except Exception:
        return None
    if review.get('state') != 'verified_identical' or review.get('blocking'):
        return None
    related = sorted({r for r in review.get('related_ids') or [] if isinstance(r, str)})[:50]
    if not related:
        return None
    with connect(service.inventory.database) as db:  # only the related jobs: a page read, never every job
        rows = [dict(r) for r in db.execute("SELECT job_id,state,manifest,output FROM audio_jobs WHERE state='completed' AND job_id IN (%s) ORDER BY job_id" % ','.join('?' * len(related)), related)]
    for job in rows:
        try:
            job['manifest'], job['output'] = json.loads(job['manifest']), json.loads(job['output'] or '{}')
        except (TypeError, ValueError):
            continue
        output = job['output'] if isinstance(job['output'], dict) else {}
        sources = (job['manifest'] if isinstance(job['manifest'], dict) else {}).get('sources') or []
        if (output.get('validation') or {}).get('passed') is not True or len(sources) != len(members):
            continue
        if any(not isinstance(s, dict) or s.get('size') != m.get('size') for s, m in zip(sources, members)):
            continue
        record, final = _sorted_record(service, output)
        if record and (not exists or os.path.isfile(final)):
            return {'job': job, 'output': output, 'record': record, 'final': final}
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


def _history(job, manifest, current):
    """True for another book's job that is only history: its book is gone (no current group has its id) and the job never
    produced anything (stopped, no output, no replacement lineage). A queued, running or finished job, a job with a
    replacement lineage, and any job of a book that is still listed keep counting as sharing."""
    if job['state'] != 'needs attention' or job['output']:
        return False
    if any(k in manifest for k in ('replacement_id', 'replacement_parent_job_id')):
        return False
    return manifest.get('candidate_id') not in current


class _Holders:
    """Every path another book holds now, {key: title}, and the folders holding one: another current group's members,
    another book's job (its sources and cover; history of a gone book aside, N16), another book's reacquire record (an
    archived one of a gone book aside, N16). Titles of groups are read only for the paths asked about. folders: the
    folders where another book holds audio (a cover another book's job used stays by itself, ruling 24)."""
    def __init__(self, db, identity, current):
        self.db, self.groups, self.titles, covers = db, {}, {}, set()
        if _table(db, 'catalog_group_members'):
            for r in db.execute('SELECT c.path,c.group_id FROM catalog_group_members c JOIN book_groups g ON g.id=c.group_id WHERE g.superseded=0 AND g.id!=?', (identity,)):
                self.groups.setdefault(_key(r['path']), r['group_id'])
        if _table(db, 'audio_jobs'):
            for r in db.execute("SELECT state,output,manifest FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id') IS NOT ?", (identity,)):
                try:
                    manifest = json.loads(r['manifest'])
                except (TypeError, ValueError):
                    continue
                if not isinstance(manifest, dict) or _history(r, manifest, current):
                    continue
                title = str((manifest.get('metadata') or {}).get('title') or 'another book')
                for path in (s.get('path', '') for s in manifest.get('sources') or [] if isinstance(s, dict)):
                    if path:
                        self.titles.setdefault(_key(path), title)
                cover = manifest['cover'].get('path', '') if isinstance(manifest.get('cover'), dict) else ''
                if cover and _key(cover) not in self.titles:
                    self.titles[_key(cover)] = title
                    covers.add(_key(cover))
        if _table(db, 'reacquire_markers'):
            for r in db.execute('SELECT candidate_id,state,snapshot FROM reacquire_markers WHERE candidate_id!=?', (identity,)):
                if r['state'] == 'archived' and r['candidate_id'] not in current:
                    continue
                try:
                    snapshot = json.loads(r['snapshot'])
                except (TypeError, ValueError):
                    continue
                title = _title((snapshot.get('group') or {}).get('evidence')) or 'another book'
                for member in snapshot.get('members') or []:
                    if isinstance(member, dict) and member.get('path'):
                        self.titles.setdefault(_key(member['path']), title)
        self.folders = {os.path.dirname(k) for k in (*self.groups, *self.titles) if k not in covers}

    def __contains__(self, key):
        return key in self.groups or key in self.titles

    def title(self, key):
        if key in self.groups:
            row = self.db.execute('SELECT evidence FROM book_groups WHERE id=?', (self.groups[key],)).fetchone()
            return (_title(row['evidence']) if row else '') or 'another book'
        return self.titles[key]


def _guard(root, folder, guarded, text):
    """Every folder from the drive root down to folder, held by the DirectoryBoundary remove() uses: no junction, symlink
    or other reparse point (Senua's N14). Once per folder."""
    if _key(folder) in guarded:
        return
    try:
        with DirectoryBoundary(ordinary(root), ordinary(folder)):
            pass
    except (BoundaryError, OSError):
        raise refused('link')
    guarded.add(_key(folder))


def _below(entries, member_keys):
    """True when a subfolder of the folder listed as entries holds audio (SOUND) that is not this book's, or cannot be
    read through: every ordinary subfolder, down, never through a link or junction. Bounded: past _WALK entries the
    folder counts as holding something else (its files stay)."""
    pending, seen = [e.path for e in entries if e.is_dir(follow_symlinks=False) and not os.path.isjunction(e.path)], 0
    while pending:
        try:
            with os.scandir(pending.pop()) as listing:
                for entry in listing:
                    seen += 1
                    if seen > _WALK:
                        return True
                    if entry.is_dir(follow_symlinks=False):
                        if not os.path.isjunction(entry.path):
                            pending.append(entry.path)
                    elif Path(entry.name).suffix.lower() in SOUND and _key(entry.path) not in member_keys:
                        return True
        except OSError:
            return True
    return False


def _others(members, roots, output, holders, guarded, text):
    """Ruling 24: the other files of the book's own folders (cover, text, anything not audio), only when the folder holds
    no other book: no audio file on disk that is not this book's, in the folder or any subfolder, in any format (SOUND),
    and nothing another book holds in it or below it (a group member, a job's source or cover, a reacquire record;
    Senua's N18). One that another book holds stays, and so does anything the app cannot place: a subfolder, a link, a
    file with a second name. ([other files], stay count, [(folder, root)])."""
    member_keys = {_key(m) for m in members}
    others, stay, folders = [], 0, []
    for folder in sorted({_key(Path(m).parent): str(Path(m).parent) for m in members}.values()):
        try:
            f = ordinary(folder)
        except BoundaryError:
            raise refused('link')
        root = next((r for r in roots if inside(str(f), r) and _key(f) != _key(r)), None)
        if root is None or output and inside(str(f), output) or not os.path.isdir(f):
            continue  # a source folder itself is no book's folder; a folder already gone has nothing left
        _guard(root, f, guarded, text)
        folders.append((str(f), root))
        try:
            with os.scandir(f) as listing:
                entries = list(listing)
        except OSError:
            raise DeleteRefused('offline', "Can't reach %s. Nothing was deleted." % root, root=root)
        inner = _key(f) + os.sep
        foreign = (_key(f) in holders.folders or any(h.startswith(inner) for h in holders.folders)
                   or any(_key(e.path) not in member_keys and Path(e.name).suffix.lower() in SOUND for e in entries) or _below(entries, member_keys))
        for entry in entries:
            key = _key(entry.path)
            if key in member_keys:
                continue
            if foreign or key in holders or entry.is_symlink() or os.path.isjunction(entry.path) or not entry.is_file(follow_symlinks=False):
                stay += 1
                continue
            try:
                p = ordinary(entry.path)
                facts = os.lstat(p)
            except FileNotFoundError:
                continue
            except (BoundaryError, OSError):
                stay += 1
                continue
            if not stat.S_ISREG(facts.st_mode) or getattr(facts, 'st_file_attributes', 0) & 0x400 or facts.st_nlink != 1:
                stay += 1
                continue
            others.append({'path': str(p), 'size': facts.st_size, 'root': root, 'kind': 'other'})
    return others, stay, folders


def _working(service, jobs, text):
    """Ruling 26: every working file of the book's stopped jobs on the app's own drive, through the working lifecycle's
    discard in dry run (the checks the delete makes, nothing removed). A file the app cannot prove is its own refuses
    the press now (Senua's N14 rule). [{'path', 'size', 'kind', 'job_id', 'attempt_id', 'original'}]."""
    working = getattr(service, 'working', None)
    found = []
    for job in jobs:
        if job['state'] != 'needs attention' or job['output']:
            continue
        try:
            listing, _marker = service._working_listing(job['job_id'])  # a link, junction or unknown item: ValueError
            attempts = {name for name, _files in listing}
            with connect(service.inventory.database) as db:
                if _table(db, 'working_attempts'):
                    attempts |= {r[0] for r in db.execute('SELECT attempt_id FROM working_attempts WHERE job_id=?', (job['job_id'],))}
            if not attempts:
                continue
            if working is None or not hasattr(working, 'discard'):
                raise BoundaryError('Working files cannot be removed here')
            sources = (json.loads(job['manifest']) or {}).get('sources') or []
            for attempt in sorted(attempts):
                for path, size in working.discard(job['job_id'], attempt, dry_run=True):
                    match = _SNAPSHOT.fullmatch(Path(path).name)
                    original = sources[int(match.group(1))].get('path') if match and int(match.group(1)) < len(sources) else None
                    found.append({'path': path, 'size': size, 'kind': 'working', 'job_id': job['job_id'], 'attempt_id': attempt, 'original': original})
        except DeleteRefused:
            raise
        except Exception:
            raise refused('working')
    return found


def _folders(book_folders, files, output):
    """Ruling 24: the folders this press leaves empty: a book folder all of whose entries are listed files, then each
    parent all of whose entries are listed files or such folders, up to but never a folder directly inside a source
    folder, never a source folder, never one in Sorted. A folder already empty is not touched. Only an ordinary folder
    (no junction, symlink or reparse point, from the drive root down) is listed (see _removable). Deepest first:
    [(folder, root)]."""
    listed = {_key(f['path']) for f in files if f['kind'] != 'working'}
    planned, out = set(), []
    for folder, root in sorted(book_folders, key=lambda item: -len(Path(item[0]).parts)):
        current = folder
        while _key(current) not in planned:
            try:
                deep = len(Path(current).relative_to(Path(root)).parts) >= 2
            except ValueError:
                deep = False
            if not deep or output and inside(current, output):
                break
            try:
                with os.scandir(current) as listing:
                    names = [_key(e.path) for e in listing]
            except OSError:
                break
            if not names or any(n not in listed and n not in planned for n in names) or not _removable(current, root):
                break
            planned.add(_key(current))
            out.append((current, root))
            current = str(Path(current).parent)
    return out


def _removable(folder, root):
    """An ordinary folder: it and every folder from the drive root down to it held by DirectoryBoundary (no junction,
    symlink or other reparse point). Ruling 24a: no filesystem capability is required."""
    try:
        with DirectoryBoundary(ordinary(root), ordinary(folder)):
            return True
    except (BoundaryError, OSError):
        return False


def _empty(folder):
    """The folder's listing shows nothing: no file, subfolder or link (ruling 24a's first condition)."""
    with os.scandir(folder) as listing:
        return next(listing, None) is None


def _remove_folder(folder, root):
    """Ruling 24a: remove one listed folder if it is empty now; True when it is gone. Its ancestors are held (no junction
    or symlink, none renamed meanwhile), the folder itself must be an ordinary directory, never directly inside a source
    folder (_folders) and never in Sorted (_folders), and its listing must show nothing. Then a plain rmdir, which
    fails if anything arrived in it meanwhile: never anything recursive. Any failure keeps the folder ("1 folder
    stayed."); the book is forgotten all the same."""
    try:
        target = ordinary(folder)
        with DirectoryBoundary(ordinary(root), target.parent):
            facts = os.lstat(target)
            if not stat.S_ISDIR(facts.st_mode) or getattr(facts, 'st_file_attributes', 0) & 0x400 or os.path.isjunction(target) or os.path.islink(target):
                return False
            if not _empty(target):
                return False
            os.rmdir(target)
    except (BoundaryError, OSError):
        return False
    return not os.path.lexists(folder)


def _stamp(path):
    """[size, modification time, volume, file id]: a file unchanged since it was hashed keeps all four."""
    facts = os.stat(path)
    return [facts.st_size, facts.st_mtime_ns, facts.st_dev, facts.st_ino]


def _copy_proof(service, row, source, files, output, text, stop=None, proven=None):
    """Remove this copy: the proof, now (Judy's update spec, section 4). Every file of the copy, in order, has the size and
    SHA-256 of the matching source the audiobook was arranged from; then, last, the audiobook is where the app put it
    with its recorded size and checksum (the full output check). No listed file is the audiobook's own file. stop: set
    by drain and close; a stopped proof raises InterruptedError. proven: the press's own proof, made before it took the
    app's locks (Senua's N19, see _prove): nothing is hashed again, and every file it hashed, the audiobook included,
    must be unchanged since (size, modification time, native identity), the audiobook at the same place."""
    from audio_pipeline import digest
    sources = (source['job'].get('manifest') or {}).get('sources') or []
    members = row.get('members') or []
    mismatch = DeleteRefused('not_identical', 'These files no longer match the ones the audiobook was arranged from. Nothing was deleted.')
    if len(sources) != len(members):
        raise mismatch
    stamps = {}
    for member, item in zip(members, sources):
        try:
            if member.get('missing'):
                raise mismatch
            stamp = _stamp(member['path'])  # before the hash: a write during it changes the time
            if proven is not None:
                if stamp != proven['stamps'].get(_key(member['path'])):
                    raise mismatch
            elif stamp[0] != item.get('size') or digest(member['path'], stop) != item.get('sha256'):
                raise mismatch
            stamps[_key(member['path'])] = stamp
        except FileNotFoundError:
            raise mismatch
        except InterruptedError:
            raise
        except OSError:
            raise DeleteRefused('offline', "Can't reach %s. Nothing was deleted." % Path(member['path']).anchor, root=Path(member['path']).anchor)
    name = _sorted_name(output)
    if output and not os.path.isdir(output):
        raise DeleteRefused('offline', "Can't reach %s. Nothing was deleted." % output, root=output)
    record, final = _sorted_record(service, source['output'])
    missing = DeleteRefused('sorted_missing', 'The audiobook is not where the app put it in %s. Nothing was deleted.' % name)
    changed = DeleteRefused('sorted_changed', 'The audiobook in %s has changed since the app arranged it. Nothing was deleted.' % name)
    if not record or not os.path.lexists(final):
        raise missing
    try:
        held = _stamp(final)
    except OSError:
        raise missing
    if proven is not None:
        if _key(final) != _key(proven['path']) or held != proven['stamps'].get(_key(final)) or record.get('sha256') != proven['record'].get('sha256'):
            raise changed
    elif not service._output_valid(source['output'], stop):
        if not os.path.lexists(final):
            raise missing
        raise changed
    try:
        if any(_stamp(f['path'])[2:] == held[2:] for f in files):
            raise refused('is_sorted')
    except OSError:
        raise missing
    stamps[_key(final)] = held
    verified = proven['verified_at'] if proven is not None else datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {'path': final, 'size': record.get('size'), 'verified_at': verified, 'record': record, 'stamps': stamps}


def plan(service, identity, revision, mode='delete', stop=None, proven=None, wait=False):
    """Read-only: what the press would remove now. {'files': [{'path', 'size', 'root', 'kind'}], 'bytes', 'folders':
    [(folder, root)], 'stay', 'last_copy', 'sorted', 'members', 'jobs', 'kind', 'row', 'blocked'}. Raises DeleteRefused
    with every refusal check (the preview runs them before the confirm). stop and proven: see _copy_proof.

    wait=True (the queued Delete's preview, 0.22.1; Judy 1.5): a scan, or the book's own processing, is not a refusal but
    what the delete waits for: 'blocked' names it ('scan' or 'book') and the plan is made anyway, read-only. The run
    itself always plans with wait=False, so a blocker never lets anything be deleted."""
    if mode not in MODES:
        raise refused('invalid')
    text = _TEXT[mode]['refused']
    blocked = None
    if scanning(service) and wait:
        blocked = 'scan'
    elif scanning(service):
        # Senua's 0.22.0 final review, N13 (probe P1): a Delete while the scan held the book's queued files let the scan
        # find them gone, and with no catalog row it wrote each back as a new one-file book with a raw "[Errno 2]" error;
        # the scan then ended "completed with errors", which stops an automatic run. Keep, Approve, Scan again and Convert
        # already wait for the scan; Delete and Remove this copy now do too, before they read or touch anything.
        raise DeleteRefused('busy', BUSY)
    try:
        row = service.reviews._row('Audiobooks', identity, revision)
    except ValueError:
        raise DeleteRefused('changed', CHANGED)
    inventory = service.inventory
    roots = [str(ordinary(r)) for r in inventory.source_roots('Audiobooks')]
    output = getattr(inventory, 'output_root', None)
    output = str(ordinary(output)) if output else None
    members = [m['path'] for m in row.get('members') or []]
    if not members:
        raise refused('no_files')
    source = None
    with connect(inventory.database) as db:
        jobs = _jobs(db, identity)
        if any(j['state'] in ('pending', 'running') for j in jobs):
            if not wait:
                raise DeleteRefused('busy', BUSY)
            blocked = blocked or 'book'
        if mode == 'delete':
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
                    raise DeleteRefused('sorted', 'A finished audiobook of this book is in %s. Nothing was deleted.' % _sorted_name(output))
        elif jobs:
            raise refused('has_job')  # a copy has no job of its own: a book with one is no "Needs you" duplicate
        if _table(db, 'automatic_candidates'):
            researching = db.execute("SELECT 1 FROM automatic_candidates WHERE id=? AND state='Researching'", (identity,)).fetchone()
            if researching and not wait:
                raise DeleteRefused('busy', BUSY)
            if researching:
                blocked = blocked or 'book'
        # The server's own offer: Delete's (a finished, queued or researched book was refused above with its own line; any
        # other book without it, one the app can still fix, a duplicate, Files unclear, is refused here), or the copy's.
        if mode == 'delete':
            kind = offer(service, row)
        else:
            source = copy_source(service, row, exists=False)  # the press says why the audiobook fails, see _copy_proof
            kind = 'verified_duplicate' if source else None
        if kind is None:
            raise refused('not_offered', mode)
        # Shared: another current book, another book's job, or another book's reacquire record holds the file. History of
        # a book that is gone does not count (Senua's 0.22.0 final review, N16): an archived marker (its originals are
        # confirmed gone) or a stopped job of that book names the paths it had, and a copy reacquired at those paths is a
        # new book, which Delete refused as "shared" with a book that is not listed. See _history.
        current = {r[0] for r in db.execute('SELECT id FROM book_groups WHERE superseded=0')} if _table(db, 'book_groups') else set()
        holders = _Holders(db, identity, current)
        shared = {p: holders.title(_key(p)) for p in members if _key(p) in holders}
        if shared:
            listed = [{'path': p, 'other': other} for p, other in sorted(shared.items())]
            if len(listed) == 1:
                raise DeleteRefused('shared', '"%s" also belongs to "%s". Nothing was deleted.' % (listed[0]['path'], listed[0]['other']), listed)
            raise DeleteRefused('shared', '%d of this book\'s files also belong to other books. Nothing was deleted.' % len(listed), listed)
    files, guarded = [], set()
    for path in members:
        try:
            p = ordinary(path)
        except BoundaryError:
            raise refused('link')
        root = next((r for r in roots if inside(str(p), r) and _key(p) != _key(r)), None)
        if root is None or output and inside(str(p), output) or p.suffix.lower() not in AUDIO:
            # Never outside a configured source root, never in Sorted, never anything but this book's audio.
            raise refused('outside')
        if not os.path.isdir(root):
            raise DeleteRefused('offline', "Can't reach %s. Nothing was deleted." % root, root=root)
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
            raise refused('second_name')
        _guard(root, p.parent, guarded, text)
        files.append({'path': str(p), 'size': facts.st_size, 'root': root, 'kind': 'audio'})
    others, stay, book_folders = _others(members, roots, output, holders, guarded, text)
    files += others
    working = _working(service, jobs, text) if mode == 'delete' else []
    # Ruling 26: a working copy of an original already gone is the last copy of that audio; the dialog says so.
    gone = [w for w in working if w['original'] and not os.path.lexists(w['original'])]
    last_copy = None if not gone else 'some' if any(f['kind'] == 'audio' for f in files) else 'all'
    folders = _folders(book_folders, files, output)
    proof = _copy_proof(service, row, source, files, output, text, stop, proven) if mode == 'copy' else None  # the audiobook last
    files += working
    return {'files': files, 'bytes': sum(f['size'] for f in files), 'folders': folders, 'stay': stay, 'last_copy': last_copy,
            'sorted': proof, 'members': members, 'jobs': jobs, 'kind': kind, 'row': row, 'blocked': blocked}


def processing(service, identity):
    """The book is converting, queued for conversion or being researched: what a queued Delete waits for ('book'),
    the same facts plan() refuses as 'busy'. Read-only."""
    with connect(service.inventory.database) as db:
        if any(j['state'] in ('pending', 'running') for j in _jobs(db, identity)):
            return True
        return bool(_table(db, 'automatic_candidates') and db.execute("SELECT 1 FROM automatic_candidates WHERE id=? AND state='Researching'", (identity,)).fetchone())


def preview(service, identity, revision, mode='delete', wait=False):
    """POST /api/candidate/delete-preview: {'files': [{'path', 'size', 'kind'}], 'bytes', 'folders': [path], 'stay':
    {'items'}, 'last_copy', 'kind', 'sorted': None | {'path', 'size', 'verified_at'}, 'refusal': None | {...}, 'blocked':
    None | {'kind'}}. wait: see plan (Delete book only)."""
    wait = wait and mode == 'delete'
    try:
        with _stoppable(service) as stop:
            found = plan(service, identity, revision, mode, stop, wait=wait)
    except DeleteRefused as refusal:
        return {'files': [], 'bytes': 0, 'folders': [], 'stay': {'items': 0}, 'last_copy': None, 'sorted': None, 'refusal': refusal.payload()}
    shown = found['sorted']
    return {'files': [{'path': f['path'], 'size': f['size'], 'kind': f['kind']} for f in found['files']], 'bytes': found['bytes'],
            'folders': [folder for folder, _root in found['folders']], 'stay': {'items': found['stay']}, 'last_copy': found['last_copy'],
            'kind': found['kind'], 'sorted': {k: shown[k] for k in ('path', 'size', 'verified_at')} if shown else None, 'refusal': None,
            'blocked': {'kind': found['blocked']} if found.get('blocked') else None}


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


@contextlib.contextmanager
def _hold(found, output):
    """Remove this copy: the audiobook in Sorted held open, without write or delete sharing, while the copy's files go,
    and checked once more (its recorded size and native identity) right before the first one. A refusal here touches
    nothing."""
    proof = found.get('sorted')
    with contextlib.ExitStack() as stack:
        if proof:
            record, name = proof['record'], _sorted_name(output)
            final = ordinary(record['final_path'])
            try:
                stack.enter_context(DirectoryBoundary(ordinary(record['root']), final.parent))
                facts = stack.enter_context(VerifiedFile(final)).facts()
            except (BoundaryError, OSError):
                if not os.path.lexists(final):
                    raise DeleteRefused('sorted_missing', 'The audiobook is not where the app put it in %s. Nothing was deleted.' % name)
                raise DeleteRefused('sorted_changed', 'The audiobook in %s has changed since the app arranged it. Nothing was deleted.' % name)
            if facts['size'] != record.get('size') or record.get('identity') is not None and facts['identity'] != record['identity']:
                raise DeleteRefused('sorted_changed', 'The audiobook in %s has changed since the app arranged it. Nothing was deleted.' % name)
        yield


@contextlib.contextmanager
def _stoppable(service):
    """A stop event for one proof, among the presses drain and close stop (merge_service's _approve_stops). A stopped
    proof is refused 'busy': nothing was touched."""
    stop = threading.Event()
    presses = service.__dict__.setdefault('_approve_stops', set())
    presses.add(stop)
    if getattr(service, 'draining', False) or service.__dict__.get('_closing'):
        stop.set()
    try:
        yield stop
    except InterruptedError:
        raise DeleteRefused('busy', BUSY) from None
    finally:
        presses.discard(stop)


def _prove(service, identity, revision):
    """Remove this copy, Senua's 0.22.0 review, N19: the press's proof hashes every file of the copy and the whole
    audiobook in Sorted, often over the network. It ran holding the app's operation and group locks, so the status poll,
    Approve, Keep and the list waited for it, and nothing could stop it: Quit waited for the hashes. Now it runs before
    the press takes either lock, and drain and close stop it; under the locks the plan is made again from the catalog
    and every file it hashed must be unchanged since (_copy_proof), then _hold checks the audiobook once more right
    before the first file goes. The proof's 'sorted' entry."""
    with _stoppable(service) as stop:
        return plan(service, identity, revision, 'copy', stop=stop)['sorted']


def _bounded(values):
    return isinstance(values, list) and len(values) <= 10000 and all(isinstance(p, str) and 1 <= len(p) <= 1000 for p in values)


def delete(service, identity, revision, paths, folders=None, mode='delete'):
    """POST /api/candidate/delete: {'deleted', 'bytes', 'failed': [{'path', 'cause', 'detail'}], 'forgotten', 'folders':
    {'removed', 'stayed'}}. paths and folders are exactly those the dialog showed. Raises DeleteRefused before touching
    any file. forgotten is True only after the records transaction committed."""
    folders = [] if folders is None else folders
    if mode not in MODES or not _bounded(paths) or not _bounded(folders):
        raise refused('invalid')
    proven = _prove(service, identity, revision) if mode == 'copy' else None  # before the locks (N19)
    with service.operation_lock, service.inventory.group_lock:
        found = plan(service, identity, revision, mode, proven=proven)
        same = sorted(_key(f['path']) for f in found['files']) == sorted(_key(p) for p in paths) and len(set(map(_key, paths))) == len(paths)
        if not same or sorted(_key(f) for f, _root in found['folders']) != sorted(_key(f) for f in folders):
            raise DeleteRefused('files_changed', _TEXT[mode]['files_changed'])
        output = getattr(service.inventory, 'output_root', None)
        deleted, removed_bytes, failed = 0, 0, []
        with critical_sections.critical(critical_sections.DELETE), _hold(found, output):
            for item in found['files']:
                if item['kind'] == 'working':
                    continue
                outcome = remove(item['path'], item['root'], item['size'])
                if outcome is None:
                    deleted += 1
                    removed_bytes += item['size']
                else:
                    failed.append({'path': item['path'], 'cause': outcome[0], 'detail': outcome[1]})
            # The app's working files (ruling 26), attempt by attempt, after the book's own files: the discard proves each
            # file is the app's own and needs no original, so it removes the last copy too, for this action only.
            attempts = sorted({(w['job_id'], w['attempt_id']) for w in found['files'] if w['kind'] == 'working'})
            for job_id, attempt_id in attempts:
                try:
                    for _path, size in service.working.discard(job_id, attempt_id):
                        deleted += 1
                        removed_bytes += size
                except Exception as error:
                    failed.append({'path': WORKING, 'cause': _cause(error), 'detail': str(error)[:500]})
                    break
        forgotten, removed, stayed = False, 0, 0
        if not failed:
            # Every listed file is gone, or was already.
            still = [p for p in [*found['members'], *(f['path'] for f in found['files'])] if os.path.lexists(p)]
            if still:
                failed.extend({'path': p, 'cause': 'other', 'detail': 'Still on disk'} for p in dict.fromkeys(still))
            else:
                with critical_sections.critical(critical_sections.DELETE):  # ruling 27: folders and records, once begun
                    # Folders are housekeeping: one that cannot be removed stays and never keeps the book listed.
                    for folder, root in found['folders']:
                        if _remove_folder(folder, root):
                            removed += 1
                        else:
                            stayed += 1
                    forget(service, identity, found['members'], found['jobs'], [f['path'] for f in found['files'] if f['kind'] == 'other'])
                    forgotten = True
    service.after_delete(identity)
    return {'deleted': deleted, 'bytes': removed_bytes, 'failed': failed, 'forgotten': forgotten, 'folders': {'removed': removed, 'stayed': stayed}}


def present(service, row):
    """The offer's count (Judy's update spec, section 4): every file the press would delete, read without touching the
    source drive (a page read): the book's present audio, the other files the catalog holds in its folders when no other
    audio file is catalogued there, and its stopped jobs' working files on the app's own drive. plan() decides."""
    members = row.get('members') or []
    count = sum(1 for m in members if not m.get('missing'))
    keys = {_key(m['path']) for m in members}
    folders = {_key(Path(m['path']).parent): str(Path(m['path']).parent) for m in members}  # the catalog's own spelling: LIKE folds ASCII only
    try:
        with connect(service.inventory.database) as db:
            for folder, spelled in folders.items():
                pattern = spelled.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '\\\\%'
                under = list(db.execute("SELECT path,missing FROM files WHERE path LIKE ? ESCAPE '\\'", (pattern,)))  # the folder and below (N18)
                rows = [r for r in under if os.path.dirname(_key(r['path'])) == folder]
                foreign = any(_key(r['path']) not in keys and Path(r['path']).suffix.lower() in SOUND and not r['missing'] for r in under)
                if not foreign:
                    count += sum(1 for r in rows if _key(r['path']) not in keys and not r['missing'])
            jobs = _jobs(db, row['id'])
        for job in jobs:
            if job['state'] == 'needs attention' and not job['output'] and hasattr(service, '_working_listing'):
                count += sum(len(names) for _attempt, names in service._working_listing(job['job_id'])[0])
    except Exception:
        pass  # a hint only: the press itself reads the disk and refuses what it cannot prove
    return count


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


def forget(service, identity, members, jobs, others=()):
    """One transaction: every record of this book. Its group goes, so its files never regroup as it; its file rows go,
    so a copy reacquired at the same paths is a new book with a new identity (Judy, section 5.6); the catalog rows of
    the other files Delete removed (ruling 24) go with them."""
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
                for path in [*members, *others]:
                    db.execute('DELETE FROM %s WHERE path=?' % table, (path,))
