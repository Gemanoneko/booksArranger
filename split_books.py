"""Split-book grouping (v0.15.0): files that provably form one book become one candidate.

A book is often held as many files: one M4B per chapter (155 chapter files of one Dan
Brown novel), "Title 1.m4b" / "Title 2.m4b" part sets, or CD1/CD2 folders. Each such file
used to be its own candidate and the v0.14.0 split-part guard held all of them. This pure
module decides which single-file candidates of one folder (or of one book's disc/part
folders) are provably the parts of ONE book, in a proven order, so the existing source
scope, order, hashed membership and admission machinery can treat them as one source set
that becomes one M4B.

Grouped only when every check passes; anything else holds (the files stay separate and
the split-part guard keeps holding them). Never guessed:
  - one book title: the same album tag on every file (or, without any album, the same
    title tag / file name once the part number is removed);
  - consistent tags: identical author, artist, composer, narrator/reader credits, readers
    named in comments, language and series tags; one container and one audio profile
    (codec, sample rate, channels);
  - every file is only a chapter or part: its own name or title tag beyond the shared book
    name is a number, a chapter/part/CD marker (with or without a chapter name), front or
    back matter (prologue, epilogue ...) or "unknown title". A distinct name ("Повелитель
    Хаоса", "Двигающийся палец") may be a separate book or story; a volume or book marker
    ("Том 3", "Книга 1", "Vol. 2") may be a separate book of a series: both hold;
  - coherent numbering: every file has a position (embedded track number, or a part number
    in the file name, or its disc folder), no duplicates, no gaps, starting at 0 or 1,
    discs 1..n, declared totals (track 3/7) equal the files found, and the embedded and
    file-name orders agree when both exist;
  - no other catalogued audio file in the same place carries the same book title.
"""
import re
import unicodedata
from pathlib import Path

from source_identity import norm, text

VERSION = 'split-books-v1'
MAX_PARTS = 500
# Folders that hold one disc or part of a book: "CD1", "Disc 2", "Часть 3".
DISC_FOLDER = re.compile(r'(?:cd|disc|disk|диск|часть|part)[ _.-]*(\d{1,3})', re.I)
# "Книга (часть 1)" / "Book (part 2)": the part folders of one book share the base name.
PART_FOLDER = re.compile(r'^(.*?)[\s(\[]*(?:часть|ч\.|part)\s*(\d{1,3})\s*[)\]]?\s*$', re.I)
PART_MARKER = r'(?:часть|ч\.|глава|гл\.|chapter|ch\.|part|pt\.?|cd|disc|disk|диск|track|трек|эпизод|episode|раздел|section)'
# A volume or book of a series may be a separate book: never grouped.
VOLUME_WORDS = r'(?:книга|кн\.|том|т\.|volume|vol\.?|book|выпуск|сезон|season)'
VOLUME_MARKER = re.compile(r'(?<![^\W\d_])' + VOLUME_WORDS + r'\s*[#№]?\s*\d', re.I)
ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
# Only a chapter or part marker may carry a chapter name ("Часть 1. ТЕНЬ ПРОШЛОГО"); an episode,
# CD, disc or track number followed by a name may be a separate work (Senua M2).
NAMED_PART = r'(?:часть|ч\.|глава|гл\.|chapter|ch\.|part|pt\.?)'
# A year-like number is part of a title ("Метро 2033", "Фантастика 2021"), never a part number.
YEAR = re.compile(r'^(?:1[5-9]\d\d|20\d\d)$')
MARKED_NUMBER = re.compile(PART_MARKER + r'\s*[#№]?\s*(\d{1,4})(?!\d)', re.I)
LEADING_NUMBER = re.compile(r'^\W*(\d{1,4})(?!\d)')
# Words that never name a separate work; front and back matter of a book.
GENERIC = {'unknown', 'title', 'untitled', 'track', 'трек', 'часть', 'глава', 'chapter', 'part', 'cd', 'disc', 'диск', 'без', 'имени', 'no', 'name'}
MATTER = ('пролог', 'эпилог', 'вступление', 'введение', 'предисловие', 'послесловие', 'интерлюдия', 'аннотация', 'от автора', 'заключение',
          'prologue', 'prolog', 'epilogue', 'introduction', 'intro', 'foreword', 'preface', 'afterword', 'interlude', 'outro', 'conclusion',
          'opening credits', 'end credits', 'credits')
