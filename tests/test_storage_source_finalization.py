"""Old-copy file cleanup retains native write fences and exact disposal proof."""
import contextlib
import copy
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from test_storage_relocation_operator import OperatorNativeTests
from storage_relocation import RelocationRefused
from storage_relocation_operator import digest, packed
from storage_source_finalization import (plan_source_finalization, apply_source_finalization,
                                         verify_source_finalization)


class SourceFinalizationTests(OperatorNativeTests):
    # Inherit fixture helpers only; inherited test methods are removed below so
    # this module does not duplicate the operator suite.
    def test_forged_source_plan_members_cannot_authorize_source_git_or_unknown_data_removal(self):
        (self.source/'.git').mkdir();(self.source/'.git/config').write_bytes(b'protected history')
        (self.source/'program.py').write_bytes(b'protected source')
        prepared,sealed=self.copied();self.enabled(sealed)
        original=json.loads(Path(prepared['source_plan']).read_text('utf8'))
        seal_path=Path(str(self.manifest)+'.sealed.json');seal_bytes=seal_path.read_bytes()
        base=json.loads(seal_bytes)
        try:
            for relative in ('data/program.py','data/unknown-user-file.txt','data/library-book.m4b'):
                forged=copy.deepcopy(original);member=copy.deepcopy(forged['files'][0]);member['relative']=relative
                forged['files'].append(member)
                forged['owned_state']['files'].append({'relative':relative,'sha256':member['sha256'],'kind':'catalog-row'})
                filename=self.work/('forged-'+relative.rsplit('/',1)[-1]+'.json')
                filename.write_bytes(packed(forged))
                changed=dict(base,source_plan=str(filename),source_plan_sha256=digest(packed(forged)))
                seal_path.write_bytes(packed(changed))
                with self.assertRaises(RelocationRefused):plan_source_finalization(self.manifest,sealed['manifest_sha256'])
                self.assertTrue((self.backup/'data/owned.bin').exists())
                self.assertEqual((self.backup/'.git/config').read_bytes(),b'protected history')
                self.assertEqual((self.backup/'program.py').read_bytes(),b'protected source')
        finally:seal_path.write_bytes(seal_bytes)

    def test_lifecycle_group_requires_exact_review_and_explicit_rollback_forfeiture(self):
        from storage_lifecycle_retirement import review_source_retirement,execute_source_retirement
        _,sealed=self.copied();self.enabled(sealed)
        group=review_source_retirement(self.manifest,sealed['manifest_sha256'],
            protected_paths=[str(self.target/'data')])
        self.assertEqual(group['scope_paths'],[str(self.backup/'data')])
        self.assertEqual(group['role'],'retained-source')
        with self.assertRaisesRegex(RelocationRefused,'forfeiture'):
            execute_source_retirement(group['review'],group['review_sha256'],selected_roots=[group['group_id']])
        with self.assertRaisesRegex(RelocationRefused,'complete explicitly reviewed'):
            execute_source_retirement(group['review'],group['review_sha256'],
                selected_roots=[str(self.backup)],forfeit_rollback=True)
        with self.assertRaisesRegex(RelocationRefused,'protected current'):
            execute_source_retirement(group['review'],group['review_sha256'],
                selected_roots=[group['group_id']],forfeit_rollback=True,
                protected_paths=[str(self.backup/'data/owned.bin')])
        self.assertTrue((self.backup/'data/owned.bin').exists())
        result=execute_source_retirement(group['review'],group['review_sha256'],
            selected_roots=[group['group_id']],forfeit_rollback=True,
            protected_paths=[str(self.target/'data')])
        self.assertTrue(result['complete']);self.assertFalse((self.backup/'data').exists())
        done=review_source_retirement(self.manifest,sealed['manifest_sha256'])
        self.assertEqual(done['state'],'already_removed');self.assertFalse(done['can_remove'])
        self.assertEqual(done['bytes'],0);self.assertEqual(done['scope_paths'],group['scope_paths'])

    def test_selected_data_retired_root_absence_and_reuse_do_not_affect_new_catalog(self):
        _,sealed=self.copied();self.enabled(sealed)
        plan=plan_source_finalization(self.manifest,sealed['manifest_sha256']);sha=digest(packed(plan))
        with self.assertRaisesRegex(RelocationRefused,'forfeiture'):
            apply_source_finalization(self.manifest,sealed['manifest_sha256'],sha)
        result=apply_source_finalization(self.manifest,sealed['manifest_sha256'],sha,forfeit_rollback=True)
        self.assertEqual(result['phase'],'retired');self.assertTrue(result['complete'])
        self.assertFalse(result['folder_holds'])
        self.assertFalse((self.backup/'data/inventory.sqlite3').exists())
        self.assertFalse((self.backup/'data/owned.bin').exists())
        self.assertFalse((self.backup/'data').exists())
        moved=self.backup.with_name(self.backup.name+'-retained-source');self.backup.rename(moved)
        with verify_source_finalization(result['receipt_path'],result['receipt_sha256'],
                                       database=self.target/'data/inventory.sqlite3') as lease:
            lease.revalidate()
            self.assertEqual(lease.receipt['source_snapshot_sha256'],plan['source_snapshot_sha256'])
        with contextlib.closing(sqlite3.connect(self.target/'data/inventory.sqlite3')) as db:
            db.execute('INSERT INTO decisions VALUES(?,?)',('after-old-cleanup','kept new work'));db.commit()
        with verify_source_finalization(result['receipt_path'],result['receipt_sha256'],
                                       database=self.target/'data/inventory.sqlite3') as lease:lease.revalidate()
        self.backup.mkdir();(self.backup/'unrelated.txt').write_bytes(b'new unrelated object')
        with verify_source_finalization(result['receipt_path'],result['receipt_sha256'],
                                       database=self.target/'data/inventory.sqlite3') as lease:lease.revalidate()
        self.assertEqual((self.backup/'unrelated.txt').read_bytes(),b'new unrelated object')
        replay=apply_source_finalization(self.manifest,sealed['manifest_sha256'],sha,forfeit_rollback=True)
        self.assertTrue(replay['complete']);self.assertEqual(replay['files_removed'],0)

    def test_nested_scope_directories_removed_shared_source_git_preserved(self):
        import uuid
        identifier=str(uuid.uuid4());nested=self.source/'data/source-recovery'/identifier
        nested.mkdir(parents=True);file=nested/'state.bin';file.write_bytes(b'owned')
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE source_cleanup(id TEXT,state TEXT)')
            db.execute('INSERT INTO source_cleanup VALUES(?,?)',(identifier,'removed'))
            db.execute('INSERT INTO owned_artifacts VALUES(?,?,?,?)',(str(file),digest(file.read_bytes()),file.stat().st_size,'recovery'))
            db.commit()
        (self.source/'.git').mkdir();(self.source/'.git/keep').write_bytes(b'history')
        (self.source/'source.py').write_bytes(b'print(1)')
        _,sealed=self.copied();self.enabled(sealed)
        plan=plan_source_finalization(self.manifest,sealed['manifest_sha256']);sha=digest(packed(plan))
        result=apply_source_finalization(self.manifest,sealed['manifest_sha256'],sha,forfeit_rollback=True)
        self.assertTrue(result['complete']);self.assertFalse((self.backup/'data').exists())
        self.assertEqual((self.backup/'.git/keep').read_bytes(),b'history')
        self.assertEqual((self.backup/'source.py').read_bytes(),b'print(1)')

    def test_directory_interruption_without_closed_receipt_stays_held(self):
        import storage_source_finalization as finalizer
        _,sealed=self.copied();self.enabled(sealed)
        plan=plan_source_finalization(self.manifest,sealed['manifest_sha256']);sha=digest(packed(plan))
        original=finalizer._publish_file
        def fail_directory(*args,**kwargs):
            if args[4]=='removed' and kwargs.get('kind')=='directory':raise RuntimeError('directory closed receipt interruption')
            return original(*args,**kwargs)
        with patch.object(finalizer,'_publish_file',fail_directory):
            with self.assertRaisesRegex(RuntimeError,'directory closed'):
                apply_source_finalization(self.manifest,sealed['manifest_sha256'],sha,forfeit_rollback=True)
        with self.assertRaises((RelocationRefused,FileNotFoundError)):
            with verify_source_finalization(str(self.manifest)+'.source-finalization.json',sha,
                                           database=self.target/'data/inventory.sqlite3'):pass

    def test_restart_after_directory_intent_rechecks_remaining_native_fence(self):
        import storage_source_finalization as finalizer
        _,sealed=self.copied();self.enabled(sealed)
        plan=plan_source_finalization(self.manifest,sealed['manifest_sha256']);sha=digest(packed(plan))
        with patch.object(finalizer.SourceDirectoryDelete,'dispose',side_effect=RuntimeError('before directory disposition')):
            with self.assertRaisesRegex(RuntimeError,'before directory'):
                apply_source_finalization(self.manifest,sealed['manifest_sha256'],sha,forfeit_rollback=True)
        with self.assertRaises(PermissionError):(self.backup/'data/new.bin').write_bytes(b'forbidden')
        with verify_source_finalization(str(self.manifest)+'.source-finalization.json',sha,
                                       database=self.target/'data/inventory.sqlite3') as lease:lease.revalidate()
        result=apply_source_finalization(self.manifest,sealed['manifest_sha256'],sha,forfeit_rollback=True)
        self.assertTrue(result['complete'])

    def test_delete_relaxed_directory_blocks_competing_ads_children_and_subdirectories(self):
        import storage_source_finalization as finalizer
        import subprocess,sys
        # Positive ordinary controls establish that these operations really
        # work on this local provider before invoking the protected path.
        ordinary=self.area/'ordinary-control';ordinary.mkdir()
        (ordinary/'child').write_bytes(b'allowed');(ordinary/'sub').mkdir()
        Path(str(ordinary)+':probe').write_bytes(b'allowed ADS')
        renamed=ordinary.with_name('ordinary-renamed');ordinary.rename(renamed);renamed.rename(ordinary)
        _,sealed=self.copied();self.enabled(sealed)
        plan=plan_source_finalization(self.manifest,sealed['manifest_sha256']);sha=digest(packed(plan))
        original=finalizer.SourceDirectoryDelete.dispose;observed=[]
        def probe(deleting,record,security):
            # A separate OS process competes while DELETE alone is relaxed.
            program="import pathlib,sys; p=pathlib.Path(sys.argv[1]); failures=0\nfor op in (lambda:(p/'child').write_bytes(b'x'),lambda:(p/'sub').mkdir(),lambda:pathlib.Path(str(p)+':arriving').write_bytes(b'x'),lambda:p.rename(p.with_name(p.name+'-raced'))):\n try:op()\n except PermissionError:failures+=1\nsys.exit(0 if failures==4 else 9)"
            child=subprocess.run([sys.executable,'-I','-B','-c',program,str(deleting.path)],capture_output=True,timeout=30)
            self.assertEqual(child.returncode,0,child.stderr.decode(errors='replace'));observed.append(record['relative'])
            return original(deleting,record,security)
        with patch.object(finalizer.SourceDirectoryDelete,'dispose',probe):
            result=apply_source_finalization(self.manifest,sealed['manifest_sha256'],sha,forfeit_rollback=True)
        self.assertTrue(result['complete']);self.assertTrue(observed)

    def test_interruption_after_disposition_never_adopts_intent_only_absence(self):
        import storage_source_finalization as finalizer
        _,sealed=self.copied();self.enabled(sealed)
        plan=plan_source_finalization(self.manifest,sealed['manifest_sha256']);sha=digest(packed(plan))
        original=finalizer._publish_file
        def fail_removed(database,certificate,certificate_path,relative,state,previous,**proof):
            if state=='removed':raise RuntimeError('private interruption before closed receipt registration')
            return original(database,certificate,certificate_path,relative,state,previous,**proof)
        with patch.object(finalizer,'_publish_file',fail_removed):
            with self.assertRaisesRegex(RuntimeError,'private interruption'):
                apply_source_finalization(self.manifest,sealed['manifest_sha256'],sha,forfeit_rollback=True)
        with self.assertRaises((RelocationRefused,FileNotFoundError)):
            with verify_source_finalization(str(self.manifest)+'.source-finalization.json',sha,
                                           database=self.target/'data/inventory.sqlite3'):pass
        with self.assertRaises(PermissionError):(self.backup/'data/new.bin').write_bytes(b'forbidden')
        with contextlib.closing(sqlite3.connect(self.target/'data/inventory.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT value FROM decisions WHERE id=?',('kept',)).fetchone()[0],
                             'original decision')


for _name in list(vars(OperatorNativeTests)):
    if _name.startswith('test_'):setattr(SourceFinalizationTests,_name,None)
del OperatorNativeTests

if __name__=='__main__':unittest.main()
