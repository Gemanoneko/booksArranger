import contextlib, datetime, hashlib, json, os, pathlib, sys
root=pathlib.Path(r"C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger")
retained=pathlib.Path(r"C:/Antigravity Projects/Worktrees/Books Arranger/books-0242-candidate-20261101")
evidence=root/'Docs'/'Evidence'/'v0.24.5_2026-11-04'/'pack-recovery'
sys.path[:0]=[str(root/'scripts'),str(root)]
from build_native import bootstrap
proof={'schema':'books-pack-stale-manifest-recovery-v1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'action':'archive exact stale manifest through existing native CAS; preserve all artifacts and retained runtime'}
def save(): (evidence/'archive-proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
with contextlib.ExitStack() as stack:
    bootstrap(stack)
    from build_fs_guard import BuildTree, PriorBuild, capture_metadata, archive_metadata
    main=stack.enter_context(BuildTree(root)); kept=stack.enter_context(BuildTree(retained))
    source=root/'dist'/'release-artifacts.json'
    if os.path.lexists(root/'build-cache'/'runtime-pointer.json'):raise RuntimeError('Prior-candidate state changed; stop')
    plan=capture_metadata(main,source)
    if plan['receipt']['sha256']!='5c23fe856d8df656793af93f5e6e897727d1e8726f6696e42d9c676b9e9c8832':raise RuntimeError('Exact stale manifest bytes differ')
    old=json.loads(source.read_bytes())
    if (old['version'],old['build_id'])!=('0.24.1','c8f9f07a-1004-4119-8b29-51587040e331'):raise RuntimeError('Exact prior identity differs')
    (evidence/'stale-manifest.json').write_bytes(source.read_bytes())
    manifest=retained/'dist'/'release-artifacts.json'
    pointer=retained/'build-cache'/'runtime-pointer.json'
    if kept.protect(manifest)['sha256']!='a8acd696647c4a231b5724d5237f2c02fab514bb5aa3e6fc7c9f7a8cea93d9d2':raise RuntimeError('Retained artifact manifest differs')
    if kept.protect(pointer)['sha256']!='71ddc7f94cf4ff2bdb18845c0d49a0904c4e11b28e38afe3b91679c408326d65':raise RuntimeError('Retained runtime pointer differs')
    current=json.loads(manifest.read_bytes());runtime=json.loads(pointer.read_bytes())
    if current['build_id']!=runtime['build_id'] or current['build_id']!='c87f0090-7289-4c9b-8eed-eacc948b6d3e':raise RuntimeError('Retained candidate identity differs')
    runtime_root=pathlib.Path(runtime['root'])
    if not runtime_root.is_relative_to(retained/'build-cache'/'builds'):raise RuntimeError('Retained runtime escapes its checkout')
    targets=[]
    def add(tree,path,expected=None):
        path=tree.child(path)
        targets.append((tree,path,expected))
    for tree,base,record in [(main,root,old),(kept,retained,current)]:
        for item in record['artifacts']:add(tree,base/'dist'/item['path'],{'sha256':item['sha256'],'size':item['size']})
        payload=base/'dist'/record['unpacked']
        for name,item in record['payload']['files'].items():add(tree,payload/name,item)
    for name,item in runtime['files'].items():add(kept,runtime_root/name,item)
    add(kept,manifest);add(kept,pointer)
    for tree,base in [(main,root),(kept,retained)]:
        pins=base/'desktop'/'runtime-pins.json'
        if tree.protect(pins)['sha256']!='bd5eb2996b522df8f81c232d32ff5e1a6bb22ae4b1e4cd6d03a6cb1f6ce8f110':raise RuntimeError('Original runtime pins differ')
        add(tree,pins)
    def snapshot():
        rows=[{'path':str(path),**tree.protect(path,expected)} for tree,path,expected in targets]
        raw=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
        return {'files':len(rows),'logical_bytes':sum(r['size'] for r in rows),'inventory_sha256':hashlib.sha256(raw).hexdigest()}
    proof['original_manifest']=plan
    proof['before']=snapshot();proof['state']='VERIFIED_BEFORE_ARCHIVE';save()
    def still_held():
        if os.path.lexists(root/'build-cache'/'runtime-pointer.json'):raise RuntimeError('Unexpected prior runtime pointer arrived')
        for tree in (main,kept):
            for boundary in tree.directories.values():boundary.revalidate()
    previous=archive_metadata(main,plan,still_held)
    proof['archived_path']=previous;proof['state']='ARCHIVED';save()
    archived=capture_metadata(main,previous)
    if archived['receipt']!=plan['receipt']:raise RuntimeError('Archived original native identity differs')
    proof['archived_manifest']=archived
    proof['after']=snapshot()
    if proof['before']!=proof['after']:raise RuntimeError('Retained pins or artifacts changed')
    if os.path.lexists(source) or os.path.lexists(root/'build-cache'/'runtime-pointer.json'):raise RuntimeError('Active stale metadata still present')
    if PriorBuild(main).plans:raise RuntimeError('Unchanged guard does not recognize fresh candidate state')
    proof.update(state='VERIFIED_COMPLETE',unchanged_guard_accepts_fresh_state=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save()
print(json.dumps(proof,indent=2))
