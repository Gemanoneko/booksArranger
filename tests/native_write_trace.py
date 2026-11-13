"""Actual Windows directory-change observations for private filesystem proofs."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import struct
import threading


class Overlapped(ctypes.Structure):
    _fields_=[('Internal',ctypes.c_size_t),('InternalHigh',ctypes.c_size_t),
              ('Offset',wintypes.DWORD),('OffsetHigh',wintypes.DWORD),('hEvent',wintypes.HANDLE)]


class NativeWriteTrace:
    def __init__(self,root):
        self.root=Path(root);self.events=[];self.failure=None
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        self.api.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        self.api.CreateFileW.restype=wintypes.HANDLE
        self.api.CreateEventW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.BOOL,wintypes.LPCWSTR]
        self.api.CreateEventW.restype=wintypes.HANDLE
        self.api.ReadDirectoryChangesW.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,wintypes.BOOL,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.POINTER(Overlapped),ctypes.c_void_p]
        self.api.GetOverlappedResult.argtypes=[wintypes.HANDLE,ctypes.POINTER(Overlapped),ctypes.POINTER(wintypes.DWORD),wintypes.BOOL]
        self.api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        self.api.ResetEvent.argtypes=[wintypes.HANDLE]
        self.api.CancelIoEx.argtypes=[wintypes.HANDLE,ctypes.POINTER(Overlapped)]
        self.api.CloseHandle.argtypes=[wintypes.HANDLE]
        self.stop=threading.Event();self.ready=threading.Event()
    def __enter__(self):
        self.handle=self.api.CreateFileW(str(self.root),1,7,None,3,0x02000000|0x40000000,None)
        if self.handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
        self.event=self.api.CreateEventW(None,True,False,None)
        if not self.event:self.api.CloseHandle(self.handle);raise ctypes.WinError(ctypes.get_last_error())
        self.thread=threading.Thread(target=self._read,daemon=True);self.thread.start()
        if not self.ready.wait(5):raise RuntimeError('Native filesystem trace did not arm')
        if self.failure:raise self.failure
        return self
    def _read(self):
        try:
            while not self.stop.is_set():
                buffer=ctypes.create_string_buffer(65536);overlapped=Overlapped();overlapped.hEvent=self.event
                self.api.ResetEvent(self.event)
                if not self.api.ReadDirectoryChangesW(self.handle,buffer,len(buffer),True,0x5b,None,ctypes.byref(overlapped),None):
                    raise ctypes.WinError(ctypes.get_last_error())
                self.ready.set()
                while self.api.WaitForSingleObject(self.event,50)==258:
                    if self.stop.is_set():self.api.CancelIoEx(self.handle,ctypes.byref(overlapped))
                returned=wintypes.DWORD()
                if not self.api.GetOverlappedResult(self.handle,ctypes.byref(overlapped),ctypes.byref(returned),False):
                    if self.stop.is_set() and ctypes.get_last_error()==995:return
                    raise ctypes.WinError(ctypes.get_last_error())
                if not returned.value:raise RuntimeError('Native filesystem trace overflowed')
                offset=0
                while True:
                    following,action,length=struct.unpack_from('<III',buffer.raw,offset)
                    name=buffer.raw[offset+12:offset+12+length].decode('utf-16-le')
                    self.events.append({'action':action,'path':str(self.root/name)})
                    if not following:break
                    offset+=following
        except BaseException as error:self.failure=error;self.ready.set()
    def __exit__(self,*unused):
        self.stop.set();self.thread.join(5)
        if self.thread.is_alive():raise RuntimeError('Native filesystem trace did not close')
        self.api.CloseHandle(self.event);self.api.CloseHandle(self.handle)
        if self.failure:raise self.failure
