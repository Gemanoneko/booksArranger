"""User standing rules for output metadata, separate from verified work identity.
Only the private automatic admission path supplies these facts. Public/manual reviews
continue to use their existing evidence contract.
"""
import copy
import re
from pathlib import Path
from source_identity import filename_identity, norm, text

POLICY_VERSION='standing-17-v1'
LANGUAGES={'ru':'ru','rus':'ru','russian':'ru','русский':'ru','en':'en','eng':'en','english':'en','английский':'en','ja':'ja','jpn':'ja','japanese':'ja','fr':'fr','fra':'fr','french':'fr','de':'de','deu':'de','german':'de','es':'es','spa':'es','spanish':'es'}

def russian_source_title(row):
    """One consistent recording title, never a chapter name or guessed translation."""
    values=[]
    for member in row.get('members',[]):
        tags={k.casefold():v for k,v in member.get('metadata',{}).get('tags',{}).items()}
        value=text(tags.get('album'))
        if not value and len(row.get('members',[]))==1:value=text(tags.get('title'))
        if not value:
            parsed=filename_identity(member.get('filename',''))
            if parsed.get('author') or len(row.get('members',[]))==1:value=parsed.get('title','')
        if value and re.search('[А-Яа-яЁё]',value):values.append(value)
    if len(values)!=len(row.get('members',[])) or len({norm(v) for v in values})!=1:return None
    return values[0] if values else None

def recording_language(row):
    known=set()
    for member in row.get('members',[]):
        tags={k.casefold():v for k,v in member.get('metadata',{}).get('tags',{}).items()}
        raw=text(tags.get('language')).casefold()
        if raw:
            value=LANGUAGES.get(raw)
            if not value:return {'value':None,'basis':'embedded'},['Recording language evidence uncertain']
            known.add(value)
    if len(known)>1:return {'value':None,'basis':'embedded'},['Recording languages conflict']
    if known:return {'value':next(iter(known)),'basis':'embedded'},[]
    # A recording's Russian source label is provenance, not original-work language.
    return {'value':'ru' if russian_source_title(row) else None,'basis':'source_label'},[]

def build_policy(row,work,preferred_title,authors,english_verified=False,series='',number='',collection=None,local=None):
    language=work.get('original_language') or None
    if language and not re.fullmatch('[a-z]{2,3}',language):raise ValueError('Invalid verified original language')
    names=[text(v) for v in authors if text(v)]
    if not names or len(names)>30:raise ValueError('Verified author identity unavailable')
    reasons=[];source_title=russian_source_title(row)
    if english_verified:
        title=text(preferred_title);basis='published_english'
    elif language in ('ru','en'):
        title=text(preferred_title);basis='verified_original'
    elif local:
        # Locally agreed title, cleaned of bracketed narrator/year notes; never a guessed translation.
        title=text(preferred_title);basis='local_agreement'
    elif source_title:
        title=source_title;basis='source_russian'
        if norm(source_title) not in {norm(v) for v in work.get('titles',[])}:reasons.append('Russian recording alias needs a verified original-work bridge')
    else:
        title=text(preferred_title);basis='verified_original'
    if not title:reasons.append('Recording title unavailable')
    credit='; '.join(names)
    # A two-token name or Latin script does not establish family-name order.
    folder=credit
    record_language,record_reasons=recording_language(row);reasons.extend(record_reasons)
    # An incomplete position is omitted, never converted into standalone evidence.
    series=text(series) if series and number else '';number=text(number) if series else ''
    review={'title':title,'canonical_author':credit,'author':folder,'original_language':'Russian' if language=='ru' else 'Other' if language else 'Unknown',
        'series':series,'number':number,'genre':'','topic':'','narrator':'','multi_author':False,'anthology':bool(collection)}
    narrators={text({k.casefold():v for k,v in m.get('metadata',{}).get('tags',{}).items()}.get('narrator') or {k.casefold():v for k,v in m.get('metadata',{}).get('tags',{}).items()}.get('reader')) for m in row.get('members',[])}-{''}
    if len(narrators)==1:review['narrator']=next(iter(narrators))
    elif len(narrators)>1:reasons.append('Mixed recordings in this group')
    facts={'policy_version':POLICY_VERSION,'source_fingerprint':row['fingerprint'],'work_ids':[work['id']],
        'original_title':text(work.get('original_title') or preferred_title),'authors':names,
        'original_language':{'value':language,'status':'verified' if language else 'unknown'},'recording_language':record_language,
        'title_basis':basis,'author_folder_basis':'verified_full_name',
        'series_state':'verified' if series else 'omitted_unknown','collection':copy.deepcopy(collection),'cover':{'kind':'absent'}}
    if local:facts.update(identity_basis='local_agreement',local_agreement=copy.deepcopy(local))
    validate_policy(row,review,facts)
    return review,facts,reasons

