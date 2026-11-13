"""Genuine private lifecycle plans + native files + private UUID HKCU keys."""
import base64
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
import winreg
from unittest.mock import patch

import storage_lifecycle as life
from native_io import VerifiedFile
from storage_relocation_operator import packed,digest,NativeItem,Security
from storage_relocation import RelocationRefused
import terminal_cleanup_journal as terminal


@unittest.skipUnless(os.name=='nt','Native Windows registry terminal cleanup')
class TerminalJournalTests(unittest.TestCase):
    def setUp(self):
        root=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',str(Path(__file__).resolve().parents[1]/'scratch')))
        self.area=root/('terminal-registry-'+uuid.uuid4().hex);self.area.mkdir(parents=True)
        self.registrations=patch.object(life,'registered_bootstraps',return_value=[]);self.registrations.start()
        self.configurations=patch.object(life,'known_configurations',return_value=[]);self.configurations.start()
        plan=life.selection_plan('new',self.area/'Data',application_dir=self.area/'Application',profile_dir=self.area/'Profile')
        committed=life.commit_selection(plan,digest(packed(plan)),process_name='Books Terminal No Such Fixture.exe')
        self.bootstrap=Path(committed['bootstrap']);self.boot=json.loads(self.bootstrap.read_bytes())
        self.owner_document=Path(self.boot['ownership_manifest']);self.profile=self.area/'Profile'
        (self.profile/'Preferences').write_bytes(b'{"private":"owned"}')
        refreshed=life.refresh_ownership(self.owner_document,digest(self.owner_document.read_bytes()),
            output_path=self.area/'review-ownership.json',bootstrap_path=str(self.bootstrap))
        self.ordinary=life.plan_cleanup(refreshed['ownership_path'],refreshed['ownership_sha256'],
            selected_roots=[str(self.profile)],bootstrap_paths=[str(self.bootstrap)])
        self.selection=dict(schema='books-terminal-cleanup-selection-v1',installation_id=self.boot['installation_id'],
                            ordinary=self.ordinary,controls=None,directories=[])
        self.lease_path=self.area/'terminal-owner.lock';self.lease_path.write_bytes(b'private owner')
        self.lease=VerifiedFile(self.lease_path,writable=True).__enter__();self.journals=[];self.registry_aliases=[]
        self.real_process_check=life.process_check
        self.process=patch.object(life,'process_check',return_value={'state':'available','busy':[]});self.process.start()
    def journal(self,selection=None,process_name='Books Arranger.exe'):
        selection=selection or self.selection
        journal=terminal.RegistryCleanupJournal(self.bootstrap,digest(self.bootstrap.read_bytes()),
            self.owner_document,digest(self.owner_document.read_bytes()),selection,digest(packed(selection)),
            owner_handle=self.lease.handle,owner_identity=self.lease.facts()['identity'],owner_path=self.lease_path,process_name=process_name)
        journal.__enter__();self.journals.append(journal);return journal
    def tearDown(self):
        for journal in self.journals:
            journal.close()
            # Only these created private UUID registry trees are exported and
            # cleared. No real AppID/uninstaller registration is accessed.
            path=journal.registry_path
            self.assertTrue(path.startswith(terminal.BASE+'\\'+self.boot['installation_id']+'\\'))
            captured={}
            def remove(relative,depth=0):
                self.assertLess(depth,4)
                try:key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,relative,0,terminal.ACCESS)
                except FileNotFoundError:return
                with key:
                    count,values,_=winreg.QueryInfoKey(key);self.assertLess(count,128)
                    captured[relative]=[winreg.EnumValue(key,i) for i in range(values)]
                    children=[winreg.EnumKey(key,i) for i in range(count)]
                for child in children:remove(relative+'\\'+child,depth+1)
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER,relative)
            remove(path)
            for alias in self.registry_aliases:
                self.assertTrue(alias.startswith(terminal.BASE+'\\'+self.boot['installation_id']+'\\'))
                remove(alias)
            encoded={key:[[name,base64.b64encode(value).decode() if isinstance(value,bytes) else value,kind]
                           for name,value,kind in values] for key,values in captured.items()}
            (self.area/('registry-evidence-'+journal.transaction_id+'.json')).write_bytes(packed(encoded))
            parent=terminal.BASE+'\\'+self.boot['installation_id']
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,parent,0,terminal.ACCESS) as key:
                    empty=winreg.QueryInfoKey(key)[:2]==(0,0)
                if empty:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,parent)
            except FileNotFoundError:pass
        self.lease.__exit__(None,None,None)
        if self.process:self.process.stop()
        self.configurations.stop();self.registrations.stop()
    def dispose_all(self,journal):
        for target in self.ordinary['targets']:
            for entry in target['files']:self.assertTrue(journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])['removed'])
            for entry in target['directories']:self.assertTrue(journal.dispose_directory(entry['path'],entry['identity'])['removed'])

    def test_exact_native_file_directory_and_terminal_key_removed_last(self):
        journal=self.journal()
        with self.assertRaises(RelocationRefused):journal.finish()
        self.dispose_all(journal)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,journal.registry_path,0,terminal.ACCESS) as key:
            self.assertIsNotNone(winreg.QueryValueEx(key,'Authority'))
        result=journal.finish();self.assertTrue(result['complete']);self.assertFalse(self.profile.exists())
        with self.assertRaises(FileNotFoundError):winreg.OpenKey(winreg.HKEY_CURRENT_USER,journal.registry_path,0,terminal.ACCESS)

    def test_foreign_path_and_wrong_selected_hash_refuse(self):
        journal=self.journal();file=self.ordinary['targets'][0]['files'][0]
        with self.assertRaises(RelocationRefused):journal.dispose_file(file['path'],file['facts'],'0'*64)
        foreign=self.area/'foreign';foreign.write_bytes(b'keep')
        with NativeItem(foreign) as held:facts=held.facts;sha=held.sha256()
        with self.assertRaises(RelocationRefused):journal.dispose_file(foreign,facts,sha)
        self.assertEqual(foreign.read_bytes(),b'keep')

    def test_actual_ads_write_and_rename_competitor_denied_before_native_disposition(self):
        journal=self.journal();entry=self.ordinary['targets'][0]['files'][0]
        ordinary=self.area/'ordinary';ordinary.write_bytes(b'positive');Path(str(ordinary)+':arrival').write_bytes(b'positive')
        from native_io import kernel
        from ctypes import wintypes
        original=kernel.SetFileInformationByHandle;calls=[]
        original.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];original.restype=wintypes.BOOL
        def competing(handle,kind,value,size):
            if kind==4:
                program="import pathlib,sys;p=pathlib.Path(sys.argv[1]);n=0\nfor op in (lambda:pathlib.Path(str(p)+':arrival').write_bytes(b'ADS'),lambda:p.write_bytes(b'changed'),lambda:p.rename(p.with_name('raced'))):\n try:op()\n except PermissionError:n+=1\nsys.exit(0 if n==3 else 9)"
                result=subprocess.run([sys.executable,'-I','-B','-c',program,entry['path']],capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'));calls.append(True)
            return original(handle,kind,value,size)
        with patch.object(kernel,'SetFileInformationByHandle',competing):
            self.assertTrue(journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])['removed'])
        self.assertTrue(calls)

    def test_kernel_success_registry_failure_never_restores_writable_twin(self):
        journal=self.journal();entry=self.ordinary['targets'][0]['files'][0];record=journal._record
        def fail(definition,phase,**values):
            if phase=='pending':raise OSError('private pending RegFlushKey failure')
            return record(definition,phase,**values)
        with patch.object(journal,'_record',fail),patch.object(journal,'_restore',side_effect=AssertionError('must not restore post-kernel')):
            result=journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])
        self.assertFalse(result['removed']);self.assertTrue(result['kernel_success']);self.assertFalse(Path(entry['path']).exists())
        repeat=journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])
        self.assertFalse(repeat['removed']);self.assertTrue(repeat['held'])
        with self.assertRaises(RelocationRefused):journal.finish()

    def test_unknown_child_and_registry_arrivals_prevent_terminal_completion(self):
        journal=self.journal();entry=self.ordinary['targets'][0]['files'][0]
        self.assertTrue(journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])['removed'])
        foreign=self.profile/'unknown';foreign.write_bytes(b'keep')
        directory=self.ordinary['targets'][0]['directories'][0]
        result=journal.dispose_directory(directory['path'],directory['identity']);self.assertTrue(result['held'])
        self.assertEqual(foreign.read_bytes(),b'keep')
        with self.assertRaises(RelocationRefused):journal.finish()
        winreg.SetValueEx(journal.handle,'ForeignArrival',0,winreg.REG_SZ,'keep')
        self.assertEqual(winreg.QueryValueEx(journal.handle,'ForeignArrival')[0],'keep')

    def test_foreign_acl_after_intent_is_not_overwritten(self):
        journal=self.journal();entry=self.ordinary['targets'][0]['files'][0];actual=Security.apply_planned_write_fence;changed={}
        def drift(security,item,original,expected):
            wrong=security.planned_write_fence_acl(original,True);buffer=ctypes.create_string_buffer(wrong)
            self.assertEqual(security.api.SetSecurityInfo(item.handle,1,4|0x80000000,None,None,buffer,None),0)
            changed.update(security.capture(item));return actual(security,item,original,expected)
        with patch.object(Security,'apply_planned_write_fence',drift):
            result=journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])
        self.assertTrue(result['held']);self.assertFalse(result['security_restored'])
        with NativeItem(entry['path'],writable_security=True) as item:
            self.assertEqual(Security().capture(item)['sddl'],changed['sddl'])
            definition=journal.members[terminal._key(entry['path'])]
            Security().restore(item,journal._get(definition,'intent')['original_security'])

    def test_intent_flush_failure_happens_before_acl_mutation(self):
        journal=self.journal();entry=self.ordinary['targets'][0]['files'][0]
        with NativeItem(entry['path']) as held:original=Security().capture(held)
        put=journal._put
        def fail(key,name,value,*args):
            result=put(key,name,value,*args)
            if name.endswith(':intent'):raise OSError('private intent flush interruption')
            return result
        with patch.object(journal,'_put',fail),patch.object(Security,'apply_planned_write_fence',side_effect=AssertionError('ACL mutation before flush')):
            result=journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])
        self.assertTrue(result['held'])
        with NativeItem(entry['path']) as held:self.assertEqual(Security().capture(held)['sddl'],original['sddl'])

    def test_bootstrap_ownership_and_native_control_namespace_can_be_removed_last(self):
        import storage_lifecycle_controls as controls
        namespace=controls.create_control_namespace(self.area/'Application','cleanup')
        pin=controls.capture_control_producer(self.area/'Application',self.boot['installation_id'],[namespace])
        previous,facts,sha=life._json(self.bootstrap)
        changed=dict(previous,control_provenance=pin)
        life._replace_bootstrap(self.bootstrap,packed(changed),dict(value=previous,facts=facts,sha256=sha))
        self.boot=changed
        # Ordinary roots are independently admitted by the genuine refreshed
        # lifecycle plan; external controls retain their own producer pins.
        all_roots=[row['path'] for row in json.loads(self.owner_document.read_bytes())['roots']]
        refreshed=life.refresh_ownership(self.owner_document,digest(self.owner_document.read_bytes()),
            output_path=self.area/'all-review.json',bootstrap_path=str(self.bootstrap))
        ordinary=life.plan_cleanup(refreshed['ownership_path'],refreshed['ownership_sha256'],selected_roots=all_roots,
                                   bootstrap_paths=[str(self.bootstrap)])
        review=controls.review_control_records(self.bootstrap)
        self.assertFalse(review['holds'])
        control_plan=controls.plan_control_retirement(review,selected_state_roots=all_roots,application_will_be_removed=True)
        selection=dict(schema='books-terminal-cleanup-selection-v1',installation_id=self.boot['installation_id'],ordinary=ordinary,
                       controls=control_plan,directories=review['directories'])
        journal=self.journal(selection)
        for target in ordinary['targets']:
            for entry in target['files']:self.assertTrue(journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])['removed'])
            for entry in target['directories']:self.assertTrue(journal.dispose_directory(entry['path'],entry['identity'])['removed'])
        # Sealed registry authority survives deletion of the exact bootstrap and
        # ownership documents themselves; it creates no replacement disk log.
        for entry in sorted(control_plan['files'],key=lambda row:row['path']==str(self.bootstrap)):
            self.assertTrue(journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])['removed'])
        for entry in review['directories']:
            self.assertTrue(journal.dispose_directory(entry['path'],entry['identity'])['removed'])
        self.assertFalse(self.bootstrap.exists());self.assertFalse(self.owner_document.exists())
        self.assertFalse(Path(namespace['path']).exists());self.assertTrue(journal.finish()['complete'])

    def test_values_inside_private_transaction_are_owned_for_its_lifetime(self):
        journal=self.journal();self.dispose_all(journal)
        winreg.SetValueEx(journal.handle,'ForeignArrival',0,winreg.REG_SZ,'preserve')
        result=journal.finish();self.assertTrue(result['complete'])
        self.assertEqual(result['registry_value_ownership'],'private transaction key lifetime')
        self.assertTrue(result['retained_registry_containers'])

    def test_selected_empty_directory_fence_blocks_real_stream_child_subdir_and_rename(self):
        ordinary=self.area/'ordinary-directory';ordinary.mkdir();Path(str(ordinary)+':positive').write_bytes(b'yes')
        (ordinary/'child').write_bytes(b'yes');(ordinary/'subdir').mkdir();ordinary.rename(self.area/'ordinary-renamed')
        journal=self.journal();entry=self.ordinary['targets'][0]['files'][0]
        self.assertTrue(journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])['removed'])
        from native_io import kernel
        from ctypes import wintypes
        original=kernel.SetFileInformationByHandle
        original.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];original.restype=wintypes.BOOL
        def competing(handle,kind,value,size):
            if kind==4:
                program="import pathlib,sys;p=pathlib.Path(sys.argv[1]);n=0\nfor op in (lambda:pathlib.Path(str(p)+':arrival').write_bytes(b'ADS'),lambda:(p/'child').write_bytes(b'changed'),lambda:(p/'subdir').mkdir(),lambda:p.rename(p.with_name('raced'))):\n try:op()\n except PermissionError:n+=1\nsys.exit(0 if n==4 else 9)"
                result=subprocess.run([sys.executable,'-I','-B','-c',program,str(self.profile)],capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            return original(handle,kind,value,size)
        directory=self.ordinary['targets'][0]['directories'][0]
        with patch.object(kernel,'SetFileInformationByHandle',competing):
            self.assertTrue(journal.dispose_directory(directory['path'],directory['identity'])['removed'])

    def test_closed_registry_failure_does_not_adopt_missing_or_reused_name(self):
        journal=self.journal();entry=self.ordinary['targets'][0]['files'][0];record=journal._record
        def fail(definition,phase,**values):
            if phase=='closed':raise OSError('private closed RegFlushKey interruption')
            return record(definition,phase,**values)
        with patch.object(journal,'_record',fail):result=journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])
        self.assertTrue(result['held']);self.assertFalse(result['removed']);self.assertFalse(Path(entry['path']).exists())
        Path(entry['path']).write_bytes(b'unrelated replacement')
        self.assertTrue(journal.dispose_file(entry['path'],entry['facts'],entry['sha256'])['held'])
        self.assertEqual(Path(entry['path']).read_bytes(),b'unrelated replacement')

    def test_readonly_fake_owner_cannot_enroll_registry_transaction(self):
        file=self.area/'readonly-owner';file.write_bytes(b'not ownership')
        with VerifiedFile(file) as held:
            journal=terminal.RegistryCleanupJournal(self.bootstrap,digest(self.bootstrap.read_bytes()),
                self.owner_document,digest(self.owner_document.read_bytes()),self.selection,digest(packed(self.selection)),
                owner_handle=held.handle,owner_identity=held.facts()['identity'],owner_path=file)
            with self.assertRaisesRegex(RelocationRefused,'authority'):journal.__enter__()

    def test_genuine_retained_package_mutable_membership_keeps_original_producer_authority(self):
        app=self.area/'Application';app.mkdir(exist_ok=True);old=app/'old.exe';old.write_bytes(b'private never executed old binary')
        trusted=dict(schema='books-trusted-legacy-package-v1',version='0.27.0',installer_sha256=None,
                     files={'old.exe':dict(size=old.stat().st_size,sha256=digest(old.read_bytes()))})
        retained=life.retire_legacy_package(str(app),'0.27.0',_trusted=trusted,process_name='Books Never Executed Retention Fixture.exe')
        previous,facts,sha=life._json(self.bootstrap)
        changed=life._attach_retained_package(dict(previous),dict(manifest=retained['receipt'],sha256=retained['receipt_sha256']))
        self.assertNotEqual(changed['ownership_manifest'],changed['ownership_provenance']['manifest'])
        life._replace_bootstrap(self.bootstrap,packed(changed),dict(value=previous,facts=facts,sha256=sha));self.boot=changed
        journal=self.journal()
        self.assertEqual(journal.authority['ownership_path'],previous['ownership_provenance']['manifest'])
        self.assertEqual(journal.authority['current_ownership_path'],changed['ownership_manifest'])
        self.assertNotEqual(journal.authority['current_ownership_sha256'],journal.authority['ownership_sha256'])
        self.dispose_all(journal);self.assertTrue(journal.finish()['complete'])
        self.assertEqual((Path(retained['retained_application'])/'old.exe').read_bytes(),b'private never executed old binary')

    def test_explicit_fixture_process_name_runs_real_discovery_without_product_bypass(self):
        self.process.stop();self.process=None
        name='Books Never Executed Terminal Discovery Fixture.exe'
        with patch.object(life,'process_check',wraps=self.real_process_check) as probe:
            journal=self.journal(process_name=name)
            self.assertEqual(probe.call_args.args[1],name)
            self.assertEqual(journal.authority['process_name'],name)

    # These final-boundary cases were reconstructed after crash corruption;
    # they are new verification, not an assertion of byte-exact test recovery.
    def test_after_final_flush_value_uses_only_private_key_lifetime_authority(self):
        journal=self.journal();self.dispose_all(journal);put=journal._put;arrivals=[]
        def arrive(key,name,value,*args):
            result=put(key,name,value,*args)
            if name=='Terminal':
                winreg.SetValueEx(key,'LatePrivateValue',0,winreg.REG_SZ,'private transaction record')
                winreg.FlushKey(key);arrivals.append(True)
            return result
        with patch.object(journal,'_put',arrive):result=journal.finish()
        self.assertEqual(arrivals,[True]);self.assertTrue(result['complete'])
        self.assertEqual(result['registry_value_ownership'],'private transaction key lifetime')
        with self.assertRaises(FileNotFoundError):
            winreg.OpenKey(winreg.HKEY_CURRENT_USER,journal.registry_path,0,terminal.ACCESS)

    def test_after_final_flush_subkey_is_preserved_by_native_delete_refusal(self):
        journal=self.journal();self.dispose_all(journal);put=journal._put;arrivals=[]
        def arrive(key,name,value,*args):
            result=put(key,name,value,*args)
            if name=='Terminal':
                with winreg.CreateKeyEx(key,'LateUnknownChild',0,terminal.ACCESS) as child:
                    winreg.SetValueEx(child,'Keep',0,winreg.REG_SZ,'unowned child bytes')
                    winreg.FlushKey(child)
                arrivals.append(True)
            return result
        with patch.object(journal,'_put',arrive):
            with self.assertRaisesRegex(RelocationRefused,'subkey|held'):journal.finish()
        self.assertEqual(arrivals,[True]);self.assertFalse(journal.finished)
        with winreg.OpenKey(journal.handle,'LateUnknownChild',0,terminal.ACCESS) as child:
            self.assertEqual(winreg.QueryValueEx(child,'Keep')[0],'unowned child bytes')

    def test_shared_parent_value_and_sibling_survive_final_delete(self):
        journal=self.journal();self.dispose_all(journal);remove=terminal._delete_actual_key;arrivals=[]
        sibling_name='preserved-sibling-'+uuid.uuid4().hex
        sibling_path=terminal.BASE+'\\'+self.boot['installation_id']+'\\'+sibling_name
        self.registry_aliases.append(sibling_path)
        parent=journal.registry_handles[-2];value_name='PrivateTestParent-'+uuid.uuid4().hex
        def arrive(handle):
            winreg.SetValueEx(parent,value_name,0,winreg.REG_SZ,'shared parent is not owned')
            with winreg.CreateKeyEx(parent,sibling_name,0,terminal.ACCESS) as sibling:
                winreg.SetValueEx(sibling,'Keep',0,winreg.REG_SZ,'shared sibling')
                winreg.FlushKey(sibling)
            winreg.FlushKey(parent);arrivals.append(True);return remove(handle)
        try:
            with patch.object(terminal,'_delete_actual_key',arrive):result=journal.finish()
            self.assertEqual(arrivals,[True]);self.assertTrue(result['complete'])
            self.assertEqual(winreg.QueryValueEx(parent,value_name)[0],'shared parent is not owned')
            with winreg.OpenKey(parent,sibling_name,0,terminal.ACCESS) as sibling:
                self.assertEqual(winreg.QueryValueEx(sibling,'Keep')[0],'shared sibling')
            self.assertIn('HKCU\\'+terminal.BASE+'\\'+self.boot['installation_id'],result['retained_registry_containers'])
        finally:
            # This exact unique value was created by this test, not by the
            # cleanup operation. Export the assertion before test teardown.
            winreg.DeleteValue(parent,value_name)

    def test_existing_transaction_uuid_is_not_adopted_or_changed(self):
        journal=self.journal();authority=winreg.QueryValueEx(journal.handle,'Authority')
        with self.assertRaisesRegex(RelocationRefused,'already exists'):
            terminal._create_transaction(journal.registry_path)
        self.assertEqual(winreg.QueryValueEx(journal.handle,'Authority'),authority)
        self.assertFalse(journal.finished)


