"""Finite per-user application publication: pinned stage, exact reservation, no replace."""
import contextlib
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import uuid

from native_io import DirectoryBoundary,kernel
from storage_relocation import _inside,_relative,_key
from storage_relocation_operator import (NativeItem,Security,local_root,need,packed,digest,
    pinned_receipt,create_new,_no_directory_streams)
from lifecycle_directory_cleanup import dispose_owned_empty_directory
from directory_retention import retain_directory_no_replace

SCHEMA='books-application-publication-v1'


def _publish(path,value):
    raw=packed(value);sha=digest(raw)
    if path.exists():
        with pinned_receipt(path,sha) as previous:need(previous==value,'Application publication receipt differs')
    else:create_new(path,raw)
    return sha


def _private_create(path):
    """CREATE_NEW directory with protected current-user + SYSTEM ACL atomically."""
    api=ctypes.WinDLL('advapi32',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    api.OpenProcessToken.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
    api.GetTokenInformation.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    api.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(wintypes.LPWSTR)]
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,ctypes.POINTER(ctypes.c_void_p),ctypes.c_void_p]
    token=wintypes.HANDLE();need(api.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)),'Current installer token unavailable')
    sid=wintypes.LPWSTR();descriptor=ctypes.c_void_p()
    try:
        size=wintypes.DWORD();api.GetTokenInformation(token,1,None,0,ctypes.byref(size));need(0<size.value<65536,'Installer token size invalid')
        buffer=ctypes.create_string_buffer(size.value)
        need(api.GetTokenInformation(token,1,buffer,len(buffer),ctypes.byref(size)),'Installer user unavailable')
        sid_pointer=ctypes.cast(buffer,ctypes.POINTER(ctypes.c_void_p))[0]
        need(api.ConvertSidToStringSidW(sid_pointer,ctypes.byref(sid)),'Installer SID unavailable')
        need(api.ConvertStringSecurityDescriptorToSecurityDescriptorW('D:P(A;OICI;FA;;;'+sid.value+')(A;OICI;FA;;;SY)',1,
            ctypes.byref(descriptor),None),'Private application ACL unavailable')
        # NtCreateFile(FILE_CREATE | FILE_DIRECTORY_FILE) returns the creator's
        # directory handle atomically. CreateDirectory followed by Open cannot
        # distinguish a competing replacement in that initial observation gap.
        class Unicode(ctypes.Structure):
            _fields_=[('length',wintypes.USHORT),('maximum',wintypes.USHORT),('buffer',wintypes.LPWSTR)]
        class ObjectAttributes(ctypes.Structure):
            _fields_=[('length',wintypes.ULONG),('root',wintypes.HANDLE),('name',ctypes.POINTER(Unicode)),
                      ('attributes',wintypes.ULONG),('security',ctypes.c_void_p),('quality',ctypes.c_void_p)]
        class IoStatus(ctypes.Structure):_fields_=[('status',ctypes.c_void_p),('information',ctypes.c_size_t)]
        text=ctypes.create_unicode_buffer('\\??\\'+str(path));length=len(text.value.encode('utf-16-le'))
        need(length<65534,'Application creation path is too long')
        name=Unicode(length,length+2,ctypes.cast(text,wintypes.LPWSTR))
        attributes=ObjectAttributes(ctypes.sizeof(ObjectAttributes),None,ctypes.pointer(name),0x40,descriptor,None)
        api_nt=ctypes.WinDLL('ntdll');api_nt.NtCreateFile.restype=wintypes.LONG
        api_nt.NtCreateFile.argtypes=[ctypes.POINTER(wintypes.HANDLE),wintypes.DWORD,ctypes.POINTER(ObjectAttributes),
            ctypes.POINTER(IoStatus),ctypes.c_void_p,wintypes.ULONG,wintypes.ULONG,wintypes.ULONG,wintypes.ULONG,ctypes.c_void_p,wintypes.ULONG]
        created=wintypes.HANDLE();status=IoStatus()
        result=api_nt.NtCreateFile(ctypes.byref(created),0x160081,ctypes.byref(attributes),ctypes.byref(status),
            None,0x10,1,2,0x200021,None,0)
        need(result>=0 and created and status.information==2,'Atomic application CREATE_NEW directory refused')
        try:
            from native_io import FileInfo
            info=FileInfo();need(kernel.GetFileInformationByHandle(created,ctypes.byref(info)) and
                info.attributes&0x10 and not info.attributes&0x400 and info.volume and (info.index_high or info.index_low),
                'Created application directory type/native identity unavailable')
            item=NativeItem(path,directory=True);item.handle=created
            return dict(identity=[info.volume,info.index_high,info.index_low],security=Security().capture(item))
        finally:kernel.CloseHandle(created)
    finally:
        kernel.CloseHandle(token)
        local=ctypes.WinDLL('kernel32');local.LocalFree.argtypes=[ctypes.c_void_p]
        if sid:local.LocalFree(sid)
        if descriptor:local.LocalFree(descriptor)


