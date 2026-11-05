"""Exact repository-recorded user decisions, distinct from fetched/manual citations.

Only the private standing-metadata admission accepts these records. Recording a
decision is not a public fetch; its timestamp and attribution retain that meaning.
"""
import copy

SCHEMA='books-curated-user-decision-v1'
SOURCE_KIND='curated_user_decision'
LEGACY_WORLD='user:middle-earth-2026-11-01'
LEGACY_RECORDED='2026-11-01T11:36:38Z'  # f942ac2: SeriesPreview_Diagnosis_2026-11-01.md
KEYS={'schema','source_kind','decision_ref','recorded_utc','decision_actor','decision_identity',
      'field','cited_value','source_url','reviewer_actor','reviewer_identity','basis','binding'}


def _decision(ref):
    from tolkien_trilogy import DECISION,RECORDED,SERIES,WORLD
    if ref==DECISION:return RECORDED.isoformat().replace('+00:00','Z'),{'series':SERIES,'universe':WORLD}
    if ref==LEGACY_WORLD:return LEGACY_RECORDED,{'universe':WORLD}
    raise ValueError('Unknown curated user decision')


def _binding(review,facts,original_title,cycle):
    from tolkien_trilogy import FIELDS
    return {'source_fingerprint':facts.get('source_fingerprint'),'work_ids':copy.deepcopy(facts.get('work_ids')),
            'authors':copy.deepcopy(facts.get('authors')),'original_title':original_title,'catalog_cycle':cycle,
            'review':{field:review.get(field,'') for field in FIELDS}}


def evidence(result,decision_ref,field,value):
    recorded,fields=_decision(decision_ref)
    if fields.get(field)!=value:raise ValueError('Unknown curated decision field/value')
    work=result.get('work') or {};series=work.get('verified_series') or {}
    return {'schema':SCHEMA,'source_kind':SOURCE_KIND,'decision_ref':decision_ref,'recorded_utc':recorded,
            'decision_actor':'user','decision_identity':'Sergei','field':field,'cited_value':value,'source_url':'',
            'reviewer_actor':'assistant','reviewer_identity':'Books Arranger recorded user decision',
            'basis':'Repository-recorded exact Tolkien work/cycle and user naming or world decision.',
            'binding':_binding(result.get('review') or {},result.get('metadata_facts') or {},work.get('original_title'),series.get('source_url'))}


def validate(record,row,review,facts):
    """Validate one detached record against this accepted private source/work/field.

    A schema label, blank URL or user attribution alone grants no admission. Generic
    public/manual/local records continue through their own unchanged validators.
    """
    from tolkien_trilogy import DECISION,CYCLE,WORKS,AUTHORS,author_world
    if not isinstance(record,dict) or set(record)!=KEYS or record.get('schema')!=SCHEMA or record.get('source_kind')!=SOURCE_KIND:
        raise ValueError('Invalid curated user decision record')
    recorded,fields=_decision(record.get('decision_ref'))
    field=record.get('field')
    if (field not in fields or record.get('cited_value')!=fields[field] or review.get(field)!=fields[field]
        or record.get('recorded_utc')!=recorded or record.get('decision_actor')!='user' or record.get('decision_identity')!='Sergei'
        or record.get('source_url')!='' or record.get('reviewer_actor') not in ('user','assistant')):
        raise ValueError('Curated user decision field or attribution differs')
    for key in ('reviewer_identity','basis'):
        if not isinstance(record.get(key),str) or not record[key].strip() or len(record[key])>4000:raise ValueError('Invalid curated decision review attribution')
    if not isinstance(facts,dict) or not isinstance(row,dict) or not row.get('fingerprint') or facts.get('source_fingerprint')!=row['fingerprint']:
        raise ValueError('Curated user decision source binding differs')
    original=facts.get('original_title');expected=WORKS.get(original);ids=facts.get('work_ids');authors=facts.get('authors')
    if (not expected or not isinstance(ids,list) or len(ids)!=1 or not isinstance(ids[0],str)
        or not isinstance(authors,list) or len(authors)!=1
        or review.get('canonical_author')!=authors[0] or facts.get('series_state')!='verified' or review.get('number')!=expected[1]
        or record.get('binding')!=_binding(review,facts,original,CYCLE)):
        raise ValueError('Curated user decision work binding differs')
    if record['decision_ref']==DECISION:
        if authors[0] not in AUTHORS or not author_world(review,facts):raise ValueError('Current trilogy decision proof differs')
    else:
        from public_research import _exact_people
        world=(facts.get('shared_routing') or {}).get('universe') or {}
        if (ids!=[expected[0]] or review.get('series')!='Властелин колец' or world.get('id')!=LEGACY_WORLD
            or not any(_exact_people(authors[0],[alias]) for alias in AUTHORS)
            or world.get('name')!='Middle-earth' or world.get('basis')!='user'
            or world.get('evidence')!=['user:middle-earth-decision-2026-11-01']
            or world.get('members')!=[{'work_id':ids[0],'authors':authors,'series_id':CYCLE}]):
            raise ValueError('Legacy Middle-earth decision proof differs')
    return copy.deepcopy(record)
