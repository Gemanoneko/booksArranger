"""Owned, external file-disposition journal; caller handles remain retained.

Implements BooksArranger_RuntimeDisposition_Contract_2026-11-13.md. No SQLite,
environment discovery, path-delete fallback, or remote journal is used.
"""
import base64
import contextlib
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import re
import threading
import uuid

from storage_relocation import _inside
from storage_relocation_operator import (Security,need,local_root,packed,digest,create_new,
    pinned_receipt,security_equivalent,bounded_json)
from lifecycle_fence_security import _delete_relaxed

SCHEMA='books-runtime-file-disposition-v1'
MAX_RECORD=256*1024


def _publish_record(path,record):
    raw=packed(record)
    need(0<len(raw)<=MAX_RECORD,'Runtime disposition journal record exceeds its recovery bound')
    return create_new(path,raw)


def _facts(held,*,pending=False):
    from native_io import kernel
    need(held.handle and kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)),
         'Disposition original native handle is unavailable')
    value=held.facts()
    need(value['links'] in ((0,1) if pending else (1,)) and not value['attributes']&(0x400|0x10),
         'Disposition requires one ordinary unique file')
    return value


def _local_provider(handle):
    from native_io import kernel
    serial=wintypes.DWORD();maximum=wintypes.DWORD();flags=wintypes.DWORD();fs=ctypes.create_unicode_buffer(261)
    api=kernel.GetVolumeInformationByHandleW
    api.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),ctypes.POINTER(wintypes.DWORD),wintypes.LPWSTR,wintypes.DWORD]
    api.restype=wintypes.BOOL
    need(api(handle,None,0,ctypes.byref(serial),ctypes.byref(maximum),ctypes.byref(flags),fs,len(fs)) and
         fs.value.upper()=='NTFS' and serial.value,'Unsupported disposition provider: verified local NTFS required')
    final=kernel.GetFinalPathNameByHandleW
    final.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD];final.restype=wintypes.DWORD
    path=ctypes.create_unicode_buffer(32768);size=final(handle,path,len(path),1)
    need(size and size<len(path) and path.value.startswith('\\\\?\\Volume{') and
         len(path.value)>49 and path.value[47:49]=='}\\',
         'Unsupported disposition provider: remote/unverifiable native volume')


def _load(path):
    from native_io import VerifiedFile
    from source_cleanup import single_stream
    with VerifiedFile(path) as held:
        need(held.facts()['links']==1 and 0<held.facts()['size']<=MAX_RECORD,'Runtime journal record is not bounded/unique')
        single_stream(path);raw=b''.join(held.chunks())
    return bounded_json(raw,digest(raw)),digest(raw)


def _absent(path):
    with os.scandir(path.parent) as entries:
        return path.name.casefold() not in {entry.name.casefold() for entry in entries}


class SecurityHandle:
    """Security-only access, compatible with caller's retained WRITE/DELETE."""
    directory=False
    def __init__(self,path):self.path=Path(path).absolute();self.handle=None
    def __enter__(self):
        from native_io import kernel,FileInfo,VerifiedFile
        self.handle=kernel.CreateFileW(str(self.path),0x60080,7,None,3,0x00200000,None)
        if self.handle==ctypes.c_void_p(-1).value:
            self.handle=None;need(False,'Cannot retain disposition security-only handle')
        try:
            self.info=FileInfo();need(kernel.GetFileInformationByHandle(self.handle,ctypes.byref(self.info)) and
                not self.info.attributes&(0x400|0x10),'Disposition security handle type changed')
            view=VerifiedFile(self.path);view.handle=self.handle;view.info=self.info;self.facts=view.facts()
            need(self.facts['links']==1,'Disposition security handle is not unique');return self
        except BaseException:self.close();raise
    def close(self):
        from native_io import kernel
        if self.handle:
            need(kernel.CloseHandle(self.handle),'Disposition security handle did not close');self.handle=None
    def __exit__(self,*args):self.close()


