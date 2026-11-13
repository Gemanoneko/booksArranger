"""Finite external control-record visibility and explicit retirement preflight.

No directory census grants ownership. Every removable record must originate in
an installation pin or a separately pinned native producer index. Active catalog
references are holds, including references spelled through a different alias.
"""
import hashlib
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import uuid
import base64

from native_io import DirectoryBoundary,VerifiedFile
from source_cleanup import single_stream

SCHEMA='books-control-retirement-plan-v1'
PIN_SLOTS=('ownership_provenance','package_ownership','retained_package','retained_profile','storage_relocation')
SQL_REFERENCES=('storage_relocation_verification','storage_relocation_source_finalization',
                'storage_relocation_source_finalization_files')
MAX_FILES=400000
EXPECTED_SCHEMAS={
 'bootstrap':{'books-arranger-installation-v1'},
 'ownership_manifest':{'books-installation-ownership-v1'},
 'ownership_provenance':{'books-installation-ownership-v1'},
 'package_ownership':{'books-installation-ownership-v1'},
 'retained_package':{'books-legacy-package-retirement-v1'},
 'retained_profile':{'books-retained-profile-copy-v1'},
 'storage_relocation':{'books-storage-relocation-v1'},
 'control_provenance':{'books-control-producer-index-v1'},
 'catalog:storage_relocation_verification':{'books-storage-target-verification-v1'},
 'catalog:storage_relocation_source_finalization':{'books-source-finalization-v1','books-source-retirement-v1'},
 'catalog:storage_relocation_source_finalization_files':{'books-source-file-finalization-v1'},
}
NAMESPACE_SCHEMAS={'books-application-publication-v1','books-application-empty-target-admission-v1',
    'books-owned-empty-directory-disposal-v1','books-owned-file-disposal-v1'}
EXPECTED_SCHEMAS['native-transaction']=NAMESPACE_SCHEMAS
NAMESPACE_SCHEMAS.add('books-control-namespace-creation-v1')
EXPECTED_SCHEMAS['selection-intent']={'books-installation-selection-intent-v1'}


class ControlRecordsHeld(ValueError):
    def __init__(self,message,recovery_record=None):
        self.recovery_record=recovery_record
        super().__init__(message)


def _need(value,message):
    if not value:raise ControlRecordsHeld(message)


def _life():
    import storage_lifecycle
    return storage_lifecycle


def _read(path,sha=None):
    value,facts,digest=_life()._json(str(path))
    _need(sha is None or sha==digest,'Control-record pin changed: '+str(path))
    return value,facts,digest


def _key(path):return os.path.normcase(str(Path(path).absolute()))