# Tags that must be identical on every part: the album exactly, brackets included ("The Hunger
# Games (Book 1)" vs "(Book 2)", Senua M1), and author, reader and recording credits.
SAME_TAGS = ('album', 'artist', 'album_artist', 'albumartist', 'author', 'composer', 'narrator', 'reader', 'performer', 'language', 'series', 'series-part', 'series_part')
NARRATOR_TEXT = ('comment', 'description', 'synopsis')


def _tags(member):
    return {str(k).casefold(): v for k, v in member.get('metadata', {}).get('tags', {}).items()}


def _nfc(value):
    return unicodedata.normalize('NFC', str(value or ''))


def _number(value):
    match = re.match(r'^\s*(\d{1,4})(?:\s*/\s*(\d{1,4}))?\s*$', str(value or ''))
    return (int(match[1]), int(match[2]) if match[2] else None) if match else (None, None)


def _profile(member):
    streams = [s for s in member.get('metadata', {}).get('probe', {}).get('streams', []) if s.get('codec_type') == 'audio']
    if len(streams) != 1:
        return None
    stream = streams[0]
    return (stream.get('codec_name'), str(stream.get('sample_rate')), stream.get('channels'))


def unit(path):
    """(folder that holds the book, disc number or None, kind). Disc/part folders of one
    book belong to their parent; the kind keeps part folders of different books apart."""
    parent = Path(path).parent
    name = _nfc(parent.name).strip()
    disc = DISC_FOLDER.fullmatch(name)
    if disc:
        return str(parent.parent), int(disc[1]), 'disc folders'
    part = PART_FOLDER.match(name)
    if part and re.search(r'[^\W\d_]{2}', part[1]):
        from local_identity import title_key
        return str(parent.parent), int(part[2]), 'part folders ' + title_key(part[1])
    return str(parent), None, 'folder'


def book_key(member):
    """The book title every part must share: the album tag, else the title tag or file
    name without its part number. Returns (basis, key) or None when nothing names a book."""
    from local_identity import title_key
    tags = _tags(member)
    album = text(tags.get('album'))
    if album:
        return 'album', title_key(album)
    for basis, value in (('title tag', text(tags.get('title'))), ('file name', Path(member['filename']).stem)):
        value = _nfc(value)
        value = re.sub(r'(?:[\s._-]+|\s*' + PART_MARKER + r'\s*)\d{1,4}\s*$', '', value, flags=re.I)
        value = re.sub(r'^\s*\d{1,4}[\s._-]+', '', value)
        key = title_key(value)
        # "Глава", "Part", "unknown title" alone name a chapter, not the book.
        if key and re.search(r'[^\W\d_]{2}', value) and not all(w in GENERIC for w in re.findall(r'[^\W\d_]+', value.casefold())):
            return basis, key
    return None


def _arabic(value):
    """Roman numerals after a part or volume word read as numbers: "Часть II" = "Часть 2"."""
    def convert(match):
        total, previous = 0, 0
        for char in reversed(match[2].upper()):
            number = ROMAN[char]
            total = total - number if number < previous else total + number
            previous = max(previous, number)
        return match[1] + str(total) if 0 < total < 100 else match[0]
    return re.sub(r'((?<![^\W\d_])(?:' + PART_MARKER[3:-1] + r'|книга|том|volume|vol\.?|book)\s*)([IVXLC]{1,7})(?![^\W\d_])', convert, _nfc(value), flags=re.I)


def _common_prefix(values):
    """Longest shared start of all names, cut back so it ends between words in every name
    (never inside a word or a number) and never on a part or volume word, which belongs to
    each part's own label."""
    if not values:
        return ''
    folded = [v.casefold() for v in values]
    prefix = folded[0]
    for value in folded[1:]:
        cut = 0
        while cut < min(len(prefix), len(value)) and prefix[cut] == value[cut]:
            cut += 1
        prefix = prefix[:cut]
    while prefix and prefix[-1].isalnum() and any(len(v) > len(prefix) and v[len(prefix)].isalnum() for v in folded):
        prefix = prefix[:-1]
    while True:
        trimmed = re.sub(r'(?:^|(?<=[\s._\-–—,:;(]))(?:' + PART_MARKER + r'|' + VOLUME_WORDS + r')[\s._\-–—,:;#№]*$', '', prefix, flags=re.I)
        if trimmed == prefix:
            break
        prefix = trimmed
    return values[0][:len(prefix)]


