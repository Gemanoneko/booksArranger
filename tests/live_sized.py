"""A live-sized catalog for list and status timing tests (0.22.1), grown from one real converted fixture book.

Sergei's catalog on 2026-10-25: 1,572 current books, 512 approved, 657 jobs (508 finished), 2,950 research records. The
fixture's one converted book (its file row, group review, context, job and research record) is cloned in SQL into that
many books, each in its own (absent) folder of the same source root, so every count the list and the status computation
walk is live-sized. The clones are catalog rows only: no file is created, read or written.
"""
import json
import uuid
from pathlib import Path

from review_backend import member_key
from scanner import connect

LIVE = {'books': 1572, 'approved': 512, 'finished': 508, 'records': 2950}


def _swap(value, old, new):
    """value with every occurrence of the strings in `old` replaced by the matching `new` (JSON text)."""
    text = json.dumps(value, ensure_ascii=False)
    for a, b in zip(old, new):
        text = text.replace(json.dumps(a, ensure_ascii=False)[1:-1], json.dumps(b, ensure_ascii=False)[1:-1])
    return json.loads(text)


def grow(inventory, books=LIVE['books'], approved=LIVE['approved'], finished=LIVE['finished'], records=LIVE['records']):
    """Clone the catalog's one converted book. Returns the new candidate ids, approved ones first."""
    with connect(inventory.database) as db:
        job = dict(db.execute("SELECT * FROM audio_jobs WHERE state='completed'").fetchone())
        manifest = json.loads(job['manifest'])
        group = dict(db.execute('SELECT * FROM book_groups WHERE id=?', (manifest['candidate_id'],)).fetchone())
        members = json.loads(group['evidence'])['members']
        if len(members) != 1:
            raise ValueError('grow() clones a one-file book')
        source = dict(db.execute('SELECT * FROM files WHERE root=? AND path=?', (group['root'], members[0]['path'])).fetchone())
        context = json.loads(db.execute('SELECT data FROM candidate_context WHERE id=?', (group['id'],)).fetchone()[0])
        record = db.execute('SELECT * FROM automatic_candidates WHERE id=?', (group['id'],)).fetchone()
        record = dict(record) if record else None
        old_path = Path(source['path'])
        paths = [str(old_path.parent.parent / ('Клон %04d' % n) / old_path.name) for n in range(books)]
        db.executemany('INSERT INTO files(root,path,size,modified,seen,kind,arrival,metadata,error,missing,review) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       [(source['root'], path, source['size'], source['modified'], source['seen'], source['kind'], source['arrival'],
                         source['metadata'], '', 0, source['review']) for path in paths])
    rows = inventory.candidates('Audiobooks', limit=1000000)['rows']  # the groups are rebuilt for the new files
    by_path = {row['members'][0]['path']: row for row in rows if len(row['members']) == 1}
    ids = [by_path[path]['id'] for path in paths]
    old = [str(old_path), member_key(str(old_path)), group['id'], group['fingerprint']]
    with connect(inventory.database) as db:
        for n, (path, identity) in enumerate(zip(paths, ids)):
            new = [path, member_key(path), identity, by_path[path]['fingerprint']]
            if n < approved:
                revision = by_path[path]['revision']
                db.execute('UPDATE book_groups SET review=? WHERE id=?', (group['review'], identity))
                db.execute('INSERT OR REPLACE INTO candidate_context VALUES(?,?,?)', (identity, revision, json.dumps(_swap(context, old, new), ensure_ascii=False)))
            if n < finished:
                job_id = str(uuid.uuid4())
                clone_manifest = _swap(manifest, old + [job['job_id']], new + [job_id])
                clone_manifest['candidate_revision'] = by_path[path]['revision']
                output = _swap(json.loads(job['output']), old + [job['job_id']], new + [job_id])
                output['final_path'] = str(Path(output['final_path']).parent / ('Клон %04d.m4b' % n))
                db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                           (job_id, json.dumps(clone_manifest, ensure_ascii=False), job['manifest_hash'], 'completed', 'completed', None,
                            job['journal'], json.dumps(output, ensure_ascii=False), '', job['created'], job['updated']))
            if record and n < records:
                fingerprint = by_path[path]['fingerprint']
                db.execute('INSERT OR REPLACE INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',
                           (identity, by_path[path]['revision'], fingerprint, 'Held', record['result'], None, record['attempted'], record['matcher_version']))
    return ids