def assert_no_pending_overlap(scopes,installation_id=None):
    """A new installation UUID cannot adopt another pending native scope."""
    import winreg
    from terminal_cleanup_journal import BASE,SCHEMA as JOURNAL_SCHEMA,MAX_AUTHORITY
    candidates=[Path(p).absolute() for p in scopes];candidate_keys={_key(os.path.realpath(p)) for p in candidates}
    candidate_ids=set()
    from storage_relocation_operator import NativeItem
    for path in candidates:
        if path.exists():
            with NativeItem(path,directory=path.is_dir()) as held:candidate_ids.add(tuple(held.facts['identity']))
    try:base=winreg.OpenKey(winreg.HKEY_CURRENT_USER,BASE,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY)
    except FileNotFoundError:return
    with base:
        count=winreg.QueryInfoKey(base)[0];_need(count<=512,'Pending cleanup installation bound exceeded')
        for i in range(count):
            identifier=winreg.EnumKey(base,i)
            _need(str(uuid.UUID(identifier))==identifier,'Unrecognized pending cleanup installation')
            with winreg.OpenKey(base,identifier) as installed:
                count_tx=winreg.QueryInfoKey(installed)[0];_need(count_tx<=512,'Pending cleanup transaction bound exceeded')
                for j in range(count_tx):
                    tx=winreg.EnumKey(installed,j)
                    _need(str(uuid.UUID(tx))==tx,'Unrecognized pending cleanup transaction')
                    with winreg.OpenKey(installed,tx) as key:raw,kind=winreg.QueryValueEx(key,'Authority')
                    _need(kind==winreg.REG_BINARY and len(raw)<=MAX_AUTHORITY,'Pending cleanup authority cannot be checked')
                    authority=json.loads(raw)
                    _need(authority.get('schema')==JOURNAL_SCHEMA and authority.get('installation_id')==identifier and
                        authority.get('transaction_id')==tx,'Pending cleanup authority is not bound to its private transaction')
                    record='HKCU\\'+BASE+'\\'+identifier+'\\'+tx
                    if identifier==installation_id:raise ControlRecordsHeld('An interrupted cleanup for this installation must be reviewed first',record)
                    body=base64.b64decode(authority['bootstrap_raw'],validate=True)
                    _need(hashlib.sha256(body).hexdigest()==authority['bootstrap_sha256'],'Pending cleanup bootstrap pin changed')
                    old=json.loads(body);paths=[old[k] for k in ('application_dir','data_dir','profile_dir','temp_dir','downloads_dir','logs_dir')]
                    paths.extend(row['path'] for row in authority.get('root_pins',[]))
                    pending_ids={tuple(row['identity']) for row in authority.get('root_pins',[])}
                    for member in authority.get('members',{}).values():
                        pending_ids.add(tuple(member.get('identity') or member.get('facts',{}).get('identity',[])))
                    if candidate_ids & pending_ids:raise ControlRecordsHeld('Selected native storage belongs to an interrupted cleanup',record)
                    for path in paths:
                        known=_key(os.path.realpath(Path(path).absolute()))
                        if any(_life()._under(Path(known),Path(current)) or _life()._under(Path(current),Path(known)) for current in candidate_keys):
                            raise ControlRecordsHeld('Selected storage overlaps an interrupted cleanup; changing the installation ID does not adopt it',record)


def cleanup_status(installation_id):
    """Read-only recovery inventory; it never adopts or clears a transaction."""
    import winreg
    from terminal_cleanup_journal import BASE,SCHEMA as JOURNAL_SCHEMA,MAX_AUTHORITY
    _need(str(uuid.UUID(installation_id))==installation_id,'Canonical installation UUID required')
    path=BASE+'\\'+installation_id
    try:key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,path,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY)
    except FileNotFoundError:return dict(installation_id=installation_id,pending=False,transactions=[])
    rows=[]
    with key:
        count=winreg.QueryInfoKey(key)[0];_need(count<=512,'Pending cleanup transaction bound exceeded')
        for index in range(count):
            tx=winreg.EnumKey(key,index);_need(str(uuid.UUID(tx))==tx,'Canonical transaction UUID required')
            with winreg.OpenKey(key,tx) as record:raw,kind=winreg.QueryValueEx(record,'Authority')
            _need(kind==winreg.REG_BINARY and len(raw)<=MAX_AUTHORITY,'Pending cleanup authority cannot be checked')
            value=json.loads(raw)
            _need(value.get('schema')==JOURNAL_SCHEMA and value.get('installation_id')==installation_id and value.get('transaction_id')==tx,
                  'Pending cleanup authority is not bound to its transaction')
            rows.append(dict(transaction_id=tx,recovery_record='HKCU\\'+path+'\\'+tx,authority_sha256=hashlib.sha256(raw).hexdigest(),
                scope_paths=[r['path'] for r in value.get('root_pins',[])],
                required_gone=value.get('required_gone',[]),automatic_resume=False))
    return dict(installation_id=installation_id,pending=bool(rows),transactions=rows)


def create_control_namespace(application_dir,kind):
    """Mint a unique private root through the verified atomic creator API."""
    _need(kind in {'installation','cleanup','recovery'},'Unknown control namespace purpose')
    app=_life()._absolute(str(application_dir));token=str(uuid.uuid4())
    root=app.parent/('BooksArrangerRecords-'+token)
    from application_publication import _private_create
    from storage_relocation_operator import NativeItem,Security
    with DirectoryBoundary(root.anchor,root.parent):
        created=_private_create(root)
        with NativeItem(root,directory=True) as held:
            _need(held.facts['identity']==created['identity'] and
                Security().capture(held)['sddl']==created['security']['sddl'],'New control namespace changed before admission')
    return dict(path=str(root),identity=created['identity'],creator_security=created['security'],kind=kind,token=token)


