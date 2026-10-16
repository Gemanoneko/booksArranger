"""Exact-handle build staging. Existing trees are never adopted or recursively deleted.
Windows only. All mutation is under fresh UUID directories with retained ancestry.
"""
import contextlib
import hashlib
import os
from pathlib import Path
import uuid
import zipfile
import sys

# Caller must load this module only under its bootstrap/source lease.
from native_io import BoundaryError, DirectoryBoundary, VerifiedFile, kernel, FileInfo
import ctypes
from ctypes import wintypes

class BuildTree:
    def __init__(self, root):
        self.root = Path(root).absolute()
        self.stack = contextlib.ExitStack()
        self.directories = {}
        self.files = {}
        self.created = {}
    def __enter__(self):
        self.directory(self.root)
        return self
    def __exit__(self, *args):
        return self.stack.__exit__(*args)
    def child(self, path):
        from native_io import ordinary
        value = ordinary(path)
        if not value.is_relative_to(self.root):
            raise BoundaryError('Build path escapes owned checkout')
        return value
    def _create_directory(self, value, share=1):
        # NtCreateFile(FILE_CREATE) opens the new directory atomically relative
        # to the retained parent HANDLE; no mkdir-then-adopt pathname window.
        # share is READ (1) or READ|WRITE (3); DELETE sharing is never granted,
        # so the held directory itself can never be renamed, deleted or replaced.
        if share not in (1,3):raise BoundaryError('Fresh directory sharing must deny DELETE')
        parent=self.directory(value.parent)
        parent_lease=self.directories[str(parent).casefold()]
        parent_handle=parent_lease.handles[-1]
        class Unicode(ctypes.Structure):
            _fields_=[('length',wintypes.USHORT),('maximum',wintypes.USHORT),('buffer',wintypes.LPWSTR)]
        class Attributes(ctypes.Structure):
            _fields_=[('length',wintypes.ULONG),('root',wintypes.HANDLE),('name',ctypes.POINTER(Unicode)),('flags',wintypes.ULONG),('security',ctypes.c_void_p),('qos',ctypes.c_void_p)]
        class Status(ctypes.Structure):
            _fields_=[('status',ctypes.c_void_p),('information',ctypes.c_size_t)]
        name_buffer=ctypes.create_unicode_buffer(value.name)
        name=Unicode(len(value.name.encode('utf-16-le')),len(name_buffer)*2,ctypes.cast(name_buffer,wintypes.LPWSTR))
        attributes=Attributes(ctypes.sizeof(Attributes),parent_handle,ctypes.pointer(name),0x40,None,None)
        nt=ctypes.WinDLL('ntdll');nt.NtCreateFile.argtypes=[ctypes.POINTER(wintypes.HANDLE),wintypes.DWORD,ctypes.POINTER(Attributes),ctypes.POINTER(Status),ctypes.c_void_p,wintypes.ULONG,wintypes.ULONG,wintypes.ULONG,wintypes.ULONG,ctypes.c_void_p,wintypes.ULONG];nt.NtCreateFile.restype=wintypes.LONG
        handle=wintypes.HANDLE();status=Status()
        result=nt.NtCreateFile(ctypes.byref(handle),0x100081,ctypes.byref(attributes),ctypes.byref(status),None,0x10,share,2,0x200021,None,0)
        if result<0:raise BoundaryError('Fresh native directory creation refused: '+hex(result&0xffffffff))
        self.stack.callback(kernel.CloseHandle,handle)
        info=FileInfo()
        if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or info.attributes&0x400 or not info.attributes&0x10:raise BoundaryError('Fresh directory native identity refused')
        class Lease:
            handles=[handle]
            def revalidate(inner):
                now=FileInfo()
                if not kernel.GetFileInformationByHandle(handle,ctypes.byref(now)) or now.attributes&0x400 or (now.volume,now.index_high,now.index_low)!=(info.volume,info.index_high,info.index_low):raise BoundaryError('Fresh directory native identity changed')
        lease=Lease();lease.parent=value
        self.directories[str(value).casefold()]=lease
        return value
    def directory(self, path, create=False):
        value = self.child(path)
        key = str(value).casefold()
        if key not in self.directories:
            if create and not value.exists():
                self.directory(value.parent, create=True)
                self._create_directory(value)
            else:
                self.directories[key] = self.stack.enter_context(DirectoryBoundary(self.root, value, create=False))
        self.directories[key].revalidate()
        return value
    def protect(self, path, expected=None):
        value = self.child(path)
        self.directory(value.parent)
        key = str(value).casefold()
        if key not in self.files:
            held = self.stack.enter_context(VerifiedFile(value))
            facts = held.facts()
            if facts['links'] != 1:
                raise BoundaryError('Build input/output hardlink refused')
            self.files[key] = held
        held = self.files[key]
        result = {'sha256': held.sha256(), 'size': held.facts()['size']}
        if expected is not None and result != expected:
            raise BoundaryError('Build file differs from accepted manifest')
        return result
    def fresh(self, parent, allow_child_rename=False):
        parent = self.directory(parent, create=True)
        value = parent / str(uuid.uuid4())
        # mkdir has no exist_ok: UUID collision refuses, never adopts.
        # A Windows rename opens the TARGET parent directory for write, so a
        # READ-only-shared hold makes every rename into it fail with EBUSY.
        # allow_child_rename adds WRITE sharing only (never DELETE) for an
        # output tree whose producer renames its own children inside it.
        self._create_directory(value, 3 if allow_child_rename else 1)
        self.created[str(value).casefold()] = value
        return value
    def write(self, path, chunks):
        value = self.child(path)
        if not any(value.is_relative_to(p) for p in self.created.values()):
            raise BoundaryError('Writes require a fresh owned UUID tree')
        self.directory(value.parent, create=True)
        handle = kernel.CreateFileW(str(value), 0x40000000 | 0x81, 1, None, 1, 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise BoundaryError('Owned output creation refused: ' + str(ctypes.WinError(ctypes.get_last_error())))
        try:
            info = FileInfo()
            if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)) or info.attributes & (0x400 | 0x10) or info.links != 1:
                raise BoundaryError('Owned output is not one ordinary file')
            identity = (info.volume, info.index_high, info.index_low)
            digest = hashlib.sha256(); size = 0
            kernel.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
            kernel.WriteFile.restype = wintypes.BOOL
            for block in chunks:
                block = bytes(block)
                if not block: continue
                buffer = ctypes.create_string_buffer(block); written = wintypes.DWORD()
                if not kernel.WriteFile(handle, buffer, len(block), ctypes.byref(written), None) or written.value != len(block):
                    raise BoundaryError('Owned output write incomplete')
                digest.update(block); size += len(block)
            kernel.FlushFileBuffers.argtypes = [wintypes.HANDLE]; kernel.FlushFileBuffers.restype = wintypes.BOOL
            if not kernel.FlushFileBuffers(handle): raise BoundaryError('Owned output durability refused')
        finally:
            kernel.CloseHandle(handle)
        expected = {'sha256': digest.hexdigest(), 'size': size}
        actual = self.protect(value, expected)
        held = self.files[str(value).casefold()]
        if tuple(held.facts()['identity']) != identity:
            raise BoundaryError('Owned output identity substituted')
        return actual
    def copy(self, source, target):
        self.protect(source)
        return self.write(target, self.files[str(self.child(source)).casefold()].chunks())
    def extract_zip(self, archive, target, max_bytes=2_000_000_000):
        # Archive read is pinned by its retained native handle; ZipFile's path
        # reopening cannot change its identity while this read lease is alive.
        self.protect(archive)
        target = self.directory(target, create=True)
        if not any(target.is_relative_to(p) for p in self.created.values()):
            raise BoundaryError('Extraction requires a fresh owned UUID tree')
        with zipfile.ZipFile(archive) as z:
            entries = z.infolist()
            names = set(); total = 0
            for entry in entries:
                name = entry.filename
                parts = name.replace('\\', '/').split('/')
                if name.startswith(('/', '\\')) or '\\' in name or any(p in ('.', '..') for p in parts) or any(':' in p for p in parts):
                    raise BoundaryError('Archive contains traversal/device member')
                canonical = name.rstrip('/').casefold()
                if not canonical or canonical in names: raise BoundaryError('Archive contains duplicate/empty member')
                names.add(canonical)
                mode = entry.external_attr >> 16
                if mode & 0o170000 not in (0, 0o040000, 0o100000):
                    raise BoundaryError('Archive contains link/special member')
                total += entry.file_size
                if total > max_bytes: raise BoundaryError('Archive exceeds staging byte budget')
                self.child(target / name.rstrip('/'))
            result = {}
            for entry in entries:
                destination = target / entry.filename.rstrip('/')
                if entry.is_dir(): self.directory(destination, create=True); continue
                with z.open(entry) as stream:
                    facts = self.write(destination, iter(lambda: stream.read(1024 * 1024), b''))
                if facts['size'] != entry.file_size: raise BoundaryError('Archive extraction size mismatch')
                result[entry.filename] = facts
            return result
    def tree_manifest(self, folder):
        folder = self.directory(folder)
        result = {}
        def visit(parent):
            self.directory(parent)
            for item in os.scandir(parent):
                path = Path(item.path)
                if item.is_dir(follow_symlinks=False): visit(path)
                else: result[path.relative_to(folder).as_posix()] = self.protect(path)
        visit(folder)
        return result


