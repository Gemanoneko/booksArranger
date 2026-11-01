"""0.24.2 backend integration regressions; private catalogs and deterministic seams.

No real media, provider, socket, codec, app or discovery operation is performed.
The production approval, cache, diagnostic, grouping and routing consumers run.
"""
import copy
import json
import os
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import admission_diagnostics
import groups
import pause_state
import public_research
from audio_pipeline import ChapterValidationError
from audio_jobs import AudioJobs
from automatic_processing import AutomaticProcessing
from merge_service import MergeService, SharedSnapshot, StatusUnavailable
from organization import plan
from review_backend import CandidateReviewService
from scanner import connect
from shared_routing import resolve

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'backend-242-tests'


class PrivateCatalog(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=AREA)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.db = self.base / 'catalog.sqlite3'
        self.source = str(self.base / 'source')
        self.output = str(self.base / 'sorted')
        with connect(self.db) as db:
            groups.setup(db)
            db.execute('CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT)')
            db.execute('CREATE TABLE automatic_candidates(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,state TEXT,result TEXT,retry_at REAL,attempted TEXT,matcher_version TEXT)')

    def put_book(self, identity=None, revision=2, fingerprint='same-files', review=None, members=None, scope=None):
        identity = identity or str(uuid.uuid4())
        members = members or [{'path': os.path.join(self.source, identity, 'book.m4b'), 'metadata': {}}]
        evidence = {'members': members, 'metadata': {}, 'conflicts': []}
        with connect(self.db) as db:
            db.execute('INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence,review,approved,changed) VALUES(?,?,?,?,?,?,?,?,?)',
                       (identity, self.source, scope or identity, revision, fingerprint, json.dumps(evidence), json.dumps(review) if review else '', 0, 0))
        return dict(evidence, id=identity, revision=revision, fingerprint=fingerprint, review=review, source_root=self.source)

    def stored_row(self, library, identity, revision=None):
        with connect(self.db) as db:
            row = db.execute('SELECT * FROM book_groups WHERE id=? AND superseded=0', (identity,)).fetchone()
        if not row or revision is not None and row['revision'] != revision:
            raise ValueError('Candidate changed; reload evidence before reviewing')
        return dict(json.loads(row['evidence']), id=row['id'], revision=row['revision'], fingerprint=row['fingerprint'],
                    review=json.loads(row['review']) if row['review'] else None, source_root=row['root'])

    def service(self):
        service = MergeService.__new__(MergeService)
        service.inventory = SimpleNamespace(database=self.db, worker=None, roots={'Audiobooks': self.source}, output_root=self.output)
        service.draining = False
        service.reviews = SimpleNamespace(_row=self.stored_row, _source_root=lambda row: self.source)
        return service


class ApprovalCurrentnessTests(PrivateCatalog):
    def setUp(self):
        super().setUp()
        self.current = self.put_book(review={'title': 'Newly edited metadata', 'author': 'Writer'})
        self.merge = self.service()
        reviews = CandidateReviewService.__new__(CandidateReviewService)
        reviews.inventory = SimpleNamespace(database=self.db, candidate=lambda library, identity: copy.deepcopy(self.current))
        reviews.page_local = threading.local()
        self.merge.reviews = reviews
        self.merge.jobs = SimpleNamespace(claimed=lambda job: False)
        self.research = Mock(side_effect=AssertionError('Stale approval must stop before research'))
        self.merge.automatic = SimpleNamespace(candidate=lambda row: None, retained=lambda row: None,
                                               research=SimpleNamespace(approved=self.research))
        self.job = str(uuid.uuid4())
        with connect(self.db) as db:
            db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT,state TEXT,reason TEXT,created TEXT,manifest_hash TEXT)')
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?)',
                       (self.job, json.dumps({'candidate_id': self.current['id']}), 'pending', 'manual accepted job', 'now', 'hash'))
            db.execute('INSERT INTO candidate_context VALUES(?,?,?)', (self.current['id'], 2, json.dumps({'user_approval': {'accepted': True}})))

    def test_no_preview_same_files_changed_metadata_refuses_stale_revision(self):
        with connect(self.db) as db:
            before = tuple(db.execute('SELECT * FROM audio_jobs').fetchone())
        with self.assertRaisesRegex(ValueError, 'Candidate changed'):
            self.merge.approve_book(self.current['id'], 1, fingerprint='same-files')
        self.research.assert_not_called()
        with connect(self.db) as db:
            self.assertEqual(tuple(db.execute('SELECT * FROM audio_jobs').fetchone()), before)
        self.assertEqual(self.current['review']['title'], 'Newly edited metadata')

    def test_preview_does_not_rebase_when_source_fingerprint_changed(self):
        with self.assertRaisesRegex(ValueError, 'Candidate changed'):
            self.merge.approve_book(self.current['id'], 1, path='shown.m4b', fingerprint='old-files')
        self.research.assert_not_called()


class PageConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.release = threading.Event()
        self.threads = []
        self.addCleanup(self.finish)

    def finish(self):
        self.release.set()
        for thread in self.threads:
            thread.join(3)
            self.assertFalse(thread.is_alive(), 'private page caller must terminate')

    def call_thread(self, operation, output):
        def call():
            try: output.append(('value', operation()))
            except BaseException as error: output.append(('error', error))
        thread = threading.Thread(target=call)
        self.threads.append(thread)
        thread.start()
        return thread

    def make_page(self):
        entered = threading.Event()
        calls = []
        merge = MergeService.__new__(MergeService)
        merge._quiet_token = lambda *args: None
        def page(*args):
            calls.append(args)
            entered.set()
            if not self.release.wait(3): raise AssertionError('private page computation did not release')
            return {'rows': [{'id': 'before-control'}], 'total': 1}
        merge.reviews = SimpleNamespace(page=page)
        return merge, entered, calls

    def test_same_page_key_shares_inflight_read_and_returns_detached_values(self):
        merge, entered, calls = self.make_page()
        first = []
        self.call_thread(lambda: merge.cached_page(50, 0, '', 'all'), first)
        self.assertTrue(entered.wait(2))
        # A bounded second read times out while joining the existing computation.
        shared = merge._page_shared[(50, 0, '', 'all', None)]
        shared._wait = .02
        with self.assertRaises(StatusUnavailable): merge.cached_page(50, 0, '', 'all')
        self.assertEqual(len(calls), 1)
        self.release.set()
        self.threads[0].join(3)
        self.assertEqual(first[0][0], 'value')
        first[0][1]['rows'][0]['id'] = 'mutated by caller'
        self.assertEqual(merge.cached_page(50, 0, '', 'all')['rows'][0]['id'], 'before-control')
        self.assertEqual(len(calls), 1)

    def test_invalidation_keeps_one_flight_but_rejects_its_precontrol_result(self):
        merge, entered, calls = self.make_page()
        output = []
        self.call_thread(lambda: merge.cached_page(50, 0, '', 'all'), output)
        self.assertTrue(entered.wait(2))
        shared = merge._page_shared[(50, 0, '', 'all', None)]
        shared._wait = .02
        merge.invalidate_status()
        with self.assertRaises(StatusUnavailable): merge.cached_page(50, 0, '', 'all')
        self.assertEqual(len(calls), 1, 'invalidation must not fork duplicate work')
        self.release.set()
        self.threads[0].join(3)
        self.assertEqual(output[0][0], 'error')
        self.assertIsInstance(output[0][1], StatusUnavailable)
        merge.reviews.page = Mock(return_value={'rows': [{'id': 'after-control'}], 'total': 1})
        self.assertEqual(merge.cached_page(50, 0, '', 'all')['rows'][0]['id'], 'after-control')
        merge.reviews.page.assert_called_once()

    def test_distinct_page_keys_do_not_share_the_wrong_result(self):
        merge = MergeService.__new__(MergeService)
        merge._quiet_token = lambda *args: None
        merge.reviews = SimpleNamespace(page=Mock(side_effect=lambda limit, offset, search, status: {'rows': [search]}))
        self.assertEqual(merge.cached_page(20, 0, 'first', 'all')['rows'], ['first'])
        self.assertEqual(merge.cached_page(20, 0, 'second', 'all')['rows'], ['second'])
        self.assertEqual(merge.reviews.page.call_count, 2)


