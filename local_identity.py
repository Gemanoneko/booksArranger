"""Local-agreement work identity (Sergei decision 2026-10-12).

When the embedded tags and the file/folder names of one recording agree on the
title and the author, that agreement is the book's identity; no Internet
confirmation is required. Pure functions only: no file, network or database
access. Every decision is recorded field by field (which local fields agreed and
how) so it stays explainable and can be revalidated against the current row.

Field states:
  green  - an embedded tag and a file/folder name agree in the same script
  yellow - they agree across scripts/languages (transliteration, word order)
  red    - local sources name different values for the field (a real conflict)
  grey   - fewer than two independent local sources carry the field (missing)

Only title and author decide identity. A red title, author, series or number
keeps the book on the existing research/review path; grey optional fields are
gaps for the Internet or are omitted. Order of name words never matters.
"""
import hashlib
import itertools
import re
import unicodedata
from pathlib import Path

from source_identity import filename_identity, norm, text

AGREEMENT_VERSION = 'local-agree-v1'
STATES = ('green', 'yellow', 'red', 'grey')
AUTHOR_TAGS = ('author', 'album_artist', 'albumartist', 'artist')
NARRATOR_TAGS = ('narrator', 'reader', 'performer')
# Credits that name no person ("Collection", "Various"): never an author.
NOT_PEOPLE = {'сборник', 'сборники', 'антология', 'various', 'variousartists', 'variousauthors', 'разные', 'разныеавторы',
              'коллективавторов', 'авторскийколлектив', 'неизвестен', 'неизвестныйавтор', 'unknown', 'unknownartist', 'аноним', 'народное', 'народные'}
# Folders that organise the library rather than name a book or person.
CONTAINER_NAMES = {'unsorted', 'audiobooks', 'аудиокниги', 'audio', 'books', 'книги', 'mp3', 'новое', 'new', 'incoming', 'downloads'}
DISC = re.compile(r'(?:cd|disc|disk|диск|часть|part)[ _.-]*\d{1,3}', re.I)

# ---------------------------------------------------------------- name keys
# Consonant skeleton in a shared alphabet. Vowels, y/й and h/х are dropped and
# doubled consonants collapse, so "Rollins"/"Роллинс" -> RLNS, "James"/"Джеймс"
# -> GMS, "Stephen"/"Стивен" -> STVN. Only used across scripts.
CYRILLIC = {
    'б': 'B', 'в': 'V', 'г': 'G', 'д': 'D', 'ж': 'G', 'з': 'S', 'к': 'K', 'л': 'L', 'м': 'M', 'н': 'N', 'п': 'P',
    'р': 'R', 'с': 'S', 'т': 'T', 'ф': 'V', 'х': '', 'ц': 'TS', 'ч': 'C', 'ш': 'X', 'щ': 'XC',
    'а': '', 'е': '', 'ё': '', 'и': '', 'й': '', 'о': '', 'у': '', 'ы': '', 'э': '', 'ю': '', 'я': '', 'ь': '', 'ъ': '',
    'і': '', 'ї': '', 'є': '', 'ґ': 'G', 'ў': ''}
LATIN_MULTI = (('dzh', 'G'), ('sch', 'X'), ('tch', 'C'), ('zh', 'G'), ('dj', 'G'), ('sh', 'X'), ('ph', 'V'), ('th', 'T'),
               ('ck', 'K'), ('kh', ''), ('gh', ''), ('qu', 'KV'), ('x', 'KS'))
LATIN_SINGLE = {'b': 'B', 'd': 'D', 'f': 'V', 'g': 'G', 'j': 'G', 'k': 'K', 'l': 'L', 'm': 'M', 'n': 'N', 'p': 'P', 'q': 'K',
                'r': 'R', 's': 'S', 't': 'T', 'v': 'V', 'z': 'S', 'h': '', 'y': '', 'a': '', 'e': '', 'i': '', 'o': '', 'u': ''}
