"""Windows directory identity guards and same-directory no-replace publication."""
import contextlib
import ctypes
from ctypes import wintypes
import os
import time
import re
import hashlib
from pathlib import Path

class BoundaryError(ValueError):pass

class FileInUse(BoundaryError):
    """The exact file is open in another program without the sharing this check needs (ERROR_SHARING_VIOLATION).
    Still a BoundaryError: every caller keeps refusing exactly as before. It proves nothing unsafe about the file,
    so a caller may report "try again" rather than "can't confirm it is safe"."""
SHARING_VIOLATION=32

if os.name=='nt':
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    kernel.MoveFileExW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD]
    kernel.MoveFileExW.restype=wintypes.BOOL
    kernel.GetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_void_p]
    kernel.GetFileInformationByHandle.restype=wintypes.BOOL
    # One ABI identity per DLL binding: research and audio launches can overlap.
    # Per-call Structure classes would race on shared ctypes function argtypes.
    class ThreadEntry(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('thread',wintypes.DWORD),('process',wintypes.DWORD),('base',wintypes.LONG),('delta',wintypes.LONG),('flags',wintypes.DWORD)]
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Thread32First.argtypes=[wintypes.HANDLE,ctypes.POINTER(ThreadEntry)];kernel.Thread32First.restype=wintypes.BOOL
    kernel.Thread32Next.argtypes=[wintypes.HANDLE,ctypes.POINTER(ThreadEntry)];kernel.Thread32Next.restype=wintypes.BOOL
    kernel.OpenThread.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenThread.restype=wintypes.HANDLE
    kernel.ResumeThread.argtypes=[wintypes.HANDLE];kernel.ResumeThread.restype=wintypes.DWORD
    kernel.GetProcessIdOfThread.argtypes=[wintypes.HANDLE];kernel.GetProcessIdOfThread.restype=wintypes.DWORD
    class FileInfo(ctypes.Structure):
        _fields_=[('attributes',wintypes.DWORD),('creation',wintypes.FILETIME),('access',wintypes.FILETIME),('write',wintypes.FILETIME),('volume',wintypes.DWORD),('size_high',wintypes.DWORD),('size_low',wintypes.DWORD),('links',wintypes.DWORD),('index_high',wintypes.DWORD),('index_low',wintypes.DWORD)]

def ordinary(path):
    value=str(path)
    if not os.path.isabs(value) or value.startswith(('\\\\?\\','\\\\.\\')):
        raise BoundaryError('Only ordinary absolute filesystem paths are accepted')
    parts=Path(value).parts
    if any(part in {'.','..'} or ':' in part for part in parts[1:]):
        raise BoundaryError('Traversal and alternate data streams are rejected')
    reserved={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
    if any(re.search(r'[<>"|?*\x00-\x1f]',part) or part.endswith(('.', ' ')) or part.upper().split('.')[0] in reserved for part in parts[1:]):
        raise BoundaryError('Special/device-shaped destination or source path is rejected')
    return Path(os.path.abspath(value))

class DirectoryBoundary:
    """Hold ancestor directory handles without write/delete sharing during publication."""
    def __init__(self,root,parent,create=False,*,writable_parent=False,rename_destination=False):
        if type(writable_parent) is not bool:raise BoundaryError('Writable parent capability must be explicit')
        if type(rename_destination) is not bool:raise BoundaryError('Rename destination capability must be explicit')
        if rename_destination and writable_parent:raise BoundaryError('Rename destination capability is separate from writable publication')
        self.writable_parent=writable_parent;self.rename_destination=rename_destination
        self.root=ordinary(root);self.parent=ordinary(parent);self.create=create
        self.handles=[];self.identities=[]
        try:self.parent.relative_to(self.root)
        except ValueError:raise BoundaryError('Destination is outside the configured library')

    def __enter__(self):
        if os.name!='nt':raise BoundaryError('Verified Windows no-replace publication is unavailable on this platform')
        parts=self.parent.parts
        current=Path(parts[0])
        try:
            for index in range(len(parts)):
                if index:current=current/parts[index]
                if not current.exists():
                    if not self.create or not current.is_relative_to(self.root):
                        raise BoundaryError('An inspected destination ancestor is unavailable')
                    current.mkdir()
                if current.is_symlink() or os.path.isjunction(current):
                    raise BoundaryError('Destination ancestor is a symlink or junction')
                # OPEN_REPARSE_POINT prevents transparently following a swapped reparse entry.
                # READ_ATTRIBUTES alone does not participate in Windows sharing
                # checks. LIST_DIRECTORY makes deny-delete sharing effective.
                access=0x81 | (0x40000000 if self.writable_parent and index==len(parts)-1 else 0)
                # Win32 absolute rename opens the destination leaf for directory writes.
                # Only this explicit rename leaf shares WRITE; every ancestor and
                # every default/copy guard still denies WRITE and DELETE.
                share=3 if self.rename_destination and index==len(parts)-1 else 1
                handle=kernel.CreateFileW(str(current),access,share,None,3,0x02000000|0x00200000,None)
                if handle==ctypes.c_void_p(-1).value:
                    raise BoundaryError(f'Destination directory cannot be protected: {ctypes.WinError(ctypes.get_last_error())}')
                self.handles.append(handle)
                info=FileInfo()
                if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)):
                    raise BoundaryError('Cannot inspect destination directory identity')
                if info.attributes&0x400 or not info.attributes&0x10:
                    raise BoundaryError('Destination ancestry contains an unexpected reparse entry or non-directory')
                self.identities.append((str(current),info.volume,info.index_high,info.index_low))
            return self
        except BaseException:
            self.__exit__(None,None,None)
            raise

    def revalidate(self):
        for handle,identity in zip(self.handles,self.identities):
            info=FileInfo()
            if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or info.attributes&0x400:
                raise BoundaryError('Destination boundary changed during publication')
            if (info.volume,info.index_high,info.index_low)!=identity[1:]:
                raise BoundaryError('Destination directory identity drifted')

    def __exit__(self,*_):
        for handle in reversed(self.handles):kernel.CloseHandle(handle)
        self.handles=[]

