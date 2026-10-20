"""Human-entered metadata evidence, independent of mutable canonical drafts.

Records are append-only and bound to candidate identity + observed source fingerprint.
No record approves a book or takes precedence over a provider.
"""
import copy
import datetime
import json
import uuid

FIELDS=('title','author','canonical_author','original_language','series','number','genre','topic','narrator','universe')

def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS manual_metadata_sources (source_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, fingerprint TEXT NOT NULL, saved_utc TEXT NOT NULL, payload TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS manual_metadata_candidate ON manual_metadata_sources(candidate_id,saved_utc,source_id)')

def capture(row,review,note):
    values={k:v.strip() for k,v in review.items() if k in FIELDS and isinstance(v,str) and v.strip()}
    # Unknown original language is not evidence of a language disagreement.
    if values.get('original_language','').casefold() in {'unknown','unverified'}:values.pop('original_language',None)
    for field in ('multi_author','anthology'):
        if review.get(field) is True:values[field]=True
    if not values and not note.strip():return None
    return {'source_id':str(uuid.uuid4()),'candidate_id':row['id'],'fingerprint':row['fingerprint'],
            'saved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'provider':'Entered by you','actor':'user','values':values,'note':note}

def append(db,record):
    if record is None:return
    # Repeated approval of an unchanged preview does not create duplicate evidence.
    last=db.execute('SELECT payload FROM manual_metadata_sources WHERE candidate_id=? AND fingerprint=? ORDER BY saved_utc DESC,source_id DESC LIMIT 1',(record['candidate_id'],record['fingerprint'])).fetchone()
    if last:
        old=json.loads(last[0])
        if old['values']==record['values'] and old['note']==record['note']:return
    db.execute('INSERT INTO manual_metadata_sources VALUES(?,?,?,?,?)',
               (record['source_id'],record['candidate_id'],record['fingerprint'],record['saved_utc'],json.dumps(record,ensure_ascii=False)))

def records(db,row):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='manual_metadata_sources' AND type='table'").fetchone():return []
    result=[]
    for saved in db.execute('SELECT payload FROM manual_metadata_sources WHERE candidate_id=? ORDER BY saved_utc,source_id',(row['id'],)):
        record=json.loads(saved[0]);record['status']='current' if record['fingerprint']==row['fingerprint'] else 'stale'
        result.append(record)
    return result

def proposals(sources):
    current=[r for r in sources if r['status']=='current']
    if not current:return []
    # Show the latest saved manual source, retaining prior records for inspection.
    r=current[-1];v=r['values']
    return [{'id':r['source_id'],'provider':'Entered by you','public_url':'',
             'title':v.get('title',''),'authors':v.get('canonical_author') or v.get('author',''),
             'original_language':v.get('original_language',''),'series':v.get('series',''),
             'number':v.get('number',''),'universe':v.get('universe',''),
             'per_field_evidence':copy.deepcopy(r),'manual_source':True}]

def compare(manual,providers):
    """Explicit disagreements only; blank fields never defeat another source."""
    norm=lambda x:' '.join(str(x).casefold().split())
    conflicts=[]
    for own in manual:
        for other in providers:
            for field in ('title','authors','series','number','universe'):
                left=own.get(field);right=other.get(field)
                if isinstance(left,list):left='; '.join(left)
                if isinstance(right,list):right='; '.join(right)
                if left and right and norm(left)!=norm(right):
                    conflicts.append({'field':field,'manual_value':left,'other_value':right,'manual_source_id':own.get('id'),'other_source_id':other.get('id'),'other_provider':other.get('provider','Source'),'other_source_url':other.get('public_url',''),'cause':'metadata_conflict'})
    return conflicts


def acceptance(row,review):
    import hashlib
    payload=json.dumps(review,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return {'schema':'manual-metadata-acceptance-v1','fingerprint':row['fingerprint'],
            'review_sha256':hashlib.sha256(payload.encode()).hexdigest()}

def approved(row,ctx):
    proof=ctx.get('manual_metadata_acceptance')
    return bool(ctx.get('metadata_approved') and ctx.get('metadata_actor')=='user' and ctx.get('manual_note','').strip()
                and proof==acceptance(row,row.get('review') or {}))


# Conversion of the existing producer's exact legacy reasons, never UI text heuristics.
# Unknown reasons remain unclassified; source/order/audio failures are excluded.
_METADATA_HOLDS={
 'Sources disagree on the title or author':('metadata_conflict',['title','canonical_author']),
 'Book identity uncertain':('identity_uncertain',['title','canonical_author']),
 'Cover not verified':('cover_unverified',[]),
}
def holds(automatic):
    if not automatic or automatic.get('state')!='Held':return []
    result=copy.deepcopy(automatic.get('metadata_holds',[]))
    for reason in automatic.get('reasons',[]):
        typed=_METADATA_HOLDS.get(reason)
        if typed:result.append({'cause':typed[0],'fields':list(typed[1]),'reason':reason})
    return result


def compare_research(entered,result):
    from source_identity import norm,title_matches,author_matches
    work=result.get('work') or {};review=result.get('review') or {}
    if not work and not review:return []  # Absent provider identity is not disagreement.
    aliases={norm(v) for v in work.get('titles',[]) if v}
    authors={norm(v) for v in work.get('author_aliases',[]) if v}
    if review.get('title'):aliases.add(norm(review['title']))
    if review.get('canonical_author'):authors.add(norm(review['canonical_author']))
    result_conflicts=[]
    for own in entered:
        if own.get('title') and aliases and not title_matches(own['title'],aliases,work.get('author_aliases',[])):
            result_conflicts.append({'field':'title','manual_value':own['title'],'other_value':review.get('title') or list(work.get('titles',[])),'other_work_id':work.get('id'),'other_aliases':list(work.get('titles',[])),'manual_source_id':own['id'],'other_sources':copy.deepcopy([s for s in result.get('sources',[]) if s.get('kind')!='manual_metadata']),'cause':'metadata_conflict'})
        credit=own.get('authors')
        if credit and authors and norm(credit) not in authors and not author_matches(credit,authors):
            result_conflicts.append({'field':'canonical_author','manual_value':credit,'other_value':review.get('canonical_author') or list(work.get('author_aliases',[])),'other_work_id':work.get('id'),'manual_source_id':own['id'],'other_sources':copy.deepcopy([s for s in result.get('sources',[]) if s.get('kind')!='manual_metadata']),'cause':'metadata_conflict'})
        for field in ('series','number','universe'):
            if own.get(field) and review.get(field) and norm(own[field])!=norm(review[field]):
                result_conflicts.append({'field':field,'manual_value':own[field],'other_value':review[field],'other_work_id':work.get('id'),'manual_source_id':own['id'],'other_sources':copy.deepcopy([s for s in result.get('sources',[]) if s.get('kind')!='manual_metadata']),'cause':'metadata_conflict'})
    return result_conflicts
