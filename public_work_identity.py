"""Small, pure catalog adapters; labels/edition languages never authorize recording work."""
import re

class EvidenceConflict(ValueError):pass

KINDS={'novel','novella','novelette','short story','literary work','poem','play'}

def item(value):
    return value if isinstance(value,str) and re.fullmatch(r'Q[1-9][0-9]{0,11}',value) else None

def claims(entity,property):
    data=entity.get('claims',{}) if isinstance(entity,dict) else {}
    if not isinstance(data,dict):raise ValueError('Malformed catalog claims')
    values=data.get(property,[])
    if not isinstance(values,list) or len(values)>30:raise ValueError('Malformed work claims')
    return [c for c in values if isinstance(c,dict) and c.get('rank')!='deprecated']

def values(entity,property):
    result=[]
    for claim in claims(entity,property):
        snak=claim.get('mainsnak',{})
        if not isinstance(snak,dict) or snak.get('property')!=property:raise EvidenceConflict('Conflicting catalog relationship property')
        if snak.get('snaktype') not in ('value','novalue','somevalue'):raise ValueError('Malformed work claim')
        qualifiers=claim.get('qualifiers',{})
        if property in ('P50','P407') and (not isinstance(qualifiers,dict) or qualifiers):raise EvidenceConflict('Qualified work identity relationship needs stronger evidence')
        if snak.get('snaktype')!='value':continue
        data=snak.get('datavalue',{})
        if not isinstance(data,dict):raise ValueError('Malformed work value')
        result.append(data.get('value'))
    return result

def ids(entity,property):
    found=[]
    for value in values(entity,property):
        id=item(value.get('id')) if isinstance(value,dict) else None
        if not id:raise ValueError('Invalid catalog entity relationship')
        if id not in found:found.append(id)
    return found

def names(entity):
    result=[]
    for language in ('en','ru','ja'):
        label=entity.get('labels',{}).get(language,{})
        if isinstance(label,dict) and isinstance(label.get('value'),str):result.append(label['value'])
        aliases=entity.get('aliases',{}).get(language,[])
        if not isinstance(aliases,list):raise ValueError('Malformed catalog aliases')
        result.extend(a['value'] for a in aliases[:20] if isinstance(a,dict) and isinstance(a.get('value'),str))
    result.extend(v['text'] for v in values(entity,'P1476') if isinstance(v,dict) and isinstance(v.get('text'),str))
    return list(dict.fromkeys(v for v in result if v and len(v)<=500))

def label(entity,language):
    value=entity.get('labels',{}).get(language,{})
    return value.get('value','') if isinstance(value,dict) and isinstance(value.get('value',''),str) else ''

def series_position(entity,related):
    relations=claims(entity,'P179')
    live=[c for c in relations if c.get('mainsnak',{}).get('snaktype')=='value']
    if len(live)!=1:return None
    relation=live[0];snak=relation.get('mainsnak',{})
    if snak.get('property')!='P179':raise EvidenceConflict('Conflicting series relationship property')
    id=item(snak.get('datavalue',{}).get('value',{}).get('id'))
    qualifiers=relation.get('qualifiers',{})
    if not isinstance(qualifiers,dict) or set(qualifiers)!={'P1545'}:return None
    ordinal=qualifiers['P1545']
    if not isinstance(ordinal,list) or len(ordinal)!=1:return None
    ordinal=ordinal[0]
    if ordinal.get('property')!='P1545' or ordinal.get('snaktype')!='value':return None
    number=ordinal.get('datavalue',{}).get('value')
    name=label(related.get(id,{}),'en') or label(related.get(id,{}),'ru')
    if not name or not isinstance(number,str) or not re.fullmatch(r'[0-9]{1,4}(?:\.[0-9]{1,3})?',number):return None
    return {'name':name,'number':number,'source_url':'https://www.wikidata.org/wiki/'+entity['id']}

