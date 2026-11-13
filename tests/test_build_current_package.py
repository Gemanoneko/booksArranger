"""Native-held main-installer provenance stays outside the app archive."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(os.name=='nt','Native build provenance')
class CurrentPackageProducerTests(unittest.TestCase):
    def test_generated_uninstaller_is_pinned_only_in_second_phase_manifest(self):
        import sys
        scripts=Path(__file__).resolve().parents[1]/'scripts'
        sys.path.insert(0,str(scripts))
        try:
            spec=importlib.util.spec_from_file_location('current_package_generator',scripts/'build-nsis-generator.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            from build_fs_guard import BuildTree
            parent=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',Path(__file__).resolve().parents[1]/'scratch'))
            parent.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='current-package-',dir=parent) as area:
                root=Path(area);(root/'operations').mkdir();(root/'outputs').mkdir()
                with BuildTree(root) as tree:
                    owned=tree.fresh(root/'operations');output=tree.fresh(root/'outputs')
                    archive=output/'win-unpacked/resources/app.asar'
                    tree.write(archive,[b'private immutable already-packed app archive'])
                    tree.write(output/'win-unpacked/Books Arranger.exe',[b'private generated executable fixture'])
                    uninstaller=output/'generated-uninstaller.exe';tree.write(uninstaller,[b'private newly compiled uninstaller fixture'])
                    icon=owned/'icons/icon.ico';tree.write(icon,[b'private verified icon fixture'])
                    before=archive.read_bytes()
                    record=module.emit_current_package(tree,{'icon':str(icon),'source_head':'a'*40},owned,output,uninstaller,'1.2.3')
                    producer=json.loads(Path(record['path']).read_text('utf8'))
                    self.assertEqual(producer['files']['Uninstall Books Arranger.exe']['sha256'],hashlib.sha256(uninstaller.read_bytes()).hexdigest())
                    self.assertEqual(producer['files']['uninstallerIcon.ico']['sha256'],hashlib.sha256(icon.read_bytes()).hexdigest())
                    self.assertEqual(archive.read_bytes(),before)
                    self.assertFalse((archive.parent/'backend/current-package.json').exists(),
                        'no late edit to normal app payload is permitted')
                    include=(owned/'lifecycle-main-provenance/current-package.nsh').read_text('utf8')
                    self.assertIn(record['sha256'],include)
                    self.assertIn('!macro BooksCurrentPackagePayload ROOT',include)
                    self.assertIn('!macro BooksCurrentPackageVerify ROOT',include)
                    with self.assertRaises(RuntimeError):
                        module.emit_current_package(tree,{'icon':str(icon),'source_head':'untrusted'},owned,output,uninstaller,'1.2.3')
        finally:sys.path.remove(str(scripts))


if __name__=='__main__':unittest.main()
