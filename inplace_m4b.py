"""Single-M4B in-place metadata edit (0.21.0).

The copy flow's own preservation plan, applied to the original instead of a staged copy: the planned
moov is appended after the original end of file, then the old moov's 4-byte type becomes 'free'. No
mdat/audio byte moves, so the result is byte-identical to the copy flow's checked.m4b.

Eligibility is the copy flow's own route into metadata preservation (automatic profile, one .m4b
whose AAC audio is stream-copied, no approved repair, a preservation plan that needs no repair), plus
what an in-place edit needs (one ordinary link, a held deny-writers handle, a same-volume destination,
no foreign named streams). Any refusal before the first written byte returns None, and the copy flow
then runs every one of its own checks (on a cover copy this attempt staged too, 0.21.0 F1). After the
first write, every failure undoes the edit (a full-read proof that the file's original extent is still
the reviewed original, then length, the 4 type bytes, the download marker it removed, write time and
attributes, then a full-hash proof) before anything else. A crash leaves an inplace_edits row that
recovery undoes, or proves moved, at startup and before any new attempt on that source.

No decode is performed (Sergei, 2026-10-22). Audio integrity rests on the byte proof: with the 4
type bytes reverted, the file's original extent hashes to the reviewed SHA-256, and the appended
bytes equal the plan.
"""
import base64
import contextlib
import critical_sections
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import audio_pipeline as ap
import m4b_preservation as mp
import m4b_repair
import source_proofs
import zone_identifier
from encoding_policy import AUTOMATIC_PROFILE, choose_automatic_encoding, freeze_automatic_policy
from native_io import BoundaryError, DirectoryBoundary, VerifiedFile, ordinary
from scanner import connect
from sqlite_retry import transaction

SELECTION = 'existing_m4b_in_place_metadata_edit'
MODE = 'in_place'
SCHEMA = 'books-m4b-in-place-edit-v1'
OPEN = ('intended', 'written', 'publishing', 'unresolved')


class Ineligible(Exception):
    """Before any write: the copy flow then runs, with all of its own checks."""


class Unresolved(ap.ValidationError):
    """The edit began and its undo is not proven yet; the journal keeps it for recovery."""


def _fault(point, handle=None):
    """Test seam only: a named step of the write sequence (with its open writer, where one is held)."""


def _stamp():
    return datetime.now(timezone.utc).isoformat()


def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS inplace_edits(job_id TEXT,attempt_id TEXT,path TEXT,state TEXT,intent TEXT,detail TEXT,updated TEXT,PRIMARY KEY(job_id,attempt_id))')


DAMAGED = 'The journal record of this edit is damaged; the file was not changed'
_FILETIME_EPOCH = 116444736000000000  # 100-ns ticks from 1601 to 1970, as VerifiedFile.facts and restore_metadata convert


def _text(value):
    return type(value) is str


def _count(value):
    return type(value) is int and value >= 0


def _path(value):
    try:
        return type(value) is str and ordinary(value) is not None
    except ValueError:
        return False


def _identity(value):
    return type(value) is list and len(value) == 3 and all(_count(part) for part in value)


def _write_time(value):
    """A write time restore_metadata sets exactly: whole 100-ns ticks of a positive 64-bit FILETIME (0.21.1 m-4)."""
    return type(value) is int and value % 100 == 0 and 0 < value // 100 + _FILETIME_EPOCH < 2 ** 63


def _attributes(value):
    """Attributes restore_metadata accepts: ARCHIVE and NORMAL only, as the edit requires of the original (0.21.1 m-4)."""
    return type(value) is int and value >= 0 and not value & ~0xA0


def _marker_bytes(value):
    """A journaled download marker, base64 text of 1 to MAX_MARKER bytes, as its bytes; anything else is None."""
    if type(value) is not str:
        return None
    try:
        raw = base64.b64decode(value, validate=True)
    except ValueError:
        return None
    return raw if 0 < len(raw) <= zone_identifier.MAX_MARKER else None


