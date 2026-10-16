"""Private installer preparation worker, authorized only by live native lease."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).absolute().parent.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from build_native import bootstrap,lease_check

def run(argv, proof, cwd=ROOT):
    remaining=max(1,(proof['deadline']-time.time()*1000)/1000)
    result=subprocess.run(argv,cwd=cwd,capture_output=True,timeout=remaining,creationflags=0x08000000,env=os.environ.copy())
    # electron-builder reports its errors on stdout, so a stderr-only message is empty.
    # Separate bounded tails: a long stdout can never push stderr out of the message.
    if result.returncode:raise RuntimeError('Build command failed '+str(argv[:2])+'\nstderr tail: '+result.stderr.decode(errors='replace')[-4000:]+'\nstdout tail: '+result.stdout.decode(errors='replace')[-4000:])
    return result.stdout.decode('utf8',errors='strict').replace('\r\n','\n')

def prepare(tree,proof):
    owned=tree.directory(proof['ownedRoot']);tree.created[str(owned).casefold()]=owned
    pins_path=ROOT/'desktop'/'runtime-pins.json';tree.protect(pins_path)
    pins=json.loads(pins_path.read_text('utf8'));runtime=tree.directory(owned/'runtime',create=True)
    for name in ['python','ffmpeg']:
        pin=pins[name]
        if not pin['url'].startswith('https://') or len(pin['sha256'])!=64:raise RuntimeError('Invalid trusted runtime pin')
        existing=ROOT/'build-cache'/'downloads'/(name+'-'+pin['version'])/pin['file']
        if existing.exists():
            facts=tree.protect(existing)
            if facts['sha256']!=pin['sha256']:raise RuntimeError('Cached archive fingerprint differs; preserved')
            archive=existing
        else:
            archive=owned/'downloads'/pin['file']
            request=urllib.request.Request(pin['url'],headers={'User-Agent':'Books-Arranger-build'})
            with urllib.request.urlopen(request,timeout=60) as response:
                if not response.url.startswith('https://'):raise RuntimeError('Runtime redirect is not HTTPS')
                facts=tree.write(archive,iter(lambda:response.read(1024*1024),b''))
            if facts['sha256']!=pin['sha256']:raise RuntimeError('Downloaded runtime fingerprint differs; preserve for investigation')
        extracted=tree.directory(owned/'extract'/name,create=True)
        tree.extract_zip(archive,extracted)
        destination=tree.directory(runtime/name,create=True)
        if name=='python':
            for relative in tree.tree_manifest(extracted):tree.copy(extracted/relative,destination/relative)
            output=run([str(destination/'python.exe'),'-I','-B','-c','import sys,sqlite3,ctypes,ssl,hashlib,zlib,json,http.server,msvcrt;print(sys.version.split()[0])'],proof).strip()
            if output!=pin['version']:raise RuntimeError('Bundled Python version mismatch')
        else:
            children=list(extracted.iterdir())
            if len(children)!=1 or not children[0].is_dir():raise RuntimeError('Unexpected FFmpeg archive layout')
            top=tree.directory(children[0]);bin_path=tree.directory(top/'bin')
            for source in bin_path.iterdir():
                if source.name in ['ffmpeg.exe','ffprobe.exe'] or source.suffix.lower()=='.dll':tree.copy(source,destination/source.name)
            tree.copy(top/'LICENSE.txt',destination/'LICENSE.txt')
            version=run([str(destination/'ffmpeg.exe'),'-hide_banner','-version'],proof)
            run([str(destination/'ffprobe.exe'),'-hide_banner','-version'],proof)
            if '--enable-gpl' in version or '--enable-nonfree' in version:raise RuntimeError('FFmpeg license configuration refused')
            license_text=run([str(destination/'ffmpeg.exe'),'-hide_banner','-L'],proof)
            tree.write(destination/'BUILD.txt',[(json.dumps(pin,indent=2)+'\n'+version+'\n'+license_text).encode()])
    backend=tree.directory(owned/'backend',create=True)
    pkg=json.loads((ROOT/'package.json').read_text('utf8'))
    for source in ROOT.glob('*.py'):
        if source.name not in {'app.py','install_app_entries.py'}:tree.copy(source,backend/source.name)
    for name in ['public_source_leads.json','replacement_eye_plan.json']:tree.copy(ROOT/name,backend/name)
    for source in (ROOT/'web').iterdir():tree.copy(source,backend/'web'/source.name)
    tree.write(backend/'VERSION',[(pkg['version']+'\n').encode()])
    python=runtime/'python'/'python.exe'
    run([str(python),'-I','-m','compileall','-q','-j','0','--invalidation-mode','unchecked-hash',str(backend)],proof)
    version=run([str(python),'-I','-B','-c','import sys;sys.path.insert(0,sys.argv[1]);import desktop_backend,web_server;print(web_server.version())',str(backend)],proof).strip()
    if version!=pkg['version']:raise RuntimeError('Staged backend version mismatch')
    return runtime,backend,pins,pkg

def build(tree,proof,runtime,backend,pins,pkg,prior):
    # electron-builder extracts Electron to win-unpacked.tmp then renames it to
    # win-unpacked inside this directory; that rename needs WRITE (not DELETE) sharing.
    output=tree.fresh(ROOT/'dist'/'builds',allow_child_rename=True);build_id=output.name
    config={**pkg['build'],'directories':{**pkg['build']['directories'],'output':str(output)},'extraResources':[{'from':str(backend),'to':'backend'},{'from':str(runtime/'python'),'to':'python'},{'from':str(runtime/'ffmpeg'),'to':'ffmpeg'}],'artifactName':'Books-Arranger-Setup-'+pkg['version']+'.exe'}
    config_path=Path(proof['ownedRoot'])/'builder-config.json'
    tree.write(config_path,[json.dumps(config,indent=2).encode()])
    run([proof['node'],str(ROOT/'node_modules'/'electron-builder'/'cli.js'),'--win','--publish','never','--config',str(config_path)],proof)
    # Final verification is intentionally a separate held-source Node worker,
    # using @electron/asar, and refuses to emit a verified manifest until the
    # NSIS embedded app64.7z payload has been independently compared.
    request={**proof,'build_id':build_id,'output':str(output),'runtime':str(runtime),'backend':str(backend),'pins':pins,'version':pkg['version']}
    tree.write(Path(proof['ownedRoot'])/'build-result.json',[json.dumps(request).encode()])
    seven=ROOT/'node_modules'/'7zip-bin'/'win'/'x64'/'7za.exe'
    tree.protect(seven)
    installer=output/('Books-Arranger-Setup-'+pkg['version']+'.exe')
    installer_size=tree.protect(installer)['size']
    listing=run([str(seven),'l','-slt',str(installer)],proof)
    def entries(text):
        result=[]
        for block in text.split('----------')[-1].split('\n\n'):
            properties=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
            if 'Path' in properties:result.append(properties)
        return result
    # 7zip-bin's reduced 7za has no NSIS handler: it opens the installer AS the one
    # embedded app 7z it finds at an offset (NSIS stub before it, NSIS data after it).
    # Require exactly that shape, then carve those exact bytes from the held installer
    # handle. Member checks and the payload-equality verifier below are unchanged.
    sections=listing.split('\n--\n')
    header=dict(line.split(' = ',1) for line in sections[-1].split('\n----------\n')[0].splitlines() if ' = ' in line) if len(sections)==2 else {}
    try:offset,physical,tail=int(header['Offset']),int(header['Physical Size']),int(header.get('Tail Size','0'))
    except (KeyError,ValueError):raise RuntimeError('Expected exactly one embedded NSIS app 7z archive')
    if header.get('Type')!='7z' or offset<=0 or physical<=0 or tail<0 or offset+physical+tail!=installer_size:raise RuntimeError('Expected exactly one embedded NSIS app 7z archive')
    held_installer=tree.files[str(tree.child(installer)).casefold()]
    def carve():
        position=0
        for block in held_installer.chunks():
            start=max(offset-position,0);end=min(offset+physical-position,len(block));position+=len(block)
            if start<end:yield block[start:end]
            if position>=offset+physical:return
    embedded=tree.fresh(Path(proof['ownedRoot'])/'nsis-archive')
    app_archive=embedded/'app-64.7z'
    if tree.write(app_archive,carve())['size']!=physical:raise RuntimeError('Embedded NSIS app archive carve incomplete')
    if next(tree.files[str(tree.child(app_archive)).casefold()].chunks(),b'')[:6]!=b"7z\xbc\xaf'\x1c":raise RuntimeError('Carved NSIS app archive signature refused')
    payload=tree.fresh(Path(proof['ownedRoot'])/'nsis-payload')
    app_listing=run([str(seven),'l','-slt',str(app_archive)],proof)
    if sorted(e['Path'] for e in entries(app_listing))!=sorted(e['Path'] for e in entries(listing)):raise RuntimeError('Carved NSIS app archive members differ from installer listing')
    names=set()
    for properties in entries(app_listing):
        relative=properties['Path']
        canonical=relative.replace('\\','/')
        if not canonical or canonical.startswith('/') or ':' in canonical or any(p in ('.','..') for p in canonical.split('/')) or canonical.casefold() in names or properties.get('Symbolic Link') or properties.get('Hard Link'):raise RuntimeError('NSIS app payload member refused')
        names.add(canonical.casefold())
        destination=tree.child(payload/canonical)
        tree.directory(destination if properties.get('Folder')=='+' else destination.parent,create=True)
    run([str(seven),'x',str(app_archive),'-o'+str(payload),'-y'],proof)
    tree.tree_manifest(payload);tree.tree_manifest(output/'win-unpacked')
    request['nsis_payload']=str(payload)
    remaining=max(1,(proof['deadline']-time.time()*1000)/1000)
    verifier=subprocess.run([proof['node'],str(ROOT/'scripts'/'build-manifest.mjs')],cwd=ROOT,input=json.dumps(request).encode(),capture_output=True,timeout=remaining,creationflags=0x08000000,env=os.environ.copy())
    if verifier.returncode:raise RuntimeError('Installer verification refused: '+verifier.stderr.decode(errors='replace')[-8000:])
    manifest=json.loads(verifier.stdout)
    if manifest.get('payload',{}).get('verified') is not True:raise RuntimeError('Verifier did not attest actual payload')
    from build_fs_guard import producer_receipt,publish_metadata,disposable_stage_receipts,retire_disposable_stage
    # New metadata is fully materialized/verified before touching old pointers.
    # CREATE_NEW unique temporaries and a native producer record bind every old
    # file identity in a later run; a schema/hash-only file is never adopted.
    tree.created[str(ROOT/'dist').casefold()]=ROOT/'dist'
    tree.created[str(ROOT/'build-cache').casefold()]=ROOT/'build-cache'
    import uuid
    transaction=str(uuid.uuid4())
    manifest_temp=ROOT/'dist'/('release-artifacts.json.new-'+transaction)
    pointer_temp=ROOT/'build-cache'/('runtime-pointer.json.new-'+transaction)
    tree.write(manifest_temp,[verifier.stdout])
    runtime_files=dict(sorted(tree.tree_manifest(runtime).items()))
    pointer={'schema':'books-runtime-pointer-v1','build_id':build_id,'root':str(runtime),'files':runtime_files,'manifest_sha256':hashlib.sha256(json.dumps(runtime_files,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    tree.write(pointer_temp,[json.dumps(pointer,sort_keys=True,separators=(',',':')).encode()])
    record=producer_receipt(tree,Path(proof['ownedRoot']),manifest,pointer,manifest_temp,pointer_temp)
    record['disposable_stage_files']=disposable_stage_receipts(tree,Path(proof['ownedRoot']))
    tree.write(Path(proof['ownedRoot'])/'producer-receipt.json',[json.dumps(record,sort_keys=True,separators=(',',':')).encode()])
    tree.write(Path(proof['ownedRoot'])/'metadata-rotation-plan.json',[json.dumps({'schema':'books-build-rotation-plan-v1','transaction':transaction,'old':prior.plans,'new':{'manifest':str(manifest_temp),'pointer':str(pointer_temp)},'producer_receipt':str(Path(proof['ownedRoot'])/'producer-receipt.json'),'state':'verified-new-before-old-archive'},sort_keys=True).encode()])
    archived=prior.archive()
    tree.write(Path(proof['ownedRoot'])/'metadata-rotation-archives.json',[json.dumps({'schema':'books-build-rotation-archives-v1','transaction':transaction,'archived':archived},sort_keys=True).encode()])
    try:
        pointer_receipt=publish_metadata(tree,pointer_temp,ROOT/'build-cache'/'runtime-pointer.json')
        manifest_receipt=publish_metadata(tree,manifest_temp,ROOT/'dist'/'release-artifacts.json')
    except Exception:
        # Never overwrite an unexpected stable path. Exact archived originals,
        # unique new files and durable intent remain for an explicit recovery.
        # A missing/colliding pair is refused by subsequent preparation.
        raise RuntimeError('Metadata publication stopped; prior/new evidence preserved at '+str(Path(proof['ownedRoot'])/'metadata-rotation-plan.json'))
    tree.write(Path(proof['ownedRoot'])/'metadata-rotation-complete.json',[json.dumps({'schema':'books-build-rotation-complete-v1','transaction':transaction,'archived':archived,'manifest_receipt':manifest_receipt,'pointer_receipt':pointer_receipt},sort_keys=True).encode()])
    cleanup_warning=None;disposed=0
    try:disposed=retire_disposable_stage(tree,Path(proof['ownedRoot']),record['disposable_stage_files'])
    except Exception as error:cleanup_warning=str(error)
    tree.write(Path(proof['ownedRoot'])/'staging-cleanup-result.json',[json.dumps({'schema':'books-build-staging-cleanup-v1','removed_files':disposed,'warning':cleanup_warning,'old_accepted_artifacts':'preserved','runtime':'preserved','prior_cleanup_requires':['new QA GO and review CLEAR','new runtime owner generation verified','exact old producer native facts','preserve installers/data/recovery/unknown files']},sort_keys=True).encode()])
    print(json.dumps({'verified':True,'output':str(output),'build_id':build_id,'manifest':str(ROOT/'dist'/'release-artifacts.json'),'manifest_sha256':manifest_receipt['sha256'],'prior_archived':archived,'staging_cleanup_removed':disposed,'cleanup_warning':cleanup_warning}))

def main():
    proof=json.loads(sys.stdin.read());proof.pop('manifestPath',None)
    with contextlib.ExitStack() as stack:
        bootstrap(stack);lease_check(proof)
        from build_fs_guard import BuildTree,PriorBuild
        with BuildTree(ROOT) as tree:
            prior=PriorBuild(tree)
            runtime,backend,pins,pkg=prepare(tree,proof)
            build(tree,proof,runtime,backend,pins,pkg,prior)
if __name__=='__main__':
    try:main()
    except Exception as e:print('Guarded build phase: '+str(e),file=sys.stderr);sys.exit(1)
