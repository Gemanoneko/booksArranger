"""Explicit selected old DATA retirement using native write-fenced disposal.

No source/Git/library directory is removed. Generic directory disposition is
not weakened. Every removed member needs an immutable closed-disposition receipt;
mere intent followed by absence is a held outcome, never successful cleanup.
"""
import contextlib
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sqlite3

from storage_relocation import parse_manifest, _key, _inside, _relative
from storage_relocation_operator import (NativeItem, Security, bounded_operation, checkpoint,
    create_new, digest, packed, pinned_receipt, need, _readonly_database, _catalog_owner,
    _scan, verify_source_fence, logical_catalog_digest, local_root, security_equivalent)

REGISTRY_SQL = '''CREATE TABLE IF NOT EXISTS storage_relocation_source_finalization(
 catalog_id TEXT PRIMARY KEY,generation TEXT NOT NULL,base_fence_sha256 TEXT NOT NULL,
 verification_sha256 TEXT NOT NULL,receipt_path TEXT NOT NULL,receipt_sha256 TEXT NOT NULL,
 state TEXT NOT NULL,revision INTEGER NOT NULL)'''
FILES_SQL = '''CREATE TABLE IF NOT EXISTS storage_relocation_source_finalization_files(
 catalog_id TEXT NOT NULL,generation TEXT NOT NULL,relative TEXT NOT NULL,state TEXT NOT NULL,
 receipt_path TEXT NOT NULL,receipt_sha256 TEXT NOT NULL,revision INTEGER NOT NULL,
 PRIMARY KEY(catalog_id,generation,relative))'''
SCHEMA = 'books-source-finalization-v1'
TERMINAL_SCHEMA = 'books-source-retirement-v1'


def _absent(path):
    # A removed parent's closed proof is validated separately. Never treat a
    # failed listing/access error as positive absence.
    parent=path.parent
    while not parent.exists():parent=parent.parent
    with os.scandir(parent) as entries:
        names={entry.name.casefold() for entry in entries}
    child=path
    while child.parent!=parent:child=child.parent
    need(child.name.casefold() not in names,'Removed old name was reused; held')


def _removed_proof(c,record,row,directory=False):
    need(row and row['state']=='removed','Closed old-member removal is missing')
    with pinned_receipt(row['receipt_path'],row['receipt_sha256']) as read:proof=dict(read)
    need(all(proof.get(k)==c[k] for k in ('catalog_id','generation','base_fence_sha256','verification_sha256')) and
         proof.get('relative')==record['relative'] and proof.get('state')=='removed' and
         proof.get('revision')==row['revision'],'Old-member removal proof differs')
    closed=proof.get('closed_disposition') or {}
    need(all(closed.get(k) is True for k in ('disposition_success','native_close','observed_absent')),
         'Closed native old-member proof is missing')
    if directory:
        need(closed.get('directory_identity')==record['identity'] and closed.get('empty_streamfree') is True,
             'Old-directory native removal proof differs')
    else:need(closed.get('facts')==record['facts'] and closed.get('sha256')==record['sha256'],
              'Old-file native removal proof differs')
    return proof


class SourceDirectoryDelete(NativeItem):
    """DELETE-only selected, write-fenced directory; never a generic bypass."""
    def __enter__(self):
        from native_io import kernel,FileInfo,VerifiedFile
        self.handle=kernel.CreateFileW(str(self.path),0x20000|0x10000|0x81,1,None,3,0x02000000|0x00200000,None)
        if self.handle==ctypes.c_void_p(-1).value:
            self.handle=None;need(False,'Cannot reopen exact source directory for disposition')
        try:
            self.info=FileInfo()
            need(kernel.GetFileInformationByHandle(self.handle,ctypes.byref(self.info)) and
                 self.info.attributes&0x10 and not self.info.attributes&0x400,'Source directory type changed')
            self.view=VerifiedFile(self.path);self.view.handle=self.handle;self.view.info=self.info
            self.facts=self.view.facts();return self
        except BaseException:self.__exit__(None,None,None);raise

    def dispose(self,record,security):
        from native_io import kernel
        from storage_relocation_operator import _no_directory_streams
        need(self.facts['identity']==record['identity'] and
             _delete_fenced(security,self,record['applied_security']),'Source directory identity/fence changed')
        with os.scandir(self.path) as entries:need(next(entries,None) is None,'Old directory is not empty')
        _no_directory_streams(self.path)
        value=wintypes.BOOL(True)
        kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        kernel.SetFileInformationByHandle.restype=wintypes.BOOL
        need(kernel.SetFileInformationByHandle(self.handle,4,ctypes.byref(value),ctypes.sizeof(value)),
             'Exact source directory disposition refused')
        need(kernel.CloseHandle(self.handle),'Source directory native close failed');self.handle=None
        _absent(self.path)


