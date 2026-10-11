"""Pure recording comparisons; callers supply freshly verified facts, never title guesses.

Input keys: identity_verified, work_ids (ordered canonical component IDs),
collection_kind, series_volume; recording_language/narrator/edition are facts
{value: str, verified: bool}; manifest is {complete, observed_count, tracks}.
Each observed track may contain source_sha256 + size_bytes, packet_sha256 and
chapter_sha256. Packet hashes describe encoded packets, not decoded equivalence.
Packet-only equivalence is intentionally unsupported: decoder configuration and
presentation timing are not proven by payload or chapter hashes. Only complete
ordered source byte equality plus chapter equality can authorize reuse.
Existing jobs add id, approved, completed_verified and current_output_valid. No filesystem operations.
"""
import hashlib
import json
import re
from collections.abc import Mapping


def _identity(item):
    ids = item.get('work_ids')
    if item.get('identity_verified') is not True or not isinstance(ids, (list, tuple)) or not ids:
        return None
    if any(not isinstance(v, str) or not v.strip() for v in ids):
        return None
    kind = item.get('collection_kind', 'single')
    volume = item.get('series_volume')
    if not isinstance(kind, str) or (volume is not None and not isinstance(volume, str)):
        return None
    return (kind, tuple(ids), volume)


def _fact(item, key):
    value = item.get(key)
    if isinstance(value, Mapping) and value.get('verified') is True:
        text = value.get('value')
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-fA-F]{64}', value) is not None


def _manifest(item):
    value = item.get('manifest')
    if not isinstance(value, Mapping) or value.get('complete') is not True:
        return None
    tracks = value.get('tracks')
    count = value.get('observed_count')
    if not isinstance(tracks, (list, tuple)) or not tracks or type(count) is not int or count != len(tracks):
        return None
    if any(not isinstance(track, Mapping) for track in tracks):
        return None
    for track in tracks:
        source = (_sha(track.get('source_sha256')) and type(track.get('size_bytes')) is int
                  and track['size_bytes'] > 0)
        if not _sha(track.get('chapter_sha256')) or not (source or _sha(track.get('packet_sha256'))):
            return None
    return tracks


def _proof(left, right):
    a, b = _manifest(left), _manifest(right)
    if a is None or b is None or len(a) != len(b):
        return None
    # Full source bytes bind decoder configuration, container edit/priming and
    # presentation timing as well as audio. Packet payload equality cannot.
    if all(_sha(x.get('source_sha256')) and _sha(y.get('source_sha256'))
           and x['source_sha256'].lower() == y['source_sha256'].lower()
           and type(x.get('size_bytes')) is int and x['size_bytes'] > 0
           and x['size_bytes'] == y.get('size_bytes') and type(y.get('size_bytes')) is int
           and _sha(x.get('chapter_sha256')) and _sha(y.get('chapter_sha256'))
           and x['chapter_sha256'].lower() == y['chapter_sha256'].lower()
           for x, y in zip(a, b)):
        return 'complete_ordered_source_bytes'
    return None


def destination_suffix(candidate):
    """Safe deterministic suggestion; caller must still publish without replacement."""
    facts = [_fact(candidate, key) for key in ('narrator', 'edition')]
    label = ' - '.join(v for v in facts if v)
    label = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', label).strip(' .')[:80].rstrip(' .')
    seed = {'identity': _identity(candidate), 'facts': facts,
            'language': _fact(candidate, 'recording_language'),
            'manifest': candidate.get('manifest'), 'id': candidate.get('id')}
    digest = hashlib.sha256(json.dumps(seed, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':'), default=str).encode()).hexdigest()[:16]
    return (label + ' - ' if label else '') + 'recording-' + digest


def classify_recording(candidate, existing):
    """Return pure evidence/review/hold/reuse recommendations, never deletion rights.

    Caller must validate any reused output and current source completeness again.
    related_ids refer to supplied records; UI resolves names through trusted facts.
    An identical but unfinished job blocks a second job, without claiming readiness.
    """
    identity = _identity(candidate)
    result = {'classification': 'new', 'evidence': [], 'review_required': False,
              'hold': False, 'reuse_job_id': None, 'destination_suffix': destination_suffix(candidate),
              'duplicate_review': None}
    if identity is None or _manifest(candidate) is None:
        result.update(classification='uncertain', hold=True)
        result['evidence'].append('Verified component identity and complete observed manifest required.')
        return result
    related, identical, distinct, possible = [], [], [], []
    for other in existing:
        other_identity = _identity(other)
        # A constituent shared with an assembly is not the same book. Component
        # order, collection kind and known volume are all part of exact identity.
        if other_identity is None or other_identity[0] != identity[0]:
            continue
        if sorted(other_identity[1]) != sorted(identity[1]):
            continue
        if other_identity[2] and identity[2] and other_identity[2] != identity[2]:
            continue
        other_id = other.get('id')
        if not isinstance(other_id, str) or not other_id:
            result.update(classification='uncertain', hold=True)
            result['evidence'].append('Related recording has no stable identity.')
            return result
        related.append(other_id)
        differences = [key for key in ('recording_language', 'narrator', 'edition')
                       if _fact(candidate, key) and _fact(other, key)
                       and _fact(candidate, key).casefold() != _fact(other, key).casefold()]
        proof = _proof(candidate, other) if other_identity == identity else None
        if other_identity != identity:
            possible.append(other_id)
            result['evidence'].append({'id': other_id, 'reason': 'Component order or volume identity remains uncertain'})
            continue
        if proof and differences:
            possible.append(other_id)
            result['evidence'].append({'id': other_id, 'reason': 'Content identity conflicts with verified credits', 'fields': differences})
        elif proof:
            identical.append(other)
            result['evidence'].append({'id': other_id, 'reason': proof})
        elif differences and _manifest(other) is not None:
            distinct.append(other_id)
            result['evidence'].append({'id': other_id, 'reason': 'Verified distinct recording facts', 'fields': differences})
        else:
            possible.append(other_id)
            result['evidence'].append({'id': other_id, 'reason': 'Recording equivalence not established'})
    if not related:
        return result
    # Ambiguous relationships take precedence; never reuse a known match while
    # concealing another conflicting/uncertain relationship.
    if possible:
        state = 'possible'
        result.update(classification=state, review_required=True, hold=True)
    elif identical:
        state = 'verified_identical'
        eligible = sorted((v for v in identical if v.get('approved') is True
                           and v.get('completed_verified') is True and v.get('current_output_valid') is True), key=lambda v: v['id'])
        result.update(classification=state, review_required=True,
                      hold=not bool(eligible), reuse_job_id=eligible[0]['id'] if eligible else None)
    else:
        state = 'related_distinct'
        result.update(classification=state, review_required=True)
    result['duplicate_review'] = {'state': state, 'blocking': result['hold'],
                                  'related_ids': sorted(set(related))}
    return result
