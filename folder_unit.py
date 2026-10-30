"""Ruling 68 (Sergei 2026-10-28): "Never divide the files that were in 1 folder into different books", with his answers of
2026-10-29 (ruling 71): a folder where each file is already a whole book keeps one book per file (71a), and a folder
holding a series of separately tagged novels by one author is one book per novel (71b). Everything else in one source
folder is one book; a folder the evidence cannot settle is raised as a question (ruling 51), never split or joined
silently. Pure: catalog members in, a verdict out. groups.build applies it; protected (approved, reviewed, queued or
converted) files are never moved by it.

The source folder is the folder that holds the files, with disc and part folders of one book rolled up to their parent
(split_books.unit), so "CD 1" and "CD 2" are one folder. Whole .m4b files are always books of their own (71a: the
author folders, Глубина, Созвездие Льва and the library root keep their volumes)."""
import re
from pathlib import Path

import split_books
import tag_text
import track_order

VERSION = 'folder-unit-v1'
# A single file this long is a whole book, not a story or a part (71a); measured from the catalog's own probe.
WHOLE_BOOK_SECONDS = 3 * 3600
MAX_FILES = 500


def unit_of(path):
    """(folder, kind): the source folder a file belongs to. Part folders of different books stay apart by their kind."""
    folder, _, kind = split_books.unit(path)
    return folder, kind


def _norm(value):
    return ''.join(c for c in str(value or '').casefold().replace('ё', 'е') if c.isalnum())


def _tags(member):
    return tag_text.tags(member.get('metadata') or {})


def _track(member):
    match = re.fullmatch(r'\s*0*(\d{1,4})\s*(?:/\s*0*(\d{1,4})\s*)?', str(_tags(member).get('track') or _tags(member).get('tracknumber') or ''))
    return (int(match[1]), int(match[2]) if match[2] else None) if match else (None, None)


def _credit(member):
    tags = _tags(member)
    return ' '.join(str(tags.get('author') or tags.get('artist') or tags.get('album_artist') or tags.get('albumartist') or '').split())


def _album(member):
    return ' '.join(str(_tags(member).get('album') or '').split())


def book_name(items):
    """A name for one proposed book of a folder question: its album tag, else its file-name title, else its file name."""
    albums = [a for a in (_album(m) for m in items) if a]
    if albums:
        return max(set(albums), key=albums.count)
    from source_identity import filename_identity
    if len(items) == 1:
        return filename_identity(items[0]['filename']).get('title') or Path(items[0]['filename']).stem
    return Path(items[0]['filename']).stem


def _one_author(items):
    credits = list(dict.fromkeys(c for c in (_credit(m) for m in items) if c))
    if len(credits) <= 1:
        return True
    from local_identity import same_person, compare_names
    return all(_norm(a) == _norm(b) or same_person(a, b) or compare_names(a, b) for a in credits for b in credits)


def _self_numbered(items):
    """The files of one proposed book number themselves 1..n (file names, else track tags)."""
    if len(items) < 2:
        return False
    if track_order.filename_sequence(track_order.member_names(items)):
        return True
    tracks = sorted(_track(m)[0] for m in items if _track(m)[0] is not None)
    return len(tracks) == len(items) and tracks[0] in (0, 1) and tracks == list(range(tracks[0], tracks[0] + len(items)))


def _whole_files(books):
    """71a: every proposed book is one file, and every file is long enough to be a whole book."""
    files = [items[0] for items in books]
    return all(len(items) == 1 for items in books) and all(isinstance(m.get('duration'), (int, float)) and m['duration'] >= WHOLE_BOOK_SECONDS for m in files)