def label(value, prefix):
    """What this part's name says beyond the shared book name.

    Returns (kind, position): kind is 'number' / 'generic' / 'part' / 'matter' (a chapter or
    part), 'volume' (may be a separate book of a series) or 'distinct' (a separate work)."""
    rest = text(_after_prefix(_nfc(value), prefix))
    if VOLUME_MARKER.search(rest):
        return 'volume', None
    marked = MARKED_NUMBER.search(rest)
    leading = LEADING_NUMBER.match(rest)
    number = leading or marked
    position = int(number[1]) if number else None
    if number and YEAR.match(number[1]):
        return 'distinct', position
    remainder = rest
    if leading:
        remainder = remainder[leading.end():]
    remainder = re.sub(r'^[\W_]+', '', remainder)
    words = re.findall(r'[^\W\d_]+', remainder.casefold())
    if not words:
        return 'number', position
    if all(w in GENERIC for w in words):
        return 'generic', position
    if re.match(NAMED_PART + r'\s*[#№]?\s*\d', remainder, re.I) or (marked and marked.start() <= (leading.end() if leading else 0) + 2
                                                                    and re.match(NAMED_PART, marked[0], re.I)):
        return 'part', position
    folded = ' '.join(words)
    if any(folded == m or folded.startswith(m + ' ') for m in MATTER):
        return 'matter', position
    return 'distinct', position


def _after_prefix(raw, prefix):
    """The rest of a name after a shared start, matched as written or by letters and digits only
    ("Тёмный экзорцист Том I" after the album "Тёмный экзорцист")."""
    if not prefix:
        return raw
    if raw.casefold().startswith(prefix.casefold()):
        return raw[len(prefix):]
    target = norm(prefix)
    if target:
        for cut in range(1, len(raw) + 1):
            if norm(raw[:cut]) == target and (cut == len(raw) or not raw[cut].isalnum()):
                return raw[cut:]
    return raw


def _labels(values):
    """Label every name against the shared prefix; identical names carry no label at all."""
    values = [_arabic(v) for v in values]
    if len(set(v.casefold() for v in values)) == 1:
        return None, [('same', None)] * len(values)
    prefix = _common_prefix(values)
    return prefix, [label(v, prefix) for v in values]


def book_name(members):
    """The shared start of the file names, without separators or a dangling part marker:
    "Dan Brown - The Lost Symbol" for "Dan Brown - The Lost Symbol - 01 - unknown title"."""
    stems = [_arabic(Path(m['filename']).stem) for m in members]
    prefix, _ = _labels(stems)
    if prefix is None:
        prefix = stems[0]
    name = re.sub(r'[\s._\-–—,:;(#№]+$', '', prefix)
    return text(name) if re.search(r'[^\W\d_]{2}', name) else ''


