"""0.30.0, Judy's spec section 10: the details panel's "Book metadata" line no longer prints the internal grouping key
(a path, a \\x1f, Album and Artist tags read as Latin-1). Every rendered candidate carries scope_view, the engine's own
display facts: {kind, album, artist, track, track_total, basis, repaired, folders, title, author}, read from the repaired tag
text (tag_text). The key (scope) itself is unchanged. Pure grouping on catalog-shaped rows plus one SQLite read for the
volumes' recorded reasons; no audio, no network."""
import json
import sqlite3
import unittest
from pathlib import Path

import groups

ROOT = str(Path('X:/private-fixture'))
FOLDER = str(Path(ROOT) / 'Unsorted' / 'Линдквист - Впусти меня')


def latin1(text):
    """cp1251 bytes read as ISO-8859-1, as some MP3 uploads store Russian tags."""
    return text.encode('cp1251').decode('latin-1')


def file(path, **tags):
    metadata = {'tags': tags, 'probe': {'format': {'duration': '60'}}}
    return {'root': ROOT, 'path': str(path), 'kind': 'audiobook', 'size': 10, 'modified': 10, 'metadata': json.dumps(metadata, ensure_ascii=False),
            'error': '', 'missing': 0}


def only(built):
    assert len(built) == 1, list(built)
    return next(iter(built.values()))


def stored(evidence, identity='book-1'):
    """A book_groups row as SQLite returns it to render()."""
    return {'id': identity, 'root': ROOT, 'scope': evidence['scope'], 'revision': 1, 'fingerprint': 'f' * 64, 'evidence': json.dumps(evidence, ensure_ascii=False),
            'review': '', 'approved': 0, 'changed': 0}


