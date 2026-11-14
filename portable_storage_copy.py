"""Verified no-replace portable data copy; caller holds the catalog owner lock.

The source is never changed. Incomplete private stages are retained. A published
target is accepted on retry only through its durable prepublication identity
and complete verified census, never because a destination happens to exist.
"""
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import msvcrt
import os
from pathlib import Path
import shutil
import uuid

from application_publication import _private_create
from native_io import DirectoryBoundary,FileInfo,VerifiedFile,kernel
from source_cleanup import single_stream
from storage_relocation import _inside,_key,_relative
from storage_relocation_operator import (NativeItem,Security,bounded_json,bounded_operation,
    checkpoint,create_new,digest,local_root,need,packed,security_equivalent,_no_directory_streams)

SCHEMA='books-portable-data-copy-v1'
MAX_MEMBERS=100000


def _names(root):
    directories={'':root};files={}
    for folder,children,leaves in os.walk(root,followlinks=False):
        checkpoint();folder=Path(folder)
        need(not folder.is_symlink() and not os.path.isjunction(folder),'Copy directory is a link')
        for name in children:
            path=folder/name;relative=_relative(str(path.relative_to(root)));key=_key(relative)
            need(key not in directories and not path.is_symlink() and not os.path.isjunction(path),'Copy directory is linked or ambiguous')
            directories[key]=path
        for name in leaves:
            path=folder/name;relative=_relative(str(path.relative_to(root)));key=_key(relative)
            need(key not in files and key not in directories and not path.is_symlink(),'Copy file is linked or ambiguous')
            files[key]=path
        need(len(files)+len(directories)<=MAX_MEMBERS,'Copy membership exceeds its bound')
    return directories,files


def _borrow_lock(path,owner_file):
    need(isinstance(owner_file,VerifiedFile) and owner_file.handle and owner_file.writable and
         Path(owner_file.path).name==path.name=='inventory.sqlite3.lock',
         'Copy requires the exact caller-owned catalog lock handle')
    item=NativeItem(path);item.handle=owner_file.handle;item.view=owner_file
    item.facts=owner_file.refresh();item.info=owner_file.info
    # The owner may have opened the historical logical alias. Prove that the
    # ordinary physical name selects this same held identity; this read-only
    # probe shares WRITE only with the already-held catalog owner, never DELETE.
    probe=kernel.CreateFileW(str(path),0x80,1|2,None,3,0x00200000,None)
    need(probe!=ctypes.c_void_p(-1).value,'Cannot identify the caller-owned catalog lock')
    try:
        info=FileInfo()
        need(kernel.GetFileInformationByHandle(probe,ctypes.byref(info)) and info.links==1 and
             not info.attributes&(0x400|0x10) and [info.volume,info.index_high,info.index_low]==item.facts['identity'],
             'Catalog lock name differs from its held owner identity')
    finally:kernel.CloseHandle(probe)
    return item


def _hold(root,stack,*,owner_file=None,hash_files=True):
    directories,files=_names(root);result={'directories':{},'files':{}};held={}
    security=Security()
    for directory,entries in ((True,directories),(False,files)):
        for key,path in sorted(entries.items(),key=lambda pair:(pair[0].count('\\'),pair[0])):
            checkpoint()
            if not directory and owner_file is not None and key=='inventory.sqlite3.lock':
                item=_borrow_lock(path,owner_file)
            else:item=stack.enter_context(NativeItem(path,directory=directory))
            need(not item.facts['attributes']&(0x400|0x200|0x800),'Copy refuses linked, sparse or compressed members')
            if directory:_no_directory_streams(path)
            else:single_stream(path)
            record=dict(facts=item.facts,security=security.capture(item))
            if not directory and hash_files:record['sha256']=item.sha256()
            result['directories' if directory else 'files'][key]=record
            held[(directory,key)]=item
    after_dirs,after_files=_names(root)
    need(set(after_dirs)==set(directories) and set(after_files)==set(files),'Copy membership changed while inspected')
    return result,held


def _source_matches(actual,snapshot,*,hashed):
    need(isinstance(snapshot,dict) and set(snapshot)=={'files','directories'} and
         '' in snapshot['directories'],'Copy requires a complete native source snapshot')
    for kind in ('files','directories'):
        need(set(actual[kind])==set(snapshot[kind]),'Source membership differs from the reviewed snapshot')
        for key,record in actual[kind].items():
            expected=snapshot[kind][key]
            need(record['facts']==expected['facts'] and record['security']==expected['security'],
                 'Source identity, metadata or permissions changed')
            if kind=='files':
                need(isinstance(expected.get('sha256'),str) and len(expected['sha256'])==64,'Source content pin is missing')
                if hashed:need(record['sha256']==expected['sha256'],'Source bytes changed')


