"""Sergei's 2026-11-04 names/route for the three confirmed, still-planned trilogy books.

Catalog work/cycle identity, accepted original title, position, complete Tolkien
credit and source fingerprint bind the decision. A title or author alone never
establishes membership. Frozen publications are not rewritten by this module.
"""
import copy
from datetime import datetime,timezone

DECISION='user:tolkien-trilogy-2026-11-04'
# Time of the durable decision document (37ab171), not a guessed chat timestamp.
RECORDED=datetime.fromisoformat('2026-11-04T19:52:41+00:00')
CYCLE='https://fantlab.ru/work1693'
SERIES='Lord of the Rings'
WORLD='Middle-earth'
WORKS={'The Fellowship of the Ring':('fantlab:1667','1'),
       'The Two Towers':('fantlab:1668','2'),
       'The Return of the King':('fantlab:1669','3')}
AUTHORS={'Tolkien J. R. R.','J. R. R. Tolkien','John Ronald Reuel Tolkien','Джон Рональд Руэл Толкин'}
FIELDS=('title','author','canonical_author','series','number','universe')


def superseded_series(entered,value):
    """Only the old exact Russian spelling predating this superseding decision."""
    if value not in ('Властелин колец','Властелин Колец') or 'series' not in (entered.get('fields') or []):return False
    saved=(entered.get('saved_utc') or {}).get('series')
    if saved is None:return True  # Legacy receipts predate per-field save provenance.
    try:
        moment=datetime.fromisoformat(saved.replace('Z','+00:00'))
        return moment.tzinfo is not None and moment<=RECORDED
    except (ValueError,TypeError,AttributeError):return False


def _binding(review,facts):
    return {'source_fingerprint':facts.get('source_fingerprint'),
            'work_ids':copy.deepcopy(facts.get('work_ids')),
            'authors':copy.deepcopy(facts.get('authors')),
            'review':{field:review.get(field,'') for field in FIELDS}}


def _confirmed(result):
    work=result.get('work') or {};review=result.get('review') or {};facts=result.get('metadata_facts') or {}
    expected=WORKS.get(work.get('original_title'));series=work.get('verified_series') or {}
    identity=work.get('id');authors=facts.get('authors')
    if not expected or not isinstance(identity,str) or not (identity==expected[0] or identity.startswith('local:')):return False
    # Local work IDs are accepted only with the same verified catalog cycle,
    # exact original work title and confirmed position, as the installed Fellowship.
    return (facts.get('work_ids')==[identity] and bool(facts.get('source_fingerprint'))
            and isinstance(authors,list) and len(authors)==1 and authors[0] in AUTHORS
            and review.get('canonical_author')==authors[0] and facts.get('series_state')=='verified'
            and series.get('source_url')==CYCLE and str(series.get('number'))==expected[1]
            and str(review.get('number'))==expected[1]
            and series.get('name') in ('Властелин колец','Властелин Колец',SERIES,'The Lord of the Rings')
            and review.get('series') in ('Властелин колец','Властелин Колец',SERIES,'The Lord of the Rings'))


def apply(result):
    """Detached current decision; later explicit field choices and chosen folders win."""
    out=copy.deepcopy(result);facts=out.get('metadata_facts')
    if not isinstance(facts,dict):return out
    facts.pop('trilogy_routing',None)
    if not _confirmed(out):return out
    review=out['review'];names=(out.get('approval') or {}).get('names') or {}
    saved=facts.get('entered_names') or {};entered=set(saved.get('fields') or [])
    typed=set((out.get('approval') or {}).get('typed_names') or [])
    explicit_series='series' in typed or 'series' in names and 'series' not in entered
    if not explicit_series and ('series' not in entered or superseded_series(saved,review.get('series'))):review['series']=SERIES
    if not review.get('universe') and 'universe' not in names and 'universe' not in entered:review['universe']=WORLD
    if review.get('series')==SERIES and review.get('universe')==WORLD:
        facts['trilogy_routing']={'schema':'books-trilogy-routing-v1','decision':DECISION,
                                  'catalog_cycle':CYCLE,'original_title':out['work']['original_title'],
                                  'binding':_binding(review,facts)}
        evidence=out.setdefault('evidence',[])
        from curated_decisions import evidence as decision_evidence
        for field,value in (('series',SERIES),('universe',WORLD)):
            item=decision_evidence(out,DECISION,field,value)
            if item not in evidence:evidence.append(item)
    return out


def author_world(review,facts):
    """The pure planner's narrowly bound author/world exception, never a name guess."""
    if not isinstance(facts,dict):return False
    receipt=facts.get('trilogy_routing')
    if not isinstance(receipt,dict) or set(receipt)!={'schema','decision','catalog_cycle','original_title','binding'}:return False
    expected=WORKS.get(receipt.get('original_title'))
    binding=_binding(review,facts);ids=facts.get('work_ids');authors=facts.get('authors')
    return (receipt.get('schema')=='books-trilogy-routing-v1' and receipt.get('decision')==DECISION
            and receipt.get('catalog_cycle')==CYCLE and receipt.get('binding')==binding
            and bool(facts.get('source_fingerprint')) and bool(expected) and isinstance(ids,list) and len(ids)==1
            and isinstance(ids[0],str) and (ids[0]==expected[0] or ids[0].startswith('local:'))
            and isinstance(authors,list) and len(authors)==1 and authors[0] in AUTHORS
            and review.get('canonical_author')==authors[0] and review.get('series')==SERIES
            and review.get('universe')==WORLD and review.get('number')==expected[1])


def pending_changed(manifest):
    """Only an accepted, catalog-bound pending manifest needs the new naming plan.

    The queue retains the old manifest and uses its existing set-aside/research
    path. This function never edits a manifest, a saved name or a publication.
    """
    if not isinstance(manifest,dict):return False
    review=manifest.get('metadata') or {};facts=manifest.get('metadata_facts') or {}
    ids=facts.get('work_ids');original=facts.get('original_title')
    if not isinstance(ids,list) or len(ids)!=1 or original not in WORKS:return False
    fields=(manifest.get('evidence') or {}).get('metadata_fields') or []
    citation=any(isinstance(item,dict) and item.get('field')=='series' and item.get('source_url')==CYCLE for item in fields)
    if not citation:return False
    result={'review':review,'metadata_facts':facts,
            'work':{'id':ids[0],'original_title':original,'verified_series':{
                'provider':'fantlab','name':review.get('series'),'number':review.get('number'),'source_url':CYCLE}}}
    corrected=apply(result)
    return bool((corrected.get('metadata_facts') or {}).get('trilogy_routing') and
                (corrected['review']!=review or not author_world(review,facts)))
