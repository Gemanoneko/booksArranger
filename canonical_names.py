"""0.30.0 items 5 and 6 (Sergei 2026-11-18, backlog "Why books aren't sorted — library-wide"): one author folder per author
and series names in the original language. Pure: Sergei's author rules (author_rules.Rules) and a FantLab cycle record are
passed in; nothing is fetched, nothing is written.

Item 5, one author folder per author, in the Latin, surname-first form the library already uses ("Rowling J. K"),
whatever source or script answered. Two names are the same author only when (conservative: a wrong merge is worse than a
split):
  1. one of Sergei's rules (or a rule research learned) files the credit under the other name: «Роулинг Джоан» and
     «Джоан Роулинг» are ruled "Rowling J. K" (same_as), followed to its end; a rule scoped to a folder counts for a book
     in that folder (the book's own folder is passed in);
  2. or both are written with exactly the same full words (in any order) and the same initials in the same order, case,
     punctuation and ё/е aside: "J. K. Rowling" and "Rowling J. K." are one name, so are "Tove Jansson" and "Jansson
     Tove". Since Senua's 0.30.0 review (m2) the initials' order counts: "K. J. Parker" and "Parker J. K." are two people
     (every word, initials too, used to be compared sorted).
Nothing else merges: never an initial against a full first name ("J. K. Rowling" / "Joanne Rowling"), never initials in
another order, never a name in another script without a rule (never a transliteration, ruling 39), never a surname alone,
never two credits of a book. A credit Sergei kept (a keep rule) stays exactly as it is spelled. Among several spellings of
one name the one the library already files under wins (rules' known authors), else the surname-first order of the name
(local_identity.surname_first, ruling 3).

Item 6, the series name in the language the work was written in: a FantLab cycle of a work not written in Russian is
named by its original name in Latin letters ("Гарри Поттер" -> "Harry Potter", "Муми-тролли" -> "Mumintrollen"). A
cycle written in Russian, one with no original name, or an original name in another script keeps its Russian name.
A series Sergei entered, a Goodreads series (already written as published) or one a folder names is never renamed."""
import base64
import hashlib
import json
import re


def _people(name):
    return [part for part in re.split(r'\s*;\s*', str(name or '')) if part.strip()]


def _order_key(name):
    """The name's full words in any order and its initials in their own order, case, punctuation and ё/е aside: "J. K.
    Rowling" and "Rowling J. K." -> (rowling; j k); "Tove Jansson" and "Jansson Tove" -> (jansson tove); "K. J. Parker" ->
    (parker; k j), never "Parker J. K." (parker; j k)."""
    import unicodedata
    import local_identity
    found = local_identity.words(unicodedata.normalize('NFC', local_identity.text(name)))
    return ' '.join(sorted(word for word in found if len(word) > 1)) + ';' + ' '.join(word for word in found if len(word) == 1)


def author(name, rules=None, folder=''):
    """(the name the author's folder uses, why or ''). name: one credit ("A; B" credits are left as they are). folder: the
    book's own folder path, for a rule Sergei scoped to a folder."""
    import local_identity
    value = local_identity.text(name)
    if not value or len(_people(value)) != 1:
        return value, ''
    why = ''
    rule = rules.rule(value, folder) if rules is not None else None
    if rule and rule['kind'] != 'same_as':
        return value, ('your rule keeps this spelling' if rule['kind'] == 'keep' else '')  # m2: kept (or no author) stays as it is
    ruled = rules.same_as(value, folder) if rules is not None else ''
    if ruled and ruled != value:
        value, why = local_identity.text(ruled), 'your rule files this name under "%s"' % ruled
    if local_identity.script(value) != 'latin':
        return value, why
    filed = _filed(value, rules)
    if filed:
        return filed, why or ('' if filed == value else 'the folder the library already files this author under (same name, surname first)')
    chosen = _surname_first(value)
    if chosen != value:
        return chosen, why or 'surname first'
    return value, why


_INITIAL = re.compile(r'[^\W\d_]\.?')


def _surname_first(value):
    """local_identity.surname_first (ruling 3) for a name that is not already written surname first: a name ending in
    initials ("Rowling J. K", "Tolkien J. R. R.") is surname first already and never turned around again."""
    import local_identity
    tokens = value.split()
    if len(tokens) >= 2 and _INITIAL.fullmatch(tokens[-1]) and not _INITIAL.fullmatch(tokens[0]):
        return value
    chosen, order = local_identity.surname_first(value)
    return chosen if order.startswith('surname first') else value


