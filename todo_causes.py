"""Typed causes for the three hold rows of the to-do list (Judy 2026-10-24, 0.22.0 review B4): Order unclear, Files
unclear and Part of a bigger book. Derived from the members already in the row and the recorded hold: no new
research, no file access. The UI maps each cause to its own sentence; 'unknown' has a sentence too."""
import re
from pathlib import Path

ORDER = 'Playback order uncertain'
MEMBERSHIP = 'Source membership uncertain'
MIXED = 'Mixed recordings in this group'
PIECE = 'One part of a bigger book'
HOLD_GROUPS = ('part_of_book', 'files_unclear', 'order_unclear')  # the order a book with several holds counts in


def _tags(member):
    return {str(k).casefold(): v for k, v in ((member.get('metadata') or {}).get('tags') or {}).items()}


def _number(value):
    match = re.match(r'^\s*(\d+)', str(value or ''))
    return int(match[1]) if match else None


def _total(value):
    match = re.fullmatch(r'\s*\d+\s*/\s*(\d+)\s*', str(value or ''))
    return int(match[1]) if match else None


def _raw(member, *names):
    tags = _tags(member)
    return next((str(tags[n]) for n in names if tags.get(n) not in (None, '')), '')


def holds(record):
    """The hold groups a recorded research result asks about, in counting order (several may apply)."""
    reasons = [str(r) for r in (record.get('reasons') or [])]
    found = []
    if (record.get('identity_hold') or {}).get('kind') == 'piece' or PIECE in reasons:
        found.append('part_of_book')
    if MEMBERSHIP in reasons or MIXED in reasons:
        found.append('files_unclear')
    if ORDER in reasons:
        found.append('order_unclear')
    return found


def order_cause(members):
    """{'cause': no_tracks | some_missing | tied | gaps | conflict | odd_tracks | unknown, 'missing', 'total'}
    conflict: the file names and the track tags number the files differently; odd_tracks: a track tag is not a plain
    number ("1.", "1-1"). Both measured common on the live catalog (2026-10-24: 40 and 32 of 120 rows)."""
    total = len(members)
    numbers = [_number(_raw(m, 'track', 'tracknumber')) for m in members]
    missing = sum(n is None for n in numbers)
    if total and missing == total:
        return {'cause': 'no_tracks', 'missing': missing, 'total': total}
    if missing:
        return {'cause': 'some_missing', 'missing': missing, 'total': total}
    positions = [(_number(_raw(m, 'disc', 'discnumber')) or 1, n) for m, n in zip(members, numbers)]
    if len(set(positions)) != len(positions):
        return {'cause': 'tied', 'missing': 0, 'total': total}
    discs = sorted({p[0] for p in positions})
    for disc in discs:
        tracks = sorted(p[1] for p in positions if p[0] == disc)
        if tracks[0] not in (0, 1) or tracks != list(range(tracks[0], tracks[-1] + 1)):
            return {'cause': 'gaps', 'missing': 0, 'total': total}
    if discs != list(range(1, len(discs) + 1)):
        return {'cause': 'gaps', 'missing': 0, 'total': total}
    if any(m.get('order_conflict') for m in members):
        return {'cause': 'conflict', 'missing': 0, 'total': total}
    if any(not re.fullmatch(r'\s*\d+(?:\s*/\s*\d+)?\s*', _raw(m, 'track', 'tracknumber')) for m in members):
        return {'cause': 'odd_tracks', 'missing': 0, 'total': total}
    return {'cause': 'unknown', 'missing': 0, 'total': total}


def _key(value):
    return re.sub(r'[\W_]+', ' ', str(value or '').casefold().replace('ё', 'е')).strip()


