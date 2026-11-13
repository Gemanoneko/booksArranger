"""Native-held main-installer provenance stays outside the app archive."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import re
import struct
import zlib


@unittest.skipUnless(os.name=='nt','Native build provenance')
class CurrentPackageProducerTests(unittest.TestCase):
    def test_nsis_app_archive_is_selected_only_from_one_valid_raw_data_block(self):
        import sys
        scripts=Path(__file__).resolve().parents[1]/'scripts'
        sys.path.insert(0,str(scripts))
        try:
            from build_phase import NSIS_SIGNATURE,SEVEN_SIGNATURE,nsis_app_archive
        finally:
            sys.path.remove(str(scripts))

        class HeldBytes:
            def __init__(self,data):self.data=data
            def read_at(self,offset,size):return self.data[offset:offset+size]

        def raw(data):return struct.pack('<I',len(data))+data

        def setup(*blocks):
            stub=b'MZ'+bytes(1022)
            data=raw(b'hdr')+b''.join(blocks)
            header=struct.pack('<I',0)+NSIS_SIGNATURE+struct.pack('<II',3,28+len(data)+4)
            installer=stub+header+data
            return installer+struct.pack('<I',zlib.crc32(installer[512:]))

        packed=b'packed bytes'
        next_header=b'next header'
        start=struct.pack('<QQI',len(packed),len(next_header),zlib.crc32(next_header))
        archive=SEVEN_SIGNATURE+b'\0\4'+struct.pack('<I',zlib.crc32(start))+start+packed+next_header
        prefix=raw(bytes(9*1024*1024))
        installer=setup(prefix,raw(archive),raw(b'NSIS tail'))
        self.assertEqual(nsis_app_archive(HeldBytes(installer),len(installer)),
                         (1024+28+7+len(prefix)+4,len(archive)))
        for label,damaged,pattern in (
            ('duplicate',setup(raw(archive),raw(archive)),'Multiple raw'),
            ('nested',setup(raw(b'prefix'+archive)),'Expected one raw'),
            ('compressed',setup(struct.pack('<I',0x80000000|len(archive))+archive),'Expected one raw'),
            ('truncated',installer[:-1],'installer framing'),
            ('partial length',setup(raw(archive),b'\x04'),'Truncated NSIS block length'),
            ('out-of-frame size',setup(struct.pack('<I',len(archive)+1)+archive),'Invalid NSIS block extent'),
            ('archive trailer',setup(raw(archive+b'x')),'header or extent'),
            ('bad start CRC',setup(raw(archive[:8]+bytes(4)+archive[12:])),'header or extent'),
            ('bad next CRC',setup(raw(archive[:-1]+b'x')),'next-header CRC'),
            ('bad NSIS CRC',installer[:-4]+bytes(4),'installer CRC'),
        ):
            with self.subTest(label=label),self.assertRaisesRegex(RuntimeError,pattern):
                nsis_app_archive(HeldBytes(damaged),len(damaged))

    def test_only_pinned_dead_legacy_helpers_are_excluded_from_private_template(self):
        import sys
        root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
        try:
            import build_phase
            fixture=root/'scratch/installUtil.nsh'
            raw=(fixture if fixture.is_file() else root/'node_modules/app-builder-lib/templates/nsis/include/installUtil.nsh').read_bytes()
            private=build_phase.private_install_util(raw)
            for name in (b'GetInQuotes',b'GetFileParent',b'uninstallOldVersion'):
                self.assertNotIn(b'Function '+name+b'\n',private)
            self.assertIn(b'Function handleUninstallResult',private)
            self.assertIn(b'!macro uninstallOldVersion ROOT_KEY',private,'replacement hook remains fail-closed')
            self.assertEqual(hashlib.sha256(raw).hexdigest(),build_phase.INSTALL_UTIL_SHA256)
            with self.assertRaisesRegex(RuntimeError,'template differs'):build_phase.private_install_util(raw+b'; changed')
        finally:sys.path.remove(str(root/'scripts'))

    def test_every_live_wizard_variable_has_a_declaration_in_each_build_branch(self):
        desktop=Path(__file__).resolve().parents[1]/'desktop'
        lines=(desktop/'installer.nsh').read_text('utf8').splitlines()
        for uninstaller in (False,True):
            stack=[];active=True;declared=set();used=set()
            for line in lines:
                value=line.strip()
                if re.match(r'!if',value,re.I):
                    exact=re.fullmatch(r'!(ifdef|ifndef)\s+BUILD_UNINSTALLER',value,re.I)
                    condition=(uninstaller if exact.group(1).lower()=='ifdef' else not uninstaller) if exact else None
                    stack.append((active,condition));active=active and condition is not False;continue
                if re.match(r'!else\b',value,re.I):
                    parent,condition=stack[-1];active=parent and condition is not True;continue
                if re.match(r'!endif\b',value,re.I):active=stack.pop()[0];continue
                if not active or value.startswith(';'):continue
                match=re.fullmatch(r'Var\s+(Books\w+)',value)
                if match:declared.add(match[1]);continue
                used.update(re.findall(r'\$(Books\w+)\b',line))
            self.assertFalse(stack)
            if not uninstaller:
                used.update(re.findall(r'\$(Books\w+)\b',(desktop/'installer-safe-upgrade.nsh').read_text('utf8')))
            self.assertEqual(used-declared,set(),('missing declarations',uninstaller,used-declared))
            self.assertEqual(declared-used,set(),('unused declarations',uninstaller,declared-used))

    def test_installer_only_helper_is_excluded_from_uninstaller(self):
        text=(Path(__file__).resolve().parents[1]/'desktop/installer.nsh').read_text('utf8')
        self.assertNotIn('!include StrContains.nsh',text)
        self.assertNotIn('${StrContains}',text)
        function=text.split('Function BooksNormalizeDirectory\n',1)[1].split('FunctionEnd',1)[0]
        self.assertEqual(re.findall(r'^\s*Push (\$[123])$',function,re.M),['$1','$2','$3'])
        self.assertEqual(re.findall(r'^\s*Pop (\$[123])$',function,re.M),['$3','$2','$1'])

    def test_private_include_supplies_early_symbols_without_duplicate_plugins(self):
        import sys
        scripts=Path(__file__).resolve().parents[1]/'scripts';sys.path.insert(0,str(scripts))
        try:
            import build_phase
            rendered=build_phase.private_nsis_include(Path('I:/private build/nsis-generator'),
                payload=Path('I:/private build/payload'),files={'backend/helper.py':{'sha256':'a'*64}}).decode('utf8')
            self.assertNotIn('!addplugindir',rendered)
            self.assertIn('StdUtils.HashFile',rendered)
            process='!define BOOKS_LIFECYCLE_PROCESS_NAME "${PRODUCT_FILENAME}.exe"'
            self.assertLess(rendered.index(process),rendered.index('!include "'))
            self.assertNotIn('${APP_EXECUTABLE_FILENAME}',rendered)
            self.assertLess(rendered.index('!include MUI2.nsh'),rendered.index('!include "'))
            self.assertIn(r'!define /ifndef UNINSTALL_REGISTRY_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UNINSTALL_APP_KEY}"',rendered)
        finally:sys.path.remove(str(scripts))

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
