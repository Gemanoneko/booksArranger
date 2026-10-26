"""Ruling 36 (Sergei 2026-10-26): Sergei's entries are final (ruling 6a); nothing asks for or requires evidence text.

- His Approve of the metadata no longer needs a "Manual evidence" note (it refused "Confirm the author role and record
  metadata evidence"), and his approved values count as approved without one (manual_metadata.approved).
- The background source refresh still never changes a book he entered values for: the protection is his "Entered by you"
  values, not an evidence note. A note alone protects nothing now.
- The stored notes stay in the catalog, unused.
A private catalog with a synthetic source file; no network, no library access."""
import base64
import json
import os
import tempfile
import unittest
from pathlib import Path

import manual_metadata
from scan_wait import finish_scan

AREA = Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT', 'C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared')) / 'no-evidence-tests'
PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='


class NoEvidenceTests(unittest.TestCase):
    def setUp(self):
        from scanner import Inventory
        from review_backend import CandidateReviewService
        AREA.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(temp.cleanup)
        base = Path(temp.name); audio = base / 'audio'; audio.mkdir()
        (audio / 'book.m4b').write_bytes(b'synthetic source fixture, not real audio'); (audio / 'cover.png').write_bytes(base64.b64decode(PNG))
        roots = {'Audiobooks': str(audio), 'Podcasts': str(base / 'podcasts'), 'Ebooks': str(base / 'ebooks')}
        def reader(path, kind, stop):
            return {'title': 'Book', 'track_title': 'Book', 'tags': {'album': 'Book'}, 'method': 'fixture', 'probe': {'format': {'duration': '1.0'}}}
        self.inv = Inventory(base / 'catalog.sqlite3', roots, reader); self.inv.launch('Audiobooks'); finish_scan(self.inv)
        self.service = CandidateReviewService(self.inv, base / 'cache')
        row = self.service.page()['rows'][0]
        self.row = self.service.covers('Audiobooks', row['id'], row['revision'])
        self.review = {'title': 'Book', 'author': 'Writer', 'canonical_author': 'Writer', 'original_language': 'Other'}

    def test_his_approve_needs_no_evidence_note(self):
        cover = self.row['cover_choices'][0]['id']
        accepted = self.service.save('Audiobooks', self.row['id'], self.row['revision'], self.review, True, '', cover_id=cover)
        self.assertTrue(accepted['metadata_approved'], 'approved with no note')
        ctx = self.service._context(accepted)
        self.assertTrue(manual_metadata.approved(dict(accepted, review=accepted['review']), ctx) or not ctx.get('manual_metadata_acceptance'),
                        'his approved values stand without a note')
        with self.assertRaisesRegex(ValueError, 'Confirm the author first.'):
            self.service.save('Audiobooks', accepted['id'], accepted['revision'], dict(self.review, canonical_author=''), True, '', cover_id=cover)
        with self.assertRaisesRegex(ValueError, 'evidence'):  # control: the assistant's own approvals still carry theirs
            self.service.save('Audiobooks', accepted['id'], accepted['revision'], self.review, True, '', cover_id=cover, actor='assistant')

    def test_manual_acceptance_holds_without_a_note(self):
        row = {'id': 'book-a', 'fingerprint': 'source-v1', 'review': {'title': 'Book', 'canonical_author': 'Writer'}}
        ctx = {'metadata_approved': True, 'metadata_actor': 'user', 'manual_note': '', 'manual_metadata_acceptance': manual_metadata.acceptance(row, row['review'])}
        self.assertTrue(manual_metadata.approved(row, ctx))

    def test_entered_values_protect_the_book_from_a_source_refresh_and_a_note_alone_does_not(self):
        from scanner import connect
        identity, revision = self.row['id'], self.row['revision']
        with connect(self.inv.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT)')
            db.execute('INSERT OR REPLACE INTO candidate_context(id,revision,data) VALUES(?,?,?)', (identity, revision, json.dumps({'manual_note': 'An old note'})))
        receipt = self.inv.refresh_candidate_sources('Audiobooks', identity, revision, force=True)
        self.assertNotIn('preserved', receipt.get('reason', ''), 'a note alone no longer protects the book')
        current = self.service.page()['rows'][0]
        with connect(self.inv.database) as db:
            manual_metadata.initialize(db)
            manual_metadata.append(db, manual_metadata.capture(current, {'title': 'Book'}, ''))
            db.execute('INSERT OR REPLACE INTO candidate_context(id,revision,data) VALUES(?,?,?)', (current['id'], current['revision'], json.dumps({})))
        receipt = self.inv.refresh_candidate_sources('Audiobooks', current['id'], current['revision'], force=True)
        self.assertEqual(receipt['state'], 'held');self.assertIn('preserved', receipt['reason'], 'his entered values protect it')


if __name__ == '__main__':
    unittest.main()
