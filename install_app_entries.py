"""Install only Books Arranger's two ordinary user Start-menu entries; never launch them."""
import contextlib
import hashlib
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
class GUID(ctypes.Structure):
    _fields_=[('data1',wintypes.DWORD),('data2',wintypes.WORD),('data3',wintypes.WORD),('data4',ctypes.c_ubyte*8)]
    @classmethod
    def value(cls,text):return cls.from_buffer_copy(uuid.UUID(text).bytes_le)

class ShellLink:
    """Small native IShellLinkW/IPersistFile wrapper: save/read, never execute."""
    def __init__(self):
        self.ole=ctypes.OleDLL('ole32');self.link=ctypes.c_void_p();self.persist=ctypes.c_void_p()
        self.ole.CoInitializeEx.argtypes=[ctypes.c_void_p,wintypes.DWORD];self.ole.CoInitializeEx.restype=ctypes.c_long
        result=self.ole.CoInitializeEx(None,2)
        if result not in (0,1):raise OSError('Windows shortcut support could not initialize')
        self.initialized=True
        try:
            self.ole.CoCreateInstance.argtypes=[ctypes.POINTER(GUID),ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)]
            self.ole.CoCreateInstance.restype=ctypes.c_long
            self.check(self.ole.CoCreateInstance(ctypes.byref(GUID.value('00021401-0000-0000-c000-000000000046')),None,1,ctypes.byref(GUID.value('000214f9-0000-0000-c000-000000000046')),ctypes.byref(self.link)))
            self.check(self.call(self.link,0,[ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)],ctypes.byref(GUID.value('0000010b-0000-0000-c000-000000000046')),ctypes.byref(self.persist)))
        except BaseException:self.close();raise
    @staticmethod
    def check(value):
        if value<0:raise OSError('Windows could not read or save the app shortcut ('+str(value)+')')
    @staticmethod
    def call(pointer,index,types,*args):
        table=ctypes.cast(pointer,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        method=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,*types)(table[index])
        return method(pointer,*args)
    def close(self):
        for pointer in (self.persist,self.link):
            if pointer:self.call(pointer,2,[]);pointer.value=None
        if self.initialized:self.ole.CoUninitialize();self.initialized=False
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def set(self,target,args,directory,description):
        for index,value in ((20,target),(11,args),(9,directory),(7,description)):
            self.check(self.call(self.link,index,[wintypes.LPCWSTR],str(value)))
        self.check(self.call(self.link,15,[ctypes.c_int],1))
    def save(self,path):self.check(self.call(self.persist,6,[wintypes.LPCWSTR,wintypes.BOOL],str(path),True))
    def load(self,path):self.check(self.call(self.persist,5,[wintypes.LPCWSTR,wintypes.DWORD],str(path),0))
    def fields(self):
        result={}
        for key,index in (('target',3),('args',10),('directory',8)):
            buffer=ctypes.create_unicode_buffer(32768)
            if index==3:code=self.call(self.link,index,[wintypes.LPWSTR,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD],buffer,len(buffer),None,0)
            else:code=self.call(self.link,index,[wintypes.LPWSTR,ctypes.c_int],buffer,len(buffer))
            self.check(code);result[key]=buffer.value
        return result

def user_programs():
    shell=ctypes.OleDLL('shell32');ole=ctypes.OleDLL('ole32');out=ctypes.c_void_p()
    shell.SHGetKnownFolderPath.argtypes=[ctypes.POINTER(GUID),wintypes.DWORD,wintypes.HANDLE,ctypes.POINTER(ctypes.c_void_p)]
    shell.SHGetKnownFolderPath.restype=ctypes.c_long
    ShellLink.check(shell.SHGetKnownFolderPath(ctypes.byref(GUID.value('a77f5d77-2e2b-44c3-a6a2-aba601054a51')),0,None,ctypes.byref(out)))
    try:return Path(ctypes.wstring_at(out))
    finally:
        ole.CoTaskMemFree.argtypes=[ctypes.c_void_p];ole.CoTaskMemFree(out)

def entries(base=BASE, runtime=None):
    runtime=Path(runtime or Path(sys.executable).with_name('pythonw.exe')).resolve()
    from native_io import ordinary
    ordinary(runtime)
    result=[]
    for label,entry,description in (
        ('Books Arranger','launch-web.pyw','Open Books Arranger or show its running app.'),
        ('Restart Books Arranger','restart-web.pyw','Restart Books Arranger when it is idle. Saved automatic work stays paused.'),
    ):
        script=ordinary(Path(base)/entry)
        result.append({'label':label,'target':str(runtime),'args':subprocess.list2cmdline(['-I','-B',str(script)]),'directory':str(Path(base).resolve()),'description':description})
    return result

def install(programs=None, *, base=BASE, runtime=None):
    """Fixed app entries only. Existing unrelated links are never overwritten."""
    from native_io import ordinary, VerifiedFile, DirectoryBoundary, publish_no_replace
    folder=Path(programs or user_programs())/'Books Arranger'
    with contextlib.ExitStack() as topology:
        topology.enter_context(DirectoryBoundary(folder.anchor,folder.parent))
        folder.mkdir(exist_ok=True)
        boundary=topology.enter_context(DirectoryBoundary(folder.anchor,folder))
        planned=entries(base,runtime);results=[]
        # Validate both existing entries before creating either new one.
        for entry in planned:
            path=folder/(entry['label']+'.lnk')
            if os.path.lexists(path):
                with VerifiedFile(path),ShellLink() as link:
                    link.load(path);fields=link.fields()
                if Path(fields['target']).resolve()!=Path(entry['target']) or fields['args']!=entry['args'] or Path(fields['directory']).resolve()!=Path(entry['directory']):
                    raise FileExistsError('An unrelated Start-menu entry already uses '+entry['label']+'. No entries were changed.')
                entry['existing']=True
        for entry in planned:
            path=folder/(entry['label']+'.lnk')
            if entry.get('existing'):results.append({'path':str(path),'action':'reused'});continue
            fd,temp=tempfile.mkstemp(prefix='.books-arranger-',suffix='.lnk',dir=folder)
            temporary=Path(temp)
            # Keep the exclusively-created CRT handle open (no delete sharing) while COM writes.
            # Failed/uncertain evidence is retained, never removed merely by its temporary name.
            with os.fdopen(fd,'r+b') as produced:
                with ShellLink() as link:
                    link.set(entry['target'],entry['args'],entry['directory'],entry['description']);link.save(temporary)
                    link.load(temporary)
                    if link.fields()!= {key:entry[key] for key in ('target','args','directory')}:
                        raise OSError('The app shortcut did not match its fixed target')
                produced.seek(0);raw=produced.read(65537)
                if not raw or len(raw)>65536:raise OSError('The app shortcut was not a bounded produced file')
                produced.flush();os.fsync(produced.fileno())
            publish_no_replace(temporary,path,boundary,hashlib.sha256(raw).hexdigest(),len(raw))
            results.append({'path':str(path),'action':'created'})
        return results

if __name__=='__main__':
    import json
    print(json.dumps({'entries':install()},ensure_ascii=False))
