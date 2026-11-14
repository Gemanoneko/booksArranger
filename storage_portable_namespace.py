"""Root-relative current storage names; immutable origin names are evidence only.

This pure codec grants no filesystem or disposal authority. Native admission must
hold the current root/catalog and validate the durable binding registration.
"""
from dataclasses import dataclass
import hashlib
import json
import ntpath
from types import MappingProxyType

from storage_relocation import (_inside, _key, _need, _object, _relative, _root,
                                _sha, _uuid, _facts, parse_manifest)

SCHEMA = 'books-portable-runtime-v1'
TABLE = 'storage_portable_runtime'
SQL = f'''CREATE TABLE {TABLE}(
    catalog_id TEXT PRIMARY KEY, generation TEXT NOT NULL,
    binding_id TEXT NOT NULL, binding_sha256 TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision>0))'''


def relative_path(value):
    """Every managed path is a strict child of the current installation anchor."""
    return _relative(value)


def anchored(anchor, relative):
    return ntpath.join(_root(str(anchor)), relative_path(relative))


def registration(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone():
        return None
    rows = db.execute(f'SELECT catalog_id,generation,binding_id,binding_sha256,revision FROM {TABLE}').fetchall()
    _need(len(rows) == 1, 'Portable storage binding is missing or ambiguous')
    return tuple(rows[0])


@dataclass(frozen=True)
class Namespace:
    anchor: str
    value: object
    digest: str
    origin: object
    controls: object

    @property
    def data(self):
        return anchored(self.anchor, self.value['data'])

    @property
    def origin_data(self):
        return ntpath.join(self.origin.source_root, self.origin.scopes[0])

    @property
    def previous_data(self):
        return self.value['previous_data']

    def current_path(self, path):
        """Translate only the exact internal data namespace, never library roots."""
        path = _root(str(path))
        for base in (self.data, self.origin_data, ntpath.join(self.origin.target_root,self.origin.scopes[0]), *self.value['aliases']):
            if _inside(path, base):
                tail = ntpath.relpath(path, base)
                return self.data if tail == '.' else ntpath.join(self.data, _relative(tail))
        _need(False, 'Path is outside the bound application data namespace')

    def origin_path(self, path):
        current = self.current_path(path)
        tail = ntpath.relpath(current, self.data)
        return self.origin_data if tail == '.' else ntpath.join(self.origin_data, _relative(tail))

    def control_path(self, origin_path, expected_sha256):
        """Resolve only a separately pinned typed control, not arbitrary old paths."""
        row = self.controls.get(_key(str(origin_path)))
        if row is None:
            row = next((item for item in self.controls.values()
                        if _key(anchored(self.anchor,item['relative']))==_key(str(origin_path))),None)
        _need(row is not None and row['sha256'] == expected_sha256,
              'Historical control is absent from the current portable binding')
        return anchored(self.anchor, row['relative'])

    def file_binding(self, path):
        tail = ntpath.relpath(self.current_path(path), self.data)
        return self.value['files'].get(_key(_relative(tail)))

    def permitted(self, path):
        try:
            self.current_path(path)
            return True
        except ValueError:
            return False


def parse_binding(raw, digest, anchor, origin_raw):
    _sha(digest)
    _need(isinstance(raw, bytes) and 0 < len(raw) <= 64 * 1024 * 1024 and
          hashlib.sha256(raw).hexdigest() == digest, 'Portable binding bytes changed')
    value = json.loads(raw.decode('utf8'), object_pairs_hook=_object)
    fields = {'schema', 'binding_id', 'catalog_id', 'generation', 'data', 'origin',
              'controls', 'root_identity', 'files', 'directories', 'detach_sha256',
              'retention_sha256', 'migration_id', 'revision','origin_ancestry','previous_ancestry','previous_data','aliases'}
    _need(isinstance(value, dict) and set(value) == fields and value['schema'] == SCHEMA,
          'Unsupported portable storage binding')
    for field in ('binding_id', 'catalog_id', 'generation', 'migration_id'):
        _uuid(value[field])
    _need(type(value['revision']) is int and value['revision'] > 0, 'Invalid portable binding revision')
    relative_path(value['data'])
    _root(value['previous_data'])
    _need(isinstance(value['aliases'],list) and 1<=len(value['aliases'])<=1000,'Invalid prior namespace list')
    for alias in value['aliases']:_root(alias)
    _need(value['previous_data'] in value['aliases'],'Immediate previous namespace is missing')
    for field in ('detach_sha256', 'retention_sha256'):
        _sha(value[field])
    origin = value['origin']
    _need(isinstance(origin, dict) and set(origin) == {'path', 'relative', 'sha256'},
          'Portable binding needs its exact immutable origin descriptor')
    _root(origin['path']); relative_path(origin['relative']); _sha(origin['sha256'])
    manifest = parse_manifest(origin_raw, origin['sha256'])
    _need((value['catalog_id'], value['generation']) == (manifest.catalog_id, manifest.generation)
          and len(manifest.scopes) == 1, 'Portable binding belongs to a different catalog generation')
    controls = {}
    relatives = set()
    _need(isinstance(value['controls'], list) and 1 <= len(value['controls']) <= 100000,
          'Invalid portable control census')
    for row in value['controls']:
        _need(isinstance(row, dict) and set(row) == {'origin', 'relative', 'sha256', 'kind'},
              'Malformed portable control binding')
        key = _key(_root(row['origin'])); relative = _key(relative_path(row['relative'])); _sha(row['sha256'])
        _need(key not in controls and relative not in relatives and isinstance(row['kind'], str) and row['kind'],
              'Duplicate or untyped portable control')
        controls[key] = row; relatives.add(relative)
    _need(controls.get(_key(origin['path'])) == dict(origin=origin['path'], relative=origin['relative'],
          sha256=origin['sha256'], kind='relocation-manifest'), 'Portable origin control pin differs')
    for field in ('files', 'directories'):
        _need(isinstance(value[field], dict) and len(value[field]) <= 100000,
              'Invalid portable native member census')
        for key in value[field]:
            _need(key == _key(_relative(key, root=field == 'directories')),
                  'Portable member key is not canonical')
            row=value[field][key]
            expected={'prior','current','copied_from','location_history','prior_security','current_security'} | ({'sha256'} if field=='files' else set())
            _need(isinstance(row,dict) and set(row)==expected,'Portable native bridge has unknown fields')
            _need(isinstance(row['location_history'],list) and 1<=len(row['location_history'])<=1000,'Invalid location history')
            for history in row['location_history']:
                if field=='files':_facts(history)
                else:_need(isinstance(history,list) and len(history)==3 and all(type(n) is int and n>=0 for n in history),'Invalid historical directory identity')
            if field=='files':
                _facts(row['prior']);_facts(row['current']);_facts(row['copied_from']);_sha(row['sha256'])
            else:
                for kind in ('prior','current','copied_from'):
                    _need(isinstance(row[kind],list) and len(row[kind])==3 and all(type(n) is int and n>=0 for n in row[kind]),
                          'Portable directory identity is malformed')
            for kind in ('prior_security','current_security'):
                security=row[kind]
                _need(isinstance(security,dict) and set(security)=={'bytes','sddl','protected','sha256'},
                      'Portable security bridge is malformed')
                _sha(security['sha256'])
    _need('' in value['directories'] and 'inventory.sqlite3' in value['files'] and
          'inventory.sqlite3.lock' in value['files'] and
          value['root_identity']==value['directories']['']['current'],'Portable root/catalog bridge is incomplete')
    for field in ('origin_ancestry','previous_ancestry'):
        _need(isinstance(value[field],list) and value[field], 'Portable ancestry bridge is missing')
        for row in value[field]:
            _need(isinstance(row,list) and len(row)==4 and ntpath.isabs(row[0]) and
                  all(type(n) is int and n>=0 for n in row[1:]),'Invalid portable ancestry bridge')
    return Namespace(_root(str(anchor)), MappingProxyType(value), digest, manifest, MappingProxyType(controls))