PEOPLE_SEPARATOR = re.compile(r'\s[-–—&]\s|[,;/]|\s(?:и|and)\s', re.I)
PATRONYMIC = re.compile(r'(?:[а-я]+(?:ович|евич|ич|овна|евна|ична|инична))|(?:[a-z]+(?:ovich|evich|ovna|evna|ichna))')


def script(value):
    value = str(value or '')
    if re.search('[А-Яа-яЁёІіЇїЄєҐґЎў]', value):
        return 'cyrillic'
    folded = ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c))
    if re.search('[A-Za-z]', folded):
        return 'latin'
    return 'other'


def words(value):
    """Name/title words in order, casefolded, ё->е, without punctuation or digits."""
    return re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)?", str(value or '').casefold().replace('ё', 'е'))


def _collapse(key):
    return re.sub(r'(.)\1+', r'\1', key)


def _cyrillic_keys(word):
    base = ''.join(CYRILLIC.get(c, '') for c in word.replace('дж', 'ж').replace('тч', 'ч').replace('тс', 'ц'))
    keys = {_collapse(base)}
    # Russian renders a Latin initial H as Г (Гарри = Harry) as well as Х.
    if word[:1] == 'г':
        keys.add(_collapse(base[1:]))
    return {k for k in keys if k}


def _latin_keys(word):
    folded = ''.join(c for c in unicodedata.normalize('NFKD', word) if not unicodedata.combining(c)).lower()
    folded = re.sub(r'[^a-z]', '', folded)
    variants = {folded}
    # Ambiguous English spellings: ch can be ч or к (Michael), w can be в or a vowel
    # (Wells = Уэллс), final s/x are silent in French names (Jules, Dumas, Roux).
    for old, options in (('rz', ('zh',)), ('cz', ('ch',)), ('sz', ('sh',)), ('ch', ('tch', 'k', '')), ('w', ('v', ''))):
        variants |= {v.replace(old, option) for v in variants for option in options if old in v}
    variants |= {v[:-1] for v in variants if len(v) > 3 and v.endswith('j')}
    variants |= {v[:-1] for v in variants if len(v) > 3 and v[-1] in 'sx'}
    keys = set()
    for variant in list(variants)[:16]:
        out = []
        index = 0
        while index < len(variant):
            for old, new in LATIN_MULTI:
                if variant.startswith(old, index):
                    out.append(new)
                    index += len(old)
                    break
            else:
                char = variant[index]
                if char == 'c':
                    out.append('S' if variant[index + 1:index + 2] in ('e', 'i', 'y') else 'K')
                else:
                    out.append(LATIN_SINGLE.get(char, ''))
                index += 1
        key = _collapse(''.join(out))
        if key:
            keys.add(key)
    return keys


def _ending(word):
    """Feminine/plural -a endings separate Петров from Петрова across scripts."""
    return 'a' if word[-1:] in ('a', 'а', 'я') else 'other'


def word_keys(word):
    kind = script(word)
    if kind == 'cyrillic':
        return _cyrillic_keys(word)
    if kind == 'latin':
        return _latin_keys(word)
    return set()


def _significant(tokens):
    """Drop initials and patronymics; they never decide a name match."""
    kept, dropped = [], []
    for token in tokens:
        if len(token) == 1 or PATRONYMIC.fullmatch(token):
            dropped.append(token)
        else:
            kept.append(token)
    return kept, dropped


def _pair(a, b):
    """'same' (identical word), 'cross' (transliteration across scripts) or None."""
    if a == b:
        return 'same'
    if script(a) == script(b) or 'other' in (script(a), script(b)):
        return None
    if _ending(a) != _ending(b):
        return None
    shared = word_keys(a) & word_keys(b)
    return 'cross' if shared and max(len(k) for k in shared) >= 1 else None