def _acl(security, captured):
    raw = __import__('base64').b64decode(captured['bytes'], validate=True)
    memory = ctypes.create_string_buffer(raw)
    present = wintypes.BOOL(); defaulted = wintypes.BOOL(); pointer = ctypes.c_void_p()
    need(security.api.GetSecurityDescriptorDacl(memory, ctypes.byref(present), ctypes.byref(pointer),
         ctypes.byref(defaulted)) and present.value and pointer, 'Finalization DACL unavailable')
    header = ctypes.string_at(pointer, 8); length = int.from_bytes(header[2:4], 'little')
    need(8 <= length <= 65535, 'Finalization ACL is malformed')
    data = bytearray(ctypes.string_at(pointer, length)); count = int.from_bytes(header[4:6], 'little')
    entries = []; offset = 8
    for _ in range(count):
        size = int.from_bytes(data[offset+2:offset+4], 'little')
        need(size >= 8 and offset+size <= length, 'Finalization ACE is malformed')
        entries.append((offset,bytes(data[offset:offset+size]))); offset += size
    return memory, pointer, data, entries


def _relaxed_acl(security, base):
    memory, pointer, data, entries = _acl(security, base)
    changed = False
    for offset, entry in entries:
        mask = int.from_bytes(entry[4:8], 'little')
        if entry[0] == 1 and entry[1] == 0 and mask & 0x10000 and \
                security.api.IsWellKnownSid(pointer.value+offset+8, 1):
            data[offset+4:offset+8] = (mask & ~0x10000).to_bytes(4,'little'); changed = True
    need(changed, 'Explicit source DELETE denial is missing')
    return data


def _delete_fenced(security, item, base, current=None):
    current = current or security.capture(item)
    if not security.has_write_fence(item,current,include_delete=False):return False
    if current['sddl'].partition('D:')[0] != base['sddl'].partition('D:')[0]:return False
    expected = _relaxed_acl(security,base)
    _, _, actual, _ = _acl(security,current)
    return current['protected'] and actual == expected


def _relax_delete(security, item, base):
    current = security.capture(item)
    need(security_equivalent(current,base), 'Original source fence changed before finalization')
    need(security.has_write_fence(item,current), 'Original source is not write-fenced')
    data = _relaxed_acl(security,base); buffer = ctypes.create_string_buffer(bytes(data))
    status = security.api.SetSecurityInfo(item.handle,1,4|0x80000000,None,None,buffer,None)
    need(status == 0, 'Cannot permit exact old-file disposition: '+str(status))
    need(_delete_fenced(security,item,base), 'DELETE-only relaxation changed source write protection')


def _restore_delete_fence(security, item, base):
    """Restore only this operation's exact full or relaxed DACL transition."""
    current=security.capture(item)
    need(security_equivalent(current,base) or _delete_fenced(security,item,base,current),
         'Old cleanup security changed; foreign permissions retained')
    security.restore(item,base)