def _manifest(path,sha):
    with pinned_receipt(path,sha) as value:package=dict(value)
    need(package.get('schema')=='books-trusted-current-package-v1' and isinstance(package.get('files'),dict) and
         0<len(package['files'])<=100000,'Unsupported trusted current package')
    need({'Books Arranger.exe','Uninstall Books Arranger.exe','uninstallerIcon.ico'}.issubset(package['files']) and
         package.get('generated_uninstaller_sha256')==package['files']['Uninstall Books Arranger.exe'].get('sha256'),
         'Trusted package must bind normal application and newly generated uninstaller/icon')
    names=set()
    for name,entry in package['files'].items():
        relative=_relative(name);need(_key(relative) not in names,'Duplicate/case-alias package member');names.add(_key(relative))
        need(isinstance(entry,dict) and type(entry.get('size')) is int and entry['size']>=0 and
             isinstance(entry.get('sha256'),str) and len(entry['sha256'])==64,'Invalid package member hash/size')
    return package


def _snapshot(root,package):
    """Actual ordinary membership + every native ID/hash, held until scan done."""
    from source_cleanup import single_stream
    expected=package['files'];files={};directories={};expected_dirs={'.'}
    for name in expected:
        parent=Path(name).parent
        while str(parent)!='.':expected_dirs.add(parent.as_posix());parent=parent.parent
    with contextlib.ExitStack() as stack:
        stack.enter_context(DirectoryBoundary(root.anchor,root))
        for folder,names,entries in os.walk(root,followlinks=False):
            folder=Path(folder);item=stack.enter_context(NativeItem(folder,directory=True))
            _no_directory_streams(folder)
            relative=folder.relative_to(root).as_posix();directories[relative]=item.facts['identity']
            for name in entries:
                path=folder/name;relative=path.relative_to(root).as_posix()
                need(relative in expected,'Unknown application stage member retained')
                item=stack.enter_context(NativeItem(path));single_stream(path)
                sha=item.sha256();known=expected[relative]
                need(item.facts['size']==known['size'] and sha==known['sha256'],'Application payload bytes differ')
                files[relative]=dict(facts=item.facts,sha256=sha)
        need(set(files)==set(expected) and set(directories)==expected_dirs,'Application payload membership differs')
    return dict(root_identity=directories['.'],files=files,directories=directories)


def admit_empty_application_target(target,*,receipt_path,protected_paths=()):
    """Explicit earlier user selection, not implicit adoption during extraction."""
    target=local_root(target);receipt_path=Path(receipt_path).absolute()
    for protected in protected_paths:
        protected=Path(protected).absolute()
        need(not _inside(str(target.resolve()),str(protected.resolve())) and not _inside(str(protected.resolve()),str(target.resolve())),
             'Selected application target overlaps protected source/library/data')
    need(not _inside(str(receipt_path.resolve()),str(target.resolve())),'Target admission must live outside selected directory')
    with DirectoryBoundary(target.anchor,target.parent),NativeItem(target,directory=True) as held:
        with os.scandir(target) as entries:need(next(entries,None) is None,'Selected application target is not empty')
        _no_directory_streams(target)
        proof=dict(schema='books-application-empty-target-admission-v1',phase='selected-empty',target=str(target),
                   identity=held.facts['identity'],token=uuid.uuid4().hex)
        sha=_publish(receipt_path,proof)
    return dict(path=str(receipt_path),sha256=sha)


