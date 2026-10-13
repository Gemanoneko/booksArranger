"""Local-agreement work identity (Sergei decision 2026-10-12).

When the embedded tags and the file/folder names of one recording agree on the
title and the author, that agreement is the book's identity; no Internet
confirmation is required. Pure functions except folder_siblings(), which reads
the app's own catalog read-only. Every decision is recorded field by field
(which local fields agreed and how) so it stays explainable and can be
revalidated against the current row.

Field states:
  green  - an embedded tag and a file/folder name agree in the same script
  yellow - they agree across scripts (a transliteration of the same name, any word order)
  red    - local sources name different values, or the credit is not an author (conflict)
  grey   - fewer than two independent local sources carry the field (missing)

Only title and author decide identity. A red title, author, series or number
keeps the book on the existing research/review path; grey optional fields are
gaps for the Internet or are omitted. Order of name words never matters.

Never an author: narrator/reader credits (читает, исп., read by ...) and collection
credits (Сборник, Разные авторы ...). Sergei's rulings (2026-10-13):
  1. a collection compiled or read by a narrator, clear from two local signals, is
     filed under the collections root (Сборники); the narrator is only the narrator;
  2. a title spelled slightly differently in the tag and the file name agrees; the tag wins;
  3. one author written several ways gets one canonical spelling (canonical_author);
  4. a generic title such as "Сборник рассказов" is accepted when the author agrees.
"""
from collections import Counter
import hashlib
import itertools
import re
import unicodedata
from pathlib import Path

from source_identity import filename_identity, norm, text

AGREEMENT_VERSION = 'local-agree-v4'
# Records written by earlier versions keep validating (approved and completed books).
KNOWN_AGREEMENT_VERSIONS = ('local-agree-v3', AGREEMENT_VERSION)
# Sergei ruling 1 (2026-10-13) names these readers as narrator-compilers of collections. Under a
# collection folder, a plain credit of exactly this person, who the library also credits as a
# reader, is the narrator, never the author. Князев is not listed: two different Князевs read
# books in this library (Игорь, Владимир) and the ruling names only the surname.
RULED_NARRATORS = ('Олег Булдаков',)
STATES = ('green', 'yellow', 'red', 'grey')
AUTHOR_TAGS = ('author', 'album_artist', 'albumartist', 'artist')
# composer is not used: in this library it holds the author as often as the reader.
NARRATOR_TAGS = ('narrator', 'reader', 'performer')
FREE_TEXT_TAGS = ('comment', 'description', 'synopsis', 'lyrics', 'album_artist', 'albumartist', 'artist', 'author', 'title', 'album')
VARIOUS_AUTHORS = {'разныеавторы', 'various', 'variousauthors', 'variousartists', 'коллективавторов', 'авторскийколлектив', 'многоавторов'}
COLLECTION_LABEL = 'Разные авторы'
# Credits that name no person ("Collection", "Various"): never an author, and no fall-through.
NOT_PEOPLE = {'сборник', 'сборники', 'антология', 'various', 'variousartists', 'variousauthors', 'разные', 'разныеавторы',
              'коллективавторов', 'авторскийколлектив', 'неизвестен', 'неизвестныйавтор', 'unknown', 'unknownartist', 'аноним', 'народное', 'народные',
              'антологии', 'сборникрассказов', 'коллекция', 'collection', 'anthology', 'compilation', 'многоавторов'}
# Reader/narrator markers: a credit or name carrying one is a recording credit, never the author.
NARRATOR_MARKER = re.compile(r'(?<![^\W\d_])(?:читает|читают|читала|читал|чит\.|исполняет|исполняют|исполнил[аи]?|исп\.|озвучил[аи]?|озвучивает|озвучка|'
                             r'чтец|чтица|начитал[аи]?|начитывает|read\s+by|narrated\s+by|narrators?|readers?|performed\s+by)(?![^\W\d_])', re.I)
# Collections need the collection research path, never a single local author.
COLLECTION_FOLDER = re.compile(r'(?<![^\W\d_])(?:сборник\w*|антологи\w*|anthology|anthologies|collections?|компиляци\w*)(?![^\W\d_])', re.I)
COLLECTION_TITLE = re.compile(r'(?<![^\W\d_])(?:сборник\w*|антологи\w*|коллекци\w*|избранное|рассказы|повести|stories|anthology|collection|omnibus)(?![^\W\d_])', re.I)
# A title that names only a part, chapter or numbered file of a book.
PART_TITLE = re.compile(r'(?:^|\s|[-–—.,:(])(?:глава|часть|ч\.|chapter|part|cd|disc|диск|track|трек)\s*\d{1,3}\s*\)?\s*$|'
                        r'(?<=[^\W\d_])\s+\d{1,2}\s*$|^\W*\d{1,4}\W*$', re.I)
# Folders that organise the library rather than name a book or person.
CONTAINER_NAMES = {'unsorted', 'audiobooks', 'аудиокниги', 'audio', 'books', 'книги', 'mp3', 'новое', 'new', 'incoming', 'downloads'}
DISC = re.compile(r'(?:cd|disc|disk|диск|часть|part)[ _.-]*\d{1,3}', re.I)
PART_SEGMENT = re.compile(r'\W*(?:(?:глава|часть|ч\.|chapter|part|cd|disc|диск|track|трек)\s*)?\d{1,4}\W*', re.I)
TRAILING_PART = re.compile(r'(?:\s*[-_.,]\s*|\s+)(?:\d{1,3}|(?:часть|ч\.|part|глава|chapter|том|vol\.?)\s*\d{1,3})\s*$', re.I)
PART_FOLDER = re.compile(r'(?:\(|\s|^)(?:часть|ч\.|part|cd|disc|диск|том|vol\.?|volume)\s*\d{1,3}\)?\s*$', re.I)
PEOPLE_SEPARATOR = re.compile(r'\s[-–—]\s|[&,;/\\]|\s(?:и|and)\s', re.I)
PATRONYMIC = re.compile(r'(?:[а-я]+(?:ович|евич|ич|овна|евна|ична|инична))|(?:[a-z]+(?:ovich|evich|ovna|evna|ichna))')
# A first name alone never identifies an author (it may only be part of a full name).
GIVEN_NAMES = set('''
александр алексей анатолий андрей антон аркадий артем артём артур борис вадим валентин валерий василий виктор виталий владимир владислав
всеволод вячеслав геннадий георгий герман глеб григорий даниил денис дмитрий евгений егор иван игорь илья кирилл константин лев леонид максим
марк михаил никита николай олег павел петр пётр роман руслан сергей станислав степан тимур федор фёдор юрий ярослав яков эдуард
александра алена алёна алина алла анастасия анна валентина вера виктория галина дарья евгения екатерина елена ирина кира лариса любовь
людмила марина мария наталья наталия наташа надежда ольга светлана софья татьяна юлия яна уна
джеймс джон роберт майкл уильям дэвид ричард джозеф томас чарльз кристофер дэниел мэтью энтони стивен пол эндрю джордж эдвард тимоти фрэнк
питер адам дуглас терри джо гарри филип дэн нил бен клайв дин рэй мэри дженнифер элизабет сара лора энн джейн урсула генри брэндон брендон грэм
james john robert michael william david richard joseph thomas charles christopher daniel matthew anthony mark donald steven stephen paul
andrew kenneth kevin brian george edward ronald timothy jason jeffrey ryan jacob gary nicholas eric jonathan larry justin scott brandon frank
benjamin gregory samuel raymond patrick alexander jack dennis jerry tyler aaron henry peter adam douglas nathan walter harold carl arthur
gerald roger keith jeremy terry lawrence sean christian albert joe ethan jesse bruce bryan ralph roy jordan eugene wayne louis alan philip
harry vincent dan neil ben clive dean ray mary patricia jennifer linda elizabeth barbara susan jessica sarah karen nancy lisa margaret betty
sandra ashley dorothy emily donna michelle carol amanda melissa deborah stephanie rebecca laura sharon cynthia kathleen amy helen anna nicole
ruth katherine samantha christine emma catherine rachel janet maria heather julie joyce victoria kelly joan lauren alice jane ursula una
лена марта влад фрэнсис анджей фриц грейди тимоти рэмси дрю колин джоан джош саймон тим гай брэйден брейден джульет ник энди иэн нейт джеральд
джемма йон тодд барбара гордон карлос кэтрин алекс кристина ханну кодзи содзи киноко митио стэнли стенли алджернон бентли крейг айзек
martha neal fritz grady thimoty colin josh simon tim algernon bentley craig isaac jesper jeff rick shaun stanley gordon mitchel michio kinoko
andrzej guy nick andy ian nate gerald gemma jon todd barbara carlos catherine alex kristina hannu koji soji graham
'''.split())
NAME_PARTICLES = {'de', 'van', 'von', 'der', 'le', 'la', 'du', 'di', 'da', 'де', 'ван', 'фон', 'дер', 'ле', 'ла', 'дю', 'ди', 'да'}
INITIALS = re.compile(r'^(?:[^\W\d_]\.){1,3}[^\W\d_]?\.?$')