def remove_manifest_files(root, folder, manifest):
    """Retire only accepted ordinary file identities, never recursive folders.

    Unknown files, substituted bytes, hardlinks and all directories remain.
    Directory disposal is intentionally excluded (NTFS arriving-stream race).
    """
    with BuildTree(root) as tree:
        folder = tree.directory(folder)
        with contextlib.ExitStack() as deletes:
            held = []
            for relative, expected in manifest.items():
                if not isinstance(relative,str) or Path(relative).is_absolute(): raise BoundaryError('Cleanup requires relative manifest paths')
                path = tree.child(folder / relative)
                if not path.is_relative_to(folder): raise BoundaryError('Cleanup path escapes exact owned folder')
                tree.directory(path.parent)
                item = deletes.enter_context(VerifiedFile(path, delete=True))
                native=item.facts()
                actual={k:native[k] for k in ('identity','dev','ino','identity_method','attributes','links','modified','size')}|{'sha256':item.sha256()}
                no_named_streams(path)
                if native['links']!=1:raise BoundaryError('Cleanup hardlink refused')
                _receipt_equal(actual,expected)
                held.append(item)
            for item in held: item.dispose()
        return len(held)


def no_named_streams(path):
    """Refuse ambiguous metadata; rename never discards unexamined ADS."""
    class Stream(ctypes.Structure):
        _fields_=[('size',ctypes.c_longlong),('name',wintypes.WCHAR*296)]
    kernel.FindFirstStreamW.argtypes=[wintypes.LPCWSTR,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];kernel.FindFirstStreamW.restype=wintypes.HANDLE
    kernel.FindNextStreamW.argtypes=[wintypes.HANDLE,ctypes.c_void_p];kernel.FindNextStreamW.restype=wintypes.BOOL
    kernel.FindClose.argtypes=[wintypes.HANDLE]
    stream=Stream();handle=kernel.FindFirstStreamW(str(path),0,ctypes.byref(stream),0)
    if handle==ctypes.c_void_p(-1).value:raise BoundaryError('Metadata stream enumeration unavailable')
    try:
        while True:
            if stream.name!='::$DATA':raise BoundaryError('Metadata named stream refused; original preserved')
            if not kernel.FindNextStreamW(handle,ctypes.byref(stream)):
                if ctypes.get_last_error()!=38:raise BoundaryError('Metadata stream enumeration incomplete')
                return
    finally:kernel.FindClose(handle)


