"""0.30.0 sorting moves (Sergei 2026-11-18, backlog "Why books aren't sorted — library-wide", items 2, 5 and 6): books
already in Audiobooks Sorted that are not where the app files them now.

  item 2  a series found after publication (series backfill) files the book in its series folder; 81 books were held
          because the series folder is another folder than the one the book was published in;
  item 5  one author folder per author (canonical_names.author: a rule's name, or the same words surname first);
  item 6  the series in the language it was written in (canonical_names.series_in_original, from the FantLab cycle
          research cited).

Nothing here moves a book by itself. plan() lists every book that would move (current path -> new path, the items, or
why it is left as it is) and a digest of that list; a book moves only after Sergei's explicit approval of that exact list
(MergeService.sorting_moves_apply with the digest he saw). New books simply get the right path when they are converted.
A move is the app's usual verified move (book_move: the exact held file hashed, a no-replace rename or a verified copy,
journaled; the old folder removed only when empty). A book that needs its series written into the file first goes
through series backfill (retag in its folder, verified), and only then moves into its series folder (series_backfill
follow-up).

plan() reads the catalog and, for each listed book, whether its file and its target exist (os.path.lexists). It opens no
audio file and writes nothing."""
import copy
import hashlib
import json
import ntpath
import os

SCHEMA = 'books-sorting-moves-v1'
ITEMS = {'series': 'Item 2: series found after publication', 'author': 'Item 5: one author folder per author',
         'series_language': 'Item 6: series name in the original language'}
# series_backfill reasons that mean "a series was found and the book's series folder is another folder".
SERIES_FOLDER_REASONS = ('The recorded series paths do not share their original parent',)


def key(path):
    return ntpath.normcase(ntpath.normpath(str(path or '')))


def _inside(path, root):
    return bool(root) and key(path).startswith(key(root).rstrip('\\') + '\\')


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _entered(facts, field):
    names = (facts or {}).get('entered_names') or {}
    return field in (names.get('fields') or [])


def canonical(db, manifest, rules, series=None):
    """(review, facts, reasons, notes) for a finished book as the app files it now: its manifest's names with item 5 (the
    author's folder) and item 6 (the series' language) applied, and series (item 2: {'name','number','provider',
    'source_url'}) added when given. reasons: the items that changed something; notes: why, in words."""
    import canonical_names
    review = dict(manifest.get('metadata') or {})
    facts = copy.deepcopy(manifest.get('metadata_facts')) if isinstance(manifest.get('metadata_facts'), dict) else None
    reasons, notes = [], []
    if series:
        review.update(series=series['name'], number=str(series['number']))
        if facts is not None:
            facts['series_state'] = 'verified'
        reasons.append('series')
        notes.append('series %s %s (%s)' % (series['name'], series['number'], series.get('provider') or 'source'))
    credit = review.get('author') or review.get('canonical_author') or ''
    if credit and not _entered(facts, 'author') and not review.get('anthology') and not review.get('multi_author'):
        # Senua's 0.30.0 review, m2: a rule scoped to a folder counts in the book's own (source) folder.
        sources = manifest.get('sources') or [{}]
        folder = ntpath.dirname(str((sources[0] if isinstance(sources[0], dict) else {}).get('path') or ''))
        filed, why = canonical_names.author(credit, rules, folder)
        if filed and filed != credit:
            review['author'] = filed
            if review.get('canonical_author') == credit:
                review['canonical_author'] = filed
            if facts is not None and facts.get('authors') == [credit]:
                facts['authors'] = [filed]
            reasons.append('author')
            notes.append('author folder "%s" (%s)' % (filed, why))
    # Futaba's 0.30.0 QA, C1: a book whose language is Unknown (HP 1) was looked at only when 'Other', so the plan showed
    # «Гарри Поттер» until a re-lookup. FantLab's own cycle decides (its language and original name, series_in_original);
    # only a book recorded as a Russian original keeps its name without asking.
    if review.get('series') and review.get('original_language') != 'Russian' and not _entered(facts, 'series'):
        source = (facts or {}).get('series_source') or {}
        provider = (series or {}).get('provider') or source.get('provider')
        url = (series or {}).get('source_url') or source.get('url') or source.get('source_url')
        named, why = canonical_names.series_in_original(db, review['series'], provider, url)
        if named != review['series']:
            review['series'] = named
            if 'series' not in reasons:
                reasons.append('series_language')
            notes.append('series "%s" (%s)' % (named, why))
    return review, facts, reasons, notes


