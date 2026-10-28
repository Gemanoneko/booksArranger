"""Versioned hierarchy planner; activation requires publication relocation support.

Only accepted metadata enters this pure planner. Directory names are never evidence.
Legacy publications keep their frozen path until a relocation binding is committed.
"""
import os
from metadata import safe_name

POLICY='books-hierarchy-v2'
# Sergei 2026-10-24, rulings 11 and 11a: a book Sergei approves with no author anywhere, and none typed, is filed as
# Без автора\<Title>.m4b (no author in the file name). It is the last resort: the app asks for the author first.
NO_AUTHOR='Без автора'

def plan(output_root,review,*,collection_fallback='legacy',facts=None):
    if not isinstance(output_root,str) or not os.path.isabs(output_root):raise ValueError('Output root must be absolute')
    if collection_fallback!='legacy':raise ValueError('Collection fallback needs an accepted product decision')
    def text(field):
        value=review.get(field,'')
        if not isinstance(value,str) or len(value)>2000:raise ValueError('Routing fields must be bounded text')
        return value.strip()
    title=text('title');author=text('author') or text('canonical_author')
    cycle=text('series');universe=text('universe');number=text('number')
    collection=review.get('anthology',False);multi=review.get('multi_author',False)
    if type(collection)is not bool or type(multi)is not bool:raise ValueError('Routing choices must be explicit booleans')
    if not author:raise ValueError('Confirm the author credit')
    if not title and not (collection and (cycle or universe)):raise ValueError('Confirm the book title')
    if author==NO_AUTHOR and not collection:
        destination=os.path.join(output_root,NO_AUTHOR,safe_name(title)+'.m4b')
        if len(destination)>240:raise ValueError('Verified metadata exceeds the supported Windows output path length')
        return {'policy_version':POLICY,'root':output_root,'path':destination,'relative_path':os.path.relpath(destination,output_root),
                'accepted_routing':{'author':author,'cycle':'','universe':'','number':'','collection':False,'multi_author_cycle':False}}
    if multi and not (cycle or universe or collection):raise ValueError('Confirm the cycle or universe')
    if collection and cycle and number and title and not universe and not multi:
        # 0.22.2 (Sergei 2026-10-26, «Протоколы SCP»; Brief: "Сборники/Series for a series of collections"): a collection
        # with its series and position files under Сборники\<Series>\ with the series naming of every book,
        # "<Series> - <N> - <Title> - <Author>". Without a position it files as before.
        from anthology_volumes import STORY_FAMILY
        parts=(cycle,number,title,author)
        # Sergei explicitly approved concise filenames only for these four confirmed, already-numbered anthology titles.
        if cycle==STORY_FAMILY and number in {'1','2','3','4'} and title==cycle+' '+number:parts=(title,author)
        destination=append_recording_suffix(os.path.join(output_root,'Сборники',safe_name(cycle),' - '.join(safe_name(v) for v in parts)+'.m4b'),review,facts)
        if len(destination)>240:raise ValueError('Verified metadata exceeds the supported Windows output path length')
        return {'policy_version':POLICY,'root':output_root,'path':destination,'relative_path':os.path.relpath(destination,output_root),
                'accepted_routing':{'author':author,'cycle':cycle,'universe':'','number':number,'collection':True,'multi_author_cycle':False}}
    folders=[]
    if universe:
        folders.append(safe_name(universe))
        if cycle:folders.append(safe_name(cycle))
    elif cycle:
        if not multi:folders.append(safe_name(author))
        folders.append(safe_name(cycle))
    elif collection:folders.append('Сборники')  # Preserve unspecified existing behavior.
    else:folders.append(safe_name(author))
    if collection and (cycle or universe):
        applicable=cycle or universe
        stem=' - '.join([safe_name(v) for v in (title,applicable) if v]+['Short Stories'])
    else:
        if cycle and not number:raise ValueError('Confirm series position; do not invent a number')
        stem=' - '.join(safe_name(v) for v in ([cycle,number,title,author] if cycle else [title,author]))
    destination=append_recording_suffix(os.path.join(output_root,*folders,stem+'.m4b'),review,facts)
    if len(destination)>240:raise ValueError('Verified metadata exceeds the supported Windows output path length')
    return {'policy_version':POLICY,'root':output_root,'path':destination,'relative_path':os.path.relpath(destination,output_root),
            'accepted_routing':{'author':author,'cycle':cycle,'universe':universe,'number':number,'collection':collection,'multi_author_cycle':multi}}


def append_recording_suffix(destination,review,facts=None):
    """Preview routing uses already policy-validated context, never filename clues."""
    if not facts or not isinstance(facts,dict) or 'destination_suffix' not in facts:return destination
    import re
    suffix=facts['destination_suffix']
    if facts.get('policy_version')!='standing-17-v1' or not isinstance(facts.get('source_fingerprint'),str) or not facts['source_fingerprint'] or not facts.get('work_ids') or facts.get('authors')!=str(review.get('canonical_author','')).split('; '):raise ValueError('Recording suffix source/identity proof changed')
    if not isinstance(suffix,str) or len(suffix)>160 or not re.fullmatch(r'(?:.+ - )?recording-[0-9a-f]{16}',suffix) or safe_name(suffix)!=suffix:raise ValueError('Recording suffix proof malformed')
    result=destination[:-4]+' - '+suffix+'.m4b'
    if len(result)>240:raise ValueError('Verified metadata exceeds the supported Windows output path length')
    return result


def frozen_plan(manifest,output_root,review=None):
    """Reproduce source-derived recording distinction from exact frozen inputs."""
    import hashlib,json
    facts=manifest.get('metadata_facts');metadata=manifest['metadata']
    if isinstance(facts,dict) and 'destination_suffix' in facts:
        from recording_classification import destination_suffix
        tracks=[]
        for source in manifest['sources']:
            chapters=manifest.get('source_chapters',[]) if len(manifest['sources'])==1 and os.path.splitext(source['path'])[1].lower()=='.m4b' else []
            tracks.append({'source_sha256':source['sha256'],'size_bytes':source['size'],'chapter_sha256':hashlib.sha256(json.dumps(chapters,sort_keys=True,separators=(',',':')).encode()).hexdigest()})
        language=facts.get('recording_language') or {}
        candidate={'id':manifest['candidate_id'],'identity_verified':True,'work_ids':facts.get('work_ids'),'collection_kind':(facts.get('collection') or {}).get('kind','single'),'series_volume':metadata.get('number') or None,'narrator':{'value':metadata.get('narrator',''),'verified':bool(metadata.get('narrator'))},'recording_language':{'value':language.get('value'),'verified':language.get('basis') in ('embedded','recording_credit')},'edition':{'value':'','verified':False},'manifest':{'complete':True,'observed_count':len(tracks),'tracks':tracks}}
        if destination_suffix(candidate)!=facts['destination_suffix']:raise ValueError('Frozen recording suffix differs from source-derived proof')
    return plan(output_root,review if review is not None else metadata,facts=facts)
