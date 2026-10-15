"""Remove only a verified Windows download marker; never other named streams.

This is a marker operation, not atomic whole-file recovery. The ordinary source
cleanup must independently reacquire its deny-delete lease and recheck streams.
"""
import base64
import configparser
import ctypes
import hashlib
from ctypes import wintypes as W

from native_io import BoundaryError, VerifiedFile, FileInfo, kernel, ordinary

MARKER=':Zone.Identifier:$DATA'
MAX_MARKER=8192

def streams(path):
    class Stream(ctypes.Structure):_fields_=[('size',ctypes.c_longlong),('name',W.WCHAR*296)]
    kernel.FindFirstStreamW.argtypes=[W.LPCWSTR,ctypes.c_int,ctypes.c_void_p,W.DWORD];kernel.FindFirstStreamW.restype=W.HANDLE
    kernel.FindNextStreamW.argtypes=[W.HANDLE,ctypes.c_void_p];kernel.FindNextStreamW.restype=W.BOOL
    kernel.FindClose.argtypes=[W.HANDLE]
    value=Stream();handle=kernel.FindFirstStreamW(str(path),0,ctypes.byref(value),0)
    if handle==ctypes.c_void_p(-1).value:raise BoundaryError('Cannot inspect download-marker streams')
    found=[]
    try:
        while True:
            found.append((value.name,int(value.size)))
            if len(found)>16:raise BoundaryError('Unexpected filesystem streams preserved')
            if not kernel.FindNextStreamW(handle,ctypes.byref(value)):
                if ctypes.get_last_error()!=38:raise BoundaryError('Cannot finish download-marker stream inspection')
                return found
    finally:kernel.FindClose(handle)

class _MarkerLease(VerifiedFile):
    """Allow exact named-stream DELETE while denying data writers.

    DELETE sharing is necessary for the stream disposition. Other deleters can
    move the base name, so identity must be checked again by normal cleanup.
    """
    def __enter__(self):
        self.handle=kernel.CreateFileW(str(self.path),0x81,5,None,3,0x00200000,None)
        if self.handle==ctypes.c_void_p(-1).value:
            self.handle=None;raise BoundaryError('Cannot protect download-marker base file')
        try:
            self.info=FileInfo()
            if not kernel.GetFileInformationByHandle(self.handle,ctypes.byref(self.info)) or self.info.attributes&(0x400|0x10) or self.info.links!=1:
                raise BoundaryError('Download marker base is not a unique ordinary file')
            return self
        except BaseException:self.__exit__(None,None,None);raise

def _known_marker(raw):
    if not raw or len(raw)>MAX_MARKER:raise BoundaryError('Unknown download marker contents preserved')
    try:
        text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
        parser=configparser.ConfigParser(interpolation=None,strict=True);parser.read_string(text)
        allowed={'zoneid','referrerurl','hosturl','lastwriterpackagefamilyname'}
        if parser.defaults() or parser.sections()!=['ZoneTransfer'] or not set(parser['ZoneTransfer'])<=allowed or parser['ZoneTransfer'].get('zoneid') not in {'0','1','2','3','4'}:
            raise ValueError('Unknown marker schema')
    except (ValueError,UnicodeError,configparser.Error) as error:raise BoundaryError('Unknown download marker contents preserved') from error

def remove_marker(path,validate,persist):
    """Validate the current source and journal exact marker bytes before removal.

    Caller holds ordinary ancestry and review scope. validate receives a held
    base file and must prove reviewed source identity/full hash. persist must
    commit the receipt durably before returning. A late unknown stream refuses
    further cleanup, even if the known marker has already been removed.
    """
    path=ordinary(path);found=streams(path)
    if found==[('::$DATA',path.stat().st_size)]:return False
    if {name for name,size in found}!={'::$DATA',MARKER}:
        raise BoundaryError('Additional filesystem streams require review; original retained')
    size=next(size for name,size in found if name==MARKER)
    if not 0<size<=MAX_MARKER:raise BoundaryError('Unknown download marker size preserved')
    with _MarkerLease(path) as original:
        validate(original)
        # This literal suffix is the only ADS path ever accepted by this module.
        handle=kernel.CreateFileW(str(path)+':Zone.Identifier',0x10081,5,None,3,0x00200000,None)
        if handle==ctypes.c_void_p(-1).value:raise BoundaryError('Cannot protect exact download marker')
        try:
            info=FileInfo()
            if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or (info.volume,info.index_high,info.index_low)!=(original.info.volume,original.info.index_high,original.info.index_low) or info.links!=1 or info.attributes&(0x400|0x10):
                raise BoundaryError('Download marker native identity differs')
            actual=(info.size_high<<32)|info.size_low
            if actual!=size:raise BoundaryError('Download marker changed during inspection')
            kernel.ReadFile.argtypes=[W.HANDLE,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD),ctypes.c_void_p];kernel.ReadFile.restype=W.BOOL
            buffer=ctypes.create_string_buffer(MAX_MARKER+1);count=W.DWORD()
            if not kernel.ReadFile(handle,buffer,len(buffer),ctypes.byref(count),None) or count.value!=size:raise BoundaryError('Cannot read bounded download marker')
            raw=buffer.raw[:count.value];_known_marker(raw)
            if streams(path)!=found:raise BoundaryError('Filesystem streams changed; original retained')
            validate(original)
            persist({'schema':'books-zone-identifier-removal-v1','path':str(path),'identity':original.facts()['identity'],
                     'marker_sha256':hashlib.sha256(raw).hexdigest(),'marker_bytes_base64':base64.b64encode(raw).decode('ascii'),'marker_size':len(raw)})
            if streams(path)!=found:raise BoundaryError('Filesystem streams changed after marker intent; original retained')
            class Disposition(ctypes.Structure):_fields_=[('delete',W.BOOL)]
            kernel.SetFileInformationByHandle.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD];kernel.SetFileInformationByHandle.restype=W.BOOL
            disposition=Disposition(True)
            if not kernel.SetFileInformationByHandle(handle,4,ctypes.byref(disposition),ctypes.sizeof(disposition)):
                raise BoundaryError('Download marker disposition refused; no pathname deletion attempted')
        finally:kernel.CloseHandle(handle)
        if streams(path)!=[('::$DATA',original.facts()['size'])]:raise BoundaryError('Additional filesystem streams preserved after marker removal')
        validate(original)
    return True