def target(db, row, rules, output_root, series=None, placed=None, effective=None):
    """{'job_id', 'from', 'to', 'items', 'why'} for one completed job (an audio_jobs row), or {'refused': reason} with
    'from', or None when the book is where the app files it. placed: series backfill wrote this approved book's series
    under its new name in its own folder (item 2); the book is expected exactly there and goes on to its series folder.
    effective: where the book's last move took it (None: never moved); a moved book is planned no further: None when it
    is where the app files it now (an approved move took it there), else left where it was moved to."""
    from metadata import propose
    from series_backfill import published_root
    manifest = json.loads(row['manifest'])
    output = json.loads(row['output'])
    current = output.get('final_path') or ''
    found = {'job_id': row['job_id'], 'from': current}
    root = str(published_root(manifest, output))
    review, facts, reasons, notes = canonical(db, manifest, rules, series)
    if placed and not reasons:
        reasons, notes = ['series'], ['its series folder']
    if not reasons:
        return None
    if series:
        found['series'] = {'name': review['series'], 'number': review['number'], 'provider': series.get('provider') or '',
                           'source_url': series.get('source_url') or ''}
    if not _inside(current, output_root) or not _inside(root, output_root) and key(root) != key(output_root):
        return dict(found, refused='Not in Audiobooks Sorted; left as it is', items=reasons)
    if (facts or {}).get('destination_override'):
        return dict(found, refused='You chose its folder; left as it is', items=reasons)
    try:
        now = propose('', root, 'audiobook', {}, manifest['metadata'], automatic_facts=copy.deepcopy(manifest.get('metadata_facts')))
        wanted = propose('', root, 'audiobook', {}, review, automatic_facts=facts)
    except (ValueError, KeyError, TypeError) as error:
        return dict(found, refused='No name for it: ' + (str(error) or type(error).__name__), items=reasons)
    if effective is not None:
        if effective and wanted.get('path') and key(effective) == key(wanted['path']):
            return None
        return dict(found, refused='Already moved to a folder you chose; left as it is', items=reasons)
    if placed:
        if key(placed) != key(current):
            return dict(found, refused='The audiobook is not where its series update put it; left as it is', items=reasons)
    elif not now.get('path') or key(now['path']) != key(current):
        return dict(found, refused="Its name does not follow the app's naming; left as it is", items=reasons)
    if not wanted.get('path'):
        return dict(found, refused='No name for it: ' + (wanted.get('reason') or 'unknown'), items=reasons)
    if key(wanted['path']) == key(current):
        return None
    return dict(found, to=wanted['path'], items=reasons, why='; '.join(notes))


def _moved(db, job_id):
    """None when the book was never moved; else the final path of its last effective move ('' while one is unfinished)."""
    import book_move
    if not book_move.have(db):
        return None
    rows = db.execute("SELECT state,final_json FROM book_moves WHERE job_id=? AND state NOT IN ('failed','cancelled') ORDER BY generation", (job_id,)).fetchall()
    if not rows:
        return None
    state, final = rows[-1]
    try:
        return (json.loads(final) or {}).get('final_path') or '' if state in book_move.EFFECTIVE and final else ''
    except (TypeError, ValueError):
        return ''


