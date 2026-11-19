"""Join into one book (0.30.0 item D; Judy's 0.30.0 spec, section 8; Sergei's answers, round 2: 8 review, 9 yes, 10 no).

The app sometimes keeps the named parts of one novel as separate books: «Впусти меня», five single-file .m4b parts, one
album, tracks 1/5 to 5/5, each with its own part title, so part_sets.decide calls them separate volumes ("each file names
its own work"). Sergei selects the rows and joins them. A join RECORDS one book (assumption A12): nothing is converted,
repaired, moved or opened for writing. The audio is joined when the joined book is converted (ruling 19a: every part's
own chapters kept in order, a part without chapters one chapter named after it), and a damaged part is repaired there.

The record (book_joins): the files of the joined book in Sergei's play order, each with its size and time, and his title.
groups.build files them as one candidate while every file still matches; a changed or missing file lapses the record and
the files group as before (the same rule as the separate-volume facts). The join wins over the planners and over the
parts' own protected groups (a part with a job or saved values would otherwise keep its files); a part's inferred or kept
separate-volume fact is replaced by the join. The joined book's title and author are Sergei's names (entered_names: his
book entries for its files); a series that came from the part names is cleared, a series every file's tags agree on is
left to the tags (A14). The joined book is not approved and automatic processing holds it for his approval (answer 8,
review), as a Save in Edit names does (names_approval_pending).

join() does it all in one catalog transaction or nothing (Judy 8.5): queued conversions of the parts are set aside (the
record stays in history), failed jobs are set aside (they leave Needs attention and its counts), accepted Retry and Repair
requests are withdrawn (m4b_readmission.withdraw), approvals go. A part that converts now (or whose retry check runs) is
'busy': the queued join waits for it and never aborts it. Every part is checked again when the join runs.

preview() is read-only: the parts in play order with their facts, the order basis, the proposed title and author, the
series the join drops or keeps, per-part refusals and the effect counts. The page words all of it."""
import datetime
import json
import re
import time
import uuid
from pathlib import Path

VERSION = 'book-join-v1'
TABLE = ('CREATE TABLE IF NOT EXISTS book_joins(root TEXT NOT NULL, path TEXT NOT NULL, join_id TEXT NOT NULL, position INTEGER NOT NULL, '
         'parts INTEGER NOT NULL, size INTEGER NOT NULL, modified TEXT NOT NULL, title TEXT NOT NULL, created TEXT NOT NULL, PRIMARY KEY(root,path))')
SCOPE = '\x1fJoined by you\x1f'
GROUPING = 'One book: joined by you.'
JOIN_REASON = 'Set aside: joined into one book by you. Nothing ran; the joined book is checked from the start.'
TITLE_NEEDED = 'Type a title first.'
LIMIT = 200  # parts in one join (a page holds at most this many rows)


class Refused(ValueError):
    """Nothing was joined. cause: the page's key (finished, changed, gone, queued, manual, root, title, count, failed); title:
    the part it names, if any."""
    def __init__(self, cause, message, title=''):
        super().__init__(message)
        self.cause, self.title = cause, title


class Busy(ValueError):
    """A part converts now (or its retry check runs): the queued join waits for it."""


def _stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def setup(db):
    """The record and its triggers: any change regroups the catalog (book_catalog_revision, groups.setup made it)."""
    db.execute(TABLE)
    db.execute('CREATE INDEX IF NOT EXISTS book_joins_by_join ON book_joins(join_id)')
    if _table(db, 'book_catalog_revision'):
        for operation in ('INSERT', 'UPDATE', 'DELETE'):
            db.execute(f'CREATE TRIGGER IF NOT EXISTS book_joins_{operation.lower()} AFTER {operation} ON book_joins '
                       'BEGIN UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1; END')


def scope(paths, join_id):
    """The joined book's group scope: its first file's folder (the list sorts by scope), then the join."""
    return str(Path(paths[0]).parent) + SCOPE + join_id


