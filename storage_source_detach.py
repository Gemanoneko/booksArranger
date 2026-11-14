"""Explicit release of an active retained generation's dependency on the old source."""
from contextlib import closing, contextmanager, ExitStack
from pathlib import Path
import sqlite3

from storage_relocation import RelocationRefused, _inside, _key, _relative

TABLE = 'storage_relocation_source_detach'
SQL = f'''CREATE TABLE {TABLE}(
    catalog_id TEXT NOT NULL, generation TEXT NOT NULL, manifest_sha256 TEXT NOT NULL,
    source_fence_sha256 TEXT NOT NULL, verification_sha256 TEXT NOT NULL, retention_sha256 TEXT NOT NULL,
    receipt_path TEXT NOT NULL, receipt_sha256 TEXT NOT NULL, PRIMARY KEY(catalog_id, generation))'''
FIELDS = ('catalog_id','generation','manifest_sha256','source_fence_sha256','verification_sha256','retention_sha256')
SCHEMA = 'books-retained-source-detach-v1'


def registration(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone():
        return None
    rows=db.execute(f'SELECT {",".join(FIELDS)},receipt_path,receipt_sha256 FROM {TABLE}').fetchall()
    if len(rows)!=1:
        raise RelocationRefused('Source detach registration is missing or ambiguous')
    return tuple(rows[0])


def receipt_path(manifest_path):
    return Path(str(manifest_path)+'.source-detached.json')


@contextmanager
def verify_runtime_receipt(path,manifest,row,*,receipt_rename_parent=None):
    from storage_relocation_operator import need,pinned_receipt
    expected=receipt_path(path)
    need(Path(row[6])==expected,'Source detach receipt must be the exact operation sibling')
    with pinned_receipt(expected,row[7],receipt_rename_parent=receipt_rename_parent) as proof:
        need(proof.get('schema')==SCHEMA and tuple(proof.get(field) for field in FIELDS)==row[:6] and
             proof.get('target_root')==manifest.target_root and
             proof.get('target_identity')==list(manifest.directories[''].target) and
             proof.get('source_root_identity')==list(manifest.directories[''].source) and
             proof.get('source_snapshot_sha256')==manifest.source_snapshot_sha256 and
             proof.get('forfeit_unreconciled_rollback') is True and proof.get('disposal_authorized') is False,
             'Source detach receipt differs from the pinned active migration')
        yield proof


def _archive(held, backup_pin, plan, fence, manifest):
    from storage_relocation_operator import NativeItem, Security, checkpoint, need, pinned_receipt
    from native_io import DirectoryBoundary
    from source_cleanup import single_stream
    path=Path(backup_pin['path']).absolute()
    archive=held.enter_context(pinned_receipt(path,backup_pin['sha256']))
    root=path.parent
    need(path.name=='complete.json' and root.drive==Path(manifest.target_root).drive and
         not any(_inside(str(root),scope) for scope in (manifest.source_root,manifest.target_root,str(fence.root))) and
         archive.get('schema')=='books-cold-preservation-v1' and archive.get('complete') is True and
         archive.get('authority') is False and archive.get('archive_root')==str(root) and
         archive.get('logical_catalog_sha256')==plan['logical_catalog_sha256'],
         'Detach requires an independent exact cold archive on the local target drive')
    scope=Path(plan['scopes'][0])
    raw=root/'raw'
    held.enter_context(DirectoryBoundary(raw.anchor,raw))
    from storage_relocation_operator import _no_directory_streams
    planned={_key(row['relative']):row for row in plan['files']}
    dirs={_key(row['relative']):row for row in plan['directories'] if _inside(row['relative'],str(scope))}
    archived={}; secured={_key(row['relative']):row['original_security'] for row in plan['security']}
    security=Security()
    children={}
    for row in archive['members']:
        checkpoint()
        directory=row['kind']=='directory'
        need(directory or row['kind']=='file','Malformed retained archive kind')
        relative=Path() if row['relative']=='.' and directory else Path(_relative(row['relative']))
        key=_key(str(scope/relative))
        need(key not in archived and key in (dirs if directory else planned),'Archive scope differs from original plan')
        archived[key]=row
        member=raw/relative
        if member!=raw:
            need(member.parent in children,'Archive child lacks its verified parent')
            children[member.parent].add(member.name)
        item=held.enter_context(NativeItem(member,directory=directory))
        need(item.facts==row['archive_facts'] and security.capture(item)==row['archive_security'] and
             row['source_security']==secured[key],'Archive native facts or permissions changed')
        if directory:
            _no_directory_streams(member)
            children[member]=set()
            need(row['source_facts']['identity']==dirs[key]['identity'],'Archive source directory identity changed')
        else:
            single_stream(member)
            actual=row['source_facts']
            prior=planned[key]['facts']
            if key==_key(plan['catalog_relative']+'-shm'):
                actual=dict(actual,modified=prior['modified'])
            need(actual==prior and item.sha256()==row['sha256']==planned[key]['sha256'],
                 'Archive differs from the original fenced bytes')
    need(set(archived)==set(planned)|set(dirs),'Archive is missing an original member')
    for folder,names in children.items():
        need({child.name for child in folder.iterdir()}==names,'Archive contains unexpected members')
    standalone=root/'standalone'/'inventory.backup.sqlite3'
    held.enter_context(DirectoryBoundary(standalone.anchor,standalone.parent))
    snap=held.enter_context(NativeItem(standalone))
    single_stream(standalone)
    need({item.name for item in standalone.parent.iterdir()}=={standalone.name} and
         archive['standalone']['path']==str(standalone) and snap.facts==archive['standalone']['facts'] and
         snap.sha256()==archive['standalone']['sha256']==manifest.source_snapshot_sha256,
         'Independent standalone backup differs')


from storage_relocation_operator import bounded_operation


@bounded_operation
def source_detach(manifest_path,manifest_sha256,source_plan_sha256,backup_pin,*,consent_sha256=None):
    """Preview by default. An exact reviewed consent publishes an I-only admission."""
    from catalog_owner import catalog_lock
    from storage_relocation_native import logical_catalog_location,selected_catalog_relocation
    from storage_relocation_operator import checkpoint,create_new,digest,need,packed,pinned_receipt
    path=Path(manifest_path).absolute()
    pin={'manifest':str(path),'sha256':manifest_sha256}
    with selected_catalog_relocation(pin) as context, ExitStack() as held:
        manifest=context.manifest
        database=Path(manifest.target_root)/manifest.scopes[0]/'inventory.sqlite3'
        logical=logical_catalog_location(database)
        path_out=receipt_path(path)
        with catalog_lock(logical,{}):
            context.require_normal_operation()
            need(context.retention_record and not context.detach_record and not context.finalization_record and
                 context.source_fence and not path_out.exists(), 'Source detach requires untouched attached retained runtime')
            source_fence=context.source_fence
            fence=source_fence.receipt
            need(fence['source_plan_sha256']==source_plan_sha256,'Source detach plan pin differs')
            plan_path=Path(str(path)+'.sealed.json')
            seal=held.enter_context(pinned_receipt(plan_path,digest(plan_path.read_bytes())))
            need(seal['source_plan_sha256']==source_plan_sha256 and seal['manifest_sha256']==manifest_sha256 and
                 seal['source_fence_sha256']==context.activation_row[6],'Source detach is not bound to current seal')
            plan=held.enter_context(pinned_receipt(seal['source_plan'],source_plan_sha256))
            _archive(held,backup_pin,plan,source_fence,manifest)
            source_fence.revalidate()
            proof=dict(zip(FIELDS,(*context.activation_row[:3],context.activation_row[6],
                                   context.verification_record[4],context.retention_record[5])))
            proof.update(schema=SCHEMA,target_root=manifest.target_root,target_identity=list(manifest.directories[''].target),
                         source_root_identity=list(manifest.directories[''].source),
                         source_snapshot_sha256=manifest.source_snapshot_sha256, source_original=str(source_fence.root),
                         source_plan_sha256=source_plan_sha256,backup=dict(backup_pin),
                         forfeit_unreconciled_rollback=True,disposal_authorized=False)
            sha=digest(packed(proof))
            result=dict(phase='source-detach-preview',consent_sha256=sha,proof=proof)
            if consent_sha256 is None:return result
            need(consent_sha256==sha,'Source detach differs from separately reviewed consent')
            context.require_normal_operation()
            from storage_relocation_operator import Security
            security=Security()
            for key,item in context.retained_items.items():
                checkpoint();item.revalidate()
                need(security.capture(item)['sha256']==context.retained['target_members'][key]['security_sha256'],
                     'Retained target became ineligible during detach')
            output=create_new(path_out,packed(proof))
            with closing(sqlite3.connect(database,timeout=2)) as db:
                db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
                need(registration(db) is None,'Source detach registration appeared during preparation')
                row=tuple(db.execute('SELECT * FROM storage_relocation_activation').fetchone())
                need(row==context.activation_row,'Active generation changed before detach')
                db.execute(SQL)
                db.execute(f'INSERT INTO {TABLE} VALUES(?,?,?,?,?,?,?,?)',
                           (*(proof[field] for field in FIELDS),str(path_out),output))
                source_fence.revalidate();db.commit()
            return dict(result,phase='source-detached',receipt_path=str(path_out),receipt_sha256=output)