def capture_control_producer(application_dir,installation_id,namespaces,*,extra_files=(),prior_pin=None,deferred_files=()):
    """Seal exact finite transaction members; unknown arrivals remain holds."""
    app=_life()._absolute(str(application_dir));entries={};directories=[]
    if prior_pin:
        prior,_,_=_read(prior_pin['manifest'],prior_pin['sha256'])
        _need(prior.get('schema')=='books-control-producer-index-v1' and prior.get('installation_id')==installation_id and
            _key(prior['application_dir'])==_key(app),'Prior control producer belongs to another installation')
        for entry in prior['files']:entries[_key(entry['path'])]=entry
        directories.extend(prior.get('directories',[]))
        record,_=_file(prior_pin['manifest'],'control_provenance',prior_pin['sha256'])
        entries[_key(record['path'])]={k:record[k] for k in ('path','facts','sha256','kind')}
    from storage_relocation_operator import NativeItem,Security
    for namespace in namespaces:
        root=Path(namespace['path'])
        _need(root.parent==app.parent and root.name=='BooksArrangerRecords-'+namespace['token'],
              'Control namespace differs from its native creation producer')
        with DirectoryBoundary(root.anchor,root.parent),NativeItem(root,directory=True) as held:
            _need(held.facts['identity']==namespace['identity'] and Security().capture(held)['sddl']==namespace['creator_security']['sddl'],
                  'Control namespace native identity or ACL changed')
            for path in root.iterdir():
                _need(path.is_file() and not path.is_symlink(),'Unknown nested control namespace entry: '+str(path))
                entry,value=_file(path,'native-transaction')
                entries[_key(path)]={k:entry[k] for k in ('path','facts','sha256','kind')}
        directories.append(namespace)
    for item in extra_files:
        entry,_=_file(item['path'],item['kind'],item.get('sha256'))
        entries[_key(entry['path'])]={k:entry[k] for k in ('path','facts','sha256','kind')}
    for item in deferred_files:
        # The caller retains the exact CURRENT bootstrap and has preselected
        # this no-replace rotation name. Its original native ID/bytes survive.
        path=Path(item['path']);source=Path(item['source'])
        _need(source==app.parent/_life().BOOTSTRAP and path.parent==app.parent and
              path.name.startswith('books-arranger-installation.previous-') and path.suffix=='.json',
              'Deferred control is not an exact bootstrap rotation')
        _,facts,sha=_read(source,item['sha256']);_need(facts==item['facts'],'Bootstrap changed before producer sealing')
        entries[_key(path)]=dict(path=str(path),facts=facts,sha256=sha,kind='bootstrap')
    _need(len(entries)<=MAX_FILES,'Control producer bound exceeded')
    value=dict(schema='books-control-producer-index-v1',installation_id=installation_id,application_dir=str(app),
        files=list(entries.values()),directories=directories)
    path=app.parent/('books-control-producer-'+str(uuid.uuid4())+'.json')
    written=_life()._write_new(path,json.dumps(value,sort_keys=True).encode())
    return dict(manifest=str(path),sha256=written['sha256'])


def _file(path,kind,pin=None):
    path=Path(path).absolute()
    _life()._local(path)
    _need(path.suffix.casefold()=='.json' and path.name.casefold() not in {'package.json','package-lock.json'},
          'Source/program files are never external control-record ownership')
    _need(not any((ancestor/'.git').exists() for ancestor in (path.parent,*path.parents)),
          'External source-repository records remain protected')
    value,facts,sha=_read(path,pin)
    _need(kind in EXPECTED_SCHEMAS and value.get('schema') in EXPECTED_SCHEMAS[kind],
          'Control record is not a recognized typed producer for '+kind)
    with DirectoryBoundary(Path(path).anchor,Path(path).parent),VerifiedFile(path) as held:
        single_stream(path)
        _need(held.facts()==facts and held.sha256()==sha and facts['links']==1,'Control record changed or is hardlinked')
    return dict(path=str(Path(path).absolute()),kind=kind,facts=facts,sha256=sha,bytes=facts['size']),value