@contextlib.contextmanager
def _active(manifest_path,manifest_sha256):
    manifest_path = Path(manifest_path).absolute()
    with contextlib.ExitStack() as stack:
        manifest = parse_manifest(packed(stack.enter_context(pinned_receipt(manifest_path,manifest_sha256))),manifest_sha256)
        seal_path = Path(str(manifest_path)+'.sealed.json')
        seal = stack.enter_context(pinned_receipt(seal_path,digest(seal_path.read_bytes())))
        base_path = Path(str(manifest_path)+'.source-fence.json')
        base = stack.enter_context(pinned_receipt(base_path,seal['source_fence_sha256']))
        plan = stack.enter_context(pinned_receipt(seal['source_plan'],seal['source_plan_sha256']))
        from storage_state_ownership import require_plan_membership
        require_plan_membership(plan)
        need(base['source_plan_sha256']==seal['source_plan_sha256'] and
            plan['catalog_id']==manifest.catalog_id and plan['generation']==manifest.generation and
            plan['source_root']==manifest.source_root and plan['target_root']==manifest.target_root,
            'Finalization source plan is not the sealed independently verified source generation')
        database = Path(seal['target_database']); owner = stack.enter_context(_catalog_owner(database))
        from migration_operation import catalog_identity_lease
        native = stack.enter_context(catalog_identity_lease(database))
        relative=_key(os.path.relpath(database,manifest.target_root))
        binding=manifest.files.get(relative)
        need(binding and 'catalog-storage' in binding.receipt_classes and
             native=={key:(list(binding.target[key]) if key=='identity' else binding.target[key]) for key in native},
             'Current target catalog is not the independently verified native copy')
        target_root=stack.enter_context(NativeItem(manifest.target_root,directory=True))
        need(target_root.facts['identity']==seal['target_root_identity'],'Current target root was replaced')
        with contextlib.closing(_readonly_database(database)) as db:
            rows = db.execute('SELECT * FROM storage_relocation_activation').fetchall()
            need(len(rows)==1 and rows[0]['catalog_id']==manifest.catalog_id and rows[0]['generation']==manifest.generation and
                 rows[0]['manifest_sha256']==manifest_sha256 and rows[0]['source_snapshot_sha256']==manifest.source_snapshot_sha256 and
                 rows[0]['phase']=='active' and rows[0]['revision']==3 and rows[0]['source_fence_sha256']==seal['source_fence_sha256'] and
                 json.loads(rows[0]['target_root_identity'])==seal['target_root_identity'],
                 'Old-data finalization requires an active independently verified generation')
            verification = db.execute('SELECT * FROM storage_relocation_verification').fetchall()
            need(len(verification)==1 and verification[0]['catalog_id']==manifest.catalog_id and
                 verification[0]['generation']==manifest.generation and verification[0]['manifest_sha256']==manifest_sha256,
                 'Independent verification registration is missing')
            verification = dict(verification[0])
        proof = stack.enter_context(pinned_receipt(verification['receipt_path'],verification['receipt_sha256']))
        need(proof.get('complete') is True and proof['manifest_sha256']==manifest_sha256 and
             proof['catalog_id']==manifest.catalog_id and proof['generation']==manifest.generation and
             proof['manifest_path']==str(manifest_path) and proof['source_snapshot_sha256']==manifest.source_snapshot_sha256 and
             proof['source_fence_sha256']==seal['source_fence_sha256'] and
             proof['verified_state_sha256']==verification['verified_state_sha256'], 'Independent verification proof differs')
        root = local_root(base['source_original'])
        need(not _inside(str(root),manifest.target_root) and not _inside(manifest.target_root,str(root)),
             'Old source is an alias/current target, not a separate original')
        from native_io import DirectoryBoundary
        stack.enter_context(DirectoryBoundary(root.anchor,root))
        original = stack.enter_context(NativeItem(root,directory=True))
        need(original.facts['identity']==base['source_root_identity'], 'Old original root was replaced')
        security = Security(); directories=[]
        try:existing=_file_rows(database,{'catalog_id':manifest.catalog_id,'generation':manifest.generation})
        except sqlite3.OperationalError:existing={}
        for record in base['items']:
            if record['kind']!='directory':continue
            prior=existing.get(_key(record['relative']))
            if prior and prior['state']=='removed':
                _removed_proof(dict(catalog_id=manifest.catalog_id,generation=manifest.generation,
                    base_fence_sha256=seal['source_fence_sha256'],verification_sha256=verification['receipt_sha256']),record,prior,True)
                _absent(root/record['relative']);continue
            item = stack.enter_context(NativeItem(root/record['relative'],directory=True))
            need(item.facts['identity']==record['identity'] and
                 (security_equivalent(security.capture(item),record['applied_security']) and security.has_write_fence(item) or
                  prior and prior['state']=='intent' and _delete_fenced(security,item,record['applied_security'])),
                 'Old directory recreation fence changed')
            directories.append((item,record))
        yield stack,manifest_path,manifest,seal,base,plan,database,owner,native,verification,root,directories