def _native_receipt(tree,path):
    value=tree.child(path);facts=tree.protect(value);no_named_streams(value)
    held=tree.files[str(value).casefold()]
    refreshed=FileInfo()
    if not kernel.GetFileInformationByHandle(held.handle,ctypes.byref(refreshed)) or refreshed.attributes&(0x400|0x10) or refreshed.links!=1:raise BoundaryError('Native receipt reparse/type/link drift')
    held.info=refreshed
    original=held.facts()
    return {k:original[k] for k in ('identity','dev','ino','identity_method','attributes','links','modified','size')}|{'sha256':facts['sha256']}


def _receipt_equal(actual,expected):
    wanted=('identity','dev','ino','identity_method','attributes','links','modified','size','sha256')
    if not isinstance(expected,dict) or any(k not in expected or actual[k]!=expected[k] for k in wanted):
        raise BoundaryError('Original native identity/content receipt differs; substituted file preserved')


def capture_metadata(tree,path):
    """Hold and remember the exact original stable file before a long build."""
    value=tree.child(path)
    receipt=_native_receipt(tree,value)
    if receipt['size']>16*1024*1024:raise BoundaryError('Build metadata exceeds bounded size')
    return {'path':str(value),'receipt':receipt}


def release_file(tree,path):
    key=str(tree.child(path)).casefold()
    held=tree.files.pop(key,None)
    if held is not None:held.__exit__(None,None,None)


