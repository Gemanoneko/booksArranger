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
import sqlite3
import subprocess
from types import SimpleNamespace
import unittest
import uuid

from merge_service import MergeService
from native_io import BoundaryError, DirectoryBoundary, VerifiedFile
import pause_state
from scanner import connect
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


class MovesReplay:
    """The two storage moves replayed on private folders (a mixin for a unittest.TestCase; 0.30.0 item A and sort-1 reuse
    it): self.old_root is the original data folder's root, self.data the data folder after move_portably()."""
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


@unittest.skipUnless(os.name == 'nt', 'Windows native identities and junctions')
class RecoveryAncestryAcrossMovesTests(MovesReplay, unittest.TestCase):
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


@unittest.skipUnless(os.name == 'nt', 'Windows native identities and junctions')
class HeldBeforeTheFixTests(MovesReplay, unittest.TestCase):
    """Futaba's 0.30.0 F1: Sergei's Brom cleanup was refused under 0.29.0 and held. The item B fix decides only when the
    check runs again, and nothing ran it again: Resume, Retry cleanup and a restart all left the held row as it was."""

    def policy(self):
        self.policy_calls += 1
        refused = self.refuse_from is not None and self.policy_calls >= self.refuse_from
        return (None if refused else str(self.sorted)), (str(self.library),)

    def worker(self, data):
        return CleanupJobs(data / 'inventory.sqlite3', data / 'source-recovery', lambda db, intent: True,
                           contextlib.nullcontext, output_policy=self.policy)

    def book(self, data, count=3):
        """A completed published book whose cleanup enrols at `data`, with its recovery copies made and its originals
        still in place (its library and Sorted folder are, like Z:, untouched by the storage moves)."""
        self.library = self.area / 'Library';self.library.mkdir()
        self.sorted = self.area / 'Sorted';self.sorted.mkdir()
        self.sources = []
        for index in range(count):
            path = self.library / ('%02d.mp3' % index);path.write_bytes(bytes([65 + index]) * 4096);facts = path.stat()
            self.sources.append({'path': str(path), 'size': facts.st_size, 'modified': str(facts.st_mtime_ns),
                                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        final = self.sorted / 'Brom.m4b';final.write_bytes(b'validated fixture output')
        with DirectoryBoundary(self.sorted, final.parent) as boundary:parent = boundary.identities
        digest = hashlib.sha256(final.read_bytes()).hexdigest();size = final.stat().st_size
        validation = {'passed': True, 'checks': 'Output checks passed', 'profile': 'fixture', 'sha256': digest, 'size': size,
                      'tags': {'media_type': '2', 'title': 'Brom', 'artist': 'Author'}, 'source_pcm_frames': [100] * count,
                      'source_pcm_rate': 100, 'decoded_duration': count, 'duration_tolerance': .01, 'chapters': []}
        job = {'job_id': 'brom', 'state': 'completed',
               'manifest': {'root': str(self.library), 'output_root': str(self.sorted), 'sources': self.sources,
                            'cover': {'path': str(final), 'sha256': digest}, 'profile': 'fixture',
                            'metadata': {'title': 'Brom', 'canonical_author': 'Author'}, 'chapters': []},
               'output': {'root': str(self.sorted), 'final_path': str(final), 'size': size, 'sha256': digest,
                          'parent_identity': parent, 'validation': validation}}
        self.policy_calls, self.refuse_from = 0, 3  # enrolment, the run's start, then its first removal is refused
        with connect(data / 'inventory.sqlite3') as db:
            db.execute('CREATE TABLE IF NOT EXISTS owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER)')
        jobs = self.worker(data)
        try:
            id = jobs.enroll(job, {})
            with self.assertRaisesRegex(BoundaryError, 'No sorted output folder'):jobs.run(id)
        finally:
            jobs.close()
        self.refuse_from = None
        self.assertEqual(self.members(data, id), ['backup_verified'] * count, 'positive control: every recovery copy is made')
        return id

    @staticmethod
    def catalog(data):
        return contextlib.closing(sqlite3.connect(data / 'inventory.sqlite3'))

    def members(self, data, id):
        with self.catalog(data) as db:
            return [row[0] for row in db.execute('SELECT state FROM cleanup_members WHERE cleanup_id=? ORDER BY path', (id,))]

    def row(self, id):
        with self.catalog(self.data) as db:
            return db.execute('SELECT state,reason FROM source_cleanup WHERE id=?', (id,)).fetchone()

    def sweep(self, worker, started=True):
        """The held-cleanup sweep the retention pass runs once the queue is idle (MergeService._finish_held_cleanups);
        only a Start admitted in this launch (`started`: the generation _authorize_automatic_cleanup records) authorizes it."""
        service = MergeService.__new__(MergeService)
        service.jobs = SimpleNamespace(_thread=None);service.cleanup = worker;service._purge_tried = set()
        service._kept_by_choice = lambda job_ids: set();service._settle_folder_jobs = lambda: None
        service.inventory = SimpleNamespace(database=str(self.data / 'inventory.sqlite3'));service.draining = False
        service._start_generation = 0
        if started:service._automatic_cleanup_generation = 0
        service._finish_held_cleanups()
        if worker.thread is not None:
            worker.thread.join(120);self.assertFalse(worker.thread.is_alive())

    def originals_kept(self):
        return all(Path(source['path']).exists() for source in self.sources)

    def test_a_cleanup_held_under_0_29_0_is_checked_again_and_finishes(self):
        id = self.book(self.old_root / SCOPE)  # 29 Oct: enrolled, recovery copies made, originals still in place
        self.move_explicitly()
        runtime = self.move_portably()
        with self.catalog(self.data) as db:
            backups = [row[0] for row in db.execute('SELECT backup FROM cleanup_members WHERE cleanup_id=?', (id,))]
            self.assertTrue(backups and all(Path(path).parent == self.data / 'source-recovery' / id for path in backups),
                            'the portable move rewrote the recovery copies\' current paths')
            # The row exactly as 0.29.0's hold() left it after the refusal: needs attention, that reason, no hold cause.
            with db:db.execute("UPDATE source_cleanup SET state='needs_attention',reason=?,updated=? WHERE id=?",
                               (REFUSED, '2026-11-18T10:09:00.000000+00:00', id))
            self.assertEqual(db.execute('SELECT count(*) FROM source_cleanup_holds WHERE cleanup_id=?', (id,)).fetchone()[0], 0)
        honest = json.loads(self.intent(id))
        self.admit(*runtime)
        worker = self.worker(self.data)  # a restart: startup changes nothing and starts nothing
        self.assertEqual(tuple(self.row(id)), ('needs_attention', REFUSED));self.assertIsNone(worker.thread)
        self.sweep(worker, started=False)  # no Start pressed: the held cleanup is left alone
        self.assertIsNone(worker.thread);self.assertEqual(tuple(self.row(id)), ('needs_attention', REFUSED))
        # 0.30.0 R2-1: a Pause saved in the catalog holds it after a Start too: a safety hold records one without ending
        # the Start (AudioJobs._hold_queue), read here from the real catalog.
        with self.catalog(self.data) as db, db:pause_state.record(db, 'jobs', 'interrupted', 'Audiobook jobs stopped at a safety hold')
        self.sweep(worker)
        self.assertIsNone(worker.thread);self.assertEqual(tuple(self.row(id)), ('needs_attention', REFUSED))
        with self.catalog(self.data) as db, db:pause_state.clear(db, 'jobs')
        # Negative controls: what the relocation records do not prove stays held, with the same reason, nothing removed.
        root = next(i for i, row in enumerate(honest['recovery_identity']) if _key(row[0]) == _key(str(self.old_root)))
        forged = json.loads(json.dumps(honest));forged['recovery_identity'][root][1:] = self.elsewhere[-2][1:]
        self.set_intent(id, forged)
        self.sweep(worker)
        self.assertEqual(tuple(self.row(id)), ('needs_attention', REFUSED), 'forged ancestry');self.assertTrue(self.originals_kept())
        self.set_intent(id, honest)
        native.close()  # the recovery folder replaced while the app is closed: same name, same bytes, another folder
        (self.data / 'source-recovery').rename(self.data / 'moved-aside')
        shutil.copytree(self.data / 'moved-aside', self.data / 'source-recovery')
        self.admit(*runtime);worker = self.worker(self.data)
        self.sweep(worker)
        self.assertEqual(tuple(self.row(id)), ('needs_attention', REFUSED), 'replaced recovery folder');self.assertTrue(self.originals_kept())
        native.close()
        shutil.rmtree(self.data / 'source-recovery');(self.data / 'moved-aside').rename(self.data / 'source-recovery')
        self.admit(*runtime);worker = self.worker(self.data)
        # A cleanup whose restore began is never run again by the sweep (it would remove originals Sergei asked back).
        with self.catalog(self.data) as db, db:
            db.execute("UPDATE cleanup_members SET restore_intent=? WHERE cleanup_id=? AND path=?",
                       (json.dumps({'identity': [1, 0, 1]}), id, self.sources[0]['path']))
        self.sweep(worker)
        self.assertEqual(tuple(self.row(id)), ('needs_attention', REFUSED), 'restore begun');self.assertTrue(self.originals_kept())
        with self.catalog(self.data) as db, db:
            db.execute("UPDATE cleanup_members SET restore_intent='' WHERE cleanup_id=?", (id,))
        # The honest held row: the next admitted Start checks it again and the relocation-aware check lets it finish.
        self.sweep(worker)
        self.assertEqual(tuple(self.row(id)), ('completed', ''))
        self.assertFalse(any(Path(source['path']).exists() for source in self.sources))
        self.assertEqual(self.members(self.data, id), ['removed'] * len(self.sources))
        self.assertTrue(all((self.data / 'source-recovery' / id / ('%05d.mp3' % index)).is_file() for index in range(len(self.sources))))

    def intent(self, id):
        with self.catalog(self.data) as db:
            return db.execute('SELECT intent FROM source_cleanup WHERE id=?', (id,)).fetchone()[0]

    def set_intent(self, id, intent):
        with self.catalog(self.data) as db, db:
            db.execute('UPDATE source_cleanup SET intent=? WHERE id=?', (json.dumps(intent, ensure_ascii=False, sort_keys=True, separators=(',', ':')), id))


def setUpModule():
    global _owner
    from scratch_area import module_disposition_owner
    _owner = module_disposition_owner()  # the originals' removal needs one when this module runs alone (Senua 0.30.0 M1)


def tearDownModule():
    _owner.close()


if __name__ == '__main__':
    unittest.main()
