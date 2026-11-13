"""Only the freshly compiled NSIS uninstaller generator, under a live build lease."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).absolute().parent.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from build_native import bootstrap,lease_check,strict_json


def current_package_include(filename,sha256):
    value=str(filename)
    if any(c in value for c in '\0\r\n'):raise RuntimeError('Unsafe current-package manifest path')
    value=value.replace('$','$$').replace('"','$\\"')
    return ('!macro BooksCurrentPackagePayload ROOT\n'
        '  File "/oname=${ROOT}\\current-package.json" "'+value+'"\n!macroend\n'
        '!macro BooksCurrentPackageVerify ROOT\n  Push $R8\n'
        '  ${StdUtils.HashFile} $R8 "SHA2-256" "${ROOT}\\current-package.json"\n'
        '  ${If} $R8 != "'+sha256+'"\n    Pop $R8\n    SetErrorLevel 21\n    Quit\n  ${EndIf}\n'
        '  Pop $R8\n!macroend\n').encode('utf8')


def emit_current_package(tree,request,owned,output,uninstaller,version):
    """Second NSIS phase owns self-hash provenance without a self-hash cycle.

    Normal app64.7z remains unchanged. Only MAIN installer compiles this fresh
    file into its private helper payload; uninstaller consumes the external
    closed installation-produced binary ownership receipt instead.
    """
    icon=Path(request['icon'])
    if icon!=owned/'icons/icon.ico' or not re.fullmatch('[a-f0-9]{40}',request.get('source_head','')):
        raise RuntimeError('Current-package producer identity is not an exact build input')
    files=tree.tree_manifest(output/'win-unpacked')
    if any(name.casefold() in {'uninstall books arranger.exe','uninstallericon.ico'} for name in files):
        raise RuntimeError('Unexpected generated NSIS file already in normal app payload')
    files['Uninstall Books Arranger.exe']=tree.protect(uninstaller)
    files['uninstallerIcon.ico']=tree.protect(icon)
    record={'schema':'books-trusted-current-package-v1','version':version,'build_id':output.name,
        'source_head':request['source_head'],'generated_uninstaller_sha256':files['Uninstall Books Arranger.exe']['sha256'],
        'files':dict(sorted(files.items()))}
    folder=tree.directory(owned/'lifecycle-main-provenance',create=True)
    filename=folder/'current-package.json'
    facts=tree.write(filename,[(json.dumps(record,sort_keys=True,indent=2)+'\n').encode('utf8')])
    tree.write(folder/'current-package.nsh',[current_package_include(filename,facts['sha256'])])
    return {'path':str(filename),'sha256':facts['sha256'],'files':len(files)}

def main():
    if len(sys.argv)!=3 or not re.fullmatch('[a-f0-9]{64}',sys.argv[2]):
        raise RuntimeError('Exact generator request and SHA required')
    request_path=Path(sys.argv[1]).absolute()
    with contextlib.ExitStack() as stack:
        bootstrap(stack)
        from build_fs_guard import BuildTree
        from native_io import FileInfo,kernel
        from desktop_host import owner_proof
        import ctypes
        with BuildTree(ROOT) as tree:
            actual=tree.protect(request_path)
            if actual['sha256']!=sys.argv[2]:raise RuntimeError('Generator request changed')
            request=strict_json(request_path.read_bytes())
            proof=request['lease'];lease_check(proof)
            owned=Path(proof['ownedRoot'])
            if request_path!=owned/'nsis-generator-request.json' or proof['mode']!='build':
                raise RuntimeError('Generator request outside exact owned operation')
            tree.created[str(owned).casefold()]=owned
            output=Path(request['output'])
            if output.parent!=ROOT/'dist/builds' or not re.fullmatch('[a-f0-9-]{36}',output.name):
                raise RuntimeError('Generator output is not a fresh build leaf')
            tree.directory(output)
            held_directory=tree.directories[str(output).casefold()]
            info=FileInfo()
            if not kernel.GetFileInformationByHandle(held_directory.handles[-1],ctypes.byref(info)):
                raise RuntimeError('Generator output identity unavailable')
            identity=[int(info.volume),int(info.index_high),int(info.index_low)]
            if identity!=request['output_identity']:
                raise RuntimeError('Generator output directory was replaced')
            version=json.loads((ROOT/'package.json').read_text('utf8'))['version']
            image=output/('Books-Arranger-Setup-'+version+'.exe')
            cwd=tree.directory(owned/'nsis-generator')
            if request['image']!=str(image) or request['cwd']!=str(cwd):
                raise RuntimeError('Unlisted generator image/cwd')
            # Native hold denies replacement/write through launch and completion.
            facts=tree.protect(image)
            held=tree.files[str(image).casefold()]
            if next(held.chunks(),b'')[:2]!=b'MZ':
                raise RuntimeError('Generated image has no PE header')
            image_native=held.facts()
            private=os.environ.copy()
            for name in ('TEMP','TMP'):
                if Path(private.get(name,'')).absolute()!=owned:
                    raise RuntimeError('Generator temporary path is not private')
            if Path(private.get('USERPROFILE','')).absolute()!=owned/'profile':
                raise RuntimeError('Generator profile is not private')
            private['__COMPAT_LAYER']='RunAsInvoker'
            remaining=(proof['deadline']-time.time()*1000)/1000
            if remaining<=0:raise RuntimeError('Generator lease expired')
            tree.write(owned/'nsis-generator-start.json',[json.dumps({'image':str(image),'native':image_native,**facts,'cwd':str(cwd),'creationflags':0x08000000},sort_keys=True).encode()])
            child=None;completed=False;generation=None
            try:
                # The child inherits the already-owned non-breakaway build Job.
                # Only this newly returned Popen handle can be terminated here.
                child=subprocess.Popen([str(image)],cwd=cwd,env=private,stdin=subprocess.DEVNULL,creationflags=0x08000000)
                generation=owner_proof(child,image)
                code=child.wait(timeout=remaining)
                if code:raise RuntimeError('NSIS generator failed: '+str(code))
                if tree.protect(image)!=facts:raise RuntimeError('Generated image drift')
                uninstaller=output/('Books-Arranger-Setup-'+version+'.__uninstaller.exe')
                tree.protect(uninstaller)
                package_provenance=emit_current_package(tree,request,owned,output,uninstaller,version)
                completed=True
            finally:
                if child is not None and child.poll() is None:
                    child.terminate();child.wait(timeout=3)
                tree.write(owned/'nsis-generator-result.json',[json.dumps({'schema':'books-nsis-generator-v1','completed':completed,'returncode':None if child is None else child.returncode,'owner':generation,'image':str(image),'image_native':image_native,'current_package':package_provenance if completed else None,**facts},sort_keys=True).encode()])

if __name__=='__main__':
    try:main()
    except Exception as error:print('Guarded NSIS generator: '+str(error),file=sys.stderr);sys.exit(1)
