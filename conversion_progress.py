"""Pure revision-bound approval/completion predicates; no media reads or mutations."""
import os
from pathlib import Path

def approved_scope(row,ctx,key_for):
    if ctx.get('automatic_pending'):return False
    if row.get('changed') or not all(ctx.get(k) for k in ('metadata_approved','source_coverage_confirmed','order_confirmed')):
        return False
    if row.get('conflicts') or not row.get('review') or not row.get('preview',{}).get('path'):return False
    members=row.get('members',[]);keys=[key_for(m['path']) for m in members]
    included=ctx.get('included',[]);order=ctx.get('track_order',[])
    if not included or len(set(included))!=len(included) or set(order)!=set(keys) or len(order)!=len(keys) or not set(included)<=set(keys):return False
    selected=[m for m,k in zip(members,keys) if k in included]
    if len(selected)==1 and Path(selected[0]['path']).suffix.lower()=='.m4b' and not ctx.get('metadata_facts'):return False
    if any(m.get('error') or m.get('missing') for m in members):return False
    albums={str({k.casefold():v for k,v in m.get('metadata',{}).get('tags',{}).items()}.get('album') or '').strip().casefold() for m in selected}
    if len(members)>1 and (len(albums)!=1 or not next(iter(albums),'').strip()) and not ctx.get('metadata_facts'):return False
    for m in selected:
        saved=ctx.get('source_hashes',{}).get(key_for(m['path']),{})
        value=saved.get('sha256','')
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value.lower()):return False
        if any(str(saved.get(k))!=str(m.get(k)) for k in ('size','modified')):return False
    return bool(ctx.get('cover_id') and any(c.get('id')==ctx['cover_id'] for c in ctx.get('cover_choices',[])))

def completed_book(row,ctx,job,source,storage,folders,output_current,key_for,modern_profile):
    if not output_current or job.get('state')!='completed':return False
    manifest=job['manifest'];record=job.get('output') or {}
    if manifest.get('candidate_id')!=row['id'] or manifest.get('candidate_revision')!=row['revision'] or manifest.get('metadata')!=row.get('review'):return False
    if record.get('validation',{}).get('passed') is not True or record.get('job_id')!=job['job_id']:return False
    if os.path.normcase(record.get('final_path',''))!=os.path.normcase(row['preview']['path']):return False
    sources=manifest.get('sources',[]);included=ctx.get('included',[])
    if [key_for(s['path']) for s in sources]!=[k for k in ctx.get('track_order',[]) if k in included]:return False
    if ctx.get('cover_id')!=manifest.get('cover',{}).get('id'):return False
    for s in sources:
        saved=ctx.get('source_hashes',{}).get(key_for(s['path']),{})
        if any(str(saved.get(k))!=str(s.get(k)) for k in ('sha256','size','modified')):return False
    policy=manifest.get('cleanup_policy',{})
    if (policy.get('enabled') or source) and (not source or source.get('state')!='completed'):return False
    if (manifest.get('profile') in ({modern_profile} if isinstance(modern_profile,str) else set(modern_profile)) or storage) and (not storage or storage.get('state')!='completed'):return False
    # Empty-folder housekeeping is separate from verified audiobook/file cleanup.
    return True

def phase_progress(phase,measurement=None):
    result={'phase':phase}
    if measurement and measurement.get('phase')=='encoding':
        result.update(phase='encoding',completed=measurement['completed'],total=measurement['total'])
    return result
