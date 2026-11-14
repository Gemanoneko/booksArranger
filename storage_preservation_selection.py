"""Explicit copy-only admission for a finite reviewed inventory."""
import ntpath
import re

from storage_relocation import _key, _relative
from storage_relocation_operator import need, pinned_receipt

SCHEMA = 'books-storage-preservation-selection-v1'
HOLD = 'Copy-only files remain untyped for normal application use or disposal'
AREAS = {'merge-cache\\audio-staging', 'merge-cache\\covers',
         'merge-cache\\series-backfill', 'chapter-repairs'}


def approved_members(pin, source, target, scope):
    need(isinstance(pin, dict) and set(pin) == {'path', 'sha256'}, 'Exact preservation selection pin required')
    with pinned_receipt(pin['path'], pin['sha256']) as receipt:
        need(set(receipt) == {'schema','source','target','scope','members'}
             and receipt['schema'] == SCHEMA
             and (receipt['source'], receipt['target'], receipt['scope']) == (str(source), str(target), scope),
             'Preservation selection scope or roots differ')
        need(isinstance(receipt['members'], list) and 0 < len(receipt['members']) <= 15000,
             'Preservation selection exceeds bounds')
        result = {}
        for row in receipt['members']:
            need(isinstance(row, dict) and set(row) == {'relative','kind','facts','security_sha256','sha256'},
                 'Invalid preservation member')
            relative = _relative(row['relative'])
            path = _key(ntpath.relpath(relative, scope))
            need(any(path == area or path.startswith(area + '\\') for area in AREAS)
                 and not any(part == '.git' for part in path.split('\\')),
                 'Preservation member escapes bounded data subareas')
            need(row['kind'] in ('file', 'directory') and isinstance(row['facts'], dict)
                 and isinstance(row['security_sha256'], str) and re.fullmatch('[a-f0-9]{64}', row['security_sha256'])
                 and (re.fullmatch('[a-f0-9]{64}', row['sha256'] or '') if row['kind'] == 'file' else row['sha256'] is None),
                 'Malformed preservation evidence')
            key = _key(relative)
            need(key not in result, 'Duplicate preservation member')
            result[key] = row
        return result


def compare_member(expected, actual, kind, security, facts=None):
    need(expected['kind'] == kind and expected['relative'] == actual['relative'],
         'Preservation member path or kind changed')
    need(expected['facts'] == (actual['facts'] if facts is None else facts)
         and expected['security_sha256'] == security['sha256']
         and expected['sha256'] == actual.get('sha256'),
         'Preservation member identity, bytes, timestamp or security changed: ' + expected['relative'])
