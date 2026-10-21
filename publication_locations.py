"""Pure SQLite publication relocation bindings. No filesystem action or verification.

Original receipts remain provenance. Effective locations are a separate envelope;
callers retain their catalog generation lease through any destructive decision.
A stored proof is never current native/media verification by itself.
"""
import copy
import hashlib
import json
import ntpath
import re
import sqlite3
import uuid
from datetime import datetime, timezone

SCHEMA='books-output-relocation-v1'
PROOF_SCHEMA='books-output-location-proof-v1'
KINDS=frozenset({'base','Chapters','Chaptersv2','replacement'})
STAGES=('planned','copy_intent','copied','temporary_verified','final_publish_intent','final_published',
        'location_committed','old_removal_intent','original_removed','complete')
COMMITTED=frozenset(STAGES[6:])

class PublicationRefused(ValueError):
    def __init__(self,code,message):super().__init__(message);self.code=code;self.cause=code


def _need(value,message,code='invalid_publication_binding'):
    if not value:raise PublicationRefused(code,message)


def _packed(value):
    try:return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    except (ValueError,TypeError) as error:raise PublicationRefused('invalid_publication_binding','Noncanonical publication JSON') from error


def _digest(value):return hashlib.sha256(_packed(value).encode('utf-8')).hexdigest()
def _now():return datetime.now(timezone.utc).isoformat()
def _object(value):
    try:result=json.loads(value) if isinstance(value,str) else copy.deepcopy(value)
    except (ValueError,TypeError) as error:raise PublicationRefused('invalid_publication_binding','Malformed publication JSON') from error
    _need(isinstance(result,dict),'Publication object required');return json.loads(_packed(result))