def _bootstrap(path):
    value,facts,sha=_read(path)
    _need(value.get('schema')=='books-arranger-installation-v1','Unrecognized installation bootstrap')
    expected=Path(value['application_dir']).parent/_life().BOOTSTRAP
    _need(_key(expected)==_key(path),'Bootstrap is outside its exact installation parent')
    return value,facts,sha


def _references(path):
    """Typed references only; never recursive substitution of arbitrary JSON."""
    bootstrap,_,_=_bootstrap(path);rows=[dict(path=str(path),kind='bootstrap')]
    rows.append(dict(path=bootstrap['ownership_manifest'],kind='ownership_manifest'))
    for slot in PIN_SLOTS:
        pin=bootstrap.get(slot)
        if pin:
            _need(isinstance(pin,dict) and set(pin)=={'manifest','sha256'},'Malformed installation control pin')
            rows.append(dict(path=pin['manifest'],sha256=pin['sha256'],kind=slot))
    pin=bootstrap.get('control_provenance')
    if pin:
        index,_,_=_read(pin['manifest'],pin['sha256'])
        _need(index.get('schema')=='books-control-producer-index-v1' and
              index.get('installation_id')==bootstrap['installation_id'] and
              _key(index['application_dir'])==_key(bootstrap['application_dir']), 'Control producer belongs to another installation')
        rows.append(dict(path=pin['manifest'],sha256=pin['sha256'],kind='control_provenance'))
        for entry in index.get('files',[]):
            _need(set(entry)=={'path','facts','sha256','kind'},'Unknown control producer entry')
            rows.append(dict(path=entry['path'],sha256=entry['sha256'],kind=entry['kind'],expected_facts=entry['facts']))
    database=Path(bootstrap['data_dir'])/'inventory.sqlite3'
    if database.exists():
        from storage_lifecycle_snapshot import frozen_connection
        with frozen_connection(database) as db:
            db.execute('PRAGMA query_only=ON');db.execute('PRAGMA temp_store=MEMORY')
            for table in SQL_REFERENCES:
                columns={r[1] for r in db.execute('PRAGMA table_info('+table+')')}
                if {'receipt_path','receipt_sha256'}<=columns:
                    found=db.execute('SELECT DISTINCT receipt_path,receipt_sha256 FROM '+table+' LIMIT '+str(MAX_FILES+1)).fetchall()
                    _need(len(found)<=MAX_FILES,'Catalog control-reference bound exceeded')
                    rows.extend(dict(path=p,sha256=s,kind='catalog:'+table) for p,s in found)
    _need(len(rows)<=MAX_FILES,'Installation control-reference bound exceeded')
    return bootstrap,rows


def _census_display(root):
    """Unknown old folders are visible, never thereby eligible for deletion."""
    root=Path(root);files=[];bytes_total=0
    with DirectoryBoundary(root.anchor,root):
        for folder,dirs,names in os.walk(root,followlinks=False):
            with DirectoryBoundary(root,folder):pass
            for name in names:
                path=Path(folder)/name
                with VerifiedFile(path) as held:
                    facts=held.facts();bytes_total+=facts['size'];files.append(dict(path=str(path),identity=facts['identity'],bytes=facts['size']))
                    _need(len(files)<=MAX_FILES,'Control display bound exceeded')
    return dict(path=str(root),scope_paths=[e['path'] for e in files],file_entries=files,bytes=bytes_total,kind='unconfirmed-control-folder',
                can_remove=False,state='ownership_not_confirmed',reason='No pinned producer proves ownership of every member.')