def _named_works(books):
    """71a by the file names: every proposed book is one file named "[NN] Author - Title" with one shared start and
    different work titles ("01 Сапковский - Последнее желание", "02 Сапковский - Меч предназначения"; "Кинг - Оно",
    "Кинг - Мизери"): each file is a whole book. Not when a folder names another author, which makes the shared start
    the book ("Нисио Исин - Monogatari Series"), nor in a folder named as a collection of stories ("Рассказы",
    "Сборник"), nor when the start is a part marker ("Часть Первая - …")."""
    if len(books) < 2 or any(len(items) != 1 for items in books):
        return False
    files = [items[0] for items in books]
    # A file shorter than two hours is a story or a part, not a whole book, whatever its name says (Бойся Чужого).
    if any(isinstance(m.get('duration'), (int, float)) and m['duration'] < 2 * 3600 for m in files):
        return False
    from source_identity import filename_identity
    from local_identity import work_name, chapter_works, COLLECTION_TITLE, COLLECTION_FOLDER, tag_index
    folder = Path(files[0]['path']).parent.name
    if COLLECTION_TITLE.search(folder) or COLLECTION_FOLDER.search(folder):
        return False
    names = []
    for m in files:
        stem = re.sub(r'^\s*\d{1,4}[ _.-]+', '', Path(m['filename']).stem)
        parts = re.split(r'\s+[–—-]\s+', stem, maxsplit=1)
        names.append((parts[0], parts[1]) if len(parts) == 2 and len(_norm(parts[0])) >= 3 and re.search(r'[^\W\d_]', parts[1]) else ('', stem))
    if any(re.match(r'(?i)\s*(?:часть|глава|книга|том|эпизод|выпуск|part|chapter|book|episode|cd|disc|диск)(?![^\W\d_])', s or t) for s, t in names):
        return False  # «Часть Первая - Нубилийский Пролив»: parts of one book (rulings 19c and 50)
    tag_titles = {' '.join(str(_tags(m).get('title') or '').split()) for m in files}
    own = next(iter(tag_titles)) if len(tag_titles) == 1 else ''
    keys = chapter_works([title for _, title in names], own)
    if '' in keys or len(set(keys)) != len(files) or (own and _norm(work_name(own)) in keys):
        return False
    starts = {_norm(start) for start, _ in names}
    series_named = bool(own) and all(re.match(r'\s*' + re.escape(own) + r'\s*\d{1,3}\s*[.:]\s*\S', t, re.I) for _, t in names)
    if not (len(starts) == 1 and '' not in starts or series_named):
        return False  # plain different names ("Альфа", "Бета") say nothing about whole books: the folder is asked
    if len(starts) == 1 and '' not in starts:
        # One shared start a folder names as the book's author's other name: the start is the book (Monogatari).
        from groups import _folder_names_another_author
        index = tag_index(m['metadata'].get('tags') for m in files)
        if _folder_names_another_author(files[0]['path'], names[0][0], index):
            return False
    return True


_VOLUME_TAIL = re.compile(r'^(.*?)[\s.,:;_-]*(?:№|#|no\.?|книга|кн\.|book|vol\.?|volume)?\s*0*(\d{1,3})\s*$', re.I)


def _numbered_volumes(books):
    """71a by the tags: every proposed book is one file whose own album names one volume of a numbered set, the same name
    with its own number («Пртоколы SCP. Сейф №1», «№2», «№3»; «Безымянная 1», «Безымянная 10»). «Часть», «Том», CD and
    disc numbers are parts of one book (ruling 50), never volumes."""
    if len(books) < 2 or any(len(items) != 1 for items in books):
        return False
    albums = [_album(items[0]) for items in books]
    if any(not a for a in albums) or len({_norm(a) for a in albums}) != len(albums):
        return False
    if any(re.search(r'(?i)(?:часть|част\.|том|part|cd|disc|диск|глава|chapter|эпизод|сезон|выпуск)\s*№?\s*\d{1,3}\s*$', a) for a in albums):
        return False
    found = [_VOLUME_TAIL.match(a) for a in albums]
    if any(m is None or not re.search(r'[^\W\d_]{2}', m[1]) for m in found):
        return False
    return len({_norm(m[1]) for m in found}) == 1 and len({int(m[2]) for m in found}) == len(found)


