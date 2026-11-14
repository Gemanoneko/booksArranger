"""Classify an independently pinned copy census without assigning disposal rights."""
from collections import defaultdict
from pathlib import PureWindowsPath
import hashlib
import json
import re
import uuid

from review_backend import image_kind
from storage_relocation import _key, _relative


def _uuid(name, version):
    try:
        value = uuid.UUID(name)
    except (ValueError, AttributeError):
        return False
    return value.version == version and str(value) == name


def _diagnostic(name):
    return re.fullmatch(r'[0-9a-f]{32}\.(?:stdout|stderr)', name) and _uuid(
        str(uuid.UUID(name.split('.')[0])), 4)


def _image_provenance(member, read, candidates, sources):
    name = PureWindowsPath(member['relative'])
    if name.suffix not in ('.jpg', '.png') or not _uuid(name.stem, 5):
        return None
    if not 0 < member['facts']['size'] <= 8 * 1024 * 1024:
        return None
    data = read(member, 8 * 1024 * 1024)
    if len(data) != member['facts']['size'] or hashlib.sha256(data).hexdigest() != member['sha256']:
        return None
    try:
        if image_kind(data) != name.suffix[1:]:
            return None
    except ValueError:
        return None
    sha = member['sha256']
    proof = []
    for kind, inputs, domain in (
        ('embedded-candidate', candidates, ''), ('neutral-candidate', candidates, 'neutral:'),
        ('public-candidate', candidates, 'public-cover:'), ('book-source', sources, ''),
    ):
        proof.extend((kind, item) for item in inputs
                     if str(uuid.uuid5(uuid.NAMESPACE_URL, item + domain + sha)) == name.stem)
    return proof[0] if len(proof) == 1 else None


def _chapter_parent(data, repair, jobs):
    try:
        rows = [json.loads(line) for line in data.splitlines()]
        if not data.endswith(b'\n') or [row['state'] for row in rows] != [
            'intent', 'validated', 'copying', 'publishing', 'completed'
        ] or {row['job_id'] for row in rows} != {repair} or len({row['parent_job_id'] for row in rows}) != 1:
            return None
        parent = rows[0]['parent_job_id']
        job = jobs.get(parent)
        if not job or job[0] != 'completed' or not job[5]:
            return None
        manifest, output = json.loads(job[4]), json.loads(job[5])
        intent, validation, copying, publishing, completed = [row['data'] for row in rows]
        # Relocated publication parents require the existing native parent-binding
        # resolver. This offline classifier does not substitute for that authority.
        if intent.get('parent_location') is not None:
            return None
        original = PureWindowsPath(output['final_path'])
        style = validation.get('chapter_format', {}).get('description', {})
        modern = style.get('entry_size') == 65 and style.get('font_name') == 'Arial' and style.get('layout') == 'Apple QTFF legacy text'
        expected = str(original.with_name(original.stem + (' - Chapters v2.m4b' if modern else ' - Chapters.m4b')))
        if (intent['parent_output'], intent['parent_sha256'], intent['parent_size'],
            intent['parent_manifest_sha256'], intent.get('output_root', intent['root']), intent['mode']) != (
            str(original), output['sha256'], output['size'],
            hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            manifest.get('output_root', manifest['root']), 'copy existing validated AAC; source-track navigation'
        ):
            return None
        if any(intent[key] != manifest[key] for key in ('candidate_id','candidate_revision','sources','cover','root','profile')):
            return None
        if any(row['destination'] != expected for row in (intent, copying, publishing, completed)):
            return None
        if any(row['validation'] != validation for row in (copying, publishing, completed)):
            return None
        if (validation['chapters'], validation['cover_sha256'], validation['profile']) != (
                intent['chapters'], manifest['cover']['sha256'], manifest['profile']):
            return None
        return parent
    except (AttributeError, KeyError, TypeError, UnicodeError, ValueError):
        return None


