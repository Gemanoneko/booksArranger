"""Private native transaction/fencing controls; no installed app or user catalog."""
import contextlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

from storage_relocation import RelocationRefused
from storage_relocation_operator import (NativeItem, Security, prepare_source, seal_target,
    activate_target, verify_target, enable_target, rollback_unwritten, classify_historical_files, digest, packed,
    verify_source_fence, security_equivalent)
from storage_relocation_operator import recover_unactivated_source


class OperatorPureTests(unittest.TestCase):
    def test_security_equivalence_does_not_hide_permission_or_owner_changes(self):
        original = {'sddl': 'O:SYG:SYD:(A;ID;FA;;;SY)', 'protected': False}
        auto = {'sddl': 'O:SYG:SYD:AI(A;ID;FA;;;SY)', 'protected': False}
        self.assertTrue(security_equivalent(auto, original))
        for changed in ('O:BAG:SYD:AI(A;ID;FA;;;SY)', 'O:SYG:SYD:AI(A;ID;FR;;;SY)',
                        'O:SYG:SYD:AI(A;ID;FA;;;BA)', 'O:SYG:SYD:PAI(A;ID;FA;;;SY)'):
            self.assertFalse(security_equivalent(dict(auto, sddl=changed), original))
        protected = {'sddl': 'O:SYG:SYD:PAI(A;;FA;;;SY)', 'protected': True}
        self.assertTrue(security_equivalent(protected, original, copied_target=True))
        self.assertFalse(security_equivalent(dict(protected, protected=False), original, copied_target=True))


