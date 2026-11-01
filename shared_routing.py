"""Identity-bound evidence for shared-series/world folders.

The research/review owner supplies independently established memberships. This module
never discovers a relationship from matching names, folders, narrators or coauthors.
Its receipt is frozen with metadata_facts; old manifests without it keep their route.
"""
import copy
import re
import unicodedata

POLICY = 'books-shared-routing-v1'
_FIELDS = ('title', 'author', 'canonical_author', 'series', 'number', 'universe')


class RoutingEvidenceError(ValueError):
    """A caller can hold this book for an explicit series/world answer."""
    code = 'shared_routing_identity'


def _fail(detail):
    raise RoutingEvidenceError(detail + " Confirm this book's series and world in Edit names.")


def _text(value, label, limit=2000, *, empty=False):
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()):
        _fail('Shared routing ' + label + ' is missing or malformed.')
    return value.strip()


def _key(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def _credits(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 30:
        _fail("Shared routing needs each book's complete author credit.")
    result = [_text(item, 'author', 300) for item in value]
    if len({_key(item) for item in result}) != len(result):
        _fail('Shared routing repeats an author in one book.')
    return result


def _work_ids(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 100:
        _fail('Shared routing needs the accepted work identity.')
    result = [_text(item, 'work identity', 200) for item in value]
    if len(set(result)) != len(result):
        _fail('Shared routing repeats a work identity.')
    return result


def _identity(value, basis):
    value = _text(value, 'series/world identity', 1000)
    # IDs are supplied by the identity owner, not derived here from the display name.
    # A user decision has its own durable ID, never an invented catalog identity.
    if basis == 'user':
        valid = value.startswith('user:') and len(value) > 5
    else:
        valid = bool(re.match(r'(?:https://[^/]+/|[a-z][a-z0-9_.-]*:)[^\s]+$', value)) and not value.startswith('user:')
    if not valid:
        _fail('Shared routing needs a stable catalog or user-decision identity.')
    return value


def _binding(review, facts):
    if not isinstance(review, dict) or not isinstance(facts, dict):
        _fail('Shared routing has no accepted metadata binding.')
    values = {field: _text(review.get(field, ''), field, empty=True) for field in _FIELDS}
    authors = _credits(facts.get('authors'))
    if values['canonical_author'] != '; '.join(authors):
        _fail('Shared routing author evidence changed.')
    return {'source_fingerprint': _text(facts.get('source_fingerprint'), 'source fingerprint', 256),
            'work_ids': _work_ids(facts.get('work_ids')), 'authors': authors, 'review': values}


def _authority(value, kind, binding):
    if not isinstance(value, dict) or set(value) != {'id', 'name', 'basis', 'evidence', 'members'}:
        _fail('Shared routing ' + kind + ' evidence is malformed.')
    basis = value.get('basis')
    if basis not in ('catalog', 'user'):
        _fail('Shared routing needs confirmed catalog evidence or a user decision.')
    identity = _identity(value['id'], basis)
    name = _text(value['name'], kind + ' name')
    field = 'series' if kind == 'series' else 'universe'
    if not binding['review'][field] or name != binding['review'][field]:
        _fail('Shared routing ' + kind + ' no longer matches the accepted name.')
    evidence = value['evidence']
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 20:
        _fail('Shared routing needs its catalog citations or user-decision receipts.')
    evidence = [_text(item, 'evidence receipt', 2000) for item in evidence]
    members = value['members']
    if not isinstance(members, list) or not 1 <= len(members) <= 100:
        _fail('Shared routing needs a bounded list of confirmed member books.')
    seen = {}; normalized = []; teams = set(); series_ids = set()
    for member in members:
        expected = {'work_id', 'authors'} if kind == 'series' else {'work_id', 'authors', 'series_id'}
        if not isinstance(member, dict) or set(member) != expected:
            _fail('Shared routing membership is incomplete.')
        work_id = _text(member['work_id'], 'member work identity', 200)
        authors = _credits(member['authors'])
        if work_id in seen:
            _fail('Shared routing repeats or conflicts on one member work.')
        seen[work_id] = authors
        teams.add(frozenset(_key(author) for author in authors))
        item = {'work_id': work_id, 'authors': authors}
        if kind == 'world':
            series_id = member['series_id']
            if series_id is not None:
                # A world's member can be a standalone. A named series needs its own
                # stable identity; two spellings of one series never count as two.
                series_id = _identity(series_id, 'user' if isinstance(series_id, str) and series_id.startswith('user:') else 'catalog')
                series_ids.add(series_id)
            item['series_id'] = series_id
        if kind == 'world' and work_id in binding['work_ids'] and bool(binding['review']['series']) != (item['series_id'] is not None):
            _fail("Shared world membership no longer matches this book's series.")
        normalized.append(item)
    current_team = frozenset(_key(author) for author in binding['authors'])
    for work_id in binding['work_ids']:
        if work_id not in seen or frozenset(_key(author) for author in seen[work_id]) != current_team:
            _fail('Shared routing membership does not identify this book and every credited author.')
    shared = len(seen) > 1 and (len(teams) > 1 or (kind == 'world' and len(series_ids) > 1))
    return {'id': identity, 'name': name, 'basis': basis, 'evidence': evidence, 'members': normalized}, shared


def build(review, facts, *, series=None, universe=None):
    """Freeze independently confirmed memberships after final accepted name choices.

    Authority: {id, name, basis: 'catalog'|'user', evidence: [receipt IDs/URLs],
    members: [{work_id, authors: [complete canonical credits]}]}. World members
    additionally carry series_id (a stable identity, or None for a standalone).
    Every current work ID and its complete authors must be among those members.
    A witness list can be partial: two established works suffice; no census is claimed.
    """
    if series is None and universe is None:
        _fail('Shared routing has no confirmed series or world.')
    binding = _binding(review, facts)
    result = {'policy_version': POLICY, 'binding': binding}
    if series is not None:
        result['series'], _ = _authority(series, 'series', binding)
    if universe is not None:
        result['universe'], _ = _authority(universe, 'world', binding)
    _coherent(result)
    return copy.deepcopy(result)


def _coherent(proof):
    if 'series' not in proof or 'universe' not in proof:
        return
    for member in proof['universe']['members']:
        if member['work_id'] in proof['binding']['work_ids'] and member['series_id'] != proof['series']['id']:
            _fail('Shared series and world evidence disagree on this book.')


def resolve(review, facts):
    """Validate the frozen proof; absence leaves all existing routing unchanged."""
    result = {'multi_author_series': False, 'shared_world': False}
    if not isinstance(facts, dict) or 'shared_routing' not in facts:
        return result
    proof = facts['shared_routing']
    if not isinstance(proof, dict) or proof.get('policy_version') != POLICY or set(proof) - {'policy_version', 'binding', 'series', 'universe'}:
        _fail('Shared routing receipt is malformed or unsupported.')
    if proof.get('binding') != _binding(review, facts):
        _fail('Shared routing source or accepted names changed.')
    if 'series' not in proof and 'universe' not in proof:
        _fail('Shared routing receipt has no confirmed membership.')
    if 'series' in proof:
        _, result['multi_author_series'] = _authority(proof['series'], 'series', proof['binding'])
    if 'universe' in proof:
        _, result['shared_world'] = _authority(proof['universe'], 'world', proof['binding'])
    _coherent(proof)
    return result
