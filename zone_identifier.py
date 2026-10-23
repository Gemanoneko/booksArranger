"""Remove only a verified Windows download marker; never other named streams.

This is a marker operation, not atomic whole-file recovery. The ordinary source
cleanup must independently reacquire its deny-delete lease and recheck streams.
"""
import base64
import contextlib
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
            # The stream was opened by the held base file's own name. A library share reports a separate file
            # index for a named stream (seen on Z:, 2026-10-18: base 10420294, stream 10420328), so only the
            # volume, links and attributes are compared; the base file's content is proven by its full hash
            # before and after (validate). Sergei, 2026-10-18: marker metadata alone never holds a cleanup.
            if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or info.volume!=original.info.volume or info.links!=1 or info.attributes&(0x400|0x10):
                raise BoundaryError('Download marker native identity differs')
            actual=(info.size_high<<32)|info.size_low
            if actual!=size:raise BoundaryError('Download marker changed during inspection')
            kernel.ReadFile.argtypes=[W.HANDLE,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD),ctypes.c_void_p];kernel.ReadFile.restype=W.BOOL
            buffer=ctypes.create_string_buffer(MAX_MARKER+1);count=W.DWORD()
            if not kernel.ReadFile(handle,buffer,len(buffer),ctypes.byref(count),None) or count.value!=size:raise BoundaryError('Cannot read bounded download marker')
            # Any bounded content of this exact marker stream is metadata: its bytes go into the durable
            # receipt below, so nothing is lost (Sergei, 2026-10-18: marker contents never hold a cleanup).
            raw=buffer.raw[:count.value]
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


def restore_marker(path,raw):
    """Undo of an in-place edit only (0.21.1): put back the exact marker bytes it journaled and removed.

    Caller holds the base file deny-writers and deny-delete, so the name stays bound to it. The stream is created new
    (never over an existing one) and must then hold exactly these bytes. Writing it moves the base write time, so the
    caller restores that afterwards.
    """
    path=ordinary(path)
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_MARKER:raise BoundaryError('Unknown download marker size preserved')
    handle=kernel.CreateFileW(str(path)+':Zone.Identifier',0x40000000|0x80000000,0,None,1,0x00200000,None)
    if handle==ctypes.c_void_p(-1).value:raise BoundaryError('Cannot restore the download marker')
    try:
        kernel.WriteFile.argtypes=[W.HANDLE,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD),ctypes.c_void_p];kernel.WriteFile.restype=W.BOOL
        kernel.FlushFileBuffers.argtypes=[W.HANDLE];kernel.FlushFileBuffers.restype=W.BOOL
        count=W.DWORD()
        if not kernel.WriteFile(handle,raw,len(raw),ctypes.byref(count),None) or count.value!=len(raw) or not kernel.FlushFileBuffers(handle):
            raise BoundaryError('Cannot restore the download marker')
        kernel.SetFilePointerEx.argtypes=[W.HANDLE,ctypes.c_longlong,ctypes.c_void_p,W.DWORD];kernel.SetFilePointerEx.restype=W.BOOL
        kernel.ReadFile.argtypes=[W.HANDLE,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD),ctypes.c_void_p];kernel.ReadFile.restype=W.BOOL
        buffer=ctypes.create_string_buffer(MAX_MARKER+1)
        if not kernel.SetFilePointerEx(handle,0,None,0) or not kernel.ReadFile(handle,buffer,len(buffer),ctypes.byref(count),None) or buffer.raw[:count.value]!=raw:
            raise BoundaryError('The restored download marker could not be proven')
    finally:kernel.CloseHandle(handle)
    if [size for name,size in streams(path) if name==MARKER]!=[len(raw)]:raise BoundaryError('The restored download marker could not be proven')


@contextlib.contextmanager
def readable_source_streams(path, original):
    """Read-only admission, distinct from deletion-grade single_stream.

    Caller holds ordinary ancestry and VerifiedFile for the whole proof. The
    exact download metadata stream remains intact and locked until admission
    finishes; unknown named streams remain a refusal. Yield a recheck that the
    caller must run before its durable enqueue. This never authorizes cleanup.
    """
    path=ordinary(path);before=original.facts()
    if original.path!=path or before['links']!=1 or original.delete or original.writable:
        raise BoundaryError('Read admission needs the same unique read-only protected source')
    found=streams(path)
    plain=[('::$DATA',before['size'])]
    if found==plain:
        def check():
            if streams(path)!=found:raise BoundaryError('Filesystem streams changed during read admission')
        yield check
        check();return
    if len(found)!=2 or plain[0] not in found or {name for name,size in found}!={'::$DATA',MARKER}:
        raise BoundaryError('Additional filesystem streams require review; original retained')
    size=next(size for name,size in found if name==MARKER)
    if not 0<size<=MAX_MARKER:raise BoundaryError('Unknown download marker size preserved')
    handle=kernel.CreateFileW(str(path)+':Zone.Identifier',0x80000081,1,None,3,0x00200000,None)
    if handle==ctypes.c_void_p(-1).value:raise BoundaryError('Cannot protect read-only download marker')
    try:
        def read_marker():
            info=FileInfo()
            if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or info.volume!=original.info.volume or info.links!=1 or info.attributes&(0x400|0x10):
                raise BoundaryError('Download marker native identity differs')
            if (info.size_high<<32)|info.size_low!=size:raise BoundaryError('Download marker changed during read admission')
            kernel.SetFilePointerEx.argtypes=[W.HANDLE,ctypes.c_longlong,ctypes.c_void_p,W.DWORD];kernel.SetFilePointerEx.restype=W.BOOL
            if not kernel.SetFilePointerEx(handle,0,None,0):raise BoundaryError('Cannot rewind protected download marker')
            kernel.ReadFile.argtypes=[W.HANDLE,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD),ctypes.c_void_p];kernel.ReadFile.restype=W.BOOL
            buffer=ctypes.create_string_buffer(MAX_MARKER+1);count=W.DWORD()
            if not kernel.ReadFile(handle,buffer,len(buffer),ctypes.byref(count),None) or count.value!=size:raise BoundaryError('Cannot read bounded download marker')
            return buffer.raw[:count.value],(info.volume,info.index_high,info.index_low,info.links,info.attributes)
        raw,identity=read_marker()
        # Exact27-byte marker observed on all44 refused library files, not
        # generic NUL stripping or a relaxation of the recognized INI schema.
        observed=bytes.fromhex('5b5a6f6e655472616e736665725d0d0a5a6f6e6549643d330d0a00')
        _known_marker(raw[:-1] if raw==observed else raw)
        def check():
            if original.facts()!=before or streams(path)!=found or read_marker()!=(raw,identity):
                raise BoundaryError('Filesystem streams changed during read admission')
        check();yield check;check()
    finally:kernel.CloseHandle(handle)