# 0.31.0 step 4d (Judy's BooksArranger_0.31.0_UX.md, section 3 and Notes for Ender): what a page control needs beside the
# 0.30.0 plan, all additive (the digest signs the same four values per book as before). Every item and refusal also carries
# 'book_id', 'title', 'author', 'from_shown' and 'to_shown' (the paths under Audiobooks Sorted), 'kept' (False: keeping a
# book where it is has no engine yet) and 'approved_not_moved' (None, or {'key', 'reason'}: he approved this move and it
# could not run; the book is listed again, never dropped in silence). A refusal carries 'refused_key', the reason as a
# key the page words (REFUSAL_KEYS; 'other' for a sentence with no key).
REFUSAL_KEYS = (('name_exists', ('A file with the new name is already there',)), ('same_target', ('Another listed book would get the same name',)),
                ('chosen_folder', ('You chose its folder', 'Already moved to a folder you chose')), ('not_in_sorted', ('Not in Audiobooks Sorted',)),
                ('not_app_name', ("Its name does not follow the app's naming",)),
                ('not_where_recorded', ('The audiobook is not where the catalog says', 'The audiobook is not where its series update put it')),
                ('newer_version', ('Part of a replacement or a newer version',)), ('kept_files', ('Files kept at your choice',)),
                ('data_move', ('Kept as published while the data folder move is unfinished',)), ('sources_disagree', ('Series sources need review',)),
                ('no_name', ('No name for it', 'Could not be planned')))
NOT_MOVED_KEYS = (('file_changed', ('The book changed since you approved', 'The published audiobook changed', 'no longer matches')),
                  ('place_changed', ('The planned place changed',)), ('name_exists', ('A file with the series name already exists',)))


def reason_key(text, table=REFUSAL_KEYS):
    """The key of a refusal sentence, 'other' when it has none."""
    text = str(text or '')
    return next((name for name, marks in table if any(mark in text for mark in marks)), 'other')


def _shown(path, output_root):
    """The path under Audiobooks Sorted, as the page shows it; the whole path when it is not inside."""
    path = str(path or '')
    return path[len(str(output_root).rstrip('\\/')) + 1:] if _inside(path, output_root) else path


def _held_series(db):
    """{job_id: {'name','number','provider','source_url'}}: series backfill found a series and held the book only because its
    series folder is another folder (item 2), or holds it for Sergei's approval of that move. 0.31.0 (Judy 3.3): also a book
    whose approved move then could not run (record 'approved_failed'): it comes back to the list, with why ('failed')."""
    import series_backfill
    if not _table(db, 'series_backfill'):
        return {}
    found = {}
    reasons = SERIES_FOLDER_REASONS + (series_backfill.MOVE_WAITS,)
    for job_id, reason, record in db.execute("SELECT job_id,reason,record FROM series_backfill WHERE state='held'"):
        try:
            record = json.loads(record)
        except (TypeError, ValueError):
            continue
        failed = record.get('approved_failed') if isinstance(record.get('approved_failed'), dict) else None
        if reason not in reasons and not failed:
            continue
        approved = record.get('approved_found') if isinstance(record.get('approved_found'), dict) else {}
        name, number = record.get('series') or approved.get('name'), str(record.get('number') or approved.get('number') or '').strip()
        if name and number:
            found[job_id] = {'name': name, 'number': number, 'provider': record.get('provider') or approved.get('provider') or '',
                             'source_url': record.get('source_url') or approved.get('source_url') or ''}
            if failed:
                found[job_id]['failed'] = str(failed.get('reason') or reason)
    return found


def _placed_series(db):
    """{job_id: the path series backfill wrote it at}: an approved book whose series is written in its own folder under its
    new name (item 2) and that still waits for, or lost, its move into the series folder."""
    if not _table(db, 'series_backfill'):
        return {}
    found = {}
    for job_id, record in db.execute("SELECT job_id,record FROM series_backfill WHERE state='done'"):
        try:
            record = json.loads(record)
        except (TypeError, ValueError):
            continue
        if isinstance(record, dict) and record.get('move_approved') and record.get('new_path'):
            found[job_id] = record['new_path']
    return found


RETAINED = 'Kept as published while the data folder move is unfinished; left as it is'
SAME_TARGET = 'Another listed book would get the same name; left as it is'


