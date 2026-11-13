"""Relocation authority has explicit path, receipt class, catalog and generation."""
import copy
import hashlib
import json
import unittest
from storage_relocation import parse_manifest, RelocationRefused


def facts(volume, inode):
    return {'size': 21, 'modified': 123456700, 'dev': volume, 'ino': inode,
            'identity_method': 'FileIdInfo128', 'identity_api_error': 0,
            'identity': [volume, 0, inode], 'links': 1, 'attributes': 32}


def fixture():
    return {'schema': 'books-storage-relocation-v1',
            'generation': 'd9ab5afe-fcd4-4ebe-a779-b4e701edc039',
            'catalog_id': 'f351a0ae-6cc2-4450-b6e9-f2c1cb4ec4f4',
            'source_root': r'C:\private-old', 'target_root': r'I:\private-new',
            'scopes': ['data'], 'source_snapshot_sha256': 'a' * 64,
            'directories': [
                {'relative': '', 'source_identity': [1, 0, 1], 'target_identity': [2, 0, 1]},
                {'relative': 'data', 'source_identity': [1, 0, 2], 'target_identity': [2, 0, 2]}],
            'files': [{'relative': r'data\évidence.bin', 'source_facts': facts(1, 3),
                       'target_facts': facts(2, 4), 'sha256': 'b' * 64,
                       'receipt_classes': ['working-file']}]}


def parse(value):
    raw = json.dumps(value, ensure_ascii=False).encode()
    return parse_manifest(raw, hashlib.sha256(raw).hexdigest())


class RelocationManifestTests(unittest.TestCase):
    def test_native_facts_remain_actual_and_every_authority_dimension_matters(self):
        value = fixture(); manifest = parse(value); path = r'C:\private-old\data\évidence.bin'
        actual, expected = facts(2, 4), facts(1, 3)
        args = dict(receipt_class='working-file', catalog_id=manifest.catalog_id,
                    generation=manifest.generation)
        self.assertTrue(manifest.historical_facts_match(path, actual, expected, **args))
        self.assertEqual(actual['identity'], [2, 0, 4])
        for changed in ('size', 'modified', 'ino', 'attributes', 'identity_api_error'):
            bad = copy.deepcopy(actual); bad[changed] += 1
            self.assertFalse(manifest.historical_facts_match(path, bad, expected, **args), changed)
        bad = copy.deepcopy(actual); bad['identity'][2] += 1
        self.assertFalse(manifest.historical_facts_match(path, bad, expected, **args))
        self.assertFalse(manifest.historical_facts_match(path, expected, expected, **args))
        self.assertFalse(manifest.historical_facts_match(path, actual, actual, **args))
        self.assertFalse(manifest.historical_facts_match(path, actual, expected,
                         **dict(args, receipt_class='recovery-copy')))
        for changed in ('catalog_id', 'generation'):
            with self.assertRaises(RelocationRefused):
                manifest.historical_facts_match(path, actual, expected, **dict(args, **{changed: 'wrong'}))
        with self.assertRaises(RelocationRefused):
            manifest.historical_facts_match(path, actual, expected, **dict(args, receipt_class='producer-closure'))

    def test_alias_scope_does_not_include_other_projects_or_neighbor_prefixes(self):
        manifest = parse(fixture())
        self.assertTrue(manifest.permitted(r'C:\private-old\data\évidence.bin'))
        for path in (r'C:\private-old\data-other\évidence.bin', r'C:\private-old\sibling\file',
                     r'C:\private-old2\data\évidence.bin', r'Z:\Audiobooks\book.m4b'):
            self.assertFalse(manifest.permitted(path), path)

    def test_duplicate_json_keys_and_unpinned_bytes_refuse(self):
        raw = b'{"schema":1,"schema":2}'
        with self.assertRaises(RelocationRefused):parse_manifest(raw, hashlib.sha256(raw).hexdigest())
        raw = json.dumps(fixture()).encode()
        with self.assertRaises(RelocationRefused):parse_manifest(raw, '0' * 64)

    def test_ambiguous_paths_native_links_missing_ancestry_and_unknown_schema_refuse(self):
        changes = [
            lambda v: v.update(target_root=r'\\server\share\new'),
            lambda v: v.update(target_root=r'C:\private-old\nested'),
            lambda v: v.update(source_root='C:\\'),
            lambda v: v.update(scopes=['data', 'DATA']),
            lambda v: v.update(scopes=['data', r'data\nested']),
            lambda v: v.update(schema='unknown'),
            lambda v: v.update(unrecognized_authority=True),
            lambda v: v['files'][0].update(relative=r'data\..\sibling'),
            lambda v: v['files'][0].update(relative=r'data\file:stream'),
            lambda v: v['files'][0].update(relative=r'data\CON.txt'),
            lambda v: v['files'][0].update(relative=r'data\name.'),
            lambda v: v['files'][0].update(relative=r'data\*.bin'),
            lambda v: v['files'].append(copy.deepcopy(v['files'][0])),
            lambda v: v['files'][0]['target_facts'].update(links=2),
            lambda v: v['files'][0]['target_facts'].update(attributes=0x420),
            lambda v: v['files'][0]['target_facts'].update(ino=True),
            lambda v: v['files'][0]['target_facts'].update(identity=[0, 0, 0]),
            lambda v: v['files'][0].update(receipt_classes=[{}]),
            lambda v: v['files'][0].update(receipt_classes=['producer-closure']),
            lambda v: v['directories'].pop(),
        ]
        for change in changes:
            value = fixture(); change(value)
            with self.subTest(value=value), self.assertRaises(RelocationRefused):parse(value)

    def test_validated_bindings_are_immutable(self):
        manifest = parse(fixture()); entry = next(iter(manifest.files.values()))
        with self.assertRaises(TypeError):entry.target['size'] = 2
        with self.assertRaises(TypeError):manifest.files['other'] = entry
        with self.assertRaises(TypeError):entry.target['identity'][0] = 7


if __name__ == '__main__':unittest.main()
