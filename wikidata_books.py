"""0.31.0 step 2 (Sergei 2026-11-22, rulings R1, R2 and R5): Wikidata as a working source for a book's English title,
original language, original title, the author's English name and its series with the number.

Until 0.31.0 Wikidata was asked and supplied 0 of 151 series: the series adapter wanted a referenced statement and took
the first five search hits by title, and the English label it read was dropped. Makoto's tested findings
(Team/Research/BooksArranger_WikidataSeriesSource_2026-11-22.md in the studio repo) are what this module follows:

  - a match needs the title AND the author AND "is a written work", never the title alone: the first search hit was the
    right book 17 times in 28, type and author checked together were right 26 times in 26 (films, TV series, games,
    paintings, towns and other authors' novels share the Russian label);
  - an edition or translation item (P629) is not the work and carries no series;
  - the original language is P407 (P364 is empty on books); its values vary ("English", "American English", two at once);
  - the English name may sit only under the label "mul" (all languages): Douglas Adams, the Harry Potter series;
  - P1476 holds many titles; the original one is the one whose language tag is the work's language;
  - a book may carry two series statements (Discworld 8 and City Watch 1), or point at a fictional universe in place of a
    series (Metro 2033 universe): both are doubtful shapes (series_certainty), never filed.

Pure: the three answers of the look-up (the search, the candidates, the entities they point to) are passed in; nothing is
fetched here. public_research asks through its client (cache, per-site bounds, pauses)."""
import re
import urllib.parse

API = 'https://www.wikidata.org/w/api.php?'
LANGUAGES = 'ru|en|mul'
SEARCH_LIMIT = 10      # the right book was up to sixth in the search (Makoto, row 15)
RELATED_LIMIT = 50     # wbgetentities takes 50 ids a call
# The types of a written work, by the type item's English label (the type items are fetched with the authors, so a label
# is in hand; ids alone would miss every subtype: "science fiction novel", "dystopian novel", "children's book").
WORK_TYPES = {'Q7725634', 'Q8261', 'Q571', 'Q47461344', 'Q49084', 'Q149537'}  # literary work, novel, book, written work, short story, novella
WORK_LABELS = {'literary work', 'written work', 'novel', 'novella', 'novelette', 'short story', 'book', 'short novel', 'fairy tale',
               'poem', 'play', 'non-fiction work', 'creative work', 'short story collection', 'graphic novel', 'light novel',
               'web novel', 'serial novel', 'epic poem', 'novel in verse', 'memoir', 'autobiography', 'essay'}
WORK_TAILS = (' novel', ' novella', ' novelette', ' short story', ' book', ' literary work', ' tale', ' fiction')
NOT_WORK_WORDS = ('series', 'trilogy', 'tetralogy', 'pentalogy', 'cycle', 'saga', 'film', 'comic', 'audio', 'edition', 'translation',
                  'television', 'video', 'game', 'franchise', 'universe', 'award', 'publisher', 'magazine')
# A series item that is no narrative series of books.
UNIVERSE_WORDS = ('universe', 'franchise', 'fictional', 'setting')
UNIVERSE_TYPES = {'Q559618', 'Q196600'}  # fictional universe, media franchise (Metro 2034 points at "Metro 2033 universe")
EDITORIAL_TYPES = {'Q20655472'}  # an editorial collection (a publisher's book series) names no reading order
# ISO 639-3 codes of the languages P407 names without a two-letter code of their own.
LANGUAGE_3 = {'eng': 'en', 'rus': 'ru', 'cmn': 'zh', 'zho': 'zh', 'jpn': 'ja', 'pol': 'pl', 'fra': 'fr', 'deu': 'de', 'spa': 'es', 'ita': 'it',
              'swe': 'sv', 'nor': 'no', 'nob': 'no', 'nno': 'no', 'dan': 'da', 'fin': 'fi', 'ukr': 'uk', 'ces': 'cs', 'kor': 'ko', 'por': 'pt', 'nld': 'nl'}


def search_url(title):
    """The label and alias prefix search in the title's own language (it takes no author; the author is checked after)."""
    language = 'ru' if re.search('[А-Яа-яЁё]', str(title)) else 'en'
    return API + urllib.parse.urlencode({'action': 'wbsearchentities', 'search': str(title), 'language': language, 'uselang': language,
                                         'type': 'item', 'limit': SEARCH_LIMIT, 'format': 'json', 'maxlag': 5})