def archive_metadata(tree,plan,validator,before_open=None):
    """CAS archive exact old metadata through native rename, never a pathname.

    The read lease is deliberately released because DELETE requires sharing.
    That gap confers no authority: publish's same original identity+bytes must
    match, and its retained DELETE handle prevents a name swap during callback.
    """
    from native_io import publish_no_replace
    source=tree.child(plan['path']);parent=tree.directory(source.parent)
    destination=parent/(source.name+'.previous-'+str(uuid.uuid4()))
    expected=plan['receipt']
    release_file(tree,source)
    if before_open:before_open(source)
    boundary=tree.directories[str(parent).casefold()]
    def checked(proof):
        if proof['identity']!=expected['identity'] or proof['sha256']!=expected['sha256'] or proof['size']!=expected['size']:raise BoundaryError('Metadata CAS native identity/content substituted; original preserved')
        # The publisher's retained DELETE handle excludes write/rename. A read
        # handle with SHARE_DELETE can inspect that exact file without weakening
        # the publisher handle's restrictive sharing on other openers.
        handle=kernel.CreateFileW(str(source),0x81,7,None,3,0x00200000,None)
        if handle==ctypes.c_void_p(-1).value:raise BoundaryError('Cannot inspect metadata held by rename')
        try:
            info=FileInfo()
            if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or info.attributes&(0x400|0x10) or info.links!=1 or [info.volume,info.index_high,info.index_low]!=expected['identity'] or info.attributes!=expected['attributes'] or ((info.write.dwHighDateTime<<32)|info.write.dwLowDateTime)-116444736000000000!=expected['modified']//100:raise BoundaryError('Metadata rename attributes/link/identity drift')
            no_named_streams(source)
            validator()
        finally:kernel.CloseHandle(handle)
    publish_no_replace(source,destination,boundary,expected_sha256=expected['sha256'],expected_size=expected['size'],before_rename=checked)
    try:
        _receipt_equal(_native_receipt(tree,destination),expected)
    except BoundaryError as drift:
        # An arriving stream/link is never discarded. Restore this same original
        # identity to its original empty name, including every stream, then
        # refuse the rotation. A colliding/replaced name is never overwritten.
        release_file(tree,destination)
        def original_only(proof):
            if proof['identity']!=expected['identity']:raise BoundaryError('Archival recovery original identity differs')
        try:publish_no_replace(destination,source,boundary,expected['sha256'],expected['size'],original_only)
        except Exception as error:raise BoundaryError('Archival drift; exact previous evidence preserved at '+str(destination)) from error
        raise drift
    return str(destination)


