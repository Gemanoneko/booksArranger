"""Real native alias protection; ordinary/competing access are positive controls."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid

from native_io import DirectoryBoundary, VerifiedFile, BoundaryError, kernel
from storage_relocation_native import configure, close, facts_match
from storage_relocation import RelocationRefused


@unittest.skipUnless(os.name == 'nt', 'Windows configured temporary work')
class ConfiguredTempTests(unittest.TestCase):
    def test_selected_temp_never_searches_fallback_after_path_loss(self):
        import storage_relocation_native as native
        parent=Path(os.environ.get('BOOKS_RELOCATION_FIXTURE_TARGET',Path(__file__).resolve().parents[1]/'scratch'))
        with tempfile.TemporaryDirectory(prefix='selected-temp-',dir=parent) as owned:
            path=Path(owned)/'work';path.mkdir()
            original=tempfile.tempdir
            try:
                native.configure_work_temp({'BOOKS_WORK_TEMP':str(path),'TEMP':str(path),'TMP':str(path)})
                self.assertEqual(Path(tempfile.gettempdir()),path)
                with tempfile.TemporaryFile() as proof:
                    proof.write(b'configured I temporary work')
                with self.assertRaises(PermissionError):path.rename(path.with_name('away'))
                # The normal retained boundary already prevents a pathname
                # outage. Close this TEST handle only to simulate drive loss;
                # tempfile must still raise rather than search C or cwd.
                native._temp_lease['boundary'].__exit__(None,None,None)
                path.rename(path.with_name('away'))
                with self.assertRaises(FileNotFoundError):tempfile.TemporaryFile()
                self.assertEqual(Path(tempfile.gettempdir()),path)
                path.with_name('away').rename(path)
            finally:native.close()
            self.assertEqual(tempfile.tempdir,original)


@unittest.skipUnless(os.name == 'nt', 'Windows native handle contract')
class NativeRelocationTests(unittest.TestCase):
    def setUp(self):
        default = Path(__file__).resolve().parents[1] / 'scratch'
        default.mkdir(exist_ok=True)
        source_parent = Path(os.environ.get('BOOKS_RELOCATION_FIXTURE_SOURCE', default))
        target_parent = Path(os.environ.get('BOOKS_RELOCATION_FIXTURE_TARGET', default))
        self.left = tempfile.TemporaryDirectory(prefix='relocation-source-', dir=source_parent)
        self.right = tempfile.TemporaryDirectory(prefix='relocation-target-', dir=target_parent)
        self.source = Path(self.left.name) / 'old'
        self.target = Path(self.right.name) / 'new'
        (self.source / 'data').mkdir(parents=True)
        (self.source / 'data' / 'évidence.bin').write_bytes(b'unchanged independently copied bytes')
        self.source_facts = {}
        for relative in ('', 'data'):
            with DirectoryBoundary(self.source.anchor, self.source / relative) as boundary:
                self.source_facts[relative] = list(boundary.identities[-1][1:])
        with VerifiedFile(self.source / 'data' / 'évidence.bin') as held:
            self.old = held.facts(); self.sha = held.sha256()
        shutil.copytree(self.source, self.target)
        target_dirs = {}
        for relative in ('', 'data'):
            with DirectoryBoundary(self.target.anchor, self.target / relative) as boundary:
                target_dirs[relative] = list(boundary.identities[-1][1:])
        with VerifiedFile(self.target / 'data' / 'évidence.bin') as held:
            self.new = held.facts()
            self.assertEqual(held.sha256(), self.sha)
        self.assertNotEqual(self.old['identity'], self.new['identity'])
        self.manifest = {'schema': 'books-storage-relocation-v1', 'generation': str(uuid.uuid4()),
            'catalog_id': str(uuid.uuid4()), 'source_root': str(self.source),
            'target_root': str(self.target), 'scopes': ['data'],
            'source_snapshot_sha256': 'a' * 64,
            'directories': [{'relative': r, 'source_identity': self.source_facts[r],
                             'target_identity': target_dirs[r]} for r in ('', 'data')],
            'files': [{'relative': r'data\évidence.bin', 'source_facts': self.old,
                       'target_facts': self.new, 'sha256': self.sha,
                       'receipt_classes': ['working-file']}]}
        self.file = Path(self.right.name) / 'manifest.json'
        self.raw = json.dumps(self.manifest, ensure_ascii=False).encode('utf8')
        self.file.write_bytes(self.raw)
        self.original = self.source.with_name('original-preserved')
        self.source.rename(self.original)
        result = subprocess.run([str(Path(os.environ['SystemRoot']) / 'System32/cmd.exe'),
            '/d', '/c', 'mklink', '/J', str(self.source), str(self.target)],
            capture_output=True, creationflags=0x08000000, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self):
        close()
        self.left.cleanup()
        self.right.cleanup()

    def select(self):
        return configure(self.file, hashlib.sha256(self.raw).hexdigest())

    def write_alias(self):
        # Real access positive control: opening WRITE on this mount-point would
        # permit FSCTL_SET_REPARSE_POINT; during a lease it MUST be sharing-denied.
        ctypes.set_last_error(0)
        handle = kernel.CreateFileW(str(self.source), 0x40000000, 7, None, 3,
                                    0x02000000 | 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            return None, ctypes.get_last_error()
        kernel.CloseHandle(handle)
        return True, 0

    def test_exact_alias_keeps_actual_target_identity_and_denies_retarget_delete(self):
        self.assertEqual(self.write_alias(), (True, 0), 'positive control before retained lease')
        with self.assertRaises(BoundaryError):
            with DirectoryBoundary(self.source.anchor, self.source / 'data'):pass
        selected = self.select()
        with DirectoryBoundary(self.source.anchor, self.source / 'data') as boundary:
            self.assertEqual(self.write_alias(), (None, 32), 'writer needed to retarget must be denied')
            kernel.RemoveDirectoryW.argtypes = [ctypes.c_wchar_p]
            kernel.RemoveDirectoryW.restype = ctypes.c_int
            ctypes.set_last_error(0)
            self.assertFalse(kernel.RemoveDirectoryW(str(self.source)))
            self.assertIn(ctypes.get_last_error(), (5, 32))
            with VerifiedFile(self.source / 'data' / 'évidence.bin') as held:
                self.assertEqual(held.facts(), self.new)
                self.assertEqual(held.sha256(), self.sha)
            alias = next(row for row in boundary.identities if row[0] == str(self.source))
            self.assertEqual(tuple(alias[1:]), selected.manifest.directories[''].target)
            boundary.revalidate()
        self.assertEqual(self.write_alias(), (True, 0), 'positive control after retained lease')
        self.source.rmdir()
        self.assertFalse(self.source.exists(), 'real junction delete succeeds only after lease closes')

    def test_selected_alias_does_not_authorize_sibling_paths_or_historical_facts_without_catalog(self):
        self.select()
        with self.assertRaises(BoundaryError):
            with DirectoryBoundary(self.source.anchor, self.source / 'other-project'):pass
        with self.assertRaises(RelocationRefused):
            facts_match(self.source / 'data' / 'évidence.bin', self.new, self.old,
                        receipt_class='working-file')

    def test_wrong_physical_target_and_missing_manifest_refuse_without_fallback(self):
        wrong = dict(self.manifest, target_root=str(Path(self.right.name) / 'missing'))
        raw = json.dumps(wrong).encode(); self.file.write_bytes(raw)
        with self.assertRaises((BoundaryError, RelocationRefused)):
            configure(self.file, hashlib.sha256(raw).hexdigest())
        with self.assertRaises(BoundaryError):
            configure(Path(self.right.name) / 'not-present.json', hashlib.sha256(raw).hexdigest())


if __name__ == '__main__':unittest.main()