# ---------------------------------------------------------------- transliteration
# Across scripts two words are the same name only when their consonants match in
# order AND every vowel sound is spelled in a way standard Russian transcription
# allows (Stephen/Стивен, Rollins/Роллинс, Hawking/Хокинг). Different vowels are
# different names: King/Кинг but not Kong or Хокинг.
CYR_CONS = {'б': 'B', 'в': 'V', 'г': 'G', 'д': 'D', 'ж': 'G', 'з': 'S', 'к': 'K', 'л': 'L', 'м': 'M', 'н': 'N', 'п': 'P',
            'р': 'R', 'с': 'S', 'т': 'T', 'ф': 'V', 'ц': 'TS', 'ч': 'C', 'ш': 'X', 'щ': 'XC', 'ґ': 'G'}
CYR_VOWELS = set('аеёиоуыэюяйіїєў')
CYR_SIMPLE = {'а': 'a', 'е': 'e', 'ё': 'e', 'и': 'i', 'й': 'y', 'о': 'o', 'у': 'u', 'ы': 'y', 'э': 'e', 'ю': 'yu', 'я': 'ya',
              'і': 'i', 'ї': 'yi', 'є': 'ye', 'ў': 'u'}
LAT_VOWELS = set('aeiouy')
LATIN_SINGLE = {'b': 'B', 'd': 'D', 'f': 'V', 'g': 'G', 'j': 'G', 'k': 'K', 'l': 'L', 'm': 'M', 'n': 'N', 'p': 'P', 'q': 'K',
                'r': 'R', 's': 'S', 't': 'T', 'v': 'V', 'z': 'S'}
# Longest first; each option is a list of tokens.
LATIN_CHOICES = (('dzh', ([('C', 'G')],)), ('sch', ([('C', 'X')],)), ('tch', ([('C', 'C')],)), ('zh', ([('C', 'G')],)),
                 ('dj', ([('C', 'G')],)), ('sh', ([('C', 'X')],)), ('ph', ([('C', 'V')],)), ('th', ([('C', 'T')],)),
                 ('ck', ([('C', 'K')],)), ('kh', ([],)), ('gh', ([],)), ('ch', ([('C', 'C')], [('C', 'K')], [])),
                 ('qu', ([('C', 'K'), ('C', 'V')],)), ('x', ([('C', 'K'), ('C', 'S')],)), ('w', ([('C', 'V')], [('V', 'w')])))
# Russian vowel cluster -> English spellings that standard transcription renders that way
# (beyond the plain letter-for-letter transliteration, which is always accepted).
VOWEL_TABLE = {
    'а': {'a', 'u', 'o', 'aa', 'au'}, 'э': {'a', 'e', 'ae', 'ai', 'ea', 'aa'},
    'е': {'e', 'a', 'ea', 'ai', 'ay', 'ee', 'ie', 'ae', 'aa', 'u', 'ei', 'eu'},
    'ей': {'a', 'ay', 'ai', 'ei', 'ey', 'ea', 'ae', 'aye'}, 'эй': {'a', 'ay', 'ai', 'ei', 'ey', 'ea', 'ae', 'aye'},
    'и': {'i', 'e', 'ee', 'ea', 'y', 'ie', 'ey', 'ei', 'ui'}, 'ий': {'y', 'i', 'iy', 'ii', 'ie', 'yi'}, 'ый': {'y', 'yi', 'iy'},
    'ай': {'i', 'y', 'ai', 'ei', 'ie', 'igh', 'uy', 'ay', 'ey', 'ae'}, 'аи': {'ai', 'i'},
    'о': {'o', 'a', 'au', 'aw', 'oa', 'ou', 'oe', 'eo', 'ow'}, 'оу': {'o', 'ow', 'oa', 'ou', 'oe'}, 'ой': {'oy', 'oi', 'oye'},
    'у': {'u', 'oo', 'ou', 'ue', 'ew', 'o', 'w', 'wo'}, 'ю': {'u', 'ew', 'eu', 'ue', 'iu', 'yu'}, 'я': {'ya', 'ia', 'a', 'ja', 'ie'},
    'уэ': {'we', 'wa', 'ue', 'wae'}, 'уи': {'wi', 'wee', 'ui', 'wy'}, 'уо': {'wo', 'wa', 'wau', 'waw'}, 'уа': {'wa', 'ua'},
    'ау': {'ou', 'ow', 'au'}, 'ио': {'io', 'eo'}, 'аа': {'aa', 'a'}}


def script(value):
    value = str(value or '')
    if re.search('[А-Яа-яЁёІіЇїЄєҐґЎў]', value):
        return 'cyrillic'
    folded = ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c))
    if re.search('[A-Za-z]', folded):
        return 'latin'
    return 'other'


def words(value):
    """Name/title words in order, NFC, casefolded, ё->е, without punctuation or digits."""
    value = unicodedata.normalize('NFC', str(value or '')).casefold().replace('ё', 'е')
    return re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)?", value)


def _finish(tokens):
    """Merge adjacent vowels into one cluster and collapse repeated consonants."""
    out = []
    for kind, value in tokens:
        if out and kind == 'V' and out[-1][0] == 'V':
            out[-1] = ('V', out[-1][1] + value)
        elif out and kind == 'C' and out[-1] == ('C', value):
            continue
        else:
            out.append((kind, value))
    return tuple(out)


def _latin_variants(word):
    folded = ''.join(c for c in unicodedata.normalize('NFKD', word) if not unicodedata.combining(c)).lower()
    folded = re.sub(r'[^a-z]', '', folded)
    found = {folded}
    if folded.startswith('mc') and len(folded) > 3:
        found.add('mac' + folded[2:])                      # McNeill = Макнилл
    for value in list(found):
        if len(value) > 3 and value.endswith('e') and value[-2] not in LAT_VOWELS:
            found.add(value[:-1])                          # silent final e: Doyle, Clive
        if len(value) > 4 and value.endswith('es') and value[-3] not in LAT_VOWELS:
            found.add(value[:-2] + 's')                    # James, Charles
    for old, new in (('rz', 'zh'), ('cz', 'ch'), ('sz', 'sh')):  # Polish: Andrzej = Анджей
        found |= {v.replace(old, new) for v in found if old in v}
    found |= {v[:-1] + 'y' for v in found if len(v) > 3 and v.endswith('j')}   # final j is й
    return sorted(found)


def _latin_sequences(word):
    out = []

    def expand(value, index, tokens):
        if len(out) >= 64:
            return
        if index >= len(value):
            out.append(_finish(tokens))
            return
        for pattern, options in LATIN_CHOICES:
            if value.startswith(pattern, index):
                for option in options:
                    expand(value, index + len(pattern), tokens + option)
                return
        char = value[index]
        if char in LAT_VOWELS:
            token = [('V', char)]
        elif char == 'c':
            token = [('C', 'S')] if value[index + 1:index + 2] in ('e', 'i', 'y') else [('C', 'K')]
        elif char == 'h':
            token = []
        else:
            token = [('C', LATIN_SINGLE[char])] if char in LATIN_SINGLE else []
        expand(value, index + 1, tokens + token)

    for variant in _latin_variants(word):
        expand(variant, 0, [])
    return set(out)


def _cyrillic_sequences(word):
    word = unicodedata.normalize('NFC', word).replace('дж', 'ж').replace('тч', 'ч')
    variants = [word] + ([word[1:]] if word.startswith('г') else [])   # Г for a Latin H: Гарри = Harry
    out = set()
    for variant in variants:
        tokens = []
        for char in variant:
            if char in CYR_VOWELS:
                tokens.append(('V', char))
            elif char in CYR_CONS:
                tokens += [('C', c) for c in CYR_CONS[char]]
            # х (Latin h/kh), ь and ъ carry no consonant of their own here
        out.add(_finish(tokens))
    return out


def _vowels_agree(latin, cyrillic):
    cyrillic = cyrillic.replace('ё', 'е')
    if latin == ''.join(CYR_SIMPLE.get(c, '') for c in cyrillic):
        return True
    return latin in VOWEL_TABLE.get(cyrillic, ())


def _same_sound(latin, cyrillic):
    if len(latin) != len(cyrillic):
        return False
    for (kind_a, value_a), (kind_b, value_b) in zip(latin, cyrillic):
        if kind_a != kind_b:
            return False
        if kind_a == 'C' and value_a != value_b:
            return False
        if kind_a == 'V' and not _vowels_agree(value_a, value_b):
            return False
    return True


def transliterated(a, b):
    """True when one Latin and one Cyrillic word are the same name."""
    if script(a) == script(b) or 'other' in (script(a), script(b)):
        return False
    latin, cyrillic = (a, b) if script(a) == 'latin' else (b, a)
    left, right = _latin_sequences(latin), _cyrillic_sequences(cyrillic)
    return any(_same_sound(x, y) for x in sorted(left) for y in sorted(right))