def compare_names(left, right):
    """Order-insensitive person-name comparison.

    Returns None when the names differ, else {'match': 'same'|'cross',
    'subset': bool, 'how': str}. One side may omit given names (surname only)
    or initials/patronymics; every remaining word must pair one to one.
    """
    a, a_dropped = _significant(words(left))
    b, b_dropped = _significant(words(right))
    if not a or not b or len(a) > 5 or len(b) > 5:
        return None
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    # A list of people ("A - B", "A, B", "A и B") is never a fuller form of one name.
    several = any(PEOPLE_SEPARATOR.search(str(v or '')) for v in (left, right))
    if several and len(a) != len(b):
        return None
    best = None
    for chosen in itertools.permutations(large, len(small)):
        kinds = [_pair(x, y) for x, y in zip(small, chosen)]
        if None in kinds:
            continue
        # A cross-script pairing must rest on at least one long, distinctive word.
        if 'cross' in kinds:
            strong = any(kind == 'same' or max((len(k) for k in word_keys(x) & word_keys(y)), default=0) >= 3
                         for kind, x, y in zip(kinds, small, chosen))
            if not strong:
                continue
        kind = 'cross' if 'cross' in kinds else 'same'
        if best is None or (best == 'cross' and kind == 'same'):
            best = kind
    if best is None:
        return None
    subset = len(small) != len(large)
    if subset and len(small) == 1 and len(small[0]) < 3:
        return None
    how = ['word order ignored']
    if best == 'cross':
        how.insert(0, 'same name in another script (transliteration)')
    if subset:
        how.append('one source gives only part of the name')
    if a_dropped or b_dropped:
        how.append('initials/patronymic ignored')
    return {'match': best, 'subset': subset, 'how': '; '.join(how)}


# ---------------------------------------------------------------- titles
ARTICLES = re.compile(r'^(?:the|a|an)\s+', re.I)


def clean_title(value, numbered=False):
    """Remove bracketed notes (narrator, year, edition); leading numbers stay part of a title."""
    value = str(value or '')
    value = re.sub(r'\s*[\[(\{][^\])\}]{0,120}[\])\}]\s*', ' ', value)
    if numbered:
        value = re.sub(r'(?:\s*[-_.,]\s*|\s+)(?:\d{1,4}|часть\s*\d{1,3}|part\s*\d{1,3}|глава\s*\d{1,3})\s*$', '', value, flags=re.I)
    return text(value)


def title_key(value, numbered=False):
    cleaned = clean_title(value, numbered)
    return norm(ARTICLES.sub('', cleaned)) or norm(cleaned)


def _index_stripped(value):
    """A path name may prefix the title with its position: "03. Title", "01 - Title"."""
    return re.sub(r'^\s*\d{1,4}(?:\s*[._-]\s*|\s+)', '', str(value or ''))


def title_segments_match(value, titles):
    """True when a local name, or one of its ' - ' / '. ' segments, is one of the titles."""
    keys = {title_key(t) for t in titles if title_key(t)}
    if not keys:
        return False
    pieces = [value] + re.split(r'\s+[–—-]\s+|\.\s+', str(value or ''))
    for piece in pieces:
        for candidate in (piece, _index_stripped(piece)):
            if title_key(candidate) in keys or title_key(candidate, True) in keys:
                return True
    return False


# ---------------------------------------------------------------- sources
def _tags(member):
    return {str(k).casefold(): v for k, v in member.get('metadata', {}).get('tags', {}).items()}


