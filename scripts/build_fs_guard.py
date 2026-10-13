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
    def _create_directory(self, value):
        # NtCreateFile(FILE_CREATE) opens the new directory atomically relative
        # to the retained parent HANDLE; no mkdir-then-adopt pathname window.
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
        result=nt.NtCreateFile(ctypes.byref(handle),0x100081,ctypes.byref(attributes),ctypes.byref(status),None,0x10,1,2,0x200021,None,0)
        if result<0:raise BoundaryError('Fresh native directory creation refused: '+hex(result&0xffffffff))
        self.stack.callback(kernel.CloseHandle,handle)
        info=FileInfo()
        if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or info.attributes&0x400 or not info.attributes&0x10:raise BoundaryError('Fresh directory native identity refused')
        class Lease:
            handles=[handle]
            def revalidate(inner):
                now=FileInfo()
                if not kernel.GetFileInformationByHandle(handle,ctypes.byref(now)) or now.attributes&0x400 or (now.volume,now.index_high,now.index_low)!=(info.volume,info.index_high,info.index_low):raise BoundaryError('Fresh directory native identity changed')
        self.directories[str(value).casefold()]=Lease()
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
    def fresh(self, parent):
        parent = self.directory(parent, create=True)
        value = parent / str(uuid.uuid4())
        # mkdir has no exist_ok: UUID collision refuses, never adopts.
        self._create_directory(value)
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
                if item.facts()['links'] != 1 or {'sha256': item.sha256(), 'size': item.facts()['size']} != expected:
                    raise BoundaryError('Cleanup manifest identity/content mismatch; nothing removed')
                held.append(item)
            for item in held: item.dispose()
        return len(held)
