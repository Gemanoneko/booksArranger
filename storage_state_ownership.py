"""Finite catalog-state membership, independent of a CLI's proposed scope name."""
import contextlib
import json
import ntpath
from pathlib import Path
import re
import sqlite3

from storage_relocation import RelocationRefused,_inside,_key


def require_catalog_scope(scopes,catalog_relative):
    parent=ntpath.dirname(catalog_relative)
    if not parent or len(scopes)!=1 or _key(scopes[0])!=_key(parent):
        raise RelocationRefused('Only the exact selected catalog parent is a managed state scope; source/Git/shared ancestors are protected')


def catalog_state_membership(database,*,logical_root=None,physical_root=None,immutable=False):
    """Read before fencing/census; hashes are checked through census handles."""
    database=Path(database).absolute();root=Path(logical_root or database.parent)
    physical=Path(physical_root or root)
    owned={};markers=set();directories={'merge-cache','merge-cache/covers','merge-cache/audio-staging',
        'source-recovery','replacement-recovery','chapter-repairs','openlibrary-index'}
    protected=[]
    from runtime_disposition_ledger import closed_ledger_members
    ledger=physical/'file-disposition-ledger'
    ledger_members=closed_ledger_members(ledger)
    if ledger_members:
        directories.add('file-disposition-ledger')
        for member in ledger_members:
            owned[str(root/'file-disposition-ledger'/Path(member['path']).name)]=(member['sha256'],member['size'])
    with contextlib.closing(sqlite3.connect(database.as_uri()+'?mode=ro'+('&immutable=1' if immutable else ''),uri=True,timeout=2)) as db:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('PRAGMA temp_store=MEMORY')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        def pin(path,sha,size=None):
            if not isinstance(path,str) or not ntpath.isabs(path) or not _inside(path,str(root)):return
            if not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):
                raise RelocationRefused('Catalog state has no typed content ownership: '+path)
            previous=owned.get(path)
            if previous and (previous[0]!=sha or previous[1] is not None and size is not None and previous[1]!=size):
                raise RelocationRefused('Conflicting catalog ownership: '+path)
            owned[path]=(sha,size if size is not None else previous[1] if previous else None)
        for table,pathcol,hashcol,sizecol in (('working_files','path','sha256','size'),
                ('storage_cleanup_files','path','sha256','size'),('owned_artifacts','path','sha256','size')):
            if table not in tables:continue
            for row in db.execute('SELECT * FROM '+table):
                if table=='owned_artifacts' and row['kind']=='output':continue
                if table in ('working_files','storage_cleanup_files') and row['state'] in {'removed','absent_after_intent','not_created','creation_intended'}:continue
                pin(row[pathcol],row[hashcol],row[sizecol])
        if 'working_attempts' in tables:
            for row in db.execute('SELECT job_id,attempt_id,producer,state FROM working_attempts'):
                if row['producer']!='closed' and row['state']!='retired':
                    raise RelocationRefused('Unclosed/uncertain producer needs supported source reconciliation before relocation')
                if all(re.fullmatch('[a-f0-9-]{36}',v or '') for v in (row['job_id'],row['attempt_id'])):
                    directories.update({'merge-cache/audio-staging/'+row['job_id'],
                        'merge-cache/audio-staging/'+row['job_id']+'/'+row['attempt_id']})
        if 'source_cleanup' in tables:
            for row in db.execute('SELECT id FROM source_cleanup'):
                if re.fullmatch('[a-f0-9-]{36}',row[0] or ''):directories.add('source-recovery/'+row[0])
        if 'producer_recovery_checkpoints' in tables:
            for row in db.execute('SELECT * FROM producer_recovery_checkpoints'):
                if row['state']!='isolated_retained':continue
                from producer_recovery import verify_retained
                retained=verify_retained(db,row['job_id'],row['attempt_id'])
                for item in retained['native']['files']:pin(item['path'],item['sha256'],item['facts']['size'])
        for table in ('jobs','files','queue'):
            if table not in tables:continue
            columns={r[1] for r in db.execute('PRAGMA table_info('+table+')')}
            for column in ('root','path'):
                if column in columns:
                    protected.extend(r[0] for r in db.execute('SELECT DISTINCT '+column+' FROM '+table)
                        if isinstance(r[0],str) and ntpath.isabs(r[0]))
        if 'audio_jobs' in tables:
            for row in db.execute('SELECT job_id,manifest,output FROM audio_jobs'):
                manifest=json.loads(row['manifest']);output=json.loads(row['output']) if row['output'] else {}
                protected.extend(v for v in [manifest.get('root'),output.get('final_path'),
                    *(s.get('path') for s in manifest.get('sources',[]) if isinstance(s,dict))]
                    if isinstance(v,str) and ntpath.isabs(v))
                identifier=row['job_id'];directories.add('merge-cache/audio-staging/'+identifier)
                marker_relative=Path('merge-cache/audio-staging')/identifier/'ownership.json'
                marker=physical/marker_relative
                if marker.exists():
                    from storage_relocation_operator import pinned_receipt,digest
                    from native_io import VerifiedFile
                    with VerifiedFile(marker) as held:
                        raw=b''.join(held.chunks())
                        if json.loads(raw)!={'job_id':identifier,'manifest':manifest}:
                            raise RelocationRefused('Staging marker differs from its catalog producer')
                    markers.add(str(root/marker_relative))
                cover=manifest.get('cover')
                if isinstance(cover,dict):pin(cover.get('path'),cover.get('sha256'),cover.get('size'))
                artifacts=output.get('validation',{}).get('staging_artifacts',{})
                attempt=artifacts.get('attempt_id')
                if isinstance(attempt,str) and re.fullmatch('[a-f0-9-]{36}',attempt):
                    for name,facts in artifacts.get('files',{}).items():
                        if not isinstance(name,str) or Path(name).name!=name:raise RelocationRefused('Invalid generated artifact name')
                        pin(str(root/marker_relative.parent/attempt/name),facts.get('sha256'),facts.get('size'))
        if 'candidate_context' in tables:
            for row in db.execute('SELECT data FROM candidate_context'):
                for cover in json.loads(row[0]).get('cover_choices',[]):
                    identifier=cover.get('id');sha=cover.get('sha256')
                    if isinstance(identifier,str) and re.fullmatch('[a-f0-9-]{36}',identifier) and isinstance(sha,str):
                        for extension in ('.png','.jpg'):
                            candidate=root/'merge-cache/covers'/(identifier+extension)
                            if (physical/candidate.relative_to(root)).exists():pin(str(candidate),sha)
        if 'audiobook_replacement_retirements' in tables:
            for row in db.execute('SELECT replacement_id,original_path,recovery_json FROM audiobook_replacement_retirements'):
                if not row[2]:continue
                recovery=json.loads(row[2]);path=recovery.get('path')
                expected=root/'replacement-recovery'/row[0]/(__import__('hashlib').sha256(row[1].encode('utf8')).hexdigest()+'.m4b')
                if not isinstance(path,str) or _key(path)!=_key(str(expected)) or recovery.get('purged_at') or recovery.get('copy_pending'):continue
                owned[str(expected)]=(recovery['sha256'],recovery['size'])
                directories.add('replacement-recovery/'+row[0])
    if any(_inside(path,str(root)) or _inside(str(root),path) for path in protected):
        raise RelocationRefused('Selected application state overlaps recorded book library/source/output paths; libraries are protected')
    # Native index provenance is separately validated by the operator's typed
    # classifier. Only its exact admitted leaf/journal/receipt names qualify.
    return {'owned':{_key(path):value for path,value in owned.items()},
        'markers':{_key(path) for path in markers},'directories':set(directories)}


