"""Offline, explicit storage-transfer transactions; never moves the shared tree.

The source/target catalog .lock objects are independent: this operator owns both
and retains a reversible native write fence on the original source. No operation
is enabled merely by parsing a manifest or by finding a same-named directory.
"""
import base64
import contextlib
import contextvars
import ctypes
from ctypes import wintypes
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid
from functools import wraps

from storage_relocation import (RelocationRefused, RECEIPT_CLASSES, parse_manifest,
                                _object, _root, _relative, _inside, _key)

PLAN_SCHEMA = 'books-storage-source-plan-v1'
FENCE_SCHEMA = 'books-storage-source-fence-v1'
ACTIVATION_SQL = '''CREATE TABLE IF NOT EXISTS storage_relocation_activation(
 catalog_id TEXT PRIMARY KEY,generation TEXT NOT NULL,manifest_sha256 TEXT NOT NULL,
 source_snapshot_sha256 TEXT NOT NULL,phase TEXT NOT NULL,revision INTEGER NOT NULL,
 source_fence_sha256 TEXT NOT NULL,target_root_identity TEXT NOT NULL)'''
VERIFICATION_SQL = '''CREATE TABLE IF NOT EXISTS storage_relocation_verification(
 catalog_id TEXT PRIMARY KEY,generation TEXT NOT NULL,manifest_sha256 TEXT NOT NULL,
 receipt_path TEXT NOT NULL,receipt_sha256 TEXT NOT NULL,verified_state_sha256 TEXT NOT NULL)'''
MAX_RECEIPT = 128 * 1024 * 1024
MAX_FILES = 100000
_DEADLINE = contextvars.ContextVar('books_relocation_operator_deadline', default=None)


def checkpoint():
    deadline = _DEADLINE.get()
    need(deadline is None or time.monotonic() < deadline, 'Offline relocation exceeded its 600-second operation bound')


def bounded_operation(function):
    @wraps(function)
    def run(*args, **kwargs):
        token = _DEADLINE.set(min(_DEADLINE.get() or float('inf'), time.monotonic() + 600))
        try:return function(*args, **kwargs)
        finally:_DEADLINE.reset(token)
    return run


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def need(condition, message):
    if not condition:
        raise RelocationRefused(message)


def security_equivalent(actual, expected, *, copied_target=False):
    """SetSecurityInfo may set SE_DACL_AUTO_INHERITED; permissions stay exact.

    Only that documented bookkeeping bit may differ. Owner, group, protection,
    ACE order/masks/SIDs and each ACE's inheritance flags remain byte-for-byte
    in the canonical SDDL comparison. The original full descriptor is retained.
    """
    def normalized(sddl):
        head, marker, tail = sddl.partition('D:')
        if not marker:return sddl
        flags, opening, entries = tail.partition('(')
        flags = flags.replace('AI', '')
        if copied_target:
            flags = flags.replace('P', '')
            def ace(match):
                fields = match.group(0)[1:-1].split(';')
                if len(fields) >= 2:fields[1] = fields[1].replace('ID', '')
                return '(' + ';'.join(fields) + ')'
            entries = re.sub(r'\([^()]*\)', ace, opening + entries)
            opening = ''
        return head + marker + flags + opening + entries
    return (not copied_target or actual['protected']) and normalized(actual['sddl']) == normalized(expected['sddl'])


def bounded_json(raw, sha256=None):
    need(isinstance(raw, bytes) and 0 < len(raw) <= MAX_RECEIPT, 'Bounded transaction receipt required')
    if sha256 is not None:
        need(digest(raw) == sha256, 'Transaction receipt fingerprint changed')
    try:
        return json.loads(raw.decode('utf8'), object_pairs_hook=_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              RelocationRefused('Non-finite transaction value refused')))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RelocationRefused('Transaction receipt is not strict UTF-8 JSON') from error


def _windows():
    need(os.name == 'nt', 'Offline relocation requires Windows native ownership')
    from native_io import kernel
    kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    kernel.GetDriveTypeW.restype = wintypes.UINT
    return kernel


def local_root(value):
    root = Path(_root(str(value)))
    kernel = _windows()
    need(kernel.GetDriveTypeW(root.anchor) == 3, 'Relocation requires a local fixed volume')
    return root


