"""Rebind only an explicit relocation decision; never alter its historical manifest."""
import copy

def for_relocation(manifest,review,evidence):
    from shared_routing import resolve,build
    from publication_locations import _digest
    original=manifest['metadata'];facts=manifest.get('metadata_facts')
    if not isinstance(facts,dict) or 'shared_routing' not in facts:return manifest
    resolve(original,facts)  # Reject an already stale or malformed historical proof.
    if review==original:return manifest
    changed={key for key in set(original)|set(review) if original.get(key)!=review.get(key)}
    if changed-{'universe','multi_author'} or len(evidence)!=1:raise ValueError('Shared routing changes require one explicit relocation decision')
    decision=evidence[0]
    if decision.get('actor')!='user' or not decision.get('evidence') or decision.get('candidate_id')!=manifest.get('candidate_id'):
        raise ValueError('Shared routing decision is not bound to this book')
    if decision.get('review_sha256')!=_digest(original) or decision.get('fingerprint')!=facts.get('source_fingerprint'):
        raise ValueError('Shared routing decision source or accepted review changed')
    values=decision.get('values') or {}
    if set(values)-{'universe','multi_author'} or any(review.get(key)!=value for key,value in values.items()) or not changed<=set(values):
        raise ValueError('Shared routing decision does not match the requested route')
    planned=copy.deepcopy(manifest);new=planned['metadata_facts'];proof=new.pop('shared_routing')
    series=proof.get('series')
    world=proof.get('universe') if review.get('universe')==original.get('universe') else None
    if series or world:new['shared_routing']=build(review,new,series=series,universe=world)
    return planned
