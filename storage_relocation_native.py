"""Native leases for an explicitly selected offline storage relocation.

Legacy processes have no context. Configuring a descriptor permits only the
exact managed junction access; historical identity comparisons additionally
require a live target catalog owner and an active durable generation.
"""
import contextlib
import ctypes
from ctypes import wintypes
import json
import ntpath
import os
from pathlib import Path
import sqlite3
import struct
import threading
import tempfile

from storage_relocation import parse_manifest, RelocationRefused, _plain, _key

MANIFEST_ENV = 'BOOKS_STORAGE_RELOCATION_MANIFEST'
DIGEST_ENV = 'BOOKS_STORAGE_RELOCATION_SHA256'
_context = None
_temp_lease = None
_lock = threading.RLock()


class VerificationRequired(RelocationRefused):
    """A sealed catalog may be inspected offline, never started normally."""


def verification_message(database):
    return ('The database at “'+str(database)+'” is not enabled for use. Complete offline verification '
            'and explicitly enable the database with the relocation tool before opening Books Arranger.')


def current():
    return _context


def _need(condition, message):
    if not condition:
        raise RelocationRefused(message)


def _junction_target(handle):
    from native_io import kernel
    kernel.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    kernel.DeviceIoControl.restype = wintypes.BOOL
    buffer = ctypes.create_string_buffer(16 * 1024)
    returned = wintypes.DWORD()
    if not kernel.DeviceIoControl(handle, 0x000900A8, None, 0, buffer, len(buffer),
                                  ctypes.byref(returned), None):
        raise RelocationRefused('Cannot inspect the selected storage junction')
    raw = buffer.raw[:returned.value]
    _need(len(raw) >= 16, 'Truncated storage reparse data')
    tag, length, reserved, offset, size, print_offset, print_size = struct.unpack_from('<I6H', raw)
    _need(tag == 0xA0000003 and reserved == 0 and length >= 8 and
          length + 8 == len(raw), 'Only an exact bounded mount-point junction is supported')
    paths = raw[16:]
    for start, count in ((offset, size), (print_offset, print_size)):
        _need(start % 2 == count % 2 == 0 and start + count <= len(paths),
              'Storage reparse string bounds differ')
    target = paths[offset:offset + size].decode('utf-16-le', errors='strict')
    _need(target.startswith('\\??\\') and '\x00' not in target,
          'Storage junction does not name an ordinary local target')
    target = target[4:]
    _need(len(ntpath.splitdrive(target)[0]) == 2, 'Storage junction target is not a local drive')
    return ntpath.normcase(ntpath.normpath(target))