def entities_url(ids):
    """Labels in Russian, English and "mul" (the trap: an English name stored once for all languages has no "en" label)."""
    return API + urllib.parse.urlencode({'action': 'wbgetentities', 'ids': '|'.join(ids), 'props': 'labels|aliases|claims|info',
                                         'languages': LANGUAGES, 'format': 'json', 'maxlag': 5})


def item(value):
    return value if isinstance(value, str) and re.fullmatch(r'Q[1-9][0-9]{0,11}', value) else None


def search_ids(data):
    hits = data.get('search') if isinstance(data, dict) else None
    if not isinstance(hits, list):
        raise ValueError('Malformed Wikidata search answer')
    return list(dict.fromkeys(hit['id'] for hit in hits[:SEARCH_LIMIT] if isinstance(hit, dict) and item(hit.get('id'))))


def entities(data, wanted):
    records = data.get('entities') if isinstance(data, dict) else None
    if not isinstance(records, dict):
        raise ValueError('Malformed Wikidata entities answer')
    # In the order asked for (the search's own order), whatever order the answer lists them in: the items they point
    # to are then asked for in one order too, so the same book always makes the same request (one cache entry).
    return {key: records[key] for key in wanted if isinstance(records.get(key), dict) and records[key].get('id') == key
            and all(isinstance(records[key].get(part, {}), dict) for part in ('labels', 'aliases', 'claims'))}


def label(entity, *languages):
    """The first label there is among these languages ('' for none)."""
    labels = entity.get('labels') if isinstance(entity, dict) and isinstance(entity.get('labels'), dict) else {}
    for language in languages:
        value = labels.get(language)
        if isinstance(value, dict) and isinstance(value.get('value'), str) and value['value'].strip():
            return value['value'].strip()
    return ''


def _latin(value):
    return bool(value) and not re.search('[А-Яа-яЁё぀-ヿ㐀-鿿가-힯]', value) and bool(re.search('[A-Za-z]', value))


def english(entity):
    """The English name: the "en" label, else the "mul" label when it is in Latin letters."""
    value = label(entity, 'en')
    if value:
        return value
    value = label(entity, 'mul')
    return value if _latin(value) else ''


def _statements(entity, prop):
    claims = entity.get('claims') if isinstance(entity, dict) and isinstance(entity.get('claims'), dict) else {}
    values = claims.get(prop)
    if not isinstance(values, list):
        return []
    return [claim for claim in values[:60] if isinstance(claim, dict) and claim.get('rank') != 'deprecated'
            and isinstance(claim.get('mainsnak'), dict) and claim['mainsnak'].get('snaktype') == 'value']


def _value(claim):
    data = claim['mainsnak'].get('datavalue')
    return data.get('value') if isinstance(data, dict) else None


def ids(entity, prop):
    """The items a property names. Qualifiers on the statement are ignored: an author's "stated as" or ordinal does not make
    the author doubtful (the old adapter raised a conflict on them, which held six finished books for review)."""
    found = []
    for claim in _statements(entity, prop):
        value = _value(claim)
        key = item(value.get('id')) if isinstance(value, dict) else None
        if key and key not in found:
            found.append(key)
    return found


def texts(entity, prop):
    """[(text, language)] of a monolingual-text property (P1476, the titles)."""
    found = []
    for claim in _statements(entity, prop):
        value = _value(claim)
        if isinstance(value, dict) and isinstance(value.get('text'), str) and value['text'].strip():
            found.append((value['text'].strip(), str(value.get('language') or '')))
    return found


def strings(entity, prop):
    return [value.strip() for value in (_value(claim) for claim in _statements(entity, prop)) if isinstance(value, str) and value.strip()]


def names(entity):
    """Every name the search may have matched: the labels and aliases in Russian, English and "mul", and the titles."""
    found = []
    for language in ('ru', 'en', 'mul'):
        value = label(entity, language)
        if value:
            found.append(value)
        aliases = (entity.get('aliases') or {}).get(language) if isinstance(entity.get('aliases'), dict) else None
        if isinstance(aliases, list):
            found.extend(alias['value'].strip() for alias in aliases[:30] if isinstance(alias, dict) and isinstance(alias.get('value'), str) and alias['value'].strip())
    found.extend(value for value, _ in texts(entity, 'P1476'))
    return list(dict.fromkeys(value for value in found if value and len(value) <= 500))