class ChapterDiagnosticTests(PrivateCatalog):
    def setUp(self):
        super().setUp()
        self.row = self.put_book()
        self.other = self.put_book()
        self.review = CandidateReviewService.__new__(CandidateReviewService)
        self.review.inventory = SimpleNamespace(database=self.db)
        self.review.cache = self.base / 'cache'
        self.member = dict(self.row['members'][0], duration=10)
        self.diagnostic = {'file': 'book.m4b', 'path': self.member['path'], 'chapter_index': 2,
                           'chapter_id': 2, 'chapter_title': 'Last chapter', 'predicate': 'end_exceeds_audio',
                           'start': 8.0, 'end': 12.0, 'duration': 10.0}

    def test_joined_typed_failure_is_persisted_for_exact_candidate_and_activity_clears(self):
        failure = ChapterValidationError(copy.deepcopy(self.diagnostic))
        observed = []
        def verify(*args, **kwargs):
            kwargs['on_check']({'state': 'checking', 'path': self.member['path']})
            observed.append(copy.deepcopy(self.review._chapter_activity))
            raise failure
        with patch('audio_pipeline.verified_source_chapters', side_effect=verify):
            with self.assertRaises(ChapterValidationError) as raised:
                self.review.source_chapter_plan(self.row, self.member, {'sha256': 'a' * 64}, threading.Event(), joined=True)
        self.assertEqual(raised.exception.admission_error, {'chapter_diagnostic': self.diagnostic})
        self.assertEqual(set(observed[0]), {self.row['id']})
        self.assertEqual(self.review._chapter_activity, {})
        with connect(self.db) as db:
            self.assertEqual(admission_diagnostics.read(db, self.row), {'chapter_diagnostic': self.diagnostic})
            self.assertIsNone(admission_diagnostics.read(db, self.other))

    def test_single_source_uses_strict_parser_and_preserves_typed_failure(self):
        with patch('audio_pipeline.source_chapters', side_effect=ChapterValidationError(self.diagnostic)) as strict,              patch('audio_pipeline.verified_source_chapters') as joined:
            with self.assertRaises(ChapterValidationError):
                self.review.source_chapter_plan(self.row, self.member, {}, threading.Event(), joined=False)
        strict.assert_called_once()
        joined.assert_not_called()
        self.assertEqual(self.review._chapter_activity, {})

    def test_changed_revision_fingerprint_and_superseded_row_cannot_save_stale_diagnostic(self):
        for update in (dict(revision=3), dict(fingerprint='new-files')):
            with self.subTest(update=update), connect(self.db) as db:
                admission_diagnostics.save(db, dict(self.row, **update), self.diagnostic)
                self.assertIsNone(admission_diagnostics.read(db, self.row))
        with connect(self.db) as db:
            db.execute('UPDATE book_groups SET superseded=1 WHERE id=?', (self.row['id'],))
            admission_diagnostics.save(db, self.row, self.diagnostic)
            self.assertIsNone(admission_diagnostics.read(db, self.row))

    def test_currentness_and_clear_are_scoped_to_the_relevant_candidate(self):
        with connect(self.db) as db:
            admission_diagnostics.save(db, self.row, self.diagnostic)
            admission_diagnostics.save(db, self.other, self.diagnostic)
            self.assertIsNone(admission_diagnostics.read(db, dict(self.row, revision=3)))
            self.assertIsNone(admission_diagnostics.read(db, dict(self.row, fingerprint='new-files')))
            admission_diagnostics.clear(db, dict(self.row, revision=3))
            self.assertIsNotNone(admission_diagnostics.read(db, self.row))
            admission_diagnostics.clear(db, self.row)
            self.assertIsNone(admission_diagnostics.read(db, self.row))
            self.assertIsNotNone(admission_diagnostics.read(db, self.other))

    def test_interruption_clears_only_live_activity_and_never_invents_a_diagnostic(self):
        def interrupted(*args, **kwargs):
            kwargs['on_check']({'state': 'checking'})
            raise InterruptedError()
        with patch('audio_pipeline.verified_source_chapters', side_effect=interrupted):
            with self.assertRaises(InterruptedError):
                self.review.source_chapter_plan(self.row, self.member, {}, threading.Event(), joined=True)
        self.assertEqual(self.review._chapter_activity, {})
        with connect(self.db) as db: self.assertIsNone(admission_diagnostics.read(db, self.row))