def valid(db, root):
    """{join_id: (paths in play order, title)} of the joins on this root whose every file still matches its record (size,
    time, present, readable). Read-only; {} before the first join."""
    if not _table(db, 'book_joins'):
        return {}
    found = {}
    for row in db.execute("""SELECT j.join_id,j.path,j.parts,j.title FROM book_joins j JOIN files f ON f.root=j.root AND f.path=j.path
            WHERE j.root=? AND j.size=f.size AND j.modified=CAST(f.modified AS TEXT) AND f.error='' AND f.missing=0
            ORDER BY j.join_id,j.position""", (root,)):
        entry = found.setdefault(row[0], {'paths': [], 'parts': row[2], 'title': row[3]})
        entry['paths'].append(row[1])
    return {key: (tuple(value['paths']), value['title']) for key, value in found.items() if len(value['paths']) == value['parts'] and value['paths']}


def record(db, root, join_id, members, title):
    """Write the record of one join (members: [{path, size, modified}] in play order). A file in an older join leaves it
    (that join lapses: its record is no longer whole)."""
    setup(db)
    now = _stamp()
    for position, member in enumerate(members, 1):
        db.execute('INSERT OR REPLACE INTO book_joins VALUES(?,?,?,?,?,?,?,?,?)',
                   (root, member['path'], join_id, position, len(members), int(member['size']), str(member['modified']), title, now))


# ---------------------------------------------------------------- what the dialog proposes (Judy 8.3, 8.4)
_PART_WORDS = re.compile(r'(?<![^\W\d_])(?:часть|part|книга|book|том|volume|vol\.|диск|disc|cd)\s*(?:[0-9]{1,4}|[ivxlc]{1,7}\b|[а-яё]+(?:ая|ый|ой|ий|ья))', re.I)
_NUMBER = re.compile(r'(?<![^\W_])[0-9]{1,4}(?![^\W_])')


def _words(text):
    return ' '.join(str(text or '').split())


def _key(text):
    return _words(text).casefold()


def part_title(row):
    """A part's own title, as its line in the dialog shows it (repaired text): a single file's title tag, else its file
    name; a part of several files its list title."""
    import tag_text
    members = row.get('members') or []
    if len(members) == 1:
        title = _words(tag_text.tags(members[0].get('metadata')).get('title') or '')
        return title if isinstance(title, str) and title else Path(members[0]['path']).stem
    if not members:
        return ''
    review = row.get('review') or {}
    return _words(review.get('title') or row.get('title_clue') or '') or Path(members[0]['path']).parent.name


def track_of(row):
    """(track, total) of a single-file part from its album track tag ("1/5"), else (None, None)."""
    import tag_text
    members = row.get('members') or []
    if len(members) != 1:
        return None, None
    tags = tag_text.tags(members[0].get('metadata'))
    match = re.match(r'^\s*(\d{1,4})\s*(?:/\s*(\d{1,4}))?\s*$', str(tags.get('track') or tags.get('tracknumber') or ''))
    if not match or int(match[1]) < 1:
        return None, None
    return int(match[1]), int(match[2]) if match[2] and int(match[2]) > 0 else None


def _name_number(row, title):
    """The number a part's file name (else its title) carries: its last number ("Впусти меня 5", "Часть 3")."""
    members = row.get('members') or []
    for text in ((Path(members[0]['path']).stem if members else ''), title):
        found = _NUMBER.findall(str(text or ''))
        if found:
            return int(found[-1])
    return None


def order(parts):
    """parts: [{'row', 'title', ...}] as selected. Returns (ordered parts, basis): basis {'basis': album_tracks | file_names |
    none, 'first', 'last', 'total', 'missing': [n], 'duplicate': n or None}. Strongest evidence first (Judy 8.3)."""
    from groups import natural
    path = lambda part: str((part['row'].get('members') or [{}])[0].get('path') or '')
    by_name = sorted(parts, key=lambda part: (natural(Path(path(part)).name), path(part)))
    tracks = [part['track'] for part in parts]
    if parts and all(track is not None for track in tracks):
        ordered = sorted(parts, key=lambda part: (part['track'], natural(Path(path(part)).name), path(part)))
        counts = {}
        for track in tracks:
            counts[track] = counts.get(track, 0) + 1
        duplicate = next((track for track in sorted(counts) if counts[track] > 1), None)
        totals = [part['track_total'] for part in parts if part['track_total']]
        total = max(totals + [max(tracks)]) if totals else None
        missing = [n for n in range(1, total + 1) if n not in counts] if total else []
        return ordered, {'basis': 'album_tracks', 'first': min(tracks), 'last': max(tracks), 'total': total, 'missing': missing, 'duplicate': duplicate}
    numbers = [_name_number(part['row'], part['title']) for part in parts]
    if parts and all(number is not None for number in numbers):
        rank = {id(part): number for part, number in zip(parts, numbers)}
        ordered = sorted(parts, key=lambda part: (rank[id(part)], natural(Path(path(part)).name), path(part)))
        return ordered, {'basis': 'file_names', 'first': None, 'last': None, 'total': None, 'missing': [], 'duplicate': None}
    return by_name, {'basis': 'none', 'first': None, 'last': None, 'total': None, 'missing': [], 'duplicate': None}


