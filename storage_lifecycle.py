"""Bounded installer discovery and exact, opt-in retained-data cleanup.

Selection never moves a catalog. Discovery never initializes a schema. Cleanup
never expands a file ownership receipt into recursive deletion of its parent.
The native wizard is only a consumer of this independently checked contract.
"""
import argparse
import configparser
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import re
from pathlib import Path
import sqlite3
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_io import DirectoryBoundary, VerifiedFile, VerifiedDirectory, kernel, BoundaryError
from source_cleanup import single_stream

MAX_JSON = 64 * 1024 * 1024
MAX_CANDIDATES = 64
MAX_OWNED_FILES = 100000
BOOTSTRAP = 'books-arranger-installation.json'
OWNERSHIP_SCHEMA = 'books-installation-ownership-v1'
PLAN_SCHEMA = 'books-installation-cleanup-plan-v1'


def capture_current_package(application_dir,installation_id):
    """Install-only snapshot, admitted against the fresh pinned builder payload."""
    source=Path(__file__).resolve().parent/'current-package.json'
    producer,_,_= _json(source)
    _need(producer.get('schema')=='books-trusted-current-package-v1','package_ownership_required')
    app=_absolute(application_dir);expected=producer['files'];members=set();files=[];directories=set()
    with contextlib.ExitStack() as stack:
        boundary=stack.enter_context(DirectoryBoundary(app.anchor,app))
        identity=list(boundary.identities[-1][1:])
        for folder,names,entries in os.walk(app,followlinks=False):
            folder=Path(folder);stack.enter_context(DirectoryBoundary(app,folder));directories.add(folder)
            for name in entries:members.add((folder/name).relative_to(app).as_posix())
        _need(members==set(expected),'package_members_changed',app)
        expected_dirs={app}
        for relative in expected:
            parent=(app/relative).parent
            while parent!=app:expected_dirs.add(parent);parent=parent.parent
        _need(directories==expected_dirs,'package_members_changed',app)
        for relative,known in sorted(expected.items()):
            _need(not Path(relative).is_absolute() and '..' not in Path(relative).parts,'package_members_changed')
            path=app/relative;held=stack.enter_context(VerifiedFile(path));single_stream(path);facts=held.facts()
            _need(facts['links']==1 and facts['size']==known['size'] and held.sha256()==known['sha256'],'package_members_changed',path)
            files.append(dict(relative=relative,facts=facts,sha256=known['sha256']))
        value=dict(schema=OWNERSHIP_SCHEMA,installation_id=installation_id,application_dir=str(app),
            roots=[dict(path=str(app),identity=identity,role='application',files=files)])
        output=app.parent/('books-package-owned-'+str(uuid.uuid4())+'.json')
        produced=_write_new(output,json.dumps(value,sort_keys=True).encode('utf8'))
        return dict(manifest=str(output),sha256=produced['sha256'])


def remove_current_package(bootstrap_path,expected_application_dir=None):
    bootstrap,_,_=_json(bootstrap_path,65536)
    _need(bootstrap.get('schema')=='books-arranger-installation-v1','package_ownership_required')
    if expected_application_dir is not None:
        _need(os.path.normcase(str(_absolute(expected_application_dir)))==os.path.normcase(str(_absolute(bootstrap['application_dir']))),
            'installation_location_changed',bootstrap_path)
    pin=bootstrap.get('package_ownership');_need(isinstance(pin,dict) and set(pin)=={'manifest','sha256'},'package_ownership_required')
    owner,_,sha=_json(pin['manifest']);_need(sha==pin['sha256'] and owner.get('installation_id')==bootstrap['installation_id'] and
        owner.get('application_dir')==bootstrap['application_dir'],'package_ownership_required')
    _need(process_check([bootstrap['application_dir']])['state']=='available','in_use')
    plan=plan_cleanup(pin['manifest'],pin['sha256'],selected_roots=[bootstrap['application_dir']],bootstrap_paths=[str(bootstrap_path)])
    digest=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return execute_cleanup(plan,digest)


def _attach_retained_package(bootstrap,pin):
    receipt,_,sha=_json(pin['manifest'])
    _need(sha==pin['sha256'] and receipt.get('schema')=='books-legacy-package-retirement-v1' and
        receipt.get('state')=='original-retained','legacy_retention_unverified')
    kept=_absolute(receipt['retained_application'])
    with DirectoryBoundary(kept.anchor,kept) as held:_need(list(held.identities[-1][1:])==receipt['root_identity'],'legacy_retention_unverified')
    for entry in receipt['files']:
        with VerifiedFile(kept/entry['relative']) as held:
            _need(held.facts()==entry['facts'] and held.sha256()==entry['sha256'],'legacy_retention_unverified')
    owner,_,_=_json(bootstrap['ownership_manifest'])
    _need(owner['schema']==OWNERSHIP_SCHEMA and owner['installation_id']==bootstrap['installation_id'],'ownership_not_confirmed')
    roots=list(owner['roots']);root=dict(path=str(kept),identity=receipt['root_identity'],role='backups',files=receipt['files'])
    found=next((entry for entry in roots if entry['path']==str(kept)),None)
    if found:_need(found==root,'ownership_changed')
    else:roots.append(root)
    changed=dict(owner,roots=roots);output=_absolute(bootstrap['application_dir']).parent/('books-arranger-owned-'+str(uuid.uuid4())+'.json')
    _write_new(output,json.dumps(changed,sort_keys=True).encode('utf8'))
    bootstrap['ownership_manifest']=str(output);bootstrap['retained_package']=pin
    return bootstrap


def _seal_install_controls(value,namespace_pin=None,previous=None,backup_path=None):
    from storage_lifecycle_controls import capture_control_producer
    app=_absolute(value['application_dir']);namespaces=[];extra=[];deferred=[]
    if namespace_pin:
        creation,_,sha=_json(namespace_pin['manifest']);_need(sha==namespace_pin['sha256'] and
            creation.get('schema')=='books-control-namespace-creation-v1' and creation.get('application_dir')==str(app),
            'control_namespace_unverified')
        namespaces.append(creation['namespace'])
    intent=app.parent/'books-arranger-selection-in-progress.json'
    if intent.exists():extra.append(dict(path=str(intent),kind='selection-intent'))
    retained=value.get('retained_package')
    if retained:
        record,_,sha=_json(retained['manifest']);_need(sha==retained['sha256'],'legacy_retention_unverified')
        if record.get('intent'):extra.append(dict(path=record['intent']['manifest'],sha256=record['intent']['sha256'],kind='retained_package'))
    if previous:
        old=previous['value']
        for field in ('ownership_manifest','ownership_provenance','package_ownership','retained_package','retained_profile','storage_relocation'):
            pin=old.get(field)
            if not pin:continue
            extra.append(dict(path=pin if field=='ownership_manifest' else pin['manifest'],kind=field,
                **({} if field=='ownership_manifest' else dict(sha256=pin['sha256']))))
        if backup_path:
            deferred.append(dict(path=str(backup_path),source=str(app.parent/BOOTSTRAP),facts=previous['facts'],sha256=previous['sha256']))
    value['control_provenance']=capture_control_producer(str(app),value['installation_id'],namespaces,extra_files=extra,
        prior_pin=previous['value'].get('control_provenance') if previous else None,deferred_files=deferred)
    return value


def publish_current_package(bootstrap_path,retained_package=None,control_namespace=None):
    bootstrap,facts,sha=_json(bootstrap_path,65536)
    _need(bootstrap.get('schema')=='books-arranger-installation-v1','package_ownership_required')
    _need(process_check([bootstrap['application_dir']])['state']=='available','in_use')
    changed=dict(bootstrap,package_ownership=capture_current_package(bootstrap['application_dir'],bootstrap['installation_id']))
    if retained_package:changed=_attach_retained_package(changed,retained_package)
    previous=dict(value=bootstrap,facts=facts,sha256=sha)
    backup=Path(bootstrap_path).with_name('books-arranger-installation.previous-'+str(uuid.uuid4())+'.json')
    changed=_seal_install_controls(changed,control_namespace,previous,backup)
    retained=_replace_bootstrap(Path(bootstrap_path),json.dumps(changed,sort_keys=True).encode('utf8'),
        previous,backup_path=backup)
    return dict(ok=True,bootstrap=str(bootstrap_path),previous_bootstrap=retained)


def admit_application_target(application_dir,registered_application_dir='',registered_version='',process_name='Books Arranger.exe'):
    """Read-only pre-INSTFILES admission; unknown existing content is retained."""
    target=_absolute(application_dir);_local(target)
    from storage_lifecycle_controls import assert_no_pending_overlap
    assert_no_pending_overlap([str(target)])
    _need(not any((ancestor/'.git').exists() for ancestor in (target,*target.parents)),
        'application_target_source_repository',target)
    if not target.exists():
        ancestor=target.parent
        while not ancestor.exists():ancestor=ancestor.parent
        with DirectoryBoundary(ancestor.anchor,ancestor):pass
        return dict(ok=True,state='new_target',path=str(target))
    with DirectoryBoundary(target.anchor,target):
        from storage_relocation_operator import _no_directory_streams
        _no_directory_streams(target)
        empty=not any(target.iterdir())
    if empty:return dict(ok=True,state='empty_target',path=str(target))
    _need(registered_application_dir and os.path.normcase(str(_absolute(registered_application_dir)))==os.path.normcase(str(target)),
        'application_target_not_empty',target)
    if registered_version=='0.27.0':retire_legacy_package(str(target),registered_version,_inspect=True,process_name=process_name)
    else:retire_owned_package(str(target),registered_version,_inspect=True,process_name=process_name)
    return dict(ok=True,state='verified_old_package',path=str(target))


def legacy_update_plan(application_dir,version,*,process_name='Books Arranger.exe'):
    """Preserve this machine's exact legacy catalog/profile during silent update."""
    app=_absolute(application_dir);bootstrap=app.parent/BOOTSTRAP
    if bootstrap.exists():
        value,_,_=_json(bootstrap,65536)
        _need(value.get('schema')=='books-arranger-installation-v1' and
            value.get('application_dir')==str(app),'legacy_update_requires_assisted_setup',bootstrap)
        return dict(existing_bootstrap=True)
    _need(version=='0.27.0','legacy_update_requires_assisted_setup',app)
    _need(process_check([app],process_name)['state']=='available','in_use')
    roaming=os.environ.get('APPDATA');_need(roaming,'legacy_update_requires_assisted_setup')
    settings=Path(roaming)/'Books Arranger'/'desktop-settings.json'
    _need(settings.exists(),'legacy_update_requires_assisted_setup',settings)
    value,_,_=_json(settings,16384)
    _need(isinstance(value,dict) and isinstance(value.get('dataDir'),str),'legacy_update_requires_assisted_setup',settings)
    chosen=selection_plan('existing',str(_absolute(value['dataDir'])/'inventory.sqlite3'),
        application_dir=str(app),profile_dir=str(app.parent/'Profile'),config_paths=[str(settings)])
    _need(chosen['selection'].get('profile_confirmed') is True and
        _absolute(chosen['selection']['associated_profile'])==settings.parent,'legacy_update_requires_assisted_setup',settings)
    for name in ('Profile','Temp','Downloads','Logs'):
        path=app.parent/name
        _need(not path.exists() or not any(path.iterdir()),'legacy_update_requires_assisted_setup',path)
    return dict(existing_bootstrap=False,plan=chosen)


def retire_owned_package(installation_dir,version,*,process_name='Books Arranger.exe',_inspect=False):
    root=_absolute(installation_dir);bootstrap,_,_=_json(root.parent/BOOTSTRAP,65536)
    _need(bootstrap.get('schema')=='books-arranger-installation-v1' and
        _absolute(bootstrap['application_dir'])==root,'package_ownership_required')
    pin=bootstrap.get('package_ownership');_need(isinstance(pin,dict),'package_ownership_required')
    owner,_,sha=_json(pin['manifest']);_need(sha==pin['sha256'] and owner.get('installation_id')==bootstrap['installation_id'] and
        owner.get('application_dir')==str(root) and len(owner['roots'])==1,'package_ownership_required')
    package=owner['roots'][0];_need(package['path']==str(root) and package['role']=='application','package_ownership_required')
    with DirectoryBoundary(root.anchor,root) as held:_need(list(held.identities[-1][1:])==package['identity'],'package_ownership_required')
    files={entry['relative']:dict(size=entry['facts']['size'],sha256=entry['sha256'],facts=entry['facts']) for entry in package['files']}
    trusted=dict(schema='books-trusted-legacy-package-v1',version=version,files=files,installer_sha256=None,package_proof_sha256=sha)
    return retire_legacy_package(installation_dir,version,process_name=process_name,_trusted=trusted,_inspect=_inspect)


