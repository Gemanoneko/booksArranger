"""Pure queued-route observation. A proposal is never approval or output ownership."""
import copy,hashlib,json,ntpath
from organization import frozen_plan,POLICY

SCHEMA='books-queued-destination-review-v1'
REASON='Queued destination needs review'
STALE="This book's destination or review changed. Check the current details before retrying."
def packed(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(packed(value).encode()).hexdigest()
def path_key(value):
    if not isinstance(value,str) or not value or not ntpath.isabs(value) or '\x00' in value:raise ValueError('A canonical absolute output path is required')
    return ntpath.normcase(ntpath.normpath(value))
def policy(roots,sources,output_root):
    if output_root is not None:path_key(output_root)
    return {'schema':'books-effective-destination-policy-v1','legacy_roots':{key:ntpath.normpath(str(value)) for key,value in roots.items()},'audiobook_sources':[ntpath.normpath(str(value)) for value in sources],'output_root':ntpath.normpath(str(output_root)) if output_root is not None else None,'routing_policy_version':POLICY}
def observe(manifest,effective_policy):
    if effective_policy.get('schema')!='books-effective-destination-policy-v1' or effective_policy.get('routing_policy_version')!=POLICY:raise ValueError('Current destination policy is unavailable')
    source=manifest['root'];path_key(source)
    if path_key(source) not in {path_key(value) for value in effective_policy['audiobook_sources']}:raise ValueError('Queued source root is outside current configured sources')
    old=manifest['output_root'] if 'output_root' in manifest else source
    path_key(old);path_key(manifest['destination'])
    target=effective_policy['output_root'] or source
    desired=frozen_plan(manifest,target,dict(manifest['metadata'],organization_policy=POLICY))['path']
    if path_key(old)==path_key(target) and path_key(manifest['destination'])==path_key(desired):return None
    return {'schema':SCHEMA,'state':'needs_review','manifest_sha256':digest(manifest),'policy':copy.deepcopy(effective_policy),'policy_sha256':digest(effective_policy),'old_root':old,'proposed_root':target,'old_destination':manifest['destination'],'proposed_destination':desired,'routing_policy_version':POLICY}
class DestinationReviewNeeded(ValueError):
    def __init__(self,observation):
        super().__init__(REASON);self.observation=copy.deepcopy(observation)

def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS audio_destination_holds(job_id TEXT PRIMARY KEY,manifest_hash TEXT NOT NULL,binding TEXT NOT NULL,created TEXT NOT NULL)')
def current(db,row,effective_policy):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='audio_destination_holds'").fetchone():return None
    saved=db.execute('SELECT * FROM audio_destination_holds WHERE job_id=?',(row['job_id'],)).fetchone()
    if saved is None:return None
    binding=json.loads(saved['binding']);held=binding['held_row'];observation=binding['observation']
    if saved['manifest_hash']!=row['manifest_hash'] or held!=dict(row):raise ValueError(STALE)
    if observation!=observe(json.loads(row['manifest']),effective_policy):raise ValueError(STALE)
    if observation['manifest_sha256']!=row['manifest_hash']:raise ValueError(STALE)
    return copy.deepcopy(observation)
