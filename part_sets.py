"""Whole .m4b parts of one folder: one book split into files, separate volumes of a series, or a question for Sergei.

Sergei's ruling 19 ("parts of a bigger book are connected in the correct order to form the bigger book") and 19a (M4B parts
are joined keeping each part's chapters, re-encoded once), extended 2026-10-24 for parts without an explicit part marker:
a read-only classification of the library's bare-numbered sets ("Геном 1", "Геном 2") found most of them to be one book
split into files and only a few to be real volumes ("Торадора! Том 1-10"). The chapter lists of the parts decide:

  join      the chapter numbering continues across every file ("Глава 35" -> "Глава 36"), or end matter (Эпилог,
            Послесловие, afterword) appears only in the last file and every file carries the same title tag;
  volumes   never joined: every file ends with its own author's afterword, every file starts its numbering again
            ("Глава 1" / "Пролог"), or every file names its own work; a volume of a series keeps ruling 15's naming;
  ask       "Part of a bigger book" with the proposed order and "Approve as one book", never joined on its own:
            season/episode chapters (s01e10 -> s02e01, "Эпизод 10" -> "Эпизод 11"), a joined book over 30 hours, book or
            volume words in the names ("Книга первая", "Book 2", "Том 2": outside knowledge decides), several authors (a
            fairy-tale chest), files naming several works ("Альфа 1", "Альфа 2", "Бета"), and any set the chapters do not
            settle (story collections "Миры Джорджа Мартина 1/2");
  missing   the track numbers say parts are missing ("Незнакомцы 1/3", "2/3"): a Missing files row naming them.

Pure: decide() takes the parts in order with their tags, durations and chapter titles; no file or catalog access."""
import re
import unicodedata

VERSION = 'part-sets-v1'
LONG_HOURS = 30
_STEMS = ('перв', 'втор', 'трет', 'четверт', 'пят', 'шест', 'седьм', 'восьм', 'девят', 'десят', 'одиннадцат', 'двенадцат',
          'тринадцат', 'четырнадцат', 'пятнадцат', 'шестнадцат', 'семнадцат', 'восемнадцат', 'девятнадцат', 'двадцат')
ORDINALS = {stem + ending: n for n, stem in enumerate(_STEMS, 1) for ending in ('ая', 'ый', 'ой', 'ий', 'ья', 'ей', 'ое', 'ье')}
ROMAN = re.compile(r'^(?=[ivxlc]+$)(c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$', re.I)
_TOKEN = r'\s*[#№:\-–—]?\s*([0-9]{1,4}|[ivxlc]{1,7}\b|[а-яё]+)'
# Chapter numbers: "Глава 12", "Chapter 3", "Эпизод 99", "Глава седьмая", "12 ГЛАВА", a leading "016." / "0018 -", "Часть 11".
CHAPTER_WORD = re.compile(r'(?<![^\W\d_])(?:глава|гл\.|chapter|ch\.|эпизод|episode|фрагмент|строфа)' + _TOKEN, re.I)
PART_WORD = re.compile(r'(?<![^\W\d_])(?:часть|part)' + _TOKEN, re.I)
TRAILING_WORD = re.compile(r'(?<![^\W\d_])([0-9]{1,4})\s*(?:глава|chapter)\b', re.I)
LEADING = re.compile(r'^\s*([0-9]{1,4})(?:[-.][0-9]{1,3})?\s*(?:[.)\-–—:]|\s)')
# A file that starts its numbering again: its first chapter is the prologue or chapter one ("Пролог", "Глава 1", "Том II.
# Пролог"); a section name first ("Ракетный удар. Глава 1", "Владычица теней, глава 1") is a part of the book going on.
START_AGAIN = re.compile(r'^\W*(?:(?:том|volume|vol\.)\s*[0-9ivxlc]{1,6}\W+)?(?:пролог|prologue|prolog|(?:глава|chapter|часть|part|эпизод|episode)'
                         r'\s*(?:0*1|i|первая|one)(?![\w])|0*1\s*[.)\-–—:])', re.I)