@bounded_operation
def plan_source_finalization(manifest_path,manifest_sha256):
    with _active(manifest_path,manifest_sha256) as operation:
        _,path,manifest,seal,base,plan,database,owner,native,verification,root,directories=operation
        from storage_state_ownership import validate_plan_snapshot_membership
        validate_plan_snapshot_membership(plan,seal['source_plan'],base['source_snapshot_sha256'],base['source_original'])
        with verify_source_fence(str(path)+'.source-fence.json',seal['source_fence_sha256']):
            with contextlib.ExitStack() as handles:
                _,files,_=_scan(root,tuple(plan['scopes']),handles)
                expected={_key(row['relative']):row for row in plan['files']}
                need(set(files)==set(expected) and all(files[key]['facts']==expected[key]['facts'] and
                     files[key]['sha256']==expected[key]['sha256'] for key in files), 'Original data changed before cleanup preview')
                security={_key(row['relative']):row for row in base['items'] if row['kind']=='file'}
                result={'schema':SCHEMA,'catalog_id':manifest.catalog_id,'generation':manifest.generation,
                    'manifest_sha256':manifest_sha256,'source_snapshot_sha256':manifest.source_snapshot_sha256,
                    'base_fence_sha256':seal['source_fence_sha256'],'verification_sha256':verification['receipt_sha256'],
                    'source_original':str(root),'source_root_identity':base['source_root_identity'],
                    'target_database':str(database),'target_catalog_identity':native,'scopes':plan['scopes'],
                    'catalog_relative':plan['catalog_relative'],'files':[dict(row,
                         applied_security=security[key]['applied_security']) for key,row in sorted(files.items())],
                    'directories':[record for _,record in directories],
                    'target_review_logical_sha256':logical_catalog_digest(database),
                    'bytes':sum(row['facts']['size'] for row in files.values()),
                    'forfeit_rollback_required':True,'folder_policy':'exact selected data directories only; preserve source and shared parents'}
                return result


def _file_rows(database,certificate):
    with contextlib.closing(_readonly_database(database)) as db:
        return {_key(row['relative']):dict(row) for row in db.execute(
            'SELECT * FROM storage_relocation_source_finalization_files WHERE catalog_id=? AND generation=?',
            (certificate['catalog_id'],certificate['generation']))}


def _publish_file(database,certificate,certificate_path,relative,state,previous,**proof):
    revision=previous['revision']+1 if previous else 1
    record={'schema':'books-source-file-finalization-v1','catalog_id':certificate['catalog_id'],
        'generation':certificate['generation'],'base_fence_sha256':certificate['base_fence_sha256'],
        'verification_sha256':certificate['verification_sha256'],'relative':relative,'state':state,
        'revision':revision,**proof}
    path=Path(str(certificate_path)+'.file-'+digest(relative.encode('utf8'))+'.'+str(revision)+'.json')
    raw=packed(record); sha=digest(raw)
    if path.exists():
        with pinned_receipt(path,sha) as old:need(old==record,'Existing file finalization receipt differs')
    else:create_new(path,raw)
    row=(certificate['catalog_id'],certificate['generation'],relative,state,str(path),sha,revision)
    with contextlib.closing(sqlite3.connect(database,timeout=2)) as db:
        db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
        current=db.execute('SELECT * FROM storage_relocation_source_finalization_files WHERE catalog_id=? AND generation=? AND relative=?',row[:3]).fetchone()
        need((dict(zip(('catalog_id','generation','relative','state','receipt_path','receipt_sha256','revision'),current)) if current else None)==previous,
             'File finalization compare-and-set changed')
        if current:db.execute('UPDATE storage_relocation_source_finalization_files SET state=?,receipt_path=?,receipt_sha256=?,revision=? '
                              'WHERE catalog_id=? AND generation=? AND relative=?',row[3:]+row[:3])
        else:db.execute('INSERT INTO storage_relocation_source_finalization_files VALUES(?,?,?,?,?,?,?)',row)
        db.commit()
    return dict(zip(('catalog_id','generation','relative','state','receipt_path','receipt_sha256','revision'),row))