def _copy_file(source,destination,expected,security):
    """CREATE_NEW and stream the already-held source; preserve ordinary metadata."""
    value=hashlib.sha256();size=0
    with destination.open('xb') as stream:
        handle=msvcrt.get_osfhandle(stream.fileno());info=FileInfo()
        need(kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) and info.links==1 and
             not info.attributes&(0x10|0x400|0x200|0x800),'New copy has no ordinary unique creator identity')
        identity=[info.volume,info.index_high,info.index_low]
        creator=NativeItem(destination);creator.handle=handle
        descriptor=security.capture(creator)
        for block in source.view.chunks():
            checkpoint();size+=len(block);need(size<=expected['facts']['size'],'Source exceeded its pinned size')
            value.update(block);stream.write(block)
        need(size==expected['facts']['size'] and value.hexdigest()==expected['sha256'],'Source bytes changed during held copy')
        stream.flush();os.fsync(stream.fileno())
        class Basic(ctypes.Structure):
            _fields_=[('creation',ctypes.c_longlong),('access',ctypes.c_longlong),('write',ctypes.c_longlong),('change',ctypes.c_longlong),('attributes',wintypes.DWORD)]
        basic=Basic();basic.write=expected['facts']['modified']//100+116444736000000000
        basic.attributes=expected['facts']['attributes'] or 0x80
        kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        kernel.SetFileInformationByHandle.restype=wintypes.BOOL
        need(kernel.SetFileInformationByHandle(handle,0,ctypes.byref(basic),ctypes.sizeof(basic)),
             'Cannot preserve copied file timestamps and attributes')
    return identity,descriptor


def _target_matches(current,snapshot):
    for kind in ('directories','files'):
        need(set(current[kind])==set(snapshot[kind]),'Copied membership differs')
        for key,record in current[kind].items():
            original=snapshot[kind][key]
            need(security_equivalent(record['security'],original['security'],copied_target=True),'Copied permissions differ')
            need(record['facts']['attributes']==original['facts']['attributes'],'Copied attributes differ')
            if kind=='files':
                need(record['facts']['links']==1 and record['sha256']==original['sha256'] and
                     all(record['facts'][field]==original['facts'][field] for field in ('size','modified','attributes')),
                     'Copied file bytes or ordinary metadata differ')


def _read(path):
    with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as held:
        need(held.facts()['links']==1 and held.facts()['size']<=64*1024*1024,'Copy receipt is not ordinary and bounded')
        raw=b''.join(held.chunks());return bounded_json(raw),digest(raw)


def _journal_boundary(path,parent):
    if path==parent:return DirectoryBoundary(path.anchor,path,rename_destination=True)
    ancestor=parent if path.is_relative_to(parent) and parent!=Path(path.anchor) else None
    return DirectoryBoundary(path.anchor,path,rename_ancestor=ancestor)