def _path_components(row, root):
    """Most specific first: file name (if it names a book), parent, grandparent folders."""
    members = row.get('members', [])
    single = len(members) == 1
    components = []
    for member in members[:1] if single else []:
        components.append({'kind': 'file name', 'value': Path(member['filename']).stem, 'numbered': False})
    # File names of a multi-file recording usually repeat "Author - Title NN".
    if not single:
        stems = {title_key(Path(m['filename']).stem, True) for m in members}
        if len(stems) == 1 and next(iter(stems)) and filename_identity(members[0]['filename']).get('author'):
            components.append({'kind': 'file names', 'value': Path(members[0]['filename']).stem, 'numbered': True})
    folders = {str(Path(m['path']).parent) for m in members}
    if len(folders) != 1:
        # Disc folders under one book folder share the grandparent.
        parents = {str(Path(f).parent) for f in folders}
        if len(parents) == 1 and all(DISC.fullmatch(Path(f).name.strip()) for f in folders):
            folders = parents
        else:
            return components
    folder = Path(next(iter(folders)))
    if DISC.fullmatch(folder.name.strip()):
        folder = folder.parent
    root_key = norm(str(Path(root))) if root else None
    for level, kind in ((folder, 'folder'), (folder.parent, 'parent folder')):
        if root_key is not None and (norm(str(level)) == root_key or len(norm(str(level))) <= len(root_key)):
            break
        name = level.name.strip()
        if not name or norm(name) in CONTAINER_NAMES:
            break
        components.append({'kind': kind, 'value': name, 'numbered': False})
    return components


def _segments(value, numbered):
    parsed = filename_identity(value + '.x')
    pieces = [clean_title(value, numbered)]
    if parsed.get('author'):
        pieces += [parsed['author'], clean_title(parsed['title'], numbered)]
    for part in re.split(r'\s+[–—-]\s+|\.\s+', value):
        part = clean_title(part, numbered)
        if part and part not in pieces:
            pieces.append(part)
    return [p for p in pieces if p], parsed


def _embedded(row):
    """Consistent embedded title/author/series across every member, or a conflict."""
    members = row.get('members', [])
    found = {'title': None, 'author': None, 'series': None, 'number': None, 'conflicts': [], 'ignored': []}
    albums = {text(_tags(m).get('album')) for m in members}
    if len(members) == 1 and albums == {''}:
        albums = {text(_tags(members[0]).get('title'))}
        field = 'title'
    else:
        field = 'album'
    keys = {title_key(a) for a in albums if a}
    if len(keys) > 1 or (keys and '' in albums):
        found['conflicts'].append({'field': 'title', 'detail': 'embedded %s differs between files' % field})
    elif keys:
        found['title'] = {'kind': 'embedded', 'field': field, 'value': next(a for a in albums if a)}
    credits = {}
    for name in AUTHOR_TAGS:
        values = {text(_tags(m).get(name)) for m in members}
        if values == {''}:
            continue
        if len(values) > 1:
            found['conflicts'].append({'field': 'author', 'detail': 'embedded %s differs between files' % name})
            continue
        if norm(next(iter(values))) in NOT_PEOPLE:
            found['ignored'].append({'field': name, 'value': next(iter(values)), 'why': 'names no person (collection or various authors)'})
            continue
        credits[name] = next(iter(values))
    narrators = {text(_tags(m).get(n)) for m in members for n in NARRATOR_TAGS} - {''}
    people = []
    for name in AUTHOR_TAGS:
        value = credits.get(name)
        if not value:
            continue
        if any(compare_names(value, n) for n in narrators):
            found['ignored'].append({'field': name, 'value': value, 'why': 'same as the narrator tag'})
            continue
        if not any(compare_names(value, p['value']) for p in people):
            people.append({'kind': 'embedded', 'field': name, 'value': value})
    found['people'] = people
    found['author'] = people[0] if len(people) == 1 else None
    for name, key in (('series', 'series'), ('number', 'series-part')):
        values = {text(_tags(m).get(key) or _tags(m).get(key.replace('-', '_'))) for m in members}
        if values == {''}:
            continue
        if len(values) > 1:
            found['conflicts'].append({'field': name, 'detail': 'embedded %s differs between files' % name})
        else:
            found[name] = {'kind': 'embedded', 'field': key, 'value': next(iter(values))}
    return found


