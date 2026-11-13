"""Finite owned-directory disposal under caller-owned cleanup admission.

The caller owns the cleanup plan/catalog lease and releases only its selected
leaf handle. This helper does not discover ownership or recursively delete.
"""
import contextlib
import base64
import os
from pathlib import Path

from storage_relocation import _inside
from storage_relocation_operator import (NativeItem, Security, create_new, digest,
    packed, pinned_receipt, need, local_root, _no_directory_streams)
from storage_source_finalization import SourceDirectoryDelete, _relax_delete

SCHEMA='books-owned-empty-directory-disposal-v1'


def _read(path):
    sha=digest(path.read_bytes())
    with pinned_receipt(path,sha) as value:return dict(value),sha


def _publish(path,value):
    raw=packed(value);sha=digest(raw)
    if path.exists():
        with pinned_receipt(path,sha) as old:need(old==value,'Directory disposal receipt differs')
    else:create_new(path,raw)
    return sha


def _restore(path,identity,original,expected_acl):
    """Never restore permissions on an unverified name/replacement object."""
    from lifecycle_fence_security import restore_owned_fence
    return restore_owned_fence(path,identity,original,expected_acl,directory=True)


def dispose_owned_empty_directory(path,expected_identity,*,receipt_path):
    path=local_root(path);receipt_path=Path(receipt_path).absolute()
    identity=list(expected_identity)
    need(len(identity)==3 and all(isinstance(n,int) for n in identity),'Expected native directory identity required')
    need(not _inside(str(receipt_path),str(path)),'Disposal receipt must be outside the selected directory')
    need(not _inside(str(receipt_path.resolve()),str(path.resolve())),
         'Disposal receipt aliases the selected directory')
    need(receipt_path.parent.is_dir(),'Owned durable receipt parent is missing')
    from native_io import DirectoryBoundary
    with contextlib.ExitStack() as parents:
        parents.enter_context(DirectoryBoundary(path.anchor,path.parent))
        parents.enter_context(DirectoryBoundary(receipt_path.anchor,receipt_path.parent))
        closed_path=Path(str(receipt_path)+'.closed.json')
        if closed_path.exists():
            intent,_=_read(receipt_path);closed,sha=_read(closed_path)
            need(intent.get('schema')==SCHEMA and intent.get('path')==str(path) and intent.get('identity')==identity and
                 closed.get('schema')==SCHEMA and closed.get('phase')=='removed' and closed.get('path')==str(path) and
                 closed.get('identity')==identity and closed.get('intent_sha256')==digest(packed(intent)) and
                 all(closed.get(k) is True for k in ('native_close','observed_absent','empty_streamfree')),
                 'Existing directory closed proof differs')
            with os.scandir(path.parent) as entries:absent=path.name.casefold() not in {e.name.casefold() for e in entries}
            return dict(removed=absent,held=not absent,phase='removed' if absent else 'replacement-held',
                        receipt_path=str(closed_path),receipt_sha256=sha,
                        reason=None if absent else 'A new object occupies the retired directory name; retained')
        if receipt_path.exists():
            intent,sha=_read(receipt_path)
            need(intent.get('schema')==SCHEMA and intent.get('path')==str(path) and intent.get('identity')==identity,
                 'Existing directory intent differs')
            restored,reason=_restore(path,identity,intent['original_security'],intent.get('expected_fence_acl',''))
            return dict(removed=False,held=True,phase='interrupted-held',receipt_path=str(receipt_path),
                        receipt_sha256=sha,security_restored=restored,
                        reason='Intent has no closed-disposition proof; '+(reason or 'original permissions restored on the verified remaining object'))
        security=Security();intent=None;intent_sha=None;guard=None
        try:
            guard=NativeItem(path,directory=True,writable_security=True).__enter__()
            need(guard.facts['identity']==identity,'Owned directory native identity changed')
            with os.scandir(path) as entries:need(next(entries,None) is None,'Owned directory is nonempty; retained')
            _no_directory_streams(path)
            original=security.capture(guard)
            intent=dict(schema=SCHEMA,phase='intent',path=str(path),identity=identity,
                        facts=guard.facts,original_security=original)
            intent['expected_fence_acl']=base64.b64encode(security.planned_write_fence_acl(original,True)).decode('ascii')
            intent_sha=_publish(receipt_path,intent)
            applied=security.apply_planned_write_fence(guard,intent['original_security'],base64.b64decode(intent['expected_fence_acl'],validate=True))
            need(security.has_write_fence(guard,applied),'Owned directory write fence did not apply')
            _publish(Path(str(receipt_path)+'.fenced.json'),dict(schema=SCHEMA,phase='fenced',
                path=str(path),identity=identity,intent_sha256=intent_sha,applied_security=applied))
            _relax_delete(security,guard,applied)
            guard.__exit__(None,None,None);guard=None
            with SourceDirectoryDelete(path,directory=True) as deleting:
                deleting.dispose(dict(identity=identity,applied_security=applied),security)
            proof=dict(schema=SCHEMA,phase='removed',path=str(path),identity=identity,intent_sha256=intent_sha,
                       native_close=True,observed_absent=True,empty_streamfree=True)
            sha=_publish(closed_path,proof)
            return dict(removed=True,held=False,phase='removed',receipt_path=str(closed_path),receipt_sha256=sha)
        except Exception as error:
            if guard:guard.__exit__(None,None,None);guard=None
            if intent is None:raise
            restored,restore_error=_restore(path,identity,intent['original_security'],intent['expected_fence_acl'])
            held=dict(schema=SCHEMA,phase='held',path=str(path),identity=identity,intent_sha256=intent_sha,
                      reason=str(error),security_restored=restored,restoration_error=restore_error)
            held_path=Path(str(receipt_path)+'.held.json')
            if not held_path.exists():_publish(held_path,held)
            return dict(removed=False,held=True,phase='held',receipt_path=str(receipt_path),receipt_sha256=intent_sha,
                        reason=str(error)+(('; permission restoration held: '+restore_error) if restore_error else ''),
                        security_restored=restored)
        finally:
            if guard:guard.__exit__(None,None,None)