class PauseAndMembershipTests(PrivateCatalog):
    def test_absent_pause_history_is_unknown_and_origins_remain_scope_specific(self):
        with connect(self.db) as db:
            self.assertIsNone(pause_state.read(db, 'jobs'))
            self.assertIsNone(pause_state.read(db, 'automatic'))
            user = pause_state.record(db, 'jobs', 'user', 'Paused by user')
            update = pause_state.record(db, 'automatic', 'update', 'Paused for update')
            self.assertEqual(pause_state.read(db, 'jobs'), user)
            self.assertEqual(pause_state.read(db, 'automatic'), update)
            pause_state.clear(db, 'automatic')
            self.assertIsNone(pause_state.read(db, 'automatic'))
            self.assertEqual(pause_state.read(db, 'jobs'), user)

    def test_automatic_stop_records_real_origin_and_passes_it_to_jobs(self):
        auto = AutomaticProcessing.__new__(AutomaticProcessing)
        auto.database = self.db
        auto.lock = threading.RLock()
        auto.start_pending = None
        auto.stop_event = threading.Event()
        auto._run_row = lambda: None
        auto.closed = False
        auto.inventory = SimpleNamespace(stop=Mock())
        auto.merge = SimpleNamespace(pause=Mock())
        auto.status = lambda: {'state': 'Paused'}
        for origin in ('update', 'closing', 'interrupted'):
            with self.subTest(origin=origin):
                auto.stop(force=True, origin=origin)
                with connect(self.db) as db: self.assertEqual(pause_state.read(db, 'automatic')['origin'], origin)
                auto.merge.pause.assert_called_with(origin=origin)
        auto.stop(force=True, origin='user')
        auto.merge.pause.assert_called_with()
        with connect(self.db) as db: self.assertEqual(pause_state.read(db, 'automatic')['origin'], 'user')

    def test_cancel_reports_whether_any_pending_start_existed(self):
        auto = AutomaticProcessing.__new__(AutomaticProcessing)
        auto.lock = threading.RLock()
        auto._pending_wake = threading.Event()
        auto.on_change = Mock()
        auto.status = lambda: {'state': 'Paused', 'start_pending': auto.start_pending}
        auto.start_pending = {'kind': 'scan'}
        self.assertEqual(auto.cancel_start(), {'state': 'Paused', 'start_pending': None, 'cancelled': True})
        self.assertEqual(auto.cancel_start(), {'state': 'Paused', 'start_pending': None, 'cancelled': False})
        self.assertTrue(auto._pending_wake.is_set())

    def test_membership_checking_requires_an_active_scan(self):
        service = self.service()
        service._unit_siblings = lambda db, row: []
        row = self.put_book()
        row['coverage'] = 'Scan incomplete'
        for worker, expected in ((None, False), (SimpleNamespace(is_alive=lambda: False), False),
                                 (SimpleNamespace(is_alive=lambda: True), True)):
            with self.subTest(active=expected):
                service.inventory.worker = worker
                payload = {'kind': 'files_unclear'}
                service._membership_lines(row, {}, payload)
                self.assertEqual(payload['membership_checking'], expected)
                self.assertEqual(payload['membership_reason'], 'incomplete_scan')

    def test_complete_scan_unresolved_siblings_is_a_hold_not_active_checking(self):
        service = self.service()
        service.inventory.worker = SimpleNamespace(is_alive=lambda: True)
        service._unit_siblings = lambda db, row: ['another-book']
        row = self.put_book()
        row['coverage'] = 'Scanned scope complete'
        payload = {'kind': 'files_unclear'}
        service._membership_lines(row, {}, payload)
        self.assertFalse(payload['membership_checking'])
        self.assertEqual(payload['membership_reason'], 'unresolved_siblings')
        service._unit_siblings = lambda db, row: []
        payload = {'kind': 'files_unclear'}
        service._membership_lines(row, {}, payload)
        self.assertEqual(payload['membership'], 'established')
        self.assertFalse(payload['membership_checking'])


def peer_result(work, author, series_url='https://fantlab.ru/work100', series='Series', number='1'):
    return {'work': {'id': work, 'verified_series': {'name': series, 'number': number, 'source_url': series_url}},
            'review': {'title': 'Book ' + work, 'author': author, 'canonical_author': author, 'series': series, 'number': number},
            'metadata_facts': {'source_fingerprint': 'files-' + work, 'work_ids': [work], 'authors': [author], 'series_state': 'verified'}}


