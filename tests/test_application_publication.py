"""Private actual native publication; never invokes installed application."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

import application_publication as publication
from storage_relocation_operator import NativeItem,packed,digest
from storage_relocation import RelocationRefused
from directory_retention import retain_directory_no_replace,DirectoryRetentionRefused


@unittest.skipUnless(os.name=='nt','Native Windows publication')
class PublicationTests(unittest.TestCase):
    def setUp(self):
        parent=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',str(Path(__file__).resolve().parents[1]/'scratch')))
        self.area=parent/('application-publication-'+uuid.uuid4().hex);self.area.mkdir(parents=True)
        self.target=self.area/'Application';self.transaction=self.area/'transaction.json'
        self.package=self.area/'current-package.json'
        self.payload={'Books Arranger.exe':b'new private exe','resources/app.bin':b'new payload',
                      'Uninstall Books Arranger.exe':b'fresh uninstaller','uninstallerIcon.ico':b'icon'}
        manifest=dict(schema='books-trusted-current-package-v1',version='0.27.0',build_id='private',
                      generated_uninstaller_sha256=digest(self.payload['Uninstall Books Arranger.exe']),
                      source_head='0'*40,files={k:dict(size=len(v),sha256=digest(v)) for k,v in self.payload.items()})
        self.package.write_bytes(packed(manifest));self.package_sha=digest(self.package.read_bytes())
    def prepare(self,**kwargs):
        return publication.prepare_application_stage(self.target,transaction_path=self.transaction,
            package_manifest=self.package,package_sha256=self.package_sha,**kwargs)
    def extract(self,prepared):
        stage=Path(prepared['stage'])
        for name,data in self.payload.items():
            file=stage/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
    def verify(self,prepared):return publication.verify_publish_application(prepared['plan_path'],prepared['plan_sha256'])

    def test_fresh_stage_full_native_identity_publication_and_restart(self):
        prepared=self.prepare();self.extract(prepared)
        with NativeItem(Path(prepared['stage'])/'Books Arranger.exe') as held:before=held.facts
        result=self.verify(prepared);self.assertTrue(result['published'])
        with NativeItem(self.target/'Books Arranger.exe') as held:self.assertEqual(held.facts,before)
        self.assertTrue(self.verify(prepared)['published'])

    def test_retained_old_package_and_new_target_continuation_preserve_original_ids(self):
        self.target.mkdir();(self.target/'old.exe').write_bytes(b'old original')
        with NativeItem(self.target/'old.exe') as held:before=held.facts
        with NativeItem(self.target,directory=True) as root:identity=root.facts['identity']
        retained=self.area/'RetainedApplication';closed=retain_directory_no_replace(self.target,retained,identity)
        receipt=self.area/'retention.json'
        value=dict(schema='books-legacy-package-retirement-v1',state='original-retained',root=str(self.target),
                   retained_application=str(retained),root_identity=identity,retention=closed)
        receipt.write_bytes(packed(value))
        prepared=self.prepare(target_admission=dict(path=str(receipt),sha256=digest(receipt.read_bytes())))
        self.extract(prepared);self.assertTrue(self.verify(prepared)['published'])
        with NativeItem(retained/'old.exe') as held:self.assertEqual(held.facts,before)

    def test_existing_empty_unknown_target_and_source_library_data_overlap_refused(self):
        self.target.mkdir()
        with self.assertRaises(RelocationRefused):self.prepare()
        self.target.rmdir()
        for protected in (self.area,self.target,self.target/'Data'):
            with self.assertRaises(RelocationRefused):self.prepare(protected_paths=[protected])
        self.assertFalse(self.transaction.exists())

    def test_payload_unknown_or_changed_member_refuses_without_placeholder_loss(self):
        prepared=self.prepare();self.extract(prepared)
        (Path(prepared['stage'])/'resources/app.bin').write_bytes(b'wrong')
        with self.assertRaises(RelocationRefused):self.verify(prepared)
        with NativeItem(self.target,directory=True) as root:self.assertEqual(root.facts['identity'],prepared['placeholder_identity'])

    def test_same_bytes_new_native_stage_or_placeholder_refuses(self):
        prepared=self.prepare();self.extract(prepared)
        old=self.area/'OriginalStage';Path(prepared['stage']).rename(old)
        shutil.copytree(old,prepared['stage'])
        with self.assertRaises(RelocationRefused):self.verify(prepared)
        self.assertTrue(self.target.exists());self.assertTrue(old.exists())

    def test_foreign_target_arrival_during_no_replace_gap_preserves_both(self):
        prepared=self.prepare();self.extract(prepared)
        original=publication.retain_directory_no_replace
        def arrival(source,target,expected):
            process=subprocess.run([sys.executable,'-I','-B','-c',
                "import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.mkdir();(p/'foreign').write_bytes(b'preserve')",str(target)],timeout=30)
            self.assertEqual(process.returncode,0)
            return original(source,target,expected)
        with patch.object(publication,'retain_directory_no_replace',arrival):
            with self.assertRaises(DirectoryRetentionRefused):self.verify(prepared)
        self.assertEqual((self.target/'foreign').read_bytes(),b'preserve')
        self.assertEqual((Path(prepared['stage'])/'Books Arranger.exe').read_bytes(),self.payload['Books Arranger.exe'])

    def test_earlier_empty_selection_converts_to_owned_new_placeholder(self):
        self.target.mkdir()
        with NativeItem(self.target,directory=True) as held:old=held.facts['identity']
        admission=publication.admit_empty_application_target(self.target,receipt_path=self.area/'selection.json')
        prepared=self.prepare(target_admission=admission)
        self.assertNotEqual(prepared['placeholder_identity'],old)
        self.extract(prepared);self.assertTrue(self.verify(prepared)['published'])

    def test_wrong_placeholder_identity_preserves_foreign_empty_directory(self):
        prepared=self.prepare();self.extract(prepared)
        self.target.rename(self.area/'OriginalPlaceholder');self.target.mkdir()
        with self.assertRaises(RelocationRefused):self.verify(prepared)
        self.assertTrue(self.target.is_dir());self.assertTrue(Path(prepared['stage']).is_dir())

    def test_readonly_payload_hashes_and_replay_after_placeholder_closed(self):
        prepared=self.prepare();self.extract(prepared)
        (Path(prepared['stage'])/'Books Arranger.exe').chmod(0o444)
        with patch.object(publication,'retain_directory_no_replace',side_effect=RuntimeError('before rename interruption')):
            with self.assertRaisesRegex(RuntimeError,'before rename'):self.verify(prepared)
        self.assertFalse(self.target.exists());self.assertTrue(Path(prepared['stage']).exists())
        self.assertTrue(self.verify(prepared)['published'])

    def test_pinned_package_change_is_refused_before_target_disposal(self):
        prepared=self.prepare();self.extract(prepared)
        self.package.write_bytes(self.package.read_bytes()+b' ')
        with self.assertRaises(RelocationRefused):self.verify(prepared)
        with NativeItem(self.target,directory=True) as held:self.assertEqual(held.facts['identity'],prepared['placeholder_identity'])

    def test_replacement_after_atomic_creation_never_acquires_owned_authority(self):
        original=publication._private_create
        def raced(path):
            created=original(path)
            if Path(path)==self.target:
                Path(path).rmdir() # exact empty private fixture only
                Path(path).mkdir();(Path(path)/'foreign').write_bytes(b'keep untouched')
            return created
        with patch.object(publication,'_private_create',raced):
            with self.assertRaisesRegex(RelocationRefused,'replaced'):self.prepare()
        self.assertEqual((self.target/'foreign').read_bytes(),b'keep untouched')
        self.assertFalse(Path(str(self.transaction)+'.plan.json').exists())


if __name__=='__main__':unittest.main()