def review_control_records(bootstrap_path,*,other_bootstraps=()):
    bootstrap,refs=_references(bootstrap_path);files={};holds=[]
    _,bootstrap_facts,bootstrap_sha=_read(bootstrap_path)
    roots=[];owner,current_ownership_facts,current_ownership_sha=_read(bootstrap['ownership_manifest'])
    root_pin=bootstrap.get('ownership_provenance');_need(isinstance(root_pin,dict),'Initial installation producer is not pinned')
    initial,ownership_facts,ownership_sha=_read(root_pin['manifest'],root_pin['sha256'])
    _need(initial.get('installation_id')==bootstrap['installation_id'],'Initial control producer belongs to another installation')
    _need(owner.get('installation_id')==bootstrap['installation_id'],'State ownership belongs to another installation')
    for root in owner.get('roots',[]):roots.append(str(Path(root['path']).absolute()))
    for ref in refs:
        path=Path(ref['path']).absolute()
        # A control inside an exact data root belongs to that reviewed data
        # obligation; do not count the same bytes twice in external records.
        if any(_life()._under(path,Path(root)) for root in roots):continue
        try:
            entry,value=_file(path,ref['kind'],ref.get('sha256'))
            if ref.get('expected_facts'):_need(entry['facts']==ref['expected_facts'],'Producer control native identity changed')
            key=tuple(entry['facts']['identity'])
            if key in files:
                files[key]['aliases']=sorted(set(files[key]['aliases']+[str(path)]));continue
            entry['aliases']=[str(path)];files[key]=entry
        except (OSError,ValueError) as error:
            holds.append(dict(path=str(path),state='control_record_unverified',reason=str(error),bytes=None))
    directories=[]
    pin=bootstrap.get('control_provenance')
    if pin:
        index,_,_=_read(pin['manifest'],pin['sha256'])
        from storage_relocation_operator import NativeItem,Security
        known_paths={_key(entry['path']) for entry in files.values()}
        for row in index.get('directories',[]):
            try:
                _need(set(row)=={'path','identity','creator_security','kind','token'},'Unknown control namespace producer fields')
                path=Path(row['path'])
                _need(path.parent==Path(bootstrap['application_dir']).parent and path.name=='BooksArrangerRecords-'+row['token'],
                    'Control directory differs from its exact private producer')
                with DirectoryBoundary(path.anchor,path.parent),NativeItem(path,directory=True) as held:
                    _need(held.facts['identity']==row['identity'] and Security().capture(held)['sddl']==row['creator_security']['sddl'],
                        'Control directory identity or ACL changed')
                    _need(all(p.is_file() and _key(p) in known_paths for p in path.iterdir()),'Unknown control namespace arrival remains protected')
                directories.append(dict(path=str(path),identity=row['identity'],producer_pin=pin))
            except (OSError,ValueError) as error:holds.append(dict(path=row.get('path',''),state='control_namespace_unverified',reason=str(error),bytes=0))
    required={}
    for other in other_bootstraps:
        if _key(other)==_key(bootstrap_path):continue
        try:
            _,references=_references(other)
            for ref in references:
                if not Path(ref['path']).exists():continue
                _,facts,_=_read(ref['path'],ref.get('sha256'))
                required.setdefault(tuple(facts['identity']),[]).append(dict(bootstrap=str(other),kind=ref['kind']))
        except (OSError,ValueError,sqlite3.Error) as error:
            holds.append(dict(path=str(other),state='installation_reference_unchecked',reason=str(error),bytes=None))
    for key,entry in files.items():
        entry['required_by']=required.get(key,[])
        entry['can_remove']=False
        entry['state']='used_by_another_installation' if entry['required_by'] else 'control_retirement_last'
        entry['reason']='Required by another retained installation or catalog.' if entry['required_by'] else \
            'Retire last, after selected state and application removal and a durable terminal journal are verified.'
    for name in ('BooksArrangerInstallerTransactions','CleanupReceipts'):
        folder=Path(bootstrap['application_dir']).parent/name
        if folder.exists():
            try:
                display=_census_display(folder)
                unknown=[entry for entry in display.pop('file_entries') if tuple(entry['identity']) not in files]
                display['scope_paths']=[entry['path'] for entry in unknown]
                display['bytes']=sum(entry['bytes'] for entry in unknown)
                # The container itself is also visible when empty; no name-
                # based authority is invented for a zero-byte directory.
                holds.append(display)
            except (OSError,ValueError) as error:holds.append(dict(path=str(folder),state='control_record_unverified',reason=str(error),bytes=None))
    return dict(schema='books-control-review-v1',bootstrap=str(Path(bootstrap_path).absolute()),
        bootstrap_sha256=bootstrap_sha,bootstrap_facts=bootstrap_facts,
        ownership_path=root_pin['manifest'],ownership_sha256=ownership_sha,ownership_facts=ownership_facts,
        current_ownership_path=bootstrap['ownership_manifest'],current_ownership_sha256=current_ownership_sha,current_ownership_facts=current_ownership_facts,
        installation_id=bootstrap['installation_id'],application_dir=bootstrap['application_dir'],
        state_roots=roots,files=sorted(files.values(),key=lambda e:_key(e['path'])),directories=directories,holds=holds,
        bytes=sum(e['bytes'] for e in files.values())+sum(e.get('bytes') or 0 for e in holds))