class SharedPeerConsumerTests(PrivateCatalog):
    def setUp(self):
        super().setUp()
        self.merge = self.service()
        self.first = peer_result('catalog:one', 'Writer One')
        self.second = peer_result('catalog:two', 'Writer Two', number='2')
        self.one = self.add_result(self.first)
        self.two = self.add_result(self.second)
        auto = AutomaticProcessing.__new__(AutomaticProcessing)
        auto.database = self.db
        auto.rules_changed_for = Mock(return_value=False)
        auto.research = SimpleNamespace(identity=lambda row, root: ({'id': row['id']}, None),
                                        with_names=lambda row, root, local: local,
                                        approved=lambda row, root, retained: copy.deepcopy(retained['result']))
        self.merge.automatic = auto
        # The receipt validator has its own real-fixture tests in series-1. This seam
        # controls current local evidence while this suite exercises consumer filtering.
        self.validation = patch('public_research.retained_gap_fields', return_value={'eligible': True})
        self.validator = self.validation.start()
        self.addCleanup(self.validation.stop)

    def add_result(self, result):
        row = self.put_book(fingerprint=result['metadata_facts']['source_fingerprint'])
        with connect(self.db) as db:
            db.execute('INSERT INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',
                       (row['id'], row['revision'], row['fingerprint'], 'Held', json.dumps(result), None, 'fixed-stamp', 'fixture'))
        return row

    def routed(self):
        return self.merge._shared_result(self.one, self.first)

    def test_general_current_peer_omits_author_folder_but_keeps_author_credit(self):
        result = self.routed()
        self.assertTrue(resolve(result['review'], result['metadata_facts'])['multi_author_series'])
        self.assertEqual(plan(self.output, result['review'], facts=result['metadata_facts'])['relative_path'].split(os.sep)[0], 'Series')
        self.assertEqual(result['metadata_facts']['authors'], ['Writer One'])
        self.assertEqual(self.first['review']['author'], 'Writer One')

    def test_same_name_with_a_different_stable_series_id_does_not_join(self):
        self.second['work']['verified_series']['source_url'] = 'https://fantlab.ru/work999'
        with connect(self.db) as db:
            db.execute('UPDATE automatic_candidates SET result=? WHERE id=?', (json.dumps(self.second), self.two['id']))
        result = self.routed()
        self.assertFalse(resolve(result['review'], result['metadata_facts'])['multi_author_series'])

    def test_stale_fingerprint_rules_and_conflicting_local_names_cannot_supply_peer_authority(self):
        for cause in ('fingerprint', 'rules', 'names'):
            with self.subTest(cause=cause):
                self.merge._shared_peers = {}
                self.merge.automatic.rules_changed_for.return_value = cause == 'rules'
                self.validator.return_value = None if cause == 'names' else {'eligible': True}
                with connect(self.db) as db:
                    db.execute('UPDATE automatic_candidates SET fingerprint=? WHERE id=?',
                               ('stale' if cause == 'fingerprint' else self.two['fingerprint'], self.two['id']))
                result = self.routed()
                self.assertFalse(resolve(result['review'], result['metadata_facts'])['multi_author_series'])

    def test_peer_result_change_invalidates_cache_even_if_attempt_timestamp_does_not_change(self):
        self.assertTrue(resolve(self.routed()['review'], self.routed()['metadata_facts'])['multi_author_series'])
        self.second['work']['verified_series']['source_url'] = 'https://fantlab.ru/work999'
        with connect(self.db) as db:
            db.execute('UPDATE automatic_candidates SET result=? WHERE id=?', (json.dumps(self.second), self.two['id']))
        result = self.routed()
        self.assertFalse(resolve(result['review'], result['metadata_facts'])['multi_author_series'])

    def test_general_world_collects_two_distinct_series_by_confirmed_world_identity(self):
        self.second['work']['verified_series'].update(name='Other series', source_url='https://fantlab.ru/work200')
        self.second['review']['series'] = 'Other series'
        for result, row in ((self.first, self.one), (self.second, self.two)):
            result['review']['universe'] = 'Shared world'
            result['work']['verified_world'] = {'id': 'user:world-confirmed', 'name': 'Shared world', 'basis': 'user', 'evidence': ['user:world-decision']}
            with connect(self.db) as db:
                db.execute('UPDATE automatic_candidates SET result=? WHERE id=?', (json.dumps(result), row['id']))
        result = self.routed()
        self.assertTrue(resolve(result['review'], result['metadata_facts'])['shared_world'])
        self.assertEqual(plan(self.output, result['review'], facts=result['metadata_facts'])['relative_path'].split(os.sep)[:2], ['Shared world', 'Series'])


