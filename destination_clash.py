"""0.31.0 step 1c (Sergei 2026-11-22): two books never share one destination.

"Goes to" and Approve checked only the disk for a taken name (merge_service._approval_destination, approve_book), so two
rows that planned the same file both showed it free: his two Sprawl volumes, both "Sprawl Trilogy", one destination. A
name is also taken when another current row plans it or a book waiting to convert has it. Both rows are then held with
this reason, their own (never "Part of a bigger book"), and each names the other books so the page can word it.

  hold = {'kind': 'same_destination', 'detail': '', 'destination': path under Audiobooks Sorted, 'absolute': whole path,
          'count': how many other books, 'others': [other]}        (identity_hold of the held result; ask.destination.shared)
  other = {'book_id', 'kind': 'row' | 'queued', 'job_id' (queued only), 'name', 'title', 'author'}
  name: the other book's own file name (one file) or folder name, which tells it apart; its title is the same as this row's.

A book that already waits to convert keeps its name (it had it first) and is named as 'queued'; the newcomer is held.
Reads only the catalog and the rows' planned names the engine noted in this session (MergeService._planned)."""
import json
import ntpath

HOLD = 'same_destination'
REASON = 'Another book would get the same name'
REFUSED = REASON + '. Change the title, author, series or number. Nothing was changed.'
LISTED = 10  # others named one by one; 'count' carries the rest
WAITING = ('pending', 'running', 'needs attention')


class Shared(ValueError):
    """Approve, or automatic filing, refused: other books plan this destination. identity_hold is the typed hold."""
    def __init__(self, hold):
        super().__init__(REFUSED)
        self.identity_hold = hold
        self.code = 'same_name'


def key(path):
    return ntpath.normcase(ntpath.normpath(str(path or '')))


def name_of(paths):
    """What tells a book apart from one with the same title: its file name without the author before it ("03-Мона Лиза
    овердрайв" of "Уильям Гибсон - 03-Мона Лиза овердрайв.m4b"), or the folder of a book of several files."""
    paths = [str(p) for p in paths or [] if p]
    if not paths:
        return ''
    if len(paths) == 1:
        from source_identity import filename_identity
        stem = ntpath.splitext(ntpath.basename(paths[0]))[0]
        pieces = stem.split(' - ', 1)
        return (pieces[1] if len(pieces) == 2 and filename_identity(ntpath.basename(paths[0])).get('author') else stem).strip() or stem
    return ntpath.basename(ntpath.dirname(paths[0]))


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def queued(db, destination, own):
    """The books waiting to convert that have this destination: jobs not completed and not set aside, of another book.
    A cleanup task of an extra source, a replacement and a retry of the same book share a name by design and never count."""
    if not _table(db, 'audio_jobs'):
        return []
    wanted = key(destination)
    aside = ' AND job_id NOT IN (SELECT job_id FROM audio_job_set_aside)' if _table(db, 'audio_job_set_aside') else ''
    found = []
    for job_id, state, target, candidate, title, author, task, replacement, source in db.execute(
            "SELECT job_id,state,json_extract(manifest,'$.destination'),json_extract(manifest,'$.candidate_id'),json_extract(manifest,'$.metadata.title'),"
            "json_extract(manifest,'$.metadata.author'),json_extract(manifest,'$.task_kind'),"
            "coalesce(json_extract(manifest,'$.replacement_id'),json_extract(manifest,'$.replacement_parent_job_id')),json_extract(manifest,'$.sources')"
            " FROM audio_jobs WHERE state IN (%s) AND output IS NULL%s ORDER BY created,job_id" % (','.join('?' * len(WAITING)), aside), WAITING):
        if not target or key(target) != wanted or candidate == own or task or replacement:
            continue
        if any(item['book_id'] == candidate for item in found):
            continue
        try:
            paths = [s.get('path') for s in json.loads(source or '[]') if isinstance(s, dict)]
        except (TypeError, ValueError):
            paths = []
        found.append({'book_id': candidate, 'kind': 'queued', 'job_id': job_id, 'name': name_of(paths), 'title': title or '', 'author': author or ''})
    return found


def rows(db, destination, own, planned):
    """The other current rows that plan this destination. planned: {book id: {'revision', 'fingerprint', 'key', 'name',
    'title', 'author'}}, what the engine noted for each row it planned a name for; an entry counts only while its book is
    current, unchanged and has no job (a book with a job is queued()'s)."""
    wanted = key(destination)
    found = []
    for book_id, entry in list((planned or {}).items()):
        if book_id == own or entry.get('key') != wanted:
            continue
        current = db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=? AND superseded=0', (book_id,)).fetchone() if _table(db, 'book_groups') else None
        if current is None or current[0] != entry.get('revision') or current[1] != entry.get('fingerprint'):
            continue
        if _table(db, 'audio_jobs') and db.execute(
                "SELECT 1 FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? AND state IN (%s) LIMIT 1" % ','.join('?' * (len(WAITING) + 1)),
                (book_id, *WAITING, 'completed')).fetchone():
            continue
        found.append({'book_id': book_id, 'kind': 'row', 'name': entry.get('name') or '', 'title': entry.get('title') or '', 'author': entry.get('author') or ''})
    return found


def hold(destination, relative, others, own_name=''):
    """The typed hold for `others` sharing `destination`, or None when there are none. A name equal to this row's own
    (two folders holding a file of the same name) is given with its folder, so it still tells the books apart."""
    if not others:
        return None
    return {'kind': HOLD, 'detail': '', 'destination': relative or '', 'absolute': str(destination or ''), 'count': len(others),
            'others': [dict(other) for other in sorted(others, key=lambda o: (o['kind'] != 'queued', o['name'].casefold(), o['book_id'] or ''))[:LISTED]]}