def _supports_title(title, components, author_value):
    key = title_key(title)
    authors = [author_value] if author_value else []
    for component in components:
        pieces, _ = _segments(component['value'], component['numbered'])
        for piece in pieces:
            piece_key = title_key(piece, component['numbered'])
            if piece_key and key in (piece_key, title_key(_index_stripped(piece), component['numbered'])):
                return component
            # "Author Title" or "Title Author" written without a separator.
            for author in authors:
                for variant in (' '.join(words(author)), ' '.join(reversed(words(author)))):
                    if piece_key in (norm(variant) + key, key + norm(variant)):
                        return component
    return None


def _supports_author(author, components):
    best = None
    for component in components:
        pieces, parsed = _segments(component['value'], component['numbered'])
        # A structured "Author - Title" name supports only through its author part;
        # a bare folder name supports only when it is short enough to be a name.
        if parsed.get('author'):
            pieces = [parsed['author']]
        elif len(words(component['value'])) > 4:
            continue
        for piece in pieces:
            result = compare_names(author, piece)
            if result and (best is None or (best[1]['match'] == 'cross' and result['match'] == 'same')
                           or (best[1]['subset'] and not result['subset'])):
                best = (component, result, piece)
    return best


def _contradicts(components, title, author):
    """Structured 'Author - Title' names that pair one local value with a different other value."""
    found = []
    for component in components:
        parsed = filename_identity(component['value'] + '.x')
        if not parsed.get('author'):
            continue
        claimed_author, claimed_title = parsed['author'], clean_title(parsed['title'], component['numbered'])
        if title and title_key(claimed_title, component['numbered']) == title_key(title) and author and not compare_names(author, claimed_author):
            found.append({'field': 'author', 'detail': '%s "%s" credits a different author' % (component['kind'], component['value'])})
        if author and compare_names(author, claimed_author) and title and title_key(claimed_title, component['numbered']) != title_key(title):
            found.append({'field': 'title', 'detail': '%s "%s" names a different book by this author' % (component['kind'], component['value'])})
    return found


def folder_siblings(database, row, limit=2000):
    """Other catalogued audio files directly in this candidate's folders (read-only query)."""
    import contextlib
    import json
    import sqlite3
    members = row.get('members', [])
    own = {m['path'] for m in members}
    folders = {str(Path(m['path']).parent) for m in members}
    found = []
    with contextlib.closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
        db.execute('PRAGMA query_only=ON')
        for folder in sorted(folders)[:20]:
            prefix = folder.rstrip('\\/') + '\\'
            pattern = prefix.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
            for path, metadata in db.execute("SELECT path,metadata FROM files WHERE kind='audiobook' AND missing=0 AND path LIKE ? ESCAPE '!' LIMIT ?", (pattern, limit)):
                if path in own or str(Path(path).parent) != folder:
                    continue
                try:
                    tags = {str(k).casefold(): text(v) for k, v in json.loads(metadata).get('tags', {}).items()}
                except (ValueError, TypeError, AttributeError):
                    tags = {}
                found.append({'path': path, 'filename': Path(path).name, 'tags': tags})
    return found