def _strip_numbers(title):
    return _words(_NUMBER.sub(' ', _PART_WORDS.sub(' ', str(title or ''))))


def proposed_title(parts):
    """Judy 8.4: the album every file of every part shares (repaired text), else the words every part title starts with
    once part numbers are dropped (Впусти меня 5 and Впусти меня give «Впусти меня»), else ''."""
    import tag_text
    from groups import DISC_SUFFIX
    albums = set()
    shown = ''
    for part in parts:
        for member in part['row'].get('members') or []:
            album = _words(tag_text.tags(member.get('metadata')).get('album') or '')
            album = _words(DISC_SUFFIX.sub('', album)) or album
            albums.add(_key(album))
            shown = shown or album
    if len(albums) == 1 and '' not in albums and shown:
        return shown
    stripped = [_strip_numbers(part['title']).split() for part in parts]
    if not stripped or not all(stripped):
        return ''
    common = []
    for words in zip(*stripped):
        # Punctuation around a word is no difference ("меня." before "Часть 1", "меня" before "5").
        cleaned = [re.sub(r'^\W+|\W+$', '', word).casefold() for word in words]
        if len(set(cleaned)) != 1 or not cleaned[0]:
            break
        common.append(words[0])
    return re.sub(r'^[\W_]+|[\W_]+$', '', ' '.join(common)).strip()


def tag_series(parts):
    """A14: {'name', 'number'} when every file of every part carries the same series and number in its tags, else None."""
    values = set()
    for part in parts:
        for member in part['row'].get('members') or []:
            metadata = member.get('metadata') or {}
            values.add((_words(metadata.get('series') or ''), _words(metadata.get('number') or '')))
    if len(values) == 1:
        name, number = next(iter(values))
        if name and number:
            return {'name': name, 'number': number}
    return None


# ---------------------------------------------------------------- the parts' jobs (read under the queue's lock for the join)
def _job_rows(db, identity):
    """The part's jobs that are not set aside, newest first: [{job_id, state, output, intent}]."""
    if not _table(db, 'audio_jobs'):
        return []
    aside = ' AND job_id NOT IN (SELECT job_id FROM audio_job_set_aside)' if _table(db, 'audio_job_set_aside') else ''
    rows = db.execute("SELECT job_id,state,output,journal FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=?" + aside +
                      ' ORDER BY created DESC, job_id DESC', (identity,)).fetchall()
    found = []
    for row in rows:
        try:
            journal = json.loads(row['journal'] or '{}')
        except ValueError:
            journal = {}
        found.append({'job_id': row['job_id'], 'state': row['state'], 'output': row['output'], 'intent': isinstance(journal, dict) and 'publication_intent' in journal})
    return found


def _requests(db, job_ids):
    """The accepted Retry and Repair requests of these jobs (as parent or child): [(parent, child, state)]."""
    import m4b_readmission
    if not job_ids or not m4b_readmission._exists(db):
        return []
    marks = json.dumps(sorted(job_ids))
    return [tuple(row) for row in db.execute("SELECT parent_job_id,child_job_id,state,kind FROM m4b_readmissions WHERE state IN ('queued','admitted') AND "
                                              "(parent_job_id IN (SELECT value FROM json_each(?)) OR child_job_id IN (SELECT value FROM json_each(?)))", (marks, marks))]


def approved(db, identity):
    """The part is approved: its group says so, or its saved context at its revision holds an approval (Sergei's or the
    automatic pass's)."""
    row = db.execute('SELECT approved,revision FROM book_groups WHERE id=?', (identity,)).fetchone()
    if not row:
        return False
    if row[0]:
        return True
    if not _table(db, 'candidate_context'):
        return False
    saved = db.execute('SELECT revision,data FROM candidate_context WHERE id=?', (identity,)).fetchone()
    if not saved or saved[0] != row[1]:
        return False
    try:
        data = json.loads(saved[1] or '{}')
    except ValueError:
        return False
    return isinstance(data, dict) and bool(data.get('metadata_approved') or data.get('user_approval') or data.get('automatic_approval'))