def _consonants(word):
    sequences = _cyrillic_sequences(word) if script(word) == 'cyrillic' else _latin_sequences(word)
    return max((sum(kind == 'C' for kind, _ in s) for s in sequences), default=0)


def _letter_classes(letter):
    """Sound classes a name may start with, so an initial can stand for a word in either script."""
    if script(letter) == 'cyrillic':
        if letter in CYR_VOWELS:
            return {'V'}
        return {'C:' + CYR_CONS.get(letter, '?')[:1]} | ({'C:H'} if letter in ('г', 'х') else set())
    if letter in LAT_VOWELS:
        return {'V'}
    return {'c': {'C:K', 'C:S', 'C:C'}, 'h': {'C:H'}, 'w': {'C:V', 'V'}, 'x': {'C:K'}}.get(letter, {'C:' + LATIN_SINGLE.get(letter, '?')})


def _initial_fits(initial, word):
    if script(initial) == script(word):
        return word.startswith(initial)
    return bool(_letter_classes(initial) & _letter_classes(word[:1]))



def _pair(a, b):
    """'same' (identical word), 'cross' (same name in the other script) or None."""
    if a == b:
        return 'same'
    return 'cross' if transliterated(a, b) else None


def _parts(value):
    tokens = words(value)
    full = [t for t in tokens if len(t) > 1]
    initials = [t for t in tokens if len(t) == 1]
    dropped = []
    # A patronymic is dropped only from a name of 3+ words that keeps 2+ other words;
    # -ович/-евич/-ич surnames (Гжендович, Костюкевич) are surnames otherwise.
    if len(full) >= 3:
        for token in list(full):
            if PATRONYMIC.fullmatch(token) and len(full) - 1 >= 2:
                full.remove(token)
                dropped.append(token)
                break
    return full, initials, dropped


def compare_names(left, right):
    """Order-insensitive person-name comparison.

    Returns None when the names differ, else {'match': 'same'|'cross', 'subset': bool,
    'exact': bool, 'how': str}. Every full word pairs one to one; an initial pairs with a
    word starting the same way. One side may name only part of the name (surname only),
    never just a first name, and never one person out of a list of several.
    """
    a, a_initials, a_dropped = _parts(left)
    b, b_initials, b_dropped = _parts(right)
    if not a or not b or len(a) > 5 or len(b) > 5:
        return None
    several = any(PEOPLE_SEPARATOR.search(str(v or '')) for v in (left, right))
    (small, small_initials), (large, large_initials) = sorted(((a, a_initials), (b, b_initials)), key=lambda side: len(side[0]))
    best = None
    for chosen in itertools.permutations(range(len(large)), len(small)):
        kinds = [_pair(small[i], large[j]) for i, j in enumerate(chosen)]
        if None in kinds:
            continue
        if 'cross' in kinds and not any(kind == 'same' or _consonants(small[i]) >= 2 for i, kind in enumerate(kinds)):
            continue
        extra = [large[j] for j in range(len(large)) if j not in chosen]
        unused = list(small_initials)
        expanded = False
        for word in list(extra):
            fit = next((i for i in unused if _initial_fits(i, word)), None)
            if fit is not None:
                unused.remove(fit)
                extra.remove(word)
                expanded = True
        # Initials written on both sides must pair one to one, letter for letter:
        # "Стругацкий А." is not "Стругацкий Б.", "Толстой А.Н." is not "Толстой Л.Н.".
        other = list(large_initials)
        for initial in list(unused):
            fit = next((x for x in other if x == initial or _initial_fits(initial, x)), None)
            if fit is not None:
                other.remove(fit)
                unused.remove(initial)
        if unused and other:
            continue
        # An initial left over beside an unmatched full word names a different first name.
        if unused and extra:
            continue
        kind = 'cross' if 'cross' in kinds else 'same'
        rank = (len(extra), kind == 'cross')
        if best is None or rank < best[0]:
            best = (rank, kind, extra, unused + other, expanded)
    if best is None:
        return None
    _, kind, extra, unused, expanded = best
    subset = bool(extra)
    if subset:
        if several or len(extra) > 2:
            return None
        # Only a surname may stand for the full name; a first name alone never does.
        if len(small) == 1 and (len(small[0]) < 3 or norm(small[0]) in GIVEN_NAMES):
            return None
    how = ['word order ignored']
    if kind == 'cross':
        how.insert(0, 'same name in another script (transliteration)')
    if subset:
        how.append('one source gives only the surname')
    if a_dropped or b_dropped or unused or a_initials and not b_initials or b_initials and not a_initials:
        how.append('initials/patronymic ignored')
    exact = not subset and not (a_dropped or b_dropped or unused or expanded)
    return {'match': kind, 'subset': subset, 'exact': exact, 'expanded': expanded, 'how': '; '.join(how)}


def middle_initial_same(left, right, spellings=()):
    """'Dick Philip K.' = 'Дик Филип Киндред': the surname and the first name are written in full
    on both sides and only the middle name is an initial on one side.

    Never an initial standing for a first name (Senua R2-2: "Толстой А." stays apart from
    "Толстой Алексей"), and never when any library spelling of the same first name and
    surname carries a different middle name or middle initial (two different people)."""
    match = compare_names(left, right)
    if not match or match['subset'] or not match['expanded']:
        return False
    (short, short_initials, _), (large, large_initials, _) = sorted((_parts(left), _parts(right)), key=lambda side: len(side[0]))
    if len(short) < 2 or len(large) != len(short) + 1 or len(short_initials) != 1 or large_initials:
        return False
    # An initial written first ("M. Mary Smith") is a first-name initial, never a middle one (Senua minor).
    written = words(left if len(_parts(left)[0]) == len(short) else right)
    if written and len(written[0]) == 1:
        return False
    if not any(norm(word) in GIVEN_NAMES for word in short):
        return False
    middle = [word for word in large if not any(_pair(word, s) for s in short)]
    if len(middle) != 1 or not _initial_fits(short_initials[0], middle[0]):
        return False
    for spelling in spellings:
        full, initials, _ = _parts(spelling)
        core = [word for word in full if any(_pair(word, s) for s in short)]
        if len(core) != len(short):
            continue
        if any(not _pair(word, middle[0]) for word in full if word not in core) or any(not _initial_fits(i, middle[0]) for i in initials):
            return False
    return True


def slip_same(left, right):
    """One word differs by a single letter in the same script (a doubled letter, "Pratchet" /
    "Pratchett"), every other word identical; words of 6+ letters only. Used only to adopt a
    spelling that fetched catalog evidence confirms (confirmed_spellings)."""
    a, b = words(left), words(right)
    if len(a) != len(b) or len(a) < 2:
        return False
    rest = list(b)
    unmatched = []
    for word in a:
        if word in rest:
            rest.remove(word)
        else:
            unmatched.append(word)
    if len(unmatched) != 1 or len(rest) != 1:
        return False
    x, y = unmatched[0], rest[0]
    return script(x) == script(y) != 'other' and min(len(x), len(y)) >= 6 and _edits(x, y, 1) == 1 and x[0] == y[0]


def same_person(left, right):
    """Two credits merge only on a full match: no extra or dropped word. The same words
    (initials and patronymics included, any order) are always the same credit."""
    if words(left) and sorted(words(left)) == sorted(words(right)):
        return True
    match = compare_names(left, right)
    return bool(match and match['exact'])


