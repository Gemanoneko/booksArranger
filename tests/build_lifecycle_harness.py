"""Compile identical shipped NSIS include in an isolated, non-product namespace.

Never invokes the installed application or writes a product registration. The
silent native smoke proves busy refusal precedes an isolated section sentinel.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import base64
import io
import tarfile
import urllib.request


def prepare_supervisor(source,out):
    """Verify an installed locked provider, then copy its exact bytes privately.

    This never installs a package or executes a dependency lifecycle script.
    Registry tarballs are SHA512-checked against the existing source lockfile;
    every copied member must already be byte-identical in that installation.
    """
    source=Path(source).absolute();out=Path(out).absolute()
    if out.exists():raise ValueError('Ownership verification output must be new')
    lock=json.loads((source/'package-lock.json').read_text('utf8'));verified=[]
    for relative in ('node_modules/koffi','node_modules/@koromix/koffi-win32-x64'):
        pin=lock['packages'][relative];installed=source/relative
        package=json.loads((installed/'package.json').read_text('utf8'))
        if package['version']!=pin['version'] or pin['version']!='3.3.2':raise ValueError('Installed ownership provider version differs')
        with urllib.request.urlopen(pin['resolved'],timeout=30) as response:archive=response.read(50*1024*1024+1)
        if len(archive)>50*1024*1024:raise ValueError('Ownership tarball bound exceeded')
        actual='sha512-'+base64.b64encode(hashlib.sha512(archive).digest()).decode()
        if actual!=pin['integrity']:raise ValueError('Ownership provider integrity differs from trusted lockfile')
        with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
            for member in tar:
                if member.isdir():continue
                if not member.isfile() or not member.name.startswith('package/'):raise ValueError('Nonordinary ownership archive member')
                name=member.name[len('package/'):];path=Path(name)
                if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe ownership archive path')
                body=tar.extractfile(member).read();original=installed/path
                if original.is_symlink() or not original.is_file() or original.read_bytes()!=body:raise ValueError('Installed ownership bytes differ: '+str(original))
                verified.append((Path(relative)/path,body))
    out.mkdir(parents=True)
    for relative,body in verified:
        target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
    files=[dict(path=p.as_posix(),sha256=hashlib.sha256(body).hexdigest(),size=len(body)) for p,body in verified]
    receipt=dict(schema='books-verified-ownership-runtime-v1',source=str(source),lock_sha256=hashlib.sha256((source/'package-lock.json').read_bytes()).hexdigest(),
        files=files,koffi_root=str(out/'node_modules/koffi'),dependency_scripts_executed=False,implicit_install=False)
    (out/'verification.json').write_text(json.dumps(receipt,indent=2),encoding='utf8');print(json.dumps(dict(koffi_root=receipt['koffi_root'],files=len(files),verification=str(out/'verification.json'))))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--native-pages',action='store_true');parser.add_argument('--publication',action='store_true');parser.add_argument('--prepare-supervisor-from');args=parser.parse_args()
    if args.prepare_supervisor_from:return prepare_supervisor(args.prepare_supervisor_from,args.out)
    root=Path(__file__).resolve().parents[1];out=Path(args.out).absolute()
    # Isolated Python deliberately omits the script directory from sys.path.
    # These maintained harness consumers come only from this exact test tree.
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    if out.exists():raise ValueError('Harness output must be a new owned directory')
    out.mkdir(parents=True)
    pointer=json.loads((root/'build-cache/runtime-pointer.json').read_text('utf8'))
    runtime=Path(pointer['root'])/'python'
    payload=out/'payload';(payload/'python').mkdir(parents=True);(payload/'backend').mkdir()
    for file in runtime.iterdir():
        if file.is_file():shutil.copy2(file,payload/'python'/file.name)
    for file in root.glob('*.py'):shutil.copy2(file,payload/'backend'/file.name)
    shutil.copy2(root/'desktop/legacy-package-0.27.0.json',payload/'backend/legacy-package-0.27.0.json')
    # Copy exact executable bytes under a TEST-ONLY name, no product process use.
    busy_name='Books Lifecycle Busy Fixture.exe'
    shutil.copy2(payload/'python/python.exe',payload/'python'/busy_name)
    payload_hashes={str(p.relative_to(payload)).replace('/','\\'):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in payload.rglob('*') if p.is_file()}
    nsis=root/'build-cache/pack-inputs/nsis';resources=root/'build-cache/pack-inputs/nsis-resources'
    templates=root/'node_modules/app-builder-lib/templates/nsis/include'
    verify='\n'.join('${StdUtils.HashFile} $R8 "SHA2-256" "${ROOT}\\'+name+'"\nStrCmp $R8 "'+digest+'" +3\nSetErrorLevel 21\nQuit'
                     for name,digest in payload_hashes.items())
    source='''Unicode true
RequestExecutionLevel user
Name "Books Lifecycle Private Harness"
OutFile "@OUT@\\harness.exe"
InstallDir "@OUT@\\Application"
!addincludedir "@TEMPLATES@"
!addplugindir /x86-unicode "@RESOURCES@\\plugins\\x86-unicode"
!include MUI2.nsh
!include LogicLib.nsh
!include StdUtils.nsh
!define APP_EXECUTABLE_FILENAME "Books Lifecycle Private Harness.exe"
!define APP_FILENAME "Application"
!define UNINSTALL_REGISTRY_KEY "Software\\BooksLifecyclePrivateHarnessNeverProduct"
!define INSTALL_REGISTRY_KEY "Software\\BooksLifecyclePrivateHarnessNeverProductInstall"
!define BOOKS_LIFECYCLE_PROCESS_NAME "@BUSY@"
!define BOOKS_LIFECYCLE_PAYLOAD "@PAYLOAD@"
!define isUpdated '0 == 1'
!macro BooksLifecycleVerifyPayload ROOT
@VERIFY@
!macroend
!include "@INCLUDE@"
!insertmacro customPageAfterChangeDir
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Function .onInit
!insertmacro customCheckAppRunning
FunctionEnd
!macro uninstallOldVersion ROOT_KEY
FileOpen $0 "@OUT@\\unsafe-old-uninstaller-reached.txt" w
FileWrite $0 "UNSAFE old macro was invoked"
FileClose $0
!macroend
Section "private"
!insertmacro customCheckAppRunning
!insertmacro uninstallOldVersion HKEY_CURRENT_USER
FileOpen $0 "@OUT@\\section-reached.txt" w
FileWrite $0 "native section reached"
FileClose $0
SectionEnd
'''
    values={'OUT':out,'TEMPLATES':templates,'RESOURCES':resources,'BUSY':busy_name,'PAYLOAD':payload,
            'VERIFY':verify,'INCLUDE':root/'desktop/installer.nsh'}
    for key,value in values.items():source=source.replace('@'+key+'@',str(value))
    nsi=out/'harness.nsi';nsi.write_text(source,encoding='utf8')
    compiled=subprocess.run([str(nsis/'Bin/makensis.exe'),'/V2',str(nsi)],capture_output=True,text=True,timeout=120,creationflags=0x08000000)
    (out/'compile.log').write_text(compiled.stdout+'\n'+compiled.stderr,encoding='utf8')
    if compiled.returncode:raise RuntimeError(compiled.stdout+compiled.stderr)
    un_source='''Unicode true
RequestExecutionLevel user
Name "Books Lifecycle Private Uninstall Harness"
OutFile "@OUT@\\uninstall-generator.exe"
InstallDir "@OUT@\\Application"
!addincludedir "@TEMPLATES@"
!addplugindir /x86-unicode "@RESOURCES@\\plugins\\x86-unicode"
!include MUI2.nsh
!include LogicLib.nsh
!include StdUtils.nsh
!define APP_EXECUTABLE_FILENAME "Books Lifecycle Private Harness.exe"
!define APP_FILENAME "Application"
!define BOOKS_LIFECYCLE_PROCESS_NAME "@BUSY@"
!define BOOKS_LIFECYCLE_PAYLOAD "@PAYLOAD@"
!define BUILD_UNINSTALLER
!define isUpdated '0 == 1'
!macro BooksLifecycleVerifyPayload ROOT
@VERIFY@
!macroend
!include "@INCLUDE@"
!insertmacro customUnWelcomePage
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro customUninstallPage
!insertmacro MUI_LANGUAGE "English"
Function .onInit
WriteUninstaller "@OUT@\\private-uninstaller.exe"
SetErrorLevel 0
Quit
FunctionEnd
Function un.onInit
!insertmacro customCheckAppRunning
FunctionEnd
Section
SectionEnd
Section "Uninstall"
!insertmacro customUnInstall
FileOpen $0 "@OUT@\\uninstall-section-reached.txt" w
FileWrite $0 "native uninstall section reached"
FileClose $0
SectionEnd
'''
    for key,value in values.items():un_source=un_source.replace('@'+key+'@',str(value))
    un_nsi=out/'uninstall-harness.nsi';un_nsi.write_text(un_source,encoding='utf8')
    compiled_un=subprocess.run([str(nsis/'Bin/makensis.exe'),'/V2',str(un_nsi)],capture_output=True,text=True,timeout=120,creationflags=0x08000000)
    (out/'uninstall-compile.log').write_text(compiled_un.stdout+'\n'+compiled_un.stderr,encoding='utf8')
    if compiled_un.returncode:raise RuntimeError(compiled_un.stdout+compiled_un.stderr)
    private_env=dict(os.environ)
    for key,relative in [('TEMP','temp'),('TMP','temp'),('APPDATA','profile/Roaming'),('LOCALAPPDATA','profile/Local'),('USERPROFILE','profile')]:
        target=out/'environment'/relative;target.mkdir(parents=True,exist_ok=True);private_env[key]=str(target)
    (out/'Application').mkdir()
    subprocess.run([str(out/'uninstall-generator.exe'),'/S'],check=True,timeout=30,creationflags=0x08000000,env=private_env)
    busy=subprocess.Popen([str(payload/'python'/busy_name),'-I','-B','-c','import time;time.sleep(12)'],
                          stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=0x08000000,env=private_env)
    try:
        time.sleep(.4)
        refused=subprocess.run([str(out/'harness.exe'),'/S'],capture_output=True,timeout=45,creationflags=0x08000000,env=private_env)
        alive=busy.poll() is None
        if refused.returncode!=20 or not alive or (out/'section-reached.txt').exists():
            raise AssertionError(('busy guard did not refuse before section',refused.returncode,alive))
        # NSIS's special _?= suffix consumes the unquoted remainder verbatim;
        # list2cmdline would quote the whole spaced argument and bypass it.
        uninstall_command='"'+str(out/'private-uninstaller.exe')+'" /S _?='+str(out/'Application')
        un_refused=subprocess.run(uninstall_command,capture_output=True,timeout=45,creationflags=0x08000000,env=private_env)
        if un_refused.returncode!=20 or busy.poll() is not None or (out/'uninstall-section-reached.txt').exists():
            raise AssertionError(('busy uninstall guard did not refuse before section',un_refused.returncode,busy.poll()))
        busy.wait(timeout=15)
        accepted=subprocess.run([str(out/'harness.exe'),'/S'],capture_output=True,timeout=45,creationflags=0x08000000,env=private_env)
        if accepted.returncode or not (out/'section-reached.txt').exists():
            raise AssertionError(('available positive control failed',accepted.returncode))
        if (out/'unsafe-old-uninstaller-reached.txt').exists():raise AssertionError('Old uninstall macro was executed')
        un_accepted=subprocess.run(uninstall_command,capture_output=True,timeout=45,creationflags=0x08000000,env=private_env)
        if un_accepted.returncode or not (out/'uninstall-section-reached.txt').exists():
            raise AssertionError(('available uninstall positive control failed',un_accepted.returncode))
        publication=None
        if args.publication:
            sys.path.insert(0,str(root))
            from lifecycle_publication_harness import run_publication_harness
            publication=run_publication_harness(root,out,payload,verify,private_env)
        pages={'actual_native_pages':False}
        if args.native_pages:
            sys.path.insert(0,str(root))
            import storage_lifecycle as lifecycle
            plan=lifecycle.selection_plan('new',str(out/'Data'),application_dir=str(out/'Application'),profile_dir=str(out/'Profile'))
            digest=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            lifecycle.commit_selection(plan,digest,process_name=busy_name)
            (out/'Profile'/'Local State').write_text('{}',encoding='utf8')
            (out/'Temp'/'personal.pdf').write_bytes(b'Unknown personal content must remain protected')
            from lifecycle_native_pages import inspect_pages
            pages=inspect_pages(out/'private-uninstaller.exe',out/'Application',private_env,out/'native-pages.json')
        evidence={'include_sha256':hashlib.sha256((root/'desktop/installer.nsh').read_bytes()).hexdigest(),
                  'helper_sha256':hashlib.sha256((root/'storage_lifecycle.py').read_bytes()).hexdigest(),
                  'harness_sha256':hashlib.sha256((out/'harness.exe').read_bytes()).hexdigest(),
                  'payload_files':len(payload_hashes),'busy_refusal_exit':refused.returncode,
                  'busy_uninstall_refusal_exit':un_refused.returncode,'available_uninstall_exit':un_accepted.returncode,
                  'busy_fixture_survived':alive,'available_exit':accepted.returncode,
                  'section_sentinel':True,'product_registration_written':False,'native_pages_shown':pages['actual_native_pages'],
                  'private_desktop_only':True,'unsafe_old_macro_executed':False}
        evidence['publication']=publication
        (out/'evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf8')
        print(json.dumps(evidence))
    finally:
        if busy.poll() is None:busy.wait(timeout=15)


if __name__=='__main__':main()
