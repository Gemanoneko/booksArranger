"""Explicit historical storage bindings for a verified offline local-volume move.

This module never follows a junction, changes a receipt, copies a file, grants
producer closure, or fabricates native facts. Native access/activation leases
are separate; the pure manifest validator cannot authorize a live operation.
"""
from dataclasses import dataclass
import hashlib
import json
import ntpath
import re
from types import MappingProxyType
import uuid

SCHEMA = 'books-storage-relocation-v1'
MAX_MANIFEST_BYTES = 64 * 1024 * 1024
MAX_ENTRIES = 100000
FACT_KEYS = frozenset({'size', 'modified', 'dev', 'ino', 'identity_method',
                       'identity_api_error', 'identity', 'links', 'attributes'})
# Each historical comparison names its own contract. Process/boot/producer
# closure proofs are deliberately absent: relocation cannot create them.
RECEIPT_CLASSES = frozenset({'working-file', 'staging-artifact', 'cleanup-file',
    'recovery-copy', 'retained-source', 'index-leaf', 'index-journal',
    'repair-copy', 'storage-directory', 'catalog-storage','catalog-owner-lock','file-disposition-control'})


class RelocationRefused(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise RelocationRefused(message)


def _object(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, 'Duplicate relocation JSON key')
        result[key] = value
    return result


def _uuid(value):
    _need(isinstance(value, str), 'Canonical relocation UUID required')
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as error:
        raise RelocationRefused('Canonical relocation UUID required') from error
    _need(str(parsed) == value, 'Canonical relocation UUID required')
    return value


def _sha(value):
    _need(isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value),
          'Exact lowercase SHA-256 required')
    return value


def _relative(value, *, root=False):
    _need(isinstance(value, str) and (root or bool(value)), 'Relative storage path required')
    if value == '' and root:
        return ''
    _need(not value.startswith(('\\', '/')) and not ntpath.splitdrive(value)[0],
          'Storage entry must be relative')
    parts = value.replace('/', '\\').split('\\')
    _need(all(part and part not in ('.', '..') and ':' not in part and
              not part.endswith((' ', '.')) and not any(ord(c) < 32 or c in '<>"|?*' for c in part)
              for part in parts), 'Ambiguous storage path refused')
    _need(all(not re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',
                              part, re.IGNORECASE) for part in parts),
          'Windows device path refused')
    return '\\'.join(parts)


def _root(value):
    _need(isinstance(value, str), 'Absolute local storage root required')
    drive, tail = ntpath.splitdrive(value)
    _need(re.fullmatch('[A-Za-z]:', drive or '') and tail.startswith(('\\', '/')),
          'Absolute local drive path required; UNC/device roots are unsupported')
    relative = _relative(tail[1:])
    _need(relative != '', 'Whole drive relocation refused')
    return drive.upper() + '\\' + relative


def _key(value):
    return ntpath.normcase(value)


def _inside(path, root):
    return _key(path) == _key(root) or _key(path).startswith(_key(root) + '\\')


def _facts(value, *, directory=False):
    _need(isinstance(value, dict) and set(value) == FACT_KEYS,
          'Complete native file facts required')
    numeric = ('size', 'modified', 'dev', 'ino', 'identity_api_error', 'links', 'attributes')
    _need(all(type(value[k]) is int and value[k] >= 0 for k in numeric),
          'Native facts contain invalid numeric fields')
    identity = value['identity']
    _need(isinstance(identity, list) and len(identity) == 3 and
          all(type(n) is int and 0 <= n <= 0xffffffff for n in identity) and
          identity[0] > 0 and bool(identity[1] or identity[2]), 'Native identity is ambiguous')
    _need(value['dev'] > 0 and value['ino'] > 0 and value['links'] == 1 and
          value['identity_method'] in ('FileIdInfo128', 'BY_HANDLE_FILE_INFORMATION64'),
          'Native identity method or link count is unsupported')
    _need(not value['attributes'] & 0x400 and bool(value['attributes'] & 0x10) == directory,
          'Reparse or wrong-type storage entry refused')
    # Tuples make the validated native identity immutable as well as the map.
    return MappingProxyType(dict(value, identity=tuple(identity)))


def _plain(facts):
    return dict(facts, identity=list(facts['identity']))


@dataclass(frozen=True)
class FileBinding:
    relative: str
    source: object
    target: object
    sha256: str
    receipt_classes: frozenset


@dataclass(frozen=True)
class DirectoryBinding:
    relative: str
    source: tuple
    target: tuple


