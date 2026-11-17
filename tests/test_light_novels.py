"""0.29.0 item 4: Light Novels as an audiobook type (Sergei 2026-11-17). Pure checks plus one private catalog; no library."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import entered_names
import light_novels
from organization import plan

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'light-novel-tests'
AREA.mkdir(parents=True, exist_ok=True)
ROOT = 'Z:\\Audiobooks'


class FolderTests(unittest.TestCase):
    def test_a_light_novels_or_ranobe_folder_below_the_root_pre_ticks(self):
        for path in ('Z:\\Audiobooks\\Light Novels\\Yukito Ayatsuji\\Another\\01.mp3', 'Z:\\Audiobooks\\light novels\\X\\a.m4b',
                     'Z:\\Audiobooks\\Ранобэ\\Автор\\Книга\\01.mp3', 'Z:\\Audiobooks\\Unsorted\\Ранобэ\\b.mp3'):
            with self.subTest(path=path):self.assertTrue(light_novels.from_path(path, ROOT))
        for path in ('Z:\\Audiobooks\\Light Novels Extra\\a.mp3', 'Z:\\Audiobooks\\My Light Novels\\a.mp3', 'Z:\\Audiobooks\\Ранобэшки\\a.mp3',
                     'Z:\\Audiobooks\\Fiction\\Light Novels.mp3'):
            with self.subTest(path=path):self.assertFalse(light_novels.from_path(path, ROOT), 'the exact folder segment, never a substring')
        self.assertFalse(light_novels.from_path('Z:\\Light Novels\\Book\\a.mp3', 'Z:\\Light Novels'), 'the library root itself is not a segment')

    def test_a_book_is_one_only_when_every_file_is(self):
        row = {'members': [{'path': ROOT + '\\Light Novels\\A\\1.mp3'}, {'path': ROOT + '\\Light Novels\\A\\2.mp3'}]}
        self.assertTrue(light_novels.from_row(row, ROOT))
        row['members'].append({'path': ROOT + '\\Other\\3.mp3'})
        self.assertFalse(light_novels.from_row(row, ROOT))
        self.assertFalse(light_novels.from_row({'members': []}, ROOT))


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.root = os.path.abspath('synthetic-output')
        self.review = {'title': 'Иная', 'canonical_author': 'Ayatsuji Yukito', 'series': 'Иная', 'number': '1'}

    def path(self, **changes):
        return plan(self.root, dict(self.review, **changes))['relative_path'].replace(os.sep, '/')

    def test_light_novels_go_in_front_of_the_usual_hierarchy(self):
        self.assertEqual(self.path(light_novel=True), 'Light Novels/Ayatsuji Yukito/Иная/Иная - 1 - Иная - Ayatsuji Yukito.m4b')
        self.assertEqual(self.path(light_novel=True, series='', number=''), 'Light Novels/Ayatsuji Yukito/Иная - Ayatsuji Yukito.m4b')
        planned = plan(self.root, dict(self.review, light_novel=True))
        self.assertEqual((planned['root'], planned['accepted_routing']['light_novel']), (self.root, True))
        # Positive control: an older review (no key) and an explicit No route exactly as before.
        self.assertEqual(self.path(), 'Ayatsuji Yukito/Иная/Иная - 1 - Иная - Ayatsuji Yukito.m4b')
        self.assertEqual(self.path(light_novel=False), self.path())
        self.assertNotIn('light_novel', plan(self.root, self.review)['accepted_routing'], 'older routing receipts are unchanged')

    def test_a_book_is_a_light_novel_or_a_collection_not_both(self):
        with self.assertRaisesRegex(ValueError, 'not both'):self.path(light_novel=True, anthology=True)
        with self.assertRaisesRegex(ValueError, 'explicit booleans'):self.path(light_novel='yes')


class NamesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.database = str(Path(self.temp.name) / 'catalog.sqlite3')
        self.row = {'id': 'book', 'members': [{'path': ROOT + '\\Light Novels\\A\\1.mp3', 'sha256': 'a' * 64, 'size': 1}], 'fingerprint': 'f'}

    def tearDown(self):
        self.temp.cleanup()

    def test_edit_names_saves_light_novel_as_yes_or_no(self):
        read = {'title': 'Иная', 'author': 'A', 'series': '', 'number': '', 'universe': '', 'collection': False, 'light_novel': True}
        entered_names.check({'light_novel': False})
        with self.assertRaisesRegex(ValueError, 'Light novel must be an explicit boolean'):entered_names.check({'light_novel': 'no'})
        with self.assertRaisesRegex(ValueError, 'not both'):entered_names.check({'light_novel': True, 'collection': True})
        entries = entered_names.plan(self.row, {'light_novel': False}, read, 'scope')
        self.assertEqual([(kind, field, value) for kind, field, value, *_ in entries], [('book', 'light_novel', 'false')], 'his untick is his value')
        entered_names.save(self.database, self.row, entries)
        self.assertEqual(entered_names.book_values(self.database, self.row), {'light_novel': False})
        self.assertEqual(entered_names.effective(self.database, self.row, read, 'scope')['light_novel']['value'], False)
        self.assertEqual(entered_names.remembered(self.database, self.row, read, 'scope')[0]['to'], 'false')
        self.assertEqual(entered_names.entered(entered_names.book_values(self.database, self.row)), ['light_novel'])

    def test_the_review_follows_typed_then_saved_then_the_folder_and_never_a_collection(self):
        from public_research import PublicResearch
        research = PublicResearch.__new__(PublicResearch)
        research.client = SimpleNamespace(database=self.database)
        def review(**extra):
            return research.light_novel({'review': dict({'title': 'Иная'}, **extra)}, self.row, ROOT, extra.pop('typed', None))['review']
        self.assertTrue(review()['light_novel'], 'the folder pre-ticks')
        entered_names.save(self.database, self.row, [('book', 'light_novel', 'false', '', '', '')])
        self.assertNotIn('light_novel', review(), 'his saved untick wins over the folder')
        result = research.light_novel({'review': {'title': 'Иная'}}, self.row, ROOT, {'light_novel': True})
        self.assertTrue(result['review']['light_novel'], 'a value typed now wins over the saved one')
        self.assertNotIn('light_novel', review(anthology=True), 'a collection is never a light novel')
        plain = dict(self.row, members=[{'path': ROOT + '\\Fiction\\A\\1.mp3'}])
        self.assertNotIn('light_novel', research.light_novel({'review': {'title': 'X'}}, plain, ROOT)['review'])


class FormTests(unittest.TestCase):
    def test_the_details_panel_and_manual_window_accept_light_novel(self):
        import manual_conversion
        values = {field: '' for field in manual_conversion.TEXT_FIELDS}
        self.assertEqual(manual_conversion._metadata(dict(values, light_novel=True))['light_novel'], True)
        self.assertIs(manual_conversion._metadata(dict(values, light_novel=False))['light_novel'], False, 'his untick is kept')
        self.assertNotIn('light_novel', manual_conversion._metadata(values))
        with self.assertRaisesRegex(ValueError, 'not both'):manual_conversion._metadata(dict(values, light_novel=True, anthology=True))


if __name__ == '__main__':
    unittest.main()
