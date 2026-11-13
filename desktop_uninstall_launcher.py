"""Verify and launch only this installation's pinned new uninstaller.

The Electron caller runs this synchronously before profile/application startup,
with selected TEMP/TMP already set. A PID is only a bounded NSIS wait hint;
normal process/catalog admission is never bypassed.
"""
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
LEGACY_027_UNINSTALLER='4e52e6a409ecef777c9c4ece2d7d8d128e2d100bce5cf2c9f11183cfad6ccd39'


def launch_uninstaller(bootstrap_path,bootstrap_sha256,application_dir,*,parent_pid,silent=False,_spawn=None):
    from storage_relocation_operator import local_root,pinned_receipt,need
    from storage_relocation import _inside
    from native_io import DirectoryBoundary,VerifiedFile
    from source_cleanup import single_stream
    from storage_relocation_native import configure_work_temp
    configure_work_temp()
    app=local_root(application_dir);configuration=local_root(bootstrap_path)
    need(parent_pid==os.getppid() and type(parent_pid) is int and parent_pid>0,
         'Uninstall launcher parent is not the actual creating process')
    with contextlib.ExitStack() as held:
        held.enter_context(DirectoryBoundary(configuration.anchor,configuration.parent))
        value=held.enter_context(pinned_receipt(configuration,bootstrap_sha256))
        need(value.get('schema')=='books-arranger-installation-v1' and
             Path(value.get('application_dir','')).absolute()==app,'Uninstall selection belongs to another installation')
        need('maintenance_temp_dir' in value and 'maintenance_temp_identity' in value,
             'Required installation maintenance settings are missing; repair the installation before uninstalling')
        temp=local_root(value['maintenance_temp_dir'])
        need(not _inside(str(temp),str(app)) and not _inside(str(app),str(temp)),
             'Uninstall temporary work overlaps the application')
        for name in ('data_dir','profile_dir','temp_dir','downloads_dir','logs_dir'):
            selected=local_root(value[name])
            need(not _inside(str(temp),str(selected)) and not _inside(str(selected),str(temp)),
                 'Uninstall maintenance work overlaps retained application state')
        need(not any((parent/'.git').exists() for parent in (temp,*temp.parents)),
             'Uninstall maintenance work is inside development source')
        need(all(os.environ.get(name)==str(temp) for name in ('BOOKS_WORK_TEMP','TEMP','TMP')),
             'Uninstall requires its explicit selected temporary environment; no fallback is allowed')
        maintenance=held.enter_context(DirectoryBoundary(temp.anchor,temp))
        need(list(maintenance.identities[-1][1:])==value['maintenance_temp_identity'],
             'Uninstall maintenance native identity changed; no alternate storage was opened')
        boundary=held.enter_context(DirectoryBoundary(app.anchor,app))
        pin=value.get('package_ownership')
        need(isinstance(pin,dict) and set(pin)=={'manifest','sha256'},'Pinned new-package ownership is required for uninstall launch')
        owner=held.enter_context(pinned_receipt(pin['manifest'],pin['sha256']))
        need(owner.get('schema')=='books-installation-ownership-v1' and
             owner.get('installation_id')==value['installation_id'] and owner.get('application_dir')==str(app) and
             len(owner.get('roots',[]))==1,'Uninstaller package producer differs from this installation')
        package=owner['roots'][0]
        need(package.get('role')=='application' and package.get('path')==str(app) and
             package.get('identity')==list(boundary.identities[-1][1:]),'Uninstaller application native root changed')
        selected=[file for file in package.get('files',[]) if file.get('relative')=='Uninstall Books Arranger.exe']
        need(len(selected)==1,'This package has no unique owned uninstaller')
        expected=selected[0];executable=app/'Uninstall Books Arranger.exe'
        image=held.enter_context(VerifiedFile(executable));single_stream(executable)
        actual_sha=image.sha256()
        need(actual_sha!=LEGACY_027_UNINSTALLER,'The unsafe legacy uninstaller cannot be executed; use verified package retirement')
        need(image.facts()==expected['facts'] and actual_sha==expected['sha256'],
             'Uninstaller native identity/content changed; nothing was launched')
        environment=dict(os.environ,TEMP=str(temp),TMP=str(temp),BOOKS_WORK_TEMP=str(temp))
        # The actual native file and ancestry remain held through CreateProcess.
        arguments=[str(executable),'/BOOKSLAUNCHERPID='+str(parent_pid)]
        if silent:arguments.append('/S')
        child=(_spawn or subprocess.Popen)(arguments,env=environment,stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True,
            creationflags=0x00000008|0x00000200)
        need(type(child.pid) is int and child.pid>0,'Uninstaller process creation was not confirmed')
        return dict(started=True,pid=child.pid,configured_temp=str(temp))


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installation-config',required=True);parser.add_argument('--sha256',required=True)
    parser.add_argument('--application-dir',required=True);parser.add_argument('--parent-pid',required=True,type=int)
    parser.add_argument('--silent',action='store_true');args=parser.parse_args(argv)
    try:
        result=launch_uninstaller(args.installation_config,args.sha256,args.application_dir,parent_pid=args.parent_pid,silent=args.silent)
        print(json.dumps(result));return 0
    except Exception as error:print(json.dumps(dict(started=False,error=str(error))));return 1


if __name__=='__main__':raise SystemExit(main())