def publish_metadata(tree,temporary,destination):
    from native_io import publish_no_replace
    temporary=tree.child(temporary);destination=tree.child(destination)
    receipt=_native_receipt(tree,temporary)
    parent=tree.directory(destination.parent)
    release_file(tree,temporary)
    def checked(proof):
        if proof['identity']!=receipt['identity']:raise BoundaryError('New metadata native identity substituted')
        no_named_streams(temporary)
    publish_no_replace(temporary,destination,tree.directories[str(parent).casefold()],receipt['sha256'],receipt['size'],checked)
    _receipt_equal(_native_receipt(tree,destination),receipt)
    return receipt


def _relative_file(tree,base,name):
    if not isinstance(name,str) or not name or '\\' in name or Path(name).is_absolute() or any(p in ('','.','..') for p in name.split('/')):raise BoundaryError('Producer record path refused')
    value=tree.child(base/name)
    if not value.is_relative_to(base):raise BoundaryError('Producer record escapes exact build')
    return value


def _json_metadata(path):
    import json
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise BoundaryError('Duplicate metadata field refused')
            result[key]=value
        return result
    try:return json.loads(Path(path).read_text('utf8'),object_pairs_hook=pairs)
    except (ValueError,UnicodeError) as error:raise BoundaryError('Corrupt metadata preserved') from error