class FinalizationLease:
    def __init__(self,path,sha256,*,database=None):
        self.path=Path(path).absolute();self.sha256=sha256;self.database=database;self.stack=contextlib.ExitStack();self.live=False
    def __enter__(self):
        from native_io import DirectoryBoundary
        try:
            self.receipt=self.stack.enter_context(pinned_receipt(self.path,self.sha256))
            c=self.receipt;terminal=c.get('schema')==TERMINAL_SCHEMA
            need(terminal or c.get('schema')==SCHEMA,'Unsupported old-source finalization certificate')
            database=Path(self.database or c['target_database']).absolute()
            from migration_operation import catalog_identity_lease
            native=self.stack.enter_context(catalog_identity_lease(database))
            need(native==c['target_catalog_identity'],'Finalization belongs to a different target catalog')
            with contextlib.closing(_readonly_database(database)) as db:
                active=db.execute('SELECT * FROM storage_relocation_activation').fetchall()
                need(len(active)==1 and active[0]['catalog_id']==c['catalog_id'] and active[0]['generation']==c['generation'] and
                     active[0]['manifest_sha256']==c['manifest_sha256'] and active[0]['phase']=='active' and
                     active[0]['revision']==3 and active[0]['source_fence_sha256']==c['base_fence_sha256'],
                     'Finalized source is not bound to the active target generation')
                verification=db.execute('SELECT * FROM storage_relocation_verification').fetchall()
                need(len(verification)==1 and verification[0]['catalog_id']==c['catalog_id'] and
                     verification[0]['generation']==c['generation'] and verification[0]['manifest_sha256']==c['manifest_sha256'] and
                     verification[0]['receipt_sha256']==c['verification_sha256'],
                     'Finalized source independent verification registration changed')
                row=db.execute('SELECT * FROM storage_relocation_source_finalization WHERE catalog_id=?',(c['catalog_id'],)).fetchone()
                need(row and row['generation']==c['generation'] and row['base_fence_sha256']==c['base_fence_sha256'] and
                     row['verification_sha256']==c['verification_sha256'] and row['receipt_path']==str(self.path) and
                     row['receipt_sha256']==self.sha256 and row['state'] in ('finalizing','files-finalized','retired') and row['revision']>0 and
                     (not terminal or row['state']=='retired' and row['revision']==3),
                     'Old-source finalization registration differs')
            if terminal:
                baseline=self.stack.enter_context(pinned_receipt(c['baseline_path'],c['baseline_sha256']))
                need(baseline.get('schema')==SCHEMA and
                     all(baseline.get(k)==c.get(k) for k in baseline if k!='schema'),
                     'Terminal retirement baseline differs')
                rows=_file_rows(database,c)
                expected={_key(r['relative']) for r in c['files']+c['directories']}
                need(set(rows)==expected,'Terminal retirement membership differs')
                for record in c['files']:_removed_proof(c,record,rows[_key(record['relative'])])
                for record in c['directories']:_removed_proof(c,record,rows[_key(record['relative'])],True)
                self.terminal=True;self.live=True;return self
            self.terminal=False
            self.root=local_root(c['source_original']);self.stack.enter_context(DirectoryBoundary(self.root.anchor,self.root))
            self.original=self.stack.enter_context(NativeItem(self.root,directory=True))
            need(self.original.facts['identity']==c['source_root_identity'],'Finalized original root was replaced')
            self.directories=[];self.security=Security();rows=_file_rows(database,c)
            for record in c['directories']:
                prior=rows.get(_key(record['relative']))
                if prior and prior['state']=='removed':
                    _removed_proof(c,record,prior,True);_absent(self.root/record['relative']);continue
                item=self.stack.enter_context(NativeItem(self.root/record['relative'],directory=True))
                need(item.facts['identity']==record['identity'] and
                     (security_equivalent(self.security.capture(item),record['applied_security']) and self.security.has_write_fence(item) or
                      prior and prior['state']=='intent' and _delete_fenced(self.security,item,record['applied_security'])),
                     'Old folder recreation fence changed')
                self.directories.append((item,record))
            rows=_file_rows(database,c);expected={_key(record['relative']):record for record in c['files']}
            need(set(rows).issubset(set(expected)|{_key(r['relative']) for r in c['directories']}),'Unknown old-source finalization member')
            for key,record in expected.items():
                path=self.root/record['relative'];row=rows.get(key);closed=None
                if row:
                    # Keep the verified bytes in memory. No destructive action
                    # uses this proof file, and the actual catalog owner keeps
                    # its SHA registration stable; avoid one persistent handle
                    # per already-removed artifact at ordinary app startup.
                    with pinned_receipt(row['receipt_path'],row['receipt_sha256']) as read:proof=dict(read)
                    need(proof['catalog_id']==c['catalog_id'] and proof['generation']==c['generation'] and
                         proof['base_fence_sha256']==c['base_fence_sha256'] and proof['verification_sha256']==c['verification_sha256'] and
                         proof['relative']==record['relative'] and proof['state']==row['state'] and proof['revision']==row['revision'],
                         'Old-file finalization proof differs')
                    if row['state']=='removed':
                        closed=proof.get('closed_disposition') or {}
                        need(closed.get('disposition_success') is True and closed.get('native_close') is True and
                             closed.get('observed_absent') is True and closed.get('facts')==record['facts'] and
                             closed.get('sha256')==record['sha256'],'Closed native old-file removal proof is missing')
                        _absent(path)
                        continue
                    need(row['state']=='intent','Unknown old-file finalization phase')
                # Mere intent plus missing pathname is never a removal receipt.
                item=self.stack.enter_context(NativeItem(path))
                current=self.security.capture(item)
                need(item.facts==record['facts'] and (security_equivalent(current,record['applied_security']) or
                     row and _delete_fenced(self.security,item,record['applied_security'],current)),
                     'Remaining old file lost its native write fence')
            self.live=True;return self
        except BaseException:self.stack.close();raise
    def revalidate(self):
        need(self.live,'Old-source finalization lease is closed')
        if self.terminal:return
        self.original.revalidate()
        for item,record in self.directories:
            item.revalidate();need(security_equivalent(self.security.capture(item),record['applied_security']) or
                                 _delete_fenced(self.security,item,record['applied_security']),
                                 'Old folder recreation fence changed')
    def __exit__(self,*args):self.live=False;return self.stack.__exit__(*args)