def retire_legacy_package(installation_dir, version, *, process_name='Books Arranger.exe',_trusted=None,_inspect=False):
    """Remove only an exact accepted binary payload. Never execute its uninstaller.

    Registry publication and the installer-created shortcuts remain the NEW
    installer's transaction. Existing data is never part of this package receipt.
    Unknown versions, extra members and partial prior removal are held for review.
    """
    _need(_trusted is not None or version == '0.27.0', 'unsupported_legacy_package', installation_dir)
    root = _absolute(installation_dir); _local(root)
    source = Path(__file__).resolve().parent/'legacy-package-0.27.0.json'
    if not source.exists():source = Path(__file__).resolve().parent/'desktop'/source.name
    manifest = _trusted if _trusted is not None else _json(source)[0]
    _need(manifest.get('schema') == 'books-trusted-legacy-package-v1' and
          manifest.get('version') == version, 'unsupported_legacy_package')
    expected = manifest['files']
    _need(0 < len(expected) < 2000, 'unsupported_legacy_package')
    _need(process_check([root], process_name)['state']=='available','in_use',root)
    with contextlib.ExitStack() as stack:
        boundary = stack.enter_context(DirectoryBoundary(root.anchor,root))
        observed = set(); directories = []
        for folder, names, files in os.walk(root,followlinks=False):
            folder=Path(folder)
            with DirectoryBoundary(root,folder) as parent:
                directories.append((folder,list(parent.identities[-1][1:])))
            for name in names:
                _need(not (folder/name).is_symlink(),'unsupported_legacy_package',folder/name)
            for name in files:observed.add((folder/name).relative_to(root).as_posix())
        _need(observed == set(expected),'legacy_package_changed',root)
        expected_dirs={root}
        for relative in expected:
            parent=(root/relative).parent
            while parent!=root:
                expected_dirs.add(parent);parent=parent.parent
        _need({path for path,_ in directories}==expected_dirs,'legacy_package_changed',root)
        prepared=[]
        for relative, known in sorted(expected.items()):
            _need(not Path(relative).is_absolute() and '..' not in Path(relative).parts,
                  'unsupported_legacy_package')
            path=root/relative
            parent=stack.enter_context(DirectoryBoundary(root,path.parent))
            held=stack.enter_context(VerifiedFile(path,delete=True));single_stream(path)
            facts=held.facts()
            _need(facts['links']==1 and facts['size']==known['size'] and
                  held.sha256()==known['sha256'],'legacy_package_changed',path)
            if 'facts' in known:_need(facts==known['facts'],'legacy_package_changed',path)
            prepared.append((path,parent,held,facts))
        if _inspect:return dict(ok=True,state='verified_old_package',path=str(root))
        # Preserve the ORIGINAL directory and all native file identities. This
        # is a same-volume retained rename, never copy/delete pseudo-rollback.
        transaction=str(uuid.uuid4())
        journal=root.parent/('books-legacy-retirement-'+transaction+'.json')
        backup=root.parent/('RetainedApplication-'+transaction)
        root_identity=list(boundary.identities[-1][1:])
        receipt=dict(schema='books-legacy-package-retirement-v1',root=str(root),version=version,
                     installer_sha256=manifest['installer_sha256'],
                     package_proof_sha256=manifest.get('package_proof_sha256'),
                     files=[dict(relative=p.relative_to(root).as_posix(),facts=f,sha256=expected[p.relative_to(root).as_posix()]['sha256']) for p,_,_,f in prepared],
                     retained_application=str(backup),root_identity=root_identity,
                     state='retention-intent')
        intent_proof=_write_new(journal,json.dumps(receipt,sort_keys=True).encode('utf8'))
        # Release ancestry handles that conflict with our own root DELETE rename.
        for parent in [boundary]+[p for _,p,_,_ in prepared]:parent.__exit__(None,None,None)
        # NTFS also refuses parent rename while a child denies DELETE sharing.
        # The following operation retains the ENTIRE directory, never deletes
        # a member. Re-admit every original identity/content at its retained
        # name before any new application extraction may proceed.
        for _,_,held,_ in prepared:held.__exit__(None,None,None)
        from directory_retention import retain_directory_no_replace
        result=retain_directory_no_replace(root,backup,root_identity)
        _need(result.get('original_preserved') is True,'legacy_original_not_preserved')
        with contextlib.ExitStack() as checked:
            kept=checked.enter_context(DirectoryBoundary(backup.anchor,backup))
            _need(list(kept.identities[-1][1:])==root_identity,'legacy_original_not_preserved')
            observed=set()
            for folder,_,entries in os.walk(backup,followlinks=False):
                checked.enter_context(DirectoryBoundary(backup,folder))
                observed.update((Path(folder)/name).relative_to(backup).as_posix() for name in entries)
            _need(observed==set(expected),'legacy_original_changed_after_retention',backup)
            for old,_,_,facts in prepared:
                path=backup/old.relative_to(root);held=checked.enter_context(VerifiedFile(path));single_stream(path)
                _need(held.facts()==facts and held.sha256()==expected[old.relative_to(root).as_posix()]['sha256'],
                      'legacy_original_changed_after_retention',path)
        complete=dict(receipt,state='original-retained',retention=result,intent=dict(manifest=str(journal),sha256=intent_proof['sha256']))
        completed=root.parent/('books-legacy-retirement-complete-'+transaction+'.json')
        produced=_write_new(completed,json.dumps(complete,sort_keys=True).encode('utf8'))
    return dict(ok=True,result='legacy_package_retained',receipt=str(completed),receipt_sha256=produced['sha256'],
                retained_application=str(backup),removed_files=0,removed_directories=[])


class LifecycleRefused(ValueError):
    def __init__(self, code, path=''):
        self.code, self.path = code, str(path)
        super().__init__(code)


def _wait_uninstall_launcher(pid,application_dir):
    """Wait only for the exact pinned new launcher; never ignore a live PID."""
    _need(isinstance(pid,int) and 0<pid<2**32,'invalid_launcher_pid')
    root=_absolute(str(application_dir));bootstrap,_,_=_json(root.parent/BOOTSTRAP,65536)
    _need(bootstrap.get('application_dir')==str(root),'launcher_package_unverified')
    pin=bootstrap.get('package_ownership');_need(isinstance(pin,dict),'launcher_package_unverified')
    package,_,sha=_json(pin['manifest']);_need(sha==pin['sha256'],'launcher_package_unverified')
    expected=next((f for r in package.get('roots',[]) if r.get('path')==str(root)
                   for f in r.get('files',[]) if f.get('relative')=='Books Arranger.exe'),None)
    _need(expected is not None,'launcher_package_unverified')
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    process=kernel.OpenProcess(0x1000|0x100000,False,pid)
    if not process:
        # A vanished PID grants no exemption. The unchanged full inventory and
        # catalog locks below still decide whether uninstall can proceed.
        _need(ctypes.get_last_error()==87,'process_check_unavailable');return
    try:
        kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        image=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(image))
        _need(kernel.QueryFullProcessImageNameW(process,0,image,ctypes.byref(size)),'process_check_unavailable')
        _need(os.path.normcase(image.value)==os.path.normcase(str(root/'Books Arranger.exe')),'launcher_package_unverified')
        with VerifiedFile(image.value) as held:
            _need(held.facts()==expected['facts'] and held.sha256()==expected['sha256'],'launcher_package_unverified')
            kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
            _need(kernel.WaitForSingleObject(process,5000)==0,'in_use')
    finally:kernel.CloseHandle(process)


def process_check(installation_dirs=(), process_name='Books Arranger.exe',*,launcher_pid=None):
    """Native inventory only: this never sends messages or terminates a PID."""
    _need(isinstance(process_name, str) and process_name and
          Path(process_name).name == process_name, 'invalid_process_name')
    roots = tuple(_absolute(str(p)) for p in installation_dirs)
    if launcher_pid is not None:
        _need(len(roots)==1,'launcher_package_unverified');_wait_uninstall_launcher(launcher_pid,roots[0])
    class Entry(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('usage', wintypes.DWORD), ('pid', wintypes.DWORD),
                    ('heap', ctypes.c_size_t), ('module', wintypes.DWORD), ('threads', wintypes.DWORD),
                    ('parent', wintypes.DWORD), ('priority', wintypes.LONG), ('flags', wintypes.DWORD),
                    ('image', wintypes.WCHAR * 260)]
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    _need(snapshot != ctypes.c_void_p(-1).value, 'process_check_unavailable')
    busy = []
    try:
        entry = Entry(); entry.size = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        _need(more, 'process_check_unavailable')
        while more:
            if entry.pid != os.getpid():
                if entry.image.lower() == process_name.lower():
                    busy.append({'pid': entry.pid, 'kind': 'application'})
                elif roots and entry.image.lower() in ('python.exe', 'pythonw.exe', 'ffmpeg.exe', 'ffprobe.exe'):
                    process = kernel.OpenProcess(0x1000, False, entry.pid)
                    _need(process, 'process_check_unavailable')
                    try:
                        image = ctypes.create_unicode_buffer(32768); size = wintypes.DWORD(len(image))
                        _need(kernel.QueryFullProcessImageNameW(process, 0, image, ctypes.byref(size)), 'process_check_unavailable')
                        if any(_under(Path(image.value), root) for root in roots):
                            busy.append({'pid': entry.pid, 'kind': 'worker'})
                    finally:kernel.CloseHandle(process)
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:kernel.CloseHandle(snapshot)
    # Legacy Python hosts may execute from the compatibility cache, outside the
    # installed binary root. A closed Electron window/finished encoder is not
    # batch closure: inspect bounded known per-machine catalog owner locks too.
    for config in known_configurations():
        if not Path(config).exists():continue
        settings,_,_=_json(config,16384)
        _need(isinstance(settings,dict),'process_check_unavailable',config)
        if not settings.get('dataDir'):continue
        lock=_absolute(settings['dataDir'])/'inventory.sqlite3.lock'
        if not lock.exists():continue
        try:
            with VerifiedFile(lock):pass
        except BoundaryError:
            busy.append({'kind':'catalog-owner','path':str(lock)})
    return {'state': 'in_use' if busy else 'available', 'busy': busy}


def _need(condition, code, path=''):
    if not condition:
        raise LifecycleRefused(code, path)


def _absolute(value):
    _need(isinstance(value, str) and value and '\n' not in value and '\r' not in value and
          '\x00' not in value and Path(value).is_absolute(), 'invalid_path', value)
    return Path(value).absolute()


def _under(path, root):
    try:
        return os.path.commonpath((os.path.normcase(str(path)), os.path.normcase(str(root)))) == os.path.normcase(str(root))
    except ValueError:
        return False


def _resolved(handle):
    kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(32768)
    size = kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    _need(0 < size < len(buffer), 'cannot_resolve_physical_path')
    value = buffer.value
    if value.startswith('\\\\?\\UNC\\'):
        value = '\\\\' + value[8:]
    elif value.startswith('\\\\?\\'):
        value = value[4:]
    return str(Path(value))


def _json(path, limit=MAX_JSON):
    path = _absolute(str(path))
    with DirectoryBoundary(path.anchor, path.parent), VerifiedFile(path) as file:
        facts = file.facts()
        _need(facts['links'] == 1 and facts['size'] <= limit, 'invalid_bounded_file', path)
        single_stream(path)
        raw = b''.join(file.chunks())
        def unique(pairs):
            result = {}
            for key, value in pairs:
                _need(key not in result, 'duplicate_json_key', path)
                result[key] = value
            return result
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique), facts, hashlib.sha256(raw).hexdigest()


def _local(path):
    kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    kernel.GetDriveTypeW.restype = wintypes.UINT
    _need(kernel.GetDriveTypeW(Path(path).anchor) == 3, 'local_fixed_drive_required', path)


def _pinned_relocation(database, activation, registration=None, selection=None):
    """Read-only descriptor discovery, never target activation or repair."""
    from storage_relocation import parse_manifest
    catalog_id,generation,manifest_sha,phase=activation
    _need(phase in ('active','verifying'),'relocation_verification_required',database)
    if selection is None:
        _need(registration is not None,'relocation_configuration_required',database)
        rid,rgen,rsha,receipt_path,receipt_sha,_=registration
        _need((rid,rgen,rsha)==(catalog_id,generation,manifest_sha),'relocation_configuration_required',database)
        receipt,_,digest=_json(receipt_path)
        _need(digest==receipt_sha and receipt.get('schema')=='books-storage-target-verification-v1' and
              (receipt.get('catalog_id'),receipt.get('generation'),receipt.get('manifest_sha256'))==
              (catalog_id,generation,manifest_sha),'relocation_configuration_required',database)
        selection={'manifest':receipt['manifest_path'],'sha256':manifest_sha}
    _need(isinstance(selection,dict) and set(selection)=={'manifest','sha256'} and
          selection['sha256']==manifest_sha,'relocation_configuration_required',database)
    path=_absolute(selection['manifest'])
    with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as file:
        _need(file.facts()['links']==1 and file.facts()['size']<=64*1024*1024,'relocation_configuration_required',path)
        single_stream(path);manifest=parse_manifest(b''.join(file.chunks()),selection['sha256'])
    _need((manifest.catalog_id,manifest.generation)==(catalog_id,generation),'relocation_configuration_required',path)
    target=_absolute(manifest.target_root)
    physical=_absolute(str(database))
    _need(_under(physical,target),'relocation_configuration_required',database)
    relative=physical.relative_to(target)
    _need(manifest.permitted(str(Path(manifest.source_root)/relative)),'relocation_configuration_required',database)
    with DirectoryBoundary(target.anchor,target) as directory:
        _need(tuple(directory.identities[-1][1:])==manifest.directories[''].target,'relocation_configuration_required',target)
    return dict(manifest=str(path),sha256=selection['sha256'])


