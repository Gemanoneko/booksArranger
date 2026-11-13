"""Retain a whole original application directory without copying its identities.

This is a same-parent native rename, never directory deletion, merging or a
general reparse bypass. The caller retains its independently verified package
members and publishes its installation transaction/rollback receipt.
"""
import ctypes
import contextlib
from ctypes import wintypes
import os
from pathlib import Path

from native_io import DirectoryBoundary,FileInfo,kernel,ordinary


class DirectoryRetentionRefused(ValueError):pass


def _need(condition,message):
    if not condition:raise DirectoryRetentionRefused(message)


@contextlib.contextmanager
def _rename_parent(path):
    # Namespace renames need WRITE sharing on the immediate parent. Holding all
    # ancestors and denying DELETE on this actual parent still freezes its path;
    # competing destination arrivals are handled by native no-replace semantics.
    _need(path.parent!=path,'A drive root is not an application retention parent')
    with DirectoryBoundary(path.anchor,path.parent) as ancestors:
        handle=kernel.CreateFileW(str(path),0x81,3,None,3,0x02000000|0x00200000,None)
        if handle==ctypes.c_void_p(-1).value:raise DirectoryRetentionRefused('Cannot retain application rename parent')
        try:
            original=FileInfo()
            _need(kernel.GetFileInformationByHandle(handle,ctypes.byref(original)) and
                original.attributes&0x10 and not original.attributes&0x400,'Application rename parent is not ordinary')
            class Lease:
                def revalidate(self):
                    ancestors.revalidate();now=FileInfo()
                    _need(kernel.GetFileInformationByHandle(handle,ctypes.byref(now)) and
                        (now.volume,now.index_high,now.index_low)==(original.volume,original.index_high,original.index_low),
                        'Application rename parent identity changed')
            lease=Lease();lease.handle=handle
            yield lease
        finally:kernel.CloseHandle(handle)


def _atomic_fresh_directory(parent,name):
    class Unicode(ctypes.Structure):
        _fields_=[('length',wintypes.USHORT),('maximum',wintypes.USHORT),('buffer',wintypes.LPWSTR)]
    class Attributes(ctypes.Structure):
        _fields_=[('length',wintypes.ULONG),('root',wintypes.HANDLE),('name',ctypes.POINTER(Unicode)),
            ('flags',wintypes.ULONG),('security',ctypes.c_void_p),('qos',ctypes.c_void_p)]
    class Status(ctypes.Structure):
        _fields_=[('status',ctypes.c_void_p),('information',ctypes.c_size_t)]
    text=ctypes.create_unicode_buffer(name)
    value=Unicode(len(name.encode('utf-16-le')),ctypes.sizeof(text),ctypes.cast(text,wintypes.LPWSTR))
    attrs=Attributes(ctypes.sizeof(Attributes),parent.handle,ctypes.pointer(value),0x40,None,None)
    api=ctypes.WinDLL('ntdll');api.NtCreateFile.argtypes=[ctypes.POINTER(wintypes.HANDLE),wintypes.DWORD,
        ctypes.POINTER(Attributes),ctypes.POINTER(Status),ctypes.c_void_p,wintypes.ULONG,wintypes.ULONG,
        wintypes.ULONG,wintypes.ULONG,ctypes.c_void_p,wintypes.ULONG];api.NtCreateFile.restype=wintypes.LONG
    handle=wintypes.HANDLE();status=Status()
    result=api.NtCreateFile(ctypes.byref(handle),0x100081,ctypes.byref(attrs),ctypes.byref(status),None,0x10,1,2,0x200021,None,0)
    _need(result>=0 and status.information==2,'Original retained, but atomic creation of a fresh application directory refused; preserve both locations')
    return handle


def retain_directory_no_replace(source,retained,expected_identity):
    source=ordinary(source);retained=ordinary(retained)
    _need(source.parent==retained.parent and source!=retained,
          'Original application retention requires a distinct same-parent location')
    _need(isinstance(expected_identity,(list,tuple)) and len(expected_identity)==3 and
          all(type(n) is int and n>=0 for n in expected_identity),'Expected original directory native identity is required')
    kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.SetFileInformationByHandle.restype=wintypes.BOOL
    kernel.CreateDirectoryW.argtypes=[wintypes.LPCWSTR,ctypes.c_void_p]
    kernel.CreateDirectoryW.restype=wintypes.BOOL
    with _rename_parent(source.parent) as parent:
        _need(not os.path.lexists(retained),'Retained original destination already exists; no merge is allowed')
        handle=kernel.CreateFileW(str(source),0x10000|0x20000|0x81,1,None,3,0x02000000|0x00200000,None)
        if handle==ctypes.c_void_p(-1).value:
            raise DirectoryRetentionRefused('Original application cannot be retained by its exact native handle: '+str(ctypes.WinError(ctypes.get_last_error())))
        try:
            info=FileInfo()
            _need(kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) and
                  info.attributes & 0x10 and not info.attributes & 0x400 and
                  [info.volume,info.index_high,info.index_low]==list(expected_identity),
                  'Original application root identity/type changed')
            # FILE_RENAME_INFO's union is DWORD-sized. This Win32 API uses an
            # absolute destination; every ordinary ancestor and the SAME parent
            # remain held. Flags zero never replaces an existing name.
            encoded=str(retained).encode('utf-16-le')
            class Rename(ctypes.Structure):
                _fields_=[('flags',wintypes.DWORD),('root',wintypes.HANDLE),
                    ('length',wintypes.DWORD),('name',wintypes.WCHAR*(len(encoded)//2+1))]
            rename=Rename();rename.flags=0;rename.root=None
            rename.length=len(encoded)
            ctypes.memmove(ctypes.addressof(rename)+Rename.name.offset,encoded,len(encoded))
            parent.revalidate()
            if not kernel.SetFileInformationByHandle(handle,3,ctypes.byref(rename),ctypes.sizeof(rename)):
                raise DirectoryRetentionRefused('Original application native rename refused: '+str(ctypes.WinError(ctypes.get_last_error())))
            _need(kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) and
                [info.volume,info.index_high,info.index_low]==list(expected_identity),
                'Retained original directory native identity changed')
            check=kernel.CreateFileW(str(retained),0x80,5,None,3,0x02000000|0x00200000,None)
            if check==ctypes.c_void_p(-1).value:raise DirectoryRetentionRefused('Cannot verify retained original destination')
            try:
                destination=FileInfo()
                _need(kernel.GetFileInformationByHandle(check,ctypes.byref(destination)) and
                    [destination.volume,destination.index_high,destination.index_low]==list(expected_identity) and
                    not destination.attributes&0x400,'Retained original destination differs')
            finally:kernel.CloseHandle(check)
            # Atomic CREATE_NEW semantics. A raced old-name arrival is retained,
            # never overwritten; the caller's transaction stays partial/held.
            fresh=_atomic_fresh_directory(parent,source.name)
            try:
                created=FileInfo()
                _need(kernel.GetFileInformationByHandle(fresh,ctypes.byref(created)) and
                    created.attributes&0x10 and not created.attributes&0x400 and
                    not any(os.scandir(source)),'Fresh application location is not an ordinary empty directory')
                return {'source':str(source),'retained':str(retained),'retained_identity':list(expected_identity),
                    'new_source_identity':[created.volume,created.index_high,created.index_low],'original_preserved':True}
            finally:kernel.CloseHandle(fresh)
        finally:kernel.CloseHandle(handle)