class NativeContext:
    def __init__(self, manifest_path, expected_sha256):
        from native_io import DirectoryBoundary, VerifiedFile, kernel
        from source_cleanup import single_stream
        self.stack = contextlib.ExitStack()
        self.database = None
        self.owner = None
        self.owner_file = None
        self.catalog_handle = None
        self.catalog_binding = None
        self.source_fence = None
        self.activation_row = None
        self.verification_record = None
        self.pending_verification = None
        self.finalization_record = None
        self.pending_finalization = None
        self.manifest_path = Path(manifest_path).absolute()
        self._closed = False
        try:
            self.stack.enter_context(DirectoryBoundary(self.manifest_path.anchor, self.manifest_path.parent))
            descriptor = self.stack.enter_context(VerifiedFile(self.manifest_path))
            _need(descriptor.facts()['links'] == 1 and descriptor.facts()['size'] <= 64 * 1024 * 1024,
                  'Selected storage descriptor is not an ordinary bounded unique file')
            single_stream(self.manifest_path)
            self.manifest = parse_manifest(b''.join(descriptor.chunks()), expected_sha256)
            target = Path(self.manifest.target_root)
            kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
            kernel.GetDriveTypeW.restype = wintypes.UINT
            _need(kernel.GetDriveTypeW(target.anchor) == 3,
                  'Relocated application state requires its configured local fixed drive')
            self.target_boundary = self.stack.enter_context(DirectoryBoundary(target.anchor, target))
            _need(tuple(self.target_boundary.identities[-1][1:]) == self.manifest.directories[''].target,
                  'Configured storage target native root identity changed')
        except BaseException:
            self.stack.close()
            raise

    def is_alias(self, path, operation_path):
        return (_key(str(path)) == _key(self.manifest.source_root) and
                self.manifest.permitted(str(operation_path)))

    def alias_handle(self, path, operation_path, handle):
        """Return an independently owned ordinary target handle, not fake facts."""
        from native_io import kernel, FileInfo
        _need(self.is_alias(path, operation_path), 'Unselected storage alias refused')
        self.target_boundary.revalidate()
        _need(_junction_target(handle) == _key(self.manifest.target_root),
              'Storage junction points at a different physical target')
        duplicate = kernel.CreateFileW(self.manifest.target_root, 0x81, 1, None, 3,
                                       0x02000000 | 0x00200000, None)
        if duplicate == ctypes.c_void_p(-1).value:
            raise RelocationRefused('Cannot retain the actual storage target directory')
        try:
            info = FileInfo()
            _need(kernel.GetFileInformationByHandle(duplicate, ctypes.byref(info)) and
                  not info.attributes & 0x400 and info.attributes & 0x10 and
                  (info.volume, info.index_high, info.index_low) == self.manifest.directories[''].target,
                  'Storage target native directory identity differs')
            return duplicate, info
        except BaseException:
            kernel.CloseHandle(duplicate)
            raise

    def revalidate_alias(self, handle):
        self.target_boundary.revalidate()
        _need(_junction_target(handle) == _key(self.manifest.target_root),
              'Retained storage junction target changed')

    def _activation(self,initializing=False):
        _need(not self._closed and self.owner is not None and self.owner.get('held') is True,
              'Historical storage comparison requires a live catalog ownership lease')
        self.target_boundary.revalidate()
        from native_io import kernel,FileInfo
        _need(self.owner_file is not None and self.owner_file.handle is not None,
              'Relocation catalog native owner has closed')
        info=FileInfo()
        _need(kernel.GetFileInformationByHandle(self.owner_file.handle,ctypes.byref(info)) and
              [info.volume,info.index_high,info.index_low]==self.owner['lock_identity'],
              'Relocation catalog native owner identity changed')
        catalog_info=FileInfo()
        _need(self.catalog_handle is not None and
              kernel.GetFileInformationByHandle(self.catalog_handle,ctypes.byref(catalog_info)) and
              [catalog_info.volume,catalog_info.index_high,catalog_info.index_low]==
              list(self.catalog_binding.target['identity']) and catalog_info.links==1 and
              not catalog_info.attributes & (0x400|0x10),
              'Selected catalog native file identity differs from the sealed target')
        if self.source_fence is not None:self.source_fence.revalidate()
        uri = Path(self.database).as_uri() + '?mode=ro'
        with contextlib.closing(sqlite3.connect(uri, uri=True, timeout=2)) as db:
            db.execute('PRAGMA query_only=ON')
            db.execute('PRAGMA temp_store=MEMORY')
            rows = db.execute('SELECT catalog_id,generation,manifest_sha256,source_snapshot_sha256,'
                'phase,revision,source_fence_sha256,target_root_identity FROM storage_relocation_activation').fetchall()
            verification=db.execute('SELECT catalog_id,generation,manifest_sha256,receipt_path,'
                'receipt_sha256,verified_state_sha256 FROM storage_relocation_verification').fetchall() if rows and rows[0][4]=='active' else []
            finalization=db.execute('SELECT catalog_id,generation,base_fence_sha256,verification_sha256,'
                'receipt_path,receipt_sha256,state,revision FROM storage_relocation_source_finalization').fetchall() \
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='storage_relocation_source_finalization'").fetchone() else []
        _need(len(rows) == 1, 'Exactly one active catalog storage generation is required')
        row = rows[0]
        _need(row[:4] == (self.manifest.catalog_id, self.manifest.generation, self.manifest.digest,
                          self.manifest.source_snapshot_sha256) and row[4] in ('verifying','active') and
              type(row[5]) is int and row[5] > 0 and isinstance(row[6], str) and
              len(row[6]) == 64 and json.loads(row[7]) == list(self.manifest.directories[''].target),
              'Catalog storage generation does not match the explicitly selected descriptor')
        _need(self.activation_row is None or tuple(row)==self.activation_row,
              'Active relocation generation changed during catalog ownership')
        if row[4]=='active':
            _need(len(verification)==1 and verification[0][:3]==
                  (self.manifest.catalog_id,self.manifest.generation,self.manifest.digest),
                  'Normal storage admission requires its independent verification registration')
            registered=tuple(verification[0])
            if initializing:self.pending_verification=registered
            else:_need(self.verification_record==registered,
                       'Independent storage verification changed during catalog ownership')
        _need(len(finalization)<=1,'Multiple source finalization generations are not supported')
        finalized=tuple(finalization[0]) if finalization else None
        if finalized:
            _need(row[4]=='active' and finalized[:3]==(self.manifest.catalog_id,self.manifest.generation,row[6]) and
                  finalized[3]==verification[0][4] and finalized[6] in ('finalizing','files-finalized','retired') and
                  type(finalized[7]) is int and finalized[7]>0,
                  'Source finalization does not belong to this independently verified catalog')
        if initializing:self.pending_finalization=finalized
        else:_need(self.finalization_record==finalized,'Source finalization changed during catalog ownership')
        return row

    def require_normal_operation(self):
        row=self._activation()
        if row[4]!='active':raise VerificationRequired(verification_message(self.database))

    @contextlib.contextmanager
    def catalog_lease(self, database, owner, owner_file):
        _need(self.database is None and self.manifest.permitted(str(database)),
              'Relocation requires its exact managed catalog')
        binding=self.manifest.files.get(_key(self.manifest.relative(str(database))))
        _need(binding and 'catalog-storage' in binding.receipt_classes,
              'Selected catalog has no explicit source-to-target native storage binding')
        self.database, self.owner, self.owner_file = str(Path(database).absolute()), owner, owner_file
        try:
            from native_io import kernel
            # Permit SQLite read/write handles, but exclude rename/replacement
            # for the entire catalog owner lifetime. UUIDs copied inside another
            # database are insufficient authority for this native file.
            self.catalog_binding=binding
            self.catalog_handle=kernel.CreateFileW(self.database,0x81,3,None,3,0x00200000,None)
            if self.catalog_handle==ctypes.c_void_p(-1).value:
                self.catalog_handle=None
                raise RelocationRefused('Cannot retain the sealed target catalog native file')
            row=self._activation(initializing=True)
            from storage_relocation_operator import verify_source_fence,pinned_receipt
            with contextlib.ExitStack() as evidence:
                finalization=self.pending_finalization
                if finalization:
                    from storage_source_finalization import verify_source_finalization
                    fence=evidence.enter_context(verify_source_finalization(finalization[4],finalization[5],database=self.database))
                else:
                    fence=evidence.enter_context(verify_source_fence(str(self.manifest_path)+'.source-fence.json',row[6]))
                receipt=fence.receipt
                _need(receipt.get('generation')==self.manifest.generation and
                      receipt.get('catalog_id')==self.manifest.catalog_id and
                      receipt.get('source_snapshot_sha256')==self.manifest.source_snapshot_sha256,
                      'Source write fence belongs to a different storage generation')
                self.source_fence=fence
                self.finalization_record=finalization
                self.activation_row=tuple(row)
                if row[4]=='active':
                    registration=self.pending_verification
                    proof=evidence.enter_context(pinned_receipt(registration[3],registration[4]))
                    _need(proof.get('schema')=='books-storage-target-verification-v1' and
                          proof.get('catalog_id')==self.manifest.catalog_id and
                          proof.get('generation')==self.manifest.generation and
                          proof.get('manifest_path')==str(self.manifest_path) and
                          proof.get('manifest_sha256')==self.manifest.digest and
                          proof.get('source_snapshot_sha256')==self.manifest.source_snapshot_sha256 and
                          proof.get('source_fence_sha256')==row[6] and
                          proof.get('verified_state_sha256')==registration[5] and
                          proof.get('target_root_identity')==list(self.manifest.directories[''].target) and
                          proof.get('source_root_identity')==list(self.manifest.directories[''].source) and
                          proof.get('complete') is True and not proof.get('held_classes'),
                          'Independent storage verification does not authorize this catalog generation')
                    self.verification_record=registration
                self._activation()
                yield self
        finally:
            if self.catalog_handle is not None:
                kernel.CloseHandle(self.catalog_handle)
                self.catalog_handle=None
            self.catalog_binding=None
            self.owner = self.database = self.owner_file = self.source_fence = self.activation_row = None
            self.verification_record=self.pending_verification=None
            self.finalization_record=self.pending_finalization=None

    def facts_match(self, logical_path, actual, expected, receipt_class):
        self.require_normal_operation()
        return self.manifest.historical_facts_match(str(logical_path), actual, expected,
            receipt_class=receipt_class, catalog_id=self.manifest.catalog_id,
            generation=self.manifest.generation)

    def identity_match(self, logical_path, actual_facts, expected_identity, receipt_class):
        self.require_normal_operation()
        if not self.manifest.permitted(str(logical_path)):
            return False
        binding = self.manifest.files.get(_key(self.manifest.relative(str(logical_path))))
        return bool(binding and receipt_class in binding.receipt_classes and
                    all(actual_facts.get(key)==_plain(binding.target)[key] for key in
                        ('identity','dev','ino','identity_method','identity_api_error')) and
                    actual_facts.get('links')==1 and not actual_facts.get('attributes',0)&0x410 and
                    expected_identity == list(binding.source['identity']))

    def catalog_identity_match(self, actual, expected):
        """Copied catalog LOCATION only; never producer origin/closure evidence."""
        self.require_normal_operation()
        binding=self.manifest.files.get(_key(self.manifest.relative(self.database)))
        keys=('identity','dev','ino','identity_method','identity_api_error','links')
        return bool(binding and 'catalog-storage' in binding.receipt_classes and
                    set(actual)==set(expected)==set(keys) and
                    actual=={k:_plain(binding.target)[k] for k in keys} and
                    expected=={k:_plain(binding.source)[k] for k in keys})

    def ancestry_match(self, boundary, expected, operation_path, prefix=False):
        self.require_normal_operation()
        _need(self.manifest.permitted(str(operation_path)), 'Unmanaged ancestry binding refused')
        boundary.revalidate()
        actual = boundary.identities
        if prefix and isinstance(expected,(list,tuple)) and len(expected)<=len(actual):actual=actual[:len(expected)]
        if not isinstance(expected, (list, tuple)) or len(actual) != len(expected):
            return False
        for now, old in zip(actual, expected):
            if not isinstance(old, (list, tuple)) or len(old) != 4 or _key(now[0]) != _key(old[0]):
                return False
            if tuple(now[1:]) == tuple(old[1:]):
                continue
            path = str(now[0])
            if _key(path) == _key(self.manifest.source_root):
                relative = ''
            else:
                try:
                    relative = self.manifest.relative(path)
                except RelocationRefused:
                    return False
            binding = self.manifest.directories.get(_key(relative))
            if not binding or tuple(old[1:]) != binding.source or tuple(now[1:]) != binding.target:
                return False
        return True

    def close(self):
        _need(self.owner is None, 'Cannot close relocation context while its catalog is owned')
        if not self._closed:
            self.stack.close()
            self._closed = True


