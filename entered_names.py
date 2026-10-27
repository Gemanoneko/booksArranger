"""Edit names (Sergei 2026-10-26; Judy 0.22.2 section 1): every book row lets Sergei correct its title, author, series,
number, universe and collection, and the correction lasts.

- A saved value is Sergei's (ruling 6a, "Entered by you") and belongs to the book's files (book_key: its member paths), so
  it survives a new scan, a regroup and a Retry. Research and Approve use it before anything the files say.
- A name fix reaches every book that reads the same text under the same author (or, for a collection or a book with no
  author, the same folder): «Пртоколы» typed as «Протоколы» once fixes the other books of that folder. A title is never
  fixed across authors. A one-word spelling change inside a longer name is remembered as that word ("Пртоколы" ->
  "Протоколы"), anything else as the whole value. Authors keep their own rules (author_rules): an author is never a fix.
- The same text means the same characters, digits included, ignoring only case and spacing (Senua's 0.22.2 review, M1):
  a fix of King's «01» never reaches «1408», and «Книга 1» never «Книга 12». A word fix never changes a number.
- Append-only, as the author rules: a newer entry wins (insertion order); Forget is a newer row that takes one back, and
  takes back the whole press it belongs to (the book's value and the fix saved with it).
- A field set back to what the files say is no correction for this book (M2): a 'files' entry (kind book, scope
  FILES) says so. It is newer than every earlier value of the field, so none comes back, and no fix reaches that field
  of this book; it is never "Entered by you" and never listed. A fix saved from this book still reaches the others
  (Forget takes it back from all of them).

Values: title, author, series, number, universe (text) and collection (bool). Nothing here touches a file or a job.
"""
import hashlib
import json
import os
import re
import time
import uuid

from scanner import connect

FIELDS = ('title', 'author', 'series', 'number', 'universe', 'collection')
FIXED = ('title', 'series', 'universe')  # the names a fix may reach other books with
FILES = 'files'  # the scope of a book entry that sets a field back to what the files say (no correction)
TABLE = ('CREATE TABLE IF NOT EXISTS names_entries(entry_id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN (\'book\',\'fix\',\'forget\')), '
         'book_key TEXT NOT NULL DEFAULT \'\', field TEXT NOT NULL DEFAULT \'\', value TEXT NOT NULL DEFAULT \'\', source TEXT NOT NULL DEFAULT \'\', '
         'scope TEXT NOT NULL DEFAULT \'\', candidate_id TEXT NOT NULL DEFAULT \'\', retracts TEXT NOT NULL DEFAULT \'\', press TEXT NOT NULL DEFAULT \'\', '
         'saved_utc TEXT NOT NULL)')
TRIGGERS = ("CREATE TRIGGER IF NOT EXISTS names_entries_no_update BEFORE UPDATE ON names_entries BEGIN SELECT RAISE(ABORT,'names_entries is append-only'); END",
            "CREATE TRIGGER IF NOT EXISTS names_entries_no_delete BEFORE DELETE ON names_entries BEGIN SELECT RAISE(ABORT,'names_entries is append-only'); END")
COLUMNS = '(entry_id, kind, book_key, field, value, source, scope, candidate_id, retracts, press, saved_utc)'


def _stamp():
    now = time.time()
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(now)) + '.%06dZ' % (int(now * 1e6) % 1000000)


def _text(value):
    return ' '.join(str(value or '').split())[:1000]


def setup(db):
    db.execute(TABLE)
    for trigger in TRIGGERS:
        db.execute(trigger)


def book_key(row):
    """The book's files: its member paths, case-folded and sorted (a regroup of the same files keeps the key)."""
    paths = sorted(os.path.normcase(str(m['path'])) for m in row.get('members') or [])
    return hashlib.sha256(json.dumps(paths, ensure_ascii=False).encode('utf-8')).hexdigest()


