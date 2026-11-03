"""Omen 0.24.5 regressions: private catalog metadata; no media or network access."""
import contextlib
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

import author_rules
import groups
import local_identity
from organization import plan, frozen_plan
from public_research import PublicResearch, attach_shared_routing
from shared_routing import resolve


class OfflineResearch(PublicResearch):
    def _gap_fill(self, *args, **kwargs):
        # The cache may be empty: the user's exact membership decision is sufficient.
        return {'closed': [], 'unfilled': ['original_title', 'series']}


class OmenApprovalTests(unittest.TestCase):
    def setUp(self):
        area = Path(os.environ.get('BOOKS_TEST_ROOT', Path(__file__).resolve().parents[1] / 'scratch' / 'omen-0245'))
        area.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=area)
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = str(self.base / 'Audiobooks')
        self.sorted = str(self.base / 'Audiobooks Sorted')
        self.database = self.base / 'catalog.sqlite3'
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute('CREATE TABLE files(root TEXT,path TEXT,kind TEXT,metadata TEXT,missing INTEGER DEFAULT 0,PRIMARY KEY(root,path))')
            author_rules.seed(db)
            db.commit()
        client = type('PrivateCache', (), {'database': str(self.database)})()
        self.research = OfflineResearch(client, leads=[])

    def book(self, title, author='Gordon McGill', series='', number='', **extra):
        tags = dict(title=title, album=title, artist=author, album_artist=author, **extra)
        if series: tags['series'] = series
        if number: tags['series-part'] = number
        metadata = {'title': title, 'artist': author, 'tags': tags,
                    'probe': {'format': {'duration': '60'}, 'streams': [
                        {'codec_type': 'audio', 'codec_name': 'aac', 'sample_rate': '44100', 'channels': 1}]}}
        item = {'root': self.root, 'path': str(Path(self.root) / 'Omen' / (title + '.m4b')),
                'kind': 'audiobook', 'size': 1000, 'modified': 1000, 'metadata': json.dumps(metadata),
                'error': '', 'missing': 0, 'seen': 1, 'arrival': 0, 'review': ''}
        with contextlib.closing(sqlite3.connect(self.database)) as db:
            db.execute("INSERT INTO files VALUES(?,?,'audiobook',?,0)", (self.root, item['path'], item['metadata']))
            db.commit()
        built = list(groups.build([item]).values())
        self.assertEqual(len(built), 1)
        return dict(built[0], id='private-omen', revision=7, fingerprint='private-source-fingerprint', source_root=self.root)

    def planned(self, result):
        return plan(self.sorted, result['review'], facts=result['metadata_facts'])

    def test_final_conflict_preview_and_approval_share_root_series(self):
        row = self.book('The Final Conflict', series='Omen', number='3')
        before = copy.deepcopy(row)
        preview = self.research.approved(row, self.root)
        approved = self.research.approved(row, self.root)
        self.assertEqual(self.planned(preview), self.planned(approved))
        self.assertEqual(Path(self.planned(approved)['path']).parent, Path(self.sorted) / 'Omen')
        self.assertEqual(approved['review']['number'], '3')
        self.assertEqual(approved['metadata_facts']['authors'], ['McGill Gordon'])
        self.assertIn('McGill Gordon', Path(self.planned(approved)['path']).name)
        self.assertEqual(row, before)

    def test_armageddon_editor_defaults_extract_series_and_preserve_title_year(self):
        row = self.book('Omen 4 - Armageddon 2000')
        values, _, local = self.research.names_read(row, self.root)
        self.assertEqual({key: values[key] for key in ('title', 'series', 'number')},
                         {'title': 'Armageddon 2000', 'series': 'Omen', 'number': '4'})
        self.assertFalse(local.get('series_unconfirmed'))

    def test_armageddon_approval_uses_the_same_extracted_values_and_shared_folder(self):
        row = self.book('Omen 4 - Armageddon 2000')
        preview = self.research.approved(row, self.root)
        approved = self.research.approved(row, self.root)
        self.assertEqual(self.planned(preview), self.planned(approved))
        self.assertEqual({key: approved['review'][key] for key in ('title', 'series', 'number')},
                         {'title': 'Armageddon 2000', 'series': 'Omen', 'number': '4'})
        self.assertFalse(approved['approval']['series_question'])
        self.assertEqual(Path(self.planned(approved)['path']).parent, Path(self.sorted) / 'Omen')
        self.assertIn('Armageddon 2000', Path(self.planned(approved)['path']).name)
        self.assertEqual(approved['metadata_facts']['authors'], ['McGill Gordon'])

    def test_explicit_series_and_position_win_over_confirmed_membership(self):
        row = self.book('Omen 4 - Armageddon 2000')
        result = self.research.approved(row, self.root, names={'series': 'My selected series', 'number': '8'})
        self.assertEqual((result['review']['series'], result['review']['number']), ('My selected series', '8'))
        self.assertFalse(resolve(result['review'], result['metadata_facts'])['multi_author_series'])
        self.assertEqual(Path(self.planned(result)['path']).parent, Path(self.sorted) / 'McGill Gordon' / 'My selected series')

    def test_explicit_empty_series_is_not_restored(self):
        row = self.book('Omen 4 - Armageddon 2000')
        result = self.research.approved(row, self.root, names={'series': '', 'number': ''})
        self.assertFalse(result['review'].get('series'))
        self.assertFalse(resolve(result['review'], result['metadata_facts'])['multi_author_series'])

    def test_typed_other_author_does_not_inherit_shared_authority(self):
        row = self.book('The Final Conflict', series='Omen', number='3')
        result = self.research.approved(row, self.root, author='Another Writer')
        self.assertFalse(resolve(result['review'], result['metadata_facts'])['multi_author_series'])
        self.assertIn('Writer Another', str(self.planned(result)['path']))

    def test_narrator_cannot_confirm_the_year_title(self):
        row = self.book('Omen 4 - Armageddon 2000', author='Another Writer', narrator='Gordon McGill')
        values, _, _ = self.research.names_read(row, self.root)
        self.assertEqual(values['title'], 'Omen 4 - Armageddon 2000')
        self.assertEqual((values['series'], values['number']), ('', ''))

    def test_explicit_destination_remains_authoritative(self):
        row = self.book('The Final Conflict', series='Omen', number='3')
        result = self.research.approved(row, self.root)
        chosen = str(Path(self.sorted) / 'Chosen destination')
        result['metadata_facts']['destination_override'] = {'id': 'private-choice', 'folder': chosen, 'identity': {}}
        self.assertEqual(Path(self.planned(result)['path']).parent, Path(chosen))