def validate_census_ownership(source,scopes,catalog_relative,files,directories,membership,classes):
    require_catalog_scope(scopes,catalog_relative)
    root=Path(source)/ntpath.dirname(catalog_relative);relative_root=ntpath.dirname(catalog_relative)
    allowed_dirs=set(membership['directories']);proof=[]
    index_paths={key for key,names in classes.items() if set(names)&{'index-leaf','index-journal'}}
    index_controls=set()
    for key,names in classes.items():
        if 'index-leaf' not in names:continue
        leaf=ntpath.basename(key);parent=ntpath.dirname(key)
        owner=leaf.replace('index-','pending-',1) if leaf.startswith('index-') else leaf
        index_controls.add(_key(ntpath.join(parent,owner+'.owner.json')))
        if leaf.startswith('index-'):index_controls.add(key+'.complete.json')
    for record in directories.values():
        if not _inside(record['relative'],scopes[0]):continue
        relative=ntpath.relpath(record['relative'],relative_root).replace('\\','/')
        if relative=='.':continue
        if relative not in allowed_dirs or any(p.casefold()=='.git' for p in relative.split('/')):
            raise RelocationRefused('Unknown/source/Git directory is outside typed catalog ownership: '+record['relative'])
    for key,record in files.items():
        relative=ntpath.relpath(record['relative'],relative_root).replace('\\','/')
        if any(part.casefold()=='.git' for part in relative.split('/')) or \
           Path(relative).suffix.casefold() in {'.py','.pyc','.pyo','.js','.mjs','.cjs','.ts','.tsx','.jsx','.nsh','.nsi','.md','.exe','.dll'} or \
           Path(relative).name.casefold() in {'.gitignore','.gitmodules','package.json','package-lock.json'}:
            raise RelocationRefused('Source/Git/program file is protected independently of supplied ownership rows: '+record['relative'])
        path=_key(str(Path(source)/record['relative']))
        fixed='/' not in relative and (relative in {'inventory.sqlite3','inventory.sqlite3-wal','inventory.sqlite3-shm',
            'inventory.sqlite3-journal','inventory.sqlite3.lock','web-instance.json'} or
            re.fullmatch(r'web-instance\.(?:ended|stale|orphan)-[a-f0-9-]+\.json',relative))
        expected=membership['owned'].get(path)
        index=key in index_paths or key in index_controls
        if relative=='openlibrary-index/import-lock.sqlite3.lock':
            import hashlib
            index=record['facts']['size'] in (0,1) and record['sha256'] in {hashlib.sha256(b'').hexdigest(),hashlib.sha256(b'0').hexdigest()}
        if not (fixed or expected is not None or path in membership['markers'] or index):
            raise RelocationRefused('Unknown file is outside typed catalog ownership: '+record['relative'])
        if expected and (record['sha256']!=expected[0] or expected[1] is not None and record['facts']['size']!=expected[1]):
            raise RelocationRefused('Typed catalog-owned bytes changed: '+record['relative'])
        proof.append({'relative':record['relative'],'sha256':record['sha256'],'kind':
            'catalog-fixed' if fixed else 'catalog-row' if expected else 'index-provenance' if index else 'catalog-marker'})
    return {'schema':'books-typed-catalog-membership-v1','catalog_relative':catalog_relative,
        'scope':scopes[0],'files':proof,'directories':[r['relative'] for r in directories.values()]}


