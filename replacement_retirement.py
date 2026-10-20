"""Retire only three approved former outputs after a verified current successor.

Recovery copies of the retired outputs are deleted once the replacement is verified (purge_recoveries,
v0.16.8, Sergei 2026-10-18). A purged copy is recorded (purged_at); history is then proven from the
records, the verified replacement and the former output's absence.
"""
import contextlib
import hashlib
import json
import os
import shutil
import threading
import time
import ctypes
from ctypes import wintypes
from datetime import datetime,timedelta,timezone
from pathlib import Path
from native_io import DirectoryBoundary,VerifiedFile,ordinary,BoundaryError,kernel,FileInfo
from source_cleanup import single_stream
from replacement_jobs import digest,now

kernel.WriteFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
kernel.WriteFile.restype=wintypes.BOOL

class ReplacementRetirement:
    def __init__(self,store,root,library,stop,guard,former_guard,bindings=None):
        self.store=store;self.root=ordinary(root);self.library=ordinary(library);self.stop=stop;self.guard=guard
        self.former_guard=former_guard
        self.bindings=bindings
        self.lock=threading.RLock();self.current=None;self.last_errors={}
        with DirectoryBoundary(self.root.anchor,self.root,create=True) as boundary:self.root_identity=boundary.identities

    def _stop(self):
        if self.stop.is_set():raise InterruptedError('Former audiobook retirement paused; verified recovery retained')

    @staticmethod
    def _hash(file,stop=None):
        h=hashlib.sha256();deadline=time.monotonic()+600
        for block in file.chunks():
            if stop is not None and stop.is_set():raise InterruptedError('Protected file verification paused')
            if time.monotonic()>deadline:raise TimeoutError('Protected file verification exceeded its bound')
            h.update(block)
        return h.hexdigest()

    @contextlib.contextmanager
    def _current(self,relation,historical=False,stop=None):
        original=json.loads(relation['current_output_json'])
        record,envelope=self.bindings.current(original,'replacement') if self.bindings else (original,None)
        path=ordinary(record['final_path']);root=ordinary(record.get('root',self.library))
        if not path.is_relative_to(root) or path.suffix.lower()!='.m4b':raise BoundaryError('Current replacement is outside its bound audiobook root')
        with DirectoryBoundary(root,path.parent) as boundary,VerifiedFile(path) as file:
            if [list(v) for v in boundary.identities]!=[list(v) for v in record['parent_identity']] or file.facts()['links']!=1 or file.facts()['size']!=record['size'] or self._hash(file,stop if historical else self.stop)!=record['sha256']:
                raise BoundaryError('Current replacement changed; former outputs retained')
            if record.get('identity') is not None and record['identity']!=file.facts()['identity']:raise BoundaryError('Current replacement native identity changed')
            if self.guard(relation,historical=historical) is not True:raise BoundaryError('Replacement approval or publication changed')
            yield {'original':original,'effective':record,'envelope':envelope,'kind':'replacement','journal_sha256':None}

    @contextlib.contextmanager
    def _publication_transaction(self,relation,*publications,historical=False):
        from scanner import connect
        with connect(self.store.database) as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT * FROM audiobook_replacements WHERE id=?',(relation['id'],)).fetchone()
            if not current or dict(current)!=relation:raise BoundaryError('Replacement relation changed before native disposition')
            if not self.store.structural_guard(relation,historical=historical,db=db):raise BoundaryError('Replacement approval changed before native disposition')
            for publication in publications:
                if publication is None:continue
                if self.bindings:
                    if not self.bindings.guard(db,publication['original'],publication['envelope'],kind=publication['kind'],repair_journal_sha256=publication.get('journal_sha256'),require_transaction=True):raise BoundaryError('Publication generation changed before native disposition')
                elif publication.get('envelope') is not None:raise BoundaryError('Relocated publication guard unavailable')
            yield db

    @contextlib.contextmanager
    def _recovery(self,relation,row,historical=False,stop=None):
        recovery=json.loads(row['recovery_json']);path=ordinary(recovery['path']);expected=self.root/relation['id']
        proof=json.loads(row['provenance_json']);approval=json.loads(relation['approval_json'])
        expected_path=expected/(hashlib.sha256(row['original_path'].encode('utf-8')).hexdigest()+'.m4b')
        if (row['replacement_id']!=relation['id'] or proof.get('path')!=row['original_path'] or proof not in approval['old_outputs'] or
                path!=expected_path or recovery.get('sha256')!=proof['sha256'] or recovery.get('size')!=proof['size'] or
                recovery.get('copy_pending') is True or recovery.get('facts',{}).get('size')!=proof['size']):raise BoundaryError('Former-output recovery correspondence changed')
        with DirectoryBoundary(self.root,expected) as boundary,VerifiedFile(path,writable=not historical) as file:
            if boundary.identities!=[tuple(v) for v in recovery['ancestry']] or file.facts()!=recovery['facts'] or file.facts()['links']!=1 or self._hash(file,stop if historical else self.stop)!=recovery['sha256']:
                raise BoundaryError('Former-output recovery changed; no old output disposition allowed')
            if not historical:file.flush()
            single_stream(path)
            yield file

    def _absent(self,path,root=None):
        with DirectoryBoundary(root or self.library,path.parent):
            # lstat rather than exists: broken/reparse names are never absence.
            try:path.lstat()
            except FileNotFoundError:return True
            return False

    def _copy(self,relation,row,original,proof,destination,boundary):
        backup=destination/(hashlib.sha256(row['original_path'].encode('utf-8')).hexdigest()+'.m4b')
        if not row['recovery_json']:
            # Exclusive blank creation, then protect its exact native identity before writing.
            with backup.open('xb') as stream:
                stream.flush();os.fsync(stream.fileno())
                import msvcrt
                info=FileInfo()
                if not kernel.GetFileInformationByHandle(msvcrt.get_osfhandle(stream.fileno()),ctypes.byref(info)) or info.attributes&(0x400|0x10) or info.links!=1:
                    raise BoundaryError('Exclusive recovery creation identity cannot be established')
                created_identity=[info.volume,info.index_high,info.index_low]
            with VerifiedFile(backup,writable=True) as copy:
                if copy.facts()['size']!=0 or copy.facts()['links']!=1 or copy.facts()['identity']!=created_identity:raise BoundaryError('Unknown recovery-copy identity')
                intent={'path':str(backup),'facts':copy.facts(),'ancestry':boundary.identities,'sha256':proof['sha256'],'size':proof['size'],'copy_pending':True,'retired_at':None,'expire_after':None}
                row=self.store.copy_intent(row,intent)
        intent=json.loads(row['recovery_json'])
        if intent.get('copy_pending') is not True or intent['path']!=str(backup) or intent['sha256']!=proof['sha256'] or intent['size']!=proof['size']:
            raise BoundaryError('Recovery-copy intent changed')
        with VerifiedFile(backup,writable=True) as copy:
            facts=copy.facts()
            if facts['identity']!=intent['facts']['identity'] or facts['dev']!=intent['facts']['dev'] or facts['ino']!=intent['facts']['ino'] or facts['links']!=1 or facts['size']>proof['size']:
                raise BoundaryError('Interrupted recovery copy identity changed')
            # Resume only a byte-exact prefix of the protected original; never adopt unknown output.
            copied=facts['size'];prefix=hashlib.sha256();remaining=copied
            for block in original.chunks():
                if not remaining:break
                self._stop();part=block[:remaining];prefix.update(part);remaining-=len(part)
            if remaining or self._hash(copy,self.stop)!=prefix.hexdigest():raise BoundaryError('Interrupted recovery copy is not the exact original prefix')
            kernel.SetFilePointerEx.argtypes=[wintypes.HANDLE,ctypes.c_longlong,ctypes.c_void_p,wintypes.DWORD];kernel.SetFilePointerEx.restype=wintypes.BOOL
            if not kernel.SetFilePointerEx(copy.handle,copied,None,0):raise BoundaryError('Cannot resume verified recovery copy')
            skip=copied
            for block in original.chunks():
                self._stop()
                if skip>=len(block):skip-=len(block);continue
                block=block[skip:];skip=0;buffer=ctypes.create_string_buffer(block);written=wintypes.DWORD()
                if not kernel.WriteFile(copy.handle,buffer,len(block),ctypes.byref(written),None) or written.value!=len(block):raise BoundaryError('Native recovery copy did not complete its write')
            copy.restore_metadata(proof['facts']['modified'],proof['facts']['attributes']);copy.flush()
            if copy.facts()['links']!=1 or copy.facts()['size']!=proof['size'] or self._hash(copy,self.stop)!=proof['sha256']:raise BoundaryError('Former-output recovery copy failed verification')
            recovery={'path':str(backup),'facts':copy.facts(),'ancestry':boundary.identities,'sha256':proof['sha256'],'size':proof['size'],'retired_at':None,'expire_after':None}
            return self.store.file_transition(row,'copied',recovery)

    def run(self,relation):
        with self.lock:
            if self.current:raise BoundaryError('A former-output retirement is already active')
            self.current=relation['id'];phase='checking'
            try:
                if relation['state']=='completed':return relation
                if relation['state'] not in {'published','retiring'}:raise BoundaryError('New audiobook must be current before old output retirement')
                self._stop()
                approval=json.loads(relation['approval_json']);rows=self.store.files(relation['id'])
                if len(rows)!=3 or {r['original_path'] for r in rows}!={item['path'] for item in approval['old_outputs']}:
                    raise BoundaryError('Exact former-output receipt set changed')
                if any(json.loads(row['provenance_json']) not in approval['old_outputs'] for row in rows):raise BoundaryError('Former-output provenance changed')
                with contextlib.ExitStack() as stack:
                    from scanner import connect
                    with connect(self.store.database) as db:parent_row=self.store.raw_job(db,relation['parent_job_id'])
                    former=stack.enter_context(self.former_guard(relation,parent_row))
                    destination=self.root/relation['id']
                    boundary=stack.enter_context(DirectoryBoundary(self.root.anchor,destination,create=True))
                    if boundary.identities[:len(self.root_identity)]!=self.root_identity:raise BoundaryError('Recovery storage ancestry changed')
                    successor=stack.enter_context(self._current(relation))
                    for source in approval['sources']:
                        path=ordinary(source['path']);stack.enter_context(DirectoryBoundary(self.library,path.parent));file=stack.enter_context(VerifiedFile(path))
                        if file.facts()['links']!=1 or file.facts()['size']!=source['size'] or self._hash(file,self.stop)!=source['sha256']:raise BoundaryError('Original source changed; former conversions retained')
                    if relation['state']=='published':relation=self.store.transition(relation,'retiring')
                    required=sum(json.loads(r['provenance_json'])['size'] for r in rows if r['state']=='waiting')
                    if shutil.disk_usage(destination).free<required+1024*1024:raise BoundaryError('Insufficient verified recovery space; old outputs retained')
                    # Base last reduces exposure, but exact partial-intent recovery remains mandatory.
                    base=approval['parent_output']
                    rows.sort(key=lambda row:row['original_path']==base)
                    for index,row in enumerate(rows):
                        self._stop();phase='verifying former output'
                        proof=json.loads(row['provenance_json']);publication=former.get(row['original_path']) if former else None
                        if self.bindings and publication is None:raise BoundaryError('Former publication lacks its independent authoritative location proof')
                        record=publication['effective'] if publication else {'root':str(self.library),'final_path':row['original_path'],'parent_identity':proof['ancestry']}
                        path=ordinary(record['final_path']);output_root=ordinary(record['root'])
                        if not path.is_relative_to(output_root) or path==ordinary(successor['effective']['final_path']):raise BoundaryError('Former-output allowlist is unsafe')
                        ancestry=stack.enter_context(DirectoryBoundary(output_root,path.parent))
                        if [list(v) for v in ancestry.identities]!=[list(v) for v in record['parent_identity']]:raise BoundaryError('Former-output ancestry changed')
                        if row['state'] in {'retirement_intended','removed'} and self._absent(path,output_root):
                            if publication and publication['envelope'] is not None and row['state']=='retirement_intended':raise BoundaryError('Relocated former-output absence needs exact native-owner closure; recovery retained')
                            stack.enter_context(self._recovery(relation,row))
                            if row['state']=='retirement_intended':
                                recovery=json.loads(row['recovery_json']);retired=now();recovery.update(retired_at=retired,expire_after=(datetime.fromisoformat(retired)+timedelta(hours=24)).isoformat())
                                row=self.store.file_transition(row,'removed',recovery)
                            continue
                        if row['state']=='removed':raise BoundaryError('A retired old output unexpectedly exists; no replay allowed')
                        with contextlib.ExitStack() as leaf:
                            original=VerifiedFile(path,delete=True).__enter__()
                            leaf.callback(lambda:original.__exit__(None,None,None) if original.handle is not None else None)
                            facts=original.facts()
                            native_match=facts['identity']==record['identity'] if record.get('identity') is not None else facts==proof['facts']
                            if not native_match or facts['links']!=1 or facts['size']!=proof['size'] or self._hash(original,self.stop)!=proof['sha256']:
                                raise BoundaryError('Former output changed; it cannot be retired')
                            single_stream(path)
                            if row['state']=='waiting':
                                phase='copying verified former output'
                                row=self._copy(relation,row,original,dict(proof,facts=facts),destination,boundary)
                            stack.enter_context(self._recovery(relation,row))
                            self._stop()
                            if self.guard(relation) is not True:raise BoundaryError('Replacement publication changed before old disposition')
                            if row['state']=='copied':row=self.store.file_transition(row,'retirement_intended')
                            if row['state']!='retirement_intended':raise BoundaryError('Old disposition has no exact durable intent')
                            phase='native former-output disposition';self._stop()
                            with self._publication_transaction(relation,successor,*(former.values() if former else ())) as db:
                                ancestry.revalidate();original.dispose();original.__exit__(None,None,None)
                                if not self._absent(path,output_root):raise BoundaryError('Native former-output disposition did not establish absence')
                                recovery=json.loads(row['recovery_json']);retired=now();recovery.update(retired_at=retired,expire_after=(datetime.fromisoformat(retired)+timedelta(hours=24)).isoformat(),effective_retirement=publication,native_handle_closed=True)
                                phase='recording native disposition';row=self.store.file_transition(row,'removed',recovery,db=db)
                    return self.store.transition(relation,'completed')
            except BaseException as error:
                diagnostic={'type':type(error).__name__,'message':str(error),'phase':phase,'secondary':[],'at':now()}
                self.last_errors[relation['id']]=diagnostic
                try:self.store.failure(relation,error,phase)
                except Exception as secondary:diagnostic['secondary'].append({'type':type(secondary).__name__,'message':str(secondary)})
                raise
            finally:self.current=None

    def purge_recoveries(self,relation):
        """Delete the recovery copies of a completed replacement's retired outputs, after verifying the current
        replacement in full. Each copy must still be the recorded one (identity and full hash); an already
        missing copy is recorded as purged. Idempotent: a purged record is skipped."""
        if relation['state']!='completed':return 0
        rows=[r for r in self.store.files(relation['id']) if r['state']=='removed' and not json.loads(r['recovery_json'] or '{}').get('purged_at')]
        if not rows:return 0
        freed=0
        with self.lock,self._current(relation,historical=True,stop=self.stop) as successor:
            for row in rows:
                self._stop();recovery=json.loads(row['recovery_json']);path=ordinary(recovery['path']);expected=self.root/relation['id']
                if path.parent!=expected:raise BoundaryError('Former-output recovery is outside its owned folder')
                try:path.lstat();present=True
                except FileNotFoundError:present=False
                if present:
                    with DirectoryBoundary(self.root,expected),VerifiedFile(path,delete=True) as file:
                        if file.facts()!=recovery['facts'] or file.facts()['links']!=1 or self._hash(file,self.stop)!=recovery['sha256']:
                            raise BoundaryError('Former-output recovery changed; preserved')
                        with self._publication_transaction(relation,successor,historical=True) as db:
                            file.dispose();file.__exit__(None,None,None)
                            try:path.lstat()
                            except FileNotFoundError:pass
                            else:raise BoundaryError('Recovery copy disposition did not remove its name')
                            self.store.file_purged(row,dict(recovery,purged_at=now(),purged_bytes=recovery['size']),db=db);freed+=recovery['size']
                else:
                    with self._publication_transaction(relation,successor,historical=True) as db:self.store.file_purged(row,dict(recovery,purged_at=now(),purged_bytes=0),db=db)
            try:expected.rmdir()
            except OSError:pass
        return freed

    def historical_retired(self,parent_row,stop=None):
        """Known base absence is valid history even during partial retirement.

        stop (optional) lets a routine caller interrupt the read-only hashing; an
        interruption is raised, never reported as "not history".
        """
        try:
            relation=self.store.get(parent=parent_row['job_id'])
            if not relation or relation['state'] not in {'retiring','completed'} or digest(parent_row)!=relation['parent_record_sha256']:return False
            parent_output=json.loads(parent_row['output']);path=ordinary(parent_output['final_path'])
            row=next((r for r in self.store.files(relation['id']) if r['original_path']==str(path)),None)
            if not row or row['state'] not in {'retirement_intended','removed'}:return False
            proof=json.loads(row['provenance_json'])
            if proof['sha256']!=parent_output['sha256'] or proof['size']!=parent_output['size']:return False
            with self.former_guard(relation,parent_row) as former,self._current(relation,historical=True,stop=stop):
                publication=former.get(str(path)) if former else None
                if self.bindings and publication is None:return False
                if publication:path=ordinary(publication['effective']['final_path'])
                root=publication['effective']['root'] if publication else self.library
                if row['state']=='retirement_intended' and publication and publication['envelope'] is not None:return False
                if json.loads(row['recovery_json'] or '{}').get('purged_at'):return self._absent(path,root)
                with self._recovery(relation,row,historical=True,stop=stop):return self._absent(path,root)
        except InterruptedError:raise
        except (ValueError,OSError,KeyError):return False
