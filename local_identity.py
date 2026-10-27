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
джастин джефф лорел лорелл laurell laurel йеспер
роджер ширли shirley говард гарольд дональд кеннет кевин брайан рональд джейсон джеффри райан джейкоб гэри николас эрик джонатан ларри
скотт бенджамин грегори сэмюэл сэмюель рэймонд реймонд патрик деннис джерри тайлер аарон натан уолтер джереми лоуренс шон кристиан альберт
итан джесси брюс ральф юджин уэйн луис алан алистер винсент орсон теодор эрнест курт хью кларк брэм чак дейв дэйв джек джим стив тед вернор
харлан клиффорд найджел гилберт эдгар оскар редьярд маркус нейл нэйл дэниэл айра агата маргарет патриция сьюзен сьюзан кэрол
донна мишель джессика эмили оливия шарлотта джоанн дафна лоис кэролайн стефани ребекка кейт хелен луиза элис мэдлин сильвия
iain ted bram chuck dave jim steve orson theodore ernest kurt hugh clark harlan clifford nigel gilbert edgar oscar rudyard marcus
agatha olivia charlotte daphne lois caroline kate louise madeline sylvia
'''.split())
# Ruling 33 (Sergei 2026-10-26, m-13): Russian and other Slavic first names as written in Latin letters ("Ilya_Marchenko").
# They show where the surname is (surname first), and that the writing language needs an answer before a Latin folder.
# Words that are also common title words in Latin letters (Roman, Vera, Lyubov, Nadezhda, Lev) are left out.
SLAVIC_LATIN_GIVEN = frozenset('''
ilya ilia oleg pavel igor sergey sergei dmitry dmitri dmitriy andrey andrei alexey alexei aleksey aleksei nikolai nikolay vladimir mikhail
yuri yuriy yury ivan maxim maksim evgeny evgeniy yevgeny viktor vitaly vitaliy vadim vasily vasiliy kirill konstantin leonid nikita ruslan
stanislav timur fedor fyodor yaroslav anatoly anatoliy arkady arkadiy gennady gennadiy grigory grigoriy valery valeriy vyacheslav egor yegor
semyon semen arseny arseniy bogdan taras olga tatyana tatiana natalia natalya svetlana irina elena yelena ekaterina yekaterina anastasia
lyudmila ludmila galina larisa yulia yuliya daria darya ksenia kseniya oksana hanna ganna olena nadia zinaida polina alina alyona alena
'''.split())
GIVEN_NAMES |= SLAVIC_LATIN_GIVEN
# Ruling 29 («Голиаф», Sergei 2026-10-26): first names that are Russian spellings of English and other foreign names
# («Скотт», «Стивен», «Роджер»). An author credited so writes in another language: the book is a translation. The
# Russian names (and those both languages share: Анна, Мария, Марк, Лена, Марта, Влад) never are.
RUSSIAN_GIVEN = frozenset('''
александр алексей анатолий андрей антон аркадий артем артём артур борис вадим валентин валерий василий виктор виталий владимир владислав
всеволод вячеслав геннадий георгий герман глеб григорий даниил денис дмитрий евгений егор иван игорь илья кирилл константин лев леонид максим
марк михаил никита николай олег павел петр пётр роман руслан сергей станислав степан тимур федор фёдор юрий ярослав яков эдуард
александра алена алёна алина алла анастасия анна валентина вера виктория галина дарья евгения екатерина елена ирина кира лариса любовь
людмила марина мария наталья наталия наташа надежда ольга светлана софья татьяна юлия яна уна лена марта влад
'''.split())
FOREIGN_CYRILLIC_GIVEN = frozenset(w for w in GIVEN_NAMES if re.fullmatch(r'[а-яё]+', w) and w not in RUSSIAN_GIVEN)


def foreign_given(name):
    """True when a Cyrillic credit's first name is a Russian spelling of a foreign one ("Скотт Вестерфельд")."""
    return any(w.replace('ё', 'е') in FOREIGN_CYRILLIC_GIVEN or w in FOREIGN_CYRILLIC_GIVEN for w in words(name))
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
    word = unicodedata.normalize('NFC', word)
    # 0.22.2 («Джек из Тени»): a Ж that is no Дж may stand for a Latin Z (the Polish Ż: Желязны = Zelazny).
    zed = re.sub(r'(?<!д)ж', 'з', word) if re.search(r'(?<!д)ж', word) else ''
    word = word.replace('дж', 'ж').replace('тч', 'ч')
    variants = [word] + ([word[1:]] if word.startswith('г') else [])   # Г for a Latin H: Гарри = Harry
    if zed:
        variants.append(zed.replace('дж', 'ж').replace('тч', 'ч'))
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


def numbered_credit(name, names=()):
    """True for a credit that is no person's name but a label with a number: initials and a number ("sk 1408"), or any
    credit carrying the number of the book's own title or file name ("1408"). A person's name holds no number."""
    numbers = re.findall(r'\d+', str(name or ''))
    if not numbers:
        return False
    letters = [w for w in re.findall(r'[^\W\d_]+', str(name)) if w]
    if all(len(w) <= 3 for w in letters):
        return True
    own = {n.lstrip('0') for value in names for n in re.findall(r'\d+', str(value or ''))}
    return any(n.lstrip('0') in own for n in numbers if len(n) >= 2)


def lone_number(row, title, siblings=None):
    """0.22.1, item 10 (b): a single file titled only with a number of three or four digits ("1986", "1408") is a whole
    book, unless files beside it are named with numbers too (real parts); "01" or "05" stays a chapter or part. A sibling's
    title tag alone does not count: «1408» sits beside "Stephen King - A Face in the Crowd.m4b" whose title tag is "1"."""
    return bool(title and len(row.get('members', [])) == 1 and re.fullmatch(r'\W*[1-9]\d{2,3}\W*', clean_title(title))
                and not any(re.fullmatch(r'\W*\d{1,4}\W*', clean_title(_index_stripped(v)) or v) for s in (siblings or [])
                            for v in (filename_identity(s['filename']).get('title') or Path(s['filename']).stem,) if v))


# «11.22.63» (Sergei 2026-10-26): a title made of three or more numbers joined by dots, slashes or dashes ("11/22/63",
# "11.22.63") is a name (a date), never a bare part number.
DATE_TITLE = re.compile(r'^\W*\d{1,4}(?:\s*[./\-]\s*\d{1,4}){2,3}\W*$')


def _claims_person(value):
    """A structured name's author slot makes a person claim only when it looks like a name."""
    return bool(value) and not re.search(r'\d', value) and 1 <= len(words(value)) <= 4 and not NARRATOR_MARKER.search(value)


def filename_matches_local_work(filename, titles, authors, embedded_authors=()):
    """Re-use local agreement's title semantics without inventing an author.

    A complete filename can repeat an author-prefixed album or a numbered cycle
    label. Its parsed title alone loses that context. Real person claims still
    must match the accepted author; numeric cycle labels need a matching actual
    embedded author instead. No metadata, order or source-membership gate is
    replaced by this check.
    """
    component={'kind':'file name','value':Path(filename).stem,'numbered':False}
    parsed=filename_identity(filename)
    if not any(_title_support(title,[component],'') for title in titles):
        return False
    claimed=parsed.get('author','')
    if not claimed:
        return True
    if _claims_person(claimed):
        return any(compare_names(claimed,author) for author in authors)
    # Position suffixes are source labels, never people. Do not extend this to
    # arbitrary non-person credits, narrator markers, or missing author evidence.
    positioned=bool(re.fullmatch(r'.*[^\W\d_].*\s+\d{1,4}(?:\.\d{1,3})?',claimed))
    return bool(positioned and not NARRATOR_MARKER.search(claimed) and
                any(compare_names(value,author) for value in embedded_authors for author in authors))


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
        tagged = set()
        albums = {}
        root_key = norm(str(Path(root)))
        for path, metadata in db.execute("SELECT path,metadata FROM files WHERE root=? AND kind='audiobook'", (root,)):
            try:
                tags = {str(k).casefold(): str(v) for k, v in json.loads(metadata).get('tags', {}).items()}
            except (ValueError, TypeError, AttributeError):
                continue
            readers.update(text(tags[k]) for k in NARRATOR_TAGS if text(tags.get(k)))
            readers.update(text(n) for n in narrator_names([tags.get(k, '') for k in FREE_TEXT_TAGS]))
            folder = str(Path(path).parent)
            if text(tags.get('album')):
                albums.setdefault(folder, Counter())[text(tags.get('album'))] += 1
            credits = [text(tags.get(k)) for k in AUTHOR_TAGS]
            tagged.update(unicodedata.normalize('NFC', c) for c in credits if _person_like(c))
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
    # v5: names the library credits in author/artist TAGS (not folder names), read by looks_like_person().
    tag_keys = {}
    for spelling in tagged:
        for k in _spelling_keys(spelling):
            tag_keys.setdefault(k, []).append(spelling)
    # Ruling 45: the book folders beside each other under one parent folder, each with the album most of its files carry.
    sibling_albums = {}
    for folder, counts in albums.items():
        sibling_albums.setdefault(str(Path(folder).parent), {})[folder] = counts.most_common(1)[0][0]
    index = {'readers': readers, 'spellings': dict(spellings), 'keys': keys, 'tag_keys': tag_keys, 'sibling_albums': sibling_albums}
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
    # 0.22.1 (Sergei 2026-10-25, "Laurell K. Hamilton"): a middle initial between two words shows the first name comes first.
    middle = len(tokens) == 3 and INITIALS.match(tokens[1]) and not INITIALS.match(tokens[0]) and not INITIALS.match(tokens[2])
    if (first in GIVEN_NAMES or INITIALS.match(tokens[0]) or middle) and last not in GIVEN_NAMES:
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
    # Futaba's 0.22.1 QA, M-2: a name with underscores is a file or folder name ("Richard_Ford_Labirint"), never a
    # person's spelling. It won the vote as the "local English spelling" of «Ричард Форд», so whatever author Sergei
    # confirmed, the book went to "Sorted\Richard_Ford_Labirint\". The same mark asks the question (odd_identity).
    library = sorted(spelling for spelling in candidates if '_' not in spelling)
    forms = [form for form in forms if '_' not in text(form)]

    def same(value):
        # Only the same person: never a surname alone, and never an initial read as a full
        # first name (the library may hold two different people behind "Толстой А.").
        match = compare_names(value, agreed)
        if match and not match['subset'] and not match['expanded']:
            return True
        # v0.22.0: a middle name written out on one side only ("Michael John Moorcock" / "Майкл Муркок"): the first name
        # and the surname are both written in full on both sides, so it is the same person.
        if match and match['subset'] and not match['expanded'] and min(len(_parts(value)[0]), len(_parts(agreed)[0])) >= 2 \
                and abs(len(_parts(value)[0]) - len(_parts(agreed)[0])) == 1:
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


def _part_book(row, root, siblings, components, numbered_names=False):
    """Sergei 2026-10-13: an M4B part that carries its own chapters is its own book, never
    joined (example: Clive Barker's Imajica folder of part files).

    Applies to a single .m4b candidate whose same-album siblings form, with it, one coherent
    numbered set (same author, reader and recording tags, gap-free numbering, declared totals
    met; split_books.check with parts=True, so own titles and volume numbers are allowed).
    Every part keeps its parent work (Senua R2-C1): the series is the set's album whenever a
    folder or the set's shared file name repeats it, the number is the part's proven track
    number, the title is the part's own title where the title tag and the file name agree.
    A set is filed part by part only when EVERY part qualifies; otherwise the whole set is
    held (never published piecemeal). Every part's own chapters are proven at admission
    (merge_service); without them the set stays held. Returns None when the candidate is
    not such a part."""
    members = row.get('members', [])
    if len(members) != 1 or not siblings or any(s.get('unreadable') for s in siblings):
        return None
    member = members[0]
    # .m4b only: copy mode keeps a part's chapters; an .m4a would be re-encoded (Senua R2-M1).
    if Path(member['path']).suffix.lower() != '.m4b':
        return None
    from split_books import book_key, book_name, check, _number
    key = book_key(member)
    if not key or key[0] != 'album':
        return None
    mates = [{'path': s['path'], 'filename': s['filename'], 'metadata': {'tags': s['tags']}} for s in siblings]
    mates = [m for m in mates if book_key(m) == key]
    if not mates:
        return None
    group = sorted([member] + mates, key=lambda m: m['path'])
    # v5 (numbered_names): each part is filed as its own book, so parts read by different people
    # (the volumes of a series) still form one numbered set.
    verdict = check(group, media=False, durations=False, parts=True, readers=not numbered_names)
    if not verdict['ok']:
        return None
    index = group.index(member)
    tags = _tags(member)
    set_title = text(tags.get('album'))
    shared = book_name(group)
    leads = [c for c in components if c['kind'] in ('folder', 'parent folder')] + ([{'kind': 'file names', 'value': shared, 'numbered': False}] if shared else [])
    lead = _supports_title(set_title, leads, '')
    record = {'parts': len(group), 'position': verdict['positions'][index][1], 'set_title': set_title,
              'members': [m['path'] for m in group], 'title': None, 'series': None, 'number': None, 'blocked': ''}
    titles = []
    for m in group:
        m_tags = _tags(m)
        raw_title, stem = text(m_tags.get('title')), Path(m['filename']).stem
        own_tag, own_name = _part_core(raw_title, set_title), _part_core(stem, set_title)
        titles.append((own_tag if own_tag and own_name and title_key(own_tag) == title_key(own_name) else '', raw_title, stem))
    numbered = set()
    if numbered_names:
        # Ruling 13 (Sergei 2026-10-24): a part with no title of its own is named after the set plus
        # its number ("Торадора! 5"); the set is no longer held for it (ruling 15: automatic).
        for i, (own, raw_title, stem) in enumerate(titles):
            if not own and clean_title(set_title):
                titles[i] = ('%s %d' % (clean_title(set_title), verdict['positions'][i][1]), raw_title, stem)
                numbered.add(i)
    lacking = [verdict['positions'][i][1] for i, (own, _, _) in enumerate(titles) if not own]
    if not titles[index][0]:
        record['blocked'] = 'one part of a %d-part set "%s" with no title of its own: this may be only part of the book; how to name it needs a rule' % (len(group), set_title)
    elif lacking:
        record['blocked'] = 'part %d of the %d-part set "%s" has no title of its own: this may be only part of the book, so the whole set is held (never filed piecemeal)' % (lacking[0], len(group), set_title)
    elif not lead and not numbered_names:
        # v5: one source is enough; the album tag itself names the parent work ("Сага об Элрике"
        # in an "Elric of Melniboné" folder).
        record['blocked'] = 'no folder or file name repeats the set "%s": its parts would lose their parent work, so the whole set is held' % set_title
    elif verdict['basis'] not in (('embedded track numbers', 'part numbers in the file names') if numbered_names else ('embedded track numbers',)) \
            or any(disc != 1 for disc, _ in verdict['positions']):
        # v5 (ruling 15): gap-free part numbers in the file names number a set as well as track tags.
        record['blocked'] = 'the parts of "%s" are not numbered by track tags on one disc, so the whole set is held' % set_title
    if record['blocked']:
        return record
    own, raw_title, stem = titles[index]
    record['title'] = {'state': 'green', 'value': own, 'how': 'own title of one part of a %d-part set: the title tag and the file name agree without the part number, volume marker and set name' % len(group),
                       'sources': [{'kind': 'embedded', 'field': 'title', 'value': raw_title}, {'kind': 'file name', 'value': stem}]}
    if index in numbered:
        record['title'] = {'state': 'one', 'value': own, 'basis': 'number_rule', 'how': 'Set name + part number (Sergei 2026-10-24, ruling 13): part %d of the %d-part set "%s" has no title of its own'
                           % (verdict['positions'][index][1], len(group), set_title),
                           'sources': [{'kind': 'embedded', 'field': 'album', 'value': set_title}, {'kind': 'set numbering', 'value': str(verdict['positions'][index][1])}]}
    elif numbered_names:
        record['title']['basis'] = 'tag'
    record['series'] = {'state': 'green', 'value': set_title, 'how': 'the album shared by the set, repeated in the %s; each part is its own book of that parent work (Sergei 2026-10-13)' % lead['kind'],
                        'sources': [{'kind': 'embedded', 'field': 'album', 'value': set_title}, {'kind': lead['kind'], 'value': lead['value']}]} if lead else \
        {'state': 'green', 'value': set_title, 'how': 'the album shared by the %d-part set (one source is enough, Sergei 2026-10-24); each part is its own book of that parent work' % len(group),
         'sources': [{'kind': 'embedded', 'field': 'album', 'value': set_title}, {'kind': 'set numbering', 'value': '1-%d' % len(group)}]}
    track, _ = _number(tags.get('track') or tags.get('tracknumber'))
    if numbered_names:
        track = verdict['positions'][index][1]
    record['number'] = {'state': 'green', 'value': str(track), 'how': 'the part\'s track number, gap-free across the %d-part set' % len(group),
                        'sources': [{'kind': 'embedded', 'field': 'track', 'value': text(tags.get('track') or tags.get('tracknumber'))}, {'kind': 'set numbering', 'value': '1-%d' % len(group)}]}
    if index in numbered:
        # The name already carries the set and the number ("Торадора! 5"): no series folder or prefix on top.
        record['series'] = record['number'] = None
    return record


def _piece_conflicts(row, title, part, siblings, components, author='', numbered=False):
    """Signs that this candidate is one piece of a bigger book (a chapter, a numbered part, a file
    beside others with the same title). Shared by agreement() and identify(); every entry is forced.
    numbered: the title is a ruling-13 "set name + number" name, so its trailing number is expected."""
    conflicts = []
    # 0.22.1, item 10 (b): a single file titled only with a number of three or four digits ("1986", "1408") is a whole book,
    # unless files beside it are numbered too; "01" or "05" stays a chapter or part.
    lone = lone_number(row, title, siblings)
    dated = bool(title and DATE_TITLE.fullmatch(clean_title(title)))
    if title and not numbered and not lone and (PART_TITLE.search(clean_title(title)) or not dated and not re.search(r'[^\W\d_]{2}', clean_title(title))):
        conflicts.append({'field': 'title', 'detail': 'the title names a part, chapter or numbered file; one part is not the whole book', 'force': True, 'piece': 'part_title'})
    elif title and not part and len(row.get('members', [])) == 1 and _chapter_only(row, title):
        # A single file named or tagged only "Глава 5" / "Часть 3" / "05" beside a book title is one
        # chapter of that book, even when no sibling chapter is catalogued.
        conflicts.append({'field': 'title', 'detail': 'this single file is named or tagged as one chapter or part (%s); one chapter is not the whole book'
                          % _chapter_only(row, title), 'force': True, 'piece': 'chapter'})
    elif title and not part:
        numbered_part = _numbered_part(title, components)
        if numbered_part:
            conflicts.append({'field': 'title', 'detail': '%s "%s" numbers this file as one part of "%s"; one part is not the whole book'
                              % (numbered_part['kind'], numbered_part['value'], clean_title(title)), 'force': True, 'piece': 'numbered_part', 'component': numbered_part})
    if siblings and any(s.get('unreadable') for s in siblings):
        # Fail closed: without the folder contents a part of a larger book cannot be ruled out.
        conflicts.append({'field': 'title', 'detail': 'the other files beside this book could not be checked', 'force': True, 'piece': 'unreadable'})
    elif title and siblings and not part:
        # Other audio files beside this candidate with the same title: it may be one part
        # (chapter, disc, volume file) of a larger book, so its own files are not the whole book.
        key = title_key(title)
        base = title_key(title, True)
        # A trailing year (1500-2099) is part of the title ("Метро 2033" beside "Метро 2034",
        # "Иная 2001"), never a part number; a zero-padded "Дорога 0001" stays a part (Senua M6).
        numbered = base != key and not re.search(r'(?<!\d)(?:1[5-9]\d\d|20\d\d)\s*$', clean_title(title))

        def part_of_same(sibling):
            names = [v for v in (sibling['tags'].get('album'), sibling['tags'].get('title'), Path(sibling['filename']).stem) if v]
            return numbered and any(title_key(_index_stripped(v), True) == base for v in names)
        same = [s for s in siblings if key in {title_key(v) for v in (s['tags'].get('album'), s['tags'].get('title')) if v}
                or _supports_title(title, [{'kind': 'sibling', 'value': Path(s['filename']).stem, 'numbered': True}], author)
                or part_of_same(s)]
        if same:
            conflicts.append({'field': 'title', 'detail': '%d other file(s) beside it carry this title; this may be only part of the book' % len(same), 'force': True, 'piece': 'siblings', 'count': len(same)})
    return conflicts


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
        if part['blocked']:
            conflicts.append({'field': 'title', 'detail': part['blocked'], 'force': True})
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
    conflicts += _piece_conflicts(row, title['value'] if title else '', part, siblings, components, author['value'] if author else '')
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
    # Every part of the set must carry its own chapters at admission (merge_service).
    part_book = {'parts': part['parts'], 'position': part['position'], 'set_title': part['set_title'], 'members': list(part['members']),
                 'requires_own_chapters': True} if part else None
    return {'version': AGREEMENT_VERSION, 'accepted': accepted, 'route': route, 'part_book': part_book, 'fields': fields, 'series': series, 'gaps': gaps,
            'ignored': ignored, 'conflicts': conflicts,
            'path': [{'kind': c['kind'], 'value': c['value']} for c in components]}


# ---------------------------------------------------------------- v5: title + author is enough
# Sergei 2026-10-24 (rulings 6, 6a, 13, 14, 15): a title and an author, each from ONE local source,
# identify a book. Title: the album or title tag, else the file name, else the folder name. Author:
# the author / album artist / artist tag, else "Author - Title" in the file or folder name, else a
# folder named after a person. Nothing from the Internet decides identity. Four guards stay:
#   1. a reader is never an author (tags, "читает", names in brackets, readers of other books,
#      Sergei's not-author rules), in tags AND in file or folder names;
#   2. parts stay together (grouping, groups.py); a chapter or part on its own is not a book;
#   3. a collection word or an editor credit is not an author: Сборники / "Разные авторы";
#   4. garbled tag text is not used.
# What the files cannot settle goes to Sergei as a question (an 'ask'), never to the Internet.
IDENTITY_VERSION = 'local-one-v5'
KNOWN_AGREEMENT_VERSIONS = KNOWN_AGREEMENT_VERSIONS + (IDENTITY_VERSION,)
EDITOR_MARKER = re.compile(r'(?<![^\W\d_])(?:под\s+ред\w*|ред\.|сост\.|составител\w*|составил\w*|edited\s+by|editors?|eds?\.)(?![^\W\d_])', re.I)
BRACKETS = re.compile(r'[(\[]([^()\[\]]{3,80})[)\]]')
ASK_REASONS = {'title_author': 'Title or author missing', 'author_unclear': 'Author unclear', 'same_author': 'Same author?'}
# Tag "titles" that name the format or nothing at all ("Мр3-Книга" on Марк Твен's book).
# The one shared list of generic titles: grouping (groups.py) and naming both read it. Senua's 0.22.0 review, N4 added the
# "unknown" and "new recording" families; groups._same_title_sets also checks the file names for a title no list knows.
JUNK_TITLES = {'мр3книга', 'mp3книга', 'мп3книга', 'аудиокнига', 'аудиокниги', 'audiobook', 'audiobooks', 'audio', 'книга', 'book',
               'unknown', 'untitled', 'безназвания', 'безимени', 'noname', 'unknowntitle', 'track', 'трек', 'новаякнига',
               'неизвестно', 'неизвестный', 'неизвестная', 'неизвестное', 'неизвестен', 'неизвестна', 'названиенеизвестно',
               'нетназвания', 'беззаголовка', 'новаязапись', 'запись', 'аудиозапись', 'голосоваязапись', 'аудио', 'аудиотрек',
               'notitle', 'title', 'unknownalbum', 'unknowntrack', 'newrecording', 'recording', 'voicerecording', 'audiotrack'}
PIECE_REASON = 'One part of a bigger book'


def garbled(value):
    """Mojibake that cannot be used as a name or title: replacement characters, cp1251 text read as
    Latin-1 ("Òåððè Ïðàò÷åòò") or UTF-8 read as cp1251 ("РўРµСЂСЂРё")."""
    value = str(value or '')
    if '�' in value:
        return True
    letters = [c for c in value if c.isalpha()]
    if len(letters) >= 3 and script(value) != 'cyrillic':
        if 2 * sum(1 for c in letters if 'À' <= c <= 'ÿ') >= len(letters):
            return True
    return bool(re.search('(?:[РС][Ѐ-Џѐ-џҐґ -¿‐-›№™]){2,}', value))


def bracketed_people(values):
    """Person names written in ( ) or [ ] in file or folder names: in this library a reader or an
    uploader ("(Дружинин Степан)", "[Пухов Сергей]", "(чит. Капитан Абр и Nelly)"), never the author."""
    found = []
    for value in values:
        for inner in BRACKETS.findall(unicodedata.normalize('NFC', str(value or ''))):
            inner = NARRATOR_MARKER.sub(' ', inner)
            for piece in re.split(r'\s*(?:,|;|&|/|\s+и\s+|\s+and\s+)\s*', inner):
                piece = text(piece.strip(' .:-–—'))
                if 2 <= len(words(piece)) <= 3 and not re.search(r'\d', piece) and norm(piece) not in NOT_PEOPLE \
                        and norm(piece) not in CONTAINER_NAMES and not COLLECTION_FOLDER.search(piece) and not PART_FOLDER.search(piece):
                    found.append(piece)
    return found


COMPILER = re.compile(r'(?<![^\W\d_])(?:в\s+обработке|в\s+пересказе|пересказ(?:ал[аи]?)?|обработк[аи]|сост(?:\.|авитель|авительница|авил[аи]?)|составлени[еяю]|retold\s+by|compiled\s+by|edited\s+by)\s*[:\-–—]?\s*', re.I)


def _compiler_credit(members):
    """The compiler or reteller a folk-tale collection credits in its tags ("в обработке А. Н. Толстого"), else ''."""
    for member in members[:3]:
        tags = _tags(member)
        for name in ('composer', 'comment', 'description', 'synopsis', 'lyrics'):
            value = unicodedata.normalize('NFC', str(tags.get(name) or ''))
            match = COMPILER.search(value)
            if not match:
                continue
            tail = re.split(r'[,;\n(\[|]|\s[-–—]\s|\.\s', value[match.end():], maxsplit=1)[0]
            tokens = []
            for token in tail.split():
                if not re.fullmatch(r"[^\W\d_]+(?:[-'’.][^\W\d_]*)*\.?", token):
                    break
                tokens.append(token)
            tokens = tokens[:4]
            if tokens and len(tokens[-1]) > 2:
                tokens[-1] = tokens[-1].rstrip('.')  # the sentence's full stop, never an initial
            name_value = text(' '.join(tokens))
            if len(words(name_value)) >= 2 and not NARRATOR_MARKER.search(name_value):
                return name_value
    return ''


def _consistent(members, names):
    """The one non-empty value every member that carries the tag agrees on, else '' (and whether
    members disagree)."""
    values = {text(_tags(m).get(n)) for m in members for n in names} - {''}
    return (next(iter(values)), False) if len(values) == 1 else ('', len(values) > 1)


def looks_like_person(value, index=None, surname=False):
    """A name shows it is a person by a known first name, an initial or a patronymic, or because
    the library credits the same person in an author or artist tag elsewhere. Series, universe and
    title words ("Колесо времени", "Malleus Maleficarum", "Часть Вторая") do not. surname: a single
    word is a person too when it is the surname of a name the library credits ("Сапковский" beside
    "Анджей Сапковский"; Senua's 0.22.0 review, G1)."""
    value = clean_title(value)
    tokens = value.split()
    if not tokens or len(tokens) > 5 or re.search(r'\d', value) or norm(value) in NOT_PEOPLE or norm(value) in CONTAINER_NAMES or PART_FOLDER.search(value):
        return False
    if any(norm(t) in GIVEN_NAMES or INITIALS.match(t) or PATRONYMIC.fullmatch(norm(t)) for t in tokens):
        return True
    if index and index.get('tag_keys') and len(words(value)) >= 2:
        return any(same_person(value, spelling) for k in _spelling_keys(value) for spelling in index['tag_keys'].get(k, ()))
    if surname and index and index.get('tag_keys') and len(words(value)) == 1 and len(value) >= 4:
        return any(_shares_surname(value, spelling) for k in _spelling_keys(value) for spelling in index['tag_keys'].get(k, ()))
    return False


def tag_index(tag_sets):
    """The 'tag_keys' part of catalog_index() from tag dicts already in memory (groups.build has the catalog rows):
    every person-like author or artist credit, by blocking key."""
    tagged = set()
    for tags in tag_sets:
        tags = {str(k).casefold(): v for k, v in (tags or {}).items()}
        tagged.update(unicodedata.normalize('NFC', c) for c in (text(tags.get(k)) for k in AUTHOR_TAGS) if _person_like(c))
    keys = {}
    for spelling in tagged:
        for k in _spelling_keys(spelling):
            keys.setdefault(k, []).append(spelling)
    return {'tag_keys': keys}


# Words that label a part or a chapter, never a work of its own ("Глава 3", "Эпизод 2 Глава 01-02", "Предисловие переводчика").
PART_WORDS = frozenset('''глава главы гл часть части ч chapter chap part pt track трек пролог эпилог prologue epilogue эпизод episode
том vol volume книга book диск disc disk cd предисловие послесловие вступление введение intro introduction outro начало конец финал
от автора переводчика переводчик история истории рассказ рассказы и первая вторая третья четвертая пятая шестая седьмая восьмая
девятая десятая первый второй третий i ii iii iv v vi vii viii ix x'''.split())
TRAILING_POSITION = re.compile(r'(?:[\s_.,:;-]*(?:ч|часть|part|pt|глава|chapter|cd|disc|диск|том|vol|книга|book)?\.?\s*\d{1,4}(?:\s*[-/]\s*\d{1,4})?)\s*$', re.I)


def work_name(value):
    """The work a title tag or a file-name title names, its position and part number aside ("1.1 Психическая атака" and
    "Последнее желание 2" -> "Психическая атака", "Последнее желание"); '' for a chapter or part label, a junk title
    ("Аудиокнига", "Без имени") or garbled text. Senua's 0.22.0 review (G1, G3): files naming two works are two books."""
    value = clean_title(value)
    if not value or garbled(value) or norm(value) in JUNK_TITLES:
        return ''
    value = re.sub(r'^\s*\d[\d.\-_ ]*', '', value)
    for _ in range(3):
        value = TRAILING_POSITION.sub('', value).strip(' .,:;-–—_')
    tokens = re.findall(r'[^\W\d_]+', value.casefold().replace('ё', 'е'))
    if not tokens or all(t in PART_WORDS for t in tokens) or norm(value) in JUNK_TITLES:
        return ''
    return text(value)


# Senua's 0.22.0 release review, N10/N11: a title that opens with a chapter or part label names a piece of the book, whatever
# follows the label ("Глава 1. Там где ветер", "Часть 1. Бродяжья зона. Глава 01", "Часть первая. Фрагмент 1", "Пролог. Корона
# Холмов"). Book, volume and episode words ("Книга 2", "Том 3", "Эпизод 4") are no chapter labels: they may name books.
_ORDINAL_WORD = (r'(?:перв|втор|трет|четв[её]рт|пят|шест|седьм|восьм|девят|десят|одиннадцат|двенадцат|тринадцат|четырнадцат|'
                 r'пятнадцат|шестнадцат|семнадцат|восемнадцат|девятнадцат|двадцат)(?:ая|ый|ой|ий|ья|ей|ое|ье)|first|second|third|'
                 r'fourth|fifth|sixth|seventh|eighth|ninth|tenth|one|two|three|four|five|six|seven|eight|nine|ten')
CHAPTER_LABEL = re.compile(r'^\W*(?:(?:глава|гл\.?|chapter|chap\.|ch\.|часть|ч\.|part|pt\.?|фрагмент|fragment)\s*[#№:.\-–—]?\s*'
                           r'(?:\d{1,4}|[ivxlc]{1,7}|' + _ORDINAL_WORD + r')(?![^\W\d_])'
                           r'|(?:пролог|prologue|prolog|эпилог|epilogue|epilog|послесловие|предисловие|afterword|foreword|вступление|'
                           r'введение|интерлюдия|interlude)(?![^\W\d_]))', re.I)


def _own_title_tail(value, own):
    """What follows the book's own title and a number at the start of a title, else None: "Пастушья корона 01. Глава 1.
    Там где ветер" -> "глава 1. там где ветер", "Пастушья корона 02" -> '' (own: "Пастушья корона")."""
    def fold(v):
        return ' '.join(unicodedata.normalize('NFC', str(v or '')).casefold().replace('ё', 'е').split())
    value, own = fold(value), fold(clean_title(own))
    if not own or not value.startswith(own):
        return None
    match = re.match(r'[\s_.,:;\-–—]*(?:№\s*)?\d{1,4}(?:[-.]\d{1,3})?(?!\d)(?![^\W\d_])', value[len(own):])
    return value[len(own) + match.end():].strip(' _.,:;-–—') if match else None


def chapter_works(values, own=''):
    """The work each title of one set names (norm keys, in order; '' for none): work_name(), chapter labels aside. Senua's
    0.22.0 release review, N10/N11: grouping read every chapter name as a work, so «Пастушья корона» (77 files named
    "Пастушья корона 01. Глава 1. Там где ветер", "Пастушья корона 02", ...) stopped joining and 21 albums whose title tags
    are chapter names ("Глава 1. Дом, милый дом - 1", "Часть 1. Бродяжья зона. Глава 01") were held as several books.
    A title names no work of its own when
      - it opens with a chapter or part label (CHAPTER_LABEL), whatever follows; or
      - it is the book's own title (own: the shared title tag, or the album) and a number ("Пастушья корона 00. Словарь
        Нак-мак-фиглов") and the set is visibly chapters: some title is the own title and a number alone ("Пастушья корона
        02") or followed by a chapter label. Without that, "Ведьмак 1. Последнее желание" and "Ведьмак 2. Меч
        предназначения" under one "Ведьмак" tag still name two works."""
    titles = [clean_title(v) for v in values]
    bare = [re.sub(r'^\s*\d[\d.\-_ ]*', '', t) for t in titles]
    tails = [_own_title_tail(b, own) for b in bare]
    chapters = any(t == '' or CHAPTER_LABEL.match(t) for t in tails if t is not None)
    return ['' if CHAPTER_LABEL.match(b) or chapters and tail is not None else norm(work_name(title))
            for title, b, tail in zip(titles, bare, tails)]


def _shares_surname(a, b):
    """The same surname (any script), first names aside: "Дж. Р.Р. Толкин" / "Джон Рональд Руэл Толкин"."""
    left = [w for w in words(a) if len(w) >= 4 and norm(w) not in GIVEN_NAMES]
    right = [w for w in words(b) if len(w) >= 4 and norm(w) not in GIVEN_NAMES]
    return any(_pair(x, y) for x in left for y in right)


def _person_folder(component, index=None):
    """A folder whose whole name is a person (an author folder). Universe, series and container
    folders ("Star Wars", "Dragonlance") are not people."""
    value = clean_title(component['value'])
    if not _person_like(value) or len(words(value)) > 4 or PEOPLE_SEPARATOR.search(value):
        return ''
    return value if looks_like_person(value, index) else ''


def _clean_credit(value, title, who):
    """An author tag as an author credit: a title in quotes or a bracketed note glued to the name is
    removed ("Дэн Абнетт «Первый и Единственный»"), the book's own title glued to it too
    ("Кинг___Легенда_о_пуле"), and so is a reader joined by a dash ("Александр Варго - Пухов Сергей").
    Returns (credit, readers removed)."""
    value = text(value)
    value = text(re.sub(r'[«“"„][^«»“”"„]{2,120}[»”"“]', ' ', value))
    value = text(re.sub(r'\s*[\[(][^\])]{0,80}[\])]', ' ', value))
    spaced = text(value.replace('_', ' '))
    if title and len(words(title)) >= 2 and title_key(title) != title_key(spaced) and title_key(title) in title_key(spaced):
        # Remove the title's words (in order) from the credit; what is left is the name.
        pattern = r'[\s._\-–—:]*'.join(re.escape(w) for w in re.findall(r'[^\W_]+', title))
        rest = text(re.sub(pattern, ' ', spaced, flags=re.I).strip(' .,:;-–—'))
        if rest and re.search(r'[^\W\d_]{2}', rest):
            value = rest
    pieces = [text(p) for p in re.split(r'\s+[-–—]\s+', value) if text(p)]
    if len(pieces) > 1:
        kept = [p for p in pieces if not who.why(p)]
        if len(kept) == 1:
            return kept[0], [p for p in pieces if p != kept[0]]
    # The same name written twice ("Герберт Фрэнк Герберт Фрэнк", "Кинг Стивен; Кинг Стивен") is one credit.
    parts = [text(p) for p in re.split(r'\s*[,;/]\s*', value) if text(p)]
    if len(parts) > 1 and all(same_person(parts[0], p) for p in parts[1:]):
        return parts[0], []
    tokens = value.split()
    half = len(tokens) // 2
    if len(tokens) >= 4 and len(tokens) % 2 == 0 and same_person(' '.join(tokens[:half]), ' '.join(tokens[half:])):
        return ' '.join(tokens[:half]), []
    return value, []


def _numbered_title(set_title, value):
    """Ruling 13 (Sergei 2026-10-24): a numbered part with no title of its own is named after its
    set plus its number: "Торадора! Том 5" in the set "Торадора!" -> "Торадора! 5"."""
    from split_books import _arabic
    numbers = re.findall(r'(?<!\d)(\d{1,3})(?!\d)', _arabic(clean_title(value))[-24:])
    if not numbers or not clean_title(set_title):
        return ''
    return '%s %d' % (clean_title(set_title), int(numbers[-1]))


# ------------------------------------------------------------ 0.22.1, item 9: the folder structure is a local source
# Sergei 2026-10-25 (ruling 6: a local source is enough): "Z:\Audiobooks\James Rollins\Sigma Force\2. Map of Bones\" is
# James Rollins, Sigma Force #2, "Map of Bones". Author folder, series folder, then the book: a folder or a file named
# "N. Title", "Книга N. Title", "<Series> N. Title" or "N Title", with an uploader's catalog number before "Книга N"
# ("477. Книга 1. Аннигиляция (Сергей Пухов)") and a reader in brackets after it.
STRUCTURE_VERSION = 'folders-v1'
_UPLOADER = re.compile(r'^\s*\d{2,6}\s*\.\s+(?=(?:книга|кн\.|book|том|т\.|vol\.?|volume)\s*[#№]?\s*\d)', re.I)
_BOOK_POSITION = re.compile(r'^\s*(?:(?:книга|кн\.|book|том|т\.|vol\.?|volume)\s*[#№]?\s*)?(\d{1,3}(?:[.,]5)?)(?:\s*[.:_)\-–—]\s*|\s+)(\S.*)$', re.I)
_SERIES_POSITION = re.compile(r'^\s*(\D{2,80}?)[\s_]+(\d{1,3}(?:[.,]5)?)\s*[.:\-–—]\s*(\S.*)$')
_SERIES_WORDS = re.compile(r'[\s,_-]+(?:trilogy|series|saga|cycle|chronicles?|duology|quartet|tetralogy|трилогия|серия|сага|цикл|дилогия|тетралогия)\s*$', re.I)
_READER_TAIL = re.compile(r'\s*[(\[]([^()\[\]]{3,80})[)\]]\s*$')
_LOOKALIKE = str.maketrans('аеорсухкмтіАВЕКМНОРСТХІ', 'aeopcyxkmtiABEKMHOPCTXI')


def latin_lookalikes(value):
    """A word written in Latin letters with a Cyrillic look-alike in it ("Sigmа" with a Cyrillic а) in Latin letters."""
    def fix(match):
        word = match[0]
        latin = sum(1 for c in word if 'a' <= c.casefold() <= 'z')
        return word.translate(_LOOKALIKE) if latin and latin >= len(word) - latin else word
    return re.sub(r'[^\W\d_]+', fix, str(value or ''))


def _series_name(name, author):
    """The series a series folder names, without the author written before it, a count of its books or a reader in
    brackets (the live "Ли Патрик – Трэвис Чейз 1-3 [Пухов Сергей]" is "Трэвис Чейз", "Робин Хобб - Сага о Видящих" is
    "Сага о Видящих"). A dash after something that is not the author keeps the name whole ("Книга Крови - Том 4")."""
    value = text(name)
    while True:
        tail = _READER_TAIL.search(value)
        if not tail or not text(value[:tail.start()]):
            break
        value = text(value[:tail.start()])
    value = text(re.sub(r'\s*\(?\d{1,3}\s*[-–—]\s*\d{1,3}\)?\s*$', '', value)) or value
    pieces = re.split(r'\s+[-–—]\s+', value, maxsplit=1)
    if len(pieces) == 2 and re.search(r'[^\W\d_]{2}', pieces[1]) and compare_names(_without_year(pieces[0]), author):
        value = text(pieces[1])
    return value


def _without_year(value):
    """A name with a year beside it ("Энн Маккефри (2012)") without the year."""
    return text(re.sub(r'\s*[(\[]?\s*(?:1[89]|20)\d{2}\s*[)\]]?\s*', ' ', str(value or '')))


def _credit_people(value):
    """The people one credit names ("С. Лукьяненко, И. Кузнецов" is two), a year beside them aside."""
    return [text(p) for p in re.split(r'\s*[,;&/]\s*|\s+(?:и|and)\s+', _without_year(value), flags=re.I) if text(p)]


_READER_KEYS = {}


def _reader_keys(readers):
    """{spelling key: [reader]} of the library's readers and the ruled ones, made once per reader set (W18). A name of
    short words only has no key ('') and is always compared."""
    found = _READER_KEYS.get(readers)
    if found is None:
        found = {}
        for reader in list(readers) + list(RULED_NARRATORS):
            for key in _spelling_keys(reader) or ('',):
                found.setdefault(key, []).append(reader)
        _READER_KEYS.clear()
        _READER_KEYS[readers] = found
    return found


def _title_credit(author_folder, members, index=None, rules=None, folder=''):
    """Whether a piece before a title is a credit of THIS book (Senua's 0.22.1 review, W1 and W8): every person in it is
    the book's own author (its author folder, or an author tag of its files; a slip in a first name aside, "Марина
    Ясинская" tagged "Мария Ясинская") or a known reader (narrator tags, the library's readers, ruling 1). With no author
    tag the file name's own author slot is the book's author (the 0.22.0 file-name reading), so a person there counts.
    A reader credited in an author tag (Sergei's not_author rules, ruling 12) is no author tag here.

    Senua's 0.22.1 review, W18: both lists are built once, only when a piece is judged, with each distinct name once (a
    240-file book with 1,000 library readers made 297,840 same_person calls, 21.3 s); a library reader is looked up by
    its spelling keys, never compared with every credit."""
    known = {}

    def lists():
        if not known:
            own = list(dict.fromkeys(p for m in members for name in NARRATOR_TAGS for p in _credit_people(text(_tags(m).get(name)))))
            keyed = _reader_keys(frozenset((index or {}).get('readers') or ()))
            known['own'], known['keyed'] = own, keyed

            def reader(value):
                if any(same_person(value, r) for r in known['own']):
                    return True
                candidates = dict.fromkeys(r for key in list(_spelling_keys(value)) + [''] for r in keyed.get(key, ()))
                return any(same_person(value, r) for r in candidates)
            known['reader'] = reader
            credits = dict.fromkeys(p for m in members for name in AUTHOR_TAGS for p in _credit_people(text(_tags(m).get(name))))
            known['tagged'] = [p for p in credits if not (rules is not None and rules.not_author(p, folder)) and not reader(p)]
        return known

    def person(value):
        facts = lists()
        if any(compare_names(value, own) or _shares_surname(value, own) for own in [author_folder] + facts['tagged'] if own):
            return True
        if facts['reader'](value):
            return True
        return not facts['tagged'] and looks_like_person(value, index)

    def credited(piece):
        people = _credit_people(piece)
        return bool(people) and all(_person_like(p) and person(p) for p in people)

    def uncredited(piece):
        """The people of a piece that names this book's own author beside someone the tags do not credit (W17: «С.
        Лукьяненко, И. Кузнецов - Печать сумрака» tagged only Лукьяненко), else []."""
        people = _credit_people(piece)
        if len(people) < 2 or not all(_person_like(p) for p in people):
            return []
        missing = [p for p in people if not person(p)]
        return missing if missing and len(missing) < len(people) else []
    credited.uncredited = uncredited
    return credited


def _balanced(value):
    """Bracketed notes removed innermost first ("Чужой Дозор (2017 (с 1932))"), then any bracket left without its pair, so
    no title keeps a dangling ")" (Senua's 0.22.1 review, W1)."""
    value = str(value or '')
    while True:
        stripped = re.sub(r'\s*[(\[{][^()\[\]{}]*[)\]}]', ' ', value)
        if stripped == value:
            break
        value = stripped
    return text(re.sub(r'[()\[\]{}]', ' ', value))


_UNIVERSE = re.compile(r'^\s*(вселенная\s+\S.*?)(?:\s+[-–—]\s+(\S.*?))?\s*$', re.I)


def universe_of(name):
    """Rulings 30 and 37 (Sergei 2026-10-26): a folder named «Вселенная …» is a universe (Universe > Series > Book).
    ('Вселенная Дозоров', 'Межавторский цикл') for "Вселенная Дозоров - Межавторский цикл" (the universe and the one
    numbered series in it); ('Вселенная X', '') for a folder that names only its universe; None for any other name."""
    match = _UNIVERSE.match(text(name))
    return (text(match[1]), text(match[2] or '')) if match else None


def book_universe(row, root):
    """The universe the book's folders name (universe_of on each folder between the library root and its files, nearest
    first), else ''."""
    for name in _ancestors(row, root):
        place = universe_of(name)
        if place:
            return place[0]
    return ''


def _relative_parts(path, root):
    """The path's names below the source root, else None."""
    try:
        parts = Path(path).parts
        base = Path(root).parts
    except (TypeError, ValueError):
        return None
    if not root or len(parts) <= len(base) or [norm(p) for p in parts[:len(base)]] != [norm(p) for p in base]:
        return None
    return list(parts[len(base):])


def folder_structure(row, root, index=None, rules=None, folder=''):
    """{'author', 'series', 'position', 'title', 'reader', 'file_series', 'book', 'book_name', 'series_folder'} when the
    book sits at Author\\Series\\<book> below its source root and <book> names its place in the series; else None.
    <book> is the folder that holds every file, or the file itself when it sits directly in the series folder."""
    members = row.get('members') or []
    if not members:
        return None
    paths = [_relative_parts(m['path'], root) for m in members]
    if any(p is None or len(p) < 3 for p in paths) or len({tuple(norm(x) for x in p[:3]) for p in paths}) != 1:
        return None
    first = paths[0]
    author, series = text(first[0]), text(first[1])
    if norm(author) in CONTAINER_NAMES or norm(series) in CONTAINER_NAMES or COLLECTION_FOLDER.search(author) or COLLECTION_FOLDER.search(series):
        return None
    if not looks_like_person(author, index) or looks_like_person(_series_name(series, author), index) or DISC.fullmatch(series.strip()):
        return None
    if _BOOK_POSITION.match(_UPLOADER.sub('', _series_name(series, author))):
        # Senua's 0.22.1 review, W2: a second-level folder named like a book ("James S. A. Corey\5. Игры Немезиды\5. Игры
        # Немезиды 1.m4b", "Joe Hill\930. Коробка в форме сердца (Михаил Прокопов)") is that book's own folder under its
        # author, never a series: no series «5. Игры Немезиды» #5.
        return None
    if len(first) == 3:
        if len(members) != 1:
            return None
        book, kind = Path(first[2]).stem, 'file'
    else:
        book, kind = first[2], 'folder'
    name = text(book)
    reader = ''
    tail = _READER_TAIL.search(name)
    if tail:
        reader, name = text(tail[1]), text(name[:tail.start()])
    name = _UPLOADER.sub('', name)
    file_series = ''
    match = _BOOK_POSITION.match(name)
    if match:
        position, title = match[1], match[2]
    else:
        match = _SERIES_POSITION.match(name)
        if not match or kind != 'file' or looks_like_person(match[1], index):
            return None
        file_series, position, title = text(match[1]), match[2], match[3]
    title = text(re.sub(r'\s*[-–—]\s*$', '', title))
    # "Title - Author" or "Author - Title" written into the book's name: the author is not part of the title, nor a year
    # beside the author ("08. Энн Маккефри (2012) - Белый дракон").
    for piece in re.split(r'\s+[-–—]\s+', title):
        if piece != title and (compare_names(piece, author) or compare_names(_without_year(piece), author)):
            title = text(re.sub(r'(?:^|\s+[-–—]\s+)' + re.escape(piece) + r'(?:\s+[-–—]\s+|$)', ' - ', title).strip(' -–—'))
    # Senua's 0.22.1 review, W1: in a shared-universe folder the book's own author stands before its title ("16 - Сергей
    # Недоруб - Севастопольский дозор" in "Сергей Лукьяненко\Вселенная Дозоров - Межавторский цикл", "05 - С. Лукьяненко, И.
    # Кузнецов - Печать сумрака"): a leading piece that is only such people is a credit, never part of the title.
    # Her W8 (Jane 2026-10-26): only the book's own author or a known reader is such a credit; any other person is part of
    # the title («Жозеф Фуше - Портрет политического деятеля» in "Стефан Цвейг\Биографии", tagged Стефан Цвейг).
    credited = _title_credit(author, members, index, rules, folder)
    uncredited = []
    while True:
        pieces = re.split(r'\s+[-–—]\s+', title, maxsplit=1)
        if len(pieces) < 2 or not re.search(r'[^\W\d_]{2}', _balanced(pieces[1])):
            break
        if not credited(pieces[0]):
            # Senua's 0.22.1 review, W17: the book's own author beside a co-author the tags do not name. The people are
            # no part of the title; who the author is becomes a question (identify), never filed in silence.
            missing = credited.uncredited(pieces[0])
            if not missing:
                break
            uncredited += missing
        title = text(pieces[1])
    title = clean_title(_balanced(title))
    if not title or not re.search(r'[^\W\d_]{2}', title) or garbled(title) or NARRATOR_MARKER.search(title) or CHAPTER_LABEL.match(title)             or set(words(title)) <= PART_WORDS or PART_FOLDER.search(name) or DISC.search(name):
        return None  # a disc, part or chapter folder ("1 часть", "CD 2") is a piece of a book, not a book of a series
    position = position.replace(',', '.')
    position = str(int(position)) if position.isdigit() else position
    named = _series_name(series, author)
    place = universe_of(named)
    if place and not place[1]:
        return None  # a folder that names only its universe holds books of it, in no series (book_universe)
    # The file names carry the folder's title too ("Энн Маккефри (2012) - Белый дракон (Часть 1).m4b"): folder and file
    # names agree, so they win over a tag that names something else (the series album "Пернский цикл"), item 9. Only for a
    # book FOLDER (Senua's 0.22.1 review, W1): a single file's "folder title" is its own name, so it always "agrees" and
    # beat every clean tag title («Сергей Недоруб - Севастопольский дозор», «Игры Немезиды 1» with the file's part number).
    key = title_key(title)
    files = kind == 'folder' and bool(key) and any(key in title_key(Path(m['path']).stem) for m in members)
    # Rulings 30 and 37: «Вселенная Дозоров - Межавторский цикл» is the universe and its one numbered series, named in full.
    return {'version': STRUCTURE_VERSION, 'author': author, 'universe': place[0] if place else '',
            'series': place[1] if place else latin_lookalikes(text(_SERIES_WORDS.sub('', named)) or named),
            'position': position, 'title': title, 'reader': reader, 'file_series': file_series, 'book': kind, 'book_name': text(book),
            'series_folder': series, 'files_name_title': files, 'uncredited': uncredited}


_BARE_NUMBER = re.compile(r'(?:\s*[-_.,]\s*|\s+)\d{1,3}\s*$')


def whole_in_book_folder(row, siblings):
    """Backlog item 10(b) (Sergei 2026-10-25: a single file is a whole book unless real sibling parts exist), applied by Jane
    to numbered files (2026-10-26, Senua's 0.22.1 review W1): a single file whose name ends in a bare number ("5. Игры
    Немезиды 1.m4b", one 16 h file) with no other audio file beside it, in a folder that names the book without that
    number ("5. Игры Немезиды"), is the whole book: the folder's title, never "set name + number". Rulings 13 and 15 name
    a numbered file set name + number only when sibling files exist. Returns that title, else ''. siblings None (not
    read) is never "no siblings"; a volume or part word ("Том 5", "Часть 1") is not a bare number, and a bitrate is
    still asked."""
    members = row.get('members') or []
    if len(members) != 1 or siblings is None or siblings:
        return ''
    path = Path(members[0]['path'])
    stem = clean_title(_index_stripped(path.stem))
    if not _BARE_NUMBER.search(stem) or _BITRATE_TAIL.search(stem):
        return ''  # a number that looks like a bitrate ("Антитела 128") is asked (Q3, odd_identity), never dropped
    book = text(_BARE_NUMBER.sub('', stem))
    folder = text(path.parent.name)
    while True:
        tail = _READER_TAIL.search(folder)
        if not tail or not text(folder[:tail.start()]):
            break
        folder = text(folder[:tail.start()])
    folder = _UPLOADER.sub('', folder)
    match = _BOOK_POSITION.match(folder)
    if not match:
        # Senua's 0.22.1 review, W14: only a folder that carries the book's position or an uploader number ("5. Игры
        # Немезиды", "930. Коробка в форме сердца") is that book's own folder. A set's folder is named the same way as its
        # volumes ("Торадора!\Торадора! 6.m4b", "Ведьмак\Ведьмак 3.m4b"): a lone volume there keeps its number (rulings 13, 15).
        return ''
    folder = clean_title(match[2])
    return book if book and re.search(r'[^\W\d_]{2}', book) and title_key(folder) == title_key(book) else ''


def _transliterated_title(a, b):
    """The same words in two scripts ("Kosti volhvov" / "Кости волхвов"): a transliteration, not a translation."""
    left, right = words(a), words(b)
    return bool(left) and len(left) == len(right) and all(transliterated(x, y) or norm(x) == norm(y) for x, y in zip(left, right))


def _structured_title(title, structure, author_names, index=None):
    """The book's title once its place in Sergei's folders is known: (title record, the replaced tag title or '').
    The tag title stays unless it is empty, a reader credit, a person, only the series and the book's number, the
    series and number before the folder's title ("Anita Blake 0 - Those Who Seek Forgiveness"), or a translation whose
    original the folder names in Latin letters ("Кости волхвов" in "2. Map of Bones", ruling 16)."""
    folder = structure['title']
    record = {'state': 'one', 'value': folder, 'basis': 'folder_name', 'how': 'the folder structure (Author\\Series\\N. Title)',
              'sources': [{'kind': 'folder structure', 'value': structure['book_name']}]}
    if title is None:
        return record, ''
    value = title['value']
    key, folder_key = title_key(value), title_key(folder)
    if key == folder_key:
        # The same title; a file name read without a tag ("25 - Марина Ясинская - Чужой Дозор (2017 (с 1932))") keeps no
        # dangling bracket either (Senua's 0.22.1 review, W1).
        return (dict(title, value=clean_title(_balanced(value))) if re.search(r'[()\[\]{}]', value) else title), ''
    series_names = [s for s in (structure['series'], structure['file_series'], structure['series_folder']) if s]
    numbered = {title_key('%s %s' % (s, structure['position'])) for s in series_names}
    if NARRATOR_MARKER.search(value) or looks_like_person(value, index) or any(compare_names(value, a) for a in author_names if a) \
            or key in numbered or key in {title_key(s) for s in series_names}:
        return record, value
    if key.endswith(folder_key) and any(key.startswith(title_key(s)) for s in series_names):
        return record, value
    if structure.get('book') == 'file' and title.get('basis') == 'file_name':
        # Senua's 0.22.1 review, W15: with no title tag, a single file's title was the 0.22.0 file-name reading, which takes
        # "X - Y" for "Author - Title" («Ревущий мясник» of "3. Сын целлулоида - Ревущий мясник.m4b"). The structure read the
        # same name knowing the folders and drops only a credit of this book (W1, W8), so it wins.
        return dict(record, how=record['how'] + '; read from the file name knowing its folders'), value
    if structure.get('files_name_title') and folder_key not in key and script(folder) == script(value):
        # The folder and the file names name this book; the tag names something else (a series album, item 9). A tag
        # that adds to the folder's title ("Единая теория всего. Том 1" in "4. Единая Теория Всего") is kept above.
        return dict(record, how=record['how'] + '; the file names agree, the tag "%s" names something else' % value), value
    if script(folder) == 'latin' and script(value) == 'cyrillic' and not _transliterated_title(value, folder):
        # The folder names the original title in Latin letters; the tag carries the translation (ruling 16).
        return dict(record, how=record['how'] + '; the original title, the tag "%s" is the translation (ruling 16)' % value, aliases=[value]), value
    return title, ''


def _named_elsewhere(name, members, ancestors):
    """«Призрак дома на холме» (Sergei 2026-10-26): a person-shaped "Name - " before a title in a tag is a credit when
    another local source names the same person: a folder above the book ("Shirley Jackson") or the composer tag. The
    composer tag alone never names an author (here it often names the reader); it only confirms the name before the dash."""
    if not _person_like(name):
        return False
    others = [text(_tags(m).get('composer')) for m in members] + [clean_title(a) for a in ancestors[:3]]
    return any(value and _person_like(value) and (compare_names(name, value) or same_person(name, value)) for value in others)


def _original_from_file_name(title, author, members, candidates, index=None):
    """«The Haunting of Hill House.m4b» tagged «Призрак дома на холме» by an author the library writes in Latin letters:
    the file name carries the English original (rulings 16 and 29), the tag the translation (kept as an alias). Only one
    file, a Latin name of two or more words with no digit that is no transliteration of the tag title, no person, no
    chapter or junk name and no Russian written in Latin letters. Returns the title record, or None."""
    if len(members) != 1 or not title or not author or script(title['value']) != 'cyrillic' or title.get('basis') != 'tag':
        return None
    stem = clean_title(Path(members[0]['path']).stem)
    if script(stem) != 'latin' or len(words(stem)) < 2 or re.search(r'\d|_', stem) or norm(stem) in JUNK_TITLES \
            or set(words(stem)) <= PART_WORDS or _transliterated_title(stem, title['value']) or looks_like_person(stem, index) \
            or _russian_in_latin(stem, 'Автор'):
        return None
    latin = script(author['name']) == 'latin' or any(script(c['name']) == 'latin' and compare_names(c['name'], author['name']) for c in candidates)
    if not latin:
        return None
    return dict(title, value=stem, basis='file_name', aliases=list(title.get('aliases') or []) + [title['value']],
                how='the file name, the original title (rulings 16 and 29); the tag "%s" is the translation' % title['value'],
                sources=title['sources'] + [{'kind': 'file name', 'value': Path(members[0]['path']).stem}])


class _Readers:
    """Who reads in this library and this book (guard 1)."""

    def __init__(self, own, bracketed, catalog, rules, folder):
        self.own = [r for r in own if r]
        self.bracketed = [r for r in bracketed if r]
        self.catalog = catalog or ()
        self.rules = rules
        self.folder = folder

    def why(self, name):
        """'' when the name may be an author, else the plain reason it is a reader."""
        if not name:
            return ''
        if self.rules is not None and self.rules.not_author(name, self.folder):
            return 'Sergei: not an author (a reader, label or uploader)'
        if any(same_person(name, r) for r in RULED_NARRATORS):
            return 'a reader named in Sergei ruling 1 (2026-10-13)'
        if any(compare_names(name, r) for r in self.own):
            return 'credited as the reader of this book'
        if any(compare_names(name, r) for r in self.bracketed):
            return 'named in brackets in a file or folder name (a reader or uploader)'
        if any(same_person(name, r) for r in self.catalog):
            return 'credited as a reader on other books in this library'
        return ''

    def count(self, name):
        return sum(1 for r in self.catalog if same_person(name, r)) if self.catalog else 0


def identify(row, root='', siblings=None, readers=None, index=None, rules=None):
    """v5 identity record (title + author from one local source). Same shape as agreement(), plus
    'ask' (a question for Sergei) or 'held' (a piece of a bigger book). Pure except for the rules
    object (Sergei's author rules, already loaded) and index (catalog_index, already read)."""
    members = row.get('members', [])
    components = _path_components(row, root)
    ancestors = _ancestors(row, root)
    folder_text = '\\'.join(reversed(ancestors))
    embedded = _embedded(row)
    own_readers = list(embedded['readers']) + narrator_names([c['value'] for c in components] + ancestors[:2])
    who = _Readers(own_readers, bracketed_people([c['value'] for c in components] + ancestors[:2]),
                   readers if readers is not None else (index or {}).get('readers'), rules, folder_text)
    ignored = []
    conflicts = []
    collection_credits = []
    # ------------------------------------------------------------ title (one source is enough)
    part = _part_book(row, root, siblings, components, numbered_names=True)
    title = None
    tag_title_author = ''
    if part and part['title']:
        title = dict(part['title'])
    if title is None:
        field = 'album' if len(members) > 1 or members and text(_tags(members[0]).get('album')) else 'title'
        value, mixed = _consistent(members, ('album',)) if len(members) > 1 else (text(_tags(members[0]).get(field)), False) if members else ('', False)
        if len(members) > 1 and not value and not mixed and row.get('numbered_set'):
            # A same-title set (groups.py, guard 2): every file carries the one title tag.
            titles = {title_key(_tags(m).get('title')) for m in members}
            if len(titles) == 1 and '' not in titles:
                field = 'title'
                value = text(_tags(members[0]).get('title'))
        if value and garbled(value):
            ignored.append({'field': field, 'value': value, 'why': 'garbled text is not used'})
            value = ''
        if value and norm(value) in JUNK_TITLES:
            ignored.append({'field': field, 'value': value, 'why': 'names the format, not the book'})
            value = ''
        if value and not mixed:
            title = {'state': 'one', 'value': clean_title(value), 'basis': 'tag', 'how': 'the embedded %s tag' % field,
                     'sources': [{'kind': 'embedded', 'field': field, 'value': value}]}
            # "Ширли Джексон - Призрак дома на холме" in the title tag: the person before the dash is an
            # author credit, the rest is the title.
            parsed = filename_identity(value + '.x')
            dotted = re.match(r'^\s*([^.\d]{3,60}?)\.\s+(\S.*)$', value)
            if parsed.get('author') and (looks_like_person(parsed['author'], index) or _named_elsewhere(parsed['author'], members, ancestors)) \
                    and re.search(r'[^\W\d_]{2}', parsed.get('title', '')):
                title['value'] = clean_title(parsed['title'])
                title['how'] += ' (the author named before the title is set aside)'
                tag_title_author = parsed['author']
            elif dotted and looks_like_person(dotted[1], index) and re.search(r'[^\W\d_]{2}', dotted[2]):
                # 0.22.1, item 10 (Sergei 2026-10-25): "Джастин Кронин. Перерождение 2" in the title tag: the person before
                # the full stop is an author credit, never part of the title.
                title['value'] = clean_title(dotted[2])
                title['how'] += ' (the author named before the title is set aside)'
                tag_title_author = text(dotted[1])
    if title is None:
        named = dict(row.get('numbered_set') or {})
        if named.get('name') and (garbled(named['name']) or norm(clean_title(named['name'])) in JUNK_TITLES):
            # Senua's 0.22.0 review, G2: a set named by a junk title tag ("Аудиокнига", "Без имени") has no name.
            ignored.append({'field': 'title', 'value': named['name'], 'why': 'names the format, not the book'})
            named['name'] = ''
        for component in components:
            if component['kind'] in ('folder', 'parent folder'):
                continue
            parsed = filename_identity(component['value'] + '.x')
            value = clean_title(_index_stripped(named.get('name') or parsed.get('title') or component['value']), component['numbered'])
            if not value and component['kind'] == 'file name' and lone_number(row, component['value'], siblings):
                value = clean_title(component['value'])  # «1408.m4b» (item 10 b): the number is the book's title
            if value and not garbled(value) and (re.search(r'[^\W\d_]{2}', value) or component['kind'] == 'file name' and lone_number(row, value, siblings)):
                title = {'state': 'one', 'value': value, 'basis': 'file_name', 'how': 'the %s' % component['kind'],
                         'sources': [{'kind': component['kind'], 'value': component['value']}]}
                break
        if title is None and named.get('name') and not garbled(named['name']):
            title = {'state': 'one', 'value': clean_title(named['name']), 'basis': 'file_name', 'how': 'the shared start of the file names',
                     'sources': [{'kind': 'file names', 'value': named['name']}]}
    if title is None:
        for component in components:
            if component['kind'] != 'folder':
                continue
            parsed = filename_identity(component['value'] + '.x')
            value = clean_title(parsed.get('title') or component['value'])
            if value and not garbled(value) and re.search(r'[^\W\d_]{2}', value) and norm(value) not in CONTAINER_NAMES:
                title = {'state': 'one', 'value': value, 'basis': 'folder_name', 'how': 'the folder name',
                         'sources': [{'kind': 'folder', 'value': component['value']}]}
                break
    # 0.22.1, item 9 (Sergei 2026-10-25, ruling 6): the folder structure Author\Series\N. Title is a local source. It names the
    # series and the book's place in it, the author, and the title when the tags do not (or carry the translation of a
    # title the folder names in Latin letters, ruling 16).
    structure = folder_structure(row, root, index, rules, folder_text) if not (part and part['title']) else None
    if structure:
        title, replaced = _structured_title(title, structure, [structure['author'], tag_title_author], index)
        if replaced:
            ignored.append({'field': 'title', 'value': replaced, 'why': 'the folder structure names the book (Author / Series / N. Title)'})
    if part and part['blocked']:
        conflicts.append({'field': 'title', 'detail': part['blocked'], 'force': True, 'piece': 'part_set',
                          'position': part['position'], 'parts': part['parts'], 'set': part['set_title']})
    pieces = _piece_conflicts(row, title['value'] if title else '', part, siblings, components, numbered=bool(title and title.get('basis') == 'number_rule'))
    if structure:
        # Its own book of a series (Sergei: "Перерождение 2. Двенадцать" is book 2, "Двенадцать"): no chapter or part of another.
        pieces = [p for p in pieces if p.get('piece') not in ('part_title', 'chapter', 'numbered_part', 'siblings')]
    whole = '' if structure or part else whole_in_book_folder(row, siblings)
    if whole:
        # Item 10(b) as Jane applied it (above): the whole book in its own folder, its number no part number.
        pieces = [p for p in pieces if p.get('piece') not in ('part_title', 'numbered_part')]
        value = clean_title(title['value']) if title is not None else ''
        if value and _BARE_NUMBER.search(value) and title_key(_BARE_NUMBER.sub('', value)) == title_key(whole):
            # A title read from the name ("Игры Немезиды 1", no title tag) loses the number too.
            title = dict(title, value=whole, how=title['how'] + '; the whole book in its own folder, no part number (item 10(b))')
    for piece in pieces:
        if piece['piece'] == 'numbered_part' and title and title['basis'] == 'tag':
            # Ruling 13: "Торадора! Том 5" with the title tag "Торадора!" is part 5, named after its set.
            named = _numbered_title(title['value'], piece['component']['value'])
            if named:
                title = {'state': 'one', 'value': named, 'basis': 'number_rule', 'how': 'Set name + part number (Sergei 2026-10-24, ruling 13)',
                         'sources': [title['sources'][0], {'kind': piece['component']['kind'], 'value': piece['component']['value']}]}
                continue
        conflicts.append(piece)
    if len(members) == 1 and not part and title and Path(members[0]['path']).suffix.lower() == '.m4b' \
            and any(c.get('piece') in ('part_title', 'numbered_part', 'siblings') for c in conflicts):
        # Rulings 13 and 15: a whole .m4b numbered as one part of a set ("Незнакомцы 1.m4b",
        # "Лучший экипаж Солнечной, Part 1.m4b") whose set cannot be proven is its own book, named
        # after the set plus its number. Chapter files and unnumbered pieces stay held.
        stem = clean_title(_index_stripped(Path(members[0]['filename']).stem))
        tag_title = clean_title(text(_tags(members[0]).get('title')))
        if TRAILING_PART.search(stem):
            base = TRAILING_PART.sub('', tag_title) if TRAILING_PART.search(tag_title) else text(_tags(members[0]).get('album')) or TRAILING_PART.sub('', stem)
            named = _numbered_title(base, stem)
            if named and re.search(r'[^\W\d_]{2}', named):
                conflicts = [c for c in conflicts if c.get('piece') not in ('part_title', 'numbered_part', 'siblings')]
                title = {'state': 'one', 'value': named, 'basis': 'number_rule', 'how': 'Set name + part number (Sergei 2026-10-24, rulings 13 and 15)',
                         'sources': [title['sources'][0], {'kind': 'file name', 'value': Path(members[0]['filename']).stem}]}
    if len(members) == 1 and (row.get('volume_of_set') or {}).get('kept'):
        # Kept as separate books by Sergei (Judy's spec, 2026-10-25): the set question is answered, so this file never
        # returns as one part of a bigger book for it. Title from its own tag, else its file name, else set name + part number.
        conflicts = [c for c in conflicts if c.get('piece') not in ('part_title', 'numbered_part', 'siblings', 'part_set')]
        tags = _tags(members[0])
        album = clean_title(text(tags.get('album')))
        album_key = title_key(work_name(album) or album)

        def own(value):
            value = clean_title(_index_stripped(value))
            named = work_name(value) if value and not garbled(value) else ''
            return value if named and title_key(named) != album_key else ''
        stem = Path(members[0]['filename']).stem
        tag_title, name_title = own(text(tags.get('title'))), own(stem)
        number = re.match(r'^\s*(\d{1,4})', str(tags.get('track') or tags.get('tracknumber') or '')) or re.search(r'(\d{1,4})\D*$', stem)
        if tag_title:
            title = {'state': 'one', 'value': tag_title, 'basis': 'tag', 'how': 'the embedded title tag', 'sources': [{'kind': 'embedded', 'field': 'title', 'value': tag_title}]}
        elif name_title:
            title = {'state': 'one', 'value': name_title, 'basis': 'file_name', 'how': 'the file name', 'sources': [{'kind': 'file name', 'value': stem}]}
        elif album and number and (not title or title_key(title['value']) == album_key):
            title = {'state': 'one', 'value': '%s %d' % (album, int(number[1])), 'basis': 'number_rule', 'how': 'Set name + part number (rulings 13 and 15)',
                     'sources': [{'kind': 'embedded', 'field': 'album', 'value': album}, {'kind': 'file name', 'value': stem}]}
    # ------------------------------------------------------------ author (one source is enough)
    candidates = []  # {'name', 'source', 'basis', 'kind'} in order of preference
    folk = []  # folk-tale credits whose rule files the book under its compiler or reteller, if one is credited

    def offer(name, source, basis, kind):
        name = text(name)
        if not name:
            return
        if rules is not None:
            # Sergei's lasting answers (ruling 12) decide before any guess, garbled spellings included.
            target = rules.same_as(name, folder_text)
            if target:
                if not any(same_person(target, c['name']) for c in candidates if c['kind'] == kind):
                    candidates.append({'name': target, 'source': source, 'basis': basis, 'kind': kind, 'rule': rules.rule_id(name, folder_text), 'as_seen': name})
                return
            if rules.keep(name, folder_text):
                if not any(same_person(name, c['name']) for c in candidates if c['kind'] == kind):
                    candidates.append({'name': name, 'source': source, 'basis': basis, 'kind': kind, 'rule': rules.rule_id(name, folder_text)})
                return
        if kind == 'tag' and not garbled(name):
            name, dropped = _clean_credit(name, title['value'] if title else '', who)
            for reader in dropped:
                ignored.append({'field': source, 'value': reader, 'why': who.why(reader) or 'joined to the author credit'})
            if not name:
                return
            pieces = [text(p) for p in re.split(r'\s+[-–—]\s+', name) if text(p)]
            people = [p for p in pieces if _person_like(p)]
            if len(people) >= 2:
                # Senua's 0.22.0 review, G4 (ruling 14): "Author - Reader" where neither name is a known reader credits two
                # people. Never the whole string; a file or folder name that names one decides it, else it is asked.
                # N5: the same for three or more names ("Варго - Сидоров - Петрова"); a piece that is no person is set aside.
                for piece in pieces:
                    if piece in people:
                        offer(piece, source, basis, kind)
                    else:
                        ignored.append({'field': source, 'value': piece, 'why': 'not a person, between dashes in a credit naming several people'})
                return
        if title and title_key(name) == title_key(title['value']):
            # "Потаённое окно в потаённый сад" in the artist tag of that book: the title, not an author.
            ignored.append({'field': source, 'value': name, 'why': 'the book title, not an author'})
            return
        if garbled(name):
            ignored.append({'field': source, 'value': name, 'why': 'garbled text is not used'})
            return
        if kind == 'tag' and numbered_credit(name, [title['value'] if title else '', Path(members[0]['filename']).stem if members else '']):
            # «1408» (Sergei 2026-10-26): the artist tag "sk 1408", initials and the title's number, is a rip label, no author.
            ignored.append({'field': source, 'value': name, 'why': 'initials and a number, not a person\'s name'})
            return
        if norm(name) in NOT_PEOPLE or norm(name) in VARIOUS_AUTHORS or EDITOR_MARKER.search(name) or len(re.split(r'\s*[,;]\s*', name)) >= 3:
            collection_credits.append(name)
            ignored.append({'field': source, 'value': name, 'why': 'a collection, editor or several-author credit, never one author'})
            return
        if rules is not None and rules.collection(name, folder_text):
            collection_credits.append(name)
            if rules.options(name, folder_text).get('fallback') == 'compiler':
                folk.append(name)
            ignored.append({'field': source, 'value': name, 'why': 'Sergei: a collection or anthology name, never one author'})
            return
        if NARRATOR_MARKER.search(name):
            ignored.append({'field': source, 'value': name, 'why': 'reader/narrator credit, never the author'})
            return
        reason = who.why(name)
        if reason:
            ignored.append({'field': source, 'value': name, 'why': reason})
            return
        if any(same_person(name, c['name']) or compare_names(name, c['name']) or slip_same(name, c['name']) for c in candidates if c['kind'] == kind):
            return  # one person; a one-letter slip ("Стейплз" / "Стейплс") included
        candidates.append({'name': name, 'source': source, 'basis': basis, 'kind': kind})

    for name in AUTHOR_TAGS:
        value, mixed = _consistent(members, (name,))
        if mixed:
            # Ruling 19 (joined parts): one person spelled two ways ("Иван Петров" / "Петров Иван") is one credit, in its
            # most common spelling; different people stay "differs between files".
            spellings = [text(_tags(m).get(name)) for m in members if text(_tags(m).get(name))]
            distinct = list(dict.fromkeys(spellings))
            if all(same_person(distinct[0], v) or compare_names(distinct[0], v) for v in distinct[1:]):
                value = max(distinct, key=lambda v: (spellings.count(v), -distinct.index(v)))
            else:
                ignored.append({'field': name, 'value': '', 'why': 'differs between files'})
                continue
        offer(value, {'album_artist': 'album artist tag', 'albumartist': 'album artist tag'}.get(name, name + ' tag'), 'tag', 'tag')
    # Guard 3: a collection credit in the tags ("Сборник", "Разные авторы", an editor, a long list of
    # authors) files the book as a collection unless a tag also names one person.
    tag_collection = bool(collection_credits)
    slots = []
    unnamed = []  # author slots that do not look like a person: proposals for a question, never the author
    if tag_title_author:
        before = len(candidates)
        offer(tag_title_author, 'title tag', 'tag', 'slot')
        if len(candidates) > before:
            candidates[-1]['person'] = True
            slots.append(candidates[-1])
    for component in components:
        parsed = filename_identity(component['value'] + '.x')
        claimed = parsed.get('author') or ''
        if not claimed or row.get('numbered_set') and component['kind'] in ('file name', 'file names'):
            # In a numbered set the shared start of the file names is the book, not its author.
            continue
        if not _claims_person(claimed) and not (norm(claimed) in NOT_PEOPLE or EDITOR_MARKER.search(claimed)):
            continue
        source = {'file name': 'file name', 'file names': 'file name', 'folder': 'folder name', 'parent folder': 'folder name'}[component['kind']]
        before = len(candidates)
        offer(claimed, source, 'file_name' if source == 'file name' else 'folder_name', 'slot')
        if len(candidates) > before:
            slot = candidates[-1]
            # Only a slot that shows it is a person may contradict a tag. "Series - 01. Title" and
            # "Title - Person" names put a non-person in the author slot: such a slot is never the
            # author; any other slot is the author when no tag names one ("Author - Title" is the
            # library's naming convention).
            rest = text(parsed.get('title'))
            slot['person'] = looks_like_person(slot['name'], index) or any(compare_names(slot['name'], c['name']) for c in candidates if c['kind'] == 'tag')
            slot['plausible'] = slot['person'] or not (re.match(r'^\W*\d', rest) or looks_like_person(rest, index) or PART_FOLDER.search(slot['name'])
                                                       or re.match(r'^\W*(?:часть|глава|part|chapter|том|книга|book|vol)', slot['name'], re.I))
            if slot['person']:
                slots.append(slot)
            elif not slot['plausible']:
                candidates.pop()
                unnamed.append(slot)
    for component in components:
        if component['kind'] not in ('folder', 'parent folder') or filename_identity(component['value'] + '.x').get('author'):
            continue
        person = _person_folder(component, index)
        if person and title and title_key(person) != title_key(title['value']):
            offer(person, 'folder name', 'folder_name', 'folder')
    for ancestor in ancestors[2:4]:
        # A person-named author folder above the book's own folders ("Stephen King\Регуляторы\...").
        person = _person_folder({'value': ancestor}, index)
        if person:
            offer(person, 'folder name', 'folder_name', 'folder')
    if structure:
        # Item 9: the author folder. Scrambled tags (Sergei 2026-10-25, "Black Order": the title in the artist tag, the
        # reader in the album tag): a credit that is no person and not the folder's author gives way to the folder.
        offer(structure['author'], 'folder name', 'folder_name', 'folder')
        # The tags are scrambled when a title or album tag, or every file name, names the folder's author.
        scrambled = any(compare_names(text(_tags(m).get(f)), structure['author']) for m in members[:3] for f in ('title', 'album') if text(_tags(m).get(f)))             or bool(members) and all(any(compare_names(piece, structure['author']) for piece in re.split(r'\s+[-–—]\s+', Path(m['filename']).stem)) for m in members)
        for c in list(candidates):
            if c['kind'] in ('tag', 'slot') and not c.get('rule') and (scrambled or not c.get('person') and not looks_like_person(c['name'], index))                     and not compare_names(c['name'], structure['author']) and not _shares_surname(c['name'], structure['author']):
                candidates.remove(c)
                if c in slots:
                    slots.remove(c)
                ignored.append({'field': c['source'], 'value': c['name'], 'why': 'not a person; the folder structure names the author'})
    if folk:
        # Folk tales (Sergei 2026-10-24): the compiler or reteller the files credit is the author, else Сборники.
        compiler = _compiler_credit(members)
        if compiler:
            offer(compiler, 'compiler credit', 'tag', 'tag')
    tagged = [c for c in candidates if c['kind'] == 'tag']
    author = None
    ask = None
    def same(a, b):
        return bool(compare_names(a, b) or _shares_surname(a, b))
    if len(tagged) > 1:
        # Two people credited in the tags. One is the author when a file or folder name names it
        # (and no name names the other).
        named = [c for c in tagged if any(same(c['name'], s['name']) for s in candidates if s['kind'] != 'tag')]
        if len(named) == 1:
            author = named[0]
            ignored += [{'field': c['source'], 'value': c['name'], 'why': 'not named in any file or folder name; a recording credit, not the author'} for c in tagged if c is not named[0]]
        else:
            ask = {'kind': 'author_unclear', 'why': 'two_people'}
    elif tagged:
        author = tagged[0]
        if any(not same(s['name'], author['name']) for s in slots):
            ask = {'kind': 'author_unclear', 'why': 'tag_and_name'}
            author = None
    elif not tag_collection:
        if any(not same(a['name'], b['name']) for a in slots for b in slots):
            ask = {'kind': 'author_unclear', 'why': 'names_differ'}
        elif candidates:
            author = candidates[0]
    if structure and structure.get('uncredited') and ask is None:
        # Senua's 0.22.1 review, W17: the name credits the book's author and someone the tags do not name («С. Лукьяненко,
        # И. Кузнецов - Печать сумрака» tagged only Лукьяненко). Two people: asked, each a choice, never filed in silence.
        for name in structure['uncredited']:
            if not any(same_person(name, c['name']) for c in candidates):
                candidates.append({'name': name, 'source': 'file name', 'basis': 'file_name', 'kind': 'slot', 'person': True})
        ask = {'kind': 'author_unclear', 'why': 'two_people'}
        author = None
    if author is None and ask is None and rules is not None:
        # An answer about one of the book's own folders: «Гробница Саргераса» -> Brooks Robert, «Созвездие Льва» -> Сборники.
        found = rules.folder_rule(ancestors)
        if found and found[0] == 'same_as':
            author = {'name': found[1], 'source': 'folder name', 'basis': 'rule', 'kind': 'folder', 'rule': found[2]}
        elif found and found[0] == 'collection':
            collection_credits.append('Sergei: a collection folder')
    route = None
    if author is None and ask is None and title:
        marked = [n for n in ancestors if COLLECTION_FOLDER.search(n)]
        signals = (['collection folder "%s"' % marked[0]] if marked else []) + \
            (['collection title'] if COLLECTION_TITLE.search(title['value']) else []) + \
            (['collection credit "%s"' % collection_credits[0]] if collection_credits else [])
        if collection_credits or len(signals) >= 1 and any('reader' in i['why'] or 'brackets' in i['why'] or 'Sergei' in i['why'] for i in ignored) \
                or len(signals) >= 2:
            narrators = []
            for value in own_readers + [i['value'] for i in ignored if 'reader' in i['why'] or 'brackets' in i['why'] or 'uploader' in i['why']]:
                name = text(narrator_names([value])[0]) if NARRATOR_MARKER.search(value) and narrator_names([value]) else text(value)
                if name and not any(same_person(name, n) for n in narrators) and norm(name) not in NOT_PEOPLE:
                    narrators.append(name)
            route = {'kind': 'narrator_collection', 'signals': signals or ['collection credit'], 'narrators': narrators[:4], 'credit': COLLECTION_LABEL,
                     'credit_basis': 'tag "%s"' % collection_credits[0] if collection_credits else 'collection label (no author credit locally)'}
    # Ruling 14: a credited person suspected to be a reader is a question for Sergei, never the author.
    suspects = [{'name': i['value'], 'source': i['field']} for i in ignored if i['value'] and i['why'] in (
        'credited as a reader on other books in this library', 'named in brackets in a file or folder name (a reader or uploader)')]
    if author is None and ask is None and route is None:
        ask = {'kind': 'author_unclear', 'why': 'reader'} if suspects and title else {'kind': 'title_author', 'why': 'author_missing' if title else 'both_missing'}
    elif title is None and ask is None:
        ask = {'kind': 'title_author', 'why': 'title_missing'}
    if ask and ask['kind'] == 'title_author' and any('garbled' in i['why'] for i in ignored):
        ask['why'] = 'garbled'
    if not structure and not part:
        original = _original_from_file_name(title, author, members, candidates, index)
        if original:
            ignored.append({'field': 'title', 'value': title['value'], 'why': 'the translation; the file name carries the original title'})
            title = original
    fields = {}
    if title:
        fields['title'] = {k: title[k] for k in ('state', 'value', 'basis', 'how', 'sources', 'aliases') if k in title}
        if title['state'] == 'one' and title['basis'] == 'tag':
            support = _title_support(title['value'], components, author['name'] if author else '')
            if support:
                # Shown for explanation only: one source is enough.
                fields['title'].update(state='green', how=title['how'] + '; the %s agrees (%s)' % (support[0]['kind'], support[1]),
                                       sources=title['sources'] + [{'kind': support[0]['kind'], 'value': support[0]['value']}])
    else:
        fields['title'] = {'state': 'grey', 'value': '', 'basis': '', 'how': 'no local source names it', 'sources': []}
    if author:
        how = {'tag': 'the %s' % author['source'], 'file_name': 'the author part of the file name', 'folder_name': 'the folder name',
               'rule': 'Sergei\'s rule for the folder name'}[author['basis']]
        if author.get('rule'):
            how += '; Sergei\'s rule (ruling 12) for "%s"' % author.get('as_seen', author['name'])
        state = 'one'
        supported = [c for c in candidates if c is not author and compare_names(c['name'], author['name'])]
        value = author['name']
        if supported:
            match = compare_names(author['name'], supported[0]['name'])
            state = 'yellow' if match['match'] == 'cross' else 'green'
            how += '; the %s agrees' % supported[0]['source']
            fuller = max(supported, key=lambda c: len(_parts(c['name'])[0]))
            if len(_parts(value)[0]) < 2 <= len(_parts(fuller['name'])[0]):
                # A surname alone ("Кинг") gives way to the full name another source agrees on.
                value = fuller['name']
        author = dict(author, name=value)
        fields['author'] = {'state': state, 'value': author['name'], 'basis': author['basis'], 'how': how,
                            'sources': [{'kind': author['source'], 'value': author['name']}] + [{'kind': c['source'], 'value': c['name']} for c in supported[:2]],
                            'partial': len(_parts(author['name'])[0]) < 2 and not author.get('rule')}
        if author.get('rule'):
            fields['author']['rule'] = author['rule']
    else:
        fields['author'] = {'state': 'red' if ask and ask['kind'] == 'author_unclear' else 'grey', 'value': '', 'basis': '', 'how': 'no author',
                            'sources': [{'kind': c['source'], 'value': c['name']} for c in candidates[:4]]}
    piece = next((c for c in conflicts if c.get('piece')), None)
    for name in ('series', 'number'):
        value = embedded[name]
        if not value:
            fields[name] = {'state': 'grey', 'value': '', 'sources': [], 'how': 'no embedded %s tag' % name}
            continue
        target = embedded['series']['value'] if name == 'number' and embedded['series'] else value['value']
        supported = next((c for c in components if norm(target) and norm(target) in norm(c['value']) and
                          (name == 'series' or re.search(r'(?<!\d)0*' + re.escape(value['value'].lstrip('0') or '0') + r'(?!\d)', c['value']))), None)
        fields[name] = ({'state': 'green', 'value': value['value'], 'sources': [value, {'kind': supported['kind'], 'value': supported['value']}],
                         'how': 'embedded tag repeated in the %s' % supported['kind']} if supported else
                        {'state': 'grey', 'value': value['value'], 'sources': [value], 'how': 'only the embedded tag names it'})
    if part and part['series'] and (fields['series']['state'] != 'green' or fields['number']['state'] != 'green'):
        fields['series'], fields['number'] = part['series'], part['number']
    from_folders = False
    # Rulings 30 and 37: in a universe folder its one numbered series is the folder's, whatever series a tag names.
    if structure and (structure.get('universe') or fields['series']['state'] != 'green' or fields['number']['state'] != 'green'):
        # Item 9: the series folder and the book's number in it ("Sigma Force\2. Map of Bones", "Книга 1", "Перерождение 2.").
        fields['series'] = {'state': 'green', 'value': structure['series'], 'how': 'the series folder (Author / Series / N. Title)',
                            'sources': [{'kind': 'folder structure', 'value': structure['series_folder']}]}
        fields['number'] = {'state': 'green', 'value': structure['position'], 'how': 'the book\'s number in its series folder',
                            'sources': [{'kind': 'folder structure', 'value': structure['book_name']}]}
        from_folders = True
    # Ruling 41 (Sergei 2026-10-27, "2. Yes"): a name that reads "Series N. Title" fills Series, Number and Title itself and
    # the book files without a question; the series never stays inside the title. A series the files already name the
    # same way keeps its source; one that names another series leaves the title as it is (its own names disagree).
    found = series_title_parts(fields['title']['value'], author['name'] if author else '') if fields['title']['value'] and not part else None
    if found:
        # Ruling 45 (Sergei 2026-10-27): the series its sibling book folders carry decides it when the name only repeats
        # its own title as the series («Мертвый ноль 7. Мертвый ноль» beside «Сновидения Ехо 5. Сундук мертвеца»). A name
        # that names another series keeps it (Senua's 0.22.3 review, M2: one parent folder often holds several series).
        # A sibling that already holds this number in that series shows it is another series: the name stands.
        carried, taken = sibling_series(row, root, index, author['name'] if author else '')
        if carried and found['number'] not in taken and series_key(found['series']) == series_key(found['title']):
            found = dict(found, series=carried)
        named = fields['series']['state'] == 'green' and fields['number']['state'] == 'green'
        whole = fields['title']['value']
        if not named:
            source = [{'kind': 'the title (%s)' % (fields['title'].get('basis') or 'name'), 'value': whole}]
            fields['series'] = {'state': 'green', 'value': found['series'], 'how': 'the series before the number in "%s" (ruling 41)' % whole, 'sources': source}
            fields['number'] = {'state': 'green', 'value': found['number'], 'how': 'the number in "%s" (ruling 41)' % whole, 'sources': source}
        if not named or (norm(fields['series']['value']) == norm(found['series']) and _same_number(fields['number']['value'], found['number'])):
            fields['title'] = dict(fields['title'], value=found['title'], how=fields['title'].get('how', '') + '; the title after the series and number (ruling 41)',
                                   aliases=list(fields['title'].get('aliases') or []) + [whole])
    if fields['series']['state'] == 'green' and series_spelling(fields['series']['value']) != fields['series']['value']:
        # Ruling 46: one series, one spelling, whichever name its files use.
        fields['series'] = dict(fields['series'], value=series_spelling(fields['series']['value']), how=fields['series'].get('how', '') + '; spelled as Sergei ruled (ruling 46)')
    series = {'name': fields['series']['value'], 'number': fields['number']['value']} if fields['series']['state'] == 'green' and fields['number']['state'] == 'green' else {}
    if series and from_folders:
        series['folder'] = True
    accepted = bool(title and (author or route) and not ask and not piece)
    gaps = []
    if accepted and not route:
        if script(fields['title']['value']) != 'latin':
            gaps.append('original_title')
        if not series:
            gaps.append('series')
        if fields['author'].get('partial'):
            gaps.append('author_full')
    if ask:
        fallback = next((a for a in ancestors if norm(a) not in CONTAINER_NAMES and not DISC.fullmatch(a.strip())), '') if not title else ''
        ask['fields'] = {'title': {'proposal': fields['title']['value'] or clean_title(fallback), 'basis': fields['title']['basis'] or ('folder_name' if fallback else '')},
                         'author': {'proposal': author['name'] if author else '', 'basis': author['basis'] if author else ''}}
        if ask['kind'] == 'title_author' and not author and unnamed:
            # "Колесо времени - 01. Око мира": the name's author slot, offered for Sergei to confirm or correct.
            ask['fields']['author'] = {'proposal': unnamed[0]['name'], 'basis': unnamed[0]['basis']}
        if ask['kind'] == 'author_unclear':
            pool = tagged + [s for s in candidates if s['kind'] != 'tag']
            if ask['why'] == 'reader':
                pool = [{'name': s['name'], 'source': {'album_artist': 'album artist tag', 'albumartist': 'album artist tag'}.get(s['source'], s['source'] if ' ' in s['source'] else s['source'] + ' tag')}
                        for s in suspects]
            listed = []
            for c in pool:
                if not any(same_person(c['name'], x['name']) for x in listed):
                    listed.append({'name': c['name'], 'source': c['source'], 'reader_count': who.count(c['name'])})
            # Preselect the best guess: a tag credit, never a reader of other books while another exists.
            listed.sort(key=lambda c: (c['reader_count'] > 0, c['source'] not in ('artist tag', 'author tag'), c['source'] != 'album artist tag'))
            ask['candidates'] = listed[:6]
            ask['fields']['author']['proposal'] = listed[0]['name'] if listed else ''
            ask['fields']['author']['basis'] = 'tag' if listed and listed[0]['source'].endswith('tag') else 'file_name' if listed and listed[0]['source'] == 'file name' else 'folder_name' if listed else ''
    part_book = {'parts': part['parts'], 'position': part['position'], 'set_title': part['set_title'], 'members': list(part['members']),
                 'requires_own_chapters': True} if part and not part['blocked'] else None
    return {'version': IDENTITY_VERSION, 'accepted': accepted, 'route': route if accepted else None, 'part_book': part_book, 'fields': fields,
            'series': series, 'gaps': gaps, 'ignored': ignored, 'conflicts': conflicts, 'ask': ask,
            # Rulings 30 and 37: the universe the book's folders name («Вселенная Дозоров»), else ''.
            'universe': (structure or {}).get('universe') or book_universe(row, root),
            'held': piece['detail'] if piece and not ask else '',
            # Judy 2026-10-24 (0.22.0 review, B4): the typed cause of a "Part of a bigger book" row and its numbers.
            'piece': {k: piece[k] for k in ('piece', 'count', 'position', 'parts', 'set') if k in piece} if piece and not ask else None,
            'path': [{'kind': c['kind'], 'value': c['value']} for c in components]}


def same_author_question(name, forms, rules):
    """Ruling 12: a new author folder name that looks like an author the library already has (another script, a
    near spelling, a surname alone) is asked once: {'kind': 'same_author', 'new', 'existing', 'existing_books', 'why'}.
    None when the name is known, Sergei answered it (same_as / keep), or nothing is close."""
    if rules is None or not name:
        return None
    known = rules.known_authors
    if name.casefold() in known or any(rules.keep(f) or rules.same_as(f) for f in [name] + list(forms)):
        return None
    best = None
    for low, (existing, books) in known.items():
        match = compare_names(name, existing)
        if match and match['exact']:
            # The same full name in the other script or another word order: the language rule already answered it
            # (AuthorRulings 2026-10-24), so the book files under the folder the library has. Not a question.
            return {'kind': 'merge', 'existing': existing}
        why = ('translation' if match['match'] == 'cross' else 'near') if match else ''
        if not why:
            a, b = ' '.join(sorted(words(name))), ' '.join(sorted(words(existing)))
            if slip_same(name, existing) or (script(a) == script(b) != 'other' and min(len(a), len(b)) >= 8 and _edits(a, b, 2) <= 2):
                why = 'near'
        if why and (best is None or books > best[2]):
            best = (why, existing, books)
    if not best:
        return None
    return {'kind': 'same_author', 'new': name, 'existing': best[1], 'existing_books': best[2], 'why': best[0]}


def shown(record):
    """The title and author a row shows for Approve (Judy 2026-10-24, section 3): the identity, else the question's
    proposal. A suspected reader is never proposed (ruling 14): the author is then empty, which files the book under
    Без автора only if Sergei approves without typing or choosing one (ruling 11a)."""
    fields = record['fields']
    ask = record.get('ask') or {}
    proposal = ask.get('fields') or {}
    title = fields['title']['value'] or (proposal.get('title') or {}).get('proposal', '')
    title_basis = fields['title'].get('basis') or (proposal.get('title') or {}).get('basis', '')
    # 0.22.1, item 10 (c): a book held as a piece asks nothing, so its row shows the author the app resolved (it showed an
    # empty Author field and "Goes to Без автора").
    resolved = record.get('accepted') or not ask
    author = fields['author']['value'] if resolved else (proposal.get('author') or {}).get('proposal', '')
    author_basis = fields['author'].get('basis') if resolved else (proposal.get('author') or {}).get('basis', '')
    candidates = list(ask.get('candidates') or [])
    if ask.get('why') == 'reader' or any(c['name'] == author and c.get('reader_count') for c in candidates):
        author, author_basis = '', ''
    if '_' in author:
        # Futaba's 0.22.1 QA, M-2 (Judy 11.3: Goes to follows the Author field): a folder or file name read as the author
        # ("Richard_Ford") is asked with its underscores gone (odd_identity's proposal, which the Author field shows), and
        # Approve with nothing typed files that, never the underscores.
        author = text(author.replace('_', ' '))
    return {'title': title, 'title_basis': title_basis, 'author': author, 'author_basis': author_basis,
            'collection': bool(record.get('route')), 'candidates': candidates, 'kind': ask.get('kind', ''), 'why': ask.get('why', ''),
            'piece': record.get('held', '')}


def settled(record, title, author, state, typed=(), collection=False, rules=None, folder='', answered=False):
    """A copy of the record whose identity is Sergei's (rulings 6a and 6b): state 'entered' for values he saved,
    'approved' for an Approve. Typed fields get basis 'entered'. Questions, pieces and part sets are settled by him.
    rules: his same_as rules apply to the author as they do to a tag (Senua's 0.22.0 review, m2: typed "Терри Пратчетт"
    goes to Pratchett Terry, not to a second folder). answered: the author is his Same author? answer (m3), not typed."""
    import copy
    record = copy.deepcopy(record)
    for name, value in (('title', title), ('author', author)):
        if name == 'author' and collection:
            continue
        old = record['fields'][name]
        basis = 'entered' if name in typed else (old.get('basis') or 'entered')
        how = 'Entered by you' if name in typed else 'Your Same author? answer' if name == 'author' and answered else 'Shown on the row'
        rule = ''
        if name == 'author' and rules is not None and text(value):
            target = rules.same_as(text(value), folder)
            if target:
                rule = rules.rule_id(text(value), folder)
                how += '; Sergei\'s rule (ruling 12) for "%s"' % text(value)
                value = target
        record['fields'][name] = {'state': state, 'value': text(value), 'basis': basis,
                                  'how': how + ('; approved by you (Sergei 2026-10-24, ruling 6b)' if state == 'approved' else ' (Sergei 2026-10-24, ruling 6a)'),
                                  'sources': [{'kind': 'entered by you' if name in typed else 'approval', 'value': text(value)}], 'partial': False}
        if rule:
            record['fields'][name]['rule'] = rule
    if not collection:
        record['route'] = None
    record.update(accepted=True, ask=None, conflicts=[], held='', part_book=None, gaps=[])
    return record


# 0.22.1 (Jane for Sergei, 2026-10-26, after the outcome measurement on the live copy): names the app reads but should
# not file without asking. Once the file-name order (item 9) let held books through, some went to Sorted with names
# like "Антитела 128" (the bitrate), "Neil Gaiman &Terry Pratchett" (two people as one author), "Richard_Ford_Labirint"
# (a folder name as the author), "Мертвый ноль 7. Мертвый ноль" (the series and number in the title) or "Master vetrov
# i zakatov" (Russian in Latin letters). Each is a question on the to-do list with the existing rows (Title or author
# missing, Author unclear); the app renames nothing. When unsure, asking is the safe default.
_BITRATE_TAIL = re.compile(r'(?:[\s_\-–—]+|(?<=[^\W\d_]))(?:64|96|112|128|160|192|256|320)\s*(?:kbps|kb/s|kbit/s)?\s*$', re.I)
# "<Series> N. Title", "<Series> - 01. Title", "<Series> #3 - Title": the series before the number, the title after it.
# The number stands alone ("Warhammer 40000. Месть Гоббо" is no series 40 and book 000).
_SERIES_PARTS = re.compile(r'^(?P<series>.*?[^\W\d_].*?)\s*(?:[\-–—]\s*)?(?P<hash>#\s*)?(?<!\d)(?P<number>\d{1,3}(?:[.,]5)?)\s*(?P<separator>[.:\-–—])\s+(?P<title>.*?[^\W\d_].*)$')
# A word that numbers a part, never a series name ("Книга 1. Пробуждение", "Part 2. The Return").
_NOT_A_SERIES = re.compile(r'^\W*(?:книга|кн|том|т|часть|ч|глава|выпуск|сезон|серия|эпизод|диск|book|volume|vol|part|pt|chapter|episode|season|issue|disc|disk|cd)\W*$', re.I)
# Senua's 0.22.3 review, m4: a "series" that ends in such a word numbers a part of one work («Война и мир. Том 1. Часть 2»).
_PART_TAIL = re.compile(r'(?:^|[\s.,;:\-–—])(?:книга|кн|том|т|часть|ч|глава|выпуск|сезон|эпизод|диск|book|volume|vol|part|pt|chapter|episode|season|issue|disc|disk|cd)\.?\s*$', re.I)
_PEOPLE_JOIN = re.compile(r'\s*(?:[,;&/]|\s+и\s+|\s+and\s+)\s*', re.I)
_RUSSIAN_WORDS = {'i', 'v', 'na', 'iz', 'ot', 'dlya', 'bez', 'ili', 'pro', 'pod', 'nad'}
_TRANSLIT = re.compile(r'zh|kh|shch|yy|iy$|yu|ya|ov$|ogo$|ykh$|aya$|oye$|iye$')


def _people(author):
    """The people a credit names when it joins two or more ("Neil Gaiman &Terry Pratchett", "С. Лукьяненко, А. Громов");
    [] for one person, "Sapkowski, Andrzej" (surname, name) or a name with a suffix ("King, Jr.")."""
    parts = [text(p) for p in _PEOPLE_JOIN.split(str(author or '')) if text(p)]
    people = [p for p in parts if len(words(p)) >= 2 or re.match(r'^[^\W\d_]\.\s*[^\W\d_]', p)]
    return people if len(parts) >= 2 and len(people) >= 2 else []


def _russian_in_latin(title, author):
    """A Russian title written in Latin letters ("Master vetrov i zakatov") on a book whose author the app writes in
    Cyrillic. Lower-case Russian small words and transliteration endings both count; English titles have neither."""
    if script(title) != 'latin' or script(author) != 'cyrillic':
        return False
    tokens = re.findall(r'[A-Za-z]+', str(title))
    small = sum(1 for t in tokens if t in _RUSSIAN_WORDS)  # lower case only: "I Am Legend" is English
    endings = sum(1 for t in tokens if len(t) > 3 and _TRANSLIT.search(t.lower()))
    return small + endings >= 2 and (small or endings >= 2)


def _series_in_title(title, folders=()):
    """True when the title carries a series and number its own names show it should not: a "#N" marker ("Сновидения Ехо
    #3 - Вся правда о нас"), the title repeated after the number ("Мертвый ноль 7. Мертвый ноль", "Крысы 1. Крысы"), or a
    book folder that names the title without the series ("Профессия: инквизитор 7. Война миров" in "Олег Дивов_ Война
    миров_Ирина Зубкова"). A name the files carry the same way everywhere ("Червь 1. Созревание" in "Червь", "Колесо
    времени - 01. Око мира" in a folder of that name) is filed as it is: measured on the live copy, the plain pattern
    alone asked 91 books, 31 of them one consistently named series."""
    found = _SERIES_PARTS.match(text(title))
    if not found:
        return False
    series, tail = words(found['series']), words(found['title'])
    if not tail or found['hash']:
        return bool(tail)
    if len(tail) <= len(series) and series[-len(tail):] == tail:
        return True
    for folder in folders:
        named = words(folder)
        inside = any(named[i:i + len(tail)] == tail for i in range(len(named) - len(tail) + 1))
        if inside and not set(series) <= set(named):
            return True
    return False


def series_title_parts(title, author=''):
    """Ruling 41 (Sergei 2026-10-27): {'series', 'number', 'title'} when a name reads "Series N. Title" («Крысы 1.
    Крысы», «Профессия: инквизитор 1. Леди не движется», «Колесо времени - 01. Око мира», «Сновидения Ехо #3 - Вся
    правда о нас»), else None. The author written before the series is not part of it ("Робин Хобб - Сага 2. X"); a
    word that only numbers a part ("Книга 1. X") or the author's own name is no series. The number is written as the
    folder structure writes it ("01" is "1", "1,5" is "1.5")."""
    found = _SERIES_PARTS.match(text(title))
    if not found:
        return None
    series = text(_series_name(text(found['series']).rstrip(' ,;-–—#'), author or ''))
    rest = text(found['title'])
    if not series or not rest or not re.search(r'[^\W\d_]', series) or _NOT_A_SERIES.match(series) or _PART_TAIL.search(series) \
            or (author and compare_names(series, author)):
        return None
    # m4: "Apollo 13: The Untold Story" is a title with a number and a subtitle, never series Apollo, book 13, and a code
    # number like «Агент 007» is no position in a series. Neither is split; the odd-name check still asks when it should.
    if found['separator'] == ':' or re.fullmatch(r'00\d', found['number']):
        return None
    return {'series': series, 'number': series_number(found['number']), 'title': rest}


def series_number(value):
    """A position as the folder structure writes it: "01" is "1"; "1,5" and "01.5" are "1.5" (Senua's 0.22.3 review, m4)."""
    value = text(value).replace(',', '.')
    whole, dot, part = value.partition('.')
    if whole.isdigit() and (not dot or part.isdigit()):
        return str(int(whole)) + (dot + part if dot else '')
    return value


# Ruling 46 (Sergei 2026-10-27, "2. Yes. Сновидения Ехо"): series names that are one series, by their key, and the one
# spelling they are filed under. The key folds case, "ё" and punctuation (norm); add a pair when Sergei rules one.
SERIES_SPELLINGS = {'сновиденияэхо': 'Сновидения Ехо', 'сновиденияехо': 'Сновидения Ехо'}


def series_spelling(name):
    """The spelling a series is filed under: Sergei's ruled one, else the name as written."""
    return SERIES_SPELLINGS.get(norm(name), text(name))


def series_key(name):
    """One key per series however it is spelled (ruling 46)."""
    return norm(series_spelling(name))


def sibling_series(row, root, index, author=''):
    """Ruling 45: the series the other book folders under this book's parent folder carry in their albums ("Series N.
    Title"), when at least two of them name it and no other series is named as often, with the numbers they hold in it;
    ('', set()) otherwise. Only a book in one folder that is not directly under the library root; read from the catalog
    index (no file is opened)."""
    albums = (index or {}).get('sibling_albums') or {}
    folders = {str(Path(m['path']).parent) for m in row.get('members', [])}
    if len(folders) != 1:
        return '', set()
    own = next(iter(folders))
    parent = str(Path(own).parent)
    if not root or norm(parent) == norm(str(Path(root))):
        return '', set()
    counts, spellings, numbers = Counter(), {}, {}
    for folder, album in (albums.get(parent) or {}).items():
        if folder == own:
            continue
        parts = series_title_parts(album, author)
        if parts:
            key = series_key(parts['series'])
            counts[key] += 1
            spellings.setdefault(key, Counter())[series_spelling(parts['series'])] += 1
            numbers.setdefault(key, set()).add(parts['number'])
    ranked = counts.most_common(2)
    if not ranked or ranked[0][1] < 2 or len(ranked) > 1 and ranked[1][1] == ranked[0][1]:
        return '', set()
    return spellings[ranked[0][0]].most_common(1)[0][0], numbers[ranked[0][0]]


def _same_number(left, right):
    """The same position in a series, however it is written ("01" and "1", "01.5" and "1.5")."""
    return series_number(left) == series_number(right)


def odd_identity(title, author, local_author='', no_author='', ruled=False, folders=()):
    """{'kind', 'why', 'proposal'?, 'candidates'?} when the title or author the app would file needs Sergei's answer,
    else None. kind is an existing question row: 'title_author' or 'author_unclear'. ruled: a rule chose the author (his
    answer, or the library's own folder for that name), so only the title is checked. folders: the names of the book's
    own folders and their parents, which may name the title without its series."""
    title, author = text(title), text(author)
    if title and re.search(r'[^\W\d_]', _BITRATE_TAIL.sub('', title)) and _BITRATE_TAIL.search(title):
        return {'kind': 'title_author', 'why': 'title_bitrate'}
    if title and _series_in_title(title, folders):
        return {'kind': 'title_author', 'why': 'title_series'}
    if author and author != no_author and not ruled:
        if '_' in author:
            clean = text(local_author) if local_author and '_' not in local_author else text(author.replace('_', ' '))
            # Ruling 33 (Sergei 2026-10-26): a Latin "Given Surname" name is proposed surname first ("Marchenko Ilya").
            return {'kind': 'title_author', 'why': 'author_folder', 'proposal': surname_first(clean)[0]}
        people = _people(author)
        if people:
            return {'kind': 'author_unclear', 'why': 'two_people', 'candidates': people}
    if title and author and _russian_in_latin(title, author):
        return {'kind': 'title_author', 'why': 'title_latin'}
    return None


_LATIN_TO_CYRILLIC = (('shch', 'щ'), ('sch', 'щ'), ('zh', 'ж'), ('kh', 'х'), ('ts', 'ц'), ('ch', 'ч'), ('sh', 'ш'), ('yu', 'ю'), ('ya', 'я'),
                      ('yo', 'ё'), ('ye', 'е'), ('iy', 'ий'), ('yy', 'ый'), ('a', 'а'), ('b', 'б'), ('v', 'в'), ('w', 'в'), ('g', 'г'), ('d', 'д'),
                      ('e', 'е'), ('z', 'з'), ('i', 'и'), ('j', 'й'), ('k', 'к'), ('l', 'л'), ('m', 'м'), ('n', 'н'), ('o', 'о'), ('p', 'п'),
                      ('r', 'р'), ('s', 'с'), ('t', 'т'), ('u', 'у'), ('f', 'ф'), ('h', 'х'), ('c', 'к'), ('q', 'к'), ('x', 'кс'), ('y', 'ы'))
_SLAVIC_CYRILLIC = {'ilya': 'илья', 'ilia': 'илья', 'igor': 'игорь', 'sergey': 'сергей', 'sergei': 'сергей', 'dmitry': 'дмитрий', 'dmitri': 'дмитрий',
                    'dmitriy': 'дмитрий', 'andrey': 'андрей', 'andrei': 'андрей', 'alexey': 'алексей', 'alexei': 'алексей', 'aleksey': 'алексей',
                    'aleksei': 'алексей', 'nikolai': 'николай', 'nikolay': 'николай', 'yuri': 'юрий', 'yuriy': 'юрий', 'yury': 'юрий',
                    'evgeny': 'евгений', 'evgeniy': 'евгений', 'yevgeny': 'евгений', 'vitaly': 'виталий', 'vitaliy': 'виталий', 'vasily': 'василий',
                    'vasiliy': 'василий', 'anatoly': 'анатолий', 'anatoliy': 'анатолий', 'arkady': 'аркадий', 'arkadiy': 'аркадий',
                    'gennady': 'геннадий', 'gennadiy': 'геннадий', 'grigory': 'григорий', 'grigoriy': 'григорий', 'valery': 'валерий',
                    'valeriy': 'валерий', 'vyacheslav': 'вячеслав', 'yegor': 'егор', 'fyodor': 'фёдор', 'semyon': 'семён', 'arseny': 'арсений',
                    'arseniy': 'арсений', 'olga': 'ольга', 'tatyana': 'татьяна', 'tatiana': 'татьяна', 'natalia': 'наталья', 'natalya': 'наталья',
                    'lyudmila': 'людмила', 'ludmila': 'людмила', 'yulia': 'юлия', 'yuliya': 'юлия', 'daria': 'дарья', 'darya': 'дарья',
                    'ksenia': 'ксения', 'kseniya': 'ксения', 'hanna': 'ханна', 'ganna': 'ганна', 'yelena': 'елена', 'yekaterina': 'екатерина',
                    'alyona': 'алёна'}


def cyrillic_spelling(name):
    """A Latin name in Cyrillic letters by the usual Russian romanization read backwards ("Marchenko Ilya" -> «Марченко Илья»).
    A proposal Sergei may correct, never a decision."""
    result = []
    for word in text(name).split():
        low = word.casefold()
        if low in _SLAVIC_CYRILLIC:
            result.append(_SLAVIC_CYRILLIC[low].capitalize())
            continue
        out, at = '', 0
        while at < len(low):
            if not ('a' <= low[at] <= 'z'):
                out += low[at]; at += 1; continue
            for latin, cyrillic in _LATIN_TO_CYRILLIC:
                if low.startswith(latin, at):
                    if latin in ('e', 'ye') and at == 0:
                        cyrillic = 'э' if latin == 'e' else 'е'
                    if latin == 'y' and at == len(low) - 1 and at and low[at - 1] in 'aeiou':
                        cyrillic = 'й'
                    out += cyrillic; at += len(latin); break
            else:
                at += 1
        result.append(out.capitalize())
    return ' '.join(result)


def name_language(name):
    """Ruling 33 (Sergei 2026-10-26): one person, one folder, picked by the language the author writes in. A Latin name
    whose first name is a Russian or other Slavic one ("Ilya Marchenko") may be a Russian author transliterated or a
    writer in another language. The caller asks only when nothing decides it (no catalog language, no folder of the
    person in Audiobooks Sorted, no rule). Returns [Latin surname first, Cyrillic surname first], else []."""
    name = text(name)
    if script(name) != 'latin' or not any(w in SLAVIC_LATIN_GIVEN for w in words(name)) or len(words(name)) < 2:
        return []
    latin = surname_first(name)[0]
    return [latin, cyrillic_spelling(latin)]


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
    for value in record['fields']['title'].get('aliases') or ():
        # Item 9: the translation in the tags of a book the folder names in its original ("Кости волхвов" / "Map of Bones").
        if clean_title(value) and clean_title(value) not in forms:
            forms.append(clean_title(value))
    return forms


def work_id(record):
    title = title_key(record['fields']['title']['value'])
    author = 'collection' if record.get('route') else '|'.join(sorted(words(record['fields']['author']['value'])))
    return 'local:' + hashlib.sha256((title + '\x1f' + author).encode('utf-8')).hexdigest()[:24]


def summary(record):
    """Compact, explainable record stored with the metadata facts."""
    def field(name):
        value = record['fields'][name]
        compact = {'state': value['state'], 'value': value['value'], 'how': value['how'],
                   'sources': [{k: s[k] for k in ('kind', 'field', 'value') if k in s} for s in value['sources'] if s][:4]}
        if value.get('basis'):
            compact['basis'] = value['basis']
        if value.get('rule'):
            compact['rule'] = value['rule']
        return compact
    return {'version': record.get('version', AGREEMENT_VERSION), 'title': field('title'), 'author': field('author'),
            'series': field('series'), 'number': field('number'), 'gaps': list(record['gaps']),
            'ignored': [dict(i) for i in record['ignored']][:6], 'route': dict(record['route']) if record.get('route') else None,
            'part_book': dict(record['part_book']) if record.get('part_book') else None}


def revalidate(row, root, recorded, siblings=None, readers=None, index=None, rules=None):
    """Re-derive agreement (v5: identify()) from the current row; refuse any drift."""
    current = identify(row, root, siblings, readers, index, rules) if recorded.get('version') == IDENTITY_VERSION else agreement(row, root, siblings, readers)
    if recorded.get('route'):
        if not current.get('route') or current['route']['kind'] != recorded['route']['kind'] or current['route']['narrators'] != recorded['route']['narrators'] \
                or current['fields']['title']['value'] != recorded['title']['value'] and recorded['title'].get('state') not in ('entered', 'approved'):
            raise ValueError('Local collection evidence changed')
        return current
    sergei = {name for name in ('title', 'author') if recorded.get(name, {}).get('state') in ('entered', 'approved')}
    if sergei:
        # Rulings 6a/6b: Sergei's values are the identity. They are bound to this book's fingerprint (validate_policy),
        # so only the facts the files still decide are compared.
        for name in ('series', 'number'):
            if current['fields'][name]['state'] != recorded[name]['state'] or current['fields'][name]['value'] != recorded[name]['value']:
                raise ValueError('Local identity evidence changed')
        return current
    if (current.get('part_book') or None) != (recorded.get('part_book') or None):
        raise ValueError('Local identity evidence changed')
    if not current['accepted']:
        raise ValueError('Local identity evidence no longer agrees')
    for name in ('title', 'author', 'series', 'number'):
        if current['fields'][name]['state'] != recorded[name]['state'] or current['fields'][name]['value'] != recorded[name]['value']:
            raise ValueError('Local identity evidence changed')
    return current
