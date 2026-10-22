"""Single-M4B in-place metadata edit (0.21.0).

The copy flow's own preservation plan, applied to the original instead of a staged copy: the planned
moov is appended after the original end of file, then the old moov's 4-byte type becomes 'free'. No
mdat/audio byte moves, so the result is byte-identical to the copy flow's checked.m4b.

Eligibility is the copy flow's own route into metadata preservation (automatic profile, one .m4b
whose AAC audio is stream-copied, no approved repair, a preservation plan that needs no repair), plus
what an in-place edit needs (one ordinary link, a held deny-writers handle, a same-volume destination,
no foreign named streams). Any refusal before the first written byte returns None and the copy flow
runs unchanged. After the first write, every failure undoes the edit (length, the 4 type bytes,
write time and attributes, then a full-hash proof) before anything else. A crash leaves an
inplace_edits row that recovery undoes at startup and before any new attempt on that source.

No decode is performed (Sergei, 2026-10-22). Audio integrity rests on the byte proof: with the 4
type bytes reverted, the file's original extent hashes to the reviewed SHA-256, and the appended
bytes equal the plan.
"""
import contextlib
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
    """Before any write: the copy flow runs unchanged."""


class Unresolved(ap.ValidationError):
    """The edit began and its undo is not proven yet; the journal keeps it for recovery."""


def _fault(point, handle=None):
    """Test seam only: a named step of the write sequence (with its open writer, where one is held)."""


def _stamp():
    return datetime.now(timezone.utc).isoformat()


def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS inplace_edits(job_id TEXT,attempt_id TEXT,path TEXT,state TEXT,intent TEXT,detail TEXT,updated TEXT,PRIMARY KEY(job_id,attempt_id))')


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
            merged = json.loads(row['detail']) | (detail or {})
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
            and (manifest.get('cleanup_policy') or {}).get('enabled') is True)


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
    found = zone_identifier.streams(path)
    if found == [('::$DATA', size)]:
        return False
    if len(found) == 2 and {name for name, _ in found} == {'::$DATA', zone_identifier.MARKER}:
        return True
    raise Ineligible('Additional filesystem streams require review')


def _same_volume(handle, root, destination):
    parent = destination.parent
    while not parent.exists():
        if parent == root or not parent.is_relative_to(root):
            return False
        parent = parent.parent
    with DirectoryBoundary(root, parent) as target:
        return target.identities[-1][1] == handle.info.volume


def _undo(handle, intent, proven_identity=True):
    """Restore the exact original: length, the 4 type bytes, write time and attributes; prove the reviewed hash."""
    facts = handle.refresh()
    if not intent['size'] <= facts['size'] <= intent['output_size'] or facts['links'] != 1:
        raise Unresolved('The edited source has an unexpected length or alias; it was not changed')
    if not proven_identity and facts['identity'] != intent['identity']:
        # A share may report a new file ID after reconnecting: prove the content is our original before changing it.
        digest = hashlib.sha256(); offset = 0
        for block in handle.chunks():
            head = block[:max(0, intent['size'] - offset)]
            digest.update(mp._patched(head, offset, ((intent['type_offset'], b'moov'),))); offset += len(block)
        if digest.hexdigest() != intent['sha256']:
            raise Unresolved('The file at the original path is not the edited original; it was not changed')
    if facts['size'] != intent['size']:
        handle.truncate(intent['size'])
    if handle.read_at(intent['type_offset'], 4) != b'moov':
        handle.write_at(intent['type_offset'], b'moov')
    handle.flush(); handle.restore_metadata(intent['modified'], intent['attributes']); handle.flush()
    facts = handle.refresh()
    if facts['size'] != intent['size'] or str(facts['modified']) != str(intent['modified']) or handle.sha256() != intent['sha256']:
        raise Unresolved('The original bytes could not be proven after the undo')


