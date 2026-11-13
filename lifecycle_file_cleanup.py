"""Exact caller-owned file disposal with finite named-stream write fencing."""
import contextlib
import base64
import ctypes
import os
from pathlib import Path

from lifecycle_directory_cleanup import _read,_publish
from storage_relocation import _inside
from storage_relocation_operator import NativeItem,Security,local_root,need,digest,packed
from storage_source_finalization import _relax_delete,_delete_fenced

SCHEMA='books-owned-file-disposal-v1'


class LifecycleFileDelete(NativeItem):
    def __enter__(self):
        from native_io import kernel,FileInfo,VerifiedFile
        self.handle=kernel.CreateFileW(str(self.path),0x20000|0x10000|0x81,1,None,3,0x00200000,None)
        if self.handle==ctypes.c_void_p(-1).value:
            self.handle=None;need(False,'Cannot reopen exact owned file for disposition')
        try:
            self.info=FileInfo()
            need(kernel.GetFileInformationByHandle(self.handle,ctypes.byref(self.info)) and
                 not self.info.attributes&(0x10|0x400),'Owned file type changed')
            self.view=VerifiedFile(self.path,delete=True);self.view.handle=self.handle;self.view.info=self.info
            self.facts=self.view.facts();need(self.facts['links']==1,'Hardlinked owned file retained');return self
        except BaseException:self.__exit__(None,None,None);raise

    def dispose(self,facts,sha256,applied,security,*,intent_path,intent_sha256):
        from native_io import kernel
        from source_cleanup import single_stream
        need(self.facts==facts and self.sha256()==sha256,'Owned file identity/bytes changed before disposition')
        need(_delete_fenced(security,self,applied),'Owned file lost its finite write fence')
        single_stream(self.path)
        from fenced_file_disposition import FencedFileDisposition
        with FencedFileDisposition(self.view,intent_path=intent_path,intent_sha256=intent_sha256,
                facts=facts,sha256=sha256,applied_security=applied) as capability:
            self.capability=capability
            self.view.dispose(fence=capability)
        need(kernel.CloseHandle(self.handle),'Owned file native close failed');self.handle=None;self.view.handle=None
        with os.scandir(self.path.parent) as entries:
            need(self.path.name.casefold() not in {e.name.casefold() for e in entries},'Owned file disposition is not settled')


def _restore(path,identity,original,expected_acl):
    from lifecycle_fence_security import restore_owned_fence
    return restore_owned_fence(path,identity,original,expected_acl)


