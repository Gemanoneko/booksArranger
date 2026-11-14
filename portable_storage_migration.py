"""Staged portable adoption. Every stage is restartable from immutable receipts.

Only the installer invokes this producer. It never deletes an old catalog,
source tree, archive, installation, or prior transaction record.
"""
import contextlib,ctypes,hashlib,json,os,shutil,sqlite3,uuid
from ctypes import wintypes
from pathlib import Path
from native_io import DirectoryBoundary,VerifiedDirectory,VerifiedFile,FileInfo,kernel,ordinary
from storage_relocation import _key,_inside
from storage_relocation_operator import NativeItem,Security,need,packed,digest
from installation_storage import encode,decode,SCHEMA as INSTALL_SCHEMA


def _read(path):
    from storage_lifecycle import _json
    return _json(path)

# Legacy 0.28.7/8 bound receipts included every diagnostic path update.
# This exception applies only to that typed stage, never generic control JSON.
MAX_BOUND_RECEIPT = 128 * 1024 * 1024


def _read_bound(path,intent,anchor):
    from storage_lifecycle import _json
    from portable_catalog_paths import COLUMNS
    value,facts,sha=_json(path,MAX_BOUND_RECEIPT)
    need(isinstance(value,dict) and set(value)=={'storage_relocation','changed_locations'},'Malformed portable bound receipt')
    pin=value['storage_relocation']
    if intent['bootstrap'].get('storage_relocation'):
        expected=anchor/'Storage'/('runtime-'+str(uuid.uuid5(uuid.UUID(intent['migration_id']),'runtime'))+'.json')
        need(isinstance(pin,dict) and set(pin)=={'manifest','sha256'} and Path(pin['manifest'])==expected,
             'Portable bound receipt refers to another runtime')
        descriptor,_,descriptor_sha=_read(expected)
        need(descriptor_sha==pin['sha256'] and descriptor.get('migration_id')==intent['migration_id'],
             'Portable bound runtime digest changed')
    else:need(pin is None,'Unexpected portable runtime binding')
    changes=value['changed_locations']
    if isinstance(changes,list):
        need(len(changes)<=400000,'Legacy portable change census exceeds bound')
        for row in changes:
            need(isinstance(row,list) and len(row)==5 and row[0] in COLUMNS and row[1] in COLUMNS[row[0]] and
                 type(row[2]) is int and all(isinstance(x,str) and len(x)<=32767 for x in row[3:]),
                 'Malformed legacy portable path change')
    else:
        need(isinstance(changes,dict) and set(changes)=={'schema','count','columns','sha256','authority'} and
             changes['schema']=='books-portable-path-change-summary-v1' and changes['authority'] is False and
             type(changes['count']) is int and 0<=changes['count']<=400000 and isinstance(changes['columns'],dict),
             'Malformed portable path summary')
        from storage_relocation import _sha
        _sha(changes['sha256'])
        need(all(k in {t+'.'+c for t,cols in COLUMNS.items() for c in cols} and type(v) is int and 0<=v<=100000
                 for k,v in changes['columns'].items()) and sum(changes['columns'].values())==changes['count'],
             'Portable path summary count differs')
    return value,facts,sha


def _new(path,value):
    from storage_lifecycle import _write_new
    return _write_new(path,packed(value))['sha256']

def _pending(bootstrap,phase,message):
    return dict(ok=True,bootstrap=str(bootstrap),database='',result='portable_migration_pending',pending=True,phase=phase,message=message)


def _census(data,owner_file=None):
    result={'files':{},'directories':{}}
    security=Security()
    with DirectoryBoundary(data.anchor,data):
        for path in [data,*sorted(data.rglob('*'))]:
            need(not path.is_symlink() and not os.path.isjunction(path),'Portable data contains a link')
            relative='' if path==data else _key(str(path.relative_to(data)))
            if owner_file is not None and path==data/'inventory.sqlite3.lock':
                with _catalog_pin(path) as identity:
                    need(identity==owner_file.facts()['identity'],'Catalog owner is for a different data root')
                result['files'][relative]=dict(facts=owner_file.facts(),security=security.capture(owner_file),sha256=owner_file.sha256())
                continue
            with NativeItem(path,directory=path.is_dir()) as item:
                record=dict(facts=item.facts,security=security.capture(item))
                if not item.directory:
                    need(item.facts['links']==1,'Portable data contains a hard link')
                    record['sha256']=item.sha256()
                result['directories' if item.directory else 'files'][relative]=record
            need(sum(len(v) for v in result.values())<=100000,'Portable data census exceeds bound')
    return result