# Every field _edit writes into the intent, each with the values its undo can use. A row of any other shape is unresolved
# on its own book, never an exception that stops the engine from starting (0.21.0 M1), and its undo writes nothing
# (0.21.1 m-4). tests/test_inplace_m4b.py damages each key of a row the edit really wrote, so a new field fails it until
# it is listed here (0.21.1 F15: 'identity' was read by recovery but missing from this list).
_SHAPE = {'schema': lambda value: value == SCHEMA, 'job_id': _text, 'attempt_id': _text, 'path': _path, 'root': _path,
          'destination': _path, 'identity': _identity, 'size': _count, 'modified': _write_time, 'attributes': _attributes,
          'sha256': _text, 'type_offset': _count, 'appended_size': _count, 'appended_sha256': _text, 'output_size': _count,
          'output_sha256': _text, 'zone_marker': lambda value: value is None or _marker_bytes(value) is not None}


def _keyed(row):
    """A row the journal can address. SQLite admits NULL, or any type, in this non-INTEGER primary key (0.21.1 F16)."""
    return type(row['job_id']) is str and type(row['attempt_id']) is str


def _json_object(raw):
    """One journal column as a JSON object; SQL NULL, text that is not JSON, or any other JSON value raises Unresolved."""
    try:
        value = json.loads(raw) if isinstance(raw, (str, bytes)) else None
    except ValueError:
        value = None
    if not isinstance(value, dict):
        raise Unresolved(DAMAGED)
    return value


def _legacy_marker(detail):
    """0.21.0 journaled the marker bytes only in their removal receipt. A detail it cannot read restores none, as 0.21.0."""
    try:
        receipt = _json_object(detail).get('zone_marker')
    except Unresolved:
        return None
    value = receipt.get('marker_bytes_base64') if isinstance(receipt, dict) else None
    raw = _marker_bytes(value)
    return value if raw is not None and hashlib.sha256(raw).hexdigest() == receipt.get('marker_sha256') else None


def _intent(row):
    """The journaled intent, every field checked before recovery reads any of it or writes any byte."""
    intent = _json_object(row['intent'])
    if 'zone_marker' not in intent:  # a row 0.21.0 wrote
        intent = intent | {'zone_marker': _legacy_marker(row['detail'])}
    if any(key not in intent or not valid(intent[key]) for key, valid in _SHAPE.items()) or not (
            intent['type_offset'] <= intent['size'] - 4 and intent['size'] < intent['output_size']):
        raise Unresolved(DAMAGED)
    return intent


def _record(database, job_id, attempt_id, state, intent=None, detail=None):
    def write(db):
        ensure(db)
        row = db.execute('SELECT detail FROM inplace_edits WHERE job_id=? AND attempt_id=?', (job_id, attempt_id)).fetchone()
        if row is None:
            if intent is None:
                raise BoundaryError('In-place journal intent is missing')
            db.execute('INSERT INTO inplace_edits VALUES(?,?,?,?,?,?,?)', (job_id, attempt_id, intent['path'], state,
                       json.dumps(intent, sort_keys=True), json.dumps(detail or {}, sort_keys=True), _stamp()))
        else:
            try:
                kept = _json_object(row['detail'])
            except Unresolved:  # a damaged detail never stops the row from settling; its text is kept as evidence (M1)
                kept = {'damaged_detail': row['detail'] if isinstance(row['detail'], str) else repr(row['detail'])}
            merged = kept | (detail or {})
            db.execute('UPDATE inplace_edits SET state=?,detail=?,updated=? WHERE job_id=? AND attempt_id=?',
                       (state, json.dumps(merged, sort_keys=True), _stamp(), job_id, attempt_id))
    transaction(database, write)


class Session:
    """What the job layer lends one attempt: its catalog and identity, for the durable edit journal."""
    def __init__(self, database, job_id, attempt_id):
        self.database = str(database); self.job_id = job_id; self.attempt_id = attempt_id

    def record(self, state, intent=None, **detail):
        _record(self.database, self.job_id, self.attempt_id, state, intent, detail)


