"""Ruling 78: explicit Start over retains choices, refreshes only its observed sources.

Private SQLite catalogs and tiny synthetic bytes only. No scan worker, HTTP, codec,
publication, app launch or source discovery. Production guards and refresh commit run.
"""
import copy
import hashlib
import json
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import book_restart
import groups
import m4b_readmission
import retry_refusal
from audio_jobs import AudioJobs
from automatic_processing import AutomaticProcessing
from merge_service import MergeService
from review_backend import member_key
from scanner import Inventory, connect

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'restart-242-tests'


class RestartFixture(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.db = self.base / 'catalog.sqlite3'
        self.library = self.base / 'source'
        self.folder = self.library / 'A Book'
        self.folder.mkdir(parents=True)
        self.sorted = self.base / 'sorted'
        self.sorted.mkdir()
        self.paths = [str(self.folder / ('Part ' + str(n).zfill(2) + '.m4b')) for n in (1, 2)]
        self.reader = Mock(side_effect=lambda path, *_: self.metadata(path))
        self.inv = Inventory(self.db, {'Audiobooks': str(self.library)}, self.reader, output_root=str(self.sorted))
        with connect(self.db) as db:
            groups.setup(db)
            db.execute('CREATE TABLE candidate_context(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL)')
            for path in self.paths:
                Path(path).write_bytes(b'private source fixture ' + Path(path).name.encode())
                stat = Path(path).stat()
                db.execute('INSERT INTO files(root,path,size,modified,seen,kind,arrival,metadata) VALUES(?,?,?,?,?,?,?,?)',
                           (str(self.library), path, stat.st_size, stat.st_mtime_ns, 1, 'audiobook', 0, json.dumps(self.metadata(path))))
            db.execute("INSERT INTO jobs(root,label,generation,state) VALUES(?,?,1,'completed')", (str(self.library), 'Audiobooks'))
        rows = self.inv.candidates('Audiobooks')['rows']
        self.assertEqual(len(rows), 1, 'matching recording facts and explicit parts establish one private book')
        self.assertEqual({member['path'] for member in rows[0]['members']}, set(self.paths))
        self.id = rows[0]['id']
        self.review = {'title': 'Accepted title', 'author': 'John Writer', 'series': 'Accepted series', 'number': '2'}
        self.context = {'track_actor': 'user', 'track_order': [member_key(p) for p in reversed(self.paths)],
                        'included': [member_key(p) for p in self.paths], 'cover_id': 'chosen-cover',
                        'cover_choices': [{'id': 'chosen-cover', 'sha256': 'c' * 64}], 'manual_note': 'Accepted note',
                        'metadata_actor': 'user', 'destination_override': {'folder': str(self.sorted / 'Chosen')},
                        'metadata_facts': {'stale': True}, 'duplicate_review': {'stale': True},
                        'source_hashes': {'old': 'a' * 64}, 'metadata_approved': True,
                        'source_coverage_confirmed': True, 'order_confirmed': True}
        with connect(self.db) as db:
            db.execute('UPDATE book_groups SET review=?,approved=1 WHERE id=?', (json.dumps(self.review), self.id))
            db.execute('INSERT INTO candidate_context VALUES(?,?,?)', (self.id, rows[0]['revision'], json.dumps(self.context)))
        self.jobs = AudioJobs(self.db, None, lambda manifest: True, lambda record: False)
        self.addCleanup(self.jobs.close)
        self.row = self.current()
        self.manifest = {'job_id': str(uuid.uuid4()), 'candidate_id': self.id, 'candidate_revision': self.row['revision'],
                         'root': str(self.library), 'metadata': copy.deepcopy(self.review), 'sources': [],
                         'destination': str(self.sorted / 'accepted.m4b'), 'profile': 'private-fixture',
                         'evidence': {'manual_note': 'Accepted note'}, 'cover': {'id': 'chosen-cover'},
                         'cleanup_policy': {'enabled': False}}
        for path in reversed(self.paths):
            stat = Path(path).stat()
            self.manifest['sources'].append({'path': path, 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                                             'fingerprint': {'size': stat.st_size, 'modified': str(stat.st_mtime_ns)}})
        self.job = self.jobs.enqueue(self.manifest)
        self.jobs._update(self.job, state='needs attention', stage='checking', reason='private source changed',
                          journal=json.dumps({'failure': {'retryable': False}}))
        with connect(self.db) as db:
            m4b_readmission.ensure(db)
            record = retry_refusal.record('Frozen source changed; failed job preserved', 'source_changed', '2026-11-01T00:00:00Z')
            db.execute('INSERT INTO m4b_readmissions VALUES(?,?,?,?,?,?,?,?)',
                       (self.job, 'retry', 1, 'refused', None, json.dumps(record), 'a', 'b'))
        service = MergeService.__new__(MergeService)
        service.inventory = self.inv
        service.jobs = self.jobs
        service.draining = False
        service.pause = Mock()  # Teardown stops a private automatic controller; queue pause is tested separately.
        service.operation_lock = threading.RLock()
        service.reviews = SimpleNamespace(lock=threading.RLock(), _context=self.context_for,
                                         _row=lambda library, identity, revision=None: self.inv.candidate(library, identity))
        service.invalidate_status = Mock()
        service.restart_row = Mock(return_value=None)
        service.attention_summary = Mock(return_value={self.job: {'startover': 'automatic'}})
        self.auto = AutomaticProcessing(service, research=SimpleNamespace(client=None))
        self.addCleanup(self.auto.close)
        self.auto.request_start = Mock(return_value={'action': 'started'})
        service.automatic = self.auto
        self.service = service

    @staticmethod
    def metadata(path):
        # Whole M4Bs require recording evidence before they can be one part set.
        # These facts belong only to the generated fixture; no media probe runs.
        number = int(Path(path).stem.rsplit(' ', 1)[1])
        return {'title': 'A Book', 'artist': 'John Writer',
                'tags': {'title': 'Part ' + str(number), 'album': 'A Book', 'artist': 'John Writer', 'track': str(number) + '/2'},
                'probe': {'format': {'duration': '1'},
                          'streams': [{'codec_type': 'audio', 'codec_name': 'aac', 'sample_rate': '24000', 'channels': 1}]}}

    def current(self):
        return self.inv.candidate('Audiobooks', self.id)

    def context_for(self, row):
        with connect(self.db) as db:
            value = db.execute('SELECT revision,data FROM candidate_context WHERE id=?', (row['id'],)).fetchone()
        return json.loads(value['data']) if value and value['revision'] == row['revision'] else {}

    def saved_context(self):
        with connect(self.db) as db:
            row = db.execute('SELECT revision,data FROM candidate_context WHERE id=?', (self.id,)).fetchone()
        return row['revision'], json.loads(row['data'])

    def set_context(self, value):
        with connect(self.db) as db:
            db.execute('UPDATE candidate_context SET data=? WHERE id=?', (json.dumps(value), self.id))

    def press(self):
        return self.service.start_over('Audiobooks', self.id, self.row['revision'], self.job)

    def before_job(self):
        return self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?', (self.job,))[0]

    def repair(self):
        Path(self.paths[0]).write_bytes(b'private repaired bytes')

    def refresh(self):
        return self.inv.refresh_candidate_sources('Audiobooks', self.id, self.row['revision'], force=True, restart_job=self.job)


class RestartApprovalTests(RestartFixture):
    def test_saved_approval_returns_to_automatic_and_keeps_choices_and_frozen_job(self):
        before = self.before_job()
        answer = self.press()
        self.assertEqual(answer['outcome'], 'automatic')
        self.auto.request_start.assert_called_once_with(server_closing=False)
        row = self.current()
        self.assertEqual(row['review'], self.review)
        self.assertFalse(self.auto.manual_draft(row))
        with connect(self.db) as db:
            self.assertFalse(book_restart.book(db, self.id)['manual_draft'])
            self.assertIsNone(book_restart.current_job(db, self.id))
        context = self.context_for(row)
        for key in ('track_order', 'included', 'track_actor', 'cover_id', 'cover_choices', 'manual_note', 'destination_override'):
            self.assertEqual(context[key], self.context[key], key)
        for key in ('metadata_facts', 'duplicate_review', 'automatic_approval', 'automatic_pending'):
            self.assertNotIn(key, context)
        self.assertEqual(context['source_hashes'], {})
        self.assertFalse(context['metadata_approved'])
        self.assertEqual(self.before_job(), before, 'immutable manifest, hash, journal and job row')

    def test_changed_review_is_a_real_manual_draft_and_is_not_discarded(self):
        edited = dict(self.review, title='New unapproved title')
        with connect(self.db) as db:
            db.execute('UPDATE book_groups SET review=? WHERE id=?', (json.dumps(edited), self.id))
        before = self.saved_context()
        self.assertEqual(self.press()['outcome'], 'manual_draft')
        self.assertEqual(self.current()['review'], edited)
        self.assertEqual(self.saved_context(), before)
        self.assertTrue(self.auto.manual_draft(self.current()))

    def test_unapproved_notes_cover_order_and_draft_flag_are_not_reclassified(self):
        for update in ({'manual_note': 'New note'}, {'cover_id': 'different-cover'},
                       {'track_order': list(reversed(self.context['track_order']))}, {'manual_draft_active': True}):
            with self.subTest(update=update):
                self.set_context(dict(self.context, **update))
                with connect(self.db) as db:
                    facts = book_restart.book(db, self.id)
                    self.assertFalse(book_restart.prepare_automatic(db, facts, self.manifest))
                self.assertEqual(self.saved_context()[1], dict(self.context, **update))

    def test_editing_lease_stays_a_hold_with_unchanged_saved_approval(self):
        with connect(self.db) as db:
            db.execute('INSERT INTO automatic_manual_drafts VALUES(?,?,?)', (self.id, self.row['revision'], time.time() + 300))
        self.assertEqual(self.press()['outcome'], 'manual_draft')
        self.assertTrue(self.auto.manual_draft(self.current()))
        self.assertNotIn('automatic_restart', self.saved_context()[1])

    def test_restart_marker_binds_candidate_revision_fingerprint_and_review(self):
        self.press()
        context = self.context_for(self.row)
        self.assertTrue(book_restart.restart_current(self.row, context))
        for field, value in (('id', str(uuid.uuid4())), ('revision', self.row['revision'] + 1),
                             ('fingerprint', 'different'), ('review', dict(self.review, title='Edited'))):
            with self.subTest(field=field):
                self.assertFalse(book_restart.restart_current(dict(self.row, **{field: value}), context))
        self.assertFalse(book_restart.restart_current(self.row, dict(context, manual_draft_active=True)))

    def test_first_restart_creates_immediate_refresh_record_without_an_old_auto_row(self):
        self.press()
        with connect(self.db) as db:
            saved = dict(db.execute('SELECT * FROM automatic_candidates WHERE id=?', (self.id,)).fetchone())
        self.assertEqual(saved['state'], 'Pending')
        self.assertIsNone(saved['retry_at'])
        self.assertTrue(json.loads(saved['result'])['source_refresh_required'])

    def test_restart_removes_old_backoff_and_reasons_but_keeps_research_history(self):
        old = {'reasons': ['Source files changed'], 'wait': {'retry_at': 9999999999}, 'gap_deferrals': {'old': 1},
               'research_history': [{'attempt': 3}], 'job_id': self.job}
        with connect(self.db) as db:
            db.execute('INSERT INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',
                       (self.id, self.row['revision'], self.row['fingerprint'], 'Held', json.dumps(old), time.time() + 300, 'old', 'v'))
        self.press()
        with connect(self.db) as db:
            saved = dict(db.execute('SELECT * FROM automatic_candidates WHERE id=?', (self.id,)).fetchone())
        result = json.loads(saved['result'])
        self.assertIsNone(saved['retry_at'])
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['research_history'], old['research_history'])
        self.assertNotIn('wait', result)
        self.assertNotIn('gap_deferrals', result)


