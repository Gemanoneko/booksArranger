"""Source-matched Eye of God replacement proof; no queue/publication/retirement."""
import copy
import hashlib
import math
from pathlib import Path
import re
import struct
import uuid

from audio_pipeline import Paused, ValidationError, probe
from encoding_policy import PROFILE, freeze_policy
from metadata import audiobook_sort_title
from native_io import DirectoryBoundary, VerifiedFile, ordinary
from quicktime_chapters import MAX_MOOV, boxes, description

VERSION = 'source-matched-replacement-media-v1'
SOURCE_COUNT = 40
PCM_RATE = 44100
CHAPTER_TOLERANCE_SECONDS = .001
DECODE_TOLERANCE_SECONDS = .25
EXPECTED_ENCODING = {'codec': 'aac', 'bitrate': 128000, 'channels': 1, 'sample_rate': PCM_RATE}
SHA = re.compile(r'[0-9a-f]{64}')


def _fail(message):
    raise ValidationError(message)


def _identity(value):
    try:
        if type(value) is not str or str(uuid.UUID(value)) != value:
            _fail('Replacement identity is invalid')
    except (ValueError, AttributeError):
        _fail('Replacement identity is invalid')
    return value


def _milliseconds(frames):
    whole, remainder = divmod(frames * 1000, PCM_RATE)
    return whole + int(remainder * 2 > PCM_RATE or remainder * 2 == PCM_RATE and whole % 2 == 1)


def _recording_language_lines(manifest):
    """Existing comment representation only; never infer narration from work language."""
    values = []
    explicit = manifest.get('metadata', {}).get('edition_language')
    if explicit:
        values.append(explicit)
    for source in manifest.get('sources', []):
        value = source.get('metadata', {}).get('edition_language')
        if value and value not in values:
            values.append(value)
    # Preserve an already explicitly frozen supported comment; do not invent a
    # language when no edition/source/comment evidence exists.
    for line in manifest.get('comments', '').splitlines():
        if line.startswith('Recording language: '):
            value = line[len('Recording language: '):]
            if value and value not in values:
                values.append(value)
    result = []
    for value in values:
        if type(value) is not str or len(value) > 200 or '\n' in value or '\r' in value or '\0' in value:
            _fail('Frozen recording-language comment evidence is malformed')
        result.append('Recording language: ' + value)
    return result


def _plan(sources, frozen):
    if not isinstance(frozen, dict) or not isinstance(sources, list) or len(sources) != SOURCE_COUNT:
        _fail('Replacement requires the complete frozen forty-source plan')
    tracks = frozen.get('tracks')
    if not isinstance(tracks, list) or len(tracks) != SOURCE_COUNT or frozen.get('source_count') != SOURCE_COUNT:
        _fail('Replacement source boundary proof is incomplete')
    wanted = {'profile': PROFILE, **EXPECTED_ENCODING}
    if frozen.get('encoding') != wanted or frozen.get('source_policy') != 'KEEP_ALL_40_ORIGINALS':
        _fail('Replacement must preserve original sources and the approved 128k mono profile')
    if frozen.get('pcm_rate') != PCM_RATE or frozen.get('chapter_readback_tolerance_ms') != 1 or frozen.get('output_decoded_padding_tolerance_seconds') != DECODE_TOLERANCE_SECONDS:
        _fail('Replacement media proof tolerances changed')
    frames = 0
    total_bytes = 0
    seen = set()
    for index, (source, track) in enumerate(zip(sources, tracks), 1):
        if not isinstance(source, dict) or not isinstance(track, dict):
            _fail('Replacement source evidence is malformed')
        path = source.get('path')
        size = source.get('size')
        digest = source.get('sha256')
        if type(path) is not str or Path(path).suffix.lower() != '.mp3' or path in seen:
            _fail('Replacement must use distinct original MP3s in their proved order')
        ordinary(path)
        seen.add(path)
        if type(size) is not int or size <= 0 or type(digest) is not str or not SHA.fullmatch(digest):
            _fail('Replacement source bytes are not fully identified')
        count = track.get('pcm_frames')
        if type(count) is not int or count <= 0 or count > PCM_RATE * 7 * 86400:
            _fail('Replacement source PCM frame proof is invalid')
        if type(track.get('order')) is not int or type(track.get('size')) is not int or track.get('order') != index or track.get('path') != path or track.get('size') != size or track.get('sha256') != digest or track.get('pcm_rate') != PCM_RATE:
            _fail('Replacement source order or identity differs from the saved proof')
        if track.get('title') != f'Track {index:02}' or track.get('start_ms') != _milliseconds(frames):
            _fail('Replacement chapter names or starts differ from the saved forty-track plan')
        frames += count
        total_bytes += size
        if track.get('end_ms') != _milliseconds(frames):
            _fail('Replacement chapter endpoints differ from exact source PCM frames')
    if type(frozen.get('total_source_pcm_frames')) is not int or frozen['total_source_pcm_frames'] != frames or type(frozen.get('source_bytes')) is not int or frozen['source_bytes'] != total_bytes:
        _fail('Replacement source totals differ from the complete proof')
    seconds = frozen.get('total_decoded_source_seconds')
    if type(seconds) not in (float, int) or not math.isfinite(seconds) or abs(seconds - frames / PCM_RATE) > 1e-6:
        _fail('Replacement decoded source duration differs from exact PCM frames')
    _identity(frozen.get('parent_job_id'))
    return tracks, frames