def inspect_existing(database, *, config_paths=()):
    """Read-only, WAL-aware recognition; aliases deduplicate by native file ID."""
    path = _absolute(str(database))
    result = {'path': str(path), 'state': 'could_not_check', 'bytes': None,
              'profile_confirmed': False, 'profile_dir': None, 'aliases': [str(path)]}
    relocation=None;registration=None
    try:
        _local(path)
        _need(path.name == 'inventory.sqlite3', 'unsupported_database', path)
        # This file is a discovery read, not a deletion authority. Resolving its
        # existing ancestors allows an old-looking alias to be SHOWN/deduped.
        with VerifiedFile(path) as held:
            facts = held.facts(); physical = _resolved(held.handle)
            _need(facts['links'] == 1, 'unsupported_database', path)
            single_stream(path)
            result.update(bytes=facts['size'], identity=facts['identity'], resolved_path=physical,
                          data_dir=str(Path(physical).parent), facts=facts,
                          wal_present=Path(str(path) + '-wal').exists())
            lock = Path(str(path) + '.lock')
            with contextlib.ExitStack() as stack:
                if lock.exists():
                    stack.enter_context(VerifiedFile(lock))
                with contextlib.closing(sqlite3.connect(Path(physical).as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
                    db.execute('PRAGMA query_only=ON'); db.execute('PRAGMA temp_store=MEMORY')
                    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    _need({'jobs', 'queue', 'files'} <= tables, 'unsupported_database', path)
                    columns = {row[1] for row in db.execute('PRAGMA table_info(files)')}
                    _need({'root', 'path', 'size', 'modified', 'kind'} <= columns, 'unsupported_database', path)
                    _need(db.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'unsupported_database', path)
                    if 'storage_relocation_activation' in tables:
                        rows=db.execute('SELECT catalog_id,generation,manifest_sha256,phase FROM storage_relocation_activation').fetchall()
                        _need(len(rows)==1,'relocation_configuration_required',path)
                        relocation=tuple(rows[0])
                        if 'storage_relocation_verification' in tables:
                            rows=db.execute('SELECT catalog_id,generation,manifest_sha256,receipt_path,receipt_sha256,verified_state_sha256 FROM storage_relocation_verification').fetchall()
                            _need(len(rows)<=1,'relocation_configuration_required',path)
                            registration=tuple(rows[0]) if rows else None
            result['state'] = 'available'
        for config in tuple(config_paths)[:MAX_CANDIDATES]:
            try:
                settings, settings_facts, settings_hash = _json(config, 16384)
                if not isinstance(settings, dict) or not isinstance(settings.get('dataDir'), str):
                    continue
                configured = _absolute(settings['dataDir']) / 'inventory.sqlite3'
                with VerifiedFile(configured) as file:
                    same = file.facts()['identity'] == result['identity']
                if same:
                    result.update(profile_confirmed=True, profile_dir=str(Path(config).absolute().parent),
                                  profile_settings_path=str(Path(config).absolute()),
                                  profile_settings_facts=settings_facts, profile_settings_sha256=settings_hash)
                    if relocation and settings.get('storage_relocation'):
                        result['storage_relocation']=_pinned_relocation(result['resolved_path'],relocation,selection=settings['storage_relocation'])
                    break
            except (OSError, ValueError, sqlite3.Error):
                continue
        if relocation:
            result['storage_relocation']=result.get('storage_relocation') or _pinned_relocation(result['resolved_path'],relocation,registration)
            result['verification_required']=relocation[3]!='active'
    except LifecycleRefused as error:
        result.update(state=error.code, error_path=error.path)
    except (FileNotFoundError, NotADirectoryError):
        result['state'] = 'location_unavailable'
    except PermissionError:
        result['state'] = 'access_denied'
    except BoundaryError as error:
        code=getattr(error, 'diagnostic', {}).get('windows_error')
        result['state'] = ('in_use' if code == 32 else 'location_unavailable' if code in (2,3,21,53,67)
                           else 'access_denied' if code == 5 else 'could_not_check')
    except sqlite3.DatabaseError:
        result['state'] = 'unsupported_database'
    except (OSError, ValueError):
        result['state'] = 'could_not_check'
    return result


def known_candidates(config_paths=(), extra_candidates=(), bootstrap_paths=()):
    """No directory crawl: explicit configurations and exact conventional paths."""
    configs = list(config_paths)
    roaming = os.environ.get('APPDATA')
    if roaming:
        configs.append(str(Path(roaming) / 'Books Arranger' / 'desktop-settings.json'))
    _need(len(configs) <= MAX_CANDIDATES and len(extra_candidates) <= MAX_CANDIDATES,
          'discovery_bound_exceeded')
    paths = list(extra_candidates)
    bootstraps=list(bootstrap_paths)+registered_bootstraps()
    _need(len(bootstraps)<=MAX_CANDIDATES,'discovery_bound_exceeded')
    for bootstrap in bootstraps:
        if not Path(bootstrap).exists():continue
        try:
            value,_,_=_json(bootstrap,65536)
            _need(value.get('schema')=='books-arranger-installation-v1','invalid_installation_reference',bootstrap)
            paths.append(str(_absolute(value['data_dir'])/'inventory.sqlite3'))
            configs.append(str(_absolute(value['profile_dir'])/'desktop-settings.json'))
        except (OSError,ValueError):paths.append(str(Path(bootstrap).absolute()))
    for config in configs:
        try:
            value, _, _ = _json(config, 16384)
            if isinstance(value, dict) and isinstance(value.get('dataDir'), str):
                paths.append(str(_absolute(value['dataDir']) / 'inventory.sqlite3'))
        except (OSError, ValueError):
            # Failed CONFIG paths remain visible; they are not a false empty scan.
            paths.append(str(Path(config).absolute()))
    local = os.environ.get('LOCALAPPDATA')
    if local:
        paths.append(str(Path(local) / 'Books Arranger' / 'data' / 'inventory.sqlite3'))
    _need(len(paths) <= MAX_CANDIDATES, 'discovery_bound_exceeded')
    rows, by_identity, seen = [], {}, set()
    for path in paths:
        key = os.path.normcase(str(Path(path).absolute()))
        if key in seen:
            continue
        seen.add(key)
        row = inspect_existing(path, config_paths=configs)
        identity = tuple(row.get('identity') or ())
        if row['state'] == 'available' and identity in by_identity:
            by_identity[identity]['aliases'].append(row['path'])
        else:
            rows.append(row)
            if row['state'] == 'available':
                by_identity[identity] = row
    return {'schema': 'books-catalog-discovery-v1', 'candidates': rows,
            'locations_checked': len(seen), 'scan_complete': all(r['state'] == 'available' for r in rows)}


def known_configurations(extra=()):
    configs=list(extra)
    if os.environ.get('APPDATA'):
        configs.append(str(Path(os.environ['APPDATA'])/'Books Arranger'/'desktop-settings.json'))
    for bootstrap in registered_bootstraps():
        if not Path(bootstrap).exists():continue
        value,_,_=_json(bootstrap,65536)
        _need(value.get('schema')=='books-arranger-installation-v1','installation_reference_unchecked',bootstrap)
        configs.append(str(_absolute(value['profile_dir'])/'desktop-settings.json'))
    _need(len(configs)<=MAX_CANDIDATES,'discovery_bound_exceeded')
    return tuple(dict.fromkeys(configs))


def inspect_new(folder, *, protected_paths=()):
    path = _absolute(str(folder)); _local(path)
    _need(not any(_under(path, _absolute(str(p))) or _under(_absolute(str(p)), path)
                  for p in protected_paths), 'protected_location', path)
    ancestor = path
    while not ancestor.exists():
        _need(ancestor.parent != ancestor, 'location_unavailable', path)
        ancestor = ancestor.parent
    with DirectoryBoundary(ancestor.anchor, ancestor) as held:
        _need(not path.exists() or path.is_dir(), 'new_folder_not_empty', path)
        _need(not path.exists() or not any(path.iterdir()), 'new_folder_not_empty', path)
        return {'mode': 'new', 'data_dir': str(path), 'ancestor': str(ancestor),
                'ancestor_identity': list(held.identities[-1][1:]), 'existing': path.exists()}


def _maintenance_selection(app, profile, data, previous=None, protected_paths=()):
    """Review a portable operational parent, outside retained user state."""
    old=previous or {};path=_absolute(old.get('maintenance_temp_dir') or str(app.parent/'MaintenanceTemp'))
    _local(path)
    protected=[app,profile,data,app.parent/'Temp',app.parent/'Downloads',app.parent/'Logs',
               app.parent/'CleanupReceipts',app.parent/'InstallerTransactions',
               *_protected_paths(protected_paths),*_other_installation_paths(old.get('installation_id'),str(app))]
    pin=old.get('control_provenance')
    if pin:
        index,_,sha=_json(pin['manifest']);_need(sha==pin['sha256'],'ownership_not_confirmed')
        protected.extend(entry['path'] for entry in index.get('directories',()))
    _need(not any(_under(path,_absolute(str(p))) or _under(_absolute(str(p)),path) for p in protected),
          'storage_locations_overlap',path)
    _need(not any((ancestor/'.git').exists() for ancestor in (path,*path.parents)),
          'application_target_source_repository',path)
    if old.get('maintenance_temp_dir') is not None:
        expected=old.get('maintenance_temp_identity')
        _need(isinstance(expected,list) and len(expected)==3 and all(type(n) is int and 0<=n<=0xffffffff for n in expected),
              'ownership_not_confirmed',path)
        with DirectoryBoundary(path.anchor,path) as held:
            _need(list(held.identities[-1][1:])==expected,'selection_changed',path)
        return dict(path=str(path),existing=True,identity=expected,previously_bound=True)
    selected=inspect_new(path,protected_paths=protected)
    return dict(path=str(path),**{k:v for k,v in selected.items() if k not in ('mode','data_dir')},previously_bound=False)


def _commit_maintenance(selected):
    path=_absolute(selected['path']);_local(path)
    if selected['previously_bound']:
        with DirectoryBoundary(path.anchor,path) as held:
            identity=list(held.identities[-1][1:]);_need(identity==selected['identity'],'selection_changed',path)
    else:
        ancestor=_absolute(selected['ancestor'])
        with DirectoryBoundary(ancestor.anchor,ancestor) as held:
            _need(list(held.identities[-1][1:])==selected['ancestor_identity'],'selection_changed',ancestor)
        current=inspect_new(path);_need(current['existing']==selected['existing'],'selection_changed',path)
        with DirectoryBoundary(path.anchor,path,create=True) as held:identity=list(held.identities[-1][1:])
    return str(path),identity


def selection_plan(mode, location, *, application_dir, profile_dir, config_paths=(), protected_paths=()):
    app, profile = _absolute(str(application_dir)), _absolute(str(profile_dir))
    from storage_lifecycle_controls import assert_no_pending_overlap
    selected=_absolute(str(location));data_scope=selected.parent if selected.name=='inventory.sqlite3' else selected
    assert_no_pending_overlap([str(app),str(profile),str(data_scope)])
    previous=None;bootstrap=app.parent/BOOTSTRAP
    if bootstrap.exists():
        old,oldfacts,oldhash=_json(bootstrap,65536)
        _need(old.get('schema')=='books-arranger-installation-v1' and old.get('application_dir')==str(app),
              'existing_installation_selection_preserved',bootstrap)
        previous=dict(path=str(bootstrap),facts=oldfacts,sha256=oldhash,value=old)
    if mode == 'existing':
        row = inspect_existing(location, config_paths=known_configurations(config_paths))
        _need(row['state'] == 'available', row['state'], location)
        chosen = dict(mode=mode, database=row['path'], data_dir=row['data_dir'], database_facts=row['facts'],
                      resolved_database=row['resolved_path'], profile_confirmed=row['profile_confirmed'],
                      associated_profile=row.get('profile_dir'),
                      profile_settings_path=row.get('profile_settings_path'),
                      profile_settings_facts=row.get('profile_settings_facts'),
                      profile_settings_sha256=row.get('profile_settings_sha256'))
        if row.get('storage_relocation'):chosen['storage_relocation']=row['storage_relocation']
        if row.get('verification_required'):chosen['verification_required']=True
        if chosen.get('profile_confirmed'):
            chosen['profile_source_authority']=_profile_source_authority(chosen['associated_profile'])
    elif mode == 'new':
        chosen = inspect_new(location, protected_paths=protected_paths)
        chosen['database'] = str(_absolute(str(location)) / 'inventory.sqlite3')
    else:
        raise LifecycleRefused('invalid_mode')
    _need(not _under(_absolute(chosen['data_dir']), app), 'data_inside_application', chosen['data_dir'])
    if previous:
        old=previous['value']
        if mode=='existing' and _absolute(old['data_dir'])==_absolute(chosen['data_dir']):
            profile=_absolute(old['profile_dir'])
        else:
            # A reviewed new/different catalog gets a separate fresh profile;
            # the old profile and its pending decisions remain retained.
            profile=app.parent/('Profile-'+str(uuid.uuid4()))
    data=_absolute(chosen['data_dir'])
    _need(not _under(app,data),'data_contains_application',data)
    for managed in (profile,app.parent/'Temp',app.parent/'Downloads',app.parent/'Logs'):
        _need(not _under(data,managed) and not _under(managed,data),'storage_locations_overlap',data)
    result={'schema': 'books-installation-selection-v1', 'application_dir': str(app),
            'profile_dir': str(profile), 'selection': chosen,
            'maintenance_selection':_maintenance_selection(app,profile,data,previous['value'] if previous else None,protected_paths)}
    if previous:result['previous_bootstrap']=previous
    return result


def _replace_bootstrap(path,raw,expected,*,backup_path=None):
    """Exact native old-file rotation + no-replace publish; retain rollback copy."""
    from native_io import rename_no_replace
    path=_absolute(str(path));temp=path.with_name('.books-installation-'+str(uuid.uuid4())+'.json')
    backup=Path(backup_path) if backup_path is not None else path.with_name('books-arranger-installation.previous-'+str(uuid.uuid4())+'.json')
    _need(backup.parent==path.parent and backup.name.startswith('books-arranger-installation.previous-') and backup.suffix=='.json',
        'invalid_bootstrap_rotation',backup)
    produced=_write_new(temp,raw)
    with DirectoryBoundary(path.anchor,path.parent,rename_destination=True) as boundary,VerifiedFile(path,delete=True) as old:
        _need(old.facts()==expected['facts'] and old.sha256()==expected['sha256'],'selection_changed',path)
        rename_no_replace(old,backup,boundary,boundary,expected_identity=old.facts(),
                          expected_size=old.facts()['size'],expected_sha256=expected['sha256'])
        try:
            with VerifiedFile(temp,delete=True) as new:
                _need(new.facts()==produced['facts'] and new.sha256()==produced['sha256'],'output_identity_changed',temp)
                rename_no_replace(new,path,boundary,boundary,expected_identity=new.facts(),
                                  expected_size=new.facts()['size'],expected_sha256=produced['sha256'])
        except BaseException:
            # Restore the same still-held original, never a pathname copy. A
            # conflicting current name is preserved and reported for recovery.
            old.path=backup
            rename_no_replace(old,path,boundary,boundary,expected_identity=old.facts(),
                              expected_size=old.facts()['size'],expected_sha256=expected['sha256'])
            raise
    return str(backup)


def _write_new(path, raw):
    """Native CREATE_NEW producer; existing files are never replace targets."""
    _need(isinstance(raw,bytes),'invalid_output')
    return _write_new_chunks(path,(raw[offset:offset+1024*1024] for offset in range(0,len(raw),1024*1024)))


def _write_new_chunks(path, chunks):
    """Stream a bounded block producer through one native CREATE_NEW handle."""
    from native_io import FileInfo
    path=_absolute(str(path))
    with DirectoryBoundary(path.anchor,path.parent,create=True):
        held=VerifiedFile(path,delete=True,writable=True)
        held.handle=kernel.CreateFileW(str(path),0xC0010081,1,None,1,0x00200000,None)
        if held.handle==ctypes.c_void_p(-1).value:
            held.handle=None;raise LifecycleRefused('existing_output_preserved',path)
        complete=False
        try:
            held.info=FileInfo()
            _need(kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)) and
                  not held.info.attributes & (0x400|0x10) and held.info.links==1,'output_identity_changed',path)
            kernel.WriteFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
            kernel.WriteFile.restype=wintypes.BOOL
            for block in chunks:
                _need(isinstance(block,bytes) and len(block)<=1024*1024,'invalid_output')
                buffer=ctypes.create_string_buffer(block);done=wintypes.DWORD()
                _need(kernel.WriteFile(held.handle,buffer,len(block),ctypes.byref(done),None) and done.value==len(block),'output_write_failed',path)
            held.flush()
            _need(kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)),'output_identity_changed',path)
            digest=held.sha256();complete=True
        finally:
            if not complete:held.dispose()
            held.__exit__(None,None,None)
        # Last-write time can settle when the writer handle closes. The receipt
        # names the closed file, just as later deletion verification will see it.
        with VerifiedFile(path) as closed:
            _need(closed.sha256()==digest,'output_identity_changed',path)
            return {'facts':closed.facts(),'sha256':digest}


def _profile_source_allowed(path):
    allowed=[]
    roaming=os.environ.get('APPDATA')
    if roaming:allowed.append(Path(roaming)/'Books Arranger')
    for bootstrap in registered_bootstraps():
        if not Path(bootstrap).exists():continue
        value,_,_=_json(bootstrap,65536)
        if value.get('schema')=='books-arranger-installation-v1':allowed.append(_absolute(value['profile_dir']))
    return any(os.path.normcase(_physical(path))==os.path.normcase(_physical(root)) for root in allowed if root.exists())


def _profile_source_authority(path):
    """Seal the registered source before stock registry publication replaces it."""
    path=_absolute(str(path));_need(_profile_source_allowed(path),'profile_account_not_confirmed',path)
    with DirectoryBoundary(path.anchor,path) as boundary:
        result=dict(profile=str(path),identity=list(boundary.identities[-1][1:]),account_sid=_current_user_sid())
    roaming=os.environ.get('APPDATA')
    if roaming and os.path.normcase(_physical(path))==os.path.normcase(_physical(Path(roaming)/'Books Arranger')):
        result['kind']='legacy-current-account';return result
    for bootstrap in registered_bootstraps():
        value,facts,sha=_json(bootstrap,65536)
        if value.get('schema')!='books-arranger-installation-v1' or _absolute(value['profile_dir'])!=path:continue
        producer=value.get('ownership_provenance')
        _need(isinstance(producer,dict),'profile_producer_not_confirmed',bootstrap)
        owned,_,digest=_json(producer['manifest'])
        _need(digest==producer['sha256'] and owned.get('installation_id')==value['installation_id'],
              'profile_producer_not_confirmed',bootstrap)
        _need(any(_absolute(root['path'])==path and root.get('role')=='profile' and root.get('identity')==result['identity']
                  for root in owned.get('roots',[])),'profile_producer_not_confirmed',path)
        result.update(kind='registered-installation',bootstrap=str(bootstrap),bootstrap_facts=facts,bootstrap_sha256=sha,
                      producer=dict(producer));return result
    raise LifecycleRefused('profile_account_not_confirmed',str(path))