def _same(value):
    """The text a whole-value fix compares: case and spacing ignored, every other character kept (digits too). Empty
    for an empty value, which never matches (Senua's 0.22.2 review, M1: local_identity.words() drops digits, so "01"
    matched «1408» and "Книга 1" matched "Книга 12")."""
    return _text(value).casefold()


def _files(entry):
    return entry['kind'] == 'book' and entry.get('scope') == FILES


def scope_of(row, author, collection=False):
    """Where a fix from this book reaches: its author (key), or for a collection or a book with no author, its folder."""
    from author_rules import key
    if author and not collection:
        return 'author:' + key(author)
    members = row.get('members') or []
    folder = os.path.dirname(str(members[0]['path'])) if members else ''
    return 'folder:' + os.path.normcase(folder)


def _rows(database):
    with connect(database) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='names_entries'").fetchone():
            return []
        return [dict(r) for r in db.execute('SELECT * FROM names_entries ORDER BY rowid')]


def _live(rows):
    """The entries still in force: forgets take theirs back; per book and field (or per fix key) the newest wins."""
    gone = {r['retracts'] for r in rows if r['kind'] == 'forget'}
    newest = {}
    for r in rows:
        if r['kind'] == 'forget' or r['entry_id'] in gone:
            continue
        slot = ('book', r['book_key'], r['field']) if r['kind'] == 'book' else ('fix', r['field'], _same(r['source']), r['scope'])
        newest.pop(slot, None)
        newest[slot] = r
    return list(newest.values())


def _fix_applies(fix, field, value, scope):
    """The value a fix turns this read value into, else None."""
    if fix['field'] != field or fix['scope'] != scope or not value:
        return None
    if _same(value) and _same(value) == _same(fix['source']):
        return fix['value']
    # A word fix: the misspelled word replaced wherever it stands as a whole word ("Пртоколы SCP. Сейф №1").
    if len(fix['source'].split()) == 1 and len(fix['value'].split()) == 1:
        pattern = re.compile(r'(?<![^\W_])' + re.escape(fix['source']) + r'(?![^\W_])', re.I)
        if pattern.search(value):
            return pattern.sub(lambda _: fix['value'], value)
    return None


def effective(database, row, read, scope, rows=None):
    """{field: {'value', 'entry', 'source', 'saved', 'fix'?}} Sergei's values for this book: his entries for its files,
    else what a fix makes of the values read (read: {field: text}). scope: scope_of() for the book."""
    live = _live(_rows(database) if rows is None else rows)
    key = book_key(row)
    found, files = {}, set()
    for r in live:
        if r['kind'] == 'book' and r['book_key'] == key and r['field'] in FIELDS:
            if _files(r):
                files.add(r['field'])  # set back to what the files say: no correction, no fix (M2)
                continue
            value = r['value'] == 'true' if r['field'] == 'collection' else r['value']
            found[r['field']] = {'value': value, 'entry': r['entry_id'], 'source': r['source'], 'saved': r['saved_utc']}
    for r in live:
        if r['kind'] != 'fix' or r['field'] in found or r['field'] in files:
            continue
        fixed = _fix_applies(r, r['field'], read.get(r['field'], ''), scope)
        if fixed is not None:
            found[r['field']] = {'value': fixed, 'entry': r['entry_id'], 'source': r['source'], 'fix': True, 'saved': r['saved_utc']}
    return found


def relevant(row, rows):
    """The ids of the entries in force that may reach this book (may_apply's test), sorted."""
    live = _live(rows)
    key = book_key(row)
    found = [r['entry_id'] for r in live if r['kind'] == 'book' and r['book_key'] == key]
    fixes = [r for r in live if r['kind'] == 'fix' and r['source']]
    if fixes:
        hay = [str(row.get('title_clue') or '')]
        for member in row.get('members') or []:
            hay.append(str(member.get('path') or ''))
            hay.extend(str(v) for v in ((member.get('metadata') or {}).get('tags') or {}).values())
        hay = ' '.join(hay).casefold()
        found += [r['entry_id'] for r in fixes if str(r['source']).casefold() in hay]
    return sorted(found)