def narrator_names(texts):
    """Names that follow a reader/narrator marker ("читает: Олег Булдаков", "исп. Роман Волков")."""
    found = []
    for value in texts:
        value = unicodedata.normalize('NFC', str(value or ''))
        for match in NARRATOR_MARKER.finditer(value):
            tail = re.split(r'[,;\n(\[|]|\s[-–—]\s|\.\s', value[match.end():].lstrip(' :.-–—'), maxsplit=1)[0]
            # Only the leading name words: no web addresses, handles or numbers.
            name = []
            for token in tail.split():
                if not re.fullmatch(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*\.?", token):
                    break
                name.append(token)
            name = ' '.join(name[:4])
            if len(words(name)) >= 1:
                found.append(name)
    return found


# ---------------------------------------------------------------- titles
ARTICLES = re.compile(r'^(?:the|a|an)\s+', re.I)
QUOTES = '"\'«»“”„‟‹›`'


def clean_title(value, numbered=False):
    """Remove bracketed notes, invisible format characters and stray quotes; numbers stay."""
    value = unicodedata.normalize('NFC', str(value or ''))
    value = ''.join(c for c in value if unicodedata.category(c) != 'Cf')
    value = re.sub(r'\s*[\[(\{][^\])\}]{0,120}[\])\}]\s*', ' ', value)
    if numbered:
        value = re.sub(r'(?:\s*[-_.,]\s*|\s+)(?:\d{1,4}|часть\s*\d{1,3}|part\s*\d{1,3}|глава\s*\d{1,3})\s*$', '', value, flags=re.I)
    value = text(value)
    for _ in range(2):
        for opening, closing in (('«', '»'), ('“', '”'), ('"', '"'), ("'", "'"), ('„', '“')):
            if value.endswith(closing) and value.count(opening if opening != closing else closing) < (1 if opening != closing else 2):
                value = value[:-1].rstrip()
            if value.startswith(opening) and value.count(closing if opening != closing else opening) < (1 if opening != closing else 2):
                value = value[1:].lstrip()
    return text(value)


def title_key(value, numbered=False):
    cleaned = clean_title(value, numbered)
    return norm(ARTICLES.sub('', cleaned)) or norm(cleaned)


def _index_stripped(value):
    """A path name may prefix the title with its position: "03. Title", "01 - Title"."""
    return re.sub(r'^\s*\d{1,4}(?:\s*[._-]\s*|\s+)', '', str(value or ''))


def _title_part_candidates(value, numbered):
    """The whole name, its title part, and the LAST real segment of that part.

    "Series 03. Title" and "Author - Series - Title" end with the book title; an
    earlier segment ("Траун" in "Траун. Союзники") is a series, never the title.
    """
    parsed = filename_identity(value + '.x')
    part = parsed['title'] if parsed.get('author') else value
    candidates = [value, part]
    segments = [s for s in re.split(r'\s+[–—-]\s+|\.\s+', part) if s.strip()]
    while segments and (PART_SEGMENT.fullmatch(segments[-1].strip()) or not re.search(r'[^\W\d_]', segments[-1])):
        segments.pop()
    if segments:
        candidates.append(segments[-1])
    out = []
    for candidate in candidates:
        for form in (candidate, _index_stripped(candidate)):
            key = title_key(form, numbered)
            if key and key not in out:
                out.append(key)
    return out, parsed


def title_segments_match(value, titles):
    """True when a local name, its title part or its last segment is one of the titles."""
    keys = {title_key(t) for t in titles if title_key(t)}
    if not keys:
        return False
    for numbered in (False, True):
        candidates, _ = _title_part_candidates(str(value or ''), numbered)
        if keys.intersection(candidates):
            return True
    return False


# ---------------------------------------------------------------- sources
def _tags(member):
    return {str(k).casefold(): v for k, v in member.get('metadata', {}).get('tags', {}).items()}


def _book_folder(row):
    """The folder that names the book: the common folder, or the parent of its disc/part folders."""
    members = row.get('members', [])
    folders = {str(Path(m['path']).parent) for m in members}
    if len(folders) != 1:
        parents = {str(Path(f).parent) for f in folders}
        if len(parents) == 1 and all(DISC.fullmatch(Path(f).name.strip()) for f in folders):
            return Path(next(iter(parents)))
        return None
    folder = Path(next(iter(folders)))
    return folder.parent if DISC.fullmatch(folder.name.strip()) else folder


def _path_components(row, root):
    """Most specific first: file name (if it names a book), parent, grandparent folders."""
    members = row.get('members', [])
    single = len(members) == 1
    components = []
    for member in members[:1] if single else []:
        components.append({'kind': 'file name', 'value': Path(member['filename']).stem, 'numbered': False})
    # File names of a multi-file recording usually repeat "Author - Title NN".
    if not single and row.get('split_book'):
        # Split book (v0.15.0): the shared start of the part names ("Dan Brown - The Lost Symbol"
        # of "Dan Brown - The Lost Symbol - 01 - unknown title"), re-derived from the files.
        from split_books import book_name
        shared = book_name(members)
        if shared:
            components.append({'kind': 'file names', 'value': shared, 'numbered': False})
    elif not single:
        stems = {title_key(Path(m['filename']).stem, True) for m in members}
        if len(stems) == 1 and next(iter(stems)) and filename_identity(members[0]['filename']).get('author'):
            components.append({'kind': 'file names', 'value': Path(members[0]['filename']).stem, 'numbered': True})
    folder = _book_folder(row)
    if folder is None:
        return components
    root_key = norm(str(Path(root))) if root else None
    for level, kind in ((folder, 'folder'), (folder.parent, 'parent folder')):
        if root_key is not None and (norm(str(level)) == root_key or len(norm(str(level))) <= len(root_key)):
            break
        name = level.name.strip()
        if not name or norm(name) in CONTAINER_NAMES:
            break
        components.append({'kind': kind, 'value': name, 'numbered': False})
    return components


def _ancestors(row, root):
    """Every folder name between the library root and the files."""
    names = []
    root_key = norm(str(Path(root))) if root else None
    for member in row.get('members', [])[:1]:
        for level in Path(member['path']).parents:
            if root_key is not None and len(norm(str(level))) <= len(root_key):
                break
            names.append(level.name)
    return names


def _person_pieces(component):
    """Name pieces a path component offers for an author; reader-marked pieces are excluded."""
    parsed = filename_identity(component['value'] + '.x')
    if parsed.get('author'):
        pieces = [parsed['author']]
    elif len(words(component['value'])) > 4:
        return []
    else:
        pieces = [clean_title(component['value'])]
    return [p for p in pieces if p and not NARRATOR_MARKER.search(p) and not re.search(r'\d', p)]


def _embedded(row):
    """Consistent embedded title/author/series across every member, or a conflict."""
    members = row.get('members', [])
    found = {'title': None, 'author': None, 'series': None, 'number': None, 'conflicts': [], 'ignored': [], 'people': [], 'collection_credits': []}
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
    texts = [text(_tags(m).get(n)) for m in members[:3] for n in FREE_TEXT_TAGS]
    readers = [text(_tags(m).get(n)) for m in members for n in NARRATOR_TAGS] + narrator_names(texts)
    found['readers'] = sorted({r for r in readers if r})
    credits = {}
    for name in AUTHOR_TAGS:
        values = {text(_tags(m).get(name)) for m in members}
        if values == {''}:
            continue
        if len(values) > 1:
            found['conflicts'].append({'field': 'author', 'detail': 'embedded %s differs between files' % name})
            continue
        value = next(iter(values))
        if norm(value) in NOT_PEOPLE:
            # No fall-through to another credit: a collection is never credited to a person.
            found['conflicts'].append({'field': 'author', 'detail': 'embedded %s "%s" names a collection, not an author' % (name, value)})
            found['collection_credits'].append(value)
            continue
        if NARRATOR_MARKER.search(value):
            found['ignored'].append({'field': name, 'value': value, 'why': 'reader/narrator credit, never the author'})
            continue
        credits[name] = value
    people = []
    for name in AUTHOR_TAGS:
        value = credits.get(name)
        if not value:
            continue
        if any(compare_names(value, r) for r in found['readers']):
            found['ignored'].append({'field': name, 'value': value, 'why': 'same person as the reader/narrator credit'})
            continue
        if not any(same_person(value, p['value']) for p in people):
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


def _edits(a, b, limit):
    """Levenshtein distance, stopping as soon as it exceeds limit."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i]
        for j, char_b in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char_a != char_b)))
        if min(current) > limit:
            return limit + 1
        previous = current
    return previous[-1]


def _typo(a, b):
    """A spelling slip between two title keys: same digits and script, one letter different
    (two in titles of 15+ letters). Different volume numbers are never a typo."""
    if not a or not b or a == b or re.findall(r'\d+', a) != re.findall(r'\d+', b) or script(a) != script(b):
        return False
    shortest = min(len(a), len(b))
    if shortest < 6:
        return False
    limit = 1 if shortest < 15 else 2
    return _edits(a, b, limit) <= limit


def _title_support(title, components, author_value):
    """(component, how) for the first name that agrees with the tag title, exactly or by a typo."""
    component = _supports_title(title, components, author_value)
    if component:
        return component, 'same title after removing brackets, track numbers and punctuation'
    key = title_key(title)
    for component in components:
        candidates, _ = _title_part_candidates(component['value'], component['numbered'])
        if any(_typo(key, candidate) for candidate in candidates):
            return component, 'the tag and the %s differ by a spelling slip; the tag spelling wins (Sergei 2026-10-13)' % component['kind']
    return None


def _supports_title(title, components, author_value):
    key = title_key(title)
    authors = [author_value] if author_value else []
    for component in components:
        candidates, _ = _title_part_candidates(component['value'], component['numbered'])
        if key in candidates:
            return component
        # "Author Title" or "Title Author" written without a separator.
        whole = title_key(component['value'], component['numbered'])
        for author in authors:
            for variant in (' '.join(words(author)), ' '.join(reversed(words(author)))):
                if whole in (norm(variant) + key, key + norm(variant)):
                    return component
    return None


def _supports_author(author, components):
    best = None
    for component in components:
        for piece in _person_pieces(component):
            result = compare_names(author, piece)
            if result and (best is None or (best[1]['match'] == 'cross' and result['match'] == 'same')
                           or (best[1]['subset'] and not result['subset'])):
                best = (component, result, piece)
    return best


def _numbered_part(title, components):
    """A single file named "Title 1" / "Title (часть 1)", or a folder named with a part marker,
    whose name without that number is the book title: one numbered part, not the whole book."""
    key = title_key(title)
    for component in components:
        if component['kind'] not in ('file name', 'folder'):
            continue
        raw = component['value']
        parsed = filename_identity(raw + '.x')
        forms = {_index_stripped(raw), _index_stripped(parsed.get('title') or raw)}
        for form in forms:
            if PART_FOLDER.search(form) and title_key(PART_FOLDER.sub('', form)) == key:
                return component
            if component['kind'] == 'file name':
                cleaned = clean_title(form)
                stripped = TRAILING_PART.sub('', cleaned)
                if stripped != cleaned and title_key(stripped) == key:
                    return component
    return None


def _chapter_only(row, title):
    """The single file's own name or title tag says only "Глава 5", "Part 2" or "05"."""
    member = row['members'][0]
    stem = Path(member['filename']).stem
    parsed = filename_identity(member['filename'])
    track_title = text(_tags(member).get('title'))
    for value in (stem, parsed.get('title') or stem, track_title):
        value = clean_title(value)
        if value and title_key(value) != title_key(title) and PART_SEGMENT.fullmatch(value.strip()):
            # A lone "01" is how some rips name a one-file book; any other bare number, or a
            # chapter/part name, is one piece of a larger book.
            if re.fullmatch(r'\W*0*1\W*', value.strip()):
                continue
            return '"%s"' % value
    return ''


def _claims_person(value):
    """A structured name's author slot makes a person claim only when it looks like a name."""
    return bool(value) and not re.search(r'\d', value) and 1 <= len(words(value)) <= 4 and not NARRATOR_MARKER.search(value)


def _contradicts(components, title, author):
    """Structured 'Author - Title' names that pair one local value with a different other value."""
    found = []
    for component in components:
        parsed = filename_identity(component['value'] + '.x')
        if not parsed.get('author'):
            continue
        claimed_author = parsed['author']
        candidates, _ = _title_part_candidates(component['value'], component['numbered'])
        same_title = bool(title) and (title_key(title) in candidates or any(_typo(title_key(title), c) for c in candidates))
        if same_title and author and _claims_person(claimed_author) and not compare_names(author, claimed_author):
            found.append({'field': 'author', 'detail': '%s "%s" credits a different author' % (component['kind'], component['value'])})
        if author and compare_names(author, claimed_author) and title and not same_title:
            found.append({'field': 'title', 'detail': '%s "%s" names a different book by this author' % (component['kind'], component['value'])})
    return found


UNREADABLE = {'path': '', 'filename': '', 'tags': {}, 'unreadable': True}
_INDEX = {}


def _spelling_keys(value):
    """Blocking keys: the consonant string of each long word, in any script."""
    keys = set()
    for word in words(value):
        if len(word) < 3:
            continue
        sequences = _cyrillic_sequences(word) if script(word) == 'cyrillic' else _latin_sequences(word)
        keys.update(''.join(v for kind, v in seq if kind == 'C') for seq in sequences)
    return {k for k in keys if len(k) >= 2}


def _person_like(value):
    return bool(value) and 2 <= len(words(value)) <= 5 and not re.search(r'\d', value) and not NARRATOR_MARKER.search(value) \
        and norm(value) not in NOT_PEOPLE and norm(value) not in CONTAINER_NAMES and not COLLECTION_FOLDER.search(value)


def catalog_index(database, root):
    """Library-wide facts read once per catalog revision (read-only):

    readers   - every name credited as a reader (narrator/reader/performer tags, or after
                "читает", "исп.", "read by" in any tag); an author with that exact name is held;
    spellings - every author-credit spelling (tags and author folder names) with the number of
                book folders using it, for one canonical spelling per person (ruling 3).
    """
    import contextlib
    import json
    import sqlite3
    with contextlib.closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
        db.execute('PRAGMA query_only=ON')
        has = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='book_catalog_revision'").fetchone()
        revision = db.execute('SELECT revision FROM book_catalog_revision WHERE id=1').fetchone() if has else None
        key = (str(Path(database).resolve()), root, revision[0] if revision else None)
        if revision and key in _INDEX:
            return dict(_INDEX[key], confirmed=confirmed_spellings(database))
        readers = set()
        uses = set()
        root_key = norm(str(Path(root)))
        for path, metadata in db.execute("SELECT path,metadata FROM files WHERE root=? AND kind='audiobook'", (root,)):
            try:
                tags = {str(k).casefold(): str(v) for k, v in json.loads(metadata).get('tags', {}).items()}
            except (ValueError, TypeError, AttributeError):
                continue
            readers.update(text(tags[k]) for k in NARRATOR_TAGS if text(tags.get(k)))
            readers.update(text(n) for n in narrator_names([tags.get(k, '') for k in FREE_TEXT_TAGS]))
            folder = str(Path(path).parent)
            credits = [text(tags.get(k)) for k in AUTHOR_TAGS]
            for level in Path(path).parents:
                if len(norm(str(level))) <= len(root_key):
                    break
                parsed = filename_identity(level.name + '.x')
                credits.append(parsed['author'] if parsed.get('author') else level.name)
            uses.update((folder, c) for c in credits if _person_like(c))
    readers = frozenset(n for n in readers if len(words(n)) >= 2)
    spellings = Counter(unicodedata.normalize('NFC', spelling) for _, spelling in {(folder, unicodedata.normalize('NFC', c)) for folder, c in uses})
    keys = {}
    for spelling in spellings:
        for k in _spelling_keys(spelling):
            keys.setdefault(k, []).append(spelling)
    index = {'readers': readers, 'spellings': dict(spellings), 'keys': keys}
    if revision:
        _INDEX.clear()
        _INDEX[key] = index
    return dict(index, confirmed=confirmed_spellings(database))


_CONFIRMED = {}
# Fetched 'authors' evidence from VERIFIED records only (Senua M5): research results that were
# admitted (state Queued), approved reviews and job manifests. A source URL is present only for
# fetched catalog or publisher pages; local-agreement citations have none. Research that is
# still waiting or held (for example "Author and work not independently verified") never confirms.
CONFIRMED_QUERIES = {
    'automatic_candidates': "SELECT json_extract(e.value,'$.cited_value'),json_extract(e.value,'$.source_url'),c.result FROM "
                            "(SELECT result FROM automatic_candidates WHERE state='Queued' AND json_valid(result) AND json_type(result,'$.metadata_facts')='object') c,"
                            "json_each(c.result,'$.evidence') e WHERE json_extract(e.value,'$.field')='authors'",
    'candidate_context': "SELECT json_extract(e.value,'$.cited_value'),json_extract(e.value,'$.source_url'),NULL FROM "
                         "(SELECT data FROM candidate_context WHERE json_valid(data) AND json_extract(data,'$.metadata_approved')=1) c,"
                         "json_each(c.data,'$.metadata_evidence') e WHERE json_extract(e.value,'$.field')='authors'",
    'audio_jobs': "SELECT json_extract(e.value,'$.cited_value'),json_extract(e.value,'$.source_url'),j.manifest FROM "
                  "(SELECT manifest FROM audio_jobs WHERE json_valid(manifest)) j,json_each(j.manifest,'$.evidence.metadata_fields') e "
                  "WHERE json_extract(e.value,'$.field')='authors'"}
CONFIRMED_KEYS = {'automatic_candidates': "SELECT count(*),max(attempted) FROM automatic_candidates WHERE state='Queued'",
                  'candidate_context': 'SELECT count(*),sum(revision) FROM candidate_context',
                  'audio_jobs': 'SELECT count(*),max(updated) FROM audio_jobs'}


def _record_spellings(record):
    """Author spellings the confirming record itself saw locally (tags, file and folder names)."""
    import json
    seen = set()
    try:
        data = json.loads(record) if isinstance(record, str) else {}
    except ValueError:
        return seen
    for clue in data.get('local_clues') or []:
        if isinstance(clue, dict) and (clue.get('field') in AUTHOR_TAGS or clue.get('field') == 'author'):
            seen.add(text(clue.get('value')))
    for source in data.get('sources') or []:
        if not isinstance(source, dict) or not source.get('path'):
            continue
        tags = {str(k).casefold(): v for k, v in ((source.get('metadata') or {}).get('tags') or {}).items()}
        seen.update(text(tags.get(k)) for k in AUTHOR_TAGS)
        for level in list(Path(str(source['path'])).parents)[:3]:
            parsed = filename_identity(level.name + '.x')
            seen.add(text(parsed['author'] if parsed.get('author') else level.name))
    return {unicodedata.normalize('NFC', s).casefold() for s in seen if s}


def confirmed_spellings(database):
    """Library-wide author spellings confirmed by fetched, verified catalog or publisher evidence
    (read-only): {spelling: {'urls': [...], 'seen': [local spellings in the confirming records]}}.
    Any read problem yields {} (current behaviour: the most common local spelling)."""
    import contextlib
    import json
    import sqlite3
    try:
        with contextlib.closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
            db.execute('PRAGMA query_only=ON')
            tables = sorted(name for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if name in CONFIRMED_QUERIES)
            key = (str(Path(database).resolve()),) + tuple(tuple(db.execute(CONFIRMED_KEYS[name]).fetchone()) for name in tables)
            if key in _CONFIRMED:
                return _CONFIRMED[key]
            found = {}
            for name in tables:
                for value, url, record in db.execute(CONFIRMED_QUERIES[name]):
                    url = str(url or '')
                    if not url.startswith('https://'):
                        continue
                    try:
                        values = json.loads(value) if isinstance(value, str) and value.startswith('[') else [value]
                    except ValueError:
                        values = [value]
                    for item in values if isinstance(values, list) else [values]:
                        spelling = unicodedata.normalize('NFC', text(item))
                        if _person_like(spelling) and not PEOPLE_SEPARATOR.search(spelling):
                            entry = found.setdefault(spelling, {'urls': set(), 'seen': set()})
                            entry['urls'].add(url)
                            entry['seen'] |= _record_spellings(record)
    except (sqlite3.Error, OSError, ValueError):
        return {}
    result = {spelling: {'urls': sorted(e['urls'])[:5], 'seen': sorted(e['seen'])} for spelling, e in found.items()}
    _CONFIRMED.clear()
    _CONFIRMED[key] = result
    return result


def catalog_readers(database, root):
    return catalog_index(database, root)['readers']


def surname_first(name):
    """Surname first (ruling 3), only when a known first name shows where the surname is."""
    name = unicodedata.normalize('NFC', re.sub(r'\s*[\[(\{][^\])\}]{0,120}[\])\}]?', ' ', str(name or '')))
    tokens = [t.strip('_*~') for t in text(name).split() if t.strip('_*~')]
    if len(tokens) < 2 or PEOPLE_SEPARATOR.search(name):
        return ' '.join(tokens) or text(name), 'kept as written (one word or several people)'
    first, last = norm(tokens[0]), norm(tokens[-1])
    if (first in GIVEN_NAMES or INITIALS.match(tokens[0])) and last not in GIVEN_NAMES:
        # The surname is the last word, with a lowercase particle before it ("де Клемешье").
        cut = len(tokens) - 1
        while cut > 1 and tokens[cut - 1].casefold() in NAME_PARTICLES:
            cut -= 1
        return ' '.join(tokens[cut:] + tokens[:cut]), 'surname first ("%s" is a first name or initial)' % tokens[0]
    if first not in GIVEN_NAMES and (last in GIVEN_NAMES or PATRONYMIC.fullmatch(last) or len(tokens) > 2 and norm(tokens[1]) in GIVEN_NAMES):
        return ' '.join(tokens), 'already surname first'
    return ' '.join(tokens), 'kept as written (surname position not known locally)'


def canonical_author(agreed, forms, index, language=''):
    """One spelling per person (Sergei 2026-10-13, ruling 3): Russian name for a Russian original,
    English otherwise; within that the most common local spelling (book folders), ties broken
    alphabetically; then surname first. Returns (name, record of the choice).

    v0.15.0: within the chosen script, a spelling that fetched catalog or publisher evidence
    confirms anywhere in the library (index['confirmed'], confirmed_spellings) wins over the
    local majority, so a majority typo ("Pratchet") gives way to the confirmed spelling and
    every book of the author gets one folder. Without a confirmation nothing changes. A middle
    initial may stand for the middle name when first name and surname are written in full on
    both sides (middle_initial_same: "Dick Philip K." / "Дик Филип Киндред")."""
    candidates = set()
    if index:
        for k in _spelling_keys(agreed):
            candidates.update(index['keys'].get(k, ()))
    library = sorted(candidates)

    def same(value):
        # Only the same person: never a surname alone, and never an initial read as a full
        # first name (the library may hold two different people behind "Толстой А.").
        match = compare_names(value, agreed)
        if match and not match['subset'] and not match['expanded']:
            return True
        return middle_initial_same(value, agreed, library)
    counts = Counter()
    if index:
        # Library-wide counts only, so every book of one author sees the same counts and the
        # same choice; this book's own folder is already among them.
        for spelling in library:
            if same(spelling):
                counts[spelling] += index['spellings'].get(spelling, 0)
    for form in forms:
        form = unicodedata.normalize('NFC', text(form))
        if form and same(form) and form not in counts:
            counts[form] = 1
    if not counts:
        counts[text(agreed)] = 1
    latin = {k: v for k, v in counts.items() if script(k) == 'latin'}
    cyrillic = {k: v for k, v in counts.items() if script(k) != 'latin'}
    if language == 'ru':
        pool, why = cyrillic or counts, 'Russian original: Russian name' + ('' if cyrillic else ' not found locally')
    elif language:
        pool, why = latin or counts, 'original not Russian: English name' + ('' if latin else ' not found locally')
    elif latin:
        pool, why = latin, 'original language unknown; an English spelling exists locally, so the English name is used'
    else:
        pool, why = counts, 'original language unknown; only Russian spellings exist locally'
    # The script is chosen from local spellings only (ruling 3); a confirmed spelling of the same
    # person in that script then wins (same name rules, or a one-letter slip of a local spelling).
    scripts = {script(k) for k in pool}
    confirmed = {}
    for spelling, entry in sorted(((index or {}).get('confirmed') or {}).items()):
        # A one-letter slip is adopted only when the confirming record itself saw that local
        # spelling (Senua M5): "Terry Pratchet" files confirmed as "Terry Pratchett".
        seen = set(entry.get('seen', ()))
        slip = any(slip_same(spelling, local) and unicodedata.normalize('NFC', text(local)).casefold() in seen for local in [agreed] + sorted(pool))
        if script(spelling) in scripts and (same(spelling) or slip):
            confirmed[spelling] = entry['urls']
    if confirmed:
        pool = {spelling: counts.get(spelling) or (index or {}).get('spellings', {}).get(spelling, 0) for spelling in confirmed}
        why += '; spelling confirmed by fetched catalog evidence (library-wide confirmed-spelling list)'
    # Case variants ("РОБЕРТ ХАЙНЛАЙН" folder, "Роберт Хайнлайн" tag) are one spelling; show the
    # most common form that is not written in capitals.
    groups = {}
    for spelling, count in pool.items():
        groups.setdefault(spelling.casefold(), []).append((spelling, count))
    def display(variants):
        written = sorted(variants, key=lambda item: (item[0].isupper(), -item[1], item[0]))[0][0]
        return written.title() if written.isupper() else written
    ranked = sorted(((display(v), sum(c for _, c in v)) for v in groups.values()), key=lambda item: (-item[1], item[0]))
    chosen, order = surname_first(ranked[0][0])
    record = {'chosen': chosen, 'spelling': ranked[0][0], 'why': why, 'order': order,
              'counts': [[k, v] for k, v in sorted(counts.items(), key=lambda item: (-item[1], item[0]))][:8]}
    if confirmed:
        record['confirmed_by'] = next((urls for spelling, urls in confirmed.items() if spelling.casefold() == ranked[0][0].casefold()), [])
    return chosen, record


def folder_siblings(database, row, root):
    """Other catalogued audio files beside this candidate (read-only, exact, no row cap).

    Direct children of the candidate's folder(s); for a disc or part folder ("CD1",
    "Книга (часть 1)") also the files in the other disc/part folders of the same book.
    Fails closed (one unreadable marker) when the folder set is too large to check.
    """
    import contextlib
    import json
    import sqlite3
    members = row.get('members', [])
    own = {m['path'] for m in members}
    folders = sorted({str(Path(m['path']).parent) for m in members})
    if not root or len(folders) > 20:
        return [dict(UNREADABLE)]
    parents = set()
    for folder in folders:
        name = Path(folder).name.strip()
        if DISC.fullmatch(name) or PART_FOLDER.search(name):
            parents.add(str(Path(folder).parent))
    found = []
    with contextlib.closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
        db.execute('PRAGMA query_only=ON')

        def under(folder):
            prefix = folder.rstrip('\\/') + '\\'
            upper = prefix[:-1] + chr(ord(prefix[-1]) + 1)
            return [path for (path,) in db.execute('SELECT path FROM files WHERE root=? AND path>=? AND path<?', (root, prefix, upper))]

        wanted = []
        for folder in folders:
            wanted += [p for p in under(folder) if str(Path(p).parent) == folder]
        if not own <= set(wanted):
            # The range query must find the candidate's own files; otherwise the root or path
            # strings do not match the catalog and nothing beside the book can be ruled out.
            return [dict(UNREADABLE)]
        for parent in parents:
            base = title_key(PART_FOLDER.sub('', Path(folders[0]).name), True)
            for path in under(parent):
                holder = Path(path).parent
                if str(holder.parent) != parent or str(holder) in folders:
                    continue
                name = holder.name.strip()
                if DISC.fullmatch(name) or (PART_FOLDER.search(name) and title_key(PART_FOLDER.sub('', name), True) == base):
                    wanted.append(path)
        for path in dict.fromkeys(wanted):
            if path in own:
                continue
            record = db.execute('SELECT kind,missing,metadata FROM files WHERE root=? AND path=?', (root, path)).fetchone()
            if not record or record[0] != 'audiobook' or record[1]:
                continue
            try:
                tags = {str(k).casefold(): text(v) for k, v in json.loads(record[2]).get('tags', {}).items()}
            except (ValueError, TypeError, AttributeError):
                tags = {}
            found.append({'path': path, 'filename': Path(path).name, 'tags': tags})
    return found


PART_LEAD = re.compile(r'^\W*(?:книга|кн\.|том|т\.|volume|vol\.?|book|часть|ч\.|part|выпуск)\s*[#№]?\s*\d{1,3}\s*[.:,\-–—)]*\s*', re.I)


def _part_core(value, set_title):
    """A part's own title: its name without the leading number, the set name and a leading
    volume or part marker ("Книга 1. Пятый Доминион. Главы 1-20" -> "Пятый Доминион. Главы 1-20")."""
    from split_books import _arabic
    value = clean_title(_arabic(value))
    for _ in range(3):
        before = value
        value = _index_stripped(value).strip()
        if set_title:
            target = norm(set_title)
            for cut in range(1, len(value) + 1):
                if norm(value[:cut]) == target and (cut == len(value) or not value[cut].isalnum()):
                    value = value[cut:]
                    break
        value = PART_LEAD.sub('', value).strip(' .,:;-–—')
        if value == before:
            break
    value = text(value)
    return value if re.search(r'[^\W\d_]{2}', value) else ''


def _part_book(row, root, siblings, components):
    """Sergei 2026-10-13: an M4B part that carries its own chapters is its own book, never
    joined (example: Clive Barker's Imajica folder of part files).

    Applies to a single M4B candidate whose same-album siblings form, with it, one coherent
    numbered set (same author, reader and recording tags, gap-free numbering, declared totals
    met; split_books.check with parts=True, so own titles and volume numbers are allowed).
    Names follow the evidence rules: the shared album is the series only when a folder or the
    set's shared file name repeats it, the number only when the track tag and the file name
    agree, the title is the part's own title where the title tag and the file name agree.
    Unknowns are omitted. Its own chapters are proven at admission (merge_service); a part
    without them stays held. Returns None when the candidate is not such a part."""
    members = row.get('members', [])
    if len(members) != 1 or not siblings or any(s.get('unreadable') for s in siblings):
        return None
    member = members[0]
    if Path(member['path']).suffix.lower() not in ('.m4b', '.m4a'):
        return None
    from split_books import book_key, book_name, check, _labels, _number
    key = book_key(member)
    if not key or key[0] != 'album':
        return None
    mates = [{'path': s['path'], 'filename': s['filename'], 'metadata': {'tags': s['tags']}} for s in siblings]
    mates = [m for m in mates if book_key(m) == key]
    if not mates:
        return None
    group = sorted([member] + mates, key=lambda m: m['path'])
    verdict = check(group, media=False, durations=False, parts=True)
    if not verdict['ok']:
        return None
    index = group.index(member)
    disc, position = verdict['positions'][index]
    tags = _tags(member)
    set_title = text(tags.get('album'))
    stem = Path(member['filename']).stem
    record = {'parts': len(group), 'position': position, 'set_title': set_title, 'title': None, 'series': None, 'number': None}
    raw_title = text(tags.get('title'))
    own_tag, own_name = _part_core(raw_title, set_title), _part_core(stem, set_title)
    if own_tag and own_name and title_key(own_tag) == title_key(own_name):
        record['title'] = {'state': 'green', 'value': own_tag, 'how': 'own title of one part of a %d-part set: the title tag and the file name agree without the part number, volume marker and set name' % len(group),
                           'sources': [{'kind': 'embedded', 'field': 'title', 'value': raw_title}, {'kind': 'file name', 'value': stem}]}
    track, _ = _number(tags.get('track') or tags.get('tracknumber'))
    _, labels = _labels([Path(m['filename']).stem for m in group])
    named = labels[index][1]
    if disc == 1 and verdict['basis'] == 'embedded track numbers' and track is not None and track == named:
        shared = book_name(group)
        leads = [c for c in components if c['kind'] in ('folder', 'parent folder')] + ([{'kind': 'file names', 'value': shared, 'numbered': False}] if shared else [])
        lead = _supports_title(set_title, leads, '')
        if lead:
            record['series'] = {'state': 'green', 'value': set_title, 'how': 'the album shared by the set, repeated in the %s; each part is its own book (Sergei 2026-10-13)' % lead['kind'],
                                'sources': [{'kind': 'embedded', 'field': 'album', 'value': set_title}, {'kind': lead['kind'], 'value': lead['value']}]}
            record['number'] = {'state': 'green', 'value': str(track), 'how': 'the part number in the track tag and the file name',
                                'sources': [{'kind': 'embedded', 'field': 'track', 'value': text(tags.get('track') or tags.get('tracknumber'))}, {'kind': 'file name', 'value': stem}]}
    return record


def agreement(row, root='', siblings=None, readers=None):
    """Field-by-field local agreement record for one candidate row.

    siblings: other audio files beside the candidate, from folder_siblings(); readers: names
    credited as readers anywhere in the library, from catalog_readers(). None skips that check
    (pure unit use only; research and admission always supply both).
    """
    embedded = _embedded(row)
    components = _path_components(row, root)
    if readers and any(COLLECTION_FOLDER.search(n) for n in _ancestors(row, root)):
        # Ruling 1 names these readers as narrator-compilers: under a collection folder their
        # exact credit, when the library also credits them as readers, is a reader credit. The
        # R3-1 self-reading guard below still holds a folder that names the reader.
        for person in list(embedded['people']):
            if any(same_person(person['value'], n) for n in RULED_NARRATORS) and any(same_person(person['value'], r) for r in readers):
                embedded['people'].remove(person)
                embedded['ignored'].append({'field': person['field'], 'value': person['value'],
                                            'why': 'a reader named in Sergei ruling 1 (2026-10-13) and credited as a reader in this library; the narrator, never the author'})
        embedded['author'] = embedded['people'][0] if len(embedded['people']) == 1 else None
    fields = {}
    conflicts = list(embedded['conflicts'])
    ignored = list(embedded['ignored'])
    title = embedded['title']
    author = embedded['author']
    catalog = readers or ()
    part = _part_book(row, root, siblings, components)
    if part:
        # Its own book (Sergei 2026-10-13): its own title, not the set's album, is the title.
        title = {'kind': 'embedded', 'field': 'title', 'value': part['title']['value']} if part['title'] else None
        if not part['title']:
            conflicts.append({'field': 'title', 'detail': 'one part of a %d-part set "%s" with no title of its own: this may be only part of the book; how to name it needs a rule'
                              % (part['parts'], part['set_title']), 'force': True})
    readers = embedded['readers'] + narrator_names([c['value'] for c in components])
    if len(embedded['people']) > 1:
        # Two different people in author/artist credits (often author and narrator). Resolve
        # only when an author folder names exactly one of them and no file or folder name
        # mentions any other; otherwise it is a real conflict.
        def named(person, kinds):
            return any(compare_names(person['value'], piece) for c in components if c['kind'] in kinds for piece in _person_pieces(c))
        folders = [p for p in embedded['people'] if named(p, ('folder', 'parent folder'))]
        everywhere = [p for p in embedded['people'] if named(p, ('file name', 'file names', 'folder', 'parent folder'))]
        if len(folders) == 1 and everywhere == folders:
            author = folders[0]
            ignored += [{'field': p['field'], 'value': p['value'], 'why': 'not named in any file or folder name; treated as a recording credit, not the author'}
                        for p in embedded['people'] if p is not author]
        else:
            first, second = embedded['people'][:2]
            conflicts.append({'field': 'author', 'detail': 'embedded %s "%s" and %s "%s" name different people' % (first['field'], first['value'], second['field'], second['value'])})
    if author and any(compare_names(author['value'], r) for r in readers):
        conflicts.append({'field': 'author', 'detail': '"%s" is also credited as the reader' % author['value'], 'force': True})
    elif author and catalog and any(same_person(author['value'], r) for r in catalog):
        conflicts.append({'field': 'author', 'detail': '"%s" is credited as a reader on other books in this library; held for review' % author['value'], 'force': True})
    marked = [n for n in _ancestors(row, root) if COLLECTION_FOLDER.search(n)]
    title_marked = bool(title and COLLECTION_TITLE.search(clean_title(title['value'])))
    if title and (PART_TITLE.search(clean_title(title['value'])) or not re.search(r'[^\W\d_]{2}', clean_title(title['value']))):
        conflicts.append({'field': 'title', 'detail': 'the title names a part, chapter or numbered file; one part is not the whole book', 'force': True})
    elif title and not part and len(row.get('members', [])) == 1 and _chapter_only(row, title['value']):
        # A single file named or tagged only "Глава 5" / "Часть 3" / "05" beside a book title is one
        # chapter of that book, even when no sibling chapter is catalogued.
        conflicts.append({'field': 'title', 'detail': 'this single file is named or tagged as one chapter or part (%s); one chapter is not the whole book'
                          % _chapter_only(row, title['value']), 'force': True})
    elif title and not part:
        numbered_part = _numbered_part(title['value'], components)
        if numbered_part:
            conflicts.append({'field': 'title', 'detail': '%s "%s" numbers this file as one part of "%s"; one part is not the whole book'
                              % (numbered_part['kind'], numbered_part['value'], clean_title(title['value'])), 'force': True})
    if siblings and any(s.get('unreadable') for s in siblings):
        # Fail closed: without the folder contents a part of a larger book cannot be ruled out.
        conflicts.append({'field': 'title', 'detail': 'the other files beside this book could not be checked', 'force': True})
    elif title and siblings and not part:
        # Other audio files beside this candidate with the same title: it may be one part
        # (chapter, disc, volume file) of a larger book, so its own files are not the whole book.
        key = title_key(title['value'])
        base = title_key(title['value'], True)
        # A trailing year (1500-2099) is part of the title ("Метро 2033" beside "Метро 2034",
        # "Иная 2001"), never a part number; a zero-padded "Дорога 0001" stays a part (Senua M6).
        numbered = base != key and not re.search(r'(?<!\d)(?:1[5-9]\d\d|20\d\d)\s*$', clean_title(title['value']))

        def part_of_same(sibling):
            names = [v for v in (sibling['tags'].get('album'), sibling['tags'].get('title'), Path(sibling['filename']).stem) if v]
            return numbered and any(title_key(_index_stripped(v), True) == base for v in names)
        same = [s for s in siblings if key in {title_key(v) for v in (s['tags'].get('album'), s['tags'].get('title')) if v}
                or _supports_title(title['value'], [{'kind': 'sibling', 'value': Path(s['filename']).stem, 'numbered': True}], author['value'] if author else '')
                or part_of_same(s)]
        if same:
            conflicts.append({'field': 'title', 'detail': '%d other file(s) beside it carry this title; this may be only part of the book' % len(same), 'force': True})
    # Author first: a title written together with the author needs the author's words.
    if author:
        support = _supports_author(author['value'], components)
        if support:
            component, result, piece = support
            # Keep the fuller credit as written; the tag wins a tie (natural word order).
            fuller = piece if len(_parts(piece)[0]) > len(_parts(author['value'])[0]) else author['value']
            fields['author'] = {'state': 'yellow' if result['match'] == 'cross' else 'green', 'value': text(fuller),
                                'sources': [author, {'kind': component['kind'], 'value': component['value'], 'matched': piece}],
                                'how': result['how'], 'partial': len(_parts(fuller)[0]) < 2}
    if title:
        support = _title_support(title['value'], components, author['value'] if author else '')
        if support:
            component, how = support
            fields['title'] = {'state': 'green', 'value': clean_title(title['value']),
                               'sources': [title, {'kind': component['kind'], 'value': component['value']}], 'how': how}
    if part and part['title']:
        fields['title'] = part['title']
    # A structured-name contradiction always holds, even when another name supports the field.
    conflicts += [dict(c, force=True) for c in _contradicts(components, title['value'] if title else '', author['value'] if author else '')]
    real_author = 'author' in fields and not any(c['field'] == 'author' and (c.get('force') or c['detail'].startswith('embedded')) for c in conflicts)
    if real_author and marked:
        # Ruling 4 accepts a generic title by an agreeing author, but inside a collection folder the
        # credited person may be the compiler or one contributor: that stays a research case.
        conflicts.append({'field': 'title', 'detail': 'collection folder "%s": unclear whether "%s" is the author or the compiler; needs collection research'
                          % (marked[0], author['value']), 'force': True})
    for name in ('title', 'author'):
        if any(c['field'] == name and (c.get('force') or c['detail'].startswith('embedded')) for c in conflicts):
            fields.pop(name, None)
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
    if part and part['series'] and 'red' not in (fields['series']['state'], fields['number']['state'])             and (fields['series']['state'] != 'green' or fields['number']['state'] != 'green'):
        fields['series'], fields['number'] = part['series'], part['number']
    accepted = fields['title']['state'] in ('green', 'yellow') and fields['author']['state'] in ('green', 'yellow') \
        and not any(fields[n]['state'] == 'red' for n in ('series', 'number'))
    route = None
    # Only credits set aside in this book's own tags as readers count; "reads other books
    # elsewhere" is a research hold, never a reason to file the book as a collection.
    reader_credit = any('reader' in i['why'] for i in embedded['ignored'])
    # Never route while any person credit remains (a real author is never dropped).
    no_person = not embedded['people']
    # R3-1: an author folder that names the reader means the author reads his own book: hold it.
    reader_values = [text(narrator_names([v])[0]) if NARRATOR_MARKER.search(v) and narrator_names([v]) else text(v)
                     for v in embedded['readers'] + [i['value'] for i in embedded['ignored'] if 'reader' in i['why']]]
    reader_folder = any(compare_names(r, piece) for r in reader_values if r for c in components
                        if c['kind'] in ('folder', 'parent folder') for piece in _person_pieces(c))
    # Every collection filing needs a collection folder; a reader-named folder never routes.
    if no_person and marked and not reader_folder and not accepted and fields['title']['state'] == 'green' and not any(c['field'] == 'title' for c in conflicts) \
            and fields['author']['state'] != 'green' and fields['author']['state'] != 'yellow' \
            and (embedded['collection_credits'] or reader_credit) and not any(fields[n]['state'] == 'red' for n in ('series', 'number')):
        # Ruling 1: a collection compiled or read by a narrator goes to the collections root when
        # two independent local signals say it is a collection; anything less stays research.
        signals = (['collection folder "%s"' % marked[0]] if marked else []) + (['collection title'] if title_marked else []) + \
            (['collection credit "%s"' % embedded['collection_credits'][0]] if embedded['collection_credits'] else []) + \
            (['the credited person is the reader'] if reader_credit else [])
        if len(signals) >= 2:
            names = []
            for value in embedded['readers'] + [i['value'] for i in embedded['ignored'] if 'reader' in i['why']]:
                name = text(narrator_names([value])[0]) if NARRATOR_MARKER.search(value) and narrator_names([value]) else text(value)
                if name and not any(same_person(name, n) for n in names) and norm(name) not in NOT_PEOPLE:
                    names.append(name)
            credit = next((c for c in embedded['collection_credits'] if norm(c) in VARIOUS_AUTHORS), '')
            route = {'kind': 'narrator_collection', 'signals': signals, 'narrators': names[:4], 'credit': COLLECTION_LABEL,
                     'credit_basis': 'tag "%s"' % credit if credit else 'collection label (no author credit locally)'}
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
    part_book = {'parts': part['parts'], 'position': part['position'], 'set_title': part['set_title'], 'requires_own_chapters': True} if part else None
    return {'version': AGREEMENT_VERSION, 'accepted': accepted, 'route': route, 'part_book': part_book, 'fields': fields, 'series': series, 'gaps': gaps,
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
    author = 'collection' if record.get('route') else '|'.join(sorted(words(record['fields']['author']['value'])))
    return 'local:' + hashlib.sha256((title + '\x1f' + author).encode('utf-8')).hexdigest()[:24]


def summary(record):
    """Compact, explainable record stored with the metadata facts."""
    def field(name):
        value = record['fields'][name]
        return {'state': value['state'], 'value': value['value'], 'how': value['how'],
                'sources': [{k: s[k] for k in ('kind', 'field', 'value') if k in s} for s in value['sources'] if s][:4]}
    return {'version': AGREEMENT_VERSION, 'title': field('title'), 'author': field('author'),
            'series': field('series'), 'number': field('number'), 'gaps': list(record['gaps']),
            'ignored': [dict(i) for i in record['ignored']][:6], 'route': dict(record['route']) if record.get('route') else None,
            'part_book': dict(record['part_book']) if record.get('part_book') else None}


def revalidate(row, root, recorded, siblings=None, readers=None):
    """Re-derive agreement from the current row; refuse any drift."""
    current = agreement(row, root, siblings, readers)
    if recorded.get('route'):
        if not current.get('route') or current['route']['kind'] != recorded['route']['kind'] or current['route']['narrators'] != recorded['route']['narrators'] \
                or current['fields']['title']['value'] != recorded['title']['value']:
            raise ValueError('Local collection evidence changed')
        return current
    if (current.get('part_book') or None) != (recorded.get('part_book') or None):
        raise ValueError('Local identity evidence changed')
    if not current['accepted']:
        raise ValueError('Local identity evidence no longer agrees')
    for name in ('title', 'author', 'series', 'number'):
        if current['fields'][name]['state'] != recorded[name]['state'] or current['fields'][name]['value'] != recorded[name]['value']:
            raise ValueError('Local identity evidence changed')
    return current
