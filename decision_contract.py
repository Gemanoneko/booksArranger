"""Bounded HTTP intent shape and deterministic, server-derived effect domains."""
import copy
from durable_decisions import digest
from scanner import connect


def effects(action,payload):
    if action=='names':return sorted('names.'+key for key in payload['names'])
    if action=='approve':
        keys={'approval'}|{'names.'+key for key in payload.get('names') or {}}
        for key in ('title','author'):
            if payload.get(key) is not None and payload[key].strip():keys.add('names.'+key)
        return sorted(keys)
    if action in ('review','tracks','metadata_choices','file_review'):return [action]
    raise ValueError('Unsupported saved-decision action')


def file_identity(library,path):return 'file:'+digest({'library':library,'path':path})


def file_fingerprint(library,path,size,modified):return digest({'library':library,'path':path,'size':size,'modified':modified})


def file_row(inventory,library,path):
    roots=inventory.source_roots(library) if hasattr(inventory,'source_roots') else (inventory.roots[library],)
    with connect(inventory.database) as db:
        rows=[dict(row) for row in db.execute('SELECT root,path,size,modified,kind,error,missing FROM files WHERE path=?',(path,)) if row['root'] in roots]
    if len(rows)!=1 or rows[0]['kind'] not in ('audiobook','ebook'):raise ValueError('Only a known audiobook/ebook catalog file can receive saved metadata')
    return rows[0]


def validate(handler,action,payload):
    """Validate without normalizing away any byte of the submitted JSON values."""
    if not isinstance(payload,dict):raise ValueError('Saved choices must be an object')
    if action=='names':
        handler.shape(payload,{'names'});handler.names_value(payload['names'])
    elif action=='approve':
        handler.shape(payload,set(),{'title','author','names','without_missing','choice','path'})
        for key in ('title','author','path'):handler.text_value(payload.get(key),1000,nullable=True)
        if payload.get('names') is not None:handler.names_value(payload['names'],partial=True)
        if type(payload.get('without_missing',False)) is not bool or payload.get('choice') not in (None,'same','different'):raise ValueError('Invalid saved approval choice')
    elif action=='review':
        handler.shape(payload,{'review','approve'},{'manual_note','proposal_id','cover_id','names_row_only'})
        handler.review_data(copy.deepcopy(payload['review']))
        if type(payload['approve']) is not bool or type(payload.get('names_row_only',False)) is not bool:raise ValueError('Review choices must be explicit booleans')
        handler.text_value(payload.get('manual_note',''))
        for key in ('proposal_id','cover_id'):
            if payload.get(key) is not None:handler.uuid_value(payload[key])
    elif action=='tracks':
        handler.shape(payload,{'order','included','source_coverage_confirmed','order_confirmed','chapters'},{'evidence_note'})
        for key in ('order','included'):
            values=payload[key]
            if not isinstance(values,list) or len(values)>10000 or any(not isinstance(value,str) or not 1<=len(value)<=128 for value in values) or len(set(values))!=len(values):raise ValueError('Invalid bounded source member list')
        for key in ('source_coverage_confirmed','order_confirmed','chapters'):
            if type(payload[key]) is not bool:raise ValueError('Track choices must be explicit booleans')
        handler.text_value(payload.get('evidence_note',''))
    elif action=='metadata_choices':
        handler.shape(payload,{'signature','choices'},{'manual_note'});handler.text_value(payload['signature'],1000);handler.text_value(payload.get('manual_note',''))
        if not isinstance(payload['choices'],list) or len(payload['choices'])>100 or any(not isinstance(value,dict) for value in payload['choices']):raise ValueError('Invalid saved metadata choices')
    elif action=='file_review':
        handler.shape(payload,{'path','size','modified','review'})
        handler.text_value(payload['path'],32767)
        if type(payload['size']) is not int or payload['size']<0 or not isinstance(payload['modified'],str) or not payload['modified'].isascii() or not payload['modified'].isdigit() or len(payload['modified'])>19 or int(payload['modified'])>9223372036854775807:raise ValueError('Invalid saved source fingerprint')
        handler.review_data(copy.deepcopy(payload['review']))
    else:raise ValueError('Unsupported saved-decision action')
    return copy.deepcopy(payload)