def _path(value):
    _need(isinstance(value,str) and bool(value),'Publication path required')
    name=value.replace('/',chr(92));drive,tail=ntpath.splitdrive(name)
    _need(bool(drive) and tail.startswith(chr(92)) and not name.startswith((chr(92)*2+'?'+chr(92),chr(92)*2+'.'+chr(92))),'Ordinary absolute publication path required')
    parts=[part for part in tail.split(chr(92)) if part]
    _need(all(part not in {'.','..'} and not part.endswith(('.', ' ')) and not re.search(r'[<>:"|?*\x00-\x1f]',part) for part in parts),'Unsafe publication path')
    reserved={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
    _need(all(part.split('.')[0].upper() not in reserved for part in parts),'Device-shaped publication path')
    return ntpath.normcase(ntpath.normpath(name))


def _contained(root,path):
    root=_path(root);path=_path(path)
    try:return path!=root and ntpath.commonpath([root,path])==root
    except ValueError:return False


def _hash(value):return isinstance(value,str) and bool(re.fullmatch('[0-9a-f]{64}',value))
def _size(value):return type(value) is int and value>0

def _native(value):
    return isinstance(value,(list,tuple)) and len(value)==3 and all(type(v) is int and v>=0 for v in value) and value[0]>0 and any(value[1:])


def _ancestry(value,root,path):
    _need(isinstance(value,list) and bool(value),'Publication parent identities required')
    seen=[]
    for item in value:
        _need(isinstance(item,(list,tuple)) and len(item)==4 and _native(list(item[1:])),'Malformed publication parent identity')
        seen.append(_path(item[0]))
    _need(len(set(seen))==len(seen) and _path(root) in seen and seen[-1]==ntpath.dirname(_path(path)),'Publication ancestry does not bind its root and final parent')
    for left,right in zip(seen,seen[1:]):
        _need(ntpath.dirname(right)==left,'Publication ancestry is not contiguous')


def _receipt(value):
    receipt=_object(value)
    _need(_hash(receipt.get('sha256')) and _size(receipt.get('size')),'Publication content hash/size required')
    _need(_contained(receipt.get('root'),receipt.get('final_path')),'Publication path is outside its root')
    _ancestry(receipt.get('parent_identity'),receipt['root'],receipt['final_path'])
    return receipt


def _location(receipt):
    return {key:copy.deepcopy(receipt[key]) for key in ('root','final_path','sha256','size','parent_identity','identity') if key in receipt}


def _source_fingerprint(manifest):
    facts=manifest.get('metadata_facts')
    _need(facts is None or isinstance(facts,dict),'Malformed source metadata facts')
    return (facts or {}).get('source_fingerprint')


def publication_id(job_id,kind,original_receipt):
    """Stable UUID of parent lineage, publication kind and canonical receipt."""
    _need(isinstance(job_id,str) and bool(job_id),'Publication job identity required')
    _need(kind in KINDS,'Unknown publication kind')
    return str(uuid.uuid5(uuid.NAMESPACE_URL,'books-publication-v1:'+job_id+':'+kind+':'+_digest(_receipt(original_receipt))))


def initialize(db):
    """Initialize the protocol schema without committing the caller's transaction."""
    expected={
        'output_relocations':set('migration_id publication_id publication_kind immutable_receipt_sha256 job_id schema stage original_output_json original_output_sha256 original_manifest_hash original_publication_intent_sha256 candidate_id candidate_revision source_fingerprint planned_destination target_root routing_policy_version accepted_routing_json previous_location_json destination_verification_json generation last_error created_utc updated_utc'.split()),
        'migration_events':set('event_id migration_id publication_id generation from_stage to_stage outcome proof_json error created_utc'.split())}
    for table,columns in expected.items():
        found={row[1] for row in db.execute('PRAGMA table_info('+table+')')}
        _need(not found or found==columns,'Existing publication schema differs from the pinned protocol')
    # Do not executescript/commit: callers may already hold an operation transaction.
    db.execute('''CREATE TABLE IF NOT EXISTS output_relocations(
      migration_id TEXT NOT NULL,publication_id TEXT PRIMARY KEY,publication_kind TEXT NOT NULL,
      immutable_receipt_sha256 TEXT NOT NULL,job_id TEXT NOT NULL REFERENCES audio_jobs(job_id),
      schema TEXT NOT NULL,stage TEXT NOT NULL,original_output_json TEXT NOT NULL,
      original_output_sha256 TEXT NOT NULL,original_manifest_hash TEXT NOT NULL,
      original_publication_intent_sha256 TEXT NOT NULL,candidate_id TEXT NOT NULL,
      candidate_revision INTEGER NOT NULL,source_fingerprint TEXT NOT NULL,
      planned_destination TEXT NOT NULL,target_root TEXT NOT NULL,routing_policy_version TEXT NOT NULL,
      accepted_routing_json TEXT NOT NULL,previous_location_json TEXT NOT NULL,
      destination_verification_json TEXT,generation INTEGER NOT NULL,last_error TEXT,
      created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS migration_events(
      event_id INTEGER PRIMARY KEY AUTOINCREMENT,migration_id TEXT NOT NULL,publication_id TEXT NOT NULL,
      generation INTEGER NOT NULL,from_stage TEXT,to_stage TEXT NOT NULL,outcome TEXT NOT NULL,
      proof_json TEXT,error TEXT,created_utc TEXT NOT NULL)''')
    for action in ('UPDATE','DELETE'):
        db.execute(f"CREATE TRIGGER IF NOT EXISTS migration_events_no_{action.lower()} BEFORE {action} ON migration_events BEGIN SELECT RAISE(ABORT,'Migration events are append-only'); END")


def _fetch(db,sql,args):
    cursor=db.execute(sql,args);row=cursor.fetchone()
    return dict(zip([column[0] for column in cursor.description],tuple(row))) if row is not None else None


def _completed_parent_lineage(db,identity,manifest,journal,parent):
    """Accept the one supported completed series-retag successor, never a guess.

    SeriesBackfill preserves the original publication intent and replaces the
    current receipt. Replay its exact catalog transformation; native media proof
    remains the planner/worker's responsibility. Pin the entire durable record.
    """
    intent=_receipt(journal['publication_intent'])
    if _digest(intent)==_digest(parent):return None
    _need(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='series_backfill'").fetchone(),
          'Completed parent publication intent/output differs')
    rows=db.execute('SELECT job_id,state,reason,record FROM series_backfill WHERE job_id=?',(identity,)).fetchall()
    _need(len(rows)==1,'Exactly one completed parent backfill is required')
    saved=dict(zip(('job_id','state','reason','record'),tuple(rows[0])))
    _need(saved['job_id']==identity and saved['state']=='done' and saved['reason']=='','Parent backfill is not complete')
    record=_object(saved['record']);review=_object(record.get('review'))
    _need(intent.get('job_id')==identity==parent.get('job_id'),'Parent backfill publication job differs')
    _need(_path(record.get('temp'))==ntpath.join(ntpath.dirname(_path(intent['final_path'])),'.books-arranger-series-'+identity+'.m4b'),
          'Parent backfill temporary belongs to another job')
    _need(record.get('removal_intended') is True,'Parent backfill removal chain is incomplete')
    _need(_native(record.get('old_identity')) and _native(record.get('new_identity'))
          and record['old_identity']!=record['new_identity'] and record['old_identity'][0]==record['new_identity'][0],
          'Parent backfill native identities are invalid')
    _need(type(record.get('new_mtime')) is int and record['new_mtime']>0,'Parent backfill modification proof is missing')
    for prefix,receipt in (('old',intent),('new',parent)):
        _need(record.get(prefix+'_path')==receipt['final_path'] and record.get(prefix+'_sha256')==receipt['sha256']
              and type(record.get(prefix+'_size')) is int and record[prefix+'_size']==receipt['size'],
              'Parent backfill does not bind the exact '+prefix+' receipt')
        _need(record.get('root')==receipt['root'],'Parent backfill root differs')
    _need(_path(intent['final_path'])!=_path(parent['final_path']) and ntpath.dirname(_path(intent['final_path']))==ntpath.dirname(_path(parent['final_path'])),
          'Parent backfill is not a same-directory retag')
    _need(record.get('parent_identity')==intent['parent_identity']==parent['parent_identity'],'Parent backfill ancestry differs')
    legacy_proof_absent='series_proof' not in record
    # Before 0.18 only Goodreads/FantLab existed and this optional research
    # annotation was not produced. Do not add it: absence is part of the pinned
    # original record. It is never a replacement for publication/media proof.
    _need(record.get('provider') in {'goodreads','fantlab','wikidata','publisher'} and isinstance(record.get('source_url'),str)
          and record['source_url'].startswith(('https://','http://'))
          and (record['provider'] in {'goodreads','fantlab'} if legacy_proof_absent else isinstance(record['series_proof'],dict))
          and isinstance(record.get('research_receipts'),list) and isinstance(record.get('deferred_sources'),list),
          'Parent backfill provider provenance is incomplete')
    _need(isinstance(record.get('series'),str) and bool(record['series'].strip()) and isinstance(record.get('number'),str)
          and review.get('series')==record['series'] and review.get('number')==record['number'] and isinstance(review.get('title'),str)
          and bool(review['title'].strip()),'Parent backfill review differs')
    _need(manifest.get('root')==record['root'] and manifest.get('destination')==record['new_path']
          and manifest.get('metadata')==review,'Parent backfill manifest differs')
    if isinstance(manifest.get('metadata_facts'),dict):
        facts=manifest['metadata_facts'];source=facts.get('series_source')
        _need(facts.get('series_state')=='verified' and isinstance(source,dict)
              and source.get('provider')==record['provider'] and source.get('url')==record['source_url']
              and source.get('evidence')==record['research_receipts'] and source.get('deferred_sources')==record['deferred_sources'],
              'Parent backfill manifest provider evidence differs')
        _need(not legacy_proof_absent or not any(key in facts or key in source for key in ('series_proof','proof')),
              'Parent backfill is missing manifest-declared research proof')
    expected=copy.deepcopy(intent)
    expected.update(final_path=record['new_path'],sha256=record['new_sha256'],size=record['new_size'],parent_identity=record['parent_identity'])
    validation=_object(expected.get('validation'));validation.update(sha256=record['new_sha256'],size=record['new_size'])
    validation['tags']=dict(validation.get('tags') or {},album=' - '.join([review['series'],review.get('number',''),review['title']]),grouping=review['series'])
    expected['validation']=validation
    _need(_digest(expected)==_digest(parent),'Parent backfill contains unexplained receipt changes')
    return {'schema':'books-completed-series-backfill-lineage-v1','job_id':identity,'record_sha256':_digest(record),
            'original_intent_sha256':_digest(intent),'completed_receipt_sha256':_digest(parent),'manifest_sha256':_digest(manifest)}


def _job(db,job,kind,receipt):
    job=_object(job);identity=job.get('job_id');_need(isinstance(identity,str) and identity,'Job identity unavailable')
    try:durable=_fetch(db,'SELECT * FROM audio_jobs WHERE job_id=?',(identity,))
    except sqlite3.Error as error:raise PublicationRefused('catalog_job_unavailable','Publication catalog job unavailable') from error
    _need(durable is not None,'Publication catalog job unavailable','catalog_job_unavailable')
    _need(durable.get('state')=='completed' and job.get('state')=='completed','Only completed publication jobs are eligible','publication_not_completed')
    manifest=_object(job.get('manifest'));stored=_object(durable.get('manifest'))
    _need(_hash(job.get('manifest_hash')) and job['manifest_hash']==durable.get('manifest_hash')==_digest(manifest)==_digest(stored),'Frozen publication manifest changed')
    _need(manifest.get('job_id')==identity,'Manifest job identity differs')
    journal=_object(durable.get('journal'));given=_object(job.get('journal'))
    _need('publication_intent' in journal and _digest(journal['publication_intent'])==_digest(given.get('publication_intent')),'Original publication intent differs')
    parent=_receipt(durable.get('output'))
    _need(isinstance(parent.get('validation'),dict) and parent['validation'].get('passed') is True,'Completed parent publication validation did not pass')
    lineage=_completed_parent_lineage(db,identity,manifest,journal,parent)
    if kind in {'base','replacement'}:
        _need(_digest(_receipt(durable.get('output')))==_digest(receipt),'Receipt is not the durable original publication')
        _need(_digest(_receipt(job.get('output')))==_digest(receipt),'Supplied original output differs')
        _need(lineage is not None or _digest(journal['publication_intent'])==_digest(receipt),'Original publication intent differs from receipt')
    _need(isinstance(manifest.get('candidate_id'),str) and manifest['candidate_id'] and type(manifest.get('candidate_revision')) is int and manifest['candidate_revision']>=0,'Candidate provenance unavailable')
    return job,manifest,journal,lineage


def _event(db,row,from_stage,to_stage,outcome,proof=None,error=None):
    db.execute('INSERT INTO migration_events(migration_id,publication_id,generation,from_stage,to_stage,outcome,proof_json,error,created_utc) VALUES(?,?,?,?,?,?,?,?,?)',
        (row['migration_id'],row['publication_id'],row['generation'],from_stage,to_stage,outcome,_packed(proof) if proof is not None else None,error,_now()))


def _load(db,pubid):return _fetch(db,'SELECT * FROM output_relocations WHERE publication_id=?',(pubid,))


def _frozen(row):
    mutable={'stage','destination_verification_json','generation','last_error','updated_utc'}
    return {key:value for key,value in row.items() if key not in mutable}


def _binding(row,job,manifest,journal,receipt,kind,lineage):
    _need(row['schema']==SCHEMA and row['publication_id']==publication_id(job['job_id'],kind,receipt) and row['publication_kind']==kind and row['job_id']==job['job_id'],'Publication binding identity differs')
    _need(row['immutable_receipt_sha256']==row['original_output_sha256']==_digest(receipt)==_digest(_object(row['original_output_json'])),'Immutable original receipt changed')
    _need(row['original_manifest_hash']==job['manifest_hash'] and row['original_publication_intent_sha256']==_digest(journal['publication_intent']),'Frozen publication provenance changed')
    _need(row['candidate_id']==manifest['candidate_id'] and row['candidate_revision']==manifest['candidate_revision'],'Frozen publication candidate changed')
    routing=_object(row['accepted_routing_json'])
    _need(routing.get('completed_parent_lineage')==lineage,'Completed parent lineage changed after enrollment')
    _need(routing.get('routing_policy_version')==row['routing_policy_version'] and isinstance(row['source_fingerprint'],str) and bool(row['source_fingerprint']),'Accepted routing binding differs')
    fingerprint=_source_fingerprint(manifest)
    _need(not fingerprint or fingerprint==row['source_fingerprint'],'Original source fingerprint changed')
    _need(_contained(row['target_root'],row['planned_destination']) and _path(row['planned_destination'])!=_path(receipt['final_path']),'Relocation path is invalid')
    _need(_object(row['previous_location_json'])==receipt,'Previous publication location differs')
    _need(row['stage'] in STAGES and type(row['generation']) is int and row['generation']>=0,'Relocation state is malformed')


def plan(db,job,kind,original_receipt,target_root,destination,accepted_routing):
    """Freeze one relocation. No directory creation, collision check or copying.

    For chapter publications the caller must first validate the authoritative
    immutable repair journal; its optional SHA can be pinned in accepted_routing.
    The stored parent job intent is provenance, not that chapter receipt.
    """
    receipt=_receipt(original_receipt);job,manifest,journal,lineage=_job(db,job,kind,receipt);pubid=publication_id(job['job_id'],kind,receipt)
    routing=_object(accepted_routing);version=routing.get('routing_policy_version')
    _need('completed_parent_lineage' not in routing or routing['completed_parent_lineage']==lineage,'Supplied parent lineage differs')
    if lineage is not None:routing['completed_parent_lineage']=lineage
    _need(isinstance(version,str) and bool(version.strip()),'Accepted routing policy version required')
    fingerprint=routing.get('source_fingerprint') or _source_fingerprint(manifest)
    _need(isinstance(fingerprint,str) and bool(fingerprint),'Accepted source fingerprint required')
    if routing.get('repair_journal_sha256') is not None:_need(_hash(routing['repair_journal_sha256']),'Invalid repair journal digest')
    _need(_contained(target_root,destination) and _path(destination)!=_path(receipt['final_path']),'Relocation destination is invalid')
    # Path alias/collision/native ownership are the engine's separate preflight.
    db.execute('SAVEPOINT publication_plan')
    try:
        existing=_load(db,pubid)
        if existing:
            _binding(existing,job,manifest,journal,receipt,kind,lineage)
            _history(db,existing)
            _need(_path(existing['target_root'])==_path(target_root) and _path(existing['planned_destination'])==_path(destination) and _object(existing['accepted_routing_json'])==routing,'A different relocation already exists')
            db.execute('RELEASE publication_plan');return copy.deepcopy(existing)
        now=_now();row={'migration_id':str(uuid.uuid4()),'publication_id':pubid,'publication_kind':kind,'immutable_receipt_sha256':_digest(receipt),'job_id':job['job_id'],
            'schema':SCHEMA,'stage':'planned','original_output_json':_packed(receipt),'original_output_sha256':_digest(receipt),'original_manifest_hash':job['manifest_hash'],
            'original_publication_intent_sha256':_digest(journal['publication_intent']),'candidate_id':manifest['candidate_id'],'candidate_revision':manifest['candidate_revision'],
            'source_fingerprint':fingerprint,'planned_destination':destination,'target_root':target_root,'routing_policy_version':version,'accepted_routing_json':_packed(routing),
            'previous_location_json':_packed(receipt),'destination_verification_json':None,'generation':0,'last_error':None,'created_utc':now,'updated_utc':now}
        _binding(row,job,manifest,journal,receipt,kind,lineage)
        db.execute('INSERT INTO output_relocations('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
        _event(db,row,None,'planned','transition',{'frozen_binding_sha256':_digest(_frozen(row))});db.execute('RELEASE publication_plan');return copy.deepcopy(row)
    except BaseException:
        db.execute('ROLLBACK TO publication_plan');db.execute('RELEASE publication_plan');raise


def _final_proof(row,proof,generation):
    proof=_object(proof);receipt=_receipt(row['original_output_json'])
    _need(proof.get('schema')==PROOF_SCHEMA and proof.get('publication_id')==row['publication_id'] and proof.get('immutable_receipt_sha256')==row['immutable_receipt_sha256'] and type(proof.get('generation')) is int and proof['generation']==generation,'Final proof generation/publication differs')
    _need(_path(proof.get('final_path'))==_path(row['planned_destination']) and _path(proof.get('root'))==_path(row['target_root']),'Final proof does not name planned final location')
    _need(proof.get('sha256')==receipt['sha256'] and type(proof.get('size')) is int and proof['size']==receipt['size'],'Final content differs from immutable publication')
    _need(_native(proof.get('identity')),'Final native file identity required');_ancestry(proof.get('parent_identity'),proof['root'],proof['final_path'])
    media=_object(proof.get('media_validation'))
    _need(media.get('passed') is True and media.get('full_content_sha256')==receipt['sha256'] and type(media.get('size')) is int and media['size']==receipt['size'],'Complete destination media/hash proof required')
    publication=_object(proof.get('final_publication'))
    _need(publication.get('published') is True,'Final no-replace publication proof required')
    for key in ('final_path','root','sha256','size','identity','parent_identity'):
        _need(_packed(publication.get(key))==_packed(proof[key]),'Final publication proof differs from verified final path')
    return proof


def _proof_for(db,row,stage):
    event=_fetch(db,"SELECT proof_json FROM migration_events WHERE publication_id=? AND outcome='transition' AND to_stage=? ORDER BY event_id DESC LIMIT 1",(row['publication_id'],stage))
    _need(event is not None,'Required prior migration phase is unavailable')
    return _object(event['proof_json'])


def _claim(row,proof,generation,schema):
    proof=_object(proof)
    _need(proof.get('schema')==schema and proof.get('publication_id')==row['publication_id'] and proof.get('immutable_receipt_sha256')==row['immutable_receipt_sha256'] and type(proof.get('generation')) is int and proof['generation']==generation,'Migration phase identity/generation differs')
    return proof


def _old_copy(row,value):
    old=_receipt(value);original=_receipt(row['original_output_json'])
    _need(_native(old.get('identity')),'Original copy native identity required')
    _need(all(_packed(old[key])==_packed(original[key]) for key in ('root','final_path','sha256','size','parent_identity')),'Original copy proof differs from immutable publication')
    return old


def _temporary(row,proof):
    _need(_path(proof.get('root'))==_path(row['target_root']) and _contained(proof['root'],proof.get('temporary_path')),'Temporary artifact is outside the target root')
    _need(_path(proof['temporary_path']) not in {_path(row['planned_destination']),_path(_receipt(row['original_output_json'])['final_path'])},'Temporary artifact aliases an original/final publication')
    _need(ntpath.dirname(_path(proof['temporary_path']))==ntpath.dirname(_path(row['planned_destination'])),'Temporary publication must share the final parent')
    _ancestry(proof.get('parent_identity'),proof['root'],proof['temporary_path'])


def _phase_proof(db,row,stage,proof,generation):
    """Validate structural claims and every link to the exact prior artifact."""
    if stage=='copy_intent':
        proof=_claim(row,proof,generation,'books-output-copy-intent-v1');_temporary(row,proof)
        _need(proof.get('no_replace') is True and proof.get('creation')=='owned_exclusive_create','Exclusive owned temporary creation intent required')
        _old_copy(row,proof.get('original_location'))
        for saved in db.execute("SELECT publication_id,proof_json FROM migration_events WHERE outcome='transition' AND to_stage='copy_intent'"):
            if saved[0]!=row['publication_id']:
                other=_object(saved[1]);_need(_path(other.get('temporary_path'))!=_path(proof['temporary_path']),'Temporary artifact name belongs to another publication')
        return proof
    if stage in {'copied','temporary_verified'}:
        proof=_claim(row,proof,generation,'books-output-temporary-proof-v1');_temporary(row,proof)
        _need(_native(proof.get('identity')) and proof.get('flushed') is True,'Flushed temporary native identity required')
        original=_receipt(row['original_output_json'])
        _need(proof.get('sha256')==original['sha256'] and type(proof.get('size')) is int and proof['size']==original['size'],'Temporary complete-copy content differs from original')
        prior_stage='copy_intent' if stage=='copied' else 'copied';prior=_proof_for(db,row,prior_stage)
        digest_key='copy_intent_sha256' if stage=='copied' else 'copied_proof_sha256'
        _need(proof.get(digest_key)==_digest(prior),'Temporary proof does not bind its exact previous phase')
        for key in ('root','temporary_path','parent_identity'):
            _need(_packed(proof[key])==_packed(prior[key]),'Temporary artifact scope changed')
        if stage=='temporary_verified':
            _need(proof['identity']==prior['identity'],'Temporary native identity changed before verification')
            media=_object(proof.get('media_validation'))
            _need(media.get('passed') is True and media.get('full_content_sha256')==original['sha256'] and type(media.get('size')) is int and media['size']==original['size'],'Temporary media/full-content verification required')
        return proof
    if stage=='final_publish_intent':
        proof=_claim(row,proof,generation,'books-output-final-publish-intent-v1');_temporary(row,proof)
        prior=_proof_for(db,row,'temporary_verified')
        _need(proof.get('temporary_verification_sha256')==_digest(prior) and proof.get('no_replace') is True,'Final publication lacks exact verified temporary/no-replace intent')
        _need(_path(proof.get('final_path'))==_path(row['planned_destination']),'Final publication intent destination differs')
        for key in ('root','temporary_path','parent_identity'):
            _need(_packed(proof[key])==_packed(prior[key]),'Final publication temporary scope differs')
        _need(proof.get('temporary_identity')==prior['identity'],'Final publication temporary native identity differs')
        return proof
    if stage in {'final_published','location_committed'}:
        proof=_final_proof(row,proof,generation);intent=_proof_for(db,row,'final_publish_intent')
        _need(proof.get('final_publish_intent_sha256')==_digest(intent),'Final publication lacks its exact precommitted no-replace intent')
        _need(proof['identity']==intent['temporary_identity'] and proof['parent_identity']==intent['parent_identity'],'Final publication native identity/parent differs from verified temporary')
        _need(proof['final_publication'].get('no_replace') is True,'Final publication does not attest no-replace disposition')
        if stage=='location_committed':
            prior=_proof_for(db,row,'final_published')
            _need(all(_packed(prior[key])==_packed(proof[key]) for key in ('root','final_path','sha256','size','identity','parent_identity','final_publication','final_publish_intent_sha256')),'Committed final publication differs from its published proof')
        return proof
    return proof


def _removal_intent(row,proof,generation):
    proof=_object(proof);receipt=_receipt(row['original_output_json'])
    _need(proof.get('publication_id')==row['publication_id'] and proof.get('immutable_receipt_sha256')==row['immutable_receipt_sha256'] and type(proof.get('generation')) is int and proof['generation']==generation,'Old-removal intent publication/generation differs')
    old=_receipt(proof.get('old_location'))
    _need(_native(old.get('identity')),'Old-removal intent native identity required')
    _need(all(old[key]==receipt[key] for key in ('root','final_path','sha256','size','parent_identity')),'Old-removal intent differs from immutable original')
    _need(proof.get('destination_verification_sha256')==_digest(_object(row['destination_verification_json'])),'Old removal is not bound to committed final proof')
    return proof


def _removal_complete(db,row,proof):
    proof=_object(proof)
    intent=_fetch(db,"SELECT proof_json FROM migration_events WHERE publication_id=? AND outcome='transition' AND to_stage='old_removal_intent' ORDER BY event_id DESC LIMIT 1",(row['publication_id'],))
    _need(intent is not None and proof.get('removal_intent_sha256')==_digest(_object(intent['proof_json'])),'Removal completion lacks exact precommitted intent')
    _need(proof.get('original_removed') is True and proof.get('native_owner_closed') is True,'Removal completion requires native-owner closure proof')
    if 'absence_reconciled' in proof:_need(type(proof['absence_reconciled']) is bool,'Invalid absence-reconciliation disposition')
    return proof


def transition(db,pubid,expected_generation,newstage,proof=None,error=None):
    """CAS one durable stage and append its event inside a savepoint.

    Proofs are structural claims supplied by the native migration owner. This
    ledger performs no side effect and does not certify those claims itself.
    Location commit and consumer cache invalidation belong in the caller's
    same catalog transaction. Refusals are append-only within that transaction.
    """
    db.execute('SAVEPOINT publication_transition')
    row=None
    try:
        row=_load(db,pubid);_need(row is not None,'Relocation unavailable')
        _need(type(expected_generation) is int and row['generation']==expected_generation,'Relocation generation changed','relocation_generation_changed')
        durable=_fetch(db,'SELECT * FROM audio_jobs WHERE job_id=?',(row['job_id'],))
        receipt=_receipt(row['original_output_json'])
        job,manifest,journal,lineage=_job(db,durable,row['publication_kind'],receipt)
        _binding(row,job,manifest,journal,receipt,row['publication_kind'],lineage);_history(db,row)
        _need(newstage in STAGES,'Unknown relocation stage')
        _need(error is None or isinstance(error,str),'Relocation error must be text')
        oldstage=row['stage'];normal=oldstage!='complete' and STAGES.index(newstage)==STAGES.index(oldstage)+1
        retained=newstage=='complete' and oldstage in {'location_committed','old_removal_intent'}
        _need(normal or retained,'Illegal relocation transition')
        proof=_object(proof) if proof is not None else None
        if newstage in STAGES[1:7]:_phase_proof(db,row,newstage,proof,expected_generation)
        if retained:
            _need(proof and proof.get('outcome')=='copied_verified_original_retained' and isinstance(proof.get('reason'),str) and proof['reason'].strip(),'Retained-original outcome requires an explicit reason')
            if error is None:error=proof['reason']
        if newstage=='complete' and not retained:_need(proof and proof.get('outcome')=='moved','Completion requires proven removal outcome')
        destination=row['destination_verification_json']
        if newstage in {'final_published','location_committed'}:
            final=_final_proof(row,proof,expected_generation);destination=_packed(final)
            if newstage=='location_committed':
                prior=_object(row['destination_verification_json'])
                _need(all(prior[key]==final[key] for key in ('root','final_path','sha256','size','identity','parent_identity','final_publication')),'Final location changed between publication and commit')
        if newstage in COMMITTED:
            _need(destination is not None,'Committed location requires final-path proof')
            saved=_object(destination);_final_proof(row,saved,saved.get('generation'))
        if newstage=='old_removal_intent':_removal_intent(row,proof,expected_generation)
        if newstage=='original_removed':_removal_complete(db,row,proof)
        generation=expected_generation+1
        changed=db.execute('UPDATE output_relocations SET stage=?,destination_verification_json=?,generation=?,last_error=?,updated_utc=? WHERE publication_id=? AND generation=?',
            (newstage,destination,generation,error,_now(),pubid,expected_generation)).rowcount
        _need(changed==1,'Relocation generation changed','relocation_generation_changed')
        updated=_load(db,pubid);_event(db,updated,oldstage,newstage,'transition',proof,error)
        db.execute('RELEASE publication_transition');return copy.deepcopy(updated)
    except BaseException as failure:
        db.execute('ROLLBACK TO publication_transition');db.execute('RELEASE publication_transition')
        if row is not None and isinstance(failure,PublicationRefused):_event(db,row,row['stage'],str(newstage),'refusal',None,str(failure))
        raise


def _history(db,row):
    cursor=db.execute("SELECT * FROM migration_events WHERE publication_id=? AND outcome='transition' ORDER BY event_id",(row['publication_id'],))
    columns=[c[0] for c in cursor.description];events=[dict(zip(columns,tuple(r))) for r in cursor]
    _need(len(events)==row['generation']+1 and events[0]['from_stage'] is None and events[0]['to_stage']=='planned','Relocation event history is incomplete')
    _need(_object(events[0]['proof_json']).get('frozen_binding_sha256')==_digest(_frozen(row)),'Frozen relocation plan differs from journal')
    prior=None
    for generation,event in enumerate(events):
        _need(event['generation']==generation and event['migration_id']==row['migration_id'] and event['from_stage']==prior,'Relocation event generation differs')
        if prior is not None:
            _need(event['to_stage'] in STAGES,'Unknown relocation event stage')
            normal=prior!='complete' and STAGES.index(event['to_stage'])==STAGES.index(prior)+1
            retained=event['to_stage']=='complete' and prior in {'location_committed','old_removal_intent'}
            _need(normal or retained,'Relocation event graph differs')
            if retained:
                proof=_object(event['proof_json']);_need(proof.get('outcome')=='copied_verified_original_retained' and isinstance(proof.get('reason'),str) and bool(proof['reason'].strip()),'Retained-original journal proof differs')
            if event['to_stage'] in {'final_published','location_committed'}:_final_proof(row,_object(event['proof_json']),generation-1)
            if event['to_stage'] in STAGES[1:7]:_phase_proof(db,row,event['to_stage'],_object(event['proof_json']),generation-1)
            if event['to_stage']=='old_removal_intent':_removal_intent(row,_object(event['proof_json']),generation-1)
            if event['to_stage']=='original_removed':_removal_complete(db,row,_object(event['proof_json']))
            if event['to_stage']=='complete' and not retained:_need(_object(event['proof_json']).get('outcome')=='moved','Completion journal removal outcome differs')
        prior=event['to_stage']
    _need(prior==row['stage'],'Relocation current stage differs from events')
    finals=[event for event in events if event['to_stage'] in {'final_published','location_committed'}]
    if finals:
        _need(row['destination_verification_json']==finals[-1]['proof_json'],'Stored final destination proof differs from its journal')


def resolve(db,job,kind,original_receipt,verify=None):
    """Return separate immutable provenance and current-location envelopes.

    No verifier means verified=False, including for committed bindings. A
    verifier must prove current native ancestry/identity, full content and media
    semantics before returning literal True. Destructive consumers additionally
    retain and recheck their operation/generation lease through disposal.
    Unknown derived receipts never bypass an existing same-kind binding.
    """
    receipt=_receipt(original_receipt);job,manifest,journal,lineage=_job(db,job,kind,receipt);pubid=publication_id(job['job_id'],kind,receipt)
    exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='output_relocations'").fetchone()
    row=_load(db,pubid) if exists else None
    if exists and row is None:
        other=db.execute('SELECT 1 FROM output_relocations WHERE job_id=? AND publication_kind=? LIMIT 1',(job['job_id'],kind)).fetchone()
        _need(other is None,'Original receipt differs from the existing publication binding','immutable_receipt_mismatch')
    effective=_location(receipt)
    envelope={'publication_id':pubid,'original_receipt':copy.deepcopy(receipt),'effective_location':effective,'stage':'original','generation':None,'relocation':None,'verified':False,'outcome':None}
    if row:
        _binding(row,job,manifest,journal,receipt,kind,lineage);_history(db,row)
        if row['stage'] in COMMITTED:
            _need(row['destination_verification_json'] is not None,'Committed destination proof unavailable','relocated_output_unavailable')
            saved=_object(row['destination_verification_json']);final=_final_proof(row,saved,saved.get('generation'))
            effective={key:copy.deepcopy(final[key]) for key in ('root','final_path','sha256','size','parent_identity','identity')}
        envelope.update(effective_location=effective,stage=row['stage'],generation=row['generation'],relocation=copy.deepcopy(row))
        if row['stage']=='complete':
            event=_fetch(db,"SELECT proof_json FROM migration_events WHERE publication_id=? AND outcome='transition' ORDER BY event_id DESC LIMIT 1",(pubid,))
            envelope['outcome']=_object(event['proof_json']).get('outcome')
    if verify is not None:
        _need(callable(verify),'Publication verifier must be callable')
        code='relocated_output_unavailable' if row and row['stage'] in COMMITTED else 'original_output_unavailable'
        try:accepted=verify(copy.deepcopy(effective),copy.deepcopy(envelope))
        except Exception as error:raise PublicationRefused(code,'Current publication verification unavailable: '+str(error)) from error
        _need(accepted is True,'Current publication verification refused',code)
        current_exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='output_relocations'").fetchone()
        current=_load(db,pubid) if current_exists else None
        _need(current==row,'Relocation changed during verification','relocation_generation_changed')
        _job(db,job,kind,receipt)
        envelope['verified']=True
    return copy.deepcopy(envelope)