def prepare_replacement(parent, newjobid, frozenplan):
    """Derive one new immutable source-matched manifest; never enqueue it."""
    _identity(newjobid)
    if not isinstance(parent, dict) or parent.get('state') != 'completed':
        _fail('Replacement requires its recorded completed parent')
    manifest = parent.get('manifest')
    output = parent.get('output')
    if not isinstance(manifest, dict) or not isinstance(output, dict):
        _fail('Replacement parent manifest/output proof is missing')
    parentid = _identity(manifest.get('job_id'))
    tracks, _ = _plan(manifest.get('sources'), frozenplan)
    if newjobid == parentid or frozenplan.get('parent_job_id') != parentid:
        _fail('Replacement must be a new job tied to its exact proved parent')
    destination = ordinary(manifest.get('destination'))
    if destination.suffix.lower() != '.m4b' or str(destination) != output.get('final_path'):
        _fail('Replacement parent publication relation differs')
    root = ordinary(manifest.get('root'))
    try:
        destination.relative_to(root)
    except ValueError:
        _fail('Replacement destination is outside its approved root')
    result = copy.deepcopy(manifest)
    result['job_id'] = newjobid
    result['destination'] = str(destination.with_name(destination.stem + ' - Final.m4b'))
    result['profile'] = PROFILE
    result['encoding_policy'] = freeze_policy(result['sources'])
    result['chapters'] = [track['title'] for track in tracks]
    result['replacement_parent_job_id'] = parentid
    result['replacement_media_version'] = VERSION
    result['replacement_media_plan'] = copy.deepcopy(frozenplan)
    # Reuse the supported comment label for an explicitly approved edition value.
    # Existing source edition values are also appended by audio_pipeline itself.
    comments = result.get('comments', '')
    if type(comments) is not str:
        _fail('Frozen replacement comments are malformed')
    for line in _recording_language_lines(result):
        if line not in comments.splitlines():
            comments += ('\n' if comments else '') + line
    result['comments'] = comments
    for key in ('cleanup_policy', 'attempt_id', 'automatic_approval', 'automatic_pending'):
        result.pop(key, None)
    return result