def digest_for(database, row, rows=None):
    """The book's names stamp, stored with its job (metadata_facts.entered_names.digest): the entries in force that may
    reach it. Read-only, from the book's files and the store alone (no identity read), so research and the queue's claim
    check compute the same value; NONE when nothing may reach it. A job whose stamp is not the book's now was planned
    under other names (a Save or a Forget since) and never starts (AudioJobs' claim check)."""
    ids = relevant(row, _rows(database) if rows is None else rows)
    return hashlib.sha256(json.dumps(ids).encode('utf-8')).hexdigest()[:32]


NONE = hashlib.sha256(json.dumps([]).encode('utf-8')).hexdigest()[:32]


def stamp(database):
    """(rows, newest) of the store: any Save or Forget changes it. Read-only, cheap."""
    with connect(database) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='names_entries'").fetchone():
            return (0, '')
        return tuple(db.execute("SELECT count(*), coalesce(max(saved_utc), '') FROM names_entries").fetchone())


def may_apply(database, row, rows=None):
    """False when no entry in force can reach this book: no entry for its files, and no fix whose old text appears in its
    folder, file names, title clue or tags. Cheap (no identity read); True means "read the identity to know"."""
    return bool(relevant(row, _rows(database) if rows is None else rows))


def book_values(database, row, rows=None):
    """{field: value} Sergei saved for this book's files (stored values only, no read): the list's Place and Entered
    lines."""
    key = book_key(row)
    found = {}
    for r in _live(_rows(database) if rows is None else rows):
        if r['kind'] == 'book' and r['book_key'] == key and r['field'] in FIELDS and not _files(r):
            found[r['field']] = r['value'] == 'true' if r['field'] == 'collection' else r['value']
    return found


def entered(values):
    """The fields of book_values() in editor order (the row's "Entered by you: title, series." line)."""
    return [field for field in FIELDS if field in values]


def in_use(database, field):
    """Values of series or universe Sergei has entered (one source of the editor's pick-lists)."""
    return sorted({r['value'] for r in _live(_rows(database)) if r['field'] == field and r['kind'] in ('book', 'fix') and r['value'] and not _files(r)}, key=str.casefold)


def remembered(database, row, read, scope):
    """[{id, field, from, to}] the corrections in force for this book, for the editor's list (Judy 1.5)."""
    values = effective(database, row, read, scope)
    return [{'id': item['entry'], 'field': field, 'from': item.get('source', ''), 'to': item['value'] if field != 'collection' else ('true' if item['value'] else 'false')}
            for field, item in sorted(values.items(), key=lambda pair: FIELDS.index(pair[0]))]


def _word_fix(old, new):
    """('Пртоколы', 'Протоколы') when new is old with one word respelled (a near spelling), else None."""
    a, b = str(old).split(), str(new).split()
    if len(a) != len(b) or len(a) < 2:
        return None
    changed = [(x, y) for x, y in zip(a, b) if x != y]
    if len(changed) != 1:
        return None
    x, y = (re.sub(r'^\W+|\W+$', '', w) for w in changed[0])
    import local_identity
    if not x or not y or len(x) < 4 or local_identity._edits(x.casefold(), y.casefold(), 3) > 2:
        return None
    if re.findall(r'\d+', x) != re.findall(r'\d+', y):
        return None  # M1: another number is no spelling fix ("Том1" -> "Том2" stays this book's whole value)
    return x, y


def check(values):
    """Judy 1.3 and 1.6: a title is needed; Series and Number go together (the planner refuses an invented number).
    Raises ValueError with the sentence the row shows."""
    for field, value in values.items():
        if field not in FIELDS:
            raise ValueError('Unknown name field')
        if field == 'collection':
            if type(value) is not bool:
                raise ValueError('Collection must be an explicit boolean')
        elif not isinstance(value, str) or len(value) > 1000 or any(c in value for c in '\x00\r\n'):
            raise ValueError('The ' + field + ' must be one line of text')
    if 'title' in values and not _text(values['title']):
        raise ValueError('Type a title first.')
    series, number = _text(values.get('series', '')), _text(values.get('number', ''))
    if 'series' in values or 'number' in values:
        if series and not number:
            raise ValueError('Type the number in the series, or clear the series.')
        if number and not series:
            raise ValueError('Type the series name, or clear the number.')