def offered(manifest):
    sources = manifest.get('sources') or []
    try:
        repairs = m4b_repair.approved_repairs(manifest)
    except ValueError:
        return False
    # Only a job whose frozen cleanup policy retires the original after verification may consume it. A policy that
    # keeps the sources (a manually approved M4B, a Retry child that keeps a retained checkpoint) keeps the copy flow.
    return (os.name == 'nt' and manifest.get('profile') == AUTOMATIC_PROFILE and len(sources) == 1
            and Path(sources[0]['path']).suffix.lower() == '.m4b' and not manifest.get('replacement_id') and not repairs
            and (manifest.get('cleanup_policy') or {}).get('enabled') is True
            # A recovery child (0.21.1 ruling 5) keeps the copy flow: its original stays a protected dependency of the
            # retained attempt until the old files are removed, so it is never edited or moved in place.
            and not (manifest.get('retry_intent') or {}).get('retained_checkpoint_id'))


@contextlib.contextmanager
def _before_write():
    try:
        yield
    except InterruptedError:
        raise
    except Ineligible:
        raise
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise Ineligible(str(error) or type(error).__name__) from error


def edit(manifest, stage, stop, progress, session):
    """An Edited (verified, held deny-writers, not yet moved), or None for the unchanged copy flow."""
    if session is None or not offered(manifest):
        return None
    try:
        return _edit(manifest, Path(stage), stop, progress, session)
    except Ineligible as error:
        progress('Checking sources', {'in_place': {'fallback': str(error)[:500]}})
        return None


def _hashes(handle, plan, stop):
    """One full read: the reviewed hash of the original and the hash the planned output will have."""
    original = hashlib.sha256(); output = hashlib.sha256(); offset = 0; patches = mp._patches(plan)
    for block in handle.chunks():
        if stop.is_set():
            raise ap.Paused('Operation paused; this book will restart')
        original.update(block); output.update(mp._patched(block, offset, patches)); offset += len(block)
    if offset != plan.source_size:
        raise Ineligible('Source length changed while it was hashed')
    output.update(plan.appended_movie)
    return original.hexdigest(), output.hexdigest()


def _byte_proof(handle, plan, intent, stop):
    """Audio untouched: [0, original size) with the type reverted is the reviewed file; the tail is the plan."""
    original = hashlib.sha256(); whole = hashlib.sha256(); tail = bytearray(); offset = 0
    revert = ((intent['type_offset'], b'moov'),)
    for block in handle.chunks():
        if stop.is_set():
            raise ap.Paused('Operation paused; this book will restart')
        whole.update(block); head = block[:max(0, plan.source_size - offset)]
        original.update(mp._patched(head, offset, revert)); tail += block[len(head):]; offset += len(block)
    if (offset != intent['output_size'] or original.hexdigest() != intent['sha256'] or bytes(tail) != plan.appended_movie
            or whole.hexdigest() != intent['output_sha256']):
        raise ap.ValidationError('In-place edit changed retained source bytes or differs from its plan')


def _covr(movie):
    """The single approved cover payload inside the appended movie bytes."""
    def child(data, kind, skip=0):
        found = [box for box in mp.boxes(data[skip:]) if box.kind == kind]
        mp.need(len(found) == 1, 'Appended metadata structure differs')
        return found[0].payload
    meta = child(child(mp.boxes(movie)[0].payload, b'udta'), b'meta')
    return child(child(child(meta, b'ilst', 4), b'covr'), b'data')[8:]


def _marker(path, size):
    """The original's download marker bytes, or None. They are journaled before the first write so every undo can put
    them back (0.21.1 m-3); any other named stream refuses."""
    found = zone_identifier.streams(path)
    if found == [('::$DATA', size)]:
        return None
    if len(found) == 2 and {name for name, _ in found} == {'::$DATA', zone_identifier.MARKER}:
        with open(str(path) + ':Zone.Identifier', 'rb') as stream:
            raw = stream.read(zone_identifier.MAX_MARKER + 1)
        if 0 < len(raw) <= zone_identifier.MAX_MARKER:
            return raw
        raise Ineligible('Unknown download marker size preserved')
    raise Ineligible('Additional filesystem streams require review')