def configure(manifest_path, expected_sha256):
    global _context
    with _lock:
        _need(_context is None, 'A different storage relocation is already selected')
        result = NativeContext(manifest_path, expected_sha256)
        _context = result
        return result


def configure_from_environment(environment=None):
    environment = os.environ if environment is None else environment
    file, digest = environment.get(MANIFEST_ENV), environment.get(DIGEST_ENV)
    if not file and not digest:
        return None
    _need(file and digest, 'Both explicit storage descriptor and SHA-256 are required')
    if _context is not None:
        _need(str(_context.manifest_path) == str(Path(file).absolute()) and
              _context.manifest.digest == digest, 'Storage selection differs from retained context')
        return _context
    return configure(file, digest)


@contextlib.contextmanager
def selected_catalog_relocation(selection):
    """Temporarily retain an explicit descriptor without changing work temp."""
    global _context
    prior=current()
    if selection is None:
        _need(prior is None,'An unrelated catalog relocation is already selected')
        yield None
        return
    if prior is not None:
        _need(str(prior.manifest_path)==str(Path(selection['manifest']).absolute()) and
              prior.manifest.digest==selection['sha256'],'Storage selection differs from retained context')
        yield prior
        return
    selected=configure(selection['manifest'],selection['sha256'])
    try:
        yield selected
    finally:
        with _lock:
            _need(_context is selected,'Retained catalog relocation context changed')
            selected.close()
            _context=None