def _separate_novels(books):
    """71b: two or more separately tagged books, each numbered on its own from 1, by one author (Хроники Нарнии,
    Космическая трилогия: albums "… Книга 1. …", "… Книга 2. …", file names restarting at 01)."""
    if len(books) < 2 or any(len(items) < 2 for items in books):
        return False
    albums = [_norm(_album(items[0])) for items in books]
    if '' in albums or len(set(albums)) != len(albums) or any(len({_norm(_album(m)) for m in items}) != 1 for items in books):
        return False
    return all(_self_numbered(items) for items in books) and _one_author([m for items in books for m in items])


def _track_total(items):
    """Every file tagged k/N with the one N the folder holds, each k once (Lyons: 01/38 .. 38/38)."""
    found = [_track(m) for m in items]
    totals = {total for _, total in found}
    numbers = sorted(n for n, _ in found if n is not None)
    return len(totals) == 1 and None not in totals and next(iter(totals)) == len(items) and numbers == list(range(1, len(items) + 1))


def _continuing_tracks(items):
    """Track numbers that run on across the proposed books, 1..N over the folder (Wolfe: disc 03 tracks 1-38, disc 04 39-78)."""
    numbers = sorted(_track(m)[0] for m in items if _track(m)[0] is not None)
    return len(numbers) == len(items) and numbers[0] in (0, 1) and numbers == list(range(numbers[0], numbers[0] + len(items)))


def _main_with_extras(books, total):
    """One book plus a few extra files beside it (a novel with a glossary or bonus stories: Страуд + Словарь.mp3)."""
    ordered = sorted(books, key=len, reverse=True)
    main, rest = ordered[0], ordered[1:]
    extra = sum(len(items) for items in rest)
    # The extras credit the book's own author (or no one): another author's file beside a novel is asked.
    return len(main) >= 3 and len(main) * 4 >= total * 3 and extra <= 4 and all(len(items) <= 2 for items in rest) \
        and _one_author([m for items in books for m in items])


def verdict(items, scope_of, kept=frozenset(), container=False):
    """items: every audio file of one source folder that is not a whole .m4b (catalog members); scope_of: {path: the book
    the per-file rules proposed}. Returns {'verdict': 'one'|'separate'|'ask', 'basis', 'books': [{'name', 'files'}]}."""
    proposed = {}
    for item in sorted(items, key=lambda m: m['path']):
        proposed.setdefault(scope_of[item['path']], []).append(item)
    books = sorted(proposed.values(), key=lambda group: group[0]['path'])
    shown = [{'name': book_name(group), 'files': len(group)} for group in books]
    names = [b['name'] for b in shown]
    for book, group in zip(shown, books):
        if names.count(book['name']) > 1:
            # Two proposed books with one album (stories of different authors): the credit or the file name tells them apart.
            credit = _credit(group[0])
            book['name'] = book['name'] + ' (' + (credit or Path(group[0]['filename']).stem) + ')'
    def answer(kind, basis):
        return {'verdict': kind, 'basis': basis, 'books': shown, 'version': VERSION}
    if len(books) < 2:
        return answer('one', 'one book')
    if len(items) > MAX_FILES:
        return answer('separate', 'too many files to judge')
    present = [item for item in items if not item.get('missing')]
    if present and all(item['path'] in kept for item in present):
        # His "Keep as separate books" holds for the files still there; a file that went missing does not take it back.
        return answer('separate', 'kept as separate books by you')
    if container:
        return answer('separate', 'a library or container folder, not a book')
    if _whole_files(books):
        return answer('separate', 'each file is a whole book')
    if _named_works(books):
        return answer('separate', 'each file names its own book')
    if _numbered_volumes(books):
        return answer('separate', 'each file is one numbered volume')
    if track_order.filename_sequence(track_order.member_names(items)):
        return answer('one', 'the file names number the whole folder')
    if _separate_novels(books):
        return answer('separate', 'separately tagged books of one author, each numbered on its own')
    if _track_total(items):
        return answer('one', 'the track tags number the whole folder')
    if _continuing_tracks(items):
        return answer('one', 'the track numbers run on across the folder')
    if _main_with_extras(books, len(items)):
        return answer('one', 'one book with a few extra files')
    return answer('ask', 'the folder may hold more than one book')