def _validate_receipt(manifest, validation):
    if not isinstance(manifest, dict) or not isinstance(validation, dict):
        _fail('Replacement manifest/validation is malformed')
    if manifest.get('replacement_media_version') != VERSION or manifest.get('profile') != PROFILE or manifest.get('cleanup_policy'):
        _fail('Replacement dispatch must keep originals and use the frozen source-matched profile')
    _identity(manifest.get('job_id'))
    plan = manifest.get('replacement_media_plan')
    tracks, frames = _plan(manifest.get('sources'), plan)
    if manifest.get('replacement_parent_job_id') != plan['parent_job_id'] or manifest['job_id'] == plan['parent_job_id']:
        _fail('Replacement parent/new-job relation changed')
    if manifest.get('encoding_policy') != freeze_policy(manifest['sources']) or manifest.get('chapters') != [track['title'] for track in tracks]:
        _fail('Replacement frozen encoding/chapter policy changed')
    if validation.get('profile') != PROFILE:
        _fail('Replacement private output used an unexpected profile')
    encoding = validation.get('encoding', {})
    if not isinstance(encoding, dict) or encoding.get('mode') not in (None, 'encode') or encoding.get('selection') != 'highest_verified_mp3_stream_bitrate' or encoding.get('source_bitrates') != [128000] * SOURCE_COUNT:
        _fail('Replacement must encode the forty verified 128k MP3 sources')
    if any(type(encoding.get(key)) is not int or encoding.get(key) != value for key, value in EXPECTED_ENCODING.items() if key != 'codec') or encoding.get('codec', 'aac') != 'aac':
        _fail('Replacement selected settings differ from 128k mono 44100Hz')
    if validation.get('source_pcm_rate') != PCM_RATE or validation.get('source_pcm_frames') != [track['pcm_frames'] for track in tracks]:
        _fail('Fresh source PCM boundaries differ from the saved original proof')
    expected = frames / PCM_RATE
    for key in ('expected_duration', 'decoded_duration'):
        value = validation.get(key)
        if type(value) not in (int, float) or not math.isfinite(value):
            _fail('Replacement complete decoded duration proof is missing')
        tolerance = 1e-6 if key == 'expected_duration' else DECODE_TOLERANCE_SECONDS
        if abs(value - expected) > tolerance:
            _fail('Replacement decoded audio differs from the complete source duration')
    wanted = [{'start': t['start_ms'], 'end': t['end_ms'], 'title': t['title']} for t in tracks]
    if validation.get('chapters') != wanted:
        _fail('Replacement generated chapter plan changed')
    if type(validation.get('size')) is not int or validation['size'] <= 0 or not isinstance(validation.get('sha256'), str) or not SHA.fullmatch(validation['sha256']):
        _fail('Replacement private file identity proof is missing')
    return tracks, expected


def _finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        _fail('Replacement media readback contains invalid timing')
    if not math.isfinite(number):
        _fail('Replacement media readback contains nonfinite timing')
    return number


