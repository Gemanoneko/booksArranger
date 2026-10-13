"""CREATE_NEW desktop settings, under retained ordinary profile ancestry."""
import ctypes,json,sys
from ctypes import wintypes
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_io import DirectoryBoundary,VerifiedFile,FileInfo,kernel

def save(path,folder):
 path=Path(path).absolute();folder=Path(folder).absolute()
 if path.name!='desktop-settings.json':raise ValueError('Unknown settings target')
 raw=json.dumps({'dataDir':str(folder),'catalogMode':'existing'}).encode('utf-8')
 with DirectoryBoundary(path.anchor,path.parent,create=True):
  held=VerifiedFile(path,delete=True,writable=True)
  held.handle=kernel.CreateFileW(str(path),0xC0010081,1,None,1,0x00200000,None)
  if held.handle==ctypes.c_void_p(-1).value:held.handle=None;raise RuntimeError('Existing or unknown desktop settings were preserved')
  complete=False
  try:
   held.info=FileInfo()
   if not kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)) or held.info.attributes&(0x400|0x10) or held.info.links!=1:raise RuntimeError('Settings producer file differs')
   kernel.WriteFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p];kernel.WriteFile.restype=wintypes.BOOL
   buffer=ctypes.create_string_buffer(raw);count=wintypes.DWORD()
   if not kernel.WriteFile(held.handle,buffer,len(raw),ctypes.byref(count),None) or count.value!=len(raw):raise RuntimeError('Settings write failed')
   held.flush();complete=True
  finally:
   if not complete:held.dispose()
   held.__exit__(None,None,None)
 return {'ok':True}
def main():
 try:result=save(*sys.argv[1:])
 except Exception as error:print(json.dumps({'ok':False,'error':str(error)}));return 1
 print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())