def contents(members, title=''):
    """Judy 6.1: the files of a one-folder book that are not its main title (a novel plus stories): [{title, author, files}],
    and how many of them credit another author than the book's main credit. None when every file names the book."""
    if len(members) < 2:
        return None
    albums = [_album(m) for m in members]
    counts = {}
    for album in albums:
        if album:
            counts[_norm(album)] = counts.get(_norm(album), 0) + 1
    if len(counts) < 2:
        return None
    main = max(counts, key=counts.get)
    credits = [c for c in (_credit(m) for m in members if _norm(_album(m)) == main) if c]
    main_credit = max(set(credits), key=credits.count) if credits else ''
    stories = []
    seen = {}
    for member, album in zip(members, albums):
        if _norm(album) == main or not album:
            continue
        key = _norm(album)
        if key in seen:
            seen[key]['files'] += 1
            continue
        seen[key] = {'title': album, 'author': _credit(member), 'files': 1}
        stories.append(seen[key])
    if not stories:
        return None
    from local_identity import same_person, compare_names
    other = sum(1 for s in stories if s['author'] and main_credit and not (_norm(s['author']) == _norm(main_credit) or same_person(s['author'], main_credit) or compare_names(s['author'], main_credit)))
    return {'stories': stories[:50], 'other_authors': other}


# The skipped part numbers a numbering lists: the Missing files row shows the first 500 (merge_service._established_gap).
MAX_LISTED = 500


def _ranges(values):
    """[[a, b]]: the runs of numbers the sorted, distinct values skip between their first and last. Read from neighbouring
    values, so time and memory follow the number of files, never the size of a number in a name (Senua 0.24.0 M3: three
    files named 3000001..3000003, or one id of nine digits beside "01")."""
    return [[a + 1, b - 1] for a, b in zip(values, values[1:]) if b > a + 1]


def _listed(ranges, limit=MAX_LISTED):
    """The first limit skipped numbers, in order, from their runs (never the whole run built)."""
    found = []
    for a, b in ranges:
        found.extend(range(a, min(b, a + limit - len(found) - 1) + 1))
        if len(found) >= limit:
            break
    return found


def _token(name, value, width):
    return str(value).zfill(width)


# Ruling 73f (Sergei 2026-10-30, narrows 71m; Senua 0.24.0 d4): a number in a file name far larger than the folder's other
# part numbers is a year or a download id ("01-03.mp3" beside "Интервью 2019.mp3"; "track_3000003.mp3"), not a part, and
# makes no Missing files. Far larger: NOT_A_PART or more and more than FAR times the number below it.
# Ruling 73i (Sergei 2026-10-30, narrows 73f; Senua 0.24.0 d6): 73f drops only an outlier next to smaller part numbers.
# When no place in the names holds smaller part numbers, numbers that are all NOT_A_PART or more are the parts
# ("1001…1012" without "1005" names 1005), counted from the first of them (nothing below it is missing).
NOT_A_PART = 1000
FAR = 2