def _readback(manifest, raw, tracks, expected):
    if not isinstance(raw, dict):
        _fail('Replacement media readback is malformed')
    streams = raw.get('streams', [])
    if not isinstance(streams, list) or any(not isinstance(s, dict) for s in streams):
        _fail('Replacement stream readback is malformed')
    audio = [s for s in streams if s.get('codec_type') == 'audio']
    if len(audio) != 1:
        _fail('Replacement must contain one audio stream')
    stream = audio[0]
    if (stream.get('codec_name'), str(stream.get('sample_rate')), stream.get('channels')) != ('aac', '44100', 1) or stream.get('profile') != 'LC':
        _fail('Replacement actual audio is not AAC-LC mono 44100Hz')
    bitrate = stream.get('bit_rate')
    if type(bitrate) not in (int, str) or not str(bitrate).isdigit() or int(bitrate) <= 0:
        _fail('Replacement actual AAC stream rate is unavailable')
    cover = [s for s in streams if s.get('codec_type') == 'video' and s.get('disposition', {}).get('attached_pic') == 1]
    if len(cover) != 1 or any(s.get('codec_type') == 'video' and s not in cover for s in streams):
        _fail('Replacement must have one attached cover and no other video')
    tags = {k.lower(): str(v) for k, v in raw.get('format', {}).get('tags', {}).items()}
    review = manifest['metadata']
    wanted = {'title': review['title'], 'artist': review['canonical_author'], 'album_artist': review['canonical_author'], 'media_type': '2', 'genre': 'Audiobook'}
    if review.get('series'):
        wanted['album'] = ' - '.join([review['series'], review.get('number', ''), review['title']])
        wanted['grouping'] = review['series']
        if str(review.get('number', '')).isdigit() and 0 < int(review['number']) < 65536:
            wanted['track'] = str(int(review['number']))
    else:
        wanted['album'] = review['title']
    sort = audiobook_sort_title(review)
    if sort != review['title']:
        wanted['sort_name'] = sort
    if any(tags.get(key) != value for key, value in wanted.items()):
        _fail('Replacement actual canonical metadata changed')
    if review.get('narrator') and 'Narrator: ' + review['narrator'] not in tags.get('comment', '').splitlines():
        _fail('Replacement narrator credit is missing')
    language_lines = _recording_language_lines(manifest)
    actual_language_lines = [line for line in tags.get('comment', '').splitlines() if line.startswith('Recording language: ')]
    if set(actual_language_lines) != set(language_lines):
        _fail('Replacement actual recording-language comment evidence is missing')
    chapters = raw.get('chapters')
    if not isinstance(chapters, list) or len(chapters) != SOURCE_COUNT:
        _fail('Replacement actual chapter count changed')
    for chapter, track in zip(chapters, tracks):
        if not isinstance(chapter, dict):
            _fail('Replacement actual chapter readback is malformed')
        if chapter.get('tags', {}).get('title') != track['title']:
            _fail('Replacement actual chapter name or order changed')
        if abs(_finite(chapter.get('start_time')) - track['start_ms'] / 1000) > CHAPTER_TOLERANCE_SECONDS + 1e-9 or abs(_finite(chapter.get('end_time')) - track['end_ms'] / 1000) > CHAPTER_TOLERANCE_SECONDS + 1e-9:
            _fail('Replacement actual chapter boundary changed')
    if abs(_finite(raw.get('format', {}).get('duration')) - expected) > DECODE_TOLERANCE_SECONDS:
        _fail('Replacement actual duration differs from complete sources')
    return {'actual_audio': {key: stream.get(key) for key in ('codec_name', 'profile', 'sample_rate', 'channels', 'channel_layout', 'bit_rate')},
            'actual_audio_language_tag': stream.get('tags', {}).get('language'), 'actual_tags': tags,
            'recording_language_comment_lines': language_lines,
            'recording_language_scope': 'Explicit frozen edition/source comments only; absent evidence stays absent; no new MP4 language tag or inference from original-work language',
            'actual_chapters': copy.deepcopy(chapters)}


def _one(data, kind):
    matches = [value for name, value in boxes(data) if name == kind]
    if len(matches) != 1:
        _fail('Replacement movie atom structure is missing or ambiguous')
    return matches[0]


def _sample_bytes(table):
    if len(table) < 20 or table[8:12] != b'\0' * 4:
        _fail('Replacement audio sample-size table is malformed')
    uniform, count = struct.unpack_from('>II', table, 12)
    if not count or count > MAX_MOOV // 4:
        _fail('Replacement audio sample-size count exceeds its bound')
    if uniform:
        if len(table) != 20:
            _fail('Replacement uniform sample-size table has extra bytes')
        return uniform * count, count
    if len(table) != 20 + count * 4:
        _fail('Replacement sample sizes disagree with their count')
    total = 0
    for (size,) in struct.iter_unpack('>I', table[20:]):
        if not size:
            _fail('Replacement audio sample has zero size')
        total += size
    return total, count


def _movie_accounting(moov, file_size, mdat_payload_size):
    if len(moov) > MAX_MOOV or len(moov) < 8 or moov[4:8] != b'moov' or int.from_bytes(moov[:4], 'big') != len(moov):
        _fail('Replacement movie metadata exceeds or violates its bound')
    tracks = [value for kind, value in boxes(moov[8:]) if kind == b'trak']
    audio = []; chapter = []
    if len(tracks) > 3:
        _fail('Replacement movie has unexpected tracks')
    for track in tracks:
        media = _one(track[8:], b'mdia')
        handler = _one(media[8:], b'hdlr')
        if len(handler) < 20:
            _fail('Replacement movie track handler is truncated')
        kind = handler[16:20]
        info = _one(media[8:], b'minf')
        samples = _one(info[8:], b'stbl')
        if kind == b'soun':
            audio.append(_sample_bytes(_one(samples[8:], b'stsz')))
        elif kind == b'text':
            table = _one(samples[8:], b'stsd')
            if len(table) < 16 or table[8:16] != b'\0\0\0\0\0\0\0\1':
                _fail('Replacement chapter sample description is malformed')
            entries = boxes(table[16:])
            if len(entries) != 1 or entries[0][0] != b'text':
                _fail('Replacement chapter sample type is unsupported')
            value = description(entries[0][1])
            if value['entry_size'] != 65 or value['font_name'] != 'Arial':
                _fail('Replacement chapter text does not use the corrected QuickTime layout')
            chapter.append(value)
        else:
            _fail('Replacement movie has an unexpected media track')
    if len(audio) != 1 or len(chapter) != 1:
        _fail('Replacement movie requires one audio and one chapter text track')
    payload, count = audio[0]
    if payload > mdat_payload_size or mdat_payload_size >= file_size or payload >= file_size:
        _fail('Replacement audio samples exceed actual file/media bounds')
    return {'audio_payload_bytes': payload, 'audio_sample_count': count, 'nonaudio_bytes': file_size - payload, 'chapter_description': chapter[0]}