def plan(db, output_root, rules=None, exists=os.path.lexists, retained=frozenset()):
    """Every finished book in Audiobooks Sorted that the app now files elsewhere: {'schema', 'output_root', 'items': [...],
    'refused': [...], 'counts', 'digest'}. An item: {'job_id', 'from', 'to', 'items', 'why'}; a refusal: {'job_id', 'from',
    'refused', 'items'}. Read only (the catalog; exists() on the listed paths). retained: the retained jobs of a catalog in
    retained-runtime mode (storage_relocation_native.retained_job_ids); each is left as published (Senua's 0.30.0 review,
    M3, as series backfill and the other passes leave them)."""
    items, refused = [], []
    if not output_root or not _table(db, 'audio_jobs'):
        return _answer(output_root, items, refused)
    newest = {}
    for job_id, candidate in db.execute("SELECT job_id,json_extract(manifest,'$.candidate_id') FROM audio_jobs ORDER BY created,job_id"):
        newest[candidate] = job_id
    replaced = set()
    if _table(db, 'audiobook_replacements'):
        replaced = {r[0] for r in db.execute('SELECT parent_job_id FROM audiobook_replacements')} | {r[0] for r in db.execute('SELECT replacement_job_id FROM audiobook_replacements')}
    kept = {r[0] for r in db.execute('SELECT job_id FROM kept_files')} if _table(db, 'kept_files') else set()
    series = _held_series(db)
    # Futaba's 0.30.0 slice C delta: an approved book whose series was written in its own folder and whose move into the
    # series folder then failed for good (a stranger file at the target) read as "where the app files it" and got no line:
    # stuck in silence. It is planned from where series backfill put it: listed again, or refused with the reason.
    placed = _placed_series(db)
    rows = db.execute("SELECT job_id,manifest,output FROM audio_jobs WHERE state='completed' AND output IS NOT NULL ORDER BY job_id").fetchall()
    for row in rows:
        row = {'job_id': row[0], 'manifest': row[1], 'output': row[2]}
        try:
            manifest = json.loads(row['manifest'])
            output = json.loads(row['output'])
        except (TypeError, ValueError):
            continue
        if newest.get(manifest.get('candidate_id')) != row['job_id'] or manifest.get('replacement_id') or manifest.get('replacement_parent_job_id'):
            continue
        if __import__('publication_reuse').task(manifest):
            continue
        current = output.get('final_path') or ''
        if not _inside(current, output_root) and row['job_id'] not in series:
            # Outside Sorted (a book published into its library before 0.13.0): listed only when it would change.
            found = target(db, row, rules, output_root)
            if found:
                refused.append(dict(found, refused=found.get('refused') or 'Not in Audiobooks Sorted; left as it is', to=None))
            continue
        try:
            # A moved book: the receipt keeps the published place, the move chain the new one (book_move).
            found = target(db, row, rules, output_root, series.get(row['job_id']), placed=placed.get(row['job_id']), effective=_moved(db, row['job_id']))
        except Exception as error:  # one malformed record never hides the others
            refused.append({'job_id': row['job_id'], 'from': current, 'refused': 'Could not be planned: ' + (str(error) or type(error).__name__)[:200], 'items': []})
            continue
        if not found:
            continue
        failed = (series.get(row['job_id']) or {}).get('failed')
        if failed:
            found['approved_not_moved'] = {'key': reason_key(failed, NOT_MOVED_KEYS), 'reason': failed}
        if row['job_id'] in placed and 'to' in found:
            found['placed'] = True  # its series is in the file already: an approval only moves it (sorting_moves_apply)
            found['approved_not_moved'] = {'key': 'other', 'reason': 'Its series was written; the move into its series folder did not run'}
        if 'refused' not in found:
            why = (RETAINED if row['job_id'] in retained else
                   'Part of a replacement or a newer version; left as it is' if row['job_id'] in replaced else
                   'Files kept at your choice; left as they are' if row['job_id'] in kept else
                   'The audiobook is not where the catalog says' if not exists(found['from']) else
                   'A file with the new name is already there' if exists(found['to']) else '')
            if why:
                found = dict(found, refused=why)
        (refused if 'refused' in found else items).append(found)
    # Senua's 0.30.0 review, m3: two listed books with one target would leave the second move failing at run time (the
    # move never overwrites); the list Sergei approves must be one that can run whole, so neither is listed to move.
    targets = {}
    for item in items:
        targets.setdefault(key(item['to']), []).append(item)
    clash = {id(item) for group in targets.values() if len(group) > 1 for item in group}
    refused += [dict(item, refused=SAME_TARGET) for item in items if id(item) in clash]
    items = [item for item in items if id(item) not in clash]
    # 0.31.0 step 4d: what the page's list shows per book (one catalog read for every listed book).
    listed = items + refused
    names = {}
    if listed:
        names = {r[0]: (r[1], r[2] or '', r[3] or r[4] or '') for r in db.execute(
            "SELECT job_id,json_extract(manifest,'$.candidate_id'),json_extract(manifest,'$.metadata.title'),json_extract(manifest,'$.metadata.canonical_author'),"
            "json_extract(manifest,'$.metadata.author') FROM audio_jobs WHERE job_id IN (SELECT value FROM json_each(?))", (json.dumps([i['job_id'] for i in listed]),))}
    for item in listed:
        book_id, title, author = names.get(item['job_id'], (None, '', ''))
        item.update(book_id=book_id, title=title, author=author, from_shown=_shown(item.get('from'), output_root),
                    to_shown=_shown(item.get('to'), output_root) if item.get('to') else None, kept=False)
        item.setdefault('approved_not_moved', None)
        if 'refused' in item:
            item['refused_key'] = reason_key(item['refused'])
    return _answer(output_root, items, refused)