def _counted(members, *names):
    counts = {}
    for m in members:
        value = _raw(m, *names).strip()
        counts[value] = counts.get(value, 0) + 1
    return [{'name': name or '(none)', 'files': n} for name, n in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def files_cause(members, reasons, title='', split=False, works=None):
    """{'cause': works | track_total | disc_total | one_of_many | lack_title | mixed | parts | unknown, the numbers its
    sentence needs, 'flagged' (paths without the title), 'albums' / 'artists' ([{name, files}] for mixed), 'works'
    ([{name, files}]: the books the title tags of a joined album name, Senua's 0.22.0 review G3)}"""
    reasons = [str(r) for r in reasons or []]
    here = len(members)
    if MEMBERSHIP in reasons and isinstance(works, list) and len(works) > 1:
        # Every work, so the row's "+ n more" is exact (Judy's part-sets copy check N1); bounded for the payload.
        return {'cause': 'works', 'works': [{'name': str(w.get('name') or ''), 'files': int(w.get('files') or 0)} for w in works[:200]]}
    if MEMBERSHIP in reasons:
        if here == 1:
            total = _total(_raw(members[0], 'track', 'tracknumber'))
            if total and total > 1:
                return {'cause': 'one_of_many', 'index': _number(_raw(members[0], 'track', 'tracknumber')), 'total': total}
        by_disc = {}
        for m in members:
            by_disc.setdefault(_number(_raw(m, 'disc', 'discnumber')) or 1, []).append(m)
        for disc, part in sorted(by_disc.items()):
            totals = [t for t in (_total(_raw(m, 'track', 'tracknumber')) for m in part) if t]
            if totals:
                said = max(set(totals), key=totals.count)
                if said != len(part):
                    return {'cause': 'track_total', 'tags_say': said, 'here': len(part)}
        disc_totals = [t for t in (_total(_raw(m, 'disc', 'discnumber')) for m in members) if t]
        if disc_totals:
            said = max(set(disc_totals), key=disc_totals.count)
            if said != len(by_disc):
                return {'cause': 'disc_total', 'tags_say': said, 'here': len(by_disc)}
        key = _key(title)
        if key and here > 1:
            def mentions(m):
                values = [_raw(m, 'album'), _raw(m, 'title'), m.get('filename') or Path(m['path']).name, Path(m['path']).parent.name]
                return any(key in _key(v) for v in values if v)
            flagged = [m['path'] for m in members if not mentions(m)]
            if flagged and len(flagged) < here:
                return {'cause': 'lack_title', 'missing': len(flagged), 'total': here, 'flagged': flagged}
        if split:
            return {'cause': 'parts'}
    if MIXED in reasons:
        albums, artists = _counted(members, 'album'), _counted(members, 'artist')
        return {'cause': 'mixed', 'albums': albums if len(albums) > 1 else [], 'artists': artists if len(albums) <= 1 and len(artists) > 1 else []}
    return {'cause': 'unknown'}


def piece_cause(hold):
    """{'cause': chapter | numbered_part | siblings | part_set | unreadable | unknown, 'beside', 'index', 'total', 'set'}"""
    piece = (hold or {}).get('piece') or {}
    kind = piece.get('piece')
    if kind in ('chapter', 'part_title'):
        return {'cause': 'chapter'}
    if kind == 'numbered_part':
        return {'cause': 'numbered_part'}
    if kind == 'siblings':
        return {'cause': 'siblings', 'beside': int(piece.get('count') or 0)}
    if kind == 'part_set':
        return {'cause': 'part_set', 'index': piece.get('position'), 'total': piece.get('parts'), 'set': piece.get('set') or ''}
    if kind == 'unreadable':
        return {'cause': 'unreadable'}
    if kind == 'set':
        # Rulings 19 and 19a: a set of .m4b parts their chapters do not settle (part_sets.decide's basis is the cause).
        cause = piece.get('cause') if piece.get('cause') in ('seasons', 'book_words', 'long', 'authors', 'unclear', 'unreadable') else 'unclear'
        return {'cause': 'set_' + cause, 'parts': int(piece.get('parts') or 0), 'hours': piece.get('hours')}
    return {'cause': 'unknown'}


def files(members, order=None, included=None, flagged=()):
    """The files Approve will use, in its order: [{name, folder, track, disc, flag}]."""
    keyed = {m['member_key']: m for m in members if m.get('member_key')}
    chosen = [keyed[k] for k in order if k in keyed and (included is None or k in included)] if order else list(members)
    flagged = set(flagged)
    return [{'name': m.get('filename') or Path(m['path']).name, 'folder': str(Path(m['path']).parent), 'path': m['path'],
             'track': _raw(m, 'track', 'tracknumber'), 'disc': _raw(m, 'disc', 'discnumber'), 'flag': m['path'] in flagged} for m in chosen]