def _account_output(output, size, stop):
    with output.open('rb') as incoming:
        top = []; position = 0; moov = None; mdat_size = None
        while position < size:
            if stop.is_set():
                raise Paused('Replacement verification paused; originals remain unchanged')
            incoming.seek(position); header = incoming.read(8)
            if len(header) != 8:
                _fail('Replacement top-level movie atom is truncated')
            length, kind = struct.unpack('>I4s', header)
            if length < 8 or position + length > size or len(top) >= 4:
                _fail('Replacement top-level movie atom is unsupported')
            top.append(kind)
            if kind == b'moov':
                if length > MAX_MOOV:
                    _fail('Replacement movie metadata exceeds its bound')
                incoming.seek(position); moov = incoming.read(length)
                if len(moov) != length:
                    _fail('Replacement movie metadata ended early')
            if kind == b'mdat':
                mdat_size = length - 8
            position += length
        if top != [b'ftyp', b'moov', b'free', b'mdat']:
            _fail('Replacement only supports its owned unfragmented faststart MP4 layout')
        return _movie_accounting(moov, size, mdat_size)


def verify_replacement(manifest, validation, output, stage, stop):
    """Verify a protected private artifact; caller registers/publishes separately."""
    tracks, expected = _validate_receipt(manifest, validation)
    output = ordinary(output); stage = ordinary(stage)
    if output.parent != stage or output.suffix.lower() != '.m4b':
        _fail('Replacement validation must use the exact owned private output')
    with DirectoryBoundary(stage, stage), VerifiedFile(output) as held:
        facts = held.facts()
        if facts['links'] != 1 or facts['size'] != validation['size']:
            _fail('Replacement private output size or native links changed')
        digest = hashlib.sha256()
        for block in held.chunks():
            if stop.is_set():
                raise Paused('Replacement verification paused; originals remain unchanged')
            digest.update(block)
        if digest.hexdigest() != validation['sha256']:
            _fail('Replacement private output bytes changed since validation')
        actual = _readback(manifest, probe(output, stage, stop), tracks, expected)
        accounting = _account_output(output, facts['size'], stop)
        receipt = {'version': VERSION, 'source_policy': 'KEEP_ALL_40_ORIGINALS', 'source_count': SOURCE_COUNT, 'selected_encoding': copy.deepcopy(EXPECTED_ENCODING),
                   'source_bytes': manifest['replacement_media_plan']['source_bytes'], 'output_bytes': facts['size'], 'growth_bytes': facts['size'] - manifest['replacement_media_plan']['source_bytes'],
                   'source_pcm_frames': sum(t['pcm_frames'] for t in tracks), 'pcm_rate': PCM_RATE, 'chapter_tolerance_seconds': CHAPTER_TOLERANCE_SECONDS,
                   'decoded_padding_tolerance_seconds': DECODE_TOLERANCE_SECONDS, 'private_identity': facts, 'sha256': validation['sha256'],
                   'cover_sha256': manifest['cover']['sha256'], 'cover_check': 'Complete pipeline cover extraction passed; exact private output hash revalidated',
                   'audio_quality': 'Source-matched AAC re-encoding is lossy; perceptual or bit-identical quality is not certified', **actual, **accounting}
        result = copy.deepcopy(validation)
        result['replacement_media'] = receipt
        return result