def _answer(output_root, items, refused):
    items = sorted(items, key=lambda i: (i['from'].casefold(), i['job_id']))
    refused = sorted(refused, key=lambda i: (str(i.get('from') or '').casefold(), i['job_id']))
    counts = {name: sum(1 for i in items if name in i['items']) for name in ITEMS}
    counts.update(moves=len(items), refused=len(refused))
    refused_counts = {name: sum(1 for i in refused if name in (i.get('items') or [])) for name in ITEMS}
    signed = [[i['job_id'], i['from'], i['to'], i['items']] for i in items]
    digest = hashlib.sha256(json.dumps([SCHEMA, str(output_root or ''), signed], ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
    return {'schema': SCHEMA, 'output_root': str(output_root or ''), 'items': items, 'refused': refused, 'counts': counts,
            'refused_counts': refused_counts, 'digest': digest}


def markdown(answer, title='Books Arranger 0.30.0: sorting moves (dry run)', note=''):
    """The list as Markdown for Sergei: current path -> new path, the items, and each refusal."""
    lines = ['# ' + title, '']
    if note:
        lines += [note, '']
    counts, refused_counts = answer['counts'], answer['refused_counts']
    lines += ['Output folder: `%s`' % answer['output_root'], '', 'Plan digest: `%s`' % answer['digest'], '', '## Counts', '',
              '| Item | Would move | Left as it is |', '|---|---:|---:|']
    for name, label in ITEMS.items():
        lines.append('| %s | %d | %d |' % (label, counts[name], refused_counts[name]))
    lines += ['| **Books** | **%d** | **%d** |' % (counts['moves'], counts['refused']), '',
              'A book can count under more than one item (for example a series found and its author folder).', '', '## Would move', '']
    if not answer['items']:
        lines.append('None.')
    for n, item in enumerate(answer['items'], 1):
        lines += ['%d. `%s`' % (n, item['from']), '   -> `%s`' % item['to'],
                  '   Items: %s. %s' % (', '.join({'series': '2', 'author': '5', 'series_language': '6'}[i] for i in item['items']), item.get('why') or '')]
    lines += ['', '## Left as it is', '']
    if not answer['refused']:
        lines.append('None.')
    for n, item in enumerate(answer['refused'], 1):
        items = ', '.join({'series': '2', 'author': '5', 'series_language': '6'}.get(i, i) for i in item.get('items') or [])
        lines += ['%d. `%s`' % (n, item.get('from') or ''), '   Why: %s%s' % (item['refused'], ('. Items: ' + items) if items else '')]
    return '\n'.join(lines) + '\n'
