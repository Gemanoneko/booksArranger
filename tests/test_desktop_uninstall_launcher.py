"""The registered uninstall route uses exact package bytes and selected temp."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import desktop_uninstall_launcher as launcher
import storage_lifecycle as life
import storage_relocation_native as relocation
from storage_relocation import RelocationRefused
from native_io import DirectoryBoundary


@unittest.skipUnless(os.name == 'nt', 'Windows native package admission')
class UninstallLauncherTests(unittest.TestCase):
    def setUp(self):
        root=Path(os.environ['BOOKS_QA_FIXTURE_ROOT'])
        root.mkdir(parents=True,exist_ok=True)
        self.folder=Path(tempfile.mkdtemp(prefix='uninstall-launch-',dir=root))
        self.app=self.folder/'Application';self.app.mkdir()
        for name,content in [('Books Arranger.exe',b'private application, never executed'),
                             ('Uninstall Books Arranger.exe',b'private new uninstaller, never executed')]:
            (self.app/name).write_bytes(content)
        self.registrations=patch.object(life,'registered_bootstraps',return_value=[])
        self.registrations.start();self.addCleanup(self.registrations.stop)
        self.configurations=patch.object(life,'known_configurations',return_value=[])
        self.configurations.start();self.addCleanup(self.configurations.stop)
        plan=life.selection_plan('new',self.folder/'Data',application_dir=self.app,profile_dir=self.folder/'Profile')
        committed=life.commit_selection(plan,hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            process_name='Books No Such Uninstall Launcher Fixture.exe')
        self.bootstrap=Path(committed['bootstrap']);self.value=json.loads(self.bootstrap.read_bytes())
        files={p.name:dict(size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
               for p in self.app.iterdir()}
        producer=dict(schema='books-trusted-current-package-v1',files=files)
        original=life._json
        def trusted(path,*args):
            if Path(path).name=='current-package.json':return producer,{},'a'*64
            return original(path,*args)
        with patch.object(life,'_json',side_effect=trusted):
            self.value['package_ownership']=life.capture_current_package(str(self.app),self.value['installation_id'])
        maintenance=self.folder/'MaintenanceTemp';maintenance.mkdir(exist_ok=True)
        with DirectoryBoundary(maintenance.anchor,maintenance) as boundary:
            self.value.update(maintenance_temp_dir=str(maintenance),
                maintenance_temp_identity=list(boundary.identities[-1][1:]))
        self.bootstrap.write_bytes(json.dumps(self.value).encode())
        self.temp=Path(self.value['maintenance_temp_dir'])
        self.environment=patch.dict(os.environ,BOOKS_WORK_TEMP=str(self.temp),TEMP=str(self.temp),TMP=str(self.temp))
        self.environment.start();self.addCleanup(self.environment.stop)
        self.previous=relocation._temp_lease;relocation._temp_lease=None
        self.addCleanup(self.release_temp)

    def release_temp(self):
        current=relocation._temp_lease
        if current is not None:
            current['boundary'].__exit__(None,None,None)
            tempfile.tempdir=current['previous']
        relocation._temp_lease=self.previous

    def run_launcher(self,spawn):
        return launcher.launch_uninstaller(str(self.bootstrap),hashlib.sha256(self.bootstrap.read_bytes()).hexdigest(),
            str(self.app),parent_pid=os.getppid(),_spawn=spawn)

    def test_selected_environment_and_executable_remain_held_through_process_creation(self):
        called=[]
        def spawn(arguments,**options):
            called.append((arguments,options))
            with self.assertRaises(OSError):(self.app/'Uninstall Books Arranger.exe').rename(self.app/'moved.exe')
            with self.assertRaises(OSError):(self.app/'Uninstall Books Arranger.exe').write_bytes(b'replaced')
            return types.SimpleNamespace(pid=os.getpid())
        result=self.run_launcher(spawn)
        self.assertTrue(result['started']);self.assertEqual(len(called),1)
        arguments,options=called[0]
        self.assertEqual(arguments[0],str(self.app/'Uninstall Books Arranger.exe'))
        self.assertEqual(arguments[1],'/BOOKSLAUNCHERPID='+str(os.getppid()))
        self.assertEqual({options['env'][key] for key in ('TEMP','TMP','BOOKS_WORK_TEMP')},{str(self.temp)})
        self.assertEqual(result['configured_temp'],str(self.temp))

    def test_changed_uninstaller_never_starts(self):
        executable=self.app/'Uninstall Books Arranger.exe';executable.write_bytes(b'changed new uninstaller')
        with self.assertRaisesRegex(RelocationRefused,'identity/content changed'):
            self.run_launcher(lambda *args,**kwargs:self.fail('changed executable launched'))
        self.assertEqual(executable.read_bytes(),b'changed new uninstaller')

    def test_inherited_temporary_fallback_is_refused(self):
        with patch.dict(os.environ,TEMP=str(self.folder)):
            with self.assertRaisesRegex(RelocationRefused,'temporary work environment'):
                self.run_launcher(lambda *args,**kwargs:self.fail('wrong temporary environment launched'))
        self.assertTrue(self.bootstrap.exists())

    def test_other_application_cannot_borrow_the_package(self):
        other=self.folder/'Other';other.mkdir()
        with self.assertRaisesRegex(RelocationRefused,'another installation'):
            launcher.launch_uninstaller(str(self.bootstrap),hashlib.sha256(self.bootstrap.read_bytes()).hexdigest(),
                str(other),parent_pid=os.getppid(),_spawn=lambda *args,**kwargs:self.fail('foreign package launched'))

    def test_unsafe_legacy_fingerprint_is_never_executed(self):
        current=hashlib.sha256((self.app/'Uninstall Books Arranger.exe').read_bytes()).hexdigest()
        with patch.object(launcher,'LEGACY_027_UNINSTALLER',current):
            with self.assertRaisesRegex(RelocationRefused,'unsafe legacy uninstaller'):
                self.run_launcher(lambda *args,**kwargs:self.fail('unsafe legacy launched'))

    def test_replaced_maintenance_directory_cannot_borrow_the_path(self):
        original=self.temp.with_name('original-maintenance');self.temp.rename(original);self.temp.mkdir()
        with self.assertRaisesRegex(RelocationRefused,'maintenance native identity changed'):
            self.run_launcher(lambda *args,**kwargs:self.fail('replacement maintenance root used'))
        self.assertTrue(original.exists());self.assertTrue(self.temp.exists())


if __name__=='__main__':unittest.main()