def verify_source_finalization(path,sha256,*,database=None):
    return FinalizationLease(path,sha256,database=database)


@bounded_operation
def apply_source_finalization(manifest_path,manifest_sha256,expected_plan_sha256,*,forfeit_rollback=False):
    need(forfeit_rollback is True,'Old-copy cleanup requires explicit forfeiture of rollback')
    certificate_path=Path(str(Path(manifest_path).absolute())+'.source-finalization.json')
    terminal_path=Path(str(certificate_path)+'.retired.json')
    # Completed replay is read-only and has no old-path dependency. Still pin
    # the explicitly selected manifest and original reviewed baseline SHA.
    if terminal_path.exists():
        with pinned_receipt(manifest_path,manifest_sha256):pass
        terminal_sha=digest(terminal_path.read_bytes())
        with pinned_receipt(terminal_path,terminal_sha) as terminal:
            need(terminal.get('schema')==TERMINAL_SCHEMA and terminal['manifest_sha256']==manifest_sha256 and
                 terminal['baseline_sha256']==expected_plan_sha256,'Retirement replay differs from reviewed source/manifest')
            with contextlib.closing(_readonly_database(terminal['target_database'])) as db:
                registered=db.execute('SELECT state FROM storage_relocation_source_finalization WHERE catalog_id=?',
                                      (terminal['catalog_id'],)).fetchone()
        need(registered and registered[0] in ('finalizing','retired'),'Retirement replay registration differs')
        if registered[0]=='retired':
            with verify_source_finalization(terminal_path,terminal_sha) as lease:need(lease.terminal,'Retirement proof is not terminal')
            return {'phase':'retired','complete':True,'files_removed':0,'bytes_removed':0,
                'receipt_path':str(terminal_path),'receipt_sha256':terminal_sha,'folder_holds':[],
                'disposition':'previously recorded selected-source retirement verified; no old-path action'}
    with _active(manifest_path,manifest_sha256) as operation:
        _,path,manifest,seal,base,plan,database,owner,native,verification,root,directories=operation
        if certificate_path.exists():
            certificate=operation[0].enter_context(pinned_receipt(certificate_path,expected_plan_sha256))
            with verify_source_finalization(certificate_path,expected_plan_sha256,database=database):pass
        else:
            certificate=plan_source_finalization(path,manifest_sha256)
            need(digest(packed(certificate))==expected_plan_sha256,'Old-data cleanup differs from the exact reviewed plan')
            create_new(certificate_path,packed(certificate))
        with contextlib.closing(sqlite3.connect(database,timeout=2)) as db:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE');db.execute(REGISTRY_SQL);db.execute(FILES_SQL)
            expected=(manifest.catalog_id,manifest.generation,seal['source_fence_sha256'],verification['receipt_sha256'],
                      str(certificate_path),expected_plan_sha256,'finalizing',1)
            row=db.execute('SELECT * FROM storage_relocation_source_finalization').fetchall()
            if row:need(len(row)==1 and tuple(row[0][:6])==expected[:6],'Old-source cleanup registration changed')
            else:db.execute('INSERT INTO storage_relocation_source_finalization VALUES(?,?,?,?,?,?,?,?)',expected)
            db.commit()
        records={_key(record['relative']):record for record in certificate['files']}
        rows=_file_rows(database,certificate)
        lock=_key(certificate['catalog_relative']+'.lock');old_owner=None
        if lock in records and (root/records[lock]['relative']).exists():
            old_owner=NativeItem(root/records[lock]['relative'],writable_security=True).__enter__()
        removed=0;bytes_removed=0;security=Security()
        try:
            for key in sorted(records,key=lambda key:(key==lock,key)):
                checkpoint();record=records[key];file=root/record['relative'];previous=rows.get(key)
                if previous and previous['state']=='removed':continue
                if key==lock and old_owner:old_owner.__exit__(None,None,None);old_owner=None
                guard=None
                try:
                    guard=NativeItem(file,writable_security=True).__enter__()
                    need(guard.facts==record['facts'] and guard.sha256()==record['sha256'],'Old cleanup file identity/bytes changed')
                    if not previous:
                        previous=_publish_file(database,certificate,certificate_path,record['relative'],'intent',None,
                            path=str(file),facts=record['facts'],sha256=record['sha256'],applied_security=record['applied_security'])
                        rows[key]=previous
                    current=security.capture(guard)
                    if security_equivalent(current,record['applied_security']):_relax_delete(security,guard,record['applied_security'])
                    else:need(_delete_fenced(security,guard,record['applied_security'],current),'Old cleanup DELETE fence changed')
                    guard.__exit__(None,None,None);guard=None
                    from native_io import VerifiedFile,kernel,DirectoryBoundary
                    with DirectoryBoundary(file.anchor,file.parent),VerifiedFile(file,delete=True) as deleting:
                        need(deleting.facts()==record['facts'] and deleting.sha256()==record['sha256'],
                             'Old cleanup file changed before exact native disposition')
                        from fenced_file_disposition import FencedFileDisposition
                        with FencedFileDisposition(deleting,intent_path=previous['receipt_path'],
                                intent_sha256=previous['receipt_sha256'],facts=record['facts'],
                                sha256=record['sha256'],applied_security=record['applied_security']) as capability:
                            deleting.dispose(fence=capability)
                        need(kernel.CloseHandle(deleting.handle),'Old cleanup native handle did not close')
                        deleting.handle=None
                    with os.scandir(file.parent) as listing:absent=file.name not in {entry.name for entry in listing}
                    need(absent,'Old cleanup disposition is not settled; source remains held')
                    rows[key]=_publish_file(database,certificate,certificate_path,record['relative'],'removed',previous,
                        closed_disposition={'facts':record['facts'],'sha256':record['sha256'],
                            'disposition_success':True,'native_close':True,'observed_absent':True})
                    removed+=1;bytes_removed+=record['facts']['size']
                except BaseException:
                    if guard:guard.__exit__(None,None,None)
                    # Retain WRITE denial even if namespace removal was refused.
                    if file.exists():
                        with NativeItem(file,writable_security=True) as remaining:
                            need(remaining.facts['identity']==record['facts']['identity'],'Old cleanup name was replaced; held')
                            need(remaining.facts==record['facts'] and remaining.sha256()==record['sha256'],
                                 'Old cleanup file changed; permissions retained')
                            _restore_delete_fence(security,remaining,record['applied_security'])
                    raise
        finally:
            if old_owner:old_owner.__exit__(None,None,None)
        # Only the already captured DATA scope members are eligible. Ancestor
        # root/repository handles remain held throughout, and never disposed.
        for guard,record in sorted(directories,key=lambda pair:len(Path(pair[1]['relative']).parts),reverse=True):
            checkpoint();key=_key(record['relative']);previous=rows.get(key)
            need(_key(record['relative']) in {_key(r['relative']) for r in certificate['directories']},
                 'Unreviewed old directory is outside cleanup authority')
            need(guard.facts['identity']==record['identity'],'Old directory identity changed')
            if not previous:
                previous=_publish_file(database,certificate,certificate_path,record['relative'],'intent',None,kind='directory')
                rows[key]=previous
            # Acquire security rights while the original share-READ guard is
            # retained; WRITE_DAC is not FILE_WRITE_DATA sharing access.
            with NativeItem(root/record['relative'],directory=True,writable_security=True) as security_guard:
                current=security.capture(security_guard)
                if security_equivalent(current,record['applied_security']):
                    _relax_delete(security,security_guard,record['applied_security'])
                else:need(_delete_fenced(security,security_guard,record['applied_security'],current),
                          'Old directory DELETE fence changed')
            guard.__exit__(None,None,None) # selected leaf only; parents held
            with SourceDirectoryDelete(root/record['relative'],directory=True) as deleting:
                deleting.dispose(record,security)
            rows[key]=_publish_file(database,certificate,certificate_path,record['relative'],'removed',previous,
                kind='directory',closed_disposition={'directory_identity':record['identity'],'empty_streamfree':True,
                    'disposition_success':True,'native_close':True,'observed_absent':True})
        # Validate every registered closed proof before publishing terminal
        # authority. No intent-only missing member can reach this transaction.
        all_expected={_key(r['relative']) for r in certificate['files']+certificate['directories']}
        need(set(rows)==all_expected,'Old-source retirement has unknown/incomplete members')
        for record in certificate['files']:_removed_proof(certificate,record,rows[_key(record['relative'])])
        for record in certificate['directories']:_removed_proof(certificate,record,rows[_key(record['relative'])],True)
        terminal=dict(certificate,schema=TERMINAL_SCHEMA,baseline_path=str(certificate_path),
                      baseline_sha256=expected_plan_sha256)
        terminal_path=Path(str(certificate_path)+'.retired.json');raw=packed(terminal);terminal_sha=digest(raw)
        if terminal_path.exists():
            with pinned_receipt(terminal_path,terminal_sha) as prior:need(prior==terminal,'Retirement certificate differs')
        else:create_new(terminal_path,raw)
        with contextlib.closing(sqlite3.connect(database,timeout=2)) as db:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
            cursor=db.execute("UPDATE storage_relocation_source_finalization SET state='retired',revision=3,receipt_path=?,receipt_sha256=? "
                "WHERE catalog_id=? AND generation=? AND receipt_path=? AND receipt_sha256=? AND state='finalizing' AND revision=1",
                (str(terminal_path),terminal_sha,manifest.catalog_id,manifest.generation,str(certificate_path),expected_plan_sha256))
            need(cursor.rowcount==1,'Retirement publication compare-and-set changed');db.commit()
        return {'phase':'retired','complete':True,'files_removed':removed,'bytes_removed':bytes_removed,
                'receipt_path':str(terminal_path),'receipt_sha256':terminal_sha,'folder_holds':[],
                'disposition':'selected old application data retired; source/shared parents preserved; rollback forfeited'}