def close():
    global _context,_temp_lease
    with _lock:
        if _context is not None:
            _context.close()
            _context = None
        if _temp_lease is not None:
            _temp_lease['boundary'].__exit__(None,None,None)
            tempfile.tempdir=_temp_lease['previous']
            _temp_lease=None


def facts_match(path, actual, expected, *, receipt_class):
    if _context and _context.manifest.permitted(str(path)):_context.require_normal_operation()
    if actual == expected:
        return True
    return bool(_context and _context.facts_match(path, actual, expected, receipt_class))


def identity_match(path, actual_facts, expected_identity, *, receipt_class):
    if _context and _context.manifest.permitted(str(path)):_context.require_normal_operation()
    if actual_facts['identity'] == expected_identity:
        return True
    return bool(_context and _context.identity_match(path, actual_facts, expected_identity, receipt_class))


def ancestry_match(boundary, expected, *, operation_path, prefix=False):
    if _context and _context.manifest.permitted(str(operation_path)):_context.require_normal_operation()
    actual=boundary.identities
    if prefix and isinstance(expected,(list,tuple)) and len(expected)<=len(actual):actual=actual[:len(expected)]
    if [list(x) for x in actual] == [list(x) for x in expected]:
        boundary.revalidate()
        return True
    return bool(_context and _context.ancestry_match(boundary, expected, operation_path,prefix))


