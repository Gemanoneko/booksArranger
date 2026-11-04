"""Typed verification/cleanup work referring to one immutable existing publication.

The parent owns publication/location/output mutation. The child owns only its
duplicate sources, verification result and cleanup/recovery receipts. This module
does not open or delete files and never turns a pathname collision into proof.
"""
import copy
import hashlib
import json
import re
import uuid
from pathlib import Path

KIND='duplicate_source_cleanup'
RELATION='books-publication-reuse-v1'
RESULT='books-duplicate-verification-v1'


def packed(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(packed(value).encode('utf-8')).hexdigest()
def task(manifest):return isinstance(manifest,dict) and manifest.get('task_kind')==KIND
def result(value):return isinstance(value,dict) and value.get('schema')==RESULT


def setup(db):
    db.execute('CREATE TABLE IF NOT EXISTS duplicate_cleanup_tasks(candidate_id TEXT,source_fingerprint TEXT,parent_output_sha256 TEXT,job_id TEXT UNIQUE NOT NULL,PRIMARY KEY(candidate_id,source_fingerprint,parent_output_sha256))')


def _fail(reason):raise ValueError('Extra source kept: '+reason)


def _uuid(value):
    try:return isinstance(value,str) and str(uuid.UUID(value))==value
    except (ValueError,TypeError,AttributeError):return False


def _tracks(manifest):
    sources=manifest.get('sources');parts=manifest.get('part_chapters') or []
    if not isinstance(sources,list) or not sources:_fail('complete ordered sources are unavailable')
    out=[]
    for index,source in enumerate(sources):
        if not isinstance(source,dict) or not isinstance(source.get('path'),str):_fail('source correspondence is unavailable')
        sha=source.get('sha256');size=source.get('size')
        if not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha) or type(size)is not int or size<=0:_fail('source byte evidence is unavailable')
        chapters=[]
        if len(sources)==1 and Path(source['path']).suffix.lower()=='.m4b':chapters=manifest.get('source_chapters') or []
        elif len(parts)==len(sources):chapters=parts[index].get('chapters') or []
        out.append({'sha256':sha,'size':size,'chapters_sha256':digest(chapters)})
    return out


def source_scope(manifest):
    tracks=_tracks(manifest)
    return {'candidate_id':manifest.get('candidate_id'),'candidate_revision':manifest.get('candidate_revision'),
            'source_fingerprint':(manifest.get('metadata_facts') or {}).get('source_fingerprint'),
            'sources':[dict(track,path=source['path'],modified=str(source.get('modified')))
                       for source,track in zip(manifest['sources'],tracks)]}


def same_recording(child,parent):
    """Entire ordered byte/chapter scope plus accepted identity and known credits."""
    current=child.get('metadata_facts') or {};prior=parent.get('metadata_facts') or {}
    ids=current.get('work_ids');other=prior.get('work_ids')
    if not isinstance(ids,list) or not ids or ids!=other or len(set(ids))!=len(ids):return False
    if (current.get('collection') or {}).get('kind','single')!=(prior.get('collection') or {}).get('kind','single'):return False
    if _tracks(child)!=_tracks(parent):return False
    if child.get('chapters',[])!=parent.get('chapters',[]):return False
    now=child.get('metadata') or {};old=parent.get('metadata') or {}
    for key in ('narrator','number'):
        a=str(now.get(key) or '').strip().casefold();b=str(old.get(key) or '').strip().casefold()
        if a and b and a!=b:return False
    for key in ('recording_language','edition'):
        a=current.get(key) or {};b=prior.get(key) or {}
        a=a.get('value') if isinstance(a,dict) else a;b=b.get('value') if isinstance(b,dict) else b
        if a and b and str(a).casefold()!=str(b).casefold():return False
    # An explicit different title/author/series/world/cover asks for new choices;
    # silently deleting its sources would discard that request.
    entered=set((current.get('entered_names') or {}).get('fields') or [])
    for key in entered & {'title','author','series','number','universe'}:
        field='canonical_author' if key=='author' else key
        if now.get(field,'')!=old.get(field,''):return False
    if (current.get('cover') or {}).get('kind')=='retained_choice' and (child.get('cover') or {}).get('sha256')!=(parent.get('cover') or {}).get('sha256'):return False
    return True


def _parent(db,parent_id):
    if not _uuid(parent_id):_fail('the existing publication identity is invalid')
    raw=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent_id,)).fetchone()
    if not raw or raw['state']!='completed' or not raw['output']:_fail('the existing audiobook is not durably completed')
    row=dict(raw);manifest=json.loads(row['manifest']);output=json.loads(row['output'])
    if task(manifest) or result(output):_fail('a reuse chain is not publication proof')
    if row['manifest_hash']!=digest(manifest) or output.get('job_id')!=parent_id or (output.get('validation') or {}).get('passed') is not True:_fail('the existing publication receipt changed')
    from audio_jobs import AudioJobs
    from source_cleanup import CleanupJobs
    AudioJobs._validate_record(output);CleanupJobs._validation_contract(manifest,output)
    exists=lambda table:db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
    if exists('audiobook_replacements') and db.execute('SELECT 1 FROM audiobook_replacements WHERE parent_job_id=? OR replacement_job_id=?',(parent_id,parent_id)).fetchone():_fail('the existing audiobook has a replacement lineage requiring review')
    return row,manifest,output