def plan_control_retirement(review,*,selected_state_roots=(),application_will_be_removed=False):
    fresh=review_control_records(review['bootstrap'],other_bootstraps=_life().registered_bootstraps())
    _need(fresh==review,'External control records or installation references changed since review')
    _need(not fresh['holds'] and not any(e['required_by'] for e in fresh['files']),
          'Unconfirmed or retained-installation control references remain')
    selected={_key(p) for p in selected_state_roots}
    # Absence is not disposal proof: an unavailable/moved volume must not turn
    # dependent state into permission to erase its last installation records.
    _need(application_will_be_removed is True and all(_key(root) in selected for root in fresh['state_roots']),
          'Retained data or application binaries still require these control records')
    return dict(schema=SCHEMA,review=fresh,files=fresh['files'],state_roots=fresh['state_roots'],
        bootstrap_path=fresh['bootstrap'],bootstrap_sha256=fresh['bootstrap_sha256'],bootstrap_facts=fresh['bootstrap_facts'],
        ownership_path=fresh['ownership_path'],ownership_sha256=fresh['ownership_sha256'],directories=fresh['directories'],
        bytes=fresh['bytes'],phase='awaiting-terminal-journal')


def execute_control_retirement(plan,plan_sha256,*,journal_provider=None):
    raw=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
    _need(hashlib.sha256(raw).hexdigest()==plan_sha256 and plan.get('schema')==SCHEMA,'Control retirement plan changed')
    _need(journal_provider is not None,'A reviewed durable terminal journal provider is required before final control-record deletion')
    # No unjournalled final record deletion or silently retained-file exception.
    return journal_provider.retire_controls(plan)