def _validate_profile_source_authority(path,authority):
    _need(isinstance(authority,dict) and authority.get('profile')==str(path) and authority.get('account_sid')==_current_user_sid(),
          'profile_account_not_confirmed',path)
    with DirectoryBoundary(path.anchor,path) as held:
        _need(list(held.identities[-1][1:])==authority.get('identity'),'profile_source_changed',path)
    if authority.get('kind')=='legacy-current-account':
        roaming=os.environ.get('APPDATA')
        _need(roaming and os.path.normcase(_physical(path))==os.path.normcase(_physical(Path(roaming)/'Books Arranger')),
              'profile_account_not_confirmed',path)
    else:
        _need(authority.get('kind')=='registered-installation','profile_account_not_confirmed',path)
        value,facts,sha=_json(authority['bootstrap'],65536)
        _need(facts==authority['bootstrap_facts'] and sha==authority['bootstrap_sha256'] and
              value.get('ownership_provenance')==authority['producer'] and _absolute(value['profile_dir'])==path,
              'profile_source_changed',path)
        _,_,digest=_json(authority['producer']['manifest'])
        _need(digest==authority['producer']['sha256'],'profile_source_changed',path)


def _current_user_sid():
    api=ctypes.WinDLL('advapi32',use_last_error=True);token=wintypes.HANDLE()
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    api.OpenProcessToken.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
    api.GetTokenInformation.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    api.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(wintypes.LPWSTR)]
    _need(api.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)),'profile_account_not_confirmed')
    sid=wintypes.LPWSTR()
    try:
        size=wintypes.DWORD();api.GetTokenInformation(token,1,None,0,ctypes.byref(size))
        _need(0<size.value<65536,'profile_account_not_confirmed')
        data=ctypes.create_string_buffer(size.value)
        _need(api.GetTokenInformation(token,1,data,len(data),ctypes.byref(size)),'profile_account_not_confirmed')
        pointer=ctypes.cast(data,ctypes.POINTER(ctypes.c_void_p))[0]
        _need(api.ConvertSidToStringSidW(pointer,ctypes.byref(sid)),'profile_account_not_confirmed')
        return str(sid.value)
    finally:
        kernel.CloseHandle(token)
        if sid:
            local=ctypes.WinDLL('kernel32');local.LocalFree.argtypes=[ctypes.c_void_p];local.LocalFree(sid)


def _copy_profile(source,destination,settings_path,settings_facts,settings_sha256,proof_path,catalog_identity,source_authority=None):
    source,destination=_absolute(str(source)),_absolute(str(destination))
    if source_authority is None:_need(_profile_source_allowed(source),'profile_account_not_confirmed',source)
    else:_validate_profile_source_authority(source,source_authority)
    _need(not _under(source,destination) and not _under(destination,source),'profile_roots_overlap')
    value,facts,digest=_json(settings_path,16384)
    _need(facts==settings_facts and digest==settings_sha256,'settings_changed',settings_path)
    result=[];source_members=[]
    with contextlib.ExitStack() as stack:
        original=stack.enter_context(DirectoryBoundary(source.anchor,source))
        original_identity=list(original.identities[-1][1:])
        with DirectoryBoundary(destination.anchor,destination) as held:target_identity=list(held.identities[-1][1:])
        catalog_path=_absolute(value['dataDir'])/'inventory.sqlite3'
        catalog=stack.enter_context(VerifiedFile(catalog_path))
        _need(catalog.facts()['identity']==catalog_identity,'settings_changed',settings_path)
        for folder,dirs,names in os.walk(source,followlinks=False):
            _need(len(source_members)+len(dirs)+len(names)<=MAX_OWNED_FILES,'profile_copy_bound_exceeded',source)
            parent=Path(folder)
            stack.enter_context(DirectoryBoundary(parent.anchor,parent))
            for name in dirs:
                child=parent/name
                _need(not child.is_symlink() and not os.path.isjunction(child) and name!='.git','profile_contains_unknown_entry',child)
            for name in names:
                path=parent/name;held=stack.enter_context(VerifiedFile(path));single_stream(path)
                _need(held.facts()['links']==1,'profile_contains_unknown_entry',path)
                source_members.append((path,held,held.facts(),held.sha256()))
        # Every source file stays deny-write/delete held throughout all copies.
        for path,held,facts,digest in source_members:
            relative=path.relative_to(source);target=destination/relative
            produced=_write_new(target,b''.join(held.chunks()))
            _need(produced['sha256']==digest and produced['facts']['size']==facts['size'],'profile_copy_verification_failed',target)
            result.append(dict(relative=str(relative),**produced))
        source_files=[dict(relative=str(path.relative_to(source)),facts=facts,sha256=digest) for path,_,facts,digest in source_members]
        proof=dict(schema='books-retained-profile-copy-v1',account_sid=_current_user_sid(),
            source_profile=str(source),source_identity=original_identity,source_files=source_files,
            target_profile=str(destination),target_identity=target_identity,target_files=result,
            settings=dict(relative=str(Path(settings_path).relative_to(source)),facts=settings_facts,sha256=settings_sha256),
            catalog=dict(path=str(catalog_path),identity=catalog_identity))
        saved=_write_new(proof_path,json.dumps(proof,sort_keys=True).encode('utf8'))
    return result,dict(manifest=str(proof_path),sha256=saved['sha256']),dict(path=str(source),identity=original_identity,
        role='profile',provenance='retained-profile-v1',files=source_files)


def commit_selection(plan, expected_plan_sha256, *, installation_id=None, storage_relocation=None,
                     process_name='Books Arranger.exe',require_package=False,retained_package=None,control_namespace=None):
    """Final install commit only. No catalog migration or schema initialization."""
    raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode('utf8')
    _need(hashlib.sha256(raw).hexdigest()==expected_plan_sha256 and
          plan.get('schema')=='books-installation-selection-v1','selection_changed')
    app,profile=_absolute(plan['application_dir']),_absolute(plan['profile_dir'])
    _need(profile.parent==app.parent and profile!=app,'invalid_installation_layout',profile)
    root=app.parent;bootstrap=root/BOOTSTRAP
    _local(root)
    status=process_check([app],process_name)
    _need(status['state']=='available','in_use')
    chosen=plan['selection'];mode=chosen['mode']
    discovered=chosen.get('storage_relocation')
    _need(storage_relocation is None or discovered is None or storage_relocation==discovered,'invalid_relocation_selection')
    storage_relocation=storage_relocation or discovered
    previous=plan.get('previous_bootstrap')
    maintenance_review=_maintenance_selection(app,profile,_absolute(chosen['data_dir']),
        previous['value'] if previous else None)
    selected_maintenance=plan.get('maintenance_selection')
    _need(isinstance(selected_maintenance,dict) and selected_maintenance.get('path')==maintenance_review['path'] and
          selected_maintenance.get('previously_bound')==maintenance_review['previously_bound'] and
          (not maintenance_review['previously_bound'] or selected_maintenance.get('identity')==maintenance_review['identity']),
          'selection_changed')
    if bootstrap.exists():
        existing,existingfacts,existinghash=_json(bootstrap,65536)
        _need(previous and existingfacts==previous['facts'] and existinghash==previous['sha256'] and
              existing==previous['value'],'selection_changed',bootstrap)
        if (existing.get('data_dir')==chosen['data_dir'] and existing.get('profile_dir')==str(profile) and mode=='existing'):
            check=inspect_existing(chosen['database'])
            _need(check['state']=='available' and check['facts']==chosen['database_facts'],'selection_changed',chosen['database'])
            if existing.get('storage_relocation')==storage_relocation and not require_package and existing.get('maintenance_temp_dir'):
                return {'ok':True,'bootstrap':str(bootstrap),'result':'existing_selection_kept','database':chosen['database']}
            from catalog_owner import catalog_lock
            with catalog_lock(chosen['database'],{}):
                with VerifiedFile(chosen['database']) as held:
                    _need(held.facts()==chosen['database_facts'],'selection_changed',chosen['database'])
                changed=dict(existing)
                changed['maintenance_temp_dir'],changed['maintenance_temp_identity']=_commit_maintenance(plan['maintenance_selection'])
                if require_package:changed['package_ownership']=capture_current_package(str(app),existing['installation_id'])
                if retained_package:changed=_attach_retained_package(changed,retained_package)
                if storage_relocation:changed['storage_relocation']=storage_relocation
                else:changed.pop('storage_relocation',None)
                backup_name=bootstrap.with_name('books-arranger-installation.previous-'+str(uuid.uuid4())+'.json')
                changed=_seal_install_controls(changed,control_namespace,previous,backup_name)
                backup=_replace_bootstrap(bootstrap,json.dumps(changed,sort_keys=True).encode('utf8'),previous,backup_path=backup_name)
            return {'ok':True,'bootstrap':str(bootstrap),'result':'selection_updated','database':chosen['database'],
                    'previous_bootstrap':backup,'settings_preserved':True,'ownership_manifest':existing['ownership_manifest']}
    else:_need(previous is None,'selection_changed',bootstrap)
    journal=root/'books-arranger-selection-in-progress.json'
    # A power loss can leave a partially copied Chromium profile. Its presence
    # must never be treated as fresh, empty, or a successful preserved profile.
    # Immutable intent survives for explicit recovery; no recursive rollback.
    _need(not journal.exists() or previous is not None,'installation_commit_incomplete',journal)
    installation_id=installation_id or (previous['value']['installation_id'] if previous else str(uuid.uuid4()))
    _need(str(uuid.UUID(installation_id))==installation_id,'invalid_installation_id')
    dirs={'profile_dir':profile,'temp_dir':root/'Temp','downloads_dir':root/'Downloads','logs_dir':root/'Logs'}
    prior_roots=[]
    if previous:
        prior,_,_=_json(previous['value']['ownership_manifest'])
        _need(prior.get('schema')==OWNERSHIP_SCHEMA and prior.get('installation_id')==installation_id,'ownership_not_confirmed')
        prior_roots=prior['roots']
    for key,path in dirs.items():
        _local(path)
        if path.exists() and any(path.iterdir()):
            prior=next((r for r in prior_roots if _absolute(r['path'])==path),None)
            _need(key!='profile_dir' and prior is not None,'new_managed_folder_not_empty',path)
            with DirectoryBoundary(path.anchor,path) as held:
                _need(list(held.identities[-1][1:])==prior['identity'],'selection_changed',path)
    if mode=='existing':
        again=inspect_existing(chosen['database'],config_paths=[chosen['profile_settings_path']] if chosen.get('profile_settings_path') else ())
        _need(again['state']=='available' and again['facts']==chosen['database_facts'] and
              again['resolved_path']==chosen['resolved_database'],'selection_changed',chosen['database'])
    else:
        old_ancestor=_absolute(chosen['ancestor'])
        with DirectoryBoundary(old_ancestor.anchor,old_ancestor) as held:
            _need(list(held.identities[-1][1:])==chosen['ancestor_identity'],'selection_changed',old_ancestor)
        again=inspect_new(chosen['data_dir'])
        _need(again['existing']==chosen['existing'],'selection_changed',chosen['data_dir'])
    from catalog_owner import catalog_lock
    with contextlib.ExitStack() as stack:
        if mode=='existing':
            stack.enter_context(catalog_lock(chosen['database'],{}))
            with VerifiedFile(chosen['database']) as selected:
                _need(selected.facts()==chosen['database_facts'],'selection_changed',chosen['database'])
        else:
            data=_absolute(chosen['data_dir'])
            with DirectoryBoundary(data.anchor,data,create=True):pass
        if previous is None:
            _write_new(journal,json.dumps(dict(schema='books-installation-selection-intent-v1',
                plan_sha256=expected_plan_sha256,installation_id=installation_id,
                application_dir=str(app),profile_dir=str(profile),data_dir=chosen['data_dir']),sort_keys=True).encode('utf8'))
        for path in dirs.values():
            with DirectoryBoundary(path.anchor,path,create=True):pass
        maintenance,maintenance_identity=_commit_maintenance(plan['maintenance_selection'])
        copied=[];retained_profile=None;retained_profile_root=None
        if chosen.get('profile_confirmed'):
            copied,retained_profile,retained_profile_root=_copy_profile(chosen['associated_profile'],profile,chosen['profile_settings_path'],
                chosen['profile_settings_facts'],chosen['profile_settings_sha256'],root/('books-retained-profile-'+str(uuid.uuid4())+'.json'),
                chosen['database_facts']['identity'],chosen.get('profile_source_authority'))
        # Selected DB is explicit, so preserved old profile cannot silently point
        # a new installation at a different catalog. If old settings differ, stop.
        settings=profile/'desktop-settings.json'
        if settings.exists():
            old,_,_=_json(settings,16384)
            if _absolute(old.get('dataDir',''))!=_absolute(chosen['data_dir']):
                with VerifiedFile(_absolute(old.get('dataDir',''))/'inventory.sqlite3') as kept,VerifiedFile(chosen['database']) as selected:
                    _need(kept.facts()['identity']==selected.facts()['identity'],'copied_settings_selection_differs',settings)
        elif mode=='existing':
            item=_write_new(settings,json.dumps({'dataDir':chosen['data_dir'],'catalogMode':mode}).encode('utf8'))
            copied.append(dict(relative=settings.name,**item))
        owned=[]
        for key,path in dirs.items():
            with DirectoryBoundary(path.anchor,path) as held:identity=list(held.identities[-1][1:])
            prior=next((r for r in prior_roots if _absolute(r['path'])==path),None)
            owned.append(dict(path=str(path),identity=identity,role={'profile_dir':'profile','temp_dir':'work',
                'downloads_dir':'downloads','logs_dir':'logs'}[key],files=copied if key=='profile_dir' else prior['files'] if prior else [],
                provenance={'profile_dir':'created-profile-v1','temp_dir':'created-temp-v1','downloads_dir':'created-updater-v1',
                            'logs_dir':'created-logs-v1'}[key]))
        if mode=='new':
            data=_absolute(chosen['data_dir'])
            with DirectoryBoundary(data.anchor,data) as held:identity=list(held.identities[-1][1:])
            owned.append(dict(path=str(data),identity=identity,role='database',files=[],provenance='created-data-v1'))
        else:
            data=_absolute(chosen['data_dir'])
            with DirectoryBoundary(data.anchor,data) as held:identity=list(held.identities[-1][1:])
            owned.append(dict(path=str(data),identity=identity,role='database',files=[],provenance='recognized-catalog-v1',
                              catalog_identity=chosen['database_facts']['identity']))
        current_paths={_absolute(r['path']) for r in owned}
        if retained_profile_root and _absolute(retained_profile_root['path']) not in current_paths:
            owned.append(retained_profile_root);current_paths.add(_absolute(retained_profile_root['path']))
        owned.extend(r for r in prior_roots if _absolute(r['path']) not in current_paths)
        if retained_package:
            receipt,_,receipt_sha=_json(retained_package['manifest'])
            _need(receipt_sha==retained_package['sha256'] and receipt.get('schema')=='books-legacy-package-retirement-v1' and
                receipt.get('state')=='original-retained','legacy_retention_unverified')
            kept=_absolute(receipt['retained_application'])
            with DirectoryBoundary(kept.anchor,kept) as held:_need(list(held.identities[-1][1:])==receipt['root_identity'],'legacy_retention_unverified')
            for entry in receipt['files']:
                with VerifiedFile(kept/entry['relative']) as held:
                    _need(held.facts()==entry['facts'] and held.sha256()==entry['sha256'],'legacy_retention_unverified')
            owned.append(dict(path=str(kept),identity=receipt['root_identity'],role='backups',files=receipt['files']))
        ownership=root/('books-arranger-owned-'+str(uuid.uuid4())+'.json')
        ownerbytes=json.dumps(dict(schema=OWNERSHIP_SCHEMA,installation_id=installation_id,application_dir=str(app),roots=owned),sort_keys=True).encode('utf8')
        producer=_write_new(ownership,ownerbytes)
        value=dict(schema='books-arranger-installation-v1',installation_id=installation_id,
                   application_dir=str(app),data_dir=chosen['data_dir'],catalog_mode=mode,
                   ownership_manifest=str(ownership),maintenance_temp_dir=maintenance,
                   maintenance_temp_identity=maintenance_identity,**{key:str(path) for key,path in dirs.items()})
        value['ownership_provenance']=dict(manifest=str(ownership),sha256=producer['sha256'])
        if retained_profile:value['retained_profile']=retained_profile
        if storage_relocation is not None:
            _need(isinstance(storage_relocation,dict) and set(storage_relocation)=={'manifest','sha256'},'invalid_relocation_selection')
            from storage_relocation import parse_manifest
            descriptor,_,descriptor_digest=_json(storage_relocation['manifest'],64*1024*1024)
            _need(descriptor_digest==storage_relocation['sha256'],'invalid_relocation_selection')
            # Pure validation only: runtime/operator still require activation.
            parse_manifest(Path(storage_relocation['manifest']).read_bytes(),storage_relocation['sha256'])
            value['storage_relocation']=storage_relocation
        if require_package:value['package_ownership']=capture_current_package(str(app),installation_id)
        if retained_package:value['retained_package']=retained_package
        backup_name=bootstrap.with_name('books-arranger-installation.previous-'+str(uuid.uuid4())+'.json') if previous else None
        value=_seal_install_controls(value,control_namespace,previous,backup_name)
        output=json.dumps(value,sort_keys=True).encode('utf8')
        backup=_replace_bootstrap(bootstrap,output,previous,backup_path=backup_name) if previous else None
        if not previous:_write_new(bootstrap,output)
    return {'ok':True,'bootstrap':str(bootstrap),'result':'selection_committed','database':chosen['database'],
            'settings_preserved':bool(chosen.get('profile_confirmed')),'ownership_manifest':str(ownership),'previous_bootstrap':backup}