def _all_job_ids(db, identity):
    if not _table(db, 'audio_jobs'):
        return []
    return [row[0] for row in db.execute("SELECT job_id FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=?", (identity,))]


def facts(db, identity, claimed=None, checking=None):
    """One part's job facts: {'state': finished | converting | queued | failed | candidate, 'queued', 'failed', 'request',
    'jobs' (the unfinished jobs the join sets aside), 'requests' (the accepted requests it withdraws)}. claimed: the job the
    conversion worker holds; checking: the job whose retry check runs."""
    jobs = _job_rows(db, identity)
    requests = _requests(db, _all_job_ids(db, identity))
    children = {child for _parent, child, state, _kind in requests if state == 'admitted' and child}
    finished = any(job['state'] == 'completed' or job['output'] or job['intent'] for job in jobs)
    running = any(job['state'] == 'running' or job['job_id'] in (claimed, checking) for job in jobs) or any(checking in (parent, child) for parent, child, _state, _kind in requests if checking)
    queued = any(job['state'] == 'pending' and job['job_id'] not in children for job in jobs)
    failed = any(job['state'] == 'needs attention' and not job['output'] and not job['intent'] for job in jobs)
    state = 'finished' if finished else 'converting' if running else 'queued' if queued else 'failed' if failed else 'candidate'
    return {'state': state, 'queued': queued, 'failed': failed, 'request': bool(requests), 'request_kind': requests[0][3] if requests else None,
            'jobs': [job for job in jobs if job['state'] in ('pending', 'needs attention') and not job['output'] and not job['intent']],
            'requests': requests}


# ---------------------------------------------------------------- preview (read-only)
def _cause_text(cause, title):
    """The engine's sentence for a refusal (the page words the dialog from the cause; this is the outcome's text)."""
    return {'finished': '«%s» is already a finished audiobook. Join books that are not converted yet.',
            'changed': '«%s» changed.', 'gone': '«%s» is no longer listed.',
            'queued': '«%s» already has a queued action. Cancel it first.',
            'manual': '«%s» is a Manual Conversion draft. It can\'t be joined.',
            'root': '«%s» is in another library folder. Join books from one library folder.'}.get(cause, '«%s» can\'t be joined.') % title


def _parts(service, items, queued_presses):
    """[{'id','revision','row','title',...}] of the selected books, read now, and [refusal] for the ones that cannot join."""
    parts, refusals = [], []
    for item in items:
        identity, revision = item['id'], item['revision']
        try:
            row = service.reviews._row('Audiobooks', identity)
        except ValueError:
            refusals.append({'id': identity, 'title': item.get('title') or '', 'cause': 'gone'})
            continue
        title = part_title(row)
        track, total = track_of(row)
        part = {'id': identity, 'revision': row['revision'], 'row': row, 'title': title, 'track': track, 'track_total': total,
                'root': service.reviews._source_root(row)}
        if row['revision'] != revision:
            refusals.append({'id': identity, 'title': title, 'cause': 'changed'})
        elif row.get('manual_conversion'):
            refusals.append({'id': identity, 'title': title, 'cause': 'manual'})
        elif (queued_presses or {}).get(identity) not in (None, 'retry', 'repair'):
            refusals.append({'id': identity, 'title': title, 'cause': 'queued'})
        parts.append(part)
    roots = {part['root'] for part in parts}
    if len(roots) > 1:
        first = parts[0]['root']
        refusals.extend({'id': part['id'], 'title': part['title'], 'cause': 'root'} for part in parts if part['root'] != first)
    return parts, refusals


def _authors(service, parts):
    """(proposed author, [distinct authors], {part id: series {'name','number'}}) from each part's own Approve preview (the
    rule that names a single book: shared credit, English name, surname first)."""
    authors, series = [], {}
    for part in parts:
        try:
            preview = service.approval_preview(part['id'], part['revision'])
        except Exception:
            continue
        author = _words(preview.get('author') or '')
        if author and _key(author) not in {_key(a) for a in authors}:
            authors.append(author)
        if isinstance(preview.get('series'), dict):
            series[part['id']] = preview['series']
    return (authors[0] if len(authors) == 1 else ''), authors, series


