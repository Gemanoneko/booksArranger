"""Narrow source-preserving retry eligibility; never modifies a failed job."""
import hashlib
import json
import uuid
from pathlib import Path
from manifest_compatibility import equivalent_manifest

REASONS={
    # Exact zero-count text writer quirk; every original track byte is preserved.
    'M4B preservation requires review: Sample size table',
    'Remux changed the decoder configuration or relative audio packet timing',
    'M4B leading gaps or edit presentation require a verified preservation plan',
    # Raised by the old remux path's presentation proof, which byte-exact preservation does not use.
    'M4B presentation bounds cannot be verified',
    # Writer families now proven byte-exact (0.16.7); admission still requires a passing plan().
    'M4B preservation requires review: Unsupported/ambiguous brand',
    'M4B preservation requires review: Unsupported structural box',
    # Coverless sources: the movie start now excludes the added attached cover (0.16.7).
    'Preservation changed decoder, packets or presentation',
    # Refused by the old 262,144-chunk cap (raised in 0.16.7); admission still requires plan().
    'M4B preservation requires review: Table count/extent',
}
SCHEMA='m4b-metadata-preservation-v1'

def profile_proof(profile,module_sha256):
    """Compact JSON schema; each track hash still covers its entire native box."""
    tracks=[{'id':track['id'],'handler':track['handler'].decode('ascii'),
             'codec':track['codec'].decode('ascii'),'chap':list(track['chap']),
             'samples':track['samples'],'sha256':track['sha256']} for track in profile.tracks]
    proof={'schema':SCHEMA,'module_sha256':module_sha256,
           'movie_sha256':profile.movie_sha256,'tracks':tracks,
           'profile_only_not_pcm_verification':True}
    # Blank metadata the plan drops is part of what the admitted child will change.
    dropped=getattr(profile,'metadata_dropped',())
    if dropped:proof['metadata_dropped']=[dict(item) for item in dropped]
    notes=getattr(profile,'profile_notes',())
    if notes:proof['source_profile_notes']=[dict(item) for item in notes]
    return proof

def eligible(row):
    if row.get('reason') not in REASONS:return False
    return unpublished_single_m4b(row)

def unpublished_single_m4b(row):
    """Static rule shared with user-requested damage repair: a failed, unpublished,
    hash-consistent single-.m4b job that is not itself a repair or replacement child."""
    if row['state']!='needs attention' or row.get('output'):
        return False
    journal=json.loads(row['journal']);manifest=json.loads(row['manifest'])
    try:
        if str(uuid.UUID(row['job_id']))!=row['job_id'] or manifest.get('job_id')!=row['job_id']:return False
    except (ValueError,TypeError):return False
    if hashlib.sha256(json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=row['manifest_hash']:return False
    if 'publication_intent' in journal or manifest.get('m4b_repair') or manifest.get('replacement_id'):
        return False
    sources=manifest.get('sources',[])
    return len(sources)==1 and Path(sources[0]['path']).suffix.lower()=='.m4b' and bool(manifest.get('source_chapters') is not None)

def bind(parent, fresh, proof):
    """Require the identical reviewed manifest; add only the new repair relation."""
    if not eligible(parent):raise ValueError('Failure is outside the reviewed M4B repair cohort')
    prior=json.loads(parent['manifest'])
    if not equivalent_manifest(prior,fresh):raise ValueError('Frozen review/source/cover/policy changed; failed job preserved')
    if fresh['job_id']==parent['job_id']:raise ValueError('A repair needs a distinct job identity')
    if proof.get('schema')!=SCHEMA or len(proof.get('module_sha256',''))!=64 or not proof.get('tracks'):
        raise ValueError('Source-preservation profile proof is missing')
    result=dict(fresh)
    result['m4b_repair']={'schema':SCHEMA,'parent_job_id':parent['job_id'],
        'parent_manifest_hash':parent['manifest_hash'],
        'parent_journal_sha256':hashlib.sha256(parent['journal'].encode()).hexdigest(),
        'source_profile':proof,'one_child_per_failed_parent':True}
    return result
