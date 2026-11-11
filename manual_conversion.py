"""Durable user-selected audiobook sources and immutable queue admission."""

import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import uuid

from audio_pipeline import INPUT_FORMATS, same_source
from chapter_plan import prepare as prepare_chapters
from encoding_policy import AUTOMATIC_PROFILE, freeze_automatic_policy
from metadata import future_audio_tags
from native_io import DirectoryBoundary, VerifiedFile, ordinary
from review_backend import member_key, source_hash, utc
from scanner import connect, fresh_stat, inside


TEXT_FIELDS = ('title', 'author', 'series', 'number', 'universe', 'collection', 'narrator', 'genre')
AUDIO_SUFFIXES = frozenset(INPUT_FORMATS) - {'.png', '.jpg', '.jpeg'}
MAX_TRACKS = 500
SOURCE_FACT_FIELDS = ('path', 'size', 'modified', 'dev', 'ino')


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def path_key(path):
    return os.path.normcase(os.path.abspath(path))


def source_keys(manifest):
    return {path_key(path) for source in manifest.get('sources', ())
            if isinstance(path := source.get('path'), str) and path}


def has_table(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE name='manual_conversions'").fetchone() is not None


def setup(db):
    db.execute('''CREATE TABLE IF NOT EXISTS manual_conversions(
        id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL, job_id TEXT UNIQUE,
        manifest TEXT, updated TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS manual_conversion_sources(
        path_key TEXT PRIMARY KEY, draft_id TEXT NOT NULL, root TEXT NOT NULL)''')
    db.execute('CREATE INDEX IF NOT EXISTS manual_conversion_sources_draft ON manual_conversion_sources(draft_id)')


def active_keys(db, root=None):
    if not has_table(db):
        return set()
    if root is not None:
        return {r[0] for r in db.execute('SELECT path_key FROM manual_conversion_sources WHERE root=?', (root,))}
    return {r[0] for r in db.execute('SELECT path_key FROM manual_conversion_sources')}


def manual_group(db, identity):
    return has_table(db) and db.execute('SELECT 1 FROM manual_conversions WHERE id=? AND job_id IS NOT NULL', (identity,)).fetchone() is not None


def grouping_inputs(db, root):
    if not has_table(db):
        return set(), set()
    manual_ids = {r[0] for r in db.execute('SELECT id FROM manual_conversions WHERE job_id IS NOT NULL')}
    blocked = {r[0] for r in db.execute('''SELECT s.path_key FROM manual_conversion_sources s
        JOIN manual_conversions d ON d.id=s.draft_id WHERE s.root=? AND d.job_id IS NOT NULL''', (root,))}
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='source_retirements'").fetchone():
        blocked.update(path_key(row[0]) for row in db.execute('''SELECT r.path FROM source_retirements r
            JOIN manual_conversions d ON d.job_id=r.job_id WHERE r.root=? AND r.state='removed' ''', (root,)))
    return manual_ids, blocked


def reserved_by(db, manifest):
    if not has_table(db):
        return None
    keys = source_keys(manifest)
    if not keys:
        return None
    return db.execute('''SELECT path_key,draft_id FROM manual_conversion_sources
        WHERE path_key IN (SELECT value FROM json_each(?)) AND draft_id!=? LIMIT 1''',
        (packed(sorted(keys)), manifest.get('manual_conversion', ''))).fetchone()


def exact_binding(db, manifest):
    identity = manifest.get('manual_conversion')
    if not identity or identity != manifest['candidate_id'] or not has_table(db):
        raise ValueError('Manual conversion binding is unavailable')
    row = db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone()
    frozen = {key: value for key, value in manifest.items() if key != 'attempt_id'}
    if not row or row['revision'] != frozen['candidate_revision'] or row['job_id'] != frozen['job_id'] or row['manifest'] != packed(frozen):
        raise ValueError('Saved manual conversion changed')
    return row


def output_allowed(db, job, root, final):
    if not has_table(db):
        return False
    row = db.execute('SELECT manifest FROM manual_conversions WHERE job_id=?', (job,)).fetchone()
    if not row:
        return False
    manifest = json.loads(row[0])
    return ordinary(manifest['output_root']) == root and ordinary(manifest['destination']) == final


def _uuid(value):
    try:
        return str(uuid.UUID(value))
    except (TypeError, ValueError, AttributeError):
        raise ValueError('Invalid manual draft identity') from None


def _revision(value):
    if type(value) is not int or value < 0:
        raise ValueError('Invalid manual draft revision')
    return value


def _path(value):
    if not isinstance(value, str) or not value or len(value) > 1000:
        raise ValueError('Choose an absolute Windows path')
    return ordinary(value)


def _track_paths(tracks):
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= MAX_TRACKS:
        raise ValueError(f'Choose between 1 and {MAX_TRACKS} audio tracks')
    paths = []
    for track in tracks:
        if not isinstance(track, dict) or set(track) != {'path', 'included'} or type(track['included']) is not bool:
            raise ValueError('Invalid manual track selection')
        path = _path(track['path'])
        if path.suffix.lower() not in AUDIO_SUFFIXES:
            raise ValueError(f'Unsupported audio file: {path.name}')
        paths.append({'path': str(path), 'included': track['included']})
    if len({path_key(track['path']) for track in paths}) != len(paths):
        raise ValueError('Each audio file can be selected only once')
    if not any(track['included'] for track in paths):
        raise ValueError('Include at least one audio file')
    return paths


def _metadata(values):
    if not isinstance(values, dict) or set(values) - {*TEXT_FIELDS, 'anthology'}:
        raise ValueError('Invalid manual metadata fields')
    result = {}
    for field in TEXT_FIELDS:
        value = values.get(field, '')
        if not isinstance(value, str) or len(value) > 1000 or '\0' in value:
            raise ValueError(f'Invalid {field}')
        result[field] = value.strip()
    if type(values.get('anthology', False)) is not bool:
        raise ValueError('Invalid short-story collection choice')
    result['anthology'] = values.get('anthology', False)
    return result


def _source(value):
    if isinstance(value, dict) and value == {'kind': 'files'}:
        return value
    if isinstance(value, dict) and set(value) == {'kind', 'path'} and value['kind'] == 'folder':
        return {'kind': 'folder', 'path': str(_path(value['path']))}
    raise ValueError('Choose a folder or audio files')


def _edit(value):
    required = {'id', 'revision', 'source', 'tracks', 'metadata', 'destination'}
    if not isinstance(value, dict) or not required <= value.keys() <= required | {'metadata_touched', 'inspections'}:
        raise ValueError('Invalid manual draft details')
    destination = value['destination']
    metadata = _metadata(value['metadata'])
    touched = value.get('metadata_touched', list(value['metadata']))
    if not isinstance(touched, list) or any(not isinstance(field, str) or field not in metadata for field in touched) or len(touched) != len(set(touched)):
        raise ValueError('Invalid edited metadata fields')
    inspections = value.get('inspections', [])
    if not isinstance(inspections, list) or len(inspections) > MAX_TRACKS or any(
        not isinstance(proof, str) or len(proof) != 64 or any(char not in '0123456789abcdef' for char in proof) for proof in inspections
    ):
        raise ValueError('Invalid source inspection proofs')
    return _uuid(value['id']), _revision(value['revision']), {
        'source': _source(value['source']), 'tracks': _track_paths(value['tracks']),
        'metadata': metadata, 'metadata_touched': sorted(touched),
        'destination': str(_path(destination)) if destination != '' else '',
    }, set(inspections)


class ManualConversions:
    def __init__(self, service):
        self.service = service
        self.inventory = service.inventory
        self._inspection_key = secrets.token_bytes(32)
        with connect(self.inventory.database) as db:
            setup(db)

    def _roots(self, paths):
        configured = tuple(ordinary(root) for root in self.inventory.source_roots())
        found = {next((root for root in configured if inside(path, root)), None) for path in paths}
        for path in paths:
            if any(inside(path, self.inventory.roots[label]) for label in ('Podcasts', 'Ebooks') if label in self.inventory.roots):
                raise ValueError('Choose audiobook sources outside the podcast and ebook libraries')
            if self.inventory.output_root and inside(path, self.inventory.output_root):
                raise ValueError('Choose source audio outside the sorted audiobook folder')
            if inside(path, self.service.cache_dir.parent):
                raise ValueError('Choose source audio outside Books Arranger’s data folder')
        if len(found) != 1:
            raise ValueError('Choose audio files within one audiobook source or one external folder')
        root = found.pop()
        if root is not None:
            return root, str(root)
        parents = {path.parent for path in paths}
        if len(parents) != 1:
            raise ValueError('Choose audio files from one folder outside the audiobook sources')
        return parents.pop(), str(configured[0])

    def _selection(self, data, read=False):
        selected = [ordinary(track['path']) for track in data['tracks'] if track['included']]
        source = data['source']
        if source['kind'] == 'folder' and any(path.parent != ordinary(source['path']) for path in selected):
            raise ValueError('Folder jobs include audio directly in the selected folder')
        root, catalog_root = self._roots(selected)
        files = []
        identities = set()
        for path in selected:
            with DirectoryBoundary(root.anchor, root), DirectoryBoundary(root, path.parent), VerifiedFile(path) as handle:
                facts = handle.facts()
                if facts['links'] != 1 or tuple(facts['identity']) in identities:
                    raise ValueError(f'Choose ordinary audio files with one filesystem link: {path.name}')
                identities.add(tuple(facts['identity']))
                stat = fresh_stat(path)
                item = {'path': str(path), 'size': stat.st_size, 'modified': str(stat.st_mtime_ns),
                        'dev': facts['dev'], 'ino': facts['ino']}
                if read:
                    item['metadata'] = self._read(path)
                    item['sha256'] = source_hash(path, stat)
            files.append(item)
        return str(root), catalog_root, files

    def _read(self, path):
        return self.inventory.reader(str(path), 'audiobook', threading.Event())

    def _inspection_proof(self, item):
        facts = [path_key(item['path']), *(item[field] for field in SOURCE_FACT_FIELDS[1:])]
        return hmac.digest(self._inspection_key, packed(facts).encode('utf-8'), 'sha256').hex()

    def _saved_edit(self, prior, data, root, catalog_root, files, inspections):
        previous = {path_key(item['path']): item for item in prior.get('source_facts', []) + prior.get('excluded_source_facts', [])}
        for item in files:
            original = previous.pop(path_key(item['path']), None)
            changed = original is None or any(original[field] != item[field] for field in SOURCE_FACT_FIELDS[1:])
            if changed and self._inspection_proof(item) not in inspections:
                if original is None and not inspections:
                    raise ValueError('Inspect source audio before saving or queuing. Load the folder or choose the files again.')
                raise ValueError(f'Source audio changed: {Path(item["path"]).name}. Load the folder or choose the files again to review it.')
        enriched = data | {'source_root': root, 'catalog_root': catalog_root, 'source_facts': files}
        excluded = [previous[key] for track in data['tracks'] if (key := path_key(track['path'])) in previous]
        if excluded:
            enriched['excluded_source_facts'] = excluded
        return enriched

    def inspect(self, request):
        import groups
        if isinstance(request, dict) and request.get('kind') == 'files' and set(request) == {'kind', 'paths'}:
            if not isinstance(request['paths'], list):
                raise ValueError('Choose audio files')
            tracks = _track_paths([{'path': path, 'included': True} for path in request['paths']])
            source = {'kind': 'files'}
        else:
            source = _source(request)
            if source['kind'] != 'folder':
                raise ValueError('Choose audio files')
            folder = ordinary(source['path'])
            with DirectoryBoundary(folder.anchor, folder):
                tracks = _track_paths([{'path': str(path), 'included': True} for path in folder.iterdir()
                                       if path.suffix.lower() in AUDIO_SUFFIXES and path.is_file()])
        tracks.sort(key=lambda track: (groups.natural(Path(track['path']).name), path_key(track['path'])))
        _, _, files = self._selection({'source': source, 'tracks': tracks})
        suggestions = self._suggestions(files)
        return {'source': source, 'tracks': tracks, 'suggestions': suggestions,
                'inspections': [self._inspection_proof(item) for item in files],
                'match_source': 'Matching embedded audio metadata' if suggestions else ''}

    def _suggestions(self, files):
        # Every file must corroborate a field. Track titles and artist alone do not identify a recording.
        if len(files) > 24:
            return {}
        try:
            tags = [{key.casefold(): val for key, val in self._read(Path(item['path'])).get('tags', {}).items()} for item in files]
        except (ValueError, OSError):
            return {}
        fields = {'title': ('album',), 'author': ('album_artist', 'author'), 'series': ('series',),
                  'number': ('series_number',), 'universe': ('universe',), 'collection': ('collection',),
                  'narrator': ('narrator',), 'genre': ('genre',)}
        result = {}
        for field, aliases in fields.items():
            values = [next((row[key].strip() for key in aliases if isinstance(row.get(key), str) and row[key].strip()), '') for row in tags]
            if values and values[0] and len(values[0]) <= 1000 and all(value.casefold() == values[0].casefold() for value in values):
                result[field] = values[0]
        return result

    def _destination(self, destination, source_root):
        if not destination:
            raise ValueError('Choose an export file with Save As')
        path = ordinary(destination)
        if path.suffix.lower() != '.m4b':
            raise ValueError('Choose an .m4b export filename')
        if any(inside(path, root) for root in (*self.inventory.all_source_roots(), source_root, self.service.cache_dir.parent)):
            raise ValueError('Choose an export path outside the source libraries and selected source folder')
        with DirectoryBoundary(path.anchor, path.parent):
            if os.path.lexists(path):
                raise ValueError(f'An output already exists at {path}. Choose a different path.')
        return path

    def _view(self, db, row):
        value = json.loads(row['data']) | {'id': row['id'], 'revision': row['revision'], 'state': 'draft'}
        value.pop('source_facts', None)
        value.pop('excluded_source_facts', None)
        value.pop('source_root', None)
        value.pop('catalog_root', None)
        if row['job_id'] is None:
            return value
        job = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (row['job_id'],)).fetchone()
        value.update(job_id=row['job_id'], candidate_id=row['id'])
        if not job:
            return value | {'state': 'failed', 'reason': 'The saved conversion job is unavailable'}
        state = {'pending': 'queued', 'running': 'running', 'needs attention': 'failed', 'completed': 'cleanup'}[job['state']]
        reason = job['reason']
        if state == 'cleanup':
            cleanup = db.execute('SELECT state,reason FROM source_cleanup WHERE job_id=?', (row['job_id'],)).fetchone()
            if cleanup:
                reason = cleanup['reason']
            if not reason:
                storage = db.execute('SELECT reason FROM storage_cleanup_jobs WHERE job_id=?', (row['job_id'],)).fetchone()
                if storage:
                    reason = storage['reason']
        elif state == 'queued' and not reason:
            import pause_state
            if (pause_state.read(db, 'jobs') or {}).get('origin') == 'user':
                reason = 'Waiting for audiobook jobs to resume'
            elif self.inventory.worker and self.inventory.worker.is_alive():
                reason = 'Waiting for the library scan to finish'
        journal = json.loads(job['journal'])
        reopen_allowed = state == 'failed' and self._failed_unowned(db, job)
        retry_allowed = reopen_allowed and journal.get('failure', {}).get('retryable') is True
        return value | {'state': state, 'reason': reason, 'stage': job['stage'], 'retry_allowed': retry_allowed,
                        'reopen_allowed': reopen_allowed}

    def list(self):
        with connect(self.inventory.database) as db:
            values = [self._view(db, row) for row in db.execute('SELECT * FROM manual_conversions ORDER BY updated DESC,id')]
        if any(value['state'] == 'cleanup' for value in values):
            converted = self.service.converted_ids()
            for value in values:
                if value['state'] == 'cleanup' and value['id'] in converted:
                    value['state'] = 'converted'
        return {'drafts': values}

    def _overlaps(self, db, files, identity):
        import audio_jobs
        from producer_recovery import protected_dependency
        keys = {path_key(item['path']) for item in files}
        owner = db.execute('''SELECT path_key,draft_id FROM manual_conversion_sources WHERE draft_id!=?
            AND path_key IN (SELECT value FROM json_each(?)) LIMIT 1''', (identity, packed(sorted(keys)))).fetchone()
        if owner:
            raise ValueError(f'{owner[0]} is reserved by manual draft {owner[1]}')
        if protected_dependency(db, [item['path'] for item in files]):
            raise ValueError('Selected audio is protected by an interrupted conversion. Resolve its recovery hold first.')
        for path, owner_job in db.execute('SELECT path,job_id FROM owned_artifacts'):
            if path_key(path) in keys:
                raise ValueError(f'{path} is an output or recovery file owned by job {owner_job}')
        overlap = []
        for job in db.execute('SELECT * FROM audio_jobs WHERE ' + audio_jobs.CURRENT):
            manifest = json.loads(job['manifest'])
            shared = next((path for item in manifest.get('sources', ())
                           if isinstance(path := item.get('path'), str) and path and path_key(path) in keys), None)
            if shared is None or manifest.get('manual_conversion') == identity:
                continue
            if job['state'] == 'completed' and db.execute("SELECT 1 FROM source_cleanup WHERE job_id=? AND state='completed'", (job['job_id'],)).fetchone():
                continue
            if job['state'] in ('running', 'completed') or job['output'] or self.service.jobs._claimed == job['job_id'] or 'publication_intent' in json.loads(job['journal']):
                raise ValueError(f'{shared} is already owned by audiobook job {job["job_id"]} ({job["state"]}). Check that job before retrying.')
            overlap.append((job, manifest))
        return overlap

    def _save(self, db, identity, revision, data, root, catalog_root, files, inspections):
        previous = db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone()
        prior = json.loads(previous['data']) if previous else {}
        if previous and previous['job_id']:
            raise ValueError('This manual conversion is already queued')
        enriched = self._saved_edit(prior, data, root, catalog_root, files, inspections)
        if prior == enriched and previous['revision'] in {revision, revision + 1}:
            return previous
        if (previous['revision'] if previous else 0) != revision:
            raise ValueError('Draft changed. Reopen its saved details and try again.')
        self._overlaps(db, files, identity)
        db.execute('DELETE FROM manual_conversion_sources WHERE draft_id=?', (identity,))
        db.executemany('INSERT INTO manual_conversion_sources VALUES(?,?,?)',
                       ((path_key(item['path']), identity, root) for item in files))
        db.execute('''INSERT INTO manual_conversions VALUES(?,?,?,NULL,NULL,?) ON CONFLICT(id) DO UPDATE SET
                      revision=excluded.revision,data=excluded.data,updated=excluded.updated''', (identity, revision + 1, packed(enriched), utc()))
        return db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone()

    def save(self, request):
        identity, revision, data, inspections = _edit(request)
        root, catalog_root, files = self._selection(data)
        with self.service.jobs._lock, connect(self.inventory.database) as db:
            db.execute('BEGIN IMMEDIATE')
            return {'draft': self._view(db, self._save(db, identity, revision, data, root, catalog_root, files, inspections))}

    def discard(self, request):
        if not isinstance(request, dict) or set(request) != {'id', 'revision'}:
            raise ValueError('Invalid manual draft identity')
        identity, revision = _uuid(request['id']), _revision(request['revision'])
        with self.service.jobs._lock, connect(self.inventory.database) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone()
            if row and (row['job_id'] or row['revision'] != revision):
                raise ValueError('Draft changed or is already queued')
            db.execute('DELETE FROM manual_conversion_sources WHERE draft_id=?', (identity,))
            db.execute('DELETE FROM manual_conversions WHERE id=?', (identity,))
        return {'discarded': True}

    def _cover(self, identity, review):
        from neutral_cover import neutral_cover
        from review_backend import image_kind

        authors = [review['author']] if review['author'] else []
        data = neutral_cover(review['title'], authors=authors)['bytes']
        sha = hashlib.sha256(data).hexdigest()
        cover_id = str(uuid.uuid5(uuid.UUID(identity), sha))
        reviews = self.service.reviews
        path = reviews.cache / (cover_id + '.' + image_kind(data))
        with DirectoryBoundary(reviews.cache.anchor, reviews.cache) as boundary:
            if boundary.identities != reviews.cache_identity:
                raise ValueError('Cover cache changed')
            try:
                with path.open('xb') as target:
                    target.write(data)
                    target.flush()
                    os.fsync(target.fileno())
            except FileExistsError:
                pass
            with VerifiedFile(path) as handle:
                if handle.sha256() != sha:
                    raise ValueError('Cached neutral cover changed')
        return {'id': cover_id, 'path': str(path), 'sha256': sha, 'source_label': 'Neutral cover',
                'thumbnail_url': '/api/cover?id=' + cover_id}

    def _plan(self, identity, data, root, destination, files):
        import groups
        from audio_pipeline import part_chapter_name, source_chapters, verified_source_chapters
        review = data['metadata'] | {'canonical_author': data['metadata']['author'],
                                    'original_language': 'Unknown', 'multi_author': False, 'topic': ''}
        if not review['title']:
            raise ValueError('Enter the title before queuing conversion')
        members = [groups.member(item | {'metadata': packed(item['metadata']), 'error': '', 'missing': 0}) for item in files]
        prepare_chapters(members)
        sources = [item | {'fingerprint': {key: item[key] for key in ('size', 'modified')}} for item in files]
        comments = future_audio_tags({}, review)['COMMENTS']
        for field, label in (('universe', 'Universe'), ('collection', 'Collection'), ('genre', 'Genre')):
            if review[field]:
                comments += ('\n' if comments else '') + f'{label}: {review[field]}'
        manifest = {'job_id': str(uuid.uuid4()), 'candidate_id': identity, 'manual_conversion': identity,
                    'sources': sources, 'metadata': review, 'destination': str(destination), 'root': root,
                    'output_root': str(destination.parent), 'profile': AUTOMATIC_PROFILE,
                    'encoding_policy': freeze_automatic_policy(sources), 'cover': self._cover(identity, review),
                    'comments': comments, 'chapters': [part_chapter_name(member) for member in members] if len(members) > 1 else [],
                    'cleanup_policy': {'enabled': True, 'empty_source_folders': False, 'recovery_retention_hours': 24,
                                       'recovery_root': str(self.service.cleanup.root)},
                    'evidence': {'metadata_actor': 'user', 'metadata_utc': utc(), 'track_actor': 'user',
                                 'track_basis': 'Selected files and playback order entered by you',
                                 'recording_completeness': 'unknown'}}
        stop = threading.Event()
        if len(sources) == 1 and Path(sources[0]['path']).suffix.lower() == '.m4b':
            duration = members[0]['duration']
            if duration is None:
                raise ValueError('Could not read source M4B duration')
            manifest['source_chapters'] = source_chapters(Path(sources[0]['path']), self.service.reviews.cache, stop, duration)
        elif len(sources) > 1:
            parts = []
            for member, source in zip(members, sources):
                path = Path(source['path'])
                duration = member['duration']
                part = {'name': part_chapter_name(member), 'chapters': []}
                if path.suffix.lower() in {'.m4a', '.m4b'} and duration is not None:
                    plan = verified_source_chapters(path, self.service.reviews.cache, stop, duration, source=source)
                    part['chapters'] = plan['chapters']
                    if plan['terminal_end_correction']:
                        part['terminal_end_correction'] = plan['terminal_end_correction']
                parts.append(part)
            if any(part['chapters'] for part in parts):
                manifest['part_chapters'] = parts
        return manifest, members

    def _project(self, db, manifest, members, catalog_root):
        import groups
        groups.setup(db)
        identity = manifest['candidate_id']
        review = manifest['metadata']
        scope = str(Path(members[0]['path']).parent) + '\x1fmanual:' + identity
        for order, member in enumerate(members):
            member.update(order=order, order_conflict=False, order_evidence='Selected order')
        evidence = {'scope': scope, 'title_clue': review['title'], 'artists': [review['author']] if review['author'] else [],
                    'languages': [], 'title_evidence': [review['title']], 'series_clues': [], 'conflicts': [],
                    'members': members, 'companions': [], 'metadata': {'tags': {}, 'title': review['title'], 'notes': []},
                    'order_unverified': False, 'membership_unverified': False, 'completeness_unverified': True,
                    'manual_conversion': True, 'manual_destination': manifest['destination']}
        raw = packed(evidence)
        db.execute('''INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence,review,approved)
                      VALUES(?,?,?,?,?,?,?,1)''', (identity, catalog_root, scope, manifest['candidate_revision'],
                      hashlib.sha256(raw.encode('utf-8')).hexdigest(), raw, packed(review)))
        binding = cleanup_binding(db, manifest)
        db.execute('INSERT INTO candidate_context VALUES(?,?,?)', (identity, manifest['candidate_revision'], packed(binding['context'])))

    def _admit(self, db, manifest, identity, revision, data, root, catalog_root, facts, members, inspections):
        saved = self._save(db, identity, revision, data, root, catalog_root, facts, inspections)
        if saved['revision'] != manifest['candidate_revision']:
            raise ValueError('Manual draft changed while the job was prepared')
        for job, _ in self._overlaps(db, facts, identity):
            if self._retained_work(db, job['job_id']):
                raise ValueError(f'Overlapping job {job["job_id"]} still owns working files. Resolve its working-file hold first.')
        db.execute('UPDATE manual_conversions SET job_id=?,manifest=?,updated=? WHERE id=?',
                   (manifest['job_id'], packed(manifest), utc(), identity))
        self._project(db, manifest, members, catalog_root)
        db.execute('DELETE FROM book_group_sync WHERE root=?', (catalog_root,))

    def settle_overlapping_jobs(self, manifest):
        import book_restart

        with self.service.jobs._lock, connect(self.inventory.database) as db:
            db.execute('BEGIN IMMEDIATE')
            exact_binding(db, manifest)
            row = db.execute('SELECT state,output FROM audio_jobs WHERE job_id=?', (manifest['job_id'],)).fetchone()
            if not row or row['state'] != 'completed' or not json.loads(row['output'] or '{}').get('validation', {}).get('passed'):
                raise ValueError('Overlapping jobs are held until the manual export is verified')
            for job, other in self._overlaps(db, manifest['sources'], manifest['candidate_id']):
                if self._retained_work(db, job['job_id']):
                    raise ValueError(f'Overlapping job {job["job_id"]} still owns working files. Originals were retained.')
                if db.execute('SELECT 1 FROM audio_job_set_aside WHERE job_id=?', (job['job_id'],)).fetchone() is None:
                    book_restart.set_aside(db, job['job_id'], other['candidate_id'], other['candidate_revision'], kind='manual_conversion')

    def queue(self, request):
        identity, revision, data, inspections = _edit(request)
        with connect(self.inventory.database) as db:
            prior = db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone()
            if prior and prior['job_id']:
                saved = json.loads(prior['data'])
                if all(saved[key] == value for key, value in data.items()):
                    return {'draft': self._view(db, prior)}
                raise ValueError('This manual conversion is already queued')
        root, catalog_root, files = self._selection(data, read=True)
        destination = self._destination(data['destination'], root)
        facts = [{key: item[key] for key in SOURCE_FACT_FIELDS} for item in files]
        saved = json.loads(prior['data']) if prior else {}
        enriched = self._saved_edit(saved, data, root, catalog_root, facts, inspections)
        manifest, members = self._plan(identity, data, root, destination, files)
        if prior and prior['revision'] != revision:
            raise ValueError('Draft changed. Reopen its saved details and try again.')
        manifest['candidate_revision'] = revision if prior and enriched == saved else revision + 1
        with self.service._review_boundary():
            with connect(self.inventory.database) as db:
                current = db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone()
                if current and current['job_id']:
                    if all(json.loads(current['data'])[key] == value for key, value in data.items()):
                        return {'draft': self._view(db, current)}
                    raise ValueError('This manual conversion is already queued')
            self.service.jobs.enqueue(manifest, manual_context=lambda db, frozen: self._admit(
                db, frozen, identity, revision, data, root, catalog_root, facts, members, inspections))
        self._resume()
        with connect(self.inventory.database) as db:
            return {'draft': self._view(db, db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone())}

    def _resume(self):
        from audio_jobs import StartRefused
        import pause_state
        self.service.invalidate_status()
        try:
            generation = self.service._capture_start_generation()
            with connect(self.inventory.database) as db:
                if (pause_state.read(db, 'jobs') or {}).get('origin') == 'user':
                    return
            try:
                self.service.resume(start_generation=generation)
            except StartRefused as refused:
                if refused.start_state == 'busy':
                    self.service.start_when_settled(start_generation=generation)
        except (ValueError, OSError):
            # The job is already durable. The normal Resume action starts it when the queue is available.
            pass

    @staticmethod
    def _retained_work(db, job_id):
        return (db.execute("SELECT 1 FROM working_attempts WHERE job_id=? AND (state!='retired' OR producer!='closed') LIMIT 1", (job_id,)).fetchone()
                or db.execute("SELECT 1 FROM working_files WHERE job_id=? AND state NOT IN ('removed','not_created','absent_after_intent') LIMIT 1", (job_id,)).fetchone()
                or db.execute('SELECT 1 FROM owned_artifacts WHERE job_id=? LIMIT 1', (job_id,)).fetchone()) is not None

    def _failed_unowned(self, db, job):
        return (job['state'] == 'needs attention' and not job['output'] and self.service.jobs._claimed != job['job_id']
                and 'publication_intent' not in json.loads(job['journal']) and not self._retained_work(db, job['job_id'])
                and not db.execute('SELECT 1 FROM source_cleanup WHERE job_id=?', (job['job_id'],)).fetchone())

    @staticmethod
    def _draft_request(request):
        if not isinstance(request, dict) or set(request) != {'id', 'revision'}:
            raise ValueError('Invalid manual draft identity')
        return _uuid(request['id']), _revision(request['revision'])

    def reopen(self, request):
        import book_restart

        identity, revision = self._draft_request(request)
        with self.service._review_boundary(), self.service.jobs._lock, connect(self.inventory.database) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone()
            if row and not row['job_id'] and row['revision'] == revision + 1:
                return {'draft': self._view(db, row)}
            if not row or row['revision'] != revision or not row['job_id']:
                raise ValueError('Open the current saved conversion before editing it')
            job = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (row['job_id'],)).fetchone()
            if not job or not self._failed_unowned(db, job):
                raise ValueError('This conversion still owns work or may have published an output. Its accepted plan is retained.')
            exact_binding(db, json.loads(job['manifest']))
            book_restart.set_aside(db, job['job_id'], identity, revision, kind='manual_edit')
            db.execute('DELETE FROM candidate_context WHERE id=?', (identity,))
            db.execute('DELETE FROM book_groups WHERE id=?', (identity,))
            db.execute('UPDATE manual_conversions SET revision=?,job_id=NULL,manifest=NULL,updated=? WHERE id=?', (revision + 1, utc(), identity))
            db.execute('DELETE FROM book_group_sync WHERE root=?', (json.loads(row['data'])['catalog_root'],))
            response = {'draft': self._view(db, db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone())}
        self.service._invalidate_manual_projection()
        return response

    def retry(self, request):
        identity, revision = self._draft_request(request)
        with self.service.jobs._lock, connect(self.inventory.database) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone()
            if not row or row['revision'] != revision or not row['job_id']:
                raise ValueError('Open the current saved conversion before retrying')
            job = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (row['job_id'],)).fetchone()
            if not job:
                raise ValueError('The saved conversion job is unavailable')
            manifest = json.loads(job['manifest'])
            exact_binding(db, manifest)
            if job['state'] == 'needs attention':
                journal = json.loads(job['journal'])
                if not self._failed_unowned(db, job) or journal.get('failure', {}).get('retryable') is not True:
                    raise ValueError('This conversion cannot be retried yet')
                self._destination(manifest['destination'], manifest['root'])
                db.execute("UPDATE audio_jobs SET state='pending',stage='queued',reason='',updated=? WHERE job_id=?", (utc(), job['job_id']))
            elif job['state'] != 'pending':
                raise ValueError('This conversion is already running or has a verified output')
        self._resume()
        with connect(self.inventory.database) as db:
            return {'draft': self._view(db, db.execute('SELECT * FROM manual_conversions WHERE id=?', (identity,)).fetchone())}

    def guard(self, manifest):
        with connect(self.inventory.database) as db:
            exact_binding(db, manifest)
            if reserved_by(db, manifest):
                return False
            keys = active_keys(db)
        if not all(path_key(source['path']) in keys for source in manifest['sources']):
            return False
        for source in manifest['sources']:
            with DirectoryBoundary(ordinary(manifest['root']).anchor, manifest['root']), DirectoryBoundary(manifest['root'], Path(source['path']).parent), VerifiedFile(source['path']) as handle:
                facts = handle.facts()
                if facts['links'] != 1 or (facts['dev'], facts['ino']) != (source['dev'], source['ino']):
                    return False
                same_source(source, threading.Event())
        return True

    def cleanup_output(self, manifest, path):
        with connect(self.inventory.database) as db:
            exact_binding(db, manifest)
        if ordinary(path) != ordinary(manifest['destination']):
            raise ValueError('The verified output is outside this manual job’s exact Save As path')
        if any(inside(path, root) for root in (*self.inventory.all_source_roots(), manifest['root'], self.service.cache_dir.parent)):
            raise ValueError('The output now overlaps a source or data folder. Originals were retained.')

    def release_cleaned(self, job_id):
        with connect(self.inventory.database) as db:
            db.execute('''DELETE FROM manual_conversion_sources WHERE draft_id IN
                          (SELECT d.id FROM manual_conversions d JOIN source_cleanup c ON c.job_id=d.job_id
                           WHERE d.job_id=? AND c.state='completed')''', (job_id,))


def cleanup_binding(db, manifest):
    exact_binding(db, manifest)
    cover = manifest['cover']
    order = [member_key(item['path']) for item in manifest['sources']]
    context = {'track_order': order, 'included': order, 'cover_id': cover['id'], 'cover_choices': [cover],
               'source_coverage_confirmed': True, 'order_confirmed': True, 'metadata_approved': True,
               'source_hashes': {key: {field: item[field] for field in ('size', 'modified', 'sha256', 'dev', 'ino')}
                                 for key, item in zip(order, manifest['sources'])},
               'metadata_actor': 'user', 'track_actor': 'user', 'chapters': bool(manifest['chapters']),
               'track_evidence': 'Selected files and playback order entered by you', 'user_approval': True}
    return {'context': context, 'review': manifest['metadata'], 'revision': manifest['candidate_revision']}