@bounded_operation
def copy_data(source,target,snapshot,journal_dir,*,owner_file=None):
    source,target,journal_dir=map(local_root,(source,target,journal_dir))
    need(source!=target and not _inside(str(source),str(target)) and not _inside(str(target),str(source)),
         'Copy roots overlap')
    need(not any(_inside(str(journal_dir),str(root)) for root in (source,target)),
         'Copy journal must be outside both data roots')
    need(source.is_dir() and target.parent.is_dir() and journal_dir.is_dir(),'Copy roots or journal are unavailable')
    snapshot_sha=digest(packed(snapshot));prepared_path=journal_dir/'portable-copy.prepared.json'
    completed_path=journal_dir/'portable-copy.complete.json'
    request=dict(schema=SCHEMA,source=str(source),target=str(target),snapshot_sha256=snapshot_sha)
    security=Security()
    with contextlib.ExitStack() as source_stack:
        rename_ancestor=target.parent if source.is_relative_to(target.parent) and target.parent!=Path(source.anchor) else None
        source_stack.enter_context(DirectoryBoundary(source.anchor,source,rename_ancestor=rename_ancestor))
        parent=source_stack.enter_context(DirectoryBoundary(target.anchor,target.parent,rename_destination=True))
        source_stack.enter_context(_journal_boundary(journal_dir,target.parent))
        need(owner_file is not None or not (source/'inventory.sqlite3.lock').exists(),
             'Copy must retain the caller-owned catalog lock')
        source_now,source_items=_hold(source,source_stack,owner_file=owner_file,hash_files=False)
        _source_matches(source_now,snapshot,hashed=False)
        if prepared_path.exists():
            prepared,prepared_sha=_read(prepared_path)
            need(all(prepared.get(key)==value for key,value in request.items()) and prepared.get('phase')=='verified',
                 'Copy preparation belongs to another reviewed source')
            stage=Path(prepared['stage']);need(stage.parent==target.parent and
                stage.name.startswith('.books-portable-copy-') and prepared['census']['directories']['']['facts']['identity']==prepared['root_identity'],
                'Prepared copy stage is outside its owned parent')
            # A retry cannot use metadata alone as proof of unchanged source.
            for key,expected in snapshot['files'].items():
                need(source_items[(False,key)].sha256()==expected['sha256'],'Source bytes changed before copy recovery')
        else:
            need(not os.path.lexists(target) and not completed_path.exists(),'Existing copy target has no recorded publication authority')
            size=sum(row['facts']['size'] for row in snapshot['files'].values())
            need(shutil.disk_usage(target.parent).free>=size+1024*1024,'Target has insufficient space for a complete independent copy')
            attempt=str(uuid.uuid4());stage=target.parent/('.books-portable-copy-'+attempt)
            create_new(journal_dir/('portable-copy.attempt-'+attempt+'.json'),packed(dict(request,phase='copying',stage=str(stage))))
            creators={}
            with contextlib.ExitStack() as target_stack:
                source_dirs,source_files=_names(source)
                for key,path in sorted(source_dirs.items(),key=lambda pair:(pair[0].count('\\'),pair[0])):
                    checkpoint();destination=stage if key=='' else stage/path.relative_to(source)
                    parent.revalidate()
                    own=_private_create(destination)
                    item=target_stack.enter_context(NativeItem(destination,directory=True,writable_security=True))
                    need(item.facts['identity']==own['identity'] and security.capture(item)==own['security'],
                         'New copy directory identity or creator permissions changed')
                    _no_directory_streams(destination);need(not any(destination.iterdir()),'New copy directory is not empty')
                    creators[(True,key)]=(item,own)
                for key,path in sorted(source_files.items()):
                    checkpoint();destination=stage/path.relative_to(source)
                    identity,descriptor=_copy_file(source_items[(False,key)],destination,snapshot['files'][key],security)
                    item=target_stack.enter_context(NativeItem(destination,writable_security=True));single_stream(destination)
                    need(item.facts['identity']==identity and security.capture(item)==descriptor,'Copied creator identity changed')
                    creators[(False,key)]=(item,dict(identity=identity,security=descriptor))
                # Preserve the source security only on our exact newly-created
                # objects. This never changes the original's ACL or ownership.
                for (directory,key),(item,own) in reversed(list(creators.items())):
                    item.revalidate();expected=snapshot['directories' if directory else 'files'][key]['security']
                    need(security.capture(item)==own['security'] and own['security']['sddl'].partition('D:')[0]==expected['sddl'].partition('D:')[0],
                         'Source owner/group differs from private copy creator')
                    security.restore(item,expected,copied_target=True)
                with contextlib.ExitStack() as verified:
                    census,_=_hold(stage,verified);_target_matches(census,snapshot)
                    need(all(census['directories' if directory else 'files'][key]['facts']['identity']==own['identity']
                         for (directory,key),(item,own) in creators.items()),'Copied native creator identity changed')
                root_identity=census['directories']['']['facts']['identity']
                prepared=dict(request,phase='verified',stage=str(stage),root_identity=root_identity,census=census)
                prepared_sha=create_new(prepared_path,packed(prepared))
        # Source bytes were copied/hashed through these same deny-writer handles.
        # Check permissions and complete membership again before publication.
        current_dirs,current_files=_names(source)
        need(set(current_dirs)==set(snapshot['directories']) and set(current_files)==set(snapshot['files']),
             'Source membership changed before copy publication')
        for (directory,key),item in source_items.items():
            item.revalidate();expected=snapshot['directories' if directory else 'files'][key]
            need(security.capture(item)==expected['security'],'Source permissions changed before publication')
            need(item.view.refresh()==expected['facts'],'Source facts changed before publication')
        if os.path.lexists(target):
            need(not os.path.lexists(stage),'Both staged and published copy locations exist; kept for review')
        else:
            need(stage.is_dir(),'Prepared copy stage is unavailable')
            with contextlib.ExitStack() as check:
                before,_=_hold(stage,check);need(before==prepared['census'],'Prepared copy changed before publication')
            # Reuse the reviewed native directory-handle no-replace rename.
            # All stage read handles are closed, while parent/source guards stay.
            from portable_storage_migration import _move_directory
            _move_directory(stage,target,prepared['root_identity'])
        with contextlib.ExitStack() as after:
            final,_=_hold(target,after)
            need(final==prepared['census'] and final['directories']['']['facts']['identity']==prepared['root_identity'],
                 'Published copy differs from its durable native publication record')
            _target_matches(final,snapshot);parent.revalidate()
            complete=dict(request,phase='complete',prepared_sha256=prepared_sha,root_identity=prepared['root_identity'],census=final)
            if completed_path.exists():
                existing,_=_read(completed_path);need(existing==complete,'Copy completion receipt changed')
            else:create_new(completed_path,packed(complete))
            return final
