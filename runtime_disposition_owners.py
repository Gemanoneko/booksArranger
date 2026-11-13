"""Process-wide native catalog owners for disposition workers.

Registration is separate from normal-work admission: read-only installer and
verification leases must never create a journal or recover an old intent.
"""
from contextlib import contextmanager
from pathlib import Path
import threading

from storage_relocation import _inside

_lock=threading.RLock()
_owners=[]
_support=[]


@contextmanager
def support_dispositions(parent,scopes):
    """Explicit build/settings/QA owner; never selected by ambient defaults.

    The caller names its already guarded, application-owned parent and finite
    work scopes. A fresh private UUID directory and CREATE_NEW native lock
    establish authority, rather than adopting a previous test/runtime owner.
    """
    import ctypes,uuid
    from native_io import DirectoryBoundary,VerifiedFile,FileInfo,kernel
    from application_publication import _private_create
    from runtime_file_disposition import DispositionContext
    parent=Path(parent).absolute()
    with DirectoryBoundary(parent.anchor,parent):
        root=parent/('file-disposition-'+uuid.uuid4().hex)
        created=_private_create(root)
        with DirectoryBoundary(root.anchor,root) as boundary:
            if list(boundary.identities[-1][1:])!=created['identity']:
                raise RuntimeError('Fresh disposition support directory was replaced')
            owner_path=root/'owner.lock';held=VerifiedFile(owner_path,writable=True)
            held.handle=kernel.CreateFileW(str(owner_path),0x40000081,1,None,1,0x00200000,None)
            if held.handle==ctypes.c_void_p(-1).value:
                held.handle=None;raise RuntimeError('Fresh disposition support owner could not be created')
            try:
                held.info=FileInfo()
                if not kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)):
                    raise RuntimeError('Disposition support native identity unavailable')
                with DispositionContext(root/'ledger',scopes=scopes,owner_handle=held.handle,
                        owner_identity=held.facts()['identity'],owner_path=owner_path,owner_kind='support') as context:
                    with _lock:_support.append(context)
                    try:yield context
                    except Exception as error:
                        raise RuntimeError('Support cleanup is held at '+str(root)+
                            '; original marker SHA-256 '+context.marker_sha256+'. '+str(error)) from error
                    finally:
                        with _lock:_support.remove(context)
            finally:held.__exit__(None,None,None)


def recover_support(root,expected_marker_sha256,*,targets):
    """Explicit recovery of ONE old support owner, never fresh-root adoption.

    ``targets`` must be supplied by the caller's independently retained source
    producer/selection: exact path -> {facts,sha256}. Journal paths cannot add
    targets or turn a missing file into successful disposal. Normal startup
    does not scan arbitrary UUID folders and infer this authority.
    """
    import re
    from native_io import DirectoryBoundary,VerifiedFile
    from runtime_file_disposition import DispositionContext,_load,recover
    from storage_relocation_operator import pinned_receipt,need
    root=Path(root).absolute()
    need(re.fullmatch('file-disposition-[a-f0-9]{32}',root.name) and isinstance(targets,dict) and targets,
         'Explicit old support UUID and independently pinned targets required')
    normalized={str(Path(path).absolute()):value for path,value in targets.items()}
    need(len(normalized)==len(targets) and all(isinstance(v,dict) and set(v)=={'facts','sha256'} for v in normalized.values()),
         'Unsupported support source-producer target schema')
    marker_path=root/'ledger/context.json';owner_path=root/'owner.lock'
    with DirectoryBoundary(root.anchor,root),pinned_receipt(marker_path,expected_marker_sha256) as marker:
        need(marker.get('owner_kind')=='support' and marker.get('owner_path')==str(owner_path) and
             marker.get('root')==str(root/'ledger'),'Old support owner/namespace binding differs')
        for path in (root/'ledger').glob('*.intent.json'):
            intent,_=_load(path);source=normalized.get(intent.get('path'))
            need(source is not None and intent.get('facts')==source['facts'] and intent.get('sha256')==source['sha256'],
                 'Old support journal target is not independently source-producer bound')
        with VerifiedFile(owner_path,writable=True) as held:
            need(held.facts()['identity']==marker.get('owner_identity') and held.facts()['size']==0,
                 'Old support native owner was replaced or changed')
            with DispositionContext(root/'ledger',scopes=tuple(normalized),owner_handle=held.handle,
                    owner_identity=held.facts()['identity'],owner_path=owner_path,owner_kind='support') as context:
                outcome=recover(context)
                return dict(root=str(root),marker_sha256=expected_marker_sha256,**outcome)