def plan(row, values, read, scope, now=None):
    """The entries a Save would write: [(kind, field, value, source, scope, retracts)]. values: the editor's values; read:
    what the files say (before any correction); now: effective() for the book, so an unchanged field writes nothing and
    a field set back to what the files say writes a 'files' entry: no correction for this book, none of its earlier
    values comes back and no fix reaches it (Senua's 0.22.2 review, M2; a fix saved from it still reaches the others).
    Authors never become fixes (they keep their own rules)."""
    now = now or {}
    entries = []
    for field in FIELDS:
        if field not in values:
            continue
        new = bool(values[field]) if field == 'collection' else _text(values[field])
        old = bool(read.get(field)) if field == 'collection' else _text(read.get(field, ''))
        current = now[field]['value'] if field in now else old
        current = bool(current) if field == 'collection' else _text(current)
        if new == current:
            continue
        stored = ('true' if new else 'false') if field == 'collection' else new
        if new == old:
            # Typed back to the files' own text (M2): it used to forget only the newest entry, so an older one came back.
            entries.append(('book', field, stored, '' if field == 'collection' else old, FILES, ''))
            continue
        entries.append(('book', field, stored, '' if field == 'collection' else old, '', ''))
        if field in FIXED and old and new and new != old:
            word = _word_fix(old, new)
            entries.append(('fix', field, word[1] if word else new, word[0] if word else old, scope, ''))
    return entries


def save(database, row, entries):
    """Write plan()'s entries in one transaction, as one press. Returns the press id ('' when nothing was written)."""
    if not entries:
        return ''
    press = uuid.uuid4().hex
    with connect(database) as db:
        setup(db)
        db.execute('BEGIN IMMEDIATE')
        for kind, field, value, source, where, retracts in entries:
            db.execute('INSERT INTO names_entries ' + COLUMNS + ' VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (uuid.uuid4().hex, kind, book_key(row) if kind == 'book' else '', field, value, source, where, row.get('id', ''), retracts, press, _stamp()))
    return press


def forget(database, entry_id):
    """Take one entry back, with the rest of the press it was saved in (the book's value and the fix saved with it, so
    the books the fix reached go back too). Returns the ids taken back; [] when it was no longer in force."""
    rows = _rows(database)
    live = {r['entry_id']: r for r in _live(rows)}
    target = live.get(entry_id)
    if target is None:
        return []
    taken = [entry_id] + [r['entry_id'] for r in live.values() if r['entry_id'] != entry_id and target['press'] and r['press'] == target['press']
                          and r['field'] == target['field']]
    press = uuid.uuid4().hex
    with connect(database) as db:
        setup(db)
        db.execute('BEGIN IMMEDIATE')
        for item in taken:
            db.execute('INSERT INTO names_entries ' + COLUMNS + ' VALUES(?,?,?,?,?,?,?,?,?,?,?)', (uuid.uuid4().hex, 'forget', '', '', '', '', '', '', item, press, _stamp()))
    return taken


def reach(entries, others):
    """The other books a press's fixes would change: [row] of others ([(row, read, scope)], the current books read) whose
    read value a fix turns into another."""
    fixes = [{'field': field, 'value': value, 'source': source, 'scope': where} for kind, field, value, source, where, _ in entries if kind == 'fix']
    if not fixes:
        return []
    return [other for other, read, where in others
            if any(_fix_applies(fix, fix['field'], read.get(fix['field'], ''), where) not in (None, read.get(fix['field'], '')) for fix in fixes)]