def check(members, others=(), media=True, durations=True, parts=False):
    """Decide whether these members are the parts of one book.

    members: candidate member dicts (path, filename, metadata, error, missing, duration);
    others: every other catalogued audio file of the same unit and book title that is not
    among the members (protected or already grouped elsewhere); media=False skips the audio
    profile check where the catalog probe is not carried (rendered rows: admission probes
    every part again and refuses differing profiles); durations=False skips the duration check
    for catalog siblings that carry tags only; parts=True asks whether the files are the
    numbered parts of one set while each may be its own book (Sergei 2026-10-13: an M4B part
    with its own chapters), so a part's own title or volume number does not hold.
    Returns {'ok': bool, 'reasons': [...], 'positions': [(disc, track), ...] in member order,
             'basis': str, 'book_name': str}."""
    reasons = []
    result = {'ok': False, 'reasons': reasons, 'positions': [], 'basis': '', 'book_name': ''}
    if len(members) < 2:
        reasons.append('only one part')
        return result
    if len(members) > MAX_PARTS:
        reasons.append('more than %d parts' % MAX_PARTS)
        return result
    if others:
        reasons.append('%d other file(s) with this book title are separate candidates or protected' % len(others))
    units = {unit(m['path'])[::2] for m in members}
    if len(units) != 1:
        reasons.append('parts are in different places')
    if any(m.get('error') or m.get('missing') for m in members):
        reasons.append('a part is unavailable or unreadable')
    if len({Path(m['path']).suffix.casefold() for m in members}) != 1:
        reasons.append('mixed file formats')
    profiles = {_profile(m) for m in members} if media else {'not checked here'}
    if None in profiles:
        reasons.append('audio profile unknown')
    elif len(profiles) != 1:
        reasons.append('mixed recordings (audio profiles differ)')
    if durations and any(not isinstance(m.get('duration'), (int, float)) or m['duration'] <= 0 for m in members):
        reasons.append('a part has no known duration')
    keys = {book_key(m) for m in members}
    if len(keys) != 1 or None in keys:
        reasons.append('parts name different books')
    tags = [_tags(m) for m in members]
    for name in SAME_TAGS:
        if len({norm(t.get(name)) for t in tags}) > 1:
            reasons.append('mixed %s tags (different authors, readers or recordings)' % name.replace('_', ' '))
    from local_identity import narrator_names
    readers = {tuple(sorted(norm(n) for n in narrator_names([text(t.get(k)) for k in NARRATOR_TEXT]))) for t in tags}
    if len(readers) > 1:
        reasons.append('mixed narrators named in comments')
    # Every part is only a chapter or part of the book, judged from the file names and,
    # when they differ, the title tags.
    stems = [_nfc(Path(m['filename']).stem) for m in members]
    stem_prefix, stem_labels = _labels(stems)
    # Every title tag that exists is labelled (Senua C1: a title on one part only, "Book 2 Cathing
    # Fire", still names a separate book); a title equal to the album says nothing.
    album = _nfc(text(tags[0].get('album')))
    present = [_arabic(x) for x in (_nfc(text(t.get('title'))) for t in tags) if x and norm(x) != norm(album)]
    title_labels = []
    if present and not (len(present) == len(members) and len({x.casefold() for x in present}) == 1):
        shared = _common_prefix(present) if len({x.casefold() for x in present}) > 1 else ''
        title_labels = [label(x, album if album and norm(x).startswith(norm(album)) else shared) for x in present]
    for kinds in (() if parts else (stem_labels, title_labels)):
        found = {k for k, _ in kinds}
        if 'volume' in found:
            reasons.append('a volume or book number: the files may be separate books of a series')
            break
        if 'distinct' in found:
            reasons.append('a part has its own title: the files may be separate books or stories')
            break
    # Positions: embedded disc/track numbers, else part numbers in the file names, else disc folders.
    discs = []
    for m, t in zip(members, tags):
        _, folder_disc, kind = unit(m['path'])
        tag_disc, disc_total = _number(t.get('disc') or t.get('discnumber'))
        if folder_disc is not None and tag_disc is not None and tag_disc != folder_disc and kind == 'disc folders':
            reasons.append('disc folder and disc tag disagree')
        discs.append((folder_disc if folder_disc is not None else tag_disc if tag_disc is not None else 1, disc_total))
    tracks = [_number(t.get('track') or t.get('tracknumber')) for t in tags]
    named = [position for _, position in stem_labels] if stem_prefix is not None else [None] * len(members)
    per_disc = {}
    for (disc, _), _m in zip(discs, members):
        per_disc[disc] = per_disc.get(disc, 0) + 1
    if all(track is not None for track, _ in tracks):
        basis = 'embedded track numbers'
        positions = [(disc, track) for (disc, _), (track, _) in zip(discs, tracks)]
        # Futaba F1: when the file names number every part, each number must equal its track
        # number, not just sort the same way ("Метро 2033"/"2034" or "Fallout 3"/"4" as tracks 1, 2).
        # Names that repeat a number ("Часть 2 … 1", "Часть 2 … 2") are sub-part labels: tags decide.
        if all(n is not None for n in named) and len(set(zip([d for d, _ in discs], named))) == len(named):
            if any(n != track for n, (track, _) in zip(named, tracks)):
                reasons.append('the numbers in the file names differ from the track numbers')
    elif any(track is not None for track, _ in tracks):
        basis = ''
        positions = []
        reasons.append('only some parts carry a track number')
    elif all(n is not None for n in named):
        basis = 'part numbers in the file names'
        positions = [(disc, n) for (disc, _), n in zip(discs, named)]
    elif all(count == 1 for count in per_disc.values()) and len(per_disc) == len(members) and any(unit(m['path'])[1] is not None for m in members):
        basis = 'one file per disc or part folder'
        positions = [(disc, 1) for disc, _ in discs]
    else:
        basis = ''
        positions = []
        reasons.append('playback order unclear (no track or part numbers)')
    if positions:
        if len(set(positions)) != len(positions):
            reasons.append('duplicate part numbers')
        for disc in sorted(per_disc):
            numbers = sorted(p for d, p in positions if d == disc)
            if numbers and numbers[0] not in (0, 1):
                reasons.append('numbering does not start at 1 (parts before %d missing)' % numbers[0])
            elif numbers and numbers != list(range(numbers[0], numbers[0] + len(numbers))):
                reasons.append('gap in part numbers')
        if sorted(per_disc) != list(range(1, len(per_disc) + 1)):
            reasons.append('missing disc or part folder')
        for (disc, disc_total), (track, total) in zip(discs, tracks):
            if total is not None and total != per_disc.get(disc):
                reasons.append('a part says %d parts, %d found' % (total, per_disc.get(disc, 0)))
                break
            if disc_total is not None and disc_total != len(per_disc):
                reasons.append('a part says %d discs, %d found' % (disc_total, len(per_disc)))
                break
    reasons[:] = list(dict.fromkeys(reasons))
    result.update(ok=not reasons, positions=positions, basis=basis, book_name=book_name(members))
    return result