class ScopeViewTests(unittest.TestCase):
    def view(self, group, volumes=None):
        self.assertTrue(hasattr(groups, 'scope_view'), 'the engine builds the display facts (positive control: missing before 0.30.0)')
        return groups.scope_view(group, volumes)

    def test_an_album_book_names_its_album_and_artist_never_the_key(self):
        group = only(groups.build([file(Path(FOLDER) / '01.mp3', album='Впусти меня', artist='Линдквист Йон Айвиде', track='1/2'),
                                   file(Path(FOLDER) / '02.mp3', album='Впусти меня', artist='Линдквист Йон Айвиде', track='2/2')]))
        self.assertIn('\x1f', group['scope'], 'the key itself is unchanged')
        view = self.view(group)
        self.assertEqual({k: view[k] for k in ('kind', 'album', 'artist', 'track', 'track_total', 'basis', 'repaired', 'folders')},
                         {'kind': 'album', 'album': 'Впусти меня', 'artist': 'Линдквист Йон Айвиде', 'track': None, 'track_total': None,
                          'basis': None, 'repaired': False, 'folders': [FOLDER]})
        self.assertNotIn('\x1f', json.dumps(view, ensure_ascii=False))

    def test_a_cp1251_album_read_as_latin1_is_sent_repaired_and_says_so(self):
        album, artist = latin1('Впусти меня'), latin1('Линдквист Йон Айвиде')
        self.assertNotEqual(album, 'Впусти меня')
        group = only(groups.build([file(Path(FOLDER) / '01.mp3', album=album, artist=artist, track='1/2'),
                                   file(Path(FOLDER) / '02.mp3', album=album, artist=artist, track='2/2')]))
        view = self.view(group)
        self.assertEqual((view['kind'], view['album'], view['artist'], view['repaired']), ('album', 'Впусти меня', 'Линдквист Йон Айвиде', True))
        self.assertEqual(group['members'][0]['metadata']['tags']['album'], album, 'the raw tag snapshot stays raw')
        # Only the shown text counts: a repaired comment alone is no repaired album line.
        plain = only(groups.build([file(Path(FOLDER) / 'a.m4b', album='Впусти меня', comment=latin1('Комментарий к книге'))]))
        self.assertFalse(self.view(plain)['repaired'])

    def test_one_audiobook_file_carries_its_track(self):
        group = only(groups.build([file(Path(FOLDER) / 'Впусти меня 2.m4b', album='Впусти меня', artist='Линдквист Йон Айвиде', track='2/5')]))
        view = self.view(group)
        self.assertEqual((view['kind'], view['album'], view['track'], view['track_total']), ('single_file', 'Впусти меня', 2, 5))
        bare = only(groups.build([file(Path(FOLDER) / 'Впусти меня.m4b', title='Впусти меня', track='3')]))
        self.assertEqual({k: self.view(bare)[k] for k in ('kind', 'album', 'artist', 'track', 'track_total')},
                         {'kind': 'single_file', 'album': None, 'artist': None, 'track': 3, 'track_total': None}, 'a missing album or artist is None, never "Unknown"')

    def test_a_volume_kept_separate_says_the_engines_own_reason(self):
        paths = [Path(FOLDER) / ('Впусти меня %d.m4b' % n) for n in (1, 2)]
        built = groups.build([file(path, album='Впусти меня', artist='Линдквист Йон Айвиде', track='%d/5' % n) for n, path in enumerate(paths, 1)],
                             volumes=frozenset(str(path) for path in paths))
        self.assertEqual(len(built), 2)
        group = next(g for g in built.values() if g['members'][0]['path'] == str(paths[1]))
        self.assertTrue(group['scope'].endswith('\x1fVolume of a series'))
        cases = {'each file names its own work': 'each file names its own work',
                 'each file starts again at chapter 1': 'each file starts again at chapter 1',
                 'each file ends with its own afterword': 'each file ends with its own afterword',
                 'no chapters to compare': 'there are no chapters to compare',
                 groups.KEPT_BASIS + ' on 2026-11-18': 'you chose Keep as separate books',
                 'a reason this build does not know': None}
        for recorded, said in cases.items():
            view = self.view(group, {str(paths[1]): recorded})
            self.assertEqual((view['kind'], view['basis'], view['album'], view['track'], view['track_total']), ('volume', said, 'Впусти меня', 2, 5), recorded)
        self.assertIsNone(self.view(group)['basis'], 'no recorded reason: none is invented')

    def test_every_other_grouping_has_its_kind(self):
        unsorted = Path(ROOT) / 'Unsorted'
        standalone = only(groups.build([file(unsorted / 'Рассказ.mp3')]))
        self.assertEqual(self.view(standalone)['kind'], 'standalone')
        work = only(groups.build([file(unsorted / 'Лукьяненко Сергей - Ночной дозор.mp3')]))
        view = self.view(work)
        self.assertEqual((view['kind'], view['author'], view['title']), ('filename_work', 'Лукьяненко Сергей', 'Ночной дозор'))
        # Scope shapes the other planners store (split books, numbered and same-title sets, part sets, folder units,
        # anthology volumes, provisional subgroups, manual conversions), read from the key's own tag.
        member = groups.member(file(Path(FOLDER) / '01.mp3', album='Впусти меня', artist='Линдквист Йон Айвиде', title='Впусти меня'))
        def kind(scope, **extra):
            return self.view({'scope': scope, 'members': [member], **extra})
        self.assertEqual(kind(FOLDER + '\x1fSplit book впустименя')['kind'], 'split_book')
        self.assertEqual(kind(FOLDER + '\x1fSplit book')['kind'], 'split_book')
        self.assertEqual(kind(FOLDER + '\x1fNumbered set 01')['kind'], 'numbered_set')
        self.assertEqual(kind(FOLDER + '\x1fUnverified numbered source set')['kind'], 'numbered_set')
        same = kind(FOLDER + '\x1fSame title впустименя')
        self.assertEqual((same['kind'], same['title'], same['artist']), ('same_title', 'Впусти меня', 'Линдквист Йон Айвиде'))
        self.assertEqual(kind(FOLDER + '\x1fSame album впустименя')['kind'], 'album')
        self.assertEqual(kind(FOLDER + '\x1fPart set впустименя\x1fлиндквист')['kind'], 'album')
        self.assertEqual(kind(FOLDER + '\x1fAlbum впустименя\x1fArtist линдквист\x1fProvisional subgroup ' + FOLDER)['kind'], 'album')
        for decision in ('one', 'ask', 'remainder'):
            folder = kind(FOLDER + '\x1fSource folder', folder_unit={'kind': decision})
            self.assertEqual((folder['kind'], folder['basis']), ('folder', decision))
        self.assertEqual(kind(FOLDER + '\x1fFolder remainder', folder_unit={'kind': 'remainder'})['basis'], 'remainder')
        self.assertEqual(kind(FOLDER + '\x1fNamed anthology volume Калейдоскоп 4')['kind'], 'anthology')
        self.assertEqual(kind(FOLDER + '\x1fmanual:1234')['kind'], 'other')
        self.assertEqual(kind(FOLDER)['kind'], 'other')

    def test_folders_are_every_distinct_folder_in_member_order(self):
        cds = [file(Path(FOLDER) / ('CD%d' % n) / '01.mp3', album='Впусти меня', artist='Линдквист Йон Айвиде', track='1') for n in (1, 2, 3)]
        group = only(groups.build(cds))
        self.assertEqual(self.view(group)['folders'], [str(Path(FOLDER) / ('CD%d' % n)) for n in (1, 2, 3)])
        self.assertEqual(self.view({'scope': 'x', 'members': []})['folders'], [], 'no folder known: none')

    def test_every_rendered_candidate_carries_scope_view_with_the_recorded_volume_reason(self):
        path = Path(FOLDER) / 'Впусти меня 2.m4b'
        group = only(groups.build([file(path, album='Впусти меня', track='2/5')], volumes=frozenset({str(path)})))
        rendered = groups.render(stored(group), ROOT, True, {}, {str(path): 'each file names its own work'})
        self.assertEqual(rendered['scope'], group['scope'], 'the key is unchanged')
        self.assertEqual((rendered['scope_view']['kind'], rendered['scope_view']['basis']), ('volume', 'each file names its own work'))
        self.assertEqual(groups.render(stored(group), ROOT, True)['scope_view']['basis'], None, 'callers without the catalog read send no reason')
        # The catalog read: only a volume fact that still matches its file counts.
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE files(root TEXT, path TEXT, size INTEGER, modified TEXT, kind TEXT, metadata TEXT, error TEXT, missing INTEGER)')
        db.execute('CREATE TABLE part_volumes(root TEXT, path TEXT, size INTEGER, modified TEXT, basis TEXT NOT NULL, checked TEXT NOT NULL, PRIMARY KEY(root,path))')
        db.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?)', (ROOT, str(path), 10, '10', 'audiobook', '{}', '', 0))
        db.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?)', (ROOT, 'changed.m4b', 11, '10', 'audiobook', '{}', '', 0))
        db.execute('INSERT INTO part_volumes VALUES(?,?,?,?,?,?)', (ROOT, str(path), 10, '10', 'each file names its own work', 'now'))
        db.execute('INSERT INTO part_volumes VALUES(?,?,?,?,?,?)', (ROOT, 'changed.m4b', 10, '10', 'no chapters to compare', 'now'))
        self.assertEqual(groups.volume_bases(db, ROOT), {str(path): 'each file names its own work'})
        empty = sqlite3.connect(':memory:')
        self.assertEqual(groups.volume_bases(empty, ROOT), {}, 'no volumes table yet: nothing')


if __name__ == '__main__':
    unittest.main()