def _move_directory(source,target,identity):
    """Same-volume no-replace rename by the exact native source handle."""
    source=ordinary(source);target=ordinary(target)
    need(source.drive==target.drive and source!=target,'Native data move needs the same volume')
    with DirectoryBoundary(source.anchor,source.parent,rename_destination=True) as before, \
         DirectoryBoundary(target.anchor,target.parent,rename_destination=True) as after, \
         VerifiedDirectory(source,delete=True) as root:
        need(root.facts()['identity']==identity and not os.path.lexists(target),'Portable data move location changed')
        encoded=str(target).encode('utf-16-le')
        class Rename(ctypes.Structure):
            _fields_=[('flags',wintypes.DWORD),('root',wintypes.HANDLE),('length',wintypes.DWORD),('name',wintypes.WCHAR*(len(encoded)//2+1))]
        value=Rename();value.flags=0;value.root=None;value.length=len(encoded)
        ctypes.memmove(ctypes.addressof(value)+Rename.name.offset,encoded,len(encoded))
        kernel.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        kernel.SetFileInformationByHandle.restype=wintypes.BOOL
        before.revalidate();after.revalidate()
        need(kernel.SetFileInformationByHandle(root.handle,3,ctypes.byref(value),ctypes.sizeof(value)),
             'Portable data native move refused: '+str(ctypes.WinError(ctypes.get_last_error())))
        info=FileInfo();need(kernel.GetFileInformationByHandle(root.handle,ctypes.byref(info)) and
            [info.volume,info.index_high,info.index_low]==identity,'Moved data identity differs')


def _controls(anchor,entries):
    """Copy exact historical bytes; absolute origin strings stay inert evidence."""
    from storage_lifecycle import _write_new
    folder=anchor/'Storage/controls'
    with DirectoryBoundary(folder.anchor,folder,create=True):pass
    result=[]
    for entry in entries:
        origin,sha,kind=entry[:3]
        path=Path(entry[3] if len(entry)==4 else origin);key=_key(str(origin))
        if any(_key(r['origin'])==key for r in result):
            need(next(r for r in result if _key(r['origin'])==key)['sha256']==sha,'Conflicting historical control pins')
            continue
        destination=folder/(digest(key.encode())+'.json')
        with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as held:
            need(held.facts()['links']==1 and held.facts()['size']<=64*1024*1024 and held.sha256()==sha,'Historical control changed')
            raw=b''.join(held.chunks())
        if destination.exists():
            with VerifiedFile(destination) as saved:need(saved.sha256()==sha,'Existing portable control differs')
        else:_write_new(destination,raw)
        result.append(dict(origin=str(origin),relative=str(destination.relative_to(anchor)),sha256=sha,kind=kind))
    return result


def _context(bootstrap,*,physical=False):
    from catalog_owner import catalog_lock
    from storage_relocation_native import selected_catalog_relocation,logical_catalog_location
    stack=contextlib.ExitStack()
    try:
        context=stack.enter_context(selected_catalog_relocation(bootstrap['storage_relocation'],physical_catalog=physical))
        stack.enter_context(catalog_lock(logical_catalog_location(Path(bootstrap['data_dir'])/'inventory.sqlite3'),{}))
        context.require_normal_operation()
        return stack,context
    except BaseException:stack.close();raise


def step(bootstrap_path,plan_sha256,*,reviewed_plan=None):
    from storage_lifecycle import process_check
    bootstrap_path=Path(bootstrap_path).absolute();anchor=bootstrap_path.parent;storage=anchor/'Storage'
    with DirectoryBoundary(storage.anchor,storage,create=True):pass
    journal=storage/'portable-migration.json'
    if not journal.exists():
        bootstrap,facts,sha=_read(bootstrap_path)
        if bootstrap.get('schema')==INSTALL_SCHEMA:
            value=decode(bootstrap,anchor)
            if value.get('storage_relocation'):
                owner,context=_context(value)
                with owner:context.require_normal_operation()
            return dict(ok=True,bootstrap=str(bootstrap_path),database=str(Path(decode(bootstrap,anchor)['data_dir'])/'inventory.sqlite3'),result='portable_selection_kept',pending=False)
        need(bootstrap.get('schema')=='books-arranger-installation-v1','Unsupported installation migration source')
        app=Path(bootstrap['application_dir']);need(app.parent==anchor,'Portable application anchor differs')
        need(process_check([app])['state']=='available','Close Books Arranger before updating its storage')
        migration=str(uuid.uuid4())
        intent=dict(schema='books-portable-migration-intent-v1',migration_id=migration,
            installation_id=bootstrap['installation_id'],completion='Storage/migration-'+migration+'.complete.json',
            plan_sha256=plan_sha256,bootstrap=bootstrap,bootstrap_sha256=sha,bootstrap_facts=facts,
            reviewed_plan=reviewed_plan,
            source_data=bootstrap['data_dir'],target_data=str(anchor/'Data'))
        _new(journal,intent)
        return _pending(bootstrap_path,'prepared','Preparing your library…')
    intent,_,_= _read(journal)
    if (anchor/intent['completion']).exists():
        current,_,_=_read(bootstrap_path)
        need(current.get('schema')==INSTALL_SCHEMA,'Completed portable installation is unavailable')
        value=decode(current,anchor)
        if value.get('storage_relocation'):
            owner,context=_context(value)
            with owner:context.require_normal_operation()
        return dict(ok=True,bootstrap=str(bootstrap_path),database=str(Path(value['data_dir'])/'inventory.sqlite3'),result='portable_selection_kept',pending=False)
    need(intent.get('schema')=='books-portable-migration-intent-v1' and intent['plan_sha256']==plan_sha256,
         'Portable migration belongs to another reviewed installer selection')
    original=intent['bootstrap'];app=Path(original['application_dir']);need(app.parent==anchor,'Portable migration escaped its installation')
    need(process_check([app])['state']=='available','Close Books Arranger before completing setup')
    source=Path(intent['source_data']);target=Path(intent['target_data'])
    need(target==anchor/'Data' and source!=app and not _inside(str(source),str(app)),'Invalid portable data namespace')
    stem=storage/('migration-'+intent['migration_id'])
    def stage(name):return Path(str(stem)+'.'+name+'.json')
    complete=anchor/intent['completion']
    if complete.exists():
        current,_,_=_read(bootstrap_path);done,_,_=_read(complete)
        need(current.get('schema')==INSTALL_SCHEMA and done['binding_sha256']==current.get('storage_relocation',{}).get('sha256'),
             'Completed portable migration configuration changed')
        return dict(ok=True,bootstrap=str(bootstrap_path),database=str(target/'inventory.sqlite3'),result='portable_selection_committed',pending=False)
    relocation=original.get('storage_relocation')
    if relocation and not stage('preview').exists():
        owner,context=_context(original)
        with owner:
            if context.detach_record:
                value=dict(already_detached=True,receipt_sha256=context.detach_record[7],receipt_path=context.detach_record[6])
            else:
                fence=context.source_fence.receipt
                candidates=[]
                for path in (anchor/'Backups').glob('*/complete.json'):
                    proof,_,sha=_read(path)
                    if (proof.get('schema')=='books-cold-preservation-v1' and proof.get('complete') is True and
                        proof.get('archive_root')==str(path.parent) and proof.get('logical_catalog_sha256')):
                        candidates.append((path,sha,proof))
                # Exact source file identities select the archive without inventing authority.
                source_identity=list(context.manifest.directories[context.manifest.scopes[0].lower()].source)
                matches=[(p,s) for p,s,v in candidates if any(r.get('relative')=='.' and
                    r.get('source_facts',{}).get('identity')==source_identity for r in v.get('members',[]))]
                need(len(matches)==1,'No unique verified independent archive is available; existing data was kept')
                archive=dict(path=str(matches[0][0]),sha256=matches[0][1]);source_plan=fence['source_plan_sha256']
                value=dict(archive=archive,source_plan_sha256=source_plan)
            if context.namespace:
                value['origin_ancestry']=context.namespace.value['origin_ancestry']
            else:
                logical=Path(context.manifest.source_root)/context.manifest.scopes[0]
                with DirectoryBoundary(logical.anchor,logical) as boundary:
                    value['origin_ancestry']=[list(row) for row in boundary.identities]
        if not value.get('already_detached'):
            from storage_source_detach import source_detach
            value['preview']=source_detach(relocation['manifest'],relocation['sha256'],value['source_plan_sha256'],value['archive'])
        _new(stage('preview'),value)
        return _pending(bootstrap_path,'verified','Checking copied files…')
    if relocation and not stage('detached').exists():
        preview,_,_=_read(stage('preview'))
        from storage_source_detach import registration,source_detach,receipt_path
        with contextlib.closing(sqlite3.connect((source/'inventory.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:registered=registration(db)
        if registered:
            owner,context=_context(original,physical=True)
            with owner:
                need(context.detach_record==registered,'Source detach registration changed')
                value=dict(receipt_path=registered[6],receipt_sha256=registered[7])
        else:
            receipt=receipt_path(relocation['manifest']);recovery=preview['preview']['consent_sha256'] if receipt.exists() else None
            value=source_detach(relocation['manifest'],relocation['sha256'],preview['source_plan_sha256'],preview['archive'],
                consent_sha256=preview['preview']['consent_sha256'],recovery_receipt_sha256=recovery)
        _new(stage('detached'),value)
        return _pending(bootstrap_path,'detached','Preparing application-owned storage…')
    if not stage('snapshot').exists():
        if relocation:
            owner,context=_context(original,physical=True)
            with owner:
                if context.namespace:
                    ns=context.namespace
                    controls=[(r['origin'],r['sha256'],r['kind'],ns.control_path(r['origin'],r['sha256'])) for r in ns.value['controls']]
                    controls.append((str(context.configuration_path),context.configuration_digest,'previous-runtime',str(context.configuration_path)))
                else:
                    manifest=Path(relocation['manifest'])
                    seal,_,seal_sha=_read(str(manifest)+'.sealed.json')
                    need(seal['manifest_sha256']==context.manifest.digest and
                         seal['source_fence_sha256']==context.activation_row[6],'Portable source seal changed')
                    controls=[(str(manifest),relocation['sha256'],'relocation-manifest'),
                        (str(manifest)+'.sealed.json',seal_sha,'seal'),
                        (str(manifest)+'.source-fence.json',context.activation_row[6],'source-fence'),
                        (seal['source_plan'],seal['source_plan_sha256'],'source-plan'),
                        (context.verification_record[3],context.verification_record[4],'verification'),
                        (context.retention_record[4],context.retention_record[5],'retention'),
                        (context.detach_record[6],context.detach_record[7],'source-detach')]
                history=dict(catalog_id=context.manifest.catalog_id,generation=context.manifest.generation,
                    scope=context.manifest.scopes[0],source_root=context.manifest.source_root,
                    target_root=context.manifest.target_root,controls=[list(row) for row in controls],
                    detach_sha256=context.detach_record[7],retention_sha256=context.retention_record[5],
                    previous_namespace=dict(context.namespace.value) if context.namespace else None,
                    previous_registration=[context.namespace.origin.catalog_id,context.namespace.origin.generation,
                        context.namespace.value['binding_id'],context.namespace.digest,context.namespace.value['revision']] if context.namespace else None)
                history['origin_ancestry']=_read(stage('preview'))[0]['origin_ancestry']
                with DirectoryBoundary(source.anchor,source) as boundary:
                    history['previous_ancestry']=(context.namespace.value['previous_ancestry'] if context.namespace else [])+[list(row) for row in boundary.identities]
                if not stage('history').exists():_new(stage('history'),history)
                else:need(_read(stage('history'))[0]==history,'Portable history changed')
            # Close SQLite admission reads before freezing the mutable catalog;
            # no new SQLite connection may change sidecars during this census.
        with DirectoryBoundary(source.anchor,source),VerifiedFile(source/'inventory.sqlite3.lock',writable=True) as lock:
            snapshot=_census(source,lock)
        _new(stage('snapshot'),snapshot)
        return _pending(bootstrap_path,'snapshotted','Moving your library into application storage…')
    snapshot,_,snapshot_sha=_read(stage('snapshot'))
    if not stage('moved').exists():
        identity=snapshot['directories']['']['facts']['identity']
        if source==target:
            current=_census(target)
        elif not source.exists() and target.exists():
            current=_census(target)
            need(current['directories']['']['facts']['identity']==identity,'Interrupted move target differs')
        else:
            need(source.exists() and (source.drive!=target.drive or not target.exists()),'Portable move locations are ambiguous; both kept')
            with DirectoryBoundary(source.anchor,source),VerifiedFile(source/'inventory.sqlite3.lock',writable=True) as lock:
                current=_census(source,lock);need(current==snapshot,'Data changed after migration review')
                if source.drive!=target.drive:
                    from portable_storage_copy import copy_data
                    copy_journal=Path(str(stem)+'.copy')
                    with DirectoryBoundary(copy_journal.anchor,copy_journal,create=True):pass
                    current=copy_data(source,target,snapshot,copy_journal,owner_file=lock)
            if source.drive==target.drive:
                _move_directory(source,target,identity);current=_census(target)
        need(set(current['files'])==set(snapshot['files']) and set(current['directories'])==set(snapshot['directories']),
             'Moved data membership changed')
        for name,row in snapshot['files'].items():
            if source.drive==target.drive:need(current['files'][name]==row,'Moved data bytes or identity changed')
            else:need(current['files'][name]['sha256']==row['sha256'],'Copied data bytes changed')
        _new(stage('moved'),current)
        return _pending(bootstrap_path,'moved','Binding your preserved library…')
    return _finish(intent,original,anchor,bootstrap_path,stage,snapshot)


def _finish(intent,original,anchor,bootstrap_path,stage,snapshot):
    if stage('published').exists() and original.get('storage_relocation'):
        # Final admission owns the same catalog lock itself.
        return _finish_guarded(intent,original,anchor,bootstrap_path,stage,snapshot)
    moved,_,_=_read(stage('moved'))
    target=anchor/'Data'
    with DirectoryBoundary(target.anchor,target,rename_ancestor=anchor) as root, \
         VerifiedFile(target/'inventory.sqlite3.lock',writable=True), \
         _catalog_pin(target/'inventory.sqlite3') as identity:
        need(list(root.identities[-1][1:])==moved['directories']['']['facts']['identity'] and
             identity==moved['files']['inventory.sqlite3']['facts']['identity'],
             'Current portable catalog was replaced between migration stages')
        return _finish_guarded(intent,original,anchor,bootstrap_path,stage,snapshot)


@contextlib.contextmanager
def _catalog_pin(path):
    handle=kernel.CreateFileW(str(path),0x81,3,None,3,0x00200000,None)
    need(handle!=ctypes.c_void_p(-1).value,'Cannot retain the current catalog native file')
    try:
        info=FileInfo()
        need(kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) and info.links==1 and not info.attributes&0x410,
             'Current catalog is not an ordinary unique native file')
        yield [info.volume,info.index_high,info.index_low]
    finally:kernel.CloseHandle(handle)


def _finish_guarded(intent,original,anchor,bootstrap_path,stage,snapshot):
    from storage_lifecycle import _write_new,_replace_bootstrap,_seal_install_controls
    from storage_portable_namespace import SQL,TABLE,registration
    target=anchor/'Data';relocation=original.get('storage_relocation')
    moved,_,_=_read(stage('moved'))
    if not stage('bound').exists():
        if relocation:
            history,_,_=_read(stage('history'));controls=_controls(anchor,history['controls'])
            origin=next(row for row in controls if row['kind']=='relocation-manifest')
            files={name:dict(prior=snapshot['files'][name]['facts'],current=row['facts'],sha256=row['sha256'],
                    prior_security=snapshot['files'][name]['security'],current_security=row['security'])
                   for name,row in moved['files'].items()}
            directories={name:dict(prior=snapshot['directories'][name]['facts']['identity'],current=row['facts']['identity'],
                    prior_security=snapshot['directories'][name]['security'],current_security=row['security'])
                   for name,row in moved['directories'].items()}
            previous=history.get('previous_namespace')
            for category in ('files','directories'):
                rows=files if category=='files' else directories
                for name,row in rows.items():
                    row['copied_from']=row['prior']
                    row['location_history']=[row['prior']]
                    if previous and name in previous[category]:
                        old=previous[category][name]
                        actual=snapshot[category][name]['facts']
                        current=actual if category=='files' else actual['identity']
                        # Mutable catalog bytes may evolve, but an origin bridge
                        # never transfers to a replacement native object.
                        identity=current['identity'] if category=='files' else current
                        expected=old['current']['identity'] if category=='files' else old['current']
                        need(identity==expected,'Previous portable member native identity changed')
                        row['prior']=old['prior'];row['prior_security']=old['prior_security']
                        for prior_location in old.get('location_history',[old['copied_from']]):
                            if prior_location not in row['location_history']:row['location_history'].append(prior_location)
            binding_id=str(uuid.uuid5(uuid.UUID(intent['migration_id']),'runtime'))
            binding=dict(schema='books-portable-runtime-v1',binding_id=binding_id,
                catalog_id=history['catalog_id'],generation=history['generation'],data='Data',
                origin=dict(path=origin['origin'],relative=origin['relative'],sha256=origin['sha256']),
                controls=controls,root_identity=moved['directories']['']['facts']['identity'],files=files,directories=directories,
                origin_ancestry=history['origin_ancestry'],previous_ancestry=history['previous_ancestry'],
                detach_sha256=history['detach_sha256'],retention_sha256=history['retention_sha256'],
                migration_id=intent['migration_id'],revision=(previous['revision']+1 if previous else 1),
                previous_data=str(Path(intent['source_data'])),
                aliases=list(dict.fromkeys((previous.get('aliases',[]) if previous else [])+[str(Path(intent['source_data']))])))
            path=anchor/'Storage'/('runtime-'+binding_id+'.json');sha=digest(packed(binding))
            if path.exists():need(_read(path)[2]==sha,'Portable runtime binding changed')
            else:_new(path,binding)
            expected=(history['catalog_id'],history['generation'],binding_id,sha,binding['revision'])
            with contextlib.closing(sqlite3.connect((target/'inventory.sqlite3').as_uri()+'?mode=rw',uri=True,timeout=2)) as db:
                db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
                prior=registration(db)
                if prior is None or (history.get('previous_registration') and list(prior)==history['previous_registration']):
                    from portable_catalog_paths import migrate
                    changes=migrate(db,[str(Path(history['source_root'])/history['scope']),str(Path(history['target_root'])/history['scope']),intent['source_data']],str(target))
                    if prior is None:db.execute(SQL)
                    else:db.execute(f'DELETE FROM {TABLE} WHERE catalog_id=?',(history['catalog_id'],))
                    db.execute(f'INSERT INTO {TABLE} VALUES(?,?,?,?,?)',expected);db.commit()
                else:
                    need(prior==expected,'Catalog belongs to another portable transition');changes=[];db.rollback()
            output=dict(storage_relocation=dict(manifest=str(path),sha256=sha),changed_locations=changes)
        else:output=dict(storage_relocation=None,changed_locations=[])
        _new(stage('bound'),output)
        return _pending(bootstrap_path,'bound','Saving your existing settings…')
    bound,_,_=_read_bound(stage('bound'),intent,anchor)
    if not stage('settings').exists():
        settings=Path(original['profile_dir'])/'desktop-settings.json'
        value,facts,sha=_read(settings)
        changed=dict(value,dataDir='Data',catalogMode=original['catalog_mode'])
        if bound['storage_relocation']:
            changed['storage_relocation']=dict(bound['storage_relocation'],manifest=str(Path(bound['storage_relocation']['manifest']).relative_to(anchor)))
        else:changed.pop('storage_relocation',None)
        expected=dict(value=value,facts=facts,sha256=sha)
        if value!=changed:
            _replace_bootstrap(settings,packed(changed),expected)
        current,current_facts,current_sha=_read(settings)
        need(current==changed,'Portable settings publication differs')
        _new(stage('settings'),dict(path=str(settings),facts=current_facts,sha256=current_sha))
        return _pending(bootstrap_path,'settings','Finishing setup…')
    if not stage('published').exists():
        current,facts,sha=_read(bootstrap_path)
        if current.get('schema')==INSTALL_SCHEMA:
            need(current.get('storage_relocation',{}).get('sha256')==(bound['storage_relocation'] or {}).get('sha256'),
                 'Current installation differs from the interrupted publication')
        else:
            need(current==original and sha==intent['bootstrap_sha256'] and facts==intent['bootstrap_facts'],
                 'Installation changed during its portable transition')
            value=dict(original,data_dir=str(target))
            if bound['storage_relocation']:value['storage_relocation']=bound['storage_relocation']
            else:value.pop('storage_relocation',None)
            owner,_,_=_read(original['ownership_manifest']);owner=dict(owner,roots=[dict(r) for r in owner['roots']])
            for row in owner['roots']:
                if row['path']==intent['source_data']:
                    row['path']=str(target);row['identity']=moved['directories']['']['facts']['identity']
                    row['catalog_identity']=moved['files']['inventory.sqlite3']['facts']['identity']
            owner_path=anchor/('books-arranger-owned-portable-'+intent['migration_id']+'.json')
            if owner_path.exists():need(_read(owner_path)[0]==owner,'Portable owner changed')
            else:_new(owner_path,owner)
            value['ownership_manifest']=str(owner_path)
            # Bootstrap references become relative; old receipt bytes remain exact.
            extra=[]
            for field in ('package_ownership','retained_package','retained_profile','ownership_provenance','control_provenance'):
                pin=value.get(field)
                if pin:extra.append((pin['manifest'],pin['sha256'],field))
            mapped=_controls(anchor,extra)
            for field in ('package_ownership','retained_package','retained_profile','ownership_provenance','control_provenance'):
                if value.get(field):
                    row=next(r for r in mapped if _key(r['origin'])==_key(value[field]['manifest']))
                    value[field]=dict(manifest=str(anchor/row['relative']),sha256=row['sha256'])
            encoded=encode(value,anchor)
            _replace_bootstrap(bootstrap_path,packed(encoded),dict(value=current,facts=facts,sha256=sha))
            need(_read(bootstrap_path)[0]==encoded,'Portable bootstrap publication differs')
        _new(stage('published'),dict(bootstrap_sha256=_read(bootstrap_path)[2]))
        return _pending(bootstrap_path,'published','Checking the completed installation…')
    current,_,_=_read(bootstrap_path)
    need(current.get('schema')==INSTALL_SCHEMA and current['data_dir']=='Data','Portable installation readback differs')
    settings,_,_=_read(stage('settings'))
    need(_read(settings['path'])[2]==settings['sha256'],'Portable settings changed before completion')
    if bound['storage_relocation']:
        value=decode(current,anchor);owner,context=_context(value)
        with owner:need(context.namespace is not None,'Portable runtime did not admit its current namespace')
    completion=anchor/intent['completion']
    done=dict(schema='books-portable-migration-complete-v1',migration_id=intent['migration_id'],
        installation_id=intent['installation_id'],bootstrap_sha256=_read(bootstrap_path)[2])
    if bound['storage_relocation']:
        done.update(kind='retained-runtime',binding_sha256=bound['storage_relocation']['sha256'])
    else:done.update(kind='legacy-catalog',data_dir='Data',catalog_identity=moved['files']['inventory.sqlite3']['facts']['identity'])
    _new(completion,done)
    return dict(ok=True,bootstrap=str(bootstrap_path),database=str(target/'inventory.sqlite3'),
                result='portable_selection_committed',pending=False)