class QueenGroupingTests(PrivateCatalog):
    TITLES = ('Маскер', 'Безумие', 'Послание', 'Методы убийства')

    def setUp(self):
        super().setUp()
        self.paths = []
        folder = os.path.join(self.source, '2. Королева Бедлама')
        with connect(self.db) as db:
            for number, title in enumerate(self.TITLES, 1):
                path = os.path.join(folder, 'Часть ' + str(number) + '. ' + title + '.m4b')
                self.paths.append(path)
                metadata = {'tags': {'title': title, 'album': 'Королева Бедлама', 'artist': 'МакКаммон Роберт',
                                     'album_artist': 'МакКаммон Роберт', 'composer': 'Князев Игорь', 'track': str(number) + '/4'},
                            'probe': {'format': {'duration': '100'}, 'streams': [{'codec_type': 'audio', 'codec_name': 'aac', 'sample_rate': '44100', 'channels': 1}]}}
                db.execute('INSERT INTO files(root,path,size,modified,seen,kind,arrival,metadata) VALUES(?,?,?,?,?,?,?,?)',
                           (self.source, path, 100, 200, 1, 'audiobook', 0, json.dumps(metadata)))
                db.execute('INSERT INTO part_volumes VALUES(?,?,?,?,?,?)',
                           (self.source, path, 100, '200', 'each file names its own work', 'recorded'))

    def grouping(self, build=False):
        with connect(self.db) as db:
            inputs = groups._sync_inputs(db, self.source)
            return inputs, groups._sync_build(db, self.source, inputs) if build else None

    def test_confirmed_four_sections_become_one_candidate_and_old_receipts_remain(self):
        with connect(self.db) as db: before = [tuple(row) for row in db.execute('SELECT * FROM part_volumes ORDER BY path')]
        inputs, built = self.grouping(build=True)
        self.assertEqual(inputs['parts'][1], frozenset())
        self.assertEqual(len(built), 1)
        self.assertEqual({m['path'] for group in built.values() for m in group['members']}, set(self.paths))
        with connect(self.db) as db: self.assertEqual([tuple(row) for row in db.execute('SELECT * FROM part_volumes ORDER BY path')], before)

    def test_confirmed_identity_never_bypasses_missing_audio_profile(self):
        with connect(self.db) as db:
            for row in db.execute('SELECT path,metadata FROM files').fetchall():
                metadata=json.loads(row['metadata']);metadata['probe']['streams']=[]
                db.execute('UPDATE files SET metadata=? WHERE path=?',(json.dumps(metadata),row['path']))
        inputs,built=self.grouping(build=True)
        self.assertEqual(inputs['parts'][1],frozenset())
        self.assertEqual(len(built),4,'identity evidence does not waive recording compatibility')

    def test_explicit_keep_separate_on_any_member_protects_the_whole_edition(self):
        with connect(self.db) as db:
            db.execute('UPDATE part_volumes SET basis=? WHERE path=?', (groups.KEPT_BASIS, self.paths[0]))
        inputs, _ = self.grouping()
        self.assertEqual(inputs['parts'][1], frozenset(self.paths))
        self.assertIn(self.paths[0], inputs['parts'][2])

    def test_existing_job_or_review_protects_the_member_from_automatic_regroup(self):
        with connect(self.db) as db:
            member = groups.member(db.execute('SELECT * FROM files WHERE path=?', (self.paths[0],)).fetchone())
        row = self.put_book(members=[member], review={'title': 'Approved section'})
        inputs, _ = self.grouping()
        self.assertEqual(inputs['parts'][1], frozenset(self.paths))
        with connect(self.db) as db:
            db.execute("UPDATE book_groups SET review='' WHERE id=?", (row['id'],))
            db.execute('CREATE TABLE audio_jobs(manifest TEXT)')
            db.execute('INSERT INTO audio_jobs VALUES(?)', (json.dumps({'candidate_id': row['id']}),))
        inputs, _ = self.grouping()
        self.assertEqual(inputs['parts'][1], frozenset(self.paths))

    def test_wrong_writer_or_missing_section_never_fabricates_exact_edition(self):
        with connect(self.db) as db:
            raw = db.execute('SELECT metadata FROM files WHERE path=?', (self.paths[0],)).fetchone()[0]
            changed = json.loads(raw)
            changed['tags']['artist'] = 'Different writer'
            db.execute('UPDATE files SET metadata=? WHERE path=?', (json.dumps(changed), self.paths[0]))
        self.assertEqual(self.grouping()[0]['parts'][1], frozenset(self.paths))
        with connect(self.db) as db:
            db.execute('UPDATE files SET metadata=? WHERE path=?', (raw, self.paths[0]))
            db.execute('DELETE FROM files WHERE path=?', (self.paths[-1],))
        self.assertEqual(self.grouping()[0]['parts'][1], frozenset(self.paths[:-1]))