def create_new(path, raw):
    """Durable CREATE_NEW receipt under held ordinary ancestry; never replaces."""
    from native_io import DirectoryBoundary, VerifiedFile
    path = Path(path).absolute()
    with DirectoryBoundary(path.anchor, path.parent):
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_BINARY, 0o600)
        try:
            with os.fdopen(descriptor, 'wb', closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            os.close(descriptor)
        with VerifiedFile(path) as held:
            need(held.facts()['links'] == 1 and held.sha256() == digest(raw), 'New receipt readback failed')
    return digest(raw)


class NativeItem:
    """Actual retained object, with security-descriptor access and deny writers."""
    def __init__(self, path, *, directory=False, writable_security=False):
        self.path = Path(path).absolute()
        self.directory = directory
        self.writable_security = writable_security
        self.handle = None

    def __enter__(self):
        from native_io import FileInfo, VerifiedFile
        kernel = _windows()
        access = 0x20000 | 0x81 | (0x40000 if self.writable_security else 0)
        self.handle = kernel.CreateFileW(str(self.path), access, 1, None, 3,
                                        0x00200000 | (0x02000000 if self.directory else 0), None)
        if self.handle == ctypes.c_void_p(-1).value:
            self.handle = None
            raise RelocationRefused('Native item cannot exclude writers: ' + str(self.path) + ': ' +
                                    str(ctypes.WinError(ctypes.get_last_error())))
        try:
            self.info = FileInfo()
            need(kernel.GetFileInformationByHandle(self.handle, ctypes.byref(self.info)),
                 'Native object identity unavailable')
            need(not self.info.attributes & 0x400 and bool(self.info.attributes & 0x10) == self.directory,
                 'Reparse/wrong-type relocation object refused')
            self.view = VerifiedFile(self.path)
            self.view.handle = self.handle
            self.view.info = self.info
            self.facts = self.view.facts()
            need(self.directory or self.facts['links'] == 1, 'Hardlinked relocation file refused')
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def sha256(self):
        need(not self.directory, 'Directory has no content hash')
        value = hashlib.sha256()
        for block in self.view.chunks():checkpoint(); value.update(block)
        return value.hexdigest()

    def revalidate(self):
        from native_io import FileInfo
        kernel = _windows(); fresh = FileInfo()
        need(kernel.GetFileInformationByHandle(self.handle, ctypes.byref(fresh)), 'Native identity recheck failed')
        need((fresh.volume, fresh.index_high, fresh.index_low) == tuple(self.facts['identity']) and
             fresh.attributes == self.facts['attributes'], 'Native identity/attributes changed')

    def __exit__(self, *unused):
        if self.handle is not None:
            _windows().CloseHandle(self.handle)
            self.handle = None


class Security:
    """Capture/restore exact owner/group/DACL and apply an explicit write denial."""
    def __init__(self):
        _windows()
        self.api = ctypes.WinDLL('advapi32', use_last_error=True)
        self.local = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.GetSecurityInfo.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)]
        self.api.GetSecurityInfo.restype = wintypes.DWORD
        self.api.GetSecurityDescriptorLength.argtypes = [ctypes.c_void_p]
        self.api.GetSecurityDescriptorLength.restype = wintypes.DWORD
        self.api.GetSecurityDescriptorControl.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.WORD),
                                                        ctypes.POINTER(wintypes.DWORD)]
        self.api.GetSecurityDescriptorControl.restype = wintypes.BOOL
        self.api.GetSecurityDescriptorDacl.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.BOOL)]
        self.api.GetSecurityDescriptorDacl.restype = wintypes.BOOL
        self.api.SetSecurityInfo.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.DWORD,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        self.api.SetSecurityInfo.restype = wintypes.DWORD
        self.api.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD)]
        self.api.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
        self.local.LocalFree.argtypes = [ctypes.c_void_p]
        self.local.LocalFree.restype = ctypes.c_void_p

    def _sddl(self, descriptor):
        text = wintypes.LPWSTR(); length = wintypes.DWORD()
        need(self.api.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor, 1, 7,
             ctypes.byref(text), ctypes.byref(length)), 'Security descriptor cannot be serialized')
        try:return text.value
        finally:self.local.LocalFree(text)

    def capture(self, item):
        owner = ctypes.c_void_p(); group = ctypes.c_void_p(); dacl = ctypes.c_void_p()
        descriptor = ctypes.c_void_p()
        status = self.api.GetSecurityInfo(item.handle, 1, 7, ctypes.byref(owner), ctypes.byref(group),
                                        ctypes.byref(dacl), None, ctypes.byref(descriptor))
        need(status == 0, 'Cannot capture native security descriptor: ' + str(status))
        try:
            control = wintypes.WORD(); revision = wintypes.DWORD()
            need(self.api.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision)),
                 'Security descriptor controls unavailable')
            raw = ctypes.string_at(descriptor, self.api.GetSecurityDescriptorLength(descriptor))
            return {'bytes': base64.b64encode(raw).decode('ascii'), 'sddl': self._sddl(descriptor),
                    'protected': bool(control.value & 0x1000), 'sha256': digest(raw)}
        finally:self.local.LocalFree(descriptor)

    def has_write_fence(self, item, captured=None, *, include_delete=True):
        captured = captured or self.capture(item)
        if not captured['protected']:return False
        raw = base64.b64decode(captured['bytes'], validate=True)
        memory = ctypes.create_string_buffer(raw)
        present = wintypes.BOOL(); defaulted = wintypes.BOOL(); dacl = ctypes.c_void_p()
        if not self.api.GetSecurityDescriptorDacl(memory, ctypes.byref(present), ctypes.byref(dacl),
                                                 ctypes.byref(defaulted)) or not present.value or not dacl:
            return False
        class AclSize(ctypes.Structure):
            _fields_ = [('count', wintypes.DWORD), ('used', wintypes.DWORD), ('free', wintypes.DWORD)]
        self.api.GetAclInformation.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.c_int]
        self.api.GetAclInformation.restype = wintypes.BOOL
        self.api.GetAce.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
        self.api.GetAce.restype = wintypes.BOOL
        self.api.IsWellKnownSid.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.api.IsWellKnownSid.restype = wintypes.BOOL
        size = AclSize()
        if not self.api.GetAclInformation(dacl, ctypes.byref(size), ctypes.sizeof(size), 2) or size.count > 4096:
            return False
        required = 0x10156 if item.directory else 0x10116
        if not include_delete:required &= ~0x10000
        for index in range(size.count):
            ace = ctypes.c_void_p()
            if not self.api.GetAce(dacl, index, ctypes.byref(ace)):return False
            header = ctypes.string_at(ace, 8)
            mask = int.from_bytes(header[4:8], 'little')
            if header[0] == 1 and header[1] == 0 and mask & required == required and \
                    self.api.IsWellKnownSid(ace.value + 8, 1):
                return True
        return False

    def restore(self, item, original, *, copied_target=False):
        raw = self.validate_capture(original)
        memory = ctypes.create_string_buffer(raw)
        present = wintypes.BOOL(); defaulted = wintypes.BOOL(); dacl = ctypes.c_void_p()
        need(self.api.GetSecurityDescriptorDacl(memory, ctypes.byref(present), ctypes.byref(dacl),
             ctypes.byref(defaulted)) and present.value, 'Original DACL is absent/unsupported')
        flags = 4 | (0x80000000 if original['protected'] or copied_target else 0x20000000)
        status = self.api.SetSecurityInfo(item.handle, 1, flags, None, None, dacl, None)
        need(status == 0, 'Cannot restore native DACL: ' + str(status))
        need(security_equivalent(self.capture(item), original, copied_target=copied_target),
             'Restored security descriptor differs')

    def validate_capture(self, captured):
        need(isinstance(captured,dict) and set(captured)=={'bytes','sddl','protected','sha256'} and
            isinstance(captured['sddl'],str) and type(captured['protected']) is bool,
            'Captured security descriptor shape is invalid')
        raw=base64.b64decode(captured['bytes'],validate=True)
        need(20<=len(raw)<=65536 and raw[0]==1 and int.from_bytes(raw[2:4],'little')&0x8000 and
            digest(raw)==captured['sha256'],'Captured relative security descriptor is malformed or changed')
        memory=ctypes.create_string_buffer(raw)
        nt=ctypes.WinDLL('ntdll');nt.RtlValidRelativeSecurityDescriptor.argtypes=[ctypes.c_void_p,wintypes.ULONG,wintypes.ULONG]
        nt.RtlValidRelativeSecurityDescriptor.restype=ctypes.c_ubyte
        need(nt.RtlValidRelativeSecurityDescriptor(memory,len(raw),7),
            'Captured security descriptor component bounds are invalid')
        need(self._sddl(memory)==captured['sddl'] and bool(int.from_bytes(raw[2:4],'little')&0x1000)==captured['protected'],
            'Captured security descriptor text/control differs from its bounded bytes')
        return raw

    def captured_acl(self,captured):
        memory=ctypes.create_string_buffer(self.validate_capture(captured))
        present=wintypes.BOOL();defaulted=wintypes.BOOL();pointer=ctypes.c_void_p()
        need(self.api.GetSecurityDescriptorDacl(memory,ctypes.byref(present),ctypes.byref(pointer),ctypes.byref(defaulted)) and
            present.value and pointer,'Captured DACL is unavailable')
        header=ctypes.string_at(pointer,8);length=int.from_bytes(header[2:4],'little')
        need(8<=length<=65535,'Captured DACL bounds are invalid')
        return ctypes.string_at(pointer,length)

    def planned_write_fence_acl(self, original, directory):
        """Compute the exact intended DACL BEFORE any security mutation."""
        # Explicit DENY for Everyone, without inheritance or changing owner. The
        # exact original descriptor remains durable rollback material.
        class Trustee(ctypes.Structure):
            _fields_ = [('multiple', ctypes.c_void_p), ('operation', ctypes.c_int),
                        ('form', ctypes.c_int), ('type', ctypes.c_int), ('name', ctypes.c_void_p)]
        class Access(ctypes.Structure):
            _fields_ = [('permissions', wintypes.DWORD), ('mode', ctypes.c_int),
                        ('inheritance', wintypes.DWORD), ('trustee', Trustee)]
        self.api.ConvertStringSidToSidW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
        self.api.ConvertStringSidToSidW.restype = wintypes.BOOL
        sid = ctypes.c_void_p()
        need(self.api.ConvertStringSidToSidW('S-1-1-0', ctypes.byref(sid)), 'Everyone SID unavailable')
        raw = self.validate_capture(original); memory = ctypes.create_string_buffer(raw)
        present = wintypes.BOOL(); defaulted = wintypes.BOOL(); dacl = ctypes.c_void_p()
        need(self.api.GetSecurityDescriptorDacl(memory, ctypes.byref(present), ctypes.byref(dacl),
             ctypes.byref(defaulted)) and present.value, 'Cannot preserve source DACL')
        entry = Access(0x10156 if directory else 0x10116, 3, 0,
                       Trustee(None, 0, 0, 5, sid))
        replacement = ctypes.c_void_p()
        self.api.SetEntriesInAclW.argtypes = [wintypes.ULONG, ctypes.POINTER(Access),
                                            ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        self.api.SetEntriesInAclW.restype = wintypes.DWORD
        try:
            status = self.api.SetEntriesInAclW(1, ctypes.byref(entry), dacl, ctypes.byref(replacement))
            need(status == 0, 'Cannot construct explicit source write fence: ' + str(status))
            header=ctypes.string_at(replacement,8);length=int.from_bytes(header[2:4],'little')
            need(8<=length<=65535,'Computed native write-fence ACL is malformed')
            result=bytearray(ctypes.string_at(replacement,length))
            # SetSecurityInfo(PROTECTED_DACL) converts existing inherited ACEs
            # to explicit ones. Persist that exact intended transition before
            # mutation; every ACE mask/SID/order and other flag stays strict.
            offset=8;count=int.from_bytes(result[4:6],'little')
            for _ in range(count):
                size=int.from_bytes(result[offset+2:offset+4],'little')
                need(size>=8 and offset+size<=length,'Computed source fence ACE is malformed')
                result[offset+1]&=~0x10
                offset+=size
            return bytes(result)
        finally:
            if replacement:self.local.LocalFree(replacement)
            self.local.LocalFree(sid)

    def deny_writes(self, item):
        original=self.capture(item)
        expected=self.planned_write_fence_acl(original,item.directory)
        return original,self.apply_planned_write_fence(item,original,expected)

    def apply_planned_write_fence(self,item,original,expected):
        need(expected==self.planned_write_fence_acl(original,item.directory),
            'Intended write-fence ACL changed before mutation')
        need(security_equivalent(self.capture(item),original),
            'Security changed after the durable intent; foreign permissions retained')
        acl=ctypes.create_string_buffer(expected)
        status=self.api.SetSecurityInfo(item.handle,1,4|0x80000000,None,None,acl,None)
        need(status==0,'Cannot apply native source write fence: '+str(status))
        applied=self.capture(item)
        need(applied['sddl']!=original['sddl'] and applied['protected'] and
            applied['sddl'].partition('D:')[0]==original['sddl'].partition('D:')[0] and
            self.captured_acl(applied)==expected and self.has_write_fence(item,applied),
            'Applied write fence differs from the persisted intended security transition')
        return applied


def _readonly_database(path,*,immutable=False):
    # immutable is reserved for an independently pinned CLOSED standalone
    # backup, never a live source/target with potentially committed WAL state.
    db = sqlite3.connect(Path(path).absolute().as_uri() + '?mode=ro'+('&immutable=1' if immutable else ''), uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON'); db.execute('PRAGMA temp_store=MEMORY')
    return db


def classify_historical_files(database, *, managed_root=None,logical_catalog=None,index_root=None,immutable=False):
    """Typed DB path consumer registry; no filename-based blanket authority."""
    logical_catalog=Path(logical_catalog or database).absolute()
    physical_index=Path(index_root or Path(database).parent/'openlibrary-index')
    logical_index=logical_catalog.parent/'openlibrary-index'
    result = {str(logical_catalog): {'catalog-storage'}}; held = []
    managed_root = str(managed_root or Path(database).absolute().parent)
    def add(path, *classes):
        if not isinstance(path, str) or not ntpath.isabs(path):return
        if _inside(path,str(physical_index)):
            path=str(logical_index/ntpath.relpath(path,str(physical_index)))
        result.setdefault(path, set()).update(classes)
    add(str(logical_catalog)+'.lock','catalog-owner-lock')
    from runtime_disposition_ledger import closed_ledger_members
    for member in closed_ledger_members(physical_index.parent/'file-disposition-ledger'):
        add(str(logical_catalog.parent/'file-disposition-ledger'/Path(member['path']).name),'file-disposition-control')
    with contextlib.closing(_readonly_database(database,immutable=immutable)) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'output_relocations' in tables:
            for row in db.execute('SELECT publication_id,stage FROM output_relocations'):
                if row['stage']!='complete':
                    held.append({'class':'output_relocations','publication_id':row['publication_id'],'state':row['stage'],
                        'reason':'Finish or explicitly reconcile the existing offline publication operation at its source catalog before storage relocation; its reviewed catalog-native plan is immutable'})
        for table, pathcolumn, classes in (
            ('working_files', 'path', ('working-file',)),
            ('storage_cleanup_files', 'path', ('cleanup-file',)),
            ('cleanup_members', 'backup', ('recovery-copy',)),
            ('owned_artifacts', 'path', ('staging-artifact',))):
            if table not in tables:continue
            columns = {row[1] for row in db.execute('PRAGMA table_info("' + table + '")')}
            if pathcolumn not in columns:
                held.append({'class': table, 'reason': 'Unrecognized path schema'}); continue
            for row in db.execute('SELECT * FROM "' + table + '"'):
                add(row[pathcolumn], *classes)
                if table == 'storage_cleanup_files' and row['kind'] == 'recovery':
                    add(row[pathcolumn], 'recovery-copy')
        if 'producer_recovery_checkpoints' in tables:
            for record in db.execute('SELECT state,native FROM producer_recovery_checkpoints'):
                if record['state'] == 'disposed':continue  # terminal immutable history; no surviving artifact bridge
                if record['state']!='isolated_retained':
                    held.append({'class':'producer_recovery_checkpoints','state':record['state'],
                        'reason':'Complete supported source isolation before relocation; prepared/origin uncertainty is not copy authority'})
                    continue
                try:
                    native = json.loads(record['native'])
                    need(isinstance(native, dict) and native.get('schema') == 'books-unadopted-attempt-fence-v1' and
                         native.get('ownership_authority') is False and isinstance(native.get('files'), list),
                         'Unknown retained source proof')
                    for item in native['files']:
                        need(isinstance(item, dict) and isinstance(item.get('path'), str) and
                             isinstance(item.get('facts'), dict), 'Unknown retained source file proof')
                        add(item['path'], 'retained-source')
                except (ValueError, TypeError, KeyError):
                    held.append({'class': 'producer_recovery_checkpoints',
                                 'reason': 'Unknown whole retained provenance proof; files preserved'})
        if 'inplace_edits' in tables:
            for edit in db.execute('SELECT * FROM inplace_edits'):
                try:
                    from inplace_m4b import _intent
                    intent = _intent(dict(edit))
                    need(edit['state'] == 'published' and isinstance(intent, dict) and
                         intent.get('path') == edit['path'] and isinstance(intent.get('destination'), str) and
                         not _inside(edit['path'], managed_root) and not _inside(intent['destination'], managed_root),
                         'Unresolved or moved in-place repair proof')
                    job = db.execute('SELECT state,output FROM audio_jobs WHERE job_id=?', (edit['job_id'],)).fetchone()
                    output = json.loads(job['output']) if job and job['output'] else None
                    need(job and job['state'] == 'completed' and isinstance(output, dict) and
                         isinstance(intent.get('output_sha256'), str) and
                         re.fullmatch('[a-f0-9]{64}', intent['output_sha256']) and
                         output.get('sha256') == intent['output_sha256'] and
                         isinstance(output.get('final_path'), str) and
                         not _inside(output['final_path'], managed_root),
                         'Terminal in-place repair has no matching completed unmoved output')
                    # The Z:/library receipt stays strictly validated by existing
                    # code. Relocation neither opens it nor rewrites its proof.
                except (ValueError, TypeError, KeyError) as error:
                    held.append({'class': 'inplace_edits', 'job_id': edit['job_id'], 'state': edit['state'],
                                 'reason': 'Whole repair proof needs typed core adapter: ' + str(error)})
        if 'audiobook_replacement_retirements' in tables:
            for row in db.execute('SELECT replacement_id,original_path,recovery_json,state FROM audiobook_replacement_retirements'):
                if not row['recovery_json']:continue
                try:
                    recovery=json.loads(row['recovery_json']);path=recovery['path']
                    expected=logical_catalog.parent/'replacement-recovery'/row['replacement_id']/(digest(row['original_path'].encode('utf8'))+'.m4b')
                    need(str(uuid.UUID(row['replacement_id']))==row['replacement_id'] and _key(path)==_key(str(expected)) and
                        isinstance(recovery.get('facts'),dict) and recovery.get('sha256') and
                        re.fullmatch('[a-f0-9]{64}',recovery['sha256']) and type(recovery.get('size')) is int and
                        recovery['size']>=0 and recovery['facts'].get('size')==recovery['size'] and
                        not recovery.get('copy_pending'),'Unclosed or unknown replacement recovery proof')
                    if recovery.get('purged_at'):
                        need(not os.path.lexists(path),'Purged replacement recovery has reappeared; preserve it')
                        continue
                    add(path,'recovery-copy')
                except (ValueError,TypeError,KeyError,OSError) as error:
                    held.append({'class':'audiobook_replacement_retirements','state':row['state'],
                        'reason':'Replacement recovery needs source-side reconciliation: '+str(error)})
    index = physical_index
    if index.exists():
        from native_io import DirectoryBoundary, VerifiedFile
        from source_cleanup import single_stream
        with DirectoryBoundary(index.anchor, index):
            for owner in sorted(index.glob('*.owner.json')):
                try:
                    with VerifiedFile(owner) as protected:
                        need(protected.facts()['links'] == 1 and protected.facts()['size'] <= 65536,
                             'Index ownership receipt is not unique bounded data')
                        single_stream(owner); receipt = bounded_json(b''.join(protected.chunks()))
                    need(set(receipt) == {'binding', 'identities'} and isinstance(receipt['binding'], str) and
                         (receipt['binding'] == 'openlibrary-active-v1' or
                          re.fullmatch('[a-f0-9]{64}', receipt['binding'])) and
                         isinstance(receipt['identities'], list) and len(receipt['identities']) == 2,
                         'Unknown index ownership schema')
                    for identity in receipt['identities']:
                        need(isinstance(identity, list) and len(identity) == 3 and
                             all(type(n) is int and n >= 0 for n in identity), 'Unknown index native identity')
                    leaf = owner.with_name(owner.name[:-len('.owner.json')])
                    journal = leaf.with_name(leaf.name + '-journal')
                    if leaf.exists():add(str(leaf), 'index-leaf')
                    if journal.exists():add(str(journal), 'index-journal')
                    if leaf.name.startswith('pending-'):
                        ready = leaf.with_name(leaf.name.replace('pending-', 'index-', 1))
                        complete = ready.with_name(ready.name + '.complete.json')
                        if ready.exists():
                            with VerifiedFile(complete) as protected:
                                need(protected.facts()['links'] == 1 and protected.facts()['size'] <= 65536,
                                     'Index completion receipt is invalid')
                                single_stream(complete); done = bounded_json(b''.join(protected.chunks()))
                            need(set(done) == {'token', 'sha256', 'size', 'identity'} and
                                 done['token'] == receipt['binding'] and done['identity'] == receipt['identities'][0],
                                 'Index completion/owner provenance differs')
                            add(str(ready), 'index-leaf')
                except (ValueError, TypeError, OSError, KeyError) as error:
                    held.append({'class': 'openlibrary-index', 'path': str(owner),
                                 'reason': 'Unknown/invalid index provenance: ' + str(error)})
    return {path: sorted(classes) for path, classes in result.items()}, held


class SourceFenceLease:
    """Retained original-source read fence, bound to its renamed physical root."""
    def __init__(self, path, expected_sha256, *, allow_restored=False):
        self.path = Path(path).absolute()
        self.expected_sha256 = expected_sha256
        self.stack = contextlib.ExitStack()
        self.items = []
        self.live = False
        self.allow_restored = allow_restored

    def __enter__(self):
        from native_io import DirectoryBoundary, VerifiedFile
        from source_cleanup import single_stream
        try:
            self.stack.enter_context(DirectoryBoundary(self.path.anchor, self.path.parent))
            self.descriptor = self.stack.enter_context(VerifiedFile(self.path))
            need(self.descriptor.facts()['links'] == 1 and self.descriptor.facts()['size'] <= MAX_RECEIPT,
                 'Source fence receipt is linked/oversized')
            single_stream(self.path)
            self.receipt = bounded_json(b''.join(self.descriptor.chunks()), self.expected_sha256)
            required = {'schema', 'generation', 'catalog_id', 'source_snapshot_sha256', 'source_original', 'target_root',
                        'source_root_identity', 'scopes', 'catalog_relative', 'items', 'source_plan_sha256'}
            need(isinstance(self.receipt, dict) and set(self.receipt) == required and
                 self.receipt['schema'] == FENCE_SCHEMA, 'Unsupported source write-fence receipt')
            for key in ('generation', 'catalog_id'):
                need(str(uuid.UUID(self.receipt[key])) == self.receipt[key], 'Malformed source fence identity')
            need(len(self.receipt['source_snapshot_sha256']) == 64, 'Source snapshot identity missing')
            self.root = local_root(self.receipt['source_original'])
            self.stack.enter_context(DirectoryBoundary(self.root.anchor, self.root))
            self.root_item = self.stack.enter_context(NativeItem(self.root, directory=True))
            need(self.root_item.facts['identity'] == self.receipt['source_root_identity'],
                 'Original source root was replaced; logical alias is not source proof')
            scopes = tuple(_relative(s) for s in self.receipt['scopes'])
            need(scopes and len(scopes) <= 32, 'Source fence has no bounded managed scopes')
            records = self.receipt['items']
            need(isinstance(records, list) and 0 < len(records) <= MAX_FILES,
                 'Source fence item count invalid')
            seen = set(); security = Security()
            for record in records:
                checkpoint()
                need(isinstance(record, dict) and set(record) == {'relative', 'kind', 'identity',
                     'original_security', 'applied_security'}, 'Malformed source fence item')
                relative = _relative(record['relative'])
                need(any(_inside(relative, scope) for scope in scopes), 'Source fence item escapes owned scope')
                need(_key(relative) not in seen and record['kind'] in ('file', 'directory'),
                     'Duplicate/wrong-type source fence entry')
                seen.add(_key(relative))
                path = self.root / relative
                self.stack.enter_context(DirectoryBoundary(path.anchor, path.parent))
                item = self.stack.enter_context(NativeItem(path, directory=record['kind'] == 'directory'))
                need(item.facts['identity'] == record['identity'], 'Original fenced source identity changed')
                captured = security.capture(item)
                fenced = captured['sddl'] == record['applied_security']['sddl'] and security.has_write_fence(item, captured)
                restored = self.allow_restored and security_equivalent(captured, record['original_security'])
                need(fenced or restored,
                     'Original source write fence is no longer installed')
                self.items.append((item, record))
            for scope in scopes:
                need(_key(scope) in seen, 'Managed source root has no write fence')
            # The receipt covers every namespace entry, not just named files.
            # Unknown entries can never remain writable outside the source fence.
            with contextlib.ExitStack() as census:
                directories, files, _ = _scan(self.root, scopes, census, hash_files=False)
                namespace = set(files) | {key for key in directories if
                    any(_inside(key, scope) for scope in scopes)}
                need(namespace == seen, 'Source fence membership changed or contains an unfenced entry')
            catalog = _relative(self.receipt['catalog_relative'])
            lock = _key(catalog + '.lock')
            need(lock in seen and _key(catalog) in seen, 'Source catalog and owner lock must both be fenced')
            self.heartbeat = [(item, record) for item, record in self.items if
                              _key(record['relative']) == lock or _key(record['relative']) in {_key(s) for s in scopes}]
            self.security = security
            self.live = True
            return self
        except BaseException:
            self.stack.close()
            raise

    def revalidate(self):
        need(self.live, 'Original source fence lease is closed')
        self.root_item.revalidate()
        # Every file/list-directory handle remains open denying WRITE/DELETE.
        # Recheck the admission/creation fences without reopening or rehashing
        # thousands of frozen original files for every historical comparison.
        for item, record in self.heartbeat:
            item.revalidate()
            captured = self.security.capture(item)
            need(captured['sddl'] == record['applied_security']['sddl'] or
                 self.allow_restored and security_equivalent(captured, record['original_security']),
                 'Original source admission fence changed')

    def __exit__(self, *unused):
        self.live = False
        return self.stack.__exit__(*unused)


def verify_source_fence(path, expected_sha256):
    """Caller retains this context manager through its active target owner lease."""
    return SourceFenceLease(path, expected_sha256)


@contextlib.contextmanager
def _catalog_owner(database):
    """Actual .lock ownership even when a copied source-fence DACL is present."""
    from native_io import DirectoryBoundary
    database = Path(database).absolute()
    lock = Path(str(database) + '.lock')
    need(lock.is_file(), 'Existing catalog ownership file is required; not created by relocation')
    with DirectoryBoundary(lock.anchor, lock.parent), NativeItem(lock, writable_security=True) as owned:
        yield owned


def _closed_state(database):
    """Persisted quiescence supplements actual native ownership; never creates closure."""
    states = {}; blockers = []
    with contextlib.closing(_readonly_database(database)) as db:
        need(db.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'Source catalog integrity check failed')
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        need({'jobs', 'queue', 'files'}.issubset(tables), 'Unrecognized Books Arranger catalog')
        columns = {row[1] for row in db.execute('PRAGMA table_info(files)')}
        need({'root','path','size','modified','kind'}.issubset(columns),
             'Unsupported Books Arranger catalog file schema')
        if 'storage_relocation_activation' in tables:
            need(not db.execute('SELECT 1 FROM storage_relocation_activation LIMIT 1').fetchone(),
                 'Catalog already has a relocation generation; use its reviewed handoff rather than a new source plan')
        for table, column, active in (
            ('audio_jobs', 'state', {'running'}),
            ('jobs', 'state', {'running', 'scanning'}), ('source_cleanup', 'state', {'removing', 'copying', 'checking'}),
            ('inplace_edits', 'state', {'editing', 'writing', 'publishing'})):
            if table not in tables:continue
            columns = {row[1] for row in db.execute('PRAGMA table_info("' + table + '")')}
            need(column in columns, 'Unsupported catalog state schema: ' + table)
            values = [list(row) for row in db.execute('SELECT "' + column + '",count(*) FROM "' + table +
                                                     '" GROUP BY "' + column + '"')]
            states[table] = values
            for state, count in values:
                if str(state).casefold() in active:
                    blockers.append({'table': table, 'state': state, 'count': count})
        if 'working_attempts' in tables:
            columns = {row[1] for row in db.execute('PRAGMA table_info(working_attempts)')}
            need({'job_id','attempt_id','state','producer'}.issubset(columns), 'Unsupported producer ownership schema')
            states['working_attempts'] = [list(row) for row in db.execute(
                'SELECT state,producer,count(*) FROM working_attempts GROUP BY state,producer')]
            for attempt in db.execute("SELECT * FROM working_attempts WHERE producer IN ('active','open','producing')"):
                try:
                    need(attempt['state'] == 'isolated_retained', 'Producer has no terminal retained-disposal state')
                    _prove_disposed_attempt(db, database, attempt['job_id'], attempt['attempt_id'])
                except (ValueError, OSError, KeyError, TypeError) as error:
                    blockers.append({'table':'working_attempts','state':attempt['state'],
                                     'producer':attempt['producer'],'job_id':attempt['job_id'],
                                     'reason':str(error)})
    need(not blockers, 'Catalog has active/unclosed obligations: ' + json.dumps(blockers))
    return states


def _prove_empty_owned_stage(stage, data_root):
    from native_io import DirectoryBoundary
    stage, data_root = Path(stage), Path(data_root)
    need(stage.is_relative_to(data_root) and stage != data_root, 'Retained stage escapes app-owned data root')
    with contextlib.ExitStack() as held:
        current = data_root
        held.enter_context(DirectoryBoundary(current.anchor, current))
        for part in stage.relative_to(data_root).parts:
            with os.scandir(current) as entries:present = {entry.name for entry in entries}
            if part not in present:return  # positive ordinary parent listing proves this exact child absent
            current = current / part
            held.enter_context(DirectoryBoundary(current.anchor, current))
        with os.scandir(stage) as entries:
            need(not any(entries), 'Disposed retained attempt has remaining/unknown stage files')


def _prove_disposed_attempt(db, database, job_id, attempt_id):
    """Existing independently authenticated disposal proof, never copy authority."""
    from producer_recovery import verify_retained
    record = verify_retained(db, job_id, attempt_id, states=('disposed',))
    native, proof = record['native'], record['proof']; disposal = proof.get('disposal') or {}
    need(isinstance(disposal.get('removed'), str) and bool(disposal['removed']) and
         isinstance(disposal.get('child_job_id'), str), 'Disposed producer has no completed disposal receipt')
    expected_files = [{'name': item['name'], 'sha256': item['sha256']} for item in native['files']]
    need(disposal.get('files') == expected_files and all(re.fullmatch('[a-f0-9]{64}', item['sha256'])
         for item in expected_files), 'Disposed producer file proof differs')
    child_id = disposal['child_job_id']
    child = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (child_id,)).fetchone()
    need(child is not None and child['state'] == 'completed', 'Disposed producer child is not completed')
    output = json.loads(child['output'] or 'null'); manifest = json.loads(child['manifest'])
    binding = manifest.get('retry_intent') or {}
    relation = db.execute('SELECT binding FROM audio_retry_intents WHERE parent_job_id=? AND child_job_id=?',
                          (job_id,child_id)).fetchone()
    need(isinstance(output, dict) and output.get('job_id') == child_id and
         (output.get('validation') or {}).get('passed') is True and relation and
         json.loads(relation[0]) == binding and binding.get('parent_job_id') == job_id and
         binding.get('retained_checkpoint_id') == record['checkpoint_id'] and binding.get('retained_disposal') is True,
         'Disposed producer verified-child lineage differs')
    data = Path(database).absolute().parent
    expected = data / 'merge-cache' / 'audio-staging' / job_id / attempt_id
    need(_key(native['stage']) == _key(str(expected)), 'Disposed producer stage differs from exact catalog location')
    _prove_empty_owned_stage(expected, data)


def logical_catalog_digest(database,*,immutable=False):
    """Stable original schema+rows; relocation activation metadata is separate."""
    value = hashlib.sha256()
    def atom(item):
        return {'sqlite_blob_base64': base64.b64encode(item).decode('ascii')} if isinstance(item, bytes) else item
    with contextlib.closing(_readonly_database(database,immutable=immutable)) as db:
        db.execute('BEGIN')
        internal = {'storage_relocation_activation', 'storage_relocation_verification'}
        objects = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        for row in objects:
            if row['tbl_name'] in internal:continue
            value.update(packed(list(row))); value.update(b'\n')
        for obj in objects:
            if obj['type'] != 'table' or obj['name'] in internal:continue
            name = obj['name']; quoted = '"' + name.replace('"', '""') + '"'
            need(not str(obj['sql']).lstrip().upper().startswith('CREATE VIRTUAL TABLE'),
                 'Virtual catalog table needs an explicit relocation adapter')
            columns = list(db.execute('PRAGMA table_info(' + quoted + ')'))
            primary = sorted((row['pk'], row['name']) for row in columns if row['pk'])
            order = ','.join('"' + column.replace('"', '""') + '"' for _, column in primary) if primary else 'rowid'
            value.update(packed({'table': name}))
            for row in db.execute('SELECT * FROM ' + quoted + ' ORDER BY ' + order):
                checkpoint()
                value.update(packed([atom(item) for item in row])); value.update(b'\n')
    return value.hexdigest()


def _snapshot_database(database, destination):
    """Consistent SQLite backup including WAL, in a new separately owned file."""
    need(not destination.exists(), 'Snapshot destination already exists')
    create_new(destination, b'')
    with contextlib.closing(_readonly_database(database)) as source:
        with contextlib.closing(sqlite3.connect(destination)) as target:
            source.backup(target, pages=256, sleep=0.01, progress=lambda *_: checkpoint())
            need(target.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'Backup integrity check failed')
    from native_io import DirectoryBoundary, VerifiedFile
    with DirectoryBoundary(destination.anchor, destination.parent), VerifiedFile(destination) as held:
        return held.sha256()


def _scan(root, scopes, stack, *, security_access=False, hash_files=True):
    """Retain all exact scope entries; collect no sibling-project file tree."""
    from native_io import DirectoryBoundary
    from source_cleanup import single_stream
    stack.enter_context(DirectoryBoundary(root.anchor, root))
    dirs, files, handles, identities = {}, {}, {}, {}
    def directory(relative):
        key = _key(relative)
        if key in dirs:return handles[key]
        path = root / relative if relative else root
        item = stack.enter_context(NativeItem(path, directory=True, writable_security=security_access))
        if relative and any(_inside(relative,scope) for scope in scopes):_no_directory_streams(path)
        native = tuple(item.facts['identity'])
        need(native not in identities or identities[native] == key, 'Native directory aliases/overlapping scopes refused')
        identities[native] = key
        dirs[key] = {'relative': relative, 'identity': item.facts['identity']}
        handles[key] = item
        return item
    directory('')
    for scope in scopes:
        chain = []
        relative = scope
        while relative:
            chain.append(relative); relative = ntpath.dirname(relative)
        for relative in reversed(chain):directory(relative)
        pending = [scope]
        while pending:
            relative = pending.pop()
            item = directory(relative); item.revalidate()
            with os.scandir(root / relative) as entries:
                children = sorted(list(entries), key=lambda entry: entry.name)
            for entry in children:
                checkpoint()
                name = _relative(ntpath.join(relative, entry.name))
                need(not entry.is_symlink() and not os.path.isjunction(entry.path), 'Reparse scope child refused')
                if entry.is_dir(follow_symlinks=False):
                    directory(name); pending.append(name)
                else:
                    need(_key(name) not in files and _key(name) not in dirs, 'Ambiguous duplicate storage name')
                    leaf = stack.enter_context(NativeItem(root / name, writable_security=security_access))
                    native = tuple(leaf.facts['identity'])
                    need(native not in identities, 'Native file alias/duplicate scope refused')
                    identities[native] = _key(name)
                    single_stream(root / name)
                    files[_key(name)] = {'relative': name, 'facts': leaf.facts,
                                         'sha256': leaf.sha256() if hash_files else None}
                    handles[_key(name)] = leaf
                need(len(dirs) + len(files) <= MAX_FILES, 'Managed storage census exceeds bound')
    return dirs, files, handles


def _no_directory_streams(path):
    """Reject unknown app-state directory ADS; never delete their contents."""
    kernel=_windows()
    class Stream(ctypes.Structure):
        _fields_=[('size',ctypes.c_longlong),('name',wintypes.WCHAR*296)]
    kernel.FindFirstStreamW.argtypes=[wintypes.LPCWSTR,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.FindFirstStreamW.restype=wintypes.HANDLE
    kernel.FindNextStreamW.argtypes=[wintypes.HANDLE,ctypes.c_void_p];kernel.FindNextStreamW.restype=wintypes.BOOL
    kernel.FindClose.argtypes=[wintypes.HANDLE]
    stream=Stream();handle=kernel.FindFirstStreamW(str(path),0,ctypes.byref(stream),0)
    if handle==ctypes.c_void_p(-1).value:
        need(ctypes.get_last_error()==38,'Cannot inspect app-state directory streams');return
    try:
        count=0
        while True:
            count+=1;need(count<=16 and stream.name=='::$DATA' and stream.size==0,
                         'Unknown app-state directory stream retained')
            if not kernel.FindNextStreamW(handle,ctypes.byref(stream)):
                need(ctypes.get_last_error()==38,'Cannot finish app-state directory stream check');return
    finally:kernel.FindClose(handle)


def _validate_roots(source_root, target_root, scopes, catalog_relative, workspace):
    source, target = local_root(source_root), local_root(target_root)
    need(not _inside(str(source), str(target)) and not _inside(str(target), str(source)), 'Relocation roots overlap')
    need(isinstance(scopes, (tuple, list)) and 0 < len(scopes) <= 32, 'Explicit managed scopes required')
    scopes = tuple(_relative(s) for s in scopes)
    need(len({_key(s) for s in scopes}) == len(scopes) and
         not any(_inside(a, b) for a in scopes for b in scopes if a != b), 'Duplicate/nested scopes refused')
    catalog = _relative(catalog_relative)
    need(ntpath.basename(catalog) == 'inventory.sqlite3', 'Expected Books Arranger inventory.sqlite3 catalog')
    need(any(_inside(catalog, scope) for scope in scopes), 'Catalog escapes explicit scopes')
    from storage_state_ownership import require_catalog_scope
    require_catalog_scope(scopes,catalog)
    work = local_root(workspace)
    need(not _inside(str(work), str(source)) and not _inside(str(work), str(target)),
         'Transaction evidence must be outside source and target copied trees')
    need(work.is_dir(), 'Explicit existing transaction workspace required')
    return source, target, scopes, catalog, work


def source_plan_consent_sha256(plan):
    """Consent ignores ONLY known SQLite SHM last-write bookkeeping.

    The independently saved source plan retains exact fresh native facts. SHM
    bytes/identity/size, WAL and the main database remain strictly consent-bound.
    SQLite read-only inspection may update this index file's LastWriteTime.
    """
    projection = dict(plan)
    projection.pop('consent_sha256', None)
    shm = _key(plan['catalog_relative'] + '-shm')
    projection['files'] = [dict(row, facts=dict(row['facts'], modified=0))
                           if _key(row['relative']) == shm else row for row in plan['files']]
    return digest(packed(projection))


@bounded_operation
def prepare_source(source_root, target_root, scopes, catalog_relative, workspace, *,
                   receipt_classes=None, apply=False, catalog_id=None, generation=None,
                   expected_plan_sha256=None):
    """Plan by default; apply creates immutable evidence then fences only source scopes.

    Source bytes are never removed or copied by this API. A failed/partial fence
    is recorded and remains held for explicit recovery, not silently undone.
    """
    source, target, scopes, catalog, work = _validate_roots(
        source_root, target_root, scopes, catalog_relative, workspace)
    catalog_id = catalog_id or str(uuid.uuid4()); generation = generation or str(uuid.uuid4())
    need(str(uuid.UUID(catalog_id)) == catalog_id and str(uuid.UUID(generation)) == generation,
         'Canonical transaction identities required')
    database = source / catalog
    with contextlib.ExitStack() as stack:
        stack.enter_context(_catalog_owner(database))
        states = _closed_state(database)
        inferred, held = classify_historical_files(database, managed_root=str(source))
        from storage_state_ownership import catalog_state_membership,validate_census_ownership
        membership=catalog_state_membership(database)
        classes = inferred if receipt_classes is None else receipt_classes
        need(isinstance(classes, dict), 'Explicit typed historical path registry required')
        normalized_classes = {}
        for path, names in classes.items():
            need(isinstance(path, str) and isinstance(names, list) and names and
                 all(c in RECEIPT_CLASSES and c != 'storage-directory' for c in names),
                 'Invalid historical path class registry')
            if not _inside(path, str(source)):continue  # unchanged libraries stay strict/unmapped
            relative = _relative(ntpath.relpath(path, str(source)))
            need(any(_inside(relative, scope) for scope in scopes), 'Historical path escapes managed scopes')
            normalized_classes[_key(relative)] = sorted(set(names))
        logical_sha = logical_catalog_digest(database)
        snapshot = work / ('catalog-snapshot-' + generation + '.sqlite3')
        snapshot_sha = _snapshot_database(database, snapshot) if apply else None
        # Every SQLite connection is closed before collecting the final held
        # native facts: no later read can dirty SHM timestamps after this census.
        dirs, files, handles = _scan(source, scopes, stack, security_access=apply)
        owned_state=validate_census_ownership(source,scopes,catalog,files,dirs,membership,normalized_classes)
        missing = sorted(key for key in normalized_classes if key not in files)
        # Terminal historic paths may already be absent; no mapping/authority is
        # created for them. Their immutable terminal history remains in catalog.
        security = Security()
        records = []
        for key in sorted(handles, key=lambda key: (key.count('\\'), key)):
            item = handles[key]
            if not any(_inside(key, scope) for scope in scopes):continue
            records.append({'relative': dirs[key]['relative'] if key in dirs else files[key]['relative'],
                            'kind': 'directory' if key in dirs else 'file',
                            'identity': item.facts['identity'], 'original_security': security.capture(item)})
        plan = {'schema': PLAN_SCHEMA, 'generation': generation, 'catalog_id': catalog_id,
                'source_root': str(source), 'target_root': str(target), 'scopes': list(scopes),
                'catalog_relative': catalog, 'states': states, 'held_classes': held,'owned_state':owned_state,'snapshot_path':str(snapshot),
                'historical_absent_paths': missing, 'receipt_classes': normalized_classes,
                'directories': list(dirs.values()), 'files': list(files.values()), 'security': records,
                'logical_catalog_sha256': logical_sha,
                'consent_policy': 'Only exact catalog SHM.modified is volatile; full native facts retained in source plan'}
        plan['consent_sha256'] = source_plan_consent_sha256(plan)
        if not apply:return plan
        plan_raw = packed(plan); plan_path = work / ('source-plan-' + generation + '.json')
        need(expected_plan_sha256 == plan['consent_sha256'],
             'Source state/ownership plan differs from the explicitly reviewed SHA-256')
        plan_sha = create_new(plan_path, plan_raw)
        applied = []
        try:
            # All rollback originals were made durable BEFORE the first DACL
            # change. Per-entry NEW receipts make interruption inspectable.
            for index, record in enumerate(records):
                checkpoint()
                item = handles[_key(record['relative'])]
                need(security_equivalent(security.capture(item), record['original_security']),
                     'Source security changed after preflight')
                _, fence = security.deny_writes(item)
                written = dict(record, applied_security=fence)
                create_new(work / ('fence-' + generation + '-' + str(index) + '.json'), packed(written))
                applied.append(written)
            for key, item in handles.items():item.revalidate()
            with contextlib.ExitStack() as census:
                final_dirs, final_files, _ = _scan(source, scopes, census, hash_files=False)
                need(set(final_dirs) == set(dirs) and set(final_files) == set(files),
                     'Source membership changed before its full write fence was established')
                need(all(final_dirs[key]['identity'] == dirs[key]['identity'] for key in dirs) and
                     all(final_files[key]['facts'] == files[key]['facts'] for key in files),
                     'Source native facts changed before its full write fence was established')
            receipt = {'schema': FENCE_SCHEMA, 'generation': generation, 'catalog_id': catalog_id,
                       'source_snapshot_sha256': snapshot_sha, 'source_original': str(source), 'target_root': str(target),
                       'source_root_identity': dirs['']['identity'], 'scopes': list(scopes),
                       'catalog_relative': catalog, 'items': applied, 'source_plan_sha256': plan_sha}
            fence_path = work / ('source-fence-' + generation + '.json')
            fence_sha = create_new(fence_path, packed(receipt))
        except BaseException as error:
            failure = {'generation': generation, 'source_plan_sha256': plan_sha,
                       'applied_items': len(applied), 'error': str(error),
                       'disposition': 'source held; explicit recovery required; not activated'}
            create_new(work / ('source-fence-failed-' + generation + '.json'), packed(failure))
            raise
    with verify_source_fence(fence_path, fence_sha) as proof:proof.revalidate()
    return {'phase': 'source-fenced', 'generation': generation, 'catalog_id': catalog_id,
            'source_plan': str(plan_path), 'source_plan_sha256': plan_sha,
            'source_fence': str(fence_path), 'source_fence_sha256': fence_sha,
            'snapshot': str(snapshot), 'source_snapshot_sha256': snapshot_sha,
            'held_classes': held, 'files': len(files), 'bytes': sum(f['facts']['size'] for f in files.values())}


@contextlib.contextmanager
def pinned_receipt(path, expected_sha256):
    from native_io import DirectoryBoundary, VerifiedFile
    from source_cleanup import single_stream
    path = Path(path).absolute()
    with DirectoryBoundary(path.anchor, path.parent), VerifiedFile(path) as held:
        need(held.facts()['links'] == 1 and held.facts()['size'] <= MAX_RECEIPT,
             'Receipt is linked/oversized')
        single_stream(path)
        raw = b''.join(held.chunks())
        yield bounded_json(raw, expected_sha256)


def _same_copy_inventory(plan, dirs, files):
    expected_dirs = {_key(row['relative']): row for row in plan['directories']}
    expected_files = {_key(row['relative']): row for row in plan['files']}
    need(set(expected_dirs) == set(dirs) and set(expected_files) == set(files),
         'Copied storage membership differs; unknown or missing entries are retained')
    for key, expected in expected_files.items():
        current = files[key]
        need(expected['sha256'] == current['sha256'] and
             expected['facts']['size'] == current['facts']['size'] and
             expected['facts']['modified'] == current['facts']['modified'],
             'Copied storage bytes/timestamps differ: ' + expected['relative'])


@bounded_operation
def seal_target(source_plan, source_plan_sha256, source_fence, source_fence_sha256,
                source_original, manifest_path):
    """Verify an independently copied target; no shared-folder copy/move here."""
    manifest_path = Path(manifest_path).absolute()
    with contextlib.ExitStack() as held:
        plan = held.enter_context(pinned_receipt(source_plan, source_plan_sha256))
        initial_fence = held.enter_context(pinned_receipt(source_fence, source_fence_sha256))
        need(plan.get('schema') == PLAN_SCHEMA and initial_fence.get('schema') == FENCE_SCHEMA and
             initial_fence['source_plan_sha256'] == source_plan_sha256 and
             plan['catalog_id'] == initial_fence['catalog_id'] and
             plan['generation'] == initial_fence['generation'], 'Source phase receipts do not agree')
        need(set(plan) == {'schema','generation','catalog_id','source_root','target_root','scopes',
                          'catalog_relative','states','held_classes','historical_absent_paths','receipt_classes',
                          'directories','files','security','logical_catalog_sha256','consent_sha256','consent_policy','owned_state','snapshot_path'},
             'Unsupported or incomplete source plan; source remains held')
        from storage_state_ownership import require_plan_membership
        require_plan_membership(plan)
        original = local_root(source_original)
        from storage_state_ownership import validate_plan_snapshot_membership
        validate_plan_snapshot_membership(plan,source_plan,initial_fence['source_snapshot_sha256'],original)
        target = local_root(plan['target_root'])
        need(not _inside(str(original), str(target)) and not _inside(str(target), str(original)),
             'Original backup and target overlap')
        need(not _inside(str(manifest_path), str(original)) and not _inside(str(manifest_path), str(target)),
             'Descriptor must be outside copied state roots')
        fence = dict(initial_fence, source_original=str(original))
        final_fence_path = Path(str(manifest_path) + '.source-fence.json')
        if final_fence_path.exists():
            raw = packed(fence)
            with pinned_receipt(final_fence_path, digest(raw)) as existing:need(existing == fence, 'Source fence differs')
            final_fence_sha = digest(raw)
        else:final_fence_sha = create_new(final_fence_path, packed(fence))
        original_lease = held.enter_context(verify_source_fence(final_fence_path, final_fence_sha))
        original_lease.revalidate()
        database = target / plan['catalog_relative']
        target_owner = held.enter_context(_catalog_owner(database))
        security = Security()
        # Open all exact target objects before changing copied ACLs. The actual
        # target .lock owner (not the source copy's lock) excludes old writers.
        with contextlib.ExitStack() as target_handles:
            dirs, files, handles = _scan(target, tuple(plan['scopes']), target_handles, security_access=True)
            if not manifest_path.exists():_same_copy_inventory(plan, dirs, files)
            originals = {_key(record['relative']): record for record in plan['security']}
            for key in sorted(originals, key=lambda key: (key.count('\\'), key)):
                security.restore(handles[key], originals[key]['original_security'], copied_target=True)
            need(logical_catalog_digest(database) == plan['logical_catalog_sha256'],
                 'Target catalog metadata/history differs from consistent source snapshot')
            if manifest_path.exists():
                raw = manifest_path.read_bytes(); manifest = parse_manifest(raw, digest(raw))
                need(manifest.generation == plan['generation'] and manifest.catalog_id == plan['catalog_id'] and
                     manifest.source_snapshot_sha256 == initial_fence['source_snapshot_sha256'],
                     'Existing sealed generation differs')
                for binding in manifest.files.values():
                    current = files.get(_key(binding.relative))
                    if 'catalog-storage' in binding.receipt_classes:
                        need(current and current['facts']['identity'] == list(binding.target['identity']),
                             'Previously sealed catalog native identity changed')
                    else:
                        need(current and current['facts'] == dict(binding.target, identity=list(binding.target['identity'])) and
                             current['sha256'] == binding.sha256, 'Previously sealed historical copy changed')
                manifest_sha = manifest.digest
            else:
                source_dirs = {_key(record['relative']): record for record in plan['directories']}
                source_files = {_key(record['relative']): record for record in plan['files']}
                entries = []
                for key, classes in sorted(plan['receipt_classes'].items()):
                    if key not in source_files:continue
                    entries.append({'relative': source_files[key]['relative'],
                                    'source_facts': source_files[key]['facts'], 'target_facts': files[key]['facts'],
                                    'sha256': source_files[key]['sha256'], 'receipt_classes': classes})
                descriptor = {'schema': 'books-storage-relocation-v1', 'generation': plan['generation'],
                              'catalog_id': plan['catalog_id'], 'source_root': plan['source_root'],
                              'target_root': plan['target_root'], 'scopes': plan['scopes'],
                              'source_snapshot_sha256': initial_fence['source_snapshot_sha256'],
                              'directories': [{'relative': record['relative'],
                                  'source_identity': source_dirs[key]['identity'], 'target_identity': record['identity']}
                                  for key, record in sorted(dirs.items())], 'files': entries}
                raw = packed(descriptor); manifest_sha = digest(raw)
                parse_manifest(raw, manifest_sha)
                create_new(manifest_path, raw)
            target_root_identity = dirs['']['identity']
        # All ordinary copied media were retained/hash checked above. Release
        # database read-only handles for the one target-owned metadata write;
        # .lock ownership and source fence stay retained through commit/readback.
        with contextlib.closing(sqlite3.connect(database, timeout=2)) as db:
            db.execute('PRAGMA synchronous=FULL'); db.execute('BEGIN IMMEDIATE')
            db.execute(ACTIVATION_SQL)
            rows = db.execute('SELECT * FROM storage_relocation_activation').fetchall()
            expected = (plan['catalog_id'], plan['generation'], manifest_sha,
                        initial_fence['source_snapshot_sha256'], 'sealed', 1, final_fence_sha,
                        json.dumps(target_root_identity))
            if rows:
                need(len(rows) == 1 and tuple(rows[0]) == expected, 'Target has a different/active relocation generation')
            else:db.execute('INSERT INTO storage_relocation_activation VALUES(?,?,?,?,?,?,?,?)', expected)
            original_lease.revalidate(); target_owner.revalidate(); db.commit()
            need(tuple(db.execute('SELECT * FROM storage_relocation_activation').fetchone()) == expected,
                 'Sealed activation metadata readback failed')
        verification = {'schema': 'books-storage-target-seal-v1', 'generation': plan['generation'],
                        'catalog_id': plan['catalog_id'], 'manifest': str(manifest_path),
                        'manifest_sha256': manifest_sha, 'source_fence_sha256': final_fence_sha,
                        'source_plan_sha256': source_plan_sha256, 'source_plan': str(Path(source_plan).absolute()),
                        'target_database': str(database),
                        'target_root_identity': target_root_identity,
                        'logical_catalog_sha256': plan['logical_catalog_sha256'], 'held_classes': plan['held_classes']}
        seal_path = Path(str(manifest_path) + '.sealed.json')
        if seal_path.exists():
            with pinned_receipt(seal_path, digest(packed(verification))) as previous:
                need(previous == verification, 'Existing target seal differs')
        else:create_new(seal_path, packed(verification))
        return dict(verification, phase='sealed-not-active', complete=not plan['held_classes'])


@bounded_operation
def activate_target(manifest_path, manifest_sha256):
    """Enter verification-only admission; no normal application work is enabled."""
    manifest_path = Path(manifest_path).absolute()
    with contextlib.ExitStack() as held:
        descriptor = held.enter_context(pinned_receipt(manifest_path, manifest_sha256))
        manifest = parse_manifest(packed(descriptor), manifest_sha256)
        seal_path = Path(str(manifest_path) + '.sealed.json')
        # Seal is CREATE_NEW and hash-pinned by the descriptor/generation fields;
        # its own bytes are retained while the matching DB transition occurs.
        raw = seal_path.read_bytes()
        seal = held.enter_context(pinned_receipt(seal_path, digest(raw)))
        need(seal['manifest_sha256'] == manifest_sha256 and seal['catalog_id'] == manifest.catalog_id and
             seal['generation'] == manifest.generation, 'Target seal and descriptor disagree')
        fence = held.enter_context(verify_source_fence(str(manifest_path) + '.source-fence.json',
                                                     seal['source_fence_sha256']))
        database = Path(seal['target_database'])
        need(_inside(str(database), manifest.target_root) and manifest.permitted(
             ntpath.join(manifest.source_root, ntpath.relpath(str(database), manifest.target_root))),
             'Sealed database escapes managed target')
        owner = held.enter_context(_catalog_owner(database))
        need(logical_catalog_digest(database) == seal['logical_catalog_sha256'],
             'Target has new application writes; activation/rollback needs reconciliation')
        with contextlib.closing(sqlite3.connect(database, timeout=2)) as db:
            db.execute('PRAGMA synchronous=FULL'); db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM storage_relocation_activation').fetchall()
            expected = (manifest.catalog_id, manifest.generation, manifest_sha256,
                        manifest.source_snapshot_sha256, 'sealed', 1, seal['source_fence_sha256'],
                        json.dumps(seal['target_root_identity']))
            verifying = tuple(list(expected[:4]) + ['verifying', 2] + list(expected[6:]))
            need(len(row) == 1 and tuple(row[0]) in (expected, verifying), 'Activation generation/phase changed')
            if tuple(row[0]) == expected:
                changed = db.execute('UPDATE storage_relocation_activation SET phase=?,revision=? '
                                     'WHERE catalog_id=? AND generation=? AND manifest_sha256=? AND phase=? AND revision=?',
                                     ('verifying', 2, manifest.catalog_id, manifest.generation, manifest_sha256, 'sealed', 1))
                need(changed.rowcount == 1, 'Activation compare-and-set failed')
            fence.revalidate(); owner.revalidate(); db.commit()
            need(tuple(db.execute('SELECT * FROM storage_relocation_activation').fetchone()) == verifying,
                 'Verification-only generation readback failed')
        return {'phase': 'verifying', 'generation': manifest.generation, 'catalog_id': manifest.catalog_id,
                'storage_relocation': {'manifest': str(manifest_path), 'sha256': manifest_sha256},
                'held_classes': seal['held_classes'], 'complete': False,
                'disposition': 'independent target verification required; no normal library work admitted'}


@contextlib.contextmanager
def _verification_operation(manifest_path, manifest_sha256):
    manifest_path = Path(manifest_path).absolute()
    with contextlib.ExitStack() as held:
        descriptor = held.enter_context(pinned_receipt(manifest_path, manifest_sha256))
        manifest = parse_manifest(packed(descriptor), manifest_sha256)
        seal_path = Path(str(manifest_path) + '.sealed.json')
        seal = held.enter_context(pinned_receipt(seal_path, digest(seal_path.read_bytes())))
        need(seal['manifest_sha256'] == manifest_sha256 and seal['catalog_id'] == manifest.catalog_id and
             seal['generation'] == manifest.generation, 'Verification seal and manifest disagree')
        plan = held.enter_context(pinned_receipt(seal['source_plan'], seal['source_plan_sha256']))
        fence = held.enter_context(verify_source_fence(str(manifest_path) + '.source-fence.json',
                                                     seal['source_fence_sha256']))
        database = Path(seal['target_database'])
        need(_inside(str(database), manifest.target_root), 'Verification catalog escapes target')
        owner = held.enter_context(_catalog_owner(database))
        from native_io import DirectoryBoundary
        held.enter_context(DirectoryBoundary(Path(manifest.target_root).anchor, Path(manifest.target_root)))
        root = held.enter_context(NativeItem(manifest.target_root, directory=True))
        need(root.facts['identity'] == seal['target_root_identity'], 'Verification target root was replaced')
        yield manifest_path, manifest, seal, plan, fence, database, owner


def _activation_record(manifest, seal, phase, revision):
    return (manifest.catalog_id, manifest.generation, manifest.digest,
            manifest.source_snapshot_sha256, phase, revision, seal['source_fence_sha256'],
            json.dumps(seal['target_root_identity']))


@contextlib.contextmanager
def _capture_verification(operation):
    manifest_path, manifest, seal, plan, fence, database, owner = operation
    logical = logical_catalog_digest(database)
    need(logical == plan['logical_catalog_sha256'], 'Target original catalog schema/history changed before verification')
    with contextlib.ExitStack() as handles:
        source_dirs, source_files, _ = _scan(fence.root, tuple(plan['scopes']), handles)
        expected_dirs = {_key(row['relative']): row for row in plan['directories']}
        expected_files = {_key(row['relative']): row for row in plan['files']}
        need(set(source_dirs) == set(expected_dirs) and set(source_files) == set(expected_files),
             'Original source membership changed after fence')
        for key, row in source_dirs.items():
            need(row['identity'] == expected_dirs[key]['identity'], 'Original source directory identity changed')
        for key, row in source_files.items():
            need(row['facts'] == expected_files[key]['facts'] and row['sha256'] == expected_files[key]['sha256'],
                 'Original source native facts/bytes changed after fence')
        target_dirs, target_files, _ = _scan(Path(manifest.target_root), tuple(plan['scopes']), handles)
        need(set(target_dirs) == set(manifest.directories), 'Target directory membership changed')
        for key, row in target_dirs.items():
            need(row['identity'] == list(manifest.directories[key].target), 'Target directory native identity changed')
        catalog = _key(plan['catalog_relative'])
        sqlite_family = {catalog + suffix for suffix in ('', '-wal', '-shm', '-journal')}
        ordinary = set(target_files) - sqlite_family
        need(ordinary == set(expected_files) - sqlite_family,
             'Target has unknown/missing non-database files before verification')
        for key in ordinary:
            current, old = target_files[key], expected_files[key]
            need(current['sha256'] == old['sha256'] and current['facts']['size'] == old['facts']['size'] and
                 current['facts']['modified'] == old['facts']['modified'],
                 'Target work/recovery/cache bytes changed before verification')
        for key, binding in manifest.files.items():
            current = target_files.get(key)
            need(current is not None, 'Historical copied artifact disappeared before verification')
            if 'catalog-storage' in binding.receipt_classes:
                need(current['facts']['identity'] == list(binding.target['identity']), 'Copied catalog identity changed')
            else:
                need(current['facts'] == dict(binding.target, identity=list(binding.target['identity'])) and
                     current['sha256'] == binding.sha256, 'Historical copied native identity/bytes changed')
        native_catalog = target_files[catalog]['facts']
        state = {'generation': manifest.generation, 'catalog_id': manifest.catalog_id,
                 'manifest_sha256': manifest.digest, 'logical_catalog_sha256': logical,
                 'source_root_identity': fence.root_item.facts['identity'],
                 'target_root_identity': target_dirs['']['identity'],
                 'directories': sorted(target_dirs.values(), key=lambda row: row['relative']),
                 'files': sorted((target_files[key] for key in ordinary), key=lambda row: row['relative']),
                 'catalog_identity': {key: native_catalog[key] for key in
                      ('identity','dev','ino','identity_method','identity_api_error','links')},
                 'source_plan_sha256': seal['source_plan_sha256'], 'source_fence_sha256': seal['source_fence_sha256']}
        fence.revalidate(); owner.revalidate()
        yield state, len(target_files), len(target_dirs)


@bounded_operation
def verify_target(manifest_path, manifest_sha256, verification_path=None):
    """Independent reopen/hash/native verification; creates a NEW pinned receipt."""
    with _verification_operation(manifest_path, manifest_sha256) as operation:
        path, manifest, seal, plan, fence, database, owner = operation
        with contextlib.closing(_readonly_database(database)) as db:
            row = db.execute('SELECT * FROM storage_relocation_activation').fetchall()
            need(len(row) == 1 and tuple(row[0]) == _activation_record(manifest, seal, 'verifying', 2),
                 'Independent verification requires exact verification-only generation')
        with _capture_verification(operation) as (state, file_count, directory_count):
            receipt = {'schema': 'books-storage-target-verification-v1',
                       'generation': manifest.generation, 'catalog_id': manifest.catalog_id,
                       'manifest_path': str(path), 'manifest_sha256': manifest_sha256,
                       'source_snapshot_sha256': manifest.source_snapshot_sha256,
                       'source_plan_sha256': seal['source_plan_sha256'],
                       'source_fence_sha256': seal['source_fence_sha256'],
                       'verified_state_sha256': digest(packed(state)),
                       'logical_catalog_sha256': state['logical_catalog_sha256'],
                       'source_original': str(fence.root), 'target_root': manifest.target_root,
                       'source_root_identity': state['source_root_identity'],
                       'target_root_identity': state['target_root_identity'],
                       'files_verified': file_count, 'directories_verified': directory_count,
                       'held_classes': plan['held_classes'], 'complete': not plan['held_classes']}
            output = Path(verification_path).absolute() if verification_path else Path(str(path) + '.verified.json')
            need(not _inside(str(output), manifest.source_root) and not _inside(str(output), manifest.target_root) and
                 not _inside(str(output), str(fence.root)), 'Verification receipt must be outside both data trees')
            raw = packed(receipt); sha = digest(raw)
            if output.exists():
                with pinned_receipt(output, sha) as previous:need(previous == receipt, 'Existing verification receipt differs')
            else:create_new(output, raw)
            return {'phase': 'verified-not-enabled', 'verification_path': str(output),
                    'verification_sha256': sha, 'verified_state_sha256': receipt['verified_state_sha256'],
                    'held_classes': plan['held_classes'], 'complete': not plan['held_classes']}


@bounded_operation
def enable_target(manifest_path, manifest_sha256, verification_path, verification_sha256):
    """Enable normal admission only after pinned independent proof+fresh recheck."""
    with _verification_operation(manifest_path, manifest_sha256) as operation:
        path, manifest, seal, plan, fence, database, owner = operation
        with pinned_receipt(verification_path, verification_sha256) as proof:
            need(proof.get('schema') == 'books-storage-target-verification-v1' and
                 proof['generation'] == manifest.generation and proof['catalog_id'] == manifest.catalog_id and
                 proof['manifest_path'] == str(path) and proof['manifest_sha256'] == manifest_sha256 and
                 proof['source_plan_sha256'] == seal['source_plan_sha256'] and
                 proof['source_fence_sha256'] == seal['source_fence_sha256'],
                 'Independent verification receipt belongs to another transfer')
            need(not proof['held_classes'] and not plan['held_classes'],
                 'Unsupported held obligations require explicit typed compatibility before enabling')
            with _capture_verification(operation) as (state, _, _):
                need(digest(packed(state)) == proof['verified_state_sha256'],
                     'Target/source state changed after independent verification')
            expected_registration = (manifest.catalog_id, manifest.generation, manifest_sha256,
                                     str(Path(verification_path).absolute()), verification_sha256,
                                     proof['verified_state_sha256'])
            with contextlib.closing(sqlite3.connect(database, timeout=2)) as db:
                db.execute('PRAGMA synchronous=FULL'); db.execute('BEGIN IMMEDIATE')
                rows = db.execute('SELECT * FROM storage_relocation_activation').fetchall()
                need(len(rows) == 1 and tuple(rows[0]) in (
                     _activation_record(manifest,seal,'verifying',2), _activation_record(manifest,seal,'active',3)),
                     'Normal admission generation/phase changed')
                db.execute(VERIFICATION_SQL)
                registered = db.execute('SELECT * FROM storage_relocation_verification').fetchall()
                if registered:need(len(registered) == 1 and tuple(registered[0]) == expected_registration,
                                    'Independent verification registration changed')
                else:db.execute('INSERT INTO storage_relocation_verification VALUES(?,?,?,?,?,?)', expected_registration)
                if rows[0][4] == 'verifying':
                    changed = db.execute('UPDATE storage_relocation_activation SET phase=?,revision=? WHERE '
                        'catalog_id=? AND generation=? AND manifest_sha256=? AND phase=? AND revision=?',
                        ('active',3,manifest.catalog_id,manifest.generation,manifest_sha256,'verifying',2))
                    need(changed.rowcount == 1, 'Normal admission compare-and-set failed')
                fence.revalidate(); owner.revalidate(); db.commit()
                need(db.execute('SELECT phase,revision FROM storage_relocation_activation').fetchone() == ('active',3),
                     'Normal admission readback failed')
            return {'phase': 'active', 'generation': manifest.generation, 'catalog_id': manifest.catalog_id,
                    'storage_relocation': {'manifest': str(path), 'sha256': manifest_sha256},
                    'verification_path': str(Path(verification_path).absolute()),
                    'verification_sha256': verification_sha256, 'complete': True, 'held_classes': []}


@bounded_operation
def rollback_unwritten(manifest_path, manifest_sha256):
    """Fence target first, restore original source only with no unreconciled writes.

    A new decision/job/book/cache write refuses rollback. Both copies remain;
    this API removes no files and never overwrites a newer catalog snapshot.
    """
    manifest_path = Path(manifest_path).absolute()
    completed_path = Path(str(manifest_path) + '.rollback-complete.json')
    target_fence_path = Path(str(manifest_path) + '.rollback-target-fence.json')
    with contextlib.ExitStack() as held:
        descriptor = held.enter_context(pinned_receipt(manifest_path, manifest_sha256))
        manifest = parse_manifest(packed(descriptor), manifest_sha256)
        seal_path = Path(str(manifest_path) + '.sealed.json')
        seal = held.enter_context(pinned_receipt(seal_path, digest(seal_path.read_bytes())))
        need(seal.get('manifest_sha256') == manifest_sha256 and seal.get('catalog_id') == manifest.catalog_id and
             seal.get('generation') == manifest.generation and 'source_plan' in seal,
             'Rollback requires the exact complete target seal')
        plan = held.enter_context(pinned_receipt(seal['source_plan'], seal['source_plan_sha256']))
        source_fence_path = Path(str(manifest_path) + '.source-fence.json')
        source_receipt = held.enter_context(pinned_receipt(source_fence_path, seal['source_fence_sha256']))
        database = Path(seal['target_database']); target = local_root(manifest.target_root)
        owner = held.enter_context(_catalog_owner(database))
        resumed_target = None
        if target_fence_path.exists():
            raw = target_fence_path.read_bytes(); target_fence_sha = digest(raw)
            resumed_target = held.enter_context(verify_source_fence(target_fence_path, target_fence_sha))
            need(resumed_target.receipt['catalog_id'] == manifest.catalog_id and
                 resumed_target.receipt['generation'] == manifest.generation and
                 _key(resumed_target.receipt['source_original']) == _key(manifest.target_root),
                 'Rollback target fence belongs to another operation')
        source_lease = held.enter_context(SourceFenceLease(source_fence_path, seal['source_fence_sha256'],
                                                          allow_restored=bool(resumed_target)))
        need(logical_catalog_digest(database) == seal['logical_catalog_sha256'],
             'Rollback refused: new target catalog writes require explicit reconciliation')
        expected_files = {_key(row['relative']): row for row in plan['files']}
        catalog_key = _key(plan['catalog_relative'])
        sidecars = {catalog_key + ending for ending in ('', '-wal', '-shm', '-journal')}
        if resumed_target is None:
            security = Security()
            with contextlib.ExitStack() as target_handles:
                dirs, files, handles = _scan(target, tuple(plan['scopes']), target_handles, security_access=True)
                need((set(files) - sidecars) == (set(expected_files) - sidecars),
                     'Rollback refused: new/missing target work requires explicit reconciliation')
                for key in set(files) - sidecars:
                    need(files[key]['sha256'] == expected_files[key]['sha256'],
                         'Rollback refused: changed target work requires explicit reconciliation')
                target_security = []
                for key, item in handles.items():
                    if not any(_inside(key, scope) for scope in plan['scopes']):continue
                    target_security.append({'relative': dirs[key]['relative'] if key in dirs else files[key]['relative'],
                                            'kind': 'directory' if key in dirs else 'file',
                                            'identity': item.facts['identity'],
                                            'original_security': security.capture(item)})
            # Enter rollback state while target owner and original source fence
            # remain held. After target DACL fencing the DB is intentionally RO.
            with contextlib.closing(sqlite3.connect(database, timeout=2)) as db:
                db.execute('PRAGMA synchronous=FULL'); db.execute('BEGIN IMMEDIATE')
                rows = db.execute('SELECT * FROM storage_relocation_activation').fetchall()
                need(len(rows) == 1 and rows[0][:4] == (manifest.catalog_id, manifest.generation,
                     manifest_sha256, manifest.source_snapshot_sha256) and rows[0][4] in ('sealed', 'verifying', 'active', 'rolling-back'),
                     'Rollback generation/phase changed')
                db.execute('UPDATE storage_relocation_activation SET phase=?,revision=? WHERE catalog_id=? '
                           'AND generation=? AND manifest_sha256=?',
                           ('rolling-back', 3, manifest.catalog_id, manifest.generation, manifest_sha256))
                source_lease.revalidate(); owner.revalidate(); db.commit()
            intent = {'schema': 'books-storage-rollback-intent-v1', 'generation': manifest.generation,
                      'catalog_id': manifest.catalog_id, 'manifest_sha256': manifest_sha256,
                      'target_security': target_security}
            intent_path = Path(str(manifest_path) + '.rollback-intent.json')
            if not intent_path.exists():create_new(intent_path, packed(intent))
            else:
                with pinned_receipt(intent_path, digest(packed(intent))) as old:need(old == intent, 'Rollback intent changed')
            applied = []
            with contextlib.ExitStack() as target_handles:
                dirs, files, handles = _scan(target, tuple(plan['scopes']), target_handles, security_access=True)
                for index, record in enumerate(sorted(target_security, key=lambda r: (r['relative'].count('\\'), r['relative']))):
                    checkpoint()
                    item = handles[_key(record['relative'])]
                    need(item.facts['identity'] == record['identity'], 'Target identity changed during rollback fence')
                    _, captured = security.deny_writes(item)
                    applied.append(dict(record, applied_security=captured))
                    create_new(Path(str(manifest_path) + '.rollback-fence-' + str(index) + '.json'), packed(applied[-1]))
                receipt = {'schema': FENCE_SCHEMA, 'generation': manifest.generation,
                           'catalog_id': manifest.catalog_id, 'source_snapshot_sha256': manifest.source_snapshot_sha256,
                           'source_original': str(target), 'target_root': source_receipt['source_original'],
                           'source_root_identity': dirs['']['identity'], 'scopes': list(plan['scopes']),
                           'catalog_relative': plan['catalog_relative'], 'items': applied,
                           'source_plan_sha256': seal['source_plan_sha256']}
                target_fence_sha = create_new(target_fence_path, packed(receipt))
            resumed_target = held.enter_context(verify_source_fence(target_fence_path, target_fence_sha))
        # The target is now durably fenced even if the operator crashes. Only
        # after proving that fence may source protection be restored.
        resumed_target.revalidate()
        security = Security()
        for record in sorted(source_lease.receipt['items'], key=lambda r: (r['relative'].count('\\'), r['relative'])):
            checkpoint()
            path = source_lease.root / record['relative']
            with NativeItem(path, directory=record['kind'] == 'directory', writable_security=True) as item:
                need(item.facts['identity'] == record['identity'], 'Original identity changed before ACL restore')
                current = security.capture(item)
                need(current['sddl'] == record['applied_security']['sddl'] or
                     security_equivalent(current, record['original_security']), 'Unexpected original source protection')
                security.restore(item, record['original_security'])
        result = {'schema': 'books-storage-rollback-complete-v1', 'generation': manifest.generation,
                  'catalog_id': manifest.catalog_id, 'manifest_sha256': manifest_sha256,
                  'source_original': source_lease.receipt['source_original'],
                  'source_root_identity': source_lease.receipt['source_root_identity'],
                  'target_original': str(target), 'target_fence_sha256': target_fence_sha,
                  'disposition': 'original writable; copied target retained and write-fenced; no files removed'}
        if completed_path.exists():
            with pinned_receipt(completed_path, digest(packed(result))) as previous:need(previous == result, 'Rollback receipt changed')
        else:create_new(completed_path, packed(result))
        return result


@bounded_operation
def recover_unactivated_source(source_plan, source_plan_sha256):
    """Recover interrupted source preparation only before any target scope exists.

    This restores permissions on exact original identities; it never copies,
    removes, replaces or rewinds source content. Post-copy recovery must use the
    two-owner rollback transaction, not this pre-copy recovery operation.
    """
    source_plan = Path(source_plan).absolute()
    with pinned_receipt(source_plan, source_plan_sha256) as plan:
        need(plan.get('schema') == PLAN_SCHEMA, 'Unrecognized source recovery plan')
        source = local_root(plan['source_root']); target = local_root(plan['target_root'])
        need(all(not os.path.lexists(target / _relative(scope)) for scope in plan['scopes']),
             'Source recovery refused: a copied target scope exists; use fenced rollback')
        from native_io import DirectoryBoundary
        with DirectoryBoundary(source.anchor, source), NativeItem(source, directory=True) as root, \
                _catalog_owner(source / plan['catalog_relative']):
            original = next(row for row in plan['directories'] if row['relative'] == '')
            need(root.facts['identity'] == original['identity'], 'Original source root identity changed')
            security = Security()
            for record in sorted(plan['security'], key=lambda row: (row['relative'].count('\\'), row['relative'])):
                checkpoint()
                relative = _relative(record['relative'])
                need(any(_inside(relative, scope) for scope in plan['scopes']), 'Recovery entry escapes managed scope')
                with NativeItem(source / relative, directory=record['kind'] == 'directory', writable_security=True) as item:
                    need(item.facts['identity'] == record['identity'], 'Recovery item was replaced; retained')
                    security.restore(item, record['original_security'])
            result = {'schema': 'books-storage-source-recovery-v1', 'generation': plan['generation'],
                      'catalog_id': plan['catalog_id'], 'source_plan_sha256': source_plan_sha256,
                      'source_original': str(source), 'source_root_identity': root.facts['identity'],
                      'restored_items': len(plan['security']), 'disposition': 'source permissions restored; no content changed'}
            output = source_plan.with_name(source_plan.name + '.recovered.json')
            if output.exists():
                with pinned_receipt(output, digest(packed(result))) as previous:need(previous == result, 'Recovery receipt differs')
            else:create_new(output, packed(result))
            return result
