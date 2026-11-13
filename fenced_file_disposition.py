"""Finite native capability for helpers with an already durable write fence.

This does not bypass the stream guard: it verifies the saved intent, exact
held bytes and the still-applied, DELETE-relaxed fence immediately at disposal.
The helper retains responsibility for its existing native-close certificate.
"""
from contextlib import ExitStack
from pathlib import Path
import ctypes


class FencedFileDisposition:
    def __init__(self,held,*,intent_path,intent_sha256,facts,sha256,applied_security):
        self.held=held;self.handle=held.handle;self.path=Path(held.path).absolute()
        self.intent_path=Path(intent_path).absolute();self.intent_sha256=intent_sha256
        self.facts=facts;self.sha256=sha256;self.applied=applied_security
        self.stack=ExitStack();self.live=False;self.kernel_success=False
    def __enter__(self):
        from storage_relocation_operator import pinned_receipt,need
        from native_io import DirectoryBoundary
        try:
            self.stack.enter_context(DirectoryBoundary(self.intent_path.anchor,self.intent_path.parent))
            record=self.stack.enter_context(pinned_receipt(self.intent_path,self.intent_sha256))
            schema=record.get('schema')
            need(schema in ('books-owned-file-disposal-v1','books-source-file-finalization-v1') and
                 record.get('phase',record.get('state'))=='intent' and record.get('path')==str(self.path) and
                 record.get('facts')==self.facts and record.get('sha256')==self.sha256,
                 'Finite disposition intent does not bind this exact file')
            from runtime_file_disposition import _local_provider
            _local_provider(self.handle)
            from storage_relocation_operator import Security
            security=Security()
            if schema=='books-owned-file-disposal-v1':
                import base64
                original=record.get('original_security');security.validate_capture(original)
                expected=base64.b64decode(record.get('expected_fence_acl',''),validate=True)
                need(expected==security.planned_write_fence_acl(original,False) and
                     security.captured_acl(self.applied)==expected and self.applied.get('protected') is True and
                     self.applied['sddl'].partition('D:')[0]==original['sddl'].partition('D:')[0],
                     'Finite disposition applied ACL differs from its durable planned transition')
            else:
                need(record.get('applied_security')==self.applied,
                     'Source disposition ACL is not pinned by its durable native intent')
                security.validate_capture(self.applied)
            self.live=True;self.authorize(self.held);return self
        except BaseException:self.stack.close();raise
    def authorize(self,held):
        from native_io import kernel
        from runtime_file_disposition import SecurityHandle,_local_provider
        from storage_relocation_operator import Security,need
        from storage_source_finalization import _delete_fenced
        from source_cleanup import single_stream
        need(self.live and held is self.held and held.handle==self.handle and self.handle,
             'Finite disposition capability does not own this live handle')
        _local_provider(held.handle)
        need(kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)) and
             held.facts()==self.facts and held.sha256()==self.sha256,
             'Finite disposition exact identity/bytes changed')
        with SecurityHandle(self.path) as security_handle:
            need(security_handle.facts['identity']==self.facts['identity'] and
                 _delete_fenced(Security(),security_handle,self.applied),
                 'Finite disposition write/ADS fence is not retained')
        single_stream(self.path)
        return self
    def mark_pending(self):self.kernel_success=True
    def __exit__(self,*args):self.live=False;self.stack.close()
