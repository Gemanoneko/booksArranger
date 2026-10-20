"""Explicit new conversion intent; frozen failed work and author credits stay immutable."""
import copy,hashlib,json,os
from organization import frozen_plan,POLICY

def packed(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(packed(value).encode()).hexdigest()
def reviewed(value):
    result=copy.deepcopy(value)
    for key in ('job_id','attempt_id','m4b_repair','retry_intent'):result.pop(key,None)
    if 'output_root' not in result:result['output_root']=result['root']
    return result

def bind(parent,fresh,output_root,*,retention=None):
    prior=json.loads(parent['manifest'])
    if any(key in prior or key in fresh for key in ('replacement_id','replacement_parent_job_id')):raise ValueError('Replacement destination requires its exact authorized lineage; generic route Retry is unavailable')
    if parent['state']!='needs attention' or parent.get('output') or json.loads(parent['journal']).get('publication_intent') or digest(prior)!=parent['manifest_hash']:raise ValueError('Failed parent publication/source binding changed')
    without_route=lambda value:{key:item for key,item in reviewed(value).items() if key not in {'output_root','destination'}}
    if fresh['job_id']==parent['job_id'] or without_route(prior)!=without_route(fresh):raise ValueError('Frozen approved source/review/cover/policy changed; failed intent retained')
    approved=reviewed(fresh);routing=dict(approved['metadata'],organization_policy=POLICY)
    destination=frozen_plan(approved,output_root,routing)['path']
    target=copy.deepcopy(fresh);target['output_root']=str(output_root);target['destination']=destination
    if retention:
        target['cleanup_policy']=dict(target['cleanup_policy'],enabled=False,empty_source_folders=False)
    binding={'schema':'books-explicit-retry-intent-v1','parent_job_id':parent['job_id'],'parent_manifest_hash':parent['manifest_hash'],'parent_journal_sha256':hashlib.sha256(parent['journal'].encode()).hexdigest(),'approved_manifest':approved,'approved_manifest_sha256':digest(approved),'routing_policy_version':POLICY,'routing_review':routing,'target_root':str(output_root),'destination':destination,'retained_checkpoint_id':retention}
    target['retry_intent']=binding
    return target

def validate(manifest,current,output_root):
    try:
        binding=manifest['retry_intent'];approved=binding['approved_manifest']
        if binding['schema']!='books-explicit-retry-intent-v1' or binding['approved_manifest_sha256']!=digest(approved) or approved!=reviewed(current):return False
        if binding['routing_policy_version']!=POLICY or binding['target_root']!=str(output_root):return False
        routing=dict(approved['metadata'],organization_policy=POLICY)
        if binding['routing_review']!=routing or binding['destination']!=frozen_plan(approved,output_root,routing)['path']:return False
        expected=copy.deepcopy(approved);expected['output_root']=str(output_root);expected['destination']=binding['destination']
        if binding.get('retained_checkpoint_id'):expected['cleanup_policy']=dict(expected['cleanup_policy'],enabled=False,empty_source_folders=False)
        return reviewed(manifest)==expected
    except (KeyError,TypeError,ValueError):return False

def guard(db,manifest,current,output_root):
    if not validate(manifest,current,output_root):return False
    binding=manifest['retry_intent'];parent=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(binding['parent_job_id'],)).fetchone()
    if not parent or parent['manifest_hash']!=binding['parent_manifest_hash'] or hashlib.sha256(parent['journal'].encode()).hexdigest()!=binding['parent_journal_sha256'] or parent['output'] or parent['state']!='needs attention':return False
    relation=db.execute('SELECT binding FROM audio_retry_intents WHERE parent_job_id=? AND child_job_id=?',(parent['job_id'],manifest['job_id'])).fetchone()
    if not relation or json.loads(relation[0])!=binding:return False
    if binding.get('retained_checkpoint_id'):
        from producer_recovery import verify_retained
        attempt=verify_retained(db,parent['job_id'],parent['attempt_id'])
        if attempt['checkpoint_id']!=binding['retained_checkpoint_id']:return False
    return True

def ready_compatible(row,manifest,verified):
    if not verified:return False
    binding=manifest.get('retry_intent') or {};approved=binding.get('approved_manifest') or {}
    try:
        if row['revision']!=manifest['candidate_revision'] or row['review']!=approved['metadata']:return False
        if os.path.normcase(row['preview']['path']) not in {os.path.normcase(approved['destination']),os.path.normcase(manifest['destination'])}:return False
        return validate(manifest,approved,binding['target_root'])
    except (KeyError,TypeError,ValueError):return False