def _filed(value, rules):
    """The library's own spelling of exactly this name (same words in the same order, surname first), with the most books;
    '' if none."""
    import local_identity
    if rules is None:
        return ''
    wanted = _order_key(value)
    # 0.31.0 step 3: the name a rule in force files a credit under is the author's folder, whatever other order of the
    # same words finished books still sit under (the learned "Cixin Liu", corrected to "Liu Cixin": the corrected rule
    # decides, and the finished books follow it when they are moved).
    targets = {local_identity.text(row.get('target')).casefold() for row in getattr(rules, 'rules', []) or []
               if isinstance(row, dict) and row.get('kind') == 'same_as' and row.get('target')}
    found = []
    for spelling, count in getattr(rules, 'known_authors', {}).values():
        if spelling and local_identity.script(spelling) == 'latin' and _order_key(spelling) == wanted:
            found.append((spelling.casefold() in targets, _surname_first(spelling) == spelling, count, spelling))
    if not found:
        return ''
    return sorted(found, key=lambda item: (not item[0], not item[1], -item[2], item[3]))[0][3]


def same_author(a, b, rules=None, folder=''):
    """Item 5's rule: True only when a rule or the very same words make a and b one author (see the module text)."""
    if not a or not b:
        return False
    first, second = author(a, rules, folder)[0], author(b, rules, folder)[0]
    return _order_key(first) == _order_key(second)


def folder_key(name):
    """The author folder a credit gives (metadata.safe_name, as organization.plan files it), casefolded."""
    from metadata import safe_name
    return safe_name(name).casefold()


# ------------------------------------------------------------------ item 6
FANTLAB_CYCLE = re.compile(r'https://fantlab\.ru/work([1-9]\d{0,9})')


def series_original(record):
    """The original-language name of a FantLab cycle (its /work/<id>/extended record) of a work not written in Russian, in
    Latin letters; '' when the Russian name stays (written in Russian, no original name, another script)."""
    import local_identity
    if not isinstance(record, dict):
        return ''
    original = local_identity.text(record.get('work_name_orig'))
    language = {'jp': 'ja'}.get(local_identity.text(record.get('lang_code')), local_identity.text(record.get('lang_code')))
    if original and language and language != 'ru' and re.fullmatch('[a-z]{2,3}', language) and local_identity.script(original) == 'latin':
        return original
    return ''


def cycle_api(source_url):
    """The FantLab API URL of a cycle cited as https://fantlab.ru/work<id> (research's series receipt), else ''."""
    match = FANTLAB_CYCLE.fullmatch(str(source_url or ''))
    return 'https://api.fantlab.ru/work/' + match[1] + '/extended' if match else ''


def cached_record(db, url):
    """A research-cache answer (public_research_cache) as JSON, only when its bytes still hash to the recorded SHA-256; None
    otherwise. Read only: any age (the record is the receipt research used), no request."""
    if not url:
        return None
    try:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='public_research_cache'").fetchone():
            return None
        row = db.execute('SELECT raw,sha256 FROM public_research_cache WHERE url=?', (url,)).fetchone()
    except Exception:
        return None
    if not row:
        return None
    try:
        raw = base64.b64decode(row[0], validate=True)
        if hashlib.sha256(raw).hexdigest() != row[1]:
            return None
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def series_in_original(db, name, provider, source_url):
    """Item 6 for a series already filed: (name in the original language, why) from the cached FantLab cycle research cited,
    else (name, ''). Only a FantLab answer is renamed (an entered, Goodreads or folder series stays as it is)."""
    import local_identity
    if provider != 'fantlab':
        return name, ''
    record = cached_record(db, cycle_api(source_url))
    if not record or local_identity.series_key(local_identity.text(record.get('work_name'))) != local_identity.series_key(name):
        return name, ''  # not the cycle the series was filed from: nothing is renamed
    original = series_original(record)
    if original and local_identity.text(original) != local_identity.text(name) and local_identity.script(name) != 'latin':
        return original, 'the series in the language it was written in (FantLab: %s)' % source_url
    return name, ''


# ------------------------------------------------------------------ 0.31.0 step 3: one title rule (R1, R3)
TITLE_RULES = ('his', 'russian_original', 'english', 'no_english_title', 'unknown_language')


def book_title(title, catalog=None, his=False):
    """THE title rule (Sergei 2026-11-22, rulings R1 and R3; Brief "Confirmed rules"): (the title a book is filed under,
    which rule decided, one of TITLE_RULES).

      his               a title Sergei typed, entered or approved is his answer and is never replaced
      russian_original  written in Russian: the Russian title (the catalog's own Russian name of the work, else the files')
      english           any other original language: the English title, from whichever source has it (FantLab, Wikidata)
      no_english_title  not written in Russian and no English title found: the title in the files, and nobody is asked (R3)
      unknown_language  no source says what language it was written in: the title in the files, as before

    title: the title the files give. catalog: what a source says of the work, {'language', 'english_title',
    'original_title', 'title_native'} (public_research's catalog record, a gap_fill ledger's 'catalog', or None). Until
    0.31.0 only an English original got its English title: a book translated from Chinese, Polish or Japanese kept its
    Russian title (Sergei's «Тёмный лес»)."""
    import local_identity
    title = local_identity.text(title)
    catalog = catalog if isinstance(catalog, dict) else {}
    language = local_identity.text(catalog.get('language'))
    if his:
        return title, 'his'
    if not language:
        return title, 'unknown_language'
    if language == 'ru':
        return local_identity.text(catalog.get('title_native')) or title, 'russian_original'
    english = local_identity.text(catalog.get('english_title')) or (local_identity.text(catalog.get('original_title')) if language == 'en' else '')
    if english and local_identity.script(english) == 'latin':
        return english, 'english'
    return title, 'no_english_title'


