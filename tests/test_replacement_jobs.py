"""Private SQL/native replacement fixtures; never instantiate a live app or media child."""
import copy
import hashlib
import json
import os
import sqlite3
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from audio_jobs import AudioJobs
from current_audiobook import CurrentAudiobooks
from merge_service import MergeService
from native_io import BoundaryError,DirectoryBoundary,VerifiedFile
from replacement_jobs import Replacements,packed,digest,now
from replacement_retirement import ReplacementRetirement
from scanner import connect

class ReplacementTests(unittest.TestCase):
    def setUp(self):
        area=Path(__file__).resolve().parents[1]/'scratch/replacement-unit-fixtures'
        area.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='owned-',dir=area)
        self.root=Path(self.temp.name);self.library=self.root/'library';self.library.mkdir()
        self.db=self.root/'private.sqlite';self.queue=AudioJobs(self.db,None,lambda m:True,lambda r:True)
        self.store=Replacements(self.db);self.parent_id=str(uuid.uuid4());self.new_id=str(uuid.uuid4());self.candidate=str(uuid.uuid4());self.relation_id=str(uuid.uuid4())
        self.stop=threading.Event();self.sources=[]
        for index in range(40):
            path=self.library/f'{index:02d}.mp3';path.write_bytes(bytes([index+1])*128)
            facts=path.stat();self.sources.append({'path':str(path),'size':128,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fingerprint':{'size':128,'modified':facts.st_mtime_ns}})
        self.old=[self.library/'Book.m4b',self.library/'Book - Chapters.m4b',self.library/'Book - Chapters v2.m4b']
        for index,path in enumerate(self.old):path.write_bytes(bytes([70+index])*2048)
        self.final=self.library/'Book - Final.m4b';self.final.write_bytes(b'new validated fixture'*256)
        self.parent_manifest={'job_id':self.parent_id,'candidate_id':self.candidate,'candidate_revision':1,'root':str(self.library),'destination':str(self.old[0]),'metadata':{'title':'Book','canonical_author':'Author'},'sources':self.sources,'cover':{'id':'cover','sha256':'a'*64,'source_label':'Private selected cover'},'profile':'legacy'}
        self.new_manifest={**copy.deepcopy(self.parent_manifest),'job_id':self.new_id,'destination':str(self.final),'profile':'source-matched','replacement_parent_job_id':self.parent_id,'replacement_id':self.relation_id,'chapters':[]}
        self.parent_output=self.record(self.parent_id,self.old[0]);self.new_output=self.record(self.new_id,self.final)
        self.insert_job(self.parent_manifest,self.parent_output)
        with connect(self.db) as db:
            db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,revision INTEGER,review TEXT)')
            db.execute('CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT)')
            db.execute('CREATE TABLE owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER)')
            db.execute('CREATE TABLE storage_cleanup_jobs(job_id TEXT PRIMARY KEY,output_hash TEXT,state TEXT,reason TEXT,updated TEXT)')
            db.execute('INSERT INTO book_groups VALUES(?,?,?)',(self.candidate,1,'review'))
            db.execute('INSERT INTO candidate_context VALUES(?,?,?)',(self.candidate,1,'context'))
            self.parent_row=self.store.raw_job(db,self.parent_id)
            group=dict(db.execute('SELECT * FROM book_groups').fetchone());context=dict(db.execute('SELECT * FROM candidate_context').fetchone())
        self.repairs=self.root/'chapter-repairs';self.repair_journals={}
        for index,path in enumerate(self.old[1:],1):
            repair_id=str(uuid.uuid4());directory=self.repairs/repair_id;directory.mkdir(parents=True)
            chapters=[{'title':f'Track {n+1:02d}','start_ms':n*1000,'end_ms':(n+1)*1000} for n in range(40)]
            intent={'parent_output':str(self.old[0]),'parent_sha256':self.parent_output['sha256'],'parent_size':self.parent_output['size'],
                    'parent_manifest_sha256':hashlib.sha256(json.dumps(self.parent_manifest,sort_keys=True).encode()).hexdigest(),
                    'candidate_id':self.candidate,'candidate_revision':1,'sources':self.sources,'cover':self.parent_manifest['cover'],
                    'root':str(self.library),'profile':'legacy','mode':'copy existing validated AAC; source-track navigation','destination':str(path),'chapters':chapters}
            record=self.record(self.parent_id,path);validation={'sha256':record['sha256'],'size':record['size'],'chapters':chapters,'cover_sha256':'a'*64,'profile':'legacy'}
            if index==2:validation['chapter_format']={'description':{'entry_size':65,'font_name':'Arial','layout':'Apple QTFF legacy text'}}
            publication={'destination':str(path),'validation':validation,'parent_identity':record['parent_identity']}
            rows=[{'job_id':repair_id,'parent_job_id':self.parent_id,'state':state,'data':data} for state,data in [('intent',intent),('validated',validation),('copying',publication),('publishing',publication),('completed',publication)]]
            journal=directory/'corrected-artifact.jsonl';journal.write_text(''.join(json.dumps(row)+'\n' for row in rows),encoding='utf-8')
            self.repair_journals[str(path)]=(repair_id,journal)
        old=[]
        for path in self.old:
            with DirectoryBoundary(self.library,path.parent) as boundary,VerifiedFile(path) as file:
                old.append({'path':str(path),'size':file.facts()['size'],'sha256':file.sha256(),'facts':file.facts(),'ancestry':boundary.identities,'publication_id':self.parent_id if path==self.old[0] else self.repair_journals[str(path)][0],'journal_sha256':None if path==self.old[0] else hashlib.sha256(self.repair_journals[str(path)][1].read_bytes()).hexdigest()})
        approval={'group_row':group,'context_row':context,'destination':str(self.final),'profile':'source-matched','sources':self.sources,'old_outputs':old,'parent_output':str(self.old[0]),'replacement_manifest':copy.deepcopy(self.new_manifest)}
        self.binding={'id':self.relation_id,'parent_row':self.parent_row,'approval':approval,'previous_publication':{'id':'reviewed-v2','sha256':old[-1]['sha256']},'timestamp':now()}
        self.service=MergeService.__new__(MergeService);self.service.operation_lock=threading.RLock();self.service.inventory=SimpleNamespace(database=self.db,roots={'Audiobooks':str(self.library)});self.service.replacements=self.store
        self.publications=CurrentAudiobooks(self.library,self.repairs,self.store)
        self.retire=ReplacementRetirement(self.store,self.root/'separate-recovery',self.library,self.stop,self.service._replacement_guard,self.publications.protect_former)

    def tearDown(self):
        self.publications.close();self.queue.close();self.temp.cleanup()

    def record(self,id,path):
        with DirectoryBoundary(self.library,path.parent) as boundary,VerifiedFile(path) as file:
            sha=file.sha256();size=file.facts()['size'];tags={'title':'Book','artist':'Author','media_type':'2'}
            return {'job_id':id,'root':str(self.library),'final_path':str(path),'owned_temp':str(path)+'.private','size':size,'sha256':sha,'parent_identity':[list(value) for value in boundary.identities],
                    'validation':{'passed':True,'checks':'Output checks passed','tags':tags,'profile':'source-matched','sha256':sha,'size':size,'chapters':[],
                                  'replacement_media':{'actual_tags':tags,'actual_audio':{'codec_name':'aac','channels':1,'sample_rate':'44100'}}}}

    def insert_job(self,manifest,output):
        journal={'publication_intent':output,'history':[{'stage':'publishing','details':output}]}
        timestamp=now()
        with self.queue._db() as db:
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',(manifest['job_id'],packed(manifest),digest(manifest),'completed','completed',None,packed(journal),packed(output),'',timestamp,timestamp))

    def admit(self):
        with self.queue._db() as db:
            db.execute('BEGIN IMMEDIATE');self.store.admission(db,self.new_manifest,self.binding)
            timestamp=now();db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',(self.new_id,packed(self.new_manifest),digest(self.new_manifest),'completed','completed',None,packed({'publication_intent':self.new_output,'history':[{'stage':'publishing','details':self.new_output}]}),packed(self.new_output),'',timestamp,timestamp))
        return self.store.get(new_job=self.new_id)

    def publish(self):
        relation=self.admit()
        with connect(self.db) as db:
            db.execute('INSERT INTO storage_cleanup_jobs VALUES(?,?,?,?,?)',(self.new_id,self.new_output['sha256'],'completed','',now()))
            stored=dict(db.execute('SELECT * FROM storage_cleanup_jobs').fetchone());row=self.store.raw_job(db,self.new_id)
        return self.store.publish(relation,row,self.new_output,stored,True)

    def test_admission_keeps_parent_and_binds_distinct_job_atomically(self):
        relation=self.admit();self.assertEqual(relation['state'],'queued')
        with connect(self.db) as db:self.assertEqual(self.store.raw_job(db,self.parent_id),self.parent_row)
        self.assertNotEqual(relation['parent_job_id'],relation['replacement_job_id']);self.assertEqual(len(self.store.files(relation['id'])),3)

    def test_changed_parent_refuses_atomic_admission(self):
        with connect(self.db) as db:db.execute('UPDATE audio_jobs SET reason=? WHERE job_id=?',('changed',self.parent_id))
        with self.assertRaises(ValueError):self.admit()
        self.assertEqual(self.store.rows(),[])

    def test_changed_context_refuses_atomic_admission(self):
        with connect(self.db) as db:db.execute('UPDATE candidate_context SET data=?',('different',))
        with self.assertRaises(ValueError):self.admit()
        self.assertEqual(self.store.rows(),[])

    def test_failed_new_job_insert_rolls_back_relation_and_receipts(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.queue._db() as db:
                db.execute('BEGIN IMMEDIATE');self.store.admission(db,self.new_manifest,self.binding)
                db.execute('INSERT INTO audio_jobs(job_id) VALUES(?)',(self.parent_id,))
        self.assertEqual(self.store.rows(),[])

    def test_publication_refuses_incomplete_storage_before_old_disposition(self):
        relation=self.admit()
        with connect(self.db) as db:row=self.store.raw_job(db,self.new_id)
        with self.assertRaises(ValueError):self.store.publish(relation,row,self.new_output,{'job_id':self.new_id,'state':'checking'},True)
        self.assertTrue(all(path.exists() for path in self.old));self.assertEqual(self.store.get(new_job=self.new_id)['state'],'queued')

    def test_publication_ownership_conflict_preserves_former_current(self):
        relation=self.admit()
        with connect(self.db) as db:
            db.execute('INSERT INTO storage_cleanup_jobs VALUES(?,?,?,?,?)',(self.new_id,self.new_output['sha256'],'completed','',now()))
            db.execute('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)',(str(self.final),'other','output','b'*64,1))
            stored=dict(db.execute('SELECT * FROM storage_cleanup_jobs').fetchone());row=self.store.raw_job(db,self.new_id)
        with self.assertRaises(ValueError):self.store.publish(relation,row,self.new_output,stored,True)
        self.assertEqual(self.store.get(new_job=self.new_id)['state'],'queued');self.assertTrue(all(p.exists() for p in self.old))

    def test_raw_six_rows_project_five_distinct_completed_books(self):
        self.publish();jobs=self.queue.status()['jobs']
        for index in range(4):jobs.append({'job_id':str(uuid.uuid4()),'state':'completed','manifest':{'candidate_id':f'other{index}'}})
        visible,count=self.store.projected(jobs);self.assertEqual(count,5);self.assertEqual(len(visible),5)
        self.assertEqual(next(j for j in visible if j['manifest']['candidate_id']==self.candidate)['job_id'],self.new_id)

    def test_actual_state_uses_raw_completion_rows_during_active_replacement(self):
        self.admit();jobs=self.queue.status()['jobs']
        new=next(j for j in jobs if j['job_id']==self.new_id);new.update(state='running',stage='creating',progress=None)
        for index in range(4):jobs.append({'job_id':str(uuid.uuid4()),'state':'completed','stage':'completed','reason':'','manifest':{'candidate_id':f'other{index}','metadata':{'title':'Other'}}})
        status={'state':'Running','queued':0,'completed':5,'failed':0,'current_job_id':self.new_id,'jobs':jobs}
        self.service.jobs=SimpleNamespace(status=lambda:copy.deepcopy(status))
        self.service.cleanup=SimpleNamespace(status=lambda:[],current=None,thread=None)
        self.service.storage_cleanup=SimpleNamespace(status=lambda:[],folder_status=lambda:[]);self.service._post_current=None
        def totals(raw,*_):
            self.assertTrue(any(j['job_id']==self.parent_id and j['state']=='completed' for j in raw))
            count=len({j['manifest']['candidate_id'] for j in raw if j['state']=='completed'})
            return {'approved':5,'converted':count}
        self.service.progress_books=totals
        result=self.service.state();self.assertEqual(result['completed'],5);self.assertEqual(result['converted_total'],5);self.assertEqual(result['current_job_id'],self.new_id)

    def test_new_published_representative_never_falls_back_when_file_missing(self):
        self.publish();self.final.unlink()
        result=self.publications.describe(self.queue.status()['jobs'],self.candidate)
        self.assertEqual(result['state'],'unavailable');self.assertNotIn('path',result);self.assertTrue(self.old[0].exists())

    def test_exact_old_three_retired_with_new_and_forty_sources_preserved(self):
        relation=self.publish();final_hash=hashlib.sha256(self.final.read_bytes()).hexdigest()
        result=self.retire.run(relation);self.assertEqual(result['state'],'completed');self.assertFalse(any(p.exists() for p in self.old))
        self.assertEqual(hashlib.sha256(self.final.read_bytes()).hexdigest(),final_hash)
        self.assertTrue(all(Path(s['path']).exists() for s in self.sources))
        for row in self.store.files(relation['id']):
            recovery=json.loads(row['recovery_json']);self.assertEqual(row['state'],'removed');self.assertEqual(hashlib.sha256(Path(recovery['path']).read_bytes()).hexdigest(),recovery['sha256'])
            from datetime import datetime
            self.assertGreaterEqual((datetime.fromisoformat(recovery['expire_after'])-datetime.fromisoformat(recovery['retired_at'])).total_seconds(),86400)
        with connect(self.db) as db:self.assertEqual(self.store.raw_job(db,self.parent_id),self.parent_row)

    def test_recovery_copies_go_once_the_replacement_is_verified_and_history_still_holds(self):
        # v0.16.8 (Sergei, 2026-10-18): all backups of a verified book are removed, replacement-recovery too.
        relation=self.retire.run(self.publish());rows=self.store.files(relation['id'])
        copies=[Path(json.loads(r['recovery_json'])['path']) for r in rows];self.assertTrue(all(p.exists() for p in copies))
        copies[0].unlink()  # already gone: recorded, never an error
        expected=sum(json.loads(r['recovery_json'])['size'] for r in rows[1:])
        self.assertEqual(self.retire.purge_recoveries(relation),expected)
        self.assertFalse(any(p.exists() for p in copies));self.assertFalse((self.retire.root/relation['id']).exists())
        for row in self.store.files(relation['id']):
            recovery=json.loads(row['recovery_json']);self.assertEqual(row['state'],'removed');self.assertTrue(recovery['purged_at'])
        self.assertEqual(self.retire.purge_recoveries(relation),0,'a rerun removes nothing twice')
        self.assertTrue(self.retire.historical_retired(self.parent_row),'the former book stays history, not a held book')

    def test_changed_replacement_keeps_its_former_output_copies(self):
        relation=self.retire.run(self.publish());self.final.write_bytes(b'changed')
        with self.assertRaises(BoundaryError):self.retire.purge_recoveries(relation)
        self.assertTrue(all(Path(json.loads(r['recovery_json'])['path']).exists() for r in self.store.files(relation['id'])))

    def test_changed_source_blocks_all_old_disposition(self):
        relation=self.publish();Path(self.sources[0]['path']).write_bytes(b'changed source')
        with self.assertRaises(ValueError):self.retire.run(relation)
        self.assertTrue(all(p.exists() for p in self.old))

    def test_changed_new_current_blocks_all_old_disposition(self):
        relation=self.publish();self.final.write_bytes(b'wrong current')
        with self.assertRaises(ValueError):self.retire.run(relation)
        self.assertTrue(all(p.exists() for p in self.old))

    def test_old_hardlink_substitution_is_refused(self):
        relation=self.publish();sentinel=self.library/'unrelated.m4b';sentinel.write_bytes(self.old[0].read_bytes());self.old[0].unlink();os.link(sentinel,self.old[0])
        before=sentinel.read_bytes()
        with self.assertRaises(ValueError):self.retire.run(relation)
        self.assertEqual(sentinel.read_bytes(),before);self.assertTrue(self.old[0].exists())

    def test_stale_receipt_cas_cannot_regress_terminal_state(self):
        relation=self.publish();row=self.store.files(relation['id'])[0]
        with connect(self.db) as db:db.execute('UPDATE audiobook_replacement_retirements SET state=? WHERE original_path=?',('removed',row['original_path']))
        with self.assertRaises(ValueError):self.store.file_transition(row,'copied',{'unknown':'recovery'})
        self.assertEqual(next(r for r in self.store.files(relation['id']) if r['original_path']==row['original_path'])['state'],'removed')

    def test_base_missing_without_durable_intent_is_not_historical_success(self):
        self.publish();self.old[0].unlink()
        self.assertFalse(self.retire.historical_retired(self.parent_row))

    def test_partial_base_intent_absence_preserves_history_before_overall_completion(self):
        relation=self.publish();row=next(r for r in self.store.files(relation['id']) if r['original_path']==str(self.old[0]));proof=json.loads(row['provenance_json'])
        destination=self.retire.root/relation['id']
        with DirectoryBoundary(self.retire.root.anchor,destination,create=True) as boundary,VerifiedFile(self.old[0],delete=True) as original:
            row=self.retire._copy(relation,row,original,proof,destination,boundary)
            row=self.store.file_transition(row,'retirement_intended');relation=self.store.transition(relation,'retiring');original.dispose()
        self.assertFalse(self.old[0].exists());self.assertTrue(self.old[1].exists());self.assertTrue(self.retire.historical_retired(self.parent_row))
        result=self.retire.run(relation);self.assertEqual(result['state'],'completed')

    def test_stop_before_copy_never_retires_and_fresh_resume_is_guarded(self):
        relation=self.publish();self.stop.set()
        with self.assertRaises(InterruptedError):self.retire.run(relation)
        self.assertTrue(all(p.exists() for p in self.old));self.stop.clear()
        result=self.retire.run(self.store.get(new_job=self.new_id));self.assertEqual(result['state'],'completed')

    def test_native_disposition_never_replayed_after_receipt_write_failure(self):
        relation=self.publish();original=self.store.file_transition;calls=[]
        def fail_after(row,state,recovery=None):
            if state=='removed' and not calls:calls.append(row['original_path']);raise sqlite3.OperationalError('injected unclassified receipt failure')
            return original(row,state,recovery)
        with patch.object(self.store,'file_transition',side_effect=fail_after):
            with self.assertRaises(sqlite3.OperationalError):self.retire.run(relation)
        self.assertFalse(Path(calls[0]).exists())
        # Explicit guarded resume reconciles exact durable intent/absence, not a second dispose.
        with patch.object(VerifiedFile,'dispose',autospec=True,side_effect=VerifiedFile.dispose) as dispose:
            result=self.retire.run(self.store.get(new_job=self.new_id))
        self.assertEqual(result['state'],'completed');self.assertEqual(dispose.call_count,2)

    def test_wrong_recovery_for_partial_absence_refuses_history(self):
        relation=self.publish();row=next(r for r in self.store.files(relation['id']) if r['original_path']==str(self.old[0]));proof=json.loads(row['provenance_json'])
        destination=self.retire.root/relation['id']
        with DirectoryBoundary(self.retire.root.anchor,destination,create=True) as boundary,VerifiedFile(self.old[0],delete=True) as original:
            row=self.retire._copy(relation,row,original,proof,destination,boundary);row=self.store.file_transition(row,'retirement_intended');self.store.transition(relation,'retiring');original.dispose()
        Path(json.loads(row['recovery_json'])['path']).write_bytes(b'changed recovery')
        self.assertFalse(self.retire.historical_retired(self.parent_row))

    def test_recovery_native_guard_spans_old_close_absence_and_removed_cas(self):
        relation=self.publish();checked=[];actual_exit=VerifiedFile.__exit__;actual_absent=self.retire._absent;actual_transition=self.store.file_transition
        def protected_attempt(path,phase):
            row=next(r for r in self.store.files(relation['id']) if r['original_path']==str(path))
            if not row['recovery_json'] or row['state'] not in {'retirement_intended','removed'}:return
            recovery=json.loads(row['recovery_json']);backup=Path(recovery['path']);before=backup.read_bytes()
            with self.assertRaises(OSError):backup.write_bytes(b'forbidden change')
            with self.assertRaises(OSError):backup.rename(backup.with_suffix('.moved'))
            with self.assertRaises(OSError):backup.unlink()
            self.assertEqual(backup.read_bytes(),before);self.assertEqual(hashlib.sha256(before).hexdigest(),recovery['sha256']);checked.append(phase)
        def close(file,*args):
            try:
                if file.delete and file.path in self.old:protected_attempt(file.path,'before old close')
            finally:result=actual_exit(file,*args)
            if file.delete and file.path in self.old:protected_attempt(file.path,'after old close')
            return result
        def absent(path):protected_attempt(path,'absence');return actual_absent(path)
        def transition(row,state,recovery=None):
            if state=='removed':protected_attempt(Path(row['original_path']),'removed CAS')
            return actual_transition(row,state,recovery)
        with patch.object(VerifiedFile,'__exit__',new=close),patch.object(self.retire,'_absent',side_effect=absent),patch.object(self.store,'file_transition',side_effect=transition):self.retire.run(relation)
        for phase in ['before old close','after old close','absence','removed CAS']:self.assertEqual(checked.count(phase),3)

    def test_copy_birth_native_identity_swap_is_refused_before_any_disposal(self):
        relation=self.publish();actual_enter=VerifiedFile.__enter__;swapped=[]
        def enter(file):
            if file.writable and file.path.is_relative_to(self.retire.root) and file.path.exists() and file.path.stat().st_size==0 and not swapped:
                # Ordinary pathname rename is rightly refused under held ancestry.
                # Exercise the birth gap with an exact DELETE-capable private leaf handle,
                # using the same no-replace, same-parent native rename shape as publication.
                import ctypes
                from ctypes import wintypes
                nt=ctypes.WinDLL('ntdll',use_last_error=True);encoded=file.path.with_suffix('.born').name.encode('utf-16-le')
                class Rename(ctypes.Structure):
                    _fields_=[('replace',wintypes.BOOLEAN),('root',wintypes.HANDLE),('length',wintypes.DWORD),('name',wintypes.WCHAR*(len(encoded)//2+1))]
                class Status(ctypes.Structure):_fields_=[('status',ctypes.c_void_p),('information',ctypes.c_size_t)]
                nt.NtSetInformationFile.argtypes=[wintypes.HANDLE,ctypes.POINTER(Status),ctypes.c_void_p,wintypes.ULONG,ctypes.c_int];nt.NtSetInformationFile.restype=wintypes.LONG
                rename=Rename();rename.replace=False;rename.root=None;rename.length=len(encoded)
                ctypes.memmove(ctypes.addressof(rename)+Rename.name.offset,encoded,len(encoded))
                # Native original handle is kept alive until a distinct replacement exists.
                born=VerifiedFile(file.path,delete=True);actual_enter(born)
                try:
                    status=Status();self.assertGreaterEqual(nt.NtSetInformationFile(born.handle,ctypes.byref(status),ctypes.byref(rename),ctypes.sizeof(rename),10),0)
                    file.path.write_bytes(b'');swapped.append(str(file.path))
                finally:born.__exit__(None,None,None)
            return actual_enter(file)
        with patch.object(VerifiedFile,'__enter__',new=enter):
            with self.assertRaises(ValueError):self.retire.run(relation)
        self.assertEqual(len(swapped),1);self.assertTrue(all(p.exists() for p in self.old));self.assertTrue(all(r['state']=='waiting' for r in self.store.files(relation['id'])))

    def test_actual_audio_pause_resume_preserves_retired_completed_history(self):
        self.retire.run(self.publish())
        self.queue.historical_retirement=self.retire.historical_retired;self.retire.stop=self.queue._stop
        def actual_output(record):
            path=Path(record['final_path'])
            return path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
        self.queue.output_validator=actual_output
        self.queue.pause();self.assertTrue(self.queue._stop.is_set());self.queue.resume()
        self.queue._thread.join(3);self.assertFalse(self.queue._thread.is_alive())
        with connect(self.db) as db:self.assertEqual(self.store.raw_job(db,self.parent_id),self.parent_row)

    def test_paused_history_proof_preserves_partial_base_retirement(self):
        relation=self.publish();row=next(r for r in self.store.files(relation['id']) if r['original_path']==str(self.old[0]));proof=json.loads(row['provenance_json']);destination=self.retire.root/relation['id']
        with DirectoryBoundary(self.retire.root.anchor,destination,create=True) as boundary,VerifiedFile(self.old[0],delete=True) as original:
            row=self.retire._copy(relation,row,original,proof,destination,boundary);self.store.file_transition(row,'retirement_intended');self.store.transition(relation,'retiring');original.dispose()
        self.stop.set();self.assertTrue(self.retire.historical_retired(self.parent_row));self.assertTrue(self.stop.is_set())
        # A routine caller's own stop interrupts the read-only proof; it is raised, never "not history".
        routine=threading.Event();routine.set()
        with self.assertRaises(InterruptedError):self.retire.historical_retired(self.parent_row,stop=routine)

    def test_swapped_valid_other_recovery_is_refused_before_old_disposition(self):
        relation=self.publish();destination=self.retire.root/relation['id'];rows=self.store.files(relation['id']);copied=[]
        with DirectoryBoundary(self.retire.root.anchor,destination,create=True) as boundary:
            for row in rows[:2]:
                proof=json.loads(row['provenance_json'])
                with VerifiedFile(row['original_path']) as original:copied.append(self.retire._copy(relation,row,original,proof,destination,boundary))
        with connect(self.db) as db:db.execute('UPDATE audiobook_replacement_retirements SET recovery_json=? WHERE original_path=?',(copied[1]['recovery_json'],copied[0]['original_path']))
        with self.assertRaises(ValueError):self.retire.run(relation)
        self.assertTrue(all(p.exists() for p in self.old))

    def test_valid_file_wrong_parent_relation_is_unavailable_for_every_consumer(self):
        relation=self.publish()
        with connect(self.db) as db:db.execute('UPDATE audiobook_replacements SET parent_job_id=? WHERE id=?',(str(uuid.uuid4()),relation['id']))
        corrupt=self.store.get(new_job=self.new_id)
        self.assertFalse(self.store.structural_guard(corrupt));self.assertEqual(self.publications.describe(self.queue.status()['jobs'],self.candidate)['state'],'unavailable')
        with self.assertRaises(ValueError):self.retire.run(corrupt)
        self.assertTrue(all(p.exists() for p in self.old))

    def test_completed_manifest_source_drift_cannot_be_current_or_retire_old(self):
        relation=self.publish()
        changed=copy.deepcopy(self.new_manifest);changed['sources'][0]['sha256']='f'*64
        with connect(self.db) as db:db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=? WHERE job_id=?',(packed(changed),digest(changed),self.new_id))
        self.assertFalse(self.store.structural_guard(relation));self.assertEqual(self.publications.describe(self.queue.status()['jobs'],self.candidate)['state'],'unavailable')
        with self.assertRaises(ValueError):self.retire.run(relation)
        self.assertTrue(all(p.exists() for p in self.old))

    def test_manifest_hash_drift_is_refused_even_when_output_is_valid(self):
        relation=self.publish()
        with connect(self.db) as db:db.execute('UPDATE audio_jobs SET manifest_hash=? WHERE job_id=?',('f'*64,self.new_id))
        self.assertFalse(self.store.structural_guard(relation));self.assertEqual(self.publications.describe(self.queue.status()['jobs'],self.candidate)['state'],'unavailable')

    def test_completed_relation_does_not_bypass_staging_cleanup(self):
        relation=self.publish()
        with connect(self.db) as db:db.execute('UPDATE storage_cleanup_jobs SET state=? WHERE job_id=?',('needs_attention',self.new_id))
        self.assertFalse(self.store.structural_guard(relation));self.assertEqual(self.publications.describe(self.queue.status()['jobs'],self.candidate)['state'],'unavailable')

    def test_verified_current_inspector_tags_cover_and_folder_target_agree(self):
        self.publish();self.service.publications=self.publications;self.service.jobs=self.queue
        row={'id':self.candidate,'revision':1,'members':[{'path':s['path'],'metadata':{'tags':{}}} for s in self.sources],
             'metadata':{},'audiobook_ready':True,'metadata_approved':True,'review':self.parent_manifest['metadata'],'selected_cover':self.parent_manifest['cover'],'cover_choices':[]}
        self.service.reviews=SimpleNamespace(_row=lambda *_:row,enrich=lambda value:value)
        self.service.cleanup=SimpleNamespace(status=lambda _:None)
        import time
        deadline=time.monotonic()+5
        while self.publications.describe(self.queue.status()['jobs'],self.candidate)['state']=='verifying' and time.monotonic()<deadline:time.sleep(.01)
        current=self.service.current_audiobook(self.candidate);self.assertEqual(current['state'],'verified');self.assertEqual(current['path'],str(self.final))
        inspected=self.service.inspect('Audiobooks','candidates',self.candidate)['inspector'];created=inspected['sections'][-1]
        self.assertEqual(created['heading'],'Current audiobook metadata');self.assertEqual(created['path'],str(self.final));self.assertEqual(created['raw_tags'],self.new_output['validation']['tags']);self.assertEqual(created['cover']['id'],'cover')
        with patch.object(self.service,'dispatch_folder') as folder:self.service.open_folder('Audiobooks','candidates',self.candidate,'output')
        folder.assert_called_once_with(str(self.library))

    def test_current_cache_invalidates_after_native_file_change_without_old_fallback(self):
        self.publish();import time
        deadline=time.monotonic()+5
        while self.publications.describe(self.queue.status()['jobs'],self.candidate)['state']=='verifying' and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(self.publications.describe(self.queue.status()['jobs'],self.candidate)['state'],'verified')
        self.final.write_bytes(b'changed current bytes')
        self.assertEqual(self.publications.describe(self.queue.status()['jobs'],self.candidate)['state'],'unavailable');self.assertTrue(self.old[0].exists())

    def test_ready_replacement_requires_current_relation_and_normal_cleanup(self):
        from conversion_progress import completed_book
        relation=self.publish();job=next(j for j in self.queue.status()['jobs'] if j['job_id']==self.new_id)
        row={'id':self.candidate,'revision':1,'review':self.parent_manifest['metadata'],'preview':{'path':str(self.old[0])}}
        keys=[s['path'] for s in self.sources];ctx={'included':keys,'track_order':keys,'cover_id':'cover','source_hashes':{s['path']:{'size':s['size'],'sha256':s['sha256'],'modified':s.get('modified')} for s in self.sources}}
        self.assertTrue(completed_book(row,ctx,job,None,{'state':'completed'},None,True,lambda p:p,{'source-matched'},relation))
        self.assertFalse(completed_book(row,ctx,job,None,{'state':'checking'},None,True,lambda p:p,{'source-matched'},relation))
        self.assertFalse(completed_book(row,ctx,job,None,{'state':'completed'},None,True,lambda p:p,{'source-matched'},None))

    def test_completed_not_current_keeps_original_completion_representative(self):
        relation=self.admit();jobs=self.queue.status()['jobs'];representative,binding=self.store.representative(jobs,self.candidate)
        self.assertEqual(binding['state'],'queued');self.assertEqual(representative['job_id'],self.parent_id)
        visible,count=self.store.projected(jobs);self.assertEqual(count,1);self.assertEqual(visible[0]['job_id'],self.parent_id)

    def large_old_fixture(self):
        path=self.old[2];path.write_bytes(b'old distinct recovery bytes'*140000)
        with DirectoryBoundary(self.library,path.parent) as boundary,VerifiedFile(path) as file:
            proof=next(v for v in self.binding['approval']['old_outputs'] if v['path']==str(path))
            proof.update(size=file.facts()['size'],sha256=file.sha256(),facts=file.facts(),ancestry=boundary.identities)
        journal=self.repair_journals[str(path)][1];rows=[json.loads(line) for line in journal.read_text().splitlines()]
        rows[1]['data'].update(size=proof['size'],sha256=proof['sha256'])
        for row in rows[2:]:row['data']['validation']=copy.deepcopy(rows[1]['data'])
        journal.write_text(''.join(json.dumps(row)+'\n' for row in rows),encoding='utf-8');proof['journal_sha256']=hashlib.sha256(journal.read_bytes()).hexdigest()
        return path

    def interrupt_partial_copy(self):
        from replacement_retirement import kernel
        path=self.large_old_fixture();relation=self.publish();actual=kernel.WriteFile;calls=[]
        def write(*args):
            result=actual(*args);calls.append(args[2]);self.stop.set();return result
        with patch.object(kernel,'WriteFile',write):
            with self.assertRaises(InterruptedError):self.retire.run(relation)
        self.assertEqual(len(calls),1);self.assertTrue(all(p.exists() for p in self.old))
        row=next(r for r in self.store.files(relation['id']) if r['original_path']==str(path));receipt=json.loads(row['recovery_json'])
        backup=Path(receipt['path']);self.assertTrue(receipt['copy_pending']);self.assertGreater(backup.stat().st_size,0);self.assertLess(backup.stat().st_size,path.stat().st_size)
        self.assertEqual(backup.read_bytes(),path.read_bytes()[:backup.stat().st_size]);self.stop.clear()
        return relation,backup

    def test_actual_partial_copy_stop_resumes_exact_native_prefix(self):
        relation,backup=self.interrupt_partial_copy();result=self.retire.run(self.store.get(new_job=self.new_id))
        self.assertEqual(result['state'],'completed');self.assertFalse(any(p.exists() for p in self.old));self.assertTrue(backup.exists());self.assertTrue(self.final.exists())

    def test_corrupt_interrupted_copy_prefix_refuses_all_disposition(self):
        relation,backup=self.interrupt_partial_copy()
        with backup.open('r+b') as stream:stream.write(b'wrong prefix')
        with self.assertRaises(ValueError):self.retire.run(self.store.get(new_job=self.new_id))
        self.assertTrue(all(p.exists() for p in self.old));self.assertTrue(self.final.exists())

    def test_stop_after_intent_before_native_disposition_preserves_old_files(self):
        relation=self.publish();actual=self.store.file_transition;dispose=VerifiedFile.dispose
        def transition(row,state,*args,**kwargs):
            result=actual(row,state,*args,**kwargs)
            if state=='retirement_intended':self.stop.set()
            return result
        with patch.object(self.store,'file_transition',transition),patch.object(VerifiedFile,'dispose',autospec=True,side_effect=dispose) as called:
            with self.assertRaises(InterruptedError):self.retire.run(relation)
            called.assert_not_called()
        self.assertTrue(all(p.exists() for p in self.old));self.stop.clear()
        self.assertEqual(self.retire.run(self.store.get(new_job=self.new_id))['state'],'completed')

    def test_changed_authoritative_repair_journal_refuses_old_disposition(self):
        relation=self.publish();journal=self.repair_journals[str(self.old[2])][1]
        rows=[json.loads(line) for line in journal.read_text().splitlines()];rows[0]['data']['parent_sha256']='f'*64
        journal.write_text(''.join(json.dumps(row)+'\n' for row in rows),encoding='utf-8')
        with patch.object(VerifiedFile,'dispose',autospec=True) as disposal:
            with self.assertRaises(ValueError):self.retire.run(relation)
            disposal.assert_not_called()
        self.assertTrue(all(p.exists() for p in self.old))

    def test_fake_old_publication_id_refuses_self_consistent_db_proof(self):
        relation=self.publish();approval=json.loads(relation['approval_json']);proof=approval['old_outputs'][1];proof['publication_id']=str(uuid.uuid4())
        with connect(self.db) as db:
            db.execute('UPDATE audiobook_replacements SET approval_json=? WHERE id=?',(packed(approval),relation['id']))
            db.execute('UPDATE audiobook_replacement_retirements SET provenance_json=? WHERE original_path=?',(packed(proof),proof['path']))
        with self.assertRaises(ValueError):self.retire.run(self.store.get(new_job=self.new_id))
        self.assertTrue(all(p.exists() for p in self.old))

    def test_wrong_derived_old_path_refuses_other_valid_file(self):
        relation=self.publish();approval=json.loads(relation['approval_json']);proof=approval['old_outputs'][1];other=self.library/'Other valid.m4b';other.write_bytes(self.old[1].read_bytes());old_path=proof['path'];proof['path']=str(other)
        with connect(self.db) as db:
            db.execute('UPDATE audiobook_replacements SET approval_json=? WHERE id=?',(packed(approval),relation['id']))
            db.execute('UPDATE audiobook_replacement_retirements SET original_path=?,provenance_json=? WHERE original_path=?',(str(other),packed(proof),old_path))
        with self.assertRaises(ValueError):self.retire.run(self.store.get(new_job=self.new_id))
        self.assertTrue(all(p.exists() for p in self.old));self.assertTrue(other.exists())

    def test_merge_resume_drains_completed_paused_postprocessing_without_reencode(self):
        relation=self.publish();self.stop.set();self.queue._stop=self.stop;self.queue.pending_postprocessing=self.service._pending_replacement_postprocessing
        self.service.jobs=self.queue;self.service._no_scan=lambda:None;self.service._prune_completed=lambda _,**__:None
        self.service.cleanup=SimpleNamespace(thread=None,_rows=lambda *_:[])
        self.queue.postprocessing=lambda _:self.retire.run(self.store.get(new_job=self.new_id))
        self.queue.historical_retirement=self.retire.historical_retired;self.queue.runner=lambda *_:self.fail('Completed replacement must not reencode')
        self.service.state=lambda:self.queue.status()
        from automatic_processing import AutomaticProcessing
        auto=AutomaticProcessing.__new__(AutomaticProcessing);auto.merge=self.service;auto.stop_event=threading.Event();auto.current=None;auto.next_retry_at=None
        auto.inventory=SimpleNamespace(worker=None,stop=lambda:None);updates=[]
        auto._run_row=lambda:{'phase':'research','checkpoint':packed({'pending':[],'done':[]})}
        auto._update=lambda id,**values:updates.append(values)
        # The same saved-work branch used by normal automatic Start must resume queue=0 postprocessing.
        self.service.state=lambda:self.queue.status()|{'postprocessing_pending':bool(self.service._pending_replacement_postprocessing())}
        auto._work('private-automatic-run');self.queue._thread.join(10);self.assertFalse(self.queue._thread.is_alive())
        self.assertTrue(any(update.get('state')=='Completed' for update in updates))
        self.assertEqual(self.store.get(new_job=self.new_id)['state'],'completed')
        with connect(self.db) as db:self.assertEqual(self.store.raw_job(db,self.parent_id),self.parent_row)

if __name__=='__main__':unittest.main()