def plan(members, blocked=(), chaptered=frozenset()):
    """Group eligible single-file members into split books.

    members: member dicts of files that are currently single-file candidates (not protected);
    blocked: member dicts of every other catalogued audio file (protected or in a multi-file
    group), so a book title shared with any of them holds the cluster; chaptered: paths of M4B
    parts known to carry their own chapters (found at admission). Such parts are never joined:
    each is its own book (Sergei 2026-10-13), so their cluster is never grouped.
    Returns (groups, holds): groups = [{'scope', 'unit', 'key', 'members', 'positions', 'basis',
    'book_name'}], holds = [{'unit', 'key', 'paths', 'reasons'}]."""
    clusters = {}
    for m in members:
        key = book_key(m)
        if key is None:
            continue
        place = unit(m['path'])
        clusters.setdefault((place[0], place[2], key[1]), []).append(m)
    others = {}
    for m in blocked:
        key = book_key(m)
        if key is not None:
            place = unit(m['path'])
            others.setdefault((place[0], place[2], key[1]), []).append(m)
    groups, holds = [], []
    for (folder, kind, key), items in sorted(clusters.items(), key=lambda kv: kv[0]):
        if len(items) < 2:
            continue
        items = sorted(items, key=lambda m: m['path'])
        verdict = check(items, others.get((folder, kind, key), ()))
        if any(m['path'] in chaptered for m in items):
            verdict['ok'] = False
            verdict['reasons'].append('parts carry their own chapters: each part is its own book (Sergei 2026-10-13)')
        if not verdict['ok']:
            holds.append({'unit': folder, 'kind': kind, 'key': key, 'paths': [m['path'] for m in items], 'reasons': verdict['reasons']})
            continue
        order = sorted(range(len(items)), key=lambda i: verdict['positions'][i])
        groups.append({'scope': folder + '\x1fSplit book ' + key + ('' if kind == 'folder' else '\x1f' + kind),
                       'unit': folder, 'kind': kind, 'key': key, 'members': [items[i] for i in order],
                       'positions': [verdict['positions'][i] for i in order], 'basis': verdict['basis'], 'book_name': verdict['book_name']})
    return groups, holds
