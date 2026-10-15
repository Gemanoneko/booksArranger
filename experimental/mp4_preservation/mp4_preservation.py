"""Isolated, unexecuted MP4 bytes proof. No filesystem or application integration."""
import hashlib
import struct
from fractions import Fraction

MAX_BYTES = 8 * 1024 * 1024
MAX_ITEMS = 4096
MAX_TAG = 8000


class Refused(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise Refused(message)


def atom(kind, payload):
    need(len(kind) == 4 and len(payload) <= MAX_BYTES - 8, 'Atom bound')
    return struct.pack('>I4s', len(payload) + 8, kind) + payload


def boxes(data):
    need(isinstance(data, bytes) and len(data) <= MAX_BYTES, 'Bytes bound')
    result = []
    at = 0
    while at < len(data):
        need(len(result) < MAX_ITEMS and at + 8 <= len(data), 'Atom header bound')
        size, kind = struct.unpack_from('>I4s', data, at)
        need(size >= 8 and at + size <= len(data), 'Unsupported atom size')
        result.append((kind, data[at + 8:at + size]))
        at += size
    return result


def children(data, kinds):
    parts = boxes(data)
    need([k for k, _ in parts] == list(kinds), 'Unsupported or duplicate layout')
    return dict(parts)


def full(data, size=None, version=0):
    need(len(data) >= 4 and data[:4] == bytes([version, 0, 0, 0]), 'Full-box version/flags')
    if size is not None:
        need(len(data) == size, 'Full-box size')


def rows(data, width, version=0):
    full(data, version=version)
    need(len(data) >= 8, 'Table header')
    count = int.from_bytes(data[4:8], 'big')
    need(0 < count <= MAX_ITEMS and len(data) == 8 + count * width, 'Table count/bounds')
    return [data[8 + i * width:8 + (i + 1) * width] for i in range(count)]


def u32(data, offset):
    return struct.unpack_from('>I', data, offset)[0]


def inspect(data):
    """Validate supported structure and return exact rational stored presentation.

    Decoder/PCM behavior is intentionally not certified by this structural proof.
    """
    top = children(data, (b'ftyp', b'moov', b'mdat'))
    need(len(top[b'ftyp']) >= 8 and len(top[b'ftyp']) % 4 == 0, 'File type')
    need(top[b'ftyp'][:4] == b'M4A ', 'Unsupported brand')
    need(all(top[b'ftyp'][i:i + 4] in (b'M4A ', b'isom', b'mp42')
             for i in range(8, len(top[b'ftyp']), 4)), 'Unsupported compatible brand')
    movie = children(top[b'moov'], (b'mvhd', b'trak', b'udta'))
    full(movie[b'mvhd'], 100)
    movie_scale, movie_duration = struct.unpack_from('>II', movie[b'mvhd'], 12)
    need(movie_scale > 0 and movie_duration > 0, 'Movie clock')
    track = children(movie[b'trak'], (b'tkhd', b'edts', b'mdia'))
    need(len(track[b'tkhd']) == 84 and track[b'tkhd'][:4] == b'\0\0\0\3', 'Track header profile')
    need(u32(track[b'tkhd'], 12) > 0 and u32(track[b'tkhd'], 20) == movie_duration, 'Track identity/duration')
    need(track[b'tkhd'][32:36] == b'\0' * 4 and track[b'tkhd'][76:84] == b'\0' * 8, 'Layer/alternate/visual track')
    edit = children(track[b'edts'], (b'elst',))[b'elst']
    edits = []
    for row in rows(edit, 12):
        duration, start, integer, fraction = struct.unpack('>Iihh', row)
        need(duration > 0 and start >= -1 and (integer, fraction) == (1, 0), 'Unsupported edit')
        edits.append((duration, start))
    need(sum(d for d, _ in edits) == movie_duration, 'Edit/movie duration mismatch')
    media = children(track[b'mdia'], (b'mdhd', b'hdlr', b'minf'))
    full(media[b'mdhd'], 24)
    scale, duration = struct.unpack_from('>II', media[b'mdhd'], 12)
    need(scale > 0 and duration > 0, 'Media clock')
    full(media[b'hdlr'])
    need(len(media[b'hdlr']) >= 24 and media[b'hdlr'][8:12] == b'soun', 'Audio handler only')
    minf = children(media[b'minf'], (b'smhd', b'dinf', b'stbl'))
    full(minf[b'smhd'], 8)
    dref = children(minf[b'dinf'], (b'dref',))[b'dref']
    full(dref)
    need(dref[4:8] == b'\0\0\0\1', 'One data reference required')
    need(children(dref[8:], (b'url ',))[b'url '] == b'\0\0\0\1', 'External data refused')
    table_parts = boxes(minf[b'stbl'])
    kinds = [k for k, _ in table_parts]
    expected = [b'stsd', b'stts']
    if b'ctts' in kinds:
        expected.append(b'ctts')
    expected += [b'stsc', b'stsz', kinds[-1] if kinds else b'']
    need(kinds == expected and kinds[-1] in (b'stco', b'co64'), 'Sample table profile')
    table = dict(table_parts)
    stsd = table[b'stsd']
    full(stsd)
    need(stsd[4:8] == b'\0\0\0\1', 'One decoder description required')
    entry = children(stsd[8:], (b'mp4a',))[b'mp4a']
    need(len(entry) >= 28 and entry[:6] == b'\0' * 6 and entry[6:8] == b'\0\1'
         and entry[8:16] == b'\0' * 8, 'Audio entry/reference/version')
    esds = children(entry[28:], (b'esds',))[b'esds']
    full(esds)
    need(len(esds) > 4, 'Missing opaque decoder descriptor')
    timing = []
    for row in rows(table[b'stts'], 8):
        count, delta = struct.unpack('>II', row)
        need(count > 0 and delta > 0 and len(timing) + count <= MAX_ITEMS, 'Timing bound')
        timing.extend([delta] * count)
    need(sum(timing) == duration, 'Decode duration mismatch')
    composition = [0] * len(timing)
    if b'ctts' in table:
        ctts = table[b'ctts']
        need(ctts[:1] in (b'\0', b'\1'), 'Composition version')
        composition = []
        for row in rows(ctts, 8, version=ctts[0]):
            count = u32(row, 0)
            offset = int.from_bytes(row[4:], 'big', signed=ctts[0] == 1)
            need(count > 0 and len(composition) + count <= len(timing), 'Composition bound')
            composition.extend([offset] * count)
        need(len(composition) == len(timing), 'Composition count mismatch')
    need(rows(table[b'stsc'], 12) == [struct.pack('>III', 1, 1, 1)], 'One sample per chunk profile')
    stsz = table[b'stsz']
    full(stsz)
    need(len(stsz) >= 12 and u32(stsz, 8) == len(timing), 'Sample size count')
    fixed = u32(stsz, 4)
    need(len(stsz) == (12 if fixed else 12 + 4 * len(timing)), 'Sample sizes bound')
    sizes = [fixed] * len(timing) if fixed else [u32(stsz, 12 + 4 * i) for i in range(len(timing))]
    offset_kind = kinds[-1]
    offsets = [int.from_bytes(r, 'big') for r in rows(table[offset_kind], 4 if offset_kind == b'stco' else 8)]
    need(len(offsets) == len(sizes), 'Chunk/sample count mismatch')
    start = 8 + len(top[b'ftyp']) + 8 + len(top[b'moov']) + 8
    cursor = start
    packets = []
    for offset, size in zip(offsets, sizes):
        need(size > 0 and offset == cursor and offset + size <= len(data), 'Overlapping/gapped/outside payload')
        packets.append(data[offset:offset + size])
        cursor += size
    need(cursor == len(data), 'Unclaimed payload')
    for length, media_start in edits:
        if media_start != -1:
            need(Fraction(media_start, scale) + Fraction(length, movie_scale) <= Fraction(duration, scale), 'Edit outside media')
    udta = children(movie[b'udta'], (b'meta',))[b'meta']
    full(udta)
    meta = children(udta[4:], (b'hdlr', b'ilst'))
    full(meta[b'hdlr'])
    need(len(meta[b'hdlr']) >= 24 and meta[b'hdlr'][8:12] == b'mdir', 'Apple metadata handler')
    tag = children(meta[b'ilst'], (b'sonm',))[b'sonm']
    tagdata = children(tag, (b'data',))[b'data']
    need(tagdata[:8] == b'\0\0\0\1\0\0\0\0' and 8 < len(tagdata) <= MAX_TAG + 8, 'UTF-8 metadata profile')
    try:
        tagdata[8:].decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        raise Refused('Invalid UTF-8 tag') from exc
    return {'movie_duration': Fraction(movie_duration, movie_scale),
            'edits': tuple((Fraction(d, movie_scale), None if s == -1 else Fraction(s, scale)) for d, s in edits),
            'sample_durations': tuple(Fraction(t, scale) for t in timing),
            'composition_offsets': tuple(Fraction(c, scale) for c in composition),
            'decoder_description': stsd, 'packets': tuple(packets),
            'offsets': tuple(offsets), 'mdat_start': start, 'offset_kind': offset_kind,
            'tag': tagdata[8:]}


CONTAINERS = {b'moov', b'trak', b'edts', b'mdia', b'minf', b'dinf', b'stbl', b'udta', b'ilst', b'sonm'}


def _rewrite(data, tag, delta):
    result = []
    for kind, payload in boxes(data):
        if kind in CONTAINERS:
            payload = _rewrite(payload, tag, delta)
        elif kind == b'meta':
            payload = payload[:4] + _rewrite(payload[4:], tag, delta)
        elif kind == b'data':
            payload = payload[:8] + tag
        elif kind in (b'stco', b'co64'):
            width = 4 if kind == b'stco' else 8
            values = []
            for row in rows(payload, width):
                relocated = int.from_bytes(row, 'big') + delta
                need(0 <= relocated < 1 << (8 * width), 'Chunk relocation overflow')
                values.append(relocated.to_bytes(width, 'big'))
            payload = payload[:8] + b''.join(values)
        result.append(atom(kind, payload))
    return b''.join(result)


def prove(source, candidate, approved_tag):
    """Require exact deterministic authorized transformation, not timing alone."""
    need(isinstance(approved_tag, str), 'Tag must be text')
    encoded = approved_tag.encode('utf-8', errors='strict')
    need(0 < len(encoded) <= MAX_TAG, 'Tag length bound')
    before, after = inspect(source), inspect(candidate)
    delta = len(encoded) - len(before['tag'])
    need(candidate == _rewrite(source, encoded, delta), 'Unauthorized byte change')
    for key in ('movie_duration', 'edits', 'sample_durations', 'composition_offsets', 'decoder_description', 'packets'):
        need(before[key] == after[key], 'Presentation or compressed media changed')
    need(after['mdat_start'] == before['mdat_start'] + delta, 'Payload relocation mismatch')
    return {'schema': 'isolated-mp4-bytes-proof-v1', 'metadata_delta': delta,
            'sample_count': len(before['packets']), 'source_sha256': hashlib.sha256(source).hexdigest(),
            'candidate_sha256': hashlib.sha256(candidate).hexdigest(),
            'pcm_verified': False, 'decoder_semantics_verified': False}


def retag(source, approved_tag):
    before = inspect(source)
    need(isinstance(approved_tag, str), 'Tag must be text')
    encoded = approved_tag.encode('utf-8', errors='strict')
    need(0 < len(encoded) <= MAX_TAG, 'Tag length bound')
    candidate = _rewrite(source, encoded, len(encoded) - len(before['tag']))
    return candidate, prove(source, candidate, approved_tag)