def goes_to(service, part, title, author, names):
    """The joined book's Goes to line, from the same preview as Edit names (MergeService.approval_preview), planned on the
    first part with Sergei's title, author and series. {'path', 'absolute', 'taken', 'reason'}."""
    try:
        preview = service.approval_preview(part['id'], part['revision'], title=title, author=author, names=names)
    except (ValueError, OSError) as error:
        return {'path': '', 'absolute': '', 'taken': False, 'reason': str(error)[:300]}
    return {key: preview.get(key) for key in ('path', 'absolute', 'taken', 'reason')}


def _names(kept, dropped):
    """The series names a join plans with: the tags' series (A14), else none when a dropped one would come back."""
    if kept:
        return {'series': kept['name'], 'number': kept['number']}
    return {'series': '', 'number': ''} if dropped else {}


def preview(service, items, title=None, author=None, queued_presses=None):
    """POST /api/candidate/join-preview. items: [{id, revision}] as selected. With title (and author) typed, only the Goes
    to line is planned ({'goes_to'}). Otherwise {'parts': [...] in play order, 'order': basis, 'title', 'author', 'authors',
    'series': {'dropped', 'kept'}, 'goes_to', 'refusals': [{id, title, cause}], 'effects': {queued, failed, requests,
    approvals}}. queued_presses: {book id: action} of the action queue. Read-only."""
    from scanner import connect
    parts, refusals = _parts(service, items, queued_presses)
    if title is not None:
        # The dialog's own order (items as sent): its first part plans the line.
        if not parts:
            return {'goes_to': {'path': '', 'absolute': '', 'taken': False, 'reason': ''}}
        if not _words(title):
            return {'goes_to': {'path': '', 'absolute': '', 'taken': False, 'reason': TITLE_NEEDED}}
        return {'goes_to': goes_to(service, parts[0], _words(title), None if author is None else _words(author), _names(tag_series(parts), True))}
    claimed, checking = _worker(service)
    with connect(service.inventory.database) as db:
        for part in parts:
            part['facts'] = facts(db, part['id'], claimed, checking)
            part['approved'] = approved(db, part['id'])
    for part in parts:
        if part['facts']['state'] == 'finished':
            refusals.append({'id': part['id'], 'title': part['title'], 'cause': 'finished'})
    ordered, basis = order(parts)
    author_value, authors, series = _authors(service, ordered)
    kept = tag_series(ordered)
    dropped = None
    if not kept and series:
        names = [value.get('name') for value in series.values() if value.get('name')]
        if names:
            name = max(set(names), key=names.count)
            dropped = {'name': name, 'numbers': [series[part['id']]['number'] for part in ordered if part['id'] in series and series[part['id']].get('name') == name]}
    proposal = proposed_title(ordered)
    shown = []
    presses = queued_presses or {}
    for part in ordered:
        row, part_facts = part['row'], part['facts']
        seconds = sum(float(m.get('duration') or 0) for m in row.get('members') or [])
        shown.append({'id': part['id'], 'revision': part['revision'], 'title': part['title'], 'files': len(row.get('members') or []),
                      'hours': round(seconds / 3600, 6), 'seconds': round(seconds), 'track': part['track'], 'track_total': part['track_total'],
                      'state': part_facts['state'], 'has_queued_job': part_facts['queued'], 'has_failed_job': part_facts['failed'],
                      'has_repair_request': part_facts['request'] or presses.get(part['id']) in ('retry', 'repair'), 'has_approval': part['approved'],
                      'request_kind': part_facts['request_kind'] or (presses.get(part['id']) if presses.get(part['id']) in ('retry', 'repair') else None),
                      'm4b': bool(row.get('members')) and all(Path(m['path']).suffix.lower() == '.m4b' for m in row.get('members') or [])})
    effects = {'queued': sum(p['has_queued_job'] for p in shown), 'failed': sum(p['has_failed_job'] for p in shown),
               'requests': sum(p['has_repair_request'] for p in shown), 'approvals': sum(p['has_approval'] for p in shown)}
    return {'parts': shown, 'order': basis, 'title': proposal, 'author': author_value, 'authors': authors,
            'series': {'dropped': dropped, 'kept': kept},
            'goes_to': goes_to(service, ordered[0], proposal, author_value, _names(kept, dropped)) if ordered and proposal else {'path': '', 'absolute': '', 'taken': False, 'reason': TITLE_NEEDED},
            'refusals': refusals, 'effects': effects}