def _protected_paths(extra=()):
    from scanner import DEFAULT_ROOTS
    roots=[*DEFAULT_ROOTS.values(),*extra]
    for config in known_configurations():
        source=Path(config).parent/'audiobook-sources.json'
        if not source.exists():continue
        value,_,_=_json(source,16384)
        _need(isinstance(value,dict) and set(value)<={'audiobook_sources','audiobook_output_root'},'installation_reference_unchecked',source)
        configured=value.get('audiobook_sources',[])
        _need(isinstance(configured,list) and len(configured)<=32,'installation_reference_unchecked',source)
        roots.extend(configured)
        if value.get('audiobook_output_root'):roots.append(value['audiobook_output_root'])
    return tuple(str(_absolute(str(p))) for p in roots)


def _catalog_library_roots(roots):
    found=[]
    for root in roots:
        if root.get('role')!='database':continue
        database=_absolute(root['path'])/'inventory.sqlite3'
        if not database.exists():continue
        from storage_lifecycle_snapshot import frozen_connection
        with frozen_connection(database) as db:
            db.execute('PRAGMA query_only=ON');db.execute('PRAGMA temp_store=MEMORY')
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ('jobs','files'):
                if table not in tables:continue
                for row in db.execute('SELECT DISTINCT root FROM '+table):
                    _need(len(found)<=128,'installation_reference_unchecked',database)
                    if isinstance(row[0],str) and Path(row[0]).is_absolute():found.append(row[0])
    return found


def registered_bootstraps():
    """Bounded read-only per-user registrations; never executes registry text."""
    if os.name != 'nt':
        return []
    import winreg
    found = set()
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r'Software\Microsoft\Windows\CurrentVersion\Uninstall',
                               0, winreg.KEY_READ | view) as root:
                count = winreg.QueryInfoKey(root)[0]
                _need(count <= 2048, 'registration_scan_bound_exceeded')
                for index in range(count):
                    with winreg.OpenKey(root, winreg.EnumKey(root, index)) as key:
                        try:
                            name = winreg.QueryValueEx(key, 'DisplayName')[0]
                            location = winreg.QueryValueEx(key, 'InstallLocation')[0]
                        except FileNotFoundError:
                            continue
                        if isinstance(name,str) and (name=='Books Arranger' or
                            re.fullmatch(r'Books Arranger \d+\.\d+\.\d+',name)) and isinstance(location,str):
                            found.add(str(_absolute(location).parent / BOOTSTRAP))
        except FileNotFoundError:
            continue
    return sorted(found)


def _other_installation_paths(installation_id,application_dir=None):
    protected = []
    for path in registered_bootstraps():
        if not Path(path).exists():
            continue
        value, _, _ = _json(path, 65536)
        _need(value.get('schema') == 'books-arranger-installation-v1', 'installation_reference_unchecked', path)
        same=(value.get('installation_id')==installation_id and application_dir is not None and
              os.path.normcase(str(_absolute(value['application_dir'])))==os.path.normcase(str(_absolute(application_dir))))
        if not same:
            for key in ('application_dir', 'data_dir', 'profile_dir', 'temp_dir', 'downloads_dir', 'logs_dir','maintenance_temp_dir'):
                if value.get(key):protected.append(str(_absolute(value[key])))
    return protected


def _physical(path):
    """Resolve only for exclusion/dedup, never to grant deletion authority."""
    return str(_absolute(str(path)).resolve(strict=True))


def plan_cleanup(ownership_path, expected_sha256, *, selected_roots, protected_paths=(),bootstrap_paths=()):
    manifest, _, digest = _json(ownership_path)
    _need(digest == expected_sha256, 'ownership_changed', ownership_path)
    _need(isinstance(manifest, dict) and {'schema','installation_id','roots'}<=set(manifest) and
          set(manifest)<={'schema','installation_id','application_dir','roots','producer'} and
          manifest['schema'] == OWNERSHIP_SCHEMA, 'ownership_not_confirmed', ownership_path)
    _need(str(uuid.UUID(manifest['installation_id'])) == manifest['installation_id'], 'ownership_not_confirmed')
    roots = manifest['roots']; selected = {_absolute(str(p)) for p in selected_roots}
    _need(isinstance(roots, list) and len(roots) <= 32 and selected, 'invalid_cleanup_selection')
    protected = _protected_paths((*protected_paths, *_other_installation_paths(manifest['installation_id'],manifest.get('application_dir')),
                                  *_catalog_library_roots(roots)))
    actual_protected = []
    for path in protected:
        try:
            # Network library roots cannot alias a local fixed-volume state
            # target. Keep their lexical exclusion without contacting the NAS.
            _local(_absolute(path))
            actual_protected.append(_physical(path))
        except LifecycleRefused:pass
        except FileNotFoundError:pass
    targets, count = [], 0
    root_identities=set();file_identities=set()
    known = set()
    for root in roots:
        _need(isinstance(root, dict) and {'path', 'identity', 'role', 'files'} <= set(root) and
              set(root) <= {'path','identity','role','files','provenance','catalog_identity','directories'}, 'ownership_not_confirmed')
        path = _absolute(root['path']); known.add(path)
        if path not in selected:
            continue
        from storage_state_ownership import validate_cleanup_root
        try:
            validate_cleanup_root(manifest,root,bootstrap_paths=list(bootstrap_paths) or registered_bootstraps(),
                ownership_path=str(ownership_path),ownership_sha256=expected_sha256)
        except ValueError as error:raise LifecycleRefused('ownership_not_confirmed',path) from error
        _local(path); physical = _physical(path)
        _need(root['role'] in {'application','database', 'profile', 'work', 'recovery', 'cache', 'downloads', 'logs', 'backups'},
              'ownership_not_confirmed', path)
        _need(not any(_under(path, _absolute(p)) or _under(_absolute(p), path) for p in protected), 'protected_location', path)
        _need(not any(_under(Path(physical), Path(p)) or _under(Path(p), Path(physical)) for p in actual_protected),
              'protected_alias', path)
        # A root inside a Git checkout needs exact files; this never selects
        # .git/source or recursively broadens to the containing checkout.
        with DirectoryBoundary(path.anchor, path) as boundary:
            _need(list(boundary.identities[-1][1:]) == root['identity'], 'changed_since_review', path)
        _need(tuple(root['identity']) not in root_identities,'duplicate_cleanup_alias',path)
        root_identities.add(tuple(root['identity']))
        files = root['files']; _need(isinstance(files, list), 'ownership_not_confirmed', path)
        count += len(files); _need(count <= MAX_OWNED_FILES, 'cleanup_bound_exceeded')
        entries, seen = [], set();permitted_directories={path}
        for item in root.get('directories',[]):
            _need(isinstance(item,dict) and set(item)=={'relative','identity'},'ownership_not_confirmed',path)
            relative=item['relative'];_need(isinstance(relative,str) and relative and ':' not in relative and
                not Path(relative).is_absolute() and all(p not in ('','.','..','.git') for p in relative.replace('\\','/').split('/')),
                'ownership_not_confirmed',path)
            directory=path/relative
            with DirectoryBoundary(directory.anchor,directory) as held:
                _need(list(held.identities[-1][1:])==item['identity'],'changed_since_review',directory)
            permitted_directories.add(directory)
        for item in files:
            _need(isinstance(item, dict) and set(item) == {'relative', 'facts', 'sha256'}, 'ownership_not_confirmed', path)
            rel = item['relative']
            _need(isinstance(rel, str) and rel and not Path(rel).is_absolute() and ':' not in rel and
                  all(p not in ('', '.', '..', '.git') for p in rel.replace('\\', '/').split('/')),
                  'ownership_not_confirmed', path)
            file = path / rel; key = os.path.normcase(str(file))
            _need(key not in seen, 'duplicate_cleanup_target', file); seen.add(key)
            parent=file.parent
            while _under(parent,path):
                permitted_directories.add(parent)
                if parent==path:break
                parent=parent.parent
            with DirectoryBoundary(file.anchor, file.parent), VerifiedFile(file) as held:
                facts = held.facts(); single_stream(file)
                _need(facts == item['facts'] and facts['links'] == 1 and held.sha256() == item['sha256'],
                      'changed_since_review', file)
                _need(tuple(facts['identity']) not in file_identities,'duplicate_cleanup_alias',file)
                file_identities.add(tuple(facts['identity']))
                entries.append(dict(path=str(file), facts=facts, sha256=item['sha256']))
        # Unknown children are visible blockers, not permission to recursively
        # delete them. Empty subdirectories are retained unless explicitly owned.
        found = set()
        walked = 0
        for folder, dirs, names in os.walk(path, followlinks=False):
            walked += len(dirs) + len(names)
            _need(walked <= MAX_OWNED_FILES, 'cleanup_bound_exceeded', path)
            for name in dirs:
                entry = Path(folder) / name
                _need(not entry.is_symlink() and not os.path.isjunction(entry) and name != '.git', 'ownership_not_confirmed', entry)
                _need(entry in permitted_directories,'ownership_not_confirmed',entry)
            for name in names:found.add(os.path.normcase(str(Path(folder) / name)))
        _need(found == seen, 'ownership_not_confirmed', path)
        directories=[]
        for directory in sorted(permitted_directories,key=lambda p:(-len(p.parts),str(p))):
            with DirectoryBoundary(directory.anchor,directory) as held:
                directories.append(dict(path=str(directory),identity=list(held.identities[-1][1:])))
        content_roles={root['role']}
        for entry in entries:
            relative=str(Path(entry['path']).relative_to(path)).replace('\\','/')
            if relative.startswith(('source-recovery/','replacement-recovery/')):content_roles.add('recovery')
            if relative.startswith(('merge-cache/audio-staging/','chapter-repairs/')):content_roles.add('work')
            if relative.startswith(('merge-cache/covers/','openlibrary-index/')):content_roles.add('cache')
        targets.append(dict(path=str(path), resolved_path=physical, identity=root['identity'], role=root['role'], files=entries,
                            directories=directories,content_roles=sorted(content_roles)))
    _need(selected <= known and len(targets) == len(selected), 'ownership_not_confirmed')
    selected_roles={role for target in targets for role in target['content_roles']}
    phrases={'database':'databases and job history','profile':'settings and credentials','work':'work files',
             'recovery':'recovery copies','cache':'caches and downloads','downloads':'caches and downloads','logs':'logs','backups':'backups'}
    phrases['application']='application binaries'
    selected_phrases=sorted({phrases[r] for r in selected_roles})
    warning='This deletes the selected '+', '.join(selected_phrases)+'.'
    if 'recovery' in selected_roles:warning+=' Selected recovery copies of original audio will also be deleted.'
    return {'schema': PLAN_SCHEMA, 'installation_id': manifest['installation_id'], 'ownership_path': str(_absolute(str(ownership_path))),
            'ownership_sha256': digest, 'targets': targets,
            'bootstrap_paths':list(map(str,bootstrap_paths)),
            'bytes': sum(item['facts']['size'] for target in targets for item in target['files']),'warning':warning}


def execute_cleanup(plan, expected_plan_sha256, *, protected_paths=()):
    raw = json.dumps(plan, sort_keys=True, separators=(',', ':')).encode('utf-8')
    _need(hashlib.sha256(raw).hexdigest() == expected_plan_sha256 and plan.get('schema') == PLAN_SCHEMA,
          'cleanup_plan_changed')
    current = plan_cleanup(plan['ownership_path'], plan['ownership_sha256'],
                           selected_roots=[t['path'] for t in plan['targets']], protected_paths=protected_paths,
                           bootstrap_paths=plan.get('bootstrap_paths',()))
    _need(current == plan, 'changed_since_review')
    removed, removed_bytes,removed_directories = [], 0,[]
    failure=None
    ownership,_,_=_json(plan['ownership_path'])
    control=(_absolute(ownership['application_dir']).parent if ownership.get('application_dir') else
        _absolute(plan['ownership_path']).parent)/'CleanupReceipts'
    _need(not any(_under(control,_absolute(t['path'])) for t in plan['targets']),'cleanup_receipt_inside_selected_scope',control)
    with DirectoryBoundary(control.anchor,control,create=True):pass
    try:
        with contextlib.ExitStack() as stack:
            prepared = []
            # ALL entries are retained and revalidated before the first disposition.
            for target in plan['targets']:
                for item in target['files']:
                    path = Path(item['path'])
                    boundary = stack.enter_context(DirectoryBoundary(path.anchor, path.parent))
                    handle = stack.enter_context(VerifiedFile(path, delete=True))
                    single_stream(path)
                    _need(handle.facts() == item['facts'] and handle.sha256() == item['sha256'], 'changed_since_review', path)
                    prepared.append((path, boundary, handle, item['facts']['size']))
            from lifecycle_file_cleanup import dispose_owned_file
            for path, boundary, handle, size in prepared:
                boundary.revalidate();facts=handle.facts();sha=handle.sha256()
                handle.__exit__(None,None,None)
                result=dispose_owned_file(path,facts,sha,receipt_path=control/('file-'+str(uuid.uuid4())+'.json'))
                _need(result.get('removed') is True,'cleanup_incomplete',path)
                removed.append(str(path));removed_bytes+=size
        for target in plan['targets']:
            for item in target['directories']:
                path=Path(item['path'])
                with DirectoryBoundary(path.anchor,path.parent) as boundary:
                    with VerifiedDirectory(path,delete=True) as directory:
                        _need(directory.facts()['identity']==item['identity'],'changed_since_review',path)
                    boundary.revalidate()
                    from lifecycle_directory_cleanup import dispose_owned_empty_directory
                    result=dispose_owned_empty_directory(path,item['identity'],receipt_path=control/('directory-'+str(uuid.uuid4())+'.json'))
                    _need(result.get('removed') is True,'cleanup_incomplete',path)
                _need(not os.path.lexists(path),'cleanup_incomplete',path)
                removed_directories.append(str(path))
    except (OSError,ValueError) as error:
        if not removed:raise
        failure=getattr(error,'code','cleanup_incomplete')
    leftovers = [path for path in removed if os.path.lexists(path)]
    _need(not leftovers, 'cleanup_incomplete', leftovers[0] if leftovers else '')
    return {'ok': failure is None, 'removed_files': len(removed), 'removed_bytes': removed_bytes,
            'removed_directories':removed_directories,
            'retained_directories': [t['path'] for t in plan['targets'] if os.path.lexists(t['path'])],
            'result': 'selected_data_removed' if failure is None else 'partial_cleanup',
            'code':failure or 'ok','remaining_files':[item['path'] for t in plan['targets'] for item in t['files'] if os.path.lexists(item['path'])]}