class DispositionContext:
    def __init__(self,control_root,*,scopes,owner_handle,owner_identity,owner_path,owner_kind,catalog_identity=None,marker_validator=None):
        self.control_root=Path(control_root).absolute();self.scopes=tuple(Path(s).absolute() for s in scopes)
        self.owner_handle=owner_handle;self.owner_identity=list(owner_identity);self.owner_path=Path(owner_path).absolute()
        self.owner_kind=owner_kind;self.catalog_identity=catalog_identity
        self.marker_validator=marker_validator;self.previous_marker=None
        self.lock=threading.RLock();self.stack=contextlib.ExitStack();self.live=False;self.operations=set()
    def __enter__(self):
        from native_io import DirectoryBoundary
        from storage_relocation_operator import NativeItem
        with self.lock:
            need(not self.live and self.owner_kind in ('catalog','support') and self.scopes,'Explicit disposition owner/scopes required')
            local_root(self.control_root);local_root(self.owner_path)
            need(len(self.owner_identity)==3 and all(type(x) is int and x>=0 for x in self.owner_identity),
                 'Actual disposition owner native identity required')
            try:
                self.owner_boundary=self.stack.enter_context(DirectoryBoundary(self.owner_path.anchor,self.owner_path.parent))
                self._owner()
                # Refuse unsupported existing provider before creating a ledger.
                nearest=self.control_root
                while not nearest.exists():nearest=nearest.parent
                with NativeItem(nearest,directory=True) as parent:_local_provider(parent.handle)
                self.boundary=self.stack.enter_context(DirectoryBoundary(self.control_root.anchor,self.control_root,create=True))
                root=self.stack.enter_context(NativeItem(self.control_root,directory=True));_local_provider(root.handle)
                marker=dict(schema=SCHEMA,phase='context',owner_kind=self.owner_kind,owner_path=str(self.owner_path),
                    owner_identity=self.owner_identity,catalog_identity=self.catalog_identity,root=str(self.control_root),
                    root_identity=root.facts['identity'],ancestry=self.boundary.identities)
                # JSON round-trip canonicalizes native tuple ancestry.
                marker=bounded_json(packed(marker));self.marker=marker;self.marker_path=self.control_root/'context.json'
                if self.marker_path.exists():
                    previous,self.marker_sha256=_load(self.marker_path)
                    if previous!=marker:
                        need(callable(self.marker_validator) and self.marker_validator(
                            bounded_json(packed(previous)),bounded_json(packed(marker))) is True,
                            'Disposition context ownership/root binding changed')
                        self.previous_marker=previous
                else:self.marker_sha256=_publish_record(self.marker_path,marker)
                self.stack.enter_context(pinned_receipt(self.marker_path,self.marker_sha256))
                self.live=True;return self
            except BaseException:self.stack.close();raise
    def _owner(self):
        from native_io import kernel,FileInfo
        info=FileInfo()
        need(self.owner_handle and kernel.GetFileInformationByHandle(self.owner_handle,ctypes.byref(info)) and
             [info.volume,info.index_high,info.index_low]==self.owner_identity and info.links==1 and
             not info.attributes&(0x400|0x10),'Actual disposition owner handle changed/closed')
        # Granted data-write/delete access plus an ERROR_SHARING_VIOLATION
        # writer probe proves native ownership, not a path/PID or ACL denial.
        class Basic(ctypes.Structure):
            _fields_=[('attributes',wintypes.ULONG),('access',wintypes.ULONG),('handles',wintypes.ULONG),
                      ('pointers',wintypes.ULONG),('reserved',wintypes.ULONG*10)]
        nt=ctypes.WinDLL('ntdll');nt.NtQueryObject.argtypes=[wintypes.HANDLE,wintypes.ULONG,ctypes.c_void_p,wintypes.ULONG,ctypes.c_void_p]
        nt.NtQueryObject.restype=wintypes.LONG;basic=Basic()
        need(nt.NtQueryObject(self.owner_handle,0,ctypes.byref(basic),ctypes.sizeof(basic),None)>=0 and
             basic.access&(0x2|0x10000),'Disposition owner handle has no native writer/disposition authority')
        check=kernel.CreateFileW(str(self.owner_path),0x80,7,None,3,0x00200000,None)
        need(check!=ctypes.c_void_p(-1).value,'Disposition owner path cannot be matched to native handle')
        try:
            fresh=FileInfo();need(kernel.GetFileInformationByHandle(check,ctypes.byref(fresh)) and
                [fresh.volume,fresh.index_high,fresh.index_low]==self.owner_identity,'Disposition owner path was replaced')
        finally:kernel.CloseHandle(check)
        probe=kernel.CreateFileW(str(self.owner_path),0x40000000,7,None,3,0x00200000,None)
        error=ctypes.get_last_error()
        if probe!=ctypes.c_void_p(-1).value:kernel.CloseHandle(probe);need(False,'Disposition owner does not exclude a competing writer')
        need(error==32,'Disposition ownership cannot be proven by native sharing exclusion')
    def revalidate(self,path=None):
        need(self.live,'Disposition context is closed');self._owner();self.owner_boundary.revalidate();self.boundary.revalidate()
        if path is not None:
            path=Path(path).absolute()
            need(any(_inside(str(path),str(scope)) for scope in self.scopes),'File is outside explicit disposition scopes')
            need(not _inside(str(path),str(self.control_root)) and path!=self.owner_path,'Disposition target is its own owner/journal')
    def close(self):
        with self.lock:
            need(not self.operations,'Disposition context still has live prepared handles')
            self.live=False;self.stack.close()
    def __exit__(self,*args):self.close()


