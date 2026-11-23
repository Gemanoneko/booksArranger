"""0.30.0 sorting moves (Sergei 2026-11-18, backlog "Why books aren't sorted — library-wide", items 2, 5 and 6): books
already in Audiobooks Sorted that are not where the app files them now.

  item 2  a series found after publication (series backfill) files the book in its series folder; 81 books were held
          because the series folder is another folder than the one the book was published in;
  item 5  one author folder per author (canonical_names.author: a rule's name, or the same words surname first);
  item 6  the series in the language it was written in (canonical_names.series_in_original, from the FantLab cycle
          research cited).

Nothing here moves a book by itself. plan() lists every book that would move (current path -> new path, the items, or
why it is left as it is) and a digest of that list. Until 0.31.0 a book moved only after Sergei's explicit approval of that
exact list (MergeService.sorting_moves_apply with the digest he saw). 0.31.0 (ruling R18, Sergei 2026-11-22: "If the author
and series are found, then put it in the folder according to our rules"): the app applies the list itself, item by item
(rule_filing.RuleFiling), so every refusal below still decides; a book whose listed change cannot be made stays where it is
and is listed with its reason. New books simply get the right path when they are converted.
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


# 0.31.0 step 3 (rulings R1 and R3): the English title of a translated book, by the one title rule
# (canonical_names.book_title) from the title the detail look-up recorded for the finished book (gap_fill's ledger: 92
# books on a copy of the live catalog have one that was never applied). Planned by default since milestone B (plan()'s
# titles; a dry run can leave it out). Milestone B gave the file its English name with its move only (the verified move
# renames the exact file: its bytes, tags included, are not changed). 0.31.0 ruling R27 (Sergei 2026-11-23): the English
# title and an author credit put in order are written inside the file's tags and into the app's list too (name_write):
# a listed item carries 'names', {'title', 'author', 'canonical_author'} that differ from the book's manifest, when the
# change rewrites the file (name_write.needed) and the book has not been moved before (its location is then a chain on top
# of its receipt, book_move, which a rewrite would break: such a book keeps the move alone).
TITLE_ITEM = 'title'
# 0.31.0 milestone B (Judy's spec 3.4): each reason a listed book has, as fields the record of renames and moves keeps
# (canonical()'s details): {'kind': 'series', 'name', 'number', 'provider', 'source_url'}, {'kind': 'title', 'title',
# 'provider', 'source_url'}, {'kind': 'author', 'name'}, {'kind': 'series_name', 'name', 'provider', 'source_url'}.
REASON_KINDS = ('series', 'title', 'author', 'series_name')
# The refusals that are a lasting obstacle only Sergei could clear (Judy 3.2: counted in the quiet line and listed in 3.4a).
# Every other refusal is his own decision, a book the rules do not manage, or work in progress: never counted.
LASTING_KEYS = ('name_exists', 'same_target', 'not_app_name', 'not_where_recorded', 'no_name')


def _provider(url):
    """The source a citation is from, as the page names sources ('fantlab', 'wikidata', 'goodreads'), '' when unknown."""
    host = str(url or '').split('://', 1)[-1].split('/', 1)[0].casefold()
    return next((name for name in ('fantlab', 'wikidata', 'goodreads', 'wikipedia', 'litres') if name in host), '')


def recorded_title(db, job_id):
    """recorded_titles() for one book, or None."""
    if not _table(db, 'gap_fill'):
        return None
    row = db.execute("SELECT record FROM gap_fill WHERE job_id=? AND state='found'", (job_id,)).fetchone()
    try:
        catalog = ((json.loads(row[0]).get('found') or {}).get('catalog')) if row else None
    except (TypeError, ValueError, AttributeError):
        return None
    return catalog if isinstance(catalog, dict) and catalog.get('language') else None


def recorded_titles(db):
    """{job_id: catalog} of the finished books whose detail look-up found the work's catalog record (gap_fill, state
    'found'): {'language', 'original_title', 'english_title'?, 'title_native', ...}."""
    if not _table(db, 'gap_fill'):
        return {}
    found = {}
    for job_id, record in db.execute("SELECT job_id,record FROM gap_fill WHERE state='found'"):
        try:
            catalog = ((json.loads(record).get('found') or {}).get('catalog'))
        except (TypeError, ValueError, AttributeError):
            continue
        if isinstance(catalog, dict) and catalog.get('language'):
            found[job_id] = catalog
    return found


def canonical(db, manifest, rules, series=None, catalog=None, details=None):
    """(review, facts, reasons, notes) for a finished book as the app files it now: its manifest's names with item 5 (the
    author's folder) and item 6 (the series' language) applied, and series (item 2: {'name','number','provider',
    'source_url'}) added when given. reasons: the items that changed something; notes: why, in words. details: a list
    that takes each reason as fields (REASON_KINDS), for the record of renames and moves."""
    import canonical_names
    review = dict(manifest.get('metadata') or {})
    facts = copy.deepcopy(manifest.get('metadata_facts')) if isinstance(manifest.get('metadata_facts'), dict) else None
    reasons, notes = [], []
    details = [] if details is None else details
    if series:
        review.update(series=series['name'], number=str(series['number']))
        if facts is not None:
            facts['series_state'] = 'verified'
        reasons.append('series')
        notes.append('series %s %s (%s)' % (series['name'], series['number'], series.get('provider') or 'source'))
        details.append({'kind': 'series', 'name': series['name'], 'number': str(series['number']), 'provider': series.get('provider') or '',
                        'source_url': series.get('source_url') or ''})
    if catalog and not _entered(facts, 'title'):
        local = (facts or {}).get('local_agreement') if isinstance((facts or {}).get('local_agreement'), dict) else {}
        his = (local.get('title') or {}).get('state') in ('entered', 'approved') if isinstance(local.get('title'), dict) else False
        titled, rule = canonical_names.book_title(review.get('title') or '', catalog, his=his)
        if rule == 'english' and titled and titled != review.get('title'):
            notes.append('title "%s" (the English title of "%s"; %s)' % (titled, review.get('title'), catalog.get('english_source') or catalog.get('source_url') or 'recorded by the detail look-up'))
            review['title'] = titled
            reasons.append(TITLE_ITEM)
            cited = catalog.get('english_source') or catalog.get('source_url') or ''
            details.append({'kind': 'title', 'title': titled, 'provider': str(catalog.get('english_provider') or '') or _provider(cited), 'source_url': cited})
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
            details.append({'kind': 'author', 'name': filed})
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
                details.append({'kind': 'series_name', 'name': named, 'provider': provider or '', 'source_url': url or ''})
            else:
                next(entry for entry in details if entry['kind'] == 'series')['name'] = named
            notes.append('series "%s" (%s)' % (named, why))
    return review, facts, reasons, notes


def target(db, row, rules, output_root, series=None, placed=None, effective=None, catalog=None, ruled=False, placed_kinds=None):
    """{'job_id', 'from', 'to', 'items', 'why'} for one completed job (an audio_jobs row), or {'refused': reason} with
    'from', or None when the book is where the app files it. placed: series backfill wrote this approved book's series
    under its new name in its own folder (item 2); the book is expected exactly there and goes on to its series folder.
    effective: where the book's last move took it (None: never moved); a moved book is planned no further: None when it
    is where the app files it now (an approved move took it there), else left where it was moved to.
    ruled (0.31.0 milestone B): that last move was not to a folder Sergei chose (the app's rules, his approval of a listed
    move, or Use computed folder took the book there), so the rules still file the book: it is planned from where it is
    now. A folder he chose with Choose folder… is his and is never planned on (ruling R26).
    placed_kinds (0.31.0 R27): the kinds of change of a book whose new names were written in its own folder (name_write),
    which now only moves; a placed book without them is a written series."""
    import name_write
    from metadata import propose
    from series_backfill import published_root
    manifest = json.loads(row['manifest'])
    output = json.loads(row['output'])
    current = output.get('final_path') or ''
    found = {'job_id': row['job_id'], 'from': current}
    root = str(published_root(manifest, output))
    details = []
    review, facts, reasons, notes = canonical(db, manifest, rules, series, catalog, details)
    if placed and not reasons:
        reasons, notes = (list(placed_kinds), ['its folder']) if placed_kinds else (['series'], ['its series folder'])
    if not reasons:
        return None
    found['reasons'] = details
    found['filed'] = {'title': str(review.get('title') or ''), 'author': str(review.get('author') or review.get('canonical_author') or '')}
    if series:
        found['series'] = {'name': review['series'], 'number': review['number'], 'provider': series.get('provider') or '',
                           'source_url': series.get('source_url') or ''}
    by_rules = bool(ruled and effective)
    if by_rules:
        found['from'] = current = effective  # the catalog's own record of where the last move put it
    if not _inside(current, output_root) or not _inside(root, output_root) and key(root) != key(output_root):
        return dict(found, refused='Not in Audiobooks Sorted; left as it is', items=reasons)
    if (facts or {}).get('destination_override'):
        return dict(found, refused='You chose its folder; left as it is', items=reasons)
    try:
        now = propose('', root, 'audiobook', {}, manifest['metadata'], automatic_facts=copy.deepcopy(manifest.get('metadata_facts')))
        wanted = propose('', root, 'audiobook', {}, review, automatic_facts=facts)
    except (ValueError, KeyError, TypeError) as error:
        return dict(found, refused='No name for it: ' + (str(error) or type(error).__name__), items=reasons)
    if effective is not None and not by_rules:
        if effective and wanted.get('path') and key(effective) == key(wanted['path']):
            return None
        return dict(found, refused='Already moved to a folder you chose; left as it is', items=reasons)
    if by_rules:
        pass  # where the move chain says it is (plan() checks the file is there; the move itself proves its bytes)
    elif placed:
        if key(placed) != key(current):
            return dict(found, refused='The audiobook is not where its series update put it; left as it is', items=reasons)
    elif not now.get('path') or key(now['path']) != key(current):
        return dict(found, refused="Its name does not follow the app's naming; left as it is", items=reasons)
    if not wanted.get('path'):
        return dict(found, refused='No name for it: ' + (wanted.get('reason') or 'unknown'), items=reasons)
    if key(wanted['path']) == key(current):
        return None
    names = name_write.needed(manifest.get('metadata'), review) if effective is None and not placed else {}
    return dict(found, to=wanted['path'], items=reasons, why='; '.join(notes), **({'names': names} if names else {}))


def _moved(db, job_id):
    """None when the book was never moved; else the final path of its last effective move ('' while one is unfinished)."""
    return _last_move(db, job_id)[0]


def _last_move(db, job_id):
    """(_moved()'s answer, ruled). ruled: the last move carries no folder Sergei chose (no override), so the rules still
    file the book (target())."""
    import book_move
    if not book_move.have(db):
        return None, False
    rows = db.execute("SELECT state,final_json,override_id FROM book_moves WHERE job_id=? AND state NOT IN ('failed','cancelled') ORDER BY generation", (job_id,)).fetchall()
    if not rows:
        return None, False
    state, final, override = rows[-1]
    try:
        return ((json.loads(final) or {}).get('final_path') or '' if state in book_move.EFFECTIVE and final else ''), not override
    except (TypeError, ValueError):
        return '', False


def certain(found, manifest):
    """0.31.0 (rulings R18 and R21): a series the look-up kept for a finished book, judged by the one rule
    (series_certainty). A record kept before that rule existed never passed it; a doubtful one counts as not found, so the
    book is planned without it and nothing says so. Any failure to judge is doubtful."""
    try:
        import series_certainty
        from public_research import edition_volume
        title = str((manifest.get('metadata') or {}).get('title') or '')
        candidate = {name: found.get(name) for name in ('name', 'number', 'provider', 'source_url')}
        return series_certainty.judge(candidate, {'volume': edition_volume(title)[1]})['verdict'] == series_certainty.CERTAIN
    except Exception:
        return False


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
NOT_MOVED_KEYS = (('file_changed', ('The book changed since you approved', 'The published audiobook changed', 'no longer matches',
                                    'The book changed since its new names were approved')),
                  ('place_changed', ('The planned place changed',)), ('name_exists', ('A file with the series name already exists',)),
                  # 0.31.0 R27: the rewrite of the file's tags did not prove out (a tag that did not read back, any other
                  # change found by the proofs, a file that cannot be retagged); the book is left as it was.
                  ('tags_not_written', ('did not read back', 'changed while retagging', 'cannot be retagged safely',
                                        'could not be written', 'Series update failed', "does not fit the book's recorded author credit")))


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
    # WRITE_WAITS: the guard holds a write in the book's own folder for the same approval (series_backfill).
    reasons = SERIES_FOLDER_REASONS + (series_backfill.MOVE_WAITS, series_backfill.WRITE_WAITS)
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


def plan(db, output_root, rules=None, exists=os.path.lexists, retained=frozenset(), titles=True):
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
    # 0.31.0 R27: so is a book whose new names were written in its own folder (name_write) and whose move did not run yet.
    import name_write
    placed_kinds = {}
    for job_id, (path, kinds) in name_write.placed(db).items():
        if job_id not in placed:
            placed[job_id], placed_kinds[job_id] = path, kinds
    # titles (0.31.0 step 3, rulings R1 and R3): the English title of a translated book is planned too.
    recorded = recorded_titles(db) if titles else {}
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
        held = series.get(row['job_id'])
        if held and not certain(held, manifest):
            held = None  # doubtful by the one rule: as if no series was found (R18), and nothing says so
        if not _inside(current, output_root) and not held:
            # Outside Sorted (a book published into its library before 0.13.0): listed only when it would change.
            found = target(db, row, rules, output_root)
            if found:
                refused.append(dict(found, refused=found.get('refused') or 'Not in Audiobooks Sorted; left as it is', to=None))
            continue
        try:
            # A moved book: the receipt keeps the published place, the move chain the new one (book_move).
            effective, ruled = _last_move(db, row['job_id'])
            found = target(db, row, rules, output_root, held, placed=placed.get(row['job_id']), effective=effective,
                           catalog=recorded.get(row['job_id']), ruled=ruled, placed_kinds=placed_kinds.get(row['job_id']))
        except Exception as error:  # one malformed record never hides the others
            refused.append({'job_id': row['job_id'], 'from': current, 'refused': 'Could not be planned: ' + (str(error) or type(error).__name__)[:200], 'items': []})
            continue
        if not found:
            continue
        failed = (held or {}).get('failed')
        if failed:
            found['approved_not_moved'] = {'key': reason_key(failed, NOT_MOVED_KEYS), 'reason': failed}
        if row['job_id'] in placed and 'to' in found:
            found['placed'] = True  # its series (or its names) is in the file already: an approval only moves it (sorting_moves_apply)
            found['approved_not_moved'] = {'key': 'other', 'reason': 'Its names were written; the move into its folder did not run' if row['job_id'] in placed_kinds
                                           else 'Its series was written; the move into its series folder did not run'}
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
    names = list(ITEMS) + ([TITLE_ITEM] if any(TITLE_ITEM in (i.get('items') or []) for i in items + refused) else [])
    counts = {name: sum(1 for i in items if name in i['items']) for name in names}
    counts.update(moves=len(items), refused=len(refused))
    refused_counts = {name: sum(1 for i in refused if name in (i.get('items') or [])) for name in names}
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
                  '   Items: %s. %s' % (', '.join({'series': '2', 'author': '5', 'series_language': '6'}.get(i, i) for i in item['items']), item.get('why') or '')]
    lines += ['', '## Left as it is', '']
    if not answer['refused']:
        lines.append('None.')
    for n, item in enumerate(answer['refused'], 1):
        items = ', '.join({'series': '2', 'author': '5', 'series_language': '6'}.get(i, i) for i in item.get('items') or [])
        lines += ['%d. `%s`' % (n, item.get('from') or ''), '   Why: %s%s' % (item['refused'], ('. Items: ' + items) if items else '')]
    return '\n'.join(lines) + '\n'