def series_name(found, language='', english=''):
    """The same rule for the name of a series a source found (R1: "its series folder is named in English"; it replaces
    0.30.0 item 6 for originals not written in Latin letters): (name, which rule decided).

      written in Russian           the source's Russian name
      any other original language  the English name: `english` (another source in hand names the same series in English,
                                   Wikidata's label), else the source's own English name, else the name it has in Latin
                                   letters (0.30.0 item 6: the original-language name), else the name as the source gives it
      language unknown             the name as the source gives it (0.30.0 item 6 decided it from FantLab's own cycle)

    found: a series candidate ({'name', 'name_english'?, 'name_russian'?}). A series Sergei typed, one his folders name
    or one the files' tags name never comes here: it is never renamed."""
    import local_identity
    name = local_identity.text((found or {}).get('name'))
    language = local_identity.text(language)
    if language == 'ru':
        return local_identity.text((found or {}).get('name_russian')) or name, 'russian_original'
    if language:
        for value in (english, (found or {}).get('name_english')):
            value = local_identity.text(value)
            if value and local_identity.script(value) == 'latin':
                return value, 'english'
        return name, 'english' if local_identity.script(name) == 'latin' else 'no_english_name'
    return name, 'unknown_language'


# ------------------------------------------------------------------ 0.31.0 step 3: the order of a Latin author name
ORDER_UNKNOWN = 'kept as the source writes it (the order could not be established)'


def latin_order(name, credit='', evidence=None):
    """(the Latin name with the surname first, why) for the Latin spelling a source gives an author (rulings 3, 33, 39).
    A name is turned around only on evidence, in this order; with none it stays exactly as the source writes it:

      1. the source's own family-name field (Wikidata P734): evidence['family'] is the first or the last word(s);
      2. a first name or initial the app knows shows where the surname is (local_identity.surname_first);
      3. a Chinese name (evidence['language'] 'zh'): the sources write the family name first, so it stays as written;
      4. the credit in the files shows it: one Latin word is the credit's surname in the other alphabet («Лев Гроссман»
         -> "Grossman Lev"; «Лю Цысинь» is surname first, so "Liu Cixin" stays).

    Until 0.31.0 a two-word name whose order the app did not know was turned around whenever the Cyrillic credit's order
    was known, whichever way that was: "Liu Cixin" became "Cixin Liu" (Sergei 2026-11-22)."""
    import local_identity
    value = local_identity.text(name)
    tokens = value.split()
    evidence = evidence if isinstance(evidence, dict) else {}
    if len(tokens) < 2 or len(_people(value)) != 1 or local_identity.PEOPLE_SEPARATOR.search(value):
        return value, 'kept as written (one word or several people)'
    family = local_identity.text(evidence.get('family')).split()
    if family and len(family) < len(tokens):
        low, wanted = [token.casefold() for token in tokens], [token.casefold() for token in family]
        if low[:len(wanted)] == wanted:
            return value, 'already surname first (the source names "%s" as the family name)' % ' '.join(family)
        if low[-len(wanted):] == wanted:
            return ' '.join(tokens[-len(wanted):] + tokens[:-len(wanted)]), 'surname first (the source names "%s" as the family name)' % ' '.join(family)
    if _INITIAL.fullmatch(tokens[-1]) and not _INITIAL.fullmatch(tokens[0]):
        return value, 'already surname first'
    chosen, why = local_identity.surname_first(value)
    if why.startswith('surname first') or why == 'already surname first':
        return chosen, why
    if local_identity.text(evidence.get('language')) in ('zh', 'cn'):
        return value, 'kept as the source writes it (a Chinese name: the family name comes first)'
    shown = local_identity.text(credit).split()
    if len(tokens) == 2 and len(shown) == 2 and local_identity.script(credit) != 'latin':
        ordered, order = local_identity.surname_first(credit)
        if not order.startswith('kept as written'):
            surname = local_identity.words(ordered.split()[0])
            hits = [token for token in tokens if surname and local_identity.words(token) and local_identity._pair(local_identity.words(token)[0], surname[0]) == 'cross']
            if len(hits) == 1:
                other = next(token for token in tokens if token is not hits[0])
                return hits[0] + ' ' + other, 'surname first (the credit "%s" in the files shows which word is the surname)' % local_identity.text(credit)
    return value, ORDER_UNKNOWN