def agreement(row, root='', siblings=None):
    """Field-by-field local agreement record for one candidate row.

    siblings: other audio files in the same folder(s), from folder_siblings()."""
    embedded = _embedded(row)
    components = _path_components(row, root)
    fields = {}
    conflicts = list(embedded['conflicts'])
    ignored = list(embedded['ignored'])
    title = embedded['title']
    author = embedded['author']
    if len(embedded['people']) > 1:
        # Two different people in author/artist credits (often author and narrator). Resolve
        # only when an author folder names exactly one of them and no file or folder name
        # mentions any other; otherwise it is a real conflict.
        def named(person, kinds):
            return any(compare_names(person['value'], piece) for c in components if c['kind'] in kinds
                       for piece in ([filename_identity(c['value'] + '.x').get('author')] if filename_identity(c['value'] + '.x').get('author') else []) + [c['value']] if piece)
        folders = [p for p in embedded['people'] if named(p, ('folder', 'parent folder'))]
        everywhere = [p for p in embedded['people'] if named(p, ('file name', 'file names', 'folder', 'parent folder'))]
        if len(folders) == 1 and everywhere == folders:
            author = folders[0]
            ignored += [{'field': p['field'], 'value': p['value'], 'why': 'not named in any file or folder name; treated as a recording credit, not the author'}
                        for p in embedded['people'] if p is not author]
        else:
            first, second = embedded['people'][:2]
            conflicts.append({'field': 'author', 'detail': 'embedded %s "%s" and %s "%s" name different people' % (first['field'], first['value'], second['field'], second['value'])})
    if siblings and any(s.get('unreadable') for s in siblings):
        # Fail closed: without the folder contents a part of a larger book cannot be ruled out.
        conflicts.append({'field': 'title', 'detail': 'the other files in this folder could not be checked', 'force': True})
    elif title and siblings:
        # Other audio files beside this candidate with the same title: it may be one part
        # (chapter, disc, volume file) of a larger book, so its own files are not the whole book.
        key = title_key(title['value'])
        # "Title 1" beside "Title 2": a numbered part of one book split into files.
        base = title_key(title['value'], True)
        numbered = base != key
        def part_of_same(sibling):
            names = [v for v in (sibling['tags'].get('album'), sibling['tags'].get('title'), Path(sibling['filename']).stem) if v]
            return numbered and any(title_key(_index_stripped(v), True) == base for v in names)
        same = [s for s in siblings if key in {title_key(v) for v in (s['tags'].get('album'), s['tags'].get('title')) if v}
                or _supports_title(title['value'], [{'kind': 'sibling', 'value': Path(s['filename']).stem, 'numbered': True}], author['value'] if author else '')
                or part_of_same(s)]
        if same:
            conflicts.append({'field': 'title', 'detail': '%d other file(s) in the same folder carry this title; this may be only part of the book' % len(same), 'force': True})
    # Author first: a title written together with the author needs the author's words.
    if author:
        support = _supports_author(author['value'], components)
        if support:
            component, result, piece = support
            # Keep the fuller credit as written; the tag wins a tie (natural word order).
            fuller = piece if len(_significant(words(piece))[0]) > len(_significant(words(author['value']))[0]) else author['value']
            fields['author'] = {'state': 'yellow' if result['match'] == 'cross' else 'green', 'value': text(fuller),
                                'sources': [author, {'kind': component['kind'], 'value': component['value'], 'matched': piece}],
                                'how': result['how'], 'partial': len(_significant(words(fuller))[0]) < 2}
    if title:
        component = _supports_title(title['value'], components, author['value'] if author else '')
        if component:
            fields['title'] = {'state': 'green', 'value': clean_title(title['value']),
                               'sources': [title, {'kind': component['kind'], 'value': component['value']}],
                               'how': 'same title after removing brackets, track numbers and punctuation'}
    for contradiction in _contradicts(components, title['value'] if title else '', author['value'] if author else ''):
        if contradiction['field'] not in fields:
            conflicts.append(contradiction)
    # An embedded credit conflict outranks any path support for the author, and a shared
    # folder title outranks title support.
    if any(c['field'] == 'author' and c['detail'].startswith('embedded') for c in conflicts):
        fields.pop('author', None)
    if any(c['field'] == 'title' and c.get('force') for c in conflicts):
        fields.pop('title', None)
    for name, value in (('title', title), ('author', author)):
        if name in fields:
            continue
        if any(c['field'] == name for c in conflicts):
            fields[name] = {'state': 'red', 'value': value['value'] if value else '', 'sources': [value] if value else [],
                            'how': '; '.join(c['detail'] for c in conflicts if c['field'] == name)}
        else:
            available = [value] if value else []
            path_only = [] if value else [{'kind': c['kind'], 'value': c['value']} for c in components[:1]]
            fields[name] = {'state': 'grey', 'value': value['value'] if value else '', 'sources': available + path_only,
                            'how': 'only one local source names it' if value or path_only else 'no local source names it'}
    for name in ('series', 'number'):
        value = embedded[name]
        if any(c['field'] == name for c in conflicts):
            fields[name] = {'state': 'red', 'value': '', 'sources': [], 'how': '; '.join(c['detail'] for c in conflicts if c['field'] == name)}
            continue
        if not value:
            fields[name] = {'state': 'grey', 'value': '', 'sources': [], 'how': 'no embedded %s tag' % name}
            continue
        target = embedded['series']['value'] if name == 'number' and embedded['series'] else value['value']
        supported = None
        for component in components:
            if norm(target) and norm(target) in norm(component['value']):
                if name == 'series' or re.search(r'(?<!\d)0*' + re.escape(value['value'].lstrip('0') or '0') + r'(?!\d)', component['value']):
                    supported = component
                    break
        fields[name] = ({'state': 'green', 'value': value['value'], 'sources': [value, {'kind': supported['kind'], 'value': supported['value']}],
                         'how': 'embedded tag repeated in the %s' % supported['kind']} if supported else
                        {'state': 'grey', 'value': value['value'], 'sources': [value], 'how': 'only the embedded tag names it'})
    accepted = fields['title']['state'] in ('green', 'yellow') and fields['author']['state'] in ('green', 'yellow') \
        and not any(fields[n]['state'] == 'red' for n in ('series', 'number'))
    if fields['series']['state'] != 'green' or fields['number']['state'] != 'green':
        series = {}
    else:
        series = {'name': fields['series']['value'], 'number': fields['number']['value']}
    gaps = []
    if accepted:
        if script(fields['title']['value']) != 'latin':
            gaps.append('original_title')
        if not series:
            gaps.append('series')
        if fields['author'].get('partial'):
            gaps.append('author_full')
    return {'version': AGREEMENT_VERSION, 'accepted': accepted, 'fields': fields, 'series': series, 'gaps': gaps,
            'ignored': ignored, 'conflicts': conflicts,
            'path': [{'kind': c['kind'], 'value': c['value']} for c in components]}