# A volume of a series ("Торадора! Том 3", "Volume 2"): with every file starting again, separate books (ruling 15).
TOME_WORDS = re.compile(r'(?<![^\W\d_])(?:том|volume|vol\.)\s*(?:[0-9]{1,3}|[ivxlc]{1,6}\b)', re.I)
END_MATTER = re.compile(r'(?<![^\W\d_])(?:эпилог|послесловие|afterword|epilogue|от автора)', re.I)
AUTHOR_AFTERWORD = re.compile(r'(?<![^\W\d_])(?:послесловие автора|авторское послесловие|afterword|от автора)', re.I)
SEASON = re.compile(r'(?<![^\W\d_])(?:s\d{1,2}\s*e\d{1,3}|season\s*\d|сезон\s*\d)', re.I)
# Senua's 0.22.0 review, N3: an episode number that is not inside a chapter ("Эпизод 11", not "Глава 7. Эпизод 2") marks
# episodes of a series, which ruling 19b asks about like seasons.
EPISODE = re.compile(r'(?<![^\W\d_])(?:эпизод|episode)' + _TOKEN, re.I)
CHAPTER_WORD_ONLY = re.compile(r'(?<![^\W\d_])(?:глава|гл\.|chapter|ch\.)', re.I)
VOLUME_WORDS = re.compile(r'(?<![^\W\d_])(?:книга|book)\s*(?:[0-9]{1,3}|[ivxlc]{1,6}\b|первая|вторая|третья|четвертая|четвёртая|'
                          r'пятая|шестая|one|two|three)', re.I)
AUTHOR_DASH = re.compile(r'^\s*([^\W\d_][^\W\d_.]+(?:\s+[^\W\d_][^\W\d_.]*\.?){1,3})\s+[-–—]\s+\S')


def read_chapters(paths, stop=None, timeout=60):
    """{path: [chapter titles]} read with ffprobe (read only, no window); None for a file that could not be read."""
    import json
    import shutil
    import subprocess
    executable = shutil.which('ffprobe')
    found = {}
    for path in paths:
        if stop is not None and stop.is_set():
            raise InterruptedError()
        found[path] = None
        if not executable:
            continue
        try:
            raw = subprocess.run([executable, '-v', 'error', '-protocol_whitelist', 'file', '-show_chapters', '-of', 'json', str(path)],
                                 stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if raw.returncode == 0:
                data = json.loads(raw.stdout.decode('utf-8', 'replace') or '{}')
                found[path] = [str((c.get('tags') or {}).get('title', '')) for c in data.get('chapters') or []]
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return found


def parts_of(row, chapters):
    """decide()'s parts for a catalog row (its members in the row's order) and the chapters read for them."""
    from pathlib import Path
    parts = []
    for m in row.get('members') or []:
        tags = {str(k).casefold(): str(v) for k, v in ((m.get('metadata') or {}).get('tags') or {}).items()}
        parts.append({'name': Path(m['path']).stem, 'title': tags.get('title', ''), 'track': tags.get('track') or tags.get('tracknumber') or '',
                      'hours': float(m.get('duration') or 0) / 3600, 'credits': ' | '.join(tags.get(k, '') for k in ('author', 'composer', 'album_artist')),
                      'chapters': chapters.get(m['path'])})
    return parts


def _nfc(value):
    return unicodedata.normalize('NFC', str(value or ''))


def _value(token):
    token = token.casefold().replace('ё', 'е')
    if token.isdigit():
        return int(token)
    if ROMAN.match(token):
        total, previous = 0, 0
        for char in reversed(token):
            value = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}[char]
            total += -value if value < previous else value
            previous = max(previous, value)
        return total or None
    return ORDINALS.get(token)


def chapter_number(title):
    """The number a chapter title carries ("Глава 12. Холден" -> 12, "Глава седьмая" -> 7, "016. Глава 9" -> 9), else None.
    A chapter word wins over a part word ("Часть вторая. Глава 65" -> 65)."""
    title = _nfc(title)
    for pattern in (CHAPTER_WORD, TRAILING_WORD):
        for token in pattern.findall(title):
            value = _value(token)
            if value is not None:
                return value
    match = LEADING.match(title)
    if match:
        return int(match[1])
    for token in PART_WORD.findall(title):
        value = _value(token)
        if value is not None:
            return value
    return None


def _episode(title):
    """True for a title numbered as an episode and not as a chapter ("Эпизод 11", "Episode two")."""
    title = _nfc(title)
    return not CHAPTER_WORD_ONLY.search(title) and any(_value(token) is not None for token in EPISODE.findall(title))


def _numbers(chapters):
    return [n for n in (chapter_number(c) for c in chapters) if n is not None]


def _work(value):
    from local_identity import work_name
    from source_identity import norm
    return norm(work_name(re.sub(r'^\s*[0-9][0-9.\-]*\s*', '', _nfc(value))))


