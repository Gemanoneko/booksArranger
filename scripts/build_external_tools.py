"""Exact retained Git-for-Windows wrapper profile for this build runtime.

This exception belongs only to the fixed external executable. Source, output,
Node, Python and other external-tool unique-file checks remain unchanged.
"""
import ctypes
from ctypes import wintypes as W
import os
from pathlib import Path
from native_io import BoundaryError,DirectoryBoundary,VerifiedFile,kernel,ordinary

# 2026-11-14 diagnostic candidate: independently verified signed installed
# Git 2.56.1.windows.1 wrapper/core. All four DLL pins and exact alias/link
# profiles remain unchanged. Evidence: ../refusal-fixture-20261114/git-profile-candidate.json.
GIT_WRAPPER_SHA256='177bc8a9af84fa3a400c694c975fda731d048279c074e1a93947ce8b067ebb48'
GIT=Path('C:/Program Files/Git/cmd/git.exe')
GIT_ALIASES=(GIT,GIT.with_name('git-lfs.exe'))
CORE=Path('C:/Program Files/Git/ucrt64/bin/git.exe')
CORE_SHA256='9bf8ee81d79f38a11eaf7799499a634c46a718e009a4a9b2b20b115804643302'
CORE_ALIASES=tuple(CORE.with_name(name) for name in ('git.exe','git-upload-pack.exe','git-upload-archive.exe','git-receive-pack.exe'))
CORE_DLLS={
 'libiconv-2.dll':'94ec68fb8d342b6c91b6b48a8d95092819cdcd006a7166e0b68062f946afd08a',
 'libintl-8.dll':'0e5a178731e6be6d115442a6ade3df7f03265cd1fc4338f8b6f86a8001cbf582',
 'libpcre2-8-0.dll':'1f609cde2ce432efb7d2b0c7b84a14a6dbfc9622d1ac1a3cbadf51c5b0b4dada',
 'zlib1.dll':'8ae7aeb0467763a1e271cd831ca8e2f7fd101602adb9923100ea26c6be2a559b',
}
# Git for Windows installs each backend DLL as one file with exactly two names:
# the backend folder and libexec/git-core. Both literal folders are pinned here.
CORE_DLL_DIRS=(CORE.parent,CORE.parent.parent/'libexec'/'git-core')

def _name(path):return os.path.normcase(os.path.abspath(path))

def _native_aliases(path):
    kernel.FindFirstFileNameW.argtypes=[W.LPCWSTR,W.DWORD,ctypes.POINTER(W.DWORD),W.LPWSTR];kernel.FindFirstFileNameW.restype=W.HANDLE
    kernel.FindNextFileNameW.argtypes=[W.HANDLE,ctypes.POINTER(W.DWORD),W.LPWSTR];kernel.FindNextFileNameW.restype=W.BOOL
    kernel.FindClose.argtypes=[W.HANDLE]
    length=W.DWORD(32768);buffer=ctypes.create_unicode_buffer(length.value)
    search=kernel.FindFirstFileNameW(str(path),0,ctypes.byref(length),buffer)
    if search==ctypes.c_void_p(-1).value:raise BoundaryError('Cannot enumerate fixed Git wrapper aliases')
    names=[]
    try:
        while True:
            name=buffer.value
            if not name.startswith('\\') or name.startswith('\\\\'):raise BoundaryError('Unexpected native Git alias name')
            names.append(_name(ordinary(path.drive+name)))
            if len(names)>16:raise BoundaryError('Unexpected fixed Git alias count')
            length.value=len(buffer)
            if not kernel.FindNextFileNameW(search,ctypes.byref(length),buffer):
                if ctypes.get_last_error()!=38:raise BoundaryError('Cannot complete fixed Git alias enumeration')
                break
    finally:kernel.FindClose(search)
    if len(set(names))!=len(names):raise BoundaryError('Ambiguous fixed Git alias enumeration')
    return set(names)

def _retain_profile(stack,primary,aliases,digest,label='Fixed Git wrapper'):
    """Internal native fixture seam; production supplies only literal constants.
    label names the profile in every refusal, so a failed re-pin says which file moved."""
    primary=ordinary(primary);aliases=tuple(ordinary(path) for path in aliases)
    expected={_name(path) for path in aliases}
    if len(aliases) not in (2,4) or len(expected)!=len(aliases) or _name(primary) not in expected or any(path.parent!=primary.parent for path in aliases):
        raise BoundaryError(label+' profile is invalid')
    stack.enter_context(DirectoryBoundary(primary.anchor,primary.parent))
    held=stack.enter_context(VerifiedFile(primary));facts=held.facts()
    if facts['links']!=len(aliases) or held.sha256()!=digest:raise BoundaryError(label+' hash/link profile differs')
    if _native_aliases(primary)!=expected:raise BoundaryError(label+' alias membership differs')
    for path in aliases:
        alias=stack.enter_context(VerifiedFile(path))
        if alias.facts()!=facts:raise BoundaryError(label+' aliases do not identify the same immutable file')
    if _native_aliases(primary)!=expected or held.facts()!=facts:raise BoundaryError(label+' profile drifted while acquiring holds')
    return str(primary)

def _retain_dependency(stack,primary,aliases,digest):
    """Internal native fixture seam: one pinned DLL with exactly two same-named
    aliases in two distinct literal folders. Production supplies only constants."""
    primary=ordinary(primary);aliases=tuple(ordinary(path) for path in aliases)
    expected={_name(path) for path in aliases}
    if len(aliases)!=2 or len(expected)!=2 or _name(primary) not in expected or any(path.name!=primary.name for path in aliases) or len({_name(path.parent) for path in aliases})!=2:
        raise BoundaryError('Fixed Git local runtime dependency profile is invalid')
    for path in aliases:stack.enter_context(DirectoryBoundary(path.anchor,path.parent))
    held=stack.enter_context(VerifiedFile(primary));facts=held.facts()
    if facts['links']!=len(aliases) or held.sha256()!=digest:raise BoundaryError('Fixed Git local runtime dependency hash/link profile differs')
    if _native_aliases(primary)!=expected:raise BoundaryError('Fixed Git local runtime dependency alias membership differs')
    for path in aliases:
        alias=stack.enter_context(VerifiedFile(path))
        if alias.facts()!=facts:raise BoundaryError('Fixed Git local runtime dependency aliases do not identify the same immutable file')
    if _native_aliases(primary)!=expected or held.facts()!=facts:raise BoundaryError('Fixed Git local runtime dependency drifted while acquiring holds')
    return str(primary)

def retain_git(stack):
    capability=_retain_profile(stack,GIT,GIT_ALIASES,GIT_WRAPPER_SHA256)
    _retain_profile(stack,CORE,CORE_ALIASES,CORE_SHA256,'Fixed Git core')
    for name,digest in CORE_DLLS.items():
        _retain_dependency(stack,CORE.parent/name,tuple(folder/name for folder in CORE_DLL_DIRS),digest)
    return capability