class OmenBoundaryTests(unittest.TestCase):
    def result(self, title='The Final Conflict', number='3', author='McGill Gordon', series='Omen'):
        return {'review': {'title': title, 'author': author, 'canonical_author': author, 'series': series, 'number': number},
                'metadata_facts': {'source_fingerprint': 'private-fingerprint', 'work_ids': ['local:private-omen'],
                                   'authors': [author], 'series_state': 'verified'},
                'work': {'id': 'local:private-omen'}}

    def test_all_confirmed_omen_books_keep_actual_author(self):
        for number, title, author in [('1', 'The Omen', 'David Seltzer'), ('2', 'Damien', 'Joseph Howard'),
                                      ('3', 'The Final Conflict', 'Gordon McGill'), ('4', 'Armageddon 2000', 'Gordon McGill')]:
            with self.subTest(number=number):
                original = self.result(title, number, author)
                result = attach_shared_routing(original)
                self.assertTrue(resolve(result['review'], result['metadata_facts'])['multi_author_series'])
                self.assertEqual(result['metadata_facts']['authors'], [author])
                self.assertNotIn('shared_routing', original['metadata_facts'])

    def test_wrong_work_position_credit_and_same_named_series_fail_closed(self):
        for values in [dict(title='Other work'), dict(number='2'), dict(author='Other Writer'),
                       dict(series='Other series'), dict(title='Armageddon 2001', number='4')]:
            with self.subTest(values=values):
                result = attach_shared_routing(self.result(**values))
                self.assertFalse(resolve(result['review'], result['metadata_facts'])['multi_author_series'])

    def test_title_year_exception_requires_exact_full_author_series_and_position(self):
        for title, author in [('Omen 3 - Armageddon 2000', 'Gordon McGill'),
                              ('Other 4 - Armageddon 2000', 'Gordon McGill'),
                              ('Omen 4 - Armageddon 2000', 'Other Writer'),
                              ('Omen 4 - Armageddon 2000', 'McGill'),
                              ('Omen 4 - Armageddon 2000', 'G. McGill'),
                              ('Omen 4 - Armageddon 2001', 'Gordon McGill'),
                              ('Omen 4 - Chapter 2', 'Gordon McGill'),
                              ('Omen 4 - 2. Armageddon 2000', 'Gordon McGill'),
                              ('Apollo 13: The Untold Story', 'Gordon McGill')]:
            with self.subTest(title=title, author=author):
                self.assertIsNone(local_identity.series_title_parts(title, author))
        self.assertEqual(local_identity.series_title_parts('Omen 4 - Armageddon 2000', 'McGill Gordon'),
                         {'series': 'Omen', 'number': '4', 'title': 'Armageddon 2000'})

    def test_changed_source_or_names_invalidate_existing_routing_proof(self):
        result = attach_shared_routing(self.result())
        for changes in [('title', 'Other work'), ('number', '4'), ('series', 'Other series'), ('canonical_author', 'Other Writer')]:
            altered = copy.deepcopy(result)
            altered['review'][changes[0]] = changes[1]
            with self.subTest(field=changes[0]):
                self.assertFalse(resolve(altered['review'], altered['metadata_facts'])['multi_author_series'])
        result['metadata_facts']['source_fingerprint'] = 'new-source'
        self.assertFalse(resolve(result['review'], result['metadata_facts'])['multi_author_series'])

    def test_old_published_manifest_is_not_rewritten_by_new_approval(self):
        original = self.result()
        manifest = {'metadata': copy.deepcopy(original['review']), 'metadata_facts': copy.deepcopy(original['metadata_facts'])}
        before = copy.deepcopy(manifest)
        root = os.path.abspath('private-output')
        old = frozen_plan(manifest, root)
        attach_shared_routing(original)
        self.assertEqual(manifest, before)
        self.assertEqual(frozen_plan(manifest, root), old)
        self.assertEqual(Path(old['path']).parent, Path(root) / 'McGill Gordon' / 'Omen')


if __name__ == '__main__':
    unittest.main()
