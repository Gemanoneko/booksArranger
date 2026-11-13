"""Actual cross-volume copy, preserved receipts, active generation and restart."""
import ctypes
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid

from scanner import connect
from source_cleanup import packed
from native_io import VerifiedFile, BoundaryError
from working_lifecycle import WorkingLifecycle, digest
from catalog_owner import catalog_lock
from storage_relocation import RelocationRefused
import storage_relocation_native as native
import storage_relocation_operator as operator


@unittest.skipUnless(os.name == 'nt', 'Windows native relocation contract')
class RelocatedWorkingIntegrationTests(unittest.TestCase):
    def test_install_commit_binds_verified_relocated_catalog_and_retains_profile(self):
        from unittest.mock import patch
        import storage_lifecycle as lifecycle
        self.relocate()
        physical=self.target/'data/inventory.sqlite3'
        roaming=Path(self.right.name)/'Roaming'
        profile=roaming/'Books Arranger'
        profile.mkdir(parents=True)
        settings=profile/'desktop-settings.json'
        settings.write_text(json.dumps({'dataDir':str(self.database.parent),'catalogMode':'existing'}),encoding='utf8')
        outbox=profile/'fixture-outbox.json'
        outbox.write_text('{"fixture":"pending review"}',encoding='utf8')
        app=Path(self.right.name)/'New installation'/'Application'
        app.mkdir(parents=True)
        destination=app.parent/'Profile'
        pin={'manifest':str(self.descriptor),'sha256':self.descriptor_sha}
        with patch.dict(os.environ,{'APPDATA':str(roaming)}),patch.object(lifecycle,'registered_bootstraps',return_value=[]):
            plan=lifecycle.selection_plan('existing',physical,application_dir=app,profile_dir=destination,
                                          config_paths=[str(settings)])
            self.assertTrue(plan['selection']['profile_confirmed'])
            self.assertEqual(plan['selection']['storage_relocation'],pin)
            plan_sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            with self.assertRaisesRegex(lifecycle.LifecycleRefused,'invalid_relocation_selection'):
                lifecycle.commit_selection(plan,plan_sha,storage_relocation={**pin,'sha256':'0'*64},
                                           process_name='Books Private Relocation QA.exe')
            self.assertFalse(destination.exists())
            receipt=lifecycle.commit_selection(plan,plan_sha,process_name='Books Private Relocation QA.exe')
        self.assertIsNone(native.current(),'the installer releases its temporary relocation context')
        bootstrap=json.loads(Path(receipt['bootstrap']).read_text('utf8'))
        self.assertEqual(bootstrap['data_dir'],str(physical.parent))
        self.assertEqual(bootstrap['storage_relocation'],pin)
        self.assertEqual((destination/settings.name).read_bytes(),settings.read_bytes())
        self.assertEqual((destination/outbox.name).read_bytes(),outbox.read_bytes())

    def test_source_recovered_retained_intent_moves_only_with_independent_working_receipt(self):
        from runtime_disposition_owners import admit_catalog,context_for
        from runtime_file_disposition import prepare_disposition
        with catalog_lock(self.database,{}):
            admit_catalog(self.database)
            with VerifiedFile(self.file,delete=True) as held:
                prepared=prepare_disposition(held,context_for(self.file));prepared.abort('source-side refusal before disposition')
        # Source-side exact recovery writes a distinct RETAINED terminal proof;
        # it neither closes a producer nor certifies deletion.
        with catalog_lock(self.database,{}):admit_catalog(self.database)
        retained=list((self.source/'data/file-disposition-ledger').glob('*.retained.json'))
        self.assertEqual(len(retained),1);original=retained[0].read_bytes()
        self.relocate();native.configure(self.descriptor,self.descriptor_sha)
        with catalog_lock(self.database,{}):WorkingLifecycle(self.database,self.stage).retire(self.job,self.attempt)
        self.assertFalse(self.file.exists())
        self.assertEqual(retained[0].read_bytes(),original)
        self.assertEqual((self.backup/'data/merge-cache/audio-staging'/self.job/self.attempt/self.filename).read_bytes(),b'owned closed producer diagnostic')

    def test_closed_runtime_ledger_relocates_without_old_acl_or_identity_authority(self):
        from runtime_disposition_owners import admit_catalog
        transient=self.source/'data/transient.bin';transient.write_bytes(b'closed temporary output')
        with catalog_lock(self.database,{}):
            admit_catalog(self.database)
            with VerifiedFile(transient,delete=True) as held:held.dispose()
        marker=self.source/'data/file-disposition-ledger/context.json'
        original=marker.read_bytes()
        self.relocate();native.configure(self.descriptor,self.descriptor_sha)
        with catalog_lock(self.database,{}):
            admit_catalog(self.database)
            self.assertEqual(marker.read_bytes(),original)
            self.assertFalse(transient.exists())
            newfile=self.source/'data/new-generation.bin';newfile.write_bytes(b'new generation work')
            with VerifiedFile(newfile,delete=True) as held:held.dispose()
        with catalog_lock(self.database,{}):admit_catalog(self.database)
        self.assertEqual((self.backup/'data/file-disposition-ledger/context.json').read_bytes(),original)

    def setUp(self):
        scratch=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',Path(__file__).resolve().parents[1]/'scratch'))
        scratch.mkdir(exist_ok=True)
        self.left=tempfile.TemporaryDirectory(prefix='move-integration-source-',dir=os.environ.get('BOOKS_RELOCATION_FIXTURE_SOURCE',scratch))
        self.right=tempfile.TemporaryDirectory(prefix='move-integration-target-',dir=os.environ.get('BOOKS_RELOCATION_FIXTURE_TARGET',scratch))
        self.source=Path(self.left.name)/'source';self.target=Path(self.right.name)/'target'
        self.backup=Path(self.left.name)/'original-preserved';self.work=Path(self.right.name)/'operator'
        self.work.mkdir();self.plan=None
        data=self.source/'data';data.mkdir(parents=True);self.database=data/'inventory.sqlite3'
        self.stage=data/'merge-cache/audio-staging';self.job=str(uuid.uuid4());self.attempt=str(uuid.uuid4())
        folder=self.stage/self.job/self.attempt;folder.mkdir(parents=True)
        self.filename='a'*32+'.stderr';self.file=folder/self.filename;self.file.write_bytes(b'owned closed producer diagnostic')
        with VerifiedFile(self.file) as h:self.facts=h.facts();self.filehash=h.sha256()
        manifest={'root':str(Path(self.left.name)/'unchanged-library'),'sources':[]}
        frozen=packed(manifest);mh=digest(manifest)
        (folder.parent/'ownership.json').write_text(packed({'job_id':self.job,'manifest':manifest}),encoding='utf8')
        WorkingLifecycle(self.database,self.stage)
        with connect(self.database) as db:
            db.execute('CREATE TABLE audio_jobs(job_id TEXT,manifest TEXT,manifest_hash TEXT,state TEXT,stage TEXT,attempt_id TEXT,journal TEXT,output TEXT,reason TEXT,created TEXT,updated TEXT)')
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',(self.job,frozen,mh,'pending','pending',self.attempt,'{}',None,'','initial','initial'))
            db.execute('INSERT INTO working_attempts VALUES(?,?,?,?,?,?,?,?)',(self.job,self.attempt,frozen,mh,'closed','closed','','initial'))
            db.execute('INSERT INTO working_files VALUES(?,?,?,?,?,?,?,?,?,?)',(self.job,self.attempt,self.filename,str(self.file),'generated','closed',self.filehash,self.facts['size'],packed(self.facts),'initial'))
        with catalog_lock(self.database,{}):pass

    def tearDown(self):
        native.close()
        # Explicit restoration only of THESE private fixture files. This is not
        # a production rollback claim after target application writes.
        if self.plan:
            root=self.backup if self.backup.exists() else self.source
            rows=json.loads(Path(self.plan).read_text('utf8'))['security']
            for record in sorted(rows,key=lambda r:len(Path(r['relative']).parts)):
                if not (root/record['relative']).exists():continue
                with operator.NativeItem(root/record['relative'],directory=record['kind']=='directory',writable_security=True) as item:
                    self.assertEqual(item.facts['identity'],record['identity'])
                    operator.Security().restore(item,record['original_security'])
        self.left.cleanup();self.right.cleanup()

    def relocate(self,enable=True):
        args=(str(self.source),str(self.target),['data'],r'data\inventory.sqlite3',str(self.work))
        preview=operator.prepare_source(*args)
        prepared=operator.prepare_source(*args,apply=True,catalog_id=preview['catalog_id'],generation=preview['generation'],expected_plan_sha256=preview['consent_sha256'])
        self.plan=prepared['source_plan']
        shutil.copytree(self.source,self.target,copy_function=shutil.copy2)
        # Fresh private copy: preserve its reviewed source fence as a real
        # migration copier must; copy2 alone omits Windows security descriptors.
        fence=json.loads(Path(prepared['source_fence']).read_text('utf8'))
        for record in fence['items']:
            with operator.NativeItem(self.target/record['relative'],directory=record['kind']=='directory',
                                     writable_security=True) as item:
                operator.Security().restore(item,record['applied_security'])
        self.source.rename(self.backup)
        self.descriptor=self.work/'relocation.json'
        sealed=operator.seal_target(prepared['source_plan'],prepared['source_plan_sha256'],
            prepared['source_fence'],prepared['source_fence_sha256'],str(self.backup),str(self.descriptor))
        self.descriptor_sha=sealed['manifest_sha256']
        operator.activate_target(str(self.descriptor),self.descriptor_sha)
        result=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/cmd.exe'),'/d','/c','mklink','/J',str(self.source),str(self.target)],capture_output=True,timeout=10,creationflags=0x08000000)
        self.assertEqual(result.returncode,0,result.stderr)
        if enable:self.enable()

    def enable(self):
        verified=operator.verify_target(str(self.descriptor),self.descriptor_sha)
        operator.enable_target(str(self.descriptor),self.descriptor_sha,
            verified['verification_path'],verified['verification_sha256'])

    def test_pending_work_retires_copied_exact_bytes_keeps_old_receipt_and_restarts(self):
        self.relocate();native.configure(self.descriptor,self.descriptor_sha)
        with catalog_lock(self.database,{}) as owner:
            self.assertTrue(owner['held'])
            WorkingLifecycle(self.database,self.stage).retire(self.job,self.attempt)
            with connect(self.database) as db:
                row=db.execute('SELECT facts,state FROM working_files').fetchone()
                self.assertEqual(json.loads(row['facts']),self.facts,'old native receipt bytes are not rewritten')
                self.assertEqual(row['state'],'removed')
        self.assertFalse(self.file.exists())
        original=self.backup/'data/merge-cache/audio-staging'/self.job/self.attempt/self.filename
        self.assertEqual(original.read_bytes(),b'owned closed producer diagnostic')
        native.close();native.configure(self.descriptor,self.descriptor_sha)
        with catalog_lock(self.database,{}):WorkingLifecycle(self.database,self.stage).retire(self.job,self.attempt)
        self.assertEqual(original.read_bytes(),b'owned closed producer diagnostic')

    def test_unavailable_target_and_replaced_copied_artifact_refuse_without_source_fallback(self):
        self.relocate()
        moved=self.target.with_name('temporarily-away');self.target.rename(moved)
        with self.assertRaises((BoundaryError,RelocationRefused)):
            native.configure(self.descriptor,self.descriptor_sha)
        moved.rename(self.target)
        self.file.unlink();self.file.write_bytes(b'owned closed producer diagnostic')
        native.configure(self.descriptor,self.descriptor_sha)
        with catalog_lock(self.database,{}),self.assertRaises(BoundaryError):
            WorkingLifecycle(self.database,self.stage).retire(self.job,self.attempt)
        self.assertTrue(self.file.exists())
        self.assertTrue((self.backup/'data/merge-cache/audio-staging'/self.job/self.attempt/self.filename).exists())

    def test_omitting_descriptor_cannot_open_relocated_catalog_as_writable_legacy(self):
        self.relocate()
        physical=self.target/'data/inventory.sqlite3'
        before=physical.read_bytes()
        with self.assertRaisesRegex(RelocationRefused,'relocation generation'):
            connect(physical)
        with self.assertRaisesRegex(RelocationRefused,'relocation generation'):
            with catalog_lock(physical,{}):pass
        from audio_jobs import AudioJobs
        with self.assertRaisesRegex(RelocationRefused,'relocation generation'):
            AudioJobs(physical,None,None,None)
        self.assertEqual(physical.read_bytes(),before)

    def test_catalog_clone_and_same_path_replacement_have_no_generation_authority(self):
        self.relocate()
        physical=self.target/'data/inventory.sqlite3'
        clone=self.target/'data/cloned/inventory.sqlite3'
        clone.parent.mkdir()
        shutil.copy2(physical,clone)
        native.configure(self.descriptor,self.descriptor_sha)
        with self.assertRaisesRegex(RelocationRefused,'storage binding'):
            with catalog_lock(self.database.parent/'cloned/inventory.sqlite3',{}):pass
        native.close()
        # Hold the original native object alive so NTFS cannot recycle its ID.
        preserved=physical.with_name('sealed-original.sqlite3')
        physical.rename(preserved);shutil.copy2(preserved,physical)
        native.configure(self.descriptor,self.descriptor_sha)
        with self.assertRaisesRegex(RelocationRefused,'native file identity'):
            with catalog_lock(self.database,{}):pass
        self.assertEqual(physical.read_bytes(),preserved.read_bytes())
        physical.unlink();preserved.rename(physical)
        with catalog_lock(self.database,{}):
            with self.assertRaises(PermissionError):physical.rename(preserved)

    def test_runtime_restarts_after_verified_old_copy_retirement_without_old_root(self):
        from storage_source_finalization import plan_source_finalization,apply_source_finalization
        self.relocate()
        plan=plan_source_finalization(self.descriptor,self.descriptor_sha)
        result=apply_source_finalization(self.descriptor,self.descriptor_sha,
            operator.digest(operator.packed(plan)),forfeit_rollback=True)
        self.assertTrue(result['complete'])
        # Original shared code/root is outside selected DATA ownership. Its
        # eventual retirement must not become a permanent runtime dependency.
        moved=self.backup.with_name('retired-original-location')
        self.backup.rename(moved)
        native.configure(self.descriptor,self.descriptor_sha)
        try:
            with catalog_lock(self.database,{}):
                WorkingLifecycle(self.database,self.stage).retire(self.job,self.attempt)
                self.assertFalse(self.file.exists())
            native.close();native.configure(self.descriptor,self.descriptor_sha)
            with catalog_lock(self.database,{}):
                with connect(self.database) as db:
                    self.assertEqual(db.execute('SELECT state FROM working_files').fetchone()[0],'removed')
        finally:
            native.close();moved.rename(self.backup)

    def test_real_approved_conversion_runs_after_copy_and_restart_keeps_verified_output(self):
        from unittest.mock import patch
        import test_automatic_media as fixtures
        from scanner import Inventory
        from merge_service import MergeService
        from public_research import PublicClient
        import sqlite3
        f=fixtures.AutomaticMediaTests('test_confident_no_manual_form_to_verified_chapters_retained_recovery')
        with patch.object(fixtures,'AREA',Path(self.right.name)):
            f.setUp()
        traces=contextlib.ExitStack();target_trace=source_trace=None
        try:
            f.service.close()
            # Build a fresh private catalog for the unchanged private book
            # library outside our simulated shared-root alias.
            shutil.rmtree(self.source)
            self.database.parent.mkdir(parents=True)
            roots={'Audiobooks':str(f.audio),'Podcasts':str(f.base/'podcasts'),'Ebooks':str(f.base/'ebooks')}
            sorted_root=f.base/'sorted';sorted_root.mkdir()
            with contextlib.closing(sqlite3.connect(f.inv.database)) as old,contextlib.closing(sqlite3.connect(self.database)) as new:old.backup(new)
            inv=Inventory(self.database,roots,output_root=str(sorted_root))
            f.inv=inv;f.service=MergeService(inv,self.database.parent/'merge-cache')
            f.client=PublicClient(inv.database,fetch=f.client.fetch)
            with catalog_lock(self.database,roots):
                row,result=f.result()
                with patch.object(f.service.jobs,'resume',return_value=None):
                    _,job_id=f.service.approve_automatic(row,result,threading.Event(),f.client)
            self.assertEqual(f.service.jobs.status()['jobs'][0]['state'],'pending')
            f.service.close()
            with catalog_lock(self.database,{}):pass
            self.relocate(enable=False);native.configure(self.descriptor,self.descriptor_sha)
            selected_temp=self.work/'temporary-work';selected_temp.mkdir()
            traces.enter_context(patch.dict(os.environ,{'BOOKS_WORK_TEMP':str(selected_temp),
                'TEMP':str(selected_temp),'TMP':str(selected_temp)}))
            native.configure_work_temp()
            with tempfile.TemporaryFile() as generic_work:generic_work.write(b'explicitly selected Python temporary output')
            from native_write_trace import NativeWriteTrace
            target_trace=traces.enter_context(NativeWriteTrace(Path(self.right.name)))
            source_trace=traces.enter_context(NativeWriteTrace(self.backup))
            control=self.work/'filesystem-trace-positive-control'
            control.write_bytes(b'actual native notification');control.unlink()
            # Actual backend startup, before constructors that could repair,
            # move or retire sources. This is a private headless Python child,
            # not the user's installed Electron app or current catalog.
            environment=dict(os.environ,BOOKS_ARRANGER_DESKTOP_TOKEN='a'*64,
                BOOKS_STORAGE_RELOCATION_MANIFEST=str(self.descriptor),
                BOOKS_STORAGE_RELOCATION_SHA256=self.descriptor_sha)
            admission=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve().parents[1]/'desktop_storage_admission.py'),
                '--database',str(self.target/'data/inventory.sqlite3')],env=environment,
                capture_output=True,timeout=15,creationflags=0x08000000)
            self.assertNotEqual(admission.returncode,0)
            self.assertEqual(json.loads(admission.stdout)['code'],'verification_required')
            self.assertIn('with the relocation tool',json.loads(admission.stdout)['error'])
            # Copy the pinned fixture's backend code out of the catalog's
            # ancestor, as in an installed layout. Never weaken that guard.
            backend=self.work/'installed-backend'
            backend.mkdir()
            for module in Path(__file__).resolve().parents[1].glob('*.py'):
                shutil.copyfile(module,backend/module.name)
            startup=subprocess.run([sys.executable,'-I','-B',str(backend/'desktop_backend.py'),
                '--database',str(self.database),'--port','5212','--catalog-mode=existing'],
                env=environment,capture_output=True,timeout=15,creationflags=0x08000000)
            self.assertNotEqual(startup.returncode,0)
            self.assertIn(b'offline verification',startup.stderr)
            self.assertTrue(all(p.is_file() for p in f.sources),'verification admission did not retire any private book source')
            self.assertFalse((self.database.parent/'web-instance.json').exists(),'verification stops before backend instance/worker creation')
            self.enable()
            with catalog_lock(self.database,roots):
                f.inv=Inventory(self.database,roots,output_root=str(sorted_root))
                f.service=MergeService(f.inv,self.database.parent/'merge-cache')
                f.service.jobs.resume();f.wait()
                job=next(j for j in f.service.jobs.status()['jobs'] if j['job_id']==job_id)
                self.assertEqual(job['state'],'completed',job)
                output=Path(job['output']['final_path'])
                self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),job['output']['sha256'])
                self.assertTrue(all(not p.exists() for p in f.sources),'only these private sources retired after verification')
                f.service.close()
            native.close();native.configure(self.descriptor,self.descriptor_sha);native.configure_work_temp()
            with catalog_lock(self.database,roots):
                f.inv=Inventory(self.database,roots,output_root=str(sorted_root))
                f.service=MergeService(f.inv,self.database.parent/'merge-cache')
                self.assertTrue(output.is_file())
                self.assertEqual(f.service.jobs.status()['jobs'][0]['state'],'completed')
                f.service.close()
            traces.close()
            self.assertTrue(any(e['path'].endswith('filesystem-trace-positive-control') for e in target_trace.events))
            self.assertTrue(any('audio-staging' in e['path'] and e['path'].endswith('.m4b') for e in target_trace.events),
                'actual native trace must observe conversion staging writes on target volume')
            self.assertTrue(any(Path(e['path'])==output for e in target_trace.events),
                'actual native trace must observe final output publication')
            self.assertEqual(source_trace.events,[],'retained original C data was not written during target conversion/restart')
            report=os.environ.get('BOOKS_QA_WRITE_TRACE_REPORT')
            if report:
                with Path(report).open('x',encoding='utf8') as trace_file:
                    json.dump({'python':sys.executable,'backend':str(Path(__file__).resolve().parents[1]),
                        'ffmpeg':shutil.which('ffmpeg'),'target_events':target_trace.events,
                        'retained_source_events':source_trace.events,'final_output_sha256':job['output']['sha256'],
                        'scope':'private roots only; excludes OS/personal/global locations'},trace_file,indent=2)
        finally:
            try:
                traces.close()
                if native.current():
                    with catalog_lock(self.database,{}):f.tearDown()
                else:f.tearDown()
            finally:native.close()

    def test_mutable_index_db_and_journal_keep_original_owner_receipt_across_relocation(self):
        import openlibrary_index as index
        from native_io import DirectoryBoundary
        leaf=self.database.parent/'openlibrary-index/active.sqlite3'
        with DirectoryBoundary(leaf.anchor,leaf.parent,create=True) as boundary:
            with index._owned_sqlite(leaf,'openlibrary-active-v1',boundary) as db:
                db.execute('CREATE TABLE state(key TEXT PRIMARY KEY,value TEXT)')
                db.execute('INSERT INTO state VALUES(?,?)',('retained','before'))
        receipt=leaf.with_name(leaf.name+'.owner.json').read_bytes()
        self.relocate();native.configure(self.descriptor,self.descriptor_sha)
        with catalog_lock(self.database,{}):
            with index._read_sqlite(leaf) as (db,held):
                self.assertEqual(db.execute('SELECT value FROM state').fetchone()[0],'before')
            with DirectoryBoundary(leaf.anchor,leaf.parent) as boundary:
                with index._owned_sqlite(leaf,'openlibrary-active-v1',boundary) as db:
                    db.execute('UPDATE state SET value=?',('after legitimate index write',))
            with index._read_sqlite(leaf) as (db,held):
                self.assertEqual(db.execute('SELECT value FROM state').fetchone()[0],'after legitimate index write')
            self.assertEqual(leaf.with_name(leaf.name+'.owner.json').read_bytes(),receipt)

    def test_replacement_recovery_row_reuses_copied_bytes_without_rewriting_provenance(self):
        from native_io import DirectoryBoundary
        from replacement_retirement import ReplacementRetirement
        identifier=str(uuid.uuid4());original=Path(self.left.name)/'unchanged-library/former.m4b'
        original.parent.mkdir();original.write_bytes(b'former private output')
        root=self.database.parent/'replacement-recovery';folder=root/identifier;folder.mkdir(parents=True)
        recovery=folder/(hashlib.sha256(str(original).encode('utf8')).hexdigest()+'.m4b')
        recovery.write_bytes(original.read_bytes())
        with DirectoryBoundary(root,folder) as boundary,VerifiedFile(recovery) as held:
            saved={'path':str(recovery),'facts':held.facts(),'ancestry':boundary.identities,
                'sha256':held.sha256(),'size':held.facts()['size'],'retired_at':'fixture','expire_after':None}
        proof={'path':str(original),'sha256':saved['sha256'],'size':saved['size']}
        relation={'id':identifier,'approval_json':packed({'old_outputs':[proof]})}
        row={'replacement_id':identifier,'original_path':str(original),'provenance_json':packed(proof),
            'recovery_json':packed(saved),'state':'removed','reason':'','updated':'fixture'}
        with connect(self.database) as db:
            db.execute('CREATE TABLE audiobook_replacement_retirements(replacement_id TEXT,original_path TEXT,provenance_json TEXT,recovery_json TEXT,state TEXT,reason TEXT,updated TEXT)')
            db.execute('INSERT INTO audiobook_replacement_retirements VALUES(?,?,?,?,?,?,?)',tuple(row.values()))
        self.relocate();native.configure(self.descriptor,self.descriptor_sha)
        service=ReplacementRetirement.__new__(ReplacementRetirement);service.root=root;service.stop=threading.Event()
        with catalog_lock(self.database,{}):
            with service._recovery(relation,row,historical=True) as held:self.assertEqual(held.sha256(),saved['sha256'])
            with connect(self.database) as db:self.assertEqual(db.execute('SELECT recovery_json FROM audiobook_replacement_retirements').fetchone()[0],row['recovery_json'])
            recovery.write_bytes(b'changed copied recovery')
            with self.assertRaises(BoundaryError):
                with service._recovery(relation,row,historical=True):pass
        self.assertEqual((self.backup/'data/replacement-recovery'/identifier/recovery.name).read_bytes(),b'former private output')

    def test_immutable_index_generation_keeps_completion_and_pending_owner_after_copy(self):
        import openlibrary_index as index
        from native_io import DirectoryBoundary,publish_no_replace
        token='b'*64;directory=self.database.parent/'openlibrary-index'
        pending=directory/('pending-'+token+'.sqlite3');ready=directory/('index-'+token+'.sqlite3')
        with DirectoryBoundary(directory.anchor,directory,create=True) as boundary:
            with index._owned_sqlite(pending,token,boundary) as db:
                db.execute('CREATE TABLE evidence(value TEXT)');db.execute('INSERT INTO evidence VALUES(?)',('private immutable index',))
            with VerifiedFile(pending) as held:facts=held.facts();sha=held.sha256()
            publish_no_replace(pending,ready,boundary,expected_sha256=sha,expected_size=facts['size'])
            complete=ready.with_name(ready.name+'.complete.json')
            index._publish_json(complete,{'token':token,'sha256':sha,'size':facts['size'],'identity':facts['identity']},boundary)
        lock=directory/'import-lock.sqlite3.lock';lock.write_bytes(b'')
        owner=pending.with_name(pending.name+'.owner.json');before=(owner.read_bytes(),complete.read_bytes())
        self.relocate();native.configure(self.descriptor,self.descriptor_sha)
        with catalog_lock(self.database,{}),index._read_sqlite(ready) as (db,held):
            self.assertEqual(db.execute('SELECT value FROM evidence').fetchone()[0],'private immutable index')
            self.assertEqual(held.sha256(),sha)
        self.assertEqual((owner.read_bytes(),complete.read_bytes()),before)

    def test_retained_producer_origin_proof_stays_immutable_while_location_is_bridged(self):
        from producer_recovery import ProducerRecovery,CLAIM,verify_retained
        import sqlite3
        library=Path(self.left.name)/'unchanged-library';library.mkdir()
        original=library/'unchanged-original.m4b';original.write_bytes(b'private original intact')
        self.file.unlink();self.filename='source00000.m4b';self.file=self.file.with_name(self.filename)
        self.file.write_bytes(b'unadopted private snapshot retained')
        candidate=str(uuid.uuid4())
        manifest={'job_id':self.job,'candidate_id':candidate,'root':str(library),
            'sources':[{'path':str(original),'size':original.stat().st_size,'sha256':hashlib.sha256(original.read_bytes()).hexdigest()}]}
        (self.file.parent.parent/'ownership.json').write_text(packed({'job_id':self.job,'manifest':manifest}),encoding='utf8')
        with connect(self.database) as db:
            db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,superseded INTEGER)')
            db.execute('INSERT INTO book_groups VALUES(?,?,?,?)',(candidate,2,'explicit-private-fixture',0))
            db.execute('UPDATE audio_jobs SET state=?,manifest=?,manifest_hash=?',('needs attention',packed(manifest),digest(manifest)))
            db.execute('UPDATE working_attempts SET producer=?,state=?,manifest=?,manifest_hash=?',('active','producing',packed(manifest),digest(manifest)))
            db.execute('UPDATE working_files SET name=?,path=?,role=?,state=?,sha256=?,size=?,facts=?',
                (self.filename,str(self.file),'source','creation_intended','',0,'{}'))
        uptime=[100000]
        # Controlled old/later startup facts are explicit TEST provenance, never
        # a claim of production reboot or closure. File/catalog leases are real.
        platform=lambda:{'schema':'books-windows-startup-v1','system_volume_serial':'fixture-volume',
            'machine_guid':'explicit-private-machine','computer':'fixture','windows_directory':'C:/Windows','uptime_ms':uptime[0]}
        private_source=os.environ.get('BOOKS_QA_SOURCE_RUNTIME_ROOT')
        if private_source:
            runtime=Path(private_source).absolute()
            self.assertEqual(runtime.parent,Path(os.environ['BOOKS_RELOCATION_FIXTURE_SOURCE']))
            self.assertTrue(runtime.name.startswith('private-source-runtime-'))
            self.assertEqual(json.loads((runtime/'fixture-runtime-owner.json').read_text('utf8')),
                {'schema':'books-private-runtime-fixture-v1','disposable':True})
            self.assertNotEqual(runtime.drive.lower(),Path(sys.executable).drive.lower())
            control=self.work/'old-runtime-proof.json'
            control.write_text(json.dumps({'database':str(self.database),'stage':str(self.stage),'job':self.job}),encoding='utf8')
            code=('import sys,json;sys.path.insert(0,sys.argv[1]);from pathlib import Path;'
                'from producer_recovery import ProducerRecovery,CLAIM;v=json.loads(Path(sys.argv[2]).read_text("utf8"));'
                'uptime=[100000];platform=lambda:{"schema":"books-windows-startup-v1","system_volume_serial":"fixture-volume",'
                '"machine_guid":"explicit-private-machine","computer":"fixture","windows_directory":"C:/Windows","uptime_ms":uptime[0]};'
                'r=ProducerRecovery(v["database"],v["stage"],platform=platform);'
                'r.record_origin(v["job"],{"actor":"user","claim":CLAIM,"evidence":"Explicit synthetic fixture historical fact, never production attestation"});'
                'r.prepare(v["job"]);uptime[0]=5000;r.isolate(v["job"]);'
                'print(json.dumps({"executable":sys.executable,"backend":str(Path(__import__("producer_recovery").__file__).parent)}))')
            result=subprocess.run([str(runtime/'python/python.exe'),'-I','-B','-c',code,str(runtime/'backend'),str(control)],
                cwd=runtime/'backend',capture_output=True,timeout=20,creationflags=0x08000000)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            reported=json.loads(result.stdout)
            self.assertEqual(Path(reported['executable']),runtime/'python/python.exe')
            self.assertEqual(Path(reported['backend']),runtime/'backend')
            unavailable=runtime.with_name(runtime.name+'.offline')
            self.assertFalse(unavailable.exists());runtime.rename(unavailable)
            self.addCleanup(lambda:unavailable.rename(runtime))
            self.assertFalse((runtime/'python/python.exe').exists())
            self.assertFalse((runtime/'backend/producer_recovery.py').exists())
            uptime[0]=5000
        else:
            recovery=ProducerRecovery(self.database,self.stage,platform=platform)
            recovery.record_origin(self.job,{'actor':'user','claim':CLAIM,
                'evidence':'Explicit synthetic fixture historical fact, never production attestation'})
            recovery.prepare(self.job);uptime[0]=5000;recovery.isolate(self.job)
        with connect(self.database) as db:
            immutable=tuple(db.execute('SELECT native,proof FROM producer_recovery_checkpoints WHERE state=?',('isolated_retained',)).fetchone())
        self.relocate();native.configure(self.descriptor,self.descriptor_sha)
        with catalog_lock(self.database,{}):
            recovery=ProducerRecovery(self.database,self.stage,platform=platform)
            with recovery.protect_retained(self.job) as record:
                self.assertEqual(record['proof']['native_sha256'],json.loads(immutable[1])['native_sha256'])
                self.assertFalse(record['proof']['ownership_authority'])
            with connect(self.database) as db:
                self.assertEqual(tuple(db.execute('SELECT native,proof FROM producer_recovery_checkpoints WHERE state=?',('isolated_retained',)).fetchone()),immutable)
                verify_retained(db,self.job,self.attempt)
            with self.assertRaisesRegex(BoundaryError,'retained'):
                WorkingLifecycle(self.database,self.stage).retire(self.job,self.attempt)
            self.assertTrue(self.file.exists());self.assertEqual(original.read_bytes(),b'private original intact')
        target_python=os.environ.get('BOOKS_QA_TARGET_PYTHON')
        target_backend=os.environ.get('BOOKS_QA_TARGET_BACKEND')
        if target_python or target_backend:
            self.assertTrue(target_python and target_backend,'both target executable and backend must be explicit')
            self.assertNotEqual(Path(target_python).drive.lower(),Path(sys.executable).drive.lower(),
                'this proof must create old provenance under a different source runtime volume')
            environment=dict(os.environ,BOOKS_STORAGE_RELOCATION_MANIFEST=str(self.descriptor),
                BOOKS_STORAGE_RELOCATION_SHA256=self.descriptor_sha)
            control=self.work/'target-retained-proof.json'
            control.write_text(json.dumps({'database':str(self.database),'stage':str(self.stage),'job':self.job,
                'immutable':immutable}),encoding='utf8')
            code=('import sys,json;sys.path.insert(0,sys.argv[1]);'
                'from pathlib import Path;from storage_relocation_native import configure_from_environment;'
                'from catalog_owner import catalog_lock;from producer_recovery import ProducerRecovery;'
                'from scanner import connect;v=json.loads(Path(sys.argv[2]).read_text("utf8"));'
                'configure_from_environment();'
                'platform=lambda:{"schema":"books-windows-startup-v1","system_volume_serial":"fixture-volume",'
                '"machine_guid":"explicit-private-machine","computer":"fixture","windows_directory":"C:/Windows","uptime_ms":5000};'
                '\nwith catalog_lock(v["database"],{}):\n'
                ' r=ProducerRecovery(v["database"],v["stage"],platform=platform)\n'
                ' with r.protect_retained(v["job"]):pass\n'
                ' with connect(v["database"]) as db:assert list(db.execute("SELECT native,proof FROM producer_recovery_checkpoints WHERE state=?",("isolated_retained",)).fetchone())==v["immutable"]\n'
                'print(json.dumps({"executable":sys.executable,"backend":str(Path(__import__("producer_recovery").__file__).parent),"proof_unchanged":True}))')
            result=subprocess.run([target_python,'-I','-B','-c',code,target_backend,str(control)],
                cwd=target_backend,env=environment,capture_output=True,timeout=20,creationflags=0x08000000)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            proof=json.loads(result.stdout)
            self.assertEqual(Path(proof['executable']),Path(target_python))
            self.assertEqual(Path(proof['backend']),Path(target_backend))
            self.assertTrue(proof['proof_unchanged'])


if __name__=='__main__':unittest.main()