class PreparedDisposition:
    def __init__(self,held,context):
        self.held=held;self.context=context;self.handle=held.handle;self.path=Path(held.path).absolute()
        self.phase='new';self.security_handle=None;self.intent=None;self.intent_sha256=None
        self.kernel_success=False;self.operation_id=uuid.uuid4().hex;self.security=Security()
    def _record(self,phase,**values):
        record=dict(schema=SCHEMA,operation_id=self.operation_id,phase=phase,intent_sha256=self.intent_sha256,**values)
        path=self.context.control_root/(self.operation_id+'.'+phase+'.json')
        if path.exists():
            previous,sha=_load(path)
            need(previous==record or phase=='held' and previous.get('intent_sha256')==self.intent_sha256,
                 'Runtime disposition journal phase changed');return sha
        return _publish_record(path,record)
    def _restore(self):
        if not self.intent or not self.security_handle:return False,'Original security intent/handle unavailable'
        try:
            need(self.held.handle==self.handle and _facts(self.held)==self.intent['facts'] and
                 self.held.sha256()==self.intent['sha256'],'Original disposition bytes/native handle changed')
            current=self.security.capture(self.security_handle);original=self.intent['original_security']
            if security_equivalent(current,original):return True,None
            acl=self.security.captured_acl(current);expected=base64.b64decode(self.intent['expected_acl'],validate=True)
            need(current['protected'] and current['sddl'].partition('D:')[0]==original['sddl'].partition('D:')[0] and
                 acl in (expected,_delete_relaxed(expected)) and self.security.has_write_fence(self.security_handle,current,include_delete=False),
                 'Foreign changed security retained; restoration refused')
            self.security.restore(self.security_handle,original);return True,None
        except Exception as error:return False,str(error)
    def authorize(self,held):
        from source_cleanup import single_stream
        with self.context.lock:
            self.context.revalidate(self.path)
            need(self.phase in ('prepared','authorized') and held is self.held and held.handle==self.handle,
                 'Prepared disposition does not authorize this exact live handle')
            need(_facts(held)==self.intent['facts'] and held.sha256()==self.intent['sha256'],'Disposition target native facts/bytes changed')
            current=self.security.capture(self.security_handle)
            need(current['protected'] and self.security.captured_acl(current)==base64.b64decode(self.intent['expected_acl'],validate=True) and
                 current['sddl'].partition('D:')[0]==self.intent['original_security']['sddl'].partition('D:')[0] and
                 self.security.has_write_fence(self.security_handle,current),'Disposition write/ADS fence changed')
            single_stream(self.path);self.phase='authorized';return self
    def mark_pending(self):
        # Core calls this IMMEDIATELY after SetDisposition returns SUCCESS.
        self.kernel_success=True;self.phase='kernel-success'
        with self.context.lock:
            self.context.revalidate(self.path)
            self._record('pending',facts=self.intent['facts'],sha256=self.intent['sha256'])
            self.phase='pending'
    def abort(self,error):
        with self.context.lock:
            if self.phase in ('closed','aborted'):return
            if self.kernel_success:
                self.phase='kernel-success';self._record('held',reason=str(error),restore_forbidden=True);return
            restored,reason=self._restore();self.phase='aborted'
            try:
                if self.intent:self._record('held',reason=str(error),restored=restored,restoration_error=reason)
            finally:
                if self.security_handle:self.security_handle.close();self.security_handle=None
                self.context.operations.discard(self)
    def close(self):
        from native_io import kernel
        with self.context.lock:
            if self.phase in ('closed','aborted'):return
            if not self.kernel_success:self.abort('Prepared disposition closed before successful native disposition');return
            need(self.held.handle==self.handle and self.handle,'Disposition original handle was replaced/closed without native proof')
            self.context.revalidate(self.path)
            closing=_facts(self.held,pending=True)
            # NTFS reports link count zero after successful SetDisposition.
            # This narrow, kernel-success-only transition does not authorize a
            # different identity or change the immutable original receipt.
            need(dict(closing,links=self.intent['facts']['links'])==self.intent['facts'] and self.held.sha256()==self.intent['sha256'],
                 'Disposition close ticket no longer names the exact original native bytes')
            # Own the actual original CloseHandle, never accept a caller bool.
            need(kernel.CloseHandle(self.handle),'Disposition original native CloseHandle failed')
            self.held.handle=None
            if self.security_handle:self.security_handle.close();self.security_handle=None
            try:
                self.context.revalidate(self.path)
                need(_absent(self.path),'Disposition native close did not establish namespace absence')
                self._record('closed',facts=self.intent['facts'],closed_native_facts=closing,
                             sha256=self.intent['sha256'],native_close=True,observed_absent=True)
                self.phase='closed'
            except BaseException:
                self.phase='held';raise
            finally:self.context.operations.discard(self)