def wikidata_work(entity,related,title,author,norm,credit_matches):
    if norm(title) not in {norm(v) for v in names(entity)}:return None
    if ids(entity,'P629'):return None # edition-of relation is not original-work evidence
    authors=ids(entity,'P50');languages=ids(entity,'P407');types=ids(entity,'P31')
    if len(authors)>1 and any(credit_matches(author,v) for id in authors for v in names(related.get(id,{}))):raise EvidenceConflict('Multiple-author work needs stronger evidence')
    if len(authors)!=1:return None
    person=related.get(authors[0],{})
    aliases=names(person)
    if not author or not any(credit_matches(author,v) or len(str(author).split())==1 and len(v.split())==2 and norm(author)==norm(v.split()[-1]) for v in aliases):return None
    if len(languages)>1:raise EvidenceConflict('Conflicting original work languages')
    language=related.get(languages[0],{}) if languages else {}
    kinds={label(related.get(id,{}),'en').casefold() for id in types}
    if any('collection' in kind or 'anthology' in kind for kind in kinds):raise EvidenceConflict('Anthology author credits need stronger evidence')
    if not kinds.intersection(KINDS):return None
    codes=[v for v in values(language,'P218') if isinstance(v,str) and re.fullmatch('[a-z]{2,3}',v)]
    if len(set(codes))>1:raise EvidenceConflict('Conflicting original work languages')
    code=codes[0] if codes else ''
    original=list(dict.fromkeys(v['text'] for v in values(entity,'P1476') if isinstance(v,dict) and (not code or v.get('language')==code) and isinstance(v.get('text'),str) and v['text']))
    if len(original)>1:raise EvidenceConflict('Conflicting original work titles')
    if len(original)!=1:return None
    series=claims(entity,'P179')
    standalone=bool(series and all(c.get('mainsnak',{}).get('snaktype')=='novalue' for c in series))
    native=label(person,'ru') if code=='ru' else label(person,'en')
    english=label(entity,'en')
    if not native:return None
    return {'provider':'wikidata','work_id':entity['id'],'work_name':original[0] if code=='ru' else label(entity,'ru') or original[0],
        'work_name_orig':original[0],'work_name_alts':names(entity),'lang_code':code,'image':'','work_type_name':next(iter(sorted(kinds.intersection(KINDS)))),
        'authors':[{'type':'autor','name':label(person,'ru') or native,'name_orig':label(person,'en') or native}],
        'parents':{'cycles':[] if standalone else None,'digest':{}},'work_root_saga':[],
        'translations':[{'lang_code':'en','translations':[{'titles':[{'title':english}]}]}] if english else [],
        'source_url':'https://www.wikidata.org/wiki/'+entity['id'],'standalone_confirmed':standalone,'known_series':bool(series and not standalone),'author_aliases':aliases,'verified_series':series_position(entity,related)}

def openlibrary_matches(data,titles,authors,norm,credit_matches):
    docs=data.get('docs',[]) if isinstance(data,dict) else []
    if not isinstance(docs,list):raise ValueError('Malformed Open Library work result')
    found={}
    for record in docs[:5]:
        if not isinstance(record,dict) or not re.fullmatch('/works/OL[1-9][0-9]{0,11}W',str(record.get('key',''))):continue
        title=record.get('title');names=record.get('author_name',[])
        if not isinstance(title,str) or not isinstance(names,list) or len(names)!=1 or not isinstance(names[0],str):continue
        if norm(title) not in {norm(v) for v in titles} or not any(credit_matches(names[0],name) for name in authors):continue
        found[record['key']]=record
    return list(found.values())

def primary_fields(pair,phrase):
    """Explicit facts immediately attached to this already verified author/title credit."""
    block=pair.get('excerpt','').casefold().replace('ё','е')
    separator=r'[\s.,:;–—\-()«»“”"\x27]{1,30}'
    found={'standalone':False,'language':None}
    for pattern in (phrase(pair['author'])+separator+phrase(pair['title']),phrase(pair['title'])+separator+phrase(pair['author'])):
        match=re.search(pattern,block)
        if not match:continue
        tail=re.sub(r'^[\s,.():;–—-]*','',block[match.end():match.end()+200])
        standalone=re.match(r'(?:(?:a|an|the) )?stand[ -]?alone (?:novel|book|short story)\b|(?:самостоятельный|внесерийный) (?:роман|рассказ)\b',tail)
        if standalone:
            found['standalone']=True;tail=re.sub(r'^[\s,.():;–—-]*','',tail[standalone.end():])
        language=re.match(r'(?:original language\s*:|originally written in|язык оригинала\s*:)\s*(english|russian|английский|русский)\b',tail)
        if language:found['language']='en' if language[1] in ('english','английский') else 'ru'
    return found