def related_ids(works):
    """The items the candidates point to that the match reads: authors, series, languages and types."""
    found = []
    for work in works:
        for prop in ('P50', 'P179', 'P407', 'P31'):
            for key in ids(work, prop):
                if key not in found:
                    found.append(key)
    return found[:RELATED_LIMIT]


def written_work(entity, related):
    """True when one of the item's types is a written work (by the type's English name) and it is no edition (P629)."""
    if ids(entity, 'P629'):
        return False
    for key in ids(entity, 'P31'):
        if key in WORK_TYPES:
            return True
        name = english(related.get(key) or {}).casefold()
        if not name or any(word in name for word in NOT_WORK_WORDS):
            continue
        if name in WORK_LABELS or name.endswith(WORK_TAILS):
            return True
    return False


def language_code(entity, related):
    """The work's language as a two- or three-letter code, '' when Wikidata names none or names two different ones.
    "American English" and "British English" are English, "Standard Chinese" and "Mandarin" are Chinese."""
    codes = set()
    for key in ids(entity, 'P407'):
        language = related.get(key) or {}
        code = next(iter(strings(language, 'P218')), '')
        if not code:
            tag = next(iter(strings(language, 'P305')), '')
            code = tag.split('-')[0].casefold() if tag else ''
        if not code:
            code = LANGUAGE_3.get(next(iter(strings(language, 'P220')), '').casefold(), '')
        if not code:
            name = english(language).casefold()
            code = next((value for word, value in (('english', 'en'), ('russian', 'ru'), ('chinese', 'zh'), ('mandarin', 'zh'), ('japanese', 'ja'))
                         if word in name), '')
        code = LANGUAGE_3.get(code, code)
        if not re.fullmatch('[a-z]{2,3}', code or ''):
            return ''
        codes.add(code)
    return codes.pop() if len(codes) == 1 else ''


def _original_title(entity, code):
    if not code:
        return ''
    found = list(dict.fromkeys(value for value, language in texts(entity, 'P1476') if language.casefold().split('-')[0] == code))
    return found[0] if len(found) == 1 else ''


def series_statements(entity, related):
    """Each "part of the series" statement of the work that names a series of books: {'id', 'ordinal' ('' for none),
    'kind' ('series' or 'universe'), 'name_en', 'name_ru', 'statement_id', 'revision'}. An editorial collection (a
    publisher's book series) is left out: it names no reading order."""
    found = []
    for claim in _statements(entity, 'P179'):
        value = _value(claim)
        key = item(value.get('id')) if isinstance(value, dict) else None
        if not key:
            continue
        series = related.get(key) or {}
        kinds = ids(series, 'P31')
        if EDITORIAL_TYPES.intersection(kinds):
            continue
        # A universe in place of a series: by the series item's own types, else by its types' names, else by its own name.
        labels = [name for name in (english(related.get(kind) or {}).casefold() for kind in kinds) if name]
        own = (english(series) + ' ' + label(series, 'ru')).casefold()
        universe = bool(UNIVERSE_TYPES.intersection(kinds)) or bool(labels) and all(any(word in name for word in UNIVERSE_WORDS) for name in labels) \
            or (not kinds and any(word in own for word in ('universe', 'franchise', 'вселенная')))
        qualifiers = claim.get('qualifiers') if isinstance(claim.get('qualifiers'), dict) else {}
        ordinals = [snak.get('datavalue', {}).get('value') for snak in qualifiers.get('P1545') or []
                    if isinstance(snak, dict) and snak.get('snaktype') == 'value' and isinstance(snak.get('datavalue'), dict)]
        ordinal = ordinals[0].strip() if len(ordinals) == 1 and isinstance(ordinals[0], str) else ''
        found.append({'id': key, 'ordinal': ordinal if re.fullmatch(r'[1-9]\d{0,3}', ordinal) else '', 'ordinal_as_written': ordinal,
                      'kind': 'universe' if universe else 'series', 'name_en': english(series), 'name_ru': label(series, 'ru'),
                      'statement_id': claim.get('id') if isinstance(claim.get('id'), str) else '',
                      'revision': series.get('lastrevid') if type(series.get('lastrevid')) is int else None})
    return found


