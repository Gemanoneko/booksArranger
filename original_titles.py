"""Ruling 29 (Sergei 2026-10-26): when a translated book with only a Russian title converts.

- Written in Russian originally: it converts now, under the Russian title.
- Not written in Russian: it waits for the English original title, then converts under it.
- If no English title can be found: it converts under the Russian title.

Locally the app knows a book is a translation when the library writes its author in Latin letters (the folder language
rule of ruling 3: Russian authors in Cyrillic, everyone else in English), and the title it read is Cyrillic. Such a book
is held "Waiting for the original title" (public_research._local_lookup) while the background pass asks the sources once
(gap_fill.GapFill, in its own lane); research then reads the answer recorded here. One record per work (title and
author), so the same work found again under other files is not asked twice. Sergei's Approve, or the English title he
types, ends the wait at once (rulings 6a and 6b).

States: 'waiting' (to be asked), 'deferred' (a source was closed; asked again at next_attempt), 'found' (an English
original title: record['title'], record['language']), 'russian' (the sources say it was written in Russian), 'none'
(no English title: nothing found, or an original in another language).
"""
import hashlib
import json
import time

from scanner import connect

TABLE = ('CREATE TABLE IF NOT EXISTS original_titles(key TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, title TEXT NOT NULL, '
         'author TEXT NOT NULL, state TEXT NOT NULL, record TEXT NOT NULL, updated TEXT NOT NULL)')
FINAL = ('found', 'russian', 'none')
WAIT_REASON = 'Waiting for the original title'
RESEARCH_AGAIN = 900  # seconds: research reads this table again even if no pass has woken it


def _stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def key(title, author):
    import local_identity
    return hashlib.sha256(json.dumps([local_identity.title_key(title), ' '.join(sorted(local_identity.words(author)))], ensure_ascii=False).encode('utf-8')).hexdigest()


def setup(db):
    db.execute(TABLE)


def entry(database, title, author):
    """The recorded lookup of this work, or None."""
    with connect(database) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='original_titles'").fetchone():
            return None
        row = db.execute('SELECT * FROM original_titles WHERE key=?', (key(title, author),)).fetchone()
    if row is None:
        return None
    value = dict(row)
    value['record'] = json.loads(value['record'] or '{}')
    return value


def want(database, candidate_id, title, author):
    """Ask the background pass about this work (once): a 'waiting' record, unless one exists. Returns False when the
    catalog is busy behind another writer: the only write research makes must not fail the book's research (T2 of the
    SQLITE_BUSY fix); the book still waits, and its next research (RESEARCH_AGAIN) asks again."""
    from public_research import catalog_busy
    try:
        with connect(database, timeout=1) as db:  # never long behind another writer (research waits for nothing)
            setup(db)
            db.execute('INSERT OR IGNORE INTO original_titles VALUES(?,?,?,?,?,?,?)', (key(title, author), candidate_id, title, author, 'waiting', '{}', _stamp()))
    except Exception as error:
        if not catalog_busy(error):
            raise
        return False
    return True


def record(database, title, author, state, value):
    with connect(database) as db:
        setup(db)
        current = db.execute('SELECT candidate_id FROM original_titles WHERE key=?', (key(title, author),)).fetchone()
        db.execute('INSERT OR REPLACE INTO original_titles VALUES(?,?,?,?,?,?,?)',
                   (key(title, author), current[0] if current else '', title, author, state, json.dumps(value, ensure_ascii=False), _stamp()))


def due(database, clock=time.time):
    """The lookups to ask now: waiting ones, and deferred ones whose source should be open again."""
    with connect(database) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='original_titles'").fetchone():
            return []
        rows = [dict(r) for r in db.execute("SELECT * FROM original_titles WHERE state IN ('waiting','deferred') ORDER BY updated")]
    result = []
    for row in rows:
        row['record'] = json.loads(row['record'] or '{}')
        if row['state'] == 'deferred' and (row['record'].get('next_attempt') or 0) > clock():
            continue
        result.append(row)
    return result


def outcome(found):
    """(state, record) from a background lookup's answer (public_research.fill_gaps)."""
    import local_identity
    catalog = (found or {}).get('catalog') or {}
    language = str(catalog.get('language') or '')
    original = local_identity.text(catalog.get('original_title') or '')
    receipt = {'language': language, 'source_url': catalog.get('source_url', ''), 'author_latin': catalog.get('author_latin', '')}
    if language == 'ru':
        return 'russian', receipt
    if original and language == 'en' and local_identity.script(original) == 'latin':
        return 'found', dict(receipt, title=original)
    return 'none', dict(receipt, original=original)


def translation(title, author):
    """True when a book waits for its English original title: the title read is Cyrillic and the author is written in
    Latin letters (a writer in another language, the library's folder language rule)."""
    import local_identity
    return local_identity.script(title) == 'cyrillic' and local_identity.script(author) == 'latin'