def validate_policy(row,review,facts):
    if not isinstance(facts,dict) or facts.get('policy_version')!=POLICY_VERSION or facts.get('source_fingerprint')!=row.get('fingerprint'):raise ValueError('Standing metadata source binding changed')
    if not isinstance(facts.get('work_ids'),list) or not facts['work_ids'] or len(facts['work_ids'])>100 or any(not isinstance(v,str) or not v or len(v)>200 for v in facts['work_ids']):raise ValueError('Invalid verified work identity')
    authors=facts.get('authors')
    if not isinstance(authors,list) or not authors or len(authors)>30 or any(not isinstance(v,str) or not v or len(v)>300 for v in authors) or review.get('canonical_author')!='; '.join(authors):raise ValueError('Verified author credit changed')
    origin=facts.get('original_language',{})
    language=origin.get('value')
    if origin.get('status')!=('verified' if language else 'unknown') or language and not re.fullmatch('[a-z]{2,3}',language):raise ValueError('Original language provenance invalid')
    if review.get('original_language')!=('Russian' if language=='ru' else 'Other' if language else 'Unknown'):raise ValueError('Original and recording languages confused')
    basis=facts.get('title_basis')
    if basis not in ('published_english','verified_original','source_russian','local_agreement'):raise ValueError('Invalid title provenance')
    identity=facts.get('identity_basis')
    if identity not in (None,'local_agreement'):raise ValueError('Invalid identity provenance')
    if identity=='local_agreement':
        agreed=facts.get('local_agreement')
        from local_identity import KNOWN_AGREEMENT_VERSIONS,IDENTITY_VERSION
        # Books approved under an earlier agreement version keep validating (v0.15.0: v3 and v4).
        if not isinstance(agreed,dict) or agreed.get('version') not in KNOWN_AGREEMENT_VERSIONS:raise ValueError('Local identity agreement record invalid')
        # v5 (Sergei 2026-10-24): one local source is enough for the title and the author.
        # 'entered' / 'approved': Sergei's saved values or his Approve (rulings 6a, 6b).
        states=('green','yellow','one','entered','approved') if agreed.get('version')==IDENTITY_VERSION else ('green','yellow')
        if agreed.get('route'):
            # Ruling 1 collection: the title agrees and the narrator is never the author credit.
            narrators=agreed['route'].get('narrators',[])
            if agreed.get('title',{}).get('state') not in (states if agreed.get('version')==IDENTITY_VERSION else ('green',)) or not review.get('anthology') or (facts.get('collection') or {}).get('kind')!='narrator_collection' or review.get('canonical_author') in narrators:
                raise ValueError('Local collection record invalid')
        elif any(agreed.get(k,{}).get('state') not in states for k in ('title','author')):raise ValueError('Local identity agreement record invalid')
    elif basis=='local_agreement':raise ValueError('Local title provenance without local identity')
    if basis=='source_russian' and review.get('title')!=russian_source_title(row):raise ValueError('Russian source title changed or ambiguous')
    if facts.get('series_state')=='omitted_unknown' and (review.get('series') or review.get('number')):raise ValueError('Unknown series must be omitted')
    if facts.get('series_state')=='verified' and (not review.get('series') or not review.get('number')):raise ValueError('Verified series position required')
    if facts.get('author_folder_basis') not in ('surname_first','verified_full_name'):raise ValueError('Invalid author folder provenance')
    if facts['author_folder_basis']=='verified_full_name' and review.get('author')!='; '.join(authors):raise ValueError('Verified full author name changed')
    if facts.get('cover',{}).get('kind') not in ('embedded','neutral','absent'):raise ValueError('Invalid cover provenance')
    return copy.deepcopy(facts)
