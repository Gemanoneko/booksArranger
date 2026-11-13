"""Scoped native runtime disposition controls; no live catalog/library."""
import base64
import contextlib
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import threading
import unittest
import uuid
from unittest.mock import patch

from native_io import VerifiedFile,kernel
from storage_relocation_operator import Security,digest,security_equivalent
from storage_relocation import RelocationRefused
import runtime_file_disposition as runtime


@unittest.skipUnless(os.name=='nt','Native Windows runtime disposition')
class RuntimeDispositionTests(unittest.TestCase):
    def setUp(self):
        base=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',str(Path(__file__).resolve().parents[1]/'scratch')))
        self.area=base/('runtime-disposition-'+uuid.uuid4().hex);self.area.mkdir(parents=True)
        self.owner_path=self.area/'catalog.lock';self.owner_path.write_bytes(b'actual unique owner')
        self.owner=VerifiedFile(self.owner_path,writable=True).__enter__()
        self.context=runtime.DispositionContext(self.area/'ledger',scopes=[self.area],owner_handle=self.owner.handle,
            owner_identity=self.owner.facts()['identity'],owner_path=self.owner_path,owner_kind='catalog',catalog_identity=['private',1])
        self.context.__enter__();self.file=self.area/'owned.bin';self.file.write_bytes(b'owned bytes')
    def tearDown(self):
        for operation in list(self.context.operations):
            if operation.kernel_success and operation.held.handle==operation.handle:operation.close()
            else:operation.abort('private test teardown')
        self.context.close();self.owner.__exit__(None,None,None)
    def prepared(self,held):return runtime.prepare_disposition(held,self.context)
    def kernel_dispose(self,held,guard):
        guard.authorize(held)
        kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        kernel.SetFileInformationByHandle.restype=wintypes.BOOL
        value=wintypes.BOOL(True)
        self.assertTrue(kernel.SetFileInformationByHandle(held.handle,4,ctypes.byref(value),ctypes.sizeof(value)))
        guard.mark_pending()

    def test_mark_pending_keeps_original_handle_until_actual_close(self):
        with VerifiedFile(self.file,delete=True) as held:
            original=held.handle;guard=self.prepared(held);self.kernel_dispose(held,guard)
            self.assertEqual(held.handle,original);self.assertTrue(self.file.exists())
            guard.close();self.assertIsNone(held.handle);self.assertFalse(self.file.exists())
        report=runtime.recover(self.context)
        self.assertEqual(report['removed'],[str(self.file)]);self.assertFalse(report['held'])

    def test_oversized_intent_refuses_before_acl_or_native_disposition(self):
        with runtime.SecurityHandle(self.file) as sec:original=Security().capture(sec)
        with VerifiedFile(self.file,delete=True) as held:
            with patch.object(runtime.Security,'planned_write_fence_acl',return_value=b'x'*(runtime.MAX_RECORD)), \
                 patch.object(runtime.Security,'apply_planned_write_fence',side_effect=AssertionError('ACL must remain original')):
                with self.assertRaisesRegex(Exception,'recovery bound'):self.prepared(held)
        with runtime.SecurityHandle(self.file) as sec:self.assertEqual(Security().capture(sec),original)
        self.assertEqual(self.file.read_bytes(),b'owned bytes')
        self.assertFalse(list(self.context.control_root.glob('*.intent.json')))

    def test_closed_native_history_does_not_reopen_retired_parent_or_reused_name(self):
        parent=self.area/'stage';parent.mkdir();file=parent/'temporary.bin';file.write_bytes(b'old exact temporary')
        with VerifiedFile(file,delete=True) as held:
            guard=self.prepared(held);self.kernel_dispose(held,guard);guard.close()
        parent.rmdir()
        self.assertFalse(runtime.recover(self.context)['held'])
        parent.mkdir();file.write_bytes(b'unrelated replacement')
        self.assertFalse(runtime.recover(self.context)['held'])
        self.assertEqual(file.read_bytes(),b'unrelated replacement')

    def test_after_last_caller_check_arriving_native_ads_denied(self):
        program="import ctypes,sys;from ctypes import wintypes;k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];k.CreateFileW.restype=wintypes.HANDLE;k.WriteFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p];k.CloseHandle.argtypes=[wintypes.HANDLE];h=k.CreateFileW(sys.argv[1],0x40000000,7,None,2,0,None);opened=h!=ctypes.c_void_p(-1).value;n=wintypes.DWORD();ok=opened and bool(k.WriteFile(h,b'arrival',7,ctypes.byref(n),None)) and n.value==7;k.CloseHandle(h);sys.exit(0 if ok else 8)"
        ordinary=self.area/'ordinary';ordinary.write_bytes(b'positive')
        self.assertEqual(subprocess.run([sys.executable,'-I','-B','-c',program,str(ordinary)+':arrival'],timeout=30).returncode,0)
        from source_cleanup import single_stream
        with VerifiedFile(self.file,delete=True) as held:
            single_stream(self.file);guard=self.prepared(held);guard.authorize(held)
            self.assertEqual(subprocess.run([sys.executable,'-I','-B','-c',program,str(self.file)+':arrival'],timeout=30).returncode,8)
            self.kernel_dispose(held,guard);guard.close()

    def test_writable_original_handle_security_handle_does_not_conflict(self):
        with VerifiedFile(self.file,delete=True,writable=True) as held:
            guard=self.prepared(held);guard.authorize(held);guard.abort('caller retained bytes')
        self.assertEqual(self.file.read_bytes(),b'owned bytes');self.file.write_bytes(b'writable again')

    def test_pending_journal_failure_never_restores_delete_pending_acl(self):
        with VerifiedFile(self.file,delete=True) as held:
            guard=self.prepared(held);original=guard._record
            def fail(phase,**values):
                if phase=='pending':raise OSError('pending fsync failure')
                return original(phase,**values)
            with patch.object(guard,'_record',fail):
                with self.assertRaisesRegex(OSError,'fsync'):self.kernel_dispose(held,guard)
            self.assertTrue(guard.kernel_success)
            with patch.object(guard.security,'restore',side_effect=AssertionError('must not restore after native success')):
                guard.abort('pending journal failed');guard.close()
        self.assertFalse(self.file.exists())

    def test_intent_then_fence_failure_restores_exact_original(self):
        with VerifiedFile(self.file,delete=True) as held:
            with runtime.SecurityHandle(self.file) as sec:original=Security().capture(sec)
            real=runtime.Security.apply_planned_write_fence
            def fail_after(security,item,source,expected):real(security,item,source,expected);raise RuntimeError('after fence interruption')
            with patch.object(runtime.Security,'apply_planned_write_fence',fail_after):
                with self.assertRaisesRegex(RuntimeError,'after fence'):self.prepared(held)
            with runtime.SecurityHandle(self.file) as sec:self.assertTrue(security_equivalent(Security().capture(sec),original))
        report=runtime.recover(self.context);self.assertEqual(report['restored'],[str(self.file)])

    def test_foreign_dacl_changed_after_intent_is_preserved(self):
        with VerifiedFile(self.file,delete=True) as held:
            real=runtime.Security.apply_planned_write_fence;changed={}
            def foreign(security,item,original,expected):
                # Apply a different, structurally valid protected ACL (directory
                # deny mask includes DELETE_CHILD), which is not this intent.
                other=security.planned_write_fence_acl(original,True)
                buffer=ctypes.create_string_buffer(other)
                self.assertEqual(security.api.SetSecurityInfo(item.handle,1,4|0x80000000,None,None,buffer,None),0)
                changed.update(security.capture(item));return real(security,item,original,expected)
            with patch.object(runtime.Security,'apply_planned_write_fence',foreign):
                with self.assertRaises(RelocationRefused):self.prepared(held)
            with runtime.SecurityHandle(self.file) as sec:self.assertEqual(Security().capture(sec)['sddl'],changed['sddl'])
        report=runtime.recover(self.context);self.assertTrue(report['held'])
        # Normalize only this exact private fixture, using its durable original.
        intent,_=runtime._load(next(self.context.control_root.glob('*.intent.json')))
        with runtime.SecurityHandle(self.file) as sec:Security().restore(sec,intent['original_security'])

    def test_closed_proof_failure_absence_is_held_not_recovered_as_removed(self):
        with VerifiedFile(self.file,delete=True) as held:
            guard=self.prepared(held);self.kernel_dispose(held,guard);original=guard._record
            def fail(phase,**values):
                if phase=='closed':raise OSError('closed fsync failure')
                return original(phase,**values)
            with patch.object(guard,'_record',fail):
                with self.assertRaisesRegex(OSError,'closed fsync'):guard.close()
        report=runtime.recover(self.context);self.assertFalse(report['removed']);self.assertTrue(report['held'])

    def test_handle_swap_cannot_certify_native_close(self):
        with VerifiedFile(self.file,delete=True) as held:
            guard=self.prepared(held);self.kernel_dispose(held,guard);original=held.handle
            held.handle=self.owner.handle
            with self.assertRaises(RelocationRefused):guard.close()
            held.handle=original;guard.close()

    def test_matching_ticket_value_with_foreign_native_identity_cannot_close(self):
        with VerifiedFile(self.file,delete=True) as held:
            guard=self.prepared(held);self.kernel_dispose(held,guard);original=held.handle
            held.handle=self.owner.handle;guard.handle=self.owner.handle
            with self.assertRaises(RelocationRefused):guard.close()
            self.context.revalidate()
            held.handle=original;guard.handle=original;guard.close()

    def test_authorize_refreshes_cached_metadata_from_same_native_handle(self):
        with VerifiedFile(self.file,delete=True,writable=True) as held:
            guard=self.prepared(held);original=guard.intent['original_security']
            held.restore_metadata(guard.intent['facts']['modified']+1000000000,guard.intent['facts']['attributes'])
            with self.assertRaisesRegex(RelocationRefused,'facts/bytes'):guard.authorize(held)
            guard.abort('caller metadata changed')
            # Explicitly restore only the exact private fixture's SD after the
            # guard correctly refused stale-facts rollback.
            with runtime.SecurityHandle(self.file) as sec:Security().restore(sec,original)

    def test_same_bytes_replacement_and_foreign_security_not_adopted_on_recovery(self):
        with VerifiedFile(self.file,delete=True) as held:
            guard=self.prepared(held);guard.abort('no disposition')
        (self.area/'original-bytes-kept').write_bytes(self.file.read_bytes())
        self.file.unlink();self.file.write_bytes(b'owned bytes')
        report=runtime.recover(self.context);self.assertTrue(report['held']);self.assertFalse(report['restored'])
        self.assertEqual(self.file.read_bytes(),b'owned bytes')

    def test_sqlite_write_transaction_and_cross_thread_owner_no_deadlock(self):
        database=self.area/'fixture.sqlite3'
        with contextlib.closing(sqlite3.connect(database)) as db:
            db.execute('CREATE TABLE evidence(value TEXT)');db.commit();db.execute('BEGIN IMMEDIATE')
            result=[]
            def worker():
                try:
                    with VerifiedFile(self.file,delete=True) as held:
                        guard=self.prepared(held);self.kernel_dispose(held,guard);guard.close()
                    result.append('done')
                except BaseException as error:result.append(error)
            thread=threading.Thread(target=worker);thread.start();thread.join(10)
            self.assertFalse(thread.is_alive());self.assertEqual(result,['done']);db.rollback()

    def test_provider_refusal_before_acl_or_intent_and_remote_root_no_fallback(self):
        with VerifiedFile(self.file,delete=True) as held:
            with runtime.SecurityHandle(self.file) as sec:before=Security().capture(sec)
            with patch.object(runtime,'_local_provider',side_effect=RelocationRefused('unsupported provider')):
                with self.assertRaisesRegex(RelocationRefused,'provider'):self.prepared(held)
            with runtime.SecurityHandle(self.file) as sec:self.assertEqual(Security().capture(sec)['sddl'],before['sddl'])
        self.assertFalse(list(self.context.control_root.glob('*.intent.json')))
        kernel.GetDriveTypeW.argtypes=[wintypes.LPCWSTR];kernel.GetDriveTypeW.restype=wintypes.UINT
        if kernel.GetDriveTypeW('Z:\\')==4:
            remote=runtime.DispositionContext('Z:/Books Arranger/never-created-runtime-ledger-'+uuid.uuid4().hex,
                scopes=[self.area],owner_handle=self.owner.handle,owner_identity=self.owner.facts()['identity'],
                owner_path=self.owner_path,owner_kind='support')
            with self.assertRaises(RelocationRefused):remote.__enter__()

    def test_intent_fsync_failure_cannot_leave_unbound_security_transition(self):
        original=runtime.create_new
        def failure(path,raw):
            value=runtime.bounded_json(raw)
            if value.get('phase')=='intent':original(path,raw);raise OSError('intent fsync interruption')
            return original(path,raw)
        with VerifiedFile(self.file,delete=True) as held:
            with runtime.SecurityHandle(self.file) as sec:before=Security().capture(sec)
            with patch.object(runtime,'create_new',failure):
                with self.assertRaisesRegex(OSError,'intent fsync'):self.prepared(held)
            with runtime.SecurityHandle(self.file) as sec:self.assertTrue(security_equivalent(Security().capture(sec),before))
        report=runtime.recover(self.context);self.assertEqual(report['restored'],[str(self.file)]);self.assertFalse(report['held'])

    def test_unknown_malformed_orphan_records_are_held(self):
        (self.context.control_root/'foreign.txt').write_bytes(b'keep')
        (self.context.control_root/(uuid.uuid4().hex+'.pending.json')).write_bytes(b'{}')
        report=runtime.recover(self.context);self.assertEqual(len(report['held']),2)

    def test_recovery_after_crash_with_fence_but_no_disposition_restores_original(self):
        with VerifiedFile(self.file,delete=True) as held:
            guard=self.prepared(held);original=guard.intent['original_security']
            # Emulate vanished in-memory operation without calling abort: only
            # this private process's handles close, durable intent/fence remain.
            guard.security_handle.close();guard.security_handle=None
            self.context.operations.discard(guard)
        with runtime.SecurityHandle(self.file) as sec:self.assertTrue(Security().has_write_fence(sec))
        report=runtime.recover(self.context);self.assertEqual(report['restored'],[str(self.file)]);self.assertFalse(report['held'])
        with runtime.SecurityHandle(self.file) as sec:self.assertTrue(security_equivalent(Security().capture(sec),original))

    def test_failed_actual_original_close_does_not_publish_closed_success(self):
        with VerifiedFile(self.file,delete=True) as held:
            guard=self.prepared(held);self.kernel_dispose(held,guard);original_handle=held.handle
            close=kernel.CloseHandle
            def refuse(handle):
                value=getattr(handle,'value',handle)
                return False if value==original_handle else close(handle)
            with patch.object(kernel,'CloseHandle',refuse):
                with self.assertRaisesRegex(RelocationRefused,'CloseHandle failed'):guard.close()
            self.assertEqual(held.handle,original_handle)
            self.assertFalse(list(self.context.control_root.glob('*.closed.json')))
            self.assertTrue(Security().has_write_fence(guard.security_handle));guard.close()

    def test_foreign_owner_readonly_handle_cannot_enroll_context(self):
        with VerifiedFile(self.file) as foreign:
            context=runtime.DispositionContext(self.area/'foreign-ledger',scopes=[self.area],owner_handle=foreign.handle,
                owner_identity=foreign.facts()['identity'],owner_path=self.file,owner_kind='support')
            with self.assertRaisesRegex(RelocationRefused,'authority'):context.__enter__()
        self.assertFalse((self.area/'foreign-ledger').exists())

    def test_marker_bridge_is_explicit_immutable_and_only_closed_history_is_accepted(self):
        with VerifiedFile(self.file,delete=True) as held:
            guard=self.prepared(held);self.kernel_dispose(held,guard);guard.close()
        # Leave a separate unresolved old intent; relocation must hold it.
        unresolved=self.area/'unresolved.bin';unresolved.write_bytes(b'keep')
        with VerifiedFile(unresolved,delete=True) as held:
            guard=self.prepared(held);guard.abort('unresolved historical intention')
        old_sha=self.context.marker_sha256;old_bytes=self.context.marker_path.read_bytes()
        self.context.close();old=self.area/'old-ledger';(self.area/'ledger').rename(old)
        shutil.copytree(old,self.area/'ledger')
        def make(callback=None):
            return runtime.DispositionContext(self.area/'ledger',scopes=[self.area],owner_handle=self.owner.handle,
                owner_identity=self.owner.facts()['identity'],owner_path=self.owner_path,owner_kind='catalog',
                catalog_identity=['private',1],marker_validator=callback)
        with self.assertRaises(RelocationRefused):make().__enter__()
        with self.assertRaises(RelocationRefused):make(lambda previous,current:False).__enter__()
        calls=[]
        def approved(previous,current):
            calls.append((previous,current));return previous['root_identity']!=current['root_identity']
        self.context=make(approved).__enter__()
        self.assertEqual(len(calls),1);self.assertEqual(self.context.marker_sha256,old_sha)
        self.assertEqual(self.context.marker_path.read_bytes(),old_bytes)
        # The old closed path now holds unrelated data; historical validation
        # must neither inspect nor delete it and must not claim new-ID removal.
        self.file.write_bytes(b'unrelated replacement')
        report=runtime.recover(self.context)
        self.assertEqual(report['historical'],[str(self.file)]);self.assertFalse(report['removed'])
        self.assertTrue(report['held']);self.assertEqual(self.file.read_bytes(),b'unrelated replacement')
        # Fresh operations bind actual current ownership, even though their
        # immutable root marker SHA still refers to the approved old bytes.
        fresh=self.area/'fresh.bin';fresh.write_bytes(b'fresh')
        with VerifiedFile(fresh,delete=True) as held:
            guard=self.prepared(held);self.kernel_dispose(held,guard);guard.close()
        report=runtime.recover(self.context);self.assertEqual(report['removed'],[str(fresh)])


if __name__=='__main__':unittest.main()