def prepare_disposition(held,context):
    from source_cleanup import single_stream
    prepared=PreparedDisposition(held,context)
    with context.lock:
        context.revalidate(prepared.path);_local_provider(held.handle);local_root(prepared.path)
        need(getattr(held,'delete',False),'Disposition requires the caller\'s existing DELETE handle')
        try:
            facts=_facts(held);single_stream(prepared.path)
            prepared.security_handle=SecurityHandle(prepared.path).__enter__()
            need(prepared.security_handle.facts['identity']==facts['identity'],'Disposition security handle belongs to another native object')
            original=prepared.security.capture(prepared.security_handle)
            expected=prepared.security.planned_write_fence_acl(original,False)
            intent=dict(schema=SCHEMA,operation_id=prepared.operation_id,phase='intent',owner_kind=context.owner_kind,
                owner_path=str(context.owner_path),owner_identity=context.owner_identity,catalog_identity=context.catalog_identity,
                context_sha256=context.marker_sha256,current_context_sha256=digest(packed(context.marker)),
                path=str(prepared.path),facts=facts,sha256=held.sha256(),
                original_security=original,expected_acl=base64.b64encode(expected).decode('ascii'))
            prepared.intent=intent
            prepared.intent_sha256=digest(packed(intent))
            _publish_record(context.control_root/(prepared.operation_id+'.intent.json'),intent)
            prepared.security.apply_planned_write_fence(prepared.security_handle,original,expected)
            single_stream(prepared.path)
            prepared._record('fenced',expected_acl=intent['expected_acl']);prepared.phase='prepared'
            context.operations.add(prepared);return prepared
        except BaseException as error:
            prepared.abort(error);raise