def dispose_owned_file(path,expected_facts,expected_sha256,*,receipt_path):
    path=local_root(path);receipt_path=Path(receipt_path).absolute();facts=dict(expected_facts)
    need(isinstance(facts.get('identity'),list) and len(facts['identity'])==3 and facts.get('links')==1,
         'Exact reviewed ordinary file facts required')
    need(isinstance(expected_sha256,str) and len(expected_sha256)==64 and all(c in '0123456789abcdef' for c in expected_sha256),
         'Exact reviewed file SHA256 required')
    need(not _inside(str(receipt_path),str(path)) and receipt_path!=path,'Receipt must be outside selected file')
    need(receipt_path.resolve()!=path.resolve(),'Receipt aliases the selected file')
    from native_io import DirectoryBoundary
    from source_cleanup import single_stream
    with contextlib.ExitStack() as parents:
        parents.enter_context(DirectoryBoundary(path.anchor,path.parent))
        parents.enter_context(DirectoryBoundary(receipt_path.anchor,receipt_path.parent))
        closed_path=Path(str(receipt_path)+'.closed.json')
        if closed_path.exists():
            intent,_=_read(receipt_path);closed,sha=_read(closed_path)
            need(intent.get('schema')==SCHEMA and intent.get('path')==str(path) and intent.get('facts')==facts and
                 intent.get('sha256')==expected_sha256 and closed.get('schema')==SCHEMA and closed.get('phase')=='removed' and
                 closed.get('path')==str(path) and closed.get('facts')==facts and closed.get('sha256')==expected_sha256 and
                 closed.get('intent_sha256')==digest(packed(intent)) and all(closed.get(k) is True for k in ('native_close','observed_absent','single_stream')),
                 'Existing owned-file closed proof differs')
            with os.scandir(path.parent) as entries:absent=path.name.casefold() not in {e.name.casefold() for e in entries}
            return dict(removed=absent,held=not absent,phase='removed' if absent else 'replacement-held',
                        receipt_path=str(closed_path),receipt_sha256=sha)
        if receipt_path.exists():
            intent,sha=_read(receipt_path)
            need(intent.get('schema')==SCHEMA and intent.get('path')==str(path) and intent.get('facts')==facts and
                 intent.get('sha256')==expected_sha256,'Existing owned-file intent differs')
            restored,reason=_restore(path,facts['identity'],intent['original_security'],intent.get('expected_fence_acl',''))
            return dict(removed=False,held=True,phase='interrupted-held',receipt_path=str(receipt_path),receipt_sha256=sha,
                        security_restored=restored,reason='Intent has no closed proof; '+(reason or 'original permissions restored on verified object'))
        security=Security();guard=None;intent=None;intent_sha=None;deleting=None
        try:
            guard=NativeItem(path,writable_security=True).__enter__()
            need(guard.facts==facts and guard.sha256()==expected_sha256,'Reviewed owned-file identity/bytes changed')
            single_stream(path)
            intent=dict(schema=SCHEMA,phase='intent',path=str(path),facts=facts,sha256=expected_sha256,
                        original_security=security.capture(guard))
            intent['expected_fence_acl']=base64.b64encode(security.planned_write_fence_acl(intent['original_security'],False)).decode('ascii')
            intent_sha=_publish(receipt_path,intent)
            applied=security.apply_planned_write_fence(guard,intent['original_security'],base64.b64decode(intent['expected_fence_acl'],validate=True))
            need(security.has_write_fence(guard,applied),'Owned file write fence did not apply')
            _publish(Path(str(receipt_path)+'.fenced.json'),dict(schema=SCHEMA,phase='fenced',path=str(path),facts=facts,
                     sha256=expected_sha256,intent_sha256=intent_sha,applied_security=applied))
            _relax_delete(security,guard,applied);guard.__exit__(None,None,None);guard=None
            with LifecycleFileDelete(path) as deleting:
                deleting.dispose(facts,expected_sha256,applied,security,intent_path=receipt_path,intent_sha256=intent_sha)
            proof=dict(schema=SCHEMA,phase='removed',path=str(path),facts=facts,sha256=expected_sha256,
                       intent_sha256=intent_sha,native_close=True,observed_absent=True,single_stream=True)
            sha=_publish(closed_path,proof)
            return dict(removed=True,held=False,phase='removed',receipt_path=str(closed_path),receipt_sha256=sha)
        except Exception as error:
            if guard:guard.__exit__(None,None,None);guard=None
            if intent is None:raise
            if deleting and getattr(getattr(deleting,'capability',None),'kernel_success',False):
                restored,restore_error=False,'Successful native disposition retains its write fence; closed proof required'
            else:restored,restore_error=_restore(path,facts['identity'],intent['original_security'],intent['expected_fence_acl'])
            held=dict(schema=SCHEMA,phase='held',path=str(path),facts=facts,intent_sha256=intent_sha,
                      reason=str(error),security_restored=restored,restoration_error=restore_error)
            held_path=Path(str(receipt_path)+'.held.json')
            if not held_path.exists():_publish(held_path,held)
            return dict(removed=False,held=True,phase='held',receipt_path=str(receipt_path),receipt_sha256=intent_sha,
                        security_restored=restored,reason=str(error)+(('; permission restoration held: '+restore_error) if restore_error else ''))
        finally:
            if guard:guard.__exit__(None,None,None)