_LEVELDB=re.compile(r'(?:CURRENT|LOCK|LOG(?:\.old)?|MANIFEST-\d{6,}|\d{6,}\.(?:log|ldb))')
_CACHE=re.compile(r'(?:index|data_[0-9]+|f_[a-f0-9]{6,}|[a-f0-9]{16}_[0-9]+|the-real-index)')
_UUID=r'[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}'


def _runtime_name(provenance, relative):
    """Finite generated-name classes under a native-proven private created root."""
    parts=relative.replace('\\','/').split('/');name=parts[-1]
    if provenance in {'created-profile-v1','retained-profile-v1'}:
        fixed={'.updaterId','audiobook-sources.json','desktop-settings.json','last-load.json','last-load.json.tmp','Local State',
               'Preferences','Secure Preferences','lockfile','DIPS','declarative_performance_observer.db'}
        if len(parts)==1 and (name in fixed or any(name==base+suffix for base in ('DIPS','declarative_performance_observer.db')
                                                 for suffix in ('-wal','-shm','-journal'))):return True
        if len(parts)==3 and parts[:2]==['Local Storage','leveldb'] and _LEVELDB.fullmatch(name):return True
        if len(parts)==2 and parts[0]=='Session Storage' and _LEVELDB.fullmatch(name):return True
        if len(parts)>=2 and parts[0] in {'Cache','Code Cache','GPUCache','DawnGraphiteCache','DawnWebGPUCache',
                                        'GrShaderCache','GraphiteDawnCache','ShaderCache','WebGPUCache'}:
            allowed={'Cache_Data','js','wasm','index-dir'}
            return all(p in allowed for p in parts[1:-1]) and bool(_CACHE.fullmatch(name))
        if len(parts)==2 and parts[0]=='Network':
            names={'Cookies','Network Persistent State','TransportSecurity','Trust Tokens','Reporting and NEL'}
            return name in names or any(name==base+suffix for base in names for suffix in ('-wal','-shm','-journal'))
        if len(parts)==3 and parts[0]=='IndexedDB' and re.fullmatch(r'https?_127\.0\.0\.1_\d+\.indexeddb\.leveldb',parts[1]):
            return bool(_LEVELDB.fullmatch(name))
        if len(parts)==3 and parts[0]=='blob_storage' and re.fullmatch(_UUID,parts[1]) and re.fullmatch(_UUID,name):return True
        return False
    if provenance=='created-temp-v1':
        return len(parts)==1 and bool(re.fullmatch(r'etilqs_[A-Za-z0-9]+|\.org\.chromium\.Chromium\.[A-Za-z0-9_-]+|books-[a-f0-9]{32}\.(?:tmp|log)',name))
    if provenance=='created-updater-v1':
        if parts[0]=='books-arranger-updater':parts=parts[1:]
        return (len(parts)==1 and name in {'installer.exe','current.blockmap'} or len(parts)==2 and parts[0]=='pending' and
                (name in {'update-info.json','installer.exe','package.7z'} or
                 re.fullmatch(r'Books-Arranger-Setup-\d+\.\d+\.\d+\.exe(?:\.blockmap)?',name)))
    if provenance=='created-logs-v1':
        return (len(parts)==1 and bool(re.fullmatch(r'books-(?:app|backend|worker|update)(?:-[0-9T_-]+)?\.log',name)) or
                len(parts)==2 and parts[0]=='CrashDumps' and bool(re.fullmatch(_UUID+r'\.(?:dmp|json)',name)))
    return False


def _runtime_directory(provenance,relative):
    parts=relative.replace('\\','/').split('/')
    if provenance in {'created-profile-v1','retained-profile-v1'}:
        if parts[0] in {'Cache','Code Cache','GPUCache','DawnGraphiteCache','DawnWebGPUCache',
                        'GrShaderCache','GraphiteDawnCache','ShaderCache','WebGPUCache'}:
            return all(p in {'Cache_Data','js','wasm','index-dir'} for p in parts[1:])
        if parts in (['Local Storage'],['Local Storage','leveldb'],['Session Storage'],['Network'],['IndexedDB'],['blob_storage']):return True
        if len(parts)==2 and parts[0]=='blob_storage' and re.fullmatch(_UUID,parts[1]):return True
        if len(parts)==2 and parts[0]=='IndexedDB' and re.fullmatch(r'https?_127\.0\.0\.1_\d+\.indexeddb\.leveldb',parts[1]):return True
    if provenance=='created-updater-v1':return parts in (['books-arranger-updater'],['books-arranger-updater','pending'],['pending'])
    if provenance=='created-logs-v1':return parts==['CrashDumps']
    if provenance=='created-temp-v1':return len(parts)==1 and bool(re.fullmatch(r'scoped_dir\d+_\d+|\.org\.chromium\.Chromium\.[A-Za-z0-9_-]+',parts[0]))
    return False