def _same_volume(handle, root, destination):
    parent = destination.parent
    while not parent.exists():
        if parent == root or not parent.is_relative_to(root):
            return False
        parent = parent.parent
    with DirectoryBoundary(root, parent) as target:
        return target.identities[-1][1] == handle.info.volume


def _edited_original(handle, intent):
    """One full read before any undo write: [0, size) with the type reverted is the reviewed original. That alone proves
    the undo (cut to size, revert the 4 type bytes) yields the exact original, so the bytes past size are not judged: an
    append that is whole, torn, or zero-filled by a power loss at full length is cut off the same way (0.21.0 F12)."""
    original = hashlib.sha256(); offset = 0; revert = ((intent['type_offset'], b'moov'),)
    for block in handle.chunks():
        original.update(mp._patched(block[:max(0, intent['size'] - offset)], offset, revert)); offset += len(block)
    return offset >= intent['size'] and original.hexdigest() == intent['sha256']


def _undo(handle, intent, same_identity=True):
    """Restore the exact original: length, the 4 type bytes, the download marker, write time and attributes; prove the
    reviewed hash.

    Nothing is written until the file is proven to be the edited original (0.21.0 F3): always by its content against
    the journal, and by its native identity too, except in recovery, where a share may report a new file ID after
    reconnecting. A file that fails either proof is left exactly as found. A marker the edit removed is put back from its
    journaled bytes (0.21.1 m-3); one still present is left as it is."""
    facts = handle.refresh()
    if not intent['size'] <= facts['size'] <= intent['output_size'] or facts['links'] != 1:
        raise Unresolved('The edited source has an unexpected length or alias; it was not changed')
    if same_identity and facts['identity'] != intent['identity'] or not _edited_original(handle, intent):
        raise Unresolved('The file at the original path is not the edited original; it was not changed')
    marker = _marker_bytes(intent['zone_marker'])
    removed = marker is not None and zone_identifier.MARKER not in {name for name, _ in zone_identifier.streams(handle.path)}
    if facts['size'] != intent['size']:
        handle.truncate(intent['size'])
    if handle.read_at(intent['type_offset'], 4) != b'moov':
        handle.write_at(intent['type_offset'], b'moov')
    handle.flush()
    if removed:  # before the write time: writing a named stream moves the file's own write time
        zone_identifier.restore_marker(handle.path, marker)
    handle.restore_metadata(intent['modified'], intent['attributes']); handle.flush()
    facts = handle.refresh()
    if facts['size'] != intent['size'] or str(facts['modified']) != str(intent['modified']) or handle.sha256() != intent['sha256']:
        raise Unresolved('The original bytes could not be proven after the undo')


def _undo_released(held, path, intent):
    """Undo through a fresh writer: the rename's DELETE handle cannot also hold WRITE (its named proof shares DELETE only).
    A writer reopened by path must be the journaled identity, and _undo proves its content before it writes."""
    if held.get('final') is not None:
        held['final'].__exit__(None, None, None); held['final'] = None
    writer = held.get('writer')
    with contextlib.nullcontext(writer) if writer is not None else VerifiedFile(path, writable=True) as handle:
        _undo(handle, intent)


class Edited:
    """A verified in-place edit, still at the original path, held READ|DELETE deny-writers for the rename."""
    def __init__(self, path, stack, boundary, handle, validation, intent, session):
        self.path = path; self._stack = stack; self.boundary = boundary; self.handle = handle
        self.validation = validation; self.intent = intent; self.session = session

    def undo(self):
        """Before the move only. Raises Unresolved (journaled) when the original cannot be proven."""
        try:
            _undo_released({'final': self.handle}, self.path, self.intent)
        except Exception as error:
            self.session.record('unresolved', reason=str(error)[:500])
            raise Unresolved('In-place metadata edit could not be undone yet; the original is journaled for recovery: ' + str(error)) from error
        self.session.record('rolled_back')

    def close(self):
        self.handle.__exit__(None, None, None); self._stack.close()