def require_plan_membership(plan):
    require_catalog_scope(plan['scopes'],plan['catalog_relative'])
    ownership=plan.get('owned_state')
    if not isinstance(ownership,dict) or ownership.get('schema')!='books-typed-catalog-membership-v1' or \
       ownership.get('catalog_relative')!=plan['catalog_relative'] or ownership.get('scope')!=plan['scopes'][0] or \
       sorted((r['relative'],r['sha256']) for r in ownership.get('files',[]))!=sorted((r['relative'],r['sha256']) for r in plan['files']) or \
       sorted(ownership.get('directories',[]))!=sorted(r['relative'] for r in plan['directories']):
        raise RelocationRefused('Source plan has no exact typed app-state ownership; source/Git/libraries remain protected')
    for row in plan['files']:
        relative=ntpath.relpath(row['relative'],plan['scopes'][0]).replace('\\','/')
        if any(p.casefold()=='.git' for p in relative.split('/')) or Path(relative).suffix.casefold() in {'.py','.pyc','.pyo','.js','.mjs','.cjs','.ts','.tsx','.jsx','.nsh','.nsi','.md','.exe','.dll'}:
            raise RelocationRefused('Source/Git/program files are never catalog-state retirement authority')


def validate_plan_snapshot_membership(plan,plan_path,snapshot_sha256,physical_source):
    """Re-derive typing from the independently pinned closed SQLite backup.

    A forged owned_state list cannot authorize deletion merely by repeating
    the file census. Never query a frozen original/WAL after its final fence.
    """
    require_plan_membership(plan)
    from native_io import DirectoryBoundary,VerifiedFile
    from source_cleanup import single_stream
    from storage_relocation_operator import classify_historical_files,logical_catalog_digest
    expected=Path(plan_path).absolute().parent/('catalog-snapshot-'+plan['generation']+'.sqlite3')
    if Path(plan.get('snapshot_path','')).absolute()!=expected:
        raise RelocationRefused('Source snapshot is not the exact independently created transaction backup')
    with DirectoryBoundary(expected.anchor,expected.parent),VerifiedFile(expected) as held:
        single_stream(expected)
        if held.facts()['links']!=1 or held.sha256()!=snapshot_sha256 or any(Path(str(expected)+suffix).exists() for suffix in ('-wal','-shm','-journal')):
            raise RelocationRefused('Closed standalone source backup changed or was mixed with journal sidecars')
        if logical_catalog_digest(expected,immutable=True)!=plan['logical_catalog_sha256']:
            raise RelocationRefused('Pinned closed backup differs from the original logical catalog snapshot')
        logical_root=Path(plan['source_root'])/ntpath.dirname(plan['catalog_relative'])
        physical_root=Path(physical_source)/ntpath.dirname(plan['catalog_relative'])
        membership=catalog_state_membership(expected,logical_root=logical_root,physical_root=physical_root,immutable=True)
        classes,held_classes=classify_historical_files(expected,managed_root=plan['source_root'],
            logical_catalog=logical_root/'inventory.sqlite3',index_root=physical_root/'openlibrary-index',immutable=True)
        normalized={_key(ntpath.relpath(path,plan['source_root'])):names for path,names in classes.items() if _inside(path,plan['source_root'])}
        proof=validate_census_ownership(Path(plan['source_root']),plan['scopes'],plan['catalog_relative'],
            {_key(r['relative']):r for r in plan['files']},{_key(r['relative']):r for r in plan['directories']},membership,normalized)
        if proof!=plan['owned_state']:
            raise RelocationRefused('Frozen source catalog does not establish the reviewed app-state membership')