def relocated_marker(previous,current):
    """Location bridge only under the selected active catalog generation."""
    from storage_relocation_native import current as selected
    from storage_relocation import _key
    relocation=selected()
    if relocation is None or relocation.database is None:return False
    relocation.require_normal_operation()
    manifest=relocation.manifest
    if set(previous)!=set(current) or previous.get('schema')!=current.get('schema') or \
       previous.get('phase')!='context' or previous.get('owner_kind')!='catalog' or current.get('owner_kind')!='catalog':return False
    try:
        for field in ('owner_path','root'):
            if _key(manifest.logical_location(previous[field]))!=_key(manifest.logical_location(current[field])):return False
        owner=manifest.files.get(_key(manifest.relative(manifest.logical_location(current['owner_path']))))
        if not owner or 'catalog-owner-lock' not in owner.receipt_classes or \
           list(owner.source['identity'])!=previous['owner_identity'] or list(owner.target['identity'])!=current['owner_identity']:return False
        catalog=manifest.files.get(_key(manifest.relative(str(relocation.database))))
        if not catalog or 'catalog-storage' not in catalog.receipt_classes or \
           list(catalog.source['identity'])!=previous['catalog_identity'] or list(catalog.target['identity'])!=current['catalog_identity']:return False
        root=manifest.directories.get(_key(manifest.relative(manifest.logical_location(current['root']))))
        if not root or list(root.source)!=previous['root_identity'] or list(root.target)!=current['root_identity']:return False
        # Open a real boundary; a bare ancestry array cannot acquire authority.
        from native_io import DirectoryBoundary
        root_path=Path(current['root'])
        with DirectoryBoundary(root_path.anchor,root_path) as boundary:
            if not relocation.ancestry_match(boundary,previous['ancestry'],operation_path=root_path):return False
            if [list(item) for item in boundary.identities]!=current['ancestry']:return False
        return True
    except (KeyError,ValueError,TypeError):return False


@contextmanager
def registered_catalog(database, roots, held):
    entry=dict(database=Path(database).absolute(),roots=tuple(Path(p).absolute() for p in roots.values()),
               held=held,context=None,catalog_handle=None,admitted=False)
    with _lock:_owners.append(entry)
    try:yield
    finally:
        with _lock:
            try:
                if entry['context']:entry['context'].close()
                if entry['catalog_handle']:
                    from native_io import kernel
                    if not kernel.CloseHandle(entry['catalog_handle']):
                        raise RuntimeError('Disposition catalog native lease did not close')
            finally:_owners.remove(entry)


def admit_catalog(database):
    """Called only after normal-operation admission, before business workers."""
    database=Path(database).absolute()
    with _lock:
        matches=[e for e in _owners if e['database']==database]
        if not matches:return False
        if len(matches)!=1:raise RuntimeError('Ambiguous native catalog disposition owner')
        matches[0]['admitted']=True
        # New catalogs acquire their stable native identity after schema commit.
        if database.exists():_initialize(matches[0])
        return True


def catalog_created(database):
    database=Path(database).absolute()
    with _lock:
        for entry in _owners:
            if entry['database']==database and entry['admitted']:_initialize(entry)


def _initialize(entry):
    if entry['context']:return entry['context']
    import ctypes
    from native_io import kernel,FileInfo
    from runtime_file_disposition import DispositionContext,recover
    held=entry['held'];database=entry['database']
    catalog_handle=kernel.CreateFileW(str(database),0x81,3,None,3,0x00200000,None)
    if catalog_handle==ctypes.c_void_p(-1).value:raise RuntimeError('Cannot retain exact disposition catalog identity')
    try:
        info=FileInfo()
        if not kernel.GetFileInformationByHandle(catalog_handle,ctypes.byref(info)) or info.attributes&(0x400|0x10) or info.links!=1:
            raise RuntimeError('Disposition catalog must be an ordinary unique native file')
        identity=[info.volume,info.index_high,info.index_low]
        context=DispositionContext(database.parent/'file-disposition-ledger',
            scopes=(database.parent,*entry['roots']),owner_handle=held.handle,
            owner_identity=held.facts()['identity'],owner_path=held.path,
            owner_kind='catalog',catalog_identity=identity,marker_validator=relocated_marker).__enter__()
    except BaseException:kernel.CloseHandle(catalog_handle);raise
    try:
        outcome=recover(context)
        if outcome['held']:raise RuntimeError('File disposition recovery requires attention: '+str(outcome['held']))
    except BaseException:context.close();kernel.CloseHandle(catalog_handle);raise
    entry['catalog_handle']=catalog_handle
    entry['context']=context
    return context


def context_for(path):
    """Actual retained owner, shared across threads; no environment/PID fallback."""
    path=Path(path).absolute()
    with _lock:
        relevant=[e for e in _owners if
                 any(_inside(str(path),str(root)) for root in (e['database'].parent,*e['roots']))]
        if any(not e['admitted'] for e in relevant):
            raise RuntimeError('Exact file removal requires one admitted native catalog owner')
        matches=[e for e in relevant if e['admitted']]
        if not matches:
            support=[c for c in _support if any(_inside(str(path),str(root)) for root in c.scopes)]
            if len(support)==1:return support[0]
        if len(matches)!=1:raise RuntimeError('Exact file removal requires one admitted native catalog owner')
        return _initialize(matches[0])