def _edit(manifest, stage, stop, progress, session):
    item = manifest['sources'][0]; stack = contextlib.ExitStack(); held = {'writer': None, 'final': None}
    def release():
        for key in ('writer', 'final'):
            if held[key] is not None:
                held[key].__exit__(None, None, None); held[key] = None
        stack.close()
    try:
        with _before_write():
            source = ordinary(item['path']); root = ordinary(manifest['root'])
            out_root = ordinary(manifest.get('output_root', manifest['root'])); destination = ordinary(manifest['destination'])
            if destination.suffix.lower() != '.m4b' or not destination.is_relative_to(out_root) or os.path.normcase(str(destination)) == os.path.normcase(str(source)):
                raise Ineligible('Destination is not a distinct library M4B')
            if manifest.get('encoding_policy') != freeze_automatic_policy(manifest['sources']):
                raise Ineligible('Frozen automatic encoding policy changed')
            cover = ap.protected_cover(manifest, stage, stop).read_bytes(); tags = ap.preservation_tags(manifest)
            if hashlib.sha256(cover).hexdigest() != manifest['cover']['sha256']:
                raise Ineligible('Protected cover differs from reviewed artwork')
            boundary = stack.enter_context(DirectoryBoundary(root, source.parent))
            writer = held['writer'] = VerifiedFile(source, writable=True).__enter__()  # READ|WRITE, shared for reading only
            facts = writer.facts()
            if facts['links'] != 1 or facts['attributes'] & ~0xA0 or facts['size'] != item['size'] or str(facts['modified']) != str(item['modified']):
                raise Ineligible('Source identity, links or attributes do not allow an in-place edit')
            marker = _marker(source, facts['size'])
            plan = mp.plan(facts['size'], writer.read_at, tags, cover, frozenset())
            if plan.repairs or plan.tail_padding or plan.appended_media or plan.header_patches:
                raise Ineligible('This book needs a repair')
            if _covr(plan.appended_movie) != cover:
                raise Ineligible('Planned cover differs from reviewed artwork')
            if not _same_volume(writer, out_root, destination) or os.path.lexists(destination):
                raise Ineligible('Destination exists or is on another volume')
            if shutil.disk_usage(source.parent).free < len(plan.appended_movie) + 16 * 1024 * 1024:
                raise Ineligible('Insufficient library space for the appended metadata')
            raw = ap.probe(source, stage, stop); duration, profile = ap.audio_info(raw)
            audio = next(s for s in raw['streams'] if s.get('codec_type') == 'audio')
            encoding = choose_automatic_encoding([(*profile, audio.get('bit_rate'), audio.get('channel_layout'))], single_m4b=True)
            if encoding.get('mode') != 'copy' or encoding.get('codec') != 'aac':
                raise Ineligible('Only stream-copied AAC is edited in place')
            chapters = ap.source_chapters(source, stage, stop, duration)
            if manifest.get('source_chapters') != chapters:
                raise Ineligible('Existing M4B chapters differ from the frozen complete source plan')
            evidence = ap.copied_audio_evidence(source, stage, stop, duration, source_relative=True)
            original, expected = _hashes(writer, plan, stop)
            if original != item['sha256']:
                raise Ineligible('Source changed — review required')
        intent = {'schema': SCHEMA, 'job_id': manifest['job_id'], 'attempt_id': manifest['attempt_id'], 'path': str(source),
                  'root': str(root), 'destination': str(destination), 'identity': facts['identity'], 'size': facts['size'],
                  'modified': facts['modified'], 'attributes': facts['attributes'], 'sha256': original,
                  'type_offset': plan.movie_offset + 4, 'appended_size': len(plan.appended_movie),
                  'appended_sha256': hashlib.sha256(plan.appended_movie).hexdigest(),
                  'output_size': facts['size'] + len(plan.appended_movie), 'output_sha256': expected,
                  'zone_marker': base64.b64encode(marker).decode('ascii') if marker is not None else None}
        session.record('intended', intent)  # durable before the first written byte
    except BaseException:
        release(); raise
    try:
        source_proofs.forget(source)
        progress('Creating audio', {'encoding': encoding, 'source_metadata_preservation': True, 'in_place': True})
        # Ruling 27: the two writes and their journal step finish once begun; an update waits for them.
        with critical_sections.critical(critical_sections.TAG_EDIT):
            _fault('before_append')
            writer.write_at(plan.source_size, plan.appended_movie); _fault('appended'); writer.flush()
            _fault('before_type_patch')
            writer.write_at(intent['type_offset'], b'free'); writer.flush(); _fault('type_patched')
            session.record('written')
        progress('Checking output', {})
        raw = ap.probe(source, stage, stop); actual, profile = ap.audio_info(raw)
        if profile != ('aac', str(encoding['sample_rate']), encoding['channels']) or abs(actual - duration) > .25:
            raise ap.ValidationError('Preserved output audio profile is incorrect')
        if ap.source_chapters(source, stage, stop, duration) != chapters:
            raise ap.ValidationError('Preserved source chapter presentation changed')
        actual_tags = {key.lower(): str(value) for key, value in raw.get('format', {}).get('tags', {}).items()}
        if any(actual_tags.get(key, '') != str(value) for key, value in tags.items()):
            raise ap.ValidationError('Preserved output approved metadata differs')
        if ap.copied_audio_evidence(source, stage, stop, duration, source_relative=True) != evidence:
            raise ap.ValidationError('Preservation changed decoder, packets or presentation')
        _fault('checked', writer)
        writer.__exit__(None, None, None); held['writer'] = None  # readers cannot share a DELETE handle; reacquire below
        if marker is not None:
            def same(base):
                if base.facts()['identity'] != intent['identity'] or base.facts()['size'] != intent['output_size']:
                    raise BoundaryError('In-place source identity changed before its download marker removal')
            def persist(receipt):  # before the removal: only the marker the undo would put back is removed
                if receipt['marker_bytes_base64'] != intent['zone_marker']:
                    raise BoundaryError('Download marker changed during the in-place edit')
                session.record('written', zone_marker=receipt)
            zone_identifier.remove_marker(source, same, persist)
        final = held['final'] = VerifiedFile(source, delete=True).__enter__()  # READ|DELETE deny-writers, held through the rename
        _fault('reacquired')
        if final.facts()['identity'] != intent['identity'] or final.facts()['links'] != 1:
            raise ap.ValidationError('In-place source identity changed after the edit')
        _byte_proof(final, plan, intent, stop)
        if zone_identifier.streams(source) != [('::$DATA', intent['output_size'])]:
            raise ap.ValidationError('Additional filesystem streams appeared during the in-place edit')
        # The copy flow's last check of its output, the same refusal (Sergei: the fast path runs every check the copy flow runs)
        if ap.digest(manifest['cover']['path'], stop) != manifest['cover']['sha256']:
            raise ap.ValidationError('Selected cover changed — review required')
        session.record('written', verified=_stamp())
        receipt = mp.receipt(plan, original, expected) | {'all_retained_bytes_verified': True}
        validation = {'profile': manifest['profile'], 'encoding': encoding | {'selection': SELECTION}, 'publication_mode': MODE,
                      'duration': actual, 'expected_duration': duration, 'sha256': expected, 'size': intent['output_size'],
                      'chapters': chapters, 'preserved_source_chapters': chapters, 'source_durations': [duration],
                      'copied_audio_evidence': evidence, 'metadata_preservation': receipt, 'tags': actual_tags,
                      'in_place': {'schema': SCHEMA, 'original_sha256': original, 'original_size': intent['size'],
                                   'type_offset': intent['type_offset'], 'appended_sha256': intent['appended_sha256'],
                                   'all_retained_bytes_verified': True, 'decoded': False, 'zone_marker_removed': marker is not None},
                      'checks': 'Output checks passed', 'device': 'Apple Books sync not checked'}
        held['final'] = None  # owned by the Edited from here
        return Edited(source, stack, boundary, final, validation, intent, session)
    except Exception as failure:
        try:
            _undo_released(held, source, intent)
        except Exception as undo_error:
            release()
            session.record('unresolved', reason=str(undo_error)[:500])
            raise Unresolved('In-place metadata edit could not be undone yet; the original is journaled for recovery: ' + str(undo_error)) from failure
        release()
        session.record('rolled_back', failure=str(failure)[:500])
        if isinstance(failure, InterruptedError):
            raise
        progress('Checking sources', {'in_place': {'rolled_back': str(failure)[:500]}})
        return None
    except BaseException:
        release(); raise  # a crash: the journaled intent drives recovery


