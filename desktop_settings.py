"""CREATE_NEW desktop settings, under retained ordinary profile ancestry."""
import ctypes,json,sys
from ctypes import wintypes
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_io import DirectoryBoundary,VerifiedFile,FileInfo,kernel

def _create(path,value,name):
 path=Path(path).absolute()
 if path.name!=name:raise ValueError('Unknown settings target')
 raw=json.dumps(value).encode('utf-8')
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
def save(path,folder):
 return _create(path,{'dataDir':str(Path(folder).absolute()),'catalogMode':'existing'},'desktop-settings.json')

def configure_sources(path,roots,sources,output_root=None):
 from source_config import normalize_sources
 config=normalize_sources(roots,sources,output_root)
 return _create(path,config.to_fields(),'audiobook-sources.json')

def main():
 try:
  if sys.argv[1:2]==['--configure-sources']:
   if len(sys.argv)!=4:raise ValueError('Expected new source settings path and bounded plan JSON path')
   plan_path=Path(sys.argv[3])
   with plan_path.open('rb') as source:raw=source.read(16385)
   if len(raw)>16384:raise ValueError('Source configuration plan exceeds bound')
   plan=json.loads(raw);result=configure_sources(sys.argv[2],plan['roots'],plan['audiobook_sources'],plan.get('audiobook_output_root'))
  else:result=save(*sys.argv[1:])
 except Exception as error:print(json.dumps({'ok':False,'error':str(error)}));return 1
 print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())