def _worker(service):
    """(the job the conversion worker holds, the job whose retry check runs) now."""
    jobs = getattr(service, 'jobs', None)
    lock = getattr(jobs, '_lock', None)
    if jobs is None or lock is None:
        return None, None
    with lock:
        checking = dict(getattr(jobs, '_priority_status', None) or {})
        return getattr(jobs, '_claimed', None), checking.get('job_id') if checking.get('state') == 'checking' else None


def busy(service, ids):
    """True when a part converts now or its retry check runs: what a queued join waits for (blocker 'book'). Read-only."""
    from scanner import connect
    claimed, checking = _worker(service)
    try:
        with connect(service.inventory.database) as db:
            return any(facts(db, identity, claimed, checking)['state'] == 'converting' for identity in ids)
    except Exception:
        return True  # unknown: it waits, never joins beside work it can't see


# ---------------------------------------------------------------- the join
def _check_items(items):
    if not isinstance(items, list) or not 2 <= len(items) <= LIMIT:
        raise Refused('count', 'Select at least 2 books to join them.')
    ids = [item['id'] for item in items]
    if len(set(ids)) != len(ids):
        raise Refused('count', 'Each book can be joined once.')
    return ids


def join(service, items, title, author=None):
    """Record the selected books as one book, in this order (items: [{id, revision}], the dialog's play order), with this
    title and author ('' or None: none typed). One transaction; Refused (nothing joined) or Busy (a part converts now:
    nothing joined, the queued join waits). Returns {'book_id', 'title', 'parts', 'queued', 'failed', 'requests',
    'approvals'}."""
    import book_restart
    import entered_names
    import groups
    import m4b_readmission
    from scanner import connect
    ids = _check_items(items)
    title = _words(title)
    author = _words(author)
    if not title:
        raise Refused('title', TITLE_NEEDED)
    parts, refusals = _parts(service, items, None)
    if refusals:
        first = refusals[0]
        raise Refused(first['cause'], 'Join cancelled: ' + _cause_text(first['cause'], first['title']) + ' Nothing was joined.', first['title'])
    by_id = {part['id']: part for part in parts}
    ordered = [by_id[identity] for identity in ids]
    root = ordered[0]['root']
    members = [{'path': m['path'], 'size': m['size'], 'modified': m['modified']} for part in ordered for m in part['row'].get('members') or []]
    paths = [m['path'] for m in members]
    if len(set(paths)) != len(paths) or not members:
        raise Refused('changed', 'Join cancelled: these books share files. Nothing was joined.')
    kept = tag_series(ordered)
    _value, _authors_found, series = _authors(service, ordered) if not kept else ('', [], {})
    names = _names(kept, bool(series))
    join_id = str(uuid.uuid4())
    group_scope = scope(paths, join_id)
    effects = {'queued': 0, 'failed': 0, 'requests': 0, 'approvals': 0}
    kind = None
    jobs = service.jobs
    with service.inventory.group_lock, connect(service.inventory.database) as db:
        db.execute('BEGIN IMMEDIATE')
        for part in ordered:
            current = db.execute('SELECT revision,superseded,approved,root FROM book_groups WHERE id=?', (part['id'],)).fetchone()
            if current is None or current['superseded']:
                raise Refused('gone', 'Join cancelled: ' + _cause_text('gone', part['title']) + ' Nothing was joined.', part['title'])
            if current['revision'] != part['revision'] or current['root'] != root:
                raise Refused('changed', 'Join cancelled: ' + _cause_text('changed', part['title']) + ' Nothing was joined.', part['title'])
            effects['approvals'] += approved(db, part['id'])
        groups.setup(db)
        book_restart.ensure(db)
        setup(db)
        # The parts' separate-volume facts (inferred, or kept by Keep as separate books) are replaced by his join.
        if _table(db, 'part_volumes'):
            db.executemany('DELETE FROM part_volumes WHERE root=? AND path=?', [(root, path) for path in paths])
        record(db, root, join_id, members, title)
        # The parts stop being books: their approvals and saved values go with them (as Keep as separate books and ruling
        # 71d's regroup drop a set's), so a part never comes back approved.
        marks = json.dumps(ids)
        db.execute("UPDATE book_groups SET review='',approved=0,changed=0,revision=revision+1 WHERE id IN (SELECT value FROM json_each(?))", (marks,))
        if _table(db, 'candidate_context'):
            db.execute('DELETE FROM candidate_context WHERE id IN (SELECT value FROM json_each(?))', (marks,))
        groups.sync(db, root)
        joined = db.execute('SELECT * FROM book_groups WHERE root=? AND scope=? AND superseded=0', (root, group_scope)).fetchone()
        if joined is None or [m['path'] for m in json.loads(joined['evidence'])['members']] != paths:
            raise Refused('failed', 'Join cancelled: these books could not be recorded as one book. Nothing was joined.')
        left = db.execute('SELECT count(*) FROM book_groups WHERE superseded=0 AND id IN (SELECT value FROM json_each(?))', (json.dumps(ids),)).fetchone()[0]
        if left:
            raise Refused('failed', 'Join cancelled: these books could not be recorded as one book. Nothing was joined.')
        row = {'id': joined['id'], 'members': [{'path': path} for path in paths]}
        entries = [('book', 'title', title, '', '', '')]
        if author:
            entries.append(('book', 'author', author, '', '', ''))
        if 'series' in names:
            entries += [('book', 'series', names['series'], '', '', ''), ('book', 'number', names['number'], '', '', '')]
        entered_names.save_in_transaction(db, row, entries)
        # Answer 8 (review): automatic processing holds the joined book for his approval, as a Save in Edit names does.
        context = {'names_approval_pending': {'revision': joined['revision'], 'fingerprint': joined['fingerprint']}, 'joined_by_you': {'join_id': join_id, 'at': _stamp()}}
        db.execute('CREATE TABLE IF NOT EXISTS candidate_context(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO candidate_context VALUES(?,?,?)', (joined['id'], joined['revision'], json.dumps(context, ensure_ascii=False)))
        # Last, under the conversion queue's lock until the commit: a part's job is either claimed before (Busy, nothing
        # joined) or sees the join (set aside, so it never starts). Not waited for: a press that holds that lock while it
        # waits for this transaction's writer would wait on us; it is tried again shortly instead.
        lock = getattr(jobs, '_lock', None)
        if lock is not None and not lock.acquire(timeout=5):
            raise Busy('The conversion queue is busy. The join waits its turn.')
        try:
            claimed, checking = (getattr(jobs, '_claimed', None), (dict(getattr(jobs, '_priority_status', None) or {}))) if jobs is not None else (None, {})
            checking = checking.get('job_id') if checking.get('state') == 'checking' else None
            now = _stamp()
            for part in ordered:
                found = facts(db, part['id'], claimed, checking)
                if found['state'] == 'converting':
                    raise Busy('«%s» is converting. The join waits its turn.' % part['title'])
                if found['state'] == 'finished':
                    raise Refused('finished', 'Join cancelled: ' + _cause_text('finished', part['title']) + ' Nothing was joined.', part['title'])
                effects['queued'] += found['queued']
                effects['failed'] += found['failed']
                effects['requests'] += found['request']
                kind = kind or found['request_kind']
                for job in found['jobs']:
                    if job['state'] == 'pending':
                        db.execute("UPDATE audio_jobs SET state='needs attention',reason=?,updated=? WHERE job_id=? AND state='pending'", (JOIN_REASON, now, job['job_id']))
                    db.execute('INSERT OR IGNORE INTO audio_job_set_aside VALUES(?,?,?,?,?)', (job['job_id'], part['id'], part['revision'], 'join', now))
                for parent, _child, _state, _kind in found['requests']:
                    m4b_readmission.withdraw(db, parent, time.time(), any_state=True)
            db.commit()
        finally:
            if lock is not None:
                lock.release()
    service.__dict__.pop('_needs_cache', None)
    invalidate = getattr(service, 'invalidate_status', None)
    if callable(invalidate):
        invalidate()
    return {'book_id': joined['id'], 'title': title, 'parts': len(ordered), 'request_kind': kind, **effects}