@dataclass(frozen=True)
class Manifest:
    generation: str
    catalog_id: str
    source_root: str
    target_root: str
    scopes: tuple
    source_snapshot_sha256: str
    digest: str
    files: object
    directories: object

    def relative(self, logical_path):
        _need(isinstance(logical_path, str) and _inside(logical_path, self.source_root),
              'Path is outside the explicitly relocated source root')
        relative = ntpath.relpath(logical_path, self.source_root)
        return _relative(relative)

    def permitted(self, logical_path):
        try:
            relative = self.relative(logical_path)
        except RelocationRefused:
            return False
        return any(_inside(relative, scope) for scope in self.scopes)

    def logical_location(self,path):
        """Explicit scoped location only; does not authorize filesystem access."""
        if self.permitted(path):return ntpath.normpath(path)
        _need(isinstance(path,str) and _inside(path,self.target_root),
              'Selected location is outside the relocated managed storage')
        relative=_relative(ntpath.relpath(path,self.target_root))
        logical=ntpath.join(self.source_root,relative)
        _need(self.permitted(logical),'Selected physical location escapes managed storage scopes')
        return logical

    def historical_facts_match(self, logical_path, actual, expected, *,
                               receipt_class, catalog_id, generation):
        """Pure predicate only; caller must retain a live activation/native lease.

        A different record class, catalog, generation, native identity, size,
        timestamp or fact field refuses. This never replaces same-handle hashes.
        """
        _need(catalog_id == self.catalog_id and generation == self.generation,
              'Historical receipt requires its exact catalog and generation')
        _need(receipt_class in RECEIPT_CLASSES and receipt_class != 'storage-directory',
              'Unsupported historical receipt class')
        if not self.permitted(logical_path):
            return False
        binding = self.files.get(_key(self.relative(logical_path)))
        return bool(binding and receipt_class in binding.receipt_classes and
                    actual == _plain(binding.target) and expected == _plain(binding.source))


def parse_manifest(raw, expected_sha256):
    _need(isinstance(raw, bytes) and 0 < len(raw) <= MAX_MANIFEST_BYTES,
          'Relocation manifest exceeds its bounded byte contract')
    _sha(expected_sha256)
    _need(hashlib.sha256(raw).hexdigest() == expected_sha256,
          'Relocation manifest SHA-256 differs from explicit selection')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(
                               RelocationRefused('Non-finite relocation value refused')))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RelocationRefused('Relocation manifest is not strict UTF-8 JSON') from error
    keys = {'schema', 'generation', 'catalog_id', 'source_root', 'target_root', 'scopes',
            'source_snapshot_sha256', 'files', 'directories'}
    _need(isinstance(value, dict) and set(value) == keys and value['schema'] == SCHEMA,
          'Unsupported relocation manifest schema')
    source, target = _root(value['source_root']), _root(value['target_root'])
    _need(not _inside(source, target) and not _inside(target, source),
          'Source and target storage roots overlap')
    scopes = value['scopes']
    _need(isinstance(scopes, list) and 0 < len(scopes) <= 32, 'Bounded explicit scopes required')
    scopes = tuple(_relative(s) for s in scopes)
    _need(len({_key(s) for s in scopes}) == len(scopes), 'Duplicate storage scope refused')
    _need(not any(_inside(a, b) for a in scopes for b in scopes if a != b),
          'Nested storage scopes refused')
    rawfiles, rawdirs = value['files'], value['directories']
    _need(isinstance(rawfiles, list) and isinstance(rawdirs, list) and
          len(rawfiles) + len(rawdirs) <= MAX_ENTRIES, 'Bounded relocation entries required')
    files, directories = {}, {}
    for entry in rawdirs:
        _need(isinstance(entry, dict) and set(entry) == {'relative', 'source_identity', 'target_identity'},
              'Malformed relocated directory binding')
        relative = _relative(entry['relative'], root=True)
        _need(relative == '' or any(_inside(relative, s) or _inside(s, relative) for s in scopes),
              'Directory binding is outside managed scopes/ancestors')
        identities = []
        for key in ('source_identity', 'target_identity'):
            identity = entry[key]
            _need(isinstance(identity, list) and len(identity) == 3 and
                  all(type(n) is int and 0 <= n <= 0xffffffff for n in identity) and
                  identity[0] and (identity[1] or identity[2]), 'Directory identity is ambiguous')
            identities.append(tuple(identity))
        key = _key(relative)
        _need(key not in directories, 'Duplicate relocated directory path')
        directories[key] = DirectoryBinding(relative, *identities)
    _need('' in directories, 'Relocation root directory binding is missing')
    for entry in rawfiles:
        _need(isinstance(entry, dict) and set(entry) == {'relative', 'source_facts',
              'target_facts', 'sha256', 'receipt_classes'}, 'Malformed relocated file binding')
        relative = _relative(entry['relative'])
        _need(any(_inside(relative, scope) for scope in scopes), 'File binding escapes managed scope')
        classes = entry['receipt_classes']
        _need(isinstance(classes, list) and classes and
              all(isinstance(c, str) and c in RECEIPT_CLASSES and c != 'storage-directory' for c in classes) and
              len(set(classes)) == len(classes),
              'Unknown or duplicate historical file receipt class')
        key = _key(relative)
        _need(key not in files and key not in directories, 'Duplicate relocated file path')
        parent = ntpath.dirname(relative)
        _need(_key(parent) in directories, 'File parent has no native directory binding')
        files[key] = FileBinding(relative, _facts(entry['source_facts']), _facts(entry['target_facts']),
                                 _sha(entry['sha256']), frozenset(classes))
    for key, binding in directories.items():
        if binding.relative:
            _need(_key(ntpath.dirname(binding.relative)) in directories,
                  'Directory binding ancestry is incomplete')
    return Manifest(_uuid(value['generation']), _uuid(value['catalog_id']), source, target, scopes,
                    _sha(value['source_snapshot_sha256']), expected_sha256,
                    MappingProxyType(files), MappingProxyType(directories))