def retained_observation_match(actual,expected,boundary,*,operation_path):
    """Typed location bridge for an ALREADY validated retained-proof record.

    Origin/native hashes and boot closure stay in their immutable old record.
    This checks only a fresh independently hashed physical observation while
    all files, ancestry, source fence and active catalog owner remain retained.
    """
    if actual==expected:
        boundary.revalidate()
        return True
    if not _context:return False
    _context.require_normal_operation()
    keys={'schema','ownership_authority','catalog','stage','ancestry','marker_sha256','files'}
    if not isinstance(expected,dict) or set(actual)!=keys or set(expected)!=keys:return False
    if any(actual[k]!=expected[k] for k in ('schema','ownership_authority','stage','marker_sha256')):return False
    if actual['schema']!='books-unadopted-attempt-fence-v1' or actual['ownership_authority'] is not False:return False
    if not _context.catalog_identity_match(actual['catalog'],expected['catalog']):return False
    if not ancestry_match(boundary,expected['ancestry'],operation_path=operation_path):return False
    if not isinstance(expected['files'],list) or len(actual['files'])!=len(expected['files']):return False
    for now,old in zip(actual['files'],expected['files']):
        if not isinstance(old,dict) or set(now)!=set(old) or set(now)!={'name','path','facts','sha256'}:return False
        if any(now[k]!=old[k] for k in ('name','path','sha256')):return False
        if not facts_match(now['path'],now['facts'],old['facts'],receipt_class='retained-source'):return False
    return True


def require_normal_operation(database):
    """Admission before constructor recovery, schema writes or any workers."""
    if _context:
        path=str(Path(database).absolute())
        try:_context.manifest.logical_location(path)
        except RelocationRefused:
            assert_legacy_catalog(database)
            return
        _context.require_normal_operation()
    else:assert_legacy_catalog(database)


def logical_catalog_location(database):
    if not _context:return str(Path(database).absolute())
    return _context.manifest.logical_location(str(Path(database).absolute()))


def assert_legacy_catalog(database):
    """An existing relocated catalog never becomes legacy by omitting config.

    Open read-only, WAL-aware, before a writable SQLite connection can run its
    own journal recovery/schema initializers. New/ordinary legacy files retain
    their existing behavior; no new database or sidecar is created deliberately.
    """
    path=Path(database).absolute()
    if not path.is_file():return
    with contextlib.closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON');db.execute('PRAGMA temp_store=MEMORY')
        relocated=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='storage_relocation_activation'").fetchone()
    _need(not relocated,'This catalog has a storage relocation generation. Select its exact installation/relocation configuration before opening it. No legacy writable catalog was opened.')


def configure_work_temp(environment=None):
    """Pin Python's temporary directory; never let tempfile search a fallback."""
    global _temp_lease
    environment=os.environ if environment is None else environment
    selected=environment.get('BOOKS_WORK_TEMP')
    if selected is None:return None
    _need(isinstance(selected,str) and Path(selected).is_absolute(),
          'Configured temporary work requires an absolute directory')
    path=str(Path(selected).absolute())
    _need(environment.get('TEMP')==path and environment.get('TMP')==path,
          'Python temporary work environment differs from its explicit selection')
    if _temp_lease is not None:
        _need(_temp_lease['path']==path,'A different temporary work location is already retained')
        _temp_lease['boundary'].revalidate();return path
    from native_io import DirectoryBoundary,kernel
    kernel.GetDriveTypeW.argtypes=[wintypes.LPCWSTR];kernel.GetDriveTypeW.restype=wintypes.UINT
    _need(kernel.GetDriveTypeW(Path(path).anchor)==3,'Temporary application work requires its configured local fixed drive')
    boundary=DirectoryBoundary(Path(path).anchor,path)
    boundary.__enter__()
    _temp_lease={'path':path,'boundary':boundary,'previous':tempfile.tempdir}
    # Assigning tempfile.tempdir is intentional. Merely setting TEMP/TMP lets
    # Python silently search personal/system fallback folders if a drive fails.
    tempfile.tempdir=path
    return path