@unittest.skipUnless(os.name == 'nt', 'Native Windows relocation tests')
class OperatorNativeTests(unittest.TestCase):
    def setUp(self):
        default = Path(__file__).resolve().parents[1] / 'scratch'
        area = Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT', str(default)))
        area.mkdir(parents=True, exist_ok=True)
        source_area = Path(os.environ.get('BOOKS_OPERATOR_C_ROOT', str(area)))
        source_area.mkdir(parents=True, exist_ok=True)
        self.tag = 'storage-operator-' + uuid.uuid4().hex
        self.area = area / self.tag; self.area.mkdir()
        self.source = source_area / (self.tag + '-source')
        (self.source / 'data').mkdir(parents=True)
        self.target = self.area / 'target'
        self.work = self.area / 'transaction'; self.work.mkdir()
        self.database = self.source / 'data/inventory.sqlite3'
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.executescript('CREATE TABLE jobs(state TEXT); CREATE TABLE queue(state TEXT);'
                             'CREATE TABLE files(root TEXT,path TEXT,size INTEGER,modified INTEGER,kind TEXT);'
                             'CREATE TABLE decisions(id TEXT,value TEXT);')
            db.execute('INSERT INTO decisions VALUES(?,?)', ('kept', 'original decision'))
            db.commit()
        Path(str(self.database) + '.lock').write_bytes(b'0')
        self.original = self.source / 'data/owned.bin'; self.original.write_bytes(b'original owned bytes')
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE owned_artifacts(path TEXT,sha256 TEXT,size INTEGER,kind TEXT)')
            db.execute('INSERT INTO owned_artifacts VALUES(?,?,?,?)',(str(self.original),digest(self.original.read_bytes()),self.original.stat().st_size,'recovery'))
            db.commit()
        self.manifest = self.work / 'relocation.json'
        self.backup = None
        self.receipts = []

    def tearDown(self):
        # Only these NEW private fixtures are normalized for the studio cleanup.
        # This is not production rollback after post-activation writes.
        source = self.backup or self.source
        for receipt in self.receipts:
            if not Path(receipt).exists():continue
            record = json.loads(Path(receipt).read_text('utf8'))
            root = Path(record['source_original'])
            if not root.exists() and self.backup:root = self.backup
            for entry in sorted(record['items'], key=lambda e: (e['relative'].count('\\'), e['relative'])):
                path = root / entry['relative']
                if not path.exists():continue
                with NativeItem(path, directory=entry['kind'] == 'directory', writable_security=True) as held:
                    self.assertEqual(held.facts['identity'], entry['identity'])
                    Security().restore(held, entry['original_security'])

    def args(self):
        return (self.source, self.target, ['data'], 'data/inventory.sqlite3', self.work)

    def test_broad_repo_unknown_data_and_library_paths_never_gain_cleanup_ownership(self):
        (self.source/'.git').mkdir();(self.source/'.git/config').write_bytes(b'private git history')
        (self.source/'program.py').write_bytes(b'private source')
        args=(self.source.parent,self.area.parent/('uncreated-'+uuid.uuid4().hex),[self.source.name],
            self.source.name+'/data/inventory.sqlite3',self.work)
        with self.assertRaisesRegex(RelocationRefused,'exact selected catalog parent'):
            prepare_source(*args)
        unknown=self.source/'data/unknown-user-document.txt';unknown.write_bytes(b'not application owned')
        with self.assertRaisesRegex(RelocationRefused,'Unknown file'):
            prepare_source(*self.args())
        self.assertEqual(unknown.read_bytes(),b'not application owned');unknown.unlink()
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('INSERT INTO files VALUES(?,?,?,?,?)',(str(self.source/'data'),str(self.original),self.original.stat().st_size,0,'audiobook'))
            db.commit()
        with self.assertRaisesRegex(RelocationRefused,'library/source/output'):
            prepare_source(*self.args())
        self.assertTrue((self.source/'.git/config').exists());self.assertTrue(self.original.exists())
        with contextlib.closing(sqlite3.connect(self.database)) as db:db.execute('DELETE FROM files');db.commit()
        plan=prepare_source(*self.args())
        self.assertEqual(plan['owned_state']['schema'],'books-typed-catalog-membership-v1')
        self.assertNotIn('program.py',{r['relative'] for r in plan['files']})

    def test_prepared_producer_checkpoint_stays_held_without_copy_closure_authority(self):
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE producer_recovery_checkpoints(state TEXT,native TEXT)')
            db.execute('INSERT INTO producer_recovery_checkpoints VALUES(?,?)',('prepared','old native observation'))
            db.commit()
        plan=prepare_source(*self.args())
        self.assertTrue(any(row['class']=='producer_recovery_checkpoints' and row['state']=='prepared' for row in plan['held_classes']))
        _,sealed=self.copied()
        self.assertFalse(sealed['complete'])
        activate_target(self.manifest,sealed['manifest_sha256'])
        verified=verify_target(self.manifest,sealed['manifest_sha256'])
        self.assertFalse(verified['complete'])
        with self.assertRaisesRegex(RelocationRefused,'Unsupported|held|reconciliation'):
            enable_target(self.manifest,sealed['manifest_sha256'],verified['verification_path'],verified['verification_sha256'])

    def test_pending_offline_publication_plan_is_held_before_catalog_native_identity_changes(self):
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE output_relocations(publication_id TEXT,stage TEXT)')
            db.execute('INSERT INTO output_relocations VALUES(?,?)',('private-publication','old_removal_intent'));db.commit()
        plan=prepare_source(*self.args())
        self.assertTrue(any(row['class']=='output_relocations' for row in plan['held_classes']))
        self.original.write_bytes(b'positive preview did not fence source')
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute("UPDATE output_relocations SET stage='complete'");db.commit()
        classes,held=classify_historical_files(self.database,managed_root=str(self.source))
        self.assertFalse(any(row['class']=='output_relocations' for row in held))

    def test_origin_only_uncertain_attempt_requires_source_reconciliation(self):
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE working_attempts(job_id TEXT,attempt_id TEXT,state TEXT,producer TEXT)')
            db.execute('INSERT INTO working_attempts VALUES(?,?,?,?)',(str(uuid.uuid4()),str(uuid.uuid4()),'uncertain','uncertain'))
            db.execute('CREATE TABLE producer_origin_facts(id TEXT,record TEXT)')
            db.execute('INSERT INTO producer_origin_facts VALUES(?,?)',('historical','Uncertainty is not closure authority'))
            db.commit()
        with self.assertRaisesRegex(RelocationRefused,'Unclosed/uncertain producer'):
            prepare_source(*self.args())
        self.original.write_bytes(b'positive source remained unfenced')

    def prepare(self):
        preview = prepare_source(*self.args())
        prepared = prepare_source(*self.args(), apply=True, catalog_id=preview['catalog_id'],
                    generation=preview['generation'], expected_plan_sha256=preview['consent_sha256'])
        self.receipts.append(prepared['source_fence'])
        return prepared

    def copied(self):
        prepared = self.prepare()
        shutil.copytree(self.source, self.target, copy_function=shutil.copy2)
        self.backup = self.source.with_name(self.source.name + '-original')
        self.source.rename(self.backup)
        sealed = seal_target(prepared['source_plan'], prepared['source_plan_sha256'],
                             prepared['source_fence'], prepared['source_fence_sha256'],
                             self.backup, self.manifest)
        self.receipts.append(str(self.manifest) + '.source-fence.json')
        return prepared, sealed

    def enabled(self, sealed):
        verifying = activate_target(self.manifest, sealed['manifest_sha256'])
        self.assertEqual(verifying['phase'], 'verifying')
        self.assertEqual(verifying, activate_target(self.manifest, sealed['manifest_sha256']))
        verified = verify_target(self.manifest, sealed['manifest_sha256'])
        active = enable_target(self.manifest, sealed['manifest_sha256'],
                               verified['verification_path'], verified['verification_sha256'])
        return active

    def test_complete_native_cycle_original_fence_and_unwritten_rollback(self):
        prepared, sealed = self.copied()
        original = self.backup / 'data/owned.bin'
        with self.assertRaises(PermissionError):original.write_bytes(b'forbidden')
        with self.assertRaises(PermissionError):(self.backup / 'data/new.bin').write_bytes(b'forbidden')
        with contextlib.closing(sqlite3.connect(self.backup / 'data/inventory.sqlite3')) as old_writer:
            with self.assertRaises(sqlite3.OperationalError):
                old_writer.execute('INSERT INTO decisions VALUES(?,?)', ('forbidden', 'old writer'))
        active = self.enabled(sealed)
        self.assertEqual(active['phase'], 'active')
        with verify_source_fence(str(self.manifest) + '.source-fence.json', sealed['source_fence_sha256']) as lease:
            lease.revalidate()
            self.assertEqual(lease.receipt['source_original'], str(self.backup))
        result = rollback_unwritten(self.manifest, sealed['manifest_sha256'])
        self.receipts.append(str(self.manifest) + '.rollback-target-fence.json')
        self.assertIn('write-fenced', result['disposition'])
        original.write_bytes(b'rollback original positive')
        with self.assertRaises(PermissionError):(self.target / 'data/owned.bin').write_bytes(b'forbidden')
        self.assertEqual((self.target / 'data/owned.bin').read_bytes(), b'original owned bytes')

    def test_new_target_decision_refuses_stale_rollback_and_keeps_source_fenced(self):
        _, sealed = self.copied(); self.enabled(sealed)
        with contextlib.closing(sqlite3.connect(self.target / 'data/inventory.sqlite3')) as db:
            db.execute('INSERT INTO decisions VALUES(?,?)', ('new', 'post migration decision')); db.commit()
        with self.assertRaisesRegex(RelocationRefused, 'new target catalog writes'):
            rollback_unwritten(self.manifest, sealed['manifest_sha256'])
        with self.assertRaises(PermissionError):(self.backup / 'data/owned.bin').write_bytes(b'forbidden')
        with contextlib.closing(sqlite3.connect(self.target / 'data/inventory.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT value FROM decisions WHERE id=?', ('new',)).fetchone()[0],
                             'post migration decision')

    def test_reviewed_source_plan_drift_or_live_writer_refuses_before_fence(self):
        preview = prepare_source(*self.args())
        self.original.write_bytes(b'changed after preview')
        with self.assertRaisesRegex(RelocationRefused, 'reviewed SHA|catalog-owned bytes changed'):
            prepare_source(*self.args(), apply=True, catalog_id=preview['catalog_id'],
                           generation=preview['generation'], expected_plan_sha256=preview['consent_sha256'])
        self.original.write_bytes(b'still writable positive')
        with open(self.original, 'r+b'):
            with self.assertRaisesRegex(RelocationRefused, 'exclude writers'):prepare_source(*self.args())
        self.original.write_bytes(b'original owned bytes')
        self.assertTrue(prepare_source(*self.args())['files'])

    def test_unknown_target_member_refuses_seal_keeps_both_copies(self):
        prepared = self.prepare(); shutil.copytree(self.source, self.target)
        (self.target / 'data/unowned.txt').write_bytes(b'unknown content')
        self.backup = self.source.with_name(self.source.name + '-original'); self.source.rename(self.backup)
        with self.assertRaisesRegex(RelocationRefused, 'membership differs'):
            seal_target(prepared['source_plan'], prepared['source_plan_sha256'],
                        prepared['source_fence'], prepared['source_fence_sha256'], self.backup, self.manifest)
        self.assertTrue((self.target / 'data/unowned.txt').exists())
        self.assertTrue((self.backup / 'data/owned.bin').exists())
        self.assertFalse(self.manifest.exists())

    def test_wal_shm_inspection_consents_volatile_time_but_preserves_exact_fenced_facts(self):
        # A deliberately crashed PRIVATE SQLite writer leaves committed WAL/SHM.
        # No application or user database is used by this fixture.
        script = self.work / 'leave-private-wal.py'
        script.write_text('import sqlite3,os,sys\n'
                          'db=sqlite3.connect(sys.argv[1]);db.execute("PRAGMA journal_mode=WAL")\n'
                          'db.execute("INSERT INTO decisions VALUES(?,?)",("wal","committed WAL value"));db.commit()\n'
                          'os._exit(0)\n', encoding='utf8')
        subprocess.run([sys.executable, '-I', '-B', str(script), str(self.database)],
                       check=True, timeout=30, creationflags=0x08000000)
        self.assertTrue(Path(str(self.database) + '-wal').exists())
        self.assertTrue(Path(str(self.database) + '-shm').exists())
        preview = prepare_source(*self.args())
        prepared = prepare_source(*self.args(), apply=True, catalog_id=preview['catalog_id'],
                    generation=preview['generation'], expected_plan_sha256=preview['consent_sha256'])
        self.receipts.append(prepared['source_fence'])
        plan = json.loads(Path(prepared['source_plan']).read_text('utf8'))
        shm = next(row for row in plan['files'] if row['relative'].endswith('-shm'))
        with NativeItem(self.source / shm['relative']) as item:
            self.assertEqual(item.facts, shm['facts'])
            self.assertEqual(item.sha256(), shm['sha256'])
        with contextlib.closing(sqlite3.connect(prepared['snapshot'])) as backup:
            self.assertEqual(backup.execute('SELECT value FROM decisions WHERE id=?', ('wal',)).fetchone()[0],
                             'committed WAL value')

    def test_copied_source_fence_acl_is_removed_only_on_owned_target(self):
        prepared = self.prepare(); shutil.copytree(self.source, self.target)
        fence = json.loads(Path(prepared['source_fence']).read_text('utf8'))
        for entry in sorted(fence['items'], key=lambda e: (e['relative'].count('\\'), e['relative'])):
            with NativeItem(self.target / entry['relative'], directory=entry['kind'] == 'directory',
                            writable_security=True) as item:
                Security().restore(item, entry['applied_security'])
        with self.assertRaises(PermissionError):(self.target / 'data/owned.bin').write_bytes(b'forbidden')
        self.backup = self.source.with_name(self.source.name + '-original'); self.source.rename(self.backup)
        sealed = seal_target(prepared['source_plan'], prepared['source_plan_sha256'],
                             prepared['source_fence'], prepared['source_fence_sha256'], self.backup, self.manifest)
        self.receipts.append(str(self.manifest) + '.source-fence.json')
        (self.target / 'data/owned.bin').write_bytes(b'target positive after owned ACL restoration')
        with self.assertRaises(PermissionError):(self.backup / 'data/owned.bin').write_bytes(b'forbidden')
        self.assertEqual(sealed['phase'], 'sealed-not-active')

    def test_source_prepare_interruption_has_pinned_original_acl_recovery(self):
        import storage_relocation_operator as operator
        preview = prepare_source(*self.args()); calls = []
        original = Security.deny_writes
        def fail_second(security, item):
            calls.append(str(item.path))
            if len(calls) == 2:raise RuntimeError('private interruption before second DACL')
            return original(security, item)
        with patch.object(Security, 'deny_writes', fail_second):
            with self.assertRaisesRegex(RuntimeError, 'private interruption'):
                prepare_source(*self.args(), apply=True, catalog_id=preview['catalog_id'],
                    generation=preview['generation'], expected_plan_sha256=preview['consent_sha256'])
        plan = self.work / ('source-plan-' + preview['generation'] + '.json')
        failure = self.work / ('source-fence-failed-' + preview['generation'] + '.json')
        self.assertTrue(plan.exists() and failure.exists())
        result = recover_unactivated_source(plan, digest(plan.read_bytes()))
        self.assertEqual(result['disposition'], 'source permissions restored; no content changed')
        self.assertEqual(result, recover_unactivated_source(plan, digest(plan.read_bytes())))
        (self.source / 'data/recovered-positive.bin').write_bytes(b'permissions restored')
        self.assertEqual(self.original.read_bytes(), b'original owned bytes')

    def test_target_seal_interruption_after_sql_commit_replays_exact_generation(self):
        import storage_relocation_operator as operator
        prepared = self.prepare(); shutil.copytree(self.source, self.target)
        self.backup = self.source.with_name(self.source.name + '-original'); self.source.rename(self.backup)
        self.receipts.append(str(self.manifest) + '.source-fence.json')
        original = operator.create_new
        def fail_seal(path, raw):
            if str(path).endswith('.sealed.json'):raise RuntimeError('private interruption after sealed SQL')
            return original(path, raw)
        args = (prepared['source_plan'], prepared['source_plan_sha256'], prepared['source_fence'],
                prepared['source_fence_sha256'], self.backup, self.manifest)
        with patch.object(operator, 'create_new', fail_seal):
            with self.assertRaisesRegex(RuntimeError, 'after sealed SQL'):seal_target(*args)
        self.assertTrue(self.manifest.exists())
        self.assertFalse(Path(str(self.manifest) + '.sealed.json').exists())
        sealed = seal_target(*args)
        self.assertEqual(sealed['generation'], prepared['generation'])
        self.assertEqual(self.enabled(sealed)['phase'], 'active')

    def test_index_registry_bridges_database_and_journal_only_from_typed_owner(self):
        index = self.source / 'data/openlibrary-index'; index.mkdir()
        leaf = index / 'active.sqlite3'; leaf.write_bytes(b'private index data fixture')
        journal = index / 'active.sqlite3-journal'; journal.write_bytes(b'private index journal fixture')
        with NativeItem(leaf) as data, NativeItem(journal) as sidecar:
            owner = {'binding': 'openlibrary-active-v1',
                     'identities': [data.facts['identity'], sidecar.facts['identity']]}
        receipt = index / 'active.sqlite3.owner.json'; receipt.write_bytes(packed(owner))
        classes, held = classify_historical_files(self.database)
        self.assertEqual(classes[str(leaf)], ['index-leaf'])
        self.assertEqual(classes[str(journal)], ['index-journal'])
        self.assertFalse(held)
        receipt.write_bytes(packed(dict(owner, binding='unrecognized')))
        classes, held = classify_historical_files(self.database)
        self.assertNotIn(str(leaf), classes)
        self.assertTrue(any(record['class'] == 'openlibrary-index' for record in held))

    def test_verification_then_same_identity_changed_bytes_refuses_enable(self):
        _, sealed = self.copied()
        activate_target(self.manifest, sealed['manifest_sha256'])
        with contextlib.closing(sqlite3.connect(self.target / 'data/inventory.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT phase,revision FROM storage_relocation_activation').fetchone(),
                             ('verifying', 2))
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='storage_relocation_verification'").fetchone())
        verified = verify_target(self.manifest, sealed['manifest_sha256'])
        path = self.target / 'data/owned.bin'; before = path.stat(); raw = path.read_bytes()
        path.write_bytes(b'X' + raw[1:]); os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(path.stat().st_ino, before.st_ino)
        with self.assertRaisesRegex(RelocationRefused, 'bytes changed'):
            enable_target(self.manifest, sealed['manifest_sha256'],
                          verified['verification_path'], verified['verification_sha256'])
        with self.assertRaises(PermissionError):(self.backup / 'data/owned.bin').write_bytes(b'forbidden')

    def test_verification_pin_and_full_activation_row_must_match(self):
        _, sealed = self.copied(); activate_target(self.manifest, sealed['manifest_sha256'])
        verified = verify_target(self.manifest, sealed['manifest_sha256'])
        with self.assertRaisesRegex(RelocationRefused, 'fingerprint'):
            enable_target(self.manifest, sealed['manifest_sha256'], verified['verification_path'], '0' * 64)
        with contextlib.closing(sqlite3.connect(self.target / 'data/inventory.sqlite3')) as db:
            db.execute('UPDATE storage_relocation_activation SET source_fence_sha256=?', ('0' * 64,)); db.commit()
        with self.assertRaisesRegex(RelocationRefused, 'verification-only generation'):
            verify_target(self.manifest, sealed['manifest_sha256'])
        with contextlib.closing(sqlite3.connect(self.target / 'data/inventory.sqlite3')) as db:
            db.execute('UPDATE storage_relocation_activation SET source_fence_sha256=?', (sealed['source_fence_sha256'],)); db.commit()
        active = enable_target(self.manifest, sealed['manifest_sha256'],
                               verified['verification_path'], verified['verification_sha256'])
        self.assertEqual(active['phase'], 'active')

    def test_terminal_unmoved_inplace_and_disposed_checkpoint_history_need_no_bridge(self):
        from inplace_m4b import SCHEMA
        intent = {'schema': SCHEMA, 'job_id': 'terminal-job', 'attempt_id': 'terminal-attempt',
                  'path': r'Z:\library\old.m4b', 'root': r'Z:\library', 'destination': r'Z:\sorted\book.m4b',
                  'identity': [1, 0, 1], 'size': 100, 'modified': 123456700, 'attributes': 32,
                  'sha256': 'a' * 64, 'type_offset': 0, 'appended_size': 100,
                  'appended_sha256': 'b' * 64, 'output_size': 200, 'output_sha256': 'c' * 64, 'zone_marker': None}
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE inplace_edits(job_id TEXT,attempt_id TEXT,path TEXT,state TEXT,intent TEXT,detail TEXT,updated TEXT)')
            db.execute('CREATE TABLE audio_jobs(job_id TEXT,state TEXT,output TEXT)')
            db.execute('CREATE TABLE producer_recovery_checkpoints(state TEXT,native TEXT)')
            db.execute('INSERT INTO inplace_edits VALUES(?,?,?,?,?,?,?)', ('terminal-job','terminal-attempt',
                intent['path'],'published',json.dumps(intent),'{}','initial'))
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?)', ('terminal-job','completed',
                json.dumps({'final_path':intent['destination'],'sha256':intent['output_sha256']})))
            db.execute('INSERT INTO producer_recovery_checkpoints VALUES(?,?)', ('disposed','old immutable proof bytes'))
            db.commit()
        _, held = classify_historical_files(self.database, managed_root=str(self.source))
        self.assertFalse(held)
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('UPDATE inplace_edits SET state=?', ('unresolved',)); db.commit()
        _, held = classify_historical_files(self.database, managed_root=str(self.source))
        self.assertTrue(any(record['class'] == 'inplace_edits' for record in held))

    def test_hardlink_and_ads_refuse_without_deleting_anything(self):
        link = self.original.with_name('alias.bin'); os.link(self.original, link)
        with self.assertRaisesRegex(RelocationRefused, 'Hardlinked'):prepare_source(*self.args())
        link.unlink()
        with open(str(self.original) + ':unexpected', 'wb') as stream:stream.write(b'owned negative fixture')
        with self.assertRaises(ValueError):prepare_source(*self.args())
        self.assertTrue(self.original.exists())

    def test_directory_ads_refuses_without_hiding_its_bytes(self):
        stream=str(self.source/'data')+':unrecognized'
        with open(stream,'wb') as output:output.write(b'owned directory ADS negative fixture')
        with self.assertRaisesRegex(RelocationRefused,'directory stream'):prepare_source(*self.args())
        with open(stream,'rb') as preserved:self.assertEqual(preserved.read(),b'owned directory ADS negative fixture')


if __name__ == '__main__':unittest.main()