def _rows(database, where='', params=()):
    """Open edits, read-only: a catalog that never edited in place has no journal table and nothing to do."""
    with connect(database) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='inplace_edits'").fetchone():
            return []
        return [dict(row) for row in db.execute('SELECT * FROM inplace_edits WHERE state IN (?,?,?,?)' + where, OPEN + tuple(params))]


def _prove_move(intent, final_path):
    """The rename happened: the old path is absent and final_path holds exactly the planned output, fully hashed under a
    deny-writers handle (0.21.0 F2; a matching size alone proved nothing, F7). Returns a receipt published_move accepts."""
    old = ordinary(intent['path']); final = ordinary(final_path)
    if os.path.lexists(old):
        raise Unresolved('The edited original is still at its path; its move is not proven')
    with VerifiedFile(final) as handle:
        facts = handle.facts()
        if facts['links'] != 1 or facts['size'] != intent['output_size'] or handle.sha256() != intent['output_sha256']:
            raise Unresolved('The edited original is missing and its destination does not hold it')
    if os.path.lexists(old):
        raise Unresolved('The edited original is still at its path; its move is not proven')
    return {'schema': 'books-in-place-recovered-move-v1', 'old_path': str(old), 'final_path': str(final),
            'identity': facts['identity'], 'journaled_identity': intent['identity'], 'destination_native': facts,
            'sha256': intent['output_sha256'], 'size': intent['output_size'], 'old_absent': True, 'copy_fallback': False,
            'content_basis': 'Recovered: the full hash of the destination under a deny-writers handle equals the planned output',
            'recovered': _stamp()}