def _undo_released(held, path, intent):
    """Undo through a fresh writer: the rename's DELETE handle cannot also hold WRITE (its named proof shares DELETE only)."""
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
                  'output_size': facts['size'] + len(plan.appended_movie), 'output_sha256': expected}
        session.record('intended', intent)  # durable before the first written byte
    except BaseException:
        release(); raise
    try:
        source_proofs.forget(source)
        progress('Creating audio', {'encoding': encoding, 'source_metadata_preservation': True, 'in_place': True})
        _fault('before_append')
        writer.write_at(plan.source_size, plan.appended_movie); _fault('appended'); writer.flush()
        _fault('before_type_patch')
        writer.write_at(intent['type_offset'], b'free'); writer.flush(); _fault('type_patched')
        session.record('written'); progress('Checking output', {})
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
        if marker:
            def same(base):
                if base.facts()['identity'] != intent['identity'] or base.facts()['size'] != intent['output_size']:
                    raise BoundaryError('In-place source identity changed before its download marker removal')
            zone_identifier.remove_marker(source, same, lambda receipt: session.record('written', zone_marker=receipt))
        final = held['final'] = VerifiedFile(source, delete=True).__enter__()  # READ|DELETE deny-writers, held through the rename
        _fault('reacquired')
        if final.facts()['identity'] != intent['identity'] or final.facts()['links'] != 1:
            raise ap.ValidationError('In-place source identity changed after the edit')
        _byte_proof(final, plan, intent, stop)
        if zone_identifier.streams(source) != [('::$DATA', intent['output_size'])]:
            raise ap.ValidationError('Additional filesystem streams appeared during the in-place edit')
        session.record('written', verified=_stamp())
        receipt = mp.receipt(plan, original, expected) | {'all_retained_bytes_verified': True}
        validation = {'profile': manifest['profile'], 'encoding': encoding | {'selection': SELECTION}, 'publication_mode': MODE,
                      'duration': actual, 'expected_duration': duration, 'sha256': expected, 'size': intent['output_size'],
                      'chapters': chapters, 'preserved_source_chapters': chapters, 'source_durations': [duration],
                      'copied_audio_evidence': evidence, 'metadata_preservation': receipt, 'tags': actual_tags,
                      'in_place': {'schema': SCHEMA, 'original_sha256': original, 'original_size': intent['size'],
                                   'type_offset': intent['type_offset'], 'appended_sha256': intent['appended_sha256'],
                                   'all_retained_bytes_verified': True, 'decoded': False, 'zone_marker_removed': bool(marker)},
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


def reconcile(database, row):
    """Recovery for one open edit: undo it if the original is still at its path, else confirm the move."""
    intent = json.loads(row['intent']); path = ordinary(intent['path'])
    try:
        if os.path.lexists(path):
            with DirectoryBoundary(intent['root'], path.parent), VerifiedFile(path, writable=True) as handle:
                _undo(handle, intent, proven_identity=False)
            state, detail = 'rolled_back', {'recovered': _stamp()}
        elif os.path.lexists(intent['destination']) and os.path.getsize(intent['destination']) == intent['output_size']:
            state, detail = 'published', {'recovered_move': _stamp()}  # the job's own publication record proves the bytes
        else:
            raise Unresolved('The edited original is missing and its destination does not hold it')
    except (ValueError, OSError) as error:
        state, detail = 'unresolved', {'reason': str(error)[:500]}
    _record(database, row['job_id'], row['attempt_id'], state, detail=detail)
    return state, detail


def recover_all(database):
    """Startup: undo every interrupted edit before a scan or a new attempt can see a changed original."""
    return [reconcile(database, row) for row in _rows(database)]


def clear(database, manifest):
    """Before an attempt: no source of this job may carry an unresolved in-place edit."""
    rows = _rows(database)
    if not rows:
        return
    names = {os.path.normcase(os.path.abspath(str(item.get('path', '')))) for item in manifest.get('sources', [])}
    for row in rows:
        if os.path.normcase(row['path']) in names:
            state, detail = reconcile(database, row)
            if state == 'unresolved':
                raise Unresolved('An interrupted in-place metadata edit of this book could not be undone yet: ' + detail['reason'])


def published_move(database, job_id, path):
    """The journaled rename that retired this original into its output, or None."""
    with connect(database) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='inplace_edits'").fetchone():
            return None
        rows = [dict(r) for r in db.execute("SELECT * FROM inplace_edits WHERE job_id=? AND state='published'", (job_id,))]
    for row in rows:
        rename = json.loads(row['detail']).get('rename') or {}
        if os.path.normcase(row['path']) == os.path.normcase(path) and rename.get('old_absent') is True and os.path.normcase(rename.get('old_path', '')) == os.path.normcase(path):
            return rename
    return None