def book(candidates, related, title, author, title_key, same_person, people, partial=False):
    """The one written work among the search's candidates whose name is this title and whose authors include every person
    the files credit, or None. {'conflict': why} when two different works fit (never a guess between them).

    candidates, related: {id: entity}; title_key: local_identity.title_key; same_person(local name, other name, partial);
    people(author) -> the credited people. partial: the files give a surname only.
    The record: {'work_id', 'source_url', 'revision', 'language', 'english_title', 'original_title', 'title_ru', 'authors':
    [{'id', 'name_en', 'name_ru'}], 'author_count' (the work's own), 'series': series_statements()}."""
    wanted = title_key(title)
    local = people(author)
    if not wanted or not local:
        return None
    matches = []
    for entity in candidates.values():
        if wanted not in {title_key(name) for name in names(entity)}:
            continue
        if not written_work(entity, related):
            continue
        credited = [(key, related.get(key) or {}) for key in ids(entity, 'P50')]
        used, matched = set(), []
        for person in local:
            hit = next((key for key, record in credited if key not in used and any(same_person(person, name, partial) for name in names(record))), None)
            if hit is None:
                break
            used.add(hit)
            matched.append(hit)
        if len(matched) != len(local):
            continue
        matches.append((entity, matched, len(credited)))
    if not matches:
        return None
    if len(matches) > 1:
        return {'conflict': 'Wikidata holds %d written works with this title by this author' % len(matches)}
    entity, matched, count = matches[0]
    code = language_code(entity, related)
    title_en = english(entity) or next((value for value, language in texts(entity, 'P1476') if language.casefold().split('-')[0] == 'en'), '')
    original = _original_title(entity, code) or (title_en if code == 'en' else label(entity, 'ru') if code == 'ru' else '')
    return {'work_id': entity['id'], 'source_url': 'https://www.wikidata.org/wiki/' + entity['id'],
            'revision': entity.get('lastrevid') if type(entity.get('lastrevid')) is int else None,
            'language': code, 'english_title': title_en if _latin(title_en) else '', 'original_title': original, 'title_ru': label(entity, 'ru'),
            'authors': [{'id': key, 'name_en': english(related.get(key) or {}), 'name_ru': label(related.get(key) or {}, 'ru'),
                         'family_ids': ids(related.get(key) or {}, 'P734'), 'given_ids': ids(related.get(key) or {}, 'P735')} for key in matched],
            'author_count': count, 'series': series_statements(entity, related)}


def series(record):
    """The series candidate of a matched work for series_certainty.judge, or None when the work is in no series. The name
    follows ruling R1: English unless the work was written in Russian. 'doubt' is set for the doubtful shapes Wikidata
    itself shows: more than one series on the book, or a universe in place of a series."""
    statements = record.get('series') or []
    if not statements:
        return None
    base = {'provider': 'wikidata', 'source_url': record['source_url'], 'work_id': record['work_id'], 'work_revision': record.get('revision')}
    if len(statements) > 1:
        return dict(base, name='; '.join(s['name_en'] or s['name_ru'] for s in statements)[:300], number='', doubt='several_series',
                    series_ids=[s['id'] for s in statements])
    only = statements[0]
    russian = record.get('language') == 'ru'
    name = (only['name_ru'] or only['name_en']) if russian else (only['name_en'] or only['name_ru'])
    found = dict(base, name=name, number=only['ordinal'], number_from='source' if only['ordinal'] else '', series_id=only['id'],
                 statement_id=only['statement_id'], series_revision=only['revision'], numbering_scheme='Wikidata series statement with its ordinal',
                 name_english=only['name_en'], name_russian=only['name_ru'])
    if only['kind'] == 'universe':
        found['doubt'] = 'universe'
    elif not name:
        found['doubt'] = 'no_name'
    return found


def name_order(author, name_items):
    """The author's family name and given name as Wikidata's own structured fields give them (P734, P735): {'family',
    'given'} in English ('' where the person has none). name_items: {id: entity} of the name items."""
    def first(keys):
        return next((english(name_items.get(key) or {}) for key in keys if english(name_items.get(key) or {})), '')
    return {'family': first(author.get('family_ids') or []), 'given': first(author.get('given_ids') or [])}
