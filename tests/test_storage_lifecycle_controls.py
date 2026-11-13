"""Private native control-record visibility, authority and final-journal holds."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import subprocess
import uuid
from unittest.mock import patch

import storage_lifecycle as lifecycle
import storage_lifecycle_controls as controls


@unittest.skipUnless(os.name=='nt','Requires Windows native facts')
class ControlTests(unittest.TestCase):
    def setUp(self):
        base=Path(os.environ.get('BOOKS_LIFECYCLE_TEST_ROOT') or os.environ.get('BOOKS_QA_FIXTURE_ROOT') or
            Path(__file__).resolve().parents[1]/'scratch'/'lifecycle-controls')
        base.mkdir(parents=True,exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=base,prefix='controls-')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        environment=patch.dict(os.environ,APPDATA=str(self.root/'Roaming'),LOCALAPPDATA=str(self.root/'Local'))
        environment.start();self.addCleanup(environment.stop)
        registrations=patch.object(lifecycle,'registered_bootstraps',return_value=[]);registrations.start();self.addCleanup(registrations.stop)
        app=self.root/'Installation'/'Application';app.mkdir(parents=True)
        plan=lifecycle.selection_plan('new',str(app.parent/'Data'),application_dir=str(app),profile_dir=str(app.parent/'Profile'))
        sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        result=lifecycle.commit_selection(plan,sha,process_name='Books No Such Control Fixture.exe')
        self.bootstrap=Path(result['bootstrap']);self.value=json.loads(self.bootstrap.read_text())

    def test_pinned_controls_are_visible_and_physical_duplicates_count_once(self):
        result=controls.review_control_records(self.bootstrap)
        expected={str(self.bootstrap),self.value['ownership_manifest'],self.value['control_provenance']['manifest'],
            str(self.bootstrap.parent/'books-arranger-selection-in-progress.json')}
        self.assertEqual({r['path'] for r in result['files']},expected)
        self.assertEqual(result['bytes'],sum(Path(p).stat().st_size for p in expected))
        self.assertTrue(all(not row['can_remove'] for row in result['files']))
        self.assertEqual(result['holds'],[])

    def test_unconfirmed_empty_control_directory_is_visible_at_zero_bytes(self):
        directory=self.bootstrap.parent/'CleanupReceipts';directory.mkdir()
        result=controls.review_control_records(self.bootstrap)
        row=next(r for r in result['holds'] if r['path']==str(directory))
        self.assertEqual(row['bytes'],0);self.assertFalse(row['can_remove'])

    def test_other_installation_native_references_protect_the_same_records(self):
        other=self.root/'Other'/'books-arranger-installation.json';other.parent.mkdir()
        value=dict(self.value,application_dir=str(other.parent/'Application'));value.pop('control_provenance',None)
        other.write_text(json.dumps(value))
        result=controls.review_control_records(self.bootstrap,other_bootstraps=[str(other)])
        row=next(r for r in result['files'] if r['path']==self.value['ownership_manifest'])
        self.assertEqual(row['state'],'used_by_another_installation');self.assertTrue(row['required_by'])

    def test_changed_pin_is_held_and_no_file_is_removed(self):
        owner=Path(self.value['ownership_manifest']);owner.write_bytes(owner.read_bytes()+b' ')
        with self.assertRaisesRegex(controls.ControlRecordsHeld,'pin changed'):
            controls.review_control_records(self.bootstrap)
        self.assertTrue(owner.exists());self.assertTrue(self.bootstrap.exists())

    def test_control_retirement_requires_all_state_and_a_durable_terminal_provider(self):
        result=controls.review_control_records(self.bootstrap)
        with self.assertRaises(controls.ControlRecordsHeld):controls.plan_control_retirement(result,application_will_be_removed=True)
        plan=controls.plan_control_retirement(result,selected_state_roots=result['state_roots'],application_will_be_removed=True)
        sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with self.assertRaisesRegex(controls.ControlRecordsHeld,'durable terminal journal'):
            controls.execute_control_retirement(plan,sha)
        self.assertTrue(self.bootstrap.exists())

    def test_source_or_git_files_do_not_become_controls_from_a_path_pin(self):
        source=self.root/'program.py';source.write_text('print("source remains")')
        with self.assertRaises(controls.ControlRecordsHeld):controls._file(source,'ownership_manifest')
        repo=self.root/'source';(repo/'.git').mkdir(parents=True)
        example=repo/'example.json';example.write_text(json.dumps(dict(schema='books-installation-ownership-v1')))
        with self.assertRaises(controls.ControlRecordsHeld):controls._file(example,'ownership_manifest')
        self.assertTrue(source.exists());self.assertTrue(example.exists())

    def test_terminal_selection_removes_data_package_controls_and_registry_last(self):
        app=Path(self.value['application_dir']);binary=app/'Books Arranger.exe';binary.write_bytes(b'never executed private package')
        producer=dict(schema='books-trusted-current-package-v1',files={binary.name:dict(size=binary.stat().st_size,
            sha256=hashlib.sha256(binary.read_bytes()).hexdigest())})
        real=lifecycle._json
        def trusted(path,*args):
            if Path(path).name=='current-package.json':return producer,{},'a'*64
            return real(path,*args)
        with patch.object(lifecycle,'_json',side_effect=trusted):
            pin=lifecycle.capture_current_package(str(app),self.value['installation_id'])
        self.value['package_ownership']=pin;self.bootstrap.write_text(json.dumps(self.value))
        namespace=controls.create_control_namespace(str(app),'installation')
        creation=Path(namespace['path'])/'namespace.json'
        saved=lifecycle._write_new(creation,json.dumps(dict(schema='books-control-namespace-creation-v1',
            application_dir=str(app),namespace=namespace),sort_keys=True).encode())
        old=dict(self.value)
        self.value=lifecycle._seal_install_controls(self.value,dict(manifest=str(creation),sha256=saved['sha256']),previous=dict(value=old))
        self.bootstrap.write_text(json.dumps(self.value))
        review=lifecycle.review_uninstall(self.bootstrap,output_dir=self.root)
        selectable=[r['path'] for r in review['targets'] if r['can_remove']]
        self.assertIn(str(self.bootstrap),selectable)
        plan=lifecycle.plan_selected_cleanup(review['ownership_path'],review['ownership_sha256'],selectable,
            bootstrap_paths=[str(self.bootstrap)])
        sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        import terminal_cleanup_journal as terminal
        provider=terminal.RegistryCleanupJournal;checks=[];test=self
        def node_check(identifier,expected):
            script='try{require(process.argv[1]).assertNoPendingCleanup(process.argv[2]);process.exitCode=0}catch(e){process.exitCode=17}'
            result=subprocess.run(['node','-e',script,str(Path(lifecycle.__file__).parent/'desktop/pending-cleanup.js'),identifier],
                capture_output=True,timeout=15,creationflags=0x08000000)
            test.assertEqual(result.returncode,expected,result.stderr)
        class Observed(provider):
            def __enter__(self):
                result=super().__enter__()
                node_check(test.value['installation_id'],17);node_check(str(uuid.uuid4()),0)
                test.assertTrue(controls.cleanup_status(test.value['installation_id'])['pending'])
                with test.assertRaises(controls.ControlRecordsHeld):controls.assert_no_pending_overlap([str(app)],str(uuid.uuid4()))
                controls.assert_no_pending_overlap([str(test.root/'UnrelatedStorage')],str(uuid.uuid4()))
                checks.append('actual-registry-before-disposal');return result
        with patch.object(terminal,'RegistryCleanupJournal',Observed):
            result=lifecycle.execute_selected_cleanup(plan,sha,owner_path=self.root/'terminal-owner.lock',
                process_name='Books Never Executed Cleanup Fixture.exe')
        self.assertTrue(result['ok'],result);self.assertTrue(result['controls_removed']);self.assertTrue(result['package_removed'])
        self.assertFalse(app.exists());self.assertFalse(self.bootstrap.exists())
        self.assertFalse(Path(self.value['control_provenance']['manifest']).exists())
        self.assertFalse(Path(namespace['path']).exists());self.assertEqual(checks,['actual-registry-before-disposal'])
        node_check(self.value['installation_id'],0)
        self.assertFalse(controls.cleanup_status(self.value['installation_id'])['pending'])
        for root in ('data_dir','profile_dir','temp_dir','downloads_dir','logs_dir'):self.assertFalse(Path(self.value[root]).exists())


if __name__=='__main__':unittest.main()