def recover(context):
    """Restore this owner's exact remaining originals; absence alone is held."""
    from native_io import VerifiedFile,DirectoryBoundary
    from lifecycle_fence_security import restore_owned_fence
    result=dict(restored=[],held=[],removed=[],historical=[],retained=[])
    with context.lock:
        context.revalidate()
        members=list(context.control_root.iterdir())
        need(len(members)<=100000,'Runtime disposition ledger exceeds bounded recovery admission')
        for member in members:
            if member.name=='context.json':continue
            match=re.fullmatch(r'([0-9a-f]{32})\.(intent|fenced|pending|closed|held|retained)\.json',member.name)
            if not match or not (context.control_root/((match[1] if match else '')+'.intent.json')).is_file():
                result['held'].append(dict(receipt=str(member),reason='Unknown/orphan runtime disposition journal member retained'))
        for path in sorted(context.control_root.glob('*.intent.json')):
            try:
                intent,sha=_load(path);operation=intent['operation_id']
                need(intent.get('schema')==SCHEMA and intent.get('phase')=='intent' and path.name==operation+'.intent.json' and
                     intent.get('context_sha256')==context.marker_sha256,'Recovery intent context mismatch')
                current_owner=dict(owner_kind=context.owner_kind,owner_path=str(context.owner_path),
                                   owner_identity=context.owner_identity,catalog_identity=context.catalog_identity)
                fields=('owner_kind','owner_path','owner_identity','catalog_identity')
                historical=intent.get('current_context_sha256')!=digest(packed(context.marker))
                if historical:
                    need(context.previous_marker and intent.get('current_context_sha256')==digest(packed(context.previous_marker)) and
                         all(intent.get(k)==context.previous_marker.get(k) for k in fields),
                         'Recovery historical owner was not approved by active relocation validation')
                else:need(all(intent.get(k)==current_owner[k] for k in fields),'Recovery actual native owner differs')
                target=Path(intent['path'])
                original=intent['original_security'];security=Security();security.validate_capture(original)
                expected=base64.b64decode(intent['expected_acl'],validate=True)
                need(expected==security.planned_write_fence_acl(original,False),'Recovery intended security transition differs')
                for phase in ('fenced','pending','closed','held','retained'):
                    phase_path=context.control_root/(operation+'.'+phase+'.json')
                    if not phase_path.exists():continue
                    record,_=_load(phase_path)
                    need(record.get('schema')==SCHEMA and record.get('operation_id')==operation and
                         record.get('phase')==phase and record.get('intent_sha256')==sha,
                         'Recovery journal phase is malformed or belongs to another intent')
                    if phase=='fenced':need(record.get('expected_acl')==intent['expected_acl'],'Recovery fenced proof differs')
                    if phase in ('pending','closed','retained'):need(record.get('facts')==intent['facts'] and record.get('sha256')==intent['sha256'],
                                                        'Recovery disposition proof native facts differ')
                retained_path=context.control_root/(operation+'.retained.json')
                held_path=context.control_root/(operation+'.held.json')
                forbidden_restore=held_path.exists() and _load(held_path)[0].get('restore_forbidden') is True
                if retained_path.exists():
                    retained,_=_load(retained_path)
                    need(not forbidden_restore and not (context.control_root/(operation+'.pending.json')).exists() and
                         not (context.control_root/(operation+'.closed.json')).exists() and
                         retained.get('original_security_sha256')==digest(packed(original)) and
                         retained.get('observed_remaining') is True and retained.get('original_acl_verified') is True,
                         'Retained recovery cannot settle a native-success/pending disposition')
                    result['retained'].append(str(target));continue
                closed_path=context.control_root/(operation+'.closed.json')
                if closed_path.exists():
                    closed,_=_load(closed_path)
                    need(closed.get('schema')==SCHEMA and closed.get('operation_id')==operation and closed.get('phase')=='closed' and
                         closed.get('intent_sha256')==sha and closed.get('facts')==intent['facts'] and
                         closed.get('sha256')==intent['sha256'] and closed.get('native_close') is True and closed.get('observed_absent') is True,
                         'Recovery closed native disposition proof differs')
                    actual=closed.get('closed_native_facts') or {}
                    need(actual.get('links') in (0,1) and dict(actual,links=intent['facts']['links'])==intent['facts'],
                         'Recovery exact native close identity proof differs')
                    # This immutable proof concerns the OLD closed identity.
                    # Its staging parent may since have been legitimately
                    # retired, or its name reused. Reopening that name cannot
                    # improve the closed proof and grants no fresh authority.
                    result['historical' if historical else 'removed'].append(str(target));continue
                need(not historical,'Historical operation has no closed native proof; relocation recovery held')
                context.revalidate(target)
                need(not forbidden_restore and not (context.control_root/(operation+'.pending.json')).exists(),
                     'Native-success disposition requires explicit settlement, not ACL restoration')
                with DirectoryBoundary(target.anchor,target.parent),VerifiedFile(target) as held:
                    need(_facts(held)==intent['facts'] and held.sha256()==intent['sha256'],'Recovery remaining native file/bytes differ')
                    restored,reason=restore_owned_fence(target,intent['facts']['identity'],original,intent['expected_acl'])
                    need(restored,reason or 'Runtime security restoration refused')
                    with SecurityHandle(target) as security_handle:
                        need(security_equivalent(Security().capture(security_handle),original),
                             'Recovered original ACL changed before retained proof')
                    need(_facts(held)==intent['facts'] and held.sha256()==intent['sha256'],
                         'Recovered retained file identity/content changed')
                    _publish_record(context.control_root/(operation+'.retained.json'),dict(schema=SCHEMA,
                        operation_id=operation,phase='retained',intent_sha256=sha,facts=intent['facts'],
                        sha256=intent['sha256'],original_security_sha256=digest(packed(original)),
                        observed_remaining=True,original_acl_verified=True))
                result['restored'].append(str(target))
            except Exception as error:result['held'].append(dict(receipt=str(path),reason=str(error)))
    return result