def classify_retained_selection(members, scope, source_root, db, read):
    """Return per-member evidence classes. Unmatched members stay copy-only."""
    scope_path = PureWindowsPath(_relative(scope))
    root = PureWindowsPath(source_root) / scope_path
    selected = {}
    for member in members:
        path = PureWindowsPath(_relative(member['relative'])).relative_to(scope_path)
        key = _key(str(path))
        if key in selected:
            raise ValueError('Duplicate retained member')
        selected[key] = (path.parts, member)
    result = {}

    def classify(key, label, **evidence):
        result[key] = dict(relative=selected[key][1]['relative'], category=label,
                           resume_authority=False, disposal_authority=False, **evidence)

    candidates = {row[0] for row in db.execute('SELECT id FROM book_groups')}
    sources = {row[0] for row in db.execute('SELECT path FROM files')}
    jobs = {row[0]: row[1:] for row in db.execute(
        'SELECT job_id,state,stage,attempt_id,manifest_hash,manifest,output FROM audio_jobs')}
    attempts = {(job, attempt): (producer, state) for job, attempt, producer, state in db.execute(
        'SELECT job_id,attempt_id,producer,state FROM working_attempts')}
    intended = {(_key(path), job, attempt) for path, job, attempt in db.execute(
        "SELECT path,job_id,attempt_id FROM working_files WHERE state='creation_intended' "
        "AND COALESCE(sha256,'')='' AND COALESCE(size,0)=0")}
    preserved = {(_key(path), job) for path, job in db.execute(
        "SELECT path,job_id FROM storage_cleanup_preserved WHERE reason='Legacy evidence lacks exact producer bytes; preserved'")}

    stage_groups = defaultdict(list)
    repairs = defaultdict(list)
    cover_diagnostics = defaultdict(dict)
    for key, (parts, member) in selected.items():
        if len(parts) == 3 and parts[:2] == ('merge-cache', 'covers') and member['kind'] == 'file':
            name = parts[2]
            if _diagnostic(name) and 0 <= member['facts']['size'] <= (1024 * 1024 if name.endswith('.stderr') else 8 * 1024 * 1024):
                token, extension = name.split('.')
                cover_diagnostics[token][extension] = key
            else:
                origin = _image_provenance(member, read, candidates, sources)
                if origin:
                    classify(key, 'deterministic-cover-cache', origin=origin[0],
                             origin_sha256=hashlib.sha256(origin[1].encode('utf-8')).hexdigest())
        elif len(parts) in (4, 5) and parts[:2] == ('merge-cache', 'audio-staging') and all(_uuid(p,4) for p in parts[2:4]):
            stage_groups[parts[2:4]].append(key)
        elif len(parts) in (2, 3) and parts[0] == 'chapter-repairs' and _uuid(parts[1],4):
            repairs[parts[1]].append(key)
        elif parts == ('merge-cache', 'series-backfill') and member['kind'] == 'directory':
            classify(key, 'retained-series-backfill-root')

    for pair in cover_diagnostics.values():
        if set(pair) == {'stdout', 'stderr'}:
            for key in pair.values():
                classify(key, 'retained-cover-diagnostic-pair')

    for (job_id, attempt_id), keys in stage_groups.items():
        job = jobs.get(job_id)
        if job is None:
            continue
        terminal_history = job[0] == 'completed' and (job_id, attempt_id) not in attempts
        closed_attention = (job[0] == 'needs attention' and job[2] == attempt_id and
                            attempts.get((job_id, attempt_id)) in {('closed', 'closed'), ('closed', 'attention')})
        if not (terminal_history or closed_attention):
            continue
        for key in keys:
            parts, member = selected[key]
            path = _key(str(root.joinpath(*parts)))
            if len(parts) == 5 and member['kind'] == 'file':
                if terminal_history and (path, job_id) in preserved:
                    classify(key, 'retained-legacy-stage', job_id=job_id, attempt_id=attempt_id)
                if closed_attention and (path, job_id, attempt_id) in intended:
                    classify(key, 'retained-unconfirmed-stage', job_id=job_id, attempt_id=attempt_id)
        # Directory classification records history only. Full directory census and
        # the selected pin still govern whether the directory can be copied.
        for key in keys:
            parts, member = selected[key]
            if len(parts) == 4 and member['kind'] == 'directory':
                classify(key, 'retained-closed-stage-directory', job_id=job_id, attempt_id=attempt_id)

    for repair, keys in repairs.items():
        journal = _key(str(PureWindowsPath('chapter-repairs',repair,'corrected-artifact.jsonl')))
        if journal not in keys:
            continue
        member = selected[journal][1]
        if member['kind'] != 'file' or not 0 < member['facts']['size'] <= 2 * 1024 * 1024:
            continue
        data = read(member, 2 * 1024 * 1024)
        if len(data) != member['facts']['size'] or hashlib.sha256(data).hexdigest() != member['sha256']:
            continue
        parent = _chapter_parent(data, repair, jobs)
        if parent is None:
            continue
        for key in keys:
            parts, member = selected[key]
            if key == journal or len(parts) == 2 and member['kind'] == 'directory':
                classify(key, 'retained-completed-chapter-evidence', repair_id=repair, parent_job_id=parent)
            elif (len(parts) == 3 and member['kind'] == 'file' and
                  (parts[2] == 'chapters.txt' or _diagnostic(parts[2])) and member['facts']['size'] <= 8 * 1024 * 1024):
                classify(key, 'retained-chapter-diagnostic', repair_id=repair, parent_job_id=parent)
    return result
