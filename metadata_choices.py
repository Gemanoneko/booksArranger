"""Explicit per-candidate metadata decisions; never approval or provider priority.

Question signatures cover content/provenance, not retrieval timestamps. Different
works are coherent profiles; field choices require a shared authoritative work ID.
Only the service's existing review save path applies the returned draft patch.
"""
import copy
import datetime
import hashlib
import json
import uuid

SCHEMA='books-metadata-choice-v1'
IDENTITY=('title','canonical_author','original_language')
PROFILE=IDENTITY+('series','number','universe')
FIELDS=PROFILE+('genre','topic','narrator')
VOLATILE={'retrieved_utc','retrieved_at','saved_utc','fetched_at','checked_at','attempted_utc','timestamp'}
STALE='Sources changed. Compare the updated results before saving.'


class ChoiceChanged(ValueError):
    code='metadata_choice_changed'
    def __init__(self,message=STALE):super().__init__(message)


def packed(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def signature(value):return hashlib.sha256(packed(value).encode('utf-8')).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _stable(value):
    if isinstance(value,dict):return {key:_stable(item) for key,item in sorted(value.items()) if key not in VOLATILE}
    if isinstance(value,list):return sorted((_stable(item) for item in value),key=packed)
    return value


def _text(value):
    if isinstance(value,list):return '; '.join(str(item).strip() for item in value if isinstance(item,str) and item.strip())
    return str(value).strip() if isinstance(value,(str,int)) and type(value) is not bool else ''


def _norm(value):return ' '.join(_text(value).casefold().split())


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS metadata_choices(decision_id TEXT PRIMARY KEY,candidate_id TEXT NOT NULL,fingerprint TEXT NOT NULL,candidate_revision INTEGER NOT NULL,evidence_signature TEXT NOT NULL,saved_utc TEXT NOT NULL,actor TEXT NOT NULL,payload TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS metadata_choices_candidate ON metadata_choices(candidate_id,fingerprint,saved_utc,decision_id)')
    for action in ('UPDATE','DELETE'):
        db.execute(f"CREATE TRIGGER IF NOT EXISTS metadata_choices_no_{action.lower()} BEFORE {action} ON metadata_choices BEGIN SELECT RAISE(ABORT,'Metadata choices are append-only'); END")


def records(db,row):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata_choices'").fetchone():return []
    result=[]
    for saved in db.execute('SELECT payload FROM metadata_choices WHERE candidate_id=? ORDER BY saved_utc,decision_id',(row['id'],)):
        value=json.loads(saved[0]);value['status']='current' if value['fingerprint']==row['fingerprint'] else 'stale';result.append(value)
    return result


def _source(proposal,manual=False):
    values={field:_text(proposal.get(field)) for field in FIELDS}
    values['canonical_author']=_text(proposal.get('canonical_author') or proposal.get('authors') or proposal.get('author'))
    if _norm(values['original_language']) in {'unknown','unverified','und'}:values['original_language']=''
    provenance={'id':_text(proposal.get('id') or proposal.get('source_id')),
        'provider':_text(proposal.get('provider')) or ('Entered by you' if manual else 'Metadata source'),
        'public_url':_text(proposal.get('public_url')),'work_id':_text(proposal.get('work_id')),
        'retrieved_utc':proposal.get('retrieved_utc') or proposal.get('saved_utc') or '',
        'evidence':copy.deepcopy(proposal.get('per_field_evidence') or proposal.get('evidence') or {}),'manual_source':manual,
        'source_links':copy.deepcopy(proposal.get('source_links') or [])}
    if not provenance['id']:provenance['id']=signature(_stable(provenance))
    return {'values':values,'source':provenance}


def _sources(providers,manual,conflicts):
    sources=[_source(proposal) for proposal in providers if isinstance(proposal,dict) and not proposal.get('manual_source')]
    for record in manual:
        if record.get('status','current')!='current':continue
        proposal=dict(record.get('values',{}),id=record.get('source_id'),provider='Entered by you',saved_utc=record.get('saved_utc'),per_field_evidence=record)
        sources.append(_source(proposal,True))
    # Automatic research can expose exact compared assertions without a full
    # lookup proposal. Retain unknown fields as not supplied; never copy fields
    # from the manual record into the competing work's profile.
    automatic={}
    known={s['source']['id'] for s in sources}
    for conflict in conflicts:
        if not isinstance(conflict,dict):continue
        field=conflict.get('field');field='canonical_author' if field in {'authors','author'} else field
        if field not in FIELDS or not isinstance(conflict.get('other_value'),(str,int)):continue
        identity=_text(conflict.get('other_source_id') or conflict.get('other_work_id') or conflict.get('other_url') or conflict.get('other_provider'))
        if not identity or identity in known:continue
        observed=[source for source in conflict.get('other_sources',[]) if isinstance(source,dict)]
        names=sorted({str(source.get('provider') or source.get('kind') or source.get('name')) for source in observed if source.get('provider') or source.get('kind') or source.get('name')})
        links=[{'provider':source.get('provider') or source.get('kind') or source.get('name') or 'Source record','url':source.get('public_url') or source.get('source_url') or source.get('url')} for source in observed if source.get('public_url') or source.get('source_url') or source.get('url')]
        proposal=automatic.setdefault(identity,{'id':identity,'work_id':conflict.get('other_work_id',''),'provider':conflict.get('other_provider') or ', '.join(names) or 'Research source not named','public_url':conflict.get('other_url',''),'source_links':links,'per_field_evidence':[]})
        proposal[field]=conflict['other_value'];proposal['per_field_evidence'].append({key:copy.deepcopy(conflict[key]) for key in ('field','other_value','other_work_id','other_sources','other_source_id','other_provider','other_url') if key in conflict})
    sources.extend(_source(value) for value in automatic.values())
    # Retrieval order is not evidence identity. Repeated identical assertions
    # remain inspectable without manufacturing additional agreement votes.
    unique={signature(_stable(source)):source for source in sources}
    return [unique[key] for key in sorted(unique)]


def _question(row,sources,kind,field=None,profile_fields=PROFILE):
    relevant=profile_fields if kind=='work_profile' else (field,)
    groups={};missing=[]
    for source in sources:
        values={key:source['values'].get(key,'') for key in relevant}
        if kind=='field' and not values[field]:missing.append(copy.deepcopy(source['source']));continue
        evidence=copy.deepcopy(source['source'])
        # Scope per-field evidence when a provider supplied typed field records.
        if isinstance(evidence.get('evidence'),list):
            evidence['evidence']=[item for item in evidence['evidence'] if not isinstance(item,dict) or item.get('field') in set(relevant)|{'authors'}]
        elif isinstance(evidence.get('evidence'),dict) and set(evidence['evidence'])&set(FIELDS):
            evidence['evidence']={key:value for key,value in evidence['evidence'].items() if key in relevant or key not in FIELDS}
        key=signature({key:_norm(value) for key,value in values.items()})
        group=groups.setdefault(key,{'id':key,'values':values,'sources':[]});group['sources'].append(evidence)
    options=sorted(groups.values(),key=lambda option:option['id'])
    for option in options:option['sources'].sort(key=lambda source:packed(_stable(source)))
    content={'type':kind,'field':field,'profile_fields':list(relevant) if kind=='work_profile' else [],'options':options,'not_supplied':sorted(missing,key=lambda source:packed(_stable(source)))}
    qid=signature({'candidate_id':row['id'],'fingerprint':row['fingerprint'],'type':kind,'field':field})
    return dict(content,id=qid,label='Which book is this recording of?' if kind=='work_profile' else 'Which '+field.replace('_',' ')+' should this book use?',
                evidence_signature=signature(_stable(content)),resolved=False,decision=None)


def questions(row,providerproposals,manualsources,automaticconflicts):
    sources=_sources(providerproposals,manualsources,automaticconflicts)
    different=[field for field in FIELDS if len({_norm(s['values'][field]) for s in sources if s['values'][field]})>1]
    result=[]
    if different:
        workids={s['source']['work_id'] for s in sources}
        proven_same=bool(sources) and len(workids)==1 and '' not in workids
        # Matching title/author spelling alone is never proof of a shared work.
        if any(field in IDENTITY for field in different) or not proven_same:result=[_question(row,sources,'work_profile',profile_fields=PROFILE+tuple(field for field in different if field not in PROFILE))]
        else:result=[_question(row,sources,'field',field) for field in different]
    return {'signature':signature({'candidate_id':row['id'],'fingerprint':row['fingerprint'],'questions':[(q['id'],q['evidence_signature']) for q in result]}),
            'questions':result,'unresolved_count':len(result)}


def present(db,row,providers,manual,conflicts):
    history=records(db,row);current=[record for record in history if record['status']=='current']
    candidates={identity for record in current for identity in record.get('correction_source_ids',[])}
    baseline=questions(row,providers,[record for record in manual if record.get('source_id') not in candidates],conflicts)
    scopes={question['id']:question['evidence_signature'] for question in baseline['questions']}
    ignored={identity for record in current if any(choice.get('mode')=='corrected' and scopes.get(choice['question_id'])==choice['evidence_signature'] for choice in record.get('choices',[])) for identity in record.get('correction_source_ids',[])}
    result=questions(row,providers,[record for record in manual if record.get('source_id') not in ignored],conflicts)
    for question in result['questions']:
        prior=[(record,choice) for record in current for choice in record.get('choices',[]) if choice['question_id']==question['id']]
        if prior:
            record,choice=prior[-1];question['previous_decision']=copy.deepcopy(record)
            if choice['evidence_signature']==question['evidence_signature']:
                question['decision']=copy.deepcopy(choice);question['resolved']=choice['mode']!='unresolved';question['chosen_by']='you'
            else:question['renewed']=True
    result['unresolved_count']=sum(not question['resolved'] for question in result['questions'])
    result['decision_history']=history
    result['manual_source_ids']=[record['source_id'] for record in manual if record.get('status','current')=='current' and record.get('source_id')]
    return result


def prepare(row,snapshot,submitted_signature,choices,actor='user',note=''):
    if submitted_signature!=snapshot['signature']:raise ChoiceChanged()
    if actor not in {'user','assistant'} or not isinstance(note,str) or len(note)>16000:raise ValueError('Invalid metadata decision actor or note')
    if not isinstance(choices,list) or len(choices)!=len(snapshot['questions']):raise ValueError('Choose an explicit answer for every displayed metadata question')
    byid={choice.get('question_id'):choice for choice in choices if isinstance(choice,dict)}
    if len(byid)!=len(choices) or set(byid)!={q['id'] for q in snapshot['questions']}:raise ValueError('Metadata choices do not match displayed questions')
    patch={};corrected={};saved=[]
    for question in snapshot['questions']:
        choice=byid[question['id']];mode=choice.get('mode','provider' if choice.get('option_id') else 'unresolved')
        if mode=='provider':
            option=next((option for option in question['options'] if option['id']==choice.get('option_id')),None)
            if option is None:raise ValueError('Choose a displayed metadata result')
            values=copy.deepcopy(option['values'])
        elif mode=='corrected':
            values=choice.get('values');allowed=set(question.get('profile_fields') or PROFILE) if question['type']=='work_profile' else {question['field']}
            if not isinstance(values,dict) or not values or set(values)-allowed or any(not isinstance(value,str) or len(value)>2000 for value in values.values()):raise ValueError('Enter bounded corrected values for the displayed conflict')
            if question['type']=='work_profile' and (not {'title','canonical_author'}<=set(values) or not values['title'].strip() or not values['canonical_author'].strip()):raise ValueError('A corrected work needs its complete title and author identity')
            values={key:value.strip() for key,value in values.items()};corrected.update(values)
        elif mode=='unresolved':values={}
        else:raise ValueError('Unknown metadata choice')
        if mode!='unresolved':
            if question['type']=='work_profile':
                values={key:values.get(key,'') for key in question.get('profile_fields') or PROFILE}
                # Do not retain an author folder belonging to an unchosen work.
                values['author']=values['canonical_author']
            patch.update(values)
        compared={key:copy.deepcopy(value) for key,value in question.items() if key not in {'decision','previous_decision','renewed','chosen_by','resolved'}}
        saved.append({'question_id':question['id'],'evidence_signature':question['evidence_signature'],'mode':mode,'option_id':choice.get('option_id') if mode=='provider' else None,
                      'values':copy.deepcopy(values),'compared_snapshot':compared})
    corrected={key:value for key,value in corrected.items() if value and not (key=='original_language' and value.casefold() in {'unknown','unverified','und'})}
    record={'schema':SCHEMA,'decision_id':str(uuid.uuid4()),'candidate_id':row['id'],'fingerprint':row['fingerprint'],'candidate_revision':row['revision'],
            'evidence_signature':snapshot['signature'],'saved_utc':now(),'actor':actor,'note':note,'choices':saved,'corrected_values':corrected,
            'baseline_manual_source_ids':list(snapshot.get('manual_source_ids',[]))}
    return {'patch':patch,'corrected_values':corrected,'record':record}


def append(db,record,applied_revision=None):
    """Called in the existing context/manual-source transaction after capture."""
    initialize(db);record=copy.deepcopy(record)
    if record.get('schema')!=SCHEMA or record.get('actor') not in {'user','assistant'}:raise ValueError('Invalid metadata decision record')
    if applied_revision is not None:record['applied_revision']=applied_revision
    corrected=record.get('corrected_values') or {};record['correction_source_ids']=[]
    if corrected and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='manual_metadata_sources'").fetchone():
        for saved in db.execute('SELECT source_id,payload FROM manual_metadata_sources WHERE candidate_id=? AND fingerprint=?',(record['candidate_id'],record['fingerprint'])):
            source=json.loads(saved[1]);values=source.get('values',{})
            if saved[0] not in record.get('baseline_manual_source_ids',[]) and values==corrected:record['correction_source_ids'].append(saved[0])
    db.execute('INSERT INTO metadata_choices VALUES(?,?,?,?,?,?,?,?)',(record['decision_id'],record['candidate_id'],record['fingerprint'],record['candidate_revision'],record['evidence_signature'],record['saved_utc'],record['actor'],packed(record)))
    return record


def admission(snapshot,review):
    """A scoped answer is a draft constraint, never permission to approve.

    Automatic re-evaluation must still produce the exact chosen values through
    its normal source gates. Start over cannot silently revert to a provider.
    """
    if snapshot.get('unresolved_count',0):
        raise ValueError('Resolve metadata question before approving this book')
    for question in snapshot.get('questions',[]):
        if not question.get('resolved'):continue
        decision=question.get('decision') or {}
        for field,value in decision.get('values',{}).items():
            actual=review.get(field,'')
            if field=='original_language':
                def language(v):
                    v=str(v).strip().casefold()
                    return 'Unknown' if v in {'','unknown','und','unverified'} else 'Russian' if v in {'ru','rus','russian','русский'} else 'Other'
                actual,value=language(actual),language(value)
            if _norm(actual)!=_norm(value):
                raise ValueError('Saved metadata choice differs from this draft; review the chosen values before approving')
    return True