def _part_numbers(values, alone=False):
    """The part numbers among sorted, distinct file-name numbers: every value below the first one that is NOT_A_PART or
    more and more than FAR times the value before it (that one and every value above it are not parts). The smallest is
    compared with 0, so a place whose numbers are all NOT_A_PART or more holds no part numbers ([]) when another place may
    hold smaller ones (73f: "3000001_01", "3000002_02" reads 01, 02). alone (73i: no place holds smaller part numbers)
    keeps the smallest, so such a place is the numbering and only an outlier above its own numbers is left out. Values
    under NOT_A_PART, however far apart, and a numbering that climbs past it (0998, 0999, 1000, 1002) are all kept."""
    below = values[0] if alone and values else 0
    for index, value in enumerate(values):
        if value >= NOT_A_PART and value > FAR * below:
            return values[:index]
        below = value
    return values


def numbers(members):
    """Judy 5.2, the Numbers line: what the present numbering does, from the file names, else the track tags. Printed
    tokens (zero-padded like the names), never 'missing'. None when the files are numbered 1..n without a skip, or when
    nothing numbers them. A year or an id in a name is left out of the numbering (ruling 73f, _part_numbers); a place in
    the names that holds only those numbers numbers nothing while the next place holds smaller part numbers. When no place
    does, the first such place is the numbering (ruling 73i), read before the track tags and counted from its first
    number: None without a skip. 'counts_from_one': whether the numbers below 'start' count as missing (False for 73i)."""
    names = track_order.member_names(members)
    digits = [re.findall(r'\d+', Path(str(n)).stem) for n in names]
    runs = [[int(v) for v in d] for d in digits]
    found = None
    alone = False
    if runs and all(runs):
        shortest = min(len(r) for r in runs)
        chosen = large = None
        for index in list(range(shortest)) + [-i for i in range(1, shortest + 1)]:
            values = [r[index] for r in runs]
            if len(set(values)) == len(values):
                kept = _part_numbers(sorted(values))
                if kept:
                    chosen = (index, values, kept)
                    break
                large = large or (index, values)  # every number here is NOT_A_PART or more
        if chosen is None and large is not None:
            alone = True  # 73i: no place holds smaller part numbers
            chosen = (*large, _part_numbers(sorted(large[1]), alone=True))
        if chosen is not None:
            index, values, kept = chosen
            # Zero-padded like the parts' own names, never like a year's or an id's.
            width = max(len(d[index]) for d, value in zip(digits, values) if value <= kept[-1])
            found = ('names', kept, width)
    disc = None
    if found is None:
        tracks = [_track(m)[0] for m in members]
        if all(t is not None for t in tracks) and len(set(tracks)) == len(tracks):
            found = ('tags', sorted(tracks), 1)
            discs = {re.sub(r'\D.*$', '', str(_tags(m).get('disc') or _tags(m).get('discnumber') or '').strip()).lstrip('0') for m in members}
            if len(discs) == 1 and next(iter(discs)) not in ('', '1'):
                disc = int(next(iter(discs)))  # Wolfe «Солнце и Замок»: every file disc 05, tracks 1-70
    if found is None:
        return None
    source, values, width = found
    first, last = values[0], values[-1]
    ranges = _ranges(values)  # values are sorted and distinct (checked above)
    if not ranges and (first in (0, 1) or alone) and disc is None:
        return None
    # 'missing': the first MAX_LISTED skipped numbers (every reader lists at most that many).
    if disc is not None:
        token = lambda value: '%02d-%02d' % (disc, value)
        return {'source': source, 'first': token(first), 'last': token(last), 'skipped': [token(a) if a == b else token(a) + '-' + token(b) for a, b in
                ranges][:6], 'skipped_total': len(ranges), 'missing': _listed(ranges), 'start': first, 'end': last, 'disc': disc,
                'counts_from_one': True}
    tokens = [_token(source, a, width) if a == b else _token(source, a, width) + '-' + _token(source, b, width) for a, b in ranges[:6]]
    return {'source': source, 'first': _token(source, first, width), 'last': _token(source, last, width),
            'skipped': tokens, 'skipped_total': len(ranges), 'missing': _listed(ranges), 'start': first, 'end': last,
            'counts_from_one': not alone}