class RegistryFinishModelTests(unittest.TestCase):
    def test_modeled_replacement_is_preserved_and_reported_without_live_key_rename(self):
        # The live-host registry-rename control is intentionally retired after
        # the crash investigation. This exercises the production finish flow
        # against distinct fake key objects, not a native replacement proof.
        import threading
        class Key:
            def __init__(self,name):self.name=name;self.closed=False
            def Close(self):self.closed=True
        parent=Key('parent');owned=Key('original owned object');replacement=Key('unrelated replacement')
        namespace={};removed=[]
        journal=object.__new__(terminal.RegistryCleanupJournal)
        journal.lock=threading.RLock();journal._validate=lambda:None
        journal.members={};journal.required_gone=[];journal.handle=owned
        journal.registry_handles=[parent,owned];journal.transaction_id='modeled-transaction'
        journal.registry_path='Software\\PrivateModeledFixture\\modeled-transaction'
        journal.native_registry_name='modeled native name';journal.authority_sha256='a'*64
        journal.selection_sha256='b'*64;journal.authority={'installation_id':'modeled-installation'}
        journal.finished=False;journal.live=True
        journal._put=lambda handle,*args: self.assertIs(handle,owned)
        def remove(handle):
            # Arrival after the final name check changes only the namespace;
            # the retained object ticket must still select the old object.
            namespace[journal.transaction_id]=replacement
            self.assertIs(handle,owned);removed.append(handle)
        def info(handle):
            return (len(namespace),0,0) if handle is parent else (0,1,0)
        with patch.object(terminal,'_assert_key',side_effect=lambda handle,name:self.assertIs(handle,owned)), \
             patch.object(terminal,'_delete_actual_key',side_effect=remove), \
             patch.object(terminal.winreg,'QueryInfoKey',side_effect=info), \
             patch.object(terminal.winreg,'EnumKey',side_effect=lambda handle,index:sorted(namespace)[index]), \
             patch.object(terminal.winreg,'FlushKey'), \
             patch.object(terminal.winreg,'DeleteKey',side_effect=AssertionError('Path-based deletion is forbidden')):
            result=journal.finish()
        self.assertEqual(removed,[owned]);self.assertTrue(owned.closed)
        self.assertIs(namespace[journal.transaction_id],replacement);self.assertFalse(replacement.closed)
        self.assertTrue(result['registry_object_removed']);self.assertFalse(result['registry_namespace_absent'])
        self.assertEqual([row['path'] for row in result['retained_registry_records']],['HKCU\\'+journal.registry_path])


if __name__=='__main__':unittest.main()
