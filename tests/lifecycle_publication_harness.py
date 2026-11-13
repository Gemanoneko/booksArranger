"""Compile the shipped late extraction override in a private registry namespace."""
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import os
from unittest.mock import patch
import uuid
import winreg


def assert_retained_runtime_copy(maintenance,terminal,expected_sha256):
    """Only the disclosed, native-pinned known copy may remain; unknowns fail."""
    from native_io import DirectoryBoundary,VerifiedFile
    from source_cleanup import single_stream
    runtime=terminal['selection']['retained_runtime_copy'];assert runtime['verified'] is True,runtime
    actual=Path(runtime['path']);maintenance=Path(maintenance)
    assert actual!=maintenance and actual.is_relative_to(maintenance)
    with DirectoryBoundary(maintenance.anchor,maintenance) as held,VerifiedFile(actual) as image:
        single_stream(actual)
        assert list(held.identities[-1][1:])==runtime['maintenance_identity']
        assert image.facts()==runtime['facts'] and image.facts()['links']==1
        assert image.sha256()==runtime['sha256']==expected_sha256
        assert runtime['bytes']==image.facts()['size']
    assert [p for p in maintenance.rglob('*') if p.is_file()]==[actual]
    allowed=set(actual.parents)-set(maintenance.parents)
    assert all(p in allowed for p in maintenance.rglob('*') if p.is_dir())
    return runtime