def derive(db,manifest,parent_id):
    """Backend-derived admission relation; no filesystem/proof flags are trusted."""
    row,parent,output=_parent(db,parent_id)
    if not same_recording(manifest,parent):_fail('the complete recording no longer matches the arranged sources')
    eligible=[]
    for other in db.execute("SELECT job_id,manifest FROM audio_jobs WHERE state='completed' AND output IS NOT NULL"):
        candidate=json.loads(other['manifest'])
        if task(candidate):continue
        try:
            if same_recording(manifest,candidate):
                _parent(db,other['job_id']);eligible.append(other['job_id'])
        except (ValueError,KeyError,TypeError):continue
    if eligible!=[parent_id]:_fail('one unambiguous existing publication is required')
    scope=source_scope(manifest)
    if not _uuid(scope['candidate_id']) or type(scope['candidate_revision'])is not int or not scope['source_fingerprint']:_fail('the duplicate review binding is unavailable')
    return {'schema':RELATION,'parent_job_id':parent_id,'parent_manifest_sha256':row['manifest_hash'],
            'parent_output_sha256':digest(output),'source_scope':scope}


def admit(db,manifest):
    """Atomic queue admission; caller owns BEGIN IMMEDIATE and the queue lock."""
    capability=resolve(db,manifest)
    setup(db);relation=capability['relation'];scope=relation['source_scope']
    slot=(scope['candidate_id'],scope['source_fingerprint'],relation['parent_output_sha256'])
    prior=db.execute('SELECT job_id FROM duplicate_cleanup_tasks WHERE candidate_id=? AND source_fingerprint=? AND parent_output_sha256=?',slot).fetchone()
    if prior:
        if prior[0]!=manifest['job_id']:_fail('this source generation already has cleanup work')
        return
    db.execute('INSERT INTO duplicate_cleanup_tasks VALUES(?,?,?,?)',(*slot,manifest['job_id']))


def resolve(db,manifest,owner_job_id=None):
    """One capability with distinct immutable parent and child cleanup owners."""
    if not task(manifest):_fail('this is not a duplicate cleanup task')
    owner=owner_job_id or manifest.get('job_id')
    if not _uuid(owner) or manifest.get('job_id')!=owner:_fail('the cleanup owner changed')
    relation=manifest.get('publication_reuse')
    if not isinstance(relation,dict) or relation.get('schema')!=RELATION:_fail('the existing publication relation is unavailable')
    expected=derive(db,manifest,relation.get('parent_job_id'))
    if expected!=relation:_fail('the duplicate or publication receipt changed')
    row,parent,output=_parent(db,relation['parent_job_id'])
    return {'schema':RELATION,'cleanup_job_id':owner,'manifest':copy.deepcopy(manifest),
            'relation':copy.deepcopy(relation),'parent_job':row,'parent_manifest':parent,'parent_output':output}


def verification(capability,source_facts,location):
    """The worker's durable verification result; never an output/publication record."""
    return {'schema':RESULT,'cleanup_job_id':capability['cleanup_job_id'],'publication_reuse':copy.deepcopy(capability['relation']),
            'parent_output':copy.deepcopy(capability['parent_output']),'source_facts':copy.deepcopy(source_facts),
            'parent_location':copy.deepcopy(location)}


def checked_result(db,manifest,value,owner_job_id=None):
    capability=resolve(db,manifest,owner_job_id)
    if not result(value) or set(value)!={'schema','cleanup_job_id','publication_reuse','parent_output','source_facts','parent_location'}:_fail('the cleanup verification result is unavailable')
    if value['cleanup_job_id']!=capability['cleanup_job_id'] or value['publication_reuse']!=capability['relation'] or value['parent_output']!=capability['parent_output']:_fail('the cleanup verification owner or parent changed')
    facts=value['source_facts']
    if not isinstance(facts,list) or len(facts)!=len(manifest['sources']):_fail('the verified source scope is incomplete')
    for actual,source in zip(facts,manifest['sources']):
        if not isinstance(actual,dict) or actual.get('path')!=source['path'] or actual.get('sha256')!=source['sha256'] or actual.get('size')!=source['size'] or not actual.get('identity'):_fail('the verified source correspondence changed')
    child=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(capability['cleanup_job_id'],)).fetchone()
    if child and child['state']=='completed':
        if child['manifest_hash']!=digest(manifest) or json.loads(child['manifest'])!=manifest or json.loads(child['output'] or '{}')!=value or json.loads(child['journal']).get('duplicate_verification')!=value:_fail('the durable child verification receipt changed')
    return capability