class PublishedVerifierTests(PrivateCatalog):
    def setUp(self):
        super().setUp()
        self.jobs = AudioJobs(self.db, None, lambda manifest: True, lambda record: True)
        self.addCleanup(self.jobs.close)
        self.foreground = threading.Event()
        self.jobs.background_stop = self.foreground
        self.created = []

    def published(self):
        identity = str(uuid.uuid4())
        job = str(uuid.uuid4())
        manifest = {'job_id': job, 'candidate_id': identity, 'candidate_revision': 1,
                    'sources': [{'path': os.path.join(self.source, identity, 'book.m4b'), 'sha256': 'a' * 64, 'fingerprint': {'size': 10, 'modified': '1'}}],
                    'metadata': {'title': 'Private'}, 'destination': os.path.join(self.output, job + '.m4b'),
                    'profile': 'private', 'evidence': {}, 'cover': {}}
        self.jobs.enqueue(manifest)
        record = {'job_id': job, 'final_path': manifest['destination'], 'owned_temp': os.path.join(str(self.base), 'owned-' + job),
                  'sha256': 'b' * 64, 'size': 100, 'validation': {'passed': True}}
        self.created.append(job)
        self.jobs._update(job, state='completed', stage='completed', output=json.dumps(record), created=str(len(self.created)).zfill(3))
        return job

    def run_idle(self):
        self.jobs.start_published_check()
        thread = self.jobs._verifier
        self.assertIsNotNone(thread)
        thread.join(3)
        self.assertFalse(thread.is_alive(), 'private verifier must close')

    def row(self, job):
        return self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job,))[0]

    def test_validation_fault_then_lift_is_rechecked_and_restores_completed(self):
        job = self.published()
        original = self.row(job)
        blocked = [True]
        calls = []
        def validate(record, stop, pace):
            calls.append(record['job_id'])
            if blocked[0]: raise PermissionError('private held-open output')
            return True
        self.jobs.output_current = validate
        with patch('audio_jobs.time.monotonic', return_value=1000) as clock:
            self.run_idle()
            self.assertEqual(self.row(job)['state'], 'needs attention')
            self.assertIn('held-open', self.row(job)['reason'])
            self.run_idle()
            self.assertEqual(calls, [job], 'bounded retry delay avoids repeated fault probes')
            blocked[0] = False
            clock.return_value = 1061
            self.run_idle()
        current = self.row(job)
        self.assertEqual(current['state'], 'completed')
        self.assertEqual(current['reason'], '')
        self.assertEqual(current['output'], original['output'])
        self.assertEqual(current['manifest'], original['manifest'])
        self.assertEqual(current['manifest_hash'], original['manifest_hash'])
        self.assertEqual(calls, [job, job])

    def test_interrupted_idle_pass_resumes_only_the_unchecked_rows(self):
        first, second, third = [self.published() for _ in range(3)]
        calls = []
        interrupted = [False]
        def validate(record, stop, pace):
            job = record['job_id']
            calls.append(job)
            if job == second and not interrupted[0]:
                interrupted[0] = True
                self.foreground.set()
                raise InterruptedError('private foreground work preempted check')
            return True
        self.jobs.output_current = validate
        self.run_idle()
        self.assertEqual(calls, [first, second])
        self.assertTrue(all(self.row(job)['state'] == 'completed' for job in self.created))
        self.foreground.clear()
        self.run_idle()
        self.assertEqual(calls, [first, second, second, third])
        self.assertIsNone(self.jobs._thread, 'no conversion worker was started')

    def test_verifier_does_not_overwrite_a_row_changed_while_validation_runs(self):
        job = self.published()
        self.jobs._update(job, state='needs attention', reason='old validation failure')
        def validate(record, stop, pace):
            self.jobs._update(job, reason='newer user-visible failure')
            return True
        self.jobs.output_current = validate
        self.run_idle()
        self.assertEqual(self.row(job)['state'], 'needs attention')
        self.assertEqual(self.row(job)['reason'], 'newer user-visible failure')


if __name__ == '__main__':
    unittest.main()
