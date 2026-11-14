"""Explicit finite disposal of a detached generation's old physical DATA copy."""
from contextlib import ExitStack
from pathlib import Path

from native_io import DirectoryBoundary, VerifiedFile, kernel
from storage_relocation import _inside, _key
from storage_relocation_operator import (NativeItem, Security, _no_directory_streams, _scan, bounded_operation, checkpoint,
    create_new, digest, local_root, logical_catalog_digest, need, packed, pinned_receipt,
    security_equivalent)
from storage_source_detach import _archive, verify_runtime_receipt
from storage_source_finalization import (SourceDirectoryDelete, _absent, _relax_delete,
    _restore_delete_fence)

SCHEMA = 'books-detached-source-retirement-v1'


def _absent_control(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return
    need(False, 'Previous retirement intent or result exists; reconcile manually')


def _dispose(item, record, security, path, intent_sha):
    from fenced_file_disposition import FencedFileDisposition
    original = record['applied_security']
    relaxed = False
    try:
        with NativeItem(item.path, directory=item.directory, writable_security=True) as acl:
            item.revalidate()
            need(acl.facts['identity'] == item.facts['identity'], 'Old retirement security handle differs')
            if item.directory:
                # Removing children naturally changes directory timestamps.
                need(next(item.path.iterdir(), None) is None, 'Old directory contains an unreviewed member')
                _no_directory_streams(item.path)
            else:
                need(acl.facts == item.facts, 'Old retirement file facts differ')
            relaxed = True
            _relax_delete(security, acl, original)
        item.__exit__(None, None, None)
        if item.directory:
            with SourceDirectoryDelete(item.path, directory=True) as deleting:
                deleting.dispose(record, security)
        else:
            with DirectoryBoundary(item.path.anchor, item.path.parent), VerifiedFile(item.path, delete=True) as deleting:
                with FencedFileDisposition(deleting, intent_path=path, intent_sha256=intent_sha,
                        facts=record['facts'], sha256=record['sha256'], applied_security=original) as capability:
                    deleting.dispose(fence=capability)
                need(kernel.CloseHandle(deleting.handle), 'Old retirement native close failed')
                deleting.handle = None
        _absent(item.path)
    except BaseException:
        if not relaxed:
            raise
        # A different object or DACL is never adopted during failure recovery.
        try:
            item.path.lstat()
        except FileNotFoundError:
            raise
        with NativeItem(item.path, directory=item.directory, writable_security=True) as remaining:
            need(remaining.facts['identity'] == item.facts['identity'], 'Old retirement name replaced; held')
            _restore_delete_fence(security, remaining, original)
        raise


@bounded_operation
def retire_detached_source(manifest_path, manifest_sha256, *, consent_sha256=None, forfeit_rollback=False):
    """Return exact review by default. Only its explicit consent permits disposition."""
    from catalog_owner import catalog_lock
    from types import SimpleNamespace
    from storage_relocation_native import logical_catalog_location, selected_catalog_relocation
    from storage_state_ownership import require_plan_membership
    path = Path(manifest_path).absolute()
    intent_path = Path(str(path) + '.detached-retirement.json')
    terminal_path = Path(str(intent_path) + '.closed.json')
    pin = {'manifest': str(path), 'sha256': manifest_sha256}
    with selected_catalog_relocation(pin) as context, ExitStack() as held:
        manifest = context.manifest
        db = Path(manifest.target_root) / manifest.scopes[0] / 'inventory.sqlite3'
        with catalog_lock(logical_catalog_location(db), {}):
            context.require_normal_operation()
            need(context.detach_record and context.retention_record and not context.finalization_record,
                 'Retirement requires the separately detached active retained catalog')
            _absent_control(intent_path)
            _absent_control(terminal_path)
            detached = held.enter_context(verify_runtime_receipt(path, manifest, context.detach_record))
            seal_path = Path(str(path) + '.sealed.json')
            seal = held.enter_context(pinned_receipt(seal_path, digest(seal_path.read_bytes())))
            fence = held.enter_context(pinned_receipt(str(path) + '.source-fence.json', detached['source_fence_sha256']))
            plan = held.enter_context(pinned_receipt(seal['source_plan'], detached['source_plan_sha256']))
            require_plan_membership(plan)
            need(plan['scopes'] == fence['scopes'] == list(manifest.scopes) and len(plan['scopes']) == 1 and
                 plan['catalog_relative'] == fence['catalog_relative'] and
                 fence['source_plan_sha256'] == detached['source_plan_sha256'] == seal['source_plan_sha256'] and
                 detached['source_fence_sha256'] == seal['source_fence_sha256'] and
                 manifest_sha256 == seal['manifest_sha256'] and
                 all(plan[field] == fence[field] == detached[field] for field in ('catalog_id','generation','target_root')) and
                 fence['source_snapshot_sha256'] == manifest.source_snapshot_sha256 and
                 fence['source_root_identity'] == detached['source_root_identity'] and
                 fence['source_original'] == detached['source_original'], 'Old retirement authority differs from detach')
            root = local_root(fence['source_original'])
            scope = plan['scopes'][0]
            need(root.drive != db.drive and all(not _inside(str(root), side) and not _inside(side, str(root))
                 for side in (manifest.source_root, manifest.target_root)), 'Old retirement is not a separate physical root')
            _archive(held, detached['backup'], plan, SimpleNamespace(root=root), manifest)
            directories, files, members = _scan(root, (scope,), held, hash_files=True)
            expected_files = {_key(row['relative']): row for row in plan['files']}
            expected_dirs = {_key(row['relative']): row for row in plan['directories']}
            records = {_key(row['relative']): row for row in fence['items']}
            scoped = {key for key in directories if _inside(key, scope)}
            owner_key = _key(plan['catalog_relative'] + '.lock')
            need(files == expected_files and directories == expected_dirs and set(records) == set(files) | scoped and
                 len(records) == len(fence['items']) and owner_key in files and
                 members[''].facts['identity'] == fence['source_root_identity'],
                 'Old retirement source census differs from the detached generation')
            security = Security()
            for key, record in records.items():
                checkpoint()
                item = members[key]
                need(record['kind'] == ('directory' if item.directory else 'file') and
                     item.facts['identity'] == record['identity'] and
                     security_equivalent(security.capture(item), record['applied_security']) and
                     security.has_write_fence(item), 'Old retirement identity or write fence differs')
            target_digest = logical_catalog_digest(db)
            deletion_order = sorted(files, key=lambda key: (key == owner_key, key))
            deletion_order += sorted(scoped, key=lambda key: (-len(Path(key).parts), key))
            proof = dict(schema=SCHEMA, state='intent', catalog_id=manifest.catalog_id, generation=manifest.generation,
                         source_original=str(root), scope=scope, target_database=str(db),
                         target_logical_sha256=target_digest, detach_receipt_sha256=context.detach_record[7],
                         source_plan_sha256=detached['source_plan_sha256'], source_fence_sha256=detached['source_fence_sha256'],
                         backup=detached['backup'], order=deletion_order, files=len(files), directories=len(scoped),
                         bytes=sum(row['facts']['size'] for row in files.values()), forfeit_rollback_required=True)
            sha = digest(packed(proof))
            if consent_sha256 is None:
                return dict(phase='detached-source-retirement-preview', consent_sha256=sha, proof=proof)
            need(consent_sha256 == sha and forfeit_rollback is True,
                 'Retirement requires the exact separately reviewed consent and rollback forfeiture')
            context.require_normal_operation()
            for key, item in context.retained_items.items():
                checkpoint()
                item.revalidate()
                need(security.capture(item)['sha256'] == context.retained['target_members'][key]['security_sha256'],
                     'Retained target changed before old retirement')
            create_new(intent_path, packed(proof))
            held.enter_context(pinned_receipt(intent_path, sha))
            closed = []
            for key in deletion_order:
                checkpoint()
                item = members[key]
                record = dict(records[key], **({} if item.directory else files[key]))
                journal = Path(str(intent_path) + '.' + digest(key.encode('utf8')))
                disposition = dict(record, schema='books-source-file-finalization-v1', state='intent',
                                   path=str(item.path), retirement_sha256=sha)
                pending_sha = create_new(journal, packed(disposition))
                _dispose(item, record, security, journal, pending_sha)
                result = dict(disposition, state='removed', intent_sha256=pending_sha,
                              disposition_success=True, native_close=True, observed_absent=True)
                closed.append(create_new(Path(str(journal) + '.closed.json'), packed(result)))
            _absent(root / scope)
            result = dict(proof, phase='detached-source-retired', state='removed', complete=True,
                          intent_sha256=sha, closed_dispositions=closed)
            receipt_sha = create_new(terminal_path, packed(result))
            return dict(result, receipt_path=str(terminal_path), receipt_sha256=receipt_sha)