def reconcile(database, row):
    """Recovery for one open edit: undo it if the original is still at its path, else prove the move and record its receipt.

    'offline' (0.21.0 F13): the journaled library root cannot be seen, as when its share is not reconnected yet, so the
    original is not proven missing. Nothing is recorded; the row stays open for the next start or attempt. A visible root
    without the book's folder (renamed or deleted) is a missing original (0.21.1 F17). A row the journal cannot address is
    damaged; nothing is written or recorded, and unresolved() reports it on its own book (0.21.1 F16)."""
    try:
        if not _keyed(row):
            raise Unresolved(DAMAGED)
        intent = _intent(row); path = ordinary(intent['path'])
        if os.path.lexists(path):
            with DirectoryBoundary(intent['root'], path.parent), VerifiedFile(path, writable=True) as handle:
                _undo(handle, intent, same_identity=False)
            state, detail = 'rolled_back', {'recovered': _stamp()}
        elif os.path.lexists(intent['destination']):
            state, detail = 'published', {'rename': _prove_move(intent, intent['destination']), 'recovered_move': _stamp()}
        elif not os.path.isdir(intent['root']):
            return 'offline', {'root': intent['root']}
        else:
            raise Unresolved('The edited original is missing and its destination does not hold it')
    except (ValueError, OSError) as error:
        state, detail = 'unresolved', {'reason': str(error)[:500] or type(error).__name__}
    if _keyed(row):
        _record(database, row['job_id'], row['attempt_id'], state, detail=detail)
    return state, detail


