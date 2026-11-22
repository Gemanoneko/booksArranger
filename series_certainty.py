"""0.31.0, rulings R18, R21 and R22 (Sergei 2026-11-22): the one place that decides whether a series a source found for a
book is certain or doubtful. A doubtful series is treated as not found: no question, no hold, the book goes on without it.

Certain: the source matched the book's title and every credited author (the adapters return nothing otherwise), it names
exactly one series, and nothing the book's own files say contradicts it. The number may come from the source, from the
book's own tags or names ("Series 3. Title", «Летопись первая»), or be counted by the app from FantLab's cycle order (R21:
a series found by FantLab alone with a counted number is good enough to file).

Doubtful (WHY, the keys the page may word; each is recorded with the book so it can say a doubtful series was dropped):
  several_series     the source puts the book in more than one series (Discworld 8 and City Watch 1)
  universe           the source names a fictional universe or a setting in place of a series (Metro 2033 universe)
  no_number          a series is named and no number is known from the source, the book's own names or its tags
  number_mismatch    the source's number is not the number the book's own title or tags give
  contradicts_local  the files name another series, or another number in the same series
  source_conflict    the source contradicts itself (two works fit, two different numbers)
  sources_disagree   two sources in hand give the book different numbers (which source wins is not ruled)
  unconfirmed_name   the title only looks like "Series N. Title" and no source confirms that series

Callers: public_research (the look-up before review, Approve's preview, the series look-up of finished books through
PublicResearch.series_verdict). Nothing else may decide this; a new doubtful shape is added here."""
import re

CERTAIN, DOUBTFUL = 'certain', 'doubtful'
WHY = ('several_series', 'universe', 'no_number', 'number_mismatch', 'contradicts_local', 'source_conflict', 'sources_disagree',
       'unconfirmed_name', 'no_name')
NUMBER_FROM = ('source', 'counted', 'names', 'tags')  # where a certain series' number came from


def _text(value):
    return ' '.join(str(value or '').split())


def _number(value):
    """A position as the folder structure writes it ("01" is "1", "1,5" is "1.5"); '' for none."""
    value = _text(value).replace(',', '.')
    if not re.fullmatch(r'\d{1,4}(?:\.\d{1,3})?', value):
        return ''
    whole, _, part = value.partition('.')
    part = part.rstrip('0')
    return str(int(whole)) + ('.' + part if part else '')


def same_number(left, right):
    return bool(_number(left)) and _number(left) == _number(right)


def _words(name):
    return re.findall(r'[^\W_]+', _text(name).casefold().replace('ё', 'е'))


def _script(name):
    value = _text(name)
    if re.search('[А-Яа-яЁё]', value):
        return 'cyrillic'
    return 'latin' if re.search('[A-Za-z]', value) else ''


def names_agree(left, right):
    """True when two series names may be one series: written in different alphabets (not comparable, so no contradiction),
    the same words, or one name's words all inside the other's ("Sprawl" and "Sprawl trilogy"; small words aside)."""
    a, b = _words(left), _words(right)
    if not a or not b or _script(left) != _script(right):
        return True
    small = {'the', 'a', 'an', 'of', 'series', 'trilogy', 'saga', 'cycle', 'цикл', 'серия', 'сага', 'трилогия'}
    a, b = [word for word in a if word not in small] or a, [word for word in b if word not in small] or b
    return set(a) <= set(b) or set(b) <= set(a)


def judge(candidate, local=None, others=()):
    """{'verdict': CERTAIN or DOUBTFUL, 'why': '' or one of WHY, 'series': the series to file (name, number, provider,
    source_url and the adapter's own proof keys) or None, 'number_from': one of NUMBER_FROM or ''}.

    candidate: what an adapter found: {'name', 'number' ('' when the source gives none), 'provider', 'source_url', 'doubt'?
      (the source's own doubtful shape), 'number_from'? ('source', or 'counted' for FantLab's cycle order)}.
    local: what the book's own files say, never overruled by a source:
      'series', 'number'  a series the files name (tags, his folders, what he entered)
      'volume'            the number the book's own title gives («Летопись первая» -> 1), or None
      'hint'              {'series', 'number'}: a name that only looks like "Series N. Title" (nothing confirms it)
    others: certain series of other sources in hand for the same book."""
    local = local or {}
    series = {key: value for key, value in (candidate or {}).items() if key not in ('doubt',)}

    def doubtful(why):
        return {'verdict': DOUBTFUL, 'why': why, 'series': None, 'number_from': '',
                'found': {'provider': _text(series.get('provider')), 'name': _text(series.get('name')), 'number': _text(series.get('number')),
                          'source_url': _text(series.get('source_url'))}}
    if not candidate:
        return doubtful('no_name')
    if candidate.get('doubt'):
        return doubtful(candidate['doubt'] if candidate['doubt'] in WHY else 'source_conflict')
    name = _text(candidate.get('name'))
    if not name:
        return doubtful('no_name')
    hint = local.get('hint') if isinstance(local.get('hint'), dict) else {}
    volume = local.get('volume')
    number, origin = _number(candidate.get('number')), candidate.get('number_from') or 'source'
    if not number:
        # The source names the series and no number: the book's own names or tags may give it (ruling R21's wording).
        for value, where in ((volume, 'names'), (hint.get('number'), 'names'), (local.get('number'), 'tags')):
            if value is not None and _number(value):
                number, origin = _number(value), where
                break
        if not number:
            return doubtful('no_number')
    if volume is not None and _number(volume) and not same_number(number, volume):
        return doubtful('number_mismatch')
    if hint.get('number') and not same_number(number, hint['number']):
        return doubtful('number_mismatch')
    if hint.get('series') and not names_agree(name, hint['series']):
        return doubtful('contradicts_local')
    if local.get('series'):
        if not names_agree(name, local['series']) or local.get('number') and not same_number(number, local['number']):
            return doubtful('contradicts_local')
    elif local.get('number') and not same_number(number, local['number']):
        return doubtful('contradicts_local')
    for other in others or ():
        if isinstance(other, dict) and _number(other.get('number')) and not same_number(number, other['number']):
            return doubtful('sources_disagree')
    series.update(name=name, number=number)
    series['number_from'] = origin if origin in NUMBER_FROM else 'source'
    return {'verdict': CERTAIN, 'why': '', 'series': series, 'number_from': series['number_from']}


def dropped(verdict):
    """The record kept with a book for a doubtful series that was dropped: {'provider', 'name', 'number', 'why', 'source_url'}."""
    found = dict(verdict.get('found') or {})
    found['why'] = verdict.get('why') or ''
    return found