def author_forms(record):
    """Every local spelling of the agreed author, as written."""
    forms = []
    for source in record['fields']['author']['sources']:
        for value in (source.get('value'), source.get('matched')):
            value = text(value)
            if value and compare_names(value, record['fields']['author']['value']) and value not in forms:
                forms.append(value)
    return forms


def title_forms(record):
    forms = [record['fields']['title']['value']]
    for source in record['fields']['title']['sources']:
        value = clean_title(source.get('value'))
        if value and title_key(value) == title_key(forms[0]) and value not in forms:
            forms.append(value)
    return forms


def work_id(record):
    title = title_key(record['fields']['title']['value'])
    author = '|'.join(sorted(words(record['fields']['author']['value'])))
    return 'local:' + hashlib.sha256((title + '\x1f' + author).encode('utf-8')).hexdigest()[:24]


def summary(record):
    """Compact, explainable record stored with the metadata facts."""
    def field(name):
        value = record['fields'][name]
        return {'state': value['state'], 'value': value['value'], 'how': value['how'],
                'sources': [{k: s[k] for k in ('kind', 'field', 'value') if k in s} for s in value['sources'] if s][:4]}
    return {'version': AGREEMENT_VERSION, 'title': field('title'), 'author': field('author'),
            'series': field('series'), 'number': field('number'), 'gaps': list(record['gaps']),
            'ignored': [dict(i) for i in record['ignored']][:6]}


def revalidate(row, root, recorded, siblings=None):
    """Re-derive agreement from the current row; refuse any drift."""
    current = agreement(row, root, siblings)
    if not current['accepted']:
        raise ValueError('Local identity evidence no longer agrees')
    for name in ('title', 'author', 'series', 'number'):
        if current['fields'][name]['state'] != recorded[name]['state'] or current['fields'][name]['value'] != recorded[name]['value']:
            raise ValueError('Local identity evidence changed')
    return current
