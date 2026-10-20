"""Native worker for already planned, exclusively leased output relocations.

No enrollment, configuration, discovery, owner acquisition or process control.
The caller supplies the reviewed operation lease, durable SQLite commit policy,
actual media verifier and transactional consumer invalidation. Unknown artifacts
and unsupported durability remain retained, never adopted/deleted by pathname.
"""
import contextlib
import copy
import ctypes
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading

import publication_locations as locations
from native_io import BoundaryError,DirectoryBoundary,FileInfo,VerifiedFile,kernel,ordinary,publish_no_replace
from source_cleanup import single_stream


class MigrationRefused(ValueError):
    def __init__(self,code,message):super().__init__(message);self.code=code


def packed(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(packed(value).encode('utf-8')).hexdigest()
def need(value,code,message):
    if not value:raise MigrationRefused(code,message)


def row(db,sql,args=()):
    cursor=db.execute(sql,args);value=cursor.fetchone()
    return dict(zip([column[0] for column in cursor.description],tuple(value))) if value is not None else None


def native_identity(value):return isinstance(value,list) and len(value)==3 and all(type(i) is int and i>=0 for i in value) and value[0]>0 and any(value[1:])


class MigrationWorker:
    def __init__(self,database,*,operation_lease,media_verify,invalidate,fault=None,stop=None):
        self.database=ordinary(database)
        need(callable(operation_lease) and callable(media_verify) and callable(invalidate),'missing_migration_capability','Migration lease, media verifier and invalidation callbacks are required')
        self.operation_lease=operation_lease;self.media_verify=media_verify;self.invalidate=invalidate
        self.fault=fault;self.stop=stop or threading.Event()

    def _check(self):
        if self.stop.is_set():raise InterruptedError('Output migration stopped; owned copies retained')

    def _catalog_identity(self):
        handle=kernel.CreateFileW(str(self.database),0x80,7,None,3,0x00200000,None)
        need(handle!=ctypes.c_void_p(-1).value,'catalog_identity_unavailable','Cannot inspect the supplied catalog identity')
        try:
            info=FileInfo()
            need(bool(kernel.GetFileInformationByHandle(handle,ctypes.byref(info))) and not info.attributes&(0x400|0x10) and info.links==1,'catalog_identity_unavailable','Catalog is not a unique ordinary file')
            return [int(info.volume),int(info.index_high),int(info.index_low)]
        finally:kernel.CloseHandle(handle)

    def _fault(self,point):
        if self.fault:self.fault(point,{'publication_id':self.publication_id,'stage':self.current['stage'],'generation':self.current['generation']})

    def _read_row(self):
        current=row(self.db,'SELECT * FROM output_relocations WHERE publication_id=?',(self.publication_id,))
        need(current is not None,'relocation_not_planned','Only an already planned publication can migrate')
        job=row(self.db,'SELECT * FROM audio_jobs WHERE job_id=?',(current['job_id'],))
        original=json.loads(current['original_output_json'])
        locations.resolve(self.db,job,current['publication_kind'],original)
        return current

    def _prior(self,stage):
        event=row(self.db,"SELECT * FROM migration_events WHERE publication_id=? AND outcome='transition' AND to_stage=? ORDER BY event_id DESC LIMIT 1",(self.publication_id,stage))
        need(event is not None,'missing_phase_proof','Required durable migration phase is missing')
        return json.loads(event['proof_json'])

    def _begin(self):
        need(not self.db.in_transaction,'unexpected_catalog_transaction','Migration requires its own explicit stage transaction')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            actual=self._read_row()
            need(actual==self.current and self.lease['generation_guard'](self.publication_id,self.current['generation']) is True,'relocation_generation_changed','Migration lease/generation changed')
        except BaseException:self.db.rollback();raise

    def _durable(self):
        proof=self.lease['durable_commit'](self.db)
        need(not self.db.in_transaction,'catalog_not_durable','Commit callback did not commit the stage')
        actual=self._read_row();latest=row(self.db,'SELECT * FROM migration_events WHERE publication_id=? ORDER BY event_id DESC LIMIT 1',(self.publication_id,))
        journal=str(self.db.execute('PRAGMA journal_mode').fetchone()[0]).lower();synchronous=int(self.db.execute('PRAGMA synchronous').fetchone()[0])
        need(journal in {'wal','delete','truncate','persist'} and synchronous in {2,3},'catalog_not_durable','SQLite durability policy requires a persistent journal and FULL/EXTRA synchronization')
        need(isinstance(proof,dict) and proof.get('schema')=='books-migration-durable-commit-v1' and proof.get('committed') is True and proof.get('publication_id')==self.publication_id and proof.get('generation')==actual['generation'] and proof.get('relocation_sha256')==digest(actual) and proof.get('event_sha256')==digest(latest) and proof.get('journal_mode')==journal and proof.get('synchronous')==synchronous and proof.get('owner_invocation_id')==self.lease['native_owner']['invocation_id'],'catalog_not_durable','Commit policy/readback proof does not match the exact durable stage')
        self.current=actual

    def _advance(self,stage,proof,transaction=False):
        if not transaction:self._begin()
        try:
            locations.transition(self.db,self.publication_id,self.current['generation'],stage,proof)
            if stage=='location_committed':
                effective={key:copy.deepcopy(proof[key]) for key in ('root','final_path','sha256','size','identity','parent_identity')}
                self.invalidate(self.db,copy.deepcopy(self.original),effective)
                need(self.db.in_transaction,'invalidation_committed_early','Consumer invalidation must remain in the same stage transaction')
            self._fault('before_'+stage+'_commit');self._durable()
        except BaseException:
            if self.db.in_transaction:self.db.rollback()
            raise
        self._fault('after_'+stage)

    def _event(self,outcome,proof):
        self._begin()
        try:
            self.db.execute('INSERT INTO migration_events(migration_id,publication_id,generation,from_stage,to_stage,outcome,proof_json,error,created_utc) VALUES(?,?,?,?,?,?,?,?,?)',
                (self.current['migration_id'],self.publication_id,self.current['generation'],self.current['stage'],self.current['stage'],outcome,packed(proof),None,locations._now()))
            self._durable()
        except BaseException:
            if self.db.in_transaction:self.db.rollback()
            raise

    def _common(self,schema):
        return {'schema':schema,'publication_id':self.publication_id,'immutable_receipt_sha256':self.current['immutable_receipt_sha256'],'generation':self.current['generation']}

    def _file_proof(self,file,path,boundary):
        self._check();single_stream(path);facts=file.facts()
        need(facts['links']==1,'file_alias','Migration requires a unique ordinary file')
        hash=hashlib.sha256()
        for block in file.chunks():self._check();hash.update(block)
        sha=hash.hexdigest();self._check();boundary.revalidate()
        need(facts['size']==self.original['size'] and sha==self.original['sha256'],'output_content_changed','Full held output hash/size differs from the immutable publication')
        return {'root':str(boundary.root),'final_path':str(path),'sha256':sha,'full_content_sha256':sha,'size':facts['size'],'identity':facts['identity'],'parent_identity':json.loads(packed(boundary.identities))}

    @contextlib.contextmanager
    def _original_held(self,delete=False):
        with DirectoryBoundary(self.original['root'],self.old.parent) as boundary,VerifiedFile(self.old,delete=delete) as file:
            proof=self._file_proof(file,self.old,boundary)
            need(proof['parent_identity']==self.original['parent_identity'],'original_ancestry_changed','Original publication ancestry changed')
            if self.current['stage']!='planned':
                intent=self._prior('copy_intent')
                need(proof['identity']==intent['original_location']['identity'],'original_identity_changed','Original publication native identity changed')
            yield file,proof,boundary

    @contextlib.contextmanager
    def _target_boundary(self):
        # Opt in at the initial native open. Never reopen a protected readonly
        # parent for write access or relax its existing sharing contract.
        boundary=DirectoryBoundary(self.current['target_root'],self.final.parent,create=True,writable_parent=True)
        try:boundary.__enter__()
        except BoundaryError as error:raise MigrationRefused('destination_parent_capability_unavailable','The destination parent cannot retain its required native write capability; original output retained: '+str(error)) from error
        try:yield boundary
        finally:boundary.__exit__(None,None,None)

    def _root_alias(self,old_boundary,target_boundary):
        find=lambda boundary:next(tuple(identity[1:]) for identity in boundary.identities if ordinary(identity[0])==boundary.root)
        need(find(old_boundary)!=find(target_boundary),'output_root_alias','Source and destination output roots alias one directory')

    def _temp_scope(self,boundary):
        return {'root':self.current['target_root'],'temporary_path':str(self.temporary),'parent_identity':json.loads(packed(boundary.identities))}

    @contextlib.contextmanager
    def _created_file(self):
        # CREATE_NEW and OPEN_REPARSE_POINT; no pathname overwrite/truncate.
        handle=kernel.CreateFileW(str(self.temporary),0xC0000081,1,None,1,0x00200000,None)
        if handle==ctypes.c_void_p(-1).value:raise BoundaryError('Exclusive migration temporary creation refused')
        file=VerifiedFile(self.temporary,writable=True);file.handle=handle;file.info=FileInfo()
        try:
            need(bool(kernel.GetFileInformationByHandle(handle,ctypes.byref(file.info))) and not file.info.attributes&(0x400|0x10) and file.info.links==1,'temporary_creation_unproven','Cannot capture exact created temporary identity')
            self._fault('created_before_journal')
            yield file
        finally:file.__exit__(None,None,None)

    def _created_receipt(self):
        event=row(self.db,"SELECT proof_json FROM migration_events WHERE publication_id=? AND outcome='artifact_created' ORDER BY event_id DESC LIMIT 1",(self.publication_id,))
        return json.loads(event['proof_json']) if event else None

    def _write_copy(self,source,temporary):
        # Only a native identity already journaled by this publication reaches
        # this truncation. A creation-before-journal gap never reaches it.
        kernel.SetFilePointerEx.argtypes=[W.HANDLE,ctypes.c_longlong,ctypes.c_void_p,W.DWORD];kernel.SetFilePointerEx.restype=W.BOOL
        kernel.SetEndOfFile.argtypes=[W.HANDLE];kernel.SetEndOfFile.restype=W.BOOL
        need(bool(kernel.SetFilePointerEx(temporary.handle,0,None,0)) and bool(kernel.SetEndOfFile(temporary.handle)),'temporary_write_refused','Cannot reset the exact owned temporary')
        self._fault('after_owned_truncate')
        kernel.WriteFile.argtypes=[W.HANDLE,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD),ctypes.c_void_p];kernel.WriteFile.restype=W.BOOL
        for block in source.chunks():
            self._check();at=0
            while at<len(block):
                remaining=block[at:];buffer=ctypes.create_string_buffer(remaining);written=W.DWORD()
                need(bool(kernel.WriteFile(temporary.handle,buffer,len(remaining),ctypes.byref(written),None)) and 0<written.value<=len(remaining),'temporary_write_refused','Owned copy write did not complete')
                at+=written.value
            self._fault('copy_chunk')
        temporary.flush()
        need(bool(kernel.GetFileInformationByHandle(temporary.handle,ctypes.byref(temporary.info))),'temporary_write_refused','Cannot inspect flushed owned temporary')
        self._fault('after_copy_flush')

    def _media(self,path,source_proof,destination_proof):
        self._check()
        try:supplied=self.media_verify(path,copy.deepcopy(self.original),self.stop)
        except InterruptedError:raise
        except Exception as error:raise MigrationRefused('media_verification_unavailable','Fresh media verification refused: '+str(error)) from error
        need(isinstance(supplied,dict) and supplied.get('kind') in {'sealed_media_proof_reused','fresh_full_media_verified'} and supplied.get('supported_validation_contract') in {'books-audio-output-v1','books-authorized-chapter-output-v1'} and supplied.get('passed') is True,'media_verification_unproven','A typed supported full-content media proof is required')
        need(supplied.get('immutable_receipt_sha256')==digest(self.original) and supplied.get('validation_sha256')==digest(self.original.get('validation')) and supplied.get('full_content_sha256')==self.original['sha256'] and type(supplied.get('size')) is int and supplied['size']==self.original['size'] and isinstance(supplied.get('details'),dict) and bool(supplied['details']),'media_verification_unproven','Media proof does not seal this immutable publication and full content')
        if self.current['publication_kind'] in {'Chapters','Chaptersv2'}:
            accepted=json.loads(self.current['accepted_routing_json']);journal=accepted.get('repair_journal_sha256')
            need(isinstance(journal,str) and len(journal)==64 and supplied.get('authoritative_repair_journal_sha256')==journal and supplied['supported_validation_contract']=='books-authorized-chapter-output-v1','repair_provenance_unproven','Authoritative chapter journal proof is required')
        need(source_proof['sha256']==destination_proof['sha256']==self.original['sha256'] and source_proof['size']==destination_proof['size']==self.original['size'],'media_verification_unproven','Fresh source/destination content proofs differ')
        return dict(copy.deepcopy(supplied),source_full_hash=copy.deepcopy(source_proof),destination_full_hash=copy.deepcopy(destination_proof),
            original_manifest_hash=self.current['original_manifest_hash'],original_publication_intent_sha256=self.current['original_publication_intent_sha256'])

    def _flush_parent(self,boundary):
        boundary.revalidate()
        proof={'schema':'books-directory-flush-v1','supported':False,'identity':list(boundary.identities[-1]) if boundary.identities else None,
            'required_access':'GENERIC_WRITE|LIST_DIRECTORY|READ_ATTRIBUTES','filesystem_support':'unproven','same_retained_parent_handle':False}
        if getattr(boundary,'writable_parent',False) is not True or not boundary.handles or not boundary.identities or ordinary(boundary.identities[-1][0])!=boundary.parent:
            return dict(proof,failure_stage='initial_capable_parent_unavailable',windows_error=None)
        # Borrow this exact initially acquired boundary handle; its owner alone
        # closes it. Successful OS flush does not certify NAS hardware behavior.
        handle=boundary.handles[-1];info=FileInfo()
        need(bool(kernel.GetFileInformationByHandle(handle,ctypes.byref(info))) and not info.attributes&0x400 and bool(info.attributes&0x10) and [int(info.volume),int(info.index_high),int(info.index_low)]==list(boundary.identities[-1][1:]),'directory_identity_changed','Retained capable directory handle differs from the protected ancestry')
        boundary.revalidate()
        kernel.FlushFileBuffers.argtypes=[W.HANDLE];kernel.FlushFileBuffers.restype=W.BOOL
        supported=bool(kernel.FlushFileBuffers(handle))
        return dict(proof,supported=supported,same_retained_parent_handle=True,failure_stage=None if supported else 'retained_capable_handle_flush',windows_error=0 if supported else ctypes.get_last_error(),filesystem_support='os_flush_succeeded' if supported else 'unproven')

    def _final_proof(self,file,boundary,source_proof):
        destination=self._file_proof(file,self.final,boundary);media=self._media(self.final,source_proof,destination)
        intent=self._prior('final_publish_intent')
        need(destination['identity']==intent['temporary_identity'] and destination['parent_identity']==intent['parent_identity'],'final_identity_changed','Final output is not the exact intended temporary publication')
        file.flush();durability={'file_flushed':True,'parent_directory':self._flush_parent(boundary)}
        publication={key:copy.deepcopy(destination[key]) for key in ('root','final_path','sha256','size','identity','parent_identity')}
        return dict(self._common(locations.PROOF_SCHEMA),**publication,media_validation=media,final_publish_intent_sha256=digest(intent),
            final_publication=dict(copy.deepcopy(publication),published=True,no_replace=True),filesystem_durability=durability)

    def _source_seal(self):return self._prior('copy_intent')['original_location']

    def _plan_copy(self):
        with self._original_held() as (source,source_proof,old_boundary),self._target_boundary() as boundary:
            self._root_alias(old_boundary,boundary)
            need(not os.path.lexists(self.final) and not os.path.lexists(self.temporary),'destination_collision','Final or temporary migration pathname already exists; both were retained')
            proof=dict(self._common('books-output-copy-intent-v1'),**self._temp_scope(boundary),no_replace=True,creation='owned_exclusive_create',original_location=source_proof)
            self._advance('copy_intent',proof)

    def _copy(self):
        with self._original_held() as (source,source_proof,old_boundary),self._target_boundary() as boundary:
            self._root_alias(old_boundary,boundary);intent=self._prior('copy_intent');created=self._created_receipt()
            need(self._temp_scope(boundary)['parent_identity']==intent['parent_identity'],'temporary_ancestry_changed','Temporary parent differs from the durable copy intent')
            need(not os.path.lexists(self.final),'destination_collision','An unknown final output exists before publication')
            if created:
                need(created.get('schema')=='books-output-created-artifact-v1' and created.get('publication_id')==self.publication_id and created.get('copy_intent_sha256')==digest(intent) and created.get('temporary_path')==str(self.temporary) and created.get('parent_identity')==intent['parent_identity'] and native_identity(created.get('identity')),'temporary_ownership_unproven','Created artifact journal is malformed')
                need(os.path.lexists(self.temporary),'temporary_ownership_unproven','The exact journaled temporary is missing; no replacement was created')
                holder=VerifiedFile(self.temporary,writable=True)
            else:
                need(not os.path.lexists(self.temporary),'temporary_ownership_unproven','Temporary creation has no native identity journal; unknown file retained')
                holder=self._created_file()
            with holder as temporary:
                single_stream(self.temporary);facts=temporary.facts()
                need(facts['links']==1 and facts['identity']!=source_proof['identity'],'temporary_ownership_unproven','Temporary aliases another source/output')
                if created:need(facts['identity']==created['identity'],'temporary_ownership_unproven','The journaled temporary native identity was replaced')
                else:
                    created={'schema':'books-output-created-artifact-v1','publication_id':self.publication_id,'copy_intent_sha256':digest(intent),
                        'temporary_path':str(self.temporary),'root':self.current['target_root'],'identity':facts['identity'],'parent_identity':intent['parent_identity'],
                        'owner_invocation_id':self.lease['native_owner']['invocation_id'],'created_empty':facts['size']==0}
                    need(created['created_empty'],'temporary_creation_unproven','New migration artifact was not empty')
                    self._event('artifact_created',created);self._fault('after_creation_journal')
                self._write_copy(source,temporary)
                checked=self._file_proof(temporary,self.temporary,boundary)
                need(checked['identity']==created['identity'],'temporary_identity_changed','Owned temporary identity changed while copying')
                proof=dict(self._common('books-output-temporary-proof-v1'),**self._temp_scope(boundary),identity=checked['identity'],sha256=checked['sha256'],size=checked['size'],
                    flushed=True,copy_intent_sha256=digest(intent),created_artifact_sha256=digest(created))
                self._advance('copied',proof)

    def _held_temporary(self,temporary,boundary):
        checked=self._file_proof(temporary,self.temporary,boundary)
        prior=self._prior('copied')
        need(checked['identity']==prior['identity'] and checked['parent_identity']==prior['parent_identity'],'temporary_identity_changed','Temporary is not the recorded completed copy')
        return checked

    def _verify_temporary(self):
        with self._original_held() as (source,source_proof,old_boundary),self._target_boundary() as boundary,VerifiedFile(self.temporary) as temporary:
            self._root_alias(old_boundary,boundary);checked=self._held_temporary(temporary,boundary)
            proof=dict(self._common('books-output-temporary-proof-v1'),**self._temp_scope(boundary),identity=checked['identity'],sha256=checked['sha256'],size=checked['size'],
                flushed=True,copied_proof_sha256=digest(self._prior('copied')),media_validation=self._media(self.temporary,source_proof,checked))
            self._advance('temporary_verified',proof)

    def _plan_publication(self):
        with self._original_held() as (source,source_proof,old_boundary),self._target_boundary() as boundary,VerifiedFile(self.temporary) as temporary:
            self._root_alias(old_boundary,boundary);checked=self._held_temporary(temporary,boundary);prior=self._prior('temporary_verified')
            need(not os.path.lexists(self.final),'destination_collision','An unknown final output exists before its publication intent')
            proof=dict(self._common('books-output-final-publish-intent-v1'),**self._temp_scope(boundary),final_path=str(self.final),temporary_identity=checked['identity'],
                no_replace=True,temporary_verification_sha256=digest(prior))
            self._advance('final_publish_intent',proof)

    def _publish(self):
        with self._original_held() as (source,source_proof,old_boundary),self._target_boundary() as boundary:
            self._root_alias(old_boundary,boundary);intent=self._prior('final_publish_intent')
            temp_exists=os.path.lexists(self.temporary);final_exists=os.path.lexists(self.final)
            need(temp_exists!=final_exists,'publication_ownership_unproven','Publication must have exactly one known temporary or final file; unknown copies retained')
            self._begin()
            try:
                if temp_exists:
                    def before_rename(actual):
                        self._check();boundary.revalidate()
                        need(actual['identity']==intent['temporary_identity'] and actual['sha256']==self.original['sha256'] and actual['size']==self.original['size'],'temporary_identity_changed','Publication acquired a different native temporary')
                        need(self.lease['generation_guard'](self.publication_id,self.current['generation']) is True,'relocation_generation_changed','Migration generation changed before final disposition')
                        self._fault('before_native_publication')
                    publish_no_replace(self.temporary,self.final,boundary,self.original['sha256'],self.original['size'],before_rename)
                    self._fault('after_native_publication')
                with VerifiedFile(self.final,writable=True) as final:
                    proof=self._final_proof(final,boundary,source_proof)
                    self._advance('final_published',proof,transaction=True)
            except BaseException:
                if self.db.in_transaction:self.db.rollback()
                raise

    def _commit_location(self):
        with self._original_held() as (source,source_proof,old_boundary),self._target_boundary() as boundary,VerifiedFile(self.final,writable=True) as final:
            self._root_alias(old_boundary,boundary)
            need(not os.path.lexists(self.temporary),'temporary_ownership_unproven','Unexpected temporary remains after final publication')
            proof=self._final_proof(final,boundary,source_proof)
            self._advance('location_committed',proof)

    def _retain(self,final,boundary,proof,reason):
        self._advance('complete',{'outcome':'copied_verified_original_retained','reason':reason})
        return self._envelope(final,boundary,proof)

    def _remove_or_retain(self):
        with self._target_boundary() as boundary,VerifiedFile(self.final,writable=True) as final:
            need(not os.path.lexists(self.temporary),'temporary_ownership_unproven','Unknown temporary exists beside the committed final output')
            if not os.path.lexists(self.old):
                need(self.current['stage']=='old_removal_intent','original_removal_unproven','Original output vanished without a removal intent')
                intent=self._prior('old_removal_intent');callback=self.lease.get('removal_closure')
                closure=callback(copy.deepcopy(intent)) if callable(callback) else None
                need(isinstance(closure,dict) and closure.get('schema')=='books-migration-removal-closure-v1' and closure.get('removal_intent_sha256')==digest(intent) and closure.get('native_owner_closed') is True and closure.get('prior_owner_invocation_id')==intent.get('owner_invocation_id'),'original_removal_closure_unproven','Missing original is not adopted without exact intent and native-owner closure')
                with DirectoryBoundary(self.original['root'],self.old.parent) as old_boundary:
                    need(not os.path.lexists(self.old),'original_identity_changed','A replacement appeared at the original pathname')
                    proof=self._final_proof(final,boundary,self._source_seal())
                    self._advance('original_removed',{'removal_intent_sha256':digest(intent),'original_removed':True,'native_owner_closed':True,'absence_reconciled':True,'closure':closure})
                    self._advance('complete',{'outcome':'moved'});return self._envelope(final,boundary,proof)
            with self._original_held() as (source,source_proof,old_boundary):
                self._root_alias(old_boundary,boundary);proof=self._final_proof(final,boundary,source_proof)
                if not proof['filesystem_durability']['parent_directory']['supported']:
                    return self._retain(final,boundary,proof,'Destination copied and fully verified; a protected directory flush capability is unavailable, so directory persistence is unproven and the original output was retained')
            try:
                original=self._original_held(delete=True)
                with original as (old,old_proof,old_boundary):
                    # Fresh final proof and exact old DELETE lease remain held
                    # through committed intent, generation guard and disposition.
                    proof=self._final_proof(final,boundary,old_proof)
                    need(proof['filesystem_durability']['parent_directory']['supported'],'directory_durability_unproven','Destination directory durability changed before removal')
                    if self.current['stage']=='location_committed':
                        intent={'publication_id':self.publication_id,'immutable_receipt_sha256':self.current['immutable_receipt_sha256'],'generation':self.current['generation'],
                            'old_location':old_proof,'destination_verification_sha256':digest(json.loads(self.current['destination_verification_json'])),
                            'owner_invocation_id':self.lease['native_owner']['invocation_id']}
                        self._advance('old_removal_intent',intent)
                    else:
                        intent=self._prior('old_removal_intent')
                        need(old_proof['identity']==intent['old_location']['identity'],'original_identity_changed','Old removal intent names another native file')
                    self._begin()
                    try:
                        boundary.revalidate();old_boundary.revalidate();self._check()
                        need(self.lease['generation_guard'](self.publication_id,self.current['generation']) is True,'relocation_generation_changed','Migration lease changed immediately before exact old disposition')
                        old.dispose();self._fault('old_disposition_before_close');old.__exit__(None,None,None)
                        self._fault('after_old_disposition')
                        need(not os.path.lexists(self.old),'original_removal_unproven','Disposed original pathname did not disappear')
                        removed={'removal_intent_sha256':digest(intent),'original_removed':True,'native_owner_closed':old.handle is None,'absence_reconciled':False,'owner_invocation_id':self.lease['native_owner']['invocation_id']}
                        self._advance('original_removed',removed,transaction=True)
                    except BaseException:
                        if self.db.in_transaction:self.db.rollback()
                        raise
                    self._advance('complete',{'outcome':'moved'});return self._envelope(final,boundary,proof)
            except (BoundaryError,OSError) as error:
                with self._original_held() as (source,source_proof,old_boundary):
                    proof=self._final_proof(final,boundary,source_proof)
                    return self._retain(final,boundary,proof,'Destination verified; exact original disposition was refused: '+str(error))

    def _envelope(self,file,boundary,proof):
        current=self._read_row();job=row(self.db,'SELECT * FROM audio_jobs WHERE job_id=?',(current['job_id'],))
        def verify(location,envelope):
            boundary.revalidate()
            return location['final_path']==str(self.final) and file.facts()['identity']==location['identity'] and proof['sha256']==location['sha256'] and proof['size']==location['size']
        return locations.resolve(self.db,job,current['publication_kind'],self.original,verify)

    def run(self,publication_id):
        need(os.name=='nt','native_capability_unavailable','Native output migration requires Windows')
        self.publication_id=publication_id
        with self.operation_lease(publication_id) as lease:
            need(isinstance(lease,dict) and isinstance(lease.get('db'),sqlite3.Connection) and lease.get('drained') is True and all(callable(lease.get(key)) for key in ('generation_guard','durable_commit')),'migration_lease_unproven','A drained operation lease with generation/durability capabilities is required')
            owner=lease.get('native_owner')
            need(isinstance(owner,dict) and owner.get('schema')=='books-migration-native-owner-v1' and isinstance(owner.get('invocation_id'),str) and bool(owner['invocation_id']) and native_identity(owner.get('catalog_identity')) and isinstance(owner.get('owner_handle_proof'),dict) and bool(owner['owner_handle_proof']),'native_owner_unproven','Retained native catalog-owner proof is required')
            need(owner['owner_handle_proof'].get('held') is True and native_identity(owner['owner_handle_proof'].get('lock_identity')) and isinstance(owner['owner_handle_proof'].get('lock_ancestry'),list) and bool(owner['owner_handle_proof']['lock_ancestry']),'native_owner_unproven','Retained catalog lock facts/ancestry are required')
            self.lease=lease;self.db=lease['db']
            need(not self.db.in_transaction,'unexpected_catalog_transaction','Migration lease must yield an idle stage connection')
            catalog=self.db.execute('PRAGMA database_list').fetchall();main=next((value[2] for value in catalog if value[1]=='main'),None)
            need(main and ordinary(main)==self.database,'catalog_identity_changed','Lease yielded a different catalog')
            need(self._catalog_identity()==owner['catalog_identity'],'catalog_identity_changed','Native catalog identity differs from the retained operation lease')
            need(str(self.db.execute('PRAGMA journal_mode').fetchone()[0]).lower() in {'wal','delete','truncate','persist'} and int(self.db.execute('PRAGMA synchronous').fetchone()[0]) in {2,3},'catalog_not_durable','Stage connection must already use persistent FULL/EXTRA SQLite durability')
            self.current=self._read_row();self.original=json.loads(self.current['original_output_json']);self.old=ordinary(self.original['final_path']);self.final=ordinary(self.current['planned_destination'])
            self.temporary=self.final.with_name('.'+self.publication_id+'.'+self.current['migration_id']+'.migration-partial')
            manifest=json.loads(row(self.db,'SELECT manifest FROM audio_jobs WHERE job_id=?',(self.current['job_id'],))['manifest'])
            need(all(ordinary(source['path'])!=self.old for source in manifest.get('sources',[])),'original_source_not_output','An original input source can never be removed as migrated output')
            while True:
                self._check();stage=self.current['stage']
                if stage=='planned':self._plan_copy()
                elif stage=='copy_intent':self._copy()
                elif stage=='copied':self._verify_temporary()
                elif stage=='temporary_verified':self._plan_publication()
                elif stage=='final_publish_intent':self._publish()
                elif stage=='final_published':self._commit_location()
                elif stage in {'location_committed','old_removal_intent'}:return self._remove_or_retain()
                elif stage=='original_removed':
                    with self._target_boundary() as boundary,VerifiedFile(self.final,writable=True) as file:
                        proof=self._final_proof(file,boundary,self._source_seal());self._advance('complete',{'outcome':'moved'});return self._envelope(file,boundary,proof)
                elif stage=='complete':
                    with self._target_boundary() as boundary,VerifiedFile(self.final,writable=True) as file:
                        proof=self._final_proof(file,boundary,self._source_seal());return self._envelope(file,boundary,proof)
                else:raise MigrationRefused('unsupported_migration_stage','Unknown migration stage')
