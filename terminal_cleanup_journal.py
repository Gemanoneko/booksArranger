"""Private HKCU journal for the LAST finite, reviewed installation cleanup.

No CLI, file journal, recursive directory removal or native bypass boolean.
All deletion members originate in genuine pinned lifecycle plans. Registry
authority/intent is flushed before ACL mutation and removed only after closure.
"""
import base64
import contextlib
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import threading
import uuid
import winreg

from native_io import DirectoryBoundary,FileInfo,VerifiedFile,kernel
from storage_relocation_operator import (NativeItem,Security,need,packed,digest,bounded_json,
    local_root,_no_directory_streams)
from storage_source_finalization import _relax_delete,_delete_fenced
from lifecycle_fence_security import restore_owned_fence

BASE=r'Software\Books Arranger\UninstallTransactions'
SCHEMA='books-terminal-registry-cleanup-v1'
MAX_RECORD=256*1024
MAX_AUTHORITY=16*1024*1024
MAX_MEMBERS=10000
ACCESS=winreg.KEY_ALL_ACCESS|winreg.KEY_WOW64_64KEY


class _RegistryHandle(int):
    """Owned native HKEY, accepted by winreg without reopening its pathname."""
    def __new__(cls,value):
        item=int.__new__(cls,value);item.closed=False;return item
    def Close(self):
        if not self.closed:winreg.CloseKey(int(self));self.closed=True


def _native_key_name(handle):
    nt=ctypes.WinDLL('ntdll');nt.NtQueryKey.argtypes=[wintypes.HANDLE,wintypes.ULONG,ctypes.c_void_p,wintypes.ULONG,ctypes.c_void_p]
    nt.NtQueryKey.restype=wintypes.LONG
    buffer=ctypes.create_string_buffer(65540);returned=wintypes.ULONG()
    need(nt.NtQueryKey(int(handle),3,buffer,len(buffer),ctypes.byref(returned))>=0,
         'Terminal registry native key identity unavailable/deleted')
    length=int.from_bytes(buffer.raw[:4],'little')
    need(0<length<=65536 and length%2==0 and length+4<=returned.value<=len(buffer),
         'Terminal registry native name bounds are invalid')
    name=buffer.raw[4:4+length].decode('utf-16-le','strict')
    need('\x00' not in name,'Terminal registry native name is malformed');return name


def _current_sid():
    api=ctypes.WinDLL('advapi32',use_last_error=True);kernel.GetCurrentProcess.restype=wintypes.HANDLE
    api.OpenProcessToken.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
    api.GetTokenInformation.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    api.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(wintypes.LPWSTR)]
    token=wintypes.HANDLE();text=wintypes.LPWSTR()
    need(api.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)),'Terminal current user token unavailable')
    try:
        size=wintypes.DWORD();api.GetTokenInformation(token,1,None,0,ctypes.byref(size))
        need(0<size.value<=65536,'Terminal current user SID bounds invalid');data=ctypes.create_string_buffer(size.value)
        need(api.GetTokenInformation(token,1,data,len(data),ctypes.byref(size)) and
             api.ConvertSidToStringSidW(ctypes.cast(data,ctypes.POINTER(ctypes.c_void_p))[0],ctypes.byref(text)),
             'Terminal current user SID unavailable')
        return text.value
    finally:
        if text:
            local=ctypes.WinDLL('kernel32');local.LocalFree.argtypes=[ctypes.c_void_p];local.LocalFree(text)
        kernel.CloseHandle(token)


def _assert_key(handle,expected):
    need(_native_key_name(handle).casefold()==expected.casefold(),'Terminal registry key renamed, linked or escaped its exact namespace')
    try:
        _,kind=winreg.QueryValueEx(handle,'SymbolicLinkValue')
        need(kind!=winreg.REG_LINK,'Terminal registry link objects are unsupported')
    except FileNotFoundError:pass