class RestartRefreshTests(RestartFixture):
    def test_repaired_sources_refresh_without_scan_and_rebase_preserved_choices(self):
        self.press()
        old_context = self.saved_context()[1]
        before = self.before_job()
        self.repair()
        with patch.object(self.inv, 'refresh_candidate_sources', wraps=self.inv.refresh_candidate_sources) as refresh:
            result = self.auto._refresh_observed_sources(self.row, {'source_refresh_required': True})
        self.assertEqual(result['state'], 'refreshed', result)
        refresh.assert_called_once()
        self.assertTrue(refresh.call_args.kwargs['force'])
        self.assertEqual(refresh.call_args.kwargs['restart_job'], self.job)
        current = result['row']
        self.assertGreater(current['revision'], self.row['revision'])
        self.assertNotEqual(current['fingerprint'], self.row['fingerprint'])
        revision, context = self.saved_context()
        self.assertEqual(revision, current['revision'])
        self.assertEqual(context, dict(old_context, automatic_restart=dict(old_context['automatic_restart'],
                                                                         revision=current['revision'], fingerprint=current['fingerprint'])))
        self.assertFalse(self.auto.manual_draft(current))
        self.assertEqual(self.before_job(), before)
        self.assertIsNone(self.inv.worker)
        self.assertEqual(self.reader.call_count, 2)
        self.assertEqual(Path(self.paths[0]).read_bytes(), b'private repaired bytes')

    def test_failed_job_without_exact_startover_authority_stays_protected(self):
        self.repair()
        result = self.refresh()
        self.assertEqual(result['state'], 'held')
        self.reader.assert_not_called()
        self.assertEqual(self.current()['fingerprint'], self.row['fingerprint'])

    def test_refresh_authority_rejects_other_candidate_wrong_paths_and_stale_marker(self):
        self.press()
        with connect(self.db) as db:
            self.assertTrue(book_restart.refresh_authority(db, self.row, self.paths, self.job))
            self.assertFalse(book_restart.refresh_authority(db, dict(self.row, id=str(uuid.uuid4())), self.paths, self.job))
            self.assertFalse(book_restart.refresh_authority(db, self.row, self.paths[:1], self.job))
            self.assertFalse(book_restart.refresh_authority(db, self.row, self.paths, str(uuid.uuid4())))
            db.execute("UPDATE automatic_restarts SET kind='release' WHERE id=?", (self.id,))
            self.assertFalse(book_restart.refresh_authority(db, self.row, self.paths, self.job))

    def test_unrelated_durable_job_on_a_member_still_blocks_refresh(self):
        self.press()
        other = copy.deepcopy(self.manifest)
        other.update(job_id=str(uuid.uuid4()), candidate_id=str(uuid.uuid4()), destination=str(self.sorted / 'other.m4b'))
        other_job = self.jobs.enqueue(other)
        self.repair()
        result = self.refresh()
        self.assertEqual(result['state'], 'held', result)
        self.assertIn('durable conversion job', result['reason'])
        self.reader.assert_not_called()
        self.assertIsNotNone(self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?', (other_job,)))

    def test_same_candidate_new_job_is_not_covered_by_the_old_setaside(self):
        self.press()
        other = copy.deepcopy(self.manifest)
        other.update(job_id=str(uuid.uuid4()), candidate_revision=self.row['revision'] + 1)
        self.jobs.enqueue(other)
        self.assertEqual(self.refresh()['state'], 'held')
        self.reader.assert_not_called()

    def test_publication_intent_output_and_cleanup_each_revoke_refresh_authority(self):
        self.press()
        before = self.before_job()
        for field, value in (('journal', json.dumps({'publication_intent': {}})), ('output', json.dumps({'path': 'fixture'}))):
            with self.subTest(field=field):
                self.jobs._update(self.job, **{field: value})
                self.assertEqual(self.refresh()['state'], 'held')
                self.jobs._update(self.job, **{field: before[field]})
        with connect(self.db) as db:
            db.execute('CREATE TABLE source_cleanup(job_id TEXT)')
            db.execute('INSERT INTO source_cleanup VALUES(?)', (self.job,))
        self.assertEqual(self.refresh()['state'], 'held')
        self.reader.assert_not_called()

    def test_new_saved_choices_during_refresh_are_not_overwritten(self):
        self.press()
        self.repair()
        refresh = self.inv.refresh_candidate_sources
        def race(*args, **kwargs):
            result = refresh(*args, **kwargs)
            revision, context = self.saved_context()
            self.set_context(dict(context, manual_note='New note during refresh'))
            return result
        with patch.object(self.inv, 'refresh_candidate_sources', side_effect=race):
            result = self.auto._refresh_observed_sources(self.row, {'source_refresh_required': True})
        self.assertEqual(result['state'], 'held', result)
        self.assertIn('Saved choices changed', result['reason'])
        self.assertEqual(self.saved_context()[1]['manual_note'], 'New note during refresh')

    def test_new_candidate_revision_during_context_rebase_is_not_overwritten(self):
        self.press()
        self.repair()
        get_row = self.service.reviews._row
        def race(*args):
            current = get_row(*args)
            with connect(self.db) as db:
                db.execute('UPDATE book_groups SET revision=revision+1 WHERE id=?', (self.id,))
            return current
        with patch.object(self.service.reviews, '_row', side_effect=race):
            result = self.auto._refresh_observed_sources(self.row, {'source_refresh_required': True})
        self.assertEqual(result['state'], 'held', result)
        self.assertIn('Book changed', result['reason'])
        self.assertEqual(self.saved_context()[0], self.row['revision'])

    def test_cancelled_refresh_never_reads_and_automatic_caller_stops(self):
        self.press()
        self.auto.stop_event.set()
        with self.assertRaises(InterruptedError):
            self.auto._refresh_observed_sources(self.row, {'source_refresh_required': True})
        self.reader.assert_not_called()
        self.auto.request_start.assert_called_once()

    def test_ordinary_unchanged_candidate_does_not_request_a_forced_refresh(self):
        with patch.object(self.inv, 'refresh_candidate_sources') as refresh:
            self.assertIsNone(self.auto._refresh_observed_sources(self.row, {'reasons': []}))
        refresh.assert_not_called()