def run_publication_harness(root,out,payload,verify,environment):
    import storage_lifecycle as lifecycle
    work=out/'publication-matrix';work.mkdir();normal=work/'normal';normal.mkdir()
    (normal/'Books Arranger.exe').write_bytes(b'Private fixture payload; never executed')
    (normal/'resource.dat').write_bytes(b'Private staged extraction marker')
    icon=work/'fixture.ico';icon.write_bytes(b'private opaque icon file fixture')
    uninstaller=out/'private-uninstaller.exe'
    files={p.name:dict(size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in normal.iterdir()}
    files['Uninstall Books Arranger.exe']=dict(size=uninstaller.stat().st_size,sha256=hashlib.sha256(uninstaller.read_bytes()).hexdigest())
    files['uninstallerIcon.ico']=dict(size=icon.stat().st_size,sha256=hashlib.sha256(icon.read_bytes()).hexdigest())
    package=work/'current-package.json';package.write_text(json.dumps(dict(schema='books-trusted-current-package-v1',version='0.28.0',
        build_id=str(uuid.uuid4()),source_head='0'*40,generated_uninstaller_sha256=files['Uninstall Books Arranger.exe']['sha256'],files=files)),encoding='utf8')
    package_sha=hashlib.sha256(package.read_bytes()).hexdigest()
    generated=work/'current-package.nsh'
    generated.write_text('!macro BooksCurrentPackagePayload ROOT\nFile "/oname=${ROOT}\\current-package.json" "'+str(package)+'"\n!macroend\n'
        '!macro BooksCurrentPackageVerify ROOT\n${StdUtils.HashFile} $R8 "SHA2-256" "${ROOT}\\current-package.json"\n'
        'StrCmp $R8 "'+package_sha+'" +3\nSetErrorLevel 21\nQuit\n!macroend\n',encoding='utf8')
    registry='Software\\BooksLifecyclePrivateHarness\\'+str(uuid.uuid4())
    def compile_case(label,target,data,*,mode='new',updated=False,config_paths=(),registrations=()):
        plan_path='';plan_sha=''
        if not updated:
            with patch.dict(os.environ,environment),patch.object(lifecycle,'registered_bootstraps',return_value=list(registrations)):
                plan=lifecycle.selection_plan(mode,str(data),application_dir=str(target),profile_dir=str(target.parent/'Profile'),config_paths=config_paths)
            plan_path=work/(label+'-selection.json');raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode();plan_path.write_bytes(raw)
            plan_sha=hashlib.sha256(raw).hexdigest()
        marker=work/(label+'-downstream.txt')
        source=r'''Unicode true
RequestExecutionLevel user
Name "Books Private Publication Fixture"
OutFile "@EXE@"
InstallDir "@TARGET@"
!addincludedir "@TEMPLATES@"
!addplugindir /x86-unicode "@RESOURCES@\plugins\x86-unicode"
!include MUI2.nsh
!include LogicLib.nsh
!include StdUtils.nsh
!define APP_EXECUTABLE_FILENAME "Books Arranger.exe"
!define APP_FILENAME "Application"
!define APP_BUILD_DIR "@NORMAL@"
!define UNINSTALLER_OUT_FILE "@UNINSTALLER@"
!define UNINSTALL_FILENAME "Uninstall Books Arranger.exe"
!define UNINSTALL_REGISTRY_KEY "@REGISTRY@"
!define UNINSTALLER_ICON "@ICON@"
!define BOOKS_LIFECYCLE_PROCESS_NAME "Books Lifecycle Busy Fixture.exe"
!define BOOKS_LIFECYCLE_PAYLOAD "@PAYLOAD@"
!define BOOKS_CURRENT_PACKAGE_INCLUDE "@PACKAGE_INCLUDE@"
!define isUpdated '@UPDATED@'
!macro BooksLifecycleVerifyPayload ROOT
@VERIFY@
!macroend
!include "@INCLUDE@"
Page instfiles
!insertmacro MUI_LANGUAGE "English"
Function .onInit
StrCpy $BooksPlan "@PLAN@"
StrCpy $BooksPlanSha "@PLAN_SHA@"
!insertmacro customCheckAppRunning
FunctionEnd
; Model the pinned template's definition order. Both poison bodies MUST be
; replaced by the SAME shipped late include before their first section call.
!macro uninstallOldVersion ROOT_KEY
FileOpen $0 "@POISON@" w
FileWrite $0 "Unsafe old uninstaller was invoked"
FileClose $0
!macroend
!macro installApplicationFiles
FileOpen $0 "@POISON@" w
FileWrite $0 "Unsafe direct extraction was invoked"
FileClose $0
!macroend
Section
!insertmacro customCheckAppRunning
!insertmacro uninstallOldVersion HKEY_CURRENT_USER
SetOutPath $INSTDIR
!insertmacro installApplicationFiles
; Exact downstream stock responsibilities occur only after publication.
WriteRegStr HKCU "@REGISTRY@" "InstallLocation" "$INSTDIR"
WriteRegStr HKCU "@REGISTRY@" "DisplayVersion" "0.28.0"
!insertmacro customInstall
FileOpen $0 "@MARKER@" w
FileWrite $0 "$INSTDIR"
FileClose $0
SectionEnd
'''
        values=dict(EXE=work/(label+'.exe'),TARGET=target,TEMPLATES=root/'node_modules/app-builder-lib/templates/nsis/include',
            RESOURCES=root/'build-cache/pack-inputs/nsis-resources',NORMAL=normal,UNINSTALLER=uninstaller,REGISTRY=registry,
            ICON=icon,PAYLOAD=payload,PACKAGE_INCLUDE=generated,VERIFY=verify,INCLUDE=root/'desktop/installer.nsh',
            PLAN=plan_path,PLAN_SHA=plan_sha,POISON=work/'unsafe-execution.txt',MARKER=marker,UPDATED='1 == 1' if updated else '0 == 1')
        for name,value in values.items():source=source.replace('@'+name+'@',str(value))
        script=work/(label+'.nsi');script.write_text(source,encoding='utf8')
        compiled=subprocess.run([str(root/'build-cache/pack-inputs/nsis/Bin/makensis.exe'),'/V2',str(script)],capture_output=True,text=True,timeout=120,creationflags=0x08000000)
        (work/(label+'-compile.log')).write_text(compiled.stdout+compiled.stderr,encoding='utf8')
        if compiled.returncode:raise AssertionError(compiled.stdout+compiled.stderr)
        run=subprocess.run([str(values['EXE']),'/S'],env=environment,capture_output=True,timeout=120,creationflags=0x08000000)
        return run.returncode,marker
    target=work/'Installation'/'Application';target.parent.mkdir()
    try:
        fresh,marker=compile_case('fresh',target,target.parent/'Data')
        assert fresh==0 and marker.read_text()==str(target),('Fresh publication did not reach final downstream commit',fresh)
        bootstrap=target.parent/lifecycle.BOOTSTRAP
        first=json.loads(bootstrap.read_text());assert first['application_dir']==str(target) and first.get('package_ownership')
        from native_io import VerifiedFile
        with VerifiedFile(target/'Books Arranger.exe') as held:original=held.facts()
        repaired,marker=compile_case('inplace',target,target.parent/'SeparateData')
        assert repaired==0 and marker.read_text()==str(target),('In-place publication did not continue',repaired)
        after=json.loads(bootstrap.read_text());retained=json.loads(Path(after['retained_package']['manifest']).read_text())
        with VerifiedFile(Path(retained['retained_application'])/'Books Arranger.exe') as held:assert held.facts()==original
        assert not (work/'unsafe-execution.txt').exists()
        repo=work/'PersonalRepository';(repo/'.git').mkdir(parents=True);source=repo/'program.py';source.write_bytes(b'personal source remains')
        before=source.read_bytes();refused,marker=compile_case('unknown',repo,work/'NeverCreatedData')
        assert refused==20 and not marker.exists() and source.read_bytes()==before and not (work/'NeverCreatedData').exists()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry) as key:assert winreg.QueryValueEx(key,'InstallLocation')[0]==str(target)
        # Exercise the REAL accepted 0.27 payload with a never-executed old
        # uninstaller. Its native original identities survive directory retention.
        legacy=work/'LegacyMachine'/'Application';legacy.mkdir(parents=True)
        trusted=json.loads((root/'desktop/legacy-package-0.27.0.json').read_text())
        accepted=root/'dist/builds/0245e25b-e185-4357-b48c-8f1cb4b242c0'
        installer=accepted/'Books-Arranger-Setup-0.27.0.exe'
        assert installer.stat().st_size==trusted['installer_size'] and hashlib.sha256(installer.read_bytes()).hexdigest()==trusted['installer_sha256']
        static=work/'legacy-static';static.mkdir()
        extracted=subprocess.run(['C:/Program Files/7-Zip/7z.exe','x','-y','-o'+str(static),str(installer)],capture_output=True,timeout=120,creationflags=0x08000000)
        assert extracted.returncode==0
        for relative,expected in trusted['files'].items():
            source=accepted/'win-unpacked'/relative
            if not source.exists():
                matches=[p for p in static.rglob(Path(relative).name) if p.is_file() and p.stat().st_size==expected['size'] and hashlib.sha256(p.read_bytes()).hexdigest()==expected['sha256']]
                assert len(matches)==1,(relative,matches);source=matches[0]
            assert source.stat().st_size==expected['size'] and hashlib.sha256(source.read_bytes()).hexdigest()==expected['sha256'],relative
            destination=legacy/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        with VerifiedFile(legacy/'Books Arranger.exe') as held:legacy_original=held.facts()
        old_backend=legacy/'resources/backend';catalog=work/'LegacyCatalog'/'inventory.sqlite3';catalog.parent.mkdir()
        seed=subprocess.run([str(payload/'python/python.exe'),'-I','-B','-c',
            'import sys;sys.path.insert(0,sys.argv[1]);import scanner;c=scanner.connect(sys.argv[2]);c.commit();c.close()',str(old_backend),str(catalog)],env=environment,capture_output=True,timeout=30,creationflags=0x08000000)
        assert seed.returncode==0,seed.stderr
        old_profile=Path(environment['APPDATA'])/'Books Arranger';(old_profile/'Local Storage/leveldb').mkdir(parents=True)
        settings=old_profile/'desktop-settings.json';settings.write_text(json.dumps(dict(dataDir=str(catalog.parent),catalogMode='existing')))
        decisions=old_profile/'Local Storage/leveldb/000001.log';decisions.write_bytes(b'legacy pending decisions and credential fixture bytes')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,registry) as key:
            winreg.SetValueEx(key,'InstallLocation',0,winreg.REG_SZ,str(legacy));winreg.SetValueEx(key,'DisplayVersion',0,winreg.REG_SZ,'0.27.0')
        legacy_exit,legacy_marker=compile_case('legacy-silent',legacy,catalog,updated=True)
        assert legacy_exit==0 and legacy_marker.read_text()==str(legacy),('Actual legacy silent update failed',legacy_exit)
        legacy_bootstrap=legacy.parent/lifecycle.BOOTSTRAP;upgraded=json.loads(legacy_bootstrap.read_text())
        assert upgraded['data_dir']==str(catalog.parent)
        current_profile=Path(upgraded['profile_dir'])
        assert (current_profile/decisions.relative_to(old_profile)).read_bytes()==decisions.read_bytes()
        retained_legacy=json.loads(Path(upgraded['retained_package']['manifest']).read_text())
        with VerifiedFile(Path(retained_legacy['retained_application'])/'Books Arranger.exe') as held:assert held.facts()==legacy_original
        # The second install uses the latest per-install profile, with changed
        # decisions, despite stock registry replacement BEFORE customInstall.
        (current_profile/'Local Storage/leveldb/000001.log').write_bytes(b'latest post-upgrade pending decisions')
        new_target=work/'NewDirectory'/'Application';new_target.parent.mkdir()
        with patch.object(lifecycle,'registered_bootstraps',return_value=[str(legacy_bootstrap)]):
            # compile_case snapshots the registered source bootstrap before the
            # child writes its private registry InstallLocation.
            newdir_exit,newdir_marker=compile_case('newdir-existing-profile',new_target,catalog,mode='existing',
                config_paths=[str(current_profile/'desktop-settings.json')],registrations=[str(legacy_bootstrap)])
        assert newdir_exit==0 and newdir_marker.read_text()==str(new_target),('Existing profile new-directory install failed',newdir_exit)
        latest=json.loads((new_target.parent/lifecycle.BOOTSTRAP).read_text())
        assert (Path(latest['profile_dir'])/'Local Storage/leveldb/000001.log').read_bytes()==b'latest post-upgrade pending decisions'
        assert decisions.read_bytes()==b'legacy pending decisions and credential fixture bytes'
        # The registered route's exact configured maintenance root is supplied
        # BEFORE NSIS, including its own initial self-copy. Review and planning
        # run inside the actual private NSIS child, never a hidden harness TEMP.
        maintenance=Path(latest['maintenance_temp_dir'])
        assert maintenance.exists() and not any(maintenance.iterdir())
        terminal_environment=dict(environment,TEMP=str(maintenance),TMP=str(maintenance),BOOKS_WORK_TEMP=str(maintenance))
        observed_plan=work/'terminal-selection-observed.json';observed_review=work/'terminal-review-observed.ini'
        terminal_marker=work/'terminal-downstream.txt'
        terminal_source=r'''Unicode true
RequestExecutionLevel user
Name "Books Private Terminal Cleanup"
OutFile "@GENERATOR@"
InstallDir "@TARGET@"
!addincludedir "@TEMPLATES@"
!addplugindir /x86-unicode "@RESOURCES@\plugins\x86-unicode"
!include MUI2.nsh
!include LogicLib.nsh
!include StdUtils.nsh
!define APP_EXECUTABLE_FILENAME "Books Arranger.exe"
!define APP_FILENAME "Application"
!define BUILD_UNINSTALLER
!define UNINSTALL_REGISTRY_KEY "@REGISTRY@"
!define BOOKS_LIFECYCLE_PROCESS_NAME "Books Lifecycle Busy Fixture.exe"
!define BOOKS_LIFECYCLE_PAYLOAD "@PAYLOAD@"
!define isUpdated '0 == 1'
!macro BooksLifecycleVerifyPayload ROOT
@VERIFY@
!macroend
!include "@INCLUDE@"
UninstPage instfiles
!insertmacro MUI_LANGUAGE "English"
Function .onInit
WriteUninstaller "@UNINSTALLER@"
SetErrorLevel 0
Quit
FunctionEnd
Function un.onInit
StrCpy $INSTDIR "@TARGET@"
!insertmacro customCheckAppRunning
Call un.BooksNewRequest
WriteINIStr "$BooksRequest" "request" "action" "review-uninstall"
WriteINIStr "$BooksRequest" "request" "application_dir" "$INSTDIR"
WriteINIStr "$BooksRequest" "request" "bootstrap" "@BOOTSTRAP@"
Call un.BooksRunHelper
${If} $2 != "1"
  Call un.BooksRefuse
${EndIf}
StrCpy $BooksCleanupReview $BooksResponse
CopyFiles /SILENT "$BooksCleanupReview" "@OBSERVED_REVIEW@"
Call un.BooksNewRequest
WriteINIStr "$BooksRequest" "request" "action" "plan-cleanup"
ReadINIStr $0 "$BooksCleanupReview" "result" "ownership_path"
WriteINIStr "$BooksRequest" "request" "ownership_path" "$0"
ReadINIStr $0 "$BooksCleanupReview" "result" "ownership_sha256"
WriteINIStr "$BooksRequest" "request" "ownership_sha256" "$0"
ReadINIStr $0 "$BooksCleanupReview" "result" "authority_bootstrap"
WriteINIStr "$BooksRequest" "request" "authority_bootstrap" "$0"
ReadINIStr $4 "$BooksCleanupReview" "result" "count"
StrCpy $5 0
StrCpy $7 0
${DoWhile} $5 < $4
  ReadINIStr $0 "$BooksCleanupReview" "target$5" "can_remove"
  ${If} $0 == "True"
    ReadINIStr $0 "$BooksCleanupReview" "target$5" "path"
    WriteINIStr "$BooksRequest" "selected$7" "path" "$0"
    IntOp $7 $7 + 1
  ${EndIf}
  IntOp $5 $5 + 1
${Loop}
WriteINIStr "$BooksRequest" "request" "selected_count" "$7"
Call un.BooksRunHelper
${If} $2 != "1"
  Call un.BooksRefuse
${EndIf}
ReadINIStr $BooksCleanupPlan "$BooksResponse" "result" "plan_path"
ReadINIStr $BooksCleanupSha "$BooksResponse" "result" "plan_sha256"
CopyFiles /SILENT "$BooksCleanupPlan" "@OBSERVED_PLAN@"
StrCpy $BooksCleanupMode "remove"
FunctionEnd
Section
SectionEnd
Section "Uninstall"
!insertmacro customUnInstall
!insertmacro customRemoveFiles
DeleteRegKey HKCU "@REGISTRY@"
FileOpen $0 "@MARKER@" w
FileWrite $0 "all finite cleanup and downstream metadata completed"
FileClose $0
SectionEnd
'''
        terminal_exe=work/'terminal-uninstaller.exe'
        substitutions=dict(GENERATOR=work/'terminal-generator.exe',TARGET=new_target,TEMPLATES=root/'node_modules/app-builder-lib/templates/nsis/include',
            RESOURCES=root/'build-cache/pack-inputs/nsis-resources',REGISTRY=registry,PAYLOAD=payload,VERIFY=verify,
            INCLUDE=root/'desktop/installer.nsh',UNINSTALLER=terminal_exe,BOOTSTRAP=new_target.parent/lifecycle.BOOTSTRAP,
            OBSERVED_PLAN=observed_plan,OBSERVED_REVIEW=observed_review,MARKER=terminal_marker)
        for name,value in substitutions.items():terminal_source=terminal_source.replace('@'+name+'@',str(value))
        terminal_nsi=work/'terminal.nsi';terminal_nsi.write_text(terminal_source,encoding='utf8')
        built=subprocess.run([str(root/'build-cache/pack-inputs/nsis/Bin/makensis.exe'),'/V2',str(terminal_nsi)],capture_output=True,text=True,timeout=120,creationflags=0x08000000)
        (work/'terminal-compile.log').write_text(built.stdout+built.stderr);assert built.returncode==0,built.stdout+built.stderr
        generated_run=subprocess.run([str(substitutions['GENERATOR']),'/S'],env=terminal_environment,capture_output=True,timeout=30,creationflags=0x08000000)
        assert generated_run.returncode==0,('Private uninstaller generator failed',generated_run.returncode,generated_run.stderr)
        # Model this freshly built uninstaller as the ACTUAL current package
        # member, then run the genuine producer against its builder input. Only
        # builder metadata injection is scoped here; runtime proof is never mocked.
        shutil.copyfile(terminal_exe,new_target/'Uninstall Books Arranger.exe')
        actual_producer=json.loads(package.read_text())
        actual_producer['files']['Uninstall Books Arranger.exe']=dict(size=terminal_exe.stat().st_size,
            sha256=hashlib.sha256(terminal_exe.read_bytes()).hexdigest())
        actual_producer['generated_uninstaller_sha256']=actual_producer['files']['Uninstall Books Arranger.exe']['sha256']
        real_json=lifecycle._json
        def builder_input(path,*args):
            if Path(path)==Path(lifecycle.__file__).parent/'current-package.json':
                return actual_producer,{},hashlib.sha256(json.dumps(actual_producer,sort_keys=True).encode()).hexdigest()
            return real_json(path,*args)
        with patch.dict(os.environ,environment),patch.object(lifecycle,'_json',side_effect=builder_input):
            lifecycle.publish_current_package(new_target.parent/lifecycle.BOOTSTRAP)
        # No _?= suppression: exercise the initial NSIS self-copy and its child.
        cleaned=subprocess.run([str(terminal_exe),'/S'],env=terminal_environment,capture_output=True,timeout=120,creationflags=0x08000000)
        import time
        deadline=time.monotonic()+120;empty_without_result=0
        while time.monotonic()<deadline:
            children=any(maintenance.iterdir())
            if terminal_marker.exists():break
            empty_without_result=empty_without_result+1 if not children else 0
            if empty_without_result>=10:break
            time.sleep(.1)
        assert cleaned.returncode==0 and terminal_marker.exists(),('Terminal native macro flow refused',cleaned.returncode)
        terminal=json.loads(observed_plan.read_text());assert terminal['schema']=='books-lifecycle-terminal-cleanup-v1'
        assert not new_target.exists() and not (new_target.parent/lifecycle.BOOTSTRAP).exists()
        for row in terminal['selection']['controls']['files']:assert not Path(row['path']).exists(),row['path']
        runtime=assert_retained_runtime_copy(maintenance,terminal,actual_producer['generated_uninstaller_sha256'])
        evidence=dict(fresh_exit=fresh,inplace_exit=repaired,unknown_exit=refused,legacy_silent_027_exit=legacy_exit,newdir_existing_profile_exit=newdir_exit,terminal_cleanup_exit=cleaned.returncode,
            terminal_controls_and_bootstrap_gone=True,downstream_bootstrap_and_registry=True,
            configured_maintenance_temp=str(maintenance),private_helper_workspace_removed=True,retained_runtime_copy=runtime,
            reserved_maintenance_parent_empty=False,unknown_maintenance_residue=False,
            original_native_file_identity_preserved=True,unknown_source_unchanged=True,unsafe_old_binary_or_extractor_executed=False,
            current_product_registration_touched=False,private_registry_key=registry,
            include_sha256=hashlib.sha256((root/'desktop/installer.nsh').read_bytes()).hexdigest(),
            late_include_sha256=hashlib.sha256((root/'desktop/installer-safe-upgrade.nsh').read_bytes()).hexdigest())
        (work/'evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf8');return evidence
    finally:
        try:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,registry)
        except FileNotFoundError:pass
        parent=registry.rsplit('\\',1)[0]
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,parent) as key:empty=winreg.QueryInfoKey(key)[:2]==(0,0)
            if empty:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,parent)
        except FileNotFoundError:pass