def validate_cleanup_root(manifest,root,*,bootstrap_paths=(),ownership_path=None,ownership_sha256=None):
    """A proposed receipt is evidence, never its own ownership authority.

    The native wizard supplies its exact installation bootstrap; registered
    installations may also be admitted. Every ordinary root must descend from
    its immutable creation producer, with fresh finite member typing below.
    """
    from storage_lifecycle import _json,_absolute,_runtime_name,_runtime_directory
    def need(value,message):
        if not value:raise RelocationRefused(message)
    def read_pin(pin):
        need(isinstance(pin,dict) and set(pin)=={'manifest','sha256'} and
            isinstance(pin['sha256'],str) and re.fullmatch('[a-f0-9]{64}',pin['sha256']),
            'Cleanup requires a pinned installation producer')
        value,_,sha=_json(pin['manifest']);need(sha==pin['sha256'],'Cleanup producer receipt changed')
        return value
    selected_bootstrap=None;authority=None
    for candidate in bootstrap_paths:
        try:bootstrap,_,_=_json(candidate,65536)
        except (ValueError,OSError):continue
        if bootstrap.get('schema')=='books-arranger-installation-v1' and \
           bootstrap.get('installation_id')==manifest.get('installation_id') and \
           _key(bootstrap.get('application_dir',''))==_key(manifest.get('application_dir','')):
            selected_bootstrap=str(_absolute(str(candidate)));authority=bootstrap;break
    need(authority is not None,'Cleanup ownership is not bound to an explicit or registered installation')
    role=root.get('role');path=str(_absolute(root['path']))
    if role=='application':
        pin=authority.get('package_ownership');initial=read_pin(pin)
        need(ownership_path is not None and _key(str(_absolute(ownership_path)))==_key(str(_absolute(pin['manifest']))) and
             ownership_sha256==pin['sha256'] and initial==manifest and len(initial.get('roots',[]))==1 and
             root==initial['roots'][0] and _key(path)==_key(authority['application_dir']),
             'Application cleanup requires its exact installed-package producer')
        return True
    if role=='backups' and authority.get('retained_package'):
        retained=read_pin(authority['retained_package'])
        if _key(path)==_key(retained.get('retained_application','')):
            need(retained.get('schema')=='books-legacy-package-retirement-v1' and retained.get('state')=='original-retained' and
                root.get('identity')==retained.get('root_identity') and root.get('files')==retained.get('files'),
                'Retained original package differs from its closed producer')
            return True
    pin=authority.get('ownership_provenance');initial=read_pin(pin)
    producer=manifest.get('producer')
    if producer is None:
        need(ownership_path is not None and _key(str(_absolute(ownership_path)))==_key(str(_absolute(pin['manifest']))) and
            ownership_sha256==pin['sha256'] and manifest==initial,'Cleanup receipt has no immutable creation producer')
    else:
        need(isinstance(producer,dict) and set(producer)=={'bootstrap','manifest','sha256'} and
            _key(str(_absolute(producer['bootstrap'])))==_key(selected_bootstrap) and
            {k:producer[k] for k in ('manifest','sha256')}==pin,
            'Refreshed cleanup receipt changed its original producer')
    need(initial.get('installation_id')==manifest.get('installation_id') and
        _key(initial.get('application_dir',''))==_key(authority['application_dir']),
        'Creation producer belongs to a different installation')
    originals=[r for r in initial.get('roots',[]) if _key(r.get('path',''))==_key(path)]
    need(len(originals)==1 and all(root.get(k)==originals[0].get(k) for k in ('identity','role','provenance','catalog_identity')),
        'Cleanup location or native root differs from the installation-created state')
    provenance=root.get('provenance');files=root.get('files',[]);dirs=root.get('directories',[])
    if provenance in {'created-data-v1','recognized-catalog-v1'}:
        database=Path(path)/'inventory.sqlite3'
        if not database.exists():
            need(provenance=='created-data-v1' and not files and not dirs and not any(Path(path).iterdir()),
                'An uninitialized created catalog is not empty')
            return True
        # Installer cleanup must not open the reviewed original SQLite tuple:
        # even a mode=ro WAL reader can change SHM read marks after census.
        # The source-migration snapshot path above remains independent.
        from storage_lifecycle_snapshot import frozen_catalog
        from storage_relocation_operator import classify_historical_files
        with frozen_catalog(database) as snapshot:
            membership=catalog_state_membership(snapshot,logical_root=database.parent,
                physical_root=database.parent,immutable=True)
            classes,held=classify_historical_files(snapshot,managed_root=str(Path(path).parent),
                logical_catalog=database,index_root=database.parent/'openlibrary-index',immutable=True)
        folder=Path(path).name
        census={_key(ntpath.join(folder,r['relative'])):dict(relative=ntpath.join(folder,r['relative']),
            facts=r['facts'],sha256=r['sha256']) for r in files}
        directories={_key(ntpath.join(folder,r['relative'])):{'relative':ntpath.join(folder,r['relative'])} for r in dirs}
        # Index leaves are typed by native owner/control provenance, never by a
        # bare file extension in a forged ownership list.
        normalized={_key(ntpath.relpath(p,str(Path(path).parent))):v for p,v in classes.items() if _inside(p,path)}
        validate_census_ownership(Path(path).parent,[folder],ntpath.join(folder,'inventory.sqlite3'),
            census,directories,membership,normalized)
    else:
        runtime_provenance=provenance
        if provenance=='retained-profile-v1':
            proof=read_pin(authority.get('retained_profile'))
            from storage_lifecycle import _current_user_sid
            need(proof.get('schema')=='books-retained-profile-copy-v1' and proof.get('account_sid')==_current_user_sid() and
                 _key(proof.get('source_profile',''))==_key(path) and proof.get('source_identity')==root['identity'] and
                 _key(proof.get('target_profile',''))==_key(authority['profile_dir']) and
                 proof.get('source_files')==originals[0].get('files'),
                 'Retained profile lacks its exact same-account original copy producer')
            source_files=proof.get('source_files',[]);target_files=proof.get('target_files',[])
            need(isinstance(source_files,list) and isinstance(target_files,list) and
                 [(r.get('relative'),r.get('sha256'),r.get('facts',{}).get('size')) for r in source_files]==
                 [(r.get('relative'),r.get('sha256'),r.get('facts',{}).get('size')) for r in target_files],
                 'Retained profile copy does not preserve exact relative content membership')
            settings=proof.get('settings',{});catalog=proof.get('catalog',{})
            need(isinstance(catalog.get('identity'),list) and len(catalog['identity'])==3 and
                 any(all(member.get(k)==settings.get(k) for k in ('relative','facts','sha256')) for member in source_files),
                 'Retained profile copy lacks its settings/catalog affinity proof')
            runtime_provenance='created-profile-v1'
        need(runtime_provenance in {'created-profile-v1','created-temp-v1','created-updater-v1','created-logs-v1'},
            'Cleanup root has no supported installation-created provenance')
        need(all(_runtime_name(runtime_provenance,r['relative']) for r in files) and
            all(_runtime_directory(runtime_provenance,r['relative']) for r in dirs),
            'Unknown files/directories are outside finite application-state ownership')
    return True
