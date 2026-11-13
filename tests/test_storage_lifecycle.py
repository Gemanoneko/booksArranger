"""Private Win32 lifecycle fixtures, no installed app or personal data mutation."""
import contextlib
import configparser
import hashlib
import json
import os
import shutil
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

import storage_lifecycle as lifecycle
from native_io import VerifiedFile, DirectoryBoundary


@unittest.skipUnless(os.name == 'nt', 'Native lifecycle safety requires Windows')
class LifecycleTests(unittest.TestCase):
    def setUp(self):
        base = Path(os.environ.get('BOOKS_LIFECYCLE_TEST_ROOT') or os.environ.get('BOOKS_QA_FIXTURE_ROOT') or
                    Path(__file__).resolve().parents[1]/'scratch'/'lifecycle-tests')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='case-', dir=base)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bootstraps=[]
        environment=patch.dict(os.environ,{'APPDATA':str(self.base/'Roaming'),'LOCALAPPDATA':str(self.base/'Local')})
        environment.start();self.addCleanup(environment.stop)
        registrations=patch.object(lifecycle,'registered_bootstraps',side_effect=lambda:self.bootstraps)
        registrations.start();self.addCleanup(registrations.stop)

    def catalog(self, name='catalog'):
        folder = self.base / name; folder.mkdir()
        path = folder / 'inventory.sqlite3'
        with contextlib.closing(sqlite3.connect(path)) as db, db:
            db.executescript('CREATE TABLE jobs(root TEXT);CREATE TABLE queue(path TEXT);'
                'CREATE TABLE files(root TEXT,path TEXT,size INTEGER,modified INTEGER,kind TEXT);')
        return path

    def manifest(self, root, files, role='profile'):
        # Positive authority is produced by the real installation commit, never
        # an arbitrary hand-authored JSON list with matching file hashes.
        app=self.base/'Application'
        if role=='database':
            mode='existing';location=root/'inventory.sqlite3';profile=self.base/'Profile'
        else:
            mode='new';location=self.base/'Data';profile=root
            original=self.base/'fixture-source-original';root.rename(original)
        plan=lifecycle.selection_plan(mode,str(location),application_dir=str(app),profile_dir=str(profile))
        digest=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        committed=lifecycle.commit_selection(plan,digest,process_name='Books Lifecycle No Such Fixture.exe')
        bootstrap=Path(committed['bootstrap']);self.bootstraps.append(str(bootstrap))
        if role!='database':shutil.copytree(original,root,dirs_exist_ok=True)
        value=json.loads(bootstrap.read_text());owner=Path(value['ownership_manifest'])
        result=lifecycle.refresh_ownership(owner,hashlib.sha256(owner.read_bytes()).hexdigest(),
            output_path=self.base/'ownership-review.json',bootstrap_path=str(bootstrap))
        return Path(result['ownership_path']),result['ownership_sha256']

    def used_catalog(self,*,pending=False):
        """Normally generated native ledger plus typed recovery/index state."""
        from runtime_disposition_owners import registered_catalog,admit_catalog
        path=self.catalog();root=path.parent;lock=Path(str(path)+'.lock');lock.write_bytes(b'')
        discarded=root/'retired.tmp';discarded.write_bytes(b'ordinary retired runtime work')
        with VerifiedFile(lock,writable=True) as owner,registered_catalog(path,{},owner):
            admit_catalog(path)
            with VerifiedFile(discarded,delete=True) as held:
                if pending:
                    from runtime_disposition_owners import context_for
                    from runtime_file_disposition import prepare_disposition
                    guard=prepare_disposition(held,context_for(discarded));guard.abort('fixture retained before native success')
                else:held.dispose()
        identifier=str(uuid.uuid4());original=str(self.base/'Library'/'old.m4b')
        recovery=root/'replacement-recovery'/identifier/(hashlib.sha256(original.encode()).hexdigest()+'.m4b')
        recovery.parent.mkdir(parents=True);recovery.write_bytes(b'original replacement recovery audio')
        with VerifiedFile(recovery) as held:
            details=dict(path=str(recovery),facts=held.facts(),size=held.facts()['size'],sha256=held.sha256())
        with contextlib.closing(sqlite3.connect(path)) as db,db:
            db.execute('CREATE TABLE audiobook_replacement_retirements(replacement_id TEXT,original_path TEXT,recovery_json TEXT,state TEXT)')
            db.execute('INSERT INTO audiobook_replacement_retirements VALUES (?,?,?,?)',(identifier,original,json.dumps(details),'retained'))
        index=root/'openlibrary-index';index.mkdir();leaf=index/'active.sqlite3';journal=index/'active.sqlite3-journal'
        leaf.write_bytes(b'typed private OpenLibrary index');journal.write_bytes(b'typed private index journal')
        with VerifiedFile(leaf) as a,VerifiedFile(journal) as b:
            (index/'active.sqlite3.owner.json').write_text(json.dumps(dict(binding='openlibrary-active-v1',identities=[a.facts()['identity'],b.facts()['identity']])))
        return path

    def test_used_catalog_refresh_cleanup_accepts_closed_ledger_recovery_and_typed_index(self):
        path=self.used_catalog();root=path.parent
        # A genuine uncheckpointed source tuple must stay byte/fact identical.
        writer=('import os,sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute("PRAGMA journal_mode=WAL");'
                'c.execute("PRAGMA wal_autocheckpoint=0");c.execute("INSERT INTO jobs(root) VALUES (?)",(sys.argv[2],));c.commit();os._exit(0)')
        result=subprocess.run([sys.executable,'-I','-B','-c',writer,str(path),str(self.base/'Library')],capture_output=True,timeout=15,creationflags=0x08000000)
        self.assertEqual(result.returncode,0,result.stderr)
        def tuple_facts():
            result={}
            for suffix in ('','-wal','-shm'):
                with VerifiedFile(str(path)+suffix) as held:result[suffix]=(held.facts(),held.sha256())
            return result
        before=tuple_facts();graph,markers,dirs=lifecycle._catalog_ownership(root)
        self.assertEqual(tuple_facts(),before)
        self.assertTrue(any('/file-disposition-ledger/' in p.replace('\\','/') for p in graph))
        self.assertTrue(any('/replacement-recovery/' in p.replace('\\','/') for p in graph))
        self.assertIn(str(root/'openlibrary-index/active.sqlite3'),markers)
        manifest,digest=self.manifest(root,[],role='database')
        plan=lifecycle.plan_cleanup(manifest,digest,selected_roots=[str(root)],bootstrap_paths=self.bootstraps)
        self.assertTrue(any('file-disposition-ledger' in row['path'] for row in plan['targets'][0]['files']))
        sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        result=lifecycle.execute_cleanup(plan,sha)
        self.assertTrue(result['ok'],result);self.assertFalse(root.exists())

    def test_used_catalog_refresh_unknown_index_member_remains_held(self):
        path=self.used_catalog();unknown=path.parent/'openlibrary-index/personal.sqlite3';unknown.write_bytes(b'never adopt by extension')
        manifest,digest=self.manifest(path.parent,[],role='database')
        with self.assertRaises(lifecycle.LifecycleRefused):
            lifecycle.plan_cleanup(manifest,digest,selected_roots=[str(path.parent)],bootstrap_paths=self.bootstraps)
        self.assertEqual(unknown.read_bytes(),b'never adopt by extension')

    def test_used_catalog_pending_disposition_stays_held(self):
        path=self.used_catalog(pending=True)
        with self.assertRaises(ValueError):lifecycle._catalog_ownership(path.parent)
        self.assertTrue((path.parent/'retired.tmp').exists());self.assertTrue(path.exists())

    def test_used_catalog_orphan_disposition_record_stays_held(self):
        path=self.used_catalog();ledger=path.parent/'file-disposition-ledger'
        next(ledger.glob('*.intent.json')).unlink()
        with self.assertRaises(lifecycle.LifecycleRefused):lifecycle._catalog_ownership(path.parent)
        self.assertTrue(path.exists())

    def test_used_catalog_retained_disposition_requires_typed_target_ownership(self):
        from runtime_disposition_owners import registered_catalog,admit_catalog
        path=self.used_catalog(pending=True);target=path.parent/'retired.tmp'
        # Supported owner recovery positively records restored retained bytes.
        with VerifiedFile(str(path)+'.lock',writable=True) as owner,registered_catalog(path,{},owner):admit_catalog(path)
        self.assertTrue(list((path.parent/'file-disposition-ledger').glob('*.retained.json')))
        with VerifiedFile(target) as held:sha=held.sha256();size=held.facts()['size']
        with contextlib.closing(sqlite3.connect(path)) as db,db:
            db.execute('CREATE TABLE owned_artifacts(path TEXT,sha256 TEXT,size INTEGER,kind TEXT)')
            db.execute('INSERT INTO owned_artifacts VALUES (?,?,?,?)',(str(target),sha,size,'recovery'))
        graph,_,_=lifecycle._catalog_ownership(path.parent)
        self.assertEqual(graph[str(target)],(sha,size));self.assertTrue(target.exists())

    def test_existing_recognition_is_read_only_and_profile_association_is_explicit(self):
        path = self.catalog(); before = path.read_bytes(); profile = self.base / 'profile'; profile.mkdir()
        settings = profile / 'desktop-settings.json'; settings.write_text(json.dumps({'dataDir':str(path.parent)}))
        result = lifecycle.inspect_existing(path, config_paths=[settings])
        self.assertEqual(result['state'], 'available'); self.assertTrue(result['profile_confirmed'])
        self.assertEqual(result['profile_dir'], str(profile)); self.assertEqual(path.read_bytes(), before)
        self.assertFalse(Path(str(path)+'.lock').exists())
        self.assertFalse(Path(str(path)+'-journal').exists())

    def test_missing_and_invalid_candidates_do_not_become_empty_new_catalogs(self):
        missing = self.base / 'missing' / 'inventory.sqlite3'
        self.assertEqual(lifecycle.inspect_existing(missing)['state'], 'location_unavailable')
        invalid = self.base / 'inventory.sqlite3'; invalid.write_bytes(b'not a database')
        self.assertEqual(lifecycle.inspect_existing(invalid)['state'], 'unsupported_database')
        self.assertFalse(missing.parent.exists())

    def test_new_selection_validates_without_creating_and_refuses_nonempty(self):
        new = self.base / 'future'
        result = lifecycle.selection_plan('new', new, application_dir=self.base/'Application', profile_dir=self.base/'Profile')
        self.assertEqual(result['selection']['mode'], 'new'); self.assertFalse(new.exists())
        new.mkdir(); (new/'unrelated').write_text('keep')
        with self.assertRaisesRegex(lifecycle.LifecycleRefused, 'new_folder_not_empty'):
            lifecycle.inspect_new(new)

    def test_busy_native_catalog_ownership_is_reported(self):
        path = self.catalog(); lock = Path(str(path)+'.lock'); lock.write_bytes(b'owner')
        with VerifiedFile(lock, writable=True):
            self.assertEqual(lifecycle.inspect_existing(path)['state'], 'in_use')
        self.assertEqual(lifecycle.inspect_existing(path)['state'], 'available')

    def test_frozen_wal_queries_preserve_the_complete_original_tuple(self):
        from storage_lifecycle_snapshot import frozen_connection
        path=self.catalog();lock=Path(str(path)+'.lock');lock.write_bytes(b'')
        writer=('import os,sqlite3,sys;c=sqlite3.connect(sys.argv[1]);'
                'c.execute("PRAGMA journal_mode=WAL");c.execute("PRAGMA wal_autocheckpoint=0");'
                'c.execute("INSERT INTO jobs(root) VALUES (?)",(sys.argv[2],));c.commit();os._exit(0)')
        result=subprocess.run([sys.executable,'-I','-B','-c',writer,str(path),str(self.base/'Library')],
            capture_output=True,timeout=15,creationflags=0x08000000)
        self.assertEqual(result.returncode,0,result.stderr)
        tuple_paths=[Path(str(path)+suffix) for suffix in ('','-wal','-shm')]
        self.assertTrue(all(p.exists() for p in tuple_paths))
        def original():
            result={}
            for member in tuple_paths:
                with VerifiedFile(member) as held:result[str(member)]=(held.facts(),held.sha256())
            return result
        before=original()
        for _ in range(2):
            with frozen_connection(path) as db:
                self.assertEqual(db.execute('SELECT root FROM jobs').fetchall(),[(str(self.base/'Library'),)])
        self.assertEqual(original(),before)
        temporary=Path(os.environ.get('BOOKS_WORK_TEMP') or os.environ['TEMP'])
        self.assertEqual(list(temporary.glob('books-sqlite-*')),[])

    def test_frozen_snapshot_refuses_live_native_writer_then_accepts_closed_source(self):
        from storage_lifecycle_snapshot import frozen_connection
        from native_io import BoundaryError
        path=self.catalog();Path(str(path)+'.lock').write_bytes(b'')
        before=path.read_bytes()
        with VerifiedFile(path,writable=True):
            with self.assertRaises(BoundaryError):
                with frozen_connection(path):self.fail('live writer was admitted')
        with frozen_connection(path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],0)
        self.assertEqual(path.read_bytes(),before)

    def test_frozen_snapshot_preserves_and_refuses_a_new_tuple_member(self):
        from storage_lifecycle_snapshot import frozen_connection
        path=self.catalog();Path(str(path)+'.lock').write_bytes(b'')
        journal=Path(str(path)+'-journal');write=lifecycle._write_new_chunks;inserted=False
        def arrive(target,chunks):
            nonlocal inserted
            result=write(target,chunks)
            if not inserted:
                inserted=True;journal.write_bytes(b'foreign arrival retained')
            return result
        with patch.object(lifecycle,'_write_new_chunks',side_effect=arrive):
            with self.assertRaisesRegex((lifecycle.LifecycleRefused,RuntimeError),'snapshot_source_changed'):
                with frozen_connection(path):self.fail('changed tuple was admitted')
        self.assertEqual(journal.read_bytes(),b'foreign arrival retained')

    def test_keep_and_plan_do_not_remove_data_but_exact_execution_does(self):
        root = self.base/'private'; root.mkdir(); file = root/'Local State'; file.write_bytes(b'owned history')
        manifest, digest = self.manifest(root, [file]); original = file.read_bytes()
        with patch.object(lifecycle, 'registered_bootstraps', side_effect=lambda:self.bootstraps):
            plan = lifecycle.plan_cleanup(manifest, digest, selected_roots=[root])
            self.assertEqual(file.read_bytes(), original)
            raw = json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()
            result = lifecycle.execute_cleanup(plan, hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['removed_files'], 1); self.assertEqual(result['removed_bytes'], len(original))
        self.assertFalse(file.exists()); self.assertFalse(root.exists()); self.assertTrue(manifest.exists())

    def test_unknown_sibling_and_changed_file_refuse_before_any_removal(self):
        root = self.base/'private'; root.mkdir(); file = root/'Preferences'; file.write_bytes(b'owned')
        manifest, digest = self.manifest(root, [file]); sibling=root/'unknown'; sibling.write_bytes(b'keep')
        with patch.object(lifecycle, 'registered_bootstraps', side_effect=lambda:self.bootstraps):
            with self.assertRaisesRegex(lifecycle.LifecycleRefused, 'ownership_not_confirmed'):
                lifecycle.plan_cleanup(manifest, digest, selected_roots=[root])
            sibling.unlink(); plan=lifecycle.plan_cleanup(manifest,digest,selected_roots=[root]); file.write_bytes(b'changed')
            raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
            with self.assertRaisesRegex(lifecycle.LifecycleRefused, 'changed_since_review'):
                lifecycle.execute_cleanup(plan,hashlib.sha256(raw).hexdigest())
        self.assertTrue(file.exists())

    def test_protected_physical_alias_never_grants_old_location_cleanup(self):
        root=self.base/'private';root.mkdir();file=root/'Preferences';file.write_bytes(b'keep')
        manifest,digest=self.manifest(root,[file])
        with patch.object(lifecycle,'registered_bootstraps',side_effect=lambda:self.bootstraps):
            with self.assertRaises(lifecycle.LifecycleRefused):
                lifecycle.plan_cleanup(manifest,digest,selected_roots=[root],protected_paths=[root])
        self.assertTrue(file.exists())

    def test_real_junction_is_deduplicated_for_discovery_and_protected_for_cleanup(self):
        database=self.catalog('retained');alias=self.base/'old-alias'
        subprocess.run([os.environ.get('SystemRoot',r'C:\Windows')+r'\System32\cmd.exe','/d','/c','mklink','/J',str(alias),str(database.parent)],
                       check=True,capture_output=True,timeout=10,creationflags=0x08000000)
        self.addCleanup(lambda:alias.rmdir() if alias.exists() else None)
        with patch.dict(os.environ,{'APPDATA':str(self.base/'missing-roaming'),'LOCALAPPDATA':str(self.base/'missing-local')}):
            rows=lifecycle.known_candidates(extra_candidates=[str(database),str(alias/'inventory.sqlite3')])['candidates']
        available=[r for r in rows if r['state']=='available']
        self.assertEqual(len(available),1);self.assertEqual(len(available[0]['aliases']),2)
        manifest,digest=self.manifest(database.parent,[database],role='database')
        value=json.loads(manifest.read_text());value['roots'][0]['path']=str(alias)
        raw=json.dumps(value).encode();manifest.write_bytes(raw);digest=hashlib.sha256(raw).hexdigest()
        with patch.object(lifecycle,'registered_bootstraps',side_effect=lambda:self.bootstraps):
            with self.assertRaises(lifecycle.LifecycleRefused):
                lifecycle.plan_cleanup(manifest,digest,selected_roots=[alias],protected_paths=[database.parent])
        self.assertTrue(database.exists())

    def test_locked_last_file_blocks_all_dispositions(self):
        root=self.base/'state';root.mkdir();first=root/'DIPS';last=root/'DIPS-wal'
        script=self.base/'create-real-wal.py';script.write_text('import sqlite3,sys,os\nd=sqlite3.connect(sys.argv[1]);d.execute("PRAGMA journal_mode=WAL");d.execute("PRAGMA wal_autocheckpoint=0");d.execute("CREATE TABLE cache(value)");d.execute("INSERT INTO cache VALUES(1)");d.commit();os._exit(0)\n')
        subprocess.run([sys.executable,'-I','-B',str(script),str(first)],check=True,timeout=20,creationflags=0x08000000)
        manifest,digest=self.manifest(root,[first,last])
        main_before=first.read_bytes();wal_before=last.read_bytes()
        with patch.object(lifecycle,'registered_bootstraps',side_effect=lambda:self.bootstraps):
            plan=lifecycle.plan_cleanup(manifest,digest,selected_roots=[root])
            raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
            with VerifiedFile(last,writable=True),self.assertRaises(ValueError):
                lifecycle.execute_cleanup(plan,hashlib.sha256(raw).hexdigest())
        self.assertEqual(first.read_bytes(),main_before);self.assertEqual(last.read_bytes(),wal_before)

    def test_wal_only_committed_schema_is_recognized_without_changing_main_or_wal(self):
        folder=self.base/'crash-wal';folder.mkdir();database=folder/'inventory.sqlite3'
        script=self.base/'create_wal.py';script.write_text('import sqlite3,os,sys\n'
            'd=sqlite3.connect(sys.argv[1]);d.execute("PRAGMA journal_mode=WAL");d.execute("PRAGMA wal_autocheckpoint=0");'
            'd.executescript("CREATE TABLE jobs(root TEXT);CREATE TABLE queue(path TEXT);CREATE TABLE files(root TEXT,path TEXT,size INTEGER,modified INTEGER,kind TEXT)");d.commit();os._exit(0)\n')
        subprocess.run([sys.executable,'-I','-B',str(script),str(database)],check=True,timeout=20,creationflags=0x08000000)
        wal=Path(str(database)+'-wal');self.assertTrue(wal.exists());mainbytes=database.read_bytes();walbytes=wal.read_bytes()
        result=lifecycle.inspect_existing(database)
        self.assertEqual(result['state'],'available');self.assertTrue(result['wal_present'])
        self.assertEqual(database.read_bytes(),mainbytes);self.assertEqual(wal.read_bytes(),walbytes)

    def test_new_install_commit_creates_bootstrap_but_no_false_load_success_marker(self):
        app=self.base/'installation'/'Application';profile=app.parent/'Profile';data=app.parent/'Data'
        plan=lifecycle.selection_plan('new',data,application_dir=app,profile_dir=profile)
        raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
        result=lifecycle.commit_selection(plan,hashlib.sha256(raw).hexdigest(),process_name='Books Lifecycle No Such Fixture.exe')
        bootstrap=json.loads(Path(result['bootstrap']).read_text())
        self.assertEqual(bootstrap['catalog_mode'],'new');self.assertEqual(bootstrap['data_dir'],str(data))
        self.assertTrue(data.is_dir());self.assertEqual(list(data.iterdir()),[])
        self.assertFalse((profile/'desktop-settings.json').exists())
        self.assertFalse((data/'inventory.sqlite3').exists())

    def test_ini_transport_preserves_unicode_paths_and_pins_reviewed_selection(self):
        app=self.base/'Книги'/'Application';profile=app.parent/'Profile';data=app.parent/'Data'
        request=self.base/'request.ini';response=self.base/'response.ini'
        request.write_text('[request]\naction=selection\nmode=new\nlocation='+str(data)+'\napplication_dir='+str(app)+
                           '\nprofile_dir='+str(profile)+'\n',encoding='utf-16')
        self.assertEqual(lifecycle.wizard(request,response),0)
        ini=configparser.ConfigParser(interpolation=None)
        ini.read(response,encoding='utf-16');planpath=Path(ini['result']['plan_path'])
        self.assertEqual(hashlib.sha256(planpath.read_bytes()).hexdigest(),ini['result']['plan_sha256'])
        self.assertEqual(json.loads(planpath.read_text())['selection']['data_dir'],str(data))
        self.assertFalse(data.exists())

    def test_explicit_new_catalog_switch_retains_old_bootstrap_profile_and_database(self):
        app=self.base/'installation'/'Application';profile=app.parent/'Profile';olddata=app.parent/'Data'
        first=lifecycle.selection_plan('new',olddata,application_dir=app,profile_dir=profile)
        raw=json.dumps(first,sort_keys=True,separators=(',',':')).encode()
        committed=lifecycle.commit_selection(first,hashlib.sha256(raw).hexdigest(),process_name='Books Lifecycle No Such Fixture.exe')
        # Simulate the application's separately verified initial successful load.
        olddb=olddata/'inventory.sqlite3'
        with contextlib.closing(sqlite3.connect(olddb)) as db,db:
            db.executescript('CREATE TABLE jobs(root TEXT);CREATE TABLE queue(path TEXT);CREATE TABLE files(root TEXT,path TEXT,size INTEGER,modified INTEGER,kind TEXT)')
        saved=profile/'desktop-settings.json';saved.write_text(json.dumps({'dataDir':str(olddata),'catalogMode':'existing'}))
        before=olddb.read_bytes();bootstrap=Path(committed['bootstrap']);oldbootstrap=bootstrap.read_bytes()
        nextdata=app.parent/'SeparateData'
        plan=lifecycle.selection_plan('new',nextdata,application_dir=app,profile_dir=profile)
        self.assertNotEqual(plan['profile_dir'],str(profile))
        raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
        result=lifecycle.commit_selection(plan,hashlib.sha256(raw).hexdigest(),process_name='Books Lifecycle No Such Fixture.exe')
        new=json.loads(bootstrap.read_text())
        self.assertEqual(new['data_dir'],str(nextdata));self.assertNotEqual(new['profile_dir'],str(profile))
        self.assertEqual(Path(result['previous_bootstrap']).read_bytes(),oldbootstrap)
        self.assertEqual(olddb.read_bytes(),before);self.assertTrue(saved.exists())

    def test_refresh_recognizes_normal_private_chromium_files_but_not_personal_sibling(self):
        app=self.base/'installation'/'Application';profile=app.parent/'Profile';data=app.parent/'Data'
        plan=lifecycle.selection_plan('new',data,application_dir=app,profile_dir=profile)
        raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
        committed=lifecycle.commit_selection(plan,hashlib.sha256(raw).hexdigest(),process_name='Books Lifecycle No Such Fixture.exe')
        bootstrap=json.loads(Path(committed['bootstrap']).read_text());owner=Path(bootstrap['ownership_manifest'])
        self.bootstraps.append(committed['bootstrap'])
        (profile/'Local Storage'/'leveldb').mkdir(parents=True)
        (profile/'Local Storage'/'leveldb'/'000001.log').write_bytes(b'pending decision bytes')
        (profile/'DIPS').write_bytes(b'closed profile cache')
        (profile/'DawnWebGPUCache').mkdir()
        digest=hashlib.sha256(owner.read_bytes()).hexdigest()
        result=lifecycle.refresh_ownership(owner,digest,output_path=self.base/'review-one.json',bootstrap_path=committed['bootstrap'])
        self.assertEqual(result['blockers'],{})
        snapshot=json.loads(Path(result['ownership_path']).read_text())
        roots=[r for r in snapshot['roots'] if r['path']==str(profile)]
        self.assertEqual(len(roots[0]['files']),2)
        reviewed=lifecycle.plan_cleanup(result['ownership_path'],result['ownership_sha256'],selected_roots=[profile])
        self.assertEqual(reviewed['bytes'],len(b'pending decision bytesclosed profile cache'))
        personal=profile/'my-tax-return.pdf';personal.write_bytes(b'keep')
        again=lifecycle.refresh_ownership(owner,digest,output_path=self.base/'review-two.json',bootstrap_path=committed['bootstrap'])
        self.assertEqual(again['blockers'][str(profile)],'ownership_not_confirmed')
        self.assertEqual(personal.read_bytes(),b'keep')

    def test_existing_install_copies_confirmed_profile_decisions_without_changing_source_bytes(self):
        database=self.catalog('source-data')
        source=Path(os.environ['APPDATA'])/'Books Arranger';(source/'Local Storage'/'leveldb').mkdir(parents=True)
        settings=source/'desktop-settings.json';settings.write_text(json.dumps({'dataDir':str(database.parent),'catalogMode':'existing'}))
        decisions=source/'Local Storage'/'leveldb'/'000001.log';decisions.write_bytes(b'uncertain accepted decision request/hash')
        app=self.base/'new-install'/'Application';profile=app.parent/'Profile'
        plan=lifecycle.selection_plan('existing',database,application_dir=app,profile_dir=profile)
        self.assertTrue(plan['selection']['profile_confirmed'])
        before=database.read_bytes();settings_before=settings.read_bytes();decisions_before=decisions.read_bytes()
        raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
        result=lifecycle.commit_selection(plan,hashlib.sha256(raw).hexdigest(),process_name='Books Lifecycle No Such Fixture.exe')
        self.assertTrue(result['settings_preserved']);self.assertEqual(database.read_bytes(),before)
        self.assertEqual(settings.read_bytes(),settings_before);self.assertEqual(decisions.read_bytes(),decisions_before)
        self.assertEqual((profile/'Local Storage'/'leveldb'/'000001.log').read_bytes(),decisions_before)
        self.assertEqual((profile/'desktop-settings.json').read_bytes(),settings_before)

    def test_reused_catalog_refresh_claims_typed_work_only_and_keeps_unknown_sibling(self):
        database=self.catalog('source-data');root=database.parent
        manifest,digest=self.manifest(root,[database],role='database')
        refreshed=lifecycle.refresh_ownership(manifest,digest,output_path=self.base/'refresh-data.json',bootstrap_path=self.bootstraps[-1])
        self.assertEqual(refreshed['blockers'],{})
        current=json.loads(Path(refreshed['ownership_path']).read_text());selected=next(r for r in current['roots'] if r['path']==str(root));self.assertEqual({e['relative'] for e in selected['files']},{'inventory.sqlite3','inventory.sqlite3.lock'})
        sibling=root/'unrelated-photo.jpg';sibling.write_bytes(b'personal')
        again=lifecycle.refresh_ownership(manifest,digest,output_path=self.base/'refresh-data-unknown.json',bootstrap_path=self.bootstraps[-1])
        self.assertEqual(again['blockers'][str(root)],'ownership_not_confirmed');self.assertTrue(sibling.exists())

    def test_active_relocated_database_discovers_only_pinned_verification_descriptor(self):
        database=self.catalog('catalog');catalog=str(uuid.uuid4());generation=str(uuid.uuid4())
        with DirectoryBoundary(self.base.anchor,self.base) as d:root_id=list(d.identities[-1][1:])
        with DirectoryBoundary(database.parent.anchor,database.parent) as d:data_id=list(d.identities[-1][1:])
        value=dict(schema='books-storage-relocation-v1',generation=generation,catalog_id=catalog,
            source_root=r'C:\private-lifecycle-migration-source',target_root=str(self.base),scopes=['catalog'],source_snapshot_sha256='a'*64,
            directories=[dict(relative='',source_identity=[111,0,1],target_identity=root_id),
                         dict(relative='catalog',source_identity=[111,0,2],target_identity=data_id)],files=[])
        manifest=self.base/'relocation.json';raw=json.dumps(value).encode();manifest.write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
        receipt=self.base/'verification.json';proof=dict(schema='books-storage-target-verification-v1',catalog_id=catalog,
            generation=generation,manifest_sha256=sha,manifest_path=str(manifest),complete=True)
        receipt_raw=json.dumps(proof).encode();receipt.write_bytes(receipt_raw);receipt_sha=hashlib.sha256(receipt_raw).hexdigest()
        with contextlib.closing(sqlite3.connect(database)) as db,db:
            db.execute('CREATE TABLE storage_relocation_activation(catalog_id,generation,manifest_sha256,phase)')
            db.execute('INSERT INTO storage_relocation_activation VALUES(?,?,?,?)',(catalog,generation,sha,'active'))
            db.execute('CREATE TABLE storage_relocation_verification(catalog_id,generation,manifest_sha256,receipt_path,receipt_sha256,verified_state_sha256)')
            db.execute('INSERT INTO storage_relocation_verification VALUES(?,?,?,?,?,?)',(catalog,generation,sha,str(receipt),receipt_sha,'c'*64))
        result=lifecycle.inspect_existing(database)
        self.assertEqual(result['state'],'available');self.assertEqual(result['storage_relocation'],dict(manifest=str(manifest),sha256=sha))
        receipt.write_bytes(receipt_raw+b' ')
        refused=lifecycle.inspect_existing(database)
        self.assertEqual(refused['state'],'relocation_configuration_required')

    def test_interrupted_profile_copy_is_retained_and_never_adopted_on_retry(self):
        database=self.catalog();app=self.base/'Installation'/'Application';app.mkdir(parents=True)
        plan=lifecycle.selection_plan('existing',str(database),application_dir=str(app),profile_dir=str(app.parent/'Profile'))
        plan['selection'].update(profile_confirmed=True,associated_profile=str(self.base/'source'),
            profile_settings_path='unused',profile_settings_facts={},profile_settings_sha256='0'*64)
        raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode();sha=hashlib.sha256(raw).hexdigest()
        def interrupted(source,destination,*args):
            (destination/'Local State').write_bytes(b'preserved partial bytes')
            raise OSError('simulated power loss')
        with patch.object(lifecycle,'process_check',return_value={'state':'available'}),patch.object(lifecycle,'inspect_existing',return_value=dict(state='available',facts=plan['selection']['database_facts'],resolved_path=plan['selection']['resolved_database'])),patch.object(lifecycle,'_copy_profile',side_effect=interrupted):
            with self.assertRaises(OSError):lifecycle.commit_selection(plan,sha)
            with self.assertRaises(lifecycle.LifecycleRefused) as raised:lifecycle.commit_selection(plan,sha)
        self.assertEqual(raised.exception.code,'installation_commit_incomplete')
        self.assertEqual((app.parent/'Profile'/'Local State').read_bytes(),b'preserved partial bytes')
        self.assertFalse((app.parent/lifecycle.BOOTSTRAP).exists())

    def test_legacy_package_retirement_holds_unknown_and_busy_members_without_running_executable(self):
        root=self.base/'oldApplication';root.mkdir();binary=root/'Uninstall Books Arranger.exe'
        binary.write_bytes(b'fixture bytes are never executed');known=dict(size=binary.stat().st_size,sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
        with VerifiedFile(binary) as held:original_facts=held.facts()
        receipt=dict(schema='books-trusted-legacy-package-v1',version='0.27.0',installer_sha256='a'*64,files={binary.name:known})
        real=lifecycle._json
        def trusted(path,*args):
            if Path(path).name=='legacy-package-0.27.0.json':return receipt,{},'b'*64
            return real(path,*args)
        with patch.object(lifecycle,'_json',side_effect=trusted),patch.object(lifecycle,'process_check',return_value={'state':'available'}):
            personal=root/'personal.txt';personal.write_bytes(b'keep')
            with self.assertRaises(lifecycle.LifecycleRefused):lifecycle.retire_legacy_package(str(root),'0.27.0')
            self.assertTrue(binary.exists());personal.unlink()
            with VerifiedFile(binary):
                with self.assertRaises((OSError,ValueError)):lifecycle.retire_legacy_package(str(root),'0.27.0')
                self.assertTrue(binary.exists())
            result=lifecycle.retire_legacy_package(str(root),'0.27.0')
        self.assertEqual(result['removed_files'],0);self.assertFalse(binary.exists())
        self.assertEqual((Path(result['retained_application'])/binary.name).read_bytes(),b'fixture bytes are never executed')
        with VerifiedFile(Path(result['retained_application'])/binary.name) as held:self.assertEqual(held.facts(),original_facts)
        self.assertTrue(Path(result['receipt']).exists())

    def test_current_package_receipt_never_grants_recursive_application_deletion(self):
        root=self.base/'App';root.mkdir()
        plan=lifecycle.selection_plan('new',str(self.base/'Data'),application_dir=str(root),profile_dir=str(self.base/'Profile'))
        sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        committed=lifecycle.commit_selection(plan,sha,process_name='Books Lifecycle No Such Fixture.exe')
        self.bootstraps.append(committed['bootstrap'])
        binary=root/'Books Arranger.exe';binary.write_bytes(b'new fixture binary')
        producer=dict(schema='books-trusted-current-package-v1',files={binary.name:dict(size=binary.stat().st_size,sha256=hashlib.sha256(binary.read_bytes()).hexdigest())})
        real=lifecycle._json
        def trusted(path,*args):
            if Path(path).name=='current-package.json':return producer,{},'a'*64
            return real(path,*args)
        bootstrap=Path(committed['bootstrap']);saved=json.loads(bootstrap.read_text());install=saved['installation_id']
        with patch.object(lifecycle,'_json',side_effect=trusted),patch.object(lifecycle,'process_check',return_value={'state':'available'}):
            pin=lifecycle.capture_current_package(str(root),install)
            saved['package_ownership']=pin;bootstrap.write_text(json.dumps(saved))
            personal=root/'book.m4b';personal.write_bytes(b'never delete unknown arriving book')
            with self.assertRaises((OSError,ValueError)):lifecycle.remove_current_package(str(bootstrap))
            self.assertTrue(binary.exists());self.assertTrue(personal.exists());personal.unlink()
            with VerifiedFile(binary):
                with self.assertRaises((OSError,ValueError)):lifecycle.remove_current_package(str(bootstrap))
                self.assertTrue(binary.exists())
            result=lifecycle.remove_current_package(str(bootstrap))
        self.assertTrue(result['ok']);self.assertFalse(root.exists())

    def test_forged_hashed_receipt_cannot_claim_source_as_data_or_backup(self):
        app=self.base/'Application';data=self.base/'Data';profile=self.base/'Profile'
        plan=lifecycle.selection_plan('new',str(data),application_dir=str(app),profile_dir=str(profile))
        sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        committed=lifecycle.commit_selection(plan,sha,process_name='Books Lifecycle No Such Fixture.exe')
        self.bootstraps.append(committed['bootstrap']);bootstrap=json.loads(Path(committed['bootstrap']).read_text())
        original=Path(bootstrap['ownership_manifest']);owner=json.loads(original.read_text())
        source=data/'program.py';source.write_bytes(b'print("personal source must survive")')
        with VerifiedFile(source) as held:entry=dict(relative='program.py',facts=held.facts(),sha256=held.sha256())
        root=next(r for r in owner['roots'] if r['path']==str(data));root['files']=[entry]
        owner['producer']=dict(bootstrap=committed['bootstrap'],**bootstrap['ownership_provenance'])
        for role in ('database','backups'):
            root['role']=role;forged=self.base/('forged-'+role+'.json');raw=json.dumps(owner).encode();forged.write_bytes(raw)
            with self.assertRaises(lifecycle.LifecycleRefused):lifecycle.plan_cleanup(forged,hashlib.sha256(raw).hexdigest(),selected_roots=[data])
            self.assertTrue(source.exists())

    def test_application_source_target_is_refused_before_any_extraction_or_new_data(self):
        root=self.base/'source-repository';(root/'.git').mkdir(parents=True)
        files={root/'program.py':b'personal source',root/'package.json':b'{"private":true}',root/'book.m4b':b'personal book'}
        for path,raw in files.items():path.write_bytes(raw)
        with self.assertRaises(lifecycle.LifecycleRefused):lifecycle.admit_application_target(str(root))
        self.assertEqual({path:path.read_bytes() for path in files},files)
        self.assertFalse((self.base/'Data').exists())
        empty=self.base/'empty-target';empty.mkdir();self.assertEqual(lifecycle.admit_application_target(str(empty))['state'],'empty_target')

    def test_background_catalog_owner_blocks_even_without_a_matching_encoder_or_app(self):
        database=self.catalog();lock=Path(str(database)+'.lock');lock.write_bytes(b'owned lock')
        profile=Path(os.environ['APPDATA'])/'Books Arranger';profile.mkdir(parents=True)
        (profile/'desktop-settings.json').write_text(json.dumps(dict(dataDir=str(database.parent))))
        with VerifiedFile(lock,writable=True):
            result=lifecycle.process_check((),process_name='Books No Such Encoder Fixture.exe')
            self.assertEqual(result['state'],'in_use');self.assertEqual(result['busy'][0]['kind'],'catalog-owner')
        self.assertEqual(lifecycle.process_check((),process_name='Books No Such Encoder Fixture.exe')['state'],'available')

    def test_legacy_silent_update_keeps_exact_machine_catalog_and_profile_bytes(self):
        database=self.catalog('current-machine-data');source=Path(os.environ['APPDATA'])/'Books Arranger'
        (source/'Local Storage'/'leveldb').mkdir(parents=True)
        settings=source/'desktop-settings.json';settings.write_text(json.dumps(dict(dataDir=str(database.parent),catalogMode='existing')))
        decisions=source/'Local Storage'/'leveldb'/'000001.log';decisions.write_bytes(b'pending accepted decision and credential bytes')
        app=self.base/'current-machine-install'/'Application';app.mkdir(parents=True)
        plan=lifecycle.legacy_update_plan(str(app),'0.27.0',process_name='Books No Such Encoder Fixture.exe')['plan']
        self.assertEqual(plan['selection']['data_dir'],str(database.parent));self.assertEqual(plan['selection']['associated_profile'],str(source))
        self.assertFalse((app.parent/'Profile').exists());before=database.read_bytes()
        sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        result=lifecycle.commit_selection(plan,sha,process_name='Books No Such Encoder Fixture.exe')
        bootstrap=json.loads(Path(result['bootstrap']).read_text())
        self.assertEqual(bootstrap['data_dir'],str(database.parent));self.assertEqual(database.read_bytes(),before)
        self.assertEqual((Path(bootstrap['profile_dir'])/decisions.relative_to(source)).read_bytes(),decisions.read_bytes())
        self.assertEqual((Path(bootstrap['profile_dir'])/settings.name).read_bytes(),settings.read_bytes())

    def test_legacy_silent_update_missing_settings_refuses_before_any_changes(self):
        app=self.base/'legacy'/'Application';app.mkdir(parents=True);binary=app/'Books Arranger.exe';binary.write_bytes(b'original')
        with self.assertRaisesRegex(lifecycle.LifecycleRefused,'legacy_update_requires_assisted_setup'):
            lifecycle.legacy_update_plan(str(app),'0.27.0',process_name='Books No Such Encoder Fixture.exe')
        self.assertEqual(binary.read_bytes(),b'original');self.assertFalse((app.parent/'Profile').exists())

    def test_retained_legacy_profile_requires_genuine_same_account_copy_proof(self):
        database=self.catalog('legacy-data');source=Path(os.environ['APPDATA'])/'Books Arranger';source.mkdir(parents=True)
        (source/'desktop-settings.json').write_text(json.dumps(dict(dataDir=str(database.parent),catalogMode='existing')))
        original=source/'Preferences';original.write_bytes(b'{"retained":"original"}')
        app=self.base/'new'/'Application';app.mkdir(parents=True)
        plan=lifecycle.selection_plan('existing',str(database),application_dir=str(app),profile_dir=str(app.parent/'Profile'))
        sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        result=lifecycle.commit_selection(plan,sha,process_name='Books No Such Retained Profile Fixture.exe')
        bootstrap=Path(result['bootstrap']);self.bootstraps.append(str(bootstrap));value=json.loads(bootstrap.read_text())
        (Path(value['profile_dir'])/'Preferences').write_bytes(b'{"new":"current decisions"}')
        owner=Path(value['ownership_manifest']);review=lifecycle.refresh_ownership(owner,hashlib.sha256(owner.read_bytes()).hexdigest(),
            output_path=self.base/'retained-profile-review.json',bootstrap_path=str(bootstrap))
        admitted=lifecycle.plan_cleanup(review['ownership_path'],review['ownership_sha256'],selected_roots=[source],bootstrap_paths=[str(bootstrap)])
        self.assertTrue(admitted['targets']);self.assertEqual(original.read_bytes(),b'{"retained":"original"}')
        pin=value['retained_profile'];proof=Path(pin['manifest']);content=json.loads(proof.read_text())
        content['account_sid']='S-1-5-21-0-0-0-9999';raw=json.dumps(content).encode();forged=self.base/'forged-profile-proof.json';forged.write_bytes(raw)
        value['retained_profile']=dict(manifest=str(forged),sha256=hashlib.sha256(raw).hexdigest());bootstrap.write_text(json.dumps(value))
        with self.assertRaises(lifecycle.LifecycleRefused):lifecycle.plan_cleanup(review['ownership_path'],review['ownership_sha256'],selected_roots=[source],bootstrap_paths=[str(bootstrap)])
        self.assertTrue(original.exists())


if __name__=='__main__':unittest.main()