def execute_terminal_selection(selection,selection_sha256,*,owner_path,process_name='Books Arranger.exe'):
    """One fresh helper owns the complete finite transaction through LAST key."""
    from terminal_cleanup_journal import RegistryCleanupJournal
    _need(selection.get('schema')=='books-terminal-cleanup-selection-v1' and
        hashlib.sha256(json.dumps(selection,sort_keys=True,separators=(',',':')).encode()).hexdigest()==selection_sha256,
        'Terminal selection pin changed')
    control=selection['controls'];review=control['review'];life=_life()
    bootstrap,_,bootstrap_sha=_bootstrap(review['bootstrap'])
    _need(bootstrap_sha==review['bootstrap_sha256'],'Bootstrap changed before terminal cleanup')
    maintenance=bootstrap.get('maintenance_temp_dir')
    owner_path=Path(owner_path).absolute();life._write_new(owner_path,b'')
    removed=[];removed_dirs=[];removed_bytes=0;registry=None
    try:
        with contextlib.ExitStack() as runtime_held, VerifiedFile(owner_path,writable=True) as owner:
            runtime=selection.get('retained_runtime_copy')
            if runtime and runtime.get('verified'):
                fresh=life.runtime_copy_row(bootstrap,runtime['path'])
                _need(fresh==runtime,'Uninstaller runtime copy changed since review')
                boundary=runtime_held.enter_context(DirectoryBoundary(Path(maintenance).anchor,Path(maintenance)))
                _need(list(boundary.identities[-1][1:])==runtime['maintenance_identity'],'Uninstaller maintenance identity changed')
                runtime_held.enter_context(DirectoryBoundary(Path(maintenance),Path(runtime['path']).parent))
                image=runtime_held.enter_context(VerifiedFile(runtime['path']));single_stream(runtime['path'])
                _need(image.facts()==runtime['facts'] and image.sha256()==runtime['sha256'],'Uninstaller runtime copy changed since review')
            identity=[owner.info.volume,owner.info.index_high,owner.info.index_low]
            with RegistryCleanupJournal(review['bootstrap'],review['bootstrap_sha256'],review['ownership_path'],review['ownership_sha256'],
                selection,selection_sha256,owner_handle=owner.handle,owner_identity=identity,owner_path=owner_path,
                process_name=process_name) as journal:
                registry=journal.registry_path
                def remove_file(item):
                    result=journal.dispose_file(item['path'],item['facts'],item['sha256'])
                    _need(result.get('removed') is True,result.get('reason','Terminal file removal is held')+': '+item['path'])
                def remove_directory(item):
                    result=journal.dispose_directory(item['path'],item['identity'])
                    _need(result.get('removed') is True,result.get('reason','Terminal directory removal is held')+': '+item['path'])
                plans=([selection['ordinary']] if selection.get('ordinary') else [])+selection.get('packages',[])
                for plan in plans:
                    for target in plan['targets']:
                        for item in target['files']:
                            remove_file(item)
                            removed.append(item['path']);removed_bytes+=item['facts']['size']
                        for item in target['directories']:
                            remove_directory(item);removed_dirs.append(item['path'])
                directories=selection.get('directories',[])
                internal=[];external=[]
                for item in control['files']:
                    (internal if any(life._under(Path(item['path']),Path(d['path'])) for d in directories) else external).append(item)
                for item in internal:
                    remove_file(item);removed.append(item['path']);removed_bytes+=item['bytes']
                for item in sorted(directories,key=lambda row:len(Path(row['path']).parts),reverse=True):
                    remove_directory(item);removed_dirs.append(item['path'])
                # The active bootstrap is the final filesystem authority. Its
                # sealed bytes remain in HKCU until all selected objects close.
                external.sort(key=lambda row:(_key(row['path'])==_key(review['bootstrap']),_key(row['path'])))
                for item in external:
                    remove_file(item);removed.append(item['path']);removed_bytes+=item['bytes']
                terminal=journal.finish()
        retained_records=list(terminal.get('retained_registry_records',()))
        import winreg
        for path in terminal.get('retained_registry_containers',()):
            size=None
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,path.removeprefix('HKCU\\'),0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
                    if winreg.QueryInfoKey(key)[:2]==(0,0):size=0
            except OSError:pass
            retained_records.append(dict(path=path,bytes=size,reason='Reserved shared registry namespace retained.'))
        if maintenance:
            size=None
            try:size=0 if not any(Path(maintenance).iterdir()) else None
            except (OSError,ValueError):pass
            retained_records.append(dict(path=maintenance,bytes=size,
                reason='Reserved maintenance parent used by this uninstaller. This parent is kept.'))
        if selection.get('retained_runtime_copy'):
            retained_records.append(selection['retained_runtime_copy'])
        return dict(ok=True,result='selected_data_removed',removed_files=len(removed),removed_bytes=removed_bytes,
            removed_directories=removed_dirs,retained_directories=[],remaining_files=[],package_removed=True,controls_removed=True,
            complete=True,registry_record_removed=terminal.get('registry_object_removed',terminal.get('registry_removed',False)),
            registry_namespace_absent=terminal.get('registry_namespace_absent'),retained_records=retained_records)
    except (OSError,ValueError) as error:
        return dict(ok=False,result='partial_cleanup' if registry else 'cleanup_refused',removed_files=len(removed),
            removed_bytes=removed_bytes,removed_directories=removed_dirs,complete=False,package_removed=False,controls_removed=False,
            retained_directories=[p for p in review['state_roots']+[review['application_dir']] if Path(p).exists()],
            remaining_files=[item['path'] for item in control['files'] if Path(item['path']).exists()],
            recovery_record='HKCU\\'+registry if registry else None,reason=str(error),
            retained_records=[life.runtime_copy_row(bootstrap,selection['retained_runtime_copy']['path'])]
                if selection.get('retained_runtime_copy') else [])