class PriorBuild:
    """Verified old producer receipt retained while a new build is prepared."""
    def __init__(self,tree):
        self.tree=tree;root=tree.root
        manifest=root/'dist'/'release-artifacts.json';pointer=root/'build-cache'/'runtime-pointer.json'
        present=[os.path.lexists(manifest),os.path.lexists(pointer)]
        self.plans={}
        if not any(present):return
        if not all(present):raise BoundaryError('Incomplete prior candidate preserved; manual exact-evidence recovery required')
        self.plans={'manifest':capture_metadata(tree,manifest),'pointer':capture_metadata(tree,pointer)}
        self.manifest=_json_metadata(manifest);self.pointer=_json_metadata(pointer)
        m,p=self.manifest,self.pointer
        try:
            identity=str(uuid.UUID(m['build_id']))
            if identity!=m['build_id'] or p['build_id']!=identity or m['schema']!='books-desktop-artifacts-v1' or p['schema']!='books-runtime-pointer-v1' or m['unpacked']!='builds/'+identity+'/win-unpacked' or m['payload']['verified'] is not True or m['payload']['installer_equivalent'] is not True:raise ValueError('schema')
            self.runtime=tree.child(p['root'])
            relative=self.runtime.relative_to(root/'build-cache'/'builds')
            if len(relative.parts)!=2 or relative.parts[1]!='runtime' or str(uuid.UUID(relative.parts[0]))!=relative.parts[0]:raise ValueError('runtime ownership')
            self.unpacked=root/'dist'/'builds'/identity/'win-unpacked'
            producer=self.runtime.parent/'producer-receipt.json'
            self.producer_plan=capture_metadata(tree,producer);self.producer=_json_metadata(producer)
            r=self.producer
            if r['schema']!='books-build-producer-v1' or r['build_id']!=identity or r['owned_root']!=str(self.runtime.parent) or r['source_head']!=m['source_head']:raise ValueError('producer')
            _receipt_equal(self.plans['manifest']['receipt'],r['manifest_receipt'])
            _receipt_equal(self.plans['pointer']['receipt'],r['pointer_receipt'])
            self.verify()
        except (KeyError,ValueError,TypeError) as error:raise BoundaryError('Unknown/corrupt prior producer metadata preserved') from error
    def verify(self):
        if not self.plans:return
        tree=self.tree;m,p,r=self.manifest,self.pointer,self.producer
        _receipt_equal(_native_receipt(tree,self.producer_plan['path']),self.producer_plan['receipt'])
        import re,json
        if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)',m.get('version','')) or not re.fullmatch('[a-f0-9]{40}',m.get('source_head','')) or not re.fullmatch('[a-f0-9]{64}',m.get('product_digest','')) or m['payload'].get('shell_version')!=m['version'] or m['payload'].get('backend_version')!=m['version']:raise BoundaryError('Prior version/source proof differs')
        if hashlib.sha256(json.dumps(p['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()!=p['manifest_sha256']:raise BoundaryError('Prior runtime map digest differs')
        for base,hashes,natives in [(self.runtime,p['files'],r['runtime_files']),(self.unpacked,m['payload']['files'],r['payload_files'])]:
            if set(tree.tree_manifest(base))!=set(hashes) or set(hashes)!=set(natives):raise BoundaryError('Prior build file membership differs')
            for name,expected in hashes.items():
                path=_relative_file(tree,base,name)
                tree.protect(path,expected);_receipt_equal(_native_receipt(tree,path),natives[name])
        artifacts=m['artifacts']
        if not isinstance(artifacts,list) or len(artifacts)!=3:raise BoundaryError('Prior artifact inventory differs')
        names=set()
        for artifact in artifacts:
            name=artifact['path'];names.add(name)
            if not name.startswith('builds/'+m['build_id']+'/'):raise BoundaryError('Prior artifact path outside exact build')
            path=_relative_file(tree,tree.root/'dist',name)
            tree.protect(path,{'sha256':artifact['sha256'],'size':artifact['size']})
            _receipt_equal(_native_receipt(tree,path),r['artifacts'][name])
        stem='builds/'+m['build_id']+'/Books-Arranger-Setup-'+m['version']+'.exe'
        if names!={stem,stem+'.blockmap','builds/'+m['build_id']+'/latest.yml'} or names!=set(r['artifacts']):raise BoundaryError('Prior artifact producer membership differs')
    def archive(self):
        result={}
        try:
            for name,plan in self.plans.items():result[name]=archive_metadata(self.tree,plan,self.verify)
        except Exception:
            for name,previous in result.items():
                try:publish_metadata(self.tree,previous,self.plans[name]['path'])
                except Exception as error:raise BoundaryError('Prior metadata archive stopped; exact previous evidence retained at '+previous) from error
            raise
        return result


def producer_receipt(tree,owned_root,manifest,pointer,manifest_temp,pointer_temp):
    root=tree.root;runtime=Path(pointer['root']);unpacked=root/'dist'/manifest['unpacked']
    return {'schema':'books-build-producer-v1','build_id':manifest['build_id'],'owned_root':str(owned_root),'source_head':manifest['source_head'],
        'manifest_receipt':_native_receipt(tree,manifest_temp),'pointer_receipt':_native_receipt(tree,pointer_temp),
        'runtime_files':{name:_native_receipt(tree,_relative_file(tree,runtime,name)) for name in pointer['files']},
        'payload_files':{name:_native_receipt(tree,_relative_file(tree,unpacked,name)) for name in manifest['payload']['files']},
        'artifacts':{item['path']:_native_receipt(tree,_relative_file(tree,root/'dist',item['path'])) for item in manifest['artifacts']}}


def disposable_stage_receipts(tree,owned_root):
    """Only newly owned redundant copies, never runtime/artifacts/metadata."""
    owned=tree.child(owned_root)
    result={}
    for name in ['downloads','extract','backend','nsis-archive','nsis-payload']:
        folder=owned/name
        if not os.path.lexists(folder):continue
        for relative in tree.tree_manifest(folder):
            path=_relative_file(tree,folder,relative)
            result[path.relative_to(owned).as_posix()]=_native_receipt(tree,path)
    return result


def retire_disposable_stage(tree,owned_root,receipts):
    owned=tree.child(owned_root)
    for name in receipts:
        if name.split('/')[0] not in {'downloads','extract','backend','nsis-archive','nsis-payload'}:raise BoundaryError('Disposable staging domain refused')
        release_file(tree,_relative_file(tree,owned,name))
    return remove_manifest_files(tree.root,owned,receipts)