def prepare_application_stage(target,*,transaction_path,package_manifest,package_sha256,protected_paths=(),target_admission=None):
    target=local_root(target);transaction_path=Path(transaction_path).absolute();package_manifest=Path(package_manifest).absolute()
    need(target.parent!=target and target.parent.is_dir(),'Application target parent must already exist')
    for protected in protected_paths:
        protected=Path(protected).absolute()
        need(not _inside(str(target.resolve()),str(protected.resolve())) and not _inside(str(protected.resolve()),str(target.resolve())),
             'Application target overlaps protected source/library/data')
    need(not _inside(str(transaction_path.resolve()),str(target.resolve())) and
         not _inside(str(package_manifest.resolve()),str(target.resolve())),'Application controls must be outside target')
    need(not transaction_path.exists(),'Application transaction already exists; inspect its durable receipts')
    package=_manifest(package_manifest,package_sha256);token=uuid.uuid4().hex
    stage=target.with_name(target.name+'.books-stage-'+token)
    with DirectoryBoundary(target.anchor,target.parent),DirectoryBoundary(transaction_path.anchor,transaction_path.parent):
        admission=None
        if os.path.lexists(target):
            need(isinstance(target_admission,dict) and set(target_admission)=={'path','sha256'},
                 'Existing application target requires an earlier pinned native admission')
            with pinned_receipt(target_admission['path'],target_admission['sha256']) as value:admission=dict(value)
            retention=admission.get('retention') or {}
            retained=admission.get('schema')=='books-legacy-package-retirement-v1' and admission.get('state')=='original-retained' and \
                 Path(retention.get('source','')).absolute()==target and retention.get('original_preserved') is True
            selected=admission.get('schema')=='books-application-empty-target-admission-v1' and admission.get('phase')=='selected-empty' and \
                 admission.get('target')==str(target) and isinstance(admission.get('token'),str)
            need(retained or selected,'Existing target is not an earlier admitted native placeholder/selection')
        intent=dict(schema=SCHEMA,phase='prepare-intent',target=str(target),stage=str(stage),token=token,
                    package_manifest=str(package_manifest),package_sha256=package_sha256,target_admission=target_admission,
                    protected_paths=[str(Path(p).absolute()) for p in protected_paths])
        _publish(transaction_path,intent)
        created_placeholder=None
        if admission is None:created_placeholder=_private_create(target)
        elif selected:
            # Convert the earlier exact user-selected empty directory into our
            # own atomic reservation. Any raced arrival wins and stays intact.
            disposed=dispose_owned_empty_directory(target,admission['identity'],
                receipt_path=Path(str(transaction_path)+'.selected-empty-disposal.json'))
            need(disposed['removed'],'Earlier selected empty target could not be reserved')
            created_placeholder=_private_create(target)
        with NativeItem(target,directory=True) as reserved:
            if created_placeholder:need(reserved.facts['identity']==created_placeholder['identity'],
                                        'Atomically created placeholder was replaced')
            if admission is not None and retained:need(reserved.facts['identity']==retention['new_source_identity'],'Application placeholder identity changed')
            with os.scandir(target) as entries:need(next(entries,None) is None,'Application placeholder is not empty')
            _no_directory_streams(target);placeholder=reserved.facts['identity']
            created_stage=_private_create(stage)
            with NativeItem(stage,directory=True) as held:
                need(held.facts['identity']==created_stage['identity'],'Atomically created stage was replaced')
                stage_identity=held.facts['identity'];security=Security().capture(held)
                need(security['sddl']==created_stage['security']['sddl'],'Private creator stage permissions changed')
        plan=dict(intent,phase='prepared',placeholder_identity=placeholder,stage_identity=stage_identity,
                  stage_security=security)
        plan_path=Path(str(transaction_path)+'.plan.json');sha=_publish(plan_path,plan)
        return dict(stage=str(stage),target=str(target),plan_path=str(plan_path),plan_sha256=sha,
                    placeholder_identity=placeholder,token=token)


def verify_publish_application(plan_path,plan_sha256):
    plan_path=Path(plan_path).absolute()
    with pinned_receipt(plan_path,plan_sha256) as read:plan=dict(read)
    need(plan.get('schema')==SCHEMA and plan.get('phase')=='prepared','Unsupported application publication plan')
    target=local_root(plan['target']);stage=local_root(plan['stage'])
    need(target.parent==stage.parent and target!=stage,'Application stage must be a distinct same-parent directory')
    package=_manifest(plan['package_manifest'],plan['package_sha256'])
    completed=Path(str(plan_path)+'.published.json')
    if completed.exists():
        sha=digest(completed.read_bytes())
        with pinned_receipt(completed,sha) as proof:
            need(proof.get('plan_sha256')==plan_sha256 and proof.get('phase')=='published','Publication replay receipt differs')
            need(_snapshot(target,package)==proof['snapshot'],'Published application changed after closure')
        return dict(published=True,phase='published',target=str(target),stage=str(stage),receipt_path=str(completed),receipt_sha256=sha)
    with DirectoryBoundary(target.anchor,target.parent,rename_destination=True):
        with NativeItem(stage,directory=True) as held:
            need(held.facts['identity']==plan['stage_identity'] and Security().capture(held)['sddl']==plan['stage_security']['sddl'],
                 'Owned application stage identity/security changed')
        snapshot=_snapshot(stage,package)
        need(snapshot['root_identity']==plan['stage_identity'],'Application stage was replaced')
        verified=Path(str(plan_path)+'.verified-stage.json')
        _publish(verified,dict(schema=SCHEMA,phase='verified-stage',plan_sha256=plan_sha256,snapshot=snapshot))
        # Stock extraction never touches the final target. Dispose only its
        # exact admitted reservation; a foreign arrival is never adopted.
        result=dispose_owned_empty_directory(target,plan['placeholder_identity'],
                     receipt_path=Path(str(plan_path)+'.placeholder-disposal.json'))
        need(result['removed'],'Application placeholder could not be retired; stage retained')
        renamed=retain_directory_no_replace(stage,target,plan['stage_identity'])
        # The native rename primitive recreates an owned empty stage name. It
        # is recorded, never mistaken for the original package staging tree.
        final=_snapshot(target,package)
        need(final==snapshot,'Published application native identities/bytes changed; normal admission refused')
        proof=dict(schema=SCHEMA,phase='published',plan_sha256=plan_sha256,target=str(target),stage=str(stage),
                   snapshot=final,rename=renamed,placeholder_disposal=result)
        sha=_publish(completed,proof)
        return dict(published=True,phase='published',target=str(target),stage=str(stage),receipt_path=str(completed),
                    receipt_sha256=sha,empty_stage_identity=renamed['new_source_identity'])