def _tracks(parts):
    out = []
    for p in parts:
        match = re.fullmatch(r'\s*(\d{1,4})\s*(?:/\s*(\d{1,4}))?\s*', str(p.get('track') or ''))
        out.append((int(match[1]), int(match[2]) if match[2] else None) if match else (None, None))
    return out


def decide(parts):
    """parts: [{'name' (file name without extension), 'title' (title tag), 'track', 'hours', 'credits' (author, composer and
    album-artist tags in one string), 'chapters': [chapter titles] or None when they could not be read}] in their order. Returns {'decision': join | volumes | ask | missing,
    'basis', 'version', and 'missing' / 'total' for missing}."""
    def result(decision, basis, **more):
        return dict({'decision': decision, 'basis': basis, 'version': VERSION}, **more)
    if len(parts) < 2:
        return result('ask', 'one part')
    if any(p.get('chapters') is None for p in parts):
        return result('ask', 'unreadable')
    chapters = [[_nfc(c) for c in p['chapters']] for p in parts]
    titles = [_nfc(p.get('title') or '') for p in parts]
    names = [_nfc(p.get('name') or '') for p in parts]
    numbers = [_numbers(c) for c in chapters]
    restarts = [bool(c) and bool(START_AGAIN.match(c[0])) for c in chapters]
    afterwords = [bool(c) and bool(AUTHOR_AFTERWORD.search(c[-1])) for c in chapters]
    works = [_work(t or n) for t, n in zip(titles, names)]
    credited = [m[1].casefold() for c in chapters for m in (AUTHOR_DASH.match(t) for t in c) if m]
    caution = ''
    if any(SEASON.search(t) or _episode(t) for t in titles + names + [t for c in chapters for t in c]):
        caution = 'seasons'
    elif any(VOLUME_WORDS.search(t) for t in titles + names + [t for c in chapters for t in c[:3]]):
        caution = 'book_words'
    elif len({_nfc(p.get('credits') or '').casefold() for p in parts}) > 1 or len(set(credited)) > 1 and len(credited) * 2 >= sum(len(c) for c in chapters):
        caution = 'authors'  # several authors or readers credited: a disc set of tales, an anthology
    elif any(TOME_WORDS.search(t) for t in titles + names):
        caution = 'book_words'  # N3: "Том 1 / Том 2" like "Книга 1 / 2"; tome-named volumes that start again stay volumes below
    # Volumes of a series: never joined.
    if all(afterwords):
        return result('volumes', 'each file ends with its own afterword')
    # Parts the track numbers say are missing ("Незнакомцы 1/3", "2/3"; a story missing from a collection).
    tracks = _tracks(parts)
    if all(t is not None for t, _ in tracks):
        have = sorted(t for t, _ in tracks)
        total = max([n for _, n in tracks if n] + have)
        missing = [n for n in range(1, total + 1) if n not in have]
        if missing:
            return result('missing', 'parts missing', missing=missing, total=total)
    if not any(chapters):
        # No chapters to compare (the split rules refused these files as one book): they stay books of their own.
        return result('volumes', 'no chapters to compare')
    # Every file starting again or naming its own work: volumes, unless book or season words leave it to Sergei.
    if all(restarts) or len(set(works)) == len(parts) and '' not in works:
        if caution and not any(TOME_WORDS.search(t) for t in titles + names):
            return result('ask', caution)
        return result('volumes', 'each file starts again at chapter 1' if all(restarts) else 'each file names its own work')
    if caution:
        return result('ask', caution)
    if sum(float(p.get('hours') or 0) for p in parts) > LONG_HOURS:
        return result('ask', 'long')
    # N3: files naming two or more works (not one each: that is the volumes rule above) hold several works, so they are asked
    # ("Альфа 1", "Альфа 2", "Бета", "Гамма"). The row shows the "chapters don't settle it" sentence (todo_causes).
    if len({w for w in works if w}) > 1:
        return result('ask', 'works')
    # One book split into files.
    def continues(before, after):
        return bool(before and after) and after[0] in (before[-1], before[-1] + 1) and after[0] > 1
    if all(continues(a, b) for a, b in zip(numbers, numbers[1:])):
        return result('join', 'chapter numbering continues')
    ends = [any(END_MATTER.search(t) for t in c) for c in chapters]
    # "The files share one title tag": the same title, a part number at its end aside ("Пепел Вавилона 1", "2").
    if ends[-1] and not any(ends[:-1]) and all(works) and len(set(works)) == 1:
        return result('join', 'end matter only in the last file')
    return result('ask', 'unclear')
