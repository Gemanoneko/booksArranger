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
    if result.returncode:raise RuntimeError('Build command failed '+str(argv[:2])+': '+result.stderr.decode(errors='replace')[-8000:])
    return result.stdout.decode('utf8',errors='strict').replace('\r\n','\n')

def prepare(tree,proof):
    if (ROOT/'dist'/'release-artifacts.json').exists() or (ROOT/'build-cache'/'runtime-pointer.json').exists():raise RuntimeError('Existing accepted candidate/runtime pointer preserved; exact-identity retirement required before a new build')
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

def build(tree,proof,runtime,backend,pins,pkg):
    output=tree.fresh(ROOT/'dist'/'builds');build_id=output.name
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
    tree.protect(installer)
    listing=run([str(seven),'l','-slt',str(installer)],proof)
    members=[]
    for block in listing.split('----------')[-1].split('\n\n'):
        properties=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
        name=properties.get('Path','')
        if name.lower().endswith('.7z') and 'app' in Path(name).name.lower():members.append(name)
    if len(members)!=1:raise RuntimeError('Expected exactly one actual NSIS app64 archive')
    member=members[0]
    if any(p in ('..','.') for p in member.replace('\\','/').split('/')) or ':' in member or member.startswith(('/', '\\')):raise RuntimeError('NSIS embedded archive path refused')
    embedded=tree.fresh(Path(proof['ownedRoot'])/'nsis-archive')
    run([str(seven),'e',str(installer),member,'-o'+str(embedded),'-y'],proof)
    archives=list(embedded.iterdir())
    if len(archives)!=1:raise RuntimeError('NSIS extraction produced unexpected entries')
    app_archive=archives[0];tree.protect(app_archive)
    payload=tree.fresh(Path(proof['ownedRoot'])/'nsis-payload')
    app_listing=run([str(seven),'l','-slt',str(app_archive)],proof)
    names=set()
    for block in app_listing.split('----------')[-1].split('\n\n'):
        properties=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
        relative=properties.get('Path')
        if relative is None:continue
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
    # Stable accepted pointer uses CREATE_NEW only. Previous/unknown manifests
    # refuse publication until exact accepted-identity cleanup is completed.
    tree.created[str(ROOT/'dist').casefold()]=ROOT/'dist'
    manifest_facts=tree.write(ROOT/'dist'/'release-artifacts.json',[verifier.stdout])
    runtime_files=dict(sorted(tree.tree_manifest(runtime).items()))
    pointer={'schema':'books-runtime-pointer-v1','build_id':build_id,'root':str(runtime),'files':runtime_files,'manifest_sha256':hashlib.sha256(json.dumps(runtime_files,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    tree.created[str(ROOT/'build-cache').casefold()]=ROOT/'build-cache'
    tree.write(ROOT/'build-cache'/'runtime-pointer.json',[json.dumps(pointer,sort_keys=True).encode()])
    print(json.dumps({'verified':True,'output':str(output),'build_id':build_id,'manifest':str(ROOT/'dist'/'release-artifacts.json'),'manifest_sha256':manifest_facts['sha256']}))

def main():
    proof=json.loads(sys.stdin.read());proof.pop('manifestPath',None)
    with contextlib.ExitStack() as stack:
        bootstrap(stack);lease_check(proof)
        from build_fs_guard import BuildTree
        with BuildTree(ROOT) as tree:
            runtime,backend,pins,pkg=prepare(tree,proof)
            build(tree,proof,runtime,backend,pins,pkg)
if __name__=='__main__':
    try:main()
    except Exception as e:print('Guarded build phase: '+str(e),file=sys.stderr);sys.exit(1)
