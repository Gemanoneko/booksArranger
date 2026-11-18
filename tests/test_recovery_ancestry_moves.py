"""0.30.0 item B: a source cleanup recorded before two storage moves still finds its own recovery folder.

Sergei's Brom cleanup recorded its recovery folder's ancestry under the original data folder (29 Oct). The data then
moved twice: an explicit relocation (a fresh copy, the original kept aside, the old root made a junction to the copy,
the sealed books-storage-relocation-v1 manifest), then the 14 Nov portable installation move
(books-portable-runtime-v1). Retry cleanup refused with "Persisted recovery ancestry changed".

These tests replay that history on private folders with real native identities: the operator's own census and
manifest validator for the first move; portable_storage_migration's own census, same-volume native rename and runtime
binding producer for the second. Then the cleanup's own recovery check runs (CleanupJobs._recovery_boundary).
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
import uuid

from native_io import BoundaryError, DirectoryBoundary, VerifiedFile
from scratch_area import DEFAULT_SCRATCH, remove_own_area
from source_cleanup import CleanupJobs
from storage_relocation import _key, parse_manifest
import portable_storage_migration as portable
import storage_relocation_native as native
import storage_relocation_operator as operator

PREFIX = 'recovery-ancestry-'
SCOPE = r'Projects\Books\data'
REFUSED = 'Persisted recovery ancestry changed'
COPY = b'recovery copy of an original'


@unittest.skipUnless(os.name == 'nt', 'Windows native identities and junctions')
class RecoveryAncestryAcrossMovesTests(unittest.TestCase):
    def setUp(self):
        base = Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT', DEFAULT_SCRATCH));base.mkdir(parents=True, exist_ok=True)
        self.area = base / (PREFIX + uuid.uuid4().hex);self.area.mkdir()
        remove_own_area(self, self.area, PREFIX)
        self.addCleanup(self._remove_junction)
        self.addCleanup(native.close)
        self.old_root = self.area / 'C'  # the old shared root; a junction to the copy after the first move
        self.new_root = self.area / 'I'  # the first move's target
        self.cleanup_id = str(uuid.uuid4())
        data = self.old_root / SCOPE
        data.mkdir(parents=True);(data / 'inventory.sqlite3.lock').write_bytes(b'')
        # A recovery folder recorded and then replaced before any move: a genuinely different recovery set.
        self.stale = self.record(data)
        (data / 'source-recovery').rename(data / 'retired-recovery')
        self.honest = self.record(data)  # the Brom cleanup's record (29 Oct)
        folder = data / 'source-recovery' / self.cleanup_id;folder.mkdir()
        (folder / '00000.mp3').write_bytes(COPY)
        # A recovery folder that no recorded move explains.
        self.elsewhere = self.record(self.area / 'Elsewhere')

    def _remove_junction(self):
        if os.path.isjunction(self.old_root):os.rmdir(self.old_root)  # removes the link only, never its target

    @staticmethod
    def record(data):
        """The ancestry a cleanup persists at enrolment: CleanupJobs.root_identity, stored as JSON in its intent."""
        jobs = CleanupJobs(data / 'inventory.sqlite3', data / 'source-recovery', lambda db, intent: True, contextlib.nullcontext)
        jobs.close()
        return json.loads(json.dumps(jobs.root_identity))

    @staticmethod
    def admit(descriptor, sha):
        """Select a storage relocation the way the app does at startup. The live catalog-owner lease it also requires
        (an owned catalog with its activation, verification and detach registrations) is outside this replay; every
        identity and ancestry comparison below is the production one."""
        context = native.configure(descriptor, sha)
        context.require_normal_operation = lambda: None
        return context

    def check(self, data, recorded):
        """The cleanup's own recovery check; Retry cleanup runs it before anything else."""
        jobs = CleanupJobs(data / 'inventory.sqlite3', data / 'source-recovery', lambda db, intent: True, contextlib.nullcontext)
        try:
            with contextlib.ExitStack() as stack:
                jobs._recovery_boundary(stack, jobs.root / self.cleanup_id, {'recovery_identity': recorded})
        finally:
            jobs.close()

    def move_explicitly(self):
        """The first move: a fresh copy (every folder gets a new native identity), the original kept aside, the old
        root a junction to the copy, and the manifest seal_target writes from the operator's census."""
        with contextlib.ExitStack() as stack:
            source_dirs, source_files, _ = operator._scan(self.old_root, (SCOPE,), stack)
        shutil.copytree(self.old_root, self.new_root)
        with contextlib.ExitStack() as stack:
            dirs, files, _ = operator._scan(self.new_root, (SCOPE,), stack)
        self.old_root.rename(self.area / 'C-original')
        result = subprocess.run([str(Path(os.environ['SystemRoot']) / 'System32/cmd.exe'), '/d', '/c', 'mklink', '/J',
                                 str(self.old_root), str(self.new_root)], capture_output=True, timeout=10, creationflags=0x08000000)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.catalog_id, self.generation = str(uuid.uuid4()), str(uuid.uuid4())
        descriptor = {'schema': 'books-storage-relocation-v1', 'generation': self.generation, 'catalog_id': self.catalog_id,
                      'source_root': str(self.old_root), 'target_root': str(self.new_root), 'scopes': [SCOPE],
                      'source_snapshot_sha256': source_files[_key(SCOPE + r'\inventory.sqlite3')]['sha256'],
                      'directories': [{'relative': row['relative'], 'source_identity': source_dirs[key]['identity'],
                                       'target_identity': row['identity']} for key, row in sorted(dirs.items())],
                      'files': [{'relative': source_files[key]['relative'], 'source_facts': source_files[key]['facts'],
                                 'target_facts': files[key]['facts'], 'sha256': source_files[key]['sha256'],
                                 'receipt_classes': ['recovery-copy']} for key in sorted(files) if '\\source-recovery\\' in key]}
        raw = operator.packed(descriptor);self.manifest_sha = operator.digest(raw);parse_manifest(raw, self.manifest_sha)
        self.manifest = self.area / 'operator' / 'relocation.json';self.manifest.parent.mkdir()
        operator.create_new(self.manifest, raw)

    def move_portably(self, previous=None):
        """A portable installation move (the 14 Nov move; with `previous`, a later one): the ancestry history step()
        records, then portable_storage_migration's own census, native rename and runtime binding producer."""
        if previous is None:
            self.admit(self.manifest, self.manifest_sha)
            logical = self.old_root / SCOPE
            with DirectoryBoundary(logical.anchor, logical) as boundary:  # step(): read through the junction
                origin = [list(row) for row in boundary.identities]
            source = self.new_root / SCOPE  # the installation's data folder is the physical copy
            controls = [[str(self.manifest), self.manifest_sha, 'relocation-manifest']]
            # Detach and retention receipts belong to the first move's later phases; nothing here reads them.
            marker = hashlib.sha256(b'fixture detach and retention receipts').hexdigest()
            history = dict(detach_sha256=marker, retention_sha256=marker, previous_namespace=None,
                           previous_registration=None, previous_ancestry=[])
            installation = self.area / 'Arranger'
        else:
            context = self.admit(*previous);ns = context.namespace
            origin = ns.value['origin_ancestry'];source = Path(ns.data)
            controls = [[r['origin'], r['sha256'], r['kind'], ns.control_path(r['origin'], r['sha256'])] for r in ns.value['controls']]
            controls.append([str(context.configuration_path), context.configuration_digest, 'previous-runtime', str(context.configuration_path)])
            history = dict(detach_sha256=ns.value['detach_sha256'], retention_sha256=ns.value['retention_sha256'],
                           previous_namespace=dict(ns.value), previous_ancestry=list(ns.value['previous_ancestry']),
                           previous_registration=[ns.origin.catalog_id, ns.origin.generation, ns.value['binding_id'],
                                                  ns.digest, ns.value['revision']])
            installation = self.area / 'Arranger-later'
        with DirectoryBoundary(source.anchor, source) as boundary:
            history['previous_ancestry'] += [list(row) for row in boundary.identities]
        native.close()
        history.update(catalog_id=self.catalog_id, generation=self.generation, scope=SCOPE, source_root=str(self.old_root),
                       target_root=str(self.new_root), controls=controls, origin_ancestry=origin)
        storage = installation / 'Storage';storage.mkdir(parents=True)
        migration = str(uuid.uuid4());stem = storage / ('migration-' + migration)
        def stage(name):return Path(str(stem) + '.' + name + '.json')
        portable._new(stage('history'), history)
        with DirectoryBoundary(source.anchor, source), VerifiedFile(source / 'inventory.sqlite3.lock', writable=True) as lock:
            portable._new(stage('snapshot'), portable._census(source, lock))
        snapshot = portable._read(stage('snapshot'))[0]
        target = installation / 'Data'
        portable._move_directory(source, target, snapshot['directories']['']['facts']['identity'])
        portable._new(stage('moved'), portable._census(target))
        portable._finish_guarded(dict(migration_id=migration, source_data=str(source)),
                                 dict(storage_relocation=dict(manifest=str(self.manifest), sha256=self.manifest_sha)),
                                 installation, installation / 'installation.json', stage, snapshot)
        bound = portable._read(stage('bound'))[0]['storage_relocation']
        self.data = target
        return bound['manifest'], bound['sha256']

    def test_recovery_recorded_before_two_moves_is_still_its_own(self):
        self.move_explicitly()
        self.admit(self.manifest, self.manifest_sha)
        self.check(self.old_root / SCOPE, self.honest)  # one move: the relocation manifest bridges it
        native.close()
        self.admit(*self.move_portably())
        self.check(self.data, self.honest)  # both moves: Sergei's Brom cleanup
        self.assertEqual((self.data / 'source-recovery' / self.cleanup_id / '00000.mp3').read_bytes(), COPY)

    def test_different_recovery_sets_after_two_moves_stay_refused(self):
        self.move_explicitly()
        runtime = self.move_portably()
        self.admit(*runtime)
        root = next(i for i, row in enumerate(self.honest) if _key(row[0]) == _key(str(self.old_root)))
        forged = [list(row) for row in self.honest];forged[root][1:] = self.elsewhere[-2][1:]
        for name, recorded in (('replaced before the moves', self.stale), ('outside every recorded move', self.elsewhere),
                               ('old root identity no record proves', forged)):
            with self.subTest(name), self.assertRaisesRegex(BoundaryError, REFUSED):
                self.check(self.data, recorded)
        # The recovery folder itself replaced after the moves: same name, same bytes, another folder. The selected
        # relocation holds the data folder against writers, so this happens while the app is closed.
        native.close()
        (self.data / 'source-recovery').rename(self.data / 'moved-aside')
        folder = self.data / 'source-recovery' / self.cleanup_id;folder.mkdir(parents=True)
        (folder / '00000.mp3').write_bytes(COPY)
        self.admit(*runtime)
        with self.assertRaisesRegex(BoundaryError, REFUSED):
            self.check(self.data, self.honest)

    def test_a_later_portable_move_extends_the_chain(self):
        self.move_explicitly()
        first = self.move_portably()
        self.admit(*first)
        between = self.record(self.data)  # a cleanup enrolled between the second and third move
        native.close()
        self.admit(*self.move_portably(first))
        for name, recorded in (('before every move', self.honest), ('between the moves', between)):
            with self.subTest(name):
                self.check(self.data, recorded)
        with self.assertRaisesRegex(BoundaryError, REFUSED):
            self.check(self.data, self.stale)


if __name__ == '__main__':
    unittest.main()