def publish_no_replace(temporary,destination,boundary,expected_sha256=None,expected_size=None,before_rename=None):
    temporary=ordinary(temporary);destination=ordinary(destination)
    if temporary.parent!=destination.parent or destination.parent!=boundary.parent:
        raise BoundaryError('Publication requires an owned same-directory temporary')
    boundary.revalidate()
    # Rename the verified file HANDLE, not a name which can be swapped. Deny
    # other writers/deleters while holding our own DELETE access for the rename.
    handle=kernel.CreateFileW(str(temporary),0x10081,1,None,3,0x00200000,None)
    if handle==ctypes.c_void_p(-1).value:raise BoundaryError('Cannot protect owned destination temporary')
    try:
        info=FileInfo()
        if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or info.attributes&(0x400|0x10):
            raise BoundaryError('Publication temporary is not an ordinary file')
        size=(info.size_high<<32)|info.size_low
        if expected_size is not None and size!=expected_size:raise BoundaryError('Publication temporary size differs from checked output')
        kernel.ReadFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
        kernel.ReadFile.restype=wintypes.BOOL
        hash=hashlib.sha256();buffer=ctypes.create_string_buffer(1024*1024);count=wintypes.DWORD()
        while True:
            if not kernel.ReadFile(handle,buffer,len(buffer),ctypes.byref(count),None):raise BoundaryError('Cannot read protected publication temporary')
            if not count.value:break
            hash.update(buffer.raw[:count.value])
        if expected_sha256 is not None and hash.hexdigest()!=expected_sha256:raise BoundaryError('Publication temporary bytes differ from checked output')
        target=destination.name
        encoded=target.encode('utf-16-le')
        class Rename(ctypes.Structure):
            _fields_=[('replace',wintypes.BOOLEAN),('root',wintypes.HANDLE),('length',wintypes.DWORD),('name',wintypes.WCHAR*(len(encoded)//2+1))]
        rename=Rename();rename.replace=False;rename.root=None;rename.length=len(encoded)
        ctypes.memmove(ctypes.addressof(rename)+Rename.name.offset,encoded,len(encoded))
        # A simple name with NULL RootDirectory renames within the protected
        # source file's existing parent. No absolute-path target lookup occurs.
        nt=ctypes.WinDLL('ntdll',use_last_error=True)
        class StatusBlock(ctypes.Structure):_fields_=[('status',ctypes.c_void_p),('information',ctypes.c_size_t)]
        nt.NtSetInformationFile.argtypes=[wintypes.HANDLE,ctypes.POINTER(StatusBlock),ctypes.c_void_p,wintypes.ULONG,ctypes.c_int];nt.NtSetInformationFile.restype=wintypes.LONG
        nt.RtlNtStatusToDosError.argtypes=[wintypes.LONG];nt.RtlNtStatusToDosError.restype=wintypes.ULONG
        boundary.revalidate()
        if before_rename:before_rename({'identity':[info.volume,info.index_high,info.index_low],'sha256':hash.hexdigest(),'size':size})
        status=StatusBlock();result=nt.NtSetInformationFile(handle,ctypes.byref(status),ctypes.byref(rename),ctypes.sizeof(rename),10)
        if result<0:
            error=nt.RtlNtStatusToDosError(result)
            if error in {80,183}:raise FileExistsError('Destination collision; existing file was preserved')
            raise BoundaryError(f'Handle-bound no-replace publication failed: {ctypes.WinError(error)}')
    finally:kernel.CloseHandle(handle)

class RenamePostconditionError(BoundaryError):
    """The OS accepted rename; retain its durable intent for reconciliation.

    Never respond by copying, recreating the old name or assuming no change.
    """


def rename_no_replace(source,destination,source_boundary,destination_boundary,*,expected_identity,expected_size,expected_sha256):
    """Rename this caller-held DELETE handle, without copying or replacement.

    The caller must prove full content on this SAME retained native identity
    (recording a fresh-hash or accepted-cache basis), then keep its deny-writer
    handle held through durable catalog commit. No bytes are re-read here.
    This function supplies name/native identity proof, not catalog durability.
    """
    if os.name!='nt':raise BoundaryError('Handle-bound rename requires Windows')
    if not isinstance(source,VerifiedFile) or not source.handle or source.delete is not True:
        raise BoundaryError('Rename requires the already-held source DELETE capability')
    old=ordinary(source.path);destination=ordinary(destination)
    if os.path.normcase(str(old))==os.path.normcase(str(destination)):
        raise BoundaryError('Rename requires a distinct destination name')
    if (not isinstance(source_boundary,DirectoryBoundary) or not isinstance(destination_boundary,DirectoryBoundary)
        or not source_boundary.handles or not destination_boundary.handles
        or old.parent!=source_boundary.parent or destination.parent!=destination_boundary.parent):
        raise BoundaryError('Rename requires both retained exact parent boundaries')
    if type(expected_size) is not int or expected_size<0 or not isinstance(expected_sha256,str) or not re.fullmatch('[0-9a-f]{64}',expected_sha256):
        raise BoundaryError('Exact previously checked content size/SHA256 required')

    def refresh(handle,path):
        view=VerifiedFile(path);view.handle=handle;view.info=FileInfo()
        if not kernel.GetFileInformationByHandle(handle,ctypes.byref(view.info)):
            raise BoundaryError('Rename native identity refresh failed')
        return view.info,view.facts()

    def ordinary_unique(facts):
        if facts['links']!=1 or facts['attributes']&(0x400|0x10):raise BoundaryError('Rename requires a unique ordinary source')
        if (facts['identity_method']=='FileIdInfo128' and facts['identity_api_error']==0
            or facts['identity_method']=='BY_HANDLE_FILE_INFORMATION64' and facts['identity_api_error'] in {1,50,87}):return
        raise BoundaryError('Rename native identity method is unknown')

    def named(path,expected):
        # Only this temporary read-open shares DELETE, so it can coexist with
        # OUR original DELETE handle. That original still denies other deleters.
        handle=kernel.CreateFileW(str(path),0x81,1|4,None,3,0x00200000,None)
        if handle==ctypes.c_void_p(-1).value:raise BoundaryError('Rename named-file proof open refused')
        try:
            _,facts=refresh(handle,path);ordinary_unique(facts)
            if facts!=expected:raise BoundaryError('Renamed pathname does not name the held source identity')
            return facts
        finally:
            if not kernel.CloseHandle(handle):raise BoundaryError('Rename named-file proof checked-close failed')

    source_boundary.revalidate();destination_boundary.revalidate()
    source.info,before=refresh(source.handle,old);ordinary_unique(before)
    if type(expected_identity) is not dict or before!=expected_identity or before['size']!=expected_size:
        raise BoundaryError('Rename held source differs from its complete checked identity/size')
    named(old,before)
    old_parent=FileInfo();new_parent=FileInfo()
    if (not kernel.GetFileInformationByHandle(source_boundary.handles[-1],ctypes.byref(old_parent))
        or not kernel.GetFileInformationByHandle(destination_boundary.handles[-1],ctypes.byref(new_parent))
        or any(info.attributes&0x400 or not info.attributes&0x10 for info in (old_parent,new_parent))):
        raise BoundaryError('Rename parent native identity unavailable')
    if not old_parent.volume or old_parent.volume!=source.info.volume or new_parent.volume!=old_parent.volume:
        raise BoundaryError('Rename requires matching native source/destination volumes')
    if os.path.lexists(destination):raise FileExistsError('Rename destination exists; both files preserved')
    encoded=str(destination).encode('utf-16-le')
    if not encoded or len(encoded)>65532:raise BoundaryError('Rename absolute wide destination exceeds bound')
    class Rename(ctypes.Structure):
        _fields_=[('replace',wintypes.BOOLEAN),('root',wintypes.HANDLE),('length',wintypes.DWORD),
                  ('name',wintypes.WCHAR*(len(encoded)//2+1))]
    rename=Rename();rename.replace=False;rename.root=None;rename.length=len(encoded)
    ctypes.memmove(ctypes.addressof(rename)+Rename.name.offset,encoded,len(encoded))
    kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.SetFileInformationByHandle.restype=wintypes.BOOL
    source_boundary.revalidate();destination_boundary.revalidate()
    if not kernel.SetFileInformationByHandle(source.handle,3,ctypes.byref(rename),ctypes.sizeof(rename)):
        error=ctypes.get_last_error()
        if error in {80,183}:raise FileExistsError('Rename destination collision; existing file preserved')
        raise BoundaryError(f'No-copy handle-bound rename refused (Windows error {error})')
    try:
        source.info,after=refresh(source.handle,destination);ordinary_unique(after)
        if after!=before:raise BoundaryError('Held source identity changed across rename')
        destination_facts=named(destination,after)
        source_boundary.revalidate();destination_boundary.revalidate()
        if os.path.lexists(old):raise BoundaryError('Old pathname remains or was replaced after rename')
        return {'schema':'books-native-no-copy-rename-v1','old_path':str(old),'final_path':str(destination),
            'identity':after['identity'],'source_native_before':before,'source_native_after':after,
            'destination_native':destination_facts,'sha256':expected_sha256,'size':expected_size,
            'content_basis':'Caller-proven full content on same retained identity; denywriters across rename (caller records fresh-hash or accepted-cache basis)',
            'source_delete_handle_still_held':True,'named_read_handle_checked_closed':True,
            'old_absent':True,'no_replace':True,'copy_fallback':False,
            'api':'SetFileInformationByHandle(FileRenameInfo)','root_directory_null':True,
            'absolute_destination_utf16_bytes':len(encoded)}
    except BaseException as error:
        raise RenamePostconditionError('OS rename accepted; postcondition unproved, retain durable rename intent: '+str(error)) from error

class ProtectedFiles:
    """Deny write/delete access to owned immutable snapshots while media tools read them."""
    def __init__(self,paths):self.paths=paths;self.handles=[]
    def __enter__(self):
        try:
            for path in self.paths:
                handle=kernel.CreateFileW(str(ordinary(path)),0x81,1,None,3,0x00200000,None)
                if handle==ctypes.c_void_p(-1).value:raise BoundaryError('Cannot protect source snapshot from modification')
                self.handles.append(handle)
                info=FileInfo()
                if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or info.attributes&(0x400|0x10):
                    raise BoundaryError('Source snapshot is not an ordinary protected file')
            return self
        except BaseException:self.__exit__(None,None,None);raise
    def __exit__(self,*_):
        for handle in reversed(self.handles):kernel.CloseHandle(handle)
        self.handles=[]

class VerifiedFile:
    """Read/hash/dispose one exact ordinary identity; never delete a pathname.

    DELETE access is acquired only by a caller that holds the source ancestry.
    Denying both WRITE and DELETE prevents replacement until close. Hashing uses
    this same native handle so no higher-level reopening weakens the identity.
    """
    def __init__(self,path,delete=False,writable=False):
        self.path=ordinary(path);self.delete=delete;self.writable=writable;self.handle=None
    def __enter__(self):
        if os.name!='nt':raise BoundaryError('Verified file disposition requires Windows')
        self.handle=kernel.CreateFileW(str(self.path),0x81|(0x10000 if self.delete else 0)|(0x40000000 if self.writable else 0),1,None,3,0x00200000,None)
        if self.handle==ctypes.c_void_p(-1).value:
            code=ctypes.get_last_error();self.handle=None
            raise (FileInUse if code==SHARING_VIOLATION else BoundaryError)(f'Cannot protect exact file: {ctypes.WinError(code)}')
        try:
            info=FileInfo()
            if not kernel.GetFileInformationByHandle(self.handle,ctypes.byref(info)) or info.attributes&(0x400|0x10):
                raise BoundaryError('Expected an ordinary non-reparse file')
            self.info=info
            return self
        except BaseException:self.__exit__(None,None,None);raise
    def facts(self):
        i=self.info
        ticks=(i.write.dwHighDateTime<<32)|i.write.dwLowDateTime
        class FileId(ctypes.Structure):_fields_=[('volume',ctypes.c_ulonglong),('id',ctypes.c_ubyte*16)]
        kernel.GetFileInformationByHandleEx.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];kernel.GetFileInformationByHandleEx.restype=wintypes.BOOL
        extended=FileId();available=kernel.GetFileInformationByHandleEx(self.handle,18,ctypes.byref(extended),ctypes.sizeof(extended))
        error=ctypes.get_last_error() if not available else 0
        if not available and error not in (1,50,87):raise BoundaryError('Cannot verify protected file identity')
        if not i.volume or not (i.index_high or i.index_low) or available and (not extended.volume or not any(extended.id)):
            raise BoundaryError('Protected file identity is zero or ambiguous')
        return {'size':(i.size_high<<32)|i.size_low,'modified':(ticks-116444736000000000)*100,
            'dev':extended.volume if available else i.volume,'ino':int.from_bytes(bytes(extended.id),'little') if available else (i.index_high<<32)|i.index_low,
            'identity_method':'FileIdInfo128' if available else 'BY_HANDLE_FILE_INFORMATION64','identity_api_error':error,
            'identity':[i.volume,i.index_high,i.index_low],'links':i.links,'attributes':i.attributes}
    def chunks(self):
        kernel.SetFilePointerEx.argtypes=[wintypes.HANDLE,ctypes.c_longlong,ctypes.c_void_p,wintypes.DWORD]
        kernel.SetFilePointerEx.restype=wintypes.BOOL
        kernel.ReadFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
        kernel.ReadFile.restype=wintypes.BOOL
        if not kernel.SetFilePointerEx(self.handle,0,None,0):raise BoundaryError('Cannot rewind protected file')
        buffer=ctypes.create_string_buffer(1024*1024);count=wintypes.DWORD()
        while True:
            if not kernel.ReadFile(self.handle,buffer,len(buffer),ctypes.byref(count),None):raise BoundaryError('Protected file read failed')
            if not count.value:break
            yield buffer.raw[:count.value]
    def sha256(self):
        value=hashlib.sha256()
        for block in self.chunks():value.update(block)
        return value.hexdigest()
    def flush(self):
        if not self.writable:raise BoundaryError('Recovery durability requires its owned write-capable handle')
        kernel.FlushFileBuffers.argtypes=[wintypes.HANDLE];kernel.FlushFileBuffers.restype=wintypes.BOOL
        if not kernel.FlushFileBuffers(self.handle):raise BoundaryError('Recovery storage cannot satisfy the required durable flush')
    def restore_metadata(self,modified,attributes):
        if not self.writable or attributes&~0xA0:raise BoundaryError('Unsupported recoverable source attributes')
        class Basic(ctypes.Structure):_fields_=[('creation',ctypes.c_longlong),('access',ctypes.c_longlong),('write',ctypes.c_longlong),('change',ctypes.c_longlong),('attributes',wintypes.DWORD)]
        value=Basic();value.write=int(modified)//100+116444736000000000;value.attributes=attributes or 0x80
        kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];kernel.SetFileInformationByHandle.restype=wintypes.BOOL
        if not kernel.SetFileInformationByHandle(self.handle,0,ctypes.byref(value),ctypes.sizeof(value)):raise BoundaryError('Cannot preserve recovery timestamps/attributes')
        if not kernel.GetFileInformationByHandle(self.handle,ctypes.byref(self.info)):raise BoundaryError('Cannot verify restored filesystem metadata')
    def dispose(self):
        if not self.delete:raise BoundaryError('File was not opened for exact-handle removal')
        kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        kernel.SetFileInformationByHandle.restype=wintypes.BOOL
        value=wintypes.BOOL(True)
        if not kernel.SetFileInformationByHandle(self.handle,4,ctypes.byref(value),ctypes.sizeof(value)):
            raise BoundaryError(f'Exact-handle removal is unsupported or denied: {ctypes.WinError(ctypes.get_last_error())}')
    def __exit__(self,*_):
        if self.handle is not None:kernel.CloseHandle(self.handle);self.handle=None

class DirectoryNotEmptyError(BoundaryError):pass
class DirectoryDispositionUnsupported(BoundaryError):pass

class VerifiedDirectory(VerifiedFile):
    """Protect one ordinary directory; disposition never removes contents.

    The caller holds ancestors only through the target's parent. A separate
    ancestor handle on the target would conflict with its own DELETE access.
    Windows FileDispositionInfo checks emptiness atomically and refuses new
    children after delete-pending, without a recursive/pathname fallback.
    """
    def __enter__(self):
        if os.name!='nt':raise BoundaryError('Verified empty-directory disposition requires Windows')
        self.handle=kernel.CreateFileW(str(self.path),0x81|(0x10000 if self.delete else 0),1,None,3,0x02000000|0x00200000,None)
        if self.handle==ctypes.c_void_p(-1).value:
            error=ctypes.get_last_error();self.handle=None
            if error in (2,3):raise FileNotFoundError(str(self.path))
            raise BoundaryError(f'Cannot protect exact directory: {ctypes.WinError(error)}')
        try:
            info=FileInfo()
            if not kernel.GetFileInformationByHandle(self.handle,ctypes.byref(info)) or info.attributes&0x400 or not info.attributes&0x10:
                raise BoundaryError('Expected an ordinary non-reparse directory')
            self.info=info
            return self
        except BaseException:self.__exit__(None,None,None);raise
    def facts(self):
        facts=super().facts();i=self.info
        return {k:facts[k] for k in ('identity','identity_method','identity_api_error','dev','ino')}|{'created':(i.creation.dwHighDateTime<<32)|i.creation.dwLowDateTime}
    def empty(self):
        # All names, including hidden entries and .git, are substantive. The
        # target identity cannot be renamed/replaced while this handle is held.
        with os.scandir(self.path) as entries:
            if next(entries,None) is not None:return False
        class Stream(ctypes.Structure):_fields_=[('size',ctypes.c_longlong),('name',wintypes.WCHAR*296)]
        kernel.FindFirstStreamW.argtypes=[wintypes.LPCWSTR,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];kernel.FindFirstStreamW.restype=wintypes.HANDLE
        kernel.FindNextStreamW.argtypes=[wintypes.HANDLE,ctypes.c_void_p];kernel.FindNextStreamW.restype=wintypes.BOOL
        kernel.FindClose.argtypes=[wintypes.HANDLE]
        stream=Stream();h=kernel.FindFirstStreamW(str(self.path),0,ctypes.byref(stream),0)
        if h==ctypes.c_void_p(-1).value:
            if ctypes.get_last_error()==38:return True # A streamless directory.
            raise BoundaryError('Cannot verify empty-directory filesystem streams')
        try:
            while True:
                if stream.name!='::$DATA' or stream.size:return False
                if not kernel.FindNextStreamW(h,ctypes.byref(stream)):
                    if ctypes.get_last_error()!=38:raise BoundaryError('Cannot finish directory-stream verification')
                    return True
        finally:kernel.FindClose(h)
    def require_empty_disposition(self):
        """Only an unambiguous local, streamless exact-handle volume can remove.

        Named streams have their own sharing namespace. Directory DELETE
        sharing and enumeration cannot exclude an arriving ADS on NTFS. The
        native disposition itself must therefore refuse such a capability.
        No mapped/path-volume fallback or extra scan establishes atomic safety.
        """
        if self.handle is None:raise DirectoryDispositionUnsupported('Empty source folder retained: exact directory handle is unavailable')
        try:
            api=kernel.GetVolumeInformationByHandleW
            api.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.POINTER(wintypes.DWORD),ctypes.POINTER(wintypes.DWORD),wintypes.LPWSTR,wintypes.DWORD];api.restype=wintypes.BOOL
            serial=wintypes.DWORD();maximum=wintypes.DWORD();flags=wintypes.DWORD();filesystem=ctypes.create_unicode_buffer(261)
            if not api(self.handle,None,0,ctypes.byref(serial),ctypes.byref(maximum),ctypes.byref(flags),filesystem,len(filesystem)):
                raise DirectoryDispositionUnsupported(f'Empty source folder retained: exact-handle filesystem capability is unavailable (Windows error {ctypes.get_last_error()})')
            if not serial.value or serial.value!=self.info.volume or not filesystem.value or not maximum.value:
                raise DirectoryDispositionUnsupported('Empty source folder retained: filesystem capability or volume identity is ambiguous')
            if flags.value&0x40000:
                raise DirectoryDispositionUnsupported(f'Empty source folder retained: {filesystem.value} supports named data streams; arriving directory stream data cannot be protected atomically')
            final=kernel.GetFinalPathNameByHandleW
            final.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD];final.restype=wintypes.DWORD
            location=ctypes.create_unicode_buffer(32768);length=final(self.handle,location,len(location),1) # VOLUME_NAME_GUID, no mapped-name fallback.
            if not length or length>=len(location) or not location.value.startswith('\\\\?\\Volume{'):
                raise DirectoryDispositionUnsupported('Empty source folder retained: a local exact-handle volume provider cannot be established')
            if len(location.value)<49 or location.value[47]!='}' or ord(location.value[48])!=92 or not re.fullmatch(r'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}',location.value[11:47]) or location.value[11:47].replace('-','')=='0'*32:
                raise DirectoryDispositionUnsupported('Empty source folder retained: exact-handle volume provider identity is ambiguous')
            return {'filesystem':filesystem.value,'volume_serial':serial.value,'flags':flags.value,'local_volume_path':location.value}
        except AttributeError as error:
            raise DirectoryDispositionUnsupported('Empty source folder retained: exact-handle filesystem capability API is unavailable') from error
    def dispose_empty(self):
        self.require_empty_disposition() # Safety floor even when called outside StorageCleanup.
        if not self.delete:raise BoundaryError('Directory was not opened for exact-handle removal')
        if not self.empty():raise DirectoryNotEmptyError('Nonempty source folder retained')
        kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];kernel.SetFileInformationByHandle.restype=wintypes.BOOL
        value=wintypes.BOOL(True)
        if not kernel.SetFileInformationByHandle(self.handle,4,ctypes.byref(value),ctypes.sizeof(value)):
            error=ctypes.get_last_error()
            if error==145:raise DirectoryNotEmptyError('A new source-folder entry was retained')
            raise BoundaryError(f'Exact empty-directory disposition is unsupported or denied: {ctypes.WinError(error)}')

class OwnedProcessJob:
    """Kill-on-close Windows job contains only the newly launched media process tree."""
    def __init__(self,process):self.process=process;self.handle=None
    def __enter__(self):
        class Basic(ctypes.Structure):
            _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),('flags',wintypes.DWORD),('min_working',ctypes.c_size_t),('max_working',ctypes.c_size_t),('active',wintypes.DWORD),('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(name,ctypes.c_ulonglong) for name in ['read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes']]
        class Extended(ctypes.Structure):
            _fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];kernel.CreateJobObjectW.restype=wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];kernel.SetInformationJobObject.restype=wintypes.BOOL
        kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE];kernel.AssignProcessToJobObject.restype=wintypes.BOOL
        self.handle=kernel.CreateJobObjectW(None,None)
        if not self.handle:raise BoundaryError('Cannot create an owned media process job')
        info=Extended();info.basic.flags=0x2000
        if not kernel.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)) or not kernel.AssignProcessToJobObject(self.handle,wintypes.HANDLE(int(self.process._handle))):
            self.__exit__(None,None,None)
            raise BoundaryError('Cannot establish owned media-process cancellation on this host')
        if getattr(self.process,'_books_suspended',False):
            try:resume_owned_primary(self.process.pid)
            except BaseException:self.__exit__(None,None,None);raise
        return self
    def __exit__(self,*_):
        if not self.handle:return
        processes=[]
        class Accounting(ctypes.Structure):
            _fields_=[('user',ctypes.c_longlong),('system',ctypes.c_longlong),('period_user',ctypes.c_longlong),('period_system',ctypes.c_longlong),('faults',wintypes.DWORD),('total',wintypes.DWORD),('active',wintypes.DWORD),('terminated',wintypes.DWORD)]
        kernel.QueryInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p];kernel.QueryInformationJobObject.restype=wintypes.BOOL
        kernel.TerminateJobObject.argtypes=[wintypes.HANDLE,wintypes.UINT];kernel.TerminateJobObject.restype=wintypes.BOOL
        try:
            info=Accounting()
            if not kernel.QueryInformationJobObject(self.handle,1,ctypes.byref(info),ctypes.sizeof(info),None):
                raise BoundaryError('Cannot verify owned media-process tree completion')
            if info.active:
                class ProcessList(ctypes.Structure):
                    _fields_=[('assigned',wintypes.DWORD),('count',wintypes.DWORD),('ids',ctypes.c_size_t*1024)]
                listed=ProcessList()
                if not kernel.QueryInformationJobObject(self.handle,3,ctypes.byref(listed),ctypes.sizeof(listed),None):
                    kernel.TerminateJobObject(self.handle,1)
                    raise BoundaryError('Cannot inspect owned cancellation process handles')
                kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
                kernel.IsProcessInJob.argtypes=[wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL)];kernel.IsProcessInJob.restype=wintypes.BOOL
                kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
                for pid in list(listed.ids)[:listed.count]:
                    process=kernel.OpenProcess(0x100000|0x1000,False,pid)
                    if process:
                        member=wintypes.BOOL()
                        if kernel.IsProcessInJob(process,self.handle,ctypes.byref(member)) and member.value:processes.append(process)
                        else:kernel.CloseHandle(process)
                if not kernel.TerminateJobObject(self.handle,1):raise BoundaryError('Cannot cancel the owned media-process tree')
                deadline=time.monotonic()+3
                while info.active and time.monotonic()<deadline:
                    time.sleep(.02)
                    if not kernel.QueryInformationJobObject(self.handle,1,ctypes.byref(info),ctypes.sizeof(info),None):raise BoundaryError('Cannot verify media cancellation')
                if info.active:raise BoundaryError('Owned media process tree has not finished stopping')
                # Accounting can reach zero before process teardown releases its
                # inherited files. Wait on exact owned handles, never a reused PID.
                for process in processes:
                    remaining=max(0,int((deadline-time.monotonic())*1000))
                    if kernel.WaitForSingleObject(process,remaining)!=0:raise BoundaryError('Owned process teardown has not completed')
        finally:
            for process in processes:kernel.CloseHandle(process)
            kernel.CloseHandle(self.handle);self.handle=None

def resume_owned_primary(pid):
    """Resume only the sole primary thread of our newly suspended owned process."""
    snapshot=kernel.CreateToolhelp32Snapshot(4,0)
    if snapshot==ctypes.c_void_p(-1).value:raise BoundaryError('Cannot inspect owned suspended primary thread')
    ids=[]
    try:
        entry=ThreadEntry();entry.size=ctypes.sizeof(entry);found=kernel.Thread32First(snapshot,ctypes.byref(entry))
        while found:
            if entry.process==pid:ids.append(entry.thread)
            found=kernel.Thread32Next(snapshot,ctypes.byref(entry))
    finally:kernel.CloseHandle(snapshot)
    if len(ids)!=1:raise BoundaryError('Owned process must have exactly one suspended primary thread')
    thread=kernel.OpenThread(0x42,False,ids[0])
    if not thread:raise BoundaryError('Cannot open owned suspended primary thread')
    try:
        if kernel.GetProcessIdOfThread(thread)!=pid or kernel.ResumeThread(thread)!=1:raise BoundaryError('Cannot safely resume owned primary thread')
    finally:kernel.CloseHandle(thread)