def _open_or_create_leaf(parent,name,expected,*,fresh=False):
    """Never follow a registry link and never adopt an existing UUID key."""
    api=ctypes.WinDLL('advapi32',use_last_error=True)
    api.RegOpenKeyExW.argtypes=[wintypes.HANDLE,wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
    api.RegOpenKeyExW.restype=wintypes.LONG
    api.RegCreateKeyExW.argtypes=[wintypes.HANDLE,wintypes.LPCWSTR,wintypes.DWORD,wintypes.LPWSTR,wintypes.DWORD,
        wintypes.DWORD,ctypes.c_void_p,ctypes.POINTER(wintypes.HANDLE),ctypes.POINTER(wintypes.DWORD)]
    api.RegCreateKeyExW.restype=wintypes.LONG
    handle=wintypes.HANDLE();disposition=wintypes.DWORD()
    if not fresh:
        status=api.RegOpenKeyExW(int(parent),name,8,ACCESS,ctypes.byref(handle)) # REG_OPTION_OPEN_LINK
        if status==0:
            result=_RegistryHandle(handle.value)
            try:_assert_key(result,expected);return result
            except BaseException:result.Close();raise
        need(status in (2,3),'Terminal shared registry parent cannot be opened safely')
    status=api.RegCreateKeyExW(int(parent),name,0,None,0,ACCESS,None,ctypes.byref(handle),ctypes.byref(disposition))
    need(status==0,'Terminal registry key cannot be created')
    result=_RegistryHandle(handle.value)
    try:
        need(not fresh or disposition.value==1,'Terminal UUID key already exists; never adopt or clear it')
        _assert_key(result,expected);return result
    except BaseException:result.Close();raise


def _create_transaction(registry_path):
    expected='\\REGISTRY\\USER\\'+_current_sid();handles=[]
    try:
        # An actual current-user handle permits native-name verification rather
        # than trusting the HKCU pseudo handle or thread/path redirection.
        root=winreg.OpenKey(winreg.HKEY_CURRENT_USER,'',0,ACCESS);handles.append(root);_assert_key(root,expected)
        parts=registry_path.split('\\')
        for index,name in enumerate(parts):
            need(name and name not in ('.','..') and '\x00' not in name,'Terminal registry component invalid')
            _assert_key(handles[-1],expected);expected+='\\'+name
            handles.append(_open_or_create_leaf(handles[-1],name,expected,fresh=index==len(parts)-1))
        return handles,expected
    except BaseException:
        for handle in reversed(handles):handle.Close()
        raise


def _delete_actual_key(handle):
    """The kernel refuses subkeys; no name-based replacement can be deleted."""
    nt=ctypes.WinDLL('ntdll');nt.NtDeleteKey.argtypes=[wintypes.HANDLE];nt.NtDeleteKey.restype=wintypes.LONG
    need(nt.NtDeleteKey(int(handle))>=0,'Terminal registry key has a subkey or native deletion is held')


def _uuid(value):
    need(isinstance(value,str) and str(uuid.UUID(value))==value,'Canonical cleanup UUID required');return value


def _key(path):return os.path.normcase(str(Path(path).absolute()))


def _read_document(path,sha256):
    from source_cleanup import single_stream
    path=Path(path).absolute()
    with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as held:
        facts=held.facts();need(facts['links']==1 and facts['size']<=MAX_AUTHORITY,'Bounded unique lifecycle authority required')
        single_stream(path);raw=b''.join(held.chunks());need(digest(raw)==sha256,'Lifecycle authority SHA changed')
        return bounded_json(raw,sha256),facts,base64.b64encode(raw).decode('ascii')


def _positive_absence(path):
    path=Path(path).absolute();parent=path.parent
    while not parent.exists():parent=parent.parent
    with DirectoryBoundary(parent.anchor,parent):
        child=path
        while child.parent!=parent:child=child.parent
        with os.scandir(parent) as names:return child.name.casefold() not in {entry.name.casefold() for entry in names}


class _DeleteItem(NativeItem):
    def __enter__(self):
        self.handle=kernel.CreateFileW(str(self.path),0x30081,1,None,3,0x00200000|(0x02000000 if self.directory else 0),None)
        if self.handle==ctypes.c_void_p(-1).value:
            self.handle=None;need(False,'Terminal cleanup cannot retain exact DELETE handle')
        try:
            self.info=FileInfo();need(kernel.GetFileInformationByHandle(self.handle,ctypes.byref(self.info)) and
                not self.info.attributes&0x400 and bool(self.info.attributes&0x10)==self.directory,
                'Terminal cleanup native type changed')
            self.view=VerifiedFile(self.path);self.view.handle=self.handle;self.view.info=self.info;self.facts=self.view.facts()
            need(self.directory or self.facts['links']==1,'Terminal cleanup hardlinked file held');return self
        except BaseException:self.__exit__(None,None,None);raise


class RegistryCleanupJournal:
    def __init__(self,bootstrap_path,bootstrap_sha256,ownership_path,ownership_sha256,selection,selection_sha256,*,
                 owner_handle,owner_identity,owner_path,transaction_id=None,process_name='Books Arranger.exe'):
        self.bootstrap_path=Path(bootstrap_path).absolute();self.bootstrap_sha256=bootstrap_sha256
        self.ownership_path=Path(ownership_path).absolute();self.ownership_sha256=ownership_sha256
        self.selection=selection;self.selection_sha256=selection_sha256
        self.owner_handle=owner_handle;self.owner_identity=list(owner_identity);self.owner_path=Path(owner_path).absolute()
        self.transaction_id=_uuid(transaction_id or str(uuid.uuid4()));self.stack=contextlib.ExitStack()
        self.lock=threading.RLock();self.handle=None;self.live=False;self.finished=False
        self.members={};self.root_pins=[];self.holds=[];self.registry_handles=[]
        need(isinstance(process_name,str) and process_name and Path(process_name).name==process_name,
             'Exact lifecycle process name required')
        self.process_name=process_name
    def _owner(self):
        # Reuse the actual granted-access/native-ID/sharing-exclusion recipe;
        # invoking this method does not create a runtime filesystem journal.
        from runtime_file_disposition import DispositionContext
        DispositionContext._owner(self)
    def _validate(self):
        need(self.live and not self.finished,'Terminal cleanup journal is closed');self._owner()
        self.owner_boundary.revalidate()
        _assert_key(self.handle,self.native_registry_name)
        raw,kind=winreg.QueryValueEx(self.handle,'Authority')
        need(kind==winreg.REG_BINARY and raw==packed(self.authority),'Terminal registry authority changed after admission')
    def _admit(self):
        import storage_lifecycle as life
        import storage_lifecycle_controls as controls
        need(isinstance(self.selection,dict) and digest(packed(self.selection))==self.selection_sha256 and
             self.selection.get('schema')=='books-terminal-cleanup-selection-v1','Pinned terminal lifecycle selection required')
        bootstrap,bootstrap_facts,bootstrap_raw=_read_document(self.bootstrap_path,self.bootstrap_sha256)
        ownership,ownership_facts,ownership_raw=_read_document(self.ownership_path,self.ownership_sha256)
        installation_id=_uuid(bootstrap.get('installation_id'))
        need(bootstrap.get('schema')=='books-arranger-installation-v1' and
             self.bootstrap_path==Path(bootstrap['application_dir']).absolute().parent/life.BOOTSTRAP and
             ownership.get('schema')=='books-installation-ownership-v1' and ownership.get('installation_id')==installation_id and
             self.selection.get('installation_id')==installation_id,
             'Terminal cleanup authority is not this genuine installation/bootstrap')
        provenance=bootstrap.get('ownership_provenance') or {}
        need(provenance.get('manifest')==str(self.ownership_path) and provenance.get('sha256')==self.ownership_sha256,
             'Terminal ownership is not the pinned installation producer')
        # In-place package retention legitimately publishes a NEW mutable
        # membership document while preserving the original producer pin.
        current_path=Path(bootstrap['ownership_manifest']).absolute()
        current,current_facts,current_sha=life._json(current_path)
        current,current_facts,current_raw=_read_document(current_path,current_sha)
        need(current.get('schema')=='books-installation-ownership-v1' and current.get('installation_id')==installation_id and
             current.get('application_dir')==bootstrap['application_dir'],
             'Mutable current ownership belongs to another installation')
        retained_pin=bootstrap.get('retained_package')
        if retained_pin:
            receipt,_,_=_read_document(retained_pin['manifest'],retained_pin['sha256'])
            need(receipt.get('schema')=='books-legacy-package-retirement-v1' and receipt.get('state')=='original-retained',
                 'Mutable retained package lacks its pinned closed producer')
            retained=dict(path=receipt['retained_application'],identity=receipt['root_identity'],role='backups',files=receipt['files'])
            need(any(root==retained for root in current.get('roots',[])),
                 'Mutable ownership does not preserve the exact retained-package proof')
        # This optional row records a retained operational copy only. It never
        # enters the member list and conveys no filesystem removal authority.
        need(not set(self.selection)-{'schema','installation_id','ordinary','packages','controls','directories','retained_runtime_copy'},
             'Unknown terminal selection domain')
        plans=[]
        ordinary=self.selection.get('ordinary')
        if ordinary is not None:plans.append(ordinary)
        packages=self.selection.get('packages',[]);need(isinstance(packages,list) and len(packages)<=8,'Bounded package plans required')
        pin=bootstrap.get('package_ownership')
        for package in packages:
            need(pin and package.get('ownership_path')==pin['manifest'] and package.get('ownership_sha256')==pin['sha256'],
                 'Package cleanup lacks this installation\'s pinned package authority')
            plans.append(package)
        for plan in plans:
            need(plan.get('schema')==life.PLAN_SCHEMA and plan.get('installation_id')==installation_id,
                 'Unrecognized lifecycle cleanup plan')
            fresh=life.plan_cleanup(plan['ownership_path'],plan['ownership_sha256'],
                selected_roots=[t['path'] for t in plan['targets']],bootstrap_paths=plan.get('bootstrap_paths',()))
            need(fresh==plan,'Genuine lifecycle cleanup changed after review')
            for target in plan['targets']:
                self.root_pins.append(dict(path=target['path'],identity=target['identity']))
                for entry in target['files']:self._member(entry['path'],'file',facts=entry['facts'],sha256=entry['sha256'])
                for entry in target['directories']:self._member(entry['path'],'directory',identity=entry['identity'])
        control=self.selection.get('controls')
        if control is not None:
            need(control.get('schema')==controls.SCHEMA and control.get('phase')=='awaiting-terminal-journal' and
                 control.get('review',{}).get('installation_id')==installation_id and
                 Path(control['review']['bootstrap']).absolute()==self.bootstrap_path and
                 not control['review'].get('holds') and not any(e.get('required_by') for e in control['files']),
                 'External controls lack a genuine unheld lifecycle selection')
            need(control['files']==control['review']['files'] and control['state_roots']==control['review']['state_roots'] and
                 control.get('bootstrap_path')==str(self.bootstrap_path) and control.get('bootstrap_sha256')==self.bootstrap_sha256 and
                 control.get('bootstrap_facts')==bootstrap_facts and control.get('ownership_path')==str(self.ownership_path) and
                 control.get('ownership_sha256')==self.ownership_sha256 and
                 controls.review_control_records(self.bootstrap_path,other_bootstraps=life.registered_bootstraps())==control['review'],
                 'Complete external control selection or installation references changed')
            selected_dirs={(_key(row['path']),tuple(row['identity'])) for row in self.selection.get('directories',[])}
            need(all((_key(row['path']),tuple(row['identity'])) in selected_dirs for row in control.get('directories',[])),
                 'Selected complete controls omit a known owned namespace directory')
            _,references=controls._references(self.bootstrap_path)
            refs={_key(ref['path']):ref for ref in references}
            for entry in control['files']:
                ref=refs.get(_key(entry['path']));need(ref,'Control is not a typed installation/producer reference')
                actual,_=controls._file(entry['path'],ref['kind'],ref.get('sha256'))
                need(actual['facts']==entry['facts'] and actual['sha256']==entry['sha256'],
                     'Selected control native identity/hash changed')
                self._member(entry['path'],'file',facts=entry['facts'],sha256=entry['sha256'])
            self.required_gone=[bootstrap['application_dir'],*control['state_roots']]
        else:self.required_gone=[]
        for entry in self.selection.get('directories',[]):
            need(isinstance(entry,dict) and set(entry)=={'path','identity','producer_pin'},'Unknown control directory admission')
            producer_pin=entry['producer_pin'];known_pin=bootstrap.get('control_provenance')
            need(known_pin and producer_pin==known_pin,'Control directory producer is not pinned by this installation')
            producer,_,_=_read_document(producer_pin['manifest'],producer_pin['sha256'])
            need(producer.get('schema')=='books-control-producer-index-v1' and producer.get('installation_id')==installation_id and
                 _key(producer['application_dir'])==_key(bootstrap['application_dir']),'Control namespace producer belongs to another installation')
            matching=[row for row in producer.get('directories',[]) if _key(row['path'])==_key(entry['path']) and row['identity']==entry['identity']]
            need(len(matching)==1,'Control namespace lacks an exact native CREATE_NEW producer')
            creation=matching[0]
            need(isinstance(creation.get('kind'),str) and creation['kind'] and isinstance(creation.get('token'),str) and
                 0<len(creation['token'])<=128,'Malformed control namespace creator')
            Security().validate_capture(creation['creator_security'])
            with NativeItem(entry['path'],directory=True) as held:
                need(held.facts['identity']==entry['identity'] and
                     Security().capture(held)['sddl']==creation['creator_security']['sddl'],'Control namespace creator native identity/security changed')
            self.root_pins.append(dict(path=entry['path'],identity=entry['identity']))
            self._member(entry['path'],'directory',identity=entry['identity'])
        need(self.members and len(self.members)<=MAX_MEMBERS,'Bounded finite terminal selection required')
        for definition in self.members.values():
            path=Path(definition['path']);local_root(path)
            need(_key(path)!=_key(self.owner_path) and not (definition['kind']=='directory' and
                 (self.owner_path==path or path in self.owner_path.parents)),'Cleanup includes its own actual owner lease')
        for root in self.root_pins:
            with NativeItem(root['path'],directory=True) as held:need(held.facts['identity']==root['identity'],'Selected root native identity changed')
        need(life.process_check([bootstrap['application_dir'],*self.required_gone],self.process_name)['state']=='available',
             'Books Arranger users/jobs still active; terminal cleanup refused')
        return dict(schema=SCHEMA,phase='authority',installation_id=installation_id,transaction_id=self.transaction_id,
            bootstrap_path=str(self.bootstrap_path),bootstrap_sha256=self.bootstrap_sha256,bootstrap_facts=bootstrap_facts,bootstrap_raw=bootstrap_raw,
            ownership_path=str(self.ownership_path),ownership_sha256=self.ownership_sha256,ownership_facts=ownership_facts,ownership_raw=ownership_raw,
            current_ownership_path=str(current_path),current_ownership_sha256=current_sha,
            current_ownership_facts=current_facts,current_ownership_raw=current_raw,process_name=self.process_name,
            selection_sha256=self.selection_sha256,selection=self.selection,owner_path=str(self.owner_path),owner_identity=self.owner_identity,
            members=self.members,root_pins=self.root_pins,required_gone=self.required_gone)
    def _member(self,path,kind,**values):
        path=str(Path(path).absolute());key=_key(path);definition=dict(path=path,kind=kind,**values)
        need(key not in self.members or self.members[key]==definition,'Conflicting terminal cleanup member authority')
        self.members[key]=definition
    def __enter__(self):
        try:return self._enter()
        except BaseException:self.close();raise
    def _enter(self):
        with self.lock:
            local_root(self.owner_path);self.owner_boundary=self.stack.enter_context(DirectoryBoundary(self.owner_path.anchor,self.owner_path.parent))
            self._owner()
            # Fresh admission only. Existing transaction recovery is explicit;
            # it never re-adopts missing bootstrap/selection files by name.
            self.authority=self._admit()
            self.registry_path=BASE+'\\'+self.authority['installation_id']+'\\'+self.transaction_id
            self.registry_handles,self.native_registry_name=_create_transaction(self.registry_path)
            self.handle=self.registry_handles[-1]
            self.authority['registry_contract']=dict(native_key=self.native_registry_name,
                value_ownership='all values on this exact privately CREATE_NEW key for its lifetime',
                subkeys='unsupported and retained',shared_parents='never deleted')
            self.authority_sha256=digest(packed(self.authority))
            need(len(packed(self.authority))<=MAX_AUTHORITY,'Terminal registry authority bound exceeded before cleanup')
            self._put(self.handle,'Authority',self.authority,MAX_AUTHORITY)
            self.live=True;return self
    def _put(self,key,name,value,bound=MAX_RECORD):
        raw=packed(value);need(len(raw)<=bound,'Terminal registry record bound exceeded')
        try:
            existing,kind=winreg.QueryValueEx(key,name)
            need(kind==winreg.REG_BINARY and existing==raw,'Immutable terminal registry record changed')
        except FileNotFoundError:winreg.SetValueEx(key,name,0,winreg.REG_BINARY,raw)
        winreg.FlushKey(key)
        return digest(raw)
    def _record(self,definition,phase,**values):
        name=digest(_key(definition['path']).encode('utf8'))
        value=dict(schema=SCHEMA,authority_sha256=self.authority_sha256,selection_sha256=self.selection_sha256,
            member=definition,phase=phase,**values)
        if phase!='intent':
            intent=self._get(definition,'intent');need(intent,'Terminal phase lacks durable intent')
            value['intent_sha256']=digest(packed(intent))
        return self._put(self.handle,'Phase:'+name+':'+phase,value)
    def _get(self,definition,phase):
        name=digest(_key(definition['path']).encode('utf8'))
        try:
            raw,kind=winreg.QueryValueEx(self.handle,'Phase:'+name+':'+phase)
            need(kind==winreg.REG_BINARY and len(raw)<=MAX_RECORD,'Terminal registry phase is malformed')
            value=bounded_json(raw,digest(raw))
            need(value.get('schema')==SCHEMA and value.get('authority_sha256')==self.authority_sha256 and
                 value.get('selection_sha256')==self.selection_sha256 and value.get('member')==definition and value.get('phase')==phase,
                 'Terminal registry phase authority differs')
            if phase!='intent':
                intent=self._get(definition,'intent')
                need(intent and value.get('intent_sha256')==digest(packed(intent)),
                     'Terminal registry phase does not pin its original durable intent')
            return value
        except FileNotFoundError:return None
    def _definition(self,path,kind,**expected):
        self._validate();key=_key(path);need(key in self.members,'Path is not an exact reviewed terminal member')
        definition=self.members[key]
        need(definition['kind']==kind and all(definition.get(k)==v for k,v in expected.items()),'Terminal member native/hash selection differs')
        return definition
    def dispose_file(self,path,facts,sha):
        with self.lock:return self._dispose(self._definition(path,'file',facts=facts,sha256=sha))
    def dispose_directory(self,path,identity):
        with self.lock:return self._dispose(self._definition(path,'directory',identity=list(identity)))
    def _restore(self,definition,intent):
        path=Path(definition['path']);directory=definition['kind']=='directory'
        try:
            with NativeItem(path,directory=directory) as held:
                need(held.facts['identity']==(definition.get('identity') or definition['facts']['identity']),
                     'Terminal remaining name is a replacement')
                if not directory:need(held.facts==definition['facts'] and held.sha256()==definition['sha256'],
                                      'Terminal remaining original bytes changed')
            return restore_owned_fence(path,definition.get('identity') or definition['facts']['identity'],
                intent['original_security'],intent['expected_acl'],directory=directory)
        except Exception as error:return False,str(error)
    def _dispose(self,definition):
        from source_cleanup import single_stream
        path=Path(definition['path']);directory=definition['kind']=='directory';guard=None;deleting=None
        kernel_success=False;intent=None
        closed=self._get(definition,'closed')
        if closed:
            need(closed.get('native_close') is True and closed.get('observed_absent') is True,'Terminal closed proof incomplete')
            need(_positive_absence(path),'Terminal removed name was reused; foreign arrival retained')
            return dict(removed=True,phase='closed',path=str(path))
        with contextlib.ExitStack() as boundaries:
            boundaries.enter_context(DirectoryBoundary(path.anchor,path.parent))
            for root in self.root_pins:
                root_path=Path(root['path'])
                if root_path in path.parents:
                    held_root=boundaries.enter_context(NativeItem(root_path,directory=True))
                    need(held_root.facts['identity']==root['identity'],'Selected root was replaced; terminal member held')
            intent=self._get(definition,'intent')
            if intent:
                if self._get(definition,'pending'):
                    return dict(removed=False,held=True,phase='interrupted-held',path=str(path),reason='Native pending proof lacks closed disposition; fence retained')
                restored,reason=self._restore(definition,intent)
                return dict(removed=False,held=True,phase='interrupted-held',path=str(path),security_restored=restored,
                            reason=reason or 'Existing intent has no closed disposition proof; original retained')
            try:
                guard=NativeItem(path,directory=directory,writable_security=True).__enter__()
                from runtime_file_disposition import _local_provider
                _local_provider(guard.handle)
                if directory:
                    need(guard.facts['identity']==definition['identity'],'Terminal selected directory native ID changed')
                    with os.scandir(path) as names:need(next(names,None) is None,'Unknown child arrival retained')
                    _no_directory_streams(path)
                else:
                    need(guard.facts==definition['facts'] and guard.sha256()==definition['sha256'],'Terminal selected file native facts/hash changed')
                    single_stream(path)
                security=Security();original=security.capture(guard);expected=security.planned_write_fence_acl(original,directory)
                intent=dict(original_security=original,expected_acl=base64.b64encode(expected).decode('ascii'))
                self._record(definition,'intent',**intent) # RegFlushKey BEFORE any ACL mutation.
                applied=security.apply_planned_write_fence(guard,original,expected)
                self._record(definition,'fenced',applied_security=applied)
                _relax_delete(security,guard,applied);guard.__exit__(None,None,None);guard=None
                deleting=_DeleteItem(path,directory=directory).__enter__()
                need(deleting.facts['identity']==(definition.get('identity') or definition['facts']['identity']) and
                     _delete_fenced(security,deleting,applied),'Terminal reopened native object/fence changed')
                if directory:
                    with os.scandir(path) as names:need(next(names,None) is None,'Unknown directory child retained')
                    _no_directory_streams(path)
                else:
                    need(kernel.GetFileInformationByHandle(deleting.handle,ctypes.byref(deleting.info)) and
                         deleting.view.facts()==definition['facts'] and deleting.sha256()==definition['sha256'],
                         'Terminal native disposition facts/bytes changed')
                    single_stream(path)
                self._validate()
                kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
                kernel.SetFileInformationByHandle.restype=wintypes.BOOL;value=wintypes.BOOL(True)
                need(kernel.SetFileInformationByHandle(deleting.handle,4,ctypes.byref(value),ctypes.sizeof(value)),
                     'Terminal exact native disposition refused')
                kernel_success=True # MUST precede all post-kernel journal I/O.
                self._record(definition,'pending',disposition_success=True)
                need(kernel.CloseHandle(deleting.handle),'Terminal exact native close failed');deleting.handle=None
                with os.scandir(path.parent) as names:need(path.name.casefold() not in {e.name.casefold() for e in names},
                    'Terminal native disposition did not settle absence')
                self._record(definition,'closed',native_close=True,observed_absent=True)
                return dict(removed=True,phase='closed',path=str(path))
            except Exception as error:
                if guard:guard.__exit__(None,None,None);guard=None
                if deleting:deleting.__exit__(None,None,None);deleting=None
                restored=False;reason=None
                if intent and not kernel_success:restored,reason=self._restore(definition,intent)
                if intent:
                    try:self._record(definition,'held',reason=str(error),kernel_success=kernel_success,
                                     security_restored=restored,restoration_error=reason)
                    except Exception:pass # Never roll back post-success ACLs to make a journal write work.
                return dict(removed=False,held=True,phase='held',path=str(path),kernel_success=kernel_success,
                            security_restored=restored,reason=str(error)+(('; '+reason) if reason else ''))
            finally:
                if guard:guard.__exit__(None,None,None)
                if deleting:deleting.__exit__(None,None,None)
    def finish(self):
        with self.lock:
            self._validate()
            for definition in self.members.values():
                proof=self._get(definition,'closed')
                need(proof and proof.get('native_close') is True and proof.get('observed_absent') is True,
                     'Terminal cleanup has outstanding members; registry retained')
                need(_positive_absence(definition['path']),'Unknown name arrived in selected namespace; retained')
            need(all(_positive_absence(path) for path in self.required_gone),
                 'Retained application/state still depends on external control records')
            need(winreg.QueryInfoKey(self.handle)[0]==0,'Unknown terminal registry subkey retained')
            self._put(self.handle,'Terminal',dict(schema=SCHEMA,phase='terminal',authority_sha256=self.authority_sha256,
                      selection_sha256=self.selection_sha256,all_selected_closed=True))
            # This precise, privately CREATE_NEW key owns ALL its VALUES for
            # its lifetime. A late value is covered by that narrow contract;
            # no such ownership is asserted for any subkey/shared parent.
            # After the final flush, recheck the actual retained key name. The
            # native deletion operates on that handle, never a reopened name.
            _assert_key(self.handle,self.native_registry_name)
            _delete_actual_key(self.handle) # Kernel atomically refuses subkeys.
            self.handle.Close();self.registry_handles.pop();self.handle=None
            winreg.FlushKey(self.registry_handles[-1])
            # Successful removal proves this owned key OBJECT was deleted.
            # A replacement at its former name is unrelated and must remain
            # visible to the consumer, rather than being called path absence.
            namespace_absent=None
            try:
                parent=self.registry_handles[-1]
                count=winreg.QueryInfoKey(parent)[0]
                if count<=MAX_MEMBERS:
                    names=[winreg.EnumKey(parent,index) for index in range(count)]
                    namespace_absent=self.transaction_id.casefold() not in {name.casefold() for name in names}
            except OSError:pass
            retained_records=[] if namespace_absent is True else [dict(path='HKCU\\'+self.registry_path,
                reason='An unrelated replacement record remains' if namespace_absent is False else
                       'The former registry location could not be checked',bytes=None)]
            self.finished=True;self.live=False
            return dict(complete=True,phase='terminal',registry_removed=True,transaction_id=self.transaction_id,
                        files_removed=sum(d['kind']=='file' for d in self.members.values()),
                        directories_removed=sum(d['kind']=='directory' for d in self.members.values()),
                        registry_key_deleted_by_handle=True,registry_value_ownership='private transaction key lifetime',
                        registry_object_removed=True,registry_namespace_absent=namespace_absent,
                        retained_registry_records=retained_records,
                        retained_registry_containers=['HKCU\\'+BASE,'HKCU\\'+BASE+'\\'+self.authority['installation_id']])
    def close(self):
        for handle in reversed(self.registry_handles):handle.Close()
        self.registry_handles=[];self.handle=None
        self.live=False;self.stack.close()
    def __exit__(self,*args):self.close()