def _catalog_ownership(root, catalog_identity=None):
    """Use the same typed catalog graph as relocation and cleanup admission."""
    from storage_lifecycle_snapshot import frozen_catalog
    from storage_state_ownership import catalog_state_membership
    from storage_relocation_operator import classify_historical_files
    from storage_relocation import _key
    database=root/'inventory.sqlite3'
    try:
        with VerifiedFile(database) as held:
            if catalog_identity is not None:
                _need(held.facts()['identity']==catalog_identity,'ownership_not_confirmed',database)
            with frozen_catalog(database) as snapshot:
                with contextlib.closing(sqlite3.connect(snapshot.as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
                    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    _need({'jobs','queue','files'}<=tables,'unsupported_database',database)
                    for table,where in (('audio_jobs',"state='running'"),
                                        ('working_attempts',"COALESCE(producer,'')!='closed' AND state NOT IN ('retired')"),
                                        ('inplace_edits',"state NOT IN ('published','rolled_back')")):
                        if table in tables:
                            _need(not db.execute('SELECT 1 FROM '+table+' WHERE '+where+' LIMIT 1').fetchone(),
                                  'work_closure_unconfirmed',database)
                membership=catalog_state_membership(snapshot,logical_root=root,physical_root=root,immutable=True)
                classes,holds=classify_historical_files(snapshot,managed_root=str(root.parent),
                    logical_catalog=database,index_root=root/'openlibrary-index',immutable=True)
                _need(not holds,'work_closure_unconfirmed',database)
    except RuntimeError as error:
        # The support-disposition context annotates failures with its recovery
        # location. Translate only an underlying typed refusal into a UI hold;
        # unrelated native/snapshot errors are never treated as owned content.
        from storage_relocation import RelocationRefused
        cause=error.__cause__
        while cause is not None:
            if isinstance(cause,LifecycleRefused):raise cause from error
            if isinstance(cause,RelocationRefused):
                raise LifecycleRefused('work_closure_unconfirmed',str(database)) from error
            cause=cause.__cause__
        raise
    # Membership keys are normalized for Windows identity matching. Return actual
    # spellings from this finite physical census, never an extension allowlist.
    owned={};markers=set();index=set()
    for path,kinds in classes.items():
        if not set(kinds)&{'index-leaf','index-journal'}:continue
        index.add(_key(path))
        if 'index-leaf' in kinds:
            leaf=Path(path);owner=leaf.name.replace('index-','pending-',1) if leaf.name.startswith('index-') else leaf.name
            index.add(_key(str(leaf.with_name(owner+'.owner.json'))))
            if leaf.name.startswith('index-'):index.add(_key(path+'.complete.json'))
    for folder,_,names in os.walk(root,followlinks=False):
        for name in names:
            path=Path(folder)/name;key=_key(str(path))
            if key in membership['owned']:owned[str(path)]=membership['owned'][key]
            elif key in membership['markers'] or key in index:markers.add(str(path))
            elif path==root/'openlibrary-index/import-lock.sqlite3.lock':
                with VerifiedFile(path) as held:
                    single_stream(path)
                    _need(held.facts()['links']==1 and held.facts()['size'] in (0,1) and
                        held.sha256() in {hashlib.sha256(b'').hexdigest(),hashlib.sha256(b'0').hexdigest()},
                        'ownership_not_confirmed',path)
                markers.add(str(path))
    return owned,markers,membership['directories']


def refresh_ownership(ownership_path, expected_sha256, *, output_path,bootstrap_path=None):
    """NEW exact review snapshot after closure; never rewrites old provenance."""
    manifest,_,digest=_json(ownership_path);_need(digest==expected_sha256,'ownership_changed',ownership_path)
    _need(manifest.get('schema')==OWNERSHIP_SCHEMA,'ownership_not_confirmed',ownership_path)
    roots=[];blockers={}
    for original in manifest['roots']:
        root=dict(original);provenance=root.get('provenance');path=_absolute(root['path'])
        if provenance is None:
            roots.append(root);continue
        try:
            with contextlib.ExitStack() as stack:
                boundary=stack.enter_context(DirectoryBoundary(path.anchor,path))
                _need(list(boundary.identities[-1][1:])==root['identity'],'ownership_not_confirmed',path)
                if provenance=='created-data-v1' and not (path/'inventory.sqlite3').exists():
                    _need(not any(path.iterdir()),'ownership_not_confirmed',path)
                    graph,markers,known_dirs={},set(),set()
                else:
                    graph,markers,known_dirs= _catalog_ownership(path,root.get('catalog_identity')) if provenance in ('created-data-v1','recognized-catalog-v1') else ({},set(),set())
                entries=[];directories=[];count=0
                for folder,dirs,names in os.walk(path,followlinks=False):
                    count+=len(dirs)+len(names);_need(count<=MAX_OWNED_FILES,'ownership_graph_bound_exceeded',path)
                    parent=Path(folder);stack.enter_context(DirectoryBoundary(parent.anchor,parent))
                    for name in dirs:
                        child=parent/name
                        _need(not child.is_symlink() and not os.path.isjunction(child) and name!='.git','ownership_not_confirmed',child)
                        relative=str(child.relative_to(path)).replace('\\','/')
                        _need(relative in known_dirs if provenance in ('created-data-v1','recognized-catalog-v1') else
                              _runtime_directory(provenance,relative),'ownership_not_confirmed',child)
                        with DirectoryBoundary(child.anchor,child) as held:
                            directories.append(dict(relative=relative,identity=list(held.identities[-1][1:])))
                    for name in names:
                        file=parent/name;relative=str(file.relative_to(path));expected=None
                        if provenance in ('created-data-v1','recognized-catalog-v1'):
                            fixed=parent==path and (name in {'inventory.sqlite3','inventory.sqlite3-wal','inventory.sqlite3-shm',
                                'inventory.sqlite3-journal','inventory.sqlite3.lock','web-instance.json'} or
                                re.fullmatch(r'web-instance\.(?:ended|stale|orphan)-[a-f0-9-]+\.json',name))
                            expected=graph.get(str(file))
                            _need(fixed or expected is not None or str(file) in markers,'ownership_not_confirmed',file)
                        else:_need(_runtime_name(provenance,relative),'ownership_not_confirmed',file)
                        handle=stack.enter_context(VerifiedFile(file));single_stream(file);facts=handle.facts();sha=handle.sha256()
                        _need(facts['links']==1,'ownership_not_confirmed',file)
                        if expected:_need(sha==expected[0] and (expected[1] is None or facts['size']==expected[1]),'ownership_not_confirmed',file)
                        entries.append(dict(relative=relative,facts=facts,sha256=sha))
                root['files']=entries
                root['directories']=directories
        except LifecycleRefused as error:blockers[str(path)]=error.code
        except BoundaryError as error:blockers[str(path)]='in_use' if getattr(error,'diagnostic',{}).get('windows_error')==32 else 'could_not_check'
        except (OSError,ValueError,sqlite3.Error):blockers[str(path)]='could_not_check'
        roots.append(root)
    refreshed=dict(manifest,roots=roots)
    if bootstrap_path:
        bootstrap,_,_=_json(bootstrap_path,65536);pin=bootstrap.get('ownership_provenance')
        _need(isinstance(pin,dict) and bootstrap.get('installation_id')==manifest['installation_id'],'ownership_not_confirmed')
        original,_,sha=_json(pin['manifest']);_need(sha==pin['sha256'] and original['installation_id']==manifest['installation_id'],'ownership_not_confirmed')
        refreshed['producer']=dict(bootstrap=str(bootstrap_path),manifest=pin['manifest'],sha256=pin['sha256'])
    raw=json.dumps(refreshed,sort_keys=True).encode('utf8')
    produced=_write_new(output_path,raw)
    return dict(ownership_path=str(_absolute(str(output_path))),ownership_sha256=produced['sha256'],blockers=blockers)


def verified_runtime_copy(bootstrap, runtime_path):
    """Read-only proof of the NSIS self-copy; grants no deletion authority."""
    from storage_relocation_operator import local_root
    runtime=local_root(runtime_path);maintenance=local_root(bootstrap['maintenance_temp_dir'])
    app=local_root(bootstrap['application_dir'])
    _need(runtime!=maintenance and _under(runtime,maintenance),'runtime_copy_unverified',runtime)
    with contextlib.ExitStack() as held:
        boundary=held.enter_context(DirectoryBoundary(maintenance.anchor,maintenance))
        _need(list(boundary.identities[-1][1:])==bootstrap['maintenance_temp_identity'],'runtime_copy_unverified',maintenance)
        held.enter_context(DirectoryBoundary(maintenance,runtime.parent))
        pin=bootstrap['package_ownership'];owner,_,digest=_json(pin['manifest'])
        _need(digest==pin['sha256'] and owner['installation_id']==bootstrap['installation_id'] and
              owner['application_dir']==str(app) and len(owner['roots'])==1,'runtime_copy_unverified',runtime)
        package=owner['roots'][0]
        application=held.enter_context(DirectoryBoundary(app.anchor,app))
        _need(package['path']==str(app) and package['role']=='application' and
              package['identity']==list(application.identities[-1][1:]),'runtime_copy_unverified',runtime)
        selected=[item for item in package['files'] if item['relative']=='Uninstall Books Arranger.exe']
        _need(len(selected)==1,'runtime_copy_unverified',runtime);expected=selected[0]
        source=held.enter_context(VerifiedFile(app/expected['relative']));single_stream(app/expected['relative'])
        _need(source.facts()==expected['facts'] and source.sha256()==expected['sha256'],'runtime_copy_unverified',runtime)
        copy=held.enter_context(VerifiedFile(runtime));single_stream(runtime);facts=copy.facts()
        _need(facts['links']==1 and facts['size']==expected['facts']['size'] and copy.sha256()==expected['sha256'],
              'runtime_copy_unverified',runtime)
        return dict(path=str(runtime),facts=facts,sha256=expected['sha256'],bytes=facts['size'],
            maintenance_path=str(maintenance),maintenance_identity=bootstrap['maintenance_temp_identity'],
            reason='Uninstaller program (kept)',verified=True)


def runtime_copy_row(bootstrap,runtime_path):
    try:
        proof=verified_runtime_copy(bootstrap,runtime_path)
        return dict(proof,role='maintenance-copy',content_roles=['maintenance-copy'],resolved_path=proof['path'],
            state='maintenance_copy_verified',can_remove=False,entry_type='file')
    except (OSError,ValueError,KeyError):
        return dict(path=str(runtime_path),resolved_path=str(runtime_path),role='maintenance-copy',content_roles=['maintenance-copy'],
            state='maintenance_copy_unverified',bytes=None,can_remove=False,entry_type='file',
            reason='Uninstaller program could not be verified. Kept for review.',verified=False)


def review_uninstall(bootstrap_path, *, output_dir=None,expected_application_dir=None,runtime_path=None):
    bootstrap,_,_=_json(bootstrap_path,65536)
    _need(bootstrap.get('schema')=='books-arranger-installation-v1','ownership_not_confirmed',bootstrap_path)
    from storage_lifecycle_controls import assert_no_pending_overlap
    assert_no_pending_overlap([bootstrap[k] for k in ('application_dir','data_dir','profile_dir','temp_dir','downloads_dir','logs_dir')],bootstrap['installation_id'])
    if expected_application_dir is not None:
        _need(os.path.normcase(str(_absolute(expected_application_dir)))==os.path.normcase(str(_absolute(bootstrap['application_dir']))),
            'installation_location_changed',bootstrap_path)
    manifest,_,digest=_json(bootstrap['ownership_manifest'])
    _need(manifest.get('installation_id')==bootstrap.get('installation_id'),'ownership_not_confirmed',bootstrap_path)
    ownership_path=bootstrap['ownership_manifest'];blockers={}
    if output_dir is not None:
        refreshed=refresh_ownership(ownership_path,digest,
            output_path=_absolute(str(output_dir))/('owned-review-'+str(uuid.uuid4())+'.json'),bootstrap_path=str(bootstrap_path))
        ownership_path,digest=refreshed['ownership_path'],refreshed['ownership_sha256'];blockers=refreshed['blockers']
        manifest,_,_=_json(ownership_path)
    rows=[]
    for root in manifest.get('roots',[]):
        path=root.get('path',''); row=dict(path=path,role=root.get('role',''),state='ownership_not_confirmed',bytes=None,can_remove=False)
        try:
            _need(path not in blockers,blockers.get(path,'ownership_not_confirmed'),path)
            plan=plan_cleanup(ownership_path,digest,selected_roots=[path],bootstrap_paths=[str(bootstrap_path)])
            row.update(state='available',bytes=plan['bytes'],can_remove=True,resolved_path=plan['targets'][0]['resolved_path'],
                       content_roles=plan['targets'][0]['content_roles'])
        except LifecycleRefused as error:row['state']=error.code
        except BoundaryError as error:
            row['state']='in_use' if getattr(error,'diagnostic',{}).get('windows_error')==32 else 'could_not_check'
        except (OSError,ValueError):row['state']='could_not_check'
        rows.append(row)
    if bootstrap.get('maintenance_temp_dir'):
        maintenance=_absolute(bootstrap['maintenance_temp_dir']);size=None;state='maintenance_reserved'
        try:
            with DirectoryBoundary(maintenance.anchor,maintenance) as held:
                _need(list(held.identities[-1][1:])==bootstrap.get('maintenance_temp_identity'),'ownership_not_confirmed',maintenance)
            from storage_lifecycle_controls import _census_display
            size=0 if not any(maintenance.iterdir()) else None
        except (OSError,ValueError):state='maintenance_unchecked'
        rows.append(dict(path=str(maintenance),resolved_path=str(maintenance),role='maintenance',content_roles=['maintenance'],
            state=state,bytes=size,can_remove=False,entry_type='folder',
            reason='Reserved maintenance parent used by this uninstaller. This parent is kept.'))
    if runtime_path:rows.append(runtime_copy_row(bootstrap,runtime_path))
    source_pin=None
    if bootstrap.get('storage_relocation') and output_dir is not None:
        config=bootstrap['storage_relocation']
        try:
            from storage_lifecycle_retirement import review_source_retirement
            source=review_source_retirement(config['manifest'],config['sha256'],
                protected_paths=[bootstrap['data_dir'],bootstrap['profile_dir']])
            if source.get('can_remove') is True:
                path=_absolute(str(output_dir))/('source-review-'+str(uuid.uuid4())+'.json')
                produced=_write_new(path,json.dumps(source,sort_keys=True).encode('utf8'))
                source_pin=dict(path=str(path),sha256=produced['sha256'])
            rows.append(dict(path=source['path'],resolved_path='; '.join(source['scope_paths']),
                role='retained-source',content_roles=['retained-source'],state=source.get('state','available'),bytes=source['bytes'],
                can_remove=source.get('can_remove') is True,group_id=source['group_id']))
        except (OSError,ValueError):
            rows.append(dict(path=config['manifest'],resolved_path='',role='retained-source',
                state='retained_source_unverified',bytes=None,can_remove=False))
    from storage_lifecycle_controls import review_control_records
    try:
        controls=review_control_records(bootstrap_path,other_bootstraps=registered_bootstraps())
        terminal_available=bool(bootstrap.get('package_ownership')) and not controls['holds'] and not any(r['required_by'] for r in controls['files'])
        for record in controls['files']:
            rows.append(dict(path=record['path'],resolved_path='; '.join(record['aliases']),role='records',
                content_roles=['records'],state=record['state'],bytes=record['bytes'],can_remove=False,
                reason=record['reason'],entry_type='file'))
        if terminal_available:
            # One explicit grouped row grants no independent file authority:
            # final planning still requires every dependent state root and the
            # exact package in the SAME native registry transaction.
            rows=[r for r in rows if r['path']!=str(bootstrap_path)]
            rows.append(dict(path=str(bootstrap_path),resolved_path='; '.join(r['path'] for r in controls['files']),
                role='records',content_roles=['records'],state='available',bytes=controls['bytes'],can_remove=True,
                reason='Remove installation records last. Select all dependent data locations; application binaries are included.',entry_type='group'))
        for record in controls['holds']:
            rows.append(dict(path=record['path'],resolved_path='; '.join(record.get('scope_paths',[])),role='records',
                content_roles=['records'],state=record['state'],bytes=record.get('bytes'),can_remove=False,
                reason=record['reason'],entry_type='folder' if record.get('kind')=='unconfirmed-control-folder' else 'file'))
    except (OSError,ValueError,sqlite3.Error) as error:
        controls=None
        rows.append(dict(path=str(bootstrap_path),resolved_path='',role='records',content_roles=['records'],
            state='control_record_unverified',bytes=None,can_remove=False,reason=str(error),entry_type='file'))
    return dict(schema='books-uninstall-review-v1',installation_id=bootstrap['installation_id'],source_pin=source_pin,controls=controls,
                authority_bootstrap=str(bootstrap_path),
                ownership_path=ownership_path,ownership_sha256=digest,targets=rows,
                database=str(Path(bootstrap['data_dir'])/'inventory.sqlite3'),profile_dir=bootstrap['profile_dir'])


def plan_selected_cleanup(ownership_path,ownership_sha256,selected_roots,source_pin=None,bootstrap_paths=(),runtime_path=None):
    for bootstrap_path in bootstrap_paths:
        if str(bootstrap_path) in selected_roots:
            from storage_lifecycle_controls import review_control_records,plan_control_retirement
            _need(len(bootstrap_paths)==1 and source_pin is None,'complete_control_cleanup_requires_separate_source_retirement')
            bootstrap,_,_=_json(bootstrap_path,65536)
            selected=[p for p in selected_roots if str(p)!=str(bootstrap_path)]
            ordinary=plan_cleanup(ownership_path,ownership_sha256,selected_roots=selected,bootstrap_paths=bootstrap_paths) if selected else None
            controls=plan_control_retirement(review_control_records(bootstrap_path,other_bootstraps=registered_bootstraps()),
                selected_state_roots=selected,application_will_be_removed=True)
            pin=bootstrap.get('package_ownership');_need(isinstance(pin,dict),'package_ownership_required')
            package=plan_cleanup(pin['manifest'],pin['sha256'],selected_roots=[bootstrap['application_dir']],bootstrap_paths=bootstrap_paths)
            selection=dict(schema='books-terminal-cleanup-selection-v1',installation_id=bootstrap['installation_id'],
                ordinary=ordinary,packages=[package],controls=controls,directories=controls['directories'])
            if runtime_path:selection['retained_runtime_copy']=runtime_copy_row(bootstrap,runtime_path)
            targets=(list(ordinary['targets']) if ordinary else [])+list(package['targets'])
            targets.append(dict(path=str(bootstrap_path),resolved_path='; '.join(r['path'] for r in controls['files'])))
            return dict(schema='books-lifecycle-terminal-cleanup-v1',selection=selection,targets=targets,
                bytes=(ordinary['bytes'] if ordinary else 0)+package['bytes']+controls['bytes'],
                warning='This permanently deletes the selected data, application binaries and listed installation records. Installation records are removed last.')
    source=None
    if source_pin:
        source,_,sha=_json(source_pin['path']);_need(sha==source_pin['sha256'],'cleanup_plan_changed')
    selected=list(selected_roots)
    grouped=source is not None and source['path'] in selected
    ordinary=[path for path in selected if not grouped or path!=source['path']]
    plan=plan_cleanup(ownership_path,ownership_sha256,selected_roots=ordinary,bootstrap_paths=bootstrap_paths) if ordinary else None
    if not grouped:
        _need(plan is not None,'invalid_cleanup_selection');return plan
    targets=list(plan['targets']) if plan else []
    targets.append(dict(path=source['path'],resolved_path='; '.join(source['scope_paths'])))
    return dict(schema='books-lifecycle-combined-cleanup-v1',ordinary=plan,source=source,
        bytes=(plan['bytes'] if plan else 0)+source['bytes'],targets=targets,
        warning=(plan['warning']+' ' if plan else '')+
            'This deletes the listed retained source data folders and permanently removes rollback to that source copy.')


def execute_selected_cleanup(plan,sha,*,owner_path=None,process_name='Books Arranger.exe'):
    if plan.get('schema')=='books-lifecycle-terminal-cleanup-v1':
        _need(hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()==sha,'cleanup_plan_changed')
        from storage_lifecycle_controls import execute_terminal_selection
        selection=plan['selection'];digest=hashlib.sha256(json.dumps(selection,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        # Helper extraction/CWD is already private and outside the installation
        # being removed. Its temporary native owner is not retained app data.
        _need(owner_path is not None,'terminal_owner_required')
        return execute_terminal_selection(selection,digest,owner_path=owner_path,process_name=process_name)
    if plan.get('schema')!= 'books-lifecycle-combined-cleanup-v1':return execute_cleanup(plan,sha)
    _need(hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()==sha,'cleanup_plan_changed')
    ordinary=plan['ordinary'];source=plan['source']
    if ordinary:
        fresh=plan_cleanup(ordinary['ownership_path'],ordinary['ownership_sha256'],selected_roots=[t['path'] for t in ordinary['targets']],bootstrap_paths=ordinary.get('bootstrap_paths',()))
        _need(fresh==ordinary,'changed_since_review')
    from storage_lifecycle_retirement import execute_source_retirement
    retired=execute_source_retirement(source['review'],source['review_sha256'],
        selected_roots=[source['group_id']],forfeit_rollback=True)
    result=dict(ok=True,removed_files=retired.get('files_removed',0),removed_bytes=retired.get('bytes_removed',0),
        removed_directories=source['scope_paths'] if retired.get('complete') else [],retained_directories=[],remaining_files=[],result='selected_data_removed')
    if ordinary:
        try:
            extra=execute_cleanup(ordinary,hashlib.sha256(json.dumps(ordinary,sort_keys=True,separators=(',',':')).encode()).hexdigest())
            result.update(extra);result['removed_files']+=retired.get('files_removed',0);result['removed_bytes']+=retired.get('bytes_removed',0)
            result['removed_directories']+=source['scope_paths']
        except (OSError,ValueError):
            result.update(ok=False,result='partial_cleanup',remaining_files=[i['path'] for t in ordinary['targets'] for i in t['files'] if os.path.lexists(i['path'])],
                retained_directories=[t['path'] for t in ordinary['targets'] if os.path.lexists(t['path'])])
    return result


MESSAGES={
    'installation_commit_incomplete':'An interrupted installation left retained profile work. Existing data was kept. Review books-arranger-selection-in-progress.json before retrying; the partial profile will not be adopted automatically.',
    'unsupported_legacy_package':'This installed package cannot be safely replaced automatically. Its uninstaller was not run. Keep its data and use a verified supported package.',
    'legacy_package_changed':'The old application contains changed or unrecognized files. Nothing was removed. Its uninstaller was not run.',
    'in_use':'Books Arranger is still using this database. Choose Quit in Books Arranger and wait for its work to finish, then choose Check again.',
    'unsupported_database':'This file is not a supported Books Arranger database. Choose another database or a separate new data folder.',
    'new_folder_not_empty':'The new data folder contains files. Choose a separate empty folder.',
    'selection_changed':'The selected location changed during setup. Check it again before continuing.',
    'changed_since_review':'The selected location changed during setup. Check it again before continuing.',
    'protected_alias':'This location points to data used by another installation. Keep it and select only locations that are no longer used.',
    'ownership_not_confirmed':'Books Arranger cannot confirm which files it owns at this location. Keep this location.',
    'location_unavailable':'Books Arranger cannot reach the selected location. Reconnect the drive or restore the folder before continuing.',
    'relocation_configuration_required':'This database was relocated. Its verified storage configuration is required before it can be used. Select the existing installation or finish the relocation verification.',
    'relocation_verification_required':'Relocation verification is not complete. Keep this database and finish verification before starting work.',
}


def _read_ini(path):
    path=_absolute(str(path))
    with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as held:
        _need(held.facts()['links']==1 and held.facts()['size']<=65536,'invalid_request',path)
        single_stream(path);raw=b''.join(held.chunks())
    parser=configparser.ConfigParser(interpolation=None,strict=True)
    # Unicode NSIS writes UTF-16LE with BOM; test/other callers may use UTF-8.
    parser.read_string(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))
    _need(parser.has_section('request'),'invalid_request')
    return parser


def _list_ini(ini,name,bound=MAX_CANDIDATES):
    count=ini.getint('request',name+'_count',fallback=0)
    _need(0<=count<=bound,'invalid_request')
    return [ini.get(name+str(i),'path') for i in range(count)]


def wizard(request_path,response_path):
    """A bounded INI bridge; native NSIS never evaluates JSON or shell text."""
    response=configparser.ConfigParser(interpolation=None)
    response['result']={'ok':'0','code':'could_not_check'}
    exitcode=1
    from storage_lifecycle_controls import ControlRecordsHeld
    try:
        ini=_read_ini(request_path);req=ini['request'];action=req.get('action','')
        if action=='process-check':
            result=process_check(_list_ini(ini,'installation'),req.get('process_name','Books Arranger.exe'),
                launcher_pid=int(req['launcher_pid']) if req.get('launcher_pid') else None)
            _need(result['state']=='available','in_use')
        elif action=='admit-application-target':
            result=admit_application_target(req['application_dir'],req.get('registered_application_dir',''),req.get('registered_version',''),req.get('process_name','Books Arranger.exe'))
        elif action=='legacy-update-plan':
            result=legacy_update_plan(req['application_dir'],req.get('version',''),process_name=req.get('process_name','Books Arranger.exe'))
            response['result']['existing_bootstrap']=str(result['existing_bootstrap'])
            if result.get('plan'):
                raw=json.dumps(result['plan'],sort_keys=True,separators=(',',':')).encode('utf8')
                path=Path(response_path).parent/('legacy-update-selection-'+str(uuid.uuid4())+'.json');produced=_write_new(path,raw)
                response['result'].update(plan_path=str(path),plan_sha256=produced['sha256'])
        elif action=='prepare-application-stage':
            from application_publication import prepare_application_stage,admit_empty_application_target
            from storage_lifecycle_controls import create_control_namespace
            target=_absolute(req['application_dir']);namespace=create_control_namespace(str(target),'installation');control=Path(namespace['path'])
            creation=control/'namespace.json';created=_write_new(creation,json.dumps(dict(schema='books-control-namespace-creation-v1',
                application_dir=str(target),namespace=namespace),sort_keys=True).encode())
            response['result'].update(control_namespace=str(creation),control_namespace_sha256=created['sha256'])
            admission=None
            if req.get('retained_package'):
                kept,_,sha=_json(req['retained_package']);_need(sha==req['retained_package_sha256'],'legacy_retention_unverified')
                if os.path.normcase(kept.get('root',''))==os.path.normcase(str(target)):
                    admission=dict(path=req['retained_package'],sha256=sha)
            if admission is None and target.exists():
                admission=admit_empty_application_target(target,receipt_path=control/('empty-admission-'+str(uuid.uuid4())+'.json'))
            package=Path(__file__).resolve().parent/'current-package.json';_,_,sha=_json(package)
            result=prepare_application_stage(target,transaction_path=control/('publish-'+str(uuid.uuid4())+'.json'),
                package_manifest=package,package_sha256=sha,target_admission=admission)
            response['result'].update(stage=result['stage'],plan_path=result['plan_path'],plan_sha256=result['plan_sha256'])
        elif action=='publish-application-stage':
            from application_publication import verify_publish_application
            result=verify_publish_application(req['plan_path'],req['plan_sha256'])
            _need(result.get('published') is True,'application_publication_held',req['plan_path'])
            if result.get('empty_stage_identity'):
                from lifecycle_directory_cleanup import dispose_owned_empty_directory
                cleanup=dispose_owned_empty_directory(result['stage'],result['empty_stage_identity'],
                    receipt_path=Path(req['plan_path']).parent/('empty-stage-'+str(uuid.uuid4())+'.json'))
                response['result']['retained_stage']='' if cleanup.get('removed') else result['stage']
            response['result'].update(target=result['target'],receipt=result['receipt_path'],receipt_sha256=result.get('receipt_sha256',result.get('sha256','')))
        elif action=='retire-legacy-package':
            result=retire_legacy_package(req['installation_dir'],req['version'],
                process_name=req.get('process_name','Books Arranger.exe'))
            response['result'].update(receipt=result['receipt'],receipt_sha256=result['receipt_sha256'])
        elif action=='retire-owned-package':
            result=retire_owned_package(req['installation_dir'],req['version'],process_name=req.get('process_name','Books Arranger.exe'))
            response['result'].update(receipt=result['receipt'],receipt_sha256=result['receipt_sha256'])
        elif action=='remove-package':
            result=remove_current_package(req['bootstrap'],req['application_dir'])
        elif action=='capture-package':
            retained=dict(manifest=req['retained_package'],sha256=req['retained_package_sha256']) if req.get('retained_package') else None
            namespace=dict(manifest=req['control_namespace'],sha256=req['control_namespace_sha256']) if req.get('control_namespace') else None
            result=publish_current_package(req['bootstrap'],retained,namespace)
        elif action=='discover':
            result=known_candidates(_list_ini(ini,'config'),_list_ini(ini,'candidate'),_list_ini(ini,'bootstrap'))
            response['result']['count']=str(len(result['candidates']))
            for index,row in enumerate(result['candidates']):
                response['candidate'+str(index)]={key:str(row.get(key) if row.get(key) is not None else '')
                    for key in ('path','state','bytes','resolved_path','profile_dir','profile_confirmed')}
                response['candidate'+str(index)]['display_state']={
                    'available':'Available','in_use':'In use','access_denied':'Access denied',
                    'location_unavailable':'Location unavailable','unsupported_database':'Unsupported database'
                }.get(row['state'],'Could not check')
        elif action=='selection':
            result=selection_plan(req['mode'],req['location'],application_dir=req['application_dir'],
                                  profile_dir=req['profile_dir'],config_paths=_list_ini(ini,'config'))
            raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode('utf8')
            plan=Path(response_path).absolute().parent/('selection-'+str(uuid.uuid4())+'.json')
            _write_new(plan,raw)
            response['result'].update(plan_path=str(plan),plan_sha256=hashlib.sha256(raw).hexdigest(),
                data_dir=result['selection']['data_dir'],database=result['selection']['database'],
                profile_dir=result['profile_dir'],profile_confirmed=str(result['selection'].get('profile_confirmed',False)))
        elif action=='commit-selection':
            plan,_,digest=_json(req['plan_path'])
            _need(digest==req['plan_sha256'],'selection_changed')
            retained=dict(manifest=req['retained_package'],sha256=req['retained_package_sha256']) if req.get('retained_package') else None
            namespace=dict(manifest=req['control_namespace'],sha256=req['control_namespace_sha256']) if req.get('control_namespace') else None
            result=commit_selection(plan,digest,process_name=req.get('process_name','Books Arranger.exe'),require_package=True,retained_package=retained,control_namespace=namespace)
            response['result'].update(bootstrap=result['bootstrap'],database=result['database'],outcome=result['result'])
        elif action=='review-uninstall':
            result=review_uninstall(req['bootstrap'],output_dir=Path(response_path).absolute().parent,expected_application_dir=req['application_dir'],runtime_path=req.get('runtime_path'))
            response['result'].update(count=str(len(result['targets'])),database=result['database'],profile_dir=result['profile_dir'],
                ownership_path=result['ownership_path'],ownership_sha256=result['ownership_sha256'],authority_bootstrap=result['authority_bootstrap'])
            if result.get('source_pin'):response['result'].update(source_review=result['source_pin']['path'],source_review_sha256=result['source_pin']['sha256'])
            for index,row in enumerate(result['targets']):
                response['target'+str(index)]={key:str(row.get(key) if row.get(key) is not None else '')
                    for key in ('path','state','bytes','role','can_remove','resolved_path','reason','entry_type')}
                labels={'database':'Database and job history','profile':'Settings and credentials',
                    'records':'Installation and rollback records',
                    'maintenance':'Installer temporary work (retained parent)',
                    'maintenance-copy':'Uninstaller program (kept)',
                    'retained-source':'Retained source (rollback copy)',
                    'work':'Conversion work','recovery':'Recovery copies','cache':'Caches and downloads',
                    'downloads':'Caches and downloads','logs':'Logs','backups':'Backups'}
                response['target'+str(index)]['display_role']=', '.join(labels.get(role,'Ownership not confirmed') for role in row.get('content_roles',[row['role']]))
        elif action=='plan-cleanup':
            source_pin=dict(path=req['source_review'],sha256=req['source_review_sha256']) if req.get('source_review') else None
            result=plan_selected_cleanup(req['ownership_path'],req['ownership_sha256'],_list_ini(ini,'selected',32),source_pin,
                bootstrap_paths=[req['authority_bootstrap']] if req.get('authority_bootstrap') else (),runtime_path=req.get('runtime_path'))
            raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode('utf8')
            plan=Path(response_path).absolute().parent/('cleanup-'+str(uuid.uuid4())+'.json')
            _write_new(plan,raw)
            response['result'].update(plan_path=str(plan),plan_sha256=hashlib.sha256(raw).hexdigest(),bytes=str(result['bytes']),warning=result['warning'],count=str(len(result['targets'])),
                forfeits_rollback='1' if result.get('schema')=='books-lifecycle-combined-cleanup-v1' else '0')
            for index,target in enumerate(result['targets']):response['selected'+str(index)]={'path':target['path'],'resolved_path':target['resolved_path']}
        elif action=='execute-cleanup':
            _need(req.get('confirmed')=='1','confirmation_required')
            plan,_,digest=_json(req['plan_path']);_need(digest==req['plan_sha256'],'cleanup_plan_changed')
            result=execute_selected_cleanup(plan,digest,owner_path=Path(response_path).absolute().parent/('terminal-owner-'+str(uuid.uuid4())+'.lock'),
                process_name=req.get('process_name','Books Arranger.exe'))
            response['result'].update(removed_files=str(result['removed_files']),removed_bytes=str(result['removed_bytes']),outcome=result['result'],
                removed_directories=str(len(result['removed_directories'])),package_removed='1' if result.get('package_removed') else '0',
                registry_object_removed=str(result.get('registry_record_removed','')),
                registry_namespace_absent=str(result.get('registry_namespace_absent','')))
            remaining=[dict(path=path,reason='Could not remove; retained for review',bytes=None)
                       for path in result['remaining_files']+result['retained_directories']]+result.get('retained_records',[])
            response['result']['remaining_count']=str(len(remaining))
            for index,row in enumerate(remaining):
                response['remaining'+str(index)]={'path':row['path'],'reason':row['reason'],
                    'bytes':'' if row.get('bytes') is None else str(row['bytes'])}
            if not result['ok']:
                response['result'].update(code='partial_cleanup',message='Uninstall is incomplete. Some selected data was removed before an unexpected failure. Remaining files were kept; check them again before retrying.')
                if result.get('recovery_record'):
                    response['result'].update(path=result['recovery_record'],
                        message='Cleanup is unfinished for this installation. Keep it closed and review the recovery record at “'+result['recovery_record']+'” before retrying.')
        else:raise LifecycleRefused('unsupported_action')
        if action in {'execute-cleanup','remove-package'} and not result['ok']:
            if action=='remove-package':response['result'].update(code='partial_package_cleanup',message='Application removal is incomplete. Some exact app-owned files were removed; retained directories or changed members remain. No recursive deletion was used.')
            response['result']['ok']='0';exitcode=1
        else:response['result'].update(ok='1',code='ok');exitcode=0
    except ControlRecordsHeld as error:
        if error.recovery_record:
            response['result'].update(code='pending_cleanup',path=error.recovery_record,
                message='Cleanup is unfinished for this installation. Keep it closed and review the recovery record at “'+error.recovery_record+'” before retrying.')
        else:response['result'].update(code='control_records_held',message='This location could not be checked. Keep it or restore access before continuing.',details=str(error))
    except LifecycleRefused as error:
        response['result'].update(code=error.code,path=error.path,message=MESSAGES.get(error.code,'This location could not be checked. Keep it or restore access before continuing.'))
    except (OSError,ValueError,sqlite3.Error,configparser.Error):
        response['result'].update(code='could_not_check',message='This location could not be checked. Keep it or restore access before continuing.')
    import io
    output=io.StringIO();response.write(output,space_around_delimiters=False)
    _write_new(response_path,output.getvalue().encode('utf-16'))
    return exitcode


def _run(request):
    action = request.get('action')
    if action == 'process-check':return process_check(request.get('installation_dirs', ()), request.get('process_name', 'Books Arranger.exe'))
    if action == 'discover':return known_candidates(request.get('config_paths', ()), request.get('candidate_paths', ()))
    if action == 'inspect':return inspect_existing(request['database'], config_paths=request.get('config_paths', ()))
    if action == 'selection':return selection_plan(request['mode'], request['location'], application_dir=request['application_dir'],
        profile_dir=request['profile_dir'], config_paths=request.get('config_paths', ()), protected_paths=request.get('protected_paths', ()))
    if action == 'commit-selection':return commit_selection(request['plan'],request['plan_sha256'],
        installation_id=request.get('installation_id'),storage_relocation=request.get('storage_relocation'),
        process_name=request.get('process_name','Books Arranger.exe'))
    if action == 'plan-cleanup':return plan_cleanup(request['ownership_path'], request['ownership_sha256'],
        selected_roots=request['selected_roots'], protected_paths=request.get('protected_paths', ()))
    if action == 'execute-cleanup':return execute_cleanup(request['plan'], request['plan_sha256'], protected_paths=request.get('protected_paths', ()))
    if action == 'review-uninstall':return review_uninstall(request['bootstrap'])
    if action == 'refresh-ownership':return refresh_ownership(request['ownership_path'],request['ownership_sha256'],output_path=request['output_path'])
    raise LifecycleRefused('unsupported_action')


def main(argv=None):
    parser = argparse.ArgumentParser(); parser.add_argument('--request');parser.add_argument('--wizard-request');parser.add_argument('--wizard-response');parser.add_argument('--cleanup-status')
    args = parser.parse_args(argv)
    try:
        if args.cleanup_status:
            _need(not args.request and not args.wizard_request and not args.wizard_response,'invalid_request')
            from storage_lifecycle_controls import cleanup_status
            print(json.dumps(dict(ok=True,result=cleanup_status(args.cleanup_status)),ensure_ascii=False));return 0
        if args.wizard_request or args.wizard_response:
            _need(args.wizard_request and args.wizard_response and not args.request,'invalid_request')
            return wizard(args.wizard_request,args.wizard_response)
        _need(args.request,'invalid_request')
        request, _, _ = _json(args.request)
        result = _run(request)
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=False)); return 0
    except LifecycleRefused as error:
        print(json.dumps({'ok': False, 'code': error.code, 'path': error.path}, ensure_ascii=False)); return 1
    except (OSError, ValueError, sqlite3.Error):
        print(json.dumps({'ok': False, 'code': 'could_not_check'})); return 1


if __name__ == '__main__':raise SystemExit(main())
