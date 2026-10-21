"""Journaled same-volume Windows moves. No byte copy or copy/delete fallback.

Original conversion receipts stay immutable. Rename intent precedes the native
operation; restart reconciliation requires the exact intended file and parents.
An explicit retained-copy cleanup is a separate, narrowly bound protocol.
"""
import contextlib
import copy
import hashlib
import json
import os
import sqlite3
from pathlib import Path

import publication_locations as locations
from native_io import DirectoryBoundary,VerifiedFile,ordinary,rename_no_replace,kernel
from output_migration import MigrationWorker,need,row,digest,packed,native_identity
from source_cleanup import single_stream


class RenameWorker(MigrationWorker):
    def _check(self):
        if self.stop.is_set():raise InterruptedError('Output move stopped at a recoverable journal boundary')

    def _advance(self,stage,proof,transaction=False):
        if not transaction:self._begin()
        try:
            locations.move_transition(self.db,self.publication_id,self.current['generation'],stage,proof)
            if stage=='location_committed':
                final=proof['final'];self.invalidate(self.db,copy.deepcopy(self.original),{k:copy.deepcopy(final[k]) for k in ('root','final_path','sha256','size','identity','parent_identity')})
                need(self.db.in_transaction,'invalidation_committed_early','Move invalidation must remain in the catalog transaction')
            self._fault('before_'+stage+'_commit');self._durable()
        except BaseException:
            if self.db.in_transaction:self.db.rollback()
            raise
        self._fault('after_'+stage)

    def _claim(self,schema):
        return dict(self._common(schema),strategy=self.strategy,frozen_binding_sha256=digest(locations._frozen(self.current)),
            operation_plan_sha256=self.lease['operation_plan_sha256'])

    def _content(self,file,path,boundary,*,cached=False):
        self._check();single_stream(path);facts=file.facts()
        need(facts['links']==1 and facts['size']==self.original['size'],'output_content_changed','Move requires the unique exact-size original publication')
        basis=None
        if cached and self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='verified_outputs'").fetchone():
            known=row(self.db,'SELECT * FROM verified_outputs WHERE path=? AND sha256=?',(os.path.normcase(str(path)),self.original['sha256']))
            stat=path.stat();observed=[stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns]
            native=[facts['dev'],facts['ino'],facts['size'],facts['modified']]
            if known and known['job_id']==self.current['job_id'] and json.loads(known['identity'])==observed==native:
                basis={'kind':'accepted_persisted_verification_cache','identity':observed,'cache_record_sha256':digest(known)}
        if basis is None:
            full=hashlib.sha256()
            for block in file.chunks():self._check();full.update(block)
            need(full.hexdigest()==self.original['sha256'],'output_content_changed','Move full held content differs from immutable receipt')
            basis={'kind':'fresh_full_held_hash'}
        self._check();boundary.revalidate()
        return {'root':str(boundary.root),'final_path':str(path),'sha256':self.original['sha256'],
            'full_content_sha256':self.original['sha256'],'size':facts['size'],'identity':facts['identity'],
            'native':facts,'parent_identity':json.loads(packed(boundary.identities)),'content_basis':basis}

    @contextlib.contextmanager
    def _old(self):
        with DirectoryBoundary(self.original['root'],self.old.parent) as boundary,VerifiedFile(self.old,delete=True) as file:
            yield file,boundary

    @contextlib.contextmanager
    def _new(self,create=False):
        with DirectoryBoundary(self.current['target_root'],self.final.parent,create=create,rename_destination=True) as boundary:
            yield boundary

    def _intent(self,source,boundary,target,destination=None):
        need(source['parent_identity']==self.original['parent_identity'],'original_ancestry_changed','Move original ancestry changed')
        target_proof={'root':str(target.root),'final_path':str(self.final),'parent_identity':json.loads(packed(target.identities))}
        need(source['identity'][0]==target_proof['parent_identity'][-1][1],'cross_volume_move','Native source/destination volumes differ; no copy fallback')
        proof=dict(self._claim('books-output-native-move-intent-v1'),original_location=source,target=target_proof,no_replace=True,copy_fallback=False)
        if destination is not None:proof['destination_location']=destination
        return proof

    def _final(self,destination,source,native=None):
        publication={k:copy.deepcopy(destination[k]) for k in ('root','final_path','sha256','size','identity','parent_identity')}
        return dict(self._common(locations.PROOF_SCHEMA),**publication,media_validation=self._media(self.final,source,destination),
            final_publication=dict(copy.deepcopy(publication),published=True,no_replace=True,copy_fallback=False,native_rename=copy.deepcopy(native)),
            filesystem_durability={'operation':'same_volume_rename','server_power_loss_guarantee':False})

    def _commit_and_finish(self,final,intent):
        if self.current['stage']=='renamed':
            final=dict(final,generation=self.current['generation'])
            proof=dict(self._claim('books-output-native-move-commit-v1'),intent_sha256=digest(intent),final=final)
            self._advance('location_committed',proof)
        if self.current['stage']=='location_committed':
            self._advance('complete',dict(self._claim('books-output-native-move-complete-v1'),intent_sha256=digest(intent),outcome='moved'))

    def _envelope_checked(self,proof):
        job=row(self.db,'SELECT * FROM audio_jobs WHERE job_id=?',(self.current['job_id'],))
        return locations.resolve(self.db,job,self.current['publication_kind'],self.original,
            lambda location,envelope:all(location.get(k)==proof[k] for k in ('root','final_path','sha256','size','identity','parent_identity')))

    def _rename(self):
        stage=self.current['stage']
        if stage in {'planned','rename_intent'} and os.path.lexists(self.old):
            with self._old() as (source,old_boundary),self._new(create=True) as target:
                need(not os.path.lexists(self.final),'destination_collision','Move destination exists; preserve both files')
                original=self._content(source,self.old,old_boundary,cached=True)
                if stage=='planned':self._advance('rename_intent',self._intent(original,old_boundary,target))
                intent=self._prior('rename_intent')
                need(original['identity']==intent['original_location']['identity'] and original['parent_identity']==intent['original_location']['parent_identity']
                    and json.loads(packed(target.identities))==intent['target']['parent_identity'],'rename_identity_changed','Move intent file or protected parents changed')
                self._check();self._fault('before_native_rename')
                native=rename_no_replace(source,self.final,old_boundary,target,expected_identity=original['native'],expected_size=original['size'],expected_sha256=original['sha256'])
                self._fault('after_native_rename_before_journal')
                destination=dict(original,root=str(target.root),final_path=str(self.final),parent_identity=json.loads(packed(target.identities)),
                    native=native['destination_native'],content_basis={'kind':'same_protected_native_file_after_no_copy_rename','source_content_basis':original['content_basis']})
                final=self._final(destination,original,native)
                proof=dict(self._claim('books-output-native-renamed-v1'),intent_sha256=digest(intent),old_absent=True,final=final)
                self._advance('renamed',proof)
                self._commit_and_finish(final,intent)
                # Original DELETE handle still denies all other writers/deleters
                # through namespace proof and complete durable catalog readback.
                old_boundary.revalidate();target.revalidate()
                return self._envelope_checked(destination)
        # A restart never infers rename completion from a pathname/hash alone.
        # Require the pinned same native file, both parent identities and full
        # destination bytes after the previous protective handle was lost.
        intent=self._prior('rename_intent')
        with DirectoryBoundary(self.original['root'],self.old.parent) as old_boundary,self._new() as target,VerifiedFile(self.final) as file:
            need(not os.path.lexists(self.old),'rename_ambiguous','Move recovery requires original absent and intended destination present')
            need(json.loads(packed(old_boundary.identities))==intent['original_location']['parent_identity']
                and json.loads(packed(target.identities))==intent['target']['parent_identity'],'rename_ancestry_changed','Move recovery parent identities changed')
            destination=self._content(file,self.final,target)
            need(destination['identity']==intent['original_location']['identity'],'rename_identity_changed','Move recovery destination is not the exact intended native source')
            if stage=='rename_intent':
                final=self._final(destination,intent['original_location'],{'recovered_same_native_file':True,'copy_fallback':False})
                self._advance('renamed',dict(self._claim('books-output-native-renamed-v1'),intent_sha256=digest(intent),old_absent=True,final=final))
            else:
                final=copy.deepcopy(self._prior('renamed')['final'])
                need(all(final[k]==destination[k] for k in ('root','final_path','sha256','size','identity','parent_identity')),'rename_identity_changed','Recovered final differs from journal')
            self._commit_and_finish(final,intent)
            return self._envelope_checked(destination)

    def _duplicate_done(self,target,file,intent,basis,destination):
        expected=intent['destination_location']
        need(all(destination[k]==expected[k] for k in ('root','final_path','sha256','size','identity','parent_identity')),'duplicate_destination_changed','Protected verified duplicate destination changed')
        if self.current['stage']=='duplicate_cleanup_intent':
            proof=dict(self._claim('books-output-duplicate-removed-v1'),intent_sha256=digest(intent),old_absent=True,
                destination_location=expected,basis=basis)
            self._advance('duplicate_removed',proof)
        if self.current['stage']=='duplicate_removed':
            self._advance('complete',dict(self._claim('books-output-native-move-complete-v1'),intent_sha256=digest(intent),outcome='moved'))
        return self._envelope_checked(destination)

    def _duplicates(self):
        exists=os.path.lexists(self.old)
        with self._new() as target,VerifiedFile(self.final) as final:
            # Explicit duplicate cleanup ALWAYS full-hashes the protected Sorted
            # file and old file; it never borrows rename cache authority.
            destination=self._content(final,self.final,target)
            if exists:
                with self._old() as (old,old_boundary):
                    original=self._content(old,self.old,old_boundary)
                    if self.current['stage']=='complete':
                        last=row(self.db,"SELECT proof_json FROM migration_events WHERE publication_id=? AND outcome='transition' ORDER BY event_id DESC LIMIT 1",(self.publication_id,))
                        need(json.loads(last['proof_json']).get('outcome')=='copied_verified_original_retained','duplicate_scope_changed','Only an exact retained verified copy can authorize duplicate cleanup')
                        self._advance('duplicate_cleanup_intent',self._intent(original,old_boundary,target,destination))
                    intent=self._prior('duplicate_cleanup_intent')
                    need(original==intent['original_location'] and destination==intent['destination_location'],'duplicate_identity_changed','Duplicate cleanup native/content proof changed')
                    self._check();self._begin()
                    try:
                        old_boundary.revalidate();target.revalidate()
                        need(self.lease['generation_guard'](self.publication_id,self.current['generation']) is True,'relocation_generation_changed','Duplicate cleanup generation changed before disposition')
                        old.dispose();self._fault('duplicate_disposition_before_close')
                        handle=old.handle
                        need(bool(kernel.CloseHandle(handle)),'duplicate_close_unproven','Exact duplicate disposition checked-close failed')
                        old.handle=None;self._fault('after_duplicate_disposition')
                        need(not os.path.lexists(self.old),'duplicate_removal_unproven','Exact old duplicate pathname did not disappear')
                        proof=dict(self._claim('books-output-duplicate-removed-v1'),intent_sha256=digest(intent),old_absent=True,
                            destination_location=intent['destination_location'],basis='exact_handle_disposition_closed')
                        self._advance('duplicate_removed',proof,transaction=True)
                    except BaseException:
                        if self.db.in_transaction:self.db.rollback()
                        raise
                    # No cancellation or callback exception was deliberately
                    # introduced between disposition and durable removed commit.
                    return self._duplicate_done(target,final,intent,'exact_handle_disposition_closed',destination)
            need(self.current['stage'] in {'duplicate_cleanup_intent','duplicate_removed','complete'},'duplicate_removal_unproven','Missing old file has no exact duplicate cleanup intent')
            intent=self._prior('duplicate_cleanup_intent')
            with DirectoryBoundary(self.original['root'],self.old.parent) as old_boundary:
                need(json.loads(packed(old_boundary.identities))==intent['original_location']['parent_identity'] and not os.path.lexists(self.old),
                    'duplicate_ancestry_changed','Duplicate cleanup source namespace changed')
                return self._duplicate_done(target,final,intent,'intent_bound_absence_with_verified_destination',destination)

    def run(self,publication_id):
        need(os.name=='nt','native_capability_unavailable','Native output move requires Windows')
        self.publication_id=publication_id
        with self.operation_lease(publication_id) as lease:
            need(isinstance(lease,dict) and isinstance(lease.get('db'),sqlite3.Connection) and all(callable(lease.get(k)) for k in ('generation_guard','durable_commit')),'migration_lease_unproven','A real generation/durability operation lease is required')
            need(lease.get('operation_strategy')=='rename' and isinstance(lease.get('operation_plan_sha256'),str),'rename_scope_unproven','Exact reviewed native move strategy required')
            owner=lease.get('native_owner') or {}
            lock=owner.get('owner_handle_proof') or {}
            need(owner.get('schema')=='books-migration-native-owner-v1' and isinstance(owner.get('invocation_id'),str) and bool(owner['invocation_id'])
                and native_identity(owner.get('catalog_identity')) and lock.get('held') is True and native_identity(lock.get('lock_identity'))
                and isinstance(lock.get('lock_ancestry'),list) and bool(lock['lock_ancestry'])
                and lease.get('move_action') in {'rename','remove_verified_duplicate'} and lease.get('drained') is True
                and owner.get('catalog_identity')==self._catalog_identity(),'native_owner_unproven','Real drained native catalog move owner required')
            self.lease=lease;self.db=lease['db']
            need(not self.db.in_transaction,'unexpected_catalog_transaction','Move requires idle durable operation connection')
            main=next((v[2] for v in self.db.execute('PRAGMA database_list') if v[1]=='main'),None)
            need(main and ordinary(main)==self.database,'catalog_identity_changed','Move lease yielded another catalog')
            need(str(self.db.execute('PRAGMA journal_mode').fetchone()[0]).lower() in {'wal','delete','truncate','persist'}
                and int(self.db.execute('PRAGMA synchronous').fetchone()[0]) in {2,3},'catalog_not_durable','Native move requires persistent FULL/EXTRA journal')
            self.current=self._read_row();self.original=json.loads(self.current['original_output_json'])
            self.old=ordinary(self.original['final_path']);self.final=ordinary(self.current['planned_destination'])
            manifest=json.loads(row(self.db,'SELECT manifest FROM audio_jobs WHERE job_id=?',(self.current['job_id'],))['manifest'])
            need(all(ordinary(v['path'])!=self.old for v in manifest.get('sources',[])),'original_source_not_output','Input source may never be moved as publication output')
            self.strategy=locations.RENAME_STRATEGY if lease['move_action']=='rename' else locations.DUPLICATE_STRATEGY
            self._check()
            return self._rename() if self.strategy==locations.RENAME_STRATEGY else self._duplicates()