def recover_all(database):
    """Startup: undo every interrupted edit before a scan or a new attempt can see a changed original. A row it cannot
    settle stays journaled 'unresolved' (see unresolved()); a catalog it cannot read or write raises."""
    return [reconcile(database, row) for row in _rows(database)]


ATTENTION = 'An interrupted in-place metadata edit of this book could not be undone yet: '


def unresolved(database):
    """{job_id: attention reason} for every edit recovery could not settle, and every row it cannot address (F16)."""
    found = {}
    for row in _rows(database):
        if type(row['job_id']) is not str or _keyed(row) and row['state'] != 'unresolved':
            continue
        try:
            reason = _json_object(row['detail']).get('reason') if _keyed(row) else DAMAGED
        except Unresolved as damaged:  # an 'unresolved' row recovery left untouched (offline) keeps its detail as found
            reason = str(damaged)
        found[row['job_id']] = ATTENTION + str(reason or 'unknown reason')
    return found


def clear(database, manifest):
    """Before an attempt: no source of this job may carry an unresolved in-place edit.

    An edit whose library root cannot be seen ('offline') does not refuse the attempt: that attempt cannot read the source
    either, and nothing writes to a source that differs from its review (an in-place edit first requires the reviewed
    size, write time and hash; the copy flow only reads it). The next attempt or start that can see the root settles it."""
    rows = _rows(database)
    if not rows:
        return
    names = {os.path.normcase(os.path.abspath(str(item.get('path', '')))) for item in manifest.get('sources', [])}
    for row in rows:
        # This job's own rows, and any edit of one of its sources. A row whose path column is damaged is matched by its job
        # alone, so it refuses only its own book's attempt, never another book's (0.21.0 M1).
        if row['job_id'] == manifest.get('job_id') or isinstance(row['path'], str) and os.path.normcase(row['path']) in names:
            state, detail = reconcile(database, row)
            if state == 'unresolved':
                raise Unresolved(ATTENTION + detail['reason'])


def published_move(database, job_id, path):
    """The journaled rename that retired this original into its output, or None. A damaged row proves no move, so source
    cleanup refuses this book on its own ("receipt is missing") instead of raising (0.21.0 M1)."""
    with connect(database) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='inplace_edits'").fetchone():
            return None
        rows = [dict(r) for r in db.execute("SELECT * FROM inplace_edits WHERE job_id=? AND state='published'", (job_id,))]
    for row in rows:
        try:
            rename = _json_object(row['detail']).get('rename')
        except Unresolved:
            continue
        if (_keyed(row) and isinstance(row['path'], str) and isinstance(rename, dict) and isinstance(rename.get('old_path'), str)
                and isinstance(rename.get('final_path'), str) and _identity(rename.get('identity')) and rename.get('old_absent') is True
                and os.path.normcase(row['path']) == os.path.normcase(path) == os.path.normcase(rename['old_path'])):
            return rename
    return None


def confirm_move(database, job_id, path, final_path):
    """Cleanup, when no receipt was journaled (a crash or a rename postcondition error after the rename, before
    startup recovery): prove the move into the job's current output, record its receipt and return it; else None."""
    with connect(database) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='inplace_edits'").fetchone():
            return None
        rows = [dict(r) for r in db.execute("SELECT * FROM inplace_edits WHERE job_id=? AND state IN ('publishing','published','unresolved')", (job_id,))]
    for row in rows:
        if not _keyed(row) or not isinstance(row['path'], str) or os.path.normcase(row['path']) != os.path.normcase(path):
            continue  # a row it cannot address cannot record a receipt either (F16)
        try:
            receipt = _prove_move(_intent(row), final_path)
        except (ValueError, OSError):
            continue  # damaged, or not this attempt's output; the caller refuses without a receipt
        _record(database, job_id, row['attempt_id'], 'published', detail={'rename': receipt, 'recovered_move': _stamp()})
        return receipt
    return None
